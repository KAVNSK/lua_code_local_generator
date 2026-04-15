from app.semantic import evaluate_semantic_rules


def test_semantic_rules_expected_stdout():
    errs = evaluate_semantic_rules("42", 42, {"expected_stdout": "42"})
    assert not errs


def test_semantic_rules_expected_stdout_mismatch():
    errs = evaluate_semantic_rules("41", 41, {"expected_stdout": "42"})
    assert any("expected_stdout_mismatch" in e for e in errs)


def test_semantic_rules_regex_and_forbid():
    errs = evaluate_semantic_rules(
        "value=abc",
        "value=abc",
        {"expected_stdout_regex": r"^value=\\d+$", "forbid_stdout_contains": ["abc"]},
    )
    assert any("expected_stdout_regex_mismatch" in e for e in errs)
    assert any("forbid_stdout_contains_match" in e for e in errs)


def test_semantic_rules_allowed_values_and_non_empty():
    errs = evaluate_semantic_rules(
        "",
        None,
        {"allowed_stdout_values": ["1", "2"], "require_non_empty_stdout": True},
    )
    assert any("stdout_empty_but_required" in e for e in errs)


def test_semantic_rules_expected_type_and_len_and_keys():
    value = [{"class": "A"}, {"class": "B"}]
    errs = evaluate_semantic_rules(
        "ignored",
        value,
        {"expected_type": "array", "expected_len": 2, "required_keys": ["class"]},
    )
    assert not errs


def test_semantic_rules_all_items_predicate_and_numeric_range():
    value = [{"score": 10}, {"score": 11}]
    errs = evaluate_semantic_rules(
        "ignored",
        value,
        {
            "all_items_predicate": "score >= 10",
            "numeric_range": {"path": "0.score", "min": 5, "max": 20},
        },
    )
    assert not errs


def test_semantic_rules_numeric_range_on_scalar():
    errs = evaluate_semantic_rules(
        "ignored",
        12,
        {"expected_type": "number", "numeric_range": {"min": 10, "max": 20}},
    )
    assert not errs
