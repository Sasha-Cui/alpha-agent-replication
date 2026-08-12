#!/usr/bin/env python3
"""Build a fail-closed source and result audit for Agentic AI Screening.

The arXiv bundle contains the manuscript, one workflow image, and bibliography,
not the experiment.  The paper links one public news dataset and prints one
December-2023 LLM-S prompt/output example.  Those recoverable components are
audited without promoting a later unaffiliated implementation to native code or
crediting any printed portfolio result as reproduced.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import tarfile
from collections import Counter
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path(
    "/nfs/roberts/scratch/pi_btk22/zc362/agentic_ai_screening_audit"
)
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/agentic_ai_screening"
WORK_ID = "CensusArxiv260323300"
SYSTEM_ID = "SYS-AGENTIC-AI-SCREENING"
ARXIV_ID = "2603.23300"
INDEPENDENT_COMMIT = "f6d056fae10e1ff2e77bf092e125ba09e93560d0"

PINS = {
    "primary/2603.23300v1.pdf": "4bc3147d386ab882c4c5589e43c79abe4af8ebf1f11ffcdf6fc5f496ef57ff1d",
    "primary/arxiv-abs.html": "e10462bb7a20ca1cac6cc7d3cc4ba8cce2a13bf5fd43478404666c7e73708b19",
    "primary/arxiv-api.xml": "e7e4dac0bf677e437a5b223d184591b8dd890954957ee3e5baad7ab0c04cf3a8",
    "source/2603.23300v1.tar": "7798b193b252c64332250ade11f17321f7ac1a47c7dcbf69dd34a57cb93758b5",
    "build/00README.json": "6a78b93ed7710cb1d9db39bad6ebf483cea429865948b6a4e8a6ca2faee97937",
    "build/agentic.bib": "37020249083f2f7d7878664d5ff11174fef0a9a202fe8ec3f1492f3155ffbab2",
    "build/Figure_workflow_1.0.png": "74467cd1f6a4d4cee7f5dc2d4b2f96d4ad28fd864ae6c0859c6e01a374f98a9a",
    "build/main.bbl": "1c7624296c4dbfb04103e49ae0e7ecd309322a842e70d5affc2395625550b929",
    "build/main.tex": "288f45134b467121335b2554dc796f9d69e48743d999cb2e85e584f8551701f3",
    "build/main.pdf": "03e14b0fa15a048a7b02381a3e56098d2c4b44ba8404676c71ea51d3630c05a4",
    "build/pass2.log": "c6ef38ee6c843e4b5005858799822827fd36bf857047dec11f5b791cde63fad4",
    "primary/gemini-2-flash-release.html": "036e07ffa71d3fd6214771d26c35387c0f85c7fd47868c8ef68a84222f640b47",
    "primary/gemini-2-flash-model.html": "20159c85d2ab1177fd7afa81a63ac5d228a455e6c1c41653f622b580771a29fa",
    "discovery/hf-dataset-api.json": "0f5a9deb13ca761934d9a2d2c6e775ec2a9dc74fe886768310bb9792285b1500",
    "discovery/hf-readme.md": "7659faedbb17e6523b81d275bf64e3158df6e222115a9ff4a7cacccf4294d065",
    "discovery/hf-news.jsonl": "c1585588777ef9be792aa4aac23f54b6ada7e469086e7887c95a31bb0cbbcae2",
    "discovery/github-arxiv-id.json": "3a79cd4f0865f2a78dde892ee39cf14345ae2b0b2781e9aa9204638cacb6901f",
    "discovery/github-authors.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-exact-title.json": "86dd4cb2c457c67cd10379b7f76cde29ad24f0a4e07cf8e7e60d9c70e073fd48",
    "discovery/alanhsieh2000_agentic_portfolio-repo.json": "7bb6bce65c066de6a643ff5215b8bcc84c9a3045750c10243abeb67ef8048705",
    "discovery/alanhsieh2000_agentic_portfolio-commits.json": "301ba4676478c16996873e36a4b08dcd951760a82374394f4af8335a6b1e8471",
    "discovery/independent-commit.txt": "5a06392a3f58e99ebaf4cb895dec746b3eccd5dc94ad8abfc2d1f73526c60c9c",
    "discovery/independent-pin/agentic_portfolio-f6d056f.tar.gz": "3ec98a054d0cd8ece3ef25c5f0130d529ce61f665cf9f9d65b7f3c97766d632b",
    "discovery/independent-pytest-isolated.log": "d23e186237171c67fd50d405fe0ced7425c9a805796dca6e5073c6356fa90af7",
    "discovery/lewisbakkero_sparsis-repo.json": "8a56c660eccb33ebb92ed5f922085e8adffe29466e3ad30b1076814302bd5e32",
    "discovery/lewisbakkero_sparsis-commits.json": "b9cdc50bfc2dd36615be8c177e6ff7c54e23d3e61397257c070a48f7720a4251",
}

SOURCE_MEMBERS = {
    "00README.json": 374,
    "agentic.bib": 37077,
    "Figure_workflow_1.0.png": 133920,
    "main.bbl": 13113,
    "main.tex": 210461,
}
METHODS = ("NW", "Residual NW", "Deep learning", "POET", "NLS")
OBJECTIVES = ("GMV", "MV", "MSR")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_tar(path: Path) -> dict[str, int]:
    members: dict[str, int] = {}
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe archive member: {member.name}")
            if member.isfile():
                members[member.name] = member.size
    return members


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    if safe_tar(scratch / "source/2603.23300v1.tar") != SOURCE_MEMBERS:
        raise ValueError("official source archive member inventory changed")
    independent = safe_tar(
        scratch / "discovery/independent-pin/agentic_portfolio-f6d056f.tar.gz"
    )
    if not any(name.endswith("/README.md") for name in independent):
        raise ValueError("independent archive no longer contains README.md")
    html = (scratch / "primary/arxiv-abs.html").read_text(errors="replace")
    for marker in ("Submitted on 24 Mar 2026", "2603.23300v1", "Mehmet Caner"):
        if marker not in html:
            raise ValueError(f"arXiv marker changed: {marker}")
    log = (scratch / "build/pass2.log").read_text(errors="replace")
    if "Output written on main.pdf (67 pages" not in log:
        raise ValueError("official source rebuild did not finish at 67 pages")
    release = (scratch / "primary/gemini-2-flash-release.html").read_text(
        errors="replace"
    )
    if 'article:published_time" content="2024-12-11"' not in release:
        raise ValueError("Gemini 2.0 Flash release date marker changed")
    model = (scratch / "primary/gemini-2-flash-model.html").read_text(
        errors="replace"
    )
    for marker in ("Knowledge cutoff</td>", "August 2024", "shut down June 1, 2026"):
        if marker not in model:
            raise ValueError(f"Gemini model marker changed: {marker}")
    pytest_log = (scratch / "discovery/independent-pytest-isolated.log").read_text()
    if "114 passed" not in pytest_log:
        raise ValueError("pinned independent test suite no longer records 114 passed")
    repo = json.loads(
        (scratch / "discovery/alanhsieh2000_agentic_portfolio-repo.json").read_text()
    )
    if (
        repo["full_name"] != "alanhsieh2000/agentic_portfolio"
        or repo["created_at"] != "2026-08-05T10:10:23Z"
    ):
        raise ValueError("independent repository identity changed")
    if INDEPENDENT_COMMIT not in (
        scratch / "discovery/independent-commit.txt"
    ).read_text():
        raise ValueError("independent implementation commit marker changed")
    return {"official_source_files": len(SOURCE_MEMBERS)}


def latex_number(cell: str) -> tuple[str, float]:
    rendered = re.sub(r"\\(?:textbf|bf)\s*\{([^{}]+)\}", r"\1", cell)
    rendered = rendered.replace("{", "").replace("}", "")
    rendered = rendered.split(r"\\", 1)[0].strip()
    match = re.search(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", rendered)
    if not match:
        raise ValueError(f"numeric value missing: {cell!r}")
    return match.group(), float(match.group())


def period_for(label: str) -> str:
    if label == "tab:long short":
        return "mixed_2020-01_to_2024-04_and_2015-01_to_2024-04"
    if label.endswith(" 10"):
        return "2015-01_to_2024-04"
    return "2020-01_to_2024-04"


def table_screen(label: str) -> str:
    return label.removeprefix("tab:").rsplit(" ", 1)[0] if label.endswith((" 5", " 10")) else label.removeprefix("tab:")


def parse_tables(tex: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, list[float]]]]:
    blocks = list(re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}", tex, re.S))
    if len(blocks) != 22:
        raise ValueError(f"expected 22 tables, found {len(blocks)}")
    results: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    sharpe_tables: dict[str, dict[str, list[float]]] = {}
    for table_number, match in enumerate(blocks, 1):
        block = match.group(1)
        label_match = re.search(r"\\label\{([^}]+)\}", block)
        caption_match = re.search(r"\\caption\{([^}]+)\}", block)
        if not label_match or not caption_match:
            raise ValueError(f"table {table_number} is missing label or caption")
        label = label_match.group(1)
        table_rows: dict[str, list[float]] = {}
        before = len(results)
        accepted = set(METHODS) | {"LLM-S", "Best 2 stage model"}
        for line in block.splitlines():
            cells = line.split("&")
            method = cells[0].strip()
            if method not in accepted:
                continue
            values = [latex_number(cell) for cell in cells[1:]]
            if label == "tab:long short":
                if len(values) != 4:
                    raise ValueError("long-short table width changed")
                fields = (
                    ("5_year", "Equal-Weighted"),
                    ("5_year", "Value-Weighted"),
                    ("10_year", "Equal-Weighted"),
                    ("10_year", "Value-Weighted"),
                )
                for (rendered, numeric), (horizon, weighting) in zip(values, fields):
                    results.append(
                        result_cell(
                            table_number, label, method, "Sharpe Ratio", weighting,
                            horizon, rendered, numeric
                        )
                    )
            else:
                if method not in METHODS or len(values) != 9:
                    raise ValueError(f"standard result table width changed: {label}/{method}")
                table_rows[method] = [numeric for _, numeric in values]
                fields = tuple(
                    (group, objective)
                    for group in ("Sharpe Ratio", "Returns", "Variance")
                    for objective in OBJECTIVES
                )
                for (rendered, numeric), (group, objective) in zip(values, fields):
                    results.append(
                        result_cell(
                            table_number, label, method, group, objective,
                            period_for(label), rendered, numeric
                        )
                    )
        count = len(results) - before
        expected = 8 if label == "tab:long short" else 45
        if count != expected:
            raise ValueError(f"expected {expected} cells in {label}, found {count}")
        if table_rows:
            sharpe_tables[label] = table_rows
        inventory.append(
            {
                "table_number": table_number,
                "label": label,
                "screen_or_comparison": table_screen(label),
                "period": period_for(label),
                "printed_numeric_cells": count,
                "native_cells_regenerated": 0,
                "caption": " ".join(caption_match.group(1).split()),
            }
        )
    if len(results) != 953 or len(sharpe_tables) != 21:
        raise ValueError(
            f"expected 953 result cells and 21 standard tables; found {len(results)}, {len(sharpe_tables)}"
        )
    return results, inventory, sharpe_tables


def result_cell(
    table_number: int,
    label: str,
    method: str,
    metric_group: str,
    objective: str,
    period: str,
    rendered: str,
    numeric: float,
) -> dict[str, Any]:
    return {
        "table_number": table_number,
        "table_label": label,
        "screen_or_comparison": table_screen(label),
        "period_or_horizon": period,
        "method_or_model": method,
        "metric_group": metric_group,
        "objective_or_weighting": objective,
        "rendered_value": rendered,
        "numeric_value": numeric,
        "author_native_pipeline_executed": False,
        "native_result_regenerated": False,
        "paper_result_credit": False,
    }


def arithmetic_rows(tables: Mapping[str, Mapping[str, list[float]]]) -> list[dict[str, Any]]:
    rows = []
    for label, methods in tables.items():
        for method in METHODS:
            values = methods[method]
            for index, objective in enumerate(OBJECTIVES):
                reported = values[index]
                annual_return = values[3 + index]
                variance = values[6 + index]
                implied = annual_return / math.sqrt(variance)
                difference = abs(reported - implied)
                rows.append(
                    {
                        "table_label": label,
                        "method": method,
                        "objective": objective,
                        "reported_sharpe": reported,
                        "reported_annual_return": annual_return,
                        "reported_variance": variance,
                        "implied_return_over_sqrt_variance": implied,
                        "absolute_difference": difference,
                        "within_0_002_tolerance": difference <= 0.002,
                    }
                )
    if len(rows) != 315:
        raise ValueError(f"expected 315 Sharpe arithmetic checks, found {len(rows)}")
    failures = [row for row in rows if not row["within_0_002_tolerance"]]
    keys = {(row["table_label"], row["method"], row["objective"]) for row in failures}
    expected = {("tab:llm 10", "NLS", "MSR"), ("tab:finbert+llm 10", "POET", "MV")}
    if keys != expected:
        raise ValueError(f"printed arithmetic mismatch set changed: {keys}")
    return rows


def sharpe(tables: Mapping[str, Mapping[str, list[float]]], label: str) -> list[float]:
    return [value for method in METHODS for value in tables[label][method][:3]]


def wins(tables: Mapping[str, Mapping[str, list[float]]], left: str, right: str) -> int:
    return sum(a > b for a, b in zip(sharpe(tables, left), sharpe(tables, right)))


def consistency_rows(tables: Mapping[str, Mapping[str, list[float]]]) -> list[dict[str, str]]:
    comparisons = {
        "llm_vs_baseline_5y": wins(tables, "tab:llm 5", "tab:baseline 5"),
        "logistic_vs_baseline_5y": wins(tables, "tab:logistic 5", "tab:baseline 5"),
        "llm_vs_analyst_5y": wins(tables, "tab:llm 5", "tab:analyst 5"),
        "llm_vs_novy_marx_5y": wins(tables, "tab:llm 5", "tab:novy marx 5"),
        "finbert_vs_baseline_5y": wins(tables, "tab:finbert 5", "tab:baseline 5"),
        "finbert_vs_logistic_5y": wins(tables, "tab:finbert 5", "tab:logistic 5"),
        "finbert_vs_analyst_5y": wins(tables, "tab:finbert 5", "tab:analyst 5"),
        "agentic_vs_baseline_5y": wins(tables, "tab:finbert+llm 5", "tab:baseline 5"),
        "agentic_vs_finbert_5y": wins(tables, "tab:finbert+llm 5", "tab:finbert 5"),
        "agentic_vs_llm_5y": wins(tables, "tab:finbert+llm 5", "tab:llm 5"),
        "finbert_vs_logistic_10y": wins(tables, "tab:finbert 10", "tab:logistic 10"),
        "finbert_vs_baseline_10y": wins(tables, "tab:finbert 10", "tab:baseline 10"),
    }
    expected = {
        "llm_vs_baseline_5y": 13, "logistic_vs_baseline_5y": 13,
        "llm_vs_analyst_5y": 15, "llm_vs_novy_marx_5y": 15,
        "finbert_vs_baseline_5y": 14, "finbert_vs_logistic_5y": 14,
        "finbert_vs_analyst_5y": 15, "agentic_vs_baseline_5y": 14,
        "agentic_vs_finbert_5y": 14, "agentic_vs_llm_5y": 15,
        "finbert_vs_logistic_10y": 15, "finbert_vs_baseline_10y": 15,
    }
    if comparisons != expected:
        raise ValueError(f"printed cross-table comparisons changed: {comparisons}")
    finbert_market = sum(value > 0.6324 for value in sharpe(tables, "tab:finbert 5"))
    agentic_market = sum(value > 0.6324 for value in sharpe(tables, "tab:finbert+llm 5"))
    triple_market = sum(
        value > 0.6324 for value in sharpe(tables, "tab:llm+finbert+analyst 5")
    )
    values = (
        ("printed_sharpe_identity", "two_mismatches", "313/315 printed triples satisfy Sharpe = annual return / sqrt(annual variance) within 0.002; LLM-S 10y NLS/MSR differs by 0.0084 and Agentic 10y POET/MV contains malformed return 01092"),
        ("agentic_10y_poet_mv_return", "missing_decimal_typographical_error", "source prints 01092; 0.1092 would imply Sharpe 0.2357 and reconcile with printed 0.2358 at displayed precision"),
        ("llm_10y_nls_msr", "printed_triple_conflict", "0.0740 / sqrt(0.0258) = 0.4607, not the printed Sharpe 0.4691"),
        ("llm_vs_baseline_5y", "claim_matches_printed_tables", f"LLM-S is higher in {comparisons['llm_vs_baseline_5y']}/15 cells; exceptions are POET/MSR and NLS/MSR"),
        ("logistic_vs_baseline_5y", "claim_matches_printed_tables", f"logistic is higher in {comparisons['logistic_vs_baseline_5y']}/15 cells"),
        ("llm_vs_analyst_and_novy_marx_5y", "claim_matches_printed_tables", "LLM-S is higher in all 15/15 cells against each comparator"),
        ("finbert_5y_comparisons", "claim_matches_printed_tables", "FinBERT is higher in 14/15 cells versus baseline and logistic, 15/15 versus analysts, and 11/15 exceed market Sharpe 0.6324"),
        ("agentic_5y_comparisons", "claim_matches_printed_tables", f"Agentic is higher in 14/15 versus baseline, 14/15 versus FinBERT, 15/15 versus LLM-S, and {agentic_market}/15 exceed market Sharpe 0.6324"),
        ("three_agent_5y", "claim_matches_printed_tables", f"all 15 three-agent Sharpe ratios are lower than two-agent Agentic and {triple_market}/15 exceed market"),
        ("finbert_10y_comparisons", "claim_matches_printed_tables", "FinBERT is higher in all 15/15 cells versus logistic and baseline"),
        ("subsequent_return_leakage_check", "asserted_without_released_statistic", "paper says signals do not systematically align with subsequent returns but releases no test statistic, sample, code, or signal ledger"),
        ("intersection_attribution", "asserted_without_released_lineage", "claims 1.037 of 1.187 Sharpe is attributable to intersection and union fallback has 0.545, but releases no dated decomposition or output arrays"),
        ("selected_stock_count", "asserted_without_released_lineage", "average 22 selected stocks and 50% trivial-intersection dates cannot be checked without annual rules and monthly signal sets"),
        ("screen_label_direction", "methodological_interpretation_boundary", "Stage 2 pools all non-hold buy and sell names and explicitly may assign either weight sign, so Stage-1 buy/sell labels do not constrain final position direction"),
        ("causal_masking", "prompt_instruction_not_model_control", "the released text asks Gemini to use causal masking; it is not evidence of an enforced attention mask, timestamped request, or training-data cutoff"),
        ("theory_to_empirics", "conditional_not_empirically_verified", "the sensible-screening theory assumes an oracle-like subset relation; public artifacts do not establish that LLM-S or FinBERT satisfies it"),
    )
    if finbert_market != 11 or agentic_market != 14 or triple_market != 0:
        raise ValueError("market comparison counts changed")
    return [{"check": a, "status": b, "detail": c} for a, b, c in values]


def news_audit(scratch: Path) -> dict[str, Any]:
    records = [
        json.loads(line)
        for line in (scratch / "discovery/hf-news.jsonl").read_text().splitlines()
        if line.strip()
    ]
    schema = {"id_", "links", "symbol", "company", "Title", "Text", "Publishdate"}
    if len(records) != 4589 or any(set(record) != schema for record in records):
        raise ValueError("linked Hugging Face JSONL row count or schema changed")
    ids = [record["id_"] for record in records]
    dates = [date.fromisoformat(record["Publishdate"]) for record in records]
    years = Counter(item.year for item in dates)
    expected_years = {
        2006: 3, 2007: 55, 2008: 73, 2009: 66, 2010: 131, 2011: 98,
        2012: 208, 2013: 90, 2014: 97, 2015: 116, 2016: 145, 2017: 248,
        2018: 284, 2019: 354, 2020: 278, 2021: 348, 2022: 476,
        2023: 918, 2024: 601,
    }
    if years != Counter(expected_years) or len(set(ids)) != len(ids):
        raise ValueError("linked news distribution or identifier uniqueness changed")
    api = json.loads((scratch / "discovery/hf-dataset-api.json").read_text())
    if (
        api["sha"] != "d3e37035640bc90830ee8741dfa52815b719a26a"
        or api["lastModified"] != "2024-11-14T15:16:41.000Z"
    ):
        raise ValueError("Hugging Face dataset revision marker changed")
    return {
        "repository": "KrossKinetic/SP500-Financial-News-Articles-Time-Series",
        "revision": api["sha"],
        "last_modified": api["lastModified"],
        "license": "MIT",
        "rows": len(records),
        "unique_ids": len(set(ids)),
        "unique_symbols": len({record["symbol"] for record in records}),
        "minimum_publish_date": min(dates).isoformat(),
        "maximum_publish_date": max(dates).isoformat(),
        "rows_2015_through_2024_04": sum(item >= date(2015, 1, 1) for item in dates),
        "rows_2020_through_2024_04": sum(item >= date(2020, 1, 1) for item in dates),
        "rows_by_year": {str(year): count for year, count in sorted(years.items())},
        "schema": sorted(schema),
        "exact_linked_input_recovered": True,
        "finbert_model_identifier_recovered": False,
        "paper_sentiment_scores_or_signals_recovered": False,
        "paper_result_credit": False,
    }


def method_rows() -> list[dict[str, str]]:
    values = (
        ("official_document_source", "complete_document_only", "v1 TeX, bibliography, workflow PNG, and generated bibliography are released; no experiment source is present"),
        ("author_native_runtime", "missing", "no attributable data, LLM, FinBERT, estimator, optimizer, or backtest runtime was recovered"),
        ("equity_universe", "partial", "full S&P 500 including delisted firms is stated, but point-in-time memberships, identifiers, eligibility rules, and vintages are absent"),
        ("crsp_compustat_data", "missing_proprietary", "monthly January 2005--April 2024 CRSP/Compustat panel is not released"),
        ("characteristics", "mostly_specified", "log market equity, book-to-market, and 12-month momentum; 1/99 winsorization, cross-sectional z-scores, and missing-to-zero are stated"),
        ("accounting_lag", "specified", "annual accounting data are assumed available six months after fiscal-year end"),
        ("linked_news_dataset", "exact_link_recovered", "pinned Hugging Face revision has 4,589 rows, 469 symbols, and dates 2006-12-04 through 2024-04-20"),
        ("ibes_recommendations", "missing_proprietary", "IBES/WRDS recommendation snapshot, analyst mappings, and derived monthly signals are absent"),
        ("fama_french_factors", "missing_snapshot", "three-factor model is named for residual nodewise estimation but exact factor file and vintage are absent"),
        ("llm_s_prompt", "partial_one_date", "agent/task prompt is printed only for December 2023; earlier annual prompts, injected data, tool traces, and outputs are absent"),
        ("llm_s_model", "family_only_retired", "Gemini 2.0 Flash is named without immutable model ID/revision; service shut down 2026-06-01"),
        ("llm_s_generation_parameters", "missing", "temperature, top-p, token limit, seed, retries, safety settings, and response metadata are absent"),
        ("crewai_runtime_and_tools", "names_only", "four tool names and snippets are printed; implementations, CrewAI version, database schema, and tool-call records are absent"),
        ("annual_llm_rules", "one_of_required_years", "one 2024 rule from December 2023 is printed; the full annual rule ledger for both evaluation windows is absent"),
        ("finbert_model", "missing_identifier", "FinBERT is named generically; checkpoint/revision, tokenizer, batching, truncation, inference code, and probabilities are absent"),
        ("finbert_aggregation", "partial", "positive-minus-negative probability, seven-day exponential weighting, and +/-0.1 thresholds are stated; exact timestamp and aggregation edge cases are absent"),
        ("ensemble_rule", "specified_prose", "two-agent intersection with union fallback at cardinality <=1 and three-agent majority vote are described"),
        ("ensemble_signal_ledger", "missing", "no dated buy/sell/hold sets, intersection/union flags, or selected-stock counts are released"),
        ("logistic_benchmark", "partial", "annual 15-year rolling cross-sectional logistic and top/bottom deciles are stated; target definition, features, solver, regularization, ties, and outputs are absent"),
        ("novy_marx_benchmark", "partial", "top/bottom 150 profitability-plus-value ranks are stated; exact construction, data fields, ties, and outputs are absent"),
        ("precision_estimators", "partial", "nodewise, residual nodewise, POET, deep learning, and NLS are described mathematically but implementation choices and fitted artifacts are absent"),
        ("deep_learning_estimator", "underspecified", "architecture, loss, optimizer, hyperparameters, validation, seeds, checkpoints, and training traces are absent"),
        ("portfolio_objectives", "mostly_specified", "GMV, 1% monthly target MV, and MSR formulas are printed; solver details, constraints, risk-free convention, and edge cases are absent"),
        ("formation_and_test_windows", "specified_dates_only", "180-month rolling formation and 2020-01--2024-04 plus 2015-01--2024-04 tests are stated; exact return matrix is absent"),
        ("transaction_cost", "formula_specified", "10 bp net-return formula is printed; corporate-action/execution conventions and generated turnover are absent"),
        ("random_seeds", "missing", "no seeds for LLM calls, deep learning, baselines, or repeated runs are released"),
        ("runtime_environment", "missing", "no author lockfile, versions, hardware description, or executable configuration is released"),
        ("raw_results", "missing", "no model requests/responses, signals, scores, weights, returns, fitted matrices, tables, or decomposition arrays are released"),
        ("published_result_lineage", "missing", "0/953 printed numeric table cells can be linked to an author-native executable output"),
    )
    return [{"dimension": a, "status": b, "evidence": c} for a, b, c in values]


def prompt_rows() -> list[dict[str, Any]]:
    return [
        {
            "component": "LLM-S agent backstory/system-like prompt",
            "date_scope": "December 2023 for 2024 rules",
            "exact_text_printed": True,
            "all_evaluation_dates_recovered": False,
            "input_cross_section_recovered": False,
            "tool_implementations_recovered": False,
            "author_model_request_replayable": False,
            "paper_result_credit": False,
        },
        {
            "component": "LLM-S CrewAI task prompt",
            "date_scope": "December 2023 for 2024 rules",
            "exact_text_printed": True,
            "all_evaluation_dates_recovered": False,
            "input_cross_section_recovered": False,
            "tool_implementations_recovered": False,
            "author_model_request_replayable": False,
            "paper_result_credit": False,
        },
        {
            "component": "LLM-S example model output/rule",
            "date_scope": "December 2023 for 2024 rules",
            "exact_text_printed": True,
            "all_evaluation_dates_recovered": False,
            "input_cross_section_recovered": False,
            "tool_implementations_recovered": False,
            "author_model_request_replayable": False,
            "paper_result_credit": False,
        },
    ]


def discovery_rows(scratch: Path) -> list[dict[str, Any]]:
    arxiv = json.loads((scratch / "discovery/github-arxiv-id.json").read_text())
    authors = json.loads((scratch / "discovery/github-authors.json").read_text())
    title = json.loads((scratch / "discovery/github-exact-title.json").read_text())
    if (arxiv["total_count"], authors["total_count"], title["total_count"]) != (30, 0, 4):
        raise ValueError("bounded GitHub search counts changed")
    return [
        {"route": "arxiv_v1_source", "result_count": 5, "finding": "manuscript TeX, bibliography, workflow image, and generated bibliography only; no experiment runtime/data/results", "attributable_native_implementation_recovered": False, "negative_search_limit": "describes pinned v1 archive only"},
        {"route": "github_code_arxiv_id", "result_count": arxiv["total_count"], "finding": "visible matches are citations, indexes, review material, or later interpretations", "attributable_native_implementation_recovered": False, "negative_search_limit": "bounded current indexed search; not proof about private, deleted, moved, or unindexed material"},
        {"route": "github_code_exact_title", "result_count": title["total_count"], "finding": "no affirmative author-attributable runtime recovered", "attributable_native_implementation_recovered": False, "negative_search_limit": "bounded current indexed search only"},
        {"route": "github_author_names", "result_count": authors["total_count"], "finding": "no matching author-attributable code result", "attributable_native_implementation_recovered": False, "negative_search_limit": "name search cannot rule out aliases, organizations, private repositories, or different accounts"},
        {"route": "alanhsieh2000_agentic_portfolio", "result_count": 1, "finding": "created 2026-08-05, uses Claude Sonnet 4.5, custom LLM-F, PyPortfolioOpt, 60/24-month returns, and current SEC/Yahoo data; materially divergent unaffiliated implementation", "attributable_native_implementation_recovered": False, "negative_search_limit": "no affirmative author relationship was recovered; absence of a link is not proof of identity"},
        {"route": "lewisbakkero_sparsis", "result_count": 1, "finding": "academic-review repository containing paper material, not an implementation of the experiment", "attributable_native_implementation_recovered": False, "negative_search_limit": "classification is limited to the pinned public repository snapshot"},
    ]


def build(scratch: Path, output: Path) -> dict[str, Any]:
    validated = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    tex = (scratch / "build/main.tex").read_text(encoding="utf-8")
    results, tables, sharpe_tables = parse_tables(tex)
    arithmetic = arithmetic_rows(sharpe_tables)
    consistency = consistency_rows(sharpe_tables)
    news = news_audit(scratch)
    methods = method_rows()
    prompts = prompt_rows()
    discovery = discovery_rows(scratch)

    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "table_inventory.csv", tables)
    write_csv(output / "sharpe_arithmetic_audit.csv", arithmetic)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "prompt_component_inventory.csv", prompts)
    write_csv(output / "discovery_evidence.csv", discovery)
    write_json(output / "linked_news_dataset_audit.json", news)

    chronology = {
        "paper_test_windows_end": "2024-04-30",
        "gemini_2_0_flash_first_public_date": "2024-12-11",
        "months_after_test_window_end_at_first_public_release": 7,
        "documented_knowledge_cutoff": "2024-08",
        "knowledge_cutoff_after_test_window_end": True,
        "service_shutdown_date": "2026-06-01",
        "literal_model_available_during_test_windows": False,
        "retrospective_data_layer_holdout_possible": True,
        "retrospective_model_knowledge_holdout_established": False,
        "timestamped_requests_and_exact_model_revision_recovered": False,
        "assessment": "A retrospective run after April 2024 is possible, but prompt wording alone cannot exclude model-pretraining knowledge through August 2024 or establish the missing request/model lineage.",
    }
    write_json(output / "model_release_chronology.json", chronology)

    independent = {
        "repository": "alanhsieh2000/agentic_portfolio",
        "pinned_commit": INDEPENDENT_COMMIT,
        "repository_created": "2026-08-05",
        "paper_submitted": "2026-03-24",
        "author_attribution_evidence_recovered": False,
        "classification": "unaffiliated_post_paper_interpretation",
        "isolated_test_suite": "114 passed",
        "internal_component_execution_credit": True,
        "author_native_execution_credit": False,
        "paper_result_credit": False,
        "published_result_cells_regenerated": 0,
        "material_divergences": [
            "Claude Sonnet 4.5 replaces Gemini 2.0 Flash",
            "custom LLM-F replaces FinBERT",
            "PyPortfolioOpt replaces the five paper precision estimators",
            "60-month history with 24-month fallback replaces the paper's 180-month window",
            "12% annual MV target is not the literal 1% monthly target",
            "a configurable 2% risk-free default is added without paper lineage",
            "current SEC EDGAR and Yahoo reconstruction replaces exact CRSP/Compustat/IBES/WRDS snapshots",
        ],
    }
    write_json(output / "independent_implementation_audit.json", independent)

    provenance = {
        "arxiv": {
            "id": ARXIV_ID,
            "version": "v1",
            "submitted": "2026-03-24",
            "pages": 67,
            "source_files": validated["official_source_files"],
            "source_archive_sha256": PINS["source/2603.23300v1.tar"],
            "official_pdf_sha256": PINS["primary/2603.23300v1.pdf"],
            "rebuilt_pdf_sha256": PINS["build/main.pdf"],
            "rebuild_extracted_token_multiset_jaccard": 0.9936239193083574,
            "visual_qa": {
                "official_pages_inspected": 67,
                "rebuilt_pages_inspected": 67,
                "unreadable_clipped_or_overlapping_pages": 0,
            },
        },
        "linked_news_dataset": {
            "repository": news["repository"],
            "revision": news["revision"],
            "jsonl_sha256": PINS["discovery/hf-news.jsonl"],
        },
        "release_boundary": {
            "attributable_native_implementation_recovered": False,
            "complete_author_prompt_history_recovered": False,
            "one_printed_prompt_and_output_example_recovered": True,
            "exact_linked_news_input_recovered": True,
            "complete_paper_data_recovered": False,
            "paper_result_output_recovered": False,
            "bounded_negative_search_is_proof_of_nonexistence": False,
        },
    }
    write_json(output / "source_provenance.json", provenance)

    readme = """# Agentic AI Screening paper/source audit

This audit pins arXiv `2603.23300v1`, rebuilds its 67-page source, visually
checks every official and rebuilt page, inventories all 22 result tables and
all **953 printed numeric result cells**, and assigns **0/953 native result credit**.
The source archive contains five document assets, not the authors'
experiment.  No attributable native implementation was recovered.

## What is genuinely recoverable

- The linked Hugging Face news revision is pinned and inspected: 4,589 rows,
  469 symbols, and publication dates from 2006-12-04 through 2024-04-20.
- The paper prints the LLM-S CrewAI agent/task prompt and deterministic rule
  output for December 2023.  This is one date, not the annual prompt, injected
  cross-section, tool-call, and output history required by the tests.
- The characteristic preprocessing, seven-day news weighting, ensemble rule,
  180-month window, three objectives, five estimator families, and 10 bp cost
  equation are described to varying degrees.  They are method specification,
  not executable result lineage.

## Why the paper is not truly replicated

The public package omits the point-in-time S&P 500 membership and identifiers;
CRSP/Compustat and IBES/WRDS snapshots; exact Fama--French input; full annual
prompts, data payloads, tool implementations, Gemini requests and rule outputs;
the FinBERT checkpoint and probabilities; all monthly signals and ensemble
sets; estimator/deep-learning implementations and hyperparameters; seeds and
environment; fitted matrices, portfolio weights, returns, costs, tables, and
decomposition arrays.  Consequently none of the 953 printed cells can be
regenerated through an author-native path.

Gemini 2.0 Flash first became public on 2024-12-11, seven months after the
reported test data end, so a retrospective data split is possible.  Its
documented knowledge cutoff is August 2024, after that test end.  The paper's
instruction to “use causal masking” is prompt text, not evidence of a model
attention control, a timestamped request, or a model-knowledge holdout.  Strict
prospective/model-chronology faithfulness therefore remains unverified.

## Checks on the printed record

- 313/315 Sharpe/return/variance triples reconcile within 0.002.  The 10-year
  LLM-S NLS/MSR row implies 0.4607 rather than printed 0.4691.
- The 10-year Agentic POET/MV return is printed as `01092`; interpreting it as
  `0.1092` reconciles with the printed 0.2358 Sharpe and is almost certainly a
  missing decimal, but the ledger preserves the source literally.
- Major cross-table comparison counts in the prose agree with the printed
  tables.  This internal agreement does not verify the experiment.
- Claims that signals do not align with subsequent returns, that the
  intersection contributes 1.037 of 1.187 Sharpe, that fallback-union dates
  are 50%, and that 22 stocks are selected on average lack released statistics
  or dated signal/output arrays.
- Stage 2 pools buy and sell names and may reverse their signs, so the screening
  labels do not constrain final position direction.  The theoretical guarantee
  is conditional on “sensible screening”; the public artifacts do not show the
  empirical agents satisfy that assumption.

A pinned later repository passes **114 tests**, which is useful evidence about
its own components.  It is an unaffiliated interpretation created over four
months after the paper and materially changes the model, sentiment agent,
estimator, return window, risk-free convention, and data sources.  It receives
no author-native or paper-result credit.

The honest present assessment is: strong document reproducibility, one exact linked
input component, one-date prompt/output specification, and zero end-to-end empirical replication.
Reaching 100% paper faithfulness from the
current public record is impossible without author data/runtime/output lineage;
that boundary is recorded rather than filled with proxies.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    manifest: dict[str, Any] = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_versions_audited": ["v1"],
        "official_pdf_and_source_recovered": True,
        "official_document_rebuild_completed": True,
        "official_pages_visually_checked": 67,
        "rebuilt_pages_visually_checked": 67,
        "published_result_tables": 22,
        "published_numeric_table_cells": len(results),
        "native_numeric_table_cells_regenerated": 0,
        "sharpe_arithmetic_checks": len(arithmetic),
        "sharpe_arithmetic_mismatches": sum(
            not row["within_0_002_tolerance"] for row in arithmetic
        ),
        "linked_news_rows_recovered": news["rows"],
        "linked_news_symbols_recovered": news["unique_symbols"],
        "printed_llm_prompt_or_output_components_recovered": len(prompts),
        "complete_annual_prompt_and_output_sets_recovered": 0,
        "independent_component_tests_passed": 114,
        "attributable_native_implementation_recovered": False,
        "full_end_to_end_pipeline_reproduced": False,
        "paper_evidence_route": "paper_only_one_linked_input_and_one_date_prompt_no_native_results",
        "output_sha256": {},
    }
    output_files = sorted(
        path for path in output.iterdir()
        if path.is_file() and path.name != "manifest.json"
    )
    manifest["output_sha256"] = {path.name: sha256(path) for path in output_files}
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if args.strict and not manifest["full_end_to_end_pipeline_reproduced"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
