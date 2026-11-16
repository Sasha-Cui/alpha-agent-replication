#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Explain the complete news sensitivity, including a constant-action result."""

from pathlib import Path
from collections import Counter
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def read(path):
    return json.loads(path.read_text())


def main():
    source = PUBLIC / "tradingagents_news_accounts"
    done = read(source / "completion.json")
    if done["status"] != "complete_separate_descriptive_sensitivity":
        raise ValueError("Complete accounts required")
    for name, digest in done["outputs"].items():
        if sha256(source / name) != digest:
            raise ValueError("Completed account statistics changed")
    path = PRIVATE / "tradingagents_news_accounts/daily_accounts.parquet"
    if sha256(path) != done["accounts_sha256"]:
        raise ValueError("Private account changed")
    frame = pd.read_parquet(path)
    records = {}
    inputs = {}
    for name, recipe in [
        ("tradingagents_GOOGL", "tradingagents_GOOGL"),
        ("tradingagents_GOOGL_single_news_source", "tradingagents_GOOGL_company_news"),
    ]:
        item = next(r for r in done["source_evidence"] if r["run"] == name)
        p = PRIVATE / name / "decisions.json"
        if sha256(p) != item["decisions_sha256"]:
            raise ValueError("Completed decisions changed")
        records[name] = read(p)
        recipe_path = PUBLIC / "recipes" / (recipe + ".json")
        r = read(recipe_path)
        if sha256(recipe_path) != item["recipe_sha256"] or sha256(Path(r["input_file"])) != item["input_sha256"]:
            raise ValueError("Completed recipe/input identity changed")
        inputs[name] = read(Path(r["input_file"]))
    original, repaired = [records[n] for n in ("tradingagents_GOOGL", "tradingagents_GOOGL_single_news_source")]
    if [r["date"] for r in original] != [r["date"] for r in repaired] or len(original) != 61:
        raise ValueError("Decision dates changed")
    same_paths = []
    for clock in ["next_close", "same_close_infeasible_diagnostic"]:
        for cost in [0, 10, 25, 50]:
            values = []
            for name, arm in [
                ("tradingagents_GOOGL", "native"),
                ("tradingagents_GOOGL_single_news_source", "native"),
                ("tradingagents_GOOGL_single_news_source", "buy_hold_matched_clock"),
            ]:
                selected = frame.loc[
                    (frame.run == name) & (frame.arm == arm) & (frame.clock == clock) & (frame.cost_bps == cost)
                ].sort_values("date")
                if len(selected) != 61:
                    raise ValueError("Incomplete account comparison")
                values.append(
                    selected[["net_return", "turnover", "fee_fraction", "wealth", "cash", "shares"]].to_numpy()
                )
            same_paths.append(
                {
                    "clock": clock,
                    "cost_bps": cost,
                    "original_repaired_buy_hold_paths_identical": all(np.array_equal(values[0], x) for x in values[1:]),
                }
            )
    diagnostics = {
        "actions": {name: dict(Counter(r["native"] for r in rows)) for name, rows in records.items()},
        "changed_reports": {
            key: sum(a["reports"][key] != b["reports"][key] for a, b in zip(original, repaired))
            for key in original[0]["reports"]
        },
        "input_items": {n: len(v["items"]) for n, v in inputs.items()},
        "input_prices": {n: len(v["prices"]) for n, v in inputs.items()},
        "account_path_checks": same_paths,
        "new_model_calls": 0,
        "one_trajectory_per_policy": True,
    }
    if diagnostics["actions"] != {name: {"BUY": 61} for name in records}:
        raise ValueError("Narrative constant-BUY count differs from source")
    if diagnostics["changed_reports"] != {
        "news_report": 61,
        "market_report": 0,
        "fundamentals_report": 0,
        "sentiment_report": 0,
    }:
        raise ValueError("Narrative report-change counts differ from source")
    if diagnostics["input_items"] != {"tradingagents_GOOGL": 88, "tradingagents_GOOGL_single_news_source": 10117}:
        raise ValueError("Narrative corpus counts differ from source")
    if inputs["tradingagents_GOOGL"]["prices"] != inputs["tradingagents_GOOGL_single_news_source"]["prices"]:
        raise ValueError("Complete373price-row identity changed")
    if not all(r["original_repaired_buy_hold_paths_identical"] for r in same_paths):
        raise ValueError("Expected constant-BUY interpretation fails full-path check")
    rows = read(source / "comparisons.json")
    out = PUBLIC / "tradingagents_news_report"
    out.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "comparisons_full_audit.csv", index=False)
    atomic_json(out / "policy_diagnostics.json", diagnostics)
    table = []
    for cost in [0, 10, 25, 50]:
        x = next(
            r
            for r in rows
            if r["clock"] == "next_close" and r["cost_bps"] == cost and r["contrast"] == "repaired_minus_original_GOOGL"
        )
        y = next(
            r
            for r in rows
            if r["clock"] == "next_close"
            and r["cost_bps"] == cost
            and r["contrast"] == "repaired_minus_matched_buy_hold"
        )
        table.append(
            f"| {cost} | {100 * (x['right_ending_wealth'] - 1):.3f}% | {100 * (x['left_ending_wealth'] - 1):.3f}% | {100 * (y['right_ending_wealth'] - 1):.3f}% | {100 * x['cumulative_return_difference']:+.3f}pp |"
        )
    primary = next(
        r
        for r in rows
        if r["clock"] == "next_close"
        and r["cost_bps"] == 10
        and r["contrast"] == "three_equity_news_sensitivity_minus_original"
    )
    text = [
        "# TradingAgents Alphabet-news repair — completed descriptive sensitivity",
        "",
        "The larger issuer-news corpus changes every daily news report but leaves the portfolio unchanged. Both original and repaired runs issue **BUY on all 61 days**. Under the declared long-only cash/share account, repeated BUY instructions retain the fully invested position. Original, repaired and matched buy-and-hold paths are identical, including fees, wealth and shares, at every tested cost and clock. This is a completed null realized comparison, not evidence that news can never help.",
        "",
        "## Same complete quarter and economic settings",
        "",
        "| One-way fee, bp | Original GOOGL | Repaired GOOGL | Matched buy-and-hold | Repair minus original |",
        "|---|---|---|---|---|",
        *table,
        "",
        "[Full audit table, including same-close diagnostics and the three-equity sensitivity](comparisons_full_audit.csv). Returns are cumulative for January 2–March 28, 2024, with next-close fills. Same-close results are infeasible diagnostics. No terminal forced liquidation is imposed.",
        "",
        f"The separate three-equity sensitivity retains the exact AAPL and AMZN accounts and changes only the GOOGL policy realization. Equal initial capital then drifts without daily rebalancing. At 10bp it returns {100 * (primary['left_ending_wealth'] - 1):.3f}%, identical to the original three-equity account. The original published result was not overwritten.",
        "",
        "## Evidence and limitations",
        "",
        "- The input corpus expands from 88 to 10,117 items, while all 373 price rows are preserved. The additional 10,029 news items use the verified issuer mapping. One complete company-news source is supplied; independent feeds are honestly unavailable. No article is truncated.",
        "- All 61 news reports change. Fundamentals, market and sentiment reports remain identical. This confirms that the news repair was active even though the categorical trading actions stay BUY.",
        "- Full cached replay matches all 61 records with zero differences, including the 23- and 27-record interruption prefixes. No new API call is made by replay or accounting.",
        "- The independent cash/share reconstruction matches the target-weight account within 5.56e-16. [Policy diagnostics](policy_diagnostics.json) verify every fee/clock path.",
        "- Current model/data snapshots, empty source experience banks, categorical sizing and a single issuer/quarter limit the inference. This is not a causal treatment-effect estimate over repeated LLM trajectories, a significant-alpha result, JKP132 attribution, or full-paper reproduction. The earlier failed five-day duplicated-feed variant remains separate.",
        "",
        "[Account validation](../tradingagents_news_accounts/completion.json) · [Fixed descriptive protocol](../tradingagents_news_account_protocol.json) · [Source review](../SOURCE_REVIEW_PACKET.md) · [Report validation](validation.json)",
        "",
        "Rebuild on Bouchet from the canonical checkout:",
        "",
        "```bash",
        "/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python scripts/build_tradingagents_news_report_v2.py",
        "```",
        "",
    ]
    (out / "REPORT.md").write_text("\n".join(text))
    atomic_json(
        out / "validation.json",
        {
            "status": "pass",
            "complete_account_sha256": sha256(source / "completion.json"),
            "all8_fee_clock_combinations_full_path_equal": True,
            "rows_per_path": 61,
            "builder_sha256": sha256(Path(__file__)),
            "no_statistical_significance_claim": True,
            "new_model_calls": 0,
            "outputs": {p.name: sha256(p) for p in out.iterdir() if p.is_file() and p.name != "validation.json"},
        },
    )
    print("TA_NEWS_REPORT_FULL_PATH_CHECK_PASS")


if __name__ == "__main__":
    main()
