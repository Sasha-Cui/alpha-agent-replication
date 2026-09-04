from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M011_fincon"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m011_recipe_pins_primary_and_gap_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M011"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("mechanism_path", "mechanism_sha256"),
        ("gaps_path", "gaps_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m011_recipe_freezes_hierarchy_beliefs_and_cvar():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["analysts"]) == ["market", "fundamental", "attention", "risk"]
    belief = recipe["belief_policy"]
    assert belief["procedural_memory_months"] == 60
    assert belief["minimum_rankic_months"] == 24
    assert belief["belief_learning_rate"] == 0.25
    risk = recipe["risk_control"]
    assert risk["return_history_months"] == 60
    assert risk["monthly_cvar_tail_probability"] == 0.05
    assert risk["cvar_penalty"] == 0.5
    assert recipe["chronological_policy"]["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m011_recipe_remains_pinned_after_the_ledger_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    milestone = next(row for row in ledger["milestones"] if row["milestone_id"] == "M011")
    assert milestone["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    if milestone["status"] == "completed_in_spirit":
        manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
        assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
