from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M028_treevo"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m028_recipe_pins_primary_source_and_strict_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M028"
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("prompt_inventory_path", "prompt_inventory_sha256"),
        ("operator_inventory_path", "operator_inventory_sha256"),
        ("method_audit_path", "method_audit_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    provenance = json.loads((ROOT / evidence["source_provenance_path"]).read_text())
    assert provenance["versions"]["v2"]["main_sha256"] == recipe["paper_source"]["source_main_sha256"]


def test_m028_recipe_freezes_hierarchical_population_and_operator_budget():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert len(recipe["seed_features"]) == 6
    assert recipe["tree_grammar"]["binary_internal_nodes"] == [
        "mean",
        "difference",
        "product",
    ]
    policy = recipe["evolution_policy"]
    assert policy["population_size"] == 10
    assert policy["evaluation_budget"] == 200
    assert 10 + policy["offspring_generations"] * policy["offspring_per_generation"] == 200
    assert policy["operator_rotation"] == ["crossover", "mutation", "pruning"]
    assert policy["mutation_probabilities"] == {"root": 0.4, "internal": 0.4, "fine": 0.2}
    assert policy["search_training_months"] == 96
    assert policy["search_validation_months"] == 24
    assert policy["final_common_returns_used_for_search_or_selection"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 6
    assert len(recipe["invented_elements"]) >= 8


def test_m028_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M028"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
