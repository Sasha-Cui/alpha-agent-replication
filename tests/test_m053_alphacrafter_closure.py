from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M053_alphacrafter"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m053_closure_pins_current_paper_and_release():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v2"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["current_head_sha"] == current["audited_head_sha"]
    assert current["current_head_matches_audited_release"] is True
    assert current["tag_count"] == current["release_count"] == 0
    assert current["new_factor_pool_or_result_artifact_found"] is False


def test_m053_reuses_audit_and_separates_components_from_results():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["native_component_checks_passed"] == 6
    assert audit["v2_published_numeric_result_units"] == 304
    assert audit["v2_native_numeric_units_regenerated"] == 0
    assert audit["v2_empirical_panels"] == 14
    assert audit["v2_native_empirical_panels_regenerated"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "produce no security score" in assessment["why_components_are_not_a_signal"]
    assert "received zero responses" in assessment["why_override_probe_is_not_a_replication"]
    assert "replace AlphaCrafter's defining workflow" in assessment["why_jkp_cannot_fill_the_gap"]
    assert len(assessment["preserved_components"]) == 3
    assert len(assessment["required_but_missing"]) == 5


def test_m053_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M053"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 53
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 42
