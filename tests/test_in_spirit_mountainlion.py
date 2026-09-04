from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import mountainlion_fusion_scores


MODALITIES = {
    "technical": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("prc_highprc_252d", 1), ("rvol_21d", -1)],
    "market_dynamics": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1), ("beta_60m", 1)],
    "fundamental_quality": [("gp_at", 1), ("ocf_at", 1), ("f_score", 1), ("z_score", 1), ("qmj_prof", 1)],
    "valuation_safety": [("be_me", 1), ("at_me", 1), ("qmj_safety", 1), ("beta_60m", -1)],
}
ML_FEATURES = ["ret_12_1", "ret_6_1", "ret_1_0", "prc_highprc_252d", "rvol_21d"]


def fixture(months: int = 92, securities: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(97)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(
        dict.fromkeys(feature for specifications in MODALITIES.values() for feature, _ in specifications)
    )
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame.ret_12_1
        + 0.015 * frame.gp_at
        - 0.01 * frame.rvol_21d
        + rng.normal(scale=0.1, size=len(frame))
    )
    return frame


def test_mountainlion_runs_four_agents_two_tracks_and_adaptive_fusion():
    frame = fixture()
    scores, history = mountainlion_fusion_scores(
        frame,
        MODALITIES,
        ML_FEATURES,
        common_start="2007-01-31",
    )
    common = frame.month.ge("2007-01-31")
    assert scores.loc[common].notna().all()
    assert history.agent_count.eq(4).all()
    assert history.modality_count.eq(4).all()
    assert history.ml_training_months.eq(60).all()
    assert history.fusion_history_months.eq(24).all()
    assert history.llm_alpha.between(0.1, 0.9).all()
    assert history.modality_disagreement_rate.between(0.0, 1.0).all()
    assert history.finite_scores.eq(50).all()


def test_mountainlion_is_deterministic_and_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = mountainlion_fusion_scores(
        frame,
        MODALITIES,
        ML_FEATURES,
        common_start="2007-01-31",
    )
    changed = frame.copy()
    changed.loc[changed.month.ge("2007-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = mountainlion_fusion_scores(
        changed,
        MODALITIES,
        ML_FEATURES,
        common_start="2007-01-31",
    )
    first = frame.month.eq(pd.Timestamp("2007-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = mountainlion_fusion_scores(
        frame,
        MODALITIES,
        ML_FEATURES,
        common_start="2007-01-31",
    )
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_mountainlion_rejects_missing_agent_modality():
    frame = fixture()
    invalid = dict(MODALITIES)
    invalid.pop("valuation_safety")
    try:
        mountainlion_fusion_scores(
            frame,
            invalid,
            ML_FEATURES,
            common_start="2007-01-31",
        )
    except ValueError as error:
        assert "four frozen modalities" in str(error)
    else:
        raise AssertionError("incomplete MountainLion modality graph was accepted")
