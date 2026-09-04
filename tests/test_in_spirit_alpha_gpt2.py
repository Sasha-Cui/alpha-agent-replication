from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import alpha_gpt2_rolling_scores


SEEDS = ["ret_1_0", "ret_3_1", "ret_6_1", "ret_12_1", "prc_highprc_252d", "resff3_6_1"]
RISKS = ["rvol_21d", "o_score", "z_score"]


def fixture(months: int = 70, securities: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(37)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    for name in [*SEEDS, *RISKS]:
        frame[name] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = -0.02 * frame.ret_1_0 - 0.01 * frame.ret_3_1 + rng.normal(scale=0.15, size=len(frame))
    return frame


def run(frame: pd.DataFrame):
    return alpha_gpt2_rolling_scores(
        frame,
        SEEDS,
        RISKS,
        common_start="2005-01-31",
    )


def test_alpha_gpt2_executes_all_three_stages_with_fixed_cardinalities():
    frame = fixture()
    scores, history, catalog = run(frame)
    assert len(catalog) == 51
    assert catalog.seed_orientation.eq("negative_mean_reversion").all()
    assert history.eligible_candidates.eq(51).all()
    assert history.selected_factors.eq(5).all()
    assert history.finite_scores.eq(30).all()
    assert history.high_risk_count.between(6, 7).all()
    assert scores.loc[frame.month.ge("2005-01-31")].notna().all()


def test_alpha_gpt2_selection_and_model_ignore_current_and_future_returns():
    frame = fixture()
    scores, history, _ = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history, _ = run(changed)
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    assert history.training_end.iloc[0] == "2004-12-31"
    assert history.training_months.eq(60).all()


def test_alpha_gpt2_rejects_non_frozen_seed_cardinality():
    frame = fixture()
    try:
        alpha_gpt2_rolling_scores(frame, SEEDS[:5], RISKS, common_start="2005-01-31")
    except ValueError as error:
        assert "six unique" in str(error)
    else:
        raise AssertionError("invalid seed cardinality was accepted")
