from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M060_metaps"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m060_recipe_freezes_v3_router_before_result():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["milestone_id"] == "M060"
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["paper_source"]["attributable_code_data_checkpoint_or_actions_found"] is False
    assert list(recipe["strategy_library"]) == [
        "news_impulse",
        "momentum_follow",
        "mean_revert_fade",
        "cross_asset_hedge",
        "risk_reset",
        "macro_rotation",
        "earnings_drift",
        "liquidity_rebate",
        "small_cap_breakout",
        "volatility_breakout",
    ]
    policy = recipe["supervision_policy"]
    assert policy["selected_view"] == "V3_balanced_competence"
    assert policy["router_training_months"] == 120
    assert policy["v2_horizons_months"] == [1, 3, 6]
    assert policy["v2_horizon_weights"] == [0.2, 0.3, 0.5]
    assert policy["candidate_budget"] == 10
    assert policy["final_common_or_current_forward_return_used_for_router_selection"] is False


def test_m060_recipe_pins_primary_and_audit_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["paper_source"]["pdf_sha256"] == "fd2ce88b351e9abfc0c96103f7927ee9f365231bfce8df492beb4054777148f6"
    assert recipe["paper_source"]["source_sha256"] == "c6e3378c0cccf455c2dc7fa11bccda70b4c279bb7e16c3901f99df0237b46780"
    for key, path_key in (
        ("audit_manifest", "audit_manifest_path"),
        ("source_provenance", "source_provenance_path"),
        ("method_specification", "method_specification_path"),
        ("component_execution", "component_execution_path"),
        ("release_search", "release_search_path"),
    ):
        assert digest(ROOT / recipe["strict_evidence"][path_key]) == recipe["strict_evidence"][f"{key}_sha256"]


def test_m060_recipe_discloses_distance_and_ledger_state():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["preserved_elements"] and recipe["approximated_elements"] and recipe["invented_elements"]
    assert recipe["anti_leakage"]["m060_common_result_seen_before_recipe_freeze"] is False
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M060"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
