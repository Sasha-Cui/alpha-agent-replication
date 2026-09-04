#!/usr/bin/env python3
"""Evaluate FactorEngine's showcased evolved factor on monthly U.S./JKP data."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

from alpha_evolve.headline_backtest import build_strategy_path, formation_universe, return_statistics
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


CANDIDATE_ID = "factorengine_showcased_evolved_factor_40"
LISTING_SHA256 = "69977f4ef5ee18f0c4e071737dba62753a0f45bea5dca5e4215885d8f66d8b20"
INPUT_COLUMNS = ["id", "permno", "eom", "me", "ret", "ret_exc_lead1m", "prc", "prc_high", "prc_low", "tvol"]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def evolved_factor_score(frame: pd.DataFrame, smoothing_window: int = 5) -> pd.Series:
    ordered = frame.sort_values(["security_id", "month"], kind="stable").copy()
    close = pd.to_numeric(ordered.prc, errors="coerce").abs()
    high = pd.to_numeric(ordered.prc_high, errors="coerce").abs()
    low = pd.to_numeric(ordered.prc_low, errors="coerce").abs()
    volume = pd.to_numeric(ordered.tvol, errors="coerce")
    ret = pd.to_numeric(ordered.ret, errors="coerce")
    opening = (close / (1 + ret)).where(ret.gt(-1) & np.isfinite(ret) & close.gt(0))
    daily_range = high - low
    turnover = volume * close
    valid = opening.notna() & daily_range.gt(0) & turnover.gt(0)
    sf1 = (-turnover * (close - (high + low) / 2) / (daily_range + 1e-9)).where(valid)
    sf2 = (-turnover * (high - opening) / (daily_range + 1e-9)).where(valid)
    sf3 = (turnover * (np.minimum(opening, close) - low) / (daily_range + 1e-9)).where(valid)

    def rank_norm(values: pd.Series) -> pd.Series:
        ranks = values.groupby(ordered.month, sort=False).rank(method="average")
        counts = values.notna().groupby(ordered.month, sort=False).transform("sum")
        return ranks / (counts + 1) - 0.5

    raw = 0.25 * rank_norm(sf1) + 0.25 * rank_norm(sf2) + 0.50 * rank_norm(sf3)
    smoothed = raw.groupby(ordered.security_id, sort=False).transform(
        lambda values: values.ewm(
            span=smoothing_window, min_periods=max(1, smoothing_window // 2),
            adjust=True, ignore_na=False,
        ).mean()
    )
    means = smoothed.groupby(ordered.month, sort=False).transform("mean")
    stds = smoothed.groupby(ordered.month, sort=False).transform(lambda values: values.std(ddof=0))
    score = ((smoothed - means) / (stds + 1e-9)).where(stds.gt(0))
    return score.reindex(frame.index).replace([np.inf, -np.inf], np.nan)


def load_panel(path: Path, settings: dict) -> tuple[pd.DataFrame, pd.Series]:
    warmup = pd.Timestamp(settings["formation_start"]) - pd.offsets.MonthEnd(8)
    raw = pd.read_parquet(
        path, columns=INPUT_COLUMNS,
        filters=[("eom", ">=", warmup), ("eom", "<=", pd.Timestamp(settings["realized_return_end"]))],
    )
    expanded = formation_universe(raw, warmup, settings["formation_end"], settings["top_n_by_formation_market_equity"])
    scores = evolved_factor_score(expanded)
    keep = expanded.month.between(pd.Timestamp(settings["formation_start"]), pd.Timestamp(settings["formation_end"]))
    formed = expanded.loc[keep].copy().reset_index(drop=True)
    score = scores.loc[keep].reset_index(drop=True)
    return formed, score


def build_metrics(contract: dict, root: Path, paths: dict[str, pd.DataFrame]) -> tuple[list[dict], list[dict]]:
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    factors = pd.read_csv(root / contract["factor_panel_path"], parse_dates=["month"])
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack(
        [paths[policy].gross_return.to_numpy() - cost / 10000 * paths[policy].traded_notional.to_numpy()
         for policy, cost in cases]
    )
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError("incomplete FactorEngine partial return path")
    merged = paths["zero"][["month"]].merge(factors, on="month", validate="one_to_one")
    attr = contract["attribution"]
    reconstruction = rolling_crossfit_reconstruction(
        merged[contract["factor_columns"]].to_numpy(float), y, attr["train_months"],
        attr["validation_months"], np.asarray(attr["ridge_lambdas"]), attr["n_unpenalized"],
    )
    eval_dates = paths["zero"].month.iloc[attr["train_months"]:].reset_index(drop=True)
    lags, metrics, residual_rows = automatic_hac_lag(len(eval_dates)), [], []
    for column, ((policy, cost), name) in enumerate(zip(cases, names)):
        net, residual = y[:, column], reconstruction.residuals[:, column]
        alpha, se = float(residual.mean()), float(hac_mean_se(residual, lags))
        t_value, p_value = alpha / se, float(2 * norm.sf(abs(alpha / se)))
        path = paths[policy]
        metrics.append(
            {"case": name, "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
             "missing_return_policy": policy, "cost_bps_one_way": cost,
             **{f"full_{key}": value for key, value in return_statistics(net).items()},
             "evaluation_months": len(eval_dates), "evaluation_start": str(eval_dates.iloc[0].date()),
             "evaluation_end": str(eval_dates.iloc[-1].date()),
             "jkp_residual_mean_annualized": 12 * alpha, "jkp_residual_se_annualized": 12 * se,
             "jkp_residual_t_hac": t_value, "jkp_residual_p_two_sided": p_value,
             "exploratory_bonferroni69_p": min(1.0, 69 * p_value), "hac_lags": lags,
             "average_traded_notional": float(path.traded_notional.mean()),
             "annualized_linear_cost_drag": float(12 * cost / 10000 * path.traded_notional.mean()),
             "minimum_finite_signal_count": int(path.finite_signal_count.min()),
             "maximum_missing_forward_gross_weight": float(path.missing_forward_return_gross_weight.max())}
        )
        residual_rows.extend(
            {"case": name, "month": str(month.date()), "net_return": float(value),
             "factor_replication_return": float(fitted), "residual": float(remain),
             "selected_lambda": float(lam)}
            for month, value, fitted, remain, lam in zip(
                eval_dates, net[attr["train_months"]:], reconstruction.fitted_values[:, column],
                residual, reconstruction.selected_lambdas[:, column]
            )
        )
    return metrics, residual_rows


def evaluate(root: Path, output: Path) -> None:
    if (output / "run_manifest.json").exists():
        raise ValueError("completed M046 run already exists")
    study = root / "paper_runs/us_jkp_headline"
    contract_path, recipe_path = study / "benchmark_contract.json", output / "recipe.json"
    component_path = root / "paper_runs/paper_replication_audits/factorengine/factor_program_execution.csv"
    contract, recipe = json.loads(contract_path.read_text()), json.loads(recipe_path.read_text())
    evidence = pd.read_csv(component_path)
    evolved = evidence.loc[evidence.listing.eq("evolved_factor_after_40_iterations")].iloc[0]
    if contract["status"] != "frozen" or recipe["status"] != "frozen_for_execution":
        raise ValueError("frozen benchmark and FactorEngine recipe required")
    if recipe["candidate_id"] != CANDIDATE_ID or evolved.listing_sha256 != LISTING_SHA256:
        raise ValueError("FactorEngine evolved listing identity mismatch")
    if evolved.observed_failure != "NameError: daily_range_expr is not defined":
        raise ValueError("FactorEngine compatibility-repair boundary changed")
    implementation = [Path(__file__).resolve(), root / "src/alpha_evolve/headline_backtest.py",
                      root / "src/alpha_evolve/submission_analysis.py", root / "scripts/run_broad_jkp_crossfit.py"]
    relative = [str(path.relative_to(root)) for path in [recipe_path, *implementation]]
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *relative], cwd=root, check=True)
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    formed, score = load_panel(Path(contract["data"]["path"]), settings)
    paths, primary_holdings = {}, None
    for policy in ("zero", "adverse_100"):
        paths[policy], holdings = build_strategy_path(formed, score, settings, policy)
        if policy == "zero":
            primary_holdings = holdings
    if any(not path.path_status.eq("ok").all() for path in paths.values()):
        raise ValueError("FactorEngine partial lacks complete formation coverage")
    private_holdings = root / "artifacts/us_jkp_headline/v1/M046_formation_holdings.parquet"
    assert primary_holdings is not None
    primary_holdings.to_parquet(private_holdings, index=False)
    metrics, residual_rows = build_metrics(contract, root, paths)
    output.mkdir(parents=True, exist_ok=True)
    pd.concat([frame.assign(missing_return_policy=policy) for policy, frame in paths.items()]).to_csv(
        output / "monthly_returns.csv", index=False
    )
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = paths["zero"].copy()
    primary_path["net_return"] = primary_path.gross_return - 0.001 * primary_path.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    report = f'''# M046: FactorEngine showcased evolved factor on monthly U.S./JKP data

Status: **completed central partial adaptation**, not the FactorEngine evolution system or headline factor pool.

The representative factor printed after 40 evolution iterations is retained with default 0.25/0.25/0.50 component weights, five-period EWM, and positive source direction. Its sole execution defect is repaired by restoring `daily_range_expr = high - low`, exactly as the seed program directly above defines it. Monthly JKP bars, the prior-close-implied open, and common value-weighted deciles are disclosed adaptations.

At 10 bp one-way costs, the 305-month path has CAGR {primary['full_cagr']:.2%}, annualized Sharpe {primary['full_annualized_sharpe']:.3f}, and maximum drawdown {primary['full_maximum_drawdown']:.2%}. The 185-month JKP133 residual mean is {primary['jkp_residual_mean_annualized']:.2%} annually (HAC t={primary['jkp_residual_t_hac']:.3f}, p={primary['jkp_residual_p_two_sided']:.4f}; descriptive 69-test bound={primary['exploratory_bonferroni69_p']:.4f}).

This evaluates the strongest concrete evolved program, not the unreleased report corpus, LLM search, factor pool, LightGBM synthesis, native Qlib backtest, or paper metrics. Prior outcomes were known, so inference is exploratory.
'''
    (output / "verdict.md").write_text(report)
    public_names = ["monthly_returns.csv", "primary_monthly_returns.csv", "metrics.csv",
                    "attribution_residuals.csv", "verdict.md"]
    manifest = {
        "status": "evaluated_partial", "milestone_id": "M046", "candidate_id": CANDIDATE_ID,
        "benchmark_id": contract["benchmark_id"], "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "contract_sha256": digest(contract_path), "recipe_sha256": digest(recipe_path),
        "factor_program_execution_sha256": digest(component_path),
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                    "platform": platform.system()},
        "primary_result": primary, "private_holdings_path": str(private_holdings),
        "private_holdings_sha256": digest(private_holdings), "prior_jkp_outcomes_seen": True,
        "confirmatory_claim": False,
        "implementation_sha256": {str(path.relative_to(root)): digest(path) for path in implementation},
        "output_sha256": {name: digest(output / name) for name in public_names},
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps(primary, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("paper_runs/us_jkp_headline/M046_factorengine"))
    args = parser.parse_args()
    os.umask(0o077)
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    private = root / "artifacts/us_jkp_headline/v1"
    private.mkdir(parents=True, exist_ok=True)
    with (private / "operation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status_path = private / "operation.json"
        status = {"state": "running", "phase": "evolved_factor_evaluation", "milestone_id": "M046",
                  "pid": os.getpid(), "hostname": socket.gethostname(),
                  "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
                  "started_at_utc": datetime.now(timezone.utc).isoformat(),
                  "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]}
        write_json(status_path, status)
        try:
            evaluate(root, output.resolve())
        except BaseException as error:
            status.update(state="failed", finished_at_utc=datetime.now(timezone.utc).isoformat(),
                          error_type=type(error).__name__, error=str(error))
            write_json(status_path, status)
            raise
        status.update(state="complete", finished_at_utc=datetime.now(timezone.utc).isoformat())
        write_json(status_path, status)


if __name__ == "__main__":
    main()
