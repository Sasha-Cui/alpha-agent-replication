#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Calibrated grouped economic comparisons; native and opening-only rules retained."""

from pathlib import Path
import argparse
import json
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_inference import grouped_t_effect
from alpha_evolve.fidelity_inference_v2 import adjust_grouped_family
from analyze_native_oos_v2 import load_arm, aligned_difference, ARMS
from analyze_publication_upgrade import metrics

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", choices=["all", "alphaagent", "quantaalpha"], default="all")
    args = p.parse_args()
    calibration = PUBLIC / "native_grouped_calibration/summary.json"
    c = json.loads(calibration.read_text())
    if c["status"] != "complete" or len(c["results"]) != 8:
        raise ValueError("Grouped calibration incomplete")
    amendment = PUBLIC / "native_inference_amendment.json"
    if not amendment.exists():
        raise ValueError("Missing explicit inference amendment")
    cases = ["alphaagent", "quantaalpha"] if args.case == "all" else [args.case]
    out = PUBLIC / ("native_grouped_oos_analysis" if args.case == "all" else "native_grouped_oos_" + args.case)
    if (out / "completion.json").exists():
        raise ValueError("Preserve completed analysis")
    performance = []
    comparisons = []
    evidence = []
    paths = []
    for case in cases:
        prefix = "alphaagent_pooled20_oos" if case == "alphaagent" else "quantaalpha_bounded_oos"
        for execution in ["native", "opening_information"]:
            suffix = "" if execution == "native" else "_open_information"
            values = {}
            proofs = []
            for arm in ARMS:
                value, proof = load_arm(prefix + "_" + arm + suffix, case, arm, False)
                values[arm] = value
                proofs.append(proof)
                performance.append({"case": case, "arm": arm, "execution": execution, **metrics(value, frequency=252)})
                paths.append(value.rename("net_return").reset_index().assign(case=case, arm=arm, execution=execution))
            if (
                len({r["core_settings"] for r in proofs}) != 1
                or len({r["library_manifest_sha256"] for r in proofs}) != 1
            ):
                raise ValueError("Paired arms differ beyond the prespecified feature intervention")
            for proof in proofs:
                proof.pop("core_settings")
                evidence.append({**proof, "execution": execution})
            for base in ["alpha158", "source4"]:
                left, right = values[base + "_plus_library"], values[base]
                aligned_difference(left, right)
                result = grouped_t_effect(
                    left.to_numpy(), right.to_numpy(), frequency=252, groups=4, threshold=0.02, confidence=0.99
                )
                # Avoid the inherited function's historical TOST5 label for the
                # deliberately more conservative primary99 interval.
                result["within_economic_margin_using_primary99"] = result.pop("equivalent_within_margin_tost5")
                result["rules_out_positive_margin_using_primary99"] = result.pop("rules_out_positive_margin_one_sided5")
                role = "primary_economic" if execution == "opening_information" and base == "alpha158" else "diagnostic"
                comparisons.append({"case": case, "execution": execution, "baseline": base, "role": role, **result})
    primary = [r for r in comparisons if r["role"] == "primary_economic"]
    complete = len(primary) == 2
    family_inputs, adjusted = adjust_grouped_family(primary, 2, complete)
    for row, family_input, pvalue in zip(primary, family_inputs, adjusted):
        row["p_value_used_in_family"] = family_input
        row["degenerate_comparisons_use_p_one"] = True
        row["family_adjusted_p"] = float(pvalue)
        row["multiplicity_method"] = (
            "Holm over both prespecified primary economic contrasts"
            if complete
            else "Conservative Bonferroni upper bound for the two-contrast family; other case incomplete"
        )
        row["positive_primary99_interval_and_adjusted_p_below001"] = (
            row["primary_ci_low"] > 0 and pvalue < 0.01 and not row["degenerate_sampling_variation"]
        )
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in [("performance", performance), ("comparisons", comparisons), ("execution_evidence", evidence)]:
        atomic_json(out / (name + ".json"), rows)
    pd.concat(paths, ignore_index=True).to_csv(out / "daily_net_returns.csv", index=False)
    atomic_json(
        out / "completion.json",
        {
            "status": "complete_family" if complete else "partial_case_analysis",
            "cases": cases,
            "primary_family_complete": complete,
            "calibration_sha256": sha256(calibration),
            "inference_amendment_sha256": sha256(amendment),
            "opening_rule_protocol_sha256": sha256(PUBLIC / "opening_execution_sensitivity_protocol.json"),
            "script_sha256": sha256(Path(__file__)),
            "family_adjustment_source_sha256": sha256(ROOT / "src/alpha_evolve/fidelity_inference_v2.py"),
            "validation_source_files": {
                str(p.relative_to(ROOT)): sha256(p) for p in [
                    ROOT / "scripts/analyze_native_oos_v2.py",
                    ROOT / "scripts/fidelity_alpha_terminal_v2.py",
                ]
            },
            "new_model_calls": 0,
            "full_original_paper_reproduced": False,
            "JKP132_alpha_established": False,
            "pristine_confirmatory_claim": False,
            "inference": "Four contiguous block means,99percent pointwise intervals,1percent family significance. Block independence/approximate normality are assumptions; calibration is not a universal coverage guarantee.",
            "return_metric_convention": "cagr fields are252-session annualized geometric returns, not calendar-time CAGR; primary intervals cover annualized arithmetic mean differences, not CAGR differences.",
            "outputs": {f.name: sha256(f) for f in out.iterdir() if f.is_file()},
        },
    )
    print(
        "GROUPED_NATIVE_OOS_ANALYSIS", args.case, "complete_family" if complete else "partial_case_analysis", flush=True
    )


if __name__ == "__main__":
    main()
