#!/usr/bin/env python3
"""Run the frozen M065 FactorMAD-inspired debate miner on U.S./JKP."""

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
from alpha_evolve.in_spirit import factormad_debate_scores
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


MILESTONE_ID = "M065"
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
        raise ValueError("M065 in-spirit run already exists; do not silently overwrite it")
    strict_study = root / "paper_runs/us_jkp_headline"
    contract_path = strict_study / "benchmark_contract.json"
    recipe_path = output / "recipe.json"
    contract = json.loads(contract_path.read_text())
    recipe = json.loads(recipe_path.read_text())
    if recipe["study_id"] != STUDY_ID or recipe["milestone_id"] != MILESTONE_ID:
        raise ValueError("wrong in-spirit recipe")
    if recipe["status"] != "frozen_before_jkp_result":
        raise ValueError("FactorMAD recipe is not frozen")
    if recipe["fidelity_label"] != "in_spirit_reconstruction":
        raise ValueError("FactorMAD result must remain explicitly in-spirit")
    debate_policy = recipe["debate_policy"]
    prediction_model = recipe["prediction_model"]
    if prediction_model["common_or_post_training_returns_used_for_factor_or_model_selection"] is not False:
        raise ValueError("FactorMAD recipe permits common-period feedback")
    if contract["status"] != "frozen":
        raise ValueError("common benchmark contract is not frozen")

    source_path = Path(contract["data"]["path"])
    factor_path = root / contract["factor_panel_path"]
    pinned = {
        recipe["strict_evidence"]["audit_manifest_path"]: recipe["strict_evidence"]["audit_manifest_sha256"],
        recipe["strict_evidence"]["source_provenance_path"]: recipe["strict_evidence"]["source_provenance_sha256"],
        recipe["strict_evidence"]["method_specification_path"]: recipe["strict_evidence"][
            "method_specification_sha256"
        ],
        recipe["strict_evidence"]["component_execution_path"]: recipe["strict_evidence"]["component_execution_sha256"],
        recipe["strict_evidence"]["release_search_path"]: recipe["strict_evidence"]["release_search_sha256"],
    }
    for relative, expected in pinned.items():
        if digest(root / relative) != expected:
            raise ValueError(f"pinned FactorMAD evidence changed: {relative}")
    audit = json.loads((root / recipe["strict_evidence"]["audit_manifest_path"]).read_text())
    provenance = json.loads((root / recipe["strict_evidence"]["source_provenance_path"]).read_text())
    if audit["attributable_implementation_found"] is not False:
        raise ValueError("pinned FactorMAD implementation status changed")
    if provenance["doi"] != "10.1145/3768292.3770377":
        raise ValueError("pinned FactorMAD paper identity changed")
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
    extended_settings["formation_start"] = debate_policy["prehistory_formation_start"]
    grammar = recipe["factor_grammar"]
    features = grammar["seed_features"]
    print("loading FactorMAD training and common formations", flush=True)
    extended = load_formations(source_path, features, extended_settings)
    scores, accepted_factors, debate_history = factormad_debate_scores(
        extended,
        features,
        common_start=settings["formation_start"],
        training_months=debate_policy["training_months"],
        existing_seed_probability=debate_policy["existing_seed_probability"],
        debate_rounds=debate_policy["debate_rounds"],
        maximum_correction_iterations=debate_policy["maximum_correction_iterations"],
        predictive_metric_threshold=debate_policy["predictive_metric_threshold"],
        maximum_rankic_correlation=debate_policy["maximum_rankic_correlation"],
        target_accepted_factors=debate_policy["target_accepted_factors"],
        maximum_debate_episodes=debate_policy["maximum_debate_episodes"],
        random_seed=debate_policy["random_seed"],
        ridge_penalty=prediction_model["ridge_penalty"],
    )
    common_mask = extended["month"].between(settings["formation_start"], settings["formation_end"])
    formed = extended.loc[common_mask].copy()
    scores = scores.loc[formed.index]
    expected_months = pd.date_range(settings["formation_start"], settings["formation_end"], freq="ME")
    if formed["month"].nunique() != len(expected_months) or scores.notna().sum() != len(formed):
        raise ValueError("FactorMAD reconstruction does not cover the fixed formation calendar")
    if len(accepted_factors) != debate_policy["target_accepted_factors"]:
        raise ValueError("FactorMAD reconstruction has an incomplete accepted-factor registry")

    private = root / "artifacts/us_jkp_in_spirit/v1"
    private.mkdir(parents=True, exist_ok=True)
    os.chmod(private, 0o700)
    holdings_path = private / "M065_formation_holdings.parquet"
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
        raise ValueError(f"incomplete FactorMAD path: {bad.to_dict(orient='records')[:5]}")

    factors = pd.read_csv(factor_path, parse_dates=["month"])
    merged = base.merge(factors, on="month", validate="one_to_one")
    attribution = contract["attribution"]
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    case_names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    returns = np.column_stack(
        [
            paths[policy].gross_return.to_numpy() - cost / 10000 * paths[policy].traded_notional.to_numpy()
            for policy, cost in cases
        ]
    )
    if not np.isfinite(returns).all() or (returns <= -1).any():
        raise ValueError("nonfinite or nonpositive-NAV FactorMAD return path")
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
    accepted_factors.to_csv(output / "accepted_factors.csv", index=False)
    debate_history.to_csv(output / "debate_history.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = base.copy()
    primary_path["net_return"] = base.gross_return - 0.001 * base.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    debate_episodes = int(accepted_factors["episode"].max())
    corrected_factors = int(accepted_factors["corrected"].sum())
    seed_source_counts = accepted_factors["seed_source"].value_counts().to_dict()
    complexity_counts = {
        str(int(key)): int(value) for key, value in accepted_factors["complexity"].value_counts().sort_index().items()
    }
    proposer_counts = debate_history["proposer"].value_counts().to_dict()
    strongest_model_weights = (
        accepted_factors.assign(_absolute=accepted_factors["linear_model_weight"].abs())
        .sort_values(["_absolute", "factor"], ascending=[False, True])
        .head(10)
        .set_index("factor")["linear_model_weight"]
        .to_dict()
    )
    verdict = f"""# M065: FactorMAD in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native FactorMAD GPT-4o debates, factor code, or A-share model.

The reconstruction preserves two differently initialized agents, alternating proposal and critique, existing/generated seed branches, ten debate rounds, validator/corrector intervention, predictive and correlation gates, 100 accepted interpretable factors, and a frozen linear prediction model. It required {debate_episodes} episodes, corrected {corrected_factors} factors, used seed sources {seed_source_counts}, and accepted complexity counts {complexity_counts}. All debate feedback and model fitting used only the 120 pre-common training months.

At 10 bp one-way costs, the 305-month path has CAGR {primary["full_cagr"]:.2%}, annualized Sharpe {primary["full_annualized_sharpe"]:.3f}, and maximum drawdown {primary["full_maximum_drawdown"]:.2%}. Mean monthly traded notional is {primary["average_traded_notional"]:.3f}, and minimum signal coverage is {primary["minimum_finite_signal_count"]} stocks.

Across the 185-month rolling JKP attribution window, residual mean return is {primary["jkp_residual_mean_annualized"]:.2%} annually (HAC t={primary["jkp_residual_t_hac"]:.3f}, p={primary["jkp_residual_p_two_sided"]:.4f}, 95% interval [{primary["jkp_residual_ci_low_annualized"]:.2%}, {primary["jkp_residual_ci_high_annualized"]:.2%}]).

This result answers how one transparent FactorMAD-inspired debate pipeline transfers to the common monthly U.S. universe. It does not reproduce the A-share panel, native prompts, GPT-4o responses, generated Python, validator traces, LR/MLP/LightGBM artifacts, overlapping Top-50 sleeves, or paper empirical claims.
"""
    (output / "verdict.md").write_text(verdict)
    if frozen_hashes != {"contract": digest(contract_path), "recipe": digest(recipe_path)}:
        raise RuntimeError("frozen FactorMAD recipe or common contract changed during evaluation")
    outputs = [
        "monthly_returns.csv",
        "primary_monthly_returns.csv",
        "metrics.csv",
        "attribution_residuals.csv",
        "accepted_factors.csv",
        "debate_history.csv",
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
        "candidate_library_size": grammar["candidate_count"],
        "debate_episodes": debate_episodes,
        "accepted_factor_count": len(accepted_factors),
        "debate_record_count": len(debate_history),
        "corrected_factor_count": corrected_factors,
        "seed_source_counts": seed_source_counts,
        "complexity_counts": complexity_counts,
        "proposer_counts": proposer_counts,
        "strongest_model_weights": strongest_model_weights,
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
    output = (args.output or root / "paper_runs/us_jkp_in_spirit/M065_factormad").resolve()
    evaluate(root, output)


if __name__ == "__main__":
    main()
