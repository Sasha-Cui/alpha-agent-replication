from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import alphaagents_debate_scores


SPECIALISTS = {
    "fundamental": [("be_me", 1), ("gp_at", 1), ("ocf_at", 1), ("f_score", 1), ("z_score", 1), ("qmj_prof", 1)],
    "sentiment": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1), ("ret_1_0", 1)],
    "valuation": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("prc_highprc_252d", 1), ("turnover_126d", 1), ("rvol_21d", -1)],
}
ORDER = ["fundamental", "sentiment", "valuation"]


def fixture(months: int = 8, securities: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(103)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(
        dict.fromkeys(feature for specifications in SPECIALISTS.values() for feature, _ in specifications)
    )
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = rng.normal(scale=0.1, size=len(frame))
    return frame


def test_alphaagents_runs_two_round_robin_passes_and_consolidates_consensus():
    frame = fixture()
    scores, history = alphaagents_debate_scores(frame, SPECIALISTS, speaker_order=ORDER)
    assert scores.notna().all()
    assert history.specialist_count.eq(3).all()
    assert history.round_robin_passes.eq(2).all()
    assert history.speaking_turns.eq(6).all()
    assert history.final_disagreement_rate.le(history.initial_disagreement_rate).all()
    np.testing.assert_allclose(
        history.final_disagreement_rate + history.unanimous_after_debate_rate,
        1.0,
        rtol=0,
        atol=1e-15,
    )
    assert history.finite_scores.eq(50).all()


def test_alphaagents_is_deterministic_and_ignores_all_return_outcomes():
    frame = fixture()
    scores, history = alphaagents_debate_scores(frame, SPECIALISTS, speaker_order=ORDER)
    changed = frame.copy()
    changed["ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = alphaagents_debate_scores(
        changed,
        SPECIALISTS,
        speaker_order=ORDER,
    )
    pd.testing.assert_series_equal(scores, changed_scores)
    pd.testing.assert_frame_equal(history, changed_history)


def test_alphaagents_rejects_a_single_pass_debate():
    frame = fixture()
    try:
        alphaagents_debate_scores(
            frame,
            SPECIALISTS,
            speaker_order=ORDER,
            round_robin_passes=1,
        )
    except ValueError as error:
        assert "at least two turns" in str(error)
    else:
        raise AssertionError("single-pass AlphaAgents debate was accepted")


def test_alphaagents_handles_missing_specialist_opinions_without_runtime_warnings():
    frame = fixture()
    first = frame.index[0]
    for feature, _ in SPECIALISTS["fundamental"]:
        frame.loc[first, feature] = np.nan
    for feature, _ in SPECIALISTS["sentiment"]:
        frame.loc[first, feature] = np.nan
    scores, history = alphaagents_debate_scores(frame, SPECIALISTS, speaker_order=ORDER)
    assert np.isnan(scores.loc[first])
    assert history.finite_scores.iloc[0] == 49
