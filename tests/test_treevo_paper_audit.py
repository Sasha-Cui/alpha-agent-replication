from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/treevo"
SPEC = importlib.util.spec_from_file_location(
    "audit_treevo_paper", ROOT / "scripts/audit_treevo_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_both_official_versions_are_byte_pinned_and_source_rebuilt() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1", "v2"]
    assert data["official_pdf_and_source_recovered"] is True
    assert data["official_document_rebuilds_completed"] == 2
    provenance = json.loads(
        (AUDIT_DIR / "source_provenance.json").read_text(encoding="utf-8")
    )
    assert provenance["repeated_downloads_byte_identical"] is True
    assert provenance["current_abs_repeated_byte_identical"] is True
    assert provenance["versions"]["v1"]["pdf_pages"] == 9
    assert provenance["versions"]["v2"]["pdf_pages"] == 17
    assert provenance["versions"]["v1"]["source_files"] == 16
    assert provenance["versions"]["v2"]["source_files"] == 28
    assert provenance["versions"]["v1"]["rebuild_token_multiset_jaccard"] > 0.998
    assert provenance["versions"]["v2"]["rebuild_token_multiset_jaccard"] > 0.999
    assert provenance["visual_qa"] == {
        "unreadable_or_clipped_pages": 0,
        "v1_pages_inspected": 9,
        "v2_pages_inspected": 17,
    }
    assert provenance["document_reconstruction_credit"] is True
    assert provenance["native_system_source_credit"] is False


def test_complete_versioned_result_denominators_remain_zero_native() -> None:
    v1 = rows("published_result_ledger_v1.csv")
    v2 = rows("published_result_ledger_v2.csv")
    figure_v1 = rows("exact_figure_result_ledger_v1.csv")
    figure_v2 = rows("exact_figure_result_ledger_v2.csv")
    assert len(v1) == manifest()["published_numeric_table_result_cells_v1"] == 96
    assert len(v2) == manifest()["published_numeric_table_result_cells_v2"] == 206
    assert Counter(row["table"] for row in v1) == {"Table 1": 48, "Table 2": 48}
    assert Counter(row["table"] for row in v2) == {
        "Table 1": 56,
        "Table 2": 48,
        "Table 4": 10,
        "Table 5": 24,
        "Table 6": 32,
        "Table 7": 36,
    }
    assert sum(row["treevo_output"] == "True" for row in v1) == 24
    assert sum(row["treevo_output"] == "True" for row in v2) == 78
    assert len(figure_v1) == manifest()["published_exact_figure_numeric_units_v1"] == 18
    assert len(figure_v2) == manifest()["published_exact_figure_numeric_units_v2"] == 87
    assert Counter(row["figure"] for row in figure_v2) == {
        "Figure 6": 12,
        "Figure 8": 75,
    }
    assert Counter(row["duplicate_kind"] for row in figure_v2) == {
        "none": 34,
        "same_value_as_table_cell": 8,
        "symmetric_matrix_duplicate": 30,
        "structural_correlation_diagonal": 15,
    }
    assert manifest()["published_numeric_result_units_v1"] == 114
    assert manifest()["published_numeric_result_units_v2"] == 293
    assert manifest()["figure_numeric_units_with_independent_information_v1"] == 18
    assert manifest()["figure_numeric_units_with_independent_information_v2"] == 34
    v1_runs = {
        (row["panel"], row["series"], row["coordinate"]): row["rendered_value"]
        for row in figure_v1
    }
    assert v1_runs[("CSI300", "TreEvo", "Run 3")] == "0.0688"
    assert v1_runs[("CSI500", "ReEvo", "Run 1")] == "0.0367"
    figure8 = {
        (row["panel"], row["series"], row["coordinate"]): row
        for row in figure_v2 if row["figure"] == "Figure 8"
    }
    assert figure8[("EoH", "Factor 1", "Factor 3")]["rendered_value"] == "-0.91"
    assert figure8[("EoH", "Factor 3", "Factor 1")]["duplicate_kind"] == (
        "symmetric_matrix_duplicate"
    )
    assert figure8[("TreEvo", "Factor 4", "Factor 5")]["rendered_value"] == "-0.64"
    assert all(row["native_pipeline_executed"] == "False" for row in v1 + v2)
    assert all(row["paper_result_credit"] == "False" for row in v1 + v2)
    assert all(row["native_pipeline_regenerated"] == "False" for row in figure_v1 + figure_v2)
    assert all(row["paper_result_credit"] == "False" for row in figure_v1 + figure_v2)
    data = manifest()
    assert data["published_result_cells_faithfully_regenerated_v1"] == 0
    assert data["published_result_cells_faithfully_regenerated_v2"] == 0
    assert data["full_end_to_end_pipeline_reproduced"] is False


def test_prompts_operators_and_figures_have_explicit_component_boundaries() -> None:
    prompts = rows("prompt_inventory.csv")
    operators = rows("operator_inventory.csv")
    figures = rows("figure_inventory.csv")
    assert len(prompts) == 7
    assert sum(int(row["runtime_slots"]) for row in prompts) == 7
    assert all(row["exact_template_recovered"] == "True" for row in prompts)
    assert all(row["actual_filled_request_recovered"] == "False" for row in prompts)
    assert all(row["response_recovered"] == "False" for row in prompts)
    assert all(row["native_prompt_call_credit"] == "False" for row in prompts)
    assert len(operators) == 22
    assert Counter(row["category"] for row in operators) == {
        "Cross-Section": 8,
        "Time-Series": 14,
    }
    assert all(row["native_semantics_released"] == "False" for row in operators)
    assert Counter(row["version"] for row in figures) == {"v1": 5, "v2": 8}
    assert sum(int(row["panels"]) for row in figures if row["version"] == "v1") == 11
    assert sum(int(row["panels"]) for row in figures if row["version"] == "v2") == 23
    assert all(row["full_resolution_visually_inspected"] == "True" for row in figures)
    assert all(row["legible_and_unclipped"] == "True" for row in figures)
    assert all(row["underlying_numeric_array_released"] == "False" for row in figures)


def test_metric_equations_execute_only_as_synthetic_components() -> None:
    execution = json.loads(
        (AUDIT_DIR / "conditional_metric_execution.json").read_text(encoding="utf-8")
    )
    assert execution["classification"] == (
        "audit-declared synthetic metric-equation component"
    )
    assert execution["days"] == 12 and execution["stocks"] == 5
    assert len(execution["daily_metrics_sha256"]) == 64
    assert execution["paper_market_data_used"] is False
    assert execution["native_evaluator_used"] is False
    assert execution["paper_result_credit"] is False


def test_displayed_arithmetic_revision_conflicts_and_model_timing_are_audited() -> None:
    checks = {row["claim_id"]: row for row in rows("internal_consistency_audit.csv")}
    assert len(checks) == 15
    assert checks["v2_table2_14_31_percent"]["status"] == (
        "passes_displayed_arithmetic"
    )
    assert "14.3148%" in checks["v2_table2_14_31_percent"]["audit_finding"]
    assert checks["v2_eoh_beats_reevo_all_cases"]["status"] == (
        "claim_contradicted_by_displayed_table"
    )
    assert "6/8" in checks["v2_eoh_beats_reevo_all_cases"]["audit_finding"]
    assert checks["v2_duplicate_treevo_std"]["status"] == (
        "hard_same_version_table_conflict"
    )
    assert checks["v1_framework_population"]["status"] == (
        "hard_method_description_conflict"
    )
    assert checks["v1_figure5_table2_mismatch"]["status"] == (
        "unresolved_same_version_result_mismatch"
    )
    assert checks["model_release_timing"]["status"] == (
        "unresolved_public_provenance_conflict"
    )
    assert "private prerelease is possible" in checks["model_release_timing"][
        "audit_finding"
    ]
    assert checks["code_generation_prompt"]["status"] == "missing_native_prompt"
    revisions = {row["dimension"]: row for row in rows("version_revision_audit.csv")}
    assert revisions["us_universe"]["v1"] == "SPX, DJI"
    assert revisions["us_universe"]["v2"] == "SPX, NDX"
    assert revisions["table_result_cells"]["v1"] == "96"
    assert revisions["table_result_cells"]["v2"] == "206"
    assert revisions["exact_figure_numeric_units"]["v1"] == "18"
    assert revisions["exact_figure_numeric_units"]["v2"] == "87"
    assert revisions["native_result_reproduction"]["v1"] == "0/114"
    assert revisions["native_result_reproduction"]["v2"] == "0/293"


def test_method_ledger_identifies_scientific_inputs_not_package_gaps() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 31
    for dimension in (
        "data_vendor_snapshot",
        "calendar_timezone",
        "membership_delistings",
        "metric_edge_cases",
        "sampling_parameters",
        "seed_trees",
        "parent_selection",
        "code_generation",
        "sandbox_validation",
        "random_seeds",
        "baseline_versions",
        "costs",
        "factor_outputs",
        "raw_results",
        "environment",
    ):
        assert methods[dimension]["status"] == "missing"
    assert methods["prompt_templates"]["status"] == "partial"
    assert methods["population"]["status"] == "specified"
    assert methods["mutation_probabilities"]["status"] == "specified"
    assert methods["llm_primary"]["status"] == "ambiguous"


def test_bounded_search_and_author_pages_do_not_invent_public_code() -> None:
    discovery = rows("discovery_evidence.csv")
    assert len(discovery) == 9
    assert all(
        row["attributable_treevo_system_recovered"] == "False"
        for row in discovery
    )
    assert all("not proof" in row["negative_search_limit"] for row in discovery)
    provenance = json.loads(
        (AUDIT_DIR / "source_provenance.json").read_text(encoding="utf-8")
    )
    author = provenance["author_page_boundary"]
    assert author["peng_yang_page_lists_v1"] is True
    assert author["peng_yang_page_code_link_for_treevo"] is False
    assert author["shengcai_liu_page_lists_code_links_for_other_papers"] is True
    assert manifest()["attributable_implementation_source_files_recovered"] == 0


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned TreEvo primary-source scratch is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {
        path.name: path.read_bytes() for path in first.iterdir()
    } == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audit_treevo_paper.py"),
            "--output",
            str(tmp_path / "strict"),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict_manifest = json.loads(
        (tmp_path / "strict/manifest.json").read_text(encoding="utf-8")
    )
    assert strict_manifest["full_end_to_end_pipeline_reproduced"] is False


def test_manifest_hashes_outputs_and_readme_states_honest_boundary() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "native TreEvo\nexperiment not reproduced" in text
    assert "**0/114 for v1 and 0/293 for v2**" in text
    assert "Installing packages cannot reconstruct" in text
    assert "bounded public search" in text


def test_paper_route_records_completed_audit_without_inventing_code() -> None:
    route = ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    with route.open(newline="", encoding="utf-8") as stream:
        selected = [
            row for row in csv.DictReader(stream)
            if row["canonical_work_id"] == audit.WORK_ID
        ]
    assert len(selected) == 1
    row = selected[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_v1_zero_of_114_v2_zero_of_293_"
        "seven_prompt_templates_no_attributable_pipeline"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    blocker = row["precise_native_or_access_blocker"]
    assert "0/114 v1" in blocker and "0/293 v2" in blocker
    assert "seven v2 tree/operator prompt templates" in blocker
    assert "Qwen3-Max" in blocker
    assert row["proxy_role"] == "no_proxy"
