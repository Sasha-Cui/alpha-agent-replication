#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source bootstrap
"""Validate causal clocks and independently reconstruct v2 source-agent accounts."""

from pathlib import Path
import sys
import json
import argparse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_economics import cash_account, categorical_targets
from alpha_evolve.fidelity_accounts_v2 import binary_share_account, equal_initial_capital
from analyze_publication_upgrade import metrics, series, whole_account
from fidelity_equity_evidence_v3 import validate_source, final_output_guard

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def read(path):
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.suffix == ".jsonl"
        else json.loads(path.read_text())
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    out = PUBLIC / ("account_preview" if args.allow_partial else "accounts")
    private_out = PRIVATE / out.name
    runs = [
        (case, symbol)
        for case, symbols in [
            ("finmem", ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]),
            ("tradingagents", ["AAPL", "GOOGL", "AMZN"]),
            ("finagent", ["TSLA", "AAPL", "AMZN", "GOOGL", "MSFT"]),
        ]
        for symbol in symbols
    ]
    checks, missing, performance, paths, source_scores = [], [], [], {}, []
    overrides = read(PUBLIC / "primary_run_overrides.json") if (PUBLIC / "primary_run_overrides.json").exists() else {}
    # Resolve every source and full replay before computing any account. The
    # final path refuses partial input sets and preserves existing attempts.
    admitted = {}
    pending = []
    for case, symbol in runs:
        name = case + '_' + symbol
        frozen = case == 'finmem' and symbol == 'TSLA'
        source = ROOT / 'artifacts/publication_upgrade_v1/finmem_native' if frozen else PRIVATE / name
        recipe = ROOT / 'paper_runs/publication_upgrade_v1/finmem_recipe.json' if frozen else PUBLIC / 'recipes' / (name + '.json')
        if name in overrides:
            source = PRIVATE / overrides[name]['run_directory']
            recipe = ROOT / overrides[name]['recipe']
        completion = source / 'completion.json'
        replay = ROOT / 'artifacts/publication_upgrade_v1/finmem_full_replay_validation.json' if frozen else PRIVATE / (source.name + '_full_replay_validation.json')
        if not completion.exists() or read(completion).get('status') != 'complete' or not replay.exists():
            pending.append(name)
            continue
        admitted[name] = validate_source(ROOT, source, recipe, case, frozen=frozen)
    if not args.allow_partial:
        if pending:
            raise ValueError('Final accounts require every source and verified full replay; pending: ' + ', '.join(pending))
        final_output_guard(out, private_out)
    out.mkdir(exist_ok=True)
    private_out.mkdir(exist_ok=True)
    for case, symbol in runs:
        name = case + "_" + symbol
        if name not in admitted:
            missing.append(name)
            continue
        frozen = case == "finmem" and symbol == "TSLA"
        run = ROOT / "artifacts/publication_upgrade_v1/finmem_native" if frozen else PRIVATE / name
        recipe_path = (
            ROOT / "paper_runs/publication_upgrade_v1/finmem_recipe.json"
            if frozen
            else PUBLIC / "recipes" / (name + ".json")
        )
        if name in overrides:
            run = PRIVATE / overrides[name]["run_directory"]
            recipe_path = ROOT / overrides[name]["recipe"]
        completion_path = run / "completion.json"
        if not completion_path.exists() or read(completion_path)["status"] != "complete":
            missing.append(name)
            continue
        recipe, completion = read(recipe_path), read(completion_path)
        input_path = (
            ROOT / "artifacts/publication_upgrade_v1/finmem_inputs.json" if frozen else Path(recipe["input_file"])
        )
        if sha256(recipe_path) != completion["recipe_sha256"] or sha256(input_path) != completion["input_sha256"]:
            raise ValueError(name + ": input or recipe no longer matches completion")
        records_path = run / ("decisions.json" if case == "tradingagents" else "decisions.jsonl")
        records = read(records_path)
        hash_key = "decisions_sha256" if case == "tradingagents" else "decision_sha256"
        if hash_key in completion and sha256(records_path) != completion[hash_key]:
            raise ValueError(name + ": decisions changed after completion")
        raw = read(input_path)
        price = pd.DataFrame(raw["rows" if case == "finmem" else "prices"]).set_index("date").adjusted_close
        if price.index.has_duplicates or not price.index.is_monotonic_increasing:
            raise ValueError(name + ": duplicate or unordered prices")
        if case == "finmem":
            selected = [r for r in records if r["mode"] == "Test" and r["arm"] == "native"]
            start, end = recipe["test_start"], recipe["test_end"]
            expected = price.loc[(price.index >= start) & (price.index < end)].index.tolist()
            for row in records:
                latest = row["latest_external_input_date"]
                if latest is not None and latest > row["date"]:
                    raise ValueError(name + ": future text")
            actions = {r["date"]: {1: "BUY", 0: "HOLD", -1: "SELL"}[r["direction"]] for r in selected}
        elif case == "tradingagents":
            selected = records
            start, end = recipe["start"], recipe["end"]
            expected = price.loc[(price.index >= start) & (price.index <= end)].index.tolist()
            for row in records:
                for tool in row["tool_trace"]:
                    if tool["driver_cutoff"] != row["date"] or tool["effective_cutoff"] > row["date"]:
                        raise ValueError(name + ": future tool cutoff")
                    if tool.get("latest_input_date") and tool["latest_input_date"] > tool["effective_cutoff"]:
                        raise ValueError(name + ": future tool input")
            actions = {r["date"]: r["native"] for r in selected}
        else:
            selected = [r for r in records if r["arm"] == "native_causal"]
            start, end = recipe["test_start"], recipe["test_end"]
            expected = price.loc[(price.index >= start) & (price.index < end)].index.tolist()
            for row in selected:
                if row["latest_price_in_state"] > row["date"] or (
                    row["latest_news_available_date"] and row["latest_news_available_date"] > row["date"]
                ):
                    raise ValueError(name + ": future validation input")
            actions = {r["date"]: r["decision"] or "HOLD" for r in selected}
            if not selected[-1]["terminal_valuation"]:
                raise ValueError(name + ": missing terminal valuation")
        if [r["date"] for r in selected] != expected:
            raise ValueError(name + ": incomplete, duplicated or reordered decision calendar")
        dates = price.loc[(price.index >= start) & (price.index <= end)].index
        prices = price.loc[dates].to_numpy(float)
        # Only the declared terminal valuation day may lack an actor action.
        action_list = [actions.get(day, "HOLD") for day in dates]
        realized = price.pct_change(fill_method=None).loc[dates].to_numpy()[:, None]
        path_rows, max_error = [], 0.0
        for arm, action_sequence in [
            ("native", action_list),
            ("buy_hold_matched_clock", ["BUY"] + ["HOLD"] * (len(dates) - 1)),
        ]:
            for lag in [0, 1]:
                for cost in [0, 10, 25, 50]:
                    if case == "finagent":
                        values, turnover = whole_account(action_sequence, prices, cost, lag)
                        if arm == "native" and lag == 1 and cost == 10:
                            error = float(np.max(np.abs(values - np.array([r["realized_return"] for r in selected]))))
                            max_error = max(max_error, error)
                            if error > 1e-12:
                                raise ValueError(name + ": native whole-share account mismatch")
                    else:
                        values, turnover, fees = cash_account(categorical_targets(action_sequence, lag), realized, cost)
                        independent = binary_share_account(action_sequence, prices, cost, lag)
                        error = float(np.max(np.abs(independent[:, :3] - np.stack([values, turnover, fees], axis=1))))
                        max_error = max(max_error, error)
                        if error > 1e-12:
                            raise ValueError(name + ": independent account mismatch")
                    clock = "next_close" if lag else "same_close_infeasible_diagnostic"
                    performance.append(
                        {
                            "case": case,
                            "symbol": symbol,
                            "arm": arm,
                            "clock": clock,
                            "cost_bps": cost,
                            **metrics(series(dates, values)),
                        }
                    )
                    for day, value, turn in zip(dates, values, turnover):
                        path_rows.append(
                            {
                                "date": day,
                                "arm": arm,
                                "clock": clock,
                                "cost_bps": cost,
                                "return": float(value),
                                "traded_notional": float(turn),
                            }
                        )
                    if lag == 1 and cost == 10:
                        paths[(case, symbol, arm)] = series(dates, values)
        pd.DataFrame(path_rows).to_parquet(private_out / (name + "_daily_accounts.parquet"), index=False)
        if case == "finmem":
            value = sum(
                r["direction"] * np.log(price.iloc[price.index.get_loc(r["date"]) + 1] / price.loc[r["date"]])
                for r in selected
            )
            source_scores.append(
                {
                    "case": case,
                    "symbol": symbol,
                    "signed_log_return_sum": float(value),
                    "scored_decisions": len(selected),
                    "label": "Source score, not a self-financing portfolio return",
                }
            )
        replay_path = (
            ROOT / "artifacts/publication_upgrade_v1/finmem_full_replay_validation.json"
            if frozen
            else PRIVATE / (run.name + "_full_replay_validation.json")
        )
        checks.append(
            {
                "case": case,
                "symbol": symbol,
                "decisions": len(selected),
                "valuation_days": len(dates),
                "completed_training_and_test_records": len(records),
                "maximum_independent_account_error": max_error,
                "causal_input_dates_pass": True,
                "replay_status": read(replay_path)["status"] if replay_path.exists() else "pending",
                "recipe_sha256": sha256(recipe_path),
                "decisions_sha256": sha256(records_path),
                "input_sha256": sha256(input_path),
                "frozen_v1_trajectory": frozen,
                "source_replay_evidence": admitted[name],
            }
        )
    aggregates = []
    for case in ["finmem", "tradingagents", "finagent"]:
        symbols = [symbol for candidate, symbol in runs if candidate == case]
        if any((case, symbol, "native") not in paths for symbol in symbols):
            continue
        for arm in ["native", "buy_hold_matched_clock"]:
            matrix = pd.concat([paths[(case, symbol, arm)].rename(symbol) for symbol in symbols], axis=1)
            if matrix.isna().any().any():
                raise ValueError(case + ": account calendars differ; no implicit dropna or filling")
            combined = series(matrix.index, equal_initial_capital(matrix.to_numpy()))
            pd.DataFrame({"date": combined.index, "return": combined.values}).to_parquet(
                private_out / (case + "_" + arm + "_aggregate.parquet"), index=False
            )
            aggregates.append(
                {
                    "case": case,
                    "arm": arm,
                    "assets": symbols,
                    "weight_rule": "Equal initial capital in independent accounts; no daily cross-account rebalancing",
                    "clock": "next_close",
                    "cost_bps": 10,
                    **metrics(combined),
                }
            )
    atomic_json(
        out / "validation.json",
        {
            "status": "partial" if missing else "pass",
            "completed_runs": checks,
            "missing_runs": missing,
            "claim": "Execution-clock and account validation; full-paper replication and independent human review are not established",
            "script_sha256": sha256(Path(__file__)),
            "source_gate_sha256": sha256(ROOT / 'scripts/fidelity_equity_evidence_v3.py'),
            "private_account_outputs": {str(p.relative_to(ROOT)): sha256(p) for p in sorted(private_out.glob('*.parquet'))},
            "primary_run_overrides_sha256": sha256(PUBLIC / 'primary_run_overrides.json') if overrides else None,
        },
    )
    atomic_json(out / "performance.json", performance)
    atomic_json(out / "aggregate_performance.json", aggregates)
    atomic_json(out / "finmem_source_scores.json", source_scores)
    validation = read(out / 'validation.json')
    validation['public_outputs'] = {p.name: sha256(p) for p in out.glob('*.json') if p.name != 'validation.json'}
    atomic_json(out / 'validation.json', validation)
    print(
        json.dumps(
            {
                "completed": len(checks),
                "missing": missing,
                "aggregate_cases": sorted({row["case"] for row in aggregates}),
                "maximum_account_error": max((r["maximum_independent_account_error"] for r in checks), default=None),
            }
        )
    )
    if missing and not args.allow_partial:
        raise SystemExit("Incomplete runs; final account analysis not closed")


if __name__ == "__main__":
    main()
