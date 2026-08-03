"""Statistical and portfolio helpers for the submission evidence build.

The functions in this module are deliberately independent of the paper's
hand-written candidate formulas.  They implement the frozen evaluator:
portfolio weights, drift-aware traded notional, HAC alpha, multiplicity, and a
paired moving-block bootstrap.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor, sqrt
from typing import Iterable, Mapping

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests


@dataclass(frozen=True)
class AlphaResult:
    n_months: int
    start: str
    end: str
    hac_lags: int
    alpha_monthly: float
    alpha_annualized: float
    alpha_se_monthly: float
    alpha_t_hac: float
    p_value_two_sided: float
    ci_low_annualized: float
    ci_high_annualized: float
    residual_vol_monthly: float
    appraisal_ratio_annualized: float
    sharpe_annualized: float
    r_squared: float


def automatic_hac_lag(n_obs: int) -> int:
    """Newey-West rule used in the frozen protocol."""
    if n_obs <= 1:
        return 0
    return max(0, floor(4.0 * (n_obs / 100.0) ** (2.0 / 9.0)))


def annualized_sharpe(values: Iterable[float]) -> float:
    x = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 2:
        return float("nan")
    sd = float(x.std(ddof=1))
    if not np.isfinite(sd) or sd <= 0:
        return float("nan")
    return float(sqrt(12.0) * x.mean() / sd)


def alpha_regression(
    frame: pd.DataFrame,
    return_col: str,
    factor_cols: list[str],
    *,
    month_col: str = "month",
    hac_lags: int | None = None,
) -> AlphaResult:
    """Estimate factor alpha with a HAC covariance and asymptotic interval."""
    cols = [month_col, return_col, *factor_cols]
    reg = frame[cols].replace([np.inf, -np.inf], np.nan).dropna().copy()
    reg[month_col] = pd.to_datetime(reg[month_col], errors="coerce")
    reg = reg.dropna(subset=[month_col]).sort_values(month_col)
    if len(reg) <= len(factor_cols) + 3:
        raise ValueError("insufficient observations for alpha regression")
    y = reg[return_col].astype("float64")
    x = sm.add_constant(reg[factor_cols].astype("float64"), has_constant="add")
    lags = automatic_hac_lag(len(reg)) if hac_lags is None else int(hac_lags)
    fit = sm.OLS(y, x).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": lags, "use_correction": True},
        use_t=False,
    )
    alpha = float(fit.params["const"])
    se = float(fit.bse["const"])
    t_value = alpha / se if se > 0 else float("nan")
    p_value = float(2.0 * stats.norm.sf(abs(t_value))) if np.isfinite(t_value) else float("nan")
    residual_sd = float(pd.Series(fit.resid).std(ddof=max(1, len(factor_cols) + 1)))
    ar = float(sqrt(12.0) * alpha / residual_sd) if residual_sd > 0 else float("nan")
    z = float(stats.norm.ppf(0.975))
    return AlphaResult(
        n_months=int(len(reg)),
        start=str(reg[month_col].min().date()),
        end=str(reg[month_col].max().date()),
        hac_lags=lags,
        alpha_monthly=alpha,
        alpha_annualized=12.0 * alpha,
        alpha_se_monthly=se,
        alpha_t_hac=t_value,
        p_value_two_sided=p_value,
        ci_low_annualized=12.0 * (alpha - z * se),
        ci_high_annualized=12.0 * (alpha + z * se),
        residual_vol_monthly=residual_sd,
        appraisal_ratio_annualized=ar,
        sharpe_annualized=annualized_sharpe(y),
        r_squared=float(fit.rsquared),
    )


def target_weights(
    frame: pd.DataFrame,
    score_col: str,
    strategy: str,
    *,
    id_col: str = "security_id",
    weight_col: str = "weight",
    return_col: str = "ret_exc_lead1m",
    quantile: float = 0.1,
    min_side: int = 20,
) -> pd.Series:
    """Return frozen signed target weights for one month.

    Long-short weights sum to zero with one dollar in each leg. Long-only
    weights sum to one. Formation uses only the identifier, score, and
    formation-date weight; next-month return availability is deliberately not
    an eligibility condition. An empty series means the portfolio could not
    form.
    """
    del return_col  # kept in the public signature for backward compatibility
    x = frame[[id_col, score_col, weight_col]].copy()
    x = x.replace([np.inf, -np.inf], np.nan).dropna()
    x = x[x[weight_col] > 0]
    x = x.drop_duplicates(id_col, keep="last").set_index(id_col)
    if strategy == "long_only_top5_equal_weighted":
        if len(x) < max(5, min_side):
            return pd.Series(dtype="float64")
        selected = (
            x.assign(_id_sort=x.index.astype(str))
            .sort_values([score_col, "_id_sort"], ascending=[False, True], kind="mergesort")
            .head(5)
        )
        return pd.Series(1.0 / len(selected), index=selected.index, dtype="float64")
    if strategy == "long_only_top_decile_value_weighted":
        if len(x) < max(10, min_side):
            return pd.Series(dtype="float64")
        n_select = max(min_side, int(np.floor(quantile * len(x))))
        if n_select > len(x):
            return pd.Series(dtype="float64")
        selected = (
            x.assign(_id_sort=x.index.astype(str))
            .sort_values([score_col, "_id_sort"], ascending=[False, True], kind="mergesort")
            .head(n_select)
        )
        weights = selected[weight_col].astype("float64")
        return weights / weights.sum()
    if len(x) < max(2 * min_side, 10):
        return pd.Series(dtype="float64")
    n_side = max(min_side, int(np.floor(quantile * len(x))))
    if 2 * n_side > len(x):
        return pd.Series(dtype="float64")
    ordered = x.assign(_id_sort=x.index.astype(str)).sort_values(
        [score_col, "_id_sort"], ascending=[True, True], kind="mergesort"
    )
    low = ordered.head(n_side)
    high = ordered.tail(n_side)
    if not low.index.intersection(high.index).empty:
        raise RuntimeError("deterministic long and short legs overlap")
    long_w = high[weight_col].astype("float64")
    short_w = low[weight_col].astype("float64")
    long_w = long_w / long_w.sum()
    short_w = -short_w / short_w.sum()
    return pd.concat([long_w, short_w]).groupby(level=0).sum().sort_index()


def realized_portfolio_return(
    weights: pd.Series,
    frame: pd.DataFrame,
    *,
    id_col: str = "security_id",
    return_col: str = "ret_exc_lead1m",
    missing_return_policy: str = "zero",
) -> float:
    """Realize a frozen portfolio without conditioning formation on t+1 data.

    A held security whose next-month return is missing receives either zero
    (the primary protocol) or a position-adverse unit move: -100% for a long
    and +100% for a short. Both preserve ex-ante weights and avoid reweighting
    on future coverage.
    """
    if weights.empty:
        return float("nan")
    returns = (
        frame[[id_col, return_col]]
        .drop_duplicates(id_col, keep="last")
        .set_index(id_col)[return_col]
        .astype("float64")
    )
    aligned = returns.reindex(weights.index)
    missing = aligned.isna()
    if missing_return_policy == "zero":
        aligned = aligned.fillna(0.0)
    elif missing_return_policy == "adverse_100":
        aligned = aligned.copy()
        aligned.loc[missing] = -np.sign(weights.loc[missing])
    else:
        raise ValueError(f"unknown missing_return_policy: {missing_return_policy}")
    return float(np.dot(weights.to_numpy(dtype="float64"), aligned.to_numpy(dtype="float64")))


def missing_return_gross_weight(
    weights: pd.Series,
    frame: pd.DataFrame,
    *,
    id_col: str = "security_id",
    return_col: str = "ret_exc_lead1m",
) -> float:
    """Fraction of absolute portfolio weight assigned to missing t+1 returns."""
    if weights.empty:
        return float("nan")
    returns = (
        frame[[id_col, return_col]]
        .drop_duplicates(id_col, keep="last")
        .set_index(id_col)[return_col]
    )
    missing = returns.reindex(weights.index).isna()
    gross = float(weights.abs().sum())
    if gross <= 0:
        return float("nan")
    return float(weights.abs().loc[missing].sum() / gross)


def drift_weights(previous: pd.Series, previous_returns: pd.Series) -> pd.Series:
    """Drift risky-asset weights to the next pretrade instant.

    Weights are expressed per dollar of strategy NAV and ``previous_returns``
    must contain total security returns over the holding month. Dividing all
    risky holdings by the same post-return NAV retains changes in long and
    short gross exposure; the subsequent L1 trade therefore includes exposure
    restoration.
    """
    if previous.empty:
        return previous.copy()
    r = previous_returns.reindex(previous.index).fillna(0.0)
    if (r < -1.0).any():
        raise ValueError("total security return below -100%")
    portfolio_return = float(np.dot(previous.to_numpy(dtype="float64"), r.to_numpy(dtype="float64")))
    post_return_nav = 1.0 + portfolio_return
    if not np.isfinite(post_return_nav) or post_return_nav <= 0:
        raise ValueError("strategy NAV is nonpositive after the realized return")
    return (previous * (1.0 + r) / post_return_nav).sort_index()


def traded_notional(current: pd.Series, pretrade: pd.Series) -> float:
    """Total absolute signed-weight change per dollar of strategy NAV."""
    if current.empty and pretrade.empty:
        return float("nan")
    if pretrade.empty:
        return float(current.abs().sum())
    if current.empty:
        return float(pretrade.abs().sum())
    idx = current.index.union(pretrade.index)
    return float((current.reindex(idx, fill_value=0.0) - pretrade.reindex(idx, fill_value=0.0)).abs().sum())


def weight_diagnostics(weights: pd.Series) -> dict[str, float | int]:
    if weights.empty:
        return {
            "n_long": 0,
            "n_short": 0,
            "max_abs_weight": float("nan"),
            "weight_hhi": float("nan"),
            "gross_exposure": float("nan"),
        }
    return {
        "n_long": int((weights > 0).sum()),
        "n_short": int((weights < 0).sum()),
        "max_abs_weight": float(weights.abs().max()),
        "weight_hhi": float(np.square(weights.to_numpy(dtype="float64")).sum()),
        "gross_exposure": float(weights.abs().sum()),
    }


def multiplicity_adjustments(
    p_values: Mapping[str, float],
    *,
    planned_m: int | None = None,
) -> pd.DataFrame:
    """Return Holm, BH, and BY adjusted values, padding failures with p=1."""
    ids = list(p_values)
    raw = np.array([p_values[key] for key in ids], dtype="float64")
    raw = np.where(np.isfinite(raw), np.clip(raw, 0.0, 1.0), 1.0)
    m = len(raw) if planned_m is None else int(planned_m)
    if m < len(raw):
        raise ValueError("planned_m cannot be smaller than observed hypotheses")
    padded = np.concatenate([raw, np.ones(m - len(raw), dtype="float64")])
    holm = multipletests(padded, alpha=0.05, method="holm")[1][: len(raw)]
    bh = multipletests(padded, alpha=0.05, method="fdr_bh")[1][: len(raw)]
    by = multipletests(padded, alpha=0.05, method="fdr_by")[1][: len(raw)]
    return pd.DataFrame(
        {
            "candidate_id": ids,
            "p_value_two_sided": raw,
            "holm_p_value": holm,
            "bh_q_value": bh,
            "by_q_value": by,
        }
    )


def moving_block_indices(
    n_obs: int,
    block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if n_obs <= 0 or block_length <= 0:
        raise ValueError("n_obs and block_length must be positive")
    n_blocks = int(np.ceil(n_obs / block_length))
    starts = rng.integers(0, n_obs, size=n_blocks)
    blocks = [(start + np.arange(block_length)) % n_obs for start in starts]
    return np.concatenate(blocks)[:n_obs]


def paired_block_bootstrap_alpha(
    frame: pd.DataFrame,
    candidate_cols: list[str],
    factor_cols: list[str],
    *,
    n_bootstrap: int = 2000,
    block_length: int = 6,
    seed: int = 20260802,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Re-estimate all alpha coefficients under paired moving-block draws.

    The family uses a common complete calendar. Studentization uses each
    candidate's original HAC standard error; the regression coefficients are
    re-estimated in every draw. This preserves cross-candidate dependence and
    provides a transparent single-step max-|t| adjustment.
    """
    cols = [*candidate_cols, *factor_cols]
    xframe = frame[cols].replace([np.inf, -np.inf], np.nan).dropna().astype("float64")
    if len(xframe) <= len(factor_cols) + 12:
        raise ValueError("insufficient common observations for block bootstrap")
    y = xframe[candidate_cols].to_numpy(dtype="float64")
    factors = xframe[factor_cols].to_numpy(dtype="float64")
    design = np.column_stack([np.ones(len(xframe)), factors])
    coef = np.linalg.lstsq(design, y, rcond=None)[0]
    alpha_hat = coef[0]
    se = np.empty(len(candidate_cols), dtype="float64")
    observed_t = np.empty(len(candidate_cols), dtype="float64")
    for j, candidate in enumerate(candidate_cols):
        tmp = xframe[[candidate, *factor_cols]].copy()
        tmp.insert(0, "month", pd.date_range("2000-01-31", periods=len(tmp), freq="ME"))
        result = alpha_regression(tmp, candidate, factor_cols)
        se[j] = result.alpha_se_monthly
        observed_t[j] = result.alpha_t_hac
    rng = np.random.default_rng(seed)
    alpha_boot = np.empty((n_bootstrap, len(candidate_cols)), dtype="float64")
    for b in range(n_bootstrap):
        idx = moving_block_indices(len(xframe), block_length, rng)
        xb = design[idx]
        yb = y[idx]
        alpha_boot[b] = np.linalg.lstsq(xb, yb, rcond=None)[0][0]
    centered_t = (alpha_boot - alpha_hat[None, :]) / se[None, :]
    max_abs = np.nanmax(np.abs(centered_t), axis=1)
    max_one_sided = np.nanmax(centered_t, axis=1)
    max_abs_p = np.array(
        [(1.0 + np.sum(max_abs >= abs(t))) / (n_bootstrap + 1.0) for t in observed_t]
    )
    individual_p = np.array(
        [
            (1.0 + np.sum(np.abs(centered_t[:, j]) >= abs(observed_t[j])))
            / (n_bootstrap + 1.0)
            for j in range(len(candidate_cols))
        ]
    )
    simultaneous_critical = float(np.quantile(max_abs, 0.95))
    rows = []
    for j, candidate in enumerate(candidate_cols):
        rows.append(
            {
                "candidate_id": candidate,
                "bootstrap_alpha_point_monthly": float(alpha_hat[j]),
                "bootstrap_alpha_ci_low_annualized": float(12.0 * np.quantile(alpha_boot[:, j], 0.025)),
                "bootstrap_alpha_ci_high_annualized": float(12.0 * np.quantile(alpha_boot[:, j], 0.975)),
                "bootstrap_p_value_two_sided": float(individual_p[j]),
                "max_abs_t_p_value": float(max_abs_p[j]),
                "simultaneous_ci_low_annualized": float(12.0 * (alpha_hat[j] - simultaneous_critical * se[j])),
                "simultaneous_ci_high_annualized": float(12.0 * (alpha_hat[j] + simultaneous_critical * se[j])),
            }
        )
    observed_max = float(np.nanmax(observed_t))
    reality_check_p = float(
        (1.0 + np.sum(max_one_sided >= observed_max)) / (n_bootstrap + 1.0)
    )
    metadata: dict[str, float | int] = {
        "n_common_months": int(len(xframe)),
        "n_candidates": int(len(candidate_cols)),
        "n_bootstrap": int(n_bootstrap),
        "block_length": int(block_length),
        "seed": int(seed),
        "simultaneous_critical_value": simultaneous_critical,
        "white_reality_check_style_p_value": reality_check_p,
    }
    return pd.DataFrame(rows), metadata


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    if total <= 0:
        return float("nan"), float("nan")
    p = successes / total
    z = float(stats.norm.ppf(0.5 + confidence / 2.0))
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    spread = z * sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denom
    return center - spread, center + spread
