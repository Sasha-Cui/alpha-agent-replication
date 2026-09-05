from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M034_quantagents"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m034_recipe_pins_paper_site_and_strict_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M034"
    assert digest(ROOT / recipe["paper_source"]["pdf_path"]) == recipe["paper_source"]["pdf_sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_audit_path", "method_audit_sha256"),
        ("prompt_inventory_path", "prompt_inventory_sha256"),
        ("site_documentation_path", "site_documentation_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    provenance = json.loads((ROOT / evidence["source_provenance_path"]).read_text())
    assert provenance["official_pdf_sha256"] == recipe["paper_source"]["pdf_sha256"]
    assert provenance["project_repository_head"] == recipe["paper_source"]["author_site_commit"]


def test_m034_recipe_freezes_four_agents_memories_meetings_and_dual_rewards():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert len(recipe["strategy_pool"]) == 10
    assert [key for key in recipe["agents_and_meetings"] if key != "meetings"] == [
        "Otto",
        "Bob",
        "Dave",
        "Emily",
    ]
    policy = recipe["memory_and_policy"]
    assert policy["memory_history_months"] == 120
    assert policy["retrieved_similar_cases"] == 10
    assert policy["new_strategy_members"] == 3
    assert policy["adaptive_reward_window"] == 12
    assert policy["risk_alert_threshold"] == 0.75
    assert policy["risk_policy_weight_when_triggered"] == 0.5
    assert policy["market_report_weight"] + policy["strategy_policy_weight"] == 1.0
    assert policy["risk_component_weights"] == [0.25, 0.25, 0.25, 0.25]
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 8


def test_m034_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M034"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
