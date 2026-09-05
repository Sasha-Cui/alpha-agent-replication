from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import contesttrade_dual_contest_scores


DATA_AGENTS = [
    ("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("be_me", 1),
    ("at_me", 1), ("gp_at", 1), ("ocf_at", 1), ("f_score", 1),
    ("z_score", 1), ("qmj_safety", 1), ("qmj_prof", 1), ("niq_su", 1),
    ("saleq_su", 1), ("turnover_126d", 1), ("rvol_21d", -1), ("beta_60m", -1),
]
RESEARCH_AGENTS = {
    "momentum": {"features": [{"column": "ret_12_1", "sign": 1}, {"column": "ret_6_1", "sign": 1}, {"column": "ret_1_0", "sign": 1}], "judge_score_1_to_5": 4.0},
    "reversal": {"features": [{"column": "ret_1_0", "sign": -1}, {"column": "ret_6_1", "sign": -1}, {"column": "prc_highprc_252d", "sign": -1}], "judge_score_1_to_5": 3.5},
    "fundamentals": {"features": [{"column": "be_me", "sign": 1}, {"column": "gp_at", "sign": 1}, {"column": "ocf_at", "sign": 1}, {"column": "f_score", "sign": 1}], "judge_score_1_to_5": 4.5},
    "event_driven": {"features": [{"column": "niq_su", "sign": 1}, {"column": "saleq_su", "sign": 1}, {"column": "turnover_126d", "sign": 1}], "judge_score_1_to_5": 4.0},
    "risk_control": {"features": [{"column": "z_score", "sign": 1}, {"column": "qmj_safety", "sign": 1}, {"column": "qmj_prof", "sign": 1}, {"column": "rvol_21d", "sign": -1}, {"column": "beta_60m", "sign": -1}], "judge_score_1_to_5": 5.0},
}


def fixture(months: int = 55, securities: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(101)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(
        dict.fromkeys(
            [name for name, _ in DATA_AGENTS]
            + [str(item["column"]) for spec in RESEARCH_AGENTS.values() for item in spec["features"]]
        )
    )
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.025 * frame.gp_at
        + 0.015 * frame.ret_12_1
        - 0.01 * frame.rvol_21d
        + rng.normal(scale=0.1, size=len(frame))
    )
    return frame


def test_contesttrade_runs_both_contests_and_normalizes_research_weights():
    frame = fixture()
    scores, history = contesttrade_dual_contest_scores(
        frame,
        DATA_AGENTS,
        RESEARCH_AGENTS,
        common_start="2004-01-31",
    )
    common = frame.month.ge("2004-01-31")
    assert scores.loc[common].notna().all()
    assert history.data_candidate_count.eq(16).all()
    assert history.data_selected_count.between(1, 8).all()
    assert history.research_agent_count.eq(5).all()
    assert history.data_history_months.eq(24).all()
    assert history.research_history_months.eq(24).all()
    allocations = history.filter(like="allocation__")
    np.testing.assert_allclose(allocations.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert allocations.ge(0).all().all()
    assert history.finite_scores.eq(50).all()


def test_contesttrade_is_deterministic_and_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = contesttrade_dual_contest_scores(
        frame,
        DATA_AGENTS,
        RESEARCH_AGENTS,
        common_start="2004-01-31",
    )
    changed = frame.copy()
    changed.loc[changed.month.ge("2004-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = contesttrade_dual_contest_scores(
        changed,
        DATA_AGENTS,
        RESEARCH_AGENTS,
        common_start="2004-01-31",
    )
    first = frame.month.eq(pd.Timestamp("2004-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = contesttrade_dual_contest_scores(
        frame,
        DATA_AGENTS,
        RESEARCH_AGENTS,
        common_start="2004-01-31",
    )
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_contesttrade_rejects_incomplete_data_team():
    frame = fixture()
    try:
        contesttrade_dual_contest_scores(
            frame,
            DATA_AGENTS[:-1],
            RESEARCH_AGENTS,
            common_start="2004-01-31",
        )
    except ValueError as error:
        assert "sixteen unique" in str(error)
    else:
        raise AssertionError("incomplete ContestTrade Data Team was accepted")
