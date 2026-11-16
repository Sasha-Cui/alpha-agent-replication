#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source bootstrap
"""Frozen paired economic analysis after native execution and accounting gates."""

from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_inference import paired_effect, holm_adjust
from analyze_publication_upgrade import metrics

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"
PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
ARMS = ["source4", "source4_plus_library", "alpha158", "alpha158_plus_library"]


def core_settings(config):
    """Everything economic except the explicitly varied feature loader."""
    core = copy.deepcopy(config)
    handler = core["task"]["dataset"]["kwargs"]["handler"]["kwargs"]
    loader = handler["data_loader"]
    if loader["class"] == "NestedDataLoader":
        children = loader["kwargs"]["dataloader_l"]
        if len(children) != 2 or children[1]["class"] != "qlib.data.dataset.loader.StaticDataLoader":
            raise ValueError("Unexpected extra feature-loader semantics")
        loader = children[0]
    if loader["class"] != "qlib.contrib.data.loader.QlibDataLoader":
        raise ValueError("Unexpected source market-data loader")
    loader = copy.deepcopy(loader)
    loader["kwargs"]["config"]["feature"] = "DECLARED_FEATURE_INTERVENTION"
    handler["data_loader"] = loader
    # The source YAML aliases the same object here; normalize it explicitly so
    # differently serialized aliases cannot hide divergent task settings.
    if "data_handler_config" in core:
        core["data_handler_config"] = copy.deepcopy(handler)
    return json.dumps(core, sort_keys=True, default=str)


def require_primary_library(case, library):
    expected = (
        {f"alphaagent_rounds_paper_gpt35_{i:02d}" for i in range(1, 21)}
        if case == "alphaagent"
        else {"quantaalpha_bounded"}
    )
    if set(library["source_manifests"]) != expected:
        raise ValueError("Primary source trial set incomplete or substituted: " + case)
    if library.get("experiment_index_filter") is not None:
        raise ValueError("An individual-task library is not the complete primary library")
    required_programs = set()
    for name, digest in library["source_manifests"].items():
        path = PRIVATE / name / "used_factor_manifest.json"
        if sha256(path) != digest:
            raise ValueError("Primary source-used manifest changed")
        manifest = json.loads(path.read_text())
        allowed = {row["index"] for row in manifest["experiments"] if row.get("within_first_five_rounds", True)}
        required_programs.update(
            row["sha256"]
            for row in manifest["programs"]
            if any(use["experiment_index"] in allowed for use in row["uses"])
        )
    if {row["code_sha256"] for row in library["programs"]} != required_programs:
        raise ValueError("Primary library drops or substitutes source-used programs")
    if case == "alphaagent":
        for name in expected:
            from alpha_constructor_abort_v3 import validate_five as validate_alpha_five_attempts
            validate_alpha_five_attempts(PRIVATE / name)


def load_arm(run_name, case, arm, plumbing, *, secondary_unit=None):
    # YAML is supplied by the central Python3.12 analysis runtime. Pure
    # financial/configuration guards remain usable in the Python3.9 test env.
    import yaml

    run = PRIVATE / run_name
    completion = json.loads((run / "completion.json").read_text())
    recipe = json.loads((run / "execution_recipe.json").read_text())
    proof_path = run / "independent_accounts/validation.json"
    proof = json.loads(proof_path.read_text())
    if completion["case"] != case or completion["arm"] != arm:
        raise ValueError("Unexpected arm/case identity")
    if completion["status"] != "native_new_period_run_complete_independent_validation_pending":
        raise ValueError("Native arm is incomplete")
    if proof["status"] != "pass" or proof["recipe_sha256"] != sha256(run / "execution_recipe.json"):
        raise ValueError("Independent accounting gate failed or changed")
    if any(obj["plumbing_search_period_only"] != plumbing for obj in [completion, recipe, proof]):
        raise ValueError("Search-period and later-period evidence cannot be mixed")
    for filename, key in [
        ("ret.pkl", "returns_sha256"),
        ("qlib_res.csv", "metrics_sha256"),
        ("oos_config.yaml", "config_sha256"),
    ]:
        if sha256(run / filename) != completion[key]:
            raise ValueError("Native completed artifact changed")
    account_path = run / "independent_accounts/account.csv"
    if sha256(account_path) != proof["account_csv_sha256"]:
        raise ValueError("Validated account export changed")
    frame = pd.read_csv(account_path, index_col="date", parse_dates=True)
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Invalid account calendar")
    net = frame["return"] - frame["cost"]
    if not np.isfinite(net).all() or (net <= -1).any():
        raise ValueError("Invalid independently accounted net return")
    libraries = [
        path
        for path in PRIVATE.glob("*_fixed_library/library_manifest.json")
        if sha256(path) == recipe["library_manifest_sha256"]
    ]
    if not libraries:
        raise ValueError("Hash-pinned source library unavailable")
    library = json.loads(libraries[0].read_text())
    if not plumbing:
        if secondary_unit is None:
            require_primary_library(case, library)
        else:
            from native_secondary_evidence_v2 import require_secondary_library

            require_secondary_library(case, library, secondary_unit, PRIVATE)
        if frame.index.min() < pd.Timestamp(recipe["embargo"]["first_evaluation_execution_open"]):
            raise ValueError("Economic path overlaps source-label information")
    expected_features = (158 if arm.startswith("alpha158") else 4) + (
        library["distinct_expressions"] if arm.endswith("_plus_library") else 0
    )
    if any(row["features"] != expected_features or row["infinite_values"] for row in proof["processed_features"]):
        raise ValueError("Native processed feature count/finiteness differs from frozen intervention")
    config = yaml.safe_load((run / "oos_config.yaml").read_text())
    return net, {
        "run": run_name,
        "case": case,
        "arm": arm,
        "completion_sha256": sha256(run / "completion.json"),
        "account_validation_sha256": sha256(proof_path),
        "account_sha256": sha256(account_path),
        "recipe_sha256": sha256(run / "execution_recipe.json"),
        "library_manifest_sha256": recipe["library_manifest_sha256"],
        "core_settings": core_settings(config),
        "features": expected_features,
    }


def aligned_difference(left, right):
    if not left.index.equals(right.index):
        raise ValueError("Paired economic calendars differ; do not silently intersect")
    return left - right


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alphaagent-prefix", default="alphaagent_pooled20_oos")
    parser.add_argument("--quantaalpha-prefix", default="quantaalpha_bounded_oos")
    parser.add_argument("--plumbing-search-period", action="store_true")
    args = parser.parse_args()
    if not args.plumbing_search_period and (PUBLIC / "native_inference_amendment.json").exists():
        raise ValueError("Original bootstrap is now diagnostic; use the calibrated grouped-analysis followthrough")
    protocol_path = PUBLIC / "native_new_period_analysis_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    inference = protocol["inference"]
    if (
        inference["frequency"] != 252
        or inference["mean_block_sessions"] != 20
        or inference["hac_lags"] != 5
        or inference["replicates"] != 4999
        or inference["seed"] != 20260917
    ):
        raise ValueError("Frozen analysis parameters changed")
    out = PUBLIC / ("native_oos_pipeline_check" if args.plumbing_search_period else "native_oos_analysis")
    if (out / "completion.json").exists():
        raise ValueError("Preserve completed analysis")
    performance, evidence, comparisons, sensitivity, returns = [], [], [], [], []
    for case, prefix in [("alphaagent", args.alphaagent_prefix), ("quantaalpha", args.quantaalpha_prefix)]:
        paths = {}
        case_evidence = []
        for arm in ARMS:
            values, proof = load_arm(prefix + "_" + arm, case, arm, args.plumbing_search_period)
            paths[arm] = values
            case_evidence.append(proof)
            performance.append({"case": case, "arm": arm, **metrics(values, frequency=252)})
            returns.append(values.rename("net_return").reset_index().assign(case=case, arm=arm))
        if len({row["core_settings"] for row in case_evidence}) != 1:
            raise ValueError("Paired arms differ beyond the declared feature intervention")
        if len({row["library_manifest_sha256"] for row in case_evidence}) != 1:
            raise ValueError("Paired arms use different frozen source libraries")
        evidence.extend(case_evidence)
        for baseline, role in [("alpha158", "primary"), ("source4", "secondary")]:
            left, right = paths[baseline + "_plus_library"], paths[baseline]
            aligned_difference(left, right)
            result = paired_effect(
                left.to_numpy(),
                right.to_numpy(),
                frequency=252,
                mean_block=20,
                replicates=4999,
                seed=20260917,
                threshold=0.02,
                hac_lags=5,
            )
            comparisons.append(
                {"case": case, "contrast": baseline + "_plus_library minus " + baseline, "role": role, **result}
            )
            for block in [5, 60]:
                check = paired_effect(
                    left.to_numpy(),
                    right.to_numpy(),
                    frequency=252,
                    mean_block=block,
                    replicates=4999,
                    seed=20260917,
                    threshold=0.02,
                    hac_lags=5,
                )
                sensitivity.append({"case": case, "baseline": baseline, **check})
    primary = [row for row in comparisons if row["role"] == "primary"]
    adjusted = holm_adjust([row["bootstrap_p_two_sided"] for row in primary])
    for row, value in zip(primary, adjusted):
        row["holm_p_two_sided_two_primary_contrasts"] = float(value)
        row["positive_effect_and_holm_p_below_005"] = bool(
            row["annualized_arithmetic_effect"] > 0 and value < 0.05 and not row["degenerate_sampling_variation"]
        )
    out.mkdir(parents=True, exist_ok=True)
    for row in evidence:
        row["core_settings_sha256"] = hashlib.sha256(row.pop("core_settings").encode()).hexdigest()
    for name, content in [
        ("performance", performance),
        ("comparisons", comparisons),
        ("block_sensitivity", sensitivity),
        ("execution_evidence", evidence),
    ]:
        atomic_json(out / (name + ".json"), content)
    pd.concat(returns, ignore_index=True).to_csv(out / "daily_net_returns.csv", index=False)
    atomic_json(
        out / "completion.json",
        {
            "status": "search_period_pipeline_check_complete"
            if args.plumbing_search_period
            else "conditional_native_new_period_analysis_complete",
            "plumbing_search_period_only": args.plumbing_search_period,
            "protocol_sha256": sha256(protocol_path),
            "script_sha256": sha256(Path(__file__)),
            "primary_comparisons": len(primary),
            "new_model_calls": 0,
            "conditional_on_frozen_libraries": True,
            "independent_market_histories_per_case": 1,
            "JKP132_alpha_established_by_this_analysis": False,
            "pristine_confirmatory_claim": False,
            "full_original_paper_reproduced": False,
            "outputs": {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()},
        },
    )
    print("NATIVE_PAIRED_ANALYSIS_COMPLETE", out.name, flush=True)


if __name__ == "__main__":
    main()
