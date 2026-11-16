#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Complete matched-pool comparisons and explicitly limited JKP diagnostics."""

from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_economics import cash_account
from alpha_evolve.publication_inference import grouped_t_effect, ols_alpha, chronological_projection
from alpha_evolve.publication_portfolio import walk_forward_augmentation
from alpha_evolve.fidelity_inference_v2 import adjust_grouped_family
from alpha_evolve.fidelity_efs_pool_evidence_v2 import validate_efs_trial
from alpha_evolve.fidelity_efs_grammar_pool_v2 import require_same_financial_block
from analyze_publication_upgrade import metrics

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def read(path):
    return json.loads(path.read_text())


def strict_pair(left, right):
    if left.index.has_duplicates or not left.index.is_monotonic_increasing or not left.index.equals(right.index):
        raise ValueError("Exact complete paired calendars required; no intersection/dropna")
    if not np.isfinite(np.c_[left, right]).all() or (left <= -1).any() or (right <= -1).any():
        raise ValueError("Invalid independently accounted path")
    return left - right


def month_path(value):
    months = (1 + value).groupby(value.index.to_period("M")).prod() - 1
    if not months.index.equals(pd.period_range("2019-01", "2024-12", freq="M")):
        raise ValueError("Expected all72fixed calendar months")
    return months


def load_market(path):
    raw = pd.read_parquet(path)
    market = (
        raw.pivot(index="date", columns="ticker", values="ret")
        .sort_index()
        .reindex(columns=sorted(raw.ticker.unique()))
    )
    # Real input uses Arrow date32/Python datetime.date, whereas CSV accounts
    # parse to Timestamp. Normalize the index representation, never its values.
    market.index = pd.DatetimeIndex(market.index, name=market.index.name)
    if market.index.has_duplicates or not market.index.is_monotonic_increasing:
        raise ValueError("Invalid source market calendar")
    return market.loc["2019-01-01":"2024-12-31"]


def load_pool(group, market):
    folder = PUBLIC / "efs_pooled" / group
    private = PRIVATE / "efs_pooled" / group
    done = read(folder / "completion.json")
    if done["status"] != "complete" or not done["causal_discovery_gating"] or done["new_model_calls"] != 0:
        raise ValueError("Pool incomplete or chronology unsupported")
    for name, digest in done["output_sha256"].items():
        if sha256(folder / name) != digest:
            raise ValueError("Pooled output changed")
    for name, digest in done["private_weights_sha256"].items():
        if sha256(private / name) != digest:
            raise ValueError("Pooled weights changed")
    if group == "grammar_101_103":
        if done["control_seeds"] != [101, 102, 103]:
            raise ValueError("Unplanned control pool")
        if done["script_sha256"] != sha256(ROOT / "scripts/evaluate_efs_grammar_pool_v2.py"):
            raise ValueError("Executed control pool source changed")
    else:
        expected = (
            ["gpt41_1", "gpt41_2", "gpt41_3"]
            if group == "gpt41"
            else ["deepseek_v3_1", "deepseek_v3_2", "deepseek_v3_3"]
        )
        if done["trials"] != expected:
            raise ValueError("Missing or substituted model trial")
        for trial in expected:
            if validate_efs_trial(ROOT, trial) != done["source_proofs"][trial]:
                raise ValueError("Source/replay binding differs from evaluated pool")
        if done["script_sha256"] != sha256(ROOT / "scripts/evaluate_efs_pool_v2.py"):
            raise ValueError("Executed LLM pool source changed")
    pool_protocol = (
        PUBLIC / "efs_final_analysis_protocol.json" if group == "grammar_101_103" else PUBLIC / "efs_pool_protocol.json"
    )
    if done["protocol_sha256"] != sha256(pool_protocol):
        raise ValueError("Executed pool protocol changed")
    if group != "grammar_101_103":
        reference = read(ROOT / "paper_runs/economic_fidelity/efs_v1/recipe.json")
        fields = read(PUBLIC / "efs_pool_protocol.json")["shared_engine_fields"]
        for trial in expected:
            recipe_folder = (
                ROOT / "paper_runs/economic_fidelity/efs_v1" if trial == "gpt41_1" else PUBLIC / "efs" / trial
            )
            actual = read(recipe_folder / "recipe.json")
            if any(actual[key] != reference[key] for key in fields):
                raise ValueError("LLM/control source economic settings differ")
    paths = {}
    maximum = 0.0
    for mode in ["causal_discovery_gated", "retrospective_final_union_diagnostic"]:
        raw = pd.read_csv(folder / (mode + "_daily_returns.csv"), parse_dates=["date"]).set_index("date")
        weights = pd.read_parquet(private / (mode + "_weights.parquet"))
        if (
            not raw.index.equals(market.index)
            or not weights.index.equals(market.index)
            or list(weights.columns) != list(market.columns)
        ):
            raise ValueError("Pooled account calendar/universe differs from frozen market")
        selections = read(folder / (mode + "_selections.json"))
        if [r["execution_date"] for r in selections] != [str(d.date()) for d in market.index]:
            raise ValueError("Selection calendar mismatch")
        if mode == "causal_discovery_gated" and any(r["selected_future_discoveries"] for r in selections):
            raise ValueError("Future-discovered factor used")
        for cost in [0, 10, 25, 50]:
            value, _, _ = cash_account(weights.to_numpy(), market.to_numpy(), cost)
            error = float(np.max(np.abs(value - raw["total_cost_" + str(cost)])))
            maximum = max(maximum, error)
            if error > 1e-12:
                raise ValueError("Independent pool re-accounting differs from saved return")
            paths[(mode, cost)] = raw["total_cost_" + str(cost)]
    return paths, {
        "group": group,
        "completion_sha256": sha256(folder / "completion.json"),
        "maximum_reaccounting_difference": maximum,
        "library_factors": done["library_factors"],
    }


def main():
    out = PUBLIC / "efs_pooled_analysis"
    private = PRIVATE / "efs_pooled_analysis"
    if (out / "completion.json").exists():
        raise ValueError("Preserve completed EFS analysis")
    protocol_path = PUBLIC / "efs_final_analysis_protocol.json"
    plan = read(protocol_path)
    if plan["inference"]["project_family_size"] != 4 or plan["matched_grammar_pool_seeds"] != [101, 102, 103]:
        raise ValueError("Frozen comparison population changed")
    computation = require_same_financial_block(
        (ROOT / "scripts/evaluate_efs_pool_v2.py").read_text(),
        (ROOT / "scripts/evaluate_efs_grammar_pool_v2.py").read_text(),
    )
    raw_path = ROOT / "artifacts/economic_fidelity/v1/efs_us50_daily.parquet"
    data_manifest = read(raw_path.with_name("data_manifest.json"))
    if sha256(raw_path) != data_manifest["daily_extract_sha256"]:
        raise ValueError("Frozen market panel changed")
    market = load_market(raw_path)
    if len(market) != 1510 or market.shape[1] != 50:
        raise ValueError("Expected fixed1510dayUS50panel")
    pools = {}
    evidence = []
    for group in ["grammar_101_103", "gpt41", "deepseek_v3"]:
        pools[group], proof = load_pool(group, market)
        evidence.append(proof)
    benchmark = pools["grammar_101_103"][("causal_discovery_gated", 10)]
    benchmark_monthly = month_path(benchmark)
    primary = []
    performance = []
    descriptive = []
    daily = []
    attribution = []
    reconstruction = []
    allocation = []
    factors_path = ROOT / plan["jkp"]["factor_file"]
    if sha256(factors_path) != plan["jkp"]["factor_sha256"]:
        raise ValueError("Frozen JKP panel changed")
    factors = pd.read_csv(factors_path)
    factors.index = pd.to_datetime(factors.realization_month).dt.to_period("M")
    columns = ["capm_top1000_mkt"] + [c for c in factors if c.startswith("char__")]
    if len(columns) != 133 or factors.index.has_duplicates:
        raise ValueError("Expected unique full JKP132 plus market panel")
    factors = factors.loc[benchmark_monthly.index, columns]
    if not factors.index.equals(benchmark_monthly.index) or not np.isfinite(factors.to_numpy()).all():
        raise ValueError("Incomplete factor calendar; no dropping months")
    core = plan["jkp"]["low_dimensional_diagnostic"]
    private.mkdir(parents=True, exist_ok=True)
    for group, paths in pools.items():
        for (mode, cost), value in paths.items():
            strict_pair(value, benchmark)
            performance.append({"group": group, "mode": mode, "cost_bps": cost, **metrics(value, frequency=252)})
            daily.append(value.rename("return").reset_index().assign(group=group, mode=mode, cost_bps=cost))
        if group == "grammar_101_103":
            continue
        causal = paths[("causal_discovery_gated", 10)]
        monthly = month_path(causal)
        strict_pair(monthly, benchmark_monthly)
        result = grouped_t_effect(
            monthly.to_numpy(), benchmark_monthly.to_numpy(), frequency=12, groups=4, threshold=0.02, confidence=0.99
        )
        result["within_economic_margin_using_pointwise99"] = result.pop("equivalent_within_margin_tost5")
        result["rules_out_positive_margin_using_pointwise99"] = result.pop("rules_out_positive_margin_one_sided5")
        primary.append(
            {
                "case": "efs_" + group + "_pooled_minus_matched_grammar_pool",
                "backend": group,
                "role": "prespecified_project_economic_contrast",
                "baseline": "three_trajectory_causal_grammar_pool",
                "frequency": 12,
                **result,
            }
        )
        difference = monthly - benchmark_monthly
        try:
            full = ols_alpha(difference.to_numpy(), factors.to_numpy(), frequency=12)
        except ValueError as error:
            attribution.append(
                {
                    "backend": group,
                    "model": "JKP132_plus_market",
                    "status": "not_identified",
                    "months": 72,
                    "regressors_plus_intercept": 134,
                    "reason": str(error),
                }
            )
        else:
            raise ValueError("Underidentified134parameter/72month OLS was incorrectly accepted: " + str(full))
        try:
            small = grouped_t_effect(
                difference.to_numpy(),
                factors=factors[core].to_numpy(),
                frequency=12,
                groups=4,
                threshold=0.02,
                confidence=0.99,
            )
            small["within_economic_margin_using_pointwise99"] = small.pop("equivalent_within_margin_tost5")
            small["rules_out_positive_margin_using_pointwise99"] = small.pop("rules_out_positive_margin_one_sided5")
            attribution.append(
                {
                    "backend": group,
                    "model": "prespecified_six_factor_projection",
                    "status": "conditional_low_dimensional_diagnostic",
                    "not_JKP132_alpha": True,
                    "not_in_primary_discovery_family": True,
                    **small,
                }
            )
        except ValueError as error:
            attribution.append(
                {
                    "backend": group,
                    "model": "prespecified_six_factor_projection",
                    "status": "insufficient_for_grouped_diagnostic",
                    "reason": str(error),
                    "no_JKP132_alpha_claim": True,
                }
            )
        for name, components in [("ridge_all_factors", None), ("pca5_ridge", 5)]:
            projected = chronological_projection(
                difference.to_numpy(), factors.to_numpy(), min_train=36, penalty=10, components=components
            )
            reconstruction.append(
                {
                    "backend": group,
                    "model": name,
                    **{k: v for k, v in projected.items() if k not in ["predictions", "residual"]},
                    "not_a_tradable_forecast": True,
                    "no_unrestricted_alpha_p_value": True,
                }
            )
            pd.DataFrame(
                {
                    "month": difference.index[36:].astype(str),
                    "difference": difference.iloc[36:].to_numpy(),
                    "reconstructed": projected["predictions"][36:],
                    "residual": projected["residual"],
                }
            ).to_csv(private / (group + "_" + name + "_reconstruction.csv"), index=False)
        # Allocation uses only pre-month history for all exposures; it remains
        # synthetic gross-factor evidence because factor/financing costs are absent.
        alloc = walk_forward_augmentation(
            factors.to_numpy(), monthly.to_numpy(), min_train=36, risk_aversion=10, shrinkage=0.5, target_asset_vol=0.10
        )
        months = monthly.index[36:]
        alloc_path = pd.DataFrame(alloc["returns"], index=months.astype(str), columns=["jkp_only", "jkp_plus_efs"])
        alloc_path.index.name = "month"
        alloc_path.to_csv(private / (group + "_allocation_returns.csv"))
        np.savez_compressed(
            private / (group + "_allocation_weights.npz"),
            weights=alloc["weights"],
            months=months.astype(str).to_numpy(dtype=str),
            sleeves=np.asarray(columns + ["efs_agent"]),
        )
        for i, arm in enumerate(["jkp_only", "jkp_plus_efs"]):
            r = alloc["returns"][:, i]
            allocation.append(
                {
                    "backend": group,
                    "arm": arm,
                    "months": len(r),
                    "evaluation_start": str(months[0]),
                    "evaluation_end": str(months[-1]),
                    "mean_annualized": float(12 * r.mean()),
                    "vol_annualized": float(np.sqrt(12) * r.std(ddof=1)),
                    "certainty_equivalent_gamma10_annualized": float(12 * (r.mean() - 5 * r.var(ddof=1))),
                    "mean_agent_weight_in_input_units": float(alloc["weights"][:, i, -1].mean()),
                    "parameters": alloc["parameters"],
                    "claim_boundary": alloc["claim_boundary"],
                    "no_alpha_p_value": True,
                }
            )
        for cost in [0, 10, 25, 50]:
            left = paths[("causal_discovery_gated", cost)]
            right = pools["grammar_101_103"][("causal_discovery_gated", cost)]
            strict_pair(left, right)
            descriptive.append(
                {
                    "backend": group,
                    "contrast": "causal_LLM_pool_minus_causal_grammar_pool",
                    "cost_bps": cost,
                    "full_sample_annualized_monthly_mean_increment": float(
                        12 * (month_path(left) - month_path(right)).mean()
                    ),
                    "cumulative_return_difference": float((1 + left).prod() - (1 + right).prod()),
                    "descriptive_only": True,
                }
            )
    # The identical allocator also receives the matched grammar sleeve. Its
    # common JKP-only baseline must agree with both LLM diagnostics exactly.
    alloc = walk_forward_augmentation(
        factors.to_numpy(),
        benchmark_monthly.to_numpy(),
        min_train=36,
        risk_aversion=10,
        shrinkage=0.5,
        target_asset_vol=0.10,
    )
    months = benchmark_monthly.index[36:]
    for group in ["gpt41", "deepseek_v3"]:
        check = pd.read_csv(private / (group + "_allocation_returns.csv")).jkp_only.to_numpy()
        if not np.allclose(check, alloc["returns"][:, 0], rtol=0, atol=1e-14):
            raise ValueError("Supposedly common JKP baseline differs across agent sleeves")
    pd.DataFrame(alloc["returns"], index=months.astype(str), columns=["jkp_only", "jkp_plus_grammar"]).rename_axis(
        "month"
    ).to_csv(private / "grammar_allocation_returns.csv")
    np.savez_compressed(
        private / "grammar_allocation_weights.npz",
        weights=alloc["weights"],
        months=months.astype(str).to_numpy(dtype=str),
        sleeves=np.asarray(columns + ["grammar_agent"]),
    )
    for i, arm in enumerate(["jkp_only", "jkp_plus_grammar"]):
        r = alloc["returns"][:, i]
        allocation.append(
            {
                "backend": "grammar_101_103",
                "arm": arm,
                "months": len(r),
                "evaluation_start": str(months[0]),
                "evaluation_end": str(months[-1]),
                "mean_annualized": float(12 * r.mean()),
                "vol_annualized": float(np.sqrt(12) * r.std(ddof=1)),
                "certainty_equivalent_gamma10_annualized": float(12 * (r.mean() - 5 * r.var(ddof=1))),
                "mean_agent_weight_in_input_units": float(alloc["weights"][:, i, -1].mean()),
                "parameters": alloc["parameters"],
                "claim_boundary": alloc["claim_boundary"],
                "no_alpha_p_value": True,
            }
        )
    for row in allocation:
        row["common_jkp_only_baseline_verified"] = True
        row["repeated_baseline_is_not_an_independent_fit"] = True
    # Keep all frozen individual controls and all LLM trials, without selection.
    controls = ROOT / "artifacts/publication_upgrade_v1/efs_controls/daily_returns.parquet"
    control_data = pd.read_parquet(controls)
    for arm in ["initial", "equal_weight"]:
        chosen = control_data.loc[
            (control_data.arm == arm) & (control_data.cadence == "daily") & (control_data.cost_bps == 10)
        ]
        value = pd.Series(chosen["return"].to_numpy(), index=pd.DatetimeIndex(chosen.date))
        strict_pair(value, benchmark)
        performance.append(
            {
                "group": "frozen_" + arm,
                "mode": "descriptive_control",
                "cost_bps": 10,
                "source_sha256": sha256(controls),
                **metrics(value),
            }
        )
    for seed in range(101, 111):
        folder = ROOT / f"artifacts/publication_upgrade_v1/efs_matched/seed_{seed}"
        done = read(folder / "completion.json")
        path = folder / "daily_returns.csv"
        if sha256(path) != done["returns_sha256"]:
            raise ValueError("Frozen individual control changed")
        frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
        strict_pair(frame.total_cost_10, benchmark)
        performance.append(
            {
                "group": "grammar_seed_" + str(seed),
                "mode": "single_trial_descriptive",
                "cost_bps": 10,
                "source_sha256": sha256(path),
                **metrics(frame.total_cost_10),
            }
        )
    for group in ["gpt41", "deepseek_v3"]:
        trials = (
            ["gpt41_1", "gpt41_2", "gpt41_3"]
            if group == "gpt41"
            else ["deepseek_v3_1", "deepseek_v3_2", "deepseek_v3_3"]
        )
        for trial in trials:
            folder = ROOT / "paper_runs/economic_fidelity/efs_v1" if trial == "gpt41_1" else PUBLIC / "efs" / trial
            frame = pd.read_csv(folder / "llm_daily_returns.csv", parse_dates=["date"]).set_index("date")
            strict_pair(frame.total_cost_10, benchmark)
            performance.append(
                {"group": trial, "mode": "single_trial_descriptive", "cost_bps": 10, **metrics(frame.total_cost_10)}
            )
    inputs, adjusted = adjust_grouped_family(primary, 4, False)
    for row, p_input, p in zip(primary, inputs, adjusted):
        row.update(
            project_family_p_input=p_input,
            conservative_project_family_p=p,
            project_family_status="partial_requires_native_AlphaAgent_and_Quanta_results",
            positive_pointwise99_and_project_bound_below001=bool(
                row["primary_ci_low"] > 0 and p < 0.01 and not row["degenerate_sampling_variation"]
            ),
        )
    out.mkdir(exist_ok=True)
    for name, rows in [
        ("primary_comparisons", primary),
        ("performance", performance),
        ("descriptive_comparisons", descriptive),
        ("factor_attribution_diagnostics", attribution),
        ("chronological_reconstruction_diagnostics", reconstruction),
        ("gross_factor_allocation_diagnostics", allocation),
        ("execution_evidence", evidence),
    ]:
        atomic_json(out / (name + ".json"), rows)
    pd.concat(daily, ignore_index=True).to_csv(out / "daily_pool_returns.csv", index=False)
    atomic_json(
        out / "completion.json",
        {
            "status": "both_efs_pooled_cases_complete_project_family_pending",
            "protocol_sha256": sha256(protocol_path),
            "script_sha256": sha256(Path(__file__)),
            "factor_panel_sha256": sha256(factors_path),
            "monthly_calibration_reference_sha256": sha256(PUBLIC / "efs_monthly_inference_reference.json"),
            "matched_financial_block_sha256": computation,
            "months": 72,
            "days": 1510,
            "new_model_calls": 0,
            "full_original_paper_reproduced": False,
            "pristine_confirmation": False,
            "JKP132_unrestricted_alpha_identified": False,
            "outputs": {p.name: sha256(p) for p in out.iterdir() if p.is_file() and p.name != "completion.json"},
            "private_outputs": {p.name: sha256(p) for p in private.iterdir() if p.is_file()},
        },
    )
    print("EFS_POOLED_ANALYSIS_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
