#!/usr/bin/env python3
# ruff: noqa: E401, E731 - preserve the committed prospective semantic snapshot
# ruff: noqa: E402 - standalone source-path bootstrap
"""Fixed grammar search with the EFS candidate schedule, evaluator and account."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import argparse, collections, json
import numpy as np, pandas as pd
from alpha_evolve.economic_fidelity import Factor, seed_factors, top_weights, daily_account
from alpha_evolve.openrouter_budget import atomic_json, sha256
from run_efs_economic_fidelity import ResearchEngine, rank_pool

OUT = ROOT / "artifacts/publication_upgrade_v1/efs_matched"

# This grammar is fixed independently of any control outcome. Price-only expressions
# span momentum/reversal, volatility, moving-average distance and interaction terms.
PRIMITIVES = [
    "prices[-1]/prices[-window]-1",
    "np.mean(np.diff(prices[-window:])/prices[-window:-1])",
    "np.std(np.diff(prices[-window:])/prices[-window:-1])",
    "prices[-1]/np.mean(prices[-window:])-1",
    "(prices[-1]-np.min(prices[-window:]))/(np.max(prices[-window:])-np.min(prices[-window:])+1e-8)",
    "(np.mean(prices[-window:])-np.mean(prices[:-window]))/(np.std(prices)+1e-8)",
    "(prices[-1]-prices[-window])/(np.std(np.diff(prices[-window:]))+1e-8)",
    "(prices[-1]-np.median(prices[-window:]))/(np.std(prices[-window:])+1e-8)",
]


def proposal(rng, number):
    a, b = rng.integers(0, len(PRIMITIVES), size=2)
    w = int(rng.choice([3, 7, 14, 21]))
    coef = float(rng.choice([-0.75, -0.5, -0.25, 0.25, 0.5, 0.75]))
    sign = int(rng.choice([-1, 1]))
    op = int(rng.integers(0, 3))
    # Stable family label allows the same latest/best-version retention rule.
    expr = ["a+c*b", "a*(1+c*np.tanh(b))", "a/(1+abs(c*b))"][op]
    return f"def grammar_{a}_{b}_{op}_{w}_v{number}(prices, window={w}):\n    a = {PRIMITIVES[a]}\n    b = {PRIMITIVES[b]}\n    c = {coef}\n    return {sign}*({expr})\n"


def run(seed):
    recipe = json.loads((ROOT / "paper_runs/economic_fidelity/efs_v1/recipe.json").read_text())
    frozen = json.loads((ROOT / "paper_runs/publication_upgrade_v1/efs_matched_recipe.json").read_text())
    for path, expected in recipe["implementation_sha256"].items():
        if sha256(ROOT / path) != expected:
            raise ValueError("Frozen EFS implementation changed: " + path)
    frame = pd.read_parquet(ROOT / "artifacts/economic_fidelity/v1/efs_us50_daily.parquet")
    tickers = sorted(frame.ticker.unique())
    prices_df = (
        frame.pivot(index="date", columns="ticker", values="adjusted_close").reindex(columns=tickers).sort_index()
    )
    dates = pd.DatetimeIndex(prices_df.index)
    prices = prices_df.to_numpy(float)
    first = np.array([col[np.flatnonzero(np.isfinite(col) & (col > 0))[0]] for col in prices.T])
    prices = prices / first * 100
    returns = (
        frame.pivot(index="date", columns="ticker", values="ret").reindex(index=dates, columns=tickers).to_numpy(float)
    )
    execution = np.flatnonzero((dates >= recipe["start"]) & (dates <= recipe["end"]))
    source_proposals = json.loads((ROOT / "paper_runs/economic_fidelity/efs_v1/llm_proposals.json").read_text())
    schedule = collections.Counter(r["round"] for r in source_proposals if "code" in r)
    engine = ResearchEngine(prices, dates, tickers, recipe)
    pool = {f.sha256: f for f in seed_factors()}
    all_hashes = set(pool)
    rng = np.random.default_rng(seed)
    targets = np.zeros((len(execution), len(tickers)))
    selections = []
    proposals = []
    round_no = counter = 0
    for row, index in enumerate(execution):
        decision = index - 1
        chosen = []
        if row < recipe["warmup_days"]:
            eligible = np.isfinite(prices[decision - 29 : decision + 1]).all(axis=0)
            targets[row, eligible] = 1 / eligible.sum()
        else:
            stats = {key: engine.performance(factor, decision) for key, factor in pool.items()}
            ranked = rank_pool(pool, stats)
            pool = {key: pool[key] for key in ranked[: recipe["pool_max"]]}
            if (row - recipe["warmup_days"]) % recipe["search_interval_days"] == 0:
                round_no += 1
                for _ in range(schedule[round_no]):
                    counter += 1
                    code = proposal(rng, counter)
                    record = {
                        "round": round_no,
                        "number": counter,
                        "code": code,
                        "decision_date": str(dates[decision].date()),
                    }
                    try:
                        factor = Factor(code, "programmatic_grammar", decision)
                        metrics = engine.performance(factor, decision)
                        record["validation"] = metrics
                        if metrics["mean_return"] <= metrics["benchmark_mean_return"] or metrics["mean_rankic"] <= 0:
                            raise ValueError("training admission criterion not met")
                        if factor.sha256 in all_hashes:
                            raise ValueError("duplicate source")
                        pool[factor.sha256] = factor
                        all_hashes.add(factor.sha256)
                        stats[factor.sha256] = metrics
                        record["status"] = "accepted"
                    except Exception as exc:
                        record.update(status="rejected", reason=type(exc).__name__ + ": " + str(exc))
                    proposals.append(record)
            ranked = rank_pool(pool, stats)
            chosen = ranked[: recipe["selected_factors"]]
            scores = np.stack([engine.scores(pool[key], decision) for key in chosen])
            common = np.isfinite(scores).all(axis=0)
            composite = np.full(len(tickers), np.nan)
            composite[common] = scores[:, common].mean(axis=0)
            targets[row] = top_weights(composite, recipe["portfolio_assets"])
        selections.append({"date": str(dates[index].date()), "factor_hashes": chosen})
        if row % 250 == 0:
            print(seed, row, len(proposals), flush=True)
    if len(proposals) != sum(schedule.values()):
        raise ValueError("Candidate budget mismatch")
    output = OUT / f"seed_{seed}"
    output.mkdir(parents=True, exist_ok=True)
    daily = pd.DataFrame({"date": dates[execution]})
    for bp in frozen["cost_bps"]:
        r, turn, fees = daily_account(targets, returns[execution], bp)
        daily[f"total_cost_{bp}"] = r
        daily[f"turnover_cost_{bp}"] = turn
    daily.to_csv(output / "daily_returns.csv", index=False)
    pd.DataFrame(targets, index=dates[execution], columns=tickers).to_parquet(output / "weights.parquet")
    atomic_json(output / "proposals.json", proposals)
    atomic_json(output / "selections.json", selections)
    atomic_json(
        output / "completion.json",
        {
            "seed": seed,
            "days": len(daily),
            "scheduled_rounds": round_no,
            "candidate_count": len(proposals),
            "source_candidate_count": sum(schedule.values()),
            "accepted": sum(r["status"] == "accepted" for r in proposals),
            "script_sha256": sha256(Path(__file__)),
            "recipe_sha256": sha256(ROOT / "paper_runs/publication_upgrade_v1/efs_matched_recipe.json"),
            "returns_sha256": sha256(output / "daily_returns.csv"),
            "all_seed_results_must_be_reported": True,
        },
    )
    print("COMPLETE", seed, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    run(p.parse_args().seed)
