from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import trusttrade_selective_consensus_scores


REPORTS = {
    "fundamentals": {"a": [("value", 1), ("quality", 1)], "b": [("quality", 1), ("safety", 1)], "c": [("value", 1), ("safety", 1)]},
    "market": {"a": [("momentum", 1), ("trend", 1)], "b": [("trend", 1), ("volume", 1)], "c": [("momentum", 1), ("volume", 1)]},
    "news": {"a": [("news", 1), ("quality", 1)], "b": [("news", 1), ("value", 1)], "c": [("news", 1), ("momentum", 1)]},
    "sentiment": {"a": [("ret_1_0", -1), ("risk", -1)], "b": [("risk", -1), ("safety", 1)], "c": [("ret_1_0", -1), ("safety", 1)]},
}
RISK = [("risk", 1), ("rvol_21d", 1), ("safety", -1)]


def fixture(months: int = 84, securities: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(179)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = {feature for domain in REPORTS.values() for specs in domain.values() for feature, _ in specs} | {feature for feature, _ in RISK}
    features |= {"ret_3_1", "ret_6_1", "ret_12_1", "prc_highprc_252d"}
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = 0.02 * frame.quality + 0.015 * frame.momentum - 0.01 * frame.risk + rng.normal(scale=0.08, size=len(frame))
    return frame


def run(frame: pd.DataFrame):
    return trusttrade_selective_consensus_scores(
        frame,
        REPORTS,
        RISK,
        common_start="2005-01-31",
        temporal_horizons_months=[1, 3, 6, 12],
        reflection_reward_horizons_months=[1, 3, 6, 12],
        reflection_reward_weights=[0.25] * 4,
        long_reflection_history_months=24,
        minimum_long_reflection_months=20,
        short_reflection_history_months=6,
    )


def test_trusttrade_selects_consensus_and_uses_purged_reflection():
    frame = fixture()
    scores, history = run(frame)
    common = frame.month.ge("2005-01-31")
    assert scores.loc[common].notna().all()
    assert history.long_reflection_months.eq(24).all()
    assert history.short_reflection_months.eq(6).all()
    assert (pd.to_datetime(history.long_reflection_end) <= pd.to_datetime(history.reflection_cutoff)).all()
    assert (pd.to_datetime(history.reflection_cutoff) < pd.to_datetime(history.formation_month)).all()
    assert (history.buy_count + history.hold_count + history.sell_count).eq(40).all()
    reliability = history.filter(like="reliability__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.filter(like="mean_consensus__").apply(lambda column: column.between(0.0, 1.0)).all().all()
    assert history.mean_risk_cap.between(0.25, 0.75).all()
    assert history.finite_scores.eq(40).all()


def test_trusttrade_is_deterministic_and_ignores_current_future_rewards():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2005-01-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first = frame.month.eq(pd.Timestamp("2005-01-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = run(frame)
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_trusttrade_rejects_short_purge_or_missing_domain():
    frame = fixture()
    bad_reports = dict(REPORTS)
    bad_reports.pop("sentiment")
    for reports, purge in ((bad_reports, 12), (REPORTS, 6)):
        try:
            trusttrade_selective_consensus_scores(
                frame,
                reports,
                RISK,
                common_start="2005-01-31",
                temporal_horizons_months=[1, 3, 6, 12],
                reflection_reward_horizons_months=[1, 3, 6, 12],
                reflection_reward_weights=[0.25] * 4,
                reflection_reward_purge_months=purge,
            )
        except ValueError as error:
            assert "four frozen domains" in str(error) or "purge" in str(error)
        else:
            raise AssertionError("invalid TrustTrade policy was accepted")
