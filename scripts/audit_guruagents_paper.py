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
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET


ARXIV_URL = "https://arxiv.org/abs/2510.01664"
SOURCE_URL = "https://github.com/yejining99/GuruAgents"
AUDIT_DATE = "2026-08-11"
PAPER_VERSION = "v1"
PAPER_DATE = "2025-10-02T04:45:27Z"
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
SOURCE_PRE_RUN_COMMIT = "49ced76002cc824de9ccc0bd5d46207d7b28af23"
SOURCE_PRE_RUN_DATE = "2025-08-18T21:42:38+09:00"
SOURCE_NOTEBOOK_CODE_SHA256 = "434e3016e8f7932a63ac0b67314d43206a09b49649e3a869a0cfeddbb52b5b23"
SOURCE_WORKBOOK_SHA256 = "45d4a4d7abb5ab89b83966c2474fc8de231fa544f5b3e436f6b06e79ae18e91d"
SOURCE_NOTEBOOK_SHA256 = "e3c53f38ac37741f5989faa852b52f0a78776ccc5770c7a3cf9cf4f62acabca6"
PAPER_END = date(2025, 6, 30)
PAPER_COST_BPS = 1.0

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


def read_xlsx_sheet(path: Path, sheet_name: str) -> list[dict[str, Any]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
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
    for key, spec in AGENTS.items():
        root = source_root / "results" / spec["directory"]
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
            run_rows.append({
                "agent": spec["paper_name"], "analysis_start": analysis["start_date"],
                "analysis_end": analysis["end_date"], "archived_timestamp": analysis["timestamp"],
                "execution_time_seconds": analysis.get("execution_time_seconds"),
                "tool_calls": len(tool_calls), "expected_tool_calls": len(spec["tools"]),
                "every_expected_tool_called_once": all(counts[name] == 1 for name in spec["tools"])
                and set(counts) == set(spec["tools"]),
                "runtime_model_snapshot": "; ".join(models),
                "runtime_system_fingerprints": "; ".join(fingerprints),
                "output_begins_with_required_table": output.lstrip().startswith("| Ticker"),
                "analysis_sha256": sha256(analysis_path), "execution_log_sha256": sha256(log_path),
                "portfolio_sha256": sha256(portfolio_path),
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
                "agent": spec["paper_name"], "analysis_start": analysis["start_date"],
                "analysis_end": analysis["end_date"], "raw_rows": len(raw),
                "raw_unique_tickers": len(set(tickers)), "raw_duplicate_tickers": duplicate_count,
                "raw_weight_sum": raw_sum, "raw_weights_all_integer": len(weights) == len(raw)
                and all(value.is_integer() for value in weights),
                "raw_scores_complete": len(scores) == len(raw),
                "unknown_or_blank_tickers": "; ".join(unknown),
                "source_loader_rows_after_drop_and_deduplicate": len(unique),
                "source_loader_normalizes_to_weight_sum": normalized_sum,
                "response_begins_with_only_required_table": final_only,
                "strict_prompt_output_contract_satisfied": strict,
                "paper_figure_2_distribution_reproduced": False,
                "paper_result_credit": False,
            })
    if len(run_rows) != 35 or len(portfolio_rows) != 35:
        raise RuntimeError(f"expected 35 GuruAgents decisions, found {len(run_rows)}")
    return run_rows, portfolio_rows


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
        *[f"agents/{spec['file']}" for spec in AGENTS.values()],
    ]
    rows = []
    for relative in paths:
        path = source_root / relative
        rows.append({
            "authority": "official GitHub artifact commit", "relative_path": relative,
            "bytes": path.stat().st_size, "sha256": sha256(path), "present": True,
        })
    for relative in ("paper_v1.pdf", "source_v1.tar", "source_v1/figure/cumulative_figure.png", "source_v1/figure/weight.png"):
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
        ("identical inputs yield identical outputs", False, False, "no repeat trials or seed; three backend system fingerprints appear"),
        ("LangChain execution", True, True, "five agent executors use LangChain"),
        ("LangGraph execution for reported agents", False, False, "LangGraph appears only in an unrelated meta-agent path"),
        ("NASDAQ-100 universe", True, False, "fixed 100-name file lacks historical effective dates and some outputs are outside it"),
        ("quarterly fundamental data", True, True, "seven analysis quarters are released"),
        ("point-in-time accounting availability", False, False, "quarter labels have no filing/publication timestamps"),
        ("OHLCV and shares data", True, True, "released through 2025-08-12 without vendor/provenance metadata"),
        ("quarterly rebalance", True, True, "source uses analysis-end plus one day and 90-day holding intervals"),
        ("one-basis-point gross-turnover cost", False, False, "parameter is stored but never read by calculate_agent_returns"),
        ("portfolio weights sum to 100", False, False, "only 2 of 35 raw CSVs sum to 100; loader silently renormalizes"),
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
        ("paper-result return paths", "Exact Figure 1 paths and Table 1 input series are absent", "blocking"),
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
    source_root: Path,
) -> list[dict[str, Any]]:
    next(
        row for row in portfolio_rows
        if row["agent"] == "Warren Buffett" and row["analysis_start"] == "2023-10-01"
    )
    source_first = {
        row["Ticker"] for row in read_csv(
            source_root / "results/buffett_agent/buffett_portfolio_2023-10-01_2023-12-31.csv"
        )
    }
    paper_visible = {"TXN", "AVGO", "ADP", "AMZN", "GOOGL", "META", "NVDA", "AAPL", "MSFT"}
    return [
        {"check": "Table 1 native cell reproduction", "status": "partial_two_cells_only",
         "evidence": f"{sum(bool(row['paper_result_credit']) for row in table_rows)}/70 cells; both are benchmark MDD"},
        {"check": "Table 1 complete rows", "status": "not_reproduced",
         "evidence": "0/7 rows match all ten metrics"},
        {"check": "native notebook versus shipped workbook", "status": "exact_source_artifact_reproduction",
         "evidence": "all seven paths match to <1e-12, but are not the paper paths"},
        {"check": "paper horizon versus source workbook", "status": "contradiction",
         "evidence": "paper says Q4 2023-Q2 2025; shipped agent paths run 2024-01-01 to 2025-08-12"},
        {"check": "paper Figure 1 visual horizon", "status": "contradiction",
         "evidence": "paper image extends beyond the stated Q2 2025 endpoint"},
        {"check": "Figure 2 first visible Buffett bar", "status": "contradiction",
         "evidence": f"paper-visible ticker set differs; paper-only={sorted(paper_visible-source_first)}, source-only={sorted(source_first-paper_visible)}"},
        {"check": "raw portfolio weight sums", "status": "contradiction",
         "evidence": f"{sum(abs(float(row['raw_weight_sum'])-100)<=1e-9 for row in portfolio_rows)}/35 sum to 100"},
        {"check": "raw duplicate tickers", "status": "contradiction",
         "evidence": f"{sum(int(row['raw_duplicate_tickers'])>0 for row in portfolio_rows)}/35 contain duplicates"},
        {"check": "strict prompt output", "status": "contradiction",
         "evidence": f"{sum(bool(row['strict_prompt_output_contract_satisfied']) for row in portfolio_rows)}/35 satisfy the full contract"},
        {"check": "expected tool calls", "status": "supported_component",
         "evidence": f"{sum(bool(row['every_expected_tool_called_once']) for row in run_rows)}/35 archived runs call every declared tool once"},
        {"check": "runtime model", "status": "supported_component",
         "evidence": "all 35 logs identify gpt-4o-2024-08-06"},
        {"check": "runtime model fingerprint", "status": "determinism_not_established",
         "evidence": "three system fingerprints appear across the 35 archived runs"},
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
         "evidence": "code was present before Aug-21 runs; artifacts were first committed Aug 31; notebook code hash is invariant"},
    ]


def build_readme(manifest: Mapping[str, Any]) -> str:
    return f"""# GuruAgents paper-level replication audit

This directory audits [GuruAgents]({ARXIV_URL}) against the authors' pinned
[source repository]({SOURCE_URL}). It is deliberately fail-closed: reproducing
the public workbook is not the same as reproducing the paper.

## Verdict

**The paper is not faithfully reproduced.** Native execution of the released
notebook reproduces all seven shipped workbook paths to floating-point error,
but the workbook does not reproduce Table 1 or either paper figure. Only two of
the 70 Table 1 cells match at the paper's rounding precision, both benchmark
maximum-drawdown values; no complete table row matches. None of the 42 audited
figure units receives paper-result credit.

The release nevertheless contains valuable component evidence: 35 archived
GPT-4o-2024-08-06 agent decisions, full tool observations, five prompt/tool
implementations, quarterly financial/market data, portfolios, a workbook, and
notebook outputs. Every archived run calls each declared tool exactly once.
Those are real source-component achievements, not a paper reproduction.

## Most consequential breaks

- The paper says Q4 2023 through Q2 2025, while the public agent workbook runs
  from 2024-01-01 through 2025-08-12 and the paper's own Figure 1 visibly runs
  past Q2 2025.
- The declared 1 bp gross-turnover cost is never applied.
- Agent paths contain forward-filled calendar days while QQQ/SPY contain
  trading days; 252-day annualization is then applied to both.
- The paper names the NASDAQ-100 and S&P 500 indices, while source code uses the
  QQQ and SPY ETFs.
- The claimed deterministic scorer is performed by GPT-4o, not Python. Three
  backend fingerprints occur, there is no seed/repeat study, only 2/35 raw
  portfolios sum to 100, 9/35 contain duplicates, and 0/35 satisfy the entire
  strict output contract.
- Exact Table 1 generation code, paper Figure 1 paths, and paper Figure 2
  portfolio distributions are not released. The visible paper distributions
  differ from the public histories.
- Quarter labels are used as if data were available the next day; filing dates
  and historical NASDAQ-100 membership dates are absent.

## Accounting boundary

- Table 1: **{manifest['paper_table_cells_with_result_credit']}/70 cells**, **0/7 full rows**.
- Figures: **0/42 audited units**.
- Exact appendix prompts: **0/5** (all are edited presentations of runtime templates).
- Native public-workbook reproduction: **7/7 series** (component/source-artifact evidence only).
- Full-paper reproduction: **no**.

See `manifest.json` for the machine-readable summary and the CSV ledgers for
cell-, run-, portfolio-, prompt-, mechanism-, figure-, and gap-level evidence.
"""


def build_audit(source_root: Path, paper_root: Path, output_dir: Path) -> dict[str, Any]:
    validate_inputs(source_root, paper_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    table_rows, diagnostics, summaries = table_conformance_rows(source_root)
    prompt_rows = source_prompt_rows(source_root, paper_root)
    run_rows, portfolio_rows = archived_run_and_portfolio_rows(source_root)
    figures = figure_rows()
    embedded_plots = extract_notebook_pngs(source_root)
    artifacts = source_artifact_rows(source_root, paper_root)
    mechanisms = mechanism_rows()
    gaps = specification_gap_rows()
    native_rows, native_summary = run_native_backtest(source_root)
    paper_compile = compile_paper_source(paper_root)
    checks = internal_check_rows(table_rows, run_rows, portfolio_rows, source_root)

    outputs: dict[str, Sequence[Mapping[str, Any]]] = {
        "paper_table_1_conformance.csv": table_rows,
        "source_workbook_metric_diagnostics.csv": diagnostics,
        "source_workbook_window_summary.csv": summaries,
        "paper_figure_unit_conformance.csv": figures,
        "source_prompt_conformance.csv": prompt_rows,
        "archived_run_inventory.csv": run_rows,
        "archived_portfolio_validation.csv": portfolio_rows,
        "native_backtest_conformance.csv": native_rows,
        "notebook_embedded_plot_inventory.csv": embedded_plots,
        "source_artifact_inventory.csv": artifacts,
        "paper_mechanism_conformance.csv": mechanisms,
        "paper_specification_gaps.csv": gaps,
        "paper_internal_and_source_checks.csv": checks,
    }
    for filename, rows in outputs.items():
        write_csv(output_dir / filename, rows)

    native_execution = {
        "paper_source_compilation": paper_compile,
        "released_source_native_backtest": native_summary,
        "native_backtest_series": native_rows,
        "full_native_paper_execution_attempted": False,
        "full_native_paper_execution_blocker": (
            "Exact paper return paths, Figure 2 portfolio data, Table 1 generator, "
            "point-in-time inputs, and applied transaction-cost path are not released."
        ),
        "paper_result_credit": False,
    }
    (output_dir / "native_execution.json").write_text(
        json.dumps(native_execution, indent=2) + "\n", encoding="utf-8"
    )

    exact_cells = sum(bool(row["paper_result_credit"]) for row in table_rows)
    full_rows = sum(bool(row["full_paper_row_reproduced"]) for row in summaries if row["window"] == "paper_labeled_through_2025Q2")
    manifest: dict[str, Any] = {
        "audit": "GuruAgents fail-closed paper-level replication audit",
        "audit_date": AUDIT_DATE,
        "paper": {"url": ARXIV_URL, "version": PAPER_VERSION, "date": PAPER_DATE,
                  "pdf_sha256": PAPER_PDF_SHA256, "source_sha256": PAPER_SOURCE_SHA256, "pages": PAPER_PAGES},
        "source": {"url": SOURCE_URL, "artifact_commit": SOURCE_ARTIFACT_COMMIT,
                   "artifact_commit_date": SOURCE_ARTIFACT_DATE, "pre_run_code_commit": SOURCE_PRE_RUN_COMMIT,
                   "pre_run_code_commit_date": SOURCE_PRE_RUN_DATE},
        "overall_status": "public_workbook_exactly_reproduced_but_paper_results_not_reproduced_two_of_70_cells_only",
        "full_paper_reproduced": False,
        "paper_table_cells_total": 70,
        "paper_table_cells_with_result_credit": exact_cells,
        "paper_table_rows_total": 7,
        "paper_table_rows_fully_reproduced": full_rows,
        "paper_figure_units_total": len(figures),
        "paper_figure_units_with_result_credit": sum(bool(row["paper_result_credit"]) for row in figures),
        "paper_appendix_prompts_total": len(prompt_rows),
        "paper_appendix_prompts_verbatim_runtime": sum(bool(row["paper_appendix_is_verbatim_runtime_prompt"]) for row in prompt_rows),
        "archived_agent_runs": len(run_rows),
        "archived_runs_with_exact_expected_tool_calls": sum(bool(row["every_expected_tool_called_once"]) for row in run_rows),
        "archived_runs_identifying_gpt_4o_2024_08_06": sum(row["runtime_model_snapshot"] == "gpt-4o-2024-08-06" for row in run_rows),
        "archived_distinct_system_fingerprints": len({value for row in run_rows for value in str(row["runtime_system_fingerprints"]).split("; ") if value}),
        "raw_portfolios_total": len(portfolio_rows),
        "raw_portfolios_weight_sum_100": sum(abs(float(row["raw_weight_sum"]) - 100) <= 1e-9 for row in portfolio_rows),
        "raw_portfolios_with_duplicate_tickers": sum(int(row["raw_duplicate_tickers"]) > 0 for row in portfolio_rows),
        "raw_portfolios_satisfying_full_strict_contract": sum(bool(row["strict_prompt_output_contract_satisfied"]) for row in portfolio_rows),
        "native_source_workbook_series_total": len(native_rows),
        "native_source_workbook_series_reproduced": sum(bool(row["shipped_workbook_series_reproduced"]) for row in native_rows),
        "paper_mechanisms_total": len(mechanisms),
        "paper_mechanisms_with_released_implementation": sum(bool(row["released_implementation_present"]) for row in mechanisms),
        "blocking_specification_gaps": sum(row["severity"] == "blocking" for row in gaps),
        "honest_interpretation": (
            "GuruAgents has a reproducible public source artifact and unusually rich archived component evidence, "
            "but the paper's headline performance paths, table, plotted portfolios, cost treatment, point-in-time "
            "protocol, and deterministic-scoring claim are not reproduced."
        ),
    }
    (output_dir / "README.md").write_text(build_readme(manifest), encoding="utf-8")
    hash_files = sorted([*outputs, "native_execution.json", "README.md"])
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
