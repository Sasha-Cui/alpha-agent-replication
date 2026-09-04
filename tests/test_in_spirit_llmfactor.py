from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import llmfactor_rolling_scores


FACTORS = ["ret_1_0", "rmax5_21d", "turnover_126d", "niq_su", "saleq_su", "be_me", "gp_at", "o_score"]
PEER_FEATURES = ["market_equity", "be_me", "gp_at"]
PEER_INPUTS = ["ret_1_0", "ret_6_1"]


def fixture(months: int = 70, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(43)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    for feature in sorted(set([*FACTORS, *PEER_FEATURES, *PEER_INPUTS])):
        frame[feature] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(scale=0.05, size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.niq_su - 0.01 * frame.o_score + rng.normal(scale=0.1, size=len(frame))
    return frame


def run(frame: pd.DataFrame):
    return llmfactor_rolling_scores(
        frame,
        FACTORS,
        PEER_FEATURES,
        PEER_INPUTS,
        common_start="2005-01-31",
    )


def test_llmfactor_executes_relation_five_factor_and_five_price_stages():
    frame = fixture()
    scores, history = run(frame)
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert history.peer_relation_coverage.eq(30).all()
    assert history.five_price_history_coverage.eq(30).all()
    assert history.finite_scores.eq(30).all()
    assert history.filter(regex=r"^factor_[1-5]$").nunique(axis=1).eq(5).all()


def test_llmfactor_prediction_ignores_current_and_future_labels():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    assert history.training_end.iloc[0] == "2004-12-31"
    assert history.training_months.eq(60).all()


def test_llmfactor_rejects_wrong_factor_cardinality():
    frame = fixture()
    try:
        llmfactor_rolling_scores(
            frame,
            FACTORS[:7],
            PEER_FEATURES,
            PEER_INPUTS,
            common_start="2005-01-31",
        )
    except ValueError as error:
        assert "eight candidates" in str(error)
    else:
        raise AssertionError("invalid factor cardinality was accepted")
