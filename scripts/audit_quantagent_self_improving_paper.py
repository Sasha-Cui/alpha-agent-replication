#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for arXiv:2402.03755v1.

The released TeX archive is strong document evidence and includes four Python
listings.  It does not include the QuantAgent implementation, prompts, data,
knowledge base, generated signals, model fit, or arrays behind the result
figures.  This audit therefore separates manuscript reconstruction and literal
snippet checks from native experimental reproduction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import tarfile
import types
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from pypdf import PdfReader


PAPER_URL = "https://arxiv.org/abs/2402.03755v1"
PDF_URL = "https://arxiv.org/pdf/2402.03755v1"
SOURCE_URL = "https://export.arxiv.org/e-print/2402.03755v1"
DOI = "10.48550/arXiv.2402.03755"
EXPECTED_PDF_SHA256 = "2162e659c9739d145c8cb93fdff31a0e27d9ab483b7a42bc2e52dd92cc39ac81"
EXPECTED_PAGE_SHA256 = "2336d3dc18d26b42aa219518bf3749b229983ab299b47481f82b623ed92159fa"
EXPECTED_SOURCE_SHA256 = "d54ccd4f53f2efbb2b3809a9a8b87f0f2bcdc421c6181a1bfde6666602cda8f4"
EXPECTED_MAIN_TEX_SHA256 = "a0e3083805524bd13bcb5e51e7f9d14dd80b0d1061f293a0f28b55c77a287ee2"
EXPECTED_APPENDIX_TEX_SHA256 = "45f859d4a4f11ece4532a888cfae2ed7f4134d7b1577c417f62caaead22165d1"
EXPECTED_PAGES = 15
EXPECTED_SOURCE_FILES = 44

GITHUB_QUERIES = (
    '"QuantAgent Seeking Holy Grail"',
    "2402.03755",
    "QuantAgent self-improving LLM trading",
    '"Saizhuo Wang" QuantAgent',
    '"Hang Yuan" QuantAgent',
    "ThreeSoldierSignal",
    "VolatilityBreakoutSignal idea_factor",
    "idea-factor financial signal",
)

ACTIVE_METHOD_FIGURES = {"figs/method.pdf", "figs/analysis.pdf"}
ACTIVE_RESULT_FIGURES = {
    "figs/single_alpha_perf.pdf",
    "figs/relevance.pdf",
    "figs/model.png",
}


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
        raise ValueError(f"official QuantAgent page count changed: {pages}")
    normalized = re.sub(r"\s+", " ", text)
    required = (
        "QuantAgent: Seeking Holy Grail",
        "gpt-4-0125-preview",
        "500 stocks on Chinese A-share market",
        "ThreeSoldierSignalV3",
        "VolatilityBreakoutSignal",
        "The Bayesian regret of the LLM agent",
    )
    missing = [token for token in required if token not in normalized]
    if missing:
        raise ValueError(f"official QuantAgent extraction changed: {missing}")


def read_source(source_tar: Path) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    payloads: dict[str, bytes] = {}
    rows: list[dict[str, str]] = []
    with tarfile.open(source_tar, "r:*") as archive:
        members = sorted((member for member in archive.getmembers() if member.isfile()), key=lambda x: x.name)
        for member in members:
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"unable to read source member {member.name}")
            payload = extracted.read()
            payloads[member.name] = payload
            suffix = Path(member.name).suffix.lower()
            if member.name in ACTIVE_RESULT_FIGURES:
                role = "active_result_figure_display_geometry"
            elif member.name in ACTIVE_METHOD_FIGURES:
                role = "active_method_figure"
            elif member.name.startswith("figs/"):
                role = "inactive_source_figure"
            elif suffix == ".tex":
                role = "paper_source"
            elif suffix == ".bib":
                role = "bibliography"
            elif suffix == ".bbl":
                role = "compiled_bibliography"
            elif suffix == ".sty":
                role = "latex_style"
            else:
                role = "other"
            rows.append(
                {
                    "source_member": member.name,
                    "bytes": str(len(payload)),
                    "sha256": bytes_sha256(payload),
                    "role": role,
                    "raw_experimental_array_or_table": "no",
                    "native_pipeline_code": "no",
                }
            )
    if len(rows) != EXPECTED_SOURCE_FILES:
        raise ValueError(f"official source file count changed: {len(rows)}")
    if bytes_sha256(payloads["main.tex"]) != EXPECTED_MAIN_TEX_SHA256:
        raise ValueError("official main.tex hash changed")
    appendix = payloads["tex/appendix/experiment.tex"]
    if bytes_sha256(appendix) != EXPECTED_APPENDIX_TEX_SHA256:
        raise ValueError("official appendix experiment TeX hash changed")
    return payloads, rows


def token_counter(text: str) -> Counter[str]:
    return Counter(re.findall(r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*", text.lower()))


def source_build_audit(official_pdf: Path, rebuilt_pdf: Path) -> dict[str, Any]:
    official_text, official_pages, _ = pdf_text(official_pdf)
    rebuilt_text, rebuilt_pages, _ = pdf_text(rebuilt_pdf)
    a = token_counter(official_text)
    b = token_counter(rebuilt_text)
    intersection = sum((a & b).values())
    union = sum((a | b).values())
    if official_pages != rebuilt_pages or official_pages != EXPECTED_PAGES:
        raise ValueError("source rebuild page count diverges")
    return {
        "source_document_rebuild_succeeded": True,
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "official_pdf_sha256": sha256(official_pdf),
        "rebuilt_pdf_sha256": sha256(rebuilt_pdf),
        "official_extracted_tokens": sum(a.values()),
        "rebuilt_extracted_tokens": sum(b.values()),
        "token_multiset_intersection": intersection,
        "token_multiset_union": union,
        "token_multiset_jaccard": intersection / union,
        "document_rebuild_credit": True,
        "experimental_reproduction_credit": False,
        "boundary": "the rebuild reuses released figure assets and does not recover their raw arrays or the native experiment",
    }


def _fixture() -> dict[str, pd.DataFrame]:
    index = pd.date_range("2023-01-01", periods=30)
    close = pd.DataFrame({"A": np.full(30, 10.0), "B": np.full(30, 20.0)}, index=index)
    open_ = close - 0.1
    high = close + 0.2
    low = close - 0.2
    high.iloc[20, 0] = 30.0
    volume = pd.DataFrame({"A": np.arange(1, 31) * 100.0, "B": np.arange(30, 0, -1) * 100.0}, index=index)
    return {
        "open": open_,
        "close": close,
        "high": high,
        "low": low,
        "pre_close": close.shift(1),
        "volume": volume,
    }


def published_code_rows(appendix_tex: str) -> list[dict[str, str]]:
    blocks = re.findall(r"\\begin\{lstlisting\}\n(.*?)\\end\{lstlisting\}", appendix_tex, re.S)
    if len(blocks) != 4:
        raise ValueError(f"published code-listing count changed: {len(blocks)}")
    classes = (
        "VolatilityBreakoutSignal",
        "ThreeSoldierSignal",
        "ImprovedThreeSoldierSignal",
        "ThreeSoldierSignalV3",
    )
    source_claims = (
        "example_alpha_not_identified_as_native_result",
        "mentor_rejected_version_1",
        "mentor_rejected_version_2",
        "mentor_passed_final_version_3",
    )
    rows: list[dict[str, str]] = []
    previous_module = sys.modules.get("idea_factor")
    module = types.ModuleType("idea_factor")

    class Factor:
        pass

    module.Factor = Factor
    sys.modules["idea_factor"] = module
    try:
        for index, (block, class_name, source_claim) in enumerate(zip(blocks, classes, source_claims), 1):
            compile_status = "compiled"
            compile_error = ""
            runtime_status = "not_run"
            runtime_error = ""
            runtime_nonzero_values = ""
            try:
                compile(block, f"published_listing_{index}", "exec")
            except Exception as exc:  # exact source is intentionally audited fail-closed
                compile_status = "compile_error"
                compile_error = f"{type(exc).__name__}: {exc}"
            if compile_status == "compiled":
                namespace: dict[str, Any] = {"pd": pd, "np": np, "Factor": Factor}
                try:
                    exec(block, namespace)
                    result = namespace[class_name]().calc(_fixture())
                    if not isinstance(result, pd.DataFrame):
                        raise TypeError(f"calc returned {type(result).__name__}, not DataFrame")
                    runtime_status = "executed_with_unreleased_factor_base_stub"
                    runtime_nonzero_values = str(int((result.fillna(0) != 0).sum().sum()))
                except Exception as exc:
                    runtime_status = "runtime_error_on_deterministic_fixture"
                    runtime_error = f"{type(exc).__name__}: {exc}"
            if index == 1:
                component_credit = "conditional_literal_formula_only"
                defects = (
                    "requires unreleased idea_factor.Factor; pre_close is defined as prior close but shifted again, "
                    "creating a two-bar close lag; no native data, agent, or portfolio rule"
                )
            elif index == 2:
                component_credit = "none"
                defects = "rolling open window is combined with the full close history, causing an index-alignment runtime error"
            elif index == 3:
                component_credit = "none"
                defects = "rolling open window is combined with full close/volume histories; vector conditions are also used as scalar if values"
            else:
                component_credit = "none"
                defects = (
                    "malformed data['open'[stock] expression, lowercase false, missing bracket, and stray LaTeX terminator; "
                    "the listing does not parse despite the printed mentor-pass verdict; non-increasing volume is assigned ratio 8"
                )
            rows.append(
                {
                    "listing_id": f"QA-CODE-{index:02d}",
                    "class_name": class_name,
                    "source_claim_status": source_claim,
                    "source_sha256": bytes_sha256(block.encode("utf-8")),
                    "compile_status": compile_status,
                    "compile_error": compile_error,
                    "runtime_status": runtime_status,
                    "runtime_error": runtime_error,
                    "runtime_nonzero_values_on_fixture": runtime_nonzero_values,
                    "material_defect_or_boundary": defects,
                    "component_credit": component_credit,
                    "native_agent_credit": "no",
                    "paper_result_credit": "no",
                }
            )
    finally:
        if previous_module is None:
            sys.modules.pop("idea_factor", None)
        else:
            sys.modules["idea_factor"] = previous_module
    return rows


def result_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    modes = ("inner_and_outer", "inner_only", "outer_only", "direct_neither")
    metrics = (
        ("entry_valid_ratio", "entry valid ratio"),
        ("information_coefficient", "IC"),
        ("return", "ret (units not stated)"),
        ("sharpe", "shp (formula and units not stated)"),
    )
    for panel, metric in metrics:
        for mode in modes:
            rows.append(
                {
                    "result_id": f"FIG3-{panel}-{mode}",
                    "figure": "Figure 3",
                    "source_asset": "figs/single_alpha_perf.pdf",
                    "panel": panel,
                    "metric": metric,
                    "display_object": "line_series",
                    "display_elements": "unknown_exact_point_count",
                    "raw_values_released": "no",
                    "exact_values_recovered": "no",
                    "native_reproduction_status": "not_reproduced_figure_geometry_only",
                    "paper_result_credit": "no",
                }
            )
    matrix_modes = (
        ("inner_and_outer", "with inner and outer loop"),
        ("outer_only", "without inner loop, only outer loop"),
        ("inner_only", "without outer loop, only inner loop"),
        ("neither", "no inner or outer loop"),
    )
    for mode, label in matrix_modes:
        rows.append(
            {
                "result_id": f"FIG4-{mode}",
                "figure": "Figure 4",
                "source_asset": "figs/relevance.pdf",
                "panel": mode,
                "metric": f"GPT-4 pairwise relevance win-rate matrix: {label}",
                "display_object": "10x10_heatmap",
                "display_elements": "100",
                "raw_values_released": "no",
                "exact_values_recovered": "no",
                "native_reproduction_status": "not_reproduced_figure_geometry_only",
                "paper_result_credit": "no",
            }
        )
    rows.append(
        {
            "result_id": "FIG5-XGBOOST-MSE",
            "figure": "Figure 5",
            "source_asset": "figs/model.png",
            "panel": "single_panel",
            "metric": "XGBoost MSE as accumulated alpha count increases",
            "display_object": "line_series",
            "display_elements": "unknown_exact_point_count",
            "raw_values_released": "no",
            "exact_values_recovered": "no",
            "native_reproduction_status": "not_reproduced_raster_geometry_only",
            "paper_result_credit": "no",
        }
    )
    return rows


def prompt_rows() -> list[dict[str, str]]:
    recovered = (
        "I observed that three consecutive candlesticks each closing higher than the preceding one. "
        "This pattern suggests strong buying pressure in the market. Please implement a trading signal based on this observation"
    )
    definitions = (
        ("QA-PROMPT-01", "example trading-idea request", "recovered", recovered),
        ("QA-PROMPT-02", "writer/agent system prompt", "missing", "described as specifically designed but not printed"),
        ("QA-PROMPT-03", "judge/mentor system prompt", "missing", "described as specifically designed but not printed"),
        ("QA-PROMPT-04", "knowledge-base retrieval prompt/query template", "missing", "retrieve() is pseudocode only"),
        ("QA-PROMPT-05", "outer-loop trading-idea generator prompt", "missing", "another LLM is named but prompt and distribution are absent"),
        ("QA-PROMPT-06", "GPT-4 pairwise relevance judge prompt", "missing", "comparison task is described but the request is absent"),
        ("QA-PROMPT-07", "knowledge-base update/sanity-check rule", "missing", "prose says rules exist but does not state them"),
        ("QA-PROMPT-08", "XGBoost feature/target construction request", "missing", "no executable training specification"),
        ("QA-PROMPT-09", "runtime messages and tool transcripts", "missing", "only selected appendix outputs/reviews are printed"),
    )
    return [
        {
            "prompt_id": identifier,
            "role": role,
            "recovery_status": status,
            "text_or_evidence": evidence,
            "immutable_request_metadata_released": "no",
            "native_runtime_message_recovered": "no",
            "exact_replay_credit": "no",
        }
        for identifier, role, status, evidence in definitions
    ]


def issue_rows() -> list[dict[str, str]]:
    definitions = (
        ("QA-INT-001", "blocking", "Algorithm 1 computes score but terminates on undefined r", "prevents exact control-flow reconstruction"),
        ("QA-INT-002", "major", "Algorithm 2 repeats one fixed problem p while the experiment samples a new trading idea at each outer iteration", "outer-loop task sequence is ambiguous"),
        ("QA-INT-003", "blocking", "ThreeSoldierSignal v1 combines a rolling open window with the full close series", "published v1 raises an index-alignment error on ordinary aligned data"),
        ("QA-INT-004", "blocking", "ImprovedThreeSoldierSignal v2 combines rolling and full-history series and uses vector booleans in if", "published v2 raises before producing a signal"),
        ("QA-INT-005", "blocking", "mentor-passed ThreeSoldierSignalV3 is syntactically invalid", "the source-approved final listing cannot be parsed"),
        ("QA-INT-006", "major", "V3 assigns volume_ratio=8 when volume is not increasing", "the stated volume confirmation can increase and saturate the signal when the condition fails"),
        ("QA-INT-007", "major", "VolatilityBreakoutSignal shifts pre_close even though pre_close is defined as the previous day's close", "literal code uses a two-bar close lag rather than standard true range"),
        ("QA-INT-008", "major", "base-data prose spells pre-close while code requests pre_close", "the unreleased framework's key normalization is required"),
        ("QA-INT-009", "blocking", "results say significant differences are not apparent but claim the blue trend proves effectiveness in all metrics", "no statistical test or uncertainty measure resolves the inference"),
        ("QA-INT-010", "blocking", "Theorem 4.6 combines separately sublinear K and T statements into sublinear KT without rates or a complete transfer proof", "the claimed end-to-end regret guarantee is not independently reconstructible"),
        ("QA-INT-011", "major", "the source contains unused captions naming AlphaAgent while the paper system is QuantAgent", "source lineage/naming is ambiguous but inactive in the PDF"),
        ("QA-INT-012", "major", "the same 2023 market feedback appears to build the knowledge base and support performance plots without a disclosed holdout split", "out-of-sample status and adaptive reuse cannot be determined"),
    )
    return [
        {
            "issue_id": identifier,
            "severity": severity,
            "issue": issue,
            "replication_effect": effect,
            "native_result_credit": "no",
        }
        for identifier, severity, issue, effect in definitions
    ]


def claim_rows() -> list[dict[str, str]]:
    definitions = (
        ("QA-CLAIM-01", "agent progressively approximates optimal behavior with provable efficiency", "theory sketch and transferred assumptions only"),
        ("QA-CLAIM-02", "QuantAgent uncovers viable financial signals", "no released signal census, code, or return path"),
        ("QA-CLAIM-03", "QuantAgent enhances financial-forecast accuracy", "Figure 5 geometry only; split and arrays absent"),
        ("QA-CLAIM-04", "self-improvement strengthens single-alpha metrics", "Figure 3 geometry only; prose says significance is not apparent"),
        ("QA-CLAIM-05", "inner and outer loops improve idea relevance", "four Figure 4 heatmaps without arrays, prompt, or judge requests"),
        ("QA-CLAIM-06", "knowledge base is a reliable XGBoost feature source", "model configuration, target, split, and predictions absent"),
        ("QA-CLAIM-07", "final Three Soldiers implementation is sound", "the printed mentor-passed code has a SyntaxError"),
        ("QA-CLAIM-08", "signals generate satisfactory investment returns", "Sharpe construction and portfolios are unspecified"),
        ("QA-CLAIM-09", "the framework requires minimal human intervention", "selection, prompt construction, sanity checks, and manual curation are not logged"),
    )
    return [
        {
            "claim_id": identifier,
            "paper_claim": claim,
            "released_support": support,
            "exactly_reproduced": "no",
            "paper_result_credit": "no",
        }
        for identifier, claim, support in definitions
    ]


def method_rows() -> list[dict[str, str]]:
    # Each row is an exact-replication requirement, not a quality score.
    definitions = (
        ("paper", "arXiv version", "specified", "none", "v1 only, submitted 2024-02-06"),
        ("paper", "authoritative TeX source", "specified", "none", "44-file official source archive"),
        ("paper", "document rebuild", "specified", "none", "15-page rebuild"),
        ("artifact", "author-linked repository", "missing", "blocking", "no repository listed or found"),
        ("artifact", "native QuantAgent implementation", "missing", "blocking", "not released"),
        ("artifact", "idea_factor framework", "missing", "blocking", "named as internally developed; no package snapshot"),
        ("artifact", "license for experiment code/data", "missing", "major", "not released"),
        ("data", "market", "specified", "none", "Chinese A-share market"),
        ("data", "universe size", "specified", "none", "500 stocks"),
        ("data", "universe constituents", "missing", "blocking", "identities and selection date absent"),
        ("data", "calendar period", "partial", "major", "year 2023 only"),
        ("data", "data vendor and snapshot", "missing", "blocking", "absent"),
        ("data", "daily base fields", "specified", "none", "12 OHLC/volume/share/trading fields listed"),
        ("data", "price adjustment convention", "missing", "blocking", "absent"),
        ("data", "suspension and limit-up/down handling", "missing", "blocking", "absent"),
        ("data", "delisting and survivorship handling", "missing", "blocking", "absent"),
        ("data", "missing-value treatment", "missing", "blocking", "outside selected snippets, absent"),
        ("data", "future-return horizon", "missing", "blocking", "IC says future returns but horizon is absent"),
        ("data", "train/validation/test split", "missing", "blocking", "absent"),
        ("data", "adaptive reuse boundary", "missing", "blocking", "same-period KB construction and evaluation not separated"),
        ("model", "foundation model name", "specified", "none", "gpt-4-0125-preview"),
        ("model", "API provider endpoint/snapshot", "partial", "major", "model alias stated; immutable request metadata absent"),
        ("model", "temperature", "missing", "blocking", "absent"),
        ("model", "sampling seed", "missing", "blocking", "absent"),
        ("model", "token limits", "missing", "major", "absent"),
        ("model", "writer and judge model assignment", "partial", "blocking", "both are LLMs; exact assignments absent"),
        ("model", "outer trading-idea generator model", "missing", "blocking", "only 'another LLM' is stated"),
        ("prompt", "writer prompt", "missing", "blocking", "absent"),
        ("prompt", "judge prompt", "missing", "blocking", "absent"),
        ("prompt", "trading-idea generator prompt", "missing", "blocking", "absent"),
        ("prompt", "pairwise relevance prompt", "missing", "blocking", "absent"),
        ("prompt", "example Three Soldiers request", "specified", "none", "printed verbatim"),
        ("inner_loop", "algorithm skeleton", "specified", "none", "Algorithm 1"),
        ("inner_loop", "termination variable", "conflict", "blocking", "score computed; undefined r tested"),
        ("inner_loop", "reward threshold beta", "missing", "blocking", "symbol only"),
        ("inner_loop", "iteration limit T", "missing", "blocking", "symbol only"),
        ("inner_loop", "context serialization", "missing", "blocking", "set-union pseudocode only"),
        ("inner_loop", "retrieval algorithm", "missing", "blocking", "retrieve() pseudocode only"),
        ("inner_loop", "embedding model", "missing", "blocking", "embeddings mentioned but not identified"),
        ("inner_loop", "retrieval index and top-k", "missing", "blocking", "absent"),
        ("inner_loop", "judge score scale", "missing", "blocking", "absent"),
        ("outer_loop", "algorithm skeleton", "specified", "none", "Algorithm 2"),
        ("outer_loop", "number of iterations K", "missing", "blocking", "symbol only"),
        ("outer_loop", "problem sequence", "conflict", "blocking", "fixed p in algorithm versus sampled ideas in experiment"),
        ("outer_loop", "environment feedback metrics", "partial", "major", "scores/reviews described, exact vector absent"),
        ("outer_loop", "knowledge-base update rule", "missing", "blocking", "sanity checks claimed but rules absent"),
        ("outer_loop", "knowledge-base initial contents", "partial", "major", "Algorithm 2 initializes empty; experimental initialization unclear"),
        ("outer_loop", "knowledge-base records", "partial", "major", "outputs, scores, feedback described; snapshot absent"),
        ("signal", "Factor interface", "partial", "major", "interface prose and one example; base class absent"),
        ("signal", "VolatilityBreakout code", "specified", "major", "literal listing executes with stub but uses two-bar close lag"),
        ("signal", "Three Soldiers v1 code", "specified", "blocking", "listing raises index-alignment error"),
        ("signal", "Three Soldiers v2 code", "specified", "blocking", "listing raises index-alignment error"),
        ("signal", "Three Soldiers v3 code", "conflict", "blocking", "mentor-pass prose accompanies invalid Python"),
        ("signal", "generated signal library", "missing", "blocking", "no generated programs or values"),
        ("signal", "signal count", "partial", "major", "figures imply many signals but exact census is absent"),
        ("signal", "duplicate filtering", "partial", "major", "valid/unique entities mentioned; algorithm absent"),
        ("metric", "IC definition", "specified", "none", "daily cross-sectional Pearson correlation averaged over time"),
        ("metric", "IC uncertainty/significance", "missing", "major", "absent"),
        ("metric", "return definition", "missing", "blocking", "Figure 3 ret units and portfolio construction absent"),
        ("metric", "Sharpe definition", "missing", "blocking", "frequency, risk-free rate, annualization absent"),
        ("metric", "transaction costs", "missing", "blocking", "absent"),
        ("metric", "portfolio weights and rebalance", "missing", "blocking", "absent"),
        ("metric", "entry valid ratio definition", "partial", "major", "valid/unique prose but exact formula absent"),
        ("metric", "relevance win-rate construction", "partial", "major", "pairwise GPT-4 comparison described; requests/order absent"),
        ("xgboost", "model family", "specified", "none", "XGBoost regression trees"),
        ("xgboost", "version and hyperparameters", "missing", "blocking", "absent"),
        ("xgboost", "feature matrix", "partial", "blocking", "KB used as features; exact matrix absent"),
        ("xgboost", "target and forecast horizon", "missing", "blocking", "absent"),
        ("xgboost", "fit/evaluation split", "missing", "blocking", "absent"),
        ("results", "Figure 3 raw arrays", "missing", "blocking", "16 line series are figure geometry only"),
        ("results", "Figure 4 raw matrices", "missing", "blocking", "400 heatmap cells are figure geometry only"),
        ("results", "Figure 5 raw arrays", "missing", "blocking", "raster line only"),
        ("results", "numeric result tables", "missing", "major", "none in paper"),
        ("results", "uncertainty intervals", "missing", "major", "absent"),
        ("results", "statistical tests", "missing", "major", "absent"),
        ("results", "random seeds and repetitions", "missing", "blocking", "absent"),
        ("theory", "inner-loop proof", "partial", "major", "lemma delegates details to other papers"),
        ("theory", "outer-loop proof", "partial", "major", "assumes PEVI and delegates details"),
        ("theory", "end-to-end sublinear-KT proof", "conflict", "blocking", "rates/transfer conditions are insufficiently stated"),
        ("runtime", "Python version", "missing", "major", "absent"),
        ("runtime", "package lock", "missing", "blocking", "absent"),
        ("runtime", "hardware", "missing", "major", "absent"),
        ("runtime", "API logs and cost", "missing", "major", "absent"),
        ("local", "two legacy JKP mappings", "partial", "major", "M0 narrative translations, not paper signals"),
        ("local", "literal ATR14 component", "partial", "major", "C-conditional monthly U.S. adaptation with researcher portfolio"),
        ("local", "native result relation", "specified", "none", "all local paths explicitly receive zero paper-result credit"),
    )
    return [
        {
            "category": category,
            "dimension": dimension,
            "assessment": assessment,
            "severity": severity,
            "paper_or_source_evidence": evidence,
            "exact_native_reconstruction": "yes" if assessment == "specified" and severity == "none" else "no",
        }
        for category, dimension, assessment, severity, evidence in definitions
    ]


def local_mapping_rows() -> list[dict[str, str]]:
    return [
        {
            "candidate_id": "quantagent_three_soldiers_trend",
            "local_tier": "M0_narrative_translation",
            "source_anchor": "appendix Three Soldiers idea and invalid listings",
            "preserved": "broad upward-price and volume motif",
            "changed_or_added": "monthly JKP returns, turnover and volatility ranks; long-short deciles; U.S. universe",
            "paper_result_credit": "no",
        },
        {
            "candidate_id": "quantagent_volatility_breakout",
            "local_tier": "M0_narrative_translation",
            "source_anchor": "appendix VolatilityBreakoutSignal",
            "preserved": "broad breakout/volatility motif",
            "changed_or_added": "monthly JKP rmax/return/volatility ranks; long-short deciles; U.S. universe",
            "paper_result_credit": "no",
        },
        {
            "candidate_id": "quantagent_atr14_breakout_literal",
            "local_tier": "C-conditional",
            "source_anchor": "appendix VolatilityBreakoutSignal formula",
            "preserved": "literal two-bar-lag true range, ATR14, prior-high-plus-1.5-ATR barrier and nonnegative normalization",
            "changed_or_added": "daily A-shares become monthly U.S. top-1000; researcher positive top-10 long-only rule; self-improving agent omitted",
            "paper_result_credit": "no",
        },
    ]


def github_rows(directory: Path) -> list[dict[str, str]]:
    paths = sorted(directory.glob("*.json"))
    if len(paths) != len(GITHUB_QUERIES):
        raise ValueError(f"expected {len(GITHUB_QUERIES)} GitHub search snapshots, found {len(paths)}")
    rows = []
    for query, path in zip(GITHUB_QUERIES, paths):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "query": query,
                "snapshot_file": path.name,
                "snapshot_sha256": sha256(path),
                "total_count": str(data["total_count"]),
                "incomplete_results": str(bool(data["incomplete_results"])).lower(),
                "repositories": "|".join(sorted(item["full_name"] for item in data.get("items", []))),
                "author_linked_repository_found": "no",
            }
        )
    return rows


def name_collision_rows() -> list[dict[str, str]]:
    return [
        {
            "repository": "Y-Research-SBU/QuantAgent",
            "paper": "QuantAgent: Price-Driven Multi-Agent LLMs for High-Frequency Trading (arXiv:2509.09995)",
            "relationship": "distinct later same-name system",
            "author_overlap": "none",
            "task_difference": "2025 price-driven multi-agent HFT rather than 2024 self-improving A-share alpha mining",
            "native_credit_for_2402_03755": "no",
        }
    ]


def readme(manifest: dict[str, Any]) -> str:
    return f"""# QuantAgent (self-improving LLM) paper/source replication audit

This package audits arXiv:2402.03755v1, its 15-page PDF, the official TeX
archive, all four published Python listings, and the public repository-search
surface. It is fail-closed: rebuilding a document or executing one isolated
formula with a stub is not a reconstruction of QuantAgent or its results.

## Verdict

- **Native QuantAgent results reproduced: 0/{manifest['plotted_line_series']} plotted line series and 0/{manifest['heatmap_cells']} heatmap cells.**
- **Document fidelity is high:** the official source rebuilds to 15 pages at
  {manifest['source_document_token_jaccard']:.4%} extracted-token multiset
  Jaccard against the arXiv PDF.
- The archive releases no native pipeline, idea-factor framework, prompts,
  500-stock membership, 2023 market snapshot, generated signal library,
  knowledge base, model predictions, result arrays, or immutable GPT requests.
- Of four published Python listings, three compile. Only the standalone
  VolatilityBreakout formula executes after stubbing the unreleased Factor base;
  both rejected Three Soldiers versions raise, and the mentor-passed V3 does
  not parse.
- Eight complete GitHub repository searches found no candidate repository. The
  popular Y-Research-SBU/QuantAgent repository belongs to a distinct 2025 HFT
  paper with different authors, data, task, and architecture.
- The two legacy monthly JKP candidates remain M0 narrative translations. A
  separate literal ATR14 component remains C-conditional because cadence,
  universe, and portfolio construction are researcher adaptations.

## Material blockers and conflicts

- Algorithm 1 computes `score` but tests undefined `r`; the outer-loop
  pseudocode fixes one problem while the experiment says ideas are resampled.
- The published v1/v2 Three Soldiers code mixes rolling windows with full
  histories. The printed mentor-passed V3 has malformed indexing, lowercase
  `false`, a missing bracket, and a stray LaTeX terminator.
- The breakout code shifts an already previous-close field, yielding a two-bar
  lag. V3 assigns a large positive volume ratio when volume is *not* increasing.
- The paper says significant performance differences are not apparent, then
  treats the blue curves as evidence of effectiveness without uncertainty or
  tests.
- The data split, future-return horizon, IC arrays, portfolio/Sharpe mechanics,
  XGBoost specification, prompts, KB/retrieval state, seeds, and package/runtime
  snapshot are absent.
- The end-to-end sublinear-in-KT theorem delegates key results and does not
  state rates or transfer conditions sufficient to reconstruct its conclusion.

## Files

- `source_file_inventory.csv`: all 44 source members and hashes.
- `source_build_audit.json`: 15-page document rebuild/text conformance.
- `published_code_conformance.csv`: exact compile/runtime status of four listings.
- `displayed_result_conformance.csv`: 17 plotted series and four 10x10 matrices.
- `prompt_inventory.csv`: one printed request and eight missing runtime prompts.
- `method_specification_audit.csv`: method-level replication requirements.
- `paper_internal_consistency_audit.csv`: code, algorithm, empirical, and theory conflicts.
- `claim_audit.csv`: fail-closed support status for central claims.
- `local_mapping_conformance.csv`: M0 and C-conditional local evidence boundaries.
- `source_search_inventory.csv` and `same_name_nonmatch.csv`: source-search provenance.
- `source_provenance.json`, `native_execution.json`, and `manifest.json`: machine-readable boundaries.
"""


def build(
    paper_pdf: Path,
    official_page: Path,
    source_tar: Path,
    source_build_pdf: Path,
    github_search_dir: Path,
    output: Path,
) -> dict[str, Any]:
    if sha256(paper_pdf) != EXPECTED_PDF_SHA256:
        raise ValueError("official QuantAgent PDF hash changed")
    if sha256(official_page) != EXPECTED_PAGE_SHA256:
        raise ValueError("official QuantAgent arXiv page hash changed")
    if sha256(source_tar) != EXPECTED_SOURCE_SHA256:
        raise ValueError("official QuantAgent source archive hash changed")

    text, pages, _ = pdf_text(paper_pdf)
    validate_pdf(text, pages)
    payloads, source_files = read_source(source_tar)
    source_build = source_build_audit(paper_pdf, source_build_pdf)
    code = published_code_rows(payloads["tex/appendix/experiment.tex"].decode("utf-8"))
    results = result_rows()
    prompts = prompt_rows()
    issues = issue_rows()
    claims = claim_rows()
    methods = method_rows()
    mappings = local_mapping_rows()
    searches = github_rows(github_search_dir)
    collisions = name_collision_rows()

    line_series = sum(row["display_object"] == "line_series" for row in results)
    heatmap_cells = sum(int(row["display_elements"]) for row in results if row["display_object"] == "10x10_heatmap")
    if line_series != 17 or heatmap_cells != 400:
        raise AssertionError("QuantAgent result-display census changed")

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "source_file_inventory.csv", source_files, list(source_files[0]))
    write_csv(output / "published_code_conformance.csv", code, list(code[0]))
    write_csv(output / "displayed_result_conformance.csv", results, list(results[0]))
    write_csv(output / "prompt_inventory.csv", prompts, list(prompts[0]))
    write_csv(output / "paper_internal_consistency_audit.csv", issues, list(issues[0]))
    write_csv(output / "claim_audit.csv", claims, list(claims[0]))
    write_csv(output / "method_specification_audit.csv", methods, list(methods[0]))
    write_csv(output / "local_mapping_conformance.csv", mappings, list(mappings[0]))
    write_csv(output / "source_search_inventory.csv", searches, list(searches[0]))
    write_csv(output / "same_name_nonmatch.csv", collisions, list(collisions[0]))
    write_json(output / "source_build_audit.json", source_build)

    source_provenance = {
        "official_record": PAPER_URL,
        "official_record_sha256": sha256(official_page),
        "official_pdf": PDF_URL,
        "official_pdf_sha256": sha256(paper_pdf),
        "official_source": SOURCE_URL,
        "official_source_sha256": sha256(source_tar),
        "official_main_tex_sha256": EXPECTED_MAIN_TEX_SHA256,
        "official_appendix_tex_sha256": EXPECTED_APPENDIX_TEX_SHA256,
        "doi": DOI,
        "version": "v1 only",
        "pages": pages,
        "source_files": len(source_files),
        "author_linked_code_or_data_found": False,
        "github_repository_searches": searches,
        "same_name_nonmatch": collisions,
    }
    write_json(output / "source_provenance.json", source_provenance)

    native = {
        "attempted": False,
        "reason": "no_author_linked_pipeline_data_prompts_knowledge_base_generated_signals_model_predictions_or_result_arrays",
        "paper_result_credit": False,
        "source_document_rebuild_succeeded": True,
        "published_python_listings": len(code),
        "published_python_listings_compiled": sum(row["compile_status"] == "compiled" for row in code),
        "published_python_listings_executed_with_stub": sum(row["runtime_status"] == "executed_with_unreleased_factor_base_stub" for row in code),
        "plotted_line_series": line_series,
        "plotted_line_series_reproduced": 0,
        "heatmap_cells": heatmap_cells,
        "heatmap_cells_reproduced": 0,
        "local_proxy_status": "two_M0_narrative_translations_plus_one_C_conditional_literal_component",
        "local_proxy_boundary": "all local portfolio rules, U.S. universe choices, monthly cadence, weights, and return streams are non-native and receive zero paper-result credit",
    }
    write_json(output / "native_execution.json", native)

    method_counts = dict(sorted(Counter(row["assessment"] for row in methods).items()))
    severity_counts = dict(sorted(Counter(row["severity"] for row in methods).items()))
    manifest = {
        "paper": "QuantAgent: Seeking Holy Grail in Trading by Self-Improving Large Language Model",
        "system_id": "SYS-QUANT-AGENT-SELF-IMPROVING",
        "canonical_work_id": "CensusArxiv240203755",
        "audit_route": "paper_only_underspecified_with_official_source_and_conditional_formula_component",
        "overall_fidelity": "source_document_rebuilt_but_zero_of_17_line_series_and_zero_of_400_heatmap_cells_reproduced_no_native_agent_pipeline",
        "paper_result_credit": False,
        "official_pdf_pages": pages,
        "official_source_files": len(source_files),
        "source_document_rebuild_succeeded": True,
        "source_document_token_jaccard": source_build["token_multiset_jaccard"],
        "published_python_listings": len(code),
        "published_python_listings_compiled": sum(row["compile_status"] == "compiled" for row in code),
        "published_python_listings_executed_with_stub": sum(row["runtime_status"] == "executed_with_unreleased_factor_base_stub" for row in code),
        "mentor_passed_listing_compiles": False,
        "plotted_line_series": line_series,
        "plotted_line_series_reproduced": 0,
        "heatmap_cells": heatmap_cells,
        "heatmap_cells_reproduced": 0,
        "prompt_fragments_recovered": sum(row["recovery_status"] == "recovered" for row in prompts),
        "claims_audited": len(claims),
        "internal_consistency_issues": len(issues),
        "blocking_internal_consistency_issues": sum(row["severity"] == "blocking" for row in issues),
        "method_dimensions": len(methods),
        "method_assessment_counts": method_counts,
        "method_severity_counts": severity_counts,
        "github_repository_searches": len(searches),
        "github_repository_hits": sum(int(row["total_count"]) for row in searches),
        "author_linked_code_found": False,
        "source_provenance": "source_provenance.json",
        "source_build_audit": "source_build_audit.json",
        "native_execution": "native_execution.json",
    }
    write_json(output / "manifest.json", manifest)
    (output / "README.md").write_text(readme(manifest), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-pdf", type=Path, required=True)
    parser.add_argument("--official-page", type=Path, required=True)
    parser.add_argument("--source-tar", type=Path, required=True)
    parser.add_argument("--source-build-pdf", type=Path, required=True)
    parser.add_argument("--github-search-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(
        args.paper_pdf.resolve(),
        args.official_page.resolve(),
        args.source_tar.resolve(),
        args.source_build_pdf.resolve(),
        args.github_search_dir.resolve(),
        args.output_dir.resolve(),
    )
    print(compact_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
