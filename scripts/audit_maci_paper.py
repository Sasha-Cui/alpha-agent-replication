#!/usr/bin/env python3
"""Build a fail-closed, multi-version audit for the MACI crypto paper.

The arXiv identifier contains two materially different experiments.  Versions
1--2 use a four-expert, fine-tuned GPT-4o system and 2023--2024 data.  Version 3
replaces that study with three multi-agent architectures, four capability
variants, three model families, and calendar-2025 data.  This builder keeps the
lineages separate and never promotes document reconstruction, printed-value
arithmetic, component execution, or author-output correspondence into an
end-to-end paper-result reproduction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Mapping, Sequence
from zipfile import ZipFile


EXPECTED = {
    "v1_pdf": "e6ac85d8805726811860b07281b7f4f9792918c0f5d664f31feb6d2238b30907",
    "v2_pdf": "14013a9d2af7585e00c8f3fcada0a745df15d3abf5fbd9adba03e64c408e7909",
    "v3_pdf": "cc2652f2f0a38e7b15e99734514381c759c803f90b2768696a568959675e0b27",
    "v1_source_tar": "3118bd36447fef00b39c80866e965bd6f436be53207cf457e72581c20e6b12c6",
    "v2_source_tar": "f4fae077906e28f97a0037235e4f9cf191c6c7994c5a92581b3dd9ff95b2fd74",
    "v3_source_tar": "3e7e9e020707bec1de3d7888715020a28d6a48377c874e5897f09016ca295a49",
    "v1_rebuild": "554e93a00877026967f9925bc18c0de0e20d73f0c73096984329af3ab741840b",
    "v2_rebuild": "9dda60dcf280d58a05cfd339d7e84ad10d9845af46a9283b1afc3b7bf8cabb3d",
    "v3_rebuild": "540b9fba5ba9d7e4be035bd2c1ddf0dbda094bdf362312c210ba43b132039a5d",
    "fama_french_archive": "cd6d8e0d175b6f423862a6ad15a3073a6e4264b52b2ac9262396c79f707c6bcb",
    "author_v1_commit": "962b83d7ca8908e675fc22c6d16ce24a0ec3e52f",
    "author_current_commit": "2326185cc2d1eff02724cfeb88116ebb13f904e7",
}

FLOAT_RE = re.compile(r"(?<![\w])[-+]?\d+\.\d+")
METRICS_V1 = ("Mean", "Std", "Sharpe")
VARIANTS_V1 = ("single_gpt4o_raw", "single_gpt4o_fine_tuned", "multi_agent")
METRICS_V3 = ("Cum_pct", "Avg_pct", "Vol_pct", "SR", "MDD_pct", "Win_pct")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def numbers(line: str) -> list[float]:
    return [float(value) for value in FLOAT_RE.findall(line)]


def data_lines(path: Path, required: str) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if required in line and line.rstrip().endswith(r"\\")
    ]


def result_row(
    version: str,
    table: str,
    category: str,
    strategy: str,
    subgroup: str,
    regime: str,
    metric: str,
    value: float,
    kind: str = "direct_result",
    native: bool = False,
    duplicate: str = "",
) -> dict[str, Any]:
    return {
        "paper_version": version,
        "experimental_lineage": "v1_v2_gpt4o_four_expert_2023_2024" if version == "v1/v2" else "v3_three_architecture_calendar_2025",
        "table": table,
        "category": category,
        "strategy_or_variant": strategy,
        "subgroup": subgroup,
        "regime_or_portfolio": regime,
        "metric": metric,
        "published_value": value,
        "cell_kind": kind,
        "native_maci_output": native,
        "duplicate_measurement_group": duplicate,
        "author_output_verified": False,
        "native_regenerated_value": "",
        "paper_result_credit": False,
        "note": "Printed paper value only; no released input-to-result lineage regenerates this cell.",
    }


def parse_v1_acc(path: Path) -> list[dict[str, Any]]:
    lines = data_lines(path, "databar{")
    if len(lines) != 6:
        raise ValueError(f"classification row count changed: {len(lines)}")
    experts = ("Crypto Factor", "Technical", "Collaboration", "Market Factor", "News", "Collaboration")
    rows = []
    for index, (line, expert) in enumerate(zip(lines, experts)):
        values = numbers(line)
        if len(values) != 6:
            raise ValueError(f"classification cell count changed: {line}")
        category = "crypto_prediction" if index < 3 else "market_prediction"
        for variant_index, variant in enumerate(VARIANTS_V1):
            for metric_index, metric in enumerate(("Accuracy", "MCC")):
                rows.append(
                    result_row(
                        "v1/v2",
                        "classification",
                        category,
                        variant,
                        expert,
                        "test",
                        metric,
                        values[variant_index * 2 + metric_index],
                        native=variant == "multi_agent",
                    )
                )
    return rows


def parse_v1_market_returns(path: Path) -> list[dict[str, Any]]:
    rows = []
    for regime in ("Rise", "Fall", "Diff"):
        line = next(
            item for item in path.read_text(encoding="utf-8").splitlines()
            if rf"\textbf{{{regime}}}" in item
        )
        values = numbers(line)
        if len(values) != 3:
            raise ValueError(f"market-return cell count changed: {line}")
        for variant, value in zip(VARIANTS_V1, values):
            rows.append(
                result_row(
                    "v1/v2",
                    "market_rise_fall",
                    "market_team_financial_significance",
                    variant,
                    "market_prediction",
                    regime,
                    "weekly_mean_return",
                    value,
                    kind="derived_difference" if regime == "Diff" else "direct_result",
                    native=variant == "multi_agent",
                )
            )
    return rows


def parse_v1_portfolio(path: Path) -> list[dict[str, Any]]:
    lines = data_lines(path, "textcolor")
    if len(lines) != 12:
        raise ValueError(f"portfolio row count changed: {len(lines)}")
    periods = ("All",) * 4 + ("Boom",) * 4 + ("Bust",) * 4
    strategies = ("Ours", "Market", "1/N", "Bitcoin") * 3
    rows = []
    for line, period, strategy in zip(lines, periods, strategies):
        values = numbers(line)
        if len(values) != 3:
            raise ValueError(f"portfolio cell count changed: {line}")
        for metric, value in zip(METRICS_V1, values):
            rows.append(
                result_row(
                    "v1/v2",
                    "portfolio",
                    "portfolio_performance",
                    strategy,
                    "weekly",
                    period,
                    metric,
                    value,
                    native=strategy == "Ours",
                )
            )
    return rows


def parse_v1_asset_pricing(path: Path) -> list[dict[str, Any]]:
    lines = data_lines(path, "databar{")
    if len(lines) != 18:
        raise ValueError(f"LLM asset-pricing row count changed: {len(lines)}")
    expert_groups = ("Crypto Factor",) * 6 + ("Technical",) * 6 + ("Collaboration",) * 6
    portfolios = ("Very Low", "Low", "Medium", "High", "Very High", "HML") * 3
    rows = []
    for line, expert, portfolio in zip(lines, expert_groups, portfolios):
        values = numbers(line)
        if len(values) != 9:
            raise ValueError(f"LLM asset-pricing cell count changed: {line}")
        for variant_index, variant in enumerate(VARIANTS_V1):
            for metric_index, metric in enumerate(METRICS_V1):
                rows.append(
                    result_row(
                        "v1/v2",
                        "llm_asset_pricing",
                        "quintile_and_hml",
                        variant,
                        expert,
                        portfolio,
                        metric,
                        values[variant_index * 3 + metric_index],
                        native=variant == "multi_agent",
                    )
                )
    return rows


def parse_v1_traditional(path: Path) -> list[dict[str, Any]]:
    lines = data_lines(path, "databar{")
    if len(lines) != 6:
        raise ValueError(f"traditional-factor row count changed: {len(lines)}")
    portfolios = ("Very Low", "Low", "Medium", "High", "Very High", "HML")
    factors = ("MOM_1_0", "MOM_4_0", "MOM_4_1")
    rows = []
    for line, portfolio in zip(lines, portfolios):
        values = numbers(line)
        if len(values) != 9:
            raise ValueError(f"traditional-factor cell count changed: {line}")
        for factor_index, factor in enumerate(factors):
            for metric_index, metric in enumerate(METRICS_V1):
                rows.append(
                    result_row(
                        "v1/v2",
                        "traditional_asset_pricing",
                        "cited_risk_factor_baseline",
                        factor,
                        "top_factor",
                        portfolio,
                        metric,
                        values[factor_index * 3 + metric_index],
                    )
                )
    return rows


def parse_v1_ablation(path: Path) -> list[dict[str, Any]]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if (r"\CIRCLE" in line or r"\Circle" in line) and line.rstrip().endswith(r"\\")
    ]
    if len(lines) != 6:
        raise ValueError(f"v1 ablation row count changed: {len(lines)}")
    variants = ("full_system", "minus_crypto_factor", "minus_technical", "minus_market_factor", "minus_news", "minus_interteam_collaboration")
    metrics = ("Cumulative", "Mean", "Std", "Sharpe")
    rows = []
    for line, variant in zip(lines, variants):
        values = numbers(line)
        if len(values) != 4:
            raise ValueError(f"v1 ablation cell count changed: {line}")
        for metric, value in zip(metrics, values):
            duplicate = ""
            if variant == "full_system" and metric in METRICS_V1:
                duplicate = f"v1_full_system_{metric.lower()}"
            rows.append(
                result_row(
                    "v1/v2",
                    "ablation",
                    "agent_and_collaboration_ablation",
                    variant,
                    "multi_agent",
                    "All",
                    metric,
                    value,
                    native=True,
                    duplicate=duplicate,
                )
            )
    return rows


def v1_result_ledger(root: Path) -> list[dict[str, Any]]:
    tables = root / "Tables"
    rows = []
    rows.extend(parse_v1_acc(tables / "acc_mcc.tex"))
    rows.extend(parse_v1_market_returns(tables / "mkt_ap.tex"))
    rows.extend(parse_v1_portfolio(tables / "port.tex"))
    rows.extend(parse_v1_asset_pricing(tables / "ap.tex"))
    rows.extend(parse_v1_traditional(tables / "trad_ap.tex"))
    rows.extend(parse_v1_ablation(tables / "ablation.tex"))
    if len(rows) != 321:
        raise ValueError(f"v1/v2 denominator changed: {len(rows)}")
    if sum(row["cell_kind"] == "direct_result" for row in rows) != 318:
        raise ValueError("v1/v2 direct denominator changed")
    if sum(bool(row["native_maci_output"]) for row in rows) != 102:
        raise ValueError("v1/v2 native displayed-unit denominator changed")
    return rows


def clean_v3_strategy(line: str) -> str:
    second = line.split("&", 2)[1]
    second = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^]]*\])?\{([^{}]*)\}", r"\1", second)
    second = second.replace(r"\ ", " ").replace("$", "")
    return " ".join(second.split())


def parse_v3_performance(path: Path) -> list[dict[str, Any]]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        values = numbers(line)
        if line.rstrip().endswith(r"\\") and len(values) == 18:
            lines.append(line.strip())
    if len(lines) != 23:
        raise ValueError(f"v3 performance row count changed: {len(lines)}")
    categories = ("Hold",) * 2 + ("Deep Learning",) * 5 + ("Single Agent",) * 4 + ("Multi-Agent System",) * 12
    regimes = ("All", "Bull", "Bear")
    rows = []
    for line, category in zip(lines, categories):
        values = numbers(line)
        strategy = clean_v3_strategy(line)
        if not strategy:
            raise ValueError(f"cannot parse v3 strategy: {line}")
        for regime_index, regime in enumerate(regimes):
            for metric_index, metric in enumerate(METRICS_V3):
                rows.append(
                    result_row(
                        "v3",
                        "performance",
                        category,
                        strategy,
                        "GPT-4o",
                        regime,
                        metric,
                        values[regime_index * 6 + metric_index],
                        native=category == "Multi-Agent System",
                    )
                )
    if len(rows) != 414:
        raise ValueError("v3 performance denominator changed")
    return rows


def parse_v3_ablation(path: Path) -> list[dict[str, Any]]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.rstrip().endswith(r"\\") and ("Hier." in line or line.lstrip().startswith("$-$")):
            lines.append(line.strip())
    if len(lines) != 4:
        raise ValueError(f"v3 ablation row count changed: {len(lines)}")
    variants = ("Hierarchical ZS reference", "minus_news_agent", "minus_crypto_agent", "minus_memory")
    metrics = ("Cum_pct", "Vol_pct", "SR", "Win_pct")
    rows = []
    for line_index, (line, variant) in enumerate(zip(lines, variants)):
        values = numbers(line)
        direct = values if line_index == 0 else values[::2]
        deltas = [] if line_index == 0 else values[1::2]
        if len(direct) != 4 or (line_index and len(deltas) != 4):
            raise ValueError(f"v3 ablation cell count changed: {line}")
        for metric, value in zip(metrics, direct):
            rows.append(
                result_row(
                    "v3",
                    "ablation",
                    "multi_agent_component_ablation",
                    variant,
                    "GPT-4o",
                    "All",
                    metric,
                    value,
                    native=True,
                    duplicate=(f"v3_hier_zs_all_{metric.lower()}" if line_index == 0 else ""),
                )
            )
        for metric, value in zip(metrics, deltas):
            rows.append(
                result_row(
                    "v3",
                    "ablation",
                    "multi_agent_component_ablation",
                    variant,
                    "GPT-4o",
                    "All",
                    f"Delta_{metric}",
                    value,
                    kind="derived_delta",
                    native=True,
                )
            )
    if len(rows) != 28:
        raise ValueError(f"v3 ablation denominator changed: {len(rows)}")
    return rows


def v3_result_ledger(root: Path) -> list[dict[str, Any]]:
    exhibits = root / "Exhibits"
    rows = parse_v3_performance(exhibits / "performance.tex")
    rows.extend(parse_v3_ablation(exhibits / "ablation.tex"))
    if len(rows) != 442:
        raise ValueError(f"v3 denominator changed: {len(rows)}")
    if sum(row["cell_kind"] == "direct_result" for row in rows) != 430:
        raise ValueError("v3 direct denominator changed")
    if sum(bool(row["native_maci_output"]) for row in rows) != 244:
        raise ValueError("v3 native displayed-unit denominator changed")
    return rows


def figure_rows(source: Path, author: Path, comparison: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    comparison_by_name = {row["asset"]: row for row in comparison}
    result_units = {
        "port_BTC.pdf": 3,
        "port_USD.pdf": 3,
        "scatter_cs.pdf": 3,
        "scatter_mkt.pdf": 3,
        "bar_cs.pdf": 3,
        "bar_mkt.pdf": 3,
        "radar_cs.pdf": 3,
    }
    qualitative = {"explanation.pdf": 2}
    names = sorted(path.name for path in (source / "Figures").iterdir() if path.suffix.lower() in {".pdf", ".png"})
    if len(names) != 17:
        raise ValueError(f"v1 figure-asset count changed: {len(names)}")
    rows = []
    for name in names:
        source_path = source / "Figures" / name
        author_matches = list(author.rglob(name))
        if len(author_matches) != 1:
            raise ValueError(f"author figure match count for {name}: {len(author_matches)}")
        author_path = author_matches[0]
        source_hash = sha256_file(source_path)
        author_hash = sha256_file(author_path)
        if source_hash == author_hash:
            correspondence = "byte_identical"
        elif name == "scatter_cs.pdf":
            details = comparison_by_name[name]["pages"][0]
            if details["exact_pixel_channel_fraction"] != 1.0:
                raise ValueError("scatter_cs is no longer render-identical")
            correspondence = "render_pixel_identical_metadata_only_difference"
        elif name == "scatter_mkt.pdf":
            details = comparison_by_name[name]["pages"][0]
            source_shapes = details["source"]["drawing_shape_hash_counts"]
            author_shapes = details["author"]["drawing_shape_hash_counts"]
            if any(source_shapes.get(key, 0) < value for key, value in author_shapes.items()):
                raise ValueError("scatter_mkt author geometry is no longer a submitted-figure subset")
            correspondence = "all_author_drawing_geometry_preserved_submitted_label_adds_factor"
        elif name.startswith("port_"):
            details = comparison_by_name[name]["pages"][0]
            source_records = [row for row in details["source"]["drawing_records"] if row["x_scale_normalized_points"]]
            author_records = [row for row in details["author"]["drawing_records"] if row["x_scale_normalized_points"]]
            maximum_x = 0.0
            maximum_y = 0.0
            for left in source_records:
                matches = [
                    right for right in author_records
                    if right["point_count"] == left["point_count"] and right["color"] == left["color"]
                ]
                if len(matches) != 1:
                    raise ValueError(f"cannot pair portfolio path in {name}")
                for point_left, point_right in zip(left["x_scale_normalized_points"], matches[0]["x_scale_normalized_points"]):
                    maximum_x = max(maximum_x, abs(point_left[0] - point_right[0]))
                    maximum_y = max(maximum_y, abs(point_left[1] - point_right[1]))
            if maximum_x > 0.0000011 or maximum_y != 0:
                raise ValueError(f"portfolio path geometry changed: {name}")
            correspondence = "all_five_vector_paths_same_y_and_point_counts_after_horizontal_resize_legend_changed"
        else:
            raise ValueError(f"unexpected non-identical figure: {name}")
        rows.append(
            {
                "asset": name,
                "compiled_into_v1_pdf": name != "port_ETH.pdf",
                "role": (
                    "quantitative_result_figure" if name in result_units
                    else "qualitative_result_example" if name in qualitative
                    else "unused_quantitative_result_asset" if name == "port_ETH.pdf"
                    else "method_or_input_illustration"
                ),
                "published_plotted_result_units": result_units.get(name, 0),
                "published_qualitative_outputs": qualitative.get(name, 0),
                "source_sha256": source_hash,
                "author_sha256": author_hash,
                "author_output_correspondence": correspondence,
                "native_result_regenerated": False,
                "paper_result_credit": False,
                "note": "Author-output lineage only; no inputs or execution regenerate the plotted output.",
            }
        )
    return rows


def method_rows() -> list[dict[str, Any]]:
    entries = [
        ("v1/v2", "system_architecture", "specified_and_source_present", "Four experts, team collaboration, and source classes are recoverable."),
        ("v1/v2", "base_model", "exact_snapshot_in_source", "gpt-4o-2024-08-06, temperature 0."),
        ("v1/v2", "fine_tuned_model_ids", "incomplete_unverified", "One commented fine-tuned model ID appears in source; the actual job, selected model, and complete lineage are not released."),
        ("v1/v2", "training_period", "specified", "June--October 2023 in paper; source fine-tuning bounds end November 1."),
        ("v1/v2", "test_period", "conflicting", "Paper says November 2023--September 2024; figures end August; source handlers end January 2025; metrics imply 43 weeks."),
        ("v1/v2", "universe", "high_level_only", "Weekly top-30 CoinGecko universe stated; exact memberships are absent."),
        ("v1/v2", "raw_inputs", "missing", "data/ and processed_data/ are gitignored and absent."),
        ("v1/v2", "processed_inputs", "missing", "Factors, news, charts, prices, and labels are absent."),
        ("v1/v2", "prompt_templates", "substantial_source_present", "Templates and prompt generator are released; exact instantiated prompts are absent."),
        ("v1/v2", "model_requests_responses", "missing", "No immutable requests, responses, token/logprob records, or retry logs."),
        ("v1/v2", "checkpoints", "missing", "Runner names pickle checkpoints, but none are released."),
        ("v1/v2", "prediction_records", "missing", "Runner names JSON records, but none are released."),
        ("v1/v2", "portfolio_rules", "source_present", "Top-quintile, linear-probability ensemble, and market weights are inspectable."),
        ("v1/v2", "costs_and_slippage", "missing", "No execution-cost or slippage contract."),
        ("v1/v2", "risk_free_rate", "source_uses_zero", "Portfolio evaluator uses zero; paper does not identify a source."),
        ("v1/v2", "seeds_repetitions_uncertainty", "missing", "No seeds, repetitions, or uncertainty lineage."),
        ("v1/v2", "table_outputs", "missing", "Zero of 321 printed table units are shipped as source-derived records."),
        ("v1/v2", "figure_outputs", "author_output_verified", "All 16 compiled figure assets have author-repository content lineage; this is not regeneration."),
        ("v3", "system_architecture", "paper_only", "Hierarchical, collaborative, and debate architectures are described but absent from code."),
        ("v3", "model_snapshots", "missing", "GPT-4o, GPT-5, and Claude Sonnet 4.5 snapshot IDs are not pinned."),
        ("v3", "experiment_period", "specified", "Calendar 2025, 52 weeks."),
        ("v3", "universe", "high_level_only", "Fixed top-15 layer-1 cryptocurrencies; exact membership/corporate actions are absent."),
        ("v3", "raw_and_processed_inputs", "missing", "No frozen price/news rows, timestamps, or retrieval corpus."),
        ("v3", "memory_rag_skill_state", "missing", "No memory, retrieval index, skill library, or updates."),
        ("v3", "prompts", "partial_appendix", "Three prompts compile; unfilled runtime inputs and exact requests/responses are absent."),
        ("v3", "decision_traces", "missing", "No traces are released despite the traceability claim."),
        ("v3", "actions_orders_fills", "missing", "No action, order, fill, or timing record."),
        ("v3", "baseline_code_checkpoints", "missing", "Five deep-learning and all agent baseline runtimes are absent."),
        ("v3", "transaction_costs_slippage", "missing", "No executable market-friction contract."),
        ("v3", "risk_free_rate", "hard_result_method_conflict", "Printed full-period Sharpe values imply approximately zero, not the cited Fama-French T-bill series."),
        ("v3", "seeds_repetitions_uncertainty", "missing", "No seeds, repetitions, confidence intervals, or run dispersion."),
        ("v3", "table_outputs", "missing", "Zero of 442 printed table units have input-to-output run lineage."),
        ("v3", "figure_outputs", "paper_vector_only", "142 plotted bars/lines/points are published without underlying result arrays."),
    ]
    return [
        {"paper_version": version, "dimension": dimension, "status": status, "evidence_boundary": note}
        for version, dimension, status, note in entries
    ]


def prompt_rows(v1: Path, v3: Path) -> list[dict[str, Any]]:
    rows = []
    for version, root in (("v1/v2", v1), ("v3", v3)):
        for path in sorted((root / "Prompts").glob("*.tex")):
            compiled = version == "v1/v2" or path.name in {"crypto_instruc.tex", "trading_instruc.tex", "cot_instruc.tex"}
            rows.append(
                {
                    "paper_version": version,
                    "source_file": path.name,
                    "compiled_into_appendix": compiled,
                    "exact_runtime_values_released": False,
                    "actual_request_released": False,
                    "actual_response_released": False,
                    "note": (
                        "Appendix prompt source; placeholders remain uninstantiated."
                        if compiled else "Legacy source residue not compiled into the v3 manuscript."
                    ),
                }
            )
    if sum(row["paper_version"] == "v3" for row in rows) != 18:
        raise ValueError("v3 prompt-source count changed")
    if sum(row["paper_version"] == "v3" and row["compiled_into_appendix"] for row in rows) != 3:
        raise ValueError("v3 compiled-prompt count changed")
    return rows


def consistency_rows(v1_rows: Sequence[Mapping[str, Any]], v3_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    performance = [row for row in v3_rows if row["table"] == "performance"]
    all_values: dict[str, dict[str, float]] = {}
    bear_values: dict[str, dict[str, float]] = {}
    for row in performance:
        target = all_values if row["regime_or_portfolio"] == "All" else bear_values if row["regime_or_portfolio"] == "Bear" else None
        if target is not None:
            target.setdefault(str(row["strategy_or_variant"]), {})[str(row["metric"])] = float(row["published_value"])
    implied_rf = [values["Avg_pct"] - values["SR"] * values["Vol_pct"] / 52 for values in all_values.values()]
    mdd_violations = [
        strategy for strategy, values in bear_values.items()
        if values["Cum_pct"] < 0 and values["MDD_pct"] > values["Cum_pct"]
    ]
    market_accuracy = [
        float(row["published_value"])
        for row in v1_rows
        if row["table"] == "classification"
        and row["category"] == "market_prediction"
        and row["metric"] == "Accuracy"
    ]
    annualized = (1 + 0.8347) ** (52 / 43) - 1
    entries = [
        ("v1/v2", "artifact_placeholder", "hard_release_claim_conflict", "v1 literally prints URL_TO_YOUR_ARTIFACTS; v2 comments the statement out."),
        ("v1/v2", "python_requirement", "hard_environment_conflict", "pyproject claims >=3.9.15, while two released match statements fail to parse on Python 3.9."),
        ("v1/v2", "test_dates", "unresolved_date_conflict", "Paper says through September 2024, plots through August, and source handlers through 2024-12-31."),
        ("v1/v2", "forty_three_week_lineage", "strong_internal_correspondence", f"Market accuracies are 43-week fractions and annualizing 0.8347 over 43 weeks gives {annualized:.6f}, matching 108.32%. Values: {market_accuracy}."),
        ("v1/v2", "fine_tuning_coverage", "source_execution_gap", "Only the crypto-factor fine-tuning block is active; other expert blocks are commented and require manual edits."),
        ("v1/v2", "explanation_dimensions", "paper_source_mismatch", "Judge source scores eight criteria; paper reports five and releases no evaluation records."),
        ("v1/v2", "figure_revision", "author_output_verified_not_regenerated", "All compiled assets correspond; portfolio legends/width and one scatter label changed after the pinned pre-submission commit."),
        ("v3", "code_lineage", "no_v3_implementation_recovered", "Current author source retains the v1-style system and contains none of the v3 architectures/capabilities."),
        ("v3", "strictly_out_of_pretraining_claim", "claim_not_supported", "Official provider dates/cutoffs do not support treating all calendar-2025 observations as strictly outside every model's training distribution."),
        ("v3", "retrospective_model_availability", "temporal_validity_risk", "GPT-5 and Claude Sonnet 4.5 were released during 2025, so their full-year evaluations were necessarily retrospective."),
        ("v3", "risk_free_rate", "hard_method_result_conflict", f"Across 23 full-period rows, implied weekly RF ranges {min(implied_rf):.6f}% to {max(implied_rf):.6f}% (mean {sum(implied_rf)/len(implied_rf):.6f}%), effectively zero rather than the cited 2025 Fama-French T-bill rate."),
        ("v3", "bear_regime_mdd", "unreported_convention_or_hard_value_conflict", f"{len(mdd_violations)}/23 bear rows have negative terminal cumulative return whose magnitude exceeds printed MDD; they cannot arise from the same regime-conditioned path under the printed definition."),
        ("v3", "action_timing", "ambiguous", "Inputs at t-1 produce A_t, while the wealth equation applies A_{t-1}; close/execution timing is not resolved."),
        ("v3", "traceability", "claim_unverifiable", "The paper says every decision is traceable but releases no trace."),
    ]
    return [
        {"paper_version": version, "claim_id": claim, "status": status, "evidence": evidence}
        for version, claim, status, evidence in entries
    ]


def source_rows() -> list[dict[str, Any]]:
    return [
        {"version": "v1", "submitted_utc": "2025-01-01T13:08:17Z", "pdf_sha256": EXPECTED["v1_pdf"], "source_tar_sha256": EXPECTED["v1_source_tar"], "pages": 14, "experimental_lineage": "v1_v2_gpt4o_four_expert_2023_2024"},
        {"version": "v2", "submitted_utc": "2025-01-07T00:15:11Z", "pdf_sha256": EXPECTED["v2_pdf"], "source_tar_sha256": EXPECTED["v2_source_tar"], "pages": 14, "experimental_lineage": "v1_v2_gpt4o_four_expert_2023_2024"},
        {"version": "v3", "submitted_utc": "2026-06-16T16:36:42Z", "pdf_sha256": EXPECTED["v3_pdf"], "source_tar_sha256": EXPECTED["v3_source_tar"], "pages": 10, "experimental_lineage": "v3_three_architecture_calendar_2025"},
    ]


def artifact_rows() -> list[dict[str, Any]]:
    return [
        {"artifact": "arXiv v1/v2 paper and TeX", "url_or_commit": "https://arxiv.org/abs/2501.00826", "availability": "complete manuscript source", "system_credit": False, "result_credit": False, "note": "Document/specification evidence."},
        {"artifact": "arXiv v3 paper and TeX", "url_or_commit": "https://arxiv.org/abs/2501.00826", "availability": "complete manuscript source with three compiled prompts", "system_credit": False, "result_credit": False, "note": "Different experiment under the same identifier."},
        {"artifact": "author repository", "url_or_commit": "https://github.com/lyc0603/multi-agent", "availability": "reachable MIT Python repository", "system_credit": True, "result_credit": False, "note": "Author identity and paper title match."},
        {"artifact": "pre-submission author commit", "url_or_commit": EXPECTED["author_v1_commit"], "availability": "2330 files; 147197324 bytes", "system_credit": True, "result_credit": False, "note": "Authentic v1-style source, figures, runner, and tests; constants/data/results are omitted."},
        {"artifact": "current author commit", "url_or_commit": EXPECTED["author_current_commit"], "availability": "6566 tree entries; 378382176 blob bytes", "system_credit": True, "result_credit": False, "note": "Restores constants and extends figures but contains no v3 implementation."},
        {"artifact": "historical README repository target", "url_or_commit": "https://github.com/dlt-science/multi-agent", "availability": "HTTP 404", "system_credit": False, "result_credit": False, "note": "Bounded current access result, not proof no private/deleted artifact existed."},
        {"artifact": "Fama-French factors", "url_or_commit": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html", "availability": "official monthly factor archive pinned", "system_credit": False, "result_credit": False, "note": "2025 monthly RF is 0.30--0.38%, conflicting with table-implied approximately-zero RF."},
    ]


def external_primary_source_rows() -> list[dict[str, Any]]:
    return [
        {
            "subject": "GPT-4o API snapshot",
            "primary_source": "https://developers.openai.com/api/docs/models/gpt-4o",
            "source_fact": "OpenAI lists gpt-4o-2024-08-06 as a dated snapshot.",
            "audit_implication": "v1 source pins a real snapshot; v3 says GPT-4o without a snapshot ID.",
        },
        {
            "subject": "GPT-5 release and snapshot",
            "primary_source": "https://openai.com/index/introducing-gpt-5-for-developers/",
            "source_fact": "OpenAI released GPT-5 in the API on 2025-08-07.",
            "audit_implication": "A GPT-5 evaluation covering all of calendar 2025 is retrospective for the pre-release months.",
        },
        {
            "subject": "GPT-5 knowledge cutoff",
            "primary_source": "https://developers.openai.com/api/docs/models/gpt-5",
            "source_fact": "The GPT-5 model page lists a 2024-09-30 knowledge cutoff and dated snapshot gpt-5-2025-08-07.",
            "audit_implication": "The paper omits the exact snapshot; calendar-2025 is post-cutoff but not wholly prospective relative to release.",
        },
        {
            "subject": "Claude Sonnet 4.5 release",
            "primary_source": "https://www.anthropic.com/news/claude-sonnet-4-5",
            "source_fact": "Anthropic released Claude Sonnet 4.5 on 2025-09-29.",
            "audit_implication": "A Claude Sonnet 4.5 evaluation covering all of calendar 2025 is retrospective for the pre-release months.",
        },
        {
            "subject": "Claude Sonnet 4.5 training boundary",
            "primary_source": "https://www.anthropic.com/transparency",
            "source_fact": "Anthropic reports a Jan-2025 reliable knowledge cutoff and public internet training data through July 2025.",
            "audit_implication": "The blanket claim that all 2025 observations are strictly outside pretraining is contradicted by the disclosed training-data boundary.",
        },
        {
            "subject": "Claude Sonnet 4.5 snapshot",
            "primary_source": "https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions",
            "source_fact": "Anthropic documents the pinned ID claude-sonnet-4-5-20250929.",
            "audit_implication": "The paper names only Claude Sonnet 4.5, leaving the exact request-level model ID unrecorded.",
        },
        {
            "subject": "Fama-French risk-free factor",
            "primary_source": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
            "source_fact": "The pinned official monthly archive reports 2025 RF values from 0.30% to 0.38%.",
            "audit_implication": "The printed v3 full-period Sharpe values instead imply an approximately zero weekly risk-free rate.",
        },
    ]


def pdf_pages(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], check=True, text=True, capture_output=True)
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    if not match:
        raise ValueError(f"cannot read page count: {path}")
    return int(match.group(1))


def pdf_text_metrics(official: Path, rebuilt: Path) -> dict[str, Any]:
    def tokens(path: Path) -> list[str]:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=True,
            text=True,
            capture_output=True,
        )
        return re.findall(r"[A-Za-z0-9]+(?:[.'’-][A-Za-z0-9]+)*", result.stdout.lower())

    official_tokens = tokens(official)
    rebuilt_tokens = tokens(rebuilt)
    official_counts = Counter(official_tokens)
    rebuilt_counts = Counter(rebuilt_tokens)
    intersection = sum((official_counts & rebuilt_counts).values())
    union = sum((official_counts | rebuilt_counts).values())
    return {
        "official_tokens": len(official_tokens),
        "rebuilt_tokens": len(rebuilt_tokens),
        "token_delta": len(rebuilt_tokens) - len(official_tokens),
        "sequence_ratio": SequenceMatcher(None, official_tokens, rebuilt_tokens, autojunk=False).ratio(),
        "multiset_jaccard": intersection / union,
    }


def latex_log_summary(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    output = re.search(r"Output written on .*\((\d+) pages?", text)
    if not output:
        raise ValueError(f"cannot find final LaTeX output record: {path}")
    return {
        "undefined_citations": len(re.findall(r"Citation .* undefined", text)),
        "undefined_references": len(re.findall(r"Reference .* undefined", text)),
        "latex_errors": len(re.findall(r"^!", text, re.MULTILINE)),
        "overfull_hbox": text.count(r"Overfull \hbox"),
        "overfull_vbox": text.count(r"Overfull \vbox"),
        "underfull_hbox": text.count(r"Underfull \hbox"),
        "underfull_vbox": text.count(r"Underfull \vbox"),
        "output_pages": int(output.group(1)),
    }


def manuscript_provenance(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = []
    for version in ("v1", "v2", "v3"):
        official = getattr(args, f"official_{version}")
        run1 = getattr(args, f"rebuild_{version}_run1")
        run2 = getattr(args, f"rebuild_{version}_run2")
        final_log = getattr(args, f"rebuild_{version}_log")
        expected_pages = 10 if version == "v3" else 14
        rebuild_hash = EXPECTED[f"{version}_rebuild"]
        run1_hash = sha256_file(run1)
        run2_hash = sha256_file(run2)
        if run1_hash != rebuild_hash or run2_hash != rebuild_hash:
            raise ValueError(f"{version} rebuild hash changed")
        if pdf_pages(run1) != expected_pages or pdf_pages(run2) != expected_pages:
            raise ValueError(f"{version} rebuild page count changed")
        log = latex_log_summary(final_log)
        if log["latex_errors"] or log["undefined_citations"] or log["undefined_references"]:
            raise ValueError(f"{version} final manuscript log is not clean")
        rows.append(
            {
                "version": version,
                "official_pdf_sha256": sha256_file(official),
                "official_pages": pdf_pages(official),
                "source_tar_sha256": sha256_file(getattr(args, f"source_tar_{version}")),
                "rebuild_run1_sha256": run1_hash,
                "rebuild_run2_sha256": run2_hash,
                "rebuild_runs_byte_identical": run1_hash == run2_hash,
                "rebuild_pages": pdf_pages(run2),
                "official_rebuild_text": pdf_text_metrics(official, run2),
                "final_latex_log": log,
                "visual_qa": {
                    "status": "passed_full_document_contact_sheet_review",
                    "review_date": "2026-08-11",
                    "pages_reviewed_official": expected_pages,
                    "pages_reviewed_rebuild": expected_pages,
                    "checks": [
                        "readable_text",
                        "no_clipping",
                        "no_overlap",
                        "no_invisible_content",
                        "overall_layout_correspondence",
                    ],
                    "qualification": "Manual visual reconstruction QA only; it provides no experimental-result credit.",
                },
                "paper_result_credit": False,
            }
        )
    return rows


def author_source_inventory(v1: Path, current: Path) -> dict[str, Any]:
    def files(root: Path, suffix: str | None = None) -> list[Path]:
        return [
            path for path in root.rglob("*")
            if path.is_file()
            and ".git" not in path.relative_to(root).parts
            and (suffix is None or path.suffix == suffix)
        ]

    v1_python = files(v1, ".py")
    current_python = files(current, ".py")
    searchable = [path for path in files(current) if path.suffix.lower() in {".py", ".md"}]
    search_terms = ("hierarchical", "collaborative", "debate", "retrieval-augmented", "skill", "memory")
    hits = {term: 0 for term in search_terms}
    for path in searchable:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for term in search_terms:
            hits[term] += int(term in text)
    return {
        "pre_submission_commit": EXPECTED["author_v1_commit"],
        "current_commit": EXPECTED["author_current_commit"],
        "pre_submission_python_files": len(v1_python),
        "current_python_files": len(current_python),
        "pre_submission_constants_present": (v1 / "environ" / "constants.py").is_file(),
        "current_constants_present": (current / "environ" / "constants.py").is_file(),
        "pre_submission_data_files": len(files(v1 / "data")) if (v1 / "data").exists() else 0,
        "pre_submission_processed_data_files": len(files(v1 / "processed_data")) if (v1 / "processed_data").exists() else 0,
        "v3_architecture_capability_term_file_hits": hits,
        "v3_implementation_recovered": any(hits.values()),
        "qualification": "A zero lexical hit supports, but cannot alone prove, absence; manual source inspection also found only the v1-style system.",
    }


def validate_fama_french(path: Path) -> dict[str, float]:
    if sha256_file(path) != EXPECTED["fama_french_archive"]:
        raise ValueError("Fama-French archive hash changed")
    with ZipFile(path) as archive:
        names = archive.namelist()
        if names != ["F-F_Research_Data_Factors.csv"]:
            raise ValueError(f"Fama-French archive members changed: {names}")
        text = archive.read(names[0]).decode("utf-8")
    values = {}
    for line in text.splitlines():
        match = re.match(r"^(2025\d{2}),.*?,\s*([-+]?\d+\.\d+)\s*$", line)
        if match:
            values[match.group(1)] = float(match.group(2))
    if len(values) != 12 or min(values.values()) != 0.30 or max(values.values()) != 0.38:
        raise ValueError(f"Fama-French 2025 RF values changed: {values}")
    return values


def validate_primary_inputs(args: argparse.Namespace) -> None:
    for version in ("v1", "v2", "v3"):
        pdf = getattr(args, f"official_{version}")
        if sha256_file(pdf) != EXPECTED[f"{version}_pdf"]:
            raise ValueError(f"official {version} PDF hash changed")
        expected_pages = 14 if version != "v3" else 10
        if pdf_pages(pdf) != expected_pages:
            raise ValueError(f"official {version} page count changed")
        source_tar = getattr(args, f"source_tar_{version}")
        if sha256_file(source_tar) != EXPECTED[f"{version}_source_tar"]:
            raise ValueError(f"official {version} source tar hash changed")
    if args.author_current_commit != EXPECTED["author_current_commit"]:
        raise ValueError("current author commit changed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-source", type=Path, required=True)
    parser.add_argument("--v2-source", type=Path, required=True)
    parser.add_argument("--v3-source", type=Path, required=True)
    parser.add_argument("--source-tar-v1", type=Path, required=True)
    parser.add_argument("--source-tar-v2", type=Path, required=True)
    parser.add_argument("--source-tar-v3", type=Path, required=True)
    parser.add_argument("--author-v1", type=Path, required=True)
    parser.add_argument("--author-current", type=Path, required=True)
    parser.add_argument("--official-v1", type=Path, required=True)
    parser.add_argument("--official-v2", type=Path, required=True)
    parser.add_argument("--official-v3", type=Path, required=True)
    parser.add_argument("--rebuild-v1-run1", type=Path, required=True)
    parser.add_argument("--rebuild-v1-run2", type=Path, required=True)
    parser.add_argument("--rebuild-v1-log", type=Path, required=True)
    parser.add_argument("--rebuild-v2-run1", type=Path, required=True)
    parser.add_argument("--rebuild-v2-run2", type=Path, required=True)
    parser.add_argument("--rebuild-v2-log", type=Path, required=True)
    parser.add_argument("--rebuild-v3-run1", type=Path, required=True)
    parser.add_argument("--rebuild-v3-run2", type=Path, required=True)
    parser.add_argument("--rebuild-v3-log", type=Path, required=True)
    parser.add_argument("--fama-french-archive", type=Path, required=True)
    parser.add_argument("--author-current-commit", required=True)
    parser.add_argument("--execution-json", type=Path, required=True)
    parser.add_argument("--figure-comparison-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    validate_primary_inputs(args)
    v1 = v1_result_ledger(args.v1_source)
    v2 = v1_result_ledger(args.v2_source)
    if [row["published_value"] for row in v1] != [row["published_value"] for row in v2]:
        raise ValueError("v1/v2 printed result values changed")
    v3 = v3_result_ledger(args.v3_source)
    comparison = json.loads(args.figure_comparison_json.read_text(encoding="utf-8"))
    figures = figure_rows(args.v1_source, args.author_v1, comparison)
    execution = json.loads(args.execution_json.read_text(encoding="utf-8"))
    manuscripts = manuscript_provenance(args)
    source_inventory = author_source_inventory(args.author_v1, args.author_current)
    fama_french_rf = validate_fama_french(args.fama_french_archive)

    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "source_lineage.csv", source_rows())
    write_csv(output / "published_result_ledger_v1_v2.csv", v1)
    write_csv(output / "published_result_ledger_v3.csv", v3)
    write_csv(output / "figure_lineage_v1.csv", figures)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "prompt_inventory.csv", prompt_rows(args.v1_source, args.v3_source))
    write_csv(output / "internal_consistency_audit.csv", consistency_rows(v1, v3))
    write_csv(output / "artifact_access_audit.csv", artifact_rows())
    write_csv(output / "external_primary_source_audit.csv", external_primary_source_rows())
    (output / "native_execution.json").write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")
    (output / "manuscript_provenance.json").write_text(json.dumps(manuscripts, indent=2) + "\n", encoding="utf-8")
    (output / "author_source_inventory.json").write_text(json.dumps(source_inventory, indent=2) + "\n", encoding="utf-8")
    (output / "primary_source_validation.json").write_text(
        json.dumps(
            {
                "fama_french_archive_sha256": sha256_file(args.fama_french_archive),
                "fama_french_2025_monthly_rf_pct": fama_french_rf,
                "provider_source_count": 6,
                "paper_result_credit": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    v1_direct = [row for row in v1 if row["cell_kind"] == "direct_result"]
    v3_direct = [row for row in v3 if row["cell_kind"] == "direct_result"]
    v1_native_direct = [row for row in v1_direct if row["native_maci_output"]]
    v3_native_direct = [row for row in v3_direct if row["native_maci_output"]]
    manifest = {
        "audit": "MACI arXiv 2501.00826 multi-version paper/source/result audit",
        "overall_status": "v1_v2_author_source_and_output_lineage_without_table_regeneration_v3_paper_only_zero_table_regeneration",
        "full_end_to_end_pipeline_reproduced": False,
        "v1_v2_published_table_units": len(v1),
        "v1_v2_direct_table_results": len(v1_direct),
        "v1_v2_unique_direct_measurements": len(v1_direct) - 3,
        "v1_v2_native_maci_direct_cells": len(v1_native_direct),
        "v1_v2_native_maci_unique_direct_measurements": len(v1_native_direct) - 3,
        "v1_v2_table_units_faithfully_regenerated": 0,
        "v3_published_table_units": len(v3),
        "v3_direct_table_results": len(v3_direct),
        "v3_unique_direct_measurements": len(v3_direct) - 4,
        "v3_native_maci_displayed_table_units": sum(bool(row["native_maci_output"]) for row in v3),
        "v3_native_maci_direct_cells": len(v3_native_direct),
        "v3_native_maci_unique_direct_measurements": len(v3_native_direct) - 4,
        "v3_table_units_faithfully_regenerated": 0,
        "v1_compiled_figure_assets": sum(bool(row["compiled_into_v1_pdf"]) for row in figures),
        "v1_compiled_figure_assets_with_author_output_correspondence": sum(bool(row["compiled_into_v1_pdf"]) for row in figures),
        "v1_published_plotted_result_units_author_output_verified": sum(int(row["published_plotted_result_units"]) for row in figures if row["compiled_into_v1_pdf"]),
        "v1_published_plotted_result_units_regenerated": 0,
        "v3_plotted_bars_lines_points": 142,
        "v3_plotted_bars_lines_points_regenerated": 0,
        "v1_source_component_execution_passed": bool(execution.get("deterministic_component_harness_passed")),
        "v1_component_execution_is_paper_result_replication": False,
        "v3_source_files_recovered": 0,
        "official_source_archives_hash_verified": 3,
        "manuscript_rebuilds_deterministic": all(row["rebuild_runs_byte_identical"] for row in manuscripts),
        "manuscript_rebuilds_visual_qa_passed": all(row["visual_qa"]["status"].startswith("passed_") for row in manuscripts),
        "manuscript_rebuilds_are_result_replication": False,
        "provider_primary_sources_audited": 6,
        "fama_french_archive_hash_verified": True,
        "llm_calls_made": 0,
        "paper_evidence_route_v1_v2": "public_code_available_incomplete_author_source",
        "paper_evidence_route_v3": "paper_only_underspecified_no_released_v3_implementation",
    }
    readme = """# MACI multi-version paper-level replication audit

Overall verdict: **not reproduced end to end**.

The same arXiv identifier contains two different experiments. Versions 1--2
describe a four-expert GPT-4o system over 2023--2024. Version 3 replaces it
with three architectures, four capability variants, three model families, and
calendar-2025 data. Evidence is therefore never transferred across lineages.

## Versions 1--2

An author-owned repository and a pre-submission commit are recovered. The
source is genuine and substantial, and all 16 compiled manuscript figure
assets have author-output correspondence: 12 are byte-identical, one is
pixel-identical, and the remaining result plots preserve their vector geometry
through label or horizontal-layout changes. The published quantitative figure
content is therefore strongly verified as author output. It is **not
regenerated**: raw/processed data, exact weekly universe, checkpoints, fine-
tuned model IDs, instantiated requests/responses, prediction records, and
portfolio arrays are absent. **Zero of 321** table units and **zero of 21**
plotted quantitative result units regenerate from released inputs.

The untouched source also fails closed. Its declared Python >=3.9.15 contract
cannot parse two `match` statements on 3.9. A compatible 3.11 environment
compiles, but the raw import stops on the gitignored `environ/constants.py`.
A clearly labelled reconstruction using the later author version of that one
file permits deterministic source-component checks only; it cannot execute the
paper runner because data, records, and checkpoints are missing.

## Version 3

The author repository contains no implementation of the v3 hierarchical,
collaborative, or debate systems and no memory/RAG/skill runtime. **Zero of
442** table units and **zero of 142** plotted bars/lines/points regenerate.
The table-implied risk-free rate is approximately zero rather than the cited
Fama--French T-bill series; 20/23 bear rows also cannot be computed from the
same regime-conditioned path under the printed cumulative-return/MDD
definitions. Provider release dates and cutoffs do not support the blanket
claim that every calendar-2025 observation is strictly outside every model's
training distribution.

Arithmetic checks, manuscript rebuilds, prompt inspection, source compilation,
component execution, and figure correspondence receive no end-to-end result
credit.

## Manuscript reconstruction

All three official PDFs and source archives are hash-pinned. Two independent
builds per version are byte-identical (14 pages for v1/v2 and 10 for v3), final
logs have no unresolved citations/references or TeX errors, and every official
and rebuilt page passed a full-document visual contact-sheet review. Normalized
official/rebuilt token-multiset overlap is above 99.7% for every version. These
checks establish faithful document reconstruction only; they do not recover
any missing experimental data, model records, or result lineage.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256_file(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
