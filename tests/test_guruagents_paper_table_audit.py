from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_guruagents_paper_table.py"
SPEC = importlib.util.spec_from_file_location("guruagents_table_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def test_metric_recomputation_uses_standard_daily_and_drawdown_definitions() -> None:
    rows = [
        {"date": 43831, "normalized_value": 1.0, "daily_return": ""},
        {"date": 43832, "normalized_value": 1.1, "daily_return": 0.1},
        {"date": 43833, "normalized_value": 0.99, "daily_return": -0.1},
    ]
    result = audit.calculate_metrics(rows)
    assert result["sample_start"] == "2020-01-01"
    assert result["sample_end"] == "2020-01-03"
    assert np.isclose(result["mean_daily"], 0.0)
    assert np.isclose(result["std_daily"], math.sqrt(0.02))
    assert np.isclose(result["max_drawdown_pct"], -10.0)
    assert np.isclose(result["var_90_pct"], -8.0)
    assert np.isclose(result["cvar_90_pct"], -10.0)


def test_paper_table_has_all_seven_strategies_and_ten_metrics() -> None:
    assert len(audit.PAPER_TABLE) == 7
    assert len(audit.METRICS) == 10
    assert audit.PAPER_COST_BPS == 1.0


def test_committed_audit_truthfully_records_nonreplication() -> None:
    output = ROOT / "paper_runs/prompt_replay/guruagents/paper_table_conformance"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    with (output / "metric_conformance.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert manifest["overall_status"] == "not_reproduced"
    assert manifest["strategy_windows_fully_matched"] == 0
    assert manifest["strategy_windows_total"] == 14
    assert manifest["metric_cells_matched"] == 4
    assert manifest["metric_cells_total"] == 140
    assert manifest["source_declares_one_bp_cost"] is True
    assert manifest["source_main_return_routine_applies_declared_cost"] is False
    assert len(rows) == 140
    assert sum(row["status"] == "exact_rounding_match" for row in rows) == 4
