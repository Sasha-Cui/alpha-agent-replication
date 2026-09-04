from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M032_trading_r1"
AUDIT = ROOT / "paper_runs/paper_replication_audits/trading_r1"


def test_m032_selects_the_trained_policy_not_its_label_or_reward_components():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250911420"
    config = recipe["paper_configuration"]
    assert config["backbone"] == "Qwen3-4B"
    assert config["input_frequency"] == "daily"
    assert config["target_holding_period"] == "approximately one week"
    assert config["training_samples"] == 100000
    assert config["training_tickers"] == 14
    assert config["action_space"] == ["Strong Sell", "Sell", "Hold", "Buy", "Strong Buy"]
    assert len(recipe["required_headline_objects"]) == 6
    assert len(recipe["rejected_substitutes"]) == 5
    assert "literal Algorithm S1 labels" in recipe["rejected_substitutes"][1]["route"]


def test_m032_matches_the_pinned_and_live_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    release = recipe["official_release"]
    assert recipe["paper_pdf_sha256"] == manifest["primary_snapshot_sha256"]["paper.pdf"]
    assert release["paper_snapshot_repository_files"] == manifest["official_repository_tracked_files_current"] == 1
    assert release["paper_snapshot_repository_source_files"] == manifest["official_repository_source_code_files_current"] == 0
    assert release["live_head_unchanged"] is True
    assert release["live_repository_file"] == "README.md"
    assert release["live_repository_file_bytes"] == 49
    assert release["live_repository_commits"] == 1
    assert release["live_tags"] == release["live_releases"] == 0
    assert release["live_huggingface_models"] == release["live_huggingface_datasets"] == 0


def test_m032_preserves_specification_credit_without_result_credit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    native = json.loads((AUDIT / "native_execution.json").read_text())
    credit = recipe["paper_specification_credit"]
    assert credit["literal_algorithm_s1_reconstructed"] is True
    assert credit["decision_reward_matrix_reconstructed"] is True
    assert credit["paper_mechanisms_verified_in_native_source"] == 0
    assert credit["published_numeric_result_units"] == 348
    assert credit["native_result_units_reproduced"] == 0
    assert manifest["blocking_specification_gaps"] == 15
    assert native["native_system_execution_attempted"] is False
    assert native["paper_specification_reconstruction"]["paper_result_credit"] is False
    with (AUDIT / "paper_internal_consistency_checks.csv").open(newline="") as handle:
        checks = {row["check"]: row for row in csv.DictReader(handle)}
    assert checks["label_threshold_causality"]["status"] == "literal_formula_is_not_prefix_stable"
    assert checks["trading_r1_nvda_sharpe"]["status"] == "paper_internal_conflict"


def test_m032_has_no_return_artifact_and_advances_the_ledger():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m032 = rows["M032"]
    assert m032["status"] == "closed_not_evaluable"
    assert m032["monthly_returns_path"] == m032["metrics_path"] == m032["run_manifest_path"] == ""
    assert m032["recipe_path"] and m032["verdict_path"] and m032["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 32
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 26
