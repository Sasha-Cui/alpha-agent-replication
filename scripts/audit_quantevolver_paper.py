#!/usr/bin/env python3
"""Audit QuantEvolver arXiv v1 against its pinned official source release.

The public repository landed minutes before the paper but explicitly excludes
the market data, trained checkpoints, experiment logs, and paper reproduction
scripts.  This audit therefore enumerates every numeric table result, records
the paper's quantitative prose/figure claims, checks internal and paper/source
metric identities, inventories the released implementation, and executes only
the deterministic public component path.  The existing 3/3 grade-B disclosed-
component gate is cited separately and is never promoted to a paper result.
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
from typing import Any, Dict, List, Mapping, Sequence, Tuple


PAPER_URL = "https://arxiv.org/pdf/2605.15412v1"
PAPER_VERSION = "arXiv:2605.15412v1"
PAPER_DATE = "2026-05-14T20:54:40Z"
PAPER_SHA256 = "55f119b0cdf47f10f72b9fed0d89a46228fc9c2b1d12c5e7f10b072d04bd0f7b"
PAPER_SOURCE_SHA256 = "e040fa429db69e648bacab920fcb2e5e8dcd6d6916745b6d6d8deab35d84cb46"
SOURCE_URL = "https://github.com/QuantLLM/QuantEvolver"
SOURCE_COMMIT = "4eb0e78842138ada5334349585b114ad923564e8"
SOURCE_COMMIT_DATE = "2026-05-15T04:38:26+08:00"
README_ONLY_COMMIT = "6372a607f68f2717af2fe99601f5ae228721495a"
README_ONLY_COMMIT_DATE = "2026-05-15T04:37:50+08:00"
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_REPOSITORIES = (
    "xtwp1024/QuantEvolver",
    "effysxh/QuantEvolver",
    "yfhu86/QuantEvolver",
    "lusic2018/QuantEvolver",
)
PUBLIC_FORK_COUNT = 4
PUBLIC_FORK_BRANCH_REF_COUNT = 4
PUBLIC_FORK_UNIQUE_HEAD_COUNT = 1
PUBLIC_FORK_TAG_REF_COUNT = 0
REPOSITORY_PDF_SHA256 = "9e72f2c188882b8f3cc8a67ac724021521c522d8f40627485a5921613548c905"
DEFAULT_SOURCE_PYTHON = (
    "/nfs/roberts/project/pi_btk22/zc362/environments/current/"
    "quantevolver-v010/bin/python"
)
RECONSTRUCTED_ENV_FREEZE_SHA256 = (
    "6bd00b45a9459fee897feb1c7f786cb2d71e5c7d8faeffeff469106709d43c21"
)

PAPER_RESULT_LITERALS = ("53.22", "0.0586", "50.2644", "125.6", "2.26", "0.1923", "0.0500")
RESULT_PATH_PARTS = {
    "checkpoint",
    "checkpoints",
    "experiment",
    "experiments",
    "log",
    "logs",
    "output",
    "outputs",
    "result",
    "results",
    "run",
    "runs",
}
RESULT_ARTIFACT_SUFFIXES = (
    ".ckpt",
    ".csv",
    ".json",
    ".jsonl",
    ".log",
    ".npy",
    ".npz",
    ".out",
    ".parquet",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
    ".safetensors",
)

PINNED_SOURCE_SHA256 = {
    "README.md": "ecd1a131450cff65c71de4c0360adf3908f3d61e5a8ed50e2566d103b06fab36",
    "pyproject.toml": "f898b2db437038ddad95c4622beeb5d69eff8ed52f41b7dbcffa51e1c31bf6ab",
    "configs/example_rft_pure_verl.yaml": "942fa8e91edc5df0fb9c57c3b85444adc921341a5ea23ad75ecd6870fb4727e2",
    "configs/example_seed_pipeline.yaml": "3fb2300719fcb75e8d53964487f2e414a3883848abae9465d08bacb855d462bc",
    "examples/seed_candidates.yaml": "c8a20de0850156b8c831547a58239bb88b5d6486da50d6f9ecbaa2df0d13d718",
    "quant_evolver/dsl/evaluator.py": "8c6e8201b8794bb2166a118cb753231bca1379c8aff115c6d29799ce8400516c",
    "quant_evolver/evaluation/cross_sectional_rankic.py": "b38066082453d58295e45467fad662b33c1a1ef97232d3575348e2cfade56295",
    "quant_evolver/rft/config.py": "85218525baaac77d096c7596ae427a826986a86ee2eeab41a78ee82c80e2b248",
    "quant_evolver/rft/task_bank.py": "8eb8eb02c99525b1d605e8d54cadcc83c95aa27b643baa651972aee3c12f51dc",
    "quant_evolver/rft/prompts.py": "ad7b18ccb0e5a46f76b4b3a64210d420bbbf5b064e6383d054d28dbf0f0ea243",
    "quant_evolver/rft/reward_bridge.py": "70b1676f6afa3bcf23bf23ecf439fa22ff2baa4c7eb10d77de8e352d86d9fdca",
    "quant_evolver/rft/verl_main.py": "465090116fd5204e5b3761ca8175fa91fd6398624f757975dc6c8bfd842d1df4",
    "tests/test_dsl.py": "9c928cb3bf50de77255e0c9b48d7d7fa333f823c33f6be78e09745727154db7e",
    "tests/test_scenario_refiner.py": "75356d0b33c5f725c513d77bf364a18be6bd161167671bc0dce648923526673a",
    "tests/test_seed_taskbank.py": "d88b29663ef1234e46376a8ce8c1c58fc3688d6384244382b781bf29926214ee",
    "paper/QuantEvolver.pdf": REPOSITORY_PDF_SHA256,
}

PINNED_PAPER_SOURCE_SHA256 = {
    "bare_jrnl_new_sample4.tex": "f7d7966f8736b2b5bf49b745aa264465d0f33d84e87d9d80e782d2871a50a586",
    "figures/hyberparameter/corrth_sensitivity_binance_xsec.pdf": "9a4a487adaab334fa3cf32f51f4f173f3df5e0ff9c87a364e3ef9d9e5e542dc7",
    "figures/hyberparameter/topk_sensitivity_binance_xsec.pdf": "653e1072c7b8edd8d121b71a27f65df217b9cade700ec9908c8fb411cefc67e7",
    "figures/training/critic_score_mean.pdf": "467934e0742baf7a0fefe921caaa177e7068441024ce658b2ab0e36783ffc12b",
    "figures/training/rolling_top10_score.pdf": "24bf5741fcdd96a9326383d9d54f6f723cf299b0639aed0ee8164626311e61df",
    "figures/crypto_xsec_profitability.pdf": "5b0d8d7b4a514244d5277bad7a50639479890cbcd1bf7a9d79668fdffb1242c4",
}

COMPONENT_GATE_SHA256 = {
    "manifest.json": "a0f137a0284a4ac798d5782d6db29e102a6b732ede6c7d749b848ff53de14cdc",
    "faithfulness_ledger.csv": "4fed50f22fc64646c6d962ec1e1b494bb1db24d6187e7a7a0e13956a6642a450",
    "upstream_conformance.json": "fe83757055b8f6901b69784bd14d9232d17563a4f16d398b938a8309b47715f7",
}

BENCHMARKS = ("A", "B", "Gamma")
METRICS = ("DirAcc_pct", "IC", "RankIC", "ICIR")
OVERALL_RESULTS: Dict[str, Tuple[float, ...]] = {
    "AlphaBench": (51.82, 0.0147, 0.0362, 0.6139, 49.57, 0.0288, 0.0337, 24.4040, 55.56, 0.1480, 0.1688, 2.6021),
    "QuantaAlpha": (52.15, 0.0095, 0.0313, 3.6004, 49.41, 0.0216, 0.0235, 24.4209, 54.03, 0.1144, 0.1003, 2.0239),
    "R&D-Agent": (52.59, 0.0002, 0.0527, 0.9779, 49.40, 0.0188, 0.0205, 19.0101, 53.31, 0.1001, 0.0589, -0.8667),
    "Alpha-Jungle": (52.25, 0.0023, 0.0357, 1.5664, 49.39, 0.0185, 0.0200, 19.2806, 48.92, 0.0369, -0.0008, -0.7166),
    "QuantEvolver": (53.22, -0.0058, 0.0481, 1.1191, 49.96, 0.0500, 0.0586, 50.2644, 53.49, 0.1502, 0.1923, 5.4289),
}

ABLATIONS = (
    (True, True, True, 0.0500, 0.0586, 50.2644),
    (True, False, True, 0.0421, 0.0505, 45.8038),
    (False, True, True, 0.0434, 0.0519, 44.2189),
    (False, False, True, 0.0461, 0.0540, 44.3755),
    (False, False, False, 0.0001, 0.0002, 0.2506),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> Any:
    result = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return result.stdout


def git_blob(source_root: Path, relative: str) -> bytes:
    return run_git(source_root, "show", f"{SOURCE_COMMIT}:{relative}", binary=True)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_table_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for method, values in OVERALL_RESULTS.items():
        for benchmark_index, benchmark in enumerate(BENCHMARKS):
            for metric_index, metric in enumerate(METRICS):
                rows.append(
                    {
                        "paper_table": "Overall Evaluation",
                        "method": method,
                        "benchmark": benchmark,
                        "metric": metric,
                        "paper_value": values[benchmark_index * 4 + metric_index],
                        "cell_kind": "direct_result",
                        "native_reproduced_value": "",
                        "absolute_difference": "",
                        "status": (
                            "unavailable_missing_native_paper_result_path"
                            if method == "QuantEvolver"
                            else "unavailable_missing_native_baseline_result_path"
                        ),
                        "paper_result_credit": False,
                    }
                )
    for index, (seed, div, dsl, ic, rank_ic, icir) in enumerate(ABLATIONS, start=1):
        label = f"Seed={int(seed)};Div={int(div)};DSL={int(dsl)}"
        for metric, value in (("IC", ic), ("RankIC", rank_ic), ("ICIR", icir)):
            rows.append(
                {
                    "paper_table": "Ablation Results on Dataset B",
                    "method": label,
                    "benchmark": "B",
                    "metric": metric,
                    "paper_value": value,
                    "cell_kind": "direct_result",
                    "native_reproduced_value": "",
                    "absolute_difference": "",
                    "status": "unavailable_missing_native_ablation_result_path",
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 75 or Counter(row["paper_table"] for row in rows) != {
        "Overall Evaluation": 60,
        "Ablation Results on Dataset B": 15,
    }:
        raise RuntimeError("QuantEvolver numeric-table denominator changed")
    return rows


def ablation_design_rows() -> List[Dict[str, Any]]:
    rows = []
    for index, (seed, div, dsl, _ic, _rank_ic, _icir) in enumerate(ABLATIONS, start=1):
        for component, enabled in (("Seed", seed), ("Div", div), ("DSL", dsl)):
            rows.append(
                {
                    "paper_table": "Ablation Results on Dataset B",
                    "row": index,
                    "component": component,
                    "paper_enabled": enabled,
                    "native_paper_run_reproduced": False,
                    "status": "design_cell_enumerated_but_ablation_run_unavailable",
                }
            )
    if len(rows) != 15:
        raise RuntimeError("QuantEvolver ablation-design denominator changed")
    return rows


def published_non_table_claims() -> List[Dict[str, Any]]:
    raw = [
        ("Introduction", "relative directional-accuracy improvement", 7.8, "pct", "result", "independent_claim"),
        ("Introduction", "best out-of-sample RankIC improvement", 109.5, "pct", "result", "independent_claim"),
        ("Introduction", "top-10 out-of-sample RankIC mean improvement", 186.9, "pct", "result", "independent_claim"),
        ("Experimental Setup", "fusion correlation threshold", 0.7, "correlation", "configuration", "exact"),
        ("Experimental Setup", "compute CPU cores", 160, "cores", "configuration", "exact"),
        ("Experimental Setup", "compute RAM", 1.8, "TiB", "configuration", "exact"),
        ("Experimental Setup", "compute H20 GPUs", 8, "GPUs", "configuration", "exact"),
        ("Benchmark A", "bar and target interval", 5, "minutes", "configuration", "exact"),
        ("Benchmark B", "rebalance interval", 1, "hour", "configuration", "exact"),
        ("Overall prose A", "QuantEvolver DirAcc", 53.22, "pct", "result", "duplicate_table"),
        ("Overall prose A", "strongest baseline DirAcc", 52.59, "pct", "result", "duplicate_table"),
        ("Overall prose B", "QuantEvolver RankIC", 0.0586, "RankIC", "result", "duplicate_table"),
        ("Overall prose B", "strongest baseline RankIC", 0.0337, "RankIC", "result", "duplicate_table"),
        ("Overall prose B", "QuantEvolver IC", 0.0500, "IC", "result", "duplicate_table"),
        ("Overall prose B", "QuantEvolver ICIR", 50.2644, "ICIR", "result", "duplicate_table"),
        ("Overall prose Gamma", "QuantEvolver RankIC", 0.1923, "RankIC", "result", "duplicate_table"),
        ("Overall prose Gamma", "QuantEvolver ICIR", 5.4289, "ICIR", "result", "duplicate_table"),
        ("Overall prose Gamma", "QuantEvolver IC", 0.1502, "IC", "result", "duplicate_table"),
        ("Ablation prose", "without diversity RankIC", 0.0505, "RankIC", "result", "duplicate_table"),
        ("Ablation prose", "without seed RankIC", 0.0519, "RankIC", "result", "duplicate_table"),
        ("Ablation prose", "without seed and diversity RankIC", 0.0540, "RankIC", "result", "duplicate_table"),
        ("Ablation prose", "without DSL RankIC", 0.0002, "RankIC", "result", "duplicate_table"),
        ("Ablation prose", "without DSL ICIR", 0.2506, "ICIR", "result", "duplicate_table"),
        ("Top-k sensitivity", "lower stated small-k setting", 3, "factors", "configuration", "exact"),
        ("Top-k sensitivity", "small-k upper setting", 5, "factors", "configuration", "exact"),
        ("Top-k sensitivity", "RankIC around k=3--5", 0.050, "RankIC", "result", "approximate"),
        ("Top-k sensitivity", "RankIC at k=5", 0.0498, "RankIC", "result", "exact"),
        ("Top-k sensitivity", "RankIC at k=10", 0.0530, "RankIC", "result", "exact"),
        ("Top-k sensitivity", "RankIC at k=20", 0.0562, "RankIC", "result", "exact"),
        ("Top-k sensitivity", "RankIC at k=25", 0.0587, "RankIC", "result", "exact"),
        ("Top-k sensitivity", "RankIC at k=30", 0.0586, "RankIC", "result", "exact"),
        ("Correlation sensitivity", "strict correlation threshold", 0.50, "correlation", "configuration", "exact"),
        ("Correlation sensitivity", "RankIC at threshold 0.50", 0.0620, "RankIC", "result", "exact"),
        ("Correlation sensitivity", "next correlation threshold", 0.60, "correlation", "configuration", "exact"),
        ("Correlation sensitivity", "RankIC at threshold 0.60", 0.0601, "RankIC", "result", "exact"),
        ("Correlation sensitivity", "looser-threshold RankIC range low", 0.052, "RankIC", "result", "approximate"),
        ("Correlation sensitivity", "looser-threshold RankIC range high", 0.054, "RankIC", "result", "approximate"),
        ("Profitability case", "starting NAV normalization", 1.00, "NAV", "configuration", "exact"),
        ("Profitability case", "QuantEvolver ending NAV", 2.26, "NAV", "result", "approximate"),
        ("Profitability case", "QuantEvolver cumulative return", 125.6, "pct", "result", "approximate"),
        ("Profitability case", "Alpha158 ending NAV", 1.85, "NAV", "result", "approximate"),
        ("Profitability case", "Alpha101 ending NAV", 1.37, "NAV", "result", "approximate"),
    ]
    rows = []
    for location, claim, value, unit, role, precision in raw:
        rows.append(
            {
                "paper_location": location,
                "claim": claim,
                "paper_value": value,
                "unit": unit,
                "claim_role": role,
                "precision": precision,
                "native_reproduced_value": "",
                "status": (
                    "configuration_not_recreated"
                    if role == "configuration"
                    else "unavailable_missing_native_paper_result_path"
                ),
                "paper_result_credit": False,
            }
        )
    if len(rows) != 42 or Counter(row["claim_role"] for row in rows) != {
        "result": 31,
        "configuration": 11,
    }:
        raise RuntimeError("QuantEvolver non-table claim denominator changed")
    return rows


def internal_consistency_checks() -> List[Dict[str, Any]]:
    a_relative = (53.22 - 52.59) / 52.59 * 100.0
    b_relative = (0.0586 - 0.0337) / 0.0337 * 100.0
    implied_nav = 1.0 + 1.256
    return [
        {
            "check": "Benchmark A improvement claim versus Table Overall",
            "paper_claim": 7.8,
            "recomputed_value": a_relative,
            "status": "not_derivable_from_displayed_table_values",
            "evidence": "Table values 53.22% and 52.59% imply about 1.20% relative improvement",
        },
        {
            "check": "Benchmark B best-RankIC improvement claim versus Table Overall",
            "paper_claim": 109.5,
            "recomputed_value": b_relative,
            "status": "not_derivable_from_displayed_table_values",
            "evidence": "Table values 0.0586 and 0.0337 imply about 73.89% relative improvement",
        },
        {
            "check": "top-10 RankIC-mean improvement",
            "paper_claim": 186.9,
            "recomputed_value": "",
            "status": "not_auditable_underlying_values_absent",
            "evidence": "No top-10 method means or numeric plot array is supplied",
        },
        {
            "check": "Miner/backbone model identity",
            "paper_claim": "Qwen3-14B and all methods use Qwen-3.6-Plus",
            "recomputed_value": "",
            "status": "paper_internal_configuration_conflict",
            "evidence": "Experimental Setup names Qwen3-14B, then Compared Approaches says all methods use Qwen-3.6-Plus",
        },
        {
            "check": "Benchmark A IC/RankIC definitions",
            "paper_claim": "single asset evaluated with cross-sectional IC and RankIC equations",
            "recomputed_value": "undefined when N_t=1",
            "status": "paper_metric_definition_incomplete",
            "evidence": "Published equations correlate across assets i=1..N_t, but Benchmark A has one asset",
        },
        {
            "check": "published ICIR versus released cross-sectional evaluator",
            "paper_claim": "mean(IC_t)/(std(IC_t)+epsilon)",
            "recomputed_value": "released source multiplies by sqrt(number of valid times)",
            "status": "paper_source_metric_conflict",
            "evidence": "cross_sectional_rankic.py computes mean_ric/std_ric*sqrt(len(arr))",
        },
        {
            "check": "published predictive reward versus released cross-sectional reward",
            "paper_claim": "g(e) extracts the primary metric",
            "recomputed_value": "clip(5*mean_RankIC + 0.02*tanh(ICIR), -1, 1)",
            "status": "paper_source_reward_transform_not_disclosed",
            "evidence": "released evaluator transforms RankIC and source-defined ICIR before DiCo shaping",
        },
        {
            "check": "profitability return and rounded ending NAV",
            "paper_claim": 2.26,
            "recomputed_value": implied_nav,
            "status": "compatible_at_display_precision",
            "evidence": "125.6% from NAV 1 implies 2.256, which rounds to 2.26",
        },
        {
            "check": "equity benchmark identity",
            "paper_claim": "daily market data of CSI 300 ETF constituents",
            "recomputed_value": "",
            "status": "paper_universe_ambiguous",
            "evidence": "The manuscript does not identify whether this means CSI 300 index constituents or multiple ETF products",
        },
    ]


def specification_gaps() -> List[Dict[str, str]]:
    gaps = [
        ("data", "Benchmark A asset identity"),
        ("data", "Benchmark A venue/vendor and immutable snapshot"),
        ("data", "Benchmark A train/validation/test dates and sample counts"),
        ("data", "Benchmark A timezone, session, and 5-minute bar alignment"),
        ("data", "Benchmark B exchange identity and immutable data snapshot"),
        ("data", "Benchmark B asset universe and eligibility/liquidity rule"),
        ("data", "Benchmark B full train/validation/test dates"),
        ("data", "Benchmark B delisting, missing-bar, and survivorship treatment"),
        ("data", "Benchmark B bar construction, target horizon, and timestamp convention"),
        ("data", "Benchmark Gamma exact security universe and ETF/index interpretation"),
        ("data", "Benchmark Gamma vendor, snapshot, corporate-action treatment, and dates"),
        ("model", "unambiguous Miner model/checkpoint identity"),
        ("model", "oracle LLM identity, version, decoding parameters, and prompt"),
        ("model", "baseline model endpoints/snapshots and decoding parameters"),
        ("search", "paper seed candidates, scores, thresholds, and selected pool"),
        ("search", "paper task bank, time windows, families, and mutation hints"),
        ("training", "GRPO group size, epochs/steps, batch sizes, optimizer, and learning rate"),
        ("training", "reward coefficients, clipping bounds, quality/coverage thresholds"),
        ("training", "random seeds, number of runs, checkpoint-selection rule"),
        ("training", "trained checkpoint and training/validation trajectories"),
        ("factor", "mined factor expressions, scores, profiles, and archive history"),
        ("fusion", "candidate count, validation ranking, top-k default, and tie handling"),
        ("fusion", "decorrelation statistic/sample, greedy order, and exact threshold application"),
        ("fusion", "equal-weight fusion normalization and missing-value handling"),
        ("baseline", "AlphaBench exact implementation/configuration and mining budget"),
        ("baseline", "QuantaAlpha exact implementation/configuration and mining budget"),
        ("baseline", "R&D-Agent adaptation implementation/configuration and mining budget"),
        ("baseline", "Alpha-Jungle implementation/configuration and mining budget"),
        ("metrics", "single-asset IC/RankIC/ICIR definitions"),
        ("metrics", "ICIR annualization/scaling convention"),
        ("portfolio", "long/short selection fraction, weights, leverage, and rebalance timing"),
        ("portfolio", "transaction costs, slippage, fees, funding, and borrow assumptions"),
        ("portfolio", "daily/hourly holdings, returns, NAVs, and figure source arrays"),
        ("statistics", "uncertainty estimates, trial dispersion, and significance tests"),
        ("cost", "LLM token, API, compute-time, and monetary cost ledger"),
    ]
    return [
        {
            "category": category,
            "missing_specification_or_artifact": item,
            "paper_result_impact": "blocks_exact_native_reproduction",
        }
        for category, item in gaps
    ]


def mechanism_conformance(source_root: Path) -> List[Dict[str, Any]]:
    entries = [
        ("scenario_refinement", "exact_or_direct_match", "scenarios/refiner.py and schema.py implement structured LLM refinement"),
        ("oracle_seed_generation", "exact_or_direct_match", "seeds/generator.py calls a configurable strong model"),
        ("seed_dsl_validation", "exact_or_direct_match", "SeedValidator compiles and constrains expressions"),
        ("seed_empirical_scoring", "exact_or_direct_match", "SeedEvaluator and SeedScorer expose executable scoring"),
        ("canonical_expression_deduplication", "exact_or_direct_match", "AST canonical hashes are used for deduplication"),
        ("topk_seed_curation", "exact_or_direct_match", "SeedLibraryBuilder selects score-ranked seed subsets"),
        ("seed_time_window_cartesian_task_bank", "exact_or_direct_match", "TaskBankBuilder expands each selected seed across time splits"),
        ("task_seed_expression", "exact_or_direct_match", "TaskSpec stores seed_id and seed_expr"),
        ("task_structured_scenario", "exact_or_direct_match", "TaskSpec stores scenario text"),
        ("task_evaluation_window", "exact_or_direct_match", "TaskSpec stores split start/end"),
        ("task_factor_family", "exact_or_direct_match", "TaskSpec stores family"),
        ("task_mutation_hints", "exact_or_direct_match", "TaskSpec stores mutation_hints"),
        ("factor_dsl_parser_and_type_checks", "exact_or_direct_match", "DSL compiler/evaluator implement a constrained expression language"),
        ("factor_realizer", "exact_or_direct_match", "compile_expr emits executable Backtrader code"),
        ("single_asset_executable_evaluator", "exact_or_direct_match", "backtrader_signal and reward profiles implement single-asset evaluation"),
        ("cross_sectional_executable_evaluator", "exact_or_direct_match", "cross_sectional_rankic evaluates symbols at common timestamps"),
        ("invalid_expression_low_reward", "exact_or_direct_match", "format/runtime failures receive -1"),
        ("verl_training_integration", "exact_or_direct_match", "verl_main constructs and runs RayPPOTrainer"),
        ("grpo_advantage_estimator", "exact_or_direct_match", "build_verl_config sets adv_estimator=grpo"),
        ("grouped_rollouts", "exact_or_direct_match", "rollout n is configurable and passed to Verl"),
        ("policy_parameter_updates", "substantial_analogue", "trainer.fit is wired, but paper checkpoint/config/training execution is absent"),
        ("exact_repeat_penalty", "exact_or_direct_match", "NoveltyArchive applies an exact-expression repeat penalty"),
        ("structural_family_signature", "exact_or_direct_match", "FamilyArchive canonicalizes structural templates"),
        ("new_family_bonus", "exact_or_direct_match", "good unseen families receive a configurable bonus"),
        ("overused_low_quality_family_penalty", "exact_or_direct_match", "low-quality families beyond a quota are penalized"),
        ("single_asset_behavior_complementarity", "substantial_analogue", "ResidualResponseArchive implements a residual/correlation analogue"),
        ("cross_sectional_behavior_profiles", "exact_or_direct_match", "CrossSectionalBehaviorArchive stores rank-vector profiles"),
        ("low_behavior_correlation_bonus", "exact_or_direct_match", "low-correlation cross-sectional candidates can receive a bonus"),
        ("high_behavior_correlation_penalty", "exact_or_direct_match", "high-correlation candidates receive a linear penalty"),
        ("final_reward_clipping", "exact_or_direct_match", "training score is clipped to [-1,1]"),
        ("quality_and_coverage_archive_gate", "exact_or_direct_match", "positive factor files require metric and coverage thresholds"),
        ("expression_level_output_deduplication", "exact_or_direct_match", ".seen markers prevent duplicate saved expressions"),
        ("mined_factor_database", "substantial_analogue", "separate output and JSONL archives approximate but do not reproduce the paper database"),
        ("final_factor_library", "substantial_analogue", "generated factor files form an output library without paper metadata or contents"),
        ("dsl_free_ablation_path", "exact_or_direct_match", "free_code mode evaluates generated Backtrader factor code"),
        ("DirAcc_definition", "exact_or_direct_match", "direction reward compares factor and future-return signs"),
        ("RankIC_definition", "exact_or_direct_match", "cross-sectional evaluator uses per-time Spearman correlation"),
        ("IC_definition_cross_sectional", "absent", "released cross-sectional evaluator does not report paper-defined Pearson IC"),
        ("ICIR_definition", "conflict", "source multiplies mean/std by sqrt(T), unlike the paper equation"),
        ("predictive_reward_primary_metric", "conflict", "source transforms RankIC with factor 5 and a tanh(ICIR) term"),
        ("paper_Qwen3_14B_checkpoint", "absent", "public config contains path/to/base-model"),
        ("paper_Qwen_3_6_Plus_backbone", "absent", "no paper baseline endpoint or model snapshot is configured"),
        ("paper_oracle_model", "absent", "no paper oracle identity or snapshot is released"),
        ("paper_prompt_pack", "absent", "generic prompts are released, not the paper prompts or prompt hashes"),
        ("paper_seed_pool", "absent", "three illustrative valid seeds are not the paper's selected seed pool"),
        ("paper_task_bank", "absent", "example January 2024 windows are not any disclosed paper task bank"),
        ("paper_RFT_hyperparameters", "absent", "generic one-GPU example is not the eight-H20 experiment config"),
        ("paper_random_seeds_and_trials", "absent", "no experiment seed/trial ledger is released"),
        ("paper_trained_checkpoint", "absent", "README explicitly excludes trained checkpoints"),
        ("paper_training_logs", "absent", "README explicitly excludes experiment logs"),
        ("paper_mined_factor_library", "absent", "no factors underlying reported results are shipped"),
        ("Benchmark_A_data_and_config", "absent", "asset, data, dates, split, and native config are missing"),
        ("Benchmark_B_data_and_config", "absent", "exchange, symbols, data, dates, split, and native config are missing"),
        ("Benchmark_Gamma_data_and_config", "absent", "equity universe, data, dates, split, and native config are missing"),
        ("paper_post_selection_ranking", "absent", "no paper candidate-result array or selection runner is shipped"),
        ("paper_decorrelation_filter", "absent", "no paper 0.7 correlation-selection implementation is shipped"),
        ("paper_equal_weight_fusion", "absent", "no paper fused-signal implementation/output is shipped"),
        ("AlphaBench_baseline", "absent", "baseline implementation/config/output is missing"),
        ("QuantaAlpha_baseline", "absent", "baseline implementation/config/output is missing"),
        ("RD_Agent_adaptation", "absent", "adapted baseline implementation/config/output is missing"),
        ("Alpha_Jungle_baseline", "absent", "baseline implementation/config/output is missing"),
        ("profitability_portfolio_protocol", "substantial_analogue", "source computes an equal-mean top/bottom quintile diagnostic, not the paper portfolio"),
        ("paper_transaction_costs_and_execution", "absent", "fees, slippage, funding, borrow, orders, and fills are absent"),
        ("paper_result_tables", "absent", "no table-generating outputs or reproduction scripts are released"),
        ("paper_result_figure_arrays", "absent", "vector plots are in arXiv source but numeric arrays are absent"),
        ("paper_compute_environment", "unverifiable", "hardware is stated in paper but no environment/container/lockfile records it"),
        ("dependency_lock_and_training_stack", "unverifiable", "minimum dependency ranges and external Verl setup are not frozen"),
    ]
    rows = []
    credit_status = {"exact_or_direct_match", "substantial_analogue"}
    for dimension, status, evidence in entries:
        rows.append(
            {
                "dimension": dimension,
                "status": status,
                "source_evidence": evidence,
                "paper_mechanism_credit": status in credit_status,
                "paper_result_credit": False,
            }
        )
    if len(rows) != 67 or len({row["dimension"] for row in rows}) != len(rows):
        raise RuntimeError("QuantEvolver mechanism census changed")
    return rows


def source_inventory(source_root: Path) -> List[Dict[str, Any]]:
    listing = str(run_git(source_root, "ls-tree", "-r", "-l", SOURCE_COMMIT))
    rows = []
    for line in listing.splitlines():
        metadata, relative = line.split("\t", 1)
        _mode, _kind, object_hash, size_text = metadata.split()
        rows.append(
            {
                "path": relative,
                "git_object": object_hash,
                "bytes": int(size_text),
                "sha256": sha256_bytes(git_blob(source_root, relative)),
                "python_source": relative.endswith(".py"),
                "upstream_test": relative.startswith("tests/") and relative.endswith(".py"),
                "paper_numeric_output": False,
            }
        )
    return rows


def source_history_inventory(source_root: Path) -> List[Dict[str, Any]]:
    """Inventory every reachable revision for latent paper-result artifacts."""
    if str(run_git(source_root, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise RuntimeError("QuantEvolver source history is shallow; fetch it before auditing")
    commits = str(
        run_git(source_root, "rev-list", "--reverse", "refs/remotes/origin/main")
    ).splitlines()
    if commits != [README_ONLY_COMMIT, SOURCE_COMMIT]:
        raise RuntimeError(f"QuantEvolver reachable public history changed: {commits}")

    rows: List[Dict[str, Any]] = []
    for commit in commits:
        authored_at, subject = str(
            run_git(source_root, "show", "-s", "--format=%aI%x09%s", commit)
        ).rstrip("\n").split("\t", 1)
        paths = str(run_git(source_root, "ls-tree", "-r", "--name-only", commit)).splitlines()
        artifact_paths = [
            path
            for path in paths
            if path.lower().endswith(RESULT_ARTIFACT_SUFFIXES)
            or any(part in RESULT_PATH_PARTS for part in path.lower().split("/"))
        ]
        literal_hits: List[str] = []
        for path in paths:
            if path == "paper/QuantEvolver.pdf" or path.lower().endswith((".pdf", ".png")):
                continue
            payload = run_git(source_root, "show", f"{commit}:{path}", binary=True)
            text = payload.decode("utf-8", errors="ignore")
            for literal in PAPER_RESULT_LITERALS:
                if literal in text:
                    literal_hits.append(f"{path}:{literal}")
        rows.append(
            {
                "commit": commit,
                "authored_at": authored_at,
                "subject": subject,
                "tracked_paths": len(paths),
                "python_paths": sum(path.endswith(".py") for path in paths),
                "result_or_data_artifact_paths": len(artifact_paths),
                "result_or_data_artifact_inventory": ";".join(artifact_paths),
                "paper_result_literal_hits_outside_bundled_pdf": len(literal_hits),
                "paper_result_literal_inventory": ";".join(literal_hits),
                "paper_result_artifact_found": False,
            }
        )
    if any(
        row["result_or_data_artifact_paths"]
        or row["paper_result_literal_hits_outside_bundled_pdf"]
        for row in rows
    ):
        raise RuntimeError("QuantEvolver history unexpectedly contains a latent result artifact")
    return rows


def public_fork_audit(
    source_root: Path,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Exhaust every current public fork ref and require exact official-head identity."""
    actual_refs = {}
    for line in str(
        run_git(
            source_root,
            "for-each-ref",
            "--format=%(refname)%09%(objectname)",
            "refs/remotes/forks",
        )
    ).splitlines():
        refname, head = line.split("\t")
        actual_refs[refname] = head
    expected_refs = {
        f"refs/remotes/forks/{repository.split('/', 1)[0]}/main": SOURCE_COMMIT
        for repository in PUBLIC_FORK_REPOSITORIES
    }
    if actual_refs != expected_refs:
        raise RuntimeError(f"QuantEvolver public-fork branch refs changed: {actual_refs}")
    if str(
        run_git(source_root, "for-each-ref", "--format=%(refname)", "refs/tags")
    ).strip():
        raise RuntimeError("QuantEvolver public-fork checkout unexpectedly contains tags")
    official = str(run_git(source_root, "rev-parse", "refs/remotes/origin/main")).strip()
    if official != SOURCE_COMMIT:
        raise RuntimeError("QuantEvolver official remote head changed")

    branch_rows: List[Dict[str, Any]] = []
    for repository in PUBLIC_FORK_REPOSITORIES:
        owner = repository.split("/", 1)[0]
        head = actual_refs[f"refs/remotes/forks/{owner}/main"]
        behind, ahead = map(
            int,
            str(
                run_git(
                    source_root,
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"{official}...{head}",
                )
            ).split(),
        )
        if (ahead, behind) != (0, 0):
            raise RuntimeError(f"QuantEvolver fork no longer matches official head: {repository}")
        if str(
            run_git(
                source_root,
                "rev-list",
                head,
                "--not",
                "refs/remotes/origin/main",
            )
        ).strip():
            raise RuntimeError(f"QuantEvolver fork adds unreviewed commits: {repository}")
        branch_rows.append(
            {
                "repository": repository,
                "url": f"https://github.com/{repository}",
                "branch": "main",
                "head_commit": head,
                "relation_to_official_head": "official_head_exact",
                "commits_ahead_of_official": ahead,
                "commits_behind_official": behind,
                "tag_refs": 0,
                "unique_commits_beyond_official_history": 0,
                "unique_blobs_beyond_official_history": 0,
                "native_result_artifact_found": False,
                "paper_result_credit": False,
            }
        )
    unique_rows = [
        {
            "head_commit": SOURCE_COMMIT,
            "repositories": ";".join(sorted(PUBLIC_FORK_REPOSITORIES)),
            "branch_ref_count": len(branch_rows),
            "official_head_exact": True,
            "unique_commits_beyond_official_history": 0,
            "unique_blobs_beyond_official_history": 0,
            "native_result_artifact_found": False,
            "paper_result_credit": False,
        }
    ]
    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": PUBLIC_FORK_COUNT,
        "accessible_public_forks": len(branch_rows),
        "accessible_branch_refs": len(branch_rows),
        "tag_refs": PUBLIC_FORK_TAG_REF_COUNT,
        "unique_heads": len(unique_rows),
        "official_head_exact_unique_heads": len(unique_rows),
        "divergent_unique_heads": 0,
        "unique_commits_beyond_official_history": 0,
        "unique_blobs_beyond_official_history": 0,
        "native_result_artifacts_found": 0,
        "paper_result_credit": False,
        "interpretation": (
            "all four accessible public forks and all four branch refs resolve exactly "
            "to the audited official head; they add no code, data, checkpoint, factor, "
            "prediction, return, log, training, or paper-result lineage"
        ),
    }
    return branch_rows, unique_rows, summary


def paper_source_inventory(paper_source_root: Path) -> List[Dict[str, Any]]:
    numeric = set(PINNED_PAPER_SOURCE_SHA256) - {"bare_jrnl_new_sample4.tex"}
    rows = []
    for path in sorted(item for item in paper_source_root.rglob("*") if item.is_file()):
        relative = path.relative_to(paper_source_root).as_posix()
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "asset_role": "numeric_result_figure" if relative in numeric else "paper_source_or_nonnumeric_figure",
                "underlying_numeric_array_shipped": False,
            }
        )
    return rows


def run_checked(command: Sequence[str], cwd: Path, env: Mapping[str, str], timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        env=dict(env),
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


REAL_ENV_DRIVER = r"""
import hashlib
import httpx
import importlib
import importlib.metadata
import importlib.util
import json
import ray
import requests
import tempfile
import torch
from pathlib import Path

import pandas as pd

network_attempts = []

def block_sync_httpx(self, request, *args, **kwargs):
    network_attempts.append(f"httpx:{request.method}:{request.url}")
    raise RuntimeError("network disabled during QuantEvolver environment audit")

async def block_async_httpx(self, request, *args, **kwargs):
    network_attempts.append(f"httpx-async:{request.method}:{request.url}")
    raise RuntimeError("network disabled during QuantEvolver environment audit")

def block_requests(self, request, *args, **kwargs):
    network_attempts.append(f"requests:{request.method}:{request.url}")
    raise RuntimeError("network disabled during QuantEvolver environment audit")

httpx.Client.send = block_sync_httpx
httpx.AsyncClient.send = block_async_httpx
requests.sessions.Session.send = block_requests

module_names = []
for path in sorted(Path("quant_evolver").rglob("*.py")):
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    name = ".".join(parts)
    if name and name not in module_names:
        module_names.append(name)
for name in module_names:
    importlib.import_module(name)

from quant_evolver.rft.config import RFTConfig
from quant_evolver.rft.no_think_dataset import NoThinkRLHFDataset
from quant_evolver.rft.task_bank import (
    TaskBankBuilder,
    TaskBuildConfig,
    save_task_bank,
)
from quant_evolver.rft.verl_main import build_verl_config
from quant_evolver.seeds.library import load_seed_candidates
from quant_evolver.seeds.pipeline import SeedPipeline
from quant_evolver.utils.config import load_config
from verl.utils.dataset.rl_dataset import RLHFDataset

with tempfile.TemporaryDirectory(prefix="quantevolver-rft-audit-") as temporary:
    root = Path(temporary)
    seeds = load_seed_candidates("examples/seed_candidates.yaml")
    evaluations = SeedPipeline().run_static(seeds)
    task_cfg = TaskBuildConfig.from_dict(
        load_config("configs/example_seed_pipeline.yaml")["task_bank"]
    )
    bank = TaskBankBuilder(task_cfg).build_from_seed_evaluations(evaluations)
    task_path = root / "task_bank.yaml"
    save_task_bank(bank, task_path)
    raw = load_config("configs/example_rft_pure_verl.yaml")["rft"]
    raw.update(
        {
            "run_root": str(root / "run"),
            "output_dir": str(root / "factors"),
            "task_bank_path": str(task_path),
        }
    )
    rft = RFTConfig.from_dict(raw)
    cfg = build_verl_config(rft)
    train = pd.read_parquet(cfg.data.train_files[0])
    validation = pd.read_parquet(cfg.data.val_files[0])

package_names = [
    "backtrader",
    "numpy",
    "omegaconf",
    "pandas",
    "pyarrow",
    "pytest",
    "PyYAML",
    "quant-evolver",
    "ray",
    "ruff",
    "scipy",
    "tensordict",
    "torch",
    "transformers",
    "verl",
]
packages = {name: importlib.metadata.version(name) for name in package_names}
result = {
    "imported_source_modules": len(module_names),
    "imported_module_names": module_names,
    "resolved_packages": packages,
    "torch_cuda_available": torch.cuda.is_available(),
    "ray_initialized": ray.is_initialized(),
    "vllm_installed": importlib.util.find_spec("vllm") is not None,
    "verl_dataset_subclass": issubclass(NoThinkRLHFDataset, RLHFDataset),
    "seed_candidates": len(seeds),
    "valid_seed_candidates": sum(item.valid for item in evaluations),
    "task_bank_tasks": len(bank.tasks),
    "train_prompt_rows": len(train),
    "validation_prompt_rows": len(validation),
    "train_data_sources": sorted(train["data_source"].unique()),
    "validation_data_sources": sorted(validation["data_source"].unique()),
    "advantage_estimator": cfg.algorithm.adv_estimator,
    "rollout_backend": cfg.actor_rollout_ref.rollout.name,
    "network_attempts": network_attempts,
}
print(json.dumps(result, sort_keys=True))
"""


def native_component_checks(source_root: Path, source_python: Path) -> Dict[str, Any]:
    if not source_python.is_file():
        raise FileNotFoundError(source_python)
    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)
    env = dict(clean_env)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(source_root)
    pip_check = run_checked(
        [str(source_python), "-m", "pip", "check"], source_root, clean_env
    )
    freeze = run_checked(
        [str(source_python), "-m", "pip", "freeze", "--all"],
        source_root,
        clean_env,
    ).stdout
    freeze_sha256 = sha256_bytes(freeze.encode())
    if freeze_sha256 != RECONSTRUCTED_ENV_FREEZE_SHA256:
        raise RuntimeError(
            "QuantEvolver reconstructed environment changed: "
            f"{freeze_sha256} != {RECONSTRUCTED_ENV_FREEZE_SHA256}"
        )
    version = run_checked([str(source_python), "--version"], source_root, env).stdout.strip()
    if not version:
        version = run_checked([str(source_python), "--version"], source_root, env).stderr.strip()

    compile_code = """
import json
from pathlib import Path
root = Path('.')
files = sorted(root.glob('quant_evolver/**/*.py')) + sorted(root.glob('tests/*.py'))
for path in files:
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
print(json.dumps({'compiled': len(files)}))
"""
    compiled = json.loads(run_checked([str(source_python), "-c", compile_code], source_root, env).stdout.splitlines()[-1])
    tests = run_checked(
        [str(source_python), "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        source_root,
        env,
    )
    tests_passed = "3 passed" in tests.stdout

    smoke_code = """
import json
import numpy as np
import pandas as pd
from quant_evolver.dsl.evaluator import evaluate_expr_series
from quant_evolver.rft.task_bank import TaskBankBuilder, TaskBuildConfig
from quant_evolver.seeds.library import load_seed_candidates
from quant_evolver.seeds.pipeline import SeedPipeline
from quant_evolver.utils.config import load_config

seeds = load_seed_candidates('examples/seed_candidates.yaml')
evaluations = SeedPipeline().run_static(seeds)
cfg = TaskBuildConfig.from_dict(load_config('configs/example_seed_pipeline.yaml')['task_bank'])
bank = TaskBankBuilder(cfg).build_from_seed_evaluations(evaluations)
idx = pd.date_range('2024-01-01', periods=320, freq='5min')
x = np.arange(len(idx), dtype=float)
bars = pd.DataFrame({
    'open': 100 + .01*x + np.sin(x/17),
    'high': 100.2 + .01*x + np.sin(x/17),
    'low': 99.8 + .01*x + np.sin(x/17),
    'close': 100 + .01*x + np.sin(x/17),
    'volume': 1000 + 2*x + 10*np.cos(x/13),
}, index=idx)
values = {}
for ev in evaluations:
    if not ev.valid:
        continue
    first = evaluate_expr_series(ev.seed.expr, bars, warmup_bars=240).dropna()
    second = evaluate_expr_series(ev.seed.expr, bars, warmup_bars=240).dropna()
    values[ev.seed.id] = {
        'observations': len(first),
        'last_value': float(first.iloc[-1]),
        'deterministic': bool(np.array_equal(first.to_numpy(), second.to_numpy())),
    }
print(json.dumps({
    'seed_candidates': len(seeds),
    'valid_seeds': sum(ev.valid for ev in evaluations),
    'invalid_seeds': sum(not ev.valid for ev in evaluations),
    'example_task_bank_tasks': len(bank.tasks),
    'dsl_values': values,
}))
"""
    smoke = json.loads(run_checked([str(source_python), "-c", smoke_code], source_root, env).stdout.splitlines()[-1])
    real_outputs = []
    for _ in range(2):
        run = run_checked(
            [str(source_python), "-c", REAL_ENV_DRIVER],
            source_root,
            env,
        )
        real_outputs.append(json.loads(run.stdout.splitlines()[-1]))
    if real_outputs[0] != real_outputs[1]:
        raise RuntimeError("QuantEvolver dependency-backed component is nondeterministic")
    real = real_outputs[0]
    expected_real = {
        "imported_source_modules": 52,
        "torch_cuda_available": False,
        "ray_initialized": False,
        "vllm_installed": False,
        "verl_dataset_subclass": True,
        "seed_candidates": 4,
        "valid_seed_candidates": 3,
        "task_bank_tasks": 9,
        "train_prompt_rows": 16,
        "validation_prompt_rows": 4,
        "advantage_estimator": "grpo",
        "rollout_backend": "vllm",
        "network_attempts": [],
    }
    for key, value in expected_real.items():
        if real[key] != value:
            raise RuntimeError(
                f"QuantEvolver dependency-backed component changed for {key}: "
                f"{real[key]!r}"
            )
    real_normalized = json.dumps(real, sort_keys=True, separators=(",", ":")).encode()
    return {
        "source_python": version,
        "tracked_python_files_compiled": compiled["compiled"],
        "compile_status": "passed_in_reconstructed_declared_environment",
        "upstream_tests_shipped": 3,
        "upstream_tests_status": "passed" if tests_passed else "unexpected_output",
        "upstream_test_summary": "3 passed" if tests_passed else "unexpected pytest output",
        "pip_check": pip_check.stdout.strip(),
        "dependency_environment_reproduced": True,
        "declared_all_environment_reconstructed": True,
        "compatible_verl_environment_reconstructed": True,
        "exact_historical_dependency_versions_recovered": False,
        "full_gpu_training_environment_reproduced": False,
        "verl_selection_boundary": "verl 0.5.0 is a compatibility selection for the released API/config shape; QuantEvolver does not pin Verl or vLLM",
        "dependency_freeze_sha256": freeze_sha256,
        "dependency_freeze_lines": len(freeze.splitlines()),
        "_dependency_freeze_text": freeze,
        "public_quickstart_component": smoke,
        "real_dependency_component": real,
        "real_dependency_component_sha256": sha256_bytes(real_normalized),
        "deterministic_released_seed_dsl_components": all(
            item["deterministic"] for item in smoke["dsl_values"].values()
        ),
        "paper_data_used": False,
        "llm_or_market_api_called": False,
        "verl_training_executed": False,
        "paper_result_reproduction": False,
    }


def component_gate_summary(component_root: Path) -> Dict[str, Any]:
    for relative, expected in COMPONENT_GATE_SHA256.items():
        observed = sha256(component_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned component-gate hash changed for {relative}: {observed}")
    manifest = json.loads((component_root / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise RuntimeError("Component gate uses a different QuantEvolver source commit")
    return {
        "status": "passed_separate_grade_B_disclosed_component_gate",
        "counted_components": manifest["n_counted_components"],
        "grade_a_or_b": manifest["n_grade_a_or_b"],
        "pass_rate": manifest["faithfulness_pass_rate"],
        "technical_reference_conformance_passed": manifest["technical_reference_conformance_passed"],
        "cadence_adapted": "released bars to monthly JKP bars",
        "universe_adapted": "released configured symbols to top-1000 U.S. equities",
        "native_agent_replication": False,
        "search_or_RFT_replication": False,
        "paper_result_reproduction": False,
        "scope_warning": manifest["scope_warning"],
        "pinned_sha256": COMPONENT_GATE_SHA256,
    }


def verify_pins(source_root: Path, paper_pdf: Path, paper_source_archive: Path, paper_source_root: Path) -> None:
    if sha256(paper_pdf) != PAPER_SHA256:
        raise RuntimeError("Pinned arXiv PDF hash changed")
    if sha256(paper_source_archive) != PAPER_SOURCE_SHA256:
        raise RuntimeError("Pinned arXiv source archive hash changed")
    if str(run_git(source_root, "rev-parse", "HEAD")).strip() != SOURCE_COMMIT:
        raise RuntimeError("Official source checkout is not at the pinned commit")
    commits = str(run_git(source_root, "rev-list", "--reverse", "HEAD")).splitlines()
    if commits != [README_ONLY_COMMIT, SOURCE_COMMIT]:
        raise RuntimeError(f"Official source history changed: {commits}")
    first_tree = str(run_git(source_root, "ls-tree", "-r", "--name-only", README_ONLY_COMMIT)).splitlines()
    if first_tree != ["README.md"]:
        raise RuntimeError(f"README-only first commit changed: {first_tree}")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        observed = sha256_bytes(git_blob(source_root, relative))
        if observed != expected:
            raise RuntimeError(f"Pinned source hash changed for {relative}: {observed}")
    for relative, expected in PINNED_PAPER_SOURCE_SHA256.items():
        observed = sha256(paper_source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned paper-source hash changed for {relative}: {observed}")


def build_audit(
    source_root: Path,
    paper_pdf: Path,
    paper_source_archive: Path,
    paper_source_root: Path,
    source_python: Path,
    component_root: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    verify_pins(source_root, paper_pdf, paper_source_archive, paper_source_root)
    table = paper_table_rows()
    ablation = ablation_design_rows()
    claims = published_non_table_claims()
    checks = internal_consistency_checks()
    gaps = specification_gaps()
    mechanisms = mechanism_conformance(source_root)
    inventory = source_inventory(source_root)
    history = source_history_inventory(source_root)
    fork_branches, fork_heads, fork_summary = public_fork_audit(source_root)
    paper_assets = paper_source_inventory(paper_source_root)
    native = native_component_checks(source_root, source_python)
    dependency_freeze = native.pop("_dependency_freeze_text")
    component = component_gate_summary(component_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "paper_numeric_table_conformance.csv", table)
    write_csv(output_dir / "ablation_design_cells.csv", ablation)
    write_csv(output_dir / "published_non_table_claims.csv", claims)
    write_csv(output_dir / "paper_internal_and_source_checks.csv", checks)
    write_csv(output_dir / "paper_specification_gaps.csv", gaps)
    write_csv(output_dir / "source_mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "released_source_inventory.csv", inventory)
    write_csv(output_dir / "released_source_history_inventory.csv", history)
    write_csv(output_dir / "public_fork_branch_ref_snapshot.csv", fork_branches)
    write_csv(output_dir / "public_fork_unique_head_inventory.csv", fork_heads)
    (output_dir / "public_fork_census.json").write_text(
        json.dumps(fork_summary, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(output_dir / "paper_source_asset_inventory.csv", paper_assets)
    (output_dir / "native_component_execution.json").write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")
    (output_dir / "reconstructed_environment_freeze.txt").write_text(
        dependency_freeze, encoding="utf-8"
    )
    (output_dir / "separate_component_gate.json").write_text(json.dumps(component, indent=2) + "\n", encoding="utf-8")

    status_counts = Counter(row["status"] for row in mechanisms)
    mechanism_credit = sum(bool(row["paper_mechanism_credit"]) for row in mechanisms)
    result_claims = [row for row in claims if row["claim_role"] == "result"]
    manifest: Dict[str, Any] = {
        "audit": "QuantEvolver arXiv v1 versus official source released minutes before submission",
        "overall_status": "not_reproduced_substantial_public_framework_zero_paper_results",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": PAPER_VERSION,
        "paper_date": PAPER_DATE,
        "paper_sha256": PAPER_SHA256,
        "paper_source_sha256": PAPER_SOURCE_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": SOURCE_COMMIT,
        "source_commit_date": SOURCE_COMMIT_DATE,
        "readme_only_commit": README_ONLY_COMMIT,
        "readme_only_commit_date": README_ONLY_COMMIT_DATE,
        "source_release_before_submission_minutes": 16.2333,
        "source_history_commits": 2,
        "source_history_commits_audited": len(history),
        "source_history_result_or_data_artifact_paths": sum(
            row["result_or_data_artifact_paths"] for row in history
        ),
        "source_history_paper_result_literal_hits_outside_bundled_pdf": sum(
            row["paper_result_literal_hits_outside_bundled_pdf"] for row in history
        ),
        "source_history_paper_result_artifacts_found": sum(
            bool(row["paper_result_artifact_found"]) for row in history
        ),
        "public_fork_census_date": fork_summary["census_date"],
        "public_forks_reported_by_github_rest": fork_summary[
            "github_rest_reported_forks"
        ],
        "public_forks_accessible": fork_summary["accessible_public_forks"],
        "public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
        "public_fork_tag_refs_audited": fork_summary["tag_refs"],
        "public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "public_fork_divergent_heads_audited": fork_summary["divergent_unique_heads"],
        "public_fork_unique_commits_beyond_official_history": fork_summary[
            "unique_commits_beyond_official_history"
        ],
        "public_fork_unique_blobs_beyond_official_history": fork_summary[
            "unique_blobs_beyond_official_history"
        ],
        "public_fork_native_result_artifacts_found": False,
        "public_fork_paper_result_credit": False,
        "paper_era_source_revision_available": True,
        "repository_bundled_pdf_sha256": REPOSITORY_PDF_SHA256,
        "repository_bundled_pdf_exact_arxiv_artifact": False,
        "paper_numeric_tables_audited": ["Overall Evaluation", "Ablation Results on Dataset B"],
        "paper_numeric_table_cells_total": len(table),
        "paper_overall_table_cells_total": 60,
        "paper_ablation_result_cells_total": 15,
        "paper_ablation_design_cells_total": len(ablation),
        "native_paper_table_result_cells_reproduced": 0,
        "published_non_table_quantitative_claims_total": len(claims),
        "published_non_table_result_claims_total": len(result_claims),
        "published_non_table_configuration_claims_total": len(claims) - len(result_claims),
        "native_non_table_result_claims_reproduced": 0,
        "paper_internal_and_source_checks_total": len(checks),
        "paper_specification_gaps_total": len(gaps),
        "numeric_result_figure_panels_total": 5,
        "numeric_result_figure_arrays_shipped": 0,
        "source_mechanism_dimensions_total": len(mechanisms),
        "source_mechanism_status_counts": dict(status_counts),
        "source_mechanism_matches_or_analogues": mechanism_credit,
        "source_mechanism_fully_faithful": False,
        "tracked_source_files_total": len(inventory),
        "tracked_source_python_files_total": sum(bool(row["python_source"]) for row in inventory),
        "tracked_source_upstream_test_files_total": sum(bool(row["upstream_test"]) for row in inventory),
        "paper_source_assets_total": len(paper_assets),
        "native_source_python_files_compiled": native["tracked_python_files_compiled"],
        "native_source_upstream_tests_passed": native["upstream_tests_status"] == "passed",
        "native_released_seed_components_executed": len(native["public_quickstart_component"]["dsl_values"]),
        "native_example_task_bank_tasks_built": native["public_quickstart_component"]["example_task_bank_tasks"],
        "native_source_dependency_environment_reproduced": native[
            "dependency_environment_reproduced"
        ],
        "native_source_exact_historical_dependency_versions_recovered": native[
            "exact_historical_dependency_versions_recovered"
        ],
        "native_source_modules_imported_with_real_dependencies": native[
            "real_dependency_component"
        ]["imported_source_modules"],
        "native_rft_task_bank_tasks_prepared": native["real_dependency_component"][
            "task_bank_tasks"
        ],
        "native_rft_training_prompt_rows_prepared": native[
            "real_dependency_component"
        ]["train_prompt_rows"],
        "native_rft_validation_prompt_rows_prepared": native[
            "real_dependency_component"
        ]["validation_prompt_rows"],
        "native_rft_verl_dataset_subclass_resolved": native[
            "real_dependency_component"
        ]["verl_dataset_subclass"],
        "native_full_gpu_training_environment_reproduced": native[
            "full_gpu_training_environment_reproduced"
        ],
        "native_paper_market_data_shipped": False,
        "native_paper_checkpoint_shipped": False,
        "native_paper_experiment_logs_shipped": False,
        "native_paper_reproduction_scripts_shipped": False,
        "native_paper_factor_library_shipped": False,
        "native_paper_baselines_shipped": False,
        "native_paper_table_outputs_shipped": False,
        "native_paper_result_arrays_shipped": False,
        "native_paper_seed_or_cost_ledger_shipped": False,
        "separate_component_gate_counted": component["counted_components"],
        "separate_component_gate_passed": component["counted_components"] == component["grade_a_or_b"],
        "separate_component_gate_grade": "B",
        "separate_component_gate_paper_result_credit": False,
        "audit_runtime_called_llm_or_market_data_api": False,
        "interpretation": (
            "QuantEvolver has a real, paper-era public framework: the released DSL, seed validation, "
            "task-bank builder, evaluators, DiCo-like archives, and Verl/GRPO wiring are substantive. "
            f"{mechanism_credit}/{len(mechanisms)} audited paper mechanism dimensions are direct matches "
            "or meaningful analogues, all 55 released Python files compile, all three upstream tests pass, "
            "and all 52 package modules import in a clean dependency environment. The three valid "
            "example seeds form a nine-task bank and deterministically produce 16 training and four "
            "validation prompt rows through the released Verl bridge. This is preparatory-path evidence, "
            "not training: QuantEvolver pins neither Verl nor vLLM, vLLM is absent, and no GPU worker, "
            "model, rollout, reward loop, or optimizer runs. "
            "The complete two-commit public history contains no result/data artifact path and no paper "
            "result literal outside the bundled PDF. All four accessible public forks and four branch "
            "refs resolve exactly to the official head and add zero unique commits or blobs. The release explicitly excludes the paper data, checkpoint, logs, and reproduction "
            "scripts and ships none of the paper factors, baselines, fused outputs, result arrays, random "
            "seeds, costs, or exact experiment configuration. Therefore 0/75 table result cells and 0/31 "
            "non-table quantitative result claims are reproduced. The paper also conflicts with itself on "
            "the backbone model, conflicts with source on ICIR scaling, leaves single-asset IC/RankIC "
            "undefined under its published cross-sectional equations, and its headline 7.8% and 109.5% "
            "improvements are not derivable from the displayed table values. The existing 3/3 grade-B "
            "gate remains valid only for released seed/evaluator components under explicit monthly JKP "
            "cadence and universe adaptations; it provides zero full-paper result credit."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
        "paper_source_file_sha256": PINNED_PAPER_SOURCE_SHA256,
        "separate_component_gate_sha256": COMPONENT_GATE_SHA256,
    }

    report = f"""# QuantEvolver paper-level conformance audit

Overall verdict: **substantial public framework, but the paper is not
reproduced**. The implementation is genuine; the experiment is not public.

## Primary-source pins

- Official paper: {PAPER_URL} ({PAPER_VERSION}, submitted {PAPER_DATE}; PDF
  SHA-256 `{PAPER_SHA256}`; TeX archive SHA-256 `{PAPER_SOURCE_SHA256}`).
- Official source: {SOURCE_URL}, commit `{SOURCE_COMMIT}`
  ({SOURCE_COMMIT_DATE}), about 16.2 minutes before arXiv submission. The first
  commit `{README_ONLY_COMMIT}` contains only `README.md`; the second adds the
  complete 67-file release. The repository's 13-page PDF has SHA-256
  `{REPOSITORY_PDF_SHA256}` and is not byte-identical to the 14-page arXiv PDF.

## What genuinely passes

- All {native['tracked_python_files_compiled']} released package Python files
  parse in a clean Python 3.12 environment and all 52 package modules import.
  All three upstream tests pass. The actual released seed validator accepts 3/4
  example seeds, the example configuration builds nine seed-window tasks, and
  all three valid DSL expressions execute twice with identical values on
  deterministic synthetic OHLCV data.
- The released RFT bridge resolves against a compatibility-selected Verl 0.5.0:
  the nine tasks produce 16 training and four validation prompt rows, the
  `NoThinkRLHFDataset` subclass resolves, and the merged config selects GRPO and
  a vLLM rollout. This is not a training run or an exact historical environment:
  QuantEvolver pins neither Verl nor vLLM, vLLM is absent, and no GPU, model,
  rollout, reward loop, or optimizer executes. The 119-line resolved package
  freeze is tracked and hash-checked.
- {mechanism_credit}/{len(mechanisms)} audited mechanism dimensions are direct
  matches or substantial analogues. The release includes structured scenario
  refinement, oracle-style seed generation, DSL validation/realization, seed
  scoring and AST deduplication, seed-window task construction, single-asset and
  cross-sectional evaluators, grouped Verl/GRPO training wiring, exact/family
  diversity shaping, behavioral archives, reward clipping, and factor saving.
- The separate disclosed-component gate still passes **3/3 grade B**. It
  preserves the three released example expressions, DSL/evaluator semantics,
  and return definition while explicitly adapting bars to monthly JKP data and
  the universe to top-1000 U.S. equities. It is useful component evidence.

## Why the paper is not replicated

- The two numeric tables contain **75 result cells**: 60 overall results and 15
  ablation results. **0/75** has a native released paper-result path. The paper
  also makes 31 numeric result assertions in prose/figures (including repeats
  of table values); **0/31** is reproduced from released paper artifacts.
- The README explicitly says the public repository is reusable framework code
  only and excludes private market data, trained checkpoints, experiment logs,
  and paper-specific reproduction scripts. It also omits the paper seed pool,
  task bank, prompts, model snapshots, mined factors, validation arrays, fusion
  inputs/outputs, baseline implementations, trial seeds, costs, and result
  tables. The five numeric result plot panels are vector graphics without their
  underlying arrays.
- The complete non-shallow public history has exactly two commits. Across both
  revisions, there are **0** result/log/checkpoint/data artifact paths and **0**
  occurrences of seven distinctive displayed paper-result literals outside the
  bundled paper PDF. There are no alternate official branches, tags, releases, or
  unreachable local Git objects supplying a hidden experiment path.
- The complete dated public-fork surface has four accessible forks, four branch
  refs, no tags, and one unique head. Every ref resolves exactly to the audited
  official head, adding zero unique commits and zero unique blobs. The forks
  therefore provide no missing experiment or result lineage.
- The generic examples are not paper configs: they use placeholder model and
  asset names, January 2024 example windows, one GPU, and generic thresholds.
  The paper does not identify Benchmark A's asset, Benchmark B's exchange or
  universe, or exact dates/splits for any benchmark, and it leaves many training,
  fusion, portfolio, cost, and baseline details unspecified.

## Paper and paper/source barriers

- The paper first says QuantEvolver uses `Qwen3-14B`, then says all compared
  methods use `Qwen-3.6-Plus`. No model snapshot resolves the conflict.
- The paper defines ICIR as mean IC divided by its standard deviation. The
  released cross-sectional evaluator multiplies this by `sqrt(T)`. It also
  transforms the primary RankIC into `5*RankIC + 0.02*tanh(ICIR)` before DiCo
  shaping, a transform not disclosed in the paper's reward definition.
- Benchmark A contains one asset, but the published IC and RankIC equations are
  cross-sectional correlations over assets and are undefined for `N_t=1`; no
  single-asset replacement definition is supplied.
- The headline 7.8% directional-accuracy improvement is not derivable from
  53.22% versus 52.59% (about 1.20%). The headline 109.5% best-RankIC gain is
  not derivable from 0.0586 versus 0.0337 (about 73.89%). The claimed 186.9%
  top-10 gain has no underlying values in the paper artifacts.
- The profitability arithmetic is at least display-compatible: 125.6% from
  NAV 1 implies 2.256, which rounds to the plotted/prose value 2.26.

## Honest boundary

The source is much closer to the paper's architecture than a proxy, but no
amount of local rerunning can recover withheld experiment inputs and outputs.
The 3/3 component gate must remain separate: it is an adapted component census,
not the Miner checkpoint, RFT search, three benchmarks, factor library, fusion,
or any published result. Run `scripts/audit_quantevolver_paper.py` to regenerate
this package; `--strict` intentionally fails until native paper artifacts and
all published values are actually reproduced.
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
        default=Path(os.environ.get("QUANTEVOLVER_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/quantevolver_source")),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(os.environ.get("QUANTEVOLVER_PAPER_PDF", "/nfs/roberts/scratch/pi_btk22/zc362/quantevolver_paper/paper.pdf")),
    )
    parser.add_argument(
        "--paper-source-archive",
        type=Path,
        default=Path(os.environ.get("QUANTEVOLVER_PAPER_SOURCE_ARCHIVE", "/nfs/roberts/scratch/pi_btk22/zc362/quantevolver_paper/source.tar")),
    )
    parser.add_argument(
        "--paper-source-root",
        type=Path,
        default=Path(os.environ.get("QUANTEVOLVER_PAPER_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/quantevolver_paper/source")),
    )
    parser.add_argument(
        "--source-python",
        type=Path,
        default=Path(os.environ.get("QUANTEVOLVER_SOURCE_PYTHON", DEFAULT_SOURCE_PYTHON)),
    )
    parser.add_argument(
        "--component-root",
        type=Path,
        default=project_root / "paper_runs/faithful_component_replications",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/quantevolver",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root,
        args.paper_pdf,
        args.paper_source_archive,
        args.paper_source_root,
        args.source_python,
        args.component_root,
        args.output_dir,
    )
    print(json.dumps(manifest, indent=2))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
