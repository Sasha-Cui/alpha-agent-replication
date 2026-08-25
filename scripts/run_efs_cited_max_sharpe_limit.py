#!/usr/bin/env python3
"""Run the cited mSSRM implementation at its non-sparse m=N limit.

This is source-grounded Max-Sharpe baseline evidence only. It is not an
author-released EFS wrapper and cannot receive native EFS result credit.
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import audit_efs_paper as audit


TASKS = [
    (dataset, repeat)
    for dataset in audit.MSSRM_DATASETS
    for repeat in (1, 2)
]


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
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_nonsparse_runs"),
    )
    parser.add_argument("--task-index", type=int, choices=range(len(TASKS)), required=True)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()

    dataset, repeat = TASKS[args.task_index]
    source_name = audit.MSSRM_DATASETS[dataset]
    asset_count = audit.ASMCVAR_ASSETS[dataset]
    paper_root = args.paper_root.resolve()
    mssrm = paper_root / "mssrm_source"
    asm_cvar = paper_root / "asm_cvar_source"
    audit.validate_inputs(paper_root, mssrm, asm_cvar)

    octave = args.octave.resolve()
    version_line = subprocess.run(
        [str(octave), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[0]
    if f"version {audit.MSSRM_OCTAVE_VERSION}" not in version_line:
        raise RuntimeError(
            f"expected Octave {audit.MSSRM_OCTAVE_VERSION}, got: {version_line}"
        )

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = mssrm / "Codes_for_Experiments_in_Paper"
    data_path = (
        asm_cvar
        / "Codes_for_Experiments_in_Paper"
        / "DataSets"
        / f"{source_name}.mat"
    )
    destination = output / f"mssrm_nonsparse_{source_name}_run{repeat}.mat"
    expression = (
        "function r=tick2ret(x); r=x(2:end,:)./x(1:end-1,:)-1; endfunction; "
        f"addpath('{octave_quote(source)}'); "
        f"s=load('{octave_quote(data_path)}'); "
        "tic; "
        f"[CW,sharpe]=run_mSSRM_PGA(60,s.data,{asset_count}); "
        "elapsed=toc; "
        f"save('-mat7-binary','{octave_quote(destination)}',"
        "'CW','sharpe','elapsed'); "
        f"fprintf('DATASET={dataset} M={asset_count} REPEAT={repeat} "
        "CW_FINAL=%.12f SHARPE=%.12f ELAPSED=%.6f\\n',"
        "CW(end),sharpe,elapsed);"
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["OPENBLAS_NUM_THREADS"] = str(args.threads)
    env["OMP_NUM_THREADS"] = str(args.threads)
    if args.octave_home is not None:
        env["OCTAVE_HOME"] = str(args.octave_home.resolve())
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
    print(proc.stdout.strip().splitlines()[-1], flush=True)


if __name__ == "__main__":
    main()
