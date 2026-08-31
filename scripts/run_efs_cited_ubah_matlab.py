#!/usr/bin/env python3
"""Run the cited ASMCVaR UBAH source on the five EFS benchmark matrices.

This is cited-baseline evidence only. It executes the released ubah_run_self.m,
sharpe1self.m, and MATLAB maxdrawdown path without changing their formulas.
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import audit_efs_paper as audit


TASKS = [
    (dataset, repeat)
    for dataset in ("FF25", "FF32", "FF49", "FF100", "FF100MEOP")
    for repeat in (1, 2)
]


def matlab_quote(value: Path) -> str:
    return str(value.resolve()).replace("'", "''")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matlab", type=Path, required=True)
    parser.add_argument(
        "--paper-root",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_paper_audit"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_ubah_runs"),
    )
    parser.add_argument(
        "--task-index",
        type=int,
        choices=range(len(TASKS)),
        required=True,
    )
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()

    dataset, repeat = TASKS[args.task_index]
    source_name = audit.ASMCVAR_DATASETS[dataset]
    paper_root = args.paper_root.resolve()
    asm_cvar = paper_root / "asm_cvar_source"
    if audit.run_git(asm_cvar, "rev-parse", "HEAD").strip() != audit.ASMCVAR_COMMIT:
        raise RuntimeError("ASMCVaR source commit changed")
    if audit.run_git(asm_cvar, "rev-parse", "HEAD^{tree}").strip() != audit.ASMCVAR_TREE:
        raise RuntimeError("ASMCVaR source tree changed")

    source = asm_cvar / "Codes_for_Experiments_in_Paper"
    data_path = source / "DataSets" / f"{source_name}.mat"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"ubah_{source_name}_run{repeat}.mat"
    prefdir = output / "matlab_preferences"
    prefdir.mkdir(parents=True, exist_ok=True)

    expression = (
        f"addpath('{matlab_quote(source)}'); "
        f"s=load('{matlab_quote(data_path)}'); "
        "tic; "
        "[cum_ret,cumprod_ret,daily_ret,daily_portfolio]="
        "ubah_run_self(s.data); "
        "Sharpe=sharpe1self(cumprod_ret); "
        "MaxDD=maxdrawdown(cumprod_ret); "
        "elapsed=toc; "
        "matlab_release=version('-release'); "
        f"save('{matlab_quote(destination)}','cum_ret','cumprod_ret',"
        "'daily_ret','daily_portfolio','Sharpe','MaxDD','elapsed',"
        "'matlab_release','-v7'); "
        f"fprintf('DATASET={dataset} REPEAT={repeat} "
        "CW=%.12f SR=%.12f MDD=%.12f ELAPSED=%.6f\\n',"
        "cum_ret,Sharpe,MaxDD,elapsed);"
    )
    env = os.environ.copy()
    env["MATLAB_PREFDIR"] = str(prefdir)
    env["OMP_NUM_THREADS"] = str(args.threads)
    env["MKL_NUM_THREADS"] = str(args.threads)
    proc = subprocess.run(
        [
            str(args.matlab.resolve()),
            "-singleCompThread",
            "-batch",
            expression,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=args.timeout_seconds,
    )
    result_lines = [
        line for line in proc.stdout.splitlines() if line.startswith("DATASET=")
    ]
    if len(result_lines) != 1:
        raise RuntimeError(
            "MATLAB UBAH result marker missing or duplicated: "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    print(result_lines[0], flush=True)


if __name__ == "__main__":
    main()
