from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.in_spirit import factormad_debate_scores, factormad_factor_library


SEEDS = [
    "ret_1_0",
    "ret_3_1",
    "ret_6_1",
    "ret_12_1",
    "be_me",
    "gp_at",
    "ocf_at",
    "z_score",
    "rvol_21d",
    "beta_60m",
    "turnover_126d",
    "niq_su",
]


def fixture() -> pd.DataFrame:
    rng = np.random.default_rng(593)
    months = pd.date_range("1995-01-31", periods=84, freq="ME")
    frame = pd.DataFrame(
        {
            "month": np.repeat(months, 25),
            "security_id": np.tile(np.arange(25), len(months)),
            "weight": rng.lognormal(size=25 * len(months)),
        }
    )
    for feature in SEEDS:
        frame[feature] = rng.normal(size=len(frame))
    frame["rvol_21d"] = frame["rvol_21d"].abs()
    frame["turnover_126d"] = frame["turnover_126d"].abs()
    frame["ret"] = rng.normal(0.004, 0.04, len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame.ret_12_1 + 0.012 * frame.gp_at - 0.008 * frame.rvol_21d + rng.normal(0.0, 0.08, len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return factormad_debate_scores(
        frame,
        SEEDS,
        common_start="2000-01-31",
        training_months=60,
        debate_rounds=3,
        predictive_metric_threshold=0.001,
        maximum_rankic_correlation=0.99,
        target_accepted_factors=20,
        maximum_debate_episodes=100,
    )


def test_factormad_builds_library_debates_and_linear_factor_model():
    frame = fixture()
    library, components = factormad_factor_library(frame, SEEDS)
    assert library.shape == (len(frame), 210)
    assert set(library) == set(components)
    scores, registry, debate = run(frame)
    assert scores.loc[frame.month.ge("2000-01-31")].notna().all()
    assert len(registry) == 20 and registry.factor.nunique() == 20
    assert registry.maximum_prior_rankic_correlation.le(0.99).all()
    assert np.abs(registry.linear_model_weight).sum() == pytest.approx(1.0)
    assert {"agent_a_quality", "agent_b_diversity", "validator_corrector"}.issubset(debate.proposer)
    assert debate.groupby("episode").size().ge(4).all()


def test_factormad_is_deterministic_and_common_returns_are_sealed():
    frame = fixture()
    first = run(frame)
    repeated = run(frame)
    pd.testing.assert_series_equal(first[0], repeated[0])
    pd.testing.assert_frame_equal(first[1], repeated[1])
    pd.testing.assert_frame_equal(first[2], repeated[2])
    changed = frame.copy()
    changed.loc[changed.month.ge("2000-01-31"), "ret_exc_lead1m"] *= -1
    second = run(changed)
    pd.testing.assert_series_equal(first[0], second[0])
    pd.testing.assert_frame_equal(first[1], second[1])
    pd.testing.assert_frame_equal(first[2], second[2])


def test_factormad_rejects_impossible_factor_target():
    with pytest.raises(ValueError, match="accepted-factor target"):
        factormad_debate_scores(
            fixture(),
            SEEDS,
            common_start="2000-01-31",
            training_months=60,
            target_accepted_factors=211,
        )
