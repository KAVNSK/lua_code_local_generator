# LocalScript Agent (`json_context`)

Локальный сервис генерации и отладки Lua-кода: `FastAPI` + `Ollama` + repair loop + проверки качества. Runtime не использует внешние LLM API.

API-контракт: `../localscript-openapi.yaml`

## Назначение

Проект реализует stateless tim-style агентный контур:
- генерация Lua по естественному языку;
- встроенный clarification в `POST /generate`;
- итеративная доработка через `POST /refine`;
- диагностика кода через `POST /debug`;
- воспроизводимый локальный запуск для MLOps/DevOps.

## Архитектура

Основные модули:
- `app/main.py` — HTTP endpoints;
- `app/pipeline.py` — orchestration generate/refine/debug + repair loop;
- `app/code_checks.py` — `run_all_checks` (syntax/static/sandbox/semantic);
- `app/generate_parse.py` — JSON parse model output;
- `app/prompts.py` — шаблоны prompt-коммуникации;
- `app/ollama_client.py` — вызовы Ollama, health/warmup.

## API

База: `http://127.0.0.1:8080`

Эндпоинты:
- `GET /health`
- `POST /generate`
- `POST /refine`
- `POST /debug`

Модель API в этой ветке:
- clarification встроен в `POST /generate` и возвращается как `response_kind=clarification`;
- финальный код возвращается как `response_kind=code`;
- telemetry включает:
  - `attempts`
  - `all_checks_passed`
  - `degraded`
  - `stop_reason`
  - `llm_rounds`
  - `repair_rounds_used`.

## Быстрый запуск (Docker)

```bash
cd localscript-agent
docker compose up --build
```

После старта:
- API: `http://127.0.0.1:8080`
- Ollama: `http://127.0.0.1:11434`
- модель: `qwen2.5-coder:7b`

## Рекомендуемые параметры модели

```bash
ollama pull qwen2.5-coder:7b
```

- `NUM_CTX=4096`
- `NUM_PREDICT=256`
- `NUM_BATCH=1`
- `NUM_PARALLEL=1`
- `OLLAMA_NUM_GPU=999`

## Локальная разработка

```bash
./scripts/bootstrap_dev.sh
conda activate localscript-agent
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Требуется `lua` и `luac` в `PATH`.

## Эксплуатация CLI

Интерактивный клиент: `scripts/demo_cli.py`

```bash
python scripts/demo_cli.py
```

Полезные флаги:
- `--base-url`
- `--timeout`
- `--context-file`
- `--verbose`

Команды:
- `/help`, `/quit`
- `/health`, `/settings`, `/url <url>`
- `/ctx <file.json>`, `/ctx show`, `/ctx clear`
- `/refine`
- `/debug`, `/debug <text>`, `/debug new`
- `/log`, `/log N`, `/log all`, `/log clear`

## Эксплуатация GUI

GUI: `scripts/demo_streamlit.py`

```bash
python -m streamlit run scripts/demo_streamlit.py
```

GUI поддерживает:
- stateless flow generate/refine/debug;
- clarification chat и хранение истории на клиенте;
- semantic rules injection в prompt (`Context:` блок);
- сохранение/загрузку истории:
  - `artifacts/gui_chat_history.jsonl`.

## Тесты и качество

```bash
ruff check .
pytest -q
```

или:

```bash
./scripts/quality.sh
```

## Оценка на публичной выборке

HTTP-режим:

```bash
python scripts/eval_public.py --http --base-url http://127.0.0.1:8080
```

Direct/in-process:

```bash
python scripts/eval_public.py
```

## Отличия от `lua_manual` версии

- clarification реализован внутри `POST /generate` (нет отдельных `/clarify` и `/generate-from-clarify`);
- есть `POST /debug`;
- есть полноценный интерактивный CLI REPL;
- richer telemetry в ответе (`attempts`, `stop_reason`, `degraded` и т.д.).

## Дополнительная документация

- `docs/SETUP_GUIDE.md`
- `docs/AGENT_WORKFLOW.md`
- `docs/CLI_CURRENT_BEHAVIOR.md`
- `docs/architecture.md`
- `docs/hardware.md`
- `docs/vram_smoke.md`
- `docs/experiments/BEST_CONFIG.md`
- `docs/SUBMISSION.md`
