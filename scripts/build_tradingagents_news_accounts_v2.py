#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Separate replay-gated original/repaired TA accounts, with no new model call."""

from pathlib import Path
import argparse
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_economics import cash_account, categorical_targets
from alpha_evolve.fidelity_accounts_v2 import binary_share_account, equal_initial_capital
from analyze_publication_upgrade import metrics, series

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def require_calendar_and_cutoffs(records, price, start, end):
    expected = price.loc[(price.index >= start) & (price.index <= end)].index.tolist()
    if (
        price.index.has_duplicates
        or not price.index.is_monotonic_increasing
        or [r["date"] for r in records] != expected
    ):
        raise ValueError("Incomplete, duplicate or reordered decision/price calendar")
    for row in records:
        if row["native"] not in ("BUY", "SELL", "HOLD"):
            raise ValueError("Invalid categorical source action")
        for tool in row["tool_trace"]:
            if tool["driver_cutoff"] != row["date"] or tool["effective_cutoff"] > row["date"]:
                raise ValueError("Future tool cutoff")
            if tool.get("latest_input_date") and tool["latest_input_date"] > tool["effective_cutoff"]:
                raise ValueError("Future tool input")
    return expected


def load_run(name, recipe_path):
    run = PRIVATE / name
    done_path = run / "completion.json"
    done = json.loads(done_path.read_text())
    recipe = json.loads(recipe_path.read_text())
    input_path = Path(recipe["input_file"])
    decisions = run / "decisions.json"
    replay_path = PRIVATE / (name + "_full_replay_validation.json")
    replay = json.loads(replay_path.read_text())
    if done["status"] != "complete" or replay["status"] != "pass" or replay["original"] != name:
        raise ValueError("Source completion/full replay gate failed")
    for path, key in [(recipe_path, "recipe_sha256"), (input_path, "input_sha256"), (decisions, "decisions_sha256")]:
        if sha256(path) != done[key]:
            raise ValueError("Completed source artifacts changed")
    if replay["original_sha256"] != sha256(decisions) or replay["recipe_sha256"] != sha256(recipe_path):
        raise ValueError("Replay no longer binds the source")
    if sha256(PRIVATE / replay["replay"] / "decisions.json") != replay["replay_sha256"]:
        raise ValueError("Exact replay decisions changed")
    if any(r["status"] != "pass" for r in replay.get("transport_prefix_validation", [])):
        raise ValueError("Preserved transport prefix mismatch")
    records = json.loads(decisions.read_text())
    raw = json.loads(input_path.read_text())
    price = pd.DataFrame(raw["prices"]).set_index("date").adjusted_close
    dates = require_calendar_and_cutoffs(records, price, recipe["start"], recipe["end"])
    if len(records) != 61 or replay["records"] != 61 or replay["replay_records"] != 61:
        raise ValueError("The complete planned quarter is required")
    return {
        "name": name,
        "recipe": recipe,
        "prices": price.loc[dates],
        "records": records,
        "actions": [r["native"] for r in records],
        "proof": {
            "run": name,
            "completion_sha256": sha256(done_path),
            "recipe_sha256": sha256(recipe_path),
            "input_sha256": sha256(input_path),
            "decisions_sha256": sha256(decisions),
            "full_replay_sha256": sha256(replay_path),
            "preserved_prefixes": replay.get("transport_prefix_validation", []),
            "records": len(records),
        },
    }


def require_pair(original, repaired):
    fields = [
        "source_commit",
        "symbol",
        "start",
        "end",
        "model",
        "temperature",
        "max_completion_tokens",
        "economic_adapter",
        "controls",
    ]
    if any(original["recipe"][k] != repaired["recipe"][k] for k in fields):
        raise ValueError("Policy pair differs in prespecified non-news settings")
    pd.testing.assert_series_equal(original["prices"], repaired["prices"], check_exact=True)


def main():
    p = argparse.ArgumentParser()
    p.parse_args()
    protocol = PUBLIC / "tradingagents_news_account_protocol.json"
    plan = json.loads(protocol.read_text())
    if plan["required_records"] != 61 or plan["cost_bps"] != [0, 10, 25, 50] or plan["primary_cost_bps"] != 10:
        raise ValueError("Frozen descriptive account specification changed")
    out = PUBLIC / "tradingagents_news_accounts"
    private_out = PRIVATE / "tradingagents_news_accounts"
    if (out / "completion.json").exists():
        raise ValueError("Preserve completed sensitivity accounts")
    bundles = {}
    for name in [plan["original"], plan["repair"], *plan["other_assets_reused"]]:
        recipe = "tradingagents_GOOGL_company_news" if name == plan["repair"] else name
        bundles[name] = load_run(name, PUBLIC / "recipes" / (recipe + ".json"))
    wrapper_path = PRIVATE / plan["repair"] / "wrapper.json"
    wrapper = json.loads(wrapper_path.read_text())
    if wrapper.get("news_source_policy") != "single_frozen_company_corpus":
        raise ValueError("Unexpected repaired news-source policy")
    bundles[plan["repair"]]["proof"]["news_wrapper_sha256"] = sha256(wrapper_path)
    require_pair(bundles[plan["original"]], bundles[plan["repair"]])
    dates = bundles[plan["original"]]["prices"].index
    if any(not b["prices"].index.equals(dates) for b in bundles.values()):
        raise ValueError("Aggregate accounts must share the exact whole calendar")
    rows = []
    performance = []
    values = {}
    maximum = 0.0
    for name, bundle in bundles.items():
        price = bundle["prices"].to_numpy(float)
        realized = np.r_[0, price[1:] / price[:-1] - 1][:, None]
        for lag, clock in [(1, "next_close"), (0, "same_close_infeasible_diagnostic")]:
            for fee in plan["cost_bps"]:
                for arm, actions in [
                    ("native", bundle["actions"]),
                    ("buy_hold_matched_clock", ["BUY"] + ["HOLD"] * (len(price) - 1)),
                ]:
                    independent = binary_share_account(actions, price, fee, lag)
                    canonical = np.stack(cash_account(categorical_targets(actions, lag), realized, fee), axis=1)
                    error = float(np.max(np.abs(independent[:, :3] - canonical)))
                    if error > 1e-12:
                        raise ValueError("Independent share/cash account differs from target-weight account")
                    maximum = max(maximum, error)
                    net = independent[:, 0]
                    values[(name, arm, clock, fee)] = net
                    performance.append(
                        {
                            "run": name,
                            "arm": arm,
                            "clock": clock,
                            "cost_bps": fee,
                            **metrics(series(dates, net), frequency=252),
                        }
                    )
                    for day, x in zip(dates, independent):
                        rows.append(
                            {
                                "date": day,
                                "run": name,
                                "arm": arm,
                                "clock": clock,
                                "cost_bps": fee,
                                "net_return": x[0],
                                "turnover": x[1],
                                "fee_fraction": x[2],
                                "wealth": x[3],
                                "cash": x[4],
                                "shares": x[5],
                            }
                        )
    contrasts = []
    aggregates = []
    for lag, clock in [(1, "next_close"), (0, "same_close_infeasible_diagnostic")]:
        for fee in plan["cost_bps"]:
            for cohort, google in [
                ("original_three_equity", plan["original"]),
                ("repaired_news_three_equity", plan["repair"]),
            ]:
                names = [*plan["other_assets_reused"], google]
                net = equal_initial_capital(np.stack([values[(n, "native", clock, fee)] for n in names], axis=1))
                values[(cohort, "native", clock, fee)] = net
                aggregates.append(
                    {
                        "cohort": cohort,
                        "assets": names,
                        "clock": clock,
                        "cost_bps": fee,
                        "weighting": "Equal initial capital; no daily cross-account rebalancing",
                        **metrics(series(dates, net), frequency=252),
                    }
                )
                for day, value in zip(dates, net):
                    rows.append(
                        {
                            "date": day,
                            "run": cohort,
                            "arm": "native",
                            "clock": clock,
                            "cost_bps": fee,
                            "net_return": value,
                        }
                    )
            for label, left, right, rarm in [
                ("repaired_minus_original_GOOGL", plan["repair"], plan["original"], "native"),
                ("repaired_minus_matched_buy_hold", plan["repair"], plan["repair"], "buy_hold_matched_clock"),
                (
                    "three_equity_news_sensitivity_minus_original",
                    "repaired_news_three_equity",
                    "original_three_equity",
                    "native",
                ),
            ]:
                a = values[(left, "native", clock, fee)]
                b = values[(right, rarm, clock, fee)]
                contrasts.append(
                    {
                        "contrast": label,
                        "clock": clock,
                        "cost_bps": fee,
                        "sessions": len(dates),
                        "left_ending_wealth": float(np.prod(1 + a)),
                        "right_ending_wealth": float(np.prod(1 + b)),
                        "cumulative_return_difference": float(np.prod(1 + a) - np.prod(1 + b)),
                        "daily_mean_net_return_difference": float(np.mean(a - b)),
                        "statistical_significance_not_established": True,
                    }
                )
    # Bind the original aggregate to the already published preview. Do not
    # rewrite or select a baseline based on the repaired outcome.
    prior = pd.read_parquet(PRIVATE / "account_preview/tradingagents_native_aggregate.parquet")
    if list(pd.to_datetime(prior.date)) != list(pd.to_datetime(dates)) or not np.allclose(
        prior["return"], values[("original_three_equity", "native", "next_close", 10)], atol=1e-12, rtol=0
    ):
        raise ValueError("Original aggregate differs from the frozen comparison baseline")
    out.mkdir(exist_ok=True)
    private_out.mkdir(exist_ok=True)
    accounts = private_out / "daily_accounts.parquet"
    pd.DataFrame(rows).to_parquet(accounts, index=False)
    for name, data in [("performance", performance), ("aggregate_performance", aggregates), ("comparisons", contrasts)]:
        atomic_json(out / (name + ".json"), data)
    atomic_json(
        out / "completion.json",
        {
            "status": "complete_separate_descriptive_sensitivity",
            "scope": plan["role"],
            "records_per_source": 61,
            "maximum_independent_account_difference": maximum,
            "paired_input_price_series_identical": True,
            "original_three_equity_baseline_matches_previous_export": True,
            "full_replay_and_prefixes_required": True,
            "source_evidence": [b["proof"] for b in bundles.values()],
            "protocol_sha256": sha256(protocol),
            "accounts_sha256": sha256(accounts),
            "script_sha256": sha256(Path(__file__)),
            "new_model_calls": 0,
            "JKP132_attribution": False,
            "significant_alpha_established": False,
            "full_original_paper_reproduced": False,
            "model_trajectories_per_policy": 1,
            "outputs": {p.name: sha256(p) for p in out.iterdir() if p.is_file()},
        },
    )
    print("TA_NEWS_SEPARATE_ACCOUNTS_PASS", len(dates), maximum, flush=True)


if __name__ == "__main__":
    main()
