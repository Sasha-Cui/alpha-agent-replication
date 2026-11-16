"""Control pools preserve chronology and the exact LLM-pool financial algorithm."""

from pathlib import Path
import hashlib
import pytest
from alpha_evolve.fidelity_efs_grammar_pool_v2 import merge_grammar_discoveries, require_same_financial_block


def factor(date, origin="programmatic_grammar"):
    code = "def f(prices):\n    return prices[-1]\n"
    return {hashlib.sha256(code.encode()).hexdigest(): {"code": code, "origin": origin, "created_index": date}}


def test_earliest_actual_control_discovery_and_all_lineage_retained():
    merged = merge_grammar_discoveries({"101": factor(9), "102": factor(6), "103": factor(12)})
    value = next(iter(merged.values()))
    assert value["created_index"] == 6
    assert len(value["discoveries"]) == 3


def test_no_relabelled_llm_or_undated_control_factor():
    for row in [factor(-1), factor(2, "llm_generated")]:
        with pytest.raises(ValueError):
            merge_grammar_discoveries({"101": row})


def test_actual_control_and_llm_financial_blocks_match_and_mutation_fails():
    root = Path(__file__).parents[1]
    original = (root / "scripts/evaluate_efs_pool_v2.py").read_text()
    control = (root / "scripts/evaluate_efs_grammar_pool_v2.py").read_text()
    assert require_same_financial_block(original, control)
    changed = control.replace('recipe["portfolio_assets"]', 'recipe["selected_factors"]')
    assert changed != control
    with pytest.raises(ValueError, match="computations differ"):
        require_same_financial_block(original, changed)
