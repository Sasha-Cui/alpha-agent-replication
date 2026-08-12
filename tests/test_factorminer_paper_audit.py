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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/factorminer"
SPEC = importlib.util.spec_from_file_location(
    "audit_factorminer_paper", ROOT / "scripts/audit_factorminer_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_official_source_is_pinned_rebuilt_and_visually_checked() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1"]
    assert data["official_pdf_and_source_recovered"] is True
    assert data["official_document_rebuild_completed"] is True
    assert data["official_pages_visually_checked"] == 20
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    arxiv = provenance["arxiv"]
    assert arxiv["id"] == "2602.14670"
    assert arxiv["submitted"] == "2026-02-16"
    assert arxiv["pages"] == arxiv["rebuild_pages"] == 20
    assert arxiv["source_files"] == 33
    assert arxiv["rebuild_token_multiset_jaccard"] > 0.9997
    assert arxiv["visual_qa"] == {
        "pages_inspected": 20,
        "unreadable_clipped_or_overlapping_pages": 0,
    }


def test_all_printed_formulas_execute_only_as_independent_components() -> None:
    formulas = rows("formula_component_ledger.csv")
    assert len(formulas) == 110
    assert len({row["formula"] for row in formulas}) == 110
    assert {row["factor_id"] for row in formulas} == {
        f"{factor_id:03d}" for factor_id in range(1, 111)
    }
    assert all(row["printed_syntax_recovered"] == "True" for row in formulas)
    assert all(row["independent_exact_syntax_parsed"] == "True" for row in formulas)
    assert all(
        row["independent_synthetic_evaluation_completed"] == "True"
        for row in formulas
    )
    assert all(int(row["finite_synthetic_values"]) > 0 for row in formulas)
    assert all(row["semantic_operator_contract_author_released"] == "False" for row in formulas)
    assert all(row["author_native_runtime_used"] == "False" for row in formulas)
    assert all(row["paper_market_data_used"] == "False" for row in formulas)
    assert all(row["reported_result_lineage_verified"] == "False" for row in formulas)
    assert all(row["paper_result_credit"] == "False" for row in formulas)
    component = json.loads((AUDIT_DIR / "independent_formula_execution.json").read_text())
    assert component["printed_formula_count"] == 110
    assert len(component["printed_formula_operator_names"]) == 39
    assert component["independent_exact_formula_parse_count"] == 110
    assert component["independent_exact_formula_synthetic_evaluation_count"] == 110
    assert component["independent_normalized_catalog_exact_formula_matches"] == 2
    assert component["independent_normalized_catalog_exact_name_matches"] == 3
    assert component["author_native_code_used"] is False
    assert component["paper_result_credit"] is False


def test_result_and_figure_denominators_keep_native_credit_zero() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 488
    assert Counter(row["table"] for row in results) == {
        "main_results_top40": 308,
        "gpu_speedup": 15,
        "combination_110": 27,
        "selection_110": 30,
        "lasso_selected": 8,
        "stepwise_trajectory": 71,
        "xgboost_importance": 20,
        "factor046_tearsheet": 9,
    }
    assert all(row["native_pipeline_executed"] == "False" for row in results)
    assert all(row["native_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    figures = rows("figure_inventory.csv")
    assert len(figures) == 9
    assert sum(int(row["empirical_vector_pdf_panels"]) for row in figures) == 27
    assert sum(int(row["visible_numeric_annotations"]) for row in figures) == 12134
    assert all(row["underlying_numeric_array_released"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)
    data = manifest()
    assert data["published_numeric_table_cells"] == 488
    assert data["published_heatmap_numeric_annotations"] == 12100
    assert data["published_other_exact_figure_annotations"] == 34
    assert data["native_numeric_table_cells_regenerated"] == 0
    assert data["native_heatmap_cells_regenerated"] == 0
    assert data["native_figure_panels_regenerated"] == 0


def test_heatmap_is_self_consistent_but_conflicts_with_caption_and_catalog() -> None:
    heatmap = json.loads((AUDIT_DIR / "heatmap_audit.json").read_text())
    assert heatmap["shape"] == [110, 110]
    assert heatmap["printed_numeric_annotations"] == 12100
    assert heatmap["unique_offdiagonal_pairs"] == 5995
    assert heatmap["printed_mean_absolute_offdiagonal"] == pytest.approx(
        0.1931693077564637
    )
    assert heatmap["printed_mean_absolute_including_diagonal"] == pytest.approx(
        0.20050413223140498
    )
    assert heatmap["caption_claimed_average_absolute_correlation"] == 0.203
    assert heatmap["pairs_strictly_above_admission_threshold_0_5"] == 15
    assert heatmap["pairs_at_or_above_admission_threshold_0_5"] == 27
    assert heatmap["maximum_printed_absolute_offdiagonal"] == 0.55
    assert heatmap["appendix_heatmap_name_prefix_matches"] == 100
    assert heatmap["appendix_heatmap_name_mismatches"] == 10
    assert heatmap["mismatching_factor_ids"] == [
        "012", "016", "040", "049", "051", "055", "107", "108", "109", "110"
    ]
    assert heatmap["raw_matrix_released"] is False
    assert heatmap["result_lineage_verified"] is False


def test_internal_consistency_audit_records_material_conflicts() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert len(checks) == 12
    assert checks["main_table_global_best_claim"]["status"] == "overbroad"
    assert "29/44" in checks["main_table_global_best_claim"]["detail"]
    assert checks["main_vs_ensemble_prose"]["status"] == "protocol_or_version_mismatch"
    assert checks["heatmap_caption_average"]["status"] == "does_not_match_printed_matrix"
    assert checks["heatmap_admission_constraint"]["status"] == "visible_threshold_violations"
    assert checks["heatmap_formula_catalog_lineage"]["status"] == "catalog_mismatch"
    assert checks["factor046_financial_logic"]["status"] == "formula_description_conflict"
    assert checks["factor046_turnover_units"]["status"] == "hundredfold_display_conflict"
    assert checks["xgboost_top20_total"]["status"] == "arithmetic_conflict"
    assert "43.13%" in checks["xgboost_top20_total"]["detail"]
    assert checks["model_test_chronology"]["status"] == "prospective_interpretation_impossible"


def test_method_and_model_boundaries_are_fail_closed() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 25
    assert methods["printed_factor_formulas"]["status"] == "complete_syntax_only"
    assert methods["operator_registry"]["status"] == "partial"
    assert methods["formula_semantics"]["status"] == "ambiguous"
    for dimension in (
        "native_source", "a_share_universes", "crypto_universe", "market_data",
        "prompts", "model_parameters", "random_seeds", "baseline_implementations",
        "runtime_environment", "raw_results", "prospective_freeze",
    ):
        assert methods[dimension]["status"] == "missing"
    chronology = json.loads((AUDIT_DIR / "model_release_chronology.json").read_text())
    assert chronology["first_public_date"] == "2025-12-17"
    assert chronology["literal_model_available_before_2025_test_window"] is False
    assert chronology["retrospective_data_layer_holdout_possible"] is True
    assert chronology["retrospective_data_layer_holdout_verified"] is False


def test_discovery_does_not_promote_post_paper_interpretation_to_native() -> None:
    discovery = rows("discovery_evidence.csv")
    assert len(discovery) == 6
    assert all(row["attributable_native_artifact_recovered"] == "False" for row in discovery)
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    independent = provenance["independent_implementation"]
    assert independent["repository_created"] == "2026-02-26"
    assert independent["paper_submitted"] == "2026-02-16"
    assert independent["owner_public_name"] == "aaron"
    assert independent["author_attribution_evidence_recovered"] is False
    assert independent["classification"] == "unaffiliated_post_paper_interpretation"
    boundary = provenance["release_boundary"]
    assert boundary["attributable_native_implementation_recovered"] is False
    assert boundary["exact_printed_formula_syntax_recovered"] is True
    assert boundary["complete_author_operator_semantics_recovered"] is False
    assert boundary["reported_results_linked_to_appendix_formula_catalog"] is False
    assert boundary["bounded_negative_search_is_proof_of_nonexistence"] is False


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned FactorMiner primary-source scratch is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_factorminer_paper.py"), "--output", str(tmp_path / "strict"), "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict = json.loads((tmp_path / "strict/manifest.json").read_text())
    assert strict["full_end_to_end_pipeline_reproduced"] is False


def test_manifest_hashes_every_output_and_readme_states_boundary() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "native FactorMiner experiment is **not reproduced**" in text
    assert "all 110 exact strings" in text
    assert "only 2/110 printed formulas exactly" in text
    assert "10 same-ID labels conflict" in text
    assert "29/44" in text
    assert "unaffiliated interpretation" in text
