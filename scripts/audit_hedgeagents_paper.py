#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for HedgeAgents.

The audit pins the paper, its complete arXiv manuscript bundle, the authors'
static project repository, bounded public-artifact searches, and a later
author paper about temporal leakage in financial agents.  Manuscript builds,
website table matches, profile screenshots, and plotted curves are evidence,
not executions of the trading system.  No paper result receives replication
credit without the original implementation, frozen inputs, LLM traces,
orders, fills, and portfolio path.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]

TITLE = "HedgeAgents: A Balanced-aware Multi-agent Financial Trading System"
AUTHORS = ["Xiangyu Li", "Yawen Zeng", "Xiaofen Xing", "Jin Xu", "Xiangmin Xu"]
DOI = "10.1145/3701716.3715232"
DOI_URL = f"https://doi.org/{DOI}"
ARXIV_RECORD = "https://arxiv.org/abs/2502.13165v1"
ARXIV_PDF_URL = "https://arxiv.org/pdf/2502.13165v1"
ARXIV_SOURCE_URL = "https://arxiv.org/e-print/2502.13165v1"
AUTHOR_SITE = "https://hedgeagents.github.io/"
AUTHOR_REPOSITORY = "https://github.com/hedgeagents/hedgeagents.github.io"
LATER_AUTHOR_WARNING = "https://arxiv.org/abs/2510.07920v1"
OPENAI_DEV_DAY = "https://openai.com/index/new-models-and-developer-products-announced-at-devday/"
OPENAI_MODEL_CATALOG = "https://developers.openai.com/api/docs/models/all"

PAPER_SHA256 = "d51a97df37c27936ea69c3c951c7ac514c4dddd76bf509f866f2c647cd50505e"
PAPER_PAGES = 10
SOURCE_ARCHIVE_SHA256 = "74609167076592c8d8d7344a09f470736c62992ae9b7540bf81f01510fab713b"
SOURCE_FILE_COUNT = 20
SOURCE_FILE_BYTES = 1_924_454
SITE_HEAD = "329c5cc8613d91e517de4fbdb0dbc8476a356db5"
SITE_ARCHIVE_SHA256 = "f86c9d0562a31864ec4bc3d449af803b6048c2393a1130a351a2c657d3943ad2"
SITE_TREE_FILES = 46
SITE_TREE_BYTES = 21_503_635
REBUILD_1_SHA256 = "9df80446dbea80719f9d20fc647fc04bae79774d3a209b902e01e69de6e2cc67"
REBUILD_2_SHA256 = "05182919f8852b6017e587f54c3818918e7171eda9f81ab3ccae344392072743"
REBUILD_TEXT_SHA256 = "e22be9216e706031198bcddeac18449edf36860a659ec5734f2a326eebfe70fb"

DOWNLOAD_HASHES = {
    "arxiv_record.html": "a6c98bb5e4c5f06883dee5f178747c55974d81b423dbd8aae9669fc091d44fca",
    "hedgeagents_arxiv_v1.tar": SOURCE_ARCHIVE_SHA256,
    "hedgeagents_site_329c5cc.tar.gz": SITE_ARCHIVE_SHA256,
    "openai_models_all.html": "33d73c3abf466b8c7365d97b61fac485870da8892fa3fc3f9337475b50a07874",
    "profit_mirage_source_v1.tar": "f8888b5d281ada1b16a6ac32a43da031cc54d4afd1775e8909e5cf4ab65bd0c6",
    "profit_mirage_v1.pdf": "1024f16ced8e9b12c6a4f0c7bf56551a92da0d621507da621ee82ae68355aba5",
    "software_heritage_search_hedgeagents.json": "ee151eb14ed9c72c26521c2af5bfaf2144465bffcd32cf71371af29fbfdc4ad7",
    "wayback_hedgeagents_site.json": "a8add3f160bf2a565d2e34741ee106278e86d89df3e6ab9232774645f52cb84a",
    "wayback_orangecat0616.json": "b0276a108dc68d9c5c975826aba04ca4b40b09da6b4465e8278421efe16a445e",
    "wayback_orangecat0616_20251205_decoded.html": "58c86a3a6e3552f076103c8f71151ae31cf544b336720376db027032344ff537",
    "xiangyuli616_homepage.html": "2a1e21671b217034f8222936d8c256abe61c02756510fb72dff21466a95ff952",
    "yawenzeng_homepage.html": "2bd659bd8f1e69e37f0b22504e5b81c3a35ef0cedfc960380061ac1838696c4d",
}

GITHUB_HASHES = {
    "forks.json": "89a379e5c7b98518741b9fefa5ae3c45f85aeefaf6a713f0f16fc24edddc588a",
    "owner.json": "cfb432e10514c1c96434331288efe65150c2e687262a61ec921f13087b57069a",
    "owner_repos.json": "73d290e6a1f3fd7b2d2e10e7610edef47411f727209efe991b9421f00b6add4c",
    "search_repositories.json": "6e0149530d7bfd5defdaf1255c804550eeaae8e74bed4b0b718a9cd169aa6cc2",
}

METRICS = ("ARR_pct", "TR_pct", "SR", "CR", "SoR", "MDD_pct", "Vol_pct", "ENT", "ENB")

MAIN_RESULTS: list[tuple[str, str, tuple[float | None, ...]]] = [
    ("Market Trends", "Bitcoin", (12.92, 43.97, 0.54, 1.19, 12.49, 76.63, 3.40, None, None)),
    ("Market Trends", "FX", (4.08, 12.74, 0.61, 0.93, 11.99, 15.56, 0.38, None, None)),
    ("Market Trends", "DJIA", (7.64, 24.70, 0.59, 1.06, 11.72, 21.94, 0.78, None, None)),
    ("Rule-based", "MV", (13.03, 44.39, 0.71, 1.25, 16.14, 32.04, 1.13, 1.09, 1.02)),
    ("Rule-based", "ZMR", (-7.25, -20.21, -0.52, -3.13, -5.15, 61.52, 1.98, 1.55, 1.11)),
    ("Rule-based", "TSM", (19.13, 69.09, 0.78, 1.53, 18.21, 39.14, 1.55, 1.10, 1.09)),
    ("RL-based", "SAC", (24.71, 93.94, 1.16, 3.12, 23.15, 21.56, 1.16, 1.62, 1.14)),
    ("RL-based", "DeepTrader", (32.78, 134.11, 1.41, 4.06, 30.43, 20.95, 1.21, 2.02, 1.30)),
    ("RL-based", "AlphaMix+", (37.59, 160.47, 1.62, 3.69, 35.52, 25.56, 1.17, 2.93, 1.22)),
    ("LLM-based", "FinGPT", (34.22, 141.82, 1.93, 7.64, 39.57, 17.08, 8.76, 1.76, 1.33)),
    ("LLM-based", "FinMem", (47.67, 221.99, 1.20, 4.02, 25.42, 32.39, 2.16, 1.99, 1.25)),
    ("LLM-based", "FinAgent", (53.54, 261.98, 1.80, 4.52, 39.12, 28.24, 1.42, 2.85, 1.41)),
    ("Ours", "HedgeAgents", (71.60, 405.34, 2.41, 11.02, 58.00, 14.21, 1.30, 3.13, 1.53)),
    ("Improvement", "Improvement", (33.75, 54.72, 24.49, 44.28, 46.58, 16.76, None, 6.85, 8.51)),
]

ABLATION_RESULTS: list[tuple[str, tuple[float, ...]]] = [
    ("ESC", (43.88, 197.88, 1.90, 4.89, 42.20, 21.70, 1.12, 2.56, 1.23)),
    ("BAC", (45.58, 208.52, 1.67, 4.54, 36.36, 24.68, 1.34, 2.39, 1.17)),
    ("EMC", (40.97, 180.13, 1.96, 5.07, 39.58, 19.59, 1.02, 1.97, 1.08)),
    ("BAC+EMC", (50.68, 242.11, 2.01, 6.92, 45.60, 17.26, 1.19, 2.61, 1.28)),
    ("ESC+EMC", (44.57, 202.17, 2.24, 8.78, 55.01, 12.02, 0.94, 2.72, 1.39)),
    ("ESC+BAC", (59.81, 308.12, 1.93, 5.69, 40.16, 24.44, 1.44, 2.91, 1.42)),
    ("ESC+BAC+EMC", (71.60, 405.34, 2.41, 11.02, 58.00, 8.68, 1.30, 3.13, 1.53)),
]

LLM_RESULTS: list[tuple[str, tuple[float, ...]]] = [
    ("Chat-GLM-6B", (49.14, 231.73, 2.88, 12.26, 66.64, 9.19, 0.78, 2.46, 1.25)),
    ("Baichuan-13B", (53.24, 259.85, 2.39, 8.85, 55.59, 13.81, 1.02, 2.99, 1.46)),
    ("Qwen-72B", (61.34, 319.99, 2.16, 8.01, 50.21, 17.44, 1.29, 2.35, 1.18)),
    ("Gemini1.5 Pro", (68.61, 379.37, 2.49, 11.48, 59.94, 13.12, 1.21, 3.31, 1.57)),
    ("gpt-3.5-turbo-16k", (65.44, 352.81, 2.27, 8.44, 53.49, 17.35, 1.29, 2.93, 1.49)),
    ("gpt-4-1106-preview", (71.60, 405.34, 2.41, 11.02, 58.00, 14.21, 1.30, 3.13, 1.53)),
]

PROFILE_PERMISSIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "Dave": {
        "action": ("Buy", "Sell", "Hold", "AdjustQuantity", "AdjustPrice", "SetTradingConditions"),
        "tool": (
            "Technical Indicator Analysis", "Cryptocurrency Market Analysis", "Blockchain Event Impact Assessment",
            "Sentiment Analysis from Social Media", "Algorithmic Trading Strategies", "Regulatory Change Impact Analysis",
        ),
        "scope": ("Bitcoin Historical Price Data", "Bitcoin News Data"),
    },
    "Bob": {
        "action": ("Buy", "Sell", "Hold", "AdjustQuantity", "AdjustPrice", "SetTradingConditions"),
        "tool": (
            "Technical Indicator Analysis", "Economic Indicator Forecasting", "Corporate Earnings Analysis",
            "Dow Jones Index Component Tracking", "Sector Performance Evaluation", "Risk-Adjusted Return Analysis",
            "Portfolio Diversification Tools",
        ),
        "scope": ("DJ30 Historical Price Data", "DJ30 News Data", "DJ30 Market Trends"),
    },
    "Emily": {
        "action": ("Buy", "Sell", "Hold", "AdjustQuantity", "AdjustPrice", "SetTradingConditions"),
        "tool": (
            "Technical Indicator Analysis", "Central Bank Policy Analysis", "Global Macroeconomic Trend Analysis",
            "Forex Market Liquidity Assessment", "Currency Pair Correlation Matrix", "Geopolitical Risk Assessment",
            "Interest Rate Differential Analysis",
        ),
        "scope": ("FX Historical Price Data", "FX News Data"),
    },
    "Otto": {
        "action": (
            "Execute Asset Allocation", "Initiate Risk Assessment Protocols", "Authorize Capital Deployment",
            "Enforce Compliance with Regulatory Standards",
        ),
        "tool": (
            "Asset Allocation Optimization", "Risk Management Frameworks", "Portfolio Stress Testing",
            "Derivatives Strategy Formulation", "Fund Performance Evaluation",
        ),
        "scope": ("All Historical Price Data", "All News Data", "All Market Trends"),
    },
}

PROFILE_IMAGE_SHA256 = {
    "Dave": "c305d80f2a5db5328c710281ac56b8b9567271fc54ce65bf2cb59adb7071b4a8",
    "Bob": "9d59eb994037b53afc926c5d00a603b2dc15a13cd23d81d84b1e30f48c1f3a02",
    "Emily": "6bbd91645d4ec42619b4fd128d3e068a92ed3d3376aaf8c64479b907f8fda3ef",
    "Otto": "0b925af7e3639f854bf474b2893ec1d6f8592ad26508e8357b5f0621cf050127",
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


def pdf_text(path: Path, expected_hash: str, pages: int, markers: Sequence[str]) -> str:
    validate_hash(path, expected_hash, "paper PDF")
    reader = PdfReader(path)
    if len(reader.pages) != pages:
        raise ValueError(f"paper page count changed: {len(reader.pages)}")
    text = " ".join(" ".join((page.extract_text() or "").split()) for page in reader.pages)
    for marker in markers:
        if marker not in text:
            raise ValueError(f"paper marker missing: {marker}")
    return text


def pdftotext_hash(path: Path) -> str:
    completed = subprocess.run(
        ["pdftotext", str(path), "-"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def pdf_without_trailer_id(path: Path) -> bytes:
    payload = path.read_bytes()
    normalized, replacements = re.subn(
        rb"/ID\s*\[\s*<[0-9A-F]+>\s*<[0-9A-F]+>\s*\]", b"/ID [<ID> <ID>]", payload
    )
    if replacements != 1:
        raise ValueError(f"expected one PDF trailer ID in {path.name}, found {replacements}")
    return normalized


def source_inventory(archive: Path, source_dir: Path) -> list[dict[str, Any]]:
    validate_hash(archive, SOURCE_ARCHIVE_SHA256, "arXiv source archive")
    rows: list[dict[str, Any]] = []
    with tarfile.open(archive, "r:*") as bundle:
        members = sorted((member for member in bundle.getmembers() if member.isfile()), key=lambda member: member.name)
        if len(members) != SOURCE_FILE_COUNT or sum(member.size for member in members) != SOURCE_FILE_BYTES:
            raise ValueError("arXiv source inventory count/size changed")
        for member in members:
            path = source_dir / member.name
            if not path.is_file() or path.stat().st_size != member.size:
                raise ValueError(f"source extraction mismatch: {member.name}")
            role = (
                "primary_manuscript_source" if member.name == "hedge_www.tex" else
                "published_figure" if re.fullmatch(r"fig(?:\d+|6_[123])\.pdf", member.name) else
                "bibliography_or_typesetting_support"
            )
            rows.append({
                "path": member.name,
                "bytes": member.size,
                "sha256": sha256(path),
                "role": role,
                "is_executable_system_source": False,
                "replication_credit": False,
            })
    return rows


def _strip_html(cell: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", cell)).replace("🥇", "").replace("🥈", "").replace("🥉", "").split())


def parse_site_leaderboard(index_html: str) -> dict[str, tuple[float, ...]]:
    match = re.search(r'<table class="js-sort-table" id="results">(.*?)</table>', index_html, re.S)
    if not match:
        raise ValueError("author-site leaderboard not found")
    parsed: dict[str, tuple[float, ...]] = {}
    for row_html in re.findall(r"<tr>(.*?)</tr>", match.group(1), re.S)[1:]:
        cells = [_strip_html(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]
        if len(cells) != 13:
            raise ValueError(f"unexpected author-site leaderboard width: {len(cells)}")
        model = re.sub(r"\s+[\W_]+$", "", cells[1]).strip()
        parsed[model] = tuple(float(value) for value in cells[4:13])
    if len(parsed) != 10:
        raise ValueError(f"expected 10 author-site leaderboard rows, got {len(parsed)}")
    return parsed


def performance_ledger(site_results: Mapping[str, tuple[float, ...]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    main_lookup = {model: values for _, model, values in MAIN_RESULTS}
    for model, site_values in site_results.items():
        paper_values = main_lookup.get(model)
        if paper_values is None or any(value is None for value in paper_values):
            raise ValueError(f"unexpected site model: {model}")
        if tuple(float(value) for value in paper_values) != tuple(site_values):
            raise ValueError(f"site/paper leaderboard mismatch for {model}")

    def append_table(table: str, category: str, variant: str, values: Sequence[float | None], own: bool) -> None:
        for metric, value in zip(METRICS, values):
            if value is None:
                continue
            corroborated = table == "main" and variant in site_results
            rows.append({
                "table": table,
                "category": category,
                "variant": variant,
                "metric": metric,
                "paper_value": value,
                "hedgeagents_system_output": own,
                "arxiv_source_verified": True,
                "author_site_corroborated": corroborated,
                "native_reproduced_value": "",
                "paper_result_credit": False,
                "status": "author_site_duplicate_zero_credit" if corroborated else "paper_value_only_zero_credit",
                "note": "No released native trajectory, orders, fills, or metric-generation path.",
            })

    for category, variant, values in MAIN_RESULTS:
        append_table("main", category, variant, values, variant == "HedgeAgents")
    for variant, values in ABLATION_RESULTS:
        append_table("conference_ablation", "HedgeAgents variant", variant, values, True)
    for variant, values in LLM_RESULTS:
        append_table("llm_backbone", "HedgeAgents backbone", variant, values, True)

    if len(rows) != 236:
        raise ValueError(f"expected 236 displayed numeric table cells, got {len(rows)}")
    return rows


def profile_permission_rows(site_repo: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    image_index = {"Dave": 1, "Bob": 2, "Emily": 3, "Otto": 4}
    for agent, groups in PROFILE_PERMISSIONS.items():
        image = site_repo / f"static/images/agent{image_index[agent]}.png"
        validate_hash(image, PROFILE_IMAGE_SHA256[agent], f"{agent} profile image")
        for permission_type, names in groups.items():
            for name in names:
                rows.append({
                    "agent": agent,
                    "permission_type": permission_type,
                    "name": name,
                    "agent_named_count": len(names),
                    "profile_image": image.name,
                    "profile_image_sha256": PROFILE_IMAGE_SHA256[agent],
                    "source_format": "author_site_screenshot_manual_transcription",
                    "implementation_released": False,
                    "faithful_replication_credit": False,
                })
    return rows


def prompt_inventory() -> list[dict[str, Any]]:
    return [
        {
            "prompt": "simplified_single_agent_decision",
            "location": "paper Section 3.3",
            "publication_form": "verbatim simplified template",
            "recovered_text": "You are {Dave Profile}. The market environment today includes {Prices}, {News}. Through financial analysis tools, {Tool Results} can be obtained. The output format should be JSON, such as {Examples}.",
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "partial_template_only",
        },
        {
            "prompt": "decision_phi_D",
            "location": "paper Equation 2",
            "publication_form": "symbol only",
            "recovered_text": "",
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "missing_exact_prompt",
        },
        {
            "prompt": "budget_allocation_phi_rho",
            "location": "paper Section 3.4.1",
            "publication_form": "symbol only",
            "recovered_text": "",
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "missing_exact_prompt",
        },
        {
            "prompt": "experience_sharing_phi_c",
            "location": "paper Section 3.4.2",
            "publication_form": "symbol only",
            "recovered_text": "",
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "missing_exact_prompt",
        },
        {
            "prompt": "extreme_market_phi_B",
            "location": "paper Section 3.4.3",
            "publication_form": "symbol only",
            "recovered_text": "",
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "missing_exact_prompt",
        },
        *[
            {
                "prompt": f"profile_{agent.lower()}",
                "location": f"author site agent{index}.png",
                "publication_form": "XML-like profile screenshot",
                "recovered_text": "named actions/tools/scopes transcribed separately; full description remains image evidence",
                "runtime_values_released": False,
                "actual_request_released": False,
                "actual_response_released": False,
                "status": "author_profile_image_not_runtime_prompt",
            }
            for index, agent in enumerate(("Dave", "Bob", "Emily", "Otto"), start=1)
        ],
    ]


def method_specification_audit() -> list[dict[str, str]]:
    rows = [
        ("asset_classes", "Bitcoin, foreign exchange, DJ30 component stocks", "specified_high_level_only", "Exact tickers, currency pairs, and constituent vintage are absent."),
        ("asset_universe", "not enumerated", "missing_exact_universe", "Cannot reconstruct the traded panel or survivorship treatment."),
        ("price_source", "Yahoo Finance daily OHLCV and adjusted close", "specified_provider_schema_only", "Original query, response, time zone, corporate-action snapshot, and field used for fills are absent."),
        ("news_source", "Alpaca News API; processed daily headlines", "specified_provider_only", "Queries, subscriptions, article IDs, timestamps, filters, and frozen rows are absent."),
        ("technical_indicators", "60 standard technical indicators", "missing_indicator_list_and_parameters", "Names, windows, warm-up, library, and versions are absent."),
        ("train_test_split", "2015-01-01..2020-12-31 train; 2021-01-01..2023-12-31 test", "specified_dates", "Dates alone do not identify rows or exchange calendars."),
        ("llm_model", "gpt-4-1106-preview", "specified_historical_snapshot_now_deprecated", "Exact snapshot is no longer in the current standard model catalog."),
        ("llm_temperature", "0.7", "specified", "Seed, max tokens, top-p, stop sequences, retries, and system messages are absent."),
        ("embedding_model", "text-embedding-3-large", "specified_alias", "No embedding snapshot, batching, normalization, or vector-store implementation."),
        ("memory_retrieval", "top-k=5 across three memory types", "specified_high_level_only", "Similarity metric, chunking, insertion, deduplication, tie handling, and exact memory rows are absent."),
        ("agent_profiles", "four author-site profile screenshots", "partial_author_image_evidence", "Descriptions and permissions are visible, but no executable profile or serialization is released."),
        ("tools", "23 unique names recoverable from profile screenshots", "names_recovered_implementations_missing", "No tool function, signature, parameters, data contract, or output is released."),
        ("actions", "paper says 8; screenshots expose 10 unique names", "conflicting_action_contract", "No mapping reconciles the counts or defines order semantics."),
        ("budget_allocation_conference", "30-day cycle", "specified_cadence_partial_logic", "Risk coefficients, alpha, covariance window, solver, and failure handling are absent."),
        ("experience_sharing_conference", "end of each investment cycle; multi-round", "missing_numeric_cadence_and_rounds", "Cycle definition, round count, selection rule, and update prompt are absent."),
        ("extreme_market_conference", "daily amplitude >5% or cumulative three-day amplitude >10%", "specified_trigger_partial_logic", "Amplitude definition, price field, boundary rule, and simultaneous-event behavior are absent."),
        ("risk_objective", "expected return - lambda1*risk - lambda2*CVaR", "missing_numeric_parameters_and_solver", "lambda1, lambda2, alpha, covariance estimator, and optimization implementation are absent."),
        ("initial_capital", "not stated", "missing_initial_capital", "Cannot recreate quantities, cash, or reported portfolio path."),
        ("trade_fill_timing_and_price", "not stated", "missing_fill_model", "Signal-to-fill timing and executable price are unknown."),
        ("position_sizing_and_rounding", "actions mention quantity/price adjustment", "missing_position_sizing", "Allocation-to-order conversion, fractional shares, minimum lots, and cash rules are absent."),
        ("transaction_costs", "not stated", "missing_transaction_costs", "Fees, commissions, taxes, spread, and funding are absent."),
        ("slippage", "not stated", "missing_slippage", "No execution-impact convention."),
        ("long_short_leverage_constraints", "not stated", "missing_trading_constraints", "Shorting, leverage, borrowing, options, and exposure limits are unresolved."),
        ("metric_formulas", "nine metrics named; citations only", "missing_metric_conventions", "Risk-free rate, annualization, return frequency, ddof, and ENT/ENB definitions are absent."),
        ("baseline_implementations", "names/citations; Optuna optimization", "missing_baseline_commits_and_configs", "Forks, adapters, search spaces, trials, objectives, seeds, and selected values are absent."),
        ("randomness", "not stated", "missing_seeds_and_repetitions", "One curve per method is shown without run count or uncertainty."),
        ("runtime_environment", "not released", "missing_environment_and_lock", "No dependency lock, Python version, hardware manifest, or runner."),
        ("actual_llm_requests", "not released", "missing_runtime_requests", "Templates and screenshots cannot establish historical inputs or model responses."),
        ("native_actions_orders_fills", "not released", "missing_native_trade_ledger", "Cannot replay daily decisions or validate execution."),
        ("native_equity_curves", "figures only", "missing_exact_portfolio_trajectory", "Plots cannot substitute for dated machine-readable values."),
    ]
    return [
        {"dimension": dimension, "paper_or_author_statement": statement, "status": status, "replication_impact": impact}
        for dimension, statement, status, impact in rows
    ]


def internal_consistency_audit() -> list[dict[str, Any]]:
    sr_improvement = (2.41 / 1.93 - 1.0) * 100.0
    no_esc, no_bac, no_emc = 2.01, 2.24, 1.93
    synergy = [(2.41 / value - 1.0) * 100.0 for value in (no_esc, no_bac, no_emc)]
    return [
        {
            "claim_id": "full_system_mdd",
            "location": "main Table 1 / ablation Table 2 / LLM Table 3 / prose",
            "paper_claim": "14.21 in Table 1, Table 3, and prose; 8.68 in the full-system ablation row",
            "recomputed_or_comparison": "The no-EMC prose uses 14.21 as its reference, independently supporting 14.21.",
            "status": "hard_internal_conflict",
            "replication_implication": "No unambiguous published MDD target for the full ablation configuration.",
        },
        {
            "claim_id": "per_agent_tool_count",
            "location": "Figure 3 caption / author-site profiles",
            "paper_claim": "Each agent is equipped with 23 tools.",
            "recomputed_or_comparison": "Profiles name Dave=6, Bob=7, Emily=7, Otto=5; 23 unique names system-wide after deduplicating Technical Indicator Analysis.",
            "status": "author_source_scope_conflict",
            "replication_implication": "The executable tool contract and per-agent availability are not identified.",
        },
        {
            "claim_id": "per_agent_action_count",
            "location": "Figure 3 caption / author-site profiles",
            "paper_claim": "Each agent executes 8 actions.",
            "recomputed_or_comparison": "Profiles name 6 actions for each analyst, 4 for Otto, and 10 unique action names system-wide.",
            "status": "author_source_count_conflict",
            "replication_implication": "The action schema cannot be reconstructed without an unpublished mapping.",
        },
        {
            "claim_id": "main_table_sr_improvement",
            "location": "Table 1 Improvement row",
            "paper_claim": "24.49%",
            "recomputed_or_comparison": f"(2.41 / 1.93 - 1)*100 = {sr_improvement:.4f}% from displayed cells",
            "status": "not_roundable_from_displayed_values",
            "replication_implication": "May reflect hidden precision, but no underlying values are released.",
        },
        {
            "claim_id": "wins_all_metrics",
            "location": "contribution and overall-performance prose",
            "paper_claim": "wins across all metrics / optimal performance on all metrics",
            "recomputed_or_comparison": "HedgeAgents Vol=1.30 is not optimal; MV=1.13 and several other methods are lower, and the paper does not bold HedgeAgents Vol.",
            "status": "claim_contradicted_by_own_table",
            "replication_implication": "Headline superiority must exclude volatility or be qualified.",
        },
        {
            "claim_id": "conference_synergy_sr_percentages",
            "location": "conference ablation prose",
            "paper_claim": "41.29%, 60.65%, and 19.72%",
            "recomputed_or_comparison": "Full SR versus no-ESC/no-BAC/no-EMC gives " + ", ".join(f"{value:.2f}%" for value in synergy) + " improvements.",
            "status": "unsupported_by_displayed_ablation_values",
            "replication_implication": "The prose percentages cannot be regenerated from the published table.",
        },
        {
            "claim_id": "daily_llm_cost",
            "location": "LLM-backbone prose",
            "paper_claim": "$15 over three years, averaging 2 cents/day",
            "recomputed_or_comparison": "$15 / (3*365) = 1.37 cents/day; exact tokens, calls, and invoices are absent.",
            "status": "coarse_arithmetic_and_unverifiable_cost_claim",
            "replication_implication": "No cost reproduction is possible.",
        },
        {
            "claim_id": "risk_equation_symbols_and_cvar",
            "location": "budget-allocation equations",
            "paper_claim": "Risk equation uses I_ij while prose defines sigma_ij; CVaR integral is written from 1 to alpha.",
            "recomputed_or_comparison": "No convention, alpha, covariance window, or code resolves the symbol and integration-bound ambiguities.",
            "status": "mathematical_specification_ambiguous",
            "replication_implication": "Budget weights cannot be faithfully recomputed.",
        },
    ]


def figure_inventory() -> list[dict[str, Any]]:
    data = [
        (1, "fig1.pdf", 1, "PRUDEX radar", "10 methods", "F2PRUDEX.png"),
        (2, "fig2.pdf", 6, "three score panels and three cumulative-return panels", "9 baselines / 10 curve methods", "extremelymarket.png"),
        (3, "fig3.pdf", 1, "system architecture", "not applicable", "frameworkhtml.png"),
        (4, "fig4.pdf", 1, "overall cumulative returns", "13 series", "ALLCR.png"),
        (5, "fig5.pdf", 6, "LLM-backbone metric radars", "6 backbones x 9 metrics", ""),
        (6, "fig6_1.pdf;fig6_2.pdf;fig6_3.pdf", 3, "single-asset cumulative returns", "11 series per panel", ""),
        (7, "fig7.pdf", 1, "single-agent workflow example", "not applicable", "vis1.png (richer layout)"),
        (8, "fig8.pdf", 1, "extreme-market workflow example", "not applicable", "vis4.png (richer layout)"),
        (9, "fig9.pdf", 1, "conference-ablation cumulative returns", "7 series", ""),
        (10, "fig10.pdf", 1, "LLM-backbone cumulative returns", "6 series", ""),
        (11, "fig11.pdf", 2, "memory ablation bars and t-SNE", "4 bars; 3 scatter classes", ""),
        (12, "fig12.pdf", 1, "Q1-Q3 2024 cumulative return and EMC events", "1 curve; 36 claimed markers", ""),
    ]
    return [
        {
            "figure": number,
            "source_files": files,
            "panels": panels,
            "output_type": output_type,
            "labeled_series_or_marks": series,
            "author_site_correspondence": site,
            "exact_dated_underlying_values_released": False,
            "figure_digitization_is_replication": False,
            "status": "published_visual_only_zero_result_credit",
        }
        for number, files, panels, output_type, series, site in data
    ]


def artifact_access_audit() -> list[dict[str, Any]]:
    return [
        {"artifact": "arxiv_v1_source", "availability": "20 manuscript/typesetting files including 14 figure PDFs", "tier": "paper source only", "system_source_credit": False, "note": "No trading implementation or data."},
        {"artifact": "author_project_repository", "availability": f"reachable at {SITE_HEAD}; 46 files", "tier": "R1 static documentation", "system_source_credit": False, "note": "HTML, images, JavaScript/CSS; no runner, package manifest, or trading code."},
        {"artifact": "author_site_leaderboard", "availability": "90 exact numeric duplicates of main Table 1 method rows", "tier": "author corroboration", "system_source_credit": False, "note": "Duplicated results are not regenerated results."},
        {"artifact": "author_site_profiles", "availability": "four XML-like screenshots", "tier": "partial specification", "system_source_credit": False, "note": "Names tools/actions/scopes but releases no implementation."},
        {"artifact": "author_site_workflow_images", "availability": "four workflow images and three general-experience snapshots", "tier": "qualitative output evidence", "system_source_credit": False, "note": "No structured timestamps, LLM request IDs, or complete traces."},
        {"artifact": "author_site_mathvista_residue", "availability": "6,141-record VQA explorer plus MathVista assets", "tier": "unrelated template residue", "system_source_credit": False, "note": "Explicitly excluded from HedgeAgents data and code evidence."},
        {"artifact": "linked_first_author_github", "availability": "homepage linked OrangeCat0616; current URL is 404; archived Dec 2025 profile said no public repos", "tier": "bounded negative search", "system_source_credit": False, "note": "Not proof that private/deleted artifacts never existed."},
        {"artifact": "project_owner_github", "availability": "one public repository: the static project site", "tier": "bounded negative search", "system_source_credit": False, "note": "GitHub API snapshot."},
        {"artifact": "software_heritage_search", "availability": "project site and its one fork only", "tier": "archival discovery", "system_source_credit": False, "note": "No separate system origin recovered."},
        {"artifact": "later_author_profit_mirage_paper", "availability": "paper/source pinned; no HedgeAgents runtime artifact", "tier": "validity warning", "system_source_credit": False, "note": "Does not directly measure HedgeAgents in its pre/post temporal-decay experiment."},
        {"artifact": "exact_llm_snapshot", "availability": "gpt-4-1106-preview historical preview; current catalog marks GPT-4 Turbo Preview deprecated", "tier": "unavailable exact dependency", "system_source_credit": False, "note": "A substitute model cannot receive exact-replication credit."},
    ]


def discovery_evidence(downloads: Path) -> list[dict[str, Any]]:
    api = downloads / "github_api"
    owner = json.loads((api / "owner.json").read_text(encoding="utf-8"))
    repos = json.loads((api / "owner_repos.json").read_text(encoding="utf-8"))
    forks = json.loads((api / "forks.json").read_text(encoding="utf-8"))
    search = json.loads((api / "search_repositories.json").read_text(encoding="utf-8"))
    swh = json.loads((downloads / "software_heritage_search_hedgeagents.json").read_text(encoding="utf-8"))
    archived_author = (downloads / "wayback_orangecat0616_20251205_decoded.html").read_text(encoding="utf-8")
    if "doesn&#39;t have any public repositories yet" not in archived_author:
        raise ValueError("archived author GitHub boundary marker missing")
    rows = [
        {"source": "GitHub API owner", "query_or_url": "users/hedgeagents", "result": f"type={owner['type']}; public_repos={owner['public_repos']}", "system_implementation_recovered": False, "negative_search_limit": "current public inventory only; not proof of nonexistence"},
        {"source": "GitHub API owner repos", "query_or_url": "users/hedgeagents/repos", "result": "; ".join(item["full_name"] for item in repos), "system_implementation_recovered": False, "negative_search_limit": "one static site; not proof of private/deleted artifacts"},
        {"source": "GitHub API forks", "query_or_url": "repos/hedgeagents/hedgeagents.github.io/forks", "result": "; ".join(item["full_name"] for item in forks), "system_implementation_recovered": False, "negative_search_limit": "fork inventory only"},
        {"source": "GitHub repository search", "query_or_url": "HedgeAgents in name,description,readme", "result": f"{search['total_count']} current matches; only hedgeagents/hedgeagents.github.io is author-controlled", "system_implementation_recovered": False, "negative_search_limit": "repository metadata search, not authenticated code search"},
        {"source": "Software Heritage", "query_or_url": "origin/search/hedgeagents", "result": f"{len(swh)} origins: project site and fork", "system_implementation_recovered": False, "negative_search_limit": "indexed public origins only"},
        {"source": "Wayback project site", "query_or_url": "hedgeagents.github.io/*", "result": "Feb 2025 capture contains the same static page/assets", "system_implementation_recovered": False, "negative_search_limit": "captured URLs only"},
        {"source": "First-author homepage", "query_or_url": "xiangyuli616.github.io", "result": "HedgeAgents links only to arXiv, DOI, and static project site; GitHub link points to OrangeCat0616", "system_implementation_recovered": False, "negative_search_limit": "homepage links only"},
        {"source": "Archived linked GitHub profile", "query_or_url": "github.com/OrangeCat0616", "result": "Dec 2025 capture: no public repositories", "system_implementation_recovered": False, "negative_search_limit": "single archived capture; current account URL is 404"},
        {"source": "ArXiv source", "query_or_url": ARXIV_SOURCE_URL, "result": "20 manuscript/typesetting files", "system_implementation_recovered": False, "negative_search_limit": "submission bundle only"},
        {"source": "Author-site commented links", "query_or_url": AUTHOR_SITE, "result": "Paper/Code/Dataset buttons are commented placeholders and self-link to the page", "system_implementation_recovered": False, "negative_search_limit": "static page state at pinned commit"},
    ]
    return rows


def validate_site_repo(site_repo: Path) -> str:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=site_repo, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    if head != SITE_HEAD:
        raise ValueError(f"author site HEAD changed: {head}")
    listing = subprocess.run(
        ["git", "ls-tree", "-rl", "HEAD"], cwd=site_repo, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.splitlines()
    if len(listing) != SITE_TREE_FILES:
        raise ValueError(f"author site tree count changed: {len(listing)}")
    byte_count = sum(int(line.split(maxsplit=4)[3]) for line in listing)
    if byte_count != SITE_TREE_BYTES:
        raise ValueError(f"author site byte count changed: {byte_count}")
    index = (site_repo / "index.html").read_text(encoding="utf-8")
    filters = (site_repo / "visualizer/data/filters_num.json").read_text(encoding="utf-8")
    data_public = site_repo / "visualizer/data/data_public.js"
    if "All (6141)" not in filters or data_public.stat().st_size != 5_207_209:
        raise ValueError("MathVista/VQA template residue boundary changed")
    if "<!--<span class=\"link-block\">" not in index or "<span>Code</span>" not in index:
        raise ValueError("commented code-link evidence changed")
    return index


def build_audit(paper_pdf: Path, scratch_root: Path, output_dir: Path) -> dict[str, Any]:
    downloads = scratch_root / "downloads"
    source_dir = scratch_root / "source_v1"
    site_repo = scratch_root / "site_repo"
    validate_hashed_files(downloads, DOWNLOAD_HASHES, "downloads")
    validate_hashed_files(downloads / "github_api", GITHUB_HASHES, "github_api")
    paper = pdf_text(
        paper_pdf, PAPER_SHA256, PAPER_PAGES,
        (TITLE, "gpt-4-1106-preview", "405.34", "total cost of $15", "Total Return of 68.44%"),
    )
    if len(paper) < 20_000:
        raise ValueError("paper text extraction unexpectedly short")
    source_rows = source_inventory(downloads / "hedgeagents_arxiv_v1.tar", source_dir)
    tex = (source_dir / "hedge_www.tex").read_text(encoding="utf-8")
    for marker in ("<Simplified Prompt Template>", "GPT-4-1106-preview", "\\textbf{8.68}", "\\textbf{14.21}"):
        if marker not in tex:
            raise ValueError(f"manuscript source marker missing: {marker}")
    validate_hash(downloads / "hedgeagents_site_329c5cc.tar.gz", SITE_ARCHIVE_SHA256, "author site archive")
    site_index = validate_site_repo(site_repo)
    site_results = parse_site_leaderboard(site_index)
    performance_rows = performance_ledger(site_results)
    permission_rows = profile_permission_rows(site_repo)
    prompt_rows = prompt_inventory()
    method_rows = method_specification_audit()
    consistency_rows = internal_consistency_audit()
    figure_rows = figure_inventory()
    access_rows = artifact_access_audit()
    discovery_rows = discovery_evidence(downloads)

    rebuild_1 = source_dir / "deterministic_build_1/hedge_www.pdf"
    rebuild_2 = source_dir / "deterministic_build_2/hedge_www.pdf"
    validate_hash(rebuild_1, REBUILD_1_SHA256, "first deterministic manuscript rebuild")
    validate_hash(rebuild_2, REBUILD_2_SHA256, "second deterministic manuscript rebuild")
    if pdftotext_hash(rebuild_1) != REBUILD_TEXT_SHA256 or pdftotext_hash(rebuild_2) != REBUILD_TEXT_SHA256:
        raise ValueError("deterministic rebuild extracted text changed")
    if pdf_without_trailer_id(rebuild_1) != pdf_without_trailer_id(rebuild_2):
        raise ValueError("deterministic rebuilds differ by more than trailer ID")
    later_text = " ".join(
        " ".join((page.extract_text() or "").split())
        for page in PdfReader(downloads / "profit_mirage_v1.pdf").pages
    )
    for marker in ("agent architecture Hedge-Agents", "Backtesting vs. Generalization", "five state-of- the-art LLM-based methods"):
        if marker not in later_text:
            raise ValueError(f"later-author warning marker missing: {marker}")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "paper_source_inventory.csv", source_rows)
    write_csv(output_dir / "artifact_access_audit.csv", access_rows)
    write_csv(output_dir / "discovery_evidence.csv", discovery_rows)
    write_csv(output_dir / "published_performance_ledger.csv", performance_rows)
    write_csv(output_dir / "profile_permissions.csv", permission_rows)
    write_csv(output_dir / "prompt_inventory.csv", prompt_rows)
    write_csv(output_dir / "method_specification_audit.csv", method_rows)
    write_csv(output_dir / "internal_consistency_audit.csv", consistency_rows)
    write_csv(output_dir / "figure_inventory.csv", figure_rows)

    source_provenance = {
        "title": TITLE,
        "authors": AUTHORS,
        "doi": DOI,
        "doi_url": DOI_URL,
        "arxiv_record": ARXIV_RECORD,
        "arxiv_pdf_url": ARXIV_PDF_URL,
        "arxiv_source_url": ARXIV_SOURCE_URL,
        "arxiv_version": "v1 only; submitted 2025-02-17 04:13:19 UTC",
        "license": "CC BY 4.0",
        "official_pdf_sha256": PAPER_SHA256,
        "official_pdf_pages": PAPER_PAGES,
        "arxiv_source_sha256": SOURCE_ARCHIVE_SHA256,
        "arxiv_source_files": SOURCE_FILE_COUNT,
        "arxiv_source_file_bytes": SOURCE_FILE_BYTES,
        "author_site": AUTHOR_SITE,
        "author_repository": AUTHOR_REPOSITORY,
        "author_repository_head": SITE_HEAD,
        "author_repository_archive_sha256": SITE_ARCHIVE_SHA256,
        "author_repository_tree_files": SITE_TREE_FILES,
        "author_repository_tree_bytes": SITE_TREE_BYTES,
        "first_deterministic_rebuild_sha256": REBUILD_1_SHA256,
        "second_deterministic_rebuild_sha256": REBUILD_2_SHA256,
        "pdftotext_sha256_both_rebuilds": REBUILD_TEXT_SHA256,
        "rebuild_comparison": "raw PDFs differ only in the generated PDF trailer ID; extracted text is identical",
        "rebuild_parameters": {"latex_passes": 3, "SOURCE_DATE_EPOCH": 1716273646, "FORCE_SOURCE_DATE": 1, "TZ": "UTC"},
        "visual_qa": {
            "official_paper_all_10_pages": "pass; source-native arXiv margin stamp on page 1; no clipped or overlapping content",
            "rebuilt_paper_all_10_pages": "pass; same ACM manuscript layout without arXiv margin stamp",
            "all_14_source_figure_pdfs": "pass; legible and complete",
            "author_site_15_hedgeagents_images": "pass; four unrelated MathVista/template assets explicitly excluded",
        },
        "source_archive_contains_system_code": False,
        "source_archive_interpretation": "manuscript, bibliography/typesetting support, and published figures only",
    }
    write_json(output_dir / "source_provenance.json", source_provenance)

    leakage_warning = {
        "source": LATER_AUTHOR_WARNING,
        "source_sha256": DOWNLOAD_HASHES["profit_mirage_v1.pdf"],
        "same_five_authors": True,
        "hedgeagents_named_as_representative_historical_backtest": True,
        "hedgeagents_in_pre_post_temporal_decay_experiment": False,
        "temporal_decay_experiment_methods": ["FinMem", "FinAgent", "QuantAgent", "FinCON", "TradingAgents"],
        "original_hedgeagents_test_period": "2021-01-01 through 2023-12-31",
        "gpt_4_1106_preview_official_knowledge_cutoff": "April 2023",
        "interpretation": "Material contamination risk for most of the historical test window, not direct proof that HedgeAgents' reported cells are false.",
        "replication_requirement": "A defensible rerun needs a frozen model whose training cutoff predates the entire test or a later genuinely unseen forward period plus exact inputs/traces.",
    }
    write_json(output_dir / "temporal_leakage_warning.json", leakage_warning)

    native_execution = {
        "manuscript_source_rebuilt": True,
        "manuscript_rebuild_is_system_execution": False,
        "author_site_static_assets_validated": True,
        "public_hedgeagents_system_source_found": False,
        "hedgeagents_pipeline_executed": False,
        "llm_calls_made": 0,
        "original_price_rows_loaded": 0,
        "original_news_rows_loaded": 0,
        "native_memory_rows_loaded": 0,
        "native_agent_actions_loaded": 0,
        "native_orders_or_fills_loaded": 0,
        "native_portfolio_trajectories_loaded": 0,
        "published_table_cells_faithfully_regenerated": 0,
        "strict_boundary": "document builds, author duplicates, screenshots, and plot digitization receive zero paper-result credit",
    }
    write_json(output_dir / "native_execution.json", native_execution)

    unique_tools = {name for groups in PROFILE_PERMISSIONS.values() for name in groups["tool"]}
    unique_actions = {name for groups in PROFILE_PERMISSIONS.values() for name in groups["action"]}
    manifest: dict[str, Any] = {
        "audit": "HedgeAgents primary-source, public-artifact, internal-consistency, and result-fidelity audit",
        "overall_status": "not_reproduced_no_public_system_source_frozen_inputs_runtime_traces_or_portfolio_path",
        "full_end_to_end_pipeline_reproduced": False,
        "published_numeric_table_cells": len(performance_rows),
        "hedgeagents_own_numeric_table_cells": sum(bool(row["hedgeagents_system_output"]) for row in performance_rows),
        "author_site_corroborated_main_table_cells": sum(bool(row["author_site_corroborated"]) for row in performance_rows),
        "published_numeric_table_cells_faithfully_regenerated": 0,
        "hedgeagents_own_cells_faithfully_regenerated": 0,
        "published_figures": len(figure_rows),
        "published_figure_panels": sum(int(row["panels"]) for row in figure_rows),
        "published_figures_with_exact_dated_underlying_values": 0,
        "arxiv_manuscript_source_files": len(source_rows),
        "arxiv_figure_pdf_files": sum(row["role"] == "published_figure" for row in source_rows),
        "public_system_source_files_recovered": 0,
        "author_site_tree_files": SITE_TREE_FILES,
        "author_site_hedgeagents_image_assets": 15,
        "author_site_unrelated_template_image_assets": 4,
        "author_site_unrelated_vqa_records": 6141,
        "profile_permission_rows_transcribed": len(permission_rows),
        "unique_profile_tool_names": len(unique_tools),
        "unique_profile_action_names": len(unique_actions),
        "verbatim_simplified_prompt_templates": sum(row["publication_form"] == "verbatim simplified template" for row in prompt_rows),
        "actual_llm_requests_recovered": 0,
        "actual_llm_responses_recovered": 0,
        "llm_calls_made": 0,
        "hard_or_material_internal_consistency_findings": sum(
            row["status"] in {
                "hard_internal_conflict", "author_source_scope_conflict", "author_source_count_conflict",
                "not_roundable_from_displayed_values", "claim_contradicted_by_own_table",
                "unsupported_by_displayed_ablation_values", "mathematical_specification_ambiguous",
            }
            for row in consistency_rows
        ),
        "exact_historical_llm_snapshot_currently_available": False,
        "temporal_leakage_risk_is_direct_hedgeagents_decay_measurement": False,
        "visual_qa_passed": True,
        "interpretation": (
            "The paper, complete manuscript source, static author repository, 236 displayed numeric table cells, "
            "90 author-site duplicate cells, all figures, and profile permission names are pinned. The public repository "
            "is documentation only and contains unrelated MathVista template residue. No system implementation, frozen "
            "market/news dataset, exact prompts, runtime LLM exchanges, memories, actions, orders, fills, or dated portfolio "
            "path is public in the pinned evidence, so no empirical result is faithfully regenerated."
        ),
    }

    readme = f"""# HedgeAgents paper-level replication audit

Overall verdict: **not reproduced**. This package pins the original paper, its
complete arXiv v1 manuscript bundle, the authors' public project repository,
bounded archival searches, official model provenance, and a later warning from
the same authors about temporal leakage in financial-agent backtests. It gives
zero result credit to typesetting, duplicated tables, screenshots, or plots.

## What is genuinely recovered

- The official {PAPER_PAGES}-page paper is pinned at SHA-256 `{PAPER_SHA256}`.
  The {SOURCE_FILE_COUNT}-file arXiv bundle contains the TeX, bibliography and
  typesetting support, plus 14 figure PDFs. It contains no HedgeAgents program,
  data, environment, or runner.
- Two clean three-pass LaTeX builds have identical extracted text and differ in
  raw bytes only at the generated PDF trailer ID; this audit does **not** call
  them byte-identical. All original/rebuilt pages and all source figures passed
  visual inspection.
- The author repository is pinned at `{SITE_HEAD}`. Its leaderboard repeats 90
  method cells from Table 1 exactly. Four profile screenshots name 23 unique
  tool labels system-wide, ten unique action labels, and market scopes. Four
  workflow images and three general-experience snapshots provide qualitative
  author evidence. None is an executable trace.
- All 236 displayed numeric table cells are transcribed: 119 in the main table,
  63 in the conference ablation, and 54 in the LLM-backbone table. Of these,
  126 are HedgeAgents/full-system variants or backbones. **Zero of 236** are
  regenerated from a native execution.

## Public-site contamination boundary

The site repository is an R1 static documentation artifact, not released system
code. Its 5.2 MB `visualizer/data/data_public.js`, `filters*.json`,
`data-composition.png`, `tease_scores_gpt4v.png`, and MathVista logos belong to a
6,141-record MathVista/VQA website template. They are unrelated to HedgeAgents
and are explicitly excluded from data, implementation, and result evidence.
The visible Code and Dataset controls are commented placeholders that self-link
to the page. Git history contains only website assets. Software Heritage found
the same site and its single fork, not a separate implementation.

## Material internal conflicts

- The full system's MDD is 14.21% in the main table, LLM table, and prose, but
  8.68% in the all-conferences ablation row. The ablation narrative's 24.44%
  calculation uses 14.21%, reinforcing that 8.68% is inconsistent.
- The paper says each agent has 23 tools and eight actions. The author profiles
  instead list 5-7 tools per agent (23 unique system-wide) and 4-6 actions per
  agent (ten unique system-wide). No released mapping reconciles the counts.
- Table 1 prints a 24.49% Sharpe improvement, while its displayed 2.41 and 1.93
  imply 24.8705%. The conference prose's 41.29%, 60.65%, and 19.72% Sharpe
  improvements also do not follow from the displayed ablation rows.
- The claim of optimal performance on all metrics conflicts with the table:
  HedgeAgents volatility is 1.30, while MV is 1.13 and several methods are lower.
- The budget objective leaves lambda values, confidence level, covariance
  estimator/window, and solver absent; it also switches between `I_ij` and
  `sigma_ij` and writes CVaR bounds in an unresolved order.

## Why the empirical result remains unreproducible

The exact asset universe and constituent vintage, currency pairs, frozen Yahoo
and Alpaca responses, 60 indicator definitions, prompts, tool implementations,
risk parameters, starting capital, fill price/timing, order sizing, transaction
costs, slippage, constraints, metric formulas, Optuna spaces/trials, baseline
commits, seeds, dependency lock, and repeated-run policy are absent. No LLM
request/response, memory database, action record, order, fill, cash ledger, or
dated equity series is released. Curve images cannot regenerate exact metrics.
The historical `gpt-4-1106-preview` dependency is now deprecated; using a current
model would be an adaptation, not exact replication.

## Temporal-leakage validity warning

OpenAI documented an April 2023 knowledge cutoff for `gpt-4-1106-preview`, while
the reported HedgeAgents test spans January 2021 through December 2023. Most of
that test window is therefore inside the model's stated knowledge horizon. A
later paper by the same five authors cites HedgeAgents while arguing that
historical financial-agent backtests can suffer a "profit mirage" after the
model's knowledge cutoff. Its direct pre/post decay experiment covers FinMem,
FinAgent, QuantAgent, FinCON, and TradingAgents—not HedgeAgents—so this audit
treats it as a material contamination risk, **not** proof that a particular
HedgeAgents cell is false.

Regenerate with `scripts/audit_hedgeagents_paper.py`. `--strict` intentionally
exits nonzero while the paper remains unreproduced.
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
        "--paper-pdf", type=Path,
        default=ROOT / "literature_review/papers/44_hedgeagents_a_balanced_aware_multi_agent_financial_trading_system.pdf",
    )
    parser.add_argument(
        "--scratch-root", type=Path,
        default=Path(os.environ.get("HEDGEAGENTS_AUDIT_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/hedgeagents_audit")),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "paper_runs/paper_replication_audits/hedgeagents",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(args.paper_pdf.resolve(), args.scratch_root.resolve(), args.output_dir.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return int(args.strict and not manifest["full_end_to_end_pipeline_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
