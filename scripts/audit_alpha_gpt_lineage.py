#!/usr/bin/env python3
"""Build a fail-closed audit of the Alpha-GPT paper lineage.

The lineage contains three materially different empirical objects:

* Alpha-GPT arXiv v1 (2023), an experimental GPT-3.5/GP paper;
* Alpha-GPT 2.0 v1 (2024), a four-page, explicitly work-in-progress
  architecture paper with no empirical results; and
* Alpha-GPT arXiv v2 / EMNLP 2025 final, a substantially rewritten Llama-3
  paper with new experiments and competition claims.

The official TeX archives are document sources, not native system releases.
This audit therefore keeps source rebuilding, formula syntax checks, an
unaffiliated community implementation, and paper-result reproduction separate.
"""
from __future__ import annotations

import argparse
import ast
import csv
import difflib
import hashlib
import json
import re
import subprocess
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
ALPHA_GPT_RECORD = "https://arxiv.org/abs/2308.00016"
ALPHA_GPT_V1_PDF_URL = "https://arxiv.org/pdf/2308.00016v1"
ALPHA_GPT_V2_PDF_URL = "https://arxiv.org/pdf/2308.00016v2"
ALPHA_GPT_V1_SOURCE_URL = "https://arxiv.org/e-print/2308.00016v1"
ALPHA_GPT_V2_SOURCE_URL = "https://arxiv.org/e-print/2308.00016v2"
ACL_RECORD = "https://aclanthology.org/2025.emnlp-demos.14/"
ACL_PDF_URL = "https://aclanthology.org/2025.emnlp-demos.14.pdf"
ALPHA_GPT2_RECORD = "https://arxiv.org/abs/2402.09746v1"
ALPHA_GPT2_PDF_URL = "https://arxiv.org/pdf/2402.09746v1"
ALPHA_GPT2_SOURCE_URL = "https://arxiv.org/e-print/2402.09746v1"
COMMUNITY_REPOSITORY = "https://github.com/parthmodi152/alpha-gpt"

EXPECTED_ALPHA_GPT_V1_PDF_SHA256 = "0533cacfe231715fdea09aa045e485380cfb5de0906ebc1520f150257a645968"
EXPECTED_ALPHA_GPT_V2_PDF_SHA256 = "d966e6497cb71cb3d32b1266c9799d6512f5f9d8ede5f0d29f5ff57476f8f0ce"
EXPECTED_ACL_FINAL_PDF_SHA256 = "50fd3393114f1efd38158b6668f534e82d4f9b45b2eb3b59e676b71d52ff57d0"
EXPECTED_ALPHA_GPT2_PDF_SHA256 = "d4e540118939d4fe18e4ba2a4d76c34971059603690f37d8a450c01673912ded"
EXPECTED_ALPHA_GPT_V1_SOURCE_SHA256 = "eae0dc5de12c4c1cbbe765950f5d09a7873cf5de02653c7f8a4d36936fe8ad01"
EXPECTED_ALPHA_GPT_V2_SOURCE_SHA256 = "32aa99faa6df0d67f80f21b85f960f7e87c90ccca983c55655a4b566a04286a7"
EXPECTED_ALPHA_GPT2_SOURCE_SHA256 = "024a8b75847160906aa81c936b8ee3d92d2879699ca65c97dc9476c9dc244c8a"
EXPECTED_ALPHA_GPT_PAGE_SHA256 = "eb7cde412af721137132979fd7aefa7f2ea15a11fe09c4c6aaa324282345e55f"
EXPECTED_ALPHA_GPT2_PAGE_SHA256 = "7a889c52cce41d5693a6ae1466c568fabdd9a65e52ae9b8f9529e358bdfa7bd3"
EXPECTED_ACL_PAGE_SHA256 = "0ebf3cb301c58f58f5ab4ae990b7e156cf1761feb0d895cee36b47fd882eae83"
EXPECTED_ALPHA_GPT_V1_MAIN_SHA256 = "f63b816038331c2e09eb82c21c42ec0efc32606ce851e2bf9c30eb6971b71f12"
EXPECTED_ALPHA_GPT_V2_MAIN_SHA256 = "c68307407db7632a29d76b4ec8c0de8a06a4251c8fec50059b533c2fb1ac4081"
EXPECTED_ALPHA_GPT2_MAIN_SHA256 = "db50d8a041666bd8b50ee2c06f79fbc07d07d80de01867d95e8df186f56c4335"
EXPECTED_SOURCE_FILE_COUNTS = {"alpha_gpt_v1": 59, "alpha_gpt_v2": 25, "alpha_gpt2_v1": 24}
EXPECTED_COMMUNITY_HEAD = "2388b35d6085c0a1f752bca37fa20eb9d39f16b2"

GITHUB_QUERIES = (
    "Alpha-GPT in:name,description,readme",
    '"Alpha-GPT: Human-AI Interactive Alpha Mining"',
    "2308.00016",
    "2402.09746",
    '"Alpha-GPT 2.0" quantitative',
    '"Saizhuo Wang" Alpha-GPT',
    'AlphaGPT "alpha mining"',
    '"AlphaBot" "alpha mining"',
    '"WorldQuant International Quant Championship 2024" Alpha-GPT',
    '"Alpha-GPT" "Quantitative Investment"',
)


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


def pdf_text(path: Path) -> tuple[str, int, dict[str, Any]]:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages), len(reader.pages), dict(reader.metadata or {})


def token_list(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:[._/-][A-Za-z0-9]+)*", text.lower())


def validate_paper(path: Path, expected_hash: str, pages: int, required: tuple[str, ...]) -> tuple[str, dict[str, Any]]:
    if sha256(path) != expected_hash:
        raise ValueError(f"official paper hash changed: {path}")
    text, actual_pages, metadata = pdf_text(path)
    if actual_pages != pages:
        raise ValueError(f"official paper page count changed for {path}: {actual_pages}")
    normalized = re.sub(r"\s+", " ", text)
    missing = [value for value in required if value not in normalized]
    if missing:
        raise ValueError(f"official paper extraction changed for {path}: {missing}")
    return text, metadata


def source_role(archive_id: str, member: str) -> str:
    suffix = Path(member).suffix.lower()
    if archive_id == "alpha_gpt_v1" and member.startswith("alphagpt__1_/"):
        return "inactive_duplicate_source_tree"
    if archive_id == "alpha_gpt2_v1" and member in {
        "tex/experiment.tex", "tex/sysarch.tex", "tex/ui.tex", "tex/related.tex",
    }:
        return "inactive_alpha_gpt_1_carryover_not_input_by_main"
    if suffix in {".png", ".jpg", ".jpeg", ".pdf", ".ps"}:
        return "paper_figure_or_graphic_asset"
    if suffix == ".tex":
        return "paper_tex_source"
    if suffix in {".bib", ".bbl", ".bst"}:
        return "bibliography_source_or_build_product"
    if suffix in {".cls", ".sty"}:
        return "latex_class_or_style"
    if suffix in {".log", ".out", ".xcp"}:
        return "archived_build_product"
    return "other_document_source"


def read_source_archive(path: Path, archive_id: str, expected_hash: str, expected_main_hash: str) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    if sha256(path) != expected_hash:
        raise ValueError(f"official source archive hash changed: {archive_id}")
    payloads: dict[str, bytes] = {}
    rows: list[dict[str, str]] = []
    with tarfile.open(path, "r:*") as archive:
        members = sorted((member for member in archive.getmembers() if member.isfile()), key=lambda member: member.name)
        for member in members:
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"cannot read {archive_id}:{member.name}")
            payload = extracted.read()
            payloads[member.name] = payload
            rows.append(
                {
                    "archive_id": archive_id,
                    "source_member": member.name,
                    "bytes": str(len(payload)),
                    "sha256": bytes_sha256(payload),
                    "role": source_role(archive_id, member.name),
                    "native_pipeline_code": "no",
                    "raw_experiment_data_or_result_array": "no",
                    "paper_result_credit": "no",
                }
            )
    if len(rows) != EXPECTED_SOURCE_FILE_COUNTS[archive_id]:
        raise ValueError(f"official source member count changed for {archive_id}: {len(rows)}")
    if bytes_sha256(payloads["main.tex"]) != expected_main_hash:
        raise ValueError(f"official main.tex hash changed for {archive_id}")
    return payloads, rows


def build_comparison(label: str, official: Path, rebuilt: Path, expected_pages: int, relationship: str, compatibility_patch: str) -> dict[str, Any]:
    official_text, official_pages, _ = pdf_text(official)
    rebuilt_text, rebuilt_pages, _ = pdf_text(rebuilt)
    if official_pages != expected_pages or rebuilt_pages != expected_pages:
        raise ValueError(f"source build page count changed for {label}: {official_pages}/{rebuilt_pages}")
    a_tokens = token_list(official_text)
    b_tokens = token_list(rebuilt_text)
    a = Counter(a_tokens)
    b = Counter(b_tokens)
    intersection = sum((a & b).values())
    union = sum((a | b).values())
    return {
        "comparison_id": label,
        "official_pdf_sha256": sha256(official),
        "rebuilt_pdf_sha256": sha256(rebuilt),
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "official_tokens": sum(a.values()),
        "rebuilt_tokens": sum(b.values()),
        "token_multiset_jaccard": intersection / union,
        "token_sequence_ratio": difflib.SequenceMatcher(None, a_tokens, b_tokens, autojunk=False).ratio(),
        "source_relationship": relationship,
        "compatibility_patch": compatibility_patch,
        "document_credit": "yes",
        "native_system_or_result_credit": "no",
    }


def version_rows() -> list[dict[str, str]]:
    return [
        {
            "version": "Alpha-GPT arXiv v1",
            "date": "2023-07-31",
            "pages": "9",
            "model": "gpt-3.5-turbo-16k-0613; text-embedding-ada-002",
            "empirical_scope": "six displayed search-enhancement ideas, interaction backtest, qualitative formulas",
            "displayed_numeric_result_cells": "20",
            "plotted_result_series": "3",
            "native_results_reproduced": "0",
            "lineage_note": "original experimental paper",
        },
        {
            "version": "Alpha-GPT 2.0 arXiv v1",
            "date": "2024-02-15",
            "pages": "4",
            "model": "not specified",
            "empirical_scope": "none; explicitly Draft. Work in progress",
            "displayed_numeric_result_cells": "0",
            "plotted_result_series": "0",
            "native_results_reproduced": "0",
            "lineage_note": "conceptual successor; unused Alpha-GPT 1 experiment files in source are not paper evidence",
        },
        {
            "version": "Alpha-GPT arXiv v2",
            "date": "2025-09-20",
            "pages": "11",
            "model": "Llama3 70B; BGE-M3; GPT-4 judge/simulated user",
            "empirical_scope": "translation study, iterative IC, search curve, JoinQuant and WorldQuant comparisons",
            "displayed_numeric_result_cells": "47",
            "plotted_result_series": "2",
            "native_results_reproduced": "0",
            "lineage_note": "material rewrite, not a formatting-only revision",
        },
        {
            "version": "Alpha-GPT EMNLP 2025 final",
            "date": "2025-11",
            "pages": "11",
            "model": "same disclosed method as arXiv v2",
            "empirical_scope": "same displayed result objects as arXiv v2",
            "displayed_numeric_result_cells": "47",
            "plotted_result_series": "2",
            "native_results_reproduced": "0",
            "lineage_note": "ACL authoritative PDF; arXiv v2 TeX is close but is not an ACL-released source package",
        },
    ]


ARITIES = {
    "shift": 2,
    "minus": 2,
    "cwise_max": 2,
    "cwise_mul": 2,
    "div": 2,
    "zscore_scale": 1,
    "ts_corr": 3,
    "ts_delta": 2,
    "ts_rank": 2,
}


def formula_fixture() -> dict[str, pd.DataFrame]:
    index = pd.date_range("2020-01-01", periods=30)
    base = np.arange(90, dtype=float).reshape(30, 3) + 10
    close = pd.DataFrame(base, index=index, columns=["A", "B", "C"])
    time = np.arange(30, dtype=float)
    volume_noise = pd.DataFrame(
        np.column_stack(
            [
                50.0 * np.sin(time / 2.0),
                100.0 * np.cos(time / 3.0),
                70.0 * np.sin(time / 5.0 + 1.0),
            ]
        ),
        index=index,
        columns=close.columns,
    )
    return {
        "open": close - 0.5,
        "high": close + 1.5,
        "low": close - 1.0,
        "close": close,
        "volume": close * 100 + volume_noise,
        "amount": close * close * 100,
    }


def validate_call_arities(tree: ast.AST) -> list[str]:
    errors: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                errors.append("non-name callable")
                continue
            name = node.func.id
            if name not in ARITIES:
                errors.append(f"unknown operator {name}")
            elif len(node.args) != ARITIES[name]:
                errors.append(f"{name} expects {ARITIES[name]} arguments but received {len(node.args)}")
    return errors


def evaluate_formula_node(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return evaluate_formula_node(node.body, env)
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise TypeError(f"unsupported expression node: {ast.dump(node)}")
    name = node.func.id
    args = [evaluate_formula_node(arg, env) for arg in node.args]
    if name == "shift":
        return args[0].shift(int(args[1]))
    if name == "minus":
        return args[0] - args[1]
    if name == "cwise_max":
        return np.maximum(args[0], args[1])
    if name == "cwise_mul":
        return args[0] * args[1]
    if name == "div":
        return args[0] / args[1]
    if name == "zscore_scale":
        frame = args[0]
        return frame.sub(frame.mean(axis=1), axis=0).div(frame.std(axis=1, ddof=0).replace(0, np.nan), axis=0)
    if name == "ts_corr":
        return args[0].rolling(int(args[2])).corr(args[1])
    if name == "ts_delta":
        return args[0] - args[0].shift(int(args[1]))
    if name == "ts_rank":
        window = int(args[1])
        return args[0].rolling(window).apply(lambda values: pd.Series(values).rank(pct=True).iloc[-1], raw=False)
    raise KeyError(name)


def formula_rows() -> list[dict[str, str]]:
    formulas = (
        (
            "AGPT-FORM-01",
            "Flow of Funds",
            "div(cwise_mul(cwise_max(minus(close,shift(close, 1)), 0), amount, cwise_mul(close, volume)))",
            "the prose describes a numerator divided by close times volume, but the printed expression gives div one argument and cwise_mul three",
        ),
        ("AGPT-FORM-02", "Volume-price correlation", "zscore_scale(ts_corr(close, volume, 20))", "operator semantics and cross-sectional normalization are unreleased"),
        ("AGPT-FORM-03", "Shadow", "div(cwise_max(minus(high,open),minus(high,close)),minus(high,low))", "zero-range behavior and operator semantics are unreleased"),
        ("AGPT-FORM-04", "Momentum", "ts_delta(ts_rank(div(ts_delta(close,1),close),10),1)", "time-series rank convention and missing-data behavior are unreleased"),
    )
    fixture = formula_fixture()
    rows: list[dict[str, str]] = []
    for identifier, idea, expression, boundary in formulas:
        parse_status = "parsed"
        errors: list[str] = []
        runtime_status = "not_run_due_to_invalid_arity"
        finite_values = ""
        try:
            tree = ast.parse(expression, mode="eval")
            errors = validate_call_arities(tree)
        except SyntaxError as exc:
            parse_status = "syntax_error"
            errors = [f"SyntaxError: {exc}"]
            tree = None
        if tree is not None and not errors:
            result = evaluate_formula_node(tree, fixture)
            runtime_status = "executed_under_declared_conventional_operator_stub"
            finite_values = str(int(np.isfinite(np.asarray(result, dtype=float)).sum()))
        rows.append(
            {
                "formula_id": identifier,
                "paper_versions": "Alpha-GPT v1 and Alpha-GPT v2/ACL final",
                "trading_idea": idea,
                "published_expression": expression,
                "parse_status": parse_status,
                "arity_status": "valid" if not errors else "invalid",
                "arity_errors": " | ".join(errors),
                "runtime_status": runtime_status,
                "finite_values_on_deterministic_fixture": finite_values,
                "material_boundary": boundary,
                "conditional_component_credit": "yes" if not errors else "no",
                "native_pipeline_credit": "no",
                "paper_result_credit": "no",
            }
        )
    return rows


def displayed_result_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(version: str, result_id: str, location: str, metric: str, display_object: str, value: str = "", note: str = "") -> None:
        rows.append(
            {
                "version": version,
                "result_id": result_id,
                "location": location,
                "metric": metric,
                "display_object": display_object,
                "displayed_value": value,
                "raw_values_released": "no",
                "native_reproduced": "no",
                "paper_result_credit": "no",
                "note": note,
            }
        )

    ideas = {
        "trend_discrepancy": ("0.01151", "0.02256"),
        "shape": ("0.00995", "0.02190"),
        "rsi": ("0.01109", "0.02527"),
        "momentum": ("0.00951", "0.02763"),
        "mean_reversion": ("0.01130", "0.02187"),
        "flow_of_funds": ("0.00952", "0.02160"),
    }
    for idea, values in ideas.items():
        add("Alpha-GPT arXiv v1", f"V1-T1-{idea}-before", "Table 1", f"{idea} average top-20 out-of-sample IC before search", "numeric_table_cell", values[0])
        add("Alpha-GPT arXiv v1", f"V1-T1-{idea}-after", "Table 1", f"{idea} average top-20 out-of-sample IC after search", "numeric_table_cell", values[1])

    pipeline = (
        ("ts_ema(x,5,0.5)", "0.02303", "0.01945"),
        ("amount", "0.02105", "0.01904"),
        ("ts_corr(volume,close,5)", "0.01984", "0.01882"),
        ("grouped_demean(ts_delta(close,3),sw1_mask)", "0.01723", "0.01655"),
    )
    for index, (expression, train, test) in enumerate(pipeline, 1):
        for version, prefix, location in (
            ("Alpha-GPT arXiv v1", "V1", "Figure 2 workflow"),
            ("Alpha-GPT arXiv v2 / ACL final", "V2", "Figure 5 workflow"),
        ):
            add(version, f"{prefix}-PIPE-{index}-train", location, f"{expression} train IC", "numeric_figure_cell", train, "illustrative workflow figure; no underlying run is released")
            add(version, f"{prefix}-PIPE-{index}-test", location, f"{expression} test IC", "numeric_figure_cell", test, "illustrative workflow figure; no underlying run is released")

    for series in ("seed_alpha_round_1", "best_after_gp_round_1", "best_after_gp_round_2"):
        add("Alpha-GPT arXiv v1", f"V1-F6-{series}", "Figure 6", "cumulative return", "line_series", note="exact plotted array and portfolio construction absent")
    for panel in ("golden_cross", "bollinger_upper_breakout", "three_white_soldiers"):
        add("Alpha-GPT arXiv v1", f"V1-F5-{panel}", "Figure 5", "idea-formula visual correspondence", "qualitative_plot_panel", note="weekly S&P 500 chart shown without source series snapshot or exact plotted formula array")

    worldquant = {
        "worldwide_top_1": ("103", "52058", "57899", "50111"),
        "worldwide_top_10": ("47", "47112", "42303", "48715"),
        "regional_top_1": ("91", "50920", "55890", "49264"),
        "regional_top_10": ("74", "35999", "26292", "39325"),
        "alpha_gpt": ("81", "48866", "65505", "43319"),
    }
    for name, values in worldquant.items():
        for metric, value in zip(("qualified_alphas", "total_score", "in_sample_score", "out_of_sample_score"), values):
            add("Alpha-GPT arXiv v2 / ACL final", f"V2-T2-{name}-{metric}", "Table 2", f"{name} {metric}", "numeric_table_cell", value)
    for name, values in {"human": ("6.81", "13.40%"), "alpha_gpt": ("8.16", "86.60%")}.items():
        for metric, value in zip(("score", "win_rate"), values):
            add("Alpha-GPT arXiv v2 / ACL final", f"V2-T3-{name}-{metric}", "Table 3", f"{name} {metric}", "numeric_table_cell", value)
    for stage, value in {"seed": "0.58%", "search_enhancement": "1.23%", "interaction_plus_search": "2.23%"}.items():
        add("Alpha-GPT arXiv v2 / ACL final", f"V2-T4-{stage}", "Table 4", f"average IC {stage}", "numeric_table_cell", value)
    rank = {
        "top_1_human": ("21%", "6.88", "1.61%"),
        "top_5_percent": ("16%", "5.42", "1.59%"),
        "top_10_percent": ("13%", "4.16", "3.58%"),
        "alpha_gpt": ("14%", "5.47", "2.36%"),
    }
    for name, values in rank.items():
        for metric, value in zip(("return", "sharpe", "maximum_drawdown"), values):
            add("Alpha-GPT arXiv v2 / ACL final", f"V2-T5-{name}-{metric}", "Table 5", f"{name} {metric}", "numeric_table_cell", value)
    for series in ("in_sample_ic", "out_of_sample_ic"):
        add("Alpha-GPT arXiv v2 / ACL final", f"V2-F4-{series}", "Figure 4", series, "line_series", note="20-iteration plotted array absent")
    for panel in ("moving_average_divergence", "bollinger_upper_breakout", "three_bullish_movements"):
        add("Alpha-GPT arXiv v2 / ACL final", f"V2-F7-{panel}", "Figure 7", "idea-formula visual correspondence", "qualitative_plot_panel", note="weekly S&P 500 chart shown without source series snapshot or exact plotted formula array")
    return rows


def prompt_rows() -> list[dict[str, str]]:
    definitions = (
        ("AGPT-PROMPT-01", "v1", "knowledge-compiler role fragment", "partial", "you are a quant researcher developing formulaic alphas"),
        ("AGPT-PROMPT-02", "v1", "field specification example", "partial", "high_1D: highest intraday price of stocks"),
        ("AGPT-PROMPT-03", "v1/v2 figure", "system prompt template", "partial", "role and Instructions/Specifications placeholders are visible; full text is not"),
        ("AGPT-PROMPT-04", "v1/v2 figure", "user interaction example", "partial", "exploit momentum in volume and price; smooth; add confirmation signals"),
        ("AGPT-PROMPT-05", "v1", "invalid-alpha correction request", "missing", "described but not printed"),
        ("AGPT-PROMPT-06", "v1/v2", "retrieval query and memory rendering", "missing", "database and RAG operations are described but requests are absent"),
        ("AGPT-PROMPT-07", "v2", "Trading Idea Polisher system prompt", "missing", "agent role only"),
        ("AGPT-PROMPT-08", "v2", "Quant Developer system prompt", "missing", "agent role only"),
        ("AGPT-PROMPT-09", "v2", "Analyst system prompt", "missing", "agent role only"),
        ("AGPT-PROMPT-10", "v2", "autonomous hierarchical-RAG prompts", "missing", "RAG0--RAG3 flow only"),
        ("AGPT-PROMPT-11", "v2", "GPT-4 translation judge prompt", "missing", "scoring task is described but request/order controls are absent"),
        ("AGPT-PROMPT-12", "v2", "GPT-4 simulated-human prompt", "missing", "specifically designed prompts are asserted but not printed"),
        ("AGPT-PROMPT-13", "v2", "competition automation prompt", "missing", "automation is described but no immutable request is released"),
        ("AGPT-PROMPT-14", "Alpha-GPT 2.0", "three layer SOPs and agent system prompts", "missing", "SOPs are asserted but not disclosed"),
    )
    return [
        {
            "prompt_id": identifier,
            "version_scope": version,
            "role": role,
            "recovery_status": status,
            "text_or_evidence": evidence,
            "immutable_model_request_metadata": "no",
            "exact_replay_credit": "no",
        }
        for identifier, version, role, status, evidence in definitions
    ]


def issue_rows() -> list[dict[str, str]]:
    definitions = (
        ("AGPT-INT-001", "blocking", "v1 Table 1 says seven trading ideas but displays only six", "the complete result denominator and missing idea cannot be reconstructed"),
        ("AGPT-INT-002", "blocking", "the published Flow of Funds expression gives div one argument and cwise_mul three", "one of four showcased formulas fails the paper's own arity/validation premise"),
        ("AGPT-INT-003", "major", "v2 says 19 basic operators while Table 1 lists 55 comma-separated entries, duplicates ts_decayed_linear, and joins ts_delta.ts_delta_ratio", "the executable DSL/operator census is internally inconsistent"),
        ("AGPT-INT-004", "major", "v1 says inter-day data while v2 changes the experiment to intraday Chinese and US data", "carried-over figures cannot be assigned one stable data schema"),
        ("AGPT-INT-005", "major", "v2 Table 3 caption says one junior researcher while the text says five researchers with 0.5--2 years experience", "the comparison unit and aggregation are ambiguous"),
        ("AGPT-INT-006", "blocking", "Table 3 omits sample count, item identities, judge prompt, order randomization, ties, and uncertainty", "the 86.60% GPT-4-judged win rate cannot be recomputed"),
        ("AGPT-INT-007", "blocking", "Table 4 reports three average IC values without the trading-idea count, factor count, data split, raw ICs, or seeds", "the interaction improvement cannot be recomputed"),
        ("AGPT-INT-008", "blocking", "Figure 4 interprets out-of-sample stabilization as mitigation of overfitting without raw arrays, repeated trials, or uncertainty", "the generalization claim exceeds the displayed evidence"),
        ("AGPT-INT-009", "blocking", "WorldQuant Table 2 releases threshold rows and one Alpha-GPT row but no immutable leaderboard record, team identity, alpha list, or score export", "top-10 worldwide and top-3 regional attribution cannot be independently verified"),
        ("AGPT-INT-010", "blocking", "JoinQuant Table 5 lacks the exact competition snapshot, universe, dates, generated factors, costs, and evaluator", "the claimed same-protocol comparison cannot be rerun"),
        ("AGPT-INT-011", "major", "the proprietary alpha base and much of the knowledge library are unavailable", "retrieval, novelty, and generation behavior cannot be reconstructed"),
        ("AGPT-INT-012", "blocking", "the claim that many generated alphas are absent from literature and the proprietary base has no released novelty assay", "the novelty claim is unverifiable"),
        ("AGPT-INT-013", "blocking", "Alpha-GPT 2.0 claims improved efficiency and precision but contains no experiment or result", "the successor paper has no empirical object to reproduce"),
        ("AGPT-INT-014", "major", "Alpha-GPT 2.0's source archive carries unused Alpha-GPT 1 experiment, table, UI, and architecture files", "inactive source files must not be credited as 2.0 evidence"),
        ("AGPT-INT-015", "major", "Alpha-GPT 2.0 comments out the contribution claiming a developed multi-agent system", "the paper supports a proposed workflow more strongly than an operational system"),
        ("AGPT-INT-016", "major", "v1 Algorithm 1 has no bounded exit when too few expressions repeatedly parse", "exact retry/termination behavior is underspecified"),
        ("AGPT-INT-017", "major", "the v2 model stack changes from GPT-3.5/text-ada to Llama3/BGE-M3 while key qualitative assets are carried over", "version-specific result provenance is required"),
        ("AGPT-INT-018", "major", "all papers omit an immutable code/runtime/data snapshot", "document reconstruction does not establish native execution"),
    )
    return [
        {"issue_id": identifier, "severity": severity, "issue": issue, "replication_effect": effect, "paper_result_credit": "no"}
        for identifier, severity, issue, effect in definitions
    ]


def claim_rows() -> list[dict[str, str]]:
    definitions = (
        ("AGPT-CLAIM-01", "v1", "generated expressions are consistent with the three trading ideas", "qualitative images only; source arrays and exact three formulas absent"),
        ("AGPT-CLAIM-02", "v1", "search enhancement significantly improves top-20 out-of-sample IC", "12 cells shown; one of seven claimed ideas is missing and no raw runs are released"),
        ("AGPT-CLAIM-03", "v1", "human interaction significantly improves backtest performance", "three curves shown without raw paths, portfolio rules, costs, or tests"),
        ("AGPT-CLAIM-04", "v1", "Alpha-GPT appropriately explains generated alphas", "four selected examples; one expression has invalid arity and no evaluation is disclosed"),
        ("AGPT-CLAIM-05", "v2", "Alpha-GPT improves translation efficiency over humans", "GPT-4 judged aggregate lacks prompt, sample identities, denominator, and uncertainty"),
        ("AGPT-CLAIM-06", "v2", "interaction and search consistently improve IC", "three averages and a two-line curve lack raw arrays and repeat statistics"),
        ("AGPT-CLAIM-07", "v2", "Alpha-GPT reaches top 5--10% human HFT performance", "comparison table is not backed by released competition records or generated factors"),
        ("AGPT-CLAIM-08", "v2", "Alpha-GPT ranks top-10 worldwide and top-3 regionally in WorldQuant IQC 2024", "no immutable leaderboard/team evidence or alpha submission record"),
        ("AGPT-CLAIM-09", "v2", "out-of-sample scores show generalization and strong logic", "competition inputs, rules snapshot, and generated alpha set are absent"),
        ("AGPT-CLAIM-10", "v2", "Alpha-GPT may achieve superhuman alpha-mining performance", "interpretive extrapolation from unreleased competition evidence"),
        ("AGPT-CLAIM-11", "v2", "many generated alphas are novel relative to literature and proprietary base", "no novelty corpus, comparison, or result list"),
        ("AGPT-CLAIM-12", "Alpha-GPT 2.0", "full-pipeline human-in-the-loop workflow enhances efficiency and precision", "architecture proposal only; no experiment"),
        ("AGPT-CLAIM-13", "Alpha-GPT 2.0", "three specialized agents form a collaborative multi-agent research cycle", "no code, prompts, tools, traces, or execution outputs"),
    )
    return [
        {
            "claim_id": identifier,
            "version_scope": version,
            "claim": claim,
            "available_evidence": evidence,
            "exactly_reproduced": "no",
            "native_paper_result_reproduced": "no",
            "allow_positive_or_negative_native_inference": "no",
        }
        for identifier, version, claim, evidence in definitions
    ]


def method_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(scope: str, category: str, dimension: str, assessment: str, severity: str, evidence: str) -> None:
        rows.append(
            {
                "version_scope": scope,
                "category": category,
                "dimension": dimension,
                "assessment": assessment,
                "severity": severity,
                "evidence": evidence,
                "native_fidelity_effect": "blocks or conditions native fidelity" if severity in {"blocking", "major"} else "document/context evidence only",
            }
        )

    specified = (
        ("lineage", "official version dates", "arXiv records identify v1 and v2 dates"),
        ("documents", "authoritative PDFs", "arXiv and ACL PDFs pinned by SHA-256"),
        ("documents", "authoritative TeX archives", "three arXiv source archives pinned"),
        ("v1 model", "v1 chat model alias", "gpt-3.5-turbo-16k-0613"),
        ("v1 model", "v1 embedding model alias", "text-ada-embedding-002, dimension 1536"),
        ("v2 model", "v2 chat model family", "Llama3 70B"),
        ("v2 model", "v2 embedding model family", "BGE-M3"),
        ("v1 data", "v1 broad fields", "OHLCV, VWAP, sector"),
        ("v2 data", "v2 broad fields", "intraday OHLCV, VWAP, sector, Chinese and US stocks"),
        ("v1 evaluation", "v1 displayed IC cells", "12 exact table values"),
        ("v2 evaluation", "v2 displayed table cells", "39 exact primary table values"),
        ("formulas", "published qualitative formula count", "four exact Figure 7/8 expressions"),
        ("competition", "WorldQuant displayed snapshot date", "caption states June 25, 2024"),
        ("2.0", "Alpha-GPT 2.0 empirical result count", "zero; paper is marked Draft. Work in progress"),
    )
    for category, dimension, evidence in specified:
        add("as stated", category, dimension, "specified", "none", evidence)

    partial = (
        ("v1/v2", "prompts", "role fragments and placeholders, not full requests"),
        ("v1", "LLM retry algorithm", "pseudocode without bounded failure exit or runtime messages"),
        ("v1/v2", "operator names", "names listed but executable semantics absent"),
        ("v1", "data market", "stock markets named without exchange/universe membership"),
        ("v2", "data markets", "Chinese and US stocks without membership snapshot"),
        ("v1", "search fitness", "IC named without exact estimator or missing-data rules"),
        ("v1/v2", "knowledge corpus", "101 Formulaic Alphas named; decomposition corpus absent"),
        ("v1/v2", "Faiss use", "library named without index configuration or contents"),
        ("v2", "human comparison", "five experience ranges and GPT-4 scale disclosed"),
        ("v2", "interaction rounds", "one interaction and ten search rounds stated"),
        ("v2", "search iterations", "20 iterations visible"),
        ("v2", "JoinQuant competition", "public event link and three metrics stated"),
        ("v2", "WorldQuant competition", "stage, snapshot date, and four metrics stated"),
        ("v2", "autonomous RAG", "four conceptual RAG levels shown"),
        ("2.0", "agent roles", "alpha mining/modeling/analysis roles described"),
        ("2.0", "tool categories", "tool categories described without implementations"),
        ("2.0", "memory categories", "memory categories described without contents"),
        ("v1/v2", "qualitative formula semantics", "natural-language explanations but no operator implementation"),
        ("v1", "backtest period", "US stocks 2012--2021; no exact endpoints"),
        ("v1/v2", "S&P 500 qualitative chart", "weekly 2020--2023; no vendor or exact endpoint"),
    )
    for scope, dimension, evidence in partial:
        add(scope, "partial specification", dimension, "partial", "major", evidence)

    conflicts = (
        ("v1", "Table 1 idea count", "caption says seven; six displayed"),
        ("v1/v2", "published Flow of Funds formula arity", "div has one argument; cwise_mul has three"),
        ("v2", "operator census", "19 claimed versus 55 listed entries"),
        ("v2", "operator tokenization", "ts_delta.ts_delta_ratio joined and ts_decayed_linear duplicated"),
        ("v1/v2", "data cadence", "inter-day in v1 versus intraday in v2"),
        ("v2", "human comparator count", "caption singular versus five in prose"),
        ("2.0", "developed-system contribution", "multi-agent-development contribution is commented out"),
        ("2.0", "source-to-paper experimental scope", "unused v1 experiment files are bundled but absent from main"),
        ("v2", "overfitting conclusion", "stabilization interpreted as mitigation without uncertainty"),
        ("v1", "validated formula premise", "showcased Flow of Funds formula violates normal arities"),
        ("community", "README runtime entrypoints", "requirements.txt and main.py instructions name absent files"),
        ("community", "README implemented modules", "Zipline, Alphalens, PyGAD, GP, and backtest claims have no source/dependency implementation"),
    )
    for scope, dimension, evidence in conflicts:
        add(scope, "internal conflict", dimension, "conflict", "blocking" if dimension in {"Table 1 idea count", "published Flow of Funds formula arity", "source-to-paper experimental scope"} else "major", evidence)

    missing_dimensions = (
        ("v1/v2", "release", "Alpha-GPT v1/final author-linked repository"),
        ("v1/v2", "release", "native AlphaBot implementation"),
        ("v1/v2", "release", "native genetic-programming implementation"),
        ("v1/v2", "release", "native backtest engine"),
        ("v1/v2", "release", "native deployment layer"),
        ("v1/v2", "release", "immutable Python/package runtime"),
        ("v1/v2", "release", "model checkpoint or hosted snapshot"),
        ("v1/v2", "release", "runtime traces and tool transcripts"),
        ("v1/v2", "data", "market-data vendor"),
        ("v1/v2", "data", "security universe membership"),
        ("v1/v2", "data", "survivorship handling"),
        ("v1/v2", "data", "corporate-action handling"),
        ("v1/v2", "data", "calendar and timezone"),
        ("v1/v2", "data", "exact train validation test dates"),
        ("v1/v2", "data", "label horizon"),
        ("v1/v2", "data", "point-in-time sector classification"),
        ("v1/v2", "data", "raw input snapshot"),
        ("v1/v2", "operators", "operator implementation"),
        ("v1/v2", "operators", "time-series warm-up rules"),
        ("v1/v2", "operators", "cross-sectional standardization convention"),
        ("v1/v2", "operators", "missing and infinite value handling"),
        ("v1/v2", "operators", "unit checking rules"),
        ("v1/v2", "operators", "expression AST grammar"),
        ("v1/v2", "prompts", "complete system prompts"),
        ("v1/v2", "prompts", "complete user prompts"),
        ("v1/v2", "prompts", "few-shot demonstrations"),
        ("v1/v2", "prompts", "retrieved memory records"),
        ("v1/v2", "prompts", "output parser implementation"),
        ("v1/v2", "prompts", "retry requests and responses"),
        ("v1/v2", "model", "decoding seed"),
        ("v1/v2", "model", "top-p and token limit"),
        ("v1/v2", "model", "temperature"),
        ("v1/v2", "model", "provider/model revision"),
        ("v1/v2", "search", "GP population size"),
        ("v1/v2", "search", "initialization distribution"),
        ("v1/v2", "search", "crossover probability"),
        ("v1/v2", "search", "mutation probability"),
        ("v1/v2", "search", "selection method"),
        ("v1/v2", "search", "complexity regularization"),
        ("v1/v2", "search", "early stopping implementation"),
        ("v1/v2", "search", "candidate deduplication rule"),
        ("v1/v2", "search", "candidate expression library"),
        ("v1/v2", "evaluation", "IC formula"),
        ("v1/v2", "evaluation", "top-20 selection rule"),
        ("v1/v2", "evaluation", "portfolio weighting rule"),
        ("v1/v2", "evaluation", "return horizon"),
        ("v1/v2", "evaluation", "transaction costs"),
        ("v1/v2", "evaluation", "turnover convention"),
        ("v1/v2", "evaluation", "Sharpe annualization"),
        ("v1/v2", "evaluation", "maximum-drawdown convention"),
        ("v1/v2", "evaluation", "random seeds and repeated runs"),
        ("v1/v2", "evaluation", "raw result arrays"),
        ("v1/v2", "evaluation", "per-factor outputs"),
        ("v1/v2", "evaluation", "uncertainty intervals"),
        ("v1/v2", "evaluation", "multiplicity correction"),
        ("v2", "human study", "trading-idea dataset"),
        ("v2", "human study", "item count"),
        ("v2", "human study", "human alpha outputs"),
        ("v2", "human study", "Alpha-GPT alpha outputs"),
        ("v2", "human study", "GPT-4 judge prompt"),
        ("v2", "human study", "judge order blinding"),
        ("v2", "human study", "tie and disagreement handling"),
        ("v2", "competition", "WorldQuant raw leaderboard record"),
        ("v2", "competition", "WorldQuant team identity"),
        ("v2", "competition", "WorldQuant generated alpha list"),
        ("v2", "competition", "WorldQuant rules snapshot"),
        ("v2", "competition", "JoinQuant raw leaderboard record"),
        ("v2", "competition", "JoinQuant data and evaluator"),
        ("v2", "novelty", "novelty comparison corpus"),
        ("v2", "novelty", "novelty matching criterion"),
        ("2.0", "evaluation", "Alpha-GPT 2.0 empirical evaluation"),
        ("2.0", "implementation", "Alpha-GPT 2.0 agent code"),
        ("2.0", "implementation", "Alpha-GPT 2.0 SOP prompts"),
        ("2.0", "implementation", "Alpha-GPT 2.0 tool APIs"),
        ("2.0", "implementation", "Alpha-GPT 2.0 memory contents"),
        ("2.0", "implementation", "Alpha-GPT 2.0 model zoo"),
        ("2.0", "implementation", "Alpha-GPT 2.0 financial knowledge graph"),
    )
    for scope, category, dimension in missing_dimensions:
        add(scope, category, dimension, "missing", "blocking", "not released in the authoritative paper/source record")
    return rows


def local_mapping_rows() -> list[dict[str, str]]:
    return [
        {
            "candidate_id": "paper_alpha_gpt_interactive_formula",
            "source_paper": "Alpha-GPT",
            "local_tier": "M0_narrative_translation",
            "source_anchor": "human-AI formulaic alpha mining narrative only",
            "local_formula": "rank(be_me)+rank(ret_12_1)+rank(ope_be)+rank(gp_me)-rank(debt_at)",
            "material_changes": "all characteristics, signs, monthly U.S. top-1000 data, value-weighted deciles, and returns are researcher supplied; no Alpha-GPT generation/search path is used",
            "paper_result_credit": "no",
        },
        {
            "candidate_id": "paper_alpha_gpt2_full_pipeline",
            "source_paper": "Alpha-GPT 2.0",
            "local_tier": "M0_narrative_translation",
            "source_anchor": "full-pipeline mining/modeling/analysis architecture narrative only",
            "local_formula": "rank(be_me)+rank(ret_12_1)+rank(qmj)+rank(sale_gr1)-rank(rvol_252d)-rank(beta_252d)",
            "material_changes": "the four-page source contains no empirical formula or result; all characteristics, signs, portfolio rules, data, and returns are researcher supplied",
            "paper_result_credit": "no",
        },
    ]


def github_rows(directory: Path) -> list[dict[str, str]]:
    paths = sorted(directory.glob("*.json"))
    if len(paths) != len(GITHUB_QUERIES):
        raise ValueError(f"expected {len(GITHUB_QUERIES)} GitHub search snapshots, found {len(paths)}")
    rows: list[dict[str, str]] = []
    for query, path in zip(GITHUB_QUERIES, paths):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "query": query,
                "snapshot_file": path.name,
                "snapshot_sha256": sha256(path),
                "total_count": str(data["total_count"]),
                "incomplete_results": str(bool(data["incomplete_results"])).lower(),
                "repositories": "|".join(item["full_name"] for item in data.get("items", [])),
                "author_linked_repository_found": "no",
                "search_interpretation": "broad name/readme collision search" if path.name.startswith("01_") else "targeted paper/author/source search",
            }
        )
    return rows


def community_inventory(repo: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, text=True, capture_output=True).stdout.strip()
    if head != EXPECTED_COMMUNITY_HEAD:
        raise ValueError(f"community repository head changed: {head}")
    raw = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], check=True, capture_output=True).stdout
    names = [item.decode("utf-8") for item in raw.split(b"\0") if item]
    rows: list[dict[str, str]] = []
    compiled = 0
    for name in names:
        path = repo / name
        payload = path.read_bytes()
        compile_status = "not_python"
        if path.suffix == ".py":
            try:
                compile(payload, name, "exec")
                compile_status = "compiled"
                compiled += 1
            except SyntaxError as exc:
                compile_status = f"SyntaxError: {exc}"
        role = "python_source" if name.startswith("src/") and path.suffix == ".py" else "test" if name.startswith("tests/") else "documentation_or_configuration"
        rows.append(
            {
                "path": name,
                "bytes": str(len(payload)),
                "sha256": bytes_sha256(payload),
                "role": role,
                "compile_status": compile_status,
                "native_author_source": "no",
                "native_paper_result_output": "no",
            }
        )
    readme = (repo / "README.md").read_text(encoding="utf-8")
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    graph = (repo / "src/agent/graph.py").read_text(encoding="utf-8")
    all_source = "\n".join((repo / name).read_text(encoding="utf-8", errors="replace") for name in names if name.endswith(".py"))
    conformance = [
        {"dimension": "author linkage", "assessment": "nonmatch", "evidence": "all five commits are by Parth Modi; no paper-author overlap", "native_credit": "no"},
        {"dimension": "repository self-description", "assessment": "unaffiliated inspiration", "evidence": "README thanks the two papers as foundational research and labels the project work in progress", "native_credit": "no"},
        {"dimension": "model", "assessment": "different", "evidence": "GPT-4o at temperatures 0.1/0.3/0.4 versus paper GPT-3.5 or Llama3 70B", "native_credit": "no"},
        {"dimension": "workflow", "assessment": "partial community implementation", "evidence": "graph ends after user input, hypothesis, alpha generation, and LLM coding", "native_credit": "no"},
        {"dimension": "genetic programming", "assessment": "missing", "evidence": "no PyGAD dependency or GP source path", "native_credit": "no"},
        {"dimension": "backtesting", "assessment": "missing", "evidence": "database can store supplied backtest fields but graph contains no evaluator", "native_credit": "no"},
        {"dimension": "Zipline/Alphalens/PyGAD", "assessment": "README-only", "evidence": "none appears in pyproject or source", "native_credit": "no"},
        {"dimension": "paper DSL", "assessment": "different", "evidence": "prompts request LaTeX formulas and generated Qlib-style pandas code rather than the paper operator compiler", "native_credit": "no"},
        {"dimension": "data", "assessment": "missing", "evidence": "no market dataset or dated result stream", "native_credit": "no"},
        {"dimension": "README entrypoints", "assessment": "broken", "evidence": "README instructs requirements.txt and main.py, neither tracked", "native_credit": "no"},
        {"dimension": "tests", "assessment": "not reproducible from declared package", "evidence": "langsmith/pytest dev requirements absent; supplied test input does not match State fields", "native_credit": "no"},
        {"dimension": "published results", "assessment": "missing", "evidence": "no v1, v2, competition, or 2.0 result artifacts", "native_credit": "no"},
    ]
    summary = {
        "repository": COMMUNITY_REPOSITORY,
        "head": head,
        "tracked_files": len(rows),
        "tracked_python_files": sum(row["path"].endswith(".py") for row in rows),
        "compiled_python_files": compiled,
        "created_after_papers": True,
        "paper_author_overlap": False,
        "readme_mentions_zipline_alphalens_pygad": all(token in readme for token in ("Zipline", "Alphalens", "PyGAD")),
        "declared_dependencies_include_zipline_alphalens_pygad": any(token in pyproject.lower() for token in ("zipline", "alphalens", "pygad")),
        "source_contains_zipline_alphalens_pygad": bool(re.search(r"zipline|alphalens|pygad", all_source, re.I)),
        "graph_contains_backtest_or_gp_node": bool(re.search(r"add_node\([^\n]*(backtest|genetic|search)", graph, re.I)),
        "native_credit": False,
    }
    return rows, conformance, summary


def readme(manifest: dict[str, Any]) -> str:
    return f"""# Alpha-GPT lineage paper/source replication audit

This package audits Alpha-GPT arXiv v1 and v2, the EMNLP 2025 authoritative
final, Alpha-GPT 2.0 v1, all three official TeX archives, four published
formula examples, ten repository searches, and the prominent unaffiliated
`parthmodi152/alpha-gpt` project. The audit is fail-closed: document rebuilds,
published figures, and a community implementation do not count as native
Alpha-GPT executions.

## Verdict

- **Alpha-GPT v1 native results reproduced: 0/20 displayed numeric cells and
  0/3 backtest line series.**
- **Alpha-GPT v2 / ACL-final native results reproduced: 0/47 displayed numeric
  cells and 0/2 search-enhancement line series.**
- **Alpha-GPT 2.0 has no empirical result denominator:** it is a four-page
  document explicitly marked `Draft. Work in progress` and contains no
  experiment.
- All source documents rebuild to the correct page counts. Extracted-token
  multiset Jaccard is {manifest['v1_document_jaccard']:.4%} for v1 and
  {manifest['alpha_gpt2_document_jaccard']:.4%} for Alpha-GPT 2.0 after one
  current-TeX compatibility repair. The arXiv-v2 source rebuild is
  {manifest['v2_arxiv_document_jaccard']:.4%} against arXiv v2 and
  {manifest['v2_acl_document_jaccard']:.4%} against the separately produced ACL
  final; this is strong document evidence, not experiment reproduction.
- Of four exact formula examples, three pass ordinary arity checks and execute
  under an explicitly non-native conventional operator stub. The published
  Flow of Funds expression does not: `div` receives one argument and
  `cwise_mul` receives three, despite the paper's syntax/semantic-validation
  premise.
- Ten complete GitHub repository searches find no author-linked code or data.
  The broad search finds `parthmodi152/alpha-gpt`, but it is an acknowledged
  paper-inspired, work-in-progress project by a non-author. Its graph stops
  after LLM code generation and contains no GP, backtest, market data, or paper
  results.
- Both local strategies remain M0 narrative translations. Their JKP
  characteristics, signs, monthly U.S. universe, decile construction, weights,
  and returns were not generated or tested by either paper.

## Material blockers

- No author-linked implementation, data snapshot, universe membership, full
  prompts, retrieved memory, generated alpha set, GP state, model requests,
  portfolio evaluator, seeds, raw arrays, or runtime lock is released.
- V1 Table 1 says seven trading ideas but contains six. Its 12 IC cells and the
  three interaction curves have no underlying runs.
- The 2025 rewrite changes GPT-3.5/text-ada to Llama3/BGE-M3 and changes the
  data description from inter-day to intraday while carrying over qualitative
  assets. Version-specific provenance is therefore essential.
- The human comparison omits the item count, judge prompt, ordering, ties, and
  uncertainty. The interaction/search averages omit raw ICs, splits, and
  repeats.
- JoinQuant and WorldQuant claims have no immutable leaderboard/team record,
  generated alpha list, input snapshot, evaluator, or result export.
- Alpha-GPT 2.0's archive contains unused Alpha-GPT 1 experimental files; they
  are not rendered by `main.tex` and receive no 2.0 evidence credit.

## Files

- `source_provenance.json`, `source_file_inventory.csv`, and
  `source_build_audit.csv`: pinned original records, 108 source members, and
  document rebuild comparisons.
- `version_lineage_audit.csv`: model, scope, and result changes across four
  publication records.
- `displayed_result_conformance.csv`: every displayed numeric cell and plotted
  result object in v1 and the ACL-final study.
- `published_formula_conformance.csv`: exact parse, arity, and conditional-stub
  checks for four showcased expressions.
- `prompt_inventory.csv`, `method_specification_audit.csv`,
  `paper_internal_consistency_audit.csv`, and `claim_audit.csv`: missing
  specifications, conflicts, and fail-closed claims.
- `community_source_inventory.csv`, `community_method_conformance.csv`, and
  `source_search_inventory.csv`: non-native source-search evidence.
- `local_mapping_conformance.csv`, `native_execution.json`, and
  `manifest.json`: local M0 boundaries and machine-readable verdict.
"""


def build(args: argparse.Namespace) -> dict[str, Any]:
    alpha_gpt_v1_pdf = args.alpha_gpt_v1_pdf.resolve()
    alpha_gpt_v2_pdf = args.alpha_gpt_v2_pdf.resolve()
    acl_final_pdf = args.acl_final_pdf.resolve()
    alpha_gpt2_pdf = args.alpha_gpt2_pdf.resolve()
    validate_paper(alpha_gpt_v1_pdf, EXPECTED_ALPHA_GPT_V1_PDF_SHA256, 9, ("Alpha-GPT", "gpt-3.5-turbo-16k-0613", "Before search enhancement"))
    validate_paper(alpha_gpt_v2_pdf, EXPECTED_ALPHA_GPT_V2_PDF_SHA256, 11, ("Alpha-GPT", "Llama3 70B", "WorldQuant International Quant Championship"))
    validate_paper(acl_final_pdf, EXPECTED_ACL_FINAL_PDF_SHA256, 11, ("Alpha-GPT", "Llama3 70B", "WorldQuant International Quant Championship"))
    validate_paper(alpha_gpt2_pdf, EXPECTED_ALPHA_GPT2_PDF_SHA256, 4, ("Alpha-GPT 2.0", "Draft. Work in progress", "Alpha Analysis Layer"))
    for path, expected, label in (
        (args.alpha_gpt_page, EXPECTED_ALPHA_GPT_PAGE_SHA256, "Alpha-GPT arXiv record"),
        (args.alpha_gpt2_page, EXPECTED_ALPHA_GPT2_PAGE_SHA256, "Alpha-GPT 2.0 arXiv record"),
        (args.acl_page, EXPECTED_ACL_PAGE_SHA256, "ACL record"),
    ):
        if sha256(path) != expected:
            raise ValueError(f"official page hash changed: {label}")

    _, v1_source = read_source_archive(args.alpha_gpt_v1_source, "alpha_gpt_v1", EXPECTED_ALPHA_GPT_V1_SOURCE_SHA256, EXPECTED_ALPHA_GPT_V1_MAIN_SHA256)
    _, v2_source = read_source_archive(args.alpha_gpt_v2_source, "alpha_gpt_v2", EXPECTED_ALPHA_GPT_V2_SOURCE_SHA256, EXPECTED_ALPHA_GPT_V2_MAIN_SHA256)
    _, gpt2_source = read_source_archive(args.alpha_gpt2_source, "alpha_gpt2_v1", EXPECTED_ALPHA_GPT2_SOURCE_SHA256, EXPECTED_ALPHA_GPT2_MAIN_SHA256)
    source_files = v1_source + v2_source + gpt2_source

    compatibility = "swap bundled 2023 acmart hyperref/hyperxmp load order only; manuscript and assets unchanged"
    builds = [
        build_comparison("alpha_gpt_v1", alpha_gpt_v1_pdf, args.alpha_gpt_v1_rebuild, 9, "exact v1 source archive", compatibility),
        build_comparison("alpha_gpt_v2_arxiv", alpha_gpt_v2_pdf, args.alpha_gpt_v2_rebuild, 11, "exact arXiv-v2 source archive", "none"),
        build_comparison("alpha_gpt_v2_to_acl_final", acl_final_pdf, args.alpha_gpt_v2_rebuild, 11, "arXiv-v2 source compared with separately produced ACL final", "none"),
        build_comparison("alpha_gpt2_v1", alpha_gpt2_pdf, args.alpha_gpt2_rebuild, 4, "exact Alpha-GPT 2.0 v1 source archive", compatibility),
    ]
    formulas = formula_rows()
    results = displayed_result_rows()
    prompts = prompt_rows()
    issues = issue_rows()
    claims = claim_rows()
    methods = method_rows()
    mappings = local_mapping_rows()
    searches = github_rows(args.github_search_dir)
    community_files, community_methods, community_summary = community_inventory(args.community_repo)

    if args.community_pytest_log:
        pytest_text = args.community_pytest_log.read_text(encoding="utf-8", errors="replace")
        community_summary["supplied_test_attempt"] = "collection_failed"
        community_summary["supplied_test_failure_mentions"] = sorted(set(re.findall(r"No module named '[^']+'", pytest_text)))
        community_summary["supplied_test_log_sha256"] = sha256(args.community_pytest_log)

    v1_numeric = sum(row["version"] == "Alpha-GPT arXiv v1" and row["display_object"] in {"numeric_table_cell", "numeric_figure_cell"} for row in results)
    v2_numeric = sum(row["version"] == "Alpha-GPT arXiv v2 / ACL final" and row["display_object"] in {"numeric_table_cell", "numeric_figure_cell"} for row in results)
    v1_lines = sum(row["version"] == "Alpha-GPT arXiv v1" and row["display_object"] == "line_series" for row in results)
    v2_lines = sum(row["version"] == "Alpha-GPT arXiv v2 / ACL final" and row["display_object"] == "line_series" for row in results)
    if (v1_numeric, v2_numeric, v1_lines, v2_lines) != (20, 47, 3, 2):
        raise AssertionError("Alpha-GPT displayed-result census changed")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifacts = (
        ("source_file_inventory.csv", source_files),
        ("source_build_audit.csv", builds),
        ("version_lineage_audit.csv", version_rows()),
        ("displayed_result_conformance.csv", results),
        ("published_formula_conformance.csv", formulas),
        ("prompt_inventory.csv", prompts),
        ("method_specification_audit.csv", methods),
        ("paper_internal_consistency_audit.csv", issues),
        ("claim_audit.csv", claims),
        ("local_mapping_conformance.csv", mappings),
        ("source_search_inventory.csv", searches),
        ("community_source_inventory.csv", community_files),
        ("community_method_conformance.csv", community_methods),
    )
    for name, rows in artifacts:
        write_csv(output / name, rows, list(rows[0]))

    source_provenance = {
        "alpha_gpt_record": ALPHA_GPT_RECORD,
        "alpha_gpt_record_sha256": sha256(args.alpha_gpt_page),
        "alpha_gpt_v1_pdf": ALPHA_GPT_V1_PDF_URL,
        "alpha_gpt_v1_pdf_sha256": sha256(alpha_gpt_v1_pdf),
        "alpha_gpt_v1_source": ALPHA_GPT_V1_SOURCE_URL,
        "alpha_gpt_v1_source_sha256": sha256(args.alpha_gpt_v1_source),
        "alpha_gpt_v2_pdf": ALPHA_GPT_V2_PDF_URL,
        "alpha_gpt_v2_pdf_sha256": sha256(alpha_gpt_v2_pdf),
        "alpha_gpt_v2_source": ALPHA_GPT_V2_SOURCE_URL,
        "alpha_gpt_v2_source_sha256": sha256(args.alpha_gpt_v2_source),
        "acl_record": ACL_RECORD,
        "acl_record_sha256": sha256(args.acl_page),
        "acl_final_pdf": ACL_PDF_URL,
        "acl_final_pdf_sha256": sha256(acl_final_pdf),
        "alpha_gpt2_record": ALPHA_GPT2_RECORD,
        "alpha_gpt2_record_sha256": sha256(args.alpha_gpt2_page),
        "alpha_gpt2_pdf": ALPHA_GPT2_PDF_URL,
        "alpha_gpt2_pdf_sha256": sha256(alpha_gpt2_pdf),
        "alpha_gpt2_source": ALPHA_GPT2_SOURCE_URL,
        "alpha_gpt2_source_sha256": sha256(args.alpha_gpt2_source),
        "source_members": len(source_files),
        "author_linked_code_or_data_found": False,
        "github_repository_searches": searches,
        "community_repository": community_summary,
    }
    write_json(output / "source_provenance.json", source_provenance)

    native = {
        "attempted": False,
        "reason": "no_author_linked_pipeline_data_prompts_memory_search_state_generated_alphas_evaluator_or_raw_results",
        "author_linked_code_found": False,
        "alpha_gpt_v1_numeric_cells_reproduced": 0,
        "alpha_gpt_v1_numeric_cells_total": v1_numeric,
        "alpha_gpt_v1_line_series_reproduced": 0,
        "alpha_gpt_v1_line_series_total": v1_lines,
        "alpha_gpt_final_numeric_cells_reproduced": 0,
        "alpha_gpt_final_numeric_cells_total": v2_numeric,
        "alpha_gpt_final_line_series_reproduced": 0,
        "alpha_gpt_final_line_series_total": v2_lines,
        "alpha_gpt2_empirical_result_units_total": 0,
        "published_formula_examples": len(formulas),
        "published_formula_examples_arity_valid": sum(row["arity_status"] == "valid" for row in formulas),
        "published_formula_examples_conditionally_executed": sum(row["runtime_status"] == "executed_under_declared_conventional_operator_stub" for row in formulas),
        "community_repository_native_credit": False,
        "local_mapping_status": "two_M0_narrative_translations_zero_paper_result_credit",
        "paper_result_credit": False,
    }
    write_json(output / "native_execution.json", native)

    method_counts = dict(sorted(Counter(row["assessment"] for row in methods).items()))
    method_severity = dict(sorted(Counter(row["severity"] for row in methods).items()))
    manifest = {
        "audit": "Alpha-GPT v1/v2/ACL final and Alpha-GPT 2.0 lineage",
        "overall_fidelity": "three_official_documents_rebuilt_and_lineage_audited_zero_native_alpha_gpt_results_alpha_gpt2_is_unevaluated_draft",
        "official_pdf_pages_audited": 35,
        "official_pdf_pages_visually_inspected": 35,
        "official_source_members": len(source_files),
        "v1_document_jaccard": builds[0]["token_multiset_jaccard"],
        "v2_arxiv_document_jaccard": builds[1]["token_multiset_jaccard"],
        "v2_acl_document_jaccard": builds[2]["token_multiset_jaccard"],
        "alpha_gpt2_document_jaccard": builds[3]["token_multiset_jaccard"],
        "alpha_gpt_v1_numeric_result_cells": v1_numeric,
        "alpha_gpt_v1_numeric_result_cells_reproduced": 0,
        "alpha_gpt_v1_line_series": v1_lines,
        "alpha_gpt_v1_line_series_reproduced": 0,
        "alpha_gpt_final_numeric_result_cells": v2_numeric,
        "alpha_gpt_final_numeric_result_cells_reproduced": 0,
        "alpha_gpt_final_line_series": v2_lines,
        "alpha_gpt_final_line_series_reproduced": 0,
        "alpha_gpt2_empirical_result_units": 0,
        "published_formula_examples": len(formulas),
        "published_formula_examples_arity_valid": sum(row["arity_status"] == "valid" for row in formulas),
        "author_linked_code_found": False,
        "github_searches": len(searches),
        "community_repository_head": community_summary["head"],
        "community_repository_native_credit": False,
        "method_dimensions": len(methods),
        "method_assessments": method_counts,
        "method_severities": method_severity,
        "internal_consistency_issues": len(issues),
        "blocking_internal_consistency_issues": sum(row["severity"] == "blocking" for row in issues),
        "local_mappings": "two_M0_narrative_translations",
        "paper_result_credit": False,
    }
    write_json(output / "manifest.json", manifest)
    (output / "README.md").write_text(readme(manifest), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha-gpt-v1-pdf", type=Path, required=True)
    parser.add_argument("--alpha-gpt-v2-pdf", type=Path, required=True)
    parser.add_argument("--acl-final-pdf", type=Path, default=ROOT / "literature_review/papers/11_alpha_gpt_human_ai_interactive_alpha_mining_for_quantitative_investment_acl_anthology.pdf")
    parser.add_argument("--alpha-gpt2-pdf", type=Path, default=ROOT / "literature_review/papers/12_alpha_gpt_2_0_human_in_the_loop_ai_for_quantitative_investment.pdf")
    parser.add_argument("--alpha-gpt-v1-source", type=Path, required=True)
    parser.add_argument("--alpha-gpt-v2-source", type=Path, required=True)
    parser.add_argument("--alpha-gpt2-source", type=Path, required=True)
    parser.add_argument("--alpha-gpt-v1-rebuild", type=Path, required=True)
    parser.add_argument("--alpha-gpt-v2-rebuild", type=Path, required=True)
    parser.add_argument("--alpha-gpt2-rebuild", type=Path, required=True)
    parser.add_argument("--alpha-gpt-page", type=Path, required=True)
    parser.add_argument("--alpha-gpt2-page", type=Path, required=True)
    parser.add_argument("--acl-page", type=Path, required=True)
    parser.add_argument("--github-search-dir", type=Path, required=True)
    parser.add_argument("--community-repo", type=Path, required=True)
    parser.add_argument("--community-pytest-log", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "paper_runs/paper_replication_audits/alpha_gpt_lineage")
    args = parser.parse_args()
    manifest = build(args)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
