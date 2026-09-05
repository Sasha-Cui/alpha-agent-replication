from __future__ import annotations
import numpy as np
import pandas as pd
from alpha_evolve.in_spirit import marketsenseai_strongbuy_scores

SPECIALISTS = {
    "news": ["niq_su", "saleq_su", "ret_1_0", "turnover_126d"],
    "fundamentals": ["be_me", "gp_at", "ocf_at", "f_score", "o_score"],
    "dynamics": ["ret_12_1", "ret_6_1", "prc_highprc_252d", "rvol_21d", "beta_60m"],
    "macro": ["ret", "weight", "beta_60m", "rvol_21d"],
}


def fixture():
    rng = np.random.default_rng(197)
    frame = pd.DataFrame(
        {
            "month": np.repeat(pd.date_range("2000-01-31", periods=70, freq="ME"), 40),
            "security_id": np.tile(np.arange(40), 70),
            "weight": rng.lognormal(size=2800),
        }
    )
    for feature in sorted({f for values in SPECIALISTS.values() for f in values} - {"ret", "weight"}):
        frame[feature] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(0, 0.04, len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.gp_at + rng.normal(0, 0.1, len(frame))
    return frame


def test_strongbuy_policy_emits_five_fixed_classes():
    frame = fixture()
    scores, history = marketsenseai_strongbuy_scores(frame, SPECIALISTS, common_start="2005-01-31")
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert history.strong_sell_count.eq(0).all()
    assert history.sell_count.eq(2).all()
    assert history.hold_count.eq(31).all()
    assert history.buy_count.eq(4).all()
    assert history.strong_buy_count.eq(3).all()
    assert history.finite_scores.eq(40).all()


def test_strongbuy_policy_is_deterministic_and_reward_causal():
    frame = fixture()
    scores, history = marketsenseai_strongbuy_scores(frame, SPECIALISTS, common_start="2005-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    other = marketsenseai_strongbuy_scores(changed, SPECIALISTS, common_start="2005-01-31")
    first = frame.month.eq("2005-01-31")
    np.testing.assert_allclose(scores.loc[first], other[0].loc[first])
    pd.testing.assert_series_equal(history.iloc[0], other[1].iloc[0])


def test_strongbuy_rejects_unsorted_boundaries():
    try:
        marketsenseai_strongbuy_scores(
            fixture(), SPECIALISTS, common_start="2005-01-31", percentile_boundaries=(0.2, 0.1, 0.8, 0.9)
        )
    except ValueError as error:
        assert "boundaries" in str(error)
    else:
        raise AssertionError("bad MarketSenseAI boundaries were accepted")
