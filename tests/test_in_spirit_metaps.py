from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.in_spirit import metaps_strategy_scores, metaps_v3_router_scores


LIBRARY = {
    "news_impulse": {"inputs": ["niq_su", "saleq_su"]},
    "momentum_follow": {"inputs": ["ret_3_1", "ret_6_1"]},
    "mean_revert_fade": {"inputs": ["ret_1_0"]},
    "cross_asset_hedge": {"inputs": ["beta_60m", "ret_12_1"]},
    "risk_reset": {"inputs": ["rvol_21d", "beta_60m"]},
    "macro_rotation": {"inputs": ["ret_12_1", "beta_60m", "be_me"]},
    "earnings_drift": {"inputs": ["niq_su", "saleq_su", "ret_3_1"]},
    "liquidity_rebate": {"inputs": ["ret_1_0", "turnover_126d", "rvol_21d"]},
    "small_cap_breakout": {"inputs": ["ret_6_1", "prc_highprc_252d", "weight"]},
    "volatility_breakout": {"inputs": ["ret_1_0", "rvol_21d"]},
}


def fixture() -> pd.DataFrame:
    rng = np.random.default_rng(463)
    months = pd.date_range("1995-01-31", periods=96, freq="ME")
    frame = pd.DataFrame(
        {
            "month": np.repeat(months, 25),
            "security_id": np.tile(np.arange(25), len(months)),
            "weight": rng.lognormal(size=25 * len(months)),
        }
    )
    for feature in sorted(
        {name for specification in LIBRARY.values() for name in specification["inputs"] if name != "weight"}
        | {"gp_at", "ocf_at"}
    ):
        frame[feature] = rng.normal(size=len(frame))
    frame["rvol_21d"] = frame["rvol_21d"].abs()
    frame["turnover_126d"] = frame["turnover_126d"].abs()
    frame["ret"] = rng.normal(0.004, 0.04, len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame.ret_6_1 + 0.01 * frame.niq_su - 0.01 * frame.rvol_21d + rng.normal(0.0, 0.08, len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return metaps_v3_router_scores(
        frame,
        LIBRARY,
        common_start="2001-01-31",
        router_training_months=60,
        inner_tail_fraction=0.2,
        inner_minimum_side=5,
    )


def test_metaps_builds_ten_programs_and_monthly_v3_router():
    frame = fixture()
    strategies, state, relevance = metaps_strategy_scores(frame, LIBRARY)
    assert strategies.shape == (len(frame), 10)
    assert state.shape == (96, 8)
    assert relevance.shape == (96, 10)
    scores, history, rollout = run(frame)
    common = frame.month.ge("2001-01-31")
    assert scores.loc[common].notna().all()
    assert len(history) == 24 and len(rollout) == 96
    assert history.training_examples.eq(60).all()
    assert history.finite_scores.eq(25).all()
    assert set(history.exposure_bucket).issubset({"small", "medium", "large"})
    assert history.filter(like="v3_label_count__").sum(axis=1).eq(60).all()
    np.testing.assert_allclose(history.filter(like="router_probability__").sum(axis=1), 1.0, atol=1e-14)


def test_metaps_is_deterministic_and_first_decision_ignores_test_returns():
    frame = fixture()
    scores, history, rollout = run(frame)
    repeated = run(frame)
    pd.testing.assert_series_equal(scores, repeated[0])
    pd.testing.assert_frame_equal(history, repeated[1])
    pd.testing.assert_frame_equal(rollout, repeated[2])
    changed = frame.copy()
    changed.loc[changed.month.ge("2001-01-31"), "ret_exc_lead1m"] *= -1
    other_scores, other_history, _ = run(changed)
    first = frame.month.eq("2001-01-31")
    np.testing.assert_allclose(scores.loc[first], other_scores.loc[first], rtol=0, atol=0)
    pd.testing.assert_series_equal(history.iloc[0], other_history.iloc[0])


def test_metaps_rejects_truncated_candidate_context():
    with pytest.raises(ValueError, match="ten-strategy"):
        metaps_v3_router_scores(
            fixture(),
            LIBRARY,
            common_start="2001-01-31",
            router_training_months=60,
            candidate_budget=9,
            inner_tail_fraction=0.2,
            inner_minimum_side=5,
        )
