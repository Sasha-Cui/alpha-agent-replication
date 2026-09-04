from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M020_mass"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m020_recipe_pins_audit_nonidentifiability_and_configuration():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M020"
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("nonidentifiability_path", "nonidentifiability_sha256"),
        ("configuration_path", "configuration_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    manifest = json.loads((ROOT / evidence["audit_manifest_path"]).read_text())
    assert manifest["paper_sha256"] == recipe["paper_source"]["sha256_from_pinned_audit"]


def test_m020_recipe_freezes_agent_counts_pools_aggregation_and_annealing():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert len(recipe["investor_type_features"]) == 16
    policy = recipe["simulation_policy"]
    assert policy["investor_types"] == 16
    assert policy["agents_per_type"] == 32
    assert policy["candidate_pool_size"] == 20
    assert policy["selections_per_agent"] == 5
    assert policy["aggregation_alpha"] == 0.5
    assert policy["annealing_initial_temperature"] == 40.0
    assert policy["annealing_iterations"] == 100
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m020_is_the_only_active_in_spirit_milestone():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    active = [row["milestone_id"] for row in ledger["milestones"] if row["status"] == "in_progress_in_spirit"]
    assert active == ["M020"]
