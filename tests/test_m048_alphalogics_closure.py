from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M048_alphalogics"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m048_closure_pins_current_paper_and_release_search():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["exact_repository_matches"] == 0
    assert current["author_attributable_native_matches"] == 0
    assert current["known_component_candidate_native_credit"] is False


def test_m048_reuses_audit_and_rejects_seed_or_independent_proxies():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["dsl_operations_specified"] == 59
    assert audit["valid_json_prompt_templates"] == 8
    assert audit["author_native_factor_expressions_released"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "seed/baseline libraries" in assessment["why_base_libraries_are_not_alphalogics"]
    assert "four rather than five" in assessment["why_independent_code_is_not_a_strategy"]
    assert len(assessment["required_but_missing"]) == 5


def test_m048_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M048"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 48
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 37
