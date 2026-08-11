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
PAPER_SHA256 = "6585377002a3b049a6bfadef3152a74adfe12d68ff5c48cccb8c76de4fd1b540"
PAPER_URL = "https://aclanthology.org/2025.findings-emnlp.1005.pdf"
SOURCE_URL = "https://github.com/kouzhizhuo/Automate-Strategy-Finding-with-LLM-in-Quant-investment"
PAPER_TABLE_2: Tuple[Tuple[str, float, float], ...] = (
    ("Momentum", 0.0092, 0.0208),
    ("Mean Reversion", 0.0135, 0.0187),
    ("Volatility", 0.0177, 0.0258),
    ("Fundamental", 0.0118, 0.0192),
    ("Growth", 0.0146, 0.0217),
)
PAPER_TABLE_3_SELECTED_INDICES = (1, 3, 9, 10, 13, 15, 17, 20, 21, 27, 30, 33)
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


def build_audit(source_root: Path, paper_path: Path, output_dir: Path) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official paper PDF hash does not match the pinned primary source")

    seed_path = source_root / "data/Seed Alpha.xlsx"
    source_main = (source_root / "main.py").read_text(encoding="utf-8")
    source_agent = (source_root / "AutoGPT/main.py").read_text(encoding="utf-8")
    source_dnn = (source_root / "train_dnn.m").read_text(encoding="utf-8")
    seeds = seed_alpha_rows(seed_path)
    table_2 = table_2_audit(seeds)
    inventory = result_workbook_inventory(source_root)
    if len(inventory) != 7:
        raise RuntimeError(f"Expected seven pinned factor-analysis workbooks, found {len(inventory)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "table_2_conformance.csv", table_2, list(table_2[0]))
    write_csv(
        output_dir / "factor_workbook_inventory.csv",
        inventory,
        list(inventory[0]),
    )
    table_4 = table_4_unverifiable_rows()
    write_csv(output_dir / "table_4_conformance.csv", table_4, list(table_4[0]))
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
    covers_paper_window = any(bool(row["covers_paper_test_window"]) for row in inventory)
    integrated_schema = any(bool(row["has_integrated_strategy_schema"]) for row in inventory)
    manifest = {
        "audit": "Automate Strategy Finding paper claims versus pinned public artifacts",
        "overall_status": "not_reproduced_missing_integrated_native_output",
        "paper_url": PAPER_URL,
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "source_seed_workbook": str(seed_path.relative_to(source_root)),
        "source_seed_workbook_sha256": sha256(seed_path),
        "paper_table_2_cells_matched": table_2_matches,
        "paper_table_2_cells_total": len(table_2),
        "paper_table_4_cells_verified": 0,
        "paper_table_4_cells_unverifiable": len(table_4),
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
        "paper_internal_numeric_inconsistencies_recorded": len(paper_inconsistencies),
        "interpretation": (
            "The public artifacts support a partial 2022Q4 factor-analysis and prompt-selection "
            "component audit. They do not contain the 2023 integrated portfolio path required "
            "to verify the paper's 53.173% Table 4 result, and the released DNN width differs "
            "from the paper."
        ),
    }
    report = f"""# Automate Strategy Finding paper-level conformance audit

Overall verdict: **not reproduced**. The pinned public repository supports a partial
factor-analysis and prompt-selection component, not the integrated portfolio result.

## Primary sources

- Official paper: {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.

## What the public artifacts establish

- The 37-row seed workbook exposes factor names, formulas, signed ICs, and IRs.
- Seven individual-factor analysis workbooks contain IC summaries, five quantile
  cumulative-return paths, and turnover over 2022-09-30 through 2022-12-30.
- The public prompt files and logs show a GPT-4o Assistant-based factor-comparison
  workflow. This is component evidence, not the paper's final strategy.
- Recomputing Table 2 with the inferable mean-absolute-IC rule matches
  {table_2_matches}/{len(table_2)} displayed cells at four-decimal precision.

## What is missing or inconsistent

- No shipped workbook contains the integrated Jan 2023--Jan 2024 portfolio path,
  Table 4 schema, or the reported 53.173% final return; all {len(table_4)} Table 4
  metric cells are therefore unverifiable, not zero-filled or counted as failures.
- Table 3 reports 12 selected alphas, while the public AutoGPT candidate directory
  contains seven individual-factor workbooks and no weighted 12-alpha portfolio.
- The paper describes a 10-node DNN; `train_dnn.m` sets one hidden node and its
  required `result/profit.csv` and `result/alpha/` inputs are absent.
- The paper's top-k/drop-n portfolio rule (k=13, n=5) is not implemented in the
  released Python or MATLAB files.
- The paper itself reports SSE50 return as -13.22% in Table 4 but -11.73% in prose,
  and full-model ablation Sharpe as 1.94 in Table 7 but 1.73 in prose.
- The factor runner requires unbundled RQData access. The public agent file also
  embeds a credential literal; this audit never prints, validates, or uses it.

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
