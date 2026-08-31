from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_finmem_paper.py"
SPEC = importlib.util.spec_from_file_location("finmem_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_paper_targets_cover_every_table_2_to_5_metric_cell() -> None:
    rows = audit.paper_table_rows()
    assert len(rows) == 235
    assert Counter(row["paper_table"] for row in rows) == {
        2: 160,
        3: 30,
        4: 20,
        5: 25,
    }
    groups = {(row["paper_table"], row["scope"], row["strategy_or_configuration"]) for row in rows}
    assert len(groups) == 47
    assert Counter(row["metric"] for row in rows) == {metric: 47 for metric in audit.METRICS}


def test_table_4_encodes_the_papers_volatility_values_without_repairing_them() -> None:
    rows = audit.volatility_identity_audit()
    mismatches = [row for row in rows if row["status"] == "paper_internal_annualization_mismatch"]
    assert len(rows) == 47
    assert len(mismatches) == 4
    assert {row["paper_table"] for row in mismatches} == {4}
    assert {row["strategy_or_configuration"] for row in mismatches} == {
        "buy_and_hold",
        "self_adaptive",
        "risk_seeking",
        "risk_averse",
    }


def test_committed_audit_distinguishes_history_from_end_to_end_reproduction() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finmem"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_2_5_conformance.csv")
    volatility = read_csv(output / "paper_volatility_identity_audit.csv")
    archive = read_csv(output / "released_archive_inventory.csv")
    author_outputs = read_csv(output / "historical_author_output_conformance.csv")
    action_inventory = read_csv(output / "historical_action_inventory.csv")
    action_reproduction = read_csv(output / "historical_action_metric_reproduction.csv")
    native_metrics = read_csv(output / "historical_native_metric_function_execution.csv")
    paper_versions = read_csv(output / "official_paper_version_inventory.csv")
    paper_sources = read_csv(output / "official_paper_source_inventory.csv")
    table_4_provenance = read_csv(output / "table_4_volatility_provenance.csv")
    table_4_forensics = json.loads((output / "table_4_volatility_forensics.json").read_text(encoding="utf-8"))
    fork_heads = read_csv(output / "public_fork_unique_head_inventory.csv")
    fork_branch_refs = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    fork_summary = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == "author_outputs_partially_verified_not_end_to_end_reproduced"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["end_to_end_agent_result_cells_reproduced"] == 0
    assert manifest["paper_result_rows_total"] == 47
    assert manifest["paper_result_cells_total"] == 235
    assert manifest["official_arxiv_versions_audited"] == 2
    assert manifest["official_arxiv_pdf_pages_pinned"] == 44
    assert manifest["official_table_4_pdf_pages_visually_inspected"] == 2
    assert manifest["official_arxiv_source_files_inventoried"] == 71
    assert manifest["historical_author_output_cells_exact"] == 223
    assert manifest["historical_author_output_cells_one_last_decimal_unit_difference"] == 4
    assert manifest["historical_author_output_cells_corroborated"] == 227
    assert manifest["historical_author_output_cells_conflicted_with_paper"] == 8
    assert manifest["historical_author_output_rows_all_cells_exact"] == 40
    assert manifest["historical_author_output_rows_corroborated"] == 43
    assert manifest["historical_author_output_rows_conflicted_with_paper"] == 4
    assert manifest["historical_action_metric_cells_recomputed"] == 75
    assert manifest["historical_action_metric_cells_matched"] == 67
    assert manifest["historical_action_metric_cells_conflicted_with_paper"] == 8
    assert manifest["historical_action_metric_rows_fully_matched"] == 11
    assert manifest["historical_action_metric_rows_conflicted_with_paper"] == 4
    assert manifest["historical_native_metric_configurations_executed"] == 15
    assert manifest["historical_native_metric_cells_executed"] == 75
    assert manifest["historical_native_metric_cells_matching_audit_adapter"] == 75
    assert manifest["historical_native_metric_cells_matching_paper"] == 67
    assert manifest["historical_native_metric_rows_fully_matching_paper"] == 11
    assert manifest["historical_native_metric_rows_conflicted_with_paper"] == 4
    assert manifest["historical_native_metric_maximum_adapter_error"] < 6e-13
    assert manifest["historical_native_metric_yfinance_version"] == "0.2.32"
    assert manifest["historical_native_metric_live_yfinance_calls"] == 0
    assert manifest["historical_parameterized_main_tables_executed"] == 3
    assert manifest["historical_parameterized_main_configurations_executed"] == 15
    assert manifest["historical_parameterized_main_metric_cells_executed"] == 75
    assert manifest["historical_parameterized_main_cells_matching_calculate_metrics"] == 75
    assert manifest["historical_parameterized_main_maximum_function_error"] < 1e-12
    assert manifest["historical_parameterized_main_output_sha256"] == {
        str(table): digest for table, digest in audit.HISTORICAL_MAIN_OUTPUT_SHA256.items()
    }
    assert manifest["historical_parameterized_main_live_yfinance_calls"] == 0
    assert manifest["source_calculate_metrics_function_operational"] is True
    assert manifest["source_parameterized_metrics_main_operational_with_input_adapter"] is True
    assert manifest["source_parameterized_metrics_main_formulas_changed"] is False
    assert manifest["source_metrics_entrypoint_operational_as_released"] is False
    assert manifest["buy_hold_cells_recomputed"] == 40
    assert manifest["buy_hold_cells_matched"] == 16
    assert manifest["buy_hold_cells_mismatched_against_current_yahoo"] == 24
    assert manifest["current_head_non_buy_hold_cells_without_native_outputs"] == 195
    assert manifest["non_buy_hold_cells_exact_in_historical_author_output"] == 185
    assert manifest["non_buy_hold_cells_corroborated_by_historical_author_output"] == 189
    assert manifest["paper_result_rows_fully_matched"] == 2
    assert manifest["paper_result_rows_mismatched_against_current_yahoo"] == 6
    assert manifest["paper_result_rows_unverifiable"] == 39
    assert manifest["current_head_native_action_or_return_files_shipped"] == 0
    assert manifest["historical_action_csvs_in_public_git_history"] == 18
    history = manifest["historical_repository_audit"]
    assert history["is_shallow_repository"] is False
    assert history["reachable_commits"] == 55
    assert history["reachable_objects"] == 336
    assert history["reachable_blobs"] == 171
    assert history["reachable_trees"] == 110
    assert history["unreachable_objects"] == 0
    assert history["root_commit"] == audit.SOURCE_ROOT_COMMIT
    assert history["historical_artifact_commit"] == audit.HISTORICAL_ARTIFACT_COMMIT
    assert history["historical_tree_files"] == 33
    assert history["historical_action_csvs"] == 18
    assert history["historical_notebook_sha256"] == audit.HISTORICAL_NOTEBOOK_SHA256
    assert history["historical_metrics_sha256"] == audit.HISTORICAL_METRICS_SHA256
    assert history["deletion_commit"] == audit.HISTORICAL_DELETION_COMMIT
    assert history["deleted_tree_files"] == 33
    assert manifest["public_fork_census_date"] == "2026-08-14"
    assert manifest["github_rest_reported_public_forks"] == 192
    assert manifest["graphql_accessible_public_forks"] == 181
    assert manifest["public_fork_accessibility_gap"] == 11
    assert manifest["public_fork_branch_refs_examined"] == 187
    assert manifest["public_fork_unique_heads_examined"] == 20
    assert manifest["public_fork_divergent_heads_examined"] == 11
    assert manifest["public_fork_divergent_extra_commits_examined"] == 45
    assert manifest["public_fork_divergent_changed_paths_examined"] == 299
    assert manifest["public_fork_author_attributed_divergent_heads"] == 0
    assert manifest["public_fork_additional_native_action_paths"] == 1
    assert manifest["public_fork_paper_result_artifacts_discovered"] == 0
    assert manifest["public_fork_paper_result_credit"] is False
    assert manifest["original_paper_news_filings_snapshot_shipped"] is False
    assert manifest["paper_selects_best_risk_profile_on_test_outcome"] is True
    assert manifest["paper_metric_is_self_financing_portfolio_return"] is False
    assert manifest["table_4_disputed_volatility_cells_forensically_traced"] == 8
    assert manifest["table_4_annualized_cells_matching_native_daily_values"] == 4
    assert manifest["table_4_daily_cells_matching_separate_tsla_full_output"] == 2
    assert manifest["table_4_daily_cells_absent_from_all_reachable_source_blobs"] == 2
    assert manifest["table_4_disputed_volatility_cells_receiving_result_credit"] == 0

    assert len(paper_versions) == 2
    assert {row["version"] for row in paper_versions} == {"v1", "v2"}
    assert {row["pdf_pages"] for row in paper_versions} == {"22"}
    assert {row["table_4_pdf_page"] for row in paper_versions} == {"17", "18"}
    assert all(row["table_4_page_visually_inspected"] == "yes" for row in paper_versions)
    assert all(row["table_4_values_verified_in_pdf_text"] == "yes" for row in paper_versions)
    assert all(row["table_4_values_verified_in_primary_tex"] == "yes" for row in paper_versions)
    assert all(row["annualization_equation_verified_in_primary_tex"] == "yes" for row in paper_versions)
    assert all(
        row["table_4_revision_status"] == "same_numeric_values_retained_across_v1_and_v2" for row in paper_versions
    )
    assert len(paper_sources) == 71
    assert Counter(row["version"] for row in paper_sources) == {"v1": 32, "v2": 39}
    assert Counter(row["role"] for row in paper_sources)["paper_primary_tex"] == 2

    assert len(table_4_provenance) == 8
    assert Counter(row["source_relation"] for row in table_4_provenance) == {
        "paper_annualized_cell_equals_preserved_character_daily_value": 4,
        "paper_daily_cell_matches_separate_tsla_full_output_value": 2,
        "paper_only_value_absent_from_all_reachable_source_blobs": 2,
    }
    assert all(row["defensible_paper_result_credit"] == "no" for row in table_4_provenance)
    annual = [row for row in table_4_provenance if row["metric"] == "annualized_volatility_pct"]
    assert all(
        math.isclose(
            float(row["paper_v2_percent_value"]),
            float(row["preserved_character_daily_volatility_pct"]),
            abs_tol=1e-12,
        )
        for row in annual
    )
    absent = {
        row["strategy_or_configuration"]
        for row in table_4_provenance
        if row["source_relation"] == "paper_only_value_absent_from_all_reachable_source_blobs"
    }
    assert absent == {"risk_seeking", "risk_averse"}
    assert table_4_forensics["official_arxiv_versions_audited"] == 2
    assert table_4_forensics["table_4_numeric_values_changed_between_v1_and_v2"] is False
    assert table_4_forensics["reachable_commits_scanned"] == 55
    assert table_4_forensics["reachable_objects_scanned"] == 336
    assert table_4_forensics["reachable_blobs_byte_scanned"] == 171
    assert table_4_forensics["unique_historical_notebook_blobs"] == 1
    assert table_4_forensics["cells_receiving_defensible_paper_result_credit"] == 0

    assert len(fork_branch_refs) == 187
    assert len({row["repository"] for row in fork_branch_refs}) == 181
    assert len({row["head_commit"] for row in fork_branch_refs}) == 20
    assert len(fork_heads) == 20
    assert Counter(row["classification"] for row in fork_heads)["official_public_history_reachable"] == 9
    divergent = [row for row in fork_heads if row["classification"] != "official_public_history_reachable"]
    assert len(divergent) == 11
    assert sum(int(row["extra_commit_count_beyond_official_head"]) for row in divergent) == 47
    assert all(row["official_source_author_identity_match_in_extra_commits"] == "False" for row in divergent)
    assert all(row["paper_result_credit"] == "False" for row in fork_heads)
    minirun = next(row for row in fork_heads if row["head_commit"] == audit.FORK_MINIRUN_HEAD)
    assert minirun["classification"] == ("unattributed_postpaper_tsla_hold_only_minirun_wrong_model_dates_topk")
    assert minirun["final_changed_structured_data_path_count"] == "6"
    checkpoint = next(row for row in fork_heads if row["head_commit"] == audit.FORK_CHECKPOINT_HEAD)
    assert checkpoint["classification"] == ("unattributed_postpaper_tsla_checkpoint_without_action_or_metric_output")
    assert checkpoint["final_changed_structured_data_path_count"] == "0"
    assert fork_summary["github_rest_reported_forks"] == 192
    assert fork_summary["graphql_accessible_forks"] == 181
    assert fork_summary["rest_minus_accessible_fork_gap"] == 11
    assert fork_summary["graphql_accessible_branch_refs"] == 187
    assert fork_summary["unique_heads"] == 20
    assert fork_summary["heads_reachable_from_official_history"] == 9
    assert fork_summary["divergent_heads_reviewed"] == 11
    assert fork_summary["divergent_extra_commits_reviewed"] == 45
    assert fork_summary["divergent_changed_paths_reviewed"] == 299
    assert fork_summary["divergent_heads_matching_official_source_author_identity"] == 0
    assert fork_summary["postpaper_native_action_rows"] == 19
    assert fork_summary["postpaper_native_action_unique_directions"] == [0]
    assert fork_summary["postpaper_native_action_matches_paper_model_dates_topk_or_trials"] is False
    assert fork_summary["known_author_history_paths_deleted_not_newly_contributed"] == 33
    assert fork_summary["paper_result_artifacts_discovered_in_divergent_fork_heads"] == 0
    assert fork_summary["paper_result_credit"] is False
    assert fork_summary["pickle_execution_policy"] == "byte_scan_only_no_deserialization"

    assert len(conformance) == 235
    assert Counter(row["status"] for row in conformance) == {
        "exact_displayed_precision_match": 16,
        "mismatch_against_pinned_2026_yahoo_retrieval": 24,
        "unverifiable_missing_native_action_series": 195,
    }
    buy_hold = [row for row in conformance if row["strategy_or_configuration"] == "buy_and_hold"]
    assert Counter((row["paper_table"], row["status"]) for row in buy_hold) == {
        ("2", "exact_displayed_precision_match"): 3,
        ("2", "mismatch_against_pinned_2026_yahoo_retrieval"): 22,
        ("3", "exact_displayed_precision_match"): 5,
        ("4", "exact_displayed_precision_match"): 3,
        ("4", "mismatch_against_pinned_2026_yahoo_retrieval"): 2,
        ("5", "exact_displayed_precision_match"): 5,
    }

    assert Counter(row["status"] for row in volatility) == {
        "rounding_consistent": 43,
        "paper_internal_annualization_mismatch": 4,
    }
    assert len(archive) == 10
    assert all("agent_action" in row["role"] or "paper_data" in row["role"] for row in archive)
    assert not any(row["role"] in {"native_action", "paper_result"} for row in archive)

    assert len(author_outputs) == 235
    assert Counter(row["status"] for row in author_outputs) == {
        "author_output_exact_displayed_precision_match": 223,
        "author_output_one_last_decimal_unit_difference": 4,
        "paper_conflicts_with_preserved_author_output": 8,
    }
    substantive_conflicts = [
        row for row in author_outputs if row["status"] == "paper_conflicts_with_preserved_author_output"
    ]
    assert {row["paper_table"] for row in substantive_conflicts} == {"4"}
    assert {row["metric"] for row in substantive_conflicts} == {
        "daily_volatility_pct",
        "annualized_volatility_pct",
    }
    assert {row["strategy_or_configuration"] for row in substantive_conflicts} == {
        "buy_and_hold",
        "self_adaptive",
        "risk_seeking",
        "risk_averse",
    }

    assert len(action_inventory) == 18
    assert len({row["path"] for row in action_inventory}) == 18
    assert all(row["commit"] == audit.HISTORICAL_ARTIFACT_COMMIT for row in action_inventory)
    assert all(row["parsed_action_rows"] and row["sha256"] for row in action_inventory)

    assert len(action_reproduction) == 75
    assert Counter(row["status"] for row in action_reproduction) == {
        "historical_action_exact_displayed_precision_match": 67,
        "paper_conflicts_with_historical_action_replay": 8,
    }
    assert Counter((row["paper_table"], row["status"]) for row in action_reproduction) == {
        ("3", "historical_action_exact_displayed_precision_match"): 30,
        ("4", "historical_action_exact_displayed_precision_match"): 12,
        ("4", "paper_conflicts_with_historical_action_replay"): 8,
        ("5", "historical_action_exact_displayed_precision_match"): 25,
    }

    assert len(native_metrics) == 15
    assert Counter(row["paper_table"] for row in native_metrics) == {
        "3": 6,
        "4": 4,
        "5": 5,
    }
    assert {row["source_commit"] for row in native_metrics} == {audit.HISTORICAL_ARTIFACT_COMMIT}
    assert {row["source_sha256"] for row in native_metrics} == {audit.HISTORICAL_METRICS_SHA256}
    assert {row["source_function"] for row in native_metrics} == {"calculate_metrics"}
    assert {row["yfinance_version_imported"] for row in native_metrics} == {"0.2.32"}
    assert {row["live_yfinance_calls"] for row in native_metrics} == {"0"}
    assert {row["all_five_metrics_match_audit_adapter"] for row in native_metrics} == {"True"}
    assert max(float(row["maximum_absolute_error_against_audit_adapter"]) for row in native_metrics) < 6e-13
    assert sum(int(row["paper_cells_matched"]) for row in native_metrics) == 67
    assert sum(row["paper_row_fully_matched"] == "True" for row in native_metrics) == 11
    assert {row["native_agent_result_credit"] for row in native_metrics} == {"False"}
    assert {row["parameterized_main_executed"] for row in native_metrics} == {"True"}
    assert {
        int(row["paper_table"]): row["parameterized_main_output_sha256"] for row in native_metrics
    } == audit.HISTORICAL_MAIN_OUTPUT_SHA256
    assert Counter((row["paper_table"], row["parameterized_main_warning_count"]) for row in native_metrics) == {
        ("3", "5"): 6,
        ("4", "3"): 4,
        ("5", "4"): 5,
    }
    assert {row["parameterized_main_stdout_nonempty"] for row in native_metrics} == {"True"}
    assert max(float(row["parameterized_main_maximum_function_error"]) for row in native_metrics) < 1e-12
    assert {row["parameterized_main_matches_calculate_metrics"] for row in native_metrics} == {"True"}
    assert {row["parameterized_main_input_adapter"] for row in native_metrics} == {
        "get_price_rebound_to_pinned_TSLA_ablation_json;author_local_action_paths_rebound_to_exact_git_blobs"
    }
    assert {row["source_formula_changed"] for row in native_metrics} == {"False"}
    assert {row["hardcoded_dunder_main_block_executed"] for row in native_metrics} == {"False"}

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_native_ledger_credits_historical_actions_without_claiming_common_task_fidelity() -> None:
    rows = read_csv(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == "SYS-FIN-MEM")
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R3"
    assert row["native_dated_signal_or_return_shipped"] == "Y"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A3_US_only_not_six_country"
    assert row["fidelity_class"] == "F2_dated_output_task_incompatible"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:partial_227_of_235_author_output_cells_corroborated_"
        "67_of_75_native_metric_function_cells_reproduced_zero_end_to_end_agent_cells_"
        "181_accessible_forks_187_refs_20_unique_heads_exhausted"
    )
    note = row["concise_evidence_note"]
    assert "223 exact" in note
    assert "18 dated action CSVs" in note
    assert "exact historical calculate_metrics function" in note
    assert "all 75 values matching" in note
    assert "181 accessible forks" in note
    assert "19-row" in note
    assert "not end-to-end FinMem reproduction" in note
