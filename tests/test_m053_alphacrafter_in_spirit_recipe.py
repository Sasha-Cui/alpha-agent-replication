from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M053_alphacrafter"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m053_recipe_pins_paper_and_attributable_repository():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["milestone_id"] == "M053"
    assert recipe["paper_source"]["native_components_executable"] is True
    assert recipe["paper_source"]["paper_factor_or_action_artifacts_found"] is False
    evidence = recipe["strict_evidence"]
    for p, h in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("release_execution_audit_path", "release_execution_audit_sha256"),
        ("registered_model_override_execution_path", "registered_model_override_execution_sha256"),
        ("method_specification_path", "method_specification_sha256"),
    ):
        assert digest(ROOT / evidence[p]) == evidence[h]


def test_m053_recipe_freezes_three_stage_workflow():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["miner_clusters"]) == ["technical_miner", "fundamental_miner", "risk_reversal_miner"]
    assert all(len(items) == 4 for items in recipe["miner_clusters"].values())
    policy = recipe["workflow_policy"]
    assert policy["candidate_operations"] == ["identity", "pair_mean", "pair_product"]
    assert policy["total_candidate_count"] == 48
    assert policy["validation_horizons_months"] == [1, 3, 6]
    assert policy["reward_purge_months"] == 6
    assert policy["screener_suitability_months"] == 10
    assert policy["maximum_rankic_similarity"] == 0.80
    assert policy["selected_factor_count"] == 5
    assert policy["trader_trials"] == 3
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 13
    assert len(recipe["approximated_elements"]) >= 8
    assert len(recipe["invented_elements"]) >= 8


def test_m053_is_active_when_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M053"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    assert sum(ledger["progress_summary"].values()) == 69
