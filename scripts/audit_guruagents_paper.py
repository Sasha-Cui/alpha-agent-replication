#!/usr/bin/env python3
"""Fail-closed paper-level audit of GuruAgents (arXiv:2510.01664).

The paper PDF/source and the authors' paper-era GitHub history are separate
authorities.  Native notebook execution can reproduce the shipped workbook,
but that workbook is not silently promoted to paper-result credit when its
curves and Table 1 differ from the paper.
"""
from __future__ import annotations

import argparse
import ast
import base64
import contextlib
import csv
import hashlib
import io
import itertools
import json
import math
import os
import re
import struct
import subprocess
import sys
import tempfile
import types
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET


ARXIV_URL = "https://arxiv.org/abs/2510.01664"
SOURCE_URL = "https://github.com/yejining99/GuruAgents"
AUDIT_DATE = "2026-08-30"
PAPER_VERSION = "v1"
PAPER_VERSIONS_TOTAL = 1
PAPER_DATE = "2025-10-02T04:45:27Z"
ARXIV_API_SHA256 = "a2b2d96f43e3e9bff746ad50dba59c442df503c2bca78f7d6fd08a347f9d6005"
PAPER_PDF_SHA256 = "f0afdafbaa65bed37a4fa6e2cf064194735d78425a2312e7e063c2c33a52b4bc"
PAPER_SOURCE_SHA256 = "7893ba9e25875d5aa9a338b8c8ee1b6c1f1b11c9772cd2982c1c47f4368f2189"
PAPER_PAGES = 7
PAPER_FIGURE_HASHES = {
    "figure/cumulative_figure.png": "171b035f549dfafccb45476bcc4454a0d0f49e5a15397e90d69ec756cc35137a",
    "figure/weight.png": "2743ba64b1e6974fd3e83e68dc11010b042808adefa6490059e42601f375247c",
}
PAPER_FIGURE_DIMENSIONS = {
    "figure/cumulative_figure.png": (1615, 504),
    "figure/weight.png": (1936, 2336),
}

SOURCE_ARTIFACT_COMMIT = "74ad2e6ce2e604c73a6fc2829d48ab58fe6be050"
SOURCE_ARTIFACT_DATE = "2025-08-31T14:37:52+09:00"
SOURCE_DEVELOP_COMMIT = "df8c7d70ab4668ecfc2acae76fc561933a74fe7f"
SOURCE_ROOT_COMMIT = "f2a3e3ab22887dcdbf5ce4bde81601a283c99730"
SOURCE_REMOTE_REFS = {
    "refs/heads/develop": SOURCE_DEVELOP_COMMIT,
    "refs/heads/main": SOURCE_ARTIFACT_COMMIT,
}
SOURCE_REMOTE_REF_SNAPSHOT_SHA256 = "4b5936c6d04c8fb61b588d6c7c1ed2de4c3622826db0a5275a2223f9b182a747"
SOURCE_REACHABLE_COMMITS = 19
SOURCE_UNIQUE_PATHS = 592
SOURCE_UNIQUE_BLOBS = 628
SOURCE_PRE_RUN_COMMIT = "49ced76002cc824de9ccc0bd5d46207d7b28af23"
SOURCE_PRE_RUN_DATE = "2025-08-18T21:42:38+09:00"
SOURCE_NOTEBOOK_CODE_SHA256 = "434e3016e8f7932a63ac0b67314d43206a09b49649e3a869a0cfeddbb52b5b23"
SOURCE_WORKBOOK_SHA256 = "45d4a4d7abb5ab89b83966c2474fc8de231fa544f5b3e436f6b06e79ae18e91d"
SOURCE_NOTEBOOK_SHA256 = "e3c53f38ac37741f5989faa852b52f0a78776ccc5770c7a3cf9cf4f62acabca6"
PAPER_END = date(2025, 6, 30)
PAPER_COST_BPS = 1.0

PAPER_EFFECTIVE_START = date(2023, 11, 1)
PAPER_EFFECTIVE_END = date(2025, 8, 1)
AGENTS: dict[str, dict[str, Any]] = {
    "graham": {
        "paper_name": "Benjamin Graham",
        "file": "BenjaminGraham_agent.py",
        "directory": "graham_agent",
        "prefix": "graham",
        "tools": (
            "metric_current_ratio", "metric_debt_to_equity", "metric_interest_coverage",
            "metric_roe", "metric_asset_turnover", "metric_profit_margin",
            "metric_working_capital_ratio", "metric_valuation",
        ),
        "appendix_marker": "% ========== Benjamin Graham Prompt ==========",
        "prompt_difference": (
            "Edited presentation rather than a verbatim runtime prompt: the appendix drops the "
            "2023Q4 example and replaces the runtime private-step instruction."
        ),
    },
    "altman": {
        "paper_name": "Edward Altman",
        "file": "EdwardAltman_agent.py",
        "directory": "altman_agent",
        "prefix": "altman",
        "tools": ("metric_altman", "metric_extras"),
        "appendix_marker": "% ========== Edward Altman Prompt ==========",
        "prompt_difference": (
            "Edited presentation rather than a byte-identical runtime prompt; Markdown syntax and "
            "the runtime private-step instruction are replaced."
        ),
    },
    "greenblatt": {
        "paper_name": "Joel Greenblatt",
        "file": "JoelGreenblatt_agent.py",
        "directory": "greenblatt_agent",
        "prefix": "greenblatt",
        "tools": (
            "metric_earnings_yield", "metric_roic", "metric_safety", "metric_size_liquidity",
        ),
        "appendix_marker": "% ========== Joel Greenblatt Prompt ==========",
        "prompt_difference": (
            "Edited presentation rather than a byte-identical runtime prompt; the final runtime "
            "private-step instruction is replaced."
        ),
    },
    "piotroski": {
        "paper_name": "Joseph Piotroski",
        "file": "JosephPiotroski_agent.py",
        "directory": "piotroski_agent",
        "prefix": "piotroski",
        "tools": (
            "metric_profitability", "metric_leverage_liquidity", "metric_efficiency",
            "metric_fscore",
        ),
        "appendix_marker": "% ========== Joseph Piotroski Prompt ==========",
        "prompt_difference": (
            "Edited presentation rather than a byte-identical runtime prompt; the final runtime "
            "private-step instruction is replaced."
        ),
    },
    "buffett": {
        "paper_name": "Warren Buffett",
        "file": "WarrenBuffett_agent.py",
        "directory": "buffett_agent",
        "prefix": "buffett",
        "tools": (
            "metric_debt_to_equity", "metric_interest_coverage", "metric_roe",
            "metric_profit_margin", "metric_asset_turnover", "metric_valuation",
            "metric_fcf_yield", "metric_roce",
        ),
        "appendix_marker": "% ========== Warren Buffett Prompt ==========",
        "prompt_difference": (
            "Not verbatim: the appendix changes the opening quotation, removes the runtime sentence "
            "about macro seers and their cemetery, shortens the tone/data wording, and replaces the "
            "runtime private-step instruction."
        ),
    },
}

METRICS: tuple[tuple[str, str, int], ...] = (
    ("cagr_pct", "CAGR", 4),
    ("mean_daily", "mean (daily)", 4),
    ("std_daily", "std (daily)", 4),
    ("mean_annualized", "mean (ann.)", 4),
    ("std_annualized", "std (ann.)", 4),
    ("sharpe_daily", "Sharpe", 4),
    ("sharpe_annualized", "Sharpe (ann.)", 4),
    ("max_drawdown_pct", "MDD", 4),
    ("var_90_pct", "VaR0.9", 4),
    ("cvar_90_pct", "CVaR0.9", 4),
)

PAPER_TABLE: tuple[tuple[str, str, tuple[float, ...]], ...] = (
    ("Benjamin Graham", "Benjamin_Graham_Returns", (28.7401, .0008, .0119, .1921, .1896, .0638, 1.0132, -23.8873, -1.0563, -2.1079)),
    ("Warren Buffett", "Warren_Buffett_Returns", (42.2341, .0010, .0117, .2603, .1860, .0881, 1.3991, -22.3440, -.8934, -1.9950)),
    ("Joel Greenblatt", "Joel_Greenblatt_Returns", (19.3799, .0005, .0098, .1342, .1551, .0545, .8652, -20.7409, -.9877, -1.7126)),
    ("Joseph Piotroski", "Joseph_Piotroski_Returns", (30.9300, .0008, .0111, .2014, .1762, .0720, 1.1432, -23.0692, -1.0250, -1.9732)),
    ("Edward Altman", "Edward_Altman_Returns", (25.7406, .0007, .0114, .1744, .1817, .0605, .9598, -21.7132, -1.1024, -2.0331)),
    ("NASDAQ 100", "Benchmark_QQQ", (29.3611, .0011, .0135, .2827, .2150, .0828, 1.3151, -22.7683, -1.3911, -2.4290)),
    ("S&P 500", "Benchmark_SPY", (26.3131, .0010, .0107, .2500, .1698, .0928, 1.4728, -18.7552, -.9144, -1.8389)),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_output(source_root: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source_root), *args], check=True,
        capture_output=True, text=not binary,
    )
    return proc.stdout


def git_show(source_root: Path, commit: str, path: str) -> bytes:
    return bytes(git_output(source_root, "show", f"{commit}:{path}", binary=True))


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def notebook_code_hash(raw: bytes) -> str:
    notebook = json.loads(raw)
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"] if cell.get("cell_type") == "code"
    )
    return sha256_bytes(source.encode())


def validate_inputs(source_root: Path, paper_root: Path) -> None:
    head = str(git_output(source_root, "rev-parse", "HEAD")).strip()
    if head != SOURCE_ARTIFACT_COMMIT:
        raise RuntimeError(f"expected GuruAgents {SOURCE_ARTIFACT_COMMIT}, found {head}")
    if sha256(paper_root / "paper_v1.pdf") != PAPER_PDF_SHA256:
        raise RuntimeError("GuruAgents paper PDF hash changed")
    if sha256(paper_root / "source_v1.tar") != PAPER_SOURCE_SHA256:
        raise RuntimeError("GuruAgents paper source hash changed")
    if sha256(paper_root / "arxiv_api.xml") != ARXIV_API_SHA256:
        raise RuntimeError("GuruAgents arXiv version-history snapshot changed")
    api_text = (paper_root / "arxiv_api.xml").read_text(encoding="utf-8")
    if api_text.count("<entry>") != PAPER_VERSIONS_TOTAL or "2510.01664v1" not in api_text:
        raise RuntimeError("GuruAgents arXiv version census changed")
    if sha256(source_root / "results/multi_agent_backtest_results.xlsx") != SOURCE_WORKBOOK_SHA256:
        raise RuntimeError("GuruAgents public workbook hash changed")
    if sha256(source_root / "04_multi_agent_backtesting.ipynb") != SOURCE_NOTEBOOK_SHA256:
        raise RuntimeError("GuruAgents public backtest notebook hash changed")
    for relative, expected in PAPER_FIGURE_HASHES.items():
        path = paper_root / "source_v1" / relative
        if sha256(path) != expected or png_dimensions(path) != PAPER_FIGURE_DIMENSIONS[relative]:
            raise RuntimeError(f"GuruAgents paper figure changed: {relative}")
    for commit in (SOURCE_PRE_RUN_COMMIT, SOURCE_ARTIFACT_COMMIT):
        raw = git_show(source_root, commit, "04_multi_agent_backtesting.ipynb")
        if notebook_code_hash(raw) != SOURCE_NOTEBOOK_CODE_SHA256:
            raise RuntimeError(f"notebook code changed at {commit}")


def excel_column_index(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference)
    if not match:
        raise ValueError(f"invalid XLSX reference: {reference}")
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return ["".join(node.text or "" for node in item.findall(".//x:t", ns)) for item in root]


def _worksheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    main_ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in relationships.findall(f"{{{package_ns}}}Relationship")
    }
    for sheet in workbook.findall(".//x:sheet", main_ns):
        if sheet.attrib.get("name") == sheet_name:
            target = targets[sheet.attrib[f"{{{rel_ns}}}id"]]
            return target.lstrip("/") if target.startswith("/xl/") else f"xl/{target.lstrip('/')}"
    raise KeyError(sheet_name)


def _cell_value(cell: ET.Element, strings: Sequence[str], ns: Mapping[str, str]) -> Any:
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//x:t", ns))
    value = cell.find("x:v", ns)
    if value is None or value.text is None:
        return None
    if kind == "s":
        return strings[int(value.text)]
    if kind in {"str", "e"}:
        return value.text
    if kind == "b":
        return value.text == "1"
    number = float(value.text)
    return int(number) if number.is_integer() else number


def read_xlsx_sheet_bytes(raw: bytes, sheet_name: str) -> list[dict[str, Any]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        strings = _shared_strings(archive)
        root = ET.fromstring(archive.read(_worksheet_path(archive, sheet_name)))
        matrix: list[list[Any]] = []
        for row in root.findall(".//x:sheetData/x:row", ns):
            indexed = {
                excel_column_index(cell.attrib["r"]): _cell_value(cell, strings, ns)
                for cell in row.findall("x:c", ns)
            }
            matrix.append([indexed.get(index) for index in range(max(indexed, default=-1) + 1)])
    headers = [str(value) if value is not None else "" for value in matrix[0]]
    return [dict(zip(headers, row + [None] * (len(headers) - len(row)))) for row in matrix[1:]]


def read_xlsx_sheet(path: Path, sheet_name: str) -> list[dict[str, Any]]:
    return read_xlsx_sheet_bytes(path.read_bytes(), sheet_name)


def excel_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date(1899, 12, 30) + timedelta(days=float(value))


def percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def calculate_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    observations = [row for row in rows if row.get("normalized_value") is not None]
    returns = [
        float(row["daily_return"])
        for row in observations if row.get("daily_return") not in {None, ""}
    ]
    dates = [excel_date(row["date"]) for row in observations]
    nav = [float(row["normalized_value"]) for row in observations]
    if len(dates) < 2 or len(returns) < 2:
        raise ValueError("insufficient return path")
    elapsed_years = (dates[-1] - dates[0]).days / 365.25
    daily_mean, daily_std = mean(returns), stdev(returns)
    peak = -math.inf
    drawdowns: list[float] = []
    for value in nav:
        peak = max(peak, value)
        drawdowns.append(value / peak - 1)
    var = percentile(returns, .10)
    return {
        "sample_start": dates[0].isoformat(), "sample_end": dates[-1].isoformat(),
        "observations": len(observations), "return_observations": len(returns),
        "cagr_pct": ((nav[-1] / nav[0]) ** (1 / elapsed_years) - 1) * 100,
        "mean_daily": daily_mean, "std_daily": daily_std,
        "mean_annualized": daily_mean * 252,
        "std_annualized": daily_std * math.sqrt(252),
        "sharpe_daily": daily_mean / daily_std,
        "sharpe_annualized": daily_mean / daily_std * math.sqrt(252),
        "max_drawdown_pct": min(drawdowns) * 100,
        "var_90_pct": var * 100,
        "cvar_90_pct": mean(value for value in returns if value <= var) * 100,
        "source_notebook_annualized_return_pct": (nav[-1] ** (252 / len(observations)) - 1) * 100,
    }



def benchmark_cache_paths(source_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Load the released ETF cache in the shape expected by ``calculate_metrics``."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_csv(source_root / "data/benchmark_data.csv"):
        ticker = row.get("ticker", "")
        if ticker not in {"QQQ", "SPY"} or not row.get("date") or not row.get("price"):
            continue
        grouped[ticker].append({"date": row["date"], "price": float(row["price"])})
    for rows in grouped.values():
        rows.sort(key=lambda row: row["date"])
    if set(grouped) != {"QQQ", "SPY"}:
        raise RuntimeError("released benchmark cache does not contain QQQ and SPY")
    return grouped


def benchmark_metrics_for_window(
    paths: Mapping[str, Sequence[Mapping[str, Any]]], start: date, end: date
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for ticker, rows in paths.items():
        selected = [
            row for row in rows
            if start <= date.fromisoformat(str(row["date"])) <= end
        ]
        if len(selected) < 2:
            raise ValueError(f"insufficient {ticker} observations for {start} through {end}")
        first = float(selected[0]["price"])
        previous: float | None = None
        shaped: list[dict[str, Any]] = []
        for row in selected:
            price = float(row["price"])
            shaped.append({
                "date": date.fromisoformat(str(row["date"])),
                "normalized_value": price / first,
                "daily_return": None if previous is None else price / previous - 1,
            })
            previous = price
        results[ticker] = calculate_metrics(shaped)
    return results


def benchmark_effective_window_rows(
    source_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Recover and verify the one common cache window that yields both paper rows.

    The search is deliberately restricted to starts in the paper-stated Q4 2023
    and ends from Q2 2025 through the released cache/visible Figure 1 horizon.
    Credit is awarded only because one common window reproduces all 20 cells,
    not because different endpoints are selected metric by metric.
    """
    paths = benchmark_cache_paths(source_root)
    paper_by_ticker = {
        "QQQ": next(row for row in PAPER_TABLE if row[0] == "NASDAQ 100"),
        "SPY": next(row for row in PAPER_TABLE if row[0] == "S&P 500"),
    }
    common_dates = sorted(
        set(str(row["date"]) for row in paths["QQQ"])
        & set(str(row["date"]) for row in paths["SPY"])
    )
    starts = [
        date.fromisoformat(day) for day in common_dates
        if date(2023, 10, 1) <= date.fromisoformat(day) <= date(2023, 12, 31)
    ]
    ends = [
        date.fromisoformat(day) for day in common_dates
        if date(2025, 4, 1) <= date.fromisoformat(day) <= date(2025, 8, 15)
    ]
    candidates: list[dict[str, Any]] = []
    for start in starts:
        for end in ends:
            calculated = benchmark_metrics_for_window(paths, start, end)
            ticker_matches: dict[str, int] = {}
            absolute_error = 0.0
            for ticker, (_, _, expected_values) in paper_by_ticker.items():
                matched = 0
                for (metric, _, decimals), expected in zip(METRICS, expected_values):
                    actual = float(calculated[ticker][metric])
                    tolerance = .5 * 10 ** (-decimals) + 1e-12
                    matched += int(abs(actual - expected) <= tolerance)
                    absolute_error += abs(actual - expected)
                ticker_matches[ticker] = matched
            candidates.append({
                "start": start.isoformat(), "end": end.isoformat(),
                "matched_cells": sum(ticker_matches.values()),
                "QQQ_matched_cells": ticker_matches["QQQ"],
                "SPY_matched_cells": ticker_matches["SPY"],
                "aggregate_absolute_error": absolute_error,
            })
    candidates.sort(
        key=lambda row: (
            -int(row["matched_cells"]), float(row["aggregate_absolute_error"]),
            row["start"], row["end"],
        )
    )
    perfect = [row for row in candidates if row["matched_cells"] == 20]
    if (
        len(perfect) != 1
        or perfect[0]["start"] != PAPER_EFFECTIVE_START.isoformat()
        or perfect[0]["end"] != PAPER_EFFECTIVE_END.isoformat()
    ):
        raise RuntimeError("paper benchmark effective-window recovery is no longer unique")

    calculated = benchmark_metrics_for_window(paths, PAPER_EFFECTIVE_START, PAPER_EFFECTIVE_END)
    conformance: list[dict[str, Any]] = []
    for ticker, (strategy, sheet, expected_values) in paper_by_ticker.items():
        for (metric, paper_label, decimals), expected in zip(METRICS, expected_values):
            actual = float(calculated[ticker][metric])
            tolerance = .5 * 10 ** (-decimals) + 1e-12
            exact = abs(actual - expected) <= tolerance
            conformance.append({
                "strategy": strategy, "ticker": ticker, "sheet": sheet,
                "window_start": PAPER_EFFECTIVE_START.isoformat(),
                "window_end": PAPER_EFFECTIVE_END.isoformat(),
                "observations": calculated[ticker]["observations"],
                "return_observations": calculated[ticker]["return_observations"],
                "metric": metric, "paper_label": paper_label,
                "paper_value": expected, "regenerated_value": actual,
                "absolute_error": abs(actual - expected),
                "rounding_tolerance": tolerance,
                "status": "exact_rounding_match" if exact else "mismatch",
                "paper_result_credit": exact,
                "protocol": (
                    "released ETF cache; common recovered window; sample std; "
                    "252-day annualization; zero risk-free rate"
                ),
            })
    if len(conformance) != 20 or not all(row["paper_result_credit"] for row in conformance):
        raise RuntimeError("released benchmark cache no longer reproduces both paper rows")
    summary = {
        "search_start_region": "paper-stated Q4 2023 trading dates",
        "search_end_region": (
            "2025-04-01 through released/visible Figure 1 horizon 2025-08-15"
        ),
        "candidate_common_windows": len(candidates),
        "perfect_20_of_20_windows": len(perfect),
        "unique_recovered_start": perfect[0]["start"],
        "unique_recovered_end": perfect[0]["end"],
        "paper_caption_end": PAPER_END.isoformat(),
        "caption_end_matches_recovered_end": PAPER_END == PAPER_EFFECTIVE_END,
    }
    return conformance, candidates[:10], summary


def agent_protocol_variant_rows(source_root: Path) -> list[dict[str, Any]]:
    """Exhaust coherent public portfolio choices under the recovered paper window.

    This is adverse diagnostic evidence, not paper-result credit. The released
    notebook lags quarter-labelled portfolios and therefore cannot cover the
    recovered 2023-11-01 start. We test the necessary same-quarter interpretation,
    every current/older public portfolio choice for the five overlapping quarters,
    both released price columns, and both no-cost and paper-stated 1 bp turnover
    treatments. No metric-specific endpoint or portfolio selection is allowed.
    """
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError("GuruAgents agent-protocol audit requires pandas") from exc

    paper_by_agent = {
        key: next(row for row in PAPER_TABLE if row[0] == info["paper_name"])
        for key, info in AGENTS.items()
    }
    portfolios: dict[tuple[str, str], dict[str, tuple[date, date, dict[str, float]]]] = {}
    all_tickers: set[str] = set()
    for collection in ("results", "results_22_24"):
        for agent, info in AGENTS.items():
            periods: dict[str, tuple[date, date, dict[str, float]]] = {}
            directory = source_root / collection / info["directory"]
            for path in sorted(directory.glob(f"{info['prefix']}_portfolio_*.csv")):
                match = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})", path.name)
                if match is None:
                    continue
                seen: set[str] = set()
                raw_weights: list[tuple[str, float]] = []
                for row in read_csv(path):
                    ticker = str(row.get("Ticker", "")).strip()
                    if not ticker or ticker in seen:
                        continue
                    seen.add(ticker)
                    raw_weights.append((ticker, float(row["Weight (%)"])))
                total = sum(weight for _, weight in raw_weights)
                if not raw_weights or total == 0:
                    continue
                weights = {ticker: weight / total for ticker, weight in raw_weights}
                all_tickers.update(weights)
                periods[match.group(1)] = (
                    date.fromisoformat(match.group(1)),
                    date.fromisoformat(match.group(2)),
                    weights,
                )
            portfolios[(collection, agent)] = periods

    frame = pd.read_csv(
        source_root / "data/nasdaq100_ohlcv.csv",
        usecols=["TICKERSYMBOL", "EVAL_D", "CLOSE_", "DIV_ADJ_CLOSE"],
    )
    frame = frame[frame["TICKERSYMBOL"].astype(str).isin(all_tickers)].copy()
    frame["EVAL_D"] = pd.to_datetime(frame["EVAL_D"])
    frame = frame[
        (frame["EVAL_D"] >= "2023-10-01")
        & (frame["EVAL_D"] <= PAPER_EFFECTIVE_END.isoformat())
    ].sort_values("EVAL_D")
    frame = frame.drop_duplicates(["EVAL_D", "TICKERSYMBOL"], keep="last")
    pivots = {
        column: frame.pivot(index="EVAL_D", columns="TICKERSYMBOL", values=column).sort_index()
        for column in ("CLOSE_", "DIV_ADJ_CLOSE")
    }

    def run_variant(
        agent: str, use_older: Mapping[str, bool], price_column: str, apply_cost: bool
    ) -> dict[str, Any]:
        public_periods = portfolios[("results", agent)]
        pieces: list[Any] = []
        base = 1.0
        previous_weights: dict[str, float] = {}
        for period_key in sorted(public_periods):
            collection = "results_22_24" if use_older.get(period_key, False) else "results"
            start, end, weights = portfolios[(collection, agent)][period_key]
            if period_key == max(public_periods):
                end = PAPER_EFFECTIVE_END
            available = [ticker for ticker in weights if ticker in pivots[price_column].columns]
            prices = pivots[price_column].loc[
                (pivots[price_column].index >= pd.Timestamp(start))
                & (pivots[price_column].index <= pd.Timestamp(end)),
                available,
            ].dropna(axis=1, how="all")
            if prices.empty:
                continue
            first_prices = prices.bfill().iloc[0]
            relative = prices.ffill().divide(first_prices)
            period_value = relative.mul(
                pd.Series({ticker: weights[ticker] for ticker in prices.columns})
            ).sum(axis=1, min_count=1)
            turnover_cost = 0.0
            if apply_cost:
                turnover = .5 * sum(
                    abs(weights.get(ticker, 0.0) - previous_weights.get(ticker, 0.0))
                    for ticker in set(weights) | set(previous_weights)
                )
                turnover_cost = turnover * PAPER_COST_BPS / 10_000
            period_value = base * (1 - turnover_cost) * period_value
            pieces.append(period_value)
            base = float(period_value.dropna().iloc[-1])
            previous_weights = weights
        path = pd.concat(pieces).sort_index()
        path = path[~path.index.duplicated(keep="last")]
        path = path[
            (path.index >= pd.Timestamp(PAPER_EFFECTIVE_START))
            & (path.index <= pd.Timestamp(PAPER_EFFECTIVE_END))
        ]
        shaped: list[dict[str, Any]] = []
        previous: float | None = None
        for timestamp, value in path.items():
            numeric = float(value)
            shaped.append({
                "date": timestamp.date(), "normalized_value": numeric,
                "daily_return": None if previous is None else numeric / previous - 1,
            })
            previous = numeric
        return calculate_metrics(shaped)

    rows: list[dict[str, Any]] = []
    for agent, (_, _, paper_values) in paper_by_agent.items():
        current_periods = portfolios[("results", agent)]
        older_periods = portfolios[("results_22_24", agent)]
        overlap = sorted(
            period for period in set(current_periods) & set(older_periods)
            if period <= "2024-10-01"
        )
        if len(overlap) != 5:
            raise RuntimeError(f"expected five overlapping released periods for {agent}")
        for price_column in ("CLOSE_", "DIV_ADJ_CLOSE"):
            for apply_cost in (False, True):
                candidates: list[tuple[int, float, tuple[bool, ...], dict[str, Any]]] = []
                for flags in itertools.product((False, True), repeat=len(overlap)):
                    calculated = run_variant(agent, dict(zip(overlap, flags)), price_column, apply_cost)
                    matched = 0
                    relative_error = 0.0
                    for (metric, _, decimals), expected in zip(METRICS, paper_values):
                        actual = float(calculated[metric])
                        matched += int(abs(actual - expected) <= .5 * 10 ** (-decimals) + 1e-12)
                        relative_error += abs(actual - expected) / (abs(expected) + 1e-4)
                    candidates.append((matched, relative_error, flags, calculated))
                matched, relative_error, flags, calculated = min(
                    candidates, key=lambda item: (-item[0], item[1], item[2])
                )
                row: dict[str, Any] = {
                    "agent": paper_by_agent[agent][0], "price_column": price_column,
                    "transaction_cost": "paper_1bp_half_L1" if apply_cost else "none",
                    "portfolio_variants_evaluated": len(candidates),
                    "overlap_periods": ";".join(overlap),
                    "best_variant_older_flags": "".join("1" if flag else "0" for flag in flags),
                    "best_display_precision_matches": matched, "paper_metrics_total": len(METRICS),
                    "best_aggregate_relative_error": relative_error,
                    "complete_agent_row_reproduced": matched == len(METRICS),
                    "paper_result_credit": False,
                }
                row.update({f"best_{metric}": calculated[metric] for metric, _, _ in METRICS})
                rows.append(row)
    if len(rows) != 20 or sum(int(row["portfolio_variants_evaluated"]) for row in rows) != 640:
        raise RuntimeError("GuruAgents released-portfolio protocol census changed")
    if any(row["complete_agent_row_reproduced"] for row in rows):
        raise RuntimeError("a released GuruAgents agent protocol unexpectedly reproduces a paper row")
    return rows

def table_conformance_rows(source_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    workbook = source_root / "results/multi_agent_backtest_results.xlsx"
    paper_rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for strategy, sheet, paper_values in PAPER_TABLE:
        source_rows = read_xlsx_sheet(workbook, sheet)
        dated = [(excel_date(row["date"]), row) for row in source_rows if row.get("date") is not None]
        windows = {
            "paper_labeled_through_2025Q2": [row for day, row in dated if day <= PAPER_END],
            "full_shipped_workbook": [row for _, row in dated],
        }
        for window, rows in windows.items():
            calculated = calculate_metrics(rows)
            matched = 0
            for (metric, paper_label, decimals), expected in zip(METRICS, paper_values):
                actual = float(calculated[metric])
                tolerance = .5 * 10 ** (-decimals) + 1e-12
                exact = abs(actual - expected) <= tolerance
                matched += int(exact)
                row = {
                    "strategy": strategy, "sheet": sheet, "window": window,
                    "metric": metric, "paper_label": paper_label,
                    "paper_value": expected, "native_reproduced_value": actual,
                    "absolute_error": abs(actual - expected),
                    "rounding_tolerance": tolerance,
                    "status": "exact_rounding_match" if exact else "mismatch",
                    "paper_result_credit": bool(exact and window == "paper_labeled_through_2025Q2"),
                }
                diagnostics.append(row)
                if window == "paper_labeled_through_2025Q2":
                    paper_rows.append(dict(row))
            summaries.append({
                "strategy": strategy, "sheet": sheet, "window": window,
                "sample_start": calculated["sample_start"], "sample_end": calculated["sample_end"],
                "observations": calculated["observations"],
                "return_observations": calculated["return_observations"],
                "source_notebook_annualized_return_pct": calculated["source_notebook_annualized_return_pct"],
                "matched_metrics": matched, "total_metrics": len(METRICS),
                "full_paper_row_reproduced": matched == len(METRICS),
            })
    if len(paper_rows) != 70 or len(diagnostics) != 140 or len(summaries) != 14:
        raise RuntimeError("GuruAgents Table 1 census changed")
    return paper_rows, diagnostics, summaries


def git_tree_entries(source_root: Path, commit: str) -> list[tuple[str, str]]:
    raw = bytes(git_output(source_root, "ls-tree", "-r", "-z", commit, binary=True))
    rows: list[tuple[str, str]] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, encoded_path = item.split(b"\t", 1)
        _mode, kind, object_id = metadata.decode().split()
        if kind != "blob":
            continue
        rows.append((encoded_path.decode(errors="surrogateescape"), object_id))
    return rows


def git_blob(source_root: Path, object_id: str) -> bytes:
    return bytes(git_output(source_root, "cat-file", "blob", object_id, binary=True))


def _commit_metadata(source_root: Path, commit: str) -> dict[str, Any]:
    raw = str(git_output(
        source_root,
        "show",
        "-s",
        "--format=%H%x00%aI%x00%cI%x00%an%x00%s",
        commit,
    )).rstrip("\n")
    commit_id, author_date, committer_date, author, subject = raw.split("\0", 4)
    parents = str(git_output(source_root, "rev-list", "--parents", "-n", "1", commit)).split()[1:]
    reachable = []
    for remote_ref, tip in SOURCE_REMOTE_REFS.items():
        proc = subprocess.run(
            ["git", "-C", str(source_root), "merge-base", "--is-ancestor", commit, tip],
            check=False,
            capture_output=True,
        )
        if proc.returncode == 0:
            reachable.append(remote_ref)
    return {
        "commit": commit_id,
        "author_date": author_date,
        "committer_date": committer_date,
        "author": author,
        "subject": subject,
        "parents": "; ".join(parents),
        "reachable_remote_refs": "; ".join(reachable),
    }


def public_source_history_rows(
    source_root: Path,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    local_refs = {
        "refs/heads/main": str(git_output(source_root, "rev-parse", "refs/heads/main")).strip(),
        "refs/heads/develop": str(
            git_output(source_root, "rev-parse", "refs/remotes/origin/develop")
        ).strip(),
    }
    if local_refs != SOURCE_REMOTE_REFS:
        raise RuntimeError(f"GuruAgents public ref snapshot changed: {local_refs}")
    ref_snapshot = "".join(
        f"{ref}\t{commit}\n" for ref, commit in sorted(SOURCE_REMOTE_REFS.items())
    ).encode()
    if sha256_bytes(ref_snapshot) != SOURCE_REMOTE_REF_SNAPSHOT_SHA256:
        raise RuntimeError("GuruAgents remote-ref snapshot hash changed")

    commits = str(
        git_output(source_root, "rev-list", "--reverse", "--topo-order", "--all")
    ).splitlines()
    roots = str(git_output(source_root, "rev-list", "--max-parents=0", "--all")).splitlines()
    if len(commits) != SOURCE_REACHABLE_COMMITS or roots != [SOURCE_ROOT_COMMIT]:
        raise RuntimeError(
            f"GuruAgents history census changed: commits={len(commits)}, roots={roots}"
        )

    commit_rows = [_commit_metadata(source_root, commit) for commit in commits]
    commit_by_id = {row["commit"]: row for row in commit_rows}
    commit_position = {commit: index for index, commit in enumerate(commits)}
    path_state: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"commits": [], "blobs": set()}
    )
    blob_state: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"paths": set(), "commits": set()}
    )
    tip_trees = {
        ref: dict(git_tree_entries(source_root, commit))
        for ref, commit in SOURCE_REMOTE_REFS.items()
    }
    for commit in commits:
        for path, object_id in git_tree_entries(source_root, commit):
            path_state[path]["commits"].append(commit)
            path_state[path]["blobs"].add(object_id)
            blob_state[object_id]["paths"].add(path)
            blob_state[object_id]["commits"].add(commit)

    unique_blobs = set(blob_state)
    if len(path_state) != SOURCE_UNIQUE_PATHS or len(unique_blobs) != SOURCE_UNIQUE_BLOBS:
        raise RuntimeError(
            "GuruAgents history tree census changed: "
            f"paths={len(path_state)}, blobs={len(unique_blobs)}"
        )

    path_rows: list[dict[str, Any]] = []
    candidate_words = ("result", "backtest", "portfolio", "analysis", "execution_log", "table", "figure")
    for path, state in sorted(path_state.items()):
        appearances = sorted(state["commits"], key=commit_position.__getitem__)
        present_refs = [ref for ref, tree in tip_trees.items() if path in tree]
        path_rows.append({
            "relative_path": path,
            "unique_blob_versions": len(state["blobs"]),
            "commits_containing_path": len(appearances),
            "first_seen_commit": appearances[0],
            "first_seen_author_date": commit_by_id[appearances[0]]["author_date"],
            "last_seen_commit": appearances[-1],
            "last_seen_author_date": commit_by_id[appearances[-1]]["author_date"],
            "present_remote_refs": "; ".join(present_refs),
            "paper_artifact_candidate_name": any(word in path.lower() for word in candidate_words),
        })

    target_workbook = "results/multi_agent_backtest_results.xlsx"
    current_workbook_object = str(
        git_output(source_root, "rev-parse", f"{SOURCE_ARTIFACT_COMMIT}:{target_workbook}")
    ).strip()
    workbook_objects = sorted({
        object_id
        for object_id, state in blob_state.items()
        if target_workbook in state["paths"]
    })
    workbook_cells: list[dict[str, Any]] = []
    workbook_summaries: list[dict[str, Any]] = []
    for object_id in workbook_objects:
        state = blob_state[object_id]
        raw = git_blob(source_root, object_id)
        appearances = sorted(state["commits"], key=commit_position.__getitem__)
        exact_cells = 0
        credited_cells = 0
        sample_starts: list[str] = []
        sample_ends: list[str] = []
        for strategy, sheet, paper_values in PAPER_TABLE:
            source_rows = read_xlsx_sheet_bytes(raw, sheet)
            dated = [(excel_date(row["date"]), row) for row in source_rows if row.get("date") is not None]
            rows = [row for day, row in dated if day <= PAPER_END]
            calculated = calculate_metrics(rows)
            sample_starts.append(calculated["sample_start"])
            sample_ends.append(calculated["sample_end"])
            for (metric, paper_label, decimals), expected in zip(METRICS, paper_values):
                actual = float(calculated[metric])
                tolerance = .5 * 10 ** (-decimals) + 1e-12
                exact = abs(actual - expected) <= tolerance
                credit = exact and object_id == current_workbook_object
                exact_cells += int(exact)
                credited_cells += int(credit)
                workbook_cells.append({
                    "git_blob_sha1": object_id,
                    "blob_sha256": sha256_bytes(raw),
                    "identified_as_current_public_artifact": object_id == current_workbook_object,
                    "strategy": strategy,
                    "sheet": sheet,
                    "sample_start": calculated["sample_start"],
                    "sample_end": calculated["sample_end"],
                    "metric": metric,
                    "paper_label": paper_label,
                    "paper_value": expected,
                    "historical_workbook_value": actual,
                    "absolute_error": abs(actual - expected),
                    "rounding_tolerance": tolerance,
                    "rounding_match": exact,
                    "paper_result_credit": credit,
                    "note": "non-current historical variants are not identified as the reported paper run",
                })
        tip_locations = []
        for ref, tree in tip_trees.items():
            tip_locations.extend(f"{ref}:{path}" for path, blob in tree.items() if blob == object_id)
        workbook_summaries.append({
            "git_blob_sha1": object_id,
            "blob_sha256": sha256_bytes(raw),
            "bytes": len(raw),
            "identified_as_current_public_artifact": object_id == current_workbook_object,
            "commits_containing_blob": len(appearances),
            "first_seen_commit": appearances[0],
            "first_seen_author_date": commit_by_id[appearances[0]]["author_date"],
            "last_seen_commit": appearances[-1],
            "last_seen_author_date": commit_by_id[appearances[-1]]["author_date"],
            "paths_in_history": "; ".join(sorted(state["paths"])),
            "tip_locations": "; ".join(sorted(tip_locations)),
            "sample_start_min": min(sample_starts),
            "sample_end_max": max(sample_ends),
            "paper_table_rounding_matches": exact_cells,
            "paper_table_cells_total": len(PAPER_TABLE) * len(METRICS),
            "paper_table_cells_with_result_credit": credited_cells,
            "complete_paper_table_reproduced": exact_cells == len(PAPER_TABLE) * len(METRICS),
        })
    if len(workbook_summaries) != 4 or len(workbook_cells) != 280:
        raise RuntimeError("GuruAgents historical workbook census changed")

    notebook_rows: list[dict[str, Any]] = []
    plot_rows: list[dict[str, Any]] = []
    paper_hashes = set(PAPER_FIGURE_HASHES.values())
    for object_id, state in sorted(blob_state.items()):
        if not any(path.endswith(".ipynb") for path in state["paths"]):
            continue
        raw = git_blob(source_root, object_id)
        notebook = json.loads(raw)
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook.get("cells", [])
            if cell.get("cell_type") == "code"
        )
        image_count = 0
        exact_images = 0
        for cell_index, cell in enumerate(notebook.get("cells", [])):
            for output_index, output in enumerate(cell.get("outputs", [])):
                encoded = output.get("data", {}).get("image/png") if isinstance(output, dict) else None
                if not encoded:
                    continue
                if isinstance(encoded, list):
                    encoded = "".join(encoded)
                image = base64.b64decode(encoded)
                image_hash = sha256_bytes(image)
                exact = image_hash in paper_hashes
                image_count += 1
                exact_images += int(exact)
                plot_rows.append({
                    "notebook_git_blob_sha1": object_id,
                    "notebook_paths": "; ".join(sorted(state["paths"])),
                    "paper_relevant_multi_agent_notebook": target_workbook.replace(
                        "results/multi_agent_backtest_results.xlsx", "04_multi_agent_backtesting.ipynb"
                    ) in state["paths"],
                    "cell_index": cell_index,
                    "output_index": output_index,
                    "image_sha256": image_hash,
                    "image_bytes": len(image),
                    "exact_paper_image_match": exact,
                    "paper_result_credit": exact,
                })
        appearances = sorted(state["commits"], key=commit_position.__getitem__)
        paper_relevant = "04_multi_agent_backtesting.ipynb" in state["paths"]
        lower_code = code.lower()
        notebook_rows.append({
            "git_blob_sha1": object_id,
            "blob_sha256": sha256_bytes(raw),
            "notebook_code_sha256": sha256_bytes(code.encode()),
            "paths_in_history": "; ".join(sorted(state["paths"])),
            "commits_containing_blob": len(appearances),
            "first_seen_commit": appearances[0],
            "last_seen_commit": appearances[-1],
            "paper_relevant_multi_agent_notebook": paper_relevant,
            "code_characters": len(code),
            "embedded_png_outputs": image_count,
            "embedded_pngs_matching_paper_figures": exact_images,
            "mentions_cagr": "cagr" in lower_code,
            "mentions_var_or_cvar": "cvar" in lower_code or "value at risk" in lower_code,
            "mentions_max_drawdown": "max_drawdown" in lower_code,
            "mentions_transaction_cost": "transaction_cost" in lower_code,
            "implements_complete_paper_table_generator": all(
                term in lower_code for term in ("cagr", "cvar", "max_drawdown")
            ),
            "paper_result_credit": exact_images > 0,
        })
    if len(notebook_rows) != 20 or len(plot_rows) != 14:
        raise RuntimeError(
            f"GuruAgents historical notebook census changed: {len(notebook_rows)}, {len(plot_rows)}"
        )
    relevant_notebooks = [row for row in notebook_rows if row["paper_relevant_multi_agent_notebook"]]
    relevant_plots = [row for row in plot_rows if row["paper_relevant_multi_agent_notebook"]]
    if len(relevant_notebooks) != 3 or len(relevant_plots) != 6:
        raise RuntimeError("GuruAgents paper-relevant notebook history census changed")

    history = {
        "authority": "complete reachable history of the official GitHub repository",
        "audit_date": AUDIT_DATE,
        "remote_refs": SOURCE_REMOTE_REFS,
        "remote_ref_snapshot_sha256": SOURCE_REMOTE_REF_SNAPSHOT_SHA256,
        "branches": len(SOURCE_REMOTE_REFS),
        "tags": 0,
        "root_commit": SOURCE_ROOT_COMMIT,
        "reachable_commits": len(commits),
        "unique_paths": len(path_state),
        "unique_blobs": len(unique_blobs),
        "unique_xlsx_blobs": sum(
            any(path.endswith(".xlsx") for path in state["paths"])
            for state in blob_state.values()
        ),
        "unique_notebook_blobs": len(notebook_rows),
        "paper_relevant_multi_agent_workbook_blobs": len(workbook_summaries),
        "best_historical_workbook_table_matches": max(
            row["paper_table_rounding_matches"] for row in workbook_summaries
        ),
        "paper_table_cells_total": len(PAPER_TABLE) * len(METRICS),
        "paper_relevant_multi_agent_notebook_blobs": len(relevant_notebooks),
        "paper_relevant_historical_embedded_plots": len(relevant_plots),
        "historical_embedded_plots_matching_paper_figures": sum(
            bool(row["exact_paper_image_match"]) for row in plot_rows
        ),
        "historical_notebooks_with_complete_paper_table_generator": sum(
            bool(row["implements_complete_paper_table_generator"]) for row in notebook_rows
        ),
        "paper_result_artifact_recovered_from_history": False,
        "interpretation": (
            "All public branches, reachable commits, paths, workbook versions, and notebook versions "
            "were scanned. Historical artifacts add developmental evidence but recover neither the "
            "reported table generator nor an exact published figure or complete paper result."
        ),
    }
    return (
        history,
        commit_rows,
        path_rows,
        workbook_cells,
        workbook_summaries,
        notebook_rows,
        plot_rows,
    )


def extract_source_prompt_and_tools(path: Path) -> tuple[str, list[dict[str, str]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    prompt: str | None = None
    tools: list[dict[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "template" for target in node.targets
        ):
            prompt = str(ast.literal_eval(node.value))
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "Tool":
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
        if "name" not in keywords or "func" not in keywords:
            continue
        function = keywords["func"]
        tools.append({
            "name": str(ast.literal_eval(keywords["name"])),
            "bound_method": function.attr if isinstance(function, ast.Attribute) else ast.unparse(function),
            "description": str(ast.literal_eval(keywords["description"])),
        })
    if prompt is None:
        raise RuntimeError(f"no source prompt in {path}")
    return prompt, tools


def source_prompt_rows(source_root: Path, paper_root: Path) -> list[dict[str, Any]]:
    paper_tex = (paper_root / "source_v1/main.tex").read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for key, spec in AGENTS.items():
        path = source_root / "agents" / spec["file"]
        prompt, tools = extract_source_prompt_and_tools(path)
        start = paper_tex.index(spec["appendix_marker"])
        appendix = paper_tex[start:paper_tex.index(r"\end{tcolorbox}", start)]
        appendix_plain = re.sub(r"\\[A-Za-z]+\*?(?:\[[^]]*\])?", " ", appendix)
        appendix_tokens = set(re.findall(r"[a-z0-9_]+", appendix_plain.lower()))
        source_tokens = set(re.findall(r"[a-z0-9_]+", prompt.lower()))
        overlap = len(source_tokens & appendix_tokens) / max(1, len(source_tokens | appendix_tokens))
        tool_names = tuple(tool["name"] for tool in tools)
        if tool_names != tuple(spec["tools"]):
            raise RuntimeError(f"tool declaration changed for {key}: {tool_names}")
        missing_inputs = ""
        if key == "buffett":
            missing_inputs = (
                "CurrentRatio; WorkingCapitalRatio; CashConversion; MarginStability; "
                "BuybackYield; CapExIntensity; OwnerEarningsYield"
            )
        rows.append({
            "agent": spec["paper_name"], "source_file": f"agents/{spec['file']}",
            "source_prompt_sha256": sha256_bytes(prompt.encode()),
            "source_prompt_characters": len(prompt), "paper_appendix_prompt_present": True,
            "paper_appendix_is_verbatim_runtime_prompt": False,
            "approximate_source_appendix_token_jaccard": overlap,
            "declared_tools": len(tools), "declared_tool_names": "; ".join(tool_names),
            "scoring_implemented_as_non_llm_python": False,
            "prompt_scoring_inputs_not_returned_by_declared_tools": missing_inputs,
            "status": "edited_appendix_and_llm_performs_claimed_deterministic_scoring",
            "note": spec["prompt_difference"],
        })
    return rows


def archived_run_and_portfolio_rows(source_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    members = {
        row["TICKERSYMBOL"] for row in read_csv(source_root / "data/nasdaq100_members.csv")
    }
    run_rows: list[dict[str, Any]] = []
    portfolio_rows: list[dict[str, Any]] = []
    collections = (
        ("results", "current_paper_window_candidate_collection"),
        ("results_22_24", "older_developmental_collection"),
    )
    for collection, collection_role in collections:
      for key, spec in AGENTS.items():
        root = source_root / collection / spec["directory"]
        for analysis_path in sorted(root.glob(f"{spec['prefix']}_analysis_*.json")):
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            suffix = analysis_path.name.removeprefix(f"{spec['prefix']}_analysis_").removesuffix(".json")
            portfolio_path = root / f"{spec['prefix']}_portfolio_{suffix}.csv"
            log_path = root / f"{spec['prefix']}_execution_log_{suffix}.txt"
            if not portfolio_path.is_file() or not log_path.is_file():
                raise RuntimeError(f"incomplete archived run: {analysis_path}")
            tool_calls = [str(step.get("tool_name")) for step in analysis.get("intermediate_steps", [])]
            counts = Counter(tool_calls)
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            models = sorted(set(re.findall(r"model_name': '([^']+)'", log_text)))
            fingerprints = sorted(set(re.findall(r"system_fingerprint': '([^']+)'", log_text)))
            output = str(analysis.get("final_output", ""))
            paper_period_candidate = (
                date.fromisoformat(str(analysis["start_date"])) >= date(2023, 10, 1)
                and date.fromisoformat(str(analysis["end_date"])) <= PAPER_END
            )
            run_rows.append({
                "source_collection": collection, "collection_role": collection_role,
                "agent": spec["paper_name"], "analysis_start": analysis["start_date"],
                "analysis_end": analysis["end_date"], "archived_timestamp": analysis["timestamp"],
                "paper_period_candidate": paper_period_candidate,
                "execution_time_seconds": analysis.get("execution_time_seconds"),
                "tool_calls": len(tool_calls), "expected_tool_calls": len(spec["tools"]),
                "every_expected_tool_called_once": all(counts[name] == 1 for name in spec["tools"])
                and set(counts) == set(spec["tools"]),
                "runtime_model_snapshot": "; ".join(models),
                "runtime_system_fingerprints": "; ".join(fingerprints),
                "output_begins_with_required_table": output.lstrip().startswith("| Ticker"),
                "analysis_sha256": sha256(analysis_path), "execution_log_sha256": sha256(log_path),
                "portfolio_sha256": sha256(portfolio_path),
                "analysis_relative_path": str(analysis_path.relative_to(source_root)),
                "execution_log_relative_path": str(log_path.relative_to(source_root)),
                "portfolio_relative_path": str(portfolio_path.relative_to(source_root)),
                "paper_result_credit": False,
                "status": "archived_native_agent_run_not_identified_as_paper_figure_or_table_run",
            })

            raw = read_csv(portfolio_path)
            tickers = [(row.get("Ticker") or "").strip() for row in raw]
            weights: list[float] = []
            scores: list[float] = []
            for row in raw:
                try:
                    weights.append(float(row.get("Weight (%)", "")))
                except (TypeError, ValueError):
                    pass
                try:
                    scores.append(float(row.get("Score", "")))
                except (TypeError, ValueError):
                    pass
            nonempty = [row for row in raw if (row.get("Ticker") or "").strip()]
            unique: dict[str, dict[str, str]] = {}
            for row in nonempty:
                unique.setdefault((row.get("Ticker") or "").strip(), row)
            loader_weight_sum = sum(float(row["Weight (%)"]) for row in unique.values())
            normalized_sum = 100.0 if unique and loader_weight_sum else 0.0
            raw_sum = sum(weights)
            duplicate_count = len(tickers) - len(set(tickers))
            unknown = sorted({ticker for ticker in tickers if ticker not in members})
            final_only = output.lstrip().startswith("| Ticker")
            numeric_complete = len(weights) == len(raw) and len(scores) == len(raw)
            strict = (
                final_only and numeric_complete and duplicate_count == 0 and not unknown
                and abs(raw_sum - 100) <= 1e-9
                and all(value.is_integer() for value in weights)
                and all(0 <= value <= 1 for value in scores)
            )
            portfolio_rows.append({
                "source_collection": collection, "collection_role": collection_role,
                "agent": spec["paper_name"], "analysis_start": analysis["start_date"],
                "analysis_end": analysis["end_date"], "raw_rows": len(raw),
                "paper_period_candidate": paper_period_candidate,
                "raw_unique_tickers": len(set(tickers)), "raw_duplicate_tickers": duplicate_count,
                "raw_weight_sum": raw_sum, "raw_weights_all_integer": len(weights) == len(raw)
                and all(value.is_integer() for value in weights),
                "raw_scores_complete": len(scores) == len(raw),
                "unknown_or_blank_tickers": "; ".join(unknown),
                "source_loader_rows_after_drop_and_deduplicate": len(unique),
                "source_loader_normalizes_to_weight_sum": normalized_sum,
                "response_begins_with_only_required_table": final_only,
                "strict_prompt_output_contract_satisfied": strict,
                "portfolio_sha256": sha256(portfolio_path),
                "portfolio_relative_path": str(portfolio_path.relative_to(source_root)),
                "paper_figure_2_distribution_reproduced": False,
                "paper_result_credit": False,
            })
    period_counts = Counter(
        (row["agent"], row["analysis_start"], row["analysis_end"])
        for row in run_rows
    )
    for row in [*run_rows, *portfolio_rows]:
        row["public_same_period_variants"] = period_counts[
            (row["agent"], row["analysis_start"], row["analysis_end"])
        ]
    if len(run_rows) != 95 or len(portfolio_rows) != 95:
        raise RuntimeError(f"expected 95 GuruAgents decisions, found {len(run_rows)}")
    if sum(bool(row["paper_period_candidate"]) for row in run_rows) != 60:
        raise RuntimeError("GuruAgents paper-period archived-run census changed")
    return run_rows, portfolio_rows


def overlapping_archived_run_rows(
    source_root: Path, portfolio_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in portfolio_rows:
        grouped[(str(row["agent"]), str(row["analysis_start"]), str(row["analysis_end"]))][
            str(row["source_collection"])
        ] = row
    rows: list[dict[str, Any]] = []
    for (agent, start, end), variants in sorted(grouped.items()):
        if set(variants) != {"results", "results_22_24"}:
            continue
        current = variants["results"]
        older = variants["results_22_24"]
        current_records = read_csv(source_root / str(current["portfolio_relative_path"]))
        older_records = read_csv(source_root / str(older["portfolio_relative_path"]))
        current_tickers = [(row.get("Ticker") or "").strip() for row in current_records]
        older_tickers = [(row.get("Ticker") or "").strip() for row in older_records]
        current_set, older_set = set(current_tickers), set(older_tickers)
        union = current_set | older_set
        rows.append({
            "agent": agent,
            "analysis_start": start,
            "analysis_end": end,
            "current_portfolio_sha256": current["portfolio_sha256"],
            "older_portfolio_sha256": older["portfolio_sha256"],
            "exact_portfolio_file_match": current["portfolio_sha256"] == older["portfolio_sha256"],
            "exact_ticker_order_match": current_tickers == older_tickers,
            "exact_ticker_set_match": current_set == older_set,
            "ticker_set_jaccard": len(current_set & older_set) / len(union),
            "current_rows": len(current_records),
            "older_rows": len(older_records),
            "identified_reported_paper_variant": "neither",
            "paper_result_credit": False,
            "note": (
                "Same labeled agent-period, but run-time inputs/code lineage are incomplete; "
                "divergence is not treated as a controlled repeat experiment."
            ),
        })
    if len(rows) != 25:
        raise RuntimeError(f"expected 25 alternate GuruAgents run pairs, found {len(rows)}")
    return rows


def extract_notebook_pngs(source_root: Path) -> list[dict[str, Any]]:
    notebook = json.loads((source_root / "04_multi_agent_backtesting.ipynb").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for cell_index in (11, 12):
        for output_index, output in enumerate(notebook["cells"][cell_index].get("outputs", [])):
            encoded = output.get("data", {}).get("image/png")
            if not encoded:
                continue
            raw = base64.b64decode(encoded)
            width, height = struct.unpack(">II", raw[16:24])
            rows.append({
                "notebook_cell": cell_index, "output_index": output_index,
                "sha256": sha256_bytes(raw), "width": width, "height": height,
                "paper_image_sha256": PAPER_FIGURE_HASHES[
                    "figure/cumulative_figure.png" if cell_index == 11 else "figure/weight.png"
                ],
                "exact_paper_image_match": False,
                "paper_result_credit": False,
            })
    if len(rows) != 2:
        raise RuntimeError("expected two embedded notebook plots")
    return rows


def figure_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in (
        "Benjamin Graham", "Warren Buffett", "Joel Greenblatt", "Joseph Piotroski",
        "Edward Altman", "NASDAQ 100", "S&P 500",
    ):
        rows.append({
            "figure": "Figure 1 cumulative returns", "result_unit": name,
            "paper_units_total": 7, "released_underlying_paper_series": False,
            "native_reproduction": "released notebook curve visibly and numerically differs",
            "paper_result_credit": False,
            "status": "not_reproduced_no_matching_curve_or_paper_run_path",
        })
    for spec in AGENTS.values():
        for quarter_index in range(1, 8):
            rows.append({
                "figure": "Figure 2 portfolio weights", "result_unit": f"{spec['paper_name']} / bar {quarter_index}",
                "paper_units_total": 35, "released_underlying_paper_series": False,
                "native_reproduction": "released portfolio histories produce a different dated distribution",
                "paper_result_credit": False,
                "status": "not_reproduced_paper_plot_data_not_released",
            })
    if len(rows) != 42:
        raise RuntimeError("GuruAgents figure census changed")
    return rows


def source_artifact_rows(source_root: Path, paper_root: Path) -> list[dict[str, Any]]:
    paths = [
        "README.md", "requirements.txt", "01_single_agent_demo.ipynb", "02_meta_agent_demo.ipynb",
        "03_backtesting.ipynb", "04_multi_agent_backtesting.ipynb", "05_improved_multi_agent_backtesting.ipynb",
        "data/nasdaq100_bs_cf_is.csv", "data/nasdaq100_ohlcv.csv", "data/nasdaq100_members.csv",
        "data/benchmark_data.csv", "results/multi_agent_backtest_results.xlsx",
        "results_22_24/multi_agent_backtest_results.xlsx",
        *[f"agents/{spec['file']}" for spec in AGENTS.values()],
    ]
    rows = []
    for relative in paths:
        path = source_root / relative
        rows.append({
            "authority": "official GitHub artifact commit", "relative_path": relative,
            "bytes": path.stat().st_size, "sha256": sha256(path), "present": True,
        })
    for relative in (
        "arxiv_api.xml", "paper_v1.pdf", "source_v1.tar",
        "source_v1/figure/cumulative_figure.png", "source_v1/figure/weight.png",
    ):
        path = paper_root / relative
        rows.append({
            "authority": "arXiv v1", "relative_path": relative,
            "bytes": path.stat().st_size, "sha256": sha256(path), "present": True,
        })
    return rows


def run_native_backtest(source_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        import numpy as np  # type: ignore
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError("native GuruAgents audit requires pandas, numpy, and openpyxl") from exc

    yfinance = types.ModuleType("yfinance")
    yfinance.download = lambda *args, **kwargs: (_ for _ in ()).throw(
        RuntimeError("network disabled by paper audit")
    )
    previous_yfinance = sys.modules.get("yfinance")
    sys.modules["yfinance"] = yfinance
    notebook = json.loads((source_root / "04_multi_agent_backtesting.ipynb").read_text(encoding="utf-8"))
    namespace: dict[str, Any] = {"__name__": "guruagents_native_audit"}
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            exec(compile("".join(notebook["cells"][1]["source"]), "cell_1", "exec"), namespace)
            cls = namespace["MultiAgentBacktester"]

            def pinned_benchmark(instance: Any, force_download: bool = False) -> Any:
                frame = pd.read_csv(instance.benchmark_cache_path)
                frame["date"] = pd.to_datetime(frame["date"])
                return frame

            cls.load_benchmark_data = pinned_benchmark
            backtester = cls(
                results_dir=str(source_root / "results"),
                ohlcv_path=str(source_root / "data/nasdaq100_ohlcv.csv"),
                benchmark_cache_path=str(source_root / "data/benchmark_data.csv"),
                transaction_cost=.0001,
            )
            for cell_index in (2, 3, 4):
                exec(
                    compile("".join(notebook["cells"][cell_index]["source"]), f"cell_{cell_index}", "exec"),
                    namespace,
                )
            result = backtester.run_multi_agent_backtest()
    finally:
        if previous_yfinance is None:
            sys.modules.pop("yfinance", None)
        else:
            sys.modules["yfinance"] = previous_yfinance

    mapping = {
        "graham": "Benjamin_Graham_Returns", "buffett": "Warren_Buffett_Returns",
        "greenblatt": "Joel_Greenblatt_Returns", "piotroski": "Joseph_Piotroski_Returns",
        "altman": "Edward_Altman_Returns",
    }
    rows: list[dict[str, Any]] = []
    workbook = source_root / "results/multi_agent_backtest_results.xlsx"
    for key, sheet in mapping.items():
        got = result["agent_returns"][key].reset_index(drop=True)
        expected = pd.read_excel(workbook, sheet_name=sheet)
        columns = ("normalized_value", "daily_return", "cumulative_return")
        max_error = max(
            float(np.nanmax(np.abs(got[column].to_numpy() - expected[column].to_numpy())))
            for column in columns
        )
        dates_match = bool((pd.to_datetime(got.date).to_numpy() == pd.to_datetime(expected.date).to_numpy()).all())
        rows.append({
            "series": key, "workbook_sheet": sheet, "rows": len(got),
            "shape_match": got.shape == expected.shape, "dates_match": dates_match,
            "maximum_numeric_absolute_error": max_error,
            "shipped_workbook_series_reproduced": got.shape == expected.shape and dates_match and max_error < 1e-12,
            "paper_series_reproduced": False, "paper_result_credit": False,
        })
    for key, sheet in (("QQQ", "Benchmark_QQQ"), ("SPY", "Benchmark_SPY")):
        got = result["benchmark_results"][key].reset_index(drop=True)
        expected = pd.read_excel(workbook, sheet_name=sheet)
        columns = ("price", "normalized_value", "daily_return", "cumulative_return")
        max_error = max(
            float(np.nanmax(np.abs(got[column].to_numpy() - expected[column].to_numpy())))
            for column in columns
        )
        dates_match = bool((pd.to_datetime(got.date).to_numpy() == pd.to_datetime(expected.date).to_numpy()).all())
        rows.append({
            "series": key, "workbook_sheet": sheet, "rows": len(got),
            "shape_match": got.shape == expected.shape, "dates_match": dates_match,
            "maximum_numeric_absolute_error": max_error,
            "shipped_workbook_series_reproduced": got.shape == expected.shape and dates_match and max_error < 1e-12,
            "paper_series_reproduced": False, "paper_result_credit": False,
        })
    return rows, {
        "execution_mode": "source notebook code cells 1-4; pinned released benchmark cache injected; network disabled",
        "captured_output_sha256": sha256_bytes(captured.getvalue().encode()),
        "captured_output_lines": len(captured.getvalue().splitlines()),
        "source_workbook_series_reproduced": sum(row["shipped_workbook_series_reproduced"] for row in rows),
        "source_workbook_series_total": len(rows),
        "paper_result_credit": False,
    }


def compile_paper_source(paper_root: Path) -> dict[str, Any]:
    source = paper_root / "source_v1"
    with tempfile.TemporaryDirectory(prefix="guruagents-paper-") as temporary:
        output = Path(temporary)
        exit_codes: list[int] = []
        logs: list[str] = []
        for _ in range(2):
            proc = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={output}", "main.tex"],
                cwd=source, capture_output=True, text=True,
            )
            exit_codes.append(proc.returncode)
            logs.append(proc.stdout + proc.stderr)
        pdf = output / "main.pdf"
        if exit_codes != [0, 0] or not pdf.is_file():
            raise RuntimeError("GuruAgents arXiv source did not compile twice")
        info = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True).stdout
        match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
        pages = int(match.group(1)) if match else 0
        return {
            "exit_codes": exit_codes, "produced_pdf_pages": pages,
            "expected_pdf_pages": PAPER_PAGES, "page_count_match": pages == PAPER_PAGES,
            "warning_lines_second_pass": sum(
                any(token in line for token in ("Warning", "Overfull", "Underfull"))
                for line in logs[-1].splitlines()
            ),
            "paper_result_credit": False,
        }


def mechanism_rows() -> list[dict[str, Any]]:
    entries = (
        ("five guru role prompts", True, True, "implemented and archived, but appendix text is edited rather than verbatim"),
        ("strategy-specific metric tools", True, True, "all expected tool names occur once in each archived run"),
        ("GPT-4o backbone", True, True, "logs identify gpt-4o-2024-08-06"),
        ("deterministic scoring pipeline", False, False, "scores and weights are generated by the LLM, not a deterministic Python scorer"),
        ("identical inputs yield identical outputs", False, False, "no controlled repeats or seed; 25 same-labeled period alternatives have incomplete lineage and divergent portfolios"),
        ("LangChain execution", True, True, "five agent executors use LangChain"),
        ("LangGraph execution for reported agents", False, False, "LangGraph appears only in an unrelated meta-agent path"),
        ("NASDAQ-100 universe", True, False, "fixed 100-name file lacks historical effective dates and some outputs are outside it"),
        ("quarterly fundamental data", True, True, "95 executions across 14 distinct labeled quarters are released"),
        ("point-in-time accounting availability", False, False, "quarter labels have no filing/publication timestamps"),
        ("OHLCV and shares data", True, True, "released through 2025-08-12 without vendor/provenance metadata"),
        ("quarterly rebalance", True, True, "source uses analysis-end plus one day and 90-day holding intervals"),
        ("one-basis-point gross-turnover cost", False, False, "parameter is stored but never read by calculate_agent_returns"),
        ("portfolio weights sum to 100", False, False, "only 16 of 95 raw CSVs sum to 100; the current paper-window collection is 2 of 35"),
        ("strict four-column output", False, False, "only one archived response begins directly with the requested table"),
        ("adjusted price return path", False, False, "backtest selects the first CLOSE column, which is unadjusted CLOSE_"),
        ("NASDAQ-100 index benchmark", False, False, "released path uses QQQ ETF"),
        ("S&P 500 index benchmark", False, False, "released path uses SPY ETF"),
        ("CAGR and daily/annual moments", False, False, "paper Table 1 calculation code is not released"),
        ("VaR and CVaR", False, False, "not implemented by the released multi-agent notebook"),
        ("maximum drawdown", True, True, "notebook implements MDD; the two benchmark MDD cells match"),
        ("paper Figure 1 paths", False, False, "paper paths differ from the native notebook/workbook paths"),
        ("paper Figure 2 distributions", False, False, "paper plot visibly differs from released portfolio histories"),
        ("source environment", False, False, "requirements use unbounded lower limits and no lock/container"),
        ("paper source compilation", True, True, "arXiv source compiles twice to seven pages"),
    )
    return [
        {
            "paper_mechanism": name, "released_implementation_present": present,
            "native_or_archived_execution_verified": executed,
            "paper_mechanism_faithfully_reproduced": present and executed and name in {
                "strategy-specific metric tools", "GPT-4o backbone", "LangChain execution",
                "quarterly fundamental data", "OHLCV and shares data", "quarterly rebalance",
                "maximum drawdown", "paper source compilation",
            },
            "paper_result_credit": False, "note": note,
        }
        for name, present, executed, note in entries
    ]


def specification_gap_rows() -> list[dict[str, Any]]:
    gaps = (
        ("paper-result agent return paths", "Exact five-agent Figure 1 paths and Table 1 input series are absent; benchmark paths are recovered", "blocking"),
        ("paper Figure 2 data", "The plotted holdings/weights differ from all released result histories", "blocking"),
        ("Table 1 generator", "Released notebook omits CAGR/moments/VaR/CVaR table-generation code", "blocking"),
        ("transaction costs", "Paper says 1 bp of gross turnover; source never applies the parameter", "blocking"),
        ("point-in-time fundamentals", "No filing date or availability lag is stored", "blocking"),
        ("historical constituency", "The 100-name membership file has no effective dates", "material"),
        ("data provenance", "No vendor/query/license/retrieval manifest is supplied", "material"),
        ("benchmark identity", "Paper names indices while source uses QQQ and SPY ETFs", "blocking"),
        ("observation frequency", "Agent paths include forward-filled weekends; benchmarks use trading days", "blocking"),
        ("risk-free rate", "Sharpe convention is not specified in the paper", "material"),
        ("model determinism", "No seed/repeated-run proof; archived fingerprints vary", "blocking"),
        ("reported-run attribution", "Four workbooks and same-period alternate portfolios exist without a manifest identifying the paper run", "blocking"),
        ("runtime prompt authority", "Appendix prompts are edited versions of source templates", "material"),
        ("software environment", "No pinned dependency lock, image, or Python version", "material"),
        ("portable execution", "Agent constructors contain absolute Windows data/result paths", "material"),
        ("API cost and retry policy", "No reported cost, retry, timeout, or rate-limit configuration", "material"),
    )
    return [
        {"dimension": dimension, "missing_or_conflicting_evidence": evidence, "severity": severity,
         "resolved_by_public_sources": False}
        for dimension, evidence, severity in gaps
    ]


def internal_check_rows(
    table_rows: Sequence[Mapping[str, Any]],
    run_rows: Sequence[Mapping[str, Any]],
    portfolio_rows: Sequence[Mapping[str, Any]],
    overlapping_rows: Sequence[Mapping[str, Any]],
    history: Mapping[str, Any],
    source_root: Path,
) -> list[dict[str, Any]]:
    next(
        row for row in portfolio_rows
        if row["source_collection"] == "results"
        and row["agent"] == "Warren Buffett"
        and row["analysis_start"] == "2023-10-01"
    )
    current_portfolios = [row for row in portfolio_rows if row["source_collection"] == "results"]
    source_first = {
        row["Ticker"] for row in read_csv(
            source_root / "results/buffett_agent/buffett_portfolio_2023-10-01_2023-12-31.csv"
        )
    }
    older_first = {
        row["Ticker"] for row in read_csv(
            source_root / "results_22_24/buffett_agent/buffett_portfolio_2023-10-01_2023-12-31.csv"
        )
    }
    paper_visible = {"TXN", "AVGO", "ADP", "AMZN", "GOOGL", "META", "NVDA", "AAPL", "MSFT"}
    return [
        {"check": "official arXiv version history", "status": "exhausted_one_version",
         "evidence": "arXiv API exposes v1 only; PDF, source archive, figures, and two-pass compilation are pinned"},
        {"check": "official GitHub history", "status": "exhausted_all_public_refs",
         "evidence": f"{history['branches']} branches, {history['reachable_commits']} commits, {history['unique_paths']} paths, and {history['unique_blobs']} blobs"},
        {"check": "historical Table 1 artifacts", "status": "not_reproduced",
         "evidence": f"four workbook blobs scanned; best is {history['best_historical_workbook_table_matches']}/70 rounding matches"},
        {"check": "historical paper-style plots", "status": "not_reproduced",
         "evidence": "three versions of the paper-relevant notebook contain six plots; 0 match either paper image"},
        {"check": "Table 1 native cell reproduction", "status": "two_complete_benchmark_rows_only",
         "evidence": f"{sum(bool(row['paper_result_credit']) for row in table_rows)}/70 cells; all 20 QQQ/SPY cells regenerate from one common released-cache window"},
        {"check": "Table 1 complete rows", "status": "partial_two_benchmark_rows",
         "evidence": "2/7 rows match all ten metrics; 0/5 agent rows match"},
        {"check": "native notebook versus shipped workbook", "status": "exact_source_artifact_reproduction",
         "evidence": "all seven paths match to <1e-12, but are not the paper paths"},
        {"check": "paper horizon versus effective benchmark window", "status": "recovered_caption_contradiction",
         "evidence": "the unique common cache window reproducing all 20 benchmark cells is 2023-11-01 through 2025-08-01, not the captioned Q2 2025 endpoint"},
        {"check": "paper horizon versus source workbook", "status": "contradiction",
         "evidence": "shipped agent paths run 2024-01-01 through 2025-08-12 rather than the recovered paper-effective window"},
        {"check": "paper Figure 1 visual horizon", "status": "supports_recovered_window",
         "evidence": "paper image extends beyond Q2 2025 to approximately the recovered 2025-08-01 endpoint"},
        {"check": "Figure 2 first visible Buffett bar", "status": "contradiction",
         "evidence": f"both public variants differ; paper-only versus current={sorted(paper_visible-source_first)}, versus older={sorted(paper_visible-older_first)}"},
        {"check": "current paper-window raw portfolio weight sums", "status": "contradiction",
         "evidence": f"{sum(abs(float(row['raw_weight_sum'])-100)<=1e-9 for row in current_portfolios)}/35 sum to 100"},
        {"check": "all archived raw portfolio weight sums", "status": "contradiction",
         "evidence": f"{sum(abs(float(row['raw_weight_sum'])-100)<=1e-9 for row in portfolio_rows)}/95 sum to 100"},
        {"check": "all archived raw duplicate tickers", "status": "contradiction",
         "evidence": f"{sum(int(row['raw_duplicate_tickers'])>0 for row in portfolio_rows)}/95 contain duplicates"},
        {"check": "strict prompt output", "status": "contradiction",
         "evidence": f"{sum(bool(row['strict_prompt_output_contract_satisfied']) for row in portfolio_rows)}/95 satisfy the full contract"},
        {"check": "expected tool calls", "status": "supported_component",
         "evidence": f"{sum(bool(row['every_expected_tool_called_once']) for row in run_rows)}/95 archived runs call every declared tool once"},
        {"check": "runtime model", "status": "supported_component",
         "evidence": "all 95 logs identify gpt-4o-2024-08-06"},
        {"check": "runtime model fingerprint", "status": "determinism_not_established",
         "evidence": "three system fingerprints appear across the 95 archived runs"},
        {"check": "same-labeled period alternatives", "status": "reported_run_not_attributable",
         "evidence": f"0/{len(overlapping_rows)} portfolio files match exactly and {sum(bool(row['exact_ticker_set_match']) for row in overlapping_rows)}/{len(overlapping_rows)} ticker sets match; inputs were not controlled"},
        {"check": "transaction cost", "status": "contradiction",
         "evidence": "transaction_cost=0.0001 is declared but unused in calculate_agent_returns"},
        {"check": "agent/benchmark frequency", "status": "contradiction",
         "evidence": "paper-window agents have 540 calendar observations versus 374 benchmark trading observations"},
        {"check": "benchmark instruments", "status": "contradiction",
         "evidence": "paper labels indices; source downloads QQQ and SPY"},
        {"check": "point-in-time accounting", "status": "not_supported",
         "evidence": "quarter-end portfolios begin the next day without filing availability timestamps"},
        {"check": "Buffett scoring inputs", "status": "contradiction",
         "evidence": "seven prompt inputs are not returned by any declared Buffett tool"},
        {"check": "valuation units", "status": "implementation_defect",
         "evidence": "archived tool logs report million-scale P/E and P/B values (for example MSFT P/E 33,479,836)"},
        {"check": "price column", "status": "implementation_difference",
         "evidence": "native backtest selects CLOSE_ before DIV_ADJ_CLOSE"},
        {"check": "released README", "status": "stale_nonoperational",
         "evidence": "documents Carlisle/Driehaus and nonexistent config/backtest modules instead of the paper system"},
        {"check": "source/result chronology", "status": "qualified_provenance",
         "evidence": "all 19 commits were audited; code predates archived runs, but no public manifest identifies the reported workbook/portfolio lineage"},
    ]


def build_readme(manifest: Mapping[str, Any]) -> str:
    return f"""# GuruAgents paper-level replication audit

This directory audits the only official arXiv version of
[GuruAgents]({ARXIV_URL}) against the complete reachable history of the authors'
[source repository]({SOURCE_URL}). It is deliberately fail-closed: reproducing
a public workbook is not the same as reproducing the paper.

## Verdict

**The paper is not faithfully reproduced.** Native execution of the released
notebook reproduces all seven shipped workbook paths to floating-point error,
but that workbook does not reproduce Table 1 or either paper figure. A separate,
source-grounded protocol reconstruction does recover both benchmark rows:
released QQQ and SPY prices from 2023-11-01 through 2025-08-01 regenerate all
20 benchmark cells at the paper's four-decimal precision. This is the only
perfect common window among {manifest['benchmark_window_candidate_count']}
windows searched across the paper-stated Q4 2023 start region and the Q2-to-
Figure-1 endpoint region. It proves that the table uses ETFs and extends into
Q3 2025, despite the paper caption saying Q2 2025.

The five agent rows remain unreproduced (0/50 cells), so the overall verdict
does not become a full replication. None of the 42 audited figure units receives
paper-result credit. To test whether the public alternatives can nevertheless
recover those rows,
the audit exhausts {manifest['released_agent_protocol_variants_tested']} coherent
agent protocols: every per-quarter choice between the two released portfolio
lineages, both source price columns, and both stated-cost and no-cost treatments
under the recovered window. No complete agent row appears; the best candidate
matches only {manifest['released_agent_protocol_best_display_matches']}/10 cells.

Separately, all {manifest['source_history_reachable_commits']} commits,
{manifest['source_history_unique_paths']} paths, four versions of the multi-agent
workbook, and three versions of the paper-relevant notebook were checked. No
historical workbook exceeds 2/70 Table 1 matches, none implements the missing
complete Table 1 generator, and none of six historical notebook plots matches
either paper figure.

The release nevertheless contains valuable component evidence: 95 archived
GPT-4o-2024-08-06 agent decisions (35 in the current collection and 60 in the
older collection), full tool observations, five prompt/tool implementations,
quarterly financial/market data, portfolios, workbooks, and notebook outputs.
Every archived run calls each declared tool exactly once. These are real
source-component achievements, not a paper reproduction. Twenty-five
agent-periods have two public portfolio variants; none of those files is
identical and only four ticker sets match. Because their input/code lineage is
incomplete, they are evidence of ambiguous run attribution, not controlled
repeat trials.

## Most consequential breaks

- The paper says Q4 2023 through Q2 2025, but the unique exact benchmark window
  is 2023-11-01 through 2025-08-01 and Figure 1 visibly reaches that later
  horizon. The public agent workbook instead runs 2024-01-01 through
  2025-08-12.
- The declared 1 bp gross-turnover cost is never applied.
- Agent paths contain forward-filled calendar days while QQQ/SPY contain
  trading days; 252-day annualization is then applied to both.
- The paper names the NASDAQ-100 and S&P 500 indices, while source code uses the
  QQQ and SPY ETFs.
- The claimed deterministic scorer is performed by GPT-4o, not Python. Three
  backend fingerprints occur, there is no seed/repeat study, only 16/95 raw
  portfolios sum to 100, 17/95 contain duplicates, and 0/95 satisfy the entire
  strict output contract. In the current 35-run collection, only 2/35 sum to
  100.
- Exact five-agent Table 1 input paths, complete Table 1 generation code,
  paper Figure 1 agent paths, and paper Figure 2
  portfolio distributions are not released in any public commit. The visible
  paper distributions differ from both same-period public portfolio variants.
- Quarter labels are used as if data were available the next day; filing dates
  and historical NASDAQ-100 membership dates are absent.

## Accounting boundary

- Table 1: **{manifest['paper_table_cells_with_result_credit']}/70 cells**, **{manifest['paper_table_rows_fully_reproduced']}/7 full rows**
  (both benchmark rows; 0/5 agent rows and 0/50 agent cells).
- Figures: **0/42 audited units**.
- Exact appendix prompts: **0/5** (all are edited presentations of runtime templates).
- Native public-workbook reproduction: **7/7 series** (component/source-artifact evidence only).
- Public source history: **2/2 branches, 19/19 commits, 592/592 paths** audited.
- Effective benchmark protocol: **2023-11-01 through 2025-08-01, 20/20 cells**.
- Released agent protocol census: **{manifest['released_agent_protocol_variants_tested']} variants,
  0 complete rows; best candidate 2/10 cells**.
- Full-paper reproduction: **no**.

See `manifest.json` for the machine-readable summary and the CSV ledgers for
cell-, run-, portfolio-, prompt-, mechanism-, figure-, and gap-level evidence.
"""


def build_audit(source_root: Path, paper_root: Path, output_dir: Path) -> dict[str, Any]:
    validate_inputs(source_root, paper_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    table_rows, diagnostics, summaries = table_conformance_rows(source_root)
    benchmark_rows, benchmark_window_candidates, benchmark_window_summary = (
        benchmark_effective_window_rows(source_root)
    )
    agent_protocol_rows = agent_protocol_variant_rows(source_root)
    benchmark_by_cell = {
        (row["strategy"], row["metric"]): row for row in benchmark_rows
    }
    for row in table_rows:
        recovered = benchmark_by_cell.get((row["strategy"], row["metric"]))
        if recovered is None:
            continue
        row.update({
            "window": (
                f"recovered_effective_window_{PAPER_EFFECTIVE_START}_through_"
                f"{PAPER_EFFECTIVE_END}"
            ),
            "native_reproduced_value": recovered["regenerated_value"],
            "absolute_error": recovered["absolute_error"],
            "rounding_tolerance": recovered["rounding_tolerance"],
            "status": recovered["status"],
            "paper_result_credit": recovered["paper_result_credit"],
        })

    prompt_rows = source_prompt_rows(source_root, paper_root)
    run_rows, portfolio_rows = archived_run_and_portfolio_rows(source_root)
    overlapping_rows = overlapping_archived_run_rows(source_root, portfolio_rows)
    (
        history,
        history_commits,
        history_paths,
        historical_workbook_cells,
        historical_workbook_summaries,
        historical_notebooks,
        historical_notebook_plots,
    ) = public_source_history_rows(source_root)
    figures = figure_rows()
    embedded_plots = extract_notebook_pngs(source_root)
    artifacts = source_artifact_rows(source_root, paper_root)
    mechanisms = mechanism_rows()
    gaps = specification_gap_rows()
    native_rows, native_summary = run_native_backtest(source_root)
    paper_compile = compile_paper_source(paper_root)
    checks = internal_check_rows(
        table_rows, run_rows, portfolio_rows, overlapping_rows, history, source_root
    )
    checks.append({
        "check": "released agent portfolio protocol variants",
        "status": "no_complete_agent_row_reproduced",
        "evidence": "640 coherent variants tested across both public portfolio lineages, both source price columns, and stated/no-cost treatments; best candidate matches 2/10 cells",
    })

    outputs: dict[str, Sequence[Mapping[str, Any]]] = {
        "paper_table_1_conformance.csv": table_rows,
        "source_workbook_metric_diagnostics.csv": diagnostics,
        "agent_protocol_variant_summary.csv": agent_protocol_rows,
        "benchmark_effective_window_conformance.csv": benchmark_rows,
        "benchmark_window_search_top_candidates.csv": benchmark_window_candidates,
        "benchmark_window_search_summary.csv": [benchmark_window_summary],
        "source_workbook_window_summary.csv": summaries,
        "paper_figure_unit_conformance.csv": figures,
        "source_prompt_conformance.csv": prompt_rows,
        "archived_run_inventory.csv": run_rows,
        "archived_portfolio_validation.csv": portfolio_rows,
        "archived_overlapping_run_comparison.csv": overlapping_rows,
        "public_source_history_commits.csv": history_commits,
        "public_source_history_path_inventory.csv": history_paths,
        "historical_workbook_table_conformance.csv": historical_workbook_cells,
        "historical_workbook_summary.csv": historical_workbook_summaries,
        "historical_notebook_inventory.csv": historical_notebooks,
        "historical_notebook_plot_inventory.csv": historical_notebook_plots,
        "native_backtest_conformance.csv": native_rows,
        "notebook_embedded_plot_inventory.csv": embedded_plots,
        "source_artifact_inventory.csv": artifacts,
        "paper_mechanism_conformance.csv": mechanisms,
        "paper_specification_gaps.csv": gaps,
        "paper_internal_and_source_checks.csv": checks,
    }
    for filename, rows in outputs.items():
        write_csv(output_dir / filename, rows)

    (output_dir / "public_source_history.json").write_text(
        json.dumps(history, indent=2) + "\n", encoding="utf-8"
    )

    native_execution = {
        "paper_source_compilation": paper_compile,
        "released_source_native_backtest": native_summary,
        "native_backtest_series": native_rows,
        "full_native_paper_execution_attempted": False,
        "full_native_paper_execution_blocker": (
            "Exact five-agent paper return paths, Figure 2 portfolio data, Table 1 generator, "
            "point-in-time inputs, and applied transaction-cost path are absent from every public "
            "paper/source version; the two benchmark rows are independently regenerated."
        ),
        "public_source_history": history,
        "paper_result_credit": False,
    }
    (output_dir / "native_execution.json").write_text(
        json.dumps(native_execution, indent=2) + "\n", encoding="utf-8"
    )

    exact_cells = sum(bool(row["paper_result_credit"]) for row in table_rows)
    cells_by_strategy: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in table_rows:
        cells_by_strategy[str(row["strategy"])].append(row)
    full_rows = sum(
        len(rows) == len(METRICS) and all(bool(row["paper_result_credit"]) for row in rows)
        for rows in cells_by_strategy.values()
    )
    manifest: dict[str, Any] = {
        "audit": "GuruAgents fail-closed paper-level replication audit",
        "audit_date": AUDIT_DATE,
        "paper": {"url": ARXIV_URL, "version": PAPER_VERSION,
                  "versions_total": PAPER_VERSIONS_TOTAL, "version_history_exhausted": True,
                  "date": PAPER_DATE, "api_snapshot_sha256": ARXIV_API_SHA256,
                  "pdf_sha256": PAPER_PDF_SHA256, "source_sha256": PAPER_SOURCE_SHA256,
                  "pages": PAPER_PAGES},
        "source": {"url": SOURCE_URL, "artifact_commit": SOURCE_ARTIFACT_COMMIT,
                   "artifact_commit_date": SOURCE_ARTIFACT_DATE, "pre_run_code_commit": SOURCE_PRE_RUN_COMMIT,
                   "pre_run_code_commit_date": SOURCE_PRE_RUN_DATE,
                   "remote_refs": SOURCE_REMOTE_REFS,
                   "remote_ref_snapshot_sha256": SOURCE_REMOTE_REF_SNAPSHOT_SHA256,
                   "full_public_history_audited": True},
        "overall_status": "benchmark_protocol_recovered_20_of_70_cells_reproduced_agent_results_not_reproduced",
        "full_paper_reproduced": False,
        "paper_table_cells_total": 70,
        "paper_table_cells_with_result_credit": exact_cells,
        "paper_table_rows_total": 7,
        "paper_table_rows_fully_reproduced": full_rows,
        "paper_benchmark_table_cells_total": 20,
        "benchmark_window_candidate_count": benchmark_window_summary[
            "candidate_common_windows"
        ],
        "benchmark_window_perfect_match_count": benchmark_window_summary["perfect_20_of_20_windows"],
        "paper_benchmark_table_cells_reproduced": sum(
            bool(row["paper_result_credit"]) for row in benchmark_rows
        ),
        "paper_effective_window_start": PAPER_EFFECTIVE_START.isoformat(),
        "paper_effective_window_end": PAPER_EFFECTIVE_END.isoformat(),
        "paper_effective_window_unique_in_supported_search": True,
        "paper_caption_end_matches_effective_window": PAPER_END == PAPER_EFFECTIVE_END,
        "paper_figure_units_total": len(figures),
        "paper_figure_units_with_result_credit": sum(bool(row["paper_result_credit"]) for row in figures),
        "paper_agent_table_cells_total": 50,
        "paper_agent_table_cells_with_result_credit": 0,
        "released_agent_protocol_variants_tested": sum(
            int(row["portfolio_variants_evaluated"]) for row in agent_protocol_rows
        ),
        "released_agent_protocol_complete_rows_reproduced": sum(
            bool(row["complete_agent_row_reproduced"]) for row in agent_protocol_rows
        ),
        "released_agent_protocol_best_display_matches": max(
            int(row["best_display_precision_matches"]) for row in agent_protocol_rows
        ),
        "paper_appendix_prompts_total": len(prompt_rows),
        "paper_appendix_prompts_verbatim_runtime": sum(bool(row["paper_appendix_is_verbatim_runtime_prompt"]) for row in prompt_rows),
        "source_history_reachable_commits": history["reachable_commits"],
        "source_history_unique_paths": history["unique_paths"],
        "source_history_unique_blobs": history["unique_blobs"],
        "historical_multi_agent_workbook_blobs": len(historical_workbook_summaries),
        "best_historical_workbook_table_matches": history["best_historical_workbook_table_matches"],
        "historical_paper_relevant_notebook_blobs": history["paper_relevant_multi_agent_notebook_blobs"],
        "historical_paper_relevant_embedded_plots": history["paper_relevant_historical_embedded_plots"],
        "historical_embedded_plots_matching_paper_figures": history["historical_embedded_plots_matching_paper_figures"],
        "archived_agent_runs": len(run_rows),
        "archived_current_collection_runs": sum(row["source_collection"] == "results" for row in run_rows),
        "archived_older_collection_runs": sum(row["source_collection"] == "results_22_24" for row in run_rows),
        "archived_paper_period_candidate_runs": sum(bool(row["paper_period_candidate"]) for row in run_rows),
        "archived_runs_with_exact_expected_tool_calls": sum(bool(row["every_expected_tool_called_once"]) for row in run_rows),
        "archived_runs_identifying_gpt_4o_2024_08_06": sum(row["runtime_model_snapshot"] == "gpt-4o-2024-08-06" for row in run_rows),
        "archived_distinct_system_fingerprints": len({value for row in run_rows for value in str(row["runtime_system_fingerprints"]).split("; ") if value}),
        "raw_portfolios_total": len(portfolio_rows),
        "raw_portfolios_weight_sum_100": sum(abs(float(row["raw_weight_sum"]) - 100) <= 1e-9 for row in portfolio_rows),
        "raw_portfolios_with_duplicate_tickers": sum(int(row["raw_duplicate_tickers"]) > 0 for row in portfolio_rows),
        "raw_portfolios_satisfying_full_strict_contract": sum(bool(row["strict_prompt_output_contract_satisfied"]) for row in portfolio_rows),
        "same_labeled_period_alternate_run_pairs": len(overlapping_rows),
        "alternate_run_pairs_with_exact_portfolio_file": sum(bool(row["exact_portfolio_file_match"]) for row in overlapping_rows),
        "alternate_run_pairs_with_exact_ticker_set": sum(bool(row["exact_ticker_set_match"]) for row in overlapping_rows),
        "native_source_workbook_series_total": len(native_rows),
        "native_source_workbook_series_reproduced": sum(bool(row["shipped_workbook_series_reproduced"]) for row in native_rows),
        "paper_mechanisms_total": len(mechanisms),
        "paper_mechanisms_with_released_implementation": sum(bool(row["released_implementation_present"]) for row in mechanisms),
        "blocking_specification_gaps": sum(row["severity"] == "blocking" for row in gaps),
        "honest_interpretation": (
            "GuruAgents has a reproducible current source artifact and unusually rich archived component evidence. "
            "A single common 2023-11-01 through 2025-08-01 window over the released QQQ/SPY cache independently "
            "regenerates both complete benchmark rows (20/20 cells), proving that the paper's actual endpoint "
            "extends beyond its Q2 2025 caption. The five headline agent paths, their 50 table cells, plotted "
            "portfolios, cost treatment, point-in-time protocol, reported-run lineage, and deterministic-scoring "
            "claim remain unreproduced."
        ),
    }
    (output_dir / "README.md").write_text(build_readme(manifest), encoding="utf-8")
    hash_files = sorted([*outputs, "public_source_history.json", "native_execution.json", "README.md"])
    manifest["output_sha256"] = {name: sha256(output_dir / name) for name in hash_files}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path,
        default=Path(os.environ.get("GURUAGENTS_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/guruagents_prompt_replay_source")),
    )
    parser.add_argument(
        "--paper-root", type=Path,
        default=Path(os.environ.get("GURUAGENTS_PAPER_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/guruagents_paper")),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=project_root / "paper_runs/paper_replication_audits/guruagents",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(args.source_root.resolve(), args.paper_root.resolve(), args.output_dir.resolve())
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    raise SystemExit(main())
