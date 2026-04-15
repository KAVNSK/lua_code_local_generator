from __future__ import annotations

import json
from typing import Any

import httpx
import streamlit as st


def _load_json(text: str, field_name: str) -> tuple[Any | None, str | None]:
    text = text.strip()
    if not text:
        return None, None
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, f"{field_name}: invalid JSON ({e})"


def _post_json(
    base_url: str, endpoint: str, payload: dict
) -> tuple[dict[str, Any] | None, str | None]:
    url = base_url.rstrip("/") + endpoint
    try:
        with httpx.Client(timeout=180.0) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict):
                return None, "Response is not a JSON object."
            return data, None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def _get_json(base_url: str, endpoint: str) -> tuple[dict[str, Any] | None, str | None]:
    url = base_url.rstrip("/") + endpoint
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(url)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict):
                return None, "Response is not a JSON object."
            return data, None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def _init_state() -> None:
    st.session_state.setdefault("prompt", "")
    st.session_state.setdefault("context_json", "{}")
    st.session_state.setdefault("answers_json", "[]")
    st.session_state.setdefault("previous_code", "")
    st.session_state.setdefault("feedback", "")
    st.session_state.setdefault("last_response", None)
    st.session_state.setdefault("last_error", None)
    st.session_state.setdefault("last_request", None)
    st.session_state.setdefault("action_status", None)
    st.session_state.setdefault("enable_semantic_validation", False)
    st.session_state.setdefault(
        "semantic_rules_json",
        json.dumps(
            {
                "expected_type": "number",
                "numeric_range": {"min": 0, "max": 100},
                "require_non_empty_stdout": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


def main() -> None:
    st.set_page_config(page_title="LocalScript Demo UI", layout="wide")
    _init_state()

    st.title("LocalScript Agent Demo (Streamlit)")
    st.caption("Demo UI for /health, /clarify, /generate, /generate-from-clarify, /refine")

    with st.sidebar:
        base_url = st.text_input("API base URL", value="http://127.0.0.1:8080")
        if st.button("Check /health"):
            resp, err = _get_json(base_url, "/health")
            st.session_state["last_response"] = resp
            st.session_state["last_error"] = err
            st.session_state["last_request"] = {
                "method": "GET",
                "endpoint": "/health",
                "payload": None,
            }

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Input")
        with st.expander("Field guide: what each input means", expanded=False):
            st.markdown(
                "- `Prompt`: what Lua code should do.\n"
                "- `Context JSON`: input data/environment (`wf.vars`, params).\n"
                "- `Answers JSON`: answers for `/clarify` questions.\n"
                "- `Semantic rules JSON`: semantic checks for sandbox result.\n"
                "- `Previous code`: prior generation for iterative improvement.\n"
                "- `Feedback`: what to fix/change in previous code.\n"
                "- `API base URL`: backend address (default `http://127.0.0.1:8080`)."
            )
        st.session_state["prompt"] = st.text_area(
            "Prompt",
            value=st.session_state["prompt"],
            height=120,
            help=(
                "Natural-language task for Lua generation. "
                "Describe business logic, inputs, and expected output."
            ),
        )
        st.session_state["context_json"] = st.text_area(
            "Context JSON",
            value=st.session_state["context_json"],
            height=180,
            help=(
                'Input data/environment for code execution. '
                'For example: {"wf":{"vars":{"x":1}}}'
            ),
        )
        st.session_state["answers_json"] = st.text_area(
            "Answers JSON (for /clarify or /generate-from-clarify)",
            value=st.session_state["answers_json"],
            height=140,
            help=(
                "Answers to clarification questions returned by /clarify. "
                'Example: [{"id":"q_context_json","text":"{...json...}"}]'
            ),
        )
        st.session_state["enable_semantic_validation"] = st.checkbox(
            "Enable semantic validation for this request",
            value=st.session_state["enable_semantic_validation"],
            help=(
                "When enabled, UI injects '__semantic_validation' into context, "
                "and backend runs semantic validation for this request."
            ),
        )
        st.session_state["semantic_rules_json"] = st.text_area(
            "Semantic rules JSON",
            value=st.session_state["semantic_rules_json"],
            height=170,
            help=(
                "Used only when semantic validation checkbox is enabled. "
                "Rules are merged into context as '__semantic_validation'."
            ),
        )
        st.session_state["previous_code"] = st.text_area(
            "Previous code (for /refine or iterative /generate)",
            value=st.session_state["previous_code"],
            height=140,
            help="Paste previous Lua code to refine or continue iterating.",
        )
        st.session_state["feedback"] = st.text_area(
            "Feedback (for /refine or iterative /generate)",
            value=st.session_state["feedback"],
            height=110,
            help="Tell what is wrong and what should be improved.",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            do_clarify = st.button("POST /clarify", use_container_width=True)
            do_generate = st.button("POST /generate", use_container_width=True)
        with c2:
            do_gen_clarify = st.button("POST /generate-from-clarify", use_container_width=True)
            do_refine = st.button("POST /refine", use_container_width=True)
        with c3:
            use_merged = st.button("Use merged_context as context", use_container_width=True)
            use_code = st.button("Use code as previous_code", use_container_width=True)

    context, context_err = _load_json(st.session_state["context_json"], "context")
    answers, answers_err = _load_json(st.session_state["answers_json"], "answers")
    semantic_rules, semantic_rules_err = _load_json(
        st.session_state["semantic_rules_json"], "semantic_rules"
    )
    if context_err:
        st.warning(context_err)
    if answers_err:
        st.warning(answers_err)
    if semantic_rules_err:
        st.warning(semantic_rules_err)
    context_type_err = None
    if context is not None and not isinstance(context, dict):
        context_type_err = "context: JSON must be an object or null."
        st.warning(context_type_err)
    answers_type_err = None
    if answers is not None and not isinstance(answers, list):
        st.warning("answers: JSON must be an array.")
        answers_type_err = "answers: JSON must be an array."
        answers = None
    semantic_type_err = None
    if semantic_rules is not None and not isinstance(semantic_rules, dict):
        st.warning("semantic_rules: JSON must be an object.")
        semantic_type_err = "semantic_rules: JSON must be an object."
        semantic_rules = None

    context_for_payload = context
    if st.session_state["enable_semantic_validation"]:
        if context_for_payload is None:
            context_for_payload = {}
        if isinstance(context_for_payload, dict):
            context_for_payload = dict(context_for_payload)
            if semantic_rules is not None:
                context_for_payload["__semantic_validation"] = semantic_rules
        else:
            st.warning("context must be an object when semantic validation is enabled.")

    prompt_ok = bool(st.session_state["prompt"].strip())
    previous_code_ok = bool(st.session_state["previous_code"].strip())
    feedback_ok = bool(st.session_state["feedback"].strip())

    common_context_ok = not context_err and not context_type_err
    common_answers_ok = not answers_err and not answers_type_err and answers is not None
    common_semantic_ok = not semantic_rules_err and not semantic_type_err

    readiness = {
        "/clarify": {
            "required": ["prompt", "context JSON (object|null)", "answers JSON (array)"],
            "blockers": [
                *([] if prompt_ok else ["prompt is empty"]),
                *([] if common_context_ok else ["context JSON is invalid"]),
                *([] if common_answers_ok else ["answers JSON must be a valid array"]),
                *([] if common_semantic_ok else ["semantic rules JSON is invalid"]),
            ],
        },
        "/generate": {
            "required": ["prompt", "context JSON (object|null)"],
            "blockers": [
                *([] if prompt_ok else ["prompt is empty"]),
                *([] if common_context_ok else ["context JSON is invalid"]),
                *([] if common_semantic_ok else ["semantic rules JSON is invalid"]),
            ],
        },
        "/generate-from-clarify": {
            "required": ["prompt", "context JSON (object|null)", "answers JSON (array)"],
            "blockers": [
                *([] if prompt_ok else ["prompt is empty"]),
                *([] if common_context_ok else ["context JSON is invalid"]),
                *([] if common_answers_ok else ["answers JSON must be a valid array"]),
                *([] if common_semantic_ok else ["semantic rules JSON is invalid"]),
            ],
        },
        "/refine": {
            "required": [
                "prompt",
                "context JSON (object|null)",
                "previous_code",
                "feedback",
            ],
            "blockers": [
                *([] if prompt_ok else ["prompt is empty"]),
                *([] if common_context_ok else ["context JSON is invalid"]),
                *([] if previous_code_ok else ["previous_code is empty"]),
                *([] if feedback_ok else ["feedback is empty"]),
                *([] if common_semantic_ok else ["semantic rules JSON is invalid"]),
            ],
        },
    }

    st.markdown("### Action readiness")
    for endpoint, meta in readiness.items():
        blockers = meta["blockers"]
        icon = "✅" if not blockers else "⛔"
        st.markdown(f"**{icon} {endpoint}**")
        st.caption("Required: " + ", ".join(meta["required"]))
        if blockers:
            st.caption("Blocked by: " + "; ".join(blockers))
        else:
            st.caption("Ready to send.")

    def run_post(endpoint: str, payload: dict) -> None:
        st.session_state["last_request"] = {
            "method": "POST",
            "endpoint": endpoint,
            "payload": payload,
        }
        resp, err = _post_json(base_url, endpoint, payload)
        st.session_state["last_response"] = resp
        st.session_state["last_error"] = err
        if err:
            st.session_state["action_status"] = {
                "kind": "error",
                "endpoint": endpoint,
                "message": err,
            }
        else:
            st.session_state["action_status"] = {
                "kind": "success",
                "endpoint": endpoint,
                "message": "Request sent and response received.",
            }

    if do_clarify:
        blockers = readiness["/clarify"]["blockers"]
        if blockers:
            st.session_state["action_status"] = {
                "kind": "blocked",
                "endpoint": "/clarify",
                "message": "; ".join(blockers),
            }
        else:
            run_post(
                "/clarify",
                {
                    "prompt": st.session_state["prompt"],
                    "context": context_for_payload,
                    "answers": answers,
                },
            )

    if do_generate:
        blockers = readiness["/generate"]["blockers"]
        if blockers:
            st.session_state["action_status"] = {
                "kind": "blocked",
                "endpoint": "/generate",
                "message": "; ".join(blockers),
            }
        else:
            payload: dict[str, Any] = {
                "prompt": st.session_state["prompt"],
                "context": context_for_payload,
            }
            if st.session_state["previous_code"].strip():
                payload["previous_code"] = st.session_state["previous_code"]
            if st.session_state["feedback"].strip():
                payload["feedback"] = st.session_state["feedback"]
            run_post("/generate", payload)

    if do_gen_clarify:
        blockers = readiness["/generate-from-clarify"]["blockers"]
        if blockers:
            st.session_state["action_status"] = {
                "kind": "blocked",
                "endpoint": "/generate-from-clarify",
                "message": "; ".join(blockers),
            }
        else:
            payload = {
                "prompt": st.session_state["prompt"],
                "context": context_for_payload,
                "answers": answers,
            }
            if st.session_state["previous_code"].strip():
                payload["previous_code"] = st.session_state["previous_code"]
            if st.session_state["feedback"].strip():
                payload["feedback"] = st.session_state["feedback"]
            run_post("/generate-from-clarify", payload)

    if do_refine:
        blockers = readiness["/refine"]["blockers"]
        if blockers:
            st.session_state["action_status"] = {
                "kind": "blocked",
                "endpoint": "/refine",
                "message": "; ".join(blockers),
            }
        else:
            run_post(
                "/refine",
                {
                    "prompt": st.session_state["prompt"],
                    "context": context_for_payload,
                    "previous_code": st.session_state["previous_code"],
                    "feedback": st.session_state["feedback"],
                },
            )

    if use_merged and isinstance(st.session_state.get("last_response"), dict):
        merged = st.session_state["last_response"].get("merged_context")
        if merged is not None:
            st.session_state["context_json"] = json.dumps(merged, ensure_ascii=False, indent=2)
            st.rerun()

    if use_code and isinstance(st.session_state.get("last_response"), dict):
        code = st.session_state["last_response"].get("code")
        if isinstance(code, str):
            st.session_state["previous_code"] = code
            st.rerun()

    with col_right:
        st.subheader("Last request / response")
        action_status = st.session_state.get("action_status")
        if isinstance(action_status, dict):
            kind = action_status.get("kind")
            endpoint = action_status.get("endpoint")
            message = action_status.get("message")
            text = f"{endpoint}: {message}" if endpoint else str(message)
            if kind == "success":
                st.success(text)
            elif kind == "blocked":
                st.warning(text)
            elif kind == "error":
                st.error(text)
        if st.session_state["last_request"] is not None:
            st.markdown("**Request**")
            st.json(st.session_state["last_request"], expanded=False)
        if st.session_state["last_error"]:
            st.error(st.session_state["last_error"])
        if st.session_state["last_response"] is not None:
            st.markdown("**Response**")
            st.json(st.session_state["last_response"], expanded=True)
            code = st.session_state["last_response"].get("code")
            if isinstance(code, str):
                st.markdown("**Code**")
                st.code(code, language="lua")

    st.divider()
    st.caption(
        "Tip: start with /clarify, then Use merged_context, "
        "then /generate or /generate-from-clarify."
    )


if __name__ == "__main__":
    main()
