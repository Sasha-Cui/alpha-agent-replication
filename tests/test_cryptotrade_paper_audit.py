from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_cryptotrade_paper.py"
SPEC = importlib.util.spec_from_file_location("cryptotrade_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_paper_targets_cover_every_table_2_to_4_metric_cell() -> None:
    rows = audit.paper_result_rows()
    assert len(rows) == 3 * 13 * 3 * 4 == 468
    assert {(row["asset"], row["strategy"], row["regime"]) for row in rows}
    counts = Counter(row["strategy"] for row in rows)
    assert set(counts.values()) == {36}
    assert set(audit.TRADITIONAL_STRATEGIES) | set(audit.TIME_SERIES_STRATEGIES) | set(audit.LLM_STRATEGIES) == set(
        counts
    )


def test_paper_ablation_conflict_is_encoded_without_resolving_it() -> None:
    assert audit.PAPER_ABLATION["full"] == (28.47, 0.23)
    rows = audit.paper_result_rows()
    btc = {
        row["metric"]: row["paper_value"]
        for row in rows
        if row["asset"] == "btc" and row["strategy"] == "gpt_4o" and row["regime"] == "bull"
    }
    eth = {
        row["metric"]: row["paper_value"]
        for row in rows
        if row["asset"] == "eth" and row["strategy"] == "gpt_4o" and row["regime"] == "bull"
    }
    assert audit.PAPER_ABLATION["full"] == (
        btc["total_return_pct"],
        btc["sharpe_ratio"],
    )
    assert audit.PAPER_ABLATION["full"] != (
        eth["total_return_pct"],
        eth["sharpe_ratio"],
    )
    assert len(audit.PAPER_ABLATION) * 2 == 12


def test_committed_audit_is_partial_and_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/cryptotrade"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_2_4_conformance.csv")
    selection = read_csv(output / "parameter_selection_audit.csv")
    diagnosis = read_csv(output / "traditional_mismatch_diagnosis.csv")
    history = read_csv(output / "source_history_inventory.csv")
    fork_divergence = read_csv(output / "public_fork_divergence_inventory.csv")
    traces = read_csv(output / "author_history_llm_trace_audit.csv")
    output_artifacts = read_csv(output / "author_history_output_artifact_census.csv")
    ablation_traces = read_csv(output / "table_5_author_trace_audit.csv")
    ablation = read_csv(output / "table_5_conformance.csv")

    assert manifest["overall_status"] == "partial_reproduction_traditional_plus_author_llm_traces"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_result_metric_cells_total"] == 480
    assert manifest["paper_tables_2_4_metric_cells_total"] == 468
    assert manifest["paper_table_5_metric_cells_total"] == 12
    assert manifest["native_deterministic_metric_cells_recomputed"] == 180
    assert manifest["native_deterministic_metric_cells_matched"] == 174
    assert manifest["native_deterministic_metric_cells_mismatched"] == 6
    assert manifest["author_history_llm_metric_cells_corroborated"] == 40
    assert manifest["author_history_llm_rows_corroborated"] == 10
    assert manifest["author_history_llm_rows_numeric_match_but_no_credit"] == 6
    assert manifest["paper_metric_cells_corroborated_total"] == 214
    assert manifest["author_history_model_mismatch_traces_reassignment_checked"] == 5
    assert manifest["author_history_declared_model_metric_cells_checked"] == 20
    assert manifest["author_history_declared_model_metric_cells_matching"] == 1
    assert manifest["author_history_declared_model_complete_rows_matching"] == 0
    assert manifest["paper_numeric_evidence_correspondences_total"] == 226
    assert manifest["author_history_numeric_metric_cells_corresponding"] == 52
    assert manifest["paper_result_metric_cells_unverifiable"] == 260
    assert manifest["paper_strategy_regime_or_ablation_rows_total"] == 123
    assert manifest["paper_strategy_regime_rows_fully_matched"] == 53
    assert manifest["paper_strategy_regime_rows_mismatched"] == 2
    assert manifest["paper_strategy_regime_rows_unverifiable"] == 62
    assert manifest["full_period_llm_result_logs_shipped_in_official_release"] is False
    assert manifest["matching_full_period_llm_result_traces_recovered_from_paper_author_history"] is True
    assert manifest["paper_author_history_commit"] == audit.AUTHOR_HISTORY_COMMIT
    assert manifest["paper_author_history_commits_audited"] == 89
    assert manifest["paper_author_history_unique_output_blobs_audited"] == 83
    assert manifest["paper_author_history_output_blob_bytes_audited"] == 209739069
    assert manifest["paper_author_history_final_return_sharpe_summaries_audited"] == 1371
    assert manifest["paper_author_history_output_blobs_naming_time_series_model"] == 0
    assert manifest["paper_author_history_output_blobs_matching_time_series_return_sharpe_pair"] == 0
    assert manifest["full_period_time_series_result_logs_shipped"] is False
    assert manifest["source_contains_hardcoded_credential_literal"] is False
    assert manifest["audit_imported_or_used_credential_module"] is False
    assert manifest["original_anonymous_source_status_checked_2026_08_13"] == "http_410_repository_expired"
    assert manifest["public_source_history_commits_audited"] == 11
    assert manifest["public_source_history_result_or_log_paths"] == 0
    assert manifest["public_fork_census_checked_at"] == "2026-08-14"
    assert manifest["public_forks_total"] == 37
    assert manifest["public_fork_branch_refs_total"] == 39
    assert manifest["public_fork_branch_ref_sequence_sha256"] == (
        "5c3c428ac7d6a3c2432c004ce2288f75081ae632abffb9a4128c762fcbe00bd9"
    )
    assert manifest["public_fork_branch_refs_reachable_from_official_or_author_history"] == 35
    assert manifest["public_divergent_fork_heads_total"] == 4
    assert manifest["public_divergent_fork_heads_author_attributed"] == 0
    assert manifest["public_divergent_fork_result_or_log_paths_total"] == 7
    assert manifest["public_divergent_fork_paper_result_credit_paths_total"] == 0
    assert manifest["paper_ablation_rows"] == 6
    assert manifest["paper_ablation_metric_cells_total"] == 12
    assert manifest["paper_ablation_author_history_numeric_correspondences"] == 12
    assert manifest["paper_ablation_historical_code_action_replays_exact"] == 6
    assert manifest["paper_ablation_method_faithful_metric_cells"] == 0
    assert manifest["paper_ablation_rows_with_model_identity_match"] == 0
    assert manifest["paper_ablation_rows_with_asset_identity_match"] == 5
    assert manifest["paper_ablation_full_eth_context_candidate_return_pct"] == 28.11
    assert manifest["paper_ablation_full_eth_context_candidate_sharpe_ratio"] == 0.08

    assert len(conformance) == 468
    statuses = Counter(row["status"] for row in conformance)
    assert statuses == {
        "exact_displayed_precision_match": 174,
        "author_trace_exact_metric_and_native_state_replay": 40,
        "mismatch": 6,
        "unverifiable_no_recovered_author_trace": 44,
        "unverifiable_no_shipped_full_period_output": 180,
        "unverifiable_trace_model_or_period_conflict": 24,
    }
    mismatches = [row for row in conformance if row["status"] == "mismatch"]
    assert {(row["asset"], row["strategy"], row["regime"]) for row in mismatches} == {
        ("eth", "sma", "sideways"),
        ("sol", "sma", "bear"),
    }
    sol = [row for row in mismatches if row["asset"] == "sol"]
    eth = [row for row in mismatches if row["asset"] == "eth"]
    assert {row["metric"] for row in sol} == set(audit.METRICS)
    assert {row["metric"] for row in eth} == {
        "daily_return_mean_pct",
        "daily_return_std_pct",
    }

    assert len(diagnosis) == 6
    assert Counter(row["numeric_lineage"] for row in diagnosis) == {
        "released_data_counterfactual_not_method_faithful": 4,
        "paper_internal_copy_pattern": 2,
    }
    assert all(row["method_faithful_replication_credit"] == "no" for row in diagnosis)
    sol_diagnosis = [row for row in diagnosis if row["asset"] == "sol"]
    assert all(row["period_1_display_match"] == "yes" for row in sol_diagnosis)
    eth_diagnosis = [row for row in diagnosis if row["asset"] == "eth"]
    assert all(row["duplicated_paper_cell"].startswith("eth|sma|bear|") for row in eth_diagnosis)

    assert len(history) == 11
    assert history[0]["commit"] == audit.SOURCE_ROOT_COMMIT
    assert history[-1]["commit"] == audit.SOURCE_COMMIT
    assert all(row["result_or_log_paths"] == "0" for row in history)
    assert sum(row["run_baseline_present"] == "True" for row in history) == 8

    assert len(fork_divergence) == 4
    assert {row["head_commit"] for row in fork_divergence} == {
        "685a33ae9e332c2aff7851c3b2ecaff7137136c9",
        "53ae996cd0232b43d3aef9ec49cf3bb22b017ac4",
        "f8a43b39d922f0f1b468855f63e224235b729d24",
        "3932f2d4421e1eb423a112f715fd34abaa6c65f6",
    }
    assert [int(row["divergent_commits"]) for row in fork_divergence] == [1, 2, 29, 2]
    assert [int(row["changed_paths"]) for row in fork_divergence] == [8, 409, 1931, 2]
    assert [int(row["result_or_log_paths"]) for row in fork_divergence] == [3, 4, 0, 0]
    assert {row["attribution"] for row in fork_divergence} == {"unaffiliated"}
    assert {row["paper_result_credit"] for row in fork_divergence} == {"False"}

    credited = [row for row in traces if row["credit_status"].startswith("credited")]
    diagnostic = [row for row in traces if row["credit_status"].startswith("diagnostic")]
    assert len(traces) == 16
    assert len(credited) == 10
    assert len(diagnostic) == 6
    assert all(row["action_replay_exact"] == "True" for row in traces)
    assert all(float(row["action_replay_maximum_absolute_state_error"]) == 0 for row in traces)
    assert Counter(row["model_identity_status"] for row in diagnostic) == {
        "mismatch": 5,
        "match": 1,
    }
    assert sum(row["full_period_trace"] == "False" for row in diagnostic) == 1
    assert all(row["model_identity_status"] == "match" for row in credited)
    assert all(row["full_period_trace"] == "True" for row in credited)
    reassignment = [
        row for row in diagnostic
        if row["trace_declared_model_reassignment_required"] == "True"
    ]
    assert len(reassignment) == 5
    assert {row["trace_declared_model_paper_strategy"] for row in reassignment} == {
        "gpt_3_5_turbo"
    }
    assert sum(int(row["trace_declared_model_metric_cells_matching"]) for row in reassignment) == 1
    assert {row["trace_declared_model_complete_paper_row_match"] for row in reassignment} == {"False"}
    assert {row["trace_declared_model_reassignment_required"] for row in credited} == {"False"}
    assert {row["trace_declared_model_complete_paper_row_match"] for row in credited} == {"True"}

    assert len(output_artifacts) == 83
    assert sum(int(row["blob_bytes"]) for row in output_artifacts) == 209739069
    assert sum(int(row["final_return_sharpe_summaries"]) for row in output_artifacts) == 1371
    assert {row["exact_time_series_model_tokens"] for row in output_artifacts} == {""}
    assert {row["paper_time_series_return_sharpe_pair_matches"] for row in output_artifacts} == {"0"}
    assert {row["status"] for row in output_artifacts} == {"no_time_series_model_identity_or_paper_return_sharpe_pair"}

    assert len(ablation_traces) == 7
    selected_ablation = [row for row in ablation_traces if row["trace_role"] == "selected_numeric_correspondence"]
    context_ablation = [row for row in ablation_traces if row["trace_role"] == "eth_full_prompt_context_candidate"]
    assert len(selected_ablation) == 6 and len(context_ablation) == 1
    assert sum(int(row["paper_metric_cells_matching"]) for row in selected_ablation) == 12
    assert {row["historical_code_action_replay_exact"] for row in ablation_traces} == {"True"}
    assert {row["action_replay_maximum_absolute_state_error"] for row in ablation_traces} == {"0.0"}
    assert {row["model_identity_status"] for row in selected_ablation} == {"mismatch"}
    assert Counter(row["asset_identity_status"] for row in selected_ablation) == {
        "match": 5,
        "mismatch": 1,
    }
    assert context_ablation[0]["trace_return_pct"] == "28.11"
    assert context_ablation[0]["trace_sharpe_ratio"] == "0.08"
    assert context_ablation[0]["paper_metric_cells_matching"] == "0"
    assert {row["paper_method_faithful_credit"] for row in ablation_traces} == {"False"}

    assert len(ablation) == 12
    assert Counter(row["paper_variant"] for row in ablation) == {
        "full": 2,
        "without_reflection": 2,
        "without_news": 2,
        "without_transaction_statistics": 2,
        "without_technical": 2,
        "base": 2,
    }
    assert {row["author_numeric_correspondence"] for row in ablation} == {"True"}
    assert {row["historical_code_action_replay_exact"] for row in ablation} == {"True"}
    assert {row["paper_method_faithful_credit"] for row in ablation} == {"False"}

    assert len(selection) == 6
    assert Counter(row["status"] for row in selection) == {
        "selection_rule_mismatch": 5,
        "selection_rule_match": 1,
    }
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected
