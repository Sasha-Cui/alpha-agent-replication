from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M025_contesttrade"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m025_recipe_pins_paper_source_and_strict_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M025"
    assert digest(ROOT / recipe["paper_source"]["pdf_path"]) == recipe["paper_source"]["pdf_sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("config_conformance_path", "config_conformance_sha256"),
        ("entrypoint_reachability_path", "entrypoint_reachability_sha256"),
        ("zi_semantics_path", "zi_semantics_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    manifest = json.loads((ROOT / evidence["audit_manifest_path"]).read_text())
    assert manifest["paper_sha256"] == recipe["paper_source"]["pdf_sha256"]
    assert manifest["source_commit"] == recipe["paper_source"]["source_commit"]


def test_m025_recipe_freezes_both_quantify_predict_allocate_contests():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert len(recipe["data_agents"]) == 16
    assert list(recipe["research_agents"]) == [
        "momentum",
        "reversal",
        "fundamentals",
        "event_driven",
        "risk_control",
    ]
    policy = recipe["contest_policy"]
    assert policy["data_history_months"] == 24
    assert policy["data_recent_trend_months"] == 6
    assert policy["data_context_budget_agents"] == 8
    assert policy["research_context_weight"] == 0.5
    assert policy["research_belief_weight"] == 0.5
    assert policy["research_history_months"] == 24
    assert policy["qualitative_judge_weight"] == 0.1
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 8


def test_m025_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M025"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
