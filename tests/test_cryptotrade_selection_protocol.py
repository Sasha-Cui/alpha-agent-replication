from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
for name, filename in (("audit_cryptotrade_paper", "audit_cryptotrade_paper.py"),
                       ("cryptotrade_selection_protocol", "run_cryptotrade_selection_protocol.py")):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
runner = sys.modules["cryptotrade_selection_protocol"]
audit = runner.audit


@pytest.mark.parametrize("strategy,parameter", [("sma", 15), ("slma", (15, 30)), ("macd", None)])
@pytest.mark.parametrize("indicator", [10.0, float("nan")])
def test_native_neutral_indicators_must_hold(tmp_path, strategy, parameter, indicator):
    actions = []

    class Environment:
        def __init__(self, args):
            self.done = False
            self.starting_price = 10.0
            self.total_steps = 2
            row = {"SMA_15": indicator, "SMA_30": 10.0, "MACD": indicator, "Signal_Line": 10.0}
            self.data = pd.DataFrame([row, row])

        def reset(self):
            return {"net_worth": 20.0, "cash": 10.0, "eth_held": 1.0, "open": 10.0}, 0, False, {}

        def step(self, action):
            actions.append(action)
            self.done = True
            return {"net_worth": 21.0, "cash": 10.0, "eth_held": 1.0, "open": 11.0}, 0, True, {}

    audit.source_simulation(SimpleNamespace(ETHTradingEnv=Environment), tmp_path, "sol", "2023-04-12", "2023-04-13", strategy, parameter)
    assert actions == [0.0]


def test_validation_selector_keeps_all_ties_without_test_selection():
    rows = [{"split": "validation", "parameter": p, "total_return_pct": score}
            for p, score in ((15, -3.0), (20, 2.0), (30, 2.0))]
    assert [r["parameter"] for r in runner.select_on_validation(rows, "total_return_pct")] == [20, 30]
    with pytest.raises(ValueError, match="held-out"):
        runner.select_on_validation([dict(rows[0], split="bull")], "total_return_pct")
    with pytest.raises(ValueError, match="nonfinite"):
        runner.select_on_validation([dict(rows[0], total_return_pct=float("nan"))], "total_return_pct")
    with pytest.raises(ValueError, match="unsupported"):
        runner.select_on_validation(rows, "test_return")


def test_published_sma_grid_and_explicit_slma_reconstruction():
    assert runner.candidates("sma") == (5, 10, 15, 20, 30)
    pairs = runner.candidates("slma")
    assert len(pairs) == 10
    assert all(short < long for short, long in pairs)
    assert 1 not in runner.candidates("sma")
    assert "constant_sell_counterfactual" not in audit.TRADITIONAL_STRATEGIES


def test_selection_evidence_reconstructs_metrics_from_native_wealth_paths():
    output = ROOT / "paper_runs/paper_replication_audits/cryptotrade"
    summary = audit.verify_selection_protocol(output)
    assert summary["execution_runtime"] == {"python": "3.12.4", "numpy": "2.0.2", "pandas": "2.3.3", "platform": "linux"}
    assert summary["native_baseline_sha256"] == runner.NATIVE_BASELINE_SHA256
    assert summary["native_environment_sha256"] == "a05443b96d6e86b13ee33adf1c5d6a16dac9195de6857a3e9c2916cf0c393f3f"
    assert summary["validation_native_runs"] == 90
    assert summary["held_out_native_runs"] == 72
    assert summary["native_sma1_hold_diagnostic_runs"] == 2
    assert summary["all_native_repeats_exact"] is True
    assert summary["all_adapter_native_metrics_equal_atol_1e_12"] is True
    assert summary["selection_uses_test_data"] is False
    assert summary["fixed_settings_match_cells"] == 66
    assert summary["matching_cells_by_objective_all_ties_required"] == {"total_return_pct": 16, "sharpe_ratio": 16}
    assert summary["additional_paper_result_credit"] == 0
    assert summary["native_sma1_sol_bear_metrics"]["total_return_pct"] == pytest.approx(-17.938344866190505)
    assert summary["constant_sell_counterfactual_metrics"]["total_return_pct"] == pytest.approx(1.0350520767212767)
    choices = audit.read_csv(output / "traditional_validation_choices.csv")
    eth_sma = [row for row in choices if row["asset"] == "eth" and row["strategy"] == "sma"]
    assert len(eth_sma) == 2
    assert all(json.loads(row["selected_parameters"]) == ["20", "30"] for row in eth_sma)


def test_selection_evidence_rejects_changed_path_bytes(tmp_path):
    # The first pin fails closed before any claimed metric can be consumed.
    first = next(iter(audit.SELECTION_PROTOCOL_SHA256))
    (tmp_path / first).write_text("{}\n")
    with pytest.raises(RuntimeError, match="evidence changed"):
        audit.verify_selection_protocol(tmp_path)
