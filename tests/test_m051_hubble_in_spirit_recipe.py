from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M051_hubble"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m051_recipe_pins_source_and_withholding_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["milestone_id"] == "M051"
    assert recipe["paper_source"]["attributable_native_implementation_or_formula_found"] is False
    evidence = recipe["strict_evidence"]
    for p, h in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_specification_path", "method_specification_sha256"),
        ("model_release_chronology_path", "model_release_chronology_sha256"),
        ("sandbox_component_execution_path", "sandbox_component_execution_sha256"),
    ):
        assert digest(ROOT / evidence[p]) == evidence[h]


def test_m051_recipe_freezes_safe_diverse_top_five_search():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert len(recipe["factor_families"]) == 6
    assert all(len(items) == 4 for items in recipe["factor_families"].values())
    policy = recipe["safe_search_policy"]
    assert policy["mining_rounds"] == 3
    assert len(policy["dsl_operations"]) == 5
    assert policy["negative_rag_crowded_family"] == "liquidity_volume"
    assert policy["maximum_similarity"] == 0.80
    assert policy["family_cap"] == 2 and policy["top_k"] == 5
    assert policy["calibration_end"] < policy["common_start"]
    assert policy["final_common_returns_used_for_search"] is False
    assert len(recipe["preserved_elements"]) >= 13
    assert len(recipe["approximated_elements"]) >= 8
    assert len(recipe["invented_elements"]) >= 9


def test_m051_is_active_when_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M051"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    assert sum(ledger["progress_summary"].values()) == 69
