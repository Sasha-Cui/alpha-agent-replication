from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M058_macro_machine"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m058_closure_pins_paper_and_fresh_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_source"]["version"] == current["paper_version"] == "v1"
    assert recipe["paper_source"]["official_pdf_sha256"] == current["paper_pdf_sha256"]
    assert current["paper_contains_native_implementation_url"] is False
    assert current["paper_says_materials_available_on_request"] is True
    assert current["github_repository_exact_arxiv_id_matches"] == 0
    assert current["github_repository_exact_title_matches"] == 0
    assert current["attributable_code_data_contract_or_weight_release_found"] is False


def test_m058_reuses_audit_and_rejects_equation_or_asset_proxies():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["paper_derived_components_passing_controlled_checks"] == 22
    assert audit["fail_closed_underspecified_core_operations"] == 4
    assert audit["active_empirical_table_cells"] == 132
    assert audit["author_native_table_cells_regenerated"] == 0
    assert audit["empirical_figure_panels"] == 12
    assert audit["author_native_empirical_panels_regenerated"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "cannot produce dated ETF weights" in assessment["why_equation_components_are_not_a_strategy"]
    assert "bypass the three LLM agents" in assessment["why_rule_only_proxy_is_not_the_headline"]
    assert "no mapping from ETF tilts" in assessment["why_etf_to_stock_transfer_is_not_identified"]
    assert len(assessment["preserved_components"]) == 3
    assert len(assessment["required_but_missing"]) == 5


def test_m058_has_no_fabricated_returns_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M058"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 58
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 46
