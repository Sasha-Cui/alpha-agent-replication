#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Matched three-control pool using the identical LLM-pool financial code block."""

from pathlib import Path
from types import SimpleNamespace
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.economic_fidelity import Factor, top_weights, daily_account
from alpha_evolve.publication_economics import cash_account
from alpha_evolve.fidelity_pool_v2 import eligible_discoveries
from alpha_evolve.fidelity_efs_grammar_pool_v2 import require_same_financial_block
from run_efs_economic_fidelity import ResearchEngine, rank_pool
from analyze_publication_upgrade import metrics, series

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    args = SimpleNamespace(group="grammar_101_103")
    protocol_path = PUBLIC / "efs_final_analysis_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    inputs = PRIVATE / "efs_grammar_pool_inputs"
    prepared = json.loads((inputs / "completion.json").read_text())
    if prepared["status"] != "archive_bound_control_libraries_and_accounts_pass" or prepared["seeds"] != [
        101,
        102,
        103,
    ]:
        raise ValueError("Fixed prepared control pool unavailable")
    if prepared["protocol_sha256"] != sha256(protocol_path) or prepared["library_sha256"] != sha256(
        inputs / "discovery_library.json"
    ):
        raise ValueError("Prepared control identity changed")
    if prepared["archive_binding_sha256"] != sha256(inputs / "archive_binding.json"):
        raise ValueError("Archive binding changed")
    computation = require_same_financial_block(
        Path(__file__).read_text(), (ROOT / "scripts/evaluate_efs_pool_v2.py").read_text()
    )
    recipe_path = ROOT / "paper_runs/economic_fidelity/efs_v1/recipe.json"
    recipe = json.loads(recipe_path.read_text())
    if sha256(recipe_path) != protocol["frozen_source_recipe_sha256"]:
        raise ValueError("Frozen EFS recipe changed")
    for name, digest in recipe["implementation_sha256"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError("Frozen EFS engine changed")
    library = json.loads((inputs / "discovery_library.json").read_text())
    raw_path = ROOT / "artifacts/economic_fidelity/v1/efs_us50_daily.parquet"
    if sha256(raw_path) != prepared["data_sha256"]:
        raise ValueError("Control market input changed")
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
    if (out / "completion.json").exists():
        raise ValueError("Preserve completed control pool")
    out.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    atomic_json(
        out / "input_control_gates.json",
        {
            "status": "pass",
            "prepared_control_sha256": sha256(inputs / "completion.json"),
            "protocol_sha256": sha256(protocol_path),
            "identical_financial_block_sha256": computation,
            "llm_pool_evaluator_sha256": sha256(ROOT / "scripts/evaluate_efs_pool_v2.py"),
            "new_model_calls": 0,
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
            "control_seeds": [101, 102, 103],
            "source_proofs": prepared["source_proofs"],
            "protocol_sha256": sha256(protocol_path),
            "script_sha256": sha256(Path(__file__)),
            "identical_financial_block_sha256": computation,
            "library_factors": len(library),
            "maximum_independent_account_error": max_error,
            "causal_discovery_gating": True,
            "retrospective_union_is_hindsight_diagnostic": True,
            "new_model_calls": 0,
            "new_search_runs": 0,
            "full_original_paper_reproduced": False,
            "input_control_gate_sha256": sha256(out / "input_control_gates.json"),
            "output_sha256": {p.name: sha256(p) for p in out.iterdir() if p.is_file() and p.name != "completion.json"},
            "private_weights_sha256": {p.name: sha256(p) for p in private.glob("*_weights.parquet")},
        },
    )
    print("MATCHED_GRAMMAR_POOL_COMPLETE", len(library), max_error, flush=True)


if __name__ == "__main__":
    main()
