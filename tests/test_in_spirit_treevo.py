from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import treevo_evolution_scores


SEEDS = [
    ("ret_12_1", 1),
    ("ret_6_1", 1),
    ("ret_1_0", 1),
    ("prc_highprc_252d", 1),
    ("turnover_126d", 1),
    ("rvol_21d", -1),
]


def fixture(months: int = 130, securities: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(107)
    dates = np.repeat(pd.date_range("1990-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    for feature, _ in SEEDS:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.03 * frame.ret_12_1
        - 0.015 * frame.rvol_21d
        + rng.normal(scale=0.1, size=len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return treevo_evolution_scores(
        frame,
        SEEDS,
        common_start="2000-01-31",
        training_start="1990-01-31",
        training_end="1997-12-31",
        validation_start="1998-01-31",
        validation_end="1999-12-31",
    )


def test_treevo_exhausts_budget_and_rotates_hierarchical_operators():
    frame = fixture()
    scores, history, summary = run(frame)
    assert scores.loc[frame.month.ge("2000-01-31")].notna().all()
    assert len(history) == 200
    assert history.evaluation.tolist() == list(range(1, 201))
    assert history.loc[history.generation.eq(0), "operator"].eq("initialization").sum() == 10
    assert history.operator.value_counts().to_dict() == {
        "crossover": 70,
        "mutation": 60,
        "pruning": 60,
        "initialization": 10,
    }
    assert history.selected_final.sum() == 1
    assert history.valid_candidate.any()
    assert history.loc[history.selected_final, "valid_candidate"].all()
    assert summary["evaluation_budget"] == 200
    assert summary["final_population_size"] == 10
    assert summary["selected_expression"]
    assert summary["selected_node_count"] >= 1


def test_treevo_is_deterministic_and_never_uses_common_period_outcomes():
    frame = fixture()
    scores, history, summary = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2000-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history, changed_summary = run(changed)
    pd.testing.assert_series_equal(scores, changed_scores)
    pd.testing.assert_frame_equal(history, changed_history)
    assert summary == changed_summary


def test_treevo_rejects_a_short_evaluation_budget():
    frame = fixture()
    try:
        treevo_evolution_scores(
            frame,
            SEEDS,
            common_start="2000-01-31",
            training_start="1990-01-31",
            training_end="1997-12-31",
            validation_start="1998-01-31",
            validation_end="1999-12-31",
            evaluation_budget=100,
        )
    except ValueError as error:
        assert "population or evaluation budget" in str(error)
    else:
        raise AssertionError("short TreEvo budget was accepted")
