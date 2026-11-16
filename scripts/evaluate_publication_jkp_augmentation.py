#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
import numpy as np
from alpha_evolve.publication_portfolio import walk_forward_augmentation
from alpha_evolve.openrouter_budget import atomic_json, sha256

OUT = ROOT / "paper_runs/publication_upgrade_v1/jkp_allocation_diagnostic"
OUT.mkdir(parents=True, exist_ok=True)
recipe = {
    "agent": "EFS fixed daily LLM path, aggregated to months, net of 10bp trading costs",
    "benchmark": "All 132 reconstructed JKP characteristic portfolios plus the provided top-1000 market portfolio",
    "minimum_training_months": 36,
    "covariance_diagonal_shrinkage": 0.5,
    "risk_aversion": 10.0,
    "per_sleeve_ex_ante_vol_target": 0.10,
    "risk_budget_l1_cap": 1.0,
    "agent_weight_constraint": "nonnegative",
    "factor_weight_constraint": "signed",
    "fees_boundary": "Agent internal 10bp fees are included. Factor internal turnover/financing and allocation changes are not costed; this is a synthetic gross-factor diagnostic.",
    "interpretation": "A comparison for this fixed regularized allocation rule, not a test of unrestricted factor spanning or the best attainable factor frontier.",
    "fixed_before_allocator_results": True,
}
atomic_json(OUT / "recipe.json", recipe)
factor_path = ROOT / "paper_runs/prompt_replay/guruagents/performance/factor_panel_extended_realization.csv"
agent_path = ROOT / "paper_runs/economic_fidelity/efs_v1/llm_monthly_returns.csv"
f = pd.read_csv(factor_path)
f.index = pd.to_datetime(f.realization_month).dt.to_period("M")
columns = ["capm_top1000_mkt"] + [c for c in f if c.startswith("char__")]
a = pd.read_csv(agent_path)
a.index = pd.to_datetime(a.month).dt.to_period("M")
joined = f[columns].join(a[["total_cost_10"]], how="inner").dropna()
if len(columns) != 133 or len(joined) != 72:
    raise ValueError("Unexpected JKP/EFS common panel")
result = walk_forward_augmentation(joined[columns].to_numpy(), joined.total_cost_10.to_numpy(), min_train=36)
months = joined.index[result["start_index"] :].to_timestamp("M")
paths = pd.DataFrame(result["returns"], index=months, columns=["jkp_only", "jkp_plus_efs"])
paths.index.name = "month"
paths.to_csv(OUT / "monthly_returns.csv")
weights = result["weights"]
rows = []
for i, date in enumerate(months):
    for arm, name in enumerate(["jkp_only", "jkp_plus_efs"]):
        for label, weight in zip(columns + ["efs_agent"], weights[i, arm]):
            rows.append(
                {"month": str(date.date()), "arm": name, "sleeve": label, "weight_in_input_return_units": weight}
            )
pd.DataFrame(rows).to_csv(OUT / "monthly_sleeve_exposures.csv", index=False)
summary = []
for arm in paths:
    r = paths[arm].to_numpy()
    summary.append(
        {
            "arm": arm,
            "months": len(r),
            "mean_annualized": 12 * r.mean(),
            "vol_annualized": np.sqrt(12) * r.std(ddof=1),
            "cagr": float(np.expm1(np.log1p(r).mean() * 12)),
            "certainty_equivalent_gamma10_annualized": 12 * (r.mean() - 5 * r.var(ddof=1)),
        }
    )
pd.DataFrame(summary).to_csv(OUT / "metrics.csv", index=False)
atomic_json(
    OUT / "completion.json",
    {
        "status": "complete",
        "months": len(paths),
        "training_start": str(joined.index[0]),
        "evaluation_start": str(months[0].date()),
        "evaluation_end": str(months[-1].date()),
        "factor_panel_sha256": sha256(factor_path),
        "agent_path_sha256": sha256(agent_path),
        "parameters": result["parameters"],
        "mean_agent_weight_in_input_units": float(weights[:, 1, -1].mean()),
        "mean_factor_unit_gross_exposure": float(np.abs(weights[:, :, :-1]).sum(axis=2).mean()),
        "claim_boundary": result["claim_boundary"],
    },
)
print("JKP_AUGMENTATION_COMPLETE", flush=True)
