from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M065_factormad"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m065_recipe_freezes_debate_pipeline_before_result():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["milestone_id"] == "M065"
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["paper_source"]["attributable_code_factor_library_or_result_release_found"] is False
    assert recipe["factor_grammar"]["candidate_count"] == 210
    debate = recipe["debate_policy"]
    assert debate["existing_seed_probability"] == 0.5
    assert debate["debate_rounds"] == 10
    assert debate["maximum_correction_iterations"] == 1
    assert debate["target_accepted_factors"] == 100
    assert debate["predictive_metric_threshold"] == 0.002
    assert debate["maximum_rankic_correlation"] == 0.98
    model = recipe["prediction_model"]
    assert model["selected_headline_model"] == "linear_regression"
    assert model["input_factors"] == 100
    assert model["common_or_post_training_returns_used_for_factor_or_model_selection"] is False


def test_m065_recipe_pins_publisher_and_audit_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert (
        recipe["paper_source"]["official_pdf_sha256"]
        == "5fb011bceea232aa52cd36ee0dc14a3238d3e5f5311bfc25af742127298afeab"
    )
    for key, path_key in (
        ("audit_manifest", "audit_manifest_path"),
        ("source_provenance", "source_provenance_path"),
        ("method_specification", "method_specification_path"),
        ("component_execution", "component_execution_path"),
        ("release_search", "release_search_path"),
    ):
        assert digest(ROOT / recipe["strict_evidence"][path_key]) == recipe["strict_evidence"][f"{key}_sha256"]


def test_m065_recipe_discloses_distance_and_ledger_state():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["preserved_elements"] and recipe["approximated_elements"] and recipe["invented_elements"]
    assert recipe["anti_leakage"]["m065_common_result_seen_before_recipe_freeze"] is False
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M065"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
