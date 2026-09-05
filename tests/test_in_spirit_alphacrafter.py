from __future__ import annotations
import numpy as np
import pandas as pd
from alpha_evolve.in_spirit import alphacrafter_workflow_scores

MINERS = {
    "technical_miner": [("m1", 1), ("m2", 1), ("m3", 1), ("m4", 1)],
    "fundamental_miner": [("f1", 1), ("f2", 1), ("f3", 1), ("f4", 1)],
    "risk_reversal_miner": [("r1", -1), ("r2", -1), ("r3", -1), ("r4", -1)],
}


def fixture():
    rng = np.random.default_rng(199)
    frame = pd.DataFrame(
        {
            "month": np.repeat(pd.date_range("1990-01-31", periods=100, freq="ME"), 40),
            "security_id": np.tile(np.arange(40), 100),
            "weight": rng.lognormal(size=4000),
        }
    )
    for feature, _ in {item for values in MINERS.values() for item in values}:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(0, 0.04, len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.m1 + 0.015 * frame.f1 - 0.01 * frame.r1 + rng.normal(0, 0.1, len(frame))
    return frame


def run(frame):
    return alphacrafter_workflow_scores(
        frame, MINERS, common_start="1996-01-31", validation_horizons=[1, 3, 6], validation_horizon_weights=[1 / 3] * 3
    )


def test_alphacrafter_runs_miner_screener_trader_workflow():
    frame = fixture()
    scores, history = run(frame)
    assert scores.loc[frame.month.ge("1996-01-31")].notna().all()
    assert history.maintenance_months.eq(60).all()
    assert history.selected_factor_count.eq(5).all()
    assert history.selected_miners.str.split("|").map(len).ge(2).all()
    assert history.finite_scores.eq(40).all()


def test_alphacrafter_is_deterministic_and_reward_causal():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("1996-01-31"), "ret_exc_lead1m"] *= -1000
    other = run(changed)
    first = frame.month.eq("1996-01-31")
    np.testing.assert_allclose(scores.loc[first], other[0].loc[first])
    pd.testing.assert_series_equal(history.iloc[0], other[1].iloc[0])


def test_alphacrafter_rejects_short_purge():
    try:
        alphacrafter_workflow_scores(
            fixture(),
            MINERS,
            common_start="1996-01-31",
            validation_horizons=[1, 3, 6],
            validation_horizon_weights=[1 / 3] * 3,
            reward_purge_months=3,
        )
    except ValueError as error:
        assert "purge" in str(error)
    else:
        raise AssertionError("short purge accepted")
