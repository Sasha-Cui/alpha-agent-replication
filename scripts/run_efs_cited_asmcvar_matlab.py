#!/usr/bin/env python3
"""Execute the cited ASMCVaR paper backtest under pinned MATLAB.

Results are cited-baseline evidence only and never native EFS evidence.
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import audit_efs_paper as audit


DATASETS = {
    "FF25": "FF25new",
    "FF25EU": "FF25EUnew",
    "FF32": "FF32new",
    "FF49": "FF49new",
    "FF100": "FF100new",
    "FF100MEOP": "FF100MEOPnew",
}
TASKS = [(dataset, sparsity) for dataset in DATASETS for sparsity in (10, 15, 20)]


def matlab_quote(value: Path) -> str:
    return str(value.resolve()).replace("'", "''")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matlab", type=Path, required=True)
    parser.add_argument("--paper-root", type=Path, default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_paper_audit"))
    parser.add_argument("--output", type=Path, default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_octave_runs"))
    parser.add_argument("--dataset", choices=tuple(DATASETS))
    parser.add_argument("--sparsity", type=int, choices=(10, 15, 20))
    parser.add_argument("--task-index", type=int, choices=range(len(TASKS)))
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=21600)
    args = parser.parse_args()

    if args.task_index is not None:
        dataset, sparsity = TASKS[args.task_index]
    elif args.dataset is not None and args.sparsity is not None:
        dataset, sparsity = args.dataset, args.sparsity
    else:
        parser.error("provide --task-index or both --dataset and --sparsity")

    paper_root = args.paper_root.resolve()
    mssrm = paper_root / "mssrm_source"
    asm_cvar = paper_root / "asm_cvar_source"
    audit.validate_inputs(paper_root, mssrm, asm_cvar)

    matlab = args.matlab.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = asm_cvar / "Codes_for_Experiments_in_Paper"
    source_name = DATASETS[dataset]
    data_path = source / "DataSets" / f"{source_name}.mat"
    destination = output / f"asmcvar_{source_name}_m{sparsity}_matlab_run{args.repeat}.mat"
    expression = (
        "assert(strcmp(version('-release'),'2023b')); "
        f"addpath('{matlab_quote(source)}'); s=load('{matlab_quote(data_path)}'); data=s.data; "
        "Param.winsize=60; Param.trancost=0/100; Param.kappa=1; "
        "Param.MaxIter1=10000; Param.MaxIter2=200; Param.tol_2=0.0001; "
        f"Param.tol_1=0.001; Param.m={sparsity}; Param.c=0.99; Param.rho=0.02; tic; "
        "[Paramout,CW,all_w,t,runout]=PALMstrategy(Param,data); elapsed=toc; "
        f"save('{matlab_quote(destination)}','CW','all_w','Paramout','t','runout','elapsed','-v7'); "
        f"fprintf('DATASET={dataset} M={sparsity} REPEAT={args.repeat} "
        "CW_FINAL=%.12f RUNOUT=%d T=%d ELAPSED=%.6f\\n',CW(end),runout,t,elapsed);"
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [str(matlab), "-batch", expression],
        check=True,
        env=env,
        text=True,
        timeout=args.timeout_seconds,
    )
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
