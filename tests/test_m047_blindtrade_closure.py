from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M047_blindtrade"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m047_closure_pins_the_paper_and_fresh_release_search():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["exact_repository_matches"] == current["native_code_matches"] == 0
    assert current["author_attributable_release_found"] is False
    assert current["paper_promised_feature_dataset_currently_exposed"] is False


def test_m047_reuses_audit_and_does_not_promote_a_baseline():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["author_native_table_cells_regenerated"] == 0
    assert audit["printed_prompt_schemas_valid_json"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "explicit active benchmark" in assessment["why_raw_top20_is_not_blindtrade"]
    assert "1.22 million" in assessment["scale_if_regenerated"]
    assert len(assessment["required_but_missing"]) == 5


def test_m047_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M047"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 47
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 36
