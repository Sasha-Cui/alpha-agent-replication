#!/usr/bin/env python3
# ruff: noqa: E402 - pinned source bootstrap
"""Export every factor actually consumed by native backtests, without return selection."""

from pathlib import Path
import sys
import json
import pickle
import ast
import socket
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/fidelity_completion_v2/dependencies/alphaagent_95e478"
sys.path[:0] = [str(ROOT / "src"), str(SOURCE)]
from alpha_evolve.openrouter_budget import atomic_json, sha256


def literals(code):
    result = {}
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ["name", "expr"]:
                    try:
                        value = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(value, str):
                        result[target.id] = value
    return result


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--allow-documented-early-abort", action="store_true")
    args = parser.parse_args()
    run = ROOT / "artifacts/fidelity_completion_v2" / args.run_name
    exit_record = json.loads((run / "execution_exit.json").read_text())
    if args.allow_documented_early_abort:
        from alpha_constructor_abort_v3 import validate_early as validate_early_abort
        validate_early_abort(run)
    elif exit_record['status'] == 'native_final_attempt_failed':
        from alpha_constructor_abort_v3 import validate_five as validate_alpha_five_attempts
        validate_alpha_five_attempts(run)
    elif exit_record["status"] not in ["native_loop_returned", "native_round_budget_exhausted"]:
        raise ValueError("Native attempt has not returned")

    def offline(*a, **kw):
        raise RuntimeError("Snapshot extraction cannot access network")

    socket.create_connection = offline
    socket.socket.connect = offline
    snapshots = [
        p
        for p in (run / "log/__session__").glob("*/*")
        if p.is_file() and p.parent.name.isdigit() and p.name.split("_", 1)[0].isdigit()
    ]
    snapshot = max(snapshots, key=lambda p: (int(p.parent.name), int(p.name.split("_", 1)[0])))
    stage_events = json.loads((run / "stages.json").read_text())
    successful_rounds = [
        row["loop_index"] for row in stage_events if row["stage"] == "feedback" and row.get("completed")
    ]

    # This is our own just-produced native snapshot, never a third-party pickle.
    with snapshot.open("rb") as stream:
        loop = pickle.load(stream)
    out = run / "used_programs"
    out.mkdir(exist_ok=True)
    if len(successful_rounds) != len(loop.trace.hist):
        raise ValueError("Source feedback history does not match recorded successful stages")
    programs = {}
    experiments = []
    for index, (_, experiment, feedback) in enumerate(loop.trace.hist):
        workspace = experiment.experiment_workspace.workspace_path
        matrix_path = workspace / "combined_factors_df.pkl"
        matrix = pd.read_pickle(matrix_path)
        if not isinstance(matrix.columns, pd.MultiIndex) or set(matrix.columns.get_level_values(0)) != {"feature"}:
            raise ValueError("Unexpected native matrix columns")
        features = matrix.columns.get_level_values(1).tolist()
        rows = len(matrix)
        del matrix
        candidates = {}
        for item in experiment.sub_workspace_list:
            code = item.code_dict.get("factor.py")
            if not code:
                continue
            values = literals(code)
            if "name" not in values or "expr" not in values:
                raise ValueError("Source template identity not recoverable")
            candidates[values["name"]] = {
                "code": code,
                "expression": values["expr"],
                "workspace": str(item.workspace_path),
            }
        matrix_hash = sha256(matrix_path)
        for feature in features:
            if feature not in candidates:
                raise ValueError("Native feature has no source program: " + feature)
            item = candidates[feature]
            import hashlib

            digest = hashlib.sha256(item["code"].encode()).hexdigest()
            path = out / (digest + ".py")
            if not path.exists():
                path.write_text(item["code"])
            if sha256(path) != digest:
                raise ValueError("Immutable program changed")
            record = programs.setdefault(
                digest,
                {
                    "code": str(path.relative_to(ROOT)),
                    "sha256": digest,
                    "expression": item["expression"],
                    "source_feature_name": feature,
                    "uses": [],
                },
            )
            record["uses"].append(
                {
                    "experiment_index": index,
                    "matrix": str(matrix_path.relative_to(ROOT)),
                    "matrix_sha256": matrix_hash,
                    "column": feature,
                    "source_feedback_accepted": bool(feedback),
                }
            )
        experiments.append(
            {
                "index": index,
                "source_round_index": successful_rounds[index],
                "within_first_five_rounds": successful_rounds[index] < 5,
                "matrix": str(matrix_path.relative_to(ROOT)),
                "matrix_sha256": matrix_hash,
                "rows": rows,
                "features": features,
                "source_feedback_accepted": bool(feedback),
                "workspace": str(workspace),
                "native_account": str(workspace / "ret.pkl"),
            }
        )
    result = {
        "status": "source_used_programs_identified",
        "run": args.run_name,
        "diagnostic_early_abort": args.allow_documented_early_abort,
        "native_five_attempt_budget_complete": exit_record.get("attempted_rounds") == 5,
        "selection_basis": "all source-accepted programs; no evaluation-return selection",
        "accepted_definition": "Every factor column actually consumed by a completed native backtest, irrespective of performance or feedback; feedback acceptance is retained separately. This is not a reconstruction of the authors unreleased final optimal pool.",
        "snapshot_sha256": sha256(snapshot),
        "programs": list(programs.values()),
        "experiments": experiments,
        "program_count": len(programs),
        "successful_source_rounds": successful_rounds,
        "unsuccessful_stage_events": [row for row in stage_events if not row.get("completed")],
        "source_python_hashes": json.loads((run / "execution_recipe.json").read_text())["source_python_hashes"],
        "script_sha256": sha256(Path(__file__)),
    }
    atomic_json(run / "used_factor_manifest.json", result)
    print(
        json.dumps(
            {
                "run": args.run_name,
        "diagnostic_early_abort": args.allow_documented_early_abort,
        "native_five_attempt_budget_complete": exit_record.get("attempted_rounds") == 5,
                "programs": len(programs),
                "experiments": len(experiments),
                "features_per_experiment": [len(row["features"]) for row in experiments],
            }
        )
    )


if __name__ == "__main__":
    main()
