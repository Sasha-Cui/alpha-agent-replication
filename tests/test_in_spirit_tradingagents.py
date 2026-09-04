from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import tradingagents_debate_scores


ANALYSTS = {
    "market": ["ret_12_1", "ret_6_1", "prc_highprc_252d", "rvol_21d"],
    "social": ["ret_1_0", "rmax5_21d", "turnover_126d"],
    "news": ["niq_su", "saleq_su", "ret_1_0"],
    "fundamental": ["be_me", "gp_at", "ocf_at", "f_score", "o_score"],
}


def fixture(months: int = 70, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(61)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids, "weight": rng.lognormal(size=len(ids))})
    for feature in sorted({feature for values in ANALYSTS.values() for feature in values}):
        frame[feature] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(scale=0.04, size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.ret_12_1 + 0.01 * frame.gp_at + rng.normal(scale=0.1, size=len(frame))
    return frame


def test_tradingagents_runs_analyst_research_risk_and_manager_nodes():
    frame = fixture()
    scores, history = tradingagents_debate_scores(frame, ANALYSTS, common_start="2005-01-31")
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert history.finite_scores.eq(30).all()
    assert history.risk_choice.isin(["risk_seeking", "neutral", "conservative"]).all()
    assert history.risk_multiplier.isin([1.25, 1.0, 0.75]).all()
    reliability = history.filter(like="reliability_weight__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-15)
    assert history.mean_bull_case.ge(0).all()
    assert history.mean_bear_case.le(0).all()


def test_tradingagents_reflection_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = tradingagents_debate_scores(frame, ANALYSTS, common_start="2005-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = tradingagents_debate_scores(changed, ANALYSTS, common_start="2005-01-31")
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    assert history.reflection_end.iloc[0] == "2004-12-31"
    assert history.reflection_months.eq(60).all()


def test_tradingagents_rejects_wrong_risk_debate():
    frame = fixture()
    try:
        tradingagents_debate_scores(
            frame,
            ANALYSTS,
            common_start="2005-01-31",
            risk_multipliers={"risk_seeking": 1.0},
        )
    except ValueError as error:
        assert "risk proposals" in str(error)
    else:
        raise AssertionError("invalid risk debate was accepted")
