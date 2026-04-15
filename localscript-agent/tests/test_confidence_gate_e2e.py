import pytest
from fastapi.testclient import TestClient

pytest.importorskip("pydantic_settings")

from app.main import app


def test_generate_success_without_confidence_gate(monkeypatch):
    import app.pipeline as pipeline_module

    async def _fake_chat_completion(client, settings, messages, **kwargs):
        _ = (client, settings, messages, kwargs)
        return "return 1"

    def _fake_validate_code(code, luac_path="luac"):
        _ = (code, luac_path)
        return True, []

    monkeypatch.setattr(pipeline_module, "chat_completion", _fake_chat_completion)
    monkeypatch.setattr(pipeline_module, "validate_code", _fake_validate_code)

    with TestClient(app) as client:
        response = client.post("/generate", json={"prompt": "Верни 1"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"].strip() == "return 1"
    assert body["confidence_gate_triggered"] is False
    assert body["repair_report"] is None


def test_generate_failure_triggers_confidence_gate(monkeypatch):
    import app.pipeline as pipeline_module
    from app.config import settings

    async def _fake_chat_completion(client, settings_obj, messages, **kwargs):
        _ = (client, settings_obj, messages, kwargs)
        return "return ???"

    def _fake_validate_code(code, luac_path="luac"):
        _ = (code, luac_path)
        return False, ["syntax: unexpected symbol near '?'"]

    monkeypatch.setattr(pipeline_module, "chat_completion", _fake_chat_completion)
    monkeypatch.setattr(pipeline_module, "validate_code", _fake_validate_code)
    monkeypatch.setattr(settings, "max_repair_attempts", 1, raising=False)

    with TestClient(app) as client:
        response = client.post("/generate", json={"prompt": "Верни 1"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["code"], str) and body["code"]
    assert body["confidence_gate_triggered"] is True
    report = body["repair_report"]
    assert isinstance(report, dict)
    assert report.get("status") == "low_confidence"
    assert report.get("confidence_gate_triggered") is True
    assert report.get("attempts_made") == 2  # initial + 1 repair attempt
    assert isinstance(report.get("final_errors"), list) and report["final_errors"]
