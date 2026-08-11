#!/usr/bin/env python3
"""Fail-closed audit of Alpha-R1 arXiv v1 and its official placeholder repo.

The paper says that the full implementation and resources are available, but
the only paper-era Git revision is a two-line title README.  The current head
still contains only a README whose roadmap says code and weights are coming
soon.  This audit therefore inventories every numeric table cell, every
numeric heatmap cell, quantitative prose claims, method dimensions, and the
precise missing artifacts.  It gives no result or mechanism credit to prose,
paper figures, or the local motif proxy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


PAPER_URL = "https://arxiv.org/pdf/2512.23515v1"
PAPER_VERSION = "arXiv:2512.23515v1"
PAPER_DATE = "2025-12-29T14:50:23Z"
PAPER_SHA256 = "3b88ec9d3231b097d3633de6d9c0e9840873c99497c29df85e33b20b110d00de"
PAPER_SOURCE_SHA256 = "013e3201472be17a97c37a832e77fe1edf1b122d0cc6eeea1294c3cab8cf7e01"
SOURCE_URL = "https://github.com/FinStep-AI/Alpha-R1"
SOURCE_COMMIT = "61feaa359bd57761f5ac58f75af46ddfed2d2d7b"
SOURCE_COMMIT_DATE = "2025-12-30T19:40:48+08:00"
README_UPDATE_COMMIT = "4e626b8af9411a904fc578028c5676308a79ac2b"
README_UPDATE_DATE = "2025-12-30T19:37:51+08:00"
PAPER_ERA_COMMIT = "09b2f921fe2344fc370beafc26aa0d44a6913a5b"
PAPER_ERA_COMMIT_DATE = "2025-12-26T18:06:58+08:00"
CURRENT_README_SHA256 = "508c110b9c67243c7f5c3af80c0c2c24c8b929e9e3f3fa3d7e02cd2c763f40ae"
PAPER_ERA_README_SHA256 = "97dd2fb2bbcf2081ec20c86fd5a9111cb4c0e1d39100bc3906dc0a6f5ca1c247"

PAPER_SOURCE_FILES = {
    "00README.json": "d1f6b1a71c9accb812ec5121d1fff7910c025ca7bb201948bacdb40941bc14e5",
    "ACM-Reference-Format.bst": "ee0d9fd846b95ca8b9b7721e8d9aaa066c64c9e7a61284c6315cfbb844794a39",
    "acmart.cls": "6895475b24fe526c12831f5cc1d16f37218ce5d65161f811dde4bce8dc4551b9",
    "images/Alpha-R1.pdf": "b5008c00a0c6f950917202891194abc1155b4f7d161be90490f9bb7b2552bcb2",
    "images/heatmap/csi1000/max_drawdown_heatmap.png": "272768097a4a120f8b0141cd64aa311326cc59816756dd8efed6588ca2097a5f",
    "images/heatmap/csi1000/sharpe_ratio_heatmap.png": "bd0fb391541d52f6409c2ee472619d7456829406be5442f84751366409cbe6f1",
    "images/heatmap/csi1000/total_return_heatmap.png": "db50ae4365aab3a885add070196e570ca9d62d9f8800cb131be750548e0f9f60",
    "images/heatmap/csi300/max_drawdown_heatmap.png": "53e406d7e5808370108b2bf06ff7f304f157b9990b036f8c7f2e7ba2286d2a44",
    "images/heatmap/csi300/sharpe_ratio_heatmap.png": "cdfd4eb2b2ecdccde8a01d74b0f7ec7fe115fde3b251eba75c213fa4db8d94e8",
    "images/heatmap/csi300/total_return_heatmap.png": "aa16fcd57f47fb0b13b6fe8fe8bb7550311e09ae275391e2a0d10070bdbe6b51",
    "images/nav/main_result_comparison.png": "5720132c180a53243fb350bbce9653d778254d9429ad3ff929c4a683316f0c00",
    "images/nav/main_result_csi1000_comparison.png": "497e7085d1bf4bd7f093cffaa2ef9ccc8135c16db76cbcf21f81f0c49f5a464f",
    "main.tex": "e5e8c3bf782ad0cc67afb255136193a69c6beac81745ba6e2d21bd0c40658a20",
    "sections/00_preamble.tex": "2130d31742a6e5fd9dd548e2370006bf00022302247defc397a296088a483857",
    "sections/01_title_authors.tex": "ca9a618b68b16268b9ddf35af65e2676b98b808ef9fc91a1ec5f552bd42c751a",
    "sections/02_abstract.tex": "e86c2ebd382df3c15ec2ae7bc7ec62f53fc525867345808fda94daf70328f52e",
    "sections/03_introduction.tex": "0a878ec96b2fde1ab9b03d8baf564c49621cb616e7fdce936e1f68ef3cb45576",
    "sections/04_related_work.tex": "73e08dfc3461338557dce3a51dc280e20594401021e11b59b614c8fb7ecc9e5b",
    "sections/05_methodology.tex": "7f3e3558c5fe1a1a5255192faf22f7c336a102bb34e72ee64c89bfaabea08362",
    "sections/06_experiments.tex": "200d87a350b81bb253606518fb2137275a75110f0c44f0582f9be240261624af",
    "sections/07_conclusion.tex": "765a6e5e498303308f3008709d43173603f143607e72624d94d90c411e3d1f9c",
    "sections/references.bib": "6c503931e06d20c10419e12bc2a1e65fd1b44dcbe64ad052ab928796c1655af0",
}

METRICS = ("CR_pct", "AR_pct", "Sharpe", "MDD_pct")
MAIN_RESULTS = {
    "Buy & Hold": (3.03, 6.70, 0.33, 10.49, 9.64, 22.14, 0.80, 16.87),
    "PCA": (-0.48, 0.40, -0.06, 14.69, 6.24, 16.09, 0.59, 16.13),
    "XGBoost": (-10.03, -21.65, -1.54, 15.33, 4.34, 11.77, 0.45, 19.12),
    "LightGBM": (-5.10, -10.26, -0.83, 13.43, -5.37, -6.92, -0.26, 23.88),
    "A2C": (-5.52, -11.12, -0.85, 11.22, 11.80, 26.30, 1.15, 14.00),
    "PPO": (0.89, 3.28, 0.11, 11.67, -6.44, -7.62, -0.25, 29.31),
    "Gemini 2.5 Pro Thinking": (-7.04, -14.45, -1.01, 15.08, -8.73, -15.38, -0.58, 28.37),
    "Claude 3.7 Sonnet Thinking": (-5.41, -10.23, -0.63, 13.58, 3.80, 13.26, 0.43, 16.98),
    "DeepSeek-R1": (-5.98, -11.93, -0.82, 14.88, -7.58, -12.87, -0.50, 27.89),
    "Qwen3-8B": (-6.32, -12.41, -0.77, 16.35, 2.73, 10.23, 0.29, 21.78),
    "Alpha-R1": (12.99, 27.59, 1.62, 6.76, 42.49, 78.18, 4.03, 9.25),
}

ABLATION_RESULTS = {
    "Alpha-R1 (Full)": (12.99, 27.59, 1.62, 6.76),
    "Buy & Hold (CSI 300 Index)": (3.03, 6.70, 0.33, 10.49),
    "w/o Market Price": (10.24, 22.42, 1.24, 12.87),
    "w/o News": (8.75, 19.61, 1.03, 12.01),
    "w/o Semantic Description": (7.26, 16.76, 0.83, 13.32),
    "w/o RL Optimization": (-6.32, -12.41, -0.77, 16.35),
}

GATING_RESULTS = {
    "Alpha-R1 (Semantic Gating)": (12.99, 27.59, 1.62, 6.76),
    "Lasso": (1.58, 4.63, 0.20, 11.12),
    "IC Momentum": (-6.33, -12.55, -0.80, 13.29),
}

TOP_N_VALUES = (1, 2, 3, 5, 7, 10, 20, 30, 50, 70, 100)
HOLDING_DAYS = (1, 2, 3, 5, 7, 10, 15, 20)
HEATMAP_TEXT = {
    ("CSI 300", "MDD_pct"): """
9.4 7.8 7.0 6.6 6.4 6.1 5.3 6.0
7.8 7.3 7.1 7.2 7.4 6.7 6.4 6.5
8.8 7.7 7.1 6.8 7.2 6.8 6.9 7.1
9.6 7.5 6.8 6.3 6.6 6.6 6.4 6.7
14.1 8.7 8.1 7.4 6.7 6.7 7.0 7.2
13.8 8.1 7.3 6.8 6.3 6.2 6.5 6.8
18.6 11.6 8.8 7.9 7.8 8.1 8.1 8.0
18.7 12.7 10.5 9.1 8.9 9.0 9.0 9.1
22.3 15.7 13.2 11.4 10.8 10.7 10.4 10.5
22.2 15.0 12.6 10.7 10.2 10.1 10.1 10.1
23.0 14.5 11.9 10.1 10.1 10.0 10.0 10.0
""",
    ("CSI 300", "Sharpe"): """
0.482 1.727 2.295 2.923 2.978 3.372 3.527 3.385
0.922 2.050 2.301 2.611 2.489 2.799 3.023 2.848
0.359 1.936 2.213 2.605 2.692 2.899 2.727 2.579
-0.179 1.271 1.745 2.133 2.314 2.370 2.223 2.261
-1.126 0.527 1.015 1.525 1.783 1.926 1.889 1.999
-1.273 0.434 1.128 1.618 1.775 1.862 1.754 1.750
-2.238 -0.332 0.324 0.804 0.979 1.107 1.018 0.941
-2.405 -0.690 -0.052 0.354 0.537 0.665 0.627 0.555
-3.149 -1.439 -0.761 -0.227 -0.053 0.072 0.076 0.045
-3.206 -1.510 -0.843 -0.309 -0.122 0.018 0.041 0.013
-3.493 -1.716 -1.000 -0.333 -0.080 0.079 0.102 0.068
""",
    ("CSI 300", "CR_pct"): """
4.6 17.0 22.6 29.6 31.1 34.8 36.1 31.8
8.9 20.3 22.8 26.4 24.7 27.1 28.8 25.2
3.1 18.3 20.9 26.4 27.2 28.7 26.3 23.3
-1.8 11.7 16.1 20.2 22.0 21.7 19.7 19.2
-9.4 4.4 8.6 13.3 15.3 16.0 15.2 15.5
-9.6 3.4 8.9 13.0 14.1 14.3 13.0 12.6
-15.0 -2.2 2.5 6.1 7.5 8.3 7.4 6.7
-16.6 -4.9 -0.3 2.8 4.1 5.1 4.7 4.1
-20.8 -9.9 -5.3 -1.5 -0.3 0.7 0.7 0.5
-20.7 -10.1 -5.7 -2.0 -0.7 0.3 0.5 0.3
-21.6 -11.0 -6.5 -2.1 -0.4 0.7 0.9 0.7
""",
    ("CSI 1000", "MDD_pct"): """
20.6 20.8 19.4 17.7 13.5 15.9 11.8 10.7
18.2 18.2 18.1 16.8 14.8 15.7 13.1 11.7
17.4 16.7 16.1 15.0 14.4 15.4 12.9 11.9
16.0 14.9 14.2 13.5 13.0 13.7 11.7 11.6
14.8 13.3 12.6 11.2 11.2 12.4 10.9 10.9
12.8 11.6 10.6 9.3 9.8 11.2 9.9 10.3
13.0 12.0 11.5 10.6 10.9 11.4 10.9 10.9
12.8 11.7 11.5 10.6 10.8 11.1 10.8 10.7
13.0 11.7 11.4 11.1 11.1 11.2 10.9 10.6
13.3 11.9 11.5 11.2 11.3 11.2 10.8 10.6
13.6 11.9 11.6 11.3 11.3 11.3 10.9 10.7
""",
    ("CSI 1000", "Sharpe"): """
2.710 4.021 4.198 4.007 4.394 4.380 3.980 3.615
2.473 3.703 3.844 3.741 3.872 3.917 3.645 3.335
1.828 3.023 3.554 3.734 3.678 3.850 3.560 3.258
2.073 3.195 3.664 3.763 3.879 3.900 3.717 3.526
1.925 3.275 3.696 4.033 3.965 3.850 3.786 3.615
1.510 2.937 3.563 4.031 3.874 3.738 3.798 3.604
1.002 2.293 2.765 3.101 3.031 3.037 3.130 3.125
0.515 1.847 2.294 2.730 2.717 2.763 2.857 2.940
-0.138 1.439 1.993 2.317 2.354 2.470 2.589 2.720
-0.196 1.324 1.929 2.263 2.277 2.410 2.525 2.633
-0.300 1.232 1.775 2.177 2.223 2.341 2.437 2.527
""",
    ("CSI 1000", "CR_pct"): """
59.8 83.1 89.2 80.3 87.3 86.2 63.8 49.2
37.6 59.1 61.3 58.1 59.3 60.8 49.9 40.8
23.1 41.0 49.3 51.3 50.0 54.4 45.7 38.5
24.3 38.5 44.5 46.6 48.4 50.7 45.1 40.9
21.5 37.6 42.2 46.7 46.2 46.7 44.0 40.3
15.4 30.9 37.2 42.5 41.4 41.6 41.0 37.9
9.8 23.3 27.9 31.6 31.4 31.8 32.0 31.4
4.7 18.1 22.4 27.2 27.4 28.0 28.2 28.5
-1.5 13.8 19.3 22.7 23.4 24.6 24.9 25.7
-2.0 12.7 18.7 22.3 22.7 24.0 24.1 24.6
-3.1 11.8 17.3 21.6 22.2 23.3 23.2 23.6
""",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> Any:
    result = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return result.stdout


def git_blob(source_root: Path, commit: str, relative: str) -> bytes:
    return run_git(source_root, "show", f"{commit}:{relative}", binary=True)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_table_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method, values in MAIN_RESULTS.items():
        for pool_index, pool in enumerate(("CSI 300", "CSI 1000")):
            for metric_index, metric in enumerate(METRICS):
                rows.append(
                    {
                        "paper_table": "Table 1 Main Experiment Results",
                        "method": method,
                        "asset_pool": pool,
                        "metric": metric,
                        "paper_value": values[pool_index * 4 + metric_index],
                        "native_reproduced_value": "",
                        "absolute_difference": "",
                        "status": "unavailable_official_repository_has_no_experiment_code_or_output",
                        "paper_result_credit": False,
                    }
                )
    for table, values_by_method in (
        ("Table 2 Ablation Study Results", ABLATION_RESULTS),
        ("Table 3 Gating Strategy Comparison", GATING_RESULTS),
    ):
        for method, values in values_by_method.items():
            for metric, value in zip(METRICS, values):
                rows.append(
                    {
                        "paper_table": table,
                        "method": method,
                        "asset_pool": "CSI 300",
                        "metric": metric,
                        "paper_value": value,
                        "native_reproduced_value": "",
                        "absolute_difference": "",
                        "status": "unavailable_official_repository_has_no_experiment_code_or_output",
                        "paper_result_credit": False,
                    }
                )
    counts = Counter(row["paper_table"] for row in rows)
    expected = {
        "Table 1 Main Experiment Results": 88,
        "Table 2 Ablation Study Results": 24,
        "Table 3 Gating Strategy Comparison": 12,
    }
    if len(rows) != 124 or counts != expected:
        raise RuntimeError(f"Alpha-R1 table census changed: {counts}")
    return rows


def heatmap_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (pool, metric), text in HEATMAP_TEXT.items():
        matrix = [[float(value) for value in line.split()] for line in text.strip().splitlines()]
        if len(matrix) != 11 or any(len(line) != 8 for line in matrix):
            raise RuntimeError(f"Bad Alpha-R1 heatmap shape: {pool} {metric}")
        for row_index, top_n in enumerate(TOP_N_VALUES):
            for col_index, holding_days in enumerate(HOLDING_DAYS):
                rows.append(
                    {
                        "paper_figure": "Figure 3 Parameter Sensitivity and Generalization",
                        "asset_pool": pool,
                        "metric": metric,
                        "top_n": top_n,
                        "holding_days": holding_days,
                        "paper_value": matrix[row_index][col_index],
                        "native_reproduced_value": "",
                        "absolute_difference": "",
                        "extraction": "original_arxiv_png_visible_cell_transcription",
                        "status": "unavailable_raster_only_no_native_result_path_or_underlying_array",
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 528 or Counter((r["asset_pool"], r["metric"]) for r in rows) != {
        (pool, metric): 88 for pool, metric in HEATMAP_TEXT
    }:
        raise RuntimeError("Alpha-R1 heatmap numeric denominator changed")
    return rows


def published_non_table_claims() -> list[dict[str, Any]]:
    # Result claims include repeats of table cells because each published
    # assertion still needs an evidentiary route. Configuration claims are
    # descriptive only and never receive result credit.
    raw = [
        ("Abstract", "reasoning model size", 8, "B parameters", "configuration", "exact"),
        ("Methodology", "linear reward history", 4, "years", "configuration", "exact"),
        ("Methodology", "previous-day factor lag", 1, "day", "configuration", "exact"),
        ("Methodology", "base reward scaling", 100, "multiplier", "configuration", "exact"),
        ("Methodology", "example holding period", 5, "days", "configuration", "example_not_binding"),
        ("Methodology", "judge normalization denominator", 10, "score units", "configuration", "exact"),
        ("Execution", "slot holding period", 5, "days", "configuration", "exact"),
        ("Execution", "concurrent slots", 5, "slots", "configuration", "derived_from_H"),
        ("Execution", "average daily slot turnover", 0.2, "capital fraction", "configuration", "derived_from_H"),
        ("Execution", "VWAP window", 30, "minutes", "configuration", "exact"),
        ("Execution", "VWAP start minute", 931, "HHMM", "configuration", "exact"),
        ("Execution", "VWAP end minute", 1000, "HHMM", "configuration", "exact"),
        ("Execution", "bilateral fee", 0.1, "pct each side", "configuration", "exact"),
        ("Execution", "bilateral fee", 10, "bps each side", "configuration", "duplicate_unit"),
        ("Experiments", "retained Alpha101 factors", 82, "factors", "configuration", "exact"),
        ("Experiments", "training samples per trading date", 300, "samples", "configuration", "exact"),
        ("Experiments", "random candidate factors per sample", 40, "factors", "configuration", "exact"),
        ("Experiments", "test candidate factors", 40, "factors", "configuration", "exact"),
        ("Experiments", "holding period", 5, "days", "configuration", "exact"),
        ("Experiments", "concurrent sub-portfolios", 5, "slots", "configuration", "exact"),
        ("Experiments", "stocks per slot", 10, "stocks", "configuration", "exact"),
        ("Experiments", "VWAP window", 30, "minutes", "configuration", "duplicate_method"),
        ("Experiments", "transaction cost", 0.1, "pct each side", "configuration", "duplicate_method"),
        ("Experiments", "backbone size", 8, "B parameters", "configuration", "duplicate_abstract"),
        ("Experiments", "temperature", 0, "temperature", "configuration", "exact"),
        ("Experiments", "top_p", 0.7, "probability", "configuration", "exact"),
        ("Experiments", "independent runs", 5, "runs", "configuration", "exact"),
        ("Results CSI300", "XGBoost CR", -10.03, "pct", "result", "duplicate_table"),
        ("Results CSI300", "A2C CR", -5.52, "pct", "result", "duplicate_table"),
        ("Results CSI300", "A2C Sharpe", -0.85, "Sharpe", "result", "duplicate_table"),
        ("Results CSI300", "PPO CR", 0.89, "pct", "result", "duplicate_table"),
        ("Results CSI300", "PPO Sharpe", 0.11, "Sharpe", "result", "duplicate_table"),
        ("Results CSI300", "generic LLM lower approximate drawdown", 15, "pct", "result", "approximate_range"),
        ("Results CSI300", "generic LLM upper approximate drawdown", 16, "pct", "result", "approximate_range"),
        ("Results CSI300", "Alpha-R1 Sharpe", 1.62, "Sharpe", "result", "duplicate_table"),
        ("Results CSI300", "Alpha-R1 MDD", 6.76, "pct", "result", "duplicate_table"),
        ("Results CSI1000", "A2C CSI300 CR", -5.52, "pct", "result", "duplicate_table"),
        ("Results CSI1000", "A2C CSI300 Sharpe", -0.85, "Sharpe", "result", "duplicate_table"),
        ("Results CSI1000", "PPO CSI300 CR", 0.89, "pct", "result", "duplicate_table"),
        ("Results CSI1000", "PPO CSI300 Sharpe", 0.11, "Sharpe", "result", "duplicate_table"),
        ("Results CSI1000", "A2C CR", 11.80, "pct", "result", "duplicate_table"),
        ("Results CSI1000", "PPO CR", -6.44, "pct", "result", "duplicate_table"),
        ("Results CSI1000", "PPO MDD", 29.31, "pct", "result", "duplicate_table"),
        ("Results CSI1000", "Alpha-R1 CR", 42.49, "pct", "result", "duplicate_table"),
        ("Results CSI1000", "Alpha-R1 Sharpe", 4.03, "Sharpe", "result", "duplicate_table"),
        ("Ablation", "base model Sharpe", -0.77, "Sharpe", "result", "duplicate_table"),
        ("Ablation", "semantic-description Sharpe decline", 49, "pct", "result", "derived_approximate"),
        ("Ablation", "full Sharpe", 1.62, "Sharpe", "result", "duplicate_table"),
        ("Ablation", "without semantic description Sharpe", 0.83, "Sharpe", "result", "duplicate_table"),
        ("Ablation", "without news Sharpe", 1.03, "Sharpe", "result", "duplicate_table"),
        ("Ablation", "without price Sharpe", 1.24, "Sharpe", "result", "duplicate_table"),
        ("Ablation", "full MDD", 6.76, "pct", "result", "duplicate_table"),
        ("Gating", "IC momentum lookback", 20, "days", "configuration", "exact"),
        ("Gating", "IC momentum selected factors", 10, "factors", "configuration", "exact"),
        ("Gating", "Lasso CR", 1.58, "pct", "result", "duplicate_table"),
        ("Gating", "IC Momentum CR", -6.33, "pct", "result", "duplicate_table"),
        ("Sensitivity", "holding-days lower example", 3, "days", "configuration", "range_endpoint"),
        ("Sensitivity", "holding-days upper example", 10, "days", "configuration", "range_endpoint"),
        ("Sensitivity", "TopN lower stated setting", 5, "stocks", "configuration", "range_endpoint"),
        ("Sensitivity", "TopN upper stated setting", 20, "stocks", "configuration", "range_endpoint"),
    ]
    rows = [
        {
            "section": section,
            "claim": claim,
            "paper_value": value,
            "unit": unit,
            "claim_role": role,
            "claim_kind": kind,
            "native_reproduced_value": "",
            "status": "unavailable_official_repository_has_no_native_result_or_configuration",
            "paper_result_credit": False,
        }
        for section, claim, value, unit, role, kind in raw
    ]
    if len(rows) != 60 or Counter(r["claim_role"] for r in rows) != {
        "configuration": 33,
        "result": 27,
    }:
        raise RuntimeError(f"Alpha-R1 non-table claim census changed: {Counter(r['claim_role'] for r in rows)}")
    return rows


def internal_and_source_checks() -> list[dict[str, Any]]:
    semantic_decline = (1.62 - 0.83) / 1.62 * 100
    checks = [
        ("paper availability statement versus paper-era repository", "full implementation and resources are available", "paper-era tree is a two-line title README", "paper_source_release_claim_conflict"),
        ("paper availability statement versus current repository", "full implementation and resources are available", "current README says inference code and model weights are Coming Soon", "paper_source_release_claim_conflict"),
        ("paper-era source timing", "repository existed at submission", "only title README committed 76.72 hours before submission", "paper_era_placeholder_confirmed"),
        ("current source history", "implementation availability", "three commits and one tracked README; no code-bearing revision", "current_placeholder_confirmed"),
        ("default CSI300 CR heatmap versus Table 1", "12.99", "13.0", "compatible_at_heatmap_precision"),
        ("default CSI300 Sharpe heatmap versus Table 1", "1.62", "1.618", "compatible_at_heatmap_precision"),
        ("default CSI300 MDD heatmap versus Table 1", "6.76", "6.8", "compatible_at_heatmap_precision"),
        ("default CSI1000 CR heatmap versus Table 1", "42.49", "42.5", "compatible_at_heatmap_precision"),
        ("default CSI1000 Sharpe heatmap versus Table 1", "4.03", "4.031", "compatible_at_heatmap_precision"),
        ("default CSI1000 MDD heatmap versus Table 1", "9.25", "9.3", "compatible_at_heatmap_precision"),
        ("semantic-description Sharpe decline", "approximately 49%", f"{semantic_decline:.6f}%", "compatible_at_claim_precision"),
        ("generic-LLM drawdown range", "Claude and DeepSeek lead to approximately 15--16% drawdowns", "Claude=13.58%; DeepSeek=14.88%", "paper_prose_overstates_displayed_range"),
        ("CR/AR metric identity", "all metrics averaged over five runs", "no metric formulas or per-run paths; mean CR cannot recover mean AR", "paper_metric_definition_and_inputs_missing"),
        ("five independent runs with deterministic inference", "temperature=0 and five runs", "randomized factor samples/training remain possible, but seeds and run outputs are absent", "unverifiable_missing_seeds_and_paths"),
        ("benchmark LLM cutoff", "all benchmark pre-training cutoffs no later than 2024-12-31", "no model snapshot/version metadata substantiates cutoffs", "unverifiable_missing_model_versions"),
        ("CSI1000 zero-shot claim", "transfer without retraining", "no checkpoint, training log, or evaluation invocation exists", "unverifiable_missing_training_and_test_artifacts"),
        ("LLM judge direction", "consistency penalty is normalized score/10 and applied asymmetrically", "score scale/direction and exact judge rubric are unspecified", "paper_reward_definition_incomplete"),
        ("structural penalty", "qualitatively combines parsimony and validity", "no formula, weights, or thresholds supplied", "paper_reward_definition_incomplete"),
    ]
    return [
        {"check": name, "paper_statement": paper, "observed_or_recomputed": observed, "status": status, "paper_result_credit": False}
        for name, paper, observed, status in checks
    ]


def specification_gaps() -> list[dict[str, str]]:
    raw = [
        ("data", "daily/minute price vendor and snapshot", "required for factors, VWAP, returns, and limits"),
        ("data", "news vendor, article corpus, timestamps, and deduplication", "required for state descriptions"),
        ("data", "macroeconomic announcement source and availability timestamps", "required to avoid look-ahead"),
        ("data", "point-in-time CSI300/CSI1000 memberships", "required to avoid survivorship bias"),
        ("data", "corporate-action and price-adjustment policy", "required for returns and factor values"),
        ("data", "sector taxonomy and point-in-time sector membership", "required for sector-rotation descriptions"),
        ("data", "capital-flow inputs and definitions", "required by the state description"),
        ("data", "trading calendar and suspended-stock handling", "required for slot rotation"),
        ("data", "limit-up/down and IPO metadata source", "required for execution constraints"),
        ("factors", "identities of the 82 retained Alpha101 factors", "computational-feasibility filter is not enumerated"),
        ("factors", "exact formulas and implementation conventions", "Alpha101 implementations differ on windows and ranks"),
        ("factors", "identities of the 40 test factors", "RankIC selection output is absent"),
        ("factors", "RankIC definition and tie/missing-value handling", "required to reconstruct selection"),
        ("factors", "factor normalization, winsorization, neutralization, and lagging", "required for betas and rankings"),
        ("descriptions", "technical-indicator definitions", "price atomic units cannot be reconstructed"),
        ("descriptions", "price-description generation prompt and model", "raw-to-text stage is unspecified"),
        ("descriptions", "news-description generation prompt and model", "raw-to-text stage is unspecified"),
        ("memory", "weekly summary prompt, model, decoding, and initial memory", "recursive memory cannot be replayed"),
        ("profiles", "factor-profile prompt, model, decoding, and schema", "semantic profiles cannot be reconstructed"),
        ("state", "daily state prompt, model, decoding, and schema", "market states cannot be reconstructed"),
        ("reasoning", "Alpha-R1 input prompt and output schema", "factor-gating decisions cannot be replayed"),
        ("reasoning", "exact Qwen3-8B base/revision/tokenizer", "model identity is not a reproducible snapshot"),
        ("reasoning", "trained Alpha-R1 checkpoint", "paper policy is unavailable"),
        ("reward", "beta regression target, cadence, universe, and estimator", "fixed linear scorer cannot be reconstructed"),
        ("reward", "all beta coefficients and intercept", "paper reward and portfolio ranking cannot be replayed"),
        ("reward", "reward benchmark identity", "excess return is undefined operationally"),
        ("reward", "exact judge model/version", "paper gives Claude 3.5 Haiku only as an example"),
        ("reward", "judge prompt, rubric, scale direction, and retries", "quality adjustment cannot be replayed"),
        ("reward", "structural penalty formula, weights, and thresholds", "final reward is incomplete"),
        ("training", "GRPO group size G", "advantage groups cannot be reconstructed"),
        ("training", "GRPO epsilon, KL beta, optimizer, LR, batches, and epochs", "training procedure is incomplete"),
        ("training", "zero-standard-deviation advantage handling", "edge-case behavior is undefined"),
        ("training", "training hardware and software environment", "dependency/runtime fidelity is unavailable"),
        ("training", "300-sample construction procedure", "sampling with/without replacement and candidate ordering are missing"),
        ("training", "all random seeds and five-run seed mapping", "run-level replication is impossible"),
        ("baselines", "PCA/XGBoost/LightGBM feature, target, and hyperparameters", "non-LLM baselines cannot be reconstructed"),
        ("baselines", "A2C/PPO state/action/reward and hyperparameters", "RL baselines cannot be reconstructed"),
        ("baselines", "LLM versions, prompts, APIs, and parsing", "LLM baselines cannot be replayed"),
        ("baselines", "Lasso regularization selection", "heuristic gating baseline is incomplete"),
        ("baselines", "IC Momentum tie/missing rules", "heuristic gating baseline is incomplete"),
        ("portfolio", "stock score normalization and tie handling", "top-N construction can diverge"),
        ("portfolio", "slot cash, dividends, delistings, suspensions, and deferred sells", "path accounting is incomplete"),
        ("portfolio", "VWAP fallback and fill/volume assumptions", "execution cannot be replayed"),
        ("portfolio", "whether 0.1% cost includes or adds slippage", "cost model is ambiguous"),
        ("metrics", "CR, AR, Sharpe, and MDD formulas", "table values cannot be independently checked"),
        ("metrics", "risk-free rate and annualization frequency", "Sharpe and AR cannot be reconstructed"),
        ("metrics", "averaging order across five runs", "mean metrics differ from metrics of a mean path"),
        ("outputs", "per-run selections, actions, fills, returns, and NAVs", "published results cannot be traced"),
        ("outputs", "heatmap arrays and run aggregation", "528 displayed cells are raster-only"),
        ("outputs", "baseline, ablation, and gating output tables", "no native result artifacts are shipped"),
    ]
    return [
        {"area": area, "missing_specification_or_artifact": gap, "replication_impact": impact, "resolved": "no"}
        for area, gap, impact in raw
    ]


def mechanism_conformance() -> list[dict[str, Any]]:
    requirements = [
        ("model", "8B reasoning model implementation"),
        ("model", "Qwen3-8B backbone revision"),
        ("model", "trained Alpha-R1 checkpoint"),
        ("data", "price atomic-unit builder"),
        ("data", "news atomic-unit builder"),
        ("memory", "weekly iterative memory recursion"),
        ("memory", "global historical memory artifact"),
        ("factor", "Alpha101 factor backtester"),
        ("factor", "82-factor retained zoo"),
        ("factor", "factor performance vectors"),
        ("semantic", "factor semantic-profile generator"),
        ("semantic", "factor mechanism descriptions"),
        ("semantic", "factor regime descriptions"),
        ("semantic", "factor failure-condition descriptions"),
        ("state", "daily asset-pool state generator"),
        ("state", "price/news state fusion"),
        ("state", "index-dynamics representation"),
        ("state", "sector-theme representation"),
        ("state", "capital-flow representation"),
        ("reasoning", "semantic decision-context construction"),
        ("reasoning", "context-conditioned factor gating"),
        ("reasoning", "selected-factor-list parser"),
        ("scorer", "fixed linear factor scorer"),
        ("scorer", "four-year beta estimator"),
        ("scorer", "previous-day factor lag"),
        ("portfolio", "equal-weight top-N constructor"),
        ("reward", "benchmark-excess base reward"),
        ("reward", "100x reward scaling"),
        ("reward", "external LLM judge"),
        ("reward", "judge normalization"),
        ("reward", "asymmetric reward adjustment"),
        ("reward", "structural sparsity penalty"),
        ("reward", "invalid/nonexistent-factor penalty"),
        ("training", "GRPO group advantage"),
        ("training", "clipped GRPO objective"),
        ("training", "KL reference regularization"),
        ("training", "randomized 40-of-82 factor augmentation"),
        ("execution", "H-slot rotation"),
        ("execution", "five-day holding implementation"),
        ("execution", "30-minute VWAP execution"),
        ("execution", "limit-up/limit-down constraints"),
        ("execution", "IPO-day exclusion"),
        ("execution", "bilateral 10-bps costs"),
        ("experiment", "2020--2023 beta/pretraining data"),
        ("experiment", "2024H2 CSI300 training data"),
        ("experiment", "2025H1 CSI300 test data"),
        ("experiment", "2025H1 CSI1000 zero-shot data"),
        ("experiment", "five independent runs"),
        ("experiment", "temperature/top-p inference config"),
        ("baseline", "Buy-and-Hold baseline"),
        ("baseline", "PCA baseline"),
        ("baseline", "XGBoost baseline"),
        ("baseline", "LightGBM baseline"),
        ("baseline", "A2C baseline"),
        ("baseline", "PPO baseline"),
        ("baseline", "four reasoning-LLM baselines"),
        ("ablation", "four component ablations"),
        ("gating", "Lasso gating baseline"),
        ("gating", "IC Momentum gating baseline"),
        ("sensitivity", "TopN/HoldingDays sweep"),
        ("artifact", "paper prompts"),
        ("artifact", "dependency/environment manifest"),
        ("artifact", "training/search runner"),
        ("artifact", "inference runner"),
        ("artifact", "backtest/evaluation runner"),
        ("artifact", "paper configuration files"),
        ("artifact", "random-seed ledger"),
        ("artifact", "training logs"),
        ("artifact", "factor selections/actions/fills"),
        ("artifact", "per-run NAV/return arrays"),
    ]
    rows = []
    narrative = {"8B reasoning model implementation", "context-conditioned factor gating", "GRPO group advantage"}
    for index, (area, requirement) in enumerate(requirements, start=1):
        status = "narrative_only_unverifiable" if requirement in narrative else "absent"
        evidence = (
            "README markets Alpha-R1 as an RL alpha-screening framework but supplies no implementation"
            if status == "narrative_only_unverifiable"
            else "official repository tree contains only README.md"
        )
        rows.append(
            {
                "dimension": index,
                "area": area,
                "paper_requirement": requirement,
                "official_source_evidence": evidence,
                "status": status,
                "paper_mechanism_credit": False,
            }
        )
    if len(rows) != 70:
        raise RuntimeError(f"Alpha-R1 mechanism denominator changed: {len(rows)}")
    return rows


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    tree = str(run_git(source_root, "ls-tree", "-r", "-l", SOURCE_COMMIT)).strip().splitlines()
    rows = []
    for line in tree:
        metadata, relative = line.split("\t", 1)
        mode, object_type, blob, size = metadata.split()
        payload = git_blob(source_root, SOURCE_COMMIT, relative)
        rows.append(
            {
                "relative_path": relative,
                "mode": mode,
                "object_type": object_type,
                "git_blob": blob,
                "bytes": int(size),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "python_source": relative.endswith(".py"),
                "test_file": relative.startswith("test") or "/test" in relative,
                "executable_implementation": False,
                "paper_result_artifact": False,
            }
        )
    if len(rows) != 1 or rows[0]["relative_path"] != "README.md":
        raise RuntimeError("Pinned Alpha-R1 source is no longer the one-file placeholder")
    return rows


def paper_source_inventory(paper_source_root: Path) -> list[dict[str, Any]]:
    rows = []
    numeric_figures = {
        "images/heatmap/csi1000/max_drawdown_heatmap.png",
        "images/heatmap/csi1000/sharpe_ratio_heatmap.png",
        "images/heatmap/csi1000/total_return_heatmap.png",
        "images/heatmap/csi300/max_drawdown_heatmap.png",
        "images/heatmap/csi300/sharpe_ratio_heatmap.png",
        "images/heatmap/csi300/total_return_heatmap.png",
        "images/nav/main_result_comparison.png",
        "images/nav/main_result_csi1000_comparison.png",
    }
    for relative, expected in PAPER_SOURCE_FILES.items():
        path = paper_source_root / relative
        role = "paper_source"
        if relative == "images/Alpha-R1.pdf":
            role = "method_diagram"
        elif relative in numeric_figures:
            role = "numeric_result_figure"
        rows.append(
            {
                "relative_path": relative,
                "bytes": path.stat().st_size,
                "sha256": expected,
                "asset_role": role,
                "visible_numeric_cells": 88 if "heatmap" in relative else 0,
                "underlying_numeric_array_shipped": False,
                "native_result_reproduction_path_shipped": False,
            }
        )
    return rows


def native_release_inspection(source_root: Path) -> dict[str, Any]:
    commits = str(run_git(source_root, "rev-list", "--all")).splitlines()
    current_readme = git_blob(source_root, SOURCE_COMMIT, "README.md")
    paper_readme = git_blob(source_root, PAPER_ERA_COMMIT, "README.md")
    return {
        "source_commit": SOURCE_COMMIT,
        "source_history_commits": len(commits),
        "tracked_files": 1,
        "tracked_python_files": 0,
        "tracked_test_files": 0,
        "dependency_manifests": 0,
        "runners": 0,
        "configuration_files": 0,
        "model_weight_files": 0,
        "data_files": 0,
        "result_files": 0,
        "paper_era_commit": PAPER_ERA_COMMIT,
        "paper_era_tracked_files": str(run_git(source_root, "ls-tree", "-r", "--name-only", PAPER_ERA_COMMIT)).splitlines(),
        "paper_era_readme_sha256": hashlib.sha256(paper_readme).hexdigest(),
        "current_readme_sha256": hashlib.sha256(current_readme).hexdigest(),
        "current_readme_says_organizing_code_and_models": b"organizing the code and models" in current_readme,
        "current_readme_marks_inference_code_coming_soon": b"Inference code" in current_readme and b"Coming Soon" in current_readme,
        "current_readme_marks_model_weights_coming_soon": b"Model weights" in current_readme and b"Coming Soon" in current_readme,
        "native_code_execution_possible": False,
        "native_tests_executed": 0,
        "native_paper_results_reproduced": 0,
        "motif_proxy_counted_as_native": False,
    }


def verify_pins(source_root: Path, paper_pdf: Path, paper_source_archive: Path, paper_source_root: Path) -> None:
    if str(run_git(source_root, "rev-parse", "HEAD")).strip() != SOURCE_COMMIT:
        raise RuntimeError("Alpha-R1 source HEAD changed from the audited pin")
    if sha256(paper_pdf) != PAPER_SHA256:
        raise RuntimeError("Alpha-R1 paper PDF hash changed")
    if sha256(paper_source_archive) != PAPER_SOURCE_SHA256:
        raise RuntimeError("Alpha-R1 paper-source archive hash changed")
    if hashlib.sha256(git_blob(source_root, SOURCE_COMMIT, "README.md")).hexdigest() != CURRENT_README_SHA256:
        raise RuntimeError("Alpha-R1 current README hash changed")
    if hashlib.sha256(git_blob(source_root, PAPER_ERA_COMMIT, "README.md")).hexdigest() != PAPER_ERA_README_SHA256:
        raise RuntimeError("Alpha-R1 paper-era README hash changed")
    for relative, expected in PAPER_SOURCE_FILES.items():
        observed = sha256(paper_source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Alpha-R1 paper-source hash changed for {relative}: {observed}")


def build_audit(
    source_root: Path,
    paper_pdf: Path,
    paper_source_archive: Path,
    paper_source_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    verify_pins(source_root, paper_pdf, paper_source_archive, paper_source_root)
    tables = paper_table_rows()
    heatmaps = heatmap_rows()
    claims = published_non_table_claims()
    checks = internal_and_source_checks()
    gaps = specification_gaps()
    mechanisms = mechanism_conformance()
    inventory = source_inventory(source_root)
    paper_assets = paper_source_inventory(paper_source_root)
    native = native_release_inspection(source_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "paper_numeric_table_conformance.csv", tables)
    write_csv(output_dir / "heatmap_numeric_cell_conformance.csv", heatmaps)
    write_csv(output_dir / "published_non_table_claims.csv", claims)
    write_csv(output_dir / "paper_internal_and_source_checks.csv", checks)
    write_csv(output_dir / "paper_specification_gaps.csv", gaps)
    write_csv(output_dir / "source_mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "released_source_inventory.csv", inventory)
    write_csv(output_dir / "paper_source_asset_inventory.csv", paper_assets)
    (output_dir / "native_release_inspection.json").write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")

    result_claims = [row for row in claims if row["claim_role"] == "result"]
    status_counts = Counter(row["status"] for row in mechanisms)
    manifest: dict[str, Any] = {
        "audit": "Alpha-R1 arXiv v1 versus official one-file placeholder repository",
        "overall_status": "not_reproduced_official_repository_is_placeholder_zero_native_code_or_results",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": PAPER_VERSION,
        "paper_date": PAPER_DATE,
        "paper_sha256": PAPER_SHA256,
        "paper_source_sha256": PAPER_SOURCE_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": SOURCE_COMMIT,
        "source_commit_date": SOURCE_COMMIT_DATE,
        "paper_era_commit": PAPER_ERA_COMMIT,
        "paper_era_commit_date": PAPER_ERA_COMMIT_DATE,
        "paper_era_source_before_submission_hours": 76.7236,
        "readme_update_commit": README_UPDATE_COMMIT,
        "readme_update_after_submission_hours": 20.7911,
        "current_merge_after_submission_hours": 20.8403,
        "source_history_commits": 3,
        "paper_era_source_revision_available": True,
        "paper_era_source_is_only_title_readme": True,
        "current_source_is_only_roadmap_readme": True,
        "paper_claims_full_implementation_and_resources_available": True,
        "current_readme_says_code_and_models_coming_soon": True,
        "paper_source_release_claim_conflict": True,
        "paper_numeric_tables_audited": ["Table 1 Main Experiment Results", "Table 2 Ablation Study Results", "Table 3 Gating Strategy Comparison"],
        "paper_numeric_table_cells_total": len(tables),
        "paper_main_table_cells_total": 88,
        "paper_ablation_table_cells_total": 24,
        "paper_gating_table_cells_total": 12,
        "paper_heatmap_numeric_cells_total": len(heatmaps),
        "published_table_and_heatmap_numeric_result_cells_total": len(tables) + len(heatmaps),
        "native_table_and_heatmap_result_cells_reproduced": 0,
        "published_non_table_quantitative_claims_total": len(claims),
        "published_non_table_result_claims_total": len(result_claims),
        "published_non_table_configuration_claims_total": len(claims) - len(result_claims),
        "native_non_table_result_claims_reproduced": 0,
        "numeric_result_figure_panels_total": 8,
        "numeric_heatmap_panels_total": 6,
        "numeric_nav_panels_total": 2,
        "numeric_result_figure_arrays_shipped": 0,
        "paper_internal_and_source_checks_total": len(checks),
        "paper_specification_gaps_total": len(gaps),
        "source_mechanism_dimensions_total": len(mechanisms),
        "source_mechanism_status_counts": dict(status_counts),
        "source_mechanism_matches_or_analogues": 0,
        "source_mechanism_fully_faithful": False,
        "tracked_source_files_total": len(inventory),
        "tracked_source_python_files_total": 0,
        "tracked_source_test_files_total": 0,
        "paper_source_assets_total": len(paper_assets),
        "native_code_execution_possible": False,
        "native_source_tests_passed": False,
        "native_paper_market_data_shipped": False,
        "native_paper_news_data_shipped": False,
        "native_paper_checkpoint_shipped": False,
        "native_paper_prompts_shipped": False,
        "native_paper_training_or_inference_code_shipped": False,
        "native_paper_environment_shipped": False,
        "native_paper_baselines_shipped": False,
        "native_paper_result_arrays_shipped": False,
        "native_paper_seed_or_cost_ledger_shipped": False,
        "local_motif_proxy_candidate": "code_alpha_r1_reasoning_screen",
        "local_motif_proxy_fidelity": "M0_narrative_translation",
        "local_motif_proxy_paper_result_credit": False,
        "audit_runtime_called_llm_or_market_data_api": False,
        "interpretation": (
            "Alpha-R1 is not presently reproducible from its official repository. The only revision "
            "available before arXiv submission is a two-line title README, and the current three-commit "
            "history still resolves to one README that says inference code and model weights are coming "
            "soon. This directly conflicts with the paper's statement that the full implementation and "
            "resources are available. The paper itself is unusually explicit about dates, portfolio "
            "rotation, VWAP, costs, and 652 displayed table/heatmap values; its six default heatmap cells "
            "are internally compatible with Table 1 after rounding. But none of the model, prompts, data, "
            "factor list, betas, training/search code, environment, baselines, seeds, selections, fills, "
            "paths, or output arrays is public. Therefore 0/652 table/heatmap result cells and 0/27 "
            "quantitative prose result claims are reproduced, 0/70 audited implementation dimensions "
            "match, and there is no native component execution to report. The repository's local "
            "code_alpha_r1_reasoning_screen row remains only an M0 favorable narrative translation and "
            "has zero paper-result or mechanism credit."
        ),
        "paper_source_file_sha256": PAPER_SOURCE_FILES,
    }

    report = f"""# Alpha-R1 paper-level conformance audit

Overall verdict: **not reproduced; the official repository is a placeholder**.
This is a release failure, not a failed attempt to run public Alpha-R1 code:
there is no public Alpha-R1 code to run.

## Primary-source pins

- Official paper: {PAPER_URL} ({PAPER_VERSION}, submitted {PAPER_DATE}; PDF
  SHA-256 `{PAPER_SHA256}`; TeX archive SHA-256 `{PAPER_SOURCE_SHA256}`).
- Official repository: {SOURCE_URL}, current commit `{SOURCE_COMMIT}`
  ({SOURCE_COMMIT_DATE}). Its complete three-commit history has one tracked file,
  `README.md`.
- The only pre-submission revision is `{PAPER_ERA_COMMIT}`
  ({PAPER_ERA_COMMIT_DATE}), 76.72 hours before submission. It contains a
  two-line title README and nothing else. The expanded README arrived 20.79
  hours after submission and explicitly says the code and models are being
  organized; inference code and model weights remain marked **Coming Soon**.

## Complete numeric-result boundary

- Tables 1--3 contain **124 numeric result cells**: 88 main, 24 ablation, and
  12 gating-comparison cells. The six source PNG heatmaps contain another
  **528 visible numeric cells** (11 TopN values by 8 holding periods by 3
  metrics by 2 universes). Thus the directly displayed table/heatmap
  denominator is **652**, not merely the headline table values. **0/652** has a
  native public reproduction path.
- The two NAV panels ship only raster curves. None of the eight numeric result
  figure panels includes its underlying array. The paper makes 27 other numeric
  result assertions in prose (including table repeats); **0/27** is reproduced.
- The heatmap transcription is checked against all six Table 1 values at the
  declared default `TopN=10`, `H=5`: 13.0/1.618/6.8 for CSI300 and
  42.5/4.031/9.3 for CSI1000 agree with 12.99/1.62/6.76 and
  42.49/4.03/9.25 at heatmap precision. The claimed 49% semantic-description
  Sharpe decline is also arithmetically compatible (48.765%). These internal
  checks establish transcription consistency, not experimental reproduction.

## What is missing

- No Python or other implementation, dependency file, runner, config, prompt,
  checkpoint, market/news data, 82- or 40-factor list, factor formula, fitted
  beta, baseline, ablation, seed, training log, selection, order, fill, return,
  NAV, or result table is present. **0/{len(mechanisms)}** audited mechanism
  dimensions match an implementation; three are merely narrative claims in the
  README and the rest are absent.
- The paper omits enough operational detail that a clean-room implementation
  would still require material choices: exact model revisions/prompts, data
  vendors and point-in-time membership, factor conventions, reward/judge and
  structural-penalty definitions, GRPO hyperparameters, baseline settings,
  metric formulas, aggregation order, and run seeds.
- The paper says the full implementation and resources are available at the
  repository. The repository says they are coming soon. That is a direct
  paper/source release-availability conflict.

## Honest boundary

The paper specification is useful and its displayed results are substantially
internally coherent, so a future official release could make this tractable.
Today, however, rebuilding an Alpha101-based Chinese-equity strategy from the
paper would be an independent reimplementation, not replication of the trained
Alpha-R1 system. The local `code_alpha_r1_reasoning_screen` candidate is an
M0 favorable narrative translation on unrelated JKP data; it gets zero native
mechanism or paper-result credit. Run `scripts/audit_alpha_r1_paper.py` to
regenerate this package. `--strict` intentionally fails until the official
model, inputs, runnable experiment, and all published values are reproduced.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(os.environ.get("ALPHA_R1_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/alpha_r1_source")),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(os.environ.get("ALPHA_R1_PAPER_PDF", "/nfs/roberts/scratch/pi_btk22/zc362/alpha_r1_paper/paper.pdf")),
    )
    parser.add_argument(
        "--paper-source-archive",
        type=Path,
        default=Path(os.environ.get("ALPHA_R1_PAPER_SOURCE_ARCHIVE", "/nfs/roberts/scratch/pi_btk22/zc362/alpha_r1_paper/source.tar")),
    )
    parser.add_argument(
        "--paper-source-root",
        type=Path,
        default=Path(os.environ.get("ALPHA_R1_PAPER_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/alpha_r1_paper/source")),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/alpha_r1",
    )
    parser.add_argument("--strict", action="store_true", help="Return nonzero until the full paper is reproduced")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root,
        args.paper_pdf,
        args.paper_source_archive,
        args.paper_source_root,
        args.output_dir,
    )
    print(json.dumps(manifest, indent=2))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
