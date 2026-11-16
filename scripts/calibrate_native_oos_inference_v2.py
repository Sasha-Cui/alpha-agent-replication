#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Outcome-free finite-sample diagnostics for the frozen paired daily inference."""

from pathlib import Path
import argparse
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_inference import paired_effect
from calibrate_publication_inference import wilson

OUT = ROOT / "paper_runs/fidelity_completion_v2/native_inference_calibration"


def innovations(rng, n, kind, scale):
    burn = 1000
    z = (
        rng.normal(size=n + burn)
        if kind in ["iid_normal", "ar03_normal"]
        else rng.standard_t(5, size=n + burn) * np.sqrt(3 / 5)
    )
    values = np.zeros(n + burn)
    if kind == "garch_t5":
        variance = scale**2
        for t in range(1, len(values)):
            variance = 0.05 * scale**2 + 0.05 * values[t - 1] ** 2 + 0.9 * variance
            values[t] = np.sqrt(variance) * z[t]
    else:
        rho = {"iid_normal": 0, "ar03_normal": 0.3, "ar06_t5": 0.6}[kind]
        for t in range(1, len(values)):
            values[t] = rho * values[t - 1] + scale * np.sqrt(1 - rho**2) * z[t]
    return values[burn:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cell", type=int)
    p.add_argument("--collect-only", action="store_true")
    args = p.parse_args()
    protocol = json.loads((OUT / "protocol.json").read_text())
    if args.collect_only:
        results = []
        for cell in protocol["cells"]:
            path = OUT / f"cell_{cell['index']:02d}.json"
            value = json.loads(path.read_text())
            if value["status"] != "complete" or value["protocol_sha256"] != sha256(OUT / "protocol.json"):
                raise ValueError("Incomplete or changed calibration cell")
            results.extend(value["summary"])
        atomic_json(
            OUT / "summary.json",
            {
                "status": "complete",
                "scope": "Synthetic known-zero paired differences only; no research strategy returns used. Rates have Monte Carlo uncertainty and do not prove universal coverage. Retain every DGP/block result; never choose a model or block based on real returns.",
                "results": results,
                "protocol_sha256": sha256(OUT / "protocol.json"),
            },
        )
        print("NATIVE_INFERENCE_CALIBRATION_COLLECTED", len(results))
        return
    if args.cell is None or not 0 <= args.cell < len(protocol["cells"]):
        raise ValueError("Specify one fixed calibration cell")
    cell = protocol["cells"][args.cell]
    target = OUT / f"cell_{args.cell:02d}.json"
    if target.exists():
        raise ValueError("Preserve completed calibration")
    n = cell["observations"]
    rows = []
    for trial in range(protocol["monte_carlo_replications"]):
        rng = np.random.default_rng(protocol["seed"] + args.cell * 10000 + trial)
        difference = innovations(rng, n, cell["dgp"], protocol["difference_daily_sd"])
        for block in protocol["mean_blocks"]:
            result = paired_effect(
                difference,
                np.zeros(n),
                frequency=252,
                mean_block=block,
                hac_lags=5,
                replicates=protocol["bootstrap_replicates"],
                seed=8000000 + args.cell * 100000 + trial * 100 + block,
                threshold=0.02,
            )
            rows.append(
                {
                    "replication": trial,
                    "mean_block": block,
                    "covers_zero95": result["ci95_low"] <= 0 <= result["ci95_high"],
                    "reject_zero_p005": result["bootstrap_p_two_sided"] < 0.05,
                    "reject_zero_p0025": result["bootstrap_p_two_sided"] < 0.025,
                    "false_equivalence_at_positive_2pp_boundary": result["ci90_low"] + 0.02 > -0.02
                    and result["ci90_high"] + 0.02 < 0.02,
                    "detect_2pp_with_pointwise95_interval": result["ci95_low"] + 0.02 > 0
                    or result["ci95_high"] + 0.02 < 0,
                    "ci95_width": result["ci95_high"] - result["ci95_low"],
                }
            )
        if trial % 32 == 0:
            print("CALIBRATION", args.cell, trial, flush=True)
    summary = []
    rates = [
        "covers_zero95",
        "reject_zero_p005",
        "reject_zero_p0025",
        "false_equivalence_at_positive_2pp_boundary",
        "detect_2pp_with_pointwise95_interval",
    ]
    for block in protocol["mean_blocks"]:
        group = [r for r in rows if r["mean_block"] == block]
        row = {
            **cell,
            "mean_block": block,
            "replications": len(group),
            "mean_ci95_width": float(np.mean([r["ci95_width"] for r in group])),
        }
        for metric in rates:
            count = sum(r[metric] for r in group)
            lo, hi = wilson(count, len(group))
            row[metric] = {"rate": count / len(group), "monte_carlo_ci95": [lo, hi]}
        summary.append(row)
    atomic_json(
        target,
        {
            "status": "complete",
            "cell": cell,
            "summary": summary,
            "synthetic_draw_results": rows,
            "protocol_sha256": sha256(OUT / "protocol.json"),
            "script_sha256": sha256(Path(__file__)),
            "inference_code_sha256": sha256(ROOT / "src/alpha_evolve/publication_inference.py"),
        },
    )


if __name__ == "__main__":
    main()
