#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for Profit Mirage / FactFin.

The audit pins arXiv v1 and its complete manuscript source, checks bounded
author/hub/archive searches, inventories every displayed empirical table cell,
recomputes the paper's derived comparisons, and tests the disclosed Yahoo price
schema against the reported Buy-and-Hold row.  A manuscript rebuild, a current
provider response, or a recomputed arithmetic claim is evidence about the paper;
none is an execution of FactFin.  No empirical result receives replication
credit without the original implementation, frozen data, exact prompts/model
requests, generated strategies, trades, and portfolio path.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]

TITLE = "Profit Mirage: Revisiting Information Leakage in LLM-based Financial Agents"
AUTHORS = ["Xiangyu Li", "Yawen Zeng", "Xiaofen Xing", "Jin Xu", "Xiangmin Xu"]
ARXIV_RECORD = "https://arxiv.org/abs/2510.07920v1"
ARXIV_PDF_URL = "https://arxiv.org/pdf/2510.07920v1"
ARXIV_SOURCE_URL = "https://arxiv.org/e-print/2510.07920v1"
AUTHOR_HOMEPAGE = "https://xiangyuli616.github.io/"
AUTHOR_GITHUB = "https://github.com/XiangyuLi616"

PAPER_SHA256 = "1024f16ced8e9b12c6a4f0c7bf56551a92da0d621507da621ee82ae68355aba5"
PAPER_PAGES = 12
SOURCE_ARCHIVE_SHA256 = "f8888b5d281ada1b16a6ac32a43da031cc54d4afd1775e8909e5cf4ab65bd0c6"
SOURCE_FILE_COUNT = 14
SOURCE_FILE_BYTES = 4_934_317
AUTHOR_HOMEPAGE_HEAD = "a42532c72b3837ab88763a5d22538c8d3742a02b"
AUTHOR_HOMEPAGE_ARCHIVE_SHA256 = "2c217c9dfcf9130d5b3a9b356a1de3dbeb25025da5b470cfe1293f563a08a1c4"
REBUILD_1_SHA256 = "a16fb96f1b9f5d59fcd1a2376a36da5446ece99cdc14b3837c2059e8cdbfce05"
REBUILD_2_SHA256 = "aa97b69f0d9d9f837c6330968614cab7e6ab545db87f7ac01d57262b7f1ff077"
REBUILD_LAYOUT_TEXT_SHA256 = "dcb245d9bec508e7d6aacdf1e1b0e50a6addaab5b298654304f7ef49d771347d"
NORMALIZED_OFFICIAL_AND_REBUILD_TEXT_SHA256 = "29538331baccad835fa8b0b54007d184d5dc6252c4fbe9aec03a0c4fb9aa853e"

ASSETS = ("AAPL", "NVDA", "TSLA", "BYD", "Tencent", "Bitcoin")
PERFORMANCE_METRICS = ("TR_pct", "SR", "MDD_pct")
LEAKAGE_METRICS = ("PC", "CI", "IDS")


# Table 1: the paper's historical counterfactual audit of five prior agents.
COUNTERFACTUAL_RESULTS: list[tuple[str, tuple[float, float, float]]] = [
    ("FinMem", (0.8213, 0.8743, 0.2766)),
    ("FinAgent", (0.7245, 0.7781, 0.3598)),
    ("QuantAgent", (0.7789, 0.8362, 0.2941)),
    ("FinCON", (0.7136, 0.7522, 0.3612)),
    ("TradingAgents", (0.6903, 0.7016, 0.3837)),
]


# Table 3: values are ordered AAPL TR/SR/MDD, then NVDA, TSLA, BYD,
# Tencent, and Bitcoin.  The category column is retained for audit output.
PERFORMANCE_RESULTS: list[tuple[str, str, tuple[float, ...]]] = [
    ("Market", "B&H", (-3.36, 0.05, 33.43, 27.81, 0.72, 36.89, 57.88, 0.98, 53.77, 32.43, 0.96, 19.56, 36.82, 1.12, 23.49, 70.40, 1.10, 28.11)),
    ("Fin-LLM", "FinGPT", (14.48, 0.59, 29.05, 28.01, 0.73, 32.62, 42.58, 0.85, 52.37, 10.21, 0.46, 21.31, -5.93, -0.05, 23.28, 42.81, 0.85, 24.61)),
    ("Fin-LLM", "Fin-LLaMA", (-20.05, -0.63, 37.76, 16.27, 0.55, 32.65, 63.15, 1.06, 53.71, -9.61, -0.12, 22.23, 23.64, 0.82, 23.47, 21.04, 0.53, 31.19)),
    ("Fin-LLM", "InvestLM", (-9.25, -0.21, 32.86, 38.18, 0.89, 28.40, 50.15, 0.96, 36.88, -4.11, 0.03, 23.17, -4.85, -0.06, 19.92, 54.88, 1.01, 26.66)),
    ("Single-Agent", "FinMem", (-5.68, -0.03, 32.11, 35.88, 0.84, 33.42, 52.32, 0.95, 44.63, 26.83, 0.88, 19.55, 27.77, 0.97, 17.40, 72.68, 1.26, 19.68)),
    ("Single-Agent", "FinAgent", (27.79, 0.99, 21.52, 54.86, 1.09, 27.78, 79.01, 1.24, -9.36, 32.91, 1.04, 20.17, 44.18, 1.29, 23.44, 94.63, 1.38, 24.53)),
    ("Single-Agent", "QuantAgent", (6.60, 0.36, 29.39, 49.83, 1.03, 30.12, 74.26, 1.21, 42.35, 31.74, 1.03, 18.01, 31.15, 1.08, 19.95, 90.56, 1.35, 32.98)),
    ("Multi-Agents", "TradingAgents", (12.89, 0.55, 27.26, 59.28, 1.17, 25.99, 106.01, 1.47, 36.90, 43.33, 1.26, 19.53, 42.77, 1.38, 24.18, 88.39, 1.37, 32.96)),
    ("Multi-Agents", "HedgeAgents", (16.06, 0.68, 12.12, 54.09, 1.10, 28.39, 115.09, 1.48, 48.79, 57.96, 1.49, 18.72, 66.31, 1.85, 17.67, 134.36, 1.71, 22.12)),
    ("Multi-Agents", "FinRobot", (21.76, 0.81, 21.54, 43.98, 0.72, 36.65, 96.32, 1.34, 49.99, 38.49, 1.09, 20.53, 57.54, 1.81, 14.56, 109.18, 1.51, 21.67)),
    ("Ours", "FactFin", (36.70, 1.22, 11.57, 71.34, 1.29, 24.25, 165.01, 1.83, 31.54, 84.24, 2.09, 16.01, 81.37, 2.31, 14.14, 171.46, 2.03, 16.59)),
]

PERFORMANCE_IMPROVEMENTS = (
    32.06, 23.23, 4.54, 20.34, 10.26, 6.69, 43.37, 19.13, 14.48,
    45.34, 40.27, 11.10, 22.71, 24.86, 2.88, 27.61, 18.71, 15.70,
)


# Table 4: same asset-major ordering as Table 3.
LEAKAGE_RESULTS: list[tuple[str, str, tuple[float, ...]]] = [
    ("Market", "FinGPT", (0.8239, 0.9011, 0.1851, 0.9172, 0.9240, 0.1233, 0.7587, 0.8189, 0.2818, 0.8091, 0.8393, 0.3014, 0.7188, 0.7596, 0.3316, 0.6955, 0.7277, 0.3513)),
    ("Fin-LLM", "Fin-LLaMA", (0.8785, 0.9288, 0.2127, 0.8835, 0.9113, 0.2139, 0.8355, 0.8681, 0.2425, 0.7802, 0.8123, 0.3273, 0.8425, 0.8701, 0.2259, 0.7872, 0.8129, 0.2618)),
    ("Fin-LLM", "InvestLM", (0.9187, 0.9223, 0.1618, 0.9213, 0.9322, 0.1716, 0.8527, 0.8819, 0.2123, 0.8285, 0.8391, 0.2517, 0.8612, 0.8908, 0.1959, 0.8911, 0.9121, 0.1537)),
    ("LLM-Agent", "FinMem", (0.8578, 0.8662, 0.2531, 0.8123, 0.8235, 0.2809, 0.7651, 0.8032, 0.3014, 0.7912, 0.8073, 0.2833, 0.7716, 0.8125, 0.3268, 0.8235, 0.8481, 0.2918)),
    ("LLM-Agent", "FinAgent", (0.7252, 0.7316, 0.3402, 0.7566, 0.7907, 0.3825, 0.7408, 0.7524, 0.3635, 0.7395, 0.7735, 0.3341, 0.7219, 0.7395, 0.3643, 0.7574, 0.7802, 0.3639)),
    ("LLM-Agent", "QuantAgent", (0.7436, 0.7768, 0.3251, 0.7723, 0.8168, 0.3526, 0.7262, 0.7659, 0.3422, 0.6775, 0.7079, 0.3868, 0.7358, 0.7762, 0.3425, 0.7976, 0.8038, 0.3276)),
    ("LLM-MultiAgents", "TradingAgents", (0.6882, 0.7252, 0.4248, 0.6671, 0.6975, 0.4413, 0.6816, 0.7003, 0.4151, 0.6912, 0.7306, 0.3647, 0.6728, 0.7031, 0.3849, 0.7095, 0.7334, 0.3945)),
    ("LLM-MultiAgents", "HedgeAgents", (0.6594, 0.6942, 0.4052, 0.6808, 0.7012, 0.4688, 0.7163, 0.7367, 0.3855, 0.6786, 0.6927, 0.3851, 0.6443, 0.6728, 0.3653, 0.6755, 0.6971, 0.4229)),
    ("LLM-MultiAgents", "FinRobot", (0.7267, 0.7591, 0.3845, 0.7321, 0.7414, 0.3946, 0.6591, 0.6629, 0.3773, 0.6892, 0.7248, 0.3549, 0.7166, 0.7325, 0.3561, 0.7269, 0.7343, 0.3817)),
    ("Ours", "FactFin", (0.3115, 0.2548, 0.7781, 0.2842, 0.2645, 0.7613, 0.3427, 0.3057, 0.7544, 0.2424, 0.2273, 0.8279, 0.2612, 0.2509, 0.7726, 0.2843, 0.3146, 0.7847)),
]

LEAKAGE_IMPROVEMENTS = (
    52.77, 63.30, 83.17, 57.39, 62.08, 62.39, 48.00, 53.89, 81.74,
    64.22, 67.18, 114.04, 59.45, 62.70, 100.73, 57.91, 54.87, 85.55,
)


# Table 5: CS/MCTS/RAG/SCG flag plus AAPL six metrics and TSLA six metrics.
ABLATION_RESULTS: list[tuple[str, tuple[float, ...]]] = [
    ("SCG", (8.77, 0.43, 24.34, 0.6213, 0.6457, 0.4361, 78.42, 1.22, 40.42, 0.6703, 0.6319, 0.3857)),
    ("SCG+RAG", (13.36, 0.56, 23.65, 0.5529, 0.5201, 0.4903, 104.38, 1.44, 37.45, 0.5852, 0.5638, 0.4293)),
    ("SCG+RAG+MCTS", (28.12, 0.99, 16.20, 0.4858, 0.5026, 0.5348, 130.93, 1.64, 33.52, 0.4927, 0.4481, 0.5299)),
    ("SCG+RAG+MCTS+CS", (36.70, 1.22, 11.57, 0.3115, 0.2548, 0.7781, 165.01, 1.83, 31.54, 0.3427, 0.3057, 0.7544)),
]

BACKBONE_RESULTS: list[tuple[str, tuple[float, ...]]] = [
    ("Qwen2.5-72B-Instruct", (93.12, 1.65, 20.34, 0.3098, 0.2897, 0.7623)),
    ("LLaMA-3.1 405B", (91.56, 1.62, 20.89, 0.3156, 0.2956, 0.7567)),
    ("DeepSeek-V3", (99.78, 1.76, 17.89, 0.2823, 0.2654, 0.7692)),
    ("Claude-Sonnet-3.5", (98.23, 1.74, 18.45, 0.2756, 0.2689, 0.7633)),
    ("Gemini-2.0-Flash", (89.45, 1.58, 21.78, 0.3212, 0.3045, 0.7456)),
    ("GPT-4o", (101.69, 1.79, 19.02, 0.2877, 0.2696, 0.7798)),
]

# Table 8 has three scored model responses in each of four benchmark examples.
CASE_STUDY_SCORES = [
    ("price_inquiry", "GPT-4o", 1.0),
    ("price_inquiry", "Claude-Sonnet-3.7", 1.0),
    ("price_inquiry", "Grok-3", 1.0),
    ("event_impact", "GPT-4o", 1.0),
    ("event_impact", "Claude-Sonnet-3.7", 1.0),
    ("event_impact", "Grok-3", 0.5),
    ("trend_prediction", "GPT-4o", 1.0),
    ("trend_prediction", "Claude-Sonnet-3.7", 1.0),
    ("trend_prediction", "Grok-3", 1.0),
    ("market_performance", "GPT-4o", 1.0),
    ("market_performance", "Claude-Sonnet-3.7", 1.0),
    ("market_performance", "Grok-3", 0.5),
]


YAHOO_HASHES = {
    "002594.SZ.json": "ed0232a5b0cc478664cf937538c7e1307d98a87a3f13ca41f9bd07941449377d",
    "0700.HK.json": "b3e676c741edb2b49fbb8ff1606d0becedac0489a23d1755a657bf33dcce612d",
    "AAPL.json": "93b83adc58ffe00de66c6e145010f07ca0ca238707b4b7993bc35da5b7acb203",
    "BTC-USD.json": "e0657ce691657f6a08e5fe64e8076925a3dce2ab8d0bd2e08678a579897c016a",
    "NVDA.json": "7ee2fed2ead7d427781937e0cc0523e724f3162a8049eb1d0ab08903874e27cf",
    "TSLA.json": "545ca540fa2c2aded06e93888081bba75451f9dd8fcc386392b7d749d6700807",
}

SEARCH_HASHES = {
    "arxiv_abs_2510.07920v1.html": "17fadd98dc5317377792a1759caee48e155671c0ac40f1c797a5b40d0170711e",
    "github_author_homepage_head.json": "f59b76505c864e74ff7ca5920d28650ea4d7103c514d3038c00492472320e4d7",
    "github_repo_author_homepage.json": "d325517dcae28aa659abfa67462120a4e1ead29260ec98acf5fee4f1a0bc8f4b",
    "github_repo_researchtrend_target.json": "0b2543675462426b616023ba55dfa0063916cc7584eb742284d9c387778d3dc1",
    "github_repos_XiangyuLi616.json": "348f3f86777ebd717eb459e5cbedf141281261fb7bc052054c51e3b7247a3538",
    "github_search_arxiv_id.json": "1429019648f268a8ed11c15a7edb6388cba28ab92a894e37d44414ba61758adf",
    "github_search_author_title.json": "eefc2794768c4b625c01b00083d84bbfbc042fa79d2de497c17a153f066e0cca",
    "github_search_factfin.json": "0104d487cec0ebbe6efa567cf8d1f6f66bdcf20547ea6dd27f409c1c154612aa",
    "github_search_finlake_bench.json": "bd9c7904b77c1a9b61ade0aae3576358b875275363e171c7c4df354b86323a7f",
    "github_search_finleak_bench.json": "08c082fdf7ca87ba911a2aabb0f0cf2d3e482a6feeaac9713e4578c20b2600b2",
    "github_search_profit_mirage.json": "ed74b7bb26b52db7efdd7fcc02e2fca5e04973071e817194f5faa22ec4ab6086",
    "github_user_id_139937996_response.json": "c419d598307f0737b1353cb6ba1118629fae8343ba6a928aa9792127054c6151",
    "huggingface_datasets_finlake.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "huggingface_datasets_finleak.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "huggingface_models_factfin.json": "4925643b1f226ad181c45fb507911939fd3c91ef6175172fa5e89f3abcf8477f",
    "huggingface_spaces_factfin.json": "be00b0275f72d1b78475765672ebb7ce735e82797e49c670d63e5854fc153375",
    "software_heritage_factfin.json": "1157acbee8515d8190b3cd5eb645d7d7adfc4c68486a5f5681a69705d5168555",
    "software_heritage_finleak.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "wayback_orangecat_factfin.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "wayback_xiangyuli_factfin.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "xiangyuli616_homepage_a42532c72b3837ab88763a5d22538c8d3742a02b.tar.gz": AUTHOR_HOMEPAGE_ARCHIVE_SHA256,
}

PAPER_ASSET_TO_YAHOO = {
    "AAPL": "AAPL",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "BYD": "002594.SZ",
    "Tencent": "0700.HK",
    "Bitcoin": "BTC-USD",
}

PAPER_TRADING_DAYS = {
    "AAPL": 1380,
    "NVDA": 1380,
    "TSLA": 1380,
    "BYD": 1329,
    "Tencent": 1350,
    "Bitcoin": 2008,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: Sequence[str] | None = None) -> None:
    materialized = list(rows)
    if not materialized:
        raise ValueError(f"refusing to write empty audit artifact: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields or materialized[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(materialized)


def validate_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {path}")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{label} hash changed: expected {expected}, got {actual}")


def validate_hashed_files(root: Path, expected: Mapping[str, str], label: str) -> None:
    for name, digest in expected.items():
        validate_hash(root / name, digest, f"{label}/{name}")


def _append_asset_major(
    rows: list[dict[str, Any]],
    table: str,
    category: str,
    variant: str,
    values: Sequence[float],
    metrics: Sequence[str],
    *,
    cell_kind: str = "direct_result",
    factfin_output: bool = False,
) -> None:
    if len(values) != len(ASSETS) * len(metrics):
        raise ValueError(f"unexpected width for {table}/{variant}: {len(values)}")
    for index, value in enumerate(values):
        asset = ASSETS[index // len(metrics)]
        metric = metrics[index % len(metrics)]
        duplicate = ""
        if table == "ablation" and variant == "SCG+RAG+MCTS+CS":
            duplicate = f"full_factfin_{asset}_{metric}"
        rows.append({
            "table": table,
            "category": category,
            "variant": variant,
            "asset_or_scope": asset,
            "metric": metric,
            "paper_value": value,
            "cell_kind": cell_kind,
            "factfin_system_output": factfin_output,
            "duplicate_measurement_group": duplicate,
            "native_reproduced_value": "",
            "paper_result_credit": False,
            "status": "paper_value_only_zero_credit",
            "note": "No released native result lineage, exact input snapshot, or executable paper pipeline.",
        })


def result_ledger() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant, values in COUNTERFACTUAL_RESULTS:
        for metric, value in zip(LEAKAGE_METRICS, values):
            rows.append({
                "table": "counterfactual_agents",
                "category": "prior_agent_audit",
                "variant": variant,
                "asset_or_scope": "ten_stock_average",
                "metric": metric,
                "paper_value": value,
                "cell_kind": "direct_result",
                "factfin_system_output": False,
                "duplicate_measurement_group": "",
                "native_reproduced_value": "",
                "paper_result_credit": False,
                "status": "paper_value_only_zero_credit",
                "note": "Underlying predictions, confidence distributions, perturbations, and repetitions are absent.",
            })

    for category, variant, values in PERFORMANCE_RESULTS:
        _append_asset_major(
            rows, "overall_performance", category, variant, values,
            PERFORMANCE_METRICS, factfin_output=variant == "FactFin",
        )
    _append_asset_major(
        rows, "overall_performance_improvement", "Derived", "Improvement",
        PERFORMANCE_IMPROVEMENTS, PERFORMANCE_METRICS,
        cell_kind="derived_comparison", factfin_output=False,
    )

    for category, variant, values in LEAKAGE_RESULTS:
        _append_asset_major(
            rows, "leakage_metrics", category, variant, values,
            LEAKAGE_METRICS, factfin_output=variant == "FactFin",
        )
    _append_asset_major(
        rows, "leakage_improvement", "Derived", "Improvement",
        LEAKAGE_IMPROVEMENTS, LEAKAGE_METRICS,
        cell_kind="derived_comparison", factfin_output=False,
    )

    ablation_metrics = PERFORMANCE_METRICS + LEAKAGE_METRICS
    for variant, values in ABLATION_RESULTS:
        # ABLATION_RESULTS is ordered all six AAPL metrics then all six TSLA metrics.
        for index, value in enumerate(values):
            asset = ("AAPL", "TSLA")[index // len(ablation_metrics)]
            metric = ablation_metrics[index % len(ablation_metrics)]
            duplicate = (
                f"full_factfin_{asset}_{metric}"
                if variant == "SCG+RAG+MCTS+CS" else ""
            )
            rows.append({
                "table": "ablation",
                "category": "FactFin component variant",
                "variant": variant,
                "asset_or_scope": asset,
                "metric": metric,
                "paper_value": value,
                "cell_kind": "direct_result",
                "factfin_system_output": True,
                "duplicate_measurement_group": duplicate,
                "native_reproduced_value": "",
                "paper_result_credit": False,
                "status": "paper_value_only_zero_credit",
                "note": "Full-row AAPL/TSLA values duplicate Tables 3-4; no ablation run is released.",
            })

    backbone_metrics = PERFORMANCE_METRICS + LEAKAGE_METRICS
    for variant, values in BACKBONE_RESULTS:
        for metric, value in zip(backbone_metrics, values):
            rows.append({
                "table": "llm_backbone",
                "category": "FactFin backbone",
                "variant": variant,
                "asset_or_scope": "six_asset_aggregate",
                "metric": metric,
                "paper_value": value,
                "cell_kind": "direct_result",
                "factfin_system_output": True,
                "duplicate_measurement_group": "",
                "native_reproduced_value": "",
                "paper_result_credit": False,
                "status": "paper_value_only_zero_credit",
                "note": "No exact model snapshots, requests, generated strategies, or aggregate inputs are released.",
            })

    for category, model, score in CASE_STUDY_SCORES:
        rows.append({
            "table": "finleak_case_study",
            "category": category,
            "variant": model,
            "asset_or_scope": "single_published_example",
            "metric": "score",
            "paper_value": score,
            "cell_kind": "direct_result",
            "factfin_system_output": False,
            "duplicate_measurement_group": "",
            "native_reproduced_value": "",
            "paper_result_credit": False,
            "status": "paper_value_only_zero_credit",
            "note": "Displayed prose response/score only; no immutable request, response metadata, or scorer trace.",
        })

    if len(rows) != 525:
        raise ValueError(f"expected 525 displayed empirical/derived table cells, got {len(rows)}")
    if sum(row["cell_kind"] == "direct_result" for row in rows) != 489:
        raise ValueError("direct-result denominator changed")
    if sum(bool(row["factfin_system_output"]) for row in rows) != 120:
        raise ValueError("FactFin result-cell denominator changed")
    return rows


def prompt_inventory() -> list[dict[str, Any]]:
    return [
        {
            "prompt_or_request": "strategy_code_generator",
            "paper_location": "Section 3.3",
            "publication_form": "verbatim simplified template",
            "recovered_text": (
                "Given market state with {Prices}, {Factors}, and {News}, generate "
                "executable trading strategy code, e.g., {Examples}, using only provided inputs."
            ),
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "simplified_template_only",
            "note": "Footnote says changing templates are fully disclosed in the appendix; they are absent.",
        },
        {
            "prompt_or_request": "rag_factor_extraction",
            "paper_location": "Section 3.4",
            "publication_form": "equations/symbols only",
            "recovered_text": "",
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "missing_exact_prompt",
            "note": "No retrieval query, corpus, chunks, result payload, or factorization prompt.",
        },
        {
            "prompt_or_request": "mcts_strategy_modification",
            "paper_location": "Equation 16",
            "publication_form": "P_modify symbol only",
            "recovered_text": "",
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "missing_exact_prompt",
            "note": "No modification prompt, examples, expansion response, or code contract.",
        },
        {
            "prompt_or_request": "finleak_benchmark_evaluation",
            "paper_location": "Sections 2.3 and Appendix B",
            "publication_form": "questions/scoring examples only",
            "recovered_text": "",
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "missing_exact_prompt",
            "note": "No system message, benchmark wrapper, decoding settings, or full 2,000-question dataset.",
        },
        {
            "prompt_or_request": "fine_tuning_examples",
            "paper_location": "Section 2.4",
            "publication_form": "none",
            "recovered_text": "",
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "missing_training_format",
            "note": "No input/output template, label construction, split records, or training instances.",
        },
    ]


def method_specification_audit() -> list[dict[str, str]]:
    data = [
        ("system_identity", "FactFin: SCG + RAG + MCTS + CS", "specified_high_level", "Component names and order are visible; executable interfaces are not."),
        ("asset_universe", "AAPL, NVDA, TSLA, 002594.SZ, 0700.HK, BTC-USD inferred from labels/day counts", "partially_recovered", "Ticker mappings are inferable and current Yahoo counts match, but the paper prints company and ticker as comma-separated pairs."),
        ("price_provider", "Yahoo Finance", "specified_provider_current_snapshot_pinned", "Original responses, query parameters, retrieval time, time zone, adjustment state, and exact fill field are absent."),
        ("news_provider", "Alpaca News API", "specified_provider_only", "No subscription, query, article IDs, timestamps, filters, frozen rows, or release."),
        ("data_period", "2020-01-01 through 2025-06-30", "specified_dates", "The train/validation allocation is not visible; a training period exists only in a commented source line."),
        ("evaluation_period", "2024-07-01 through 2025-06-30", "specified_dates", "No exact exchange calendars or signal/fill boundary convention."),
        ("training_period", "commented source says 2020-01-01 through 2024-06-30", "missing_from_published_paper", "A source comment cannot establish the executed split."),
        ("state_price_features", "price with volume and turnover; table lists OHLC, adj_close, vol, turn", "specified_schema_only", "Lookbacks, transformations, missing values, normalization, corporate actions, and field names are absent."),
        ("state_factors", "technical/fundamental factors including RSI, MACD, KDJ, PE, PB, ROE", "examples_only", "Complete factor list, formula library, parameters, timing, and point-in-time rules are absent."),
        ("state_news", "factorized news sentiment/topic features", "concept_only", "Model, label ontology, prompt, window, aggregation, timestamps, and outputs are absent."),
        ("action_space", "buy, sell, hold", "specified_labels_only", "No target quantity/weight, cash, inventory, shorting, leverage, or mapping from code return to orders."),
        ("llm_backbone", "GPT-4o alias, temperature 0.7", "mutable_alias_partial_config", "No dated snapshot, seed, top-p, max tokens, tools, stop rules, retry policy, or immutable requests."),
        ("strategy_language", "executable strategy code", "missing_runtime_contract", "Language, package surface, function signature, sandbox, parser, validation, timeout, and examples are absent."),
        ("rag_embedding", "text-embedding-3-large, top-k=5", "specified_alias_and_k_only", "Corpus, chunking, query, index, distance, dimensions, tie handling, and inserted records are absent."),
        ("mcts", "depth 10, UCB c=0.5", "specified_two_hyperparameters_only", "State/action nodes, branching, expansion prompt, rollouts, reward, budget, stopping rule, and seeds are absent."),
        ("counterfactual_simulator", "perturb prices/factors/news; 50 evaluation scenarios per asset", "specified_high_level_only", "delta, sigma, alpha/beta/gamma, generators, constraints, dates, seeds, and exact scenarios are absent."),
        ("counterfactual_inventory", "Table 7 reports 253/267/271/229/243/279 scenarios", "counts_only", "Relationship between inventory counts and the 50-per-asset evaluation sample is unspecified."),
        ("initial_capital", "not stated", "missing_initial_capital", "Cannot recreate cash, quantities, position limits, or portfolio path."),
        ("position_sizing", "not stated", "missing_position_sizing", "Discrete action labels do not identify traded quantities or portfolio weights."),
        ("signal_to_fill_timing", "not stated", "missing_fill_timing", "No same-day/next-day rule, price, market hours, or news cutoff."),
        ("transaction_costs", "standard transaction costs", "missing_numeric_cost_model", "No commission, tax, fee, spread, borrow, or market-specific schedule."),
        ("slippage", "realistic slippage models", "missing_numeric_slippage_model", "No formula, volume dependence, units, or parameters."),
        ("risk_free_rate", "appears in Sharpe equation", "missing_risk_free_rate", "No value, series, frequency, or currency rule."),
        ("metric_conventions", "TR, SR, MDD; PC, CI, IDS equations", "missing_operational_conventions", "Annualization, return frequency, MDD sign, confidence/probability extraction, edge cases, and aggregation are absent."),
        ("baseline_implementations", "nine baselines said to follow original specifications", "missing_baseline_code_and_configs", "No forks, commits, adapters, prompts, model requests, hyperparameters, or outputs; HedgeAgents itself has no public system code."),
        ("benchmark_dataset", "2,000 FinLeak/FinLake QA pairs, Jan 2022-Jun 2023", "missing_dataset", "Only 12 example questions/case-study scores are printed; category counts and full records are absent."),
        ("benchmark_scoring", "range/partial/qualitative scoring", "missing_executable_scorer", "The printed exact-equality equation conflicts with partial-credit and qualitative rules."),
        ("fine_tuning_data", "FNSPID; DJIA; Jan 2020-Dec 2022; test Jan-Jun 2022", "specified_source_and_overlapping_dates_only", "Exact dataset revision, rows, split, label task, and leakage controls are absent."),
        ("fine_tuning_config", "LoRA rank64 alpha16 dropout0.1 batch16 gradacc4 lr2e-4 warmup0.03", "partial_hyperparameters", "Epochs/steps, optimizer, scheduler, target modules, precision, sequence length, seed, packing, and checkpoint are absent."),
        ("randomness_and_repetitions", "temperature 0.7; no run count, seed, or uncertainty", "missing_seeds_repetitions_uncertainty", "Single point estimates cannot be regenerated or statistically assessed."),
        ("runtime_environment", "not released", "missing_environment", "No dependency lock, language version, hardware manifest, API dates, or runner."),
        ("actual_llm_requests", "not released", "missing_actual_requests", "No immutable inputs, request IDs, responses, token probabilities, or retries."),
        ("generated_strategies", "not released", "missing_generated_strategy_code", "No initial/evolved code, tree, reward, or execution logs."),
        ("actions_orders_fills", "not released", "missing_actions_orders_fills", "No dated action, quantity, order, fill, cost, slippage, or cash record."),
        ("portfolio_trajectories", "figures only", "missing_machine_readable_portfolio_paths", "Raster curves cannot establish exact dates, returns, drawdowns, or metric generation."),
    ]
    return [
        {"dimension": dimension, "paper_or_source_statement": statement, "status": status, "replication_impact": impact}
        for dimension, statement, status, impact in data
    ]


def _performance_lookup() -> dict[str, tuple[float, ...]]:
    return {model: values for _, model, values in PERFORMANCE_RESULTS}


def arithmetic_audit() -> list[dict[str, Any]]:
    performance = _performance_lookup()
    baselines = [
        values for model, values in performance.items()
        if model not in {"B&H", "FactFin"}
    ]
    factfin = performance["FactFin"]

    literal_performance_recomputed: list[float] = []
    literal_performance_matches: list[bool] = []
    for index, (paper_value, fact_value) in enumerate(zip(PERFORMANCE_IMPROVEMENTS, factfin)):
        metric = PERFORMANCE_METRICS[index % 3]
        candidates = [values[index] for values in baselines]
        best = max(candidates) if metric in {"TR_pct", "SR"} else min(candidates)
        recomputed = (
            (fact_value / best - 1.0) * 100.0
            if metric in {"TR_pct", "SR"}
            else (best - fact_value) / best * 100.0
        )
        literal_performance_recomputed.append(recomputed)
        literal_performance_matches.append(round(recomputed, 2) == paper_value)

    leakage_lookup = {model: values for _, model, values in LEAKAGE_RESULTS}
    leakage_baselines = [values for model, values in leakage_lookup.items() if model != "FactFin"]
    leakage_factfin = leakage_lookup["FactFin"]
    leakage_recomputed: list[float] = []
    leakage_matches: list[bool] = []
    for index, (paper_value, fact_value) in enumerate(zip(LEAKAGE_IMPROVEMENTS, leakage_factfin)):
        metric = LEAKAGE_METRICS[index % 3]
        candidates = [values[index] for values in leakage_baselines]
        if metric in {"PC", "CI"}:
            best = min(candidates)
            recomputed = (best - fact_value) / best * 100.0
        else:
            best = max(candidates)
            recomputed = (fact_value / best - 1.0) * 100.0
        leakage_recomputed.append(recomputed)
        leakage_matches.append(round(recomputed, 2) == paper_value)
    leakage_within_one_hundredth = [
        abs(recomputed - paper_value) <= 0.011
        for recomputed, paper_value in zip(leakage_recomputed, LEAKAGE_IMPROVEMENTS)
    ]

    average_claims = [31.91, 22.74, 9.23]
    average_recomputed = [
        sum(PERFORMANCE_IMPROVEMENTS[offset::3]) / len(ASSETS)
        for offset in range(3)
    ]
    best_sr = [max(values[index] for values in baselines) for index in range(1, 18, 3)]
    factfin_sr = list(factfin[1::3])
    ratio_of_means = (sum(factfin_sr) / 6) / (sum(best_sr) / 6)

    figure_1_pre_post = [
        ("FinMem", "SR", 1.73, 0.69, 60.12),
        ("FinAgent", "SR", 1.81, 0.74, 59.12),
        ("QuantAgent", "SR", 1.69, 0.82, 51.48),
        ("FinCON", "SR", 1.88, 0.71, 62.23),
        ("TradingAgents", "SR", 1.76, 0.78, 55.68),
        ("FinMem", "TR", 32.86, 9.25, 71.85),
        ("FinAgent", "TR", 41.31, 17.26, 58.22),
        ("QuantAgent", "TR", 29.94, 13.73, 54.14),
        ("FinCON", "TR", 35.77, 15.39, 56.96),
        ("TradingAgents", "TR", 43.52, 21.68, 50.18),
    ]
    figure_1_matches = [
        round((pre - post) / pre * 100.0, 2) == decay
        for _, _, pre, post, decay in figure_1_pre_post
    ]
    figure_1_within_two_hundredths = [
        abs((pre - post) / pre * 100.0 - decay) <= 0.021
        for _, _, pre, post, decay in figure_1_pre_post
    ]

    return [
        {
            "claim_id": "performance_improvement_row_literal",
            "paper_claim": "18 Table-3 improvement percentages",
            "recomputed_or_comparison": f"{sum(literal_performance_matches)}/18 follow literal best-baseline ranking; TSLA MDD recomputes against -9.36 as {literal_performance_recomputed[8]:.2f}% rather than 14.48%.",
            "status": "17_of_18_literal_matches_one_internal_sign_conflict",
            "replication_implication": "The printed TSLA FinAgent MDD cannot coexist with the highlighted optimum and improvement arithmetic.",
        },
        {
            "claim_id": "leakage_improvement_row",
            "paper_claim": "18 Table-4 improvement percentages",
            "recomputed_or_comparison": (
                f"{sum(leakage_matches)}/18 round exactly from the displayed best-baseline and "
                f"FactFin cells; {sum(leakage_within_one_hundredth)}/18 are within 0.01 percentage "
                "points and are compatible with hidden source precision."
            ),
            "status": "12_of_18_exact_six_hidden_precision_compatible",
            "replication_implication": (
                "The row is arithmetically plausible, but six cells require unreported source "
                "precision; underlying predictions remain unreproduced."
            ),
        },
        {
            "claim_id": "average_performance_improvements",
            "paper_claim": "average TR/SR/MDD improvements 31.91%, 22.74%, 9.23%",
            "recomputed_or_comparison": ", ".join(f"{value:.4f}%" for value in average_recomputed),
            "status": "displayed_arithmetic_reproduced" if all(round(value, 2) == claim for value, claim in zip(average_recomputed, average_claims)) else "mismatch",
            "replication_implication": "Means of the displayed improvement row verify the prose only.",
        },
        {
            "claim_id": "one_point_four_times_sharpe",
            "paper_claim": "out-of-sample Sharpe ratios 1.4x higher than the best baselines",
            "recomputed_or_comparison": f"Mean FactFin SR / mean per-asset best-baseline SR = {ratio_of_means:.4f}x; mean printed relative improvement = {average_recomputed[1]:.2f}%.",
            "status": "claim_not_supported_by_displayed_table",
            "replication_implication": "The headline ratio has no matching aggregation in the published cells.",
        },
        {
            "claim_id": "figure_1_decay_rates",
            "paper_claim": "five SR and five TR decay annotations",
            "recomputed_or_comparison": (
                f"{sum(figure_1_matches)}/10 annotations round exactly from the printed pre/post "
                f"bars; {sum(figure_1_within_two_hundredths)}/10 are within 0.02 percentage "
                "points. FinCON TR prints 56.96% versus 56.98% from displayed bars."
            ),
            "status": "9_of_10_exact_one_hidden_precision_compatible",
            "replication_implication": (
                "The row is arithmetically plausible, but one annotation requires hidden source "
                "precision; the experiment and causal attribution are not reproduced."
            ),
        },
        {
            "claim_id": "figure_3_accuracy_gains",
            "paper_claim": "+20.55% and +21.79%",
            "recomputed_or_comparison": "72.16-51.61=20.55 and 76.52-54.73=21.79 percentage points; relative gains are 39.82% and 39.81%.",
            "status": "percent_label_is_percentage_point_difference",
            "replication_implication": "The bar labels should not be read as relative percentage improvements.",
        },
    ]


def internal_consistency_audit() -> list[dict[str, str]]:
    rows = [
        ("benchmark_name", "Abstract/introduction/conclusion say FinLake-Bench; body, figures, tables, and appendix say FinLeak-Bench.", "hard_naming_conflict", "The released benchmark identity and search target are ambiguous."),
        ("claimed_benchmark_release", "The paper repeatedly says it releases FinLake-Bench, but v1/source/homepage contain no dataset URL and bounded GitHub/Hugging Face/archive searches recover none.", "claimed_release_not_recovered", "Only 12 printed example scores and several question examples are public."),
        ("claimed_template_disclosure", "SCG footnote says changing templates are fully disclosed in the appendix; the appendix contains no prompt templates.", "claim_contradicted_by_source_bundle", "The only verbatim prompt is explicitly simplified."),
        ("claimed_baseline_details", "Baselines footnote says more details are in the appendix; the appendix contains no baseline implementation/configuration section.", "claim_contradicted_by_source_bundle", "Original-specification baseline reruns cannot be audited."),
        ("tsla_finagent_mdd", "Table 3 prints FinAgent TSLA MDD=-9.36%, yet marks FactFin 31.54% optimal, InvestLM 36.88% second, and calculates 14.48% improvement from 36.88%.", "hard_internal_value_or_sign_conflict", "Literal ranking makes the bolding and improvement invalid; likely correction is not published."),
        ("finrobot_tsla_mdd_prose", "Prose says FinRobot has MDD=-49.99% for TSLA; Table 3 prints +49.99%.", "hard_sign_conflict", "The intended MDD sign convention is unresolved."),
        ("scoring_equation", "Accuracy equation requires exact answer equality times a weight, while prose/tables award interval, partial, magnitude, and qualitative credit.", "metric_definition_conflict", "No executable scorer can be derived from the equation and examples together."),
        ("bias_score_range", "Bias formula averages a frequency-weighted prediction score then subtracts 1/S; positive 0.2895/0.3122 require an unstated score scale and are impossible if p_score is a probability in [0,1].", "metric_scale_underspecified", "Reported Bias values cannot be regenerated without the missing score definition."),
        ("fine_tune_test_overlap", "Fine-tuning data span Jan 2020-Dec 2022, while the stated test period is Jan-Jun 2022.", "temporal_overlap_unresolved", "The paper calls the evaluation unseen but does not identify held-out rows or a non-overlapping split."),
        ("closed_source_superiority", "Paper says closed-source backbones consistently outperform open-source models in financial metrics and leakage control; DeepSeek-V3 has the best MDD and CI and exceeds several closed models elsewhere.", "claim_contradicted_by_own_table", "Backbone conclusion must be qualified metric by metric."),
        ("all_baselines_original_spec", "Paper says all baselines follow original specifications, including HedgeAgents, whose public author artifact is documentation only and whose executable specification is materially incomplete.", "unverifiable_implementation_claim", "No baseline fork/config/output lineage is released."),
        ("causal_leakage_attribution", "Comparable aggregate market returns across different 2021/2024 periods are treated as isolating memorization; constituents, regimes, volatility, news, and implementation drift are not controlled.", "causal_claim_not_identified", "Observed decay is not by itself a unique measurement of information leakage."),
        ("sensitivity_as_leakage", "PC/CI/IDS input sensitivity is interpreted as memorization/leakage and causal learning without a validated mapping or invariant/non-invariant perturbation taxonomy.", "construct_validity_unestablished", "Metric reproduction would not establish the claimed causal interpretation."),
        ("six_assets_wording", "Chinese equity is printed as 'BYD, 002594.SZ' and Hong Kong equity as 'Tencent, 0700.HK', which reads like four entries although each pair names one asset.", "identifier_presentation_ambiguous", "Yahoo day counts support the ticker mapping but the paper does not state it cleanly."),
    ]
    return [
        {"claim_id": cid, "paper_or_source_claim": claim, "status": status, "replication_implication": implication}
        for cid, claim, status, implication in rows
    ]


def figure_inventory() -> list[dict[str, Any]]:
    data = [
        (1, "1.png", 2, "pre/post SR and TR bars", 30, 20, "All ten decay annotations recompute from printed bar values."),
        (2, "2.png", 1, "FinLeak-Bench accuracy bars", 4, 12, "Only four cross-model averages are numerically labeled; per-model bar values are absent."),
        (3, "3.png", 2, "fine-tuning accuracy and bias/memory/generalization bars", 12, 10, "Accuracy gains are percentage-point differences labeled with percent signs."),
        (4, "4.pdf", 1, "FactFin architecture", 0, 0, "Method diagram, not an empirical result."),
        (5, "5.png", 6, "six-asset cumulative returns", 0, 54, "Nine plotted series per asset; exact dated arrays are absent."),
        (6, "6.png", 2, "AAPL/TSLA ablation cumulative returns", 0, 10, "Five plotted series per asset; exact dated arrays are absent."),
        (7, "7.png", 6, "LLM-backbone radar charts", 36, 6, "Labels transform Table-6 TR/MDD percentages to fractions; no new run lineage."),
    ]
    return [
        {
            "figure": number,
            "source_file": source,
            "panels": panels,
            "output_type": output_type,
            "exact_numeric_result_labels": labels,
            "plotted_result_series_or_bars": series,
            "audit_note": note,
            "machine_readable_underlying_results_released": False,
            "figure_digitization_is_replication": False,
            "status": "published_visual_only_zero_result_credit",
        }
        for number, source, panels, output_type, labels, series, note in data
    ]


def source_inventory(archive: Path, source_dir: Path) -> list[dict[str, Any]]:
    validate_hash(archive, SOURCE_ARCHIVE_SHA256, "arXiv source archive")
    rows: list[dict[str, Any]] = []
    with tarfile.open(archive, "r:*") as bundle:
        members = sorted((member for member in bundle.getmembers() if member.isfile()), key=lambda item: item.name)
        if len(members) != SOURCE_FILE_COUNT or sum(member.size for member in members) != SOURCE_FILE_BYTES:
            raise ValueError("arXiv source inventory count/size changed")
        for member in members:
            path = source_dir / member.name
            if not path.is_file() or path.stat().st_size != member.size:
                raise ValueError(f"source extraction mismatch: {member.name}")
            if member.name == "finleak_www.tex":
                role = "primary_manuscript_source"
            elif member.name == "appendix.tex":
                role = "manuscript_appendix_source"
            elif re.fullmatch(r"[1-7]\.(?:png|pdf)", member.name):
                role = "published_figure"
            else:
                role = "bibliography_or_typesetting_support"
            rows.append({
                "path": member.name,
                "bytes": member.size,
                "sha256": sha256(path),
                "role": role,
                "is_executable_system_source": False,
                "replication_credit": False,
            })
    return rows


def pdf_text(path: Path) -> str:
    validate_hash(path, PAPER_SHA256, "official paper PDF")
    reader = PdfReader(path)
    if len(reader.pages) != PAPER_PAGES:
        raise ValueError(f"paper page count changed: {len(reader.pages)}")
    text = " ".join(" ".join((page.extract_text() or "").split()) for page in reader.pages)
    for marker in (TITLE, "FinLake-Bench", "FinLeak-Bench", "165.01%", "0.8279"):
        if marker not in text:
            raise ValueError(f"paper marker missing: {marker}")
    return text


def pdftotext_layout(path: Path) -> bytes:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def normalized_text_hash(payload: bytes, *, strip_arxiv_stamp: bool) -> str:
    text = payload.decode("utf-8")
    if strip_arxiv_stamp:
        text = re.sub(r"^arXiv:2510\.07920v1 \[cs\.AI\] 9 Oct 2025\s*$", "", text, flags=re.M)
    compact = "".join(text.split())
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()


def artifact_access_audit() -> list[dict[str, Any]]:
    return [
        {"artifact": "arxiv_v1_source", "availability": "14 manuscript/typesetting files including seven figures", "tier": "paper source only", "system_source_credit": False, "note": "No FactFin/benchmark program, environment, or data."},
        {"artifact": "author_homepage", "availability": f"one-page static site at {AUTHOR_HOMEPAGE_HEAD}; Profit Mirage links only to arXiv", "tier": "R1 author documentation", "system_source_credit": False, "note": "No code, data, weights, or project link on the paper entry."},
        {"artifact": "author_github_account", "availability": "stable account id 139937996 renamed OrangeCat0616 to XiangyuLi616; one public homepage repository", "tier": "bounded author inventory", "system_source_credit": False, "note": "Current public inventory is not proof that private/deleted artifacts never existed."},
        {"artifact": "github_metadata_search", "availability": "title, arXiv id, FactFin, FinLake-Bench, and FinLeak-Bench searches pinned", "tier": "bounded discovery", "system_source_credit": False, "note": "Matches are surveys/citations/unaffiliated projects, not an author implementation."},
        {"artifact": "huggingface_search", "availability": "zero matching FinLake/FinLeak datasets; FactFin substring hits are unrelated fact-finding projects", "tier": "bounded discovery", "system_source_credit": False, "note": "Current hub metadata only."},
        {"artifact": "software_heritage_search", "availability": "zero FinLeak matches; FactFin substring results are unrelated FactFinder projects", "tier": "bounded archival discovery", "system_source_credit": False, "note": "Indexed origins only."},
        {"artifact": "wayback_guessed_author_repos", "availability": "no captures for OrangeCat0616/FactFin or XiangyuLi616/FactFin", "tier": "bounded archival discovery", "system_source_credit": False, "note": "Two guessed URLs only."},
        {"artifact": "researchtrend_github_target", "availability": "paper index GitHub button resolves to Bavest/fin-llama", "tier": "false-positive boundary", "system_source_credit": False, "note": "Fin-LLaMA is a cited 2023 baseline, not FactFin or FinLeak-Bench."},
        {"artifact": "release_promise_in_source", "availability": "open-source resources/model/framework bullet exists only as a commented TeX line", "tier": "non-public promise", "system_source_credit": False, "note": "Commented manuscript text is not a release."},
    ]


def discovery_evidence(search_dir: Path) -> list[dict[str, Any]]:
    validate_hashed_files(search_dir, SEARCH_HASHES, "search")
    account = json.loads((search_dir / "github_user_id_139937996_response.json").read_text(encoding="utf-8"))
    repos = json.loads((search_dir / "github_repos_XiangyuLi616.json").read_text(encoding="utf-8"))
    homepage_head = json.loads((search_dir / "github_author_homepage_head.json").read_text(encoding="utf-8"))
    if account["id"] != 139_937_996 or account["login"] != "XiangyuLi616":
        raise ValueError("author GitHub identity boundary changed")
    if [item["full_name"] for item in repos] != ["XiangyuLi616/XiangyuLi616.github.io"]:
        raise ValueError("author public repository inventory changed")
    if homepage_head["sha"] != AUTHOR_HOMEPAGE_HEAD:
        raise ValueError("author homepage head changed")
    homepage = search_dir / "author_homepage_head/index.html"
    if not homepage.is_file():
        raise FileNotFoundError("extracted pinned author homepage is missing")
    homepage_text = homepage.read_text(encoding="utf-8")
    paper_section = homepage_text[homepage_text.index("<!-- Profit Mirage -->"):homepage_text.index("<!-- HedgeAgents -->")]
    if "https://arxiv.org/abs/2510.07920" not in paper_section:
        raise ValueError("author homepage paper link changed")
    if any(token in paper_section.lower() for token in ("github.com", "huggingface.co", "dataset", ">code<")):
        raise ValueError("author homepage now contains an unreviewed Profit Mirage artifact link")

    searches = {
        "exact title": "github_search_profit_mirage.json",
        "arXiv id": "github_search_arxiv_id.json",
        "FactFin": "github_search_factfin.json",
        "FinLake-Bench": "github_search_finlake_bench.json",
        "FinLeak-Bench": "github_search_finleak_bench.json",
    }
    rows: list[dict[str, Any]] = []
    for query, filename in searches.items():
        payload = json.loads((search_dir / filename).read_text(encoding="utf-8"))
        rows.append({
            "source": "GitHub repository metadata search",
            "query_or_url": query,
            "result": f"{payload['total_count']} matches; none author-attributable system/data release",
            "system_or_dataset_recovered": False,
            "negative_search_limit": "metadata/readme search only; not private/deleted repositories or authenticated code search",
        })
    rows.extend([
        {"source": "GitHub stable author id", "query_or_url": "api.github.com/user/139937996", "result": "current login XiangyuLi616; one public repository", "system_or_dataset_recovered": False, "negative_search_limit": "current public account inventory only"},
        {"source": "Pinned author homepage", "query_or_url": AUTHOR_HOMEPAGE, "result": "Profit Mirage entry links only to arXiv", "system_or_dataset_recovered": False, "negative_search_limit": "pinned public homepage head only"},
        {"source": "Hugging Face datasets", "query_or_url": "FinLake-Bench / FinLeak-Bench", "result": "zero matches", "system_or_dataset_recovered": False, "negative_search_limit": "current hub metadata search only"},
        {"source": "Hugging Face models/spaces", "query_or_url": "FactFin", "result": "substring matches unrelated fact-finding projects", "system_or_dataset_recovered": False, "negative_search_limit": "current hub metadata search only"},
        {"source": "Software Heritage", "query_or_url": "FactFin / FinLeak-Bench", "result": "no relevant origin", "system_or_dataset_recovered": False, "negative_search_limit": "indexed public origins only"},
        {"source": "Wayback guessed repositories", "query_or_url": "OrangeCat0616/FactFin and XiangyuLi616/FactFin", "result": "no successful capture", "system_or_dataset_recovered": False, "negative_search_limit": "two guessed repository URLs only"},
        {"source": "arXiv v1 record/source", "query_or_url": ARXIV_RECORD, "result": "one version; paper/source only; no direct code or dataset URL", "system_or_dataset_recovered": False, "negative_search_limit": "submission bundle and visible record only"},
        {"source": "Third-party paper-index link", "query_or_url": "ResearchTrend GitHub button", "result": "resolves to unrelated Bavest/fin-llama baseline repository", "system_or_dataset_recovered": False, "negative_search_limit": "false-positive resolution, not an exhaustive discovery source"},
    ])
    return rows


def yahoo_diagnostics(yahoo_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    validate_hashed_files(yahoo_dir, YAHOO_HASHES, "Yahoo snapshot")
    period_start = 1_577_836_800  # 2020-01-01 UTC
    period_end = 1_751_328_000  # 2025-07-01 UTC, exclusive in this audit
    evaluation_start = 1_719_792_000  # 2024-07-01 UTC
    paper_bh = _performance_lookup()["B&H"]
    stats_rows: list[dict[str, Any]] = []
    bh_rows: list[dict[str, Any]] = []
    news_counts = dict(zip(ASSETS, (26_551, 28_432, 31_677, 17_423, 18_816, 20_213)))
    scenario_counts = dict(zip(ASSETS, (253, 267, 271, 229, 243, 279)))

    for asset_index, asset in enumerate(ASSETS):
        ticker = PAPER_ASSET_TO_YAHOO[asset]
        payload = json.loads((yahoo_dir / f"{ticker}.json").read_text(encoding="utf-8"))
        result = payload["chart"]["result"][0]
        if result["meta"]["symbol"] != ticker:
            raise ValueError(f"Yahoo symbol changed for {ticker}")
        timestamps = result["timestamp"]
        all_indexes = [i for i, stamp in enumerate(timestamps) if period_start <= stamp < period_end]
        eval_indexes = [i for i, stamp in enumerate(timestamps) if evaluation_start <= stamp < period_end]
        if len(all_indexes) != PAPER_TRADING_DAYS[asset]:
            raise ValueError(f"Yahoo day-count diagnostic changed for {asset}")
        quote = result["indicators"]["quote"][0]["close"]
        adj = result["indicators"]["adjclose"][0]["adjclose"]
        close_values = [quote[i] for i in eval_indexes]
        adj_values = [adj[i] for i in eval_indexes]
        if any(value is None for value in close_values + adj_values):
            raise ValueError(f"null evaluation endpoint for {asset}")
        close_return = (close_values[-1] / close_values[0] - 1.0) * 100.0
        adj_return = (adj_values[-1] / adj_values[0] - 1.0) * 100.0
        reported = paper_bh[asset_index * 3]
        first_date = dt.datetime.fromtimestamp(timestamps[eval_indexes[0]], dt.timezone.utc).date().isoformat()
        last_date = dt.datetime.fromtimestamp(timestamps[eval_indexes[-1]], dt.timezone.utc).date().isoformat()
        stats_rows.append({
            "paper_asset": asset,
            "inferred_yahoo_ticker": ticker,
            "paper_trading_days": PAPER_TRADING_DAYS[asset],
            "current_pinned_yahoo_days_through_2025_06_30": len(all_indexes),
            "day_count_exact_match": True,
            "paper_news_count": news_counts[asset],
            "original_news_rows_recovered": 0,
            "paper_counterfactual_scenario_count": scenario_counts[asset],
            "original_counterfactual_scenarios_recovered": 0,
            "paper_result_credit": False,
        })
        bh_rows.append({
            "paper_asset": asset,
            "inferred_yahoo_ticker": ticker,
            "first_observation_utc_date": first_date,
            "last_observation_utc_date": last_date,
            "observations": len(eval_indexes),
            "paper_buy_hold_tr_pct": reported,
            "current_yahoo_close_endpoint_tr_pct": f"{close_return:.6f}",
            "current_yahoo_adjusted_close_endpoint_tr_pct": f"{adj_return:.6f}",
            "close_display_precision_match": round(close_return, 2) == reported,
            "adjusted_close_display_precision_match": round(adj_return, 2) == reported,
            "native_original_snapshot_recovered": False,
            "paper_result_credit": False,
            "note": "Current provider diagnostic only; no paper query, snapshot, or execution/cost convention.",
        })
    return stats_rows, bh_rows


def build_audit(paper_pdf: Path, scratch_root: Path, output_dir: Path) -> dict[str, Any]:
    downloads = scratch_root / "downloads"
    source_dir = scratch_root / "source_v1"
    builds = scratch_root / "builds"
    search_dir = downloads / "search"
    paper_text = pdf_text(paper_pdf)
    if len(paper_text) < 30_000:
        raise ValueError("paper text extraction unexpectedly short")

    source_rows = source_inventory(downloads / "profit_mirage_source_v1.tar", source_dir)
    tex = (source_dir / "finleak_www.tex").read_text(encoding="utf-8")
    appendix = (source_dir / "appendix.tex").read_text(encoding="utf-8")
    for marker in (
        "We will open-source all resources, including the dataset, model weights, and framework implementation.",
        "fully disclosed in the Appendix",
        "standard transaction costs and realistic slippage models",
        "text-embedding-3-large",
        "\\textbf{FactFin}",
    ):
        if marker not in tex:
            raise ValueError(f"manuscript source marker missing: {marker}")
    if "[Prompt Template]" in appendix or "P_{\\text{modify}}" in appendix:
        raise ValueError("appendix prompt boundary changed and needs review")

    rebuild_1 = builds / "run1/finleak_www.pdf"
    rebuild_2 = builds / "run2/finleak_www.pdf"
    validate_hash(rebuild_1, REBUILD_1_SHA256, "first converged manuscript rebuild")
    validate_hash(rebuild_2, REBUILD_2_SHA256, "second converged manuscript rebuild")
    for path in (rebuild_1, rebuild_2):
        if len(PdfReader(path).pages) != PAPER_PAGES:
            raise ValueError(f"rebuild page count changed: {path}")
        layout = pdftotext_layout(path)
        if hashlib.sha256(layout).hexdigest() != REBUILD_LAYOUT_TEXT_SHA256:
            raise ValueError(f"rebuild extracted layout text changed: {path}")
        if normalized_text_hash(layout, strip_arxiv_stamp=False) != NORMALIZED_OFFICIAL_AND_REBUILD_TEXT_SHA256:
            raise ValueError(f"rebuild normalized content changed: {path}")
    official_layout = pdftotext_layout(paper_pdf)
    if normalized_text_hash(official_layout, strip_arxiv_stamp=True) != NORMALIZED_OFFICIAL_AND_REBUILD_TEXT_SHA256:
        raise ValueError("official PDF and rebuild no longer have identical normalized content")

    ledger = result_ledger()
    prompts = prompt_inventory()
    methods = method_specification_audit()
    arithmetic = arithmetic_audit()
    consistency = internal_consistency_audit()
    figures = figure_inventory()
    access = artifact_access_audit()
    discovery = discovery_evidence(search_dir)
    dataset_stats, buy_hold = yahoo_diagnostics(downloads / "yahoo")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "paper_source_inventory.csv", source_rows)
    write_csv(output_dir / "artifact_access_audit.csv", access)
    write_csv(output_dir / "discovery_evidence.csv", discovery)
    write_csv(output_dir / "published_result_ledger.csv", ledger)
    write_csv(output_dir / "prompt_inventory.csv", prompts)
    write_csv(output_dir / "method_specification_audit.csv", methods)
    write_csv(output_dir / "arithmetic_audit.csv", arithmetic)
    write_csv(output_dir / "internal_consistency_audit.csv", consistency)
    write_csv(output_dir / "figure_inventory.csv", figures)
    write_csv(output_dir / "dataset_statistics_audit.csv", dataset_stats)
    write_csv(output_dir / "buy_hold_diagnostic.csv", buy_hold)

    provenance = {
        "title": TITLE,
        "authors": AUTHORS,
        "arxiv_record": ARXIV_RECORD,
        "arxiv_pdf_url": ARXIV_PDF_URL,
        "arxiv_source_url": ARXIV_SOURCE_URL,
        "arxiv_version": "v1 only; submitted 2025-10-09 08:13:35 UTC",
        "license": "CC BY 4.0",
        "official_pdf_sha256": PAPER_SHA256,
        "official_pdf_pages": PAPER_PAGES,
        "arxiv_source_sha256": SOURCE_ARCHIVE_SHA256,
        "arxiv_source_files": SOURCE_FILE_COUNT,
        "arxiv_source_file_bytes": SOURCE_FILE_BYTES,
        "source_archive_contains_system_code": False,
        "source_archive_interpretation": "manuscript, appendix, bibliography/typesetting support, and seven published figures only",
        "author_homepage": AUTHOR_HOMEPAGE,
        "author_github": AUTHOR_GITHUB,
        "author_homepage_repository_head": AUTHOR_HOMEPAGE_HEAD,
        "author_homepage_archive_sha256": AUTHOR_HOMEPAGE_ARCHIVE_SHA256,
        "first_converged_rebuild_sha256": REBUILD_1_SHA256,
        "second_converged_rebuild_sha256": REBUILD_2_SHA256,
        "rebuild_layout_text_sha256_both": REBUILD_LAYOUT_TEXT_SHA256,
        "official_and_rebuild_normalized_content_sha256": NORMALIZED_OFFICIAL_AND_REBUILD_TEXT_SHA256,
        "rebuild_comparison": "two rebuild PDFs have equal page count, size, and extracted text; raw hashes differ, so they are not called byte-identical",
        "official_comparison": "after removing only arXiv's injected page-1 margin stamp and whitespace, official v1 and both rebuilds have identical extracted content",
        "rebuild_parameters": {"latex_passes": 3, "SOURCE_DATE_EPOCH": 1_759_968_000, "TeX_Live": "2024"},
        "visual_qa": {
            "official_paper_all_12_pages": "pass; arXiv margin stamp on page 1; no clipped, overlapping, invisible, or illegible content",
            "rebuilt_paper_all_12_pages": "pass; same manuscript layout without arXiv margin stamp",
            "all_7_embedded_figures": "pass; visible and legible on inspected pages",
        },
    }
    write_json(output_dir / "source_provenance.json", provenance)

    native_execution = {
        "manuscript_source_rebuilt": True,
        "manuscript_rebuild_is_system_execution": False,
        "current_yahoo_provider_responses_pinned": True,
        "current_yahoo_day_counts_matching_paper": sum(row["day_count_exact_match"] for row in dataset_stats),
        "current_yahoo_diagnostic_is_original_snapshot": False,
        "public_factfin_system_source_found": False,
        "public_finlake_or_finleak_dataset_found": False,
        "factfin_pipeline_executed": False,
        "llm_calls_made": 0,
        "original_price_rows_loaded": 0,
        "current_provider_price_rows_loaded": sum(int(row["current_pinned_yahoo_days_through_2025_06_30"]) for row in dataset_stats),
        "original_news_rows_loaded": 0,
        "original_counterfactual_scenarios_loaded": 0,
        "original_benchmark_questions_loaded": 0,
        "actual_llm_requests_loaded": 0,
        "generated_strategy_code_loaded": 0,
        "native_actions_orders_fills_loaded": 0,
        "native_portfolio_trajectories_loaded": 0,
        "published_table_cells_faithfully_regenerated": 0,
        "strict_boundary": "document builds, current-provider diagnostics, arithmetic checks, printed responses, and raster figures receive zero empirical paper-result credit",
    }
    write_json(output_dir / "native_execution.json", native_execution)

    manifest: dict[str, Any] = {
        "audit": "Profit Mirage / FactFin / FinLake-FinLeak primary-source, artifact, method, result, and validity audit",
        "overall_status": "not_reproduced_no_public_system_or_benchmark_release_and_missing_runtime_data_strategy_trade_lineage",
        "full_end_to_end_pipeline_reproduced": False,
        "published_empirical_or_derived_numeric_table_cells": len(ledger),
        "published_direct_numeric_result_cells": sum(row["cell_kind"] == "direct_result" for row in ledger),
        "published_derived_comparison_cells": sum(row["cell_kind"] == "derived_comparison" for row in ledger),
        "factfin_direct_numeric_result_cells": sum(bool(row["factfin_system_output"]) for row in ledger),
        "factfin_unique_direct_numeric_measurements_after_table_duplicates": 108,
        "published_table_cells_faithfully_regenerated": 0,
        "factfin_cells_faithfully_regenerated": 0,
        "published_figures": len(figures),
        "published_figure_panels": sum(int(row["panels"]) for row in figures),
        "published_figure_exact_numeric_result_labels": sum(int(row["exact_numeric_result_labels"]) for row in figures),
        "published_figure_result_series_or_bars": sum(int(row["plotted_result_series_or_bars"]) for row in figures),
        "published_figures_with_machine_readable_underlying_results": 0,
        "arxiv_manuscript_source_files": len(source_rows),
        "arxiv_published_figure_files": sum(row["role"] == "published_figure" for row in source_rows),
        "public_system_source_files_recovered": 0,
        "public_benchmark_records_recovered": 0,
        "current_yahoo_day_counts_matching_paper": sum(row["day_count_exact_match"] for row in dataset_stats),
        "current_yahoo_buy_hold_cells_matching_paper_at_display_precision": sum(
            row["close_display_precision_match"] or row["adjusted_close_display_precision_match"]
            for row in buy_hold
        ),
        "verbatim_simplified_prompt_templates": sum(row["publication_form"] == "verbatim simplified template" for row in prompts),
        "actual_llm_requests_recovered": 0,
        "actual_llm_responses_recovered": 0,
        "generated_strategies_recovered": 0,
        "llm_calls_made": 0,
        "arithmetic_claims_checked": len(arithmetic),
        "material_internal_or_validity_findings": len(consistency),
        "bounded_discovery_checks": len(discovery),
        "visual_qa_passed": True,
        "interpretation": (
            "The official v1 PDF, complete TeX bundle, author homepage/account inventory, bounded repository/hub/archive searches, "
            "all 525 displayed empirical/derived numeric table cells, 82 exact figure labels, 112 plotted bars/series, method disclosures, "
            "and a pinned current Yahoo schema diagnostic are audited. The paper source rebuilds exactly at normalized extracted-content "
            "level. Current Yahoo day counts match all six paper counts, but no current close/adjusted-close endpoint return matches a "
            "published Buy-and-Hold cell at display precision. No FactFin code, FinLake/FinLeak dataset, frozen price/news inputs, exact "
            "prompts or model requests, generated strategies, MCTS tree, counterfactuals, actions, orders, fills, or portfolio path is public "
            "in the pinned evidence. Therefore zero empirical cells are faithfully regenerated."
        ),
    }

    readme = f"""# Profit Mirage / FactFin paper-level replication audit

Overall verdict: **not reproduced**. The paper document is strongly recoverable;
the claimed FactFin experiment and FinLake/FinLeak benchmark are not. This audit
pins the original arXiv v1 PDF/source, author-side public inventory, bounded hub
and archive searches, every displayed empirical result cell, every figure, and a
current Yahoo diagnostic. It gives zero result credit to typesetting, arithmetic,
raster values, current-provider substitutions, or printed example responses.

## What is genuinely recovered

- The official {PAPER_PAGES}-page PDF is pinned at `{PAPER_SHA256}`. Its complete
  {SOURCE_FILE_COUNT}-file source bundle contains TeX, appendix, bibliography and
  typesetting files, and seven figures—**no FactFin or benchmark program/data**.
- Two independent three-pass builds converge to 12 pages with identical extracted
  layout text. After removing only arXiv's injected margin stamp and whitespace,
  the official PDF and both builds share content hash
  `{NORMALIZED_OFFICIAL_AND_REBUILD_TEXT_SHA256}`. Their raw PDF hashes differ, so
  this audit does not call them byte-identical. All 24 official/rebuilt pages and
  all seven embedded figures passed visual inspection.
- The paper's six Yahoo ticker mappings are recoverable from labels and exact day
  counts. A pinned current response matches all six reported counts: 1380 each
  for AAPL/NVDA/TSLA, 1329 for 002594.SZ, 1350 for 0700.HK, and 2008 for BTC-USD
  through June 30, 2025. This validates a provider/schema fragment, not the
  original snapshot or experiment.
- All **525** displayed empirical or derived numeric table cells are transcribed:
  489 direct results and 36 derived improvement cells. **120** are direct FactFin
  full-system, ablation, or backbone outputs (108 unique measurements after the
  full AAPL/TSLA row duplicated across tables). **Zero of 525** are faithfully
  regenerated from the paper pipeline.
- Seven figures contain 82 exact numeric result labels and 112 plotted bars/series.
  Nine of ten Figure-1 decay labels round exactly from printed bars; the FinCON
  TR label differs by 0.02 percentage points and is compatible with hidden source
  precision. The exact dated arrays behind the curves are not released.

## Artifact search and claimed release

The abstract says the authors "release FinLake-Bench," while the body mostly calls
it FinLeak-Bench. Neither the arXiv record/source nor the pinned first-author
homepage links code or data. The author's stable GitHub account ID—renamed from
`OrangeCat0616` to `XiangyuLi616`—has one public repository, the homepage. Exact
title/arXiv/name searches on GitHub, Hugging Face dataset/model/space searches,
Software Heritage, and two guessed Wayback repository URLs recover no attributable
FactFin implementation or benchmark. A paper index's GitHub button resolves to
the unrelated 2023 `Bavest/fin-llama` baseline. These are bounded public searches,
**not proof** that private, deleted, or unindexed artifacts never existed.

The source contains an open-source promise only as a commented-out TeX bullet.
The only verbatim strategy prompt is explicitly "simplified"; its footnote says
changing templates are fully disclosed in the appendix, but the appendix contains
none. A second footnote promises baseline details in the appendix; those are also
absent.

## Result and arithmetic findings

- Twelve of 18 leakage-improvement cells round exactly from displayed cells; all
  18 are within 0.01 percentage points, so the other six are compatible with
  unreported source precision. The 31.91%/22.74%/9.23% mean performance
  improvements recompute. This verifies printed arithmetic only.
- Seventeen of 18 performance-improvement cells follow literal best-baseline
  ranking. The exception is decisive: FinAgent's TSLA MDD is printed as -9.36%,
  but FactFin 31.54% is marked best, InvestLM 36.88% second, and the 14.48%
  improvement is calculated from 36.88%. The prose separately changes FinRobot's
  TSLA MDD from +49.99% in the table to -49.99%.
- FactFin's mean Sharpe is only 1.2394x the mean per-asset best-baseline Sharpe;
  the paper's "1.4x higher" headline is unsupported by its table.
- Figure 3's +20.55%/+21.79% labels are percentage-point differences. Relative
  accuracy gains are 39.82% and 39.81%.
- A direct current-Yahoo endpoint calculation reproduces **0/6** Buy-and-Hold
  cells at two-decimal display precision under both close and adjusted close.
  Bitcoin is near, but still not exact. Provider revision is possible; more
  importantly, the paper omits the field, timestamp, adjustment, and execution
  rules needed to decide the target.

## Why the experiment remains unreproducible

FactFin lacks its executable code contract, RAG corpus/index/query, MCTS node and
reward definitions, counterfactual generators/weights/seeds, training split,
starting capital, quantities/weights, timing/fill price, numerical transaction
costs and slippage, risk-free rate/metric conventions, baseline forks/configs,
seeds/repetitions, and environment lock. The public record has no frozen Yahoo or
Alpaca rows, 2,000 benchmark questions, immutable model requests, generated
strategies, tree, actions, orders, fills, cash ledger, or dated NAV.

The benchmark scorer is internally unresolved: its equation requires exact answer
equality, while examples award interval, partial, magnitude, and qualitative
credit. Fine-tuning data cover Jan 2020-Dec 2022 while the stated test period lies
inside that range (Jan-Jun 2022), with no held-out-row definition. The two-period
agent decay test changes calendar regimes and treats similar aggregate market
returns as isolating memorization; that is a contamination warning, not a causal
identification strategy. PC/CI/IDS measure constructed sensitivity but are not,
without validation, unique measures of memorization, leakage, or causal learning.

Regenerate with `scripts/audit_factfin_paper.py`. `--strict` intentionally exits
nonzero while the end-to-end paper remains unreproduced.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch-root",
        type=Path,
        default=Path(os.environ.get("FACTFIN_AUDIT_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/profit_mirage_audit")),
    )
    parser.add_argument("--paper-pdf", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "paper_runs/paper_replication_audits/factfin",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scratch_root = args.scratch_root.resolve()
    paper_pdf = (args.paper_pdf or scratch_root / "downloads/profit_mirage_v1.pdf").resolve()
    manifest = build_audit(paper_pdf, scratch_root, args.output_dir.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return int(args.strict and not manifest["full_end_to_end_pipeline_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
