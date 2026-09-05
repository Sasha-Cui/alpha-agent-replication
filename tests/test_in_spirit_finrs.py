from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import finrs_risk_sensitive_scores


MEMORY = {
    "shallow_news": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1), ("ret_1_0", 1)],
    "middle_technical": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("prc_highprc_252d", 1), ("rvol_21d", -1)],
    "deep_fundamental": [("be_me", 1), ("gp_at", 1), ("ocf_at", 1), ("f_score", 1), ("z_score", 1), ("qmj_prof", 1)],
}


def fixture(months: int = 90, securities: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(157)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(dict.fromkeys(feature for specifications in MEMORY.values() for feature, _ in specifications))
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.025 * frame.gp_at + 0.015 * frame.ret_12_1 - 0.01 * frame.rvol_21d + rng.normal(scale=0.1, size=len(frame))
    )
    frame["ret"] = rng.normal(loc=0.005, scale=0.04, size=len(frame))
    return frame


def run(frame: pd.DataFrame):
    return finrs_risk_sensitive_scores(
        frame,
        MEMORY,
        common_start="2005-07-31",
        reward_horizons=[1, 3, 6],
        multi_timescale_weights=[1 / 3, 1 / 3, 1 / 3],
    )


def test_finrs_applies_kelly_cvar_volatility_and_exposure_controls():
    frame = fixture()
    scores, history = run(frame)
    common = frame.month.ge("2005-07-31")
    assert scores.loc[common].notna().all()
    assert scores.loc[common].abs().le(0.75).all()
    assert history.reward_history_months.eq(60).all()
    assert history.mean_win_probability.between(0.5, 0.75).all()
    assert history.mean_payoff_odds.between(0.5, 2.0).all()
    assert history.mean_scaled_kelly.ge(0.0).all()
    assert history.mean_volatility_adjustment.between(0.0, 1.0).all()
    assert history.mean_cvar_cap.between(0.0, 0.75).all()
    assert history.mean_final_absolute_exposure.le(history.mean_base_absolute_position).all()
    assert history.risk_shrunk_count.gt(0).all()
    assert history.finite_scores.eq(40).all()


def test_finrs_is_deterministic_and_ignores_current_and_future_rewards():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-07-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first = frame.month.eq(pd.Timestamp("2005-07-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = run(frame)
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_finrs_rejects_wrong_exposure_ceiling():
    frame = fixture()
    try:
        finrs_risk_sensitive_scores(
            frame,
            MEMORY,
            common_start="2005-07-31",
            reward_horizons=[1, 3, 6],
            multi_timescale_weights=[1 / 3, 1 / 3, 1 / 3],
            maximum_absolute_exposure=1.0,
        )
    except ValueError as error:
        assert "exposure ceiling" in str(error)
    else:
        raise AssertionError("wrong FINRS exposure ceiling was accepted")
