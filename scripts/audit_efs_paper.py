#!/usr/bin/env python3
"""Fail-closed paper-level audit of EFS v1 and the materially revised v2.

The original arXiv v1 is the corpus/result authority.  The current v2 is
audited separately because it adds authors, a new RMT/QP factor-weighting
module, new data through 2025, and revised results.  No author-linked EFS
implementation, checkpoint, factor pool, data snapshot, or result output was
found.  The official ASMCVaR release cited by EFS ships the 623-row benchmark
matrices used by the baseline literature, so a literal 1/N reconstruction is
credited only as cited-baseline evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.io import loadmat
from scipy.stats import t as student_t


AUDIT_DATE = "2026-08-24"
ARXIV_V1_URL = "https://arxiv.org/abs/2507.17211v1"
ARXIV_V2_URL = "https://arxiv.org/abs/2507.17211v2"
ARXIV_V1_PDF_SHA256 = "7bde1f690bab7c9f694e6f8810502884394e48de6c118a895b68fcaad1a20b26"
ARXIV_V2_PDF_SHA256 = "1f6a60bbd254265542cc37d32b71c91516ef02dcd7b5f48414120aabdb8492a0"
ARXIV_V1_SOURCE_SHA256 = "5c493ff9337af2dbeaee65ee3aed3e42a46a7efd873565c1c2a61d6d698af218"
ARXIV_V2_SOURCE_SHA256 = "0aef98b39a4f73b7389bbc1325613ced13a070480bb5d96850b1459b9c53a820"
ARXIV_API_SHA256 = "7bb35b7a209859419e85880c7718196cae0d3c29d68721c61c0575ff822fc4a8"
GITHUB_SEARCH_SHA256 = "08c082fdf7ca87ba911a2aabb0f0cf2d3e482a6feeaac9713e4578c20b2600b2"

MSSRM_URL = "https://github.com/linyizun2024/mSSRM"
MSSRM_COMMIT = "4e1be268746c3c046455e2a264279f622fceaef6"
MSSRM_TREE = "4a8a92e08c8038194b42703541374278a456db9f"
MSSRM_ARCHIVE_SHA256 = "20e6f756109f725ba56074463f5ba2a3694695dd15267d0455cd3f070386c3ac"
MSSRM_PAPER_URL = "https://papers.nips.cc/paper_files/paper/2024/file/1eaa5146756be028ad6fff1efcc8e6bd-Paper-Conference.pdf"
MSSRM_PAPER_SHA256 = "27dce79e66e5278e8c75338bf1b414954b69ef30e3599bfaea01356c123109a7"
MSSRM_SUPPLEMENT_URL = "https://papers.nips.cc/paper_files/paper/2024/file/1eaa5146756be028ad6fff1efcc8e6bd-Supplemental-Conference.zip"
MSSRM_SUPPLEMENT_SHA256 = "fe9bf3918dad5bd2f077a65c77d6e67ff6b5be97338b0ea260134cd0d94440f4"
MSSRM_SUPPLEMENT_CODE_SHA256 = {
    "PGSAl0_w0.m": "23ab9b8811e0b322247700474b1cd983a398783cc90a8298600c819ceb2d051f",
    "PGSAl0_w0run.m": "5243bcb940a9dc3b4bddf43a92367302a1ad9cf52f90bc78b7c99cd6c1db708f",
}

ASMCVAR_URL = "https://github.com/linyizun2024/ASMCVaR"
ASMCVAR_COMMIT = "0ed6a63ca02118cc305ae5d34f2cf24489c024a5"
ASMCVAR_TREE = "3a0bd2408d16d3702321e009701adcf81629e83b"
ASMCVAR_ARCHIVE_SHA256 = "6c553f0d799a8379dc01a78a02fc86b02612fea6eeb21f5b0641c327b8801f9a"
ASMCVAR_PAPER_URL = "https://proceedings.mlr.press/v235/lin24w.html"
ASMCVAR_PAPER_PDF_URL = "https://raw.githubusercontent.com/mlresearch/v235/main/assets/lin24w/lin24w.pdf"
ASMCVAR_PAPER_SHA256 = "a2790162761a5436d628ece00c66aed2564ea0d9633f4483d57e022602c7e09d"
ASMCVAR_PAPER_PAGES = 17
ASMCVAR_DATASETS = {
    "FF25": "FF25new",
    "FF25EU": "FF25EUnew",
    "FF32": "FF32new",
    "FF49": "FF49new",
    "FF100": "FF100new",
    "FF100MEOP": "FF100MEOPnew",
}
ASMCVAR_ORIGINAL_T60_VALUES = {
    ("FF25", 10): {"CW": "973.23", "SR": "0.2610"},
    ("FF25EU", 10): {"CW": "122.82", "SR": "0.2758"},
    ("FF32", 10): {"CW": "1122.76", "SR": "0.2638"},
    ("FF49", 10): {"CW": "758.66", "SR": "0.2339"},
    ("FF100", 10): {"CW": "966.32", "SR": "0.2446"},
    ("FF100MEOP", 10): {"CW": "783.47", "SR": "0.2363"},
    ("FF25", 15): {"CW": "827.18", "SR": "0.2541"},
    ("FF25EU", 15): {"CW": "123.13", "SR": "0.2765"},
    ("FF32", 15): {"CW": "1303.80", "SR": "0.2615"},
    ("FF49", 15): {"CW": "694.83", "SR": "0.2286"},
    ("FF100", 15): {"CW": "1126", "SR": "0.2503"},
    ("FF100MEOP", 15): {"CW": "712.45", "SR": "0.2326"},
    ("FF25", 20): {"CW": "872.03", "SR": "0.2558"},
    ("FF25EU", 20): {"CW": "113.28", "SR": "0.2713"},
    ("FF32", 20): {"CW": "1317.01", "SR": "0.2603"},
    ("FF49", 20): {"CW": "767.61", "SR": "0.2300"},
    ("FF100", 20): {"CW": "1117.20", "SR": "0.2501"},
    ("FF100MEOP", 20): {"CW": "714.49", "SR": "0.2322"},
}
ASMCVAR_V1_ROW_BY_SPARSITY = {10: 7, 15: 15, 20: 23}
ASMCVAR_V2_ROW_BY_SPARSITY = {10: 7, 15: 15}
ASMCVAR_OBSERVATIONS = {"FF25": 623, "FF25EU": 391, "FF32": 623, "FF49": 623, "FF100": 623, "FF100MEOP": 623}
ASMCVAR_ASSETS = {"FF25": 25, "FF25EU": 25, "FF32": 32, "FF49": 49, "FF100": 100, "FF100MEOP": 100}
ASMCVAR_ALPHA_P_VALUES = {
    ("FF25", 10): {"alpha": "0.0022", "p_value": "0.0006"},
    ("FF25EU", 10): {"alpha": "0.0027", "p_value": "0"},
    ("FF32", 10): {"alpha": "0.0027", "p_value": "0.0002"},
    ("FF49", 10): {"alpha": "0.0029", "p_value": "0.0049"},
    ("FF100", 10): {"alpha": "0.0023", "p_value": "0.0038"},
    ("FF100MEOP", 10): {"alpha": "0.0020", "p_value": "0.0060"},
    ("FF25", 15): {"alpha": "0.0019", "p_value": "0.0029"},
    ("FF25EU", 15): {"alpha": "0.0027", "p_value": "0"},
    ("FF32", 15): {"alpha": "0.0025", "p_value": "0.0001"},
    ("FF49", 15): {"alpha": "0.0024", "p_value": "0.0112"},
    ("FF100", 15): {"alpha": "0.0025", "p_value": "0.0012"},
    ("FF100MEOP", 15): {"alpha": "0.0017", "p_value": "0.0109"},
    ("FF25", 20): {"alpha": "0.0019", "p_value": "0.0017"},
    ("FF25EU", 20): {"alpha": "0.0025", "p_value": "0"},
    ("FF32", 20): {"alpha": "0.0024", "p_value": "0.0001"},
    ("FF49", 20): {"alpha": "0.0023", "p_value": "0.0098"},
    ("FF100", 20): {"alpha": "0.0024", "p_value": "0.0010"},
    ("FF100MEOP", 20): {"alpha": "0.0016", "p_value": "0.0114"},
}
ASMCVAR_OVERLAP_VALUES = {
    "FF25": {"p10_15_mean": "0.9115", "p10_15_std": "0.1182", "p15_20_mean": "0.9554", "p15_20_std": "0.0808"},
    "FF25EU": {"p10_15_mean": "0.9147", "p10_15_std": "0.1215", "p15_20_mean": "0.9553", "p15_20_std": "0.0854"},
    "FF32": {"p10_15_mean": "0.8919", "p10_15_std": "0.1307", "p15_20_mean": "0.9348", "p15_20_std": "0.0958"},
    "FF49": {"p10_15_mean": "0.9468", "p10_15_std": "0.0832", "p15_20_mean": "0.9372", "p15_20_std": "0.0825"},
    "FF100": {"p10_15_mean": "0.9222", "p10_15_std": "0.1060", "p15_20_mean": "0.9543", "p15_20_std": "0.0766"},
    "FF100MEOP": {"p10_15_mean": "0.9018", "p10_15_std": "0.1154", "p15_20_mean": "0.9478", "p15_20_std": "0.0724"},
}
ASMCVAR_DATA_SHA256 = {
    "FF25new": "0f4c1e91708ce9098d12e81525468dcaa5946d5bff508db7eb953d3cd43744f4",
    "FF32new": "3eb4af4e3b3080fb226364d3b84e2d392366b9be4ba95ecf863346f2d3d143ec",
    "FF49new": "4e86d65e11ba828d4b33147d18a95ebd31ccce313fa10f4b4693aed4a2b79796",
    "FF100new": "9ceca78a8351bb785ad8943aeee4c089c280d760dcac6d4a94f5a42552e8a5ba",
    "FF100MEOPnew": "c62941fc24e338096faa24b782a21b8ada8c0e7f029fcf415271e2eaa086a039",
    "FF100MEINVnew": "71059496600edd65b88e4b558423256cfbb05d1b4c10369e7674469d836553e9",
    "FF25EUnew": "d3897865a555c8b9c8624b0ba7e0dab920c3cf0a783dec4b7a362fdd03732915",
}

MSSRM_OCTAVE_VERSION = "9.2.0"
MSSRM_DATASETS = {
    "FF25": "FF25new",
    "FF32": "FF32new",
    "FF49": "FF49new",
    "FF100": "FF100new",
    "FF100MEOP": "FF100MEOPnew",
}
MSSRM_ORIGINAL_DATASETS = {
    "FF25": "FF25new",
    "FF25EU": "FF25EUnew",
    "FF32": "FF32new",
    "FF49": "FF49new",
    "FF100": "FF100new",
    "FF100MEINV": "FF100MEINVnew",
}
MSSRM_OBSERVATIONS = {
    "FF25": 623,
    "FF25EU": 391,
    "FF32": 623,
    "FF49": 623,
    "FF100": 623,
    "FF100MEINV": 623,
    "FF100MEOP": 623,
}
MSSRM_ORIGINAL_T60_VALUES = {
    ("FF25", 10): {"CW": "615.34", "SR": "0.2481"},
    ("FF25EU", 10): {"CW": "126.02", "SR": "0.2712"},
    ("FF32", 10): {"CW": "991.89", "SR": "0.2612"},
    ("FF49", 10): {"CW": "285.02", "SR": "0.2151"},
    ("FF100", 10): {"CW": "527.09", "SR": "0.2290"},
    ("FF100MEINV", 10): {"CW": "375.75", "SR": "0.2217"},
    ("FF25", 15): {"CW": "614.71", "SR": "0.2481"},
    ("FF25EU", 15): {"CW": "125.19", "SR": "0.2708"},
    ("FF32", 15): {"CW": "996.32", "SR": "0.2615"},
    ("FF49", 15): {"CW": "262.54", "SR": "0.2135"},
    ("FF100", 15): {"CW": "522.28", "SR": "0.2289"},
    ("FF100MEINV", 15): {"CW": "383.44", "SR": "0.2232"},
    ("FF25", 20): {"CW": "614.70", "SR": "0.2481"},
    ("FF25EU", 20): {"CW": "125.19", "SR": "0.2708"},
    ("FF32", 20): {"CW": "996.23", "SR": "0.2615"},
    ("FF49", 20): {"CW": "262.06", "SR": "0.2134"},
    ("FF100", 20): {"CW": "515.50", "SR": "0.2285"},
    ("FF100MEINV", 20): {"CW": "384.65", "SR": "0.2234"},
}
MSSRM_V1_ROW_BY_SPARSITY = {10: 6, 15: 14, 20: 22}
MSSRM_V2_ROW_BY_SPARSITY = {10: 6, 15: 14}
MSSRM_CW_SHA256 = {
    ("FF25", 10): "bebe50b0c5660a2f71cd858beaf9e6a0ee07716def50eebc1306dbf8309bd491",
    ("FF25", 15): "e3f6c19cdfdfb297402f773d6b6182b4598cdc6d3e3cb2726a8793dc557ba9be",
    ("FF25", 20): "db5ffa0699304a63e5e5aab0a483e5f782e4a9388dcb901800f8a2a83c2b03ab",
    ("FF32", 10): "92cad40eb1380a6782169cefe29597235285d092dba3ee8ff7bb914ab426e0fd",
    ("FF32", 15): "baec5f111c166a2d6dc731839bb09274d935c217e0ece512abe31a64b6957324",
    ("FF32", 20): "7039cff0c527daaad6cf59608df21097cab15ba849d4b530c177398fa362b6c2",
    ("FF49", 10): "5738fcd4a3a620dd52cbaec6817bb74e1971f6607c737f2688ae25ee26e0ff38",
    ("FF49", 15): "fafd9b3c5c0c134668d421237f2aa245670c3168b172f6d0d92a12ca8a15f219",
    ("FF49", 20): "73139b9e4d4450c4e25d8a43e6799c3c8abd2c9bfcb929a0b1d2ca8caaf8b117",
    ("FF100", 10): "a6dda551f1e401e45820fd8a90205386de2914f5fa9a20f3ad7e645a5b0becec",
    ("FF100", 15): "29454ad4d6122051d91f71586153bbe281f6e9b5a20a3a628b890c44e4e16f21",
    ("FF100", 20): "4ec492771f9c9e8e17ab7775814b46ad81a60d34b262a052e1770b944c75829f",
    ("FF100MEOP", 10): "d7335570766fdb6a1b3fcf53a881e752fa523a4ec5412ecce1f96ae54b5dc653",
    ("FF100MEOP", 15): "b5976b773f39f9210282cb9b9a61329cc5605d5272184a0f32b14ff168a2bb81",
    ("FF100MEOP", 20): "19b9acb22a0e7fdea6deaf47e7298700081192889f147845a8c9718cf153ef36",
    ("FF25EU", 10): "8013d469c21f45196337a75f86a6c42dcbad657ad80fce9ad8389d54fc6324b0",
    ("FF25EU", 15): "11429d2ce75c7839b04f7d4f94365b66c0d2504debf082a8fb9abd85c158e8d0",
    ("FF25EU", 20): "c3eaf4466216cebb41b876dbf6251f9afa53f1e3e2f286ba152cde2d12afe727",
    ("FF100MEINV", 10): "562f59f9c43fbd69a45290bef1654c9c81c1d95ed138289376066f6013f41b19",
    ("FF100MEINV", 15): "df4935359d8c14142e8fafa48271f00a093a3260f00fc727fbfcdac0a9b6dda4",
    ("FF100MEINV", 20): "22e9df4224359ef939c31bced8d5eb49f18625162575bf1251e59debd29a87ff",
}

V1_TABLE_SPECS = (
    ("benchmark", "tables/benchmark.tex", "tab:bench_performance_metrics", 2, 15, (15,)),
    ("real_market", "tables/market_performance.tex", "tab:performance_metrics", 2, 9, (9,)),
    ("ablation", "tables/ablations.tex", "tab:ablation_studies", 1, 10, (10,)),
    ("score_temperature", "tables/s2w_test.tex", "tab-s2w_temp", 2, 16, (16,)),
    ("transaction_cost", "tables/transaction_cost.tex", "tab:trans_cost_results_grouped", 2, 9, (9,)),
)

V2_TABLE_SPECS = (
    ("benchmark", "tab:bench_performance_metrics", 2, 12, (12,), None),
    ("real_market", "tab:market_performance_metrics", 2, 12, (12,), None),
    ("weight_ablation", "tab:ablation", 2, 12, (12, 8), None),
    ("input_ablation", "tab:ablation_inputs", 1, 12, (12,), None),
    ("weighting_schemes", "tab:e2e_weight", 2, 12, (12,), None),
    ("factor_examples", "tab:factor_examples", 0, 1, (1,), 2),
    ("post_cutoff_oos", "tab:oos", 2, 12, (12,), None),
    ("turnover_cost", "tab:turnover", 1, 15, (15,), None),
)

V1_EXPECTED_TABLE_COUNTS = {
    "benchmark": 420,
    "real_market": 135,
    "ablation": 100,
    "score_temperature": 64,
    "transaction_cost": 54,
}
V2_EXPECTED_TABLE_COUNTS = {
    "benchmark": 240,
    "real_market": 180,
    "weight_ablation": 164,
    "input_ablation": 60,
    "weighting_schemes": 60,
    "factor_examples": 5,
    "post_cutoff_oos": 108,
    "turnover_cost": 60,
}

V1_RESULT_FIGURES = {
    "CSI_300_portfolio_performance_comparison.pdf",
    "HSI_tech_45_performance_2022_2023_final.pdf",
    "HSI_tech_45_portfolio_performance_comparison.pdf",
    "NASDAQ_50_performance_2022_2023_final.pdf",
    "NASDAQ_50_portfolio_performance_comparison.pdf",
    "csi300_factor_analysis.pdf",
    "cw_band_plot.pdf",
    "hsi45_factor_analysis.pdf",
    "hsi_portfolio_performance_comparison.pdf",
    "nasdaq_dual_analysis.pdf",
    "sparse_decay.pdf",
    "top10_tickers_by_year_market.pdf",
    "top_10_tickers_by_dataset.pdf",
    "us50_factor_analysis.pdf",
    "us_portfolio_performance_comparison.pdf",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_git(source: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source), *args],
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


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _remove_tex_wrappers(value: str) -> str:
    text = value.strip()
    previous = None
    while previous != text:
        previous = text
        text = re.sub(
            r"\\(?:textbf|emph|ttfamily|scriptsize|footnotesize)\{([^{}]*)\}",
            r"\1",
            text,
        )
    text = text.replace("$", "").replace(r"\%", "%")
    text = text.replace(r"\pm", "±").replace(" ", "")
    text = text.replace(r"\!", "").replace("~", "")
    text = text.replace(r"\textminus", "-")
    text = text.replace(r"\-", "-")
    text = re.sub(r"^\{?-\}?", "-", text)
    return text


VALUE_RE = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)(?:±-?(?:\d+(?:\.\d+)?|\.\d+))?%?$")


def _result_value(value: str) -> str | None:
    cleaned = _remove_tex_wrappers(value)
    return cleaned if VALUE_RE.fullmatch(cleaned) else None


def _row_fragments(tabular: str) -> list[list[str]]:
    clean_lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in tabular.splitlines()]
    rows: list[list[str]] = []
    buffer = ""
    for line in clean_lines:
        buffer += " " + line.strip()
        while r"\\" in buffer:
            row, buffer = buffer.split(r"\\", 1)
            rows.append([cell.strip() for cell in row.split("&")])
    return rows


def _tabular_for_label(text: str, label: str) -> str:
    marker = rf"\label{{{label}}}"
    location = text.find(marker)
    if location < 0:
        raise ValueError(f"missing table label: {label}")
    start = text.rfind(r"\begin{table", 0, location)
    end = text.find(r"\end{table", location)
    if start < 0 or end < 0:
        raise ValueError(f"could not isolate table: {label}")
    table = text[start:end]
    tabular_start = table.find(r"\begin{tabular}")
    if tabular_start < 0:
        tabular_start = table.find(r"\begin{tabular}{")
    tabular_end = table.rfind(r"\end{tabular}")
    if tabular_start < 0 or tabular_end < 0:
        raise ValueError(f"could not isolate tabular: {label}")
    return table[tabular_start:tabular_end]


def _clean_label(value: str) -> str:
    text = re.sub(r"\\multirow\{[^{}]*\}\{[^{}]*\}\{", "", value)
    text = re.sub(r"\\makecell\{", "", text)
    text = re.sub(r"\\(?:textbf|emph)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+", " ", text)
    text = text.replace("{", " ").replace("}", " ").replace("$", " ")
    return " ".join(text.split())


def _extract_table(
    version: str,
    table_id: str,
    tabular: str,
    descriptor_cells: int,
    expected_result_cells: int,
    allowed_counts: tuple[int, ...],
    fixed_result_index: int | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    row_index = 0
    for cells in _row_fragments(tabular):
        selected: list[tuple[int, str]] = []
        if fixed_result_index is not None:
            if len(cells) > fixed_result_index:
                value = _result_value(cells[fixed_result_index])
                if value is not None:
                    selected = [(0, value)]
        elif len(cells) >= descriptor_cells:
            result_cells = cells[descriptor_cells:]
            logical_position = 0
            for cell in result_cells:
                multicolumn = re.search(r"\\multicolumn\{(\d+)\}", cell)
                if multicolumn:
                    logical_position += int(multicolumn.group(1))
                    continue
                parsed = _result_value(cell)
                if parsed is not None:
                    selected.append((logical_position, parsed))
                logical_position += 1
        if len(selected) not in allowed_counts:
            continue
        descriptors = cells[:descriptor_cells] if fixed_result_index is None else cells[:2]
        row_label = " | ".join(filter(None, (_clean_label(value) for value in descriptors)))
        for result_position, paper_value in selected:
            records.append(
                {
                    "paper_version": version,
                    "paper_table": table_id,
                    "row_index": row_index,
                    "row_label": row_label,
                    "result_position": result_position,
                    "dataset": "",
                    "metric": "",
                    "paper_value": paper_value,
                    "cited_baseline_recomputed_value": "",
                    "cited_baseline_match_at_paper_precision": False,
                    "native_efs_result_credit": False,
                    "paper_result_credit": False,
                    "version_lineage_status": "version_specific_result",
                }
            )
        row_index += 1
    if records and max(int(row["result_position"]) for row in records) >= expected_result_cells:
        raise ValueError(f"result position overflow in {version} {table_id}")
    return records


def _assign_dimensions(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        version = str(row["paper_version"])
        table = str(row["paper_table"])
        pos = int(row["result_position"])
        if version == "v1" and table == "benchmark":
            datasets, metrics = ("FF25", "FF32", "FF49", "FF100", "FF100MEOP"), ("CW", "SR", "MDD")
        elif version == "v1" and table in {"real_market", "transaction_cost"}:
            datasets, metrics = ("US50", "HSI45", "CSI300"), ("CW", "SR", "MDD")
        elif version == "v1" and table == "ablation":
            datasets, metrics = ("US50", "HSI45"), ("CW", "SR", "MDD", "RankIC", "RankICIR")
        elif version == "v1" and table == "score_temperature":
            datasets, metrics = ("US50", "HSI45"), tuple(
                f"temp={temperature}:{metric}"
                for temperature in ("0.1", "0.5", "1.0", "2.0")
                for metric in ("CW", "SR")
            )
        elif version == "v2" and table == "benchmark":
            datasets, metrics = ("FF25", "FF32", "FF49", "FF100"), ("CW", "SR", "MDD")
        elif version == "v2" and table in {"real_market", "weight_ablation", "input_ablation", "post_cutoff_oos"}:
            datasets, metrics = ("US50", "HSI45", "CSI300"), ("CW", "CAGR", "SR", "MDD")
        elif version == "v2" and table == "weighting_schemes":
            datasets, metrics = ("US50", "HSI45", "CSI300"), ("m=5", "m=10", "m=15", "m=20")
        elif version == "v2" and table == "turnover_cost":
            datasets, metrics = ("US50", "HSI45", "CSI300"), ("0bp", "5bp", "10bp", "20bp", "turnover")
        elif version == "v2" and table == "factor_examples":
            row["dataset"] = "reported_in_row"
            row["metric"] = "RankIC"
            continue
        else:
            raise ValueError(f"dimension map missing: {version} {table}")
        width = len(metrics)
        row["dataset"] = datasets[pos // width]
        row["metric"] = metrics[pos % width]


def parse_v1_results(paper_root: Path) -> list[dict[str, Any]]:
    source = paper_root / "source_v1"
    records: list[dict[str, Any]] = []
    for table_id, filename, label, descriptors, expected, allowed in V1_TABLE_SPECS:
        text = (source / filename).read_text(encoding="utf-8")
        tabular = _tabular_for_label(text, label)
        records.extend(_extract_table("v1", table_id, tabular, descriptors, expected, allowed))
    _assign_dimensions(records)
    counts = Counter(str(row["paper_table"]) for row in records)
    if counts != Counter(V1_EXPECTED_TABLE_COUNTS):
        raise ValueError(f"v1 result census drifted: {counts}")
    return records


def parse_v2_results(paper_root: Path) -> list[dict[str, Any]]:
    source = paper_root / "source_v2" / "anonymous-submission-latex-2026.tex"
    text = source.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    for table_id, label, descriptors, expected, allowed, fixed_index in V2_TABLE_SPECS:
        tabular = _tabular_for_label(text, label)
        records.extend(
            _extract_table("v2", table_id, tabular, descriptors, expected, allowed, fixed_index)
        )
    _assign_dimensions(records)
    counts = Counter(str(row["paper_table"]) for row in records)
    if counts != Counter(V2_EXPECTED_TABLE_COUNTS):
        raise ValueError(f"v2 result census drifted: {counts}")
    return records


def _archive_sha(source: Path, commit: str) -> str:
    return bytes_sha256(run_git(source, "archive", "--format=tar", commit, binary=True))


def validate_inputs(paper_root: Path, mssrm: Path, asm_cvar: Path) -> dict[str, Any]:
    expected = {
        paper_root / "arxiv_v1.pdf": ARXIV_V1_PDF_SHA256,
        paper_root / "arxiv_v1_source.tar": ARXIV_V1_SOURCE_SHA256,
        paper_root / "arxiv_current.pdf": ARXIV_V2_PDF_SHA256,
        paper_root / "arxiv_source.tar": ARXIV_V2_SOURCE_SHA256,
        paper_root / "author_hosted.pdf": ARXIV_V1_PDF_SHA256,
        paper_root / "arxiv_api.xml": ARXIV_API_SHA256,
        paper_root / "github_search_arxiv.json": GITHUB_SEARCH_SHA256,
        paper_root / "github_search_title.json": GITHUB_SEARCH_SHA256,
        paper_root / "github_search_efs.json": GITHUB_SEARCH_SHA256,
    }
    data_dir = asm_cvar / "Codes_for_Experiments_in_Paper" / "DataSets"
    expected.update({data_dir / f"{name}.mat": value for name, value in ASMCVAR_DATA_SHA256.items()})
    for path, value in expected.items():
        if sha256(path) != value:
            raise ValueError(f"pinned input hash mismatch: {path}")
    for repo, commit, tree, archive in (
        (mssrm, MSSRM_COMMIT, MSSRM_TREE, MSSRM_ARCHIVE_SHA256),
        (asm_cvar, ASMCVAR_COMMIT, ASMCVAR_TREE, ASMCVAR_ARCHIVE_SHA256),
    ):
        if run_git(repo, "rev-parse", "HEAD").strip() != commit:
            raise ValueError(f"commit mismatch: {repo}")
        if run_git(repo, "rev-parse", "HEAD^{tree}").strip() != tree:
            raise ValueError(f"tree mismatch: {repo}")
        if _archive_sha(repo, commit) != archive:
            raise ValueError(f"archive mismatch: {repo}")
    searches = [json.loads((paper_root / name).read_text()) for name in (
        "github_search_arxiv.json", "github_search_title.json", "github_search_efs.json"
    )]
    if any(payload.get("total_count") != 0 for payload in searches):
        raise ValueError("GitHub repository search no longer represents an empty snapshot")
    return {"validated_file_count": len(expected), "github_search_total": 0}


def baseline_metrics(asm_cvar: Path) -> dict[str, dict[str, float]]:
    data_dir = asm_cvar / "Codes_for_Experiments_in_Paper" / "DataSets"
    mapping = {
        "FF25": "FF25new",
        "FF32": "FF32new",
        "FF49": "FF49new",
        "FF100": "FF100new",
        "FF100MEOP": "FF100MEOPnew",
    }
    output: dict[str, dict[str, float]] = {}
    for dataset, filename in mapping.items():
        matrix = np.asarray(loadmat(data_dir / f"{filename}.mat")["data"], dtype=float)
        if matrix.shape[0] != 623:
            raise ValueError(f"baseline matrix row count drifted: {filename}")
        # The 623 price-relative rows define 622 transitions: row zero is the
        # initial observation, matching the baseline-paper moving-window setup.
        returns = matrix[1:].mean(axis=1) - 1.0
        wealth = np.cumprod(1.0 + returns)
        peaks = np.maximum.accumulate(np.r_[1.0, wealth])[:-1]
        output[dataset] = {
            "CW": float(wealth[-1]),
            "SR": float(returns.mean() / returns.std(ddof=1)),
            "MDD": float(np.max(1.0 - wealth / peaks)),
            "rows": float(matrix.shape[0]),
            "assets": float(matrix.shape[1]),
        }
    return output


def validate_asmcvar_original_input(original_root: Path) -> dict[str, Any]:
    paper = original_root / "paper.pdf"
    if sha256(paper) != ASMCVAR_PAPER_SHA256:
        raise ValueError("pinned ASMCVaR PMLR paper hash mismatch")
    info = subprocess.run(["pdfinfo", str(paper)], check=True, capture_output=True, text=True).stdout
    pages = int(re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE).group(1))
    if pages != ASMCVAR_PAPER_PAGES:
        raise ValueError(f"ASMCVaR PMLR paper page count drifted: {pages}")
    return {"paper_sha256": ASMCVAR_PAPER_SHA256, "paper_pages": pages}


def load_asmcvar_native_metrics(
    results_root: Path, *, allow_missing: bool = False
) -> dict[tuple[str, int], dict[str, Any]]:
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for dataset, source_name in ASMCVAR_DATASETS.items():
        for sparsity in (10, 15, 20):
            path = results_root / f"asmcvar_{source_name}_m{sparsity}_matlab_run1.mat"
            if not path.exists() and allow_missing:
                continue
            payload = loadmat(path)
            wealth = np.asarray(payload["CW"], dtype="<f8").reshape(-1)
            weights = np.asarray(payload["all_w"], dtype="<f8")
            observations = ASMCVAR_OBSERVATIONS[dataset]
            assets = ASMCVAR_ASSETS[dataset]
            runout = int(np.asarray(payload["runout"]).reshape(-1)[0])
            final_t = int(np.asarray(payload["t"]).reshape(-1)[0])
            if wealth.shape != (observations,) or weights.shape != (assets, observations):
                raise ValueError(f"invalid ASMCVaR result shape: {path}")
            if runout != 0 or final_t != observations:
                raise ValueError(f"incomplete ASMCVaR execution: {path}")
            if not np.isfinite(wealth).all() or not np.isfinite(weights).all() or np.any(wealth <= 0):
                raise ValueError(f"non-finite ASMCVaR result: {path}")
            if np.max(np.abs(weights.sum(axis=0) - 1.0)) > 1e-10 or float(weights.min()) < -1e-12:
                raise ValueError(f"infeasible ASMCVaR weights: {path}")
            returns = wealth[1:] / wealth[:-1] - 1.0
            peaks = np.maximum.accumulate(wealth)
            repeat_path = results_root / f"asmcvar_{source_name}_m{sparsity}_matlab_run2.mat"
            repeat_equal = None
            repeat_cw_sha256 = ""
            if repeat_path.exists():
                repeated = np.asarray(loadmat(repeat_path)["CW"], dtype="<f8").reshape(-1)
                repeat_equal = bool(np.array_equal(wealth, repeated))
                repeat_cw_sha256 = bytes_sha256(repeated.tobytes(order="C"))
            output[(dataset, sparsity)] = {
                "CW": float(wealth[-1]),
                "SR": float(returns.mean() / returns.std(ddof=0)),
                "MDD": float(np.max(1.0 - wealth / peaks)),
                "wealth": wealth,
                "weights": weights,
                "observations": observations,
                "assets": assets,
                "cw_sha256": bytes_sha256(wealth.tobytes(order="C")),
                "weights_sha256": bytes_sha256(weights.tobytes(order="C")),
                "repeat_path_present": repeat_path.exists(),
                "repeat_path_equal": repeat_equal,
                "repeat_cw_sha256": repeat_cw_sha256,
                "matlab_release": "2023b",
            }
    if not allow_missing and len(output) != 18:
        raise ValueError(f"expected 18 ASMCVaR native executions, found {len(output)}")
    return output


def apply_asmcvar_credit(
    rows: list[dict[str, Any]], metrics: Mapping[tuple[str, int], Mapping[str, Any]]
) -> list[dict[str, Any]]:
    version = str(rows[0]["paper_version"])
    row_by_sparsity = ASMCVAR_V1_ROW_BY_SPARSITY if version == "v1" else ASMCVAR_V2_ROW_BY_SPARSITY
    sparsity_by_row = {row_index: sparsity for sparsity, row_index in row_by_sparsity.items()}
    audit_rows: list[dict[str, Any]] = []
    for row in rows:
        row_index = int(row["row_index"])
        if row["paper_table"] != "benchmark" or row_index not in sparsity_by_row:
            continue
        sparsity = sparsity_by_row[row_index]
        dataset, metric = str(row["dataset"]), str(row["metric"])
        native = metrics[(dataset, sparsity)]
        reproduced = float(native[metric])
        rendered = _format_like(reproduced, str(row["paper_value"]))
        match = rendered == row["paper_value"]
        row["cited_baseline_recomputed_value"] = f"{reproduced:.12g}"
        row["cited_baseline_match_at_paper_precision"] = match
        row["paper_result_credit"] = match
        audit_rows.append(
            {
                "paper_version": version,
                "sparsity": sparsity,
                "dataset": dataset,
                "metric": metric,
                "paper_value": row["paper_value"],
                "recomputed_value": f"{reproduced:.12g}",
                "recomputed_at_paper_precision": rendered,
                "match_at_paper_precision": match,
                "matlab_release": native["matlab_release"],
                "cw_sha256": native["cw_sha256"],
                "weights_sha256": native["weights_sha256"],
                "native_asmcvar_source_evidence": True,
                "native_efs_evidence": False,
                "paper_result_credit": match,
            }
        )
    expected = 45 if version == "v1" else 24
    if len(audit_rows) != expected:
        raise ValueError(f"expected {expected} ASMCVaR comparison cells for {version}")
    return audit_rows


def original_asmcvar_paper_conformance(
    metrics: Mapping[tuple[str, int], Mapping[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (dataset, sparsity), paper_values in ASMCVAR_ORIGINAL_T60_VALUES.items():
        native = metrics[(dataset, sparsity)]
        for metric in ("CW", "SR"):
            paper_value = paper_values[metric]
            reproduced = float(native[metric])
            rendered = _format_like(reproduced, paper_value)
            match = rendered == paper_value
            rows.append(
                {
                    "dataset": dataset,
                    "sparsity": sparsity,
                    "lookback": 60,
                    "metric": metric,
                    "paper_value": paper_value,
                    "recomputed_value": f"{reproduced:.12g}",
                    "recomputed_at_paper_precision": rendered,
                    "match_at_paper_precision": match,
                    "paper_location": "Table 4" if metric == "CW" else "Table 5",
                    "matlab_release": native["matlab_release"],
                    "cw_sha256": native["cw_sha256"],
                    "original_asmcvar_paper_result_credit": match,
                    "native_efs_evidence": False,
                }
            )
    if len(rows) != 36:
        raise ValueError("expected 36 original ASMCVaR CW/SR cells")
    return rows


def _uniform_buy_hold_path(data: np.ndarray) -> np.ndarray:
    observations, assets = data.shape
    cumulative = 1.0
    path = np.ones(observations, dtype=float)
    day_weight = np.ones(assets, dtype=float) / assets
    evolved_weight = np.zeros(assets, dtype=float)
    for index in range(observations):
        if index >= 5:
            day_weight = evolved_weight.copy()
        day_weight = day_weight / day_weight.sum()
        daily_return = float(data[index] @ day_weight)
        cumulative *= daily_return
        path[index] = cumulative
        evolved_weight = day_weight * data[index] / daily_return
    return path


def asmcvar_alpha_conformance(
    metrics: Mapping[tuple[str, int], Mapping[str, Any]], asm_cvar: Path
) -> list[dict[str, Any]]:
    data_root = asm_cvar / "Codes_for_Experiments_in_Paper" / "DataSets"
    market_returns: dict[str, np.ndarray] = {}
    for dataset, source_name in ASMCVAR_DATASETS.items():
        data = np.asarray(loadmat(data_root / f"{source_name}.mat")["data"], dtype=float)
        market = _uniform_buy_hold_path(data)
        market_returns[dataset] = market[1:] / market[:-1] - 1.0
    rows: list[dict[str, Any]] = []
    for (dataset, sparsity), paper_values in ASMCVAR_ALPHA_P_VALUES.items():
        strategy = np.asarray(metrics[(dataset, sparsity)]["wealth"], dtype=float)
        strategy_returns = strategy[1:] / strategy[:-1] - 1.0
        market = market_returns[dataset]
        design = np.column_stack([np.ones(market.size), market])
        covariance = np.linalg.inv(design.T @ design)
        estimate = covariance @ design.T @ strategy_returns
        residual = strategy_returns - design @ estimate
        squared_error = float(residual @ residual)
        degrees = market.size - 2
        standard_error = np.sqrt(np.diag(covariance) * squared_error / degrees)
        t_value = estimate / standard_error
        values = {"alpha": float(estimate[0]), "p_value": float(student_t.cdf(-t_value[0], degrees))}
        for metric in ("alpha", "p_value"):
            paper_value = paper_values[metric]
            rendered = _format_like(values[metric], paper_value)
            match = rendered == paper_value
            rows.append(
                {
                    "dataset": dataset,
                    "sparsity": sparsity,
                    "metric": metric,
                    "paper_value": paper_value,
                    "recomputed_value": f"{values[metric]:.12g}",
                    "recomputed_at_paper_precision": rendered,
                    "match_at_paper_precision": match,
                    "paper_location": "Table 3",
                    "original_asmcvar_paper_result_credit": match,
                    "native_efs_evidence": False,
                }
            )
    if len(rows) != 36:
        raise ValueError("expected 36 original ASMCVaR alpha/p-value cells")
    return rows


def asmcvar_overlap_conformance(
    metrics: Mapping[tuple[str, int], Mapping[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset, paper_values in ASMCVAR_OVERLAP_VALUES.items():
        supports = {m: np.asarray(metrics[(dataset, m)]["weights"]) != 0 for m in (10, 15, 20)}
        p10_15 = np.count_nonzero(supports[10] & supports[15], axis=0) / np.count_nonzero(supports[10], axis=0)
        p15_20 = np.count_nonzero(supports[15] & supports[20], axis=0) / np.count_nonzero(supports[15], axis=0)
        values = {
            "p10_15_mean": float(p10_15.mean()),
            "p10_15_std": float(p10_15.std(ddof=1)),
            "p15_20_mean": float(p15_20.mean()),
            "p15_20_std": float(p15_20.std(ddof=1)),
        }
        for metric, paper_value in paper_values.items():
            rendered = _format_like(values[metric], paper_value)
            match = rendered == paper_value
            rows.append(
                {
                    "dataset": dataset,
                    "metric": metric,
                    "paper_value": paper_value,
                    "recomputed_value": f"{values[metric]:.12g}",
                    "recomputed_at_paper_precision": rendered,
                    "match_at_paper_precision": match,
                    "paper_location": "Table 2",
                    "original_asmcvar_paper_result_credit": match,
                    "native_efs_evidence": False,
                }
            )
    if len(rows) != 24:
        raise ValueError("expected 24 original ASMCVaR overlap cells")
    return rows


def load_mssrm_native_metrics(
    results_root: Path, datasets: Mapping[str, str] = MSSRM_DATASETS
) -> dict[tuple[str, int], dict[str, Any]]:
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for dataset, source_name in datasets.items():
        for sparsity in (10, 15, 20):
            runs: list[dict[str, Any]] = []
            for repeat in (1, 2):
                path = results_root / f"mssrm_{source_name}_m{sparsity}_run{repeat}.mat"
                payload = loadmat(path)
                wealth = np.asarray(payload["CW"], dtype="<f8").reshape(-1)
                expected_observations = MSSRM_OBSERVATIONS[dataset]
                if wealth.shape != (expected_observations,) or not np.isfinite(wealth).all():
                    raise ValueError(f"invalid mSSRM wealth path: {path}")
                runs.append(
                    {
                        "path": path,
                        "wealth": wealth,
                        "source_sharpe": float(np.asarray(payload["sharpe"]).reshape(-1)[0]),
                        "elapsed_seconds": float(np.asarray(payload["elapsed"]).reshape(-1)[0]),
                        "file_sha256": sha256(path),
                    }
                )
            if not np.array_equal(runs[0]["wealth"], runs[1]["wealth"]):
                raise ValueError(f"mSSRM repeated wealth paths differ: {dataset} m={sparsity}")
            wealth = runs[0]["wealth"]
            wealth_sha = bytes_sha256(wealth.tobytes(order="C"))
            if wealth_sha != MSSRM_CW_SHA256[(dataset, sparsity)]:
                raise ValueError(f"mSSRM wealth hash drifted: {dataset} m={sparsity}")
            returns = wealth[1:] / wealth[:-1] - 1.0
            sharpe = float(returns.mean() / returns.std(ddof=1))
            if not all(np.isclose(run["source_sharpe"], sharpe, rtol=0.0, atol=1e-14) for run in runs):
                raise ValueError(f"mSSRM source/Python Sharpe mismatch: {dataset} m={sparsity}")
            peaks = np.maximum.accumulate(wealth)
            output[(dataset, sparsity)] = {
                "CW": float(wealth[-1]),
                "SR": sharpe,
                "MDD": float(np.max(1.0 - wealth / peaks)),
                "observations": int(wealth.size),
                "cw_sha256": wealth_sha,
                "repeat_paths_equal": True,
                "run_elapsed_seconds": [run["elapsed_seconds"] for run in runs],
                "run_file_sha256": [run["file_sha256"] for run in runs],
            }
    expected = len(datasets) * 3
    if len(output) != expected:
        raise ValueError(f"expected {expected} mSSRM dataset/sparsity executions")
    return output


def apply_mssrm_credit(
    rows: list[dict[str, Any]], metrics: Mapping[tuple[str, int], Mapping[str, Any]]
) -> list[dict[str, Any]]:
    version = str(rows[0]["paper_version"])
    row_by_sparsity = MSSRM_V1_ROW_BY_SPARSITY if version == "v1" else MSSRM_V2_ROW_BY_SPARSITY
    sparsity_by_row = {row_index: sparsity for sparsity, row_index in row_by_sparsity.items()}
    audit_rows: list[dict[str, Any]] = []
    for row in rows:
        row_index = int(row["row_index"])
        if row["paper_table"] != "benchmark" or row_index not in sparsity_by_row:
            continue
        sparsity = sparsity_by_row[row_index]
        dataset, metric = str(row["dataset"]), str(row["metric"])
        native = metrics[(dataset, sparsity)]
        reproduced = float(native[metric])
        rendered = _format_like(reproduced, str(row["paper_value"]))
        match = rendered == row["paper_value"]
        row["cited_baseline_recomputed_value"] = f"{reproduced:.12g}"
        row["cited_baseline_match_at_paper_precision"] = match
        row["paper_result_credit"] = match
        audit_rows.append(
            {
                "paper_version": version,
                "sparsity": sparsity,
                "dataset": dataset,
                "metric": metric,
                "paper_value": row["paper_value"],
                "recomputed_value": f"{reproduced:.12g}",
                "recomputed_at_paper_precision": rendered,
                "match_at_paper_precision": match,
                "source_commit": MSSRM_COMMIT,
                "octave_version": MSSRM_OCTAVE_VERSION,
                "source_function": "run_mSSRM_PGA(60,data,m)",
                "tick2ret_compatibility_shim": "x[1:]/x[:-1]-1",
                "native_source_runs": 2,
                "full_wealth_path_repeat_equal": native["repeat_paths_equal"],
                "cw_sha256": native["cw_sha256"],
                "native_mssrm_source_evidence": True,
                "native_efs_evidence": False,
                "paper_result_credit": match,
            }
        )
    expected_rows = 45 if version == "v1" else 24
    expected_matches = 1 if version == "v1" else 3
    if len(audit_rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} mSSRM comparison cells for {version}")
    if sum(row["paper_result_credit"] for row in audit_rows) != expected_matches:
        raise ValueError(f"mSSRM paper-precision match census drifted for {version}")
    return audit_rows


def validate_mssrm_original_inputs(original_root: Path, asm_cvar: Path) -> dict[str, Any]:
    paper = original_root / "paper.pdf"
    supplement = original_root / "supplement.zip"
    code_root = original_root / "supplement" / "mSSRMcode"
    if sha256(paper) != MSSRM_PAPER_SHA256:
        raise ValueError("pinned mSSRM NeurIPS paper hash mismatch")
    if sha256(supplement) != MSSRM_SUPPLEMENT_SHA256:
        raise ValueError("pinned mSSRM NeurIPS supplement hash mismatch")
    for filename, expected in MSSRM_SUPPLEMENT_CODE_SHA256.items():
        if sha256(code_root / filename) != expected:
            raise ValueError(f"mSSRM NeurIPS supplement code hash mismatch: {filename}")
    data_root = asm_cvar / "Codes_for_Experiments_in_Paper" / "DataSets"
    for dataset, source_name in MSSRM_ORIGINAL_DATASETS.items():
        supplement_data = code_root / f"{dataset}.mat"
        mirror_data = data_root / f"{source_name}.mat"
        if sha256(supplement_data) != sha256(mirror_data):
            raise ValueError(f"mSSRM supplement/mirror matrix mismatch: {dataset}")
    info = subprocess.run(["pdfinfo", str(paper)], check=True, capture_output=True, text=True).stdout
    pages = int(re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE).group(1))
    if pages != 28:
        raise ValueError(f"mSSRM NeurIPS paper page count drifted: {pages}")
    return {
        "paper_sha256": MSSRM_PAPER_SHA256,
        "supplement_sha256": MSSRM_SUPPLEMENT_SHA256,
        "paper_pages": pages,
        "supplement_code_sha256": MSSRM_SUPPLEMENT_CODE_SHA256,
        "supplement_matrices_byte_identical_to_mirror": len(MSSRM_ORIGINAL_DATASETS),
    }


def original_mssrm_paper_conformance(
    metrics: Mapping[tuple[str, int], Mapping[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (dataset, sparsity), paper_values in MSSRM_ORIGINAL_T60_VALUES.items():
        native = metrics[(dataset, sparsity)]
        for metric in ("CW", "SR"):
            paper_value = paper_values[metric]
            reproduced = float(native[metric])
            rendered = _format_like(reproduced, paper_value)
            match = rendered == paper_value
            rows.append(
                {
                    "dataset": dataset,
                    "sparsity": sparsity,
                    "lookback": 60,
                    "metric": metric,
                    "paper_value": paper_value,
                    "recomputed_value": f"{reproduced:.12g}",
                    "recomputed_at_paper_precision": rendered,
                    "match_at_paper_precision": match,
                    "paper_location": "Table 2 and Appendix Table 6" if metric == "CW" else "Table 1 and Appendix Table 6",
                    "native_source_runs": 2,
                    "full_wealth_path_repeat_equal": native["repeat_paths_equal"],
                    "cw_sha256": native["cw_sha256"],
                    "original_mssrm_paper_result_credit": match,
                    "native_efs_evidence": False,
                }
            )
    if len(rows) != 36 or sum(row["original_mssrm_paper_result_credit"] for row in rows) != 36:
        raise ValueError("expected all 36 original mSSRM paper cells to reproduce")
    return rows


def mssrm_supplement_correspondence(
    results_root: Path, metrics: Mapping[tuple[str, int], Mapping[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in MSSRM_ORIGINAL_DATASETS:
        path = results_root / f"neurips_supp_{dataset}_m10.mat"
        payload = loadmat(path)
        wealth = np.asarray(payload["CW"], dtype="<f8").reshape(-1)
        source_sharpe = float(np.asarray(payload["sharpe"]).reshape(-1)[0])
        mirror = metrics[(dataset, 10)]
        wealth_sha = bytes_sha256(wealth.tobytes(order="C"))
        full_path_equal = (
            wealth.shape == (MSSRM_OBSERVATIONS[dataset],) and wealth_sha == mirror["cw_sha256"]
        )
        sharpe_equal = np.isclose(source_sharpe, float(mirror["SR"]), rtol=0.0, atol=1e-14)
        rows.append(
            {
                "dataset": dataset,
                "sparsity": 10,
                "lookback": 60,
                "supplement_function": "PGSAl0_w0run",
                "mirror_function": "run_mSSRM_PGA",
                "supplement_result_file_sha256": sha256(path),
                "cw_sha256": wealth_sha,
                "full_wealth_path_equal_to_mirror": full_path_equal,
                "sharpe_equal_to_mirror": bool(sharpe_equal),
                "native_efs_evidence": False,
            }
        )
    if len(rows) != 6 or not all(
        row["full_wealth_path_equal_to_mirror"] and row["sharpe_equal_to_mirror"] for row in rows
    ):
        raise ValueError("NeurIPS supplement/mirror mSSRM correspondence failed")
    return rows


def _format_like(value: float, paper_value: str) -> str:
    raw = paper_value.rstrip("%")
    decimals = len(raw.split(".", 1)[1]) if "." in raw else 0
    scaled = Decimal(str(value)) * (Decimal(100) if paper_value.endswith("%") else Decimal(1))
    quantum = Decimal(1).scaleb(-decimals)
    rendered = format(scaled.quantize(quantum, rounding=ROUND_HALF_UP), f".{decimals}f")
    return rendered + ("%" if paper_value.endswith("%") else "")


def apply_baseline_credit(
    rows: list[dict[str, Any]], metrics: Mapping[str, Mapping[str, float]]
) -> list[dict[str, Any]]:
    audit_rows: list[dict[str, Any]] = []
    for row in rows:
        if row["paper_table"] != "benchmark" or int(row["row_index"]) != 0:
            continue
        dataset, metric = str(row["dataset"]), str(row["metric"])
        reproduced = float(metrics[dataset][metric])
        rendered = _format_like(reproduced, str(row["paper_value"]))
        match = rendered == row["paper_value"]
        row["cited_baseline_recomputed_value"] = f"{reproduced:.12g}"
        row["cited_baseline_match_at_paper_precision"] = match
        row["paper_result_credit"] = match
        audit_rows.append(
            {
                "paper_version": row["paper_version"],
                "dataset": dataset,
                "metric": metric,
                "paper_value": row["paper_value"],
                "recomputed_value": f"{reproduced:.12g}",
                "recomputed_at_paper_precision": rendered,
                "match_at_paper_precision": match,
                "protocol": "cited_ASMCVaR_623xN_price_relatives_row0_initial_622_equal_weight_transitions",
                "native_efs_evidence": False,
                "paper_result_credit": match,
            }
        )
    return audit_rows


def apply_version_lineage(v1: list[dict[str, Any]], v2: list[dict[str, Any]]) -> list[dict[str, Any]]:
    v1_common = {
        (int(row["row_index"]), str(row["dataset"]), str(row["metric"])): row
        for row in v1
        if row["paper_table"] == "benchmark"
        and int(row["row_index"]) < 20
        and row["dataset"] != "FF100MEOP"
    }
    output: list[dict[str, Any]] = []
    relabeled_rows = {9, 11, 17, 19}
    for row in v2:
        if row["paper_table"] != "benchmark":
            continue
        key = (int(row["row_index"]), str(row["dataset"]), str(row["metric"]))
        earlier = v1_common[key]
        earlier_at_v2_precision = _format_like(float(earlier["paper_value"]), str(row["paper_value"]))
        same = earlier_at_v2_precision == row["paper_value"]
        relabeled = int(row["row_index"]) in relabeled_rows
        status = (
            "v1_scores_to_asset_weights_relabelled_as_v2_RMT_QP_factor_weights_same_rounded_value"
            if relabeled and same
            else "rounded_v1_value_carried_into_v2"
            if same
            else "changed_in_v2"
        )
        row["version_lineage_status"] = status
        output.append(
            {
                "v2_row_index": row["row_index"],
                "dataset": row["dataset"],
                "metric": row["metric"],
                "v1_value": earlier["paper_value"],
                "v1_value_at_v2_precision": earlier_at_v2_precision,
                "v2_value": row["paper_value"],
                "same_at_v2_precision": same,
                "method_semantics_relabelled": relabeled,
                "status": status,
                "native_reproduction_credit": False,
            }
        )
    if len(output) != 240:
        raise ValueError("v1/v2 common benchmark comparison must contain 240 cells")
    if sum(row["same_at_v2_precision"] for row in output) != 240:
        raise ValueError("expected all common v2 benchmark cells to be rounded v1 carryovers")
    if sum(row["method_semantics_relabelled"] for row in output) != 48:
        raise ValueError("expected 48 relabelled Scores-to-Weights/RW cells")
    return output


def extract_v1_prompt(paper_root: Path) -> str:
    text = (paper_root / "source_v1" / "sections" / "appendix.tex").read_text(encoding="utf-8")
    start = text.find("title=\\textcolor{prompttitle}{EFS\\_SYSTEM\\_PROMPT}")
    end_marker = r"\noindent\textbf{Data Safety Guarantee.}"
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise ValueError("v1 prompt appendix could not be recovered")
    prompt = "\n".join(line.rstrip() for line in text[start:end].strip().splitlines()) + "\n"
    required = ("ACTION SPACE", "STRICT REQUIREMENTS", "world-class quantitative researcher")
    if not all(value in prompt for value in required):
        raise ValueError("v1 prompt extraction is incomplete")
    return prompt


def figure_inventory(paper_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for version, directory in (("v1", paper_root / "source_v1" / "figures"), ("v2", paper_root / "source_v2" / "figures")):
        for path in sorted(directory.glob("*.pdf")):
            result_bearing = version == "v2" or path.name in V1_RESULT_FIGURES
            rows.append(
                {
                    "paper_version": version,
                    "filename": path.name,
                    "sha256": sha256(path),
                    "result_bearing": result_bearing,
                    "raw_plot_data_released": False,
                    "native_result_reproduced": False,
                    "status": "vector_or_raster_figure_without_raw_plot_data" if result_bearing else "qualitative_or_architecture_figure",
                }
            )
    if Counter(row["paper_version"] for row in rows) != {"v1": 19, "v2": 3}:
        raise ValueError("EFS figure inventory drifted")
    return rows


def source_inventory(source: Path, commit: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative in run_git(source, "ls-tree", "-r", "--name-only", commit).splitlines():
        path = source / relative
        rows.append(
            {
                "repository": source.name,
                "relative_path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "is_matlab": relative.endswith(".m"),
                "is_dataset": relative.endswith(".mat"),
                "is_native_efs_source": False,
                "is_result_artifact": bool(re.search(r"(?:result|output|checkpoint|log)", relative, re.I)),
            }
        )
    return rows


def method_specification_audit() -> list[dict[str, Any]]:
    entries = [
        ("official EFS source", "missing", "blocking", "No author-linked implementation was found in the paper, author pages, or pinned GitHub searches."),
        ("official code license", "missing", "blocking", "No EFS code package exists to license."),
        ("exact EFS revision", "missing", "blocking", "No executable revision or source tree is identified."),
        ("checkpoint or factor pool", "missing", "blocking", "No generated factor pool, checkpoint, or search state is released."),
        ("raw actions and portfolio weights", "missing", "blocking", "No selected-asset or weight path is released."),
        ("raw returns and equity paths", "missing", "blocking", "Only rendered tables and figures are released."),
        ("exact experiment configuration", "missing", "blocking", "No machine-readable run configuration is released."),
        ("random seeds", "missing", "blocking", "Three searches are mentioned but their seeds are absent."),
        ("per-run outputs", "missing", "blocking", "Main results pool factors across three runs; individual paths are absent."),
        ("LLM model revisions", "missing", "blocking", "GPT-4.1 and DeepSeek-V3 are names, not immutable model snapshots."),
        ("LLM API date and provider", "partial", "major", "v2 names a production endpoint but not the exact invocation dates or immutable backend."),
        ("LLM decoding parameters", "missing", "blocking", "Temperature, top-p, token budget, and retry limit are not fixed."),
        ("prompt template v1", "specified", "none", "v1 embeds system/user prompt templates in the appendix."),
        ("prompt template v2", "conflict", "blocking", "v2 says prompts are in supplementary material, but they are absent from the v2 arXiv PDF/source."),
        ("factor DSL implementation", "missing", "blocking", "Operator names/examples are given, but executable semantics and edge cases are not."),
        ("factor validation tests", "missing", "blocking", "The paper mentions execution validation but releases no validator or tests."),
        ("initial factor library v1", "partial", "major", "v1 lists factor families/definitions but not the exact executable seed library."),
        ("initial factor library v2", "conflict", "major", "v2 alternates between Alpha101/Alpha158 examples and an unreleased concrete seed set."),
        ("data vendor", "missing", "blocking", "No vendor/download endpoint for US50, HSI45, or CSI300 is stated."),
        ("immutable market data snapshot", "missing", "blocking", "No raw market dataset or content hash is released."),
        ("price adjustment and corporate actions", "missing", "blocking", "Adjusted/unadjusted close and delisting treatment are unspecified."),
        ("US50 constituents", "partial", "major", "v1 lists 50 tickers, but v2 does not pin the revised 2019-2025 panel or selection date."),
        ("HSI45 constituents", "partial", "major", "v1 lists tickers but also randomly adds 15 names without a seed; v2 omits the revised panel."),
        ("CSI300 constituents", "missing", "blocking", "No point-in-time membership path or exact 300-name snapshot is released."),
        ("survivorship handling", "missing", "blocking", "Top-cap/current-index universe construction is not point-in-time specified."),
        ("Fama-French benchmark matrices", "partial", "major", "Cited ASMCVaR releases 623xN matrices, but EFS does not hash the exact copies used."),
        ("benchmark start/end dates v1", "conflict", "major", "Main text says 623 records while the appendix says 622; dates are absent in v1."),
        ("benchmark start/end dates v2", "specified", "none", "v2 states July 1971-May 2023 and 623 observations."),
        ("return-to-price conversion", "conflict", "major", "Both versions write P_t as a product of r_t while elsewhere r_t denotes a simple return."),
        ("cumulative wealth v1", "conflict", "major", "v1 defines CW=P_T-P_0 while tables report terminal wealth multiples."),
        ("cumulative wealth v2", "specified", "none", "v2 corrects CW to P_T/P_0."),
        ("Sharpe annualization v1", "partial", "major", "v1 mentions sqrt(252/12) but does not state which tables apply it."),
        ("Sharpe annualization v2", "conflict", "major", "v2 omits annualization from the equation while daily table values appear annualized."),
        ("risk-free rate", "partial", "major", "v2 fixes zero for daily results; v1 does not fix it globally."),
        ("maximum drawdown", "specified", "none", "Both versions provide the standard peak-to-trough definition."),
        ("lookback length", "partial", "major", "v1 fixes T=30 for factors; other optimization lookbacks and v2 revisions are incomplete."),
        ("search frequency", "partial", "major", "Both say typically weekly, not an exact schedule."),
        ("warmup duration", "missing", "blocking", "Algorithm input N_t is not fixed for the reported runs."),
        ("generation count per search", "partial", "major", "v1 ablates M but does not identify the main-run M unambiguously."),
        ("drop and retry thresholds", "missing", "blocking", "Algorithm inputs and retry acceptance thresholds lack reported values."),
        ("v2 filter thresholds", "specified", "none", "v2 supplies IC/ICIR/correlation/floor/cap defaults."),
        ("v2 per-dataset IC screen", "conflict", "major", "v2 claims no per-dataset calibration but uses 0.05 in Asia and 0.005 in the US."),
        ("v2 regularization lambda", "conflict", "major", "Main runs claim fixed lambda=0.05; discussion recommends market-dependent validation tuning."),
        ("factor weighting v1", "specified", "none", "v1 averages factors and separately tests positive score-to-asset weights."),
        ("factor weighting v2", "paper_only", "major", "RMT/QP equations are given but no executable implementation or matrices are released."),
        ("asset weighting", "partial", "major", "Equal weighting is used in main v1 runs; exact v2 asset-weight path after factor RW is incomplete."),
        ("transaction cost model v1", "partial", "major", "Rates are reported, but turnover timing and executable deduction are absent."),
        ("transaction cost model v2", "partial", "major", "Rates and turnover are tabulated, but fills/rebalances and raw paths are absent."),
        ("baseline implementations", "missing", "blocking", "EFS releases no exact baseline wrappers/configs; cited repositories are separate projects."),
        ("uncertainty for main tables", "missing", "blocking", "Pooled-factor main tables have no seed-level uncertainty or tests."),
        ("ablation uncertainty v2", "partial", "major", "v2 discloses that reduced-budget ablations are single runs and qualitative."),
        ("statistical significance", "missing", "blocking", "The only Wilcoxon table is commented out; no active uncertainty test is reported."),
        ("OOS checkpoint protocol", "conflict", "blocking", "v2 says LLM search is disabled, then says pre-2025 factors initialize a run of EFS after the cutoff."),
        ("test-set model selection", "conflict", "blocking", "Rolling performance feedback, IC screens, lambda discussion, and checkpoint comparisons use evaluation-period outcomes without a frozen validation protocol."),
        ("v1 main/no-cost table identity", "conflict", "blocking", "The same EFS m=10 configurations have 18 different values in the main and no-cost tables."),
        ("v1-to-v2 benchmark lineage", "conflict", "blocking", "All 240 common benchmark cells are rounded v1 carryovers despite a materially revised paper."),
        ("Scores-to-Weights to RW relabel", "conflict", "blocking", "Forty-eight v1 asset-score-weighting values are relabelled as v2 RMT/QP factor-weighting results."),
        ("RW overhead claim", "conflict", "major", "The 93.5 ms claim excludes the commented 582.5 s correlation-matrix construction."),
        ("software environment", "missing", "blocking", "No Python/MATLAB/dependency versions or hardware are supplied for EFS."),
        ("full native rerun", "missing", "blocking", "The released paper source is compilable, but the EFS experiment is not executable."),
    ]
    return [
        {"dimension": name, "assessment": status, "severity": severity, "evidence": evidence, "native_efs_verified": False}
        for name, status, severity, evidence in entries
    ]


def qualitative_claim_audit() -> list[dict[str, Any]]:
    return [
        {
            "paper_version": "v1",
            "claim": "EFS achieves state-of-the-art performance across all real-market metrics",
            "observed": "EFS is best in 7/9 dataset-metric cells at m=10; baseline Min-CVaR wins HSI45 MDD and 1/N wins CSI300 MDD",
            "assessment": "overstated",
        },
        {
            "paper_version": "v1",
            "claim": "US50 EFS-GPT CW=39.67 and EFS-DeepSeek CW=32.99",
            "observed": "main table reports 22.905 and 25.101; no-cost table reports 39.746±15.484 and 32.709±6.244",
            "assessment": "internally_conflicting_result_identity",
        },
        {
            "paper_version": "v2",
            "claim": "RW uses fixed defaults without per-dataset calibration",
            "observed": "paper applies IC>=0.05 to HSI45/CSI300 and IC>=0.005 to US50 and later recommends validation tuning of lambda",
            "assessment": "internally_conflicting",
        },
        {
            "paper_version": "v2",
            "claim": "new RMT/QP redundancy-aware weighting benchmark results",
            "observed": "48/48 +RW benchmark values are rounded copies of v1 rows labelled + Scores to Weights for a different weighting mechanism",
            "assessment": "unsupported_result_relabel_without_released_lineage",
        },
        {
            "paper_version": "v2",
            "claim": "RW adds negligible overhead",
            "observed": "93.5 ms excludes a commented 582.5 s correlation-matrix construction, while LLM inference is described only as several minutes",
            "assessment": "boundary_omits_material_preprocessing",
        },
        {
            "paper_version": "both",
            "claim": "faithful public end-to-end reproduction",
            "observed": "zero EFS native table cells, figure paths, factor pools, actions, weights, or returns reproduced",
            "assessment": "not_supported_by_public_evidence",
        },
    ]


def compile_sources(paper_root: Path) -> dict[str, Any]:
    if shutil.which("pdflatex") is None or shutil.which("bibtex") is None:
        raise RuntimeError("pdflatex and bibtex are required for the EFS paper audit")
    results: dict[str, Any] = {}
    for version, source, tex, expected_pages, use_bibtex in (
        ("v1", paper_root / "source_v1", "main.tex", 27, False),
        ("v2", paper_root / "source_v2", "anonymous-submission-latex-2026.tex", 13, True),
    ):
        with tempfile.TemporaryDirectory(prefix=f"efs-{version}-") as temp:
            work = Path(temp) / "source"
            shutil.copytree(source, work)
            commands = [["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex]]
            if use_bibtex:
                commands.append(["bibtex", Path(tex).stem])
            commands.extend([["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex]] * 2)
            exit_codes = []
            for command in commands:
                proc = subprocess.run(command, cwd=work, capture_output=True, text=True)
                exit_codes.append(proc.returncode)
                if proc.returncode:
                    raise RuntimeError(proc.stdout[-3000:] + proc.stderr[-3000:])
            pdf = work / f"{Path(tex).stem}.pdf"
            info = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True).stdout
            pages = int(re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE).group(1))
            if pages != expected_pages:
                raise ValueError(f"{version} compiled to {pages}, expected {expected_pages}")
            results[version] = {
                "exit_codes": exit_codes,
                "pages": pages,
                "source_files": sum(path.is_file() for path in source.rglob("*")),
                "paper_result_credit": False,
            }
    return results


def readme() -> str:
    return """# EFS paper-level replication audit

The original arXiv v1 is the corpus/result authority. The current arXiv v2 is
audited separately because it materially changes the author list, method,
datasets, paper structure, and results.

## Honest outcome

- **EFS itself: 0 native result cells reproduced in either version.** No
  author-linked EFS code, exact configuration, model snapshot, factor pool,
  search trace, action/weight path, raw return, or result output was found.
- **Original v1: 6/773 table-result cells reproduced, all cited-baseline
  evidence.** Five are 1/N MDD cells. Exact mSSRM source execution reproduces
  only 1/45 mSSRM cells at paper precision; its paired CW and MDD disagree, so
  the isolated Sharpe match does not reproduce a complete result row.
- **Current v2: 11/877 cells reproduce at its coarser display precision.** Eight
  are 1/N cells and 3/24 are mSSRM cells. All are cited-baseline evidence, not
  EFS evidence. Paper compilation and parsing receive no experiment credit.

The mSSRM release was run twice for every combination of five EFS matrices
and m={10,15,20}. All 15 full 623-point wealth paths were bit-identical across
repeats, yet 44/45 original-v1 cells disagree with EFS at printed precision.
This is an EFS baseline-protocol mismatch, not a failure to replicate mSSRM:
all 36 CW/SR cells in the original NeurIPS mSSRM paper reproduce, and all six
untouched conference-supplement m=10 wealth paths equal the mirror bit-for-bit.

## Version-lineage warning

All 240 v2 benchmark cells common to v1 are rounded carryovers. More
importantly, all 48 v1 cells labelled “+ Scores to Weights” are relabelled in
v2 as results from the newly introduced RMT/QP “+RW” factor-weighting method,
without released code, matrices, or run lineage. The two labels describe
different mechanisms, so those cells receive no new-method credit.

## Why this is not a faithful replication

The papers provide valuable equations, algorithms, v1 prompt text, several
example factors, and many settings. They do not identify the executable
experiment. Blocking gaps include immutable LLM revisions and decoding,
market-data snapshots and point-in-time universes, the EFS DSL and validator,
seeds, warmup/search schedules, generated factors, baseline wrappers, weights,
returns, and uncertainty. The two versions also conflict on cumulative-wealth
and Sharpe definitions, prompt availability, OOS search, per-dataset tuning,
and repeated result identities.

The paper therefore remains `paper_only_underspecified`. The three local EFS
JKP mappings remain M1 example/motif components; none is a native EFS formula,
portfolio, or paper-result reproduction.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", type=Path, default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_paper_audit"))
    parser.add_argument("--output", type=Path, default=Path("paper_runs/paper_replication_audits/efs"))
    parser.add_argument(
        "--mssrm-results-root",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_octave_runs"),
    )
    parser.add_argument(
        "--mssrm-original-root",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/mssrm_original_paper"),
    )
    args = parser.parse_args()
    paper_root = args.paper_root.resolve()
    output = args.output.resolve()
    mssrm_results_root = args.mssrm_results_root.resolve()
    mssrm_original_root = args.mssrm_original_root.resolve()
    mssrm = paper_root / "mssrm_source"
    asm_cvar = paper_root / "asm_cvar_source"

    validated = validate_inputs(paper_root, mssrm, asm_cvar)
    validated_mssrm_original = validate_mssrm_original_inputs(mssrm_original_root, asm_cvar)
    v1 = parse_v1_results(paper_root)
    v2 = parse_v2_results(paper_root)
    metrics = baseline_metrics(asm_cvar)
    baseline = apply_baseline_credit(v1, metrics) + apply_baseline_credit(v2, metrics)
    mssrm_metrics = load_mssrm_native_metrics(mssrm_results_root)
    mssrm_baseline = apply_mssrm_credit(v1, mssrm_metrics) + apply_mssrm_credit(v2, mssrm_metrics)
    mssrm_original_metrics = load_mssrm_native_metrics(mssrm_results_root, MSSRM_ORIGINAL_DATASETS)
    mssrm_original = original_mssrm_paper_conformance(mssrm_original_metrics)
    mssrm_supplement = mssrm_supplement_correspondence(mssrm_results_root, mssrm_original_metrics)
    lineage = apply_version_lineage(v1, v2)
    figures = figure_inventory(paper_root)
    methods = method_specification_audit()
    claims = qualitative_claim_audit()
    prompt = extract_v1_prompt(paper_root)
    compilations = compile_sources(paper_root)
    source_rows = source_inventory(mssrm, MSSRM_COMMIT) + source_inventory(asm_cvar, ASMCVAR_COMMIT)

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "v1_table_result_conformance.csv", v1)
    write_csv(output / "v2_table_result_conformance.csv", v2)
    write_csv(output / "cited_baseline_reproduction.csv", baseline)
    write_csv(output / "cited_mssrm_native_reproduction.csv", mssrm_baseline)
    write_csv(output / "cited_mssrm_original_paper_reproduction.csv", mssrm_original)
    write_csv(output / "cited_mssrm_neurips_supplement_correspondence.csv", mssrm_supplement)
    write_csv(output / "version_lineage_audit.csv", lineage)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "qualitative_claim_audit.csv", claims)
    write_csv(output / "cited_baseline_source_inventory.csv", source_rows)
    (output / "paper_prompt_v1.tex.txt").write_text(prompt, encoding="utf-8")
    (output / "README.md").write_text(readme(), encoding="utf-8")

    native = {
        "efs_native_execution_attempted": False,
        "reason": "no author-linked EFS implementation, config, factor pool, checkpoint, or result path released",
        "paper_source_compilation": compilations,
        "cited_baseline_formula_executed": True,
        "v1_cited_baseline_cells_with_credit": sum(
            row["paper_result_credit"] for row in baseline + mssrm_baseline
            if row["paper_version"] == "v1"
        ),
        "v2_cited_baseline_cells_with_credit": sum(
            row["paper_result_credit"] for row in baseline + mssrm_baseline
            if row["paper_version"] == "v2"
        ),
        "native_efs_cells_with_credit": 0,
        "matlab_baseline_source_executed": True,
        "cited_mssrm_source_executed_with_octave": True,
        "cited_mssrm_native_runs": 30,
        "cited_mssrm_full_paths_repeat_exact": 15,
        "cited_mssrm_v1_cells_checked": 45,
        "cited_mssrm_v1_cells_matching": 1,
        "cited_mssrm_v2_cells_checked": 24,
        "cited_mssrm_v2_cells_matching": 3,
        "original_mssrm_paper_cells_checked": 36,
        "original_mssrm_paper_cells_matching": 36,
        "original_mssrm_mirror_native_runs": 36,
        "original_mssrm_full_paths_repeat_exact": 18,
        "original_mssrm_neurips_supplement_native_runs": 6,
        "original_mssrm_supplement_paths_equal_mirror": 6,
        "cited_asmcvar_source_executed_with_octave": False,
        "matlab_reason": (
            "mSSRM ran natively under Octave 9.2.0 with an exact tick2ret compatibility shim; "
            "the untouched ASMCVaR entry point has a Windows-only path and its directly invoked "
            "exact core exceeded a 30-minute interactive cap"
        ),
    }
    write_json(output / "native_execution.json", native)
    provenance = {
        "audit_date": AUDIT_DATE,
        "original_paper": {"url": ARXIV_V1_URL, "pdf_sha256": ARXIV_V1_PDF_SHA256, "source_sha256": ARXIV_V1_SOURCE_SHA256, "authors": ["Haochen Luo", "Yuan Zhang", "Chen Liu"], "pages": 27},
        "current_revision": {"url": ARXIV_V2_URL, "pdf_sha256": ARXIV_V2_PDF_SHA256, "source_sha256": ARXIV_V2_SOURCE_SHA256, "updated": "2026-08-07T03:58:06Z", "authors": ["Jiandong Chen", "Haochen Luo", "Yuan Zhang", "Chen Liu", "Qingfu Zhang"], "pages": 13},
        "author_hosted_pdf": {"url": "https://www.cs.cityu.edu.hk/~cliu644/HomePage/doc/EFS/EFS_PDF.pdf", "sha256": ARXIV_V1_PDF_SHA256, "byte_identical_to_v1": True},
        "official_efs_repository_found": False,
        "github_repository_search": {"queries": ["2507.17211", "Evolutionary Factor Search", "EFS sparse portfolio LLM"], "total_repositories": 0, "snapshot_sha256": GITHUB_SEARCH_SHA256},
        "cited_mssrm_release": {"url": MSSRM_URL, "commit": MSSRM_COMMIT, "tree": MSSRM_TREE, "archive_sha256": MSSRM_ARCHIVE_SHA256, "paper_credit": "baseline_source_only"},
        "cited_mssrm_original_paper": {
            "url": MSSRM_PAPER_URL,
            "pdf_sha256": MSSRM_PAPER_SHA256,
            "pages": 28,
            "supplement_url": MSSRM_SUPPLEMENT_URL,
            "supplement_sha256": MSSRM_SUPPLEMENT_SHA256,
            "validation": validated_mssrm_original,
            "reported_cells_checked": 36,
            "reported_cells_reproduced": 36,
            "paper_credit": "original_mssrm_paper_only_not_efs",
        },
        "cited_mssrm_native_execution": {
            "octave_version": MSSRM_OCTAVE_VERSION,
            "lookback": 60,
            "sparsity_values": [10, 15, 20],
            "efs_comparison_runs": 30,
            "efs_comparison_full_paths_repeat_exact": 15,
            "original_paper_mirror_runs": 36,
            "original_paper_full_paths_repeat_exact": 18,
            "neurips_supplement_m10_runs": 6,
            "neurips_supplement_paths_equal_mirror": 6,
            "tick2ret_compatibility_shim": "x[1:]/x[:-1]-1",
            "cw_sha256": {f"{dataset}_m{sparsity}": value for (dataset, sparsity), value in sorted(MSSRM_CW_SHA256.items())},
            "paper_credit": "baseline_source_only",
        },
        "cited_asmcvar_release": {"url": ASMCVAR_URL, "commit": ASMCVAR_COMMIT, "tree": ASMCVAR_TREE, "archive_sha256": ASMCVAR_ARCHIVE_SHA256, "data_sha256": ASMCVAR_DATA_SHA256, "paper_credit": "baseline_source_only"},
        "validation": validated,
    }
    write_json(output / "source_provenance.json", provenance)

    tracked = [
        "README.md", "v1_table_result_conformance.csv", "v2_table_result_conformance.csv",
        "cited_baseline_reproduction.csv", "cited_mssrm_native_reproduction.csv",
        "cited_mssrm_original_paper_reproduction.csv",
        "cited_mssrm_neurips_supplement_correspondence.csv",
        "version_lineage_audit.csv", "figure_inventory.csv",
        "method_specification_audit.csv", "qualitative_claim_audit.csv",
        "cited_baseline_source_inventory.csv", "paper_prompt_v1.tex.txt",
        "native_execution.json", "source_provenance.json",
    ]
    manifest = {
        "paper": "EFS: Evolutionary Factor Searching for Sparse Portfolio Optimization Using Large Language Models",
        "audit_date": AUDIT_DATE,
        "paper_evidence_route": "paper_only_underspecified",
        "overall_status": "partial_6_of_773_cited_baseline_cells_reproduced_zero_efs_native_results_v2_audited_separately",
        "full_paper_reproduced": False,
        "official_efs_source_released": False,
        "original_v1_table_result_cells": len(v1),
        "original_v1_table_cells_reproduced": sum(row["paper_result_credit"] for row in v1),
        "current_v2_table_result_cells": len(v2),
        "current_v2_table_cells_reproduced": sum(row["paper_result_credit"] for row in v2),
        "native_efs_result_cells_reproduced": 0,
        "cited_mssrm_v1_cells_checked": 45,
        "cited_mssrm_v1_cells_reproduced": sum(
            row["paper_result_credit"] for row in mssrm_baseline if row["paper_version"] == "v1"
        ),
        "cited_mssrm_v2_cells_checked": 24,
        "cited_mssrm_v2_cells_reproduced": sum(
            row["paper_result_credit"] for row in mssrm_baseline if row["paper_version"] == "v2"
        ),
        "original_mssrm_paper_cells_checked": len(mssrm_original),
        "original_mssrm_paper_cells_reproduced": sum(
            row["original_mssrm_paper_result_credit"] for row in mssrm_original
        ),
        "original_mssrm_neurips_supplement_paths_checked": len(mssrm_supplement),
        "original_mssrm_neurips_supplement_paths_equal_mirror": sum(
            row["full_wealth_path_equal_to_mirror"] for row in mssrm_supplement
        ),
        "v1_v2_common_benchmark_cells": len(lineage),
        "v1_v2_common_benchmark_cells_same_at_v2_precision": sum(row["same_at_v2_precision"] for row in lineage),
        "scores_to_weights_cells_relabelled_as_rw": sum(row["method_semantics_relabelled"] for row in lineage),
        "method_specification_dimensions": len(methods),
        "method_assessment_counts": dict(sorted(Counter(row["assessment"] for row in methods).items())),
        "method_severity_counts": dict(sorted(Counter(row["severity"] for row in methods).items())),
        "source_figure_files": len(figures),
        "result_bearing_source_figure_files": sum(row["result_bearing"] for row in figures),
        "v1_prompt_recovered": True,
        "v2_prompts_released": False,
        "paper_source_compilation": compilations,
        "output_sha256": {name: sha256(output / name) for name in tracked},
    }
    write_json(output / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
