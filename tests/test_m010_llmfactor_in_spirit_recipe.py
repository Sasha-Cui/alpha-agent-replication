from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M010_llmfactor"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m010_recipe_pins_paper_prompts_and_method_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M010"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("prompt_path", "prompt_sha256"),
        ("method_path", "method_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m010_recipe_freezes_relation_five_factors_and_five_prices():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert len(recipe["relation_stage"]["peer_features"]) == 3
    assert len(recipe["relation_stage"]["peer_inputs"]) == 2
    assert len(recipe["factor_stage"]["candidates"]) == 8
    assert recipe["factor_stage"]["selected_count"] == 5
    assert recipe["prediction_stage"]["price_history"] == "current_and_four_lagged_monthly_total_returns"
    assert recipe["prediction_stage"]["training_window_months"] == 60
    assert recipe["prediction_stage"]["model"] == "rolling_ridge_binary_margin"
    assert recipe["chronological_policy"]["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m010_recipe_remains_pinned_after_the_ledger_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    milestone = next(row for row in ledger["milestones"] if row["milestone_id"] == "M010")
    assert milestone["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    if milestone["status"] == "completed_in_spirit":
        manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
        assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
