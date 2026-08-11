from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/factfin"
SPEC = importlib.util.spec_from_file_location(
    "audit_factfin_paper", ROOT / "scripts/audit_factfin_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_all_published_table_results_are_transcribed_without_credit() -> None:
    ledger = audit.result_ledger()
    assert len(ledger) == 525
    assert sum(row["cell_kind"] == "direct_result" for row in ledger) == 489
    assert sum(row["cell_kind"] == "derived_comparison" for row in ledger) == 36
    assert {
        table: sum(row["table"] == table for row in ledger)
        for table in {row["table"] for row in ledger}
    } == {
        "counterfactual_agents": 15,
        "overall_performance": 198,
        "overall_performance_improvement": 18,
        "leakage_metrics": 180,
        "leakage_improvement": 18,
        "ablation": 48,
        "llm_backbone": 36,
        "finleak_case_study": 12,
    }
    factfin = [row for row in ledger if row["factfin_system_output"]]
    assert len(factfin) == 120
    duplicate_groups = {
        row["duplicate_measurement_group"]
        for row in factfin
        if row["duplicate_measurement_group"]
    }
    assert len(duplicate_groups) == 12
    assert len(factfin) - len(duplicate_groups) == 108
    assert all(row["native_reproduced_value"] == "" for row in ledger)
    assert all(row["paper_result_credit"] is False for row in ledger)


def test_manifest_fail_closed_result_boundary() -> None:
    data = manifest()
    assert data["overall_status"] == (
        "not_reproduced_no_public_system_or_benchmark_release_and_missing_runtime_data_strategy_trade_lineage"
    )
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["published_empirical_or_derived_numeric_table_cells"] == 525
    assert data["published_direct_numeric_result_cells"] == 489
    assert data["published_derived_comparison_cells"] == 36
    assert data["factfin_direct_numeric_result_cells"] == 120
    assert data["factfin_unique_direct_numeric_measurements_after_table_duplicates"] == 108
    assert data["published_table_cells_faithfully_regenerated"] == 0
    assert data["factfin_cells_faithfully_regenerated"] == 0
    assert data["public_system_source_files_recovered"] == 0
    assert data["public_benchmark_records_recovered"] == 0
    assert data["llm_calls_made"] == 0


def test_arxiv_bundle_is_complete_manuscript_source_not_system_source() -> None:
    inventory = rows("paper_source_inventory.csv")
    assert len(inventory) == 14
    assert sum(row["role"] == "primary_manuscript_source" for row in inventory) == 1
    assert sum(row["role"] == "manuscript_appendix_source" for row in inventory) == 1
    assert sum(row["role"] == "published_figure" for row in inventory) == 7
    assert all(row["is_executable_system_source"] == "False" for row in inventory)
    assert all(row["replication_credit"] == "False" for row in inventory)


def test_document_rebuild_and_visual_qa_do_not_become_system_execution() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text(encoding="utf-8"))
    native = json.loads((AUDIT_DIR / "native_execution.json").read_text(encoding="utf-8"))
    assert provenance["arxiv_source_files"] == 14
    assert provenance["official_pdf_pages"] == 12
    assert provenance["first_converged_rebuild_sha256"] != provenance["second_converged_rebuild_sha256"]
    assert "not called byte-identical" in provenance["rebuild_comparison"]
    assert provenance["source_archive_contains_system_code"] is False
    assert set(provenance["visual_qa"].values()) == {
        "pass; visible and legible on inspected pages",
        "pass; arXiv margin stamp on page 1; no clipped, overlapping, invisible, or illegible content",
        "pass; same manuscript layout without arXiv margin stamp",
    }
    assert native["manuscript_source_rebuilt"] is True
    assert native["manuscript_rebuild_is_system_execution"] is False
    assert native["factfin_pipeline_executed"] is False
    assert native["published_table_cells_faithfully_regenerated"] == 0


def test_bounded_artifact_search_recovers_no_attributable_release() -> None:
    access = rows("artifact_access_audit.csv")
    discovery = rows("discovery_evidence.csv")
    assert len(access) == 9
    assert len(discovery) == 13
    assert all(row["system_source_credit"] == "False" for row in access)
    assert all(row["system_or_dataset_recovered"] == "False" for row in discovery)
    assert all(row["negative_search_limit"] for row in discovery)
    indexed = {row["artifact"]: row for row in access}
    assert indexed["author_homepage"]["tier"] == "R1 author documentation"
    assert indexed["researchtrend_github_target"]["tier"] == "false-positive boundary"
    assert "Bavest/fin-llama" in indexed["researchtrend_github_target"]["availability"]
    assert indexed["release_promise_in_source"]["tier"] == "non-public promise"


def test_prompt_inventory_preserves_missing_runtime_boundary() -> None:
    prompts = rows("prompt_inventory.csv")
    assert len(prompts) == 5
    assert sum(row["publication_form"] == "verbatim simplified template" for row in prompts) == 1
    assert sum(row["status"] == "missing_exact_prompt" for row in prompts) == 3
    assert sum(row["status"] == "missing_training_format" for row in prompts) == 1
    assert all(row["runtime_values_released"] == "False" for row in prompts)
    assert all(row["actual_request_released"] == "False" for row in prompts)
    assert all(row["actual_response_released"] == "False" for row in prompts)
    strategy = next(row for row in prompts if row["prompt_or_request"] == "strategy_code_generator")
    assert strategy["status"] == "simplified_template_only"
    assert "fully disclosed in the appendix" in strategy["note"]


def test_method_ledger_records_pipeline_blockers_explicitly() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 35
    for key in (
        "training_period",
        "strategy_language",
        "initial_capital",
        "position_sizing",
        "signal_to_fill_timing",
        "transaction_costs",
        "slippage",
        "risk_free_rate",
        "baseline_implementations",
        "benchmark_scoring",
        "runtime_environment",
        "actual_llm_requests",
        "generated_strategies",
        "actions_orders_fills",
        "portfolio_trajectories",
    ):
        assert methods[key]["status"].startswith("missing")
    assert methods["system_identity"]["status"] == "specified_high_level"
    assert methods["fine_tuning_data"]["status"] == "specified_source_and_overlapping_dates_only"
    assert methods["randomness_and_repetitions"]["status"] == (
        "missing_seeds_repetitions_uncertainty"
    )


def test_printed_arithmetic_is_separated_from_pipeline_replication() -> None:
    checks = {row["claim_id"]: row for row in rows("arithmetic_audit.csv")}
    assert len(checks) == 6
    assert checks["leakage_improvement_row"]["status"] == (
        "12_of_18_exact_six_hidden_precision_compatible"
    )
    assert "12/18 round exactly" in checks["leakage_improvement_row"]["recomputed_or_comparison"]
    assert "18/18 are within 0.01" in checks["leakage_improvement_row"]["recomputed_or_comparison"]
    assert checks["average_performance_improvements"]["status"] == "displayed_arithmetic_reproduced"
    assert checks["figure_1_decay_rates"]["status"] == (
        "9_of_10_exact_one_hidden_precision_compatible"
    )
    assert "9/10 annotations round exactly" in checks["figure_1_decay_rates"]["recomputed_or_comparison"]
    assert "FinCON TR prints 56.96% versus 56.98%" in checks["figure_1_decay_rates"]["recomputed_or_comparison"]
    assert checks["performance_improvement_row_literal"]["status"] == (
        "17_of_18_literal_matches_one_internal_sign_conflict"
    )
    assert checks["one_point_four_times_sharpe"]["status"] == "claim_not_supported_by_displayed_table"
    assert "1.2394x" in checks["one_point_four_times_sharpe"]["recomputed_or_comparison"]
    assert checks["figure_3_accuracy_gains"]["status"] == "percent_label_is_percentage_point_difference"


def test_material_internal_and_validity_findings_remain_visible() -> None:
    findings = {row["claim_id"]: row for row in rows("internal_consistency_audit.csv")}
    assert len(findings) == 14
    assert findings["benchmark_name"]["status"] == "hard_naming_conflict"
    assert findings["claimed_benchmark_release"]["status"] == "claimed_release_not_recovered"
    assert findings["claimed_template_disclosure"]["status"] == "claim_contradicted_by_source_bundle"
    assert findings["claimed_baseline_details"]["status"] == "claim_contradicted_by_source_bundle"
    assert findings["tsla_finagent_mdd"]["status"] == "hard_internal_value_or_sign_conflict"
    assert findings["finrobot_tsla_mdd_prose"]["status"] == "hard_sign_conflict"
    assert findings["scoring_equation"]["status"] == "metric_definition_conflict"
    assert findings["fine_tune_test_overlap"]["status"] == "temporal_overlap_unresolved"
    assert findings["closed_source_superiority"]["status"] == "claim_contradicted_by_own_table"
    assert findings["causal_leakage_attribution"]["status"] == "causal_claim_not_identified"
    assert findings["sensitivity_as_leakage"]["status"] == "construct_validity_unestablished"


def test_figures_are_inventoried_without_digitization_credit() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 7
    assert sum(int(row["panels"]) for row in figures) == 20
    assert sum(int(row["exact_numeric_result_labels"]) for row in figures) == 82
    assert sum(int(row["plotted_result_series_or_bars"]) for row in figures) == 112
    assert all(row["machine_readable_underlying_results_released"] == "False" for row in figures)
    assert all(row["figure_digitization_is_replication"] == "False" for row in figures)
    assert all(row["status"] == "published_visual_only_zero_result_credit" for row in figures)


def test_current_yahoo_diagnostic_validates_schema_not_results() -> None:
    stats = rows("dataset_statistics_audit.csv")
    buy_hold = rows("buy_hold_diagnostic.csv")
    assert len(stats) == len(buy_hold) == 6
    assert all(row["day_count_exact_match"] == "True" for row in stats)
    assert all(row["original_news_rows_recovered"] == "0" for row in stats)
    assert all(row["original_counterfactual_scenarios_recovered"] == "0" for row in stats)
    assert all(row["paper_result_credit"] == "False" for row in stats)
    assert all(row["close_display_precision_match"] == "False" for row in buy_hold)
    assert all(row["adjusted_close_display_precision_match"] == "False" for row in buy_hold)
    assert all(row["native_original_snapshot_recovered"] == "False" for row in buy_hold)
    assert all(row["paper_result_credit"] == "False" for row in buy_hold)


def test_manifest_hashes_every_output_and_readme_is_honest() -> None:
    data = manifest()
    expected = {
        path.name
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "Overall verdict: **not reproduced**" in text
    assert "**Zero of 525**" in text
    assert "not proof" in text
    assert "does not call them byte-identical" in text
    assert "reproduces **0/6** Buy-and-Hold" in text
    assert "--strict" in text and "exits\nnonzero" in text
