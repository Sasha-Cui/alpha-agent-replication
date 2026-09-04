from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M009_finagent"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m009_recipe_pins_substantive_source_and_mechanism_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M009"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("mechanism_path", "mechanism_sha256"),
        ("strategy_inventory_path", "strategy_inventory_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m009_recipe_freezes_multimodal_memory_reflection_and_tools():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert set(recipe["modalities"]) == {"market_intelligence_proxy", "price_chart_proxy"}
    memory = recipe["diversified_memory"]
    assert memory["query_horizons_months"] == [1, 3, 6]
    assert memory["memory_window_months"] == 60
    assert memory["top_k_per_query"] == 5
    assert recipe["reflection"]["training_window_months"] == 60
    assert recipe["reflection"]["high_level_weight"] == 0.25
    assert len(recipe["augmented_tools"]["candidates"]) == 3
    assert recipe["augmented_tools"]["tool_weight"] == 0.25
    assert recipe["chronological_policy"]["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m009_recipe_remains_pinned_after_the_ledger_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    milestone = next(row for row in ledger["milestones"] if row["milestone_id"] == "M009")
    assert milestone["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    if milestone["status"] == "completed_in_spirit":
        manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
        assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
