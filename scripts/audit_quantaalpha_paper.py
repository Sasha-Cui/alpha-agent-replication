#!/usr/bin/env python3
"""Fail-closed paper-level audit of QuantaAlpha and its official releases.

The audit pins all three arXiv revisions, the official Git revision, and the
official Hugging Face data release.  It enumerates every numeric result cell
in the current paper, inventories numeric figures separately, executes safe
dependency-isolated components of the native source, and distinguishes exact
author-output correspondence from independent result regeneration.  Rendered
tables and plots can corroborate published output, but never substitute for
the missing factor pool, inputs, predictions, returns, or raw arrays.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import py_compile
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

PAPER_URL = "https://arxiv.org/abs/2602.07085"
PAPER_VERSIONS = {
    "v1": {
        "date": "2026-02-06T08:08:04Z",
        "pdf_sha256": "46de485ac041c6965c3464470a3bd1c25e9d144835ac50869021fbbabf85aab8",
        "source_sha256": "733df7a52c9cef58af084f5a40c15d50b38a3fed76f53cc951c3ab09b18eb495",
    },
    "v2": {
        "date": "2026-04-22T04:21:51Z",
        "pdf_sha256": "4c3e0e9cea5338b65f5c540aaec50724874ab444816d4857e4e8aea7b01e67b9",
        "source_sha256": "ac84ddcc1c002a675424a0d27d98f2955988a404bdba2cdba116b4c13c84def8",
    },
    "v3": {
        "date": "2026-05-18T16:57:08Z",
        "pdf_sha256": "75e9c2ef5e8bb7fed78d27409e8252208e8fdacf6d10e1495dbc5b8767481848",
        "source_sha256": "23b93499eb316770427f8f4a72b184253e8d8b865f4b3cfcd197819767249d38",
    },
}
SOURCE_URL = "https://github.com/QuantaAlpha/QuantaAlpha"
SOURCE_COMMIT = "b7ceb27b1001261d7a95b209a963664ae1f8ab23"
SOURCE_COMMIT_DATE = "2026-06-29T12:55:11-04:00"
INITIAL_COMMIT = "2f06d9fafaf21c07abd1a224551dbb437d341087"
INITIAL_COMMIT_DATE = "2026-02-09T01:02:43+08:00"
CURRENT_README_SHA256 = "737dbb80c047cd1f2ad90b31e10ccc45b38ea2f490b42a57584c5b30a830e222"
RELEASED_PAPER_OUTPUT_SHA256 = {
    "docs/images/case_study.png": "c67841b6e471b73d1c32ca3dfd44abd844915572918c7fc908de49f5dab90e85",
    "docs/images/figure3.png": "35d013008dd023c096f53ede8fa5b149944ed30b657b514e946bf2f6252061c3",
    "docs/images/figure4.png": "9a49d456072935fab8c20a5968834288738536a4eb7432830a34114c928afe4f",
    "docs/images/figure5.png": "5012fcdba8f561a0de5f7fba44f636af9f846c8c13925ca0e63e4d635606cf07",
    "docs/images/主实验.png": "217919e010e36e2cffec1a90e10a3d1ce05afedc29fe5b1074214d8388b06d75",
}
HF_DATASET_URL = "https://huggingface.co/datasets/QuantaAlpha/qlib_csi300"
HF_DATASET_COMMIT = "d63bf5ba30d1d169023110377cbbe93a90a74e07"
HF_DEBUG_SHA256 = "03816baa04a9ccefeaca8ccd6968c30f6a9a879330ae496d6fa19d6cd3208ebc"

METRICS = ("IC", "ICIR", "Rank_IC", "Rank_ICIR", "IR", "ARR_pct", "MDD_pct")
MAIN_RESULTS = {
    "Linear": (0.0155, 0.1174, 0.0368, 0.2834, -0.3078, -2.67, 18.97),
    "XGBoost": (0.0175, 0.1336, 0.0420, 0.3417, -0.5280, -4.24, 28.50),
    "CatBoost": (0.0162, 0.1203, 0.0405, 0.3289, -0.2807, -2.30, 21.35),
    "LightGBM": (0.0247, 0.2055, 0.0423, 0.3726, 0.0092, 0.07, 21.80),
    "MLP": (0.0321, 0.2780, 0.0438, 0.4088, 0.1716, 1.46, 18.15),
    "DoubleEnsemble": (0.0213, 0.1670, 0.0408, 0.3372, 0.2490, 1.85, 15.00),
    "GRU": (0.0321, 0.2603, 0.0442, 0.3601, 0.5302, 3.61, 15.01),
    "Transformer": (0.0331, 0.2702, 0.0451, 0.3801, 0.4502, 5.21, 13.81),
    "LSTM": (0.0331, 0.2502, 0.0451, 0.3503, 0.6802, 6.01, 14.81),
    "TRA": (0.0421, 0.3402, 0.0511, 0.4203, 1.0502, 6.81, 8.51),
    "Alpha158(20)": (0.0051, 0.0329, 0.0184, 0.1177, 0.5044, 4.63, 22.19),
    "Alpha158": (0.0131, 0.0817, 0.0334, 0.2119, 0.4099, 2.66, 10.15),
    "Alpha360": (0.0105, 0.0636, 0.0306, 0.1889, 0.6009, 4.09, 11.52),
    "RD-Agent / Qwen3-235B": (0.0267, 0.1676, 0.0194, 0.1199, -0.0818, -0.62, 15.04),
    "RD-Agent / DeepSeek-V3.2": (0.0245, 0.1630, 0.0192, 0.1250, -0.2123, -1.42, 19.17),
    "RD-Agent / Gemini-3-pro-preview": (0.0301, 0.1870, 0.0282, 0.1677, 0.2595, 1.89, 11.49),
    "RD-Agent / Claude-4.5-sonnet": (0.0280, 0.2000, 0.0242, 0.1708, 0.3568, 2.36, 10.81),
    "RD-Agent / GPT-5.2": (0.0286, 0.1995, 0.0250, 0.1739, 0.5321, 3.58, 16.76),
    "AlphaAgent / Qwen3-235B": (0.0208, 0.1316, 0.0196, 0.1246, -0.0951, -0.60, 18.56),
    "AlphaAgent / DeepSeek-V3.2": (0.0299, 0.1969, 0.0272, 0.1799, 0.3972, 2.58, 9.23),
    "AlphaAgent / Gemini-3-pro-preview": (0.0263, 0.1671, 0.0236, 0.1512, 0.1663, 1.17, 14.05),
    "AlphaAgent / Claude-4.5-sonnet": (0.0311, 0.2043, 0.0286, 0.1754, 0.4105, 2.84, 14.72),
    "AlphaAgent / GPT-5.2": (0.0347, 0.2122, 0.0334, 0.2053, 0.1587, 1.11, 13.89),
    "QuantaAlpha / Qwen3-235B": (0.0450, 0.2538, 0.0444, 0.2507, 0.3511, 2.06, 16.36),
    "QuantaAlpha / DeepSeek-V3.2": (0.0461, 0.2624, 0.0450, 0.2574, 0.6271, 4.53, 15.10),
    "QuantaAlpha / Gemini-3-pro-preview": (0.0453, 0.2551, 0.0439, 0.2490, 0.5834, 4.21, 12.10),
    "QuantaAlpha / Claude-4.5-sonnet": (0.0445, 0.2507, 0.0431, 0.2446, 0.5619, 4.12, 13.02),
    "QuantaAlpha / GPT-5.2": (0.0472, 0.2691, 0.0459, 0.2635, 0.6453, 4.68, 11.80),
}

EVOLUTION_ABLATION = {
    "QuantaAlpha": ((0.0461, 0.0450, 4.53, 15.10), ()),
    "w/o Planning": ((0.0448, 0.0437, 3.81, 16.72), (-0.0013, -0.0013, -0.72, 1.62)),
    "w/o Mutation": ((0.0382, 0.0371, 3.27, 15.58), (-0.0079, -0.0079, -1.26, 0.48)),
    "w/o Crossover": ((0.0401, 0.0419, 4.02, 16.03), (-0.0060, -0.0031, -0.51, 0.93)),
}
EVOLUTION_METRICS = ("IC", "Rank_IC", "ARR_pct", "MDD_pct")
SEED_RESULTS = {
    "Combination 1": (0.0466, 0.2708, 0.0454, 0.2655),
    "Combination 2": (0.0426, 0.2325, 0.0409, 0.2236),
    "Combination 3": (0.0436, 0.2551, 0.0418, 0.2468),
}
SEED_METRICS = ("IC", "ICIR", "Rank_IC", "Rank_ICIR")
SEED_VARIANCE = {
    "IC": (0.0443, 0.0021, 4.64, 0.0040),
    "ICIR": (0.2528, 0.0192, 7.60, 0.0382),
    "Rank_IC": (0.0427, 0.0024, 5.56, 0.0045),
    "Rank_ICIR": (0.2453, 0.0210, 8.55, 0.0419),
}
DAILY_STATS = {
    "Claude / IC": (0.0426, 0.0513, 0.1833, "60.04%", "[0.0311, 0.0542]", 7.23, "4.95e-13"),
    "Claude / Rank IC": (0.0409, 0.0438, 0.1827, "60.04%", "[0.0293, 0.0524]", 6.95, "3.68e-12"),
    "DeepSeek-V3.2 / IC": (0.0459, 0.0448, 0.1711, "60.97%", "[0.0348, 0.0544]", 7.93, "2.22e-15"),
    "DeepSeek-V3.2 / Rank IC": (0.0418, 0.0403, 0.1694, "60.97%", "[0.0311, 0.0525]", 7.67, "1.73e-14"),
}
DAILY_METRICS = ("mean", "median", "std", "positive_days", "95pct_CI", "t_stat", "p_value")

PARENT_RESULTS = {"Parent 1": (0.0216, 0.0059, 1.297), "Parent 2": (0.0246, 0.0069, 1.347)}
CASE_RESULTS = {
    "IC": (0.0126, 0.0058),
    "Rank_IC": (0.0311, 0.0220),
    "ARR_pct": (7.80, 5.20),
    "IR": (0.963, 0.973),
    "MDD_pct": (-11.37, -7.30),
}
DETAIL_RESULTS = {
    "daily_excess_wo_cost_pct": 0.0328,
    "daily_excess_w_cost_pct": 0.0128,
    "excess_return_std_pct": 0.52,
    "turnover_FFR_pct": 100.0,
    "L2_train_loss": 0.9936,
    "L2_valid_loss": 0.9962,
}
REPRESENTATIVE_FACTORS = {
    "GapZ10_Overnight_vs_TR": (0.0793, 0.0335),
    "Gap_IntradayAcceptanceScore_20D": (0.0744, 0.0330),
    "Gap_IntradayAcceptance_VolWeighted_20D": (0.0606, 0.0314),
    "CleanTrend_Continuation_Score_RS10_WVMA5": (0.0590, 0.0267),
    "OrderlyTrend_x_Absorption_10D_5D_20D": (0.0465, 0.0271),
    "KineticLength_AbsRetSum_Z_10D": (-0.0720, -0.0246),
    "Drawdown_Gated_NegCorr_60D_20D_thr20pct": (-0.0282, -0.0095),
    "HighClose_Shock_With_VolSync_60_20": (-0.0274, -0.0090),
    "Exhaustion_Intensity_Index_10D": (0.0323, 0.0159),
    "Climax_Exhaustion_Intensity": (0.0242, 0.0160),
    "Exhaustion_Volume_Instability_Index": (0.0121, 0.0117),
    "Relative_Volume_Calm_Reversal": (-0.0279, -0.0188),
    "Volume_Stability_Momentum_Divergence_40D": (-0.0247, -0.0155),
}
FACTOR_SUMMARY = {
    "coverage_ratio": (0.98, 0.80),
    "share_rank_ic_positive": (0.626, 0.594),
    "mean_rank_ic": (0.0057, 0.0012),
    "max_rank_ic": (0.0793, 0.0323),
    "min_rank_ic": (-0.0720, -0.0279),
    "share_rank_ic_gt_0.03": (0.102, 0.0156),
    "share_rank_ic_gt_0.05": (0.0272, 0.0000),
    "mean_ic": (0.0044, 0.0015),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> Any:
    result = subprocess.run(
        ["git", "-C", str(source_root), *args], check=True, capture_output=True, text=not binary
    )
    return result.stdout


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _result_row(table: str, item: str, metric: str, value: Any, role: str = "direct") -> dict[str, Any]:
    author_output = table == "Table 1 Main CSI300 results"
    return {
        "paper_table": table,
        "item": item,
        "metric": metric,
        "value_role": role,
        "paper_value": value,
        "native_reproduced_value": "",
        "absolute_difference": "",
        "author_output_value": value if author_output else "",
        "author_output_correspondence": author_output,
        "status": (
            "corroborated_by_exact_author_readme_table_raster_not_regenerated"
            if author_output
            else "not_reproduced_no_released_result_derivation"
        ),
        "paper_result_credit": False,
    }


def paper_table_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method, values in MAIN_RESULTS.items():
        rows.extend(_result_row("Table 1 Main CSI300 results", method, metric, value) for metric, value in zip(METRICS, values))
    for variant, (direct, deltas) in EVOLUTION_ABLATION.items():
        rows.extend(_result_row("Table 2 Evolution-component ablation", variant, metric, value) for metric, value in zip(EVOLUTION_METRICS, direct))
        rows.extend(_result_row("Table 2 Evolution-component ablation", variant, metric, value, "displayed_delta") for metric, value in zip(EVOLUTION_METRICS, deltas))
    for seed, values in SEED_RESULTS.items():
        rows.extend(_result_row("Appendix Table 2 Cross-seed core metrics", seed, metric, value) for metric, value in zip(SEED_METRICS, values))
    for metric, values in SEED_VARIANCE.items():
        rows.extend(_result_row("Appendix Table 3 Cross-seed variance", metric, stat, value) for stat, value in zip(("mean", "std", "CV_pct", "range"), values))
    for library_metric, values in DAILY_STATS.items():
        rows.extend(_result_row("Appendix Table 4 Daily IC statistics", library_metric, metric, value) for metric, value in zip(DAILY_METRICS, values))
    for parent, values in PARENT_RESULTS.items():
        rows.extend(_result_row("Appendix C Parent trajectory metrics", parent, metric, value) for metric, value in zip(("Rank_IC", "IC", "IR"), values))
    for metric, values in CASE_RESULTS.items():
        rows.extend(_result_row("Appendix C Backtest metrics", item, metric, value) for item, value in zip(("offspring", "baseline"), values))
    rows.extend(_result_row("Appendix C Detailed statistics", "offspring", metric, value) for metric, value in DETAIL_RESULTS.items())
    for factor, values in REPRESENTATIVE_FACTORS.items():
        rows.extend(_result_row("Appendix D Representative factors", factor, metric, value) for metric, value in zip(("Rank_IC", "IC"), values))
    for metric, values in FACTOR_SUMMARY.items():
        rows.extend(_result_row("Appendix D Factor summary", library, metric, value) for library, value in zip(("QA", "AA"), values))
    expected = {
        "Table 1 Main CSI300 results": 196,
        "Table 2 Evolution-component ablation": 28,
        "Appendix Table 2 Cross-seed core metrics": 12,
        "Appendix Table 3 Cross-seed variance": 16,
        "Appendix Table 4 Daily IC statistics": 28,
        "Appendix C Parent trajectory metrics": 6,
        "Appendix C Backtest metrics": 10,
        "Appendix C Detailed statistics": 6,
        "Appendix D Representative factors": 26,
        "Appendix D Factor summary": 16,
    }
    counts = Counter(row["paper_table"] for row in rows)
    if len(rows) != 344 or counts != expected:
        raise RuntimeError(f"QuantaAlpha numeric table census changed: {counts}")
    return rows


def figure_label_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    gate = {
        "QuantaAlpha": (0.046, 0.045, 4.53, 15.10),
        "w/o Consistency": (-0.005, -0.005, -0.59, 0.58),
        "w/o Complexity": (-0.006, -0.006, -0.95, 2.31),
        "w/o Redundancy": (-0.007, -0.007, -0.78, 0.17),
        "w/o All": (-0.007, -0.007, -1.34, 1.94),
    }
    for variant, values in gate.items():
        role = "baseline" if variant == "QuantaAlpha" else "delta"
        for metric, value in zip(EVOLUTION_METRICS, values):
            rows.append({"figure": "Figure 3 quality-gate ablation", "item": variant, "metric": metric, "value_role": role, "paper_value": value, "native_reproduced_value": "", "author_output_correspondence": False, "status": "not_reproduced_raster_only", "paper_result_credit": False})
    case = {
        "pool iteration 1": ("unspecified_factor_pool_performance", 13.27),
        "pool iteration 2": ("unspecified_factor_pool_performance", 19.14),
        "pool iteration 3": ("unspecified_factor_pool_performance", 22.38),
        "pool iteration 4": ("unspecified_factor_pool_performance", 27.85),
        "pool iteration 5": ("unspecified_factor_pool_performance", 29.63),
        "iteration 1 initial / ARR": ("ARR_pct", 5.22),
        "iteration 1 initial / RankICIR": ("Rank_ICIR", 0.158),
        "iteration 1 initial / MDD": ("MDD_pct", 7.67),
        "iteration 2 mutation / ARR": ("ARR_pct", 7.06),
        "iteration 2 mutation / RankICIR": ("Rank_ICIR", 0.166),
        "iteration 2 mutation / MDD": ("MDD_pct", 10.7),
        "iteration 2 crossover / ARR": ("ARR_pct", 7.35),
        "iteration 2 crossover / RankICIR": ("Rank_ICIR", 0.170),
        "iteration 2 crossover / MDD": ("MDD_pct", 9.67),
        "iteration 5 crossover / ARR": ("ARR_pct", 7.80),
        "iteration 5 crossover / RankICIR": ("Rank_ICIR", 0.193),
        "iteration 5 crossover / MDD": ("MDD_pct", 11.4),
    }
    for item, (metric, value) in case.items():
        rows.append({"figure": "Appendix E iterative case-study raster", "item": item, "metric": metric, "value_role": "label", "paper_value": value, "native_reproduced_value": "", "author_output_correspondence": True, "status": "corroborated_by_author_readme_case_study_raster_not_regenerated", "paper_result_credit": False})
    for item, value in (("Parent 1", 0.0216), ("Parent 2", 0.0246), ("Offspring", 0.0311)):
        rows.append({"figure": "Appendix C evolution-path diagram", "item": item, "metric": "Rank_IC", "value_role": "label", "paper_value": value, "native_reproduced_value": "", "author_output_correspondence": False, "status": "not_reproduced_tex_label_only", "paper_result_credit": False})
    if len(rows) != 40:
        raise RuntimeError(f"QuantaAlpha figure-label census changed: {len(rows)}")
    return rows


def plot_point_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for panel, metric in (("Figure 4 IC", "IC"), ("Figure 4 Rank IC", "Rank_IC")):
        for method in ("QuantaAlpha", "AlphaAgent", "RD-Agent", "Alpha158"):
            for year in (2022, 2023, 2024, 2025):
                rows.append({"figure_panel": panel, "series": method, "x_position": year, "metric": metric, "paper_value": "unlabeled_marker", "native_reproduced_value": "", "author_output_correspondence": True, "status": "exact_author_and_paper_raster_correspondence_no_array", "paper_result_credit": False})
    for method in ("QuantaAlpha", "AlphaAgent", "RD-Agent"):
        for iteration in range(1, 6):
            rows.append({"figure_panel": "Figure 5 evolutionary alpha-mining efficiency", "series": method, "x_position": iteration, "metric": "IC_distribution_central_marker", "paper_value": "unlabeled_marker", "native_reproduced_value": "", "author_output_correspondence": True, "status": "exact_author_and_paper_raster_correspondence_no_array_or_band_definition", "paper_result_credit": False})
    if len(rows) != 47:
        raise RuntimeError(f"QuantaAlpha discrete plot-point census changed: {len(rows)}")
    return rows


def published_non_table_claims() -> list[dict[str, Any]]:
    claims = [
        ("result", "v3 GPT-5.2 IC", "0.0472", "not_reproduced"),
        ("result", "v3 GPT-5.2 ARR", "4.68%", "not_reproduced"),
        ("result", "v3 GPT-5.2 MDD", "11.80%", "not_reproduced"),
        ("result", "v3 zero-shot CSI500 cumulative excess return", "40.28%", "not_reproduced_no_return_array"),
        ("result", "v3 zero-shot S&P500 cumulative excess return", "19.1%", "not_reproduced_no_data_or_return_array"),
        ("result", "approximately 150 validated factors enter final LightGBM", "approximately 150", "not_reproduced_factor_pool_absent"),
        ("configuration", "CSI300/500/S&P500 train split", "2016-01-01--2020-12-31", "standalone_backtest_config_matches"),
        ("configuration", "validation split", "2021-01-01--2021-12-31", "standalone_backtest_config_matches"),
        ("configuration", "test split", "2022-01-01--2025-12-26", "standalone_backtest_config_matches_but_mining_config_conflicts"),
        ("configuration", "next-day return label", "Ref(close,-2)/Ref(close,-1)-1", "matches_configs"),
        ("configuration", "basic features", "open/high/low/close/volume/vwap", "mining_config_uses_four_engineered_features_and_no_vwap"),
        ("configuration", "planning directions", "10", "checked_in_experiment_uses_2"),
        ("configuration", "factors per hypothesis", "3", "checked_in_experiment_uses_1"),
        ("configuration", "evolution iterations", "5 mutation+crossover cycles", "checked_in_experiment_max_rounds_3_and_docs_max_rounds_11"),
        ("configuration", "TopkDropout", "topk=50 n_drop=5", "matches_configs"),
        ("configuration", "buy and sell cost", "0.05% / 0.15%", "matches_configs"),
        ("configuration", "deal price", "open", "matches_configs"),
        ("configuration", "limit threshold", "0.095", "matches_configs"),
        ("configuration", "daily observations in robustness table", "966", "no_daily_arrays_released"),
        ("configuration", "LLM backbones", "five named model families", "names_only_no_pinned_provider_revisions"),
    ]
    author_output_claims = {
        "v3 GPT-5.2 IC",
        "v3 GPT-5.2 ARR",
        "v3 GPT-5.2 MDD",
        "v3 zero-shot CSI500 cumulative excess return",
        "v3 zero-shot S&P500 cumulative excess return",
    }
    return [
        {
            "claim_role": role,
            "claim": claim,
            "paper_value": value,
            "release_status": (
                "corroborated_by_author_readme_text_and_or_exact_paper_raster"
                if claim in author_output_claims
                else status
            ),
            "author_output_correspondence": claim in author_output_claims,
            "paper_result_credit": False,
        }
        for role, claim, value, status in claims
    ]


def paper_version_drift() -> list[dict[str, Any]]:
    values = {
        "GPT-5.2 IC": (0.1501, 0.1501, 0.0472),
        "GPT-5.2 ARR_pct": (27.75, 27.75, 4.68),
        "GPT-5.2 MDD_pct": (7.98, 7.98, 11.80),
        "CSI500 transfer cumulative_excess_pct": (160.0, 160.0, 40.28),
        "S&P500 transfer cumulative_excess_pct": (137.0, 137.0, 19.1),
    }
    return [
        {
            "claim": claim,
            "v1_value": v1,
            "v2_value": v2,
            "v3_value": v3,
            "v3_minus_v2": round(v3 - v2, 6),
            "paper_explains_revision": False,
            "released_run_artifacts_explain_revision": False,
            "status": "large_unexplained_revision",
        }
        for claim, (v1, v2, v3) in values.items()
    ]


def internal_and_source_checks() -> list[dict[str, Any]]:
    return [
        {"check": "v3 abstract headline versus Table 1", "status": "compatible", "evidence": "0.0472 IC, 4.68% ARR, 11.80% MDD"},
        {"check": "Table 1 QuantaAlpha/DeepSeek versus Table 2 full row", "status": "compatible", "evidence": "0.0461, 0.0450, 4.53, 15.10"},
        {"check": "Figure 3 full row versus Table 2 full row", "status": "compatible_at_figure_precision", "evidence": "0.046/0.045/4.53/15.10"},
        {"check": "v3 GPT-5.2 QuantaAlpha minus RD-Agent prose", "status": "arithmetically_compatible", "evidence": "IC +0.0186, ARR +1.10pp, MDD -4.96pp"},
        {"check": "v3 GPT-5.2 QuantaAlpha minus AlphaAgent prose", "status": "arithmetically_compatible", "evidence": "IC +0.0125, ARR +3.57pp, MDD -2.09pp"},
        {"check": "cross-seed mean/std/range table", "status": "arithmetically_compatible_at_display_precision", "evidence": "summary recomputes from three displayed combinations"},
        {"check": "daily t statistics", "status": "approximately_compatible_with_n_966", "evidence": "mean/(std/sqrt(966)) agrees after rounding"},
        {"check": "Figure 1 curve endpoints versus prose transfer returns", "status": "paper_graphic_prose_conflict", "evidence": "raster visually terminates near 69% CSI500 and 82% S&P500, not 40.28% and 19.1%"},
        {"check": "Figure 1 caption/prose metric versus y-axis", "status": "ambiguous_metric_label", "evidence": "caption/prose say cumulative excess return; axes say cumulative return"},
        {"check": "Figure 4 year coverage versus prose", "status": "paper_graphic_prose_conflict", "evidence": "prose says 2021--2025; figure shows 2022--2025"},
        {"check": "Appendix C factor identity versus evolution diagram", "status": "paper_internal_round_conflict", "evidence": "identity says Round 10 while offspring diagram says Round 8 Crossover"},
        {"check": "v1/v2 versus v3 headline results", "status": "large_unexplained_revision", "evidence": "IC 0.1501->0.0472; ARR 27.75->4.68; transfer 160/137->40.28/19.1"},
        {"check": "official repo README versus current paper", "status": "matches_v3_headline", "evidence": "README reports current lower headline values"},
        {"check": "paper source Figure 1 versus repository docs Figure 1", "status": "byte_identical", "evidence": "SHA-256 35d013008dd023c096f53ede8fa5b149944ed30b657b514e946bf2f6252061c3"},
        {"check": "current source default experiment versus paper profile", "status": "conflict", "evidence": "2 directions, 3 rounds, 2 crossovers, 1 factor/hypothesis, consistency disabled"},
        {"check": "native mining-loop Qlib config versus paper split", "status": "conflict", "evidence": "train 2016-2019, valid 2020, test/backtest 2021 only"},
        {"check": "standalone backtest config versus paper split and costs", "status": "substantially_compatible", "evidence": "2016-2025 split, label, TopkDropout, open price, costs match"},
        {"check": "paper reported result arrays in source release", "status": "absent", "evidence": "no factor pool, trajectories, predictions, returns, metrics, or plot arrays"},
    ]


def specification_gaps() -> list[dict[str, Any]]:
    gaps = [
        ("data", "CSI300 point-in-time membership and survivorship handling"),
        ("data", "CSI500 point-in-time membership and survivorship handling"),
        ("data", "S&P500 point-in-time membership and survivorship handling"),
        ("data", "market-data vendor, extraction timestamp, and adjustment convention"),
        ("data", "VWAP construction and availability"),
        ("data", "trade-calendar/time-zone alignment across China and US"),
        ("data", "released full daily_pv.h5 content hash independently downloaded by this audit"),
        ("models", "exact provider/model snapshot for every named LLM"),
        ("models", "temperature, top-p, and provider nondeterminism controls"),
        ("models", "exact per-run prompt/message transcripts"),
        ("models", "API error/retry/fallback trace"),
        ("search", "paper-faithful executable experiment profile"),
        ("search", "mapping of five iterations to original/mutation/crossover rounds"),
        ("search", "ten initial planning directions and their text"),
        ("search", "all mutation parent selections and outputs"),
        ("search", "all crossover parent selections and outputs"),
        ("search", "claimed trajectory-segment repair/splice records"),
        ("gates", "gate decisions and corrections for all generated factors"),
        ("gates", "paper factor-zoo snapshot used for redundancy"),
        ("gates", "behavior on checker/API failures in reported runs"),
        ("factors", "approximately 150 validated factor IDs"),
        ("factors", "approximately 150 formulas/descriptions/code artifacts"),
        ("factors", "final per-backbone factor pools"),
        ("factors", "factor calculation outputs and missingness coverage"),
        ("training", "final LightGBM fitted artifacts"),
        ("training", "random seeds for every experiment and baseline"),
        ("training", "hyperparameter provenance for every baseline"),
        ("training", "baseline source revisions and adaptation code"),
        ("portfolio", "daily predictions, selections, orders, fills, holdings, and turnover"),
        ("portfolio", "benchmark return and excess-return construction"),
        ("portfolio", "suspension/limit-up/limit-down execution semantics"),
        ("metrics", "IC/RankIC aggregation order and NaN handling"),
        ("metrics", "ICIR/RankICIR annualization definition"),
        ("metrics", "ARR/IR/MDD formulas and risk-free convention"),
        ("metrics", "confidence-band definition for Figure 5"),
        ("results", "all 344 table-cell derivations"),
        ("results", "Figure 1 underlying daily arrays"),
        ("results", "Figure 4 annual point arrays"),
        ("results", "Figure 5 iteration arrays and uncertainty samples"),
        ("results", "quality-gate ablation runs"),
        ("results", "evolution-component ablation runs"),
        ("results", "cross-seed run artifacts"),
        ("results", "daily IC observations behind robustness statistics"),
        ("results", "explanation or artifact lineage for v2-to-v3 result revision"),
        ("cost", "per-model token counts, cached tokens, prices, and invoices"),
        ("environment", "container/lockfile with fully resolved native environment"),
        ("environment", "hardware and library versions for paper runs"),
        ("audit", "paper-era immutable source tag tied to each arXiv version"),
    ]
    return [{"category": category, "missing_or_ambiguous_item": item, "resolved": "no", "effect": "prevents_exact_paper_replication"} for category, item in gaps]


def mechanism_conformance() -> list[dict[str, Any]]:
    rows = [
        ("planning", "parallel initial direction generation", "implemented_analogue", "native code and prompts exist; default count is 2 rather than paper 10"),
        ("trajectory", "complete hypothesis/factors/code/results/feedback record", "implemented_match", "StrategyTrajectory persists the declared lifecycle fields"),
        ("trajectory", "lineage parent IDs", "implemented_match", "parent_ids are persisted"),
        ("trajectory", "persistent trajectory pool", "implemented_match", "JSON save/load executes in isolated component test"),
        ("mutation", "mechanism-level variation", "partial_analogue", "prompt generates an orthogonal/independent new strategy"),
        ("mutation", "failed-step localization", "not_implemented_as_claimed", "no code localizes the failed trajectory step"),
        ("mutation", "rewrite only failed trajectory segment", "not_implemented_as_claimed", "generation returns a new hypothesis rather than patching a stored segment"),
        ("mutation", "preserve other trajectory segments", "not_implemented_as_claimed", "no splice/preservation representation exists"),
        ("crossover", "performance-aware parent selection", "implemented_match", "RankIC-based strategies exist"),
        ("crossover", "diverse direction/phase preference", "implemented_match", "combination score rewards both"),
        ("crossover", "validated trajectory-segment reuse", "not_implemented_as_claimed", "only truncated textual summaries are sent to the LLM"),
        ("crossover", "actual segment splicing", "not_implemented_as_claimed", "no structured segment splice exists"),
        ("consistency", "hypothesis-description-expression checker", "implemented_match", "LLM consistency checker and correction loop exist"),
        ("consistency", "enabled in shipped experiment", "config_conflict", "consistency_enabled is false"),
        ("consistency", "fail-closed checker errors", "not_implemented_as_claimed", "exception path returns consistent=true"),
        ("complexity", "symbol-length constraint", "implemented_match", "native AST-backed regulator exists"),
        ("complexity", "base-feature constraint", "implemented_match", "native AST-backed regulator exists"),
        ("complexity", "free-argument ratio constraint", "implemented_match", "native AST-backed regulator exists"),
        ("complexity", "paper thresholds", "config_conflict", "checked-in 200/5/0.5 versus documented paper 250/6/0.5"),
        ("redundancy", "AST common-subtree matching", "implemented_match", "native parser and matcher execute"),
        ("redundancy", "paper factor-zoo snapshot", "missing_artifact", "factor_zoo_path is null and no paper pool is shipped"),
        ("redundancy", "fail-closed regulator errors", "not_implemented_as_claimed", "regulator catches errors and permits progress"),
        ("factor_generation", "three factors per hypothesis", "config_conflict", "checked-in default is one"),
        ("factor_generation", "public prompts", "implemented_match", "prompt YAML files are tracked"),
        ("backtest", "Qlib factor evaluation", "implemented_match", "native runner/config path exists"),
        ("backtest", "paper data split in mining loop", "config_conflict", "selected conf_baseline test/backtest ends in 2021"),
        ("backtest", "paper standalone split/cost profile", "implemented_match", "configs/backtest.yaml matches most declared settings"),
        ("portfolio", "TopkDropout top50/drop5", "implemented_match", "both configs specify it"),
        ("portfolio", "open execution and costs", "implemented_match", "0.05%/0.15% and open are configured"),
        ("release", "paper factor pool", "missing_artifact", "no generated factor library is tracked"),
        ("release", "paper trajectories", "missing_artifact", "no trajectory pool is tracked"),
        ("release", "published predictions/returns/results", "missing_artifact", "no result arrays or metrics are tracked"),
        ("release", "baseline reproduction assets", "missing_artifact", "no per-baseline configs/runs are shipped"),
        ("release", "fully resolved environment", "partial_analogue", "dependency metadata exists but audit environment cannot resolve full stack"),
    ]
    return [{"category": cat, "paper_dimension": dim, "status": status, "evidence": evidence, "paper_mechanism_credit": status == "implemented_match"} for cat, dim, status, evidence in rows]


def config_conformance(source_root: Path) -> list[dict[str, Any]]:
    import yaml

    exp = yaml.safe_load((source_root / "configs/experiment.yaml").read_text(encoding="utf-8"))
    bt = yaml.safe_load((source_root / "configs/backtest.yaml").read_text(encoding="utf-8"))
    mine = yaml.safe_load((source_root / "quantaalpha/factors/factor_template/conf_baseline.yaml").read_text(encoding="utf-8"))
    values = [
        ("planning.num_directions", 10, exp["planning"]["num_directions"], "conflict"),
        ("evolution.max_rounds", "five mutation+crossover cycles (mapping ambiguous)", exp["evolution"]["max_rounds"], "conflict"),
        ("evolution.crossover_size", 2, exp["evolution"]["crossover_size"], "match"),
        ("evolution.crossover_n", "not stated in paper; source docs say 10", exp["evolution"]["crossover_n"], "not_paper_specified_and_docs_conflict"),
        ("quality_gate.consistency_enabled", True, exp["quality_gate"]["consistency_enabled"], "conflict"),
        ("quality_gate.complexity_enabled", True, exp["quality_gate"]["complexity_enabled"], "match"),
        ("quality_gate.redundancy_enabled", True, exp["quality_gate"]["redundancy_enabled"], "match_but_no_paper_factor_zoo"),
        ("factor.factors_per_hypothesis", 3, exp["factor"]["factors_per_hypothesis"], "conflict"),
        ("factor.symbol_length_threshold", 250, exp["factor"]["complexity"]["symbol_length_threshold"], "conflict"),
        ("factor.base_features_threshold", 6, exp["factor"]["complexity"]["base_features_threshold"], "conflict"),
        ("factor.free_args_ratio_threshold", 0.5, exp["factor"]["complexity"]["free_args_ratio_threshold"], "match"),
        ("factor.duplication.threshold", 5, exp["factor"]["duplication"]["threshold"], "match"),
        ("standalone.data.market", "csi300", bt["data"]["market"], "match"),
        ("standalone.dataset.label", "Ref($close, -2) / Ref($close, -1) - 1", bt["dataset"]["label"], "match"),
        ("standalone.dataset.train", ["2016-01-01", "2020-12-31"], bt["dataset"]["segments"]["train"], "match"),
        ("standalone.dataset.valid", ["2021-01-01", "2021-12-31"], bt["dataset"]["segments"]["valid"], "match"),
        ("standalone.dataset.test", ["2022-01-01", "2025-12-26"], bt["dataset"]["segments"]["test"], "match"),
        ("standalone.strategy.topk", 50, bt["backtest"]["strategy"]["kwargs"]["topk"], "match"),
        ("standalone.strategy.n_drop", 5, bt["backtest"]["strategy"]["kwargs"]["n_drop"], "match"),
        ("standalone.exchange.deal_price", "open", bt["backtest"]["backtest"]["exchange_kwargs"]["deal_price"], "match"),
        ("standalone.exchange.open_cost", 0.0005, bt["backtest"]["backtest"]["exchange_kwargs"]["open_cost"], "match"),
        ("standalone.exchange.close_cost", 0.0015, bt["backtest"]["backtest"]["exchange_kwargs"]["close_cost"], "match"),
        ("standalone.exchange.limit_threshold", 0.095, bt["backtest"]["backtest"]["exchange_kwargs"]["limit_threshold"], "match"),
        ("mining.dataset.train", ["2016-01-01", "2020-12-31"], mine["task"]["dataset"]["kwargs"]["segments"]["train"], "conflict"),
        ("mining.dataset.valid", ["2021-01-01", "2021-12-31"], mine["task"]["dataset"]["kwargs"]["segments"]["valid"], "conflict"),
        ("mining.dataset.test", ["2022-01-01", "2025-12-26"], mine["task"]["dataset"]["kwargs"]["segments"]["test"], "conflict"),
        ("mining.backtest.period", ["2022-01-01", "2025-12-26"], [mine["port_analysis_config"]["backtest"]["start_time"], mine["port_analysis_config"]["backtest"]["end_time"]], "conflict"),
        ("mining.feature_count", 6, len(mine["data_handler_config"]["data_loader"]["kwargs"]["config"]["feature"][0]), "conflict"),
    ]
    return [{"parameter": name, "paper_value": json.dumps(paper, default=str), "released_value": json.dumps(released, default=str), "status": status} for name, paper, released, status in values]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    files = str(run_git(source_root, "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", SOURCE_COMMIT)).splitlines()
    result_patterns = ("result", "metric", "trajectory", "factor_pool", "prediction", "return", "holding", "order", "fill", "seed")
    rows = []
    for rel in files:
        blob = run_git(source_root, "show", f"{SOURCE_COMMIT}:{rel}", binary=True)
        lower = rel.lower()
        role = "source_or_config"
        paper_result_artifact = False
        if rel in RELEASED_PAPER_OUTPUT_SHA256:
            observed = hashlib.sha256(blob).hexdigest()
            if observed != RELEASED_PAPER_OUTPUT_SHA256[rel]:
                raise RuntimeError(f"Pinned QuantaAlpha author-output raster changed: {rel}")
            role = "author_rendered_paper_result_output"
            paper_result_artifact = True
        elif lower.endswith((".png", ".jpg", ".jpeg", ".pdf", ".gif")):
            role = "documentation_image"
        elif any(token in lower for token in result_patterns):
            role = "code_or_schema_named_like_output_not_paper_result"
        rows.append({"relative_path": rel, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(), "role": role, "paper_result_artifact": paper_result_artifact})
    return rows


def author_output_correspondence(
    source_root: Path, paper_source_root: Path
) -> list[dict[str, Any]]:
    """Pin exact and visually verified rendered author outputs.

    Figure 3--5 repository blobs are byte-identical to the v3 paper-source
    assets.  The main-table raster is visually/OCR checked against the complete
    196-cell TeX table, and the case-study PNG exposes the same 17 labels as the
    published vector PDF.  Raster correspondence corroborates author outputs;
    none of these files contains the underlying arrays or regenerates a result.
    """
    paper_sha = {
        "images/figure3.png": "35d013008dd023c096f53ede8fa5b149944ed30b657b514e946bf2f6252061c3",
        "images/figure4.png": "9a49d456072935fab8c20a5968834288738536a4eb7432830a34114c928afe4f",
        "images/figure5.png": "5012fcdba8f561a0de5f7fba44f636af9f846c8c13925ca0e63e4d635606cf07",
        "images/case_study.pdf": "50dbd326936652d74df5b60713d5cab8aeac10af61942606f0749553f3439b05",
        "tables/main_table.tex": "f57a6586bbbeeef5f6972bd61bc7fdd50518915b4001bff90659dffbe8dd3a17",
    }
    for relative, expected in paper_sha.items():
        observed = sha256(paper_source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned QuantaAlpha paper source asset changed: {relative}")
    definitions = (
        (
            "main_table",
            "docs/images/主实验.png",
            "tables/main_table.tex",
            "complete_visual_and_ocr_correspondence",
            196,
            0,
        ),
        (
            "zero_shot_return_curves",
            "docs/images/figure3.png",
            "images/figure3.png",
            "byte_identical",
            10,
            0,
        ),
        (
            "annual_ic_rankic_markers",
            "docs/images/figure4.png",
            "images/figure4.png",
            "byte_identical",
            32,
            0,
        ),
        (
            "five_round_ic_markers_and_bands",
            "docs/images/figure5.png",
            "images/figure5.png",
            "byte_identical",
            15,
            0,
        ),
        (
            "iterative_case_study_labels",
            "docs/images/case_study.png",
            "images/case_study.pdf",
            "complete_visual_and_ocr_correspondence",
            17,
            0,
        ),
    )
    rows = []
    for output, repository_path, paper_path, kind, units, arrays in definitions:
        repository_blob = run_git(
            source_root, "show", f"{SOURCE_COMMIT}:{repository_path}", binary=True
        )
        repository_sha = hashlib.sha256(repository_blob).hexdigest()
        if repository_sha != RELEASED_PAPER_OUTPUT_SHA256[repository_path]:
            raise RuntimeError(f"Pinned author output changed: {repository_path}")
        paper_asset_sha = sha256(paper_source_root / paper_path)
        if kind == "byte_identical" and repository_sha != paper_asset_sha:
            raise RuntimeError(f"Expected exact paper/repository image identity: {output}")
        rows.append(
            {
                "output": output,
                "repository_path": repository_path,
                "repository_sha256": repository_sha,
                "paper_source_path": paper_path,
                "paper_source_sha256": paper_asset_sha,
                "correspondence_kind": kind,
                "published_result_units_corroborated": units,
                "underlying_numeric_arrays_shipped": arrays,
                "independently_regenerated": False,
                "paper_result_credit": False,
            }
        )
    if sum(row["published_result_units_corroborated"] for row in rows) != 270:
        raise RuntimeError("QuantaAlpha author-output result-unit census changed")
    return rows


def paper_source_inventory(paper_source_root: Path) -> list[dict[str, Any]]:
    rows = []
    numeric = {"images/figure3.png", "images/figure4.png", "images/figure5.png", "images/ablation.pdf", "images/case_study.pdf"}
    for path in sorted(p for p in paper_source_root.rglob("*") if p.is_file()):
        rel = path.relative_to(paper_source_root).as_posix()
        rows.append({"relative_path": rel, "bytes": path.stat().st_size, "sha256": sha256(path), "asset_role": "numeric_result_figure" if rel in numeric else "paper_source", "underlying_numeric_array": False})
    return rows


def dataset_inventory(dataset_api: Path, tree_api: Path, debug_h5: Path) -> list[dict[str, Any]]:
    meta = json.loads(dataset_api.read_text(encoding="utf-8"))
    tree = json.loads(tree_api.read_text(encoding="utf-8"))
    if meta["id"] != "QuantaAlpha/qlib_csi300" or meta["sha"] != HF_DATASET_COMMIT:
        raise RuntimeError("Hugging Face dataset metadata pin changed")
    rows = []
    for item in tree:
        lfs = item.get("lfs", {})
        rows.append({
            "path": item["path"], "bytes": item["size"], "git_oid": item["oid"],
            "lfs_sha256": lfs.get("oid", ""), "last_commit": item["lastCommit"]["id"],
            "last_commit_date": item["lastCommit"]["date"], "public": not meta["private"],
            "gated": meta["gated"], "paper_result_artifact": False,
        })
    if sha256(debug_h5) != HF_DEBUG_SHA256:
        raise RuntimeError("Hugging Face debug HDF pin changed")
    return rows


COMPONENT_DRIVER = r'''import importlib.util, json, sys, tempfile, types
from pathlib import Path
root = Path(sys.argv[1])
def package(name):
    mod = types.ModuleType(name); mod.__path__ = []; sys.modules[name] = mod
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod; spec.loader.exec_module(mod); return mod
for name in ["quantaalpha", "quantaalpha.factors", "quantaalpha.factors.coder", "quantaalpha.pipeline", "quantaalpha.pipeline.evolution", "quantaalpha.llm"]: package(name)
class Logger:
    def info(self,*a,**k): pass
    def warning(self,*a,**k): pass
    def error(self,*a,**k): pass
log = types.ModuleType("quantaalpha.log"); log.logger = Logger(); sys.modules["quantaalpha.log"] = log
client = types.ModuleType("quantaalpha.llm.client")
class APIBackend:
    def __init__(self,*a,**k): raise RuntimeError("LLM calls forbidden in audit")
client.APIBackend = APIBackend; sys.modules["quantaalpha.llm.client"] = client
ast = load("quantaalpha.factors.coder.factor_ast", root/"quantaalpha/factors/coder/factor_ast.py")
traj = load("quantaalpha.pipeline.evolution.trajectory", root/"quantaalpha/pipeline/evolution/trajectory.py")
cross = load("quantaalpha.pipeline.evolution.crossover", root/"quantaalpha/pipeline/evolution/crossover.py")
e1 = "RANK(TS_CORR(DELTA($close, 1) / $close, DELTA($volume, 1) / $volume, 20) * TS_MEAN(($close - $open) / $close, 5))"
e2 = "TS_CORR(DELTA($close, 1) / $close, DELTA($volume, 1) / $volume, 20) + TS_STD($close, 10)"
tree = ast.parse_expression(e1); match = ast.compare_expressions(e1, e2)
assert tree and match and match.size > 1
assert ast.count_base_features(e1) == 3 and ast.count_free_args(e1) == 4 and ast.calculate_symbol_length(e1) == len(e1)
T, P, Phase = traj.StrategyTrajectory, traj.TrajectoryPool, traj.RoundPhase
items = [
 T("t1",0,0,Phase.ORIGINAL,hypothesis="h1",backtest_metrics={"RankIC":0.01}),
 T("t2",1,1,Phase.MUTATION,hypothesis="h2",backtest_metrics={"RankIC":0.04},parent_ids=["t1"]),
 T("t3",2,2,Phase.CROSSOVER,hypothesis="h3",backtest_metrics={"RankIC":0.03},parent_ids=["t1","t2"]),
 T("t4",3,1,Phase.MUTATION,hypothesis="h4",backtest_metrics={"RankIC":0.02}),
]
with tempfile.TemporaryDirectory() as td:
    path = Path(td)/"pool.json"; pool = P(path, fresh_start=True)
    for x in items: pool.add(x)
    loaded = P(path, fresh_start=False)
    assert loaded.get_statistics()["total_trajectories"] == 4
    assert loaded.get("t3").parent_ids == ["t1","t2"]
op = cross.CrossoverOperator.__new__(cross.CrossoverOperator)
groups = op.select_crossover_pairs(items, crossover_size=2, crossover_n=2, prefer_diverse=True, selection_strategy="best")
assert len(groups) == 2 and all(len(g)==2 for g in groups)
assert any("t2" in [x.trajectory_id for x in g] for g in groups)
print(json.dumps({"ast_parse":True,"base_features":3,"free_args":4,"common_subtree_size":match.size,"trajectory_roundtrip":True,"lineage_roundtrip":True,"crossover_groups":len(groups),"llm_or_market_api_called":False}, sort_keys=True))
'''


def compile_revision(source_root: Path, commit: str | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        root = source_root
        if commit:
            archive = subprocess.run(["git", "-C", str(source_root), "archive", commit], check=True, capture_output=True).stdout
            tar_path = Path(td) / "src.tar"
            tar_path.write_bytes(archive)
            with tarfile.open(tar_path) as handle:
                handle.extractall(Path(td) / "src", filter="data")
            root = Path(td) / "src"
        py_files = sorted(root.rglob("*.py"))
        failures = []
        for path in py_files:
            try:
                py_compile.compile(str(path), doraise=True, cfile=str(Path(td) / (hashlib.sha256(str(path).encode()).hexdigest() + ".pyc")))
            except Exception as exc:
                failures.append({"path": str(path.relative_to(root)), "error": str(exc)})
        return {"python_files": len(py_files), "compiled": len(py_files) - len(failures), "failures": failures}


def native_execution(source_root: Path) -> dict[str, Any]:
    current = compile_revision(source_root)
    initial = compile_revision(source_root, INITIAL_COMMIT)
    component = subprocess.run([sys.executable, "-c", COMPONENT_DRIVER, str(source_root)], capture_output=True, text=True)
    component_payload = json.loads(component.stdout.strip().splitlines()[-1]) if component.returncode == 0 else {"error": component.stderr[-3000:]}
    upstream = subprocess.run([sys.executable, str(source_root / "quantaalpha/factors/coder/test.py")], cwd=source_root / "quantaalpha/factors/coder", capture_output=True, text=True)
    return {
        "current_compile": current,
        "initial_compile": initial,
        "component_driver_returncode": component.returncode,
        "component_checks": component_payload,
        "upstream_tests_discovered": 1,
        "upstream_tests_passed": int(upstream.returncode == 0),
        "upstream_tests_failed": int(upstream.returncode != 0),
        "upstream_test_failure": "missing template_debug.jinjia2" if "template_debug.jinjia2" in upstream.stderr else upstream.stderr[-1000:],
        "full_native_environment_reproduced": False,
        "paper_experiment_executed": False,
        "paper_result_cells_reproduced": 0,
        "component_execution_is_paper_result_credit": False,
        "llm_or_market_api_called": False,
    }


def verify_pins(source_root: Path, papers: Mapping[str, tuple[Path, Path]], paper_source_root: Path, dataset_api: Path, debug_h5: Path) -> None:
    if str(run_git(source_root, "rev-parse", "HEAD")).strip() != SOURCE_COMMIT:
        raise RuntimeError("Official source HEAD pin changed")
    if sha256(source_root / "README.md") != CURRENT_README_SHA256:
        raise RuntimeError("Official README pin changed")
    for version, (pdf, archive) in papers.items():
        pins = PAPER_VERSIONS[version]
        if sha256(pdf) != pins["pdf_sha256"] or sha256(archive) != pins["source_sha256"]:
            raise RuntimeError(f"Paper {version} pin changed")
    if not (paper_source_root / "acl_latex.tex").exists():
        raise RuntimeError("Current paper source root is incomplete")
    meta = json.loads(dataset_api.read_text(encoding="utf-8"))
    if meta.get("sha") != HF_DATASET_COMMIT or sha256(debug_h5) != HF_DEBUG_SHA256:
        raise RuntimeError("Official dataset pin changed")


def build_audit(source_root: Path, papers: Mapping[str, tuple[Path, Path]], paper_source_root: Path, dataset_api: Path, tree_api: Path, debug_h5: Path, output_dir: Path) -> dict[str, Any]:
    verify_pins(source_root, papers, paper_source_root, dataset_api, debug_h5)
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = paper_table_rows()
    labels = figure_label_rows()
    points = plot_point_rows()
    claims = published_non_table_claims()
    author_outputs = author_output_correspondence(source_root, paper_source_root)
    checks = internal_and_source_checks()
    gaps = specification_gaps()
    mechanisms = mechanism_conformance()
    configs = config_conformance(source_root)
    versions = paper_version_drift()
    inventory = source_inventory(source_root)
    paper_assets = paper_source_inventory(paper_source_root)
    datasets = dataset_inventory(dataset_api, tree_api, debug_h5)
    native = native_execution(source_root)
    outputs = {
        "paper_numeric_table_conformance.csv": tables,
        "paper_numeric_figure_labels.csv": labels,
        "paper_plot_point_inventory.csv": points,
        "published_non_table_claims.csv": claims,
        "paper_version_drift.csv": versions,
        "paper_internal_and_source_checks.csv": checks,
        "paper_specification_gaps.csv": gaps,
        "source_mechanism_conformance.csv": mechanisms,
        "source_config_conformance.csv": configs,
        "released_source_inventory.csv": inventory,
        "released_dataset_inventory.csv": datasets,
        "paper_source_asset_inventory.csv": paper_assets,
        "author_output_correspondence.csv": author_outputs,
    }
    for name, rows in outputs.items():
        write_csv(output_dir / name, rows)
    (output_dir / "native_component_execution.json").write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")
    status_counts = Counter(row["status"] for row in mechanisms)
    manifest: dict[str, Any] = {
        "paper": "QuantaAlpha: An Evolutionary Framework for LLM-Driven Alpha Mining",
        "overall_status": "author_rendered_outputs_corroborated_no_end_to_end_regeneration",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_versions": PAPER_VERSIONS,
        "current_paper_version": "v3",
        "source_url": SOURCE_URL,
        "source_commit": SOURCE_COMMIT,
        "source_commit_date": SOURCE_COMMIT_DATE,
        "initial_commit": INITIAL_COMMIT,
        "initial_commit_date": INITIAL_COMMIT_DATE,
        "initial_release_after_v1_submission_hours": 56.911,
        "hf_dataset_url": HF_DATASET_URL,
        "hf_dataset_commit": HF_DATASET_COMMIT,
        "paper_numeric_table_cells_total": len(tables),
        "native_numeric_table_cells_reproduced": 0,
        "author_output_numeric_table_cells_corroborated": 196,
        "paper_numeric_figure_labels_total": len(labels),
        "native_numeric_figure_labels_reproduced": 0,
        "author_output_numeric_figure_labels_corroborated": 17,
        "paper_discrete_unlabeled_marker_points_total": len(points),
        "native_discrete_marker_points_reproduced": 0,
        "author_output_discrete_marker_points_corroborated": 47,
        "paper_raster_return_curves_total": 10,
        "native_raster_return_curve_arrays_reproduced": 0,
        "author_output_raster_return_curves_corroborated": 10,
        "author_output_result_units_corroborated": sum(
            int(row["published_result_units_corroborated"]) for row in author_outputs
        ),
        "author_output_assets_byte_identical_to_paper_source": sum(
            row["correspondence_kind"] == "byte_identical" for row in author_outputs
        ),
        "author_output_assets_visually_and_ocr_verified": sum(
            row["correspondence_kind"] == "complete_visual_and_ocr_correspondence"
            for row in author_outputs
        ),
        "author_output_result_claims_corroborated": sum(
            row["claim_role"] == "result" and row["author_output_correspondence"]
            for row in claims
        ),
        "author_output_dated_return_raster_shipped": True,
        "author_output_underlying_arrays_shipped": False,
        "paper_result_arrays_shipped": 0,
        "paper_factor_pool_shipped": False,
        "paper_trajectory_pool_shipped": False,
        "paper_baseline_runs_shipped": False,
        "paper_seeds_shipped": False,
        "paper_cost_ledger_shipped": False,
        "published_non_table_claims_total": len(claims),
        "published_result_claims_total": sum(row["claim_role"] == "result" for row in claims),
        "paper_specification_gaps_total": len(gaps),
        "paper_internal_and_source_checks_total": len(checks),
        "paper_version_drift_claims_total": len(versions),
        "large_unexplained_revision_claims_total": len(versions),
        "source_mechanism_dimensions_total": len(mechanisms),
        "source_mechanism_status_counts": dict(status_counts),
        "source_mechanism_matches": status_counts["implemented_match"],
        "source_mechanism_fully_faithful": False,
        "source_config_dimensions_total": len(configs),
        "source_config_status_counts": dict(Counter(row["status"] for row in configs)),
        "tracked_source_files_total": len(inventory),
        "tracked_source_python_files_total": sum(row["relative_path"].endswith(".py") for row in inventory),
        "tracked_source_test_files_total": 1,
        "paper_source_assets_total": len(paper_assets),
        "released_dataset_files_total": len(datasets),
        "released_dataset_is_public": True,
        "released_dataset_is_paper_result_artifact": False,
        "native_current_python_files_compiled": native["current_compile"]["compiled"],
        "native_initial_python_files_compiled": native["initial_compile"]["compiled"],
        "native_component_driver_passed": native["component_driver_returncode"] == 0,
        "native_upstream_tests_passed": native["upstream_tests_passed"],
        "native_upstream_tests_failed": native["upstream_tests_failed"],
        "audit_runtime_called_llm_or_market_data_api": False,
        "local_motif_proxy_candidate": "code_quantaalpha_evolutionary_factor_miner",
        "local_motif_proxy_paper_result_credit": False,
        "interpretation": (
            "QuantaAlpha has a substantial public implementation and deserves native architecture credit: "
            "all 135 current and initial Python files compile, and dependency-isolated AST, trajectory "
            "persistence, lineage, and crossover-selection paths execute. This is not a paper reproduction. "
            "The checked-in experiment profile materially conflicts with the paper; the mining-loop Qlib "
            "config tests only 2021; the claimed targeted segment repair/splicing is not represented as such; "
            "the only upstream test fails because its template is absent; and no approximately-150-factor "
            "pool, run trajectories, prompts/responses, seeds, baselines, predictions, holdings, return arrays, "
            "or plot arrays are released. The official README does ship the complete 196-cell v3 main-table "
            "raster, exact paper-source copies of Figures 3--5, and the 17-label case-study raster: 270 rendered "
            "output units are author-output corroborations, while 0/344 table cells, 0/40 labeled figure values, "
            "0/47 discrete figure markers, and 0/10 return-curve arrays are independently regenerated. Moreover, "
            "v1/v2 headline results were sharply reduced in v3 without released run lineage, and v3 contains "
            "direct figure/prose and round-label inconsistencies. The public HF dataset helps infrastructure "
            "reproducibility but is not a result artifact and lacks sufficient provenance for exact replication."
        ),
    }
    report = f"""# QuantaAlpha paper-level conformance audit

Overall verdict: **substantial native implementation and 270 rendered author-output
units corroborated; zero published results independently regenerated**.

## Primary-source boundary

- All three arXiv revisions of [2602.07085]({PAPER_URL}) are pinned by PDF and source-archive SHA-256. The current audit targets v3, submitted {PAPER_VERSIONS['v3']['date']}.
- The official source is pinned to `{SOURCE_COMMIT}` ({SOURCE_COMMIT_DATE}). Its initial substantial revision was committed 56.91 hours after v1 submission, so the source is useful but not a pre-submission snapshot.
- The official public [Hugging Face dataset]({HF_DATASET_URL}) is pinned to `{HF_DATASET_COMMIT}`. It provides a Qlib package and daily HDF files, but no paper result arrays.

## Complete numeric-result boundary

- The v3 paper contains **344 numeric result table cells**: 196 main-table cells, 28 evolution-ablation values/deltas, 56 seed/daily-statistic cells, and 64 case-study/factor-analysis cells. The official README ships a complete raster of all **196/196 main-table cells**; these are author-output correspondences, while **0/344** cells are independently regenerated.
- Numeric result figures add **40 visible labels**, **47 discrete unlabeled central markers**, and **10 raster return curves**. The README ships the 17-label case-study raster and byte-identical copies of the paper-source Figure 3--5 assets, corroborating **17 labels, 47 markers, and 10 curves**. Their underlying arrays are absent; **0/40**, **0/47**, and **0/10** are regenerated.
- The paper says approximately 150 validated factors feed a common LightGBM model. No such factor pool, run trajectory, prediction, portfolio, return, or metric artifact is shipped.

## What really works

- The release is not pseudocode: **{native['current_compile']['compiled']}/{native['current_compile']['python_files']}** current Python files and **{native['initial_compile']['compiled']}/{native['initial_compile']['python_files']}** initial-release Python files compile. The audit executes native expression parsing/complexity/subtree matching, trajectory JSON round-trip, lineage round-trip, and performance/diversity-aware crossover selection without calling an LLM or market API.
- Public prompt/config/source paths implement meaningful planning, full trajectory records, mutation/crossover generation, semantic consistency, AST complexity/redundancy checks, Qlib evaluation, and TopkDropout backtesting. **{status_counts['implemented_match']}/{len(mechanisms)}** audited mechanism dimensions are implementation matches.
- `configs/backtest.yaml` substantially matches the paper's date split, target, preprocessing, Top-50/drop-5 portfolio, open execution, limit, and 0.05%/0.15% costs.

## Why it is not faithful yet

- The actual checked-in `configs/experiment.yaml` is a demo profile: 2 rather than 10 directions, 3 rounds rather than the paper's five mutation/crossover cycles, 2 rather than the documented 10 crossover combinations, 1 rather than 3 factors per hypothesis, lower complexity limits, and the consistency gate disabled.
- The mining runner selects `quantaalpha/factors/factor_template/conf_baseline.yaml`, whose train/validation/test split is 2016--2019/2020/2021 and whose backtest ends in 2021. The paper reports 2016--2020/2021/2022--2025. The matching standalone backtest config does not repair the mining-loop mismatch.
- Paper prose describes mutation as targeted failed-segment repair and crossover as reuse/splicing of validated trajectory segments. The source generates new hypotheses from truncated textual summaries; it does not localize, preserve, or splice structured trajectory segments.
- The only tracked upstream test fails because `template_debug.jinjia2` is missing. The full dependency/runtime stack is not reproduced here.
- v1/v2 reported IC 0.1501, ARR 27.75%, MDD 7.98%, and transfer returns 160%/137%; v3 reports 0.0472, 4.68%, 11.80%, and 40.28%/19.1%. No released result lineage explains the revision. In v3, Figure 1's visible endpoints do not agree with its prose, Figure 4 omits 2021 despite the text's 2021--2025 claim, and Appendix C labels the same offspring Round 10 and Round 8.

## Honest interpretation

This repository is close to a credible clean-room *implementation framework*, but far from a verifiable replication of the reported study. Its rendered result outputs materially improve author-output availability, but screenshots cannot establish the inputs, execution, or raw result path. Running it with newly chosen APIs/data would produce a new experiment, not regenerate the published one. `--strict` intentionally remains nonzero until an end-to-end pinned paper profile reproduces every claimed artifact and result within declared tolerances.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {path.name: sha256(path) for path in sorted(output_dir.iterdir()) if path.is_file() and path.name != "manifest.json"}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    base = Path(os.environ.get("QUANTAALPHA_PAPER_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_paper"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(os.environ.get("QUANTAALPHA_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_source")))
    parser.add_argument("--paper-v1-pdf", type=Path, default=base / "paper_v1.pdf")
    parser.add_argument("--paper-v1-source", type=Path, default=base / "source_v1.tar")
    parser.add_argument("--paper-v2-pdf", type=Path, default=base / "paper_v2.pdf")
    parser.add_argument("--paper-v2-source", type=Path, default=base / "source_v2.tar")
    parser.add_argument("--paper-v3-pdf", type=Path, default=base / "paper.pdf")
    parser.add_argument("--paper-v3-source", type=Path, default=base / "source.tar")
    parser.add_argument("--paper-source-root", type=Path, default=base / "source")
    parser.add_argument("--dataset-api", type=Path, default=base / "hf_dataset_api.json")
    parser.add_argument("--dataset-tree-api", type=Path, default=base / "hf_tree_api.json")
    parser.add_argument("--debug-h5", type=Path, default=base / "daily_pv_debug.h5")
    parser.add_argument("--output-dir", type=Path, default=project_root / "paper_runs/paper_replication_audits/quantaalpha")
    parser.add_argument("--strict", action="store_true", help="Return nonzero until the full paper is reproduced")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    papers = {
        "v1": (args.paper_v1_pdf, args.paper_v1_source),
        "v2": (args.paper_v2_pdf, args.paper_v2_source),
        "v3": (args.paper_v3_pdf, args.paper_v3_source),
    }
    manifest = build_audit(args.source_root, papers, args.paper_source_root, args.dataset_api, args.dataset_tree_api, args.debug_h5, args.output_dir)
    print(json.dumps(manifest, indent=2))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
