from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.in_spirit import alphaagentevo_policy_scores


SEEDS = [
    "ret_1_0",
    "ret_3_1",
    "ret_6_1",
    "ret_12_1",
    "be_me",
    "gp_at",
    "ocf_at",
    "z_score",
    "rvol_21d",
    "beta_60m",
    "turnover_126d",
    "niq_su",
]
REWARD = {"validity": 0.2, "quality": 0.35, "diversity": 0.2, "novelty": 0.15, "tool_efficiency": 0.1}


def fixture() -> pd.DataFrame:
    rng = np.random.default_rng(631)
    months = pd.date_range("1995-01-31", periods=84, freq="ME")
    frame = pd.DataFrame(
        {
            "month": np.repeat(months, 25),
            "security_id": np.tile(np.arange(25), len(months)),
            "weight": rng.lognormal(size=25 * len(months)),
        }
    )
    for feature in SEEDS:
        frame[feature] = rng.normal(size=len(frame))
    frame["rvol_21d"] = frame["rvol_21d"].abs()
    frame["turnover_126d"] = frame["turnover_126d"].abs()
    frame["ret"] = rng.normal(0.004, 0.04, len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame.ret_12_1 + 0.01 * frame.gp_at - 0.008 * frame.rvol_21d + rng.normal(0.0, 0.08, len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return alphaagentevo_policy_scores(
        frame,
        SEEDS,
        REWARD,
        common_start="2000-01-31",
        training_months=60,
        training_steps=20,
        elite_pool_capacity=5,
    )


def test_alphaagentevo_runs_four_call_group_relative_training():
    frame = fixture()
    scores, elites, tools, steps = run(frame)
    assert scores.loc[frame.month.ge("2000-01-31")].notna().all()
    assert len(elites) == 5 and elites.selected_final.sum() == 1
    assert len(tools) == 80 and tools.groupby("step").size().eq(4).all()
    assert len(steps) == 20 and steps.elite_pool_size.iloc[-1] == 5
    reward_columns = tools.filter(like="reward__")
    assert reward_columns.ge(0.0).all().all() and reward_columns.le(1.0).all().all()
    np.testing.assert_allclose(tools.groupby("step").group_relative_advantage.sum(), 0.0, atol=1e-12)


def test_alphaagentevo_is_deterministic_and_common_period_is_sealed():
    frame = fixture()
    first = run(frame)
    repeated = run(frame)
    for left, right in zip(first, repeated):
        if isinstance(left, pd.Series):
            pd.testing.assert_series_equal(left, right)
        else:
            pd.testing.assert_frame_equal(left, right)
    changed = frame.copy()
    changed.loc[changed.month.ge("2000-01-31"), "ret_exc_lead1m"] *= -1
    second = run(changed)
    for left, right in zip(first, second):
        if isinstance(left, pd.Series):
            pd.testing.assert_series_equal(left, right)
        else:
            pd.testing.assert_frame_equal(left, right)


def test_alphaagentevo_enforces_four_call_cap():
    with pytest.raises(ValueError, match="four-call"):
        alphaagentevo_policy_scores(
            fixture(),
            SEEDS,
            REWARD,
            common_start="2000-01-31",
            training_months=60,
            training_steps=5,
            offspring_tool_calls_per_step=3,
            maximum_tool_calls=3,
            elite_pool_capacity=5,
        )
