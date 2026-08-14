from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_mass_paper.py"
SPEC = importlib.util.spec_from_file_location("mass_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_paper_targets_cover_every_final_numeric_and_emcl_table_cell() -> None:
    rows = audit.paper_result_rows()
    assert len(rows) == 774
    assert Counter(row["paper_table"] for row in rows) == {
        1: 264,
        2: 72,
        4: 44,
        5: 12,
        6: 6,
        7: 216,
        8: 160,
    }
    assert Counter(row["paper_table"] for row in rows if row["paper_value_is_numeric"]) == {
        1: 264,
        2: 64,
        4: 44,
        5: 12,
        6: 6,
        7: 216,
        8: 160,
    }
    groups = {(row["paper_table"], row["section"], row["stock_pool"], row["method"]) for row in rows}
    assert len(groups) == 213


def test_table_2_emcl_cells_remain_non_numeric() -> None:
    rows = [row for row in audit.paper_result_rows() if not row["paper_value_is_numeric"]]
    assert len(rows) == 8
    assert {row["paper_table"] for row in rows} == {2}
    assert {row["method"] for row in rows} == {"without_csp"}
    assert {row["stock_pool"] for row in rows} == {"CSI_300", "ChiNext_100"}
    assert {row["paper_value"] for row in rows} == {"EMCL"}


def test_committed_audit_preserves_internal_state_result_boundary() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/mass"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "final_table_result_conformance.csv")
    descriptive_table_3 = read_csv(output / "final_table_3_stock_inventory.csv")
    figures = read_csv(output / "final_empirical_figure_inventory.csv")
    snapshot = read_csv(output / "distribution_snapshot_audit.csv")
    datasets = read_csv(output / "released_dataset_inventory.csv")
    config = read_csv(output / "source_config_conformance.csv")
    history = json.loads((output / "official_source_history.json").read_text(encoding="utf-8"))
    lineage = json.loads((output / "official_release_lineage.json").read_text(encoding="utf-8"))
    counterexample = json.loads(
        (output / "native_signal_nonidentifiability.json").read_text(encoding="utf-8")
    )
    fork_census = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))
    fork_refs = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    fork_heads = read_csv(output / "public_fork_unique_head_inventory.csv")

    assert manifest["overall_status"] == "not_reproduced_partial_internal_state_only"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_result_rows_total"] == 213
    assert manifest["paper_result_cells_total_including_emcl"] == 774
    assert manifest["paper_numeric_result_cells_total"] == 766
    assert manifest["paper_numeric_result_cells_reproduced"] == 0
    assert manifest["paper_numeric_result_cells_unverifiable"] == 766
    assert manifest["paper_non_numeric_emcl_cells"] == 8
    assert manifest["paper_descriptive_table_3_rows"] == 9
    assert manifest["paper_empirical_figures_audited"] == 5
    assert manifest["paper_empirical_figures_reproduced"] == 0
    assert manifest["paper_empirical_figures_partial_internal_state_only"] == 1
    assert manifest["native_dated_distribution_snapshot_shipped"] is True
    assert manifest["distribution_snapshot_is_published_result"] is False
    assert manifest["native_signal_nonidentifiability_proved"] is True
    assert manifest["same_released_distribution_produces_distinct_native_signals"] is True
    assert manifest["native_counterexample_changed_signal_stock_count"] == 10
    assert manifest["native_agent_decision_cache_shipped"] is False
    assert manifest["native_signal_aggregation_source_shipped"] is True
    assert manifest["native_dated_signal_output_shipped"] is False
    assert manifest["native_portfolio_or_return_path_shipped"] is False
    assert manifest["released_full_four_chinese_pool_dataset"] is False
    assert manifest["released_full_six_pool_dataset"] is False
    assert manifest["audit_called_llm_or_external_api"] is False
    assert manifest["official_release_lineage_audited"] is True
    assert manifest["openreview_final_pdf_sha256"] == audit.OPENREVIEW_FINAL_PDF_SHA256
    assert manifest["openreview_final_pdf_pages"] == 26
    assert manifest["openreview_final_decision"] == "reject"
    assert manifest["anonymous_backup_all_non_readme_shared_blobs_identical"] is True
    assert manifest["anonymous_backup_additional_native_result_artifacts_found"] is False
    assert manifest["source_history_reachable_commits"] == 13
    assert manifest["source_history_root_commits"] == 1
    assert manifest["source_history_tags"] == 0
    assert manifest["source_history_unique_paths"] == 58
    assert manifest["source_history_native_result_artifacts_found"] is False
    assert manifest["public_fork_census_date"] == "2026-08-14"
    assert manifest["public_forks_reported_by_github_rest"] == 25
    assert manifest["public_forks_accessible_via_graphql"] == 25
    assert manifest["public_fork_branch_refs_audited"] == 26
    assert manifest["public_fork_unique_heads_audited"] == 5
    assert manifest["public_fork_heads_reachable_from_official_history"] == 4
    assert manifest["public_fork_divergent_heads_audited"] == 1
    assert manifest["public_fork_divergent_commits_audited"] == 3
    assert manifest["public_fork_divergent_paths_audited"] == 8
    assert manifest["public_fork_semantically_new_market_panel_found"] is False
    assert manifest["public_fork_native_result_artifacts_found"] is False
    assert manifest["public_fork_paper_result_credit"] is False

    assert len(fork_refs) == 26
    assert len({row["repository"] for row in fork_refs}) == 25
    assert len(fork_heads) == 5
    assert Counter(row["classification"] for row in fork_heads) == {
        "official_public_history_reachable": 4,
        "unaffiliated_postpaper_source_adaptation_with_semantically_duplicate_market_panel": 1,
    }
    divergent_head = next(row for row in fork_heads if row["extra_commit_count_beyond_official_head"] == "3")
    assert divergent_head["head_commit"] == audit.PUBLIC_FORK_DIVERGENT_HEAD
    assert divergent_head["extra_changed_path_count"] == "8"
    assert divergent_head["possible_native_output_paths"] == audit.PUBLIC_FORK_PARQUET_PATH
    assert divergent_head["paper_result_credit"] == "False"
    assert fork_census["fork_and_official_market_panel_bytes_differ"] is True
    assert fork_census["fork_and_official_market_panels_semantically_identical"] is True
    assert fork_census["semantic_panel_rows"] == 72_638
    assert fork_census["semantic_panel_columns"] == 19
    assert fork_census["semantic_panel_distinct_stocks"] == 100
    assert fork_census["semantic_panel_distinct_dates"] == 1_457
    assert fork_census["native_agent_decision_signal_portfolio_or_result_paths_discovered"] == 0
    assert fork_census["exact_paper_result_table_or_figure_paths_discovered"] == 0
    assert fork_census["paper_result_credit"] is False

    assert Counter(row["status"] for row in conformance) == {
        "unverifiable_no_shipped_native_signal_output_or_result_path": 766,
        "paper_non_numeric_emcl": 8,
    }
    assert len(descriptive_table_3) == 9
    assert Counter(row["style"] for row in descriptive_table_3) == {
        "Value": 3,
        "Growth": 3,
        "Beta": 3,
    }
    assert all(row["replication_credit"] == "False" for row in descriptive_table_3)
    assert len(figures) == 5
    assert {row["paper_figure"] for row in figures} == {"2", "3", "4", "5", "6"}
    assert Counter(row["status"] for row in figures) == {
        "unverifiable_no_shipped_native_output": 4,
        "partial_internal_state_only_figure_not_reproduced": 1,
    }
    assert len(snapshot) == 263
    assert snapshot[0]["date"] == "20221202"
    assert snapshot[-1]["date"] == "20231229"
    assert Counter(row["changed_from_previous_trading_date"] for row in snapshot) == {
        "True": 216,
        "False": 47,
    }
    assert all(row["investor_type_masks"] == "16" for row in snapshot)
    assert all(math.isclose(float(row["normalized_weight_sum"]), 1.0) for row in snapshot)

    assert len(datasets) == 12
    assert Counter(row["format_status"] for row in datasets) == {
        "readable": 10,
        "unreadable_ArrowInvalid": 2,
    }
    base = next(row for row in datasets if row["path"].endswith("base_data.parq"))
    labels = next(row for row in datasets if row["path"].endswith("ih_label.parq"))
    assert (base["rows"], base["distinct_dates"], base["distinct_stocks"]) == (
        "72638",
        "1457",
        "100",
    )
    assert labels["rows"] == base["rows"]
    assert manifest["released_dataset"]["paper_stock_pools"] == [
        "SSE50",
        "CSI_300",
        "ChiNext_100",
        "CSI_A500",
        "Nasdaq_100",
        "SP_500",
    ]

    assert len(config) == 25
    assert Counter(row["status"] for row in config) == {
        "match": 6,
        "mismatch": 5,
        "missing": 8,
        "incomplete": 2,
        "not_pinned": 2,
        "not_operational": 1,
        "paper_underspecified": 1,
    }
    assert history["reachable_commit_count"] == 13
    assert history["root_commit_count"] == 1
    assert history["head_tree_file_count"] == 38
    assert history["unique_historical_path_count"] == 58
    assert len(history["deleted_code_recovered"]) == 6
    assert all(not row["paper_result_artifact"] for row in history["deleted_code_recovered"])
    assert all(row["reachable_objects"] == 0 for row in history["ignored_result_paths"])
    assert history["historical_native_decision_signal_portfolio_or_result_artifacts_found"] is False

    assert lineage["anonymous_backup_commit"] == audit.ANONYMOUS_SOURCE_COMMIT
    assert lineage["anonymous_backup_root_commit_count"] == 1
    assert lineage["anonymous_backup_file_count"] == 39
    assert lineage["official_release_file_count"] == 38
    assert lineage["shared_file_count"] == 38
    assert lineage["anonymous_only_paths"] == [".README"]
    assert lineage["different_shared_blobs"] == ["README.md"]
    assert lineage["all_non_readme_shared_blobs_identical"] is True
    assert lineage["additional_decisions_signals_portfolios_results_or_stock_pools_in_backup"] is False

    assert counterexample["same_released_distribution_in_both_scenarios"] is True
    assert counterexample["investor_types"] == 16
    assert counterexample["agents_per_type"] == 32
    assert counterexample["candidate_pool_size"] == 20
    assert counterexample["selected_stocks_per_agent"] == 5
    assert counterexample["changed_signal_stock_count"] == 10
    assert counterexample["released_state_identifies_unique_signal"] is False
    assert set(counterexample["scenario_a_selected_stocks"]).isdisjoint(
        counterexample["scenario_b_selected_stocks"]
    )
    assert all(values[0] == 0.5 for values in counterexample["scenario_a_selected_signal"].values())
    assert all(values[0] == 0.5 for values in counterexample["scenario_b_selected_signal"].values())
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_live_public_fork_census_when_bouchet_sources_are_available() -> None:
    census = Path("/nfs/roberts/scratch/pi_btk22/zc362/mass_fork_census")
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/mass_source")
    snapshot = (
        ROOT
        / "paper_runs/paper_replication_audits/mass/public_fork_branch_ref_snapshot.csv"
    )
    if not census.exists() or not source.exists() or not snapshot.exists():
        return
    heads, summary, branch_rows = audit.public_fork_census(census, snapshot, source)
    assert len(heads) == 5
    assert len(branch_rows) == 26
    assert summary["divergent_heads_reviewed"] == 1
    assert summary["fork_and_official_market_panels_semantically_identical"] is True
    assert summary["paper_result_credit"] is False
