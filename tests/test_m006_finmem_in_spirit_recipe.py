from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M006_finmem"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m006_recipe_pins_primary_and_historical_action_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M006"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("action_metric_path", "action_metric_sha256"),
        ("configuration_path", "configuration_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m006_recipe_freezes_three_layer_top_five_memory_and_character():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["memory_layers"]) == ["shallow", "intermediate", "deep"]
    assert [recipe["memory_layers"][name]["daily_decay_alpha"] for name in recipe["memory_layers"]] == [0.9, 0.967, 0.988]
    for layer in recipe["memory_layers"].values():
        assert sum(layer["retrieval_weights"].values()) == 1.0
    policy = recipe["chronological_policy"]
    assert policy["memory_horizon_months"] == 60
    assert policy["top_k_per_layer"] == 5
    assert policy["trading_days_per_month"] == 21
    assert policy["risk_adjustment_magnitude"] == 0.25
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m006_recipe_remains_pinned_after_the_ledger_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    milestone = next(row for row in ledger["milestones"] if row["milestone_id"] == "M006")
    assert milestone["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    if milestone["status"] == "completed_in_spirit":
        manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
        assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
