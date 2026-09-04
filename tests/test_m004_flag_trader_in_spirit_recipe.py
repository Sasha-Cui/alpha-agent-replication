from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M004_flag_trader"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m004_recipe_pins_paper_prompt_hyperparameters_and_claim_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M004"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("prompt_path", "prompt_sha256"),
        ("hyperparameters_path", "hyperparameters_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4
    assert recipe["claim_boundary"].startswith("This is a researcher-authored")


def test_m004_recipe_freezes_one_past_only_actor_critic_surrogate():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert [item["column"] for item in recipe["state_features"]] == [
        "be_me",
        "ret_12_1",
        "ret_1_0",
        "rvol_21d",
    ]
    assert [item["semantic_prior_weight"] for item in recipe["state_features"]] == [1.0, 1.0, 0.5, -1.0]
    policy = recipe["chronological_policy"]
    assert policy["replay_window_months"] == 60
    assert policy["learning_rate"] == 0.0005
    assert policy["update_epochs"] == 1
    assert policy["clip_coefficient"] == 0.2
    assert policy["maximum_gradient_norm"] == 0.5
    assert policy["action_memory_weight"] == 0.2
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m004_recipe_remains_pinned_after_the_ledger_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    milestone = next(row for row in ledger["milestones"] if row["milestone_id"] == "M004")
    assert milestone["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    if milestone["status"] == "completed_in_spirit":
        manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
        assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
