from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M054_stratllm"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m054_closure_pins_paper_and_fresh_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["advertised_project_page_status"] == 404
    assert current["github_repository_exact_arxiv_id_matches"] == 0
    assert current["github_repository_exact_title_matches"] == 0
    assert current["attributable_action_or_result_release_found"] is False


def test_m054_reuses_audit_and_rejects_incomplete_strategy_proxy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["published_unique_empirical_numeric_units"] == 190
    assert audit["native_empirical_units_regenerated"] == 0
    assert audit["procedure_component_executed"] is True
    assert audit["procedure_component_paper_result_credit"] is False
    assessment = recipe["monthly_jkp_assessment"]
    assert "one incomplete clause" in assessment["why_s2_is_not_a_headline_partial"]
    assert "researcher-set zero cost" in assessment["why_procedure_component_is_insufficient"]
    assert "replace the central alignment experiment" in assessment["why_jkp_cannot_fill_the_gap"]
    assert "post-outcome selection" in assessment["reported_us_result_context"]
    assert len(assessment["required_but_missing"]) == 5


def test_m054_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M054"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 54
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 43
