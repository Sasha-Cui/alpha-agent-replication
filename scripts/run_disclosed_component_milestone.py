#!/usr/bin/env python3
"""Re-account a fixed disclosed-component path on the U.S./JKP benchmark."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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

from alpha_evolve.headline_backtest import return_statistics
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import (
    hac_mean_se, rolling_crossfit_reconstruction,
)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def require_fresh_output(output: Path) -> None:
    """Allow a committed recipe directory, but never overwrite completed results."""
    if (output / "run_manifest.json").exists():
        raise ValueError("output run already exists; do not silently rerun")


def load_component_holdings(path: Path, candidate_id: str) -> pd.DataFrame:
    pieces = []
    for chunk in pd.read_csv(path, chunksize=200_000):
        selected = chunk.loc[chunk.candidate_id.eq(candidate_id)]
        if len(selected):
            pieces.append(selected)
    if not pieces:
        raise ValueError(f"no holdings for {candidate_id}")
    result = pd.concat(pieces, ignore_index=True)
    result["formation_month"] = pd.to_datetime(result.formation_month)
    return result


def reconstruct_paths(months: pd.DataFrame, holdings: pd.DataFrame, missing_policy: str) -> pd.DataFrame:
    groups = {month: frame for month, frame in holdings.groupby("formation_month", sort=True)}
    previous_weights: dict[int, float] = {}
    previous_returns: dict[int, float] = {}
    rows = []
    for source in months.itertuples(index=False):
        formation = pd.Timestamp(source.formation_month)
        frame = groups.get(formation, holdings.iloc[0:0])
        weights = {int(row.permno): float(row.target_weight) for row in frame.itertuples()}
        excess, total = {}, {}
        missing_weight = 0.0
        for row in frame.itertuples():
            security, weight = int(row.permno), float(row.target_weight)
            if bool(row.realized_return_observed):
                excess[security], total[security] = float(row.effective_excess_return), float(row.effective_total_return)
            else:
                missing_weight += abs(weight)
                replacement = 0.0 if missing_policy == "zero" else -float(np.sign(weight))
                excess[security] = total[security] = replacement
        denominator = 1.0 + sum(weight * previous_returns.get(key, 0.0) for key, weight in previous_weights.items())
        if denominator <= 0 or not np.isfinite(denominator):
            raise ValueError("nonpositive component strategy NAV")
        drift = {key: weight * (1 + previous_returns.get(key, 0.0)) / denominator
                 for key, weight in previous_weights.items()}
        turnover = sum(abs(weights.get(key, 0.0) - drift.get(key, 0.0)) for key in set(weights) | set(drift))
        gross = sum(weight * excess[key] for key, weight in weights.items())
        total_return = sum(weight * total[key] for key, weight in weights.items())
        if total_return <= -1:
            raise ValueError("component strategy NAV becomes nonpositive")
        rows.append({"missing_return_policy": missing_policy, "formation_month": formation,
                     "month": pd.Timestamp(source.month), "gross_return": gross,
                     "total_security_return": total_return, "traded_notional": turnover,
                     "n_holdings": len(weights), "missing_forward_gross_weight": missing_weight,
                     "path_status": "ok"})
        previous_weights, previous_returns = weights, total
    return pd.DataFrame(rows)


def evaluate(root: Path, milestone_id: str, candidate_id: str, output: Path) -> None:
    require_fresh_output(output)
    study = root / "paper_runs/us_jkp_headline"
    contract_path = study / "benchmark_contract.json"
    recipe_path = study / f"{milestone_id}_{output.name.split('_', 1)[-1]}/recipe.json"
    contract, recipe = json.loads(contract_path.read_text()), json.loads(recipe_path.read_text())
    if contract["status"] != "frozen" or recipe["candidate_id"] != candidate_id:
        raise ValueError("frozen contract/recipe mismatch")
    source_dir = root / "paper_runs/fidelity_formula_components"
    source_manifest = json.loads((source_dir / "manifest.json").read_text())
    source_paths = {name: source_dir / name for name in ["monthly_return_paths.csv", "formation_holdings.csv"]}
    for name, path in source_paths.items():
        if digest(path) != source_manifest["output_sha256"][name]:
            raise ValueError(f"source component evidence changed: {name}")
    original = pd.read_csv(source_paths["monthly_return_paths.csv"])
    months = original.loc[original.candidate_id.eq(candidate_id), ["formation_month", "month", "n_selected"]].copy()
    months["formation_month"], months["month"] = pd.to_datetime(months.formation_month), pd.to_datetime(months.month)
    if len(months) != 305 or months.duplicated("month").any():
        raise ValueError("source component path does not cover the common calendar")
    holdings = load_component_holdings(source_paths["formation_holdings.csv"], candidate_id)
    observed_counts = holdings.groupby("formation_month").size().reindex(months.formation_month, fill_value=0).to_numpy()
    np.testing.assert_array_equal(observed_counts, months.n_selected.to_numpy())
    paths = {policy: reconstruct_paths(months, holdings, policy) for policy in ["zero", "adverse_100"]}
    factors = pd.read_csv(root / contract["factor_panel_path"], parse_dates=["month"])
    settings, attr = contract["starting_settings_retained_from_corrected_us_study"], contract["attribution"]
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack([paths[policy].gross_return.to_numpy() - cost / 10000 * paths[policy].traded_notional.to_numpy()
                         for policy, cost in cases])
    merged = paths["zero"][["month"]].merge(factors, on="month", validate="one_to_one")
    x = merged[contract["factor_columns"]].to_numpy(float)
    reconstruction = rolling_crossfit_reconstruction(x, y, attr["train_months"], attr["validation_months"],
                                                      np.asarray(attr["ridge_lambdas"]), attr["n_unpenalized"])
    eval_dates = paths["zero"].month.iloc[attr["train_months"]:].reset_index(drop=True)
    lags = automatic_hac_lag(len(eval_dates))
    metrics, residual_rows = [], []
    for column, ((policy, cost), name) in enumerate(zip(cases, names)):
        net, residual = y[:, column], reconstruction.residuals[:, column]
        alpha, se = float(residual.mean()), float(hac_mean_se(residual, lags))
        t_value = alpha / se
        p_value = float(2 * norm.sf(abs(t_value)))
        source_path = paths[policy]
        row = {"case": name, "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
               "missing_return_policy": policy, "cost_bps_one_way": cost,
               **{f"full_{key}": value for key, value in return_statistics(net).items()},
               "evaluation_months": len(eval_dates), "evaluation_start": str(eval_dates.iloc[0].date()),
               "evaluation_end": str(eval_dates.iloc[-1].date()), "jkp_residual_mean_annualized": 12 * alpha,
               "jkp_residual_se_annualized": 12 * se, "jkp_residual_t_hac": t_value,
               "jkp_residual_p_two_sided": p_value, "exploratory_bonferroni69_p": min(1.0, 69 * p_value),
               "hac_lags": lags, "average_traded_notional": float(source_path.traded_notional.mean()),
               "annualized_linear_cost_drag": float(12 * cost / 10000 * source_path.traded_notional.mean()),
               "cash_months": int(source_path.n_holdings.eq(0).sum()),
               "maximum_missing_forward_gross_weight": float(source_path.missing_forward_gross_weight.max())}
        metrics.append(row)
        residual_rows.extend({"case": name, "month": str(month.date()), "net_return": float(value),
                              "factor_replication_return": float(fitted), "residual": float(remain),
                              "selected_lambda": float(selected_lambda)}
                             for month, value, fitted, remain, selected_lambda in
                             zip(eval_dates, net[attr["train_months"]:], reconstruction.fitted_values[:, column],
                                 residual, reconstruction.selected_lambdas[:, column]))
    output.mkdir(parents=True, exist_ok=True)
    pd.concat(paths.values(), ignore_index=True).to_csv(output / "monthly_returns.csv", index=False)
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = paths["zero"].copy()
    primary_path["net_return"] = primary_path.gross_return - 0.001 * primary_path.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    report = f'''# {milestone_id}: {recipe['paper']} disclosed component

Status: **completed partial monthly U.S./JKP evaluation**, not the paper's self-improving agent.

The literal published {recipe['headline_component']} formula and its known two-bar-lag behavior are preserved. Monthly cadence, U.S. top-1,000 universe, positive-signal top-10 long-only portfolio, missing-return convention, costs, and benchmark are researcher adaptations. This component was already mapped and evaluated before the new study, so this result is exploratory rather than newly outcome-blind.

At 10 bp one-way costs, the 305-month path has CAGR {primary['full_cagr']:.2%}, annualized Sharpe {primary['full_annualized_sharpe']:.3f}, and maximum drawdown {primary['full_maximum_drawdown']:.2%}. The 185-month rolling JKP133 residual mean is {primary['jkp_residual_mean_annualized']:.2%} annually (HAC t={primary['jkp_residual_t_hac']:.3f}, p={primary['jkp_residual_p_two_sided']:.4f}; descriptive 69-test bound={primary['exploratory_bonferroni69_p']:.4f}).

The result is performance of one disclosed formula component after explicit adaptations. It does not reproduce QuantAgent's LLM idea generation, mentor feedback, self-improvement loop, native daily A-share data, XGBoost/evaluator, final agent strategy, or paper result. It must not be used as evidence that the full agent worked or failed.
'''
    (output / "verdict.md").write_text(report)
    implementation = [Path(__file__).resolve(), root / "scripts/run_fidelity_formula_components.py",
                      root / "src/alpha_evolve/headline_backtest.py", root / "scripts/run_broad_jkp_crossfit.py"]
    relative = [str(path.relative_to(root)) for path in implementation]
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *relative], cwd=root, check=True)
    manifest = {"status": "evaluated_partial", "milestone_id": milestone_id, "candidate_id": candidate_id,
                "completed_at_utc": datetime.now(timezone.utc).isoformat(), "benchmark_id": contract["benchmark_id"],
                "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "contract_sha256": digest(contract_path), "recipe_sha256": digest(recipe_path),
                "source_component_manifest_sha256": digest(source_dir / "manifest.json"),
                "source_component_output_sha256": {name: digest(path) for name, path in source_paths.items()},
                "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                            "platform": platform.system()}, "primary_result": primary,
                "prior_jkp_outcomes_seen": True, "confirmatory_claim": False,
                "implementation_sha256": {str(path.relative_to(root)): digest(path) for path in implementation},
                "output_sha256": {name: digest(output / name) for name in ["monthly_returns.csv", "primary_monthly_returns.csv", "metrics.csv", "attribution_residuals.csv", "verdict.md"]}}
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps(primary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--milestone-id", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    output = args.output if args.output.is_absolute() else args.root / args.output
    evaluate(args.root.resolve(), args.milestone_id, args.candidate_id, output.resolve())


if __name__ == "__main__":
    main()
