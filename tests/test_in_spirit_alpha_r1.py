from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import alpha_r1_contextual_gate_scores


ZOO = [
    {"column": "value", "sign": 1, "family": "value"},
    {"column": "quality", "sign": 1, "family": "quality"},
    {"column": "investment", "sign": -1, "family": "value"},
    {"column": "momentum", "sign": 1, "family": "momentum"},
    {"column": "risk", "sign": -1, "family": "quality"},
    {"column": "growth", "sign": 1, "family": "momentum"},
]

AFFINITIES = {
    "value": {
        "price_trend": -0.5,
        "volatility": 0.5,
        "price_breadth": -0.25,
        "earnings_news": 0.0,
    },
    "quality": {
        "price_trend": 0.0,
        "volatility": 1.0,
        "price_breadth": -0.5,
        "earnings_news": 0.5,
    },
    "momentum": {
        "price_trend": 1.0,
        "volatility": -0.5,
        "price_breadth": 0.5,
        "earnings_news": 0.5,
    },
}


def fixture(months: int = 64, securities: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(163)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    for item in ZOO:
        frame[str(item["column"])] = rng.normal(size=len(frame))
    frame["niq_su"] = rng.normal(size=len(frame))
    frame["saleq_su"] = rng.normal(size=len(frame))
    frame["weight"] = rng.lognormal(size=len(frame))
    frame["ret"] = rng.normal(loc=0.005, scale=0.05, size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame["quality"]
        + 0.015 * frame["momentum"]
        - 0.01 * frame["risk"]
        + rng.normal(scale=0.08, size=len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return alpha_r1_contextual_gate_scores(
        frame,
        ZOO,
        AFFINITIES,
        common_start="2003-07-31",
        selected_factor_count=2,
        price_trend_lookback_months=3,
        volatility_lookback_months=3,
        state_normalization_history_months=12,
        factor_profile_history_months=12,
        minimum_factor_profile_months=12,
        factor_profile_ridge_penalty=0.001,
        linear_beta_history_months=12,
        linear_beta_ridge_fraction=0.01,
    )


def test_alpha_r1_contextual_gate_is_sparse_chronological_and_finite():
    frame = fixture()
    scores, history = run(frame)
    common = frame.month.ge("2003-07-31")
    assert scores.loc[common].notna().all()
    assert history.factor_profile_history_months.eq(12).all()
    assert history.linear_beta_history_months.eq(12).all()
    assert history.selected_factor_count.eq(2).all()
    assert history.selected_factors.str.split("|").map(len).eq(2).all()
    assert (pd.to_datetime(history.factor_profile_history_end) < pd.to_datetime(history.formation_month)).all()
    assert (pd.to_datetime(history.linear_beta_history_end) < pd.to_datetime(history.formation_month)).all()
    assert history.finite_scores.eq(60).all()
    assert history.filter(like="state__").apply(np.isfinite).all().all()


def test_alpha_r1_gate_is_deterministic_and_ignores_current_future_rewards():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2003-07-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first = frame.month.eq(pd.Timestamp("2003-07-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = run(frame)
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_alpha_r1_rejects_non_sparse_or_unbalanced_gate():
    frame = fixture()
    for selected, performance_weight in ((6, 0.5), (2, 0.7)):
        try:
            alpha_r1_contextual_gate_scores(
                frame,
                ZOO,
                AFFINITIES,
                common_start="2003-07-31",
                selected_factor_count=selected,
                price_trend_lookback_months=3,
                volatility_lookback_months=3,
                state_normalization_history_months=12,
                factor_profile_history_months=12,
                linear_beta_history_months=12,
                performance_gate_weight=performance_weight,
                semantic_gate_weight=0.5,
            )
        except ValueError as error:
            assert "sparse" in str(error) or "sum to one" in str(error)
        else:
            raise AssertionError("invalid Alpha-R1 gate was accepted")
