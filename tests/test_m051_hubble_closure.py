from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M051_hubble"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m051_closure_pins_v2_and_fresh_release_search():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v2"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["exact_repository_matches"] == 0
    assert current["top_five_formulas_released"] is False
    assert current["native_runtime_or_persisted_diagnostics_found"] is False


def test_m051_reuses_audit_and_rejects_family_or_sandbox_proxies():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["conditional_sandbox_component_executed"] is True
    assert audit["native_empirical_units_regenerated"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "explicitly withholds" in assessment["intentional_withholding"]
    assert "manufacture a formula" in assessment["why_family_proxy_is_not_hubble"]
    assert "conditional safe execution only" in assessment["why_sandbox_component_is_insufficient"]
    assert len(assessment["required_but_missing"]) == 5


def test_m051_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M051"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 51
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 40
