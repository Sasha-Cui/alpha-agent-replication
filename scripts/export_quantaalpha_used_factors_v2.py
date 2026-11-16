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
SOURCE = ROOT / "artifacts/fidelity_completion_v2/dependencies/quantaalpha_b7ceb27"
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
    args = parser.parse_args()
    run = ROOT / "artifacts/fidelity_completion_v2" / args.run_name
    exit_record = json.loads((run / "execution_exit.json").read_text())
    if exit_record["status"] != "native_pipeline_returned":
        raise ValueError("Native evolution did not return")

    def offline(*a, **kw):
        raise RuntimeError("Snapshot extraction cannot access network")

    socket.create_connection = offline
    socket.socket.connect = offline
    pool = json.loads((run / "log/trajectory_pool.json").read_text())
    histories = []
    snapshot_hashes = {}
    for trajectory in sorted(pool["trajectories"].values(), key=lambda row: (row["round_idx"], row["direction_id"])):
        branch = f"{trajectory['phase']}_{trajectory['round_idx']:02d}_{trajectory['direction_id']:02d}"
        snapshot = run / "log" / branch / "__session__/0/4_feedback"
        with snapshot.open("rb") as stream:
            loop = pickle.load(stream)
        if len(loop.trace.hist) != 1:
            raise ValueError("Unexpected source task iteration count")
        snapshot_hashes[str(snapshot.relative_to(ROOT))] = sha256(snapshot)
        histories.append((trajectory, loop.trace.hist[0]))
    out = run / "used_programs"
    out.mkdir(exist_ok=True)
    programs = {}
    experiments = []
    for index, (trajectory, (_, experiment, feedback)) in enumerate(histories):
        workspace = experiment.experiment_workspace.workspace_path
        matrix_path = workspace / "combined_factors_df.parquet"
        matrix = pd.read_parquet(matrix_path)
        if not isinstance(matrix.columns, pd.MultiIndex) or set(matrix.columns.get_level_values(0)) != {"feature"}:
            raise ValueError("Unexpected native matrix columns")
        features = matrix.columns.get_level_values(1).tolist()
        rows = len(matrix)
        del matrix
        candidates = {}
        for item in experiment.sub_workspace_list:
            code = (getattr(item, "code_dict", None) or getattr(item, "file_dict", {})).get("factor.py")
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
                "native_config": "conf_combined_factors.yaml",
                "trajectory_id": trajectory["trajectory_id"],
                "phase": trajectory["phase"],
                "round_idx": trajectory["round_idx"],
                "direction_id": trajectory["direction_id"],
                "within_nominal_three_round_limit": trajectory["round_idx"] < 3,
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
        "selection_basis": "all source-accepted programs; no evaluation-return selection",
        "accepted_definition": "Every factor column actually consumed by a completed native backtest, irrespective of performance or feedback; feedback acceptance is retained separately. This is not a reconstruction of the authors unreleased final optimal pool.",
        "snapshot_sha256": snapshot_hashes,
        "trajectory_pool_sha256": sha256(run / "log/trajectory_pool.json"),
        "programs": list(programs.values()),
        "experiments": experiments,
        "program_count": len(programs),
        "source_python_hashes": {str(p.relative_to(SOURCE)): sha256(p) for p in sorted(SOURCE.rglob("*.py"))},
        "script_sha256": sha256(Path(__file__)),
    }
    atomic_json(run / "used_factor_manifest.json", result)
    print(
        json.dumps(
            {
                "run": args.run_name,
                "programs": len(programs),
                "experiments": len(experiments),
                "features_per_experiment": [len(row["features"]) for row in experiments],
            }
        )
    )


if __name__ == "__main__":
    main()
