from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import factfin_counterfactual_mcts_scores


STATE = {
    "price": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("prc_highprc_252d", 1), ("rvol_21d", -1)],
    "factors": [("be_me", 1), ("gp_at", 1), ("ocf_at", 1), ("f_score", 1), ("z_score", 1), ("qmj_prof", 1)],
    "factorized_news": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1), ("ret_1_0", 1)],
}
OBJECTIVE = {"validation_rankic": 1.0, "prediction_consistency": -0.01, "confidence_invariance": -0.01, "input_dependency_score": 0.01}


def fixture(months: int = 128, securities: int = 25) -> pd.DataFrame:
    rng = np.random.default_rng(137)
    dates = np.repeat(pd.date_range("1990-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(dict.fromkeys(feature for specifications in STATE.values() for feature, _ in specifications))
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
    return factfin_counterfactual_mcts_scores(
        frame,
        STATE,
        common_start="2000-01-31",
        training_start="1990-01-31",
        training_end="1997-12-31",
        validation_start="1998-01-31",
        validation_end="1999-12-31",
        initial_weights=[1 / 3, 1 / 3, 1 / 3],
        final_objective_weights=OBJECTIVE,
    )


def test_factfin_runs_depth_ten_mcts_and_fifty_counterfactual_scenarios():
    frame = fixture()
    scores, history, summary = run(frame)
    assert scores.loc[frame.month.ge("2000-01-31")].notna().all()
    assert len(history) == 100
    assert history.iteration.tolist() == list(range(1, 101))
    assert history.depth.max() <= 10
    assert history.counterfactual_finalist.any()
    assert history.selected_final.sum() == 1
    assert summary["mcts_iterations"] == 100
    assert summary["counterfactual_finalists"] == 10
    assert summary["counterfactual_scenarios"] == 50
    assert len(summary["selected_weights"]) == 3
    assert np.isclose(np.abs(summary["selected_weights"]).sum(), 1.0)


def test_factfin_is_deterministic_and_never_uses_common_period_outcomes():
    frame = fixture()
    scores, history, summary = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2000-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history, changed_summary = run(changed)
    pd.testing.assert_series_equal(scores, changed_scores)
    pd.testing.assert_frame_equal(history, changed_history)
    assert summary == changed_summary


def test_factfin_rejects_wrong_mcts_depth():
    frame = fixture()
    try:
        factfin_counterfactual_mcts_scores(
            frame,
            STATE,
            common_start="2000-01-31",
            training_start="1990-01-31",
            training_end="1997-12-31",
            validation_start="1998-01-31",
            validation_end="1999-12-31",
            initial_weights=[1 / 3, 1 / 3, 1 / 3],
            mcts_depth=5,
        )
    except ValueError as error:
        assert "depth or UCB" in str(error)
    else:
        raise AssertionError("wrong FactFin MCTS depth was accepted")
