from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.in_spirit import madevolve_candidate_library, madevolve_joint_search_scores


FEATURE_SEEDS = {
    "momentum": ["ret_1_0", "ret_3_1", "ret_6_1", "ret_12_1", "prc_highprc_252d"],
    "reversal_risk": ["rvol_21d", "rmax5_21d"],
    "liquidity": ["turnover_126d"],
    "value_quality": ["be_me", "gp_at", "ocf_at", "z_score"],
    "catalyst": ["niq_su", "saleq_su"],
}
INTERACTIONS = [
    ["ret_12_1", "rvol_21d"],
    ["ret_6_1", "turnover_126d"],
    ["ret_1_0", "niq_su"],
    ["gp_at", "ocf_at"],
    ["be_me", "z_score"],
    ["ret_12_1", "gp_at"],
    ["rvol_21d", "turnover_126d"],
    ["niq_su", "saleq_su"],
]
WRAPPERS = [
    "identity",
    "risk_dampen",
    "quality_confirm",
    "momentum_confirm",
    "defensive_regime_switch",
]
BASELINE = {
    "terms": ["identity__ret_1_0", "identity__ret_6_1", "identity__ret_12_1"],
    "wrapper": "identity",
}


def fixture() -> pd.DataFrame:
    rng = np.random.default_rng(419)
    months = pd.date_range("1990-01-31", periods=102, freq="ME")
    frame = pd.DataFrame(
        {
            "month": np.repeat(months, 25),
            "security_id": np.tile(np.arange(25), len(months)),
            "weight": rng.lognormal(size=25 * len(months)),
        }
    )
    for feature in [name for values in FEATURE_SEEDS.values() for name in values]:
        frame[feature] = rng.normal(size=len(frame))
    frame["rvol_21d"] = frame["rvol_21d"].abs()
    frame["ret"] = rng.normal(0.004, 0.04, len(frame))
    frame["ret_exc_lead1m"] = (
        0.018 * frame.ret_12_1 + 0.012 * frame.gp_at - 0.01 * frame.rvol_21d + rng.normal(0.0, 0.08, len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return madevolve_joint_search_scores(
        frame,
        FEATURE_SEEDS,
        INTERACTIONS,
        WRAPPERS,
        BASELINE,
        common_start="1996-07-31",
        generations=5,
        offspring_per_island_per_generation=1,
        inner_tail_fraction=0.2,
        inner_minimum_side=5,
    )


def test_madevolve_library_and_five_island_search_are_complete():
    frame = fixture()
    library, families = madevolve_candidate_library(frame, FEATURE_SEEDS, INTERACTIONS)
    assert library.shape == (len(frame), 40)
    assert set(library) == set(families)
    scores, blocks, generations = run(frame)
    common = frame.month.ge("1996-07-31")
    assert scores.loc[common].notna().all()
    assert len(blocks) == 1 and blocks.iloc[0].proposal_count == 25
    assert blocks.iloc[0].test_months == 24
    assert 2 <= blocks.iloc[0].term_count <= 5
    assert blocks.iloc[0].minimum_finite_scores == 25
    assert len(generations) == 5
    assert (generations.patch_proposals + generations.rewrite_proposals).eq(5).all()
    assert generations.iloc[-1].migrants == 5


def test_madevolve_is_deterministic_and_does_not_select_on_test_returns():
    frame = fixture()
    scores, blocks, generations = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("1996-07-31"), "ret_exc_lead1m"] *= -1
    other_scores, other_blocks, other_generations = run(changed)
    np.testing.assert_allclose(scores, other_scores, rtol=0, atol=0, equal_nan=True)
    pd.testing.assert_frame_equal(blocks, other_blocks)
    pd.testing.assert_frame_equal(generations, other_generations)


def test_madevolve_rejects_wrong_island_count():
    with pytest.raises(ValueError, match="five islands"):
        madevolve_joint_search_scores(
            fixture(),
            FEATURE_SEEDS,
            INTERACTIONS,
            WRAPPERS,
            BASELINE,
            common_start="1996-07-31",
            islands=4,
            generations=1,
            offspring_per_island_per_generation=1,
            inner_tail_fraction=0.2,
            inner_minimum_side=5,
        )
