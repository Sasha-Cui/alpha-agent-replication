from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import mm_arc_routing_scores


EXPERTS = {
    "trend": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("prc_highprc_252d", 1), ("turnover_126d", 1), ("rvol_21d", -1)],
    "reversal": [("ret_1_0", -1), ("ret_6_1", -1), ("prc_highprc_252d", -1), ("turnover_126d", -1), ("rvol_21d", -1), ("beta_60m", -1)],
    "breakout": [("prc_highprc_252d", 1), ("ret_1_0", 1), ("ret_6_1", 1), ("turnover_126d", 1), ("rvol_21d", 1), ("beta_60m", 1)],
    "exposure_control": [("rvol_21d", -1), ("beta_60m", -1), ("z_score", 1), ("qmj_safety", 1), ("qmj_prof", 1), ("f_score", 1)],
}
VIEWS = {"numerical_pool": 0.5, "chart_proxy": 0.25, "technical_summary_proxy": 0.25}
RABO = {"benchmark_exceedance": 0.3, "lower_tail_5pct": 0.3, "median": 0.15, "stability": 0.15, "turnover_penalty": -0.1}


def fixture(months: int = 128, securities: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(113)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(
        dict.fromkeys(feature for specifications in EXPERTS.values() for feature, _ in specifications)
    )
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.025 * frame.ret_12_1
        + 0.015 * frame.qmj_prof
        - 0.01 * frame.rvol_21d
        + rng.normal(scale=0.1, size=len(frame))
    )
    frame["ret"] = rng.normal(loc=0.005, scale=0.04, size=len(frame))
    frame["weight"] = rng.lognormal(size=len(frame))
    return frame


def run(frame: pd.DataFrame):
    return mm_arc_routing_scores(
        frame,
        EXPERTS,
        view_weights=VIEWS,
        rabo_rank_weights=RABO,
        common_start="2010-01-31",
    )


def test_mm_arc_runs_twelve_pools_admits_twenty_members_and_routes_simplex_capital():
    frame = fixture()
    scores, history = run(frame)
    common = frame.month.ge("2010-01-31")
    assert scores.loc[common].notna().all()
    assert history.single_market_pool_count.eq(12).all()
    assert history.admitted_pool_members.eq(20).all()
    assert history.audit_history_months.eq(120).all()
    assert history.regime_audit_months.ge(12).all()
    weights = history.filter(like="router_weight__")
    np.testing.assert_allclose(weights.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert weights.ge(0).all().all()
    assert history.finite_scores.eq(40).all()
    for expert in EXPERTS:
        assert history[f"selected__{expert}"].str.count("\\|").eq(4).all()


def test_mm_arc_is_deterministic_and_ignores_current_and_future_outcomes():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2010-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first = frame.month.eq(pd.Timestamp("2010-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = run(frame)
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_mm_arc_rejects_missing_expert():
    frame = fixture()
    invalid = dict(EXPERTS)
    invalid.pop("exposure_control")
    try:
        mm_arc_routing_scores(
            frame,
            invalid,
            view_weights=VIEWS,
            rabo_rank_weights=RABO,
            common_start="2010-01-31",
        )
    except ValueError as error:
        assert "four frozen experts" in str(error)
    else:
        raise AssertionError("incomplete MM-ARC expert set was accepted")
