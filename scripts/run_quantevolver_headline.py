#!/usr/bin/env python3
"""Evaluate QuantEvolver's first released seed on the common U.S./JKP contract."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm

from alpha_evolve.headline_backtest import build_strategy_path, load_formations, return_statistics
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


SOURCE_FORMULA = "div(ts_mean(returns(60)), ts_std(returns(60)))"
CANDIDATE_ID = "quantevolver_return_sharpe_60"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def quant_evolver_return_sharpe_60(history: pd.DataFrame) -> pd.DataFrame:
    """Preserve the released DSL tree on consecutive monthly close bars."""
    required = {"security_id", "month", "prc"}
    if not required.issubset(history):
        raise ValueError(f"missing score inputs: {sorted(required - set(history))}")
    frame = history[["security_id", "month", "prc"]].copy()
    frame["month"] = pd.to_datetime(frame["month"]) + pd.offsets.MonthEnd(0)
    frame["close"] = pd.to_numeric(frame["prc"], errors="coerce").abs()
    frame = frame.sort_values(["security_id", "month"], kind="mergesort")
    if frame.duplicated(["security_id", "month"]).any():
        raise ValueError("duplicate security-month score inputs")
    grouped = frame.groupby("security_id", sort=False)
    previous_close = grouped["close"].shift(1)
    previous_month = grouped["month"].shift(1)
    consecutive = previous_month.eq(frame["month"] - pd.offsets.MonthEnd(1))
    returns = ((frame["close"] - previous_close) / (previous_close + 1e-8)).where(consecutive)
    by_security = returns.groupby(frame["security_id"], sort=False)
    mean_60 = by_security.transform(lambda values: values.rolling(60, min_periods=60).mean())
    std_60 = by_security.transform(lambda values: values.rolling(60, min_periods=60).std(ddof=0))
    # The released ts_std adds 1e-8 and div adds another 1e-8.
    frame["score"] = mean_60 / (std_60.abs() + 2e-8)
    return frame[["security_id", "month", "score"]]


def load_score_history(source_path: Path, start: str, end: str) -> pd.DataFrame:
    start_month = (pd.Timestamp(start) - pd.offsets.MonthEnd(66)).date()
    end_month = pd.Timestamp(end).date()
    raw = pd.read_parquet(
        source_path,
        columns=["id", "eom", "prc"],
        filters=[("eom", ">=", date.fromisoformat(str(start_month))), ("eom", "<=", date.fromisoformat(str(end_month)))],
    )
    return raw.rename(columns={"id": "security_id", "eom": "month"})


def evaluate(root: Path, output: Path) -> None:
    if (output / "run_manifest.json").exists():
        raise ValueError("M056 run already exists; do not silently overwrite it")
    study = root / "paper_runs/us_jkp_headline"
    contract_path = study / "benchmark_contract.json"
    recipe_path = output / "recipe.json"
    contract = json.loads(contract_path.read_text())
    recipe = json.loads(recipe_path.read_text())
    if contract["status"] != "frozen" or recipe["candidate_id"] != CANDIDATE_ID:
        raise ValueError("frozen QuantEvolver recipe/contract mismatch")
    if recipe["source_formula"] != SOURCE_FORMULA or recipe["source_seed_id"] != "seed_0001":
        raise ValueError("source-selected first seed changed")

    source_path = Path(contract["data"]["path"])
    if digest(source_path) != contract["data"]["expected_sha256_from_existing_lock"]:
        raise ValueError("JKP input hash differs from the frozen contract")
    factor_path = root / contract["factor_panel_path"]
    if digest(factor_path) != contract["factor_panel_sha256"]:
        raise ValueError("common factor panel differs from the frozen contract")
    source_snapshots = {
        recipe["source_repository"]["seed_snapshot_path"]: recipe["source_repository"]["seed_snapshot_sha256"],
        recipe["source_repository"]["evaluator_snapshot_path"]: recipe["source_repository"]["evaluator_snapshot_sha256"],
        recipe["paper_audit"]["manifest_path"]: recipe["paper_audit"]["manifest_sha256"],
    }
    for relative, expected in source_snapshots.items():
        if digest(root / relative) != expected:
            raise ValueError(f"pinned QuantEvolver evidence changed: {relative}")

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
    scores = quant_evolver_return_sharpe_60(history)
    formed = formed.merge(scores, on=["security_id", "month"], how="left", validate="one_to_one")
    if any(name in formed for name in ("_headline_score", "future_return")):
        raise ValueError("reserved or future score input leaked into formation data")

    private_dir = root / "artifacts/us_jkp_headline/v1"
    private_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(private_dir, 0o700)
    holdings_path = private_dir / "M056_formation_holdings.parquet"
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
    case_names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack(
        [
            paths[policy].gross_return.to_numpy() - cost / 10000 * paths[policy].traded_notional.to_numpy()
            for policy, cost in cases
        ]
    )
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError("nonfinite or nonpositive-NAV QuantEvolver path")
    x = merged[contract["factor_columns"]].to_numpy(float)
    reconstruction = rolling_crossfit_reconstruction(
        x,
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
    for column, ((policy, cost), case) in enumerate(zip(cases, case_names)):
        candidate = paths[policy]
        net = y[:, column]
        residual = reconstruction.residuals[:, column]
        alpha = float(residual.mean())
        se = float(hac_mean_se(residual, lags))
        t_value = alpha / se
        p_value = float(2 * norm.sf(abs(t_value)))
        row = {
            "case": case,
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
                "case": case,
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
    verdict = f'''# M056: QuantEvolver first released seed on monthly U.S./JKP data

Status: **completed partial monthly U.S./JKP evaluation**, not the reinforcement-fine-tuned QuantEvolver miner.

The source-first valid example seed `return_sharpe_60` is evaluated with its complete DSL tree `{SOURCE_FORMULA}`. Close-derived simple returns, the 60-return mean/volatility ratio, positive direction, and released epsilon semantics are preserved. Each source bar becomes one month; the common largest-1,000 U.S. universe and value-weighted long/short deciles replace the example symbols and the evaluator's equal-mean quintile diagnostic. This source-order choice was fixed before the new common run, but earlier QuantEvolver proxy/component outcomes were already observed, so the result is exploratory.

At 10 bp one-way costs, the 305-month path has CAGR {primary['full_cagr']:.2%}, annualized Sharpe {primary['full_annualized_sharpe']:.3f}, and maximum drawdown {primary['full_maximum_drawdown']:.2%}. Mean monthly traded notional is {primary['average_traded_notional']:.3f}, implying {primary['annualized_linear_cost_drag']:.2%} annualized linear fee drag. The minimum formation-month signal coverage is {primary['minimum_finite_signal_count']} stocks.

Across the 185-month rolling attribution window, the JKP133 residual mean is {primary['jkp_residual_mean_annualized']:.2%} annually (HAC t={primary['jkp_residual_t_hac']:.3f}, p={primary['jkp_residual_p_two_sided']:.4f}, 95% interval [{primary['jkp_residual_ci_low_annualized']:.2%}, {primary['jkp_residual_ci_high_annualized']:.2%}]; descriptive 69-test bound={primary['exploratory_bonferroni69_p']:.4f}).

This is performance of one author-released seed after a material monthly adapter. It does not reproduce the RFT policy, trained checkpoint, seed/task bank, generated factor search, diversity shaping, mined library, fusion, native benchmarks, or any paper result. A negative or insignificant result therefore bears only on this disclosed component transfer, not on the paper's withheld headline system.
'''
    (output / "verdict.md").write_text(verdict)

    if frozen_hashes != {"contract": digest(contract_path), "recipe": digest(recipe_path)}:
        raise RuntimeError("frozen recipe or benchmark changed during evaluation")
    run_manifest = {
        "status": "evaluated_partial",
        "milestone_id": "M056",
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
        "source_evidence_sha256": source_snapshots,
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.system(),
        },
        "primary_result": primary,
        "prior_jkp_outcomes_seen": True,
        "confirmatory_claim": False,
        "implementation_sha256": {
            str(path.relative_to(root)): digest(path) for path in implementation
        },
        "output_sha256": {
            name: digest(output / name)
            for name in [
                "monthly_returns.csv",
                "primary_monthly_returns.csv",
                "metrics.csv",
                "attribution_residuals.csv",
                "verdict.md",
            ]
        },
    }
    write_json(output / "run_manifest.json", run_manifest)
    print(json.dumps(primary, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("paper_runs/us_jkp_headline/M056_quantevolver"),
    )
    args = parser.parse_args()
    os.umask(0o077)
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    evaluate(root, output.resolve())


if __name__ == "__main__":
    main()
