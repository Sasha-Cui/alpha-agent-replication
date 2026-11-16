"""Self-financing long-only accounts allowing an uninvested cash allocation."""

from __future__ import annotations
import numpy as np


def cash_account(targets, returns, costs_bps, rebalance_mask=None):
    """Earn prior holdings' return, then execute today's target at today's close.

    Targets contain securities only, sum to at most one, and exclude cash turnover.
    Cash earns zero, matching the disclosed source-account convention. A signal
    at close t must be shifted to the execution target at t+1 by the caller.
    """
    targets = np.asarray(targets, dtype=float)
    returns = np.asarray(returns, dtype=float)
    if targets.ndim != 2 or targets.shape != returns.shape:
        raise ValueError("Unaligned account arrays")
    fee = float(costs_bps) / 10000
    if (
        not 0 <= fee < 1
        or not np.isfinite(targets).all()
        or (targets < 0).any()
        or (targets.sum(axis=1) > 1 + 1e-12).any()
    ):
        raise ValueError("Invalid targets or costs")
    mask = np.ones(len(targets), dtype=bool) if rebalance_mask is None else np.asarray(rebalance_mask, dtype=bool)
    if mask.shape != (len(targets),):
        raise ValueError("Invalid rebalance mask")
    dollars = np.zeros(targets.shape[1])
    cash = nav = 1.0
    paths = []
    turnover = []
    fees = []
    for weights, realization, rebalance in zip(targets, returns, mask):
        held = dollars > 0
        if not np.isfinite(realization[held]).all() or (realization[held] < -1).any():
            raise ValueError("Invalid held return")
        marked = dollars * (1 + np.where(held, realization, 0))
        gross = cash + marked.sum()
        if gross <= 0:
            raise ValueError("Nonpositive NAV")
        if not rebalance:
            paths.append(gross / nav - 1)
            turnover.append(0.0)
            fees.append(0.0)
            dollars = marked
            nav = gross
            continue
        # Fee equation is monotone for fee<1 and sum(weights)<=1.
        lo, hi = 0.0, gross
        for _ in range(55):
            mid = (lo + hi) / 2
            if mid + fee * np.abs(mid * weights - marked).sum() > gross:
                hi = mid
            else:
                lo = mid
        after = (lo + hi) / 2
        traded = np.abs(after * weights - marked).sum()
        paths.append(after / nav - 1)
        turnover.append(traded / gross)
        fees.append(fee * traded / gross)
        dollars = after * weights
        cash = after - dollars.sum()
        nav = after
    return np.asarray(paths), np.asarray(turnover), np.asarray(fees)


def categorical_targets(actions, lag=1):
    """BUY fully invests; SELL liquidates; HOLD retains prior target; start in cash."""
    if not isinstance(lag, int) or lag < 0:
        raise ValueError("Nonnegative integer lag required")
    desired = []
    holding = 0.0
    for action in actions:
        if action in ["BUY", "buy", 1]:
            holding = 1.0
        elif action in ["SELL", "sell", -1]:
            holding = 0.0
        elif action not in ["HOLD", "hold", 0]:
            raise ValueError("Unknown categorical action")
        desired.append(holding)
    targets = np.zeros(len(desired))
    if lag < len(desired):
        targets[lag:] = np.asarray(desired)[: len(desired) - lag]
    return targets[:, None]
