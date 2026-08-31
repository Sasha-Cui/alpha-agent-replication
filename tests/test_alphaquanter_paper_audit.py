from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alphaquanter_paper.py"
SPEC = importlib.util.spec_from_file_location("alphaquanter_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_paper_targets_cover_every_numeric_cell_in_tables_5_to_14() -> None:
    rows = audit.paper_result_rows()
    assert len(rows) == 790
    assert Counter(row["paper_table"] for row in rows) == {
        5: 192,
        6: 9,
        7: 12,
        8: 15,
        10: 216,
        11: 216,
        12: 40,
        13: 45,
        14: 45,
    }
    groups = {
        (row["paper_table"], row["family_or_setting"], row["method"])
        for row in rows
    }
    assert len(groups) == 98


def test_paper_internal_table_discrepancies_are_explicit() -> None:
    rows = audit.paper_internal_consistency()
    assert {
        (row["method"], row["metric"], row["table_5_value"], row["table_10_or_11_value"])
        for row in rows
    } == {
        ("FinRLA2C", "MSFT_arr_pct", 43.15, 43.14),
        ("FinRLA2C", "NVDA_arr_pct", 37.43, 37.42),
        ("FinRLPPO", "MSFT_arr_pct", 43.91, 43.90),
    }


def test_committed_audit_keeps_component_and_agent_results_separate() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/alphaquanter"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_5_8_10_14_conformance.csv")
    datasets = read_csv(output / "released_dataset_inventory.csv")
    labels = read_csv(output / "reward_label_conformance.csv")
    label_summary = read_csv(output / "reward_label_summary.csv")
    label_lineage = read_csv(output / "reward_label_lineage_recovery.csv")
    source = read_csv(output / "source_config_conformance.csv")
    history = read_csv(output / "released_source_history_inventory.csv")
    forks = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    protocols = read_csv(output / "buy_hold_protocol_sensitivity.csv")
    fork_census = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == (
        "not_reproduced_prompt_label_component_and_buy_hold_reconstruction_only"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_result_cells_total"] == 790
    assert manifest["buy_hold_cells_recomputed"] == 34
    assert manifest["buy_hold_cells_matched_current_yahoo_at_display_precision"] == 1
    assert manifest["buy_hold_cells_mismatched_current_yahoo"] == 33
    assert manifest["current_exchange_calendar_test_observations"] == 122
    assert manifest["buy_hold_protocol_sensitivity_cells"] == 84
    assert manifest["buy_hold_protocol_cells_with_paper_result_credit"] == 0
    assert manifest["buy_hold_protocol_display_matches"] == {
        "full_period_released_evaluator|adjusted_close": 0,
        "full_period_released_evaluator|unadjusted_close": 0,
        "rolling_paper_3_calendar_months_step_7_days|adjusted_close": 1,
        "rolling_paper_3_calendar_months_step_7_days|unadjusted_close": 0,
        "rolling_released_60_observations_step_5|adjusted_close": 1,
        "rolling_released_60_observations_step_5|unadjusted_close": 1,
    }
    assert manifest["non_buy_hold_cells_unverifiable"] == 756
    assert manifest["released_prompt_label_rows"] == 2615
    assert manifest["reward_label_exact_numeric_matches_current_yahoo"] == 523
    assert manifest["reward_label_within_1e_6_current_yahoo"] == 525
    assert manifest["reward_label_regime_matches_current_yahoo"] == 2612
    assert manifest["reward_label_regime_mismatches_current_yahoo"] == 3
    assert manifest["reward_label_lineage_recovery_rows"] == 10
    assert manifest["reward_label_lineage_exact_numeric_matches"] == 2615
    assert manifest["reward_label_lineage_total"] == 2615
    assert manifest["reward_label_lineage_algebraic_nullity"] == 7
    assert (
        manifest[
            "reward_label_lineage_absolute_author_price_level_uniquely_identified"
        ]
        is False
    )
    assert manifest["reward_label_lineage_paper_result_credit"] == 0
    assert manifest["paper_test_action_rows_shipped"] == 0
    assert manifest["native_training_checkpoints_shipped"] is False
    assert manifest["released_complete_verl_runtime"] is False
    assert manifest["audit_called_llm_or_paid_external_api"] is False
    source_history = manifest["released_source_history"]
    assert source_history["public_commits_reviewed"] == 2
    assert source_history["public_branches_reviewed"] == 1
    assert source_history["public_tags"] == 0
    assert source_history["public_releases"] == 0
    assert source_history["unreachable_git_objects"] == 0
    assert source_history["historical_unique_paths_reviewed"] == 31
    assert source_history["initial_commit_contains_complete_released_tree"] is True
    assert source_history["later_commit_changes_only_readme_citations_and_paper_link"] is True
    assert source_history[
        "historical_checkpoint_result_output_log_action_trajectory_rating_paths"
    ] == 0
    assert source_history["historical_native_paper_result_payloads"] == 0
    assert source_history["history_complete_for_pinned_public_refs"] is True
    assert manifest["public_forks_accessible"] == 11
    assert manifest["public_fork_branch_refs_audited"] == 11
    assert manifest["public_fork_unique_heads_audited"] == 2
    assert manifest["public_fork_divergent_heads_audited"] == 0
    assert manifest["public_fork_unique_commits_beyond_official_history"] == 0
    assert manifest["public_fork_native_result_payloads_found"] == 0
    assert len(history) == 2
    assert [row["commit"] for row in history] == list(audit.PUBLIC_HISTORY_COMMITS)
    assert history[0]["changed_paths_relative_to_parent"] == "31"
    assert history[1]["changed_paths_relative_to_parent"] == "1"
    assert history[1]["evidence_role"] == "readme_citation_and_paper_link_update_only"
    assert all(row["native_paper_result_payload_present"] == "False" for row in history)
    assert all(row["paper_result_credit"] == "False" for row in history)
    assert len(forks) == 11
    assert Counter(row["relation_to_official_head"] for row in forks) == {
        "official_head_exact": 1,
        "official_history_ancestor": 10,
    }
    assert Counter(row["commits_behind_official"] for row in forks) == {"0": 1, "1": 10}
    assert all(row["unique_commits_beyond_official_history"] == "0" for row in forks)
    assert all(row["unique_blobs_beyond_official_history"] == "0" for row in forks)
    assert all(row["native_result_payload_found"] == "False" for row in forks)
    assert fork_census["census_date"] == audit.PUBLIC_FORK_CENSUS_DATE
    assert fork_census["github_rest_reported_forks"] == 11
    assert fork_census["accessible_public_forks"] == 11
    assert fork_census["accessible_branch_refs"] == 11
    assert fork_census["unique_heads"] == 2
    assert fork_census["divergent_unique_heads"] == 0
    assert fork_census["native_result_payloads_found"] == 0
    assert fork_census["paper_result_credit"] is False

    assert Counter(row["status"] for row in conformance) == {
        "exact_displayed_precision_match_current_yahoo": 1,
        "mismatch_against_pinned_current_yahoo": 33,
        "unverifiable_missing_token_and_cost_logs": 9,
        "unverifiable_missing_ratings_and_sample": 12,
        "unverifiable_missing_native_action_or_result_path": 735,
    }
    assert Counter(row["status"] for row in labels) == {
        "exact_current_yahoo_numeric_match": 523,
        "numeric_snapshot_difference_same_reward_regime": 2089,
        "current_yahoo_difference_crosses_reward_threshold": 3,
    }

    assert len(datasets) == 3
    assert [(row["rows"], row["distinct_trading_dates"]) for row in datasets] == [
        ("1975", "395"),
        ("640", "128"),
        ("0", "0"),
    ]
    assert datasets[-1]["status"] == "missing_paper_test_prompts_labels_and_actions"
    assert len(label_summary) == 10
    assert sum(int(row["exact_numeric_matches"]) for row in label_summary) == 523
    assert sum(int(row["reward_regime_mismatches"]) for row in label_summary) == 3
    validation = [row for row in label_summary if "validation" in row["paper_role"]]
    assert sum(int(row["reward_regime_mismatches"]) for row in validation) == 0

    assert Counter(row["paper_role"] for row in label_lineage) == {
        "paper_train": 5,
        "paper_validation_released_as_test": 5,
    }
    assert Counter(
        (
            row["paper_role"],
            row["price_path_variables"],
            row["label_equations"],
        )
        for row in label_lineage
    ) == {
        ("paper_train", "402", "395"): 5,
        ("paper_validation_released_as_test", "135", "128"): 5,
    }
    assert sum(int(row["released_labels"]) for row in label_lineage) == 2615
    assert sum(int(row["exact_numeric_matches"]) for row in label_lineage) == 2615
    assert max(
        float(row["maximum_absolute_error"]) for row in label_lineage
    ) < 4e-15
    assert {
        (row["paper_role"], row["ticker"]): row["cent_path_sha256"]
        for row in label_lineage
    } == audit.LABEL_LINEAGE_PATH_SHA256
    assert {
        row["algebraic_nullity_before_market_reference"] for row in label_lineage
    } == {"7"}
    assert all(
        float(row["scale_interval_lower"])
        < float(row["scale_interval_midpoint"])
        < float(row["scale_interval_upper"])
        for row in label_lineage
    )
    assert {
        row["absolute_author_price_level_uniquely_identified"]
        for row in label_lineage
    } == {"False"}
    assert {row["paper_2025_test_snapshot_recovered"] for row in label_lineage} == {
        "False"
    }
    assert {row["paper_result_credit"] for row in label_lineage} == {"False"}

    assert len(source) == 26
    assert Counter(row["status"] for row in source) == {
        "match": 7,
        "missing": 7,
        "calendar_count_matches_inputs_missing": 1,
        "mismatch": 3,
        "paper_underspecified": 2,
        "trading_calendar_match": 1,
        "values_match_role_mislabeled": 1,
        "incomplete": 1,
        "semantic_approximation": 1,
        "missing_original_inputs": 1,
        "not_operational_without_upstream_merge": 1,
    }

    assert len(protocols) == 84
    assert {row["paper_result_credit"] for row in protocols} == {"False"}
    errors = manifest["buy_hold_protocol_aggregate_absolute_error"]
    assert min(errors, key=errors.get) == (
        "rolling_released_60_observations_step_5|unadjusted_close"
    )

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_buy_hold_reconstruction_preserves_released_accounting() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/alphaquanter"
    rows = read_csv(output / "buy_hold_reconstruction.csv")
    assert len(rows) == 5
    tsla = next(row for row in rows if row["ticker"] == "TSLA")
    assert math.isclose(float(tsla["rolling_arr_pct"]), 45.70765313511037)
    assert math.isclose(float(tsla["full_mdd_pct"]), 48.18673442760602)
    result_cells = read_csv(output / "tables_5_8_10_14_conformance.csv")
    matches = [
        row
        for row in result_cells
        if row["status"] == "exact_displayed_precision_match_current_yahoo"
    ]
    assert [(row["paper_table"], row["method"], row["metric"]) for row in matches] == [
        ("12", "Buy & Hold", "TSLA_arr_pct")
    ]


def test_global_evidence_route_includes_protocol_sensitivity_boundary() -> None:
    status = (
        "paper_audit:completed_one_of_790_current_snapshot_buy_hold_match_"
        "2615_of_2615_released_reward_labels_recovered_"
        "122_sessions_84_protocol_sensitivity_cells_zero_paper_time_credit_"
        "11_forks_11_refs_2_official_history_heads_exhausted"
    )
    native = read_csv(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    native_row = next(row for row in native if row["system_id"] == "SYS-ALPHA-QUANTER")
    assert native_row["targeted_execution_audit_status"] == status
    note = native_row["concise_evidence_note"]
    assert "all 2,615 numeric labels exactly" in note
    assert "seven unconstrained path degrees" in note
    assert "paper-stated 122 sessions" in note
    assert "84-cell sensitivity" in note
    assert "aggregate error 1.038" in note
    assert "58.539 for the literal rule" in note
    assert "zero paper-time credit" in note

    routes = read_csv(
        ROOT
        / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    route = next(
        row for row in routes
        if row["reachable_public_code_system_ids"] == "SYS-ALPHA-QUANTER"
    )
    assert route["native_execution_audit_status"] == status
    blocker = route["precise_native_or_access_blocker"]
    assert "all 2,615 numeric labels exactly" in blocker
    assert "price-ratio lineage" in blocker
    assert "paper-stated 122 sessions" in blocker
    assert "84-cell sensitivity" in blocker
    assert "zero paper-time credit" in blocker
