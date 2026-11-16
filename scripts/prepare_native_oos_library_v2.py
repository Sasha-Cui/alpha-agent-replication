#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Materialize a fixed source-used library without evaluating future returns."""

from pathlib import Path
import argparse
import sys
import json
import hashlib
import subprocess
import tempfile
import os
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["alphaagent", "quantaalpha"], required=True)
    parser.add_argument("--run-names", nargs="+", required=True)
    parser.add_argument("--output-name", required=True)
    parser.add_argument(
        "--experiment-index",
        type=int,
        help="One prespecified source task, for the complete task-by-task secondary panel",
    )
    parser.add_argument(
        "--reuse-library",
        type=Path,
        help="Reuse only hash-verified fixed program columns with identical data and membership",
    )
    args = parser.parse_args()
    if args.experiment_index is not None and len(args.run_names) != 1:
        raise ValueError("An individual experiment requires exactly one source run")
    out = PRIVATE / args.output_name
    out.mkdir(parents=True, exist_ok=True)
    if (out / "library_manifest.json").exists():
        raise ValueError("Preserve completed fixed library")
    bounded = json.loads((PRIVATE / "bounded_factor_inputs/manifest.json").read_text())
    data = (
        Path(bounded["inputs"]["alphaagent/evaluation"]["path"])
        if args.case == "alphaagent"
        else PRIVATE / "quantaalpha_data/full/daily_pv.h5"
    )
    source = PRIVATE / "dependencies" / ("alphaagent_95e478" if args.case == "alphaagent" else "quantaalpha_b7ceb27")
    wrapper = (
        ROOT
        / "scripts"
        / ("run_alphaagent_paper_host_python.sh" if args.case == "alphaagent" else "run_quantaalpha_v2_python.sh")
    )
    provider = Path(json.loads((PRIVATE / "quantaalpha_data/manifest.json").read_text())["provider_path"])
    market = "csi500" if args.case == "alphaagent" else "csi300"
    intervals = {}
    membership_path = provider / "instruments" / f"{market}.txt"
    for line in membership_path.read_text().splitlines():
        stock, start, end = line.split()[:3]
        intervals.setdefault(stock, []).append((pd.Timestamp(start), pd.Timestamp(end)))
    programs = {}
    manifests = {}
    for name in args.run_names:
        run = PRIVATE / name
        if args.case == 'alphaagent':
            from alpha_constructor_abort_v3 import validate_five as validate_alpha_five_attempts
            validate_alpha_five_attempts(run)
            for gate in ['full_replay_validation.json', 'independent_accounts/validation.json']:
                if json.loads((run / gate).read_text()).get('status') != 'pass':
                    raise ValueError('Alpha source replay/account gate incomplete: ' + name)
        runtime_path = run / ("execution_recipe.json" if args.case == "alphaagent" else "recipe.json")
        runtime = json.loads(runtime_path.read_text())
        if "bounded_input_manifest_sha256" not in runtime:
            raise ValueError("Unbounded search is not eligible for this evaluation")
        manifest_path = run / "used_factor_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifests[name] = sha256(manifest_path)
        allowed = {row["index"] for row in manifest["experiments"] if row.get("within_first_five_rounds", True)}
        if args.experiment_index is not None:
            if args.experiment_index not in allowed:
                raise ValueError("Requested source experiment is absent or outside the fixed round budget")
            allowed = {args.experiment_index}
        for row in manifest["programs"]:
            if not any(use["experiment_index"] in allowed for use in row["uses"]):
                continue
            code = ROOT / row["code"]
            if sha256(code) != row["sha256"]:
                raise ValueError("Source-used code changed")
            entry = programs.setdefault(row["sha256"], {**row, "runs": []})
            entry["runs"].append(name)
    if not programs:
        raise ValueError("No source-used programs; report the failed search without fabricating a strategy")
    reuse = None
    if args.reuse_library:
        reuse = args.reuse_library.resolve()
        reuse_manifest = json.loads((reuse / "library_manifest.json").read_text())
        if (
            reuse_manifest["case"] != args.case
            or reuse_manifest["data_sha256"] != sha256(data)
            or reuse_manifest["membership_sha256"] != sha256(membership_path)
        ):
            raise ValueError("Reusable program library has different inputs or universe")
    frames = {}
    proofs = []
    expression_values = {}
    for digest, row in sorted(programs.items()):
        output = out / (digest + ".parquet")
        proof_path = out / (digest + ".json")
        if reuse and not output.exists() and not proof_path.exists() and (reuse / (digest + ".parquet")).exists():
            source_output = reuse / (digest + ".parquet")
            source_proof = json.loads((reuse / (digest + ".json")).read_text())
            if (
                source_proof["code_sha256"] != digest
                or source_proof["data_sha256"] != sha256(data)
                or source_proof["output_sha256"] != sha256(source_output)
            ):
                raise ValueError("Reusable fixed program column changed")
            os.link(source_output, output)
            atomic_json(
                proof_path,
                {**source_proof, "source_runs": row["runs"], "reused_from": str(source_output.relative_to(ROOT))},
            )
        if output.exists() and proof_path.exists():
            proof = json.loads(proof_path.read_text())
            if (
                proof["code_sha256"] != digest
                or proof["data_sha256"] != sha256(data)
                or sha256(output) != proof["output_sha256"]
            ):
                raise ValueError("Cached factor materialization changed")
            frame = pd.read_parquet(output)
        else:
            with tempfile.TemporaryDirectory(prefix="materialize_", dir=out) as temp:
                work = Path(temp) / "work"
                command = [
                    str(wrapper),
                    str(ROOT / "scripts/run_fidelity_factor_prefix_child_v2.py"),
                    "--code",
                    str(ROOT / row["code"]),
                    "--data",
                    str(data),
                    "--work",
                    str(work),
                    "--source",
                    str(source),
                ]
                result = subprocess.run(
                    command,
                    env={
                        **os.environ,
                        "PYTHONDONTWRITEBYTECODE": "1",
                        "OMP_NUM_THREADS": "1",
                        "OPENBLAS_NUM_THREADS": "1",
                        "NUMEXPR_NUM_THREADS": "1",
                    },
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=1800,
                )
                if result.returncode:
                    atomic_json(out / (digest + "_failure.json"), {"code": row["code"], "log": result.stdout[-12000:]})
                    raise RuntimeError("Fixed source program failed; do not drop it based on outcomes")
                value = pd.read_hdf(work / "result.h5")
                if isinstance(value, pd.DataFrame):
                    if value.shape[1] != 1:
                        raise ValueError("Expected one factor per program")
                    value = value.iloc[:, 0]
                # Calculate on the complete source universe, then retain only
                # dated model-universe rows. Never filter calculation history.
                selected = []
                for stock, series in value.groupby(level="instrument", sort=False):
                    dates = series.index.get_level_values("datetime")
                    mask = np.zeros(len(series), bool)
                    for start, end in intervals.get(stock, []):
                        mask |= np.asarray((dates >= start) & (dates <= end))
                    selected.append(series.loc[mask])
                value = pd.concat(selected).sort_index()
                value = value.loc[
                    (value.index.get_level_values("datetime") >= "2015-01-01")
                    & (value.index.get_level_values("datetime") <= "2025-12-26")
                ]
                frame = value.rename("value").to_frame()
                frame.to_parquet(output)
            proof = {
                "code_sha256": digest,
                "data_sha256": sha256(data),
                "output_sha256": sha256(output),
                "expression": row["expression"],
                "source_runs": row["runs"],
                "rows": len(frame),
                "infinite_raw_values": int(np.isinf(frame.to_numpy()).sum()),
                "no_new_period_returns_evaluated": True,
            }
            atomic_json(proof_path, proof)
        expression = row["expression"].strip()
        identity = hashlib.sha256(expression.encode()).hexdigest()
        if identity in expression_values:
            pd.testing.assert_frame_equal(expression_values[identity], frame, check_exact=True)
            proof["duplicate_of_expression"] = identity
        else:
            expression_values[identity] = frame
            frames["LLM_" + identity[:16]] = frame["value"]
        proofs.append(proof)
        print("FIXED_FACTOR", digest, len(frame), flush=True)
    matrix = pd.concat(frames, axis=1).sort_index()
    matrix.columns = pd.MultiIndex.from_product([["feature"], matrix.columns])
    matrix.to_parquet(out / "fixed_factors.parquet")
    # Alpha's historically reconstructed Qlib environment has no Parquet reader.
    matrix.to_pickle(out / "fixed_factors.pkl")
    atomic_json(
        out / "library_manifest.json",
        {
            "status": "materialized_not_yet_validated_for_evaluation",
            "case": args.case,
            "source_runs": args.run_names,
            "source_manifests": manifests,
            "alpha_terminal_gate_source_sha256": sha256(ROOT / "scripts/fidelity_alpha_terminal_v2.py") if args.case == "alphaagent" else None,
            "source_trial_completion_hashes": {
                name: sha256(PRIVATE / name / "execution_exit.json") for name in args.run_names
            } if args.case == "alphaagent" else {},
            "experiment_index_filter": args.experiment_index,
            "reused_program_library_manifest_sha256": sha256(reuse / "library_manifest.json") if reuse else None,
            "selection": "All actually source-used programs in the declared source runs/optional prespecified task, within five Alpha rounds; no outcome-based selection. Exact-expression duplicates require identical numerical columns. Individual task libraries are secondary and cannot substitute for a complete primary library.",
            "programs": proofs,
            "distinct_expressions": len(frames),
            "matrix_rows": len(matrix),
            "matrix_sha256": sha256(out / "fixed_factors.parquet"),
            "pickle_sha256": sha256(out / "fixed_factors.pkl"),
            "data_sha256": sha256(data),
            "membership_sha256": sha256(membership_path),
            "no_new_period_returns_evaluated": True,
            "requires_full_replay_causality_and_account_gates": True,
            "script_sha256": sha256(Path(__file__)),
        },
    )


if __name__ == "__main__":
    main()
