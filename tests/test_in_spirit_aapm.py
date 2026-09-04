from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import aapm_rolling_scores


REPORT = ["ret_1_0", "ret_6_1", "turnover_126d", "rmax5_21d", "gp_at"]
MANUAL = ["be_me", "f_score", "o_score", "beta_60m", "rvol_21d", "ocf_at"]
ASSET = ["market_equity", "be_me", "gp_at"]


def fixture(months: int = 130, securities: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(53)
    dates = np.repeat(pd.date_range("1990-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids, "weight": rng.lognormal(size=len(ids))})
    for feature in sorted(set([*REPORT, *MANUAL, *ASSET])):
        frame[feature] = rng.normal(size=len(frame))
    frame["ret"] = rng.normal(scale=0.05, size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.gp_at + 0.01 * frame.ret_6_1 + rng.normal(scale=0.1, size=len(frame))
    return frame


def run(frame: pd.DataFrame):
    return aapm_rolling_scores(
        frame,
        REPORT,
        MANUAL,
        ASSET,
        common_start="2000-01-31",
    )


def test_aapm_builds_hybrid_report_manual_asset_and_interaction_state():
    frame = fixture()
    scores, history, catalog = run(frame)
    assert len(catalog) == 23
    assert catalog.feature.str.startswith("report__").sum() == 5
    assert catalog.feature.str.startswith("manual__").sum() == 6
    assert catalog.feature.str.startswith("asset__").sum() == 3
    assert catalog.feature.str.startswith("interaction__").sum() == 6
    assert history.hybrid_feature_count.eq(23).all()
    assert history.finite_scores.eq(20).all()
    assert scores.loc[frame.month.ge("2000-01-31")].notna().all()


def test_aapm_prediction_uses_only_prior_pretraining_outcomes():
    frame = fixture()
    scores, history, _ = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2000-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history, _ = run(changed)
    first = frame.month.eq(pd.Timestamp("2000-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    assert history.pretraining_end.iloc[0] == "1999-12-31"
    assert history.pretraining_months.eq(120).all()


def test_aapm_rejects_wrong_hybrid_block_dimensions():
    frame = fixture()
    try:
        aapm_rolling_scores(frame, REPORT[:4], MANUAL, ASSET, common_start="2000-01-31")
    except ValueError as error:
        assert "5/6/3" in str(error)
    else:
        raise AssertionError("invalid AAPM block dimensions were accepted")
