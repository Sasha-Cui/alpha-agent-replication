from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M048_alphalogics"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m048_recipe_pins_paper_source_and_unreleased_system_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M048"
    assert recipe["paper_source"]["attributable_implementation_or_factor_pool_found"] is False
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_specification_path", "method_specification_sha256"),
        ("dsl_operation_ledger_path", "dsl_operation_ledger_sha256"),
        ("algorithm_conformance_path", "algorithm_conformance_sha256"),
        ("prompt_template_ledger_path", "prompt_template_ledger_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    audit = json.loads((ROOT / evidence["audit_manifest_path"]).read_text())
    assert audit["official_pages_visually_checked"] == 19
    assert audit["attributable_alphalogics_code_recovered"] is False
    assert audit["native_numeric_table_units_regenerated"] == 0


def test_m048_recipe_freezes_logic_compiler_inner_and_outer_loops():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    logics = recipe["initial_market_logic_library"]
    assert len(logics) == 6
    assert all(len(specifications) == 4 for specifications in logics.values())
    assert all(item["sign"] in {-1, 1} for specifications in logics.values() for item in specifications)
    dsl = recipe["compiled_factor_dsl"]
    assert dsl["allowed_operations"] == [
        "identity",
        "pair_mean",
        "pair_product",
        "triple_mean",
        "positive_gate",
    ]
    assert dsl["round_operation_order"] == dsl["allowed_operations"]
    policy = recipe["logic_evolution_policy"]
    assert policy["outer_rounds"] == 5
    assert policy["inner_candidate_budget_per_logic_round"] == 8
    assert policy["inner_early_stopping_non_improvements"] == 3
    assert policy["persistent_library"] is True
    assert policy["initial_logic_count"] == policy["final_selected_factor_count"] == 6
    assert policy["common_evaluation_start"] == "1999-07-31"
    assert policy["calibration_validation_end"] == "1999-06-30"
    assert policy["final_common_returns_used_for_search_or_model_choice"] is False
    assert len(recipe["preserved_elements"]) >= 13
    assert len(recipe["approximated_elements"]) >= 9
    assert len(recipe["invented_elements"]) >= 9


def test_m048_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M048"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
