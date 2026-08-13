#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for AlphaAgentEvo."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphaagentevo_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/alphaagentevo"
WORK_ID = "CensusORlNmZrawUMu"
SYSTEM_ID = "SYS-ALPHA-AGENT-EVO"
OPENREVIEW_ID = "lNmZrawUMu"
PDF_PATH = "/pdf/28185b019d6214870be8b91f7be88b8d019eeda9.pdf"
SUPPLEMENT_PATH = "/attachment/4a42ab9dd0ce0fd252223eab6a143bbcf681ae63.zip"

PINS = {
    "discovery/openreview-current.pdf": "5d26b8d22ef091fb89e1ae2b968821092f6f6b6ccc048f95b365713c4b182fd5",
    "discovery/openreview-current-clean.txt": "d70bde9bf247d7553914802168ec797dbb27f9994f09aca0ea23f8cda4819bd9",
    "render/contact-1.jpg": "52fdbd614e86c61c3d6af90738e424dc45978c92d60e0f5a7e1e2b794b56b2f6",
    "render/contact-2.jpg": "c67bc55cbf1b9de3043cee11f6e07bb8c550ab760f98b8c03ae1c0c9b6d9c0e7",
    "discovery/PuLam__alphaagentevo-v2-0.6B-api.json": "e1d87fa606ed8ed7db884170661c0601c477aa024fcf614b3275fa5ce762ed2b",
    "discovery/PuLam__alphaagentevo-v2-0.6B-commits.json": "536c25d9441b9e18749f79c1939148b4c1214087c858f878bcc546b3dc7ffa18",
    "discovery/nguyenha0501__alphaagentevo-qwen3-4b-v2-api.json": "34996cb555e2f824f4384c0dd826575c1edf15de42efa36fa8d335bbb0b756ce",
    "discovery/nguyenha0501__alphaagentevo-qwen3-4b-v2-commits.json": "e323a381b4c41ca00938453638cae02f998d5f91f297267dc8ce5282db4f4447",
    "candidates/nguyenha-source/config/factor_tool.py": "b907c04d070cfb6c8db3e912c936d8a0abef354da228088845bfba357ba816e6",
    "candidates/nguyenha-source/config/factor_reward_v2.py": "d82b72cc4d7060e95c102ba512c61e2023c3aaf881af8c3d9d7a0800232b7c90",
    "candidates/nguyenha-source/config/train.sh": "9def055e08af49eea98c0cd0f746901f905be75b7b360a48ec6f4e03f3a80cb5",
    "candidates/nguyenha-source/config/train.parquet": "c012c7de6b89834086541b69df423861ea65ae120c5096bf3f14652e47c8ac00",
    "candidates/nguyenha-source/config/val.parquet": "319955511de4d29b97cbdc9193b49bc6df4437b513c0f9a56bcf2d0456027f30",
    "candidates/nguyenha-source/config/test.parquet": "0bd385b72e5b941f5d5f4654877b6e83769ce4665cfa6fbd62c0f7fe636b854e",
    "candidates/nguyenha-source/data/train.parquet": "5ef7682f7c3636637e8b0bf407dfa078f8856fd21dd5c638cfc743c4a4227ad5",
    "candidates/nguyenha-source/data/val.parquet": "70401ebf060b3d57bc3536be0fc97795f1633b5d5d25660fc72d30b6ccc27b12",
    "candidates/nguyenha-source/logs/train.live.log": "2110a57797bc2af294f987fff7a666c59b3322795a092dbb09495582b93ba3f0",
    "candidates/nguyenha-source/logs/train.pretty.log": "48f547e528d6583229b9a8f8149d01f03a52f901e8da9d4ae6fe7c73b8cf6ce7",
    "candidates/nguyenha-source/logs/api.log": "c182243cb867ebd41150a371484fc59702d7f4dfc1ebd0bf2a798ae70111c2d7",
}

TABLES = {
    "table_1_alphaevo500": (10, 6, 60),
    "table_2_alpha158": (11, 6, 66),
    "table_3_multifactor_portfolio": (7, 3, 21),
}

TABLE_VALUES = {
    "table_1_alphaevo500": (
        "0.676 0.08 0.11 0.657 0.35 0.43 0.942 0.36 0.47 0.951 0.68 0.78 "
        "0.970 0.75 0.88 0.972 0.73 0.82 0.872 0.68 0.71 0.886 0.71 0.86 "
        "0.864 0.74 0.78 0.851 0.66 0.74 0.954 0.75 0.81 0.961 0.73 0.76 "
        "0.992 0.87 0.90 0.971 0.86 0.91 0.977 0.83 0.87 0.978 0.82 0.88 "
        "0.940 0.77 0.90 0.923 0.76 0.78 0.979 0.97 0.97 0.977 0.93 0.95"
    ).split(),
    "table_2_alpha158": (
        "0.766 0.000 0.074 0.823 0.003 0.003 0.714 0.000 0.058 0.713 0.125 0.132 "
        "0.619 0.022 0.024 0.633 0.094 0.107 0.905 0.236 0.495 0.900 0.643 0.783 "
        "0.975 0.294 0.550 0.966 0.750 0.848 0.714 0.100 0.113 0.674 0.500 0.543 "
        "0.792 0.350 0.450 0.974 0.848 0.856 0.889 0.327 0.519 0.874 0.872 0.943 "
        "0.988 0.156 0.293 0.975 0.828 0.903 0.952 0.506 0.613 0.917 0.909 0.926 "
        "0.982 0.581 0.725 0.982 0.963 0.994"
    ).split(),
    "table_3_multifactor_portfolio": (
        "-0.009 1.192 -0.195 0.013 1.977 -0.182 0.027 1.815 -0.192 "
        "0.064 2.046 -0.196 -0.158 0.587 -0.213 -0.027 1.532 -0.215 0.129 2.442 -0.176"
    ).split(),
}

FIGURES = (
    ("figure_1_evolution_approaches", 1, 0, 0, "qualitative approach comparison"),
    ("figure_2_framework", 2, 0, 0, "trajectory and on-policy RL framework"),
    ("figure_3_trajectories", 2, 2, 0, "IR/evolution and exploration/consistency trajectories"),
    ("figure_4_ablation", 3, 3, 16, "validity and reward-component pass-rate ablations"),
    ("figure_5_similarity", 7, 7, 14, "seed and six model similarity matrices with avg/max annotations"),
    ("figure_6_out_of_sample", 4, 4, 2, "four out-of-sample AER/IR violin panels; two selection-control IR values in prose"),
    ("figure_7_training_statistics", 3, 3, 0, "reward, response length, and output entropy trajectories"),
    ("figure_8_case_study", 8, 2, 8, "two model-turn trajectories with eight displayed IR tool results"),
)

FIGURE_VALUES = {
    "figure_4_ablation": "0.938 0.973 0.923 0.960 0.54 0.51 0.65 0.67 0.70 0.76 0.513 0.510 0.581 0.706 0.660 0.725".split(),
    "figure_5_similarity": "0.043 0.722 0.039 0.263 0.040 0.219 0.043 0.583 0.039 0.600 0.058 0.333 0.083 0.818".split(),
    "figure_6_out_of_sample": "1.05 2.72".split(),
    "figure_8_case_study": "-0.3529 -0.0793 -0.4712 -0.8117 0.9417 0.6739 0.543 1.1863".split(),
}

# Some exact annotations live only inside rasterized plots. The complete
# FIGURE_VALUES ledger is visually transcribed from inspected renders; this
# subset must additionally survive machine text extraction.
FIGURE_TEXT_VALUES = {
    "figure_4_ablation": FIGURE_VALUES["figure_4_ablation"],
    "figure_5_similarity": "0.043 0.722 0.039 0.263 0.583 0.600 0.058".split(),
    "figure_6_out_of_sample": FIGURE_VALUES["figure_6_out_of_sample"],
    "figure_8_case_study": FIGURE_VALUES["figure_8_case_study"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    if len(PdfReader(scratch / "discovery/openreview-current.pdf").pages) != 18:
        raise ValueError("official manuscript page count changed")
    text = (scratch / "discovery/openreview-current-clean.txt").read_text(errors="replace")
    for title, values in TABLE_VALUES.items():
        expected = TABLES[title][2]
        if len(values) != expected or any(value not in text for value in values):
            raise ValueError(f"published values changed for {title}")
    for title, values in FIGURE_TEXT_VALUES.items():
        if any(value not in text for value in values):
            raise ValueError(f"figure annotations changed for {title}")
    source = scratch / "candidates/nguyenha-source/config"
    python_files = sorted(source.rglob("*.py"))
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {"text": text, "candidate_python_files": python_files}


def result_rows() -> list[dict[str, Any]]:
    blocker = (
        "author AlphaEvo500 splits, exact evaluator/data snapshot, prompts, trajectories, "
        "checkpoints, portfolios, raw arrays, and paper experiment package are unrecovered"
    )
    rows = []
    for table, values in TABLE_VALUES.items():
        for index, value in enumerate(values, 1):
            rows.append({
                "table": table, "printed_numeric_unit": index, "printed_value": value,
                "source_document_recovered": True,
                "author_native_experiment_executed": False,
                "published_result_regenerated": False,
                "paper_result_credit": False,
                "blocking_reason": blocker,
            })
    return rows


def figure_rows() -> list[dict[str, Any]]:
    return [{
        "figure": figure, "display_panels": panels, "empirical_panels": empirical,
        "printed_numeric_annotations": numeric, "description": description,
        "rendered_author_asset_recovered": True,
        "underlying_numeric_arrays_recovered": False,
        "author_native_figure_regenerated": False,
        "paper_result_credit": False,
    } for figure, panels, empirical, numeric, description in FIGURES]


def figure_numeric_rows() -> list[dict[str, Any]]:
    rows = []
    for figure, values in FIGURE_VALUES.items():
        for index, value in enumerate(values, 1):
            rows.append({
                "figure": figure, "printed_numeric_annotation": index,
                "printed_value": value, "underlying_array_recovered": False,
                "published_annotation_regenerated": False, "paper_result_credit": False,
            })
    return rows


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official_manuscript", "complete", "accepted 18-page ICLR 2026 OpenReview PDF recovered and visually checked"),
        ("official_source", "not_recovered", "no accepted-version TeX/source archive was exposed by the primary record"),
        ("supplement", "listed_but_currently_unrecoverable", f"primary record lists ZIP {SUPPLEMENT_PATH}; signed-in immutable access returned 404 and logical/API access was blocked"),
        ("paper_specific_release", "missing", "no paper-author implementation, checkpoint, dataset, or result package found"),
        ("dataset", "specified_not_released", "AlphaEvo500 is 350/50/100 and Alpha158 is external; supplement promises files/splits but was not recovered"),
        ("market_and_period", "specified_not_frozen", "HS300/CSI500, 2023-01 through 2025-11 periods specified without point-in-time market panel"),
        ("portfolio", "partially_specified", "cross-sectional top 10 percent, five-trading-day rebalance; weighting/cost/slippage details are incomplete"),
        ("agent_and_tools", "paper_specification_only", "multi-turn policy, four offspring/tool calls, evaluator schema and operator appendix described without native implementation"),
        ("model_training", "partially_specified", "Qwen3 1.7B/4B, Verl, 10 RTX4090, 150 steps, GRPO-related settings disclosed without exact environment/checkpoints"),
        ("reward", "equation_specified_with_ambiguity", "five-part capped hierarchy printed, but the tool-cost denominator can be zero or negative and no floor/sign handling is stated"),
        ("prompts_and_trajectories", "not_released", "schematic tool prompt and one rendered case study are not exact filled training/evaluation calls or complete trajectories"),
        ("baselines", "named_not_replayable", "GP, AlphaAgent, Qwen3, ToolRL, GEPA, GPT-5-mini, DeepSeek-R1 and portfolio baselines lack complete pinned configs/outputs"),
        ("replications_and_uncertainty", "not_released", "no repeat count, seeds, uncertainty intervals, significance tests, or per-run output arrays"),
        ("published_results", "not_regenerated", "zero of 147 table units, zero of 21 empirical panels, and zero of 40 exact figure annotations regenerated"),
        ("search_for_release", "no_attributable_public_implementation_found", "two post-publication Hugging Face candidates are unaffiliated and receive no native credit"),
    )
    return [{"dimension": d, "status": status, "detail": detail} for d, status, detail in specs]


def internal_rows() -> list[dict[str, str]]:
    specs = (
        ("document_render", "all_pages_readable", "18/18 pages visually checked; zero unreadable, clipped, overlapping, blank, or missing research pages"),
        ("supplement_release", "listed_but_not_retrievable", "accepted record lists dataset splits and full training/evaluation source, but the archive is currently unrecovered"),
        ("reward_denominator", "specification_ambiguity", "R_tool=0 or R_tool<0 makes the printed ratio undefined or directionally anomalous; no paper floor is stated"),
        ("training_checkpoint", "specified", "paper trains 150 steps and says the step-80 checkpoint is used for testing"),
        ("llm_disclosure", "scope_conflict", "method is LLM-based while the disclosure says LLMs were used only for writing polish/grammar/visualization code; likely form wording but literally inconsistent"),
        ("historical_versions", "bounded_gap", "OpenReview says no revisions, while indexed historic immutable PDF hashes were not recoverable; accepted active manuscript is pinned"),
        ("third_party_0_6b", "unattributable_task_mismatch", "PuLam step-50 0.6B checkpoint postdates publication and has no paper-author/model-card linkage; paper evaluates 1.7B/4B step 80"),
        ("third_party_4b", "unattributable_task_mismatch", "nguyenha0501 release postdates publication, has no paper-author/model-card linkage, and trains Vietnam-market factors"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def candidate_audit(scratch: Path, python_files: list[Path]) -> dict[str, Any]:
    discovery = scratch / "discovery"
    pulam = json.loads((discovery / "PuLam__alphaagentevo-v2-0.6B-api.json").read_text())
    nguyen = json.loads((discovery / "nguyenha0501__alphaagentevo-qwen3-4b-v2-api.json").read_text())
    config = scratch / "candidates/nguyenha-source/config"
    data = scratch / "candidates/nguyenha-source/data"
    parquet = {
        split: pd.read_parquet(config / f"{split}.parquet")
        for split in ("train", "val", "test")
    }
    if [len(parquet[x]) for x in ("train", "val", "test")] != [300, 30, 99]:
        raise ValueError("third-party dataset row counts changed")
    if not pd.read_parquet(data / "train.parquet").equals(parquet["train"]):
        raise ValueError("third-party duplicated train data changed")
    if not pd.read_parquet(data / "val.parquet").equals(parquet["val"]):
        raise ValueError("third-party duplicated validation data changed")
    prompts = "\n".join(str(x) for frame in parquet.values() for x in frame["prompt"])
    if "Vietnam stock market" not in prompts:
        raise ValueError("third-party market prompt changed")
    train_sh = (config / "train.sh").read_text()
    reward = (config / "factor_reward_v2.py").read_text()
    tool = (config / "factor_tool.py").read_text()
    log = (scratch / "candidates/nguyenha-source/logs/train.live.log").read_text(errors="replace")
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    steps = [int(x) for x in re.findall(r"TaskRunner[^\n]*?\bstep:(\d+) - global_seqlen", log)]
    checkpoints = sorted({int(x) for x in re.findall(r"global_step_(\d+)", log)})
    calls = [int(x) for x in re.findall(r"\[factor-live\].*?call=(\d+)/4", log)]
    validation = {}
    for step in range(10, 100, 10):
        match = re.search(
            rf"TaskRunner[^\n]*?step:{step} - .*?val-core/alphaagentevo/reward/mean@3:([-+]?\d+\.\d+)",
            log,
        )
        if match:
            validation[str(step)] = float(match.group(1))
    required = {
        "MODEL": "Qwen/Qwen3-4B-Thinking-2507",
        "ROLLOUT_N": "3", "MAX_ASSISTANT_TURNS": "2",
        "MAX_TOOL_CALLS_PER_TURN": "4", "LEARNING_RATE": "1e-6", "KL_COEF": "0.001",
    }
    for key, value in required.items():
        if f'{key}="${{{key}:-{value}}}"' not in train_sh:
            raise ValueError(f"third-party train default changed for {key}")
    return {
        "native_paper_credit": False,
        "paper_author_identity_matches": 0,
        "candidates": [
            {
                "repository": pulam["id"], "commit": pulam["sha"],
                "created_at": pulam["createdAt"], "last_modified": pulam["lastModified"],
                "attribution": "PuLam; no paper-author identity, paper link, or model card",
                "paper_mismatch": "0.6B step-50 checkpoint versus paper 1.7B/4B step-80 evaluation",
                "native_paper_credit": False,
            },
            {
                "repository": nguyen["id"], "commit": nguyen["sha"],
                "created_at": nguyen["createdAt"], "last_modified": nguyen["lastModified"],
                "attribution": "nguyenha0501; no paper-author identity, paper link, or model card",
                "paper_mismatch": "Vietnam factors, 300/30/99 splits, custom reward, two turns, four-GPU partial run",
                "native_paper_credit": False,
            },
        ],
        "nguyenha_source": {
            "api_sibling_entries": len(nguyen.get("siblings", [])),
            "python_files_parsed": len(python_files),
            "dataset_rows": {key: len(value) for key, value in parquet.items()},
            "paper_dataset_rows": {"train": 350, "val": 50, "test": 100},
            "prompt_market": "Vietnam stock market",
            "config_dataframes_equal": {"train": True, "val": True},
            "training_model": "Qwen/Qwen3-4B-Thinking-2507",
            "training_gpus": 4,
            "requested_steps": 150,
            "completed_unique_steps": len(set(steps)),
            "last_completed_step": max(steps),
            "checkpoint_steps": checkpoints,
            "reached_training_100_percent": "Training Progress: 100%" in log,
            "final_validation_emitted": "Final validation metrics:" in log,
            "termination": "Gloo recv barrier timeout after 1,800,000 ms",
            "successful_backtests_logged": log.count("[FactorTool] backtest success"),
            "tool_call_events": len(calls),
            "tool_call_numbers_above_declared_four": sum(value > 4 for value in calls),
            "maximum_logged_call_number": max(calls),
            "validation_reward_mean_at_3": validation,
            "active_scalar_reward": "format 0-0.3 plus best-IR quality 0-0.7 workaround",
            "paper_five_component_reward_active": False,
            "reward_source_declares_tool_reward_pipeline_bug": "tool rewards" in reward and "don't reach" in reward,
            "tool_similarity_fallback_is_sequence_matcher": "SequenceMatcher" in tool,
            "paper_ast_similarity_dependency_shipped": False,
            "backtest_server_or_backend_shipped": False,
            "license_or_readme_shipped": False,
            "adds_unstated_tool_denominator_floor": "R_TOOL_FLOOR" in tool,
            "adds_unstated_reward_clip": "clip" in tool.lower(),
            "adds_unstated_high_similarity_threshold": "H_HIGH" in tool,
        },
        "bounded_negative_inference": (
            "No attributable public AlphaAgentEvo release was found in the pinned primary record or "
            "bounded public checkpoint search; this does not prove private, deleted, or unindexed artifacts never existed."
        ),
    }


def readme() -> str:
    return """# AlphaAgentEvo paper/source and public-release audit

This audit pins the accepted 18-page ICLR 2026 OpenReview manuscript for
`lNmZrawUMu`. All 18 pages were rendered and visually checked; no unreadable,
clipped, overlapping, blank, or missing research content was found. The paper
is fully readable and unusually detailed about its intended method, but that
is document evidence rather than an experimental replication.

The accepted paper reports 147 exact numeric units across Tables 1--3, 21
empirical panels across Figures 3--8, and 40 exact numeric figure/case-study
annotations. The PDF supplies none of the underlying result arrays. The
OpenReview record lists a supplementary ZIP, and the reproducibility statement
says it contains dataset files and the complete training/evaluation source.
The signed-in immutable path currently returns 404 while logical/API access is
blocked. This proves that a supplement was listed; it must not be represented
as inspected or presumed never to have existed.

No paper-author repository, checkpoint, dataset, or result package was found.
Two post-publication Hugging Face candidates were pinned, but neither author
matches a paper author and neither has a paper link or model card. PuLam's
artifact is a 0.6B step-50 checkpoint, not either paper model. The more
substantial nguyenha0501 package uses Vietnam-market prompts and 300/30/99
splits rather than AlphaEvo500's 350/50/100 HS300/CSI500 split. Its active
scalar reward is a formatting-plus-best-IR workaround, not the paper's
five-component hierarchy. It ran Qwen3-4B-Thinking-2507 on four GPUs through
step 90 of 150 and then died in a 30-minute Gloo barrier timeout; it never
emitted final validation or paper pass-rate outputs. The checkpoint tree also
omits the expression parser and backtest server/backend imported by its
training integration, as well as a README or license. Logged tool-call counters
reached 33 despite the declared four-call cap. It is useful independent
diagnostic work and receives zero native-paper credit.

The paper itself leaves a material mathematical ambiguity: its tool-cost term
can be zero or negative, yet it is used as a denominator and no floor or sign
handling is stated. The third-party candidate silently adds a floor and other
reward rules, which makes it more numerically defined but less faithful.

Accordingly, 0/147 table units, 0/21 empirical panels, and 0/40 exact figure
annotations have been regenerated by an author-native pipeline. The local
monthly characteristic portfolio remains a clearly labeled favorable motif
proxy: it receives no AlphaAgentEvo mechanism or result credit. Maximum honest
faithfulness is currently the accepted paper specification plus this explicit
artifact/access boundary, not a claimed true replication.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inputs = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    results = result_rows()
    figures = figure_rows()
    figure_numbers = figure_numeric_rows()
    candidates = candidate_audit(scratch, inputs["candidate_python_files"])
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "figure_numeric_ledger.csv", figure_numbers)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", internal_rows())
    write_json(output / "candidate_release_audit.json", candidates)
    write_json(output / "source_provenance.json", {
        "work_id": WORK_ID, "system_id": SYSTEM_ID,
        "openreview": {
            "forum_id": OPENREVIEW_ID, "venue": "ICLR 2026 Poster",
            "published": "2026-01-26", "last_modified": "2026-04-11",
            "license": "CC BY 4.0", "official_pdf_immutable_path": PDF_PATH,
            "official_pdf_sha256": PINS["discovery/openreview-current.pdf"],
            "official_pages": 18, "supplement_listed": True,
            "supplement_immutable_path": SUPPLEMENT_PATH,
            "supplement_recovered": False,
            "supplement_access_observation": "signed-in immutable path 404; logical/API access blocked",
            "visual_qa": {
                "pages_inspected": 18,
                "unreadable_clipped_overlapping_blank_or_missing_pages": 0,
                "contact_sheet_sha256": {
                    "contact-1.jpg": PINS["render/contact-1.jpg"],
                    "contact-2.jpg": PINS["render/contact-2.jpg"],
                },
            },
        },
        "candidate_release_audit": candidates,
        "release_boundary": {
            "attributable_alphaagentevo_source_recovered": False,
            "complete_research_inputs_recovered": False,
            "published_result_lineage_recovered": False,
            "third_party_checkpoints_counted_as_native": False,
        },
    })
    (output / "README.md").write_text(readme(), encoding="utf-8")
    manifest = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "openreview_id": OPENREVIEW_ID,
        "official_pdf_recovered": True, "official_pages_visually_checked": 18,
        "official_source_recovered": False,
        "official_supplement_listed": True, "official_supplement_recovered": False,
        "attributable_alphaagentevo_code_recovered": False,
        "published_numeric_result_units": len(results), "native_numeric_units_regenerated": 0,
        "figures": len(figures), "display_panels": sum(row["display_panels"] for row in figures),
        "empirical_panels": sum(row["empirical_panels"] for row in figures),
        "native_empirical_panels_regenerated": 0,
        "printed_figure_numeric_annotations": len(figure_numbers),
        "native_figure_numeric_annotations_regenerated": 0,
        "third_party_candidates": 2, "third_party_candidates_with_native_credit": 0,
        "full_end_to_end_pipeline_reproduced": False, "strict_success": False,
    }
    manifest["output_sha256"] = {
        path.name: sha256(path) for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(args.output)
    if args.strict and not manifest["strict_success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
