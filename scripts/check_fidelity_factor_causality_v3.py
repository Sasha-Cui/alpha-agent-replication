#!/usr/bin/env python3
# ruff: noqa: E402 - standalone bootstrap
"""Re-execute every distinct native factor on full and truncated historical data."""

from pathlib import Path
import argparse
import sys
import json
import subprocess
import tempfile
import os
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import sha256, atomic_json
from alpha_evolve.fidelity_causality_v2 import compare_prefix

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["quantaalpha", "alphaagent"], required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--debug-fixture", action="store_true")
    parser.add_argument(
        "--data-file", type=Path, help="Explicit evaluation panel matching the source schema and start date"
    )
    parser.add_argument("--factor-manifest", type=Path, help="Hash-pinned list of every source-accepted factor program")
    parser.add_argument(
        "--program-index", type=int, help="One fixed manifest program; do not write a partial library certificate"
    )
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if not run.is_relative_to(PRIVATE) or not run.is_dir():
        raise ValueError("Expected private run directory")
    source = PRIVATE / "dependencies" / ("quantaalpha_b7ceb27" if args.case == "quantaalpha" else "alphaagent_95e478")
    wrapper = (
        ROOT
        / "scripts"
        / ("run_quantaalpha_v2_python.sh" if args.case == "quantaalpha" else "run_alphaagent_paper_host_python.sh")
    )
    data = PRIVATE / "quantaalpha_data" / ("debug" if args.debug_fixture else "full") / "daily_pv.h5"
    if args.data_file:
        data = args.data_file.resolve()
    from quanta_continued_matrix_lineage_v1 import load_matrix_scope,assert_use_binding
    matrix_bindings,matrix_lineage_receipt=load_matrix_scope(ROOT,run,args.factor_manifest,args.case,args.debug_fixture,args.data_file)
    input_hash = sha256(data)
    source_hashes = {str(p.relative_to(source)): sha256(p) for p in sorted(source.rglob("*.py"))}
    source_hash = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    candidates = {}
    uses = {}
    selection_proof = None
    if args.factor_manifest:
        selection_proof = json.loads(args.factor_manifest.read_text())
        if selection_proof.get("selection_basis") != "all source-accepted programs; no evaluation-return selection":
            raise ValueError("Missing source acceptance selection contract")
        for row in selection_proof["programs"]:
            code = (ROOT / row["code"]).resolve()
            if not code.is_relative_to(run) or sha256(code) != row["sha256"]:
                raise ValueError("Selected factor program changed or is outside the run")
            candidates.setdefault(row["sha256"], code)
            uses[row["sha256"]] = row.get("uses", [])
    else:
        for code in sorted(run.rglob("factor.py")):
            candidates.setdefault(sha256(code), code)
    if not candidates:
        raise ValueError("No generated native factor program found")
    out = run / ("causality_debug_plumbing" if args.debug_fixture else "causality_full_universe")
    if args.debug_fixture:
        out = run / "causality_debug_nonvacuous"
    out.mkdir(exist_ok=True)
    results = []
    selected_candidates = list(candidates.items())
    if args.program_index is not None:
        if not 0 <= args.program_index < len(selected_candidates):
            raise ValueError("Program index outside immutable manifest")
        selected_candidates = [selected_candidates[args.program_index]]
    for digest, code in selected_candidates:
        proof_path = out / (digest + ".json")
        if proof_path.exists():
            proof = json.loads(proof_path.read_text())
            if (
                proof.get("driver_sha256") != sha256(Path(__file__))
                or proof.get("continued_native_matrix_lineage") != matrix_lineage_receipt
                or proof.get("child_sha256") != sha256(ROOT / "scripts/run_fidelity_factor_prefix_child_v2.py")
                or proof["input_sha256"] != input_hash
                or proof["code_sha256"] != sha256(code)
                or proof.get("source_python_sha256") != source_hash
            ):
                raise ValueError("Saved causality inputs changed")
            results.append(proof)
            continue
        if args.collect_only:
            raise ValueError("Required factor proof missing: " + digest)
        with tempfile.TemporaryDirectory(prefix="prefix_check_", dir=out) as temporary:
            root = Path(temporary)
            reference = None
            comparisons = []
            matrix_checks = []
            cutoffs = (
                [
                    ("2018_mid", "2018-06-29"),
                    ("2018_end", "2018-12-28"),
                    ("2019_mid", "2019-06-28"),
                    ("2019_late", "2019-09-30"),
                ]
                if args.debug_fixture
                else [("2019", "2019-12-31"), ("2020", "2020-12-31"), ("2021", "2021-12-31"), ("2024", "2024-12-31")]
            )
            for label, cutoff in [("full", None)] + cutoffs:
                work = root / label
                command = [
                    str(wrapper),
                    str(ROOT / "scripts/run_fidelity_factor_prefix_child_v2.py"),
                    "--code",
                    str(code),
                    "--data",
                    str(data),
                    "--work",
                    str(work),
                    "--source",
                    str(source),
                ]
                if cutoff:
                    command += ["--cutoff", cutoff]
                completed = subprocess.run(
                    command,
                    env={
                        **os.environ,
                        "PYTHONDONTWRITEBYTECODE": "1",
                        "OPENBLAS_NUM_THREADS": "1",
                        "OMP_NUM_THREADS": "1",
                    },
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=1800,
                )
                if completed.returncode:
                    comparisons.append(
                        {"cutoff": cutoff, "status": "execution_failure", "log": completed.stdout[-12000:]}
                    )
                    break
                actual = pd.read_hdf(work / "result.h5")
                if reference is None:
                    reference = actual
                    if uses.get(digest) and not args.debug_fixture:
                        computed = (
                            reference.iloc[:, 0]
                            if isinstance(reference, pd.DataFrame) and reference.shape[1] == 1
                            else reference
                        )
                        if not isinstance(computed, pd.Series):
                            raise ValueError("Expected one native factor per program")
                        for use in uses[digest]:
                            matrix_path = ROOT / use["matrix"]
                            assert_use_binding(ROOT,use,matrix_bindings)
                            matrix = (
                                pd.read_parquet(matrix_path)
                                if matrix_path.suffix == ".parquet"
                                else pd.read_pickle(matrix_path)
                            )
                            native = matrix[("feature", use["column"])]
                            if computed.name != use["column"]:
                                raise ValueError("Program output name does not match native feature")
                            check = compare_prefix(
                                computed.rename("value"),
                                native.rename("value"),
                                native.index.get_level_values("datetime").max(),
                            )
                            matrix_checks.append(
                                {"experiment_index": use["experiment_index"], "column": use["column"], **check}
                            )
                            del matrix, native
                else:
                    comparisons.append(
                        {"cutoff": cutoff, **compare_prefix(reference, actual, cutoff, require_future_rows=True)}
                    )
            proof = {
                "status": "pass"
                if len(comparisons) == 4
                and all(r["status"] == "pass" for r in comparisons)
                and all(r["status"] == "pass" for r in matrix_checks)
                else "fail",
                "code": str(code.relative_to(ROOT)),
                "code_sha256": digest,
                "input_sha256": input_hash,
                "source_python_sha256": source_hash,
                "native_matrix_checks": matrix_checks,
                "continued_native_matrix_lineage": matrix_lineage_receipt,
                "raw_infinite_values_present": any(
                    r.get("infinite_values", 0) > 0 for r in comparisons + matrix_checks
                ),
                "nonfinite_scope": "Infinite raw values are separately flagged for native preprocessing review; matching infinities alone are not evidence of future-row leakage.",
                "comparisons": comparisons,
                "scope": "debug plumbing only; no full-universe causality claim"
                if args.debug_fixture
                else "full released HDF universe at four fixed historical cutoffs; not a proof against all forms of leakage",
                "network_calls_permitted": False,
                "driver_sha256": sha256(Path(__file__)),
                "child_sha256": sha256(ROOT / "scripts/run_fidelity_factor_prefix_child_v2.py"),
            }
            atomic_json(proof_path, proof)
            results.append(proof)
            print(digest, proof["status"], flush=True)
    if args.program_index is not None:
        if any(r["status"] != "pass" for r in results):
            raise SystemExit(1)
        return
    atomic_json(
        out / "summary.json",
        {
            "status": "pass" if all(r["status"] == "pass" for r in results) else "fail",
            "distinct_programs": len(results),
            "passed": sum(r["status"] == "pass" for r in results),
            "debug_fixture_only": args.debug_fixture,
            "acceptance_manifest_sha256": sha256(args.factor_manifest) if args.factor_manifest else None,
            "certifies_selected_library": bool(selection_proof)
            and not args.debug_fixture
            and all(r["status"] == "pass" for r in results),
            "source_python_sha256": source_hash,
            "raw_nonfinite_review_required": any(r.get("raw_infinite_values_present", False) for r in results),
            "selection_scope": "source-accepted manifest"
            if selection_proof
            else "all generated files, including rejected attempts; accepted-library identity unresolved",
            "programs": results,
        },
    )
    if any(r["status"] != "pass" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
