"""Contracts for the fail-closed RAPTOR paper/source audit."""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_raptor_paper.py"
SPEC = importlib.util.spec_from_file_location("audit_raptor_paper", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)

PAPER = ROOT / "literature_review/papers/56_raptor_reasoned_agentic_portfolio_trading_with_orchestrated_rebalancing.pdf"
OUTPUT = ROOT / "paper_runs/paper_replication_audits/raptor"


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_published_final_is_pinned_and_hidden_author_link_is_preserved() -> None:
    assert audit.sha256(PAPER) == audit.EXPECTED_PDF_SHA256
    _, links = audit.validate_paper(PAPER)
    author = [row for row in links if row["uri"] == audit.AUTHOR_REPO_URL]
    assert author == [{"page": "9", "uri": audit.AUTHOR_REPO_URL}]
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["official_pdf_pages_audited"] == 11
    assert manifest["official_pdf_pages_visually_inspected"] == 11


def test_complete_anonymous_source_inventory_is_pinned_and_compiles() -> None:
    rows = csv_rows("source_file_inventory.csv")
    assert len(rows) == 825
    assert sum(row["compile_status"] == "compiled" for row in rows) == 94
    assert all(not row["compile_status"].startswith(("SyntaxError", "IndentationError")) for row in rows)
    roles = Counter(row["role"] for row in rows)
    assert roles["author_result_snapshot"] == 166
    assert roles["author_day0_decision_output"] == 503
    assert roles["candidate_backtest_runner"] == 3
    assert roles["native_result_postprocessor"] == 1
    assert all(row["end_to_end_result_credit"] == "no" for row in rows)


def test_anonymous_and_author_repositories_have_auditable_lineage() -> None:
    rows = csv_rows("repository_relationship.csv")
    assert len(rows) == 828
    assert Counter(row["relationship"] for row in rows) == {
        "byte_identical": 815, "changed": 7, "author_only": 3, "anonymous_only": 3,
    }
    by_path = {row["path"]: row for row in rows}
    for path in (
        "testing/mvo_blm_runner.py", "testingLoopMultithreaded.py",
        "mvo_blm_runner.py", "testing/scripts/visualize.py",
        "testing/2025-08-29/portfolio_snapshot_2025-08-29.json",
    ):
        assert by_path[path]["relationship"] == "byte_identical"
    provenance = json.loads((OUTPUT / "source_provenance.json").read_text(encoding="utf-8"))
    assert provenance["anonymous_repository_head"] == audit.EXPECTED_ANONYMOUS_HEAD
    assert provenance["author_repository_head"] == audit.EXPECTED_AUTHOR_HEAD
    assert provenance["all_166_snapshots_identical"] is True
    assert provenance["native_metric_module_path"] == "testing/mvo/metrics.py"
    assert (
        provenance["native_metric_module_sha256"]
        == audit.EXPECTED_NATIVE_METRIC_MODULE_SHA256
    )
    assert "inference" in provenance["anonymous_to_author_relationship"]

    history = csv_rows("source_history_inventory.csv")
    assert len(history) == 4
    assert {row["commit"] for row in history} == audit.EXPECTED_AUTHOR_COMMITS
    validation = next(row for row in history if row["commit"] == audit.EXPECTED_AUTHOR_VALIDATION_HEAD)
    assert validation["tracked_files"] == "845"
    assert validation["portfolio_snapshots"] == "166"
    assert all(row["stock_prices_csv"] == "0" and row["benchmark_data_files"] == "0" for row in history)

    branch = csv_rows("validation_branch_inventory.csv")
    assert len(branch) == 20
    assert all(row["paper_result_credit"] == "none" for row in branch)
    enhancement = next(row for row in branch if row["path"] == "paper_enhancements/enhanced_paper_sections.md")
    validator = next(row for row in branch if row["path"] == "evaluation/statistical_validation.py")
    assert "unsupported_conflicting_claims" in enhancement["assessment"]
    assert "12.49%" in enhancement["defects_or_conflicts"]
    assert "aligned_benchmarkay NameError" in validator["defects_or_conflicts"]


def test_released_snapshots_recover_every_headline_portfolio_metric() -> None:
    rows = {row["metric"]: row for row in csv_rows("snapshot_metric_reproduction.csv")}
    assert len(rows) == 10
    assert all(row["match"] == "yes" for row in rows.values())
    assert math.isclose(float(rows["total_return_percent"]["computed_value"]), 13.434819440490697)
    assert math.isclose(float(rows["annualized_return_percent"]["computed_value"]), 21.090192227941817)
    assert math.isclose(float(rows["annualized_volatility_percent"]["computed_value"]), 19.30426162364428)
    assert math.isclose(float(rows["sharpe_rf_2_percent"]["computed_value"]), .9897422727517595)
    assert math.isclose(float(rows["sortino_rf_2_percent_negative_only_sample_sd"]["computed_value"]), 1.2787050163631515)
    assert math.isclose(float(rows["maximum_drawdown_percent"]["computed_value"]), -15.33365025620428)
    assert all(row["end_to_end_pipeline_reproduced"] == "no" for row in rows.values())


def test_all_empirical_scalar_assertions_are_counted_without_inflating_credit() -> None:
    rows = csv_rows("displayed_result_conformance.csv")
    assert len(rows) == 42
    verified = [row for row in rows if row["verification_status"].startswith("verified")]
    assert len(verified) == 29
    assert Counter(row["verification_source"] for row in verified) == {
        "author_output": 18, "current_public_response": 3, "paper_internal_consistency": 8,
    }
    assert sum(row["verification_status"] != "unavailable" for row in rows) == 36
    assert sum(row["verification_status"] == "unavailable" for row in rows) == 6
    assert all(row["independent_end_to_end_reproduction"] == "no" for row in rows)
    assert Counter(row["scope"] for row in rows) == {
        "RAPTOR": 14, "rolling": 11, "interpretability": 14, "benchmark": 2, "comparison": 1,
    }
    table = [row for row in rows if row["location"] == "Table 1"]
    assert len(table) == 9
    assert all(row["author_output_value"] == "" for row in table)
    assert Counter(row["credit_boundary"] for row in table) == {
        "no_result_credit": 6,
        "paper_internal_consistency_only_no_native_result_credit": 3,
    }


    internal = csv_rows("paper_internal_scalar_checks.csv")
    assert len(internal) == 8
    assert Counter(row["check_type"] for row in internal) == {
        "paper_internal_arithmetic": 3,
        "paper_internal_duplicate": 5,
    }
    assert {row["match_at_display_precision"] for row in internal} == {"True"}
    assert {row["paper_result_credit"] for row in internal} == {"False"}
    explanation = [row for row in rows if row["location"] == "Table 1 explanation"]
    assert len(explanation) == 5
    assert {
        row["verification_source"] for row in explanation
    } == {"paper_internal_consistency"}



def test_current_public_benchmark_response_recovers_three_displayed_units_without_lineage_credit() -> None:
    assert audit.sha256(OUTPUT / "yahoo_gspc_response.json") == audit.EXPECTED_YAHOO_GSPC_SHA256
    benchmark = csv_rows("benchmark_snapshot_reproduction.csv")
    assert len(benchmark) == 165
    assert benchmark[0]["date"] == "2025-01-02"
    assert benchmark[-1]["date"] == "2025-08-29"
    assert math.isclose(float(benchmark[0]["adjusted_close"]), 5868.5498046875)
    assert math.isclose(float(benchmark[-1]["adjusted_close"]), 6460.259765625)
    assert math.isclose(float(benchmark[-1]["cumulative_return_percent"]), 10.08272879383032)
    assert all(row["paper_time_frozen_input"] == "no" and row["end_to_end_result_credit"] == "no" for row in benchmark)

    rows = csv_rows("displayed_result_conformance.csv")
    current = [row for row in rows if row["verification_source"] == "current_public_response"]
    assert [row["result_id"] for row in current] == ["RAP-002", "RAP-004", "RAP-005"]
    assert all(row["credit_boundary"] == "current_public_response_verification_only_not_paper_lineage" for row in current)
    assert all(row["author_output_value"] == "" for row in current)


def test_rolling_sharpe_conflicts_are_numerically_exposed() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert math.isclose(manifest["rolling_sample_min"], -5.267501884798236)
    assert math.isclose(manifest["rolling_sample_max"], 10.343535369432843)
    assert math.isclose(manifest["rolling_sample_mean"], 2.150896430904414)
    assert math.isclose(manifest["rolling_sample_final"], 3.7898775588598927)
    assert math.isclose(manifest["rolling_population_final"], 3.8883323324435795)
    assert math.isclose(manifest["rolling_full20_rf2_sample_mean"], 1.5993969802199037)
    assert math.isclose(manifest["rolling_full20_rf2_sample_sd"], 3.2759617841049122)
    assert manifest["rolling_claim_forensic_rows"] == 1168
    assert manifest["rolling_section_20d_conventions"] == 8
    assert manifest["rolling_section_20d_claim_cells_matching"] == 0
    assert manifest["rolling_longer_window_conventions"] == 1160
    assert manifest["rolling_longer_any_endpoint_matches"] == 290
    assert manifest["rolling_longer_both_endpoints_match"] == 11
    rows = csv_rows("rolling_sharpe_reproduction.csv")
    assert len(rows) == 166
    assert rows[0]["daily_return"] == ""
    assert rows[-1]["date"] == "2025-08-29"
    assert math.isclose(float(rows[-1]["rolling_sharpe_20d_sample_sd"]), 3.7898775588598927)
    full_window = [
        float(row["rolling_sharpe_20d_full_window_sample_sd_rf2pct"])
        for row in rows
        if row["rolling_sharpe_20d_full_window_sample_sd_rf2pct"]
    ]
    assert len(full_window) == 146
    assert round(statistics.mean(full_window), 2) == 1.60
    assert round(statistics.stdev(full_window), 2) == 3.28

    forensic = csv_rows("rolling_claim_convention_forensics.csv")
    assert len(forensic) == 1168
    section = [row for row in forensic if row["claim_scope"] == "section_4_3_explicit_20_day"]
    longer = [row for row in forensic if row["claim_scope"] == "extended_validation_unspecified_longer_window"]
    assert len(section) == 8
    assert {row["section_claim_cells_matching"] for row in section} == {"0"}
    assert len(longer) == 1160
    assert sum(
        row["longer_lower_1_1_matches_mean_or_final"] == "True"
        or row["longer_upper_1_4_matches_mean_or_final"] == "True"
        for row in longer
    ) == 290
    assert sum(row["longer_both_endpoints_match"] == "True" for row in longer) == 11

    displayed = {row["result_id"]: row for row in csv_rows("displayed_result_conformance.csv")}
    assert displayed["RAP-020"]["verification_status"].startswith("verified_rounded_full_20d")
    assert displayed["RAP-021"]["verification_status"].startswith("verified_rounded_full_20d")

    assert {
        displayed[f"RAP-{number:03d}"]["verification_status"]
        for number in range(7, 11)
    } == {"checked_conflict_all_eight_standard_20d_conventions"}
    assert {
        displayed[f"RAP-{number:03d}"]["verification_status"]
        for number in range(22, 24)
    } == {"checked_underspecified_1160_longer_window_conventions"}

def test_published_figure_rasters_have_source_correspondence_without_raw_series_inflation() -> None:
    rows = csv_rows("figure_raster_forensics.csv")
    assert len(rows) == 3
    keyed = {(row["figure"], row["series"]): row for row in rows}
    assert all(row["raster_correspondence_verified"] == "yes" for row in rows)
    assert all(row["published_raw_numeric_series_available"] == "no" for row in rows)
    assert all(row["end_to_end_pipeline_reproduced"] == "no" for row in rows)

    portfolio = keyed[("Figure 2", "RAPTOR cumulative return")]
    assert portfolio["paper_exact_color_pixels"] == "7313"
    assert portfolio["comparison_exact_color_pixels"] == "7313"
    assert portfolio["exact_color_intersection_pixels"] == "7313"
    assert float(portfolio["paper_color_pixels_within_2px_fraction"]) == 1.0
    assert float(portfolio["comparison_color_pixels_within_2px_fraction"]) == 1.0
    assert float(portfolio["author_notebook_affine_max_distance_px"]) <= 2.0
    assert math.isclose(float(portfolio["whole_figure_exact_rgb_fraction"]), 0.9999477777777778)

    benchmark = keyed[("Figure 2", "S&P 500 cumulative return")]
    assert benchmark["paper_exact_color_pixels"] == "3132"
    assert benchmark["comparison_exact_color_pixels"] == "3147"
    assert benchmark["exact_color_intersection_pixels"] == "3132"
    assert float(benchmark["paper_color_pixels_within_2px_fraction"]) == 1.0
    assert float(benchmark["comparison_color_pixels_within_2px_fraction"]) > 0.995
    assert float(benchmark["author_notebook_affine_max_distance_px"]) <= 2.0
    assert benchmark["paper_time_numeric_input_lineage"] == "missing_paper_time_csv_current_response_only"

    rolling = keyed[("Figure 3", "20-day rolling Sharpe")]
    assert rolling["paper_exact_color_pixels"] == "3530"
    assert rolling["comparison_exact_color_pixels"] == "3527"
    assert float(rolling["paper_color_pixels_within_2px_fraction"]) == 1.0
    assert float(rolling["comparison_color_pixels_within_2px_fraction"]) == 1.0

    series = csv_rows("figure_series_conformance.csv")
    assert len(series) == 3
    assert all(row["raster_curve_correspondence_verified"] == "yes" for row in series)
    assert all(row["exact_published_series_reproduced"].startswith("no_") for row in series)


def test_method_audit_exposes_output_runner_divergence_and_missing_inputs() -> None:
    rows = {row["dimension"]: row for row in csv_rows("method_specification_audit.csv")}
    assert len(rows) == 48
    assert rows["price inputs"]["assessment"] == "missing"
    assert rows["benchmark inputs"]["assessment"] == "paper_snapshot_missing_current_response_verified"
    assert rows["output cadence"]["assessment"] == "different"
    assert rows["multithreaded range runner"]["assessment"] == "implementation_bug"
    assert rows["output-runner views"]["assessment"] == "different"
    assert rows["covariance lookback"]["assessment"] == "different"
    assert rows["transaction fees"]["assessment"] == "missing"
    assert rows["WAB case study"]["assessment"] == "missing"
    assert rows["native visualization"]["assessment"] == "pass_component"
    assert all(row["end_to_end_credit"] == "no" for row in rows.values())


def test_paper_consistency_and_decision_outputs_are_not_silently_accepted() -> None:
    issues = csv_rows("paper_internal_consistency_audit.csv")
    assert len(issues) == 14
    assert any(row["issue"] == "cadence" and "daily" in row["evidence"] for row in issues)
    assert any(row["issue"] == "rolling convention" and "3.89" in row["evidence"] for row in issues)
    assert any(row["issue"] == "trace inclusion" for row in issues)

    decisions = {row["check"]: row for row in csv_rows("decision_trace_audit.csv")}
    assert decisions["decision_file_coverage"]["value"] == "503"
    assert json.loads(decisions["header_distribution"]["value"]) == {"BUY": 417, "HOLD": 86}
    assert decisions["automated_sell_language_flags_among_BUY"]["value"] == "236"
    assert decisions["AAPL_manual_trace"]["assessment"] == "contradiction"
    assert decisions["WAB_manual_trace"]["assessment"] == "contradiction_and_wrong_case_date"


def test_access_and_search_evidence_recovers_public_source_but_not_expired_4open() -> None:
    searches = csv_rows("source_search_inventory.csv")
    assert [int(row["total_count"]) for row in searches] == [0, 0, 1, 0]
    assert searches[2]["repositories"] == "anonymouspenguin3/RAPTOR-Reasoned-Agentic-Portfolio-Trading-with-Orchestrated-Rebalancing"
    assert all(row["incomplete_results"] == "false" for row in searches)

    fouropen = {row["endpoint"]: row for row in csv_rows("fouropen_access_audit.csv")}
    assert fouropen["root"]["final_http_status"] == "401"
    assert fouropen["files"]["final_http_status"] == "410"
    assert fouropen["options"]["response"] == "repository_expired"
    assert all(row["reachable_artifact"] == "no" for row in fouropen.values())


def test_native_execution_and_manifest_state_the_honest_boundary() -> None:
    execution = {row["component"]: row for row in csv_rows("native_execution.csv")}
    assert len(execution) == 6
    assert execution["testing/mvo_blm_runner.py"]["status"] == "blocked_before_backtest"
    assert "stock_prices.csv" in execution["testing/mvo_blm_runner.py"]["detail"]
    assert execution["testing/scripts/visualize.py"]["status"] == "pass"
    assert execution["testing/mvo/metrics.py"]["attempted"] == "yes_twice"
    assert execution["testing/mvo/metrics.py"]["status"] == "pass"
    assert (
        execution["testing/mvo/metrics.py"]["paper_result_credit"]
        == "author_output_postprocessing_only"
    )
    assert execution["end-to-end multi-agent backtest"]["attempted"] == "no"

    native = json.loads((OUTPUT / "native_execution.json").read_text(encoding="utf-8"))
    metric_execution = json.loads(
        (OUTPUT / "native_metric_module_execution.json").read_text(encoding="utf-8")
    )
    metric_rows = {
        row["function"]: row
        for row in csv_rows("native_metric_module_conformance.csv")
    }
    assert set(metric_rows) == set(audit.EXPECTED_NATIVE_METRIC_OUTPUT_SHA256)
    assert {name: int(row["points"]) for name, row in metric_rows.items()} == {
        "rolling_calmar_60": 165,
        "rolling_sharpe_20": 165,
        "rolling_sortino_20": 165,
    }
    assert {name: int(row["finite_points"]) for name, row in metric_rows.items()} == {
        "rolling_calmar_60": 163,
        "rolling_sharpe_20": 164,
        "rolling_sortino_20": 164,
    }
    assert {
        name: row["output_sha256"] for name, row in metric_rows.items()
    } == audit.EXPECTED_NATIVE_METRIC_OUTPUT_SHA256
    sharpe = metric_rows["rolling_sharpe_20"]
    assert sharpe["audit_series_compared"] == "True"
    assert sharpe["audit_series_finite_points_compared"] == "164"
    assert float(sharpe["maximum_audit_series_absolute_error"]) <= 2e-15
    assert sharpe["nan_pattern_matches_audit"] == "True"
    assert all(row["native_agent_or_backtest_executed"] == "False" for row in metric_rows.values())
    assert all(row["paper_result_credit"] == "False" for row in metric_rows.values())
    assert metric_execution["source_sha256"] == audit.EXPECTED_NATIVE_METRIC_MODULE_SHA256
    assert metric_execution["network_attempts"] == []
    assert metric_execution["snapshot_rows"] == 166
    assert metric_execution["return_rows"] == 165
    assert metric_execution["output_sha256"] == audit.EXPECTED_NATIVE_METRIC_OUTPUT_SHA256
    assert metric_execution["conformance"] == {
        "execution_runs": 2,
        "functions_executed": 3,
        "native_agent_or_backtest_executed": False,
        "output_points": 495,
        "paper_result_credit": False,
        "rolling_sharpe_finite_points_compared": 164,
        "rolling_sharpe_maximum_absolute_error": 1.7763568394002505e-15,
        "rolling_sharpe_nan_pattern_match": True,
        "rolling_sharpe_points_compared": 165,
    }
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert native["native_metric_module_executed"] is True
    assert native["native_metric_module_execution_runs"] == 2
    assert native["native_metric_functions_executed"] == 3
    assert native["native_metric_output_points"] == 495
    assert native["native_metric_rolling_sharpe_points_compared"] == 165
    assert native["native_metric_rolling_sharpe_finite_points_compared"] == 164
    assert native["native_metric_rolling_sharpe_nan_pattern_match"] is True
    assert native["native_metric_rolling_sharpe_maximum_absolute_error"] <= 2e-15
    assert native["author_output_verified_scalar_results"] == 18
    assert native["current_public_response_verified_scalar_results"] == 3
    assert native["paper_internal_verified_scalar_results"] == 8
    assert native["displayed_scalar_results_verified"] == 29
    assert native["displayed_scalar_results_checked"] == 36
    assert native["rolling_claim_conflicts_checked"] == 5
    assert native["rolling_claims_underspecified_checked"] == 2
    assert native["end_to_end_result_cells_reproduced"] == 0
    assert native["llm_calls_made"] == 0
    assert manifest["overall_fidelity"] == "full_author_history_and_166_output_snapshots_audited_36_of_42_scalar_units_checked_29_verified_18_author_output_3_current_public_8_paper_internal_5_conflicts_2_underspecified_6_unavailable_zero_end_to_end_result_cells_reproduced"
    assert manifest["author_result_snapshots"] == 166
    assert manifest["compiled_python_files"] == 94
    assert manifest["paper_internal_scalar_checks"] == 8
    assert manifest["paper_internal_verified_scalar_results"] == 8
    assert manifest["displayed_scalar_results_verified"] == 29
    assert manifest["displayed_scalar_results_checked"] == 36
    assert manifest["displayed_scalar_results_unavailable"] == 6
    assert manifest["rolling_claim_conflicts_checked"] == 5
    assert manifest["rolling_claims_underspecified_checked"] == 2
    assert manifest["native_metric_module_executed"] is True
    assert manifest["native_metric_module_execution_runs"] == 2
    assert manifest["native_metric_functions_executed"] == 3
    assert manifest["native_metric_output_points"] == 495
    assert manifest["native_metric_rolling_sharpe_points_compared"] == 165
    assert manifest["native_metric_rolling_sharpe_maximum_absolute_error"] <= 2e-15
    assert manifest["paper_result_credit"] == "output_current_response_or_paper_internal_verification_only_no_end_to_end_result_credit"
    assert math.isclose(manifest["benchmark_return_percent"], 10.08272879383032)
    assert manifest["published_figure_raster_curve_correspondences_verified"] == 3
    assert manifest["exact_published_figure_series_reproduced"] == 0
    assert manifest["figure_2_whole_image_different_pixels"] == 47
    assert math.isclose(manifest["figure_2_whole_image_exact_rgb_fraction"], 0.9999477777777778)

    readme = " ".join((OUTPUT / "README.md").read_text(encoding="utf-8").split())
    assert "End-to-end RAPTOR result cells reproduced: 0/42" in readme
    assert "29/42" in readme
    assert "36/42" in readme
    assert "18/42" in readme
    assert "3/42" in readme
    assert "8/42" in readme
    assert "6/42 remain unavailable" in readme
    assert "All 8 standard" in readme
    assert "290 of 1160 conventions" in readme
    assert "11 hit both" in readme
    assert "output verification, not a rerun" in readme
    assert "Published raster-curve correspondences verified: 3/3" in readme
    assert "exact published raw-series credit stays 0/3" in readme
    assert "emits 495 values across rolling Sharpe" in readme
    assert "earns no end-to-end agent or paper-result credit" in readme
