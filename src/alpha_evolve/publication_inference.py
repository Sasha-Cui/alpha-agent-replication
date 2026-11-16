"""Paired economic bounds and dependence-aware inference with explicit estimands.

Sources: Politis & Romano (1994), DOI 10.1080/01621459.1994.10476870;
Newey & West (1987), DOI 10.2307/1913610; equivalence via Schuirmann (1987),
DOI 10.1007/BF01068419. Bootstrap inference is asymptotic, not an exact test.
"""

from __future__ import annotations
import numpy as np
from scipy.stats import norm


def stationary_indices(n, replicates, mean_block, rng):
    if n < 2 or replicates < 1 or not 1 <= mean_block <= n:
        raise ValueError("Invalid bootstrap dimensions")
    result = np.empty((replicates, n), dtype=int)
    result[:, 0] = rng.integers(n, size=replicates)
    for t in range(1, n):
        restart = rng.random(replicates) < 1 / mean_block
        result[:, t] = np.where(restart, rng.integers(n, size=replicates), (result[:, t - 1] + 1) % n)
    return result


def _bounds(estimate, draws, frequency, threshold):
    centered = np.asarray(draws) - estimate
    if not len(centered) or not np.isfinite(centered).all():
        raise ValueError("Invalid bootstrap distribution")
    lo95, hi95 = estimate - np.quantile(centered, [0.975, 0.025])
    lo90, hi90 = estimate - np.quantile(centered, [0.95, 0.05])
    se = float(np.std(draws, ddof=1)) * frequency
    effect = estimate * frequency
    p = float((1 + np.sum(np.abs(centered) >= abs(estimate))) / (len(draws) + 1))
    return {
        "annualized_arithmetic_effect": float(effect),
        "ci95_low": float(lo95 * frequency),
        "ci95_high": float(hi95 * frequency),
        "ci90_low": float(lo90 * frequency),
        "ci90_high": float(hi90 * frequency),
        "one_sided95_upper": float(hi90 * frequency),
        "bootstrap_p_two_sided": p,
        "bootstrap_se_annualized": se,
        "economic_margin_annualized": float(threshold),
        "equivalent_within_margin_tost5": bool(
            se > 1e-14 and lo90 * frequency > -threshold and hi90 * frequency < threshold
        ),
        "rules_out_positive_margin_one_sided5": bool(se > 1e-14 and hi90 * frequency < threshold),
        "degenerate_sampling_variation": bool(se <= 1e-14),
        "mde80_normal_approx_annualized": float((norm.ppf(0.975) + norm.ppf(0.8)) * se),
        "power_at_margin_normal_approx": float(
            norm.cdf(-norm.ppf(0.975) - threshold / se) + 1 - norm.cdf(norm.ppf(0.975) - threshold / se)
        )
        if se > 1e-14
        else None,
    }


def _mean_hac_se(values, lags):
    values = np.asarray(values, float)
    if values.ndim == 1:
        values = values[None, :]
    n = values.shape[1]
    centered = values - values.mean(axis=1, keepdims=True)
    meat = np.sum(centered**2, axis=1)
    for lag in range(1, min(lags, n - 1) + 1):
        meat += 2 * (1 - lag / (lags + 1)) * np.sum(centered[:, lag:] * centered[:, :-lag], axis=1)
    return np.sqrt(np.maximum(meat, 0) / (n * (n - 1)))


def paired_effect(left, right, frequency=12, mean_block=6, replicates=4999, seed=20260907, threshold=0.02, hac_lags=3):
    left = np.asarray(left, float)
    right = np.asarray(right, float)
    if left.ndim != 1 or left.shape != right.shape or len(left) < 12 or not np.isfinite(np.c_[left, right]).all():
        raise ValueError("At least 12 aligned finite paired observations required")
    difference = left - right
    rng = np.random.default_rng(seed)
    indexes = stationary_indices(len(left), replicates, mean_block, rng)
    resamples = difference[indexes]
    estimate = float(difference.mean())
    draws = resamples.mean(axis=1)
    se = float(_mean_hac_se(difference, hac_lags)[0])
    bootstrap_se = _mean_hac_se(resamples, hac_lags)
    if se > 1e-14:
        valid = bootstrap_se > 1e-14
        if valid.mean() < 0.95:
            raise ValueError("Too many degenerate studentization draws")
        adjusted_draws = estimate + (draws[valid] - estimate) / bootstrap_se[valid] * se
    else:
        adjusted_draws = draws
    result = _bounds(estimate, adjusted_draws, frequency, threshold)
    result.update(
        observations=len(left),
        frequency=frequency,
        mean_block=mean_block,
        bootstrap_replicates=replicates,
        seed=seed,
        hac_lags=hac_lags,
        hac_se_annualized=se * frequency,
        inference_method="stationary bootstrap-t with HAC studentization",
        estimand="annualized mean paired return difference; confidence interval is not a CAGR interval",
    )
    if np.all(left > -1) and np.all(right > -1):
        result["observed_cagr_difference"] = float(
            np.expm1(np.log1p(left).mean() * frequency) - np.expm1(np.log1p(right).mean() * frequency)
        )
    return result


def _design(y, factors):
    y = np.asarray(y, float)
    x = np.asarray(factors, float)
    if x.ndim == 1:
        x = x[:, None]
    if y.ndim != 1 or x.ndim != 2 or len(y) != len(x) or not np.isfinite(np.c_[y, x]).all():
        raise ValueError("Unaligned or nonfinite regression data")
    design = np.c_[np.ones(len(y)), x]
    if len(y) <= design.shape[1] + 2 or np.linalg.matrix_rank(design) < design.shape[1]:
        raise ValueError("Unrestricted factor alpha is not identified with this sample/rank")
    return y, design


def ols_alpha(y, factors, frequency=12, hac_lags=3):
    y, x = _design(y, factors)
    n, k = x.shape
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ beta
    score = x * residual[:, None]
    meat = score.T @ score
    lags = min(int(hac_lags), n - 1)
    for lag in range(1, lags + 1):
        gamma = score[lag:].T @ score[:-lag]
        meat += (1 - lag / (lags + 1)) * (gamma + gamma.T)
    inverse = np.linalg.inv(x.T @ x)
    cov = inverse @ meat @ inverse * (n / (n - k))
    se = float(np.sqrt(max(cov[0, 0], 0)))
    alpha = float(beta[0])
    t = alpha / se if se > 1e-14 else (0.0 if abs(alpha) < 1e-14 else np.sign(alpha) * np.inf)
    return {
        "annualized_alpha": alpha * frequency,
        "hac_se_annualized": se * frequency,
        "hac_t": float(t),
        "hac_p_normal": float(2 * norm.sf(abs(t))),
        "observations": n,
        "factor_count": k - 1,
        "design_rank": int(np.linalg.matrix_rank(x)),
        "hac_lags": lags,
        "betas": beta[1:].tolist(),
        "residual": residual,
        "fitted": x @ beta,
    }


def _alpha_and_hac_se(y, x, hac_lags):
    n, k = x.shape
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ beta
    # Only the intercept variance is needed. Project the score with the first
    # inverse-design row instead of constructing every covariance element.
    inverse_row = np.linalg.solve(x.T @ x, np.eye(k)[:, 0])
    score = (x @ inverse_row) * residual
    variance = float(score @ score)
    for lag in range(1, min(hac_lags, n - 1) + 1):
        variance += 2 * (1 - lag / (hac_lags + 1)) * float(score[lag:] @ score[:-lag])
    return float(beta[0]), float(np.sqrt(max(variance * n / (n - k), 0)))


def refitted_alpha_bootstrap(
    y, factors, frequency=12, mean_block=6, replicates=1999, seed=20260907, threshold=0.02, hac_lags=3
):
    y, design = _design(y, factors)
    estimate, se = _alpha_and_hac_se(y, design, hac_lags)
    indexes = stationary_indices(len(y), replicates, mean_block, np.random.default_rng(seed))
    draws = []
    invalid = 0
    for idx in indexes:
        x = design[idx]
        yy = y[idx]
        if np.linalg.matrix_rank(x) < x.shape[1]:
            invalid += 1
            continue
        # The full regression and its HAC scale are refitted in every draw.
        try:
            alpha, scale = _alpha_and_hac_se(yy, x, hac_lags)
        except np.linalg.LinAlgError:
            invalid += 1
            continue
        if se > 1e-14:
            if scale <= 1e-14:
                invalid += 1
                continue
            draws.append(estimate + (alpha - estimate) / scale * se)
        else:
            draws.append(alpha)
    if len(draws) < 0.95 * replicates:
        raise ValueError("Too many rank-deficient or degenerate bootstrap draws")
    result = _bounds(estimate, draws, frequency, threshold)
    result.update(
        observations=len(y),
        factor_count=design.shape[1] - 1,
        mean_block=mean_block,
        bootstrap_replicates=replicates,
        invalid_draws=invalid,
        seed=seed,
        hac_lags=hac_lags,
        hac_se_annualized=se * frequency,
        estimator_refitted_every_draw=True,
        inference_method="stationary bootstrap-t with HAC studentization",
        estimand="intercept conditional on this specified factor model; not unrestricted JKP132 unless all 132 factors are identified",
    )
    return result


def chronological_projection(y, factors, min_train=36, penalty=10.0, components=None):
    """Expanding training-only ridge/PCA reconstruction; intentionally no alpha p-value."""
    y = np.asarray(y, float)
    x = np.asarray(factors, float)
    if y.ndim != 1 or x.ndim != 2 or len(y) != len(x) or len(y) <= min_train or not np.isfinite(np.c_[y, x]).all():
        raise ValueError("Invalid chronological data")
    if penalty <= 0:
        raise ValueError("Positive ridge penalty required")
    predictions = np.full(len(y), np.nan)
    for end in range(min_train, len(y)):
        xx = x[:end]
        yy = y[:end]
        mean = xx.mean(axis=0)
        sd = xx.std(axis=0)
        sd = np.where(sd > 1e-12, sd, 1.0)
        z = (xx - mean) / sd
        current = (x[end] - mean) / sd
        if components is not None:
            if not 1 <= components < min(end, x.shape[1]):
                raise ValueError("Invalid PCA rank")
            basis = np.linalg.svd(z, full_matrices=False)[2][:components].T
            z = z @ basis
            current = current @ basis
        ym = yy.mean()
        centered = yy - ym
        # Dual solve is equivalent and stable when the number of factors exceeds history.
        if z.shape[1] > len(z):
            beta = z.T @ np.linalg.solve(z @ z.T + penalty * np.eye(len(z)), centered)
        else:
            beta = np.linalg.solve(z.T @ z + penalty * np.eye(z.shape[1]), z.T @ centered)
        predictions[end] = ym + current @ beta
    residual = y[min_train:] - predictions[min_train:]
    return {
        "predictions": predictions,
        "residual": residual,
        "evaluation_start_index": min_train,
        "evaluation_observations": len(residual),
        "mean_residual": float(residual.mean()),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "label": "regularized chronological reconstruction diagnostic; no unrestricted spanning-alpha inference",
        "penalty": penalty,
        "components": components,
    }


def holm_adjust(pvalues):
    p = np.asarray(pvalues, float)
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid p-values")
    order = np.argsort(p)
    adjusted = np.empty(len(p))
    adjusted[order] = np.minimum(1, np.maximum.accumulate((len(p) - np.arange(len(p))) * p[order]))
    return adjusted


def grouped_t_effect(left, right=None, factors=None, frequency=12, groups=4, threshold=0.02, confidence=0.99):
    """Contiguous-block estimator t interval (Ibragimov & Müller, 2010).

    Each block refits the entire low-dimensional estimator. Validity requires
    approximately independent, approximately normal block estimates; it is not
    a distribution-free finite-sample guarantee. The interval's point estimate
    is the mean of block estimates, reported separately from the full-sample fit.
    """
    from scipy.stats import t as student_t

    y = np.asarray(left, float)
    if right is not None:
        y = y - np.asarray(right, float)
    if y.ndim != 1 or not np.isfinite(y).all() or len(y) < groups * 3 or groups < 2:
        raise ValueError("Insufficient finite observations for grouped inference")
    if factors is not None:
        y, design = _design(y, factors)
        if min(len(block) for block in np.array_split(np.arange(len(y)), groups)) <= design.shape[1] + 2:
            raise ValueError("Block-level factor estimator is not identified with adequate residual degrees of freedom")
    blocks = np.array_split(np.arange(len(y)), groups)
    estimates = []
    for idx in blocks:
        if factors is None:
            estimate = float(y[idx].mean())
        else:
            if np.linalg.matrix_rank(design[idx]) < design.shape[1]:
                raise ValueError("Block-level rank deficiency")
            estimate = float(np.linalg.lstsq(design[idx], y[idx], rcond=None)[0][0])
        estimates.append(estimate)
    estimate = float(np.mean(estimates))
    se = float(np.std(estimates, ddof=1) / np.sqrt(groups))
    df = groups - 1
    statistic = estimate / se if se > 1e-14 else (0.0 if abs(estimate) < 1e-14 else np.sign(estimate) * np.inf)
    if not 0.95 <= confidence < 1:
        raise ValueError("Primary confidence must be at least 95%")
    primary_critical = student_t.ppf((1 + confidence) / 2, df)
    primary_low = (estimate - primary_critical * se) * frequency
    primary_high = (estimate + primary_critical * se) * frequency
    critical95 = student_t.ppf(0.975, df)
    critical90 = student_t.ppf(0.95, df)
    low95, high95 = (estimate - critical95 * se) * frequency, (estimate + critical95 * se) * frequency
    low90, high90 = (estimate - critical90 * se) * frequency, (estimate + critical90 * se) * frequency
    full = float(y.mean()) if factors is None else float(np.linalg.lstsq(design, y, rcond=None)[0][0])
    return {
        "annualized_arithmetic_effect": estimate * frequency,
        "full_sample_annualized_effect": full * frequency,
        "ci95_low": float(low95),
        "ci95_high": float(high95),
        "ci90_low": float(low90),
        "ci90_high": float(high90),
        "one_sided95_upper": float(high90),
        "primary_ci_low": float(primary_low),
        "primary_ci_high": float(primary_high),
        "primary_confidence": confidence,
        "margin_upper_bound": float(primary_high),
        "margin_upper_bound_nominal_one_sided_confidence": (1 + confidence) / 2,
        "group_t_p_two_sided": float(2 * student_t.sf(abs(statistic), df)),
        "group_t_statistic": float(statistic),
        "group_standard_error_annualized": se * frequency,
        "groups": groups,
        "degrees_of_freedom": df,
        "block_lengths": [len(i) for i in blocks],
        "block_estimates_annualized": (np.asarray(estimates) * frequency).tolist(),
        "observations": len(y),
        "factor_count": 0 if factors is None else design.shape[1] - 1,
        "economic_margin_annualized": threshold,
        "equivalent_within_margin_tost5": bool(se > 1e-14 and primary_low > -threshold and primary_high < threshold),
        "rules_out_positive_margin_one_sided5": bool(se > 1e-14 and primary_high < threshold),
        "degenerate_sampling_variation": bool(se <= 1e-14),
        "mde80_t_normal_approx_annualized": float((primary_critical + norm.ppf(0.8)) * se * frequency),
        "inference_method": "contiguous-group estimator t inference; all factor coefficients refitted within each block",
        "assumption": "approximately independent normal block estimates; assessed in explicit simulation cases, not guaranteed for every financial process",
    }
