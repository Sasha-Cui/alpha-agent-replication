from __future__ import annotations
import numpy as np
import pandas as pd
from alpha_evolve.in_spirit import hubble_safe_diverse_scores

FAMILIES = {
    "range": [("range1", 1), ("range2", 1), ("range3", 1), ("range4", 1)],
    "volatility": [("vol1", 1), ("vol2", 1), ("vol3", 1), ("vol4", 1)],
    "liquidity_volume": [("liq1", 1), ("liq2", 1), ("liq3", -1), ("liq4", -1)],
}
WEIGHTS = {
    "rankic_ir": 0.30,
    "pearson_ic_ir": 0.20,
    "long_short_mean": 0.25,
    "turnover": -0.10,
    "coverage": 0.10,
    "complexity": -0.05,
}


def fixture():
    rng = np.random.default_rng(191)
    frame = pd.DataFrame(
        {
            "month": np.repeat(pd.date_range("1990-01-31", periods=60, freq="ME"), 30),
            "security_id": np.tile(np.arange(30), 60),
        }
    )
    for feature, _ in {item for specs in FAMILIES.values() for item in specs}:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.range1 + 0.015 * frame.vol1 + rng.normal(0, 0.08, len(frame))
    return frame


def run(frame):
    return hubble_safe_diverse_scores(
        frame,
        FAMILIES,
        calibration_start="1990-01-31",
        calibration_end="1993-12-31",
        common_start="1994-01-31",
        metric_weights=WEIGHTS,
    )


def test_hubble_search_is_safe_diverse_and_complete():
    frame = fixture()
    scores, metrics, history, summary = run(frame)
    assert scores.loc[frame.month.ge("1994-01-31")].notna().all()
    assert summary["candidate_count"] == 102
    assert len(history) == 15 and set(history["round"]) == {1, 2, 3}
    assert all(count <= 2 for count in pd.Series(summary["selected_families"]).value_counts())
    assert len(summary["selected_candidates"]) == 5
    assert set(WEIGHTS).issubset(metrics)


def test_hubble_search_is_deterministic_and_ignores_common_returns():
    frame = fixture()
    scores, metrics, history, summary = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("1994-01-31"), "ret_exc_lead1m"] *= -1000
    other = run(changed)
    pd.testing.assert_series_equal(scores, other[0])
    pd.testing.assert_frame_equal(metrics, other[1])
    pd.testing.assert_frame_equal(history, other[2])
    assert summary == other[3]


def test_hubble_rejects_wrong_round_count():
    try:
        hubble_safe_diverse_scores(
            fixture(),
            FAMILIES,
            calibration_start="1990-01-31",
            calibration_end="1993-12-31",
            common_start="1994-01-31",
            mining_rounds=2,
            metric_weights=WEIGHTS,
        )
    except ValueError as error:
        assert "mining rounds" in str(error)
    else:
        raise AssertionError("wrong Hubble rounds were accepted")
