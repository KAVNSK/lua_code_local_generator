from __future__ import annotations

import hashlib

import httpx

from app.config import Settings
from app.extract import extract_lua
from app.ollama_client import chat_completion
from app.prompts import build_user_message, messages_for_chat, repair_user_message_structured
from app.semantic import semantic_validate
from app.validate import validate_code


async def generate_lua(
    client: httpx.AsyncClient,
    settings: Settings,
    prompt: str,
    context: dict | None = None,
    previous_code: str | None = None,
    feedback: str | None = None,
) -> tuple[str, list[str], dict | None]:
    """
    Full loop: build prompt -> Ollama -> extract -> validate -> optional repair.
    Returns (final_code, log_lines, repair_report_or_none).
    """
    log: list[str] = []
    seen_fingerprints: set[str] = set()
    history: list[dict] = []

    user_content = build_user_message(prompt, context, previous_code, feedback)
    messages = messages_for_chat(user_content, include_few_shot=True)
    raw = await chat_completion(client, settings, messages)
    code = extract_lua(raw)
    ok, errs = _validate_with_optional_semantic(code, settings=settings, context=context)
    first_fp = _code_fingerprint(code)
    seen_fingerprints.add(first_fp)
    if ok:
        log.append("validate: pass (initial)")
        return code, log, None

    history.append(
        {
            "attempt": 0,
            "phase": "initial",
            "code_fingerprint": first_fp,
            "errors": list(errs),
            "repeated_code": False,
        }
    )
    log.append(f"validate: fail initial: {'; '.join(errs)}")
    for i in range(settings.max_repair_attempts):
        repeated_code = _code_fingerprint(code) in seen_fingerprints and i > 0
        repair_errors = list(errs)
        if repeated_code:
            repair_errors.append("repeat: candidate code repeated a prior failing attempt")
        validation_report = _validation_report(repair_errors)

        repair_msg = repair_user_message_structured(
            task_prompt=prompt,
            broken_code=code,
            context=context,
            validation_report=validation_report,
            attempt_idx=i + 1,
            prior_failures=history,
            repeated_code=repeated_code,
        )
        repair_messages = messages_for_chat(repair_msg, include_few_shot=False)
        raw = await chat_completion(client, settings, repair_messages)
        code = extract_lua(raw)
        ok, errs = _validate_with_optional_semantic(code, settings=settings, context=context)
        fp = _code_fingerprint(code)
        history.append(
            {
                "attempt": i + 1,
                "phase": f"repair_{i + 1}",
                "code_fingerprint": fp,
                "errors": list(errs),
                "repeated_code": fp in seen_fingerprints,
            }
        )
        seen_fingerprints.add(fp)
        if ok:
            log.append(f"validate: pass after repair {i + 1}")
            return code, log, None
        log.append(f"validate: fail repair {i + 1}: {'; '.join(errs)}")

    log.append("validate: returning last attempt despite errors")
    report = _confidence_gate_report(
        task_prompt=prompt,
        context=context,
        final_code=code,
        final_errors=errs,
        max_repair_attempts=settings.max_repair_attempts,
        history=history,
    )
    return code, log, report


def _code_fingerprint(code: str) -> str:
    return hashlib.sha1(code.strip().encode("utf-8")).hexdigest()


def _validation_report(errors: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for msg in errors:
        etype = "other"
        if msg.startswith("syntax:"):
            etype = "syntax"
        elif msg.startswith("static:"):
            etype = "static"
        elif msg.startswith("sandbox:"):
            etype = "sandbox"
        elif msg.startswith("heuristic:"):
            etype = "heuristic"
        elif msg.startswith("semantic:"):
            etype = "semantic"
        elif msg.startswith("repeat:"):
            etype = "repeat"
        out.append({"error_type": etype, "message": msg})
    return out


def _validate_with_optional_semantic(
    code: str,
    *,
    settings: Settings,
    context: dict | None,
) -> tuple[bool, list[str]]:
    ok, errs = validate_code(code, luac_path=settings.luac_path)
    if not ok:
        return False, errs

    if not _semantic_validation_enabled_for_request(
        settings_enabled=settings.enable_semantic_validation,
        context=context,
        context_key=settings.semantic_context_key,
    ):
        return True, []

    sem_ok, sem_errs = semantic_validate(
        code,
        context=context,
        lua_bin=settings.lua_path,
        context_key=settings.semantic_context_key,
    )
    if not sem_ok:
        return False, sem_errs
    return True, []


def _semantic_validation_enabled_for_request(
    *,
    settings_enabled: bool,
    context: dict | None,
    context_key: str,
) -> bool:
    """
    Semantic validation is enabled if either:
    1) global setting is enabled, or
    2) request context includes a semantic spec object.
    """
    if settings_enabled:
        return True
    if not isinstance(context, dict):
        return False
    return isinstance(context.get(context_key), dict)


def _confidence_gate_report(
    *,
    task_prompt: str,
    context: dict | None,
    final_code: str,
    final_errors: list[str],
    max_repair_attempts: int,
    history: list[dict],
) -> dict:
    error_counts: dict[str, int] = {}
    for h in history:
        for e in h.get("errors", []):
            error_counts[e] = error_counts.get(e, 0) + 1
    repeated_error_patterns = [
        {"error": err, "count": count} for err, count in error_counts.items() if count > 1
    ]
    repeated_error_patterns.sort(key=lambda x: x["count"], reverse=True)

    recommendation = (
        "Нужны дополнительные уточнения по задаче или данным. "
        "Рекомендуется вызвать /clarify и затем повторить /generate."
    )
    if not context:
        recommendation = (
            "Контекст отсутствует или неполон. Передайте JSON-контекст (wf.vars/wf.initVariables) "
            "через /clarify answers или context в /generate."
        )

    return {
        "status": "low_confidence",
        "confidence_gate_triggered": True,
        "task_prompt": task_prompt,
        "context_present": context is not None,
        "attempts_made": len(history),
        "max_repair_attempts": max_repair_attempts,
        "final_errors": list(final_errors),
        "final_code_fingerprint": _code_fingerprint(final_code),
        "error_history": history,
        "repeated_error_patterns": repeated_error_patterns,
        "recommendation": recommendation,
    }
