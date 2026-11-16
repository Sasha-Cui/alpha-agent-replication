"""Independent price/share ledger and fixed initial-capital aggregation for v2."""
from __future__ import annotations
import numpy as np


def binary_share_account(actions, prices, cost_bps=10, lag=1):
    """Self-financing fractional shares: BUY invests cash, SELL liquidates, HOLD drifts.

    Initial capital is one and cash earns zero. At each close mark the prior
    position, then fill the lagged order; no terminal forced liquidation.
    This uses explicit units and closed-form fills, independently of the
    generic target-weight bisection account used in the primary pipeline.
    """
    prices = np.asarray(prices, dtype=float)
    if prices.ndim != 1 or len(actions) != len(prices) or not len(prices):
        raise ValueError("Unaligned or empty actions and prices")
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("Prices must be finite and positive")
    if not isinstance(lag, int) or lag < 0 or not np.isfinite(cost_bps) or not 0 <= cost_bps < 10000:
        raise ValueError("Invalid lag or fee")
    if any(action not in ["BUY", "SELL", "HOLD"] for action in actions):
        raise ValueError("Unknown categorical action")
    cash = nav = 1.0
    units = 0.0
    fee = cost_bps / 10000
    output = []
    for i, price in enumerate(prices):
        action = actions[i-lag] if i >= lag else "HOLD"
        marked = cash + units * price
        traded = charge = 0.0
        if action == "BUY":
            bought = cash / (price * (1 + fee))
            traded = bought * price
            charge = fee * traded
            units += bought
            cash = 0.0
        elif action == "SELL":
            traded = units * price
            charge = fee * traded
            cash += traded - charge
            units = 0.0
        current = cash + units * price
        if current <= 0 or cash < 0 or units < 0:
            raise ValueError("Invalid account state")
        output.append((current/nav-1, traded/marked, charge/marked, current, cash, units))
        nav = current
    return np.asarray(output)


def equal_initial_capital(returns):
    """Combine aligned independent accounts without daily cross-account rebalancing."""
    returns = np.asarray(returns, dtype=float)
    if returns.ndim != 2 or not all(returns.shape) or not np.isfinite(returns).all() or (returns <= -1).any():
        raise ValueError("Expected finite aligned day-by-account return matrix")
    wealth = np.cumprod(1 + returns, axis=0).mean(axis=1)
    return wealth / np.r_[1.0, wealth[:-1]] - 1
