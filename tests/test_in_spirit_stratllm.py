from __future__ import annotations
import numpy as np
import pandas as pd
from alpha_evolve.in_spirit import stratllm_alignment_scores

SOURCES = {
    "price": [("momentum", 1), ("risk", -1)],
    "news": [("news", 1), ("attention", 1)],
    "annual_report": [("value", 1), ("quality", 1)],
}
STRATEGIES = {
    "S1_short_term_reversal": [("short_return", -1), ("extreme", -1)],
    "S2_breakout_momentum": [("momentum", 1), ("breakout", 1)],
    "S3_volatility_compression": [("risk", -1), ("momentum", 1)],
    "S4_price_volume_confirmation": [("momentum", 1), ("attention", 1)],
}


def fixture():
    rng = np.random.default_rng(211)
    frame = pd.DataFrame(
        {
            "month": np.repeat(pd.date_range("2000-01-31", periods=72, freq="ME"), 40),
            "security_id": np.tile(np.arange(40), 72),
            "weight": rng.lognormal(size=2880),
        }
    )
    for feature, _ in {item for values in [*SOURCES.values(), *STRATEGIES.values()] for item in values}:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(0, 0.04, len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.quality + rng.normal(0, 0.1, len(frame))
    return frame


def test_stratllm_selects_regime_modes_and_actions():
    frame = fixture()
    scores, history = stratllm_alignment_scores(frame, SOURCES, STRATEGIES, common_start="2005-01-31")
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert set(history.selected_mode).issubset({"free", "guided", "strict"})
    assert (history.buy_count + history.hold_count + history.sell_count).eq(40).all()
    np.testing.assert_allclose(history.filter(like="source_reliability__").sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.finite_scores.eq(40).all()


def test_stratllm_is_deterministic_and_reward_causal():
    frame = fixture()
    scores, history = stratllm_alignment_scores(frame, SOURCES, STRATEGIES, common_start="2005-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    other = stratllm_alignment_scores(changed, SOURCES, STRATEGIES, common_start="2005-01-31")
    first = frame.month.eq("2005-01-31")
    np.testing.assert_allclose(scores.loc[first], other[0].loc[first])
    pd.testing.assert_series_equal(history.iloc[0], other[1].iloc[0])


def test_stratllm_rejects_missing_strategy():
    bad = dict(STRATEGIES)
    bad.pop("S4_price_volume_confirmation")
    try:
        stratllm_alignment_scores(fixture(), SOURCES, bad, common_start="2005-01-31")
    except ValueError as error:
        assert "four frozen strategies" in str(error)
    else:
        raise AssertionError("missing strategy accepted")
