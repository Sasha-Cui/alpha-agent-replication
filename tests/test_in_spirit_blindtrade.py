from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_evolve.in_spirit import blindtrade_graph_intent_scores


AGENTS = {
    "momentum": [("momentum", 1), ("trend", 1)],
    "news_event": [("news", 1), ("surprise", 1)],
    "mean_reversion": [("short_return", -1), ("extreme", -1)],
    "risk_regime": [("risk", -1), ("safety", 1)],
}

INTENTS = {
    "defensive": {"momentum": 0.1, "news_event": 0.2, "mean_reversion": 0.2, "risk_regime": 0.5},
    "neutral": {"momentum": 0.25, "news_event": 0.25, "mean_reversion": 0.25, "risk_regime": 0.25},
    "aggressive": {"momentum": 0.5, "news_event": 0.2, "mean_reversion": 0.2, "risk_regime": 0.1},
}


def fixture(months: int = 48, securities: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(167)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(dict.fromkeys(feature for specs in AGENTS.values() for feature, _ in specs))
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = (
        0.02 * frame["surprise"]
        + 0.015 * frame["safety"]
        - 0.01 * frame["risk"]
        + rng.normal(scale=0.08, size=len(frame))
    )
    return frame


def run(frame: pd.DataFrame):
    return blindtrade_graph_intent_scores(
        frame,
        AGENTS,
        INTENTS,
        common_start="2002-07-31",
        agent_ic_history_months=12,
        minimum_agent_ic_months=10,
        semantic_neighbors=5,
        intent_reward_history_months=12,
        minimum_intent_reward_months=10,
    )


def test_blindtrade_policy_is_graph_based_purged_inertial_and_finite():
    frame = fixture()
    scores, history = run(frame)
    common = frame.month.ge("2002-07-31")
    assert scores.loc[common].notna().all()
    assert history.agent_ic_history_months.eq(12).all()
    assert history.intent_reward_history_months.ge(10).all()
    assert (pd.to_datetime(history.agent_ic_history_end) < pd.to_datetime(history.formation_month)).all()
    assert (pd.to_datetime(history.intent_reward_history_end) < pd.to_datetime(history.formation_month)).all()
    assert set(history.selected_intent).issubset(INTENTS)
    reliability = history.filter(like="agent_reliability__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.mean_semantic_neighbors.between(0.0, 5.0).all()
    assert history.mean_absolute_inertial_score.le(1.0).all()
    assert history.finite_scores.eq(50).all()


def test_blindtrade_is_deterministic_and_ignores_current_future_rewards():
    frame = fixture()
    scores, history = run(frame)
    changed = frame.copy()
    changed.loc[changed.month.ge("2002-07-31"), "ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = run(changed)
    first = frame.month.eq(pd.Timestamp("2002-07-31"))
    np.testing.assert_allclose(scores.loc[first], changed_scores.loc[first])
    pd.testing.assert_series_equal(history.iloc[0], changed_history.iloc[0])
    repeat_scores, repeat_history = run(frame)
    pd.testing.assert_series_equal(scores, repeat_scores)
    pd.testing.assert_frame_equal(history, repeat_history)


def test_blindtrade_rejects_identity_or_policy_shape_changes():
    frame = fixture()
    bad_agents = dict(AGENTS)
    bad_agents["ticker_identity"] = [("momentum", 1)]
    for agents, eta in ((bad_agents, 0.1), (AGENTS, 0.0)):
        try:
            blindtrade_graph_intent_scores(
                frame,
                agents,
                INTENTS,
                common_start="2002-07-31",
                execution_inertia_eta=eta,
            )
        except ValueError as error:
            assert "four frozen agents" in str(error) or "inertia" in str(error)
        else:
            raise AssertionError("invalid BlindTrade policy was accepted")
