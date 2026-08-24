#!/usr/bin/env python3
"""Run the cited mSSRM baseline release used in the EFS benchmark table.

This is cited-baseline evidence only. It does not execute or validate EFS.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import audit_efs_paper as audit


def octave_quote(value: Path) -> str:
    return str(value.resolve()).replace("'", "''")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--octave", type=Path, required=True)
    parser.add_argument("--octave-home", type=Path)
    parser.add_argument(
        "--paper-root",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_paper_audit"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_octave_runs"),
    )
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()

    paper_root = args.paper_root.resolve()
    output = args.output.resolve()
    mssrm = paper_root / "mssrm_source"
    asm_cvar = paper_root / "asm_cvar_source"
    audit.validate_inputs(paper_root, mssrm, asm_cvar)

    octave = args.octave.resolve()
    version_line = subprocess.run(
        [str(octave), "--version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    if f"version {audit.MSSRM_OCTAVE_VERSION}" not in version_line:
        raise RuntimeError(f"expected Octave {audit.MSSRM_OCTAVE_VERSION}, got: {version_line}")

    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["OPENBLAS_NUM_THREADS"] = str(args.threads)
    env["OMP_NUM_THREADS"] = str(args.threads)
    if args.octave_home is not None:
        env["OCTAVE_HOME"] = str(args.octave_home.resolve())

    source = mssrm / "Codes_for_Experiments_in_Paper"
    data_root = asm_cvar / "Codes_for_Experiments_in_Paper" / "DataSets"
    logs: list[dict[str, object]] = []
    for dataset, source_name in audit.MSSRM_DATASETS.items():
        for sparsity in (10, 15, 20):
            for repeat in (1, 2):
                destination = output / f"mssrm_{source_name}_m{sparsity}_run{repeat}.mat"
                expression = (
                    "function r=tick2ret(x); r=x(2:end,:)./x(1:end-1,:)-1; endfunction; "
                    f"addpath('{octave_quote(source)}'); "
                    f"s=load('{octave_quote(data_root / f'{source_name}.mat')}'); "
                    "tic; "
                    f"[CW,sharpe]=run_mSSRM_PGA(60,s.data,{sparsity}); "
                    "elapsed=toc; "
                    f"save('-mat7-binary','{octave_quote(destination)}','CW','sharpe','elapsed'); "
                    f"fprintf('DATASET={dataset} M={sparsity} REPEAT={repeat} "
                    "CW_FINAL=%.12f SHARPE=%.12f ELAPSED=%.6f\\n',CW(end),sharpe,elapsed);"
                )
                proc = subprocess.run(
                    [
                        str(octave),
                        "--no-init-file",
                        "--no-site-file",
                        "--quiet",
                        "--eval",
                        expression,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=args.timeout_seconds,
                )
                summary = proc.stdout.strip().splitlines()[-1]
                print(summary, flush=True)
                logs.append(
                    {
                        "dataset": dataset,
                        "sparsity": sparsity,
                        "repeat": repeat,
                        "summary": summary,
                        "output": destination.name,
                    }
                )

    metrics = audit.load_mssrm_native_metrics(output)
    metadata = {
        "paper_credit_scope": "cited_mssrm_baseline_only_not_native_efs",
        "octave_version": audit.MSSRM_OCTAVE_VERSION,
        "mssrm_commit": audit.MSSRM_COMMIT,
        "asmcvar_data_commit": audit.ASMCVAR_COMMIT,
        "lookback": 60,
        "sparsity_values": [10, 15, 20],
        "tick2ret_compatibility_shim": "x[1:]/x[:-1]-1",
        "runs": logs,
        "cw_sha256": {
            f"{dataset}_m{sparsity}": value["cw_sha256"]
            for (dataset, sparsity), value in sorted(metrics.items())
        },
        "all_15_full_wealth_paths_repeat_exact": all(
            value["repeat_paths_equal"] for value in metrics.values()
        ),
    }
    (output / "mssrm_native_execution_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
