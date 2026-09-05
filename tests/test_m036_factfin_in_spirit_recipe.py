from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M036_factfin"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m036_recipe_pins_paper_and_no_source_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M036"
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_audit_path", "method_audit_sha256"),
        ("prompt_inventory_path", "prompt_inventory_sha256"),
        ("native_execution_path", "native_execution_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    provenance = json.loads((ROOT / evidence["source_provenance_path"]).read_text())
    assert provenance["official_pdf_sha256"] == recipe["paper_source"]["pdf_sha256"]
    assert provenance["arxiv_source_sha256"] == recipe["paper_source"]["source_sha256"]


def test_m036_recipe_freezes_code_mcts_and_counterfactual_selection():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["rag_state"]) == ["price", "factors", "factorized_news"]
    grammar = recipe["strategy_code_grammar"]
    assert grammar["actions"] == ["sell", "hold", "buy"]
    assert grammar["weight_mutation_step"] == 0.25
    assert grammar["hold_band"] == [-0.2, 0.2]
    policy = recipe["search_and_counterfactual_policy"]
    assert policy["mcts_depth"] == 10
    assert policy["mcts_ucb_exploration_constant"] == 0.5
    assert policy["mcts_iterations"] == 100
    assert policy["counterfactual_finalists"] == 10
    assert policy["counterfactual_scenarios"] == 50
    assert policy["search_training_months"] == 96
    assert policy["search_validation_months"] == 24
    assert policy["final_common_returns_used_for_search_or_selection"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 8


def test_m036_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M036"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
