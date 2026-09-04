from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M067_raptor"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m067_closure_pins_current_author_repository_heads():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert current["main_head_sha"] == current["audited_main_head_sha"]
    assert current["validation_branch_head_sha"] == current["audited_validation_branch_head_sha"]
    assert recipe["official_repository"]["main_head_sha"] == current["main_head_sha"]
    assert recipe["official_repository"]["validation_branch_head_sha"] == current["validation_branch_head_sha"]
    assert current["new_price_input_decision_trace_or_backtest_release_found"] is False


def test_m067_preserves_output_credit_but_rejects_snapshot_policy_proxy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["author_result_snapshots"] == 166
    assert audit["author_output_verified_scalar_results"] == 18
    assert audit["displayed_scalar_results_verified_all_routes"] == 29
    assert audit["displayed_scalar_results"] == 42
    assert audit["published_figure_raster_correspondences_verified"] == 3
    assert audit["end_to_end_result_cells_reproduced"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "verify one 2025 portfolio output path" in assessment["why_snapshots_are_not_a_transferable_policy"]
    assert "invent a persistence policy" in assessment["why_day0_decisions_are_insufficient"]
    assert "replace the multi-agent reasoning" in assessment["why_black_litterman_component_is_not_raptor"]
    assert "fabricating actions" in assessment["why_jkp_cannot_fill_the_gap"]
    assert len(assessment["required_but_missing"]) == 5


def test_m067_has_no_fabricated_common_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M067"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 67
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 52
