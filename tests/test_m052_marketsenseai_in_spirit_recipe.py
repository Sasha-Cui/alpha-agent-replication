from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M052_marketsenseai"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m052_recipe_pins_paper_and_missing_signal_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["milestone_id"] == "M052"
    assert recipe["paper_source"]["native_signal_or_portfolio_outputs_found"] is False
    evidence = recipe["strict_evidence"]
    for p, h in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("paper_version_summary_path", "paper_version_summary_sha256"),
        ("mechanism_conformance_path", "mechanism_conformance_sha256"),
        ("specification_gaps_path", "specification_gaps_sha256"),
        ("published_2026_result_ledger_path", "published_2026_result_ledger_sha256"),
    ):
        assert digest(ROOT / evidence[p]) == evidence[h]


def test_m052_recipe_freezes_specialists_and_strong_buy_tail():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["specialists"]) == ["news", "fundamentals", "dynamics", "macro"]
    policy = recipe["synthesis_and_recommendation_policy"]
    assert policy["specialist_reliability_history_months"] == 60
    assert policy["reliability_reward_purge_months"] == 1
    assert policy["five_class_percentile_boundaries"] == [0.02, 0.05, 0.84, 0.925]
    assert policy["target_strong_buy_fraction"] == 0.075
    assert policy["ordinal_values"] == [-2, -1, 0, 1, 2]
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 6


def test_m052_is_active_when_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M052"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    assert sum(ledger["progress_summary"].values()) == 69
