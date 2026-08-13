"""Paper-derived FinPos mechanics with explicit non-author-code boundaries.

This module implements only equations printed in arXiv:2510.27251v2.  It is
not the missing FinPos agent, data pipeline, memory system, risk engine, market
simulator, baseline suite, or result generator and earns no paper-result credit.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


PAPER_BOUNDARY = (
    "paper-derived controlled mechanic, not author code, native execution, "
    "or regeneration of a published FinPos result"
)


class UnderspecifiedPaperMechanic(ValueError):
    """Raised when the paper does not determine a unique executable choice."""


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _positive_price(value: float, name: str) -> float:
    value = _finite(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def single_step_log_return(action: int, price_t: float, price_next: float) -> float:
    """Equation 1: ``a_t * log(price[t+1] / price[t])``."""
    if action not in {-1, 0, 1}:
        raise ValueError("action must be one of -1, 0, 1")
    start = _positive_price(price_t, "price_t")
    end = _positive_price(price_next, "price_next")
    return action * math.log(end / start)


def position_log_return(position: float, price_t: float, price_next: float) -> float:
    """Equation 2: ``pos_t * log(price[t+1] / price[t])``."""
    position = _finite(position, "position")
    start = _positive_price(price_t, "price_t")
    end = _positive_price(price_next, "price_next")
    return position * math.log(end / start)


def update_position(previous: float, direction: int, quantity: float) -> float:
    """Printed state equation: ``pos_t = pos_(t-1) + d_t * q_t``."""
    previous = _finite(previous, "previous")
    if direction not in {-1, 0, 1}:
        raise ValueError("direction must be one of -1, 0, 1")
    quantity = _finite(quantity, "quantity")
    if quantity < 0:
        raise ValueError("quantity cannot be negative")
    return previous + direction * quantity


def multi_timescale_score(prices: Sequence[float], t: int) -> float:
    """The unweighted 1-, 7-, and 30-trading-step raw-price score."""
    if t < 0 or t + 30 >= len(prices):
        raise ValueError("paper score requires prices at t, t+1, t+7, and t+30")
    base = _positive_price(prices[t], "price_t")
    return sum(
        _positive_price(prices[t + horizon], f"price_t_plus_{horizon}") - base
        for horizon in (1, 7, 30)
    )


def literal_reward(previous_position: float, position: float, score: float) -> float:
    """Execute the paper's reward literally, including its total-position term."""
    previous_position = _finite(previous_position, "previous_position")
    position = _finite(position, "position")
    score = _finite(score, "score")
    if position == previous_position:
        return -(score**2)
    return position * score


def sharpe_ratio(average_return: float, risk_free_rate: float, volatility: float) -> float:
    """The paper's unannualized symbolic Sharpe equation for supplied inputs."""
    average_return = _finite(average_return, "average_return")
    risk_free_rate = _finite(risk_free_rate, "risk_free_rate")
    volatility = _finite(volatility, "volatility")
    if volatility <= 0:
        raise ValueError("volatility must be positive")
    return (average_return - risk_free_rate) / volatility


def maximum_drawdown_future_trough(values: Sequence[float]) -> float:
    """The printed future-trough MDD definition for a positive value path."""
    if not values:
        raise ValueError("at least one account value is required")
    checked = [_positive_price(value, "account value") for value in values]
    future_min = checked[-1]
    drawdowns = [0.0] * len(checked)
    for index in range(len(checked) - 1, -1, -1):
        future_min = min(future_min, checked[index])
        drawdowns[index] = (checked[index] - future_min) / checked[index]
    return max(drawdowns)


def empirical_var_cvar(pnl: Sequence[float], alpha: float) -> tuple[float, float]:
    """Literal empirical lower-tail VaR/CVaR using the printed infimum definition.

    The paper does not resolve whether its phrase "95% CVaR" means ``alpha=.95``
    under this lower-tail PnL equation or a conventional 5% lower tail.  Callers
    must therefore supply alpha explicitly; this function does not repair it.
    """
    if not pnl:
        raise ValueError("at least one PnL observation is required")
    alpha = _finite(alpha, "alpha")
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")
    values = sorted(_finite(value, "PnL") for value in pnl)
    index = max(0, math.ceil(alpha * len(values)) - 1)
    var = values[index]
    tail = [value for value in values if value <= var]
    return var, sum(tail) / len(tail)


def calmar_ratio(annualized_return: float, maximum_drawdown: float) -> float:
    """The printed Calmar equation for already-computed inputs."""
    annualized_return = _finite(annualized_return, "annualized_return")
    maximum_drawdown = _finite(maximum_drawdown, "maximum_drawdown")
    if maximum_drawdown == 0:
        raise ValueError("maximum_drawdown cannot be zero")
    return annualized_return / abs(maximum_drawdown)


def cumulative_log_return_to_reported_percent(_: float) -> float:
    """Reject an unstated conversion from the printed log sum to CR percent."""
    raise UnderspecifiedPaperMechanic(
        "paper does not say whether CR% is 100*sum(log returns), "
        "100*(exp(sum(log returns))-1), or an account-value return"
    )


def cvar_to_maximum_order_quantity(_: float) -> int:
    """Reject the unstated dimensional conversion from CVaR to integer shares."""
    raise UnderspecifiedPaperMechanic(
        "paper defines CVaR as a PnL/return statistic but gives no conversion "
        "from that statistic to the integer maxcvar order-size ceiling"
    )
