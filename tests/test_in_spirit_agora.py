from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.in_spirit import agora_alpha_library, agora_sealed_joint_search_scores


SEEDS = [
    "ret_1_0",
    "ret_3_1",
    "ret_6_1",
    "ret_12_1",
    "be_me",
    "gp_at",
    "ocf_at",
    "rvol_21d",
    "beta_60m",
    "turnover_126d",
]
PANEL = {"mean_rankic": 0.4, "rankicir": 0.25, "long_short_sharpe": 0.25, "evolved_metric": 0.1}


def fixture() -> pd.DataFrame:
    rng = np.random.default_rng(521)
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
        0.02 * frame.ret_12_1 + 0.01 * frame.gp_at - 0.008 * frame.rvol_21d + rng.normal(0.0, 0.08, len(frame))
    )
    frame.loc[frame.security_id.eq(0), SEEDS] = np.nan
    return frame


def run(frame: pd.DataFrame):
    return agora_sealed_joint_search_scores(
        frame,
        SEEDS,
        PANEL,
        {"monotonicity_score_v1": 5, "excess_drawdown_penalty_v1": 10},
        common_start="2000-01-31",
        training_months=60,
        outer_rounds=20,
        target_unique_alphas=18,
        final_top_alpha_count=5,
        minimum_promotion_observations=5,
        inner_tail_fraction=0.2,
        inner_minimum_side=5,
    )


def test_agora_builds_grammar_and_sealed_registry():
    frame = fixture()
    library, components = agora_alpha_library(frame, SEEDS)
    assert library.shape == (len(frame), 145)
    assert set(library) == set(components)
    scores, registry, rounds = run(frame)
    assert scores.loc[frame.month.ge("2000-01-31")].notna().all()
    assert len(registry) == 18 and registry.alpha.nunique() == 18
    assert registry.selected_top30.sum() == 5
    assert len(rounds) == 20 and rounds.registry_size.iloc[-1] == 18
    assert rounds.channel_b_brief_records.eq(2).all()
    assert rounds.channel_c_wiki_commit.all()
    proposals = rounds.loc[rounds.metric_proposal.ne("")]
    assert set(proposals.metric_proposal) == {"monotonicity_score_v1", "excess_drawdown_penalty_v1"}


def test_agora_is_deterministic_and_common_period_is_sealed():
    frame = fixture()
    result = run(frame)
    repeated = run(frame)
    pd.testing.assert_series_equal(result[0], repeated[0])
    pd.testing.assert_frame_equal(result[1], repeated[1])
    pd.testing.assert_frame_equal(result[2], repeated[2])
    changed = frame.copy()
    changed.loc[changed.month.ge("2000-01-31"), "ret_exc_lead1m"] *= -1
    other = run(changed)
    pd.testing.assert_series_equal(result[0], other[0])
    pd.testing.assert_frame_equal(result[1], other[1])
    pd.testing.assert_frame_equal(result[2], other[2])


def test_agora_rejects_invalid_top_pool():
    with pytest.raises(ValueError, match="top-alpha"):
        agora_sealed_joint_search_scores(
            fixture(),
            SEEDS,
            PANEL,
            {"monotonicity_score_v1": 5, "excess_drawdown_penalty_v1": 10},
            common_start="2000-01-31",
            training_months=60,
            outer_rounds=20,
            target_unique_alphas=18,
            final_top_alpha_count=19,
            inner_tail_fraction=0.2,
            inner_minimum_side=5,
        )
