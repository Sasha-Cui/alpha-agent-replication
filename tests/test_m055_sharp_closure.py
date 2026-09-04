from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M055_sharp"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m055_closure_pins_paper_and_fresh_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["cited_dataset_repository_status"] == 404
    assert current["cited_dataset_owner_status"] == 404
    assert current["github_repository_exact_arxiv_id_matches"] == 0
    assert current["github_repository_exact_title_matches"] == 0
    assert current["unique_rule_code_attributable_matches"] == 0


def test_m055_reuses_audit_and_limits_component_credit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["paper_derived_components_passing_controlled_checks"] == 7
    assert audit["active_quantitative_table_cells"] == 210
    assert audit["author_native_table_cells_regenerated"] == 0
    assert audit["author_native_empirical_panels_regenerated"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "do not create the base prediction" in assessment["why_initial_rules_are_not_a_signal"]
    assert "synthetic fixtures" in assessment["why_mechanics_are_not_sharp"]
    assert "remove SHARP's attribution-guided rubric evolution" in assessment["why_jkp_cannot_fill_the_gap"]
    assert "cannot receive completed-partial strategy credit" in assessment["strongest_defensible_credit"]
    assert len(assessment["required_but_missing"]) == 5


def test_m055_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M055"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 55
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 44
