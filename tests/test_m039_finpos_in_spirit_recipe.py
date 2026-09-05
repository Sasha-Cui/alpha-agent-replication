from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M039_finpos"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m039_recipe_pins_v2_paper_components_and_no_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M039"
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_audit_path", "method_audit_sha256"),
        ("component_execution_path", "component_execution_sha256"),
        ("prompt_contract_path", "prompt_contract_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    provenance = json.loads((ROOT / evidence["source_provenance_path"]).read_text())
    assert provenance["pinned_input_sha256"]["primary/official-v2.pdf"] == recipe["paper_source"]["pdf_sha256"]
    assert provenance["pinned_input_sha256"]["primary/source-v2.tar"] == recipe["paper_source"]["source_sha256"]


def test_m039_recipe_freezes_hierarchical_memory_dual_decision_position_and_cvar():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["hierarchical_signal_memory"]) == [
        "shallow_news",
        "middle_technical",
        "deep_fundamental",
    ]
    policy = recipe["position_policy"]
    assert policy["monthly_reward_horizons"] == [1, 3, 6]
    assert sum(policy["multi_timescale_weights"]) == 1.0
    assert policy["reward_label_purge_months"] == 6
    assert policy["reward_history_months"] == 60
    assert policy["direction_hold_threshold"] == 0.1
    assert policy["position_bounds"] == [-1.0, 1.0]
    assert policy["base_trade_quantity"] == 0.25
    assert policy["cvar_history_months"] == 20
    assert policy["cvar_tail_probability"] == 0.05
    assert policy["cvar_position_cap_bounds"] == [0.25, 1.0]
    assert "HOLD" in policy["missing_signal_rule"]
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 8


def test_m039_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M039"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
