#!/usr/bin/env python3
"""Audit GuruAgents Table 1 against the authors' pinned public workbook.

The paper, stored workbook paths, and notebook summary routine are separate
evidence. Mismatches are recorded rather than treated as successful replication.
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
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from xml.etree import ElementTree as ET


PAPER_END = date(2025, 6, 30)
PAPER_COST_BPS = 1.0
SOURCE_COMMIT = "74ad2e6ce2e604c73a6fc2829d48ab58fe6be050"
METRICS: Tuple[Tuple[str, str, int], ...] = (
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
PAPER_TABLE: Tuple[Tuple[str, str, Tuple[float, ...]], ...] = (
    (
        "Benjamin Graham",
        "Benjamin_Graham_Returns",
        (28.7401, 0.0008, 0.0119, 0.1921, 0.1896, 0.0638, 1.0132, -23.8873, -1.0563, -2.1079),
    ),
    (
        "Warren Buffett",
        "Warren_Buffett_Returns",
        (42.2341, 0.0010, 0.0117, 0.2603, 0.1860, 0.0881, 1.3991, -22.3440, -0.8934, -1.9950),
    ),
    (
        "Joel Greenblatt",
        "Joel_Greenblatt_Returns",
        (19.3799, 0.0005, 0.0098, 0.1342, 0.1551, 0.0545, 0.8652, -20.7409, -0.9877, -1.7126),
    ),
    (
        "Joseph Piotroski",
        "Joseph_Piotroski_Returns",
        (30.9300, 0.0008, 0.0111, 0.2014, 0.1762, 0.0720, 1.1432, -23.0692, -1.0250, -1.9732),
    ),
    (
        "Edward Altman",
        "Edward_Altman_Returns",
        (25.7406, 0.0007, 0.0114, 0.1744, 0.1817, 0.0605, 0.9598, -21.7132, -1.1024, -2.0331),
    ),
    (
        "NASDAQ 100",
        "Benchmark_QQQ",
        (29.3611, 0.0011, 0.0135, 0.2827, 0.2150, 0.0828, 1.3151, -22.7683, -1.3911, -2.4290),
    ),
    (
        "S&P 500",
        "Benchmark_SPY",
        (26.3131, 0.0010, 0.0107, 0.2500, 0.1698, 0.0928, 1.4728, -18.7552, -0.9144, -1.8389),
    ),
)


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


def excel_column_index(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference)
    if not match:
        raise ValueError(f"Invalid XLSX cell reference: {reference}")
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def _shared_strings(archive: zipfile.ZipFile) -> List[str]:
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
    raise KeyError(f"Worksheet not found: {sheet_name}")


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


def read_xlsx_sheet(path: Path, sheet_name: str) -> List[Dict[str, Any]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        strings = _shared_strings(archive)
        root = ET.fromstring(archive.read(_worksheet_path(archive, sheet_name)))
        matrix: List[List[Any]] = []
        for row in root.findall(".//x:sheetData/x:row", ns):
            indexed = {
                excel_column_index(cell.attrib["r"]): _cell_value(cell, strings, ns)
                for cell in row.findall("x:c", ns)
            }
            matrix.append([indexed.get(index) for index in range(max(indexed, default=-1) + 1)])
    if not matrix:
        return []
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
    if not ordered:
        raise ValueError("Cannot calculate a percentile of an empty series")
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def calculate_metrics(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    observations = [row for row in rows if row.get("normalized_value") is not None]
    returns = [
        float(row["daily_return"])
        for row in observations
        if row.get("daily_return") not in {None, ""}
    ]
    if len(observations) < 2 or len(returns) < 2:
        raise ValueError("A return path needs at least two observations and two daily returns")
    dates = [excel_date(row["date"]) for row in observations]
    nav = [float(row["normalized_value"]) for row in observations]
    elapsed_years = (dates[-1] - dates[0]).days / 365.25
    daily_mean, daily_std = mean(returns), stdev(returns)
    peak = -math.inf
    drawdowns = []
    for value in nav:
        peak = max(peak, value)
        drawdowns.append(value / peak - 1.0)
    var = percentile(returns, 0.10)
    return {
        "sample_start": dates[0].isoformat(),
        "sample_end": dates[-1].isoformat(),
        "observations": len(observations),
        "return_observations": len(returns),
        "cagr_pct": ((nav[-1] / nav[0]) ** (1.0 / elapsed_years) - 1.0) * 100.0,
        "mean_daily": daily_mean,
        "std_daily": daily_std,
        "mean_annualized": daily_mean * 252.0,
        "std_annualized": daily_std * math.sqrt(252.0),
        "sharpe_daily": daily_mean / daily_std,
        "sharpe_annualized": daily_mean / daily_std * math.sqrt(252.0),
        "max_drawdown_pct": min(drawdowns) * 100.0,
        "var_90_pct": var * 100.0,
        "cvar_90_pct": mean(value for value in returns if value <= var) * 100.0,
        "source_notebook_annualized_return_pct": (nav[-1] ** (252.0 / len(observations)) - 1.0)
        * 100.0,
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_audit(source_root: Path, output_dir: Path) -> Dict[str, Any]:
    workbook = source_root / "results" / "multi_agent_backtest_results.xlsx"
    notebook = source_root / "04_multi_agent_backtesting.ipynb"
    if not workbook.is_file() or not notebook.is_file():
        raise FileNotFoundError("Source root must contain the GuruAgents results workbook and notebook 04")
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected GuruAgents {SOURCE_COMMIT}, found {commit}")

    output_dir.mkdir(parents=True, exist_ok=True)
    targets: List[Dict[str, Any]] = []
    conformance: List[Dict[str, Any]] = []
    summaries: List[Dict[str, Any]] = []
    for strategy, sheet, values in PAPER_TABLE:
        target = {"strategy": strategy, "sheet": sheet}
        target.update({metric[0]: value for metric, value in zip(METRICS, values)})
        targets.append(target)
        source_rows = read_xlsx_sheet(workbook, sheet)
        dated_rows = [(excel_date(row["date"]), row) for row in source_rows if row.get("date") is not None]
        windows = {
            "paper_labeled_through_2025Q2": [row for day, row in dated_rows if day <= PAPER_END],
            "full_shipped_workbook": [row for _, row in dated_rows],
        }
        for window, rows in windows.items():
            calculated = calculate_metrics(rows)
            matches = 0
            for (metric, paper_label, decimals), expected in zip(METRICS, values):
                actual = float(calculated[metric])
                tolerance = 0.5 * 10 ** (-decimals) + 1e-12
                matched = abs(actual - expected) <= tolerance
                matches += int(matched)
                conformance.append(
                    {
                        "strategy": strategy,
                        "sheet": sheet,
                        "window": window,
                        "metric": metric,
                        "paper_label": paper_label,
                        "paper_value": expected,
                        "recomputed_value": actual,
                        "absolute_error": abs(actual - expected),
                        "rounding_tolerance": tolerance,
                        "status": "exact_rounding_match" if matched else "mismatch",
                    }
                )
            summaries.append(
                {
                    "strategy": strategy,
                    "sheet": sheet,
                    "window": window,
                    "sample_start": calculated["sample_start"],
                    "sample_end": calculated["sample_end"],
                    "observations": calculated["observations"],
                    "return_observations": calculated["return_observations"],
                    "source_notebook_annualized_return_pct": calculated[
                        "source_notebook_annualized_return_pct"
                    ],
                    "matched_metrics": matches,
                    "total_metrics": len(METRICS),
                    "all_metrics_match": matches == len(METRICS),
                }
            )

    write_csv(
        output_dir / "paper_table_1_targets.csv",
        targets,
        ["strategy", "sheet", *[metric[0] for metric in METRICS]],
    )
    write_csv(output_dir / "metric_conformance.csv", conformance, list(conformance[0]))
    write_csv(output_dir / "strategy_summary.csv", summaries, list(summaries[0]))

    notebook_text = notebook.read_text(encoding="utf-8")
    return_block = notebook_text.split("def calculate_agent_returns", 1)[-1].split(
        "MultiAgentBacktester.calculate_agent_returns", 1
    )[0]
    fully_matched = sum(bool(row["all_metrics_match"]) for row in summaries)
    manifest = {
        "audit": "GuruAgents paper Table 1 versus pinned public source workbook",
        "overall_status": "reproduced" if fully_matched == len(summaries) else "not_reproduced",
        "paper_table": "Table 1, Summary performance metrics of agents and benchmarks",
        "paper_end_interpretation": PAPER_END.isoformat(),
        "paper_transaction_cost_bps": PAPER_COST_BPS,
        "source_commit": commit,
        "source_workbook": "results/multi_agent_backtest_results.xlsx",
        "source_workbook_sha256": sha256(workbook),
        "source_notebook": "04_multi_agent_backtesting.ipynb",
        "source_notebook_sha256": sha256(notebook),
        "source_declares_one_bp_cost": "transaction_cost=0.0001" in notebook_text,
        "source_main_return_routine_applies_declared_cost": "transaction_cost" in return_block,
        "strategy_windows_fully_matched": fully_matched,
        "strategy_windows_total": len(summaries),
        "metric_cells_matched": sum(row["status"] == "exact_rounding_match" for row in conformance),
        "metric_cells_total": len(conformance),
        "interpretation": (
            "The source workbook does not reproduce every published Table 1 value under either "
            "the paper-labeled end date or its full shipped window."
        ),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "GURUAGENTS_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/guruagents_prompt_replay_source",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/prompt_replay/guruagents/paper_table_conformance",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(args.source_root.resolve(), args.output_dir.resolve())
    print(json.dumps(manifest, indent=2))
    return int(args.strict and manifest["overall_status"] != "reproduced")


if __name__ == "__main__":
    sys.exit(main())
