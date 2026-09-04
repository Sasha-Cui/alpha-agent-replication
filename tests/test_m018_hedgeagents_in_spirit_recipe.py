from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M018_hedgeagents"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m018_recipe_pins_paper_profiles_and_method_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M018"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("profiles_path", "profiles_sha256"),
        ("method_path", "method_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m018_recipe_freezes_specialists_conference_cvar_and_trigger():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["specialists"]) == ["speculative", "equity", "defensive"]
    policy = recipe["conference_policy"]
    assert policy["history_months"] == 60
    assert policy["cvar_tail_probability"] == 0.05
    assert policy["experience_sharing_weight"] == 0.1
    assert policy["extreme_one_month_threshold"] == 0.05
    assert policy["extreme_three_month_threshold"] == 0.1
    assert policy["extreme_defensive_minimum_weight"] == 0.5
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m018_is_the_only_active_in_spirit_milestone():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    active = [row["milestone_id"] for row in ledger["milestones"] if row["status"] == "in_progress_in_spirit"]
    assert active == ["M018"]
