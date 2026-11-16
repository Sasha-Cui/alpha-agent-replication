import pytest
from alpha_evolve.finagent_schema_repair_v2 import canonical_reflection


def test_source_typo_value_is_preserved_and_raw_dictionary_is_untouched():
    raw = {
        "reasoning": {
            "short_term_reasoning": "short",
            "medium_term_reasoning": "medium",
            "long_term_reasonig": "Exact original long-term text",
        },
        "query": "original query",
    }
    result, event = canonical_reflection(raw)
    assert result["reasoning"]["long_term_reasoning"] == "Exact original long-term text"
    assert "long_term_reasonig" in raw["reasoning"]
    assert result["query"] == raw["query"]
    assert event["text_changed"] is False


def test_no_fuzzy_repair_or_overwriting_an_existing_expected_field():
    raw = {"reasoning": {"long_term_reasoning": "expected", "long_term_reasonig": "different"}}
    assert canonical_reflection(raw) == (raw, None)
    raw = {"reasoning": {"some_unknown_key": "text"}}
    assert canonical_reflection(raw) == (raw, None)
    with pytest.raises(ValueError):
        canonical_reflection({"reasoning": {"long_term_reasonig": {"not": "text"}}})
