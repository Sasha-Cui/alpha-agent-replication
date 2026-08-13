from __future__ import annotations

import math

import pytest

from alpha_evolve.metaps_paper_components import (
    NewsEvent,
    UnderspecifiedPaperMechanic,
    displayed_return,
    implied_initial_value,
    liquidity_rebate,
    momentum_follow,
    news_impulse,
    ranking_score,
    risk_reset,
    size_bucket_rule,
    v1_target,
    v2_blended_score,
    v3_balance_score,
    volatility_breakout_literal,
)


def test_news_impulse_preserves_threshold_direction_and_confidence() -> None:
    assert news_impulse([]).action == "HOLD"
    assert news_impulse([NewsEvent({"AAPL": 0.0019})]).action == "HOLD"
    decision = news_impulse([NewsEvent({"AAPL": -0.01, "NVDA": 0.005})])
    assert decision.action == "SELL AAPL"
    assert decision.size_mode == "probe_to_medium"
    assert decision.confidence == pytest.approx(0.3)


def test_momentum_follow_uses_printed_three_interval_threshold() -> None:
    decision = momentum_follow({"AAPL": [100, 100, 100, 101], "NVDA": [10, 10, 10, 9.9]})
    assert decision.action == "BUY AAPL"
    assert decision.confidence == pytest.approx(0.2)
    assert momentum_follow({"AAPL": [100, 100, 100, 100.1]}).action == "HOLD"


def test_risk_reset_reproduces_printed_score_and_exposes_action_mismatch() -> None:
    assert risk_reset(
        cash=1_000_000,
        gross_exposure=0,
        volatility_regime=0.2,
        liquidity_regime=0.2,
    ).action == "HOLD"
    decision = risk_reset(
        cash=0,
        gross_exposure=1_000_000,
        volatility_regime=1.0,
        liquidity_regime=1.0,
    )
    assert decision.action == "REDUCE"
    assert decision.size_mode == "reduce"
    assert decision.confidence == pytest.approx(0.42)


def test_liquidity_rebate_preserves_catalyst_guard_and_tight_spread_branch() -> None:
    prices = {"AAPL": [100, 100, 100, 100, 99.5]}
    assert liquidity_rebate(
        price_history=prices,
        liquidity_regime=0.8,
        volatility_regime=0.2,
        has_news=True,
    ).action == "HOLD"
    decision = liquidity_rebate(
        price_history=prices,
        liquidity_regime=0.8,
        volatility_regime=0.2,
        has_news=False,
    )
    assert decision.action == "BUY AAPL"
    assert decision.confidence == 0.47


def test_literal_volatility_breakout_can_never_emit_a_trade() -> None:
    compressed_with_last_at_high = [100.0] * 19 + [100.1]
    compressed_with_last_at_low = [100.1] * 19 + [100.0]
    assert volatility_breakout_literal({"HIGH": compressed_with_last_at_high}).action == "HOLD"
    assert volatility_breakout_literal({"LOW": compressed_with_last_at_low}).action == "HOLD"


def test_only_the_four_printed_runtime_buckets_have_a_quantity_rule() -> None:
    assert size_bucket_rule("none") == (0.0, 0)
    assert size_bucket_rule("small") == (0.04, 320)
    assert size_bucket_rule("medium") == (0.09, 800)
    assert size_bucket_rule("large") == (0.16, 1200)
    for raw_mode in ("probe_to_medium", "scalable", "reduce", "liquidity", "breakout"):
        with pytest.raises(UnderspecifiedPaperMechanic):
            size_bucket_rule(raw_mode)


def test_ranking_and_training_view_equations_execute_for_supplied_inputs() -> None:
    assert ranking_score(
        trigger_overlap=2,
        text_match=0.5,
        prior=0.1,
        missing_evidence_penalty=0.2,
        alpha=0.3,
        beta=0.4,
    ) == pytest.approx(0.7)
    assert v1_target({"momentum": 0.1, "risk": 0.05}) == "momentum"
    with pytest.raises(UnderspecifiedPaperMechanic):
        v1_target({"momentum": 0.1, "risk": 0.1})
    v2 = v2_blended_score(
        horizon_gains={3: 1.0, 5: 2.0, 10: 3.0, 20: 4.0},
        horizon_weights={3: 0.1, 5: 0.2, 10: 0.3, 20: 0.4},
        transaction_cost_proxy=0.1,
        risk_penalty=0.2,
        turnover_penalty=0.3,
        utility_prior=1.5,
        candidate_edge=0.4,
        eta=0.2,
        kappa=0.5,
    )
    assert v2 == pytest.approx(2.42)
    assert v3_balance_score(
        active_action_bonus=0.1,
        v2_score=v2,
        sample_weight=2.0,
        action_delta=-0.2,
        bucket_delta=0.05,
        strategy_delta=0.1,
    ) == pytest.approx(7.438)


def test_stock_and_sandbox_return_identities_have_different_disclosed_lineage() -> None:
    assert displayed_return(1_502_900, 1_000_000) == pytest.approx(50.29)
    implied = implied_initial_value(31_514, 264.14)
    assert implied == pytest.approx(8654.36, abs=0.01)
    assert not math.isclose(implied, 10_000.0)
