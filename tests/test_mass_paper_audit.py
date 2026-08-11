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


def test_paper_targets_cover_every_table_1_to_4_cell() -> None:
    rows = audit.paper_result_rows()
    assert len(rows) == 285
    assert Counter(row["paper_table"] for row in rows) == {
        1: 108,
        2: 72,
        3: 6,
        4: 99,
    }
    assert Counter(row["paper_table"] for row in rows if row["paper_value_is_numeric"]) == {1: 108, 2: 64, 3: 6, 4: 99}
    groups = {(row["paper_table"], row["section"], row["stock_pool"], row["method"]) for row in rows}
    assert len(groups) == 81


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
    conformance = read_csv(output / "tables_1_4_conformance.csv")
    snapshot = read_csv(output / "distribution_snapshot_audit.csv")
    datasets = read_csv(output / "released_dataset_inventory.csv")
    config = read_csv(output / "source_config_conformance.csv")

    assert manifest["overall_status"] == "not_reproduced_partial_internal_state_only"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_result_rows_total"] == 81
    assert manifest["paper_result_cells_total_including_emcl"] == 285
    assert manifest["paper_numeric_result_cells_total"] == 277
    assert manifest["paper_numeric_result_cells_reproduced"] == 0
    assert manifest["paper_numeric_result_cells_unverifiable"] == 277
    assert manifest["paper_non_numeric_emcl_cells"] == 8
    assert manifest["native_dated_distribution_snapshot_shipped"] is True
    assert manifest["distribution_snapshot_is_published_result"] is False
    assert manifest["native_agent_decision_cache_shipped"] is False
    assert manifest["native_signal_path_shipped"] is False
    assert manifest["native_portfolio_or_return_path_shipped"] is False
    assert manifest["released_full_four_pool_dataset"] is False
    assert manifest["audit_called_llm_or_external_api"] is False

    assert Counter(row["status"] for row in conformance) == {
        "unverifiable_no_shipped_native_signal_or_result_path": 277,
        "paper_non_numeric_emcl": 8,
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

    assert len(config) == 21
    assert Counter(row["status"] for row in config) == {
        "match": 6,
        "mismatch": 5,
        "missing": 5,
        "incomplete": 2,
        "not_pinned": 1,
        "not_operational": 1,
        "paper_underspecified": 1,
    }
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected
