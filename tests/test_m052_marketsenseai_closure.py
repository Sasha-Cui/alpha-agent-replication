from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M052_marketsenseai"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m052_closure_pins_paper_and_fresh_release_search():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["exact_repository_matches"] == 0
    assert current["same_day_record_implementation_status"] == "not-implemented"
    assert current["dated_recommendation_or_embedding_panel_found"] is False


def test_m052_reuses_audit_and_rejects_aggregate_or_nnls_proxies():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["sp500_stock_date_rows"] + audit["sp100_stock_date_rows"] == 12163
    assert audit["native_2026_result_units_regenerated"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "do not identify which securities" in assessment["why_aggregate_counts_are_not_actions"]
    assert "attribution" in assessment["why_nnls_is_not_the_signal"]
    assert "fabricate decisions" in assessment["why_jkp_cannot_fill_the_gap"]
    assert len(assessment["required_but_missing"]) == 5


def test_m052_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M052"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 52
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 41
