from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M032_trading_r1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m032_recipe_pins_paper_and_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M032"
    assert digest(ROOT / recipe["paper_source"]["pdf_path"]) == recipe["paper_source"]["pdf_sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("native_execution_path", "native_execution_sha256"),
        ("spec_diagnostics_path", "spec_diagnostics_sha256"),
        ("mechanism_conformance_path", "mechanism_conformance_sha256"),
        ("release_inventory_path", "release_inventory_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]


def test_m032_recipe_freezes_stages_actions_reward_and_chronology():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    groups = recipe["reasoning_stages"]["structured_thesis"]
    assert list(groups) == ["technical", "fundamental", "sentiment"]
    actions = recipe["five_actions"]
    assert actions["names"] == ["STRONG SELL", "SELL", "HOLD", "BUY", "STRONG BUY"]
    assert actions["score_values"] == [-1.0, -0.5, 0.0, 0.5, 1.0]
    assert actions["truth_quantiles"] == [0.03, 0.15, 0.53, 0.85]
    assert len(actions["decision_reward_matrix_rows_prediction_columns_truth"]) == 5
    assert all(len(row) == 5 for row in actions["decision_reward_matrix_rows_prediction_columns_truth"])
    policy = recipe["chronological_policy"]
    assert policy["monthly_label_horizons"] == [1, 3, 6]
    assert policy["multi_horizon_weights"] == [0.3, 0.5, 0.2]
    assert policy["volatility_lookback_months"] == 20
    assert policy["label_purge_months"] == 6
    assert policy["policy_training_months"] == 60
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 6
    assert len(recipe["invented_elements"]) >= 7


def test_m032_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M032"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
