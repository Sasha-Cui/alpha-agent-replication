#!/usr/bin/env python3
"""Fail-closed paper-level audit of R&D-Agent (arXiv:2505.14738).

The final arXiv v2 source is the result authority.  The audit pins both paper
revisions, the official repository at the last commit preceding each revision,
and the complete public branch/tag path history.  Released component code and
unattributed developmental outputs are credited as component/history evidence
only; without the paper run configurations, traces, data snapshot, model
snapshots, and attributable raw outputs, they cannot receive published-result
credit.
"""
from __future__ import annotations

import argparse
import compileall
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


ARXIV_URL = "https://arxiv.org/abs/2505.14738"
SOURCE_URL = "https://github.com/microsoft/RD-Agent"
AUDIT_DATE = "2026-08-14"
ARXIV_API_SHA256 = "61b02f39c6282e252e0e509633c08cf9632588a99bafaa9f6510554dbcf9bb73"
VERSIONS = {
    "v1": {
        "date": "2025-05-20T06:07:00Z",
        "pdf_sha256": "eed09588dd63962e04073a3da4d360e407e7c685921b3a1496c2b12b3c74e6d3",
        "source_sha256": "a9c27bf40966eb90259e36db9aaba3be5ec749b37da5b25caaea54268eb8cc3b",
        "pages": 7,
        "numeric_table_cells": 32,
    },
    "v2": {
        "date": "2025-10-01T03:21:53Z",
        "pdf_sha256": "36256d4e8a676259f1091f6b530416615179de2551e347fba55f0f395a0cb140",
        "source_sha256": "a33350c6405c7b252974f455e8cf7760704a725723e491faf2a7935d2ab286be",
        "pages": 33,
        "numeric_table_cells": 534,
    },
}
SOURCE_V1_COMMIT = "2112d676d0938de6fea163b2e5eb9c36771e7041"
SOURCE_V1_DATE = "2025-05-19T17:59:42+08:00"
SOURCE_V2_COMMIT = "f360d0a212793eb044c218b5e13b095e684a632d"
SOURCE_V2_DATE = "2025-09-23T16:20:00+08:00"
SOURCE_CURRENT_COMMIT = "6762f84f9bc0f5c6486c50a00e128a57ac6c3683"
SOURCE_CURRENT_DATE = "2026-08-04T19:50:56+08:00"
SOURCE_HISTORY_ROOT_COMMIT = "c740262752b585bc59e41e26807d826ec7bebe75"
SOURCE_HISTORY_REF_COUNT = 231
SOURCE_HISTORY_REF_SHA256 = "89959be7063708bf4eb6f7b143d80f218873825048b5767a46c5ed32c9821e32"
SOURCE_HISTORY_COMMIT_COUNT = 3384
SOURCE_HISTORY_PATH_COUNT = 3188
SOURCE_HISTORY_KEYWORD_PATH_COUNT = 329

HISTORICAL_ARTIFACT_SPECS = (
    (
        "bf8bdfc7db4b6069542a59eb45a7d95c85939fe3",
        "job_log.txt",
        "post_v2_single_competition_command_without_output",
    ),
    *(
        (
            "2564d0ec2c0028c2a2faebab98c4112568443af5",
            f"output_dir/{name}",
            "pre_v1_three_competition_researcher_diagnostic",
        )
        for name in ("aggregated_results.csv", "results.csv", "results_filtered.csv")
    ),
    (
        "b44bef5ec1546a26acca6ce0c84656d585417df0",
        "rdagent/scenarios/kaggle/automated_evaluation/results/20241107_051618/experiment_info.json",
        "pre_v1_automated_evaluation_metadata",
    ),
    (
        "f455327dce876ef1ad2f36ce118a3ade07f355b0",
        "rdagent/scenarios/rl/autorl_bench/results.csv",
        "post_v2_unrelated_RL_benchmark",
    ),
    *(
        (
            "1226e3c46980d1eb072dfd1f0f4ca9bad8c854b4",
            f"results/{name}_results.md",
            "between_v1_v2_39_competition_runner_ratio_diagnostic",
        )
        for name in (
            "diverse-mammoth",
            "liberal-swan",
            "moved-coral",
            "ready-haddock",
            "stable-racer",
        )
    ),
    *(
        (
            "bd9266cb170a5e687d5d47fd627f9201b79cc38a",
            f"scripts/exp/researcher/log/{stamp}/debug_llm.pkl",
            "between_v1_v2_debug_LLM_pickle_not_deserialized",
        )
        for stamp in ("2025-04-08_03-05-05-888845", "2025-04-08_03-05-13-631223")
    ),
    *(
        (
            "416ecc8161ef0a18dc04b77ca2ca81a0de7ef219",
            f"scripts/exp/researcher/output_dir/solution/1f0027620e684019a9d37666ce31bd78/{name}",
            "pre_v1_single_example_solution_artifact",
        )
        for name in ("scores.csv", "submission.csv")
    ),
)

METRICS = ("valid_submission", "above_median", "bronze", "silver", "gold", "any_medal")

MAIN_RESULTS = {
    "MLAB/GPT-4o": ((44.3, 2.6), (1.9, .7), (0, 0), (0, 0), (.8, .5), (.8, .5)),
    "OpenHands/GPT-4o": ((52, 3.3), (7.1, 1.7), (.4, .4), (1.3, .8), (2.7, 1.1), (4.4, 1.4)),
    "AIDE/GPT-4o": ((54.9, 1), (14.4, .7), (1.6, .2), (2.2, .3), (5, .4), (8.7, .5)),
    "AIDE/o1-preview": ((82.8, 1.1), (29.4, 1.3), (3.4, .5), (4.1, .6), (9.4, .8), (16.9, 1.1)),
    "ML-Master/Deepseek-R1": ((93.3, 1.3), (44.9, 1.2), (4.4, .9), (7.6, .4), (17.3, .8), (29.3, .8)),
    "ML-Master/o3+GPT-4.1": ((98.2, .9), (25.8, 1.9), (5.8, 1.6), (3.1, 1.9), (9.3, .8), (18.2, 1.9)),
    "ML-Master/GPT-5": ((85.3, 3.5), (26.2, 1.6), (4.4, 1.2), (3.1, .4), (9.3, .8), (16.9, 1.2)),
    "R&D-Agent/o3+GPT-4.1": ((94.2, .4), (44.9, .4), (6.2, .9), (7.5, 1.2), (16, .8), (29.7, .4)),
    "R&D-Agent/GPT-5": ((96, 0), (45.3, 0), (6.7, 1.5), (12, .8), (16.4, .9), (35.1, .4)),
}

RESEARCH_ABLATION = {
    "avg_loops": ((45.9, 2.2), 48.4, 19.4, 55.3, 44.0),
    "improve_rate": ((41.1, .4), 39.4, 40.0, 23.0, 40.9),
    "first_medal_hours": ((2.9, .1), 1.7, 3.0, 1.7, 2.0),
    "medal_rate": ((65.8, .8), 50.0, 47.5, 50.0, 60.0),
    "any_medal": ((35.1, .4), 26.7, 25.3, 26.7, 32.0),
}
ABLATION_CONFIGS = ("full", "without_planning", "without_exploration_path", "without_reasoning", "without_memory")

RAG_RESULTS = {
    "baseline": (68.2, 21.1, 22.2, 35.1),
    "with_RAG": (54.6, 21.1, 26.7, 32.0),
}
DIFFICULTIES = ("low_lite", "medium", "high", "all")

RUNTIME_ROWS = (
    ("MLAB/GPT-4o", 24, None), ("OpenHands/GPT-4o", 24, None),
    ("AIDE/GPT-4o", 24, None), ("AIDE/o1-preview", 24, None),
    ("ML-Master/Deepseek-R1", 12, None), ("KompeteAI/Gemini-2.5-flash", 6, None),
    ("MLE-STAR/Gemini-2.5-pro", 24, 8), ("MLE-STAR/Gemini-2.0-flash", 24, 8),
    ("AIRA/Greedy", 24, None), ("AIRA/MCTS", 24, None), ("R&D-Agent/GPT-5", 12, None),
)

CLOSED_RESULTS = {
    "InternAgent": (12, ((62.1, 3.0), (26.3, 2.6), (24.4, 2.2), (36.4, 1.2))),
    "Neo": (36, ((48.5, 1.5), (29.8, 2.3), (24.4, 2.2), (34.2, .9))),
    "R&D-Agent/GPT-5": (12, ((68.2, 2.6), (21.1, 1.5), (22.2, 2.2), (35.1, .4))),
}

RAW_MAIN = {
    "R&D-Agent/GPT-5": (
        (96.0, 45.3, 6.7, 12.0, 17.3, 36.0),
        (96.0, 45.3, 4.0, 13.4, 17.3, 34.7),
        (96.0, 45.3, 9.3, 10.7, 14.7, 34.7),
    ),
    "R&D-Agent/o3+GPT-4.1": (
        (94.7, 45.3, 8.0, 5.3, 17.3, 30.6),
        (93.3, 44.0, 5.3, 8.0, 16.0, 29.3),
        (94.7, 45.3, 5.3, 9.3, 14.7, 29.3),
    ),
}

COST_RESULTS = {
    "run_1": (4.68, 11.14, 15.82), "run_2": (7.85, 14.37, 22.22),
    "run_3": (8.43, 15.75, 24.18), "average": (6.99, 13.75, 20.74),
}

V1_RESULTS = {
    "AIDE/o1": ((34.3, 2.4), (8.8, 1.1), (10.0, 1.9), (16.9, 1.1)),
    "R&D-Agent/o1": ((48.18, 2.49), (8.95, 2.36), (18.67, 2.98), (22.4, 1.1)),
    "R&D-Agent/o3+GPT-4.1": ((51.52, 6.21), (7.89, 3.33), (16.67, 3.65), (22.45, 2.45)),
    "R&D-Agent/o3+GPT-4.1/multi-trace": ((50.54, 2.51), (9.86, 3.89), (20.0, 8.16), (24.0, .94)),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source_root), *args], check=True,
        capture_output=True, text=not binary,
    )
    return proc.stdout


def git_show(source_root: Path, commit: str, path: str) -> str:
    return str(run_git(source_root, "show", f"{commit}:{path}"))


def git_blob(source_root: Path, commit: str, path: str) -> bytes:
    return bytes(run_git(source_root, "show", f"{commit}:{path}", binary=True))


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def result_row(table: str, item: str, metric: str, statistic: str, value: float, unique_id: str | None = None) -> dict[str, Any]:
    display_id = f"{table}/{item}/{metric}/{statistic}"
    return {
        "paper_table": table,
        "item": item,
        "metric": metric,
        "statistic": statistic,
        "display_cell_id": display_id,
        "unique_measurement_id": unique_id or display_id,
        "paper_value": fmt(value),
        "native_reproduced_value": "",
        "status": "not_reproduced_no_released_paper_run_artifact",
        "paper_result_credit": False,
    }


def parse_baseline_medal_rows(paper_root: Path) -> list[tuple[str, tuple[int, int, int, int]]]:
    text = (paper_root / "source_v2" / "appendix.tex").read_text(encoding="utf-8")
    start = text.index(r"\label{tab:baseline_medal_stats}")
    end = text.index(r"\end{longtable}", start)
    block = text[start:end]
    parsed: list[tuple[str, tuple[int, int, int, int]]] = []
    pattern = re.compile(r"^([^%\\][^&]+?)\s*&\s*([0-3])\s*&\s*([0-3])\s*&\s*([0-3])\s*&\s*([0-3])\s*\\\\\s*$")
    for line in block.splitlines():
        match = pattern.match(line.strip())
        if match:
            parsed.append((match.group(1).strip(), tuple(int(match.group(i)) for i in range(2, 6))))
    if len(parsed) != 75 or len({name for name, _ in parsed}) != 75:
        raise RuntimeError(f"R&D-Agent per-competition medal census changed: {len(parsed)}")
    return parsed


def paper_table_rows(paper_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item, results in MAIN_RESULTS.items():
        for metric, pair in zip(METRICS, results):
            for stat, value in zip(("mean", "sem"), pair):
                unique = None
                if item == "R&D-Agent/GPT-5" and metric == "any_medal":
                    unique = f"summary/rd_gpt5/all/{stat}"
                rows.append(result_row("Table 2 main MLE-Bench", item, metric, stat, value, unique))

    for metric, values in RESEARCH_ABLATION.items():
        full, *ablations = values
        for stat, value in zip(("mean", "sem"), full):
            unique = f"summary/rd_gpt5/all/{stat}" if metric == "any_medal" else None
            rows.append(result_row("Table 3 research ablation", "full", metric, stat, value, unique))
        for config, value in zip(ABLATION_CONFIGS[1:], ablations):
            rows.append(result_row("Table 3 research ablation", config, metric, "reported", value))

    for item, values in RAG_RESULTS.items():
        for difficulty, value in zip(DIFFICULTIES, values):
            unique = f"summary/rd_gpt5/{difficulty}/mean" if item == "baseline" else None
            rows.append(result_row("Table 4 RAG", item, difficulty, "mean", value, unique))

    for item, hours, gpu_count in RUNTIME_ROWS:
        rows.append(result_row("Table 5 runtime and GPU", item, "runtime_hours", "reported", hours))
        if gpu_count is not None:
            rows.append(result_row("Table 5 runtime and GPU", item, "gpu_count", "reported", gpu_count))

    for item, (hours, results) in CLOSED_RESULTS.items():
        rows.append(result_row("Table 6 closed-source comparison", item, "runtime_hours", "reported", hours))
        for difficulty, pair in zip(DIFFICULTIES, results):
            for stat, value in zip(("mean", "sem"), pair):
                unique = f"summary/rd_gpt5/{difficulty}/{stat}" if item == "R&D-Agent/GPT-5" else None
                rows.append(result_row("Table 6 closed-source comparison", item, difficulty, stat, value, unique))

    for item, runs in RAW_MAIN.items():
        for run_index, values in enumerate(runs, 1):
            for metric, value in zip(METRICS, values):
                rows.append(result_row("Table 7 raw main runs", f"{item}/run_{run_index}", metric, "raw_run", value))

    for item, values in COST_RESULTS.items():
        for metric, value in zip(("research_cost_usd", "development_cost_usd", "total_cost_usd"), values):
            rows.append(result_row("Table 8 GPT-5 costs", item, metric, "reported", value))

    configs = ("ML-Master/o3+GPT-4.1", "ML-Master/GPT-5", "R&D-Agent/GPT-5", "R&D-Agent/o3+GPT-4.1")
    for competition, counts in parse_baseline_medal_rows(paper_root):
        for config, value in zip(configs, counts):
            rows.append(result_row("Table 9 per-competition medals", competition, config, "medals_across_three_runs", value))

    expected = {
        "Table 2 main MLE-Bench": 108, "Table 3 research ablation": 30,
        "Table 4 RAG": 8, "Table 5 runtime and GPU": 13,
        "Table 6 closed-source comparison": 27, "Table 7 raw main runs": 36,
        "Table 8 GPT-5 costs": 12, "Table 9 per-competition medals": 300,
    }
    if len(rows) != 534 or Counter(row["paper_table"] for row in rows) != expected:
        raise RuntimeError("R&D-Agent final numeric table census changed")
    return rows


def unique_measurement_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["unique_measurement_id"])
        if key not in unique:
            unique[key] = {
                "unique_measurement_id": key,
                "paper_value": row["paper_value"],
                "display_occurrences": 0,
                "native_reproduced_value": "",
                "status": row["status"],
                "paper_result_credit": False,
            }
        elif float(unique[key]["paper_value"]) != float(row["paper_value"]):
            raise RuntimeError(f"Repeated R&D-Agent result disagrees: {key}")
        unique[key]["display_occurrences"] += 1
    expected_occurrences = {1: 521, 2: 3, 3: 1, 4: 1}
    if len(unique) != 526 or Counter(row["display_occurrences"] for row in unique.values()) != expected_occurrences:
        raise RuntimeError("R&D-Agent unique-measurement census changed")
    return list(unique.values())


FIGURES = {
    "Figure 1 / agent_performance_compact_new.pdf": (
        "MLAB/GPT-4o", "OpenHands/GPT-4o", "AIDE/GPT-4o", "AIDE/o1-preview",
        "ML-Master/GPT-5", "ML-Master/Deepseek-R1", "R&D-Agent/GPT-5",
    ),
    "Figure 4 / backend_comparison.pdf": ("GPT-4.1 only", "o3 only", "o3(R)+GPT-4.1(D)"),
    "Figure 3 / development_ablation_narrow.png": (
        "perfect selection", "full system", "without coding workflow", "without evaluation strategy",
    ),
    "Figure 5 / lite_performance_comparison.pdf": (
        "R&D-Agent/GPT-5", "MLE-STAR/Gemini-2.5-pro", "InternAgent/Deepseek-R1",
        "KompeteAI/Gemini-2.5-flash", "ML-Master/Deepseek-R1", "Neo", "AIRA/Greedy",
        "AIDE/o1-preview", "OpenHands/GPT-4o", "MLAB/GPT-4o",
    ),
}


def figure_rows() -> list[dict[str, Any]]:
    rows = []
    for figure, labels in FIGURES.items():
        for label in labels:
            rows.append({
                "figure": figure,
                "series_or_bar": label,
                "paper_source_asset_present": True,
                "underlying_numeric_data_or_plot_code_released": False,
                "native_exact_series_reproduced": False,
                "status": "paper_asset_only_no_underlying_plot_inputs_or_generation_code",
                "paper_result_credit": False,
            })
    if len(rows) != 24 or len(FIGURES) != 4:
        raise RuntimeError("R&D-Agent result-figure census changed")
    return rows


def version_rows() -> list[dict[str, Any]]:
    rows = []
    for config, results in V1_RESULTS.items():
        for difficulty, pair in zip(DIFFICULTIES, results):
            for statistic, value in zip(("mean", "std"), pair):
                rows.append({
                    "release": "arXiv v1", "configuration": config, "metric": f"{difficulty}_any_medal",
                    "statistic": statistic, "value": fmt(value),
                    "v2_disposition": "superseded_noncomparable_protocol_24h_to_12h_models_metrics_and_seeds_changed",
                })
    if len(rows) != 32:
        raise RuntimeError("R&D-Agent v1 result census changed")
    return rows


def version_summary_rows() -> list[dict[str, Any]]:
    return [
        {
            "release": "arXiv v1", "date": VERSIONS["v1"]["date"], "pages": 7,
            "numeric_table_cells": 32, "runtime_hours": 24, "reported_error": "standard deviation",
            "reported_seed_count": "5 for o1; 6 for o3+GPT-4.1", "result_authority": False,
            "notes": "four configurations by Lite/Medium/High/All any-medal rate; includes o1 and two-trace fusion",
        },
        {
            "release": "arXiv v2", "date": VERSIONS["v2"]["date"], "pages": 33,
            "numeric_table_cells": 534, "runtime_hours": 12, "reported_error": "SEM",
            "reported_seed_count": "3", "result_authority": True,
            "notes": "rewritten report with GPT-5 and hybrid experiments, ablations, raw runs, costs, and per-competition counts",
        },
        {
            "release": "official README current", "date": SOURCE_CURRENT_DATE, "pages": "",
            "numeric_table_cells": 32, "runtime_hours": 24, "reported_error": "standard deviation",
            "reported_seed_count": "5 for o1; 6 for o3+GPT-4.1", "result_authority": False,
            "notes": "still reports v1-era configurations plus a later hybrid 30.22±1.5 value; does not report v2 GPT-5 result",
        },
    ]


MECHANISMS = (
    ("research_development_separation", "separate research proposal and development execution phases", "rdagent/scenarios/data_science/loop.py", ("propose", "develop"), "implementation present"),
    ("dynamic_time_planning", "time-aware draft/model-architecture planning", "rdagent/scenarios/data_science/proposal/exp_gen/planner/__init__.py", ("remain_percent", "suggest_model_architecture"), "implementation present but enable_planner defaults false"),
    ("research_DAG", "DAG-backed experiment trace with parent selections", "rdagent/scenarios/data_science/proposal/exp_gen/base.py", ("dag_parent", "sync_dag_parent_and_hist", "get_leaves"), "implementation present"),
    ("parallel_multi_trace", "parallel trace exploration", "rdagent/scenarios/data_science/proposal/exp_gen/router/__init__.py", ("class ParallelMultiTraceExpGen", "DS_RD_SETTING.max_trace_num"), "implementation present but max_trace_num defaults one"),
    ("interaction_kernel", "cosine similarity plus tanh score difference and exponential path decay", "rdagent/scenarios/data_science/proposal/exp_gen/proposal.py", ("alpha * sim_matrix * math.exp(-gamma * path_length)", "torch.tanh(score_diff_matrix)", "torch.clamp(logits, min=-2, max=2)"), "paper equation is implemented with alpha=beta=1 and gamma=ln(2)/30"),
    ("probabilistic_history_sampling", "softmax/categorical historical-hypothesis sampling", "rdagent/scenarios/data_science/proposal/exp_gen/proposal.py", ("torch.softmax", "torch.multinomial", "n_samples = min(2"), "implementation present"),
    ("adaptive_hypothesis_selection", "LLM select/modify/generate from candidates", "rdagent/scenarios/data_science/proposal/exp_gen/proposal.py", ("llm_select_hypothesis", "select_hypothesis"), "implementation present but llm_select_hypothesis defaults false"),
    ("round_robin_scheduler", "round-robin trace scheduler", "rdagent/scenarios/data_science/proposal/exp_gen/trace_scheduler.py", ("class RoundRobinScheduler", "return trace.NEW_ROOT"), "default scheduler exists but is not the paper's probabilistic interaction kernel"),
    ("probabilistic_scheduler", "potential-weighted leaf scheduler", "rdagent/scenarios/data_science/proposal/exp_gen/trace_scheduler.py", ("class ProbabilisticScheduler", "_softmax_probabilities"), "implementation present but not the default scheduler"),
    ("collaborative_memory", "cross-trace diversity and idea context", "rdagent/scenarios/data_science/proposal/exp_gen/idea_pool.py", ("class DSIdea", "class DSKnowledgeBase"), "implementation present; paper run state absent"),
    ("scientific_hypothesis_pipeline", "problem identification and hypothesis-driven proposal", "rdagent/scenarios/data_science/proposal/exp_gen/prompts_v2.yaml", ("hypothesis", "problem"), "prompt implementation present; exact run prompts/responses absent"),
    ("hypothesis_critique_rewrite", "critique and rewrite stage", "rdagent/scenarios/data_science/proposal/exp_gen/proposal.py", ("Hypothesis critique and rewrite", "enable_hypo_critique_rewrite"), "implementation present but defaults false"),
    ("iterative_coding_workflow", "LLM coder with iterative debugging", "rdagent/components/coder/CoSTEER/__init__.py", ("class CoSTEER", "evolving_trace"), "generic CoSTEER implementation is used by the data-science runner"),
    ("sampled_debug_data", "debugging on sampled data before full execution", "rdagent/scenarios/data_science/scen/__init__.py", ("sample_data_by_LLM", "recommend_debug_timeout"), "implementation present and source default enabled"),
    ("execution_and_score_validation", "execute generated workflow and validate scores.csv", "rdagent/scenarios/data_science/dev/runner/eval.py", ("scores.csv", "DSRunnerEvaluator", "ensemble"), "implementation present"),
    ("evaluation_alignment_feedback", "LLM checks evaluation alignment and replacement decision", "rdagent/scenarios/data_science/dev/feedback.py", ("Evaluation Aligned With Task", "Replace Best Result"), "implementation present"),
    ("best_valid_selector", "rank valid candidates by validation score", "rdagent/scenarios/data_science/proposal/exp_gen/select/submit.py", ("class BestValidSelector", "collect_sota_candidates"), "implementation present"),
    ("holdout_revalidation", "candidate re-evaluation on a common synthetic holdout", "rdagent/scenarios/data_science/proposal/exp_gen/select/submit.py", ("class ValidationSelector", "sample_rate: float = 0.8"), "implementation present but default is 80/20, not paper's 90/10"),
    ("submission_validation", "MLE-Bench submission-format/test evaluation", "rdagent/scenarios/data_science/dev/runner/eval.py", ("get_test_eval", "Submission check"), "implementation present"),
    ("optional_RAG", "optional external knowledge base", "rdagent/app/data_science/conf.py", ("enable_knowledge_base: bool = False", "knowledge_base_path"), "implementation hook present and defaults false"),
    ("MLE_Bench_environment", "MLE-Bench evaluator/runtime image", "rdagent/scenarios/kaggle/docker/mle_bench_docker/Dockerfile", ("github.com/openai/mle-bench.git", "git lfs pull"), "implementation present but upstream clone is unpinned"),
)


def mechanism_rows(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for name, spec, path, tokens, caveat in MECHANISMS:
        text = git_show(source_root, SOURCE_V2_COMMIT, path)
        present = all(token in text for token in tokens)
        rows.append({
            "mechanism": name, "paper_specification": spec, "paper_era_source_path": path,
            "required_source_tokens_found": present, "source_evidence": caveat,
            "status": "component_implementation_present_unexecuted" if present else "missing_from_paper_era_source",
            "reported_run_configuration_or_trace_released": False,
            "paper_mechanism_execution_credit": False, "paper_result_credit": False,
        })
    if len(rows) != 21 or not all(row["required_source_tokens_found"] for row in rows):
        raise RuntimeError("R&D-Agent mechanism-source census changed")
    return rows


def config_rows(source_root: Path) -> list[dict[str, Any]]:
    conf = git_show(source_root, SOURCE_V2_COMMIT, "rdagent/app/data_science/conf.py")
    proposal = git_show(source_root, SOURCE_V2_COMMIT, "rdagent/scenarios/data_science/proposal/exp_gen/proposal.py")
    selector = git_show(source_root, SOURCE_V2_COMMIT, "rdagent/scenarios/data_science/proposal/exp_gen/select/submit.py")
    docker = git_show(source_root, SOURCE_V2_COMMIT, "rdagent/scenarios/kaggle/docker/mle_bench_docker/Dockerfile")
    configs = [
        ("runtime per competition", "12 hours", "runner CLI accepts a timeout but no paper command/config is released", "unverified"),
        ("CPU", "12 vCPU", "not pinned in repository", "missing"),
        ("RAM", "220 GB", "not pinned in repository", "missing"),
        ("GPU", "one NVIDIA V100", "Docker base pins CUDA/PyTorch, not physical GPU", "unverified"),
        ("main seeds", "3", "no paper seed list or run manifest", "missing"),
        ("main backend", "GPT-5", "no exact provider deployment/model snapshot", "missing"),
        ("hybrid research backend", "o3", "no exact provider deployment/model snapshot", "missing"),
        ("hybrid development backend", "GPT-4.1", "no exact provider deployment/model snapshot", "missing"),
        ("API provider", "Azure OpenAI", "general API configuration exists; paper deployment/version absent", "unverified"),
        ("benchmark", "75 MLE-Bench competitions", "Dockerfile clones MLE-Bench live without a commit", "mismatch_unpinned" if "git clone https://github.com/openai/mle-bench.git" in docker else "missing"),
        ("difficulty counts", "22 Lite, 38 Medium, 15 High", "paper only; frozen task manifest absent", "missing"),
        ("planner enabled", "dynamic planning", "enable_planner defaults false", "mismatch_default" if "enable_planner: bool = False" in conf else "unverified"),
        ("trace scheduler", "adaptive exploration", "default is RoundRobinScheduler", "mismatch_default" if "trace_scheduler: str = \"rdagent.scenarios.data_science.proposal.exp_gen.trace_scheduler.RoundRobinScheduler\"" in conf else "unverified"),
        ("trace count", "parallel/multi-trace design", "max_trace_num defaults 1", "mismatch_default" if "max_trace_num: int = 1" in conf else "unverified"),
        ("LLM hypothesis selector", "enabled in described algorithm", "llm_select_hypothesis defaults false", "mismatch_default" if "llm_select_hypothesis: bool = False" in conf else "unverified"),
        ("hypothesis critique/rewrite", "scientific multi-step reasoning", "enable_hypo_critique_rewrite defaults false", "mismatch_default" if "enable_hypo_critique_rewrite: bool = False" in conf else "unverified"),
        ("sampled debugging", "enabled", "sample_data_by_LLM defaults true", "source_default_matches" if "sample_data_by_LLM: bool = True" in conf else "unverified"),
        ("debug timeout", "not separately specified in paper", "600 seconds", "source_only" if "debug_timeout: int = 600" in conf else "missing"),
        ("full-run timeout", "bounded by 12-hour overall budget", "3600 seconds per execution", "source_only" if "full_timeout: int = 3600" in conf else "missing"),
        ("holdout split", "stratified 90/10", "ValidationSelector defaults sample_rate=0.8", "mismatch_default" if "sample_rate: float = 0.8" in selector else "unverified"),
        ("interaction alpha", "1.0 in source implementation", "alpha=1.0", "source_matches" if "alpha, beta = 1.0, 1.0" in proposal else "missing"),
        ("interaction beta", "1.0, or 0 before a SOTA exists", "beta=1.0/0", "source_matches" if "alpha, beta = 1.0, 0" in proposal else "missing"),
        ("interaction gamma", "decay factor; appendix omits numeric value", "ln(2)/30", "source_resolves_paper_omission" if "gamma = math.log(2) / 30" in proposal else "missing"),
        ("interaction clamp", "[-2,2]", "torch.clamp min=-2 max=2", "source_matches" if "torch.clamp(logits, min=-2, max=2)" in proposal else "missing"),
        ("history samples", "n unspecified", "at most 2 plus global best", "source_resolves_paper_omission" if "n_samples = min(2, num_candidates)" in proposal else "missing"),
        ("fixed seed/data split", "three independent runs", "fix_seed_and_data_split defaults false", "unverified" if "fix_seed_and_data_split: bool = False" in conf else "missing"),
        ("RAG knowledge base", "85 non-MLE-Bench competitions", "disabled by default; corpus snapshot absent", "unverified" if "enable_knowledge_base: bool = False" in conf else "missing"),
        ("raw run outputs", "three runs for two main configurations", "not included in repository", "missing"),
        ("cost accounting", "research/development API cost per competition", "request logs and pricing snapshot absent", "missing"),
        ("baseline revisions", "official results plus ML-Master re-evaluations", "commits/configs/hardware images not pinned", "missing"),
    ]
    return [{
        "configuration": name, "paper_value": paper_value, "released_source_evidence": source_value,
        "status": status, "verified_for_reported_run": False, "paper_configuration_credit": False,
    } for name, paper_value, source_value, status in configs]


def source_snapshot_rows(source_root: Path) -> list[dict[str, Any]]:
    specs = (
        ("pre_v1", SOURCE_V1_COMMIT, SOURCE_V1_DATE, VERSIONS["v1"]["date"]),
        ("pre_v2", SOURCE_V2_COMMIT, SOURCE_V2_DATE, VERSIONS["v2"]["date"]),
        ("audit_current", SOURCE_CURRENT_COMMIT, SOURCE_CURRENT_DATE, AUDIT_DATE),
    )
    rows = []
    prefixes = ("rdagent/app/data_science/", "rdagent/scenarios/data_science/", "rdagent/scenarios/kaggle/", "docs/scens/data_science")
    for label, commit, date, cutoff in specs:
        names = str(run_git(source_root, "ls-tree", "-r", "--name-only", commit)).splitlines()
        relevant = [name for name in names if name.startswith(prefixes)]
        result_like = [name for name in relevant if re.search(r"(^|/)(results?|outputs?|logs?|traces?|checkpoints?)(/|\.|$)", name, re.I)]
        rows.append({
            "snapshot": label, "commit": commit, "commit_date": date, "cutoff_or_audit_date": cutoff,
            "tracked_files": len(names), "data_science_or_kaggle_files": len(relevant),
            "data_science_or_kaggle_python_files": sum(name.endswith(".py") for name in relevant),
            "released_result_trace_checkpoint_files": len(result_like),
        })
    expected = [(536, 249), (609, 268), (907, 268)]
    if [(row["tracked_files"], row["data_science_or_kaggle_files"]) for row in rows] != expected:
        raise RuntimeError("R&D-Agent source snapshot census changed")
    return rows


HISTORY_KEYWORD_RE = re.compile(
    r"result|output|log|trace|checkpoint|submission|score",
    re.IGNORECASE,
)


def _history_path_role(path: str, candidate_roles: Mapping[str, str]) -> str:
    if path in candidate_roles:
        return candidate_roles[path]
    if "/training_set/" in path or path.startswith("sample/"):
        return "training_or_sample_reference_not_agent_run_output"
    if path.startswith("scripts/exp/researcher/output_dir/extracted_ideas/"):
        return "retrieved_idea_input_not_agent_run_output"
    if path.startswith("scripts/exp/researcher/output_dir/idea"):
        return "idea_pool_or_intermediate_not_paper_run_output"
    if HISTORY_KEYWORD_RE.search(path):
        return "keyword_path_source_template_test_or_unattributed_nonpaper_artifact"
    return "ordinary_historical_source_path"


def _artifact_scope_summary(path: str, role: str, blob: bytes) -> str:
    if path.endswith(".pkl"):
        return "opaque debug pickle inventoried without deserialization or execution"
    text = blob.decode("utf-8", errors="replace")
    if role == "post_v2_single_competition_command_without_output":
        command = " ".join(text.split())
        return f"one cafa-6 12-hour invocation and no result payload: {command}"
    if role == "between_v1_v2_39_competition_runner_ratio_diagnostic":
        rows = [
            line
            for line in text.splitlines()
            if line.startswith("| ")
            and not line.startswith("| Competition")
            and not line.startswith("|---")
        ]
        populated = sum("N/A" not in row for row in rows)
        if len(rows) != 39:
            raise RuntimeError(f"Historical runner diagnostic row count changed: {path}")
        return (
            f"39 competition rows; {populated} populated Base/Prev/SOTA ratio rows; "
            "not the paper's 75-competition medal outputs"
        )
    if role == "pre_v1_three_competition_researcher_diagnostic":
        rows = list(csv.DictReader(io.StringIO(text)))
        competitions = sorted({row["Competition"] for row in rows})
        if len(competitions) != 3:
            raise RuntimeError(f"Historical researcher competition census changed: {path}")
        return f"{len(rows)} rows across three developmental competitions: {', '.join(competitions)}"
    if role == "pre_v1_automated_evaluation_metadata":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            if '"competition": "sf-crime"' not in text or '"results":' not in text:
                raise RuntimeError("Historical automated-evaluation metadata changed")
            return (
                "malformed pre-paper sf-crime metadata ending with an empty results key; "
                "not an executable result artifact"
            )
        return f"pre-paper automated-evaluation metadata with {len(payload)} top-level fields"
    if role == "post_v2_unrelated_RL_benchmark":
        rows = list(csv.DictReader(io.StringIO(text)))
        return f"{len(rows)} post-paper AutoRL rows outside the MLE-Bench paper scope"
    if role == "pre_v1_single_example_solution_artifact":
        rows = list(csv.reader(io.StringIO(text)))
        return f"single example-solution artifact with {max(0, len(rows) - 1)} data rows"
    raise ValueError(f"missing historical artifact summary rule: {role}")


def public_source_history(
    source_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    ref_lines = [
        line
        for line in str(
            run_git(
                source_root,
                "for-each-ref",
                "--format=%(refname) %(objectname)",
                "refs/remotes/origin",
                "refs/tags",
            )
        ).splitlines()
        if not line.startswith("refs/remotes/origin/HEAD ")
    ]
    ref_snapshot = "\n".join(sorted(ref_lines)) + "\n"
    roots = sorted(str(run_git(source_root, "rev-list", "--all", "--max-parents=0")).splitlines())
    commits = sorted(set(str(run_git(source_root, "rev-list", "--all")).splitlines()))
    paths = sorted(
        {
            path
            for path in str(
                run_git(source_root, "log", "--all", "--name-only", "--format=")
            ).splitlines()
            if path
        }
    )
    candidate_roles = {path: role for _, path, role in HISTORICAL_ARTIFACT_SPECS}
    checks = {
        "remote_ref_count": len(ref_lines) == SOURCE_HISTORY_REF_COUNT,
        "remote_ref_snapshot_sha256": (
            bytes_sha256(ref_snapshot.encode("utf-8")) == SOURCE_HISTORY_REF_SHA256
        ),
        "reachable_commit_count": len(commits) == SOURCE_HISTORY_COMMIT_COUNT,
        "root_commit": roots == [SOURCE_HISTORY_ROOT_COMMIT],
        "historical_changed_path_count": len(paths) == SOURCE_HISTORY_PATH_COUNT,
        "keyword_path_count": (
            sum(bool(HISTORY_KEYWORD_RE.search(path)) for path in paths)
            == SOURCE_HISTORY_KEYWORD_PATH_COUNT
        ),
        "artifact_candidate_paths_present": set(candidate_roles).issubset(paths),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Pinned R&D-Agent public history changed: {checks}")

    path_rows = [
        {
            "historical_path": path,
            "contains_result_output_log_trace_checkpoint_submission_or_score_keyword": bool(
                HISTORY_KEYWORD_RE.search(path)
            ),
            "selected_artifact_candidate": path in candidate_roles,
            "path_role": _history_path_role(path, candidate_roles),
            "attributable_to_published_75_competition_three_seed_run": False,
            "paper_result_credit": False,
        }
        for path in paths
    ]

    artifact_rows: list[dict[str, Any]] = []
    for commit, path, role in HISTORICAL_ARTIFACT_SPECS:
        blob = git_blob(source_root, commit, path)
        commit_date = str(run_git(source_root, "show", "-s", "--format=%cI", commit)).strip()
        remote_refs = sorted(
            line.strip()
            for line in str(run_git(source_root, "branch", "-r", "--contains", commit)).splitlines()
            if line.strip() and " -> " not in line
        )
        artifact_rows.append(
            {
                "evidence_commit": commit,
                "commit_date": commit_date,
                "remote_refs_containing_commit": ";".join(remote_refs),
                "historical_path": path,
                "blob_sha256": bytes_sha256(blob),
                "bytes": len(blob),
                "artifact_role": role,
                "scope_summary": _artifact_scope_summary(path, role, blob),
                "attributable_to_published_75_competition_three_seed_run": False,
                "contains_paper_run_config_seed_and_model_lineage": False,
                "paper_result_credit": False,
            }
        )
    if len(artifact_rows) != 15:
        raise RuntimeError("Expected fifteen bounded historical artifact candidates")

    summary = {
        "scope": "all locally pinned remote branches and tags",
        "remote_refs": len(ref_lines),
        "remote_ref_snapshot_sha256": bytes_sha256(ref_snapshot.encode("utf-8")),
        "reachable_commits": len(commits),
        "root_commit": roots[0],
        "unique_historical_changed_paths": len(paths),
        "keyword_paths": sum(bool(HISTORY_KEYWORD_RE.search(path)) for path in paths),
        "bounded_artifact_candidates_inspected": len(artifact_rows),
        "attributable_published_run_artifacts": 0,
        "paper_result_cells_reproduced_from_history": 0,
        "assessment": (
            "developmental_and_unrelated_branch_artifacts_exist_but_no_75_competition_"
            "three_seed_paper_run_lineage"
        ),
        "checks": checks,
    }
    return summary, path_rows, artifact_rows


def paper_asset_rows(paper_root: Path) -> list[dict[str, Any]]:
    result_assets = {"agent_performance_compact_new.pdf", "backend_comparison.pdf", "development_ablation_narrow.png", "lite_performance_comparison.pdf"}
    rows = []
    for path in sorted((paper_root / "source_v2" / "Figures").iterdir()):
        rows.append({
            "path": f"Figures/{path.name}", "sha256": sha256(path), "bytes": path.stat().st_size,
            "active_result_figure": path.name in result_assets,
            "underlying_numeric_data_or_generation_code_released": False,
            "status": "result_asset_without_plot_inputs" if path.name in result_assets else "architecture_diagram",
            "paper_result_credit": False,
        })
    if len(rows) != 5 or sum(bool(row["active_result_figure"]) for row in rows) != 4:
        raise RuntimeError("R&D-Agent source figure-asset census changed")
    return rows


def internal_check_rows() -> list[dict[str, Any]]:
    checks = [
        ("result authority", "arXiv v2 is a 33-page rewrite and the final available revision", "pass", True),
        ("v1 to v2 protocol", "runtime changes 24h to 12h; configurations, metrics, seeds, and error statistic change", "material_noncomparable_revision", False),
        ("raw GPT-5 summary", "rounded raw runs reconstruct all six means/SEMs to displayed precision", "pass_with_rounded_inputs", True),
        ("raw hybrid summary", "rounded raw runs imply Valid Submission SEM 0.5, while Table 2 prints 0.4; hidden precision may explain it", "not_reconstructable_from_displayed_raw_values", False),
        ("ML-Master GPT-5 uncertainty", "main prose says Any Medal 16.9±2.0, Table 2 and Figure 1 say 16.9±1.2", "contradiction", False),
        ("hybrid backend result", "Appendix backend figure says 29.3%, while Table 2 reports hybrid 29.7±0.4%", "contradiction_or_different_unidentified_run", False),
        ("Table 9 hybrid aggregation", "hybrid medal counts sum to 66/225=29.3%, but Table 7 raw Any-Medal rows imply 67/225=29.8% and Table 2 prints 29.7±0.4%; the paper does not identify separate run sets", "contradiction_or_mixed_run_sets", False),
        ("Figure 1 MLAB", "figure says 1.3±0.5; Table 2 says 0.8±0.5", "contradiction", False),
        ("Figure 1 OpenHands", "figure says 5.1±1.3; Table 2 says 4.4±1.4", "contradiction", False),
        ("Figure 1 AIDE GPT-4o", "figure says 8.6±0.5; Table 2 says 8.7±0.5", "contradiction", False),
        ("Lite figure AIRA caption", "figure plots AIRA Greedy at 47.7 while caption says AIRA reported value is 0", "contradiction", False),
        ("Table 9 caption", "caption calls two baseline configurations but table has two ML-Master and two R&D-Agent columns", "scope_label_error", False),
        ("paper 90/10 selector", "paper-era source defaults ValidationSelector to 80/20", "source_default_mismatch", False),
        ("paper algorithm defaults", "planner, LLM selection, multi-trace, and critique settings are off/one by default", "paper_run_configuration_absent", False),
        ("official trace links", "two README aka.ms result links redirect to generic Bing pages at audit date", "released_trace_links_broken", False),
        ("complete public history", "3,384 commits across 231 remote branch/tag refs contain developmental diagnostics but no attributable 75-competition three-seed paper-run bundle", "bounded_negative_result_evidence", False),
        ("current README drift", "README retains v1-era table and reports hybrid 30.22±1.5, not final-paper 29.7±0.4", "release_documentation_drift", False),
        ("source compilation", "38 paper-era data-science Python files compile; compilation is not execution", "component_packaging_pass", True),
        ("paper source compilation", "v2 LaTeX compiles to 33 pages", "paper_packaging_pass", True),
        ("quant mapping boundary", "primary paper evaluates MLE-Bench; later quant scenario code is not evidence for these results", "correct_scope_boundary", True),
    ]
    return [{"check": name, "evidence": evidence, "status": status, "supports_replication": supports} for name, evidence, status, supports in checks]


def gap_rows() -> list[dict[str, str]]:
    gaps = [
        ("paper run commands", "No exact commands or environment variables for the six v2 paper runs/ablations are released."),
        ("run configuration", "No frozen config dump proves which non-default planner, scheduler, trace, selector, critique, or merge settings were used."),
        ("raw traces", "Prompts, responses, hypotheses, DAGs, generated code, validation scores, errors, and selections are absent."),
        ("result artifacts", "Complete branch/tag history contains developmental diagnostics, debug pickles, example outputs, and one run command, but no artifact is attributable to the published 75-competition three-seed runs."),
        ("broken result links", "Both advertised aka.ms result links currently resolve to generic Bing pages."),
        ("MLE-Bench snapshot", "Dockerfile clones openai/mle-bench without a commit and performs live Git LFS pulls."),
        ("Kaggle data", "The 75 competition datasets, exact versions, hashes, and access records are not archived."),
        ("competition manifest", "Exact task order, exclusions, retry policy, and Lite/Medium/High mapping artifact are absent."),
        ("model snapshots", "GPT-5, o3, GPT-4.1, o1-preview, GPT-4o, and DeepSeek deployments/revisions are not pinned."),
        ("API settings", "Temperature, top-p, max tokens, seed support, retry/backoff, timeout, and structured-output behavior are not fully pinned per role."),
        ("three seeds", "The v2 paper reports three seeds but does not list them or bind them to runs."),
        ("hardware image", "V100, 12-vCPU, and 220-GB allocations are stated but no scheduler/container digest proves the runtime image."),
        ("12-hour enforcement", "No logs establish wall-clock accounting, API wait treatment, restarts, or timeout boundaries."),
        ("90/10 holdout", "Source default is 80/20; no run override or generated split indices establish the paper's 90/10 split."),
        ("selection leakage", "The appendix selector implementation logs validation and test scores; exact held-out construction and separation from Kaggle test grading need released evidence."),
        ("baseline provenance", "Official baseline values and ML-Master re-evaluations lack pinned commits, commands, configs, seeds, and raw outputs."),
        ("cost derivation", "Token/request logs, Azure prices, currency/date, caching, retries, and failed-call accounting are absent."),
        ("RAG corpus", "The 85-competition knowledge corpus, documents, embeddings, retrieval model, and hashes are absent."),
        ("ablation configs", "Only labels are published; exact config diffs for all research/development ablations are not released."),
        ("figure inputs", "Four result figures have no plotting data or generation scripts."),
        ("v1/v2 provenance", "The report was rewritten around a new 12-hour GPT-5 experiment without a migration/result lineage document."),
        ("README/final mismatch", "The official README does not expose the final-paper GPT-5 experiment and reports different hybrid values."),
        ("statistical precision", "Only rounded raw percentages are published; at least one SEM cannot be reconstructed at displayed precision."),
        ("closed systems", "InternAgent and Neo methods/results cannot be independently audited from this repository."),
        ("quant lineage", "The retained corpus maps a quant application lineage to a general MLE-Bench primary paper; quant proxy results cannot validate this paper."),
    ]
    return [{"gap": name, "detail": detail, "impact": "prevents exact paper-level replication"} for name, detail in gaps]


def validate_inputs(source_root: Path, paper_root: Path) -> None:
    if str(run_git(source_root, "rev-parse", "HEAD")).strip() != SOURCE_CURRENT_COMMIT:
        raise RuntimeError("R&D-Agent source checkout is not at the pinned audit revision")
    expected = {
        "arxiv_api.xml": ARXIV_API_SHA256,
        "paper_v1.pdf": VERSIONS["v1"]["pdf_sha256"], "source_v1.tar": VERSIONS["v1"]["source_sha256"],
        "paper_v2.pdf": VERSIONS["v2"]["pdf_sha256"], "source_v2.tar": VERSIONS["v2"]["source_sha256"],
    }
    for name, digest in expected.items():
        if sha256(paper_root / name) != digest:
            raise RuntimeError(f"R&D-Agent primary artifact hash mismatch: {name}")
    for version, commit in (("v1", SOURCE_V1_COMMIT), ("v2", SOURCE_V2_COMMIT)):
        resolved = str(run_git(source_root, "rev-list", "-1", f"--before={VERSIONS[version]['date']}", "main")).strip()
        if resolved != commit:
            raise RuntimeError(f"R&D-Agent nearest pre-{version} source commit changed: {resolved}")


def compile_paper(paper_root: Path, latex_command: str) -> dict[str, Any]:
    executable = shutil.which(latex_command)
    if not executable:
        return {"attempted": False, "status": "latex_command_unavailable", "paper_result_credit": False}
    with tempfile.TemporaryDirectory(prefix="rd-agent-paper-") as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(paper_root / "source_v2.tar", "r:*") as archive:
            archive.extractall(tmp_path, filter="data")
        logs = ""
        codes = []
        for _ in range(2):
            proc = subprocess.run(
                [executable, "-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                cwd=tmp_path, capture_output=True, text=True, timeout=240,
            )
            codes.append(proc.returncode)
            logs += proc.stdout + "\n" + proc.stderr
        page_matches = re.findall(r"Output written on main\.pdf \((\d+) pages", logs)
        return {
            "attempted": True, "command": executable, "passes": 2, "exit_codes": codes,
            "produced_pdf": (tmp_path / "main.pdf").exists(),
            "produced_pdf_pages": int(page_matches[-1]) if page_matches else None,
            "status": "paper_latex_compiled_no_system_or_result_credit" if codes == [0, 0] else "paper_latex_compile_failed",
            "paper_result_credit": False,
        }


def interaction_kernel_execution(proposal_path: Path, component_python: str) -> dict[str, Any]:
    executable = shutil.which(component_python) if "/" not in component_python else component_python
    if not executable or not Path(executable).exists():
        return {"attempted": False, "status": "component_python_unavailable", "paper_result_credit": False}
    code = r'''
import ast
import json
import math
import sys
import torch

tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
wanted = {"_cosine_similarity_matrix_torch", "_prob_dis_torch"}
functions = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in wanted}
assert set(functions) == wanted
module = ast.Module(
    body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *functions.values()],
    type_ignores=[],
)
ast.fix_missing_locations(module)

embedding = {
    "candidate_a": [1.0, 0.0], "candidate_b": [0.0, 1.0],
    "history_low": [1.0, 0.0], "history_high": [0.0, 1.0],
}
class FakeAPI:
    def create_embedding(self, texts):
        return [embedding[text] for text in texts]
class Hypothesis:
    def __init__(self, text):
        self.hypothesis = text
namespace = {
    "math": math,
    "APIBackend": lambda: FakeAPI(),
    "get_metric_direction": lambda competition: True,
}
exec(compile(module, sys.argv[1], "exec"), namespace)
class Holder:
    pass
Holder._cosine_similarity_matrix_torch = namespace["_cosine_similarity_matrix_torch"]
Holder._prob_dis_torch = namespace["_prob_dis_torch"]
torch.manual_seed(7)
selected = Holder()._prob_dis_torch(
    0.25,
    [(Hypothesis("history_low"), 0.1), (Hypothesis("history_high"), 0.9)],
    {"a": {"hypothesis": "candidate_a"}, "b": {"hypothesis": "candidate_b"}},
    "demo",
    5,
)
assert selected and selected[0][0] == "history_high"
print(json.dumps({"passed": True, "selected_count": len(selected), "best_history": selected[0][0]}))
'''
    proc = subprocess.run(
        [str(executable), "-c", code, str(proposal_path)],
        capture_output=True, text=True, timeout=120,
    )
    parsed: dict[str, Any] = {}
    if proc.returncode == 0:
        parsed = json.loads(proc.stdout.strip().splitlines()[-1])
    return {
        "attempted": True,
        "python": str(executable),
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0 and parsed.get("passed") is True,
        "selected_count": parsed.get("selected_count"),
        "best_history": parsed.get("best_history"),
        "stderr_tail": proc.stderr[-1000:],
        "status": "exact_paper_era_source_methods_executed" if proc.returncode == 0 else "interaction_kernel_component_failed",
        "scope": "AST-extracted native _cosine_similarity_matrix_torch and _prob_dis_torch methods with deterministic synthetic embeddings",
        "paper_result_credit": False,
    }


def source_component_execution(source_root: Path, component_python: str) -> dict[str, Any]:
    archive_bytes = run_git(source_root, "archive", SOURCE_V2_COMMIT, binary=True)
    with tempfile.TemporaryDirectory(prefix="rd-agent-source-") as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
            archive.extractall(tmp_path, filter="data")
        paths = [
            tmp_path / "rdagent/app/data_science",
            tmp_path / "rdagent/scenarios/data_science",
            tmp_path / "rdagent/scenarios/kaggle",
        ]
        py_files = sorted(path for root in paths for path in root.rglob("*.py"))
        compiled = all(compileall.compile_file(str(path), quiet=2, force=True) for path in py_files)

        scheduler_path = tmp_path / "rdagent/scenarios/data_science/proposal/exp_gen/trace_scheduler.py"
        package = types.ModuleType("rdagent")
        package.__path__ = []  # type: ignore[attr-defined]
        log_module = types.ModuleType("rdagent.log")
        log_module.rdagent_logger = types.SimpleNamespace(info=lambda *args, **kwargs: None)
        old_package, old_log = sys.modules.get("rdagent"), sys.modules.get("rdagent.log")
        try:
            sys.modules["rdagent"] = package
            sys.modules["rdagent.log"] = log_module
            spec = importlib.util.spec_from_file_location("rdagent_trace_scheduler_audit", scheduler_path)
            if not spec or not spec.loader:
                raise RuntimeError("could not load scheduler source")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            scheduler = module.ProbabilisticScheduler(max_trace_num=2, temperature=1.0)
            probabilities = scheduler._softmax_probabilities([1.0, 2.0, 3.0])
            scheduler_passed = len(probabilities) == 3 and math.isclose(sum(probabilities), 1.0, abs_tol=1e-12) and probabilities[0] < probabilities[1] < probabilities[2]
        finally:
            if old_package is None:
                sys.modules.pop("rdagent", None)
            else:
                sys.modules["rdagent"] = old_package
            if old_log is None:
                sys.modules.pop("rdagent.log", None)
            else:
                sys.modules["rdagent.log"] = old_log
        return {
            "paper_era_commit": SOURCE_V2_COMMIT,
            "data_science_and_kaggle_python_files_compiled": len(py_files), "compileall_passed": compiled,
            "native_scheduler_softmax_executed": True, "native_scheduler_softmax_passed": scheduler_passed,
            "native_scheduler_softmax_output": probabilities,
            "native_interaction_kernel_execution": interaction_kernel_execution(
                tmp_path / "rdagent/scenarios/data_science/proposal/exp_gen/proposal.py",
                component_python,
            ),
            "scope": "paper-era data-science/Kaggle compilation plus dependency-isolated scheduler and interaction-kernel components",
            "paper_result_credit": False,
        }


def render_readme(manifest: Mapping[str, Any]) -> str:
    return f"""# R&D-Agent paper-replication audit

This audit uses the final 33-page arXiv v2 report as the result authority and pins both paper revisions, the official repository at the last commit before each revision, and its complete public branch/tag path history. It is fail-closed: source-code presence, paper compilation, isolated component execution, and unattributed developmental outputs do not substitute for the reported 75-competition, three-seed experiments.

## Honest result

- **Full paper reproduced:** no.
- **Displayed numeric table cells reproduced:** 0 / {manifest['paper_numeric_table_cells_total']}.
- **Unique numeric measurements reproduced:** 0 / {manifest['paper_unique_numeric_measurements_total']}.
- **Result-figure series/bars reproduced from native data:** 0 / {manifest['paper_figure_series_total']}.
- **Paper mechanisms with identifiable source implementations:** {manifest['paper_mechanisms_with_source_implementation']} / {manifest['paper_mechanisms_total']}.
- **Paper mechanisms verified as used in a reported run:** 0 / {manifest['paper_mechanisms_total']}.
- **Paper configurations verified for a reported run:** 0 / {manifest['paper_configurations_total']}.

The repository contains meaningful paper-era MLE code, including the paper's interaction kernel, research DAG machinery, schedulers, coding/evaluation workflow, and selectors. That is implementation evidence, not result evidence: no frozen run configuration, prompts/responses, generated code, data snapshot, seeds, submissions, checkpoints, or traces link the released alternatives to the published tables.

## Scope correction

The cited primary record is the general **R&D-Agent** MLE-Bench report. It is not the separate R&D-Agent-Quant paper. The corpus system mapping describes a later quant application lineage, but quant code or the existing JKP factor proxy cannot validate this paper's MLE-Bench claims.

## Revision and release drift

The 7-page v1 paper reports 32 numeric cells from 24-hour runs using o1 and o3/GPT-4.1, with five or six seeds and standard deviations. The 33-page v2 is effectively a new experiment: 12-hour GPT-5/hybrid runs, three seeds, SEMs, ablations, raw runs, costs, and per-competition medal counts. Its 534 displayed numeric table cells represent 526 unique measurements. The current README still presents v1-era results and a hybrid value of 30.22±1.5, while v2 reports 29.7±0.4 and a new GPT-5 result of 35.1±0.4.

## Complete public-history boundary

The audit now walks {manifest['public_source_history_remote_refs']} pinned remote refs, {manifest['public_source_history_reachable_commits']} reachable commits, and {manifest['public_source_history_unique_changed_paths']} unique historical paths. It inspects {manifest['public_source_history_keyword_paths']} paths whose names mention results, outputs, logs, traces, checkpoints, submissions, or scores and records fifteen bounded artifact candidates byte-for-byte.

That history corrects an earlier overstatement: developmental artifacts do exist. They include three pre-v1 competition CSVs, five between-version diagnostics with 39 competitions each, two debug-LLM pickles inventoried without deserialization, one example solution, pre-paper metadata, one post-v2 run command, and an unrelated post-v2 AutoRL result. None carries the paper's 75-competition manifest, three seeds, model/config lineage, or published table outputs. They receive zero paper-result credit, but their existence is now explicit rather than hidden behind a blanket “no outputs” claim.

## What ran

The v2 LaTeX source compiled twice to a 33-page PDF. All 233 paper-era Python files across the data-science and Kaggle MLE paths compiled, the native probabilistic scheduler's softmax helper executed, and the exact paper-era interaction-kernel methods executed with deterministic synthetic embeddings. These checks earn component-packaging credit only and zero published-result credit.

## Why the reported experiment did not run

An exact run is not presently specified or provisioned. The paper requires 75 Kaggle datasets, three 12-hour runs per main configuration plus ablations, Azure model deployments, a V100-class environment, and frozen MLE-Bench grading. The release's MLE-Bench Dockerfile performs an unpinned live clone; paper-era defaults also disable the planner and LLM selector, set one trace, and default holdout selection to 80/20 rather than the paper's 90/10. Both advertised result-trace links now redirect to generic Bing pages. Running a guessed modern configuration would be expensive but would not be a faithful replication.

## Material internal inconsistencies

The main text says ML-Master/GPT-5 achieves 16.9±2.0, while Table 2 and Figure 1 say 16.9±1.2. Figure 1 disagrees with Table 2 for MLAB, OpenHands, and AIDE/GPT-4o. The backend appendix gives the hybrid system 29.3%, versus 29.7±0.4 in Table 2. Table 9's hybrid medal counts also total 29.3%, whereas Table 7's raw rows imply 29.8%, demonstrating that unidentified run sets were mixed. The Lite figure plots AIRA Greedy at 47.7 even though its caption says AIRA is shown as zero. Rounded hybrid raw runs imply a 0.5 Valid-Submission SEM while the summary prints 0.4. Hidden precision may explain the SEM alone, but no provenance artifact resolves the broader differences.
"""


def audit(source_root: Path, paper_root: Path, output: Path, latex_command: str, component_python: str) -> dict[str, Any]:
    validate_inputs(source_root, paper_root)
    table = paper_table_rows(paper_root)
    unique = unique_measurement_rows(table)
    figures = figure_rows()
    versions = version_rows()
    mechanisms = mechanism_rows(source_root)
    configs = config_rows(source_root)
    snapshots = source_snapshot_rows(source_root)
    history, history_paths, history_artifacts = public_source_history(source_root)
    assets = paper_asset_rows(paper_root)
    checks = internal_check_rows()
    gaps = gap_rows()
    native = {
        "official_source_url": SOURCE_URL,
        "full_native_paper_execution_attempted": False,
        "full_native_paper_execution_status": "not_runnable_faithfully_missing_frozen_inputs_run_configs_models_credentials_compute_and_traces",
        "credential_presence": {
            name: bool(os.environ.get(name)) for name in ("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "KAGGLE_USERNAME", "KAGGLE_KEY")
        },
        "docker_command_available": shutil.which("docker") is not None,
        "singularity_or_apptainer_available": bool(shutil.which("singularity") or shutil.which("apptainer")),
        "paper_source_compilation": compile_paper(paper_root, latex_command),
        "released_source_component_execution": source_component_execution(source_root, component_python),
        "paper_result_credit": False,
    }
    links = [
        {"label": "o1-preview detailed results", "url": "https://aka.ms/RD-Agent_MLE-Bench_O1-preview", "audit_date": AUDIT_DATE, "resolved_url": "https://www.bing.com/?ref=aka&shorturl=RD-Agent_MLE-Bench_O1-preview", "status": "broken_redirect_to_generic_bing_no_trace_artifact", "paper_result_credit": False},
        {"label": "o3+GPT-4.1 detailed results", "url": "https://aka.ms/RD-Agent_MLE-Bench_O3_GPT41", "audit_date": AUDIT_DATE, "resolved_url": "https://www.bing.com/?ref=aka&shorturl=RD-Agent_MLE-Bench_O3_GPT41", "status": "broken_redirect_to_generic_bing_no_trace_artifact", "paper_result_credit": False},
    ]

    output.mkdir(parents=True, exist_ok=True)
    csv_outputs = {
        "paper_numeric_table_conformance.csv": table,
        "paper_unique_measurement_conformance.csv": unique,
        "paper_figure_series_inventory.csv": figures,
        "paper_v1_result_inventory.csv": versions,
        "paper_version_summary.csv": version_summary_rows(),
        "paper_source_asset_inventory.csv": assets,
        "released_source_snapshot_summary.csv": snapshots,
        "public_source_history_path_inventory.csv": history_paths,
        "public_source_history_artifact_candidates.csv": history_artifacts,
        "released_source_mechanism_conformance.csv": mechanisms,
        "released_source_config_conformance.csv": configs,
        "released_result_link_status.csv": links,
        "paper_internal_and_source_checks.csv": checks,
        "paper_specification_gaps.csv": gaps,
    }
    for name, rows in csv_outputs.items():
        write_csv(output / name, rows)
    (output / "native_execution.json").write_text(json.dumps(native, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "public_source_history.json").write_text(
        json.dumps(history, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest: dict[str, Any] = {
        "audit_date": AUDIT_DATE,
        "paper": "R&D-Agent: An LLM-Agent Framework Towards Autonomous Data Science",
        "paper_result_authority": "arXiv v2 (2025-10-01)",
        "paper_url": ARXIV_URL,
        "paper_hashes": {f"arxiv_{version}_{kind}": data[f"{kind}_sha256"] for version, data in VERSIONS.items() for kind in ("pdf", "source")},
        "official_source_url": SOURCE_URL,
        "official_source_revision_audited": SOURCE_CURRENT_COMMIT,
        "paper_era_source_revision": SOURCE_V2_COMMIT,
        "overall_status": "paper_specification_source_and_full_history_audited_zero_native_results_missing_attributable_run_artifacts",
        "full_paper_reproduced": False,
        "paper_numeric_table_cells_total": len(table),
        "paper_numeric_table_cells_with_paper_result_credit": 0,
        "paper_unique_numeric_measurements_total": len(unique),
        "paper_unique_numeric_measurements_with_paper_result_credit": 0,
        "paper_result_figure_assets_total": len(FIGURES),
        "paper_figure_series_total": len(figures),
        "native_exact_figure_series_reproduced": 0,
        "paper_mechanisms_total": len(mechanisms),
        "paper_mechanisms_with_source_implementation": sum(bool(row["required_source_tokens_found"]) for row in mechanisms),
        "paper_mechanisms_verified_as_executed_in_reported_run": 0,
        "paper_configurations_total": len(configs),
        "paper_configurations_verified_for_reported_run": 0,
        "public_source_history_remote_refs": history["remote_refs"],
        "public_source_history_reachable_commits": history["reachable_commits"],
        "public_source_history_unique_changed_paths": history["unique_historical_changed_paths"],
        "public_source_history_keyword_paths": history["keyword_paths"],
        "public_source_history_artifact_candidates_inspected": history[
            "bounded_artifact_candidates_inspected"
        ],
        "public_source_history_attributable_paper_run_artifacts": history[
            "attributable_published_run_artifacts"
        ],
        "paper_result_cells_reproduced_from_public_history": history[
            "paper_result_cells_reproduced_from_history"
        ],
        "paper_specification_gaps_total": len(gaps),
        "v1_numeric_table_cells": len(versions),
        "v2_numeric_table_cells": len(table),
        "paper_source_assets_total": len(assets),
        "paper_source_v2_latex_compiled": native["paper_source_compilation"]["exit_codes"] == [0, 0],
        "paper_era_data_science_and_kaggle_python_files_compiled": native["released_source_component_execution"]["data_science_and_kaggle_python_files_compiled"],
        "paper_era_scheduler_component_executed": native["released_source_component_execution"]["native_scheduler_softmax_passed"],
        "paper_era_interaction_kernel_executed": native["released_source_component_execution"]["native_interaction_kernel_execution"]["passed"],
        "primary_record_scope": "general MLE-Bench R&D-Agent report; not the separate R&D-Agent-Quant paper",
    }
    (output / "README.md").write_text(render_readme(manifest), encoding="utf-8")
    output_names = [
        *csv_outputs,
        "native_execution.json",
        "public_source_history.json",
        "README.md",
    ]
    manifest["output_sha256"] = {name: sha256(output / name) for name in sorted(output_names)}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--latex-command", default="pdflatex")
    parser.add_argument("--component-python", default=sys.executable)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = audit(args.source_root, args.paper_root, args.output, args.latex_command, args.component_python)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
