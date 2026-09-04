#!/usr/bin/env python3
"""Evaluate the frozen Chain-of-Alpha close/amount formula on monthly U.S./JKP data."""
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


CANDIDATE_ID = "chain_of_alpha_volume_adjusted_mean_corr"
SOURCE_FORMULA = "Corr(Rank($close, 5), Rank($amount, 5), 5)"
INPUT_COLUMNS = ["id", "permno", "eom", "me", "ret", "ret_exc_lead1m", "prc", "dolvol"]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def percentile_rank_last(values: np.ndarray) -> float:
    if not np.isfinite(values).all():
        return np.nan
    last = values[-1]
    less = np.sum(values < last)
    equal = np.sum(values == last)
    return float((less + (equal + 1) / 2) / len(values))


def rolling_rank(values: pd.Series, groups: pd.Series, window: int = 5) -> pd.Series:
    return values.groupby(groups, sort=False).transform(
        lambda x: x.rolling(window, min_periods=window).apply(percentile_rank_last, raw=True)
    )


def rolling_corr(left: pd.Series, right: pd.Series, groups: pd.Series, window: int = 5) -> pd.Series:
    result = pd.Series(np.nan, index=left.index, dtype="float64")
    for _, indices in groups.groupby(groups, sort=False).groups.items():
        result.loc[indices] = left.loc[indices].rolling(window, min_periods=window).corr(right.loc[indices]).to_numpy()
    return result


def formula_score(raw: pd.DataFrame) -> pd.Series:
    frame = raw.sort_values(["security_id", "month"], kind="stable")
    groups = frame.security_id
    close_rank = rolling_rank(pd.to_numeric(frame.prc, errors="coerce").abs(), groups)
    amount_rank = rolling_rank(pd.to_numeric(frame.dolvol, errors="coerce"), groups)
    score = rolling_corr(close_rank, amount_rank, groups)
    return score.reindex(raw.index).replace([np.inf, -np.inf], np.nan)


def load_panel(path: Path, settings: dict) -> tuple[pd.DataFrame, pd.Series]:
    warmup = pd.Timestamp(settings["formation_start"]) - pd.offsets.MonthEnd(12)
    end = pd.Timestamp(settings["realized_return_end"])
    raw = pd.read_parquet(path, columns=INPUT_COLUMNS, filters=[("eom", ">=", warmup), ("eom", "<=", end)])
    raw["month"] = pd.to_datetime(raw.eom) + pd.offsets.MonthEnd(0)
    raw = raw.rename(columns={"id": "security_id", "me": "weight"})
    raw = raw.sort_values(["security_id", "month"], kind="stable")
    next_month = raw.groupby("security_id", sort=False).month.shift(-1)
    raw["ret_total_lead1m"] = raw.groupby("security_id", sort=False).ret.shift(-1)
    raw.loc[next_month.ne(raw.month + pd.offsets.MonthEnd(1)), "ret_total_lead1m"] = np.nan
    scores = formula_score(raw)
    raw[CANDIDATE_ID] = scores
    raw = raw.loc[raw.month.between(pd.Timestamp(settings["formation_start"]),
                                    pd.Timestamp(settings["formation_end"]))].copy()
    raw["weight"] = pd.to_numeric(raw.weight, errors="coerce")
    raw = raw.loc[raw.weight.gt(0) & raw.security_id.notna()].copy()
    rank = raw.groupby("month", sort=False).weight.rank(method="first", ascending=False)
    raw = raw.loc[rank.le(settings["top_n_by_formation_market_equity"])].reset_index(drop=True)
    return raw, raw.pop(CANDIDATE_ID)


def build_metrics(contract: dict, root: Path, paths: dict[str, pd.DataFrame]) -> tuple[list[dict], list[dict]]:
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    factors = pd.read_csv(root / contract["factor_panel_path"], parse_dates=["month"])
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack([paths[policy].gross_return.to_numpy() - cost / 10000 * paths[policy].traded_notional.to_numpy()
                         for policy, cost in cases])
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError("incomplete Chain-of-Alpha partial return path")
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
        metrics.append({
            "case": name,
            "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
            "missing_return_policy": policy,
            "cost_bps_one_way": cost,
            **{f"full_{key}": value for key, value in return_statistics(net).items()},
            "evaluation_months": len(eval_dates),
            "evaluation_start": str(eval_dates.iloc[0].date()),
            "evaluation_end": str(eval_dates.iloc[-1].date()),
            "jkp_residual_mean_annualized": 12 * alpha,
            "jkp_residual_se_annualized": 12 * se,
            "jkp_residual_t_hac": t_value,
            "jkp_residual_p_two_sided": p_value,
            "exploratory_bonferroni69_p": min(1.0, 69 * p_value),
            "hac_lags": lags,
            "average_traded_notional": float(path.traded_notional.mean()),
            "annualized_linear_cost_drag": float(12 * cost / 10000 * path.traded_notional.mean()),
            "minimum_finite_signal_count": int(path.finite_signal_count.min()),
            "maximum_missing_forward_gross_weight": float(path.missing_forward_return_gross_weight.max()),
        })
        residual_rows.extend({"case": name, "month": str(month.date()), "net_return": float(value),
                              "factor_replication_return": float(fitted), "residual": float(remain),
                              "selected_lambda": float(lam)}
                             for month, value, fitted, remain, lam in zip(
                                 eval_dates, net[attr["train_months"]:], reconstruction.fitted_values[:, column],
                                 residual, reconstruction.selected_lambdas[:, column]))
    return metrics, residual_rows


def evaluate(root: Path, output: Path) -> None:
    if (output / "run_manifest.json").exists():
        raise ValueError("completed M026 run already exists")
    study = root / "paper_runs/us_jkp_headline"
    contract_path, recipe_path = study / "benchmark_contract.json", output / "recipe.json"
    contract, recipe = json.loads(contract_path.read_text()), json.loads(recipe_path.read_text())
    if contract["status"] != "frozen" or recipe["source_formula"] != SOURCE_FORMULA:
        raise ValueError("frozen contract or source formula mismatch")
    inventory_path = root / "paper_runs/paper_replication_audits/chain_of_alpha/published_factor_inventory.csv"
    inventory = pd.read_csv(inventory_path)
    source = inventory.loc[inventory.name.eq("Volume_Adjusted_Mean_Corr")].iloc[0]
    if source.expression != SOURCE_FORMULA or float(source.rankic) != recipe["paper_rankic_direction"]:
        raise ValueError("paper factor inventory mismatch")
    implementation = [Path(__file__).resolve(), root / "src/alpha_evolve/headline_backtest.py",
                      root / "src/alpha_evolve/submission_analysis.py", root / "scripts/run_broad_jkp_crossfit.py"]
    relative = [str(path.relative_to(root)) for path in implementation]
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *relative], cwd=root, check=True)
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    formed, score = load_panel(Path(contract["data"]["path"]), settings)
    paths, holdings = {}, None
    for policy in ["zero", "adverse_100"]:
        paths[policy], held = build_strategy_path(formed, score, settings, policy)
        if policy == "zero":
            holdings = held
    if any(not path.path_status.eq("ok").all() for path in paths.values()):
        raise ValueError("Chain-of-Alpha component lacks complete formation coverage")
    private_holdings = root / "artifacts/us_jkp_headline/v1/M026_formation_holdings.parquet"
    assert holdings is not None
    holdings.to_parquet(private_holdings, index=False)
    metrics, residual_rows = build_metrics(contract, root, paths)
    output.mkdir(parents=True, exist_ok=True)
    pd.concat([frame.assign(missing_return_policy=policy) for policy, frame in paths.items()]).to_csv(
        output / "monthly_returns.csv", index=False)
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = paths["zero"].copy()
    primary_path["net_return"] = primary_path.gross_return - 0.001 * primary_path.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    report = f'''# M026: Chain-of-Alpha disclosed formula on monthly U.S./JKP data

Status: **completed partial evaluation**, not either LLM chain or the native factor portfolio.

The exact showcased `Volume_Adjusted_Mean_Corr` formula is preserved as five-period time-series ranks of close and amount followed by their five-period correlation. It was selected because it alone avoids unavailable VWAP, not because of JKP performance. JKP `abs(prc)` and source-defined USD `dolvol`, monthly cadence, the top-1,000 U.S. universe, and common value-weighted deciles are disclosed adaptations.

At 10 bp one-way costs, the 305-month path has CAGR {primary['full_cagr']:.2%}, annualized Sharpe {primary['full_annualized_sharpe']:.3f}, and maximum drawdown {primary['full_maximum_drawdown']:.2%}. The 185-month rolling JKP133 residual mean is {primary['jkp_residual_mean_annualized']:.2%} annually (HAC t={primary['jkp_residual_t_hac']:.3f}, p={primary['jkp_residual_p_two_sided']:.4f}; descriptive 69-test bound={primary['exploratory_bonferroni69_p']:.4f}).

This result does not reproduce the withdrawn paper's native parser, dual-chain prompts/models, search, selected 100-factor pool, LightGBM, Qlib portfolio, or reported RankIC. Prior project outcomes were known, so inference is exploratory.
'''
    (output / "verdict.md").write_text(report)
    public_names = ["monthly_returns.csv", "primary_monthly_returns.csv", "metrics.csv",
                    "attribution_residuals.csv", "verdict.md"]
    manifest = {
        "status": "evaluated_partial",
        "milestone_id": "M026",
        "candidate_id": CANDIDATE_ID,
        "benchmark_id": contract["benchmark_id"],
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "contract_sha256": digest(contract_path),
        "recipe_sha256": digest(recipe_path),
        "published_factor_inventory_sha256": digest(inventory_path),
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                    "platform": platform.system()},
        "primary_result": primary,
        "private_holdings_path": str(private_holdings),
        "private_holdings_sha256": digest(private_holdings),
        "prior_jkp_outcomes_seen": True,
        "confirmatory_claim": False,
        "implementation_sha256": {str(path.relative_to(root)): digest(path) for path in implementation},
        "output_sha256": {name: digest(output / name) for name in public_names},
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps(primary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("paper_runs/us_jkp_headline/M026_chain_of_alpha"))
    args = parser.parse_args()
    os.umask(0o077)
    output = args.output if args.output.is_absolute() else args.root / args.output
    evaluate(args.root.resolve(), output.resolve())


if __name__ == "__main__":
    main()
