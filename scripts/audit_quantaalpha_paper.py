#!/usr/bin/env python3
"""Fail-closed paper-level audit of QuantaAlpha and its public source lineage.

The audit pins all three arXiv revisions, the official Git revision, and the
official Hugging Face data release.  It enumerates every numeric result cell
in the current paper, inventories numeric figures separately, executes safe
dependency-isolated components of the native source, and distinguishes exact
author-output correspondence from independent result regeneration.  It also
pins the author-attributed pre-publication lineage recovered from public pull
request/fork refs, its factor pools and aggregate result JSONs, and a native
rerun against recovered author data.  Aggregate artifacts corroborate lineage;
they never substitute for predictions, returns, holdings, or raw plot arrays.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import py_compile
import re
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
# ``INITIAL_COMMIT`` is only the first commit reachable from the five current
# official branch heads.  It is not the beginning of the complete public
# QuantaAlpha lineage.  Public PR/fork refs preserve this author-attributed,
# first-parent, pre-publication sequence.
PREPUBLICATION_START_COMMIT = "3c21b90abc88d5ece9359940b3993db25c71e2ad"
PREPUBLICATION_START_DATE = "2026-01-15T16:32:16+08:00"
PREPUBLICATION_RESULTS_COMMIT = "8a034319ff925d9dc621077ebf97d48e1890dad2"
PREPUBLICATION_RESULTS_DATE = "2026-01-23T03:18:06+08:00"
PREPUBLICATION_RELEASE_COMMIT = "04df1a96adfdb26c8bf3c3ec4bfb3aca6aa08ede"
PREPUBLICATION_RELEASE_DATE = "2026-01-28T22:14:18+08:00"
PREPUBLICATION_COMMIT_COUNT = 28
PREPUBLICATION_COMMIT_SHA256 = "1288000c0b9fed423f48791de5fb8c4065059a5d21486e29956e15b79b5a8edf"
PREPUBLICATION_PATH_COUNT = 851
PREPUBLICATION_PATH_SHA256 = "30f2e513750080df391dac521a209036314d24955568d543fcd2b33035ea6b03"
PREPUBLICATION_RELEASE_LEAD_HOURS = 209.8961111111111
PUBLIC_BRANCH_HEADS = {
    "anonymous": "418758f9f7b9f324d6ed43ed807ce94872198aa9",
    "dependabot/pip/prod-1f4a4f1c40": "28f1619565001df99721f7b11e1cfb127bb31103",
    "fix_win": "453e5752c5805407147e31b6cb19cb5e8bfa21d9",
    "main": SOURCE_COMMIT,
    "windows": "c9d55b5c4cf55c77be421450acd72bd41d8b9abb",
}
PUBLIC_HISTORY_COMMIT_COUNT = 61
PUBLIC_HISTORY_COMMIT_SHA256 = "b80b2012e992519f128940ccfd9776c2d8cd9c4d4ee8f4c41f9fddd04e12c179"
PUBLIC_HISTORY_PATH_COUNT = 259
PUBLIC_HISTORY_PATH_SHA256 = "83193eff0de95293fdd842b9b59518cdc9407ee34a639dbe022e177c67c559fc"
PUBLIC_HISTORY_OBJECT_COUNTS = {"blob": 410, "tree": 242, "commit": 61}
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
# GitHub's REST metadata reported 279 forks, while GraphQL could enumerate 267
# accessible fork repositories on the checked date.  The 12-repository gap is
# retained rather than silently pretending that deleted/private/unavailable
# forks were inspectable.
PUBLIC_FORK_REST_COUNT = 279
PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT = 267
PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT = 357
PUBLIC_FORK_GRAPHQL_REF_SHA256 = "f5353dac01829a8d0fdd86dad17f15759a0ae246b6d529b41a4627ca87acb145"
PUBLIC_FORK_REPRESENTATIVE_REF_COUNT = 77
PUBLIC_FORK_REPRESENTATIVE_REF_SHA256 = "4fc1a8f2d7ae74f490640ef3e8ca87744487b43a1bf01f9c686b82e867eb08bb"
PUBLIC_FORK_UNIQUE_HEAD_SHA256 = "8abe066e04c1ef4ab6709a68328f2dfeb6a878ade1e0546a42a1fc6306a217d0"
PUBLIC_FORK_BASE_REACHABLE_HEAD_COUNT = 13
PUBLIC_FORK_DIVERGENT_HEAD_COUNT = 64
AUTHOR_POST_V1_FORK_HEADS = (
    "af0a9982567efddc3f102fccd315c33cc9b5647b",
    "6201cf80f9901bfccd91ab8eade0610a7eecfe1a",
    "225e9cca55700a851cc4da2cbfc7a0b49c623ee9",
    "ac819184beccce6103784f0a1ff229ff9e4f3fa7",
    "05d1b3b7174027ef8d79c5547387160037013fd8",
    "3227d1aeccde7de10d96cd7b7b41f72a515dfd54",
    "d012dab2d6889a7ea048c4e48c54239092ddb097",
    "36738317f6af2352994ee5d7a4413bfaac76e23b",
    "7f5e5a38fcb82e49e819678301ad7b56434c9797",
)
AUTHOR_POST_V1_EXTRA_COMMIT_COUNT = 28
AUTHOR_POST_V1_EXTRA_COMMIT_SHA256 = "7734e0a09af7c222f7119f6a168ed93481dace82be5ed15ce1dc4e72a5c7f11c"
AUTHOR_POST_V1_CHANGED_PATH_COUNT = 259
AUTHOR_POST_V1_CHANGED_PATH_SHA256 = "1fb30ebf69f94c09513def0a8b98eab0fb99de1614726be345d1fe3ec8b18f62"
AUTHOR_POST_V1_EMAILS = {
    "hanjun1650782738@126.com",
    "964280783@qq.com",
    "lw0901@example.com",
}
AUTHOR_POST_V1_NEW_DOC_IMAGE_BLOB = "ca2483ade1ea71f6bdabe760f9aa633e0038cede"
AUTHOR_POST_V1_NEW_DOC_IMAGE_SHA256 = "04188f1802fba0f967abacef2de7d36831446ebb77f4afcbcc92e29d82fd871c"
AUTHOR_POST_V1_NEW_DOC_IMAGE_BYTES = 236_909
UNAFFILIATED_SUMMARY_HEAD = "6ed6e1713f0e932b6c0a7641547e30530e425862"
UNAFFILIATED_SUMMARY_PATH = "data/results/alpha_test_final_report.json"
UNAFFILIATED_SUMMARY_SHA256 = "437f0722434416f1086a60f01770d2fff58506512a32d7eef55d13887c2300b8"
UNAFFILIATED_SUMMARY_BYTES = 4_428
DISCOVERY_SHA256 = {
    "branches.json": "be6243fec5525a694c2a72cd28f4ebe71f2bd642ad141974a54a68863ec98fd9",
    "releases.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "tags.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}
HISTORICAL_MAIN_TABLE_RASTERS = {
    "docs/images/主实验.png": "c5272933b3f87c77d28e516bc55f23dc25701a38f0391ccc6248b2b7054dbc33",
    "images/主实验.png": "aa0ad5d81e36870570a9b23b00940e7a6244eb57a7ae87d9219276d499befbd1",
}
V1_V2_MAIN_TABLE_SHA256 = "206b0c14959311a7146174cca7ed77168aaa2c6f73c0b4594272b04b6ec907ef"
NATIVE_RESULT_SUFFIXES = (
    ".csv",
    ".feather",
    ".h5",
    ".hdf5",
    ".jsonl",
    ".log",
    ".npy",
    ".npz",
    ".parquet",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
    ".ckpt",
)
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

AUTHOR_DAILY_PV_LFS_SHA256 = "19ed8ee62db6a1fbd1e0f58e76b65dadd9991d666e3b0b8d3faab257fd81f53f"
AUTHOR_DAILY_PV_LFS_BYTES = 308_774_188
FORK_QLIB_ARCHIVE_SHA256 = "233485a9035d5d0092736d336605f38474129f5c2673b8a00d046cc6e4e88542"
FORK_QLIB_ARCHIVE_BYTES = 492_502_328
RECOVERED_PROVIDER_MATRIX_SHA256 = "5b50aa45aaaf925efc9bfdc2dedb6e4211e3ee6297abaeccf3b356ee90609c4e"

RERUN_ENVIRONMENT = {
    "python": "3.12.3",
    "pyqlib": "0.9.7",
    "numpy": "2.4.1",
    "pandas": "2.3.3",
    "joblib": "1.5.3",
    "lightgbm": "4.6.0",
    "mlflow": "3.8.1",
    "scipy": "1.17.0",
    "scikit_learn": "1.8.0",
    "tables": "3.10.2",
    "numexpr": "2.14.1",
}
ALPHA158_20_NATIVE_METRICS = {
    "IC": 0.005071733580974592,
    "ICIR": 0.03287938627233083,
    "Rank_IC": 0.01838526953812549,
    "Rank_ICIR": 0.11770777250034052,
    "IR": 0.5043710541234949,
    "CR": 0.20865323814507192,
    "ARR_pct": 4.629928329578073,
    "MDD_pct": 22.18958292110946,
}
QA_GPT_COMBINED_168_NATIVE_METRICS = {
    "IC": 0.04169854922210531,
    "ICIR": 0.24708259038837793,
    "Rank_IC": 0.040913089744675654,
    "Rank_ICIR": 0.2451467139839747,
    "IR": 0.8773766571791948,
    "CR": 0.5073516482894166,
    "ARR_pct": 6.052344883424508,
    "MDD_pct": 11.929289879771857,
}

# Curated aggregate artifacts with the strongest rounded correspondence to the
# v1/v2 table.  Filename/model alignment is recorded separately because a
# numerical match alone cannot prove that a mislabeled artifact generated a
# given paper row.
PREPUBLICATION_RESULT_ARTIFACTS = {
    "row_11:Alpha158(20)": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/alpha158_20_backtest_metrics.json",
        "exact_method_filename",
    ),
    "row_19:Qwen3-235B": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/RANKIC_desc_80_AA_qwen_123_csi300_backtest_metrics.json",
        "exact_method_filename",
    ),
    "row_20:Deepseek-V3.2": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/random_80_AA_deepseek_123_csi300_backtest_metrics.json",
        "exact_method_filename",
    ),
    "row_21:Gemini-3-pro-preview": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/AA_top50_rankic_backtest_metrics.json",
        "numeric_correspondence_filename_not_model_specific",
    ),
    "row_22:Claude-4.5-sonnet": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/random_80_AA_claude_123_csi300_backtest_metrics.json",
        "exact_method_filename",
    ),
    "row_23:GPT-5.2": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/AA_top80_RankIC_AA_gpt_123_csi300_backtest_metrics.json",
        "exact_method_filename",
    ),
    "row_24:Qwen3-235B": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/RANKIC_desc_150_QA_round11_best_deepseek_aliyun_123_csi300_backtest_metrics.json",
        "numeric_correspondence_filename_conflicts_with_paper_model",
    ),
    "row_25:Deepseek-V3.2": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/RANKIC_desc_phase_mutation_150_QA_round11_best_deepseek_123_csi300_backtest_metrics.json",
        "exact_method_filename",
    ),
    "row_26:Gemini-3-pro-preview": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/random_150_RANKIC_desc_phase_mutation_300_QA_round11_best_gemini_123_backtest_metrics.json",
        "exact_method_filename",
    ),
    "row_27:Claude-4.5-sonnet": (
        "6f1586343cae1bd628f239b0d6da4e327e898091",
        "backtest_v2_results/RANKIC_desc_150_QA_round11_best_claude_123_csi300_backtest_metrics.json",
        "exact_method_filename",
    ),
    "row_28:GPT-5.2": (
        PREPUBLICATION_RESULTS_COMMIT,
        "backtest_v2_results/RANKIC_desc_150_QA_round11_best_gpt_123_csi300_backtest_metrics.json",
        "exact_method_filename",
    ),
}

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
    result = subprocess.run(["git", "-C", str(source_root), *args], check=True, capture_output=True, text=not binary)
    return result.stdout


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256_lines(lines: Sequence[str]) -> str:
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def _historical_paths(source_root: Path) -> list[str]:
    payload = subprocess.run(
        [
            "git",
            "-C",
            str(source_root),
            "-c",
            "core.quotePath=false",
            "log",
            "--all",
            "--pretty=format:",
            "--name-only",
            "-z",
        ],
        check=True,
        capture_output=True,
    ).stdout
    return sorted(
        {part.decode("utf-8") for part in payload.split(b"\0") if part},
        key=lambda item: item.encode("utf-8"),
    )


def _history_path_role(path: str) -> str:
    lower = path.lower()
    if path in HISTORICAL_MAIN_TABLE_RASTERS or path in RELEASED_PAPER_OUTPUT_SHA256:
        return "author_rendered_result_output"
    if lower.startswith("frontend-v2/"):
        return "historical_operational_frontend_or_bridge"
    if lower.endswith(NATIVE_RESULT_SUFFIXES):
        return "native_result_artifact_candidate"
    if lower.endswith(".json"):
        return "configuration_or_software_descriptor_json"
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".pdf")):
        return "documentation_image_or_document"
    return "source_config_or_documentation"


def public_source_history(
    source_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Audit every reachable public commit/path and fail closed on release drift."""
    if str(run_git(source_root, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise RuntimeError("QuantaAlpha source history is shallow")

    discovery_root = source_root / "release-discovery"
    for name, expected in DISCOVERY_SHA256.items():
        path = discovery_root / name
        if sha256(path) != expected:
            raise RuntimeError(f"Pinned GitHub release-discovery response changed: {name}")
    branches_payload = json.loads((discovery_root / "branches.json").read_text(encoding="utf-8"))
    discovered_heads = {item["name"]: item["commit"]["sha"] for item in branches_payload}
    if discovered_heads != PUBLIC_BRANCH_HEADS:
        raise RuntimeError(f"Public QuantaAlpha branch heads changed: {discovered_heads}")
    if json.loads((discovery_root / "tags.json").read_text(encoding="utf-8")) != []:
        raise RuntimeError("Unexpected QuantaAlpha public tag discovered")
    if json.loads((discovery_root / "releases.json").read_text(encoding="utf-8")) != []:
        raise RuntimeError("Unexpected QuantaAlpha public release discovered")
    for branch, expected in PUBLIC_BRANCH_HEADS.items():
        observed = str(run_git(source_root, "rev-parse", f"origin/{branch}")).strip()
        if observed != expected:
            raise RuntimeError(f"Local public branch pin changed: {branch}")

    commits = str(run_git(source_root, "rev-list", "--reverse", "--all")).splitlines()
    if len(commits) != PUBLIC_HISTORY_COMMIT_COUNT or _sha256_lines(commits) != PUBLIC_HISTORY_COMMIT_SHA256:
        raise RuntimeError("QuantaAlpha reachable commit history changed")
    paths = _historical_paths(source_root)
    if len(paths) != PUBLIC_HISTORY_PATH_COUNT or _sha256_lines(paths) != PUBLIC_HISTORY_PATH_SHA256:
        raise RuntimeError("QuantaAlpha reachable path history changed")

    fsck = subprocess.run(
        ["git", "-C", str(source_root), "fsck", "--full", "--no-reflogs", "--unreachable"],
        check=True,
        capture_output=True,
        text=True,
    )
    if fsck.stdout.strip():
        raise RuntimeError(f"Unreachable QuantaAlpha objects require review: {fsck.stdout}")

    object_lines = str(run_git(source_root, "rev-list", "--objects", "--all")).splitlines()
    object_ids = [line.split(" ", 1)[0] for line in object_lines]
    types = subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
        input="\n".join(object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    object_counts = dict(Counter(types))
    if object_counts != PUBLIC_HISTORY_OBJECT_COUNTS:
        raise RuntimeError(f"QuantaAlpha reachable object census changed: {object_counts}")

    branch_commit_sets = {
        branch: set(str(run_git(source_root, "rev-list", commit)).splitlines())
        for branch, commit in PUBLIC_BRANCH_HEADS.items()
    }
    tree_paths: dict[str, set[str]] = {}
    commit_rows = []
    for commit in commits:
        commit_paths = set(
            str(
                run_git(
                    source_root,
                    "-c",
                    "core.quotePath=false",
                    "ls-tree",
                    "-r",
                    "--name-only",
                    commit,
                )
            ).splitlines()
        )
        tree_paths[commit] = commit_paths
        meta = str(run_git(source_root, "show", "-s", "--format=%cI%x00%s", commit)).rstrip("\n").split("\0", 1)
        memberships = sorted(branch for branch, members in branch_commit_sets.items() if commit in members)
        native_result_paths = sorted(path for path in commit_paths if path.lower().endswith(NATIVE_RESULT_SUFFIXES))
        commit_rows.append(
            {
                "commit": commit,
                "commit_date": meta[0],
                "subject": meta[1],
                "public_branch_membership": ";".join(memberships),
                "tree_path_count": len(commit_paths),
                "python_path_count": sum(path.lower().endswith(".py") for path in commit_paths),
                "image_path_count": sum(
                    path.lower().endswith((".png", ".jpg", ".jpeg", ".gif")) for path in commit_paths
                ),
                "native_result_artifact_path_count": len(native_result_paths),
                "native_result_artifact_paths": ";".join(native_result_paths),
                "paper_result_credit": False,
            }
        )

    present_counts = Counter(path for commit_paths in tree_paths.values() for path in commit_paths)
    branch_path_sets = {branch: tree_paths[commit] for branch, commit in PUBLIC_BRANCH_HEADS.items()}
    path_rows = []
    for path in paths:
        role = _history_path_role(path)
        path_rows.append(
            {
                "relative_path": path,
                "suffix": Path(path).suffix.lower(),
                "history_role": role,
                "commits_present": present_counts[path],
                "public_branch_heads_present": ";".join(
                    branch for branch, members in branch_path_sets.items() if path in members
                ),
                "native_result_artifact_candidate": role == "native_result_artifact_candidate",
                "author_rendered_output": role == "author_rendered_result_output",
                "paper_result_credit": False,
            }
        )

    raw_candidates = [row for row in path_rows if row["native_result_artifact_candidate"]]
    if raw_candidates:
        raise RuntimeError(f"Historical native result candidates require review: {raw_candidates}")
    summary = {
        "repository_shallow": False,
        "public_branch_heads": PUBLIC_BRANCH_HEADS,
        "public_branches_total": len(PUBLIC_BRANCH_HEADS),
        "public_tags_total": 0,
        "public_releases_total": 0,
        "reachable_commits_total": len(commits),
        "reachable_commit_sequence_sha256": _sha256_lines(commits),
        "unique_historical_paths_total": len(paths),
        "historical_path_list_sha256": _sha256_lines(paths),
        "reachable_object_counts": object_counts,
        "unreachable_objects_total": 0,
        "native_result_artifact_paths_total": 0,
        "historical_json_paths_total": sum(path.lower().endswith(".json") for path in paths),
        "historical_image_blobs_total": len(
            {
                line.split(" ", 1)[0]
                for line in object_lines
                if " " in line and line.rsplit(" ", 1)[-1].lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
            }
        ),
        "paper_result_credit": False,
    }
    if summary["historical_json_paths_total"] != 8 or summary["historical_image_blobs_total"] != 13:
        raise RuntimeError(f"QuantaAlpha historical structured-asset census changed: {summary}")
    return commit_rows, path_rows, summary


def prepublication_public_history(
    census_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Audit the author-attributed QuantaAlpha lineage hidden from current heads.

    The range deliberately starts at the first QuantaAlpha-specific author
    commit, excluding 500+ inherited RD-Agent ancestor commits.  This corrects
    the earlier mistake of treating the five current official branch heads as
    the complete public source boundary.
    """
    if str(run_git(census_root, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise RuntimeError("QuantaAlpha public-ref census is shallow")
    range_spec = f"{PREPUBLICATION_START_COMMIT}^..{PREPUBLICATION_RELEASE_COMMIT}"
    commits = str(run_git(census_root, "rev-list", "--reverse", "--first-parent", range_spec)).splitlines()
    if len(commits) != PREPUBLICATION_COMMIT_COUNT or _sha256_lines(commits) != PREPUBLICATION_COMMIT_SHA256:
        raise RuntimeError("QuantaAlpha pre-publication commit lineage changed")
    paths: set[str] = set()
    rows = []
    for commit in commits:
        commit_paths = str(
            run_git(census_root, "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", commit)
        ).splitlines()
        paths.update(commit_paths)
        meta = str(
            run_git(census_root, "show", "-s", "--format=%cI%x00%an%x00%ae%x00%s", commit)
        ).rstrip("\n").split("\0", 3)
        result_paths = [path for path in commit_paths if path.lower().endswith(NATIVE_RESULT_SUFFIXES)]
        aggregate_json = [
            path
            for path in commit_paths
            if path.lower().endswith(".json")
            and any(token in path.lower() for token in ("backtest_v2_results/", "factor_library/", "batch_summary"))
        ]
        rows.append(
            {
                "commit": commit,
                "commit_date": meta[0],
                "author_name": meta[1],
                "author_email": meta[2],
                "subject": meta[3],
                "tree_path_count": len(commit_paths),
                "native_result_suffix_path_count": len(result_paths),
                "aggregate_result_or_factor_json_path_count": len(aggregate_json),
                "before_v1_submission": meta[0] < PAPER_VERSIONS["v1"]["date"],
                "evidence_role": "author_attributed_public_prepublication_lineage",
                "independent_regeneration": False,
            }
        )
    ordered_paths = sorted(paths, key=lambda item: item.encode("utf-8"))
    if len(ordered_paths) != PREPUBLICATION_PATH_COUNT or _sha256_lines(ordered_paths) != PREPUBLICATION_PATH_SHA256:
        raise RuntimeError("QuantaAlpha pre-publication path surface changed")
    summary = {
        "start_commit": PREPUBLICATION_START_COMMIT,
        "start_date": PREPUBLICATION_START_DATE,
        "results_commit": PREPUBLICATION_RESULTS_COMMIT,
        "results_date": PREPUBLICATION_RESULTS_DATE,
        "public_release_commit": PREPUBLICATION_RELEASE_COMMIT,
        "public_release_date": PREPUBLICATION_RELEASE_DATE,
        "public_release_lead_hours_before_v1": PREPUBLICATION_RELEASE_LEAD_HOURS,
        "quantaalpha_specific_first_parent_commits": len(commits),
        "commit_sequence_sha256": _sha256_lines(commits),
        "unique_historical_paths": len(ordered_paths),
        "historical_path_list_sha256": _sha256_lines(ordered_paths),
        "current_official_ref_surface_is_complete_public_history": False,
        "inherited_rdagent_ancestors_counted_as_quantaalpha_history": False,
    }
    return rows, summary


def public_fork_census(
    census_root: Path, branch_ref_snapshot: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fail closed over every unique head in the dated accessible-fork census.

    GitHub exposed 267 fork repositories and 357 branch refs on the census
    date.  Many refs shared the same object, so the local evidence store keeps
    one representative ref for each of the 77 unique heads.  No result credit
    is granted merely because a commit is author-attributed or a path looks
    result-like.
    """
    if str(run_git(census_root, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise RuntimeError("QuantaAlpha public-fork census is shallow")
    ref_lines = str(
        run_git(
            census_root,
            "for-each-ref",
            "refs/fork-census",
            "--format=%(refname)%09%(objectname)",
        )
    ).splitlines()
    if (
        len(ref_lines) != PUBLIC_FORK_REPRESENTATIVE_REF_COUNT
        or _sha256_lines(ref_lines) != PUBLIC_FORK_REPRESENTATIVE_REF_SHA256
    ):
        raise RuntimeError("QuantaAlpha representative public-fork ref census changed")
    refs = [line.split("\t", 1) for line in ref_lines]
    unique_heads = sorted({head for _, head in refs})
    if (
        len(unique_heads) != PUBLIC_FORK_REPRESENTATIVE_REF_COUNT
        or _sha256_lines(unique_heads) != PUBLIC_FORK_UNIQUE_HEAD_SHA256
    ):
        raise RuntimeError("QuantaAlpha public-fork unique-head census changed")

    with branch_ref_snapshot.open(newline="", encoding="utf-8") as handle:
        branch_rows = list(csv.DictReader(handle))
    expected_columns = {
        "repository",
        "branch",
        "head_commit",
        "repository_created_at",
        "repository_pushed_at",
        "head_committed_at",
        "head_author_login",
        "head_author_name",
        "head_author_email",
        "head_subject",
    }
    if not branch_rows or set(branch_rows[0]) != expected_columns:
        raise RuntimeError("QuantaAlpha public-fork branch-ref snapshot schema changed")
    branch_rows.sort(
        key=lambda row: (row["repository"].lower(), row["branch"].lower(), row["head_commit"])
    )
    canonical_branch_refs = [
        f'{row["repository"]}\t{row["branch"]}\t{row["head_commit"]}' for row in branch_rows
    ]
    if (
        len(branch_rows) != PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT
        or len({row["repository"] for row in branch_rows}) != PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT
        or len({(row["repository"], row["branch"]) for row in branch_rows}) != len(branch_rows)
        or _sha256_lines(canonical_branch_refs) != PUBLIC_FORK_GRAPHQL_REF_SHA256
        or {row["head_commit"] for row in branch_rows} != set(unique_heads)
    ):
        raise RuntimeError("QuantaAlpha complete public-fork branch-ref snapshot changed")

    base_heads = [*PUBLIC_BRANCH_HEADS.values(), PREPUBLICATION_RELEASE_COMMIT]
    author_heads = set(AUTHOR_POST_V1_FORK_HEADS)
    if not author_heads <= set(unique_heads) or UNAFFILIATED_SUMMARY_HEAD not in unique_heads:
        raise RuntimeError("Pinned QuantaAlpha fork evidence heads are absent")
    rows = []
    extra_commits_by_head: dict[str, list[str]] = {}
    changed_paths_by_head: dict[str, list[str]] = {}
    for ref, head in refs:
        extra_commits = sorted(str(run_git(census_root, "rev-list", head, "--not", *base_heads)).splitlines())
        changed_paths: set[str] = set()
        for commit in extra_commits:
            changed_paths.update(
                path
                for path in str(
                    run_git(
                        census_root,
                        "diff-tree",
                        "--root",
                        "--no-commit-id",
                        "--name-only",
                        "-r",
                        commit,
                    )
                ).splitlines()
                if path
            )
        ordered_paths = sorted(changed_paths)
        extra_commits_by_head[head] = extra_commits
        changed_paths_by_head[head] = ordered_paths
        native_result_paths = [path for path in ordered_paths if path.lower().endswith(NATIVE_RESULT_SUFFIXES)]
        result_like_json_paths = [
            path
            for path in ordered_paths
            if path.lower().endswith(".json") and any(token in path.lower() for token in ("result", "report"))
        ]
        meta = str(run_git(census_root, "show", "-s", "--format=%cI%x00%an%x00%ae%x00%s", head))
        head_date, author_name, author_email, subject = meta.rstrip("\n").split("\0", 3)
        if not extra_commits:
            classification = "official_or_prepublication_history_reachable"
        elif head in author_heads:
            classification = "author_attributed_post_v1_source_config_or_documentation_only"
        elif head == UNAFFILIATED_SUMMARY_HEAD:
            classification = "unaffiliated_post_v1_derived_summary_without_raw_lineage"
        else:
            classification = "unaffiliated_post_v1_code_config_or_data_extension"
        rows.append(
            {
                "representative_ref": ref,
                "head_commit": head,
                "head_date": head_date,
                "head_author_name": author_name,
                "head_author_email": author_email,
                "head_subject": subject,
                "extra_commit_count_beyond_official_and_prepublication_bases": len(extra_commits),
                "extra_changed_path_count": len(ordered_paths),
                "native_result_suffix_path_count": len(native_result_paths),
                "native_result_suffix_paths": ";".join(native_result_paths),
                "result_like_json_path_count": len(result_like_json_paths),
                "result_like_json_paths": ";".join(result_like_json_paths),
                "author_attributed_post_v1_lineage": head in author_heads,
                "classification": classification,
                "paper_result_credit": False,
            }
        )

    base_reachable = [row for row in rows if not row["extra_commit_count_beyond_official_and_prepublication_bases"]]
    if len(base_reachable) != PUBLIC_FORK_BASE_REACHABLE_HEAD_COUNT:
        raise RuntimeError("QuantaAlpha base-reachable fork-head count changed")
    if len(rows) - len(base_reachable) != PUBLIC_FORK_DIVERGENT_HEAD_COUNT:
        raise RuntimeError("QuantaAlpha divergent public-fork head count changed")

    author_commits = sorted({commit for head in author_heads for commit in extra_commits_by_head[head]})
    author_paths = sorted({path for head in author_heads for path in changed_paths_by_head[head]})
    if (
        len(author_commits) != AUTHOR_POST_V1_EXTRA_COMMIT_COUNT
        or _sha256_lines(author_commits) != AUTHOR_POST_V1_EXTRA_COMMIT_SHA256
    ):
        raise RuntimeError("QuantaAlpha post-v1 author commit surface changed")
    if (
        len(author_paths) != AUTHOR_POST_V1_CHANGED_PATH_COUNT
        or _sha256_lines(author_paths) != AUTHOR_POST_V1_CHANGED_PATH_SHA256
    ):
        raise RuntimeError("QuantaAlpha post-v1 author path surface changed")
    author_emails = {
        str(run_git(census_root, "show", "-s", "--format=%ae", commit)).strip()
        for commit in author_commits
    }
    nonbot_author_emails = {email for email in author_emails if "[bot]" not in email}
    if nonbot_author_emails != AUTHOR_POST_V1_EMAILS:
        raise RuntimeError(f"QuantaAlpha post-v1 author identity surface changed: {nonbot_author_emails}")
    author_native_result_paths = [path for path in author_paths if path.lower().endswith(NATIVE_RESULT_SUFFIXES)]
    if author_native_result_paths:
        raise RuntimeError(f"Author-attributed post-v1 native result paths require review: {author_native_result_paths}")

    base_objects = {
        line.split(" ", 1)[0]
        for line in str(run_git(census_root, "rev-list", "--objects", *base_heads)).splitlines()
    }
    author_image_refs: dict[tuple[str, str], str] = {}
    for head in author_heads:
        for line in str(run_git(census_root, "ls-tree", "-r", head)).splitlines():
            metadata, path = line.split("\t", 1)
            blob = metadata.split()[2]
            if path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".pdf")):
                author_image_refs[(head, path)] = blob
    author_image_blobs = set(author_image_refs.values())
    new_author_image_blobs = author_image_blobs - base_objects
    if (
        len(author_image_refs) != 81
        or len(author_image_blobs) != 9
        or new_author_image_blobs != {AUTHOR_POST_V1_NEW_DOC_IMAGE_BLOB}
    ):
        raise RuntimeError("QuantaAlpha post-v1 author image surface changed")
    new_image = run_git(census_root, "cat-file", "blob", AUTHOR_POST_V1_NEW_DOC_IMAGE_BLOB, binary=True)
    if (
        len(new_image) != AUTHOR_POST_V1_NEW_DOC_IMAGE_BYTES
        or hashlib.sha256(new_image).hexdigest() != AUTHOR_POST_V1_NEW_DOC_IMAGE_SHA256
    ):
        raise RuntimeError("QuantaAlpha post-v1 author documentation image changed")
    new_image_paths = sorted(
        {path for (_, path), blob in author_image_refs.items() if blob == AUTHOR_POST_V1_NEW_DOC_IMAGE_BLOB}
    )
    if new_image_paths != ["docs/images/WeChat.jpg"]:
        raise RuntimeError(f"Unexpected QuantaAlpha post-v1 author image paths: {new_image_paths}")

    unaffiliated_summary = run_git(
        census_root,
        "show",
        f"{UNAFFILIATED_SUMMARY_HEAD}:{UNAFFILIATED_SUMMARY_PATH}",
        binary=True,
    )
    if (
        len(unaffiliated_summary) != UNAFFILIATED_SUMMARY_BYTES
        or hashlib.sha256(unaffiliated_summary).hexdigest() != UNAFFILIATED_SUMMARY_SHA256
    ):
        raise RuntimeError("QuantaAlpha unaffiliated fork summary changed")
    summary_payload = json.loads(unaffiliated_summary)
    if (
        summary_payload.get("report_date") != "2026-02-16"
        or summary_payload.get("test_summary", {}).get("total_strategies") != 5
        or summary_payload.get("test_summary", {}).get("data_source") != "CSI300"
    ):
        raise RuntimeError("QuantaAlpha unaffiliated fork summary schema changed")

    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": PUBLIC_FORK_REST_COUNT,
        "graphql_accessible_forks": PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT,
        "rest_minus_accessible_fork_gap": PUBLIC_FORK_REST_COUNT - PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT,
        "accessibility_gap_interpretation": "deleted_private_or_otherwise_unavailable_not_inspected",
        "graphql_accessible_branch_refs": PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT,
        "graphql_accessible_branch_ref_census_sha256": PUBLIC_FORK_GRAPHQL_REF_SHA256,
        "graphql_accessible_branch_ref_snapshot_file_sha256": sha256(branch_ref_snapshot),
        "representative_unique_head_refs": len(rows),
        "representative_ref_census_sha256": _sha256_lines(ref_lines),
        "unique_heads": len(unique_heads),
        "unique_head_sha256": _sha256_lines(unique_heads),
        "heads_reachable_from_official_or_prepublication_bases": len(base_reachable),
        "divergent_heads_reviewed": len(rows) - len(base_reachable),
        "author_attributed_post_v1_heads": len(author_heads),
        "author_attributed_post_v1_extra_commits": len(author_commits),
        "author_attributed_post_v1_changed_paths": len(author_paths),
        "author_attributed_post_v1_native_result_paths": len(author_native_result_paths),
        "author_attributed_post_v1_image_refs": len(author_image_refs),
        "author_attributed_post_v1_unique_image_blobs": len(author_image_blobs),
        "author_attributed_post_v1_new_image_blobs": len(new_author_image_blobs),
        "author_attributed_post_v1_new_image_path": new_image_paths[0],
        "unaffiliated_post_v1_derived_summary_path": UNAFFILIATED_SUMMARY_PATH,
        "unaffiliated_post_v1_derived_summary_sha256": UNAFFILIATED_SUMMARY_SHA256,
        "unaffiliated_summary_matches_paper_method_or_result_lineage": False,
        "paper_result_artifacts_discovered_in_post_v1_fork_heads": 0,
        "paper_result_credit": False,
    }
    return rows, summary


def _aggregate_metric_values(metrics: Mapping[str, Any]) -> dict[str, float]:
    return {
        "IC": float(metrics["IC"]),
        "ICIR": float(metrics["ICIR"]),
        "Rank_IC": float(metrics["Rank IC"]),
        "Rank_ICIR": float(metrics["Rank ICIR"]),
        "IR": float(metrics["information_ratio"]),
        "CR": float(metrics["calmar_ratio"]),
        "ARR_pct": 100.0 * float(metrics["annualized_return"]),
        "MDD_pct": 100.0 * abs(float(metrics["max_drawdown"])),
    }


def prepublication_result_conformance(census_root: Path, paper_source_root: Path) -> list[dict[str, Any]]:
    """Compare pinned native aggregate JSONs with every cell in 11 v1/v2 rows."""
    paper_rows = _parse_v1_v2_main_table(paper_source_root.parent / "source_v1/tables/main_table.tex")
    paper = {(method, metric): value for method, metric, value in paper_rows}
    rows = []
    for method, (commit, path, filename_alignment) in PREPUBLICATION_RESULT_ARTIFACTS.items():
        blob = run_git(census_root, "show", f"{commit}:{path}", binary=True)
        payload = json.loads(blob)
        metrics = _aggregate_metric_values(payload["metrics"])
        for metric in ("IC", "ICIR", "Rank_IC", "Rank_ICIR", "IR", "CR", "ARR_pct", "MDD_pct"):
            paper_text = paper[(method, metric)]
            decimals = 2 if metric in {"ARR_pct", "MDD_pct"} else 4
            source_value = metrics[metric]
            rounded_match = f"{source_value:.{decimals}f}" == f"{float(paper_text):.{decimals}f}"
            rows.append(
                {
                    "paper_versions": "v1;v2",
                    "method": method,
                    "metric": metric,
                    "paper_value": paper_text,
                    "source_value": source_value,
                    "display_decimals": decimals,
                    "rounded_match": rounded_match,
                    "source_commit": commit,
                    "source_path": path,
                    "source_blob_sha256": hashlib.sha256(blob).hexdigest(),
                    "source_num_factors": payload.get("num_factors", ""),
                    "filename_method_alignment": filename_alignment,
                    "evidence_role": (
                        "native_aggregate_author_output_correspondence"
                        if rounded_match
                        else "nearby_native_aggregate_author_output"
                    ),
                    "independently_regenerated": False,
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 88 or sum(row["rounded_match"] for row in rows) != 74:
        raise RuntimeError("QuantaAlpha pre-publication aggregate-result correspondence changed")
    return rows


def recovered_data_provenance() -> list[dict[str, Any]]:
    return [
        {
            "artifact": "official_author_daily_pv_h5",
            "public_ref": f"{PREPUBLICATION_RESULTS_COMMIT}:git_ignore_folder/factor_implementation_source_data/daily_pv.h5",
            "bytes": AUTHOR_DAILY_PV_LFS_BYTES,
            "sha256": AUTHOR_DAILY_PV_LFS_SHA256,
            "provenance": "official_repository_git_lfs",
            "validation": "downloaded; SHA-256 verified; HDF data shape 11024067x6; calendar ends 2026-01-09",
            "paper_result_artifact": False,
        },
        {
            "artifact": "fork_preserved_qlib_provider_archive",
            "public_ref": "davide97l/QuantaAlpha@c3c55488:hf_data/cn_data.zip",
            "bytes": FORK_QLIB_ARCHIVE_BYTES,
            "sha256": FORK_QLIB_ARCHIVE_SHA256,
            "provenance": "public_fork_git_lfs_not_official_author_credit",
            "validation": "downloaded; SHA-256 verified; 60168 provider files; internal timestamps 2026-02-05",
            "paper_result_artifact": False,
        },
        {
            "artifact": "official_hdf_to_fork_provider_value_fingerprint",
            "public_ref": "SH600000 2015-01-05..2026-01-09; open/close/high/low/volume/factor",
            "bytes": "",
            "sha256": RECOVERED_PROVIDER_MATRIX_SHA256,
            "provenance": "cross_artifact_value_identity",
            "validation": "2679x6 values bit-identical; identical NaN mask; max absolute difference 0",
            "paper_result_artifact": False,
        },
    ]


def native_rerun_conformance() -> list[dict[str, Any]]:
    paper_alpha = {
        "IC": 0.0051,
        "ICIR": 0.0329,
        "Rank_IC": 0.0184,
        "Rank_ICIR": 0.1177,
        "IR": 0.5044,
        "CR": 0.2087,
        "ARR_pct": 4.63,
        "MDD_pct": 22.19,
    }
    paper_qa_gpt = {
        "IC": 0.1501,
        "ICIR": 0.9110,
        "Rank_IC": 0.1465,
        "Rank_ICIR": 0.8909,
        "IR": 3.3251,
        "CR": 3.4774,
        "ARR_pct": 27.75,
        "MDD_pct": 7.98,
    }
    definitions = (
        (
            "Alpha158(20)",
            "v1;v2;v3",
            20,
            20,
            paper_alpha,
            ALPHA158_20_NATIVE_METRICS,
            True,
            "independently_regenerated_matches_paper_rounding",
        ),
        (
            "QuantaAlpha / GPT-5.2 v1-v2 configuration",
            "v1;v2",
            170,
            168,
            paper_qa_gpt,
            QA_GPT_COMBINED_168_NATIVE_METRICS,
            False,
            "not_reproduced_two_public_expressions_fail_and_remaining_result_materially_differs",
        ),
    )
    rows = []
    for method, versions, expected_factors, executed_factors, paper_values, observed, reproduced, status in definitions:
        for metric, paper_value in paper_values.items():
            rows.append(
                {
                    "paper_versions": versions,
                    "method": method,
                    "metric": metric,
                    "paper_value": paper_value,
                    "native_rerun_value": observed[metric],
                    "absolute_difference": abs(observed[metric] - paper_value),
                    "expected_factor_count": expected_factors,
                    "executed_factor_count": executed_factors,
                    "independently_regenerated": reproduced,
                    "status": status,
                    "source_commit": PREPUBLICATION_RESULTS_COMMIT,
                    "data_fingerprint_sha256": RECOVERED_PROVIDER_MATRIX_SHA256,
                }
            )
    if len(rows) != 16 or sum(row["independently_regenerated"] for row in rows) != 8:
        raise RuntimeError("QuantaAlpha native-rerun evidence changed")
    return rows


def native_result_regeneration_payload() -> dict[str, Any]:
    return {
        "runtime": RERUN_ENVIRONMENT,
        "runtime_provenance": {
            "python_and_pyqlib": "directly evidenced by preserved 2026-01-20 author logs",
            "remaining_versions": "latest stable releases available before the author run; inferred, not directly proven",
        },
        "source_commit": PREPUBLICATION_RESULTS_COMMIT,
        "data": {
            "official_daily_pv_lfs_sha256": AUTHOR_DAILY_PV_LFS_SHA256,
            "fork_qlib_archive_sha256": FORK_QLIB_ARCHIVE_SHA256,
            "cross_artifact_matrix_sha256": RECOVERED_PROVIDER_MATRIX_SHA256,
        },
        "alpha158_20": {
            "factor_count": 20,
            "native_metrics": ALPHA158_20_NATIVE_METRICS,
            "ic_only_result_json_sha256": "97ba667b1cbc60fd134a07cf34b214ae90d67af300a558d0531e7657cc2a2848",
            "ic_only_log_sha256": "882002d5da9ad673adf07d6dbd81437c2eb47a7931bdce80b748c400b36f6887",
            "full_result_json_sha256": "e9a5a389201c6a5a849cf0f41fa7206ce447dc163228cc9a4404bcfb5bee5b7b",
            "full_log_sha256": "9b950ec89b0aede2c048ab0cbeba72c3a62696c7b335a57ec3faf46f0fe6f7bf",
            "paper_cells_independently_regenerated": 8,
            "status": "full_native_training_prediction_and_portfolio_path_matches_paper_rounding",
        },
        "quantaalpha_gpt_v1_v2": {
            "paper_factor_count": 170,
            "publicly_recomputed_factor_count": 168,
            "failed_public_expressions": ["ResidualMom_AbsorpGate_20D", "ResidualMom_VolumeConfirm_20D"],
            "native_metrics": QA_GPT_COMBINED_168_NATIVE_METRICS,
            "full_result_json_sha256": "90c7204b684d7d1f059f79551321b6bbd082b34948a91916f9d138c2235a14ff",
            "full_log_sha256": "3d6a68993d883c79548f7e945f366e13c720af76eb4600f96cb2ab42c2031559",
            "paper_cells_independently_regenerated": 0,
            "status": "mechanically_executed_but_not_result_reproduced",
        },
        "llm_or_market_api_called_during_rerun": False,
    }


def historical_branch_evidence(source_root: Path) -> list[dict[str, Any]]:
    windows = PUBLIC_BRANCH_HEADS["windows"]
    original = json.loads(str(run_git(source_root, "show", f"{windows}:experiment/original_direction.json")))
    portfolios = original.get("factor_portfolios", [])
    descriptions = [item.get("description", "") for item in portfolios]
    expression_count = sum(description.count("expression:") for description in descriptions)
    if len(portfolios) != 10 or expression_count != 30:
        raise RuntimeError("Historical QuantaAlpha direction-seed inventory changed")
    notes = str(run_git(source_root, "show", f"{windows}:experiment/README_EXPERIMENT.md"))
    required_notes = (
        "Plan parallelism**: 10 directions",
        "5 epochs, 11 rounds in total",
        "usually 3",
        "2022-01-01 to 2025-12-26",
        "no fallback logic",
    )
    if not all(token in notes for token in required_notes):
        raise RuntimeError("Historical QuantaAlpha experiment note changed")
    frontend_paths = str(
        run_git(
            source_root,
            "-c",
            "core.quotePath=false",
            "ls-tree",
            "-r",
            "--name-only",
            windows,
            "--",
            "frontend-v2",
        )
    ).splitlines()
    if len(frontend_paths) != 44:
        raise RuntimeError("Historical QuantaAlpha frontend inventory changed")

    baseline = str(
        run_git(
            source_root,
            "show",
            f"{windows}:quantaalpha/factors/factor_template/conf_baseline.yaml",
        )
    )
    required_baseline_tokens = (
        "train: [2016-01-01, 2019-12-31]",
        "valid: [2020-01-01, 2020-12-31]",
        "test: [2021-01-01, 2025-12-26]",
        "seed: 42",
        "random_state: 42",
        "start_time: 2021-01-01",
        "end_time: 2021-12-31",
    )
    if not all(token in baseline for token in required_baseline_tokens):
        raise RuntimeError("Historical Windows branch Qlib profile changed")

    for path, expected in HISTORICAL_MAIN_TABLE_RASTERS.items():
        blob = run_git(source_root, "show", f"{INITIAL_COMMIT}:{path}", binary=True)
        if hashlib.sha256(blob).hexdigest() != expected:
            raise RuntimeError(f"Historical QuantaAlpha result raster changed: {path}")

    json_paths = [path for path in _historical_paths(source_root) if path.lower().endswith(".json")]
    expected_json_paths = {
        "experiment/original_direction.json",
        "experiment/original_direction_CN.json",
        "frontend-v2/package-lock.json",
        "frontend-v2/package.json",
        "frontend-v2/tsconfig.json",
        "frontend-v2/tsconfig.node.json",
        "quantaalpha/components/benchmark/example.json",
        "quantaalpha/contrib/model/coder/benchmark/model_dict.json",
    }
    if set(json_paths) != expected_json_paths:
        raise RuntimeError(f"Historical QuantaAlpha JSON surface changed: {json_paths}")

    return [
        {
            "evidence": "paper_direction_seed_groups",
            "public_ref": f"windows@{windows}",
            "paths": "experiment/original_direction.json;experiment/original_direction_CN.json",
            "observed_units": 10,
            "detail": "10 seed groups containing 30 named Alpha158(20)-derived factor expressions",
            "evidence_role": "paper_configuration_specification",
            "underlying_run_artifact": False,
            "paper_result_credit": False,
        },
        {
            "evidence": "paper_experiment_notes",
            "public_ref": f"windows@{windows}",
            "paths": "experiment/README_EXPERIMENT.md;experiment/README_EXPERIMENT_CN.md",
            "observed_units": 2,
            "detail": "documents 10 directions, 5 epochs/11 rounds, 3 factors, mining-vs-final IC periods, and no embedding fallback",
            "evidence_role": "paper_configuration_specification",
            "underlying_run_artifact": False,
            "paper_result_credit": False,
        },
        {
            "evidence": "windows_qlib_profile",
            "public_ref": f"windows@{windows}",
            "paths": "quantaalpha/factors/factor_template/conf_baseline.yaml;quantaalpha/factors/factor_template/conf_combined_factors.yaml",
            "observed_units": 2,
            "detail": "adds seed/random_state 42 and extends test through 2025, but train/valid remain 2016-2019/2020 and port_analysis backtest remains 2021",
            "evidence_role": "partial_configuration_not_paper_profile",
            "underlying_run_artifact": False,
            "paper_result_credit": False,
        },
        {
            "evidence": "operational_frontend_and_backend_bridge",
            "public_ref": f"windows@{windows}",
            "paths": "frontend-v2/",
            "observed_units": len(frontend_paths),
            "detail": "44-file UI/backend launches native CLI and reads external live factor/backtest JSON; it embeds no paper result arrays",
            "evidence_role": "historical_operational_source",
            "underlying_run_artifact": False,
            "paper_result_credit": False,
        },
        {
            "evidence": "v1_v2_main_table_raster",
            "public_ref": f"initial@{INITIAL_COMMIT}",
            "paths": "docs/images/主实验.png",
            "observed_units": 224,
            "detail": "high-resolution raster completely visually corresponds to the identical 224-cell v1/v2 main tables; no numeric array or derivation",
            "evidence_role": "author_rendered_result_output",
            "underlying_run_artifact": False,
            "paper_result_credit": False,
        },
        {
            "evidence": "v1_v2_duplicate_main_table_raster",
            "public_ref": f"initial@{INITIAL_COMMIT}",
            "paths": "images/主实验.png",
            "observed_units": 0,
            "detail": "lower-resolution duplicate of the same v1/v2 table; counted as zero additional result units",
            "evidence_role": "duplicate_author_rendered_result_output",
            "underlying_run_artifact": False,
            "paper_result_credit": False,
        },
        {
            "evidence": "reachable_json_surface",
            "public_ref": "all_public_branches",
            "paths": ";".join(json_paths),
            "observed_units": len(json_paths),
            "detail": "all JSON files are seed/configuration, frontend descriptors, or benchmark examples; none is a paper run result",
            "evidence_role": "complete_structured_file_boundary",
            "underlying_run_artifact": False,
            "paper_result_credit": False,
        },
        {
            "evidence": "native_result_file_types",
            "public_ref": "all_61_reachable_commits",
            "paths": "",
            "observed_units": 0,
            "detail": "no CSV, Parquet, pickle, HDF, NumPy, checkpoint, log, or JSONL path occurs anywhere in public history",
            "evidence_role": "complete_negative_result_artifact_boundary",
            "underlying_run_artifact": False,
            "paper_result_credit": False,
        },
    ]


def _parse_v1_v2_main_table(path: Path) -> list[tuple[str, str, str]]:
    if sha256(path) != V1_V2_MAIN_TABLE_SHA256:
        raise RuntimeError(f"Pinned QuantaAlpha early main table changed: {path}")
    text = "\n".join(line.split("%", 1)[0] for line in path.read_text(encoding="utf-8").splitlines())
    metrics = ("IC", "ICIR", "Rank_IC", "Rank_ICIR", "IR", "CR", "ARR_pct", "MDD_pct")
    parsed: list[tuple[str, str, str]] = []
    row_index = 0
    for chunk in text.split(r"\\"):
        columns = chunk.split("&")
        if len(columns) != 10:
            continue
        values = []
        for column in columns[-8:]:
            tokens = re.findall(r"(?<![A-Za-z0-9])[-+]?\d+(?:\.\d+)?", column)
            if not tokens:
                values = []
                break
            values.append(tokens[-1])
        if len(values) != 8:
            continue
        row_index += 1
        method_tex = re.sub(r"\s+", " ", columns[1]).strip()
        method = f"row_{row_index:02d}:{method_tex}"
        parsed.extend((method, metric, value) for metric, value in zip(metrics, values))
    if row_index != 28 or len(parsed) != 224:
        raise RuntimeError(f"QuantaAlpha early main-table census changed: {row_index}/{len(parsed)}")
    return parsed


def paper_version_main_table_rows(source_root: Path, paper_source_root: Path) -> list[dict[str, Any]]:
    early_roots = {
        "v1": paper_source_root.parent / "source_v1",
        "v2": paper_source_root.parent / "source_v2",
    }
    early_tables = {
        version: _parse_v1_v2_main_table(root / "tables/main_table.tex") for version, root in early_roots.items()
    }
    if early_tables["v1"] != early_tables["v2"]:
        raise RuntimeError("QuantaAlpha v1/v2 main tables are no longer identical")
    high_res = run_git(
        source_root,
        "show",
        f"{INITIAL_COMMIT}:docs/images/主实验.png",
        binary=True,
    )
    if hashlib.sha256(high_res).hexdigest() != HISTORICAL_MAIN_TABLE_RASTERS["docs/images/主实验.png"]:
        raise RuntimeError("Historical QuantaAlpha early table raster changed")
    rows: list[dict[str, Any]] = []
    for version, cells in early_tables.items():
        for method, metric, value in cells:
            regenerated = method == "row_11:Alpha158(20)"
            native_value = ALPHA158_20_NATIVE_METRICS[metric] if regenerated else ""
            rows.append(
                {
                    "paper_version": version,
                    "paper_source_table_sha256": V1_V2_MAIN_TABLE_SHA256,
                    "method": method,
                    "metric": metric,
                    "paper_value": value,
                    "author_raster_path": "docs/images/主实验.png",
                    "author_raster_commit": INITIAL_COMMIT,
                    "author_raster_sha256": HISTORICAL_MAIN_TABLE_RASTERS["docs/images/主实验.png"],
                    "author_output_correspondence": True,
                    "native_reproduced_value": native_value,
                    "independently_regenerated": regenerated,
                    "paper_result_credit": regenerated,
                }
            )
    current_table_sha = sha256(paper_source_root / "tables/main_table.tex")
    for method, values in MAIN_RESULTS.items():
        for metric, value in zip(METRICS, values):
            regenerated = method == "Alpha158(20)"
            native_value = ALPHA158_20_NATIVE_METRICS[metric] if regenerated else ""
            rows.append(
                {
                    "paper_version": "v3",
                    "paper_source_table_sha256": current_table_sha,
                    "method": method,
                    "metric": metric,
                    "paper_value": value,
                    "author_raster_path": "docs/images/主实验.png",
                    "author_raster_commit": SOURCE_COMMIT,
                    "author_raster_sha256": RELEASED_PAPER_OUTPUT_SHA256["docs/images/主实验.png"],
                    "author_output_correspondence": True,
                    "native_reproduced_value": native_value,
                    "independently_regenerated": regenerated,
                    "paper_result_credit": regenerated,
                }
            )
    if len(rows) != 644 or Counter(row["paper_version"] for row in rows) != {
        "v1": 224,
        "v2": 224,
        "v3": 196,
    }:
        raise RuntimeError("QuantaAlpha versioned main-table census changed")
    return rows


def _result_row(table: str, item: str, metric: str, value: Any, role: str = "direct") -> dict[str, Any]:
    author_output = table == "Table 1 Main CSI300 results"
    regenerated = author_output and item == "Alpha158(20)"
    native_value = ALPHA158_20_NATIVE_METRICS[metric] if regenerated else ""
    return {
        "paper_table": table,
        "item": item,
        "metric": metric,
        "value_role": role,
        "paper_value": value,
        "native_reproduced_value": native_value,
        "absolute_difference": abs(native_value - value) if regenerated else "",
        "author_output_value": value if author_output else "",
        "author_output_correspondence": author_output,
        "independently_regenerated": regenerated,
        "status": (
            "independently_regenerated_matches_paper_rounding"
            if regenerated
            else "corroborated_by_exact_author_readme_table_raster_not_regenerated"
            if author_output
            else "not_reproduced_no_released_result_derivation"
        ),
        "paper_result_credit": regenerated,
    }


def paper_table_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method, values in MAIN_RESULTS.items():
        rows.extend(
            _result_row("Table 1 Main CSI300 results", method, metric, value) for metric, value in zip(METRICS, values)
        )
    for variant, (direct, deltas) in EVOLUTION_ABLATION.items():
        rows.extend(
            _result_row("Table 2 Evolution-component ablation", variant, metric, value)
            for metric, value in zip(EVOLUTION_METRICS, direct)
        )
        rows.extend(
            _result_row("Table 2 Evolution-component ablation", variant, metric, value, "displayed_delta")
            for metric, value in zip(EVOLUTION_METRICS, deltas)
        )
    for seed, values in SEED_RESULTS.items():
        rows.extend(
            _result_row("Appendix Table 2 Cross-seed core metrics", seed, metric, value)
            for metric, value in zip(SEED_METRICS, values)
        )
    for metric, values in SEED_VARIANCE.items():
        rows.extend(
            _result_row("Appendix Table 3 Cross-seed variance", metric, stat, value)
            for stat, value in zip(("mean", "std", "CV_pct", "range"), values)
        )
    for library_metric, values in DAILY_STATS.items():
        rows.extend(
            _result_row("Appendix Table 4 Daily IC statistics", library_metric, metric, value)
            for metric, value in zip(DAILY_METRICS, values)
        )
    for parent, values in PARENT_RESULTS.items():
        rows.extend(
            _result_row("Appendix C Parent trajectory metrics", parent, metric, value)
            for metric, value in zip(("Rank_IC", "IC", "IR"), values)
        )
    for metric, values in CASE_RESULTS.items():
        rows.extend(
            _result_row("Appendix C Backtest metrics", item, metric, value)
            for item, value in zip(("offspring", "baseline"), values)
        )
    rows.extend(
        _result_row("Appendix C Detailed statistics", "offspring", metric, value)
        for metric, value in DETAIL_RESULTS.items()
    )
    for factor, values in REPRESENTATIVE_FACTORS.items():
        rows.extend(
            _result_row("Appendix D Representative factors", factor, metric, value)
            for metric, value in zip(("Rank_IC", "IC"), values)
        )
    for metric, values in FACTOR_SUMMARY.items():
        rows.extend(
            _result_row("Appendix D Factor summary", library, metric, value)
            for library, value in zip(("QA", "AA"), values)
        )
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
            rows.append(
                {
                    "figure": "Figure 3 quality-gate ablation",
                    "item": variant,
                    "metric": metric,
                    "value_role": role,
                    "paper_value": value,
                    "native_reproduced_value": "",
                    "author_output_correspondence": False,
                    "status": "not_reproduced_raster_only",
                    "paper_result_credit": False,
                }
            )
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
        rows.append(
            {
                "figure": "Appendix E iterative case-study raster",
                "item": item,
                "metric": metric,
                "value_role": "label",
                "paper_value": value,
                "native_reproduced_value": "",
                "author_output_correspondence": True,
                "status": "corroborated_by_author_readme_case_study_raster_not_regenerated",
                "paper_result_credit": False,
            }
        )
    for item, value in (("Parent 1", 0.0216), ("Parent 2", 0.0246), ("Offspring", 0.0311)):
        rows.append(
            {
                "figure": "Appendix C evolution-path diagram",
                "item": item,
                "metric": "Rank_IC",
                "value_role": "label",
                "paper_value": value,
                "native_reproduced_value": "",
                "author_output_correspondence": False,
                "status": "not_reproduced_tex_label_only",
                "paper_result_credit": False,
            }
        )
    if len(rows) != 40:
        raise RuntimeError(f"QuantaAlpha figure-label census changed: {len(rows)}")
    return rows


def plot_point_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for panel, metric in (("Figure 4 IC", "IC"), ("Figure 4 Rank IC", "Rank_IC")):
        for method in ("QuantaAlpha", "AlphaAgent", "RD-Agent", "Alpha158"):
            for year in (2022, 2023, 2024, 2025):
                rows.append(
                    {
                        "figure_panel": panel,
                        "series": method,
                        "x_position": year,
                        "metric": metric,
                        "paper_value": "unlabeled_marker",
                        "native_reproduced_value": "",
                        "author_output_correspondence": True,
                        "status": "exact_author_and_paper_raster_correspondence_no_array",
                        "paper_result_credit": False,
                    }
                )
    for method in ("QuantaAlpha", "AlphaAgent", "RD-Agent"):
        for iteration in range(1, 6):
            rows.append(
                {
                    "figure_panel": "Figure 5 evolutionary alpha-mining efficiency",
                    "series": method,
                    "x_position": iteration,
                    "metric": "IC_distribution_central_marker",
                    "paper_value": "unlabeled_marker",
                    "native_reproduced_value": "",
                    "author_output_correspondence": True,
                    "status": "exact_author_and_paper_raster_correspondence_no_array_or_band_definition",
                    "paper_result_credit": False,
                }
            )
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
        (
            "result",
            "approximately 150 validated factors enter final LightGBM",
            "approximately 150",
            "not_reproduced_factor_pool_absent",
        ),
        (
            "configuration",
            "CSI300/500/S&P500 train split",
            "2016-01-01--2020-12-31",
            "standalone_backtest_config_matches",
        ),
        ("configuration", "validation split", "2021-01-01--2021-12-31", "standalone_backtest_config_matches"),
        (
            "configuration",
            "test split",
            "2022-01-01--2025-12-26",
            "standalone_backtest_config_matches_but_mining_config_conflicts",
        ),
        ("configuration", "next-day return label", "Ref(close,-2)/Ref(close,-1)-1", "matches_configs"),
        (
            "configuration",
            "basic features",
            "open/high/low/close/volume/vwap",
            "mining_config_uses_four_engineered_features_and_no_vwap",
        ),
        (
            "configuration",
            "planning directions",
            "10",
            "historical_windows_branch_discloses_10_seed_groups_but_current_main_uses_2",
        ),
        (
            "configuration",
            "factors per hypothesis",
            "3",
            "historical_experiment_note_says_usually_3_but_current_main_uses_1",
        ),
        (
            "configuration",
            "evolution iterations",
            "5 mutation+crossover cycles",
            "historical_experiment_note_says_5_epochs_11_rounds_but_current_main_uses_3_rounds",
        ),
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
        {
            "check": "v3 abstract headline versus Table 1",
            "status": "compatible",
            "evidence": "0.0472 IC, 4.68% ARR, 11.80% MDD",
        },
        {
            "check": "Table 1 QuantaAlpha/DeepSeek versus Table 2 full row",
            "status": "compatible",
            "evidence": "0.0461, 0.0450, 4.53, 15.10",
        },
        {
            "check": "Figure 3 full row versus Table 2 full row",
            "status": "compatible_at_figure_precision",
            "evidence": "0.046/0.045/4.53/15.10",
        },
        {
            "check": "v3 GPT-5.2 QuantaAlpha minus RD-Agent prose",
            "status": "arithmetically_compatible",
            "evidence": "IC +0.0186, ARR +1.10pp, MDD -4.96pp",
        },
        {
            "check": "v3 GPT-5.2 QuantaAlpha minus AlphaAgent prose",
            "status": "arithmetically_compatible",
            "evidence": "IC +0.0125, ARR +3.57pp, MDD -2.09pp",
        },
        {
            "check": "cross-seed mean/std/range table",
            "status": "arithmetically_compatible_at_display_precision",
            "evidence": "summary recomputes from three displayed combinations",
        },
        {
            "check": "daily t statistics",
            "status": "approximately_compatible_with_n_966",
            "evidence": "mean/(std/sqrt(966)) agrees after rounding",
        },
        {
            "check": "Figure 1 curve endpoints versus prose transfer returns",
            "status": "paper_graphic_prose_conflict",
            "evidence": "raster visually terminates near 69% CSI500 and 82% S&P500, not 40.28% and 19.1%",
        },
        {
            "check": "Figure 1 caption/prose metric versus y-axis",
            "status": "ambiguous_metric_label",
            "evidence": "caption/prose say cumulative excess return; axes say cumulative return",
        },
        {
            "check": "Figure 4 year coverage versus prose",
            "status": "paper_graphic_prose_conflict",
            "evidence": "prose says 2021--2025; figure shows 2022--2025",
        },
        {
            "check": "Appendix C factor identity versus evolution diagram",
            "status": "paper_internal_round_conflict",
            "evidence": "identity says Round 10 while offspring diagram says Round 8 Crossover",
        },
        {
            "check": "v1/v2 versus v3 headline results",
            "status": "large_unexplained_revision",
            "evidence": "IC 0.1501->0.0472; ARR 27.75->4.68; transfer 160/137->40.28/19.1",
        },
        {
            "check": "official repo README versus current paper",
            "status": "matches_v3_headline",
            "evidence": "README reports current lower headline values",
        },
        {
            "check": "paper source Figure 1 versus repository docs Figure 1",
            "status": "byte_identical",
            "evidence": "SHA-256 35d013008dd023c096f53ede8fa5b149944ed30b657b514e946bf2f6252061c3",
        },
        {
            "check": "current source default experiment versus paper profile",
            "status": "conflict",
            "evidence": "2 directions, 3 rounds, 2 crossovers, 1 factor/hypothesis, consistency disabled",
        },
        {
            "check": "native mining-loop Qlib config versus paper split",
            "status": "conflict",
            "evidence": "train 2016-2019, valid 2020, test/backtest 2021 only",
        },
        {
            "check": "standalone backtest config versus paper split and costs",
            "status": "substantially_compatible",
            "evidence": "2016-2025 split, label, TopkDropout, open price, costs match",
        },
        {
            "check": "paper reported result arrays in source release",
            "status": "aggregate_outputs_and_factor_pools_recovered_raw_arrays_absent",
            "evidence": "author-attributed pre-publication refs contain factor pools and 100+ aggregate metric artifacts, but no complete predictions/returns/holdings/plot arrays",
        },
        {
            "check": "complete public Git history result arrays",
            "status": "earlier_official_ref_census_was_incomplete",
            "evidence": "the 61 commits/five current heads omit a 28-commit author-attributed pre-publication lineage with factor pools, logs, HDF pointers, CSVs, and aggregate JSON results",
        },
        {
            "check": "historical Windows branch versus paper search specification",
            "status": "specification_disclosure_not_executable_profile",
            "evidence": "10 seed groups/30 expressions and 5 epochs/11 rounds are documented, but no matching run config or run lineage is shipped",
        },
        {
            "check": "v1/v2 paper main tables versus historical README raster",
            "status": "complete_visual_correspondence_not_regeneration",
            "evidence": "the identical 224-cell v1/v2 tables correspond to the pinned historical author raster",
        },
        {
            "check": "Alpha158(20) native end-to-end regeneration",
            "status": "all_eight_metrics_match_paper_rounding",
            "evidence": "recovered author data, Python 3.12/Qlib 0.9.7 path, LightGBM training, IC evaluation, and Top50/drop5 portfolio reproduce all eight v1/v2 values",
        },
        {
            "check": "QuantaAlpha GPT v1/v2 native result regeneration",
            "status": "material_non_reproduction",
            "evidence": "168/170 factors execute; IC 0.04170 vs 0.15008 and IR 0.87738 vs 3.32512; two public expressions fail in the released operator library",
        },
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
        (
            "search",
            "selection, ordering, and exact prompt insertion of the 10 disclosed seed groups in each reported run",
        ),
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
    resolutions = {
        "released full daily_pv.h5 content hash independently downloaded by this audit": (
            "yes",
            "official author Git-LFS object downloaded and SHA-256/HDF schema verified",
        ),
        "approximately 150 validated factor IDs": (
            "yes",
            "pre-publication author lineage contains the per-backbone 150-factor pools",
        ),
        "approximately 150 formulas/descriptions/code artifacts": (
            "yes",
            "public factor-pool JSONs contain IDs, formulas, descriptions, implementation code, feedback, and cache lineage",
        ),
        "final per-backbone factor pools": (
            "partial",
            "multiple named final pools are public; exact selection lineage for every paper row remains ambiguous",
        ),
        "hardware and library versions for paper runs": (
            "partial",
            "preserved logs prove Python 3.12 and Qlib 0.9.7; the remaining package pins are time-bounded inference",
        ),
        "paper-era immutable source tag tied to each arXiv version": (
            "partial",
            "no tag exists, but an author-attributed public-release commit predates v1 by 209.90 hours",
        ),
    }
    rows = []
    for category, item in gaps:
        resolved, evidence = resolutions.get(item, ("no", "not recovered from pinned primary/public source"))
        rows.append(
            {
                "category": category,
                "missing_or_ambiguous_item": item,
                "resolved": resolved,
                "evidence": evidence,
                "effect": "does_not_block_recovered_baseline" if resolved == "yes" else "prevents_exact_full_paper_replication",
            }
        )
    return rows


def mechanism_conformance() -> list[dict[str, Any]]:
    rows = [
        (
            "planning",
            "parallel initial direction generation",
            "implemented_analogue",
            "native code and prompts exist; default count is 2 rather than paper 10",
        ),
        (
            "trajectory",
            "complete hypothesis/factors/code/results/feedback record",
            "implemented_match",
            "StrategyTrajectory persists the declared lifecycle fields",
        ),
        ("trajectory", "lineage parent IDs", "implemented_match", "parent_ids are persisted"),
        (
            "trajectory",
            "persistent trajectory pool",
            "implemented_match",
            "JSON save/load executes in isolated component test",
        ),
        (
            "mutation",
            "mechanism-level variation",
            "partial_analogue",
            "prompt generates an orthogonal/independent new strategy",
        ),
        (
            "mutation",
            "failed-step localization",
            "not_implemented_as_claimed",
            "no code localizes the failed trajectory step",
        ),
        (
            "mutation",
            "rewrite only failed trajectory segment",
            "not_implemented_as_claimed",
            "generation returns a new hypothesis rather than patching a stored segment",
        ),
        (
            "mutation",
            "preserve other trajectory segments",
            "not_implemented_as_claimed",
            "no splice/preservation representation exists",
        ),
        ("crossover", "performance-aware parent selection", "implemented_match", "RankIC-based strategies exist"),
        ("crossover", "diverse direction/phase preference", "implemented_match", "combination score rewards both"),
        (
            "crossover",
            "validated trajectory-segment reuse",
            "not_implemented_as_claimed",
            "only truncated textual summaries are sent to the LLM",
        ),
        ("crossover", "actual segment splicing", "not_implemented_as_claimed", "no structured segment splice exists"),
        (
            "consistency",
            "hypothesis-description-expression checker",
            "implemented_match",
            "LLM consistency checker and correction loop exist",
        ),
        ("consistency", "enabled in shipped experiment", "config_conflict", "consistency_enabled is false"),
        (
            "consistency",
            "fail-closed checker errors",
            "not_implemented_as_claimed",
            "exception path returns consistent=true",
        ),
        ("complexity", "symbol-length constraint", "implemented_match", "native AST-backed regulator exists"),
        ("complexity", "base-feature constraint", "implemented_match", "native AST-backed regulator exists"),
        ("complexity", "free-argument ratio constraint", "implemented_match", "native AST-backed regulator exists"),
        ("complexity", "paper thresholds", "config_conflict", "checked-in 200/5/0.5 versus documented paper 250/6/0.5"),
        ("redundancy", "AST common-subtree matching", "implemented_match", "native parser and matcher execute"),
        (
            "redundancy",
            "paper factor-zoo snapshot",
            "missing_artifact",
            "factor_zoo_path is null and no paper pool is shipped",
        ),
        (
            "redundancy",
            "fail-closed regulator errors",
            "not_implemented_as_claimed",
            "regulator catches errors and permits progress",
        ),
        ("factor_generation", "three factors per hypothesis", "config_conflict", "checked-in default is one"),
        ("factor_generation", "public prompts", "implemented_match", "prompt YAML files are tracked"),
        ("backtest", "Qlib factor evaluation", "implemented_match", "native runner/config path exists"),
        (
            "backtest",
            "paper data split in mining loop",
            "config_conflict",
            "selected conf_baseline test/backtest ends in 2021",
        ),
        (
            "backtest",
            "paper standalone split/cost profile",
            "implemented_match",
            "configs/backtest.yaml matches most declared settings",
        ),
        ("portfolio", "TopkDropout top50/drop5", "implemented_match", "both configs specify it"),
        ("portfolio", "open execution and costs", "implemented_match", "0.05%/0.15% and open are configured"),
        ("release", "paper factor pool", "missing_artifact", "no generated factor library is tracked"),
        ("release", "paper trajectories", "missing_artifact", "no trajectory pool is tracked"),
        (
            "release",
            "published predictions/returns/results",
            "missing_artifact",
            "no result arrays or metrics are tracked",
        ),
        ("release", "baseline reproduction assets", "missing_artifact", "no per-baseline configs/runs are shipped"),
        (
            "release",
            "fully resolved environment",
            "partial_analogue",
            "dependency metadata exists but audit environment cannot resolve full stack",
        ),
    ]
    return [
        {
            "category": cat,
            "paper_dimension": dim,
            "status": status,
            "evidence": evidence,
            "paper_mechanism_credit": status == "implemented_match",
        }
        for cat, dim, status, evidence in rows
    ]


def config_conformance(source_root: Path) -> list[dict[str, Any]]:
    import yaml

    exp = yaml.safe_load((source_root / "configs/experiment.yaml").read_text(encoding="utf-8"))
    bt = yaml.safe_load((source_root / "configs/backtest.yaml").read_text(encoding="utf-8"))
    mine = yaml.safe_load(
        (source_root / "quantaalpha/factors/factor_template/conf_baseline.yaml").read_text(encoding="utf-8")
    )
    values = [
        ("planning.num_directions", 10, exp["planning"]["num_directions"], "conflict"),
        (
            "evolution.max_rounds",
            "five mutation+crossover cycles (mapping ambiguous)",
            exp["evolution"]["max_rounds"],
            "conflict",
        ),
        ("evolution.crossover_size", 2, exp["evolution"]["crossover_size"], "match"),
        (
            "evolution.crossover_n",
            "not stated in paper; source docs say 10",
            exp["evolution"]["crossover_n"],
            "not_paper_specified_and_docs_conflict",
        ),
        ("quality_gate.consistency_enabled", True, exp["quality_gate"]["consistency_enabled"], "conflict"),
        ("quality_gate.complexity_enabled", True, exp["quality_gate"]["complexity_enabled"], "match"),
        (
            "quality_gate.redundancy_enabled",
            True,
            exp["quality_gate"]["redundancy_enabled"],
            "match_but_no_paper_factor_zoo",
        ),
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
        (
            "standalone.exchange.deal_price",
            "open",
            bt["backtest"]["backtest"]["exchange_kwargs"]["deal_price"],
            "match",
        ),
        ("standalone.exchange.open_cost", 0.0005, bt["backtest"]["backtest"]["exchange_kwargs"]["open_cost"], "match"),
        (
            "standalone.exchange.close_cost",
            0.0015,
            bt["backtest"]["backtest"]["exchange_kwargs"]["close_cost"],
            "match",
        ),
        (
            "standalone.exchange.limit_threshold",
            0.095,
            bt["backtest"]["backtest"]["exchange_kwargs"]["limit_threshold"],
            "match",
        ),
        (
            "mining.dataset.train",
            ["2016-01-01", "2020-12-31"],
            mine["task"]["dataset"]["kwargs"]["segments"]["train"],
            "conflict",
        ),
        (
            "mining.dataset.valid",
            ["2021-01-01", "2021-12-31"],
            mine["task"]["dataset"]["kwargs"]["segments"]["valid"],
            "conflict",
        ),
        (
            "mining.dataset.test",
            ["2022-01-01", "2025-12-26"],
            mine["task"]["dataset"]["kwargs"]["segments"]["test"],
            "conflict",
        ),
        (
            "mining.backtest.period",
            ["2022-01-01", "2025-12-26"],
            [
                mine["port_analysis_config"]["backtest"]["start_time"],
                mine["port_analysis_config"]["backtest"]["end_time"],
            ],
            "conflict",
        ),
        (
            "mining.feature_count",
            6,
            len(mine["data_handler_config"]["data_loader"]["kwargs"]["config"]["feature"][0]),
            "conflict",
        ),
    ]
    return [
        {
            "parameter": name,
            "paper_value": json.dumps(paper, default=str),
            "released_value": json.dumps(released, default=str),
            "status": status,
        }
        for name, paper, released, status in values
    ]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    files = str(
        run_git(source_root, "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", SOURCE_COMMIT)
    ).splitlines()
    result_patterns = (
        "result",
        "metric",
        "trajectory",
        "factor_pool",
        "prediction",
        "return",
        "holding",
        "order",
        "fill",
        "seed",
    )
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
        rows.append(
            {
                "relative_path": rel,
                "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "role": role,
                "paper_result_artifact": paper_result_artifact,
            }
        )
    return rows


def author_output_correspondence(source_root: Path, paper_source_root: Path) -> list[dict[str, Any]]:
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
        repository_blob = run_git(source_root, "show", f"{SOURCE_COMMIT}:{repository_path}", binary=True)
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
    numeric = {
        "images/figure3.png",
        "images/figure4.png",
        "images/figure5.png",
        "images/ablation.pdf",
        "images/case_study.pdf",
    }
    for path in sorted(p for p in paper_source_root.rglob("*") if p.is_file()):
        rel = path.relative_to(paper_source_root).as_posix()
        rows.append(
            {
                "relative_path": rel,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "asset_role": "numeric_result_figure" if rel in numeric else "paper_source",
                "underlying_numeric_array": False,
            }
        )
    return rows


def dataset_inventory(dataset_api: Path, tree_api: Path, debug_h5: Path) -> list[dict[str, Any]]:
    meta = json.loads(dataset_api.read_text(encoding="utf-8"))
    tree = json.loads(tree_api.read_text(encoding="utf-8"))
    if meta["id"] != "QuantaAlpha/qlib_csi300" or meta["sha"] != HF_DATASET_COMMIT:
        raise RuntimeError("Hugging Face dataset metadata pin changed")
    rows = []
    for item in tree:
        lfs = item.get("lfs", {})
        rows.append(
            {
                "path": item["path"],
                "bytes": item["size"],
                "git_oid": item["oid"],
                "lfs_sha256": lfs.get("oid", ""),
                "last_commit": item["lastCommit"]["id"],
                "last_commit_date": item["lastCommit"]["date"],
                "public": not meta["private"],
                "gated": meta["gated"],
                "paper_result_artifact": False,
            }
        )
    if sha256(debug_h5) != HF_DEBUG_SHA256:
        raise RuntimeError("Hugging Face debug HDF pin changed")
    return rows


COMPONENT_DRIVER = r"""import importlib.util, json, sys, tempfile, types
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
"""


def compile_revision(source_root: Path, commit: str | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        root = source_root
        if commit:
            archive = subprocess.run(
                ["git", "-C", str(source_root), "archive", commit], check=True, capture_output=True
            ).stdout
            tar_path = Path(td) / "src.tar"
            tar_path.write_bytes(archive)
            with tarfile.open(tar_path) as handle:
                handle.extractall(Path(td) / "src", filter="data")
            root = Path(td) / "src"
        py_files = sorted(root.rglob("*.py"))
        failures = []
        for path in py_files:
            try:
                py_compile.compile(
                    str(path),
                    doraise=True,
                    cfile=str(Path(td) / (hashlib.sha256(str(path).encode()).hexdigest() + ".pyc")),
                )
            except Exception as exc:
                failures.append({"path": str(path.relative_to(root)), "error": str(exc)})
        return {"python_files": len(py_files), "compiled": len(py_files) - len(failures), "failures": failures}


def native_execution(source_root: Path) -> dict[str, Any]:
    current = compile_revision(source_root)
    initial = compile_revision(source_root, INITIAL_COMMIT)
    component_python = os.environ.get("QUANTAALPHA_COMPONENT_PYTHON", sys.executable)
    component = subprocess.run(
        [component_python, "-c", COMPONENT_DRIVER, str(source_root)], capture_output=True, text=True
    )
    component_payload = (
        json.loads(component.stdout.strip().splitlines()[-1])
        if component.returncode == 0
        else {"error": component.stderr[-3000:]}
    )
    upstream = subprocess.run(
        [component_python, str(source_root / "quantaalpha/factors/coder/test.py")],
        cwd=source_root / "quantaalpha/factors/coder",
        capture_output=True,
        text=True,
    )
    return {
        "component_python": component_python,
        "current_compile": current,
        "initial_compile": initial,
        "component_driver_returncode": component.returncode,
        "component_checks": component_payload,
        "upstream_tests_discovered": 1,
        "upstream_tests_passed": int(upstream.returncode == 0),
        "upstream_tests_failed": int(upstream.returncode != 0),
        "upstream_test_failure": "missing template_debug.jinjia2"
        if "template_debug.jinjia2" in upstream.stderr
        else upstream.stderr[-1000:],
        "full_native_environment_reproduced": False,
        "recovered_baseline_native_environment_reproduced": True,
        "paper_experiment_executed": True,
        "paper_experiment_execution_scope": "Alpha158(20) full row and 168/170-factor QuantaAlpha/GPT diagnostic",
        "paper_result_cells_reproduced": 8,
        "component_execution_is_paper_result_credit": False,
        "llm_or_market_api_called": False,
    }


def verify_pins(
    source_root: Path,
    papers: Mapping[str, tuple[Path, Path]],
    paper_source_root: Path,
    dataset_api: Path,
    debug_h5: Path,
) -> None:
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


def build_audit(
    source_root: Path,
    public_census_root: Path,
    papers: Mapping[str, tuple[Path, Path]],
    paper_source_root: Path,
    dataset_api: Path,
    tree_api: Path,
    debug_h5: Path,
    output_dir: Path,
) -> dict[str, Any]:
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
    history_commits, history_paths, history_summary = public_source_history(source_root)
    prepublication_commits, prepublication_summary = prepublication_public_history(public_census_root)
    fork_heads, fork_summary = public_fork_census(
        public_census_root, output_dir / "public_fork_branch_ref_snapshot.csv"
    )
    prepublication_results = prepublication_result_conformance(public_census_root, paper_source_root)
    recovered_data = recovered_data_provenance()
    rerun_rows = native_rerun_conformance()
    regeneration = native_result_regeneration_payload()
    branch_evidence = historical_branch_evidence(source_root)
    versioned_main_table = paper_version_main_table_rows(source_root, paper_source_root)
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
        "released_source_history_inventory.csv": history_commits,
        "released_source_history_paths.csv": history_paths,
        "prepublication_source_history_inventory.csv": prepublication_commits,
        "public_fork_unique_head_inventory.csv": fork_heads,
        "prepublication_result_conformance.csv": prepublication_results,
        "recovered_data_provenance.csv": recovered_data,
        "native_rerun_conformance.csv": rerun_rows,
        "historical_branch_evidence_inventory.csv": branch_evidence,
        "paper_version_main_table_conformance.csv": versioned_main_table,
        "released_dataset_inventory.csv": datasets,
        "paper_source_asset_inventory.csv": paper_assets,
        "author_output_correspondence.csv": author_outputs,
    }
    for name, rows in outputs.items():
        write_csv(output_dir / name, rows)
    (output_dir / "native_component_execution.json").write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")
    (output_dir / "public_source_history.json").write_text(
        json.dumps(history_summary, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "prepublication_source_history.json").write_text(
        json.dumps(prepublication_summary, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "public_fork_census.json").write_text(
        json.dumps(fork_summary, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "native_result_regeneration.json").write_text(
        json.dumps(regeneration, indent=2) + "\n", encoding="utf-8"
    )
    status_counts = Counter(row["status"] for row in mechanisms)
    manifest: dict[str, Any] = {
        "paper": "QuantaAlpha: An Evolutionary Framework for LLM-Driven Alpha Mining",
        "overall_status": "one_published_baseline_row_regenerated_main_quantaalpha_claim_not_reproduced",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_versions": PAPER_VERSIONS,
        "current_paper_version": "v3",
        "source_url": SOURCE_URL,
        "source_commit": SOURCE_COMMIT,
        "source_commit_date": SOURCE_COMMIT_DATE,
        "initial_commit": INITIAL_COMMIT,
        "initial_commit_date": INITIAL_COMMIT_DATE,
        "initial_commit_scope": "first_commit_reachable_from_current_official_heads_not_complete_public_history",
        "prepublication_start_commit": PREPUBLICATION_START_COMMIT,
        "prepublication_results_commit": PREPUBLICATION_RESULTS_COMMIT,
        "prepublication_release_commit": PREPUBLICATION_RELEASE_COMMIT,
        "prepublication_release_lead_hours_before_v1": PREPUBLICATION_RELEASE_LEAD_HOURS,
        "hf_dataset_url": HF_DATASET_URL,
        "hf_dataset_commit": HF_DATASET_COMMIT,
        "paper_numeric_table_cells_total": len(tables),
        "native_numeric_table_cells_reproduced": sum(row["independently_regenerated"] for row in tables),
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
            row["correspondence_kind"] == "complete_visual_and_ocr_correspondence" for row in author_outputs
        ),
        "author_output_result_claims_corroborated": sum(
            row["claim_role"] == "result" and row["author_output_correspondence"] for row in claims
        ),
        "author_output_dated_return_raster_shipped": True,
        "author_output_underlying_arrays_shipped": False,
        "paper_result_arrays_shipped": 0,
        "aggregate_metric_artifacts_shipped_in_prepublication_history": True,
        "paper_factor_pool_shipped": True,
        "paper_trajectory_pool_shipped": False,
        "paper_baseline_runs_shipped": True,
        "paper_seeds_shipped": False,
        "paper_seeds_field_means_random_or_run_seed_lineage": True,
        "historical_direction_seed_groups_disclosed": True,
        "paper_run_direction_seed_selection_and_order_shipped": False,
        "paper_cost_ledger_shipped": False,
        "published_non_table_claims_total": len(claims),
        "published_result_claims_total": sum(row["claim_role"] == "result" for row in claims),
        "paper_specification_gaps_total": len(gaps),
        "paper_internal_and_source_checks_total": len(checks),
        "paper_version_drift_claims_total": len(versions),
        "large_unexplained_revision_claims_total": len(versions),
        "versioned_main_table_cells_total": len(versioned_main_table),
        "versioned_main_table_cells_by_paper_version": dict(
            Counter(row["paper_version"] for row in versioned_main_table)
        ),
        "versioned_main_table_cells_author_output_corroborated": sum(
            row["author_output_correspondence"] for row in versioned_main_table
        ),
        "versioned_main_table_cells_independently_regenerated": sum(
            row["independently_regenerated"] for row in versioned_main_table
        ),
        "distinct_author_rendered_main_table_cells_across_versions": 420,
        "historical_v1_v2_main_table_cells_corroborated": 224,
        "historical_v1_v2_main_table_cells_independently_regenerated": 8,
        "prepublication_quantaalpha_specific_commits_total": len(prepublication_commits),
        "prepublication_unique_historical_paths_total": prepublication_summary["unique_historical_paths"],
        "github_rest_reported_public_forks": fork_summary["github_rest_reported_forks"],
        "graphql_accessible_public_forks": fork_summary["graphql_accessible_forks"],
        "public_fork_accessibility_gap": fork_summary["rest_minus_accessible_fork_gap"],
        "public_fork_branch_refs_examined": fork_summary["graphql_accessible_branch_refs"],
        "public_fork_unique_heads_examined": fork_summary["unique_heads"],
        "public_fork_divergent_heads_examined": fork_summary["divergent_heads_reviewed"],
        "public_fork_author_attributed_post_v1_heads": fork_summary["author_attributed_post_v1_heads"],
        "public_fork_author_attributed_post_v1_extra_commits": fork_summary[
            "author_attributed_post_v1_extra_commits"
        ],
        "public_fork_author_attributed_post_v1_native_result_paths": fork_summary[
            "author_attributed_post_v1_native_result_paths"
        ],
        "public_fork_paper_result_artifacts_discovered_post_v1": fork_summary[
            "paper_result_artifacts_discovered_in_post_v1_fork_heads"
        ],
        "prepublication_aggregate_result_cells_corresponding_at_paper_rounding": sum(
            row["rounded_match"] for row in prepublication_results
        ),
        "prepublication_aggregate_result_cells_examined": len(prepublication_results),
        "native_rerun_metric_cells_examined": len(rerun_rows),
        "native_rerun_metric_cells_independently_regenerated": sum(
            row["independently_regenerated"] for row in rerun_rows
        ),
        "alpha158_20_published_metric_cells_independently_regenerated": 8,
        "quantaalpha_gpt_v1_v2_published_metric_cells_independently_regenerated": 0,
        "official_author_daily_pv_lfs_sha256": AUTHOR_DAILY_PV_LFS_SHA256,
        "recovered_provider_cross_artifact_matrix_sha256": RECOVERED_PROVIDER_MATRIX_SHA256,
        "source_mechanism_dimensions_total": len(mechanisms),
        "source_mechanism_status_counts": dict(status_counts),
        "source_mechanism_matches": status_counts["implemented_match"],
        "source_mechanism_fully_faithful": False,
        "source_config_dimensions_total": len(configs),
        "source_config_status_counts": dict(Counter(row["status"] for row in configs)),
        "tracked_source_files_total": len(inventory),
        "tracked_source_python_files_total": sum(row["relative_path"].endswith(".py") for row in inventory),
        "tracked_source_test_files_total": 1,
        "public_source_branches_total": history_summary["public_branches_total"],
        "public_source_tags_total": history_summary["public_tags_total"],
        "public_source_releases_total": history_summary["public_releases_total"],
        "public_source_reachable_commits_total": history_summary["reachable_commits_total"],
        "public_source_unique_historical_paths_total": history_summary["unique_historical_paths_total"],
        "public_source_reachable_object_counts": history_summary["reachable_object_counts"],
        "public_source_unreachable_objects_total": history_summary["unreachable_objects_total"],
        "current_official_ref_native_result_artifact_paths_total": history_summary["native_result_artifact_paths_total"],
        "current_official_ref_surface_is_complete_public_history": False,
        "historical_branch_evidence_items_total": len(branch_evidence),
        "historical_direction_seed_groups_total": 10,
        "historical_direction_seed_factor_expressions_total": 30,
        "historical_operational_frontend_files_total": 44,
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
            "The public artifact is materially stronger than the current official branch heads imply. An "
            "author-attributed 28-commit lineage predates paper v1 and contains factor pools, aggregate result "
            "JSONs, logs, plots, and an official Git-LFS market-data object. The recovered native Python "
            "3.12/Qlib 0.9.7 pipeline independently reproduces all eight Alpha158(20) cells at paper rounding. "
            "That is real paper-result credit, but it is only one baseline row. The best paper-configured "
            "QuantaAlpha/GPT rerun executes 168 of 170 factors and materially misses the claimed v1/v2 result "
            "(IC 0.04170 versus 0.15008; IR 0.87738 versus 3.32512). Two released expressions fail under the "
            "released operator library. Raw predictions, returns, holdings, prompt transcripts, complete run "
            "lineage, and plot arrays remain absent. The v1/v2-to-v3 result revision and v3 internal conflicts "
            "also remain unexplained. A dated census exhausted all 267 GraphQL-accessible public forks and "
            "357 branch refs (77 unique heads): nine author-attributed post-v1 heads add source/config/docs but "
            "no native result arrays, while one unaffiliated post-v1 summary uses different strategies and has "
            "no raw lineage. Therefore this is a partial, evidence-backed replication—not a faithful full-paper "
            "reproduction."
        ),
    }
    report = f"""# QuantaAlpha paper-level conformance audit

Overall verdict: **one complete published baseline row independently regenerated; the
headline QuantaAlpha result does not reproduce**.

## Primary-source boundary

- All three arXiv revisions of [2602.07085]({PAPER_URL}) are pinned by PDF and source-archive SHA-256. The current audit targets v3, submitted {PAPER_VERSIONS["v3"]["date"]}.
- The current official heads are pinned to `{SOURCE_COMMIT}`, but their **{history_summary["reachable_commits_total"]}-commit/{history_summary["unique_historical_paths_total"]}-path** surface is not the complete public history.
- Public PR/fork refs preserve an author-attributed **{len(prepublication_commits)}-commit, {prepublication_summary["unique_historical_paths"]}-path** QuantaAlpha-specific lineage beginning `{PREPUBLICATION_START_COMMIT}`. Its explicit release commit `{PREPUBLICATION_RELEASE_COMMIT}` predates v1 by **{PREPUBLICATION_RELEASE_LEAD_HOURS:.2f} hours**. Inherited RD-Agent ancestors are excluded from these counts.
- A dated GitHub census enumerated **{fork_summary["graphql_accessible_forks"]} accessible forks and {fork_summary["graphql_accessible_branch_refs"]} branch refs**, collapsing to **{fork_summary["unique_heads"]} unique heads**. GitHub REST reported {fork_summary["github_rest_reported_forks"]} forks; the {fork_summary["rest_minus_accessible_fork_gap"]} deleted/private/otherwise unavailable repositories are explicitly not claimed as inspected. All {fork_summary["divergent_heads_reviewed"]} divergent unique heads were reviewed.
- Nine author-attributed post-v1 fork heads add {fork_summary["author_attributed_post_v1_extra_commits"]} unique commits and {fork_summary["author_attributed_post_v1_changed_paths"]} changed paths, but **zero native result artifacts**. Eight of their nine image blobs were already in the official/prepublication line; the only new blob is the documentation image `{fork_summary["author_attributed_post_v1_new_image_path"]}`. One unaffiliated post-v1 fork adds a derived five-strategy JSON summary with different factors/metrics and no raw lineage; it receives zero paper-result credit.
- The official public [Hugging Face dataset]({HF_DATASET_URL}) is pinned to `{HF_DATASET_COMMIT}`. It provides a Qlib package and daily HDF files, but no paper result arrays.
- The official pre-publication Git-LFS HDF object is pinned to `{AUTHOR_DAILY_PV_LFS_SHA256}`. A fork-preserved Qlib provider is separately pinned and receives no official-author credit; a 2,679x6 security slice is bit-identical between them.

## Result evidence

- The v3 paper contains **344 numeric table cells**. The README raster corroborates all 196 main-table cells as author output, but only the seven v3 Alpha158(20) cells are independently regenerated.
- The identical v1/v2 main tables contain 224 cells each. Native aggregate JSONs give rounded correspondence for **{sum(row["rounded_match"] for row in prepublication_results)}/{len(prepublication_results)} examined cells** across 11 rows. These are author-output lineage, not independent regeneration; filename/model conflicts are retained in the ledger.
- The native Alpha158(20) run reproduces all **8/8** v1/v2 metrics, including training, prediction, IC/RankIC evaluation, and the Top50/drop5 portfolio. Across version-specific tables this is **23/644** regenerated cells (8 in v1, 8 in v2, 7 in v3).
- The paper-configured QuantaAlpha/GPT diagnostic recomputes 148/150 public custom factors plus Alpha158(20), but does not reproduce the claim: IC **0.04170 vs 0.15008**, ARR **6.05% vs 27.75%**, IR **0.87738 vs 3.32512**, and MDD **11.93% vs 7.98%**.
- Numeric result figures add **40 visible labels**, **47 discrete unlabeled central markers**, and **10 raster return curves**. The README ships the 17-label case-study raster and byte-identical copies of the paper-source Figure 3--5 assets, corroborating **17 labels, 47 markers, and 10 curves**. Their underlying arrays are absent; **0/40**, **0/47**, and **0/10** are regenerated.

## What really works

- The release is not pseudocode: **{native["current_compile"]["compiled"]}/{native["current_compile"]["python_files"]}** current Python files and **{native["initial_compile"]["compiled"]}/{native["initial_compile"]["python_files"]}** initial-release Python files compile. The audit executes native expression parsing/complexity/subtree matching, trajectory JSON round-trip, lineage round-trip, and performance/diversity-aware crossover selection without calling an LLM or market API.
- Public prompt/config/source paths implement meaningful planning, full trajectory records, mutation/crossover generation, semantic consistency, AST complexity/redundancy checks, Qlib evaluation, and TopkDropout backtesting. **{status_counts["implemented_match"]}/{len(mechanisms)}** audited mechanism dimensions are implementation matches.
- The recovered `backtest_v2` profile matches the paper split, label, LightGBM seed, Top-50/drop-5 portfolio, open execution, and 0.05%/0.15% costs closely enough to reproduce Alpha158(20) exactly at displayed precision.
- Pre-publication pools preserve IDs, formulas, descriptions, implementation code, backtest feedback, and cache lineage for the LLM-generated factors.

## Why it is not faithful yet

- The actual checked-in `configs/experiment.yaml` is a demo profile: 2 rather than 10 directions, 3 rounds rather than the paper's five mutation/crossover cycles, 2 rather than the documented 10 crossover combinations, 1 rather than 3 factors per hypothesis, lower complexity limits, and the consistency gate disabled.
- Paper prose describes mutation as targeted failed-segment repair and crossover as reuse/splicing of validated trajectory segments. The source generates new hypotheses from truncated textual summaries; it does not localize, preserve, or splice structured trajectory segments.
- The current-source upstream test still fails because `template_debug.jinjia2` is missing. The released custom loader also refuses factors whose author cache paths are gone; two public expressions remain invalid under the released operator library.
- Exact LLM snapshots, prompts/responses, retry traces, parent selections, seeds, predictions, holdings, raw daily returns, and plot arrays are absent. Package versions beyond directly evidenced Python 3.12/Qlib 0.9.7 are time-bounded inference.
- v1/v2 reported IC 0.1501, ARR 27.75%, MDD 7.98%, and transfer returns 160%/137%; v3 reports 0.0472, 4.68%, 11.80%, and 40.28%/19.1%. No released result lineage explains the revision. In v3, Figure 1's visible endpoints do not agree with its prose, Figure 4 omits 2021 despite the text's 2021--2025 claim, and Appendix C labels the same offspring Round 10 and Round 8.

## Honest interpretation

The public record now supports a strong native baseline replication and much better source/data lineage than the current official heads reveal. It does **not** support the headline QuantaAlpha numbers end-to-end. The exact baseline success and the headline failure are both retained. `--strict` remains nonzero until the full reported study—not merely its framework, screenshots, or aggregate JSONs—is independently reproduced within declared tolerances.
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
    base = Path(os.environ.get("QUANTAALPHA_PAPER_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_paper"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get("QUANTAALPHA_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_source")
        ),
    )
    parser.add_argument(
        "--public-census-root",
        type=Path,
        default=Path(
            os.environ.get(
                "QUANTAALPHA_PUBLIC_CENSUS_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_fork_census",
            )
        ),
        help="bare/full clone containing pinned public PR and fork refs",
    )
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
    parser.add_argument(
        "--output-dir", type=Path, default=project_root / "paper_runs/paper_replication_audits/quantaalpha"
    )
    parser.add_argument("--strict", action="store_true", help="Return nonzero until the full paper is reproduced")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    papers = {
        "v1": (args.paper_v1_pdf, args.paper_v1_source),
        "v2": (args.paper_v2_pdf, args.paper_v2_source),
        "v3": (args.paper_v3_pdf, args.paper_v3_source),
    }
    manifest = build_audit(
        args.source_root,
        args.public_census_root,
        papers,
        args.paper_source_root,
        args.dataset_api,
        args.dataset_tree_api,
        args.debug_h5,
        args.output_dir,
    )
    print(json.dumps(manifest, indent=2))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
