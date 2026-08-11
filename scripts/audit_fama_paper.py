#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for the ACL 2024 FAMA paper.

This audit distinguishes document-level specification from native execution.
The official paper does not link code, data, generated factors, traces, or raw
result arrays, so parsing a published table is never counted as reproduction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader


PAPER_URL = "https://aclanthology.org/2024.findings-acl.233/"
PDF_URL = "https://aclanthology.org/2024.findings-acl.233.pdf"
DOI = "10.18653/v1/2024.findings-acl.233"
EXPECTED_PDF_SHA256 = "327bbaf4011b739107b4c891220fc845c48f974f64abfccdeb8229d789648296"
EXPECTED_PAGE_SHA256 = "5790d804ccb4174d562083e332cdd03cc02c0fa73dabf8ebe0d4e0ccac95bf7f"
EXPECTED_PAGES = 12

GITHUB_QUERIES = (
    "2024.findings-acl.233",
    '"Can Large Language Models Mine Interpretable Financial Factors More Effectively"',
    '"Factor Mining Agent" FAMA finance',
)

PROMPT_TEMPLATE = """“function_definition” is from “Functions and Operators” in Alpha101 (Kakushadze, 2016).
Instruction
You are an alpha generator. You should follow the following rules:
1. The inputs are the alpha factors that are currently performing well, and you are required to output a new alpha factor that is generated from the fusion of these factors, and your factor must be different from the input factor.
2. Do not repeat example answer.
3. You should return new different factors in a json array.
4. The specific function is defined as follows:
{function_definition}
5. Follow the path in "improve_path". -> Indicates that the following factors have better performance than the previous factors. You should refer it to build new alpha.
Input Example
alphas: ["(-1 * correlation(open, volume, 10))"]
generate_factor_num: 1
improve_path: "close/open" -> "rank(close)/rank(open)"
Output Example
["rank(correlation(open, volume, 10) / rank(open))"]
"""

TABLE_1 = (
    ("Alpha101", "", ".018", ".000", ".200", ".000"),
    ("GP", "100%", ".017", ".005", ".141", ".034"),
    ("LLM", "", ".015", ".008", ".139", ".011"),
    ("DTransformer", "100%", ".025", ".005", ".124", ".015"),
    ("ALSTM", "100%", ".028", ".006", ".167", ".021"),
    ("FactorVAE", "100%", ".048", ".008", ".379", ".042"),
    ("FAMA(C)", "10%", ".023", ".006", ".204", ".019"),
    ("FAMA(I-1)", "10%", ".016", ".006", ".149", ".017"),
    ("FAMA(CI-3)", "10%", ".030", ".008", ".372", ".031"),
    ("FAMA(CI-7)", "10%", ".054", ".010", ".485", ".051"),
)

TABLE_2 = (
    ("S&P500", "26.3%", "11.5%", "209.3%"),
    ("GP", "11.2%", "6.8%", "159.2%"),
    ("Alpha101", "19.7%", "4.5%", "406.1%"),
    ("ALSTM", "25.4%", "22.5%", "89.3%"),
    ("DTransformer", "27.8%", "24.7%", "93.5%"),
    ("FactorVAE", "31.8%", "22.8%", "132.2%"),
    ("FAMA", "38.4%", "4.9%", "667.2%"),
)

TABLE_4 = (
    ("gpt-3.5-turbo", ".054", ".481"),
    ("text-davinci-003", ".056", ".492"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pdf_text(path: Path) -> tuple[str, int]:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages), len(reader.pages)


def validate_pdf(text: str, pages: int) -> None:
    if pages != EXPECTED_PAGES:
        raise ValueError(f"official paper page count changed: {pages}")
    required = (
        "Factor Mining Agent",
        "Cross-Sample Selection",
        "Chain-of-Experience",
        "38 factors from Al-",
        "38.4%",
        "667.2%",
        "function_definition",
        "text-davinci-003",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise ValueError(f"official paper extraction changed: {missing}")


def initial_factor_ids(text: str) -> list[str]:
    start = text.index("We select the following factors")
    quote_start = text.index("“", start)
    quote_end = text.index("”", quote_start)
    ids = re.findall(r"\b\d{3}\b", text[quote_start:quote_end])
    if len(ids) != 71 or len(set(ids)) != 71:
        raise ValueError(f"Appendix B factor inventory changed: {len(ids)}")
    return ids


def result_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for model, _usage, ric, ric_sd, ricir, ricir_sd in TABLE_1:
        for metric, value in (
            ("RankIC_mean", ric),
            ("RankIC_std", ric_sd),
            ("RankICIR_mean", ricir),
            ("RankICIR_std", ricir_sd),
        ):
            rows.append(result_row("Table 1", 6, model, metric, value))
    for model, ar, vol, sr in TABLE_2:
        for metric, value in (("AR", ar), ("Vol", vol), ("SR", sr)):
            rows.append(result_row("Table 2", 8, model, metric, value))
    for model, ric, ricir in TABLE_4:
        for metric, value in (("RankIC", ric), ("RankICIR", ricir)):
            rows.append(result_row("Table 4", 11, model, metric, value))
    if len(rows) != 65:
        raise AssertionError("FAMA result-table census must contain 65 cells")
    return rows


def result_row(table: str, pdf_page: int, model: str, metric: str, value: str) -> dict[str, str]:
    return {
        "source_unit": table,
        "pdf_page": str(pdf_page),
        "model": model,
        "metric": metric,
        "published_display_value": value,
        "native_reproduction_status": "not_reproduced_no_author_linked_code_data_or_outputs",
        "reproduced_display_value": "",
        "display_match": "no",
        "paper_result_credit": "no",
        "evidence_boundary": "published_value_inventory_only",
    }


def configuration_rows() -> list[dict[str, str]]:
    rows = []
    for model, usage, *_rest in TABLE_1:
        if usage:
            rows.append(
                {
                    "source_unit": "Table 1",
                    "pdf_page": "6",
                    "model": model,
                    "configuration_field": "Training data usage",
                    "published_display_value": usage,
                    "audit_status": "enumerated_not_execution_verified",
                    "paper_result_credit": "no",
                }
            )
    if len(rows) != 8:
        raise AssertionError("FAMA numeric configuration census must contain 8 cells")
    return rows


def figure_rows() -> list[dict[str, str]]:
    rows = [
        {"figure": "Figure 1", "pdf_page": "1", "series": "method taxonomy", "visible_result_markers": "0", "audit_status": "conceptual_diagram"},
        {"figure": "Figure 2", "pdf_page": "4", "series": "FAMA architecture", "visible_result_markers": "0", "audit_status": "conceptual_diagram_with_formula_examples"},
        {"figure": "Figure 3a", "pdf_page": "7", "series": "RankIC by CoE iteration 0--7", "visible_result_markers": "8", "audit_status": "raster_only_no_raw_plot_values"},
        {"figure": "Figure 3a", "pdf_page": "7", "series": "RankICIR by CoE iteration 0--7", "visible_result_markers": "8", "audit_status": "raster_only_no_raw_plot_values"},
        {"figure": "Figure 3b", "pdf_page": "7", "series": "RankIC by CSS factor count 1--7", "visible_result_markers": "7", "audit_status": "raster_only_no_raw_plot_values"},
        {"figure": "Figure 3b", "pdf_page": "7", "series": "RankICIR by CSS factor count 1--7", "visible_result_markers": "7", "audit_status": "raster_only_no_raw_plot_values"},
        {"figure": "Figure 4", "pdf_page": "7", "series": "RankIC for Initial/Head/Middle/Tail", "visible_result_markers": "4", "audit_status": "raster_only_no_raw_plot_values"},
        {"figure": "Figure 4", "pdf_page": "7", "series": "RankICIR for Initial/Head/Middle/Tail", "visible_result_markers": "4", "audit_status": "raster_only_no_raw_plot_values"},
    ]
    if sum(int(row["visible_result_markers"]) for row in rows) != 38:
        raise AssertionError("FAMA figure census must contain 38 visible result markers")
    return rows


def claim_rows() -> list[dict[str, str]]:
    return [
        claim("Q001", "Abstract", "RankIC improvement over SOTA", "0.006", "0.054 - 0.048 = 0.006", "internally_recomputes", "major"),
        claim("Q002", "Abstract", "RankICIR improvement over SOTA", "0.105", "0.485 - 0.379 = 0.106", "conflicts_with_table_and_section_4_4", "major"),
        claim("Q003", "Abstract", "FAMA annualized return", "38.4%", "Table 2 repeats 38.4%", "table_repetition_not_reproduction", "blocking"),
        claim("Q004", "Abstract", "FAMA Sharpe ratio", "667.2%", "Table 2 repeats 667.2%; Equation 20 defines a dimensionless ratio", "unit_ambiguous_not_reproduced", "blocking"),
        claim("Q005", "Section 4.4", "RankIC improvement over FactorVAE", "0.006", "0.054 - 0.048 = 0.006", "internally_recomputes", "major"),
        claim("Q006", "Section 4.4", "RankICIR improvement over FactorVAE", "0.106", "0.485 - 0.379 = 0.106", "internally_recomputes", "major"),
        claim("Q007", "Section 4.6", "AR increase over best prior table row", "6.6%", "38.4 - 31.8 = 6.6 percentage points; relative increase is 20.75%", "percentage_point_language_ambiguous", "major"),
        claim("Q008", "Section 4.6", "SR improvement over best prior Sharpe", "261.1%", "667.2 - 406.1 = 261.1 percentage points; relative increase is 64.29%", "percentage_point_language_ambiguous", "major"),
        claim("Q009", "Section 4.6", "consistent performance without significant fluctuations", "qualitative", "No native return path, uncertainty interval, drawdown, or stability test is released", "not_verifiable", "blocking"),
        claim("Q010", "Section 4.6", "robustness and stability", "qualitative", "One test year is stated; no costs, turnover, seeds, or raw paths are released", "not_verifiable", "blocking"),
    ]


def claim(identifier: str, location: str, description: str, value: str, recomputation: str, assessment: str, severity: str) -> dict[str, str]:
    return {
        "claim_id": identifier,
        "location": location,
        "claim": description,
        "published_value": value,
        "audit_recomputation_or_evidence": recomputation,
        "assessment": assessment,
        "severity": severity,
        "paper_result_credit": "no",
    }


def consistency_rows() -> list[dict[str, str]]:
    return [
        issue("FAMA-INT-001", "Section 4.1 vs Appendix B", "Initial factor set contains 38 factors", "Appendix B lists 71 distinct Alpha101 identifiers", "71", "direct_conflict", "blocking"),
        issue("FAMA-INT-002", "Abstract vs Table 1/Section 4.4", "RankICIR gain is 0.105", "0.485 - 0.379 and Section 4.4 give 0.106", "0.106", "direct_conflict", "major"),
        issue("FAMA-INT-003", "Equation 7", "r(fi,fj) is a correlation", "Printed denominator is sum of squared products without the Pearson square root", "not_a_correlation_coefficient", "equation_conflict", "blocking"),
        issue("FAMA-INT-004", "Equation 1", "RankIC is a cross-sectional rank correlation", "The displayed average additionally sums a per-stock j term after Corr(order_f, order_rj)", "cross_section_dimension_unresolved", "notation_conflict", "blocking"),
        issue("FAMA-INT-005", "Sections 2.3 and 4.1", "m denotes total mining iterations", "m is reassigned as the number of clusters and set to 7", "overloaded_experiment_control", "symbol_conflict", "major"),
        issue("FAMA-INT-006", "Sections 4.1--4.2", "2020-06-01--2021-01-01 is the training and validation subset and 10% of training", "The declared validation set starts 2020-01-01, so the window is not a subset of the declared 2015--2020 training set", "split_roles_unresolved", "direct_conflict", "blocking"),
        issue("FAMA-INT-007", "Algorithm 1 vs method narrative", "Only a factor with gamma above every factor in its chain is incorporated", "Line 13 adds every generated f-prime to Fi outside the improvement conditional", "acceptance_filter_not_applied_to_factor_set", "algorithm_conflict", "blocking"),
        issue("FAMA-INT-008", "Table 2/Equation 20", "SR is a Sharpe ratio", "Table 2 formats every SR as a percentage, including FAMA 667.2%", "ratio_scale_ambiguous", "unit_conflict", "blocking"),
        issue("FAMA-INT-009", "Section 4.6", "AR increases by 6.6%", "The table difference is 6.6 percentage points; relative increase over 31.8% is 20.75%", "6.6pp_or_20.75_percent", "unit_conflict", "major"),
        issue("FAMA-INT-010", "Section 4.6", "SR improves by 261.1%", "The difference from the best prior table SR is 261.1 percentage points; relative increase is 64.29%", "261.1pp_or_64.29_percent", "unit_conflict", "major"),
        issue("FAMA-INT-011", "Section 4.6", "Top-20% stocks are bought and sold next day", "No long/short meaning, within-factor weights, execution price, or capital normalization is stated", "portfolio_rule_incomplete", "underspecified", "blocking"),
        issue("FAMA-INT-012", "Appendix D vs Figure 2", "Appendix D is the full prompt example", "The required function_definition remains a placeholder and Figure 2 shows a different abbreviated instruction", "runtime_prompt_not_reconstructable", "underspecified", "blocking"),
    ]


def issue(identifier: str, location: str, statement_a: str, statement_b: str, recomputed: str, assessment: str, severity: str) -> dict[str, str]:
    return {
        "issue_id": identifier,
        "location": location,
        "paper_statement_a": statement_a,
        "paper_statement_b_or_missing_detail": statement_b,
        "audit_recomputation": recomputed,
        "assessment": assessment,
        "severity": severity,
        "replication_effect": "prevents_exact_native_reconstruction" if severity == "blocking" else "requires_explicit_interpretation",
    }


def method_rows() -> list[dict[str, str]]:
    specs = [
        ("authoritative publication", "ACL Anthology final, DOI and 12-page PDF", "specified", "none"),
        ("author-linked implementation", "No repository or code link in paper or official record", "missing", "blocking"),
        ("author-linked supplementary files", "Official record links only the PDF", "missing", "blocking"),
        ("market data provider", "OHLCV fields are named but provider is not", "missing", "blocking"),
        ("data snapshot", "No downloadable input snapshot or hashes", "missing", "blocking"),
        ("universe", "S&P 500 stocks", "specified", "major"),
        ("constituent vintage", "No constituent list or as-of policy", "missing", "blocking"),
        ("survivorship handling", "Not stated", "missing", "blocking"),
        ("corporate-action adjustment", "Not stated for OHLCV", "missing", "blocking"),
        ("calendar/time zone", "Not stated", "missing", "major"),
        ("full data window", "2015-01-01--2022-01-01", "specified", "none"),
        ("declared training split", "2015-01-01--2020-01-01", "specified", "none"),
        ("declared validation split", "2020-01-01--2021-01-01", "specified", "none"),
        ("declared test split", "2021-01-01--2022-01-01", "specified", "none"),
        ("FAMA fitting window", "2020-06-01--2021-01-01 called training and validation and 10% of training", "conflict", "blocking"),
        ("initial factor count", "38 in Section 4.1 versus 71 identifiers in Appendix B", "conflict", "blocking"),
        ("initial factor identifiers", "71 distinct Alpha101 IDs listed", "specified", "major"),
        ("initial factor expressions", "Not reproduced; external Alpha101 source cited", "partial", "major"),
        ("operator/function definitions", "Runtime prompt contains an unresolved function_definition placeholder", "missing", "blocking"),
        ("factor formula grammar", "Only examples and a placeholder are supplied", "partial", "blocking"),
        ("cluster count", "Seven", "specified", "none"),
        ("cluster algorithm", "KMeans equations supplied", "specified", "major"),
        ("cluster initialization", "Random centers; no seed", "partial", "blocking"),
        ("cluster convergence/ties", "Not stated", "missing", "blocking"),
        ("CSS random factor per cluster", "Specified conceptually; no seed", "partial", "blocking"),
        ("CSS context count", "l=2", "specified", "none"),
        ("minimum new factor count", "u=15", "specified", "none"),
        ("mining iteration count", "m overloaded with cluster count; CI-7 reported", "conflict", "blocking"),
        ("LLM model", "text-davinci-002", "specified", "major"),
        ("LLM immutable snapshot", "No model/API revision or request date", "missing", "blocking"),
        ("temperature", "0", "specified", "none"),
        ("max_tokens", "1500", "specified", "none"),
        ("remaining decoding parameters", "Defaults delegated to mutable OpenAI documentation", "missing", "blocking"),
        ("prompt template", "One example supplied", "partial", "major"),
        ("runtime prompts", "No filled prompts or requests", "missing", "blocking"),
        ("output parser", "JSON array requested; validation/retry behavior absent", "missing", "blocking"),
        ("invalid formula handling", "Hallucination acknowledged only as a limitation", "missing", "blocking"),
        ("factor evaluation horizon", "factor rank t-1 versus return rank t", "specified", "major"),
        ("RankIC equation", "Equation 1 has unresolved cross-stock notation", "conflict", "blocking"),
        ("factor correlation equation", "Equation 7 is not the stated Pearson correlation", "conflict", "blocking"),
        ("RankICIR equation", "Equation 16 supplied but nested averaging dimensions are not operationally pinned", "partial", "blocking"),
        ("factor acceptance threshold", "RankIC > 0.01 on 2020-06-01--2021-01-01", "specified", "major"),
        ("Algorithm 1 acceptance", "Narrative and line placement disagree on adding unsuccessful factors", "conflict", "blocking"),
        ("CoE initialization", "Factors ordered by gamma within each cluster", "specified", "major"),
        ("CoE matching", "Highest printed correlation to the generated factor", "specified", "major"),
        ("CoE tie behavior", "Not stated", "missing", "major"),
        ("number of experiments", "Table 1 reports mean/std over 10 experiments", "specified", "major"),
        ("random seeds", "No seeds for KMeans, CSS, CoE deletion, baselines, or trials", "missing", "blocking"),
        ("baseline code/versions", "Names and citations only", "missing", "blocking"),
        ("baseline hyperparameters", "Not supplied", "missing", "blocking"),
        ("other-LLM model versions", "gpt-3.5-turbo and text-davinci-003 without snapshots", "partial", "blocking"),
        ("final mined factor expressions", "None released", "missing", "blocking"),
        ("factor pools/experience chains", "None released", "missing", "blocking"),
        ("API responses/search traces", "None released", "missing", "blocking"),
        ("table raw results", "Only rounded PDF values", "missing", "blocking"),
        ("figure raw arrays", "Figures 3--4 are raster-only", "missing", "blocking"),
        ("portfolio factor weights", "Equation 17 weights selected factors by past RankIC", "specified", "major"),
        ("portfolio asset selection", "Top 20% factor values", "specified", "major"),
        ("within-factor asset weights", "Not stated", "missing", "blocking"),
        ("long/short convention", "Buy and sell next day is ambiguous", "missing", "blocking"),
        ("execution timing/price", "Next day stated; price field and order convention absent", "partial", "blocking"),
        ("transaction costs/slippage", "Not stated", "missing", "blocking"),
        ("risk-free rate", "Zero", "specified", "none"),
        ("annualization", "252 trading days", "specified", "none"),
        ("AR/Vol/SR equations", "Equations 18--20 supplied", "specified", "major"),
        ("Sharpe output units", "Equation is a ratio; table prints percentages", "conflict", "blocking"),
        ("portfolio trials/aggregation", "Not stated for Table 2", "missing", "blocking"),
        ("native result artifacts", "No predictions, weights, returns, or metrics", "missing", "blocking"),
        ("local proxy relation", "Only the momentum motif is source-adjacent; value, profitability, size, weights, cadence, and portfolio rule are researcher supplied", "partial", "blocking"),
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


def github_rows(search_dir: Path) -> list[dict[str, str]]:
    rows = []
    for query in GITHUB_QUERIES:
        suffix = hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]
        path = search_dir / f"github_{suffix}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "query": query,
                "response_file": path.name,
                "response_sha256": sha256(path),
                "total_count": str(payload["total_count"]),
                "incomplete_results": str(payload["incomplete_results"]).lower(),
                "author_linked_repository_found": "no",
                "evidence_use": "negative_search_evidence_only",
            }
        )
    return rows


def build(paper_pdf: Path, official_page: Path, github_dir: Path, output: Path) -> dict[str, Any]:
    if sha256(paper_pdf) != EXPECTED_PDF_SHA256:
        raise ValueError("official FAMA PDF hash changed")
    if sha256(official_page) != EXPECTED_PAGE_SHA256:
        raise ValueError("official ACL page hash changed")
    text, pages = pdf_text(paper_pdf)
    validate_pdf(text, pages)
    ids = initial_factor_ids(text)
    html = official_page.read_text(encoding="utf-8", errors="replace")
    artifact_links = re.findall(r'href="([^"]+)"', html, flags=re.IGNORECASE)
    paper_links = [link for link in artifact_links if re.search(r"github|supp|attach|\.zip|\.tar|\.pdf", link, re.I)]
    if paper_links != [PDF_URL]:
        raise ValueError(f"official ACL artifact-link inventory changed: {paper_links}")

    results = result_rows()
    configs = configuration_rows()
    figures = figure_rows()
    claims = claim_rows()
    consistency = consistency_rows()
    methods = method_rows()
    searches = github_rows(github_dir)
    if any(row["total_count"] != "0" for row in searches):
        raise ValueError("GitHub repository search result changed; inspect before rerouting")

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "official_table_result_conformance.csv", results, list(results[0]))
    write_csv(output / "numeric_configuration_audit.csv", configs, list(configs[0]))
    write_csv(output / "figure_result_inventory.csv", figures, list(figures[0]))
    write_csv(output / "quantitative_claim_audit.csv", claims, list(claims[0]))
    write_csv(output / "paper_internal_consistency_audit.csv", consistency, list(consistency[0]))
    write_csv(output / "method_specification_audit.csv", methods, list(methods[0]))
    write_csv(output / "source_search_inventory.csv", searches, list(searches[0]))
    factor_rows = [
        {
            "appendix_position": str(index),
            "alpha101_identifier": identifier,
            "listed_in_appendix_b": "yes",
            "expression_released_in_fama_paper": "no",
            "paper_result_credit": "no",
        }
        for index, identifier in enumerate(ids, 1)
    ]
    write_csv(output / "initial_factor_inventory.csv", factor_rows, list(factor_rows[0]))
    (output / "paper_prompt_template.txt").write_text(PROMPT_TEMPLATE, encoding="utf-8")

    method_counts = dict(sorted(Counter(row["assessment"] for row in methods).items()))
    severity_counts = dict(sorted(Counter(row["severity"] for row in methods).items()))
    source_provenance = {
        "official_record": PAPER_URL,
        "official_record_sha256": sha256(official_page),
        "official_pdf": PDF_URL,
        "official_pdf_sha256": sha256(paper_pdf),
        "doi": DOI,
        "pages": pages,
        "license": "CC BY 4.0 per ACL Anthology record",
        "official_artifact_links": paper_links,
        "author_linked_code_or_supplement_found": False,
        "github_repository_searches": searches,
    }
    write_json(output / "source_provenance.json", source_provenance)

    native = {
        "attempted": False,
        "reason": "no_author_linked_code_data_model_snapshot_final_factors_or_result_artifacts",
        "paper_result_credit": False,
        "published_table_result_cells": len(results),
        "published_table_result_cells_reproduced": 0,
        "visible_figure_result_markers": sum(int(row["visible_result_markers"]) for row in figures),
        "visible_figure_result_markers_reproduced": 0,
        "local_proxy_status": "M1_example_or_motif_partial_support_only",
        "local_proxy_boundary": "momentum_motif_only; value_profitability_size_weights_monthly_deciles_and_returns_are_researcher_supplied",
    }
    write_json(output / "native_execution.json", native)

    manifest = {
        "paper": "Can Large Language Models Mine Interpretable Financial Factors More Effectively? A Neural-Symbolic Factor Mining Agent Model",
        "system_id": "SYS-FAMA",
        "canonical_work_id": "CensusACL2024findingsacl233",
        "audit_route": "paper_only_underspecified_with_motif_level_local_proxy",
        "overall_fidelity": "zero_of_65_table_results_and_zero_of_38_figure_markers_reproduced_no_native_pipeline",
        "paper_result_credit": False,
        "official_pdf_pages": pages,
        "published_table_result_cells": len(results),
        "published_table_result_cells_reproduced": 0,
        "numeric_configuration_cells": len(configs),
        "visible_figure_result_markers": 38,
        "visible_figure_result_markers_reproduced": 0,
        "quantitative_and_qualitative_claims_audited": len(claims),
        "initial_factor_count_claimed": 38,
        "initial_factor_identifiers_listed": len(ids),
        "runtime_prompt_templates_recovered": 1,
        "runtime_prompt_function_definitions_recovered": 0,
        "final_mined_factor_expressions_released": 0,
        "internal_consistency_issues": len(consistency),
        "blocking_internal_consistency_issues": sum(row["severity"] == "blocking" for row in consistency),
        "method_dimensions": len(methods),
        "method_assessment_counts": method_counts,
        "method_severity_counts": severity_counts,
        "github_repository_searches": len(searches),
        "github_repository_search_hits": sum(int(row["total_count"]) for row in searches),
        "author_linked_code_found": False,
        "source_provenance": "source_provenance.json",
        "native_execution": "native_execution.json",
    }
    write_json(output / "manifest.json", manifest)
    (output / "README.md").write_text(readme(manifest), encoding="utf-8")
    return manifest


def readme(manifest: dict[str, Any]) -> str:
    return f"""# FAMA paper-level replication audit

This package audits the authoritative ACL 2024 paper and its official ACL
Anthology record. It is deliberately fail-closed. Published numbers copied from
the PDF are an inventory, not reproduced evidence.

## Verdict

- **Native FAMA paper results reproduced: 0/{manifest['published_table_result_cells']} table cells and 0/{manifest['visible_figure_result_markers']} visible figure markers.**
- No author-linked implementation, data snapshot, model snapshot, filled prompt,
  final mined factor set, search/experience trace, prediction, portfolio path, or
  raw result file was found.
- Appendix D recovers one prompt template, but its required
  `{{function_definition}}` remains unresolved. It is specification evidence only.
- The existing local FAMA mapping remains M1 motif-level evidence: the paper
  discusses momentum/trend principles, while value, profitability, size, equal
  score weights, monthly deciles, and the tested return stream are
  researcher-supplied.

## Material paper conflicts

- Section 4.1 says the initial Alpha101 pool contains 38 factors; Appendix B
  lists {manifest['initial_factor_identifiers_listed']} distinct identifiers.
- Equation 7 labels an expression as correlation but omits the Pearson
  denominator square root, changing CSS clustering and CoE matching semantics.
- Algorithm 1 adds every generated factor to `Fi` outside the improvement test,
  contrary to the method narrative.
- The abstract's 0.105 RankICIR gain conflicts with the 0.106 table difference
  and Section 4.4.
- The stated 2020-06-01--2021-01-01 fitting window crosses the paper's declared
  training/validation boundary while being called 10% of training.
- Portfolio construction, cost treatment, result units, and random seeds are not
  specified enough to reconstruct the reported 38.4% AR or 667.2% SR.

## Files

- `official_table_result_conformance.csv`: all 65 numeric performance cells.
- `numeric_configuration_audit.csv`: eight Table 1 training-usage cells.
- `figure_result_inventory.csv`: all 38 visible result markers in Figures 3--4.
- `initial_factor_inventory.csv`: the 71 Appendix B identifiers.
- `paper_internal_consistency_audit.csv`: equation, count, split, algorithm, and
  unit conflicts.
- `method_specification_audit.csv`: exact-replication requirements and blockers.
- `paper_prompt_template.txt`: the recovered Appendix D template.
- `source_search_inventory.csv` and `source_provenance.json`: pinned source and
  negative repository-search evidence.
- `native_execution.json` and `manifest.json`: machine-readable evidence boundary.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-pdf", type=Path, required=True)
    parser.add_argument("--official-page", type=Path, required=True)
    parser.add_argument("--github-search-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(
        args.paper_pdf.resolve(),
        args.official_page.resolve(),
        args.github_search_dir.resolve(),
        args.output_dir.resolve(),
    )
    print(compact_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
