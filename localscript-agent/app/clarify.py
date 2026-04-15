from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

from app.models_io import ClarifyAnswer, ClarifyQuestion, ClarifyResponse


@dataclass(slots=True)
class _RuleQuestion:
    id: str
    text: str
    why: str
    blocking: bool
    options: list[str]


def build_clarification(
    prompt: str,
    context: dict[str, Any] | None,
    answers: list[ClarifyAnswer],
) -> ClarifyResponse:
    merged = _apply_answers(context, answers)
    assumptions: list[str] = []
    questions: list[ClarifyQuestion] = []

    answered_ids = {a.id for a in answers}
    prompt_l = prompt.lower()

    for rq in _rule_candidates(prompt_l, merged):
        if rq.id in answered_ids:
            continue
        questions.append(
            ClarifyQuestion(
                id=rq.id,
                text=rq.text,
                why=rq.why,
                blocking=rq.blocking,
                options=rq.options,
            )
        )

    if answers:
        assumptions.extend(_assumptions_from_answers(answers))

    if questions:
        status = "need_clarification"
    else:
        status = "ready_to_generate"
        if not answers:
            assumptions.append(
                "Дополнительные уточнения не требуются; "
                "генерация выполняется по текущему prompt/context."
            )

    return ClarifyResponse(
        status=status,
        questions=questions,
        assumptions=assumptions,
        merged_context=merged,
    )


def _rule_candidates(prompt_l: str, context: dict[str, Any] | None) -> list[_RuleQuestion]:
    rules: list[_RuleQuestion] = []

    need_context_tokens = [
        "wf.vars",
        "wf.initvariables",
        "restbody",
        "parsedcsv",
        "idoc",
        "zcdf",
        "контекст",
        "из полученных данных",
    ]
    if any(t in prompt_l for t in need_context_tokens) and not context:
        rules.append(
            _RuleQuestion(
                id="q_context_json",
                text=(
                    "Пришлите минимальный JSON-контекст для задачи "
                    '(например `{"wf": {"vars": ...}}`), '
                    "иначе генерация может быть некорректной."
                ),
                why="В задаче есть ссылки на wf.vars / входные данные, но context отсутствует.",
                blocking=True,
                options=[],
            )
        )

    asks_json = ("json" in prompt_l) or ("формат" in prompt_l) or ("lowcode" in prompt_l)
    explicit_wrapper = ("lua{" in prompt_l) and ("}lua" in prompt_l)
    if asks_json and not explicit_wrapper:
        rules.append(
            _RuleQuestion(
                id="q_output_format",
                text="Какой выход нужен: `plain_lua` или `json_with_lua_wrapper` (`lua{...}lua`)?",
                why="Формат результата не определен однозначно.",
                blocking=False,
                options=["plain_lua", "json_with_lua_wrapper"],
            )
        )

    time_tokens = ["unix", "iso", "дата", "время", "time", "timezone", "таймзон"]
    tz_tokens = ["utc", "z", "gmt", "+00", "таймзон", "timezone"]
    if any(t in prompt_l for t in time_tokens) and not any(t in prompt_l for t in tz_tokens):
        rules.append(
            _RuleQuestion(
                id="q_timezone",
                text="Уточните таймзону для конвертации времени (по умолчанию использовать UTC?)",
                why="Для задач по времени результат зависит от таймзоны.",
                blocking=False,
                options=["UTC", "Local", "Custom offset"],
            )
        )

    return rules


def _apply_answers(
    context: dict[str, Any] | None, answers: list[ClarifyAnswer]
) -> dict[str, Any] | None:
    merged = copy.deepcopy(context) if context is not None else None

    for a in answers:
        if a.id == "q_context_json":
            parsed = _parse_context_json(a.text)
            if parsed is not None:
                merged = _deep_merge(merged or {}, parsed)
        elif a.id in {"q_output_format", "q_timezone"}:
            if merged is None:
                merged = {}
            meta = merged.setdefault("_clarify", {})
            if isinstance(meta, dict):
                if a.id == "q_output_format":
                    meta["output_format"] = a.text.strip()
                if a.id == "q_timezone":
                    meta["timezone"] = a.text.strip()
    return merged


def _assumptions_from_answers(answers: list[ClarifyAnswer]) -> list[str]:
    out: list[str] = []
    for a in answers:
        text = a.text.strip()
        if not text:
            continue
        if a.id == "q_context_json":
            out.append("Пользователь предоставил/уточнил JSON-контекст для генерации.")
        elif a.id == "q_output_format":
            out.append(f"Формат ответа зафиксирован: {text}.")
        elif a.id == "q_timezone":
            out.append(f"Таймзона зафиксирована: {text}.")
    return out


def _parse_context_json(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out
