from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.in_spirit import sharp_evolved_rubric_scores


ANALYST_STATE = {
    "price": [
        {"column": "ret_12_1", "sign": 1},
        {"column": "ret_6_1", "sign": 1},
        {"column": "ret_1_0", "sign": -1},
    ],
    "catalyst": [{"column": "niq_su", "sign": 1}, {"column": "saleq_su", "sign": 1}],
    "quality": [{"column": "gp_at", "sign": 1}, {"column": "ocf_at", "sign": 1}],
    "attention": [{"column": "turnover_126d", "sign": 1}],
    "fear_proxy_column": "rvol_21d",
    "base_expected_return_weights": {"price": 0.5, "catalyst": 0.3, "quality": 0.2},
}
RULES = [
    {"id": "temporal_priced_in", "initial": 0.3, "minimum": 0.1, "maximum": 1.5, "step": 0.1},
    {"id": "temporal_earnings_season", "initial": 0.5, "minimum": 0.1, "maximum": 1.5, "step": 0.1},
    {"id": "news_analyst_rating", "initial": 1.3, "minimum": 0.5, "maximum": 2.0, "step": 0.1},
    {"id": "news_generic_market", "initial": 0.4, "minimum": 0.1, "maximum": 1.5, "step": 0.1},
    {"id": "macro_high_vix", "initial": 0.7, "minimum": 0.1, "maximum": 1.5, "step": 0.1},
    {"id": "news_count_low", "initial": 0.4, "minimum": 0.2, "maximum": 0.8, "step": 0.1},
]
THRESHOLDS = {
    "extreme_move_absolute_rank": 0.6,
    "minimum_catalyst_absolute_rank": 0.2,
    "high_attention_rank": 0.5,
    "weak_catalyst_absolute_rank": 0.2,
    "strong_catalyst_absolute_rank": 0.5,
    "weak_idiosyncratic_catalyst_absolute_rank": 0.25,
    "low_attention_rank": -0.5,
    "fear_history_months": 60,
    "fear_quantile": 0.8,
}


def fixture() -> pd.DataFrame:
    rng = np.random.default_rng(337)
    months = pd.date_range("1990-01-31", periods=150, freq="ME")
    frame = pd.DataFrame(
        {
            "month": np.repeat(months, 30),
            "security_id": np.tile(np.arange(30), len(months)),
            "weight": rng.lognormal(size=30 * len(months)),
        }
    )
    for feature in (
        "ret_12_1",
        "ret_6_1",
        "ret_1_0",
        "niq_su",
        "saleq_su",
        "gp_at",
        "ocf_at",
        "turnover_126d",
        "rvol_21d",
    ):
        frame[feature] = rng.normal(size=len(frame))
    frame["rvol_21d"] = frame["rvol_21d"].abs()
    frame["ret"] = rng.normal(0.005, 0.04, len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame["ret_12_1"] + 0.01 * frame["niq_su"] - 0.01 * frame["ret_1_0"] + rng.normal(0.0, 0.08, len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return sharp_evolved_rubric_scores(
        frame,
        ANALYST_STATE,
        RULES,
        THRESHOLDS,
        common_start="2000-01-31",
        inner_tail_fraction=0.2,
        inner_minimum_side=5,
    )


def test_sharp_evolves_bounded_rubrics_and_freezes_test_blocks():
    frame = fixture()
    scores, blocks, evolution = run(frame)
    common = frame.month.ge("2000-01-31")
    assert scores.loc[common].notna().all()
    assert len(blocks) == 2 and blocks.test_months.tolist() == [24, 6]
    assert blocks.rule_count.eq(6).all()
    assert blocks.minimum_finite_scores.eq(30).all()
    assert len(evolution) == 10
    assert evolution.proposed_mutation_count.between(0, 3).all()
    assert set(evolution.accepted).issubset({True, False})


def test_sharp_is_deterministic_and_does_not_use_test_returns_for_first_block():
    frame = fixture()
    scores, blocks, evolution = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2000-01-31"), "ret_exc_lead1m"] *= -1
    other_scores, other_blocks, other_evolution = run(changed)
    first_test = frame.month.between("2000-01-31", "2001-12-31")
    np.testing.assert_allclose(scores.loc[first_test], other_scores.loc[first_test], rtol=0, atol=0)
    pd.testing.assert_series_equal(blocks.iloc[0], other_blocks.iloc[0])
    pd.testing.assert_frame_equal(evolution.iloc[:5], other_evolution.iloc[:5])


def test_sharp_rejects_relaxed_mutation_bound():
    with pytest.raises(ValueError, match="mutation bound"):
        sharp_evolved_rubric_scores(
            fixture(),
            ANALYST_STATE,
            RULES,
            THRESHOLDS,
            common_start="2000-01-31",
            maximum_atomic_mutations_per_round=4,
            inner_tail_fraction=0.2,
            inner_minimum_side=5,
        )
