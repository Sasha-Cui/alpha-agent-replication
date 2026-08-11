#!/usr/bin/env python3
"""Audit QuantHarness paper results against its pinned public release.

This fail-closed audit enumerates every numeric cell in paper Tables 1 and 2,
checks the released 1-hour and 4-hour segment corpus, reconstructs the paper's
linear-regression accuracy baseline, and records what cannot be reproduced.
It never calls an LLM or treats an inferred alignment/internal arithmetic
identity as a native system reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd


SOURCE_COMMIT = "00a88cbbc3b946cbdf506038545d6b5c2df6a344"
SOURCE_URL = "https://github.com/Y-Research-SBU/QuantAgent"
PAPER_URL = "https://arxiv.org/pdf/2509.09995v4"
PAPER_SHA256 = "751e6e7274bbf1fd5179153a28d2d29817c704b5d9b714b04ba57bd739cafda2"
BENCHMARK_TREE_SHA256 = "dfee104e3df70179e87037c2ba8620a2d952e0be337eb01741593f8918d306cc"
ACCURACY_DISPLAY_TOLERANCE = 0.05 + 1e-12
PERCENT_DISPLAY_TOLERANCE = 0.005 + 1e-12
RETURN_DISPLAY_TOLERANCE = 0.0005 + 1e-12
ASSETS_4H = ("BTC", "CL", "DJI", "ES", "VIX", "NQ", "QQQ", "SPX")

PINNED_SOURCE_SHA256 = {
    "README.md": "c1d9fe4d1f46302dddf0c9b7db76678a8cab73d1c186b8a1b3e74608b3fc4417",
    "default_config.py": "5de87cf7a1e5bf7dbab70a2cb72dfec2162dd70ef790a475b72f525f10e8bb0c",
    "web_interface.py": "ca5f88b8abe8d133a8d8b0bfb4183c4934dabd8d3f89b55030671bb43a113641",
    "decision_agent.py": "e55446b9edf2c273992987ca6b3fc5d55e366a7afbff23a564b0c5b6abeb3212",
    "indicator_agent.py": "318a5b5e3aa2611852d3a7ddd088ed986102d96462b3e96b927247af6be1b0cd",
    "pattern_agent.py": "0c581d97249b4c60a004f37f18204dd618fe16b0637c5bb0c1ee677375261dd7",
    "trend_agent.py": "951edc675531ceec9579c5c82d26141c93fb5908ee18b90a34ba6b5ffa778bad",
    "trading_graph.py": "280f1dfad1b9d6d73e3d57d7dc4497c2353e6fb19169c1a28d7d9332ab91f1da",
    "static_util.py": "6f6e2f30a587bd306274f1a532e8a389d16805bcf1a5b43de8d974288d096e05",
    "graph_util.py": "5d0b64dea20f9ece985b2cb3d395dd45a80b119d947db5bd5870f7e171120bf1",
    "requirements.txt": "e7ae5c5ba744bdb13317d3bf093d2f69bca4da2403c7abc860db32cd868d06bc",
}


# table|asset|method|Sharpe|Sortino|Cumulative Return %|Max Drawdown %
TABLE_1_TEXT = """
1|AAPL|LR|0.044|0.068|10.21|-29.59
1|AAPL|XGBoost|-0.241|-0.372|-5.35|-8.23
1|AAPL|TradingAgent|-0.189|-0.245|-13.69|15.25
1|AAPL|Our|-0.155|-0.264|-22.51|-25.44
1|AMZN|LR|0.298|0.709|153.29|-13.60
1|AMZN|XGBoost|-0.248|-0.324|-6.82|-10.31
1|AMZN|TradingAgent|0.199|0.482|20.53|4.85
1|AMZN|Our|0.236|0.502|44.85|-17.31
1|DJI|LR|0.332|0.779|41.46|-3.12
1|DJI|XGBoost|0.320|0.751|3.87|-2.61
1|DJI|TradingAgent|0.194|0.332|5.82|2.34
1|DJI|Our|0.271|0.590|15.50|-3.12
1|ES|LR|0.430|0.953|74.50|-5.90
1|ES|XGBoost|0.596|0.807|9.41|-1.88
1|ES|TradingAgent|0.017|0.030|1.25|8.55
1|ES|Our|0.339|0.661|25.43|-4.72
1|QQQ|LR|0.250|0.415|59.16|-10.74
1|QQQ|XGBoost|0.684|1.604|15.54|-2.01
1|QQQ|TradingAgent|0.067|0.112|3.82|3.66
1|QQQ|Our|0.516|0.000|1.44|-0.27
1|SPX|LR|0.467|1.017|77.78|-5.12
1|SPX|XGBoost|1.266|6.048|15.34|-0.37
1|SPX|TradingAgent|-0.158|-0.226|-6.11|7.68
1|SPX|Our|0.179|0.301|12.52|-8.24
1|NQ|LR|0.246|0.399|59.11|-11.53
1|NQ|XGBoost|-0.072|-0.108|-2.00|-5.10
1|NQ|TradingAgent|-0.092|-0.114|-5.04|9.26
1|NQ|Our|0.190|0.289|19.76|-5.46
1|VIX|TradingAgent|-0.129|-0.189|-30.40|32.28
1|VIX|Our|-0.141|-0.460|-38.70|-41.14
"""
TABLE_1_METRICS = ("sharpe", "sortino", "cumulative_return_pct", "max_drawdown_pct")


# asset|method|accuracy %|delta accuracy % (blank for baseline)|Rcc|Rmax|Rmin
TABLE_2_TEXT = """
BTC|Baseline|45.0||-0.009|1.220|-1.245
BTC|LR|46.0|2.2|-0.066|1.245|-1.210
BTC|XGBoost|45.3|0.7|-0.050|1.218|-1.331
BTC|Our|50.7|12.7|0.089|1.232|-1.212
CL|Baseline|41.0||-0.373|0.970|-1.348
CL|LR|54.3|32.4|-0.114|1.178|-1.141
CL|XGBoost|40.0|-2.4|-0.056|0.958|-1.151
CL|Our|55.0|34.1|-0.008|1.200|-1.119
DJI|Baseline|47.0||0.048|0.755|-0.793
DJI|LR|52.0|10.6|0.149|0.790|-0.725
DJI|XGBoost|47.3|0.6|-0.020|0.874|-0.660
DJI|Our|52.3|11.3|0.163|0.891|-0.649
ES|Baseline|51.0||-0.048|0.538|-0.552
ES|LR|43.0|-15.7|0.032|0.553|-0.546
ES|XGBoost|52.0|2.0|-0.182|0.440|-0.644
ES|Our|55.0|7.8|0.179|0.613|-0.485
VIX|Baseline|46.3||0.059|3.259|-3.157
VIX|LR|48.7|5.2|-0.140|3.407|-3.099
VIX|XGBoost|53.3|15.1|0.161|3.325|-3.110
VIX|Our|54.7|18.1|0.458|3.872|-2.851
NQ|Baseline|43.7||-0.140|0.646|-0.793
NQ|LR|48.7|11.4|0.147|0.782|-0.670
NQ|XGBoost|47.3|8.2|-0.007|0.706|-0.753
NQ|Our|55.3|26.5|0.216|0.814|-0.639
QQQ|Baseline|47.3||-0.048|0.930|-1.017
QQQ|LR|56.0|18.4|0.175|1.113|-0.849
QQQ|XGBoost|52.7|11.4|0.210|1.206|-0.973
QQQ|Our|59.7|26.2|0.211|1.052|-0.881
SPX|Baseline|47.3||-0.162|0.719|-0.862
SPX|LR|59.7|26.2|0.377|0.960|-0.648
SPX|XGBoost|60.0|26.8|0.050|0.782|-0.712
SPX|Our|63.7|34.6|0.341|0.965|-0.641
"""
TABLE_2_METRICS = ("accuracy_pct", "delta_accuracy_pct", "rcc", "rmax", "rmin")


BENCHMARK_PROPERTIES = {
    ("4h", "BTC"): ("2023-04-01", "2025-06-23", 5000),
    ("4h", "CL"): ("2022-04-25", "2025-06-19", 5000),
    ("4h", "DJI"): ("2015-08-26", "2025-05-16", 5000),
    ("4h", "ES"): ("2022-04-19", "2025-06-19", 5000),
    ("4h", "NQ"): ("2022-04-19", "2025-06-19", 5000),
    ("4h", "QQQ"): ("2015-08-24", "2025-05-16", 5000),
    ("4h", "SPX"): ("2015-08-25", "2025-05-16", 5000),
    ("4h", "VIX"): ("2020-10-20", "2025-08-27", 5000),
    ("1h", "BTC"): ("2025-02-21", "2025-09-13", 5000),
    ("1h", "CL"): ("2024-11-12", "2025-09-10", 5000),
    ("1h", "DJI"): ("2022-11-14", "2025-09-02", 5000),
    ("1h", "ES"): ("2024-11-11", "2025-09-10", 5000),
    ("1h", "NQ"): ("2024-11-11", "2025-09-10", 5000),
    ("1h", "QQQ"): ("2022-11-14", "2025-09-02", 5000),
    ("1h", "SPX"): ("2022-11-14", "2025-09-02", 5000),
    ("1h", "DAX"): ("2024-10-21", "2025-09-22", 5000),
}


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


def git_files(root: Path) -> List[str]:
    output = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in output.splitlines() if line]


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_result_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in TABLE_1_TEXT.strip().splitlines():
        table, asset, method, *values = line.split("|")
        if len(values) != 4:
            raise ValueError(f"Malformed Table 1 row: {line}")
        for metric, value in zip(TABLE_1_METRICS, values):
            rows.append(
                {
                    "paper_table": int(table),
                    "asset": asset,
                    "method": method,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    for line in TABLE_2_TEXT.strip().splitlines():
        asset, method, *values = line.split("|")
        if len(values) != 5:
            raise ValueError(f"Malformed Table 2 row: {line}")
        for metric, value in zip(TABLE_2_METRICS, values):
            if not value:
                continue
            rows.append(
                {
                    "paper_table": 2,
                    "asset": asset,
                    "method": method,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    return rows


def table_2_records() -> List[Dict[str, Any]]:
    records = []
    for line in TABLE_2_TEXT.strip().splitlines():
        asset, method, accuracy, delta, rcc, rmax, rmin = line.split("|")
        records.append(
            {
                "asset": asset,
                "method": method,
                "accuracy_pct": float(accuracy),
                "delta_accuracy_pct": None if not delta else float(delta),
                "rcc": float(rcc),
                "rmax": float(rmax),
                "rmin": float(rmin),
            }
        )
    return records


def natural_csv_files(directory: Path) -> List[Path]:
    files = list(directory.glob("*.csv"))

    def number(path: Path) -> int:
        match = re.search(r"_(\d+)\.csv$", path.name)
        if not match:
            raise ValueError(f"Unexpected benchmark filename: {path}")
        return int(match.group(1))

    return sorted(files, key=number)


def benchmark_directory(source_root: Path, horizon: str, asset: str) -> Path:
    base = source_root / "benchmark"
    return base / "1h" / asset.lower() if horizon == "1h" else base / asset.lower()


def benchmark_tree_hash(source_root: Path) -> str:
    digest = hashlib.sha256()
    for relative in sorted(path for path in git_files(source_root) if path.startswith("benchmark/")):
        digest.update(f"{sha256(source_root / relative)}  {relative}\n".encode())
    return digest.hexdigest()


def load_4h_arrays(source_root: Path) -> Dict[str, np.ndarray]:
    arrays: Dict[str, np.ndarray] = {}
    for asset in ASSETS_4H:
        files = natural_csv_files(benchmark_directory(source_root, "4h", asset))
        values = [
            pd.read_csv(path)[["Close", "High", "Low"]].to_numpy(dtype=float)
            for path in files
        ]
        array = np.stack(values)
        if array.shape != (100, 100, 3):
            raise RuntimeError(f"Unexpected {asset} benchmark shape: {array.shape}")
        arrays[asset] = array
    return arrays


def linear_regression_directions(close: np.ndarray, window_end: int) -> np.ndarray:
    """Return slope>0 using an OLS line over 40 closes ending before window_end."""
    values = close[:, window_end - 40 : window_end]
    x = np.arange(40, dtype=float)
    centered_x = x - x.mean()
    slopes = ((values - values.mean(axis=1, keepdims=True)) * centered_x).sum(axis=1)
    return slopes > 0


def directional_accuracy(
    close: np.ndarray, directions_long: np.ndarray, reference_index: int = 96
) -> Tuple[int, float]:
    future = close[:, 97:100]
    correct = np.where(
        directions_long[:, None],
        future > close[:, reference_index, None],
        future < close[:, reference_index, None],
    )
    hits = int(correct.sum())
    return hits, 100.0 * hits / 300.0


def extrema_returns(
    values: np.ndarray, directions_long: np.ndarray, reference_index: int = 96
) -> Tuple[float, float]:
    close = values[:, :, 0]
    high = values[:, :, 1]
    low = values[:, :, 2]
    current = close[:, reference_index]
    best = np.where(
        directions_long,
        (high[:, 97:100].max(axis=1) / current - 1.0) * 100.0,
        (1.0 - low[:, 97:100].min(axis=1) / current) * 100.0,
    )
    worst = np.where(
        directions_long,
        (low[:, 97:100].min(axis=1) / current - 1.0) * 100.0,
        (1.0 - high[:, 97:100].max(axis=1) / current) * 100.0,
    )
    return float(best.mean()), float(worst.mean())


def lr_alignment_audit(arrays: Mapping[str, np.ndarray]) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int]]]:
    records = table_2_records()
    published = {
        row["asset"]: row["accuracy_pct"] for row in records if row["method"] == "LR"
    }
    rows = []
    for asset in ASSETS_4H:
        close = arrays[asset][:, :, 0]
        described = linear_regression_directions(close, 97)
        inferred = linear_regression_directions(close, 94)
        described_hits, described_value = directional_accuracy(close, described)
        inferred_hits, inferred_value = directional_accuracy(close, inferred)
        published_value = published[asset]
        rows.append(
            {
                "asset": asset,
                "published_accuracy_pct": published_value,
                "paper_described_feature_rows_zero_based": "57:97",
                "paper_described_reference_close_index": 96,
                "paper_described_correct_hits_of_300": described_hits,
                "paper_described_accuracy_pct": described_value,
                "paper_described_absolute_error": abs(published_value - described_value),
                "paper_described_status": (
                    "display_match"
                    if abs(published_value - described_value) <= ACCURACY_DISPLAY_TOLERANCE
                    else "mismatch"
                ),
                "inferred_feature_rows_zero_based": "54:94",
                "inferred_reference_close_index": 96,
                "undocumented_feature_gap_rows": "94:97",
                "inferred_correct_hits_of_300": inferred_hits,
                "inferred_accuracy_pct": inferred_value,
                "inferred_absolute_error": abs(published_value - inferred_value),
                "inferred_status": (
                    "display_match_only_with_undocumented_three_bar_gap"
                    if abs(published_value - inferred_value) <= ACCURACY_DISPLAY_TOLERANCE
                    else "mismatch"
                ),
            }
        )

    # Exhaust every 40-close window ending no later than the current close and
    # every possible reference close before the three outcomes. Compare at the
    # paper's one-decimal precision.
    published_vector = np.asarray([published[asset] for asset in ASSETS_4H])
    direction_cache = {
        end: {
            asset: linear_regression_directions(arrays[asset][:, :, 0], end)
            for asset in ASSETS_4H
        }
        for end in range(40, 98)
    }
    exact_alignments: List[Tuple[int, int]] = []
    for end in range(40, 98):
        for reference in range(97):
            values = []
            for asset in ASSETS_4H:
                _, value = directional_accuracy(
                    arrays[asset][:, :, 0], direction_cache[end][asset], reference
                )
                values.append(round(value, 1))
            if np.array_equal(np.asarray(values), published_vector):
                exact_alignments.append((end, reference))
    return rows, exact_alignments


def benchmark_inventory(source_root: Path) -> List[Dict[str, Any]]:
    rows = []
    expected_columns = ("Datetime", "Close", "High", "Low", "Open", "Volume")
    for (horizon, asset), (paper_start, paper_end, paper_bars) in BENCHMARK_PROPERTIES.items():
        directory = benchmark_directory(source_root, horizon, asset)
        files = natural_csv_files(directory)
        frames = []
        hashes = []
        numbers = []
        monotonic = True
        unique_within_file = True
        columns_match = True
        row_counts = []
        for path in files:
            frame = pd.read_csv(path)
            timestamps = pd.to_datetime(frame["Datetime"])
            frames.append(frame)
            hashes.append(sha256(path))
            numbers.append(int(re.search(r"_(\d+)\.csv$", path.name).group(1)))
            row_counts.append(len(frame))
            monotonic = monotonic and timestamps.is_monotonic_increasing
            unique_within_file = unique_within_file and not timestamps.duplicated().any()
            columns_match = columns_match and tuple(frame.columns) == expected_columns
        combined = pd.concat(frames, ignore_index=True)
        timestamps = pd.to_datetime(combined["Datetime"])
        observed_start = timestamps.min().date().isoformat()
        observed_end = timestamps.max().date().isoformat()
        sample_digest = hashlib.sha256()
        for path, file_hash in zip(files, hashes):
            relative = path.relative_to(source_root).as_posix()
            sample_digest.update(f"{file_hash}  {relative}\n".encode())
        rows.append(
            {
                "horizon": horizon,
                "asset": asset,
                "paper_full_panel_start_date": paper_start,
                "released_segment_union_start_date": observed_start,
                "start_date_match": observed_start == paper_start,
                "paper_full_panel_end_date": paper_end,
                "released_segment_union_end_date": observed_end,
                "end_date_match": observed_end == paper_end,
                "paper_full_panel_bars": paper_bars,
                "released_segment_files": len(files),
                "released_rows_total_with_overlap": sum(row_counts),
                "released_distinct_timestamps": int(timestamps.nunique()),
                "minimum_rows_per_segment": min(row_counts),
                "maximum_rows_per_segment": max(row_counts),
                "file_numbers_1_through_100_complete": numbers == list(range(1, 101)),
                "all_segments_monotonic": monotonic,
                "all_timestamps_unique_within_segment": unique_within_file,
                "columns_match_ohlcv_schema": columns_match,
                "duplicate_file_payloads": len(hashes) - len(set(hashes)),
                "sampled_segment_tree_sha256": sample_digest.hexdigest(),
                "status": (
                    "released_sampled_segments_complete_endpoints_match_full_panel_absent"
                    if observed_start == paper_start
                    and observed_end == paper_end
                    and len(files) == 100
                    and min(row_counts) == max(row_counts) == 100
                    else "released_benchmark_mismatch"
                ),
            }
        )
    return sorted(rows, key=lambda row: (row["horizon"], row["asset"]))


def source_inventory(source_root: Path) -> List[Dict[str, Any]]:
    rows = []
    for relative in git_files(source_root):
        if relative.startswith("benchmark/"):
            continue
        path = source_root / relative
        if relative.startswith("assets/") or relative.startswith("templates/assets/"):
            role = "static_illustration_or_web_asset_not_numeric_result_path"
        elif relative.startswith("tests/"):
            role = "provider_integration_test_not_paper_benchmark_test"
        elif relative.endswith((".py", ".html")):
            role = "framework_or_web_interface_source"
        else:
            role = "documentation_configuration_or_license"
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "role": role,
            }
        )
    return rows


def source_config_audit(source_root: Path) -> List[Dict[str, Any]]:
    config = (source_root / "default_config.py").read_text(encoding="utf-8")
    web = (source_root / "web_interface.py").read_text(encoding="utf-8")
    decision = (source_root / "decision_agent.py").read_text(encoding="utf-8")
    readme = (source_root / "README.md").read_text(encoding="utf-8")
    requirements = (source_root / "requirements.txt").read_text(encoding="utf-8")
    tracked = set(git_files(source_root))
    checks = {
        "agent_model": '"agent_llm_model": "gpt-4o-mini"' in config,
        "graph_model": '"graph_llm_model": "gpt-4o"' in config,
        "temperatures": config.count('"agent_llm_temperature": 0.1') == 1
        and config.count('"graph_llm_temperature": 0.1') == 1,
        "active_tail45": "            df_slice = df.tail(45)" in web,
        "commented_holdout": "#     df_slice = df.tail(49).iloc[:-3]" in web,
        "long_short": '"decision": "<LONG or SHORT>"' in decision,
        "risk_ratio": "between **1.2 and 1.8**" in decision,
        "no_risk_agent": "risk_agent.py" not in tracked,
        "no_eval_source": not any(
            re.search(r"(^|/)(eval|evaluate|benchmark|backtest|experiment)(_|\.|/)", path)
            for path in tracked
            if path.endswith(".py") and not path.startswith("benchmark/")
        ),
        "requirements_unpinned": all(
            not any(token in line for token in ("==", "~=", ">=", "<="))
            for line in requirements.splitlines()
            if line.strip()
        ),
        "readme_decision_agent": "### Decision Agent" in readme,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Pinned QuantHarness source findings changed: {checks}")

    return [
        {
            "dimension": "agent_architecture",
            "paper": "IndicatorAgent, PatternAgent, TrendAgent, RiskAgent",
            "released": "indicator_agent.py, pattern_agent.py, trend_agent.py, decision_agent.py; no risk_agent.py",
            "status": "mismatch",
            "implication": "paper/source fourth-agent role and name are not the same",
        },
        {
            "dimension": "direction_and_risk_ratio_output",
            "paper": "LONG/SHORT plus risk-reward ratio in [1.2,1.8]",
            "released": "DecisionAgent prompt requires LONG/SHORT and ratio 1.2--1.8",
            "status": "match",
            "implication": "prompt-level component only",
        },
        {
            "dimension": "agent_llm_model",
            "paper": "not disclosed for the trading experiment",
            "released": "gpt-4o-mini",
            "status": "paper_underspecified",
            "implication": "paper result cannot be recreated from paper alone",
        },
        {
            "dimension": "decision_graph_llm_model",
            "paper": "not disclosed for the trading experiment",
            "released": "gpt-4o",
            "status": "paper_underspecified",
            "implication": "source default may not identify the paper run",
        },
        {
            "dimension": "llm_temperatures",
            "paper": "not disclosed",
            "released": "agent=0.1; graph=0.1",
            "status": "paper_underspecified",
            "implication": "stochastic protocol and reproducibility are not specified",
        },
        {
            "dimension": "benchmark_segment_release",
            "paper": "100 segments x 100 rows for every asset/horizon",
            "released": "all 1,600 CSVs with 100 rows each",
            "status": "match",
            "implication": "released sampled input component is substantial",
        },
        {
            "dimension": "original_5000_bar_panels",
            "paper": "5,000 source bars per asset/horizon",
            "released": "overlapping sampled segments only; 4,082 or 4,440 distinct timestamps",
            "status": "missing",
            "implication": "sampling cannot be independently rerun",
        },
        {
            "dimension": "held_out_last_three_bars",
            "paper": "last 3 of each 100-row segment withheld from inference",
            "released": "active run_analysis uses df.tail(45); a holdout slice is commented out",
            "status": "not_implemented_in_active_public_path",
            "implication": "passing a released 100-row segment to the active path would expose the outcomes",
        },
        {
            "dimension": "paper_experiment_entrypoint",
            "paper": "run 100 segments x assets x methods and score Tables 1--2/Figure 5",
            "released": "interactive web analysis only; no experiment/evaluation runner",
            "status": "missing",
            "implication": "native benchmark cannot be replayed",
        },
        {
            "dimension": "linear_regression_baseline",
            "paper": "OLS slope over recent 40 closes",
            "released": "no LR baseline/evaluator source",
            "status": "missing",
            "implication": "audit reconstructs from prose, not released evaluator code",
        },
        {
            "dimension": "xgboost_baseline",
            "paper": "TA-Lib features; random 50/50 CSV split; majority vote; HOLD discarded",
            "released": "no training/evaluation source, split, model, actions, or seed",
            "status": "missing",
            "implication": "XGBoost result is not reproducible",
        },
        {
            "dimension": "random_baseline",
            "paper": "random LONG/SHORT and ratio uniform in [1.2,1.8]",
            "released": "no baseline source, draws, or seed",
            "status": "missing",
            "implication": "random result is not reproducible",
        },
        {
            "dimension": "accuracy_evaluator",
            "paper": "three close comparisons per segment",
            "released": "no scoring implementation or prediction files",
            "status": "missing",
            "implication": "only prose-based baseline reconstruction is possible",
        },
        {
            "dimension": "rcc_rmax_rmin_evaluator",
            "paper": "risk-aware returns over three held-out candles",
            "released": "no evaluator, risk-ratio paths, exit-order convention, or result series",
            "status": "missing",
            "implication": "Rcc is not reconstructible and extrema are diagnostic only",
        },
        {
            "dimension": "agent_predictions_and_outputs",
            "paper": "segment-level directions, ratios, rationales, and aggregate results",
            "released": "no generated action, ratio, rationale, or return series",
            "status": "missing",
            "implication": "QuantHarness result cells are unverifiable",
        },
        {
            "dimension": "table_1_portfolio_paths",
            "paper": "Sharpe, Sortino, cumulative return, max drawdown",
            "released": "no portfolio/equity/return series or metric implementation",
            "status": "missing",
            "implication": "all 120 Table 1 numeric cells are unverifiable",
        },
        {
            "dimension": "table_1_aapl_amzn_inputs",
            "paper": "AAPL and AMZN rows",
            "released": "no AAPL or AMZN benchmark directory",
            "status": "missing",
            "implication": "two Table 1 asset inputs are absent",
        },
        {
            "dimension": "one_hour_result_paths",
            "paper": "Figure 5 comparisons across eight assets",
            "released": "1-hour inputs and a static figure image, but no numeric paths/predictions",
            "status": "missing",
            "implication": "Figure 5 cannot be numerically checked",
        },
        {
            "dimension": "case_study_paths",
            "paper": "SPX 8/10 case and agent-reasoning cases",
            "released": "static images; no selected segment IDs or ten prediction records",
            "status": "missing",
            "implication": "case-study claims cannot be replayed",
        },
        {
            "dimension": "dependency_lock",
            "paper": "operational implementation",
            "released": "requirements.txt has names only and no versions",
            "status": "missing",
            "implication": "environment is not reproducibly pinned",
        },
        {
            "dimension": "benchmark_tests",
            "paper": "paper experiment conformance",
            "released": "tests cover MiniMax provider integration only",
            "status": "missing",
            "implication": "no test asserts paper benchmark behavior",
        },
        {
            "dimension": "latency_and_cost_evidence",
            "paper": "HFT/real-time framing",
            "released": "no latency, token, API-cost, or throughput logs",
            "status": "missing",
            "implication": "operational HFT feasibility is not demonstrated by release artifacts",
        },
    ]


def internal_accuracy_identity() -> List[Dict[str, Any]]:
    records = table_2_records()
    baseline = {
        row["asset"]: row["accuracy_pct"] for row in records if row["method"] == "Baseline"
    }
    rows = []
    for record in records:
        if record["delta_accuracy_pct"] is None:
            continue
        implied = (record["accuracy_pct"] - baseline[record["asset"]]) / baseline[record["asset"]] * 100.0
        error = abs(record["delta_accuracy_pct"] - implied)
        rows.append(
            {
                "asset": record["asset"],
                "method": record["method"],
                "published_accuracy_pct": record["accuracy_pct"],
                "published_baseline_accuracy_pct": baseline[record["asset"]],
                "published_delta_accuracy_pct": record["delta_accuracy_pct"],
                "implied_delta_accuracy_pct": implied,
                "absolute_error": error,
                "status": (
                    "rounding_consistent_internal_identity"
                    if error <= ACCURACY_DISPLAY_TOLERANCE
                    else "paper_internal_mismatch"
                ),
            }
        )
    return rows


def paper_anomalies() -> List[Dict[str, Any]]:
    rows = []
    for line in TABLE_1_TEXT.strip().splitlines():
        _, asset, method, _, _, _, drawdown = line.split("|")
        if method == "TradingAgent" and float(drawdown) > 0:
            rows.append(
                {
                    "paper_table": 1,
                    "asset": asset,
                    "method": method,
                    "metric": "max_drawdown_pct",
                    "paper_value": float(drawdown),
                    "finding": "positive_value_under_a_lower_is_better_max_drawdown_column",
                    "interpretation": (
                        "all eight TradingAgent drawdowns are positive while every other numeric "
                        "drawdown in Table 1 is non-positive; evaluator/sign convention is unavailable"
                    ),
                }
            )
    rows.append(
        {
            "paper_table": 2,
            "asset": "SPX",
            "method": "Our",
            "metric": "delta_accuracy_pct",
            "paper_value": 34.6,
            "finding": "displayed_accuracy_cells_imply_34_7_pct_not_34_6_pct",
            "interpretation": (
                "hidden unrounded values could explain the difference, but the displayed "
                "63.7 and 47.3 accuracy cells imply 34.6723%, which rounds to 34.7%"
            ),
        }
    )
    return rows


def table_conformance(
    arrays: Mapping[str, np.ndarray], alignment_rows: Sequence[Mapping[str, Any]]
) -> List[Dict[str, Any]]:
    alignment = {row["asset"]: row for row in alignment_rows}
    records = table_2_records()
    baseline = {
        row["asset"]: row["accuracy_pct"] for row in records if row["method"] == "Baseline"
    }
    inferred_extrema: Dict[Tuple[str, str], float] = {}
    for asset in ASSETS_4H:
        direction = linear_regression_directions(arrays[asset][:, :, 0], 94)
        rmax, rmin = extrema_returns(arrays[asset], direction)
        inferred_extrema[(asset, "rmax")] = rmax
        inferred_extrema[(asset, "rmin")] = rmin

    rows = []
    for target in paper_result_rows():
        audit_value: Any = ""
        absolute_error: Any = ""
        tolerance: Any = ""
        if target["paper_table"] == 1:
            status = "unverifiable_missing_native_portfolio_or_metric_path"
            evidence = "paper_value_only_no_shipped_returns_equity_curve_or_table_1_evaluator"
        elif target["metric"] == "delta_accuracy_pct":
            record = next(
                row
                for row in records
                if row["asset"] == target["asset"] and row["method"] == target["method"]
            )
            audit_value = (
                (record["accuracy_pct"] - baseline[target["asset"]])
                / baseline[target["asset"]]
                * 100.0
            )
            absolute_error = abs(target["paper_value"] - audit_value)
            tolerance = ACCURACY_DISPLAY_TOLERANCE
            status = (
                "paper_internal_identity_match_not_independent_reproduction"
                if absolute_error <= tolerance
                else "paper_internal_identity_mismatch"
            )
            evidence = "derived_only_from_other_printed_table_2_accuracy_cells"
        elif target["method"] == "LR" and target["metric"] == "accuracy_pct":
            audit_value = alignment[target["asset"]]["paper_described_accuracy_pct"]
            absolute_error = abs(target["paper_value"] - audit_value)
            tolerance = ACCURACY_DISPLAY_TOLERANCE
            status = (
                "paper_described_recent_40_window_display_match"
                if absolute_error <= tolerance
                else "mismatch_paper_described_recent_40_window"
            )
            evidence = "released_4h_segments_plus_prose_specification_rows_57_to_96"
        elif target["method"] == "LR" and target["metric"] in {"rmax", "rmin"}:
            audit_value = inferred_extrema[(target["asset"], target["metric"])]
            absolute_error = abs(target["paper_value"] - audit_value)
            tolerance = RETURN_DISPLAY_TOLERANCE
            status = (
                "diagnostic_inferred_gap_display_match_not_native_reproduction"
                if absolute_error <= tolerance
                else "diagnostic_inferred_gap_mismatch"
            )
            evidence = (
                "released_4h_segments_plus_paper_extrema_formula_using_LR_directions_that_"
                "match_accuracy_only_with_undocumented_rows_94_to_96_gap"
            )
        else:
            status = "unverifiable_missing_native_result_or_evaluator"
            if target["method"] == "Our":
                evidence = "no_shipped_agent_predictions_risk_ratios_or_result_series"
            elif target["method"] == "XGBoost":
                evidence = "no_shipped_xgboost_code_model_split_seed_or_predictions"
            elif target["method"] == "Baseline":
                evidence = "no_shipped_random_draws_seed_risk_ratios_or_evaluator"
            else:
                evidence = "LR_Rcc_requires_unshipped_risk_ratio_and_exit_evaluator"
        rows.append(
            {
                **target,
                "audit_value": audit_value,
                "absolute_error": absolute_error,
                "display_tolerance": tolerance,
                "status": status,
                "evidence": evidence,
            }
        )
    return rows


def build_audit(source_root: Path, paper_path: Path, output_dir: Path) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official arXiv v4 PDF hash does not match the pinned primary source")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        actual = sha256(source_root / relative)
        if actual != expected:
            raise RuntimeError(f"Pinned source hash mismatch for {relative}: {actual}")
    tree_hash = benchmark_tree_hash(source_root)
    if tree_hash != BENCHMARK_TREE_SHA256:
        raise RuntimeError(f"Pinned benchmark tree hash mismatch: {tree_hash}")

    arrays = load_4h_arrays(source_root)
    alignments, exact_alignment_pairs = lr_alignment_audit(arrays)
    if exact_alignment_pairs != [(94, 96)]:
        raise RuntimeError(f"Pinned LR alignment finding changed: {exact_alignment_pairs}")
    inventory = benchmark_inventory(source_root)
    source_files = source_inventory(source_root)
    config = source_config_audit(source_root)
    identities = internal_accuracy_identity()
    anomalies = paper_anomalies()
    conformance = table_conformance(arrays, alignments)

    status_counts = Counter(row["status"] for row in conformance)
    expected_counts = {
        "unverifiable_missing_native_portfolio_or_metric_path": 120,
        "paper_internal_identity_match_not_independent_reproduction": 23,
        "paper_internal_identity_mismatch": 1,
        "mismatch_paper_described_recent_40_window": 8,
        "diagnostic_inferred_gap_display_match_not_native_reproduction": 7,
        "diagnostic_inferred_gap_mismatch": 9,
        "unverifiable_missing_native_result_or_evaluator": 104,
    }
    if dict(status_counts) != expected_counts:
        raise RuntimeError(f"Pinned result conformance counts changed: {status_counts}")
    if len(conformance) != 272:
        raise RuntimeError(f"Expected 272 numeric paper result cells, got {len(conformance)}")
    if len(inventory) != 16 or not all(row["status"].startswith("released_sampled") for row in inventory):
        raise RuntimeError("Released benchmark inventory changed")
    if Counter(int(row["released_distinct_timestamps"]) for row in inventory) != Counter({4082: 15, 4440: 1}):
        raise RuntimeError("Released benchmark overlap counts changed")
    identity_mismatches = [
        row for row in identities if row["status"] == "paper_internal_mismatch"
    ]
    if [(row["asset"], row["method"]) for row in identity_mismatches] != [("SPX", "Our")]:
        raise RuntimeError(f"Published delta-accuracy identity findings changed: {identity_mismatches}")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_1_2_conformance.csv", conformance, list(conformance[0]))
    write_csv(output_dir / "linear_regression_alignment_audit.csv", alignments, list(alignments[0]))
    write_csv(output_dir / "table_2_delta_accuracy_identity.csv", identities, list(identities[0]))
    write_csv(output_dir / "released_benchmark_inventory.csv", inventory, list(inventory[0]))
    write_csv(output_dir / "source_config_conformance.csv", config, list(config[0]))
    write_csv(output_dir / "released_source_inventory.csv", source_files, list(source_files[0]))
    write_csv(output_dir / "paper_internal_anomalies.csv", anomalies, list(anomalies[0]))

    manifest: Dict[str, Any] = {
        "audit": "QuantHarness paper v4 Tables 1--2 versus pinned public release",
        "overall_status": "not_reproduced_released_benchmark_and_lr_diagnostic_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": "arXiv:2509.09995v4",
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "source_commit_date": "2026-07-23",
        "paper_numeric_tables_audited": [1, 2],
        "paper_numeric_result_cells_total": len(conformance),
        "paper_table_cell_counts": {"1": 120, "2": 152},
        "native_paper_result_cells_reproduced": 0,
        "paper_internal_delta_identity_cells_consistent": 23,
        "paper_internal_delta_identity_cells_inconsistent": 1,
        "paper_described_lr_accuracy_cells_recomputed": 8,
        "paper_described_lr_accuracy_cells_matched": 0,
        "paper_described_lr_accuracy_cells_mismatched": 8,
        "published_lr_accuracy_cells_exact_only_with_undocumented_three_bar_feature_gap": 8,
        "lr_alignment_search_exact_pairs": [
            {"feature_window_end_exclusive": end, "reference_close_index": reference}
            for end, reference in exact_alignment_pairs
        ],
        "inferred_gap_lr_extrema_cells_recomputed": 16,
        "inferred_gap_lr_extrema_cells_display_matched": 7,
        "inferred_gap_lr_extrema_cells_mismatched": 9,
        "numeric_result_cells_unverifiable": 224,
        "table_1_numeric_cells_unverifiable": 120,
        "table_2_numeric_cells_unverifiable": 104,
        "released_benchmark_csv_files": 1600,
        "released_benchmark_rows_with_overlap": 160000,
        "released_benchmark_asset_horizon_sets": 16,
        "released_sets_with_100_segments_of_100_rows": 16,
        "released_sets_whose_union_matches_paper_date_endpoints": 16,
        "released_distinct_timestamps_by_set": Counter(
            int(row["released_distinct_timestamps"]) for row in inventory
        ),
        "original_5000_bar_panels_shipped": False,
        "benchmark_tree_sha256": tree_hash,
        "tracked_source_files_total": len(git_files(source_root)),
        "tracked_non_benchmark_files_total": len(source_files),
        "native_agent_predictions_or_return_series_shipped": False,
        "native_table_1_portfolio_paths_shipped": False,
        "native_experiment_evaluator_shipped": False,
        "native_lr_baseline_implementation_shipped": False,
        "native_xgboost_baseline_implementation_shipped": False,
        "native_random_baseline_implementation_shipped": False,
        "one_hour_numeric_result_paths_shipped": False,
        "paper_llm_models_disclosed": False,
        "paper_llm_temperatures_disclosed": False,
        "source_dependency_versions_pinned": False,
        "active_public_web_path_enforces_three_bar_holdout": False,
        "audit_called_llm_or_paid_external_api": False,
        "paper_table_1_positive_tradingagent_drawdown_anomalies": 8,
        "paper_internal_anomalies_total": len(anomalies),
        "interpretation": (
            "The release preserves a substantial benchmark component: 1,600 sampled CSVs, "
            "all expected segment sizes, and exact paper date endpoints. The paper-described "
            "40-close LR reconstruction matches 0/8 published accuracies. All 8 values match "
            "only when the feature window ends three rows before the current/reference close, "
            "an undocumented gap that is unique in a bounded exhaustive alignment search. "
            "This is forensic component evidence, not QuantHarness replication: no native "
            "predictions, risk ratios, evaluator, baselines, seeds, portfolio paths, or numeric "
            "one-hour outputs are shipped, leaving 224/272 numeric result cells unavailable."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
    }

    report = f"""# QuantHarness paper-level conformance audit

Overall verdict: **not reproduced**. The release provides unusually substantial
sampled benchmark inputs and an inspectable multi-agent web framework, but not the
paper experiment runner, predictions, risk-ratio paths, baseline implementations,
portfolio paths, random splits/seeds, or numeric one-hour result paths.

## Primary sources

- Official paper: {PAPER_URL} (arXiv v4; SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.

## What is genuinely established

- The repository ships all 1,600 advertised sampled CSVs: 16 asset/horizon sets,
  100 files per set, and 100 OHLCV rows per file. Every sampled union reaches the
  exact start and end dates printed in Tables 3--4. The overlapping samples expose
  4,082 distinct timestamps in 15 sets and 4,440 for 1-hour DAX, not the original
  5,000-bar panels, so segment sampling itself cannot be rerun.
- Reconstructing the stated LR baseline with the most recent 40 closes available
  after withholding rows 97--99 gives **0/8** Table 2 accuracy matches. A bounded
  exhaustive search finds one and only one alignment that matches all eight printed
  accuracies: feature rows 54--93, reference close row 96, outcomes rows 97--99.
  That leaves rows 94--96 as an undocumented three-bar feature gap.
- Using those inferred LR directions and the paper's best/worst OHLC formulas gives
  7/16 Rmax/Rmin display matches. The natural paper-described directions give 0/16.
  These are forensic diagnostics, not a native evaluator reproduction.
- 23/24 printed delta-accuracy cells are rounding-consistent with percentage change
  from the printed random-baseline accuracy. SPX "Our" reports +34.6%, while its
  displayed 63.7% and 47.3% accuracies imply +34.7%. Hidden unrounded values could
  explain this; either way, these are identities, not independently reproduced data.

## Why QuantHarness is not reproduced

- Every one of the 120 numeric Table 1 cells lacks a released return/equity path and
  metric evaluator. Table 1 includes AAPL and AMZN, for which no benchmark directory
  is released. The eight TradingAgent max-drawdown values are positive while every
  other numeric drawdown is non-positive; without the evaluator, the sign convention
  cannot be resolved.
- Of Table 2's 152 numeric cells, 104 have no reconstructible native result path.
  The public tree has no random or XGBoost evaluator, 50/50 split, model, predictions,
  random seed, LR code, Rcc implementation, agent predictions, or risk-ratio records.
  The remaining checked cells are either prose reconstructions, an inferred alignment,
  or identities among already printed values.
- The paper names Indicator, Pattern, Trend, and Risk agents. The source has Indicator,
  Pattern, Trend, and Decision modules and no `risk_agent.py`. Its Decision prompt does
  preserve LONG/SHORT and the 1.2--1.8 risk-ratio range.
- The paper does not disclose the trading-run LLM models or temperatures. Source defaults
  are GPT-4o-mini for agents, GPT-4o for graph/decision, and temperature 0.1 for both,
  but there is no evidence tying those mutable defaults to the published outputs.
- The active public `run_analysis` path uses `df.tail(45)`; the only slice excluding
  the final three rows is commented out. If a released 100-row benchmark segment is
  passed to that active path, the held-out outcome rows are exposed. The paper experiment
  path is absent, so this is a release-path leakage risk, not proof of how authors ran it.
- Figure 5 and the 8/10 SPX case study are released only as static images, without
  numeric predictions or selected segment identifiers. Dependencies are unpinned and
  the shipped tests cover provider integration rather than paper-benchmark behavior.

## Honest denominator

The audit enumerates all **272** numeric cells in Tables 1--2. **Zero** is counted as
a native paper-result reproduction. There are 23 internally consistent derived cells
and one displayed derived-cell mismatch, 8 LR accuracy mismatches under the stated
window, 16 inferred-gap extrema diagnostics
(7 display matches), and 224 unavailable cells. No proxy, inferred alignment, or static
figure is promoted to a faithful end-to-end result.

Run `scripts/audit_quantharness_paper.py` to regenerate this package. Use `--strict`
when CI should fail until native predictions, evaluator paths, exact configuration,
seeds/splits, portfolio series, and numeric 1-hour outputs reproduce the paper.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "QUANTHARNESS_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/quantagent_hft_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "QUANTHARNESS_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/quantagent_hft_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/quantharness",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(), args.paper_pdf.resolve(), args.output_dir.resolve()
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
