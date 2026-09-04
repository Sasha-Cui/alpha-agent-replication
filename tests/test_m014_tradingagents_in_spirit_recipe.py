from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M014_tradingagents"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m014_recipe_pins_paper_native_graph_and_mechanism_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M014"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("native_component_path", "native_component_sha256"),
        ("mechanism_path", "mechanism_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m014_recipe_freezes_analysts_debates_risk_and_reflection():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["analysts"]) == ["market", "social", "news", "fundamental"]
    policy = recipe["debate_policy"]
    assert policy["reflection_window_months"] == 60
    assert policy["minimum_rankic_months"] == 24
    assert policy["softmax_temperature"] == 10.0
    assert policy["risk_multipliers"] == {
        "risk_seeking": 1.25,
        "neutral": 1.0,
        "conservative": 0.75,
    }
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m014_is_the_only_active_in_spirit_milestone():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    active = [row["milestone_id"] for row in ledger["milestones"] if row["status"] == "in_progress_in_spirit"]
    assert active == ["M014"]
