from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import tradinggroup_reflection_scores


AGENTS = {
    "news_sentiment": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1), ("ret_1_0", 1)],
    "financial_report": [("be_me", 1), ("gp_at", 1), ("ocf_at", 1), ("f_score", 1), ("z_score", 1), ("qmj_prof", 1)],
    "technical": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("prc_highprc_252d", 1), ("rvol_21d", -1)],
}
STYLES = {
    "aggressive": {"risk_penalty": 0.0, "safety_bonus": 0.0, "positive_risk_intercept_quantile": 1.0},
    "balanced": {"risk_penalty": 0.25, "safety_bonus": 0.0, "positive_risk_intercept_quantile": 0.8},
    "conservative": {"risk_penalty": 0.5, "safety_bonus": 0.25, "positive_risk_intercept_quantile": 0.6},
}
RISK = ["rvol_21d", "beta_60m"]
SAFETY = ["z_score", "qmj_safety", "qmj_prof"]


def fixture(months: int = 88, securities: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(109)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(
        dict.fromkeys(
            [feature for specifications in AGENTS.values() for feature, _ in specifications]
            + RISK
            + SAFETY
        )
    )
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.025 * frame.gp_at
        + 0.015 * frame.ret_12_1
        - 0.01 * frame.rvol_21d
        + rng.normal(scale=0.1, size=len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return tradinggroup_reflection_scores(
        frame,
        AGENTS,
        STYLES,
        risk_features=RISK,
        safety_features=SAFETY,
        common_start="2006-09-30",
    )


def test_tradinggroup_runs_five_agent_chain_reflection_and_risk_intercepts():
    frame = fixture()
    scores, history = run(frame)
    common = frame.month.ge("2006-09-30")
    assert scores.loc[common].notna().all()
    assert history.forecast_reflection_months.eq(60).all()
    assert history.style_reflection_months.eq(20).all()
    assert set(history.selected_style) <= set(STYLES)
    assert history.risk_intercept_count.ge(0).all()
    assert history.finite_scores.eq(50).all()
    reliability = history.filter(like="agent_reliability__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert reliability.ge(0).all().all()


def test_tradinggroup_is_deterministic_and_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2006-09-30"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first = frame.month.eq(pd.Timestamp("2006-09-30"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = run(frame)
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_tradinggroup_rejects_a_missing_information_agent():
    frame = fixture()
    invalid = dict(AGENTS)
    invalid.pop("technical")
    try:
        tradinggroup_reflection_scores(
            frame,
            invalid,
            STYLES,
            risk_features=RISK,
            safety_features=SAFETY,
            common_start="2006-09-30",
        )
    except ValueError as error:
        assert "three frozen information agents" in str(error)
    else:
        raise AssertionError("incomplete TradingGroup agent chain was accepted")
