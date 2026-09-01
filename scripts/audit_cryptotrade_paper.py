#!/usr/bin/env python3
"""Audit CryptoTrade's paper tables against pinned public code, data, and history.

The audit executes the deterministic environment, traditional signal strategies,
and recovered paper-author action traces. It never imports the API utility, calls
an LLM endpoint, or treats a numerically matching trace with a model/period conflict
as method-faithful evidence.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from argparse import Namespace
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd


SOURCE_COMMIT = "210da73af5f17992be425e61305524a5c24dae40"
SOURCE_ROOT_COMMIT = "750df03512a9263512bc782bc28e602ab74243f7"
SOURCE_COMMIT_COUNT = 11
AUTHOR_HISTORY_REF = "refs/remotes/fork_nchen/nchen"
AUTHOR_HISTORY_COMMIT = "2a6cefe6ea7dc291070b63e5699f95370a7d32d7"
AUTHOR_HISTORY_ROOT_COMMIT = "0ec929be59142b73ba6a473926c4275b235d34c8"
AUTHOR_HISTORY_COMMIT_COUNT = 89
AUTHOR_PRE_REROOT_SNAPSHOT = "255c3f5db137474ff1828129d1126abd61580ec2"
PAPER_SHA256 = "376606b05f5398c9200b0a560690693ea0a023a97631175ae02528e4dffec5cf"
PAPER_URL = "https://aclanthology.org/2024.emnlp-main.63.pdf"
SOURCE_URL = "https://github.com/Xtra-Computing/CryptoTrade"
ORIGINAL_ANONYMOUS_SOURCE_URL = "https://anonymous.4open.science/r/CryptoTrade-Public-92FC/"
DEFAULT_LSTM_RESULTS_ROOT = Path(
    "/nfs/roberts/scratch/pi_btk22/zc362/cryptotrade_lstm_results"
)
DEFAULT_LSTM_PYTHON_WRAPPER = Path(__file__).with_name("run_aapm_paper_python.sh")
LSTM_RESULT_SHA256 = {
    "cryptotrade_lstm_cell_census.csv": "db111f794da535e7d91f2cf6e5afa620726f8b0667d4fb1f9be1d94be93391ca",
    "cryptotrade_lstm_cell_summary.csv": "3ad76d582d7a5cb8cb1389956a412383e68df2c676d198e9bc11a5c3f05c491f",
    "cryptotrade_lstm_paper_grid.csv": "1b4fe9662eef41154cac6e289b4efe5dc5f39d92c084eac94e67e2e1d7ed4b73",
    "cryptotrade_lstm_paper_grid.json": "6402c7a7a127a896d039354a4ee408b696e073ca1d2940493f1568640f71498d",
    "cryptotrade_lstm_paper_grid_seed0_repeat.csv": "1f5aa20173423928eea3d438262a31a1e06c6a73a0cdf536cc3870d39ac49ea3",
    "cryptotrade_lstm_paper_grid_seed0_repeat.json": "fb84e66038ef2a7c9684dec1e9a76bbed199a5097b31f37afaa599db2d2d140c",
    "cryptotrade_lstm_probe.json": "b6f82943df313ff93934b66c06192b0ff51458f1e7c56972bfe51e27908aa2fe",
    "cryptotrade_lstm_validation_grid.csv": "dfed0873933f8efcb0d866f457f1e393dda664944fca21e3a76e4f5746ea1225",
    "cryptotrade_lstm_validation_selection.json": "1900884d4cce8a7bf7328f9ec6365b3263ed35ee21c999e44f763bef351afe57",
}
LSTM_COMPATIBLE_ENVIRONMENT = {
    "python": "3.10.8",
    "torch": "2.4.1+cpu",
    "numpy": "2.1.1",
    "pandas": "2.2.3",
    "scikit_learn": "1.5.2",
    "torch_cuda_available": False,
}
PUBLIC_FORK_CENSUS_CHECKED_AT = "2026-08-14"
PUBLIC_FORKS_TOTAL = 37
PUBLIC_FORK_BRANCH_REFS_TOTAL = 39
PUBLIC_FORK_BRANCH_REF_SEQUENCE_SHA256 = "5c3c428ac7d6a3c2432c004ce2288f75081ae632abffb9a4128c762fcbe00bd9"
PUBLIC_FORK_BRANCH_REFS_REACHABLE_FROM_OFFICIAL_OR_AUTHOR_HISTORY = 35
PUBLIC_DIVERGENT_FORK_HEADS = (
    {
        "repository": "kidclone3/CryptoTrade",
        "branch": "master",
        "ref": "refs/remotes/fork_census/kidclone3-master",
        "head_commit": "685a33ae9e332c2aff7851c3b2ecaff7137136c9",
        "divergent_commits": 1,
        "divergent_commit_sequence_sha256": "a828baa59ff0b23d8da0945f72996fcaa1c7401028c0b45dc6942bb3f06b6ce1",
        "changed_paths": 8,
        "changed_path_sequence_sha256": "1fb5d6d9a6225b98b617c5022b793f610c92cdcb928ccc08d423e1da2401f790",
        "result_or_log_paths": 3,
        "relationship": "unaffiliated_postpaper_gemini_2_5_experiment_with_empty_result_file_and_nonpaper_logs",
    },
    {
        "repository": "ADizzyPython/CryptoTrade",
        "branch": "master",
        "ref": "refs/remotes/fork_census/adizzypython-master",
        "head_commit": "53ae996cd0232b43d3aef9ec49cf3bb22b017ac4",
        "divergent_commits": 2,
        "divergent_commit_sequence_sha256": "573687269adf8afbb9f8ebf69ea38c582a9c2ed81612ce4f8fb163468d66a521",
        "changed_paths": 409,
        "changed_path_sequence_sha256": "2c6a587b76ee12e4ff92d062c1b41868f27dc0450db34408edb421e056af8f6a",
        "result_or_log_paths": 4,
        "relationship": "unaffiliated_postpaper_nifty50_rewrite_and_gemini_logs_not_cryptotrade_paper_runs",
    },
    {
        "repository": "JunTingLin/CryptoTrade",
        "branch": "master",
        "ref": "refs/remotes/fork_census/juntinglin-master",
        "head_commit": "f8a43b39d922f0f1b468855f63e224235b729d24",
        "divergent_commits": 29,
        "divergent_commit_sequence_sha256": "ca37f9c0dde714c205cfc7206a23d33365354c87a4520444e9cd0b46d7475c43",
        "changed_paths": 1931,
        "changed_path_sequence_sha256": "63aa6b62a09b53a9d00a513dd015bea92eeea0bb7cbde9984fd570a71ebc4bca",
        "result_or_log_paths": 0,
        "relationship": "unaffiliated_postpaper_local_model_taiwan_and_six_agent_extension_without_result_artifacts",
    },
    {
        "repository": "0x0wRangler/CryptoTrade",
        "branch": "master",
        "ref": "refs/remotes/fork_census/0x0wrangler-master",
        "head_commit": "3932f2d4421e1eb423a112f715fd34abaa6c65f6",
        "divergent_commits": 2,
        "divergent_commit_sequence_sha256": "0df459563d61a2f00de9bd77ce524e392828fbb1976fefd31a082bf495b4811b",
        "changed_paths": 2,
        "changed_path_sequence_sha256": "502ccfbdb07dcc25fe98f003b92e77ba3309e1c6a73f7a8984120fb602939124",
        "result_or_log_paths": 0,
        "relationship": "unaffiliated_postpaper_descriptor_and_reference_pdf_only",
    },
)
DISPLAY_TOLERANCE = 0.005 + 1e-12
METRICS = (
    "total_return_pct",
    "daily_return_mean_pct",
    "daily_return_std_pct",
    "sharpe_ratio",
)
REGIMES = ("bull", "sideways", "bear")
TRADITIONAL_STRATEGIES = {
    "buy_and_hold",
    "sma",
    "slma",
    "macd",
    "bollinger_bands",
}
TIME_SERIES_STRATEGIES = {"lstm", "informer", "autoformer", "timesnet", "patchtst"}
LLM_STRATEGIES = {"gpt_3_5_turbo", "gpt_4", "gpt_4o"}
SMA_PERIODS = (5, 10, 15, 20, 30)


# Transcribed from Tables 2--4 of the pinned official PDF. Each row is:
# asset|strategy|three total returns|three daily means|three daily stds|three Sharpes,
# with values ordered bull, sideways, bear within each metric block.
PAPER_ROWS_TEXT = """
btc|buy_and_hold|39.66|-0.83|-15.61|0.56|0.00|-0.24|2.23|1.74|2.07|0.25|0.00|-0.11
btc|sma|22.58|3.65|-21.74|0.35|0.06|-0.36|1.89|1.21|1.25|0.18|0.05|-0.29
btc|slma|38.53|-3.14|-7.68|0.55|-0.04|-0.11|2.21|0.83|1.23|0.25|-0.05|-0.09
btc|macd|13.57|-6.71|-9.51|0.22|-0.09|-0.14|1.45|1.01|1.56|0.15|-0.09|-0.09
btc|bollinger_bands|2.97|-3.19|-1.17|0.05|-0.04|-0.02|0.32|0.87|0.51|0.15|-0.05|-0.03
btc|lstm|31.67|-4.13|-17.20|0.47|-0.05|-0.28|2.11|1.62|1.27|0.22|-0.03|-0.22
btc|informer|0.34|-2.33|-13.38|0.01|-0.03|-0.21|0.82|0.54|1.02|0.01|-0.06|-0.21
btc|autoformer|14.73|-4.90|-12.72|0.24|-0.07|-0.20|1.65|1.15|1.13|0.14|-0.06|-0.18
btc|timesnet|2.84|-5.12|-13.64|0.05|-0.07|-0.22|1.06|1.10|1.04|0.05|-0.06|-0.21
btc|patchtst|1.79|-5.02|-21.94|0.03|-0.07|-0.37|0.71|0.57|1.05|0.04|-0.13|-0.35
btc|gpt_3_5_turbo|18.84|0.33|-9.12|0.30|0.01|-0.14|1.69|1.19|1.52|0.18|0.01|-0.09
btc|gpt_4|26.35|-4.07|-11.72|0.40|-0.05|-0.18|1.76|1.43|1.67|0.23|-0.04|-0.11
btc|gpt_4o|28.47|-5.08|-13.71|0.43|-0.07|-0.21|1.89|1.14|1.71|0.23|-0.06|-0.12
eth|buy_and_hold|22.59|-1.91|-12.24|0.36|-0.01|-0.17|2.62|1.94|2.39|0.14|-0.00|-0.07
eth|sma|10.17|-5.45|-10.12|0.18|-0.15|-0.15|2.29|1.64|1.64|0.08|-0.07|-0.09
eth|slma|5.20|-2.62|-15.90|0.11|-0.03|-0.24|2.37|1.08|1.86|0.05|-0.03|-0.13
eth|macd|7.72|0.77|-12.15|0.13|0.02|-0.18|1.22|1.43|1.56|0.10|0.01|-0.12
eth|bollinger_bands|2.59|4.47|-0.41|0.04|0.07|0.00|0.40|1.02|0.58|0.11|0.06|-0.01
eth|lstm|22.12|1.27|-13.22|0.36|0.02|-0.19|2.59|1.11|2.36|0.14|0.15|-0.08
eth|informer|14.55|-4.74|-11.49|0.23|-0.06|-0.17|1.54|1.45|1.65|0.15|-0.04|-0.10
eth|autoformer|7.77|-10.06|-19.44|0.13|-0.14|-0.31|1.81|1.33|1.61|0.08|-0.10|-0.20
eth|timesnet|13.31|-8.08|-10.64|0.21|-0.11|-0.16|1.50|1.08|1.04|0.14|-0.10|-0.16
eth|patchtst|8.95|-9.64|-13.76|0.15|-0.13|-0.21|1.37|1.66|1.39|0.11|-0.11|-0.15
eth|gpt_3_5_turbo|18.91|-5.02|-14.40|0.30|-0.06|-0.22|2.01|1.56|2.08|0.15|-0.04|-0.10
eth|gpt_4|25.72|0.72|-13.72|0.41|0.03|-0.21|2.45|1.67|2.02|0.17|0.02|-0.10
eth|gpt_4o|25.47|-6.59|-15.35|0.40|-0.07|-0.23|2.25|1.81|2.16|0.18|-0.04|-0.11
sol|buy_and_hold|176.72|-3.23|-36.08|1.83|0.01|-0.61|6.00|3.92|3.45|0.30|0.00|-0.18
sol|sma|119.37|-0.62|1.04|1.43|0.03|0.02|5.67|3.06|0.10|0.25|0.01|0.16
sol|slma|169.98|6.22|-8.11|1.78|0.16|-0.11|5.93|3.23|1.88|0.30|0.05|-0.06
sol|macd|23.25|-9.78|-21.07|0.35|-0.16|-0.33|1.76|2.38|2.44|0.20|-0.07|-0.13
sol|bollinger_bands|2.92|-0.46|-21.69|0.05|0.00|-0.35|0.35|1.23|1.75|0.13|-0.00|-0.20
sol|lstm|144.69|-3.56|-36.75|1.61|0.01|-0.63|5.69|3.90|3.43|0.28|0.00|-0.18
sol|informer|41.85|-6.55|-26.13|0.58|-0.10|-0.43|1.90|2.00|2.36|0.31|-0.05|-0.18
sol|autoformer|35.86|-6.17|-23.56|0.51|-0.10|-0.38|1.97|1.90|2.35|0.26|-0.05|-0.16
sol|timesnet|45.28|-10.63|-21.60|0.64|-0.18|-0.35|2.66|2.01|1.75|0.24|-0.09|-0.20
sol|patchtst|18.45|-7.10|-27.86|0.29|-0.11|-0.46|1.57|1.98|2.49|0.18|-0.06|-0.19
sol|gpt_3_5_turbo|102.45|-13.05|-24.08|1.26|-0.23|-0.39|4.54|2.42|2.60|0.28|-0.15|-0.10
sol|gpt_4|99.84|-2.16|-19.55|1.24|0.01|-0.31|4.53|3.33|2.35|0.27|0.00|-0.13
sol|gpt_4o|115.18|3.09|-16.32|1.38|0.11|-0.25|4.98|3.31|2.35|0.28|0.03|-0.10
"""


PAPER_SPLITS: Mapping[str, Mapping[str, Tuple[str, str, float, float, float]]] = {
    "btc": {
        "validation": ("2023-01-19", "2023-03-13", 20977.48, 20628.03, -1.67),
        "bear": ("2023-04-12", "2023-06-16", 30462.48, 25575.28, -15.61),
        "sideways": ("2023-06-17", "2023-08-25", 26328.68, 26163.68, -0.83),
        "bull": ("2023-10-01", "2023-12-01", 26967.40, 37718.01, 39.66),
    },
    "eth": {
        "validation": ("2023-01-13", "2023-03-12", 1417.13, 1429.60, 0.88),
        "bear": ("2023-04-12", "2023-06-16", 1892.94, 1664.98, -12.24),
        "sideways": ("2023-06-20", "2023-08-31", 1734.79, 1705.11, -1.91),
        "bull": ("2023-10-01", "2023-12-01", 1671.00, 2051.76, 22.59),
    },
    "sol": {
        "validation": ("2023-01-14", "2023-03-12", 18.29, 18.24, -0.27),
        "bear": ("2023-04-12", "2023-06-16", 23.02, 14.76, -36.08),
        "sideways": ("2023-07-08", "2023-08-31", 21.49, 20.83, -3.23),
        "bull": ("2023-10-01", "2023-12-01", 21.39, 59.25, 176.72),
    },
}


PAPER_ABLATION = {
    "full": (28.47, 0.23),
    "without_reflection": (17.14, 0.06),
    "without_news": (19.69, 0.06),
    "without_transaction_statistics": (12.70, 0.05),
    "without_technical": (17.27, 0.05),
    "base": (8.40, 0.03),
}

ABLATION_FLAG_VARIANTS = {
    (1, 1, 1, 1): "full",
    (0, 1, 1, 1): "without_reflection",
    (1, 0, 1, 1): "without_news",
    (1, 1, 0, 1): "without_transaction_statistics",
    (1, 1, 1, 0): "without_technical",
    (0, 0, 0, 0): "base",
}
ABLATION_TRACE_PINS = {
    "full": {
        "commit": "a27f56c93941c1d50ee73dda9d2dff3c8117182f",
        "blob": "b68ddce85603ba02435749e14a1d344504ef92ef",
        "path": "logs/btc-bull.out",
    },
    "without_reflection": {
        "commit": "2074e0498c2502ba934d68355d98c0eb69eb65e7",
        "blob": "22353ec7ca5b0f58b758f0afe4a4aa5a93044103",
        "path": "logs/run_agent-wo-reflection.out",
    },
    "without_news": {
        "commit": "b1684705ff235cc216d6994e63f7166cc1f75538",
        "replay_commit": "2074e0498c2502ba934d68355d98c0eb69eb65e7",
        "blob": "4872503f7114fc2e9c2a765a3675c1a06eaab052",
        "path": "logs/run_agent-wo-news.out",
    },
    "without_transaction_statistics": {
        "commit": "308c661262edf26eb375e08a1cee265a4f5388dd",
        "blob": "e7fb06974c2b5343d72a5490470830f76209e135",
        "path": "logs/run_agent-wo-txnstat.out",
    },
    "without_technical": {
        "commit": "308c661262edf26eb375e08a1cee265a4f5388dd",
        "blob": "90d1fb0ac5825d4f9334f04ea2cad43d75df86bc",
        "path": "logs/run_agent-wo-tech.out",
    },
    "base": {
        "commit": "308c661262edf26eb375e08a1cee265a4f5388dd",
        "blob": "aeda712caf0c7411e9506996a45008b950f8e4e8",
        "path": "logs/run_agent-base.out",
    },
}
ABLATION_FULL_CONTEXT_TRACE_PIN = {
    "commit": "f26948fd8e7e2163d0a74eaf9cd299c8476dca01",
    "blob": "986266c278f520a6d205f336287d366aeea06eca",
    "path": "logs/run_agent-full-28.11.out",
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


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def line_sequence_sha256(values: Sequence[str]) -> str:
    payload = "".join(f"{value}\n" for value in values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def result_or_log_path(path: str) -> bool:
    lowered = path.lower()
    parts = lowered.split("/")
    name = parts[-1]
    return (
        lowered.endswith((".out", ".log"))
        or any(part in {"log", "logs", "output", "outputs", "result", "results"} for part in parts)
        or name.startswith("env_results")
    )


def public_fork_divergence_inventory(source_root: Path) -> List[Dict[str, Any]]:
    """Fail closed over every divergent head in the dated public fork census."""
    rows: List[Dict[str, Any]] = []
    for expected in PUBLIC_DIVERGENT_FORK_HEADS:
        ref = str(expected["ref"])
        head_commit = git(source_root, "rev-parse", ref).strip()
        if head_commit != expected["head_commit"]:
            raise RuntimeError(f"CryptoTrade fork-census head changed for {ref}")
        if git(source_root, "merge-base", SOURCE_COMMIT, ref).strip() != SOURCE_COMMIT:
            raise RuntimeError(f"CryptoTrade fork-census head is not based on the pinned official head: {ref}")

        commits = git(source_root, "rev-list", "--reverse", f"{SOURCE_COMMIT}..{ref}").splitlines()
        changed_paths = sorted(git(source_root, "diff", "--name-only", SOURCE_COMMIT, ref).splitlines())
        result_paths = [path for path in changed_paths if result_or_log_path(path)]
        observed = {
            "divergent_commits": len(commits),
            "divergent_commit_sequence_sha256": line_sequence_sha256(commits),
            "changed_paths": len(changed_paths),
            "changed_path_sequence_sha256": line_sequence_sha256(changed_paths),
            "result_or_log_paths": len(result_paths),
        }
        for field, value in observed.items():
            if value != expected[field]:
                raise RuntimeError(
                    f"CryptoTrade fork-census {field} changed for {ref}: expected {expected[field]!r}, found {value!r}"
                )

        committed_at, author_name, subject = (
            git(
                source_root,
                "show",
                "-s",
                "--format=%aI%x09%an%x09%s",
                ref,
            )
            .rstrip("\n")
            .split("\t", 2)
        )
        rows.append(
            {
                "repository": expected["repository"],
                "branch": expected["branch"],
                "head_commit": head_commit,
                "head_committed_at": committed_at,
                "head_author_name": author_name,
                **observed,
                "result_or_log_inventory": ";".join(result_paths),
                "attribution": "unaffiliated",
                "relationship": expected["relationship"],
                "paper_result_credit": False,
                "head_subject": subject,
            }
        )
    return rows


def source_history_inventory(source_root: Path) -> List[Dict[str, Any]]:
    """Inventory the complete public history and any preserved result-like files."""
    if git(source_root, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise RuntimeError("CryptoTrade source history is shallow; fetch it before auditing")
    commits = git(source_root, "rev-list", "--reverse", "HEAD").splitlines()
    if len(commits) != SOURCE_COMMIT_COUNT:
        raise RuntimeError(f"Expected {SOURCE_COMMIT_COUNT} public commits, found {len(commits)}")
    if commits[0] != SOURCE_ROOT_COMMIT or commits[-1] != SOURCE_COMMIT:
        raise RuntimeError("CryptoTrade public-history endpoints changed")

    rows: List[Dict[str, Any]] = []
    for commit in commits:
        authored_at, subject = git(source_root, "show", "-s", "--format=%aI%x09%s", commit).rstrip("\n").split("\t", 1)
        paths = git(source_root, "ls-tree", "-r", "--name-only", commit).splitlines()
        result_paths = [
            path
            for path in paths
            if path.lower().endswith((".out", ".log"))
            or any(
                part in {"log", "logs", "output", "outputs", "result", "results"} for part in path.lower().split("/")
            )
        ]
        rows.append(
            {
                "commit": commit,
                "authored_at": authored_at,
                "subject": subject,
                "tracked_paths": len(paths),
                "result_or_log_paths": len(result_paths),
                "result_or_log_inventory": ";".join(result_paths),
                "run_baseline_present": "run_baseline.py" in paths,
            }
        )
    if any(row["result_or_log_paths"] for row in rows):
        raise RuntimeError("CryptoTrade public history unexpectedly contains result/log paths")
    return rows


def parse_logged_namespace(line: str) -> Dict[str, Any]:
    """Parse a logged argparse Namespace without executing any source text."""
    expression = ast.parse(line.strip(), mode="eval").body
    if not isinstance(expression, ast.Call) or not isinstance(expression.func, ast.Name):
        raise ValueError("Log does not start with a Namespace call")
    if expression.func.id != "Namespace" or expression.args:
        raise ValueError("Unexpected logged configuration expression")
    values: Dict[str, Any] = {}
    for keyword in expression.keywords:
        if keyword.arg is None:
            raise ValueError("Expanded kwargs are not allowed in a logged Namespace")
        values[keyword.arg] = ast.literal_eval(keyword.value)
    return values


def parse_author_trace(text: str) -> Tuple[Dict[str, Any], List[float], List[Dict[str, Any]]]:
    lines = text.splitlines()
    if not lines:
        raise ValueError("Empty author trace")
    args = parse_logged_namespace(lines[0])
    actions = [
        float(value)
        for value in re.findall(
            r"\*\*\* START ACTUAL ACTION \*\*\*\s*\n([-+]?\d+(?:\.\d+)?)",
            text,
        )
    ]
    state_literals = re.findall(
        r"\*\*\* START (?:INIT )?STATE \*\*\*\s*\n(\{.*?\})\s*\n"
        r"\*\*\* END (?:INIT )?STATE \*\*\*",
        text,
        flags=re.S,
    )
    states = [ast.literal_eval(value) for value in state_literals]
    if not states or len(actions) != len(states) - 1:
        raise ValueError("Author trace does not have one action between every state")
    return args, actions, states


def trace_metrics(states: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    returns = np.asarray([float(state["today_roi"]) for state in states[1:]], dtype=float) * 100
    mean = float(np.mean(returns))
    std = float(np.std(returns))
    return {
        "total_return_pct": float(states[-1]["roi"]) * 100,
        "daily_return_mean_pct": mean,
        "daily_return_std_pct": std,
        "sharpe_ratio": mean / std,
    }


def replay_author_actions(
    environment_module: Any,
    source_root: Path,
    args: Mapping[str, Any],
    actions: Sequence[float],
    recorded_states: Sequence[Mapping[str, Any]],
) -> Tuple[bool, float, bool]:
    """Replay a trace through the pinned official environment and compare every state."""
    old_cwd = Path.cwd()
    os.chdir(source_root)
    maximum_error = 0.0
    try:
        environment = environment_module.ETHTradingEnv(
            Namespace(
                dataset=args["dataset"],
                starting_date=args["starting_date"],
                ending_date=args["ending_date"],
            )
        )
        initial, _, _, _ = environment.reset()
        for key in ("cash", "eth_held", "open", "net_worth", "roi", "today_roi"):
            maximum_error = max(maximum_error, abs(float(initial[key]) - float(recorded_states[0][key])))
        for index, action in enumerate(actions, start=1):
            state, _, _, _ = environment.step(action)
            for key in ("cash", "eth_held", "open", "net_worth", "roi", "today_roi"):
                maximum_error = max(
                    maximum_error,
                    abs(float(state[key]) - float(recorded_states[index][key])),
                )
        full_period = bool(environment.done)
    finally:
        os.chdir(old_cwd)
    return maximum_error == 0.0, maximum_error, full_period


def author_trace_audit(
    environment_module: Any,
    source_root: Path,
) -> Tuple[
    List[Dict[str, Any]],
    Dict[Tuple[str, str, str], Dict[str, Any]],
    List[Dict[str, Any]],
]:
    """Recover paper-era outputs from the public branch of paper coauthor Nuo Chen."""
    if git(source_root, "rev-parse", AUTHOR_HISTORY_REF).strip() != AUTHOR_HISTORY_COMMIT:
        raise RuntimeError("Pinned CryptoTrade author-history ref is absent or changed")
    commits = git(source_root, "rev-list", "--reverse", AUTHOR_HISTORY_REF).splitlines()
    if (
        len(commits) != AUTHOR_HISTORY_COMMIT_COUNT
        or commits[0] != AUTHOR_HISTORY_ROOT_COMMIT
        or commits[-1] != AUTHOR_HISTORY_COMMIT
    ):
        raise RuntimeError("CryptoTrade author-history endpoints changed")

    pre_paths = git(source_root, "ls-tree", "-r", "--name-only", AUTHOR_PRE_REROOT_SNAPSHOT).splitlines()
    official_paths = git(source_root, "ls-tree", "-r", "--name-only", SOURCE_ROOT_COMMIT).splitlines()
    shared = sorted(set(pre_paths) & set(official_paths))
    shared_identical = sum(
        git(source_root, "rev-parse", f"{AUTHOR_PRE_REROOT_SNAPSHOT}:{path}").strip()
        == git(source_root, "rev-parse", f"{SOURCE_ROOT_COMMIT}:{path}").strip()
        for path in shared
    )
    if (len(pre_paths), len(official_paths), len(shared), shared_identical) != (406, 409, 406, 400):
        raise RuntimeError("Author-history to official-root continuity evidence changed")

    targets = paper_result_rows()
    paper: Dict[Tuple[str, str, str], Dict[str, float]] = {}
    time_series_paper: Dict[Tuple[str, str, str], Dict[str, float]] = {}
    for target in targets:
        if target["strategy"] in LLM_STRATEGIES:
            paper.setdefault((target["asset"], target["strategy"], target["regime"]), {})[target["metric"]] = float(
                target["paper_value"]
            )
        if target["strategy"] in TIME_SERIES_STRATEGIES:
            time_series_paper.setdefault((target["asset"], target["strategy"], target["regime"]), {})[
                target["metric"]
            ] = float(target["paper_value"])

    rows: List[Dict[str, Any]] = []
    credited: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    output_artifacts: List[Dict[str, Any]] = []
    seen_blobs = set()
    for commit in commits:
        for item in git(source_root, "ls-tree", "-rl", commit).splitlines():
            metadata, path = item.split("\t", 1)
            if not path.endswith((".out", ".log")):
                continue
            blob = metadata.split()[2]
            if blob in seen_blobs:
                continue
            seen_blobs.add(blob)
            text = git(source_root, "cat-file", "blob", blob)
            model_tokens = sorted(
                set(
                    value.lower()
                    for value in re.findall(
                        r"(?i)\b(?:lstm|informer|autoformer|timesnet|patchtst)\b",
                        text,
                    )
                )
            )
            summaries = [
                (float(total_return), float(sharpe))
                for total_return, sharpe in re.findall(
                    r"(?:FINAL return|Total return):\s*(-?\d+(?:\.\d+)?),\s*"
                    r"sharpe ratio:\s*(-?\d+(?:\.\d+)?)",
                    text,
                    flags=re.I,
                )
            ]
            matching_time_series_rows = sorted(
                {
                    key
                    for total_return, sharpe in summaries
                    for key, expected in time_series_paper.items()
                    if abs(total_return - expected["total_return_pct"]) <= DISPLAY_TOLERANCE
                    and abs(sharpe - expected["sharpe_ratio"]) <= DISPLAY_TOLERANCE
                }
            )
            output_artifacts.append(
                {
                    "author_commit_first_seen": commit,
                    "author_blob": blob,
                    "author_path_first_seen": path,
                    "blob_bytes": int(metadata.split()[3]),
                    "exact_time_series_model_tokens": ";".join(model_tokens),
                    "final_return_sharpe_summaries": len(summaries),
                    "paper_time_series_return_sharpe_pair_matches": len(matching_time_series_rows),
                    "matching_paper_rows": ";".join("|".join(key) for key in matching_time_series_rows),
                    "status": (
                        "candidate_time_series_evidence_requires_review"
                        if model_tokens or matching_time_series_rows
                        else "no_time_series_model_identity_or_paper_return_sharpe_pair"
                    ),
                }
            )
            if not text.startswith("Namespace("):
                continue
            try:
                args, actions, states = parse_author_trace(text)
            except (SyntaxError, ValueError):
                continue
            if not {"dataset", "model", "starting_date", "ending_date"} <= args.keys():
                continue
            regime = next(
                (
                    name
                    for name, values in PAPER_SPLITS.get(str(args["dataset"]), {}).items()
                    if name != "validation" and values[0] == args["starting_date"] and values[1] == args["ending_date"]
                ),
                None,
            )
            if regime is None:
                continue
            metrics = trace_metrics(states)
            matching_keys = [
                key
                for key, expected in paper.items()
                if key[0] == args["dataset"]
                and key[2] == regime
                and all(abs(metrics[metric] - expected[metric]) <= DISPLAY_TOLERANCE for metric in METRICS)
            ]
            if not matching_keys:
                continue
            if len(matching_keys) != 1:
                raise RuntimeError("Author trace ambiguously matches multiple paper rows")
            key = matching_keys[0]
            replay_exact, maximum_error, full_period = replay_author_actions(
                environment_module, source_root, args, actions, states
            )
            declared_model = str(args["model"])
            expected_model = {
                "gpt_3_5_turbo": "gpt-3.5-turbo",
                "gpt_4": "gpt-4-turbo",
                "gpt_4o": "gpt-4o",
            }[key[1]]
            model_matches = declared_model == expected_model
            declared_strategy = {
                "gpt-3.5-turbo": "gpt_3_5_turbo",
                "gpt-4-turbo": "gpt_4",
                "gpt-4o": "gpt_4o",
            }[declared_model]
            declared_key = (key[0], declared_strategy, key[2])
            declared_expected = paper[declared_key]
            declared_matches = sum(
                abs(metrics[metric] - declared_expected[metric]) <= DISPLAY_TOLERANCE
                for metric in METRICS
            )
            row = {
                "asset": key[0],
                "paper_strategy": key[1],
                "regime": key[2],
                "trace_declared_model": declared_model,
                "expected_runner_model": expected_model,
                "model_identity_status": "match" if model_matches else "mismatch",
                "period_start": args["starting_date"],
                "period_end_exclusive": args["ending_date"],
                "recorded_actions": len(actions),
                "full_period_trace": full_period,
                "last_recorded_date": states[-1]["date"],
                "paper_metric_cells_matching": len(METRICS),
                "trace_declared_model_paper_strategy": declared_strategy,
                "trace_declared_model_metric_cells_matching": declared_matches,
                "trace_declared_model_complete_paper_row_match": declared_matches == len(METRICS),
                "trace_declared_model_reassignment_required": not model_matches,
                "action_replay_exact": replay_exact,
                "action_replay_maximum_absolute_state_error": maximum_error,
                "author_commit": commit,
                "author_blob": blob,
                "author_path": path,
                "credit_status": (
                    "credited_author_trace_exact_metric_and_state_replay"
                    if model_matches and full_period and replay_exact
                    else "diagnostic_only_model_or_period_conflict"
                ),
            }
            if key not in credited or row["credit_status"].startswith("credited"):
                credited[key] = {**row, "metrics": metrics}
            rows.append(row)

    expected_matches = {
        ("btc", "gpt_4o", "bull"),
        ("btc", "gpt_4o", "sideways"),
        ("btc", "gpt_4o", "bear"),
        ("eth", "gpt_4o", "bull"),
        ("eth", "gpt_4o", "bear"),
        ("sol", "gpt_4o", "bull"),
        ("sol", "gpt_4o", "sideways"),
        ("btc", "gpt_4", "bull"),
        ("btc", "gpt_4", "sideways"),
        ("btc", "gpt_4", "bear"),
        ("eth", "gpt_4", "bull"),
        ("eth", "gpt_4", "sideways"),
        ("eth", "gpt_4", "bear"),
        ("sol", "gpt_4", "bull"),
        ("sol", "gpt_4", "sideways"),
        ("sol", "gpt_4", "bear"),
    }
    if set(credited) != expected_matches:
        raise RuntimeError("Recovered CryptoTrade paper-row trace inventory changed")
    if (
        len(output_artifacts),
        sum(row["blob_bytes"] for row in output_artifacts),
        sum(row["final_return_sharpe_summaries"] for row in output_artifacts),
    ) != (83, 209739069, 1371):
        raise RuntimeError("Recovered CryptoTrade author output-blob census changed")
    if any(
        row["exact_time_series_model_tokens"] or row["paper_time_series_return_sharpe_pair_matches"]
        for row in output_artifacts
    ):
        raise RuntimeError("Recovered CryptoTrade history has new candidate time-series evidence")
    reassignment_rows = [row for row in rows if row["trace_declared_model_reassignment_required"]]
    if (
        len(reassignment_rows),
        sum(int(row["trace_declared_model_metric_cells_matching"]) for row in reassignment_rows),
        sum(bool(row["trace_declared_model_complete_paper_row_match"]) for row in reassignment_rows),
    ) != (5, 1, 0):
        raise RuntimeError("CryptoTrade declared-model reassignment boundary changed")
    return rows, credited, output_artifacts


def _final_return_and_sharpe(text: str) -> Tuple[float, float]:
    matches = re.findall(
        r"(?:FINAL return|Total return):\s*(-?\d+(?:\.\d+)?),\s*"
        r"sharpe ratio:\s*(-?\d+(?:\.\d+)?)",
        text,
        flags=re.I,
    )
    if not matches:
        raise ValueError("Trace has no final return/Sharpe summary")
    return tuple(float(value) for value in matches[-1])  # type: ignore[return-value]


def _historical_environment_replay(
    source_root: Path,
    commit: str,
    args: Mapping[str, Any],
    actions: Sequence[float],
    states: Sequence[Mapping[str, Any]],
) -> Tuple[bool, float, bool]:
    """Replay a trace against the code/data tree that actually produced it."""
    archive = subprocess.run(
        ["git", "-C", str(source_root), "archive", commit, "eth_env.py", "data"],
        check=True,
        capture_output=True,
    ).stdout
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
            members = handle.getmembers()
            if any(Path(member.name).is_absolute() or ".." in Path(member.name).parts for member in members):
                raise RuntimeError("Unsafe path in pinned historical CryptoTrade archive")
            handle.extractall(root, filter="data")
        environment_module = load_environment(root)
        return replay_author_actions(environment_module, root, args, actions, states)


def _ablation_trace_record(
    source_root: Path,
    variant: str,
    pin: Mapping[str, str],
    trace_role: str,
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    observed_blob = git(source_root, "rev-parse", f"{pin['commit']}:{pin['path']}").strip()
    if observed_blob != pin["blob"]:
        raise RuntimeError(f"Pinned CryptoTrade ablation trace changed: {variant}")
    text = git(source_root, "cat-file", "blob", pin["blob"])
    args, actions, states = parse_author_trace(text)
    args.setdefault("dataset", "eth")
    final_return, final_sharpe = _final_return_and_sharpe(text)
    state_values = trace_metrics(states)
    if (
        abs(final_return - state_values["total_return_pct"]) > DISPLAY_TOLERANCE
        or abs(final_sharpe - state_values["sharpe_ratio"]) > DISPLAY_TOLERANCE
    ):
        raise RuntimeError(f"CryptoTrade ablation trace summary/state conflict: {variant}")
    replay_commit = pin.get("replay_commit", pin["commit"])
    replay_exact, maximum_error, full_period = _historical_environment_replay(
        source_root, replay_commit, args, actions, states
    )
    if not replay_exact or maximum_error != 0.0 or not full_period:
        raise RuntimeError(f"Historical CryptoTrade ablation replay changed: {variant}")

    expected_return, expected_sharpe = PAPER_ABLATION[variant]
    numeric_match = (
        abs(final_return - expected_return) <= DISPLAY_TOLERANCE
        and abs(final_sharpe - expected_sharpe) <= DISPLAY_TOLERANCE
    )
    dataset = str(args["dataset"])
    model = str(args["model"])
    model_matches = model == "gpt-4o"
    dataset_matches = dataset == "eth"
    configuration = tuple(int(args.get(name, 1)) for name in ("use_reflection", "use_news", "use_txnstat", "use_tech"))
    if ABLATION_FLAG_VARIANTS.get(configuration) != variant:
        raise RuntimeError(f"CryptoTrade ablation flag lineage changed: {variant}")
    if trace_role == "selected_numeric_correspondence" and not numeric_match:
        raise RuntimeError(f"Pinned CryptoTrade ablation numeric correspondence changed: {variant}")
    status = (
        "numeric_match_but_btc_main_table_trace_and_model_conflict"
        if variant == "full" and numeric_match
        else "numeric_match_and_historical_state_replay_but_model_conflict"
        if numeric_match
        else "eth_full_prompt_context_trace_conflicts_with_table_value_and_model"
    )
    row = {
        "trace_role": trace_role,
        "paper_variant": variant,
        "paper_expected_model": "gpt-4o",
        "trace_declared_model": model,
        "model_identity_status": "match" if model_matches else "mismatch",
        "paper_expected_asset": "eth",
        "trace_dataset": dataset,
        "asset_identity_status": "match" if dataset_matches else "mismatch",
        "period_start": args["starting_date"],
        "period_end_exclusive": args["ending_date"],
        "paper_period_status": "not_disclosed",
        "paper_return_pct": expected_return,
        "trace_return_pct": final_return,
        "paper_sharpe_ratio": expected_sharpe,
        "trace_sharpe_ratio": final_sharpe,
        "paper_metric_cells_matching": 2 if numeric_match else 0,
        "recorded_actions": len(actions),
        "full_period_trace": full_period,
        "historical_code_action_replay_exact": replay_exact,
        "action_replay_maximum_absolute_state_error": maximum_error,
        "author_commit": pin["commit"],
        "historical_replay_source_commit": replay_commit,
        "author_blob": pin["blob"],
        "author_path": pin["path"],
        "status": status,
        "paper_method_faithful_credit": False,
    }
    return row, {"return_pct": final_return, "sharpe_ratio": final_sharpe}


def ablation_trace_audit(source_root: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Audit all Table 5 cells without crediting model/asset-conflicted traces."""
    commits = git(source_root, "rev-list", "--reverse", AUTHOR_HISTORY_REF).splitlines()
    seen_blobs = set()
    exact_counts: Dict[str, int] = {variant: 0 for variant in PAPER_ABLATION}
    for commit in commits:
        for item in git(source_root, "ls-tree", "-rl", commit).splitlines():
            metadata, path = item.split("\t", 1)
            blob = metadata.split()[2]
            if blob in seen_blobs or not path.endswith((".out", ".log")):
                continue
            seen_blobs.add(blob)
            text = git(source_root, "cat-file", "blob", blob)
            if not text.startswith("Namespace("):
                continue
            try:
                args = parse_logged_namespace(text.splitlines()[0])
                observed = _final_return_and_sharpe(text)
            except (SyntaxError, ValueError):
                continue
            configuration = tuple(
                int(args.get(name, 1)) for name in ("use_reflection", "use_news", "use_txnstat", "use_tech")
            )
            variant = ABLATION_FLAG_VARIANTS.get(configuration)
            if variant and all(
                abs(actual - expected) <= DISPLAY_TOLERANCE
                for actual, expected in zip(observed, PAPER_ABLATION[variant])
            ):
                exact_counts[variant] += 1
    expected_exact_counts = {
        "full": 1,
        "without_reflection": 1,
        "without_news": 1,
        "without_transaction_statistics": 2,
        "without_technical": 2,
        "base": 2,
    }
    if exact_counts != expected_exact_counts:
        raise RuntimeError(f"CryptoTrade ablation trace census changed: {exact_counts}")

    trace_rows = []
    selected_values: Dict[str, Dict[str, float]] = {}
    for variant, pin in ABLATION_TRACE_PINS.items():
        row, values = _ablation_trace_record(source_root, variant, pin, "selected_numeric_correspondence")
        trace_rows.append(row)
        selected_values[variant] = values
    context_row, _ = _ablation_trace_record(
        source_root,
        "full",
        ABLATION_FULL_CONTEXT_TRACE_PIN,
        "eth_full_prompt_context_candidate",
    )
    trace_rows.append(context_row)

    conformance = []
    for variant, expected_values in PAPER_ABLATION.items():
        trace = next(
            row
            for row in trace_rows
            if row["paper_variant"] == variant and row["trace_role"] == "selected_numeric_correspondence"
        )
        for metric, expected, observed in zip(
            ("return_pct", "sharpe_ratio"),
            expected_values,
            (selected_values[variant]["return_pct"], selected_values[variant]["sharpe_ratio"]),
        ):
            conformance.append(
                {
                    "paper_variant": variant,
                    "metric": metric,
                    "paper_value": expected,
                    "author_trace_value": observed,
                    "absolute_error": abs(observed - expected),
                    "display_tolerance": DISPLAY_TOLERANCE,
                    "author_numeric_correspondence": True,
                    "historical_code_action_replay_exact": trace["historical_code_action_replay_exact"],
                    "model_identity_status": trace["model_identity_status"],
                    "asset_identity_status": trace["asset_identity_status"],
                    "author_commit": trace["author_commit"],
                    "author_blob": trace["author_blob"],
                    "author_path": trace["author_path"],
                    "status": trace["status"],
                    "paper_method_faithful_credit": False,
                }
            )
    if len(conformance) != 12 or sum(row["author_numeric_correspondence"] for row in conformance) != 12:
        raise RuntimeError("CryptoTrade Table 5 cell census changed")
    return trace_rows, conformance


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def lstm_environment_snapshot(wrapper: Path) -> Dict[str, Any]:
    program = (
        "import json,sys,numpy,pandas,sklearn,torch;"
        "print(json.dumps({'python':sys.version.split()[0],'torch':torch.__version__,"
        "'numpy':numpy.__version__,'pandas':pandas.__version__,"
        "'scikit_learn':sklearn.__version__,"
        "'torch_cuda_available':torch.cuda.is_available()},sort_keys=True))"
    )
    environment = dict(os.environ)
    for key in (
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONUSERBASE",
        "VIRTUAL_ENV",
        "_OLD_VIRTUAL_PATH",
        "__PYVENV_LAUNCHER__",
    ):
        environment.pop(key, None)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    result = subprocess.run(
        [str(wrapper), "-c", program],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    snapshot = json.loads(result.stdout)
    if snapshot != LSTM_COMPATIBLE_ENVIRONMENT:
        raise RuntimeError(f"CryptoTrade LSTM environment changed: {snapshot}")
    return snapshot


def load_lstm_evidence(results_root: Path, wrapper: Path) -> Dict[str, Any]:
    for filename, expected in LSTM_RESULT_SHA256.items():
        observed = sha256(results_root / filename)
        if observed != expected:
            raise RuntimeError(f"CryptoTrade LSTM evidence changed: {filename}={observed}")

    fixed_cells = read_csv(results_root / "cryptotrade_lstm_cell_census.csv")
    fixed_summary = read_csv(results_root / "cryptotrade_lstm_cell_summary.csv")
    fixed_payload = json.loads(
        (results_root / "cryptotrade_lstm_probe.json").read_text(encoding="utf-8")
    )
    validation = read_csv(results_root / "cryptotrade_lstm_validation_grid.csv")
    validation_payload = json.loads(
        (results_root / "cryptotrade_lstm_validation_selection.json").read_text(
            encoding="utf-8"
        )
    )
    paper_grid = read_csv(results_root / "cryptotrade_lstm_paper_grid.csv")
    paper_grid_payload = json.loads(
        (results_root / "cryptotrade_lstm_paper_grid.json").read_text(encoding="utf-8")
    )
    seed0_repeat = read_csv(
        results_root / "cryptotrade_lstm_paper_grid_seed0_repeat.csv"
    )
    seed0_repeat_payload = json.loads(
        (results_root / "cryptotrade_lstm_paper_grid_seed0_repeat.json").read_text(
            encoding="utf-8"
        )
    )
    if len(fixed_cells) != 240 or len(fixed_summary) != 12:
        raise RuntimeError("CryptoTrade fixed-lookback LSTM census changed")
    if fixed_payload["native_runs"] != 20 or fixed_payload["regime_runs"] != 60:
        raise RuntimeError("CryptoTrade fixed-lookback run count changed")
    fixed_groups: Dict[Tuple[str, str, str], List[Tuple[str, str]]] = {}
    for row in fixed_cells:
        key = (row["seed"], row["regime"], row["metric"])
        fixed_groups.setdefault(key, []).append(
            (row["recomputed_value"], row["action_sha256"])
        )
    if len(fixed_groups) != 120 or any(len(set(values)) != 1 for values in fixed_groups.values()):
        raise RuntimeError("CryptoTrade fixed-lookback repeats are not exact")

    if len(validation) != 120 or validation_payload["grid_runs"] != 120:
        raise RuntimeError("CryptoTrade LSTM validation grid changed")
    if validation_payload["repeat_exact_groups"] != 60:
        raise RuntimeError("CryptoTrade LSTM validation repeats changed")
    expected_lookbacks = [1, 3, 5, 10, 20, 30]
    if any(
        row["return_selected"] != expected_lookbacks
        or row["sharpe_selected"] != expected_lookbacks
        for row in validation_payload["selections"]
    ):
        raise RuntimeError("CryptoTrade LSTM validation lookbacks no longer tie")

    if len(paper_grid) != 720 or paper_grid_payload["native_seed_lookback_runs"] != 60:
        raise RuntimeError("CryptoTrade LSTM paper grid changed")
    seed0 = [row for row in paper_grid if row["seed"] == "0"]
    if seed0 != seed0_repeat or seed0_repeat_payload["native_seed_lookback_runs"] != 6:
        raise RuntimeError("CryptoTrade LSTM seed-0 paper-grid repeat changed")

    fixed_map = {
        (row["regime"], row["metric"]): row for row in fixed_summary
    }
    grid_map = {
        (row["regime"], row["metric"]): row
        for row in paper_grid_payload["summary"]
    }
    expected_cells = {
        (regime, metric) for regime in REGIMES for metric in METRICS
    }
    if set(fixed_map) != expected_cells or set(grid_map) != expected_cells:
        raise RuntimeError("CryptoTrade LSTM result-cell surface changed")
    source_default_matches = {
        key
        for key, row in fixed_map.items()
        if row["all_seeds_and_repeats_match"] == "True"
    }
    protocol_robust_matches = {
        key for key, row in grid_map.items() if row["all_seeds_and_lookbacks_match"]
    }
    if source_default_matches != {
        (regime, metric) for regime in ("bear", "bull") for metric in METRICS
    }:
        raise RuntimeError("CryptoTrade source-default LSTM matches changed")
    if protocol_robust_matches != {("bear", metric) for metric in METRICS}:
        raise RuntimeError("CryptoTrade protocol-robust LSTM matches changed")
    sideways_std = grid_map[("sideways", "daily_return_std_pct")]
    if (
        sideways_std["matches"] != 0
        or abs(sideways_std["min_recomputed_value"] - 0.11361322968) > 1e-12
        or abs(sideways_std["max_recomputed_value"] - 1.892942965348) > 1e-12
    ):
        raise RuntimeError("CryptoTrade sideways LSTM volatility boundary changed")

    adjudication = []
    for regime in REGIMES:
        for metric in METRICS:
            key = (regime, metric)
            fixed = fixed_map[key]
            grid = grid_map[key]
            source_default = key in source_default_matches
            robust = key in protocol_robust_matches
            if robust:
                status = "native_lstm_seed_and_lookback_robust_match"
            elif source_default:
                status = "source_default_match_protocol_tie_sensitive_no_credit"
            else:
                status = "seed_or_lookback_sensitive_no_credit"
            adjudication.append(
                {
                    "asset": "eth",
                    "strategy": "lstm",
                    "regime": regime,
                    "metric": metric,
                    "paper_value": float(fixed["paper_value"]),
                    "fixed5_observations": int(fixed["observations"]),
                    "fixed5_matches": int(fixed["matches"]),
                    "fixed5_unique_values": int(fixed["unique_recomputed_values"]),
                    "fixed5_min": float(fixed["min_recomputed_value"]),
                    "fixed5_max": float(fixed["max_recomputed_value"]),
                    "fixed5_unique_action_paths": int(fixed["unique_action_paths"]),
                    "seed_lookback_observations": int(grid["observations"]),
                    "seed_lookback_matches": int(grid["matches"]),
                    "seed_lookback_unique_values": int(grid["unique_recomputed_values"]),
                    "seed_lookback_min": float(grid["min_recomputed_value"]),
                    "seed_lookback_max": float(grid["max_recomputed_value"]),
                    "seed_lookback_unique_action_paths": int(grid["unique_action_paths"]),
                    "source_default_correspondence": source_default,
                    "protocol_robust_paper_result_credit": robust,
                    "exact_declared_runtime_reproduced": False,
                    "status": status,
                }
            )
    environment = lstm_environment_snapshot(wrapper)
    payload = {
        "source_commit": SOURCE_COMMIT,
        "source_run_baseline_sha256": sha256(results_root.parent / "cryptotrade_source/run_baseline.py")
        if (results_root.parent / "cryptotrade_source/run_baseline.py").exists()
        else "",
        "compatible_environment": environment,
        "paper_declared_torch": "2.3.0",
        "exact_declared_runtime_reproduced": False,
        "fixed_source_default": {
            "seeds": list(range(10)),
            "repeats_per_seed": 2,
            "lookback": 5,
            "native_runs": 20,
            "regime_runs": 60,
            "cell_observations": 240,
            "repeat_exact_groups": 120,
            "stable_matching_cells": len(source_default_matches),
        },
        "paper_validation_grid": {
            "lookbacks": expected_lookbacks,
            "seeds": list(range(10)),
            "repeats_per_seed": 2,
            "native_runs": 120,
            "repeat_exact_groups": 60,
            "all_lookbacks_tie_for_every_seed": True,
            "selection_metric_specified_by_paper": False,
        },
        "paper_seed_lookback_grid": {
            "seeds": list(range(10)),
            "lookbacks": expected_lookbacks,
            "native_runs": 60,
            "regime_runs": 180,
            "cell_observations": 720,
            "seed0_repeat_cell_rows_exact": 72,
            "protocol_robust_matching_cells": len(protocol_robust_matches),
            "source_default_only_matching_cells": len(
                source_default_matches - protocol_robust_matches
            ),
        },
        "source_compatibility": {
            "removed_unused_matplotlib_import": True,
            "cuda7_to_cpu": True,
            "added_required_dataset_eth": True,
            "return_only_instrumentation": True,
            "pinned_source_modified": False,
        },
        "network_attempts": 0,
        "llm_calls": 0,
        "paper_result_credit": (
            "four_eth_bear_cells_source_native_seed_and_lookback_robust_under_"
            "compatible_runtime"
        ),
    }
    return {
        "fixed_cells": fixed_cells,
        "validation": validation,
        "paper_grid": paper_grid,
        "adjudication": adjudication,
        "payload": payload,
        "adjudication_map": {
            (row["regime"], row["metric"]): row for row in adjudication
        },
    }


def paper_result_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in PAPER_ROWS_TEXT.strip().splitlines():
        values = line.split("|")
        if len(values) != 14:
            raise ValueError(f"Malformed paper result row: {line}")
        asset, strategy = values[:2]
        numbers = [float(value) for value in values[2:]]
        totals, means, stds, sharpes = (
            numbers[0:3],
            numbers[3:6],
            numbers[6:9],
            numbers[9:12],
        )
        for index, regime in enumerate(REGIMES):
            metrics = (totals[index], means[index], stds[index], sharpes[index])
            for metric, paper_value in zip(METRICS, metrics):
                rows.append(
                    {
                        "asset": asset,
                        "strategy": strategy,
                        "regime": regime,
                        "metric": metric,
                        "paper_value": paper_value,
                    }
                )
    return rows


def load_environment(source_root: Path) -> Any:
    module_path = source_root / "eth_env.py"
    spec = importlib.util.spec_from_file_location("cryptotrade_pinned_eth_env", module_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def source_simulation(
    environment_module: Any,
    source_root: Path,
    asset: str,
    start: str,
    end: str,
    strategy: str,
    parameter: Any = None,
) -> Dict[str, float]:
    old_cwd = Path.cwd()
    os.chdir(source_root)
    try:
        environment = environment_module.ETHTradingEnv(Namespace(dataset=asset, starting_date=start, ending_date=end))
        state, _, _, _ = environment.reset()
        start_net_worth = float(state["net_worth"])
        previous_net_worth = start_net_worth
        daily_returns: List[float] = []
        for _, row in environment.data.reset_index(drop=True).iterrows():
            net_worth = float(state["net_worth"])
            daily_returns.append(net_worth / previous_net_worth - 1)
            previous_net_worth = net_worth
            if environment.done:
                break

            cash = float(state["cash"])
            held = float(state["eth_held"])
            action = 0.0
            if strategy == "buy_and_hold":
                action = 1.0 if cash > 0 else 0.0
            elif strategy == "sma":
                period = int(parameter)
                buy = float(state["open"]) > float(row[f"SMA_{period}"])
                action = 0.5 if buy and cash > 0 else -0.5 if not buy and held > 0 else 0.0
            elif strategy == "slma":
                short, long = parameter
                buy = float(row[f"SMA_{short}"]) > float(row[f"SMA_{long}"])
                action = 0.5 if buy else -0.5 if held > 0 else 0.0
            elif strategy == "macd":
                # This intentionally preserves the released runner's signal direction.
                buy = float(row["MACD"]) < float(row["Signal_Line"])
                action = 0.5 if buy and cash > 0 else -0.5 if not buy and held > 0 else 0.0
            elif strategy == "bollinger_bands":
                lower = float(row["SMA_20"]) - 2 * float(row["STD_20"])
                upper = float(row["SMA_20"]) + 2 * float(row["STD_20"])
                price = float(state["open"])
                action = 0.5 if price < lower and cash > 0 else -0.5 if price > upper and held > 0 else 0.0
            else:
                raise ValueError(f"Unsupported deterministic source strategy: {strategy}")
            state, _, _, _ = environment.step(action)
    finally:
        os.chdir(old_cwd)

    daily = np.asarray(daily_returns, dtype=float) * 100
    mean = float(np.mean(daily))
    std = float(np.std(daily))
    return {
        "total_return_pct": (float(state["net_worth"]) / start_net_worth - 1) * 100,
        "daily_return_mean_pct": mean,
        "daily_return_std_pct": std,
        "sharpe_ratio": mean / std,
        "start_open": float(environment.starting_price),
        "end_open": float(state["open"]),
        "observations": int(environment.total_steps),
    }


def fixed_parameter(strategy: str) -> Any:
    if strategy == "sma":
        return 15
    if strategy == "slma":
        return (15, 30)
    return None


def result_conformance(
    environment_module: Any,
    source_root: Path,
    author_traces: Mapping[Tuple[str, str, str], Mapping[str, Any]],
    lstm_evidence: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[Tuple[str, str, str], Dict[str, float]]]:
    reproduced: Dict[Tuple[str, str, str], Dict[str, float]] = {}
    for asset in PAPER_SPLITS:
        for regime in REGIMES:
            start, end, *_ = PAPER_SPLITS[asset][regime]
            for strategy in sorted(TRADITIONAL_STRATEGIES):
                reproduced[(asset, strategy, regime)] = source_simulation(
                    environment_module,
                    source_root,
                    asset,
                    start,
                    end,
                    strategy,
                    fixed_parameter(strategy),
                )

    rows = []
    for target in paper_result_rows():
        strategy = target["strategy"]
        key = (target["asset"], strategy, target["regime"])
        source_value: Any = ""
        absolute_error: Any = ""
        if strategy in TRADITIONAL_STRATEGIES:
            source_value = reproduced[key][target["metric"]]
            absolute_error = abs(source_value - target["paper_value"])
            status = "exact_displayed_precision_match" if absolute_error <= DISPLAY_TOLERANCE else "mismatch"
            evidence = "pinned_native_environment_with_released_traditional_strategy_logic"
        elif strategy in TIME_SERIES_STRATEGIES:
            if target["asset"] == "eth" and strategy == "lstm":
                item = lstm_evidence["adjudication_map"][(target["regime"], target["metric"])]
                if item["fixed5_unique_values"] == 1:
                    source_value = item["fixed5_min"]
                    absolute_error = abs(source_value - target["paper_value"])
                if item["protocol_robust_paper_result_credit"]:
                    status = "native_lstm_seed_and_lookback_robust_match"
                elif item["source_default_correspondence"]:
                    status = "unverifiable_native_lstm_source_default_match_protocol_tie_sensitive"
                else:
                    status = "unverifiable_native_lstm_seed_or_lookback_sensitive"
                evidence = (
                    f"fixed5={item['fixed5_matches']}/{item['fixed5_observations']};"
                    f"seed_lookback={item['seed_lookback_matches']}/"
                    f"{item['seed_lookback_observations']};"
                    f"range=[{item['seed_lookback_min']},{item['seed_lookback_max']}];"
                    "compatible_torch_2.4.1_cpu_not_declared_torch_2.3.0_cuda"
                )
            else:
                status = "unverifiable_no_shipped_full_period_output"
                evidence = (
                    "lstm_only_released_for_eth"
                    if strategy == "lstm"
                    else "implementation_not_released"
                )
        elif strategy in LLM_STRATEGIES:
            trace = author_traces.get(key)
            if trace is None:
                status = "unverifiable_no_recovered_author_trace"
                evidence = "no_matching_trace_in_official_or_paper_author_history"
            else:
                source_value = trace["metrics"][target["metric"]]
                absolute_error = abs(source_value - target["paper_value"])
                if trace["credit_status"].startswith("credited"):
                    status = "author_trace_exact_metric_and_native_state_replay"
                else:
                    status = "unverifiable_trace_model_or_period_conflict"
                evidence = (
                    f"author_commit={trace['author_commit']};blob={trace['author_blob']};"
                    f"path={trace['author_path']};model={trace['model_identity_status']};"
                    f"full_period={trace['full_period_trace']};state_replay={trace['action_replay_exact']}"
                )
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        rows.append(
            {
                **target,
                "source_recomputed_value": source_value,
                "absolute_error": absolute_error,
                "display_tolerance": DISPLAY_TOLERANCE,
                "status": status,
                "evidence": evidence,
            }
        )
    return rows, reproduced


def split_conformance(
    environment_module: Any,
    source_root: Path,
    reproduced: Mapping[Tuple[str, str, str], Mapping[str, float]],
) -> List[Dict[str, Any]]:
    rows = []
    for asset, splits in PAPER_SPLITS.items():
        for split, (start, end, paper_open, paper_close, paper_trend) in splits.items():
            if split == "validation":
                actual = source_simulation(
                    environment_module,
                    source_root,
                    asset,
                    start,
                    end,
                    "buy_and_hold",
                )
            else:
                actual = reproduced[(asset, "buy_and_hold", split)]
            rows.append(
                {
                    "asset": asset,
                    "split": split,
                    "start": start,
                    "end": end,
                    "paper_open": paper_open,
                    "source_open": actual["start_open"],
                    "open_status": (
                        "exact_displayed_precision_match"
                        if abs(paper_open - actual["start_open"]) <= DISPLAY_TOLERANCE
                        else "mismatch"
                    ),
                    "paper_close": paper_close,
                    "source_end_open": actual["end_open"],
                    "close_status": (
                        "exact_displayed_precision_match"
                        if abs(paper_close - actual["end_open"]) <= DISPLAY_TOLERANCE
                        else "mismatch"
                    ),
                    "paper_trend_pct": paper_trend,
                    "source_costed_buy_hold_return_pct": actual["total_return_pct"],
                    "trend_status": (
                        "exact_displayed_precision_match"
                        if abs(paper_trend - actual["total_return_pct"]) <= DISPLAY_TOLERANCE
                        else "mismatch"
                    ),
                    "source_observations_including_end_price": actual["observations"],
                }
            )
    return rows


def parameter_selection_audit(
    environment_module: Any,
    source_root: Path,
    conformance: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    rows = []
    for asset, splits in PAPER_SPLITS.items():
        validation_start, validation_end, *_ = splits["validation"]
        candidates: Mapping[str, Iterable[Any]] = {
            "sma": SMA_PERIODS,
            "slma": tuple(combinations(SMA_PERIODS, 2)),
        }
        for strategy, parameters in candidates.items():
            results = [
                (
                    parameter,
                    source_simulation(
                        environment_module,
                        source_root,
                        asset,
                        validation_start,
                        validation_end,
                        strategy,
                        parameter,
                    )["total_return_pct"],
                )
                for parameter in parameters
            ]
            best_parameter, best_return = max(results, key=lambda item: item[1])
            released_fixed = fixed_parameter(strategy)
            relevant = [
                row
                for row in conformance
                if row["asset"] == asset
                and row["strategy"] == strategy
                and row["status"] in {"exact_displayed_precision_match", "mismatch"}
            ]
            rows.append(
                {
                    "asset": asset,
                    "strategy": strategy,
                    "paper_rule": "select best validation performance",
                    "released_runner_fixed_parameter": str(released_fixed),
                    "released_data_validation_argmax": str(best_parameter),
                    "released_data_validation_argmax_return_pct": best_return,
                    "fixed_parameter_equals_validation_argmax": released_fixed == best_parameter,
                    "paper_test_metric_cells_matching_with_fixed_parameter": sum(
                        row["status"] == "exact_displayed_precision_match" for row in relevant
                    ),
                    "paper_test_metric_cells_total": len(relevant),
                    "status": (
                        "selection_rule_match" if released_fixed == best_parameter else "selection_rule_mismatch"
                    ),
                }
            )
    return rows


def mismatch_diagnosis(
    environment_module: Any,
    source_root: Path,
    conformance: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Trace all six residual deterministic cells without granting invalid credit."""
    paper_rows = paper_result_rows()
    paper = {(row["asset"], row["strategy"], row["regime"], row["metric"]): row["paper_value"] for row in paper_rows}
    diagnosed: List[Dict[str, Any]] = []
    released_periods = list(environment_module.SMA_PERIODS)
    environment_module.SMA_PERIODS = [1, *released_periods]
    try:
        for row in conformance:
            if row["status"] != "mismatch":
                continue
            asset = str(row["asset"])
            regime = str(row["regime"])
            metric = str(row["metric"])
            start, end, *_ = PAPER_SPLITS[asset][regime]
            outside_grid = source_simulation(environment_module, source_root, asset, start, end, "sma", 1)[metric]
            outside_match = abs(float(row["paper_value"]) - outside_grid) <= DISPLAY_TOLERANCE
            duplicated_from = ""
            classification = "unexplained_after_released_grid_and_history_search"
            numeric_lineage = "none"
            if asset == "eth" and regime == "sideways" and metric in {"daily_return_mean_pct", "daily_return_std_pct"}:
                bear_value = paper[("eth", "sma", "bear", metric)]
                if bear_value != float(row["paper_value"]):
                    raise RuntimeError("ETH-sideways copy-pattern diagnosis changed")
                duplicated_from = f"eth|sma|bear|{metric}"
                classification = "exact_duplicate_of_eth_bear_paper_cell"
                numeric_lineage = "paper_internal_copy_pattern"
            elif asset == "sol" and regime == "bear" and outside_match:
                classification = "exact_period_1_sma_match_outside_disclosed_and_released_grid"
                numeric_lineage = "released_data_counterfactual_not_method_faithful"
            diagnosed.append(
                {
                    "asset": asset,
                    "strategy": row["strategy"],
                    "regime": regime,
                    "metric": metric,
                    "paper_value": row["paper_value"],
                    "released_fixed_15_value": row["source_recomputed_value"],
                    "period_1_counterfactual_value": outside_grid,
                    "period_1_display_match": "yes" if outside_match else "no",
                    "duplicated_paper_cell": duplicated_from,
                    "classification": classification,
                    "numeric_lineage": numeric_lineage,
                    "method_faithful_replication_credit": "no",
                }
            )
    finally:
        environment_module.SMA_PERIODS = released_periods
    counts = {
        "paper_copy": sum(row["numeric_lineage"] == "paper_internal_copy_pattern" for row in diagnosed),
        "outside_grid": sum(
            row["numeric_lineage"] == "released_data_counterfactual_not_method_faithful" for row in diagnosed
        ),
    }
    if len(diagnosed) != 6 or counts != {"paper_copy": 2, "outside_grid": 4}:
        raise RuntimeError(f"CryptoTrade residual diagnosis changed: {counts}")
    return diagnosed


def _date_bounds(path: Path, column: str, date_format: str) -> Tuple[str, str, int]:
    frame = pd.read_csv(path)
    dates = pd.to_datetime(frame[column], format=date_format, errors="raise")
    return dates.min().date().isoformat(), dates.max().date().isoformat(), len(frame)


def data_inventory(source_root: Path) -> List[Dict[str, Any]]:
    specifications = (
        ("data/eth_daily.csv", "price", "snapped_at", "%Y-%m-%d %H:%M:%S UTC"),
        ("data/bitcoin_daily_price.csv", "price", "timeOpen", "%Y-%m-%dT%H:%M:%S.%fZ"),
        ("data/solana_daily_price.csv", "price", "timeOpen", "%Y-%m-%dT%H:%M:%S.%fZ"),
        (
            "data/eth_more_transaction_statistics.csv",
            "on_chain",
            "day",
            "%d/%m/%y %H:%M",
        ),
        (
            "data/bitcoin_transaction_statistics.csv",
            "on_chain",
            "day",
            "%Y-%m-%d %H:%M:%S.%f UTC",
        ),
        (
            "data/solana_transaction_statistics.csv",
            "on_chain",
            "day",
            "%Y-%m-%d %H:%M:%S.%f UTC",
        ),
    )
    rows = []
    for relative, role, column, date_format in specifications:
        path = source_root / relative
        start, end, count = _date_bounds(path, column, date_format)
        rows.append(
            {
                "path": relative,
                "role": role,
                "rows_or_files": count,
                "date_start": start,
                "date_end": end,
                "sha256": sha256(path),
            }
        )
    for relative in (
        "data/gnews",
        "data/selected_bitcoin_202301_202401",
        "data/selected_solana_202301_202401",
    ):
        paths = sorted((source_root / relative).glob("*.json"))
        rows.append(
            {
                "path": relative,
                "role": "off_chain_news",
                "rows_or_files": len(paths),
                "date_start": paths[0].stem,
                "date_end": paths[-1].stem,
                "sha256": "directory_inventory_not_single_file",
            }
        )
    return rows


def source_execution_gaps(source_root: Path) -> List[Dict[str, str]]:
    runner = (source_root / "run_agent.sh").read_text(encoding="utf-8")
    baseline = (source_root / "run_baseline.py").read_text(encoding="utf-8")
    prompts = (source_root / "env_history.py").read_text(encoding="utf-8")
    utils = (source_root / "utils.py").read_text(encoding="utf-8")
    executable = bool((source_root / "run_agent.sh").stat().st_mode & stat.S_IXUSR)
    logs_dir = (source_root / "logs").is_dir()
    active_commands = [
        line.strip() for line in runner.splitlines() if line.strip().startswith("python -u run_agent.py")
    ]
    period_mismatches = sum(
        any(literal in command for literal in ("eth --starting_date 2023-06-17", "sol --starting_date 2023-06-17"))
        for command in active_commands
    )
    gaps = (
        (
            "readme_run_command",
            "fails_before_agent_execution",
            f"run_agent.sh executable={executable}; required logs directory present={logs_dir}",
        ),
        (
            "active_gpt4o_periods",
            "two_of_nine_commands_mismatch_paper_splits",
            f"active_commands={len(active_commands)}; mismatched_eth_sol_sideways={period_mismatches}",
        ),
        (
            "baseline_entrypoint",
            "fails_without_source_edits_and_dependencies",
            "README omits required packages; run_baseline constructs Namespace without dataset",
        ),
        (
            "asset_specific_prompts",
            "mismatch_for_btc_and_sol",
            "released prompt templates hard-code ETH instead of interpolating the dataset",
        ),
        (
            "llm_result_evidence",
            "absent_from_official_release_but_partly_recovered_from_author_history",
            "official history has no result paths; a paper coauthor's public branch preserves partial paper-period traces",
        ),
        (
            "time_series_baselines",
            "partial_native_lstm_replay_other_models_missing",
            "ETH LSTM source-function replay gives four seed/lookback-robust bear cells and four source-default-only bull correspondences; Informer/AutoFormer/TimesNet/PatchTST implementations and outputs are absent",
        ),
        (
            "model_identity",
            "paper_to_runner_mismatch",
            "paper reports GPT-4 while released shell commands use gpt-4-turbo",
        ),
        (
            "transaction_cost_specification",
            "paper_underspecified",
            "paper states a proportional fee but not its rate; source fixes EX_RATE=0.004 plus a fixed gas charge",
        ),
        (
            "credential_hygiene",
            "environment_variable_used",
            "released utility reads OPENAI_API_KEY; the audit never imports or uses the API module",
        ),
    )
    if "Namespace(starting_date=sargs['starting_date'], ending_date=sargs['ending_date'])" not in baseline:
        raise RuntimeError("Pinned baseline runner no longer has the audited missing-dataset call")
    if "You are an ETH cryptocurrency" not in prompts:
        raise RuntimeError("Pinned prompt templates no longer have the audited asset literal")
    utility_tree = ast.parse(utils)
    api_key_assignments = [
        node
        for node in ast.walk(utility_tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "api_key" for target in node.targets)
    ]
    if len(api_key_assignments) != 1 or not isinstance(api_key_assignments[0].value, ast.Call):
        raise RuntimeError("Pinned API-key loading pattern changed; re-audit it explicitly")
    return [{"component": component, "status": status, "evidence": evidence} for component, status, evidence in gaps]


def build_audit(
    source_root: Path,
    paper_path: Path,
    lstm_results_root: Path,
    lstm_python_wrapper: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official paper PDF hash does not match the pinned primary source")

    environment_module = load_environment(source_root)
    history = source_history_inventory(source_root)
    fork_divergence = public_fork_divergence_inventory(source_root)
    author_trace_rows, author_traces, author_output_artifacts = author_trace_audit(environment_module, source_root)
    ablation_trace_rows, ablation_conformance = ablation_trace_audit(source_root)
    lstm = load_lstm_evidence(lstm_results_root, lstm_python_wrapper)
    conformance, reproduced = result_conformance(
        environment_module, source_root, author_traces, lstm
    )
    splits = split_conformance(environment_module, source_root, reproduced)
    selection = parameter_selection_audit(environment_module, source_root, conformance)
    selection.append(
        {
            "asset": "eth",
            "strategy": "lstm",
            "paper_rule": "select best validation performance from [1,3,5,10,20,30]",
            "released_runner_fixed_parameter": 5,
            "released_data_validation_argmax": "all [1,3,5,10,20,30] tie",
            "released_data_validation_argmax_return_pct": 2.369788794633,
            "fixed_parameter_equals_validation_argmax": True,
            "paper_test_metric_cells_matching_with_fixed_parameter": 8,
            "paper_test_metric_cells_total": 12,
            "status": "selection_rule_nonidentifying_tie",
        }
    )
    diagnosis = mismatch_diagnosis(environment_module, source_root, conformance)
    inventory = data_inventory(source_root)
    gaps = source_execution_gaps(source_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_2_4_conformance.csv", conformance, list(conformance[0]))
    write_csv(output_dir / "dataset_split_conformance.csv", splits, list(splits[0]))
    write_csv(output_dir / "parameter_selection_audit.csv", selection, list(selection[0]))
    write_csv(output_dir / "traditional_mismatch_diagnosis.csv", diagnosis, list(diagnosis[0]))
    write_csv(output_dir / "source_history_inventory.csv", history, list(history[0]))
    write_csv(
        output_dir / "public_fork_divergence_inventory.csv",
        fork_divergence,
        list(fork_divergence[0]),
    )
    write_csv(
        output_dir / "author_history_llm_trace_audit.csv",
        author_trace_rows,
        list(author_trace_rows[0]),
    )
    write_csv(
        output_dir / "author_history_output_artifact_census.csv",
        author_output_artifacts,
        list(author_output_artifacts[0]),
    )
    write_csv(
        output_dir / "table_5_author_trace_audit.csv",
        ablation_trace_rows,
        list(ablation_trace_rows[0]),
    )
    write_csv(
        output_dir / "table_5_conformance.csv",
        ablation_conformance,
        list(ablation_conformance[0]),
    )
    write_csv(output_dir / "data_inventory.csv", inventory, list(inventory[0]))
    write_csv(output_dir / "source_execution_gaps.csv", gaps, list(gaps[0]))
    fixed_lstm_rows = [{**row, "lookback": 5} for row in lstm["fixed_cells"]]
    write_csv(
        output_dir / "lstm_fixed5_cell_census.csv",
        fixed_lstm_rows,
        list(fixed_lstm_rows[0]),
    )
    write_csv(
        output_dir / "lstm_validation_grid.csv",
        lstm["validation"],
        list(lstm["validation"][0]),
    )
    write_csv(
        output_dir / "lstm_seed_lookback_grid.csv",
        lstm["paper_grid"],
        list(lstm["paper_grid"][0]),
    )
    write_csv(
        output_dir / "lstm_cell_adjudication.csv",
        lstm["adjudication"],
        list(lstm["adjudication"][0]),
    )
    (output_dir / "lstm_execution.json").write_text(
        json.dumps(lstm["payload"], indent=2) + "\n", encoding="utf-8"
    )
    paper_inconsistencies = (
        {
            "claim": "Table 5 ablation market/asset label",
            "paper_value_a": "ETH bullish (caption/prose)",
            "paper_value_b": "Full=28.47% return, 0.23 Sharpe",
            "status": "paper_internal_mismatch",
            "evidence": (
                "The Full values equal BTC-bull GPT-4o in Table 2, while ETH-bull GPT-4o in Table 3 is 25.47% and 0.18. "
                "The paper-author trace with those exact Full values is itself BTC-bull and declares gpt-3.5-turbo."
            ),
        },
    )
    write_csv(
        output_dir / "paper_internal_inconsistencies.csv",
        paper_inconsistencies,
        list(paper_inconsistencies[0]),
    )

    match_statuses = {
        "exact_displayed_precision_match",
        "native_lstm_seed_and_lookback_robust_match",
        "author_trace_exact_metric_and_native_state_replay",
    }
    matched = sum(row["status"] in match_statuses for row in conformance)
    mismatched = sum(row["status"] == "mismatch" for row in conformance)
    unverifiable = sum(row["status"].startswith("unverifiable") for row in conformance)
    traditional_matched = sum(
        row["status"] == "exact_displayed_precision_match" for row in conformance
    )
    deterministic_matched = sum(
        row["status"]
        in {
            "exact_displayed_precision_match",
            "native_lstm_seed_and_lookback_robust_match",
        }
        for row in conformance
    )
    lstm_robust_matched = sum(
        row["status"] == "native_lstm_seed_and_lookback_robust_match"
        for row in conformance
    )
    author_corroborated = sum(
        row["status"] == "author_trace_exact_metric_and_native_state_replay" for row in conformance
    )
    deterministic = traditional_matched + mismatched
    grouped: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = {}
    for row in conformance:
        grouped.setdefault((row["asset"], row["strategy"], row["regime"]), []).append(row)
    fully_matched_rows = sum(all(row["status"] in match_statuses for row in rows) for rows in grouped.values())
    mismatched_rows = sum(any(row["status"] == "mismatch" for row in rows) for rows in grouped.values())
    unverifiable_rows = sum(all(row["status"].startswith("unverifiable") for row in rows) for rows in grouped.values())
    split_price_matches = sum(
        row[metric] == "exact_displayed_precision_match" for row in splits for metric in ("open_status", "close_status")
    )
    split_trend_matches = sum(row["trend_status"] == "exact_displayed_precision_match" for row in splits)
    manifest: Dict[str, Any] = {
        "audit": "CryptoTrade paper claims versus pinned public code and data",
        "overall_status": "partial_reproduction_traditional_lstm_plus_author_llm_traces",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "original_anonymous_source_url": ORIGINAL_ANONYMOUS_SOURCE_URL,
        "original_anonymous_source_status_checked_2026_08_13": "http_410_repository_expired",
        "public_source_history_commits_audited": len(history),
        "public_source_history_result_or_log_paths": sum(row["result_or_log_paths"] for row in history),
        "public_fork_census_checked_at": PUBLIC_FORK_CENSUS_CHECKED_AT,
        "public_forks_total": PUBLIC_FORKS_TOTAL,
        "public_fork_branch_refs_total": PUBLIC_FORK_BRANCH_REFS_TOTAL,
        "public_fork_branch_ref_sequence_sha256": PUBLIC_FORK_BRANCH_REF_SEQUENCE_SHA256,
        "public_fork_branch_refs_reachable_from_official_or_author_history": (
            PUBLIC_FORK_BRANCH_REFS_REACHABLE_FROM_OFFICIAL_OR_AUTHOR_HISTORY
        ),
        "public_divergent_fork_heads_total": len(fork_divergence),
        "public_divergent_fork_heads_author_attributed": sum(
            row["attribution"] == "paper_author" for row in fork_divergence
        ),
        "public_divergent_fork_result_or_log_paths_total": sum(row["result_or_log_paths"] for row in fork_divergence),
        "public_divergent_fork_paper_result_credit_paths_total": 0,
        "paper_result_metric_cells_total": len(conformance) + len(ablation_conformance),
        "paper_tables_2_4_metric_cells_total": len(conformance),
        "paper_table_5_metric_cells_total": len(ablation_conformance),
        "native_deterministic_metric_cells_recomputed": 192,
        "native_deterministic_metric_cells_matched": deterministic_matched,
        "native_deterministic_metric_cells_mismatched": mismatched,
        "native_lstm_metric_cells_recomputed": 12,
        "native_lstm_protocol_robust_metric_cells_reproduced": lstm_robust_matched,
        "native_lstm_source_default_metric_cells_corresponding": 8,
        "native_lstm_source_default_only_metric_cells": 4,
        "native_lstm_fixed5_runs": 20,
        "native_lstm_fixed5_regime_runs": 60,
        "native_lstm_fixed5_cell_observations": 240,
        "native_lstm_fixed5_repeat_groups_exact": 120,
        "native_lstm_validation_grid_runs": 120,
        "native_lstm_validation_repeat_groups_exact": 60,
        "native_lstm_validation_all_lookbacks_tie": True,
        "native_lstm_seed_lookback_grid_runs": 60,
        "native_lstm_seed_lookback_regime_runs": 180,
        "native_lstm_seed_lookback_cell_observations": 720,
        "native_lstm_seed0_grid_repeat_cell_rows_exact": 72,
        "native_lstm_sideways_volatility_grid_matches": 0,
        "native_lstm_exact_declared_torch_runtime_reproduced": False,
        "native_lstm_compatible_runtime": LSTM_COMPATIBLE_ENVIRONMENT,
        "native_lstm_replay_llm_calls": 0,
        "native_lstm_replay_network_attempts": 0,
        "paper_metric_cells_corroborated_total": matched,
        "paper_numeric_evidence_correspondences_total": matched + len(ablation_conformance),
        "author_history_numeric_metric_cells_corresponding": author_corroborated + len(ablation_conformance),
        "author_history_llm_metric_cells_corroborated": author_corroborated,
        "author_history_llm_rows_corroborated": sum(
            trace["credit_status"].startswith("credited") for trace in author_traces.values()
        ),
        "author_history_llm_rows_numeric_match_but_no_credit": sum(
            trace["credit_status"].startswith("diagnostic") for trace in author_traces.values()
        ),
        "author_history_model_mismatch_traces_reassignment_checked": sum(
            bool(row["trace_declared_model_reassignment_required"])
            for row in author_trace_rows
        ),
        "author_history_declared_model_metric_cells_checked": 4 * sum(
            bool(row["trace_declared_model_reassignment_required"])
            for row in author_trace_rows
        ),
        "author_history_declared_model_metric_cells_matching": sum(
            int(row["trace_declared_model_metric_cells_matching"])
            for row in author_trace_rows
            if row["trace_declared_model_reassignment_required"]
        ),
        "author_history_declared_model_complete_rows_matching": sum(
            bool(row["trace_declared_model_complete_paper_row_match"])
            for row in author_trace_rows
            if row["trace_declared_model_reassignment_required"]
        ),
        "paper_result_metric_cells_unverifiable": unverifiable + len(ablation_conformance),
        "paper_strategy_regime_or_ablation_rows_total": len(grouped) + len(PAPER_ABLATION),
        "paper_strategy_regime_rows_total": len(grouped),
        "paper_strategy_regime_rows_fully_matched": fully_matched_rows,
        "paper_strategy_regime_rows_mismatched": mismatched_rows,
        "paper_strategy_regime_rows_unverifiable": unverifiable_rows,
        "traditional_strategy_rows_total": 45,
        "traditional_strategy_rows_fully_matched": 43,
        "traditional_strategy_cells_matched": 174,
        "traditional_strategy_cells_total": 180,
        "traditional_mismatches": (
            "ETH sideways SMA: daily mean and standard deviation; SOL bear SMA: all four displayed metrics"
        ),
        "traditional_mismatches_numerically_diagnosed": len(diagnosis),
        "traditional_mismatches_method_faithfully_reproduced": 0,
        "eth_sideways_sma_cells_duplicating_eth_bear": 2,
        "sol_bear_sma_cells_matching_undisclosed_period_1": 4,
        "dataset_split_price_cells_matched": split_price_matches,
        "dataset_split_price_cells_total": len(splits) * 2,
        "dataset_split_costed_trend_cells_matched": split_trend_matches,
        "dataset_split_costed_trend_cells_total": len(splits),
        "paper_described_validation_selections_matching_released_data_argmax": sum(
            row["status"] == "selection_rule_match" for row in selection
        ),
        "paper_described_validation_selections_total": len(selection),
        "paper_described_validation_nonidentifying_ties": sum(
            row["status"] == "selection_rule_nonidentifying_tie"
            for row in selection
        ),
        "paper_ablation_rows": len(PAPER_ABLATION),
        "paper_ablation_metric_cells_total": len(ablation_conformance),
        "paper_ablation_author_history_numeric_correspondences": sum(
            row["author_numeric_correspondence"] for row in ablation_conformance
        ),
        "paper_ablation_historical_code_action_replays_exact": sum(
            row["trace_role"] == "selected_numeric_correspondence" and row["historical_code_action_replay_exact"]
            for row in ablation_trace_rows
        ),
        "paper_ablation_method_faithful_metric_cells": sum(
            row["paper_method_faithful_credit"] for row in ablation_conformance
        ),
        "paper_ablation_rows_with_model_identity_match": sum(
            row["trace_role"] == "selected_numeric_correspondence" and row["model_identity_status"] == "match"
            for row in ablation_trace_rows
        ),
        "paper_ablation_rows_with_asset_identity_match": sum(
            row["trace_role"] == "selected_numeric_correspondence" and row["asset_identity_status"] == "match"
            for row in ablation_trace_rows
        ),
        "paper_ablation_full_eth_context_candidate_return_pct": 28.11,
        "paper_ablation_full_eth_context_candidate_sharpe_ratio": 0.08,
        "paper_ablation_full_values_duplicate_btc_bull_gpt4o": (PAPER_ABLATION["full"] == (28.47, 0.23)),
        "full_period_llm_result_logs_shipped_in_official_release": False,
        "matching_full_period_llm_result_traces_recovered_from_paper_author_history": True,
        "paper_author_history_ref": AUTHOR_HISTORY_REF,
        "paper_author_history_commit": AUTHOR_HISTORY_COMMIT,
        "paper_author_history_commits_audited": AUTHOR_HISTORY_COMMIT_COUNT,
        "paper_author_history_unique_output_blobs_audited": len(author_output_artifacts),
        "paper_author_history_output_blob_bytes_audited": sum(row["blob_bytes"] for row in author_output_artifacts),
        "paper_author_history_final_return_sharpe_summaries_audited": sum(
            row["final_return_sharpe_summaries"] for row in author_output_artifacts
        ),
        "paper_author_history_output_blobs_naming_time_series_model": sum(
            bool(row["exact_time_series_model_tokens"]) for row in author_output_artifacts
        ),
        "paper_author_history_output_blobs_matching_time_series_return_sharpe_pair": sum(
            bool(row["paper_time_series_return_sharpe_pair_matches"]) for row in author_output_artifacts
        ),
        "full_period_time_series_result_logs_shipped": False,
        "all_time_series_implementations_shipped": False,
        "readme_example_is_full_period_result": False,
        "readme_run_agent_shell_executable": bool((source_root / "run_agent.sh").stat().st_mode & stat.S_IXUSR),
        "run_agent_log_directory_shipped": (source_root / "logs").is_dir(),
        "dependency_lock_or_environment_manifest_shipped": any(
            (source_root / name).is_file()
            for name in ("requirements.txt", "pyproject.toml", "environment.yml", "Dockerfile")
        ),
        "source_prompts_asset_generic": False,
        "paper_gpt4_label_matches_released_gpt4_turbo_literal": False,
        "paper_transaction_fee_rate_disclosed": False,
        "source_exchange_fee_rate": float(environment_module.EX_RATE),
        "source_fixed_gas_fee_asset_units": float(environment_module.GAS_FEE),
        "source_contains_hardcoded_credential_literal": False,
        "audit_imported_or_used_credential_module": False,
        "interpretation": (
            "The released market data, native environment, costs, and traditional-signal logic "
            "reproduce 174/180 displayed traditional-baseline metric cells. Paper-author history "
            "additionally corroborates 40 LLM cells through exact metric and native state replay. "
            "A compatible CPU replay of the released ETH LSTM source function adds four bear-market "
            "cells that match across 10 seeds and all six paper-listed lookbacks. Four bull-market "
            "cells match the source-default lookback 5 but receive no strict credit because all "
            "lookbacks tie on validation and the bull outputs are lookback-sensitive. The compatible "
            "Torch 2.4.1 CPU runtime is not the README's declared Torch 2.3.0 CUDA environment. "
            "The five full-period model-mismatched traces cannot be reassigned to their declared "
            "GPT-3.5 paper rows: only 1/20 declared-model cells and 0/5 complete rows match. "
            "All 12 Table 5 values also have exact author-history numeric correspondences and replay "
            "through their historical code snapshots, but every selected trace conflicts with the "
            "paper's stated GPT-4o identity and the Full trace is BTC rather than ETH, so those cells "
            "receive zero method-faithful credit. This is strong component/output evidence, not a full "
            "CryptoTrade replication: 256 cells remain unverifiable, the six deterministic residuals have numeric but "
            "not method-faithful explanations, LSTM validation is a non-identifying six-way tie, "
            "and the documented entrypoints are not operational without repair. A dated 37-fork/39-ref "
            "census finds no additional attributable paper outputs. All 83 unique output blobs in the "
            "coauthor history were also scanned: none names a released time-series baseline or matches "
            "a paper time-series return/Sharpe pair."
        ),
        "source_file_sha256": {
            name: sha256(source_root / name)
            for name in (
                "README.md",
                "env_history.py",
                "eth_env.py",
                "eth_trial.py",
                "run_agent.py",
                "run_agent.sh",
                "run_baseline.py",
                "utils.py",
            )
        },
    }
    if (matched, mismatched, unverifiable) != (218, 6, 244):
        raise RuntimeError(
            "Pinned CryptoTrade conformance counts changed: "
            f"matched={matched}, mismatched={mismatched}, unverifiable={unverifiable}"
        )
    if (fully_matched_rows, mismatched_rows, unverifiable_rows) != (54, 2, 61):
        raise RuntimeError("Pinned CryptoTrade row-level conformance counts changed")

    report = f"""# CryptoTrade paper-level conformance audit

Overall verdict: **partial reproduction, not a full paper replication**. The pinned
public data and native trading environment strongly reproduce deterministic
traditional baselines. A public branch controlled by paper coauthor Nuo Chen also
preserves exact author action traces for part of the LLM table, but neither those
traces nor the official artifacts fully reproduce CryptoTrade's LLM/time-series study.

## Primary sources

- Official paper: {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.
- Paper-author history: Nuo Chen's public `nchen` branch, commit
  `{AUTHOR_HISTORY_COMMIT}` ({AUTHOR_HISTORY_COMMIT_COUNT} commits inspected).
- A bounded GitHub census on {PUBLIC_FORK_CENSUS_CHECKED_AT} covers all
  {PUBLIC_FORKS_TOTAL} accessible forks and {PUBLIC_FORK_BRANCH_REFS_TOTAL} fork branch refs.
  The first-author `NuoJohnChen` fork duplicates the already-audited `master` and
  `nchen` heads; it contributes no additional commit or result lineage.

## What reproduces

- A safe adapter over the released environment, 0.4% exchange cost, fixed gas cost,
  and traditional-signal logic matches {traditional_matched}/{deterministic} displayed cells
  across Buy-and-Hold, SMA, SLMA, MACD, and Bollinger Bands.
- 43/45 traditional strategy/asset/regime rows match all four
  displayed metrics (total return, daily mean, daily standard deviation, and
  Sharpe ratio). This includes every Buy-and-Hold, SLMA, MACD, and Bollinger row.
- The released ETH LSTM source function was executed for seeds 0--9, two repeats,
  all six paper-listed look-backs, the paper validation interval, and all three
  test regimes. All 120 fixed-look-back repeat groups are exact. The four bear
  metrics match across all 60 seed/look-back combinations and receive paper-result
  credit. The four bull metrics match all 20 fixed-look-back-5 observations, but
  only look-backs 5, 10, and 20 reproduce the full row. Because every look-back
  ties on validation, those bull correspondences receive no strict protocol credit.
  Sideways is seed/look-back sensitive, and its printed 1.11 volatility matches
  0/60 grid observations (native range 0.114--1.893).
- The coauthor history corroborates {author_corroborated}/108 LLM table cells across
  10/27 LLM rows. For each credited row, all four displayed values match and every
  recorded action replays through the pinned official data/environment with zero
  state error. This verifies historical author outputs; it does **not** regenerate
  the LLM decisions or prove current endpoint determinism.
- Table 5 adds 12 result cells that were previously omitted from the audit
  denominator. All 12 have exact numeric correspondences in the paper-author
  history, and the six selected action traces replay with zero state error against
  their own pinned historical code/data snapshots. They receive **0/12 faithful
  result credit**: all six declare `gpt-3.5-turbo`, not the paper's stated GPT-4o,
  and the trace matching the Full row is BTC-bull rather than the ETH experiment
  described around Table 5. The closer ETH/full-prompt trace reports 28.11%/0.08,
  not 28.47%/0.23.
  Reassigning the five full-period model-mismatched traces to their declared
  GPT-3.5 rows does not rescue them: only 1/20 individual cells coincides and
  0/5 complete declared-model rows match. The sixth diagnostic trace has the
  correct GPT-4 identity but ends before the paper period.
- ETH-sideways SMA matches the paper's -5.45% total return and -0.07 Sharpe, but
  the released path produces -0.07+/-1.00 daily return rather than -0.15+/-1.64.
  The paper's daily cell exactly duplicates its ETH-bear SMA daily cell.
- SOL-bear SMA is the larger mismatch: the paper reports +1.04% return,
  0.02+/-0.10 daily return, and 0.16 Sharpe. Those four cells exactly reproduce
  with a 1-day moving average, but the paper and source both define the candidate
  grid as [5, 10, 15, 20, 30]; every disclosed candidate loses 17.77%--22.19%.
  The numeric lineage is therefore diagnosed without claiming faithful replication.

## Why this is not a full reproduction

- {unverifiable + len(ablation_conformance)}/{len(conformance) + len(ablation_conformance)} paper result cells remain unverifiable. The
  official release ships no complete LLM result paths; the recovered author history
  contains no matching GPT-3.5 paper row and no complete matching SOL-bear GPT-4o row.
- Six additional LLM rows numerically match the paper but receive no credit: five
  traces declare `gpt-3.5-turbo` although their filenames/table assignments imply
  GPT-4/GPT-4o, and ETH-sideways GPT-4 stops on August 6 instead of completing the
  paper period through August 30. See `author_history_llm_trace_audit.csv`.
- The original paper URL points to an anonymous 4open artifact that now returns
  HTTP 410 (`repository_expired`). All {len(history)} commits in the successor
  official GitHub history were inspected; none preserves a result or log path.
  The recovered pre-reroot author snapshot and official root share all 406 earlier
  paths, with 400 byte-identical blobs; the remaining active execution logic is
  materially continuous, and action replay supplies the stronger numeric check.
- Of {PUBLIC_FORK_BRANCH_REFS_TOTAL} fork refs, {PUBLIC_FORK_BRANCH_REFS_REACHABLE_FROM_OFFICIAL_OR_AUTHOR_HISTORY}
  are already reachable from the pinned official/coauthor histories. The four
  divergent heads are all unaffiliated and post-paper: a Gemini 2.5 experiment
  with empty/non-paper result files, a NIFTY-50/Gemini rewrite, a local-model and
  Taiwan-market six-agent extension, and a descriptor/PDF-only fork. Their
  {sum(row["result_or_log_paths"] for row in fork_divergence)} result/log-like paths
  receive zero paper credit. See `public_fork_divergence_inventory.csv`.
- Informer, AutoFormer, TimesNet, and PatchTST implementations are absent. The
  included LSTM is embedded in an ETH-only monolithic runner, has no seed, trains
  on the full requested interval, and ships no result path. Its raw entrypoint also
  omits the required `dataset` argument and hard-codes unavailable `cuda:7`. The
  audit uses a compatible Torch 2.4.1 CPU runtime rather than the README's declared
  Torch 2.3.0/CUDA environment, so exact-runtime reproduction remains false.
- The complete coauthor history contains 83 unique `.out` blobs totaling
  209,739,069 bytes. An exhaustive scan of their 1,371 final return/Sharpe summaries
  finds no standalone LSTM, Informer, AutoFormer, TimesNet, or PatchTST model token
  and no return/Sharpe pair matching any of the 45 published time-series rows. See
  `author_history_output_artifact_census.csv`.
- The paper says SMA/SLMA/LSTM parameters are selected on validation performance. The
  source prints candidate validation results and then hard-codes SMA=15 and
  SLMA=15/30; its LSTM branch hard-codes look-back 5. Only
  {manifest["paper_described_validation_selections_matching_released_data_argmax"]}/7
  fixed traditional choices equal the released-data validation argmax, while the
  LSTM validation grid is a non-identifying six-way tie.
- The paper does not disclose the transaction-fee rate. The source uses 0.4% of
  traded value plus a fixed gas charge, which is necessary to match the tables.
- `run_agent.sh` is tracked as non-executable and redirects into an absent `logs/`
  directory. Its active GPT-4o ETH/SOL sideways commands use dates that differ
  from Table 1. `run_baseline.py` omits `dataset` when constructing the environment
  and depends on packages absent from the README requirement list.
- Prompt templates hard-code ETH even for BTC and SOL. The paper's generic GPT-4
  label is implemented by the source as `gpt-4-turbo`; credited GPT-4 traces use
  that released mapping, so they are source-output corroboration rather than proof
  of exact paper endpoint identity. No immutable model snapshot exists, and a
  present-day paid rerun would not prove the published result.
- The released utility reads `OPENAI_API_KEY` from the environment. This audit does
  not import the API utility or call an endpoint.

## Paper/source inconsistencies retained as evidence

- Table 5 calls the ablation ETH/GPT-4o, but its Full values (28.47%, 0.23) exactly
  duplicate BTC-bull GPT-4o in Table 2; ETH-bull GPT-4o is 25.47%, 0.18 in Table 3.
  The recovered exact-value trace is BTC-bull and declares GPT-3.5, while the
  recovered ETH/full-prompt trace is 28.11%/0.08. The other five Table 5 values
  also come from traces declaring GPT-3.5. This supplies strong numeric lineage
  while making a method-faithful Table 5 reproduction less, not more, defensible.
- The released test-period data usually match Table 1 and exactly drive the
  traditional results, but validation prices diverge and the BTC-bear start and
  SOL-bull end prices also differ. See `dataset_split_conformance.csv`.

Run `scripts/audit_cryptotrade_paper.py` to regenerate this package. Use `--strict`
when a CI failure is desired until a defensible full-paper result exists.
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
        default=Path(
            os.environ.get(
                "CRYPTOTRADE_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/cryptotrade_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "CRYPTOTRADE_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/cryptotrade_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--lstm-results-root",
        type=Path,
        default=Path(
            os.environ.get(
                "CRYPTOTRADE_LSTM_RESULTS_ROOT", str(DEFAULT_LSTM_RESULTS_ROOT)
            )
        ),
    )
    parser.add_argument(
        "--lstm-python-wrapper",
        type=Path,
        default=Path(
            os.environ.get(
                "CRYPTOTRADE_LSTM_PYTHON_WRAPPER",
                str(DEFAULT_LSTM_PYTHON_WRAPPER),
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/cryptotrade",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.paper_pdf.resolve(),
        args.lstm_results_root.resolve(),
        args.lstm_python_wrapper.absolute(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and manifest["overall_status"] != "reproduced")


if __name__ == "__main__":
    sys.exit(main())
