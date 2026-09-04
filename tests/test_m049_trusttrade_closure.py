from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M049_trusttrade"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m049_closure_pins_paper_and_component_only_release():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["author_attributable_pipeline_found"] is False
    assert current["paper_linked_interfaces_found"] == 3
    assert current["participant_or_2026_forward_outputs_found"] is False


def test_m049_reuses_audit_and_rejects_the_human_interface_as_strategy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["future_year_affected_stock_days"] == 68
    assert audit["participant_outputs_recovered"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "human experiment" in assessment["why_interface_is_not_trusttrade"]
    assert "Sixty-eight" in assessment["temporal_validity_problem"]
    assert len(assessment["required_but_missing"]) == 5


def test_m049_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M049"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 49
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 38
