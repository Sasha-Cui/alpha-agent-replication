#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Validate saved OOS fills/positions and export independent net return evidence."""

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from validate_native_qlib_accounts_v2 import validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", required=True)
    args = parser.parse_args()
    run = ROOT / "artifacts/fidelity_completion_v2" / args.run_name
    completion = json.loads((run / "completion.json").read_text())
    recipe = json.loads((run / "execution_recipe.json").read_text())
    if completion["status"] != "native_new_period_run_complete_independent_validation_pending":
        raise ValueError("Native execution did not finish")
    for name, key in [
        ("ret.pkl", "returns_sha256"),
        ("qlib_res.csv", "metrics_sha256"),
        ("oos_config.yaml", "config_sha256"),
    ]:
        if sha256(run / name) != completion[key]:
            raise ValueError("Completed native artifact changed")
    report, fills, proof = validate(run, "oos_config.yaml")
    if not recipe["plumbing_search_period_only"]:
        import pandas as pd

        if report.index.min() < pd.Timestamp(recipe["embargo"]["first_evaluation_execution_open"]):
            raise ValueError("Economic account overlaps search-label information")
    audit = json.loads((run / "processed_feature_audit.json").read_text())
    if any(row["infinite_values"] for row in audit):
        raise ValueError("Native processor retained infinite model inputs")
    counts = {row["features"] for row in audit}
    if len(counts) != 1:
        raise ValueError("Train/validation/test feature counts differ")
    proof.update(
        case=completion["case"],
        arm=completion["arm"],
        plumbing_search_period_only=completion["plumbing_search_period_only"],
        processed_features=audit,
        recipe_sha256=sha256(run / "execution_recipe.json"),
        script_sha256=sha256(Path(__file__)),
    )
    out = run / "independent_accounts"
    out.mkdir(exist_ok=True)
    report.to_csv(out / "account.csv", index_label="date")
    fills.to_csv(out / "fills.csv", index=False)
    proof["account_csv_sha256"] = sha256(out / "account.csv")
    atomic_json(out / "validation.json", proof)
    print("INDEPENDENT_NATIVE_OOS_ACCOUNT_PASS", args.run_name, len(report), flush=True)


if __name__ == "__main__":
    main()
