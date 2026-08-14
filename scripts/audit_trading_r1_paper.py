#!/usr/bin/env python3
"""Fail-closed paper-level audit of Trading-R1.

The arXiv v1 paper is the result authority.  The official repository is pinned
and inspected separately.  It contains only a release-soon README, so literal
paper-specification reconstructions receive no native-source or paper-result
credit.  In particular, compiling the paper and executing the stated label and
decision-reward equations do not reproduce the trained model or its backtest.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


ARXIV_URL = "https://arxiv.org/abs/2509.11420v1"
PAPER_PDF_URL = "https://arxiv.org/pdf/2509.11420v1"
PAPER_SOURCE_URL = "https://arxiv.org/e-print/2509.11420v1"
PAPER_SUBMITTED = "2025-09-14T20:13:41Z"
PAPER_PDF_SHA256 = "1b269a78756a50b9da1c86ab7ad2e9050a8a14134b057022bfca4944d51408d0"
PAPER_SOURCE_SHA256 = "74b1b5e095d2fe471ca8341ff904209186abb4dceacd15e535ca600638d46760"

SOURCE_URL = "https://github.com/TauricResearch/Trading-R1"
SOURCE_COMMIT = "57810bfb4456ba1509a2a3c6d502d3085922bf83"
SOURCE_TREE = "0785cb1cb54afe4aa1b50778c29fbc44ee3d52fb"
SOURCE_COMMIT_DATE = "2025-09-15T00:22:20-04:00"
SOURCE_ARCHIVE_SHA256 = "7994206b25a13fd4955eaea93bd25b53a948e2d83fd79e369d1a3ea62fcdb861"
SOURCE_README_SHA256 = "c093742df1f22f1d1ac444bd16efca41d6c761d67fbe25a5516172ee81c381c4"

GITHUB_REPO_API_URL = "https://api.github.com/repos/TauricResearch/Trading-R1"
GITHUB_ISSUE_URL = "https://github.com/TauricResearch/Trading-R1/issues/1"
GITHUB_REPO_SNAPSHOT_SHA256 = "1b6f53ad5b3a785566f4457a9848de18eb29e723e0d29231f34e4a634629f98a"
GITHUB_ISSUE_SNAPSHOT_SHA256 = "0e5a9721c2d15e4c80b21d3efc8e1258b1f925510376116a3eeb54218bb25bae"
GITHUB_ISSUE_COMMENTS_SHA256 = "fbdf995a3431bda83624e254fd236985d6e0b9076bf71da0c6c93905253ca359"
HF_EMPTY_SNAPSHOT_SHA256 = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
OFFICIAL_PROJECT_PAGE_URL = "https://tauric.ai/research/trading-r1"
OFFICIAL_PROJECT_PAGE_SHA256 = "df3f71029ae85a6c1b99526f862855e37b4a9b9be7a99ce098738f2050a04032"
AUDIT_DATE = "2026-08-11"
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_SNAPSHOT_SHA256 = "35459b23c7a2fcf725f51f080826eda128c53b364e3085c8afe9e94d1b5afb17"
PUBLIC_FORK_REPORTED_COUNT = 30
PUBLIC_FORK_ACCESSIBLE_COUNT = 29
PUBLIC_FORK_DIVERGENT_HEAD = "3abfc727d540d0826c34d580f197163d6618b33c"
PUBLIC_FORK_DIVERGENT_README_SHA256 = "8cfcac65df4d37cdbbe05eb8881b6d312bcce2b1a2f9190bc1f89312fa4f06d9"
PAPER_AUTHOR_NAMES = {
    "Yijia Xiao",
    "Edward Sun",
    "Tong Chen",
    "Fang Wu",
    "Di Luo",
    "Wei Wang",
}
SOURCE_CODE_SUFFIXES = {".py", ".ipynb", ".sh", ".js", ".ts", ".cpp", ".c", ".rs"}

ASSETS = ("NVDA", "AAPL", "MSFT", "AMZN", "META", "SPY")
METRICS = ("CR_pct", "SR", "HR_pct", "MDD_pct")
MODELS = (
    ("SLM", "Qwen-4B"),
    ("SLM", "GPT-4.1-nano"),
    ("SLM", "GPT-4.1-mini"),
    ("LLM", "GPT-4.1"),
    ("LLM", "LLaMA-3.3"),
    ("LLM", "LLaMA-Scout"),
    ("LLM", "Qwen3-32B"),
    ("RLM", "DeepSeek"),
    ("RLM", "O3-mini"),
    ("RLM", "O4-mini"),
    ("Ours", "Supervise Finetune"),
    ("Ours", "Reinforcement Learning"),
    ("Ours", "Trading-R1"),
)

# Values are transcribed from Tables 3 and 4 of the v1 source.  Each row is
# category, model, then CR/SR/HR/MDD for NVDA, AAPL, MSFT, AMZN, META, SPY.
RESULT_TSV = """category\tmodel\tvalues
SLM\tQwen-4B\t-1.59 -1.62 52.2 2.80 -0.81 -0.92 41.7 3.76 -1.45 -1.28 50.0 4.38 -2.90 -1.13 46.2 6.05 1.32 0.14 51.7 3.80 -1.33 -3.37 42.3 1.71
SLM\tGPT-4.1-nano\t0.76 -0.09 56.0 3.82 0.44 -0.31 51.9 3.52 -0.01 -0.95 39.3 1.60 -4.88 -2.34 40.7 6.20 -3.07 -1.69 47.8 5.19 0.04 -1.23 47.6 1.38
SLM\tGPT-4.1-mini\t0.29 -0.53 58.8 2.47 -2.14 -1.92 40.0 3.69 -2.34 -1.74 27.3 4.00 2.24 0.81 50.0 2.01 1.21 0.16 56.5 1.70 -1.03 -2.47 43.5 1.44
LLM\tGPT-4.1\t3.15 0.85 65.5 2.81 4.02 1.24 50.0 2.89 2.30 0.97 63.9 1.92 3.80 1.15 64.3 2.44 5.63 1.59 68.8 1.91 0.35 -0.74 43.3 1.21
LLM\tLLaMA-3.3\t0.65 -0.16 62.2 2.78 6.73 1.78 63.6 2.40 1.58 0.54 58.1 1.59 -0.89 -0.61 58.6 6.02 3.21 1.01 62.5 2.55 1.27 0.27 64.7 1.35
LLM\tLLaMA-Scout\t-1.96 -1.64 31.8 2.90 2.03 0.58 59.4 3.21 -0.29 -1.33 36.8 1.44 -3.47 -1.48 35.7 5.95 3.51 0.92 53.1 2.78 -1.34 -3.36 36.0 1.65
LLM\tQwen3-32B\t1.74 0.27 64.5 2.80 0.62 -0.12 33.3 3.39 2.14 1.29 65.6 0.82 5.61 2.12 64.3 1.89 -1.23 -0.58 46.2 6.61 2.32 1.87 70.4 0.65
RLM\tDeepSeek\t-0.79 -0.66 50.0 3.66 0.68 -0.13 55.3 4.78 -0.38 -1.01 33.3 2.06 -1.15 -1.14 50.0 3.00 1.26 0.12 40.5 2.80 -1.15 -1.82 36.4 2.00
RLM\tO3-mini\t-2.97 -1.48 46.9 5.33 -1.89 -1.13 50.0 3.72 1.19 0.15 47.4 1.19 -3.15 -1.37 38.2 5.50 2.05 0.53 73.1 2.64 0.80 -0.25 57.6 0.62
RLM\tO4-mini\t-0.99 -0.83 43.2 3.61 -3.19 -1.36 50.0 7.88 -1.72 -1.77 48.5 2.35 -2.48 -1.28 51.6 4.83 -0.45 -0.80 53.6 2.68 -0.30 -1.34 36.8 1.72
Ours\tSupervise Finetune\t7.42 2.72 72.5 2.01 -2.37 -1.27 45.2 5.20 -0.24 -0.64 56.1 3.87 1.93 0.36 60.6 4.28 2.52 0.54 55.9 2.93 1.78 0.86 58.1 1.15
Ours\tReinforcement Learning\t3.27 1.25 62.5 2.73 4.04 1.14 57.1 3.02 -0.18 -0.81 45.7 1.66 -0.05 -0.29 52.5 4.84 -0.18 -0.36 44.4 5.11 1.85 1.00 67.6 0.69
Ours\tTrading-R1\t8.08 2.72 70.0 3.80 5.82 1.80 63.6 3.68 2.38 0.87 60.4 1.90 5.39 1.72 63.0 3.20 5.12 0.86 50.0 4.65 3.34 1.60 64.0 1.52
"""

FIGURE_ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "SPY")
FIGURE_VALUES = {
    "SLM": (-1.048, -0.888, -0.463, -1.326, -0.748, -2.358),
    "LLM": (0.871, 0.296, 0.734, 0.368, -0.170, -0.488),
    "RLM": (-0.873, -1.262, -0.047, -0.873, -0.988, -1.134),
    "Trading-SFT": (-1.266, 0.359, 0.536, -0.635, 2.725, 0.858),
    "Trading-RFT": (1.137, -0.294, -0.357, -0.811, 1.252, 0.997),
    "Trading-R1": (1.804, 1.716, 0.856, 0.873, 1.881, 1.600),
}

ACTIONS = ("STRONG SELL", "SELL", "HOLD", "BUY", "STRONG BUY")
DECISION_MATRIX = np.array(
    [
        [1.00, 0.75, -1.25, -2.00, -2.25],
        [0.75, 1.00, -0.75, -1.50, -2.00],
        [-1.50, -1.00, 1.00, -1.00, -1.50],
        [-1.75, -1.25, -0.75, 1.00, 0.75],
        [-2.00, -1.50, -1.25, 0.75, 1.00],
    ],
    dtype=float,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return proc.stdout


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def result_records() -> list[dict[str, Any]]:
    parsed = list(csv.DictReader(io.StringIO(RESULT_TSV), delimiter="\t"))
    records: list[dict[str, Any]] = []
    for row in parsed:
        values = [float(value) for value in row["values"].split()]
        if len(values) != len(ASSETS) * len(METRICS):
            raise ValueError(f"wrong result width for {row['model']}")
        record: dict[str, Any] = {"category": row["category"], "model": row["model"]}
        for offset, asset in enumerate(ASSETS):
            for metric_offset, metric in enumerate(METRICS):
                record[(asset, metric)] = values[offset * 4 + metric_offset]
        records.append(record)
    if [(r["category"], r["model"]) for r in records] != list(MODELS):
        raise ValueError("paper result model ordering drifted")
    return records


def paper_table_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in result_records():
        for asset in ASSETS:
            table = "Table 3" if asset in ASSETS[:3] else "Table 4"
            for metric in METRICS:
                value = record[(asset, metric)]
                rows.append(
                    {
                        "paper_table": table,
                        "category": record["category"],
                        "model": record["model"],
                        "asset": asset,
                        "metric": metric,
                        "paper_value": f"{value:.2f}" if metric != "HR_pct" else f"{value:.1f}",
                        "native_reproduced_value": "",
                        "status": "not_reproduced_official_code_model_data_and_predictions_not_released",
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 312:
        raise ValueError("Trading-R1 result table census must contain 312 cells")
    return rows


def _table_sr(category: str, asset: str) -> float:
    records = result_records()
    direct = {
        "Trading-SFT": "Supervise Finetune",
        "Trading-RFT": "Reinforcement Learning",
        "Trading-R1": "Trading-R1",
    }
    if category in direct:
        record = next(row for row in records if row["model"] == direct[category])
        return float(record[(asset, "SR")])
    values = [
        float(row[(asset, "SR")])
        for row in records
        if row["category"] == category
    ]
    return float(np.mean(values))


def figure_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for category, values in FIGURE_VALUES.items():
        for asset, figure_value in zip(FIGURE_ASSETS, values):
            derived = _table_sr(category, asset)
            consistent = abs(figure_value - derived) <= 0.006
            rows.append(
                {
                    "paper_figure": "Figure 5 Sharpe Ratio Heatmap",
                    "category": category,
                    "asset": asset,
                    "paper_figure_value": f"{figure_value:.3f}",
                    "table_derived_sr_from_rounded_cells": f"{derived:.6f}",
                    "internally_consistent_with_table_precision": consistent,
                    "native_reproduced_value": "",
                    "status": (
                        "paper_internal_match_only_not_native_reproduction"
                        if consistent
                        else "paper_internal_conflict_and_not_natively_reproduced"
                    ),
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 36:
        raise ValueError("Trading-R1 heatmap must contain 36 annotated values")
    return rows


def literal_label_algorithm(prices: Sequence[float]) -> pd.DataFrame:
    """Execute Algorithm S1 literally; this is not released native code."""
    price = pd.Series(prices, dtype=float, name="price")
    if len(price) == 0 or (price <= 0).any() or not np.isfinite(price).all():
        raise ValueError("prices must be a non-empty finite positive sequence")
    ema = price.ewm(span=3).mean()
    weighted = pd.Series(0.0, index=price.index, dtype=float)
    for horizon, weight in zip((3, 7, 15), (0.3, 0.5, 0.2)):
        returns = (ema - ema.shift(horizon)) / ema.shift(horizon)
        volatility = returns.rolling(20).std()
        weighted = weighted + weight * (returns / volatility)
    valid = weighted.dropna()
    labels = pd.Series(pd.NA, index=price.index, dtype="object")
    thresholds: dict[float, float] = {}
    if not valid.empty:
        quantiles = valid.quantile([0.03, 0.15, 0.53, 0.85])
        thresholds = {float(k): float(v) for k, v in quantiles.items()}
        values = weighted[weighted.notna()]
        labels.loc[values.index] = np.select(
            [
                values >= thresholds[0.85],
                values >= thresholds[0.53],
                values >= thresholds[0.15],
                values >= thresholds[0.03],
            ],
            ["STRONG BUY", "BUY", "HOLD", "SELL"],
            default="STRONG SELL",
        )
    frame = pd.DataFrame(
        {"price": price, "ema": ema, "weighted_signal": weighted, "label": labels}
    )
    frame.attrs["thresholds"] = thresholds
    return frame


def decision_reward(prediction: str, truth: str, scale: float = 1.0) -> float:
    if prediction not in ACTIONS or truth not in ACTIONS:
        raise ValueError("prediction and truth must use the five paper actions")
    if scale < 0 or not math.isfinite(scale):
        raise ValueError("scale must be finite and non-negative")
    return float(DECISION_MATRIX[ACTIONS.index(prediction), ACTIONS.index(truth)] * scale)


def specification_reconstruction_diagnostics() -> list[dict[str, Any]]:
    base_returns = np.array(
        [0.002 + 0.012 * np.sin(i / 4) + 0.006 * np.cos(i / 9) for i in range(160)]
    )
    base_prices = 100 * np.exp(np.cumsum(base_returns))
    extension_returns = np.array([0.04 * np.sin(i / 2) + 0.025 for i in range(90)])
    extension_prices = base_prices[-1] * np.exp(np.cumsum(extension_returns))
    prefix = literal_label_algorithm(base_prices)
    extended = literal_label_algorithm(np.r_[base_prices, extension_prices])
    valid = prefix["label"].notna()
    valid_index = prefix.index[valid]
    changed = int(
        (
            prefix.loc[valid_index, "label"]
            != extended.loc[valid_index, "label"]
        ).sum()
    )
    valid_count = int(valid.sum())
    return [
        {
            "diagnostic": "literal_algorithm_prefix_instability",
            "observed_value": changed,
            "denominator": valid_count,
            "status": "future_extension_changes_past_labels_via_full_sample_quantiles",
            "native_source_execution": False,
            "paper_result_credit": False,
        },
        {
            "diagnostic": "false_bullish_extreme_penalty_prediction_SB_truth_SS",
            "observed_value": f"{decision_reward('STRONG BUY', 'STRONG SELL'):.2f}",
            "denominator": "",
            "status": "matrix_penalty_is_minus_2_not_claimed_minus_2_25",
            "native_source_execution": False,
            "paper_result_credit": False,
        },
        {
            "diagnostic": "false_bearish_extreme_penalty_prediction_SS_truth_SB",
            "observed_value": f"{decision_reward('STRONG SELL', 'STRONG BUY'):.2f}",
            "denominator": "",
            "status": "matrix_penalty_is_minus_2_25_so_matrix_opposes_false_bullish_claim",
            "native_source_execution": False,
            "paper_result_credit": False,
        },
        {
            "diagnostic": "target_class_percentages_implied_by_quantiles",
            "observed_value": "15/32/38/12/3",
            "denominator": "percent_StrongBuy/Buy/Hold/Sell/StrongSell",
            "status": "matches_paper_target_distribution_in_continuous_no_tie_limit",
            "native_source_execution": False,
            "paper_result_credit": False,
        },
    ]


def mechanism_conformance() -> list[dict[str, Any]]:
    rows = [
        ("Tauric-TR1-DB raw corpus", "100k samples; 14 tickers; 2024-01-01--2025-05-31", "not_released"),
        ("daily multimodal input assembly", "news, technicals, fundamentals, sentiment, macro", "not_released"),
        ("point-in-time source snapshots", "source data as available on each day", "not_released"),
        ("20 shuffled modality variations", "about 20 variants per ticker-day", "not_released"),
        ("token filtering and compression", "regex plus LLM relevance filtering", "not_released"),
        ("literal volatility label formula", "Algorithm S1 reconstructed in this audit", "paper_spec_reconstructed_only"),
        ("forward-return label claim", "prose says forward; formula uses lagged EMA", "paper_internal_conflict"),
        ("label quantile fitting boundary", "training-only threshold fit not specified", "underspecified"),
        ("Qwen3-4B backbone", "model family named", "checkpoint_not_released"),
        ("Stage I SFT", "examples, memories, LoRA", "training_data_and_config_not_released"),
        ("Stage I RFT", "structure reward", "training_code_and_config_not_released"),
        ("Stage I self-distill augmentation", "reject-sampled cases", "pipeline_not_released"),
        ("Stage II SFT", "evidence-based reasoning", "training_data_and_config_not_released"),
        ("Stage II RFT", "opinion/quote/source reward", "training_code_and_parser_not_released"),
        ("Stage II self-distill augmentation", "professional faithful claims", "pipeline_not_released"),
        ("Stage III SFT", "recommendation patterns", "training_data_and_config_not_released"),
        ("Stage III RFT", "decision reward", "training_code_and_config_not_released"),
        ("Stage III self-distill augmentation", "directionally correct cases", "pipeline_not_released"),
        ("structure reward", "formula disclosed; exact XML/markdown parser absent", "underspecified"),
        ("evidence reward", "formula disclosed; exact extraction parser absent", "underspecified"),
        ("decision reward matrix", "matrix reconstructed in this audit", "paper_spec_reconstructed_only"),
        ("reward aggregation", "lambda values absent and decision lambda appears twice", "underspecified"),
        ("GRPO optimization", "generic objective disclosed", "hyperparameters_and_code_not_released"),
        ("SFT LoRA", "hardware disclosed", "rank_alpha_dropout_optimizer_steps_absent"),
        ("trained model checkpoints", "Trading-R1/SFT/RFT variants", "not_released"),
        ("baseline model snapshots", "names only", "exact_versions_and_access_dates_absent"),
        ("inference prompts", "standardized snapshot described", "not_released"),
        ("decoding and retries", "no temperature/top-p/seeds/malformed-output policy", "not_specified"),
        ("evaluation panel", "six result assets named by Tables 3--4", "inputs_not_released"),
        ("held-out split", "June--August 2024 claimed excluded", "split_manifest_not_released"),
        ("five actions to weights", "mapping claimed", "weights_not_specified"),
        ("holding rule", "on the order of one week", "exact_horizon_not_specified"),
        ("entry exit and rebalance", "strictly causal backtest claimed", "not_specified"),
        ("short leverage cash constraints", "long-short strategy claimed", "not_specified"),
        ("transaction costs and slippage", "no evaluation cost model", "not_specified"),
        ("Sharpe risk-free conversion", "4% annual stated but per-period conversion absent", "ambiguous"),
        ("raw model outputs and decisions", "needed for HR and return paths", "not_released"),
        ("equity curves and trade ledger", "needed for CR/SR/MDD", "not_released"),
        ("metric and table generator", "formulas only", "not_released"),
    ]
    return [
        {
            "mechanism": mechanism,
            "paper_specification": specification,
            "audit_status": status,
            "verified_in_released_native_source": False,
            "paper_spec_reconstruction_credit": status == "paper_spec_reconstructed_only",
            "paper_result_credit": False,
        }
        for mechanism, specification, status in rows
    ]


def specification_gaps() -> list[dict[str, Any]]:
    gaps = [
        ("G01", "model", "Trading-R1, SFT, and RFT checkpoints are not public", "blocking"),
        ("G02", "data", "Tauric-TR1-DB and exact evaluation prompts are not public", "blocking"),
        ("G03", "code", "official repository contains no executable source", "blocking"),
        ("G04", "predictions", "per-date baseline and Trading-R1 actions are absent", "blocking"),
        ("G05", "backtest", "action weights, entry/exit, rebalance, cash, leverage, and costs are absent", "blocking"),
        ("G06", "training", "LoRA/GRPO hyperparameters, sample counts, weights, seeds, and checkpoints are absent", "blocking"),
        ("G07", "models", "baseline model identifiers, API snapshots, prompts, and decoding are absent", "blocking"),
        ("G08", "split", "the held-out split manifest is absent although evaluation dates lie inside collection dates", "blocking"),
        ("G09", "labels", "prose says forward return but Algorithm S1 computes a lagged return", "blocking"),
        ("G10", "labels", "full-sample quantiles can change past labels when future observations are appended", "blocking"),
        ("G11", "reward", "reward lambdas are absent and lambda_dec is applied in both component and aggregate formulas", "blocking"),
        ("G12", "reward", "decision-matrix orientation contradicts the stated false-bullish asymmetry", "blocking"),
        ("G13", "metrics", "4% annual risk-free rate is not converted to an explicit daily rate", "blocking"),
        ("G14", "results", "NVDA Trading-R1 Sharpe is 2.72 in Table 3 but 1.881 in Figure 5 and 1.88 in prose", "blocking"),
        ("G15", "release", "official project page says released while linked repository still says releasing soon", "blocking"),
    ]
    return [
        {"gap_id": gap_id, "area": area, "gap": gap, "severity": severity}
        for gap_id, area, gap, severity in gaps
    ]


def internal_checks() -> list[dict[str, Any]]:
    figure = figure_rows()
    diagnostics = specification_reconstruction_diagnostics()
    changed = next(row for row in diagnostics if row["diagnostic"] == "literal_algorithm_prefix_instability")
    return [
        {"check": "result_table_census", "paper_claim": "13 models x 6 assets x 4 metrics", "observed": len(paper_table_rows()), "status": "confirmed", "paper_result_credit": False},
        {"check": "heatmap_annotation_census", "paper_claim": "6 categories x 6 assets", "observed": len(figure), "status": "confirmed", "paper_result_credit": False},
        {"check": "heatmap_table_internal_agreement", "paper_claim": "Figure 5 summarizes Tables 3--4 Sharpe ratios", "observed": f"{sum(row['internally_consistent_with_table_precision'] for row in figure)}/36", "status": "one_conflict", "paper_result_credit": False},
        {"check": "trading_r1_nvda_sharpe", "paper_claim": "one paper-level Sharpe value", "observed": "Table 3=2.72; Figure 5=1.881; prose=1.88", "status": "paper_internal_conflict", "paper_result_credit": False},
        {"check": "label_return_direction", "paper_claim": "forward returns over 3/7/15 days", "observed": "(EMA-EMA.shift(tau))/EMA.shift(tau) is a trailing return", "status": "paper_internal_conflict", "paper_result_credit": False},
        {"check": "label_threshold_causality", "paper_claim": "strictly causal evaluation", "observed": f"{changed['observed_value']}/{changed['denominator']} earlier synthetic labels change after future extension", "status": "literal_formula_is_not_prefix_stable", "paper_result_credit": False},
        {"check": "decision_penalty_orientation", "paper_claim": "false bullish receives the heavier extreme penalty", "observed": "prediction SB/truth SS=-2.00; prediction SS/truth SB=-2.25", "status": "paper_internal_conflict", "paper_result_credit": False},
        {"check": "training_evaluation_calendar", "paper_claim": "2024-06-01--2024-08-31 is held out", "observed": "evaluation interval lies inside 2024-01-01--2025-05-31 collection interval; no split manifest", "status": "claim_not_verifiable", "paper_result_credit": False},
        {"check": "evaluation_asset_narrative", "paper_claim": "examples include AAPL, GOOGL, AMZN, SPY", "observed": "tables report NVDA, AAPL, MSFT, AMZN, META, SPY and no GOOGL", "status": "paper_narrative_table_mismatch", "paper_result_credit": False},
        {"check": "reward_lambda_application", "paper_claim": "lambda_dec scales the decision component", "observed": "lambda_dec appears inside R_decision and again in R_investment", "status": "ambiguous_possible_double_scaling", "paper_result_credit": False},
        {"check": "official_release_claim", "paper_claim": "official project page says Terminal is released", "observed": "linked one-file repository says Releasing soon", "status": "official_sources_conflict", "paper_result_credit": False},
    ]


def source_archive_inventory(paper_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with tarfile.open(paper_root / "source.tar", "r:*") as archive:
        for member in sorted((m for m in archive.getmembers() if m.isfile()), key=lambda m: m.name):
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"cannot read archive member {member.name}")
            data = stream.read()
            rows.append(
                {
                    "path": member.name,
                    "bytes": len(data),
                    "sha256": bytes_sha256(data),
                    "artifact_type": "paper_source_not_executable_system_source",
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 29:
        raise ValueError("expected 29 files in arXiv source archive")
    return rows


def released_source_inventory(source_root: Path) -> list[dict[str, Any]]:
    paths = run_git(source_root, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    rows: list[dict[str, Any]] = []
    for path in paths:
        data = run_git(source_root, "show", f"HEAD:{path}", binary=True)
        rows.append(
            {
                "path": path,
                "bytes": len(data),
                "sha256": bytes_sha256(data),
                "source_code": Path(path).suffix.lower() in SOURCE_CODE_SUFFIXES,
                "native_result_artifact": False,
            }
        )
    return rows


def public_fork_audit(
    source_root: Path,
    paper_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Audit every accessible public fork ref without granting lineage by name."""
    snapshot = json.loads(
        (paper_root / "public_fork_snapshot.json").read_text(encoding="utf-8")
    )
    if len(snapshot) != PUBLIC_FORK_ACCESSIBLE_COUNT:
        raise ValueError(f"Trading-R1 accessible fork count changed: {len(snapshot)}")
    expected_refs: dict[str, tuple[str, str, str]] = {}
    tag_refs = 0
    for repository in snapshot:
        full_name = repository["full_name"]
        owner = full_name.split("/", 1)[0]
        if repository["default_branch"] not in repository["branches"]:
            raise ValueError(f"Trading-R1 fork default branch missing: {full_name}")
        tag_refs += len(repository["tags"])
        for branch, head in repository["branches"].items():
            ref = f"refs/remotes/forks/{owner}/{branch}"
            if ref in expected_refs:
                raise ValueError(f"duplicate Trading-R1 fork ref: {ref}")
            expected_refs[ref] = (full_name, branch, head)
    if len(expected_refs) != 29 or tag_refs != 0:
        raise ValueError("Trading-R1 fork branch/tag surface changed")

    observed_refs = {
        ref: run_git(source_root, "rev-parse", ref).strip()
        for ref in run_git(
            source_root,
            "for-each-ref",
            "--format=%(refname)",
            "refs/remotes/forks",
        ).splitlines()
    }
    expected_heads = {ref: values[2] for ref, values in expected_refs.items()}
    if observed_refs != expected_heads:
        raise ValueError(f"Trading-R1 fetched fork refs changed: {observed_refs}")

    payload_path_pattern = re.compile(
        r"(^|/)(models?|datasets?|configs?|predictions?|trades?|orders?|returns?|"
        r"results?|outputs?|checkpoints?|trajectories?|actions?|ratings?)(/|$)",
        flags=re.IGNORECASE,
    )
    branch_rows: list[dict[str, Any]] = []
    for ref, (repository, branch, head) in sorted(expected_refs.items()):
        ahead = int(run_git(source_root, "rev-list", "--count", head, "--not", SOURCE_COMMIT).strip())
        behind = int(run_git(source_root, "rev-list", "--count", f"{head}..{SOURCE_COMMIT}").strip())
        paths = run_git(source_root, "ls-tree", "-r", "--name-only", head).splitlines()
        source_paths = [path for path in paths if Path(path).suffix.lower() in SOURCE_CODE_SUFFIXES]
        payload_paths = [path for path in paths if payload_path_pattern.search(path)]
        if behind != 0 or ahead not in {0, 4}:
            raise ValueError(f"Trading-R1 fork relationship changed for {ref}")
        branch_rows.append({
            "repository": repository,
            "url": f"https://github.com/{repository}",
            "branch": branch,
            "head_commit": head,
            "relation_to_official_head": (
                "exact_official_head" if head == SOURCE_COMMIT else "descendant_of_official_head"
            ),
            "commits_ahead_of_official_history": ahead,
            "commits_behind_official_head": behind,
            "current_tracked_files": len(paths),
            "current_source_code_files": len(source_paths),
            "current_native_result_payload_paths": len(payload_paths),
            "native_trading_r1_pipeline_found": False,
            "paper_result_credit": False,
        })

    fork_heads = sorted(set(observed_refs.values()))
    official_objects = set(
        run_git(source_root, "rev-list", "--objects", "--no-object-names", SOURCE_COMMIT).splitlines()
    )
    fork_objects = set(
        run_git(source_root, "rev-list", "--objects", "--no-object-names", *fork_heads).splitlines()
    )
    unique_objects = sorted(fork_objects - official_objects)
    object_counts = {"commit": 0, "tree": 0, "blob": 0}
    for object_id in unique_objects:
        kind = run_git(source_root, "cat-file", "-t", object_id).strip()
        if kind not in object_counts:
            raise ValueError(f"unexpected Trading-R1 fork object type: {kind}")
        object_counts[kind] += 1
    if object_counts != {"commit": 4, "tree": 4, "blob": 4}:
        raise ValueError(f"Trading-R1 unique fork objects changed: {object_counts}")

    unique_commits = sorted(
        set(run_git(source_root, "rev-list", *fork_heads, "--not", SOURCE_COMMIT).splitlines())
    )
    if len(unique_commits) != 4:
        raise ValueError(f"Trading-R1 unique fork commits changed: {unique_commits}")
    commit_rows: list[dict[str, Any]] = []
    all_changed_paths: set[str] = set()
    for commit in unique_commits:
        metadata = run_git(
            source_root,
            "show",
            "-s",
            "--format=%aI%x00%an%x00%s",
            commit,
        ).rstrip("\n").split("\x00", 2)
        if len(metadata) != 3:
            raise ValueError(f"Trading-R1 fork metadata parse failed: {commit}")
        authored_at, author_name, subject = metadata
        changed_paths = sorted(
            set(
                run_git(
                    source_root,
                    "diff-tree",
                    "--root",
                    "-m",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    commit,
                ).splitlines()
            )
            - {""}
        )
        source_paths = [path for path in changed_paths if Path(path).suffix.lower() in SOURCE_CODE_SUFFIXES]
        payload_paths = [path for path in changed_paths if payload_path_pattern.search(path)]
        all_changed_paths.update(changed_paths)
        commit_rows.append({
            "commit": commit,
            "authored_at": authored_at,
            "author_name": author_name,
            "subject": subject,
            "changed_paths": len(changed_paths),
            "changed_source_code_paths": len(source_paths),
            "changed_native_result_payload_paths": len(payload_paths),
            "authored_after_paper_submission": authored_at[:10] > PAPER_SUBMITTED[:10],
            "exact_paper_author_display_name_match": author_name in PAPER_AUTHOR_NAMES,
            "native_trading_r1_pipeline_found": False,
            "paper_result_credit": False,
        })
    commit_rows.sort(key=lambda row: (row["authored_at"], row["commit"]))
    divergent_readme = run_git(
        source_root, "show", f"{PUBLIC_FORK_DIVERGENT_HEAD}:README.md", binary=True
    )
    if (
        all_changed_paths != {"README.md"}
        or len(divergent_readme) != 157
        or bytes_sha256(divergent_readme) != PUBLIC_FORK_DIVERGENT_README_SHA256
        or not all(row["authored_after_paper_submission"] for row in commit_rows)
        or any(row["exact_paper_author_display_name_match"] for row in commit_rows)
        or any(row["changed_source_code_paths"] for row in commit_rows)
        or any(row["changed_native_result_payload_paths"] for row in commit_rows)
    ):
        raise ValueError("Trading-R1 divergent fork evidence boundary changed")

    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_reported_forks": PUBLIC_FORK_REPORTED_COUNT,
        "accessible_public_forks": len(snapshot),
        "inaccessible_or_unlisted_reported_forks": PUBLIC_FORK_REPORTED_COUNT - len(snapshot),
        "accessible_branch_refs": len(branch_rows),
        "public_tag_refs": tag_refs,
        "unique_heads": len(fork_heads),
        "official_head_exact_refs": sum(
            row["relation_to_official_head"] == "exact_official_head" for row in branch_rows
        ),
        "divergent_unique_heads": len(set(fork_heads) - {SOURCE_COMMIT}),
        "unique_commits_beyond_official_history": len(unique_commits),
        "unique_trees_beyond_official_history": object_counts["tree"],
        "unique_blobs_beyond_official_history": object_counts["blob"],
        "unique_changed_paths": len(all_changed_paths),
        "current_source_code_files_across_divergent_heads": 0,
        "current_native_result_payload_paths_across_divergent_heads": 0,
        "post_submission_unique_commits": sum(
            row["authored_after_paper_submission"] for row in commit_rows
        ),
        "exact_paper_author_display_name_attributions": sum(
            row["exact_paper_author_display_name_match"] for row in commit_rows
        ),
        "native_trading_r1_pipelines_found": 0,
        "paper_result_credit": False,
        "interpretation": (
            "Twenty-eight fork refs exactly duplicate the official one-file placeholder. "
            "The only divergent fork adds four post-paper README-only edits and no code, "
            "model, dataset, configuration, prediction, trade, return, or result payload."
        ),
    }
    expected_counts = {
        "accessible_public_forks": 29,
        "accessible_branch_refs": 29,
        "unique_heads": 2,
        "official_head_exact_refs": 28,
        "divergent_unique_heads": 1,
        "unique_commits_beyond_official_history": 4,
        "unique_changed_paths": 1,
        "post_submission_unique_commits": 4,
    }
    if any(summary[key] != value for key, value in expected_counts.items()):
        raise ValueError(f"Trading-R1 public fork census changed: {summary}")
    return branch_rows, commit_rows, summary


def public_release_rows(paper_root: Path, source_root: Path) -> list[dict[str, Any]]:
    repo = json.loads((paper_root / "github_repo.json").read_text(encoding="utf-8"))
    issue = json.loads((paper_root / "github_issue_1.json").read_text(encoding="utf-8"))
    comments = json.loads((paper_root / "github_issue_1_comments.json").read_text(encoding="utf-8"))
    hf_models = json.loads((paper_root / "hf_models.json").read_text(encoding="utf-8"))
    hf_datasets = json.loads((paper_root / "hf_datasets.json").read_text(encoding="utf-8"))
    return [
        {"source": "official_git_repository", "url": SOURCE_URL, "observed_count": len(released_source_inventory(source_root)), "status": "one_readme_only", "native_result_credit": False},
        {"source": "official_git_commits", "url": SOURCE_URL, "observed_count": int(run_git(source_root, "rev-list", "--count", "HEAD").strip()), "status": "one_initial_commit", "native_result_credit": False},
        {"source": "official_git_tags", "url": SOURCE_URL, "observed_count": len(run_git(source_root, "tag", "--list").splitlines()), "status": "none", "native_result_credit": False},
        {"source": "official_github_issue", "url": GITHUB_ISSUE_URL, "observed_count": 1, "status": f"{issue['state']}; release request has {len(comments)} non-author update request", "native_result_credit": False},
        {"source": "official_huggingface_models", "url": "https://huggingface.co/api/models?author=TauricResearch", "observed_count": len(hf_models), "status": "none", "native_result_credit": False},
        {"source": "official_huggingface_datasets", "url": "https://huggingface.co/api/datasets?author=TauricResearch", "observed_count": len(hf_datasets), "status": "none", "native_result_credit": False},
        {"source": "official_project_page_release_statement", "url": OFFICIAL_PROJECT_PAGE_URL, "observed_count": 1, "status": "says_released_but_links_placeholder_repository", "native_result_credit": False},
        {"source": "github_metadata", "url": GITHUB_REPO_API_URL, "observed_count": repo["size"], "status": f"pushed_at={repo['pushed_at']}; default_branch={repo['default_branch']}", "native_result_credit": False},
    ]


def _git_archive_sha256(source_root: Path) -> str:
    data = run_git(source_root, "archive", "--format=tar", "HEAD", binary=True)
    return bytes_sha256(data)


def _parse_table_blocks(source_root: Path) -> list[list[list[float]]]:
    text = (source_root / "sections/5.results.tex").read_text(encoding="utf-8")
    blocks = re.findall(r"\\begin\{table\}.*?\\end\{table\}", text, flags=re.S)
    parsed: list[list[list[float]]] = []
    for block in blocks[:2]:
        rows: list[list[float]] = []
        for line in block.splitlines():
            numbers = [float(value) for value in re.findall(r"(?<![A-Za-z])-?\d+(?:\.\d+)?", line)]
            # A leading ``\\multirow{3}`` contributes an extra numeric token
            # on the first row of each category; the 12 metric cells are last.
            if "&" in line and len(numbers) >= 12:
                rows.append(numbers[-12:])
        parsed.append(rows)
    return parsed


def validate_paper_values(extracted_source: Path) -> None:
    parsed = _parse_table_blocks(extracted_source)
    if [len(block) for block in parsed] != [13, 13]:
        raise ValueError("could not parse all 13 rows from each paper result table")
    records = result_records()
    for block_index, assets in enumerate((ASSETS[:3], ASSETS[3:])):
        for row_index, record in enumerate(records):
            expected = [record[(asset, metric)] for asset in assets for metric in METRICS]
            if not np.allclose(parsed[block_index][row_index], expected, atol=0, rtol=0):
                raise ValueError(f"paper result transcription drift for {record['model']}")
    figure_path = extracted_source / "figures/sr_heatmap.pdf"
    text = subprocess.run(
        ["pdftotext", "-layout", str(figure_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    observed = Counter(re.findall(r"-?\d+\.\d{3}", text))
    expected = Counter(f"{value:.3f}" for values in FIGURE_VALUES.values() for value in values)
    if any(observed[value] < count for value, count in expected.items()):
        raise ValueError("paper Figure 5 transcription drift")


def validate_primary_inputs(source_root: Path, paper_root: Path) -> None:
    expected_hashes = {
        "paper.pdf": PAPER_PDF_SHA256,
        "source.tar": PAPER_SOURCE_SHA256,
        "github_repo.json": GITHUB_REPO_SNAPSHOT_SHA256,
        "github_issue_1.json": GITHUB_ISSUE_SNAPSHOT_SHA256,
        "github_issue_1_comments.json": GITHUB_ISSUE_COMMENTS_SHA256,
        "hf_models.json": HF_EMPTY_SNAPSHOT_SHA256,
        "hf_datasets.json": HF_EMPTY_SNAPSHOT_SHA256,
        "official_project_page.html": OFFICIAL_PROJECT_PAGE_SHA256,
        "public_fork_snapshot.json": PUBLIC_FORK_SNAPSHOT_SHA256,
    }
    for name, expected in expected_hashes.items():
        path = paper_root / name
        if sha256(path) != expected:
            raise ValueError(f"primary snapshot hash mismatch: {name}")
    if run_git(source_root, "rev-parse", "HEAD").strip() != SOURCE_COMMIT:
        raise ValueError("official repository commit drift")
    if run_git(source_root, "rev-parse", "HEAD^{tree}").strip() != SOURCE_TREE:
        raise ValueError("official repository tree drift")
    if _git_archive_sha256(source_root) != SOURCE_ARCHIVE_SHA256:
        raise ValueError("official repository archive drift")
    inventory = released_source_inventory(source_root)
    if len(inventory) != 1 or inventory[0]["path"] != "README.md":
        raise ValueError("official repository is no longer the pinned one-file placeholder")
    if inventory[0]["sha256"] != SOURCE_README_SHA256:
        raise ValueError("official README drift")
    if run_git(source_root, "rev-list", "--count", "HEAD").strip() != "1":
        raise ValueError("official repository history drift")
    if run_git(source_root, "tag", "--list").strip():
        raise ValueError("unexpected official release tag")
    if json.loads((paper_root / "hf_models.json").read_text()) != []:
        raise ValueError("official Hugging Face model release snapshot is no longer empty")
    if json.loads((paper_root / "hf_datasets.json").read_text()) != []:
        raise ValueError("official Hugging Face dataset release snapshot is no longer empty")
    with tempfile.TemporaryDirectory(prefix="trading-r1-validate-") as temporary:
        extracted = Path(temporary)
        with tarfile.open(paper_root / "source.tar", "r:*") as archive:
            archive.extractall(extracted, filter="data")
        validate_paper_values(extracted)


def compile_paper(paper_root: Path) -> dict[str, Any]:
    executable = shutil.which("pdflatex")
    if not executable:
        return {"attempted": False, "reason": "pdflatex_not_available", "paper_result_credit": False}
    with tempfile.TemporaryDirectory(prefix="trading-r1-paper-") as temporary:
        work = Path(temporary)
        with tarfile.open(paper_root / "source.tar", "r:*") as archive:
            archive.extractall(work, filter="data")
        exits: list[int] = []
        logs: list[str] = []
        for _ in range(2):
            proc = subprocess.run(
                [executable, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                cwd=work,
                capture_output=True,
                text=True,
            )
            exits.append(proc.returncode)
            logs.append(proc.stdout + proc.stderr)
            if proc.returncode:
                break
        output_pdf = work / "main.pdf"
        pages = 0
        if output_pdf.exists() and shutil.which("pdfinfo"):
            info = subprocess.run(["pdfinfo", str(output_pdf)], check=True, capture_output=True, text=True).stdout
            match = re.search(r"^Pages:\s+(\d+)", info, flags=re.M)
            pages = int(match.group(1)) if match else 0
        warning_lines = sum(
            any(token in line for token in ("Warning", "Overfull", "Underfull"))
            for line in logs[-1].splitlines()
        ) if logs else 0
        return {
            "attempted": True,
            "compiler": executable,
            "exit_codes": exits,
            "exit_code": exits[-1],
            "passes": len(exits),
            "pages": pages,
            "second_pass_warning_or_box_lines": warning_lines,
            "paper_result_credit": False,
            "boundary": "typesetting_reproduction_only_not_native_system_execution",
        }


def readme_text(manifest: Mapping[str, Any]) -> str:
    return f"""# Trading-R1 paper replication audit

Authority: arXiv v1, submitted {PAPER_SUBMITTED}. Audit snapshot: {AUDIT_DATE}.

## Honest result

The paper specification is partially reconstructable, but the Trading-R1 system and its published backtest are not reproducible from the official release. The official repository still contains one 49-byte release-soon README and no code, model, dataset, configuration, prediction, trade, or return artifact. The TauricResearch Hugging Face model and dataset queries are both empty in the pinned audit snapshot.

The {PUBLIC_FORK_CENSUS_DATE} fork census also exhausts all 29 accessible public forks and all 29 branch refs; GitHub reports 30 forks, so one reported fork is inaccessible or absent from the returned public list. Twenty-eight refs exactly equal the official placeholder head. The sole divergent head adds four post-paper commits, four trees, and four blobs, but all four commits only edit `README.md`; the final tree still has one 157-byte README and no source code or native result payload. Its commit author display name does not exactly match a paper author. The public fork surface therefore supplies no Trading-R1 model, data, configuration, prediction, trade, return, or result evidence.

Paper-result credit is **0/{manifest['published_numeric_result_units_total']} numeric display units**: 0/{manifest['paper_table_cells_total']} cells from Tables 3--4 and 0/{manifest['paper_figure_numeric_units_total']} annotations from Figure 5. Compiling the 58-page paper and executing literal paper equations are not native result reproduction.

## What this audit did reproduce

- Parsed and source-checked all 312 table cells (13 models × 6 assets × 4 metrics).
- Extracted all 36 annotated Sharpe values from Figure 5. Only 35/36 are internally compatible with the rounded table cells; Trading-R1/NVDA is 2.72 in Table 3 but 1.881 in Figure 5 and 1.88 in prose.
- Executed a literal reconstruction of Algorithm S1 and the published decision matrix on synthetic diagnostics. These are labeled paper-spec reconstructions, never released-source executions.
- Compiled the pinned arXiv source twice to 58 pages.

## Material blockers and inconsistencies

- Algorithm S1 is described as using forward returns but computes trailing returns with `EMA.shift(tau)`.
- Its percentile thresholds are fit over the full supplied series. In the deterministic diagnostic, appending future observations changes {manifest['literal_algorithm_changed_prefix_labels']}/{manifest['literal_algorithm_valid_prefix_labels']} already assigned prefix labels.
- The decision matrix gives prediction Strong Buy / truth Strong Sell a -2.00 penalty and the reverse mistake -2.25, opposite the prose claim that false bullish errors are penalized more heavily.
- The claimed held-out June--August 2024 interval lies inside the January 2024--May 2025 collection interval, but no split manifest is released.
- The paper does not disclose action weights, exact holding/rebalance/entry/exit rules, costs, leverage/cash constraints, baseline snapshots, prompts/decoding, raw actions, equity paths, training hyperparameters, or seeds.
- The official project page says the Terminal is released, while its linked repository still says “Releasing soon.”

The complete boundaries are recorded in `paper_mechanism_conformance.csv`, `paper_specification_gaps.csv`, and `paper_internal_consistency_checks.csv`.
"""


def build_audit(source_root: Path, paper_root: Path, output: Path) -> dict[str, Any]:
    validate_primary_inputs(source_root, paper_root)
    output.mkdir(parents=True, exist_ok=True)
    tables = paper_table_rows()
    figures = figure_rows()
    mechanisms = mechanism_conformance()
    gaps = specification_gaps()
    checks = internal_checks()
    diagnostics = specification_reconstruction_diagnostics()
    source_files = released_source_inventory(source_root)
    fork_branches, fork_commits, fork_summary = public_fork_audit(
        source_root, paper_root
    )
    paper_assets = source_archive_inventory(paper_root)
    releases = public_release_rows(paper_root, source_root)
    releases.append({
        "source": "public_github_forks",
        "url": f"{SOURCE_URL}/forks",
        "observed_count": fork_summary["accessible_public_forks"],
        "status": "all_accessible_refs_exhausted_no_native_pipeline_or_result_payload",
        "native_result_credit": False,
    })
    compile_result = compile_paper(paper_root)
    native = {
        "audit_date": AUDIT_DATE,
        "native_system_execution_attempted": False,
        "native_system_execution_blocker": "official_repository_and_all_accessible_public_forks_have_no_executable_trading_r1_code_model_dataset_predictions_or_backtest_artifacts",
        "paper_latex_compilation": compile_result,
        "paper_specification_reconstruction": {
            "attempted": True,
            "components": ["literal Algorithm S1", "decision reward matrix"],
            "native_source_execution": False,
            "paper_result_credit": False,
        },
        "paper_result_credit": False,
    }
    changed = next(row for row in diagnostics if row["diagnostic"] == "literal_algorithm_prefix_instability")
    manifest: dict[str, Any] = {
        "audit_date": AUDIT_DATE,
        "paper": "Trading-R1: Financial Trading with LLM Reasoning via Reinforcement Learning",
        "paper_authority": ARXIV_URL,
        "source_authority": SOURCE_URL,
        "overall_status": "paper_spec_mechanisms_reconstructed_but_zero_of_348_published_result_units_reproduced_official_release_still_placeholder",
        "full_paper_reproduced": False,
        "paper_table_cells_total": len(tables),
        "paper_table_cells_with_paper_result_credit": sum(row["paper_result_credit"] for row in tables),
        "paper_figure_numeric_units_total": len(figures),
        "paper_figure_numeric_units_with_paper_result_credit": sum(row["paper_result_credit"] for row in figures),
        "published_numeric_result_units_total": len(tables) + len(figures),
        "published_numeric_result_units_with_paper_result_credit": 0,
        "paper_figure_units_internally_consistent_with_rounded_tables": sum(row["internally_consistent_with_table_precision"] for row in figures),
        "paper_mechanisms_total": len(mechanisms),
        "paper_mechanisms_verified_in_released_native_source": sum(row["verified_in_released_native_source"] for row in mechanisms),
        "paper_spec_reconstruction_components": sum(row["paper_spec_reconstruction_credit"] for row in mechanisms),
        "blocking_specification_gaps": len(gaps),
        "official_repository_commits_total": int(run_git(source_root, "rev-list", "--count", "HEAD").strip()),
        "official_repository_tracked_files_current": len(source_files),
        "official_repository_source_code_files_current": sum(row["source_code"] for row in source_files),
        "official_repository_tags_total": len(run_git(source_root, "tag", "--list").splitlines()),
        "public_forks_github_reported": fork_summary["github_reported_forks"],
        "public_forks_accessible_and_audited": fork_summary["accessible_public_forks"],
        "public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
        "public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "public_fork_unique_commits_beyond_official_history_audited": fork_summary[
            "unique_commits_beyond_official_history"
        ],
        "public_fork_native_trading_r1_pipelines_found": fork_summary[
            "native_trading_r1_pipelines_found"
        ],
        "official_huggingface_models_total": len(json.loads((paper_root / "hf_models.json").read_text())),
        "official_huggingface_datasets_total": len(json.loads((paper_root / "hf_datasets.json").read_text())),
        "arxiv_source_files_total": len(paper_assets),
        "paper_compile_pages": compile_result.get("pages", 0),
        "literal_algorithm_changed_prefix_labels": int(changed["observed_value"]),
        "literal_algorithm_valid_prefix_labels": int(changed["denominator"]),
        "primary_snapshot_sha256": {
            "paper.pdf": PAPER_PDF_SHA256,
            "source.tar": PAPER_SOURCE_SHA256,
            "official_git_archive.tar": SOURCE_ARCHIVE_SHA256,
            "github_repo.json": GITHUB_REPO_SNAPSHOT_SHA256,
            "github_issue_1.json": GITHUB_ISSUE_SNAPSHOT_SHA256,
            "github_issue_1_comments.json": GITHUB_ISSUE_COMMENTS_SHA256,
            "hf_models.json": HF_EMPTY_SNAPSHOT_SHA256,
            "hf_datasets.json": HF_EMPTY_SNAPSHOT_SHA256,
            "official_project_page.html": OFFICIAL_PROJECT_PAGE_SHA256,
            "public_fork_snapshot.json": PUBLIC_FORK_SNAPSHOT_SHA256,
        },
    }
    outputs = {
        "paper_table_result_conformance.csv": tables,
        "paper_figure_numeric_conformance.csv": figures,
        "paper_mechanism_conformance.csv": mechanisms,
        "paper_specification_gaps.csv": gaps,
        "paper_internal_consistency_checks.csv": checks,
        "paper_spec_reconstruction_diagnostics.csv": diagnostics,
        "released_source_inventory.csv": source_files,
        "paper_source_asset_inventory.csv": paper_assets,
        "public_release_inventory.csv": releases,
        "public_fork_branch_ref_snapshot.csv": fork_branches,
        "public_fork_unique_commit_inventory.csv": fork_commits,
    }
    for filename, rows in outputs.items():
        write_csv(output / filename, rows)
    (output / "native_execution.json").write_text(json.dumps(native, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "public_fork_census.json").write_text(
        json.dumps(fork_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "README.md").write_text(readme_text(manifest), encoding="utf-8")
    hashed = [*outputs, "native_execution.json", "public_fork_census.json", "README.md"]
    manifest["output_sha256"] = {filename: sha256(output / filename) for filename in hashed}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("paper_runs/paper_replication_audits/trading_r1"),
    )
    args = parser.parse_args()
    manifest = build_audit(args.source_root.resolve(), args.paper_root.resolve(), args.output.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
