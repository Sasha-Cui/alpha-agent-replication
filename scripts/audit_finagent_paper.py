#!/usr/bin/env python3
"""Fail-closed paper/source audit for FinAgent (KDD 2024).

The arXiv v3 paper is the detailed result authority and the KDD proceedings
PDF is the publication authority.  The released repository is linked from the
lead author's current homepage.  Static source conformance, paper-source
compilation, and shipped strategy records are useful evidence, but none are
promoted to experimental-result reproduction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


ARXIV_URL = "https://arxiv.org/abs/2402.18485"
ARXIV_V3_DATE = "2024-06-28"
ARXIV_V3_PDF_SHA256 = "c5964450c7dd29c00cc92cbc845cd14223d08f04429f6b4b0c612c8678b69922"
ARXIV_V3_SOURCE_SHA256 = "421e432111f5543c9f7c1ba1a2b65d1d8b3ba686ad5f02c937b0d60561eaf1a7"
KDD_PDF_URL = "https://dl.acm.org/doi/pdf/10.1145/3637528.3671684"
KDD_PDF_SHA256 = "cfc31d78f7919c104f741aee197866bd8f8a938b2504b5f8eebc8b1b57f40dd8"
DOI = "10.1145/3637528.3671684"
AUTHOR_HOMEPAGE = "https://dvampire.github.io/"
SOURCE_URL = "https://github.com/DVampire/FinAgent"
SOURCE_PAPER_COMMIT = "08fb217d374b6c923b0ab3e6dbd8213e1d0fcf1c"
SOURCE_PAPER_DATE = "2024-04-11T14:03:24+08:00"
SOURCE_PAPER_TREE = "70c0a2277fded3b77195b74ab71e0d2c8723a6a4"
SOURCE_PAPER_ARCHIVE_SHA256 = "9d530843df299e08c8642b296dd5116f229fd8fb41fb42b13a8d0f113f275d4d"
SOURCE_CURRENT_COMMIT = "17248a0b8b729ee3e093e30bb7bea7f52181f363"
SOURCE_CURRENT_DATE = "2024-08-31T20:13:54+02:00"
SOURCE_CURRENT_TREE = "71047850ceab7579e8c083dfada486bbbae17007"
SOURCE_CURRENT_ARCHIVE_SHA256 = "e2954e7b22b4d1280ac28de2af979907ad3e7d5f1a8e203add2926414cff9c5c"
AUDIT_DATE = "2026-08-11"

ASSETS = ("AAPL", "AMZN", "GOOGL", "MSFT", "TSLA", "ETHUSD")
MAIN_METHODS = (
    "B&H", "MACD", "KDJ&RSI", "ZMR", "LGBM", "LSTM", "Transformer",
    "DQN", "SAC", "PPO", "FinGPT", "FinMem", "FinAgent",
)
APPENDIX_METHODS = (
    "B&H", "MACD", "KDJ&RSI", "ZMR", "LGBM", "LSTM", "Transformer",
    "DQN", "SAC", "PPO", "FinGPT", "FinMem", "No-finetuned", "w/o-MLH",
    "w/o-LHT", "w/o-HT", "w/o-T", "FinAgent",
)
MAIN_METRICS = ("ARR_pct", "SR", "MDD_pct")
APPENDIX_PANELS = (
    ("ARR_pct", "SR", "MDD_pct"),
    ("SOR", "CR", "VOL"),
)
FIGURE4_SERIES = (
    "B&H", "MACD", "KDJ&RSI", "SO&BB", "ZMR", "DQN", "SAC", "PPO",
    "FinGPT", "FinMem", "FinAgent",
)
APPENDIX_RESULT_GRAPHICS = (
    "assets/finagent_and_baselines/ppo/AAPL_PPO.pdf",
    "assets/finagent_and_baselines/ppo/GOOGL_PPO.pdf",
    "assets/finagent_and_baselines/dqn/GOOGL_DQN.pdf",
    "assets/finagent_and_baselines/dqn/AMZN_DQN.pdf",
    "assets/finagent_and_baselines/dqn/ETH_DQN.pdf",
    "assets/finagent_and_baselines/sac/ETH_SAC.pdf",
    "assets/finagent_and_baselines/sac/MSFT_SAC.pdf",
    "assets/finagent_and_baselines/sac/AMZN_SAC.pdf",
    "assets/finagent_and_baselines/fingpt/AAPL_FinGPT.pdf",
    "assets/finagent_and_baselines/fingpt/GOOGL_FinGPT.pdf",
    "assets/finagent_and_baselines/fingpt/MSFT_FinGPT.pdf",
    "assets/finagent_and_baselines/fingpt/TSLA_FinGPT.pdf",
    "assets/finagent_and_baselines/finmem/AAPL_FinMem.pdf",
    "assets/finagent_and_baselines/finmem/MSFT_FinMem.pdf",
    "assets/finagent_and_baselines/finmem/TSLA_FinMem.pdf",
    "assets/finagent_and_baselines/finmem/ETHUSD_FinMem.pdf",
    "assets/finagent_and_baselines/MACD/MACD_AAPL.pdf",
    "assets/finagent_and_baselines/MACD/MACD_GOOGL.pdf",
    "assets/finagent_and_baselines/MACD/MACD_ETHUSD.pdf",
    "assets/finagent_and_baselines/MACD/MACD_MSFT.pdf",
    "assets/finagent_and_baselines/KDJ_RSI/KDJ_RSI_AAPL.pdf",
    "assets/finagent_and_baselines/KDJ_RSI/KDJ_RSI_TSLA.pdf",
    "assets/finagent_and_baselines/ZMR/ZMR_AAPL.pdf",
    "assets/finagent_and_baselines/ZMR/ZMR_TSLA.pdf",
    "assets/finagent_and_baselines/tool_router/ETHUSD.pdf",
    "assets/finagent_and_baselines/tool_router/AAPL.pdf",
    "assets/finagent_and_baselines/finagent/AAPL_FinAgent.pdf",
    "assets/finagent_and_baselines/finagent/GOOGL_FinAgent.pdf",
    "assets/finagent_and_baselines/finagent/ETHUSD_FinAgent.pdf",
)
RULE_STRATEGY_METHODS = {
    "0": "B&H",
    "1": "MACD",
    "2": "KDJ&RSI",
    "4": "ZMR",
}
RECORD_METRICS = {
    "ARR_pct": ("ARR", 100.0),
    "SR": ("SR", 1.0),
    "MDD_pct": ("MDD", 100.0),
    "SOR": ("SOR", 1.0),
    "CR": ("CR", 1.0),
    "VOL": ("VOL", 1.0),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(source_root: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source_root), *args], check=True,
        capture_output=True, text=not binary,
    )
    return proc.stdout


def git_archive_sha256(source_root: Path, commit: str) -> str:
    return hashlib.sha256(git(source_root, "archive", commit, binary=True)).hexdigest()


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _active_table(text: str, label: str) -> str:
    end = text.rindex(label)
    starts = [match.start() for match in re.finditer(r"\\begin\{table\*?\}", text[:end])]
    if not starts:
        raise ValueError(f"active table not found before {label}")
    start = starts[-1]
    return text[start:end]


def _semantic_cells(line: str) -> list[str]:
    return [cell.strip() for cell in re.split(r"(?<!\\)&", line) if cell.strip()]


def _number(cell: str) -> str | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", cell)
    return match.group(0) if match else None


def _method_name(cell: str) -> str | None:
    for method in sorted(APPENDIX_METHODS, key=len, reverse=True):
        if method in cell or method.replace("&", "\\&") in cell:
            return method
    return None


def _result_row(table: str, item: str, metric: str, value: str) -> dict[str, Any]:
    return {
        "paper_table": table,
        "display_cell_id": f"{table}/{item}/{metric}",
        "item": item,
        "metric": metric,
        "paper_value": value,
        "native_reproduced_value": "",
        "status": "not_reproduced_no_released_agent_result_artifacts_or_exact_inputs",
        "paper_result_credit": False,
    }


def _method_rows(block: str, methods: Sequence[str], metrics: Sequence[str], table: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: list[str] = []
    for raw in block.splitlines():
        if raw.lstrip().startswith("%") or not raw.lstrip().startswith("&"):
            continue
        cells = _semantic_cells(raw)
        if not cells:
            continue
        method = _method_name(cells[0])
        if method not in methods:
            continue
        values = [_number(cell) for cell in cells[1:]]
        values = [value for value in values if value is not None]
        expected = len(ASSETS) * len(metrics)
        if len(values) != expected:
            raise RuntimeError(f"{table}/{method}: expected {expected} values, got {len(values)}")
        seen.append(method)
        for asset_index, asset in enumerate(ASSETS):
            for metric_index, metric in enumerate(metrics):
                value = values[asset_index * len(metrics) + metric_index]
                rows.append(_result_row(table, f"{asset}/{method}", metric, value))
    if tuple(seen) != tuple(methods):
        raise RuntimeError(f"{table}: method order changed: {seen}")
    return rows


def _improvement_rows(block: str, table: str, metrics: Sequence[str]) -> list[dict[str, Any]]:
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("%") and "Improvement" in line:
            values_line = lines[index + 1]
            cells = _semantic_cells(values_line)
            rows: list[dict[str, Any]] = []
            semantic_index = 0
            for asset in ASSETS:
                for metric in metrics:
                    if semantic_index >= len(cells):
                        raise RuntimeError(f"{table}: truncated improvement row")
                    value = _number(cells[semantic_index])
                    semantic_index += 1
                    if value is not None:
                        rows.append(_result_row(table, f"{asset}/Improvement", metric, value))
            return rows
    raise RuntimeError(f"{table}: active improvement row missing")


def paper_table_rows(paper_source_root: Path) -> list[dict[str, Any]]:
    main_block = _active_table(
        (paper_source_root / "tables/baselines.tex").read_text(encoding="utf-8"),
        "\\label{tab:baselines}",
    )
    rows = _method_rows(main_block, MAIN_METHODS, MAIN_METRICS, "Table 4 main comparison")
    rows += _improvement_rows(main_block, "Table 4 main comparison", MAIN_METRICS)

    appendix_block = _active_table(
        (paper_source_root / "tables/appendix_baselines.tex").read_text(encoding="utf-8"),
        "\\label{tab:app_baselines}",
    )
    split_marker = "\\toprule\n\\multirow{3}{*}{Categories}"
    pieces = appendix_block.split(split_marker)
    if len(pieces) != 3:
        raise RuntimeError("Appendix Table 7 two-panel boundary changed")
    for panel_index, metrics in enumerate(APPENDIX_PANELS):
        panel = pieces[panel_index + 1]
        table = f"Appendix Table 7 panel {panel_index + 1}"
        rows += _method_rows(panel, APPENDIX_METHODS, metrics, table)
        rows += _improvement_rows(panel, table, metrics)

    ablation_block = _active_table(
        (paper_source_root / "tables/ablation.tex").read_text(encoding="utf-8"),
        "\\label{tab:ablation}",
    )
    variants = ("T_only", "M_only", "ML", "MLH", "MLHT")
    candidate_lines = [
        line for line in ablation_block.splitlines()
        if not line.lstrip().startswith("%") and "surd" in line and "&" in line
    ]
    if len(candidate_lines) != 5:
        raise RuntimeError(f"Table 5: expected five ablation rows, got {len(candidate_lines)}")
    for variant, line in zip(variants, candidate_lines):
        values = re.findall(r"[-+]?\d+(?:\.\d+)?", line)
        expected = 6 if variant in ("T_only", "M_only") else 12
        if len(values) != expected:
            raise RuntimeError(f"Table 5/{variant}: expected {expected} values, got {len(values)}")
        cursor = 0
        for asset in ("TSLA", "ETHUSD"):
            for metric in MAIN_METRICS:
                rows.append(_result_row("Table 5 ablation", f"{asset}/{variant}", metric, values[cursor]))
                cursor += 1
                if expected == 12:
                    rows.append(_result_row(
                        "Table 5 ablation", f"{asset}/{variant}", f"{metric}_parenthetical_delta_pct",
                        values[cursor],
                    ))
                    cursor += 1

    expected_counts = {
        "Table 4 main comparison": 242,
        "Appendix Table 7 panel 1": 335,
        "Appendix Table 7 panel 2": 334,
        "Table 5 ablation": 48,
    }
    if len(rows) != 959 or Counter(row["paper_table"] for row in rows) != expected_counts:
        raise RuntimeError("FinAgent paper table census changed")
    return rows


def paper_figure_rows(paper_source_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in ASSETS:
        for series in FIGURE4_SERIES:
            rows.append({
                "paper_figure": "Figure 4 cumulative return",
                "display_unit": f"{asset}/{series}",
                "source_asset": "assets/baselines.pdf",
                "native_reproduced": False,
                "status": "raster_or_vector_plot_only_no_underlying_trajectory",
                "paper_result_credit": False,
            })
    for unit in ("ML", "MLH", "MLHT", "T"):
        rows.append({
            "paper_figure": "Figure 5 component ablation",
            "display_unit": unit,
            "source_asset": "assets/dr.pdf",
            "native_reproduced": False,
            "status": "plot_only_no_underlying_trial_records",
            "paper_result_credit": False,
        })
    for unit in ("without_diversification", "rag", "rag_plus_diversification"):
        rows.append({
            "paper_figure": "Figure 5 retrieval/diversification",
            "display_unit": unit,
            "source_asset": "assets/dr.pdf",
            "native_reproduced": False,
            "status": "plot_only_no_underlying_trial_records",
            "paper_result_credit": False,
        })
    for asset_path in APPENDIX_RESULT_GRAPHICS:
        if not (paper_source_root / asset_path).is_file():
            raise RuntimeError(f"active appendix result graphic missing: {asset_path}")
        rows.append({
            "paper_figure": "Appendix qualitative/performance cases",
            "display_unit": Path(asset_path).stem,
            "source_asset": asset_path,
            "native_reproduced": False,
            "status": "graphic_only_no_underlying_action_or_equity_path",
            "paper_result_credit": False,
        })
    if len(rows) != 102:
        raise RuntimeError(f"expected 102 figure display units, got {len(rows)}")
    return rows


def source_inventory(source_root: Path, commit: str = SOURCE_PAPER_COMMIT) -> list[dict[str, Any]]:
    paths = git(source_root, "ls-tree", "-r", "--name-only", commit).splitlines()
    rows = []
    for path in paths:
        suffix = Path(path).suffix.lower()
        if suffix == ".py":
            kind = "python_source"
        elif suffix in (".html", ".json") and path.startswith("res/prompts/"):
            kind = "prompt_or_schema"
        elif path.startswith("res/strategy_record/"):
            kind = "strategy_training_record"
        elif path.startswith("configs/"):
            kind = "configuration"
        else:
            kind = "other"
        rows.append({"commit": commit, "path": path, "kind": kind})
    return rows


def strategy_record_rows(source_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    root = source_root / "res/strategy_record"
    for path in sorted(root.rglob("*.json")):
        rel = path.relative_to(source_root).as_posix()
        payload = json.loads(path.read_text(encoding="utf-8"))
        kind = path.name.removesuffix(".json")
        parts = rel.split("/")
        rows.append({
            "path": rel,
            "asset": parts[3] if len(parts) > 3 else "",
            "strategy_index": parts[4] if len(parts) > 4 else "",
            "variant": parts[6] if len(parts) > 6 else "",
            "record_kind": kind,
            "nonempty": bool(payload),
            "payload_sha256": sha256(path),
            "paper_test_result_artifact": False,
            "paper_result_credit": False,
        })
    if len(rows) != 90:
        raise RuntimeError(f"expected 90 strategy records, got {len(rows)}")
    return rows


def strategy_record_paper_conformance_rows(
    source_root: Path,
    paper_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    appendix = {
        (str(row["item"]), str(row["metric"])): str(row["paper_value"])
        for row in paper_rows
        if str(row["paper_table"]).startswith("Appendix Table 7 panel")
    }
    rows: list[dict[str, Any]] = []
    record_root = source_root / "res/strategy_record/trading"
    for path in sorted(record_root.glob("*/*/exp001/*/best_result.json")):
        rel = path.relative_to(source_root).as_posix()
        parts = rel.split("/")
        asset, strategy_index, variant = parts[3], parts[4], parts[6]
        method = RULE_STRATEGY_METHODS.get(strategy_index)
        if method is None:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for paper_metric, (record_metric, scale) in RECORD_METRICS.items():
            paper_value = appendix[(f"{asset}/{method}", paper_metric)]
            record_value = float(payload[record_metric]) * scale
            decimals = len(paper_value.partition(".")[2])
            display_value = f"{record_value:.{decimals}f}"
            display_match = display_value == paper_value
            rows.append({
                "asset": asset,
                "method": method,
                "strategy_index": strategy_index,
                "variant": variant,
                "record_path": rel,
                "record_sha256": sha256(path),
                "paper_metric": paper_metric,
                "paper_value": paper_value,
                "released_record_value_at_paper_unit": record_value,
                "released_record_display_value": display_value,
                "display_precision_match": display_match,
                "absolute_difference": abs(float(paper_value) - record_value),
                "status": (
                    "display_precision_match_not_independent_regeneration"
                    if display_match
                    else "released_rule_record_does_not_match_appendix_table"
                ),
                "paper_result_credit": False,
            })
    if len(rows) != 288:
        raise RuntimeError(f"expected 288 rule-record/paper comparisons, got {len(rows)}")
    return rows


def source_history_rows(source_root: Path) -> list[dict[str, Any]]:
    commits = git(source_root, "rev-list", "--reverse", "--all").splitlines()
    rows: list[dict[str, Any]] = []
    output_suffixes = {".csv", ".tsv", ".json", ".jsonl", ".parquet", ".pkl", ".pickle", ".npy", ".npz", ".xlsx"}
    output_tokens = ("trajectory", "memory_record", "trading_record", "valid_record", "train_record", "action", "equity", "portfolio", "workdir")
    for commit in commits:
        paths = git(source_root, "ls-tree", "-r", "--name-only", commit).splitlines()
        first_party = [path for path in paths if not path.startswith("tools/echarts-5.4.3/")]
        strategy_records = [path for path in first_party if path.startswith("res/strategy_record/")]
        agent_outputs = [
            path for path in first_party
            if Path(path).suffix.lower() in output_suffixes
            and not path.startswith("res/strategy_record/")
            and any(token in path.lower() for token in output_tokens)
        ]
        metadata = git(source_root, "show", "-s", "--format=%aI%x00%s", commit).strip().split("\x00", 1)
        rows.append({
            "commit": commit,
            "commit_date": metadata[0],
            "subject": metadata[1],
            "tracked_files": len(paths),
            "first_party_files_excluding_vendored_echarts": len(first_party),
            "vendored_echarts_files": len(paths) - len(first_party),
            "strategy_record_files": len(strategy_records),
            "agent_output_paths": len(agent_outputs),
            "agent_output_path_list": ";".join(agent_outputs),
            "paper_result_credit": False,
        })
    if len(rows) != 7 or any(row["agent_output_paths"] for row in rows):
        raise RuntimeError("FinAgent reachable-history output boundary changed")
    return rows


def config_conformance_rows(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    config_paths = sorted((source_root / "configs/exp").rglob("*.py"))
    config_paths = [path for path in config_paths if "__pycache__" not in path.parts]
    for path in config_paths:
        text = path.read_text(encoding="utf-8")
        checks = {
            "asset": any(f'selected_asset = "{asset}"' in text for asset in ASSETS),
            "train_start": 'train_start_date = "2022-06-01"' in text,
            "train_end": 'train_end_date = "2023-06-01"' in text,
            "valid_start": 'valid_start_date = "2023-06-01"' in text,
            "valid_end": 'valid_end_date = "2024-01-01"' in text,
            "horizons_1_7_14": all(f"{term}_term_{direction}_date_range = {days}" in text
                                   for term, days in (("short", 1), ("medium", 7), ("long", 14))
                                   for direction in ("past", "next")),
            "top_k_5": "top_k = 5" in text,
            "market_model": 'model = "gpt-4-1106-preview"' in text,
            "reflection_model": 'model = "gpt-4-vision-preview"' in text,
        }
        schedule_fields = (
            "asset", "train_start", "train_end", "valid_start", "valid_end",
            "horizons_1_7_14", "top_k_5",
        )
        rows.append({
            "path": path.relative_to(source_root).as_posix(),
            **checks,
            "all_reported_core_fields_match": all(checks[key] for key in schedule_fields),
            "valid_environment_declared_mode": "train" if 'valid_environment = dict' in text else "missing",
        })
    if len(rows) != 42:
        raise RuntimeError(f"expected 42 experiment configs, got {len(rows)}")
    return rows


def source_reference_diagnostics(source_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((source_root / "configs").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for reference in re.findall(r'["\']((?:configs|res)/[^"\']+)["\']', text):
            target = source_root / reference
            if not target.exists():
                rows.append({
                    "config": path.relative_to(source_root).as_posix(),
                    "reference": reference,
                    "issue": (
                        "nonexistent_stock_list_directory" if "_stock_list_" in reference
                        else "missing_training_prompt_template"
                    ),
                })
    counts = Counter(row["issue"] for row in rows)
    if counts != {"nonexistent_stock_list_directory": 21, "missing_training_prompt_template": 60}:
        raise RuntimeError(f"source missing-reference census changed: {counts}")
    return rows


def processor_route_rows(source_root: Path) -> list[dict[str, Any]]:
    downloader_tags = set()
    for path in (source_root / "configs/downloader").rglob("*.py"):
        match = re.search(r'^tag\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            downloader_tags.add(match.group(1))
    rows = []
    for path in sorted((source_root / "configs/processor").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for route in re.findall(r'"path"\s*:\s*"workdir/([^"]+)"', text):
            rows.append({
                "processor_config": path.relative_to(source_root).as_posix(),
                "input_tag": route,
                "matching_downloader_tag": route in downloader_tags,
            })
    if sum(not row["matching_downloader_tag"] for row in rows) != 3:
        raise RuntimeError("processor/downloader route mismatch census changed")
    return rows


def static_python_rows(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(source_root.rglob("*.py")):
        if ".git" in path.parts:
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            status = "compiled"
            error = ""
        except Exception as exc:  # pragma: no cover - should fail the audit below
            status = "syntax_error"
            error = f"{type(exc).__name__}: {exc}"
        rows.append({"path": path.relative_to(source_root).as_posix(), "status": status, "error": error})
    if len(rows) != 142 or any(row["status"] != "compiled" for row in rows):
        raise RuntimeError("FinAgent static Python census/compilation changed")
    return rows


def metric_diagnostic_rows(source_root: Path) -> list[dict[str, Any]]:
    import numpy as np

    module_path = source_root / "finagent/metrics/metrics.py"
    spec = importlib.util.spec_from_file_location("released_finagent_metrics", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    returns = np.asarray([0.01, -0.02, 0.03, -0.01, 0.005], dtype=float)
    mean = float(np.mean(returns))
    std = float(np.std(returns))
    downside = float(np.std(returns[returns < 0]))
    mdd = float(module.MDD(returns))
    values = {
        "SR": (mean / std, float(module.SR(returns)), "source multiplies by sqrt(number_of_observations)"),
        "CR": (mean / mdd, float(module.CR(returns, mdd)), "source multiplies daily mean by 252"),
        "SOR": (mean / downside, float(module.SOR(returns, downside)), "source multiplies daily mean by 252"),
    }
    return [{
        "metric": metric,
        "paper_formula_value_on_probe": paper_value,
        "released_source_value_on_probe": source_value,
        "matches_paper_formula": abs(paper_value - source_value) < 1e-12,
        "diagnosis": diagnosis,
        "paper_result_credit": False,
    } for metric, (paper_value, source_value, diagnosis) in values.items()]


def mechanism_rows() -> list[dict[str, Any]]:
    specs = (
        ("provenance", "lead_author_homepage_links_repository", "source_verified", True),
        ("architecture", "multimodal_market_low_high_tool_decision_modules", "source_verified", True),
        ("architecture", "three_level_memory_and_diverse_retrieval", "source_verified", True),
        ("configuration", "six_reported_assets", "source_verified", True),
        ("configuration", "reported_train_validation_splits", "source_verified", True),
        ("configuration", "one_seven_fourteen_day_horizons", "source_verified", True),
        ("configuration", "top_k_five", "source_verified", True),
        ("configuration", "reported_openai_model_aliases", "source_verified_but_aliases_now_retired", True),
        ("prompts", "train_and_validation_prompt_families", "source_verified_with_missing_only_strategy_train_paths", True),
        ("ablations", "five_main_agent_config_families", "source_verified", True),
        ("baselines", "four_rule_strategy_implementations", "source_verified", True),
        ("portfolio", "stock_and_crypto_transaction_cost_settings", "source_verified_not_paper_disclosed", True),
        ("portfolio", "stock_and_crypto_initial_capital", "source_verified_not_paper_disclosed", True),
        ("validation", "chart_uses_only_information_available_by_decision_time", "conflict_future_14_days_rendered", False),
        ("portfolio", "paper_short_position_explanation", "conflict_release_is_long_only", False),
        ("tools", "optimized_strategy_parameters_drive_validation_signal", "conflict_signal_overwritten_by_default_parameters", False),
        ("baselines", "optuna_baseline_tuning", "missing_from_source", False),
        ("baselines", "lgbm_lstm_transformer_dqn_sac_ppo_training", "missing_from_source", False),
        ("metrics", "sharpe_formula", "conflict_source_adds_sqrt_n", False),
        ("metrics", "calmar_formula", "conflict_source_adds_252", False),
        ("metrics", "sortino_formula", "conflict_source_adds_252", False),
        ("data", "exact_immutable_dataset_snapshot", "not_released", False),
        ("data", "crypto_calendar", "conflict_eth_is_filtered_to_nyse_days", False),
        ("data", "download_and_processor_asset_list_routes", "broken_21_references_including_18_downloaders", False),
        ("data", "processor_downloader_routes", "broken_3_tag_mismatches", False),
        ("artifacts", "agent_memories_and_trajectories", "not_released", False),
        ("artifacts", "model_outputs_actions_and_equity_paths", "not_released", False),
        ("artifacts", "paper_result_tables_as_native_outputs", "not_released", False),
        ("reproducibility", "exact_dependency_environment", "not_released_at_paper_commit", False),
        ("reproducibility", "stochastic_llm_trials_and_variance", "not_reported_or_released", False),
        ("execution", "same_day_information_and_close_execution_timing", "under_specified", False),
    )
    return [{
        "area": area,
        "claim": claim,
        "status": status,
        "released_source_conformance_credit": credit,
        "paper_result_credit": False,
    } for area, claim, status, credit in specs]


def internal_check_rows() -> list[dict[str, Any]]:
    return [
        {"check": "baseline_count", "status": "internal_conflict", "detail": "prose says 9 baselines; Table 4 contains 12 comparators and the abstract says 12"},
        {"check": "figure4_vs_table4_methods", "status": "internal_conflict", "detail": "Figure 4 omits LGBM/LSTM/Transformer and adds SO&BB relative to Table 4"},
        {"check": "tsla_sr_improvement", "status": "internal_conflict", "detail": "prose/main figure claim 118%; Table 4 says 93.27% and Appendix Table 7 says 92.3217%"},
        {"check": "tsla_arr_improvement", "status": "rounding_consistent", "detail": "prose 84%; Table 4 84.39%; Appendix Table 7 84.4052%"},
        {"check": "table4_caption", "status": "caption_scope_conflict", "detail": "caption says six metrics while the active main table displays ARR, SR, and MDD only"},
        {"check": "paper_source_compile", "status": "reproduced_document", "detail": "arXiv v3 source compiles to 43 pages after two pdflatex passes"},
        {"check": "strategy_record_scope", "status": "not_paper_results", "detail": "90 JSON files are opaque rule-strategy training/default parameter records; all 288 comparable high-precision Appendix Table 7 cells mismatch"},
        {"check": "paper_vs_source_metrics", "status": "implementation_conflict", "detail": "released SR, CR, and SOR scale differently from the equations in the paper"},
    ]


def data_artifact_rows(source_root: Path) -> list[dict[str, Any]]:
    data_suffixes = {".csv", ".parquet", ".pkl", ".pickle", ".feather"}
    checkpoint_suffixes = {".pt", ".pth", ".ckpt", ".bin", ".safetensors"}
    output_suffixes = data_suffixes | {".json", ".jsonl"}
    files = [
        path for path in source_root.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    ]
    found_by_kind = {
        "market_dataset": [path for path in files if path.suffix.lower() in data_suffixes],
        "model_checkpoint": [path for path in files if path.suffix.lower() in checkpoint_suffixes],
        "agent_output": [
            path for path in files
            if path.suffix.lower() in output_suffixes
            and any(token in path.name.lower() for token in ("trajectory", "memory", "action", "equity"))
        ],
    }
    rows = []
    for kind, paths in found_by_kind.items():
        found = sorted({path.relative_to(source_root).as_posix() for path in paths})
        rows.append({
            "artifact_kind": kind,
            "released_count": len(found),
            "released_paths": ";".join(found),
            "sufficient_for_paper_result_reproduction": False,
        })
    return rows


def validate_primary_inputs(source_root: Path, paper_root: Path) -> None:
    expected_files = {
        "paper_v3.pdf": ARXIV_V3_PDF_SHA256,
        "source_v3.tar": ARXIV_V3_SOURCE_SHA256,
        "KDD24_FinAgent.pdf": KDD_PDF_SHA256,
    }
    for name, expected in expected_files.items():
        path = paper_root / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"primary paper input mismatch: {name}")
    if git(source_root, "rev-parse", "HEAD").strip() != SOURCE_CURRENT_COMMIT:
        raise ValueError("released source HEAD mismatch")
    if git(source_root, "rev-parse", f"{SOURCE_PAPER_COMMIT}^{{tree}}").strip() != SOURCE_PAPER_TREE:
        raise ValueError("paper-era source tree mismatch")
    if git(source_root, "rev-parse", f"{SOURCE_CURRENT_COMMIT}^{{tree}}").strip() != SOURCE_CURRENT_TREE:
        raise ValueError("current source tree mismatch")
    if git_archive_sha256(source_root, SOURCE_PAPER_COMMIT) != SOURCE_PAPER_ARCHIVE_SHA256:
        raise ValueError("paper-era source archive mismatch")
    if git_archive_sha256(source_root, SOURCE_CURRENT_COMMIT) != SOURCE_CURRENT_ARCHIVE_SHA256:
        raise ValueError("current source archive mismatch")
    changed = git(source_root, "diff", "--name-only", SOURCE_PAPER_COMMIT, SOURCE_CURRENT_COMMIT).splitlines()
    if changed != ["requirements.txt"]:
        raise ValueError(f"unexpected post-paper source changes: {changed}")


def compile_paper_source(paper_root: Path, latex_command: str) -> dict[str, Any]:
    if not latex_command or shutil.which(latex_command) is None:
        return {
            "attempted": False, "reason": "latex_command_unavailable",
            "paper_result_credit": False,
        }
    with tempfile.TemporaryDirectory(prefix="finagent-paper-") as temp:
        temp_root = Path(temp)
        with tarfile.open(paper_root / "source_v3.tar") as archive:
            archive.extractall(temp_root)
        passes = []
        for _ in range(2):
            proc = subprocess.run(
                [latex_command, "-interaction=nonstopmode", "main.tex"],
                cwd=temp_root, capture_output=True, text=True, timeout=180,
            )
            passes.append({"exit_code": proc.returncode, "log_tail": proc.stdout[-2000:]})
            if proc.returncode != 0:
                break
        pdf = temp_root / "main.pdf"
        page_count = None
        if pdf.is_file() and shutil.which("pdfinfo"):
            info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
            match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
            page_count = int(match.group(1)) if match else None
        return {
            "attempted": True,
            "passes": passes,
            "exit_code": passes[-1]["exit_code"],
            "compiled_pdf_sha256": sha256(pdf) if pdf.is_file() else None,
            "compiled_pages": page_count,
            "matches_arxiv_page_count": page_count == 43,
            "paper_result_credit": False,
        }


def native_execution(source_root: Path, paper_root: Path, latex_command: str) -> dict[str, Any]:
    cli = subprocess.run(
        [sys.executable, str(source_root / "tools/main.py"), "--help"],
        cwd=source_root, capture_output=True, text=True, timeout=60,
    )
    requirements_at_paper_commit = git(
        source_root, "ls-tree", "-r", "--name-only", SOURCE_PAPER_COMMIT,
    ).splitlines()
    return {
        "paper_source_compilation": compile_paper_source(paper_root, latex_command),
        "released_python_static_compilation": {"files": 142, "syntax_errors": 0},
        "entrypoint_help_probe": {
            "attempted": True,
            "exit_code": cli.returncode,
            "stderr_tail": cli.stderr[-1500:],
            "interpretation": "audit environment dependency probe only; the exact paper commit shipped no dependency specification",
        },
        "paper_commit_has_requirements_file": "requirements.txt" in requirements_at_paper_commit,
        "full_native_system_execution_attempted": False,
        "full_native_system_execution_reason": (
            "exact input snapshot, API credentials, memories, trajectories, output records, and operational preview models are unavailable"
        ),
        "published_result_units_reproduced": 0,
        "paper_result_credit": False,
    }


def render_readme(manifest: Mapping[str, Any]) -> str:
    return f"""# FinAgent paper replication audit

This is a fail-closed audit of the original KDD 2024 paper, its arXiv v3
source, and the repository linked by the lead author's homepage.  The release
is substantial—{manifest['released_python_files']} Python files, prompts,
configs, agent modules, and rule-strategy records—but it is not an executable
experimental package for the published claims.

## Honest outcome

- Paper document: reproduced from pinned source at 43 pages.
- Static released-source mechanisms matching the paper: {manifest['released_source_mechanisms_verified']} of {manifest['paper_mechanisms_audited']} audited claims.
- Published result units: **0 of {manifest['published_result_display_units_total']} reproduced** ({manifest['paper_numeric_display_cells_total']} table cells and {manifest['paper_figure_display_units_total']} figure units).
- Overall tier: **R2 / substantial static implementation evidence, no paper-result reproduction**.

No paper-result credit is assigned to values transcribed from LaTeX, plot-only
graphics, rule-strategy parameter records, static compilation, or document
compilation.  The repository contains no exact dataset snapshot, FinAgent
memories, trajectories, action/equity paths, checkpoints, or native result
tables.  All {manifest['reachable_source_history_commits']} reachable commits
were checked and none contains an agent-output path.  The 90 shipped rule
records yield {manifest['released_strategy_record_appendix_comparisons']}
default/trained comparisons against the corresponding high-precision Appendix
Table 7 cells, with {manifest['released_strategy_record_appendix_display_matches']}
display-precision matches; no released code path writes those opaque `best_*`
records.

## Material protocol conflicts

The full validation runner renders the k-line chart with the plotting default
`mode="train"`, while state construction includes 14 future days.  This
exposes future prices to the vision reflection path despite the paper's
no-lookahead claim.  The environment is long-only despite the paper's TSLA
short-position explanation.  Optimized rule parameters are loaded and then
their signals are overwritten by a default-parameter call.  OPTUNA and six
ML/RL baselines are absent.  Released SR/CR/SOR code disagrees with the paper's
equations.  Twenty-one asset-list references (including all eighteen downloader
references), sixty training-prompt references,
and three processor/downloader routes are broken.

The detailed CSVs and `native_execution.json` are the evidence ledger.  A
modern substitute model or reconstructed dataset would be an adaptation, not
an exact reproduction, and must remain labeled accordingly.
"""


def audit(source_root: Path, paper_root: Path, output: Path, latex_command: str) -> dict[str, Any]:
    validate_primary_inputs(source_root, paper_root)
    paper_source_root = paper_root / "source_v3"
    output.mkdir(parents=True, exist_ok=True)

    tables = paper_table_rows(paper_source_root)
    figures = paper_figure_rows(paper_source_root)
    inventory = source_inventory(source_root)
    strategies = strategy_record_rows(source_root)
    strategy_conformance = strategy_record_paper_conformance_rows(source_root, tables)
    history = source_history_rows(source_root)
    configs = config_conformance_rows(source_root)
    references = source_reference_diagnostics(source_root)
    routes = processor_route_rows(source_root)
    python_rows = static_python_rows(source_root)
    metrics = metric_diagnostic_rows(source_root)
    mechanisms = mechanism_rows()
    internal = internal_check_rows()
    artifacts = data_artifact_rows(source_root)
    native = native_execution(source_root, paper_root, latex_command)

    csv_outputs = {
        "paper_numeric_table_conformance.csv": tables,
        "paper_figure_display_inventory.csv": figures,
        "released_source_inventory.csv": inventory,
        "released_strategy_record_inventory.csv": strategies,
        "released_strategy_record_paper_conformance.csv": strategy_conformance,
        "released_source_history_inventory.csv": history,
        "released_config_conformance.csv": configs,
        "released_missing_reference_diagnostics.csv": references,
        "released_processor_route_diagnostics.csv": routes,
        "released_python_static_compilation.csv": python_rows,
        "paper_source_metric_formula_diagnostics.csv": metrics,
        "paper_mechanism_conformance.csv": mechanisms,
        "paper_internal_consistency_checks.csv": internal,
        "released_data_artifact_inventory.csv": artifacts,
    }
    for filename, rows in csv_outputs.items():
        write_csv(output / filename, rows)
    (output / "native_execution.json").write_text(
        json.dumps(native, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )

    manifest: dict[str, Any] = {
        "audit_date": AUDIT_DATE,
        "paper": "A Multimodal Foundation Agent for Financial Trading: Tool-Augmented, Diversified, and Generalist",
        "arxiv_url": ARXIV_URL,
        "arxiv_v3_date": ARXIV_V3_DATE,
        "doi": DOI,
        "kdd_pdf_url": KDD_PDF_URL,
        "author_homepage": AUTHOR_HOMEPAGE,
        "source_url": SOURCE_URL,
        "source_provenance": "repository_linked_from_lead_author_homepage",
        "source_paper_commit": SOURCE_PAPER_COMMIT,
        "source_current_commit": SOURCE_CURRENT_COMMIT,
        "source_change_after_paper_commit": "requirements.txt_only",
        "overall_status": "substantial_author_linked_source_but_zero_of_1061_published_result_units_reproduced",
        "replication_tier": "R2_substantial_static_implementation_no_paper_result_reproduction",
        "full_paper_reproduced": False,
        "paper_document_reproduced": bool(native["paper_source_compilation"].get("matches_arxiv_page_count")),
        "paper_numeric_display_cells_total": len(tables),
        "paper_numeric_display_cells_with_paper_result_credit": sum(row["paper_result_credit"] for row in tables),
        "paper_figure_display_units_total": len(figures),
        "paper_figure_display_units_with_paper_result_credit": sum(row["paper_result_credit"] for row in figures),
        "published_result_display_units_total": len(tables) + len(figures),
        "published_result_display_units_reproduced": 0,
        "paper_mechanisms_audited": len(mechanisms),
        "released_source_mechanisms_verified": sum(row["released_source_conformance_credit"] for row in mechanisms),
        "released_source_files_at_paper_commit": len(inventory),
        "released_python_files": sum(row["kind"] == "python_source" for row in inventory),
        "released_strategy_record_files": len(strategies),
        "released_strategy_best_params_nonempty": sum(row["record_kind"] == "best_params" and row["nonempty"] for row in strategies),
        "released_strategy_record_appendix_comparisons": len(strategy_conformance),
        "released_strategy_record_appendix_display_matches": sum(row["display_precision_match"] for row in strategy_conformance),
        "reachable_source_history_commits": len(history),
        "reachable_source_history_commits_with_agent_output_paths": sum(bool(row["agent_output_paths"]) for row in history),
        "reachable_source_history_first_party_path_sets_identical_before_requirements_only_commit": len({row["first_party_files_excluding_vendored_echarts"] for row in history[:-1]}) == 1,
        "released_experiment_configs": len(configs),
        "released_missing_references": len(references),
        "metric_formula_conflicts": sum(not row["matches_paper_formula"] for row in metrics),
        "exact_dataset_released": False,
        "agent_result_records_released": False,
        "paper_result_credit": False,
    }
    (output / "README.md").write_text(render_readme(manifest), encoding="utf-8")
    output_names = [*csv_outputs, "native_execution.json", "README.md"]
    manifest["output_sha256"] = {name: sha256(output / name) for name in sorted(output_names)}
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--latex-command", default="pdflatex")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = audit(args.source_root, args.paper_root, args.output, args.latex_command)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
