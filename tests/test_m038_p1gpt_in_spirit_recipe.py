from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M038_p1gpt"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m038_recipe_pins_paper_client_and_author_output_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M038"
    assert digest(ROOT / recipe["paper_source"]["pdf_path"]) == recipe["paper_source"]["pdf_sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("mechanism_conformance_path", "mechanism_conformance_sha256"),
        ("prompt_inventory_path", "prompt_inventory_sha256"),
        ("public_component_path", "public_component_sha256"),
        ("result_recovery_path", "result_recovery_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    component = json.loads((ROOT / evidence["public_component_path"]).read_text())
    assert component["commit"] == recipe["paper_source"]["public_client_commit"]
    assert component["paper_result_credit"] is False


def test_m038_recipe_freezes_five_layers_nine_agents_integration_and_decision():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["domain_agents"]) == [
        "fundamental",
        "technical",
        "semiconductor_cycle",
        "news",
    ]
    policy = recipe["workflow_policy"]
    assert policy["layers"] == ["input", "planning", "analysis", "integration", "decision"]
    assert policy["agent_count"] == 9
    assert policy["decision_integration_weight"] == 0.8
    assert policy["decision_risk_weight"] == 0.2
    assert policy["minimum_trade_confidence"] == 0.35
    assert policy["author_2025_positions_used_as_inputs"] is False
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 7


def test_m038_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M038"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
