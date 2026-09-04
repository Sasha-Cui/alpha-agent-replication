from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import (
    ALPHAQUANTER_TOOL_COLUMNS,
    alphaquanter_rolling_scores,
    alphaquanter_tool_scores,
    multi_horizon_monthly_return,
)


PRIMITIVES = [
    "ret_12_1", "ret_6_1", "rvol_21d", "be_me", "gp_at", "f_score", "ocf_at",
    "ret_1_0", "rmax5_21d", "turnover_126d", "beta_60m",
]


def fixture(months: int = 75, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(29)
    dates = np.repeat(pd.date_range("1999-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids, "weight": rng.lognormal(size=len(ids))})
    for name in PRIMITIVES:
        frame[name] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(scale=0.05, size=len(frame))
    frame["ret_total_lead1m"] = 0.01 * frame.be_me + 0.015 * frame.ret_12_1 + rng.normal(scale=0.1, size=len(frame))
    frame["ret_exc_lead1m"] = frame.ret_total_lead1m - 0.001
    return frame


def test_alphaquanter_tools_are_four_finite_formation_time_scores():
    frame = fixture()
    tools = alphaquanter_tool_scores(frame)
    assert tools.columns.tolist() == ALPHAQUANTER_TOOL_COLUMNS
    assert tools.notna().all().all()
    changed = frame.copy()
    changed["ret_exc_lead1m"] *= -1000
    pd.testing.assert_frame_equal(tools, alphaquanter_tool_scores(changed))


def test_multi_horizon_reward_matches_one_three_six_month_compounding():
    frame = pd.DataFrame(
        {
            "security_id": [1] * 7,
            "month": pd.date_range("2000-01-31", periods=7, freq="ME"),
            "ret_total_lead1m": [0.01] * 7,
        }
    )
    reward = multi_horizon_monthly_return(frame)
    weights = np.array([1.0, 0.8, 0.8**2])
    weights /= weights.sum()
    expected = weights @ np.array([1.01 - 1, 1.01**3 - 1, 1.01**6 - 1])
    np.testing.assert_allclose(reward.iloc[0], expected, rtol=0, atol=1e-15)
    np.testing.assert_allclose(reward.iloc[1], expected, rtol=0, atol=1e-15)
    assert reward.iloc[2:].isna().all()


def test_selective_policy_uses_only_fully_realized_past_rewards():
    frame = fixture()
    tools = alphaquanter_tool_scores(frame)
    reward = multi_horizon_monthly_return(frame)
    scores, history = alphaquanter_rolling_scores(
        frame, tools, reward, common_start="2004-07-31"
    )
    changed_reward = reward.copy()
    changed_reward.loc[frame.month.gt("2004-01-31")] *= -1000
    changed_scores, changed_history = alphaquanter_rolling_scores(
        frame, tools, changed_reward, common_start="2004-07-31"
    )
    first = frame.month.eq(pd.Timestamp("2004-07-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    assert history.training_end.iloc[0] == "2004-01-31"
    assert history.training_months.eq(60).all()
    assert history.selected_tool_1.ne(history.selected_tool_2).all()
    assert history.finite_current_scores.eq(30).all()
