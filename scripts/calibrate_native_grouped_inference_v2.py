#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Outcome-free calibration of the predeclared conservative grouped alternative."""

from pathlib import Path
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_inference import grouped_t_effect
from calibrate_native_oos_inference_v2 import innovations
from calibrate_publication_inference import wilson


def main():
    out = ROOT / "paper_runs/fidelity_completion_v2/native_grouped_calibration"
    protocol = json.loads((out / "protocol.json").read_text())
    if (out / "summary.json").exists():
        raise ValueError("Preserve completed calibration")
    results = []
    for cell in protocol["cells"]:
        counts = {
            "covers_primary99": 0,
            "reject_zero_p001": 0,
            "reject_zero_p0005": 0,
            "equivalence_at_positive_margin_boundary": 0,
        }
        for replication in range(protocol["replications"]):
            rng = np.random.default_rng(protocol["seed"] + cell["index"] * 100000 + replication)
            values = innovations(rng, cell["observations"], cell["dgp"], protocol["daily_sd"])
            result = grouped_t_effect(values, frequency=252, groups=4, threshold=0.02, confidence=0.99)
            counts["covers_primary99"] += result["primary_ci_low"] <= 0 <= result["primary_ci_high"]
            counts["reject_zero_p001"] += result["group_t_p_two_sided"] < 0.01
            counts["reject_zero_p0005"] += result["group_t_p_two_sided"] < 0.005
            counts["equivalence_at_positive_margin_boundary"] += (
                result["primary_ci_low"] + 0.02 > -0.02 and result["primary_ci_high"] + 0.02 < 0.02
            )
        row = {**cell, "replications": protocol["replications"]}
        for name, count in counts.items():
            lo, hi = wilson(count, protocol["replications"])
            row[name] = {"rate": count / protocol["replications"], "mc_ci95": [lo, hi]}
        results.append(row)
        atomic_json(out / "partial.json", results)
        print("GROUPED_CALIBRATION_CELL", cell["index"], row["covers_primary99"]["rate"], flush=True)
    atomic_json(
        out / "summary.json",
        {
            "status": "complete",
            "results": results,
            "protocol_sha256": sha256(out / "protocol.json"),
            "script_sha256": sha256(Path(__file__)),
            "inference_code_sha256": sha256(ROOT / "src/alpha_evolve/publication_inference.py"),
            "scope": "Synthetic calibration only. Approximate independence/normality of block means remains an assumption; empirical coverage in these DGPs is not a universal guarantee.",
        },
    )


if __name__ == "__main__":
    main()
