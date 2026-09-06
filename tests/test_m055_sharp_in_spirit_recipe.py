from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M055_sharp"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m055_recipe_freezes_sharp_mechanism_before_result():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["milestone_id"] == "M055"
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["paper_source"]["attributable_implementation_or_actions_found"] is False
    assert [rule["id"] for rule in recipe["initial_rubric"]] == [
        "temporal_priced_in",
        "temporal_earnings_season",
        "news_analyst_rating",
        "news_generic_market",
        "macro_high_vix",
        "news_count_low",
    ]
    policy = recipe["evolution_policy"]
    assert (policy["training_months"], policy["validation_months"], policy["frozen_test_months"]) == (48, 12, 24)
    assert policy["evolution_rounds"] == 5
    assert policy["worst_training_months"] == 20
    assert policy["maximum_atomic_mutations_per_round"] == 3
    assert policy["validation_tolerance_total_return"] == 0.005
    assert policy["final_common_returns_used_for_rubric_choice"] is False


def test_m055_recipe_pins_primary_and_audit_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["paper_source"]["pdf_sha256"] == "8a53b6ed04d0de7852e4f5311db89df2c2f4457bd3cda23ae7fcf3baf4485394"
    assert recipe["paper_source"]["source_sha256"] == "4045a5dc53bbc2612b610e2a25e7a947ca3a5e8681af915b6528e3a0875ed56a"
    for key, path_key in (
        ("audit_manifest", "audit_manifest_path"),
        ("source_provenance", "source_provenance_path"),
        ("method_specification", "method_specification_path"),
        ("component_execution", "component_execution_path"),
        ("release_search", "release_search_path"),
    ):
        expected = recipe["strict_evidence"][f"{key}_sha256"]
        assert digest(ROOT / recipe["strict_evidence"][path_key]) == expected


def test_m055_recipe_discloses_distance_and_ledger_state():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["preserved_elements"] and recipe["approximated_elements"] and recipe["invented_elements"]
    assert recipe["anti_leakage"]["m055_common_result_seen_before_recipe_freeze"] is False
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M055"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
