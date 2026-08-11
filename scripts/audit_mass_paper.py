#!/usr/bin/env python3
"""Audit MASS paper Tables 1--4 against its pinned public release.

The audit inventories the released market panel and safely decodes the pinned
agent-distribution snapshot after enforcing a narrow pickle-opcode allowlist.
It never calls an LLM endpoint and never treats internal optimizer state as a
published signal, portfolio, cost measurement, or result reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import pickle
import pickletools
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pandas as pd


SOURCE_COMMIT = "68edcaae9e6ac099d28eed90513219495b0852b7"
PAPER_SHA256 = "c31e68b722b6c4d33dd69833b48a34de8fc29ec4171498f320307ede554e6135"
PAPER_URL = "https://arxiv.org/pdf/2505.10278"
SOURCE_URL = "https://github.com/gta0804/MASS"
SNAPSHOT_SHA256 = "be7d40a8f0191bb6ee246b3a8537851b088be685afb52b51d823dde587f1a895"

TABLE_1_METRICS = ("rank_ic_pct", "rank_icir_pct", "ic_pct", "icir_pct")
TABLE_2_METRICS = TABLE_1_METRICS
TABLE_3_METRICS = ("average_daily_time_seconds", "average_daily_api_cost_usd")
TABLE_4_METRICS = ("annualized_return_pct", "sharpe_ratio", "max_drawdown_pct")


# Transcribed from Tables 1--4 of the pinned official PDF. Each line is
# section|pool|method|the metrics for that table in the order declared above.
TABLE_1_TEXT = """
main_2023|SSE50|proxy_indicator|3.82|19.73|2.89|16.63
main_2023|CSI_300|proxy_indicator|3.84|30.44|3.60|27.03
main_2023|ChiNext_100|proxy_indicator|-0.94|-7.05|0.16|1.29
main_2023|SSE50|lightgbm|3.25|21.78|4.51|27.30
main_2023|CSI_300|lightgbm|5.20|36.06|3.19|23.62
main_2023|ChiNext_100|lightgbm|2.94|30.69|0.88|8.70
main_2023|SSE50|dtml|5.04|28.15|4.93|26.71
main_2023|CSI_300|dtml|4.91|35.72|4.17|31.10
main_2023|ChiNext_100|dtml|3.45|26.55|3.21|21.97
main_2023|SSE50|master|5.13|28.37|4.97|27.01
main_2023|CSI_300|master|5.01|35.47|4.23|30.78
main_2023|ChiNext_100|master|3.92|31.03|4.07|28.62
main_2023|SSE50|sep|4.79|27.56|4.16|26.40
main_2023|CSI_300|sep|3.83|5.42|0.61|7.65
main_2023|ChiNext_100|sep|4.81|34.88|5.29|36.98
main_2023|SSE50|fincon|4.88|26.18|4.35|25.67
main_2023|CSI_300|fincon|0.70|9.57|0.96|13.42
main_2023|ChiNext_100|fincon|5.01|37.18|5.53|40.54
main_2023|SSE50|tradingagents|4.92|27.71|4.33|25.69
main_2023|CSI_300|tradingagents|3.01|10.14|1.02|14.80
main_2023|ChiNext_100|tradingagents|5.37|38.15|5.60|41.06
main_2023|SSE50|mass|8.16|41.74|5.90|33.43
main_2023|CSI_300|mass|6.50|43.49|4.65|33.32
main_2023|ChiNext_100|mass|7.62|62.87|6.28|55.88
leakage_2025_q1|SSE50|mass|4.50|24.41|6.12|38.33
leakage_2025_q1|CSI_300|mass|3.91|37.44|3.36|34.56
leakage_2025_q1|CSI_A500|mass|5.19|56.17|4.66|48.82
"""

TABLE_2_TEXT = """
ablation_2023|SSE50|without_csp|1.65|11.19|1.67|11.73
ablation_2023|CSI_300|without_csp|EMCL|EMCL|EMCL|EMCL
ablation_2023|ChiNext_100|without_csp|EMCL|EMCL|EMCL|EMCL
ablation_2023|SSE50|without_pmd|5.25|29.75|3.43|21.10
ablation_2023|CSI_300|without_pmd|2.57|33.38|2.23|30.64
ablation_2023|ChiNext_100|without_pmd|2.26|17.16|2.99|22.70
ablation_2023|SSE50|without_bo|0.76|4.75|-0.13|-8.44
ablation_2023|CSI_300|without_bo|0.36|5.36|0.41|6.69
ablation_2023|ChiNext_100|without_bo|2.88|19.43|3.12|22.03
ablation_2023|SSE50|without_mdh|6.28|32.68|3.85|25.39
ablation_2023|CSI_300|without_mdh|4.65|31.03|2.98|27.86
ablation_2023|ChiNext_100|without_mdh|-3.12|-28.93|-2.46|-26.44
ablation_2023|SSE50|mass_daily_updated_pool|8.03|41.68|5.79|33.52
ablation_2023|CSI_300|mass_daily_updated_pool|6.48|42.86|4.52|32.95
ablation_2023|ChiNext_100|mass_daily_updated_pool|7.65|63.02|6.29|55.91
ablation_2023|SSE50|mass|8.16|41.74|5.90|33.43
ablation_2023|CSI_300|mass|6.50|43.49|4.65|33.32
ablation_2023|ChiNext_100|mass|7.62|62.87|6.28|55.88
"""

TABLE_3_TEXT = """
cost_512_agents|SSE50|mass|125|0.679
cost_512_agents|CSI_300|mass|378|2.265
cost_512_agents|ChiNext_100|mass|227|1.192
"""

TABLE_4_TEXT = """
main_2023|SSE50|proxy_indicator|-2.39|-1.22|14.04
main_2023|CSI_300|proxy_indicator|-3.60|-1.62|20.57
main_2023|ChiNext_100|proxy_indicator|-20.01|-3.24|24.15
main_2023|SSE50|lightgbm|-1.88|-1.14|13.16
main_2023|CSI_300|lightgbm|-4.55|-2.12|18.57
main_2023|ChiNext_100|lightgbm|-19.32|-3.01|23.96
main_2023|SSE50|dtml|-1.69|-1.08|12.99
main_2023|CSI_300|dtml|-0.33|-0.14|22.34
main_2023|ChiNext_100|dtml|-8.23|-3.20|24.55
main_2023|SSE50|master|-1.67|-0.92|12.91
main_2023|CSI_300|master|0.79|0.33|22.05
main_2023|ChiNext_100|master|-7.88|-3.17|24.06
main_2023|SSE50|sep|-2.01|-1.07|13.12
main_2023|CSI_300|sep|-10.24|-4.32|22.67
main_2023|ChiNext_100|sep|-6.84|-3.14|24.01
main_2023|SSE50|fincon|-1.82|-0.98|13.05
main_2023|CSI_300|fincon|-9.25|-3.28|23.74
main_2023|ChiNext_100|fincon|-6.01|-2.80|23.75
main_2023|SSE50|tradingagents|-2.44|-1.71|13.15
main_2023|CSI_300|tradingagents|-7.19|-3.02|19.61
main_2023|ChiNext_100|tradingagents|-4.65|-2.82|23.84
main_2023|SSE50|mass|2.16|1.98|11.98
main_2023|CSI_300|mass|4.95|2.23|14.04
main_2023|ChiNext_100|mass|1.17|0.99|19.06
main_2023|SSE50|stock_pool_index|-9.98|-2.37|21.62
main_2023|CSI_300|stock_pool_index|-9.75|-2.92|21.44
main_2023|ChiNext_100|stock_pool_index|-19.18|-3.17|32.26
leakage_2025_q1|SSE50|mass|9.74|2.42|2.91
leakage_2025_q1|CSI_300|mass|9.36|2.66|2.99
leakage_2025_q1|CSI_A500|mass|11.34|2.93|4.08
leakage_2025_q1|SSE50|stock_pool_index|-1.88|-2.97|5.63
leakage_2025_q1|CSI_300|stock_pool_index|-3.88|-3.15|5.86
leakage_2025_q1|CSI_A500|stock_pool_index|-1.28|-3.26|6.04
"""


PINNED_SOURCE_SHA256 = {
    "README.md": "1b036a4dd5cfd87b24335609f11ba0a9a61ac49f53eb5578f57fe49d57f2bc5e",
    "ih_dist": SNAPSHOT_SHA256,
    "pdm.lock": "2c675b29b7b7ffaeba3f7bd52199ba6f1f71035a5172ef6e43c5e10cee25f838",
    "pyproject.toml": "45a6bffa2005a4728554cecc0ea096fb17f2801fc7eeaf82a63083d891243ac2",
    "stock_disagreement/agent/agent_distribution.py": "b53a2af0c97054e9db7be0aaaea2b41fbbd5a94f3fe2f62c5dd8d5397690c87c",
    "stock_disagreement/agent/basic_agent.py": "c9dd13fa10e040f85be843af07403e9d46e53ba9fed028ee32a51473cfff4c2b",
    "stock_disagreement/agent/investment_analyzer.py": "394daf70b5ac6bd965555ed66d0fd4fdd65502645c63408c300f8e666ee547d4",
    "stock_disagreement/agent/stock_selector.py": "ee58ea681a86e3d29f0cc6d7c101002618c3629b75d540881d0da330dc2f6fdc",
    "stock_disagreement/exp/trainer.py": "534845b4033cb3851a0442573b8319914d7ec0462e7882ba54c4ab900eda2033",
    "stock_disagreement/main.py": "c9f5984002d0de6a1c856bee88df0723a1a91f0806d630454b37dba19a74d6de",
    "stock_disagreement/utils/llm.py": "1f284173e84a99321ea70088a0deb93da98cdbf9b201959ea12f622d778a6069",
}


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


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_table(
    table: int,
    text: str,
    metrics: Sequence[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in text.strip().splitlines():
        values = line.split("|")
        if len(values) != 3 + len(metrics):
            raise ValueError(f"Malformed Table {table} row: {line}")
        section, pool, method = values[:3]
        for metric, value in zip(metrics, values[3:]):
            numeric = value != "EMCL"
            rows.append(
                {
                    "paper_table": table,
                    "section": section,
                    "stock_pool": pool,
                    "method": method,
                    "metric": metric,
                    "paper_value": float(value) if numeric else value,
                    "paper_value_is_numeric": numeric,
                }
            )
    return rows


def paper_result_rows() -> List[Dict[str, Any]]:
    return [
        *parse_table(1, TABLE_1_TEXT, TABLE_1_METRICS),
        *parse_table(2, TABLE_2_TEXT, TABLE_2_METRICS),
        *parse_table(3, TABLE_3_TEXT, TABLE_3_METRICS),
        *parse_table(4, TABLE_4_TEXT, TABLE_4_METRICS),
    ]


def result_conformance() -> List[Dict[str, Any]]:
    rows = []
    for target in paper_result_rows():
        if target["paper_value_is_numeric"]:
            status = "unverifiable_no_shipped_native_signal_or_result_path"
            evidence = (
                "paper_value_only; release has no agent-decision cache, signal path, "
                "baseline output, backtest path, cost log, or result table"
            )
        else:
            status = "paper_non_numeric_emcl"
            evidence = "paper reports maximum-context-length failure rather than a numeric result"
        rows.append(
            {
                **target,
                "source_recomputed_value": "",
                "status": status,
                "evidence": evidence,
            }
        )
    return rows


SAFE_PICKLE_OPCODES = {
    "PROTO",
    "FRAME",
    "EMPTY_DICT",
    "MEMOIZE",
    "MARK",
    "BININT",
    "BININT1",
    "BININT2",
    "SHORT_BINUNICODE",
    "STACK_GLOBAL",
    "TUPLE1",
    "REDUCE",
    "BINFLOAT",
    "BINGET",
    "SETITEMS",
    "STOP",
}


class DistributionSnapshotUnpickler(pickle.Unpickler):
    """Allow only the pinned Modality enum constructor, mapped to plain int."""

    def find_class(self, module: str, name: str) -> Any:
        if (module, name) == ("stock_disagreement.agent.basic_agent", "Modality"):
            return int
        raise pickle.UnpicklingError(f"forbidden global: {module}.{name}")


def safe_distribution_snapshot(path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_SHA256:
        raise RuntimeError("MASS ih_dist hash changed")
    opcodes = list(pickletools.genops(raw))
    observed = {opcode.name for opcode, _, _ in opcodes}
    unexpected = observed - SAFE_PICKLE_OPCODES
    if unexpected:
        raise RuntimeError(f"MASS ih_dist contains forbidden pickle opcodes: {sorted(unexpected)}")
    if Counter(opcode.name for opcode, _, _ in opcodes)["STACK_GLOBAL"] != 1:
        raise RuntimeError("MASS ih_dist global-constructor count changed")

    data = DistributionSnapshotUnpickler(io.BytesIO(raw)).load()
    if not isinstance(data, dict):
        raise RuntimeError("MASS ih_dist is not a date-keyed dictionary")
    rows = []
    previous: Tuple[Tuple[int, float], ...] | None = None
    for date in sorted(data):
        distribution = data[date]
        if not isinstance(date, int) or not isinstance(distribution, dict):
            raise RuntimeError("MASS ih_dist contains a non-primitive date/distribution")
        if not all(isinstance(key, int) and isinstance(value, float) for key, value in distribution.items()):
            raise RuntimeError("MASS ih_dist contains a non-primitive distribution entry")
        fingerprint = tuple(sorted(distribution.items()))
        raw_sum = math.fsum(distribution.values())
        rows.append(
            {
                "date": date,
                "investor_type_masks": len(distribution),
                "raw_weight_sum": raw_sum,
                "normalized_weight_sum": math.fsum(value / raw_sum for value in distribution.values()),
                "minimum_raw_weight": min(distribution.values()),
                "maximum_raw_weight": max(distribution.values()),
                "changed_from_previous_trading_date": previous is not None and fingerprint != previous,
                "interpretation": "native dated optimizer state; not an agent decision, signal, or return",
            }
        )
        previous = fingerprint
    summary = {
        "pickle_opcodes_total": len(opcodes),
        "pickle_opcode_names": sorted(observed),
        "pickle_global_policy": ["stock_disagreement.agent.basic_agent.Modality mapped to built-in int"],
        "dates": len(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "investor_type_masks_per_date": sorted({row["investor_type_masks"] for row in rows}),
        "changed_transitions": sum(row["changed_from_previous_trading_date"] for row in rows),
        "raw_weight_sum_min": min(row["raw_weight_sum"] for row in rows),
        "raw_weight_sum_max": max(row["raw_weight_sum"] for row in rows),
        "all_weights_positive": all(row["minimum_raw_weight"] > 0 for row in rows),
        "safe_decode_boundary": (
            "pinned hash plus opcode allowlist; sole Modality constructor mapped to built-in int; "
            "all decoded keys and values validated as primitive int/float"
        ),
    }
    if (
        summary["dates"] != 263
        or summary["first_date"] != 20221202
        or summary["last_date"] != 20231229
        or summary["investor_type_masks_per_date"] != [16]
        or summary["changed_transitions"] != 216
        or not summary["all_weights_positive"]
    ):
        raise RuntimeError(f"Pinned MASS distribution snapshot findings changed: {summary}")
    return rows, summary


DATASET_FILES = (
    "stock_disagreement/dataset/base_data.parq",
    "stock_disagreement/dataset/ih_label.parq",
    "stock_disagreement/dataset/sub_fudamental_data.parq",
    "stock_disagreement/dataset/industry_ret.parq",
    "stock_disagreement/dataset/stock_basic_data.parq",
    "stock_disagreement/dataset/financial-news-info.parq",
    "stock_disagreement/dataset/financial-news-relationship.parq",
    "stock_disagreement/dataset/macro_data/China_1-Year_Loan_Prime_Rate_LPR.csv",
    "stock_disagreement/dataset/macro_data/China_CPI_YoY_Current_Month.csv",
    "stock_disagreement/dataset/macro_data/Market_Sentiment_Index.csv",
    "stock_disagreement/dataset/macro_data/csi_300_pe_ttm.csv",
    "stock_disagreement/dataset/macro_data/yield_on_China_10_year_government_bonds.csv",
)


def dataset_inventory(source_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows = []
    for relative in DATASET_FILES:
        path = source_root / relative
        record: Dict[str, Any] = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "format_status": "",
            "rows": "",
            "columns": "",
            "minimum_date": "",
            "maximum_date": "",
            "distinct_dates": "",
            "distinct_stocks": "",
        }
        try:
            frame = pd.read_parquet(path) if path.suffix == ".parq" else pd.read_csv(path)
            record["format_status"] = "readable"
            record["rows"] = len(frame)
            record["columns"] = ";".join(map(str, frame.columns))
            if "Date" in frame:
                record["minimum_date"] = str(frame["Date"].min())
                record["maximum_date"] = str(frame["Date"].max())
                record["distinct_dates"] = int(frame["Date"].nunique())
            if "Stock" in frame:
                record["distinct_stocks"] = int(frame["Stock"].nunique())
        except Exception as error:
            record["format_status"] = f"unreadable_{type(error).__name__}"
        rows.append(record)

    base = pd.read_parquet(source_root / "stock_disagreement/dataset/base_data.parq")
    labels = pd.read_parquet(source_root / "stock_disagreement/dataset/ih_label.parq")
    features = pd.read_parquet(source_root / "stock_disagreement/dataset/sub_fudamental_data.parq")
    base_2023 = base[base["Date"].between(20230101, 20231231)]
    label_2023 = labels[labels["Date"].between(20230101, 20231231)]
    feature_2023 = features[features["Date"].between(20230101, 20231231)]
    daily_counts = base_2023.groupby("Date")["Stock"].nunique()
    summary = {
        "released_2023_sse_like_trading_dates": int(base_2023["Date"].nunique()),
        "released_2023_sse_like_distinct_stocks_across_year": int(base_2023["Stock"].nunique()),
        "released_2023_cross_section_size_min": int(daily_counts.min()),
        "released_2023_cross_section_size_max": int(daily_counts.max()),
        "base_label_key_rows_equal": len(base_2023) == len(label_2023),
        "base_feature_key_rows_equal": len(base_2023) == len(feature_2023),
        "paper_stock_pools": ["SSE50", "CSI_300", "ChiNext_100", "CSI_A500"],
        "released_stock_pool_panels": ["SSE50_like_only"],
        "invalid_news_placeholders": 2,
        "invalid_news_placeholder_bytes_each": 2,
    }
    if summary != {
        "released_2023_sse_like_trading_dates": 242,
        "released_2023_sse_like_distinct_stocks_across_year": 59,
        "released_2023_cross_section_size_min": 50,
        "released_2023_cross_section_size_max": 50,
        "base_label_key_rows_equal": True,
        "base_feature_key_rows_equal": True,
        "paper_stock_pools": ["SSE50", "CSI_300", "ChiNext_100", "CSI_A500"],
        "released_stock_pool_panels": ["SSE50_like_only"],
        "invalid_news_placeholders": 2,
        "invalid_news_placeholder_bytes_each": 2,
    }:
        raise RuntimeError(f"Pinned MASS dataset findings changed: {summary}")
    return rows, summary


def source_config_audit(source_root: Path) -> List[Dict[str, str]]:
    main = (source_root / "stock_disagreement/main.py").read_text(encoding="utf-8")
    trainer = (source_root / "stock_disagreement/exp/trainer.py").read_text(encoding="utf-8")
    agent = (source_root / "stock_disagreement/agent/basic_agent.py").read_text(encoding="utf-8")
    optimizer = (source_root / "stock_disagreement/agent/agent_distribution.py").read_text(encoding="utf-8")
    selector = (source_root / "stock_disagreement/agent/stock_selector.py").read_text(encoding="utf-8")
    pyproject = (source_root / "pyproject.toml").read_text(encoding="utf-8")

    findings = {
        "model": 'model_name: str = "Qwen2.5-72B-Instruct"' in agent,
        "types": '"--num_investor_type", type=int, default= 16' in main,
        "agents_per_type": '"--num_agents_per_investor", type=int, default= 32' in main,
        "source_alpha": "alpha:float = 0.5" in optimizer
        or "alpha:float = 0.5"
        in (source_root / "stock_disagreement/agent/investment_analyzer.py").read_text(encoding="utf-8"),
        "alpha_not_forwarded": "alpha=" not in trainer,
        "source_sa_temperature": "init_temp: float = 0.5" in optimizer,
        "source_sa_iterations": "max_iter:int = 20" in optimizer,
        "source_cooling": "cooling_rate: float = 0.95" in optimizer,
        "daily_candidate_sampling": "random.choices" in selector and "date=date" in agent,
        "daily_strategy_generation": "self.generate_strategy_and_stock_selector(date)" in agent,
        "missing_f_string_paths": 'pd.read_parquet("{ROOT_PATH}/' in main,
        "empty_root_path_count": sum(text.count('ROOT_PATH = ""') for text in (main, trainer, agent)) == 3,
        "undeclared_pandas": re.search(r'"pandas(?:[<=>]|\")', pyproject) is None,
        "undeclared_numpy": re.search(r'"numpy(?:[<=>]|\")', pyproject) is None,
        "undeclared_scipy": re.search(r'"scipy(?:[<=>]|\")', pyproject) is None,
    }
    if not all(findings.values()):
        raise RuntimeError(f"Pinned MASS source findings changed: {findings}")

    return [
        {
            "dimension": "foundation_model",
            "paper": "Qwen2.5-72B-Instruct",
            "released": "Qwen2.5-72B-Instruct",
            "status": "match",
        },
        {
            "dimension": "main_agent_scale",
            "paper": "16 types x 32 agents = 512",
            "released": "CLI defaults 16 x 32",
            "status": "match",
        },
        {
            "dimension": "sse50_candidate_pool_size",
            "paper": "20",
            "released": "CLI default stock_num=20",
            "status": "match",
        },
        {
            "dimension": "csi300_candidate_pool_size",
            "paper": "30",
            "released": "supported only by manual --stock_num override; no experiment command/config",
            "status": "not_pinned",
        },
        {"dimension": "score_alpha_sse50_csi300", "paper": "0.5", "released": "0.5 default", "status": "match"},
        {
            "dimension": "score_alpha_chinext100",
            "paper": "0.2",
            "released": "0.5 hard default; trainer never forwards a pool-specific alpha",
            "status": "mismatch",
        },
        {"dimension": "sa_initial_temperature", "paper": "40", "released": "0.5 active default", "status": "mismatch"},
        {"dimension": "sa_max_iterations", "paper": "100", "released": "20 active default", "status": "mismatch"},
        {"dimension": "sa_cooling_rate", "paper": "0.95", "released": "0.95", "status": "match"},
        {"dimension": "optimizer_lookback", "paper": "5", "released": "CLI default 5", "status": "match"},
        {
            "dimension": "main_candidate_pool_update",
            "paper": "static per agent; daily update is separate MASS(DU) ablation",
            "released": "resampled daily with random.choices (with replacement)",
            "status": "mismatch",
        },
        {
            "dimension": "daily_type_strategy",
            "paper": "one daily strategy per investor type",
            "released": "each agent generates its own strategy on every trading day",
            "status": "mismatch",
        },
        {
            "dimension": "randomness_control",
            "paper": "no seed protocol disclosed",
            "released": "Python and NumPy RNG used without a run-level seed",
            "status": "missing",
        },
        {
            "dimension": "paper_stock_pool_inputs",
            "paper": "SSE50, CSI 300, ChiNext 100; plus CSI A500 in 2025",
            "released": "SSE50-like base/label/feature panel only",
            "status": "incomplete",
        },
        {
            "dimension": "paper_news_inputs",
            "paper": "financial news for the released multimodal panel",
            "released": "two 2-byte invalid Parquet placeholders under different filenames",
            "status": "missing",
        },
        {
            "dimension": "native_entrypoint_paths",
            "paper": "runnable experiment",
            "released": "three empty ROOT_PATH constants, two literal non-f-string paths, and required filenames absent",
            "status": "not_operational",
        },
        {
            "dimension": "direct_runtime_dependencies",
            "paper": "runnable environment",
            "released": "pandas, numpy, and scipy imported but not direct project dependencies",
            "status": "incomplete",
        },
        {
            "dimension": "metric_horizon",
            "paper": "one Table 1 result set; return horizon not identified",
            "released": "prints separate 1-, 5-, and 10-day label metrics",
            "status": "paper_underspecified",
        },
        {
            "dimension": "portfolio_backtest",
            "paper": "weekly top-20%, 0.1% round-trip cost, Tables 4/Figure 2",
            "released": "no backtest, annualized-return, Sharpe, drawdown, or transaction-cost implementation",
            "status": "missing",
        },
        {
            "dimension": "cost_measurement",
            "paper": "Table 3 time and API fees",
            "released": "no request/token/cost logs or measurement script",
            "status": "missing",
        },
        {
            "dimension": "published_result_paths",
            "paper": "Tables 1--4",
            "released": "no signals, portfolios, baseline outputs, result tables, or cached LLM decisions",
            "status": "missing",
        },
    ]


def build_audit(source_root: Path, paper_path: Path, output_dir: Path) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected MASS source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official MASS paper PDF hash does not match the pinned primary source")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        actual = sha256(source_root / relative)
        if actual != expected:
            raise RuntimeError(f"Pinned MASS source hash changed for {relative}: {actual}")

    conformance = result_conformance()
    snapshot_rows, snapshot_summary = safe_distribution_snapshot(source_root / "ih_dist")
    datasets, dataset_summary = dataset_inventory(source_root)
    config = source_config_audit(source_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_1_4_conformance.csv", conformance, list(conformance[0]))
    write_csv(output_dir / "distribution_snapshot_audit.csv", snapshot_rows, list(snapshot_rows[0]))
    write_csv(output_dir / "released_dataset_inventory.csv", datasets, list(datasets[0]))
    write_csv(output_dir / "source_config_conformance.csv", config, list(config[0]))

    status_counts = Counter(row["status"] for row in conformance)
    table_counts = Counter(row["paper_table"] for row in conformance)
    numeric_table_counts = Counter(row["paper_table"] for row in conformance if row["paper_value_is_numeric"])
    row_groups = {(row["paper_table"], row["section"], row["stock_pool"], row["method"]) for row in conformance}
    if status_counts != {
        "unverifiable_no_shipped_native_signal_or_result_path": 277,
        "paper_non_numeric_emcl": 8,
    }:
        raise RuntimeError(f"Pinned MASS status counts changed: {status_counts}")
    if table_counts != {1: 108, 2: 72, 3: 6, 4: 99}:
        raise RuntimeError(f"Pinned MASS table-cell counts changed: {table_counts}")
    if numeric_table_counts != {1: 108, 2: 64, 3: 6, 4: 99}:
        raise RuntimeError(f"Pinned MASS numeric table-cell counts changed: {numeric_table_counts}")
    if len(row_groups) != 81:
        raise RuntimeError(f"Expected 81 MASS paper result rows, got {len(row_groups)}")

    manifest: Dict[str, Any] = {
        "audit": "MASS paper Tables 1--4 versus pinned public source release",
        "overall_status": "not_reproduced_partial_internal_state_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "paper_numeric_tables_audited": [1, 2, 3, 4],
        "paper_result_rows_total": len(row_groups),
        "paper_result_cells_total_including_emcl": len(conformance),
        "paper_numeric_result_cells_total": status_counts["unverifiable_no_shipped_native_signal_or_result_path"],
        "paper_non_numeric_emcl_cells": status_counts["paper_non_numeric_emcl"],
        "paper_numeric_result_cells_reproduced": 0,
        "paper_numeric_result_cells_unverifiable": status_counts[
            "unverifiable_no_shipped_native_signal_or_result_path"
        ],
        "native_agent_decision_cache_shipped": False,
        "native_signal_path_shipped": False,
        "native_portfolio_or_return_path_shipped": False,
        "native_baseline_outputs_shipped": False,
        "native_cost_or_timing_logs_shipped": False,
        "native_dated_distribution_snapshot_shipped": True,
        "distribution_snapshot_is_published_result": False,
        "distribution_snapshot": snapshot_summary,
        "released_dataset": dataset_summary,
        "released_full_four_pool_dataset": False,
        "released_sse50_like_2023_base_and_labels": True,
        "released_entrypoint_operational_without_source_and_data_repairs": False,
        "paper_main_hyperparameters_match_active_source_defaults": False,
        "paper_metric_horizon_identified": False,
        "paper_risk_free_rate_identified": False,
        "paper_random_seed_protocol_identified": False,
        "audit_called_llm_or_external_api": False,
        "interpretation": (
            "The release provides meaningful component evidence: a complete 242-day 2023 "
            "SSE50-like base/label panel and a safely decoded 263-date, 16-type optimizer-state "
            "trajectory. It does not reproduce any published result. All 277 numeric cells in "
            "Tables 1--4 lack native decisions/signals/baseline outputs/backtests/cost logs, the "
            "other paper pools are absent, and active source defaults differ from paper settings."
        ),
        "source_file_sha256": {relative: sha256(source_root / relative) for relative in PINNED_SOURCE_SHA256},
    }

    report = f"""# MASS paper-level conformance audit

Overall verdict: **not reproduced**. The public release contains real SSE50-like
input/label data and a dated learned agent-distribution snapshot, but it contains
none of the agent decisions, signals, baseline outputs, portfolios, backtests,
timing logs, or API accounting needed to reproduce Tables 1--4.

## Primary sources

- Official paper: {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.

## What the release genuinely establishes

- The base, label, and feature panels contain 242 trading dates during 2023 and
  exactly 50 stocks per date (59 distinct identifiers across constituent changes).
- `ih_dist` is a real native internal-state artifact. After checking its pinned
  hash and every pickle opcode before a restricted primitive-only decode, it has
  {snapshot_summary["dates"]} dates from {snapshot_summary["first_date"]} through
  {snapshot_summary["last_date"]}, 16 investor-type masks per date, positive weights
  with invariant raw sum 16, and {snapshot_summary["changed_transitions"]} changed
  transitions. This is optimizer state, not an action, signal, or return path.
- The released model name, 16-by-32 agent scale, SSE50 candidate count, score
  weight for SSE50/CSI 300, cooling rate, and optimizer lookback agree with the
  corresponding paper declarations.

## Why no published result is reproduced

- The audit enumerates {len(conformance)} Table 1--4 cells: 277 numeric claims and
  eight Table 2 EMCL markers. All 277 numeric claims are unverifiable from the
  release. No cached individual decisions are present, so the distribution state
  cannot be converted into the paper's signals.
- Only an SSE50-like panel is released. CSI 300, ChiNext 100, CSI A500, and the
  paper's full multimodal inputs are absent. The two news files are two-byte CRLF
  placeholders and invalid Parquet.
- The entry point cannot run as released: it has three empty `ROOT_PATH` constants,
  two literal paths missing f-string interpolation, and references absent pool,
  label, news, price-feature, and result paths.
- The paper specifies simulated-annealing initial temperature 40 and 100 iterations;
  the active source constructs defaults 0.5 and 20. The paper uses alpha=0.2 for
  ChiNext, while the source always uses the 0.5 default.
- The paper's main candidate pools are static per agent and treats daily updating as
  a separate MASS(DU) ablation. The active source resamples with replacement every
  day. It also generates one strategy per agent/day rather than one per type/day.
- Random modality, candidate-pool, and optimizer draws have no run-level seed. The
  paper does not identify which released 1/5/10-day label horizon produced Table 1,
  nor the risk-free rate behind Table 4 Sharpe ratios.
- Table 4/Figure 2 specify weekly top-20% portfolios and 0.1% round-trip costs, but
  the release has no portfolio/backtest/cost implementation. Table 3 has no timing,
  request, token, or fee logs.

Run `scripts/audit_mass_paper.py` to regenerate this package. Use `--strict` when
a CI failure is desired until the native decisions, complete inputs, experiment
configs/seeds, and result paths are released and reproduce at least one paper row.
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
        default=Path(
            os.environ.get(
                "MASS_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/mass_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "MASS_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/mass_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/mass",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.paper_pdf.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
