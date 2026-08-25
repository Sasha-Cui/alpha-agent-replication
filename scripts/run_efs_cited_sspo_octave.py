#!/usr/bin/env python3
"""Run the JMLR-linked SSPO source on one EFS benchmark matrix.

This is cited-baseline evidence only. The only compatibility shim implements
MATLAB wthresh soft thresholding exactly for the call used by SSPO_fun.m.
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import audit_efs_paper as audit


TASKS_BY_SCOPE = {
    "efs": [
        (dataset, repeat) for dataset in audit.MSSRM_DATASETS for repeat in (1, 2)
    ],
    "original": [
        (dataset, repeat)
        for dataset in audit.SSPO_ORIGINAL_DATASETS
        for repeat in (1, 2)
    ],
}


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
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_sspo_runs"),
    )
    parser.add_argument("--dataset-scope", choices=tuple(TASKS_BY_SCOPE), default="efs")
    parser.add_argument("--task-index", type=int, choices=range(10), required=True)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()

    dataset, repeat = TASKS_BY_SCOPE[args.dataset_scope][args.task_index]
    source_name = (
        audit.MSSRM_DATASETS[dataset]
        if args.dataset_scope == "efs"
        else audit.SSPO_ORIGINAL_DATASETS[dataset]
    )
    paper_root = args.paper_root.resolve()
    sspo = paper_root / "sspo_source"
    asm_cvar = paper_root / "asm_cvar_source"
    olps = paper_root / "olps_source"
    if audit.run_git(sspo, "rev-parse", "HEAD").strip() != audit.SSPO_COMMIT:
        raise RuntimeError("SSPO source commit changed")

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
    if args.dataset_scope == "efs":
        data_path = (
            asm_cvar
            / "Codes_for_Experiments_in_Paper"
            / "DataSets"
            / f"{source_name}.mat"
        )
        destination = output / f"sspo_{source_name}_run{repeat}.mat"
    else:
        data_path = olps / "Data" / f"{source_name}.mat"
        destination = output / f"sspo_original_{source_name}_run{repeat}.mat"
    expression = (
        "function y=wthresh(x,mode,threshold); "
        "if strcmp(mode,'s'); y=sign(x).*max(abs(x)-threshold,0); "
        "else; error('unsupported wthresh mode'); endif; endfunction; "
        f"addpath('{octave_quote(sspo)}'); "
        f"s=load('{octave_quote(data_path)}'); "
        "opts=struct(); tic; "
        "[CW,daily_incre_fact,daily_port_total,prim_res_total,iter_total]="
        "SSPO_run(s.data,opts); elapsed=toc; "
        f"save('-mat7-binary','{octave_quote(destination)}',"
        "'CW','daily_incre_fact','daily_port_total','iter_total','elapsed'); "
        f"fprintf('DATASET={dataset} REPEAT={repeat} "
        "CW_FINAL=%.12f ELAPSED=%.6f\\n',CW(end),elapsed);"
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
