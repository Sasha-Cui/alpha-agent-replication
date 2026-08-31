#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for RAPTOR.

The audit distinguishes three very different things:

1. recomputing published scalars from author-shipped portfolio snapshots;
2. executing the released post-processing script; and
3. reproducing the paper's end-to-end multi-agent trading experiment.

Only the first two are currently possible.  Missing price/benchmark inputs and
material paper/runner disagreements prevent an end-to-end result reproduction.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
import os
import re
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader
from scipy.ndimage import distance_transform_edt


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]

OPENREVIEW_RECORD = "https://openreview.net/forum?id=ziuTkKhgT0"
CEUR_RECORD = "https://ceur-ws.org/Vol-4162/"
CEUR_PDF = "https://ceur-ws.org/Vol-4162/paper8.pdf"
FOUROPEN_URL = (
    "https://anonymous.4open.science/r/RAPTOR-Reasoned-Agentic-Portfolio-Trading-with-Orchestrated-Rebalancing"
)
ANONYMOUS_REPO_URL = (
    "https://github.com/anonymouspenguin3/RAPTOR-Reasoned-Agentic-Portfolio-Trading-with-Orchestrated-Rebalancing"
)
AUTHOR_REPO_URL = "https://github.com/blakealmon/AI-Hedge-Fund-Driven-By-Multi-Agent-LLM-Based-Architecture"
YAHOO_GSPC_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?"
    "period1=1735689600&period2=1756512000&interval=1d&events=history&includeAdjustedClose=true"
)

EXPECTED_PDF_SHA256 = "917b30a7ab49693c863720b4677de2f00329fd31f001f9a058c94298d81d6796"
EXPECTED_CEUR_RECORD_SHA256 = "23629695a80fbe193afa7710cadfc3014f6a52be5f9e9c43790dea60be9be8a8"
EXPECTED_PDF_PAGES = 11
EXPECTED_ANONYMOUS_HEAD = "677ac773809bdadeeee7821d6ed1b589ce920f80"
EXPECTED_ANONYMOUS_INITIAL = "7925285416ce6c95584c7e5b2c2491518e78c8ce"
EXPECTED_ANONYMOUS_TREE_SHA256 = "ec72018cc0f840492c6586f4a856a560fa4bd0ef0df572c803cc421f686284e2"
EXPECTED_ANONYMOUS_ARCHIVE_SHA256 = "d9e41191002d68eb16802bb833df67c148b51e1bdaf5aa2c15d9fd8888119aec"
EXPECTED_AUTHOR_HEAD = "1793abf29ecde15597cb2bb4cb345accf655531f"
EXPECTED_AUTHOR_TREE_SHA256 = "19753dc33b2e2f68438e36ed1e32c849878fc60b22f1bfa8ed660167c8acc6f9"
EXPECTED_AUTHOR_ARCHIVE_SHA256 = "badb4c27ba34232d6539975f3191dcc7a066a0ee1456c448ec9bb21f5e33d697"
EXPECTED_AUTHOR_VALIDATION_HEAD = "9d1f10a89802bed8abd81cdda88081ef1f566a84"
EXPECTED_AUTHOR_COMMITS = {
    "be0ac36e54f619c5a4ef11571e9538f76ecd8357",
    "63977bfbb7a68912c0fb86e0c4db57f3e7cdd793",
    EXPECTED_AUTHOR_HEAD,
    EXPECTED_AUTHOR_VALIDATION_HEAD,
}
EXPECTED_AUTHOR_VALIDATION_FILES = 845
EXPECTED_YAHOO_GSPC_SHA256 = "95f61e16d6b4a5b81f772fcd8b2971b14ecef2a0161a7fdcdeb04a51fb44f743"
EXPECTED_YAHOO_GSPC_OBSERVATIONS = 165
EXPECTED_TRACKED_FILES = 825
EXPECTED_PAPER_FIGURE_2_RGB_SHA256 = "d3fe3fd892d499cb72b2ff2c803763cbf3a96dea87bf84de5c1f8b3abc2f060d"
EXPECTED_PAPER_FIGURE_3_RGB_SHA256 = "b602ed873fae56069f6ff27ed25008a1f5f5e0310924360128373263c57ff335"
EXPECTED_NOTEBOOK_FIGURE_2_PNG_SHA256 = "7de3e695fab3846b409c1f481ba51db77345d608c828374292232ed0bdc6fdd4"
EXPECTED_NOTEBOOK_FIGURE_2_RGB_SHA256 = "58be0ff34bd5fb29d069a9aa4be607b76ed94ac2f52f239c20ec178fc3cd4b20"
EXPECTED_SNAPSHOTS = 166
EXPECTED_DECISION_FILES = 503
EXPECTED_PYTHON_FILES = 94
EXPECTED_NATIVE_METRIC_MODULE_SHA256 = (
    "b7d840cdb74d1447ffc8594007d2e5edef3bd30a1d98cfcdf774151b75a94aa7"
)
EXPECTED_NATIVE_METRIC_OUTPUT_SHA256 = {
    "rolling_sharpe_20": "8127b0772ab589a593f67d45634e29cbc796fc1596ce4f03b5b1fa548fcdc10c",
    "rolling_sortino_20": "66b3482be08587a09899930961e053460d9e151ddbcc406ad14de5290cc4d856",
    "rolling_calmar_60": "3d5f49c8c7b9447dc554d69e2e0e66fa75fd1b2eaf6ca3581f812394f558b03d",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git(repo: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
    )
    return result.stdout


def tracked_paths(repo: Path) -> list[str]:
    return str(git(repo, "ls-files")).splitlines()


def stored_bytes(path: Path) -> bytes:
    if path.is_symlink():
        return ("SYMLINK:" + os.readlink(path)).encode("utf-8")
    return path.read_bytes()


def tree_sha256(repo: Path) -> str:
    return bytes_sha256(bytes(git(repo, "ls-tree", "-r", "HEAD", binary=True)))


def archive_sha256(repo: Path) -> str:
    return bytes_sha256(bytes(git(repo, "archive", "--format=tar", "HEAD", binary=True)))


def validate_repo(repo: Path, expected_head: str, expected_tree: str, expected_archive: str) -> list[str]:
    if str(git(repo, "rev-parse", "HEAD")).strip() != expected_head:
        raise ValueError(f"unexpected repository HEAD: {repo}")
    if tree_sha256(repo) != expected_tree:
        raise ValueError(f"repository tree changed: {repo}")
    if archive_sha256(repo) != expected_archive:
        raise ValueError(f"repository archive changed: {repo}")
    if subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--"]).returncode != 0:
        raise ValueError(f"tracked repository files are dirty: {repo}")
    paths = tracked_paths(repo)
    if len(paths) != EXPECTED_TRACKED_FILES:
        raise ValueError(f"tracked file count changed: {repo}: {len(paths)}")
    return paths


def validate_paper(path: Path) -> tuple[str, list[dict[str, str]]]:
    if sha256(path) != EXPECTED_PDF_SHA256:
        raise ValueError("CEUR final PDF hash changed")
    reader = PdfReader(path)
    if len(reader.pages) != EXPECTED_PDF_PAGES:
        raise ValueError(f"CEUR PDF page count changed: {len(reader.pages)}")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized = " ".join(text.split())
    for required in (
        "RAPTOR: Reasoned Agentic Portfolio Trading with",
        "The portfolio’s value increased from $1,000,000.00 to $1,134,348.19",
        "Complete artifacts and",
        "one-command scripts are provided",
    ):
        if required not in normalized:
            raise ValueError(f"required paper text missing: {required}")
    links: list[dict[str, str]] = []
    for page_index, page in enumerate(reader.pages, start=1):
        for annotation_ref in page.get("/Annots", []):
            annotation = annotation_ref.get_object()
            action = annotation.get("/A")
            uri = action.get("/URI") if action else None
            if uri:
                links.append({"page": str(page_index), "uri": str(uri)})
    author_links = [row for row in links if row["uri"] == AUTHOR_REPO_URL]
    if len(author_links) != 1 or author_links[0]["page"] != "9":
        raise ValueError(f"author repository annotation changed: {author_links}")
    return text, links


def role(path: str) -> str:
    if re.fullmatch(r"testing/\d{4}-\d{2}-\d{2}/portfolio_snapshot_\d{4}-\d{2}-\d{2}\.json", path):
        return "author_result_snapshot"
    if re.fullmatch(r"testing/\d{4}-\d{2}-\d{2}/[^/]+\.txt", path):
        return "author_day0_decision_output"
    if re.fullmatch(r"testing/\d{4}-\d{2}-\d{2}/(?:resizingReport|portfolio_optimizer_report)\.md", path):
        return "author_trade_or_optimizer_report"
    if path == "testing/visualization.out.ipynb":
        return "author_executed_notebook"
    if path in {"testing/mvo_blm_runner.py", "testingLoopMultithreaded.py", "mvo_blm_runner.py"}:
        return "candidate_backtest_runner"
    if path == "testing/scripts/visualize.py":
        return "native_result_postprocessor"
    if path in {"pyproject.toml", "uv.lock", "requirements.txt", "setup.py"}:
        return "dependency_or_build_manifest"
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        return "implementation_source"
    if suffix in {".md", ".txt"}:
        return "documentation"
    if suffix in {".json", ".toml"}:
        return "configuration_or_fixture"
    if suffix in {".png", ".ipynb"}:
        return "asset_or_notebook"
    return "other"


def source_inventory(repo: Path, paths: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    compiled = 0
    for name in paths:
        path = repo / name
        payload = stored_bytes(path)
        compile_status = "not_python"
        if name.endswith(".py"):
            try:
                compile(path.read_text(encoding="utf-8", errors="replace"), name, "exec")
                compile_status = "compiled"
                compiled += 1
            except Exception as error:  # pragma: no cover - a future source drift path
                compile_status = f"{type(error).__name__}:{error}"
        item_role = role(name)
        rows.append(
            {
                "path": name,
                "bytes": str(len(payload)),
                "sha256": bytes_sha256(payload),
                "role": item_role,
                "compile_status": compile_status,
                "paper_input": "no",
                "author_output": "yes" if item_role.startswith("author_") else "no",
                "end_to_end_result_credit": "no",
            }
        )
    if compiled != EXPECTED_PYTHON_FILES:
        raise ValueError(f"Python compile count changed: {compiled}")
    return rows


def repository_relationship(anonymous: Path, author: Path) -> list[dict[str, str]]:
    left = {name: stored_bytes(anonymous / name) for name in tracked_paths(anonymous)}
    right = {name: stored_bytes(author / name) for name in tracked_paths(author)}
    rows: list[dict[str, str]] = []
    for name in sorted(set(left) | set(right)):
        lval, rval = left.get(name), right.get(name)
        if lval is None:
            relationship = "author_only"
        elif rval is None:
            relationship = "anonymous_only"
        elif lval == rval:
            relationship = "byte_identical"
        else:
            relationship = "changed"
        rows.append(
            {
                "path": name,
                "relationship": relationship,
                "anonymous_sha256": bytes_sha256(lval) if lval is not None else "",
                "author_sha256": bytes_sha256(rval) if rval is not None else "",
                "paper_relevant": "yes"
                if role(name)
                in {
                    "author_result_snapshot",
                    "author_day0_decision_output",
                    "author_trade_or_optimizer_report",
                    "author_executed_notebook",
                    "candidate_backtest_runner",
                    "native_result_postprocessor",
                }
                else "no",
            }
        )
    counts = Counter(row["relationship"] for row in rows)
    expected = {"byte_identical": 815, "changed": 7, "author_only": 3, "anonymous_only": 3}
    if counts != expected:
        raise ValueError(f"repository relationship changed: {counts}")
    key_paths = [
        "testing/mvo_blm_runner.py",
        "testingLoopMultithreaded.py",
        "mvo_blm_runner.py",
        "testing/scripts/visualize.py",
        "testing/2025-08-29/portfolio_snapshot_2025-08-29.json",
    ]
    if any(next(row for row in rows if row["path"] == name)["relationship"] != "byte_identical" for name in key_paths):
        raise ValueError("paper-relevant source relationship changed")
    return rows


def source_history_rows(author: Path) -> list[dict[str, str]]:
    if (author / ".git/shallow").exists():
        raise ValueError("author repository is shallow; full public history was not audited")
    commits = str(git(author, "rev-list", "--all", "--reverse")).splitlines()
    if set(commits) != EXPECTED_AUTHOR_COMMITS or len(commits) != len(EXPECTED_AUTHOR_COMMITS):
        raise ValueError(f"author reachable commit set changed: {commits}")
    rows: list[dict[str, str]] = []
    for commit in commits:
        paths = str(git(author, "ls-tree", "-r", "--name-only", commit)).splitlines()
        lowered = [name.lower() for name in paths]
        datesubject = str(git(author, "show", "-s", "--format=%aI%x09%s", commit)).rstrip("\n").split("\t", 1)
        refs = str(git(author, "branch", "-a", "--contains", commit, "--format=%(refname:short)")).splitlines()
        rows.append(
            {
                "commit": commit,
                "author_date": datesubject[0],
                "subject": datesubject[1],
                "containing_refs": ";".join(sorted(ref.strip() for ref in refs if ref.strip())),
                "tracked_files": str(len(paths)),
                "python_files": str(sum(name.endswith(".py") for name in paths)),
                "portfolio_snapshots": str(
                    sum(bool(re.search(r"portfolio_snapshot_\d{4}-\d{2}-\d{2}\.json$", name)) for name in paths)
                ),
                "stock_prices_csv": str(sum(name.endswith("stock_prices.csv") for name in lowered)),
                "benchmark_data_files": str(
                    sum(bool(re.search(r"(?:sp500|s&p|gspc).*\.(?:csv|json)$", name)) for name in lowered)
                ),
                "paper_result_credit": "author_output_audit_only"
                if commit in {EXPECTED_AUTHOR_HEAD, "63977bfbb7a68912c0fb86e0c4db57f3e7cdd793"}
                else "none",
            }
        )
    expected = {
        "be0ac36e54f619c5a4ef11571e9538f76ecd8357": (1, 0, 0),
        "63977bfbb7a68912c0fb86e0c4db57f3e7cdd793": (825, 93, 166),
        EXPECTED_AUTHOR_HEAD: (825, 93, 166),
        EXPECTED_AUTHOR_VALIDATION_HEAD: (EXPECTED_AUTHOR_VALIDATION_FILES, 103, 166),
    }
    for row in rows:
        actual = (int(row["tracked_files"]), int(row["python_files"]), int(row["portfolio_snapshots"]))
        if actual != expected[row["commit"]] or row["stock_prices_csv"] != "0" or row["benchmark_data_files"] != "0":
            raise ValueError(f"author history inventory changed: {row}")
    return rows


def validation_branch_rows(author: Path) -> list[dict[str, str]]:
    main_paths = set(str(git(author, "ls-tree", "-r", "--name-only", EXPECTED_AUTHOR_HEAD)).splitlines())
    validation_paths = set(
        str(git(author, "ls-tree", "-r", "--name-only", EXPECTED_AUTHOR_VALIDATION_HEAD)).splitlines()
    )
    added = sorted(validation_paths - main_paths)
    removed = sorted(main_paths - validation_paths)
    if len(added) != 20 or removed:
        raise ValueError(f"validation branch delta changed: {len(added)} added, {len(removed)} removed")
    enhancement = bytes(
        git(
            author,
            "show",
            f"{EXPECTED_AUTHOR_VALIDATION_HEAD}:paper_enhancements/enhanced_paper_sections.md",
            binary=True,
        )
    )
    validator = bytes(
        git(author, "show", f"{EXPECTED_AUTHOR_VALIDATION_HEAD}:evaluation/statistical_validation.py", binary=True)
    )
    if not all(
        token in enhancement
        for token in (b"Claims 12.49% vs 10.08%", b"p-value: 0.019", b"January 2020 - December 2024")
    ):
        raise ValueError("post-publication enhancement claims changed")
    if b"aligned_benchmarkay" not in validator or b"np.random.choice" not in validator:
        raise ValueError("post-publication statistical-validator defects changed")
    rows: list[dict[str, str]] = []
    for name in added:
        payload = bytes(git(author, "show", f"{EXPECTED_AUTHOR_VALIDATION_HEAD}:{name}", binary=True))
        assessment = "later_generic_framework_no_paper_result_evidence"
        defects = ""
        if name == "paper_enhancements/enhanced_paper_sections.md":
            assessment = "later_template_with_unsupported_conflicting_claims"
            defects = "12.49% system result conflicts with final paper 13.43%; 2020-2024 protocol conflicts with final 2025 horizon; no result inputs"
        elif name == "evaluation/statistical_validation.py":
            assessment = "later_generic_validator_not_executed_on_paper_data"
            defects = "aligned_benchmarkay NameError in robustness path; unseeded bootstrap; no inputs or outputs"
        rows.append(
            {
                "path": name,
                "sha256": bytes_sha256(payload),
                "assessment": assessment,
                "defects_or_conflicts": defects,
                "paper_result_credit": "none",
            }
        )
    return rows


def benchmark_reproduction(path: Path, system_return_pct: float) -> tuple[list[dict[str, str]], dict[str, float]]:
    if sha256(path) != EXPECTED_YAHOO_GSPC_SHA256:
        raise ValueError("pinned Yahoo GSPC response changed")
    result = json.loads(path.read_text(encoding="utf-8"))["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["adjclose"][0]["adjclose"]
    if (
        len(timestamps) != EXPECTED_YAHOO_GSPC_OBSERVATIONS
        or len(closes) != len(timestamps)
        or any(value is None for value in closes)
    ):
        raise ValueError("Yahoo GSPC response coverage changed")
    dates = [datetime.fromtimestamp(value, timezone.utc).date().isoformat() for value in timestamps]
    benchmark_return_pct = (float(closes[-1]) / float(closes[0]) - 1) * 100
    excess_pct_points = system_return_pct - benchmark_return_pct
    if dates[0] != "2025-01-02" or dates[-1] != "2025-08-29":
        raise ValueError(f"Yahoo GSPC date coverage changed: {dates[0]} to {dates[-1]}")
    if round(benchmark_return_pct, 2) != 10.08 or round(excess_pct_points, 2) != 3.35:
        raise ValueError("current Yahoo response no longer recovers displayed benchmark assertions")
    rows = [
        {
            "date": date,
            "timestamp_utc": str(timestamp),
            "adjusted_close": repr(float(close)),
            "cumulative_return_percent": repr((float(close) / float(closes[0]) - 1) * 100),
            "source": "pinned_present_day_Yahoo_chart_response",
            "paper_time_frozen_input": "no",
            "end_to_end_result_credit": "no",
        }
        for date, timestamp, close in zip(dates, timestamps, closes)
    ]
    summary = {
        "observations": float(len(rows)),
        "first_adjusted_close": float(closes[0]),
        "last_adjusted_close": float(closes[-1]),
        "benchmark_return_pct": benchmark_return_pct,
        "system_return_pct": system_return_pct,
        "excess_percentage_points": excess_pct_points,
    }
    return rows, summary


def snapshot_rows(repo: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    rows: list[tuple[str, Path, dict[str, Any]]] = []
    for path in repo.glob("testing/*/portfolio_snapshot_*.json"):
        date = path.parent.name
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for field in ("net_liquidation", "portfolio_value", "buying_power"):
            if field not in data:
                raise ValueError(f"snapshot field missing: {path}: {field}")
        rows.append((date, path, data))
    rows.sort(key=lambda item: item[0])
    if len(rows) != EXPECTED_SNAPSHOTS or rows[0][0] != "2025-01-01" or rows[-1][0] != "2025-08-29":
        raise ValueError("snapshot coverage changed")
    return rows


def rolling_sharpe(
    returns_with_initial_nan: list[float],
    window: int = 20,
    ddof: int = 1,
    min_periods: int = 2,
    annual_risk_free_rate: float = 0.0,
) -> list[float]:
    result: list[float] = []
    for index in range(len(returns_with_initial_nan)):
        values = [
            value for value in returns_with_initial_nan[max(0, index - window + 1) : index + 1] if math.isfinite(value)
        ]
        if len(values) < min_periods:
            result.append(float("nan"))
            continue
        volatility = statistics.stdev(values) if ddof == 1 else statistics.pstdev(values)
        daily_excess = statistics.mean(values) - annual_risk_free_rate / 252
        result.append(float("nan") if volatility <= 0 else daily_excess / volatility * math.sqrt(252))
    return result


def metric_reproduction(repo: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, float]]:
    snapshots = snapshot_rows(repo)
    values = [float(data["net_liquidation"]) for _, _, data in snapshots]
    returns = [values[index] / values[index - 1] - 1 for index in range(1, len(values))]
    total_return = values[-1] / values[0] - 1
    annual_return = (1 + total_return) ** (252 / len(values)) - 1
    annual_volatility = statistics.stdev(returns) * math.sqrt(252)
    sharpe = (statistics.mean(returns) - 0.02 / 252) / statistics.stdev(returns) * math.sqrt(252)
    negative = [value for value in returns if value < 0]
    sortino = (statistics.mean(returns) - 0.02 / 252) / statistics.stdev(negative) * math.sqrt(252)
    peak = values[0]
    drawdowns: list[float] = []
    for value in values:
        peak = max(peak, value)
        drawdowns.append(value / peak - 1)
    rolling_sample = rolling_sharpe([float("nan"), *returns], ddof=1)
    rolling_population = rolling_sharpe([float("nan"), *returns], ddof=0)
    rolling_full20_rf2_sample = rolling_sharpe(
        [float("nan"), *returns],
        ddof=1,
        min_periods=20,
        annual_risk_free_rate=0.02,
    )
    finite_sample = [value for value in rolling_sample if math.isfinite(value)]
    finite_population = [value for value in rolling_population if math.isfinite(value)]
    finite_full20_rf2_sample = [value for value in rolling_full20_rf2_sample if math.isfinite(value)]
    computed = {
        "n": float(len(values)),
        "initial_value": values[0],
        "final_value": values[-1],
        "total_return_pct": total_return * 100,
        "annual_return_pct": annual_return * 100,
        "annual_volatility_pct": annual_volatility * 100,
        "sharpe": sharpe,
        "sortino": sortino,
        "maximum_drawdown_pct": min(drawdowns) * 100,
        "coverage_ratio": len(values) / EXPECTED_SNAPSHOTS,
        "rolling_sample_min": min(finite_sample),
        "rolling_sample_max": max(finite_sample),
        "rolling_sample_mean": statistics.mean(finite_sample),
        "rolling_sample_sd": statistics.stdev(finite_sample),
        "rolling_sample_final": finite_sample[-1],
        "rolling_population_min": min(finite_population),
        "rolling_population_max": max(finite_population),
        "rolling_population_final": finite_population[-1],
        "rolling_full20_rf2_sample_min": min(finite_full20_rf2_sample),
        "rolling_full20_rf2_sample_max": max(finite_full20_rf2_sample),
        "rolling_full20_rf2_sample_mean": statistics.mean(finite_full20_rf2_sample),
        "rolling_full20_rf2_sample_sd": statistics.stdev(finite_full20_rf2_sample),
        "rolling_full20_rf2_sample_final": finite_full20_rf2_sample[-1],
    }
    if round(computed["rolling_full20_rf2_sample_mean"], 2) != 1.60:
        raise ValueError("extended-validation rolling mean lineage changed")
    if round(computed["rolling_full20_rf2_sample_sd"], 2) != 3.28:
        raise ValueError("extended-validation rolling SD lineage changed")
    specs = [
        ("trading_days", "166", computed["n"], 0, "exact"),
        ("initial_value_usd", "1000000.00", computed["initial_value"], 2, "exact"),
        ("final_value_usd", "1134348.19", computed["final_value"], 2, "rounded"),
        ("total_return_percent", "13.43", computed["total_return_pct"], 2, "rounded"),
        ("annualized_return_percent", "21.09", computed["annual_return_pct"], 2, "rounded"),
        ("annualized_volatility_percent", "19.30", computed["annual_volatility_pct"], 2, "rounded"),
        ("sharpe_rf_2_percent", "1.0", computed["sharpe"], 1, "rounded"),
        ("sortino_rf_2_percent_negative_only_sample_sd", "1.28", computed["sortino"], 2, "rounded"),
        ("maximum_drawdown_percent", "-15.33", computed["maximum_drawdown_pct"], 2, "rounded"),
        ("coverage_ratio", "1.0", computed["coverage_ratio"], 1, "exact"),
    ]
    metric_rows: list[dict[str, str]] = []
    for metric, paper_value, value, decimals, convention in specs:
        match = abs(round(value, decimals) - float(paper_value)) <= 10 ** (-(decimals + 1))
        metric_rows.append(
            {
                "metric": metric,
                "paper_value": paper_value,
                "computed_value": repr(value),
                "reported_decimals": str(decimals),
                "match": "yes" if match else "no",
                "formula_or_convention": convention,
                "evidence": "166 author-shipped daily net_liquidation snapshots",
                "end_to_end_pipeline_reproduced": "no",
            }
        )
    if not all(row["match"] == "yes" for row in metric_rows):
        raise ValueError("headline metric lineage changed")
    rolling_rows = [
        {
            "date": date,
            "net_liquidation": repr(value),
            "daily_return": "" if index == 0 else repr(returns[index - 1]),
            "rolling_sharpe_20d_sample_sd": ""
            if not math.isfinite(rolling_sample[index])
            else repr(rolling_sample[index]),
            "rolling_sharpe_20d_population_sd": ""
            if not math.isfinite(rolling_population[index])
            else repr(rolling_population[index]),
            "rolling_sharpe_20d_full_window_sample_sd_rf2pct": ""
            if not math.isfinite(rolling_full20_rf2_sample[index])
            else repr(rolling_full20_rf2_sample[index]),
        }
        for index, ((date, _, _), value) in enumerate(zip(snapshots, values))
    ]
    return metric_rows, rolling_rows, computed


def rolling_claim_forensics(repo: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Exhaust standard rolling-Sharpe conventions against the paper's six claims."""
    snapshots = snapshot_rows(repo)
    values = [float(data["net_liquidation"]) for _date, _path, data in snapshots]
    returns = [values[index] / values[index - 1] - 1 for index in range(1, len(values))]
    section_claims = {
        "minimum": -2.42,
        "maximum": 5.27,
        "mean": 1.41,
        "sample_sd_across_series": 2.63,
    }
    rows: list[dict[str, Any]] = []
    for window in range(20, len(values)):
        for ddof in (0, 1):
            for min_periods_policy, min_periods in (
                ("expanding_start_min_2", 2),
                ("full_window_only", window),
            ):
                for annual_risk_free_rate in (0.0, 0.02):
                    series = rolling_sharpe(
                        [float("nan"), *returns],
                        window=window,
                        ddof=ddof,
                        min_periods=min_periods,
                        annual_risk_free_rate=annual_risk_free_rate,
                    )
                    finite = [value for value in series if math.isfinite(value)]
                    observed = {
                        "minimum": min(finite),
                        "maximum": max(finite),
                        "mean": statistics.mean(finite),
                        "sample_sd_across_series": (
                            statistics.stdev(finite) if len(finite) > 1 else float("nan")
                        ),
                        "final": finite[-1],
                    }
                    section_matches = {
                        metric: round(observed[metric], 2) == paper_value
                        for metric, paper_value in section_claims.items()
                    }
                    lower_matches = (
                        round(observed["mean"], 1) == 1.1
                        or round(observed["final"], 1) == 1.1
                    )
                    upper_matches = (
                        round(observed["mean"], 1) == 1.4
                        or round(observed["final"], 1) == 1.4
                    )
                    rows.append(
                        {
                            "claim_scope": (
                                "section_4_3_explicit_20_day"
                                if window == 20
                                else "extended_validation_unspecified_longer_window"
                            ),
                            "window": window,
                            "ddof": ddof,
                            "min_periods_policy": min_periods_policy,
                            "min_periods": min_periods,
                            "annual_risk_free_rate": annual_risk_free_rate,
                            "finite_observations": len(finite),
                            "minimum": observed["minimum"],
                            "maximum": observed["maximum"],
                            "mean": observed["mean"],
                            "sample_sd_across_series": observed["sample_sd_across_series"],
                            "final": observed["final"],
                            "section_minimum_matches": section_matches["minimum"],
                            "section_maximum_matches": section_matches["maximum"],
                            "section_mean_matches": section_matches["mean"],
                            "section_sd_matches": section_matches["sample_sd_across_series"],
                            "section_claim_cells_matching": sum(section_matches.values()),
                            "longer_lower_1_1_matches_mean_or_final": lower_matches,
                            "longer_upper_1_4_matches_mean_or_final": upper_matches,
                            "longer_both_endpoints_match": lower_matches and upper_matches,
                            "paper_result_credit": False,
                            "interpretation": (
                                "standard 20-day convention conflicts with all four displayed claims"
                                if window == 20
                                else "numeric endpoint coincidence under one of many unreported longer-window protocols"
                                if lower_matches or upper_matches
                                else "no longer-window endpoint coincidence"
                            ),
                        }
                    )
    section_rows = [row for row in rows if row["window"] == 20]
    longer_rows = [row for row in rows if row["window"] > 20]
    summary = {
        "rows": len(rows),
        "section_20d_conventions": len(section_rows),
        "section_20d_claim_cells_matching": sum(
            int(row["section_claim_cells_matching"]) for row in section_rows
        ),
        "longer_window_conventions": len(longer_rows),
        "longer_any_endpoint_matches": sum(
            row["longer_lower_1_1_matches_mean_or_final"]
            or row["longer_upper_1_4_matches_mean_or_final"]
            for row in longer_rows
        ),
        "longer_both_endpoints_match": sum(
            row["longer_both_endpoints_match"] for row in longer_rows
        ),
        "paper_result_credit": False,
    }
    if summary != {
        "rows": 1168,
        "section_20d_conventions": 8,
        "section_20d_claim_cells_matching": 0,
        "longer_window_conventions": 1160,
        "longer_any_endpoint_matches": 290,
        "longer_both_endpoints_match": 11,
        "paper_result_credit": False,
    }:
        raise ValueError(f"rolling-claim convention boundary changed: {summary}")
    return rows, summary


def paper_internal_scalar_checks() -> list[dict[str, Any]]:
    """Verify displayed Table 1 arithmetic and exact prose/table repetitions."""
    weights = {
        "WAB": (0.112, 0.087, -0.025),
        "SPY": (0.245, 0.253, 0.008),
        "XLI": (0.083, 0.089, 0.006),
    }
    rows: list[dict[str, Any]] = []
    result_ids = {"WAB": "RAP-031", "SPY": "RAP-034", "XLI": "RAP-037"}
    for ticker, (base, perturbed, displayed_delta) in weights.items():
        computed_delta = perturbed - base
        rows.append(
            {
                "result_id": result_ids[ticker],
                "check_type": "paper_internal_arithmetic",
                "ticker": ticker,
                "source_result_id": "",
                "displayed_value": displayed_delta,
                "computed_or_source_value": computed_delta,
                "match_at_display_precision": round(computed_delta, 3)
                == round(displayed_delta, 3),
                "paper_result_credit": False,
            }
        )
    duplicate_specs = (
        ("RAP-038", "WAB", "RAP-029", 0.112),
        ("RAP-039", "WAB", "RAP-030", 0.087),
        ("RAP-040", "WAB", "RAP-031", -0.025),
        ("RAP-041", "SPY", "RAP-034", 0.008),
        ("RAP-042", "XLI", "RAP-037", 0.006),
    )
    for result_id, ticker, source_result_id, value in duplicate_specs:
        rows.append(
            {
                "result_id": result_id,
                "check_type": "paper_internal_duplicate",
                "ticker": ticker,
                "source_result_id": source_result_id,
                "displayed_value": value,
                "computed_or_source_value": value,
                "match_at_display_precision": True,
                "paper_result_credit": False,
            }
        )
    if len(rows) != 8 or not all(row["match_at_display_precision"] for row in rows):
        raise ValueError("RAPTOR paper-internal scalar checks changed")
    return rows


def displayed_result_rows(
    computed: dict[str, float],
    benchmark: dict[str, float],
    rolling_summary: dict[str, Any],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(
        location: str,
        scope: str,
        metric: str,
        displayed: str,
        key: str = "",
        status: str = "unavailable",
        verification_source: str = "author_output",
    ) -> None:
        values = benchmark if verification_source == "current_public_response" else computed
        value = values.get(key) if key else None
        if status.startswith("verified"):
            credit_boundary = (
                "current_public_response_verification_only_not_paper_lineage"
                if verification_source == "current_public_response"
                else "author_output_verification_only"
            )
        else:
            credit_boundary = "no_result_credit"
        rows.append(
            {
                "result_id": f"RAP-{len(rows) + 1:03d}",
                "location": location,
                "scope": scope,
                "metric": metric,
                "displayed_value": displayed,
                "author_output_value": "" if value is None or verification_source != "author_output" else repr(value),
                "current_public_response_value": ""
                if value is None or verification_source != "current_public_response"
                else repr(value),
                "verification_status": status,
                "verification_source": verification_source if status.startswith("verified") else "none",
                "independent_end_to_end_reproduction": "no",
                "credit_boundary": credit_boundary,
            }
        )

    add("Abstract", "RAPTOR", "total_return_percent", "13.43", "total_return_pct", "verified_rounded")
    add(
        "Abstract",
        "benchmark",
        "SP500_total_return_percent",
        "10.08",
        "benchmark_return_pct",
        "verified_rounded_current_yahoo_response_not_paper_lineage",
        "current_public_response",
    )
    add("Section 4.3 paragraph 1", "RAPTOR", "total_return_percent", "13.43", "total_return_pct", "verified_rounded")
    add(
        "Section 4.3 paragraph 1",
        "benchmark",
        "SP500_total_return_percent",
        "10.08",
        "benchmark_return_pct",
        "verified_rounded_current_yahoo_response_not_paper_lineage",
        "current_public_response",
    )
    add(
        "Section 4.3 paragraph 1",
        "comparison",
        "excess_percentage_points",
        "3.35",
        "excess_percentage_points",
        "verified_rounded_current_yahoo_response_not_paper_lineage",
        "current_public_response",
    )
    add("Section 4.3 paragraph 2", "RAPTOR", "overall_sharpe", "1.0", "sharpe", "verified_rounded")
    add("Section 4.3 paragraph 2", "rolling", "rolling_20d_min", "-2.42")
    add("Section 4.3 paragraph 2", "rolling", "rolling_20d_max", "5.27")
    add("Section 4.3 paragraph 2", "rolling", "rolling_20d_mean", "1.41")
    add("Section 4.3 paragraph 2", "rolling", "rolling_20d_sd", "2.63")
    add("Extended validation", "RAPTOR", "trading_days", "166", "n", "verified_exact")
    add("Extended validation", "RAPTOR", "initial_value_usd", "1000000.00", "initial_value", "verified_exact")
    add("Extended validation", "RAPTOR", "final_value_usd", "1134348.19", "final_value", "verified_rounded")
    add("Extended validation", "RAPTOR", "total_return_percent", "13.43", "total_return_pct", "verified_rounded")
    add("Extended validation", "RAPTOR", "annualized_return_percent", "21.09", "annual_return_pct", "verified_rounded")
    add(
        "Extended validation",
        "RAPTOR",
        "annualized_volatility_percent",
        "19.30",
        "annual_volatility_pct",
        "verified_rounded",
    )
    add("Extended validation", "RAPTOR", "sharpe", "1.0", "sharpe", "verified_rounded")
    add("Extended validation", "RAPTOR", "sortino", "1.28", "sortino", "verified_rounded")
    add(
        "Extended validation",
        "RAPTOR",
        "maximum_drawdown_percent",
        "-15.33",
        "maximum_drawdown_pct",
        "verified_rounded",
    )
    add(
        "Extended validation",
        "rolling",
        "rolling_20d_mean",
        "1.60",
        "rolling_full20_rf2_sample_mean",
        "verified_rounded_full_20d_window_sample_sd_rf2pct",
    )
    add(
        "Extended validation",
        "rolling",
        "rolling_20d_sd",
        "3.28",
        "rolling_full20_rf2_sample_sd",
        "verified_rounded_full_20d_window_sample_sd_rf2pct",
    )
    add("Extended validation", "rolling", "longer_window_lower", "1.1")
    add("Extended validation", "rolling", "longer_window_upper", "1.4")
    add("Extended validation", "RAPTOR", "approximate_full_period_sharpe", "1.0", "sharpe", "verified_rounded")
    add(
        "Figure 3 caption",
        "rolling",
        "rolling_20d_min",
        "-5.26",
        "rolling_sample_min",
        "verified_near_by_truncation_not_standard_rounding",
    )
    add("Figure 3 caption", "rolling", "rolling_20d_max", "10.34", "rolling_sample_max", "verified_rounded")
    add(
        "Figure 3 caption",
        "rolling",
        "rolling_20d_final",
        "3.89",
        "rolling_sample_final",
        "conflict_population_sd_only_matches",
    )
    add("Section 4.3 coverage", "RAPTOR", "coverage_ratio_166_of_166", "1.0", "coverage_ratio", "verified_exact")
    for ticker, base, perturb, delta in (
        ("WAB", ".112", ".087", "-.025"),
        ("SPY", ".245", ".253", "+.008"),
        ("XLI", ".083", ".089", "+.006"),
    ):
        add("Table 1", "interpretability", f"{ticker}_base_weight", base)
        add("Table 1", "interpretability", f"{ticker}_perturbed_weight", perturb)
        add("Table 1", "interpretability", f"{ticker}_weight_delta", delta)
    add("Table 1 explanation", "interpretability", "WAB_base_weight", ".112")
    add("Table 1 explanation", "interpretability", "WAB_perturbed_weight", ".087")
    add("Table 1 explanation", "interpretability", "WAB_weight_delta", "-.025")
    add("Table 1 explanation", "interpretability", "SPY_weight_delta", "+.008")
    add("Table 1 explanation", "interpretability", "XLI_weight_delta", "+.006")
    internal_checks = {
        row["result_id"]: row for row in paper_internal_scalar_checks()
    }
    for row in rows:
        check = internal_checks.get(row["result_id"])
        if check is not None:
            row["verification_status"] = (
                "verified_paper_internal_arithmetic"
                if check["check_type"] == "paper_internal_arithmetic"
                else "verified_paper_internal_duplicate"
            )
            row["verification_source"] = "paper_internal_consistency"
            row["credit_boundary"] = "paper_internal_consistency_only_no_native_result_credit"
    if (
        rolling_summary["section_20d_conventions"] != 8
        or rolling_summary["section_20d_claim_cells_matching"] != 0
        or rolling_summary["longer_window_conventions"] != 1160
    ):
        raise AssertionError("rolling forensic summary changed")
    for row in rows:
        if row["result_id"] in {"RAP-007", "RAP-008", "RAP-009", "RAP-010"}:
            row["verification_status"] = (
                "checked_conflict_all_eight_standard_20d_conventions"
            )
            row["verification_source"] = "author_output_protocol_grid"
            row["credit_boundary"] = "author_output_conflict_no_result_credit"
        elif row["result_id"] in {"RAP-022", "RAP-023"}:
            row["verification_status"] = (
                "checked_underspecified_1160_longer_window_conventions"
            )
            row["verification_source"] = "author_output_protocol_grid"
            row["credit_boundary"] = "underspecified_protocol_no_result_credit"

    if len(rows) != 42:
        raise AssertionError(f"displayed-result denominator changed: {len(rows)}")
    verified = [row for row in rows if row["verification_status"].startswith("verified")]
    verified_sources = Counter(row["verification_source"] for row in verified)
    if len(verified) != 29 or verified_sources != {
        "author_output": 18,
        "current_public_response": 3,
        "paper_internal_consistency": 8,
    }:
        raise AssertionError("verified displayed-result count changed")
    if sum(row["verification_status"] == "unavailable" for row in rows) != 6:
        raise AssertionError("unavailable displayed-result count changed")
    if sum(row["verification_status"] != "unavailable" for row in rows) != 36:
        raise AssertionError("checked displayed-result count changed")
    return rows


def opaque_rgb(image: Image.Image) -> np.ndarray:
    rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, "white")
    background.alpha_composite(rgba)
    return np.asarray(background.convert("RGB"))


def paper_figure_rasters(paper: Path) -> tuple[np.ndarray, np.ndarray]:
    images = {item.image.size: opaque_rgb(item.image) for item in PdfReader(paper).pages[5].images}
    if set(images) != {(1500, 600), (1000, 400)}:
        raise ValueError(f"RAPTOR page-6 embedded image inventory changed: {set(images)}")
    figure_2 = images[(1500, 600)]
    figure_3 = images[(1000, 400)]
    if bytes_sha256(figure_2.tobytes()) != EXPECTED_PAPER_FIGURE_2_RGB_SHA256:
        raise ValueError("RAPTOR Figure 2 embedded raster changed")
    if bytes_sha256(figure_3.tobytes()) != EXPECTED_PAPER_FIGURE_3_RGB_SHA256:
        raise ValueError("RAPTOR Figure 3 embedded raster changed")
    return figure_2, figure_3


def author_notebook_figure_2(repo: Path) -> np.ndarray:
    notebook = json.loads((repo / "testing/visualization.out.ipynb").read_text(encoding="utf-8"))
    source = "".join(notebook["cells"][1]["source"])
    required = (
        "Cumulative Return (Portfolio vs S&P 500)",
        "sp500_closing_prices.csv",
        "plt.savefig(out_path, dpi=150)",
        "S&P 500 (^GSPC)",
    )
    if not all(token in source for token in required):
        raise ValueError("RAPTOR executed-notebook Figure 2 source changed")
    image_payloads = [
        "".join(output["data"]["image/png"])
        for output in notebook["cells"][1]["outputs"]
        if "image/png" in output.get("data", {})
    ]
    if len(image_payloads) != 1:
        raise ValueError("RAPTOR executed-notebook Figure 2 output inventory changed")
    raw = base64.b64decode(image_payloads[0])
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    if (
        bytes_sha256(raw) != EXPECTED_NOTEBOOK_FIGURE_2_PNG_SHA256
        or bytes_sha256(image.tobytes()) != EXPECTED_NOTEBOOK_FIGURE_2_RGB_SHA256
        or image.size != (987, 390)
    ):
        raise ValueError("RAPTOR executed-notebook Figure 2 raster changed")
    return np.asarray(image)


def render_figure_2_from_snapshots_and_current_response(
    repo: Path,
    yahoo_response: Path,
) -> np.ndarray:
    snapshots = snapshot_rows(repo)
    frame = (
        pd.DataFrame(
            {
                "date": pd.to_datetime([date for date, _, _ in snapshots]),
                "net_liquidation": [float(data["net_liquidation"]) for _, _, data in snapshots],
            }
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    portfolio_cumulative = frame["net_liquidation"] / frame["net_liquidation"].iloc[0]

    result = json.loads(yahoo_response.read_text(encoding="utf-8"))["chart"]["result"][0]
    benchmark = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
                    for timestamp in result["timestamp"]
                ]
            ),
            "Close": result["indicators"]["adjclose"][0]["adjclose"],
        }
    )
    benchmark_close = benchmark.set_index("Date")["Close"]
    benchmark_aligned = benchmark_close.reindex(frame["date"], method="ffill")
    benchmark_cumulative = benchmark_aligned / benchmark_aligned.dropna().iloc[0]

    plt.close("all")
    plt.rcdefaults()
    plt.figure(figsize=(10, 4))
    plt.plot(
        frame["date"],
        portfolio_cumulative - 1.0,
        label="Portfolio",
        linewidth=1.8,
        marker="o",
        markersize=2,
    )
    plt.plot(
        frame["date"],
        benchmark_cumulative - 1.0,
        label="S&P 500 (^GSPC)",
        linestyle="--",
        linewidth=1.5,
    )
    plt.title("Cumulative Return (Portfolio vs S&P 500)")
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return (− 1)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=150)
    plt.close()
    buffer.seek(0)
    return np.asarray(Image.open(buffer).convert("RGB"))


def same_size_color_mask_stats(
    paper: np.ndarray,
    comparison: np.ndarray,
    color: tuple[int, int, int],
    x_limits: tuple[int, int] | None = None,
) -> dict[str, float]:
    if paper.shape != comparison.shape:
        raise ValueError(f"Raster dimensions differ: {paper.shape} != {comparison.shape}")
    color_array = np.asarray(color, dtype=np.uint8)
    paper_mask = np.all(paper == color_array, axis=2)
    comparison_mask = np.all(comparison == color_array, axis=2)
    if x_limits is not None:
        minimum, maximum = x_limits
        paper_mask[:, :minimum] = False
        paper_mask[:, maximum + 1 :] = False
        comparison_mask[:, :minimum] = False
        comparison_mask[:, maximum + 1 :] = False

    def distance_values(source: np.ndarray, target: np.ndarray) -> np.ndarray:
        distances = distance_transform_edt(~target)
        y, x = np.nonzero(source)
        return distances[y, x]

    paper_to_comparison = distance_values(paper_mask, comparison_mask)
    comparison_to_paper = distance_values(comparison_mask, paper_mask)
    return {
        "paper_pixels": float(paper_mask.sum()),
        "comparison_pixels": float(comparison_mask.sum()),
        "intersection_pixels": float(np.logical_and(paper_mask, comparison_mask).sum()),
        "paper_within_2px_fraction": float(np.mean(paper_to_comparison <= 2)),
        "comparison_within_2px_fraction": float(np.mean(comparison_to_paper <= 2)),
        "paper_max_distance_px": float(paper_to_comparison.max()),
        "comparison_max_distance_px": float(comparison_to_paper.max()),
    }


def notebook_affine_distance_stats(
    notebook: np.ndarray,
    paper: np.ndarray,
    color: tuple[int, int, int],
) -> dict[str, float]:
    color_array = np.asarray(color, dtype=np.uint8)
    notebook_mask = np.all(notebook == color_array, axis=2)
    paper_mask = np.all(paper == color_array, axis=2)
    notebook_axes = (82, 978, 32, 337)
    paper_axes = (130, 1474, 56, 513)

    def data_limits(left: int, right: int) -> tuple[int, int]:
        width = right - left
        return (
            round(left + width * 0.05 / 1.10),
            round(right - width * 0.05 / 1.10),
        )

    notebook_min, notebook_max = data_limits(*notebook_axes[:2])
    paper_min, paper_max = data_limits(*paper_axes[:2])
    notebook_mask[:, :notebook_min] = False
    notebook_mask[:, notebook_max + 1 :] = False
    paper_mask[:, :paper_min] = False
    paper_mask[:, paper_max + 1 :] = False

    y, x = np.nonzero(notebook_mask)
    mapped_x = np.rint(
        paper_axes[0] + (x - notebook_axes[0]) * (paper_axes[1] - paper_axes[0]) / (notebook_axes[1] - notebook_axes[0])
    ).astype(int)
    mapped_y = np.rint(
        paper_axes[2] + (y - notebook_axes[2]) * (paper_axes[3] - paper_axes[2]) / (notebook_axes[3] - notebook_axes[2])
    ).astype(int)
    distances = distance_transform_edt(~paper_mask)[mapped_y, mapped_x]
    return {
        "notebook_data_pixels": float(len(distances)),
        "within_2px_fraction": float(np.mean(distances <= 2)),
        "maximum_distance_px": float(distances.max()),
    }


def figure_raster_forensics(
    paper: Path,
    repo: Path,
    yahoo_response: Path,
) -> list[dict[str, str]]:
    paper_figure_2, paper_figure_3 = paper_figure_rasters(paper)
    notebook_figure_2 = author_notebook_figure_2(repo)
    regenerated_figure_2 = render_figure_2_from_snapshots_and_current_response(repo, yahoo_response)
    regenerated_figure_3 = opaque_rgb(Image.open(repo / "testing/results/rolling_sharpe.png"))

    blue = (31, 119, 180)
    orange = (255, 127, 14)
    portfolio = same_size_color_mask_stats(
        paper_figure_2, regenerated_figure_2, blue, x_limits=(191, 1413)
    )
    benchmark = same_size_color_mask_stats(
        paper_figure_2, regenerated_figure_2, orange, x_limits=(191, 1413)
    )
    rolling = same_size_color_mask_stats(paper_figure_3, regenerated_figure_3, blue)
    notebook_portfolio = notebook_affine_distance_stats(notebook_figure_2, paper_figure_2, blue)
    notebook_benchmark = notebook_affine_distance_stats(notebook_figure_2, paper_figure_2, orange)
    figure_2_equal_fraction = float(np.mean(np.all(paper_figure_2 == regenerated_figure_2, axis=2)))
    figure_3_equal_fraction = float(np.mean(np.all(paper_figure_3 == regenerated_figure_3, axis=2)))

    expected_counts = (
        portfolio["paper_pixels"],
        portfolio["comparison_pixels"],
        portfolio["intersection_pixels"],
        benchmark["paper_pixels"],
        benchmark["comparison_pixels"],
        benchmark["intersection_pixels"],
        rolling["paper_pixels"],
        rolling["comparison_pixels"],
        rolling["intersection_pixels"],
        notebook_portfolio["notebook_data_pixels"],
        notebook_benchmark["notebook_data_pixels"],
    )
    if expected_counts != (
        7313.0,
        7313.0,
        7313.0,
        3132.0,
        3147.0,
        3132.0,
        3530.0,
        3527.0,
        2922.0,
        2648.0,
        969.0,
    ):
        raise ValueError(f"RAPTOR figure-raster color census changed: {expected_counts}")
    if (
        figure_2_equal_fraction != 0.9999477777777778
        or notebook_portfolio["maximum_distance_px"] > 2
        or notebook_benchmark["maximum_distance_px"] > 2
        or min(
            portfolio["paper_within_2px_fraction"],
            portfolio["comparison_within_2px_fraction"],
            benchmark["paper_within_2px_fraction"],
            notebook_portfolio["within_2px_fraction"],
            notebook_benchmark["within_2px_fraction"],
            rolling["paper_within_2px_fraction"],
            rolling["comparison_within_2px_fraction"],
        )
        != 1.0
    ):
        raise ValueError("RAPTOR figure-raster correspondence changed")

    specs = (
        (
            "Figure 2",
            "RAPTOR cumulative return",
            blue,
            portfolio,
            notebook_portfolio,
            figure_2_equal_fraction,
            "166 author snapshots plus pinned current Yahoo response; author notebook raster independently checked",
            "author_snapshots",
        ),
        (
            "Figure 2",
            "S&P 500 cumulative return",
            orange,
            benchmark,
            notebook_benchmark,
            figure_2_equal_fraction,
            "pinned current Yahoo response plus author executed-notebook raster",
            "missing_paper_time_csv_current_response_only",
        ),
        (
            "Figure 3",
            "20-day rolling Sharpe",
            blue,
            rolling,
            None,
            figure_3_equal_fraction,
            "released snapshot postprocessor regenerated raster",
            "author_snapshots_derived_series",
        ),
    )
    rows: list[dict[str, str]] = []
    for figure, series, color, stats, notebook_stats, equal_fraction, basis, lineage in specs:
        rows.append(
            {
                "figure": figure,
                "series": series,
                "color_rgb": "|".join(map(str, color)),
                "paper_exact_color_pixels": str(int(stats["paper_pixels"])),
                "comparison_exact_color_pixels": str(int(stats["comparison_pixels"])),
                "exact_color_intersection_pixels": str(int(stats["intersection_pixels"])),
                "paper_color_pixels_within_2px_fraction": repr(stats["paper_within_2px_fraction"]),
                "comparison_color_pixels_within_2px_fraction": repr(stats["comparison_within_2px_fraction"]),
                "paper_max_distance_px": repr(stats["paper_max_distance_px"]),
                "comparison_max_distance_px": repr(stats["comparison_max_distance_px"]),
                "author_notebook_data_color_pixels": (
                    "" if notebook_stats is None else str(int(notebook_stats["notebook_data_pixels"]))
                ),
                "author_notebook_affine_max_distance_px": (
                    "" if notebook_stats is None else repr(notebook_stats["maximum_distance_px"])
                ),
                "whole_figure_exact_rgb_fraction": repr(equal_fraction),
                "comparison_basis": basis,
                "paper_time_numeric_input_lineage": lineage,
                "raster_correspondence_verified": "yes",
                "published_raw_numeric_series_available": "no",
                "end_to_end_pipeline_reproduced": "no",
            }
        )
    return rows


def figure_rows(forensics: list[dict[str, str]]) -> list[dict[str, str]]:
    verified = {(row["figure"], row["series"]) for row in forensics}
    if verified != {
        ("Figure 2", "RAPTOR cumulative return"),
        ("Figure 2", "S&P 500 cumulative return"),
        ("Figure 3", "20-day rolling Sharpe"),
    }:
        raise ValueError("RAPTOR figure-raster correspondence inventory changed")
    return [
        {
            "figure": "Figure 2",
            "series": "RAPTOR cumulative return",
            "source_series_available": "yes",
            "native_postprocessor_generated": "yes",
            "published_raw_series_available": "no",
            "exact_published_series_reproduced": "no_raw_series",
            "raster_curve_correspondence_verified": "yes",
            "assessment": "all 7,313 published blue pixels reproduce exactly from the 166 author snapshots; author-notebook raster also maps within two pixels",
        },
        {
            "figure": "Figure 2",
            "series": "S&P 500 cumulative return",
            "source_series_available": "author_notebook_raster_plus_current_public_response",
            "native_postprocessor_generated": "no",
            "published_raw_series_available": "no",
            "exact_published_series_reproduced": "no_paper_time_raw_series",
            "raster_curve_correspondence_verified": "yes",
            "assessment": "all 3,132 published orange pixels occur in the current-response regeneration and the author notebook maps within two pixels; the missing paper-time CSV still blocks raw-series lineage",
        },
        {
            "figure": "Figure 3",
            "series": "20-day rolling Sharpe",
            "source_series_available": "yes",
            "native_postprocessor_generated": "yes",
            "published_raw_series_available": "no",
            "exact_published_series_reproduced": "no_published_raw_series",
            "raster_curve_correspondence_verified": "yes",
            "assessment": "all regenerated and published blue curve pixels lie within two pixels; source series explains caption extrema but not the caption terminal value under one standard-deviation convention",
        },
    ]


def method_rows() -> list[dict[str, str]]:
    specs = [
        (
            "investment universe",
            "S&P 500 constituents",
            "503-ticker universe file",
            "close",
            "universe membership vintage not documented",
        ),
        ("evaluation horizon", "2025-01-01 to 2025-08-29", "166 matching dated snapshots", "exact_output", ""),
        ("initial capital", "$1,000,000", "first snapshot $1,000,000", "exact_output", ""),
        ("price inputs", "offline OHLCV snapshots through 2025-07-27", "no tracked price CSV", "missing", "blocking"),
        (
            "benchmark inputs",
            "S&P 500 / SPY same horizon",
            "paper-time testing/sp500_closing_prices.csv absent; pinned current Yahoo response has 165 sessions",
            "paper_snapshot_missing_current_response_verified",
            "blocks exact lineage, not rounded endpoint check",
        ),
        ("Finnhub snapshots", "date-bounded news/insider/fundamental JSON", "none tracked", "missing", "blocking"),
        ("Reddit snapshots", "2025-01-01 to 2025-08-19", "none tracked", "missing", "blocking"),
        ("SimFin snapshots", "quarterly statements", "none tracked", "missing", "blocking"),
        ("Perplexity snapshots", "per-date macro JSON", "none tracked", "missing", "blocking"),
        (
            "point-in-time controls",
            "network disabled; only local snapshots",
            "runners contain live yfinance/API fallbacks",
            "conflict",
            "blocking",
        ),
        (
            "agent roles",
            "analysts, bull/bear researchers, risk managers, execution",
            "implementations are present",
            "substantial",
            "no run trace",
        ),
        (
            "blackboard schema",
            "typed append-only JSONL",
            "schema/storage code present but zero tracked JSONL logs",
            "partial",
            "no run evidence",
        ),
        (
            "debate rounds",
            "typically 2-3 per side",
            "conditional logic present; exact reported-run settings not pinned",
            "partial",
            "",
        ),
        (
            "LLM model",
            "not named",
            "default code names gpt-4o-mini but request logs absent",
            "underspecified",
            "blocking",
        ),
        (
            "LLM temperature and sampling",
            "not specified",
            "multiple source defaults; no request logs",
            "underspecified",
            "blocking",
        ),
        (
            "prompts",
            "proprietary prompts withheld",
            "many source prompts present; exact reported requests absent",
            "partial",
            "blocking",
        ),
        (
            "random seeds",
            "fixed seeds claimed by rubric",
            "no experiment seed or deterministic replay bundle",
            "missing",
            "blocking",
        ),
        (
            "paper cadence abstract",
            "biweekly",
            "testing runner uses >=14 calendar days",
            "close",
            "not identical to ten trading days",
        ),
        (
            "paper cadence setup",
            "daily, no fixed cadence",
            "contradicts paper Data/Appendix and both runners",
            "conflict",
            "blocking",
        ),
        (
            "paper cadence appendix",
            "every 10 trading days",
            "multithreaded runner has a 10-market-day path",
            "partial",
            "reported outputs align to another runner",
        ),
        (
            "output cadence",
            "unspecified lineage",
            "author log records 17 rebalances at >=14 calendar-day intervals from Jan 6",
            "different",
            "blocking",
        ),
        (
            "agent rerun frequency",
            "Data says Day 0 reuse; Setup says every day",
            "only Jan 1 has 503 decision files",
            "conflict",
            "blocking",
        ),
        (
            "multithreaded range runner",
            "Day 0 pipeline then scheduled allocation",
            "Day 0 enters revaluation-only early return when rebalance_mode is false",
            "implementation_bug",
            "blocking",
        ),
        (
            "decision persistence",
            "reuse prior decisions",
            "testing runner instead derives views from recent returns by default",
            "different",
            "blocking",
        ),
        (
            "categorical view mapping",
            "BUY/HOLD/SELL -> +2%/0/-2% annualized",
            "core BL code supports mapping",
            "exact_component",
            "not the output runner default",
        ),
        (
            "output-runner views",
            "categorical agent views",
            "recent-return mean by default; optional GPT-4o-mini daily-return prediction",
            "different",
            "blocking",
        ),
        ("root-runner views", "categorical agent views", "constant +2% for every ticker", "different", "blocking"),
        ("selection matrix", "identity", "core BL implementation uses identity", "exact_component", ""),
        (
            "confidence matrix",
            "0.5 * tau * diag(P Sigma P^T)",
            "core BL implementation matches; output runner uses empirical variance + 1e-4",
            "mixed",
            "blocking",
        ),
        (
            "covariance lookback",
            "252 trading days annualized",
            "output runner uses at most 60 prior observations",
            "different",
            "blocking",
        ),
        ("risk aversion", "3.0", "core BL default 3.0; output runner sets 5.0", "mixed", "blocking"),
        ("tau", "0.025", "core BL default .025; output runner sets .05", "mixed", "blocking"),
        (
            "optimization universe",
            "eligible S&P 500 constituents",
            "output runner limits optimization to top 50 holdings and views to top 10",
            "different",
            "blocking",
        ),
        ("long-only", "optional", "reported source paths force long-only", "partial", ""),
        (
            "transaction fees",
            "5 bps per unit turnover",
            "no matching deduction in candidate execution paths or snapshots",
            "missing",
            "blocking",
        ),
        (
            "slippage",
            "5 bps per unit turnover",
            "no matching deduction in candidate execution paths or snapshots",
            "missing",
            "blocking",
        ),
        ("daily net values", "166 complete snapshots", "166 snapshots with all three named fields", "exact_output", ""),
        (
            "benchmark result",
            "10.08%",
            "pinned current Yahoo ^GSPC adjusted-close response independently gives 10.0827288%",
            "verified_current_response",
            "not paper-time frozen input or end-to-end credit",
        ),
        (
            "WAB case study",
            "2025-09-01 trace and BL perturbation",
            "no Sep 1 outputs; Jan 1 WAB output is a different contradictory trace",
            "missing",
            "blocking",
        ),
        (
            "complete trace",
            "messages, tool calls, decision, weights included",
            "no such complete trace in paper or release",
            "missing",
            "blocking",
        ),
        (
            "Deflated Sharpe",
            "reported alongside naive Sharpe",
            "no value or implementation output",
            "missing",
            "blocking",
        ),
        (
            "additional diagnostics",
            "Calmar, turnover, beta, tracking error, VaR/CVaR",
            "not reported for the published experiment",
            "missing",
            "blocking",
        ),
        (
            "environment pinning",
            "lockfile/container/OS notes",
            "uv.lock present; no container or OS notes",
            "partial",
            "",
        ),
        (
            "one-command regeneration",
            "tables and figures",
            "README documents CLI only; missing inputs stop backtest runner",
            "missing",
            "blocking",
        ),
        ("automated tests", "not stated", "one collected function has no asserts and catches exceptions", "weak", ""),
        ("source syntax", "operational source", "all 93 Python files compile", "pass", "syntax only"),
        (
            "native visualization",
            "regenerate figures",
            "testing/scripts/visualize.py executes and emits six artifacts",
            "pass_component",
            "not end-to-end",
        ),
        (
            "result lineage",
            "reported system result",
            "headline scalars derive exactly from released snapshots",
            "verified_output",
            "pipeline lineage remains unrerunnable",
        ),
    ]
    return [
        {
            "dimension": d,
            "paper_specification": p,
            "released_source_or_output": s,
            "assessment": a,
            "severity_or_note": n,
            "end_to_end_credit": "no",
        }
        for d, p, s, a, n in specs
    ]


def consistency_rows() -> list[dict[str, str]]:
    issues = [
        ("horizon label", "Abstract calls the study a one-year reconstruction; all reported dates span eight months."),
        (
            "cadence",
            "Abstract/Introduction say biweekly, Section 4.2 says daily with no fixed cadence, and Appendix B.3 says every 10 trading days.",
        ),
        (
            "agent frequency",
            "Section 4.1 says comprehensive agents run primarily on Day 0 and later dates reuse decisions; Section 4.2 says the complete pipeline reruns every trading date.",
        ),
        (
            "price coverage",
            "Price snapshots are said to end 2025-07-27 while the principal evaluation continues to 2025-08-29.",
        ),
        (
            "Reddit coverage",
            "Reddit snapshots are said to end 2025-08-19 while daily agent execution is claimed through 2025-08-29.",
        ),
        ("case-study timing", "The WAB case is dated 2025-09-01, after the stated evaluation end date 2025-08-29."),
        ("rolling range", "Section 4.3 reports -2.42 to 5.27; Figure 3 reports -5.26 to 10.34."),
        (
            "rolling moments",
            "Section 4.3 reports mean 1.41 and SD 2.63; full-window 20-day sample-SD Sharpe with 2% annual RF exactly recovers extended validation 1.60 +/- 3.28, but not the paragraph values.",
        ),
        (
            "rolling convention",
            "At least three conventions are mixed: expanding sample-SD/zero-RF for Figure 3 extrema, population-SD/zero-RF for its final 3.89, and full-window sample-SD/2%-RF for extended mean/SD.",
        ),
        (
            "trace inclusion",
            "Appendix says one complete redacted trace is included, but only three WAB narrative snippets and a small perturbation table appear.",
        ),
        (
            "Deflated Sharpe",
            "Appendix says it is reported alongside naive Sharpe, but no Deflated Sharpe value appears.",
        ),
        (
            "diagnostic reporting",
            "Appendix promises Calmar, turnover, beta, tracking error and VaR/CVaR, but none is reported for the experiment.",
        ),
        (
            "reproducibility rating",
            "The paper assigns High under an all-five rubric while necessary inputs and a working one-command paper regeneration are absent.",
        ),
        (
            "alpha wording",
            "A return difference versus SPY is described as nontrivial alpha without a factor regression or beta estimate.",
        ),
    ]
    return [
        {"issue_id": f"RAP-I{index:02d}", "issue": issue, "evidence": evidence, "paper_result_credit": "no"}
        for index, (issue, evidence) in enumerate(issues, start=1)
    ]


def decision_rows(repo: Path) -> list[dict[str, str]]:
    files = sorted((repo / "testing/2025-01-01").glob("*.txt"))
    if len(files) != EXPECTED_DECISION_FILES:
        raise ValueError("decision-output count changed")
    headers: Counter[str] = Counter()
    finals: Counter[str] = Counter()
    flagged: list[str] = []
    patterns = [
        r"\brecommend(?:ation)?(?:ed)?\s+(?:to\s+)?sell\b",
        r"\bselling\s+(?:the\s+)?stock\b",
        r"\breduction of holdings\b",
        r"\breduce (?:our |the )?(?:position|exposure|holdings)\b",
        r"\bdo not provide a solid foundation for holding or buying\b",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        header = re.search(r"^DECISION:\s*(BUY|SELL|HOLD)", text, re.I | re.M)
        final = re.search(r"FINAL TRANSACTION PROPOSAL:\s*\*\*(BUY|SELL|HOLD)\*\*", text, re.I)
        decision = header.group(1).upper() if header else "MISSING"
        headers[decision] += 1
        if final:
            finals[final.group(1).upper()] += 1
        if decision == "BUY" and any(re.search(pattern, text.lower()) for pattern in patterns):
            flagged.append(path.name)
    expected_headers = Counter({"BUY": 417, "HOLD": 86})
    if headers != expected_headers or finals != Counter({"BUY": 417, "HOLD": 85}) or len(flagged) != 236:
        raise ValueError(f"decision-output distribution changed: {headers}, {finals}, {len(flagged)}")
    aapl = (repo / "testing/2025-01-01/AAPL.txt").read_text(encoding="utf-8")
    wab = (repo / "testing/2025-01-01/WAB.txt").read_text(encoding="utf-8")
    if (
        "recommendation to sell" not in aapl
        or "DECISION: BUY" not in aapl
        or "strategic reduction of holdings" not in wab
    ):
        raise ValueError("manual contradiction fixtures changed")
    return [
        {
            "check": "decision_file_coverage",
            "value": str(len(files)),
            "assessment": "only_2025-01-01",
            "evidence": "no later per-ticker decision files",
            "paper_result_credit": "no",
        },
        {
            "check": "header_distribution",
            "value": json.dumps(dict(headers), sort_keys=True),
            "assessment": "no_SELL_headers",
            "evidence": "long-only guardrails rewrite SELL to HOLD/BUY",
            "paper_result_credit": "no",
        },
        {
            "check": "final_proposal_distribution",
            "value": json.dumps(dict(finals), sort_keys=True),
            "assessment": "one_file_has_no_final_marker",
            "evidence": "502/503 explicit finals",
            "paper_result_credit": "no",
        },
        {
            "check": "automated_sell_language_flags_among_BUY",
            "value": str(len(flagged)),
            "assessment": "screen_only_not_236_manual_adjudications",
            "evidence": "regex flags recommendation/reduction language",
            "paper_result_credit": "no",
        },
        {
            "check": "AAPL_manual_trace",
            "value": "BUY header and final",
            "assessment": "contradiction",
            "evidence": "rationale explicitly supports recommendation to sell",
            "paper_result_credit": "no",
        },
        {
            "check": "WAB_manual_trace",
            "value": "BUY header and final",
            "assessment": "contradiction_and_wrong_case_date",
            "evidence": "Jan 1 rationale recommends strategic reduction; paper case is Sep 1 and claims aggressive positive stance",
            "paper_result_credit": "no",
        },
    ]


def search_rows(directory: Path) -> list[dict[str, str]]:
    files = sorted(directory.glob("*.json"))
    queries = {
        "01_exact_title.json": '"RAPTOR: Reasoned Agentic Portfolio Trading with Orchestrated Rebalancing"',
        "02_openreview_id.json": "ziuTkKhgT0",
        "03_anonymous_slug.json": '"RAPTOR-Reasoned-Agentic-Portfolio-Trading-with-Orchestrated-Rebalancing"',
        "04_author_title.json": '"Blake Almon" RAPTOR',
    }
    if [path.name for path in files] != sorted(queries):
        raise ValueError("GitHub search evidence set changed")
    rows: list[dict[str, str]] = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        names = [item["full_name"] for item in data.get("items", [])]
        rows.append(
            {
                "query": queries[path.name],
                "total_count": str(data["total_count"]),
                "incomplete_results": str(data["incomplete_results"]).lower(),
                "repositories": ";".join(names),
                "evidence_sha256": sha256(path),
                "native_credit": "no_search_itself_is_not_execution",
            }
        )
    if [int(row["total_count"]) for row in rows] != [0, 0, 1, 0]:
        raise ValueError("GitHub search totals changed")
    if (
        rows[2]["repositories"]
        != "anonymouspenguin3/RAPTOR-Reasoned-Agentic-Portfolio-Trading-with-Orchestrated-Rebalancing"
    ):
        raise ValueError("anonymous mirror search result changed")
    return rows


def fouropen_rows(directory: Path) -> list[dict[str, str]]:
    specs = {
        "root": ("401", "e9635ca18a865befc8be46485fb75ee4a33030472a4baceda124dc0f4e3d67eb", "not_connected"),
        "files": ("410", "033373a49223cadb7f1a6d8bdc90953b66346b9b4b03f493b0248a3bbd5c4dac", "repository_expired"),
        "options": ("410", "033373a49223cadb7f1a6d8bdc90953b66346b9b4b03f493b0248a3bbd5c4dac", "repository_expired"),
    }
    rows: list[dict[str, str]] = []
    for endpoint, (status, digest, error) in specs.items():
        body = directory / f"{endpoint}.body"
        headers = (directory / f"{endpoint}.headers").read_text(encoding="utf-8", errors="replace")
        statuses = re.findall(r"^HTTP/\S+\s+(\d{3})", headers, re.M)
        if not statuses or statuses[-1] != status or sha256(body) != digest:
            raise ValueError(f"4open evidence changed: {endpoint}")
        data = json.loads(body.read_text(encoding="utf-8"))
        if data.get("error") != error:
            raise ValueError(f"4open error changed: {endpoint}")
        rows.append(
            {
                "endpoint": endpoint,
                "final_http_status": status,
                "response": error,
                "body_sha256": digest,
                "reachable_artifact": "no",
            }
        )
    return rows


def native_execution_rows(repo: Path, python: Path) -> list[dict[str, str]]:
    env = {key: value for key, value in os.environ.items() if key not in {"OPENAI_API_KEY", "SK_PROJ_KEY"}}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    runner = subprocess.run(
        [str(python), "testing/mvo_blm_runner.py"],
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if (
        runner.returncode != 1
        or "testing/stock_prices.csv" not in runner.stderr
        or "FileNotFoundError" not in runner.stderr
    ):
        raise ValueError(f"candidate paper runner failure changed: {runner.returncode}: {runner.stderr[-500:]}")
    visualizer = subprocess.run(
        [str(python), "testing/scripts/visualize.py"],
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    outputs = sorted(path.name for path in (repo / "testing/results").glob("*"))
    expected_outputs = [
        "net_liquidation.csv",
        "net_liquidation.png",
        "rolling_sharpe.csv",
        "rolling_sharpe.png",
        "top_gainers.csv",
        "top_losers.csv",
    ]
    if visualizer.returncode != 0 or outputs != expected_outputs:
        raise ValueError(f"native visualizer execution changed: {visualizer.returncode}: {outputs}")
    source = (repo / "test_execution.py").read_text(encoding="utf-8")
    return [
        {
            "component": "testing/mvo_blm_runner.py",
            "attempted": "yes",
            "status": "blocked_before_backtest",
            "detail": "FileNotFoundError: tracked testing/stock_prices.csv is absent",
            "paper_result_credit": "no",
        },
        {
            "component": "testing/scripts/visualize.py",
            "attempted": "yes",
            "status": "pass",
            "detail": "six snapshot-derived CSV/PNG artifacts emitted",
            "paper_result_credit": "author_output_postprocessing_only",
        },
        {
            "component": "Python source compile",
            "attempted": "yes",
            "status": "pass",
            "detail": "94/94 anonymous-release Python files compiled in memory",
            "paper_result_credit": "no",
        },
        {
            "component": "pytest collection",
            "attempted": "collect_only",
            "status": "one_function",
            "detail": f"test_execution.py asserts={source.count('assert ')} and catches ImportError/Exception",
            "paper_result_credit": "no",
        },
        {
            "component": "end-to-end multi-agent backtest",
            "attempted": "no",
            "status": "not_operationally_defined",
            "detail": "unreleased inputs/API request logs plus conflicting runners would make a fresh run non-comparable",
            "paper_result_credit": "no",
        },
    ]


def native_metric_module_execution(
    repo: Path,
    python: Path,
    rolling_rows: list[dict[str, str]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    module_path = repo / "testing/mvo/metrics.py"
    if sha256(module_path) != EXPECTED_NATIVE_METRIC_MODULE_SHA256:
        raise ValueError("RAPTOR native metric module changed")
    program = r"""
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import socket
import sys
from pathlib import Path

import numpy as np

network_attempts = []
def block_connect(self, address):
    network_attempts.append(str(address))
    raise RuntimeError("network disabled during RAPTOR native metric audit")
socket.socket.connect = block_connect

root = Path(sys.argv[1])
module_path = root / "testing/mvo/metrics.py"
spec = importlib.util.spec_from_file_location("raptor_native_metrics", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

dates = []
portfolio_values = []
for directory in sorted((root / "testing").iterdir()):
    snapshot = directory / f"portfolio_snapshot_{directory.name}.json"
    if snapshot.exists() and len(directory.name) == 10:
        payload = json.loads(snapshot.read_text())
        dates.append(directory.name)
        portfolio_values.append(float(payload.get("net_liquidation", payload.get("portfolio_value"))))
returns = [
    portfolio_values[index] / portfolio_values[index - 1] - 1.0
    for index in range(1, len(portfolio_values))
]

outputs = {
    "rolling_sharpe_20": module.rolling_sharpe(returns, 20),
    "rolling_sortino_20": module.rolling_sortino(returns, 20),
    "rolling_calmar_60": module.rolling_calmar(returns, 60),
}
serialized = {}
encoded = {}
for name, series_values in outputs.items():
    canonical = "\n".join(
        "nan" if not math.isfinite(value) else format(value, ".17g")
        for value in series_values
    ).encode()
    serialized[name] = hashlib.sha256(canonical).hexdigest()
    encoded[name] = [
        None if not math.isfinite(value) else float(value)
        for value in series_values
    ]

print(json.dumps({
    "source_path": "testing/mvo/metrics.py",
    "source_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest(),
    "runtime": {
        "python": sys.version.split()[0],
        "numpy": importlib.metadata.version("numpy"),
    },
    "network_attempts": network_attempts,
    "snapshot_rows": len(portfolio_values),
    "return_rows": len(returns),
    "first_snapshot_date": dates[0],
    "last_snapshot_date": dates[-1],
    "output_sha256": serialized,
    "outputs": encoded,
}, sort_keys=True))
"""
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"OPENAI_API_KEY", "SK_PROJ_KEY", "PYTHONPATH"}
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(python), "-c", program, str(repo)],
            cwd=repo,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.stderr:
            raise ValueError(
                "RAPTOR native metric module emitted stderr: "
                + completed.stderr[-500:]
            )
        outputs.append(json.loads(completed.stdout))
    if outputs[0] != outputs[1]:
        raise ValueError("RAPTOR native metric module execution is nondeterministic")
    payload = outputs[0]
    if (
        payload["source_sha256"] != EXPECTED_NATIVE_METRIC_MODULE_SHA256
        or payload["output_sha256"] != EXPECTED_NATIVE_METRIC_OUTPUT_SHA256
        or payload["network_attempts"]
        or payload["snapshot_rows"] != EXPECTED_SNAPSHOTS
        or payload["return_rows"] != EXPECTED_SNAPSHOTS - 1
        or payload["first_snapshot_date"] != "2025-01-01"
        or payload["last_snapshot_date"] != "2025-08-29"
    ):
        raise ValueError(
            "RAPTOR native metric module provenance changed: "
            + json.dumps(
                {
                    "source_sha256": payload["source_sha256"],
                    "output_sha256": payload["output_sha256"],
                    "network_attempts": payload["network_attempts"],
                    "snapshot_rows": payload["snapshot_rows"],
                    "return_rows": payload["return_rows"],
                    "first_snapshot_date": payload["first_snapshot_date"],
                    "last_snapshot_date": payload["last_snapshot_date"],
                },
                sort_keys=True,
            )
        )

    expected_sharpe = [
        None
        if row["rolling_sharpe_20d_sample_sd"] == ""
        else float(row["rolling_sharpe_20d_sample_sd"])
        for row in rolling_rows[1:]
    ]
    native_sharpe = payload["outputs"]["rolling_sharpe_20"]
    if len(expected_sharpe) != len(native_sharpe):
        raise ValueError("RAPTOR native/audit Sharpe lengths differ")
    finite_errors = [
        abs(float(native) - float(expected))
        for native, expected in zip(native_sharpe, expected_sharpe)
        if native is not None and expected is not None
    ]
    nan_pattern_match = [
        value is None for value in native_sharpe
    ] == [
        value is None for value in expected_sharpe
    ]
    if (
        not nan_pattern_match
        or len(finite_errors) != 164
        or max(finite_errors) > 2e-15
    ):
        raise ValueError("RAPTOR native/audit rolling Sharpe diverged")

    rows = []
    direct_claim = {
        "rolling_sharpe_20": "Figure 3 rolling-Sharpe output correspondence",
        "rolling_sortino_20": "no exact published scalar/curve target",
        "rolling_calmar_60": "no exact published scalar/curve target",
    }
    for name, values in payload["outputs"].items():
        rows.append(
            {
                "function": name,
                "points": len(values),
                "finite_points": sum(value is not None for value in values),
                "output_sha256": payload["output_sha256"][name],
                "published_correspondence": direct_claim[name],
                "audit_series_compared": name == "rolling_sharpe_20",
                "audit_series_finite_points_compared": (
                    len(finite_errors) if name == "rolling_sharpe_20" else 0
                ),
                "maximum_audit_series_absolute_error": (
                    max(finite_errors) if name == "rolling_sharpe_20" else ""
                ),
                "nan_pattern_matches_audit": (
                    nan_pattern_match if name == "rolling_sharpe_20" else ""
                ),
                "native_agent_or_backtest_executed": False,
                "paper_result_credit": False,
            }
        )
    payload["conformance"] = {
        "execution_runs": 2,
        "functions_executed": 3,
        "output_points": sum(len(values) for values in payload["outputs"].values()),
        "rolling_sharpe_points_compared": len(native_sharpe),
        "rolling_sharpe_finite_points_compared": len(finite_errors),
        "rolling_sharpe_maximum_absolute_error": max(finite_errors),
        "rolling_sharpe_nan_pattern_match": nan_pattern_match,
        "native_agent_or_backtest_executed": False,
        "paper_result_credit": False,
    }
    return payload, rows


def artifact_rows() -> list[dict[str, str]]:
    return [
        {
            "artifact": "OpenReview record",
            "url": OPENREVIEW_RECORD,
            "status": "public_record_no_revisions_displayed",
            "relationship": "original workshop record",
            "credit": "paper provenance",
        },
        {
            "artifact": "CEUR final PDF",
            "url": CEUR_PDF,
            "status": "public_pinned_11_pages",
            "relationship": "published final paper",
            "credit": "paper provenance",
        },
        {
            "artifact": "listed 4open snapshot",
            "url": FOUROPEN_URL,
            "status": "expired_410_files_options_root_401",
            "relationship": "paper-listed anonymous artifact",
            "credit": "none",
        },
        {
            "artifact": "anonymous GitHub mirror",
            "url": ANONYMOUS_REPO_URL,
            "status": "public_pinned_Apache_2_0",
            "relationship": "high-confidence double-blind mirror inferred from exact slug, preparation script, dates and source identity",
            "credit": "source/output audit",
        },
        {
            "artifact": "author GitHub repository",
            "url": AUTHOR_REPO_URL,
            "status": "public_pinned_Apache_2_0",
            "relationship": "linked by hidden page-9 URI in the published PDF",
            "credit": "author attribution and source/output audit",
        },
        {
            "artifact": "current Yahoo S&P 500 chart response",
            "url": YAHOO_GSPC_URL,
            "status": "public_response_pinned_by_sha256",
            "relationship": "independent present-day endpoint check; not a paper-time frozen input",
            "credit": "three displayed scalar checks; no end-to-end result credit",
        },
    ]


def readme(manifest: dict[str, Any]) -> str:
    return f"""# RAPTOR paper/source replication audit

This package audits the 11-page published CEUR paper, its hidden author-repository
link, the expired 4open endpoint, a high-confidence public double-blind GitHub
mirror, the author-attributed repository, all 825 tracked source objects, every
released daily portfolio snapshot, and all 42 scalar empirical result assertions
or table cells in the paper. The two repositories share 815 byte-identical files;
the result snapshots and candidate runners are identical. The full four-commit
author history is also inventoried, including the later `validation_fixes` branch.

## Honest verdict

- **End-to-end RAPTOR result cells reproduced: 0/{manifest["displayed_scalar_results"]}.**
- **Published scalar units independently verified from author-shipped output:
  {manifest["author_output_verified_scalar_results"]}/{manifest["displayed_scalar_results"]}.**
  The released 166 daily snapshots recover the initial/final value, return,
  annualized return, volatility, Sharpe, Sortino, maximum drawdown, coverage, two
  Figure 3 extrema, and the extended-validation rolling mean/SD. This is output
  verification, not a rerun of the agent and portfolio pipeline.
- **Additional displayed scalar units independently checked from a pinned current
  public response: {manifest["current_public_response_verified_scalar_results"]}/{manifest["displayed_scalar_results"]}.**
  Yahoo's 165-session adjusted-close path from 2025-01-02 through 2025-08-29
  yields {manifest["benchmark_return_percent"]:.8f}% for the S&P 500, which rounds
  to 10.08%; subtracting it from the released RAPTOR endpoint yields 3.35 percentage
  points. These three are not paper-time input lineage.
- **Paper-internal arithmetic or exact repetition checks:
  {manifest["paper_internal_verified_scalar_results"]}/{manifest["displayed_scalar_results"]}.**
  Three Table 1 deltas equal perturbed minus base weights, and five explanation
  values exactly repeat their table cells. These are document-consistency checks,
  not author-output or native-agent results.
- Across author output, the current benchmark response, and paper-internal checks,
  {manifest["displayed_scalar_results_verified"]}/42 units verify. Including five
  checked rolling conflicts and two underspecified longer-window claims,
  {manifest["displayed_scalar_results_checked"]}/42 units are checked and
  {manifest["displayed_scalar_results_unavailable"]}/42 remain unavailable.
- **Published raster-curve correspondences verified:
  {manifest["published_figure_raster_curve_correspondences_verified"]}/3.**
  Figure 2's portfolio line regenerates all 7,313 exact blue pixels from the 166
  author snapshots. Its benchmark line regenerates all 3,132 published orange
  pixels from the pinned current Yahoo response; the regenerated image adds only
  15 orange pixels at the final segment. Across the complete 1500x600 chart,
  899,953/900,000 RGB pixels are identical. The author-executed notebook independently
  preserves both curves at display resolution and maps to the paper within two
  pixels after the documented 1.5x axes transform.
- Figure 3's released snapshot postprocessor regenerates the 20-day rolling-Sharpe
  curve with every exact-color pixel in both directions within two pixels. These
  are strong raster/output correspondences, not native-agent reruns: the paper
  publishes no raw figure arrays, the paper-time benchmark CSV remains absent,
  and exact published raw-series credit stays 0/3.
- The native snapshot visualizer executes and emits six CSV/PNG artifacts. The
  candidate backtest runner fails immediately because `testing/stock_prices.csv`
  is not released. The current public response verifies the historical benchmark
  raster and endpoint but does not supply paper-time provenance.
- The exact native `testing/mvo/metrics.py` module executes twice and deterministically
  emits {manifest["native_metric_output_points"]} values across rolling Sharpe,
  Sortino, and Calmar. Its {manifest["native_metric_rolling_sharpe_points_compared"]}
  Sharpe values match the independent audit series to a maximum absolute error of
  {manifest["native_metric_rolling_sharpe_maximum_absolute_error"]:.3g}. Sortino and
  Calmar have no exact published target, so this is native postprocessor evidence
  and earns no end-to-end agent or paper-result credit.
- The extended-validation rolling mean and SD are reproducible: requiring a full
  20-return window, subtracting 2%/252 daily, using sample SD, and annualizing by
  sqrt(252) gives {manifest["rolling_full20_rf2_sample_mean"]:.4f} and
  {manifest["rolling_full20_rf2_sample_sd"]:.4f}, which round to 1.60 and 3.28.
  All {manifest["rolling_section_20d_conventions"]} standard sample/population,
  expanding/full-window, and 0%/2% risk-free conventions match 0/4 cells in the
  Section 4.3 -2.42/5.27/1.41/2.63 quartet. Across every integer longer window
  from 21 to 165, {manifest["rolling_longer_any_endpoint_matches"]} of
  {manifest["rolling_longer_window_conventions"]} conventions hit at least one
  rounded 1.1/1.4 endpoint and {manifest["rolling_longer_both_endpoints_match"]}
  hit both, so the unspecified longer-window statement does not identify a
  reproducible protocol.

## Why the full paper is not reproduced

- The offline equity prices and paper-time SPY benchmark, Finnhub, Reddit, SimFin,
  and Perplexity snapshots are missing, as are exact API request/response logs and
  experiment seeds. The tracked dependency lock does not replace those inputs.
- The paper alternately specifies biweekly, daily/no-cadence, and every-ten-
  trading-day execution. The output-associated log instead records 17 rebalances
  beginning 2025-01-06 at a >=14-calendar-day cadence.
- The output runner uses at most 60 observations, risk aversion 5, tau .05, a
  top-50/top-10 universe, and recent-return or GPT-predicted daily views. The
  paper specifies 252 observations, risk aversion 3, tau .025, and categorical
  agent views mapped to annualized +/-2%/0.
- Transaction fees and slippage claimed in the paper are not deducted by the
  candidate execution paths. The WAB September 1 trace/table,
  full blackboard trace, Deflated Sharpe, and promised diagnostics are absent.
- The later `validation_fixes` branch adds no missing prices, benchmark input, or
  run outputs. Its generic statistics module has an `aligned_benchmarkay` NameError
  and an unseeded bootstrap; its enhancement template asserts unsupported 12.49%
  and 2020-2024 results that conflict with the final paper, so neither earns credit.
- Only January 1 has per-ticker decision files. Their headers contain 417 BUY,
  86 HOLD, and zero SELL decisions after long-only rewriting. AAPL and WAB are
  manually confirmed examples where a BUY header/final conflicts with a rationale
  recommending sale or reduced exposure.

## Files

- `source_provenance.json`, `artifact_access_audit.csv`,
  `source_search_inventory.csv`, and `fouropen_access_audit.csv`: pinned paper,
  repository, discovery, and access evidence.
- `source_file_inventory.csv` and `repository_relationship.csv`: complete
  anonymous-source inventory and anonymous/author byte relationship.
- `source_history_inventory.csv` and `validation_branch_inventory.csv`: every
  reachable author revision and the 20-file later-branch delta.
- `benchmark_snapshot_reproduction.csv`: the hash-pinned current Yahoo benchmark
  response, its 165 adjusted closes, and the explicit non-lineage boundary.
- `snapshot_metric_reproduction.csv`, `rolling_sharpe_reproduction.csv`,
  `rolling_claim_convention_forensics.csv`, `paper_internal_scalar_checks.csv`,
  and `displayed_result_conformance.csv`: output-derived calculations and the
  fail-closed 42-unit empirical denominator.
- `figure_series_conformance.csv` and `figure_raster_forensics.csv`: numeric-series
  availability and exact-color raster correspondence without raw-series inflation.
- `method_specification_audit.csv`, `paper_internal_consistency_audit.csv`, and
  `decision_trace_audit.csv`: method, paper, and released-decision boundaries.
- `native_execution.csv`, `native_execution.json`, and `manifest.json`: exact
  commands/outcomes and machine-readable verdict.
"""


def build(args: argparse.Namespace) -> dict[str, Any]:
    paper = args.paper.resolve()
    anonymous = args.anonymous_repo.resolve()
    author = args.author_repo.resolve()
    if sha256(args.ceur_record) != EXPECTED_CEUR_RECORD_SHA256:
        raise ValueError("CEUR volume record hash changed")
    _, pdf_links = validate_paper(paper)
    anonymous_paths = validate_repo(
        anonymous, EXPECTED_ANONYMOUS_HEAD, EXPECTED_ANONYMOUS_TREE_SHA256, EXPECTED_ANONYMOUS_ARCHIVE_SHA256
    )
    validate_repo(author, EXPECTED_AUTHOR_HEAD, EXPECTED_AUTHOR_TREE_SHA256, EXPECTED_AUTHOR_ARCHIVE_SHA256)
    if str(git(anonymous, "rev-list", "--max-parents=0", "HEAD")).strip() != EXPECTED_ANONYMOUS_INITIAL:
        raise ValueError("anonymous initial commit changed")

    source_files = source_inventory(anonymous, anonymous_paths)
    relationships = repository_relationship(anonymous, author)
    history = source_history_rows(author)
    validation_branch = validation_branch_rows(author)
    anonymous_snapshots = snapshot_rows(anonymous)
    author_snapshots = snapshot_rows(author)
    if any(sha256(left[1]) != sha256(right[1]) for left, right in zip(anonymous_snapshots, author_snapshots)):
        raise ValueError("anonymous and author snapshots differ")
    metrics, rolling, computed = metric_reproduction(anonymous)
    native_metric_module, native_metric_rows = native_metric_module_execution(
        anonymous,
        args.python.resolve(),
        rolling,
    )
    rolling_forensics, rolling_summary = rolling_claim_forensics(anonymous)
    internal_checks = paper_internal_scalar_checks()
    benchmark_rows, benchmark = benchmark_reproduction(args.yahoo_gspc_response.resolve(), computed["total_return_pct"])
    results = displayed_result_rows(computed, benchmark, rolling_summary)
    methods = method_rows()
    issues = consistency_rows()
    decisions = decision_rows(anonymous)
    searches = search_rows(args.github_search_dir)
    fouropen = fouropen_rows(args.fouropen_evidence_dir)
    executions = native_execution_rows(anonymous, args.python.resolve())
    executions.append(
        {
            "component": "testing/mvo/metrics.py",
            "attempted": "yes_twice",
            "status": "pass",
            "detail": (
                "three native rolling functions executed; 165 Sharpe points "
                "match the audit within 2e-15"
            ),
            "paper_result_credit": "author_output_postprocessing_only",
        }
    )
    figure_forensics = figure_raster_forensics(
        paper,
        anonymous,
        args.yahoo_gspc_response.resolve(),
    )
    figures = figure_rows(figure_forensics)
    artifacts = artifact_rows()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    csv_artifacts = (
        ("source_file_inventory.csv", source_files),
        ("repository_relationship.csv", relationships),
        ("source_history_inventory.csv", history),
        ("validation_branch_inventory.csv", validation_branch),
        ("snapshot_metric_reproduction.csv", metrics),
        ("benchmark_snapshot_reproduction.csv", benchmark_rows),
        ("rolling_sharpe_reproduction.csv", rolling),
        ("rolling_claim_convention_forensics.csv", rolling_forensics),
        ("paper_internal_scalar_checks.csv", internal_checks),
        ("displayed_result_conformance.csv", results),
        ("figure_series_conformance.csv", figures),
        ("figure_raster_forensics.csv", figure_forensics),
        ("method_specification_audit.csv", methods),
        ("paper_internal_consistency_audit.csv", issues),
        ("decision_trace_audit.csv", decisions),
        ("source_search_inventory.csv", searches),
        ("fouropen_access_audit.csv", fouropen),
        ("artifact_access_audit.csv", artifacts),
        ("native_execution.csv", executions),
        ("native_metric_module_conformance.csv", native_metric_rows),
    )
    for name, rows in csv_artifacts:
        write_csv(output / name, rows, list(rows[0]))

    role_counts = Counter(row["role"] for row in source_files)
    source_provenance = {
        "paper": "RAPTOR: Reasoned Agentic Portfolio Trading with Orchestrated Rebalancing",
        "authors": [
            "Blake Almon",
            "Matthew Caliboso",
            "Alex Kim",
            "Rohan Dutta",
            "Rohan Raman",
            "Mithil Srungarapu",
            "Vasu Sharma",
            "Kevin Zhu",
            "Sunishchal Dev",
        ],
        "openreview_record": OPENREVIEW_RECORD,
        "openreview_record_note": "record inspected in signed-in browser; revision history displayed no revisions; command-line PDF access was Cloudflare-blocked",
        "ceur_record": CEUR_RECORD,
        "ceur_record_sha256": sha256(args.ceur_record),
        "ceur_pdf": CEUR_PDF,
        "ceur_pdf_sha256": sha256(paper),
        "ceur_pdf_pages": EXPECTED_PDF_PAGES,
        "ceur_pdf_pages_visually_inspected": EXPECTED_PDF_PAGES,
        "pdf_links": pdf_links,
        "listed_anonymous_artifact": FOUROPEN_URL,
        "anonymous_github_repository": ANONYMOUS_REPO_URL,
        "anonymous_repository_head": EXPECTED_ANONYMOUS_HEAD,
        "anonymous_repository_initial_commit": EXPECTED_ANONYMOUS_INITIAL,
        "anonymous_repository_tree_sha256": EXPECTED_ANONYMOUS_TREE_SHA256,
        "anonymous_repository_archive_sha256": EXPECTED_ANONYMOUS_ARCHIVE_SHA256,
        "author_github_repository": AUTHOR_REPO_URL,
        "author_repository_head": EXPECTED_AUTHOR_HEAD,
        "author_repository_tree_sha256": EXPECTED_AUTHOR_TREE_SHA256,
        "author_repository_archive_sha256": EXPECTED_AUTHOR_ARCHIVE_SHA256,
        "author_repository_reachable_commits": len(history),
        "author_validation_branch_head": EXPECTED_AUTHOR_VALIDATION_HEAD,
        "author_validation_branch_files": EXPECTED_AUTHOR_VALIDATION_FILES,
        "author_validation_branch_paper_result_credit": "none_later_generic_framework_without_missing_inputs_or_results",
        "yahoo_gspc_url": YAHOO_GSPC_URL,
        "yahoo_gspc_response_sha256": sha256(args.yahoo_gspc_response),
        "yahoo_gspc_retrieved_at_note": "file modification timestamp 2026-08-13T12:30:49-04:00; pinned present-day response, not a paper-time frozen source",
        "anonymous_to_author_relationship": "high-confidence double-blind derivative/mirror inference; exact 4open-to-GitHub redirect is unavailable after expiry",
        "tracked_source_files": len(source_files),
        "source_role_counts": dict(sorted(role_counts.items())),
        "byte_identical_common_files": 815,
        "paper_relevant_candidate_runners_identical": True,
        "all_166_snapshots_identical": True,
        "native_metric_module_path": "testing/mvo/metrics.py",
        "native_metric_module_sha256": EXPECTED_NATIVE_METRIC_MODULE_SHA256,
        "license": "Apache-2.0",
    }
    write_json(output / "source_provenance.json", source_provenance)
    write_json(
        output / "native_metric_module_execution.json",
        native_metric_module,
    )

    verified = [row for row in results if row["verification_status"].startswith("verified")]
    author_verified = sum(row["verification_source"] == "author_output" for row in verified)
    current_public_verified = sum(row["verification_source"] == "current_public_response" for row in verified)
    paper_internal_verified = sum(
        row["verification_source"] == "paper_internal_consistency" for row in verified
    )
    checked_results = sum(row["verification_status"] != "unavailable" for row in results)
    rolling_conflicts = sum("conflict" in row["verification_status"] for row in results)
    rolling_underspecified = sum(
        row["verification_status"].startswith("checked_underspecified") for row in results
    )
    native = {
        "native_source_available": True,
        "native_postprocessor_executed": True,
        "native_postprocessor_status": "pass",
        "native_metric_module_executed": True,
        "native_metric_module_source_sha256": EXPECTED_NATIVE_METRIC_MODULE_SHA256,
        "native_metric_module_execution_runs": native_metric_module[
            "conformance"
        ]["execution_runs"],
        "native_metric_functions_executed": native_metric_module[
            "conformance"
        ]["functions_executed"],
        "native_metric_output_points": native_metric_module["conformance"][
            "output_points"
        ],
        "native_metric_rolling_sharpe_points_compared": native_metric_module[
            "conformance"
        ]["rolling_sharpe_points_compared"],
        "native_metric_rolling_sharpe_finite_points_compared": (
            native_metric_module["conformance"][
                "rolling_sharpe_finite_points_compared"
            ]
        ),
        "native_metric_rolling_sharpe_maximum_absolute_error": (
            native_metric_module["conformance"][
                "rolling_sharpe_maximum_absolute_error"
            ]
        ),
        "native_metric_rolling_sharpe_nan_pattern_match": native_metric_module[
            "conformance"
        ]["rolling_sharpe_nan_pattern_match"],
        "candidate_backtest_runner_attempted": True,
        "candidate_backtest_runner_status": "blocked_missing_testing_stock_prices_csv",
        "end_to_end_multi_agent_backtest_attempted": False,
        "end_to_end_reason": "unreleased_inputs_and_request_logs_plus_conflicting_paper_and_runner_protocols",
        "author_output_verified_scalar_results": author_verified,
        "current_public_response_verified_scalar_results": current_public_verified,
        "paper_internal_verified_scalar_results": paper_internal_verified,
        "displayed_scalar_results_verified": len(verified),
        "displayed_scalar_results_checked": checked_results,
        "rolling_claim_conflicts_checked": rolling_conflicts,
        "rolling_claims_underspecified_checked": rolling_underspecified,
        "displayed_scalar_results": len(results),
        "end_to_end_result_cells_reproduced": 0,
        "paper_result_credit": "output_current_response_or_paper_internal_verification_only_no_end_to_end_result_credit",
        "llm_calls_made": 0,
    }
    write_json(output / "native_execution.json", native)

    manifest = {
        "audit": "RAPTOR OpenReview / CEUR paper and public-source audit",
        "overall_fidelity": "full_author_history_and_166_output_snapshots_audited_36_of_42_scalar_units_checked_29_verified_18_author_output_3_current_public_8_paper_internal_5_conflicts_2_underspecified_6_unavailable_zero_end_to_end_result_cells_reproduced",
        "official_pdf_pages_audited": EXPECTED_PDF_PAGES,
        "official_pdf_pages_visually_inspected": EXPECTED_PDF_PAGES,
        "tracked_source_files": len(source_files),
        "compiled_python_files": sum(row["compile_status"] == "compiled" for row in source_files),
        "author_result_snapshots": len(anonymous_snapshots),
        "displayed_scalar_results": len(results),
        "author_output_verified_scalar_results": author_verified,
        "current_public_response_verified_scalar_results": current_public_verified,
        "displayed_scalar_results_verified": len(verified),
        "paper_internal_verified_scalar_results": paper_internal_verified,
        "displayed_scalar_results_checked": checked_results,
        "rolling_claim_conflicts_checked": rolling_conflicts,
        "rolling_claims_underspecified_checked": rolling_underspecified,
        "displayed_scalar_results_unavailable": sum(
            row["verification_status"] == "unavailable" for row in results
        ),
        "paper_internal_scalar_checks": len(internal_checks),
        "rolling_claim_forensic_rows": rolling_summary["rows"],
        "rolling_section_20d_conventions": rolling_summary["section_20d_conventions"],
        "rolling_section_20d_claim_cells_matching": rolling_summary[
            "section_20d_claim_cells_matching"
        ],
        "rolling_longer_window_conventions": rolling_summary["longer_window_conventions"],
        "rolling_longer_any_endpoint_matches": rolling_summary[
            "longer_any_endpoint_matches"
        ],
        "rolling_longer_both_endpoints_match": rolling_summary[
            "longer_both_endpoints_match"
        ],

        "benchmark_observations": int(benchmark["observations"]),
        "benchmark_return_percent": benchmark["benchmark_return_pct"],
        "benchmark_excess_percentage_points": benchmark["excess_percentage_points"],
        "author_repository_reachable_commits": len(history),
        "author_validation_branch_files": EXPECTED_AUTHOR_VALIDATION_FILES,
        "end_to_end_result_cells_reproduced": 0,
        "figure_series": len(figures),
        "exact_published_figure_series_reproduced": 0,
        "published_figure_raster_curve_correspondences_verified": sum(
            row["raster_correspondence_verified"] == "yes" for row in figure_forensics
        ),
        "figure_2_whole_image_exact_rgb_fraction": float(
            figure_forensics[0]["whole_figure_exact_rgb_fraction"]
        ),
        "figure_2_whole_image_different_pixels": 47,
        "figure_2_author_notebook_png_sha256": EXPECTED_NOTEBOOK_FIGURE_2_PNG_SHA256,
        "method_dimensions": len(methods),
        "internal_consistency_issues": len(issues),
        "decision_files": EXPECTED_DECISION_FILES,
        "decision_BUY": 417,
        "decision_HOLD": 86,
        "decision_SELL": 0,
        "repository_searches": len(searches),
        "anonymous_author_byte_identical_files": 815,
        "native_postprocessor_status": "pass",
        "native_metric_module_executed": True,
        "native_metric_module_source_sha256": EXPECTED_NATIVE_METRIC_MODULE_SHA256,
        "native_metric_module_execution_runs": native_metric_module[
            "conformance"
        ]["execution_runs"],
        "native_metric_functions_executed": native_metric_module[
            "conformance"
        ]["functions_executed"],
        "native_metric_output_points": native_metric_module["conformance"][
            "output_points"
        ],
        "native_metric_rolling_sharpe_points_compared": native_metric_module[
            "conformance"
        ]["rolling_sharpe_points_compared"],
        "native_metric_rolling_sharpe_maximum_absolute_error": (
            native_metric_module["conformance"][
                "rolling_sharpe_maximum_absolute_error"
            ]
        ),
        "candidate_backtest_runner_status": "blocked_missing_testing_stock_prices_csv",
        "rolling_sample_min": computed["rolling_sample_min"],
        "rolling_sample_max": computed["rolling_sample_max"],
        "rolling_sample_mean": computed["rolling_sample_mean"],
        "rolling_sample_sd": computed["rolling_sample_sd"],
        "rolling_sample_final": computed["rolling_sample_final"],
        "rolling_population_final": computed["rolling_population_final"],
        "rolling_full20_rf2_sample_min": computed["rolling_full20_rf2_sample_min"],
        "rolling_full20_rf2_sample_max": computed["rolling_full20_rf2_sample_max"],
        "rolling_full20_rf2_sample_mean": computed["rolling_full20_rf2_sample_mean"],
        "rolling_full20_rf2_sample_sd": computed["rolling_full20_rf2_sample_sd"],
        "rolling_full20_rf2_sample_final": computed["rolling_full20_rf2_sample_final"],
        "paper_result_credit": "output_current_response_or_paper_internal_verification_only_no_end_to_end_result_credit",
    }
    write_json(output / "manifest.json", manifest)
    (output / "README.md").write_text(readme(manifest), encoding="utf-8")
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--paper",
        type=Path,
        default=ROOT
        / "literature_review/papers/56_raptor_reasoned_agentic_portfolio_trading_with_orchestrated_rebalancing.pdf",
    )
    result.add_argument("--ceur-record", type=Path, required=True)
    result.add_argument("--anonymous-repo", type=Path, required=True)
    result.add_argument("--author-repo", type=Path, required=True)
    result.add_argument("--github-search-dir", type=Path, required=True)
    result.add_argument("--fouropen-evidence-dir", type=Path, required=True)
    result.add_argument(
        "--yahoo-gspc-response",
        type=Path,
        default=ROOT / "paper_runs/paper_replication_audits/raptor/yahoo_gspc_response.json",
    )
    result.add_argument("--python", type=Path, required=True)
    result.add_argument("--output", type=Path, default=ROOT / "paper_runs/paper_replication_audits/raptor")
    return result


def main() -> None:
    print(json.dumps(build(parser().parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
