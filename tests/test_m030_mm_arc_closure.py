from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M030_mm_arc"
AUDIT = ROOT / "paper_runs/paper_replication_audits/mm_arc"


def test_m030_closes_missing_trained_policy_without_denying_release_quality():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250905080"
    assert recipe["version_scope"].startswith("v3 MM-ARC wholesale replacement")
    assert recipe["paper_configuration"]["strategy_pools"] == 60
    assert recipe["paper_configuration"]["active_members"] == 300
    assert recipe["paper_configuration"]["reported_training_seeds"] == [42, 43, 44, 45, 46]
    credit = recipe["released_component_credit"]
    assert credit["tests_passed"] == 111
    assert credit["registered_artifacts"] == 35
    assert credit["verified_artifacts"] == 29
    assert credit["remaining_lfs_files"] == 6
    assert credit["remaining_lfs_bytes"] == 306295258
    assert len(recipe["missing_headline_objects"]) == 6
    assert len(recipe["rejected_substitutes"]) == 5


def test_m030_matches_lfs_execution_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    execution = json.loads((AUDIT / "release_execution_audit.json").read_text())
    assert manifest["official_repository_files"] == 107
    assert manifest["official_repository_tests_passed"] == 111
    assert manifest["registered_artifact_files_verified_after_exact_public_recovery"] == 29
    assert manifest["remaining_unavailable_lfs_payload_files"] == 6
    assert manifest["remaining_unavailable_lfs_registered_bytes"] == 306295258
    assert manifest["all_five_trained_seeds_released"] is False
    assert manifest["current_native_numeric_units_regenerated"] == 0
    assert manifest["current_published_numeric_table_units"] == 651
    assert execution["paper_decision_cycle_executed_in_audit"] is False
    assert execution["tests_use_model_runtime_doubles"] is True
    assert execution["full_model_forward_executed_in_audit"] is False
    with (AUDIT / "lfs_payload_recovery_audit.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    unavailable = [row for row in rows if row["exact_public_payload_recovered"] == "False"]
    assert len(unavailable) == 6
    assert all(row["native_model_or_strategy_execution_enabled"] == "False" for row in unavailable)


def test_m030_has_no_return_artifact_and_closes_batch_of_thirty():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m030 = rows["M030"]
    assert m030["status"] == "closed_not_evaluable"
    assert m030["monthly_returns_path"] == m030["metrics_path"] == m030["run_manifest_path"] == ""
    assert m030["recipe_path"] and m030["verdict_path"] and m030["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 30
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 24
