from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M037_atlas"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m037_recipe_pins_v5_paper_precursor_and_missing_atlas_layer():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M037"
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_audit_path", "method_audit_sha256"),
        ("prompt_artifacts_path", "prompt_artifacts_sha256"),
        ("release_execution_path", "release_execution_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    provenance = json.loads((ROOT / evidence["source_provenance_path"]).read_text())
    assert provenance["arxiv"]["pdf_sha256"]["v5"] == recipe["paper_source"]["pdf_sha256"]
    assert provenance["arxiv"]["source_sha256"]["v5"] == recipe["paper_source"]["source_sha256"]


def test_m037_recipe_freezes_analysts_template_window_score_and_updates():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["analyst_agents"]) == ["market", "news", "fundamental"]
    policy = recipe["adaptive_opro_policy"]
    assert policy["evaluation_window_decisions"] == 5
    assert sum(policy["initial_analyst_weights"].values()) == 1.0
    assert policy["initial_hold_threshold"] == 0.1
    assert policy["hold_threshold_bounds"] == [0.0, 0.4]
    assert policy["analyst_weight_update_rate"] == 0.25
    assert policy["poor_window_threshold_increment"] == 0.05
    assert policy["successful_window_threshold_decrement"] == 0.02
    assert policy["no_window_replay"] is True
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 7


def test_m037_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M037"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
