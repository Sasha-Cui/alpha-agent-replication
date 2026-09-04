#!/usr/bin/env python3
"""Evaluate XALPHA's representative elite factor on the U.S./JKP contract."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import fcntl
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

from alpha_evolve.headline_backtest import build_strategy_path, load_formations, return_statistics
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


CANDIDATE_ID = "xalpha_regime_overshoot_pressure_decay_20d_ma20_vol20"
SOURCE_FUNCTION = "regime_overshoot_pressure_decay_20d_ma20_vol20"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def xalpha_overshoot_pressure(history: pd.DataFrame) -> pd.DataFrame:
    """Execute the main-text factor independently within each security history."""
    required = {"security_id", "month", "prc"}
    if not required.issubset(history):
        raise ValueError(f"missing score inputs: {sorted(required - set(history))}")
    frame = history[["security_id", "month", "prc"]].copy()
    frame["month"] = pd.to_datetime(frame["month"]) + pd.offsets.MonthEnd(0)
    frame["close"] = pd.to_numeric(frame["prc"], errors="coerce").abs()
    frame = frame.sort_values(["security_id", "month"], kind="mergesort")
    if frame.duplicated(["security_id", "month"]).any():
        raise ValueError("duplicate security-month score inputs")
    keys = frame["security_id"]
    grouped_close = frame.groupby("security_id", sort=False)["close"]
    ma20 = grouped_close.transform(lambda x: x.rolling(20, min_periods=10).mean())
    returns = grouped_close.pct_change(fill_method=None)
    vol20 = returns.groupby(keys, sort=False).transform(
        lambda x: x.rolling(20, min_periods=10).std()
    )
    vol_median60 = vol20.groupby(keys, sort=False).transform(
        lambda x: x.rolling(60, min_periods=30).median()
    )
    high_vol = (vol20 > vol_median60).astype(float)
    threshold = (0.90 * high_vol + 0.95 * (1.0 - high_vol)) * ma20
    overshoot = (frame["close"] < threshold).astype(float)
    pressure = (overshoot * returns.abs().fillna(0.0)).groupby(keys, sort=False).transform(
        lambda x: x.rolling(20, min_periods=1).sum()
    )
    slow = pressure.groupby(keys, sort=False).transform(
        lambda x: x.ewm(span=15, adjust=False, min_periods=1).mean()
    )
    fast = pressure.groupby(keys, sort=False).transform(
        lambda x: x.ewm(span=5, adjust=False, min_periods=1).mean()
    )
    decayed = high_vol * fast + (1.0 - high_vol) * slow
    benchmark = decayed.groupby(keys, sort=False).transform(
        lambda x: x.expanding().quantile(0.75)
    )
    frame["score"] = decayed - benchmark
    return frame[["security_id", "month", "score"]]


def load_score_history(source_path: Path, start: str, end: str) -> pd.DataFrame:
    start_month = (pd.Timestamp(start) - pd.offsets.MonthEnd(120)).date()
    end_month = pd.Timestamp(end).date()
    raw = pd.read_parquet(
        source_path,
        columns=["id", "eom", "prc"],
        filters=[("eom", ">=", date.fromisoformat(str(start_month))), ("eom", "<=", date.fromisoformat(str(end_month)))],
    )
    return raw.rename(columns={"id": "security_id", "eom": "month"})


def evaluate(root: Path, output: Path) -> None:
    if (output / "run_manifest.json").exists():
        raise ValueError("M062 run already exists; do not silently overwrite it")
    study = root / "paper_runs/us_jkp_headline"
    contract_path = study / "benchmark_contract.json"
    recipe_path = output / "recipe.json"
    contract = json.loads(contract_path.read_text())
    recipe = json.loads(recipe_path.read_text())
    if contract["status"] != "frozen" or recipe["candidate_id"] != CANDIDATE_ID:
        raise ValueError("frozen XALPHA recipe/contract mismatch")
    if recipe["source_function"] != SOURCE_FUNCTION or not recipe["source_direction"].startswith("positive"):
        raise ValueError("source-selected factor or signed direction changed")
    source_path = Path(contract["data"]["path"])
    factor_path = root / contract["factor_panel_path"]
    if digest(source_path) != contract["data"]["expected_sha256_from_existing_lock"]:
        raise ValueError("JKP input hash differs from the frozen contract")
    if digest(factor_path) != contract["factor_panel_sha256"]:
        raise ValueError("common factor panel differs from the frozen contract")
    evidence = {
        recipe["paper_audit"]["manifest_path"]: recipe["paper_audit"]["manifest_sha256"],
        recipe["paper_audit"]["factor_execution_path"]: recipe["paper_audit"]["factor_execution_sha256"],
    }
    for relative, expected in evidence.items():
        if digest(root / relative) != expected:
            raise ValueError(f"pinned XALPHA evidence changed: {relative}")
    implementation = [
        Path(__file__).resolve(),
        root / "src/alpha_evolve/headline_backtest.py",
        root / "src/alpha_evolve/submission_analysis.py",
        root / "scripts/run_broad_jkp_crossfit.py",
    ]
    relative_implementation = [str(path.relative_to(root)) for path in implementation]
    subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *relative_implementation, str(recipe_path.relative_to(root))],
        cwd=root,
        check=True,
    )
    code_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    frozen_hashes = {"contract": digest(contract_path), "recipe": digest(recipe_path)}
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    formed = load_formations(source_path, [], settings)
    history = load_score_history(source_path, settings["formation_start"], settings["formation_end"])
    scores = xalpha_overshoot_pressure(history)
    formed = formed.merge(scores, on=["security_id", "month"], how="left", validate="one_to_one")
    private_dir = root / "artifacts/us_jkp_headline/v1"
    private_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(private_dir, 0o700)
    holdings_path = private_dir / "M062_formation_holdings.parquet"
    paths: dict[str, pd.DataFrame] = {}
    for policy in ("zero", "adverse_100"):
        path, holdings = build_strategy_path(formed, formed["score"], settings, policy)
        path.insert(0, "missing_return_policy", policy)
        paths[policy] = path
        if policy == "zero":
            holdings.to_parquet(holdings_path, index=False)
    base = paths["zero"]
    if not base.path_status.eq("ok").all():
        bad = base.loc[base.path_status.ne("ok"), ["formation_month", "path_status", "finite_signal_count"]]
        raise ValueError(f"incomplete fixed-calendar path: {bad.to_dict(orient='records')[:5]}")
    factors = pd.read_csv(factor_path, parse_dates=["month"])
    merged = base.merge(factors, on="month", validate="one_to_one")
    attr = contract["attribution"]
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack(
        [paths[policy].gross_return.to_numpy() - cost / 10000 * paths[policy].traded_notional.to_numpy() for policy, cost in cases]
    )
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError("nonfinite or nonpositive-NAV XALPHA path")
    reconstruction = rolling_crossfit_reconstruction(
        merged[contract["factor_columns"]].to_numpy(float),
        y,
        attr["train_months"],
        attr["validation_months"],
        np.asarray(attr["ridge_lambdas"]),
        attr["n_unpenalized"],
    )
    eval_dates = base.month.iloc[attr["train_months"]:].reset_index(drop=True)
    lags = automatic_hac_lag(len(eval_dates))
    metrics: list[dict] = []
    residual_rows: list[dict] = []
    for column, ((policy, cost), name) in enumerate(zip(cases, names)):
        candidate = paths[policy]
        net = y[:, column]
        residual = reconstruction.residuals[:, column]
        alpha = float(residual.mean())
        se = float(hac_mean_se(residual, lags))
        t_value = alpha / se
        p_value = float(2 * norm.sf(abs(t_value)))
        row = {
            "case": name,
            "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
            "missing_return_policy": policy,
            "cost_bps_one_way": cost,
            **{f"full_{key}": value for key, value in return_statistics(net).items()},
            **{f"evaluation_{key}": value for key, value in return_statistics(net[attr["train_months"]:]).items()},
            "evaluation_start": str(eval_dates.iloc[0].date()),
            "evaluation_end": str(eval_dates.iloc[-1].date()),
            "jkp_residual_mean_annualized": 12 * alpha,
            "jkp_residual_se_annualized": 12 * se,
            "jkp_residual_t_hac": t_value,
            "jkp_residual_p_two_sided": p_value,
            "jkp_residual_ci_low_annualized": 12 * (alpha - 1.959963984540054 * se),
            "jkp_residual_ci_high_annualized": 12 * (alpha + 1.959963984540054 * se),
            "exploratory_bonferroni69_p": min(1.0, 69 * p_value),
            "hac_lags": lags,
            "average_traded_notional": float(candidate.traded_notional.mean()),
            "annualized_linear_cost_drag": float(12 * cost / 10000 * candidate.traded_notional.mean()),
            "minimum_finite_signal_count": int(candidate.finite_signal_count.min()),
            "maximum_missing_forward_gross_weight": float(candidate.missing_forward_return_gross_weight.max()),
        }
        metrics.append(row)
        residual_rows.extend(
            {
                "case": name,
                "month": str(month.date()),
                "net_return": float(value),
                "factor_replication_return": float(fitted),
                "residual": float(remain),
                "selected_lambda": float(selected_lambda),
            }
            for month, value, fitted, remain, selected_lambda in zip(
                eval_dates,
                net[attr["train_months"] :],
                reconstruction.fitted_values[:, column],
                residual,
                reconstruction.selected_lambdas[:, column],
            )
        )
    output.mkdir(parents=True, exist_ok=True)
    pd.concat(paths.values(), ignore_index=True).to_csv(output / "monthly_returns.csv", index=False)
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = base.copy()
    primary_path["net_return"] = base.gross_return - 0.001 * base.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    verdict = f'''# M062: XALPHA representative overshoot factor on monthly U.S./JKP data

Status: **completed partial monthly U.S./JKP evaluation**, not the XALPHA memory-driven researcher or fused strategy.

The main-text representative elite factor `{SOURCE_FUNCTION}` is evaluated with its complete program and paper-reported positive IC direction. One source day becomes one month; the common largest-1,000 U.S. universe and value-weighted deciles replace CSI300 and the unreleased Ridge/Top-50-drop-5 path. The factor was source-selected before this run, but earlier project outcomes were seen, so inference is exploratory.

At 10 bp one-way costs, the 305-month path has CAGR {primary['full_cagr']:.2%}, annualized Sharpe {primary['full_annualized_sharpe']:.3f}, and maximum drawdown {primary['full_maximum_drawdown']:.2%}. Mean monthly traded notional is {primary['average_traded_notional']:.3f}, and minimum signal coverage is {primary['minimum_finite_signal_count']} stocks.

Across the 185-month rolling attribution window, the JKP133 residual mean is {primary['jkp_residual_mean_annualized']:.2%} annually (HAC t={primary['jkp_residual_t_hac']:.3f}, p={primary['jkp_residual_p_two_sided']:.4f}, 95% interval [{primary['jkp_residual_ci_low_annualized']:.2%}, {primary['jkp_residual_ci_high_annualized']:.2%}]; descriptive 69-test bound={primary['exploratory_bonferroni69_p']:.4f}).

This result applies only to one materially cadence-adapted evolved factor. It does not reproduce XALPHA's memory routing, hypothesis generation, factor evolution, complete library, Ridge fusion, Qlib Top-50/drop-5 portfolio, native data, or paper performance.
'''
    (output / "verdict.md").write_text(verdict)
    if frozen_hashes != {"contract": digest(contract_path), "recipe": digest(recipe_path)}:
        raise RuntimeError("frozen recipe or contract changed during evaluation")
    manifest = {
        "status": "evaluated_partial",
        "milestone_id": "M062",
        "candidate_id": CANDIDATE_ID,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": contract["benchmark_id"],
        "code_commit": code_commit,
        "contract_sha256": frozen_hashes["contract"],
        "recipe_sha256": frozen_hashes["recipe"],
        "input_sha256": digest(source_path),
        "benchmark_sha256": digest(factor_path),
        "private_holdings_path": str(holdings_path),
        "private_holdings_sha256": digest(holdings_path),
        "source_evidence_sha256": evidence,
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "platform": platform.system()},
        "primary_result": primary,
        "source_direction": "positive_signed_test_ic",
        "prior_jkp_outcomes_seen": True,
        "confirmatory_claim": False,
        "implementation_sha256": {str(path.relative_to(root)): digest(path) for path in implementation},
        "output_sha256": {
            name: digest(output / name)
            for name in ["monthly_returns.csv", "primary_monthly_returns.csv", "metrics.csv", "attribution_residuals.csv", "verdict.md"]
        },
    }
    write_json(output / "run_manifest.json", manifest)
    print(json.dumps(primary, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("paper_runs/us_jkp_headline/M062_xalpha"))
    args = parser.parse_args()
    os.umask(0o077)
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    private_dir = root / "artifacts/us_jkp_headline/v1"
    private_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(private_dir, 0o700)
    with (private_dir / "operation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status = {
            "state": "running", "phase": "run", "milestone_id": "M062", "pid": os.getpid(),
            "hostname": socket.gethostname(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        }
        operation_path = private_dir / "operation.json"
        write_json(operation_path, status)
        try:
            evaluate(root, output.resolve())
        except BaseException as error:
            status.update(state="failed", finished_at_utc=datetime.now(timezone.utc).isoformat(), error_type=type(error).__name__, error=str(error))
            write_json(operation_path, status)
            raise
        status.update(state="complete", finished_at_utc=datetime.now(timezone.utc).isoformat())
        write_json(operation_path, status)


if __name__ == "__main__":
    main()
