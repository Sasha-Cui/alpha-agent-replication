from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/p1gpt"
SPEC = importlib.util.spec_from_file_location(
    "audit_p1gpt_paper", ROOT / "scripts/audit_p1gpt_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_table_denominator_is_exhaustive_and_fail_closed() -> None:
    ledger = audit.published_result_ledger()
    assert len(ledger) == 72
    assert Counter(row["result_kind"] for row in ledger) == {
        "baseline_result": 60,
        "native_p1gpt_result": 12,
    }
    assert {row["method"] for row in ledger} == {
        "B&H", "MACD", "KDJ+RSI", "ZMR", "SMA", "P1GPT"
    }
    assert all(row["exact_native_agent_pipeline_regeneration"] is False for row in ledger)
    assert all(row["paper_result_credit"] is False for row in ledger)


def test_manifest_separates_recalculation_from_native_reproduction() -> None:
    data = manifest()
    assert data["full_paper_reproduced"] is False
    assert data["published_table_result_cells"] == 72
    assert data["displayed_table_cells_recalculated_or_checked"] == 50
    assert data["displayed_table_cells_exactly_verified"] == 46
    assert data["p1gpt_cells_checked_from_author_plot_outputs"] == 12
    assert data["p1gpt_cells_verified_from_author_plot_outputs"] == 11
    assert data["baseline_cells_recalculated"] == 36
    assert data["baseline_cells_independently_recalculated"] == 35
    assert data["p1gpt_sharpe_joint_admissible_integer_annualization_days"] == [251]
    assert data["rule_baseline_sharpe_joint_admissible_integer_annualization_days"] == [252]
    assert data["single_sharpe_annualization_convention_recovers_all_recomputed_cells"] is False
    assert data["single_starting_capital_recovers_googl_buy_hold_cr_and_mdd"] is False
    assert data["unsupported_kdj_rsi_zmr_cells"] == 22
    assert data["unsupported_kdj_rsi_zmr_cells_with_author_raster_contradiction"] == 2
    assert data["strategy_raster_curve_mdd_rows_checked"] == 6
    assert data["strategy_raster_curve_mdd_calibration_rows_within_0_25pp"] == 4
    assert data["strategy_raster_curve_mdd_conflicts"] == 2
    assert data["native_p1gpt_result_cells_faithfully_regenerated_end_to_end"] == 0
    assert data["native_p1gpt_agent_decisions_independently_regenerated"] == 0
    assert data["direct_lookahead_counterexamples"] == 1


def test_primary_source_bundle_contains_documents_not_an_experiment() -> None:
    inventory = rows("paper_source_inventory.csv")
    assert len(inventory) == 12
    assert {row["paper_version"] for row in inventory} == {"2510.23032v1"}
    assert all(row["operational_agent_or_backtest_code"] == "False" for row in inventory)
    assert all(row["raw_machine_readable_result_array"] == "False" for row in inventory)
    assert all(row["paper_result_reproduction_credit"] == "False" for row in inventory)


def test_author_assets_are_correspondence_not_native_replay() -> None:
    figures = rows("author_figure_inventory.csv")
    assert len(figures) == 7
    assert Counter(row["asset_kind"] for row in figures) == {
        "architecture_diagram": 1,
        "author_result_plot": 4,
        "author_case_report": 2,
    }
    assert sum(row["author_rendered_output_correspondence"] == "True" for row in figures) == 6
    assert all(
        row["underlying_agent_request_response_or_source_array_shipped"] == "False"
        for row in figures
    )
    assert all(row["faithfully_regenerated_from_native_agent_pipeline"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_recovered_cells_record_two_real_discrepancies() -> None:
    checks = rows("result_recovery_checks.csv")
    assert len(checks) == 48
    assert Counter(row["method"] for row in checks) == {
        "B&H": 12, "MACD": 12, "SMA": 12, "P1GPT": 12
    }
    matched = [row for row in checks if row["display_rounding_exact_match"] == "True"]
    mismatched = [row for row in checks if row["display_rounding_exact_match"] == "False"]
    assert len(matched) == 46
    assert {(row["method"], row["ticker"], row["metric"]) for row in mismatched} == {
        ("B&H", "GOOGL", "MDD"),
        ("P1GPT", "AAPL", "SR"),
    }
    assert next(row for row in mismatched if row["method"] == "B&H")["calculated_value"].startswith("6.136")
    assert next(row for row in mismatched if row["method"] == "P1GPT")["calculated_value"].startswith("3.387")
    assert all(row["native_agent_pipeline_executed"] == "False" for row in checks)
    assert all(row["paper_time_data_snapshot_shipped"] == "False" for row in checks)
    assert all(row["paper_result_reproduction_credit"] == "False" for row in checks)


def test_author_plot_positions_are_output_values_not_agent_decisions() -> None:
    positions = rows("recovered_author_plot_positions.csv")
    assert Counter(row["ticker"] for row in positions) == {
        "AAPL": 166, "GOOGL": 166, "TSLA": 166
    }
    assert {
        ticker: max(int(row["recovered_author_plotted_position"]) for row in positions if row["ticker"] == ticker)
        for ticker in ("AAPL", "GOOGL", "TSLA")
    } == {"AAPL": 3, "GOOGL": 7, "TSLA": 2}
    assert all(row["agent_decision_or_rationale_recovered"] == "False" for row in positions)
    assert all(row["paper_result_credit"] == "False" for row in positions)


def test_author_strategy_raster_contradicts_two_baseline_mdds() -> None:
    raster = rows("strategy_raster_curve_forensics.csv")
    assert len(raster) == 6
    assert {row["method"] for row in raster} == {
        "B&H", "MACD", "KDJ+RSI", "ZMR", "SMA", "P1GPT"
    }
    calibrated = [
        row for row in raster
        if row["within_0_25pp_calibration_tolerance"] == "True"
    ]
    assert {row["method"] for row in calibrated} == {"B&H", "MACD", "SMA", "P1GPT"}
    conflicts = [
        row for row in raster
        if row["status"] == "author_raster_path_materially_conflicts_with_table_mdd"
    ]
    assert {row["method"] for row in conflicts} == {"KDJ+RSI", "ZMR"}
    values = {row["method"]: row for row in conflicts}
    assert 9.9 < float(values["KDJ+RSI"]["raster_center_path_MDD_pct"]) < 10.1
    assert float(values["KDJ+RSI"]["paper_MDD_pct"]) == 1.78
    assert 13.1 < float(values["ZMR"]["raster_center_path_MDD_pct"]) < 13.3
    assert float(values["ZMR"]["paper_MDD_pct"]) == 5.46
    assert all(
        int(row["raster_center_path_peak_x"])
        < int(row["raster_center_path_trough_x"])
        for row in raster
    )
    assert all(abs(float(row["endpoint_calibration_residual_pixels"])) < 0.5 for row in raster)
    assert {row["native_strategy_or_agent_pipeline_executed"] for row in raster} == {"False"}
    assert {row["paper_result_credit"] for row in raster} == {"False"}


def test_present_day_market_snapshots_never_receive_paper_time_credit() -> None:
    snapshots = rows("market_snapshot_checks.csv")
    assert {row["ticker"] for row in snapshots} == {"AAPL", "GOOGL", "TSLA"}
    assert {row["rows"] for row in snapshots} == {"166"}
    assert {row["first_date"] for row in snapshots} == {"2025-02-03"}
    assert {row["last_date"] for row in snapshots} == {"2025-09-30"}
    assert all(row["paper_time_snapshot"] == "False" for row in snapshots)
    assert all(row["exact_paper_data_source_identified"] == "False" for row in snapshots)
    assert all(row["paper_result_credit"] == "False" for row in snapshots)


def test_metric_convention_forensics_do_not_promote_conditional_matches() -> None:
    evidence = json.loads(
        (AUDIT_DIR / "metric_convention_forensics.json").read_text(encoding="utf-8")
    )
    sharpe = evidence["sharpe_annualization"]
    assert len(sharpe["cell_bounds"]) == 12
    assert sharpe["group_intersections"]["p1gpt_author_plot_rows"][
        "joint_admissible_integer_days_240_to_260"
    ] == [251]
    assert sharpe["group_intersections"]["recomputed_rule_baselines"][
        "joint_admissible_integer_days_240_to_260"
    ] == [252]
    assert sharpe["group_intersections"]["all_recomputed_rows"][
        "joint_interval_nonempty"
    ] is False
    assert sharpe["single_common_convention_recovers_all_12_cells"] is False
    assert sharpe["paper_result_credit"] is False
    googl = evidence["googl_buy_hold_capital_consistency"]
    cr_low, cr_high = googl["starting_capital_interval_matching_CR_at_two_decimals"]
    mdd_low, mdd_high = googl["starting_capital_interval_matching_MDD_at_two_decimals"]
    assert 998 < cr_low < cr_high < 1001
    assert 956 < mdd_low < mdd_high < 958
    assert cr_low > mdd_high
    assert googl["single_constant_starting_capital_recovers_both_cells"] is False
    assert googl["paper_result_credit"] is False


def test_public_web_client_is_attributable_r3_component_not_result_pipeline() -> None:
    files = rows("public_source_file_inventory.csv")
    assert len(files) == 38
    assert sum(row["source_kind"] == "python" for row in files) == 22
    assert all(row["paper_agent_or_backtest_result_generator"] == "False" for row in files)
    execution = json.loads(
        (AUDIT_DIR / "public_component_execution.json").read_text(encoding="utf-8")
    )
    assert execution["repository"] == "https://github.com/P1GPT/web_demo"
    assert execution["repeated_archive_byte_identical"] is True
    assert execution["python_files_compiled"] == 22
    assert execution["python_compile_exit"] == 0
    assert execution["static_fidelity_tier"] == "R3"
    assert execution["client_prompt_cards"] == 5
    assert execution["paper_daily_prompt_present"] is False
    assert execution["model_service_source_shipped"] is False
    assert execution["full_service_started"] is False
    assert execution["paper_result_credit"] is False


def test_complete_public_history_contains_no_paper_result_pipeline() -> None:
    history = rows("source_history_inventory.csv")
    assert len(history) == 36
    assert history[0]["commit_sha"] == "1140ce0afd741becd43d4e0a91acad4f8d7e35b7"
    assert {head for row in history for head in row["reachable_branch_heads"].split(";")} >= {
        "origin/main",
        "origin/develop",
        "origin/gke/test",
    }
    assert all(row["candidate_paper_pipeline_paths"] == "" for row in history)
    assert all(row["paper_specific_content_paths"] == "" for row in history)
    assert all(row["native_p1gpt_result_pipeline_found"] == "False" for row in history)
    assert all(row["paper_result_credit"] == "False" for row in history)


def test_complete_public_fork_surface_adds_no_divergent_evidence() -> None:
    data = manifest()
    branches = rows("public_fork_branch_ref_snapshot.csv")
    heads = rows("public_fork_unique_head_inventory.csv")
    census = json.loads((AUDIT_DIR / "public_fork_census.json").read_text(encoding="utf-8"))
    assert data["public_fork_census_date"] == "2026-08-14"
    assert data["public_forks_reported_by_github_rest"] == 1
    assert data["public_forks_accessible_via_graphql"] == 1
    assert data["public_fork_branch_refs_audited"] == 1
    assert data["public_fork_unique_heads_audited"] == 1
    assert data["public_fork_heads_reachable_from_audited_official_history"] == 1
    assert data["public_fork_divergent_heads_audited"] == 0
    assert data["public_fork_native_result_artifacts_found"] is False
    assert data["public_fork_paper_result_credit"] is False
    assert len(branches) == len(heads) == 1
    assert branches[0]["repository"] == audit.PUBLIC_FORK_REPOSITORY
    assert branches[0]["head_commit"] == audit.PUBLIC_FORK_HEAD
    assert heads[0]["extra_commit_count_beyond_official_main"] == "0"
    assert heads[0]["head_already_exhausted_in_official_history"] == "True"
    assert heads[0]["classification"] == "official_main_history_reachable_no_divergence"
    assert heads[0]["paper_result_credit"] == "False"
    assert census["heads_reachable_from_exhaustively_audited_official_history"] == 1
    assert census["divergent_heads_reviewed"] == 0
    assert census[
        "native_agent_prompt_request_response_signal_return_or_result_paths_discovered"
    ] == 0
    assert census["exact_paper_result_table_or_figure_paths_discovered"] == 0
    assert census["paper_result_credit"] is False


def test_live_public_fork_census_when_bouchet_history_is_available() -> None:
    history_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/p1gpt_web_demo_history")
    if not history_root.exists():
        return
    branches, heads, census = audit.public_fork_census(history_root)
    assert len(branches) == len(heads) == 1
    assert census["heads_reachable_from_exhaustively_audited_official_history"] == 1
    assert census["divergent_heads_reviewed"] == 0
    assert census["paper_result_credit"] is False


def test_cited_protocol_does_not_supply_missing_baseline_parameters() -> None:
    lineage = rows("cited_protocol_lineage.csv")
    assert len(lineage) == 4
    official = [row for row in lineage if row["available_by_p1gpt_v1"] == "True"]
    assert len(official) == 3
    assert all(
        row["kdj_rsi_parameters_or_code"] in {"not_provided", "not_shipped"}
        for row in official
    )
    assert all(
        row["zmr_parameters_or_code"] in {"not_provided", "not_shipped"}
        for row in official
    )
    rejected = next(
        row for row in lineage
        if row["relationship"] == "rejected_post_paper_third_party_guess"
    )
    assert rejected["available_by_p1gpt_v1"] == "False"
    assert rejected["attributable_to_p1gpt_authors"] == "False"
    assert "placeholder" in rejected["kdj_rsi_parameters_or_code"]
    assert all(row["native_p1gpt_method_or_result_credit"] == "False" for row in lineage)


def test_consistency_audit_records_lookahead_and_metric_conflicts() -> None:
    checks = {row["check_id"]: row for row in rows("internal_consistency.csv")}
    assert len(checks) == 19
    assert checks["aapl_kdj_rsi_raster_mdd"]["status"] == "author_raster_table_metric_conflict"
    assert checks["aapl_zmr_raster_mdd"]["status"] == "author_raster_table_metric_conflict"
    assert checks["march_report_future_iphone_air"]["status"] == "direct_lookahead_counterexample"
    assert checks["lookahead_claim"]["status"] == "claim_contradicted_by_embedded_output"
    assert checks["risk_free_rate"]["status"] == "equation_execution_conflict"
    assert checks["buy_hold_googl_mdd"]["status"] == "displayed_cell_not_recovered"
    assert checks["no_leverage"]["status"] == "meaning_of_leverage_or_position_undefined"
    assert checks["best_baseline_gap"]["status"] == "passes_displayed_table_arithmetic"
    assert checks["drawdown_prose"]["status"] == "rounded_prose_overstatement"
    assert all(row["paper_result_credit"] == "False" for row in checks.values())


def test_manuscript_rebuild_and_visual_qa_are_document_evidence_only() -> None:
    rebuilds = json.loads((AUDIT_DIR / "manuscript_rebuilds.json").read_text(encoding="utf-8"))
    assert len(rebuilds) == 1
    rebuild = rebuilds[0]
    assert rebuild["same_hash_across_independent_build_directories"] is True
    assert rebuild["page_count"] == rebuild["published_page_count"] == 17
    assert rebuild["normalized_extracted_text_equal"] is True
    assert rebuild["normalized_extracted_text_sequence_ratio"] == 1.0
    assert "passed_all_17_author_and_17_rebuilt_pages" in rebuild["full_contact_sheet_visual_qa"]
    assert "passed_all_7_assets" in rebuild["embedded_asset_visual_qa"]
    assert rebuild["document_reconstruction_credit"] is True
    assert rebuild["paper_result_reproduction"] is False


def test_manifest_hashes_every_nonmanifest_output_and_readme_is_honest() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "not faithfully reproduced end to end" in text
    assert "46 exact matches" in text
    assert "two raster contradictions" in text
    assert "13.21% ZMR MDD" in text
    assert "0/12 P1GPT cells" in text
    assert "strictly avoids lookahead bias" in text
    assert "does not prove every daily signal" in text
    assert "36 reachable commits" in text
    assert "one accessible fork" in text
    assert "byte-identical" in text
    assert "excluded from native-method or result credit" in text
    assert "no single convention recovers all 12" in text
    assert "disjoint intervals" in text
    assert "Installing additional packages cannot recover" in text


def test_paper_routes_through_public_component_audit_without_proxy_credit() -> None:
    route_path = ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    with route_path.open(newline="", encoding="utf-8") as stream:
        routed = [row for row in csv.DictReader(stream) if row["canonical_work_id"] == audit.WORK_ID]
    assert len(routed) == 1
    row = routed[0]
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == audit.SYSTEM_ID
    assert row["static_fidelity_tiers"] == "R3"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_46_of_72_displayed_cells_verified_zero_of_12_"
        "native_agent_cells_end_to_end_lookahead_counterexample_1_fork_1_ref_"
        "official_head_exhausted"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert "0/12 native P1GPT cells" in row["precise_native_or_access_blocker"]
    assert "lookahead" in row["precise_native_or_access_blocker"]
    assert row["proxy_role"] == "secondary_diagnostic_after_native_review"
