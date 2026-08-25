#!/usr/bin/env python3
"""Replay the cited paper's conventional Mean-CVaR baseline.

The runner implements equations (1)-(3) from the original ASMCVaR paper as a
linear program with the paper's 60-period rolling protocol. The conventional
baseline uses c=0.95; ASMCVaR itself separately uses c=0.99. Results can earn
credit for the cited Mean-CVaR paper row, but never native EFS credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from scipy.optimize import linprog

import audit_efs_paper as audit


CONFIDENCE = 0.95
WINDOW_SIZE = 60


def array_sha256(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def solve_mean_cvar(history: np.ndarray) -> np.ndarray:
    observations, assets = history.shape
    objective = np.r_[
        np.zeros(assets),
        1.0,
        np.full(observations, 1.0 / ((1.0 - CONFIDENCE) * observations)),
    ]
    inequality = np.zeros((observations, assets + 1 + observations))
    inequality[:, :assets] = -history
    inequality[:, assets] = -1.0
    inequality[:, assets + 1 :] = -np.eye(observations)
    equality = np.r_[np.ones(assets), np.zeros(1 + observations)][None, :]
    result = linprog(
        objective,
        A_ub=inequality,
        b_ub=np.zeros(observations),
        A_eq=equality,
        b_eq=np.ones(1),
        bounds=[(0.0, None)] * assets
        + [(None, None)]
        + [(0.0, None)] * observations,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"Mean-CVaR linear program failed: {result.message}")
    weights = result.x[:assets]
    if (
        np.any(weights < -1e-10)
        or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-9)
    ):
        raise RuntimeError("Mean-CVaR solver returned an infeasible portfolio")
    return weights


def run_backtest(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    returns = data - 1.0
    observations, assets = returns.shape
    weights = np.full((observations, assets), 1.0 / assets)
    wealth = np.empty(observations)
    capital = 1.0
    for index in range(observations):
        if index >= 5:
            history = returns[max(0, index - WINDOW_SIZE) : index]
            weights[index] = solve_mean_cvar(history)
        capital *= float(data[index] @ weights[index])
        wealth[index] = capital
    if not np.isfinite(wealth).all() or not np.isfinite(weights).all():
        raise RuntimeError("Mean-CVaR backtest produced non-finite output")
    return wealth, weights


def metrics(wealth: np.ndarray) -> dict[str, float]:
    returns = wealth[1:] / wealth[:-1] - 1.0
    peaks = np.maximum.accumulate(np.r_[1.0, wealth])[:-1]
    return {
        "CW": float(wealth[-1]),
        "SR": float(returns.mean() / returns.std(ddof=0)),
        "MDD": float(np.max(1.0 - wealth / peaks)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
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
    args = parser.parse_args()

    paper_root = args.paper_root.resolve()
    mssrm = paper_root / "mssrm_source"
    asm_cvar = paper_root / "asm_cvar_source"
    audit.validate_inputs(paper_root, mssrm, asm_cvar)
    data_root = asm_cvar / "Codes_for_Experiments_in_Paper" / "DataSets"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    results: dict[str, object] = {}
    for dataset, source_name in audit.ASMCVAR_DATASETS.items():
        data = np.asarray(loadmat(data_root / f"{source_name}.mat")["data"], dtype=float)
        first_wealth, first_weights = run_backtest(data)
        second_wealth, second_weights = run_backtest(data)
        repeat_equal = bool(
            np.array_equal(first_wealth, second_wealth)
            and np.array_equal(first_weights, second_weights)
        )
        if not repeat_equal:
            raise RuntimeError(f"Mean-CVaR repeats differ for {dataset}")
        for repeat, wealth, weights in (
            (1, first_wealth, first_weights),
            (2, second_wealth, second_weights),
        ):
            np.savez_compressed(
                output / f"mean_cvar_{source_name}_run{repeat}.npz",
                wealth=wealth,
                weights=weights,
            )
        results[dataset] = {
            "source_name": source_name,
            "observations": int(data.shape[0]),
            "assets": int(data.shape[1]),
            "metrics": metrics(first_wealth),
            "wealth_sha256": array_sha256(first_wealth),
            "weights_sha256": array_sha256(first_weights),
            "repeat_equal": repeat_equal,
        }

    payload = {
        "paper_credit_scope": "original_mean_cvar_baseline_only_not_native_efs",
        "model": "ASMCVaR paper equations (1)-(3)",
        "confidence": CONFIDENCE,
        "lookback": WINDOW_SIZE,
        "initial_equal_weight_periods": 5,
        "solver": "scipy.optimize.linprog(method='highs')",
        "results": results,
    }
    destination = output / "mean_cvar_execution_metadata.json"
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
