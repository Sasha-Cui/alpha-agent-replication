"""Training-only regularized factor-sleeve allocation diagnostic."""

from __future__ import annotations
import numpy as np


def walk_forward_augmentation(factors, agent, min_train=36, risk_aversion=10.0, shrinkage=0.5, target_asset_vol=0.10):
    """Compare the same allocation rule with/without a nonnegative agent sleeve.

    Historical volatility scales each sleeve; a unit L1 risk-budget cap follows
    a diagonal-shrunk quadratic-utility solution. This is a synthetic allocation
    comparison, not unrestricted spanning inference or an all-in cost estimate.
    Factor internal turnover/financing costs are not available from return panels.
    """
    f = np.asarray(factors, float)
    a = np.asarray(agent, float)
    if f.ndim != 2 or a.shape != (len(f),) or len(a) <= min_train or not np.isfinite(np.c_[f, a]).all():
        raise ValueError("Finite aligned factors and agent required")
    if min_train < 12 or risk_aversion <= 0 or not 0 < shrinkage <= 1 or target_asset_vol <= 0:
        raise ValueError("Invalid fixed allocation settings")
    both = np.c_[f, a]
    returns = []
    weights = []
    for end in range(min_train, len(a)):
        output = []
        row_weights = []
        for include in [False, True]:
            data = both if include else f
            train = data[:end]
            sd = train.std(axis=0, ddof=1)
            if (sd <= 1e-12).any():
                raise ValueError("A sleeve has no estimable historical volatility")
            scales = target_asset_vol / (np.sqrt(12) * sd)
            z = train * scales
            mean = z.mean(axis=0)
            cov = np.atleast_2d(np.cov(z, rowvar=False))
            regularized = (1 - shrinkage) * cov + shrinkage * np.diag(np.diag(cov))
            risk_weights = np.linalg.solve(regularized, mean) / risk_aversion
            if include and risk_weights[-1] < 0:
                risk_weights = np.r_[np.linalg.solve(regularized[:-1, :-1], mean[:-1]) / risk_aversion, 0.0]
            risk_weights = risk_weights / max(1.0, np.abs(risk_weights).sum())
            physical = risk_weights * scales
            output.append(float(data[end] @ physical))
            row_weights.append(np.r_[physical, 0.0] if not include else physical)
        returns.append(output)
        weights.append(row_weights)
    return {
        "returns": np.asarray(returns),
        "weights": np.asarray(weights),
        "start_index": min_train,
        "parameters": {
            "min_train": min_train,
            "risk_aversion": risk_aversion,
            "covariance_diagonal_shrinkage": shrinkage,
            "per_sleeve_past_vol_target": target_asset_vol,
            "risk_budget_l1_cap": 1.0,
        },
        "claim_boundary": "Conditional gross-factor allocation diagnostic; not unrestricted JKP132 alpha, not a net deployable fund, and not a test of the best possible allocator.",
    }
