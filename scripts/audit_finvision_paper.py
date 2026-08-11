#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for FinVision.

This audit recovers and validates the paper, its arXiv manuscript source, an
author thesis that repeats the experiment, current public-artifact discovery
evidence, and a frozen Yahoo price diagnostic.  It deliberately gives no
paper-result credit to manuscript reconstruction, repeated thesis tables,
transcribed FinAgent values, or matches obtained from a current price feed.

No FinVision implementation, original news/price snapshot, LLM request or
response, action path, or portfolio trajectory is public in the pinned source.
Consequently zero of the paper's 72 performance cells are faithfully
regenerated here.
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
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]

TITLE = "FinVision: A Multi-Agent Framework for Stock Market Prediction"
AUTHORS = ["Sorouralsadat Fatemi", "Yuheng Hu"]
ARXIV_RECORD = "https://arxiv.org/abs/2411.08899v1"
ARXIV_PDF_URL = "https://arxiv.org/pdf/2411.08899v1"
ARXIV_SOURCE_URL = "https://arxiv.org/e-print/2411.08899v1"
DOI = "10.1145/3677052.3698688"
DOI_URL = f"https://doi.org/{DOI}"
THESIS_URL = "https://doi.org/10.6084/m9.figshare.27939588"

PAPER_SHA256 = "8483714696f009ffecd5e818ce2b8937e88be03343476bb23344b4f38b080921"
PAPER_PAGES = 9
SOURCE_ARCHIVE_SHA256 = "bc7a421b954b6a90c0a38374e6eb643333a127904916c4faa01d50ec2309a5fe"
SOURCE_FILES = 22
SOURCE_BYTES = 3_521_908
REBUILT_PDF_SHA256 = "2540a250d752c7b322c835a46b8dfa526e932a35ab9c5c73a19f2ca4f5260e6f"
SECOND_REBUILT_PDF_SHA256 = "5b6f793d209dd625a6b119f6b0c7179b8eb33c9d5076fe1abec5838dae64e777"
REBUILT_PDF_PAGES = 9
REBUILT_TEXT_SHA256 = "34b3811c8ea3ccff7b2b3be468720b6f78de07e24df8830f37b4b738cc0f80cc"
THESIS_SHA256 = "868da394c7fcf3a84de5351aef3b9a8b781c132db0803335bef2103d3b79ab8a"
THESIS_PAGES = 133
THESIS_TEXT_SHA256 = "55f3ca48caba99d981eeba4b36fd4e1fe28b726d27342d8a64db3ca31a579f34"

DOWNLOAD_HASHES = {
    "arxiv_api.xml": "ed9f968cb29bfe6a2940eabe774fa32861485c0144e780d7e8bfbfccdd625034",
    "arxiv_record.html": "c68b12f66975a4f4c1ba1f025664337b062efd9cf390b44f3a2d665ee5a08d6b",
    "author_research.html": "ff6113a4c021010fee1f1c606a5f38b3bbd10ed6346cc7b162c98ac9d5c1578e",
    "crossref_doi.json": "2ff9c1ea88b4951b98c6836ad691a939720ecb47b816ee3be8686cd8a21a2eef",
    "finvision_arxiv_v1.tar": SOURCE_ARCHIVE_SHA256,
    "finvision_author_thesis_2024.pdf": THESIS_SHA256,
    "finvision_author_thesis_2024.txt": THESIS_TEXT_SHA256,
    "thesis_metadata.json": "def44d19075b8c0f22b89fc31e2201b120f921b83b535d2df0f8916d9783680e",
    "yahoo_chart_AAPL_20230401_20240101.json": "f342cab96aa0fef51b8655f1287b5b7ec01e129d530ccd89daa8a94db38f0ce9",
    "yahoo_chart_AMZN_20230401_20240101.json": "32623af9274acf69a9cce10190b4596f213616bc3c2853a9d8391ddf7a4c1f07",
    "yahoo_chart_MSFT_20230401_20240101.json": "edf3fd3b08ac8e63fba8dc62ebdc42e4421c44817d8e6c7776776643bed2c931",
}

EVIDENCE_HASHES = {
    "github_author_code_search_finvision.json": "85d678109ac726920585f0cf0a010e4c7898b1e407159fb6fb4714743ce16cb6",
    "github_author_gists.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "github_author_repos.json": "e7bf55f93811b503e11f4b8d7eafd48ac7cedbf2f8db1d37125b8883106c8c09",
    "github_author_site_head.json": "c4fa04d2b9f38504ef867c0173d9eeb039af4cbb9fad38c3529a5020a2534fca",
    "github_author_site_repo.json": "86b1b4216d9b57c49a19060a0e45f126322be2762257e0b22b4eaccd23915e52",
    "github_author_user.json": "d6af094662ebfa988ac3f9f06b39c02073a3be0c6756838363b863d6f391ee24",
    "github_code_search_arxiv_id.json": "188b66c747bffcf744cf86850f5deadfa6179c08c239d5586c89055ef21c6f92",
    "github_code_search_exact_title.json": "18b76808af76712f5a7c2997120193467f9f50742c008f47d9e1a1a8cd2a7ba2",
    "github_code_search_finagent_values.json": "b10f1a06c34f2b55fba656b154ee81624a671b8d62cc4849a6883ca7139528d1",
    "github_code_search_finvision_values.json": "72fe7d2d357f3fb515b8f249a9bfa81f69cfd5440667e4ef72f452b81f7c4a79",
    "github_code_search_market_values.json": "07fbe7cfc843344cc52644b3b0801a3c1a7999b2ad48e781fef695077e4290ce",
    "github_code_search_models.json": "c4ee8c767861fe552a0ad1940963426a71d4ae3ceeaded78849fd172342245f1",
    "github_code_search_title_author.json": "4e632efb707232bcffb57aeb3239a6b7ae0b4fc2a9ea018a0361fa00ad9e8a7c",
    "github_commit_search_arxiv_id.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github_commit_search_exact_title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github_commit_search_models.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github_search_arxiv_id.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github_search_exact_title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github_search_title_author.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github_user_search_author.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "huggingface_author_datasets.json": "f3e9704f3e35c92777239a8cf26585eb29a3d2a8c758ba163a23e7052cef95a8",
    "huggingface_author_models.json": "d5e71ea5755b70601c0df15943e97f50559e3597dae2709be32b36cd43a76b1a",
    "huggingface_author_overview.json": "0bf2af9218a735f31fd906949e50b4c0a006fbe738409b66d2844dea4f4d5eaa",
    "openai_gpt_4o_mini_model.html": "58b6a9cdf368129f9585b685deda6575bf39d56ffc0a64df1aef53c5516b5561",
    "openai_o1_mini_model.html": "ae486dce85f213a6a8fb659c90e4ea4e7b90884a943ae439fd6e0ec02d5d7c61",
    "software_heritage_origin_search_finvision.json": "d781129ce12a375147226c5b1a4ca2a39b23704309ce978100ceeaeb351e3aa3",
    "wayback_author_github_cdx.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
}

PRICE_FILES = {
    "AAPL": "yahoo_chart_AAPL_20230401_20240101.json",
    "MSFT": "yahoo_chart_MSFT_20230401_20240101.json",
    "AMZN": "yahoo_chart_AMZN_20230401_20240101.json",
}

METRICS = ("ARR_pct", "SR", "MDD_pct")
TICKERS = ("AAPL", "MSFT", "AMZN")
METHODS = (
    "Market",
    "MACD",
    "RSI",
    "PPO",
    "DQN",
    "FinAgent",
    "FinVision",
    "FinVision-w/o Reflection",
)

# Table values as printed in the pinned manuscript/PDF and repeated in the
# author's thesis. Each tuple is ARR %, Sharpe ratio (despite the table's SR %
# header), and MDD %.
PAPER_RESULTS: dict[str, dict[str, tuple[float, float, float]]] = {
    "Market": {
        "AAPL": (13.56, 0.67, 14.93),
        "MSFT": (22.27, 1.01, 12.95),
        "AMZN": (43.57, 1.37, 17.45),
    },
    "MACD": {
        "AAPL": (1.47, -0.26, 1.33),
        "MSFT": (0.36, -0.71, 1.67),
        "AMZN": (-6.40, -1.94, 4.56),
    },
    "RSI": {
        "AAPL": (4.20, 1.22, 0.62),
        "MSFT": (1.54, -0.33, 0.63),
        "AMZN": (2.35, 0.20, 0.32),
    },
    "PPO": {
        "AAPL": (7.26, -0.42, 7.90),
        "MSFT": (6.23, -0.73, 11.26),
        "AMZN": (17.15, -0.59, 15.39),
    },
    "DQN": {
        "AAPL": (1.22, -0.90, 5.87),
        "MSFT": (17.75, -0.26, 12.85),
        "AMZN": (22.07, -0.46, 19.57),
    },
    "FinAgent": {
        "AAPL": (31.89, 1.43, 10.40),
        "MSFT": (44.74, 1.79, 5.57),
        "AMZN": (65.10, 1.61, 13.20),
    },
    "FinVision": {
        "AAPL": (14.79, 1.20, 14.38),
        "MSFT": (25.57, 1.41, 13.28),
        "AMZN": (42.14, 1.72, 12.09),
    },
    "FinVision-w/o Reflection": {
        "AAPL": (8.84, 0.62, 13.42),
        "MSFT": (16.99, 1.04, 11.79),
        "AMZN": (37.64, 1.68, 10.64),
    },
}

DATASET_ROWS = {
    ("AAPL", "training"): (42, 1081),
    ("AAPL", "testing"): (145, 4886),
    ("AMZN", "training"): (42, 1113),
    ("AMZN", "testing"): (145, 5556),
    ("MSFT", "training"): (42, 1897),
    ("MSFT", "testing"): (145, 1249),
}

FINAGENT_PRECISE = {
    ("AAPL", "ARR_pct"): 31.8972,
    ("AAPL", "SR"): 1.4326,
    ("AAPL", "MDD_pct"): 10.4032,
    ("MSFT", "ARR_pct"): 44.7359,
    ("MSFT", "SR"): 1.7884,
    ("MSFT", "MDD_pct"): 5.5732,
    ("AMZN", "ARR_pct"): 65.0998,
    ("AMZN", "SR"): 1.6096,
    ("AMZN", "MDD_pct"): 13.198,
}

PROMPTS = (
    ("news_summarizer", "text", "GPT-4o-mini", "news data and ticker"),
    ("chart_analyst", "image+text", "GPT-4o-mini", "rendered chart and ticker"),
    ("reflection_short_medium", "text", "GPT-4o-mini", "runtime JSON and unspecified window lengths"),
    ("trading_signal_chart_reflection", "image+text", "GPT-4o-mini", "30-day signal image and ticker"),
    ("prediction", "text", "o1-mini", "portfolio, agent outputs, history, and market intelligence"),
)


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


def normalized_pdf_text(path: Path, expected_hash: str, pages: int, markers: Sequence[str]) -> str:
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        raise ValueError(f"PDF hash changed for {path.name}: {actual_hash}")
    reader = PdfReader(path)
    if len(reader.pages) != pages:
        raise ValueError(f"PDF page count changed for {path.name}: {len(reader.pages)}")
    text = " ".join(" ".join((page.extract_text() or "").split()) for page in reader.pages)
    for marker in markers:
        if marker not in text:
            raise ValueError(f"required text missing from {path.name}: {marker}")
    return text


def pdf_without_trailer_id(path: Path) -> bytes:
    payload = path.read_bytes()
    normalized, replacements = re.subn(
        rb"/ID \[<[0-9A-F]+> <[0-9A-F]+>\]",
        b"/ID [<PDF_TRAILER_ID> <PDF_TRAILER_ID>]",
        payload,
    )
    if replacements != 1:
        raise ValueError(f"expected one PDF trailer ID in {path.name}, found {replacements}")
    return normalized


def pdftotext_sha256(path: Path) -> str:
    completed = subprocess.run(
        ["pdftotext", str(path), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def validate_hashed_files(root: Path, expected: Mapping[str, str], flavor: str) -> None:
    for name, expected_hash in expected.items():
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned {flavor}: {path}")
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise ValueError(f"pinned {flavor} changed for {name}: {actual_hash}")


def paper_source_inventory(archive: Path, source_dir: Path) -> list[dict[str, Any]]:
    if sha256(archive) != SOURCE_ARCHIVE_SHA256:
        raise ValueError("arXiv source archive hash changed")
    tex = (source_dir / "acmtrade.tex").read_text(encoding="utf-8")
    active_tex = "\n".join(line for line in tex.splitlines() if not line.lstrip().startswith("%"))
    rows: list[dict[str, Any]] = []
    total = 0
    with tarfile.open(archive, "r:*") as bundle:
        members = [member for member in bundle.getmembers() if member.isfile()]
        if len(members) != SOURCE_FILES:
            raise ValueError(f"arXiv source file count changed: {len(members)}")
        for member in sorted(members, key=lambda item: item.name):
            extracted = bundle.extractfile(member)
            if extracted is None:
                raise ValueError(f"cannot read arXiv member: {member.name}")
            payload = extracted.read()
            total += len(payload)
            disk = source_dir / member.name
            if not disk.is_file() or disk.read_bytes() != payload:
                raise ValueError(f"extracted arXiv source differs: {member.name}")
            name = Path(member.name).name
            suffix = Path(name).suffix.lower()
            if name == "acmtrade.tex":
                role = "primary_manuscript_source"
            elif name in {"acmtrade.bib", "acmtrade.bbl"}:
                role = "bibliography_source_or_rendered_bibliography"
            elif name == "framework.png" and name in active_tex:
                role = "published_figure_used_by_active_manuscript"
            elif suffix in {".png", ".jpg", ".jpeg"}:
                role = "unused_or_commented_development_asset_not_system_code"
            else:
                role = "publisher_template_or_typesetting_support"
            rows.append(
                {
                    "path": member.name,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "role": role,
                    "is_executable_system_source": False,
                }
            )
    if total != SOURCE_BYTES:
        raise ValueError(f"arXiv uncompressed byte count changed: {total}")
    if sum(row["role"] == "published_figure_used_by_active_manuscript" for row in rows) != 1:
        raise ValueError("expected exactly one active manuscript figure")
    return rows


def parse_performance_triplets(tex: str) -> list[tuple[float, float, float]]:
    """Extract the 24 displayed result triplets from the active LaTeX table."""
    block = tex.split(r"\textbf{Market}", 1)[1].split(r"\caption{Performance Results", 1)[0]
    block = "\n".join(line.split("%", 1)[0] for line in block.splitlines())
    groups = re.findall(
        r"\\begin\{tabular\}\{ c c c \}(.*?)\\end\{tabular\}",
        block,
        flags=re.DOTALL,
    )
    triplets: list[tuple[float, float, float]] = []
    for group in groups:
        values = [float(value) for value in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", group)]
        if not values:
            continue
        if len(values) != 3:
            raise ValueError(f"unexpected numeric group in performance table: {values}")
        triplets.append(tuple(values))
    if len(triplets) != 24:
        raise ValueError(f"expected 24 performance triplets, found {len(triplets)}")
    return triplets


def source_ordered_results() -> list[tuple[str, str, tuple[float, float, float]]]:
    order: list[tuple[str, str, tuple[float, float, float]]] = []
    for ticker in TICKERS:
        order.append(("Market", ticker, PAPER_RESULTS["Market"][ticker]))
    for ticker in TICKERS:
        for method in ("MACD", "RSI"):
            order.append((method, ticker, PAPER_RESULTS[method][ticker]))
    for ticker in TICKERS:
        for method in ("PPO", "DQN"):
            order.append((method, ticker, PAPER_RESULTS[method][ticker]))
    for ticker in TICKERS:
        order.append(("FinAgent", ticker, PAPER_RESULTS["FinAgent"][ticker]))
    for ticker in TICKERS:
        for method in ("FinVision", "FinVision-w/o Reflection"):
            order.append((method, ticker, PAPER_RESULTS[method][ticker]))
    return order


def validate_source_claims(source_dir: Path, thesis_text_path: Path) -> str:
    tex = (source_dir / "acmtrade.tex").read_text(encoding="utf-8")
    parsed = parse_performance_triplets(tex)
    expected = [values for _, _, values in source_ordered_results()]
    if parsed != expected:
        raise ValueError(f"source performance table changed: parsed={parsed}")
    required_tex = (
        "nine-month period from April 1, 2023, to December 29, 2023",
        "seven-month testing period (June 1 to December 29, 2023)",
        "Data retrieved using eodhd.com/api/news",
        "All agents, except for the final decision agent, utilize the GPT-4o-mini model",
        "operates using the o1-mini model",
        "temperature setting of 1",
        "Trading Signal Chart Reflection Prompt",
        "Prediction Agent Prompt",
        "Results for FinAgent are retrieved from the respective publication \\cite{2yang2023fingpt}",
    )
    for marker in required_tex:
        if marker not in tex:
            raise ValueError(f"required source claim missing: {marker}")
    for (ticker, period), (days, news) in DATASET_ROWS.items():
        period_label = "Training" if period == "training" else "Testing"
        if not re.search(rf"{ticker}.*?{period_label}.*?{days}.*?{news:,}", tex, flags=re.DOTALL):
            raise ValueError(f"dataset row missing from source: {ticker}/{period}")

    if sha256(thesis_text_path) != THESIS_TEXT_SHA256:
        raise ValueError("author thesis text extraction hash changed")
    thesis = " ".join(thesis_text_path.read_text(encoding="utf-8", errors="replace").split())
    if TITLE.lower() not in thesis.lower() or "Performance Results of All Models" not in thesis:
        raise ValueError("FinVision thesis chapter markers missing")
    # Each full displayed row is repeated in the thesis. Searching the three
    # formatted values together avoids claiming independent regeneration.
    for method, ticker, values in source_ordered_results():
        candidates = [
            " ".join(f"{value:.2f}" for value in values),
            " ".join(str(value) for value in values),
        ]
        if not any(candidate in thesis for candidate in candidates):
            raise ValueError(f"thesis does not corroborate {method}/{ticker}: {values}")
    return tex


def read_yahoo_prices(path: Path) -> list[tuple[datetime, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    rows = []
    for timestamp, price in zip(timestamps, adjusted):
        if price is None:
            continue
        rows.append((datetime.fromtimestamp(int(timestamp), tz=timezone.utc), float(price)))
    return rows


def market_metrics(prices: Sequence[float], annualization_days: int = 252, paper_t: int = 145) -> dict[str, float]:
    values = np.asarray(prices, dtype=float)
    returns = values[1:] / values[:-1] - 1.0
    arr = (values[-1] / values[0] - 1.0) * annualization_days / paper_t * 100.0
    sharpe = float(np.mean(returns) / np.std(returns, ddof=1) * math.sqrt(annualization_days))
    drawdowns = (np.maximum.accumulate(values) - values) / np.maximum.accumulate(values)
    return {"ARR_pct": float(arr), "SR": sharpe, "MDD_pct": float(np.max(drawdowns) * 100.0)}


def yahoo_and_dataset_audit(downloads: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    stats_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    for ticker in TICKERS:
        filename = PRICE_FILES[ticker]
        rows = read_yahoo_prices(downloads / filename)
        if len(rows) != 188:
            raise ValueError(f"current Yahoo observation count changed for {ticker}: {len(rows)}")
        dates = [stamp.date().isoformat() for stamp, _ in rows]
        if (dates[0], dates[-1]) != ("2023-04-03", "2023-12-29"):
            raise ValueError(f"current Yahoo endpoints changed for {ticker}: {dates[0]}, {dates[-1]}")
        training = [row for row in rows if row[0].date().isoformat() <= "2023-05-31"]
        testing = [row for row in rows if row[0].date().isoformat() >= "2023-06-01"]
        if (len(training), len(testing)) != (41, 147):
            raise ValueError(f"current Yahoo period counts changed for {ticker}")
        for period, literal_count, first_date, last_date in (
            ("training", len(training), training[0][0].date().isoformat(), training[-1][0].date().isoformat()),
            ("testing", len(testing), testing[0][0].date().isoformat(), testing[-1][0].date().isoformat()),
        ):
            paper_days, news_count = DATASET_ROWS[(ticker, period)]
            stats_rows.extend(
                (
                    {
                        "ticker": ticker,
                        "period": period,
                        "dimension": "trading_days",
                        "paper_value": paper_days,
                        "pinned_current_value": literal_count,
                        "first_current_session": first_date,
                        "last_current_session": last_date,
                        "status": "paper_count_differs_from_literal_exchange_sessions",
                        "faithful_replication_credit": False,
                        "interpretation": "paper transformation or endpoint convention is unspecified",
                    },
                    {
                        "ticker": ticker,
                        "period": period,
                        "dimension": "news_articles",
                        "paper_value": news_count,
                        "pinned_current_value": "",
                        "first_current_session": "",
                        "last_current_session": "",
                        "status": "not_reproduced_original_query_and_snapshot_unreleased",
                        "faithful_replication_credit": False,
                        "interpretation": "paper says Yahoo Finance content via EODHD but omits query, cutoff, timezone, and deduplication",
                    },
                )
            )
        computed = market_metrics([price for _, price in testing])
        for metric in METRICS:
            paper_value = PAPER_RESULTS["Market"][ticker][METRICS.index(metric)]
            value = computed[metric]
            rounded_match = round(value, 2) == paper_value
            diagnostic_rows.append(
                {
                    "ticker": ticker,
                    "metric": metric,
                    "paper_value": paper_value,
                    "current_yahoo_diagnostic_value": value,
                    "current_value_rounded_2dp": round(value, 2),
                    "display_match": rounded_match,
                    "formula_assumptions": "adjusted close; Jun 1-Dec 29 inclusive; C=252; paper T=145; arithmetic daily returns; Rf=0; sample std; sqrt(252) Sharpe",
                    "status": "current_input_diagnostic_match_only" if rounded_match else "current_input_diagnostic_mismatch",
                    "faithful_replication_credit": False,
                }
            )
    if sum(row["display_match"] for row in diagnostic_rows) != 3:
        raise ValueError("expected exactly three current-Yahoo display matches")
    return stats_rows, diagnostic_rows


def finagent_lineage(finagent_ledger: Path) -> dict[tuple[str, str], float]:
    values: dict[tuple[str, str], float] = {}
    with finagent_ledger.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["paper_table"] != "Appendix Table 7 panel 1" or not row["item"].endswith("/FinAgent"):
                continue
            ticker = row["item"].split("/", 1)[0]
            key = (ticker, row["metric"])
            if key in FINAGENT_PRECISE:
                values[key] = float(row["paper_value"])
    if values != FINAGENT_PRECISE:
        raise ValueError(f"pinned FinAgent lineage changed: {values}")
    return values


def performance_ledger(thesis_corroborated: bool, finagent_values: Mapping[tuple[str, str], float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method in METHODS:
        for ticker in TICKERS:
            for index, metric in enumerate(METRICS):
                lineage_value: Any = ""
                lineage_status = "not_external_transcription"
                if method == "FinAgent":
                    lineage_value = finagent_values[(ticker, metric)]
                    paper_value = PAPER_RESULTS[method][ticker][index]
                    lineage_status = (
                        "two_decimal_rounding_match"
                        if round(float(lineage_value), 2) == paper_value
                        else "two_decimal_display_lineage_with_aapl_arr_truncation"
                    )
                rows.append(
                    {
                        "method": method,
                        "ticker": ticker,
                        "metric": metric,
                        "paper_value": PAPER_RESULTS[method][ticker][index],
                        "arxiv_source_verified": True,
                        "author_thesis_corroborated": thesis_corroborated,
                        "external_finagent_value": lineage_value,
                        "external_lineage_status": lineage_status,
                        "native_reproduced_value": "",
                        "status": "not_reproduced_no_public_system_source_frozen_inputs_or_trajectory",
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 72:
        raise ValueError(f"expected 72 performance cells, found {len(rows)}")
    return rows


def prompt_inventory() -> list[dict[str, Any]]:
    return [
        {
            "prompt": name,
            "modality": modality,
            "paper_model_alias": model,
            "runtime_fields": fields,
            "template_printed_in_appendix": True,
            "runtime_values_released": False,
            "actual_request_released": False,
            "actual_response_released": False,
            "status": "template_recovered_runtime_trace_missing",
            "paper_result_credit": False,
        }
        for name, modality, model, fields in PROMPTS
    ]


def method_specification_audit() -> list[dict[str, Any]]:
    rows = [
        ("universe", "AAPL, AMZN, MSFT", "specified"),
        ("overall_period", "2023-04-01 through 2023-12-29", "specified"),
        ("warmup_period", "2023-04-01 through 2023-05-31", "specified"),
        ("testing_period", "2023-06-01 through 2023-12-29", "specified"),
        ("trading_day_counts", "42 warm-up and 145 test versus 41/147 literal sessions", "unresolved_count_convention"),
        ("news_content_source", "Yahoo Finance", "specified_at_brand_level"),
        ("news_api_provider", "EODHD API footnote", "provider_provenance_ambiguity"),
        ("news_query_parameters", "not printed", "missing"),
        ("news_timestamp_cutoff_timezone", "not printed", "missing_lookahead_control"),
        ("news_deduplication", "not printed", "missing"),
        ("chart_lookback", "past 60 days", "specified"),
        ("technical_indicators", "SMA10/50, RSI14, Bollinger20/2sd, volume, MACD", "mostly_specified"),
        ("macd_parameters", "not printed", "missing"),
        ("kdj_parameters", "not printed", "missing"),
        ("orchestration_framework", "LangGraph StateGraph", "specified_without_version"),
        ("dependency_versions", "not printed", "missing"),
        ("nondecision_model", "GPT-4o-mini alias", "alias_without_immutable_snapshot"),
        ("nondecision_temperature", "0.3", "specified"),
        ("decision_model", "o1-mini alias", "deprecated_alias_without_immutable_snapshot"),
        ("decision_temperature", "1", "specified"),
        ("model_snapshot_ids", "not printed", "missing"),
        ("prompt_templates", "five templates printed", "specified_template_only"),
        ("actual_llm_requests", "not released", "missing"),
        ("actual_llm_responses", "not released; example response is ellipsized", "missing"),
        ("llm_request_ids", "not released", "missing"),
        ("random_seeds", "not printed", "missing"),
        ("reflection_signal_window", "past 30 days", "specified"),
        ("reflection_short_medium_windows", "runtime placeholders only", "missing"),
        ("initial_capital", "not printed", "missing"),
        ("price_provider", "not printed", "missing"),
        ("price_field_and_adjustment", "not printed", "missing"),
        ("trade_fill_timing_and_price", "not printed", "missing"),
        ("position_size_execution", "prediction emits 1-10 percent-like size", "partial_no_share_rounding_or_cash_equation"),
        ("long_short_constraints", "not printed", "missing"),
        ("transaction_costs", "not printed", "missing"),
        ("slippage", "not printed", "missing"),
        ("reward_equation", "reward agent named but equation not printed", "missing"),
        ("portfolio_cash_accounting", "prompt fields shown but update equation absent", "missing"),
        ("arr_annualization_constant", "symbol C only", "missing_numeric_value"),
        ("sharpe_convention", "Rf/frequency/annualization/ddof not printed", "missing"),
        ("mdd_input_path", "formula printed; portfolio path absent", "partial"),
        ("macd_rsi_baseline_parameters", "not printed; prose says KDJ+RSI while table says RSI", "ambiguous"),
        ("ppo_dqn_hyperparameters", "not printed", "missing"),
        ("baseline_seeds_and_trials", "not printed", "missing"),
        ("finagent_value_lineage", "values trace to FinAgent Appendix Table 7", "transcription_not_reproduction"),
        ("finagent_caption_citation", "caption cites FinGPT key 2yang2023fingpt", "citation_lineage_error"),
        ("native_actions_equity_curves", "not released", "missing"),
        ("public_system_implementation", "not found in pinned author/search/archive evidence", "not_publicly_recovered_not_proof_of_nonexistence"),
    ]
    return [{"dimension": key, "paper_or_evidence": value, "status": status, "paper_result_credit": False} for key, value, status in rows]


def artifact_access_audit() -> list[dict[str, Any]]:
    return [
        {"artifact": "official_arxiv_pdf", "availability": "public_pinned", "content": "nine-page paper", "system_source_credit": False},
        {"artifact": "arxiv_v1_source", "availability": "public_pinned", "content": "manuscript, publisher support files, and figures only", "system_source_credit": False},
        {"artifact": "author_thesis", "availability": "public_pinned", "content": "FinVision chapter repeats method/prompts/table; no implementation or traces", "system_source_credit": False},
        {"artifact": "paper_listed_code_url", "availability": "none_printed", "content": "paper makes no code-release claim and prints no repository URL", "system_source_credit": False},
        {"artifact": "author_github_current", "availability": "27 public repos inspected", "content": "no attributable FinVision implementation; author site entry is descriptive only", "system_source_credit": False},
        {"artifact": "github_exact_repo_searches", "availability": "zero exact-title/arXiv/title-author repos", "content": "code-search hits are citations or paper text, not an implementation", "system_source_credit": False},
        {"artifact": "author_huggingface", "availability": "21 datasets and 74 models inspected", "content": "no attributable FinVision release", "system_source_credit": False},
        {"artifact": "software_heritage_and_wayback", "availability": "searched", "content": "no attributable archived implementation recovered", "system_source_credit": False},
        {"artifact": "original_market_news_snapshot", "availability": "not_publicly_recovered", "content": "counts printed; rows, query, and timestamps absent", "system_source_credit": False},
        {"artifact": "original_llm_and_trading_traces", "availability": "not_publicly_recovered", "content": "no requests, responses, actions, fills, rewards, cash, or equity paths", "system_source_credit": False},
    ]


def discovery_evidence(downloads: Path, evidence: Path) -> list[dict[str, Any]]:
    summaries = {
        "github_search_exact_title.json": "zero exact-title repository matches",
        "github_search_arxiv_id.json": "zero arXiv-id repository matches",
        "github_search_title_author.json": "zero title-plus-author repository matches",
        "github_code_search_exact_title.json": "42 indexed code hits; citation/index material, not an attributable system release",
        "github_code_search_arxiv_id.json": "26 indexed code hits; citations only",
        "github_code_search_title_author.json": "19 indexed code hits; no implementation recovered",
        "github_code_search_models.json": "two paper-text hits; no implementation recovered",
        "github_author_repos.json": "27 current public author repositories; none attributable to FinVision",
        "github_author_code_search_finvision.json": "one author-owned hit: descriptive research webpage",
        "github_author_gists.json": "zero public author gists",
        "huggingface_author_datasets.json": "21 current public datasets; none attributable to FinVision",
        "huggingface_author_models.json": "74 current public models; none attributable to FinVision",
        "software_heritage_origin_search_finvision.json": "20 name matches inspected; none attributable to paper/authors",
        "wayback_author_github_cdx.json": "no wildcard capture recovered for author GitHub path",
        "openai_o1_mini_model.html": "official model page: o1-mini deprecated; dated snapshot o1-mini-2024-09-12; text-only",
        "openai_gpt_4o_mini_model.html": "official model page: dated snapshot gpt-4o-mini-2024-07-18; image input supported",
    }
    rows = []
    for name, expected_hash in sorted(EVIDENCE_HASHES.items()):
        rows.append(
            {
                "file": f"evidence/{name}",
                "sha256": expected_hash,
                "summary": summaries.get(name, "pinned supporting discovery or identity evidence"),
                "negative_search_limit": "absence in searched public indexes is not proof that private or deleted artifacts never existed",
            }
        )
    for name in ("arxiv_api.xml", "arxiv_record.html", "author_research.html", "crossref_doi.json", "thesis_metadata.json"):
        rows.append(
            {
                "file": f"downloads/{name}",
                "sha256": DOWNLOAD_HASHES[name],
                "summary": "pinned primary bibliographic/author-hosted metadata",
                "negative_search_limit": "not a system implementation",
            }
        )
    return rows


def build_audit(
    paper_pdf: Path,
    scratch_root: Path,
    finagent_ledger: Path,
    output_dir: Path,
) -> dict[str, Any]:
    downloads = scratch_root / "downloads"
    evidence = scratch_root / "evidence"
    source_dir = scratch_root / "source_v1"
    archive = downloads / "finvision_arxiv_v1.tar"
    rebuilt_pdf = scratch_root / "build_deterministic/acmtrade.pdf"
    second_rebuilt_pdf = scratch_root / "build_deterministic_2/acmtrade.pdf"
    thesis_pdf = downloads / "finvision_author_thesis_2024.pdf"
    thesis_text = downloads / "finvision_author_thesis_2024.txt"

    validate_hashed_files(downloads, DOWNLOAD_HASHES, "download")
    validate_hashed_files(evidence, EVIDENCE_HASHES, "discovery evidence")
    paper_text = normalized_pdf_text(
        paper_pdf,
        PAPER_SHA256,
        PAPER_PAGES,
        (TITLE, "Dataset statistics", "Performance Results of All Models"),
    )
    rebuilt_text = normalized_pdf_text(
        rebuilt_pdf,
        REBUILT_PDF_SHA256,
        REBUILT_PDF_PAGES,
        (TITLE, "Dataset statistics", "Performance Results of All Models"),
    )
    second_rebuilt_text = normalized_pdf_text(
        second_rebuilt_pdf,
        SECOND_REBUILT_PDF_SHA256,
        REBUILT_PDF_PAGES,
        (TITLE, "Dataset statistics", "Performance Results of All Models"),
    )
    if rebuilt_text != second_rebuilt_text:
        raise ValueError("independent manuscript rebuild text differs")
    if {pdftotext_sha256(rebuilt_pdf), pdftotext_sha256(second_rebuilt_pdf)} != {REBUILT_TEXT_SHA256}:
        raise ValueError("independent manuscript pdftotext output differs")
    if pdf_without_trailer_id(rebuilt_pdf) != pdf_without_trailer_id(second_rebuilt_pdf):
        raise ValueError("independent manuscript PDFs differ beyond the trailer ID")
    normalized_pdf_text(
        thesis_pdf,
        THESIS_SHA256,
        THESIS_PAGES,
        ("Emergent Abilities of Large Language Models", "ESSAY THREE - FINVISION"),
    )
    source_rows = paper_source_inventory(archive, source_dir)
    validate_source_claims(source_dir, thesis_text)
    finagent_values = finagent_lineage(finagent_ledger)
    stats_rows, market_rows = yahoo_and_dataset_audit(downloads)
    performance_rows = performance_ledger(True, finagent_values)
    prompt_rows = prompt_inventory()
    method_rows = method_specification_audit()
    access_rows = artifact_access_audit()
    discovery_rows = discovery_evidence(downloads, evidence)

    if len(paper_text) < 20_000:
        raise ValueError("official paper text extraction unexpectedly short")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "paper_source_inventory.csv", source_rows)
    write_csv(output_dir / "artifact_access_audit.csv", access_rows)
    write_csv(output_dir / "discovery_evidence.csv", discovery_rows)
    write_csv(output_dir / "dataset_statistics_audit.csv", stats_rows)
    write_csv(output_dir / "published_performance_ledger.csv", performance_rows)
    write_csv(output_dir / "market_baseline_diagnostic.csv", market_rows)
    write_csv(output_dir / "method_specification_audit.csv", method_rows)
    write_csv(output_dir / "prompt_inventory.csv", prompt_rows)

    source_provenance = {
        "title": TITLE,
        "authors": AUTHORS,
        "doi": DOI,
        "doi_url": DOI_URL,
        "arxiv_record": ARXIV_RECORD,
        "arxiv_pdf_url": ARXIV_PDF_URL,
        "arxiv_source_url": ARXIV_SOURCE_URL,
        "official_pdf_sha256": PAPER_SHA256,
        "official_pdf_pages": PAPER_PAGES,
        "arxiv_source_sha256": SOURCE_ARCHIVE_SHA256,
        "arxiv_source_files": SOURCE_FILES,
        "arxiv_source_uncompressed_bytes": SOURCE_BYTES,
        "first_clean_rebuild_sha256": REBUILT_PDF_SHA256,
        "second_clean_rebuild_sha256": SECOND_REBUILT_PDF_SHA256,
        "rebuild_pages": REBUILT_PDF_PAGES,
        "pdftotext_sha256_both_rebuilds": REBUILT_TEXT_SHA256,
        "clean_rebuild_comparison": "all bytes identical except the PDF trailer ID; extracted text identical",
        "rebuild_parameters": {
            "latex_passes": 3,
            "SOURCE_DATE_EPOCH": 1730155920,
            "FORCE_SOURCE_DATE": 1,
            "TZ": "UTC",
        },
        "author_thesis_url": THESIS_URL,
        "author_thesis_sha256": THESIS_SHA256,
        "author_thesis_pages": THESIS_PAGES,
        "author_thesis_finvision_pdf_pages": "87-106",
        "visual_qa": {
            "official_paper_all_pages": "pass_no_clipping_overlap_or_invisible_text",
            "deterministic_rebuild_all_pages": "pass_matches_manuscript_layout_without_arxiv_margin_stamp",
            "thesis_all_133_pages_contact_sheet": "pass_no_corrupt_or_clipped_pages",
            "thesis_finvision_chapter_20_pages": "pass_legible; landscape performance table rotation is source-native",
        },
        "source_archive_contains_system_code": False,
        "source_archive_interpretation": "manuscript/typesetting support/figures only",
    }
    write_json(output_dir / "source_provenance.json", source_provenance)

    native_execution = {
        "manuscript_source_rebuilt": True,
        "manuscript_rebuild_repeated_byte_identical": False,
        "manuscript_rebuild_byte_difference": "PDF trailer ID only",
        "manuscript_rebuild_text_identical": True,
        "manuscript_rebuild_is_system_execution": False,
        "public_finvision_system_source_found": False,
        "finvision_pipeline_executed": False,
        "llm_calls_made": 0,
        "original_news_rows_loaded": 0,
        "native_agent_actions_loaded": 0,
        "native_portfolio_trajectories_loaded": 0,
        "current_yahoo_diagnostic_run": True,
        "current_yahoo_diagnostic_is_faithful_replication": False,
        "strict_boundary": "typesetting reconstruction, thesis corroboration, value lineage, and current-input diagnostics receive zero paper-result credit",
    }
    write_json(output_dir / "native_execution.json", native_execution)

    display_matches = sum(bool(row["display_match"]) for row in market_rows)
    precise_rounding = sum(row["external_lineage_status"] == "two_decimal_rounding_match" for row in performance_rows)
    manifest: dict[str, Any] = {
        "audit": "FinVision primary-source, method-specification, and result-fidelity audit",
        "overall_status": "not_reproduced_no_public_system_source_frozen_inputs_or_trajectories",
        "full_end_to_end_pipeline_reproduced": False,
        "paper_and_prompt_provenance_recovered": True,
        "published_performance_cells": len(performance_rows),
        "finvision_own_performance_cells": sum(row["method"].startswith("FinVision") for row in performance_rows),
        "published_performance_cells_faithfully_regenerated": 0,
        "finvision_own_cells_faithfully_regenerated": 0,
        "thesis_corroborated_cells": sum(row["author_thesis_corroborated"] for row in performance_rows),
        "external_finagent_transcription_cells_confirmed": sum(row["method"] == "FinAgent" for row in performance_rows),
        "external_finagent_cells_conventionally_rounded_to_display": precise_rounding,
        "external_finagent_cells_with_nonstandard_truncation": 9 - precise_rounding,
        "current_yahoo_market_diagnostic_cells": len(market_rows),
        "current_yahoo_diagnostic_display_matches": display_matches,
        "current_yahoo_diagnostic_faithful_credit": 0,
        "paper_dataset_statistic_cells": len(stats_rows),
        "paper_trading_day_count_cells_differing_from_literal_sessions": sum(row["dimension"] == "trading_days" for row in stats_rows),
        "paper_news_count_cells_unreproduced": sum(row["dimension"] == "news_articles" for row in stats_rows),
        "prompt_templates_recovered": len(prompt_rows),
        "actual_llm_requests_recovered": 0,
        "actual_llm_responses_recovered": 0,
        "llm_calls_made": 0,
        "public_system_source_files_recovered": 0,
        "arxiv_manuscript_source_files": len(source_rows),
        "arxiv_manuscript_source_is_system_code": False,
        "author_thesis_is_independent_replication": False,
        "finagent_value_lineage_is_finvision_reproduction": False,
        "market_diagnostic_is_finvision_reproduction": False,
        "visual_qa_passed": True,
        "interpretation": (
            "The original paper, its complete arXiv manuscript source, five prompt templates, "
            "official metadata, and an author thesis repeating all 72 performance cells are pinned. "
            "The archive contains no FinVision implementation. No frozen news/price inputs, runtime "
            "LLM requests/responses, action paths, or portfolio trajectories are public in the pinned "
            "evidence, so zero performance cells are faithfully regenerated."
        ),
    }

    readme = f"""# FinVision paper-level replication audit

Overall verdict: **not reproduced**. This package pins the original paper, its
complete arXiv manuscript source, the author's thesis, public artifact searches,
official model documentation, and current Yahoo price responses. It faithfully
reconstructs the paper as a document and recovers all five printed prompt templates,
but it does not recover or execute the FinVision system.

## What is recovered

- The official {PAPER_PAGES}-page paper is pinned at SHA-256 `{PAPER_SHA256}`.
- The {SOURCE_FILES}-file arXiv v1 bundle is byte-checked against its exact
  extraction. Two clean, three-pass LaTeX builds produce the same rendered content
  and identical extracted text. Their raw PDFs differ only in the generated trailer
  ID, so this audit explicitly does **not** call them byte-identical. All original
  and rebuilt pages passed visual inspection.
- The author's {THESIS_PAGES}-page thesis is pinned at SHA-256 `{THESIS_SHA256}`.
  Its FinVision chapter repeats all 72 displayed result cells and the same method
  and prompts. This is author-side corroboration, not an independent replication.
- All five Appendix prompt templates are recovered. Their runtime values, actual
  API requests/responses, model request IDs, and generated daily traces are absent.
- The nine displayed FinAgent cells trace to FinAgent Appendix Table 7. Eight are
  conventional two-decimal roundings; AAPL ARR is printed as 31.89 from 31.8972,
  a truncation/nonstandard transcription. This lineage does not reproduce FinVision.

## Why zero of 72 result cells receive reproduction credit

- The arXiv bundle contains manuscript/typesetting files and figures only—no
  LangGraph implementation, dependency lock, runnable configuration, or data code.
- No original news rows, price snapshot, chart inputs, LLM requests/responses,
  BUY/SELL/HOLD actions, position sizes, fills, rewards, cash ledger, or equity
  trajectory are released. The commented `result.png` is a picture, not an exact
  action/portfolio record from which the metrics can be regenerated.
- Core execution choices are unspecified: initial capital; price field and
  adjustment; fill timing; share rounding; long/short constraints; costs and
  slippage; reward and cash equations; seeds; dependency versions; and baseline
  hyperparameters. ARR omits numeric C, while Sharpe omits risk-free rate,
  frequency, annualization, and variance convention.
- The paper names mutable model aliases (`gpt-4o-mini`, `o1-mini`) rather than
  immutable snapshots. Official documentation now marks o1-mini deprecated.
  The paper's historical run therefore cannot be identified from the alias alone.

## Dataset and current-price diagnostic

The stated seven months is the **testing** window inside a nine-month overall
window; those statements are consistent. The unresolved count issue is different:
the paper reports 42 warm-up and 145 test trading days for every ticker, while the
pinned Yahoo responses contain 41 and 147 literal exchange sessions over the
printed inclusive dates. The paper does not state a transformation or endpoint
convention that resolves those counts.

A deliberately separate diagnostic applies one plausible metric convention to
current, hash-pinned Yahoo adjusted closes. {display_matches}/9 Market cells match
at the paper's displayed precision. This receives **zero faithful-replication
credit** because the original price snapshot/field and metric conventions are not
specified; matches against a later historical feed cannot stand in for the missing
original input and portfolio path.

## Public-artifact search boundary

Current author GitHub and Hugging Face inventories, exact-title/arXiv searches,
Software Heritage, Wayback, and value/model code searches did not recover an
attributable implementation or dataset. The paper itself prints no code URL and
makes no release promise. This is evidence that no public artifact was recovered,
not proof that private or deleted artifacts never existed.

Regenerate with `scripts/audit_finvision_paper.py`. `--strict` intentionally exits
nonzero while the paper remains unreproduced.
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
        "--paper-pdf",
        type=Path,
        default=ROOT / "literature_review/papers/40_a_multi_agent_framework_for_stock_market_prediction.pdf",
    )
    parser.add_argument(
        "--scratch-root",
        type=Path,
        default=Path(os.environ.get("FINVISION_AUDIT_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/finvision_audit")),
    )
    parser.add_argument(
        "--finagent-ledger",
        type=Path,
        default=ROOT / "paper_runs/paper_replication_audits/finagent/paper_numeric_table_conformance.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "paper_runs/paper_replication_audits/finvision",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.paper_pdf.resolve(),
        args.scratch_root.resolve(),
        args.finagent_ledger.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return int(args.strict and not manifest["full_end_to_end_pipeline_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
