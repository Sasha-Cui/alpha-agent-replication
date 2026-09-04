from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M003_fama"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m003_in_spirit_recipe_is_source_pinned_and_explicitly_non_native():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M003"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    strict = recipe["strict_evidence"]
    assert digest(ROOT / strict["audit_manifest_path"]) == strict["audit_manifest_sha256"]
    assert digest(ROOT / strict["initial_factor_inventory_path"]) == strict["initial_factor_inventory_sha256"]
    assert len(recipe["source_anchors"]) == 4
    assert recipe["claim_boundary"].startswith("This is a researcher-authored")


def test_m003_in_spirit_recipe_pins_one_chronological_symbolic_search():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert len(recipe["seed_characteristics"]) == 6
    assert recipe["symbolic_grammar"] == {
        "identity": 6,
        "pairwise_mean": 15,
        "ordered_pairwise_difference": 15,
        "pairwise_product": 15,
        "total_candidates": 51,
        "cross_sectional_input_transform": "percentile_rank_mapped_to_minus_one_plus_one",
    }
    selection = recipe["chronological_selection"]
    assert selection["training_window_months"] == 60
    assert selection["minimum_finite_rankic_months"] == 24
    assert selection["cluster_count"] == 7
    assert selection["selected_cross_samples"] == 2
    assert selection["final_common_returns_used_for_selection"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m003_is_active_and_has_no_result_before_implementation_freeze():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    milestone = next(row for row in ledger["milestones"] if row["milestone_id"] == "M003")
    assert milestone["status"] == "in_progress_in_spirit"
    for name in ("run_manifest.json", "monthly_returns.csv", "metrics.csv", "verdict.md"):
        assert not (OUTPUT / name).exists()
