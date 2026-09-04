from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import hedgeagents_conference_scores


SPECIALISTS = {
    "speculative": ["beta_60m", "rvol_21d", "ret_12_1", "at_me"],
    "equity": ["ret_12_1", "ret_6_1", "be_me", "gp_at", "f_score"],
    "defensive": ["z_score", "qmj_safety", "qmj_prof", "rvol_21d", "beta_60m"],
}


def fixture(months: int = 70, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(71)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids, "weight": rng.lognormal(size=len(ids))})
    for feature in sorted({feature for values in SPECIALISTS.values() for feature in values}):
        frame[feature] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(scale=0.03, size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.gp_at + 0.01 * frame.qmj_safety + rng.normal(scale=0.1, size=len(frame))
    return frame


def test_hedgeagents_allocates_three_sleeves_and_shares_experience():
    frame = fixture()
    scores, history = hedgeagents_conference_scores(frame, SPECIALISTS, common_start="2005-01-31")
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert history.finite_scores.eq(30).all()
    allocation = history.filter(like="allocation__")
    np.testing.assert_allclose(allocation.sum(axis=1), 1.0, rtol=0, atol=1e-15)
    assert allocation.ge(0.1 / 3 - 1e-15).all().all()
    assert history.conference_months.eq(60).all()


def test_hedgeagents_conference_uses_only_past_outcomes():
    frame = fixture()
    scores, history = hedgeagents_conference_scores(frame, SPECIALISTS, common_start="2005-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = hedgeagents_conference_scores(changed, SPECIALISTS, common_start="2005-01-31")
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    assert history.conference_end.iloc[0] == "2004-12-31"


def test_hedgeagents_extreme_market_forces_defensive_allocation():
    frame = fixture()
    frame.loc[frame.month.eq("2005-01-31"), "ret"] = 0.1
    _, history = hedgeagents_conference_scores(frame, SPECIALISTS, common_start="2005-01-31")
    assert bool(history.extreme_conference.iloc[0])
    assert history["allocation__defensive"].iloc[0] >= 0.5
