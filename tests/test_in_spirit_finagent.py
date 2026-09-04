from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import finagent_rolling_scores


FEATURES = [
    "be_me", "gp_at", "ocf_at", "ret_1_0", "turnover_126d", "ret_3_1",
    "ret_6_1", "ret_12_1", "rvol_21d", "prc_highprc_252d",
]


def fixture(months: int = 70, securities: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(41)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    for feature in FEATURES:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.ret_12_1 - 0.01 * frame.ret_1_0 + rng.normal(scale=0.1, size=len(frame))
    return frame


def test_finagent_runs_multimodal_memory_reflection_and_tool_stages():
    frame = fixture()
    scores, history = finagent_rolling_scores(frame, common_start="2005-01-31")
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert history.finite_scores.eq(20).all()
    assert history.selected_tool.isin(
        ["medium_term_momentum", "short_term_reversal", "price_breakout"]
    ).all()
    for query in ("short", "medium", "long"):
        assert history[f"{query}_memory_coverage"].eq(20).all()
        assert history[f"{query}_mean_retrieved"].eq(5.0).all()


def test_finagent_current_decision_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = finagent_rolling_scores(frame, common_start="2005-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = finagent_rolling_scores(changed, common_start="2005-01-31")
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    assert history.training_end.iloc[0] == "2004-12-31"
    assert history.training_months.eq(60).all()


def test_finagent_rejects_invalid_reflection_mix():
    frame = fixture()
    try:
        finagent_rolling_scores(
            frame,
            common_start="2005-01-31",
            high_level_weight=0.6,
            tool_weight=0.5,
        )
    except ValueError as error:
        assert "reflection weights" in str(error)
    else:
        raise AssertionError("invalid reflection mixture was accepted")
