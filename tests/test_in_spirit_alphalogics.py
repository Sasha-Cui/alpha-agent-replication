from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import alphalogics_evolution_scores


LOGICS = {
    "trend": [("momentum", 1), ("trend", 1), ("volume", 1), ("risk", -1)],
    "reversal": [("short_return", -1), ("extreme", -1), ("risk", -1), ("volume", 1)],
}


def fixture(months: int = 72, securities: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(173)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(dict.fromkeys(feature for specs in LOGICS.values() for feature, _ in specs))
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame["momentum"]
        - 0.015 * frame["risk"]
        - 0.01 * frame["short_return"]
        + rng.normal(scale=0.08, size=len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return alphalogics_evolution_scores(
        frame,
        LOGICS,
        calibration_train_start="2000-01-31",
        calibration_train_end="2001-12-31",
        calibration_validation_start="2002-01-31",
        calibration_validation_end="2003-12-31",
        common_start="2004-01-31",
        round_operation_order=[
            "identity",
            "pair_mean",
            "pair_product",
            "triple_mean",
            "positive_gate",
        ],
        minimum_validation_months=20,
    )


def test_alphalogics_runs_five_persistent_compiled_search_rounds():
    frame = fixture()
    scores, history, summary = run(frame)
    common = frame.month.ge("2004-01-31")
    assert scores.loc[common].notna().all()
    assert len(history) == 10
    assert set(history.outer_round) == {1, 2, 3, 4, 5}
    assert set(history.market_logic) == set(LOGICS)
    assert history.candidates_evaluated.between(1, 8).all()
    assert history.incumbent_validation_icir.ge(0.0).all()
    assert set(summary["selected_expressions"]) == set(LOGICS)
    assert set(summary["selected_orientations"].values()).issubset({-1, 1})
    assert summary["calibration_observations"] == 48 * 50
    assert summary["finite_common_scores"] == int(common.sum())


def test_alphalogics_is_deterministic_and_ignores_common_returns():
    frame = fixture()
    scores, history, summary = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2004-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history, changed_summary = run(changed)
    pd.testing.assert_series_equal(scores, changed_scores)
    pd.testing.assert_frame_equal(history, changed_history)
    assert summary == changed_summary


def test_alphalogics_rejects_wrong_rounds_or_overlapping_holdout():
    frame = fixture()
    for operations, common_start in (
        (["identity"], "2004-01-31"),
        (["identity", "pair_mean", "pair_product", "triple_mean", "positive_gate"], "2003-01-31"),
    ):
        try:
            alphalogics_evolution_scores(
                frame,
                LOGICS,
                calibration_train_start="2000-01-31",
                calibration_train_end="2001-12-31",
                calibration_validation_start="2002-01-31",
                calibration_validation_end="2003-12-31",
                common_start=common_start,
                round_operation_order=operations,
            )
        except ValueError as error:
            assert "five frozen DSL rounds" in str(error) or "chronology" in str(error)
        else:
            raise AssertionError("invalid AlphaLogics search was accepted")
