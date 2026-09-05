from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import atlas_adaptive_opro_scores


ANALYSTS = {
    "market": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("prc_highprc_252d", 1), ("rvol_21d", -1), ("beta_60m", -1)],
    "news": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1), ("ret_1_0", 1)],
    "fundamental": [("be_me", 1), ("gp_at", 1), ("ocf_at", 1), ("f_score", 1), ("z_score", 1), ("qmj_prof", 1)],
}
INITIAL = {"market": 1 / 3, "news": 1 / 3, "fundamental": 1 / 3}


def fixture(months: int = 15, securities: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(139)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(dict.fromkeys(feature for specifications in ANALYSTS.values() for feature, _ in specifications))
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.025 * frame.gp_at
        + 0.015 * frame.ret_12_1
        - 0.01 * frame.rvol_21d
        + rng.normal(scale=0.1, size=len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return atlas_adaptive_opro_scores(
        frame,
        ANALYSTS,
        common_start="2000-01-31",
        initial_analyst_weights=INITIAL,
    )


def test_atlas_updates_only_static_prompt_after_five_realized_decisions():
    frame = fixture()
    scores, history = run(frame)
    assert scores.notna().all()
    assert len(history) == 3
    assert history.prompt_version.tolist() == [0, 1, 2]
    assert history.window_decisions.eq(5).all()
    assert history.update_applied.tolist() == [True, True, False]
    np.testing.assert_allclose(
        history.feedback_score,
        np.clip(50.0 + 250.0 * history.window_roi, 0.0, 100.0),
        rtol=0,
        atol=1e-14,
    )
    current_weights = history[[f"analyst_weight__{analyst}" for analyst in ANALYSTS]]
    next_weights = history[[f"next_analyst_weight__{analyst}" for analyst in ANALYSTS]]
    np.testing.assert_allclose(current_weights.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    np.testing.assert_allclose(next_weights.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert (history.buy_count + history.hold_count + history.sell_count).eq(250).all()


def test_atlas_is_deterministic_and_does_not_replay_first_window():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed["ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first_window = frame.month.le(pd.Timestamp("2000-05-31"))
    pd.testing.assert_series_equal(scores.loc[first_window], changed_scores.loc[first_window])
    for name in ["prompt_version", "window_start", "window_end", "hold_threshold"]:
        assert history.iloc[0][name] == changed_history.iloc[0][name]
    repeat_scores, repeat_history = run(frame)
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_atlas_rejects_nonfive_window():
    frame = fixture()
    try:
        atlas_adaptive_opro_scores(
            frame,
            ANALYSTS,
            common_start="2000-01-31",
            evaluation_window_decisions=3,
        )
    except ValueError as error:
        assert "five-decision" in str(error)
    else:
        raise AssertionError("non-five ATLAS window was accepted")
