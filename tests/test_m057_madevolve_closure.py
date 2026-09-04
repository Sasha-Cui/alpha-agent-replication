from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M057_madevolve"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m057_closure_pins_paper_framework_and_current_head():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == "v1"
    assert recipe["official_framework"]["current_head_sha"] == current["current_head_sha"]
    assert current["current_head_sha"] == current["audited_head_sha"]
    assert current["current_head_matches_audited_release"] is True
    assert current["framework_site_status"] == 200
    assert current["tag_count"] == current["release_count"] == 0
    assert current["new_trading_code_or_evolved_program_found"] is False


def test_m057_reuses_audit_and_rejects_framework_or_skeleton_proxies():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["native_framework_component_checks_passed"] == 5
    assert audit["published_numeric_result_units"] == 214
    assert audit["native_numeric_units_regenerated"] == 0
    assert audit["empirical_panels"] == 21
    assert audit["native_empirical_panels_regenerated"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "domain-general evolutionary infrastructure" in assessment["why_framework_is_not_a_strategy"]
    assert "neither the evolved headline program" in assessment["why_appendix_skeleton_is_insufficient"]
    assert "create a new system" in assessment["why_jkp_cannot_fill_the_gap"]
    assert len(assessment["preserved_components"]) == 3
    assert len(assessment["required_but_missing"]) == 5


def test_m057_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M057"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 57
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 45
