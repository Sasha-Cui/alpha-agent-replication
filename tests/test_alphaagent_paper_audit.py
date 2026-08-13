from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alphaagent_paper.py"
SPEC = importlib.util.spec_from_file_location("alphaagent_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_targets_cover_all_numeric_table_cells() -> None:
    rows = audit.paper_numeric_rows()
    assert len(rows) == 106
    assert Counter(row["paper_table"] for row in rows) == {1: 6, 2: 100}
    assert Counter(row["cell_role"] for row in rows) == {
        "result": 100,
        "configuration": 6,
    }
    assert len(
        {
            (
                row["paper_table"],
                row["entity"],
                row["market"],
                row["period"],
                row["metric"],
            )
            for row in rows
        }
    ) == 106


def test_non_table_claims_preserve_result_boundary() -> None:
    rows = audit.published_non_table_claims()
    assert len(rows) == 26
    assert Counter(row["claim_role"] for row in rows) == {
        "result": 18,
        "configuration": 8,
    }
    assert {row["paper_result_credit"] for row in rows} == {False}


def test_committed_audit_is_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/alphaagent"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    table = read_csv(output / "tables_1_2_conformance.csv")
    claims = read_csv(output / "published_non_table_claims.csv")
    mechanisms = read_csv(output / "source_mechanism_conformance.csv")
    current_mechanisms = read_csv(output / "current_rewrite_mechanism_conformance.csv")
    history = read_csv(output / "official_history_timeline.csv")
    gaps = read_csv(output / "paper_specification_gaps.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    paper_era_inventory = read_csv(output / "paper_era_source_inventory.csv")
    paper_era_factors = read_csv(output / "paper_era_factor_artifacts.csv")
    paper_era_runs = read_csv(output / "paper_era_mlflow_run_records.csv")
    registry = read_csv(output / "post_paper_registry_metrics.csv")
    data_release = read_csv(output / "data_release_provenance.csv")
    factors = read_csv(output / "synthetic_base_factor_component.csv")
    component = json.loads((output / "native_component.json").read_text(encoding="utf-8"))
    paper_era_component = json.loads(
        (output / "paper_era_component.json").read_text(encoding="utf-8")
    )

    assert manifest["overall_status"] == (
        "partially_corroborated_paper_era_native_run_records_recovered"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_era_source_revision_available"] is True
    assert manifest["paper_v1_sha256"] == audit.PAPER_V1_SHA256
    assert manifest["paper_mechanism_commit"] == audit.PAPER_MECHANISM_COMMIT
    assert manifest["official_git_history"] == {
        "is_shallow": False,
        "reachable_commits": 493,
        "current_main_commits": 8,
        "legacy_main_commits": 485,
        "root_commits": sorted([audit.SOURCE_FIRST_COMMIT, audit.LEGACY_ROOT_COMMIT]),
        "current_and_legacy_have_common_ancestor": False,
        "paper_mechanism_is_legacy_ancestor": True,
        "preprint_cutoff_is_legacy_ancestor": True,
        "paper_mechanism_files": 856,
        "paper_mechanism_python_files": 331,
        "paper_mechanism_factor_csvs": 15,
        "preprint_cutoff_factor_csvs": 0,
    }
    assert manifest["paper_numeric_table_cells_total"] == 106
    assert manifest["paper_numeric_result_cells_total"] == 100
    assert manifest["native_paper_table_result_cells_reproduced"] == 0
    assert manifest["native_paper_table_result_cells_corroborated"] == 5
    assert manifest["paper_table_result_cells_unavailable"] == 95
    assert manifest["published_non_table_result_claims_total"] == 18
    assert manifest["native_non_table_result_claims_reproduced"] == 0
    assert manifest["paper_specification_gaps_total"] == 17
    assert manifest["source_mechanism_dimensions_total"] == 32
    assert manifest["source_mechanism_component_matches_or_analogues"] == 20
    assert manifest["source_mechanism_fully_faithful"] is False
    assert manifest["paper_era_tracked_files_total"] == 856
    assert manifest["paper_era_python_files_compiled"] == 331
    assert manifest["paper_era_factor_csv_files"] == 15
    assert manifest["paper_era_factor_expression_rows"] == 268
    assert manifest["paper_era_qlib_mlflow_run_records"] == 7
    assert manifest["paper_era_qlib_mlflow_records_with_fitted_models"] == 7
    assert manifest["paper_era_qlib_mlflow_full_table_row_matches"] == 1
    assert manifest["paper_era_qlib_mlflow_display_cells_corroborated"] == 5
    assert manifest["paper_era_named_alpha101_reference_rows"] == 101
    assert manifest["paper_era_loaded_alpha101_csv_rows"] == 116
    assert manifest["paper_era_figure4_candidate_factor_rows"] == 15
    assert manifest["paper_era_figure4_candidate_parseable_rows"] == 14
    assert manifest["paper_era_ast_component_executable"] is True
    assert manifest["post_paper_dsl_expressions_shipped"] == 13
    assert manifest["post_paper_registry_metric_entries"] == 8
    assert manifest["post_paper_registry_entries_receiving_paper_credit"] == 0
    assert manifest["current_post_paper_data_release_available"] is True
    assert manifest["current_post_paper_data_release_bytes"] == 524248466
    assert manifest["current_post_paper_data_release_valid_paper_input"] is False
    assert manifest["native_paper_factor_pool_shipped"] is True
    assert manifest["native_paper_factor_pool_result_lineage_proven"] is False
    assert manifest["native_paper_prompts_shipped"] is True
    assert manifest["native_partial_qlib_mlflow_records_shipped"] is True
    assert manifest["native_paper_metric_scalars_shipped"] is True
    assert manifest["native_paper_prediction_or_return_series_shipped"] is False
    assert manifest["native_paper_holdings_or_complete_qlib_recorders_shipped"] is False
    assert manifest["native_paper_figure_arrays_shipped"] is False
    assert manifest["native_source_tests_passed_with_dependency_stubs"] == 80
    assert manifest["native_source_tests_dependency_faithful"] is False
    assert manifest["native_synthetic_base_factors_executable"] == 4
    assert manifest["native_synthetic_component_paper_result_reproduction"] is False

    assert Counter(row["status"] for row in table) == {
        "corroborated_by_author_history_native_run_artifact": 5,
        "unavailable_missing_native_paper_result_path": 95,
        "paper_configuration_recovered_without_frozen_dataset": 6,
    }
    assert Counter(row["claim_role"] for row in claims) == {
        "result": 18,
        "configuration": 8,
    }
    assert len(mechanisms) == 32
    assert Counter(row["paper_mechanism_credit"] for row in mechanisms) == {
        "False": 12,
        "True": 20,
    }
    assert len(current_mechanisms) == 32
    assert Counter(row["paper_mechanism_credit"] for row in current_mechanisms) == {
        "False": 28,
        "True": 4,
    }
    assert len(history) == 8
    assert len(gaps) == 17
    assert len(inventory) == 141
    assert len(paper_era_inventory) == 856
    assert {row["paper_era_artifact"] for row in paper_era_inventory} == {"True"}
    assert {row["paper_result_credit"] for row in paper_era_inventory} == {"False"}
    assert len(paper_era_factors) == 15
    assert sum(int(row["expression_rows"]) for row in paper_era_factors) == 268
    alpha101 = next(
        row for row in paper_era_factors if row["path"] == "factor_zoo/alpha101.csv"
    )
    assert int(alpha101["expression_rows"]) == 116
    assert int(alpha101["alpha101_reference_rows"]) == 101
    assert int(alpha101["other_expression_rows"]) == 15
    assert len(paper_era_runs) == 7
    assert sum(int(row["tracked_files"]) for row in paper_era_runs) == 385
    for hash_field in (
        "config_sha256",
        "dataset_sha256",
        "task_sha256",
        "fitted_lightgbm_state_sha256",
    ):
        assert all(len(row[hash_field]) == 64 for row in paper_era_runs)
    exact_runs = [row for row in paper_era_runs if row["all_five_display_cells_match"] == "True"]
    assert [row["run_id"] for row in exact_runs] == [
        "77b227f86e5a47bab48178cac409a98b"
    ]
    assert exact_runs[0]["market"] == "S&P500"
    assert int(exact_runs[0]["display_cells_matching_alphaagent_row"]) == 5
    assert int(exact_runs[0]["paper_result_cells_corroborated"]) == 5
    assert int(exact_runs[0]["generated_factor_features"]) == 5
    assert {row["predictions_returns_holdings_shipped"] for row in paper_era_runs} == {"False"}
    assert len(registry) == 8
    assert {row["paper_result_credit"] for row in registry} == {"False"}
    assert len(data_release) == 1
    assert data_release[0]["paper_data_credit"] == "False"
    assert int(data_release[0]["bytes"]) == 524248466
    assert len(factors) == 4
    assert {row["native_parser_executable"] for row in factors} == {"True"}
    assert {row["paper_metric_reproduced"] for row in factors} == {"False"}
    assert component["upstream_tests"]["tests_passed"] == 80
    assert component["upstream_tests"]["status"] == (
        "passed_with_import_only_dependency_stubs"
    )
    assert component["synthetic_base_factor_component"]["deterministic"] is True
    assert component["synthetic_base_factor_component"]["sha256"] == (
        "e0bd090308b893c6bcf97cc1589538e4fcedc4a896bb90d21a0848e92d7a5dc9"
    )
    assert component["paper_result_reproduction"] is False
    assert paper_era_component["compile_passed"] is True
    assert paper_era_component["python_files_compiled"] == 331
    assert paper_era_component["ast_component_deterministic"] is True
    assert paper_era_component["identical_expression_lcs_size"] == 4
    assert paper_era_component["commutative_expression_lcs_size"] == 3
    assert paper_era_component["partial_expression_lcs_size"] == 3
    assert paper_era_component["named_alpha101_reference_rows"] == 101
    assert paper_era_component["loaded_alpha101_csv_rows"] == 116
    assert paper_era_component["alpha101_self_match_exact"] is True
    assert paper_era_component["figure4_candidate_factor_rows"] == 15
    assert paper_era_component["figure4_candidate_parseable_rows"] == 14
    assert paper_era_component["figure4_candidate_parse_failures"] == [
        "Lagged_Volume_Change_Factor_3D"
    ]
    assert paper_era_component["paper_result_reproduction"] is False

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_source_static_checks_when_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_source")
    if not source_root.exists():
        return
    assert audit.git_head(source_root) == audit.SOURCE_COMMIT
    first_commit, first_date = audit.git_first_commit(source_root)
    assert first_commit == audit.SOURCE_FIRST_COMMIT
    assert first_date.startswith("2026-07-01")
    history, timeline = audit.history_audit(source_root)
    assert history["legacy_main_commits"] == 485
    assert history["current_and_legacy_have_common_ancestor"] is False
    assert history["paper_mechanism_files"] == 856
    assert history["preprint_cutoff_factor_csvs"] == 0
    assert len(timeline) == 8

    current = {
        row["dimension"]: row
        for row in audit.current_source_conformance(source_root)
    }
    assert current["paper_era_source"]["status"] == "mismatch_post_paper_rewrite"
    assert current["largest_common_subtree"]["status"] == "missing"

    with tempfile.TemporaryDirectory() as temp_dir:
        snapshot = Path(temp_dir)
        audit.extract_git_commit(source_root, audit.PAPER_MECHANISM_COMMIT, snapshot)
        mechanisms = {
            row["dimension"]: row
            for row in audit.paper_era_source_conformance(snapshot)
        }
    assert mechanisms["paper_era_source"]["status"] == "recovered_preprint_source"
    assert mechanisms["ast_representation"]["status"] == "component_match"
    assert mechanisms["largest_common_subtree"]["status"] == "component_match"
    assert mechanisms["similarity_kind"]["status"] == "component_match"
    assert mechanisms["paper_lightgbm"]["status"] == "configuration_match"
    assert mechanisms["symbolic_length"]["status"] == "missing"
    assert mechanisms["er_score"]["status"] == "mismatch_hard_filter"
