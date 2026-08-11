from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_automate_strategy_paper.py"
SPEC = importlib.util.spec_from_file_location("automate_strategy_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def test_published_targets_cover_table_2_and_table_4() -> None:
    assert len(audit.PAPER_TABLE_2) == 5
    assert len(audit.PAPER_TABLE_3_SELECTED_INDICES) == 12
    assert len(audit.PAPER_TABLE_4) == 8
    assert len(audit.TABLE_4_METRICS) == 5
    assert audit.PAPER_TABLE_4[0][1][0] == 53.173


def test_table_2_absolute_ic_audit_is_explicit() -> None:
    rows = [
        {"index": 1, "category": "Momentum", "ic": -0.01},
        {"index": 3, "category": "Momentum", "ic": 0.02},
        {"index": 9, "category": "Momentum", "ic": -0.03},
    ]
    rows.extend(
        {"index": index, "category": category, "ic": value}
        for category, index, value in (
            ("Mean Reversion", 10, -0.0187),
            ("Volatility", 20, 0.0258),
            ("Fundamental", 27, -0.0192),
            ("Growth", 33, -0.0217),
        )
    )
    result = audit.table_2_audit(rows)
    momentum = next(
        row
        for row in result
        if row["category"] == "Momentum" and row["metric"] == "mean_ic_of_saf"
    )
    assert momentum["source_absolute_ic_aggregation"] == 0.02
    assert "absolute IC" in momentum["aggregation_note"]


def test_committed_audit_records_partial_component_not_paper_replication() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/automate_strategy_finding"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    with (output / "factor_workbook_inventory.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        inventory = list(csv.DictReader(handle))
    with (output / "table_4_conformance.csv").open(newline="", encoding="utf-8") as handle:
        table_4 = list(csv.DictReader(handle))
    assert manifest["overall_status"] == "not_reproduced_missing_integrated_native_output"
    assert manifest["paper_table_2_cells_matched"] == 3
    assert manifest["paper_table_2_cells_total"] == 10
    assert manifest["paper_table_4_cells_verified"] == 0
    assert manifest["paper_table_4_cells_unverifiable"] == 40
    assert manifest["native_integrated_portfolio_return_shipped"] is False
    assert manifest["dnn_hidden_width_matches"] is False
    assert manifest["source_agent_contains_hardcoded_credential"] is True
    assert len(inventory) == 7
    assert {row["sample_start"] for row in inventory} == {"2022-09-30"}
    assert {row["sample_end"] for row in inventory} == {"2022-12-30"}
    assert all(row["covers_paper_test_window"] == "False" for row in inventory)
    assert all(row["status"].startswith("unverifiable") for row in table_4)
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected
