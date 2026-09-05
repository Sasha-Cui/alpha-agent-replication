#!/usr/bin/env python3
"""Run the frozen M042 Alpha-R1-inspired contextual factor gate on U.S./JKP."""

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
from alpha_evolve.in_spirit import alpha_r1_contextual_gate_scores
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


MILESTONE_ID = "M042"
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
        raise ValueError("M042 in-spirit run already exists; do not silently overwrite it")
    strict_study = root / "paper_runs/us_jkp_headline"
    contract_path = strict_study / "benchmark_contract.json"
    recipe_path = output / "recipe.json"
    contract = json.loads(contract_path.read_text())
    recipe = json.loads(recipe_path.read_text())
    if recipe["study_id"] != STUDY_ID or recipe["milestone_id"] != MILESTONE_ID:
        raise ValueError("wrong in-spirit recipe")
    if recipe["status"] != "frozen_before_jkp_result":
        raise ValueError("Alpha-R1 recipe is not frozen")
    if recipe["fidelity_label"] != "in_spirit_reconstruction":
        raise ValueError("Alpha-R1 result must remain explicitly in-spirit")
    gate_policy = recipe["contextual_gate_policy"]
    if gate_policy["final_common_returns_used_for_policy_choice"] is not False:
        raise ValueError("Alpha-R1 recipe permits final-result selection")
    if contract["status"] != "frozen":
        raise ValueError("common benchmark contract is not frozen")

    source_path = Path(contract["data"]["path"])
    factor_path = root / contract["factor_panel_path"]
    pinned = {
        recipe["strict_evidence"]["audit_manifest_path"]: recipe["strict_evidence"]["audit_manifest_sha256"],
        recipe["strict_evidence"]["native_release_inspection_path"]: recipe["strict_evidence"]["native_release_inspection_sha256"],
        recipe["strict_evidence"]["paper_specification_gaps_path"]: recipe["strict_evidence"]["paper_specification_gaps_sha256"],
        recipe["strict_evidence"]["source_mechanism_conformance_path"]: recipe["strict_evidence"]["source_mechanism_conformance_sha256"],
        recipe["strict_evidence"]["paper_numeric_table_conformance_path"]: recipe["strict_evidence"]["paper_numeric_table_conformance_sha256"],
    }
    for relative, expected in pinned.items():
        if digest(root / relative) != expected:
            raise ValueError(f"pinned Alpha-R1 evidence changed: {relative}")
    audit = json.loads((root / recipe["strict_evidence"]["audit_manifest_path"]).read_text())
    if audit["paper_sha256"] != recipe["paper_source"]["pdf_sha256"]:
        raise ValueError("pinned Alpha-R1 paper identity changed")
    if audit["paper_source_sha256"] != recipe["paper_source"]["source_sha256"]:
        raise ValueError("pinned Alpha-R1 paper source changed")
    if audit["source_commit"] != recipe["paper_source"]["official_commit_checked_2026_09_05"]:
        raise ValueError("pinned Alpha-R1 placeholder commit changed")
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
    extended_settings["formation_start"] = gate_policy["prehistory_formation_start"]
    factor_zoo = recipe["factor_zoo"]
    features = list(dict.fromkeys([item["column"] for item in factor_zoo] + ["niq_su", "saleq_su"]))
    print("loading Alpha-R1 prehistory and common formations", flush=True)
    extended = load_formations(source_path, features, extended_settings)
    scores, gate_history = alpha_r1_contextual_gate_scores(
        extended,
        factor_zoo,
        recipe["semantic_family_affinities"],
        common_start=settings["formation_start"],
        selected_factor_count=gate_policy["selected_factor_count"],
        price_trend_lookback_months=gate_policy["price_trend_lookback_months"],
        volatility_lookback_months=gate_policy["volatility_lookback_months"],
        state_normalization_history_months=gate_policy["state_normalization_history_months"],
        state_zscore_clip=gate_policy["state_zscore_clip"],
        factor_profile_history_months=gate_policy["factor_profile_history_months"],
        minimum_factor_profile_months=gate_policy["minimum_factor_profile_months"],
        factor_profile_reward_purge_months=gate_policy["factor_profile_reward_purge_months"],
        factor_profile_ridge_penalty=gate_policy["factor_profile_ridge_penalty"],
        linear_beta_history_months=gate_policy["linear_beta_history_months"],
        linear_beta_reward_purge_months=gate_policy["linear_beta_reward_purge_months"],
        linear_beta_ridge_fraction=gate_policy["linear_beta_ridge_fraction"],
        performance_gate_weight=gate_policy["performance_gate_weight"],
        semantic_gate_weight=gate_policy["semantic_gate_weight"],
    )
    common_mask = extended["month"].between(settings["formation_start"], settings["formation_end"])
    formed = extended.loc[common_mask].copy()
    scores = scores.loc[formed.index]
    expected_months = pd.date_range(settings["formation_start"], settings["formation_end"], freq="ME")
    if formed["month"].nunique() != len(expected_months) or len(gate_history) != len(expected_months):
        raise ValueError("Alpha-R1 reconstruction does not cover the fixed formation calendar")

    private = root / "artifacts/us_jkp_in_spirit/v1"
    private.mkdir(parents=True, exist_ok=True)
    os.chmod(private, 0o700)
    holdings_path = private / "M042_formation_holdings.parquet"
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
        raise ValueError(f"incomplete Alpha-R1 path: {bad.to_dict(orient='records')[:5]}")

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
        raise ValueError("nonfinite or nonpositive-NAV Alpha-R1 return path")
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
    gate_history.to_csv(output / "gate_history.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = base.copy()
    primary_path["net_return"] = base.gross_return - 0.001 * base.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    selected_lists = gate_history["selected_factors"].str.split("|").tolist()
    selection_frequency = {
        feature: sum(feature in selected for selected in selected_lists)
        for feature in features
    }
    family_by_feature = {item["column"]: item["family"] for item in factor_zoo}
    family_frequency = {
        family: sum(
            family_by_feature[feature] == family
            for selected in selected_lists
            for feature in selected
        )
        for family in recipe["semantic_family_affinities"]
    }
    unique_selected_factors = sum(count > 0 for count in selection_frequency.values())
    most_selected = sorted(selection_frequency, key=lambda name: (-selection_frequency[name], name))[:5]
    most_selected_text = ", ".join(f"{name} ({selection_frequency[name]} months)" for name in most_selected)
    mean_gate_score = float(gate_history["mean_selected_gate_score"].mean())
    mean_absolute_beta = float(gate_history["mean_absolute_selected_beta"].mean())
    unavailable_selected_values = int(gate_history["unavailable_selected_values"].sum())
    verdict = f"""# M042: Alpha-R1 in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native Alpha-R1 Qwen3-8B/GRPO strategy.

The reconstruction preserves a fixed 40-factor zoo, four-year historical linear betas, factor-performance profiles, market memory, contemporaneous price and earnings-news state, context-conditioned sparse activation, group-relative scoring, and ten selected factors. It replaces the unreleased semantic LLM with a causal numerical gate: 60 purged months train each factor's state-to-RankIC profile, fixed economic family affinities supply a semantic prior, and their equally weighted group-relative scores choose ten factors. Across the path, {unique_selected_factors} factors were activated at least once; the five most frequent were {most_selected_text}. Mean selected gate score was {mean_gate_score:.3f} and mean absolute selected beta was {mean_absolute_beta:.5f}.

At 10 bp one-way costs, the 305-month path has CAGR {primary["full_cagr"]:.2%}, annualized Sharpe {primary["full_annualized_sharpe"]:.3f}, and maximum drawdown {primary["full_maximum_drawdown"]:.2%}. Mean monthly traded notional is {primary["average_traded_notional"]:.3f}, and minimum signal coverage is {primary["minimum_finite_signal_count"]} stocks.

Across the 185-month rolling JKP attribution window, residual mean return is {primary["jkp_residual_mean_annualized"]:.2%} annually (HAC t={primary["jkp_residual_t_hac"]:.3f}, p={primary["jkp_residual_p_two_sided"]:.4f}, 95% interval [{primary["jkp_residual_ci_low_annualized"]:.2%}, {primary["jkp_residual_ci_high_annualized"]:.2%}]).

This result answers how one transparent Alpha-R1-inspired contextual factor gate transfers to the common monthly U.S. universe. The official repository still contains only a README promising future code and weights. The reconstruction does not reproduce Qwen3-8B reasoning, GRPO optimization, Alpha101 definitions, Chinese price/news state, daily top-10 rotating slots, VWAP fills, or the paper's native claims; the old favorable five-factor motif was explicitly excluded.
"""
    (output / "verdict.md").write_text(verdict)
    if frozen_hashes != {"contract": digest(contract_path), "recipe": digest(recipe_path)}:
        raise RuntimeError("frozen Alpha-R1 recipe or common contract changed during evaluation")
    outputs = [
        "monthly_returns.csv",
        "primary_monthly_returns.csv",
        "metrics.csv",
        "attribution_residuals.csv",
        "gate_history.csv",
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
        "factor_zoo_count": len(factor_zoo),
        "active_factor_count": gate_policy["selected_factor_count"],
        "policy_update_months": len(gate_history),
        "unique_selected_factors": unique_selected_factors,
        "selection_frequency": selection_frequency,
        "family_selection_frequency": family_frequency,
        "mean_selected_gate_score": mean_gate_score,
        "mean_absolute_selected_beta": mean_absolute_beta,
        "unavailable_selected_values": unavailable_selected_values,
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
    output = (args.output or root / "paper_runs/us_jkp_in_spirit/M042_alpha_r1").resolve()
    evaluate(root, output)


if __name__ == "__main__":
    main()
