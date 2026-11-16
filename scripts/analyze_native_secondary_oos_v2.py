#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""All fixed task/trial increments; one explicitly reused baseline per case/arm."""

from pathlib import Path
import argparse
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_inference import grouped_t_effect
from alpha_evolve.fidelity_inference_v2 import adjust_grouped_family
from analyze_native_oos_v2 import load_arm, aligned_difference, require_primary_library
from analyze_publication_upgrade import metrics
from native_secondary_evidence_v2 import (
    expected_units,
    require_secondary_library,
    require_parent_subset,
    validate_library,
    require_complete_panel,
    validate_execution_identity,
)

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"
PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["all", "alphaagent", "quantaalpha"], default="all")
    args = parser.parse_args()
    protocol_path = PUBLIC / "native_secondary_analysis_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    if protocol["cases"] != {c: expected_units(c) for c in ("quantaalpha", "alphaagent")}:
        raise ValueError("Planned complete secondary population changed")
    inference = protocol["inference"]
    if any(
        inference[k] != v
        for k, v in {
            "groups": 4,
            "confidence": 0.99,
            "annualization": 252,
            "economic_margin": 0.02,
            "secondary_family_size": 54,
            "family_threshold": 0.01,
        }.items()
    ):
        raise ValueError("Secondary inference specification changed")
    calibration = PUBLIC / "native_grouped_calibration/summary.json"
    check = json.loads(calibration.read_text())
    if check["status"] != "complete" or len(check["results"]) != 8:
        raise ValueError("Calibration incomplete")
    cases = ["alphaagent", "quantaalpha"] if args.case == "all" else [args.case]
    out = PUBLIC / ("native_secondary_oos_" + args.case)
    if (out / "completion.json").exists():
        raise ValueError("Preserve completed secondary analysis")
    performance, comparisons, evidence, daily, summaries = [], [], [], [], []
    for case in cases:
        base_prefix = "alphaagent_pooled20" if case == "alphaagent" else "quantaalpha_bounded"
        parent_path = PRIVATE / (base_prefix + "_fixed_library/library_manifest.json")
        parent, parent_evidence = validate_library(parent_path, ROOT, PRIVATE)
        require_primary_library(case, parent)
        evidence.append({"case": case, "role": "complete_parent_library", **parent_evidence})
        libraries = {}
        for unit in expected_units(case):
            unit_prefix = (
                f"alphaagent_rounds_paper_gpt35_{unit:02d}"
                if case == "alphaagent"
                else f"quantaalpha_bounded_task_{unit:02d}"
            )
            path = PRIVATE / (unit_prefix + "_fixed_library/library_manifest.json")
            library, proof = validate_library(path, ROOT, PRIVATE)
            require_secondary_library(case, library, unit, PRIVATE)
            require_parent_subset(library, parent, sha256(parent_path))
            libraries[unit] = (unit_prefix, sha256(path))
            evidence.append({"case": case, "unit": unit, "role": "secondary_library", **proof})
        require_complete_panel(case, list(libraries))
        for execution in ("native", "opening_information"):
            suffix = "" if execution == "native" else "_open_information"
            for baseline in ("alpha158", "source4"):
                base_name = base_prefix + "_oos_" + baseline + suffix
                base_identity = validate_execution_identity(base_name, execution, PRIVATE)
                base, base_proof = load_arm(base_name, case, baseline, False)
                base_proof.update(base_identity)
                if base_proof["library_manifest_sha256"] != sha256(parent_path):
                    raise ValueError("Reused baseline differs from complete parent")
                base_core = base_proof.pop("core_settings")
                evidence.append(
                    {
                        "case": case,
                        "execution": execution,
                        "role": "common_baseline_reused",
                        "core_settings_sha256": hashlib.sha256(base_core.encode()).hexdigest(),
                        **base_proof,
                    }
                )
                performance.append(
                    {
                        "case": case,
                        "execution": execution,
                        "arm": baseline,
                        "unit": None,
                        "run": base_name,
                        "role": "common_baseline_reused",
                        **metrics(base, frequency=252),
                    }
                )
                daily.append(
                    base.rename("net_return")
                    .reset_index()
                    .assign(case=case, execution=execution, arm=baseline, unit=None, run=base_name)
                )
                for unit, (prefix, digest) in libraries.items():
                    arm = baseline + "_plus_library"
                    run_name = prefix + "_oos_" + arm + suffix
                    identity = validate_execution_identity(run_name, execution, PRIVATE)
                    value, proof = load_arm(run_name, case, arm, False, secondary_unit=unit)
                    proof.update(identity)
                    if proof["library_manifest_sha256"] != digest or proof.pop("core_settings") != base_core:
                        raise ValueError("Secondary arm differs beyond its exact planned feature library")
                    aligned_difference(value, base)
                    evidence.append({"execution": execution, "unit": unit, "reused_baseline": base_name, **proof})
                    performance.append(
                        {
                            "case": case,
                            "execution": execution,
                            "arm": arm,
                            "unit": unit,
                            "run": run_name,
                            "role": "secondary",
                            "reused_baseline": base_name,
                            **metrics(value, frequency=252),
                        }
                    )
                    daily.append(
                        value.rename("net_return")
                        .reset_index()
                        .assign(case=case, execution=execution, arm=arm, unit=unit, run=run_name)
                    )
                    result = grouped_t_effect(
                        value.to_numpy(), base.to_numpy(), frequency=252, groups=4, threshold=0.02, confidence=0.99
                    )
                    result["within_economic_margin_using_pointwise99"] = result.pop("equivalent_within_margin_tost5")
                    result["rules_out_positive_margin_using_pointwise99"] = result.pop(
                        "rules_out_positive_margin_one_sided5"
                    )
                    comparisons.append(
                        {
                            "case": case,
                            "execution": execution,
                            "unit": unit,
                            "baseline": baseline,
                            "run": run_name,
                            "reused_baseline": base_name,
                            "role": "secondary_economic" if execution == "opening_information" else "native_diagnostic",
                            **result,
                        }
                    )
    economic = [r for r in comparisons if r["role"] == "secondary_economic"]
    complete = args.case == "all"
    if len(economic) != (54 if complete else 2 * len(expected_units(args.case))):
        raise ValueError("Incomplete secondary multiplicity family")
    family_inputs, adjusted = adjust_grouped_family(economic, 54, complete)
    for row, family_input, p in zip(economic, family_inputs, adjusted):
        row["p_value_used_in_family"] = family_input
        row["degenerate_comparisons_use_p_one"] = True
        row["secondary_family_adjusted_p"] = float(p)
        row["multiplicity"] = "Holm54" if complete else "Bonferroni54 upper bound; other case incomplete"
        row["positive_secondary_pointwise99_and_family_p_below001"] = bool(
            row["primary_ci_low"] > 0 and p < 0.01 and not row["degenerate_sampling_variation"]
        )
    for case in cases:
        for execution in ("native", "opening_information"):
            for baseline in ("alpha158", "source4"):
                rows = [
                    r
                    for r in comparisons
                    if r["case"] == case and r["execution"] == execution and r["baseline"] == baseline
                ]
                require_complete_panel(case, [r["unit"] for r in rows])
                values = np.asarray([r["full_sample_annualized_effect"] for r in rows])
                summaries.append(
                    {
                        "case": case,
                        "execution": execution,
                        "baseline": baseline,
                        "units": len(rows),
                        "descriptive_effect_quantiles": dict(
                            zip(
                                ["min", "q25", "median", "q75", "max"],
                                np.quantile(values, [0, 0.25, 0.5, 0.75, 1]).tolist(),
                            )
                        ),
                        "positive_full_sample_mean_units": int((values > 0).sum()),
                        "independent_market_histories": 1,
                        "no_selected_winner": True,
                        "not_sampling_inference_across_model_trials": True,
                    }
                )
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in [
        ("performance", performance),
        ("comparisons", comparisons),
        ("execution_evidence", evidence),
        ("descriptive_distribution", summaries),
    ]:
        atomic_json(out / (name + ".json"), rows)
    pd.concat(daily, ignore_index=True).to_csv(out / "daily_net_returns.csv", index=False)
    atomic_json(
        out / "completion.json",
        {
            "status": "complete_secondary_family" if complete else "complete_case_partial_secondary_family",
            "cases": cases,
            "secondary_family_complete": complete,
            "comparisons": len(comparisons),
            "new_model_calls": 0,
            "protocol_sha256": sha256(protocol_path),
            "calibration_sha256": sha256(calibration),
            "inference_amendment_sha256": sha256(PUBLIC / "native_inference_amendment.json"),
            "opening_protocol_sha256": sha256(PUBLIC / "opening_execution_sensitivity_protocol.json"),
            "source_files": {
                str(p.relative_to(ROOT)): sha256(p)
                for p in [
                    Path(__file__),
                    ROOT / "scripts/native_secondary_evidence_v2.py",
                    ROOT / "scripts/fidelity_alpha_terminal_v2.py",
                    ROOT / "scripts/analyze_native_oos_v2.py",
                    ROOT / "src/alpha_evolve/publication_inference.py",
                    ROOT / "src/alpha_evolve/fidelity_inference_v2.py",
                ]
            },
            "conditional_on_fixed_libraries": True,
            "one_shared_market_history_per_case": True,
            "no_primary_result_replacement": True,
            "JKP132_alpha_established": False,
            "full_original_paper_reproduced": False,
            "pristine_confirmatory_claim": False,
            "outputs": {p.name: sha256(p) for p in out.iterdir() if p.is_file()},
        },
    )
    print("SECONDARY_NATIVE_OOS_ANALYSIS", args.case, "complete", flush=True)


if __name__ == "__main__":
    main()
