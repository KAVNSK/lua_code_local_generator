import pytest

pytest.importorskip("pydantic_settings")

from app.pipeline import (
    _confidence_gate_report,
    _semantic_validation_enabled_for_request,
    _validation_report,
)


def test_validation_report_classifies_error_types():
    report = _validation_report(
        [
            "syntax: unexpected symbol",
            "static: forbidden pattern",
            "sandbox: runtime error",
            "heuristic:missing",
            "repeat: same code",
        ]
    )
    assert [x["error_type"] for x in report] == [
        "syntax",
        "static",
        "sandbox",
        "heuristic",
        "repeat",
    ]


def test_confidence_gate_report_contains_repeated_patterns():
    history = [
        {"attempt": 0, "phase": "initial", "code_fingerprint": "a", "errors": ["syntax:e1"]},
        {"attempt": 1, "phase": "repair_1", "code_fingerprint": "b", "errors": ["syntax:e1"]},
    ]
    report = _confidence_gate_report(
        task_prompt="task",
        context=None,
        final_code="return 1",
        final_errors=["syntax:e1"],
        max_repair_attempts=2,
        history=history,
    )
    assert report["status"] == "low_confidence"
    assert report["confidence_gate_triggered"] is True
    assert report["repeated_error_patterns"][0]["error"] == "syntax:e1"
    assert report["repeated_error_patterns"][0]["count"] == 2


def test_semantic_validation_can_be_enabled_per_request_context():
    assert (
        _semantic_validation_enabled_for_request(
            settings_enabled=False,
            context={"__semantic_validation": {"expected_type": "array"}},
            context_key="__semantic_validation",
        )
        is True
    )
    assert (
        _semantic_validation_enabled_for_request(
            settings_enabled=False,
            context={"wf": {"vars": {"x": 1}}},
            context_key="__semantic_validation",
        )
        is False
    )
    assert (
        _semantic_validation_enabled_for_request(
            settings_enabled=True,
            context=None,
            context_key="__semantic_validation",
        )
        is True
    )
