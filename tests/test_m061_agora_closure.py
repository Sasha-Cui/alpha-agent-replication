from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M061_agora"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m061_closure_pins_paper_and_fresh_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["paper_contains_repository_url"] is False
    assert current["github_repository_exact_arxiv_id_matches"] == 0
    assert current["github_repository_exact_title_matches"] == 0
    assert current["github_code_top_alpha_registry_matches"] == 0
    assert current["attributable_code_registry_alpha_pool_checkpoint_or_action_release_found"] is False


def test_m061_reuses_audit_and_rejects_metric_or_portfolio_shell_proxies():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["complete_paper_metric_programs_executed"] == 2
    assert audit["active_quantitative_table_cells"] == 293
    assert audit["author_native_table_cells_regenerated"] == 0
    assert audit["active_empirical_figure_panels"] == 4
    assert audit["author_native_empirical_panels_regenerated"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "do not generate an alpha score" in assessment["why_metric_programs_are_not_a_strategy"]
    assert "has no signal to rank" in assessment["why_portfolio_shell_is_insufficient"]
    assert "bypass agent-to-agent search" in assessment["why_jkp_cannot_fill_the_gap"]
    assert len(assessment["preserved_components"]) == 3
    assert len(assessment["required_but_missing"]) == 5


def test_m061_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M061"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 61
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 48
