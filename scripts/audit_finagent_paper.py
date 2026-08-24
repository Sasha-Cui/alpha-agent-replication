#!/usr/bin/env python3
"""Fail-closed paper/source audit for FinAgent (KDD 2024).

The arXiv v3 paper is the detailed result authority and the KDD proceedings
PDF is the publication authority, but v1 and v2 are also pinned and compared
cell by cell because v3 materially revises the result record. The released
repository is linked from the lead author's current homepage. Static source
conformance, paper-source compilation, and shipped strategy records are useful
evidence, but none are promoted to experimental-result reproduction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


ARXIV_URL = "https://arxiv.org/abs/2402.18485"
ARXIV_V3_DATE = "2024-06-28"
ARXIV_V3_PDF_SHA256 = "c5964450c7dd29c00cc92cbc845cd14223d08f04429f6b4b0c612c8678b69922"
ARXIV_V3_SOURCE_SHA256 = "421e432111f5543c9f7c1ba1a2b65d1d8b3ba686ad5f02c937b0d60561eaf1a7"
KDD_PDF_URL = "https://dl.acm.org/doi/pdf/10.1145/3637528.3671684"
KDD_PDF_SHA256 = "cfc31d78f7919c104f741aee197866bd8f8a938b2504b5f8eebc8b1b57f40dd8"
DOI = "10.1145/3637528.3671684"
AUTHOR_HOMEPAGE = "https://dvampire.github.io/"
SOURCE_URL = "https://github.com/DVampire/FinAgent"
SOURCE_PAPER_COMMIT = "08fb217d374b6c923b0ab3e6dbd8213e1d0fcf1c"
SOURCE_PAPER_DATE = "2024-04-11T14:03:24+08:00"
SOURCE_PAPER_TREE = "70c0a2277fded3b77195b74ab71e0d2c8723a6a4"
SOURCE_PAPER_ARCHIVE_SHA256 = "9d530843df299e08c8642b296dd5116f229fd8fb41fb42b13a8d0f113f275d4d"
SOURCE_CURRENT_COMMIT = "17248a0b8b729ee3e093e30bb7bea7f52181f363"
SOURCE_CURRENT_DATE = "2024-08-31T20:13:54+02:00"
SOURCE_CURRENT_DATE_UTC = "2024-08-31T18:13:54Z"
SOURCE_CURRENT_TREE = "71047850ceab7579e8c083dfada486bbbae17007"
SOURCE_CURRENT_ARCHIVE_SHA256 = "e2954e7b22b4d1280ac28de2af979907ad3e7d5f1a8e203add2926414cff9c5c"
SOURCE_REQUIREMENTS_SHA256 = (
    "036fbac0cb161617b732478980aa484ef72d27ddd393739fa0fd343a03edb838"
)
PANDAS_TA_MIRROR_URL = "https://github.com/MerlinR/Pandas-ta-fork"
PANDAS_TA_MIRROR_COMMIT = "45db59038e6414216195dd1c24413d56ff829958"
DEFAULT_PAPER_PYTHON = str(
    Path(__file__).resolve().parent / "run_finagent_paper_python.sh"
)
PAPER_ENV_FREEZE_SHA256 = (
    "a22e445cbb6f87bf6ee65f8b24c8ef66109b64be15d64e031963a0b2e2e3529b"
)
AUDIT_DATE = "2026-08-14"
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_REST_COUNT = 26
PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT = 26
PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT = 30
PUBLIC_FORK_GRAPHQL_REF_SHA256 = "ac59ada9d1819a8117a8e5b1e0b9d4fc9c12eeda5981158d7950c7ee3db7c472"
PUBLIC_FORK_SNAPSHOT_SHA256 = "9dbc6cf87c7cfee96b229da87c31636cd79864d93b85726f5c8ed946a8bda667"
PUBLIC_FORK_REPRESENTATIVE_REF_COUNT = 7
PUBLIC_FORK_REPRESENTATIVE_REF_SHA256 = "c81a0f886d967d03bda551198f966cf12aee39322456c76d29c397188923278a"
PUBLIC_FORK_UNIQUE_HEAD_SHA256 = "9d8b679af9342aeb5105929b0a0cbf1bb7918c4e697f66886d5f05dd790531f2"
PUBLIC_FORK_BASE_REACHABLE_HEAD_COUNT = 2
PUBLIC_FORK_DIVERGENT_HEAD_COUNT = 5
PUBLIC_FORK_DIVERGENT_SURFACE_SHA256 = "aa15a29fa402af261b6166d641a4069be4b58c451bf5e84261c7e994949c11e0"
PUBLIC_FORK_DIVERGENT_COMMIT_COUNT = 27
PUBLIC_FORK_DIVERGENT_COMMIT_SHA256 = "5b201884d7f1d8aab98070e46e096d8457769dc52aa829ebc6f2c79d055edf54"
PUBLIC_FORK_DIVERGENT_PATH_COUNT = 93
PUBLIC_FORK_DIVERGENT_PATH_SHA256 = "4f633b0846ee89294a8caab1b1fe8267784bce800e5b8ea535f9a85348bd1079"
PUBLIC_FORK_NEW_FINAL_BLOB_REF_COUNT = 35
PUBLIC_FORK_NEW_FINAL_BLOB_REF_SHA256 = "43cf3d331a05489660cf624422c9edb57194117083c1f9333d54e72cac8facfe"
PUBLIC_FORK_NEW_FINAL_UNIQUE_BLOB_COUNT = 24
PUBLIC_FORK_NEW_FINAL_UNIQUE_BLOB_SHA256 = "4a2c11840049c2176e1ecf0a8ee8dd980fdd4eec508f1889ffd305fadfee8a4d"
PUBLIC_FORK_NEW_FINAL_PATH_COUNT = 18
PUBLIC_FORK_NEW_FINAL_PATH_SHA256 = "3a29a706ca7a81002ef55aec2166462dece58bb624df6e07567e3b377bd28544"
OFFICIAL_SOURCE_AUTHOR_EMAILS = {"1271421361@qq.com", "wt.zhang@ntu.edu.sg"}
OFFICIAL_SOURCE_AUTHOR_NAMES = {"wentao", "Wentao Zhang"}
EXPECTED_DIVERGENT_AUTHOR_EMAILS = {
    "127190668+BilalB84@users.noreply.github.com",
    "dltjrwlsajtwu@gmail.com",
    "ij020554@konkuk.ac.kr",
    "lute7071@gmail.com",
    "sasmco12@gmail.com",
}
DIVERGENT_FORK_FINDINGS: Mapping[str, Mapping[str, Any]] = {
    "035d6a18e42087f06918a33ccdfabdb128b19a0b": {
        "commits": 9,
        "paths": 80,
        "classification": "unattributed_postpaper_function_call_source_extension",
    },
    "191f7f16bcf971a48d48a4b156f567907043cef6": {
        "commits": 6,
        "paths": 4,
        "classification": "unattributed_postpaper_news_source_extension",
    },
    "8dd9fcf48d0d286bb0ac5a5c9e3bcac074726788": {
        "commits": 5,
        "paths": 71,
        "classification": "unattributed_postpaper_function_call_source_extension",
    },
    "b2deb8f1a7b01133d7a28145c56c09c72edee456": {
        "commits": 13,
        "paths": 13,
        "classification": "unattributed_postpaper_ftse_mib_data_pipeline_adaptation",
    },
    "b918d35623786e8fc0b58a94802015778da3db8b": {
        "commits": 8,
        "paths": 73,
        "classification": "unattributed_postpaper_prompt_source_extension",
    },
}

PAPER_VERSIONS = {
    1: {
        "submitted_at": "2024-02-28T17:06:54Z",
        "pdf_sha256": "6e64f3b3f280692d3f7f859a73ce77cab202adc1f462c860c5c9c12caaf6aea9",
        "pdf_bytes": 15107289,
        "pdf_pages": 46,
        "source_sha256": "38ac98bb92a13a001e675457cbca7a60655879620bc3564519b235b190ede536",
        "source_bytes": 14344252,
        "source_files": 97,
        "source_uncompressed_bytes": 20246006,
        "main_sha256": "3cd9ae738c3867869097eb78851d9b1c457cb1c05223c4ea8e6e3bf1e7d40462",
        "source_tree_digest": "b4c0564cca650a93473074a2d9cb8526832b8cf6335b1424760d8d0a318227f1",
        "table_cells": 768,
        "repository_commits_at_submission": 0,
        "latest_public_commit_at_submission": "",
    },
    2: {
        "submitted_at": "2024-02-29T12:49:03Z",
        "pdf_sha256": "4cb339d279076a4a546f8cb213b73036a910ba1532c592fd42276a4add63d603",
        "pdf_bytes": 15107276,
        "pdf_pages": 46,
        "source_sha256": "36f87c7fb7bf693556355ded569fd2123ec3cac67205976379d51a0450e7ace8",
        "source_bytes": 14344177,
        "source_files": 97,
        "source_uncompressed_bytes": 20246006,
        "main_sha256": "e7246cabfed418b5336e307f7ccc61eb4bad6aa87a1e9708fc3cede985feb2e1",
        "source_tree_digest": "230e309810a4df56e7c100accb8c8eb00e2bcd9f4d35c94b7bdb2af11f040c43",
        "table_cells": 768,
        "repository_commits_at_submission": 0,
        "latest_public_commit_at_submission": "",
    },
    3: {
        "submitted_at": "2024-06-28T10:35:56Z",
        "pdf_sha256": ARXIV_V3_PDF_SHA256,
        "pdf_bytes": 15364998,
        "pdf_pages": 43,
        "source_sha256": ARXIV_V3_SOURCE_SHA256,
        "source_bytes": 14723655,
        "source_files": 99,
        "source_uncompressed_bytes": 20750696,
        "main_sha256": "32a375347d3e8bb5a41ef203815a45e99e2b49c18f6d8c9d6765110e70aec7f8",
        "source_tree_digest": "04e1e10fa5e5e9024751ad79367749237ef20bde4a47c27bd12f74cf404a44d4",
        "table_cells": 959,
        "repository_commits_at_submission": 6,
        "latest_public_commit_at_submission": SOURCE_PAPER_COMMIT,
    },
}

PUBLIC_HISTORY_COMMIT_COUNT = 7
PUBLIC_HISTORY_COMMIT_SHA256 = "369b01bb4c9e14dac77b7edf74d25800bddfc15c713467c4ecc22d6001e66a60"
PUBLIC_HISTORY_PATH_COUNT = 1955
PUBLIC_HISTORY_PATH_SHA256 = "da702298ef4ef41809512edd43e1fdd84d0f875eb41d65df85a519a0347ca764"
PUBLIC_HISTORY_OBJECT_COUNTS = {"blob": 1902, "commit": 7, "tree": 327}
PUBLIC_DISCOVERY_SHA256 = {
    "branches.json": "301b4166efb6f15f3388bf264b02c517645a45dc74a4bf517d4a5cc52f6d78ca",
    "releases.json": "2ba33ca0557f1bb5b7ba88d67f9d0093c7185a36ec51fe2b7bd9372d3e001d6d",
    "tags.json": "2ba33ca0557f1bb5b7ba88d67f9d0093c7185a36ec51fe2b7bd9372d3e001d6d",
}

ASSETS = ("AAPL", "AMZN", "GOOGL", "MSFT", "TSLA", "ETHUSD")
MAIN_METHODS = (
    "B&H", "MACD", "KDJ&RSI", "ZMR", "LGBM", "LSTM", "Transformer",
    "DQN", "SAC", "PPO", "FinGPT", "FinMem", "FinAgent",
)
EARLY_MAIN_METHODS = (
    "B&H", "MACD", "KDJ&RSI", "ZMR", "DQN", "SAC", "PPO", "FinGPT",
    "FinMem", "FinAgent",
)
APPENDIX_METHODS = (
    "B&H", "MACD", "KDJ&RSI", "ZMR", "LGBM", "LSTM", "Transformer",
    "DQN", "SAC", "PPO", "FinGPT", "FinMem", "No-finetuned", "w/o-MLH",
    "w/o-LHT", "w/o-HT", "w/o-T", "FinAgent",
)
EARLY_APPENDIX_METHODS = (
    "B&H", "MACD", "KDJ&RSI", "ZMR", "DQN", "SAC", "PPO", "FinGPT",
    "FinMem", "w/o-MLH", "w/o-LHT", "w/o-HT", "w/o-T", "FinAgent",
)
MAIN_METRICS = ("ARR_pct", "SR", "MDD_pct")
APPENDIX_PANELS = (
    ("ARR_pct", "SR", "MDD_pct"),
    ("SOR", "CR", "VOL"),
)
FIGURE4_SERIES = (
    "B&H", "MACD", "KDJ&RSI", "SO&BB", "ZMR", "DQN", "SAC", "PPO",
    "FinGPT", "FinMem", "FinAgent",
)
APPENDIX_RESULT_GRAPHICS = (
    "assets/finagent_and_baselines/ppo/AAPL_PPO.pdf",
    "assets/finagent_and_baselines/ppo/GOOGL_PPO.pdf",
    "assets/finagent_and_baselines/dqn/GOOGL_DQN.pdf",
    "assets/finagent_and_baselines/dqn/AMZN_DQN.pdf",
    "assets/finagent_and_baselines/dqn/ETH_DQN.pdf",
    "assets/finagent_and_baselines/sac/ETH_SAC.pdf",
    "assets/finagent_and_baselines/sac/MSFT_SAC.pdf",
    "assets/finagent_and_baselines/sac/AMZN_SAC.pdf",
    "assets/finagent_and_baselines/fingpt/AAPL_FinGPT.pdf",
    "assets/finagent_and_baselines/fingpt/GOOGL_FinGPT.pdf",
    "assets/finagent_and_baselines/fingpt/MSFT_FinGPT.pdf",
    "assets/finagent_and_baselines/fingpt/TSLA_FinGPT.pdf",
    "assets/finagent_and_baselines/finmem/AAPL_FinMem.pdf",
    "assets/finagent_and_baselines/finmem/MSFT_FinMem.pdf",
    "assets/finagent_and_baselines/finmem/TSLA_FinMem.pdf",
    "assets/finagent_and_baselines/finmem/ETHUSD_FinMem.pdf",
    "assets/finagent_and_baselines/MACD/MACD_AAPL.pdf",
    "assets/finagent_and_baselines/MACD/MACD_GOOGL.pdf",
    "assets/finagent_and_baselines/MACD/MACD_ETHUSD.pdf",
    "assets/finagent_and_baselines/MACD/MACD_MSFT.pdf",
    "assets/finagent_and_baselines/KDJ_RSI/KDJ_RSI_AAPL.pdf",
    "assets/finagent_and_baselines/KDJ_RSI/KDJ_RSI_TSLA.pdf",
    "assets/finagent_and_baselines/ZMR/ZMR_AAPL.pdf",
    "assets/finagent_and_baselines/ZMR/ZMR_TSLA.pdf",
    "assets/finagent_and_baselines/tool_router/ETHUSD.pdf",
    "assets/finagent_and_baselines/tool_router/AAPL.pdf",
    "assets/finagent_and_baselines/finagent/AAPL_FinAgent.pdf",
    "assets/finagent_and_baselines/finagent/GOOGL_FinAgent.pdf",
    "assets/finagent_and_baselines/finagent/ETHUSD_FinAgent.pdf",
)
RULE_STRATEGY_METHODS = {
    "0": "B&H",
    "1": "MACD",
    "2": "KDJ&RSI",
    "4": "ZMR",
}
RECORD_METRICS = {
    "ARR_pct": ("ARR", 100.0),
    "SR": ("SR", 1.0),
    "MDD_pct": ("MDD", 100.0),
    "SOR": ("SOR", 1.0),
    "CR": ("CR", 1.0),
    "VOL": ("VOL", 1.0),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git(source_root: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source_root), *args], check=True,
        capture_output=True, text=not binary,
    )
    return proc.stdout


def sha256_lines(lines: Sequence[str]) -> str:
    return sha256_bytes("".join(f"{line}\n" for line in lines).encode("utf-8"))


def git_object_exists(source_root: Path, object_spec: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "-e", object_spec],
        check=False, capture_output=True,
    ).returncode == 0


def git_archive_sha256(source_root: Path, commit: str) -> str:
    return hashlib.sha256(git(source_root, "archive", commit, binary=True)).hexdigest()


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _active_table(text: str, label: str) -> str:
    end = text.rindex(label)
    starts = [match.start() for match in re.finditer(r"\\begin\{table\*?\}", text[:end])]
    if not starts:
        raise ValueError(f"active table not found before {label}")
    start = starts[-1]
    return text[start:end]


def _semantic_cells(line: str) -> list[str]:
    return [cell.strip() for cell in re.split(r"(?<!\\)&", line) if cell.strip()]


def _number(cell: str) -> str | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", cell)
    return match.group(0) if match else None


def _method_name(cell: str) -> str | None:
    for method in sorted(APPENDIX_METHODS, key=len, reverse=True):
        if method in cell or method.replace("&", "\\&") in cell:
            return method
    return None


def _result_row(table: str, item: str, metric: str, value: str) -> dict[str, Any]:
    return {
        "paper_table": table,
        "display_cell_id": f"{table}/{item}/{metric}",
        "item": item,
        "metric": metric,
        "paper_value": value,
        "native_reproduced_value": "",
        "status": "not_reproduced_no_released_agent_result_artifacts_or_exact_inputs",
        "paper_result_credit": False,
    }


def _method_rows(block: str, methods: Sequence[str], metrics: Sequence[str], table: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: list[str] = []
    for raw in block.splitlines():
        if raw.lstrip().startswith("%") or not raw.lstrip().startswith("&"):
            continue
        cells = _semantic_cells(raw)
        if not cells:
            continue
        method = _method_name(cells[0])
        if method not in methods:
            continue
        values = [_number(cell) for cell in cells[1:]]
        values = [value for value in values if value is not None]
        expected = len(ASSETS) * len(metrics)
        if len(values) != expected:
            raise RuntimeError(f"{table}/{method}: expected {expected} values, got {len(values)}")
        seen.append(method)
        for asset_index, asset in enumerate(ASSETS):
            for metric_index, metric in enumerate(metrics):
                value = values[asset_index * len(metrics) + metric_index]
                rows.append(_result_row(table, f"{asset}/{method}", metric, value))
    if tuple(seen) != tuple(methods):
        raise RuntimeError(f"{table}: method order changed: {seen}")
    return rows


def _improvement_rows(block: str, table: str, metrics: Sequence[str]) -> list[dict[str, Any]]:
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("%") and "Improvement" in line:
            values_line = lines[index + 1]
            cells = _semantic_cells(values_line)
            rows: list[dict[str, Any]] = []
            semantic_index = 0
            for asset in ASSETS:
                for metric in metrics:
                    if semantic_index >= len(cells):
                        raise RuntimeError(f"{table}: truncated improvement row")
                    value = _number(cells[semantic_index])
                    semantic_index += 1
                    if value is not None:
                        rows.append(_result_row(table, f"{asset}/Improvement", metric, value))
            return rows
    raise RuntimeError(f"{table}: active improvement row missing")


def paper_table_rows(paper_source_root: Path, paper_version: int = 3) -> list[dict[str, Any]]:
    if paper_version not in PAPER_VERSIONS:
        raise ValueError(f"unsupported FinAgent paper version: {paper_version}")
    main_methods = EARLY_MAIN_METHODS if paper_version < 3 else MAIN_METHODS
    appendix_methods = EARLY_APPENDIX_METHODS if paper_version < 3 else APPENDIX_METHODS
    main_block = _active_table(
        (paper_source_root / "tables/baselines.tex").read_text(encoding="utf-8"),
        "\\label{tab:baselines}",
    )
    rows = _method_rows(main_block, main_methods, MAIN_METRICS, "Table 4 main comparison")
    rows += _improvement_rows(main_block, "Table 4 main comparison", MAIN_METRICS)

    appendix_block = _active_table(
        (paper_source_root / "tables/appendix_baselines.tex").read_text(encoding="utf-8"),
        "\\label{tab:app_baselines}",
    )
    split_marker = "\\toprule\n\\multirow{3}{*}{Categories}"
    pieces = appendix_block.split(split_marker)
    if len(pieces) != 3:
        raise RuntimeError("Appendix Table 7 two-panel boundary changed")
    for panel_index, metrics in enumerate(APPENDIX_PANELS):
        panel = pieces[panel_index + 1]
        table = f"Appendix Table 7 panel {panel_index + 1}"
        rows += _method_rows(panel, appendix_methods, metrics, table)
        rows += _improvement_rows(panel, table, metrics)

    ablation_block = _active_table(
        (paper_source_root / "tables/ablation.tex").read_text(encoding="utf-8"),
        "\\label{tab:ablation}",
    )
    variants = ("T_only", "M_only", "ML", "MLH", "MLHT")
    candidate_lines = [
        line for line in ablation_block.splitlines()
        if not line.lstrip().startswith("%") and "surd" in line and "&" in line
    ]
    if len(candidate_lines) != 5:
        raise RuntimeError(f"Table 5: expected five ablation rows, got {len(candidate_lines)}")
    for variant, line in zip(variants, candidate_lines):
        values = re.findall(r"[-+]?\d+(?:\.\d+)?", line)
        expected = 6 if variant in ("T_only", "M_only") else 12
        if len(values) != expected:
            raise RuntimeError(f"Table 5/{variant}: expected {expected} values, got {len(values)}")
        cursor = 0
        for asset in ("TSLA", "ETHUSD"):
            for metric in MAIN_METRICS:
                rows.append(_result_row("Table 5 ablation", f"{asset}/{variant}", metric, values[cursor]))
                cursor += 1
                if expected == 12:
                    rows.append(_result_row(
                        "Table 5 ablation", f"{asset}/{variant}", f"{metric}_parenthetical_delta_pct",
                        values[cursor],
                    ))
                    cursor += 1

    expected_counts = (
        {
            "Table 4 main comparison": 191,
            "Appendix Table 7 panel 1": 266,
            "Appendix Table 7 panel 2": 263,
            "Table 5 ablation": 48,
        }
        if paper_version < 3
        else {
            "Table 4 main comparison": 242,
            "Appendix Table 7 panel 1": 335,
            "Appendix Table 7 panel 2": 334,
            "Table 5 ablation": 48,
        }
    )
    if len(rows) != PAPER_VERSIONS[paper_version]["table_cells"] or Counter(
        row["paper_table"] for row in rows
    ) != expected_counts:
        raise RuntimeError("FinAgent paper table census changed")
    return rows


def paper_figure_rows(paper_source_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in ASSETS:
        for series in FIGURE4_SERIES:
            rows.append({
                "paper_figure": "Figure 4 cumulative return",
                "display_unit": f"{asset}/{series}",
                "source_asset": "assets/baselines.pdf",
                "native_reproduced": False,
                "status": "raster_or_vector_plot_only_no_underlying_trajectory",
                "paper_result_credit": False,
            })
    for unit in ("ML", "MLH", "MLHT", "T"):
        rows.append({
            "paper_figure": "Figure 5 component ablation",
            "display_unit": unit,
            "source_asset": "assets/dr.pdf",
            "native_reproduced": False,
            "status": "plot_only_no_underlying_trial_records",
            "paper_result_credit": False,
        })
    for unit in ("without_diversification", "rag", "rag_plus_diversification"):
        rows.append({
            "paper_figure": "Figure 5 retrieval/diversification",
            "display_unit": unit,
            "source_asset": "assets/dr.pdf",
            "native_reproduced": False,
            "status": "plot_only_no_underlying_trial_records",
            "paper_result_credit": False,
        })
    for asset_path in APPENDIX_RESULT_GRAPHICS:
        if not (paper_source_root / asset_path).is_file():
            raise RuntimeError(f"active appendix result graphic missing: {asset_path}")
        rows.append({
            "paper_figure": "Appendix qualitative/performance cases",
            "display_unit": Path(asset_path).stem,
            "source_asset": asset_path,
            "native_reproduced": False,
            "status": "graphic_only_no_underlying_action_or_equity_path",
            "paper_result_credit": False,
        })
    if len(rows) != 102:
        raise RuntimeError(f"expected 102 figure display units, got {len(rows)}")
    return rows


def pdf_page_count(path: Path) -> int:
    output = subprocess.run(
        ["pdfinfo", str(path)], check=True, capture_output=True, text=True
    ).stdout
    match = re.search(r"^Pages:\s+(\d+)$", output, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"pdfinfo did not report a page count for {path}")
    return int(match.group(1))


def source_tree_digest(source_root: Path) -> str:
    rows = [
        f"{path.relative_to(source_root).as_posix()}\0{sha256(path)}"
        for path in sorted(path for path in source_root.rglob("*") if path.is_file())
    ]
    return sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))


def paper_version_rows(
    versions_root: Path, source_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    parsed = {
        version: paper_table_rows(versions_root / f"source_v{version}", version)
        for version in PAPER_VERSIONS
    }
    by_version = {
        version: {str(row["display_cell_id"]): str(row["paper_value"]) for row in rows}
        for version, rows in parsed.items()
    }
    if by_version[1] != by_version[2]:
        raise RuntimeError("FinAgent arXiv v1/v2 result tables diverged")
    v1 = by_version[1]
    v3 = by_version[3]
    all_ids = sorted(set(v1) | set(v3))
    lineage = []
    for cell_id in all_ids:
        early = v1.get(cell_id, "")
        latest = v3.get(cell_id, "")
        if not early:
            status = "added_in_v3"
        elif not latest:
            status = "removed_in_v3"
        elif float(early) != float(latest):
            status = "numeric_value_revised_in_v3"
        elif early != latest:
            status = "display_precision_only_change_in_v3"
        else:
            status = "unchanged_v1_through_v3"
        lineage.append(
            {
                "display_cell_id": cell_id,
                "v1_value": early,
                "v2_value": early,
                "v3_value": latest,
                "status": status,
                "native_reproduced": False,
                "paper_result_credit": False,
            }
        )
    expected_lineage = {
        "unchanged_v1_through_v3": 679,
        "display_precision_only_change_in_v3": 55,
        "numeric_value_revised_in_v3": 27,
        "added_in_v3": 198,
        "removed_in_v3": 7,
    }
    if Counter(row["status"] for row in lineage) != expected_lineage:
        raise RuntimeError("FinAgent official-version result lineage changed")

    result_figure_assets = ("assets/baselines.pdf", "assets/dr.pdf", *APPENDIX_RESULT_GRAPHICS)
    v3_figure_hashes = {
        relative: sha256(versions_root / "source_v3" / relative)
        for relative in result_figure_assets
    }
    rows = []
    for version, expected in PAPER_VERSIONS.items():
        pdf = versions_root / f"paper_v{version}.pdf"
        archive = versions_root / f"paper_v{version}_source.tar.gz"
        extracted = versions_root / f"source_v{version}"
        files = [path for path in extracted.rglob("*") if path.is_file()]
        if sha256(pdf) != expected["pdf_sha256"] or pdf.stat().st_size != expected["pdf_bytes"]:
            raise RuntimeError(f"FinAgent arXiv v{version} PDF drift")
        if pdf_page_count(pdf) != expected["pdf_pages"]:
            raise RuntimeError(f"FinAgent arXiv v{version} page census changed")
        if sha256(archive) != expected["source_sha256"] or archive.stat().st_size != expected["source_bytes"]:
            raise RuntimeError(f"FinAgent arXiv v{version} source archive drift")
        if len(files) != expected["source_files"] or sum(path.stat().st_size for path in files) != expected[
            "source_uncompressed_bytes"
        ]:
            raise RuntimeError(f"FinAgent arXiv v{version} source census changed")
        if sha256(extracted / "main.tex") != expected["main_sha256"]:
            raise RuntimeError(f"FinAgent arXiv v{version} main source drift")
        if source_tree_digest(extracted) != expected["source_tree_digest"]:
            raise RuntimeError(f"FinAgent arXiv v{version} extracted source tree drift")
        if any(sha256(extracted / relative) != digest for relative, digest in v3_figure_hashes.items()):
            raise RuntimeError(f"FinAgent arXiv v{version} result figures changed")
        figures = paper_figure_rows(extracted)
        cutoff = str(expected["submitted_at"])
        commits = int(str(git(source_root, "rev-list", "--all", f"--before={cutoff}", "--count")).strip())
        latest = str(
            git(source_root, "log", "--all", f"--before={cutoff}", "-1", "--format=%H")
        ).strip()
        if commits != expected["repository_commits_at_submission"] or latest != expected[
            "latest_public_commit_at_submission"
        ]:
            raise RuntimeError(f"FinAgent source cutoff changed for arXiv v{version}")
        common = set(by_version[version]) & set(v3)
        numeric_changes = sum(
            float(by_version[version][cell]) != float(v3[cell]) for cell in common
        )
        display_only = sum(
            float(by_version[version][cell]) == float(v3[cell])
            and by_version[version][cell] != v3[cell]
            for cell in common
        )
        rows.append(
            {
                "paper_version": f"v{version}",
                "submitted_at": cutoff,
                "pdf_sha256": expected["pdf_sha256"],
                "pdf_bytes": expected["pdf_bytes"],
                "pdf_pages": expected["pdf_pages"],
                "source_archive_sha256": expected["source_sha256"],
                "source_archive_bytes": expected["source_bytes"],
                "source_files": expected["source_files"],
                "source_uncompressed_bytes": expected["source_uncompressed_bytes"],
                "source_tree_digest": expected["source_tree_digest"],
                "numeric_table_cells": len(parsed[version]),
                "figure_display_units": len(figures),
                "result_figure_assets_byte_identical_to_v3": True,
                "table_values_same_as_previous_version": "" if version == 1 else by_version[version] == by_version[version - 1],
                "table_cell_ids_common_with_v3": len(common),
                "numeric_values_changed_relative_to_v3": numeric_changes,
                "display_precision_only_changes_relative_to_v3": display_only,
                "cell_ids_added_in_v3": len(set(v3) - set(by_version[version])),
                "cell_ids_removed_in_v3": len(set(by_version[version]) - set(v3)),
                "public_repository_commits_at_submission": commits,
                "latest_public_commit_at_submission": latest,
                "public_source_available_at_submission": bool(commits),
                "native_result_reproduced": False,
                "paper_result_credit": False,
            }
        )
    return rows, lineage


def source_inventory(source_root: Path, commit: str = SOURCE_PAPER_COMMIT) -> list[dict[str, Any]]:
    paths = git(source_root, "ls-tree", "-r", "--name-only", commit).splitlines()
    rows = []
    for path in paths:
        suffix = Path(path).suffix.lower()
        if suffix == ".py":
            kind = "python_source"
        elif suffix in (".html", ".json") and path.startswith("res/prompts/"):
            kind = "prompt_or_schema"
        elif path.startswith("res/strategy_record/"):
            kind = "strategy_training_record"
        elif path.startswith("configs/"):
            kind = "configuration"
        else:
            kind = "other"
        rows.append({"commit": commit, "path": path, "kind": kind})
    return rows


def strategy_record_rows(source_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    root = source_root / "res/strategy_record"
    for path in sorted(root.rglob("*.json")):
        rel = path.relative_to(source_root).as_posix()
        payload = json.loads(path.read_text(encoding="utf-8"))
        kind = path.name.removesuffix(".json")
        parts = rel.split("/")
        rows.append({
            "path": rel,
            "asset": parts[3] if len(parts) > 3 else "",
            "strategy_index": parts[4] if len(parts) > 4 else "",
            "variant": parts[6] if len(parts) > 6 else "",
            "record_kind": kind,
            "nonempty": bool(payload),
            "payload_sha256": sha256(path),
            "paper_test_result_artifact": False,
            "paper_result_credit": False,
        })
    if len(rows) != 90:
        raise RuntimeError(f"expected 90 strategy records, got {len(rows)}")
    return rows


def strategy_record_paper_conformance_rows(
    source_root: Path,
    paper_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    appendix = {
        (str(row["item"]), str(row["metric"])): str(row["paper_value"])
        for row in paper_rows
        if str(row["paper_table"]).startswith("Appendix Table 7 panel")
    }
    rows: list[dict[str, Any]] = []
    record_root = source_root / "res/strategy_record/trading"
    for path in sorted(record_root.glob("*/*/exp001/*/best_result.json")):
        rel = path.relative_to(source_root).as_posix()
        parts = rel.split("/")
        asset, strategy_index, variant = parts[3], parts[4], parts[6]
        method = RULE_STRATEGY_METHODS.get(strategy_index)
        if method is None:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for paper_metric, (record_metric, scale) in RECORD_METRICS.items():
            paper_value = appendix[(f"{asset}/{method}", paper_metric)]
            record_value = float(payload[record_metric]) * scale
            decimals = len(paper_value.partition(".")[2])
            display_value = f"{record_value:.{decimals}f}"
            display_match = display_value == paper_value
            rows.append({
                "asset": asset,
                "method": method,
                "strategy_index": strategy_index,
                "variant": variant,
                "record_path": rel,
                "record_sha256": sha256(path),
                "paper_metric": paper_metric,
                "paper_value": paper_value,
                "released_record_value_at_paper_unit": record_value,
                "released_record_display_value": display_value,
                "display_precision_match": display_match,
                "absolute_difference": abs(float(paper_value) - record_value),
                "status": (
                    "display_precision_match_not_independent_regeneration"
                    if display_match
                    else "released_rule_record_does_not_match_appendix_table"
                ),
                "paper_result_credit": False,
            })
    if len(rows) != 288:
        raise RuntimeError(f"expected 288 rule-record/paper comparisons, got {len(rows)}")
    return rows


def source_history_rows(source_root: Path) -> list[dict[str, Any]]:
    commits = git(source_root, "rev-list", "--reverse", "--all").splitlines()
    rows: list[dict[str, Any]] = []
    output_suffixes = {".csv", ".tsv", ".json", ".jsonl", ".parquet", ".pkl", ".pickle", ".npy", ".npz", ".xlsx"}
    output_tokens = ("trajectory", "memory_record", "trading_record", "valid_record", "train_record", "action", "equity", "portfolio", "workdir")
    for commit in commits:
        paths = git(source_root, "ls-tree", "-r", "--name-only", commit).splitlines()
        first_party = [path for path in paths if not path.startswith("tools/echarts-5.4.3/")]
        strategy_records = [path for path in first_party if path.startswith("res/strategy_record/")]
        agent_outputs = [
            path for path in first_party
            if Path(path).suffix.lower() in output_suffixes
            and not path.startswith("res/strategy_record/")
            and any(token in path.lower() for token in output_tokens)
        ]
        metadata = git(source_root, "show", "-s", "--format=%aI%x00%s", commit).strip().split("\x00", 1)
        rows.append({
            "commit": commit,
            "commit_date": metadata[0],
            "subject": metadata[1],
            "tracked_files": len(paths),
            "first_party_files_excluding_vendored_echarts": len(first_party),
            "vendored_echarts_files": len(paths) - len(first_party),
            "strategy_record_files": len(strategy_records),
            "agent_output_paths": len(agent_outputs),
            "agent_output_path_list": ";".join(agent_outputs),
            "paper_result_credit": False,
        })
    if len(rows) != 7 or any(row["agent_output_paths"] for row in rows):
        raise RuntimeError("FinAgent reachable-history output boundary changed")
    return rows


def public_source_history(
    source_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    discovery_root = source_root / "release-discovery"
    for name, expected in PUBLIC_DISCOVERY_SHA256.items():
        if sha256(discovery_root / name) != expected:
            raise RuntimeError(f"FinAgent public discovery drift: {name}")
    branches = json.loads((discovery_root / "branches.json").read_text(encoding="utf-8"))
    tags = json.loads((discovery_root / "tags.json").read_text(encoding="utf-8"))
    releases = json.loads((discovery_root / "releases.json").read_text(encoding="utf-8"))
    branch_pairs = [(row["name"], row["commit"]["sha"]) for row in branches]
    if branch_pairs != [("main", SOURCE_CURRENT_COMMIT)] or tags or releases:
        raise RuntimeError("FinAgent public ref discovery changed")
    if str(git(source_root, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise RuntimeError("FinAgent source checkout is shallow")

    commits_raw = str(git(source_root, "rev-list", "--reverse", "--all"))
    commits = commits_raw.splitlines()
    if len(commits) != PUBLIC_HISTORY_COMMIT_COUNT:
        raise RuntimeError("FinAgent public commit census changed")
    if sha256_bytes(commits_raw.encode("utf-8")) != PUBLIC_HISTORY_COMMIT_SHA256:
        raise RuntimeError("FinAgent public commit sequence changed")
    path_lines = str(git(source_root, "log", "--all", "--pretty=format:", "--name-only")).splitlines()
    historical_paths = sorted({line for line in path_lines if line})
    path_payload = ("\n".join(historical_paths) + "\n").encode("utf-8")
    if len(historical_paths) != PUBLIC_HISTORY_PATH_COUNT:
        raise RuntimeError("FinAgent public historical path census changed")
    if sha256_bytes(path_payload) != PUBLIC_HISTORY_PATH_SHA256:
        raise RuntimeError("FinAgent public historical path inventory changed")

    object_lines = str(git(source_root, "rev-list", "--objects", "--all")).splitlines()
    object_ids = [line.split(" ", 1)[0] for line in object_lines]
    object_proc = subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
        input="\n".join(object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    )
    object_counts = dict(Counter(object_proc.stdout.splitlines()))
    if object_counts != PUBLIC_HISTORY_OBJECT_COUNTS:
        raise RuntimeError("FinAgent reachable-object census changed")
    fsck = subprocess.run(
        ["git", "-C", str(source_root), "fsck", "--full", "--no-reflogs", "--unreachable"],
        check=True,
        capture_output=True,
        text=True,
    )
    if fsck.stdout.strip():
        raise RuntimeError("FinAgent has unreachable objects requiring review")

    output_suffixes = {
        ".csv", ".json", ".jsonl", ".npy", ".npz", ".parquet", ".pickle",
        ".pkl", ".tsv", ".xlsx",
    }
    output_tokens = (
        "action", "agent_output", "equity", "memory_record", "portfolio",
        "trading_record", "trajectory", "valid_record", "workdir",
    )
    path_blobs: dict[str, set[str]] = {path: set() for path in historical_paths}
    path_first: dict[str, tuple[str, str]] = {}
    path_last: dict[str, tuple[str, str]] = {}
    for commit in commits:
        committed_at = str(git(source_root, "show", "-s", "--format=%cI", commit)).strip()
        for line in str(git(source_root, "ls-tree", "-r", commit)).splitlines():
            object_meta, path = line.split("\t", 1)
            _mode, object_type, object_id = object_meta.split()
            if object_type != "blob":
                continue
            path_blobs[path].add(object_id)
            path_first.setdefault(path, (commit, committed_at))
            path_last[path] = (commit, committed_at)

    rows = []
    for path in historical_paths:
        suffix = Path(path).suffix.lower()
        strategy_record = path.startswith("res/strategy_record/")
        native_agent_output = (
            suffix in output_suffixes
            and not strategy_record
            and not path.startswith("tools/echarts-5.4.3/")
            and any(token in path.lower() for token in output_tokens)
        )
        if path.startswith("tools/echarts-5.4.3/"):
            classification = "vendored_echarts_dependency"
        elif strategy_record:
            classification = "opaque_rule_strategy_training_or_parameter_record_not_agent_output"
        elif path.startswith("res/prompts/"):
            classification = "prompt_or_schema"
        elif path.startswith("configs/"):
            classification = "experiment_configuration_without_native_results"
        elif suffix == ".py":
            classification = "python_source"
        else:
            classification = "source_documentation_or_nonresult_asset"
        rows.append(
            {
                "path": path,
                "extension": suffix,
                "historical_blob_versions": len(path_blobs[path]),
                "first_reachable_commit": path_first[path][0],
                "first_reachable_committed_at": path_first[path][1],
                "last_reachable_commit": path_last[path][0],
                "last_reachable_committed_at": path_last[path][1],
                "strategy_record_path": strategy_record,
                "native_agent_result_path": native_agent_output,
                "classification": classification,
                "paper_result_credit": False,
            }
        )
    native_outputs = [row for row in rows if row["native_agent_result_path"]]
    strategy_paths = [row for row in rows if row["strategy_record_path"]]
    if native_outputs or len(strategy_paths) != 90:
        raise RuntimeError("FinAgent historical result-artifact boundary changed")
    extension_counts = Counter(row["extension"] or "[none]" for row in rows)
    summary = {
        "discovered_public_branches": [{"name": name, "head": commit} for name, commit in branch_pairs],
        "discovered_public_tags": [],
        "discovered_public_releases": [],
        "reachable_commits": len(commits),
        "unique_historical_paths": len(historical_paths),
        "historical_path_extension_counts": dict(sorted(extension_counts.items())),
        "reachable_object_counts": object_counts,
        "unreachable_objects": 0,
        "historical_strategy_record_paths": len(strategy_paths),
        "native_agent_result_paths": 0,
        "exact_paper_result_table_or_figure_paths": 0,
        "independently_regenerated_paper_results": 0,
        "paper_result_credit": False,
    }
    return rows, summary


def public_fork_census(
    census_root: Path, branch_ref_snapshot: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Audit every unique head in the dated accessible public-fork census."""
    if str(git(census_root, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise RuntimeError("FinAgent public-fork census is shallow")
    ref_lines = str(git(
        census_root, "for-each-ref", "refs/fork-census",
        "--format=%(refname)%09%(objectname)",
    )).splitlines()
    if (
        len(ref_lines) != PUBLIC_FORK_REPRESENTATIVE_REF_COUNT
        or sha256_lines(ref_lines) != PUBLIC_FORK_REPRESENTATIVE_REF_SHA256
    ):
        raise RuntimeError("FinAgent representative public-fork refs changed")
    refs = [line.split("\t", 1) for line in ref_lines]
    unique_heads = sorted({head for _, head in refs})
    if (
        len(unique_heads) != PUBLIC_FORK_REPRESENTATIVE_REF_COUNT
        or sha256_lines(unique_heads) != PUBLIC_FORK_UNIQUE_HEAD_SHA256
    ):
        raise RuntimeError("FinAgent public-fork unique heads changed")

    if sha256(branch_ref_snapshot) != PUBLIC_FORK_SNAPSHOT_SHA256:
        raise RuntimeError("FinAgent public-fork branch-ref snapshot bytes changed")
    with branch_ref_snapshot.open(newline="", encoding="utf-8") as handle:
        branch_rows = list(csv.DictReader(handle))
    expected_columns = {
        "repository", "branch", "head_commit", "repository_created_at",
        "repository_pushed_at", "head_committed_at", "head_author_login",
        "head_author_name", "head_author_email", "head_subject",
    }
    if not branch_rows or set(branch_rows[0]) != expected_columns:
        raise RuntimeError("FinAgent public-fork branch-ref schema changed")
    branch_rows.sort(key=lambda row: (
        row["repository"].lower(), row["branch"].lower(), row["head_commit"],
    ))
    canonical_branch_refs = [
        f'{row["repository"]}\t{row["branch"]}\t{row["head_commit"]}'
        for row in branch_rows
    ]
    if (
        len(branch_rows) != PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT
        or len({row["repository"] for row in branch_rows})
        != PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT
        or len({(row["repository"], row["branch"]) for row in branch_rows})
        != len(branch_rows)
        or sha256_lines(canonical_branch_refs) != PUBLIC_FORK_GRAPHQL_REF_SHA256
        or {row["head_commit"] for row in branch_rows} != set(unique_heads)
    ):
        raise RuntimeError("FinAgent complete public-fork branch-ref snapshot changed")

    base_objects = {
        line.split(" ", 1)[0]
        for line in str(git(census_root, "rev-list", "--objects", SOURCE_CURRENT_COMMIT)).splitlines()
    }
    output_suffixes = {
        ".csv", ".json", ".jsonl", ".npy", ".npz", ".parquet",
        ".pickle", ".pkl", ".tsv", ".xlsx",
    }
    output_tokens = (
        "action", "agent_output", "equity", "memory_record", "portfolio",
        "trading_record", "trajectory", "valid_record", "workdir",
    )
    rows: list[dict[str, Any]] = []
    divergent_surface: list[str] = []
    all_extra_commits: set[str] = set()
    all_extra_paths: set[str] = set()
    extra_author_emails: set[str] = set()
    extra_author_names: set[str] = set()
    extra_commits_by_head: dict[str, list[str]] = {}
    new_final_blob_lines: list[str] = []
    new_final_blobs: set[str] = set()
    new_final_paths: set[str] = set()
    all_native_output_paths: set[str] = set()
    for ref, head in refs:
        extra_commits = sorted(str(git(
            census_root, "rev-list", head, "--not", SOURCE_CURRENT_COMMIT,
        )).splitlines())
        extra_commits_by_head[head] = extra_commits
        changed_paths: set[str] = set()
        extra_dates: list[str] = []
        for commit in extra_commits:
            changed_paths.update(
                path for path in str(git(
                    census_root, "diff-tree", "--root", "--no-commit-id",
                    "--name-only", "-r", commit,
                )).splitlines() if path
            )
            metadata = str(git(
                census_root, "show", "-s", "--format=%aI%x00%an%x00%ae", commit,
            )).rstrip("\n").split("\0")
            if len(metadata) != 3:
                raise RuntimeError(f"Malformed FinAgent fork commit metadata: {commit}")
            extra_dates.append(metadata[0])
            extra_author_names.add(metadata[1])
            extra_author_emails.add(metadata[2])
        ordered_paths = sorted(changed_paths)
        if extra_commits:
            expected = DIVERGENT_FORK_FINDINGS.get(head)
            if expected is None:
                raise RuntimeError(f"Unreviewed divergent FinAgent fork head: {head}")
            if (len(extra_commits), len(ordered_paths)) != (
                expected["commits"], expected["paths"],
            ):
                raise RuntimeError(f"FinAgent fork surface changed for {head}")
            if any(value[:10] <= ARXIV_V3_DATE for value in extra_dates):
                raise RuntimeError(f"Expected only post-v3 divergent commits for {head}")
            divergent_surface.append(
                f"{head}\t{';'.join(extra_commits)}\t{';'.join(ordered_paths)}"
            )
            all_extra_commits.update(extra_commits)
            all_extra_paths.update(ordered_paths)
            classification = str(expected["classification"])
        else:
            classification = "official_public_history_reachable"

        head_new_paths: list[str] = []
        head_native_outputs: list[str] = []
        for line in str(git(census_root, "ls-tree", "-rl", head)).splitlines():
            metadata, path = line.split("\t", 1)
            _mode, object_type, object_id, size = metadata.split()
            if object_type != "blob" or object_id in base_objects:
                continue
            new_final_blob_lines.append(f"{head}\t{path}\t{object_id}\t{size}")
            new_final_blobs.add(object_id)
            new_final_paths.add(path)
            head_new_paths.append(path)
            suffix = Path(path).suffix.lower()
            if (
                suffix in output_suffixes
                and not path.startswith("res/strategy_record/")
                and not path.startswith("tools/echarts-5.4.3/")
                and any(token in path.lower() for token in output_tokens)
            ):
                head_native_outputs.append(path)
                all_native_output_paths.add(path)
        head_metadata = str(git(
            census_root, "show", "-s", "--format=%cI%x00%an%x00%ae%x00%s", head,
        )).rstrip("\n").split("\0", 3)
        matching_branch_rows = [row for row in branch_rows if row["head_commit"] == head]
        rows.append({
            "representative_ref": ref,
            "head_commit": head,
            "head_date": head_metadata[0],
            "head_author_name": head_metadata[1],
            "head_author_email": head_metadata[2],
            "head_subject": head_metadata[3],
            "branch_ref_count": len(matching_branch_rows),
            "repository_count": len({row["repository"] for row in matching_branch_rows}),
            "repositories": ";".join(sorted({row["repository"] for row in matching_branch_rows})),
            "extra_commit_count_beyond_official_head": len(extra_commits),
            "extra_changed_path_count": len(ordered_paths),
            "new_final_blob_path_count": len(head_new_paths),
            "new_final_native_agent_output_path_count": len(head_native_outputs),
            "new_final_native_agent_output_paths": ";".join(head_native_outputs),
            "official_source_author_identity_match_in_extra_commits": False,
            "classification": classification,
            "paper_result_credit": False,
        })

    base_reachable = [row for row in rows if not row["extra_commit_count_beyond_official_head"]]
    if len(base_reachable) != PUBLIC_FORK_BASE_REACHABLE_HEAD_COUNT:
        raise RuntimeError("FinAgent base-reachable fork-head count changed")
    if len(rows) - len(base_reachable) != PUBLIC_FORK_DIVERGENT_HEAD_COUNT:
        raise RuntimeError("FinAgent divergent fork-head count changed")
    if set(DIVERGENT_FORK_FINDINGS) != {
        head for head, commits in extra_commits_by_head.items() if commits
    }:
        raise RuntimeError("FinAgent reviewed divergent-head set changed")
    if sha256_lines(divergent_surface) != PUBLIC_FORK_DIVERGENT_SURFACE_SHA256:
        raise RuntimeError("FinAgent divergent fork commit/path surface changed")
    if (
        len(all_extra_commits) != PUBLIC_FORK_DIVERGENT_COMMIT_COUNT
        or sha256_lines(sorted(all_extra_commits)) != PUBLIC_FORK_DIVERGENT_COMMIT_SHA256
        or len(all_extra_paths) != PUBLIC_FORK_DIVERGENT_PATH_COUNT
        or sha256_lines(sorted(all_extra_paths)) != PUBLIC_FORK_DIVERGENT_PATH_SHA256
    ):
        raise RuntimeError("FinAgent aggregate divergent fork surface changed")
    if (
        len(new_final_blob_lines) != PUBLIC_FORK_NEW_FINAL_BLOB_REF_COUNT
        or sha256_lines(new_final_blob_lines) != PUBLIC_FORK_NEW_FINAL_BLOB_REF_SHA256
        or len(new_final_blobs) != PUBLIC_FORK_NEW_FINAL_UNIQUE_BLOB_COUNT
        or sha256_lines(sorted(new_final_blobs)) != PUBLIC_FORK_NEW_FINAL_UNIQUE_BLOB_SHA256
        or len(new_final_paths) != PUBLIC_FORK_NEW_FINAL_PATH_COUNT
        or sha256_lines(sorted(new_final_paths)) != PUBLIC_FORK_NEW_FINAL_PATH_SHA256
    ):
        raise RuntimeError("FinAgent divergent fork final-blob surface changed")
    if extra_author_emails != EXPECTED_DIVERGENT_AUTHOR_EMAILS:
        raise RuntimeError(f"FinAgent divergent fork identities changed: {extra_author_emails}")
    if extra_author_emails & OFFICIAL_SOURCE_AUTHOR_EMAILS:
        raise RuntimeError("FinAgent divergent commits match an official source author email")
    if extra_author_names & OFFICIAL_SOURCE_AUTHOR_NAMES:
        raise RuntimeError("FinAgent divergent commits match an official source author name")
    if all_native_output_paths:
        raise RuntimeError(f"FinAgent fork native output paths require review: {all_native_output_paths}")

    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": PUBLIC_FORK_REST_COUNT,
        "graphql_accessible_forks": PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT,
        "rest_minus_accessible_fork_gap": (
            PUBLIC_FORK_REST_COUNT - PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT
        ),
        "graphql_accessible_branch_refs": PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT,
        "graphql_accessible_branch_ref_census_sha256": PUBLIC_FORK_GRAPHQL_REF_SHA256,
        "graphql_accessible_branch_ref_snapshot_file_sha256": sha256(branch_ref_snapshot),
        "representative_unique_head_refs": len(rows),
        "representative_ref_census_sha256": sha256_lines(ref_lines),
        "unique_heads": len(unique_heads),
        "unique_head_sha256": sha256_lines(unique_heads),
        "heads_reachable_from_official_history": len(base_reachable),
        "divergent_heads_reviewed": len(rows) - len(base_reachable),
        "divergent_extra_commits_reviewed": len(all_extra_commits),
        "divergent_changed_paths_reviewed": len(all_extra_paths),
        "divergent_heads_matching_official_source_author_identity": 0,
        "new_final_blob_references_reviewed": len(new_final_blob_lines),
        "new_final_unique_blobs_reviewed": len(new_final_blobs),
        "new_final_paths_reviewed": len(new_final_paths),
        "native_agent_result_paths_discovered": len(all_native_output_paths),
        "exact_paper_result_table_or_figure_paths_discovered": 0,
        "paper_result_credit": False,
    }
    return rows, summary


def config_conformance_rows(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    config_paths = sorted((source_root / "configs/exp").rglob("*.py"))
    config_paths = [path for path in config_paths if "__pycache__" not in path.parts]
    for path in config_paths:
        text = path.read_text(encoding="utf-8")
        checks = {
            "asset": any(f'selected_asset = "{asset}"' in text for asset in ASSETS),
            "train_start": 'train_start_date = "2022-06-01"' in text,
            "train_end": 'train_end_date = "2023-06-01"' in text,
            "valid_start": 'valid_start_date = "2023-06-01"' in text,
            "valid_end": 'valid_end_date = "2024-01-01"' in text,
            "horizons_1_7_14": all(f"{term}_term_{direction}_date_range = {days}" in text
                                   for term, days in (("short", 1), ("medium", 7), ("long", 14))
                                   for direction in ("past", "next")),
            "top_k_5": "top_k = 5" in text,
            "market_model": 'model = "gpt-4-1106-preview"' in text,
            "reflection_model": 'model = "gpt-4-vision-preview"' in text,
        }
        schedule_fields = (
            "asset", "train_start", "train_end", "valid_start", "valid_end",
            "horizons_1_7_14", "top_k_5",
        )
        rows.append({
            "path": path.relative_to(source_root).as_posix(),
            **checks,
            "all_reported_core_fields_match": all(checks[key] for key in schedule_fields),
            "valid_environment_declared_mode": "train" if 'valid_environment = dict' in text else "missing",
        })
    if len(rows) != 42:
        raise RuntimeError(f"expected 42 experiment configs, got {len(rows)}")
    return rows


def source_reference_diagnostics(source_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((source_root / "configs").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for reference in re.findall(r'["\']((?:configs|res)/[^"\']+)["\']', text):
            target = source_root / reference
            if not target.exists():
                rows.append({
                    "config": path.relative_to(source_root).as_posix(),
                    "reference": reference,
                    "issue": (
                        "nonexistent_stock_list_directory" if "_stock_list_" in reference
                        else "missing_training_prompt_template"
                    ),
                })
    counts = Counter(row["issue"] for row in rows)
    if counts != {"nonexistent_stock_list_directory": 21, "missing_training_prompt_template": 60}:
        raise RuntimeError(f"source missing-reference census changed: {counts}")
    return rows


def processor_route_rows(source_root: Path) -> list[dict[str, Any]]:
    downloader_tags = set()
    for path in (source_root / "configs/downloader").rglob("*.py"):
        match = re.search(r'^tag\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            downloader_tags.add(match.group(1))
    rows = []
    for path in sorted((source_root / "configs/processor").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for route in re.findall(r'"path"\s*:\s*"workdir/([^"]+)"', text):
            rows.append({
                "processor_config": path.relative_to(source_root).as_posix(),
                "input_tag": route,
                "matching_downloader_tag": route in downloader_tags,
            })
    if sum(not row["matching_downloader_tag"] for row in rows) != 3:
        raise RuntimeError("processor/downloader route mismatch census changed")
    return rows


def static_python_rows(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(source_root.rglob("*.py")):
        if ".git" in path.parts:
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            status = "compiled"
            error = ""
        except Exception as exc:  # pragma: no cover - should fail the audit below
            status = "syntax_error"
            error = f"{type(exc).__name__}: {exc}"
        rows.append({"path": path.relative_to(source_root).as_posix(), "status": status, "error": error})
    if len(rows) != 142 or any(row["status"] != "compiled" for row in rows):
        raise RuntimeError("FinAgent static Python census/compilation changed")
    return rows


def metric_diagnostic_rows(source_root: Path) -> list[dict[str, Any]]:
    import numpy as np

    module_path = source_root / "finagent/metrics/metrics.py"
    spec = importlib.util.spec_from_file_location("released_finagent_metrics", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    returns = np.asarray([0.01, -0.02, 0.03, -0.01, 0.005], dtype=float)
    mean = float(np.mean(returns))
    std = float(np.std(returns))
    downside = float(np.std(returns[returns < 0]))
    mdd = float(module.MDD(returns))
    values = {
        "SR": (mean / std, float(module.SR(returns)), "source multiplies by sqrt(number_of_observations)"),
        "CR": (mean / mdd, float(module.CR(returns, mdd)), "source multiplies daily mean by 252"),
        "SOR": (mean / downside, float(module.SOR(returns, downside)), "source multiplies daily mean by 252"),
    }
    return [{
        "metric": metric,
        "paper_formula_value_on_probe": paper_value,
        "released_source_value_on_probe": source_value,
        "matches_paper_formula": abs(paper_value - source_value) < 1e-12,
        "diagnosis": diagnosis,
        "paper_result_credit": False,
    } for metric, (paper_value, source_value, diagnosis) in values.items()]


def mechanism_rows() -> list[dict[str, Any]]:
    specs = (
        ("provenance", "lead_author_homepage_links_repository", "source_verified", True),
        ("architecture", "multimodal_market_low_high_tool_decision_modules", "source_verified", True),
        ("architecture", "three_level_memory_and_diverse_retrieval", "source_verified", True),
        ("configuration", "six_reported_assets", "source_verified", True),
        ("configuration", "reported_train_validation_splits", "source_verified", True),
        ("configuration", "one_seven_fourteen_day_horizons", "source_verified", True),
        ("configuration", "top_k_five", "source_verified", True),
        ("configuration", "reported_openai_model_aliases", "source_verified_but_aliases_now_retired", True),
        ("prompts", "train_and_validation_prompt_families", "source_verified_with_missing_only_strategy_train_paths", True),
        ("ablations", "five_main_agent_config_families", "source_verified", True),
        ("baselines", "four_rule_strategy_implementations", "source_verified", True),
        ("portfolio", "stock_and_crypto_transaction_cost_settings", "source_verified_not_paper_disclosed", True),
        ("portfolio", "stock_and_crypto_initial_capital", "source_verified_not_paper_disclosed", True),
        ("validation", "chart_uses_only_information_available_by_decision_time", "conflict_future_14_days_rendered", False),
        ("portfolio", "paper_short_position_explanation", "conflict_release_is_long_only", False),
        ("tools", "optimized_strategy_parameters_drive_validation_signal", "conflict_signal_overwritten_by_default_parameters", False),
        ("baselines", "optuna_baseline_tuning", "missing_from_source", False),
        ("baselines", "lgbm_lstm_transformer_dqn_sac_ppo_training", "missing_from_source", False),
        ("metrics", "sharpe_formula", "conflict_source_adds_sqrt_n", False),
        ("metrics", "calmar_formula", "conflict_source_adds_252", False),
        ("metrics", "sortino_formula", "conflict_source_adds_252", False),
        ("data", "exact_immutable_dataset_snapshot", "not_released", False),
        ("data", "crypto_calendar", "conflict_eth_is_filtered_to_nyse_days", False),
        ("data", "download_and_processor_asset_list_routes", "broken_21_references_including_18_downloaders", False),
        ("data", "processor_downloader_routes", "broken_3_tag_mismatches", False),
        ("artifacts", "agent_memories_and_trajectories", "not_released", False),
        ("artifacts", "model_outputs_actions_and_equity_paths", "not_released", False),
        ("artifacts", "paper_result_tables_as_native_outputs", "not_released", False),
        ("reproducibility", "exact_dependency_environment", "not_released_at_paper_commit", False),
        ("reproducibility", "stochastic_llm_trials_and_variance", "not_reported_or_released", False),
        ("execution", "same_day_information_and_close_execution_timing", "under_specified", False),
    )
    return [{
        "area": area,
        "claim": claim,
        "status": status,
        "released_source_conformance_credit": credit,
        "paper_result_credit": False,
    } for area, claim, status, credit in specs]


def internal_check_rows() -> list[dict[str, Any]]:
    return [
        {"check": "baseline_count", "status": "internal_conflict", "detail": "prose says 9 baselines; Table 4 contains 12 comparators and the abstract says 12"},
        {"check": "figure4_vs_table4_methods", "status": "internal_conflict", "detail": "Figure 4 omits LGBM/LSTM/Transformer and adds SO&BB relative to Table 4"},
        {"check": "tsla_sr_improvement", "status": "internal_conflict", "detail": "prose/main figure claim 118%; Table 4 says 93.27% and Appendix Table 7 says 92.3217%"},
        {"check": "tsla_arr_improvement", "status": "rounding_consistent", "detail": "prose 84%; Table 4 84.39%; Appendix Table 7 84.4052%"},
        {"check": "table4_caption", "status": "caption_scope_conflict", "detail": "caption says six metrics while the active main table displays ARR, SR, and MDD only"},
        {"check": "paper_source_compile", "status": "reproduced_document", "detail": "arXiv v3 source compiles to 43 pages after two pdflatex passes"},
        {"check": "strategy_record_scope", "status": "not_paper_results", "detail": "90 JSON files are opaque rule-strategy training/default parameter records; all 288 comparable high-precision Appendix Table 7 cells mismatch"},
        {"check": "paper_vs_source_metrics", "status": "implementation_conflict", "detail": "released SR, CR, and SOR scale differently from the equations in the paper"},
    ]


def data_artifact_rows(source_root: Path) -> list[dict[str, Any]]:
    data_suffixes = {".csv", ".parquet", ".pkl", ".pickle", ".feather"}
    checkpoint_suffixes = {".pt", ".pth", ".ckpt", ".bin", ".safetensors"}
    output_suffixes = data_suffixes | {".json", ".jsonl"}
    files = [
        path for path in source_root.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    ]
    found_by_kind = {
        "market_dataset": [path for path in files if path.suffix.lower() in data_suffixes],
        "model_checkpoint": [path for path in files if path.suffix.lower() in checkpoint_suffixes],
        "agent_output": [
            path for path in files
            if path.suffix.lower() in output_suffixes
            and any(token in path.name.lower() for token in ("trajectory", "memory", "action", "equity"))
        ],
    }
    rows = []
    for kind, paths in found_by_kind.items():
        found = sorted({path.relative_to(source_root).as_posix() for path in paths})
        rows.append({
            "artifact_kind": kind,
            "released_count": len(found),
            "released_paths": ";".join(found),
            "sufficient_for_paper_result_reproduction": False,
        })
    return rows


def validate_primary_inputs(source_root: Path, paper_root: Path) -> None:
    expected_files = {
        "paper_v3.pdf": ARXIV_V3_PDF_SHA256,
        "source_v3.tar": ARXIV_V3_SOURCE_SHA256,
        "KDD24_FinAgent.pdf": KDD_PDF_SHA256,
    }
    for name, expected in expected_files.items():
        path = paper_root / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"primary paper input mismatch: {name}")
    if git(source_root, "rev-parse", "HEAD").strip() != SOURCE_CURRENT_COMMIT:
        raise ValueError("released source HEAD mismatch")
    if git(source_root, "rev-parse", f"{SOURCE_PAPER_COMMIT}^{{tree}}").strip() != SOURCE_PAPER_TREE:
        raise ValueError("paper-era source tree mismatch")
    if git(source_root, "rev-parse", f"{SOURCE_CURRENT_COMMIT}^{{tree}}").strip() != SOURCE_CURRENT_TREE:
        raise ValueError("current source tree mismatch")
    if git_archive_sha256(source_root, SOURCE_PAPER_COMMIT) != SOURCE_PAPER_ARCHIVE_SHA256:
        raise ValueError("paper-era source archive mismatch")
    if git_archive_sha256(source_root, SOURCE_CURRENT_COMMIT) != SOURCE_CURRENT_ARCHIVE_SHA256:
        raise ValueError("current source archive mismatch")
    changed = git(source_root, "diff", "--name-only", SOURCE_PAPER_COMMIT, SOURCE_CURRENT_COMMIT).splitlines()
    if changed != ["requirements.txt"]:
        raise ValueError(f"unexpected post-paper source changes: {changed}")


def compile_paper_source(paper_root: Path, latex_command: str) -> dict[str, Any]:
    if not latex_command or shutil.which(latex_command) is None:
        return {
            "attempted": False, "reason": "latex_command_unavailable",
            "paper_result_credit": False,
        }
    with tempfile.TemporaryDirectory(prefix="finagent-paper-") as temp:
        temp_root = Path(temp)
        with tarfile.open(paper_root / "source_v3.tar") as archive:
            archive.extractall(temp_root)
        passes = []
        for _ in range(2):
            proc = subprocess.run(
                [latex_command, "-interaction=nonstopmode", "main.tex"],
                cwd=temp_root, capture_output=True, text=True, timeout=180,
            )
            passes.append({"exit_code": proc.returncode, "log_tail": proc.stdout[-2000:]})
            if proc.returncode != 0:
                break
        pdf = temp_root / "main.pdf"
        page_count = None
        if pdf.is_file() and shutil.which("pdfinfo"):
            info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
            match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
            page_count = int(match.group(1)) if match else None
        return {
            "attempted": True,
            "passes": passes,
            "exit_code": passes[-1]["exit_code"],
            "compiled_pdf_sha256": sha256(pdf) if pdf.is_file() else None,
            "compiled_pages": page_count,
            "matches_arxiv_page_count": page_count == 43,
            "paper_result_credit": False,
        }


def _marked_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith("@@@"):
            return json.loads(line.removeprefix("@@@"))
    raise RuntimeError(f"Subprocess did not emit a marked JSON summary:\n{stdout}")


def dependency_environment_execution(
    source_root: Path, paper_python: Path
) -> tuple[dict[str, Any], str]:
    if not paper_python.is_file():
        raise FileNotFoundError(paper_python)
    if sha256(source_root / "requirements.txt") != SOURCE_REQUIREMENTS_SHA256:
        raise RuntimeError("FinAgent author requirements changed")
    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)
    pip_check = subprocess.run(
        [str(paper_python), "-m", "pip", "check"],
        check=True,
        capture_output=True,
        text=True,
        env=clean_env,
    )
    freeze = subprocess.run(
        [str(paper_python), "-m", "pip", "freeze", "--all"],
        check=True,
        capture_output=True,
        text=True,
        env=clean_env,
    ).stdout
    freeze_sha256 = hashlib.sha256(freeze.encode()).hexdigest()
    if freeze_sha256 != PAPER_ENV_FREEZE_SHA256:
        raise RuntimeError(
            f"FinAgent environment changed: {freeze_sha256} != "
            f"{PAPER_ENV_FREEZE_SHA256}"
        )

    entrypoint_program = r"""
import runpy, sys
sys.path.insert(0, '.')
sys.argv = ['tools/main.py', '--help']
runpy.run_path('tools/main.py', run_name='__main__')
"""
    help_outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(paper_python), "-c", entrypoint_program],
            cwd=source_root,
            env=clean_env,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if "Main" not in completed.stdout or "--if_train" not in completed.stdout:
            raise RuntimeError(f"FinAgent entrypoint help changed:\n{completed.stdout}")
        help_outputs.append(completed.stdout)
    if help_outputs[0] != help_outputs[1]:
        raise RuntimeError("FinAgent entrypoint help is nondeterministic")

    import_program = r"""
import aiohttp, httpx, importlib, importlib.metadata, json, requests, sys
from pathlib import Path
sys.path.insert(0, '.')
network_attempts = []
def block_httpx(self, request, *args, **kwargs):
    network_attempts.append(f'httpx:{request.method}:{request.url}')
    raise RuntimeError('network disabled during FinAgent paper audit')
async def block_httpx_async(self, request, *args, **kwargs):
    network_attempts.append(f'httpx-async:{request.method}:{request.url}')
    raise RuntimeError('network disabled during FinAgent paper audit')
def block_requests(self, request, *args, **kwargs):
    network_attempts.append(f'requests:{request.method}:{request.url}')
    raise RuntimeError('network disabled during FinAgent paper audit')
async def block_aiohttp(self, method, url, *args, **kwargs):
    network_attempts.append(f'aiohttp:{method}:{url}')
    raise RuntimeError('network disabled during FinAgent paper audit')
httpx.Client.send = block_httpx
httpx.AsyncClient.send = block_httpx_async
requests.sessions.Session.send = block_requests
aiohttp.ClientSession._request = block_aiohttp

modules = []
for file in sorted(Path('finagent').rglob('*.py')):
    parts = list(file.with_suffix('').parts)
    if parts[-1] == '__init__':
        parts = parts[:-1]
    name = '.'.join(parts)
    if name and name not in modules:
        modules.append(name)
imported = []
failures = []
for name in modules:
    try:
        importlib.import_module(name)
        imported.append(name)
    except Exception as exc:
        failures.append({
            'module': name,
            'exception_type': type(exc).__name__,
            'message': str(exc),
        })
distribution = importlib.metadata.distribution('pandas-ta')
direct_url = json.loads((Path(distribution._path) / 'direct_url.json').read_text())
packages = {
    name: importlib.metadata.version(name)
    for name in (
        'gym', 'langchain', 'mmengine', 'numpy', 'openai', 'pandas',
        'pandas-ta', 'scikit-learn', 'scikit-learn-extra', 'yfinance'
    )
}
print('@@@' + json.dumps({
    'selected_core_modules': len(modules),
    'imported_core_modules': len(imported),
    'imported_module_names': imported,
    'failures': failures,
    'network_attempts': network_attempts,
    'pandas_ta_direct_url': direct_url,
    'resolved_packages': packages,
}, sort_keys=True))
"""
    import_outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(paper_python), "-c", import_program],
            cwd=source_root,
            env=clean_env,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        import_outputs.append(_marked_json(completed.stdout))
    if import_outputs[0] != import_outputs[1]:
        raise RuntimeError("FinAgent core import inventory is nondeterministic")
    imports = import_outputs[0]
    if (
        imports["selected_core_modules"] != 65
        or imports["imported_core_modules"] != 65
        or imports["failures"]
        or imports["network_attempts"]
        or imports["resolved_packages"]["pandas-ta"] != "0.3.14b0"
        or imports["pandas_ta_direct_url"].get("vcs_info", {}).get("commit_id")
        != PANDAS_TA_MIRROR_COMMIT
    ):
        raise RuntimeError(f"FinAgent dependency/import boundary changed: {imports}")

    component_program = r"""
import json, types
import numpy as np
import pandas as pd
from finagent.environment.trading import EnvironmentTrading
from finagent.metrics.metrics import ARR, VOL, DD, MDD, SR, CR, SOR

dates = pd.date_range('2024-01-01', periods=8, freq='D')
prices = pd.DataFrame({
    'timestamp': dates,
    'adj_close': [100.0, 101.0, 103.0, 102.0, 106.0, 104.0, 108.0, 110.0],
})
news = pd.DataFrame({'timestamp': dates, 'text': [f'n{i}' for i in range(8)]})
dataset = types.SimpleNamespace(
    prices={'AAPL': prices}, news={'AAPL': news}, guidances=None,
    sentiments=None, economics=None,
)
environment = EnvironmentTrading(
    dataset=dataset, selected_asset='AAPL', start_date='2024-01-03',
    end_date='2024-01-07', look_back_days=1, look_forward_days=2,
    initial_amount=1000.0, transaction_cost_pct=0.001,
)
state, info = environment.reset()
rows = [{
    'phase': 'reset', 'info': info, 'state_rows': len(state['price']),
    'state_min': str(state['price'].index.min().date()),
    'state_max': str(state['price'].index.max().date()),
}]
for action in (1, 0, -1):
    state, reward, done, truncated, info = environment.step(action)
    rows.append({
        'action': action, 'reward': reward, 'done': done,
        'truncated': truncated, 'info': info,
        'state_max': str(state['price'].index.max().date()),
    })
returns = np.array([0.01, -0.02, 0.03, -0.01, 0.005], dtype=float)
mdd = MDD(returns)
downside = DD(returns)
metrics = {
    'ARR': ARR(returns), 'VOL': VOL(returns), 'DD': downside,
    'MDD': mdd, 'SR': SR(returns), 'CR': CR(returns, mdd),
    'SOR': SOR(returns, downside),
}
print('@@@' + json.dumps({'environment': rows, 'metrics': metrics}, sort_keys=True))
"""
    component_outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(paper_python), "-c", component_program],
            cwd=source_root,
            env=clean_env,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        component_outputs.append(_marked_json(completed.stdout))
    if component_outputs[0] != component_outputs[1]:
        raise RuntimeError("FinAgent native component execution is nondeterministic")
    component = component_outputs[0]
    if (
        component["environment"][0]["state_max"] != "2024-01-05"
        or component["environment"][0]["info"]["date"] != "2024-01-03"
        or component["environment"][1]["info"]["position"] != 9
        or component["environment"][3]["info"]["position"] != 0
        or not abs(component["metrics"]["MDD"] - 0.02) < 1e-12
    ):
        raise RuntimeError(f"FinAgent native component boundary changed: {component}")

    return (
        {
            "dependency_environment_reproduced": True,
            "exact_historical_dependency_versions_recovered": False,
            "dependency_release_cutoff_utc": SOURCE_CURRENT_DATE_UTC,
            "author_requirements_commit": SOURCE_CURRENT_COMMIT,
            "author_requirements_sha256": SOURCE_REQUIREMENTS_SHA256,
            "author_requirements_only_postpaper_change": True,
            "python": str(paper_python),
            "python_version": subprocess.run(
                [str(paper_python), "--version"], check=True,
                capture_output=True, text=True, env=clean_env,
            ).stdout.strip(),
            "pip_check": pip_check.stdout.strip(),
            "dependency_freeze_sha256": freeze_sha256,
            "dependency_freeze_lines": len(freeze.splitlines()),
            "entrypoint_help_passed": True,
            "entrypoint_help_runs": len(help_outputs),
            "entrypoint_help_sha256": hashlib.sha256(
                help_outputs[0].encode()
            ).hexdigest(),
            "selected_core_modules": imports["selected_core_modules"],
            "imported_core_modules": imports["imported_core_modules"],
            "imported_module_names": imports["imported_module_names"],
            "module_import_failures": imports["failures"],
            "module_import_inventory_deterministic_across_two_runs": True,
            "network_attempts": imports["network_attempts"],
            "resolved_packages": imports["resolved_packages"],
            "pandas_ta_historical_version": "0.3.14b0",
            "pandas_ta_unaffiliated_mirror_url": PANDAS_TA_MIRROR_URL,
            "pandas_ta_unaffiliated_mirror_commit": PANDAS_TA_MIRROR_COMMIT,
            "pandas_ta_original_pypi_distribution_available": False,
            "postcutoff_mirror_build_tool_used_then_removed": "poetry-core==2.1.3",
            "source_tests_shipped": 0,
            "controlled_native_component_runs": 2,
            "controlled_native_component_deterministic": True,
            "controlled_native_component": component,
            "future_state_exposure_observed": True,
            "long_only_trading_path_executed": True,
            "transaction_cost_path_executed": True,
            "released_metric_functions_executed": 7,
            "paper_result_reproduction": False,
        },
        freeze,
    )


def native_execution(
    source_root: Path,
    paper_root: Path,
    latex_command: str,
    paper_python: Path,
) -> dict[str, Any]:
    environment, freeze = dependency_environment_execution(
        source_root, paper_python
    )
    requirements_at_paper_commit = git(
        source_root, "ls-tree", "-r", "--name-only", SOURCE_PAPER_COMMIT,
    ).splitlines()
    return {
        "paper_source_compilation": compile_paper_source(paper_root, latex_command),
        "released_python_static_compilation": {"files": 142, "syntax_errors": 0},
        "entrypoint_help_probe": {
            "attempted": True,
            "exit_code": 0,
            "passed": environment["entrypoint_help_passed"],
            "runs": environment["entrypoint_help_runs"],
            "interpretation": (
                "the original paper source entrypoint resolves under author-added "
                "requirements guidance; this is component, not result, evidence"
            ),
        },
        "dependency_environment": environment,
        "_dependency_freeze_text": freeze,
        "paper_commit_has_requirements_file": "requirements.txt" in requirements_at_paper_commit,
        "full_native_system_execution_attempted": False,
        "full_native_system_execution_reason": (
            "exact input snapshot, API credentials, memories, trajectories, output records, and operational preview models are unavailable"
        ),
        "published_result_units_reproduced": 0,
        "paper_result_credit": False,
    }


def render_readme(manifest: Mapping[str, Any]) -> str:
    return f"""# FinAgent paper replication audit

This is a fail-closed audit of the original KDD 2024 paper, all three official
arXiv versions and source archives, and the repository linked by the lead
author's homepage.  The release is substantial—{manifest['released_python_files']} Python
files, prompts, configs, agent modules, and rule-strategy records. Its core and
CLI now execute in a reconstructed environment, but the missing research inputs
and outputs still prevent an executable package for the published claims.

## Honest outcome

- Paper document: reproduced from pinned source at 43 pages.
- Official-version lineage: v1 and v2 contain 768 identical table cells; v3
  contains 959. Relative to v1/v2, v3 numerically revises
  {manifest['official_version_numeric_value_revisions_in_v3']} shared cells, changes display precision for
  {manifest['official_version_display_precision_only_changes_in_v3']}, adds {manifest['official_version_cell_ids_added_in_v3']} cell IDs, and removes
  {manifest['official_version_cell_ids_removed_in_v3']}. The 31 result-figure source assets are byte-identical across all
  three versions.
- Public source timing: v1 and v2 predate the repository; v3 has the six-commit
  paper-era tree available. Only v3 is evaluated against public implementation.
- Static released-source mechanisms matching the paper: {manifest['released_source_mechanisms_verified']} of {manifest['paper_mechanisms_audited']} audited claims.
- Dependency-backed source boundary: the original CLI help passes twice, all
  {manifest['paper_era_core_modules_imported']} core modules import twice with
  real dependencies and zero HTTP attempts, and two controlled native trading/
  metric runs agree exactly.
- Published result units: **0 of {manifest['published_result_display_units_total']} reproduced** ({manifest['paper_numeric_display_cells_total']} table cells and {manifest['paper_figure_display_units_total']} figure units).
- Overall tier: **R3 / runnable component environment, no paper-result reproduction**.

No paper-result credit is assigned to values transcribed from LaTeX, plot-only
graphics, rule-strategy parameter records, static compilation, or document
compilation.  The repository contains no exact dataset snapshot, FinAgent
memories, trajectories, action/equity paths, checkpoints, or native result
tables. All {manifest['reachable_source_history_commits']} reachable commits, {manifest['public_source_unique_historical_paths']} historical paths, and
{manifest['public_source_reachable_blobs']} blobs were checked; no unreachable object or native agent-output path
exists. The only discovered branch is `main`, with no tags or releases. The 90
shipped rule records yield {manifest['released_strategy_record_appendix_comparisons']} default/trained comparisons against the
corresponding high-precision Appendix Table 7 cells, with
{manifest['released_strategy_record_appendix_display_matches']} display-precision matches; no released code path writes those opaque
`best_*` records.

A dated GitHub census covers all {manifest['graphql_accessible_public_forks']}
reported and accessible public forks and {manifest['public_fork_branch_refs_examined']}
branch refs, collapsing to {manifest['public_fork_unique_heads_examined']} unique heads.
Both official-history heads and all {manifest['public_fork_divergent_heads_examined']}
divergent heads were checked. The divergent surface contains
{manifest['public_fork_divergent_extra_commits_examined']} unique extra commits,
{manifest['public_fork_divergent_changed_paths_examined']} changed paths, and
{manifest['public_fork_new_final_unique_blobs_examined']} new final-tree blobs. It is
limited to unaffiliated post-paper function-calling, prompt/news, and FTSE MIB
source/data-pipeline adaptations. No divergent commit matches an official-source
author identity, and no native agent result or exact paper table/figure artifact
was found; all fork evidence receives zero paper-result credit.

## What now executes

The authors added only `requirements.txt` after the paper-era source commit;
every other tracked path is unchanged. Resolving those author-listed packages
with a 2024-08-31 release cutoff produces a clean 148-line environment freeze.
The historical `pandas-ta` 0.3.14b0 distribution has been removed from PyPI, so
its runtime code is recovered from a hash-pinned unaffiliated mirror and receives
no provenance or result credit; rewritten Poetry metadata required a temporary
post-cutoff build tool that was removed from the final environment. Consequently
the environment is compatible and reproducible, not historically exact.

The original `tools/main.py --help` path succeeds, 65/65 `finagent` modules
import, and no blocked network send is attempted. A deterministic controlled
fixture executes BUY/HOLD/SELL through the native long-only environment with its
10-bp transaction cost and runs ARR, VOL, downside deviation, MDD, Sharpe,
Calmar, and Sortino functions. It also directly observes that a January 3 state
contains prices through January 5 when `look_forward_days=2`. These are stronger
native component and protocol-conflict checks, never paper-performance evidence.

## Material protocol conflicts

The full validation runner renders the k-line chart with the plotting default
`mode="train"`, while state construction includes 14 future days.  This
exposes future prices to the vision reflection path despite the paper's
no-lookahead claim.  The environment is long-only despite the paper's TSLA
short-position explanation.  Optimized rule parameters are loaded and then
their signals are overwritten by a default-parameter call.  OPTUNA and six
ML/RL baselines are absent.  Released SR/CR/SOR code disagrees with the paper's
equations.  Twenty-one asset-list references (including all eighteen downloader
references), sixty training-prompt references, and three processor/downloader
routes are broken.

The detailed CSVs and `native_execution.json` are the evidence ledger.  A
modern substitute model or reconstructed dataset would be an adaptation, not
an exact reproduction, and must remain labeled accordingly.
"""


def audit(
    source_root: Path,
    paper_root: Path,
    paper_versions_root: Path,
    output: Path,
    latex_command: str,
    fork_census_root: Path,
    fork_snapshot_path: Path,
    paper_python: Path,
) -> dict[str, Any]:
    validate_primary_inputs(source_root, paper_root)
    paper_source_root = paper_root / "source_v3"
    output.mkdir(parents=True, exist_ok=True)

    paper_versions, result_lineage = paper_version_rows(paper_versions_root, source_root)
    tables = paper_table_rows(paper_source_root)
    figures = paper_figure_rows(paper_source_root)
    inventory = source_inventory(source_root)
    strategies = strategy_record_rows(source_root)
    strategy_conformance = strategy_record_paper_conformance_rows(source_root, tables)
    history = source_history_rows(source_root)
    history_paths, history_summary = public_source_history(source_root)
    output_fork_snapshot = output / "public_fork_branch_ref_snapshot.csv"
    if fork_snapshot_path.resolve() != output_fork_snapshot.resolve():
        shutil.copyfile(fork_snapshot_path, output_fork_snapshot)
    fork_heads, fork_summary = public_fork_census(
        fork_census_root, output_fork_snapshot,
    )
    configs = config_conformance_rows(source_root)
    references = source_reference_diagnostics(source_root)
    routes = processor_route_rows(source_root)
    python_rows = static_python_rows(source_root)
    metrics = metric_diagnostic_rows(source_root)
    mechanisms = mechanism_rows()
    internal = internal_check_rows()
    artifacts = data_artifact_rows(source_root)
    native = native_execution(
        source_root, paper_root, latex_command, paper_python
    )
    dependency_freeze = native.pop("_dependency_freeze_text")

    csv_outputs = {
        "paper_numeric_table_conformance.csv": tables,
        "paper_figure_display_inventory.csv": figures,
        "released_source_inventory.csv": inventory,
        "released_strategy_record_inventory.csv": strategies,
        "released_strategy_record_paper_conformance.csv": strategy_conformance,
        "released_source_history_inventory.csv": history,
        "official_paper_version_inventory.csv": paper_versions,
        "official_paper_result_lineage.csv": result_lineage,
        "public_source_history_path_inventory.csv": history_paths,
        "public_fork_unique_head_inventory.csv": fork_heads,
        "released_config_conformance.csv": configs,
        "released_missing_reference_diagnostics.csv": references,
        "released_processor_route_diagnostics.csv": routes,
        "released_python_static_compilation.csv": python_rows,
        "paper_source_metric_formula_diagnostics.csv": metrics,
        "paper_mechanism_conformance.csv": mechanisms,
        "paper_internal_consistency_checks.csv": internal,
        "released_data_artifact_inventory.csv": artifacts,
    }
    for filename, rows in csv_outputs.items():
        write_csv(output / filename, rows)
    (output / "native_execution.json").write_text(
        json.dumps(native, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output / "paper_era_environment_freeze.txt").write_text(
        dependency_freeze, encoding="utf-8"
    )
    (output / "public_source_history.json").write_text(
        json.dumps(history_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output / "public_fork_census.json").write_text(
        json.dumps(fork_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )

    manifest: dict[str, Any] = {
        "audit_date": AUDIT_DATE,
        "paper": "A Multimodal Foundation Agent for Financial Trading: Tool-Augmented, Diversified, and Generalist",
        "arxiv_url": ARXIV_URL,
        "arxiv_v3_date": ARXIV_V3_DATE,
        "official_arxiv_versions_audited": len(paper_versions),
        "arxiv_v1_numeric_table_cells": 768,
        "arxiv_v2_numeric_table_cells": 768,
        "arxiv_v3_numeric_table_cells": 959,
        "official_version_unique_table_cell_ids": len(result_lineage),
        "official_version_numeric_value_revisions_in_v3": sum(
            row["status"] == "numeric_value_revised_in_v3" for row in result_lineage
        ),
        "official_version_display_precision_only_changes_in_v3": sum(
            row["status"] == "display_precision_only_change_in_v3" for row in result_lineage
        ),
        "official_version_cell_ids_added_in_v3": sum(
            row["status"] == "added_in_v3" for row in result_lineage
        ),
        "official_version_cell_ids_removed_in_v3": sum(
            row["status"] == "removed_in_v3" for row in result_lineage
        ),
        "official_versions_result_figure_assets_byte_identical": True,
        "official_versions_with_public_source_at_submission": sum(
            row["public_source_available_at_submission"] for row in paper_versions
        ),
        "doi": DOI,
        "kdd_pdf_url": KDD_PDF_URL,
        "author_homepage": AUTHOR_HOMEPAGE,
        "source_url": SOURCE_URL,
        "source_provenance": "repository_linked_from_lead_author_homepage",
        "source_paper_commit": SOURCE_PAPER_COMMIT,
        "source_current_commit": SOURCE_CURRENT_COMMIT,
        "source_change_after_paper_commit": "requirements.txt_only",
        "overall_status": "substantial_author_linked_source_but_zero_of_1061_published_result_units_reproduced",
        "replication_tier": "R3_runnable_component_environment_no_paper_result_reproduction",
        "full_paper_reproduced": False,
        "paper_document_reproduced": bool(native["paper_source_compilation"].get("matches_arxiv_page_count")),
        "paper_numeric_display_cells_total": len(tables),
        "paper_numeric_display_cells_with_paper_result_credit": sum(row["paper_result_credit"] for row in tables),
        "paper_figure_display_units_total": len(figures),
        "paper_figure_display_units_with_paper_result_credit": sum(row["paper_result_credit"] for row in figures),
        "published_result_display_units_total": len(tables) + len(figures),
        "published_result_display_units_reproduced": 0,
        "paper_mechanisms_audited": len(mechanisms),
        "released_source_mechanisms_verified": sum(row["released_source_conformance_credit"] for row in mechanisms),
        "released_source_files_at_paper_commit": len(inventory),
        "released_python_files": sum(row["kind"] == "python_source" for row in inventory),
        "released_strategy_record_files": len(strategies),
        "released_strategy_best_params_nonempty": sum(row["record_kind"] == "best_params" and row["nonempty"] for row in strategies),
        "released_strategy_record_appendix_comparisons": len(strategy_conformance),
        "released_strategy_record_appendix_display_matches": sum(row["display_precision_match"] for row in strategy_conformance),
        "reachable_source_history_commits": len(history),
        "reachable_source_history_commits_with_agent_output_paths": sum(bool(row["agent_output_paths"]) for row in history),
        "reachable_source_history_first_party_path_sets_identical_before_requirements_only_commit": len({row["first_party_files_excluding_vendored_echarts"] for row in history[:-1]}) == 1,
        "public_source_unique_historical_paths": history_summary["unique_historical_paths"],
        "public_source_reachable_blobs": history_summary["reachable_object_counts"]["blob"],
        "public_source_reachable_trees": history_summary["reachable_object_counts"]["tree"],
        "public_source_reachable_commit_objects": history_summary["reachable_object_counts"]["commit"],
        "public_source_unreachable_objects": history_summary["unreachable_objects"],
        "public_source_native_agent_result_paths": history_summary["native_agent_result_paths"],
        "public_source_historical_strategy_record_paths": history_summary[
            "historical_strategy_record_paths"
        ],
        "public_source_discovered_branches": len(history_summary["discovered_public_branches"]),
        "public_source_discovered_tags": len(history_summary["discovered_public_tags"]),
        "public_source_discovered_releases": len(history_summary["discovered_public_releases"]),
        "public_fork_census_date": fork_summary["census_date"],
        "github_rest_reported_public_forks": fork_summary["github_rest_reported_forks"],
        "graphql_accessible_public_forks": fork_summary["graphql_accessible_forks"],
        "public_fork_accessibility_gap": fork_summary["rest_minus_accessible_fork_gap"],
        "public_fork_branch_refs_examined": fork_summary["graphql_accessible_branch_refs"],
        "public_fork_unique_heads_examined": fork_summary["unique_heads"],
        "public_fork_divergent_heads_examined": fork_summary["divergent_heads_reviewed"],
        "public_fork_divergent_extra_commits_examined": fork_summary[
            "divergent_extra_commits_reviewed"
        ],
        "public_fork_divergent_changed_paths_examined": fork_summary[
            "divergent_changed_paths_reviewed"
        ],
        "public_fork_author_attributed_divergent_heads": fork_summary[
            "divergent_heads_matching_official_source_author_identity"
        ],
        "public_fork_new_final_unique_blobs_examined": fork_summary[
            "new_final_unique_blobs_reviewed"
        ],
        "public_fork_native_agent_result_paths_discovered": fork_summary[
            "native_agent_result_paths_discovered"
        ],
        "public_fork_exact_paper_result_paths_discovered": fork_summary[
            "exact_paper_result_table_or_figure_paths_discovered"
        ],
        "public_fork_paper_result_credit": fork_summary["paper_result_credit"],
        "released_experiment_configs": len(configs),
        "released_missing_references": len(references),
        "metric_formula_conflicts": sum(not row["matches_paper_formula"] for row in metrics),
        "paper_era_dependency_environment_reproduced": native[
            "dependency_environment"
        ]["dependency_environment_reproduced"],
        "paper_era_exact_historical_dependency_versions_recovered": native[
            "dependency_environment"
        ]["exact_historical_dependency_versions_recovered"],
        "paper_era_entrypoint_help_passed": native["dependency_environment"][
            "entrypoint_help_passed"
        ],
        "paper_era_core_modules_imported": native["dependency_environment"][
            "imported_core_modules"
        ],
        "paper_era_controlled_native_component_runs": native[
            "dependency_environment"
        ]["controlled_native_component_runs"],
        "paper_era_future_state_exposure_observed": native[
            "dependency_environment"
        ]["future_state_exposure_observed"],
        "paper_era_released_metric_functions_executed": native[
            "dependency_environment"
        ]["released_metric_functions_executed"],
        "exact_dataset_released": False,
        "agent_result_records_released": False,
        "paper_result_credit": False,
    }
    (output / "README.md").write_text(render_readme(manifest), encoding="utf-8")
    output_names = [
        *csv_outputs,
        "native_execution.json",
        "public_fork_branch_ref_snapshot.csv",
        "public_fork_census.json",
        "public_source_history.json",
        "README.md",
        "paper_era_environment_freeze.txt",
    ]
    manifest["output_sha256"] = {name: sha256(output / name) for name in sorted(output_names)}
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument(
        "--paper-versions-root",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/finagent_paper_versions"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--latex-command", default="pdflatex")
    parser.add_argument(
        "--fork-census-root", type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/finagent_fork_census"),
    )
    parser.add_argument(
        "--fork-snapshot", type=Path,
        default=project_root / "paper_runs/paper_replication_audits/finagent/public_fork_branch_ref_snapshot.csv",
    )
    parser.add_argument(
        "--paper-python",
        type=Path,
        default=Path(os.environ.get("FINAGENT_PAPER_PYTHON", DEFAULT_PAPER_PYTHON)),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = audit(
        args.source_root,
        args.paper_root,
        args.paper_versions_root,
        args.output,
        args.latex_command,
        args.fork_census_root,
        args.fork_snapshot,
        args.paper_python.resolve(),
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
