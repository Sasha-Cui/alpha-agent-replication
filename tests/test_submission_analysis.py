from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.submission_analysis import (
    alpha_regression,
    drift_weights,
    missing_return_gross_weight,
    multiplicity_adjustments,
    paired_block_bootstrap_alpha,
    realized_portfolio_return,
    target_weights,
    traded_notional,
)


def synthetic_cross_section(n: int = 100) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "security_id": np.arange(n),
            "score": np.arange(n, dtype=float),
            "weight": np.ones(n),
            "ret_exc_lead1m": np.linspace(-0.05, 0.05, n),
        }
    )


def test_long_short_weights_have_frozen_direction_and_unit_legs() -> None:
    weights = target_weights(
        synthetic_cross_section(),
        "score",
        "long_short_decile_value_weighted",
        min_side=5,
    )
    assert np.isclose(weights[weights > 0].sum(), 1.0)
    assert np.isclose(weights[weights < 0].sum(), -1.0)
    assert weights[weights > 0].index.min() >= 90
    assert weights[weights < 0].index.max() <= 9


def test_tied_scores_use_deterministic_disjoint_exact_sides() -> None:
    frame = synthetic_cross_section()
    frame["score"] = 1.0
    first = target_weights(
        frame, "score", "long_short_decile_value_weighted", min_side=5
    )
    second = target_weights(
        frame.sample(frac=1.0, random_state=7),
        "score",
        "long_short_decile_value_weighted",
        min_side=5,
    )
    pd.testing.assert_series_equal(first, second)
    assert (first > 0).sum() == 10
    assert (first < 0).sum() == 10
    assert set(first[first > 0].index).isdisjoint(first[first < 0].index)


def test_initial_and_rebalanced_traded_notional() -> None:
    initial = pd.Series([0.5, 0.5, -0.5, -0.5], index=[1, 2, 3, 4])
    assert np.isclose(traded_notional(initial, pd.Series(dtype="float64")), 2.0)
    returns = pd.Series([0.10, 0.00, 0.02, -0.01], index=initial.index)
    pretrade = drift_weights(initial, returns)
    portfolio_return = float(np.dot(initial, returns))
    expected = initial * (1.0 + returns) / (1.0 + portfolio_return)
    pd.testing.assert_series_equal(pretrade, expected)
    assert not np.isclose(pretrade[pretrade > 0].sum(), 1.0)
    assert traded_notional(initial, pretrade) > 0


def test_nonpositive_long_short_nav_is_not_silently_recapitalized() -> None:
    weights = pd.Series([1.0, -1.0], index=[1, 2])
    # The short rises 250%, so the 100/100 strategy loses 250% and cannot be
    # represented as next month's per-dollar-of-NAV weights.
    returns = pd.Series([0.0, 2.5], index=[1, 2])
    with pytest.raises(ValueError, match="NAV is nonpositive"):
        drift_weights(weights, returns)


def test_formation_does_not_condition_on_future_return_availability() -> None:
    frame = synthetic_cross_section()
    frame.loc[frame["score"] >= 90, "ret_exc_lead1m"] = np.nan
    weights = target_weights(
        frame,
        "score",
        "long_short_decile_value_weighted",
        min_side=5,
    )
    assert weights[weights > 0].index.min() >= 90
    assert np.isclose(missing_return_gross_weight(weights, frame), 0.5)
    # Missing long-leg outcomes are assigned the prespecified zero return; the
    # short leg remains frozen rather than being reweighted with hindsight.
    aligned_returns = (
        frame.set_index("security_id")["ret_exc_lead1m"].reindex(weights.index).fillna(0.0)
    )
    expected = float(np.dot(weights, aligned_returns))
    assert np.isclose(realized_portfolio_return(weights, frame), expected)
    adverse = aligned_returns.copy()
    missing = frame.set_index("security_id")["ret_exc_lead1m"].reindex(weights.index).isna()
    adverse.loc[missing] = -np.sign(weights.loc[missing])
    assert np.isclose(
        realized_portfolio_return(weights, frame, missing_return_policy="adverse_100"),
        float(np.dot(weights, adverse)),
    )


def test_alpha_regression_recovers_known_intercept() -> None:
    rng = np.random.default_rng(11)
    n = 240
    factor = rng.normal(0.002, 0.03, n)
    returns = 0.001 + 0.4 * factor + rng.normal(0.0, 0.002, n)
    frame = pd.DataFrame(
        {
            "month": pd.date_range("2000-01-31", periods=n, freq="ME"),
            "candidate": returns,
            "factor": factor,
        }
    )
    result = alpha_regression(frame, "candidate", ["factor"])
    assert abs(result.alpha_monthly - 0.001) < 0.0004
    assert result.alpha_t_hac > 3


def test_multiplicity_keeps_planned_failures_in_denominator() -> None:
    adjusted = multiplicity_adjustments({"a": 0.001, "b": 0.04}, planned_m=4)
    row_a = adjusted.set_index("candidate_id").loc["a"]
    row_b = adjusted.set_index("candidate_id").loc["b"]
    assert np.isclose(row_a["holm_p_value"], 0.004)
    assert row_b["holm_p_value"] >= 0.08


def test_paired_bootstrap_is_reproducible() -> None:
    rng = np.random.default_rng(17)
    n = 120
    factor = rng.normal(0.0, 0.02, n)
    frame = pd.DataFrame(
        {
            "f": factor,
            "a": 0.001 + 0.3 * factor + rng.normal(0.0, 0.01, n),
            "b": -0.001 - 0.2 * factor + rng.normal(0.0, 0.01, n),
        }
    )
    first, first_meta = paired_block_bootstrap_alpha(
        frame, ["a", "b"], ["f"], n_bootstrap=40, block_length=4, seed=99
    )
    second, second_meta = paired_block_bootstrap_alpha(
        frame, ["a", "b"], ["f"], n_bootstrap=40, block_length=4, seed=99
    )
    pd.testing.assert_frame_equal(first, second)
    assert first_meta == second_meta
    for row in first.to_dict("records"):
        direct = alpha_regression(
            frame.assign(month=pd.date_range("2000-01-31", periods=n, freq="ME")),
            row["candidate_id"],
            ["f"],
        )
        assert np.isclose(row["bootstrap_alpha_point_monthly"], direct.alpha_monthly)
