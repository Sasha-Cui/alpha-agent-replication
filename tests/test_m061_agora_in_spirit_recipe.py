from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M061_agora"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m061_recipe_freezes_sealed_joint_search_before_result():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["milestone_id"] == "M061"
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["paper_source"]["attributable_code_registry_alpha_pool_checkpoint_or_actions_found"] is False
    grammar = recipe["alpha_grammar"]
    assert grammar["candidate_count"] == 145
    assert grammar["target_unique_alphas"] == 94
    assert grammar["final_top_alpha_count"] == 30
    society = recipe["sealed_society"]
    assert len(society["roles"]) == 5 and society["client_count"] == 9
    assert len(society["typed_channels"]) == 3 and len(society["skill_stores"]) == 8
    assert society["metric_proposal_rounds"] == {
        "monotonicity_score_v1": 21,
        "excess_drawdown_penalty_v1": 50,
    }
    assert recipe["search_policy"]["outer_rounds"] == 100
    assert recipe["search_policy"]["common_or_post_training_returns_used_for_search_or_selection"] is False


def test_m061_recipe_pins_primary_and_audit_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["paper_source"]["pdf_sha256"] == "8e340c26444145bcb00c0f8761b9adc4404c757ca741ffc9c3281ef88833a40a"
    assert recipe["paper_source"]["source_sha256"] == "5e77d5f98b8e60a0d6b425a318e314274480e4a46f03eab10d5be30c05c182e1"
    for key, path_key in (
        ("audit_manifest", "audit_manifest_path"),
        ("source_provenance", "source_provenance_path"),
        ("method_specification", "method_specification_path"),
        ("metric_execution", "metric_execution_path"),
        ("release_search", "release_search_path"),
    ):
        assert digest(ROOT / recipe["strict_evidence"][path_key]) == recipe["strict_evidence"][f"{key}_sha256"]


def test_m061_recipe_discloses_distance_and_ledger_state():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["preserved_elements"] and recipe["approximated_elements"] and recipe["invented_elements"]
    assert recipe["anti_leakage"]["m061_common_result_seen_before_recipe_freeze"] is False
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M061"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
