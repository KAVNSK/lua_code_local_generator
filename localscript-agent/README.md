# LocalScript Agent (`lua_manual`)

Локальный сервис генерации Lua-кода для защищенных контуров: `FastAPI` + `Ollama` + встроенный pipeline проверки и доработки кода. Runtime не использует внешние LLM API.

API-контракт: `../localscript-openapi.yaml`

## Назначение

Проект реализует агентный цикл под требования трека:
- генерация Lua по естественному языку;
- уточнение требований перед генерацией;
- итеративная доработка кода по обратной связи;
- синтаксическая, статическая и опциональная семантическая валидация;
- reproducible deployment для MLOps/DevOps.

## Архитектура

Основные модули:
- `app/main.py` — endpoints и lifecycle приложения;
- `app/pipeline.py` — generate/repair loop + confidence gate;
- `app/clarify.py` — построение уточняющих вопросов и merge контекста;
- `app/validate.py` — `luac` + статические ограничения;
- `app/semantic.py`, `app/sandbox.py` — семантическая проверка через sandbox;
- `app/ollama_client.py` — интеграция с локальным Ollama.

## API

База: `http://127.0.0.1:8080`

Эндпоинты:
- `GET /health`
- `POST /clarify`
- `POST /generate-from-clarify`
- `POST /generate`
- `POST /refine`

Модель API в этой ветке:
- clarification вынесен в отдельные endpoints;
- ответ генерации содержит `code` и опционально confidence-gate поля:
  - `confidence_gate_triggered`
  - `repair_report`.

## Быстрый запуск (Docker)

```bash
cd localscript-agent
docker compose up --build
```

После старта:
- API: `http://127.0.0.1:8080`
- Ollama: `http://127.0.0.1:11434`
- модель по умолчанию: `qwen2.5-coder:7b`

## Рекомендуемые параметры модели

```bash
ollama pull qwen2.5-coder:7b
```

- `NUM_CTX=4096`
- `NUM_PREDICT=256`
- `NUM_BATCH=1`
- `NUM_PARALLEL=1`
- `OLLAMA_NUM_GPU=999` (полное размещение слоев на GPU)

Особенности этой ветки:
- в `docker-compose.yml` включен warmup:
  - `OLLAMA_WARMUP_ENABLED=true`
  - `OLLAMA_WARMUP_TIMEOUT_SECONDS=240`
  - `OLLAMA_HEALTH_TIMEOUT_SECONDS=5`.

## Локальная разработка

```bash
./scripts/bootstrap_dev.sh
conda activate localscript-agent
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Требуется наличие `lua` и `luac` в `PATH`.

## Эксплуатация GUI

GUI: `scripts/demo_streamlit.py`

```bash
python -m streamlit run scripts/demo_streamlit.py
```

GUI поддерживает:
- проверку `health`;
- flow `clarify -> generate-from-clarify -> refine`;
- режим `generate` с optional `previous_code`/`feedback`;
- инъекцию `__semantic_validation` в `context`;
- панель `Action readiness` для валидации входов до отправки.

## Эксплуатация CLI

В этой ветке нет отдельного интерактивного REPL-клиента.  
CLI-сценарии выполняются через `curl`/PowerShell или CI-скрипты.

Примеры:

```bash
curl -s http://127.0.0.1:8080/health
```

```bash
curl -s http://127.0.0.1:8080/clarify \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Отфильтруй parsedCsv по Discount\",\"context\":null,\"answers\":[]}"
```

```bash
curl -s http://127.0.0.1:8080/refine \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"То же задание\",\"previous_code\":\"return n\",\"feedback\":\"Добавь проверку входа\"}"
```

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

## Отличия от `json_context` версии

- здесь используются отдельные `POST /clarify` и `POST /generate-from-clarify`;
- нет `POST /debug`;
- акцент на confidence-gate (`confidence_gate_triggered`, `repair_report`);
- нет отдельного demo CLI REPL.

## Дополнительная документация

- `docs/SETUP_GUIDE.md`
- `docs/AGENT_WORKFLOW.md`
- `docs/architecture.md`
- `docs/hardware.md`
- `docs/vram_smoke.md`
- `docs/experiments/BEST_CONFIG.md`
- `docs/SUBMISSION.md`
