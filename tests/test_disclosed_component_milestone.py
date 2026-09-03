from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("component_milestone", ROOT / "scripts/run_disclosed_component_milestone.py")
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def test_reaccounting_keeps_targets_fixed_and_changes_only_missing_realization():
    months = pd.DataFrame({"formation_month": ["2020-01-31", "2020-02-29"],
                           "month": ["2020-02-29", "2020-03-31"], "n_selected": [2, 0]})
    holdings = pd.DataFrame([
        {"formation_month": "2020-01-31", "permno": 1, "target_weight": 0.5,
         "realized_return_observed": True, "effective_excess_return": 0.1, "effective_total_return": 0.1},
        {"formation_month": "2020-01-31", "permno": 2, "target_weight": 0.5,
         "realized_return_observed": False, "effective_excess_return": 0.1, "effective_total_return": 0.1},
    ])
    holdings["formation_month"] = pd.to_datetime(holdings.formation_month)
    zero = runner.reconstruct_paths(months, holdings, "zero")
    adverse = runner.reconstruct_paths(months, holdings, "adverse_100")
    assert zero.n_holdings.tolist() == adverse.n_holdings.tolist() == [2, 0]
    assert zero.iloc[0].gross_return == pytest.approx(0.05)
    assert adverse.iloc[0].gross_return == pytest.approx(-0.45)
    assert zero.iloc[0].traded_notional == adverse.iloc[0].traded_notional == pytest.approx(1.0)
    assert zero.iloc[1].traded_notional == pytest.approx(1.0)


def test_reaccounting_fails_on_nonpositive_strategy_nav():
    months = pd.DataFrame({"formation_month": ["2020-01-31", "2020-02-29"],
                           "month": ["2020-02-29", "2020-03-31"], "n_selected": [1, 0]})
    holdings = pd.DataFrame([{"formation_month": pd.Timestamp("2020-01-31"), "permno": 1,
                              "target_weight": 1.0, "realized_return_observed": True,
                              "effective_excess_return": -1.0, "effective_total_return": -1.0}])
    with pytest.raises(ValueError, match="nonpositive"):
        runner.reconstruct_paths(months, holdings, "zero")
