"""Paper-derived mechanics for arXiv:2606.08283v1.

This module implements only operations uniquely fixed by the printed equations.
It is not author code, an LLM replay, a data reconstruction, a portfolio backtest,
or regeneration of a published result.  Ambiguous operations fail closed instead
of choosing an implementation that the paper does not identify.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence


PAPER_BOUNDARY = (
    "paper-derived controlled mechanic, not author code, native execution, "
    "or regeneration of a Macro Economists in the Machine result"
)


class UnderspecifiedPaperMechanic(ValueError):
    """Raised when the paper does not determine one executable procedure."""


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _vector(values: Sequence[float], name: str, *, nonnegative: bool = False) -> list[float]:
    checked = [_finite(value, name) for value in values]
    if not checked:
        raise ValueError(f"{name} cannot be empty")
    if nonnegative and any(value < 0 for value in checked):
        raise ValueError(f"{name} must be nonnegative")
    return checked


def rule_raw_tilt(zscores: Sequence[float], loadings: Sequence[int]) -> float:
    """Equation 2: thresholded z-score/loading sum for one asset."""
    zscores = _vector(zscores, "zscore")
    if len(zscores) != len(loadings):
        raise ValueError("zscores and loadings must have equal length")
    if any(loading not in {-1, 0, 1} for loading in loadings):
        raise ValueError("loadings must be -1, 0, or 1")
    return sum(loading * zscore for zscore, loading in zip(zscores, loadings) if abs(zscore) >= 0.5)


def discretize_rule_tilt(raw_tilt: float) -> int:
    """Equation 3: map a raw score to the printed five-level signal."""
    value = _finite(raw_tilt, "raw_tilt")
    if value >= 2:
        return 2
    if value >= 1:
        return 1
    if value <= -2:
        return -2
    if value <= -1:
        return -1
    return 0


def conflict_detected(*, vix: float, indpro: float, breakeven: float, real_yield: float) -> bool:
    """Appendix C.1's two-clause deterministic conflict indicator."""
    values = [_finite(value, name) for value, name in (
        (vix, "vix"), (indpro, "indpro"), (breakeven, "breakeven"), (real_yield, "real_yield")
    )]
    vix, indpro, breakeven, real_yield = values
    return (vix > 1 and indpro > 1) or (breakeven > 1 and real_yield < -1)


def attenuate_conflicting_tilts(tilts: Sequence[float], *, conflict: bool, gamma: float = 0.5) -> list[float]:
    """Appendix C.1's magnitude attenuation, including its half-level outputs."""
    checked = _vector(tilts, "tilt")
    gamma = _finite(gamma, "gamma")
    if not 0 <= gamma <= 1:
        raise ValueError("gamma must lie in [0, 1]")
    return [value * gamma if conflict else value for value in checked]


def risk_off_score(*, vix: float, fed_funds: float, real_yield: float, usd: float) -> float:
    """Appendix C.2's four-indicator risk-off score."""
    vix, fed_funds, real_yield, usd = (
        _finite(value, name)
        for value, name in ((vix, "vix"), (fed_funds, "fed_funds"), (real_yield, "real_yield"), (usd, "usd"))
    )
    return (
        0.40 * (vix >= 1.5)
        + 0.25 * (fed_funds >= 1.0)
        + 0.20 * (real_yield >= 1.0)
        + 0.15 * (usd >= 0.5)
    )


def suppress_positive_cyclical_tilts(
    tilts: Sequence[float], cyclical: Sequence[bool], *, score: float, trigger: float = 0.65
) -> list[float]:
    """Appendix C.2's signal suppression for a caller-supplied cyclical mask."""
    checked = _vector(tilts, "tilt")
    if len(checked) != len(cyclical):
        raise ValueError("tilts and cyclical mask must have equal length")
    score, trigger = _finite(score, "score"), _finite(trigger, "trigger")
    return [0.0 if score >= trigger and flag and value > 0 else value for value, flag in zip(checked, cyclical)]


def rule_regime_probabilities(_: Mapping[str, float]) -> dict[str, float]:
    """Reject Appendix C.3's non-unique proportional/residual construction."""
    raise UnderspecifiedPaperMechanic(
        "four regime scores are only proportional, then clipped and normalized to unit sum, "
        "while risk-on is called the residual; the constants and ordering are not defined"
    )


def average_absolute_disagreement(hawkish: Sequence[float], dovish: Sequence[float]) -> float:
    """Equation 4's mean absolute ticker-level disagreement."""
    left, right = _vector(hawkish, "hawkish tilt"), _vector(dovish, "dovish tilt")
    if len(left) != len(right):
        raise ValueError("agent tilt vectors must have equal length")
    return sum(abs(a - b) for a, b in zip(left, right)) / len(left)


def debate_consensus(hawkish_revised: Sequence[float], dovish_revised: Sequence[float]) -> list[float]:
    """Equation 5's equal-weighted consensus for already-revised contracts."""
    left, right = _vector(hawkish_revised, "hawkish tilt"), _vector(dovish_revised, "dovish tilt")
    if len(left) != len(right):
        raise ValueError("agent tilt vectors must have equal length")
    return [(a + b) / 2 for a, b in zip(left, right)]


def inverse_volatility_weights(volatilities: Sequence[float]) -> list[float]:
    """Equation 6's normalized inverse-volatility allocation."""
    checked = _vector(volatilities, "volatility")
    if any(value <= 0 for value in checked):
        raise ValueError("volatilities must be positive")
    inverse = [1 / value for value in checked]
    total = sum(inverse)
    return [value / total for value in inverse]


def blend_with_equal_weight(ivol_weights: Sequence[float], alpha: float = 0.5) -> list[float]:
    """Equation 7's inverse-volatility/equal-weight blend."""
    weights = _vector(ivol_weights, "inverse-volatility weight", nonnegative=True)
    if not math.isclose(sum(weights), 1.0, rel_tol=0, abs_tol=1e-12):
        raise ValueError("inverse-volatility weights must sum to one")
    alpha = _finite(alpha, "alpha")
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must lie in [0, 1]")
    equal = 1 / len(weights)
    return [alpha * weight + (1 - alpha) * equal for weight in weights]


def multiplicative_macro_tilt(base_weights: Sequence[float], tilts: Sequence[float], kappa: float = 0.25) -> list[float]:
    """Equation 8's unnormalized multiplicatively tilted weights."""
    base = _vector(base_weights, "base weight", nonnegative=True)
    signals = _vector(tilts, "tilt")
    if len(base) != len(signals):
        raise ValueError("base weights and tilts must have equal length")
    if any(not -2 <= signal <= 2 for signal in signals):
        raise ValueError("tilts must lie in [-2, 2]")
    kappa = _finite(kappa, "kappa")
    return [weight * (1 + kappa * signal) for weight, signal in zip(base, signals)]


def normalize_long_only(weights: Sequence[float]) -> list[float]:
    """Normalize a nonnegative vector, as repeatedly named in the paper."""
    checked = _vector(weights, "weight", nonnegative=True)
    total = sum(checked)
    if total <= 0:
        raise ValueError("at least one weight must be positive")
    return [value / total for value in checked]


def literal_cyclical_cap_then_renormalize(
    weights: Sequence[float], cyclical: Sequence[bool], cap: float = 0.45
) -> list[float]:
    """Execute the prose literally to expose that renormalization can break the cap."""
    checked = _vector(weights, "weight", nonnegative=True)
    if len(checked) != len(cyclical):
        raise ValueError("weights and cyclical mask must have equal length")
    cap = _finite(cap, "cap")
    if not 0 < cap < 1:
        raise ValueError("cap must lie in (0, 1)")
    cyclical_total = sum(weight for weight, flag in zip(checked, cyclical) if flag)
    if cyclical_total > cap:
        scale = cap / cyclical_total
        checked = [weight * scale if flag else weight for weight, flag in zip(checked, cyclical)]
    return normalize_long_only(checked)


def constrained_portfolio_weights(*_: object, **__: object) -> list[float]:
    """Reject the unresolved cap/order/projection part of the portfolio engine."""
    raise UnderspecifiedPaperMechanic(
        "the cyclical ETF set is not enumerated; scaling cyclicals to 0.45 then "
        "renormalizing can violate that cap; and normalization, cyclical cap, "
        "single-name cap, and turnover-cap projection order is not specified"
    )


def one_way_turnover(previous: Sequence[float], target: Sequence[float]) -> float:
    """Equations 10 and 14: half the L1 change in portfolio weights."""
    left, right = _vector(previous, "previous weight"), _vector(target, "target weight")
    if len(left) != len(right):
        raise ValueError("weight vectors must have equal length")
    return 0.5 * sum(abs(a - b) for a, b in zip(left, right))


def scale_target_to_turnover_limit(
    previous: Sequence[float], target: Sequence[float], maximum: float = 0.5
) -> list[float]:
    """The unique straight-line scale toward previous weights named in the prose."""
    left, right = _vector(previous, "previous weight"), _vector(target, "target weight")
    if len(left) != len(right):
        raise ValueError("weight vectors must have equal length")
    maximum = _finite(maximum, "maximum")
    if maximum < 0:
        raise ValueError("maximum turnover cannot be negative")
    observed = one_way_turnover(left, right)
    if observed <= maximum or observed == 0:
        return right
    fraction = maximum / observed
    return [a + fraction * (b - a) for a, b in zip(left, right)]


def annualized_return_volatility_sharpe(weekly_returns: Sequence[float]) -> tuple[float, float, float]:
    """Equations 11--12, using Python's sample standard deviation."""
    returns = _vector(weekly_returns, "weekly return")
    if len(returns) < 2:
        raise ValueError("at least two weekly returns are required")
    annual_return = 52 * statistics.mean(returns)
    annual_volatility = math.sqrt(52) * statistics.stdev(returns)
    if annual_volatility == 0:
        raise ValueError("weekly return volatility cannot be zero")
    return annual_return, annual_volatility, annual_return / annual_volatility


def maximum_drawdown(weekly_returns: Sequence[float]) -> float:
    """Standard peak-to-trough drawdown on the compounded $1 path."""
    returns = _vector(weekly_returns, "weekly return")
    wealth = peak = 1.0
    worst = 0.0
    for value in returns:
        if value <= -1:
            raise ValueError("weekly returns must exceed -1")
        wealth *= 1 + value
        peak = max(peak, wealth)
        worst = min(worst, wealth / peak - 1)
    return worst


def hit_rate(weekly_returns: Sequence[float]) -> float:
    """Fraction of supplied weeks with strictly positive returns."""
    returns = _vector(weekly_returns, "weekly return")
    return sum(value > 0 for value in returns) / len(returns)


def net_return_after_cost(gross_return: float, cost_bps: float, turnover: float) -> float:
    """Equation 14's one-way transaction-cost adjustment."""
    gross_return = _finite(gross_return, "gross_return")
    cost_bps = _finite(cost_bps, "cost_bps")
    turnover = _finite(turnover, "turnover")
    if cost_bps < 0 or turnover < 0:
        raise ValueError("cost and turnover cannot be negative")
    return gross_return - cost_bps * 1e-4 * turnover


def stationary_bootstrap_sharpe_test(*_: object, **__: object) -> None:
    """Reject the unnamed bootstrap selector, seed, and p-value conventions."""
    raise UnderspecifiedPaperMechanic(
        "B=5000 and paired stationary resampling are stated, but the automatic "
        "block-length selector, seed, interval construction, p-value statistic, "
        "tail convention, and tie handling are not identified"
    )


def validate_llm_contract(*_: object, **__: object) -> None:
    """Reject reconstruction of the omitted required JSON schema."""
    raise UnderspecifiedPaperMechanic(
        "the prompt requires a JSON schema, but the schema, complete dynamic input "
        "template, narrative generator, historical-band calculation, category-policy "
        "fields, validation/retry policy, and cached contracts are not released"
    )
