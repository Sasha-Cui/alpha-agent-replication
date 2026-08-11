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


def test_committed_audit_preserves_the_native_result_boundary() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/quantharness"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_1_2_conformance.csv")
    alignments = read_csv(output / "linear_regression_alignment_audit.csv")
    inventory = read_csv(output / "released_benchmark_inventory.csv")
    identities = read_csv(output / "table_2_delta_accuracy_identity.csv")
    anomalies = read_csv(output / "paper_internal_anomalies.csv")
    source = read_csv(output / "source_config_conformance.csv")

    assert manifest["overall_status"] == (
        "not_reproduced_released_benchmark_and_lr_diagnostic_only"
    )
    assert manifest["full_paper_reproduced"] is False
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
