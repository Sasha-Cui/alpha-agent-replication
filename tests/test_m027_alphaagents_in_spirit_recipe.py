from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M027_alphaagents"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m027_recipe_pins_paper_and_source_only_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M027"
    assert digest(ROOT / recipe["paper_source"]["pdf_path"]) == recipe["paper_source"]["pdf_sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("prompt_inventory_path", "prompt_inventory_sha256"),
        ("portfolio_inventory_path", "portfolio_inventory_sha256"),
        ("method_audit_path", "method_audit_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]


def test_m027_recipe_freezes_three_agents_round_robin_and_no_backcast():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["specialist_agents"]) == [
        "fundamental",
        "sentiment",
        "valuation",
    ]
    policy = recipe["debate_policy"]
    assert policy["risk_profile"] == "risk-neutral"
    assert policy["speaker_order"] == ["fundamental", "sentiment", "valuation"]
    assert policy["round_robin_passes"] == 2
    assert policy["own_specialist_retention_weight"] == 0.65
    assert policy["peer_median_update_weight"] == 0.35
    assert policy["paper_2024_ticker_memberships_used_as_inputs"] is False
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 9
    assert len(recipe["approximated_elements"]) >= 6
    assert len(recipe["invented_elements"]) >= 6


def test_m027_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M027"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
