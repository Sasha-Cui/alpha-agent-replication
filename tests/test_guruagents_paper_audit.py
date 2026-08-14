from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_guruagents_paper.py"
SPEC = importlib.util.spec_from_file_location("guruagents_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_committed_table_census_is_complete_and_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/guruagents"
    rows = read_csv(output / "paper_table_1_conformance.csv")
    diagnostics = read_csv(output / "source_workbook_metric_diagnostics.csv")
    summary = read_csv(output / "source_workbook_window_summary.csv")
    assert len(rows) == 70
    assert len(diagnostics) == 140
    assert len(summary) == 14
    exact = [row for row in rows if row["paper_result_credit"] == "True"]
    assert len(exact) == 2
    assert {(row["strategy"], row["metric"]) for row in exact} == {
        ("NASDAQ 100", "max_drawdown_pct"),
        ("S&P 500", "max_drawdown_pct"),
    }
    assert sum(row["full_paper_row_reproduced"] == "True" for row in summary) == 0


def test_figures_and_appendix_prompts_are_not_overcredited() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/guruagents"
    figures = read_csv(output / "paper_figure_unit_conformance.csv")
    prompts = read_csv(output / "source_prompt_conformance.csv")
    embedded = read_csv(output / "notebook_embedded_plot_inventory.csv")
    assert len(figures) == 42
    assert sum(row["figure"] == "Figure 1 cumulative returns" for row in figures) == 7
    assert sum(row["figure"] == "Figure 2 portfolio weights" for row in figures) == 35
    assert {row["paper_result_credit"] for row in figures} == {"False"}
    assert len(prompts) == 5
    assert {row["paper_appendix_is_verbatim_runtime_prompt"] for row in prompts} == {"False"}
    buffett = next(row for row in prompts if row["agent"] == "Warren Buffett")
    assert "CashConversion" in buffett["prompt_scoring_inputs_not_returned_by_declared_tools"]
    assert "OwnerEarningsYield" in buffett["prompt_scoring_inputs_not_returned_by_declared_tools"]
    assert len(embedded) == 2
    assert {row["exact_paper_image_match"] for row in embedded} == {"False"}


def test_archived_runs_are_real_component_evidence_but_outputs_break_contract() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/guruagents"
    runs = read_csv(output / "archived_run_inventory.csv")
    portfolios = read_csv(output / "archived_portfolio_validation.csv")
    assert len(runs) == 95
    assert sum(row["source_collection"] == "results" for row in runs) == 35
    assert sum(row["source_collection"] == "results_22_24" for row in runs) == 60
    assert sum(row["paper_period_candidate"] == "True" for row in runs) == 60
    assert sum(row["public_same_period_variants"] == "2" for row in runs) == 50
    assert {row["runtime_model_snapshot"] for row in runs} == {"gpt-4o-2024-08-06"}
    assert {row["every_expected_tool_called_once"] for row in runs} == {"True"}
    fingerprints = {
        value
        for row in runs
        for value in row["runtime_system_fingerprints"].split("; ")
        if value
    }
    assert len(fingerprints) == 3
    assert len(portfolios) == 95
    assert sum(abs(float(row["raw_weight_sum"]) - 100) <= 1e-9 for row in portfolios) == 16
    assert sum(int(row["raw_duplicate_tickers"]) > 0 for row in portfolios) == 17
    assert sum(row["response_begins_with_only_required_table"] == "True" for row in portfolios) == 1
    assert sum(row["strict_prompt_output_contract_satisfied"] == "True" for row in portfolios) == 0
    assert {row["paper_result_credit"] for row in runs + portfolios} == {"False"}


def test_full_public_history_finds_no_missing_paper_result_artifact() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/guruagents"
    history = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))
    commits = read_csv(output / "public_source_history_commits.csv")
    paths = read_csv(output / "public_source_history_path_inventory.csv")
    workbook_cells = read_csv(output / "historical_workbook_table_conformance.csv")
    workbooks = read_csv(output / "historical_workbook_summary.csv")
    notebooks = read_csv(output / "historical_notebook_inventory.csv")
    plots = read_csv(output / "historical_notebook_plot_inventory.csv")
    alternatives = read_csv(output / "archived_overlapping_run_comparison.csv")
    assert history["reachable_commits"] == len(commits) == 19
    assert history["unique_paths"] == len(paths) == 592
    assert history["unique_blobs"] == 628
    assert len(workbook_cells) == 280
    assert len(workbooks) == 4
    assert max(int(row["paper_table_rounding_matches"]) for row in workbooks) == 2
    assert sum(int(row["paper_table_cells_with_result_credit"]) for row in workbooks) == 2
    assert {row["complete_paper_table_reproduced"] for row in workbooks} == {"False"}
    assert len(notebooks) == 20
    assert sum(row["paper_relevant_multi_agent_notebook"] == "True" for row in notebooks) == 3
    assert sum(row["implements_complete_paper_table_generator"] == "True" for row in notebooks) == 0
    assert len(plots) == 14
    assert sum(row["paper_relevant_multi_agent_notebook"] == "True" for row in plots) == 6
    assert {row["exact_paper_image_match"] for row in plots} == {"False"}
    assert len(alternatives) == 25
    assert sum(row["exact_portfolio_file_match"] == "True" for row in alternatives) == 0
    assert sum(row["exact_ticker_set_match"] == "True" for row in alternatives) == 4


def test_native_execution_reproduces_only_the_public_workbook() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/guruagents"
    rows = read_csv(output / "native_backtest_conformance.csv")
    native = json.loads((output / "native_execution.json").read_text(encoding="utf-8"))
    assert len(rows) == 7
    assert {row["shipped_workbook_series_reproduced"] for row in rows} == {"True"}
    assert max(float(row["maximum_numeric_absolute_error"]) for row in rows) < 1e-12
    assert {row["paper_series_reproduced"] for row in rows} == {"False"}
    assert native["released_source_native_backtest"]["source_workbook_series_reproduced"] == 7
    assert native["paper_source_compilation"]["exit_codes"] == [0, 0]
    assert native["paper_source_compilation"]["produced_pdf_pages"] == 7
    assert native["full_native_paper_execution_attempted"] is False
    assert native["paper_result_credit"] is False


def test_manifest_is_honest_and_outputs_are_self_verifying() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/guruagents"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["overall_status"] == (
        "full_public_history_audited_public_workbook_reproduced_but_paper_results_not_reproduced_two_of_70_cells_only"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_table_cells_total"] == 70
    assert manifest["paper_table_cells_with_result_credit"] == 2
    assert manifest["paper_table_rows_fully_reproduced"] == 0
    assert manifest["paper_figure_units_with_result_credit"] == 0
    assert manifest["paper_appendix_prompts_verbatim_runtime"] == 0
    assert manifest["paper"]["versions_total"] == 1
    assert manifest["paper"]["version_history_exhausted"] is True
    assert manifest["source"]["full_public_history_audited"] is True
    assert manifest["source_history_reachable_commits"] == 19
    assert manifest["source_history_unique_paths"] == 592
    assert manifest["source_history_unique_blobs"] == 628
    assert manifest["historical_multi_agent_workbook_blobs"] == 4
    assert manifest["best_historical_workbook_table_matches"] == 2
    assert manifest["historical_embedded_plots_matching_paper_figures"] == 0
    assert manifest["archived_agent_runs"] == 95
    assert manifest["archived_current_collection_runs"] == 35
    assert manifest["archived_older_collection_runs"] == 60
    assert manifest["archived_paper_period_candidate_runs"] == 60
    assert manifest["archived_runs_with_exact_expected_tool_calls"] == 95
    assert manifest["raw_portfolios_weight_sum_100"] == 16
    assert manifest["raw_portfolios_with_duplicate_tickers"] == 17
    assert manifest["raw_portfolios_satisfying_full_strict_contract"] == 0
    assert manifest["same_labeled_period_alternate_run_pairs"] == 25
    assert manifest["alternate_run_pairs_with_exact_portfolio_file"] == 0
    assert manifest["alternate_run_pairs_with_exact_ticker_set"] == 4
    assert manifest["native_source_workbook_series_reproduced"] == 7
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_primary_sources_are_pinned_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/guruagents_prompt_replay_source")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/guruagents_paper")
    if not source.exists() or not paper.exists():
        return
    audit.validate_inputs(source, paper)
    table, diagnostics, summaries = audit.table_conformance_rows(source)
    assert (len(table), len(diagnostics), len(summaries)) == (70, 140, 14)
    runs, portfolios = audit.archived_run_and_portfolio_rows(source)
    assert (len(runs), len(portfolios)) == (95, 95)
    assert len(audit.overlapping_archived_run_rows(source, portfolios)) == 25
    history = audit.public_source_history_rows(source)
    assert history[0]["reachable_commits"] == 19
    assert (len(history[1]), len(history[2]), len(history[3]), len(history[4])) == (19, 592, 280, 4)
    assert len(audit.source_prompt_rows(source, paper)) == 5
