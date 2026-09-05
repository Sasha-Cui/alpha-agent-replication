from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import trading_r1_reward_policy_scores


GROUPS = {
    "technical": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("prc_highprc_252d", 1), ("rvol_21d", -1)],
    "fundamental": [("be_me", 1), ("gp_at", 1), ("ocf_at", 1), ("f_score", 1), ("z_score", 1), ("qmj_prof", 1)],
    "sentiment": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1), ("ret_1_0", 1)],
}
ACTIONS = ["STRONG SELL", "SELL", "HOLD", "BUY", "STRONG BUY"]
VALUES = [-1.0, -0.5, 0.0, 0.5, 1.0]
QUANTILES = [0.03, 0.15, 0.53, 0.85]
REWARD = np.asarray(
    [
        [1.0, 0.75, -1.25, -2.0, -2.25],
        [0.75, 1.0, -0.75, -1.5, -2.0],
        [-1.5, -1.0, 1.0, -1.0, -1.5],
        [-1.75, -1.25, -0.75, 1.0, 0.75],
        [-2.0, -1.5, -1.25, 0.75, 1.0],
    ]
)


def fixture(months: int = 90, securities: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(127)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(
        dict.fromkeys(feature for specifications in GROUPS.values() for feature, _ in specifications)
    )
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame.ret_12_1
        + 0.015 * frame.gp_at
        - 0.01 * frame.rvol_21d
        + rng.normal(scale=0.1, size=len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return trading_r1_reward_policy_scores(
        frame,
        GROUPS,
        action_names=ACTIONS,
        action_values=VALUES,
        truth_quantiles=QUANTILES,
        reward_matrix=REWARD,
        common_start="2007-03-31",
        label_horizons=[1, 3, 6],
        horizon_weights=[0.3, 0.5, 0.2],
    )


def test_trading_r1_uses_purged_labels_five_actions_and_group_relative_rewards():
    frame = fixture()
    scores, history = run(frame)
    common = frame.month.ge("2007-03-31")
    assert scores.loc[common].notna().all()
    assert history.policy_training_months.eq(60).all()
    assert (pd.to_datetime(history.label_cutoff) < pd.to_datetime(history.formation_month)).all()
    assert history.training_rows.gt(1000).all()
    assert history.mean_group_relative_advantage.gt(0).all()
    assert history.mean_best_second_reward_margin.ge(0).all()
    action_counts = history.filter(like="action_count__")
    assert (action_counts.sum(axis=1) == 40).all()
    assert history.finite_scores.eq(40).all()


def test_trading_r1_is_deterministic_and_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2007-03-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first = frame.month.eq(pd.Timestamp("2007-03-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = run(frame)
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_trading_r1_rejects_short_label_purge():
    frame = fixture()
    try:
        trading_r1_reward_policy_scores(
            frame,
            GROUPS,
            action_names=ACTIONS,
            action_values=VALUES,
            truth_quantiles=QUANTILES,
            reward_matrix=REWARD,
            common_start="2007-03-31",
            label_horizons=[1, 3, 6],
            horizon_weights=[0.3, 0.5, 0.2],
            label_purge_months=3,
        )
    except ValueError as error:
        assert "shorter than the longest horizon" in str(error)
    else:
        raise AssertionError("short Trading-R1 label purge was accepted")
