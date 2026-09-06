from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.in_spirit import raptor_orchestrated_bl_scores


CARDS = {
    "fundamental": [("gp_at", 1), ("ocf_at", 1), ("z_score", 1)],
    "macro": [("beta_60m", 1), ("ret_12_1", 1), ("rvol_21d", -1)],
    "market": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", -1)],
    "news": [("niq_su", 1), ("saleq_su", 1), ("rmax5_21d", 1)],
    "social": [("turnover_126d", 1), ("rmax5_21d", 1), ("ret_1_0", 1)],
    "valuation": [("be_me", 1), ("ocf_at", 1)],
}
WEIGHTS = {
    "fundamental": 0.22,
    "macro": 0.16,
    "market": 0.22,
    "news": 0.18,
    "social": 0.10,
    "valuation": 0.12,
}


def fixture() -> pd.DataFrame:
    rng = np.random.default_rng(670)
    months = pd.date_range("1995-01-31", periods=84, freq="ME")
    securities = np.arange(40)
    frame = pd.DataFrame(
        {
            "month": np.repeat(months, len(securities)),
            "security_id": np.tile(securities, len(months)),
            "weight": rng.lognormal(4.0, 0.7, len(months) * len(securities)),
        }
    )
    for feature in sorted({column for card in CARDS.values() for column, _ in card}):
        frame[feature] = rng.normal(size=len(frame))
    frame["rvol_21d"] = frame["rvol_21d"].abs()
    frame["turnover_126d"] = frame["turnover_126d"].abs()
    frame["ret"] = rng.normal(0.006, 0.06, len(frame))
    frame["ret_exc_lead1m"] = rng.normal(0.0, 0.08, len(frame))
    return frame


def run(frame: pd.DataFrame):
    return raptor_orchestrated_bl_scores(
        frame,
        CARDS,
        WEIGHTS,
        common_start="2000-01-31",
    )


def test_raptor_builds_synchronized_agent_and_allocator_diagnostics():
    frame = fixture()
    scores, history = run(frame)
    common = frame.month.ge("2000-01-31")
    assert scores.loc[~common].isna().all()
    assert scores.loc[common].notna().all()
    assert len(history) == 24
    assert history.security_count.eq(40).all()
    assert history.append_only_message_count.eq(560).all()
    assert history.finite_score_count.eq(40).all()
    assert (history.final_BUY + history.final_HOLD + history.final_SELL).eq(40).all()
    for analyst in CARDS:
        assert (
            history[f"{analyst}_BUY"]
            + history[f"{analyst}_HOLD"]
            + history[f"{analyst}_SELL"]
        ).eq(40).all()
    np.testing.assert_allclose(history.long_only_weight_sum, 1.0, atol=1e-12)
    assert history.long_only_maximum_weight.le(0.10 + 1e-12).all()


def test_raptor_is_deterministic_and_does_not_use_current_or_forward_returns_for_views():
    frame = fixture()
    first_scores, first_history = run(frame)
    repeated_scores, repeated_history = run(frame)
    pd.testing.assert_series_equal(first_scores, repeated_scores)
    pd.testing.assert_frame_equal(first_history, repeated_history)

    changed = frame.copy()
    first_common = changed.month.eq("2000-01-31")
    changed.loc[changed.month.ge("2000-01-31"), "ret_exc_lead1m"] *= -100
    changed.loc[first_common, "ret"] *= -100
    second_scores, second_history = run(changed)
    pd.testing.assert_series_equal(first_scores.loc[first_common], second_scores.loc[first_common])
    pd.testing.assert_frame_equal(first_history.iloc[[0]], second_history.iloc[[0]])


def test_raptor_rejects_changes_to_the_frozen_agent_hierarchy():
    changed_weights = dict(WEIGHTS)
    changed_weights["market"] -= 0.01
    changed_weights["news"] += 0.01
    with pytest.raises(ValueError, match="weights changed"):
        raptor_orchestrated_bl_scores(
            fixture(),
            CARDS,
            changed_weights,
            common_start="2000-01-31",
        )
