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
