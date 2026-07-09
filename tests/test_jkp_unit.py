from __future__ import annotations

import math

import pandas as pd

from alpha_evolve.jkp import long_short_one_month, parse_cols, weighted_mean
from alpha_evolve.performance import annualized_sharpe, annualized_volatility


def test_parse_cols_trims_empty_values() -> None:
    assert parse_cols(" ret_12_1, , be_me ") == ["ret_12_1", "be_me"]


def test_weighted_mean_ignores_bad_weights() -> None:
    values = pd.Series([1.0, 3.0, 100.0])
    weights = pd.Series([1.0, 1.0, 0.0])
    assert weighted_mean(values, weights) == 2.0


def test_long_short_one_month_uses_weighted_tails() -> None:
    frame = pd.DataFrame(
        {
            "score": list(range(10)),
            "ret_exc_lead1m": [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09],
            "weight": [1.0] * 10,
        }
    )
    assert math.isclose(long_short_one_month(frame, "score", 0.2, 2), 0.08)


def test_annualized_stats_are_finite_for_nonconstant_series() -> None:
    returns = pd.Series([0.01, -0.02, 0.03, 0.00])
    assert annualized_volatility(returns) > 0
    assert math.isfinite(annualized_sharpe(returns))
