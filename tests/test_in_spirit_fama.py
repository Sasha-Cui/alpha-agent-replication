from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import (
    cross_sectional_unit_rank,
    fama_candidate_library,
    fama_rolling_scores,
    monthly_rankic,
)


SEEDS = ["a", "b", "c", "d", "e", "f"]


def fixture(months: int = 70, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(17)
    month = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    security = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": month, "security_id": security})
    for number, seed in enumerate(SEEDS):
        frame[seed] = rng.normal(size=len(frame)) + number * frame.security_id / securities
    frame["ret_exc_lead1m"] = 0.02 * frame["a"] - 0.01 * frame["b"] + rng.normal(scale=0.2, size=len(frame))
    return frame


def test_unit_rank_preserves_missingness_and_cross_sectional_endpoints():
    frame = pd.DataFrame(
        {"month": ["2020-01-31"] * 4, "x": [3.0, 1.0, np.nan, 2.0]}
    )
    ranked = cross_sectional_unit_rank(frame, ["x"])["x"]
    np.testing.assert_allclose(ranked.iloc[[0, 1, 3]], [1.0, -1.0, 0.0])
    assert np.isnan(ranked.iloc[2])


def test_fama_candidate_library_has_the_frozen_51_expression_grammar():
    frame = fixture(months=2)
    candidates = fama_candidate_library(frame, SEEDS)
    assert candidates.shape == (len(frame), 51)
    assert candidates.columns[:6].tolist() == [f"identity__{seed}" for seed in SEEDS]
    assert sum(name.startswith("mean__") for name in candidates) == 15
    assert sum(name.startswith("difference__") for name in candidates) == 15
    assert sum(name.startswith("product__") for name in candidates) == 15
    assert np.nanmax(np.abs(candidates.to_numpy())) <= 1.0


def test_monthly_rankic_and_selection_do_not_use_current_or_future_returns():
    frame = fixture()
    candidates = fama_candidate_library(frame, SEEDS)
    rankics = monthly_rankic(frame, candidates)
    scores, diagnostics = fama_rolling_scores(
        frame,
        candidates,
        rankics,
        common_start="2005-01-31",
    )
    changed = rankics.copy()
    changed.loc[changed.index >= "2005-01-31"] = -changed.loc[changed.index >= "2005-01-31"] * 1000
    changed_scores, changed_diagnostics = fama_rolling_scores(
        frame,
        candidates,
        changed,
        common_start="2005-01-31",
    )
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(diagnostics.iloc[0], changed_diagnostics.iloc[0])
    assert diagnostics.training_end.iloc[0] == "2004-12-31"
    assert diagnostics.training_months.eq(60).all()
    assert diagnostics.cluster_count.eq(7).all()


def test_selection_produces_finite_current_scores_and_two_distinct_representatives():
    frame = fixture()
    candidates = fama_candidate_library(frame, SEEDS)
    scores, diagnostics = fama_rolling_scores(
        frame,
        candidates,
        monthly_rankic(frame, candidates),
        common_start="2005-01-31",
    )
    common = frame.month.ge(pd.Timestamp("2005-01-31"))
    assert scores.loc[common].notna().all()
    assert diagnostics.selected_1.ne(diagnostics.selected_2).all()
    assert diagnostics.eligible_candidates.ge(7).all()
