from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import fincon_rolling_scores


ANALYSTS = {
    "market": ["ret_12_1", "ret_6_1", "rvol_21d"],
    "fundamental": ["be_me", "gp_at", "ocf_at", "f_score"],
    "attention": ["ret_1_0", "rmax5_21d", "turnover_126d"],
    "risk": ["z_score", "o_score", "rvol_21d"],
}


def fixture(months: int = 70, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(47)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    for feature in sorted({feature for values in ANALYSTS.values() for feature in values}):
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.ret_12_1 + 0.01 * frame.gp_at + rng.normal(scale=0.1, size=len(frame))
    return frame


def test_fincon_runs_four_analysts_belief_updates_and_cvar_control():
    frame = fixture()
    scores, history = fincon_rolling_scores(frame, ANALYSTS, common_start="2005-01-31")
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert history.finite_scores.eq(30).all()
    assert history.cvar_coverage.eq(30).all()
    beliefs = history.filter(like="belief_weight__")
    np.testing.assert_allclose(beliefs.sum(axis=1), 1.0, rtol=0, atol=1e-15)
    assert beliefs.gt(0).all().all()


def test_fincon_current_score_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = fincon_rolling_scores(frame, ANALYSTS, common_start="2005-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = fincon_rolling_scores(changed, ANALYSTS, common_start="2005-01-31")
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    assert history.procedural_end.iloc[0] == "2004-12-31"
    assert history.procedural_months.eq(60).all()


def test_fincon_rejects_missing_analyst_role():
    frame = fixture()
    try:
        fincon_rolling_scores(frame, {"market": ANALYSTS["market"]}, common_start="2005-01-31")
    except ValueError as error:
        assert "four analyst roles" in str(error)
    else:
        raise AssertionError("incomplete analyst hierarchy was accepted")
