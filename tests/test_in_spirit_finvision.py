from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import finvision_consensus_scores


FEATURES = [
    "niq_su", "saleq_su", "ret_1_0", "turnover_126d", "ret_3_1", "ret_6_1",
    "prc_highprc_252d", "rvol_21d",
]


def fixture(months: int = 70, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(59)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    for feature in FEATURES:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.niq_su + 0.01 * frame.ret_6_1 + rng.normal(scale=0.1, size=len(frame))
    return frame


def test_finvision_combines_four_upstream_agents_and_position_diagnostics():
    frame = fixture()
    scores, history = finvision_consensus_scores(frame, common_start="2005-01-31")
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert history.finite_scores.eq(30).all()
    assert (history.buy_count + history.sell_count + history.hold_count).eq(30).all()
    reliability = history.filter(like="reliability_weight__")
    assert reliability.shape[1] == 4
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-15)
    assert history.average_active_position_size.between(1, 10).all()


def test_finvision_decision_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = finvision_consensus_scores(frame, common_start="2005-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = finvision_consensus_scores(changed, common_start="2005-01-31")
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    assert history.reliability_end.iloc[0] == "2004-12-31"
    assert history.reliability_months.eq(60).all()


def test_finvision_rejects_invalid_reliability_window():
    frame = fixture()
    try:
        finvision_consensus_scores(
            frame,
            common_start="2005-01-31",
            reliability_months=12,
            minimum_rankic_months=24,
        )
    except ValueError as error:
        assert "reliability configuration" in str(error)
    else:
        raise AssertionError("invalid FinVision reliability window was accepted")
