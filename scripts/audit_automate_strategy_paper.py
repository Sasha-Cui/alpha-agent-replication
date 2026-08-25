#!/usr/bin/env python3
"""Audit Automate Strategy Finding's paper claims against its pinned source artifacts.

The public repository contains factor-analysis inputs, prompt logs, and seven
dated individual-factor workbooks. This audit distinguishes those artifacts
from the integrated portfolio results reported in the paper.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from xml.etree import ElementTree as ET


SOURCE_COMMIT = "8b50203faf50d0b561cf5ffee4d63dcdc4551884"
CURRENT_MAIN_HEAD = "ebcb5ed44a71664316c99b021026358a44aef38d"
NEW_PROJECT_HEAD = "f28e274c8be373a7e3c1a325846f07d67b079250"
PUBLIC_HISTORY_COMMITS = (
    "6145cd5cf12158ee9f29c02467f616b947958ac3",
    "496ad96f1fc525dcc43109401c11bcc79928bcd9",
    "6303684b315fc3bedfc9b87db0e38e3102033d50",
    "3e95d2141b4b53aad5be2becf83eb2f56d60ab32",
    NEW_PROJECT_HEAD,
    SOURCE_COMMIT,
    CURRENT_MAIN_HEAD,
)
PUBLIC_HISTORY_PATHS_SHA256 = "9a670889ddde51ed3e506e3163d4d25c18eac76641469d178df6d21ecbe0cac4"
DISCOVERY_SHA256 = {
    "branches.json": "3654717f907163f1879d2a58d0fb8279681a98c16669a771bdf852bdbdae9e04",
    "tags.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "releases.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}
PAPER_SHA256 = "6585377002a3b049a6bfadef3152a74adfe12d68ff5c48cccb8c76de4fd1b540"
PAPER_URL = "https://aclanthology.org/2025.findings-emnlp.1005.pdf"
SOURCE_URL = "https://github.com/kouzhizhuo/Automate-Strategy-Finding-with-LLM-in-Quant-investment"
PUBLIC_FORK_CENSUS_CHECKED_AT = "2026-08-14"
PUBLIC_FORK_BRANCH_REF_SEQUENCE_SHA256 = (
    "61c027bcfab368f1641f2d0f8e5b1901d5c6c89548464d6ef91922403cef8e2f"
)
PUBLIC_FORK_BRANCH_REFS: Tuple[Tuple[str, str, str], ...] = (
    (
        "ALADIN99I/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "6303684b315fc3bedfc9b87db0e38e3102033d50",
    ),
    (
        "aptperson/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "6303684b315fc3bedfc9b87db0e38e3102033d50",
    ),
    (
        "aptperson/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "New-project",
        NEW_PROJECT_HEAD,
    ),
    (
        "BrainLyh/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "chayao2015/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "colinmgeorge/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "DatAvalon/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "496ad96f1fc525dcc43109401c11bcc79928bcd9",
    ),
    (
        "dkeraaaa/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "HUH99/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "jingmouren/kouzhizhuo-Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "496ad96f1fc525dcc43109401c11bcc79928bcd9",
    ),
    (
        "JohnsRun/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "Lilneo786/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "maxclchen/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "6303684b315fc3bedfc9b87db0e38e3102033d50",
    ),
    (
        "mengmajun/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "496ad96f1fc525dcc43109401c11bcc79928bcd9",
    ),
    (
        "omarovic01/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "496ad96f1fc525dcc43109401c11bcc79928bcd9",
    ),
    (
        "SBY7219/Automate-Strategy-with-LLM-in-Quant",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "ShawnWangXin/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "shenghansen/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "stophobia/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "496ad96f1fc525dcc43109401c11bcc79928bcd9",
    ),
    (
        "WangGuolin/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "6303684b315fc3bedfc9b87db0e38e3102033d50",
    ),
    (
        "wangyuaqi/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "496ad96f1fc525dcc43109401c11bcc79928bcd9",
    ),
    (
        "Warden7/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "wrchow/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "xieerduoyishengzhidi/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        SOURCE_COMMIT,
    ),
    (
        "yjj5855/Automate-Strategy-Finding-with-LLM-in-Quant-investment",
        "main",
        "496ad96f1fc525dcc43109401c11bcc79928bcd9",
    ),
)
PAPER_TABLE_2: Tuple[Tuple[str, float, float], ...] = (
    ("Momentum", 0.0092, 0.0208),
    ("Mean Reversion", 0.0135, 0.0187),
    ("Volatility", 0.0177, 0.0258),
    ("Fundamental", 0.0118, 0.0192),
    ("Growth", 0.0146, 0.0217),
)
PAPER_TABLE_3_SELECTED_INDICES = (1, 3, 9, 10, 13, 15, 17, 20, 21, 27, 30, 33)
PAPER_TABLE_3: Tuple[Tuple[int, int, float, float], ...] = (
    (1, 1, -0.1459, 0.0209),
    (2, 3, -1.0265, -0.0225),
    (3, 9, -0.1978, 0.0193),
    (4, 10, 0.0556, -0.0186),
    (5, 13, -0.9450, -0.0186),
    (6, 15, -0.4053, -0.0185),
    (7, 17, -0.3199, 0.0194),
    (8, 20, 3.6186, 0.0278),
    (9, 21, -0.1830, 0.0236),
    (10, 27, -3.2145, -0.0194),
    (11, 30, -0.0058, 0.0187),
    (12, 33, -1.8351, -0.0215),
)
PAPER_TABLE_3_COMBINED_IC = -0.0587
PAPER_TABLE_4: Tuple[Tuple[str, Tuple[float, ...]], ...] = (
    ("Ours", (53.173, 0.287, 0.762, 0.208, 1.052)),
    ("XGBoost", (9.532, 0.038, 1.019, 0.067, 0.103)),
    ("LightGBM", (7.125, 0.030, 0.993, 0.053, 0.066)),
    ("MLP", (3.110, 0.013, 0.960, 0.023, 0.043)),
    ("PPO_filter", (2.865, 0.013, 0.886, 0.024, 0.017)),
    ("FinCon", (22.474, 0.077, 1.196, 0.126, 0.232)),
    ("SEP", (17.891, 0.060, 1.217, 0.103, 0.157)),
    ("SSE 50", (-13.220, -0.063, 0.859, -0.111, -0.043)),
)
TABLE_4_METRICS = ("final_return_pct", "sharpe", "volatility_pct", "sortino", "calmar")
DISPLAY_TOLERANCE = 0.00005 + 1e-12


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    ).stdout


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def public_fork_ref_inventory(source_root: Path) -> List[Dict[str, Any]]:
    """Validate the dated public-fork census against the pinned official history."""
    refs = sorted(PUBLIC_FORK_BRANCH_REFS, key=lambda row: (row[0].lower(), row[1].lower(), row[2]))
    canonical = "".join(f"{repository}\t{branch}\t{head}\n" for repository, branch, head in refs)
    if sha256_bytes(canonical.encode("utf-8")) != PUBLIC_FORK_BRANCH_REF_SEQUENCE_SHA256:
        raise RuntimeError("Automate Strategy public-fork census sequence changed")
    if len({repository for repository, _branch, _head in refs}) != 24 or len(refs) != 25:
        raise RuntimeError("Automate Strategy public-fork census cardinality changed")

    rows: List[Dict[str, Any]] = []
    for repository, branch, head in refs:
        git(source_root, "cat-file", "-e", f"{head}^{{commit}}")
        reachable = head in PUBLIC_HISTORY_COMMITS
        if not reachable:
            raise RuntimeError(
                f"Automate Strategy fork head escaped the pinned official history: {repository}@{branch}"
            )
        rows.append(
            {
                "repository": repository,
                "branch": branch,
                "head_sha": head,
                "reachable_from_pinned_official_history": reachable,
                "additional_commits": 0,
                "additional_result_or_log_paths": 0,
                "paper_result_credit": False,
            }
        )
    return rows


def excel_column_index(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference)
    if not match:
        raise ValueError(f"Invalid XLSX cell reference: {reference}")
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def _shared_strings(archive: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return ["".join(node.text or "" for node in item.findall(".//x:t", ns)) for item in root]


def _sheet_paths(archive: zipfile.ZipFile) -> Dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    main_ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in relationships.findall(f"{{{package_ns}}}Relationship")
    }
    result = {}
    for sheet in workbook.findall(".//x:sheet", main_ns):
        target = targets[sheet.attrib[f"{{{rel_ns}}}id"]]
        path = target.lstrip("/") if target.startswith("/xl/") else f"xl/{target.lstrip('/')}"
        result[sheet.attrib["name"]] = path
    return result


def _cell_value(cell: ET.Element, strings: Sequence[str], ns: Mapping[str, str]) -> Any:
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//x:t", ns))
    value = cell.find("x:v", ns)
    if value is None or value.text is None:
        return None
    if kind == "s":
        return strings[int(value.text)]
    if kind in {"str", "e"}:
        return value.text
    if kind == "b":
        return value.text == "1"
    number = float(value.text)
    return int(number) if number.is_integer() else number


def read_xlsx_matrix(path: Path, sheet_name: str) -> List[List[Any]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        strings = _shared_strings(archive)
        paths = _sheet_paths(archive)
        if sheet_name not in paths:
            raise KeyError(f"Worksheet not found in {path.name}: {sheet_name}")
        root = ET.fromstring(archive.read(paths[sheet_name]))
        matrix = []
        for row in root.findall(".//x:sheetData/x:row", ns):
            indexed = {
                excel_column_index(cell.attrib["r"]): _cell_value(cell, strings, ns)
                for cell in row.findall("x:c", ns)
            }
            matrix.append([indexed.get(index) for index in range(max(indexed, default=-1) + 1)])
    return matrix


def sheet_names(path: Path) -> List[str]:
    with zipfile.ZipFile(path) as archive:
        return list(_sheet_paths(archive))


def excel_date(value: Any) -> date:
    return date(1899, 12, 30) + timedelta(days=float(value))


def seed_alpha_rows(path: Path) -> List[Dict[str, Any]]:
    rows = []
    category = ""
    for values in read_xlsx_matrix(path, "Seed Alpha")[1:]:
        padded = values + [None] * (6 - len(values))
        if not isinstance(padded[0], (int, float)):
            continue
        if padded[1]:
            category = str(padded[1]).lstrip("•").strip()
        rows.append(
            {
                "index": int(padded[0]),
                "category": category,
                "alpha": str(padded[2]),
                "formula": str(padded[3]),
                "ic": float(padded[4]),
                "ir": float(padded[5]),
            }
        )
    return rows


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def table_2_audit(seed_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    selected = set(PAPER_TABLE_3_SELECTED_INDICES)
    output = []
    for category, expected_mean, expected_selected in PAPER_TABLE_2:
        category_rows = [row for row in seed_rows if row["category"] == category]
        selected_rows = [row for row in category_rows if row["index"] in selected]
        calculations = (
            ("mean_ic_of_saf", expected_mean, mean(abs(float(row["ic"])) for row in category_rows)),
            (
                "mean_ic_of_selected_saf",
                expected_selected,
                mean(abs(float(row["ic"])) for row in selected_rows),
            ),
        )
        for metric, expected, actual in calculations:
            error = abs(actual - expected)
            output.append(
                {
                    "category": category,
                    "metric": metric,
                    "paper_value": expected,
                    "source_absolute_ic_aggregation": actual,
                    "absolute_error": error,
                    "rounding_tolerance": DISPLAY_TOLERANCE,
                    "status": "exact_rounding_match" if error <= DISPLAY_TOLERANCE else "mismatch",
                    "aggregation_note": (
                        "Inferred mean absolute IC: the paper labels the measure Mean IC but "
                        "reports positive category values while source rows include signed ICs."
                    ),
                }
            )
    return output


def table_3_audit(seed_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_index = {int(row["index"]): row for row in seed_rows}
    output: List[Dict[str, Any]] = []
    for paper_row, source_index, paper_weight, paper_ic in PAPER_TABLE_3:
        source = by_index[source_index]
        error = abs(float(source["ic"]) - paper_ic)
        output.append(
            {
                "paper_row": paper_row,
                "source_seed_index": source_index,
                "source_alpha": source["alpha"],
                "source_formula": source["formula"],
                "metric": "ic",
                "paper_value": paper_ic,
                "source_value": source["ic"],
                "absolute_error": error,
                "rounding_tolerance": DISPLAY_TOLERANCE,
                "status": (
                    "author_workbook_exact_rounding_match"
                    if error <= DISPLAY_TOLERANCE
                    else "author_workbook_mismatch"
                ),
                "author_source_corroborated": error <= DISPLAY_TOLERANCE,
                "native_integrated_portfolio_reproduced": False,
                "evidence": "data/Seed Alpha.xlsx signed IC",
            }
        )
        output.append(
            {
                "paper_row": paper_row,
                "source_seed_index": source_index,
                "source_alpha": source["alpha"],
                "source_formula": source["formula"],
                "metric": "weight",
                "paper_value": paper_weight,
                "source_value": "",
                "absolute_error": "",
                "rounding_tolerance": DISPLAY_TOLERANCE,
                "status": "unverifiable_missing_trained_dnn_output",
                "author_source_corroborated": False,
                "native_integrated_portfolio_reproduced": False,
                "evidence": "no released selected-alpha weight artifact",
            }
        )
    output.append(
        {
            "paper_row": "combined",
            "source_seed_index": "",
            "source_alpha": "Weighted Combination",
            "source_formula": "",
            "metric": "ic",
            "paper_value": PAPER_TABLE_3_COMBINED_IC,
            "source_value": "",
            "absolute_error": "",
            "rounding_tolerance": DISPLAY_TOLERANCE,
            "status": "unverifiable_missing_trained_dnn_output",
            "author_source_corroborated": False,
            "native_integrated_portfolio_reproduced": False,
            "evidence": "no released 12-alpha combined prediction or return path",
        }
    )
    matched = [
        row
        for row in output
        if row["status"] == "author_workbook_exact_rounding_match"
    ]
    if len(output) != 25 or len(matched) != 12:
        raise RuntimeError("Automate Strategy Table 3 conformance census changed")
    return output


def result_workbook_inventory(source_root: Path) -> List[Dict[str, Any]]:
    inventory = []
    result_root = source_root / "AutoGPT/data/alpha-result"
    for path in sorted(result_root.glob("*.xlsx"), key=lambda item: int(item.stem)):
        names = sheet_names(path)
        matrix = read_xlsx_matrix(path, "各期分组累计收益率序列")
        dated = [row for row in matrix[1:] if len(row) > 1 and row[1] is not None]
        dates = [excel_date(row[1]) for row in dated]
        tags = sorted({str(row[0]) for row in dated if row[0]})
        headers = {str(value) for row in matrix[:1] for value in row if value is not None}
        inventory.append(
            {
                "file": str(path.relative_to(source_root)),
                "sha256": sha256(path),
                "role": "individual_factor_analysis_not_integrated_paper_portfolio",
                "sheet_count": len(names),
                "sheets": ";".join(names),
                "sample_start": min(dates).isoformat(),
                "sample_end": max(dates).isoformat(),
                "unique_dates": len(set(dates)),
                "dated_rows": len(dated),
                "quantile_tags": ";".join(tags),
                "has_integrated_strategy_schema": bool(
                    {"Strategy", "Final Return (%)", "Sharpe Ratio"}.intersection(headers)
                ),
                "covers_paper_test_window": max(dates) >= date(2023, 1, 1),
            }
        )
    return inventory


def table_4_unverifiable_rows() -> List[Dict[str, Any]]:
    rows = []
    for strategy, values in PAPER_TABLE_4:
        for metric, expected in zip(TABLE_4_METRICS, values):
            rows.append(
                {
                    "strategy": strategy,
                    "metric": metric,
                    "paper_value": expected,
                    "source_value": "",
                    "status": "unverifiable_missing_integrated_native_output",
                }
            )
    return rows


def _contains_usable_credential_literal(text: str) -> bool:
    """Detect a likely usable literal without ever returning or recording its value."""
    for match in re.finditer(r"api_key\s*=\s*[\"']([^\"']+)[\"']", text):
        value = match.group(1).strip()
        if len(value) >= 20 and set(value) != {"*"} and "redact" not in value.lower():
            return True
    return False


def released_source_history_audit(
    source_root: Path,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Inspect every public revision and the later New-project branch fail-closed."""
    if git(source_root, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise RuntimeError("Automate Strategy Finding source checkout is shallow")
    commits = tuple(git(source_root, "rev-list", "--reverse", "--all").splitlines())
    if commits != PUBLIC_HISTORY_COMMITS:
        raise RuntimeError(f"Public source history changed: {commits}")
    unreachable = git(
        source_root,
        "fsck",
        "--full",
        "--no-reflogs",
        "--unreachable",
        "--no-progress",
    ).strip()
    if unreachable:
        raise RuntimeError(f"Public source has unreviewed unreachable objects: {unreachable}")

    discovery_root = source_root / "release-discovery"
    for filename, expected in DISCOVERY_SHA256.items():
        path = discovery_root / filename
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"Pinned GitHub discovery response changed: {filename}")
    branches = json.loads((discovery_root / "branches.json").read_text(encoding="utf-8"))
    branch_heads = sorted((row["name"], row["commit"]["sha"]) for row in branches)
    expected_heads = sorted((("main", CURRENT_MAIN_HEAD), ("New-project", NEW_PROJECT_HEAD)))
    if branch_heads != expected_heads:
        raise RuntimeError(f"Public branch heads changed: {branch_heads}")
    if json.loads((discovery_root / "tags.json").read_text(encoding="utf-8")):
        raise RuntimeError("Public repository now exposes an unreviewed tag")
    if json.loads((discovery_root / "releases.json").read_text(encoding="utf-8")):
        raise RuntimeError("Public repository now exposes an unreviewed release")

    all_paths = sorted(
        set(
            git(
                source_root,
                "-c",
                "core.quotePath=false",
                "log",
                "--all",
                "--name-only",
                "--pretty=format:",
            ).splitlines()
        )
        - {""}
    )
    paths_digest = sha256_bytes(("\n".join(all_paths) + "\n").encode("utf-8"))
    if len(all_paths) != 39 or paths_digest != PUBLIC_HISTORY_PATHS_SHA256:
        raise RuntimeError(f"Historical path surface changed: {len(all_paths)} {paths_digest}")

    evidence_roles = {
        PUBLIC_HISTORY_COMMITS[0]: "repository_initialization_only",
        PUBLIC_HISTORY_COMMITS[1]: "factor_prompt_log_and_workbook_component_release",
        PUBLIC_HISTORY_COMMITS[2]: "placeholder_path_added_no_experiment_evidence",
        PUBLIC_HISTORY_COMMITS[3]: "later_generic_grail_component_attempt_added",
        PUBLIC_HISTORY_COMMITS[4]: "generic_grail_documentation_and_dependencies_updated",
        SOURCE_COMMIT: "placeholder_path_renamed_no_experiment_evidence",
        CURRENT_MAIN_HEAD: "credential_redaction_only_no_experiment_evidence",
    }
    history_rows: List[Dict[str, Any]] = []
    grail_names = {
        "__init__.py",
        "main.py",
        "multi_agent_system.py",
        "seed_alphas_factory.py",
        "weight_optimization.py",
    }
    result_pattern = re.compile(r"53[.]173|53[.]17|top-k|drop-n|2023-01|202301|2024-01|202401", re.I)
    for commit in commits:
        authored_at, subject = git(
            source_root, "show", "-s", "--format=%aI%x09%s", commit
        ).rstrip().split("\t", 1)
        paths = git(
            source_root, "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", commit
        ).splitlines()
        text_paths = [
            path
            for path in paths
            if Path(path).suffix.lower() in {".py", ".m", ".md", ".txt"}
        ]
        integrated_literal_paths = []
        for path in text_paths:
            text = git_bytes(source_root, "show", f"{commit}:{path}").decode(
                "utf-8", errors="replace"
            )
            if result_pattern.search(text):
                integrated_literal_paths.append(path)
        agent_text = (
            git_bytes(source_root, "show", f"{commit}:AutoGPT/main.py").decode(
                "utf-8", errors="replace"
            )
            if "AutoGPT/main.py" in paths
            else ""
        )
        memberships = [
            name
            for name, head in branch_heads
            if subprocess.run(
                ["git", "-C", str(source_root), "merge-base", "--is-ancestor", commit, head],
                check=False,
            ).returncode
            == 0
        ]
        history_rows.append(
            {
                "commit": commit,
                "authored_at": authored_at,
                "subject": subject,
                "public_branch_membership": ";".join(sorted(memberships)),
                "tracked_paths": len(paths),
                "python_source_paths": sum(path.endswith(".py") for path in paths),
                "xlsx_paths": sum(path.endswith(".xlsx") for path in paths),
                "grail_component_paths": sum(path in grail_names for path in paths),
                "integrated_result_or_portfolio_rule_literal_paths": len(integrated_literal_paths),
                "usable_hardcoded_credential_literal_present": _contains_usable_credential_literal(
                    agent_text
                ),
                "evidence_role": evidence_roles[commit],
                "integrated_native_portfolio_output_present": False,
                "published_result_regenerated": False,
                "paper_result_credit": False,
            }
        )
    if any(row["integrated_result_or_portfolio_rule_literal_paths"] for row in history_rows):
        raise RuntimeError("An unreviewed integrated-result or portfolio-rule literal appeared")
    if not history_rows[-2]["usable_hardcoded_credential_literal_present"]:
        raise RuntimeError("Pinned historical credential-presence boundary changed")
    if history_rows[-1]["usable_hardcoded_credential_literal_present"]:
        raise RuntimeError("Current main unexpectedly still contains a usable credential literal")

    component_specs = (
        (
            "main.py",
            "pipeline_orchestrator",
            "imports root-level siblings relatively, so the documented root checkout is not an importable grail package; defaults are 100-64-10 rather than paper |A|-10-1",
        ),
        (
            "seed_alphas_factory.py",
            "document_classifier_placeholder",
            "uses GPT-2 sequence classification rather than paper GPT-4o and reads outputs.hidden_states without requesting hidden states; it does not generate executable alpha formulas",
        ),
        (
            "multi_agent_system.py",
            "generic_confidence_scaler",
            "creates conservative/moderate/aggressive copies that rescale a caller-provided confidence; it does not implement paper CSA/RPA market-conditioned IC and risk evaluation",
        ),
        (
            "weight_optimization.py",
            "generic_two_linear_layer_trainer",
            "accepts caller-supplied tensors, defaults to 64 hidden and 10 outputs, and never constructs paper alpha histories, future returns, composite stock scores, or portfolio",
        ),
        (
            "README.md",
            "generic_grail_usage_claim",
            "documents an absent grail package and caller placeholders; no frozen input, command, seed, checkpoint, or expected native output is supplied",
        ),
        (
            "requirements.txt",
            "unpinned_dependency_ranges",
            "declares broad minimum versions only; no lockfile or environment pin establishes an executable historical runtime",
        ),
    )
    component_rows = []
    for path, role, finding in component_specs:
        value = git_bytes(source_root, "show", f"{NEW_PROJECT_HEAD}:{path}")
        if path.endswith(".py"):
            compile(value.decode("utf-8"), path, "exec")
        component_rows.append(
            {
                "branch": "New-project",
                "commit": NEW_PROJECT_HEAD,
                "path": path,
                "sha256": sha256_bytes(value),
                "component_role": role,
                "static_syntax_valid": path.endswith(".py"),
                "connected_to_released_workbooks": False,
                "paper_configuration_match": False,
                "native_run_shipped": False,
                "published_result_regenerated": False,
                "paper_result_credit": False,
                "finding": finding,
            }
        )

    summary = {
        "public_commits_reviewed": len(commits),
        "public_branches_reviewed": len(branch_heads),
        "public_branch_heads": dict(branch_heads),
        "public_tags": 0,
        "public_releases": 0,
        "unreachable_git_objects": 0,
        "historical_unique_paths_reviewed": len(all_paths),
        "history_complete_for_pinned_public_refs": True,
        "current_main_diff_from_pinned_commit": "credential_redaction_only",
        "current_main_contains_usable_hardcoded_credential_literal": False,
        "pinned_commit_historically_contains_usable_hardcoded_credential_literal": True,
        "new_project_branch_components_reviewed": len(component_rows),
        "new_project_python_syntax_valid": True,
        "new_project_documented_import_layout_exists": False,
        "new_project_uses_paper_gpt4o_seed_alpha_generation": False,
        "new_project_implements_paper_csa_and_rpa": False,
        "new_project_default_mlp_architecture_matches_paper": False,
        "new_project_connected_to_released_workbooks": False,
        "new_project_native_run_or_result_shipped": False,
        "new_project_paper_result_credit": False,
    }
    return history_rows, component_rows, summary


def historical_branch_runtime_observation() -> Dict[str, Any]:
    """Return the bounded native probe recorded on Bouchet for the branch payload."""
    return {
        "observed_at": "2026-08-13",
        "source_commit": NEW_PROJECT_HEAD,
        "environment": {
            "host": "Bouchet CPU node",
            "python": "3.12.3",
            "pytorch": "2.7.1",
            "transformers": "4.55.2",
            "modules": [
                "PyTorch/2.7.1-foss-2024a-CUDA-12.8.0",
                "Transformers/4.55.2-gfbf-2024a",
            ],
        },
        "probe_scope": (
            "Author files reconstructed unchanged as one importable Python package; no paper "
            "data, prompt, model API, or claimed result was supplied or fabricated."
        ),
        "static_python_files_parsed": 5,
        "reconstructed_package_import": "passed",
        "multi_agent_synthetic_probe": {
            "status": "passed",
            "input": {
                "confidence": 0.8,
                "agent": "moderate",
                "confidence_threshold": 0.6,
                "max_exposure": 0.5,
            },
            "observed_mean_confidence": 0.8,
            "observed_mean_exposure": 0.5,
            "paper_result_credit": False,
        },
        "optimizer_short_batch_probe": {
            "status": "failed",
            "input_shape": [1, 2],
            "batch_size": 32,
            "exception_type": "ZeroDivisionError",
            "cause": (
                "integer batch count is zero and the epoch returns total_loss / num_batches"
            ),
            "paper_result_credit": False,
        },
        "default_constructor_probe": {
            "status": "environment_crash_before_model_construction",
            "signal": "SIGILL",
            "boundary": (
                "Bouchet's centrally supplied tokenizers binary crashed while loading the "
                "downloaded GPT-2 tokenizer"
            ),
            "author_code_failure_inferred": False,
            "paper_result_credit": False,
        },
        "interpretation": (
            "The branch is importable when reconstructed under a valid package name, and its "
            "simple confidence-scaling agent can execute. This does not connect it to the paper "
            "experiment. The optimizer has a directly observed short-batch defect; the default "
            "constructor was not adjudicated because the environment crashed in a dependency "
            "before model construction."
        ),
    }


def build_audit(source_root: Path, paper_path: Path, output_dir: Path) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official paper PDF hash does not match the pinned primary source")
    history, branch_components, history_summary = released_source_history_audit(source_root)
    fork_refs = public_fork_ref_inventory(source_root)

    seed_path = source_root / "data/Seed Alpha.xlsx"
    source_main = (source_root / "main.py").read_text(encoding="utf-8")
    source_agent = (source_root / "AutoGPT/main.py").read_text(encoding="utf-8")
    source_dnn = (source_root / "train_dnn.m").read_text(encoding="utf-8")
    seeds = seed_alpha_rows(seed_path)
    table_2 = table_2_audit(seeds)
    table_3 = table_3_audit(seeds)
    inventory = result_workbook_inventory(source_root)
    if len(inventory) != 7:
        raise RuntimeError(f"Expected seven pinned factor-analysis workbooks, found {len(inventory)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "table_2_conformance.csv", table_2, list(table_2[0]))
    write_csv(output_dir / "table_3_conformance.csv", table_3, list(table_3[0]))
    write_csv(
        output_dir / "factor_workbook_inventory.csv",
        inventory,
        list(inventory[0]),
    )
    table_4 = table_4_unverifiable_rows()
    write_csv(output_dir / "table_4_conformance.csv", table_4, list(table_4[0]))
    write_csv(
        output_dir / "released_source_history_inventory.csv",
        history,
        list(history[0]),
    )
    write_csv(
        output_dir / "historical_branch_component_inventory.csv",
        branch_components,
        list(branch_components[0]),
    )
    write_csv(
        output_dir / "public_fork_ref_inventory.csv",
        fork_refs,
        list(fork_refs[0]),
    )
    runtime_observation = historical_branch_runtime_observation()
    (output_dir / "historical_branch_runtime_observation.json").write_text(
        json.dumps(runtime_observation, indent=2) + "\n", encoding="utf-8"
    )
    paper_inconsistencies = (
        {
            "claim": "SSE50 benchmark final return",
            "paper_table_value": -13.22,
            "paper_prose_value": -11.73,
            "status": "paper_internal_mismatch",
            "location": "Table 4 versus Section 4.4 prose",
        },
        {
            "claim": "Full-model ablation Sharpe ratio",
            "paper_table_value": 1.94,
            "paper_prose_value": 1.73,
            "status": "paper_internal_mismatch",
            "location": "Table 7 versus Section 4.6 prose",
        },
    )
    write_csv(
        output_dir / "paper_internal_inconsistencies.csv",
        paper_inconsistencies,
        list(paper_inconsistencies[0]),
    )

    hidden_match = re.search(r"hiddenLayerSize\s*=\s*(\d+)", source_dnn)
    source_hidden_nodes = int(hidden_match.group(1)) if hidden_match else None
    table_2_matches = sum(row["status"] == "exact_rounding_match" for row in table_2)
    table_3_corroborated = sum(bool(row["author_source_corroborated"]) for row in table_3)
    table_3_unverifiable = sum(row["status"].startswith("unverifiable") for row in table_3)
    covers_paper_window = any(bool(row["covers_paper_test_window"]) for row in inventory)
    integrated_schema = any(bool(row["has_integrated_strategy_schema"]) for row in inventory)
    manifest = {
        "audit": "Automate Strategy Finding paper claims versus pinned public artifacts",
        "overall_status": "not_reproduced_missing_integrated_native_output",
        "paper_url": PAPER_URL,
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "current_public_main_head": CURRENT_MAIN_HEAD,
        "new_project_branch_head": NEW_PROJECT_HEAD,
        "released_source_history": history_summary,
        "public_fork_census_checked_at": PUBLIC_FORK_CENSUS_CHECKED_AT,
        "public_forks_total": 24,
        "public_fork_branch_refs_total": len(fork_refs),
        "public_fork_branch_ref_sequence_sha256": PUBLIC_FORK_BRANCH_REF_SEQUENCE_SHA256,
        "public_fork_branch_refs_reachable_from_official_history": sum(
            bool(row["reachable_from_pinned_official_history"]) for row in fork_refs
        ),
        "public_divergent_fork_heads_total": 0,
        "public_fork_additional_result_or_log_paths_total": 0,
        "public_fork_paper_result_credit_paths_total": 0,
        "source_seed_workbook": str(seed_path.relative_to(source_root)),
        "source_seed_workbook_sha256": sha256(seed_path),
        "paper_table_2_cells_matched": table_2_matches,
        "paper_table_2_cells_total": len(table_2),
        "paper_table_4_cells_verified": 0,
        "paper_table_4_cells_unverifiable": len(table_4),
        "paper_table_3_cells_total": len(table_3),
        "paper_table_3_cells_author_source_corroborated": table_3_corroborated,
        "paper_table_3_cells_unverifiable": table_3_unverifiable,
        "factor_analysis_workbooks": len(inventory),
        "factor_analysis_window_start": min(row["sample_start"] for row in inventory),
        "factor_analysis_window_end": max(row["sample_end"] for row in inventory),
        "factor_analysis_workbooks_cover_paper_2023_window": covers_paper_window,
        "factor_analysis_workbooks_have_integrated_strategy_schema": integrated_schema,
        "paper_integrated_test_window": "2023-01 through 2024-01 (paper label)",
        "paper_final_return_pct": 53.173,
        "native_integrated_portfolio_return_shipped": False,
        "paper_table_3_selected_alpha_count": len(PAPER_TABLE_3_SELECTED_INDICES),
        "source_autogpt_candidate_workbook_count": len(inventory),
        "paper_dnn_hidden_nodes": 10,
        "source_dnn_hidden_nodes": source_hidden_nodes,
        "dnn_hidden_width_matches": source_hidden_nodes == 10,
        "source_dnn_training_inputs_shipped": (source_root / "result/profit.csv").is_file()
        and (source_root / "result/alpha").is_dir(),
        "paper_portfolio_top_k": 13,
        "paper_portfolio_drop_n": 5,
        "source_portfolio_builder_present": "top-k" in source_main.lower()
        or "drop-n" in source_main.lower(),
        "source_factor_analysis_period_literal": (
            "20220930" if 'd1 = "20220930"' in source_main else "unresolved",
            "20221231" if 'd2 = "20221231"' in source_main else "unresolved",
        ),
        "source_requires_unbundled_rqdata_access": "rqdatac.init()" in source_main,
        "source_agent_model_literal": "gpt-4o" if 'model="gpt-4o"' in source_agent else "unresolved",
        "source_agent_contains_hardcoded_credential": bool(
            re.search(r"api_key\s*=\s*[\"'][^\"']+[\"']", source_agent)
        ),
        "source_agent_historical_credential_literal_present_at_pinned_commit": (
            _contains_usable_credential_literal(source_agent)
        ),
        "source_agent_current_main_credential_redacted": not history_summary[
            "current_main_contains_usable_hardcoded_credential_literal"
        ],
        "new_project_branch_reviewed": True,
        "new_project_branch_component_attempt_is_paper_faithful": False,
        "new_project_branch_bounded_runtime_probe": {
            "package_import": runtime_observation["reconstructed_package_import"],
            "multi_agent_synthetic_probe": runtime_observation["multi_agent_synthetic_probe"][
                "status"
            ],
            "optimizer_short_batch_probe": runtime_observation[
                "optimizer_short_batch_probe"
            ]["status"],
            "default_constructor_probe": runtime_observation["default_constructor_probe"][
                "status"
            ],
        },
        "new_project_branch_paper_result_credit": False,
        "paper_internal_numeric_inconsistencies_recorded": len(paper_inconsistencies),
        "interpretation": (
            "The public artifacts support a partial 2022Q4 factor-analysis and prompt-selection "
            "component audit. They do not contain the 2023 integrated portfolio path required "
            "to verify the paper's 53.173% Table 4 result. Complete public-history review also "
            "finds a later generic Grail branch, but its components are disconnected from the "
            "released data and materially differ from the paper's GPT-4o, CSA/RPA, and |A|-10-1 "
            "MLP design. A dated census of 24 public forks and 25 branch refs finds that every "
            "fork head is already an exact commit in the audited official history, so no fork "
            "adds paper-result lineage."
        ),
    }
    report = f"""# Automate Strategy Finding paper-level conformance audit

Overall verdict: **not reproduced**. The pinned public repository supports a partial
factor-analysis and prompt-selection component, not the integrated portfolio result.

## Primary sources

- Official paper: {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.
- A bounded GitHub census on {PUBLIC_FORK_CENSUS_CHECKED_AT} covers all 24 accessible
  forks and {len(fork_refs)} fork branch refs. Every head is an exact commit in the
  already-audited official history, so the forks contribute no additional commit,
  result/log path, or paper-result lineage.

## What the public artifacts establish

- The 37-row seed workbook exposes factor names, formulas, signed ICs, and IRs.
- Seven individual-factor analysis workbooks contain IC summaries, five quantile
  cumulative-return paths, and turnover over 2022-09-30 through 2022-12-30.
- The public prompt files and logs show a GPT-4o Assistant-based factor-comparison
  workflow. This is component evidence, not the paper's final strategy.
- Recomputing Table 2 with the inferable mean-absolute-IC rule matches
  {table_2_matches}/{len(table_2)} displayed cells at four-decimal precision.
- The seed workbook corroborates all {table_3_corroborated}/12 signed IC cells
  printed for Table 3's selected alphas at four-decimal precision. This is
  author-source component evidence, not an integrated portfolio replay.
- The complete public Git surface was reviewed: {history_summary['public_commits_reviewed']}
  commits on {history_summary['public_branches_reviewed']} branches, 39 unique historical paths,
  zero tags/releases, and zero unreachable objects.
- All {len(fork_refs)} branch refs across the 24 public forks resolve to those same
  official-history commits. See `public_fork_ref_inventory.csv`.

## What is missing or inconsistent

- No shipped workbook contains the integrated Jan 2023--Jan 2024 portfolio path,
  Table 4 schema, or the reported 53.173% final return; all {len(table_4)} Table 4
  metric cells are therefore unverifiable, not zero-filled or counted as failures.
- Table 3's 12 learned weights and combined IC are absent. The public AutoGPT
  candidate directory contains only seven individual-factor workbooks and no
  weighted 12-alpha portfolio, prediction, or return path.
- The paper describes a 10-node DNN; `train_dnn.m` sets one hidden node and its
  required `result/profit.csv` and `result/alpha/` inputs are absent.
- The paper's top-k/drop-n portfolio rule (k=13, n=5) is not implemented in the
  released Python or MATLAB files.
- The later `New-project` branch adds a generic "Grail" scaffold, but it does not
  recover the missing experiment. It defaults to GPT-2 rather than GPT-4o; its
  three risk-profile copies merely rescale caller-provided confidence rather than
  implementing the paper's market-conditioned CSA/RPA; and its default MLP is
  100-64-10 rather than |A|-10-1. It accepts caller-supplied tensors, is not wired
  to any released workbook, and ships no command, frozen input, checkpoint, native
  output, portfolio path, or reported metric. Static syntax validity is not result credit.
- A bounded Bouchet probe imported the reconstructed package and exercised the simple
  confidence scaler. A one-row optimizer call failed with division by zero because
  it creates zero batches. Default GPT-2 construction could not be adjudicated: the
  centrally supplied tokenizer dependency terminated with SIGILL before model
  construction, so that environment crash is explicitly not attributed to author code.
- The paper itself reports SSE50 return as -13.22% in Table 4 but -11.73% in prose,
  and full-model ablation Sharpe as 1.94 in Table 7 but 1.73 in prose.
- The factor runner requires unbundled RQData access. The public agent file also
  contained a usable credential literal at the pinned historical commit. Current
  `main` redacts it, and that redaction is the only later main-branch change. This
  audit never prints, validates, or uses the historical value.

Run `scripts/audit_automate_strategy_paper.py` to regenerate this package. Use
`--strict` when a CI failure is desired until a native integrated return path exists.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "AUTOMATE_STRATEGY_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/automate_strategy_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "AUTOMATE_STRATEGY_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/automate_strategy_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/automate_strategy_finding",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(), args.paper_pdf.resolve(), args.output_dir.resolve()
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and manifest["overall_status"] != "reproduced")


if __name__ == "__main__":
    sys.exit(main())
