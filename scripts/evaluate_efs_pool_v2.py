#!/usr/bin/env python3
# ruff: noqa: E402 - standalone bootstrap
"""Re-evaluate complete three-trial EFS libraries with causal discovery gates."""

from pathlib import Path
import sys
import argparse
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.economic_fidelity import Factor, top_weights, daily_account
from alpha_evolve.fidelity_pool_v2 import merge_discoveries, eligible_discoveries
from alpha_evolve.fidelity_efs_pool_evidence_v2 import validate_efs_trial
from alpha_evolve.publication_economics import cash_account
from alpha_evolve.openrouter_budget import atomic_json, sha256
from run_efs_economic_fidelity import ResearchEngine, rank_pool
from analyze_publication_upgrade import metrics, series

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"
GROUPS = {
    "gpt41": ["gpt41_1", "gpt41_2", "gpt41_3"],
    "deepseek_v3": ["deepseek_v3_1", "deepseek_v3_2", "deepseek_v3_3"],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=list(GROUPS), required=True)
    args = parser.parse_args()
    protocol_path = PUBLIC / "efs_pool_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    if (PUBLIC / "efs_pooled" / args.group / "completion.json").exists():
        raise ValueError("Preserve completed pool evaluation")
    libraries, proofs, recipe = {}, {}, None
    for trial in GROUPS[args.group]:
        folder = ROOT / "paper_runs/economic_fidelity/efs_v1" if trial == "gpt41_1" else PUBLIC / "efs" / trial
        manifest_path = folder / "llm_manifest.json"
        if not manifest_path.exists():
            raise SystemExit("Required complete trajectory unavailable: " + trial)
        manifest = json.loads(manifest_path.read_text())
        if manifest["status"] != "complete" or manifest["llm_calls"] != 290:
            raise ValueError("Incomplete EFS trajectory " + trial)
        current = json.loads((folder / "recipe.json").read_text())
        for name, digest in manifest["output_sha256"].items():
            if sha256(folder / name) != digest:
                raise ValueError("Trajectory artifact changed: " + trial + "/" + name)
        if sha256(folder / "recipe.json") != manifest["recipe_sha256"]:
            raise ValueError("Trajectory recipe changed")
        if recipe is None:
            recipe = current
        else:
            for key in protocol["shared_engine_fields"]:
                if recipe[key] != current[key]:
                    raise ValueError("Incompatible pooled engine field: " + key)
        libraries[trial] = json.loads((folder / "llm_factor_library.json").read_text())
        proofs[trial] = validate_efs_trial(ROOT, trial)
    library = merge_discoveries(libraries)
    raw_path = ROOT / "artifacts/economic_fidelity/v1/efs_us50_daily.parquet"
    expected = json.loads((ROOT / "artifacts/economic_fidelity/v1/data_manifest.json").read_text())[
        "daily_extract_sha256"
    ]
    if sha256(raw_path) != expected:
        raise ValueError("Input changed")
    frame = pd.read_parquet(raw_path)
    tickers = sorted(frame.ticker.unique())
    price_frame = (
        frame.pivot(index="date", columns="ticker", values="adjusted_close").reindex(columns=tickers).sort_index()
    )
    dates, prices = pd.DatetimeIndex(price_frame.index), price_frame.to_numpy(float)
    first = np.array([col[np.flatnonzero(np.isfinite(col) & (col > 0))[0]] for col in prices.T])
    prices = prices / first * 100
    returns = (
        frame.pivot(index="date", columns="ticker", values="ret").reindex(index=dates, columns=tickers).to_numpy(float)
    )
    execution = np.flatnonzero((dates >= recipe["start"]) & (dates <= recipe["end"]))
    out = PUBLIC / "efs_pooled" / args.group
    private = PRIVATE / "efs_pooled" / args.group
    out.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    atomic_json(
        out / "input_replay_gates.json",
        {
            "status": "pass",
            "trials": proofs,
            "data_sha256": sha256(raw_path),
            "protocol_sha256": sha256(protocol_path),
            "gate_source_sha256": sha256(ROOT / "src/alpha_evolve/fidelity_efs_pool_evidence_v2.py"),
        },
    )
    factors = {key: Factor(row["code"], row["origin"], row["created_index"]) for key, row in library.items()}
    engine = ResearchEngine(prices, dates, tickers, recipe)
    summaries, max_error = [], 0.0
    for mode in ["causal_discovery_gated", "retrospective_final_union_diagnostic"]:
        hindsight = mode.startswith("retrospective")
        targets = np.zeros((len(execution), len(tickers)))
        selections = []
        for row, index in enumerate(execution):
            cutoff = int(index - 1)
            chosen = []
            available = eligible_discoveries(library, cutoff, hindsight=hindsight)
            if row < recipe["warmup_days"]:
                eligible = np.isfinite(prices[cutoff - 29 : cutoff + 1]).all(axis=0)
                targets[row, eligible] = 1 / eligible.sum()
            else:
                pool = {key: factors[key] for key in available}
                stats = {key: engine.performance(factor, cutoff) for key, factor in pool.items()}
                ranked = rank_pool(pool, stats)[: recipe["pool_max"]]
                chosen = ranked[: recipe["selected_factors"]]
                if not chosen:
                    raise ValueError("Empty selected library")
                if not hindsight and any(library[key]["created_index"] > cutoff for key in chosen):
                    raise ValueError("Future-discovered factor entered causal account")
                score = np.stack([engine.scores(pool[key], cutoff) for key in chosen])
                common = np.isfinite(score).all(axis=0)
                composite = np.full(len(tickers), np.nan)
                composite[common] = score[:, common].mean(axis=0)
                targets[row] = top_weights(composite, recipe["portfolio_assets"])
            if not np.isfinite(prices[index, targets[row] > 0]).all():
                raise ValueError("Selected execution price unavailable")
            selections.append(
                {
                    "signal_date": str(dates[cutoff].date()),
                    "execution_date": str(dates[index].date()),
                    "available_factors": len(available),
                    "selected_factor_hashes": chosen,
                    "selected_future_discoveries": sum(library[key]["created_index"] > cutoff for key in chosen),
                }
            )
        pd.DataFrame(targets, index=dates[execution], columns=tickers).to_parquet(private / (mode + "_weights.parquet"))
        output = {"date": dates[execution]}
        for cost in [0, 10, 25, 50]:
            result, turn, fees = daily_account(targets, returns[execution], cost)
            alternate = cash_account(targets, returns[execution], cost)
            error = max(float(np.max(np.abs(left - right))) for left, right in zip((result, turn, fees), alternate))
            max_error = max(max_error, error)
            if error > 1e-12:
                raise ValueError("Independent pooled account mismatch")
            output["total_cost_" + str(cost)] = result
            summaries.append(
                {"group": args.group, "mode": mode, "cost_bps": cost, **metrics(series(dates[execution], result))}
            )
        pd.DataFrame(output).to_csv(out / (mode + "_daily_returns.csv"), index=False)
        atomic_json(out / (mode + "_selections.json"), selections)
    atomic_json(out / "discovery_library.json", library)
    atomic_json(out / "performance.json", summaries)
    atomic_json(
        out / "completion.json",
        {
            "status": "complete",
            "trials": GROUPS[args.group],
            "source_proofs": proofs,
            "protocol_sha256": sha256(protocol_path),
            "script_sha256": sha256(Path(__file__)),
            "library_factors": len(library),
            "maximum_independent_account_error": max_error,
            "causal_discovery_gating": True,
            "retrospective_union_is_hindsight_diagnostic": True,
            "new_model_calls": 0,
            "full_original_paper_reproduced": False,
            "input_replay_gate_sha256": sha256(out / "input_replay_gates.json"),
            "output_sha256": {p.name: sha256(p) for p in out.iterdir() if p.is_file() and p.name != "completion.json"},
            "private_weights_sha256": {p.name: sha256(p) for p in private.glob("*_weights.parquet")},
        },
    )
    print("COMPLETE", args.group, len(library), max_error)


if __name__ == "__main__":
    main()
