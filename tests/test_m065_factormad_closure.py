from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M065_factormad"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m065_closure_pins_publisher_paper_and_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["doi"] == current["paper_doi"]
    assert recipe["paper_source"]["source_archive_available"] is False
    assert current["paper_contains_native_implementation_url"] is False
    assert current["github_repository_exact_name_matches"] == 2
    assert current["github_repository_exact_doi_matches"] == 0
    assert current["exact_name_matches_are_unaffiliated_secondary_skills"] is True
    assert current["attributable_code_factor_library_or_result_release_found"] is False


def test_m065_reuses_audit_and_rejects_component_or_proxy_credit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["paper_derived_components_passing_controlled_checks"] == 13
    assert audit["fail_closed_underspecified_core_operations"] == 7
    assert audit["active_empirical_table_cells"] == 30
    assert audit["author_native_table_cells_regenerated"] == 0
    assert audit["empirical_figure_panels"] == 8
    assessment = recipe["monthly_jkp_assessment"]
    assert "no generated factor formula" in assessment["why_components_are_not_a_signal"]
    assert "no FactorMAD lineage" in assessment["why_local_proxy_is_excluded"]
    assert "unaffiliated post-paper" in assessment["why_secondary_skills_are_not_a_release"]
    assert "manufacture the central output" in assessment["why_jkp_cannot_fill_the_gap"]
    assert len(assessment["required_but_missing"]) == 5


def test_m065_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M065"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 65
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 50
