from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M063_fin_analyst"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m063_closure_pins_current_public_surfaces():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert current["author_space_head_sha"] == recipe["current_release_check"]["author_space_head_sha"]
    assert current["organizer_dataset_head_sha"] == recipe["current_release_check"]["organizer_dataset_head_sha"]
    assert current["organizer_space_head_sha"] == recipe["current_release_check"]["organizer_space_head_sha"]
    assert current["author_space_public_and_enabled"] is True
    assert current["new_cross_sectional_policy_or_security_score_release_found"] is False


def test_m063_preserves_real_reproduction_credit_but_rejects_action_replay_proxy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["official_decision_rows_replayed"] == 97
    assert audit["organizer_equity_points_exact"] == 291
    assert audit["published_table_cells_regenerated"] == 33
    assert audit["published_cells_from_native_llm_pipeline"] == 0
    assert audit["active_empirical_table_cells"] == 119
    assessment = recipe["monthly_jkp_assessment"]
    assert "historical outputs for TSLA and BTC" in assessment["why_action_replay_is_not_a_transferable_policy"]
    assert "remove the hybrid policy" in assessment["why_rule_components_are_not_enough"]
    assert "fabricate actions" in assessment["why_jkp_cannot_fill_the_gap"]
    assert len(assessment["preserved_components"]) == 3
    assert len(assessment["required_but_missing"]) == 5


def test_m063_has_no_fabricated_common_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M063"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 63
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 49
