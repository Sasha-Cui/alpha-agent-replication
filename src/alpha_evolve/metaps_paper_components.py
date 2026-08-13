"""Paper-derived MetaPS mechanics with explicit non-author-code boundaries.

This module implements only mechanics that are fully determined by the compact
listings and equations in arXiv:2606.22385v1.  It is not the missing MetaPS
codebase, simulator, strategy registry, dataset builder, model router, or
backtester and must not be used as evidence that a published result reproduced.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


class UnderspecifiedPaperMechanic(ValueError):
    """Raised when the paper does not determine a unique executable choice."""


@dataclass(frozen=True)
class NewsEvent:
    impacts: Mapping[str, float]


@dataclass(frozen=True)
class RawDecision:
    action: str
    size_mode: str
    confidence: float | None
    risk_note: str
    reason: str = ""


def hold(reason: str) -> RawDecision:
    return RawDecision("HOLD", "none", None, "", reason)


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _return(start: float, end: float) -> float:
    start = _finite(start, "start")
    end = _finite(end, "end")
    if start == 0:
        raise ValueError("return denominator cannot be zero")
    return end / start - 1.0


def news_impulse(news: Sequence[NewsEvent]) -> RawDecision:
    """Literal news-impulse listing with the unambiguous argmax helper filled."""
    if not news:
        return hold("no catalyst")
    impacts = news[0].impacts
    if not impacts:
        return hold("no catalyst")
    ticker, impact = max(impacts.items(), key=lambda item: abs(item[1]))
    impact = _finite(impact, "news impact")
    if abs(impact) < 0.002:
        return hold("news impact too weak")
    direction = "BUY" if impact > 0 else "SELL"
    return RawDecision(
        f"{direction} {ticker}",
        "probe_to_medium",
        min(abs(impact) * 30, 1.0),
        "abort if follow-through stalls",
    )


def momentum_follow(price_history: Mapping[str, Sequence[float]]) -> RawDecision:
    """Literal three-interval momentum listing using conventional simple return."""
    best_ticker: str | None = None
    best_momentum = 0.0
    for ticker, history in price_history.items():
        if len(history) < 4:
            raise ValueError(f"{ticker} needs at least four prices")
        move_3 = _return(history[-4], history[-1])
        if abs(move_3) > abs(best_momentum):
            best_ticker, best_momentum = ticker, move_3
    if best_ticker is None or abs(best_momentum) < 0.002:
        return hold("momentum too weak")
    direction = "BUY" if best_momentum > 0 else "SELL"
    return RawDecision(
        f"{direction} {best_ticker}",
        "scalable",
        min(abs(best_momentum) * 20, 1.0),
        "pair with hedge if the book becomes one-sided",
    )


def risk_reset(
    *,
    cash: float,
    gross_exposure: float,
    volatility_regime: float,
    liquidity_regime: float,
) -> RawDecision:
    """Literal risk-reset score and branch from the paper listing."""
    cash = _finite(cash, "cash")
    gross_exposure = _finite(gross_exposure, "gross_exposure")
    volatility_regime = _finite(volatility_regime, "volatility_regime")
    liquidity_regime = _finite(liquidity_regime, "liquidity_regime")
    equity = cash + gross_exposure
    vol_risk = max(0.0, volatility_regime - 0.4) / 0.6
    liq_risk = max(0.0, liquidity_regime - 0.4) / 0.6
    exposure_risk = gross_exposure / max(equity, 1.0)
    risk = 0.4 * vol_risk + 0.3 * liq_risk + 0.3 * exposure_risk
    if risk < 0.5:
        return hold("risk elevated but no forced reset")
    return RawDecision(
        "REDUCE",
        "reduce",
        0.6 * (1.0 - 0.3 * risk),
        "no new positions until constraints cool",
    )


def liquidity_rebate(
    *,
    price_history: Mapping[str, Sequence[float]],
    liquidity_regime: float,
    volatility_regime: float,
    has_news: bool,
) -> RawDecision:
    """Literal liquidity-rebate branch with arithmetic mean filled in."""
    if not (liquidity_regime > 0.4 and volatility_regime < 0.5) or has_news:
        return hold("avoid liquidity provision during catalysts")
    candidates: list[tuple[str, float, float, float]] = []
    for ticker, history in price_history.items():
        if len(history) < 5:
            raise ValueError(f"{ticker} needs at least five prices")
        window = [_finite(value, f"{ticker} price") for value in history[-5:]]
        mid = sum(window) / len(window)
        if mid == 0:
            raise ValueError("mid price cannot be zero")
        spread = abs(window[-1] - mid) / mid
        if spread < 0.008:
            candidates.append((ticker, window[-1], mid, spread))
    if not candidates:
        return hold("no tight-spread instrument")
    ticker, price, mid, _ = max(candidates, key=lambda item: item[3])
    action = "BUY" if price < mid else "SELL"
    return RawDecision(
        f"{action} {ticker}",
        "liquidity",
        0.47,
        "stop when one-way news gaps appear",
    )


def volatility_breakout_literal(price_history: Mapping[str, Sequence[float]]) -> RawDecision:
    """Execute the printed listing literally, including its unreachable branches.

    The listing defines ``window = history[-20:]`` and ``current = history[-1]``.
    Consequently ``current <= max(window)`` and ``current >= min(window)``, so
    neither the 0.2% upper nor lower breakout condition can ever hold.
    """
    for ticker, history in price_history.items():
        if len(history) < 20:
            raise ValueError(f"{ticker} needs at least twenty prices")
        window = [_finite(value, f"{ticker} price") for value in history[-20:]]
        high, low, current = max(window), min(window), window[-1]
        if low == 0:
            raise ValueError("range denominator cannot be zero")
        range_width = (high - low) / low
        if range_width >= 0.005:
            continue
        if current > high * 1.002 or current < low * 0.998:
            raise AssertionError("printed MetaPS breakout branch is mathematically unreachable")
    return hold("no compression-breakout pattern")


SIZE_BUCKETS: Mapping[str, tuple[float, int]] = {
    "none": (0.0, 0),
    "small": (0.04, 320),
    "medium": (0.09, 800),
    "large": (0.16, 1200),
}


def size_bucket_rule(bucket: str) -> tuple[float, int]:
    """Return the two deterministic sizing values explicitly printed in the paper."""
    try:
        return SIZE_BUCKETS[bucket]
    except KeyError as exc:
        raise UnderspecifiedPaperMechanic(
            f"paper gives no mapping from raw size_mode {bucket!r} to none/small/medium/large"
        ) from exc


def ranking_score(
    *,
    trigger_overlap: int,
    text_match: float,
    prior: float,
    missing_evidence_penalty: float,
    alpha: float,
    beta: float,
) -> float:
    """The paper's candidate-ranking equation for already-computed inputs."""
    return (
        alpha * trigger_overlap
        + beta * text_match
        + prior
        - missing_evidence_penalty
    )


def v1_target(one_step_gains: Mapping[str, float]) -> str:
    """Select the V1 short-horizon winner; reject the unspecified tie policy."""
    if not one_step_gains:
        raise ValueError("at least one candidate is required")
    best = max(one_step_gains.values())
    winners = [name for name, value in one_step_gains.items() if value == best]
    if len(winners) != 1:
        raise UnderspecifiedPaperMechanic("V1 tie-breaking is not specified")
    return winners[0]


def v2_blended_score(
    *,
    horizon_gains: Mapping[int, float],
    horizon_weights: Mapping[int, float],
    transaction_cost_proxy: float,
    risk_penalty: float,
    turnover_penalty: float,
    utility_prior: float,
    candidate_edge: float,
    eta: float,
    kappa: float,
) -> float:
    """The V2 equations for explicitly supplied, otherwise-unreleased inputs."""
    if set(horizon_gains) != {3, 5, 10, 20}:
        raise ValueError("paper defines V2 horizons as exactly {3,5,10,20}")
    if set(horizon_weights) != set(horizon_gains):
        raise ValueError("one strategy-specific weight is required per V2 horizon")
    gross = sum(horizon_weights[h] * horizon_gains[h] for h in horizon_gains)
    utility = gross - transaction_cost_proxy - risk_penalty - turnover_penalty
    return (1.0 - eta) * utility + eta * utility_prior + kappa * candidate_edge


def v3_balance_score(
    *,
    active_action_bonus: float,
    v2_score: float,
    sample_weight: float,
    action_delta: float,
    bucket_delta: float,
    strategy_delta: float,
) -> float:
    """The printed V3 quality and distribution-control equations."""
    quality = (
        active_action_bonus
        + 3.0 * max(0.0, v2_score)
        + 0.08 * min(sample_weight, 1.6)
    )
    return quality + action_delta + bucket_delta + strategy_delta


def displayed_return(final_value: float, initial_value: float) -> float:
    """Return percentage under the paper's stated final/initial-value definition."""
    final_value = _finite(final_value, "final_value")
    initial_value = _finite(initial_value, "initial_value")
    if initial_value == 0:
        raise ValueError("initial value cannot be zero")
    return (final_value / initial_value - 1.0) * 100.0


def implied_initial_value(final_value: float, displayed_return_percent: float) -> float:
    """Invert the stated return identity for an arithmetic consistency check."""
    denominator = 1.0 + displayed_return_percent / 100.0
    if denominator == 0:
        raise ValueError("return implies zero denominator")
    return final_value / denominator


PAPER_BOUNDARY = (
    "paper-derived mechanics only; not author code, native simulator/training/backtest "
    "execution, or published-result regeneration"
)
