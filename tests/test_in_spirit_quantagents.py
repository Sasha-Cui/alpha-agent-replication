from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import quantagents_meeting_scores


POOL = {
    "momentum_short": [("ret_1_0", 1)],
    "momentum_medium": [("ret_6_1", 1)],
    "momentum_long": [("ret_12_1", 1)],
    "breakout": [("prc_highprc_252d", 1), ("turnover_126d", 1)],
    "reversal": [("ret_1_0", -1), ("prc_highprc_252d", -1)],
    "value_quality": [("be_me", 1), ("gp_at", 1), ("ocf_at", 1), ("f_score", 1)],
    "sentiment_surprise": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1)],
    "low_risk": [("rvol_21d", -1), ("beta_60m", -1)],
    "financial_safety": [("z_score", 1), ("qmj_safety", 1), ("qmj_prof", 1)],
    "balanced_multi_factor": [("ret_12_1", 1), ("be_me", 1), ("gp_at", 1), ("rvol_21d", -1)],
}


def fixture(months: int = 128, securities: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(131)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(dict.fromkeys(feature for specifications in POOL.values() for feature, _ in specifications))
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.025 * frame.gp_at
        + 0.015 * frame.ret_12_1
        - 0.01 * frame.rvol_21d
        + rng.normal(scale=0.1, size=len(frame))
    )
    frame["ret"] = rng.normal(loc=0.005, scale=0.04, size=len(frame))
    frame["weight"] = rng.lognormal(size=len(frame))
    return frame


def run(frame: pd.DataFrame):
    return quantagents_meeting_scores(frame, POOL, common_start="2010-01-31")


def test_quantagents_runs_four_roles_three_memories_and_all_meetings():
    frame = fixture()
    scores, history = run(frame)
    common = frame.month.ge("2010-01-31")
    assert scores.loc[common].notna().all()
    assert history.memory_history_months.eq(120).all()
    assert history.memory_type_count.eq(3).all()
    assert history.retrieved_similar_cases.eq(10).all()
    assert history.strategy_pool_size.eq(10).all()
    assert history.proposed_strategy_members.str.count("\\|").eq(2).all()
    np.testing.assert_allclose(
        history.simulated_reward_weight + history.real_reward_weight,
        1.0,
        rtol=0,
        atol=1e-15,
    )
    assert history.risk_score.between(0.0, 1.0).all()
    assert history.finite_scores.eq(40).all()


def test_quantagents_is_deterministic_and_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2010-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first = frame.month.eq(pd.Timestamp("2010-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = run(frame)
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_quantagents_rejects_short_strategy_pool():
    frame = fixture()
    invalid = dict(POOL)
    invalid.pop("balanced_multi_factor")
    try:
        quantagents_meeting_scores(frame, invalid, common_start="2010-01-31")
    except ValueError as error:
        assert "ten frozen strategy-pool members" in str(error)
    else:
        raise AssertionError("short QuantAgents strategy pool was accepted")
