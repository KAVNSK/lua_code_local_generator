from app.clarify import build_clarification
from app.models_io import ClarifyAnswer


def test_clarify_requests_context_when_missing():
    resp = build_clarification(
        prompt="Используй wf.vars.parsedCsv и отфильтруй Discount.",
        context=None,
        answers=[],
    )
    assert resp.status == "need_clarification"
    assert any(q.id == "q_context_json" and q.blocking for q in resp.questions)


def test_clarify_merges_context_from_answers():
    resp = build_clarification(
        prompt="Используй wf.vars.parsedCsv и отфильтруй Discount.",
        context=None,
        answers=[
            ClarifyAnswer(
                id="q_context_json", text='{"wf":{"vars":{"parsedCsv":[{"Discount":"10%"}]}}}'
            )
        ],
    )
    assert resp.status == "ready_to_generate"
    assert resp.merged_context is not None
    assert resp.merged_context["wf"]["vars"]["parsedCsv"][0]["Discount"] == "10%"


def test_clarify_saves_non_blocking_preferences():
    resp = build_clarification(
        prompt="Конвертируй время в unix формат",
        context={"wf": {"initVariables": {"recallTime": "2023-10-15T15:30:00+00:00"}}},
        answers=[ClarifyAnswer(id="q_timezone", text="UTC")],
    )
    assert resp.merged_context is not None
    assert resp.merged_context["_clarify"]["timezone"] == "UTC"
