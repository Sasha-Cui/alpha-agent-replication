from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M011_fincon"
AUDIT = ROOT / "paper_runs/paper_replication_audits/fincon"


def test_m011_closes_the_full_policy_without_promoting_cvar_proxy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv240706567"
    assert "conceptual verbal reinforcement" in recipe["headline_strategy"]
    assert recipe["paper_configuration"]["memory_top_k"] == 5
    assert recipe["paper_configuration"]["cvar_tail"] == "worst 1% daily PnL"
    assert recipe["official_release_boundary"] == {
        "repository_commits_audited": 11,
        "tracked_files_current": 1,
        "source_code_files_current": 0,
        "public_forks_audited": 6,
        "public_fork_native_pipelines_found": 0,
    }
    assert len(recipe["missing_headline_objects"]) == 8
    assert len(recipe["rejected_substitutes"]) == 5
    assert "M0 CVaR proxy" in recipe["result_policy"]


def test_m011_matches_official_source_and_result_audit():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    native = json.loads((AUDIT / "native_execution.json").read_text())
    assert manifest["official_repository_commits_total"] == 11
    assert manifest["official_repository_source_code_files_current"] == 0
    assert manifest["paper_mechanisms_verified_in_released_source"] == 0
    assert manifest["paper_mechanisms_total"] == 33
    assert manifest["paper_numeric_table_cells_with_paper_result_credit"] == 0
    assert manifest["paper_numeric_table_cells_total"] == 306
    assert manifest["paper_unique_numeric_measurements_with_paper_result_credit"] == 0
    assert manifest["paper_unique_numeric_measurements_total"] == 288
    assert manifest["native_exact_figure_series_reproduced"] == 0
    assert manifest["paper_figure_series_total"] == 106
    assert native["source_code_files"] == native["data_model_or_checkpoint_files"] == 0
    with (AUDIT / "paper_internal_and_source_checks.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    release = next(row for row in rows if row["check"] == "official repository current")
    assert release["status"] == "implementation_absent"


def test_m011_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m011 = rows["M011"]
    assert m011["status"] == "closed_not_evaluable"
    assert m011["monthly_returns_path"] == m011["metrics_path"] == m011["run_manifest_path"] == ""
    assert m011["recipe_path"] and m011["verdict_path"] and m011["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 11
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 9
