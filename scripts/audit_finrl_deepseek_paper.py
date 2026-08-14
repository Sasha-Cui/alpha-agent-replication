#!/usr/bin/env python3
"""Fail-closed paper-level audit of FinRL-DeepSeek.

The audit pins the arXiv paper, the nearest pre-submission and current source
revisions, the official Hugging Face data/checkpoint releases, the stored
notebook outputs, and native released-checkpoint evaluations.  Availability,
loadability, and component execution never imply paper-result reproduction.
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
import tempfile
import warnings
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


PAPER_URL = "https://arxiv.org/abs/2502.07393"
PAPER_SUBMITTED = "2025-02-11T09:23:14Z"
PAPER_PDF_SHA256 = "3a479199fac6b69525416028672288620009bb51c78381790821f4f42ce3e7ca"
PAPER_SOURCE_SHA256 = "f8def8f2b873cce6c495813201b5d3b49cc2123f72b0004859f8a94c76862719"
ARXIV_API_SHA256 = "35ed2de5cfcb3997029d3dd3a3b570ba38b60ebd1a6d78b16caa7815444da122"
SOURCE_URL = "https://github.com/benstaf/FinRL_DeepSeek"
PRE_SUBMISSION_COMMIT = "43e58573274c480e4d5f5b3c946073e2cb2e49a6"
PRE_SUBMISSION_DATE = "2025-02-07T18:05:01+01:00"
CURRENT_COMMIT = "5c21a923214bca6370800efd45f8c6c1ef776ae7"
CURRENT_DATE = "2025-04-08T14:22:13+02:00"
PUBLIC_HISTORY_COMMIT_COUNT = 36
PUBLIC_HISTORY_COMMIT_SHA256 = "7c0c0c7a57e610dc0cdb929eb63fc0f9205b733526b09c0f46cbc371d11ed09a"
PUBLIC_HISTORY_PATH_COUNT = 48
PUBLIC_HISTORY_PATH_SHA256 = "ebfa5d0dcb2a1f79da369f8762615e209c446977dc62ca50339d44e083adf8b6"
PUBLIC_HISTORY_OBJECT_COUNTS = {"blob": 73, "commit": 36, "tree": 36}
PUBLIC_DISCOVERY_SHA256 = {
    "branches.json": "16b8c064d941ff13b36aef80101fd6997d5ec4d6b492c2d2f2e766b0aef8a3aa",
    "releases.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "tags.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}
HISTORICAL_NOTEBOOK_BLOBS = 9
HISTORICAL_NOTEBOOK_VALID_JSON_BLOBS = 7
HISTORICAL_NOTEBOOK_MALFORMED_JSON_BLOBS = 2
HISTORICAL_NOTEBOOK_OUTPUT_SIGNATURE_SHA256 = (
    "11f14b79e04a05fe04e081dfd09fb93f2c8f496a3eda351b076ed07a974d8620"
)
HISTORICAL_TRAINING_LOG_BLOBS = 15
HISTORICAL_LOGS_WITH_EXACT_RELEASED_CHECKPOINT_NAME = 10
HISTORICAL_LOGS_WITH_PAPER_RELEVANT_CHECKPOINT_NAME = 5
FINRL_NOTEBOOK_COMMIT = "cd016b667da1860939b43bb77aba7ff4e35f780f"
ELEGANTRL_NOTEBOOK_COMMIT = "2fa34dd9236498beada8d8443d927970a9de1f7f"
HF_DATASET_URL = "https://huggingface.co/datasets/benstaf/nasdaq_2013_2023"
HF_DATASET_COMMIT = "b80bc15e4320eac68f53cfdd2fff3365e55dfedd"
HF_AGENTS_URL = "https://huggingface.co/benstaf/Trading_agents"
HF_AGENTS_COMMIT = "2153a7266aac75f9613fdae1bde09dbd38691c59"
OFFICIAL_HISTORY_TIPS = (CURRENT_COMMIT,)

PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_SNAPSHOT_SHA256 = (
    "ff23fbaafa28e68c759a3ef366f96b60bf39c20d136b547d8c727f0dab1bdb8f"
)
PUBLIC_FORK_REPOSITORY_LISTINGS = 81
PUBLIC_FORK_ACCESSIBLE_REPOSITORIES = 80
PUBLIC_FORK_INACCESSIBLE_REPOSITORIES = {"66my/FinRL_DeepSeek"}
PUBLIC_FORK_BRANCH_REFS = 82
PUBLIC_FORK_TAG_REFS = 0
PUBLIC_FORK_REF_SEQUENCE_SHA256 = (
    "112bdbb4e452049c60ddae15675ebfd7cab4229e7868d1e32c84ce41db2671a0"
)
PUBLIC_FORK_UNIQUE_HEADS = 10
PUBLIC_FORK_DIVERGENT_HEADS = 5
PUBLIC_FORK_DIVERGENT_COMMITS = 69
PUBLIC_FORK_DIVERGENT_COMMIT_SHA256 = (
    "983b34960d3f56bc533b50a7d68752c5ea198ff180301ae3ee0132fd23c3eaef"
)
PUBLIC_FORK_DIVERGENT_PATHS = 84
PUBLIC_FORK_DIVERGENT_PATH_SHA256 = (
    "74db6df9348ed3ad7a680379d21a38c0df974b8f2f5c030b46b1f02a30877eab"
)
PUBLIC_FORK_NEW_OBJECT_COUNTS = {"blob": 159, "commit": 69, "tree": 103}
PUBLIC_FORK_NEW_OBJECT_SHA256 = (
    "c58ecb155652168f1b12313a4fd72786469bec50223ab89e111cba592eeb2fc6"
)
PUBLIC_FORK_STRUCTURED_CHANGED_PATHS = {"FinRL_DeepSeek_backtest.ipynb"}
PUBLIC_FORK_NOTEBOOK_BLOBS = {
    "2dceec4c9bde767bc842d02d5e8695503e35c903": {
        "sha256": "d11241c718ae39d0045f1bae28af7b5e37f3636cc540d9338f9a1e3057221b9d",
        "cells": 97,
        "output_objects": 13,
        "stored_metric_entries": 0,
        "metric_signature_sha256": (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ),
        "classification": "community_initialization_fix_no_metric_output",
    },
    "4b74deee497b74321854191f9097392cd7f50baf": {
        "sha256": "6289b83aeb48890b2dacb4d8f8e540a2f87d8c5d622afca3d80c5bd2f73c3ae7",
        "cells": 104,
        "output_objects": 73,
        "stored_metric_entries": 33,
        "metric_signature_sha256": (
            "8071c92d0e71f2fedee64c68ab2900c05f220df87c0edaf4ef78e4e27915da98"
        ),
        "classification": "community_released_checkpoint_backtest_rerun",
    },
}
PUBLIC_FORK_HUANG_INTEGRATION_HEAD = "3440f29e02c259490b554e26d7bad5330fb4a0c1"
PUBLIC_FORK_HUANG_MAIN_HEAD = "662fd9da66d0955620e42de291c5e6abf0bdecd3"
PUBLIC_FORK_HEMANG_HEAD = "4b34d5fef93fb09cde54b9e96e330fd733459173"
PUBLIC_FORK_FOVI_HEAD = "7bcd8b4d12ec63d08192acb1c9eb2a652a2e7a0d"
PUBLIC_FORK_AI4FINANCE_HEAD = "c10455cae49c8a43bbfab602b4671eefce422ff4"

METRICS = ("Information Ratio", "CVaR", "Rachev Ratio")
TABLES = {
    "Table 1 main 100-epoch comparison": {
        "PPO": (0.0100, -0.0394, 1.0637),
        "CPPO": (-0.0148, -0.0439, 1.0404),
        "PPO-DeepSeek 10%": (-0.0093, -0.0338, 0.9890),
        "CPPO-DeepSeek 10%": (0.0078, -0.0437, 0.9818),
    },
    "Table 2 PPO infusion": {
        "PPO": (0.0100, -0.0394, 1.0637),
        "PPO-DeepSeek 10%": (-0.0093, -0.0338, 0.9890),
        "PPO-DeepSeek 1%": (-0.0252, -0.0459, 1.0394),
        "PPO-DeepSeek 0.1%": (-0.0011, -0.0375, 0.9536),
    },
    "Table 3 CPPO infusion": {
        "CPPO": (-0.0148, -0.0439, 1.0404),
        "CPPO-DeepSeek 10%": (0.0078, -0.0437, 0.9818),
        "CPPO-DeepSeek 1%": (-0.0032, -0.0365, 0.9573),
        "CPPO-DeepSeek 0.1%": (-0.0060, -0.0441, 0.9789),
    },
}

NOTEBOOK_RESULTS = {
    "cell80": {
        "PPO": (0.0013, -0.0415, 1.0430),
        "CPPO": (-0.0035, -0.0434, 1.1000),
        "PPO-DeepSeek 10%": (-0.0132, -0.0396, 0.9609),
        "CPPO-DeepSeek 10%": (0.0035, -0.0447, 0.9446),
    },
    "cell81": {
        "PPO": (0.0010, -0.0403, 1.0425),
        "PPO-DeepSeek 10%": (-0.0085, -0.0370, 1.0025),
        "PPO-DeepSeek 1%": (-0.0277, -0.0483, 1.0690),
    },
}

NOTEBOOK_CELL_FOR_TABLE = {
    "Table 1 main 100-epoch comparison": "cell80",
    "Table 2 PPO infusion": "cell81",
    "Table 3 CPPO infusion": "cell80",
}

COMMUNITY_NOTEBOOK_BLOB = "4b74deee497b74321854191f9097392cd7f50baf"
COMMUNITY_NOTEBOOK_RESULTS = {
    "cell87": {
        "PPO 100 epochs": (0.0097, -0.0385, 1.0739),
        "CPPO 100 epochs": (-0.0267, -0.0446, 1.0565),
        "PPO-DeepSeek 100 epochs": (-0.0104, -0.0371, 1.0370),
        "CPPO-DeepSeek 100 epochs": (-0.0000, -0.0424, 0.9751),
    },
    "cell88": {
        "PPO": (0.0097, -0.0385, 1.0739),
        "PPO-DeepSeek 10%": (-0.0104, -0.0371, 1.0370),
        "PPO-DeepSeek 1%": (-0.0219, -0.0401, 1.0300),
        "PPO-DeepSeek 0.1%": (-0.0050, -0.0379, 0.9219),
    },
}
COMMUNITY_NOTEBOOK_CELL_FOR_TABLE = {
    "Table 1 main 100-epoch comparison": "cell87",
    "Table 2 PPO infusion": "cell88",
    "Table 3 CPPO infusion": "cell87",
}
COMMUNITY_NOTEBOOK_METHOD_FOR_TABLE = {
    "Table 1 main 100-epoch comparison": {
        "PPO": "PPO 100 epochs",
        "CPPO": "CPPO 100 epochs",
        "PPO-DeepSeek 10%": "PPO-DeepSeek 100 epochs",
        "CPPO-DeepSeek 10%": "CPPO-DeepSeek 100 epochs",
    },
    "Table 2 PPO infusion": {},
    "Table 3 CPPO infusion": {
        "CPPO": "CPPO 100 epochs",
        "CPPO-DeepSeek 10%": "CPPO-DeepSeek 100 epochs",
    },
}

FIGURES = {
    "Figure 1 / download4.png": (
        "2023-01--2023-12",
        ("PPO 25 epochs", "CPPO 25 epochs", "PPO-Qwen 25 epochs", "CPPO-Qwen 25 epochs", "Nasdaq-100 index"),
    ),
    "Figure 2 / download10.png": (
        "2020-01--2023-12",
        ("PPO 20 epochs", "CPPO 20 epochs", "PPO-DeepSeek 20 epochs", "PPO-Llama 20 epochs", "CPPO-DeepSeek 20 epochs", "CPPO-Llama 20 epochs", "Nasdaq-100 index"),
    ),
    "Figure 3 / download15.png": (
        "2020-01--2023-12",
        ("PPO 100 epochs", "CPPO 100 epochs", "PPO-DeepSeek 100 epochs", "CPPO-DeepSeek 100 epochs", "Nasdaq-100 index"),
    ),
    "Figure 4 / download13.png": (
        "2020-01--2023-12",
        ("PPO 100 epochs", "CPPO 100 epochs", "PPO-DeepSeek 100 epochs", "CPPO-DeepSeek 100 epochs", "Nasdaq-100 index"),
    ),
    "Figure 5 / download17.png": (
        "2020-01--2023-12",
        ("PPO", "PPO-DeepSeek 10%", "PPO-DeepSeek 1%", "PPO-DeepSeek 0.1%", "Nasdaq-100 index"),
    ),
    "Figure 6 / download18.png": (
        "2020-01--2023-12",
        ("CPPO", "CPPO-DeepSeek 10%", "CPPO-DeepSeek 1%", "CPPO-DeepSeek 0.1%", "Nasdaq-100 index"),
    ),
}

EXPECTED_DATA_HASHES = {
    "trade_data_2019_2023.csv": "01587b66236b5563df8f871f0110bbf752f1c593427a346192c20e271efffd3b",
    "trade_data_deepseek_risk_2019_2023.csv": "e5f510b815f7e6d05dba9307b71f2ca738f7370c77a4206b17b5fbd5dd23898d",
    "trade_data_deepseek_sentiment_2019_2023.csv": "1d827b3685e914bdbb4ee6270e556ba1a4490976a717bc85dc729f26ff980fef",
}

EXPECTED_AGENT_HASHES = {
    "agent_ppo_100_epochs_20k_steps.pth": "f138a91c36e0b88b27d58bf41549de24717aec48e7107641f3dfa1838b51177b",
    "agent_cppo_100_epochs_20k_steps.pth": "c7017d10df45958f1a09ee8e009d8c99346be867ff312b03876ed1b8cfb289b1",
    "agent_ppo_deepseek_100_epochs_20k_steps.pth": "ae05dd713d1c0e8a880daad0a3be49db0314c50211805272f8a61dd84794ef84",
    "agent_ppo_deepseek_100_epochs_20k_steps_01.pth": "0969fc0b9d4c49aa816b2ec88dd321ffa619d765df27d79ef8975797747b8d5b",
    "agent_ppo_deepseek_100_epochs_20k_steps_1.pth": "3f54f756654dc9a23c9c6fe6836a0be5ac03cc1fecf8952f020e58f63291fb8c",
    "agent_cppo_deepseek_100_epochs_20k_steps.pth": "b8dc3e1cc247a16c258d6940644008f3a491f0dd962145d37659a66c55b99d44",
    "agent_cppo_deepseek_100_epochs_20k_steps_01.pth": "672fa6bfc0e656f724833fac2046f04f5598fd9a87a1ea457bcaf9b1a2edcda0",
    "agent_cppo_deepseek_100_epochs_20k_steps_1.pth": "0995acb84653b5ffbfaab13fed295ff1efa8443df66f6dfe80e0ac82280fe53d",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return proc.stdout


def git_zpaths(source_root: Path, *args: str) -> list[str]:
    raw = run_git(source_root, *args, binary=True)
    return [item.decode("utf-8") for item in raw.split(b"\0") if item]


def git_show_text(source_root: Path, revision: str, path: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(source_root), "show", f"{revision}:{path}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.stdout if proc.returncode == 0 else ""


def notebook_output_text(notebook: Mapping[str, Any]) -> str:
    fragments: list[str] = []
    for cell in notebook.get("cells", []):
        for output in cell.get("outputs", []):
            if "text" in output:
                value = output["text"]
                fragments.append("".join(value) if isinstance(value, list) else str(value))
            for mime, value in output.get("data", {}).items():
                if mime.startswith("text/"):
                    fragments.append("".join(value) if isinstance(value, list) else str(value))
    return "\n".join(fragments)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError("refusing to write empty CSV: %s" % path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_table_rows(native_seed0: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
    native = (native_seed0 or {}).get("results", {})
    rows: list[dict[str, Any]] = []
    for table, methods in TABLES.items():
        for method, values in methods.items():
            for metric, paper_value in zip(METRICS, values):
                native_value: Any = ""
                if metric == "CVaR" and method in native:
                    native_value = native[method]["cvar"]
                elif metric == "Rachev Ratio" and method in native:
                    native_value = native[method]["rachev_ratio"]
                match = native_value != "" and f"{float(native_value):.4f}" == f"{paper_value:.4f}"
                rows.append(
                    {
                        "paper_table": table,
                        "method": method,
                        "metric": metric,
                        "unique_measurement_id": method + " / " + metric,
                        "paper_value": f"{paper_value:.4f}",
                        "native_seed0_value": "" if native_value == "" else f"{float(native_value):.12g}",
                        "display_precision_match": match,
                        "status": (
                            "not_reproduced_benchmark_series_not_frozen"
                            if metric == "Information Ratio"
                            else "native_value_matches_but_protocol_unpinned_no_credit"
                            if match
                            else "native_released_checkpoint_mismatch"
                        ),
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 36 or len({row["unique_measurement_id"] for row in rows}) != 24:
        raise RuntimeError("FinRL-DeepSeek table census changed")
    return rows


def unique_measurement_rows(table_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in table_rows:
        key = str(row["unique_measurement_id"])
        if key not in unique:
            unique[key] = {
                "unique_measurement_id": key,
                "method": row["method"],
                "metric": row["metric"],
                "paper_value": row["paper_value"],
                "native_seed0_value": row["native_seed0_value"],
                "display_precision_match": row["display_precision_match"],
                "paper_result_credit": False,
            }
    if len(unique) != 24:
        raise RuntimeError("FinRL-DeepSeek unique result census changed")
    return list(unique.values())


def notebook_conformance_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table, methods in TABLES.items():
        cell = NOTEBOOK_CELL_FOR_TABLE[table]
        outputs = NOTEBOOK_RESULTS[cell]
        for method, paper_values in methods.items():
            notebook_values = outputs.get(method)
            for i, (metric, paper_value) in enumerate(zip(METRICS, paper_values)):
                notebook_value = "" if notebook_values is None else notebook_values[i]
                match = notebook_value != "" and f"{float(notebook_value):.4f}" == f"{paper_value:.4f}"
                rows.append(
                    {
                        "paper_table": table,
                        "notebook_cell": cell,
                        "method": method,
                        "metric": metric,
                        "paper_value": f"{paper_value:.4f}",
                        "stored_notebook_value": "" if notebook_value == "" else f"{float(notebook_value):.4f}",
                        "status": "missing_stored_output" if notebook_value == "" else "match" if match else "stored_output_mismatch",
                        "paper_result_credit": False,
                    }
                )
    return rows


def notebook_stale_output_rows() -> list[dict[str, Any]]:
    rows = []
    for method in ("PPO", "PPO-DeepSeek 10%"):
        for i, metric in enumerate(METRICS):
            a = NOTEBOOK_RESULTS["cell80"][method][i]
            b = NOTEBOOK_RESULTS["cell81"][method][i]
            rows.append(
                {
                    "method": method,
                    "metric": metric,
                    "cell80_value": f"{a:.4f}",
                    "cell81_value": f"{b:.4f}",
                    "status": "same_series_different_stored_output",
                }
            )
    return rows


def community_notebook_conformance_rows() -> list[dict[str, Any]]:
    """Map the post-paper community rerun to every paper table cell.

    The fork runs the authors' released checkpoints rather than retraining the
    paper systems.  Its stored metrics are adverse correspondence evidence, not
    an independent native reproduction and never receive paper-result credit.
    """

    rows: list[dict[str, Any]] = []
    for table, methods in TABLES.items():
        cell = COMMUNITY_NOTEBOOK_CELL_FOR_TABLE[table]
        outputs = COMMUNITY_NOTEBOOK_RESULTS[cell]
        aliases = COMMUNITY_NOTEBOOK_METHOD_FOR_TABLE[table]
        for method, paper_values in methods.items():
            community_method = aliases.get(method, method)
            community_values = outputs.get(community_method)
            for i, (metric, paper_value) in enumerate(zip(METRICS, paper_values)):
                community_value = "" if community_values is None else community_values[i]
                match = community_value != "" and (
                    f"{float(community_value):.4f}" == f"{paper_value:.4f}"
                )
                rows.append(
                    {
                        "paper_table": table,
                        "community_notebook_cell": cell,
                        "paper_method": method,
                        "community_method_label": (
                            community_method if community_values is not None else ""
                        ),
                        "metric": metric,
                        "paper_value": f"{paper_value:.4f}",
                        "community_stored_value": (
                            "" if community_value == "" else f"{float(community_value):.4f}"
                        ),
                        "source_blob": COMMUNITY_NOTEBOOK_BLOB,
                        "provenance": (
                            "postpaper_community_backtest_of_author_released_checkpoints"
                        ),
                        "status": (
                            "missing_postpaper_community_stored_output"
                            if community_value == ""
                            else "postpaper_community_stored_output_match"
                            if match
                            else "postpaper_community_stored_output_mismatch"
                        ),
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 36:
        raise RuntimeError("FinRL-DeepSeek community table census changed")
    counts = Counter(row["status"] for row in rows)
    if counts != {
        "postpaper_community_stored_output_mismatch": 30,
        "missing_postpaper_community_stored_output": 6,
    }:
        raise RuntimeError("FinRL-DeepSeek community metric correspondence changed")
    return rows


def figure_rows() -> list[dict[str, Any]]:
    rows = []
    for figure, (span, series) in FIGURES.items():
        for label in series:
            rows.append(
                {
                    "figure": figure,
                    "visible_date_span": span,
                    "series": label,
                    "released_numeric_series": False,
                    "native_exact_curve_reproduced": False,
                    "status": "paper_raster_only",
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 32:
        raise RuntimeError("FinRL-DeepSeek figure series census changed")
    return rows


def figure_metric_rows() -> list[dict[str, Any]]:
    return [
        {"figure": "Figure 1", "series": method, "metric": "Information Ratio", "paper_value": f"{value:.4f}", "status": "raster_label_not_reproduced", "paper_result_credit": False}
        for method, value in (
            ("PPO 25 epochs", -0.0148),
            ("CPPO 25 epochs", -0.0382),
            ("PPO-Qwen 25 epochs", -0.0178),
            ("CPPO-Qwen 25 epochs", -0.0726),
        )
    ]


def mechanism_conformance() -> list[dict[str, Any]]:
    rows = [
        ("PPO clipped objective", "train_ppo.py compute_loss_pi", "implemented_match"),
        ("Gaussian actor and critic", "MLPActorCritic in training and notebook", "implemented_match"),
        ("recommendation score in state", "llm_sentiment appended to LLM environments", "implemented_match"),
        ("10% recommendation action multipliers", "env_stocktrading_llm.py uses 0.9/0.95/1.05/1.1", "implemented_match"),
        ("1% recommendation action multipliers", "env_stocktrading_llm_1.py uses 0.99/0.995/1.005/1.01", "implemented_match"),
        ("0.1% recommendation action multipliers", "env_stocktrading_llm_01.py uses 0.999/0.9995/1.0005/1.001", "implemented_match"),
        ("neutral recommendation factor", "paper says unchanged; 10% source multiplies neutral actions by 0.98", "mechanism_conflict"),
        ("CPPO CVaR objective", "source subtracts a clipped value update from GAE; it does not implement the displayed Lagrangian objective", "not_implemented_as_claimed"),
        ("CPPO trajectory-buffer isolation", "CPPOBuffer.finish_path subtracts the full valupdate buffer from the full advantage buffer on every trajectory, repeatedly modifying earlier slices", "implementation_bug"),
        ("CVaR alpha 0.05 worst tail", "source training default alpha is 0.85 and uses 1-alpha", "config_conflict"),
        ("trajectory return D(pi)", "source updates adjusted_D_pi at every environment step from ep_ret + v - r", "mechanism_conflict"),
        ("aggregate portfolio risk", "source weights risk scores by invested stock value and omits cash", "partial_match"),
        ("paper 10% CPPO risk weights", "only train_cppo_llm_old.py uses 0.9--1.1; it is a 25-epoch local Qwen path", "missing_exact_training_lineage"),
        ("100-epoch DeepSeek CPPO 1% risk weights", "train_cppo_llm_risk.py uses 0.99--1.01 and saves an unmatched _99_101 name", "source_checkpoint_name_conflict"),
        ("100-epoch DeepSeek CPPO 0.1% risk weights", "train_cppo_llm_risk_01.py saves a name absent from the official release", "source_checkpoint_name_conflict"),
        ("DeepSeek recommendation prompt", "paper gives zero-shot core prompt; post-paper source adds few-shot examples and batching", "post_paper_prompt_expansion"),
        ("DeepSeek risk prompt", "paper gives zero-shot core prompt; post-paper source adds few-shot examples and batching", "post_paper_prompt_expansion"),
        ("temperature zero", "post-paper DeepInfra scripts set temperature=0", "post_paper_implementation_only"),
        ("one random article per stock/day", "selection code, seed, and selected article IDs are absent", "missing_artifact"),
        ("FNSPID 15.7M to 2M reduction", "neither raw subset nor reduction manifest is released", "missing_artifact"),
        ("DeepSeek V3 signal values", "frozen derived sentiment/risk columns are released", "released_derived_artifact"),
        ("PPO/CPPO released checkpoint evaluation", "eight paper-relevant checkpoints load and execute on released CSVs", "native_component_executed"),
        ("stochastic evaluation", "notebook samples Gaussian actions but sets no evaluation seed", "unreproducible_random_protocol"),
        ("Nasdaq benchmark", "notebook downloads live Yahoo ticker ndx with no frozen series", "temporally_unpinned_input"),
        ("transaction costs", "all training/backtest environments set 0.1% buy and sell costs", "implemented_match"),
        ("turbulence liquidation", "backtest sets vix threshold 70; paper does not report it", "undisclosed_material_config"),
    ]
    return [{"paper_dimension": a, "source_evidence": b, "status": c, "paper_mechanism_credit": c == "implemented_match"} for a, b, c in rows]


def config_conformance() -> list[dict[str, Any]]:
    rows = [
        ("training dates", "2013-01-01--2018-12-31", "same in preprocessing scripts", "match"),
        ("trading dates", "2019-01-01--2023-12-31", "released CSV 2019-01-02--2023-12-28; main figures visibly start 2020", "paper_figure_conflict"),
        ("training steps", "2,000,000", "100 epochs x 20,000 parser/default", "match"),
        ("epochs", "100", "100 for named main scripts", "match"),
        ("hidden layers", "not stated", "512 x 512", "source_only"),
        ("PPO gamma", "not stated", "0.995", "source_only"),
        ("PPO clip ratio", "epsilon unspecified", "0.7", "paper_underspecified"),
        ("CPPO alpha", "example 0.05 worst tail", "0.85", "conflict"),
        ("CPPO beta", "symbol only", "3000.0", "source_only"),
        ("PPO seed", "not stated", "42", "paper_underspecified"),
        ("CPPO seed", "not stated", "0", "paper_underspecified"),
        ("evaluation seed", "not stated", "none", "missing"),
        ("hmax", "not stated", "100", "source_only"),
        ("initial cash", "not stated", "1,000,000", "source_only"),
        ("buy/sell costs", "not stated", "0.001 each", "source_only"),
        ("turbulence control", "not stated", "vix >= 70 liquidates all positions", "undisclosed_material_config"),
        ("stock universe", "Nasdaq-100", "84 survivors from July 17 2023 list across all years", "lookahead_universe"),
        ("benchmark symbol", "Nasdaq-100", "live Yahoo input 'ndx'", "temporally_unpinned"),
        ("missing sentiment", "not stated", "filled with 0 outside paper score range", "paper_underspecified"),
        ("missing risk", "not stated", "filled with neutral score 3", "source_only"),
    ]
    return [{"configuration": a, "paper_value": b, "source_value": c, "status": d} for a, b, c, d in rows]


def internal_checks() -> list[dict[str, Any]]:
    checks = [
        ("Table 1 values repeated in Tables 2/3", "12 repeated cells are internally identical", "pass"),
        ("notebook cell80 versus paper Table 1", "0/12 displayed values match", "paper_source_result_conflict"),
        ("notebook cell81 versus paper Table 2", "0/9 available values match; 3 are absent", "paper_source_result_conflict"),
        ("notebook Table 3 cell", "cell82 has no output and plots result instead of result_cppo", "broken_evaluation_cell"),
        ("notebook repeated PPO metrics", "cell80 and cell81 disagree on all three metrics for the same series", "stale_output_conflict"),
        ("notebook repeated PPO-DeepSeek 10% metrics", "cell80 and cell81 disagree on all three metrics for the same series", "stale_output_conflict"),
        ("PPO 0.1% notebook path", "normalization/filtering is commented out but later referenced", "broken_evaluation_cell"),
        ("figure 2 duration", "caption says 3 years, prose says 2019--2023, raster shows 2020--2023", "paper_internal_conflict"),
        ("main figure trading span", "Figures 2--6 visibly begin 2020 despite declared 2019 start", "paper_internal_conflict"),
        ("figure 1 training duration", "caption says 3 years while 2019--2022 is four calendar years", "paper_internal_conflict"),
        ("installation entrypoint", "installation_script.sh invokes nonexistent train_ppo_deepseek.py", "broken_installation_path"),
        ("current Python syntax", "risk_deepseek_deepinfra.py has an empty api_key assignment", "post_paper_syntax_error"),
        ("paper-era prompt implementation", "pre-submission source contains no LLM API scoring script", "missing_paper_era_source"),
        ("complete public source history", "all 36 reachable commits, 48 historical paths, 145 reachable objects, and zero unreachable objects audited", "pass"),
        ("historical notebook outputs", "all 9 notebook blobs retain one identical 24-entry stale metric signature; 2 malformed revisions contain the same outputs and none contains a paper table value", "paper_source_result_conflict"),
        ("historical training-log results", "15 training logs contain no Information Ratio, CVaR (5%), or Rachev Ratio evaluation outputs", "no_result_artifact"),
        ("official checkpoint source lineage", "5/8 paper-relevant checkpoint basenames have an exact producing training-log filename; three are absent or mismatched", "partial_provenance_gap"),
    ]
    return [{"check": a, "evidence": b, "status": c} for a, b, c in checks]


def specification_gaps() -> list[dict[str, Any]]:
    gaps = [
        ("random article selection seed and selected IDs", "required for exact LLM inputs"),
        ("raw 2M-record selected FNSPID subset", "required to reconstruct derived signals"),
        ("exact paper-era API provider/model snapshot", "DeepSeek V3 service is mutable"),
        ("complete prompts including batching/few-shot messages", "paper and post-paper source differ"),
        ("LLM response logs and parsing failures", "derived scores cannot be traced"),
        ("exact FinRL/spinningup revisions used for training", "training installer follows live Git heads"),
        ("complete Python/package lock", "not released"),
        ("paper evaluation RNG seeds/states", "notebook samples actions without a seed"),
        ("frozen Nasdaq-100 benchmark series", "notebook performs a live Yahoo download"),
        ("numeric portfolio paths behind six rasters", "only PNGs are in paper source"),
        ("checkpoint-to-training-run manifest", "history proves exact log filename lineage for 5/8 paper-relevant checkpoints, but three remain absent or mismatched"),
        ("exact 100-epoch DeepSeek 10% CPPO entrypoint", "not released"),
        ("exact 100-epoch DeepSeek 1% PPO entrypoint", "not released"),
        ("exact 100-epoch DeepSeek 1% CPPO checkpoint name mapping", "not released"),
        ("exact 100-epoch DeepSeek 0.1% CPPO checkpoint name mapping", "not released"),
        ("paper table-generating notebook revision/output", "all nine reachable notebook blobs share the same stale outputs and none matches a paper table value"),
        ("explanation of 2020 raster start versus 2019 protocol", "not provided"),
        ("Nasdaq membership/reconstitution protocol", "source uses a July 2023 survivor list"),
        ("rationale for VIX threshold 70", "material backtest rule absent from paper"),
        ("replicate seeds/error bars", "paper shows two curves but no tabular uncertainty"),
    ]
    return [{"missing_item": a, "why_required": b, "resolved": "no"} for a, b in gaps]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    files = str(run_git(source_root, "ls-files")).splitlines()
    return [
        {
            "path": rel,
            "size_bytes": (source_root / rel).stat().st_size,
            "sha256": sha256(source_root / rel),
            "paper_result_artifact": False,
        }
        for rel in files
    ]


def paper_source_inventory(source_root: Path) -> list[dict[str, Any]]:
    return [
        {"path": str(path.relative_to(source_root)), "size_bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(source_root.rglob("*"))
        if path.is_file()
    ]


def public_source_history(
    source_root: Path, paper_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Audit every object reachable from the pinned official source tip.

    Historical author outputs and training logs are evidence of provenance, not
    independent paper-result reproductions.  The function therefore validates
    the complete official graph and remains fail-closed about result credit.
    Fork refs may coexist in the object store but cannot widen this boundary.
    """

    discovery_root = source_root / "release-discovery"
    for name, expected in PUBLIC_DISCOVERY_SHA256.items():
        path = discovery_root / name
        if sha256(path) != expected:
            raise ValueError("public-source discovery drift: %s" % path)
    branches = json.loads((discovery_root / "branches.json").read_text(encoding="utf-8"))
    tags = json.loads((discovery_root / "tags.json").read_text(encoding="utf-8"))
    releases = json.loads((discovery_root / "releases.json").read_text(encoding="utf-8"))
    if [(row["name"], row["commit"]["sha"]) for row in branches] != [("main", CURRENT_COMMIT)]:
        raise ValueError("public branch discovery no longer matches the audited graph")
    if tags or releases:
        raise ValueError("new public tags or releases require an audit refresh")
    if str(run_git(source_root, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise ValueError("public source checkout is shallow")

    commits_raw = run_git(source_root, "rev-list", "--reverse", *OFFICIAL_HISTORY_TIPS)
    commits = str(commits_raw).splitlines()
    if len(commits) != PUBLIC_HISTORY_COMMIT_COUNT:
        raise ValueError("public commit census changed")
    if hashlib.sha256(str(commits_raw).encode("utf-8")).hexdigest() != PUBLIC_HISTORY_COMMIT_SHA256:
        raise ValueError("public commit sequence changed")

    path_lines = str(
        run_git(
            source_root,
            "log",
            "--pretty=format:",
            "--name-only",
            *OFFICIAL_HISTORY_TIPS,
        )
    ).splitlines()
    historical_paths = sorted({line for line in path_lines if line})
    path_payload = ("\n".join(historical_paths) + "\n").encode("utf-8")
    if len(historical_paths) != PUBLIC_HISTORY_PATH_COUNT:
        raise ValueError("public historical path census changed")
    if hashlib.sha256(path_payload).hexdigest() != PUBLIC_HISTORY_PATH_SHA256:
        raise ValueError("public historical path inventory changed")

    object_lines = str(
        run_git(source_root, "rev-list", "--objects", *OFFICIAL_HISTORY_TIPS)
    ).splitlines()
    object_ids = [line.split(" ", 1)[0] for line in object_lines]
    object_proc = subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
        input="\n".join(object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    )
    object_counts = dict(Counter(object_proc.stdout.splitlines()))
    if object_counts != PUBLIC_HISTORY_OBJECT_COUNTS:
        raise ValueError("public reachable-object census changed")
    fsck = subprocess.run(
        ["git", "-C", str(source_root), "fsck", "--full", "--no-reflogs", "--unreachable"],
        check=True,
        capture_output=True,
        text=True,
    )
    if fsck.stdout.strip():
        raise ValueError("unreachable repository objects require explicit audit")

    commit_rows: list[dict[str, Any]] = []
    notebook_first_seen: dict[str, tuple[str, str]] = {}
    log_first_seen: dict[str, tuple[str, str]] = {}
    for commit in commits:
        metadata = str(run_git(source_root, "show", "-s", "--format=%H%x1f%cI%x1f%s", commit)).rstrip("\n")
        commit_id, committed_at, subject = metadata.split("\x1f", 2)
        tree_paths: list[str] = []
        notebook_paths: list[str] = []
        log_paths: list[str] = []
        python_paths: list[str] = []
        for line in str(run_git(source_root, "ls-tree", "-r", commit)).splitlines():
            object_meta, path = line.split("\t", 1)
            _mode, object_type, object_id = object_meta.split()
            if object_type != "blob":
                continue
            tree_paths.append(path)
            if path.endswith(".py"):
                python_paths.append(path)
            if path.endswith(".ipynb"):
                notebook_paths.append(path)
                notebook_first_seen.setdefault(object_id, (commit, path))
            if path.endswith(".log"):
                log_paths.append(path)
                log_first_seen.setdefault(object_id, (commit, path))
        commit_rows.append(
            {
                "commit": commit_id,
                "committed_at": committed_at,
                "subject": subject,
                "tracked_files": len(tree_paths),
                "python_files": len(python_paths),
                "notebook_files": len(notebook_paths),
                "training_log_files": len(log_paths),
                "notebook_paths": ";".join(notebook_paths),
                "training_log_paths": ";".join(log_paths),
                "independently_regenerated_paper_results": 0,
                "paper_result_credit": False,
            }
        )

    if len(notebook_first_seen) != HISTORICAL_NOTEBOOK_BLOBS:
        raise ValueError("historical notebook blob census changed")
    metric_pattern = re.compile(
        r"(Information Ratio|CVaR(?: \(5%\))?|Rachev Ratio):\s*(-?\d+\.\d+)"
    )
    paper_tokens = {
        f"{value:.4f}"
        for methods in TABLES.values()
        for values in methods.values()
        for value in values
    }
    notebook_rows: list[dict[str, Any]] = []
    for object_id, (first_commit, first_path) in notebook_first_seen.items():
        raw = run_git(source_root, "cat-file", "-p", object_id, binary=True)
        decoded = raw.decode("utf-8", errors="replace")
        pairs = metric_pattern.findall(decoded)
        signature_payload = "\n".join("%s:%s" % pair for pair in pairs).encode("utf-8")
        signature = hashlib.sha256(signature_payload).hexdigest()
        valid_json = True
        cell_count: Any = ""
        output_cell_count: Any = ""
        try:
            notebook = json.loads(decoded)
            cells = notebook.get("cells", [])
            cell_count = len(cells)
            output_cell_count = sum(
                bool(metric_pattern.search(json.dumps(cell.get("outputs", [])))) for cell in cells
            )
        except json.JSONDecodeError:
            valid_json = False
        matched_tokens = sorted(token for token in paper_tokens if token in signature_payload.decode("utf-8"))
        notebook_rows.append(
            {
                "blob": object_id,
                "first_reachable_commit": first_commit,
                "first_reachable_path": first_path,
                "size_bytes": len(raw),
                "valid_json": valid_json,
                "notebook_cells": cell_count,
                "stored_metric_output_cells": output_cell_count,
                "stored_metric_entries": len(pairs),
                "normalized_metric_output_sha256": signature,
                "paper_numeric_tokens_matched": len(matched_tokens),
                "matched_paper_numeric_tokens": ";".join(matched_tokens),
                "status": "historical_author_output_no_paper_value_match",
                "paper_result_credit": False,
            }
        )
    valid_notebooks = sum(row["valid_json"] for row in notebook_rows)
    malformed_notebooks = len(notebook_rows) - valid_notebooks
    if (valid_notebooks, malformed_notebooks) != (
        HISTORICAL_NOTEBOOK_VALID_JSON_BLOBS,
        HISTORICAL_NOTEBOOK_MALFORMED_JSON_BLOBS,
    ):
        raise ValueError("historical notebook parse census changed")
    if {row["stored_metric_entries"] for row in notebook_rows} != {24}:
        raise ValueError("historical notebook stored-output census changed")
    if {row["normalized_metric_output_sha256"] for row in notebook_rows} != {
        HISTORICAL_NOTEBOOK_OUTPUT_SIGNATURE_SHA256
    }:
        raise ValueError("historical notebook outputs changed")
    if any(row["paper_numeric_tokens_matched"] for row in notebook_rows):
        raise ValueError("historical notebook now contains a paper numeric result")

    if len(log_first_seen) != HISTORICAL_TRAINING_LOG_BLOBS:
        raise ValueError("historical training-log blob census changed")
    agent_tree = json.loads((paper_root / "hf_agents_tree.json").read_text(encoding="utf-8"))
    released_checkpoints = {
        Path(row["path"]).name for row in agent_tree if row["path"].endswith(".pth")
    }
    paper_relevant_checkpoints = set(EXPECTED_AGENT_HASHES)
    log_rows: list[dict[str, Any]] = []
    for object_id, (first_commit, first_path) in log_first_seen.items():
        raw = run_git(source_root, "cat-file", "-p", object_id, binary=True)
        decoded = raw.decode("utf-8", errors="replace")
        saved_names = sorted(
            set(re.findall(r"trained_models/([^/\s]+\.pth)", decoded))
        )
        exact_released = sorted(set(saved_names) & released_checkpoints)
        exact_paper_relevant = sorted(set(saved_names) & paper_relevant_checkpoints)
        completion_lines = len(re.findall(r"Training finished and saved in trained_models/", decoded))
        evaluation_labels = sorted(
            label
            for label in ("Information Ratio", "CVaR (5%)", "Rachev Ratio")
            if label in decoded
        )
        if evaluation_labels:
            status = "training_log_contains_unexpected_evaluation_metric_requires_review"
        elif not saved_names:
            status = "incomplete_training_log_no_checkpoint_saved"
        elif exact_released:
            status = "training_only_exact_released_checkpoint_filename_lineage"
        else:
            status = "training_only_unreleased_checkpoint_filename"
        log_rows.append(
            {
                "path": first_path,
                "blob": object_id,
                "first_reachable_commit": first_commit,
                "size_bytes": len(raw),
                "training_completion_lines": completion_lines,
                "saved_checkpoint_basenames": ";".join(saved_names),
                "exact_released_checkpoint_basenames": ";".join(exact_released),
                "exact_paper_relevant_checkpoint_basenames": ";".join(exact_paper_relevant),
                "contains_paper_evaluation_metric_labels": bool(evaluation_labels),
                "paper_evaluation_metric_labels": ";".join(evaluation_labels),
                "status": status,
                "paper_result_credit": False,
            }
        )
    released_log_matches = sum(bool(row["exact_released_checkpoint_basenames"]) for row in log_rows)
    relevant_log_matches = sum(bool(row["exact_paper_relevant_checkpoint_basenames"]) for row in log_rows)
    if released_log_matches != HISTORICAL_LOGS_WITH_EXACT_RELEASED_CHECKPOINT_NAME:
        raise ValueError("released-checkpoint log lineage census changed")
    if relevant_log_matches != HISTORICAL_LOGS_WITH_PAPER_RELEVANT_CHECKPOINT_NAME:
        raise ValueError("paper-relevant checkpoint log lineage census changed")
    if any(row["contains_paper_evaluation_metric_labels"] for row in log_rows):
        raise ValueError("historical training log now contains result metrics")

    summary = {
        "official_history_tips": list(OFFICIAL_HISTORY_TIPS),
        "fork_refs_excluded_from_official_history": True,
        "discovered_public_branches": [{"name": "main", "head": CURRENT_COMMIT}],
        "discovered_public_tags": [],
        "discovered_public_releases": [],
        "reachable_commits": len(commits),
        "unique_historical_paths": len(historical_paths),
        "reachable_object_counts": object_counts,
        "unreachable_objects": 0,
        "historical_notebook_blobs": len(notebook_rows),
        "historical_notebook_valid_json_blobs": valid_notebooks,
        "historical_notebook_malformed_json_blobs": malformed_notebooks,
        "historical_notebook_distinct_metric_output_signatures": len(
            {row["normalized_metric_output_sha256"] for row in notebook_rows}
        ),
        "historical_notebook_blobs_with_paper_numeric_match": sum(
            bool(row["paper_numeric_tokens_matched"]) for row in notebook_rows
        ),
        "historical_training_log_blobs": len(log_rows),
        "historical_training_logs_with_evaluation_metrics": sum(
            row["contains_paper_evaluation_metric_labels"] for row in log_rows
        ),
        "historical_logs_with_exact_released_checkpoint_name": released_log_matches,
        "paper_relevant_checkpoints_with_exact_training_log_name": relevant_log_matches,
        "paper_relevant_checkpoints_total": len(paper_relevant_checkpoints),
        "independently_regenerated_paper_results": 0,
        "paper_result_credit": False,
    }
    return commit_rows, notebook_rows, log_rows, summary


def public_fork_audit(source_root: Path, snapshot_path: Path) -> dict[str, Any]:
    """Exhaust every accessible public fork ref while preserving provenance.

    A post-paper community notebook can contradict displayed values without
    becoming an author result or a native retraining replication.  Later code
    adaptations are audited for artifacts and protocol drift separately.
    """

    if sha256(snapshot_path) != PUBLIC_FORK_SNAPSHOT_SHA256:
        raise RuntimeError("FinRL-DeepSeek public-fork snapshot changed")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if len(snapshot) != PUBLIC_FORK_REPOSITORY_LISTINGS:
        raise RuntimeError("FinRL-DeepSeek public-fork REST listing count changed")

    repository_rows: list[dict[str, Any]] = []
    ref_rows: list[dict[str, Any]] = []
    refs_by_head: dict[str, list[tuple[str, str, str]]] = {}
    inaccessible: set[str] = set()
    for item in snapshot:
        repository = item["full_name"]
        has_error = bool(item.get("ref_error"))
        if has_error:
            inaccessible.add(repository)
            if item["branches"] or item["tags"]:
                raise RuntimeError("inaccessible FinRL-DeepSeek fork unexpectedly has refs")
        repository_rows.append(
            {
                "repository": repository,
                "url": item["clone_url"].removesuffix(".git"),
                "default_branch": item["default_branch"],
                "created_at": item["created_at"],
                "pushed_at": item["pushed_at"],
                "accessible_via_git": not has_error,
                "branch_refs": len(item["branches"]),
                "tag_refs": len(item["tags"]),
                "access_classification": (
                    "accessible_refs_exhausted"
                    if not has_error
                    else "stale_rest_listing_repository_now_404_or_inaccessible"
                ),
            }
        )
        for kind, refs in (("branch", item["branches"]), ("tag", item["tags"])):
            for name, head in refs.items():
                refs_by_head.setdefault(head, []).append((repository, kind, name))
                ref_rows.append(
                    {
                        "repository": repository,
                        "url": item["clone_url"].removesuffix(".git"),
                        "ref_kind": kind,
                        "ref_name": name,
                        "head_commit": head,
                    }
                )
    repository_rows.sort(key=lambda row: str(row["repository"]).casefold())
    ref_rows.sort(
        key=lambda row: (
            str(row["repository"]).casefold(),
            str(row["ref_kind"]),
            str(row["ref_name"]),
        )
    )
    if inaccessible != PUBLIC_FORK_INACCESSIBLE_REPOSITORIES:
        raise RuntimeError("FinRL-DeepSeek inaccessible public-fork set changed")
    if len(repository_rows) - len(inaccessible) != PUBLIC_FORK_ACCESSIBLE_REPOSITORIES:
        raise RuntimeError("FinRL-DeepSeek accessible public-fork count changed")
    ref_counts = Counter(row["ref_kind"] for row in ref_rows)
    if (
        ref_counts["branch"],
        ref_counts["tag"],
    ) != (PUBLIC_FORK_BRANCH_REFS, PUBLIC_FORK_TAG_REFS):
        raise RuntimeError("FinRL-DeepSeek public-fork ref counts changed")
    ref_payload = (
        "\n".join(
            sorted(
                "\t".join(
                    (
                        str(row["repository"]),
                        str(row["ref_kind"]),
                        str(row["ref_name"]),
                        str(row["head_commit"]),
                    )
                )
                for row in ref_rows
            )
        )
        + "\n"
    ).encode("utf-8")
    if hashlib.sha256(ref_payload).hexdigest() != PUBLIC_FORK_REF_SEQUENCE_SHA256:
        raise RuntimeError("FinRL-DeepSeek public-fork ref sequence changed")

    official_commits = set(
        str(run_git(source_root, "rev-list", *OFFICIAL_HISTORY_TIPS)).splitlines()
    )
    if len(official_commits) != PUBLIC_HISTORY_COMMIT_COUNT:
        raise RuntimeError("FinRL-DeepSeek explicit official history changed")
    for head in refs_by_head:
        present = subprocess.run(
            ["git", "-C", str(source_root), "cat-file", "-e", f"{head}^{{commit}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        if present:
            raise RuntimeError(f"FinRL-DeepSeek public-fork object missing: {head}")
    if len(refs_by_head) != PUBLIC_FORK_UNIQUE_HEADS:
        raise RuntimeError("FinRL-DeepSeek public-fork unique-head count changed")
    divergent_heads = sorted(set(refs_by_head) - official_commits)
    if len(divergent_heads) != PUBLIC_FORK_DIVERGENT_HEADS:
        raise RuntimeError("FinRL-DeepSeek divergent public-fork head count changed")

    divergent_commits_raw = str(
        run_git(
            source_root,
            "rev-list",
            "--reverse",
            *divergent_heads,
            "--not",
            *OFFICIAL_HISTORY_TIPS,
        )
    )
    divergent_commits = divergent_commits_raw.splitlines()
    if len(divergent_commits) != PUBLIC_FORK_DIVERGENT_COMMITS:
        raise RuntimeError("FinRL-DeepSeek divergent public-fork commit count changed")
    if (
        hashlib.sha256(divergent_commits_raw.encode("utf-8")).hexdigest()
        != PUBLIC_FORK_DIVERGENT_COMMIT_SHA256
    ):
        raise RuntimeError("FinRL-DeepSeek divergent public-fork commit sequence changed")

    commit_paths: dict[str, list[str]] = {}
    changed_paths: set[str] = set()
    for commit in divergent_commits:
        paths = sorted(
            set(
                git_zpaths(
                    source_root,
                    "diff-tree",
                    "--root",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    "-z",
                    commit,
                )
            )
        )
        commit_paths[commit] = paths
        changed_paths.update(paths)
    changed_path_payload = ("\n".join(sorted(changed_paths)) + "\n").encode("utf-8")
    if len(changed_paths) != PUBLIC_FORK_DIVERGENT_PATHS:
        raise RuntimeError("FinRL-DeepSeek divergent public-fork path count changed")
    if (
        hashlib.sha256(changed_path_payload).hexdigest()
        != PUBLIC_FORK_DIVERGENT_PATH_SHA256
    ):
        raise RuntimeError("FinRL-DeepSeek divergent public-fork path inventory changed")

    def object_map(tips: Sequence[str]) -> dict[str, set[str]]:
        mapping: dict[str, set[str]] = {}
        for line in str(run_git(source_root, "rev-list", "--objects", *tips)).splitlines():
            parts = line.split(" ", 1)
            mapping.setdefault(parts[0], set())
            if len(parts) == 2:
                mapping[parts[0]].add(parts[1])
        return mapping

    official_objects = object_map(OFFICIAL_HISTORY_TIPS)
    fork_objects = object_map(divergent_heads)
    new_object_ids = sorted(set(fork_objects) - set(official_objects))
    new_object_payload = ("\n".join(new_object_ids) + "\n").encode("utf-8")
    if hashlib.sha256(new_object_payload).hexdigest() != PUBLIC_FORK_NEW_OBJECT_SHA256:
        raise RuntimeError("FinRL-DeepSeek fork unique-object inventory changed")
    object_proc = subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
        input="\n".join(new_object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    )
    object_types = object_proc.stdout.splitlines()
    new_object_counts = dict(Counter(object_types))
    if new_object_counts != PUBLIC_FORK_NEW_OBJECT_COUNTS:
        raise RuntimeError("FinRL-DeepSeek fork unique-object type census changed")
    new_blob_ids = {
        object_id
        for object_id, object_type in zip(new_object_ids, object_types)
        if object_type == "blob"
    }
    new_blob_paths = {
        path
        for object_id in new_blob_ids
        for path in fork_objects.get(object_id, set())
    }
    structured_suffixes = {
        ".ckpt",
        ".csv",
        ".h5",
        ".hdf5",
        ".ipynb",
        ".json",
        ".jsonl",
        ".log",
        ".npy",
        ".npz",
        ".parquet",
        ".pickle",
        ".pkl",
        ".pt",
        ".pth",
        ".safetensors",
    }
    structured_changed_paths = {
        path for path in new_blob_paths if Path(path).suffix.casefold() in structured_suffixes
    }
    if structured_changed_paths != PUBLIC_FORK_STRUCTURED_CHANGED_PATHS:
        raise RuntimeError("FinRL-DeepSeek fork structured-path surface changed")

    path_new_blobs: dict[str, set[str]] = {path: set() for path in changed_paths}
    first_commit_for_blob: dict[str, str] = {}
    for commit in divergent_commits:
        raw_tree = run_git(source_root, "ls-tree", "-r", "-z", commit, binary=True)
        for raw_line in raw_tree.split(b"\0"):
            if not raw_line:
                continue
            object_meta, raw_path = raw_line.split(b"\t", 1)
            _mode, object_type, object_id = object_meta.decode("ascii").split()
            path = raw_path.decode("utf-8")
            if object_type == "blob" and object_id in new_blob_ids:
                first_commit_for_blob.setdefault(object_id, commit)
                if path in path_new_blobs:
                    path_new_blobs[path].add(object_id)

    notebook_blob_ids = {
        object_id
        for object_id in new_blob_ids
        if any(path.endswith(".ipynb") for path in fork_objects.get(object_id, set()))
    }
    if notebook_blob_ids != set(PUBLIC_FORK_NOTEBOOK_BLOBS):
        raise RuntimeError("FinRL-DeepSeek public-fork notebook blob census changed")
    metric_pattern = re.compile(
        r"(Information Ratio|CVaR(?: \(5%\))?|Rachev Ratio):\s*(-?\d+\.\d+)"
    )
    paper_tokens = {
        f"{value:.4f}"
        for methods in TABLES.values()
        for values in methods.values()
        for value in values
    }
    notebook_rows: list[dict[str, Any]] = []
    for object_id in sorted(notebook_blob_ids):
        expected = PUBLIC_FORK_NOTEBOOK_BLOBS[object_id]
        raw = run_git(source_root, "cat-file", "-p", object_id, binary=True)
        if hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            raise RuntimeError("FinRL-DeepSeek fork notebook content changed")
        notebook = json.loads(raw)
        outputs = notebook_output_text(notebook)
        pairs = metric_pattern.findall(outputs)
        pair_payload = "\n".join("%s:%s" % pair for pair in pairs).encode("utf-8")
        matched_tokens = sorted(token for token in paper_tokens if token in outputs)
        output_objects = sum(len(cell.get("outputs", [])) for cell in notebook["cells"])
        if (
            len(notebook["cells"]) != expected["cells"]
            or output_objects != expected["output_objects"]
            or len(pairs) != expected["stored_metric_entries"]
            or hashlib.sha256(pair_payload).hexdigest()
            != expected["metric_signature_sha256"]
            or matched_tokens
        ):
            raise RuntimeError("FinRL-DeepSeek fork notebook evidence changed")
        source_text = "\n".join(
            "".join(cell.get("source", [])) for cell in notebook["cells"]
        )
        if object_id == COMMUNITY_NOTEBOOK_BLOB:
            required_markers = (
                "benstaf/Trading_agents",
                "/FinRL_DeepSeek/content/FinRL_LLM/trained_models/",
                '.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))',
                'returns_strategy.align(returns_benchmark, join="inner")',
            )
            if not all(marker in source_text for marker in required_markers):
                raise RuntimeError("community checkpoint rerun protocol changed")
        else:
            required_markers = (
                'load_dataset(path="benstaf/nasdaq_2013_2023"',
                "trade.fillna({'llm_sentiment': 0}, inplace=True)",
            )
            if not all(marker in source_text for marker in required_markers):
                raise RuntimeError("community initialization-only notebook changed")
        notebook_rows.append(
            {
                "blob": object_id,
                "path": "FinRL_DeepSeek_backtest.ipynb",
                "first_divergent_commit": first_commit_for_blob[object_id],
                "sha256": expected["sha256"],
                "python_version": notebook.get("metadata", {})
                .get("language_info", {})
                .get("version", ""),
                "notebook_cells": len(notebook["cells"]),
                "stored_output_objects": output_objects,
                "stored_metric_entries": len(pairs),
                "normalized_metric_output_sha256": hashlib.sha256(pair_payload).hexdigest(),
                "paper_numeric_tokens_matched": 0,
                "loads_author_released_checkpoint_snapshot": (
                    "benstaf/Trading_agents" in source_text
                ),
                "classification": expected["classification"],
                "paper_result_credit": False,
            }
        )

    head_classification = {
        PUBLIC_FORK_HUANG_INTEGRATION_HEAD: (
            "postpaper_protocol_adaptation_no_committed_new_result_or_checkpoint"
        ),
        PUBLIC_FORK_HUANG_MAIN_HEAD: (
            "postpaper_protocol_adaptation_no_committed_new_result_or_checkpoint"
        ),
        PUBLIC_FORK_HEMANG_HEAD: "community_released_checkpoint_backtest_rerun",
        PUBLIC_FORK_FOVI_HEAD: "community_initialization_fix_no_metric_output",
        PUBLIC_FORK_AI4FINANCE_HEAD: (
            "finrl_ecosystem_readme_only_no_new_result_artifact"
        ),
    }
    head_rows: list[dict[str, Any]] = []
    for head in sorted(refs_by_head):
        metadata = str(
            run_git(
                source_root,
                "show",
                "-s",
                "--format=%aI%x1f%an%x1f%ae%x1f%s",
                head,
            )
        ).rstrip("\n").split("\x1f", 3)
        if len(metadata) != 4:
            raise RuntimeError("FinRL-DeepSeek fork head metadata parse changed")
        unique_for_head = str(
            run_git(source_root, "rev-list", head, "--not", *OFFICIAL_HISTORY_TIPS)
        ).splitlines()
        raw_tree = run_git(source_root, "ls-tree", "-r", "-z", head, binary=True)
        tree_paths: list[str] = []
        tree_blob_ids: set[str] = set()
        new_paths_for_head: set[str] = set()
        for raw_line in raw_tree.split(b"\0"):
            if not raw_line:
                continue
            object_meta, raw_path = raw_line.split(b"\t", 1)
            _mode, object_type, object_id = object_meta.decode("ascii").split()
            path = raw_path.decode("utf-8")
            tree_paths.append(path)
            if object_type == "blob":
                tree_blob_ids.add(object_id)
                if object_id in new_blob_ids:
                    new_paths_for_head.add(path)
        relation = "official_history_reachable" if head in official_commits else "divergent"
        classification = (
            "official_history_copy" if relation == "official_history_reachable" else head_classification[head]
        )
        refs = sorted(refs_by_head[head])
        head_rows.append(
            {
                "head_commit": head,
                "repositories_and_refs": ";".join(
                    f"{repository}:{kind}:{name}" for repository, kind, name in refs
                ),
                "ref_count": len(refs),
                "authored_at": metadata[0],
                "author_name": metadata[1],
                "author_email": metadata[2],
                "subject": metadata[3],
                "relation_to_official_history": relation,
                "unique_commits_beyond_official_history": len(unique_for_head),
                "tracked_paths": len(tree_paths),
                "new_checkpoint_paths": sum(
                    Path(path).suffix.casefold() in {".ckpt", ".pt", ".pth", ".safetensors"}
                    for path in new_paths_for_head
                ),
                "new_dataset_paths": sum(
                    Path(path).suffix.casefold() in {".csv", ".parquet"}
                    for path in new_paths_for_head
                ),
                "new_training_log_paths": sum(
                    Path(path).suffix.casefold() == ".log" for path in new_paths_for_head
                ),
                "new_metric_output_notebook_blobs": sum(
                    blob == COMMUNITY_NOTEBOOK_BLOB for blob in tree_blob_ids
                ),
                "classification": classification,
                "paper_result_credit": False,
            }
        )
    if {row["head_commit"] for row in head_rows if row["relation_to_official_history"] == "divergent"} != set(head_classification):
        raise RuntimeError("FinRL-DeepSeek divergent head classification changed")
    if any(
        row["new_checkpoint_paths"]
        or row["new_dataset_paths"]
        or row["new_training_log_paths"]
        for row in head_rows
    ):
        raise RuntimeError("FinRL-DeepSeek fork gained an unreviewed data/training artifact")
    if sum(row["new_metric_output_notebook_blobs"] for row in head_rows) != 1:
        raise RuntimeError("FinRL-DeepSeek community output head census changed")

    huang_paths = sorted(
        str(
            run_git(
                source_root,
                "diff",
                "--name-only",
                f"{CURRENT_COMMIT}...{PUBLIC_FORK_HUANG_INTEGRATION_HEAD}",
            )
        ).splitlines()
    )
    if len(huang_paths) != 82 or any(not path.endswith(".py") for path in huang_paths):
        raise RuntimeError("FinRL-DeepSeek post-paper adaptation path surface changed")
    huang_compile = compile_revision_paths(
        source_root, PUBLIC_FORK_HUANG_INTEGRATION_HEAD, huang_paths
    )
    if huang_compile["compiled"] != 82 or huang_compile["failures"]:
        raise RuntimeError("FinRL-DeepSeek post-paper adaptation no longer syntax-compiles")
    integration_tree_paths = set(
        git_zpaths(
            source_root,
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            PUBLIC_FORK_HUANG_INTEGRATION_HEAD,
        )
    )
    protocol_sources = {
        "cppo_core": git_show_text(
            source_root, PUBLIC_FORK_HUANG_INTEGRATION_HEAD, "cppo_core.py"
        ),
        "trainer": git_show_text(
            source_root,
            PUBLIC_FORK_HUANG_INTEGRATION_HEAD,
            "train_cppo_llm_risk_standalone.py",
        ),
        "optimizer": git_show_text(
            source_root, PUBLIC_FORK_HUANG_INTEGRATION_HEAD, "auto_optimize.py"
        ),
        "clickhouse": git_show_text(
            source_root, PUBLIC_FORK_HUANG_INTEGRATION_HEAD, "clickhouse_data_adapter.py"
        ),
        "config": git_show_text(
            source_root, PUBLIC_FORK_HUANG_INTEGRATION_HEAD, "config_loader.py"
        ),
    }
    required_protocol_markers = {
        "cppo_core": ("reward_type='pnl', dsr_eta=0.01", "ir_bear_2022"),
        "trainer": (
            "Differential Sharpe Ratio",
            "from pkg.params import get_namespace",
            "from pkg.mlops import log_run",
        ),
        "optimizer": ("from ray import tune", "OptunaSearch", "MLflow"),
        "clickhouse": ("from pkg.database import repository as db",),
        "config": ("from utils.env_manager import EnvManager",),
    }
    if any(
        not all(marker in protocol_sources[name] for marker in markers)
        for name, markers in required_protocol_markers.items()
    ):
        raise RuntimeError("FinRL-DeepSeek post-paper protocol markers changed")
    missing_local_runtime_paths = {
        "pkg",
        "utils/env_manager.py",
        "backtest_finrl_deepseek.py",
    }
    if any(
        path == "pkg" or path.startswith("pkg/") for path in integration_tree_paths
    ) or not missing_local_runtime_paths.isdisjoint(integration_tree_paths):
        raise RuntimeError("FinRL-DeepSeek post-paper runtime dependency boundary changed")

    commit_rows: list[dict[str, Any]] = []
    for sequence, commit in enumerate(divergent_commits, start=1):
        metadata = str(
            run_git(
                source_root,
                "show",
                "-s",
                "--format=%aI%x1f%an%x1f%ae%x1f%s",
                commit,
            )
        ).rstrip("\n").split("\x1f", 3)
        paths = commit_paths[commit]
        introduced_metric_blob = False
        for path in paths:
            if path != "FinRL_DeepSeek_backtest.ipynb":
                continue
            tree_line = str(run_git(source_root, "ls-tree", commit, "--", path)).strip()
            if tree_line:
                object_id = tree_line.split()[2]
                introduced_metric_blob = object_id == COMMUNITY_NOTEBOOK_BLOB
        commit_rows.append(
            {
                "sequence": sequence,
                "commit": commit,
                "authored_at": metadata[0],
                "author_name": metadata[1],
                "author_email": metadata[2],
                "subject": metadata[3],
                "changed_paths": len(paths),
                "changed_path_names": ";".join(paths),
                "introduced_community_metric_notebook_blob": introduced_metric_blob,
                "paper_result_credit": False,
            }
        )
    if sum(row["introduced_community_metric_notebook_blob"] for row in commit_rows) != 1:
        raise RuntimeError("FinRL-DeepSeek community metric commit lineage changed")

    path_rows: list[dict[str, Any]] = []
    for path in sorted(changed_paths):
        if path.endswith(".ipynb"):
            classification = "community_backtest_notebook"
        elif path == "README.md":
            classification = "documentation"
        elif path.startswith("spinup/"):
            classification = "bundled_upstream_training_library"
        else:
            classification = "postpaper_training_or_infrastructure_source"
        path_rows.append(
            {
                "path": path,
                "extension": Path(path).suffix.casefold(),
                "new_blob_versions": len(path_new_blobs[path]),
                "classification": classification,
                "new_checkpoint_or_dataset_or_training_log": (
                    Path(path).suffix.casefold()
                    in {".ckpt", ".csv", ".log", ".parquet", ".pt", ".pth", ".safetensors"}
                ),
                "community_metric_output_notebook": (
                    COMMUNITY_NOTEBOOK_BLOB in path_new_blobs[path]
                ),
                "native_paper_result_artifact": False,
                "paper_result_credit": False,
            }
        )

    for row in ref_rows:
        head = str(row["head_commit"])
        row["relation_to_official_history"] = (
            "official_history_reachable" if head in official_commits else "divergent"
        )
        row["paper_result_credit"] = False

    community_rows = community_notebook_conformance_rows()
    community_counts = Counter(row["status"] for row in community_rows)
    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "snapshot_sha256": PUBLIC_FORK_SNAPSHOT_SHA256,
        "github_rest_repository_listings": len(repository_rows),
        "accessible_public_forks": len(repository_rows) - len(inaccessible),
        "stale_or_inaccessible_rest_listings": len(inaccessible),
        "stale_or_inaccessible_repositories": sorted(inaccessible),
        "accessible_branch_refs": sum(row["ref_kind"] == "branch" for row in ref_rows),
        "tag_refs": sum(row["ref_kind"] == "tag" for row in ref_rows),
        "all_refs_audited": len(ref_rows),
        "unique_heads": len(head_rows),
        "official_history_reachable_unique_heads": sum(
            row["relation_to_official_history"] == "official_history_reachable"
            for row in head_rows
        ),
        "divergent_unique_heads": len(divergent_heads),
        "divergent_unique_commits": len(divergent_commits),
        "divergent_changed_paths": len(changed_paths),
        "divergent_new_object_counts": new_object_counts,
        "divergent_new_blob_paths": len(new_blob_paths),
        "new_notebook_blob_versions": len(notebook_rows),
        "community_checkpoint_rerun_notebooks_with_metrics": 1,
        "community_stored_metric_entries": 33,
        "community_table_cells_corresponded": (
            len(community_rows)
            - community_counts["missing_postpaper_community_stored_output"]
        ),
        "community_table_cells_matching_paper": community_counts[
            "postpaper_community_stored_output_match"
        ],
        "community_table_cells_mismatching_paper": community_counts[
            "postpaper_community_stored_output_mismatch"
        ],
        "community_table_cells_missing": community_counts[
            "missing_postpaper_community_stored_output"
        ],
        "new_checkpoint_paths": 0,
        "new_dataset_paths": 0,
        "new_training_log_paths": 0,
        "postpaper_adaptation_changed_python_paths": len(huang_paths),
        "postpaper_adaptation_python_files_compiled": huang_compile["compiled"],
        "postpaper_adaptation_changes_native_objective_or_protocol": True,
        "postpaper_adaptation_requires_unreleased_local_pkg_or_runtime_services": True,
        "postpaper_adaptation_committed_result_or_checkpoint_artifacts": 0,
        "complete_paper_result_rows_found": 0,
        "independently_regenerated_native_training_runs": 0,
        "native_paper_result_artifacts_found": 0,
        "paper_result_credit": False,
    }
    return {
        "repositories": repository_rows,
        "refs": ref_rows,
        "heads": head_rows,
        "commits": commit_rows,
        "paths": path_rows,
        "notebooks": notebook_rows,
        "community_table_conformance": community_rows,
        "summary": summary,
    }


def hf_inventory(api_path: Path, tree_path: Path, kind: str) -> list[dict[str, Any]]:
    api = json.loads(api_path.read_text(encoding="utf-8"))
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    rows = []
    for item in tree:
        lfs = item.get("lfs") or {}
        rows.append(
            {
                "release_kind": kind,
                "repository_commit": api["sha"],
                "path": item["path"],
                "size_bytes": item["size"],
                "sha256_or_git_oid": lfs.get("oid", item.get("oid", "")),
                "last_commit_date": (item.get("lastCommit") or {}).get("date", ""),
                "paper_input_or_checkpoint": item["path"].endswith((".csv", ".pth")),
            }
        )
    return rows


def compile_revision(source_root: Path, revision: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        archive = run_git(source_root, "archive", revision, binary=True)
        tar_path = Path(tmp) / "source.tar"
        tar_path.write_bytes(archive)
        subprocess.run(["tar", "-xf", str(tar_path), "-C", tmp], check=True)
        python_files = sorted(Path(tmp).glob("*.py"))
        failures = []
        for path in python_files:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    warnings.simplefilter("ignore", DeprecationWarning)
                    py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                failures.append(
                    {"path": path.name, "error": str(exc).replace(str(path), path.name)}
                )
    return {"revision": revision, "python_files": len(python_files), "compiled": len(python_files) - len(failures), "failures": failures}


def compile_revision_paths(
    source_root: Path, revision: str, paths: Sequence[str]
) -> dict[str, Any]:
    python_paths = sorted(path for path in paths if path.endswith(".py"))
    if len(python_paths) != len(paths):
        raise ValueError("fork compilation path set contains non-Python files")
    with tempfile.TemporaryDirectory() as tmp:
        archive = run_git(
            source_root,
            "archive",
            revision,
            "--",
            *python_paths,
            binary=True,
        )
        tar_path = Path(tmp) / "source.tar"
        tar_path.write_bytes(archive)
        subprocess.run(["tar", "-xf", str(tar_path), "-C", tmp], check=True)
        failures = []
        for relative in python_paths:
            path = Path(tmp) / relative
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    warnings.simplefilter("ignore", DeprecationWarning)
                    py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                failures.append(
                    {"path": relative, "error": str(exc).replace(str(path), relative)}
                )
    return {
        "revision": revision,
        "python_files": len(python_paths),
        "compiled": len(python_paths) - len(failures),
        "failures": failures,
    }


def validate_native_inputs(artifacts_root: Path) -> dict[str, Any]:
    checked = []
    for subdir, expected in (("data", EXPECTED_DATA_HASHES), ("agents", EXPECTED_AGENT_HASHES)):
        for name, digest in expected.items():
            path = artifacts_root / subdir / name
            actual = sha256(path)
            if actual != digest:
                raise ValueError("artifact hash mismatch: %s" % path)
            checked.append({"path": subdir + "/" + name, "sha256": actual, "size_bytes": path.stat().st_size})
    runs = {}
    for name in ("native_seed0.json", "native_seed42.json", "native_mean.json"):
        run = json.loads((artifacts_root / name).read_text(encoding="utf-8"))
        if run["source_revision"] != CURRENT_COMMIT or len(run["results"]) != 8:
            raise ValueError("invalid native execution record: %s" % name)
        runs[name] = run
    return {
        "execution_driver": "scripts/run_finrl_deepseek_native.py",
        "source_revision": CURRENT_COMMIT,
        "execution_environment": {
            "python": "3.12.8",
            "torch": "2.10.0+cu128",
            "numpy": "2.3.5",
            "pandas": "2.2.3",
            "scipy": "1.17.1",
            "device": "cpu",
            "omp_num_threads": 8,
            "mkl_num_threads": 8,
        },
        "input_artifacts": checked,
        "runs": runs,
        "paper_result_credit": False,
        "credit_reason": "Released components execute, but the paper/notebook fix no evaluation seed or benchmark snapshot, and no run reproduces the paper table at displayed precision.",
    }


def build_audit(
    source_root: Path,
    paper_root: Path,
    artifacts_root: Path,
    fork_snapshot_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if str(run_git(source_root, "rev-parse", "HEAD")).strip() != CURRENT_COMMIT:
        raise ValueError("source checkout is not pinned to the audited current commit")
    expected_files = {
        "paper.pdf": PAPER_PDF_SHA256,
        "source.tar": PAPER_SOURCE_SHA256,
        "arxiv_api.xml": ARXIV_API_SHA256,
    }
    for name, expected in expected_files.items():
        if sha256(paper_root / name) != expected:
            raise ValueError("primary-source hash mismatch: %s" % name)
    data_api = json.loads((paper_root / "hf_nasdaq_api.json").read_text(encoding="utf-8"))
    agent_api = json.loads((paper_root / "hf_agents_api.json").read_text(encoding="utf-8"))
    if data_api["sha"] != HF_DATASET_COMMIT or agent_api["sha"] != HF_AGENTS_COMMIT:
        raise ValueError("Hugging Face release commit drift")

    output_dir.mkdir(parents=True, exist_ok=True)
    native = validate_native_inputs(artifacts_root)
    seed0 = native["runs"]["native_seed0.json"]
    tables = paper_table_rows(seed0)
    unique = unique_measurement_rows(tables)
    notebook = notebook_conformance_rows()
    figures = figure_rows()
    figure_metrics = figure_metric_rows()
    mechanisms = mechanism_conformance()
    configs = config_conformance()
    checks = internal_checks()
    gaps = specification_gaps()
    source_files = source_inventory(source_root)
    paper_files = paper_source_inventory(paper_root / "source")
    data_files = hf_inventory(paper_root / "hf_nasdaq_api.json", paper_root / "hf_nasdaq_tree.json", "dataset")
    agent_files = hf_inventory(paper_root / "hf_agents_api.json", paper_root / "hf_agents_tree.json", "checkpoint")
    history_commits, historical_notebooks, historical_logs, history_summary = public_source_history(
        source_root, paper_root
    )
    forks = public_fork_audit(source_root, fork_snapshot_path)
    fork_summary = forks["summary"]
    compile_pre = compile_revision(source_root, PRE_SUBMISSION_COMMIT)
    compile_current = compile_revision(source_root, CURRENT_COMMIT)

    outputs = {
        "paper_numeric_table_conformance.csv": tables,
        "paper_unique_measurement_conformance.csv": unique,
        "released_notebook_metric_conformance.csv": notebook,
        "released_notebook_stale_output_conflicts.csv": notebook_stale_output_rows(),
        "paper_figure_series_inventory.csv": figures,
        "paper_numeric_figure_labels.csv": figure_metrics,
        "source_mechanism_conformance.csv": mechanisms,
        "source_config_conformance.csv": configs,
        "paper_internal_and_source_checks.csv": checks,
        "paper_specification_gaps.csv": gaps,
        "released_source_inventory.csv": source_files,
        "paper_source_asset_inventory.csv": paper_files,
        "released_dataset_inventory.csv": data_files,
        "released_agent_inventory.csv": agent_files,
        "released_source_history_inventory.csv": history_commits,
        "historical_notebook_inventory.csv": historical_notebooks,
        "historical_training_log_inventory.csv": historical_logs,
        "public_fork_repository_access_inventory.csv": forks["repositories"],
        "public_fork_ref_snapshot.csv": forks["refs"],
        "public_fork_unique_head_inventory.csv": forks["heads"],
        "public_fork_divergent_commit_inventory.csv": forks["commits"],
        "public_fork_divergent_path_inventory.csv": forks["paths"],
        "public_fork_notebook_inventory.csv": forks["notebooks"],
        "public_fork_notebook_table_conformance.csv": forks[
            "community_table_conformance"
        ],
    }
    for name, rows in outputs.items():
        write_csv(output_dir / name, rows)
    (output_dir / "native_released_agent_execution.json").write_text(json.dumps(native, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "source_compilation.json").write_text(json.dumps({"pre_submission": compile_pre, "current": compile_current}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "public_source_history.json").write_text(
        json.dumps(history_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "public_fork_census.json").write_text(
        json.dumps(fork_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    notebook_counts = Counter(row["status"] for row in notebook)
    native_matches = sum(str(row["display_precision_match"]) == "True" for row in tables)
    manifest = {
        "paper": "FinRL-DeepSeek: LLM-Infused Risk-Sensitive Reinforcement Learning for Trading Agents",
        "paper_url": PAPER_URL,
        "paper_submitted": PAPER_SUBMITTED,
        "source_url": SOURCE_URL,
        "pre_submission_source_commit": PRE_SUBMISSION_COMMIT,
        "current_source_commit": CURRENT_COMMIT,
        "hf_dataset_commit": HF_DATASET_COMMIT,
        "hf_agents_commit": HF_AGENTS_COMMIT,
        "overall_status": "released_data_checkpoints_and_code_execute_but_paper_results_not_reproduced",
        "full_paper_reproduced": False,
        "paper_numeric_table_cells_total": len(tables),
        "paper_unique_numeric_measurements_total": len(unique),
        "native_table_cells_display_precision_matches": native_matches,
        "native_table_cells_with_paper_result_credit": 0,
        "stored_notebook_table_cells_present": len(notebook) - notebook_counts["missing_stored_output"],
        "stored_notebook_table_cells_missing": notebook_counts["missing_stored_output"],
        "stored_notebook_table_cells_matching_paper": notebook_counts["match"],
        "stored_notebook_same_series_conflicts": 6,
        "paper_figure_series_total": len(figures),
        "paper_numeric_figure_labels_total": len(figure_metrics),
        "native_exact_figure_series_reproduced": 0,
        "paper_relevant_released_checkpoints_executed": 8,
        "native_evaluation_protocols_executed": 3,
        "released_dataset_files_total": len(data_files),
        "released_checkpoint_files_total": sum(row["path"].endswith(".pth") for row in agent_files),
        "current_tracked_source_files_total": len(source_files),
        "public_source_reachable_commits_total": history_summary["reachable_commits"],
        "public_source_unique_historical_paths_total": history_summary["unique_historical_paths"],
        "public_source_reachable_blobs_total": history_summary["reachable_object_counts"]["blob"],
        "public_source_reachable_trees_total": history_summary["reachable_object_counts"]["tree"],
        "public_source_reachable_commit_objects_total": history_summary["reachable_object_counts"]["commit"],
        "public_source_unreachable_objects_total": history_summary["unreachable_objects"],
        "historical_notebook_blobs_total": history_summary["historical_notebook_blobs"],
        "historical_notebook_valid_json_blobs": history_summary["historical_notebook_valid_json_blobs"],
        "historical_notebook_malformed_json_blobs": history_summary["historical_notebook_malformed_json_blobs"],
        "historical_notebook_distinct_metric_output_signatures": history_summary["historical_notebook_distinct_metric_output_signatures"],
        "historical_notebook_blobs_with_paper_numeric_match": history_summary["historical_notebook_blobs_with_paper_numeric_match"],
        "historical_training_log_blobs_total": history_summary["historical_training_log_blobs"],
        "historical_training_logs_with_evaluation_metrics": history_summary["historical_training_logs_with_evaluation_metrics"],
        "historical_logs_with_exact_released_checkpoint_name": history_summary["historical_logs_with_exact_released_checkpoint_name"],
        "paper_relevant_checkpoints_with_exact_training_log_name": history_summary["paper_relevant_checkpoints_with_exact_training_log_name"],
        "public_fork_census_date": fork_summary["census_date"],
        "public_fork_rest_repository_listings": fork_summary[
            "github_rest_repository_listings"
        ],
        "public_forks_accessible": fork_summary["accessible_public_forks"],
        "public_fork_stale_or_inaccessible_rest_listings": fork_summary[
            "stale_or_inaccessible_rest_listings"
        ],
        "public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
        "public_fork_tag_refs_audited": fork_summary["tag_refs"],
        "public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "public_fork_divergent_heads_audited": fork_summary["divergent_unique_heads"],
        "public_fork_divergent_commits_audited": fork_summary[
            "divergent_unique_commits"
        ],
        "public_fork_divergent_paths_audited": fork_summary[
            "divergent_changed_paths"
        ],
        "public_fork_new_blobs_audited": fork_summary[
            "divergent_new_object_counts"
        ]["blob"],
        "public_fork_notebook_blob_versions_audited": fork_summary[
            "new_notebook_blob_versions"
        ],
        "public_fork_community_stored_metric_entries": fork_summary[
            "community_stored_metric_entries"
        ],
        "public_fork_community_table_cells_corresponded": fork_summary[
            "community_table_cells_corresponded"
        ],
        "public_fork_community_table_cells_matching_paper": fork_summary[
            "community_table_cells_matching_paper"
        ],
        "public_fork_community_table_cells_mismatching_paper": fork_summary[
            "community_table_cells_mismatching_paper"
        ],
        "public_fork_community_table_cells_missing": fork_summary[
            "community_table_cells_missing"
        ],
        "public_fork_postpaper_adaptation_python_files_compiled": fork_summary[
            "postpaper_adaptation_python_files_compiled"
        ],
        "public_fork_new_checkpoint_paths": fork_summary["new_checkpoint_paths"],
        "public_fork_new_dataset_paths": fork_summary["new_dataset_paths"],
        "public_fork_new_training_log_paths": fork_summary["new_training_log_paths"],
        "public_fork_native_paper_result_artifacts_found": fork_summary[
            "native_paper_result_artifacts_found"
        ],
        "public_fork_paper_result_credit": False,
        "pre_submission_python_files_compiled": compile_pre["compiled"],
        "pre_submission_python_files_total": compile_pre["python_files"],
        "current_python_files_compiled": compile_current["compiled"],
        "current_python_files_total": compile_current["python_files"],
        "paper_mechanism_dimensions_audited": len(mechanisms),
        "paper_mechanism_dimensions_credited": sum(row["paper_mechanism_credit"] for row in mechanisms),
        "unresolved_specification_gaps": len(gaps),
    }
    report = f"""# FinRL-DeepSeek paper-level replication audit

## Verdict

The release is a substantial and unusually useful component package: the paper-era Hugging Face release contains 15 checkpoints, the dataset release contains frozen train/trade CSVs, the Git repository contains paper-era environments/training logs, and all eight checkpoints relevant to Tables 1--3 load and execute through the authors' environment code. The complete official graph has also been audited behind an explicit provenance boundary: 36 commits, 48 historical paths, 145 reachable objects, no tags or releases, and no unreachable objects. Fork refs cannot widen those author-source claims. That materially improves reproducibility, but it does not reproduce the paper.

The paper contains **36 displayed table cells representing 24 unique measurements**, **32 raster-only return series**, and **4 numeric IR labels in Figure 1**. The released notebook has stored values for {len(notebook) - notebook_counts['missing_stored_output']}/36 table cells, but **0 match the paper**; 9 cells have no stored output. Worse, its two stored evaluations of the same PPO and PPO-DeepSeek 10% series disagree on all six corresponding metrics. Every one of the nine historical notebook blobs—including two malformed revisions—contains the same 24 stored metric entries and none contains a paper table value. Three native protocols (stochastic seeds 0 and 42, plus policy means) executed all eight released checkpoints on hash-pinned released CSVs, but no table value earns paper-result credit. Information Ratio remains uncheckable from frozen inputs because the notebook downloads the benchmark live.

The public-fork census exhausted all **{fork_summary['accessible_public_forks']} accessible repositories, {fork_summary['all_refs_audited']} refs, {fork_summary['unique_heads']} unique heads, {fork_summary['divergent_unique_commits']} divergent commits, {fork_summary['divergent_changed_paths']} changed paths, and {fork_summary['divergent_new_object_counts']['blob']} genuinely new blobs** returned by the pinned listing snapshot; one stale listing was inaccessible. One post-paper community notebook downloads the authors' `benstaf/Trading_agents` checkpoint snapshot, repairs paths/device placement and return alignment, and stores 33 metric entries. It supplies correspondence for {fork_summary['community_table_cells_corresponded']}/36 paper table cells, but **all {fork_summary['community_table_cells_mismatching_paper']} supplied cells disagree at displayed precision** and 6 remain absent. This is adverse community evidence against the released-checkpoint backtest correspondence, not an author result, a retraining replication, or proof that the paper is false.

A later divergent adaptation contributes 82 syntax-valid Python files, including a bundled Spinning Up tree, Differential-Sharpe reward paths, Ray Tune/Optuna optimization, MLflow, Redis/ParamStore, and ClickHouse integration. It commits no new checkpoint, dataset, training log, or metric output; it also depends on `pkg` and `utils.env_manager` code absent from the fork. Because it changes the objective and evaluation protocol and requires uncommitted runtime state, it cannot receive native-paper credit.

## Decisive fidelity gaps

- The paper does not fix evaluation seeds, while the notebook samples Gaussian actions.
- Figures 2--6 visibly start in 2020 despite the stated 2019--2023 trading interval.
- The exact 100-epoch DeepSeek 10% CPPO training lineage is absent. The only committed 0.9--1.1 risk script is an older 25-epoch local-Qwen path; the 100-epoch DeepSeek scripts use smaller weights and unmatched output names.
- Fifteen historical training logs establish partial checkpoint provenance, but they contain no paper evaluation metrics. Ten logs name a released checkpoint exactly; only 5/8 paper-relevant checkpoint names have exact log lineage.
- The source's CPPO update is not the displayed CVaR-PPO Lagrangian: it applies a clipped per-step value adjustment to GAE, uses alpha=0.85, and repeatedly subtracts its full update buffer during trajectory finalization.
- The one-article-per-stock/day sample, selection seed/IDs, raw selected inputs, LLM responses, frozen Yahoo benchmark, and table-generating result paths are absent.
- The installation script invokes a nonexistent training file; the post-paper risk API script does not parse.

## Honest proximity

This is close to a runnable **artifact-level reconstruction** of the authors' code path and far better than a paper-only release. It is not a faithful result replication: 0/{len(tables)} displayed table cells, 0/{len(figures)} figure series, and 0/{len(figure_metrics)} raster metric labels are reproduced with defensible paper lineage. The community mismatch raises concern but does not convert an unidentifiable native training/evaluation protocol into a falsified claim. `--strict` remains nonzero until the pinned original protocol reproduces every claimed result within declared tolerances.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    paper_root = Path(os.environ.get("FINRL_DEEPSEEK_PAPER_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_paper"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(os.environ.get("FINRL_DEEPSEEK_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_source")))
    parser.add_argument("--paper-root", type=Path, default=paper_root)
    parser.add_argument("--artifacts-root", type=Path, default=Path(os.environ.get("FINRL_DEEPSEEK_ARTIFACTS_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_artifacts")))
    parser.add_argument(
        "--fork-snapshot",
        type=Path,
        default=Path(
            os.environ.get(
                "FINRL_DEEPSEEK_FORK_SNAPSHOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_paper/public_fork_snapshot.json",
            )
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=project_root / "paper_runs/paper_replication_audits/finrl_deepseek")
    parser.add_argument("--strict", action="store_true", help="Return nonzero until the full paper is reproduced")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root,
        args.paper_root,
        args.artifacts_root,
        args.fork_snapshot,
        args.output_dir,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
