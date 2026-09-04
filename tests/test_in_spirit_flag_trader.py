from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import cross_sectional_unit_rank, flag_trader_rolling_scores


FEATURES = ["value", "momentum", "trend", "risk"]
PRIOR = [1.0, 1.0, 0.5, -1.0]


def fixture(months: int = 70, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(23)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    for feature in FEATURES:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame.value
        + 0.015 * frame.momentum
        + 0.005 * frame.trend
        - 0.01 * frame.risk
        + rng.normal(scale=0.15, size=len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return flag_trader_rolling_scores(
        frame,
        FEATURES,
        PRIOR,
        common_start="2005-01-31",
    )


def test_flag_trader_policy_uses_semantic_prior_and_produces_full_scores():
    frame = fixture()
    scores, diagnostics = run(frame)
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    ranked = cross_sectional_unit_rank(frame, FEATURES)
    semantic = ranked.loc[first, "value"] + ranked.loc[first, "momentum"] + 0.5 * ranked.loc[first, "trend"] - ranked.loc[first, "risk"]
    assert scores.loc[first].corr(semantic, method="spearman") > 0.99
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert diagnostics.finite_current_scores.eq(30).all()


def test_flag_trader_update_is_past_only_and_honors_clipping():
    frame = fixture()
    scores, diagnostics = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_diagnostics = run(changed)
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(diagnostics.iloc[0], changed_diagnostics.iloc[0])
    assert (pd.to_datetime(diagnostics.training_end) < pd.to_datetime(diagnostics.formation_month)).all()
    assert diagnostics.training_months.eq(60).all()
    assert diagnostics.clipped_gradient_norm.le(0.5 + 1e-15).all()
    assert diagnostics.parameter_delta_norm.le(0.0005 * 0.5 + 1e-15).all()
    assert diagnostics.action_memory_weight.eq(0.2).all()


def test_flag_trader_rejects_misaligned_prior():
    frame = fixture()
    try:
        flag_trader_rolling_scores(frame, FEATURES, [1.0], common_start="2005-01-31")
    except ValueError as error:
        assert "align uniquely" in str(error)
    else:
        raise AssertionError("misaligned semantic prior was accepted")
