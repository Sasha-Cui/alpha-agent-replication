from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import mass_simulation_scores


FEATURES = [
    "ret_12_1", "ret_6_1", "ret_1_0", "be_me", "gp_at", "ocf_at", "f_score", "z_score",
    "qmj_safety", "qmj_prof", "rvol_21d", "beta_60m", "turnover_126d", "prc_highprc_252d", "niq_su", "saleq_su",
]


def fixture(months: int = 70, securities: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(73)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    for feature in FEATURES:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.gp_at + 0.01 * frame.ret_12_1 + rng.normal(scale=0.1, size=len(frame))
    return frame


def test_mass_runs_512_agents_with_twenty_candidate_and_five_selection_rules():
    frame = fixture()
    scores, history = mass_simulation_scores(frame, FEATURES, common_start="2005-01-31")
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()
    assert history.finite_scores.eq(50).all()
    assert history.total_agent_selections.eq(16 * 32 * 5).all()
    assert history.annealing_iterations.eq(100).all()
    weights = history.filter(like="type_weight__")
    np.testing.assert_allclose(weights.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert weights.ge(0).all().all()


def test_mass_simulation_is_deterministic_and_ignores_future_outcomes():
    frame = fixture()
    scores, history = mass_simulation_scores(frame, FEATURES, common_start="2005-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = mass_simulation_scores(changed, FEATURES, common_start="2005-01-31")
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = mass_simulation_scores(frame, FEATURES, common_start="2005-01-31")
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_mass_rejects_wrong_population_size():
    frame = fixture()
    try:
        mass_simulation_scores(frame, FEATURES[:15], common_start="2005-01-31")
    except ValueError as error:
        assert "16 unique" in str(error)
    else:
        raise AssertionError("invalid MASS population was accepted")
