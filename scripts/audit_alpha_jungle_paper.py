#!/usr/bin/env python3
"""Fail-closed paper/source audit for Alpha-Jungle (AAAI 2026).

The nine-page AAAI-26 proceedings paper is the publication authority.  The
original arXiv v1 and current v3 sources are audited separately because v3
adds experiments and changes Annualized Return (AR) to Annualized Excess
Return (AER).  The paper releases detailed prompt templates and six example
formulas, but no author-linked implementation, data snapshot, factor pool,
search trace, model output, or result artifact.

An unaffiliated community repository is pinned and inspected as negative
evidence only.  It is neither promoted to author source nor allowed to earn
paper-result credit.
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


AUDIT_DATE = "2026-08-11"
ARXIV_URL = "https://arxiv.org/abs/2505.11122"
ARXIV_V1_URL = "https://arxiv.org/abs/2505.11122v1"
ARXIV_V3_URL = "https://arxiv.org/abs/2505.11122v3"
AAAI_ARTICLE_URL = "https://ojs.aaai.org/index.php/AAAI/article/view/37069"
AAAI_PDF_URL = "https://ojs.aaai.org/index.php/AAAI/article/download/37069/41031"
DOI = "10.1609/aaai.v40i2.37069"

ARXIV_V1_PDF_SHA256 = "3cec26455b7f37c04b4dddeee3f947cdde7a49ea904bfd4862221642a0686c5f"
ARXIV_V1_SOURCE_SHA256 = "3301816a94ef153b474c15a748c1b7ba3d23259154454da4497fd387c97f6170"
ARXIV_V3_PDF_SHA256 = "1707743f661de3c3957ef02f7b7e6ee8f926377569185162d40b71115aa18a2b"
ARXIV_V3_SOURCE_SHA256 = "8667c5c9a50bdaf23066af442e4b8fc5b8b98ba250af19110f997590616cd140"
AAAI_FINAL_PDF_SHA256 = "439e6749988619d49e9e156ab040ebc5c6b48371ae8dce8e6db831bbbd3ca12a"
ARXIV_ABS_SHA256 = "6f91650fbf2bb2203ca208e86abe2d5c9237b6851a64b266b9e592b0718679da"
GITHUB_SEARCH_SHA256 = {
    "github_search_arxiv.json": "41164c6e8978b1a555819d2a0d11876461ecaff814b53551c9a3e64e9fa5c760",
    "github_search_title.json": "48fbd3f2123d07614408bf775e2e68db5c68f13afab9d0c06df7e9598b808a2c",
    "github_search_method.json": "d76e5287b988802435517e3308f19ec45705797f69ad301dddaae8c55c41db63",
}
GITHUB_SEARCH_COUNTS = {
    "github_search_arxiv.json": 53,
    "github_search_title.json": 4,
    "github_search_method.json": 7,
}

COMMUNITY_URL = "https://github.com/dtbtc/mcts-llm-alpha"
COMMUNITY_COMMIT = "cab5d91f3cb834c3810811142407047bd2fef7ff"
COMMUNITY_TREE = "4cc43b217684bc3d502afeb27ab109ff577dbd3a"
COMMUNITY_ARCHIVE_SHA256 = "d46ec3b63a8e23743ffecf0c712521cb08dab43bd0ba56d54cfc166f2de6cda5"

V1_TABLE_SPECS = (
    ("ablation", "sections/Experiment.tex", "tab:ablation_study", 8),
    ("additional_comparison", "sections/Appendix.tex", "tab:additional_experimental_results", 6),
    ("leakage", "sections/Appendix.tex", "tab:model-comparison", 4),
    ("llm_sensitivity", "sections/Appendix.tex", "tab:llm_sensitivity", 8),
    ("csi300_lightgbm", "sections/Appendix.tex", "tab:experimental_result_csi300_lgb", 12),
    ("csi300_mlp", "sections/Appendix.tex", "tab:experimental_result_csi300_mlp", 12),
    ("csi1000_lightgbm", "sections/Appendix.tex", "tab:experimental_result_csi1000_lgb", 12),
    ("csi1000_mlp", "sections/Appendix.tex", "tab:experimental_result_csi1000_mlp", 12),
)
V3_TABLE_SPECS = (
    ("ablation", "sections/Experiment.tex", "tab:ablation_study", 8),
    ("additional_comparison", "sections/Appendix.tex", "tab:additional_experimental_results", 8),
    ("sp500", "sections/Appendix.tex", "tab:experimental_result_sp500", 6),
    ("leakage", "sections/Appendix.tex", "tab:model-comparison", 4),
    ("llm_sensitivity", "sections/Appendix.tex", "tab:llm_sensitivity", 8),
    ("cost", "sections/Appendix.tex", "tab:cost_comparison", 6),
    ("equal_cost", "sections/Appendix.tex", "tab:equal_cost_comparison", 12),
    ("csi300_lightgbm", "sections/Appendix.tex", "tab:experimental_result_csi300_lgb", 12),
    ("csi300_mlp", "sections/Appendix.tex", "tab:experimental_result_csi300_mlp", 12),
    ("csi1000_lightgbm", "sections/Appendix.tex", "tab:experimental_result_csi1000_lgb", 12),
    ("csi1000_mlp", "sections/Appendix.tex", "tab:experimental_result_csi1000_mlp", 12),
)
V1_EXPECTED_TABLE_COUNTS = {
    "ablation": 64,
    "additional_comparison": 72,
    "leakage": 20,
    "llm_sensitivity": 32,
    "csi300_lightgbm": 192,
    "csi300_mlp": 192,
    "csi1000_lightgbm": 192,
    "csi1000_mlp": 192,
}
V3_EXPECTED_TABLE_COUNTS = {
    "ablation": 64,
    "additional_comparison": 160,
    "sp500": 96,
    "leakage": 20,
    "llm_sensitivity": 48,
    "cost": 60,
    "equal_cost": 96,
    "csi300_lightgbm": 192,
    "csi300_mlp": 192,
    "csi1000_lightgbm": 192,
    "csi1000_mlp": 192,
}
FULL_TABLES = (
    "csi300_lightgbm",
    "csi300_mlp",
    "csi1000_lightgbm",
    "csi1000_mlp",
)

PAPER_FORMULAS = (
    (1, "Zscore(Ma(close-vwap,20),30)", "close, vwap", None),
    (2, "Std(Pct(vwap,20),25)*Sum(volume,40)/volume", "vwap, volume", None),
    (3, "Corr(close,volume,50)*Zscore(Ma(close-vwap,30),40)", "close, vwap, volume", None),
    (4, "Diff(Ma(volume,20),3)/Ma(volume,60)", "volume", "alpha_jungle_volume_ma_diff"),
    (
        5,
        "Corr(Pct(close,10),Pct(volume,10),10)*Corr(Pct(close,30),Pct(volume,30),30)*Skew(volume,20)",
        "close, volume",
        "alpha_jungle_multiscale_price_volume",
    ),
    (
        6,
        "Ma(Corr(volume,close,20)*Skew(high-low,20),10)",
        "close, high, low, volume",
        "alpha_jungle_range_volume_interaction",
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(source: Path, *args: str, binary: bool = False) -> Any:
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


def _remove_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def _table_for_label(text: str, label: str) -> str:
    marker = rf"\label{{{label}}}"
    location = text.find(marker)
    if location < 0:
        raise ValueError(f"missing table label: {label}")
    starts = list(re.finditer(r"\\begin\{(table\*?|wraptable)\}", text[:location]))
    if not starts:
        raise ValueError(f"missing table start for {label}")
    match = starts[-1]
    environment = match.group(1)
    end = text.find(rf"\end{{{environment}}}", location)
    if end < 0:
        raise ValueError(f"missing table end for {label}")
    return text[match.start():end]


def _row_fragments(table: str) -> list[list[str]]:
    rows: list[list[str]] = []
    buffer = ""
    for line in _remove_comments(table).splitlines():
        buffer += " " + line.strip()
        while r"\\" in buffer:
            row, buffer = buffer.split(r"\\", 1)
            rows.append([cell.strip() for cell in re.split(r"(?<!\\)&", row)])
    return rows


def _clean_cell(cell: str) -> str:
    value = cell.strip()
    previous = None
    while value != previous:
        previous = value
        value = re.sub(
            r"\\(?:textbf|emph|underline|mathbf|mathrm|textit)\{([^{}]*)\}",
            r"\1",
            value,
        )
    value = value.replace("$", "").replace("{", "").replace("}", "")
    value = value.replace(r"\,", "").replace(",", "").strip()
    return value


NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")


def _number(cell: str) -> str | None:
    value = _clean_cell(cell)
    return value if NUMBER_RE.fullmatch(value) else None


def _row_label(cells: Sequence[str]) -> str:
    text = " | ".join(cells)
    text = re.sub(r"\\(?:multirow|multicolumn)\{[^{}]*\}(?:\{[^{}]*\})?", " ", text)
    text = re.sub(r"\\(?:textbf|emph|makecell)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+", " ", text)
    text = text.replace("{", " ").replace("}", " ").replace("$", " ")
    return " ".join(text.split())


def _metrics(version: str, table: str, width: int) -> tuple[str, ...]:
    if table == "ablation":
        return (
            "LightGBM_IC", "LightGBM_RankIC", f"LightGBM_{'AR' if version == 'v1' else 'AER'}", "LightGBM_IR",
            "MLP_IC", "MLP_RankIC", f"MLP_{'AR' if version == 'v1' else 'AER'}", "MLP_IR",
        )
    if table == "additional_comparison" and version == "v1":
        return ("LR_IC", "LR_RankIC", "LightGBM_IC", "LightGBM_RankIC", "MLP_IC", "MLP_RankIC")
    if table == "additional_comparison":
        return ("LightGBM_IC", "LightGBM_RankIC", "LightGBM_AER", "LightGBM_IR", "MLP_IC", "MLP_RankIC", "MLP_AER", "MLP_IR")
    if table == "sp500":
        return ("alpha10_IC", "alpha10_RankIC", "alpha50_IC", "alpha50_RankIC", "alpha100_IC", "alpha100_RankIC")
    if table == "leakage":
        return ("IC", "RankIC", "IR", "RankIR")
    if table == "llm_sensitivity":
        return ("LightGBM_IC", "LightGBM_RankIC", "LightGBM_AR", "LightGBM_IR", "MLP_IC", "MLP_RankIC", "MLP_AR", "MLP_IR")
    if table == "cost":
        return ("time_hours", "input_tokens", "output_tokens", "server_cost_usd", "api_cost_usd", "total_cost_usd")
    if width == 12:
        return tuple(f"alpha{size}_{metric}" for size in (10, 50, 100) for metric in ("IC", "RankIC", "AR", "IR"))
    raise ValueError(f"metric mapping missing: {version}/{table}/{width}")


def _extract_table(version: str, table_id: str, block: str, width: int) -> list[dict[str, Any]]:
    metrics = _metrics(version, table_id, width)
    records: list[dict[str, Any]] = []
    row_index = 0
    for cells in _row_fragments(block):
        parsed = [(index, value) for index, cell in enumerate(cells) if (value := _number(cell)) is not None]
        if len(parsed) < width:
            continue
        selected = parsed[-width:]
        # Numeric descriptors such as the prediction horizon precede the
        # rightmost fixed-width result block and are intentionally excluded.
        start_index = selected[0][0]
        label = _row_label(cells[:start_index])
        for position, (_, paper_value) in enumerate(selected):
            metric = metrics[position]
            records.append(
                {
                    "paper_version": version,
                    "paper_table": table_id,
                    "display_cell_id": f"{version}/{table_id}/row{row_index}/{metric}",
                    "row_index": row_index,
                    "row_label": label,
                    "result_position": position,
                    "metric": metric,
                    "paper_value": paper_value,
                    "native_reproduced_value": "",
                    "native_alpha_jungle_result_credit": False,
                    "paper_result_credit": False,
                    "status": "not_reproduced_no_author_source_exact_inputs_or_native_outputs",
                }
            )
        row_index += 1
    return records


def parse_results(paper_root: Path, version: str) -> list[dict[str, Any]]:
    specs = V1_TABLE_SPECS if version == "v1" else V3_TABLE_SPECS
    source = paper_root / f"source_{version}"
    rows: list[dict[str, Any]] = []
    for table_id, filename, label, width in specs:
        text = (source / filename).read_text(encoding="utf-8")
        rows.extend(_extract_table(version, table_id, _table_for_label(text, label), width))
    counts = Counter(str(row["paper_table"]) for row in rows)
    expected = Counter(V1_EXPECTED_TABLE_COUNTS if version == "v1" else V3_EXPECTED_TABLE_COUNTS)
    if counts != expected:
        raise ValueError(f"{version} result census drifted: {counts}; expected {expected}")
    return rows


def published_final_rows(paper_root: Path, v3_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext is required for the Alpha-Jungle audit")
    proc = subprocess.run(
        ["pdftotext", "-layout", str(paper_root / "aaai_final.pdf"), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = proc.stdout
    ablation = [dict(row) for row in v3_rows if row["paper_table"] == "ablation"]
    for row_index in range(8):
        values = [
            str(row["paper_value"])
            for row in ablation
            if int(row["row_index"]) == row_index
        ]
        if len(values) != 8:
            raise ValueError(f"AAAI Table 1 row {row_index} source width drifted")
        pattern = r"\s+".join(re.escape(value) for value in values)
        if re.search(pattern, text) is None:
            raise ValueError(f"AAAI Table 1 row {row_index} not found in official PDF text")
    for row in ablation:
        row["paper_version"] = "AAAI-26_final"
        row["paper_table"] = "Table_1_ablation"
        row["display_cell_id"] = str(row["display_cell_id"]).replace("v3/ablation", "AAAI-26_final/Table_1_ablation")
        row["status"] = "official_published_cell_not_natively_reproduced"
    return ablation


def _table_rows(rows: Sequence[Mapping[str, Any]], table: str) -> list[Mapping[str, Any]]:
    return [row for row in rows if row["paper_table"] == table]


def version_lineage(v1: Sequence[Mapping[str, Any]], v3: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []

    def add(earlier: Mapping[str, Any], current: Mapping[str, Any], mapping: str) -> None:
        same = earlier["paper_value"] == current["paper_value"]
        table = str(current["paper_table"])
        position = int(current["result_position"])
        relabel = table == "ablation" and position in {2, 6}
        current_ar_conflict = (
            (table in FULL_TABLES or table in {"llm_sensitivity", "equal_cost"})
            and str(current["metric"]).endswith("_AR")
        )
        if relabel:
            status = "v1_AR_relabelled_as_v3_AER_same_numeric_value" if same else "v1_AR_relabelled_as_v3_AER_changed_value"
        else:
            status = "unchanged_between_v1_v3" if same else "changed_between_v1_v3"
        output.append(
            {
                "lineage_id": f"{mapping}/{earlier['display_cell_id']}->{current['display_cell_id']}",
                "paper_table": table,
                "mapping": mapping,
                "v1_row_index": earlier["row_index"],
                "v1_metric": earlier["metric"],
                "v1_value": earlier["paper_value"],
                "v3_row_index": current["row_index"],
                "v3_metric": current["metric"],
                "v3_value": current["paper_value"],
                "same_numeric_display_value": same,
                "AR_to_AER_semantic_relabel": relabel,
                "current_v3_AR_header_conflicts_with_AER_definition": current_ar_conflict,
                "status": status,
                "native_reproduction_credit": False,
            }
        )

    for table in ("ablation", "leakage", *FULL_TABLES):
        earlier, current = _table_rows(v1, table), _table_rows(v3, table)
        if len(earlier) != len(current):
            raise ValueError(f"direct lineage width changed for {table}")
        for left, right in zip(earlier, current):
            add(left, right, "same_table_cell_ordinal")

    earlier_sensitivity = _table_rows(v1, "llm_sensitivity")
    current_sensitivity = _table_rows(v3, "llm_sensitivity")
    for v1_row, v3_row in zip((0, 1, 2, 3), (0, 1, 2, 4)):
        for position in range(8):
            left = next(row for row in earlier_sensitivity if row["row_index"] == v1_row and row["result_position"] == position)
            right = next(row for row in current_sensitivity if row["row_index"] == v3_row and row["result_position"] == position)
            add(left, right, "same_LLM_semantic_row")

    earlier_additional = _table_rows(v1, "additional_comparison")
    current_additional = _table_rows(v3, "additional_comparison")
    v3_rows = (0, 1, 4, 5, 6, 9, 10, 11, 14, 15, 16, 19)
    position_map = ((2, 0), (3, 1), (4, 4), (5, 5))
    for v1_row, v3_row in zip(range(12), v3_rows):
        for v1_position, v3_position in position_map:
            left = next(row for row in earlier_additional if row["row_index"] == v1_row and row["result_position"] == v1_position)
            right = next(row for row in current_additional if row["row_index"] == v3_row and row["result_position"] == v3_position)
            add(left, right, "same_alpha_set_market_horizon_model_metric")

    if len(output) != 932:
        raise ValueError(f"expected 932 common v1/v3 cells, got {len(output)}")
    if sum(bool(row["same_numeric_display_value"]) for row in output) != 925:
        raise ValueError("expected 925 unchanged common cells")
    if sum(bool(row["AR_to_AER_semantic_relabel"]) for row in output) != 16:
        raise ValueError("expected sixteen AR-to-AER relabelled ablation cells")
    return output


def cost_arithmetic(v3: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = _table_rows(v3, "cost")
    by_row: dict[int, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_row.setdefault(int(row["row_index"]), []).append(row)
    rates = {
        0: (Decimal("3.076"), Decimal("0"), Decimal("0")),
        1: (Decimal("3.076"), Decimal("0"), Decimal("0")),
        2: (Decimal("3.076"), Decimal("0"), Decimal("0")),
        3: (Decimal("3.076"), Decimal("0"), Decimal("0")),
        4: (Decimal("2.07"), Decimal("2.00"), Decimal("8.00")),
        5: (Decimal("2.07"), Decimal("2.00"), Decimal("8.00")),
        6: (Decimal("2.07"), Decimal("2.00"), Decimal("8.00")),
        7: (Decimal("2.07"), Decimal("2.00"), Decimal("8.00")),
        8: (Decimal("2.07"), Decimal("0.075"), Decimal("0.30")),
        9: (Decimal("2.07"), Decimal("0.071"), Decimal("1.14")),
    }
    quantum = Decimal("0.001")
    output: list[dict[str, Any]] = []
    for row_index in range(10):
        ordered = sorted(by_row[row_index], key=lambda row: int(row["result_position"]))
        values = [Decimal(str(row["paper_value"])) for row in ordered]
        hourly, input_rate, output_rate = rates[row_index]
        server_raw = values[0] * hourly
        api_raw = (values[1] * input_rate + values[2] * output_rate) / Decimal("1000000")
        server = server_raw.quantize(quantum, rounding=ROUND_HALF_UP)
        api = api_raw.quantize(quantum, rounding=ROUND_HALF_UP)
        # The table rounds total cost only after summing the unrounded server
        # and API components (visible for FAMA: 27.069 rather than 27.070).
        total = (server_raw + api_raw).quantize(quantum, rounding=ROUND_HALF_UP)
        for position, recomputed in zip((3, 4, 5), (server, api, total)):
            paper = values[position]
            output.append(
                {
                    "row_index": row_index,
                    "metric": ordered[position]["metric"],
                    "paper_value": f"{paper:.3f}",
                    "recomputed_from_same_table_inputs": f"{recomputed:.3f}",
                    "match_at_paper_precision": paper == recomputed,
                    "evidence_type": "paper_internal_arithmetic_not_independent_experiment",
                    "paper_result_credit": False,
                }
            )
    if len(output) != 30 or not all(row["match_at_paper_precision"] for row in output):
        mismatches = [row for row in output if not row["match_at_paper_precision"]]
        raise ValueError(f"v3 cost arithmetic no longer reconciles: {mismatches}")
    return output


def formula_component_conformance(paper_root: Path, repo_root: Path) -> list[dict[str, Any]]:
    v1 = (paper_root / "source_v1/sections/Appendix.tex").read_text(encoding="utf-8")
    v3 = (paper_root / "source_v3/sections/Appendix.tex").read_text(encoding="utf-8")
    # Each formula has a distinctive operator fragment in both released sources.
    anchors = (
        r"\op{Zscore}(\op{Ma}(\op{close}-\op{vwap},20),30)",
        r"\op{Std}(\op{Pct}(\op{vwap},20),25)\cdot\op{Sum}(\op{volume},40)/\op{volume}",
        r"\op{Corr}(\op{close},\op{volume},50)\cdot\op{Zscore}(\op{Ma}(\op{close}-\op{vwap},30),40)",
        r"\op{Diff}(\op{Ma}(\op{volume},20),3)/\op{Ma}(\op{volume},60)",
        r"\op{Corr}(\op{Pct}(\op{close},10),\op{Pct}(\op{volume},10),10)",
        r"\op{Ma}(\op{Corr}(\op{volume},\op{close},20)\cdot\op{Skew}(\op{high}-\op{low},20),10)",
    )
    if not all(anchor in v1 and anchor in v3 for anchor in anchors):
        raise ValueError("one or more disclosed Alpha-Jungle formula anchors drifted")

    implementation = (repo_root / "scripts/run_fidelity_formula_components.py").read_text(encoding="utf-8")
    ledger_path = repo_root / "paper_runs/fidelity_formula_components/formula_fidelity_ledger.csv"
    with ledger_path.open(newline="", encoding="utf-8") as handle:
        ledger = {row["candidate_id"]: row for row in csv.DictReader(handle)}
    rows: list[dict[str, Any]] = []
    for number, formula, inputs, candidate_id in PAPER_FORMULAS:
        implemented = candidate_id is not None and formula in implementation and candidate_id in ledger
        tree_preserved = implemented and ledger[candidate_id]["formula_tree_preserved"] == "True"
        rows.append(
            {
                "paper_formula_number": number,
                "paper_formula": formula,
                "source_inputs": inputs,
                "present_in_v1_source": True,
                "present_in_v3_source": True,
                "local_candidate_id": candidate_id or "",
                "local_formula_tree_preserved": tree_preserved,
                "local_component_executed": implemented,
                "local_cadence": "monthly_JKP" if implemented else "",
                "paper_cadence": "daily",
                "paper_universe": "CSI300_or_CSI1000",
                "local_universe": "monthly_top_1000_US_equities" if implemented else "",
                "paper_model_and_search_reproduced": False,
                "native_alpha_jungle_result_credit": False,
                "status": (
                    "exact_formula_tree_conditionally_reconstructed_with_cadence_universe_portfolio_adaptations"
                    if implemented
                    else "not_executed_locally_missing_vwap_from_approved_JKP_inputs"
                ),
            }
        )
    if sum(bool(row["local_formula_tree_preserved"]) for row in rows) != 3:
        raise ValueError("expected exactly three preserved local Alpha-Jungle formula trees")
    return rows


def extract_prompts(paper_root: Path, version: str) -> str:
    text = (paper_root / f"source_{version}/sections/Appendix.tex").read_text(encoding="utf-8")
    start = text.find(r"\section{LLM Agent Prompts}")
    if start < 0:
        raise ValueError(f"{version} prompt section missing")
    prompt = "\n".join(line.rstrip() for line in text[start:].strip().splitlines()) + "\n"
    required = (
        "Alpha Portrait Generation Prompt",
        "Alpha Formula Generation Prompt",
        "Alpha Overfitting Risk Assessment Prompt",
        "Alpha Refinement Prompt",
    )
    if not all(value in prompt for value in required):
        raise ValueError(f"{version} prompt section incomplete")
    return prompt


def candidate_source_inventory(source: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative in git(source, "ls-files").splitlines():
        path = source / relative
        rows.append(
            {
                "relative_path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "is_python": relative.endswith(".py"),
                "is_nominal_test": bool(re.search(r"(^|/)test[^/]*\.py$", relative)),
                "is_author_linked_source": False,
                "is_paper_result_artifact": False,
            }
        )
    if len(rows) != 96 or sum(bool(row["is_python"]) for row in rows) != 40:
        raise ValueError("community source inventory drifted")
    return rows


def candidate_execution(source: Path, python: Path) -> dict[str, Any]:
    package = source / "mcts-llm-alpha"
    python_files = [str(path.relative_to(package)) for path in package.rglob("*.py") if "__pycache__" not in path.parts]
    compile_proc = subprocess.run(
        [str(python), "-m", "py_compile", *python_files],
        cwd=package,
        capture_output=True,
        text=True,
    )
    environment = {"PYTHONPATH": "src"}
    import_proc = subprocess.run(
        [str(python), "-c", "import mcts_llm_alpha"],
        cwd=package,
        env={**dict(__import__("os").environ), **environment},
        capture_output=True,
        text=True,
    )
    tests = ["test_fixes.py", "test_ranking_fixes.py", "test_rolling_fix.py"]
    pytest_proc = subprocess.run(
        [str(python), "-m", "pytest", "-o", "addopts=", "-q", *tests],
        cwd=package,
        env={**dict(__import__("os").environ), **environment},
        capture_output=True,
        text=True,
    )
    pytest_output = pytest_proc.stdout + pytest_proc.stderr
    missing_data = "No module named 'mcts_llm_alpha.data'"
    return {
        "repository_role": "unaffiliated_community_candidate_negative_evidence_only",
        "author_linked": False,
        "python": str(python),
        "python_files_compiled": len(python_files),
        "compile_exit_code": compile_proc.returncode,
        "compile_success": compile_proc.returncode == 0,
        "package_import_exit_code": import_proc.returncode,
        "package_import_success": import_proc.returncode == 0,
        "package_import_missing_internal_data_module": missing_data in (import_proc.stdout + import_proc.stderr),
        "pytest_exit_code": pytest_proc.returncode,
        "pytest_collection_errors": len(re.findall(r"^ERROR ", pytest_output, re.MULTILINE)),
        "pytest_tests_passed": 0,
        "pytest_missing_internal_data_module": missing_data in pytest_output,
        "native_paper_experiment_executed": False,
        "native_paper_result_credit": False,
    }


def candidate_method_conformance(execution: Mapping[str, Any]) -> list[dict[str, Any]]:
    entries = [
        ("author affiliation", "conflict", "Repository owner/committer is not a paper author and the paper does not link this repository."),
        ("pinned revision", "specified", f"Community commit {COMMUNITY_COMMIT} is pinned for audit only."),
        ("Python static compilation", "passes", f"All {execution['python_files_compiled']} Python files compile."),
        ("package import", "fails", "Top-level import references a nonexistent mcts_llm_alpha.data package."),
        ("nominal tests", "fails_collection", f"All three nominal test modules fail collection; {execution['pytest_collection_errors']} collection errors."),
        ("paper data package", "missing", "README/source imports describe data support, but no internal data package is tracked."),
        ("paper result artifacts", "missing", "No factor pool, checkpoint, trace, prediction, return path, or paper table output is tracked."),
        ("exact six paper formulas", "missing", "None of the six disclosed Ours formulas appears verbatim in the community tree."),
        ("LLM model", "conflict", "Default is gpt-4o-mini; the paper's main comparison uses GPT-4.1."),
        ("search budget", "conflict", "Default max_iterations is 20; paper comparisons use 1,000/2,000/3,000 generated formulas."),
        ("data interval", "conflict", "Default 2020-01-01 through 2023-12-31 differs from the paper's 2011-2020 training and 2021-2024 testing."),
        ("universe", "partial_conflict", "Default exposes CSI300 only; paper reports CSI300 and CSI1000, and v3 adds S&P500."),
        ("split date", "conflict", "Default 2022-01-01 split differs from the paper's 2021-01-01 test boundary."),
        ("MCTS structure", "partial", "A community MCTS implementation exists but cannot be imported or tied to a paper run."),
        ("FSA structure", "partial", "A frequent-subtree module exists, but no released paper tree or factor zoo validates equivalence."),
        ("exact prompts", "not_verified", "Community prompts are not byte-identical released prompt artifacts or tied to the paper's runtime calls."),
        ("native end-to-end run", "blocked", "Broken package import, absent internal data module, absent exact inputs, and absent model outputs prevent a run."),
    ]
    return [
        {
            "dimension": dimension,
            "assessment": assessment,
            "evidence": evidence,
            "author_source_credit": False,
            "paper_result_credit": False,
        }
        for dimension, assessment, evidence in entries
    ]


def figure_inventory(paper_root: Path) -> list[dict[str, Any]]:
    result_names = {
        "backtest_profit_LGB.pdf", "backtest_profit_MLP.pdf", "freq_efficiency.pdf",
        "mcts_law.pdf", "method_interpretability_comparison.pdf", "method_performance.pdf",
        "parameter_sensitivity_analysis.pdf", "computation_cost.pdf", "efficiency_comparison.pdf",
    }
    rows: list[dict[str, Any]] = []
    for version in ("v1", "v3"):
        for path in sorted((paper_root / f"source_{version}/img").iterdir()):
            if not path.is_file():
                continue
            result_bearing = path.name in result_names
            rows.append(
                {
                    "paper_version": version,
                    "filename": path.name,
                    "sha256": sha256(path),
                    "result_bearing": result_bearing,
                    "raw_plot_data_released": False,
                    "native_result_reproduced": False,
                    "status": "rendered_result_without_raw_plot_data" if result_bearing else "qualitative_or_method_illustration",
                }
            )
    if Counter(row["paper_version"] for row in rows) != {"v1": 14, "v3": 16}:
        raise ValueError("source figure inventory drifted")
    return rows


def method_specification_audit() -> list[dict[str, Any]]:
    entries = [
        ("AAAI publication authority", "specified", "none", "Official AAAI-26 article, DOI, pages 997-1005, and PDF are pinned."),
        ("arXiv original authority", "specified", "none", "v1 PDF and 27-file source archive are pinned."),
        ("arXiv current authority", "specified", "none", "v3 PDF and 28-file source archive are pinned."),
        ("author-linked implementation", "missing", "blocking", "No code link appears in the AAAI paper, arXiv record/source, or author-matched search evidence."),
        ("official source revision", "missing", "blocking", "No executable author source revision exists."),
        ("official software license", "missing", "blocking", "No author software release exists to license."),
        ("machine-readable experiment config", "missing", "blocking", "Paper settings are prose/LaTeX only."),
        ("factor pools", "missing", "blocking", "Generated alpha sets of size 10/50/100 are not released."),
        ("MCTS trees and search traces", "missing", "blocking", "No node, score, action, refinement, or budget trace is released."),
        ("LLM request/response logs", "missing", "blocking", "No runtime prompt instances, responses, tool errors, or token traces are released."),
        ("model snapshot", "partial", "blocking", "GPT-4.1 family name is given without an immutable provider snapshot/revision."),
        ("decoding temperatures", "specified", "none", "Portrait/formula 1.0, correction 0.8, and overfitting score 0.1 are stated."),
        ("prompt templates", "specified", "none", "Four detailed templates are released in both arXiv appendices."),
        ("runtime prompt assembly", "partial", "major", "Templates contain dynamic fields; exact filled prompts and ordering are absent."),
        ("random seeds for alpha search", "missing", "blocking", "No seeds for stochastic LLM generation, MCTS sampling, or model training are reported."),
        ("operator set", "specified", "none", "Appendix enumerates supported operators."),
        ("formula parser implementation", "missing", "blocking", "Syntax rules are described but executable parser/semantics are absent."),
        ("six example formulas", "specified", "none", "Six Ours formulas are printed in the appendix."),
        ("exact formula component execution", "partial", "major", "Three of six trees are locally reconstructed only under monthly U.S. adaptations."),
        ("China market-data snapshot", "missing", "blocking", "No immutable Qlib bundle or vendor snapshot is identified."),
        ("Qlib revision", "missing", "blocking", "Qlib is cited without a commit/package version."),
        ("CSI300 point-in-time constituents", "missing", "blocking", "No membership history or snapshot is released."),
        ("CSI1000 point-in-time constituents", "missing", "blocking", "No membership history or snapshot is released."),
        ("S&P500 point-in-time constituents", "missing", "blocking", "v3 adds S&P500 without membership history or snapshot."),
        ("price adjustment/corporate actions", "missing", "blocking", "Adjustment, split, dividend, suspension, and delisting rules are not pinned."),
        ("China train interval", "specified", "none", "2011-01-01 through 2020-12-31."),
        ("China test interval", "specified", "none", "2021-01-01 through 2024-11-30."),
        ("S&P500 train/test intervals", "specified_v3", "none", "2007-2015 train and 2016-01-01 through 2020-10-10 test."),
        ("bar frequency", "specified", "none", "Daily stock data are used."),
        ("input fields", "specified", "none", "Open, high, low, close, volume and vwap-dependent examples are documented."),
        ("prediction horizons", "specified", "none", "China experiments use 10- and 30-day forward returns; S&P500 uses 10-day."),
        ("label implementation", "partial", "major", "Horizon/close execution are stated, but executable alignment and suspension rules are absent."),
        ("initial MCTS budget", "specified", "none", "B=3 is reported for the studied configuration."),
        ("dynamic budget increment", "specified", "none", "b=1 is stated."),
        ("UCT exploration constant", "partial", "major", "Sensitivity is shown, but no immutable run config ties c to every reported table."),
        ("dimension sampling temperature", "specified", "none", "T=1 is stated."),
        ("few-shot example count", "specified", "none", "One example is stated for refinement suggestions."),
        ("correlation filtering ratio", "specified", "none", "eta=50% is stated."),
        ("FSA avoided patterns", "specified", "none", "Three frequent subtrees are avoided."),
        ("FSA executable semantics", "missing", "blocking", "Closed-root-gene equations lack an author implementation and exact repositories."),
        ("symbolic parameter candidates", "specified", "none", "Three candidate parameter sets per formula are reported."),
        ("parameter selection leakage control", "partial", "major", "Best backtest configuration is selected, but validation boundary and multiplicity controls are incomplete."),
        ("LightGBM configuration", "specified", "none", "Appendix supplies key hyperparameters."),
        ("MLP architecture", "specified", "none", "Three 256/128/64 layers, dropout, optimizer, learning rate, batch size, and patience are supplied."),
        ("validation split for early stopping", "missing", "blocking", "Validation dates/construction and training seeds are absent."),
        ("alpha set sizes", "specified", "none", "10, 50, and 100."),
        ("LLM search counts", "specified", "none", "1,000, 2,000, and 3,000 candidates."),
        ("non-LLM search cap", "specified", "none", "Up to 600,000 candidates."),
        ("wall-clock cap", "specified", "none", "A maximum of 24 hours is described."),
        ("baseline source revisions/configs", "missing", "blocking", "No exact baseline wrappers, commits, seeds, or run outputs are released."),
        ("portfolio top-k", "specified", "none", "Top 10% of each universe, equally weighted."),
        ("drop-n rule", "specified", "none", "n=k/w is stated."),
        ("transaction cost", "specified", "none", "0.15% per trade is stated."),
        ("trade simulator implementation", "missing", "blocking", "No fills, turnover state, corporate-action handling, or return path is released."),
        ("AER benchmark return", "missing", "blocking", "v3 defines excess return against a market benchmark without pinning its exact series/construction."),
        ("v1 AR to v3/final AER lineage", "conflict", "blocking", "Sixteen final ablation AER cells equal v1 AR cells despite changed return semantics and no run lineage."),
        ("v3 appendix metric headers", "conflict", "major", "228 v3 cells remain labelled AR while the current metric definition and main text use AER."),
        ("raw predictions/returns", "missing", "blocking", "No predictions, holdings, costs, benchmark returns, or equity paths are released."),
        ("main-table uncertainty", "missing", "blocking", "No repeated-run uncertainty or statistical tests accompany predictive/trading tables."),
        ("interpretability samples/judgments", "missing", "blocking", "Selected formulas, judge prompts/responses, per-seed rankings, and model revisions are absent."),
        ("cost input lineage", "paper_only", "major", "Runtime and token counts are printed without logs; arithmetic is internally consistent only."),
        ("hardware/software environment", "partial", "major", "Broad server assumptions are described, but native package/driver/hardware revisions are absent."),
        ("full native rerun", "missing", "blocking", "Paper sources compile, but the experiment cannot be reconstructed from public artifacts."),
    ]
    return [
        {
            "dimension": dimension,
            "assessment": assessment,
            "severity": severity,
            "evidence": evidence,
            "native_alpha_jungle_verified": False,
        }
        for dimension, assessment, severity, evidence in entries
    ]


def qualitative_claim_audit() -> list[dict[str, Any]]:
    return [
        {
            "paper_version": "AAAI-26_final",
            "claim": "published Table 1 result reproduction",
            "observed": "0/64 official table cells reproduced from an author experiment path",
            "assessment": "not_publicly_reproducible",
        },
        {
            "paper_version": "v3_and_final",
            "claim": "AER ablation results",
            "observed": "16/16 AER-position cells retain the exact v1 AR display values after the metric changed from total to benchmark-excess return",
            "assessment": "unsupported_semantic_relabel_without_run_lineage",
        },
        {
            "paper_version": "v3",
            "claim": "current evaluation consistently uses AER",
            "observed": "228 appendix result cells are still headed AR, including full and equal-cost tables",
            "assessment": "internally_inconsistent_metric_identity",
        },
        {
            "paper_version": "v3",
            "claim": "cost-performance comparison",
            "observed": "30/30 derived server/API/total cells reconcile from same-table inputs, but no runtime/token logs independently support those inputs",
            "assessment": "internally_consistent_not_independently_reproduced",
        },
        {
            "paper_version": "both",
            "claim": "data leakage concern is alleviated",
            "observed": "a direct-prompt performance comparison cannot establish absence of paper-formula contamination in proprietary LLM training data",
            "assessment": "evidence_does_not_identify_training_data_contamination",
        },
        {
            "paper_version": "AAAI-26_final",
            "claim": "improved interpretability",
            "observed": "LLM rankings are reported, but selected formulas, exact judge calls, revisions, and per-seed outputs are not released; paper notes no formal human study",
            "assessment": "paper_only_automated_judgment_not_reproducible",
        },
        {
            "paper_version": "local",
            "claim": "existing Alpha-Jungle formula component evidence",
            "observed": "3/6 disclosed Ours trees execute only after daily-China to monthly-U.S. and researcher-portfolio adaptations",
            "assessment": "conditional_component_evidence_not_agent_or_paper_result_replication",
        },
        {
            "paper_version": "community_candidate",
            "claim": "public implementation of the paper",
            "observed": "unaffiliated repository has no author link, fails import/tests, conflicts on core settings, and ships no paper outputs",
            "assessment": "not_author_source_and_not_operational_replication",
        },
    ]


def compile_sources(paper_root: Path) -> dict[str, Any]:
    if shutil.which("pdflatex") is None or shutil.which("pdfinfo") is None:
        raise RuntimeError("pdflatex and pdfinfo are required for the Alpha-Jungle audit")
    results: dict[str, Any] = {}
    for version, expected_pages, expected_files in (("v1", 30, 27), ("v3", 31, 28)):
        source = paper_root / f"source_{version}"
        with tempfile.TemporaryDirectory(prefix=f"alpha-jungle-{version}-") as temp:
            work = Path(temp) / "source"
            shutil.copytree(source, work)
            exit_codes: list[int] = []
            for _ in range(2):
                proc = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                    cwd=work,
                    capture_output=True,
                    text=True,
                )
                exit_codes.append(proc.returncode)
                if proc.returncode:
                    raise RuntimeError(proc.stdout[-4000:] + proc.stderr[-4000:])
            info = subprocess.run(
                ["pdfinfo", str(work / "main.pdf")], check=True, capture_output=True, text=True
            ).stdout
            page_match = re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE)
            if page_match is None:
                raise ValueError(f"could not read compiled {version} page count")
            pages = int(page_match.group(1))
            source_files = sum(path.is_file() for path in source.rglob("*"))
            if pages != expected_pages or source_files != expected_files:
                raise ValueError(f"{version} source drift: pages={pages}, files={source_files}")
            results[version] = {
                "exit_codes": exit_codes,
                "pages": pages,
                "source_files": source_files,
                "paper_result_credit": False,
            }
    return results


def validate_inputs(paper_root: Path, community: Path) -> dict[str, Any]:
    expected = {
        paper_root / "arxiv_v1.pdf": ARXIV_V1_PDF_SHA256,
        paper_root / "arxiv_v1_source.tar": ARXIV_V1_SOURCE_SHA256,
        paper_root / "arxiv_v3.pdf": ARXIV_V3_PDF_SHA256,
        paper_root / "arxiv_v3_source.tar": ARXIV_V3_SOURCE_SHA256,
        paper_root / "aaai_final.pdf": AAAI_FINAL_PDF_SHA256,
        paper_root / "arxiv_abs.html": ARXIV_ABS_SHA256,
    }
    expected.update({paper_root / filename: value for filename, value in GITHUB_SEARCH_SHA256.items()})
    for path, digest in expected.items():
        observed = sha256(path)
        if observed != digest:
            raise ValueError(f"pinned input hash mismatch: {path}: {observed}")
    search_counts: dict[str, int] = {}
    for filename, expected_count in GITHUB_SEARCH_COUNTS.items():
        payload = json.loads((paper_root / filename).read_text(encoding="utf-8"))
        count = int(payload.get("total_count", -1))
        if count != expected_count:
            raise ValueError(f"GitHub search snapshot drifted: {filename}={count}")
        search_counts[filename] = count
    if git(community, "rev-parse", "HEAD").strip() != COMMUNITY_COMMIT:
        raise ValueError("community commit mismatch")
    if git(community, "rev-parse", "HEAD^{tree}").strip() != COMMUNITY_TREE:
        raise ValueError("community tree mismatch")
    archive = bytes_sha256(git(community, "archive", "--format=tar", "HEAD", binary=True))
    if archive != COMMUNITY_ARCHIVE_SHA256:
        raise ValueError("community archive hash mismatch")
    return {
        "validated_file_count": len(expected),
        "github_search_counts": search_counts,
        "author_linked_repository_found": False,
        "community_archive_validated": True,
    }


def readme() -> str:
    return """# Alpha-Jungle paper-level replication audit

The official nine-page AAAI-26 proceedings paper is the publication authority.
The original arXiv v1 and current v3 extended sources are audited separately.

## Honest outcome

- **Published result reproduction: 0/64 official Table 1 cells.** No
  author-linked code, immutable experiment configuration, China/S&P500 data
  snapshot, factor pool, search trace, LLM call log, predictions, holdings,
  return path, or native result output was found.
- **Extended result reproduction: 0/956 v1 cells and 0/1,312 v3 cells.** Source
  compilation and exact table parsing verify the documents, not the experiments.
- **Formula-component evidence: 3/6 disclosed Ours formula trees.** Formulas
  4-6 are already executed locally with their operator trees preserved, but
  only after daily-China to monthly-U.S. universe/cadence and researcher-
  portfolio adaptations. They receive no MCTS, model, portfolio, or paper-
  result credit. Formulas 1-3 require VWAP, absent from the approved JKP input.
- **Prompts:** four detailed prompt templates are recoverable from both source
  releases. Exact filled runtime prompts, model responses, and immutable model
  snapshots are absent.

## Result-lineage warning

Across 932 semantically common v1/v3 cells, 925 retain the same displayed
number. All 16 v1 ablation cells labelled AR are unchanged when v3 and the
published final relabel them AER, even though AR uses total portfolio returns
and AER uses returns over an unspecified market benchmark. No executable run
lineage is released. Separately, 228 current-v3 appendix cells still use AR
headers while the current metric section and main text define AER.

The v3 cost table is arithmetically self-consistent: all 30 derived server,
API, and total-cost cells recompute from values printed in the same table. This
is an internal consistency check, not independent reproduction of runtimes or
token usage.

## Community repository

`dtbtc/mcts-llm-alpha` is pinned only as an unaffiliated community candidate.
All 40 tracked Python files compile, but the package imports a nonexistent
`mcts_llm_alpha.data` module and all three nominal tests fail collection. Its
defaults also conflict with the paper on model, search budget, dates, split,
and universes, and it contains no native factor pools or paper results.

Alpha-Jungle therefore remains
`paper_only_underspecified_with_three_adapted_disclosed_formula_components`.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--paper-root",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/alpha_jungle_paper_audit"),
    )
    parser.add_argument(
        "--community-source",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/alpha_jungle_paper_audit/candidate_dtbtc"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--candidate-python",
        type=Path,
        default=Path("/nfs/roberts/project/pi_btk22/zc362/environments/bin/kt-python"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("paper_runs/paper_replication_audits/alpha_jungle"),
    )
    args = parser.parse_args()
    paper_root = args.paper_root.resolve()
    community = args.community_source.resolve()
    repo_root = args.repo_root.resolve()
    output = args.output.resolve()

    validated = validate_inputs(paper_root, community)
    v1 = parse_results(paper_root, "v1")
    v3 = parse_results(paper_root, "v3")
    published = published_final_rows(paper_root, v3)
    lineage = version_lineage(v1, v3)
    costs = cost_arithmetic(v3)
    formulas = formula_component_conformance(paper_root, repo_root)
    prompts = {version: extract_prompts(paper_root, version) for version in ("v1", "v3")}
    source_rows = candidate_source_inventory(community)
    execution = candidate_execution(community, args.candidate_python.resolve())
    candidate_conformance = candidate_method_conformance(execution)
    figures = figure_inventory(paper_root)
    methods = method_specification_audit()
    claims = qualitative_claim_audit()
    compilations = compile_sources(paper_root)

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "aaai_final_table_result_conformance.csv", published)
    write_csv(output / "v1_extended_table_result_conformance.csv", v1)
    write_csv(output / "v3_extended_table_result_conformance.csv", v3)
    write_csv(output / "version_lineage_audit.csv", lineage)
    write_csv(output / "cost_arithmetic_audit.csv", costs)
    write_csv(output / "formula_component_conformance.csv", formulas)
    write_csv(output / "community_source_inventory.csv", source_rows)
    write_csv(output / "community_method_conformance.csv", candidate_conformance)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "qualitative_claim_audit.csv", claims)
    for version, prompt in prompts.items():
        (output / f"paper_prompts_{version}.tex.txt").write_text(prompt, encoding="utf-8")
    (output / "README.md").write_text(readme(), encoding="utf-8")
    write_json(output / "community_execution.json", execution)

    current_ar_header_conflicts = sum(
        1
        for row in v3
        if (
            row["paper_table"] in FULL_TABLES or row["paper_table"] in {"llm_sensitivity", "equal_cost"}
        )
        and str(row["metric"]).endswith("_AR")
    )
    if current_ar_header_conflicts != 228:
        raise ValueError(f"expected 228 v3 AR-header conflicts, got {current_ar_header_conflicts}")

    native = {
        "author_linked_source_found": False,
        "native_alpha_jungle_execution_attempted": False,
        "native_blocker": "no author-linked source, exact inputs/config, factor pool, trace, or result artifacts",
        "published_final_cells_reproduced": 0,
        "v1_extended_cells_reproduced": 0,
        "v3_extended_cells_reproduced": 0,
        "paper_source_compilation": compilations,
        "official_pdf_table_text_verified": True,
        "released_prompt_templates_recovered": 4,
        "adapted_exact_formula_trees_executed": sum(bool(row["local_component_executed"]) for row in formulas),
        "adapted_formula_execution_is_native_paper_credit": False,
        "community_candidate_execution": execution,
    }
    write_json(output / "native_execution.json", native)

    provenance = {
        "audit_date": AUDIT_DATE,
        "publication_authority": {
            "url": AAAI_ARTICLE_URL,
            "pdf_url": AAAI_PDF_URL,
            "doi": DOI,
            "pdf_sha256": AAAI_FINAL_PDF_SHA256,
            "pages": 9,
            "page_range": "997-1005",
            "authors": ["Yu Shi", "Yitong Duan", "Jian Li"],
        },
        "original_arxiv": {
            "url": ARXIV_V1_URL,
            "pdf_sha256": ARXIV_V1_PDF_SHA256,
            "source_sha256": ARXIV_V1_SOURCE_SHA256,
            "submitted": "2025-05-16",
            "pages": 30,
        },
        "current_arxiv": {
            "url": ARXIV_V3_URL,
            "pdf_sha256": ARXIV_V3_PDF_SHA256,
            "source_sha256": ARXIV_V3_SOURCE_SHA256,
            "submitted": "2025-11-12",
            "pages": 31,
        },
        "arxiv_record": {"url": ARXIV_URL, "html_sha256": ARXIV_ABS_SHA256},
        "official_author_repository_found": False,
        "github_repository_search": {
            "snapshot_sha256": GITHUB_SEARCH_SHA256,
            "counts": GITHUB_SEARCH_COUNTS,
            "assessment": "no_author_linked_implementation; results are indexes, unrelated repositories, or community work",
        },
        "community_candidate": {
            "url": COMMUNITY_URL,
            "commit": COMMUNITY_COMMIT,
            "tree": COMMUNITY_TREE,
            "archive_sha256": COMMUNITY_ARCHIVE_SHA256,
            "committer": "VeighNa Developer <developer@vnpy.com>",
            "commit_date": "2025-07-23T21:39:25+08:00",
            "author_linked": False,
            "paper_credit": "none_negative_evidence_only",
        },
        "validation": validated,
    }
    write_json(output / "source_provenance.json", provenance)

    tracked = [
        "README.md",
        "aaai_final_table_result_conformance.csv",
        "v1_extended_table_result_conformance.csv",
        "v3_extended_table_result_conformance.csv",
        "version_lineage_audit.csv",
        "cost_arithmetic_audit.csv",
        "formula_component_conformance.csv",
        "community_source_inventory.csv",
        "community_method_conformance.csv",
        "community_execution.json",
        "figure_inventory.csv",
        "method_specification_audit.csv",
        "qualitative_claim_audit.csv",
        "paper_prompts_v1.tex.txt",
        "paper_prompts_v3.tex.txt",
        "native_execution.json",
        "source_provenance.json",
    ]
    manifest = {
        "paper": "Navigating the Alpha Jungle: An LLM-Powered MCTS Framework for Formulaic Alpha Factor Mining",
        "audit_date": AUDIT_DATE,
        "paper_evidence_route": "paper_only_underspecified_with_three_adapted_disclosed_formula_components",
        "overall_status": "zero_of_64_published_cells_reproduced_zero_native_results_three_of_six_formula_trees_conditionally_adapted",
        "full_paper_reproduced": False,
        "official_author_source_released": False,
        "published_final_table_result_cells": len(published),
        "published_final_table_result_cells_reproduced": 0,
        "v1_extended_table_result_cells": len(v1),
        "v1_extended_table_result_cells_reproduced": 0,
        "v3_extended_table_result_cells": len(v3),
        "v3_extended_table_result_cells_reproduced": 0,
        "native_alpha_jungle_result_cells_reproduced": 0,
        "disclosed_ours_formula_trees": len(formulas),
        "adapted_formula_trees_executed": sum(bool(row["local_component_executed"]) for row in formulas),
        "adapted_formula_trees_with_paper_result_credit": 0,
        "common_v1_v3_result_cells": len(lineage),
        "common_v1_v3_same_display_value": sum(bool(row["same_numeric_display_value"]) for row in lineage),
        "v1_AR_cells_relabelled_v3_AER": sum(bool(row["AR_to_AER_semantic_relabel"]) for row in lineage),
        "v3_AR_header_cells_conflicting_with_current_AER_definition": current_ar_header_conflicts,
        "cost_derived_cells_arithmetically_consistent": sum(bool(row["match_at_paper_precision"]) for row in costs),
        "cost_arithmetic_cells_with_paper_result_credit": 0,
        "prompt_templates_recovered_per_version": 4,
        "paper_source_compilation": compilations,
        "community_candidate_python_files": sum(bool(row["is_python"]) for row in source_rows),
        "community_candidate_import_success": execution["package_import_success"],
        "community_candidate_pytest_collection_errors": execution["pytest_collection_errors"],
        "method_specification_dimensions": len(methods),
        "method_assessment_counts": dict(sorted(Counter(row["assessment"] for row in methods).items())),
        "method_severity_counts": dict(sorted(Counter(row["severity"] for row in methods).items())),
        "source_figure_files": len(figures),
        "result_bearing_source_figure_files": sum(bool(row["result_bearing"]) for row in figures),
        "output_sha256": {name: sha256(output / name) for name in tracked},
    }
    write_json(output / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
