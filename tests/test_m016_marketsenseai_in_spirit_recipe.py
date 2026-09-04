from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M016_marketsenseai"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m016_recipe_pins_paper_mechanism_and_result_ledger():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M016"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("mechanism_path", "mechanism_sha256"),
        ("result_ledger_path", "result_ledger_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m016_recipe_freezes_four_specialists_and_monthly_signal_agent():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["specialists"]) == ["news", "fundamentals", "dynamics", "macro"]
    policy = recipe["signal_policy"]
    assert policy["reliability_window_months"] == 60
    assert policy["minimum_rankic_months"] == 24
    assert policy["softmax_temperature"] == 10.0
    assert policy["buy_threshold"] == 0.1
    assert policy["sell_threshold"] == -0.1
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert "long-short deciles" in recipe["portfolio_adapter"]
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m016_is_the_only_active_in_spirit_milestone():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    active = [row["milestone_id"] for row in ledger["milestones"] if row["status"] == "in_progress_in_spirit"]
    assert active == ["M016"]
