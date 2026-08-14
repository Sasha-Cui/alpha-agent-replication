from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_quantharness_paper.py"
SPEC = importlib.util.spec_from_file_location("quantharness_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_targets_cover_all_numeric_cells_in_tables_1_and_2() -> None:
    rows = audit.paper_result_rows()
    assert len(rows) == 272
    assert Counter(row["paper_table"] for row in rows) == {1: 120, 2: 152}
    assert len({(row["paper_table"], row["asset"], row["method"]) for row in rows}) == 62
    assert len(audit.v1_v2_paper_result_rows()) == 88


def test_committed_audit_preserves_the_native_result_boundary() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/quantharness"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_1_2_conformance.csv")
    alignments = read_csv(output / "linear_regression_alignment_audit.csv")
    inventory = read_csv(output / "released_benchmark_inventory.csv")
    identities = read_csv(output / "table_2_delta_accuracy_identity.csv")
    anomalies = read_csv(output / "paper_internal_anomalies.csv")
    source = read_csv(output / "source_config_conformance.csv")
    paper_versions = read_csv(output / "official_paper_version_inventory.csv")
    versioned_results = read_csv(output / "paper_version_result_conformance.csv")
    history_commits = read_csv(output / "public_source_history_commit_inventory.csv")
    history_paths = read_csv(output / "public_source_history_path_inventory.csv")
    history_sets = read_csv(output / "public_source_history_benchmark_set_inventory.csv")
    history_images = read_csv(output / "historical_result_image_inventory.csv")
    history = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == (
        "not_reproduced_full_history_exhausted_author_table_rasters_only"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_versions_audited"] == 4
    assert manifest["version_specific_paper_numeric_result_cells_total"] == 600
    assert manifest["version_specific_paper_numeric_result_cells_by_version"] == {
        "v1": 88,
        "v2": 88,
        "v3": 152,
        "v4": 272,
    }
    assert manifest["distinct_numeric_result_table_cells_across_versions"] == 360
    assert manifest["version_specific_author_rendered_table_cells_corresponded"] == 480
    assert manifest["distinct_author_rendered_table_cells_corresponded"] == 240
    assert manifest["version_specific_native_result_cells_independently_regenerated"] == 0
    assert manifest["public_source_branches_total"] == 2
    assert manifest["public_source_tags_total"] == 0
    assert manifest["public_source_reachable_commits_total"] == 195
    assert manifest["public_source_unique_historical_paths_total"] == 1870
    assert manifest["public_source_reachable_object_counts"] == {
        "commit": 195,
        "tree": 279,
        "blob": 2228,
    }
    assert manifest["public_source_unreachable_objects_total"] == 0
    assert manifest["public_source_historical_benchmark_csv_paths_total"] == 1800
    assert manifest["public_source_historical_benchmark_asset_horizon_sets_total"] == 18
    assert manifest["public_source_historical_native_result_artifact_candidates_total"] == 0
    assert manifest["public_source_historical_unique_result_image_blobs_total"] == 7
    assert manifest["public_source_historical_unique_table_image_blobs_total"] == 4
    assert manifest["public_source_historical_unique_one_hour_result_chart_blobs_total"] == 3
    assert manifest["official_one_hour_figure_author_raster_correspondences_total"] == 2
    assert manifest["intermediate_nonpaper_one_hour_result_rasters_total"] == 1
    assert manifest["one_hour_figure_numeric_points_or_arrays_shipped"] is False
    assert manifest["paper_numeric_result_cells_total"] == 272
    assert manifest["native_paper_result_cells_reproduced"] == 0
    assert manifest["numeric_result_cells_unverifiable"] == 224
    assert manifest["paper_described_lr_accuracy_cells_matched"] == 0
    assert (
        manifest[
            "published_lr_accuracy_cells_exact_only_with_undocumented_three_bar_feature_gap"
        ]
        == 8
    )
    assert manifest["inferred_gap_lr_extrema_cells_display_matched"] == 7
    assert manifest["paper_internal_delta_identity_cells_consistent"] == 23
    assert manifest["paper_internal_delta_identity_cells_inconsistent"] == 1
    assert manifest["native_experiment_evaluator_shipped"] is False
    assert manifest["native_agent_predictions_or_return_series_shipped"] is False
    assert manifest["original_5000_bar_panels_shipped"] is False
    assert manifest["audit_called_llm_or_paid_external_api"] is False

    assert Counter(row["status"] for row in conformance) == {
        "unverifiable_missing_native_portfolio_or_metric_path": 120,
        "unverifiable_missing_native_result_or_evaluator": 104,
        "paper_internal_identity_match_not_independent_reproduction": 23,
        "paper_internal_identity_mismatch": 1,
        "mismatch_paper_described_recent_40_window": 8,
        "diagnostic_inferred_gap_display_match_not_native_reproduction": 7,
        "diagnostic_inferred_gap_mismatch": 9,
    }
    assert len(alignments) == 8
    assert {row["paper_described_status"] for row in alignments} == {"mismatch"}
    assert {row["inferred_status"] for row in alignments} == {
        "display_match_only_with_undocumented_three_bar_gap"
    }
    assert {row["inferred_feature_rows_zero_based"] for row in alignments} == {"54:94"}
    assert {row["undocumented_feature_gap_rows"] for row in alignments} == {"94:97"}

    assert len(inventory) == 16
    assert {row["released_segment_files"] for row in inventory} == {"100"}
    assert {row["minimum_rows_per_segment"] for row in inventory} == {"100"}
    assert {row["maximum_rows_per_segment"] for row in inventory} == {"100"}
    assert Counter(int(row["released_distinct_timestamps"]) for row in inventory) == {
        4082: 15,
        4440: 1,
    }
    assert all(row["start_date_match"] == "True" for row in inventory)
    assert all(row["end_date_match"] == "True" for row in inventory)

    assert len(identities) == 24
    mismatch = [row for row in identities if row["status"] == "paper_internal_mismatch"]
    assert [(row["asset"], row["method"]) for row in mismatch] == [("SPX", "Our")]
    assert len(anomalies) == 9
    assert sum(row["finding"].startswith("positive_value") for row in anomalies) == 8
    assert len(source) == 22
    assert Counter(row["status"] for row in source) == {
        "mismatch": 1,
        "match": 2,
        "paper_underspecified": 3,
        "missing": 15,
        "not_implemented_in_active_public_path": 1,
    }

    assert [row["paper_version"] for row in paper_versions] == ["v1", "v2", "v3", "v4"]
    assert [int(row["numeric_result_cells"]) for row in paper_versions] == [88, 88, 152, 272]
    assert [int(row["pdf_pages"]) for row in paper_versions] == [30, 30, 30, 32]
    assert [bool(row["line_chart_pdf_sha256"]) for row in paper_versions] == [
        False,
        False,
        True,
        True,
    ]
    assert Counter(row["paper_version"] for row in versioned_results) == {
        "v1": 88,
        "v2": 88,
        "v3": 152,
        "v4": 272,
    }
    assert sum(row["author_rendered_correspondence"] == "True" for row in versioned_results) == 480
    assert all(
        row["independently_regenerated_from_native_result_path"] == "False"
        for row in versioned_results
    )
    assert all(row["paper_result_credit"] == "False" for row in versioned_results)

    assert len(history_commits) == 195
    assert len(history_paths) == 1870
    assert len(history_sets) == 18
    assert {row["unique_historical_segment_paths"] for row in history_sets} == {"100"}
    assert len(history_images) == 7
    assert sum("table" in row["role"] for row in history_images) == 4
    assert sum("one_hour" in row["role"] for row in history_images) == 3
    assert sum(int(row["distinct_table_cells_corresponded"]) for row in history_images) == 240
    assert (
        sum(int(row["version_specific_table_cells_corresponded"]) for row in history_images)
        == 480
    )
    assert all(row["underlying_numeric_result_array_shipped"] == "False" for row in history_images)
    assert all(row["paper_result_credit"] == "False" for row in history_images)
    assert Counter(row["history_role"] for row in history_paths)[
        "released_sampled_benchmark_segment"
    ] == 1800
    assert Counter(row["history_role"] for row in history_paths)[
        "author_rendered_result_output_no_underlying_array"
    ] == 3
    assert not any(row["native_result_artifact_candidate"] == "True" for row in history_paths)
    assert history["reachable_commits_total"] == 195
    assert history["unique_historical_paths_total"] == 1870
    assert history["historical_native_result_artifact_candidates_total"] == 0
    assert history["official_one_hour_figure_author_raster_correspondences_total"] == 2
    assert history["intermediate_nonpaper_one_hour_result_rasters_total"] == 1
    assert history["paper_result_credit_from_author_rendered_images"] is False

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_lr_reconstruction_uses_only_released_four_hour_segments() -> None:
    source_root = Path(
        "/nfs/roberts/scratch/pi_btk22/zc362/quantagent_hft_source"
    )
    if not source_root.exists():
        return
    arrays = audit.load_4h_arrays(source_root)
    rows, exact_pairs = audit.lr_alignment_audit(arrays)
    assert exact_pairs == [(94, 96)]
    assert sum(row["paper_described_status"] == "display_match" for row in rows) == 0
    assert sum(row["inferred_status"].startswith("display_match") for row in rows) == 8


def test_all_official_paper_versions_match_pinned_tables_and_archives() -> None:
    paper_root = Path(
        "/nfs/roberts/scratch/pi_btk22/zc362/quantagent_hft_paper"
    )
    if not paper_root.exists():
        return
    versions = audit.paper_version_inventory(paper_root)
    rows = audit.paper_version_result_rows(paper_root)
    assert len(versions) == 4
    assert Counter(row["paper_version"] for row in rows) == {
        "v1": 88,
        "v2": 88,
        "v3": 152,
        "v4": 272,
    }
    assert sum(row["author_rendered_correspondence"] for row in rows) == 480
    assert not any(
        row["independently_regenerated_from_native_result_path"] for row in rows
    )


def test_full_public_source_history_has_no_hidden_native_result_path() -> None:
    source_root = Path(
        "/nfs/roberts/scratch/pi_btk22/zc362/quantagent_hft_source"
    )
    if not source_root.exists():
        return
    commits, paths, images, history = audit.public_source_history(source_root)
    sets = audit.historical_benchmark_set_inventory(paths)
    assert len(commits) == 195
    assert len(paths) == 1870
    assert len(sets) == 18
    assert len(images) == 7
    assert history["historical_benchmark_csv_paths_total"] == 1800
    assert history["historical_native_result_artifact_candidates_total"] == 0
    assert history["version_specific_table_cells_author_rendered_correspondence"] == 480
