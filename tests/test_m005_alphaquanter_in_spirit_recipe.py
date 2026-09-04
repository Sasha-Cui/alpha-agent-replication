from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M005_alphaquanter"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m005_recipe_pins_paper_and_released_reward_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M005"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("reward_conformance_path", "reward_conformance_sha256"),
        ("dataset_inventory_path", "dataset_inventory_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m005_recipe_freezes_selective_tools_and_causal_multi_horizon_training():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert set(recipe["tool_definitions"]) == {
        "market_technical",
        "fundamental",
        "sentiment_proxy",
        "macro_proxy",
    }
    policy = recipe["chronological_policy"]
    assert policy["monthly_reward_horizons"] == [1, 3, 6]
    assert policy["exponential_decay_eta"] == 0.8
    assert policy["reward_information_gap_months"] == 6
    assert policy["training_window_months"] == 60
    assert policy["maximum_selected_tools"] == 2
    assert policy["decision_threshold"] == 0.015
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m005_is_the_only_active_in_spirit_milestone():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    active = [row["milestone_id"] for row in ledger["milestones"] if row["status"] == "in_progress_in_spirit"]
    assert active == ["M005"]
