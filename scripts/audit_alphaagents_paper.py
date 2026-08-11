#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for arXiv:2508.11152v1.

The official TeX source is useful specification evidence: it rebuilds the
paper and exposes portfolio-membership tables that were commented out of the
PDF.  It does not contain the author pipeline, data snapshots, agent outputs,
raw return series, or the values underlying the performance plots.  This
audit therefore keeps document/source reconstruction separate from native
experimental reproduction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader


PAPER_URL = "https://arxiv.org/abs/2508.11152v1"
PDF_URL = "https://arxiv.org/pdf/2508.11152v1"
HTML_URL = "https://arxiv.org/html/2508.11152v1"
SOURCE_URL = "https://export.arxiv.org/e-print/2508.11152v1"
DOI = "10.48550/arXiv.2508.11152"
EXPECTED_PDF_SHA256 = "ce48953985eaac0faf04dbf7c1b8c4e94396cd7924d56dee37d767112a3fed65"
EXPECTED_PAGE_SHA256 = "3c5d5e56869ddadf77e88c68f0b5ff27952b08a9131543cef73cc3e32121c6b8"
EXPECTED_SOURCE_SHA256 = "ce5a31c38b75ad89496dc6176a081f83c0afe084067a01f92e42782f5478b5f5"
EXPECTED_TEX_SHA256 = "22f01c9d54fd28e86a461f294e2477585f19979f9c38f08f8b4661101b4d07c0"
EXPECTED_PAGES = 9

GITHUB_QUERIES = (
    "2508.11152",
    '"AlphaAgents: Large Language Model based Multi-Agents for Equity Portfolio Constructions"',
    "AlphaAgents equity portfolio",
    "AlphaAgents BlackRock",
    '"Tianjiao Zhao" AlphaAgents',
    '"Jingrao Lyu" AlphaAgents',
    '"Dhagash Mehta" AlphaAgents',
)

EXPECTED_COMMUNITY_REPOSITORIES = {
    "DanielTobi0/BlackRock-Finance-Agent",
    "Rynhalt/AlphaAgents",
    "hitmannoob/AlphaAgent",
    "sarthakpadhi/AlphaAgent",
    "vedurmaliya/alpha-agents",
}

COMMUNITY_SNAPSHOTS = (
    {
        "repository": "sarthakpadhi/AlphaAgent",
        "directory": "sarthakpadhi__AlphaAgent",
        "commit": "4c61ce28e49c07797b7153653f5bf7f3a742708c",
        "relationship": "unaffiliated community reimplementation",
        "material_divergence": "CrewAI replaces AutoGen; gpt-4o-mini replaces GPT-4o; India .NS/live-data workflow; no paper portfolio-result reproduction",
    },
    {
        "repository": "DanielTobi0/BlackRock-Finance-Agent",
        "directory": "DanielTobi0__BlackRock-Finance-Agent",
        "commit": "82cde8fd1b8dbcb6ebf94bfcb911957e3f1e5aac",
        "relationship": "unaffiliated community reimplementation",
        "material_divergence": "2025-10-31--2026-02-27 defaults, different 15-stock universe, gpt-5-mini structured outputs, FMP/Firecrawl data; charts are not the paper experiment",
    },
    {
        "repository": "Rynhalt/AlphaAgents",
        "directory": "Rynhalt__AlphaAgents",
        "commit": "2eca2318a3eebdb60ab1d30a1084d2e1ede2d7c2",
        "relationship": "unaffiliated community prototype",
        "material_divergence": "placeholder universe, simulated filings and deterministic mock 63-day returns; no paper data or performance paths",
    },
    {
        "repository": "hitmannoob/AlphaAgent",
        "directory": "hitmannoob__AlphaAgent",
        "commit": "",
        "relationship": "unaffiliated empty repository",
        "material_divergence": "default branch contains no commits or implementation",
    },
    {
        "repository": "vedurmaliya/alpha-agents",
        "directory": "vedurmaliya__alpha-agents",
        "commit": "8c66c28bdfe9a18814f9acdaa02b54fa3670f06c",
        "relationship": "unaffiliated community reimplementation",
        "material_divergence": "LangGraph/Groq GPT-OSS-120B replaces AutoGen/GPT-4o; SPY replaces the custom 15-stock benchmark; analysis uses current rather than historical snapshots",
    },
)

BENCHMARK = (
    "MSFT", "CDNS", "INTU", "CRM", "ORCL", "NOW", "CRWD", "MDB",
    "ADBE", "ADSK", "NTNX", "DDOG", "PANW", "SNOW", "ZS",
)
RISK_NEUTRAL_FUNDAMENTAL = (
    "MSFT", "CDNS", "INTU", "CRM", "ORCL", "NOW", "CRWD", "MDB",
    "ADBE", "ADSK", "NTNX", "DDOG", "PANW", "ZS",
)
RISK_NEUTRAL_MULTI = (
    "MSFT", "CDNS", "INTU", "CRM", "ORCL", "NOW", "CRWD", "MDB",
    "ADBE", "ADSK", "NTNX", "DDOG", "PANW",
)
RISK_AVERSE_VALUATION = (
    "MSFT", "CDNS", "INTU", "CRM", "NOW", "ADBE", "ADSK", "NTNX", "PANW", "ZS",
)
RISK_AVERSE_FUNDAMENTAL = ("CDNS", "NOW", "ADBE", "ADSK")
RISK_AVERSE_MULTI = ("MSFT", "INTU", "NOW", "MDB", "ADBE", "ADSK")

PORTFOLIOS = (
    ("all", "benchmark", BENCHMARK, "explicit_commented_source_table"),
    ("risk-neutral", "valuation", BENCHMARK, "source_says_same_as_benchmark"),
    ("risk-neutral", "fundamental", RISK_NEUTRAL_FUNDAMENTAL, "explicit_commented_source_table"),
    ("risk-neutral", "multi-agent", RISK_NEUTRAL_MULTI, "explicit_commented_source_table"),
    ("risk-averse", "valuation", RISK_AVERSE_VALUATION, "explicit_commented_source_table"),
    ("risk-averse", "fundamental", RISK_AVERSE_FUNDAMENTAL, "explicit_commented_source_table"),
    ("risk-averse", "multi-agent", RISK_AVERSE_MULTI, "explicit_commented_source_table"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pdf_text(path: Path) -> tuple[str, int, dict[str, Any]]:
    reader = PdfReader(path)
    return (
        "\n".join(page.extract_text() or "" for page in reader.pages),
        len(reader.pages),
        dict(reader.metadata or {}),
    )


def validate_pdf(text: str, pages: int) -> None:
    if pages != EXPECTED_PAGES:
        raise ValueError(f"official paper page count changed: {pages}")
    required = (
        "AlphaAgents",
        "Microsoft AutoGen",
        "GPT4o",
        "randomly selected 15 stocks",
        "February 1, 2024",
        "rolling Sharpe ratio",
        "Risk neutral vs Risk averse",
    )
    normalized = re.sub(r"\s+", " ", text)
    missing = [token for token in required if token not in normalized]
    if missing:
        raise ValueError(f"official paper extraction changed: {missing}")


def read_source(source_tar: Path) -> tuple[str, list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    tex = ""
    with tarfile.open(source_tar, "r:*") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        for member in sorted(members, key=lambda item: item.name):
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"unable to read source member {member.name}")
            payload = extracted.read()
            suffix = Path(member.name).suffix.lower()
            role = {
                ".tex": "paper_source",
                ".bib": "bibliography",
                ".bbl": "compiled_bibliography",
                ".png": "raster_figure_or_screenshot",
                ".json": "arxiv_build_manifest",
            }.get(suffix, "other")
            rows.append(
                {
                    "source_member": member.name,
                    "bytes": str(len(payload)),
                    "sha256": bytes_sha256(payload),
                    "role": role,
                    "contains_machine_readable_experimental_values": "no",
                }
            )
            if member.name == "sample-authordraft.tex":
                tex = payload.decode("utf-8")
    if not tex:
        raise ValueError("official source archive lacks sample-authordraft.tex")
    if bytes_sha256(tex.encode("utf-8")) != EXPECTED_TEX_SHA256:
        raise ValueError("official AlphaAgents TeX hash changed")
    return tex, rows


def validate_source_portfolios(tex: str) -> None:
    for profile, agent, tickers, source_status in PORTFOLIOS:
        if source_status == "source_says_same_as_benchmark":
            if "Valuation Agent &Same as benchmark" not in tex:
                raise ValueError("risk-neutral valuation source row changed")
            continue
        joined = ", ".join(tickers)
        if joined not in tex:
            raise ValueError(f"source-only portfolio changed: {profile}/{agent}")


def portfolio_rows() -> list[dict[str, str]]:
    rows = []
    for profile, agent, tickers, source_status in PORTFOLIOS:
        rows.append(
            {
                "risk_profile": profile,
                "portfolio": agent,
                "ticker_count": str(len(tickers)),
                "tickers_in_source_order": "|".join(tickers),
                "source_status": source_status,
                "pdf_visibility": "commented_out_not_visible_in_official_pdf",
                "specification_credit": "source_only",
                "native_agent_output_credit": "no",
                "performance_result_credit": "no",
            }
        )
    if len(rows) != 7 or sum(int(row["ticker_count"]) for row in rows) != 77:
        raise AssertionError("AlphaAgents source portfolio census changed")
    return rows


def result_series_rows() -> list[dict[str, str]]:
    definitions = (
        ("Figure 6", "6", "return-neutral.png", "cumulative return", "risk-neutral", "valuation/benchmark"),
        ("Figure 6", "6", "return-neutral.png", "cumulative return", "risk-neutral", "fundamental"),
        ("Figure 6", "6", "return-neutral.png", "cumulative return", "risk-neutral", "multi-agent"),
        ("Figure 6", "6", "sharpe-neutral.png", "rolling Sharpe", "risk-neutral", "valuation/benchmark"),
        ("Figure 6", "6", "sharpe-neutral.png", "rolling Sharpe", "risk-neutral", "fundamental"),
        ("Figure 6", "6", "sharpe-neutral.png", "rolling Sharpe", "risk-neutral", "multi-agent"),
        ("Figure 7", "7", "return-averse.png", "cumulative return", "risk-averse", "valuation"),
        ("Figure 7", "7", "return-averse.png", "cumulative return", "risk-averse", "fundamental"),
        ("Figure 7", "7", "return-averse.png", "cumulative return", "risk-averse", "multi-agent"),
        ("Figure 7", "7", "return-averse.png", "cumulative return", "risk-averse", "benchmark"),
        ("Figure 7", "7", "sharpe-averse.png", "rolling Sharpe", "risk-averse", "valuation"),
        ("Figure 7", "7", "sharpe-averse.png", "rolling Sharpe", "risk-averse", "fundamental"),
        ("Figure 7", "7", "sharpe-averse.png", "rolling Sharpe", "risk-averse", "multi-agent"),
        ("Figure 7", "7", "sharpe-averse.png", "rolling Sharpe", "risk-averse", "benchmark"),
        ("Figure 8", "7", "valuation.png", "cumulative return", "risk-neutral", "valuation"),
        ("Figure 8", "7", "valuation.png", "cumulative return", "risk-averse", "valuation"),
        ("Figure 8", "7", "fundamental.png", "cumulative return", "risk-neutral", "fundamental"),
        ("Figure 8", "7", "fundamental.png", "cumulative return", "risk-averse", "fundamental"),
        ("Figure 8", "7", "multi.png", "cumulative return", "risk-neutral", "multi-agent"),
        ("Figure 8", "7", "multi.png", "cumulative return", "risk-averse", "multi-agent"),
    )
    return [
        {
            "figure": figure,
            "pdf_page": page,
            "official_source_asset": asset,
            "metric": metric,
            "risk_profile": profile,
            "portfolio": portfolio,
            "raw_values_released": "no",
            "native_reproduction_status": "not_reproduced_raster_line_only",
            "paper_result_credit": "no",
        }
        for figure, page, asset, metric, profile, portfolio in definitions
    ]


def configuration_rows() -> list[dict[str, str]]:
    definitions = (
        ("Section 2.1", "specialist agents", "3"),
        ("Section 2.2.3", "trading days per year", "252"),
        ("Section 2.2.4", "minimum speaking opportunities per agent", "2"),
        ("Section 3.2", "technology stocks", "15"),
        ("Section 3.2", "agent input month", "January 2024"),
        ("Section 3.2", "portfolio initialization", "2024-02-01"),
        ("Section 3.2", "monitoring horizon", "4 months"),
        ("Section 3.2", "risk-free tenor", "1 month Treasury"),
        ("Section 4.3", "sentiment/valuation historical horizon", "1--3 months"),
    )
    return [
        {
            "location": location,
            "configuration_field": field,
            "published_value": value,
            "audit_status": "enumerated_not_execution_verified",
            "paper_result_credit": "no",
        }
        for location, field, value in definitions
    ]


def prompt_rows() -> list[dict[str, str]]:
    definitions = (
        ("P001", "valuation role", "paper_text", "recovered", "As a valuation equity analyst", "role only; no risk profile"),
        ("P002", "sentiment role", "paper_text", "recovered", "As a sentiment equity analyst", "role only; no data-window/tool schema"),
        ("P003", "fundamental role", "paper_text", "recovered", "As a fundamental financial equity analyst", "role only; runtime RAG settings absent"),
        ("P004", "news summarization", "paper_text", "recovered", "provide a concise summary", "guiding fragment, not full runtime message"),
        ("P005", "multi-agent collaboration", "paper_text", "recovered", "You are a helpful assistant skilled at coordinating", "group prompt supplied"),
        ("P006", "multi-agent debate", "paper_text", "recovered", "Each agent can not decide for the whole group", "group prompt supplied"),
        ("P007", "Zscaler risk-neutral task", "Figure 3 screenshot", "recovered", "only two option either BUY or SELL", "screenshot-only example"),
        ("P008", "risk-neutral persona/instructions", "paper claim", "missing", "", "exact profile prompt not released"),
        ("P009", "risk-averse persona/instructions", "paper claim", "missing", "", "exact profile prompt not released"),
        ("P010", "risk-seeking persona/instructions", "paper claim", "missing", "", "tested then excluded; exact prompt not released"),
    )
    return [
        {
            "prompt_id": identifier,
            "purpose": purpose,
            "source_location": location,
            "recovery_status": status,
            "salient_fragment": fragment,
            "replication_boundary": boundary,
            "native_runtime_message_recovered": "no",
        }
        for identifier, purpose, location, status, fragment, boundary in definitions
    ]


def claim_rows() -> list[dict[str, str]]:
    definitions = (
        ("Q001", "Section 4.1", "Company Z January return", "13.56%", "single example; input price snapshot absent", "not_reproduced", "major"),
        ("Q002", "Section 4.1", "S&P 500 January return", "3.85%", "single comparison; provider/adjustment convention absent", "not_reproduced", "major"),
        ("Q003", "Section 4.1", "Company Z operating margin", "-14.5%", "filing accession and RAG trace absent", "not_reproduced", "major"),
        ("Q004", "Figure 6/Section 4.3", "risk-neutral multi-agent beats benchmark and single agents", "qualitative", "three raster curves; no raw values or inference", "not_reproduced", "blocking"),
        ("Q005", "Section 4.3", "risk-averse portfolios underperform benchmark", "qualitative", "four raster curves; no raw values or inference", "not_reproduced", "blocking"),
        ("Q006", "Section 4.3", "risk-averse multi-agent has lower volatility and reduced drawdowns", "qualitative", "no volatility or drawdown table/series is released", "not_verifiable", "blocking"),
        ("Q007", "Figure 8/Section 4.3", "risk-neutral portfolios consistently beat risk-averse counterparts", "qualitative", "six raster curves; no raw values", "not_reproduced", "blocking"),
        ("Q008", "Section 3.1", "Phoenix faithfulness and relevance scores were provided", "unreported", "zero score values, evaluator prompts, labels, or traces are reported", "not_verifiable", "blocking"),
        ("Q009", "Conclusion", "multi-agent debate improves analytical rigor", "qualitative", "no controlled ablation, repeated trials, or human-review statistics", "not_verifiable", "blocking"),
        ("Q010", "Method/Conclusion", "collaboration reduces hallucinations and cognitive bias", "qualitative", "no hallucination/bias measure or comparison is reported", "not_verifiable", "blocking"),
    )
    return [
        {
            "claim_id": identifier,
            "location": location,
            "claim": claim,
            "published_value": value,
            "audit_evidence": evidence,
            "assessment": assessment,
            "severity": severity,
            "paper_result_credit": "no",
        }
        for identifier, location, claim, value, evidence, assessment, severity in definitions
    ]


def issue_rows() -> list[dict[str, str]]:
    definitions = (
        ("ALPHAAGENTS-INT-001", "Section 4.2.1 vs commented source table", "fundamental agent expands upon the 15-stock benchmark", "source table lists a 14-stock strict subset, excluding SNOW", "direct_conflict", "blocking"),
        ("ALPHAAGENTS-INT-002", "Section 3.2", "sentiment agent was excluded because news coverage was insufficient", "next paragraph says a news-sentiment portfolio was constructed; result figures omit it", "direct_conflict", "blocking"),
        ("ALPHAAGENTS-INT-003", "Sections 2.2.3 and 2.2.5", "GPT-4o is the experiment LLM", "GPT 4-o is also called an embedding model, but no embedding endpoint/model is identified", "model_role_conflict", "blocking"),
        ("ALPHAAGENTS-INT-004", "Equations in Sections 3.2 and 4.3", "one-month Treasury rate is subtracted from portfolio return", "return frequency and conversion of the Treasury quote to the matching period are omitted", "unit_ambiguity", "blocking"),
        ("ALPHAAGENTS-INT-005", "Section 2.2.3 vs Figures 6--8", "annualized cumulative return formula is supplied", "result figures use cumulative return, but compounding/aggregation code is not supplied", "metric_path_underspecified", "blocking"),
        ("ALPHAAGENTS-INT-006", "Abstract vs Section 3.2", "performance is evaluated against established benchmarks", "the operative benchmark is the same randomly selected 15-stock pool with equal weights", "benchmark_language_overstates_design", "major"),
        ("ALPHAAGENTS-INT-007", "Section 3.2", "agents were trained using January 2024 data and news", "no parameter-training procedure, checkpoint, or distinction from prompting/inference is supplied", "terminology_ambiguous", "major"),
        ("ALPHAAGENTS-INT-008", "Section 4.3", "multi-agent risk-averse portfolio has lower volatility and reduced drawdowns than individual strategies", "no volatility/drawdown results are reported and the raster curves cannot establish that claim exactly", "claim_not_operationalized", "major"),
        ("ALPHAAGENTS-INT-009", "official TeX source", "figure cross-references uniquely identify figures", "active source repeats fig:enter-label three times and fig:risk-neutral-sharpe twice", "source_reference_conflict", "major"),
    )
    return [
        {
            "issue_id": identifier,
            "location": location,
            "paper_statement_a": statement_a,
            "paper_statement_b_or_missing_detail": statement_b,
            "assessment": assessment,
            "severity": severity,
            "replication_effect": "prevents_exact_native_reconstruction" if severity == "blocking" else "requires_explicit_interpretation",
        }
        for identifier, location, statement_a, statement_b, assessment, severity in definitions
    ]


def method_rows() -> list[dict[str, str]]:
    specs = [
        ("authoritative record", "arXiv:2508.11152v1 submitted 2025-08-15", "specified", "none"),
        ("authoritative PDF", "nine-page v1 PDF is pinned", "specified", "none"),
        ("authoritative TeX source", "v1 source archive is pinned and complete enough to compile", "specified", "none"),
        ("author-linked implementation", "paper and arXiv record link no implementation", "missing", "blocking"),
        ("author-linked data/results", "no data snapshot, agent outputs, or result arrays", "missing", "blocking"),
        ("document rebuild", "official TeX compiles to nine pages with near-identical extracted text", "specified", "none"),
        ("agent framework", "Microsoft AutoGen with AutoGen Studio", "specified", "major"),
        ("agent framework version", "not stated", "missing", "blocking"),
        ("group-chat topology", "three specialist agents plus group-chat assistant", "specified", "major"),
        ("speaker scheduling", "Round Robin and each agent speaks at least twice", "specified", "major"),
        ("termination semantics", "TERMINATE requested after consensus", "partial", "blocking"),
        ("maximum messages/rounds", "not stated", "missing", "blocking"),
        ("fundamental role prompt", "role text supplied", "specified", "major"),
        ("sentiment role prompt", "role text supplied", "specified", "major"),
        ("valuation role prompt", "role text supplied", "specified", "major"),
        ("collaboration coordinator prompt", "prompt text supplied", "specified", "major"),
        ("debate coordinator prompt", "prompt text supplied", "specified", "major"),
        ("risk-neutral prompt", "profile said to be embedded by prompt engineering; text absent", "missing", "blocking"),
        ("risk-averse prompt", "profile said to be embedded by prompt engineering; text absent", "missing", "blocking"),
        ("risk-seeking prompt", "tested and excluded; text absent", "missing", "blocking"),
        ("user task prompt", "one Zscaler screenshot example only", "partial", "blocking"),
        ("LLM model", "GPT-4o", "specified", "major"),
        ("LLM immutable snapshot", "no model revision or request date", "missing", "blocking"),
        ("LLM temperature", "not stated", "missing", "blocking"),
        ("LLM top_p", "not stated", "missing", "blocking"),
        ("LLM seed", "not stated", "missing", "blocking"),
        ("LLM token limits", "not stated", "missing", "blocking"),
        ("LLM retry/error policy", "not stated", "missing", "blocking"),
        ("tool schemas and executable implementations", "described narratively only", "missing", "blocking"),
        ("annualized return formula", "252-day formula supplied", "specified", "major"),
        ("annualized volatility formula", "daily standard deviation times sqrt(252)", "specified", "major"),
        ("valuation lookback", "later described as 1--3 months", "partial", "blocking"),
        ("valuation price/volume provider", "Yahoo Finance", "specified", "major"),
        ("Yahoo/yfinance version", "not stated", "missing", "blocking"),
        ("adjusted versus unadjusted prices", "not stated", "missing", "blocking"),
        ("corporate actions/missing prices", "not stated", "missing", "blocking"),
        ("calendar/time zone", "not stated", "missing", "major"),
        ("sentiment provider", "Bloomberg financial news", "specified", "major"),
        ("Bloomberg news snapshot", "no article IDs, timestamps, or bodies", "missing", "blocking"),
        ("sentiment lookback", "January 2024 implied for experiment", "partial", "blocking"),
        ("summarization prompt", "one guiding fragment supplied", "partial", "major"),
        ("reflection procedure", "reason/critique/refine described without iteration count", "partial", "blocking"),
        ("fundamental filings", "10-K/10-Q described", "specified", "major"),
        ("filing snapshots/accessions", "not released for 15 stocks", "missing", "blocking"),
        ("fundamental report pull", "yfinance API generation/checks described; code absent", "partial", "blocking"),
        ("RAG chunking", "section-based context chunking described", "partial", "blocking"),
        ("RAG retrieval settings", "index, chunk size, top-k, reranking absent", "missing", "blocking"),
        ("RAG embedding model", "GPT 4-o is named as embedding model without endpoint", "conflict", "blocking"),
        ("RAG domain guide", "claimed but not released", "missing", "blocking"),
        ("RAG evaluation framework", "Arize Phoenix", "specified", "major"),
        ("Phoenix version/evaluator configuration", "not stated", "missing", "blocking"),
        ("Phoenix faithfulness/relevance outputs", "no score values or traces", "missing", "blocking"),
        ("stock count", "15 technology stocks", "specified", "none"),
        ("stock identities", "77 memberships across seven portfolios recovered from commented TeX tables", "specified", "major"),
        ("sampling frame", "technology sector, but eligible universe not stated", "partial", "blocking"),
        ("stock sampling seed", "random selection claimed; seed absent", "missing", "major"),
        ("benchmark portfolio", "same 15-stock pool with equal weights", "specified", "major"),
        ("portfolio decision date", "2024-02-01", "specified", "none"),
        ("evaluation end", "four months and figures ending before 2024-06-01", "partial", "blocking"),
        ("portfolio asset weights", "equal among selected stocks", "specified", "major"),
        ("decision labels", "BUY or SELL; no HOLD in screenshot", "specified", "major"),
        ("sentiment portfolio inclusion", "paper both excludes and says it was constructed", "conflict", "blocking"),
        ("risk-neutral memberships", "three portfolios recovered from commented source", "specified", "major"),
        ("risk-averse memberships", "three portfolios recovered from commented source", "specified", "major"),
        ("rebalancing", "single initialization implied; drift/rebalance treatment unstated", "partial", "blocking"),
        ("execution timing/price", "not stated", "missing", "blocking"),
        ("transaction costs/slippage", "not stated", "missing", "blocking"),
        ("dividends/corporate-action adjustment", "not stated", "missing", "blocking"),
        ("daily portfolio return aggregation", "equal weights stated; implementation absent", "partial", "blocking"),
        ("cumulative return formula", "not stated for Figures 6--8", "missing", "blocking"),
        ("overall Sharpe formula", "mean return minus risk-free rate over standard deviation", "specified", "major"),
        ("rolling Sharpe formula", "sample standard deviation equation supplied", "specified", "major"),
        ("rolling window length", "symbol w only; value absent", "missing", "blocking"),
        ("return frequency", "plots appear daily; not stated in metric definition", "partial", "blocking"),
        ("risk-free source series", "one-month Treasury named; exact series/provider absent", "partial", "blocking"),
        ("risk-free rate conversion", "periodicity conversion not stated", "missing", "blocking"),
        ("Sharpe annualization", "no sqrt(252) factor in printed Sharpe equations", "specified", "major"),
        ("raw equity prices", "not released", "missing", "blocking"),
        ("raw portfolio return paths", "not released", "missing", "blocking"),
        ("raw rolling Sharpe paths", "not released", "missing", "blocking"),
        ("performance plot values", "20 line series released only as seven raster panels", "missing", "blocking"),
        ("agent recommendations", "source exposes final membership lists but not per-agent messages/decisions", "partial", "blocking"),
        ("debate histories", "claimed as supplementary output but not attached to record", "missing", "blocking"),
        ("human review protocol", "human review claimed; raters/instructions/outcomes absent", "missing", "blocking"),
        ("RAG evaluation raw results", "not released", "missing", "blocking"),
        ("repeated trials/random seeds", "none stated", "missing", "blocking"),
        ("uncertainty/statistical testing", "none reported", "missing", "blocking"),
        ("community implementations", "five unaffiliated repositories found; all materially diverge", "partial", "blocking"),
        ("local proxy relation", "two M0 narrative translations invent factor formulas, monthly deciles, weights, and a long-short return stream", "partial", "blocking"),
    ]
    return [
        {
            "dimension": dimension,
            "paper_or_source_specification": detail,
            "assessment": assessment,
            "severity": severity,
            "replication_implication": (
                "cannot_exactly_reproduce" if severity == "blocking" else
                "requires_interpretation_or_external_source" if severity == "major" else
                "directly_specified"
            ),
        }
        for dimension, detail, assessment, severity in specs
    ]


def github_rows(search_dir: Path) -> tuple[list[dict[str, str]], set[str]]:
    rows = []
    repositories: set[str] = set()
    for query in GITHUB_QUERIES:
        suffix = hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]
        path = search_dir / f"github_{suffix}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        names = sorted(item["full_name"] for item in payload.get("items", []))
        repositories.update(names)
        rows.append(
            {
                "query": query,
                "response_file": path.name,
                "response_sha256": sha256(path),
                "total_count": str(payload["total_count"]),
                "incomplete_results": str(payload["incomplete_results"]).lower(),
                "repository_names": "|".join(names),
                "author_linked_repository_found": "no",
                "evidence_use": "search_snapshot_requires_manual_author_link_review",
            }
        )
    if any(row["incomplete_results"] != "false" for row in rows):
        raise ValueError("GitHub search was incomplete")
    if repositories != EXPECTED_COMMUNITY_REPOSITORIES:
        raise ValueError(f"GitHub repository set changed; inspect before rerouting: {sorted(repositories)}")
    return rows, repositories


def git_head(path: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def community_rows(community_dir: Path) -> list[dict[str, str]]:
    rows = []
    for snapshot in COMMUNITY_SNAPSHOTS:
        path = community_dir / snapshot["directory"]
        observed = git_head(path)
        if observed != snapshot["commit"]:
            raise ValueError(
                f"community snapshot changed for {snapshot['repository']}: {observed}"
            )
        rows.append(
            {
                "repository": snapshot["repository"],
                "snapshot_commit": observed,
                "relationship": snapshot["relationship"],
                "material_divergence": snapshot["material_divergence"],
                "author_linked": "no",
                "native_paper_pipeline": "no",
                "paper_result_series_reproduced": "0",
                "paper_result_credit": "no",
            }
        )
    return rows


def source_build_audit(official_pdf: Path, rebuilt_pdf: Path, tex: str) -> dict[str, Any]:
    official_text, official_pages, _ = pdf_text(official_pdf)
    rebuilt_text, rebuilt_pages, rebuilt_meta = pdf_text(rebuilt_pdf)
    def tokens(value: str) -> list[str]:
        return re.findall(r"\w+", value.lower())
    official_counter = Counter(tokens(official_text))
    rebuilt_counter = Counter(tokens(rebuilt_text))
    intersection = sum((official_counter & rebuilt_counter).values())
    union = sum((official_counter | rebuilt_counter).values())
    active_labels = []
    for line in tex.splitlines():
        if not line.lstrip().startswith("%"):
            active_labels.extend(re.findall(r"\\label\{([^}]+)\}", line))
    duplicates = {
        label: count for label, count in sorted(Counter(active_labels).items()) if count > 1
    }
    title = str(rebuilt_meta.get("/Title", ""))
    if rebuilt_pages != official_pages or "AlphaAgents" not in title:
        raise ValueError("official source rebuild no longer matches paper structure")
    return {
        "compiler_declared_by_arxiv": "pdflatex",
        "texlive_declared_by_arxiv": "2023",
        "local_compiler_environment": "Bouchet texlive/20240312-GCC-13.3.0",
        "source_document_rebuild_succeeded": True,
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "rebuilt_pdf_sha256": sha256(rebuilt_pdf),
        "token_multiset_intersection": intersection,
        "token_multiset_union": union,
        "token_multiset_jaccard": intersection / union,
        "active_duplicate_labels": duplicates,
        "document_rebuild_credit": True,
        "experimental_reproduction_credit": False,
        "boundary": "rebuilding the manuscript does not reconstruct the agent pipeline or plotted data",
    }


def build(
    paper_pdf: Path,
    official_page: Path,
    source_tar: Path,
    source_build_pdf: Path,
    github_dir: Path,
    community_dir: Path,
    output: Path,
) -> dict[str, Any]:
    if sha256(paper_pdf) != EXPECTED_PDF_SHA256:
        raise ValueError("official AlphaAgents PDF hash changed")
    if sha256(official_page) != EXPECTED_PAGE_SHA256:
        raise ValueError("official AlphaAgents arXiv page hash changed")
    if sha256(source_tar) != EXPECTED_SOURCE_SHA256:
        raise ValueError("official AlphaAgents source archive hash changed")

    text, pages, _ = pdf_text(paper_pdf)
    validate_pdf(text, pages)
    tex, source_files = read_source(source_tar)
    validate_source_portfolios(tex)
    portfolios = portfolio_rows()
    results = result_series_rows()
    configs = configuration_rows()
    prompts = prompt_rows()
    claims = claim_rows()
    issues = issue_rows()
    methods = method_rows()
    searches, repositories = github_rows(github_dir)
    communities = community_rows(community_dir)
    source_build = source_build_audit(paper_pdf, source_build_pdf, tex)

    if len(results) != 20:
        raise AssertionError("AlphaAgents performance-series census must contain 20 series")
    if set(row["repository"] for row in communities) != repositories:
        raise AssertionError("community search and snapshot inventories diverge")

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "source_file_inventory.csv", source_files, list(source_files[0]))
    write_csv(output / "source_only_portfolio_inventory.csv", portfolios, list(portfolios[0]))
    write_csv(output / "plotted_result_series_conformance.csv", results, list(results[0]))
    write_csv(output / "numeric_configuration_audit.csv", configs, list(configs[0]))
    write_csv(output / "prompt_inventory.csv", prompts, list(prompts[0]))
    write_csv(output / "quantitative_and_qualitative_claim_audit.csv", claims, list(claims[0]))
    write_csv(output / "paper_internal_consistency_audit.csv", issues, list(issues[0]))
    write_csv(output / "method_specification_audit.csv", methods, list(methods[0]))
    write_csv(output / "source_search_inventory.csv", searches, list(searches[0]))
    write_csv(output / "community_reimplementation_inventory.csv", communities, list(communities[0]))
    write_json(output / "source_build_audit.json", source_build)

    source_provenance = {
        "official_record": PAPER_URL,
        "official_record_sha256": sha256(official_page),
        "official_pdf": PDF_URL,
        "official_pdf_sha256": sha256(paper_pdf),
        "official_html": HTML_URL,
        "official_source": SOURCE_URL,
        "official_source_sha256": sha256(source_tar),
        "official_tex_sha256": EXPECTED_TEX_SHA256,
        "doi": DOI,
        "version": "v1 only",
        "pages": pages,
        "source_files": len(source_files),
        "author_linked_code_or_data_found": False,
        "community_repositories_found": sorted(repositories),
        "github_repository_searches": searches,
    }
    write_json(output / "source_provenance.json", source_provenance)

    native = {
        "attempted": False,
        "reason": "no_author_linked_code_input_snapshots_agent_outputs_raw_returns_or_plot_arrays",
        "paper_result_credit": False,
        "source_document_rebuild_succeeded": True,
        "source_only_portfolios_recovered": len(portfolios),
        "source_only_ticker_memberships_recovered": sum(int(row["ticker_count"]) for row in portfolios),
        "published_table_result_cells": 0,
        "published_table_result_cells_reproduced": 0,
        "plotted_performance_series": len(results),
        "plotted_performance_series_reproduced": 0,
        "local_proxy_status": "M0_narrative_translation_only",
        "local_proxy_boundary": "two local factor formulas, monthly deciles, long-short weights, and return streams are researcher supplied and do not execute the paper's agents or recovered source portfolios",
    }
    write_json(output / "native_execution.json", native)

    method_counts = dict(sorted(Counter(row["assessment"] for row in methods).items()))
    severity_counts = dict(sorted(Counter(row["severity"] for row in methods).items()))
    manifest = {
        "paper": "AlphaAgents: Large Language Model based Multi-Agents for Equity Portfolio Constructions",
        "system_id": "SYS-ALPHA-AGENTS",
        "canonical_work_id": "CensusArxiv250811152",
        "audit_route": "paper_only_underspecified_with_official_source_portfolios_and_m0_local_proxies",
        "overall_fidelity": "source_document_rebuilt_and_7_portfolios_recovered_but_zero_of_20_plotted_performance_series_reproduced_no_native_agent_pipeline",
        "paper_result_credit": False,
        "official_pdf_pages": pages,
        "official_source_files": len(source_files),
        "source_document_rebuild_succeeded": True,
        "source_document_token_jaccard": source_build["token_multiset_jaccard"],
        "source_only_portfolios_recovered": len(portfolios),
        "source_only_ticker_memberships_recovered": sum(int(row["ticker_count"]) for row in portfolios),
        "published_table_result_cells": 0,
        "published_table_result_cells_reproduced": 0,
        "plotted_performance_series": len(results),
        "plotted_performance_series_reproduced": 0,
        "numeric_configuration_cells": len(configs),
        "prompt_fragments_recovered": sum(row["recovery_status"] == "recovered" for row in prompts),
        "risk_profile_prompts_recovered": 0,
        "claims_audited": len(claims),
        "internal_consistency_issues": len(issues),
        "blocking_internal_consistency_issues": sum(row["severity"] == "blocking" for row in issues),
        "method_dimensions": len(methods),
        "method_assessment_counts": method_counts,
        "method_severity_counts": severity_counts,
        "github_repository_searches": len(searches),
        "community_repositories_audited": len(communities),
        "author_linked_code_found": False,
        "source_provenance": "source_provenance.json",
        "source_build_audit": "source_build_audit.json",
        "native_execution": "native_execution.json",
    }
    write_json(output / "manifest.json", manifest)
    (output / "README.md").write_text(readme(manifest), encoding="utf-8")
    return manifest


def readme(manifest: dict[str, Any]) -> str:
    return f"""# AlphaAgents paper/source replication audit

This package audits arXiv:2508.11152v1, its nine-page PDF, the official TeX
source archive, and the public repository search surface. It is fail-closed:
manuscript compilation, source comments, raster plots, and unaffiliated
reimplementations are not native experimental results.

## Verdict

- **Native AlphaAgents performance reproduced: 0/{manifest['plotted_performance_series']} plotted series.**
- **Document fidelity is high:** the official TeX source compiles to nine pages
  and reaches {manifest['source_document_token_jaccard']:.4%} extracted-token
  multiset Jaccard against the arXiv PDF.
- **Portfolio specification improved:** seven commented-out TeX table rows
  recover {manifest['source_only_ticker_memberships_recovered']} ticker
  memberships, including the 15-stock benchmark and six agent/risk portfolios.
- No author-linked implementation, Bloomberg/filing/price snapshot, model
  snapshot, filled risk-profile prompt, agent output, debate trace, raw return
  path, Phoenix score, or plot array was found.
- Five GitHub repositories were found and audited as unaffiliated community
  work. Every one changes core data, models, orchestration, universe, dates, or
  benchmark; none reproduces a paper result series.
- The two existing local AlphaAgents candidates remain M0 narrative
  translations. Their factor formulas, monthly long-short deciles, weights,
  and return streams are not the paper's agent-picked portfolios.

## Material blockers and conflicts

- The PDF says the risk-neutral fundamental portfolio expands the benchmark;
  the official source table instead lists 14 of the benchmark's 15 stocks.
- The sentiment agent is said to be excluded for insufficient coverage, but
  the next paragraph says a sentiment portfolio was constructed; no sentiment
  curve appears in the figures.
- GPT-4o is named both as the experiment LLM and as an embedding model, without
  a separately identified embedding endpoint or snapshot.
- The rolling Sharpe window, return frequency, Treasury-series identifier and
  rate conversion, adjusted-price convention, cumulative-return implementation,
  costs, and execution details are absent.
- Claims about reduced drawdown, lower volatility, RAG faithfulness/relevance,
  hallucination reduction, and analytical rigor have no released measurements.

## Files

- `source_file_inventory.csv`: every member and hash in the official source tar.
- `source_build_audit.json`: manuscript rebuild and text-conformance evidence.
- `source_only_portfolio_inventory.csv`: seven recovered portfolio lists.
- `plotted_result_series_conformance.csv`: all 20 result lines in Figures 6--8.
- `prompt_inventory.csv`: seven recovered fragments and three missing risk prompts.
- `method_specification_audit.csv`: exact-replication requirements and blockers.
- `paper_internal_consistency_audit.csv`: paper/source conflicts and ambiguities.
- `community_reimplementation_inventory.csv`: five non-author implementations.
- `source_search_inventory.csv` and `source_provenance.json`: pinned provenance.
- `native_execution.json` and `manifest.json`: machine-readable evidence boundary.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-pdf", type=Path, required=True)
    parser.add_argument("--official-page", type=Path, required=True)
    parser.add_argument("--source-tar", type=Path, required=True)
    parser.add_argument("--source-build-pdf", type=Path, required=True)
    parser.add_argument("--github-search-dir", type=Path, required=True)
    parser.add_argument("--community-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(
        args.paper_pdf.resolve(),
        args.official_page.resolve(),
        args.source_tar.resolve(),
        args.source_build_pdf.resolve(),
        args.github_search_dir.resolve(),
        args.community_dir.resolve(),
        args.output_dir.resolve(),
    )
    print(compact_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
