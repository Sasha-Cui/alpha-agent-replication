#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Independent Monte Carlo validation for the conservative grouped-t alternative."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import numpy as np
import pandas as pd
from alpha_evolve.publication_inference import grouped_t_effect
from alpha_evolve.openrouter_budget import atomic_json, sha256
from calibrate_publication_inference import ar, wilson

OUT = ROOT / "paper_runs/publication_upgrade_v1/grouped_inference_calibration"
OUT.mkdir(parents=True, exist_ok=True)
recipe = {
    "seed": 876201,
    "replications_per_cell": 2000,
    "months": [36, 72, 144],
    "noise_ar": [0, 0.3, 0.6],
    "noise": ["normal", "student_t5", "deterministic_heteroskedastic"],
    "factor_counts": [0, 6],
    "annual_alphas": [0, 0.02, 0.08],
    "groups": "4 for paired means; for factor intercepts 4 when block residual degrees permit, otherwise 3",
    "role": "Independent new random seed; no strategy outcomes used for choosing the inferential method",
}
atomic_json(OUT / "recipe.json", recipe)
rng = np.random.default_rng(recipe["seed"])
rows = []
for n in recipe["months"]:
    for rho in recipe["noise_ar"]:
        for noise_type in recipe["noise"]:
            counts = {
                k: {a: {"cover": 0, "reject": 0, "exclude_margin": 0, "equivalent": 0} for a in recipe["annual_alphas"]}
                for k in recipe["factor_counts"]
            }
            for rep in range(recipe["replications_per_cell"]):
                factors = ar(rng, n, 6, 0.15, 0.035)
                if noise_type == "student_t5":
                    innovations = rng.standard_t(5, n + 200) * 0.02 / np.sqrt(5 / 3) * np.sqrt(1 - rho * rho)
                    noise = np.zeros(n + 200)
                    for i in range(1, len(noise)):
                        noise[i] = rho * noise[i - 1] + innovations[i]
                    noise = noise[200:]
                else:
                    noise = ar(rng, n, 1, rho, 0.02)[:, 0]
                    if noise_type == "deterministic_heteroskedastic":
                        noise *= np.linspace(0.5, 1.5, n)
                for k in recipe["factor_counts"]:
                    y = noise if k == 0 else factors @ np.array([0.65, -0.1, 0.15, 0.1, 0.2, 0.1]) + noise
                    groups = 3 if k and n == 36 else 4
                    result = grouped_t_effect(y, factors=factors if k else None, groups=groups)
                    for alpha in recipe["annual_alphas"]:
                        value = counts[k][alpha]
                        lo = result["ci95_low"] + alpha
                        hi = result["ci95_high"] + alpha
                        value["cover"] += int(lo <= alpha <= hi)
                        value["reject"] += int(lo > 0 or hi < 0)
                        value["exclude_margin"] += int(result["one_sided95_upper"] + alpha < 0.02)
                        value["equivalent"] += int(
                            result["ci90_low"] + alpha > -0.02 and result["ci90_high"] + alpha < 0.02
                        )
            for k in recipe["factor_counts"]:
                for alpha, value in counts[k].items():
                    row = {
                        "observations": n,
                        "rho": rho,
                        "noise_type": noise_type,
                        "factor_count": k,
                        "true_annual_alpha": alpha,
                        "replications": recipe["replications_per_cell"],
                    }
                    for name, success in value.items():
                        lo, hi = wilson(success, recipe["replications_per_cell"])
                        row[name] = success / recipe["replications_per_cell"]
                        row[name + "_mc_ci95_low"] = lo
                        row[name + "_mc_ci95_high"] = hi
                    rows.append(row)
            print("DONE", n, rho, noise_type, flush=True)
pd.DataFrame(rows).to_csv(OUT / "calibration_summary.csv", index=False)
atomic_json(
    OUT / "completion.json",
    {
        "status": "complete",
        "cells": len(rows),
        "simulated_samples": len(recipe["months"])
        * len(recipe["noise_ar"])
        * len(recipe["noise"])
        * recipe["replications_per_cell"],
        "script_sha256": sha256(Path(__file__)),
        "inference_code_sha256": sha256(ROOT / "src/alpha_evolve/publication_inference.py"),
    },
)
