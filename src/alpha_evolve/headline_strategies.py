"""Source-anchored signal primitives for the U.S./JKP headline study.

These primitives are not complete trading-strategy or paper-replication claims.
Portfolio adapters and input-definition checks are recorded in each recipe.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def gpt_signal_evc(
    roa: pd.Series,
    enterprise_value_to_ebitda: pd.Series,
    price_to_cashflow: pd.Series,
) -> pd.Series:
    """GPT-Signal Section 5.1: (1/ROA)*(1/(EV/EBITDA))*(1/(P/CF)).

    Preserve the published reciprocal structure, signs, and aligned input rows.
    Undefined inputs remain missing; do not introduce epsilon protection,
    absolute-value transforms, cross-time imputation, or outcome-aware repair.
    """
    if not (roa.index.equals(enterprise_value_to_ebitda.index)
            and roa.index.equals(price_to_cashflow.index)):
        raise ValueError("EVC inputs must have identical aligned indices")
    values = pd.concat([roa, enterprise_value_to_ebitda, price_to_cashflow], axis=1).astype("float64")
    valid = np.isfinite(values).all(axis=1) & values.ne(0).all(axis=1)
    result = pd.Series(np.nan, index=roa.index, name="evc", dtype="float64")
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        reciprocal = 1.0 / values.loc[valid]
        result.loc[valid] = reciprocal.iloc[:, 0] * reciprocal.iloc[:, 1] * reciprocal.iloc[:, 2]
    return result.where(np.isfinite(result))


def gpt_signal_evc_trading_score(evc: pd.Series) -> pd.Series:
    """Use the paper's negative EVC/return relationship, not fitted JKP polarity."""
    return (-evc.astype("float64")).rename("gpt_signal_evc_score")
