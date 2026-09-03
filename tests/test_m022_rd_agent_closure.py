from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M022_rd_agent"
AUDIT = ROOT / "paper_runs/paper_replication_audits/rd_agent"


def test_m022_closes_primary_record_without_substituting_quant_lineage():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250514738"
    assert "75 Kaggle competitions" in recipe["headline_method"]
    assert "not the separate R&D-Agent-Quant" in recipe["scope_finding"]
    assert recipe["common_task_portability"] == "not applicable without substituting a different paper and system"
    assert recipe["released_component_credit"]["paper_mechanisms_with_source_implementation"] == 21
    assert recipe["released_component_credit"]["paper_era_modules_imported"] == 192
    assert len(recipe["missing_paper_result_objects"]) == 5
    assert len(recipe["rejected_substitutes"]) == 4
    assert "scope finding" in recipe["result_policy"]


def test_m022_matches_source_execution_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    native = json.loads((AUDIT / "native_execution.json").read_text())
    assert manifest["primary_record_scope"].startswith("general MLE-Bench")
    assert manifest["paper_mechanisms_with_source_implementation"] == 21
    assert manifest["paper_mechanisms_verified_as_executed_in_reported_run"] == 0
    assert manifest["paper_era_data_science_and_kaggle_python_files_compiled"] == 233
    assert manifest["paper_era_source_modules_imported"] == 192
    assert manifest["paper_numeric_table_cells_with_paper_result_credit"] == 0
    assert manifest["paper_numeric_table_cells_total"] == 534
    assert manifest["paper_unique_numeric_measurements_with_paper_result_credit"] == 0
    assert manifest["paper_unique_numeric_measurements_total"] == 526
    assert manifest["native_exact_figure_series_reproduced"] == 0
    assert manifest["paper_figure_series_total"] == 24
    assert native["full_native_paper_execution_attempted"] is False
    assert native["released_source_component_execution"]["native_scheduler_softmax_passed"] is True


def test_m022_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m022 = rows["M022"]
    assert m022["status"] == "closed_not_evaluable"
    assert m022["monthly_returns_path"] == m022["metrics_path"] == m022["run_manifest_path"] == ""
    assert m022["recipe_path"] and m022["verdict_path"] and m022["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 22
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 18
