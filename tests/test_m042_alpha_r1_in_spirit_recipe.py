from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M042_alpha_r1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m042_recipe_pins_paper_and_placeholder_release_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M042"
    assert recipe["paper_source"]["attributable_implementation_found"] is False
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("native_release_inspection_path", "native_release_inspection_sha256"),
        ("paper_specification_gaps_path", "paper_specification_gaps_sha256"),
        ("source_mechanism_conformance_path", "source_mechanism_conformance_sha256"),
        ("paper_numeric_table_conformance_path", "paper_numeric_table_conformance_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    audit = json.loads((ROOT / evidence["audit_manifest_path"]).read_text())
    assert audit["paper_sha256"] == recipe["paper_source"]["pdf_sha256"]
    assert audit["paper_source_sha256"] == recipe["paper_source"]["source_sha256"]


def test_m042_recipe_freezes_contextual_sparse_gate_before_result():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    zoo = recipe["factor_zoo"]
    assert len(zoo) == 40
    assert len({item["column"] for item in zoo}) == 40
    assert {item["sign"] for item in zoo} == {-1, 1}
    families = {item["family"] for item in zoo}
    assert families == set(recipe["semantic_family_affinities"])
    policy = recipe["contextual_gate_policy"]
    assert policy["factor_count"] == 40
    assert policy["selected_factor_count"] == 10
    assert policy["market_state_descriptors"] == [
        "price_trend",
        "volatility",
        "price_breadth",
        "earnings_news",
    ]
    assert policy["factor_profile_history_months"] == 60
    assert policy["minimum_factor_profile_months"] == 48
    assert policy["factor_profile_reward_purge_months"] == 1
    assert policy["linear_beta_history_months"] == 48
    assert policy["linear_beta_reward_purge_months"] == 1
    assert policy["performance_gate_weight"] == 0.5
    assert policy["semantic_gate_weight"] == 0.5
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert recipe["anti_leakage"]["old_five_factor_motif_used"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 8
    assert len(recipe["invented_elements"]) >= 8


def test_m042_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M042"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
