from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M060_metaps"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m060_closure_pins_paper_and_fresh_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["paper_contains_native_implementation_url"] is False
    assert current["paper_contains_dataset_or_checkpoint_url"] is False
    assert current["github_repository_exact_arxiv_id_matches"] == 0
    assert current["github_repository_exact_title_matches"] == 0
    assert current["attributable_code_data_model_or_action_release_found"] is False


def test_m060_reuses_audit_and_rejects_library_component_proxies():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["paper_derived_components_passing_controlled_checks"] == 12
    assert audit["active_quantitative_table_cells"] == 492
    assert audit["author_native_table_cells_regenerated"] == 0
    assert audit["active_empirical_figure_panels"] == 20
    assert audit["author_native_empirical_panels_regenerated"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "do not identify the trained selector" in assessment["why_components_are_not_metaps"]
    assert "one input program among ten" in assessment["why_momentum_is_not_a_defensible_headline_partial"]
    assert "mathematically unreachable" in assessment["why_volatility_listing_is_not_a_strategy"]
    assert "library ingredient" in assessment["why_jkp_cannot_fill_the_gap"]
    assert len(assessment["preserved_components"]) == 3
    assert len(assessment["required_but_missing"]) == 5


def test_m060_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M060"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 60
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 47
    assert ledger["progress_summary"]["in_progress"] == 0
