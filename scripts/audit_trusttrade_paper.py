#!/usr/bin/env python3
"""Build a fail-closed primary-source and deployed-artifact audit for TrustTrade."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/trusttrade_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/trusttrade"
WORK_ID = "CensusArxiv260322567"
SYSTEM_ID = "SYS-TRUST-TRADE"
ARXIV_ID = "2603.22567"

PINS = {
    "primary/official.pdf": "6f9facfe101b3bf0e7ea8a0082bf7f72160e87ef9744c74eb53cf0cda5faaffa",
    "primary/official.txt": "15509d75530d843fae465d05b9ed50eae605dd0dcebf1f0eb74a0fb090190eb8",
    "primary/source.tar": "53bc114b23ce00fc4a043c243c44bea11c0450036c21b93e288ff3a09506b965",
    "primary/rebuilt.pdf": "611b89ac31db287a1dd559adfc28ef5ff237b39fef737faa1fc4240a15015aa4",
    "primary/rebuilt.txt": "1ee5d091be8904ef4372c9c3721ab99a2f21a4161f53f583684f657168585708",
    "primary/arxiv-abs.html": "7437fa025861973ce6239cea30e2dc26b6e54201d8482f20a40b4787536b7b80",
    "primary/arxiv-api.xml": "27112c03a11786b0689f398562a93176fe3da7f34aa2eb27201613b2c3ed487c",
    "source/sn-article.tex": "d12f5e861fa170da387677682df248b9605c5bd38ec11b186a968902c15c8d4c",
    "source/secs/2_results.tex": "7ddcad2b7e60188ff1765693bb9a5b81be1a441667b0b2ec6e098ce89274fd4c",
    "source/secs/5_methods.tex": "a0f4ec2b3187e35a9774dfdee1eb0c9b5be1cbc658b36ccc95e7443ba06086c2",
    "source/secs/6_data_availability.tex": "67339cca8e609e903ea8d67c54dd1913285adc4ca167c4893db546efb10e92be",
    "source/secs/7_code_availability.tex": "c1de8a182113d444093dfd9479b0f30927216cab6fffba2c37c7983fc6dc2d17",
    "source/figs/reasoning_depth.tex": "f7a7317d0331e62317476b5da42cf5f52be18738dd2cf63f8ab99ca2e2529ccd",
    "source/figs/human_analysis.tex": "438f8dd982f4751fb11d384d6f0e5c7e5015c63f5e795ce88216759821158038",
    "source/figs/fig3_main.tex": "5063cbf7550d8caa953e75f63f7413e9082c1b04ed9940d900dc165e6d0e23f6",
    "source/figs/method.tex": "de79a4d71d4682df2e0bce39e9bf71f4e5f98f810c32368070a436ab61ff817d",
    "source/tabs/price_output.tex": "fa9bda61cd61447a567e295e2ada05494cac11b431a4a1d3f61332c4cebfd262",
    "source/tabs/abl.tex": "3235d0b81bc7148f0dc79b5619d67ef65969f55f54fc1809e6a956fef0a61125",
    "discovery/harvard-lab-repos.json": "29dc6667ab5f7d9ff70a226a3b3c9ff44835193cdf219599d50f1f09121981fd",
    "discovery/github-org-repo-search.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-org-code-arxiv-search.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-global-code-name-search.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-global-code-netlify-search.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-global-title-repo-search.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/netlify-aapl.html": "675419373ac5c161feeee0acc4a6545f2fd33fc23efeb8f44b15d8cf542f2a44",
    "discovery/netlify-aapl.js": "2f7bbdee865fc537f399d1d4ac03a36c9e27de7c53c9f7381fe7c5a8bb2ac479",
    "discovery/netlify-aapl.js.map": "1c5dd3c4e46537198380acfb47b38890ed2b17ca60c5783fde4bdd54af410d8d",
    "discovery/netlify-goog.html": "33b4d675133f16088e99c419b0786e4c3da5536ee0d2fd8a8a0346d614de7ca5",
    "discovery/netlify-goog.js": "fc08a53c413bfb5b82bfb91e3888b0f0eae07e4887f62b1b3e3c89e212885c93",
    "discovery/netlify-goog.js.map": "d39a33ae7c9f79b57a52d8ea627cea6931dcef7ea33c0aa339e8017075d15509",
    "discovery/netlify-nvda.html": "8bfbc4310a80aed1cc9193cadbb362a23a25d889ca1477b21c8c448d43a80423",
    "discovery/netlify-nvda.js": "4188151e2785730cd4ec1f5ea10ce2812587eeaa1080f377e3b09549475ad3c6",
    "discovery/netlify-nvda.js.map": "68616c909279471c472fb4dc5d44ffaabb1d8e7f839040571a32d20c4d0b2b53",
    "interface_data/aapl/gpt_4o_mini_aapl_trading_data_cleaned.json": "8b34a1065aa5f7388bf9997b0aff6fe3beb9888a630d9c191ba8e6436edfa976",
    "interface_data/aapl/gpt_4o_mini_aapl_market_prices.csv": "077600836d4d3707f20b027c8496384e25e1aeb07b6e665169a4de4737a65f51",
    "interface_data/goog/gpt_4o_mini_goog_trading_data_cleaned.json": "152d70a292ac2c0a321a819f809598666f29da6b3c672393a233be18be444fef",
    "interface_data/goog/gpt_4o_mini_goog_market_prices.csv": "489c0c1afd89c3635d7af51141ba4edd01261c57411ccf709d3c3587d27854df",
    "interface_data/nvda/gpt_4o_mini_nvda_trading_data_cleaned.json": "4db0b21d5cb371d424de9754c360f6f05d21ec2efe7b862308fbc60e57081499",
    "interface_data/nvda/gpt_4o_mini_nvda_market_prices.csv": "2584e9a4ae8019e3db572f9625a687211e3677054e5dfd0800eb458cd5584a7e",
    "interface_data/aapl/us_market_indices_Nasdaq.csv": "b93923af20ec5f789c3b1627fa754dc10a7cdb73a7938e32a03d0b4d6291ce64",
    "interface_data/aapl/us_market_indices_Dow.csv": "bbc0dc52bb21a4880d88277ca098407351232fb3f5dd0990b0bfb07f8eac5715",
    "interface_data/aapl/us_market_indices_S_P_500.csv": "0c2d6d31171ee74a9487e49c8445bc64cf5d7a193359263f3b03157902cf360f",
    "interface_source/aapl/HumanTradingDecisionCollectionApp.tsx": "068ab1f2ba1c0a0f145634588c3c52f018ad4c892a2bc135f0d9b3a47ec0961d",
    "interface_source/aapl/lib/dataLoader.ts": "4a8509bf90d0c6ee60b38fed97858d18cab00b734d9dcd20bc567ef81c85de64",
    "interface_source/goog/HumanTradingDecisionCollectionApp.tsx": "d4a1e1cc23deb182854d6c12b76d9be131cd19f90037e112aee697640c183351",
    "interface_source/goog/lib/dataLoader.ts": "c10ff071bff2af0ef429fcad2abc30e859652bf31212932b52e1bb2ca297de29",
    "interface_source/nvda/HumanTradingDecisionCollectionApp.tsx": "5998584cdf1f6e6b06dee3c6c145bdd2534990d372cba521e34fcbf1dcbc0bb0",
    "interface_source/nvda/lib/dataLoader.ts": "5460bad48402240f0ea4edbb017c609900acd84bb17ed11c407e9248fa2879d8",
}

FIGURES = (
    ("figs/figs/v2/tradingagents.pdf", "study1", "a", 1, 0, "pipeline schematic"),
    ("figs/figs/v2/ablation_study_plots_research_trader_risk_mean.pdf", "study1", "b-c", 2, 2, "2024 reasoning-depth ablations"),
    ("figs/figs/v2/performance_with_price_clean2_.png", "study1", "d", 1, 1, "2024 return heterogeneity"),
    ("figs/figs/v2/performance_with_price_clean_mdd2_.png", "study1", "e", 1, 1, "2024 drawdown heterogeneity"),
    ("figs/figs/stock_price/stock_AAPL_price_2.png", "study1", "f", 1, 1, "AAPL 2024 price path"),
    ("figs/figs/stock_price/stock_GOOG_price_2.png", "study1", "g", 1, 1, "GOOG 2024 price path"),
    ("figs/figs/stock_price/stock_NVDA_price_2.png", "study1", "h", 1, 1, "NVDA 2024 price path"),
    ("figs/figs/v2/user_demographics_overview_nature.png", "human_analysis", "a", 1, 1, "participant demographics"),
    ("figs/figs/v2/stock_performance_summary_nature.png", "human_analysis", "b-f", 5, 5, "human performance"),
    ("figs/figs/v2/rank_consistent_selective_weighting.png", "human_analysis", "g", 1, 1, "human information weighting"),
    ("figs/figs/v2/human_factor_combined_score_ranked.png", "human_analysis", "h", 1, 1, "human factor scores"),
    ("figs/figs/v2/consistency_comparison_subplots_v3.png", "human_analysis", "i", 1, 1, "human/LLM convergence"),
    ("figs/figs/v2/trusttrade.pdf", "study3", "a", 1, 0, "TrustTrade schematic"),
    ("figs/figs/v2/consistency_comparison_high_consensus_ci.pdf", "study3", "b", 1, 1, "consensus convergence"),
    ("figs/figs/v2/risk_return_tradeoff_abl.pdf", "study3", "c", 1, 1, "TrustTrade ablation trade-off"),
    ("tabs/price_output.tex", "study3", "d", 1, 1, "temporal-signal example output"),
    ("figs/figs/v2/risk_return_tradeoff.pdf", "main", "a", 1, 1, "2024 CR/MDD"),
    ("figs/figs/v2/sr_return_tradeoff.pdf", "main", "b", 1, 1, "2024 SR/MDD"),
    ("figs/figs/v2/risk_return_tradeoff_2026q1.pdf", "main", "c", 1, 1, "2026 CR/MDD"),
    ("figs/figs/v2/sr_return_tradeoff_2026q1.pdf", "main", "d", 1, 1, "2026 SR/MDD"),
    ("figs/figs/v2/per_stock_AAPL_2026q1.pdf", "main_2026q1", "a", 1, 1, "AAPL real-time path"),
    ("figs/figs/v2/per_stock_GOOG_2026q1.pdf", "main_2026q1", "b", 1, 1, "GOOG real-time path"),
    ("figs/figs/v2/per_stock_NVDA_2026q1.pdf", "main_2026q1", "c", 1, 1, "NVDA real-time path"),
    ("figs/figs/v2/simulation.pdf", "methods_interface", "a", 1, 0, "human interface screenshot"),
    ("figs/figs/v2/trusttrade_consensus.pdf", "methods_modules", "a", 1, 0, "consensus schematic"),
    ("figs/figs/v2/trusttrade_price.pdf", "methods_modules", "b", 1, 0, "temporal module schematic"),
    ("figs/figs/v2/trusttrade_memory.pdf", "methods_modules", "c", 1, 0, "memory schematic"),
)

PRINTED_BASELINE = {
    "AAPL": {"cr": 2.34, "arr": 10.04, "sr": 1.44, "mdd": 1.37},
    "GOOG": {"cr": 6.15, "arr": 27.96, "sr": 2.92, "mdd": 3.20},
    "NVDA": {"cr": 15.64, "arr": 82.29, "sr": 5.86, "mdd": 1.78},
}

FUTURE_FACT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bas of\b[^\n]{0,80}\b20(?:25|26)\b",
        r"\b20(?:25|26)\b[^\n]{0,80}\bas of\b",
        r"\b(?:Q[1-4]\s*(?:FY\s*)?20(?:25|26)|FY\s*20(?:25|26))\b[^\n]{0,180}\b(?:revenue|net income|earnings|eps|market cap|reported|stood|grew|growth|increase|decrease|up|down)\b",
        r"\b(?:revenue|net income|earnings|eps|market cap|reported|stood|grew|growth|increase|decrease|up|down)\b[^\n]{0,180}\b(?:Q[1-4]\s*(?:FY\s*)?20(?:25|26)|FY\s*20(?:25|26))\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*20(?:25|26)\b[^\n]{0,150}\b(?:declin|dropp|rall|surpass|reached|reported|announced|delay|stock|market cap|valuation)\w*\b",
    )
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def token_jaccard(left: str, right: str) -> float:
    a = Counter(re.findall(r"\w+", left.lower()))
    b = Counter(re.findall(r"\w+", right.lower()))
    return sum((a & b).values()) / sum((a | b).values())


def clipped_line(line: str, limit: int = 280) -> str:
    return " ".join(line.split())[:limit]


def verify_pins(scratch: Path) -> None:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise ValueError(f"pin mismatch: {relative}={observed}; expected {expected}")


def figure_rows(scratch: Path) -> list[dict[str, Any]]:
    rows = []
    for asset, figure, panel_ids, panels, empirical_panels, description in FIGURES:
        path = scratch / "source" / asset
        related_price_input = figure == "study1" and panel_ids in {"f", "g", "h"}
        rows.append(
            {
                "figure": figure,
                "panel_ids": panel_ids,
                "active_panels": panels,
                "empirical_panels": empirical_panels,
                "description": description,
                "source_asset": asset,
                "source_asset_sha256": sha256(path),
                "source_asset_recovered": True,
                "related_deployed_price_input_recovered": related_price_input,
                "raw_result_array_recovered": False,
                "author_native_regeneration": False,
                "paper_result_credit": False,
            }
        )
    if sum(row["active_panels"] for row in rows) != 32:
        raise ValueError("active panel denominator changed")
    if sum(row["empirical_panels"] for row in rows) != 26:
        raise ValueError("empirical panel denominator changed")
    return rows


def result_rows() -> list[dict[str, Any]]:
    panels = {
        "study1": tuple("bcdefgh"),
        "human_analysis": tuple("abcdefghi"),
        "study3": tuple("bcd"),
        "main": tuple("abcd"),
        "main_2026q1": tuple("abc"),
    }
    rows = []
    for figure, labels in panels.items():
        for panel in labels:
            rows.append(
                {
                    "figure": figure,
                    "panel": panel,
                    "source_panel_recovered": True,
                    "raw_result_array_recovered": False,
                    "author_native_pipeline_executed": False,
                    "author_native_panel_regenerated": False,
                    "paper_result_credit": False,
                    "blocking_reason": (
                        "no public TrustTrade implementation, exact model calls/settings, participant outputs, "
                        "2026 traces, decisions, fills, portfolio paths, baseline outputs, or raw plot arrays"
                    ),
                }
            )
    if len(rows) != 26:
        raise ValueError("result-panel denominator changed")
    return rows


def load_data(scratch: Path, ticker: str) -> tuple[dict[str, Any], dict[str, float]]:
    lower = ticker.lower()
    root = scratch / "interface_data" / lower
    records = json.loads((root / f"gpt_4o_mini_{lower}_trading_data_cleaned.json").read_text())
    with (root / f"gpt_4o_mini_{lower}_market_prices.csv").open(newline="", encoding="utf-8") as stream:
        prices = {row["Date"]: float(row["Close"]) for row in csv.DictReader(stream)}
    return records, prices


def replay(records: dict[str, Any], raw_prices: dict[str, float], *, loader_rounding: bool, include_v0_return: bool) -> dict[str, Any]:
    cash = 10_000.0
    shares = 0
    values: list[float] = []
    actions = Counter()
    for date, record in sorted(records.items()):
        price = round(raw_prices[date], 2) if loader_rounding else raw_prices[date]
        decision = record["final_trade_decision_processed"]
        action = decision["action"]
        percentage = float(decision["percentage"])
        if action not in {"BUY", "SELL", "HOLD"} or not 0 <= percentage <= 100:
            raise ValueError(f"unexpected deployed decision: {date} {decision}")
        actions[action] += 1
        if action == "BUY" and price > 0 and cash >= price:
            quantity = math.floor((cash * percentage / 100) / price)
            shares += quantity
            cash -= quantity * price
        elif action == "SELL" and shares > 0 and price > 0:
            quantity = math.floor(shares * percentage / 100)
            shares -= quantity
            cash += quantity * price
        values.append(cash + shares * price)
    return_values = ([10_000.0] + values) if include_v0_return else values
    returns = [return_values[index] / return_values[index - 1] - 1 for index in range(1, len(return_values))]
    peak = 10_000.0
    mdd = 0.0
    for value in values:
        peak = max(peak, value)
        mdd = max(mdd, (peak - value) / peak * 100)
    metrics = {
        "cr": (values[-1] / 10_000 - 1) * 100,
        "arr": ((values[-1] / 10_000) ** (252 / len(values)) - 1) * 100,
        "sr": statistics.mean(returns) / statistics.stdev(returns) * math.sqrt(252),
        "mdd": mdd,
    }
    return {"metrics": metrics, "final_value": values[-1], "actions": actions}


def replay_rows(scratch: Path) -> list[dict[str, Any]]:
    variants = (
        ("paper_literal_production_loader", True, True, "production loader cents; V0-to-first-day return included per printed V0..VT notation"),
        ("common_post_day_production_loader", True, False, "production loader cents; returns begin between consecutive displayed day-end values"),
        ("raw_csv_sensitivity", False, False, "unrounded CSV closes; returns begin between consecutive displayed day-end values"),
    )
    rows = []
    for ticker in PRINTED_BASELINE:
        records, prices = load_data(scratch, ticker)
        if len(records) != 61 or min(records) != "2024-01-02" or max(records) != "2024-03-28":
            raise ValueError(f"deployed record window changed: {ticker}")
        for variant, rounding, include_v0, note in variants:
            execution = replay(records, prices, loader_rounding=rounding, include_v0_return=include_v0)
            for metric, printed in PRINTED_BASELINE[ticker].items():
                computed = execution["metrics"][metric]
                rows.append(
                    {
                        "ticker": ticker,
                        "variant": variant,
                        "metric": metric,
                        "inactive_source_table_value": f"{printed:.2f}",
                        "computed_value": f"{computed:.12f}",
                        "computed_display_2dp": f"{computed:.2f}",
                        "matches_printed_precision": f"{computed:.2f}" == f"{printed:.2f}",
                        "final_value": f"{execution['final_value']:.12f}",
                        "buy_days": execution["actions"]["BUY"],
                        "sell_days": execution["actions"]["SELL"],
                        "hold_days": execution["actions"]["HOLD"],
                        "baseline_percentages_follow_human_widget_choices": False,
                        "variant_note": note,
                        "table_active_in_published_pdf": False,
                        "trusttrade_result_credit": False,
                        "evidence_class": "paper_linked_interface_baseline_component_sensitivity",
                    }
                )
    counts = Counter(row["variant"] for row in rows if row["matches_printed_precision"])
    expected = {"paper_literal_production_loader": 1, "common_post_day_production_loader": 3, "raw_csv_sensitivity": 7}
    if counts != Counter(expected):
        raise ValueError(f"baseline replay anchors changed: {counts}")
    return rows


def interface_rows(scratch: Path) -> list[dict[str, Any]]:
    rows = []
    for ticker in ("AAPL", "GOOG", "NVDA"):
        lower = ticker.lower()
        map_path = scratch / "discovery" / f"netlify-{lower}.js.map"
        source_map = json.loads(map_path.read_text())
        records, _ = load_data(scratch, ticker)
        first = next(iter(records.values()))
        expected_fields = {
            "company_of_interest", "trade_date", "fundamentals_report", "market_report", "news_report",
            "sentiment_report", "portfolio_summary", "fundamentals_analyst_state", "market_analyst_state",
            "news_analyst_state", "sentiment_analyst_state", "investment_debate_state",
            "trader_investment_decision", "final_trade_decision", "final_trade_decision_processed",
        }
        if set(first) != expected_fields:
            raise ValueError(f"deployed schema changed: {ticker}")
        rows.append(
            {
                "ticker": ticker,
                "paper_linked_url": f"https://tradingagents-human-{lower}.netlify.app/",
                "html_sha256": sha256(scratch / "discovery" / f"netlify-{lower}.html"),
                "production_bundle_sha256": sha256(scratch / "discovery" / f"netlify-{lower}.js"),
                "source_map_sha256": sha256(map_path),
                "source_map_entries": len(source_map["sources"]),
                "source_contents_present": sum(value is not None for value in source_map["sourcesContent"]),
                "trading_days": len(records),
                "first_date": min(records),
                "last_date": max(records),
                "input_fields": len(expected_fields),
                "human_interface_source_recovered": True,
                "human_interface_protocol_executable": True,
                "trusttrade_pipeline_source_recovered": False,
                "participant_output_recovered": False,
                "private_participant_endpoint_probed": False,
                "native_trusttrade_result_credit": False,
            }
        )
    return rows


def protocol_rows() -> list[dict[str, Any]]:
    stages = (
        ("d0", "price and indices", False, False),
        ("d1", "fundamentals", True, False),
        ("d2", "market/technical", True, False),
        ("d3", "news", True, False),
        ("d4", "sentiment", True, False),
        ("final", "aggregate and execute", False, True),
    )
    return [
        {
            "stage": stage,
            "information": information,
            "action_required": True,
            "reliability_1_to_100_required": True,
            "rationale_recorded": True,
            "ai_decision_visibility_flag_recorded": leakage,
            "most_influential_and_reliable_recorded": final,
            "trade_percentage_recorded": final,
            "execution_rule": "BUY=floor(cash*pct/close); SELL=floor(shares*pct); HOLD=no trade" if final else "none",
            "production_source_recovered": True,
        }
        for stage, information, leakage, final in stages
    ]


def contamination_rows(scratch: Path) -> list[dict[str, Any]]:
    rows = []
    fields = ("fundamentals_report", "market_report", "news_report", "sentiment_report")
    for ticker in ("AAPL", "GOOG", "NVDA"):
        records, _ = load_data(scratch, ticker)
        for date, record in sorted(records.items()):
            for field in fields:
                text = record.get(field) or ""
                future_lines = []
                future_years = set()
                for line in text.splitlines():
                    years = {int(year) for year in re.findall(r"(?<!\d)(20\d{2})(?!\d)", line)}
                    years = {year for year in years if year > int(date[:4])}
                    if years:
                        future_lines.append(line)
                        future_years.update(years)
                if not future_lines:
                    continue
                candidate = any(any(pattern.search(line) for pattern in FUTURE_FACT_PATTERNS) for line in future_lines)
                example = next(
                    (line for line in future_lines if candidate and any(pattern.search(line) for pattern in FUTURE_FACT_PATTERNS)),
                    future_lines[0],
                )
                rows.append(
                    {
                        "ticker": ticker,
                        "nominal_trade_date": date,
                        "displayed_report_field": field,
                        "future_years": ";".join(map(str, sorted(future_years))),
                        "future_year_line_count": len(future_lines),
                        "strong_realized_future_fact_candidate": candidate,
                        "example": clipped_line(example),
                        "full_field_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "classification_boundary": (
                            "year-after-trade mention; candidate is a conservative lexical screen, not a claim that every mention is leakage"
                        ),
                    }
                )
    if len(rows) != 76 or len({(row["ticker"], row["nominal_trade_date"]) for row in rows}) != 68:
        raise ValueError("future-year evidence denominator changed")
    if len({(row["ticker"], row["nominal_trade_date"]) for row in rows if row["strong_realized_future_fact_candidate"]}) != 30:
        raise ValueError("strong future-fact candidate denominator changed")
    anchors = {(row["ticker"], row["nominal_trade_date"], row["displayed_report_field"]): row for row in rows}
    for key in (
        ("AAPL", "2024-01-12", "fundamentals_report"),
        ("GOOG", "2024-01-03", "fundamentals_report"),
        ("NVDA", "2024-03-27", "sentiment_report"),
    ):
        if not anchors[key]["strong_realized_future_fact_candidate"]:
            raise ValueError(f"future-fact anchor changed: {key}")
    return rows


def priming_rows(scratch: Path) -> list[dict[str, Any]]:
    rows = []
    for ticker in ("AAPL", "GOOG", "NVDA"):
        records, _ = load_data(scratch, ticker)
        for date, record in sorted(records.items()):
            for field in ("fundamentals_report", "market_report", "news_report", "sentiment_report"):
                text = record.get(field) or ""
                match = re.search(r"final\s+transaction\s+proposal", text, re.IGNORECASE)
                if match:
                    rows.append(
                        {
                            "ticker": ticker,
                            "nominal_trade_date": date,
                            "displayed_report_field": field,
                            "decision_related_marker": match.group(0),
                            "context": clipped_line(text[match.start() : match.start() + 300]),
                            "raw_report_rendered_open_by_default": True,
                            "paper_claims_decision_related_content_removed": True,
                            "participant_priming_possible": True,
                            "full_field_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        }
                    )
    if len(rows) != 4:
        raise ValueError(f"decision-related display count changed: {len(rows)}")
    return rows


def method_rows() -> list[dict[str, Any]]:
    rows = (
        ("human stage order", True, "six named stages and the recovered production UI agree"),
        ("human response schema", True, "action, reliability, rationale, visibility flag, source judgments, and trade percentage are specified"),
        ("human execution rule", True, "paper gives percentages; production source fixes whole-share cash/share rules and $10,000 initial cash"),
        ("human participant outputs", False, "no deidentified decisions, rationales, timing logs, demographics, or portfolio paths are public"),
        ("human recruitment and ethics protocol", False, "n=19, Harvard affiliation, and consent are stated; recruitment, compensation, exclusions, and approval identifier are absent"),
        ("consensus agent count", False, "N is symbolic; no experiment value is stated"),
        ("consensus model identities/settings", False, "families/examples are named without exact revisions, prompts, temperatures, seeds, or request traces"),
        ("claim extraction schema", False, "field names are described but no runnable extractor or output contract is printed"),
        ("claim embedding model", False, "no embedding model, revision, preprocessing, or dimension is stated"),
        ("consensus hyperparameters", False, "sigma, lambda, tau, alpha, and the high-consensus cutoff are not given"),
        ("consensus graph semantics", True, "cross-report threshold edges and connected components are stated"),
        ("temporal horizons", True, "1, 7, 14, 28, 90, 180, and 360 days are stated"),
        ("temporal polynomial", False, "degree, fit details, trend-score formula, and label thresholds are absent"),
        ("temporal forecast", False, "some indicator increments are examples; full scoring functions, magnitude interval, and tie rules are absent"),
        ("temporal action sizing", False, "four signals are named but combination weights and action/position thresholds are absent"),
        ("memory horizon sets", True, "short and long horizon partitions are stated"),
        ("memory rolling window", False, "w is symbolic and slope edge cases are unspecified"),
        ("reflection prompts", False, "prompt contents, schemas, and filled calls are not released"),
        ("reflection model identities/settings", False, "no exact reflection models or inference settings are stated"),
        ("memory retrieval", False, "the active prose asserts role retrieval while detailed Chroma/time-decay retrieval is commented out"),
        ("baseline parameters", False, "named rules lack lookbacks, thresholds, execution timing, and tuning protocol"),
        ("risk-free rate", False, "Rf is symbolic with no value or frequency convention"),
        ("transaction costs and liquidity", False, "costs, slippage, spread, and liquidity are omitted and acknowledged as future work"),
        ("human ellipse", False, "definition is printed but c and the underlying human observations are absent"),
        ("2026 forward run", False, "date range and 1 PM cadence are stated; timezone, raw inputs, calls, timestamps, decisions, fills, and NAV paths are absent"),
    )
    return [
        {"dimension": dimension, "sufficiently_specified": sufficient, "evidence": evidence}
        for dimension, sufficient, evidence in rows
    ]


def consistency_rows() -> list[dict[str, Any]]:
    rows = (
        ("code_availability", "The paper points only to a 31-repository lab organization; five bounded exact repository/code searches found no TrustTrade implementation.", "claimed public model/processing/analysis code is not operationally identifiable"),
        ("historical_information_time", "68/183 stock-days contain a post-2024 year; strong examples state realized Q3 2025 revenue and January 2026 valuation in nominal January 2024 reports.", "historical human/LLM comparison inputs are not clean point-in-time evidence"),
        ("decision_content_removal", "Four raw deployed reports rendered open by default retain a 'FINAL TRANSACTION PROPOSAL' marker despite the removal claim.", "participant priming remains possible on four stock-days"),
        ("interface_sizing", "The published UI screenshot says one-share prototype sizing; the production source and Methods use percentage-of-cash/shares sizing.", "source asset and deployed protocol conflict"),
        ("memory_slope_symbol", "The stored-record prose calls Sharpe slope v^(RR), while the record and slope equation use v^(SR).", "notation is internally inconsistent"),
        ("memory_backfill_index", "Backfill prose says prior trade i<t, but the equation remains indexed R_(t,h), P_t, q_t.", "the target record/date semantics are ambiguous"),
        ("memory_sharpe_time_direction", "The text says future horizon metrics are backfilled at t+h, while Sharpe uses trailing R_(t-tau,1).", "forward versus trailing horizon semantics conflict"),
        ("inactive_baseline_table", "The strict paper-notation/production-loader replay matches 1/12 cells; plausible sensitivities match 3/12 or 7/12.", "source-retained baseline numbers lack a unique executable convention"),
        ("baseline_percentage_domain", "The human widget permits only 25/50/75/100%, but embedded GPT-4o-mini decisions include arbitrary values such as 1.93%, 20%, 53.37%, 65%, and 99.58%.", "the baseline decision stream does not obey the stated human allocation-choice domain"),
        ("human_data_availability", "The data statement links interfaces but releases no participant records or aggregate arrays behind nine human panels.", "the human-study result claims cannot be independently regenerated"),
        ("real_time_auditability", "The paper reports a 2026 1 PM daily run but exposes no timezone or timestamped request/input/decision/fill records.", "the forward-time no-future-access claim is not independently auditable"),
    )
    return [{"issue": issue, "evidence": evidence, "impact": impact} for issue, evidence, impact in rows]


def discovery_summary(scratch: Path) -> dict[str, Any]:
    repositories = json.loads((scratch / "discovery/harvard-lab-repos.json").read_text())
    search_files = sorted((scratch / "discovery").glob("github-*-search.json"))
    search_counts = {path.name: len(json.loads(path.read_text())) for path in search_files}
    if len(repositories) != 31 or any(search_counts.values()) or len(search_counts) != 5:
        raise ValueError("bounded GitHub discovery evidence changed")
    return {
        "paper_code_url": "https://github.com/Harvard-AI-and-Robotics-Lab",
        "public_organization_repositories_checked": 31,
        "bounded_exact_searches_checked": 5,
        "bounded_exact_search_matches": 0,
        "search_counts": search_counts,
        "attributable_trusttrade_pipeline_found": False,
        "negative_search_scope": "A complete current public-org inventory plus bounded exact GitHub searches; this does not prove that private, deleted, renamed, or unindexed material never existed.",
    }


def build(scratch: Path, output: Path) -> dict[str, Any]:
    verify_pins(scratch)
    output.mkdir(parents=True, exist_ok=True)

    with tarfile.open(scratch / "primary/source.tar") as archive:
        source_files = sum(member.isfile() for member in archive.getmembers())
    if source_files != 44:
        raise ValueError(f"source archive file count changed: {source_files}")

    official_pages = len(PdfReader(scratch / "primary/official.pdf").pages)
    rebuilt_pages = len(PdfReader(scratch / "primary/rebuilt.pdf").pages)
    if (official_pages, rebuilt_pages) != (24, 24):
        raise ValueError("paper page count changed")
    overlap = token_jaccard(
        (scratch / "primary/official.txt").read_text(),
        (scratch / "primary/rebuilt.txt").read_text(),
    )
    if overlap < 0.999:
        raise ValueError(f"source rebuild overlap too low: {overlap}")

    figures = figure_rows(scratch)
    results = result_rows()
    interfaces = interface_rows(scratch)
    protocols = protocol_rows()
    contamination = contamination_rows(scratch)
    priming = priming_rows(scratch)
    replays = replay_rows(scratch)
    methods = method_rows()
    inconsistencies = consistency_rows()
    discovery = discovery_summary(scratch)

    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "published_result_panel_ledger.csv", results)
    write_csv(output / "interface_artifact_inventory.csv", interfaces)
    write_csv(output / "human_interface_protocol.csv", protocols)
    write_csv(output / "input_temporal_contamination.csv", contamination)
    write_csv(output / "decision_priming_audit.csv", priming)
    write_csv(output / "inactive_baseline_replay.csv", replays)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "internal_consistency_audit.csv", inconsistencies)

    provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "arxiv_version": "v1",
        "submitted": "2026-03-23",
        "source_files": source_files,
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "official_pages_visually_checked": 24,
        "rebuilt_pages_visually_checked": 24,
        "visual_defects_observed": 0,
        "official_rebuilt_token_jaccard": overlap,
        "paper_linked_interfaces": 3,
        "paper_linked_stock_days": 183,
        "paper_linked_source_maps_with_full_sources_content": 3,
        "paper_linked_source_map_entries_each": 847,
        "participant_endpoint_probed": False,
        **discovery,
        "pins": PINS,
    }
    write_json(output / "source_provenance.json", provenance)

    readme = (
        "# TrustTrade paper-level replication audit\n\n"
        "**Verdict: not reproducible end to end.** The pinned arXiv-v1 source rebuilds to 24 pages "
        f"with {overlap:.2%} extracted-token overlap; all 24 official and all 24 rebuilt pages were "
        "visually checked without observed defects. The active paper has no numeric result table: its "
        "claims occupy 26 empirical panels, and 0/26 are author-natively regenerated because the cited "
        "lab organization exposes no identifiable TrustTrade implementation, experiment calls, human "
        "outputs, 2026 traces, decisions, fills, NAV paths, baseline outputs, or raw plot arrays.\n\n"
        "The paper-linked Netlify interfaces are nevertheless substantial author-attributable component "
        "evidence. Their three production source maps expose all 847 source contents, and their public "
        "static inputs contain 61 days each for AAPL, GOOG, and NVDA (183 stock-days). The recovered "
        "production protocol is executable: six stages, $10,000 initial cash, whole-share trades, and "
        "25/50/75/100% cash/share sizing. This is the human-interface/baseline component, **not the missing "
        "TrustTrade selective-consensus, temporal, and reflective-memory pipeline**.\n\n"
        "A source-retained ablation table is inactive and absent from the published PDF. A strict replay "
        "using the production loader's cent rounding plus the paper's literal V0..VT return notation "
        "matches 1/12 displayed cells. Two explicit sensitivities match 3/12 (post-day returns) and 7/12 "
        "(unrounded CSV closes plus post-day returns), demonstrating that the retained values do not have "
        "one uniquely specified executable convention. The embedded baseline stream also contains "
        "arbitrary percentages outside the human widget's 25/50/75/100% choices. None receives "
        "TrustTrade result credit.\n\n"
        "The public inputs materially weaken historical validity. 68/183 stock-days contain an explicit "
        "year after the nominal 2024 trade date. Not every future-year mention is leakage (some are "
        "forecasts), so the ledger preserves that boundary; however, strong examples state realized Q3 "
        "2025 revenue, January 2026 valuation, and a March 2025 NVDA/DeepSeek price event inside nominal "
        "2024 reports. In addition, four raw reports rendered open by default retain a `FINAL TRANSACTION "
        "PROPOSAL` marker despite the Methods claim that decision-related content was removed.\n\n"
        "Material blockers include missing consensus hyperparameters and embedding model, incomplete "
        "temporal scoring/threshold rules, missing memory window/prompts/models, internal forward-versus-"
        "trailing memory equations, unspecified baseline parameters/risk-free rate/costs, no participant "
        "records, and no auditable timestamped 2026 forward-run lineage. `strict_success` remains false.\n"
    )
    (output / "README.md").write_text(readme)

    generated = {
        path.name: sha256(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "active_empirical_result_panels": 26,
        "author_native_empirical_panels_regenerated": 0,
        "active_numeric_result_table_cells": 0,
        "inactive_source_table_cells": 12,
        "strict_literal_inactive_cells_matching": 1,
        "production_post_day_sensitivity_cells_matching": 3,
        "raw_csv_sensitivity_cells_matching": 7,
        "paper_linked_interfaces_recovered": 3,
        "paper_linked_stock_days_recovered": 183,
        "future_year_affected_stock_days": 68,
        "strong_future_fact_candidate_stock_days": 30,
        "decision_related_markers_exposed": 4,
        "baseline_percentages_outside_human_widget_days": 43,
        "participant_outputs_recovered": 0,
        "attributable_interface_component_recovered": True,
        "attributable_trusttrade_pipeline_found": False,
        "author_native_trusttrade_result_units_regenerated": 0,
        "strict_success": False,
        "generated_file_sha256": generated,
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return int(args.strict and not manifest["strict_success"])


if __name__ == "__main__":
    raise SystemExit(main())
