#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for Strat-LLM.

The official arXiv PDF and six-file TeX bundle are strong document evidence,
but the advertised project page is a 404 and no attributable implementation,
data snapshot, prompt set, action log, or result array was recovered.  The
paper also describes the experiment as live-forward during 2025 while naming
models first released after the stated windows.  This audit therefore gives
document and explicitly bounded procedure-component credit while keeping
native result reproduction at zero.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/strat_llm_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/stratllm"
WORK_ID = "CensusArxiv260506024"
SYSTEM_ID = "SYS-STRAT-LLM"
ARXIV_ID = "2605.06024"

PINS = {
    "raw/abs.html": "7849af7872ab0545cbf209eab1122700e8ea771e2822a136849ea8219050038a",
    "raw/abs-repeat.html": "7849af7872ab0545cbf209eab1122700e8ea771e2822a136849ea8219050038a",
    "raw/api.xml": "2476f54368ce21b3a87d860f586ba455776f80e6c09c73a0b0756742f5bd4d71",
    "raw/paper.pdf": "277597d5da577c628aa589bea40c77c2dfabe70e15b990466307aa1495ace9ab",
    "raw/paper-repeat.pdf": "277597d5da577c628aa589bea40c77c2dfabe70e15b990466307aa1495ace9ab",
    "raw/source.tar": "902b798ce49e59d1f88b48a34219fbfcba25b6410f323bf060f502e07fd1585a",
    "raw/source-repeat.tar": "902b798ce49e59d1f88b48a34219fbfcba25b6410f323bf060f502e07fd1585a",
    "source/conference_101719.tex": "1009974ba3d382701abdb360ee43674f0c825ff1e28f8894615eb8da075fe93f",
    "source/conference_101719.pdf": "e828ad697743078606276d5bb2b97e557fcb64eec98efe04402dd29b82699877",
    "discovery/project-page-body.html": "70d613e3acfba24fd2876fcbacaf639e1e111ef4d54baf70761c47673f37d6a3",
    "discovery/project-page-headers.txt": "01f77fd38a7260905d2eb6e007113dc86b543ca269c4553ca49087fcb380b35d",
    "discovery/project-page-status.txt": "9fa0918a8a29e54b9abd08496dd8fcec439a2f148588ee437700e91823bd1ae4",
    "discovery/github-code-arxiv.json": "cdc009451954c485e48e819a578e6d042d6aa4eec20ea488d595805f64c660d1",
    "discovery/github-code-title.json": "76eb3b98313cbaf943cfc521cce0cd1538d9ded127754dee82a32f9f19bbd295",
    "discovery/github-repositories-author.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-repositories-strat-llm.json": "e7b3ac80cc7b9425fcd6137cc1a9562e1ae6227f2503f5abe6492c46c8236e3e",
    "discovery/users_Strat-LLM.json": "c09de5d1ccc2828cfa7726bfe2c9ffcb3f4dda38ca04a2bd286f9718ef6ccf05",
    "discovery/repos_Strat-LLM_Strat-LLM.github.io.json": "021c328a8157d51f61925f4e35b83bc151a11127d65d542bc81b069e6e6dd38b",
    "discovery/hf-model-search.json": "b43f7911f77be5c167319f95812c75e4027ac4e7a88ae0c899a7e380b3c32dfa",
    "discovery/hf-dataset-search.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "primary_external/anthropic-claude-sonnet-4-5.html": "6724256451b7fc12a7031560faf4bcea8f7e8cbbf6e87f04764e01b3014960b7",
    "primary_external/deepseek-updates.html": "7da0928c2f0deee224dab50148cc3cfb093ae0c9adc90e6c33e20aa3f0f80643",
    "primary_external/hf-Qwen3.5-122B-A10B.json": "935b9d0063c37f66271477fe3fce66a6616787eca0bef9bac310e0e62e652b99",
    "primary_external/hf-Qwen3.5-35B-A3B.json": "439f30ecb6b7b16f9c79ffc36436d31ea91884f6597597db167dcaf215e9f023",
    "primary_external/hf-Qwen3.5-9B.json": "68a5557a3001f322b9d5dc8bc17dbfe537f09ffb96d288e178bced536a00a46b",
    "primary_external/google-gemini-3-1-pro.html": "51440cca945243db231b5d594bc3f2c5ad71185606f7908fa15d008da4244b02",
    "primary_external/kimi-blog-index.html": "18e5edfae1a0720aae7eaf4cfca5f9f41b4c48e13f64f29e12eeab652bcfb6ce",
    "primary_external/minimax-m2-5.html": "ffcc0b2572892d9088519ec812ccb3504bd9cec000f5af8a42edd27a0cdec487",
    "primary_external/openai-gpt-5-4-api.html": "15560e6e465027fe91feaa1db124f03878e42ebd2136d4cc1897399c101239be",
    "primary_external/zai-glm-5-js.js": "564335f7c416d9080e613f9d1a59299b934bd466de5706e1779b7bed96965b1e",
}

SOURCE_MEMBERS = {
    "00README.json",
    "IEEEtran.cls",
    "conference_101719.tex",
    "framework.pdf",
    "references.bib",
    "scaling_curve.pdf",
}

TABLE1_METRICS = ("TR_pct", "SR", "MDD_pct", "Vol_pct", "WR_pct", "alpha_pct")
MARKETS = ("A-shares", "US Stocks")
FIGURE2_VALUES = {
    ("Qwen3.5-9B", "Strict"): 9.48,
    ("Qwen3.5-9B", "Guided"): 8.15,
    ("Qwen3.5-35B-A3B", "Strict"): 12.33,
    ("Qwen3.5-35B-A3B", "Guided"): 10.55,
    ("Qwen3.5-122B-A10B", "Strict"): 8.48,
    ("Qwen3.5-122B-A10B", "Guided"): 13.68,
}

MODEL_RELEASES = (
    ("GPT-5.4", "2026-03-05", "primary_external/openai-gpt-5-4-api.html", "gpt-5.4-2026-03-05"),
    ("Gemini-3.1-Pro", "2026-02-19", "primary_external/google-gemini-3-1-pro.html", 'article:published_time\" content=\"2026-02-19'),
    ("Qwen3.5-9B", "2026-02-27", "primary_external/hf-Qwen3.5-9B.json", "2026-02-27T12:58:26.000Z"),
    ("Qwen3.5-35B-A3B", "2026-02-24", "primary_external/hf-Qwen3.5-35B-A3B.json", "2026-02-24T09:39:25.000Z"),
    ("Qwen3.5-122B-A10B", "2026-02-24", "primary_external/hf-Qwen3.5-122B-A10B.json", "2026-02-24T09:43:37.000Z"),
    ("GLM-5", "2026-02-12", "primary_external/zai-glm-5-js.js", "date:`2026-02-12`"),
    ("MiniMax-M2.5", "2026-02-12", "primary_external/minimax-m2-5.html", 'datePublished\":\"2026-02-12'),
    ("Kimi-K2.5", "2026-01-27", "primary_external/kimi-blog-index.html", "2026/01/27"),
    ("DeepSeek-V3.2", "2025-12-01", "primary_external/deepseek-updates.html", "date-2025-12-01"),
    ("Claude-Sonnet-4.5", "2025-09-29", "primary_external/anthropic-claude-sonnet-4-5.html", "Sep 29, 2025"),
)


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
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")

    with tarfile.open(scratch / "raw/source.tar", "r:*") as archive:
        members: set[str] = set()
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe source member: {member.name}")
            if member.isfile():
                members.add(pure.name)
    if members != SOURCE_MEMBERS:
        raise ValueError(f"unexpected official source members: {sorted(members)}")

    status = (scratch / "discovery/project-page-status.txt").read_text().splitlines()
    if status[:2] != ["404", "https://Strat-LLM.github.io/"]:
        raise ValueError(f"project page status changed: {status}")

    api = (scratch / "raw/api.xml").read_text(encoding="utf-8")
    required = (
        "http://arxiv.org/abs/2605.06024v1",
        "2026-05-07T11:17:23Z",
        "Wenliang Huang",
        "Zengyi Yu",
        "Accepted by the 2026 International Joint Conference on Neural Networks",
    )
    if not all(value in api for value in required):
        raise ValueError("canonical arXiv metadata does not match the audited v1 record")

    for model, _, source, marker in MODEL_RELEASES:
        if marker not in (scratch / source).read_text(encoding="utf-8", errors="ignore"):
            raise ValueError(f"release marker for {model} absent from {source}")
    return {"source_members": sorted(members), "project_page_status": 404}


def clean_tex_cell(value: str) -> tuple[str, float]:
    value = re.sub(r"\\cellcolor\{[^}]+\}", "", value)
    value = value.replace(r"\textbf", "").replace(r"\textit", "")
    value = value.replace("$", "").replace("{", "").replace("}", "")
    value = value.replace(r"\_", "_").replace(r"$-$", "-")
    value = value.replace(r"\\", "")
    value = value.replace("−", "-").strip()
    if value.startswith("-"):
        rendered = "-" + value[1:].strip()
    else:
        rendered = value
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", rendered):
        raise ValueError(f"cannot parse numeric TeX cell: {value!r}")
    return rendered, float(rendered)


def table_section(tex: str, label: str) -> str:
    position = tex.index(r"\label{" + label + "}")
    start = tex.rfind(r"\begin{table", 0, position)
    end = tex.index(r"\end{table", position)
    end = tex.index("}", end) + 1
    return tex[start:end]


def parse_table1(tex: str) -> list[dict[str, Any]]:
    section = table_section(tex, "tab:strategy_market_comparison")
    rows: list[dict[str, Any]] = []
    panel = ""
    for line in section.splitlines():
        if "Panel A:" in line:
            panel = "Panel A"
        elif "Panel B:" in line:
            panel = "Panel B"
        if line.lstrip().startswith("%") or "&" not in line:
            continue
        fields = [part.strip() for part in line.split("&")]
        if len(fields) != 14 or not re.search(r"\d", fields[2]):
            continue
        model = fields[0].replace(r"\_", "_")
        strategy = fields[1]
        values = [clean_tex_cell(value) for value in fields[2:]]
        for market_index, market in enumerate(MARKETS):
            for metric_index, metric in enumerate(TABLE1_METRICS):
                rendered, numeric = values[market_index * 6 + metric_index]
                rows.append(
                    {
                        "table": "Table 1",
                        "panel": panel,
                        "model": model,
                        "strategy": strategy,
                        "market": market,
                        "metric": metric,
                        "rendered_value": rendered,
                        "numeric_value": numeric,
                        "duplicate_kind": "none",
                        "duplicate_of": "",
                        "native_pipeline_executed": False,
                        "native_result_regenerated": False,
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 168:
        raise ValueError(f"expected 168 Table 1 cells, found {len(rows)}")
    return rows


def parse_table2(tex: str, table1: list[dict[str, Any]]) -> list[dict[str, Any]]:
    section = table_section(tex, "tab:think_vs_nothink")
    current_model = ""
    rows: list[dict[str, Any]] = []
    table1_index = {
        (row["model"], row["strategy"], row["market"], row["metric"]): row
        for row in table1
    }
    for line in section.splitlines():
        if "&" not in line or line.lstrip().startswith("%"):
            continue
        fields = [part.strip() for part in line.split("&")]
        if len(fields) != 5 or not re.search(r"\d", fields[2]):
            continue
        first = fields[0]
        model_match = re.search(r"\\textbf\{([^}]+)\}", first)
        if model_match:
            current_model = model_match.group(1).replace(r"\_", "_")
        strategy = re.sub(r"\\textbf\{([^}]+)\}", r"\1", fields[1]).strip()
        for metric, raw in zip(("TR_pct", "SR", "MDD_pct"), fields[2:]):
            rendered, numeric = clean_tex_cell(raw)
            key = (current_model, strategy, "A-shares", metric)
            duplicate = key in table1_index and math.isclose(
                numeric, float(table1_index[key]["numeric_value"]), abs_tol=1e-12
            )
            rows.append(
                {
                    "table": "Table 2",
                    "panel": "",
                    "model": current_model,
                    "strategy": strategy,
                    "market": "A-shares",
                    "metric": metric,
                    "rendered_value": rendered,
                    "numeric_value": numeric,
                    "duplicate_kind": "exact_repeat_of_table1" if duplicate else "none",
                    "duplicate_of": "Table 1" if duplicate else "",
                    "native_pipeline_executed": False,
                    "native_result_regenerated": False,
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 27:
        raise ValueError(f"expected 27 Table 2 cells, found {len(rows)}")
    if sum(row["duplicate_kind"] != "none" for row in rows) != 9:
        raise ValueError("expected nine exact Table 1 repeats in Table 2")
    return rows


def figure_rows(table_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tr_index = {
        (row["model"], row["strategy"]): row
        for row in table_rows
        if row["table"] == "Table 1" and row["market"] == "A-shares" and row["metric"] == "TR_pct"
    }
    output = []
    for (model, strategy), numeric in FIGURE2_VALUES.items():
        duplicate = (model, strategy) in tr_index and math.isclose(
            numeric, float(tr_index[(model, strategy)]["numeric_value"]), abs_tol=1e-12
        )
        output.append(
            {
                "figure": "Figure 2",
                "model": model,
                "strategy": strategy,
                "metric": "TR_pct",
                "rendered_value": f"{numeric:.2f}%",
                "numeric_value": numeric,
                "duplicate_kind": "exact_repeat_of_table1" if duplicate else "none",
                "duplicate_of": "Table 1" if duplicate else "",
                "underlying_array_released": False,
                "native_result_regenerated": False,
                "paper_result_credit": False,
            }
        )
    if sum(row["duplicate_kind"] != "none" for row in output) != 2:
        raise ValueError("expected two Figure 2 values to repeat Table 1")
    return output


def prompt_rows() -> list[dict[str, Any]]:
    descriptions = {
        "Free": "zero-shot native financial intuition; no external strategy constraints",
        "Guided": "S1-S4 supplied as references; model may adjust using real-time news",
        "Strict": "must adhere to S1-S4; rationale must cite specific strategy clauses",
    }
    return [
        {
            "mode": mode,
            "paper_description": description,
            "exact_system_prompt_recovered": False,
            "exact_user_prompt_recovered": False,
            "structured_output_schema_recovered": False,
            "runtime_fill_recovered": False,
            "model_request_recovered": False,
            "native_prompt_call_credit": False,
        }
        for mode, description in descriptions.items()
    ]


def strategy_rows() -> list[dict[str, Any]]:
    values = (
        ("S1", "Short-Term Reversal", "mean reversion after short-term plunges", "no plunge threshold, lookback, exit, sizing, or tie rule", False),
        ("S2", "Breakout Momentum", "buy when price breaks the 3-day high", "entry threshold only; price field, exit, sizing, and tie rule absent", True),
        ("S3", "Volatility Compression", "identify accumulation in low-volatility zones", "volatility estimator, thresholds, entry, exit, and sizing absent", False),
        ("S4", "Price-Volume Confirmation", "validate upward price trends with price-volume theory", "trend and volume definitions, thresholds, entry, exit, and sizing absent", False),
    )
    return [
        {
            "strategy_id": sid,
            "name": name,
            "paper_description": description,
            "missing_operational_details": missing,
            "has_one_exact_entry_threshold": threshold,
            "fully_executable_definition_recovered": False,
            "native_strategy_credit": False,
        }
        for sid, name, description, missing, threshold in values
    ]


def metric_rows() -> list[dict[str, Any]]:
    values = (
        ("TR", "Total Return", "reported in tables but methodology names Annualized Return"),
        ("AR", "Annualized Return", "named in methodology but absent from result tables"),
        ("alpha", "Alpha", "benchmark and formula absent"),
        ("SR", "Sharpe Ratio", "frequency, annualization, risk-free rate, and dispersion convention absent"),
        ("Sortino", "Sortino Ratio", "formula and downside target absent; not reported in tables"),
        ("MDD", "Maximum Drawdown", "formula/sign convention absent"),
        ("Calmar", "Calmar Ratio", "formula absent; not reported in tables"),
        ("Vol", "Volatility", "frequency and annualization absent"),
        ("WR", "Win Rate", "trade definition and denominator absent"),
    )
    return [
        {
            "symbol": symbol,
            "name": name,
            "paper_status": status,
            "exact_formula_recovered": False,
            "paper_input_array_recovered": False,
            "native_metric_credit": False,
        }
        for symbol, name, status in values
    ]


def method_rows() -> list[dict[str, Any]]:
    rows = (
        ("markets", "partial", "A-share and U.S. equity markets named"),
        ("asset_universe", "missing", "no ticker or membership list"),
        ("market_windows_outer", "partial", "US 2025-01-01..06-30; A-share 2025-06-01..09-30"),
        ("short_window_dates", "missing", "three approximately 15-day windows per market, dates absent"),
        ("long_window_dates", "missing", "approximately 90-day windows, exact dates absent"),
        ("price_data", "missing", "minute-level prices named; vendor, fields, timezone, adjustments, and snapshot absent"),
        ("news_data", "missing", "real-time news named; vendor, corpus, timestamps, NLP model, and snapshot absent"),
        ("annual_reports", "missing", "annual reports named; filings, retrieval, and hierarchical summarizer absent"),
        ("point_in_time_controls", "paper_only", "chronology asserted without released input timestamps"),
        ("initial_capital", "recovered", "1,000,000 local currency per market"),
        ("action_space", "recovered", "-1 sell, 0 hold, 1 buy"),
        ("execution_timing", "recovered", "decision T; execution at T+1 open"),
        ("buy_sizing", "missing", "cash truncation stated but desired buy volume rule absent"),
        ("sell_sizing", "partial", "model-designated volume, output schema absent"),
        ("transaction_costs", "missing", "costs deducted but rate/schedule absent"),
        ("slippage", "missing", "not specified"),
        ("shorting_leverage", "missing", "not specified"),
        ("corporate_actions", "missing", "not specified"),
        ("portfolio_aggregation", "missing", "asset metrics averaged; account construction/weighting absent"),
        ("exact_prompts", "missing", "three prose mode descriptions only"),
        ("strategy_library", "partial", "four motifs; only S2 has one numeric entry lookback"),
        ("structured_output_schema", "missing", "action/rationale named, exact schema and volume representation absent"),
        ("model_identifiers", "partial", "display names only; immutable API snapshots/checkpoints absent"),
        ("model_call_parameters", "missing", "temperature, top-p, token limits, reasoning settings, and retries absent"),
        ("sampling_configuration", "missing", "called standardized efficient sampling without values"),
        ("random_seeds", "missing", "no seeds or repeated-run protocol"),
        ("runtime_requests_responses", "missing", "no immutable calls or responses"),
        ("broker_implementation", "missing", "described as identical, implementation/config absent"),
        ("metric_formulas", "missing", "metric names only; TR/AR mismatch"),
        ("alpha_benchmark", "missing", "not specified"),
        ("actions_orders_fills", "missing", "not released"),
        ("cash_holdings_nav_returns", "missing", "not released"),
        ("raw_result_arrays", "missing", "not released"),
        ("native_source", "missing", "advertised project page is 404; no attributable source recovered"),
        ("environment_dependencies", "missing", "not released"),
    )
    return [
        {"dimension": dimension, "status": status, "evidence": evidence}
        for dimension, status, evidence in rows
    ]


def release_rows() -> list[dict[str, Any]]:
    outer_end = "2025-09-30"
    output = []
    for model, release, source, marker in MODEL_RELEASES:
        output.append(
            {
                "model_family": model,
                "first_public_date_used_for_audit": release,
                "after_latest_stated_evaluation_date": release > outer_end,
                "evidence_source": source,
                "evidence_marker": marker,
                "literal_live_forward_2025_possible": False,
                "defensible_interpretation": "post-hoc chronological replay of 2025 data",
            }
        )
    return output


def consistency_rows(table_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def result(check: str, status: str, detail: str) -> dict[str, str]:
        return {"check": check, "status": status, "detail": detail}

    index = {
        (row["model"], row["strategy"], row["market"], row["metric"]): float(row["numeric_value"])
        for row in table_rows if row["table"] == "Table 1"
    }
    checks = [
        result(
            "literal_live_forward_2025",
            "contradicted_by_public_model_chronology",
            "all ten model identities/families represented in the result tables have public dates after at least part of the stated 2025 windows; eight are first public in 2026",
        ),
        result(
            "defensible_temporal_interpretation",
            "post_hoc_chronological_replay_possible_but_unverified",
            "sequential feeding of frozen 2025 inputs could avoid look-ahead, but inputs, timestamps, calls, and actions are absent",
        ),
        result(
            "gpt_mdd_reduction",
            "passes_displayed_arithmetic",
            f"20.83 to 11.66 is a {100 * (20.83 - 11.66) / 20.83:.2f}% relative reduction",
        ),
        result(
            "best_us_total_return",
            "passes_table_check",
            f"GPT-5.4 Strict TR {index[('GPT-5.4', 'Strict', 'US Stocks', 'TR_pct')]:.2f}% is the highest displayed US TR",
        ),
        result(
            "best_us_alpha",
            "prose_overstates_joint_best_performance",
            "GPT-5.4 Strict has alpha 6.72%, below Kimi-K2.5_nothink 12.02% and GLM-5_nothink 8.83%",
        ),
        result(
            "highlight_caption",
            "incomplete_highlighting",
            "caption promises best and second results within each metric, but highlighting appears only for TR and MDD, not SR, Vol, WR, or alpha",
        ),
        result(
            "universal_strict_insurance",
            "under_supported_by_unpaired_rows",
            "most Table 1 models expose only one mode; a universal within-model claim cannot be tested",
        ),
        result(
            "standard_models_require_strict",
            "overbroad_relative_to_ablation",
            "Kimi-K2.5_nothink peaks at 12.05% TR in Guided rather than Strict mode",
        ),
        result(
            "disposition_effect",
            "not_identified_by_released_statistics",
            "win rate, return, and MDD do not identify realized-gain versus realized-loss holding behavior without trades",
        ),
        result(
            "temporal_horizon_significance",
            "unsupported_without_results_or_test",
            "paper says 90-day windows significantly outperform 15-day windows but publishes no horizon table, uncertainty, or statistical test",
        ),
        result(
            "metric_naming",
            "tr_ar_definition_gap",
            "methodology names Annualized Return while tables and figure report Total Return; no conversion or formula is supplied",
        ),
    ]
    return checks


def discovery_rows(scratch: Path) -> list[dict[str, Any]]:
    gh_arxiv = json.loads((scratch / "discovery/github-code-arxiv.json").read_text())
    gh_title = json.loads((scratch / "discovery/github-code-title.json").read_text())
    gh_author = json.loads((scratch / "discovery/github-repositories-author.json").read_text())
    hf_models = json.loads((scratch / "discovery/hf-model-search.json").read_text())
    hf_datasets = json.loads((scratch / "discovery/hf-dataset-search.json").read_text())
    return [
        {
            "route": "advertised_project_page",
            "result_count": 1,
            "finding": "GitHub Pages 404",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded current observation; not proof that private, deleted, moved, or unindexed material never existed",
        },
        {
            "route": "github_code_arxiv_id",
            "result_count": gh_arxiv["total_count"],
            "finding": "returned paper indexes/citations, not attributable implementation",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded indexed GitHub search; not proof that private, deleted, moved, or unindexed material never existed",
        },
        {
            "route": "github_code_exact_title_phrase",
            "result_count": gh_title["total_count"],
            "finding": "returned paper indexes/citations, not attributable implementation",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded indexed GitHub search; not proof that private, deleted, moved, or unindexed material never existed",
        },
        {
            "route": "github_repository_author_title",
            "result_count": gh_author["total_count"],
            "finding": "zero repositories",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded indexed GitHub search; not proof that private, deleted, moved, or unindexed material never existed",
        },
        {
            "route": "github_pages_owner_and_repo",
            "result_count": 0,
            "finding": "advertised owner and repository API routes not found",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded current API observation; not proof that prior or private artifacts never existed",
        },
        {
            "route": "huggingface_model_search",
            "result_count": len(hf_models),
            "finding": "three lexical collisions, none attributable to paper/authors",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded indexed Hugging Face search; not proof that private, deleted, moved, or unindexed material never existed",
        },
        {
            "route": "huggingface_dataset_search",
            "result_count": len(hf_datasets),
            "finding": "zero datasets",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded indexed Hugging Face search; not proof that private, deleted, moved, or unindexed material never existed",
        },
    ]


def build(scratch: Path, output: Path) -> dict[str, Any]:
    validated = validate_inputs(scratch)
    tex = (scratch / "source/conference_101719.tex").read_text(encoding="utf-8")
    table1 = parse_table1(tex)
    table2 = parse_table2(tex, table1)
    table_rows = table1 + table2
    figures = figure_rows(table_rows)
    prompts = prompt_rows()
    strategies = strategy_rows()
    metrics = metric_rows()
    methods = method_rows()
    releases = release_rows()
    consistency = consistency_rows(table_rows)
    discovery = discovery_rows(scratch)

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "published_result_ledger.csv", table_rows)
    write_csv(output / "figure_result_ledger.csv", figures)
    write_csv(output / "prompt_inventory.csv", prompts)
    write_csv(output / "strategy_specification_audit.csv", strategies)
    write_csv(output / "metric_specification_audit.csv", metrics)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "model_release_chronology.csv", releases)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "discovery_evidence.csv", discovery)

    procedure_component = {
        "component": "T+1 action-index and cash-truncation semantics",
        "declared_fixture": {
            "actions": [-1, 0, 1],
            "decision_days": [0, 1, 2],
            "execution_days": [1, 2, 3],
            "cash": 1000.0,
            "open_price": 101.0,
            "transaction_cost_rate": 0.0,
        },
        "computed": {
            "action_mapping": {"-1": "sell", "0": "hold", "1": "buy"},
            "maximum_affordable_integer_shares": math.floor(1000.0 / 101.0),
            "remaining_cash": 1000.0 - math.floor(1000.0 / 101.0) * 101.0,
        },
        "paper_cost_rate_used": False,
        "native_broker_used": False,
        "paper_input_used": False,
        "paper_result_credit": False,
        "boundary": "conditional synthetic procedure component only; buy sizing, costs, and broker implementation are unreleased",
    }
    write_json(output / "procedure_component_execution.json", procedure_component)

    provenance = {
        "arxiv": {
            "id": ARXIV_ID,
            "version": "v1",
            "submitted_utc": "2026-05-07T11:17:23Z",
            "authors": ["Wenliang Huang", "Zengyi Yu"],
            "venue_comment": "Accepted by IJCNN 2026",
            "pdf_pages": 6,
            "source_file_count": 6,
            "source_files": validated["source_members"],
            "repeated_downloads_byte_identical": True,
            "source_rebuild_completed": True,
            "rebuild_pages": 6,
            "rebuild_extracted_token_multiset_jaccard": 0.9984609465178915,
            "visual_qa": {"pages_inspected": 6, "unreadable_or_clipped_pages": 0},
        },
        "release_boundary": {
            "advertised_project_page_status": 404,
            "attributable_implementation_recovered": False,
            "data_snapshot_recovered": False,
            "exact_prompts_recovered": False,
            "runtime_calls_recovered": False,
            "actions_orders_fills_recovered": False,
            "nav_returns_arrays_recovered": False,
            "bounded_negative_search_is_proof_of_nonexistence": False,
        },
    }
    write_json(output / "source_provenance.json", provenance)

    readme = """# Strat-LLM paper-faithfulness audit

This fail-closed audit pins the canonical arXiv v1 PDF, API record, and six-file
source bundle for *Strat-LLM: Stratified Strategy Alignment for LLM-based Stock
Trading with Real-time Multi-Source Signals*.  The source rebuilds unmodified to
the published six-page layout with 0.99846 extracted-token multiset Jaccard, and
all six original pages were visually inspected without clipping or unreadable
content.

## Honest reproduction boundary

The native Strat-LLM experiment is **not reproduced**.  The advertised project
page returns HTTP 404, and bounded GitHub/Hugging Face searches recovered no
attributable implementation, dataset, or output release.  The paper/source ship
no stock list, exact window dates, point-in-time price/news/report snapshot,
complete strategy rules, prompts, immutable model requests, sampling settings,
broker/cost configuration, seeds, actions, orders, fills, holdings, NAV, returns,
or raw result arrays.  Consequently 0/186 unique table cells and 0/4 additional
unique Figure 2 values receive native paper-result credit.  The synthetic T+1
component is explicitly conditional and receives zero result credit.

## Published evidence denominator

- Table 1: 168 numeric cells.
- Table 2: 27 numeric cells, including nine exact repeats of Table 1.
- Figure 2: six numeric points, including two exact repeats of Table 1.
- Unique displayed empirical numeric units: 190.
- Native units regenerated: 0/190.

## Temporal finding

The literal claim of a live-forward experiment during the stated 2025 windows
is contradicted by public model chronology.  All ten model identities or
families represented in the result tables became public after at least part of
those windows, and eight first became public in 2026.  A later chronological
replay over frozen 2025 data could still avoid
look-ahead bias, but no input snapshot, timestamps, request logs, or actions were
released to verify that weaker interpretation.

Negative artifact searches are bounded current observations, not proof that
private, deleted, moved, or unindexed artifacts never existed.  No local proxy
or independent reimplementation is credited as Strat-LLM.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    manifest: dict[str, Any] = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_version_audited": "v1",
        "official_pdf_and_source_recovered": True,
        "official_document_rebuild_completed": True,
        "advertised_project_page_status": 404,
        "attributable_native_implementation_recovered": False,
        "published_numeric_table_cells": len(table_rows),
        "published_unique_numeric_table_cells": sum(row["duplicate_kind"] == "none" for row in table_rows),
        "published_figure_numeric_points": len(figures),
        "published_additional_unique_figure_points": sum(row["duplicate_kind"] == "none" for row in figures),
        "published_unique_empirical_numeric_units": sum(row["duplicate_kind"] == "none" for row in table_rows + figures),
        "native_empirical_units_regenerated": 0,
        "full_end_to_end_pipeline_reproduced": False,
        "literal_live_forward_2025_claim_supported": False,
        "post_hoc_chronological_replay_verified": False,
        "procedure_component_executed": True,
        "procedure_component_paper_result_credit": False,
        "paper_evidence_route": "paper_only_underspecified",
        "output_sha256": {},
    }
    output_files = sorted(
        path for path in output.iterdir()
        if path.is_file() and path.name != "manifest.json"
    )
    manifest["output_sha256"] = {path.name: sha256(path) for path in output_files}
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
    if args.strict and not manifest["full_end_to_end_pipeline_reproduced"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
