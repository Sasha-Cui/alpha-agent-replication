from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import agentic_screening_precision_scores


def fixture(months: int = 210, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(181)
    frame = pd.DataFrame({
        "month": np.repeat(pd.date_range("1984-01-31", periods=months, freq="ME"), securities),
        "security_id": np.tile(np.arange(securities), months),
    })
    for column in ["market_equity", "be_me", "ret_12_1", "niq_su", "saleq_su", "ret_1_0", "turnover_126d"]:
        frame[column] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(0.005, 0.05, len(frame))
    return frame


def test_agentic_screening_combines_agents_and_precision():
    frame = fixture()
    scores, history = agentic_screening_precision_scores(frame, common_start="1999-07-31")
    common = frame.month.ge("1999-07-31")
    assert scores.loc[common].notna().all()
    assert (history.final_buy_count + history.final_hold_count + history.final_sell_count).eq(30).all()
    assert history.finite_precision_count.eq(30).all()
    assert history.finite_scores.eq(30).all()


def test_agentic_screening_is_deterministic_and_return_causal():
    frame = fixture()
    scores, history = agentic_screening_precision_scores(frame, common_start="1999-07-31")
    changed = frame.copy()
    changed.loc[changed.month.gt("1999-07-31"), "ret"] *= -100
    changed_scores, changed_history = agentic_screening_precision_scores(changed, common_start="1999-07-31")
    first = frame.month.eq("1999-07-31")
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = agentic_screening_precision_scores(frame, common_start="1999-07-31")
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_agentic_screening_rejects_short_precision_history():
    try:
        agentic_screening_precision_scores(fixture(), common_start="1999-07-31", formation_history_months=60)
    except ValueError as error:
        assert "precision history" in str(error)
    else:
        raise AssertionError("short precision history was accepted")
