from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M035_timi"
AUDIT = ROOT / "paper_runs/paper_replication_audits/timi"


def test_m035_selects_the_generated_grid_bot_and_rejects_the_proxy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv251004787"
    config = recipe["paper_configuration"]
    assert config["agents"] == [
        "macro analysis", "strategy adaptation", "bot evolution", "feedback reflection"
    ]
    assert config["deployment_frequency"] == "minute-level"
    assert config["reported_supported_pairs"] == 213
    assert config["entry_order_type"] == "LIMIT"
    assert len(recipe["undisclosed_required_values_and_objects"]) == 12
    assert len(recipe["rejected_substitutes"]) == 5
    assert "previous momentum/liquidity/volatility" in recipe["rejected_substitutes"][0]["route"]


def test_m035_matches_the_pinned_paper_and_broken_supplement_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    provenance = json.loads((AUDIT / "source_provenance.json").read_text())
    assert recipe["paper_pdf_sha256"] == provenance["arxiv"]["pdf_sha256"]["v2"]
    assert recipe["paper_source_sha256"] == provenance["arxiv"]["source_sha256"]["v2"]
    assert manifest["official_versions_audited"] == ["v1", "v2"]
    assert manifest["official_pages_visually_checked"] == 33
    assert manifest["published_numeric_result_units"] == 349
    assert manifest["empirical_panels"] == 8
    assert manifest["native_numeric_units_regenerated"] == 0
    assert manifest["native_empirical_panels_regenerated"] == 0
    supplement = recipe["official_supplement"]
    assert supplement["listed"] is True
    assert supplement["recovered"] is False
    assert supplement["direct_logical_status"] == 403
    assert supplement["direct_immutable_status"] == 404
    assert supplement["immutable_path"] == provenance["openreview"]["supplement_immutable_path"]


def test_m035_preserves_the_exact_policy_and_execution_gaps():
    with (AUDIT / "method_specification_audit.csv").open(newline="") as handle:
        method = {row["dimension"]: row for row in csv.DictReader(handle)}
    assert method["supplement"]["status"] == "listed_but_currently_unrecoverable"
    assert method["paper_specific_release"]["status"] == "missing"
    assert method["prompts"]["status"] == "not_released"
    assert method["optimization"]["status"] == "paper_specification_only"
    assert method["execution"]["status"] == "partially_specified"
    assert method["costs_and_slippage"]["status"] == "underspecified"
    with (AUDIT / "internal_consistency_audit.csv").open(newline="") as handle:
        checks = {row["check"]: row for row in csv.DictReader(handle)}
    assert checks["transaction_figure_order_counts"]["status"] == "paper_prose_conflict"
    assert checks["annual_return_formula"]["status"] == "not_annualized_as_printed"


def test_m035_has_no_return_artifact_and_advances_the_ledger():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m035 = rows["M035"]
    assert m035["status"] == "closed_not_evaluable"
    assert m035["monthly_returns_path"] == m035["metrics_path"] == m035["run_manifest_path"] == ""
    assert m035["recipe_path"] and m035["verdict_path"] and m035["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 35
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 28
