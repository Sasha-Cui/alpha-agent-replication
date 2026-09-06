from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M063_fin_analyst"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m063_recipe_freezes_eight_specialist_meta_agent_before_result():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["milestone_id"] == "M063"
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["paper_source"]["attributable_pre_live_implementation_found"] is True
    assert recipe["paper_source"]["causal_cross_sectional_policy_or_historical_model_state_found"] is False
    assert list(recipe["specialists"]) == [
        "news",
        "event",
        "quarterly",
        "annual",
        "fundamentals",
        "analyst",
        "technical",
        "social",
    ]
    policy = recipe["meta_agent_policy"]
    assert sum(policy["specialist_weights"].values()) == 1.0
    assert policy["news_override_confidence"] == 0.70
    assert policy["majority_specialists"] == 5
    assert policy["paper_or_common_future_returns_used_for_aggregation"] is False


def test_m063_recipe_pins_primary_native_and_organizer_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["paper_source"]["pdf_sha256"] == "8b03c2ae99aff919be41757bb465fb958d69a3b0ccc4ceb35aef1706e2e46a79"
    assert (
        recipe["paper_source"]["source_tex_sha256"]
        == "fcd407f9bb6ac4392575c46415094f20e2019badce97363e464d2239530e91c5"
    )
    for key, path_key in (
        ("audit_manifest", "audit_manifest_path"),
        ("source_provenance", "source_provenance_path"),
        ("method_specification", "method_specification_path"),
        ("prompt_correspondence", "prompt_correspondence_path"),
        ("native_execution", "native_execution_path"),
        ("organizer_scorer", "organizer_scorer_path"),
    ):
        assert digest(ROOT / recipe["strict_evidence"][path_key]) == recipe["strict_evidence"][f"{key}_sha256"]


def test_m063_recipe_discloses_distance_and_ledger_state():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["preserved_elements"] and recipe["approximated_elements"] and recipe["invented_elements"]
    assert recipe["anti_leakage"]["m063_common_result_seen_before_recipe_freeze"] is False
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M063"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
