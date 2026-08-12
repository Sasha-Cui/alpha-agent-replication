from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/chain_of_alpha"
SPEC = importlib.util.spec_from_file_location(
    "audit_chain_of_alpha_paper", ROOT / "scripts/audit_chain_of_alpha_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_all_published_table_cells_are_exhaustive_and_fail_closed() -> None:
    ledger = audit.result_ledger()
    assert len(ledger) == 180
    assert Counter(row["table"] for row in ledger) == {
        "Table 1": 132,
        "Table 2": 18,
        "Table 3": 24,
        "Table 4": 6,
    }
    native = [row for row in ledger if row["chain_of_alpha_or_ablation_output"]]
    assert len(native) == 54
    duplicate_groups = Counter(
        row["duplicate_native_measurement_group"]
        for row in native
        if row["duplicate_native_measurement_group"]
    )
    assert duplicate_groups == {f"chain_csi1000_{metric}": 3 for metric in audit.METRICS}
    assert len(native) - sum(value - 1 for value in duplicate_groups.values()) == 42
    assert all(row["native_pipeline_executed"] is False for row in ledger)
    assert all(row["paper_result_credit"] is False for row in ledger)


def test_manifest_records_withdrawal_and_zero_native_results() -> None:
    data = manifest()
    assert data["current_primary_record_withdrawn"] is True
    assert data["current_primary_pdf_available"] is False
    assert data["current_primary_source_available"] is False
    assert data["historical_document_transformation_recovered"] is True
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["published_numeric_result_cells"] == 180
    assert data["chain_or_ablation_numeric_result_cells"] == 54
    assert data["unique_chain_or_ablation_measurements_after_repeated_full_row"] == 42
    assert data["published_result_cells_faithfully_regenerated"] == 0
    assert data["chain_result_cells_faithfully_regenerated"] == 0
    assert data["attributable_system_source_files_recovered"] == 0
    assert data["native_market_rows_predictions_factors_portfolios_or_returns_recovered"] == 0


def test_historical_transformation_is_not_promoted_to_primary_source() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text(encoding="utf-8"))
    assert provenance["current_status"] == "withdrawn; no PDF; no license"
    assert "did not have rights" in provenance["admin_comment"]
    assert provenance["official_pdf_endpoint_status"] == {"v1": 404, "v2": 404}
    assert provenance["official_source_endpoint_status"] == {"v1": 404, "v2": 404}
    assert provenance["independent_frontend_same_bytes"] is True
    assert provenance["historical_authors"] == audit.HISTORICAL_AUTHORS
    assert provenance["numbered_equations"] == 21
    assert provenance["numbered_tables"] == 6
    assert provenance["numbered_figures"] == 4
    assert provenance["data_fields"] == 8
    assert provenance["operators"] == 40
    assert provenance["document_reconstruction_credit"] is False
    assert provenance["author_site_history"]["links_when_present"] == (
        "paper and bibtex only; no code"
    )


def test_published_formula_components_execute_without_result_credit() -> None:
    factors = rows("published_factor_inventory.csv")
    execution = json.loads(
        (AUDIT_DIR / "conditional_formula_execution.json").read_text(encoding="utf-8")
    )
    assert len(factors) == len(execution) == 3
    assert {row["factor"] for row in execution} == {
        "VWAP_Stability_Enhance",
        "Volume_Adjusted_Mean_Corr",
        "VWAP_Flow_Variance_Optimization",
    }
    assert all(row["parser_status"] == "parsed" for row in execution)
    assert all(row["synthetic_output_shape"] == [32, 5] for row in execution)
    assert all(row["finite_values"] > 0 for row in execution)
    assert all(len(row["synthetic_output_sha256"]) == 64 for row in execution)
    assert all(row["native_evaluator_used"] is False for row in execution)
    assert all(row["paper_result_credit"] is False for row in execution)
    assert all(row["conditional_synthetic_execution"] == "True" for row in factors)
    assert all(row["paper_result_credit"] == "False" for row in factors)


def test_operator_field_and_prompt_denominators_are_explicit() -> None:
    operators = rows("operator_inventory.csv")
    fields = rows("data_field_inventory.csv")
    prompts = rows("prompt_inventory.csv")
    assert len(operators) == 40
    assert Counter(row["category"] for row in operators) == {
        "Mathematical": 8,
        "Time Series (rolling)": 15,
        "Regression (rolling)": 3,
        "Statistical (rolling)": 4,
        "Conditional": 7,
        "Logical": 3,
    }
    assert len(fields) == 8
    assert {row["field"] for row in fields} == {
        "$open", "$high", "$low", "$close", "$volume", "$amount", "$change", "$vwap"
    }
    assert len(prompts) == 2
    assert {row["runtime_slots"] for row in prompts} == {"4", "10"}
    assert all(row["publication_status"] == "paper explicitly calls it a demo version" for row in prompts)
    assert all(row["actual_filled_prompt_released"] == "False" for row in prompts)
    assert all(row["native_prompt_credit"] == "False" for row in prompts)


def test_displayed_arithmetic_and_real_paper_conflicts_are_audited() -> None:
    checks = {row["claim_id"]: row for row in rows("internal_consistency_audit.csv")}
    assert len(checks) == 15
    assert checks["table1_best_10_of_12"]["status"] == "passes_displayed_arithmetic"
    assert checks["ablation_optimization_ar"]["status"] == "hard_prose_table_conflict"
    assert checks["ablation_generation_ir"]["status"] == "hard_prose_table_conflict"
    assert checks["all_backbones_all_metrics"]["status"] == "claim_contradicted_by_displayed_table"
    assert "GPT-4o': 6" in checks["all_backbones_all_metrics"]["audit_finding"]
    assert "DeepSeek-V3': 4" in checks["all_backbones_all_metrics"]["audit_finding"]
    assert "Qwen3-32B': 4" in checks["all_backbones_all_metrics"]["audit_finding"]
    assert checks["production_prompt_boundary"]["status"] == "demo_not_runtime_prompt"
    assert checks["diversity_definition"]["status"] == "hard_metric_definition_conflict"
    assert checks["formula_1_units"]["status"] == "published_formula_not_unitless"
    assert checks["formula_3_units"]["status"] == "published_formula_not_unitless"
    assert all(row["paper_result_credit"] == "False" for row in checks.values())


def test_method_ledger_records_experiment_blockers_not_dependency_gaps() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 30
    for dimension in (
        "data_vendor_snapshot",
        "point_in_time_membership",
        "price_adjustments",
        "actual_factor_pool",
        "llm_requests_responses",
        "expression_parser",
        "integration_randomness",
        "portfolio_edge_cases",
        "environment",
        "result_arrays",
        "uncertainty",
    ):
        assert methods[dimension]["status"] == "missing"
    assert methods["prompts"]["status"] == "demo_only"
    assert methods["operator_semantics"]["status"] == "underspecified"
    assert methods["factor_thresholds"]["status"] == "specified_with_conflict"
    assert methods["portfolio"]["status"] == "specified_partial"
    assert methods["costs"]["status"] == "specified"


def test_unaffiliated_candidates_are_executed_only_as_adaptations() -> None:
    candidates = rows("candidate_adaptation_audit.csv")
    execution = json.loads(
        (AUDIT_DIR / "adaptation_component_execution.json").read_text(encoding="utf-8")
    )
    assert len(candidates) == 3
    assert {row["repository"] for row in candidates} == {
        "skipsuzuki/Chain-of-Alpha",
        "Haoyu-tech/LLM---Factor-generation",
        "lavender1203/worldquant-alpha-aiac",
    }
    assert {row["python_files_compiled"] for row in candidates} == {"0", "34", "150"}
    assert all(row["repeated_archive_byte_identical"] == "True" for row in candidates)
    assert all(row["repository_license_file"] == "absent" for row in candidates)
    assert all(row["author_attribution_recovered"] == "False" for row in candidates)
    assert all(row["native_chain_of_alpha_credit"] == "False" for row in candidates)
    assert all(row["paper_result_credit"] == "False" for row in candidates)
    assert execution["synthetic_variants_returned"] == 5
    assert execution["executed_component"] == "backend.optimization_chain.generate_local_rewrites"
    assert execution["classification"] == "unaffiliated post-paper deterministic inspired component"
    assert execution["paper_result_credit"] is False


def test_figures_and_searches_keep_result_and_negative_search_boundaries() -> None:
    figures = rows("figure_inventory.csv")
    discovery = rows("discovery_evidence.csv")
    assert len(figures) == 4
    assert sum(int(row["panels"]) for row in figures) == 5
    assert sum(int(row["empirical_curve_series"]) for row in figures) == 9
    assert all(row["underlying_dated_result_array_released"] == "False" for row in figures)
    assert all(row["native_pipeline_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)
    assert len(discovery) == 10
    assert all(row["attributable_system_recovered"] == "False" for row in discovery)
    assert all("not proof" in row["negative_search_limit"] for row in discovery)


def test_manifest_hashes_every_output_and_readme_is_honest() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "Overall verdict: **not reproduced**" in text
    assert "**Zero of 180**" in text
    assert "bounded public search, not" in text
    assert "demo versions" in text
    assert "Installing packages does not close the gap" in text


def test_paper_route_records_completed_audit_without_inventing_public_code() -> None:
    route = ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    with route.open(newline="", encoding="utf-8") as stream:
        selected = [row for row in csv.DictReader(stream) if row["canonical_work_id"] == audit.WORK_ID]
    assert len(selected) == 1
    row = selected[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_180_result_cells_withdrawn_no_attributable_system"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert "0/180 result cells" in row["precise_native_or_access_blocker"]
    assert "current arXiv withdrawal" in row["precise_native_or_access_blocker"]
    assert "demo prompts" in row["precise_native_or_access_blocker"]
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
