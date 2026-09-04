from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M066_alphaagentevo"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m066_closure_pins_primary_record_and_current_access_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["openreview_id"] == current["openreview_id"]
    assert current["official_supplement_listed"] is True
    assert current["official_supplement_immutable_status"] == 404
    assert current["openreview_api_status"] == 403
    assert current["official_supplement_recovered"] is False
    assert current["paper_author_code_or_checkpoint_found"] is False
    assert current["third_party_candidates_with_native_credit"] == 0


def test_m066_reuses_audit_and_rejects_third_party_or_proxy_credit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["published_numeric_result_units"] == 147
    assert audit["native_numeric_units_regenerated"] == 0
    assert audit["empirical_panels"] == 21
    assert audit["native_empirical_panels_regenerated"] == 0
    assert audit["printed_figure_numeric_annotations"] == 40
    assessment = recipe["monthly_jkp_assessment"]
    assert "prints no final alpha formula" in assessment["why_paper_specification_is_not_a_signal"]
    assert "Neither candidate is attributable" in assessment["why_third_party_candidates_are_excluded"]
    assert "no AlphaAgentEvo" in assessment["why_local_proxy_is_excluded"]
    assert "manufacture the strategy output" in assessment["why_jkp_cannot_fill_the_gap"]
    assert len(assessment["required_but_missing"]) == 5


def test_m066_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M066"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 66
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 51
