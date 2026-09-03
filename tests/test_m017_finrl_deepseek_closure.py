from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M017_finrl_deepseek"
AUDIT = ROOT / "paper_runs/paper_replication_audits/finrl_deepseek"


def test_m017_closes_common_transfer_without_denying_runnable_artifacts():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250207393"
    assert recipe["headline_variant"].startswith("100-epoch CPPO-DeepSeek with 10%")
    assert recipe["paper_configuration"]["training_steps"] == 2_000_000
    assert recipe["paper_configuration"]["cost_each_side"] == 0.001
    assert recipe["released_component_credit"]["checkpoint_files"] == 15
    assert recipe["released_component_credit"]["paper_relevant_checkpoints_executed"] == 8
    assert recipe["released_component_credit"]["native_evaluation_protocols_executed"] == 3
    assert len(recipe["missing_or_conflicting_headline_objects"]) == 7
    assert len(recipe["rejected_substitutes"]) == 5


def test_m017_matches_checkpoint_execution_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    assert manifest["released_checkpoint_files_total"] == 15
    assert manifest["released_dataset_files_total"] == 12
    assert manifest["paper_relevant_released_checkpoints_executed"] == 8
    assert manifest["native_evaluation_protocols_executed"] == 3
    assert manifest["native_current_rerun_configurations_exact"] == 17
    assert manifest["native_current_rerun_configurations_total"] == 24
    assert manifest["native_current_rerun_maximum_final_asset_relative_difference"] > 0.31
    assert manifest["native_table_cells_display_precision_matches"] == 0
    assert manifest["paper_numeric_table_cells_total"] == 36
    assert manifest["native_exact_figure_series_reproduced"] == 0
    assert manifest["paper_figure_series_total"] == 32
    assert manifest["public_fork_community_table_cells_matching_paper"] == 0
    assert manifest["public_fork_community_table_cells_corresponded"] == 30
    with (AUDIT / "source_config_conformance.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    universe = next(row for row in rows if row["configuration"] == "stock universe")
    assert universe["status"] == "lookahead_universe"


def test_m017_has_no_common_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m017 = rows["M017"]
    assert m017["status"] == "closed_not_evaluable"
    assert m017["monthly_returns_path"] == m017["metrics_path"] == m017["run_manifest_path"] == ""
    assert m017["recipe_path"] and m017["verdict_path"] and m017["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 17
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 15
