from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.in_spirit import fin_analyst_hierarchy_scores


SPECIALISTS = {
    "news": [("niq_su", 1), ("saleq_su", 1), ("ret_1_0", 1)],
    "event": [("niq_su", 1), ("saleq_su", 1), ("rmax5_21d", 1)],
    "quarterly": [("niq_su", 1), ("saleq_su", 1), ("ocf_at", 1)],
    "annual": [("be_me", 1), ("gp_at", 1), ("z_score", 1)],
    "fundamentals": [("gp_at", 1), ("ocf_at", 1), ("z_score", 1), ("be_me", 1)],
    "analyst": [("niq_su", 1), ("saleq_su", 1), ("gp_at", 1)],
    "technical": [("ret_6_1", 1), ("prc_highprc_252d", 1), ("ret_1_0", -1), ("rvol_21d", -1)],
    "social": [("turnover_126d", 1), ("rmax5_21d", 1), ("ret_1_0", 1)],
}
WEIGHTS = {
    "news": 0.25,
    "event": 0.16,
    "quarterly": 0.14,
    "technical": 0.11,
    "fundamentals": 0.11,
    "analyst": 0.11,
    "social": 0.07,
    "annual": 0.05,
}


def fixture() -> pd.DataFrame:
    rng = np.random.default_rng(557)
    months = pd.date_range("2000-01-31", periods=12, freq="ME")
    frame = pd.DataFrame({"month": np.repeat(months, 40), "security_id": np.tile(np.arange(40), 12)})
    features = sorted({feature for values in SPECIALISTS.values() for feature, _ in values})
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = rng.normal(0.0, 0.08, len(frame))
    return frame


def test_fin_analyst_hierarchy_resolves_every_specialist_panel():
    frame = fixture()
    scores, history = fin_analyst_hierarchy_scores(frame, SPECIALISTS, WEIGHTS)
    assert scores.notna().all() and len(history) == 12
    assert history.finite_scores.eq(40).all()
    assert (
        (
            history.news_override_count
            + history.majority_buy_count
            + history.majority_sell_count
            + history.weighted_resolution_count
        )
        .eq(40)
        .all()
    )
    assert (history.meta_buy_count + history.meta_hold_count + history.meta_sell_count).eq(40).all()
    for name in SPECIALISTS:
        assert (
            (history[f"{name}_buy_count"] + history[f"{name}_hold_count"] + history[f"{name}_sell_count"]).eq(40).all()
        )


def test_fin_analyst_is_deterministic_and_does_not_read_future_returns():
    frame = fixture()
    first = fin_analyst_hierarchy_scores(frame, SPECIALISTS, WEIGHTS)
    changed = frame.copy()
    changed["ret_exc_lead1m"] *= -1000
    second = fin_analyst_hierarchy_scores(changed, SPECIALISTS, WEIGHTS)
    pd.testing.assert_series_equal(first[0], second[0])
    pd.testing.assert_frame_equal(first[1], second[1])


def test_fin_analyst_rejects_incomplete_specialist_panel():
    bad = dict(SPECIALISTS)
    bad.pop("social")
    with pytest.raises(ValueError, match="eight frozen specialists"):
        fin_analyst_hierarchy_scores(fixture(), bad, WEIGHTS)
