#!/usr/bin/env python3
"""Evaluate the frozen AlphaAgent six-factor source pool on monthly U.S./JKP data."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm

from alpha_evolve.headline_backtest import build_strategy_path, return_statistics
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


FEATURES = [
    "moving_average_trend_reversal",
    "candlestick_volume_momentum",
    "amplitude_risk_momentum",
    "trading_volume_pattern",
    "volume_spike_confirmation",
    "stable_mean_reversion",
]
EXPRESSIONS = [
    "(0.3 * RANK($open)) + (0.2 * SUM($volume, 10)) + (0.2 * EMA($close, 20)) + (0.3 * (TS_RANK($high - $low, 5) > 0 ? 1 : 0))",
    "(0.25 * SUM($volume, 5)) + (0.35 * EMA($close, 10)) + (0.4 * (TS_RANK($close - $open, 15) > 0 ? 1 : 0))",
    "CORR($close - $open, $high - $low, 20)",
    "CORR($high - $low, $volume, 30)",
    "COUNT(($volume > (MEAN($volume, 30) * 1.5)) && ($close > $open), 5)",
    "($close - MEAN($close, 10)) / (STD($close, 10) + 1e-8) * (MEDIAN(STD($close, 20), 20) < TS_MAX(MEDIAN(STD($close, 20), 20), 60))",
]
SOURCE_FACTOR_SHA256 = "5cd90288c6d4a2f327e0142ad2528bed876e7151911096a75bc0b4adfd695f70"
INPUT_COLUMNS = ["id", "permno", "eom", "me", "ret", "ret_exc_lead1m", "prc", "prc_high", "prc_low", "tvol"]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def rolling(values: pd.Series, groups: pd.Series, window: int, method: str) -> pd.Series:
    def apply(series: pd.Series) -> pd.Series:
        roll = series.rolling(window, min_periods=window)
        return getattr(roll, method)()

    return values.groupby(groups, sort=False).transform(apply)


def ema(values: pd.Series, groups: pd.Series, span: int) -> pd.Series:
    return values.groupby(groups, sort=False).transform(
        lambda x: x.ewm(span=span, adjust=False, min_periods=span).mean()
    )


def rolling_corr(left: pd.Series, right: pd.Series, groups: pd.Series, window: int) -> pd.Series:
    result = pd.Series(np.nan, index=left.index, dtype="float64")
    for _, indices in groups.groupby(groups, sort=False).groups.items():
        result.loc[indices] = left.loc[indices].rolling(window, min_periods=window).corr(right.loc[indices]).to_numpy()
    return result


def time_series_ingredients(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.sort_values(["id", "month"], kind="stable").copy()
    groups = frame["id"]
    frame["close"] = pd.to_numeric(frame.prc, errors="coerce").abs()
    frame["high"] = pd.to_numeric(frame.prc_high, errors="coerce").abs()
    frame["low"] = pd.to_numeric(frame.prc_low, errors="coerce").abs()
    frame["volume"] = pd.to_numeric(frame.tvol, errors="coerce")
    frame["open"] = frame.close.groupby(groups, sort=False).shift(1)
    frame["sum_volume_10"] = rolling(frame.volume, groups, 10, "sum")
    frame["sum_volume_5"] = rolling(frame.volume, groups, 5, "sum")
    frame["ema_close_20"] = ema(frame.close, groups, 20)
    frame["ema_close_10"] = ema(frame.close, groups, 10)
    frame["range"] = frame.high - frame.low
    frame["body"] = frame.close - frame.open
    frame["ts_rank_range_positive"] = rolling(frame.range.notna().astype(float), groups, 5, "sum").eq(5).astype(float)
    frame.loc[rolling(frame.range.notna().astype(float), groups, 5, "sum").lt(5), "ts_rank_range_positive"] = np.nan
    frame["ts_rank_body_positive"] = rolling(frame.body.notna().astype(float), groups, 15, "sum").eq(15).astype(float)
    frame.loc[rolling(frame.body.notna().astype(float), groups, 15, "sum").lt(15), "ts_rank_body_positive"] = np.nan
    frame["corr_body_range_20"] = rolling_corr(frame.body, frame.range, groups, 20)
    frame["corr_range_volume_30"] = rolling_corr(frame.range, frame.volume, groups, 30)
    frame["mean_volume_30"] = rolling(frame.volume, groups, 30, "mean")
    spike = ((frame.volume > 1.5 * frame.mean_volume_30) & (frame.close > frame.open)).astype(float)
    spike = spike.where(frame.mean_volume_30.notna() & frame.open.notna())
    frame["count_spike_5"] = rolling(spike, groups, 5, "sum")
    frame["mean_close_10"] = rolling(frame.close, groups, 10, "mean")
    frame["std_close_10"] = rolling(frame.close, groups, 10, "std")
    frame["std_close_20"] = rolling(frame.close, groups, 20, "std")
    frame["median_std_20x20"] = rolling(frame.std_close_20, groups, 20, "median")
    frame["max_median_std_60"] = rolling(frame.median_std_20x20, groups, 60, "max")
    return frame


def source_features(formed: pd.DataFrame) -> pd.DataFrame:
    frame = formed.copy()
    rank_open = frame.groupby("month", sort=False).open.rank(method="average", pct=True)
    frame[FEATURES[0]] = (
        0.3 * rank_open + 0.2 * frame.sum_volume_10 + 0.2 * frame.ema_close_20
        + 0.3 * frame.ts_rank_range_positive
    )
    frame[FEATURES[1]] = (
        0.25 * frame.sum_volume_5 + 0.35 * frame.ema_close_10 + 0.4 * frame.ts_rank_body_positive
    )
    frame[FEATURES[2]] = frame.corr_body_range_20
    frame[FEATURES[3]] = frame.corr_range_volume_30
    frame[FEATURES[4]] = frame.count_spike_5
    frame[FEATURES[5]] = (
        (frame.close - frame.mean_close_10) / (frame.std_close_10 + 1e-8)
        * (frame.median_std_20x20 < frame.max_median_std_60)
    )
    for feature in FEATURES:
        values = frame[feature].replace([np.inf, -np.inf], np.nan)
        ranks = values.groupby(frame.month, sort=False).rank(method="average", pct=True)
        frame[feature] = 2.0 * (ranks - 0.5)
    return frame


def chronological_ridge_scores(
    frame: pd.DataFrame, *, train_months: int = 120, minimum_months: int = 24, ridge: float = 1.0
) -> tuple[pd.Series, pd.DataFrame]:
    months = sorted(frame.month.unique())
    scores = pd.Series(np.nan, index=frame.index, dtype="float64")
    coefficient_rows = []
    for number, month in enumerate(months):
        prior = months[max(0, number - train_months):number]
        if len(prior) < minimum_months:
            continue
        training = frame.loc[frame.month.isin(prior) & frame.lead_is_consecutive & frame.ret_exc_lead1m.notna()]
        x = training[FEATURES].fillna(0.0).to_numpy(float)
        y = training.ret_exc_lead1m.to_numpy(float)
        design = np.column_stack([np.ones(len(x)), x])
        penalty = np.diag([0.0, *([ridge] * len(FEATURES))])
        beta = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        current = frame.loc[frame.month.eq(month), FEATURES].fillna(0.0).to_numpy(float)
        scores.loc[frame.month.eq(month)] = beta[0] + current @ beta[1:]
        coefficient_rows.append({"formation_month": pd.Timestamp(month), "training_months": len(prior),
                                 "training_rows": len(training), "intercept": beta[0],
                                 **{name: value for name, value in zip(FEATURES, beta[1:])}})
    return scores, pd.DataFrame(coefficient_rows)


def cash_fill_warmup(path: pd.DataFrame) -> pd.DataFrame:
    """Represent the preregistered learning warmup as cash, not missing returns."""
    result = path.copy()
    warmup = result.path_status.eq("insufficient_formation_coverage")
    cash_columns = [
        "gross_return",
        "total_security_return",
        "traded_notional",
        "missing_forward_return_gross_weight",
        "missing_total_return_gross_weight",
    ]
    result.loc[warmup, cash_columns] = 0.0
    return result


def load_panel(path: Path, settings: dict) -> pd.DataFrame:
    warmup = pd.Timestamp(settings["formation_start"]) - pd.offsets.MonthEnd(130)
    end = pd.Timestamp(settings["realized_return_end"])
    raw = pd.read_parquet(path, columns=INPUT_COLUMNS, filters=[("eom", ">=", warmup), ("eom", "<=", end)])
    raw["month"] = pd.to_datetime(raw.eom) + pd.offsets.MonthEnd(0)
    raw = time_series_ingredients(raw)
    next_month = raw.groupby("id", sort=False).month.shift(-1)
    raw["ret_total_lead1m"] = raw.groupby("id", sort=False).ret.shift(-1)
    raw["lead_is_consecutive"] = next_month.eq(raw.month + pd.offsets.MonthEnd(1))
    raw.loc[~raw.lead_is_consecutive, "ret_total_lead1m"] = np.nan
    raw = raw.loc[raw.month.between(pd.Timestamp(settings["formation_start"]),
                                    pd.Timestamp(settings["formation_end"]))].copy()
    raw = raw.rename(columns={"id": "security_id", "me": "weight"})
    raw = raw.sort_values(["security_id", "month"], kind="stable")
    raw["weight"] = pd.to_numeric(raw.weight, errors="coerce")
    raw = raw.loc[raw.weight.gt(0) & raw.security_id.notna()].copy()
    size_rank = raw.groupby("month", sort=False).weight.rank(method="first", ascending=False)
    raw = raw.loc[size_rank.le(settings["top_n_by_formation_market_equity"])].reset_index(drop=True)
    return source_features(raw)


def evaluate(root: Path, output: Path) -> None:
    if (output / "run_manifest.json").exists():
        raise ValueError("completed M019 run already exists")
    study = root / "paper_runs/us_jkp_headline"
    contract_path, recipe_path = study / "benchmark_contract.json", output / "recipe.json"
    contract, recipe = json.loads(contract_path.read_text()), json.loads(recipe_path.read_text())
    if contract["status"] != "frozen" or recipe["source_expressions"] != EXPRESSIONS:
        raise ValueError("frozen contract or source expression mismatch")
    audit_rows = pd.read_csv(root / "paper_runs/paper_replication_audits/alphaagent/paper_era_factor_artifacts.csv")
    source = audit_rows.loc[audit_rows.path.eq(recipe["source_factor_file"])].iloc[0]
    if source.sha256 != SOURCE_FACTOR_SHA256 or recipe["source_factor_file_sha256"] != SOURCE_FACTOR_SHA256:
        raise ValueError("AlphaAgent factor-source hash mismatch")
    implementation = [Path(__file__).resolve(), root / "src/alpha_evolve/headline_backtest.py",
                      root / "src/alpha_evolve/submission_analysis.py", root / "scripts/run_broad_jkp_crossfit.py"]
    relative = [str(path.relative_to(root)) for path in implementation]
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *relative], cwd=root, check=True)
    formed = load_panel(Path(contract["data"]["path"]), contract["starting_settings_retained_from_corrected_us_study"])
    score, coefficients = chronological_ridge_scores(formed)
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    paths, holdings = {}, None
    for policy in ["zero", "adverse_100"]:
        path, held = build_strategy_path(formed, score, settings, policy)
        paths[policy] = cash_fill_warmup(path)
        if policy == "zero":
            holdings = held
    private_holdings = root / "artifacts/us_jkp_headline/v1/M019_formation_holdings.parquet"
    assert holdings is not None
    holdings.to_parquet(private_holdings, index=False)
    factors = pd.read_csv(root / contract["factor_panel_path"], parse_dates=["month"])
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack([paths[policy].gross_return.to_numpy() - cost / 10000 * paths[policy].traded_notional.to_numpy()
                         for policy, cost in cases])
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError("incomplete AlphaAgent partial return path")
    merged = paths["zero"][["month"]].merge(factors, on="month", validate="one_to_one")
    attr = contract["attribution"]
    reconstruction = rolling_crossfit_reconstruction(
        merged[contract["factor_columns"]].to_numpy(float), y, attr["train_months"], attr["validation_months"],
        np.asarray(attr["ridge_lambdas"]), attr["n_unpenalized"],
    )
    eval_dates = paths["zero"].month.iloc[attr["train_months"]:].reset_index(drop=True)
    lags, metrics, residual_rows = automatic_hac_lag(len(eval_dates)), [], []
    for column, ((policy, cost), name) in enumerate(zip(cases, names)):
        net, residual = y[:, column], reconstruction.residuals[:, column]
        alpha, se = float(residual.mean()), float(hac_mean_se(residual, lags))
        t_value, p_value = alpha / se, float(2 * norm.sf(abs(alpha / se)))
        path = paths[policy]
        row = {"case": name, "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
               "missing_return_policy": policy, "cost_bps_one_way": cost,
               **{f"full_{key}": value for key, value in return_statistics(net).items()},
               "evaluation_months": len(eval_dates), "evaluation_start": str(eval_dates.iloc[0].date()),
               "evaluation_end": str(eval_dates.iloc[-1].date()), "jkp_residual_mean_annualized": 12 * alpha,
               "jkp_residual_se_annualized": 12 * se, "jkp_residual_t_hac": t_value,
               "jkp_residual_p_two_sided": p_value, "exploratory_bonferroni69_p": min(1.0, 69 * p_value),
               "hac_lags": lags, "average_traded_notional": float(path.traded_notional.mean()),
               "annualized_linear_cost_drag": float(12 * cost / 10000 * path.traded_notional.mean()),
               "cash_warmup_months": int(path.path_status.eq("insufficient_formation_coverage").sum()),
               "scored_months": int(path.path_status.eq("ok").sum()),
               "maximum_missing_forward_gross_weight": float(path.missing_forward_return_gross_weight.max())}
        metrics.append(row)
        residual_rows.extend({"case": name, "month": str(month.date()), "net_return": float(value),
                              "factor_replication_return": float(fitted), "residual": float(remain),
                              "selected_lambda": float(lam)}
                             for month, value, fitted, remain, lam in zip(
                                 eval_dates, net[attr["train_months"]:], reconstruction.fitted_values[:, column],
                                 residual, reconstruction.selected_lambdas[:, column]))
    output.mkdir(parents=True, exist_ok=True)
    pd.concat([frame.assign(missing_return_policy=policy) for policy, frame in paths.items()]).to_csv(
        output / "monthly_returns.csv", index=False)
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    coefficients.to_csv(output / "rolling_model_coefficients.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = paths["zero"].copy()
    primary_path["net_return"] = primary_path.gross_return - 0.001 * primary_path.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    report = f'''# M019: AlphaAgent disclosed U.S. factor pool on monthly U.S./JKP data

Status: **completed partial evaluation**, not the AlphaAgent mining loop or native fitted run.

All six U.S. expressions in the paper-mechanism snapshot are retained without selecting on their new JKP performance. They are evaluated as a source-disclosed factor-pool component. Monthly JKP bars, previous close as the unavailable open proxy, cross-sectional ranks, a strictly prior-trained rolling ridge score, 24 cash warmup months, and common value-weighted deciles are disclosed adaptations.

At 10 bp one-way costs, the 305-month path has CAGR {primary['full_cagr']:.2%}, annualized Sharpe {primary['full_annualized_sharpe']:.3f}, and maximum drawdown {primary['full_maximum_drawdown']:.2%}. The 185-month rolling JKP133 residual mean is {primary['jkp_residual_mean_annualized']:.2%} annually (HAC t={primary['jkp_residual_t_hac']:.3f}, p={primary['jkp_residual_p_two_sided']:.4f}; descriptive 69-test bound={primary['exploratory_bonferroni69_p']:.4f}).

The exact five generated features used by the matching author LightGBM run are anonymous and unrecoverable. This result therefore does not reproduce the LLM search, regularized exploration, native LightGBM/top-50/drop-5 strategy, author metrics, or paper performance. Prior project outcomes were known, so inference is exploratory.
'''
    (output / "verdict.md").write_text(report)
    public_names = ["monthly_returns.csv", "primary_monthly_returns.csv", "metrics.csv",
                    "attribution_residuals.csv", "rolling_model_coefficients.csv", "verdict.md"]
    manifest = {"status": "evaluated_partial", "milestone_id": "M019", "benchmark_id": contract["benchmark_id"],
                "completed_at_utc": datetime.now(timezone.utc).isoformat(), "hostname": socket.gethostname(),
                "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "contract_sha256": digest(contract_path), "recipe_sha256": digest(recipe_path),
                "source_factor_file_sha256": SOURCE_FACTOR_SHA256,
                "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                            "platform": platform.system()}, "primary_result": primary,
                "private_holdings_path": str(private_holdings), "private_holdings_sha256": digest(private_holdings),
                "prior_jkp_outcomes_seen": True, "confirmatory_claim": False,
                "implementation_sha256": {str(path.relative_to(root)): digest(path) for path in implementation},
                "output_sha256": {name: digest(output / name) for name in public_names}}
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps(primary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("paper_runs/us_jkp_headline/M019_alphaagent"))
    args = parser.parse_args()
    os.umask(0o077)
    output = args.output if args.output.is_absolute() else args.root / args.output
    evaluate(args.root.resolve(), output.resolve())


if __name__ == "__main__":
    main()
