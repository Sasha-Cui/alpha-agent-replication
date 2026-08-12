#!/usr/bin/env python3
"""Build a fail-closed two-version paper audit for TreEvo.

The official arXiv PDFs and TeX bundles are unusually strong document evidence,
and v2 publishes seven prompt templates.  They do not include an attributable
implementation, runtime prompt fills, search traces, factor code, market data,
or result arrays.  This audit therefore gives document/procedure-component
credit while keeping native paper-result reproduction at zero.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/treevo_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/treevo"
WORK_ID = "CensusArxiv250816334"
SYSTEM_ID = "SYS-TREEVO"
ARXIV_ID = "2508.16334"

PINS = {
    "raw/api.xml": "1917c9dd4f9a45728e9d5c1152beeb7df7e58c56365f436ea134c9bfbf71a8c9",
    "raw/abs.html": "a8b16e02fa9f7696417c80701eb418506fbc132ead6d72c083ac893e0822b118",
    "raw/abs-repeat.html": "a8b16e02fa9f7696417c80701eb418506fbc132ead6d72c083ac893e0822b118",
    "raw/paper-v1.pdf": "cd95cc111d5d77091ce8995e15f2a3243b264f471e850cf3f1fdfe4cf39875de",
    "raw/paper-v2.pdf": "c0287e1fcc4ace546958c7b5ea18ac6e2f80238814dd6ada0d06f5c15a65d664",
    "raw/paper-v1-repeat.pdf": "cd95cc111d5d77091ce8995e15f2a3243b264f471e850cf3f1fdfe4cf39875de",
    "raw/paper-v2-repeat.pdf": "c0287e1fcc4ace546958c7b5ea18ac6e2f80238814dd6ada0d06f5c15a65d664",
    "raw/source-v1.tar": "e55e65836add15eb5d51253910caa18494a80ede0059076c66b702fdd1b1c137",
    "raw/source-v2.tar": "f77f75e5488e4bb51af3ce006c16c149fddea32ed84af066633a87409681792f",
    "raw/source-v1-repeat.tar": "e55e65836add15eb5d51253910caa18494a80ede0059076c66b702fdd1b1c137",
    "raw/source-v2-repeat.tar": "f77f75e5488e4bb51af3ce006c16c149fddea32ed84af066633a87409681792f",
    "build-v1/formatting-instructions-latex.pdf": "774b793072d677f89f68677349fdf80697d60d6cf5cf3df4d84f0a071efa2303",
    "build-v2/acl_latex.pdf": "bbf2985744739c8d877a488a2c30c4aa57c20ddcc3101e6b08bc7d812fb947e1",
    "primary_external/alibaba_model_history.html": "bab1a033d58eb1421063538b3be107784e14dc62cae75a99a719d4a23bd3c714",
    "primary_external/qwen3_readme.md": "0b2c2bb11806f7a00c8465f2586e2e99f15de28622fd5c9b70b83ae1ab18c75d",
    "author_pages/peng_yang.html": "2aefb6334864b8e1b92b612a12d0d75bd0d6298271e7072dfe7720f2cb53546a",
    "author_pages/shengcai_liu.html": "6803eeeae885fa247b6ed3b62ed2af4086d793b71cd4d03dd50aac7a51d70cd8",
    "discovery/code_search_1.json": "10a65d3bc696e0dc7db96708e1d195e2b03c52918ebc65f9401b408e204d1812",
    "discovery/code_search_2.json": "e6067a845f35532d3cc986e6e0893459d8386783e98207a481b0515c6139d076",
    "discovery/code_search_3.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/repo_search_1.json": "5bf010dde2d2fd861831a645f721d0b9ae711c4edb1b1b7df26caeab6a41249b",
    "discovery/repo_search_2.json": "2db6907a9e83aa32ce68c865d9f7fd722c24daa0b0eb1ccca471992cf01ad81c",
    "discovery/repo_search_3.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/repo_search_4.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/repo_search_5.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/senshinel_repos.json": "93479cc5c26e6fdbfb224d53d1d3b634c198459e30f0c6e86a9f153e77f571b2",
}

SOURCE_VERSIONS = {
    "v1": {
        "title": "From Linear to Hierarchical: Evolving Tree-structured Thoughts for Efficient Alpha Mining",
        "submitted": "2025-08-22",
        "pdf_pages": 9,
        "source_files": 16,
        "main": "formatting-instructions-latex.tex",
        "main_sha256": "199801cb69d8ec3444c002f37d4e726dbee05751951c8019a21719adc6781b34",
        "rebuild_token_multiset_jaccard": 0.9988286969253294,
        "figures": 5,
        "figure_panels": 11,
        "numeric_table_result_cells": 96,
    },
    "v2": {
        "title": "From Flat to Hierarchical: Evolving Tree-structured Thoughts for Fine-grained Alpha Mining",
        "submitted": "2026-05-31",
        "pdf_pages": 17,
        "source_files": 28,
        "main": "acl_latex.tex",
        "main_sha256": "dbc3c2da309d15f95a32162ed7c5a00f8c4f9c3446f25a618939f7e081684d3d",
        "rebuild_token_multiset_jaccard": 0.9991171926726992,
        "figures": 8,
        "figure_panels": 23,
        "numeric_table_result_cells": 206,
    },
}

METRICS = ("IC", "RankIC")
DATASETS_V1 = ("CSI300", "CSI500", "SPX", "DJI")
DATASETS_V2 = ("CSI300", "CSI500", "SPX", "NDX")

V1_TABLE1 = {
    "XGBoost": ((0.0192, 0.0241, 0.0173, 0.0217), (0.0021, 0.0027, 0.0017, 0.0022)),
    "LightGBM": ((0.0158, 0.0235, 0.0112, 0.0212), (0.0012, 0.0030, 0.0012, 0.0020)),
    "GP": ((0.0445, 0.0673, 0.0557, 0.0665), (0.0044, 0.0058, 0.0117, 0.0154)),
    "AlphaGen": ((0.0500, 0.0540, 0.0544, 0.0722), (0.0021, 0.0035, 0.0011, 0.0017)),
    "QFR": ((0.0588, 0.0602, 0.0708, 0.0674), (0.0220, 0.0014, 0.0063, 0.0033)),
    "TreEvo": ((0.0615, 0.0649, 0.0742, 0.0793), (0.0153, 0.0173, 0.0081, 0.0119)),
}
V1_TABLE2 = {
    "EoH": (
        (0.0506, 0.0462, 0.0584, 0.0653, 0.0504, 0.0458, 0.0514, 0.0546),
        (0.0188, 0.0237, 0.0046, 0.0106, 0.0129, 0.0020, 0.0110, 0.0197),
    ),
    "ReEvo": (
        (0.0411, 0.0409, 0.0426, 0.0489, 0.0362, 0.0308, 0.0368, 0.0393),
        (0.0057, 0.0218, 0.0111, 0.0322, 0.0132, 0.0186, 0.0054, 0.0071),
    ),
    "TreEvo": (
        (0.0615, 0.0649, 0.0742, 0.0793, 0.0403, 0.0543, 0.0601, 0.0573),
        (0.0153, 0.0173, 0.0081, 0.0119, 0.0155, 0.2410, 0.0099, 0.0283),
    ),
}

V2_TABLE1 = {
    "XGBoost": ((0.0197, 0.0221, 0.0169, 0.0209), (0.0025, 0.0013, 0.0016, 0.0021)),
    "LightGBM": ((0.0165, 0.0244, 0.0172, 0.0241), (0.0012, 0.0025, 0.0022, 0.0017)),
    "GP": ((0.0224, 0.0278, 0.0254, 0.0297), (0.0017, 0.0038, 0.0028, 0.0014)),
    "AlphaGen": ((0.0259, 0.0301, 0.0337, 0.0405), (0.0010, 0.0046, 0.0023, 0.0047)),
    "AlphaForge": ((0.0287, 0.0351, 0.0319, 0.0346), (0.0014, 0.0029, 0.0022, 0.0026)),
    "QFR": ((0.0302, 0.0346, 0.0374, 0.0403), (0.0032, 0.0044, 0.0039, 0.0031)),
    "TreEvo": ((0.0308, 0.0349, 0.0362, 0.0393), (0.0048, 0.0057, 0.0051, 0.0049)),
}
V2_TABLE2 = {
    "EoH": (
        (0.0238, 0.0262, 0.0348, 0.0363, 0.0284, 0.0326, 0.0254, 0.0297),
        (0.0028, 0.0037, 0.0036, 0.0046, 0.0026, 0.0030, 0.0029, 0.0034),
    ),
    "ReEvo": (
        (0.0211, 0.0269, 0.0247, 0.0283, 0.0224, 0.0268, 0.0252, 0.0302),
        (0.0017, 0.0028, 0.0031, 0.0042, 0.0033, 0.0036, 0.0024, 0.0027),
    ),
    "TreEvo": (
        (0.0308, 0.0349, 0.0362, 0.0393, 0.0317, 0.0355, 0.0285, 0.0316),
        (0.0033, 0.0057, 0.0041, 0.0049, 0.0035, 0.0037, 0.0031, 0.0043),
    ),
}
V2_TABLE4 = {
    "GP": ("10 min", None),
    "AlphaGen": ("4 hour", None),
    "AlphaForge": ("6 hour", None),
    "QFR": ("4.5 hour", None),
    "TreEvo": ("20 min", "654K"),
    "ReEvo": ("18 min", "414K"),
    "EoH": ("40 min", "632K"),
}
V2_TABLE5 = {
    "RD-Agent": (0.0267, 0.0315, 0.0283, 0.0344, 0.0249, 0.0286, 0.0214, 0.0263),
    "AlphaAgent": (0.0278, 0.0329, 0.0341, 0.0387, 0.0323, 0.0364, 0.0258, 0.0302),
    "TreEvo": (0.0308, 0.0349, 0.0362, 0.0393, 0.0317, 0.0355, 0.0285, 0.0316),
}
V2_TABLE6 = {
    "Qwen3-Max": (0.0308, 0.0349, 0.0362, 0.0393, 0.0317, 0.0355, 0.0285, 0.0316),
    "DeepSeek V3": (0.0287, 0.0337, 0.0346, 0.0375, 0.0302, 0.0347, 0.0289, 0.0331),
    "Gemini3 pro": (0.0315, 0.0368, 0.0378, 0.0416, 0.0334, 0.0371, 0.0327, 0.0363),
    "GPT5.1": (0.0318, 0.0342, 0.0358, 0.0405, 0.0323, 0.0355, 0.0309, 0.0340),
}
V2_TABLE7 = {
    "EoH": (
        0.0253, 0.0319, 0.0306, 0.0232, 0.0259, 0.0137,
        0.0273, 0.0324, 0.0301, 0.0249, 0.0284, 0.0223,
    ),
    "ReEvo": (
        0.0228, 0.0256, 0.0144, 0.0227, 0.0269, 0.0189,
        0.0218, 0.0261, 0.0105, 0.0205, 0.0245, 0.0067,
    ),
    "TreEvo": (
        0.0354, 0.0392, 0.0427, 0.0278, 0.0325, 0.0158,
        0.0343, 0.0384, 0.0431, 0.0326, 0.0359, 0.0356,
    ),
}

V1_FIGURE5 = {
    "CSI300": {
        "ReEvo": (0.0406, 0.0436, 0.0374),
        "TReEvo": (0.0570, 0.0487, 0.0581),
        "TreEvo": (0.0573, 0.0543, 0.0688),
    },
    "CSI500": {
        "ReEvo": (0.0367, 0.0503, 0.0534),
        "TReEvo": (0.0652, 0.0564, 0.0676),
        "TreEvo": (0.0693, 0.0704, 0.0782),
    },
}

V2_FIGURE6 = {
    "ReEvo": (0.0211, 0.0247, 0.0224, 0.0252),
    "TReEvo": (0.0283, 0.0325, 0.0273, 0.0273),
    "TreEvo": (0.0308, 0.0362, 0.0317, 0.0285),
}

V2_FIGURE8 = {
    "ReEvo": (
        (1.00, 0.43, 0.72, 0.94, 0.64),
        (0.43, 1.00, 0.30, 0.45, 0.26),
        (0.72, 0.30, 1.00, 0.72, 0.96),
        (0.94, 0.45, 0.72, 1.00, 0.65),
        (0.64, 0.26, 0.96, 0.65, 1.00),
    ),
    "EoH": (
        (1.00, 0.17, -0.91, 0.80, 0.31),
        (0.17, 1.00, -0.10, 0.27, 0.04),
        (-0.91, -0.10, 1.00, -0.74, -0.30),
        (0.80, 0.27, -0.74, 1.00, 0.24),
        (0.31, 0.04, -0.30, 0.24, 1.00),
    ),
    "TreEvo": (
        (1.00, 0.26, 0.13, -0.18, 0.25),
        (0.26, 1.00, 0.10, -0.46, 0.35),
        (0.13, 0.10, 1.00, -0.28, 0.24),
        (-0.18, -0.46, -0.28, 1.00, -0.64),
        (0.25, 0.35, 0.24, -0.64, 1.00),
    ),
}

OPERATORS = {
    "Cross-Section": ("abs(x)", "log(x)", "+", "-", "*", "/", ">", "<"),
    "Time-Series": (
        "ts_mean(x,l)", "ts_med(x,l)", "ts_sum(x,l)", "ts_std(x,l)",
        "ts_var(x,l)", "ts_max(x,l)", "ts_min(x,l)", "ref(x,l)",
        "mad(x,l)", "delta(x,l)", "wma(x,l)", "ema(x,l)",
        "ts_cov(x,y,l)", "ts_corr(x,y,l)",
    ),
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
        raise ValueError(f"refusing to write empty output: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def safe_tar_files(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe archive member: {member.name}")
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            files[member.name] = handle.read()
    return files


def validate_inputs(scratch: Path) -> dict[str, dict[str, bytes]]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise ValueError(f"pin changed for {relative}: {observed}")
    if (scratch / "raw/paper-v1.pdf").read_bytes() != (
        scratch / "raw/paper-v1-repeat.pdf"
    ).read_bytes():
        raise ValueError("v1 PDF repeat differs")
    if (scratch / "raw/paper-v2.pdf").read_bytes() != (
        scratch / "raw/paper-v2-repeat.pdf"
    ).read_bytes():
        raise ValueError("v2 PDF repeat differs")
    bundles = {}
    for version, spec in SOURCE_VERSIONS.items():
        first = scratch / f"raw/source-{version}.tar"
        repeat = scratch / f"raw/source-{version}-repeat.tar"
        if first.read_bytes() != repeat.read_bytes():
            raise ValueError(f"{version} source repeat differs")
        files = safe_tar_files(first)
        if len(files) != spec["source_files"]:
            raise ValueError(f"{version} source file count changed: {len(files)}")
        main = files[spec["main"]]
        if hashlib.sha256(main).hexdigest() != spec["main_sha256"]:
            raise ValueError(f"{version} main TeX changed")
        bundles[version] = files
    return bundles


def tabular_rows(
    version: str,
    table: str,
    values: Mapping[str, tuple[tuple[float, ...], tuple[float, ...]]],
    datasets: tuple[str, ...],
) -> list[dict[str, Any]]:
    rows = []
    for method, (means, stds) in values.items():
        keys = [(dataset, metric) for dataset in datasets for metric in METRICS]
        for statistic, observed in (("mean", means), ("std", stds)):
            if len(observed) != len(keys):
                raise ValueError(f"bad {version} {table} row: {method} {statistic}")
            for (dataset, metric), value in zip(keys, observed):
                rows.append(
                    {
                        "version": version,
                        "table": table,
                        "method": method,
                        "dataset": dataset,
                        "metric": metric,
                        "statistic": statistic,
                        "rendered_value": f"{value:.4f}",
                        "treevo_output": method == "TreEvo",
                        "native_pipeline_executed": False,
                        "paper_result_credit": False,
                    }
                )
    return rows


def v1_result_ledger() -> list[dict[str, Any]]:
    rows = tabular_rows("v1", "Table 1", V1_TABLE1, DATASETS_V1[:2])
    rows.extend(tabular_rows("v1", "Table 2", V1_TABLE2, DATASETS_V1))
    if len(rows) != 96:
        raise ValueError(f"v1 result denominator changed: {len(rows)}")
    return rows


def flat_mean_rows(
    table: str,
    values: Mapping[str, tuple[float, ...]],
    datasets: tuple[str, ...],
) -> list[dict[str, Any]]:
    rows = []
    keys = [(dataset, metric) for dataset in datasets for metric in METRICS]
    for method, observed in values.items():
        if len(observed) != len(keys):
            raise ValueError(f"bad {table} row: {method}")
        for (dataset, metric), value in zip(keys, observed):
            rows.append(
                {
                    "version": "v2",
                    "table": table,
                    "method": method,
                    "dataset": dataset,
                    "metric": metric,
                    "statistic": "mean",
                    "rendered_value": f"{value:.4f}",
                    "treevo_output": method == "TreEvo" or table == "Table 6",
                    "native_pipeline_executed": False,
                    "paper_result_credit": False,
                }
            )
    return rows


def v2_result_ledger() -> list[dict[str, Any]]:
    rows = tabular_rows("v2", "Table 1", V2_TABLE1, DATASETS_V2[:2])
    rows.extend(tabular_rows("v2", "Table 2", V2_TABLE2, DATASETS_V2))
    for method, (wall_time, tokens) in V2_TABLE4.items():
        for metric, value in (("wall_clock_time", wall_time), ("token_cost", tokens)):
            if value is None:
                continue
            rows.append(
                {
                    "version": "v2",
                    "table": "Table 4",
                    "method": method,
                    "dataset": "all/unspecified",
                    "metric": metric,
                    "statistic": "displayed_value",
                    "rendered_value": value,
                    "treevo_output": method == "TreEvo",
                    "native_pipeline_executed": False,
                    "paper_result_credit": False,
                }
            )
    rows.extend(flat_mean_rows("Table 5", V2_TABLE5, DATASETS_V2))
    rows.extend(flat_mean_rows("Table 6", V2_TABLE6, DATASETS_V2))
    for method, observed in V2_TABLE7.items():
        keys = [
            (quarter, metric)
            for quarter in ("Q1", "Q2", "Q3", "Q4")
            for metric in ("IC", "RankIC", "ER")
        ]
        for (quarter, metric), value in zip(keys, observed):
            rows.append(
                {
                    "version": "v2",
                    "table": "Table 7",
                    "method": method,
                    "dataset": f"CSI300-{quarter}",
                    "metric": metric,
                    "statistic": "mean",
                    "rendered_value": f"{value:.4f}",
                    "treevo_output": method == "TreEvo",
                    "native_pipeline_executed": False,
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 206:
        raise ValueError(f"v2 result denominator changed: {len(rows)}")
    return rows


def operator_inventory() -> list[dict[str, Any]]:
    return [
        {"category": category, "operator": operator, "native_semantics_released": False}
        for category, operators in OPERATORS.items()
        for operator in operators
    ]


def prompt_inventory() -> list[dict[str, Any]]:
    return [
        {
            "prompt": name,
            "published_in": "v2 TeX",
            "runtime_slots": slots,
            "exact_template_recovered": True,
            "actual_filled_request_recovered": False,
            "response_recovered": False,
            "native_prompt_call_credit": False,
        }
        for name, slots in (
            ("System Prompt", 0),
            ("Initialization Prompt", 1),
            ("Crossover Prompt", 2),
            ("Mutation-R Prompt", 1),
            ("Mutation-I Prompt", 1),
            ("Mutation-F Prompt", 1),
            ("Pruning Prompt", 1),
        )
    ]


def figure_inventory() -> list[dict[str, Any]]:
    specs = [
        ("v1", 1, 3, "conceptual"), ("v1", 2, 1, "conceptual"),
        ("v1", 3, 1, "result_curves"), ("v1", 4, 4, "result_curves"),
        ("v1", 5, 2, "result_bars"),
        ("v2", 1, 3, "conceptual"), ("v2", 2, 2, "conceptual"),
        ("v2", 3, 2, "result_distributions"), ("v2", 4, 1, "result_curves"),
        ("v2", 5, 1, "result_curves"), ("v2", 6, 1, "result_bars"),
        ("v2", 7, 10, "result_histograms"), ("v2", 8, 3, "result_heatmaps"),
    ]
    return [
        {
            "version": version,
            "figure": figure,
            "panels": panels,
            "kind": kind,
            "full_resolution_visually_inspected": True,
            "legible_and_unclipped": True,
            "underlying_numeric_array_released": False,
            "native_pipeline_regenerated": False,
            "paper_result_credit": False,
        }
        for version, figure, panels, kind in specs
    ]


def exact_figure_result_ledger_v1() -> list[dict[str, Any]]:
    rows = []
    for dataset, methods in V1_FIGURE5.items():
        for method, values in methods.items():
            for run, value in enumerate(values, start=1):
                rows.append(
                    {
                        "version": "v1",
                        "figure": "Figure 5",
                        "panel": dataset,
                        "series": method,
                        "coordinate": f"Run {run}",
                        "metric": "IC",
                        "rendered_value": f"{value:.4f}",
                        "duplicate_kind": "none",
                        "duplicate_of": "",
                        "independent_numeric_information": True,
                        "native_pipeline_regenerated": False,
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 18:
        raise ValueError(f"v1 exact figure denominator changed: {len(rows)}")
    return rows


def exact_figure_result_ledger_v2() -> list[dict[str, Any]]:
    rows = []
    for method, values in V2_FIGURE6.items():
        for dataset, value in zip(DATASETS_V2, values):
            table_duplicate = method in {"ReEvo", "TreEvo"}
            rows.append(
                {
                    "version": "v2",
                    "figure": "Figure 6",
                    "panel": "ablation",
                    "series": method,
                    "coordinate": dataset,
                    "metric": "IC",
                    "rendered_value": f"{value:.4f}",
                    "duplicate_kind": (
                        "same_value_as_table_cell" if table_duplicate else "none"
                    ),
                    "duplicate_of": (
                        f"Table 2:{method}:{dataset}:IC:mean"
                        if table_duplicate else ""
                    ),
                    "independent_numeric_information": not table_duplicate,
                    "native_pipeline_regenerated": False,
                    "paper_result_credit": False,
                }
            )
    for method, matrix in V2_FIGURE8.items():
        for row_index, values in enumerate(matrix, start=1):
            for column_index, value in enumerate(values, start=1):
                if row_index == column_index:
                    duplicate_kind = "structural_correlation_diagonal"
                    duplicate_of = "correlation_self_identity"
                    independent = False
                elif row_index > column_index:
                    duplicate_kind = "symmetric_matrix_duplicate"
                    duplicate_of = (
                        f"Figure 8:{method}:Factor {column_index}:Factor {row_index}"
                    )
                    independent = False
                else:
                    duplicate_kind = "none"
                    duplicate_of = ""
                    independent = True
                rows.append(
                    {
                        "version": "v2",
                        "figure": "Figure 8",
                        "panel": method,
                        "series": f"Factor {row_index}",
                        "coordinate": f"Factor {column_index}",
                        "metric": "correlation",
                        "rendered_value": f"{value:.2f}",
                        "duplicate_kind": duplicate_kind,
                        "duplicate_of": duplicate_of,
                        "independent_numeric_information": independent,
                        "native_pipeline_regenerated": False,
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 87:
        raise ValueError(f"v2 exact figure denominator changed: {len(rows)}")
    return rows


def metric_component_execution() -> dict[str, Any]:
    rng = np.random.default_rng(250816334)
    factors = rng.normal(size=(12, 5))
    returns = 0.15 * factors + rng.normal(size=(12, 5))
    ic_values = []
    rank_values = []
    for factor_day, return_day in zip(factors, returns):
        ic_values.append(float(np.corrcoef(factor_day, return_day)[0, 1]))
        factor_rank = np.argsort(np.argsort(factor_day))
        return_rank = np.argsort(np.argsort(return_day))
        rank_values.append(float(np.corrcoef(factor_rank, return_rank)[0, 1]))
    payload = np.asarray(ic_values + rank_values, dtype="<f8").tobytes()
    return {
        "classification": "audit-declared synthetic metric-equation component",
        "seed": 250816334,
        "days": 12,
        "stocks": 5,
        "mean_ic": float(np.mean(ic_values)),
        "mean_rankic": float(np.mean(rank_values)),
        "daily_metrics_sha256": hashlib.sha256(payload).hexdigest(),
        "paper_market_data_used": False,
        "native_evaluator_used": False,
        "paper_result_credit": False,
    }


def internal_consistency() -> list[dict[str, Any]]:
    table2 = {method: means for method, (means, _stds) in V2_TABLE2.items()}
    eoh = np.asarray(table2["EoH"])
    reevo = np.asarray(table2["ReEvo"])
    treevo = np.asarray(table2["TreEvo"])
    strongest = np.maximum(eoh, reevo)
    ic_indices = np.asarray([0, 2, 4, 6])
    improvement = np.mean((treevo[ic_indices] / strongest[ic_indices] - 1) * 100)
    t_treevo = np.asarray([0.0283, 0.0325, 0.0273, 0.0273])
    reevo_ic = reevo[ic_indices]
    treevo_ic = treevo[ic_indices]
    checks = [
        (
            "v2_table2_14_31_percent",
            "passes_displayed_arithmetic",
            f"Mean per-market IC improvement over strongest EoH/ReEvo is {improvement:.4f}%.",
        ),
        (
            "v2_eoh_beats_reevo_all_cases",
            "claim_contradicted_by_displayed_table",
            f"EoH beats ReEvo in {int(np.sum(eoh > reevo))}/8 Table 2 mean cells, not all 8.",
        ),
        (
            "v2_ablation_tree_over_flat",
            "passes_displayed_arithmetic",
            "Mean per-market TReEvo/ReEvo IC lift is "
            f"{np.mean((t_treevo / reevo_ic - 1) * 100):.4f}% (paper: 23.98%).",
        ),
        (
            "v2_ablation_operators",
            "passes_displayed_arithmetic",
            "Mean per-market TreEvo/TReEvo IC lift is "
            f"{np.mean((treevo_ic / t_treevo - 1) * 100):.4f}% (paper: 10.19%).",
        ),
        (
            "v2_table1_csi300_gain",
            "passes_displayed_arithmetic",
            f"TreEvo/QFR CSI300 IC lift is {(0.0308 / 0.0302 - 1) * 100:.4f}% (paper: over 1.99%).",
        ),
        (
            "v2_table1_csi500_exception",
            "claim_matches_table",
            "TreEvo IC 0.0362 is below QFR 0.0374 on CSI500, as v2 prose acknowledges.",
        ),
        (
            "v1_spx_rankic_std",
            "high_magnitude_probable_typo",
            "v1 prints TreEvo SPX RankIC standard deviation 0.2410 around mean 0.0543; v2 prints 0.0037 around mean 0.0355.",
        ),
        (
            "v1_figure5_table2_mismatch",
            "unresolved_same_version_result_mismatch",
            "Figure 5 prints three IC runs whose averages are CSI300 "
            "ReEvo/TReEvo/TreEvo 0.0405/0.0546/0.0601 and CSI500 "
            "0.0468/0.0631/0.0726 after four-decimal rounding; Table 2 instead "
            "prints ReEvo/TreEvo means 0.0411/0.0615 and 0.0426/0.0742. "
            "The paper does not expose run lineage that reconciles them.",
        ),
        (
            "v2_duplicate_treevo_std",
            "hard_same_version_table_conflict",
            "Table 1 vs Table 2 TreEvo standard deviations differ for CSI300 IC (0.0048 vs 0.0033) and CSI500 IC (0.0051 vs 0.0041), while their means match.",
        ),
        (
            "v1_framework_population",
            "hard_method_description_conflict",
            "v1 first describes N offspring and selection from N parents + N offspring, then three N-sized operator batches and selection of N from 3N; v2 changes to one operator type per iteration and a 2N pool.",
        ),
        (
            "model_release_timing",
            "unresolved_public_provenance_conflict",
            "v1 submitted 2025-08-22 names Qwen3-Max; Alibaba history dates qwen3-max-preview to 2025-09-05. A private prerelease is possible but undisclosed.",
        ),
        (
            "code_generation_prompt",
            "missing_native_prompt",
            "Seven tree/operator templates are published, but the prompt that converts a thought tree into executable factor code is not.",
        ),
        (
            "seed_tree",
            "unfilled_runtime_slot",
            "Initialization template contains {seed_tree}; the actual seed tree(s) are not released.",
        ),
        (
            "v2_cumulative_return",
            "author_rendered_claim_only",
            "21.17% cumulative return and >58.42% excess return appear in prose/plot without dated returns, holdings, or cost lineage.",
        ),
        (
            "table4_reference",
            "minor_document_reference_error",
            "Wall-clock prose calls Table 4 a Figure via \\ref{tab:cost_comparison}.",
        ),
    ]
    return [
        {
            "claim_id": claim_id,
            "status": status,
            "audit_finding": finding,
            "paper_result_credit": False,
        }
        for claim_id, status, finding in checks
    ]


def method_specification() -> list[dict[str, Any]]:
    rows = [
        ("market_universes", "named_partial", "CSI300, CSI500, SPX, and v2 NDX are named; point-in-time constituent snapshots are absent."),
        ("data_vendor_snapshot", "missing", "No vendor, immutable files, row counts, identifiers, or checksums."),
        ("features", "specified_partial", "Open/high/low/close/volume/VWAP and forward adjustment are named; exact construction and units are absent."),
        ("calendar_timezone", "missing", "Trading calendars, time zones, holidays, and cross-market alignment are unspecified."),
        ("membership_delistings", "missing", "Constituent timing, survivorship, IPOs, delistings, and missing values are unspecified."),
        ("split", "specified", "Train 2016-01-01--2020-01-01, validation 2020-01-01--2021-01-01, test 2021-01-01--2024-01-01."),
        ("target", "specified_partial", "Future 5-day return is named; overlap, close convention, adjustment, and missing-target rules are absent."),
        ("metric_equations", "specified", "Daily cross-sectional Pearson IC and ranked IC averaged over time are given."),
        ("metric_edge_cases", "missing", "Ties, NaNs, constant vectors, winsorization, and minimum cross-section size are unspecified."),
        ("llm_primary", "ambiguous", "Qwen3-Max is unversioned; v1 predates its documented public preview."),
        ("llm_comparison_models", "ambiguous", "DeepSeek V3, Gemini3 pro, and GPT5.1 lack exact dated endpoint/snapshot identifiers."),
        ("sampling_parameters", "missing", "Temperature, top-p, max tokens, seed, retries, and concurrency are absent."),
        ("prompt_templates", "partial", "Seven v2 tree/operator templates are present; runtime fills and code-generation prompt are absent."),
        ("seed_trees", "missing", "The published initialization prompt contains only a placeholder."),
        ("population", "specified", "Population size N=10."),
        ("evaluation_budget", "specified_partial", "TreEvo/LLM EA budget is 200; baseline budgets are described but configs are not pinned."),
        ("operator_schedule", "specified_partial", "v2 rotates crossover/mutation/pruning but exact starting order and termination mapping are absent."),
        ("mutation_probabilities", "specified", "p_R=0.4, p_I=0.4, p_F=0.2."),
        ("parent_selection", "missing", "Parent sampling, replacement, tie handling, and randomness are absent."),
        ("code_generation", "missing", "No converter prompt, code schema, generated factor, or parser is released."),
        ("sandbox_validation", "missing", "Execution sandbox, allowed packages, invalid-output correction, and timeouts are absent."),
        ("selection", "specified_partial", "v2 selects best N from a 2N pool; ties and validation-vs-training objective are unclear."),
        ("random_seeds", "missing", "Five independent runs are reported without seeds or trajectories."),
        ("baseline_versions", "missing", "Providers are cited but commits, packages, environments, and exact hyperparameters are not pinned."),
        ("portfolio", "specified_partial", "Daily Top-50/Drop-5 is named; weighting, ties, cash, limits, and initial portfolio are absent."),
        ("costs", "missing", "Fees, spread, slippage, taxes, and market impact are absent."),
        ("walk_forward", "specified_partial", "2023 quarterly tests with preceding one-year training are stated; validation and retraining details are absent."),
        ("factor_outputs", "missing", "No discovered expression/code, scores, or selected-factor set is released."),
        ("raw_results", "missing", "No per-run metrics, predictions, holdings, returns, or figure arrays are released."),
        ("uncertainty", "specified_partial", "Means and +/- values are printed, but the statistic definition and raw five runs are absent."),
        ("environment", "missing", "No TreEvo dependency lock, hardware, source tree, or executable runner."),
    ]
    return [
        {"dimension": dimension, "status": status, "audit_finding": finding}
        for dimension, status, finding in rows
    ]


def revision_audit() -> list[dict[str, Any]]:
    return [
        {"dimension": "title", "v1": SOURCE_VERSIONS["v1"]["title"], "v2": SOURCE_VERSIONS["v2"]["title"], "finding": "Linear/Efficient changed to Flat/Fine-grained."},
        {"dimension": "pages", "v1": "9", "v2": "17", "finding": "v2 adds substantial appendix and prompts."},
        {"dimension": "us_universe", "v1": "SPX, DJI", "v2": "SPX, NDX", "finding": "DJI is replaced by NDX."},
        {"dimension": "table_result_cells", "v1": "96", "v2": "206", "finding": "Latest-version denominator grows by 110 cells."},
        {"dimension": "exact_figure_numeric_units", "v1": "18", "v2": "87", "finding": "Counts every explicitly printed bar label and heatmap cell; v2 includes structural and table duplicates."},
        {"dimension": "all_displayed_numeric_result_units", "v1": "114", "v2": "293", "finding": "Table and exact figure units are both included; plotted curves without exact labels are not reverse-engineered."},
        {"dimension": "traditional_table_treevo_csi300_ic", "v1": "0.0615", "v2": "0.0308", "finding": "Mean changes by -49.92%."},
        {"dimension": "traditional_table_treevo_csi500_ic", "v1": "0.0742", "v2": "0.0362", "finding": "Mean changes by -51.21%."},
        {"dimension": "cumulative_return_claim", "v1": "16.91% over strongest baseline; >100% excess vs index", "v2": "21.17% cumulative; >58.42% excess vs index", "finding": "Claim and rendered curve are materially revised without raw lineage."},
        {"dimension": "gp_budget", "v1": "20,000 evaluations", "v2": "40,000 evaluations", "finding": "Traditional evaluation denominator doubles."},
        {"dimension": "operators", "v1": "22", "v2": "22", "finding": "Displayed traditional operator count is stable."},
        {"dimension": "prompts", "v1": "sketches only", "v2": "7 templates, 7 unresolved slots", "finding": "Procedure evidence improves, but runtime calls remain absent."},
        {"dimension": "native_result_reproduction", "v1": "0/114", "v2": "0/293", "finding": "Neither version ships executable result lineage."},
    ]


def discovery_evidence(scratch: Path) -> list[dict[str, Any]]:
    rows = []
    for name in [
        "repo_search_1.json", "repo_search_2.json", "repo_search_3.json",
        "repo_search_4.json", "repo_search_5.json", "code_search_1.json",
        "code_search_2.json", "code_search_3.json",
    ]:
        data = json.loads((scratch / "discovery" / name).read_text(encoding="utf-8"))
        rows.append(
            {
                "source": name,
                "total_count": data["total_count"],
                "returned": len(data["items"]),
                "attributable_treevo_system_recovered": False,
                "negative_search_limit": "bounded public search; not proof that private, deleted, inaccessible, or unindexed code never existed",
            }
        )
    repos = json.loads(
        (scratch / "discovery/senshinel_repos.json").read_text(encoding="utf-8")
    )
    rows.append(
        {
            "source": "senshinel_repos.json",
            "total_count": len(repos),
            "returned": len(repos),
            "attributable_treevo_system_recovered": False,
            "negative_search_limit": "one identified coauthor account only; not proof about every author or nonpublic artifact",
        }
    )
    return rows


def source_provenance(scratch: Path, bundles: Mapping[str, Mapping[str, bytes]]) -> dict[str, Any]:
    return {
        "arxiv_id": ARXIV_ID,
        "authors": ["Junji Ren", "Junjie Zhao", "Shengcai Liu", "Peng Yang"],
        "license": "arXiv nonexclusive distribution license",
        "versions": SOURCE_VERSIONS,
        "repeated_downloads_byte_identical": True,
        "current_abs_repeated_byte_identical": True,
        "source_asset_files": {
            version: sorted(
                name for name in files if name.lower().endswith((".png", ".pdf"))
            )
            for version, files in bundles.items()
        },
        "visual_qa": {
            "v1_pages_inspected": 9,
            "v2_pages_inspected": 17,
            "unreadable_or_clipped_pages": 0,
        },
        "author_page_boundary": {
            "peng_yang_page_lists_v1": True,
            "peng_yang_page_code_link_for_treevo": False,
            "shengcai_liu_page_lists_code_links_for_other_papers": True,
            "shengcai_liu_page_treevo_entry_found": False,
        },
        "alibaba_model_history_sha256": sha256(
            scratch / "primary_external/alibaba_model_history.html"
        ),
        "document_reconstruction_credit": True,
        "native_system_source_credit": False,
        "paper_result_credit": False,
    }


def readme() -> str:
    return """# TreEvo paper-level replication audit

Overall verdict: **document and prompt templates reproduced; native TreEvo
experiment not reproduced**.

## What is faithfully recovered

- Both official arXiv versions are byte-pinned, repeat-download identical, and
  source-rebuilt. Extracted-token multiset overlap with the official PDFs is
  99.88% for v1 and 99.91% for v2. Every official page was rendered and visually
  checked; no page was illegible or clipped.
- The audit transcribes all **96 v1** and **206 v2** displayed table-result
  entries, plus all exact numeric labels recoverable from figures: **18 v1** and
  **87 v2**. The figure ledger identifies eight v2 table duplicates, 30 mirrored
  heatmap cells, and 15 structural diagonals instead of treating repeats as new
  information. Curves and distributions without exact labels are not inferred
  from pixels. The audit also inventories all 22 traditional operators, eight
  v2 figures (23 panels), and all seven v2 prompt templates.
- The published IC and RankIC equations execute deterministically on a synthetic
  panel under audit-declared semantics. This is metric-component evidence only.

## Why result faithfulness is still zero

Neither source bundle contains a TreEvo implementation. The public materials do
not release the market-data snapshot or point-in-time memberships, actual seed
trees, the thought-to-code prompt, model requests/responses, generated factors,
parser/sandbox, search trajectories, random seeds, baseline configurations,
predictions, holdings, daily returns, or raw table/figure arrays. Therefore the
honest end-to-end result score is **0/114 for v1 and 0/293 for v2** displayed
numeric result units. Installing packages cannot reconstruct these scientific
inputs and lineage objects.

## Important revision and consistency findings

- v1 changes materially into v2: the title, DJI-to-NDX universe, traditional
  baseline results, evaluation budgets, return claims, figures, and result
  denominator all change. v2 adds valuable prompts and walk-forward results.
- v2 says EoH beats ReEvo in all Table 2 cases, but the displayed values support
  only 6/8. Its 14.31% claim is correct specifically as the mean per-market IC
  improvement over the stronger of EoH/ReEvo.
- v2 Tables 1 and 2 repeat the same TreEvo means but conflict on CSI300 and
  CSI500 IC standard deviations. v1 prints a likely anomalous 0.2410 SPX RankIC
  standard deviation. V1 Figure 5's displayed three-run averages also fail to
  match its Table 2 ReEvo/TreEvo means, with no released run lineage to reconcile
  the difference.
- v1 was submitted on 2025-08-22 naming Qwen3-Max, while Alibaba's public model
  history dates qwen3-max-preview to 2025-09-05. This is an unresolved public
  provenance conflict; a private prerelease may have existed but is not disclosed.
- The seven published templates still omit the crucial thought-to-executable-code
  prompt, and the initialization template contains an unreleased `{seed_tree}`.

The bounded public search found no attributable implementation. That is not proof
that private, deleted, inaccessible, or unindexed artifacts never existed. Run
`scripts/audit_treevo_paper.py` to regenerate the ledgers. `--strict`
intentionally exits nonzero while end-to-end reproduction remains false.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    bundles = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    v1 = v1_result_ledger()
    v2 = v2_result_ledger()
    figure_v1 = exact_figure_result_ledger_v1()
    figure_v2 = exact_figure_result_ledger_v2()
    write_csv(output / "published_result_ledger_v1.csv", v1)
    write_csv(output / "published_result_ledger_v2.csv", v2)
    write_csv(output / "exact_figure_result_ledger_v1.csv", figure_v1)
    write_csv(output / "exact_figure_result_ledger_v2.csv", figure_v2)
    write_csv(output / "operator_inventory.csv", operator_inventory())
    write_csv(output / "prompt_inventory.csv", prompt_inventory())
    write_csv(output / "figure_inventory.csv", figure_inventory())
    write_csv(output / "method_specification_audit.csv", method_specification())
    write_csv(output / "internal_consistency_audit.csv", internal_consistency())
    write_csv(output / "version_revision_audit.csv", revision_audit())
    write_csv(output / "discovery_evidence.csv", discovery_evidence(scratch))
    write_json(output / "conditional_metric_execution.json", metric_component_execution())
    write_json(output / "source_provenance.json", source_provenance(scratch, bundles))
    (output / "README.md").write_text(readme(), encoding="utf-8")

    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_versions_audited": ["v1", "v2"],
        "official_pdf_and_source_recovered": True,
        "official_document_rebuilds_completed": 2,
        "published_numeric_table_result_cells_v1": len(v1),
        "published_numeric_table_result_cells_v2": len(v2),
        "treevo_numeric_table_cells_v1": sum(row["treevo_output"] for row in v1),
        "treevo_numeric_table_cells_v2": sum(row["treevo_output"] for row in v2),
        "published_exact_figure_numeric_units_v1": len(figure_v1),
        "published_exact_figure_numeric_units_v2": len(figure_v2),
        "figure_numeric_units_with_independent_information_v1": sum(
            row["independent_numeric_information"] for row in figure_v1
        ),
        "figure_numeric_units_with_independent_information_v2": sum(
            row["independent_numeric_information"] for row in figure_v2
        ),
        "published_numeric_result_units_v1": len(v1) + len(figure_v1),
        "published_numeric_result_units_v2": len(v2) + len(figure_v2),
        "published_result_cells_faithfully_regenerated_v1": 0,
        "published_result_cells_faithfully_regenerated_v2": 0,
        "prompt_templates_recovered_v2": 7,
        "actual_runtime_prompt_calls_recovered": 0,
        "attributable_implementation_source_files_recovered": 0,
        "full_end_to_end_pipeline_reproduced": False,
        "conditional_metric_component_executed": True,
        "paper_result_credit_for_metric_component": False,
    }
    outputs = sorted(path for path in output.iterdir() if path.name != "manifest.json")
    manifest["output_sha256"] = {path.name: sha256(path) for path in outputs}
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return int(args.strict and not manifest["full_end_to_end_pipeline_reproduced"])


if __name__ == "__main__":
    raise SystemExit(main())
