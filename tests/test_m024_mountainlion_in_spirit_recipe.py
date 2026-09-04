from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M024_mountainlion"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m024_recipe_pins_paper_and_strict_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M024"
    assert digest(ROOT / recipe["paper_source"]["pdf_path"]) == recipe["paper_source"]["pdf_sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("mechanism_conformance_path", "mechanism_conformance_sha256"),
        ("formula_checks_path", "formula_checks_sha256"),
        ("source_execution_path", "source_execution_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]


def test_m024_recipe_freezes_four_agents_dual_tracks_and_adaptive_fusion():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["modalities"]) == [
        "technical",
        "market_dynamics",
        "fundamental_quality",
        "valuation_safety",
    ]
    assert list(recipe["four_specialized_agents"]) == [
        "A1_technical",
        "A2_market_dynamics",
        "A3_trading_recommendation",
        "A4_semantic_reflection",
    ]
    policy = recipe["dual_track_policy"]
    assert policy["ml_training_months"] == 60
    assert policy["fusion_history_months"] == 24
    assert policy["minimum_fusion_rankic_months"] == 18
    assert policy["ridge_lambda"] == 1.0
    assert policy["alpha_floor"] == 0.1
    assert policy["alpha_ceiling"] == 0.9
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 9
    assert len(recipe["approximated_elements"]) >= 6
    assert len(recipe["invented_elements"]) >= 7


def test_m024_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M024"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
