from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_trading_r1_paper.py"
SPEC = importlib.util.spec_from_file_location("trading_r1_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_complete_paper_result_census_is_fail_closed() -> None:
    tables = audit.paper_table_rows()
    figures = audit.figure_rows()
    assert len(tables) == 312
    assert Counter(row["paper_table"] for row in tables) == {
        "Table 3": 156,
        "Table 4": 156,
    }
    assert Counter(row["metric"] for row in tables) == {
        "CR_pct": 78,
        "SR": 78,
        "HR_pct": 78,
        "MDD_pct": 78,
    }
    assert len(figures) == 36
    assert sum(row["internally_consistent_with_table_precision"] for row in figures) == 35
    conflict = [
        row
        for row in figures
        if not row["internally_consistent_with_table_precision"]
    ]
    assert [(row["category"], row["asset"]) for row in conflict] == [
        ("Trading-R1", "NVDA")
    ]
    assert conflict[0]["paper_figure_value"] == "1.881"
    assert conflict[0]["table_derived_sr_from_rounded_cells"] == "2.720000"
    assert {row["paper_result_credit"] for row in tables + figures} == {False}


def test_literal_paper_spec_reconstruction_exposes_noncausal_threshold_fit() -> None:
    diagnostics = audit.specification_reconstruction_diagnostics()
    prefix = next(
        row
        for row in diagnostics
        if row["diagnostic"] == "literal_algorithm_prefix_instability"
    )
    assert prefix["observed_value"] == 72
    assert prefix["denominator"] == 126
    assert prefix["native_source_execution"] is False
    prices = 100 * np.exp(np.cumsum(np.linspace(-0.01, 0.02, 180)))
    labels = audit.literal_label_algorithm(prices)
    assert list(labels) == ["price", "ema", "weighted_signal", "label"]
    assert labels["label"].notna().sum() == 146
    assert set(labels["label"].dropna()) == set(audit.ACTIONS)


def test_decision_matrix_orientation_conflicts_with_paper_prose() -> None:
    assert audit.decision_reward("STRONG BUY", "STRONG SELL") == -2.0
    assert audit.decision_reward("STRONG SELL", "STRONG BUY") == -2.25
    assert audit.decision_reward("BUY", "STRONG BUY") == 0.75
    assert audit.decision_reward("BUY", "BUY", scale=2.0) == 2.0
    checks = audit.internal_checks()
    assert Counter(row["status"] for row in checks)["paper_internal_conflict"] == 3
    assert any(row["status"] == "literal_formula_is_not_prefix_stable" for row in checks)


def test_mechanism_ledger_separates_spec_reconstruction_from_native_source() -> None:
    mechanisms = audit.mechanism_conformance()
    gaps = audit.specification_gaps()
    assert len(mechanisms) == 39
    assert sum(row["verified_in_released_native_source"] for row in mechanisms) == 0
    assert sum(row["paper_spec_reconstruction_credit"] for row in mechanisms) == 2
    assert sum(row["paper_result_credit"] for row in mechanisms) == 0
    assert len(gaps) == 15
    assert {row["severity"] for row in gaps} == {"blocking"}


def test_committed_audit_records_zero_native_result_credit() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/trading_r1"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output / "native_execution.json").read_text(encoding="utf-8"))
    tables = read_csv(output / "paper_table_result_conformance.csv")
    figures = read_csv(output / "paper_figure_numeric_conformance.csv")
    source = read_csv(output / "released_source_inventory.csv")
    assert manifest["overall_status"] == (
        "paper_spec_mechanisms_reconstructed_but_zero_of_348_published_result_units_"
        "reproduced_official_release_still_placeholder"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_table_cells_total"] == len(tables) == 312
    assert manifest["paper_figure_numeric_units_total"] == len(figures) == 36
    assert manifest["published_numeric_result_units_total"] == 348
    assert manifest["published_numeric_result_units_with_paper_result_credit"] == 0
    assert manifest["paper_figure_units_internally_consistent_with_rounded_tables"] == 35
    assert manifest["official_repository_commits_total"] == 1
    assert manifest["official_repository_tracked_files_current"] == len(source) == 1
    assert manifest["official_repository_source_code_files_current"] == 0
    assert manifest["public_forks_github_reported"] == 30
    assert manifest["public_forks_accessible_and_audited"] == 29
    assert manifest["public_fork_branch_refs_audited"] == 29
    assert manifest["public_fork_unique_heads_audited"] == 2
    assert manifest["public_fork_unique_commits_beyond_official_history_audited"] == 4
    assert manifest["public_fork_native_trading_r1_pipelines_found"] == 0
    assert manifest["official_huggingface_models_total"] == 0
    assert manifest["official_huggingface_datasets_total"] == 0
    assert manifest["paper_compile_pages"] == 58
    assert manifest["literal_algorithm_changed_prefix_labels"] == 72
    assert native["native_system_execution_attempted"] is False
    assert native["paper_latex_compilation"]["exit_codes"] == [0, 0]
    assert native["paper_latex_compilation"]["paper_result_credit"] is False
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_committed_public_fork_census_finds_only_readme_edits() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/trading_r1"
    branches = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    commits = read_csv(output / "public_fork_unique_commit_inventory.csv")
    census = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))
    assert len(branches) == 29
    assert Counter(row["relation_to_official_head"] for row in branches) == {
        "exact_official_head": 28,
        "descendant_of_official_head": 1,
    }
    assert all(row["commits_behind_official_head"] == "0" for row in branches)
    assert all(row["current_tracked_files"] == "1" for row in branches)
    assert all(row["current_source_code_files"] == "0" for row in branches)
    assert all(row["current_native_result_payload_paths"] == "0" for row in branches)
    assert all(row["native_trading_r1_pipeline_found"] == "False" for row in branches)
    assert all(row["paper_result_credit"] == "False" for row in branches)
    assert len(commits) == 4
    assert all(row["changed_paths"] == "1" for row in commits)
    assert all(row["changed_source_code_paths"] == "0" for row in commits)
    assert all(row["changed_native_result_payload_paths"] == "0" for row in commits)
    assert all(row["authored_after_paper_submission"] == "True" for row in commits)
    assert all(row["exact_paper_author_display_name_match"] == "False" for row in commits)
    assert all(row["native_trading_r1_pipeline_found"] == "False" for row in commits)
    assert all(row["paper_result_credit"] == "False" for row in commits)
    assert census["github_reported_forks"] == 30
    assert census["accessible_public_forks"] == 29
    assert census["inaccessible_or_unlisted_reported_forks"] == 1
    assert census["accessible_branch_refs"] == 29
    assert census["public_tag_refs"] == 0
    assert census["unique_heads"] == 2
    assert census["official_head_exact_refs"] == 28
    assert census["divergent_unique_heads"] == 1
    assert census["unique_commits_beyond_official_history"] == 4
    assert census["unique_trees_beyond_official_history"] == 4
    assert census["unique_blobs_beyond_official_history"] == 4
    assert census["unique_changed_paths"] == 1
    assert census["native_trading_r1_pipelines_found"] == 0
    assert census["paper_result_credit"] is False


def test_pinned_primary_sources_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/trading_r1_source_repo")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/trading_r1_paper")
    if not source.exists() or not paper.exists():
        return
    audit.validate_primary_inputs(source, paper)
    assert audit.released_source_inventory(source) == [
        {
            "path": "README.md",
            "bytes": 49,
            "sha256": audit.SOURCE_README_SHA256,
            "source_code": False,
            "native_result_artifact": False,
        }
    ]
    assert len(audit.source_archive_inventory(paper)) == 29
    branches, commits, census = audit.public_fork_audit(source, paper)
    assert len(branches) == 29
    assert len(commits) == 4
    assert census["native_trading_r1_pipelines_found"] == 0
