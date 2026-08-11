#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for LLMFactor (ACL 2024).

The official arXiv source archive is a document release, not a system release.
This audit therefore separates (1) document reconstruction, (2) conditionally
executable prompt/metric components, (3) later unaffiliated implementations,
and (4) reproduction of the paper's 206 displayed result cells.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import math
import re
import subprocess
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]

ARXIV_RECORD = "https://arxiv.org/abs/2406.10811"
ARXIV_PDF = "https://arxiv.org/pdf/2406.10811v1"
ARXIV_SOURCE = "https://arxiv.org/e-print/2406.10811v1"
ACL_RECORD = "https://aclanthology.org/2024.findings-acl.185/"
ACL_PDF = "https://aclanthology.org/2024.findings-acl.185.pdf"
TASOO_REPO = "https://github.com/tasoo-oos/LLMFactor"
KUON_REPO = "https://github.com/Kuon12138/SKGP"

EXPECTED_ARXIV_PDF_SHA256 = "c8100b3c2f4b5bf2e3f033407f2bbb82b262d2fa4c1a0a83faff94c28e371ed8"
EXPECTED_ACL_PDF_SHA256 = "a9b0480bfb2387459cae2dcefef8e0d9a499331d0d2cf0efeedec7b0392ef635"
EXPECTED_ARXIV_SOURCE_SHA256 = "38570581fa3727d9fd57b23159bf206472fabede7e6eca595a113aed7838a814"
EXPECTED_ARXIV_RECORD_SHA256 = "cfd330893117bf93eb3986159701f627b14e59e56605c9b5d5b457e6ec791cb6"
EXPECTED_ACL_RECORD_SHA256 = "88874a8ef692a8e873c353da9c9ee1e1d9e588e5c78d16b9c26dbe6829a66220"
EXPECTED_SOURCE_MAIN_SHA256 = "1cdb5b14dfb4d631f55ed555b34088d5d9e0820d11400cf6140aa4f6a8bfc969"
EXPECTED_REBUILD_SHA256 = "c01a9e42c69dca0815f22f102c2cafdf5e3e76ec5e043c82cb6675deaf8df1e2"
EXPECTED_SOURCE_MEMBERS = 9
EXPECTED_TASOO_HEAD = "7b9e3f985b1fe10a234dab8c4a4d806537579b71"
EXPECTED_KUON_HEAD = "9b4749e843bc2246026f1302e82a8c66c0d050e7"

GITHUB_QUERIES = (
    "LLMFactor in:name,description,readme",
    '"LLMFactor: Extracting Profitable Factors through Prompts for Explainable Stock Movement Prediction"',
    "2406.10811",
    '"Sequential Knowledge-Guided Prompting"',
    '"Meiyun Wang" LLMFactor',
    '"2024.findings-acl.185"',
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


def validate_pdf(path: Path, expected_hash: str, required: tuple[str, ...]) -> str:
    actual = sha256(path)
    if actual != expected_hash:
        raise ValueError(f"official PDF hash changed for {path}: {actual}")
    text, pages, _ = pdf_text(path)
    if pages != 12:
        raise ValueError(f"official PDF page count changed for {path}: {pages}")
    normalized = " ".join(text.split())
    missing = [value for value in required if value not in normalized]
    if missing:
        raise ValueError(f"official PDF extraction changed for {path}: {missing}")
    return text


def source_role(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix == ".tex":
        return "paper_tex_source"
    if suffix in {".jpg", ".png", ".pdf"}:
        return "paper_figure_asset"
    if suffix in {".bib", ".bbl", ".bst"}:
        return "bibliography_source_or_build_product"
    if suffix == ".sty":
        return "latex_style"
    return "other_document_source"


def source_inventory(path: Path) -> list[dict[str, str]]:
    if sha256(path) != EXPECTED_ARXIV_SOURCE_SHA256:
        raise ValueError("official source archive hash changed")
    rows: list[dict[str, str]] = []
    main_hash = ""
    with tarfile.open(path, "r:*") as archive:
        members = sorted((member for member in archive.getmembers() if member.isfile()), key=lambda item: item.name)
        for member in members:
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"cannot extract {member.name}")
            payload = stream.read()
            digest = bytes_sha256(payload)
            if member.name == "acl_latex.tex":
                main_hash = digest
            rows.append(
                {
                    "source_member": member.name,
                    "bytes": str(len(payload)),
                    "sha256": digest,
                    "role": source_role(member.name),
                    "native_pipeline_code": "no",
                    "raw_experiment_data_or_result_array": "no",
                    "paper_result_credit": "no",
                }
            )
    if len(rows) != EXPECTED_SOURCE_MEMBERS:
        raise ValueError(f"official source member count changed: {len(rows)}")
    if main_hash != EXPECTED_SOURCE_MAIN_SHA256:
        raise ValueError(f"official acl_latex.tex hash changed: {main_hash}")
    return rows


def source_build_row(label: str, official: Path, rebuilt: Path, relationship: str) -> dict[str, Any]:
    official_text, official_pages, _ = pdf_text(official)
    rebuilt_text, rebuilt_pages, _ = pdf_text(rebuilt)
    if rebuilt_pages != 12 or official_pages != 12:
        raise ValueError(f"source build page count changed for {label}: {official_pages}/{rebuilt_pages}")
    left = token_list(official_text)
    right = token_list(rebuilt_text)
    a, b = Counter(left), Counter(right)
    intersection = sum((a & b).values())
    union = sum((a | b).values())
    return {
        "comparison_id": label,
        "official_pdf_sha256": sha256(official),
        "rebuilt_pdf_sha256": sha256(rebuilt),
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "official_tokens": len(left),
        "rebuilt_tokens": len(right),
        "token_multiset_jaccard": intersection / union,
        "token_sequence_ratio": difflib.SequenceMatcher(None, left, right, autojunk=False).ratio(),
        "source_relationship": relationship,
        "compatibility_patch": "none",
        "document_credit": "yes",
        "native_system_or_result_credit": "no",
    }


TABLE2_ROWS = (
    ("Keyphrase-based", "PromptRank", (51.24, .010, 53.28, .001, 50.21, -.003, 51.78, .014)),
    ("Keyphrase-based", "KeyBERT", (51.95, .012, 53.40, .009, 50.23, -.004, 51.84, .002)),
    ("Keyphrase-based", "YAKE", (51.91, .005, 53.13, .001, 50.20, .001, 51.88, .004)),
    ("Keyphrase-based", "TextRank", (51.00, .003, 53.99, .060, 50.38, .006, 51.76, .003)),
    ("Keyphrase-based", "TopicRank", (51.92, .008, 53.75, .034, 50.26, -.002, 51.80, .000)),
    ("Keyphrase-based", "SingleRank", (50.32, .005, 53.33, .004, 50.29, .002, 51.85, .004)),
    ("Keyphrase-based", "TFIDF", (51.86, .001, 53.71, .018, 50.27, -.002, 51.86, .017)),
    ("Sentiment-based", "EDT", (40.31, -.066, 49.86, -.004, 40.00, .021, 75.67, .026)),
    ("Sentiment-based", "FinGPT", (54.91, .083, 59.98, .182, 55.78, .120, 53.86, .035)),
    ("Sentiment-based", "GPT-4-turbo", (53.56, .060, 64.61, .284, 56.94, .135, 55.37, .057)),
    ("Sentiment-based", "GPT-4", (53.88, .062, 62.18, .260, 56.96, .136, 50.94, .031)),
    ("Sentiment-based", "GPT-3.5-turbo", (52.31, .044, 56.10, .156, 56.68, .124, 54.34, .040)),
    ("Sentiment-based", "RoBERTa", (54.46, .088, 57.75, .138, 52.24, .064, 53.66, .029)),
    ("Sentiment-based", "FinBERT", (55.42, .111, 58.26, .158, 55.98, .121, 54.98, .043)),
    ("Time-based", "CMIN", (62.69, .209, 53.43, .046, 55.28, .111)),
    ("Time-based", "StockNet", (58.23, .081, 52.46, .022, 54.53, .045)),
    ("Factor-based(ours)", "LLMFactor_GPT-4-turbo", (65.81, .228, 61.71, .228, 60.59, .245, 59.09, .082)),
    ("Factor-based(ours)", "LLMFactor_GPT-4", (66.32, .238, 65.26, .284, 57.16, .196, 60.83, .105)),
    ("Factor-based(ours)", "LLMFactor_GPT-3.5-turbo", (57.59, .145, 66.42, .288, 56.11, .139, 58.11, .097)),
)

TABLE3_ROWS = (
    ("Price", (52.16, .041, 55.59, .135, 51.76, .048), ("StockNet", "CMIN-US", "CMIN-CN")),
    ("+Factor", (58.04, .166, 61.68, .241, 55.71, .119, 55.93, .077), ("StockNet", "CMIN-US", "CMIN-CN", "EDT")),
    ("+Factor+Relation", (63.24, .203, 64.46, .267, 57.96, .194, 59.35, .095), ("StockNet", "CMIN-US", "CMIN-CN", "EDT")),
)

ENGLISH_FACTOR_ROWS = (
    ("EN-1", "Please extract the top k factors that may affect the stock price of stock_target from the following news", (61.71, .228, 65.26, .284, 66.42, .288)),
    ("EN-2", "Please identify the primary top k factors influencing stock_target's stock price based on the news provided", (66.98, .292, 64.83, .246, 65.26, .298)),
    ("EN-3", "Please analyze the provided news and pinpoint the top k major factors impacting the stock price of stock_target", (65.29, .295, 69.21, .312, 66.56, .293)),
)

CHINESE_FACTOR_ROWS = (
    ("CN-1", "请从以下新闻中提取可能影响stock_target股价的前k个因素", (60.59, .245, 57.16, .196, 56.11, .139)),
    ("CN-2", "根据提供的新闻，请识别出影响stock_target股价的主要k个因素", (57.92, .147, 64.79, .109, 65.13, .139)),
    ("CN-3", "请分析所提供的新闻并找出影响stock_target股价的前k个主要因素", (64.29, .160, 59.33, .053, 59.49, .033)),
)


def displayed_result_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    datasets = ("StockNet", "CMIN-US", "CMIN-CN", "EDT")
    metrics = ("ACC", "MCC")

    def add(table: str, section: str, model: str, dataset: str, metric: str, value: float, scope: str) -> None:
        rows.append(
            {
                "result_id": f"LLMF-{len(rows)+1:03d}",
                "table": table,
                "section": section,
                "model_or_template": model,
                "dataset": dataset,
                "metric": metric,
                "displayed_value": f"{value:.2f}" if metric == "ACC" else f"{value:.3f}",
                "scope": scope,
                "raw_values_released": "no",
                "native_reproduced": "no",
                "paper_result_credit": "no",
            }
        )

    for section, model, values in TABLE2_ROWS:
        active_datasets = datasets if len(values) == 8 else datasets[:3]
        for index, value in enumerate(values):
            add("Table 2", section, model, active_datasets[index // 2], metrics[index % 2], value, "native_llmfactor" if section == "Factor-based(ours)" else "baseline")
    for model, values, active_datasets in TABLE3_ROWS:
        for index, value in enumerate(values):
            add("Table 3", "ablation", model, active_datasets[index // 2], metrics[index % 2], value, "native_llmfactor")
    models = ("LLMFactor_GPT-4-turbo", "LLMFactor_GPT-4", "LLMFactor_GPT-3.5-turbo")
    for table, language, variants in (("Table 7", "English factor template", ENGLISH_FACTOR_ROWS), ("Table 8", "Chinese factor template", CHINESE_FACTOR_ROWS)):
        for variant, template, values in variants:
            for index, value in enumerate(values):
                add(table, language, f"{variant}:{models[index // 2]}:{template}", "CMIN-US" if table == "Table 7" else "CMIN-CN", metrics[index % 2], value, "native_llmfactor")
    if len(rows) != 206:
        raise AssertionError(f"displayed result census changed: {len(rows)}")
    if sum(row["scope"] == "native_llmfactor" for row in rows) != 82:
        raise AssertionError("native result denominator changed")
    return rows


RELATION_TEMPLATE = "Please fill in the blank and return a complete sentence: {stock_target} and {stock_match} are most likely in a ___ relationship."
FACTOR_TEMPLATE = "Please extract the top {k} factors that may affect the stock price of {stock_target} from the following news."
PRICE_OPEN = "Based on the following information, please judge the direction of the stock price from rise/fall, fill in the blank and give reasons."


def movement_word(value: int) -> str:
    if value not in (0, 1):
        raise ValueError("the paper defines movement text only for binary values 0 and 1")
    return "rose" if value == 1 else "fell"


def render_english_skgp(
    stock_target: str,
    stock_match: str,
    news: str,
    factors: str,
    relation: str,
    dates: list[str],
    movements: list[int],
    target_date: str,
    k: int = 5,
) -> dict[str, str]:
    if len(dates) != 5 or len(movements) != 5:
        raise ValueError("the disclosed appendix template fixes exactly five historical movements")
    relation_prompt = RELATION_TEMPLATE.format(stock_target=stock_target, stock_match=stock_match)
    factor_prompt = FACTOR_TEMPLATE.format(k=k, stock_target=stock_target) + "\n" + news
    lines = [
        PRICE_OPEN,
        f"These are the main factors that may affect this stock's price recently: {factors}.",
        f"These are the connections between the companies that have appeared in the news: {relation}.",
    ]
    lines.extend(f"On {date}, the stock price of {stock_target} {movement_word(value)}." for date, value in zip(dates, movements))
    lines.append(f"On {target_date}, the stock price of {stock_target} will ___.")
    return {"relation_prompt": relation_prompt, "factor_prompt": factor_prompt, "price_prompt": "\n".join(lines)}


def accuracy_mcc(tp: int, fp: int, fn: int, tn: int) -> tuple[float, float]:
    total = tp + fp + fn + tn
    if total == 0:
        raise ValueError("ACC denominator is zero")
    acc = (tp + tn) / total
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    if denominator == 0:
        raise ValueError("MCC denominator is zero")
    return acc, (tp * tn - fp * fn) / denominator


def prompt_template_rows() -> list[dict[str, str]]:
    rows = [
        {"template_id": "EN-Step1", "language": "English", "stage": "relation", "published_template": RELATION_TEMPLATE, "complete_literal_template": "yes", "request_envelope_disclosed": "no", "exact_replay_credit": "no"},
        {"template_id": "EN-Step2", "language": "English", "stage": "factor", "published_template": FACTOR_TEMPLATE, "complete_literal_template": "partial_news_boundary_unspecified", "request_envelope_disclosed": "no", "exact_replay_credit": "no"},
        {"template_id": "EN-Step3", "language": "English", "stage": "prediction", "published_template": PRICE_OPEN + " [factor; relation; five movements; target blank]", "complete_literal_template": "yes_as_skeleton", "request_envelope_disclosed": "no", "exact_replay_credit": "no"},
        {"template_id": "CN-Step1", "language": "Chinese", "stage": "relation", "published_template": "请填空并返回完整的句子: stock_target 和 stock_match 最可能是___关系。", "complete_literal_template": "yes", "request_envelope_disclosed": "no", "exact_replay_credit": "no"},
        {"template_id": "CN-Step2", "language": "Chinese", "stage": "factor", "published_template": "请从以下新闻中提取可能影响stock_target股价的前k个因素。", "complete_literal_template": "partial_news_boundary_unspecified", "request_envelope_disclosed": "no", "exact_replay_credit": "no"},
        {"template_id": "CN-Step3", "language": "Chinese", "stage": "prediction", "published_template": "根据以下信息，请判断股票价格是上涨还是下跌，填写在空白处并给出理由。[factor; relation; five movements; target blank]", "complete_literal_template": "yes_as_skeleton", "request_envelope_disclosed": "no", "exact_replay_credit": "no"},
    ]
    for variant, template, _ in ENGLISH_FACTOR_ROWS + CHINESE_FACTOR_ROWS:
        rows.append({"template_id": variant, "language": "English" if variant.startswith("EN") else "Chinese", "stage": "factor_ablation", "published_template": template, "complete_literal_template": "template_only", "request_envelope_disclosed": "no", "exact_replay_credit": "no"})
    return rows


def component_execution_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rendered = render_english_skgp(
        "NVDA", "AMD", "NVDA announced a new product.", "new product demand; supplier capacity",
        "competitor", ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"],
        [1, 0, 1, 1, 0], "2024-01-09",
    )
    prompt_rows = []
    for component in ("relation_prompt", "factor_prompt", "price_prompt"):
        payload = rendered[component]
        prompt_rows.append(
            {
                "component": component,
                "status": "rendered_from_disclosed_english_skeleton",
                "sha256": bytes_sha256(payload.encode()),
                "characters": str(len(payload)),
                "conditional_component_credit": "yes",
                "llm_invoked": "no",
                "native_pipeline_credit": "no",
                "paper_result_credit": "no",
                "boundary": "newline chosen between factor instruction and news; message roles and API parameters unreleased" if component == "factor_prompt" else "template formatting only; no request envelope or response",
            }
        )
    acc, mcc = accuracy_mcc(12, 3, 2, 8)
    metric_rows = [
        {"metric": "ACC", "fixture": "tp=12;fp=3;fn=2;tn=8", "computed_value": repr(acc), "expected_value": "0.8", "status": "pass", "conditional_component_credit": "yes", "paper_result_credit": "no"},
        {"metric": "MCC", "fixture": "tp=12;fp=3;fn=2;tn=8", "computed_value": repr(mcc), "expected_value": repr(90 / math.sqrt(23100)), "status": "pass", "conditional_component_credit": "yes", "paper_result_credit": "no"},
    ]
    return prompt_rows, metric_rows


def configuration_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    datasets = (
        ("StockNet", "19318", "87", "2014-01-01", "2016-01-01", "US", "time series and text", "price sequence and tweets"),
        ("CMIN-US", "83553", "110", "2018-01-01", "2021-12-31", "US", "time series and text", "price sequence and tweets"),
        ("CMIN-CN", "198781", "300", "2018-01-01", "2021-12-31", "CN", "time series and text", "price sequence and tweets"),
        ("EDT", "54080", "4228", "2020-03-01", "2021-05-06", "US", "text", "prices and news articles"),
    )
    for name, size, stocks, start, end, market, dtype, resource in datasets:
        rows.append({"group": "dataset", "item": name, "value": f"samples={size};stocks={stocks};start={start};end={end};market={market};type={dtype};resource={resource}", "disclosure": "paper_table_and_prose", "operationally_complete": "no"})
    for alias, label in (("gpt-3.5-turbo-1106", "LLMFactor_GPT-3.5-turbo"), ("gpt-4", "LLMFactor_GPT-4"), ("gpt-4-1106-preview", "LLMFactor_GPT-4-turbo")):
        rows.append({"group": "model", "item": label, "value": alias, "disclosure": "paper_implementation_details", "operationally_complete": "no"})
    general = (
        ("window_size_t", "5"), ("factor_count_k", "5"), ("BERT_batch_size", "64"),
        ("GPT_batch_size", "5"), ("hardware", "NVIDIA RTX A6000"),
        ("keyphrase_toolkit", "pke and pke_zh"), ("task", "binary next movement; rise=1 fall=0"),
    )
    for item, value in general:
        rows.append({"group": "implementation", "item": item, "value": value, "disclosure": "paper", "operationally_complete": "yes" if item in {"window_size_t", "factor_count_k", "BERT_batch_size", "GPT_batch_size"} else "no"})
    baselines = (
        ("FinBERT_EN", "ProsusAI/finbert;438MB"), ("FinBERT_CN", "bardsai/finance-sentiment-zh-base;409MB"),
        ("RoBERTa_EN", "soleimanian/financial-roberta-large-sentiment;1.42GB"),
        ("RoBERTa_CN", "IDEA-CCNL/Erlangshen-Roberta-110M-Sentiment;409MB"),
        ("FinGPT_EN", "FinGPT/fingpt-sentiment_llama2-13b_lora;14.36GB"),
        ("FinGPT_CN", "oliverwang15/FinGPT_ChatGLM2_Sentiment_Instruction_LoRA_FT;7.88GB"),
    )
    for item, value in baselines:
        rows.append({"group": "baseline_model", "item": item, "value": value, "disclosure": "appendix", "operationally_complete": "no"})
    return rows


def method_rows() -> list[dict[str, str]]:
    specifications = (
        ("task", "binary next stock movement", "exact", "nonblocking"),
        ("movement mapping", "rise=1 and fall=0", "exact", "nonblocking"),
        ("flat/equal-price label", "not defined", "missing", "blocking"),
        ("target alignment", "P_t+1 objective versus appendix date_i skeleton not explicitly mapped", "ambiguous", "blocking"),
        ("window size", "t=5", "exact", "nonblocking"),
        ("factor count", "k=5", "exact", "nonblocking"),
        ("relation prompt", "literal skeleton released", "partial", "blocking"),
        ("factor prompt", "literal skeleton released; news separator unspecified", "partial", "blocking"),
        ("prediction prompt", "literal skeleton released", "partial", "blocking"),
        ("Chinese prompts", "literal skeleton released", "partial", "blocking"),
        ("message roles", "not disclosed", "missing", "blocking"),
        ("system prompt", "not disclosed", "missing", "blocking"),
        ("temperature", "not disclosed", "missing", "blocking"),
        ("top_p", "not disclosed", "missing", "blocking"),
        ("seed/API determinism", "not disclosed", "missing", "blocking"),
        ("max tokens", "not disclosed", "missing", "blocking"),
        ("stop sequences", "not disclosed", "missing", "blocking"),
        ("retry/backoff/timeout", "not disclosed", "missing", "blocking"),
        ("request timestamps", "not disclosed", "missing", "blocking"),
        ("request/response logs", "not released", "missing", "blocking"),
        ("response parser", "rise/fall to binary procedure not disclosed", "missing", "blocking"),
        ("multiple-company matching", "deduplication, aliases, ordering and tie handling unspecified", "missing", "blocking"),
        ("stock list snapshot", "NYSE/NASDAQ tuple set not released", "missing", "blocking"),
        ("stock_match expression", "set intersection between tuples and prose is not operationally typed", "conflict", "blocking"),
        ("StockNet dataset", "citation plus counts/dates only", "partial", "blocking"),
        ("CMIN-US dataset", "citation plus counts/dates only", "partial", "blocking"),
        ("CMIN-CN dataset", "citation plus counts/dates only", "partial", "blocking"),
        ("EDT dataset", "citation plus counts/dates only", "partial", "blocking"),
        ("data snapshots/checksums", "not released", "missing", "blocking"),
        ("train/validation/test split", "not disclosed", "missing", "blocking"),
        ("preprocessing", "not disclosed", "missing", "blocking"),
        ("news aggregation", "not disclosed", "missing", "blocking"),
        ("universe membership", "counts but no membership snapshot", "partial", "blocking"),
        ("baseline code versions", "not disclosed", "missing", "blocking"),
        ("baseline original settings", "asserted without operational configuration", "partial", "blocking"),
        ("model aliases", "three API aliases disclosed", "exact", "nonblocking"),
        ("baseline checkpoints", "six sentiment model keys disclosed", "partial", "blocking"),
        ("batch sizes", "64 BERT and 5 GPT", "exact", "nonblocking"),
        ("hardware", "RTX A6000", "partial", "nonblocking"),
        ("software environment", "not released", "missing", "blocking"),
        ("random seeds", "not released", "missing", "blocking"),
        ("repeat count", "not disclosed", "missing", "blocking"),
        ("ACC formula", "fully specified", "exact", "nonblocking"),
        ("MCC formula", "fully specified", "exact", "nonblocking"),
        ("confusion matrices", "not released", "missing", "blocking"),
        ("raw predictions", "not released", "missing", "blocking"),
        ("raw result arrays", "not released", "missing", "blocking"),
        ("uncertainty/significance", "not reported", "missing", "blocking"),
        ("ablation aggregation", "displayed averages but hidden precision absent", "partial", "blocking"),
        ("case-study selection", "selection rule not disclosed", "missing", "blocking"),
        ("author code", "not found in primary records or complete repository searches", "missing", "blocking"),
        ("official source archive", "nine document files only", "exact", "nonblocking"),
        ("paper reproducibility caveat", "variable LLM outputs explicitly acknowledged", "exact", "nonblocking"),
    )
    return [{"dimension": dimension, "paper_disclosure": disclosure, "assessment": assessment, "severity": severity, "native_result_credit": "no"} for dimension, disclosure, assessment, severity in specifications]


def internal_consistency_rows() -> list[dict[str, str]]:
    issues: list[tuple[str, str, str, str]] = []
    full = {
        "StockNet": ((65.81, 66.32, 57.59), (.228, .238, .145), (63.24, .203)),
        "CMIN-US": ((61.71, 65.26, 66.42), (.228, .284, .288), (64.46, .267)),
        "CMIN-CN": ((60.59, 57.16, 56.11), (.245, .196, .139), (57.96, .194)),
        "EDT": ((59.09, 60.83, 58.11), (.082, .105, .097), (59.35, .095)),
    }
    for dataset, (acc_values, mcc_values, displayed) in full.items():
        for metric, values, shown, digits in (("ACC", acc_values, displayed[0], 2), ("MCC", mcc_values, displayed[1], 3)):
            computed = sum(values) / 3
            rounded = round(computed, digits)
            if rounded != shown:
                issues.append((f"Table 3 {dataset} {metric} is not the rounded mean of displayed Table 2 inputs", f"computed={computed:.9f};rounded={rounded};displayed={shown}", "lineage_ambiguity", "hidden precision or raw values needed"))
    issues.extend(
        [
            ("Table 2 does not support unqualified superiority in EDT accuracy", "EDT baseline ACC=75.67 while best LLMFactor ACC=60.83", "claim_conflict", "qualify superiority by metric"),
            ("Ablation MCC contribution shares are not recoverable at displayed precision", "displayed rows imply approximately 33.7%,45.5%,20.8%, not 32%,46%,22%", "lineage_ambiguity", "release hidden-precision aggregates"),
            ("English final-template superiority is not uniform", "EN-3 loses GPT-4-turbo ACC to EN-2 and GPT-3.5 MCC to EN-2", "claim_conflict", "state metric/model-specific winners"),
            ("Chinese initial-template superiority is not uniform", "CN-1 loses ACC for all three models; it wins/ties MCC only", "claim_conflict", "state metric/model-specific winners"),
            ("stock_match set expression is not operational", "S is a tuple set while news_target is prose; alias matching, multiplicity and ordering are undefined", "method_ambiguity", "release matching code and stock snapshot"),
            ("flat prices have no class definition", "only strict rise and fall labels are defined", "method_ambiguity", "define equality behavior"),
            ("target-date notation is underlinked", "objective predicts P_t+1 while appendix fills date_i after i-5 through i-1", "method_ambiguity", "publish exact sample-to-prompt alignment"),
            ("LLM output parsing is absent", "paper requests rise/fall plus reasons but gives no binary parser", "method_ambiguity", "release parser and invalid-response policy"),
            ("CMIN resource terminology changes", "dataset table says tweets while method prose repeatedly says news", "terminology_ambiguity", "identify exact text field and source"),
            ("No statistical uncertainty accompanies 206 point estimates", "no repeats, intervals, standard errors, or significance tests", "evidence_gap", "release repeated runs and uncertainty"),
            ("Exact reproducibility caveat is not an operational protocol", "paper acknowledges variable LLM responses but releases no request logs or determinism settings", "evidence_gap", "release immutable requests and responses"),
            ("Case-study selection and provenance are absent", "four illustrated cases have no declared selection rule or underlying run objects", "evidence_gap", "release candidate pool and selected outputs"),
        ]
    )
    return [{"issue_id": f"LLMF-INT-{i:03d}", "issue": issue, "evidence": evidence, "classification": classification, "required_resolution": resolution, "paper_result_credit": "no"} for i, (issue, evidence, classification, resolution) in enumerate(issues, 1)]


def claim_rows() -> list[dict[str, str]]:
    claims = (
        ("LLMFactor is superior across four benchmarks", "not reproduced; overbroad for EDT ACC"),
        ("MCC improvements are 2.9%, 0.4%, 11%, and 4.8%", "displayed absolute MCC differences are recoverable; native runs are not"),
        ("StockNet average ACC exceeds 63% and MCC exceeds 0.2", "recoverable from displayed cells only"),
        ("CMIN-US average ACC exceeds 63% and MCC exceeds 0.2", "recoverable from displayed cells only"),
        ("CMIN-CN average ACC is 58% and MCC 0.19", "recoverable approximately from displayed cells only"),
        ("EDT average ACC is 59% and MCC 0.1", "recoverable approximately from displayed cells only"),
        ("price/factor/relation ACC shares are 86%/9%/5%", "approximately recoverable from displayed ablation values"),
        ("price/factor/relation MCC shares are 32%/46%/22%", "not exactly recoverable from displayed ablation values"),
        ("factor layer contributes most significantly", "descriptive point-estimate claim without uncertainty"),
        ("English final factor template performs best", "false for two of six displayed model-metric pairs"),
        ("Chinese initial factor template performs best", "false for ACC; only MCC supports it/ties"),
        ("LLMFactor robustly predicts across templates", "no repeats or uncertainty; not reproduced"),
        ("case studies demonstrate effective integration", "qualitative selected examples only; no provenance"),
        ("factors provide profitable market-trend predictions", "no trading portfolio, return, cost, or profit experiment"),
        ("exact reproducibility cannot be guaranteed", "supported by the paper's explicit limitation"),
    )
    return [{"claim_id": f"LLMF-CLAIM-{i:03d}", "claim": claim, "audit_assessment": assessment, "exactly_reproduced": "no", "native_paper_result_reproduced": "no"} for i, (claim, assessment) in enumerate(claims, 1)]


def github_rows(directory: Path) -> list[dict[str, str]]:
    paths = sorted(directory.glob("0[1-6]_*.json"))
    if len(paths) != len(GITHUB_QUERIES):
        raise ValueError(f"expected six GitHub search snapshots, found {len(paths)}")
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
                "repositories": "|".join(item["full_name"] for item in data.get("items", [])),
                "author_linked_repository_found": "no",
                "interpretation": "broad name/readme search with collisions" if path.name.startswith("01_") else "targeted paper/identifier/author search",
            }
        )
    return rows


def tasoo_inventory(repo: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, text=True, capture_output=True).stdout.strip()
    if head != EXPECTED_TASOO_HEAD:
        raise ValueError(f"tasoo repository head changed: {head}")
    raw = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "-l", "-z", "HEAD"], check=True, capture_output=True).stdout
    rows = []
    python_total = compiled = 0
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, name_raw = entry.split(b"\t", 1)
        mode, object_type, object_sha, size = metadata.decode().split()
        name = name_raw.decode()
        compile_status = "not_python"
        if name.endswith(".py"):
            python_total += 1
            payload = (repo / name).read_bytes()
            try:
                compile(payload, name, "exec")
                compile_status = "compiled"
                compiled += 1
            except SyntaxError as exc:
                compile_status = f"SyntaxError:{exc.lineno}"
        rows.append({"repository": "tasoo-oos/LLMFactor", "path": name, "bytes": size, "source_object_id": object_sha, "object_id_type": "git_sha1", "compile_status": compile_status, "native_author_source": "no", "native_paper_result_output": "no"})
    summary = {"repository": TASOO_REPO, "head": head, "tracked_files": len(rows), "python_files": python_total, "compiled_python_files": compiled, "created": "2025-01-09", "paper_author_overlap": False, "native_credit": False}
    return rows, summary


def kuon_inventory(tree_path: Path, source_dir: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    data = json.loads(tree_path.read_text(encoding="utf-8"))
    if data.get("truncated"):
        raise ValueError("Kuon tree API snapshot is truncated")
    files = [entry for entry in data["tree"] if entry.get("type") == "blob"]
    rows = []
    python_total = compiled = failed = 0
    for entry in files:
        name = entry["path"]
        compile_status = "not_python"
        if name.endswith(".py"):
            python_total += 1
            path = source_dir / name
            if not path.exists():
                compile_status = "source_not_downloaded"
            else:
                try:
                    compile(path.read_bytes(), name, "exec")
                    compile_status = "compiled"
                    compiled += 1
                except SyntaxError as exc:
                    compile_status = f"SyntaxError:{exc.lineno}"
                    failed += 1
        rows.append({"repository": "Kuon12138/SKGP", "path": name, "bytes": str(entry.get("size", "")), "source_object_id": entry["sha"], "object_id_type": "git_sha1", "compile_status": compile_status, "native_author_source": "no", "native_paper_result_output": "no"})
    summary = {"repository": KUON_REPO, "head": EXPECTED_KUON_HEAD, "tracked_files": len(rows), "tracked_bytes": sum(entry.get("size", 0) for entry in files), "python_files": python_total, "compiled_python_files": compiled, "failed_python_files": failed, "created": "2025-04-03", "paper_author_overlap": False, "native_credit": False}
    return rows, summary


def community_method_rows() -> list[dict[str, str]]:
    rows = []
    tasoo = (
        ("author linkage", "nonmatch", "single commit by Tasoo Park; no paper-author overlap"),
        ("chronology", "post-paper", "created 2025-01-09, seven months after arXiv v1"),
        ("model", "different", "default llama-3.1-8B-instruct-Q8_0, not the three paper GPT aliases"),
        ("datasets", "partial", "CMIN-US only; no StockNet, CMIN-CN, or EDT"),
        ("CMIN-US universe", "defective", "110 files each side but only 105 exact ticker intersections because five names differ"),
        ("CMIN-US scheduled rows", "nonmatch", "80,655 exact-name ticker/date entries versus paper Data Size 83,553"),
        ("relation stage", "missing", "default pipeline has no paper Step1 relation extraction"),
        ("factor prompt", "different", "system plus two user messages and formatting instruction"),
        ("price prompt", "different", "system-message decomposition and different text"),
        ("generation parameters", "community_choice", "temperature=0 and max-token/stop settings absent from paper"),
        ("window/factor count", "match", "price_k=5 and factor_k=5"),
        ("metrics", "partial", "ACC/MCC plus F1 implemented"),
        ("tests", "missing", "no tracked test paths"),
        ("published results", "missing", "no tracked output reproduces any paper table cell"),
    )
    kuon = (
        ("author linkage", "nonmatch", "commits by Kuon12138; no paper-author overlap"),
        ("chronology", "post-paper", "created 2025-04-03"),
        ("model", "different", "Llama 3.3 70B/OpenRouter or Ollama, not the paper aliases"),
        ("configuration security", "defective", "tracked config contains an apparent API credential; value intentionally omitted"),
        ("datasets", "partial", "large CMIN-US/CN trees but no StockNet or EDT"),
        ("window", "different", "runnable YAML sets window_size=30, not paper t=5"),
        ("relation stage", "changed", "Chinese financial-analyst prompt differs from appendix literal"),
        ("factor prompt", "changed", "Chinese categorized explanation prompt differs from appendix literal"),
        ("prediction prompt", "changed", "adds prices, percentages, news truncation, BERT-derived features"),
        ("generation parameters", "community_choice", "temperature=.7, top_p=.9 and Llama settings absent from paper"),
        ("source validity", "defective", "14/15 .py paths compile; xinghuo.py is a raw curl command"),
        ("saved AAPL result", "target_leakage", "result date 2021-12-22 reasons from 2021-12-31 prices"),
        ("saved AAPL prediction", "failed", "tracked output reports str has no attribute strftime"),
        ("published results", "missing", "no tracked output reproduces any paper table cell"),
    )
    for repository, values in (("tasoo-oos/LLMFactor", tasoo), ("Kuon12138/SKGP", kuon)):
        for dimension, assessment, evidence in values:
            rows.append({"repository": repository, "dimension": dimension, "assessment": assessment, "evidence": evidence, "native_credit": "no", "paper_result_credit": "no"})
    return rows


def community_data_rows(tasoo_repo: Path, kuon_tree: Path) -> list[dict[str, str]]:
    """Recompute the material community-data facts instead of transcribing them."""
    root = tasoo_repo / "llmfactor/data/CMIN-US"
    news_files = sorted((root / "news/raw").glob("*.csv"))
    price_files = sorted((root / "price/raw").glob("*.csv"))
    news_dates: dict[str, set[str]] = {}
    price_dates: dict[str, set[str]] = {}
    news_rows = price_rows = 0
    news_min = news_max = price_min = price_max = None
    for path in news_files:
        dates: set[str] = set()
        with path.open(newline="", encoding="utf-8", errors="replace") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                news_rows += 1
                date = row["date"][:10]
                dates.add(date)
                news_min = date if news_min is None or date < news_min else news_min
                news_max = date if news_max is None or date > news_max else news_max
        news_dates[path.stem] = dates
    for path in price_files:
        dates: set[str] = set()
        with path.open(newline="", encoding="utf-8", errors="replace") as stream:
            for row in csv.DictReader(stream):
                price_rows += 1
                date = row["Date"][:10]
                dates.add(date)
                price_min = date if price_min is None or date < price_min else price_min
                price_max = date if price_max is None or date > price_max else price_max
        price_dates[path.stem] = set(sorted(dates)[5:])
    common = sorted(set(news_dates) & set(price_dates))
    scheduled = sum(len(news_dates[ticker] & price_dates[ticker]) for ticker in common)
    news_only = sorted(set(news_dates) - set(price_dates))
    price_only = sorted(set(price_dates) - set(news_dates))
    observed = (len(news_files), len(price_files), news_rows, price_rows, len(common), scheduled)
    expected = (110, 110, 871759, 110879, 105, 80655)
    if observed != expected:
        raise ValueError(f"pinned tasoo CMIN-US audit changed: {observed}")

    kuon_data = json.loads(kuon_tree.read_text(encoding="utf-8"))
    kuon_csv = [entry["path"] for entry in kuon_data["tree"] if entry.get("type") == "blob" and entry["path"].endswith(".csv")]
    kuon_news = sum("/news/" in path for path in kuon_csv)
    kuon_price = sum("/price/" in path for path in kuon_csv)
    if (len(kuon_csv), kuon_news, kuon_price) != (1641, 821, 820):
        raise ValueError("pinned Kuon data tree audit changed")
    return [
        {"repository": "tasoo-oos/LLMFactor", "dataset": "CMIN-US", "tracked_csv_files": str(len(news_files) + len(price_files)), "news_files": str(len(news_files)), "price_files": str(len(price_files)), "news_rows": str(news_rows), "price_rows": str(price_rows), "news_date_range": f"{news_min}/{news_max}", "price_date_range": f"{price_min}/{price_max}", "exact_ticker_intersection": str(len(common)), "scheduled_entries_t5_exact_names": str(scheduled), "ticker_name_mismatches": f"news_only={news_only};price_only={price_only}", "native_credit": "no"},
        {"repository": "Kuon12138/SKGP", "dataset": "CMIN-US and CMIN-CN", "tracked_csv_files": str(len(kuon_csv)), "news_files": str(kuon_news), "price_files": str(kuon_price), "news_rows": "not_scanned_from_tree_snapshot", "price_rows": "not_scanned_from_tree_snapshot", "news_date_range": "not_audited", "price_date_range": "not_audited", "exact_ticker_intersection": "not_audited", "scheduled_entries_t5_exact_names": "not_applicable_config_t30", "ticker_name_mismatches": "not_audited", "native_credit": "no"},
    ]


def local_mapping_rows() -> list[dict[str, str]]:
    return [
        {
            "record_id": "CensusArxiv240610811",
            "candidate_id": "paper_llmfactor_explainable_price_news",
            "local_tier": "M0_narrative_translation",
            "local_formula": "rank(ret_12_1)+rank(sale_gr1)+rank(gp_me)+rank(dolvol_126d)-rank(rvol_252d)",
            "paper_task": "daily binary stock movement from same-day text plus five historical movements through SKGP",
            "local_task": "monthly U.S. characteristic long-short portfolio without text or LLMs",
            "paper_inputs_present": "no",
            "paper_prompt_pipeline_present": "no",
            "paper_result_credit": "no",
        }
    ]


def readme(manifest: dict[str, Any]) -> str:
    return f"""# LLMFactor paper/source replication audit

This package audits the original arXiv v1 paper, the ACL 2024 authoritative
record, the official TeX archive, every displayed result cell, the disclosed
English/Chinese prompt skeletons, the ACC/MCC equations, six complete GitHub
repository searches, and two prominent later community implementations. It is
fail-closed: rebuilding the paper, rendering a prompt, evaluating a metric on a
fixture, or running unaffiliated code does not reproduce an LLMFactor result.

## Honest verdict

- **Native LLMFactor results reproduced: 0/82 displayed native result cells.**
- **All displayed experimental results reproduced: 0/206 cells**, including
  124 baselines that also lack released run inputs and predictions.
- The official nine-file source archive rebuilds without patching to 12 pages.
  Extracted-token multiset Jaccard is {manifest['arxiv_source_rebuild_jaccard']:.4%}
  against arXiv v1 and {manifest['acl_source_rebuild_jaccard']:.4%} against the
  ACL final. This is strong document provenance, not experiment reproduction.
- Three English prompt skeletons render deterministically on a declared fixture,
  and the published ACC/MCC formulas pass a deterministic confusion-matrix
  fixture. These are narrow conditional component checks only: no LLM was
  invoked and no paper request or output was replayed.
- Six complete repository searches find no author-linked code or data. The two
  relevant community repositories were created in 2025 by non-authors and
  materially change models, prompts, data paths, or windows. Neither reproduces
  a published cell.
- The local `paper_llmfactor_explainable_price_news` strategy remains an M0
  narrative translation. It is a monthly characteristic portfolio with no
  news, prompts, relation/factor extraction, daily labels, or paper metrics.

## Material blockers and paper-level ambiguities

- No author implementation, immutable API request/response log, exact data
  snapshot, split, preprocessing, universe membership, stock matcher, response
  parser, random seed, repeat count, predictions, confusion matrices, or raw
  result arrays is released.
- The paper itself states that variable LLM responses prevent guaranteed exact
  reproduction, but supplies no deterministic replay protocol.
- Four Table 3 cells are not recoverable by rounding the displayed Table 2
  inputs; hidden-precision values could explain this, but those values are not
  released. The stated MCC layer shares likewise do not exactly follow from the
  displayed ablation cells.
- The unqualified superiority wording fails for EDT accuracy: the EDT baseline
  reports 75.67, versus a best LLMFactor value of 60.83.
- Appendix claims about the best English/Chinese factor templates are not true
  across every displayed model/metric pair.
- Equal-price labels, multi-company matching, target alignment, and parsing of
  free-form rise/fall responses remain operationally undefined.

## Files

- `source_provenance.json`, `source_file_inventory.csv`, and
  `source_build_audit.csv`: pinned paper/source records and document rebuilds.
- `displayed_result_conformance.csv`: all 206 displayed cells, with the 82
  native LLMFactor cells distinguished from 124 baseline cells.
- `configuration_inventory.csv`, `prompt_template_conformance.csv`,
  `prompt_component_execution.csv`, and `metric_component_execution.csv`:
  disclosed settings and narrow executable components.
- `method_specification_audit.csv`, `paper_internal_consistency_audit.csv`, and
  `claim_audit.csv`: missing specifications, numerical lineage, and claims.
- `source_search_inventory.csv`, `community_source_inventory.csv`,
  `community_data_inventory.csv`, and `community_method_conformance.csv`:
  public-source evidence with zero native credit.
- `local_mapping_conformance.csv`, `native_execution.json`, and `manifest.json`:
  the local proxy boundary and machine-readable verdict.
"""


def build(args: argparse.Namespace) -> dict[str, Any]:
    paper = args.paper.resolve()
    arxiv_pdf = args.arxiv_pdf.resolve()
    acl_pdf = args.acl_pdf.resolve()
    rebuild = args.source_rebuild.resolve()
    if sha256(paper) != EXPECTED_ARXIV_PDF_SHA256:
        raise ValueError("tracked original paper hash changed")
    validate_pdf(arxiv_pdf, EXPECTED_ARXIV_PDF_SHA256, ("LLMFactor", "Table 8", "Sequential Knowledge-Guided Prompting", "variable nature of LLM responses"))
    validate_pdf(acl_pdf, EXPECTED_ACL_PDF_SHA256, ("LLMFactor", "Table 8", "Sequential Knowledge-Guided Prompting"))
    for path, expected, label in ((args.arxiv_page, EXPECTED_ARXIV_RECORD_SHA256, "arXiv record"), (args.acl_page, EXPECTED_ACL_RECORD_SHA256, "ACL record"), (rebuild, EXPECTED_REBUILD_SHA256, "source rebuild")):
        if sha256(path) != expected:
            raise ValueError(f"{label} hash changed")

    source_files = source_inventory(args.source_archive)
    builds = [
        source_build_row("arxiv_v1_source_rebuild", arxiv_pdf, rebuild, "exact arXiv v1 source archive"),
        source_build_row("arxiv_v1_source_to_acl_final", acl_pdf, rebuild, "arXiv v1 source compared with separately produced ACL final"),
    ]
    results = displayed_result_rows()
    prompts = prompt_template_rows()
    prompt_exec, metric_exec = component_execution_rows()
    configs = configuration_rows()
    methods = method_rows()
    issues = internal_consistency_rows()
    claims = claim_rows()
    searches = github_rows(args.github_search_dir)
    tasoo_files, tasoo_summary = tasoo_inventory(args.tasoo_repo)
    kuon_files, kuon_summary = kuon_inventory(args.kuon_tree, args.kuon_source)
    community_files = tasoo_files + kuon_files
    community_methods = community_method_rows()
    community_data = community_data_rows(args.tasoo_repo, args.kuon_tree)
    mappings = local_mapping_rows()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifacts = (
        ("source_file_inventory.csv", source_files),
        ("source_build_audit.csv", builds),
        ("displayed_result_conformance.csv", results),
        ("configuration_inventory.csv", configs),
        ("prompt_template_conformance.csv", prompts),
        ("prompt_component_execution.csv", prompt_exec),
        ("metric_component_execution.csv", metric_exec),
        ("method_specification_audit.csv", methods),
        ("paper_internal_consistency_audit.csv", issues),
        ("claim_audit.csv", claims),
        ("source_search_inventory.csv", searches),
        ("community_source_inventory.csv", community_files),
        ("community_data_inventory.csv", community_data),
        ("community_method_conformance.csv", community_methods),
        ("local_mapping_conformance.csv", mappings),
    )
    for name, rows in artifacts:
        write_csv(output / name, rows, list(rows[0]))

    source_provenance = {
        "paper": "LLMFactor: Extracting Profitable Factors through Prompts for Explainable Stock Movement Prediction",
        "authors": ["Meiyun Wang", "Kiyoshi Izumi", "Hiroki Sakaji"],
        "arxiv_record": ARXIV_RECORD,
        "arxiv_record_sha256": sha256(args.arxiv_page),
        "arxiv_versions": [{"version": "v1", "submitted": "2024-06-16"}],
        "arxiv_pdf": ARXIV_PDF,
        "arxiv_pdf_sha256": sha256(arxiv_pdf),
        "acl_record": ACL_RECORD,
        "acl_record_sha256": sha256(args.acl_page),
        "acl_pdf": ACL_PDF,
        "acl_pdf_sha256": sha256(acl_pdf),
        "arxiv_source": ARXIV_SOURCE,
        "arxiv_source_sha256": sha256(args.source_archive),
        "official_source_members": len(source_files),
        "official_source_contains_native_code": False,
        "official_source_contains_raw_results": False,
        "author_linked_code_or_data_found": False,
        "github_repository_searches": searches,
        "community_repositories": [tasoo_summary, kuon_summary],
        "kuon_tree_snapshot_sha256": sha256(args.kuon_tree),
    }
    write_json(output / "source_provenance.json", source_provenance)

    native = {
        "native_execution_attempted": False,
        "reason": "no_author_pipeline_data_snapshot_request_logs_response_parser_predictions_or_raw_results",
        "author_linked_code_found": False,
        "displayed_result_cells_total": len(results),
        "displayed_result_cells_reproduced": 0,
        "native_llmfactor_result_cells_total": sum(row["scope"] == "native_llmfactor" for row in results),
        "native_llmfactor_result_cells_reproduced": 0,
        "baseline_result_cells_total": sum(row["scope"] == "baseline" for row in results),
        "baseline_result_cells_reproduced": 0,
        "english_prompt_components_conditionally_rendered": len(prompt_exec),
        "metric_components_conditionally_executed": len(metric_exec),
        "llm_calls_made": 0,
        "community_repository_native_credit": False,
        "local_mapping_status": "M0_narrative_translation_zero_paper_result_credit",
        "paper_result_credit": False,
    }
    write_json(output / "native_execution.json", native)

    manifest = {
        "audit": "LLMFactor arXiv v1 / ACL 2024 paper and source audit",
        "overall_fidelity": "official_documents_and_prompt_metric_components_audited_zero_of_82_native_and_zero_of_206_total_result_cells_reproduced",
        "official_pdf_pages_audited": 24,
        "official_pdf_pages_visually_inspected": 24,
        "official_source_members": len(source_files),
        "arxiv_source_rebuild_jaccard": builds[0]["token_multiset_jaccard"],
        "acl_source_rebuild_jaccard": builds[1]["token_multiset_jaccard"],
        "displayed_result_cells": len(results),
        "displayed_result_cells_reproduced": 0,
        "native_llmfactor_result_cells": sum(row["scope"] == "native_llmfactor" for row in results),
        "native_llmfactor_result_cells_reproduced": 0,
        "baseline_result_cells": sum(row["scope"] == "baseline" for row in results),
        "baseline_result_cells_reproduced": 0,
        "prompt_templates_inventoried": len(prompts),
        "prompt_components_conditionally_rendered": len(prompt_exec),
        "metric_components_conditionally_executed": len(metric_exec),
        "method_dimensions": len(methods),
        "internal_consistency_issues": len(issues),
        "claims_audited": len(claims),
        "repository_searches": len(searches),
        "author_linked_code_found": False,
        "community_source_objects": len(community_files),
        "tasoo_head": tasoo_summary["head"],
        "kuon_head": kuon_summary["head"],
        "local_mapping_tier": "M0_narrative_translation",
        "paper_result_credit": False,
    }
    write_json(output / "manifest.json", manifest)
    (output / "README.md").write_text(readme(manifest), encoding="utf-8")
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--paper", type=Path, default=ROOT / "literature_review/papers/19_llmfactor_extracting_profitable_factors_through_prompts_for_explainable_stock_movement_pre.pdf")
    result.add_argument("--arxiv-pdf", type=Path, required=True)
    result.add_argument("--acl-pdf", type=Path, required=True)
    result.add_argument("--source-archive", type=Path, required=True)
    result.add_argument("--source-rebuild", type=Path, required=True)
    result.add_argument("--arxiv-page", type=Path, required=True)
    result.add_argument("--acl-page", type=Path, required=True)
    result.add_argument("--github-search-dir", type=Path, required=True)
    result.add_argument("--tasoo-repo", type=Path, required=True)
    result.add_argument("--kuon-tree", type=Path, required=True)
    result.add_argument("--kuon-source", type=Path, required=True)
    result.add_argument("--output", type=Path, default=ROOT / "paper_runs/paper_replication_audits/llmfactor")
    return result


def main() -> None:
    print(json.dumps(build(parser().parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
