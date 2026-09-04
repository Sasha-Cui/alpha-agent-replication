from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import finmem_layered_scores


LAYERS = {
    "shallow": {
        "features": ["ret_1_0", "rmax5_21d", "turnover_126d"],
        "daily_decay_alpha": 0.9,
        "retrieval_weights": {"recency": 0.8, "relevance": 0.15, "importance": 0.05},
    },
    "intermediate": {
        "features": ["ret_6_1", "ret_12_1", "rvol_21d"],
        "daily_decay_alpha": 0.967,
        "retrieval_weights": {"recency": 0.05, "relevance": 0.8, "importance": 0.15},
    },
    "deep": {
        "features": ["be_me", "gp_at", "ocf_at", "f_score"],
        "daily_decay_alpha": 0.988,
        "retrieval_weights": {"recency": 0.05, "relevance": 0.15, "importance": 0.8},
    },
}


def fixture(months: int = 70, securities: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(31)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids, "weight": rng.lognormal(size=len(ids))})
    features = sorted({feature for layer in LAYERS.values() for feature in layer["features"]})
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(scale=0.04, size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.ret_1_0 + 0.01 * frame.be_me + rng.normal(scale=0.1, size=len(frame))
    return frame


def test_finmem_retrieves_all_three_layers_and_top_five_memories():
    frame = fixture()
    scores, history = finmem_layered_scores(frame, LAYERS, common_start="2005-01-31")
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert history.finite_scores.eq(20).all()
    for layer in LAYERS:
        assert history[f"{layer}_memory_coverage"].eq(20).all()
        assert history[f"{layer}_mean_retrieved"].eq(5.0).all()


def test_finmem_current_decision_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = finmem_layered_scores(frame, LAYERS, common_start="2005-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = finmem_layered_scores(changed, LAYERS, common_start="2005-01-31")
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])


def test_finmem_character_switches_with_formation_time_market_regime():
    frame = fixture()
    frame.loc[frame.month.between("2004-10-31", "2004-12-31"), "ret"] = -0.05
    _, history = finmem_layered_scores(frame, LAYERS, common_start="2005-01-31")
    assert history.risk_character.iloc[0] == "risk_averse"
    frame.loc[frame.month.between("2004-11-30", "2005-01-31"), "ret"] = 0.05
    _, changed = finmem_layered_scores(frame, LAYERS, common_start="2005-01-31")
    assert changed.risk_character.iloc[0] == "risk_seeking"
