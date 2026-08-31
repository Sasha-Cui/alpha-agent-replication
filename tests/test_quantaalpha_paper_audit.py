from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_quantaalpha_paper.py"
SPEC = importlib.util.spec_from_file_location("quantaalpha_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_complete_numeric_table_census_is_fail_closed() -> None:
    rows = audit.paper_table_rows()
    assert len(rows) == 344
    assert Counter(row["paper_table"] for row in rows) == {
        "Table 1 Main CSI300 results": 196,
        "Table 2 Evolution-component ablation": 28,
        "Appendix Table 2 Cross-seed core metrics": 12,
        "Appendix Table 3 Cross-seed variance": 16,
        "Appendix Table 4 Daily IC statistics": 28,
        "Appendix C Parent trajectory metrics": 6,
        "Appendix C Backtest metrics": 10,
        "Appendix C Detailed statistics": 6,
        "Appendix D Representative factors": 26,
        "Appendix D Factor summary": 16,
    }
    assert sum(row["value_role"] == "displayed_delta" for row in rows) == 12
    assert sum(row["paper_result_credit"] for row in rows) == 8
    assert sum(row["independently_regenerated"] for row in rows) == 8
    assert sum(row["native_reproduced_value"] != "" for row in rows) == 21
    assert Counter(row["author_output_correspondence"] for row in rows) == {
        False: 148,
        True: 196,
    }


def test_numeric_figure_boundary_is_separate_and_complete() -> None:
    labels = audit.figure_label_rows()
    points = audit.plot_point_rows()
    assert len(labels) == 40
    assert Counter(row["figure"] for row in labels) == {
        "Figure 3 quality-gate ablation": 20,
        "Appendix E iterative case-study raster": 17,
        "Appendix C evolution-path diagram": 3,
    }
    assert len(points) == 47
    assert Counter(row["figure_panel"] for row in points) == {
        "Figure 4 IC": 16,
        "Figure 4 Rank IC": 16,
        "Figure 5 evolutionary alpha-mining efficiency": 15,
    }
    assert {row["paper_result_credit"] for row in labels + points} == {False}
    assert Counter(row["author_output_correspondence"] for row in labels) == {
        False: 23,
        True: 17,
    }
    assert {row["author_output_correspondence"] for row in points} == {True}


def test_revision_conflicts_and_missing_artifacts_are_explicit() -> None:
    drift = audit.paper_version_drift()
    checks = {row["check"]: row["status"] for row in audit.internal_and_source_checks()}
    gaps = audit.specification_gaps()
    mechanisms = audit.mechanism_conformance()
    assert len(drift) == 5
    assert {row["status"] for row in drift} == {"large_unexplained_revision"}
    assert drift[0]["v1_value"] == 0.1501 and drift[0]["v3_value"] == 0.0472
    assert checks["Figure 1 curve endpoints versus prose transfer returns"] == "paper_graphic_prose_conflict"
    assert checks["Figure 4 year coverage versus prose"] == "paper_graphic_prose_conflict"
    assert checks["Appendix C factor identity versus evolution diagram"] == "paper_internal_round_conflict"
    assert len(gaps) == 48 and Counter(row["resolved"] for row in gaps) == {
        "no": 42,
        "yes": 3,
        "partial": 3,
    }
    assert len(mechanisms) == 34
    assert Counter(row["status"] for row in mechanisms) == {
        "implemented_match": 15,
        "implemented_analogue": 1,
        "partial_analogue": 2,
        "not_implemented_as_claimed": 7,
        "config_conflict": 4,
        "missing_artifact": 5,
    }
    assert sum(row["paper_mechanism_credit"] for row in mechanisms) == 15


def test_early_paper_main_table_parser_is_fail_closed() -> None:
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_paper")
    if not paper.exists():
        return
    v1 = audit._parse_v1_v2_main_table(paper / "source_v1/tables/main_table.tex")
    v2 = audit._parse_v1_v2_main_table(paper / "source_v2/tables/main_table.tex")
    assert len(v1) == 224 and v1 == v2
    assert Counter(metric for _, metric, _ in v1) == {
        "IC": 28,
        "ICIR": 28,
        "Rank_IC": 28,
        "Rank_ICIR": 28,
        "IR": 28,
        "CR": 28,
        "ARR_pct": 28,
        "MDD_pct": 28,
    }


def test_committed_audit_is_self_hashing_and_separates_outputs_from_regeneration() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/quantaalpha"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output / "native_component_execution.json").read_text(encoding="utf-8"))
    tables = read_csv(output / "paper_numeric_table_conformance.csv")
    labels = read_csv(output / "paper_numeric_figure_labels.csv")
    points = read_csv(output / "paper_plot_point_inventory.csv")
    configs = read_csv(output / "source_config_conformance.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    datasets = read_csv(output / "released_dataset_inventory.csv")
    author_outputs = read_csv(output / "author_output_correspondence.csv")
    history_commits = read_csv(output / "released_source_history_inventory.csv")
    history_paths = read_csv(output / "released_source_history_paths.csv")
    branch_evidence = read_csv(output / "historical_branch_evidence_inventory.csv")
    versioned_tables = read_csv(output / "paper_version_main_table_conformance.csv")
    history_summary = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))
    prepublication_history = read_csv(output / "prepublication_source_history_inventory.csv")
    fork_heads = read_csv(output / "public_fork_unique_head_inventory.csv")
    fork_branch_refs = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    fork_summary = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))
    prepublication_results = read_csv(output / "prepublication_result_conformance.csv")
    recovered_data = read_csv(output / "recovered_data_provenance.csv")
    reruns = read_csv(output / "native_rerun_conformance.csv")
    regeneration = json.loads((output / "native_result_regeneration.json").read_text(encoding="utf-8"))
    deterministic = json.loads(
        (output / "deterministic_baseline_native_evidence.json").read_text(encoding="utf-8")
    )
    complete_recovery = json.loads(
        (output / "complete_pool_factor_recovery.json").read_text(encoding="utf-8")
    )
    complete_result = json.loads(
        (output / "complete_pool_native_result.json").read_text(encoding="utf-8")
    )
    complete_repeats = json.loads(
        (output / "complete_pool_repeatability.json").read_text(encoding="utf-8")
    )
    assert manifest["overall_status"] == (
        "one_baseline_row_plus_one_alpha158_cell_regenerated_main_claim_not_reproduced"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_table_cells_total"] == 344
    assert manifest["native_numeric_table_cells_reproduced"] == 8
    assert manifest["author_output_numeric_table_cells_corroborated"] == 196
    assert manifest["paper_numeric_figure_labels_total"] == 40
    assert manifest["paper_discrete_unlabeled_marker_points_total"] == 47
    assert manifest["author_output_discrete_marker_points_corroborated"] == 47
    assert manifest["paper_raster_return_curves_total"] == 10
    assert manifest["author_output_raster_return_curves_corroborated"] == 10
    assert manifest["author_output_numeric_figure_labels_corroborated"] == 17
    assert manifest["author_output_result_units_corroborated"] == 270
    assert manifest["author_output_assets_byte_identical_to_paper_source"] == 3
    assert manifest["author_output_assets_visually_and_ocr_verified"] == 2
    assert manifest["author_output_result_claims_corroborated"] == 5
    assert manifest["author_output_dated_return_raster_shipped"] is True
    assert manifest["author_output_underlying_arrays_shipped"] is False
    assert manifest["paper_result_arrays_shipped"] == 0
    assert manifest["aggregate_metric_artifacts_shipped_in_prepublication_history"] is True
    assert manifest["paper_factor_pool_shipped"] is True
    assert manifest["paper_baseline_runs_shipped"] is True
    assert manifest["paper_seeds_shipped"] is False
    assert manifest["paper_seeds_field_means_random_or_run_seed_lineage"] is True
    assert manifest["historical_direction_seed_groups_disclosed"] is True
    assert manifest["paper_run_direction_seed_selection_and_order_shipped"] is False
    assert manifest["versioned_main_table_cells_total"] == 644
    assert manifest["versioned_main_table_cells_by_paper_version"] == {
        "v1": 224,
        "v2": 224,
        "v3": 196,
    }
    assert manifest["versioned_main_table_cells_author_output_corroborated"] == 644
    assert manifest["versioned_main_table_cells_independently_regenerated"] == 26
    assert manifest["distinct_author_rendered_main_table_cells_across_versions"] == 420
    assert manifest["historical_v1_v2_main_table_cells_corroborated"] == 224
    assert manifest["historical_v1_v2_main_table_cells_independently_regenerated"] == 9
    assert manifest["prepublication_quantaalpha_specific_commits_total"] == 28
    assert manifest["prepublication_unique_historical_paths_total"] == 851
    assert manifest["github_rest_reported_public_forks"] == 279
    assert manifest["graphql_accessible_public_forks"] == 267
    assert manifest["public_fork_accessibility_gap"] == 12
    assert manifest["public_fork_branch_refs_examined"] == 357
    assert manifest["public_fork_unique_heads_examined"] == 77
    assert manifest["public_fork_divergent_heads_examined"] == 64
    assert manifest["public_fork_author_attributed_post_v1_heads"] == 9
    assert manifest["public_fork_author_attributed_post_v1_extra_commits"] == 28
    assert manifest["public_fork_author_attributed_post_v1_native_result_paths"] == 0
    assert manifest["public_fork_paper_result_artifacts_discovered_post_v1"] == 0
    assert manifest["prepublication_aggregate_result_cells_corresponding_at_paper_rounding"] == 74
    assert manifest["prepublication_aggregate_result_cells_examined"] == 88
    assert manifest["native_rerun_metric_cells_examined"] == 32
    assert manifest["native_rerun_metric_cells_independently_regenerated"] == 9
    assert manifest["alpha158_20_published_metric_cells_independently_regenerated"] == 8
    assert manifest["alpha158_published_metric_cells_independently_regenerated"] == 1
    assert manifest["alpha360_published_metric_cells_independently_regenerated"] == 0
    assert manifest["deterministic_baseline_native_metrics"] == audit.DETERMINISTIC_BASELINE_NATIVE_METRICS
    assert manifest["deterministic_baseline_repeat_runs_each"] == 2
    assert manifest["alpha158_repeat_max_abs_difference"] <= 6e-14
    assert manifest["alpha360_repeat_max_abs_difference"] <= 6e-14
    assert manifest["deterministic_baseline_evidence_sha256"] == audit.DETERMINISTIC_BASELINE_EVIDENCE_SHA256
    assert manifest["deterministic_baseline_driver_sha256"] == audit.DETERMINISTIC_BASELINE_DRIVER_SHA256
    assert manifest["deterministic_baseline_author_checkout_modified"] is False

    assert manifest["quantaalpha_gpt_v1_v2_published_metric_cells_independently_regenerated"] == 0
    assert manifest["quantaalpha_public_custom_factors_recomputed"] == 150
    assert manifest["quantaalpha_complete_pool_total_factors"] == 170
    assert manifest["quantaalpha_complete_pool_compatibility_repairs"] == 1
    assert manifest["quantaalpha_complete_pool_repeat_runs"] == 2
    assert manifest["quantaalpha_complete_pool_repeat_max_abs_difference"] <= 2e-15
    assert manifest["quantaalpha_complete_pool_native_metrics"] == audit.QA_GPT_COMPLETE_170_NATIVE_METRICS
    assert manifest["current_official_ref_surface_is_complete_public_history"] is False
    assert manifest["tracked_source_files_total"] == 237
    assert manifest["tracked_source_python_files_total"] == 135
    assert manifest["native_current_python_files_compiled"] == 135
    assert manifest["native_initial_python_files_compiled"] == 135
    assert manifest["native_component_driver_passed"] is True
    assert manifest["native_upstream_tests_passed"] == 0
    assert manifest["native_upstream_tests_failed"] == 1
    assert manifest["local_motif_proxy_paper_result_credit"] is False
    assert manifest["public_source_branches_total"] == 5
    assert manifest["public_source_tags_total"] == 0
    assert manifest["public_source_releases_total"] == 0
    assert manifest["public_source_reachable_commits_total"] == 61
    assert manifest["public_source_unique_historical_paths_total"] == 259
    assert manifest["public_source_reachable_object_counts"] == {
        "blob": 410,
        "tree": 242,
        "commit": 61,
    }
    assert manifest["public_source_unreachable_objects_total"] == 0
    assert manifest["current_official_ref_native_result_artifact_paths_total"] == 0
    assert manifest["historical_branch_evidence_items_total"] == 8
    assert manifest["historical_direction_seed_groups_total"] == 10
    assert manifest["historical_direction_seed_factor_expressions_total"] == 30
    assert manifest["historical_operational_frontend_files_total"] == 44
    assert len(tables) == 344 and len(labels) == 40 and len(points) == 47
    assert len(configs) == 28 and Counter(row["status"] for row in configs)["conflict"] == 11
    assert len(inventory) == 237
    assert Counter(row["paper_result_artifact"] for row in inventory) == {
        "False": 232,
        "True": 5,
    }
    assert len(author_outputs) == 5
    assert sum(int(row["published_result_units_corroborated"]) for row in author_outputs) == 270
    assert {row["underlying_numeric_arrays_shipped"] for row in author_outputs} == {"0"}
    assert {row["independently_regenerated"] for row in author_outputs} == {"False"}
    assert len(datasets) == 5 and {row["paper_result_artifact"] for row in datasets} == {"False"}
    assert len(history_commits) == 61
    assert {row["native_result_artifact_path_count"] for row in history_commits} == {"0"}
    assert {row["paper_result_credit"] for row in history_commits} == {"False"}
    assert len(history_paths) == 259
    assert {row["native_result_artifact_candidate"] for row in history_paths} == {"False"}
    assert Counter(row["history_role"] for row in history_paths)["author_rendered_result_output"] == 6
    assert len(branch_evidence) == 8
    assert {row["underlying_run_artifact"] for row in branch_evidence} == {"False"}
    assert {row["paper_result_credit"] for row in branch_evidence} == {"False"}
    assert len(versioned_tables) == 644
    assert Counter(row["paper_version"] for row in versioned_tables) == {
        "v1": 224,
        "v2": 224,
        "v3": 196,
    }
    assert {row["author_output_correspondence"] for row in versioned_tables} == {"True"}
    assert Counter(row["independently_regenerated"] for row in versioned_tables) == {
        "False": 618,
        "True": 26,
    }
    assert history_summary["reachable_commits_total"] == 61
    assert history_summary["unique_historical_paths_total"] == 259
    assert history_summary["historical_json_paths_total"] == 8
    assert history_summary["historical_image_blobs_total"] == 13
    assert history_summary["native_result_artifact_paths_total"] == 0
    assert native["component_driver_returncode"] == 0
    assert native["component_checks"]["trajectory_roundtrip"] is True
    assert native["component_checks"]["lineage_roundtrip"] is True
    assert native["component_checks"]["llm_or_market_api_called"] is False
    assert native["component_execution_is_paper_result_credit"] is False
    assert native["paper_experiment_executed"] is True
    assert native["paper_result_cells_reproduced"] == 9
    assert len(prepublication_history) == 28
    assert {row["before_v1_submission"] for row in prepublication_history} == {"True"}
    assert len(fork_heads) == 77
    assert len(fork_branch_refs) == 357
    assert len({row["repository"] for row in fork_branch_refs}) == 267
    assert len({row["head_commit"] for row in fork_branch_refs}) == 77
    assert Counter(row["classification"] for row in fork_heads) == {
        "official_or_prepublication_history_reachable": 13,
        "author_attributed_post_v1_source_config_or_documentation_only": 9,
        "unaffiliated_post_v1_derived_summary_without_raw_lineage": 1,
        "unaffiliated_post_v1_code_config_or_data_extension": 54,
    }
    assert {row["paper_result_credit"] for row in fork_heads} == {"False"}
    assert sum(row["author_attributed_post_v1_lineage"] == "True" for row in fork_heads) == 9
    assert fork_summary["graphql_accessible_forks"] == 267
    assert fork_summary["graphql_accessible_branch_refs"] == 357
    assert fork_summary["representative_unique_head_refs"] == 77
    assert fork_summary["divergent_heads_reviewed"] == 64
    assert fork_summary["author_attributed_post_v1_extra_commits"] == 28
    assert fork_summary["author_attributed_post_v1_changed_paths"] == 259
    assert fork_summary["author_attributed_post_v1_native_result_paths"] == 0
    assert fork_summary["author_attributed_post_v1_new_image_path"] == "docs/images/WeChat.jpg"
    assert fork_summary["paper_result_artifacts_discovered_in_post_v1_fork_heads"] == 0
    assert len(prepublication_results) == 88
    assert Counter(row["rounded_match"] for row in prepublication_results) == {"True": 74, "False": 14}
    assert {row["independently_regenerated"] for row in prepublication_results} == {"False"}
    assert len(recovered_data) == 3
    assert recovered_data[0]["sha256"] == audit.AUTHOR_DAILY_PV_LFS_SHA256
    assert len(reruns) == 32
    assert Counter(row["independently_regenerated"] for row in reruns) == {"True": 9, "False": 23}
    assert Counter(row["executed_factor_count"] for row in reruns) == {
        "20": 8, "158": 8, "360": 8, "170": 8,
    }
    assert Counter(row["compatibility_repairs"] for row in reruns) == {"0": 24, "1": 8}
    assert regeneration["alpha158_20"]["paper_cells_independently_regenerated"] == 8
    assert regeneration["quantaalpha_gpt_v1_v2"]["paper_cells_independently_regenerated"] == 0
    assert regeneration["quantaalpha_gpt_v1_v2"]["publicly_recomputed_factor_count"] == 170
    assert regeneration["quantaalpha_gpt_v1_v2"]["repeat_runs"] == 2
    assert regeneration["quantaalpha_gpt_v1_v2"]["repeat_max_abs_difference"] <= 2e-15
    assert regeneration["quantaalpha_gpt_v1_v2"]["native_metrics"] == (
        audit.QA_GPT_COMPLETE_170_NATIVE_METRICS
    )
    assert deterministic["author_source_modified"] is False
    assert deterministic["source_commit"] == audit.PREPUBLICATION_RESULTS_COMMIT
    assert deterministic["protocol"]["llm_or_market_api_called"] is False
    assert deterministic["baselines"]["alpha158"]["paper_metrics_matching_at_display_precision"] == ["IC"]
    assert deterministic["baselines"]["alpha360"]["paper_metrics_matching_at_display_precision"] == []
    assert deterministic["baselines"]["alpha158"]["complete_paper_row_match"] is False
    assert deterministic["baselines"]["alpha360"]["complete_paper_row_match"] is False
    assert audit.verify_deterministic_baseline_evidence(output)["evidence"]["source_commit"] == audit.PREPUBLICATION_RESULTS_COMMIT

    assert complete_recovery["author_source_modified"] is False
    assert complete_recovery["complete_pool_factor_count"] == 170
    assert {row["factor_name"] for row in complete_recovery["factors"]} == set(
        audit.COMPLETE_POOL_REPAIRED_FACTORS
    )
    assert complete_result["num_factors"] == 170
    assert complete_result["metrics"] == audit.QA_GPT_COMPLETE_170_RAW_METRICS
    assert len(complete_repeats) == 2
    assert audit.verify_complete_pool_evidence(output)["repeat_runs"] == 2
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_primary_sources_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_source")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_paper")
    census = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_fork_census")
    if not source.exists() or not paper.exists():
        return
    assert str(audit.run_git(source, "rev-parse", "HEAD")).strip() == audit.SOURCE_COMMIT
    assert audit.sha256(paper / "paper.pdf") == audit.PAPER_VERSIONS["v3"]["pdf_sha256"]
    assert audit.sha256(paper / "daily_pv_debug.h5") == audit.HF_DEBUG_SHA256
    assert len(audit.source_inventory(source)) == 237
    assert len(audit.paper_source_inventory(paper / "source")) == 36
    outputs = audit.author_output_correspondence(source, paper / "source")
    assert len(outputs) == 5
    assert sum(row["published_result_units_corroborated"] for row in outputs) == 270
    history_commits, history_paths, history_summary = audit.public_source_history(source)
    assert len(history_commits) == 61 and len(history_paths) == 259
    assert history_summary["native_result_artifact_paths_total"] == 0
    evidence = audit.historical_branch_evidence(source)
    assert len(evidence) == 8
    versioned = audit.paper_version_main_table_rows(source, paper / "source")
    assert len(versioned) == 644
    if census.exists():
        prepublication, summary = audit.prepublication_public_history(census)
        assert len(prepublication) == 28 and summary["unique_historical_paths"] == 851
        fork_heads, fork_summary = audit.public_fork_census(
            census, ROOT / "paper_runs/paper_replication_audits/quantaalpha/public_fork_branch_ref_snapshot.csv"
        )
        assert len(fork_heads) == 77 and fork_summary["divergent_heads_reviewed"] == 64
        assert fork_summary["paper_result_artifacts_discovered_in_post_v1_fork_heads"] == 0
        results = audit.prepublication_result_conformance(census, paper / "source")
        assert len(results) == 88 and sum(row["rounded_match"] for row in results) == 74
