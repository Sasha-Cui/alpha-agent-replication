#!/usr/bin/env python3
"""Run the frozen M003 FAMA-inspired symbolic reconstruction on U.S./JKP."""
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

from alpha_evolve.headline_backtest import build_strategy_path, load_formations, return_statistics
from alpha_evolve.in_spirit import fama_candidate_library, fama_rolling_scores, monthly_rankic
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


MILESTONE_ID = "M003"
STUDY_ID = "us_jkp_in_spirit_v1"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def evaluate(root: Path, output: Path) -> None:
    if (output / "run_manifest.json").exists():
        raise ValueError("M003 in-spirit run already exists; do not silently overwrite it")
    strict_study = root / "paper_runs/us_jkp_headline"
    contract_path = strict_study / "benchmark_contract.json"
    recipe_path = output / "recipe.json"
    contract = json.loads(contract_path.read_text())
    recipe = json.loads(recipe_path.read_text())
    if recipe["study_id"] != STUDY_ID or recipe["milestone_id"] != MILESTONE_ID:
        raise ValueError("wrong in-spirit recipe")
    if recipe["status"] != "frozen_before_jkp_result":
        raise ValueError("FAMA recipe is not frozen")
    if recipe["fidelity_label"] != "in_spirit_reconstruction":
        raise ValueError("FAMA result must remain explicitly in-spirit")
    selection = recipe["chronological_selection"]
    if selection["final_common_returns_used_for_selection"] is not False:
        raise ValueError("FAMA recipe permits final-result selection")
    if contract["status"] != "frozen":
        raise ValueError("common benchmark contract is not frozen")

    source_path = Path(contract["data"]["path"])
    factor_path = root / contract["factor_panel_path"]
    pinned = {
        recipe["paper_source"]["path"]: recipe["paper_source"]["sha256"],
        recipe["strict_evidence"]["audit_manifest_path"]: recipe["strict_evidence"]["audit_manifest_sha256"],
        recipe["strict_evidence"]["initial_factor_inventory_path"]: recipe["strict_evidence"]["initial_factor_inventory_sha256"],
    }
    for relative, expected in pinned.items():
        if digest(root / relative) != expected:
            raise ValueError(f"pinned FAMA evidence changed: {relative}")
    if digest(source_path) != contract["data"]["expected_sha256_from_existing_lock"]:
        raise ValueError("JKP input hash differs from the common contract")
    if digest(factor_path) != contract["factor_panel_sha256"]:
        raise ValueError("JKP factor panel differs from the common contract")

    implementation = [
        Path(__file__).resolve(),
        root / "src/alpha_evolve/in_spirit.py",
        root / "src/alpha_evolve/headline_backtest.py",
        root / "src/alpha_evolve/submission_analysis.py",
        root / "scripts/run_broad_jkp_crossfit.py",
    ]
    tracked = [str(path.relative_to(root)) for path in implementation]
    subprocess.run(["git", "ls-files", "--error-unmatch", *tracked], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *tracked, str(recipe_path.relative_to(root))],
        cwd=root,
        check=True,
    )
    code_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    frozen_hashes = {"contract": digest(contract_path), "recipe": digest(recipe_path)}

    settings = contract["starting_settings_retained_from_corrected_us_study"]
    extended_settings = dict(settings)
    extended_settings["formation_start"] = selection["prehistory_formation_start"]
    seeds = recipe["seed_characteristics"]
    print("loading FAMA prehistory and common formations", flush=True)
    extended = load_formations(source_path, seeds, extended_settings)
    candidates = fama_candidate_library(extended, seeds)
    if candidates.shape[1] != recipe["symbolic_grammar"]["total_candidates"]:
        raise ValueError("FAMA candidate grammar changed")
    print("computing candidate RankIC histories", flush=True)
    rankics = monthly_rankic(extended, candidates)
    scores, selection_history = fama_rolling_scores(
        extended,
        candidates,
        rankics,
        common_start=settings["formation_start"],
        training_months=selection["training_window_months"],
        minimum_rankic_months=selection["minimum_finite_rankic_months"],
        cluster_count=selection["cluster_count"],
        selected_cross_samples=selection["selected_cross_samples"],
    )
    common_mask = extended["month"].between(settings["formation_start"], settings["formation_end"])
    formed = extended.loc[common_mask].copy()
    scores = scores.loc[formed.index]
    expected_months = pd.date_range(settings["formation_start"], settings["formation_end"], freq="ME")
    if formed["month"].nunique() != len(expected_months) or len(selection_history) != len(expected_months):
        raise ValueError("FAMA reconstruction does not cover the fixed formation calendar")

    private = root / "artifacts/us_jkp_in_spirit/v1"
    private.mkdir(parents=True, exist_ok=True)
    os.chmod(private, 0o700)
    holdings_path = private / "M003_formation_holdings.parquet"
    paths: dict[str, pd.DataFrame] = {}
    for policy in ("zero", "adverse_100"):
        path, holdings = build_strategy_path(formed, scores, settings, policy)
        path.insert(0, "missing_return_policy", policy)
        paths[policy] = path
        if policy == "zero":
            holdings.to_parquet(holdings_path, index=False)
    base = paths["zero"]
    if not base.path_status.eq("ok").all():
        bad = base.loc[base.path_status.ne("ok"), ["formation_month", "path_status", "finite_signal_count"]]
        raise ValueError(f"incomplete FAMA path: {bad.to_dict(orient='records')[:5]}")

    factors = pd.read_csv(factor_path, parse_dates=["month"])
    merged = base.merge(factors, on="month", validate="one_to_one")
    attribution = contract["attribution"]
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    case_names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    returns = np.column_stack(
        [
            paths[policy].gross_return.to_numpy()
            - cost / 10000 * paths[policy].traded_notional.to_numpy()
            for policy, cost in cases
        ]
    )
    if not np.isfinite(returns).all() or (returns <= -1).any():
        raise ValueError("nonfinite or nonpositive-NAV FAMA return path")
    reconstruction = rolling_crossfit_reconstruction(
        merged[contract["factor_columns"]].to_numpy(float),
        returns,
        attribution["train_months"],
        attribution["validation_months"],
        np.asarray(attribution["ridge_lambdas"]),
        attribution["n_unpenalized"],
    )
    evaluation_dates = base.month.iloc[attribution["train_months"] :].reset_index(drop=True)
    lags = automatic_hac_lag(len(evaluation_dates))
    metrics: list[dict] = []
    residual_rows: list[dict] = []
    for column, ((policy, cost), case_name) in enumerate(zip(cases, case_names)):
        candidate = paths[policy]
        net = returns[:, column]
        residual = reconstruction.residuals[:, column]
        mean = float(residual.mean())
        se = float(hac_mean_se(residual, lags))
        t_value = mean / se
        p_value = float(2 * norm.sf(abs(t_value)))
        row = {
            "case": case_name,
            "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
            "missing_return_policy": policy,
            "cost_bps_one_way": cost,
            **{f"full_{key}": value for key, value in return_statistics(net).items()},
            **{
                f"evaluation_{key}": value
                for key, value in return_statistics(net[attribution["train_months"] :]).items()
            },
            "evaluation_start": str(evaluation_dates.iloc[0].date()),
            "evaluation_end": str(evaluation_dates.iloc[-1].date()),
            "jkp_residual_mean_annualized": 12 * mean,
            "jkp_residual_se_annualized": 12 * se,
            "jkp_residual_t_hac": t_value,
            "jkp_residual_p_two_sided": p_value,
            "jkp_residual_ci_low_annualized": 12 * (mean - 1.959963984540054 * se),
            "jkp_residual_ci_high_annualized": 12 * (mean + 1.959963984540054 * se),
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
                "case": case_name,
                "month": str(month.date()),
                "net_return": float(value),
                "factor_replication_return": float(fitted),
                "residual": float(remaining),
                "selected_lambda": float(selected_lambda),
            }
            for month, value, fitted, remaining, selected_lambda in zip(
                evaluation_dates,
                net[attribution["train_months"] :],
                reconstruction.fitted_values[:, column],
                residual,
                reconstruction.selected_lambdas[:, column],
            )
        )

    output.mkdir(parents=True, exist_ok=True)
    pd.concat(paths.values(), ignore_index=True).to_csv(output / "monthly_returns.csv", index=False)
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    selection_history.to_csv(output / "selection_history.csv", index=False)
    catalog = pd.DataFrame(
        {
            "candidate_id": candidates.columns,
            "operator": [name.split("__", 1)[0] for name in candidates.columns],
        }
    )
    catalog.to_csv(output / "candidate_catalog.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = base.copy()
    primary_path["net_return"] = base.gross_return - 0.001 * base.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    most_used = selection_history["selected_1"].value_counts().head(3)
    leaders = ", ".join(f"`{name}` ({count} months)" for name, count in most_used.items())
    verdict = f"""# M003: FAMA in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native FAMA replication.

The reconstruction preserves FAMA's price/volume symbolic-factor domain, RankIC objective, seven correlation-diversity groups, two cross-samples, and RankICIR-ordered experience selection. Six available JKP characteristics seed a fixed 51-expression arithmetic grammar. Every month, only the preceding 60 realized RankIC observations select and orient two representatives; their cross-sectional ranks form the common score. The unreleased text-davinci-002 generator, original 38-factor set, paper data, and private experience chains are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR {primary['full_cagr']:.2%}, annualized Sharpe {primary['full_annualized_sharpe']:.3f}, and maximum drawdown {primary['full_maximum_drawdown']:.2%}. Mean monthly traded notional is {primary['average_traded_notional']:.3f}, and minimum signal coverage is {primary['minimum_finite_signal_count']} stocks. The most frequent first experience representatives are {leaders}.

Across the 185-month rolling JKP attribution window, residual mean return is {primary['jkp_residual_mean_annualized']:.2%} annually (HAC t={primary['jkp_residual_t_hac']:.3f}, p={primary['jkp_residual_p_two_sided']:.4f}, 95% interval [{primary['jkp_residual_ci_low_annualized']:.2%}, {primary['jkp_residual_ci_high_annualized']:.2%}]).

This result answers how one transparent FAMA-inspired search transfers to the common task. It does not reproduce or validate the paper's private factors, 38.4% return, RankIC, RankICIR, or model comparison claims.
"""
    (output / "verdict.md").write_text(verdict)
    if frozen_hashes != {"contract": digest(contract_path), "recipe": digest(recipe_path)}:
        raise RuntimeError("frozen FAMA recipe or common contract changed during evaluation")
    outputs = [
        "monthly_returns.csv",
        "primary_monthly_returns.csv",
        "metrics.csv",
        "attribution_residuals.csv",
        "selection_history.csv",
        "candidate_catalog.csv",
        "verdict.md",
    ]
    manifest = {
        "status": "evaluated_in_spirit",
        "study_id": STUDY_ID,
        "milestone_id": MILESTONE_ID,
        "fidelity_label": recipe["fidelity_label"],
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": contract["benchmark_id"],
        "code_commit": code_commit,
        "contract_sha256": frozen_hashes["contract"],
        "recipe_sha256": frozen_hashes["recipe"],
        "input_sha256": digest(source_path),
        "benchmark_sha256": digest(factor_path),
        "paper_evidence_sha256": pinned,
        "candidate_count": candidates.shape[1],
        "selection_months": len(selection_history),
        "private_holdings_path": str(holdings_path),
        "private_holdings_sha256": digest(holdings_path),
        "prior_jkp_outcomes_seen": True,
        "confirmatory_claim": False,
        "native_paper_result_claim": False,
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.system(),
        },
        "primary_result": primary,
        "implementation_sha256": {str(path.relative_to(root)): digest(path) for path in implementation},
        "output_sha256": {name: digest(output / name) for name in outputs},
    }
    write_json(output / "run_manifest.json", manifest)
    print(json.dumps(primary, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output or root / "paper_runs/us_jkp_in_spirit/M003_fama").resolve()
    evaluate(root, output)


if __name__ == "__main__":
    main()
