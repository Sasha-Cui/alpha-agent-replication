#!/usr/bin/env python3
"""Audit AlphaQuanter's paper tables against its pinned public release.

The audit checks every numeric cell in Tables 5--8 and 10--14, inventories the
released prompt/label Parquets, recomputes their forward-return labels from a
hash-pinned current Yahoo retrieval, and reconstructs only the released
Buy-and-Hold evaluator. It does not call an LLM, infer unavailable actions from
labels, or promote a current market-data match to a full paper reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd


SOURCE_COMMIT = "fac423cb1b45a3d0593e88a0f9805c338d7e0fea"
PAPER_SHA256 = "433ff948a2a90cb7eb83cdb823d56ed49026795f7e2688bbe8b67bcdbd444fd5"
PAPER_URL = "https://aclanthology.org/2026.findings-acl.456.pdf"
SOURCE_URL = "https://github.com/horizon-llm/AlphaQuanter"
DISPLAY_TOLERANCE = 0.005 + 1e-12
LABEL_EXACT_TOLERANCE = 1e-12
LABEL_NEAR_TOLERANCE = 1e-6
TICKERS = ("GOOGL", "META", "MSFT", "NVDA", "TSLA")

PINNED_SOURCE_SHA256 = {
    "README.md": "966424a93d889b8a9bfd82322d3007efe151c539e992001fac8bcaa4d61e8366",
    "verl/README.md": "3fc3ca47c8849b966e034919ab364c615c0d03b90ce66f46fe1aa62996cda3f0",
    "verl/data/train.parquet": "251592bb03989c0868829a994cdedb167e619a9d702bea8223f10066740c05e5",
    "verl/data/test.parquet": "6fdf5a615741cf3c4f757152cc0c82175c5e0a44ef97bb27619d58420fd93e8b",
    "verl/recipe/langgraph_agent/stock_trading/agent.yaml": "708fbdc83289fdce612254e7c3a202a4dd73e2112f6172c75a212ce6b7e6d6e2",
    "verl/recipe/langgraph_agent/stock_trading/create_dataset.py": "999e5838c92054c6cc78e5e00d2b879b45ba4f8cc2925c880eb5ae666005a304",
    "verl/recipe/langgraph_agent/stock_trading/my_reward_fn.py": "3ddd88272d88dc7b133199e70c9e90de90ee319a8b0e67f13e5b183dce7f7819",
    "verl/recipe/langgraph_agent/stock_trading/run.sh": "b771ed0f0522d6f18e8baada17c32f106f6afaa3e5c4d0f0e2df624b304ee68e",
    "verl/recipe/langgraph_agent/stock_trading/trader.py": "230618f0c5f8cebcbac3373f0d1bb09b4dd5335458214642824deaac2ece68c2",
    "verl/verl/trainer/ppo/ray_trainer.py": "5d4cd56ab2662faf8ea35479342b5e740e4236bd43909a56bc2b1a1c59456a14",
}

LABEL_PRICE_SHA256 = {
    "GOOGL.json": "037fbef0c710f50179ca215eadcecad8503abc132d97f2903b117f5b4bfc238a",
    "META.json": "c61a58e13d2ea27818a86274056772a9645072d8c73f3f2ef463f3734e06c555",
    "MSFT.json": "e26ad2800ad0653c04ffe9260873aa76534df5434e0465528a6a5fc63cdc7203",
    "NVDA.json": "1973a33df8baf21edf81d07446fb0c824895a5076ba2524f227ca1be63692e9a",
    "TSLA.json": "ac17e753b4a70073d858ecc05003fd538b71e4c7cfdfe23cbc12bbb65e66189a",
}

TEST_PRICE_SHA256 = {
    "GOOGL.json": "4678d44c049d663ffa0da3e3b2268de13f6549cfe00dcd4d9b13e04317e3d555",
    "META.json": "15d480ceb8ab217ca7f877ee16825d12ffe9eb50a5643cace4304e30745d6a00",
    "MSFT.json": "e8df24829b9fd4408e08634bd21c4c72b2550754788335c8210c8e531bc95b5c",
    "NVDA.json": "b8e5a5f202907d25002bf71ee3e9092520f6bb47c26b795d0b13980ebdd29700",
    "TSLA.json": "14bedddfb21edc67bef3d7067ce56bc96e5806957dbfd7244f1e387cfcf3bd35",
}


TABLE_5_METRICS = (
    "GOOGL_arr_pct",
    "META_arr_pct",
    "MSFT_arr_pct",
    "NVDA_arr_pct",
    "TSLA_arr_pct",
    "average_arr_pct",
    "average_sr",
    "average_mdd_pct",
)

# family|method|five stock ARRs|average ARR|average SR|average MDD
TABLE_5_TEXT = """
Market|B&H|-14.49|45.64|36.80|25.47|-28.91|12.90|0.57|31.13
Rule|MACD|-3.17|46.82|-9.58|-12.89|22.77|8.79|0.44|21.24
Rule|ZMR|-2.26|-0.98|8.53|35.01|16.74|11.41|0.46|20.86
RL|FinRLA2C|-21.22|43.41|43.15|37.43|-35.10|13.53|0.51|33.07
RL|FinRLPPO|-19.77|50.34|43.91|18.56|-31.94|12.22|0.51|33.72
LM|Chronos-2|19.07|-12.61|20.04|38.19|-17.66|9.41|0.34|24.34
LLM|FinMem|-22.41|46.25|40.26|26.71|-22.28|13.71|0.30|29.14
LLM|TradingAgents|-14.95|29.69|38.62|-7.83|36.92|16.49|0.50|21.82
Multi-Agent|Qwen2.5-3B|1.73|36.25|40.89|-3.28|-76.98|-0.28|-0.13|20.95
Multi-Agent|Qwen2.5-7B|9.33|28.98|-4.50|-17.22|-9.11|1.50|-0.08|6.43
Multi-Agent|Qwen3-30B-A3B|-18.09|1.36|9.84|10.22|-16.51|-2.64|0.06|22.20
Multi-Agent|DeepSeek-V3.1685B|-12.43|-9.48|14.13|-24.02|0.00|-6.36|-0.26|12.49
Multi-Agent|Kimi-K21T|-23.40|-9.52|12.60|-8.33|8.88|-3.95|-0.11|26.62
Multi-Agent|GPT-4o-mini|-18.08|0.73|16.27|-5.38|5.20|-0.25|-0.06|18.28
Multi-Agent|GPT-4o|-14.95|29.69|38.62|-7.83|36.92|16.49|0.50|21.82
Single-Agent w/o RL|Qwen2.5-3B|3.06|23.08|5.10|-7.43|-32.21|-1.68|0.08|25.99
Single-Agent w/o RL|Qwen2.5-7B|-22.42|35.50|17.55|1.47|-9.63|4.49|0.16|28.96
Single-Agent w/o RL|Qwen3-30B-A3B|-26.33|32.86|37.45|29.61|-46.41|5.44|0.12|30.08
Single-Agent w/o RL|DeepSeek-V3.1685B|-25.15|32.49|25.45|10.30|-1.21|8.38|0.24|30.70
Single-Agent w/o RL|Kimi-K21T|-40.48|25.83|-3.39|-3.27|13.05|-1.65|0.15|25.30
Single-Agent w/o RL|GPT-4o-mini|-24.02|44.42|43.42|13.61|-43.71|6.74|0.25|26.78
Single-Agent w/o RL|GPT-4o|-9.01|57.18|19.39|17.60|-38.04|9.42|0.25|28.27
Single-Agent + RL|AlphaQuanter-3B|-14.68|56.15|9.82|30.55|33.33|23.03|0.43|25.16
Single-Agent + RL|AlphaQuanter-7B|-2.52|41.91|47.23|45.41|42.67|34.94|0.65|24.93
"""

TABLE_10_METRICS = tuple(
    f"{ticker}_{metric}"
    for ticker in ("GOOGL", "META", "MSFT")
    for metric in ("arr_pct", "sr", "mdd_pct")
)
TABLE_11_METRICS = tuple(
    f"{ticker}_{metric}"
    for ticker in ("NVDA", "TSLA", "average")
    for metric in ("arr_pct", "sr", "mdd_pct")
)

# family|method|ARR|SR|MDD repeated for the three Table 10 columns.
TABLE_10_TEXT = """
Market|B&H|-14.49|-0.35|27.35|45.64|1.25|31.59|36.80|1.41|18.79
Rule|MACD|-3.17|-0.04|14.14|46.82|2.17|12.51|-9.58|-0.49|19.97
Rule|ZMR|-2.26|0.01|18.47|-0.98|0.12|15.19|8.53|0.56|9.59
RL|FinRLA2C|-21.22|-0.50|29.80|43.41|1.04|34.14|43.14|1.35|20.55
RL|FinRLPPO|-19.77|-0.43|29.80|50.34|1.15|34.15|43.90|1.36|20.55
LM|Chronos-2|19.07|0.60|19.43|-12.61|-0.21|36.59|20.04|0.64|13.73
LLM|FinMem|-22.41|-0.38|29.80|46.25|0.77|34.14|40.26|0.90|20.55
LLM|TradingAgents|-14.95|-0.29|25.93|29.69|0.71|14.05|38.62|0.90|19.83
Multi-Agent|Qwen2.5-3B|1.73|0.10|5.52|36.25|0.85|15.28|40.89|1.06|12.23
Multi-Agent|Qwen2.5-7B|9.33|1.38|1.40|28.98|0.87|6.54|-4.50|-1.05|2.27
Multi-Agent|Qwen3-30B-A3B|-18.09|-0.46|26.36|1.36|0.29|16.29|9.84|0.42|15.88
Multi-Agent|DeepSeek-V3.1685B|-12.43|-0.66|12.01|-9.48|-0.25|17.18|14.13|0.60|10.09
Multi-Agent|Kimi-K21T|-23.40|-1.09|17.57|-9.52|-0.10|16.12|12.60|0.51|9.11
Multi-Agent|GPT-4o-mini|-18.08|-0.94|18.86|0.73|0.04|11.11|16.27|0.48|18.52
Multi-Agent|GPT-4o|-14.95|-0.29|25.93|29.69|0.71|14.05|38.62|0.90|19.83
Single-Agent w/o RL|Qwen2.5-3B|3.06|0.07|18.18|23.08|0.52|24.91|5.10|0.14|14.66
Single-Agent w/o RL|Qwen2.5-7B|-22.42|-0.43|28.59|35.50|0.56|28.49|17.55|0.48|19.60
Single-Agent w/o RL|Qwen3-30B-A3B|-26.33|-0.50|28.39|32.86|0.81|28.18|37.45|0.87|21.15
Single-Agent w/o RL|DeepSeek-V3.1685B|-25.15|-0.47|29.77|32.49|0.61|34.14|25.45|0.64|19.94
Single-Agent w/o RL|Kimi-K21T|-40.48|-0.39|24.67|25.83|0.68|21.65|-3.39|-0.03|19.21
Single-Agent w/o RL|GPT-4o-mini|-24.02|-0.56|23.20|44.42|0.97|23.84|43.42|1.10|12.92
Single-Agent w/o RL|GPT-4o|-9.01|-0.12|19.72|57.18|0.99|25.02|19.39|0.53|23.04
Single-Agent + RL|AlphaQuanter-3B|-14.68|-0.29|25.60|56.15|1.08|23.75|9.82|0.30|21.06
Single-Agent + RL|AlphaQuanter-7B|-2.52|0.05|21.37|41.91|0.78|25.65|47.23|1.17|14.85
"""

TABLE_11_TEXT = """
Market|B&H|25.47|0.74|33.83|-28.91|-0.20|44.10|12.90|0.57|31.13
Rule|MACD|-12.89|-0.22|30.76|22.77|0.78|28.83|8.79|0.44|21.24
Rule|ZMR|35.01|1.03|16.72|16.74|0.59|44.33|11.41|0.46|20.86
RL|FinRLA2C|37.42|0.84|32.68|-35.10|-0.19|48.18|13.53|0.51|33.07
RL|FinRLPPO|18.56|0.58|35.93|-31.94|-0.12|48.18|12.22|0.51|33.72
LM|Chronos-2|38.19|0.73|16.32|-17.66|-0.04|35.62|9.41|0.34|24.34
LLM|FinMem|26.71|0.48|36.89|-22.28|-0.27|24.32|13.71|0.30|29.14
LLM|TradingAgents|-7.83|0.03|38.74|36.92|1.17|10.56|16.49|0.50|21.82
Multi-Agent|Qwen2.5-3B|-3.28|-0.06|18.77|-76.98|-2.60|52.95|-0.28|-0.13|20.95
Multi-Agent|Qwen2.5-7B|-17.22|-0.99|14.12|-9.11|-0.59|7.82|1.50|-0.08|6.43
Multi-Agent|Qwen3-30B-A3B|10.22|0.31|23.78|-16.51|-0.25|28.71|-2.64|0.06|22.20
Multi-Agent|DeepSeek-V3.1685B|-24.02|-0.97|23.18|0.00|0.00|0.00|-6.36|-0.26|12.49
Multi-Agent|Kimi-K21T|-8.33|-0.28|18.88|8.88|0.40|71.40|-3.95|-0.11|26.62
Multi-Agent|GPT-4o-mini|-5.38|0.01|36.61|5.20|0.10|6.30|-0.25|-0.06|18.28
Multi-Agent|GPT-4o|-7.83|0.03|38.74|36.92|1.17|10.56|16.49|0.50|21.82
Single-Agent w/o RL|Qwen2.5-3B|-7.43|0.14|34.63|-32.21|-0.46|37.59|-1.68|0.08|25.99
Single-Agent w/o RL|Qwen2.5-7B|1.47|0.22|40.24|-9.63|-0.04|27.88|4.49|0.16|28.96
Single-Agent w/o RL|Qwen3-30B-A3B|29.61|0.51|33.48|-46.41|-1.08|39.22|5.44|0.12|30.08
Single-Agent w/o RL|DeepSeek-V3.1685B|10.30|0.31|39.81|-1.21|0.13|29.82|8.38|0.24|30.70
Single-Agent w/o RL|Kimi-K21T|-3.27|0.11|34.92|13.05|0.36|26.05|-1.65|0.15|25.30
Single-Agent w/o RL|GPT-4o-mini|13.61|0.35|37.60|-43.71|-0.59|36.32|6.74|0.25|26.78
Single-Agent w/o RL|GPT-4o|17.60|0.39|38.53|-38.04|-0.54|35.06|9.42|0.25|28.27
Single-Agent + RL|AlphaQuanter-3B|30.55|0.51|29.04|33.33|0.57|26.34|23.03|0.43|25.16
Single-Agent + RL|AlphaQuanter-7B|45.41|0.66|34.91|42.67|0.58|27.88|34.94|0.65|24.93
"""

TABLE_6_TEXT = """
efficiency|TradingAgents-7B|27200|1.00|1.50
efficiency|SingleAgent-7B|3100|0.11|4.49
efficiency|AlphaQuanter-7B|4100|0.15|34.94
"""
TABLE_6_METRICS = ("average_tokens", "relative_cost", "arr_pct")

TABLE_7_TEXT = """
human_faithfulness|MA|1.20|1.24|1.03|1.157
human_faithfulness|SA|1.38|1.18|1.32|1.293
human_faithfulness|SA+RL|1.70|1.28|1.68|1.557
"""
TABLE_7_METRICS = ("alignment", "grounding", "conciseness", "overall")

TABLE_8_TEXT = """
ablation|AlphaQuanter-7B|34.94|0.65|24.93
ablation|w/o Rformat|16.36|0.40|26.49
ablation|w/o Rtool|19.90|0.49|24.08
ablation|theta +0.5pct|21.25|0.28|9.18
ablation|theta -0.5pct|20.23|0.43|32.67
"""
TABLE_8_METRICS = ("average_arr_pct", "average_sr", "average_mdd_pct")

TABLE_12_TEXT = """
rolling|Buy & Hold|-23.02|2.74|50.37|40.60|45.71|23.28|-0.01|25.01
rolling|FinMem|-21.33|15.78|79.85|42.49|-24.32|18.49|-0.08|21.36
rolling|TradingAgents|-16.06|22.16|58.03|-4.52|61.86|24.29|0.25|12.16
rolling|AlphaQuanter-3B|-27.72|46.16|22.17|78.61|88.52|41.55|0.13|19.02
rolling|AlphaQuanter-7B|9.35|43.65|29.91|62.86|115.51|52.26|0.26|17.48
"""
TABLE_12_METRICS = TABLE_5_METRICS

TABLE_13_TEXT = """
ablation|AlphaQuanter-7B|-2.52|0.05|21.37|41.91|0.78|25.65|47.23|1.17|14.85
ablation|w/o Rformat|-6.40|-0.09|24.86|12.99|0.66|25.03|13.94|0.51|18.93
ablation|w/o Rtool|-14.22|-0.25|25.28|47.29|0.85|24.23|28.40|0.72|19.81
ablation|theta +0.5pct|2.83|0.10|4.59|16.07|0.27|10.91|16.53|0.48|2.40
ablation|theta -0.5pct|-13.05|-0.16|28.66|50.82|0.82|34.50|38.16|0.87|20.01
"""
TABLE_13_METRICS = TABLE_10_METRICS

TABLE_14_TEXT = """
ablation|AlphaQuanter-7B|45.41|0.66|34.91|42.67|0.58|27.88|34.94|0.65|24.93
ablation|w/o Rformat|33.70|0.49|35.55|27.59|0.43|28.06|16.36|0.40|26.49
ablation|w/o Rtool|20.73|0.43|35.24|17.28|0.70|15.85|19.90|0.49|24.08
ablation|theta +0.5pct|40.00|0.22|20.88|30.84|0.32|7.14|21.25|0.28|9.18
ablation|theta -0.5pct|31.73|0.53|36.50|-6.50|0.11|43.66|20.23|0.43|32.67
"""
TABLE_14_METRICS = TABLE_11_METRICS


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_table(table: int, text: str, metrics: Sequence[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in text.strip().splitlines():
        values = line.split("|")
        if len(values) != 2 + len(metrics):
            raise ValueError(f"Malformed Table {table} row: {line}")
        family, method = values[:2]
        for metric, value in zip(metrics, values[2:]):
            rows.append(
                {
                    "paper_table": table,
                    "family_or_setting": family,
                    "method": method,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    return rows


def paper_result_rows() -> List[Dict[str, Any]]:
    return [
        *parse_table(5, TABLE_5_TEXT, TABLE_5_METRICS),
        *parse_table(6, TABLE_6_TEXT, TABLE_6_METRICS),
        *parse_table(7, TABLE_7_TEXT, TABLE_7_METRICS),
        *parse_table(8, TABLE_8_TEXT, TABLE_8_METRICS),
        *parse_table(10, TABLE_10_TEXT, TABLE_10_METRICS),
        *parse_table(11, TABLE_11_TEXT, TABLE_11_METRICS),
        *parse_table(12, TABLE_12_TEXT, TABLE_12_METRICS),
        *parse_table(13, TABLE_13_TEXT, TABLE_13_METRICS),
        *parse_table(14, TABLE_14_TEXT, TABLE_14_METRICS),
    ]


def paper_internal_consistency() -> List[Dict[str, Any]]:
    rows = paper_result_rows()
    compact = {
        (row["family_or_setting"], row["method"], row["metric"]): row["paper_value"]
        for row in rows
        if row["paper_table"] == 5
    }
    detailed = {
        (row["family_or_setting"], row["method"], row["metric"]): row["paper_value"]
        for row in rows
        if row["paper_table"] in {10, 11}
    }
    output = []
    for key in sorted(compact.keys() & detailed.keys()):
        if not math.isclose(compact[key], detailed[key], abs_tol=1e-12):
            output.append(
                {
                    "family_or_setting": key[0],
                    "method": key[1],
                    "metric": key[2],
                    "table_5_value": compact[key],
                    "table_10_or_11_value": detailed[key],
                    "absolute_difference": abs(compact[key] - detailed[key]),
                    "status": "paper_internal_display_mismatch",
                }
            )
    return output


def load_yahoo_frame(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(result["timestamp"], unit="s", utc=True).strftime("%Y-%m-%d"),
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "unadjusted_close": quote["close"],
            "adjusted_close": adjusted,
            "volume": quote["volume"],
        }
    )
    return frame.dropna(subset=["open", "adjusted_close"]).reset_index(drop=True)


def action_label(value: float) -> str:
    if abs(value) <= 1.5:
        return "HOLD"
    return "BUY" if value > 0 else "SELL"


def extract_prompt_identity(prompt: Any) -> Tuple[str, str, bool]:
    roles = [item["role"] for item in prompt]
    system = next(item["content"] for item in prompt if item["role"] == "system")
    date_match = re.search(r"Current date:\s*([\d-]+)", system)
    ticker_match = re.search(r"Target stock ticker:\s*([A-Z]+)", system)
    if not date_match or not ticker_match:
        raise RuntimeError("Released prompt lacks a date or ticker")
    return date_match.group(1), ticker_match.group(1), roles == ["system", "human"]


def dataset_inventory(source_root: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    definitions = (
        ("paper_train", "verl/data/train.parquet", "2022-09-01", "2024-03-30", 395, 1975),
        ("paper_validation_released_as_test", "verl/data/test.parquet", "2024-05-15", "2024-11-14", 128, 640),
    )
    inventory: List[Dict[str, Any]] = []
    examples: List[Dict[str, Any]] = []
    for role, relative, expected_start, expected_end, expected_dates, expected_rows in definitions:
        path = source_root / relative
        frame = pd.read_parquet(path)
        identities = [extract_prompt_identity(prompt) for prompt in frame["prompt"]]
        dates = [identity[0] for identity in identities]
        tickers = [identity[1] for identity in identities]
        extras = list(frame["extra_info"])
        prompt_dates_match = all(date == str(extra["date"]) for date, extra in zip(dates, extras))
        roles_match = all(identity[2] for identity in identities)
        expected_calls_match = all(int(extra["expected_tool_calls"]) == 8 for extra in extras)
        counts = Counter(tickers)
        dates_per_ticker = {
            ticker: len({date for date, observed in zip(dates, tickers) if observed == ticker})
            for ticker in TICKERS
        }
        if len(frame) != expected_rows or len(set(dates)) != expected_dates:
            raise RuntimeError(f"Pinned AlphaQuanter dataset shape changed for {relative}")
        if set(counts) != set(TICKERS) or set(counts.values()) != {expected_dates}:
            raise RuntimeError(f"Pinned AlphaQuanter ticker coverage changed for {relative}")
        if not prompt_dates_match or not roles_match or not expected_calls_match:
            raise RuntimeError(f"Pinned AlphaQuanter prompt schema changed for {relative}")
        inventory.append(
            {
                "paper_role": role,
                "released_path": relative,
                "exists": True,
                "rows": len(frame),
                "distinct_trading_dates": len(set(dates)),
                "minimum_date": min(dates),
                "maximum_date": max(dates),
                "paper_start": expected_start,
                "paper_end": expected_end,
                "paper_stated_trading_days": expected_dates,
                "tickers": ";".join(sorted(counts)),
                "rows_per_ticker": ";".join(f"{ticker}:{counts[ticker]}" for ticker in sorted(counts)),
                "prompt_date_matches_extra_info": prompt_dates_match,
                "prompt_roles_system_human": roles_match,
                "expected_tool_calls_is_8": expected_calls_match,
                "released_extra_info_split": ";".join(sorted({str(extra["split"]) for extra in extras})),
                "status": "released_prompt_label_component",
            }
        )
        for index, (_, row) in enumerate(frame.iterrows()):
            date, ticker, _ = identities[index]
            examples.append(
                {
                    "paper_role": role,
                    "released_path": relative,
                    "row_index": index,
                    "date": date,
                    "ticker": ticker,
                    "ground_truth": float(row["reward_model"]["ground_truth"]),
                }
            )
        if set(dates_per_ticker.values()) != {expected_dates}:
            raise RuntimeError(f"Pinned AlphaQuanter date coverage changed for {relative}")

    inventory.append(
        {
            "paper_role": "paper_test",
            "released_path": "absent",
            "exists": False,
            "rows": 0,
            "distinct_trading_dates": 0,
            "minimum_date": "",
            "maximum_date": "",
            "paper_start": "2025-01-01",
            "paper_end": "2025-06-30",
            "paper_stated_trading_days": 122,
            "tickers": ";".join(TICKERS),
            "rows_per_ticker": "",
            "prompt_date_matches_extra_info": "",
            "prompt_roles_system_human": "",
            "expected_tool_calls_is_8": "",
            "released_extra_info_split": "",
            "status": "missing_paper_test_prompts_labels_and_actions",
        }
    )
    return inventory, examples


def current_forward_label(price_frame: pd.DataFrame, date: str) -> float:
    prices = np.round(price_frame["adjusted_close"].to_numpy(dtype=float), 2)
    positions = {value: index for index, value in enumerate(price_frame["date"])}
    index = positions[date]
    if index + 8 >= len(prices):
        raise RuntimeError(f"Current Yahoo input lacks the seven-day horizon after {date}")
    denominator = prices[index + 1]
    returns = np.asarray([prices[index + k] / denominator - 1.0 for k in range(2, 9)])
    raw_weights = np.asarray([0.8 ** (k - 1) for k in range(2, 9)], dtype=float)
    weights = 100 * raw_weights / raw_weights.sum()
    return float(returns @ weights)


def reward_label_audit(
    examples: Sequence[Mapping[str, Any]], price_root: Path
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    prices: Dict[str, pd.DataFrame] = {}
    price_inventory = []
    for filename, expected in LABEL_PRICE_SHA256.items():
        path = price_root / filename
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"Pinned AlphaQuanter label-price hash changed for {filename}: {actual}")
        ticker = filename.removesuffix(".json")
        prices[ticker] = load_yahoo_frame(path)
        price_inventory.append(
            {
                "purpose": "released_reward_label_recomputation",
                "ticker": ticker,
                "filename": filename,
                "sha256": actual,
                "observations": len(prices[ticker]),
                "minimum_date": prices[ticker]["date"].min(),
                "maximum_date": prices[ticker]["date"].max(),
                "retrieval_date": "2026-08-11",
                "interpretation": "current historical retrieval; not the unavailable paper snapshot",
            }
        )

    rows = []
    for example in examples:
        released = float(example["ground_truth"])
        recomputed = current_forward_label(prices[str(example["ticker"])], str(example["date"]))
        error = abs(released - recomputed)
        released_label = action_label(released)
        recomputed_label = action_label(recomputed)
        if error <= LABEL_EXACT_TOLERANCE:
            status = "exact_current_yahoo_numeric_match"
        elif released_label == recomputed_label:
            status = "numeric_snapshot_difference_same_reward_regime"
        else:
            status = "current_yahoo_difference_crosses_reward_threshold"
        rows.append(
            {
                **example,
                "recomputed_current_yahoo_ground_truth": recomputed,
                "absolute_error": error,
                "within_1e_12": error <= LABEL_EXACT_TOLERANCE,
                "within_1e_6": error <= LABEL_NEAR_TOLERANCE,
                "released_action_label": released_label,
                "recomputed_current_yahoo_action_label": recomputed_label,
                "reward_regime_matches": released_label == recomputed_label,
                "status": status,
            }
        )

    summaries = []
    for (role, ticker), group in pd.DataFrame(rows).groupby(["paper_role", "ticker"], sort=True):
        summaries.append(
            {
                "paper_role": role,
                "ticker": ticker,
                "rows": len(group),
                "exact_numeric_matches": int(group["within_1e_12"].sum()),
                "within_1e_6": int(group["within_1e_6"].sum()),
                "reward_regime_matches": int(group["reward_regime_matches"].sum()),
                "reward_regime_mismatches": int((~group["reward_regime_matches"]).sum()),
                "mean_absolute_error": float(group["absolute_error"].mean()),
                "maximum_absolute_error": float(group["absolute_error"].max()),
            }
        )
    return rows, summaries, price_inventory


def released_buy_every_day_metrics(frame: pd.DataFrame) -> Dict[str, float]:
    """Mirror the released Backtrader BuyAndHold loop without importing it.

    The released collector rounds OHLC to cents. Each BUY is submitted at a
    day's close for 90% of remaining cash and executes at the next day's open;
    commission is 0.1%. This implementation was checked against Backtrader
    1.9.78.123 on the pinned inputs to sub-display floating-point tolerance.
    """

    if len(frame) < 2:
        raise ValueError("Backtest requires at least two observations")
    work = frame.copy().reset_index(drop=True)
    work["open"] = work["open"].round(2)
    work["adjusted_close"] = work["adjusted_close"].round(2)
    cash = 1_000_000.0
    shares = 0
    pending_size = 0
    values: List[float] = []
    for index, row in work.iterrows():
        if pending_size:
            execution_cost = pending_size * float(row["open"]) * 1.001
            if execution_cost <= cash:
                cash -= execution_cost
                shares += pending_size
            pending_size = 0
        values.append(cash + shares * float(row["adjusted_close"]))
        if index < len(work) - 1:
            pending_size = max(
                int(math.floor(cash * 0.9 / float(row["adjusted_close"]))),
                0,
            )
    value_array = np.asarray(values, dtype=float)
    daily_returns = np.diff(value_array) / value_array[:-1]
    total_return = value_array[-1] / value_array[0] - 1.0
    peaks = np.maximum.accumulate(value_array)
    return {
        "arr_pct": ((1 + total_return) ** (252 / len(work)) - 1) * 100,
        "sr": float(np.mean(daily_returns) / np.std(daily_returns) * math.sqrt(len(work))),
        "mdd_pct": float(np.max((peaks - value_array) / peaks) * 100),
        "total_return_pct": total_return * 100,
        "observations": len(work),
    }


def buy_hold_audit(
    price_root: Path,
) -> Tuple[Dict[int, Dict[str, float]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    full: Dict[str, Dict[str, float]] = {}
    rolling: Dict[str, Dict[str, float]] = {}
    inventory = []
    for filename, expected in TEST_PRICE_SHA256.items():
        path = price_root / filename
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"Pinned AlphaQuanter test-price hash changed for {filename}: {actual}")
        ticker = filename.removesuffix(".json")
        frame = load_yahoo_frame(path)
        frame = frame[frame["date"].between("2025-01-01", "2025-06-30")].reset_index(drop=True)
        full[ticker] = released_buy_every_day_metrics(frame)
        windows = [
            released_buy_every_day_metrics(frame.iloc[start : start + 60])
            for start in range(0, len(frame), 5)
            if start + 60 <= len(frame)
        ]
        rolling[ticker] = {
            metric: float(np.mean([window[metric] for window in windows]))
            for metric in ("arr_pct", "sr", "mdd_pct")
        }
        inventory.append(
            {
                "purpose": "paper_test_buy_and_hold_reconstruction",
                "ticker": ticker,
                "filename": filename,
                "sha256": actual,
                "observations_in_paper_date_bounds": len(frame),
                "paper_stated_trading_days": 122,
                "minimum_date": frame["date"].min(),
                "maximum_date": frame["date"].max(),
                "rolling_60_observation_windows_step_5": len(windows),
                "retrieval_date": "2026-08-11",
                "interpretation": "current historical retrieval; not the unavailable paper snapshot",
            }
        )

    def flatten(values: Mapping[str, Mapping[str, float]]) -> Dict[str, float]:
        output = {
            f"{ticker}_{metric}": values[ticker][metric]
            for ticker in TICKERS
            for metric in ("arr_pct", "sr", "mdd_pct")
        }
        for metric in ("arr_pct", "sr", "mdd_pct"):
            output[f"average_{metric}"] = float(np.mean([values[ticker][metric] for ticker in TICKERS]))
        return output

    full_flat = flatten(full)
    rolling_flat = flatten(rolling)
    # Table 5 contains per-stock ARR plus average ARR/SR/MDD.
    table_5 = {
        **{f"{ticker}_arr_pct": full[ticker]["arr_pct"] for ticker in TICKERS},
        "average_arr_pct": full_flat["average_arr_pct"],
        "average_sr": full_flat["average_sr"],
        "average_mdd_pct": full_flat["average_mdd_pct"],
    }
    table_12 = {
        **{f"{ticker}_arr_pct": rolling[ticker]["arr_pct"] for ticker in TICKERS},
        "average_arr_pct": rolling_flat["average_arr_pct"],
        "average_sr": rolling_flat["average_sr"],
        "average_mdd_pct": rolling_flat["average_mdd_pct"],
    }
    metrics = {5: table_5, 10: full_flat, 11: full_flat, 12: table_12}
    rows = []
    for ticker in TICKERS:
        rows.append(
            {
                "ticker": ticker,
                "full_arr_pct": full[ticker]["arr_pct"],
                "full_sr": full[ticker]["sr"],
                "full_mdd_pct": full[ticker]["mdd_pct"],
                "full_total_return_pct": full[ticker]["total_return_pct"],
                "rolling_arr_pct": rolling[ticker]["arr_pct"],
                "rolling_sr": rolling[ticker]["sr"],
                "rolling_mdd_pct": rolling[ticker]["mdd_pct"],
            }
        )
    return metrics, rows, inventory


def result_conformance(buy_hold_metrics: Mapping[int, Mapping[str, float]]) -> List[Dict[str, Any]]:
    rows = []
    for target in paper_result_rows():
        is_buy_hold = (
            target["paper_table"] in {5, 10, 11} and target["family_or_setting"] == "Market" and target["method"] == "B&H"
        ) or (
            target["paper_table"] == 12 and target["method"] == "Buy & Hold"
        )
        recomputed: Any = ""
        absolute_error: Any = ""
        if is_buy_hold:
            recomputed = buy_hold_metrics[int(target["paper_table"])][str(target["metric"])]
            absolute_error = abs(float(target["paper_value"]) - float(recomputed))
            status = (
                "exact_displayed_precision_match_current_yahoo"
                if absolute_error <= DISPLAY_TOLERANCE
                else "mismatch_against_pinned_current_yahoo"
            )
            evidence = "released_execution_rules_plus_pinned_current_yahoo_rounded_ohlc"
        elif target["paper_table"] == 6:
            status = "unverifiable_missing_token_and_cost_logs"
            evidence = "paper_value_only_no_shipped_rollouts_token_log_or_cost_ledger"
        elif target["paper_table"] == 7:
            status = "unverifiable_missing_ratings_and_sample"
            evidence = "paper_value_only_no_shipped_50_item_sample_rater_scores_or_adjudication"
        else:
            status = "unverifiable_missing_native_action_or_result_path"
            evidence = "paper_value_only_no_shipped_checkpoint_action_series_or_trial_output"
        rows.append(
            {
                **target,
                "source_recomputed_value": recomputed,
                "absolute_error": absolute_error,
                "display_tolerance": DISPLAY_TOLERANCE if is_buy_hold else "",
                "status": status,
                "evidence": evidence,
            }
        )
    return rows


def source_release_inventory(source_root: Path) -> List[Dict[str, Any]]:
    tracked = subprocess.run(
        ["git", "-C", str(source_root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    rows = []
    for relative in tracked:
        path = source_root / relative
        lowered = relative.lower()
        if lowered.endswith(("train.parquet", "test.parquet")):
            role = "released_prompt_and_reward_label_component"
        elif lowered.startswith("figures/"):
            role = "static_paper_figure_not_numeric_result_path"
        elif lowered.endswith((".py", ".sh", ".yaml")):
            role = "source_or_configuration"
        else:
            role = "documentation_or_dependency_specification"
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "role": role,
                "native_generated_action_or_return": False,
                "checkpoint_or_training_log": False,
            }
        )
    if len(rows) != 31:
        raise RuntimeError(f"Pinned AlphaQuanter tracked-file count changed: {len(rows)}")
    return rows


def source_config_audit(source_root: Path) -> List[Dict[str, str]]:
    stock = source_root / "verl/recipe/langgraph_agent/stock_trading"
    create = (stock / "create_dataset.py").read_text(encoding="utf-8")
    reward = (stock / "my_reward_fn.py").read_text(encoding="utf-8")
    run = (stock / "run.sh").read_text(encoding="utf-8")
    trainer = (source_root / "verl/verl/trainer/ppo/ray_trainer.py").read_text(encoding="utf-8")
    market = (source_root / "data_collection/market_metrics/get_market_data.py").read_text(encoding="utf-8")
    root_readme = (source_root / "README.md").read_text(encoding="utf-8")
    verl_readme = (source_root / "verl/README.md").read_text(encoding="utf-8")
    checks = {
        "horizon": "next_t = 8" in create and "range(2, next_t + 1)" in create,
        "label_decay": "lam = 0.8" in create,
        "threshold": "THRESHOLD = 1.5" in reward,
        "alpha": '"score": 5 * result_reward' in reward,
        "tool_bounds": "num_calls <= 4 or num_calls > 8" in reward,
        "commission": "setcommission(commission=0.001)" in trainer,
        "cash_buffer": "buffer_ratio=0.9" in trainer,
        "arr_formula": "(1 + arr2) ** (252 / len(df)) - 1" in trainer,
        "sharpe_formula": "np.sqrt(len(df))" in trainer,
        "validation_dates": '"2024-05-15"' in trainer and '"2024-11-14"' in trainer,
        "validation_temperature": "val_kwargs.temperature=1.0" in run,
        "rounded_market_data": 'df[price_columns] = df[price_columns].round(2)' in market,
        "data_placeholder": '/path/to/collected_data/' in create and 'DATA_PATH = "/path/to/collected_data/"' in trainer,
        "missing_main_ppo": not (source_root / "verl/verl/trainer/main_ppo.py").exists(),
        "plural_recipe_doc_path": "recipes/stock_trading" in root_readme or "recipes/stock_trading" in verl_readme,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Pinned AlphaQuanter source findings changed: {checks}")

    return [
        {"dimension": "stock_universe", "paper": "GOOGL,META,MSFT,NVDA,TSLA", "released": "same five tickers in both Parquets", "status": "match"},
        {"dimension": "train_split", "paper": "2022-09-01 to 2024-03-30; 395 days", "released": "2022-09-01 to last trading day 2024-03-28; 395 dates", "status": "trading_calendar_match"},
        {"dimension": "validation_split", "paper": "2024-05-15 to 2024-11-14; 128 days", "released": "same dates and 128 dates, but file/split named test", "status": "values_match_role_mislabeled"},
        {"dimension": "test_split", "paper": "2025-01-01 to 2025-06-30; 122 days", "released": "absent; current exchange calendar retrieval has 121 observations", "status": "missing"},
        {"dimension": "forward_horizon_H", "paper": "7", "released": "k=2..8 relative to t+1 (seven future returns)", "status": "match"},
        {"dimension": "forward_weight_decay", "paper": "exponential eta, numeric eta not disclosed", "released": "lambda=0.8", "status": "paper_underspecified"},
        {"dimension": "decision_threshold_theta", "paper": "1.5%", "released": "THRESHOLD=1.5", "status": "match"},
        {"dimension": "result_reward_weight_alpha", "paper": "5", "released": "5 * result_reward", "status": "match"},
        {"dimension": "transaction_cost_lambda", "paper": "0.001", "released": "Backtrader commission=0.001", "status": "match"},
        {"dimension": "investment_fraction_kappa", "paper": "0.9", "released": "cash buffer_ratio=0.9 for each BUY", "status": "match"},
        {"dimension": "market_price_rounding", "paper": "not disclosed", "released": "all OHLC price columns rounded to cents before CSV write", "status": "paper_underspecified"},
        {"dimension": "main_models", "paper": "Qwen2.5-3B-Instruct and Qwen2.5-7B-Instruct", "released": "run.sh defaults Qwen2.5-7B-Instruct only; manually overridable", "status": "incomplete"},
        {"dimension": "training_algorithm", "paper": "GRPO, five epochs and Table 9 settings", "released": "GRPO and matching principal Table 9 settings", "status": "match"},
        {"dimension": "inference_temperature", "paper": "0 (deterministic)", "released": "validation temperature=1.0 and top_p=0.6", "status": "mismatch"},
        {"dimension": "three_random_seed_runs", "paper": "mean across three independent random seeds", "released": "no seed values or three-run driver", "status": "missing"},
        {"dimension": "paper_metric_sharpe", "paper": "mean daily return divided by sample standard deviation; no horizon multiplier", "released": "population std times sqrt(number of rows)", "status": "mismatch"},
        {"dimension": "full_period_evaluator", "paper": "2025-01-01 to 2025-06-30", "released": "hardcoded 2024-05-15 to 2024-11-14 validation only", "status": "missing"},
        {"dimension": "rolling_evaluator", "paper": "3 months, 7-day step", "released": "60 observations, 5-row step, hardcoded 128-row validation loop", "status": "semantic_approximation"},
        {"dimension": "collected_multimodal_data", "paper": "market, technical, news, Reddit, macro, and fundamentals", "released": "collection scripts only; DATA_PATH placeholder and no collected_data", "status": "missing_original_inputs"},
        {"dimension": "complete_VERL_runtime", "paper": "trainable end-to-end system", "released": "31-file patch snapshot; invoked verl.trainer.main_ppo is absent", "status": "not_operational_without_upstream_merge"},
        {"dimension": "documented_recipe_path", "paper": "runnable release", "released": "README uses recipes/stock_trading; tree is recipe/langgraph_agent/stock_trading", "status": "mismatch"},
        {"dimension": "checkpoints", "paper": "trained 3B and 7B policies", "released": "none", "status": "missing"},
        {"dimension": "native_action_series", "paper": "three-seed decisions for main/rolling/ablation tables", "released": "none", "status": "missing"},
        {"dimension": "token_and_cost_logs", "paper": "Table 6", "released": "none", "status": "missing"},
        {"dimension": "human_rating_records", "paper": "50 random inputs, three PhD raters", "released": "no sampled inputs, individual ratings, or rater assignment", "status": "missing"},
        {"dimension": "published_numeric_result_paths", "paper": "Tables 5--8 and 10--14 plus training figures", "released": "static PNG figures only; no numeric result tables or underlying paths", "status": "missing"},
    ]


def build_audit(
    source_root: Path,
    paper_path: Path,
    label_price_root: Path,
    test_price_root: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected AlphaQuanter source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official AlphaQuanter paper hash does not match the pinned primary source")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        actual = sha256(source_root / relative)
        if actual != expected:
            raise RuntimeError(f"Pinned AlphaQuanter source hash changed for {relative}: {actual}")

    dataset_rows, examples = dataset_inventory(source_root)
    label_rows, label_summary, label_prices = reward_label_audit(examples, label_price_root)
    buy_hold_metrics, buy_hold_rows, test_prices = buy_hold_audit(test_price_root)
    conformance = result_conformance(buy_hold_metrics)
    inconsistencies = paper_internal_consistency()
    release_files = source_release_inventory(source_root)
    config = source_config_audit(source_root)

    table_counts = Counter(row["paper_table"] for row in conformance)
    expected_table_counts = {5: 192, 6: 9, 7: 12, 8: 15, 10: 216, 11: 216, 12: 40, 13: 45, 14: 45}
    if table_counts != expected_table_counts:
        raise RuntimeError(f"AlphaQuanter paper table denominator changed: {table_counts}")
    result_status = Counter(row["status"] for row in conformance)
    expected_result_status = {
        "exact_displayed_precision_match_current_yahoo": 1,
        "mismatch_against_pinned_current_yahoo": 33,
        "unverifiable_missing_token_and_cost_logs": 9,
        "unverifiable_missing_ratings_and_sample": 12,
        "unverifiable_missing_native_action_or_result_path": 735,
    }
    if result_status != expected_result_status:
        raise RuntimeError(f"AlphaQuanter result status counts changed: {result_status}")
    label_status = Counter(row["status"] for row in label_rows)
    expected_label_status = {
        "exact_current_yahoo_numeric_match": 523,
        "numeric_snapshot_difference_same_reward_regime": 2089,
        "current_yahoo_difference_crosses_reward_threshold": 3,
    }
    if label_status != expected_label_status:
        raise RuntimeError(f"AlphaQuanter reward-label status counts changed: {label_status}")
    if len(inconsistencies) != 3:
        raise RuntimeError(f"Expected three paper internal table inconsistencies, found {len(inconsistencies)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_5_8_10_14_conformance.csv", conformance, list(conformance[0]))
    write_csv(output_dir / "released_dataset_inventory.csv", dataset_rows, list(dataset_rows[0]))
    write_csv(output_dir / "reward_label_conformance.csv", label_rows, list(label_rows[0]))
    write_csv(output_dir / "reward_label_summary.csv", label_summary, list(label_summary[0]))
    write_csv(output_dir / "buy_hold_reconstruction.csv", buy_hold_rows, list(buy_hold_rows[0]))
    price_inventory = [*label_prices, *test_prices]
    price_fields = list(dict.fromkeys(key for row in price_inventory for key in row))
    write_csv(output_dir / "external_price_input_inventory.csv", price_inventory, price_fields)
    write_csv(output_dir / "paper_internal_inconsistencies.csv", inconsistencies, list(inconsistencies[0]))
    write_csv(output_dir / "released_source_inventory.csv", release_files, list(release_files[0]))
    write_csv(output_dir / "source_config_conformance.csv", config, list(config[0]))

    manifest: Dict[str, Any] = {
        "audit": "AlphaQuanter paper Tables 5--8 and 10--14 versus pinned public release",
        "overall_status": "not_reproduced_prompt_label_component_and_buy_hold_reconstruction_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "paper_numeric_tables_audited": [5, 6, 7, 8, 10, 11, 12, 13, 14],
        "paper_numeric_result_cells_total": len(conformance),
        "paper_table_cell_counts": dict(sorted(table_counts.items())),
        "buy_hold_cells_recomputed": 34,
        "buy_hold_cells_matched_current_yahoo_at_display_precision": result_status[
            "exact_displayed_precision_match_current_yahoo"
        ],
        "buy_hold_cells_mismatched_current_yahoo": result_status[
            "mismatch_against_pinned_current_yahoo"
        ],
        "non_buy_hold_cells_unverifiable": 756,
        "paper_internal_table_5_vs_10_11_display_mismatches": len(inconsistencies),
        "released_prompt_label_rows": len(label_rows),
        "released_prompt_label_trading_dates": {"train": 395, "validation": 128},
        "paper_test_prompt_rows_shipped": 0,
        "paper_test_action_rows_shipped": 0,
        "reward_label_exact_numeric_matches_current_yahoo": label_status[
            "exact_current_yahoo_numeric_match"
        ],
        "reward_label_within_1e_6_current_yahoo": sum(row["within_1e_6"] for row in label_rows),
        "reward_label_regime_matches_current_yahoo": sum(row["reward_regime_matches"] for row in label_rows),
        "reward_label_regime_mismatches_current_yahoo": label_status[
            "current_yahoo_difference_crosses_reward_threshold"
        ],
        "released_test_named_file_is_paper_validation_split": True,
        "paper_stated_test_trading_days": 122,
        "current_exchange_calendar_test_observations": 121,
        "native_training_checkpoints_shipped": False,
        "native_agent_action_or_return_series_shipped": False,
        "native_three_seed_outputs_shipped": False,
        "native_token_or_cost_logs_shipped": False,
        "native_human_rating_records_shipped": False,
        "original_collected_multimodal_inputs_shipped": False,
        "released_complete_verl_runtime": False,
        "released_entrypoint_operational_as_standalone_checkout": False,
        "paper_inference_temperature_matches_source": False,
        "paper_sharpe_formula_matches_source": False,
        "audit_called_llm_or_paid_external_api": False,
        "buy_hold_reference_engine_validation": (
            "cent-rounded reconstruction checked against Backtrader 1.9.78.123 using the "
            "pinned current test-price inputs; maximum observed differences were below "
            "0.00001 percentage point ARR, 0.0000002 SR, and 0.000002 percentage point MDD"
        ),
        "interpretation": (
            "The release genuinely preserves 2,615 dated prompts and reward labels, the reward "
            "formula, tool/reward code, and a partial VERL integration. Current Yahoo prices "
            "reproduce 523 labels exactly and 2,612/2,615 BUY/HOLD/SELL regimes; an exact released-"
            "semantics Buy-and-Hold reconstruction matches only 1/34 repeated paper cells at "
            "display precision. This is component evidence, not AlphaQuanter replication: all "
            "756 agent/cost/human-rating cells lack native checkpoints, actions, seed outputs, "
            "logs, or ratings; the paper test split and original multimodal snapshot are absent."
        ),
        "source_file_sha256": {relative: sha256(source_root / relative) for relative in PINNED_SOURCE_SHA256},
        "external_label_price_sha256": LABEL_PRICE_SHA256,
        "external_test_price_sha256": TEST_PRICE_SHA256,
    }

    report = f"""# AlphaQuanter paper-level conformance audit

Overall verdict: **not reproduced**. The public release provides meaningful prompt,
reward-label, reward-function, data-collection, and partial training-framework
components, but it does not ship the trained policies, paper-test prompts, original
multimodal inputs, decisions, three-seed paths, token/cost logs, or human ratings.

## Primary sources

- Official paper: {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.

## What is genuinely established

- The two Parquets contain {len(label_rows):,} dated prompt/label rows: 395 trading
  dates per ticker for training and 128 per ticker for validation. Every prompt has
  the declared system/human roles, its date agrees with `extra_info`, and it requests
  at most eight tools. The file and `extra_info` call the validation split `test`;
  the paper's actual 2025 test split is absent.
- Applying the released seven-horizon, eta=0.8 forward-return formula to cent-rounded,
  hash-pinned current Yahoo prices gives {label_status['exact_current_yahoo_numeric_match']:,}/{len(label_rows):,}
  exact numeric matches and {sum(row['reward_regime_matches'] for row in label_rows):,}/{len(label_rows):,}
  matching BUY/HOLD/SELL reward regimes. All 640 validation regimes match. The three
  threshold crossings are documented row by row. These small differences are
  consistent with a changed adjusted-price snapshot and are not evidence of paper error.
- The audit reconstructs the released Backtrader market baseline exactly: cent-rounded
  OHLC, next-open order execution, repeated daily BUY orders using 90% of remaining
  cash, 0.1% commission, and the released ARR/SR/MDD formulas. On the current 2025
  Yahoo snapshot, only {result_status['exact_displayed_precision_match_current_yahoo']}/34 repeated B&H cells matches at the paper's
  displayed precision; the match is rolling-window TSLA ARR. This is a baseline
  component check, not an agent result.

## Why AlphaQuanter is not reproduced

- The audit enumerates all {len(conformance):,} numeric cells in Tables 5--8 and 10--14.
  The 34 B&H cells are recomputed; {result_status['mismatch_against_pinned_current_yahoo']} differ on current inputs. The other 756 cells are
  unverifiable because no trained checkpoint, generated action path, per-seed trial,
  baseline output, token/cost log, or individual human rating is shipped.
- The release's `test.parquet` is the paper's 2024 validation split. No 2025 test
  Parquet is present. The paper states 122 test trading days, while the current
  exchange-calendar retrieval has 121 observations in the stated inclusive bounds.
- The checkout contains 31 tracked files and is a patch over VERL, not a standalone
  training tree: `run.sh` invokes absent `verl.trainer.main_ppo`; collection and
  evaluation use `/path/to/collected_data/`; documentation points to a plural
  `recipes/stock_trading` path that is not in the tree.
- The paper says deterministic inference at temperature 0, but `run.sh` validates at
  temperature 1.0/top-p 0.6. It reports means over three random seeds but releases no
  seed values or driver. The paper's Sharpe definition is unscaled mean/sample-std;
  source evaluation uses population std and multiplies by sqrt(number of rows).
- The rolling paper says three calendar months stepped seven days; source evaluation
  uses 60 observations stepped five rows and is hardcoded to the 128-row 2024
  validation split. The audit uses that released source behavior for its diagnostic.
- Table 5 disagrees with detailed Tables 10--11 in three displayed ARR cells by 0.01
  percentage point: FinRLA2C MSFT, FinRLA2C NVDA, and FinRLPPO MSFT.

Run `scripts/audit_alphaquanter_paper.py` to regenerate this package. Use `--strict`
when CI should fail until native checkpoints/actions, original inputs, seed protocol,
logs/ratings, and paper-test paths reproduce the published results.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(os.environ.get("ALPHAQUANTER_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/alphaquanter_source")),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(os.environ.get("ALPHAQUANTER_PAPER_PDF", "/nfs/roberts/scratch/pi_btk22/zc362/alphaquanter_paper.pdf")),
    )
    parser.add_argument(
        "--label-price-root",
        type=Path,
        default=Path(os.environ.get("ALPHAQUANTER_LABEL_PRICE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/alphaquanter_yahoo_prices")),
    )
    parser.add_argument(
        "--test-price-root",
        type=Path,
        default=Path(os.environ.get("ALPHAQUANTER_TEST_PRICE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/alphaquanter_yahoo_test_prices")),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/alphaquanter",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.paper_pdf.resolve(),
        args.label_price_root.resolve(),
        args.test_price_root.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
