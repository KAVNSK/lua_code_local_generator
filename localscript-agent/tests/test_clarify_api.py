import pytest
from fastapi.testclient import TestClient

pytest.importorskip("pydantic_settings")

from app.main import app


def test_generate_from_clarify_returns_questions_when_context_missing():
    client = TestClient(app)
    response = client.post(
        "/generate-from-clarify",
        json={
            "prompt": "Используй wf.vars.parsedCsv и отфильтруй Discount",
            "context": None,
            "answers": [],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "need_clarification"
    assert body["code"] is None
    assert any(q["id"] == "q_context_json" for q in body["questions"])


def test_generate_from_clarify_generates_after_answers(monkeypatch):
    from app import main as main_module

    async def _fake_generate_lua(
        client, settings, prompt, context=None, previous_code=None, feedback=None
    ):
        _ = (client, settings, prompt, previous_code, feedback)
        return ("return wf.vars.parsedCsv", ["ok"], None)

    monkeypatch.setattr(main_module, "generate_lua", _fake_generate_lua)
    main_module.app.state.http = object()
    client = TestClient(app)
    response = client.post(
        "/generate-from-clarify",
        json={
            "prompt": "Используй wf.vars.parsedCsv и отфильтруй Discount",
            "context": None,
            "answers": [
                {
                    "id": "q_context_json",
                    "text": '{"wf":{"vars":{"parsedCsv":[{"Discount":"10%"}]}}}',
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "generated"
    assert body["code"] == "return wf.vars.parsedCsv"
    assert body["merged_context"]["wf"]["vars"]["parsedCsv"][0]["Discount"] == "10%"
