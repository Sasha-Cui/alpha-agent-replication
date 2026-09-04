from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M050_agentic_screening"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m050_closure_pins_current_v2_and_release_search():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v2"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["exact_title_repository_matches"] == 0
    assert current["arxiv_id_author_native_code_matches"] == 0
    assert current["unaffiliated_candidate_native_credit"] is False


def test_m050_reuses_audit_and_rejects_component_substitutes():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["linked_news_rows"] == 4589
    assert audit["author_native_numeric_cells_regenerated"] == 0
    assert audit["complete_annual_prompt_output_sets_recovered"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "one 2024 rule" in assessment["why_one_date_prompt_is_insufficient"]
    assert "one screening agent" in assessment["why_finbert_only_is_not_the_headline"]
    assert "PyPortfolioOpt" in assessment["why_independent_code_is_not_a_replication"]
    assert len(assessment["required_but_missing"]) == 5


def test_m050_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M050"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 50
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 39
    assert ledger["progress_summary"]["in_progress"] == 0
