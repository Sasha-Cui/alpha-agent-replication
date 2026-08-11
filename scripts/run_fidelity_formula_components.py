#!/usr/bin/env python3
"""Evaluate literal disclosed formula components on monthly JKP bars.

This is deliberately not a native-agent runner.  It preserves each published
operator tree while recording cadence, universe, and portfolio adaptations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from alpha_evolve.jkp import validate_columns  # noqa: E402
from alpha_evolve.paths import DEFAULT_JKP_USA  # noqa: E402


FORMULAS = {
    "efs_regime_switched_return_volatility": (
        "EFS Table VI, CSI300 formula 1",
        "cs_zscore((ts_mean(returns,30)+ts_decay_linear(returns,10))/(ts_std(returns,7)*ts_std(if_else(ts_momentum(prices,14)>0,ts_delay(returns,5),ts_delay(returns,30)),30)))",
        "returns, prices",
    ),
    "efs_multi_horizon_mean_volatility": (
        "EFS Table VI, CSI300 formula 2",
        "cs_zscore((ts_mean(returns,10)+ts_mean(returns,30))/(ts_std(returns,7)+ts_std(ts_delay(returns,14),30)))",
        "returns",
    ),
    "efs_skew_gated_breakout": (
        "EFS Table VI, US50 formula",
        "cs_zscore((ts_max(prices,30)-ts_decay_linear(prices,21))/((ts_std(returns,3)+ts_std(returns,30))*if_else(ts_skew(returns,14)<0,ts_std(returns,7),ts_std(returns,21))))",
        "returns, prices",
    ),
    "efs_decay_return_dispersion": (
        "EFS Table VI, HSI45 formula 1",
        "cs_zscore(ts_decay_linear(returns,30)/ts_std(ts_delta(returns,10)-ts_delta(returns,30),30))",
        "returns",
    ),
    "efs_regime_momentum_normalized_mean": (
        "EFS Table VI, HSI45 formula 2",
        "cs_rank(ts_mean(returns,14)/(ts_std(if_else(ts_momentum(prices,7)<0,ts_momentum(prices,21),ts_momentum(prices,3)),30)+ts_std(ts_delay(returns,7),21)))",
        "returns, prices",
    ),
    "quantevolver_return_sharpe_60": (
        "QuantEvolver released seed_candidates.yaml",
        "div(ts_mean(returns(60)),ts_std(returns(60)))",
        "returns",
    ),
    "quantevolver_price_zscore_reversal_120": (
        "QuantEvolver released seed_candidates.yaml",
        "neg(zscore(last(close(120)),close(120)))",
        "close",
    ),
    "quantevolver_return_log_volume_corr_60": (
        "QuantEvolver released seed_candidates.yaml",
        "corr(returns(60),log_arr(volume(60)))",
        "returns, volume",
    ),
    "alpha_jungle_volume_ma_diff": (
        "Alpha-Jungle Table 7, formula 4",
        "Diff(Ma(volume,20),3)/Ma(volume,60)",
        "volume",
    ),
    "alpha_jungle_multiscale_price_volume": (
        "Alpha-Jungle Table 7, formula 5",
        "Corr(Pct(close,10),Pct(volume,10),10)*Corr(Pct(close,30),Pct(volume,30),30)*Skew(volume,20)",
        "close, volume",
    ),
    "alpha_jungle_range_volume_interaction": (
        "Alpha-Jungle Table 7, formula 6",
        "Ma(Corr(volume,close,20)*Skew(high-low,20),10)",
        "close, high, low, volume",
    ),
    "quantagent_atr14_breakout_literal": (
        "QuantAgent Appendix A.1 VolatilityBreakoutSignal",
        "where(high>high.shift(1)+1.5*ATR14,(high-B)/ATR14,0).clip(lower=0)",
        "high, low, pre_close",
    ),
}

INPUT_COLUMNS = [
    "permno",
    "eom",
    "ret",
    "ret_exc_lead1m",
    "me",
    "prc",
    "prc_high",
    "prc_low",
    "tvol",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def roll(frame: pd.DataFrame, column: str, window: int, method: str) -> pd.Series:
    grouped = frame.groupby("permno", sort=False)[column]
    operator = {
        "mean": lambda x: x.rolling(window, min_periods=window).mean(),
        "std": lambda x: x.rolling(window, min_periods=window).std(ddof=1),
        "std0": lambda x: x.rolling(window, min_periods=window).std(ddof=0),
        "max": lambda x: x.rolling(window, min_periods=window).max(),
        "skew": lambda x: x.rolling(window, min_periods=window).skew(),
    }[method]
    return grouped.transform(operator)


def delay(frame: pd.DataFrame, column: str, periods: int) -> pd.Series:
    return frame.groupby("permno", sort=False)[column].shift(periods)


def momentum(frame: pd.DataFrame, column: str, periods: int) -> pd.Series:
    return frame[column] - delay(frame, column, periods)


def decay(frame: pd.DataFrame, column: str, window: int) -> pd.Series:
    weights = np.arange(1.0, window + 1.0)
    return frame.groupby("permno", sort=False)[column].transform(
        lambda x: x.rolling(window, min_periods=window).apply(
            lambda values: float(np.dot(values, weights) / weights.sum()), raw=True
        )
    )


def rolling_corr(
    frame: pd.DataFrame, left: str, right: str, window: int, *, source_fallback: bool = False
) -> pd.Series:
    result = pd.Series(np.nan, index=frame.index, dtype="float64")
    for _, group in frame.groupby("permno", sort=False):
        minimum = 2 if source_fallback else window
        correlation = group[left].rolling(window, min_periods=minimum).corr(group[right])
        if source_fallback:
            paired_count = group[[left, right]].notna().all(axis=1).rolling(window, min_periods=1).sum()
            left_std = group[left].rolling(window, min_periods=2).std(ddof=0)
            right_std = group[right].rolling(window, min_periods=2).std(ddof=0)
            valid = (paired_count >= 2) & (left_std >= 1e-12) & (right_std >= 1e-12)
            correlation = correlation.where(valid, 0.0)
        result.loc[group.index] = correlation.to_numpy()
    return result


def safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return (numerator / denominator.where(denominator.abs() > 1e-12)).replace([np.inf, -np.inf], np.nan)


def scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute the twelve disclosed formula trees without using future returns."""
    frame = frame.sort_values(["permno", "month"], kind="stable").copy()
    frame["returns"] = pd.to_numeric(frame["ret"], errors="coerce")
    frame["log_volume"] = np.log(pd.to_numeric(frame["tvol"], errors="coerce").abs().add(1e-8))
    # EFS formulas disclose prices; use the supplied JKP close proxy directly.
    frame["prices"] = pd.to_numeric(frame["prc"], errors="coerce").abs()
    # QuantEvolver's evaluator defines returns from close, not total returns.
    frame["close"] = pd.to_numeric(frame["prc"], errors="coerce").abs()
    previous_close = frame.groupby("permno", sort=False)["close"].shift(1)
    frame["qe_returns"] = (frame["close"] - previous_close) / (previous_close + 1e-8)

    means: dict[int, pd.Series] = {}
    stds: dict[int, pd.Series] = {}
    for window in (3, 7, 10, 14, 21, 30, 60):
        means[window] = roll(frame, "returns", window, "mean")
        stds[window] = roll(frame, "returns", window, "std")

    d5, d7, d14, d30 = (delay(frame, "returns", value) for value in (5, 7, 14, 30))
    p3, p7, p14, p21 = (momentum(frame, "prices", value) for value in (3, 7, 14, 21))

    switched = d5.where(p14 > 0, d30)
    switched_std30 = switched.groupby(frame["permno"], sort=False).transform(
        lambda x: x.rolling(30, min_periods=30).std(ddof=1)
    )
    frame["efs_regime_switched_return_volatility"] = safe_div(
        means[30] + decay(frame, "returns", 10), stds[7] * switched_std30
    )

    d14_std30 = d14.groupby(frame["permno"], sort=False).transform(lambda x: x.rolling(30, min_periods=30).std(ddof=1))
    frame["efs_multi_horizon_mean_volatility"] = safe_div(means[10] + means[30], stds[7] + d14_std30)

    skew14 = roll(frame, "returns", 14, "skew")
    gated_vol = stds[7].where(skew14 < 0, stds[21])
    frame["efs_skew_gated_breakout"] = safe_div(
        roll(frame, "prices", 30, "max") - decay(frame, "prices", 21),
        (stds[3] + stds[30]) * gated_vol,
    )

    delta = momentum(frame, "returns", 10) - momentum(frame, "returns", 30)
    delta_std30 = delta.groupby(frame["permno"], sort=False).transform(
        lambda x: x.rolling(30, min_periods=30).std(ddof=1)
    )
    frame["efs_decay_return_dispersion"] = safe_div(decay(frame, "returns", 30), delta_std30)

    regime_momentum = p21.where(p7 < 0, p3)
    regime_std30 = regime_momentum.groupby(frame["permno"], sort=False).transform(
        lambda x: x.rolling(30, min_periods=30).std(ddof=1)
    )
    d7_std21 = d7.groupby(frame["permno"], sort=False).transform(lambda x: x.rolling(21, min_periods=21).std(ddof=1))
    frame["efs_regime_momentum_normalized_mean"] = safe_div(means[14], regime_std30 + d7_std21)

    qe_mean60 = roll(frame, "qe_returns", 60, "mean")
    qe_std60 = roll(frame, "qe_returns", 60, "std0") + 1e-8
    qe_close_mean120 = roll(frame, "close", 120, "mean")
    qe_close_std120 = roll(frame, "close", 120, "std0")
    frame["quantevolver_return_sharpe_60"] = qe_mean60 / (qe_std60.abs() + 1e-8)
    frame["quantevolver_price_zscore_reversal_120"] = -((frame["close"] - qe_close_mean120) / (qe_close_std120 + 1e-8))
    frame["quantevolver_return_log_volume_corr_60"] = rolling_corr(
        frame, "qe_returns", "log_volume", 60, source_fallback=True
    )

    frame["volume"] = pd.to_numeric(frame["tvol"], errors="coerce")
    volume_ma20 = roll(frame, "volume", 20, "mean")
    volume_ma60 = roll(frame, "volume", 60, "mean")
    volume_ma20_lag3 = volume_ma20.groupby(frame["permno"], sort=False).shift(3)
    frame["alpha_jungle_volume_ma_diff"] = safe_div(volume_ma20 - volume_ma20_lag3, volume_ma60)

    close_pct10 = safe_div(frame["close"], delay(frame, "close", 10)) - 1.0
    close_pct30 = safe_div(frame["close"], delay(frame, "close", 30)) - 1.0
    volume_pct10 = safe_div(frame["volume"], delay(frame, "volume", 10)) - 1.0
    volume_pct30 = safe_div(frame["volume"], delay(frame, "volume", 30)) - 1.0
    temporary = frame[["permno"]].copy()
    temporary["c10"], temporary["v10"] = close_pct10, volume_pct10
    temporary["c30"], temporary["v30"] = close_pct30, volume_pct30
    corr10 = rolling_corr(temporary, "c10", "v10", 10)
    corr30 = rolling_corr(temporary, "c30", "v30", 30)
    frame["alpha_jungle_multiscale_price_volume"] = corr10 * corr30 * roll(frame, "volume", 20, "skew")

    frame["high"] = pd.to_numeric(frame["prc_high"], errors="coerce").abs()
    frame["low"] = pd.to_numeric(frame["prc_low"], errors="coerce").abs()
    range_frame = frame.assign(price_range=frame["high"] - frame["low"])
    range_skew20 = roll(range_frame, "price_range", 20, "skew")
    volume_close_corr20 = rolling_corr(frame, "volume", "close", 20)
    frame["range_volume_raw"] = volume_close_corr20 * range_skew20
    frame["alpha_jungle_range_volume_interaction"] = roll(frame, "range_volume_raw", 10, "mean")

    # Preserve the source literally: pre_close is itself the lagged close, and
    # the printed code shifts pre_close once again, yielding a two-bar lag.
    double_lag_close = delay(frame, "close", 2)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - double_lag_close).abs(),
            (frame["low"] - double_lag_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["true_range"] = true_range
    atr14 = roll(frame, "true_range", 14, "mean")
    barrier = delay(frame, "high", 1) + 1.5 * atr14
    breakout = safe_div(frame["high"] - barrier, atr14).where(frame["high"] > barrier, 0.0)
    frame["quantagent_atr14_breakout_literal"] = breakout.clip(lower=0.0).fillna(0.0)
    frame[list(FORMULAS)] = frame[list(FORMULAS)].replace([np.inf, -np.inf], np.nan)
    return frame


def apply_efs_cross_sectional_roots(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply EFS root operators within the declared monthly stock universe."""
    result = frame.copy()
    zscore_ids = (
        "efs_regime_switched_return_volatility",
        "efs_multi_horizon_mean_volatility",
        "efs_skew_gated_breakout",
        "efs_decay_return_dispersion",
    )
    for candidate_id in zscore_ids:
        values = pd.to_numeric(result[candidate_id], errors="coerce")
        means = values.groupby(result["month"], sort=False).transform("mean")
        stds = values.groupby(result["month"], sort=False).transform(lambda x: x.std(ddof=0))
        result[candidate_id] = (values - means) / stds.where(stds > 1e-12)
    rank_id = "efs_regime_momentum_normalized_mean"
    ranks = result.groupby("month", sort=False)[rank_id].rank(method="average", pct=True)
    result[rank_id] = 2.0 * (ranks - 0.5)
    return result


def portfolio_targets(
    frame: pd.DataFrame, candidate_id: str, top_m: int
) -> tuple[pd.DataFrame, dict[int, float], str, int, int]:
    eligible = (
        frame.dropna(subset=[candidate_id])
        .sort_values([candidate_id, "permno"], ascending=[False, True], kind="stable")
        .copy()
    )
    if candidate_id.startswith("quantevolver_"):
        side_size = len(eligible) // 5
        if side_size < 1:
            return eligible.iloc[0:0], {}, "source_top_bottom_quintile_equal_weight", 0, 0
        long_side = eligible.head(side_size)
        short_side = eligible.sort_values([candidate_id, "permno"], ascending=[True, True], kind="stable").head(
            side_size
        )
        selected = pd.concat([long_side, short_side], ignore_index=False)
        target = {
            **{int(value): 1.0 / side_size for value in long_side["permno"]},
            **{int(value): -1.0 / side_size for value in short_side["permno"]},
        }
        return selected, target, "source_top_bottom_quintile_equal_weight", side_size, side_size
    selected = eligible.head(top_m)
    if candidate_id == "quantagent_atr14_breakout_literal":
        eligible = eligible[eligible[candidate_id] > 0]
        selected = eligible.head(top_m)
        count = len(selected)
        rule = "researcher_positive_top_m_equal_weight"
        if count == 0:
            return selected, {}, rule, 0, 0
        target = {int(value): 1.0 / count for value in selected["permno"]}
        return selected, target, rule, count, 0

    if len(selected) < top_m:
        return eligible.iloc[0:0], {}, "researcher_top_m_equal_weight", 0, 0
    target = {int(value): 1.0 / top_m for value in selected["permno"]}
    return selected, target, "researcher_top_m_equal_weight", top_m, 0


def top_path(
    frame: pd.DataFrame, candidate_id: str, top_m: int, cost_bps: float
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    path_rows: list[dict[str, object]] = []
    holding_rows: list[dict[str, object]] = []
    prior_weights: dict[int, float] = {}
    prior_returns: dict[int, float] = {}
    diagnostics: dict[str, object] = {
        "candidate_id": candidate_id,
        "candidate_months_considered": 0,
        "n_path_months": 0,
        "n_complete_case_months": 0,
        "n_imputed_months": 0,
        "n_imputed_holdings": 0,
        "total_imputed_target_weight": 0.0,
        "n_omitted_no_calendar_horizon": 0,
        "n_omitted_no_target": 0,
        "n_omitted_no_observed_required_leg": 0,
    }
    is_quantevolver = candidate_id.startswith("quantevolver_")
    is_quantagent = candidate_id == "quantagent_atr14_breakout_literal"
    for month, month_frame in frame.groupby("month", sort=True):
        diagnostics["candidate_months_considered"] += 1
        if not bool(month_frame["lead_is_consecutive"].fillna(False).any()):
            diagnostics["n_omitted_no_calendar_horizon"] += 1
            prior_weights = {}
            prior_returns = {}
            continue
        selected, target, portfolio_rule_id, long_count, short_count = portfolio_targets(
            month_frame, candidate_id, top_m
        )
        if not target and not is_quantagent:
            diagnostics["n_omitted_no_target"] += 1
            prior_weights = {}
            prior_returns = {}
            continue

        selected_target = selected["permno"].map(target).astype("float64")
        selected_excess = pd.to_numeric(selected["ret_exc_lead1m"], errors="coerce")
        selected_total = pd.to_numeric(selected["ret_lead1m"], errors="coerce")
        selected_observed = (
            selected["lead_is_consecutive"].fillna(False) & selected_excess.notna() & selected_total.notna()
        )
        effective_excess = selected_excess.copy()
        effective_total = selected_total.copy()
        leg_masks: list[pd.Series] = []
        if target:
            leg_masks.append(selected_target > 0)
            if is_quantevolver:
                leg_masks.append(selected_target < 0)
        missing_required_leg = any(not bool((leg & selected_observed).any()) for leg in leg_masks)
        if missing_required_leg:
            diagnostics["n_omitted_no_observed_required_leg"] += 1
            prior_weights = {}
            prior_returns = {}
            continue
        for leg in leg_masks:
            observed_leg = leg & selected_observed
            imputed_leg = leg & ~selected_observed
            if bool(imputed_leg.any()):
                effective_excess.loc[imputed_leg] = selected_excess.loc[observed_leg].mean()
                effective_total.loc[imputed_leg] = selected_total.loc[observed_leg].mean()

        imputed = ~selected_observed
        n_imputed = int(imputed.sum())
        imputed_target_weight = float(selected_target.loc[imputed].abs().sum())
        complete_case = n_imputed == 0
        if prior_weights:
            denominator = 1.0 + sum(weight * prior_returns.get(key, 0.0) for key, weight in prior_weights.items())
            drift = {
                key: weight * (1.0 + prior_returns.get(key, 0.0)) / denominator for key, weight in prior_weights.items()
            }
        else:
            drift = {}
        turnover = sum(abs(target.get(key, 0.0) - drift.get(key, 0.0)) for key in set(target) | set(drift))
        gross = float(np.dot(selected_target, effective_excess))
        path_rows.append(
            {
                "candidate_id": candidate_id,
                "formation_month": pd.Timestamp(month),
                "month": pd.Timestamp(month) + pd.offsets.MonthEnd(1),
                "gross_excess_return": gross,
                "traded_notional": turnover,
                "cost_bps_one_way": cost_bps,
                "net_excess_return": gross - cost_bps / 10000.0 * turnover,
                "n_holdings": len(target),
                "n_selected": len(target),
                "n_observed": int(selected_observed.sum()),
                "n_imputed": n_imputed,
                "n_long": long_count,
                "n_short": short_count,
                "n_observed_long": int(((selected_target > 0) & selected_observed).sum()),
                "n_observed_short": int(((selected_target < 0) & selected_observed).sum()),
                "imputed_target_weight": imputed_target_weight,
                "complete_case_realization": complete_case,
                "portfolio_rule_id": portfolio_rule_id,
            }
        )
        effective_excess_by_permno = {
            int(permno): float(value) for permno, value in zip(selected["permno"], effective_excess)
        }
        effective_total_by_permno = {
            int(permno): float(value) for permno, value in zip(selected["permno"], effective_total)
        }
        observed_permnos = set(int(value) for value in selected.loc[selected_observed, "permno"])
        for record in selected[["permno", candidate_id]].to_dict("records"):
            permno = int(record["permno"])
            observed = permno in observed_permnos
            holding_rows.append(
                {
                    "candidate_id": candidate_id,
                    "formation_month": pd.Timestamp(month),
                    "permno": permno,
                    "score": float(record[candidate_id]),
                    "target_weight": target[permno],
                    "realized_return_weight": target[permno],
                    "realized_return_observed": observed,
                    "return_was_imputed": not observed,
                    "imputed_excess_return": np.nan if observed else effective_excess_by_permno[permno],
                    "imputed_total_return": np.nan if observed else effective_total_by_permno[permno],
                    "effective_excess_return": effective_excess_by_permno[permno],
                    "effective_total_return": effective_total_by_permno[permno],
                }
            )
        diagnostics["n_path_months"] += 1
        if complete_case:
            diagnostics["n_complete_case_months"] += 1
        else:
            diagnostics["n_imputed_months"] += 1
            diagnostics["n_imputed_holdings"] += n_imputed
            diagnostics["total_imputed_target_weight"] += imputed_target_weight
        prior_weights = target
        prior_returns = {int(permno): float(value) for permno, value in zip(selected["permno"], effective_total)}
    return pd.DataFrame(path_rows), pd.DataFrame(holding_rows), diagnostics


def build(args: argparse.Namespace) -> dict[str, object]:
    validate_columns(args.usa_path, INPUT_COLUMNS)
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    warmup = start - pd.offsets.MonthEnd(130)
    raw = pd.read_parquet(
        args.usa_path,
        columns=INPUT_COLUMNS,
        filters=[("eom", ">=", warmup), ("eom", "<=", end)],
    )
    raw["month"] = pd.to_datetime(raw["eom"], errors="coerce") + pd.offsets.MonthEnd(0)
    raw["me"] = pd.to_numeric(raw["me"], errors="coerce")
    raw = raw.sort_values(["permno", "month"], kind="stable")
    next_month = raw.groupby("permno", sort=False)["month"].shift(-1)
    raw["ret_lead1m"] = raw.groupby("permno", sort=False)["ret"].shift(-1)
    raw["lead_is_consecutive"] = next_month.eq(raw["month"] + pd.offsets.MonthEnd(1))
    raw = scores(raw)
    raw = raw[(raw["month"] >= start) & (raw["month"] <= end)]
    raw["size_rank"] = raw.groupby("month")["me"].rank(method="first", ascending=False)
    raw = raw[(raw["me"] > 0) & (raw["size_rank"] <= args.top_n)].copy()

    raw = apply_efs_cross_sectional_roots(raw)
    paths, holdings, realization_diagnostics = [], [], []
    for candidate_id in FORMULAS:
        path, held, diagnostics = top_path(raw, candidate_id, args.top_m, args.cost_bps)
        paths.append(path)
        holdings.append(held)
        realization_diagnostics.append(diagnostics)
    returns = pd.concat(paths, ignore_index=True)
    held = pd.concat(holdings, ignore_index=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    returns.to_csv(args.out_dir / "monthly_return_paths.csv", index=False)
    held.to_csv(args.out_dir / "formation_holdings.csv", index=False)

    ledger_rows = []
    for candidate_id, (source, expression, inputs) in FORMULAS.items():
        if candidate_id.startswith("quantevolver_"):
            grade = "B"
            component_fidelity = "source_disclosed_operator_tree_monthly_adaptation"
            grade_scope = "semantics_pinned_disclosed_formula_component_only"
            portfolio_rule = "monthly equal-mean top/bottom 20% long-short"
            portfolio_support = "released equal-mean top/bottom-quintile legs preserved; unlike source pair/dropna before ranking, this runner selects ex ante and imputes missing selected returns to the same-leg observed mean without altering weights"
            operator_convention = "close=abs(prc); released returns/std/div/zscore epsilons=1e-8; log_volume=log(abs(tvol)+1e-8); Pearson corr returns 0 for <2 or std<1e-12"
            material_deviation = "60/120 source bars become months; evolution and prediction model omitted"
        elif candidate_id.startswith("efs_"):
            grade = "B-conditional"
            component_fidelity = "conditional_operator_tree_monthly_adaptation"
            grade_scope = "formula_tree_with_researcher_set_m_and_equal_weights"
            portfolio_rule = f"monthly equal-weight long-only top-{args.top_m}"
            portfolio_support = "source supports long-only top-m; researcher sets m=10 and equal weights"
            operator_convention = "prices=abs(prc); sample time-series std; cs_zscore uses monthly population std; cs_rank is centered percentile rank; differences for delta/momentum; decay weights 1..n"
            material_deviation = "daily bars become monthly U.S. JKP bars; researcher sets m=10 and equal weights"
        elif candidate_id.startswith("alpha_jungle_"):
            grade = "C-conditional"
            component_fidelity = "conditional_reconstructed_formula_monthly_adaptation"
            grade_scope = "reconstructed_operators_and_researcher_portfolio_only"
            portfolio_rule = f"monthly equal-weight long-only top-{args.top_m}"
            portfolio_support = "researcher supplied; source formula normally feeds a daily ML model"
            operator_convention = "Pct=x/x.shift(n)-1; Diff=x-x.shift(n); reconstructed rolling operators"
            material_deviation = "daily China bars become U.S. months; MCTS and prediction model omitted"
        else:
            grade = "C-conditional"
            component_fidelity = "conditional_literal_signal_monthly_adaptation"
            grade_scope = "signal_with_researcher_portfolio_only"
            portfolio_rule = (
                f"monthly equal-weight long-only up to top-{args.top_m} strictly positive signals; cash if none"
            )
            portfolio_support = "researcher supplied; zero scores are no-trade because source discloses a nonnegative breakout signal but no portfolio rule"
            operator_convention = "pre_close.shift(1) preserved as two-bar close lag; rolling-mean ATR14"
            material_deviation = "daily bars become months; surrounding self-improving agent omitted"
        ledger_rows.append(
            {
                "candidate_id": candidate_id,
                "source_anchor": source,
                "exact_source_expression": expression,
                "source_inputs": inputs,
                "grade": grade,
                "component_fidelity": component_fidelity,
                "grade_scope": grade_scope,
                "formula_tree_preserved": True,
                "cadence_change": "source daily/intraday bars are replaced by monthly JKP bars",
                "universe_change": f"source universe to monthly top-{args.top_n} U.S. equities",
                "portfolio_rule": portfolio_rule,
                "portfolio_rule_source_support": portfolio_support,
                "operator_and_input_convention": operator_convention,
                "known_material_deviation": material_deviation,
                "realized_return_handling": (
                    "analytical missing-data convention: targets use the full scored formation universe; missing/nonconsecutive selected holdings receive the observed same-leg mean for both excess and total return without reranking, substitution, or weight changes; an empty required leg omits the candidate-month and resets state"
                ),
                "native_agent_replication": False,
                "full_search_or_training_pipeline_reproduced": False,
                "mapping_frozen_before_outcomes": False,
                "independent_outcome_blind_second_coder": False,
                "admissible_claim": (
                    "performance of a disclosed formula component after explicit monthly, "
                    "universe, and portfolio adaptations"
                ),
                "negative_evidence_boundary": (
                    "failure may not be attributed to the source agent, native market/cadence, "
                    "search or training procedure, or paper-level performance claim"
                ),
            }
        )
    pd.DataFrame(ledger_rows).to_csv(args.out_dir / "formula_fidelity_ledger.csv", index=False)
    output_sha256 = {
        name: sha256(args.out_dir / name)
        for name in (
            "monthly_return_paths.csv",
            "formation_holdings.csv",
            "formula_fidelity_ledger.csv",
        )
    }
    diagnostics_by_candidate = {
        str(item["candidate_id"]): {key: value for key, value in item.items() if key != "candidate_id"}
        for item in realization_diagnostics
    }
    manifest = {
        "input_path": str(args.usa_path),
        "input_sha256": sha256(args.usa_path),
        "start": args.start,
        "end": args.end,
        "top_n": args.top_n,
        "top_m": args.top_m,
        "cost_bps_one_way": args.cost_bps,
        "n_candidates": len(FORMULAS),
        "n_return_rows": len(returns),
        "n_complete_case_candidate_months": int(returns["complete_case_realization"].sum()),
        "n_imputed_candidate_months": int((~returns["complete_case_realization"]).sum()),
        "n_imputed_holdings": int(returns["n_imputed"].sum()),
        "total_imputed_target_weight": float(returns["imputed_target_weight"].sum()),
        "realization_diagnostics_by_candidate": diagnostics_by_candidate,
        "output_sha256": output_sha256,
        "scope_warning": (
            "No native agent is reproduced; source-disclosed formula components or strings are tested under declared conventions."
        ),
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usa-path", type=Path, default=DEFAULT_JKP_USA)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--start", default="1999-07-31")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--top-n", type=int, default=1000)
    parser.add_argument("--top-m", type=int, default=10)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    args = parser.parse_args()
    print(json.dumps(build(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
