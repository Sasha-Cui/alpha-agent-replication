#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Add stricter four-contrast project correction without rewriting local studies."""

from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.fidelity_inference_v2 import adjust_grouped_family

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
EXPECTED = {
    "alphaagent_opening_alpha158_increment",
    "quantaalpha_opening_alpha158_increment",
    "efs_gpt41_pooled_minus_matched_grammar_pool",
    "efs_deepseek_v3_pooled_minus_matched_grammar_pool",
}


def adjust_project(rows, require_complete=False):
    cases = [r["project_case"] for r in rows]
    if len(set(cases)) != len(cases) or not set(cases) <= EXPECTED:
        raise ValueError("Duplicate or unplanned project contrast")
    if require_complete and set(cases) != EXPECTED:
        raise ValueError("Project family incomplete")
    inputs, pvalues = adjust_grouped_family(rows, 4, set(cases) == EXPECTED)
    return [
        {
            **row,
            "project_family_status": "complete_four_contrast_v2_family"
            if set(cases) == EXPECTED
            else "partial_four_contrast_v2_family",
            "p_value_used_in_project_family": p,
            "project_adjusted_p": value,
            "correction": "Holm4" if set(cases) == EXPECTED else "Bonferroni4 conservative upper bound",
            "conditional_positive_increment_familywise": bool(
                row["primary_ci_low"] > 0 and value < 0.01 and not row["degenerate_sampling_variation"]
            ),
            "source_interval_scope": "Pointwise99%; no simultaneous2pp-margin declaration",
        }
        for row, p, value in zip(rows, inputs, pvalues)
    ]


def load(folder, filename):
    done_path = folder / "completion.json"
    done = json.loads(done_path.read_text())
    if filename == "primary_comparisons.json":
        expected_status = "both_efs_pooled_cases_complete_project_family_pending"
    elif folder.name == "native_grouped_oos_analysis":
        expected_status = "complete_family"
    elif folder.name in ["native_grouped_oos_alphaagent", "native_grouped_oos_quantaalpha"]:
        expected_status = "partial_case_analysis"
    else:
        raise ValueError("Unplanned local analysis folder")
    if done.get("status") != expected_status:
        raise ValueError("Local economic analysis is not complete in its declared scope")
    if sha256(folder / filename) != done["outputs"][filename]:
        raise ValueError("Completed local comparison changed")
    return json.loads((folder / filename).read_text()), {
        "folder": str(folder.relative_to(ROOT)),
        "completion_sha256": sha256(done_path),
        "comparison_sha256": sha256(folder / filename),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--require-complete", action="store_true")
    args = p.parse_args()
    plan_path = PUBLIC / "efs_final_analysis_protocol.json"
    plan = json.loads(plan_path.read_text())
    if set(plan["inference"]["project_v2_economic_family"]) != EXPECTED:
        raise ValueError("Fixed project family changed")
    rows = []
    evidence = []
    native = PUBLIC / "native_grouped_oos_analysis"
    folders = (
        [native]
        if (native / "completion.json").exists()
        else [PUBLIC / ("native_grouped_oos_" + case) for case in ["alphaagent", "quantaalpha"]]
    )
    for folder in folders:
        if not (folder / "completion.json").exists():
            continue
        source, proof = load(folder, "comparisons.json")
        evidence.append(proof)
        for row in source:
            if row["role"] == "primary_economic":
                if row["execution"] != "opening_information" or row["baseline"] != "alpha158":
                    raise ValueError("Native diagnostic substituted for economic primary")
                rows.append({**row, "project_case": row["case"] + "_opening_alpha158_increment"})
    folder = PUBLIC / "efs_pooled_analysis"
    if (folder / "completion.json").exists():
        source, proof = load(folder, "primary_comparisons.json")
        evidence.append(proof)
        rows.extend({**row, "project_case": row["case"]} for row in source)
    results = adjust_project(rows, args.require_complete)
    identity = hashlib.sha256(
        json.dumps({"evidence": evidence, "protocol": sha256(plan_path)}, sort_keys=True).encode()
    ).hexdigest()
    out = PUBLIC / "project_primary_family" / identity[:16]
    if (out / "completion.json").exists():
        print("PROJECT_FAMILY_SNAPSHOT_ALREADY_PRESENT", out.name)
        return
    out.mkdir(parents=True)
    atomic_json(out / "comparisons.json", results)
    atomic_json(out / "evidence.json", evidence)
    atomic_json(
        out / "completion.json",
        {
            "status": "complete_four_contrast_family"
            if {r["project_case"] for r in results} == EXPECTED
            else "partial_four_contrast_family",
            "expected_cases": sorted(EXPECTED),
            "available_cases": sorted(r["project_case"] for r in results),
            "protocol_sha256": sha256(plan_path),
            "script_sha256": sha256(Path(__file__)),
            "local_study_results_preserved": True,
            "not_pristine_confirmation": True,
            "no_simultaneous_economic_margin_claim": True,
            "new_model_calls": 0,
            "outputs": {p.name: sha256(p) for p in out.iterdir() if p.is_file()},
        },
    )
    atomic_json(
        PUBLIC / "project_primary_family/latest.json",
        {"snapshot": str(out.relative_to(ROOT)), "completion_sha256": sha256(out / "completion.json")},
    )
    print("PROJECT_PRIMARY_FAMILY", len(results), "of4", flush=True)


if __name__ == "__main__":
    main()
