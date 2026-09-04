from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import rd_agent_search_scores


BRANCHES = {
    "momentum_trend": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1)],
    "valuation": [("be_me", 1), ("at_me", 1), ("prc_highprc_252d", 1)],
    "profitability_quality": [("gp_at", 1), ("ocf_at", 1), ("f_score", 1)],
    "financial_safety": [("z_score", 1), ("qmj_safety", 1), ("qmj_prof", 1)],
    "fundamental_surprise": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1)],
    "low_risk": [("rvol_21d", -1), ("beta_60m", -1), ("turnover_126d", -1)],
}


def fixture(months: int = 132, securities: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(89)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(dict.fromkeys(feature for branch in BRANCHES.values() for feature, _ in branch))
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.025 * frame.gp_at
        + 0.015 * frame.ret_12_1
        - 0.01 * frame.rvol_21d
        + rng.normal(scale=0.1, size=len(frame))
    )
    return frame


def test_rd_agent_runs_parallel_branches_and_aggregated_finalists():
    frame = fixture()
    scores, history = rd_agent_search_scores(frame, BRANCHES, common_start="2010-01-31")
    common = frame.month.ge("2010-01-31")
    assert scores.loc[common].notna().all()
    assert history.explored_candidate_count.eq(24).all()
    assert history.branch_winner_count.eq(6).all()
    assert history.finalist_count.eq(8).all()
    assert history.selected_solution_size.isin([1, 3, 6]).all()
    assert history.finite_scores.eq(80).all()
    assert history.research_months.eq(96).all()
    assert history.validation_months.eq(24).all()


def test_rd_agent_is_deterministic_and_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = rd_agent_search_scores(frame, BRANCHES, common_start="2010-01-31")
    changed = frame.copy()
    changed.loc[changed.month.ge("2010-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = rd_agent_search_scores(
        changed,
        BRANCHES,
        common_start="2010-01-31",
    )
    first = frame.month.eq(pd.Timestamp("2010-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = rd_agent_search_scores(
        frame,
        BRANCHES,
        common_start="2010-01-31",
    )
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_rd_agent_rejects_an_incomplete_branch_graph():
    frame = fixture()
    invalid = dict(BRANCHES)
    invalid.pop("low_risk")
    try:
        rd_agent_search_scores(frame, invalid, common_start="2010-01-31")
    except ValueError as error:
        assert "six branches" in str(error)
    else:
        raise AssertionError("incomplete R&D-Agent branch graph was accepted")
