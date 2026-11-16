#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Known-span and extra-signal DGPs; all settings fixed before calibration outcomes."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import argparse
import json
import numpy as np
import pandas as pd
from scipy.stats import norm
from alpha_evolve.publication_inference import refitted_alpha_bootstrap, ols_alpha, chronological_projection
from alpha_evolve.openrouter_budget import atomic_json, sha256

OUT = ROOT / "paper_runs/publication_upgrade_v1/inference_calibration"


def wilson(success, n):
    z = norm.ppf(0.975)
    phat = success / n
    den = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / den
    radius = z * np.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / den
    return float(center - radius), float(center + radius)


def ar(rng, n, k, rho, scale):
    z = rng.normal(0, scale * np.sqrt(1 - rho * rho), (n + 200, k))
    x = np.zeros_like(z)
    for i in range(1, len(z)):
        x[i] = rho * x[i - 1] + z[i]
    return x[200:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--replications", type=int, default=600)
    p.add_argument("--bootstraps", type=int, default=499)
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = {
        "mc_replications": args.replications,
        "bootstrap_replicates_per_mc": args.bootstraps,
        "months": 72,
        "factor_count": 6,
        "factor_ar": 0.15,
        "noise_ar": 0.3,
        "noise_monthly_sd": 0.02,
        "annual_alpha_cases": [0, 0.02, 0.08],
        "mean_blocks": [3, 6, 12],
        "seed": 68001,
        "method": "stationary bootstrap-t with refitted HAC scale",
        "purpose": "Calibration after basic bootstrap failed; all block lengths retained, no strategy returns used for estimator repair",
    }
    atomic_json(OUT / "recipe.json", protocol)
    rng = np.random.default_rng(protocol["seed"])
    rows = []
    for replication in range(args.replications):
        factors = ar(rng, 72, 6, 0.15, 0.035)
        noise = ar(rng, 72, 1, 0.3, 0.02)[:, 0]
        base = factors @ np.array([0.65, -0.1, 0.15, 0.1, 0.2, 0.1]) + noise
        for block in protocol["mean_blocks"]:
            # Additive mean shifts leave bootstrap errors invariant; estimate the
            # base distribution once and translate every prespecified alternative.
            result = refitted_alpha_bootstrap(
                base, factors, mean_block=block, replicates=args.bootstraps, seed=900000 + replication * 17 + block
            )
            for alpha in protocol["annual_alpha_cases"]:
                low = result["ci95_low"] + alpha
                high = result["ci95_high"] + alpha
                rows.append(
                    {
                        "replication": replication,
                        "mean_block": block,
                        "true_annual_alpha": alpha,
                        "estimate": result["annualized_arithmetic_effect"] + alpha,
                        "ci95_low": low,
                        "ci95_high": high,
                        "covers_true_alpha": low <= alpha <= high,
                        "rejects_zero_two_sided": low > 0 or high < 0,
                        "rules_out_positive_2pp": result["one_sided95_upper"] + alpha < 0.02,
                        "equivalent_within_2pp": result["ci90_low"] + alpha > -0.02
                        and result["ci90_high"] + alpha < 0.02,
                    }
                )
        if replication % 50 == 0:
            print("MC", replication, flush=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "monte_carlo_draws.csv", index=False)
    summaries = []
    for (block, alpha), group in frame.groupby(["mean_block", "true_annual_alpha"]):
        row = {
            "mean_block": int(block),
            "true_annual_alpha": alpha,
            "replications": len(group),
            "bias": float((group.estimate - alpha).mean()),
        }
        for metric in [
            "covers_true_alpha",
            "rejects_zero_two_sided",
            "rules_out_positive_2pp",
            "equivalent_within_2pp",
        ]:
            successes = int(group[metric].sum())
            lo, hi = wilson(successes, len(group))
            row[metric] = successes / len(group)
            row[metric + "_mc_ci95_low"] = lo
            row[metric + "_mc_ci95_high"] = hi
        summaries.append(row)
    pd.DataFrame(summaries).to_csv(OUT / "calibration_summary.csv", index=False)
    # Verify full-dimensional exact spans when identified, and refusal when short.
    rng = np.random.default_rng(1234)
    factors = ar(rng, 420, 132, 0.15, 0.02)
    betas = rng.normal(0, 0.1, 132)
    y = factors @ betas
    recovered = ols_alpha(y, factors)
    try:
        ols_alpha(y[:72], factors[:72])
        raise AssertionError("Short JKP132 regression was accepted")
    except ValueError as exc:
        short_gate = str(exc)
    # Real reconstructed JKP panel: deliberately spanned synthetic candidates.
    path = ROOT / "paper_runs/prompt_replay/guruagents/performance/factor_panel_extended_realization.csv"
    panel = pd.read_csv(path)
    columns = [c for c in panel if c.startswith("char__")]
    complete = panel[columns].dropna()
    f = complete.to_numpy()
    if len(columns) != 132:
        raise ValueError("Expected exactly 132 characteristic factors")
    b = np.zeros(132)
    b[[0, 20, 50, 90]] = [0.4, -0.2, 0.5, 0.3]
    span = f @ b
    fit = ols_alpha(span, f)
    diagnostics = {}
    for label, c in [("ridge132", None), ("pca5_ridge", 5)]:
        result = chronological_projection(span[-72:], f[-72:], min_train=36, penalty=10, components=c)
        diagnostics[label] = {k: v for k, v in result.items() if k not in ["predictions", "residual"]}
    identity = {
        "simulated_full_span_alpha_annualized": recovered["annualized_alpha"],
        "simulated_full_span_max_residual": float(np.max(np.abs(recovered["residual"]))),
        "short_jkp132_refusal": short_gate,
        "empirical_factor_panel_sha256": sha256(path),
        "empirical_jkp_factor_count": 132,
        "empirical_factor_observations": len(f),
        "empirical_known_span_alpha_annualized": fit["annualized_alpha"],
        "empirical_known_span_max_residual": float(np.max(np.abs(fit["residual"]))),
        "spanned_candidate_regularization_diagnostics": diagnostics,
        "warning": "Regularized/PCA reconstruction errors can remain nonzero for a candidate known to be entirely factor-spanned; they are not evidence of an independent alpha source.",
    }
    atomic_json(OUT / "span_identity_checks.json", identity)
    atomic_json(
        OUT / "completion.json",
        {
            "status": "complete",
            "script_sha256": sha256(Path(__file__)),
            "inference_code_sha256": sha256(ROOT / "src/alpha_evolve/publication_inference.py"),
            "outputs": {p.name: sha256(p) for p in OUT.iterdir() if p.is_file() and p.name != "completion.json"},
        },
    )
    print("COMPLETE", json.dumps(identity), flush=True)


if __name__ == "__main__":
    main()
