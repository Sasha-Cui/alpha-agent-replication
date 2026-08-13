#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for the XALPHA paper."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/xalpha_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/xalpha"
WORK_ID = "CensusArxiv260708332"
SYSTEM_ID = "SYS-XALPHA"
ARXIV_ID = "2607.08332"

PINS = {
    "primary/official.pdf": "3ceda64711043a1a1cf18ea0d0f324f1b8dc74b71ac16c544551318f1a86e069",
    "primary/official.txt": "4c81a78b4d23d3f639b74c92ab35d3cd98e635958c9dc9f2e021b019f2140147",
    "primary/source.tar": "1403833bbcbc8d50f18822a23d8b2f2687be35476f205b0f34be7ce71e414e64",
    "primary/rebuilt.pdf": "be7922f9473efc4c2c02465ca0e6924b3550802f2393bbdbad8ce817d5b3b62f",
    "primary/rebuilt.txt": "52585d078f3ceeb05e32737f5309e7d51e033f9200d3b64451ad3d1929a48801",
    "primary/arxiv-api.xml": "e66c1d8f4ba95a4cfebd53a41d5920eabeb99db9ea4650d61d68c72e778a199c",
    "primary/arxiv-abs.html": "786b96ba1e305f395c95689b8812b657c028b8dae198f01f64471c04bf406bc2",
    "source/neurips_2026.tex": "9a64634b691465cdf9646ba29964487502bd5e2bc74638344cb998dcd40c7945",
    "source/appendix/case_studies.tex": "a7205912a1765753b896236b60d25dfbda6476b5ce3743fc6edfb9dc35b9a1b7",
    "source/appendix/experimental_protocol.tex": "a451f206132dd2f27d8cca24867fcbdc840950c6956505634bd8b0b05da5bb4d",
    "source/appendix/evaluation_details.tex": "b5f4873256a65db4dc211ebcd03947ae77acf3074b04e5fa917c4e50cc34c0a5",
    "source/appendix/factor_selection_details.tex": "16ec51448e6998ba3a5d2106305a70afdf7c31dbac44f7237855e06ac5952fee",
    "source/appendix/prompt_excerpts.tex": "e688a3a1d3ef35d8cbcb1ac344cea4d85511e5dddd8e806126f5712343ab44a6",
    "source/appendix/primitive_features.tex": "464bf9c32fc5ac62f638ef8283bad4f827bf1cad49b4736f1adbc7883518ad67",
    "source/appendix/runtime_pseudocode.tex": "b9697c48197782cb440072a88b8edfb88a1b1ec6ac88750b9a23ff759bf7fc76",
    "source/figures/baseline_cumulative_ar_curves_qlib_CSI300_v3_h10.png": (
        "63bed73e803fc49fa2e46b79f5b7b72b8b863992f92dbf4ccfeecb696e0d8194"
    ),
    "source/figures/single_theme_50_factor_corr_heatmap.png": (
        "6d1fc8def2d68323edcffe11784c60c67e087e5aeea38e52ceb326f5a948ddd6"
    ),
    "source/figures/six_theme_10_each_factor_corr_heatmap.png": (
        "747df1e82589918377504a097025b634f349369984a7eb1e02de88fcb44d631b"
    ),
    "source/figures/XAlpha.pdf": "ddf6d0587326c86eb50a3ce064dcbc21657bc45cfff58e3515e488ef36a3d7b8",
    "source/figures/RMA_Layer.pdf": "98f3b8e21105c904a5a096a70d7ded6a104e05edeb83b75586f6400178a7d562",
    "discovery/github-users-uwFengyuan.json": (
        "52350b320c5ca234980578faa9ecaa1574f9dc3fe6bb496b60d7dc5671e49c17"
    ),
    "discovery/github-user-repos.json": "a6161bb8a9483384ca4895773f4d5c6503e5b211f33f2a7fccbb1da4103fd265",
    "discovery/github-repos-uwFengyuan-XAlpha_Prompt.json": (
        "4f50e254a719a6b1b06b529bdaa08980e4acf0878aad0090cba7771f6ebdf0b9"
    ),
    "discovery/github-repos-XAlphaPrompt.json": (
        "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f"
    ),
    "discovery/github-repos-XALPHAalphadiscovery.json": (
        "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f"
    ),
    "discovery/github-repos-260708332.json": (
        "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f"
    ),
    "discovery/github-repos-MemoryDrivenAIQuantResearcher.json": (
        "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f"
    ),
    "discovery/github-code-XAlphaPrompt.json": (
        "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f"
    ),
    "discovery/github-code-regimeovershootpressuredecay20dma20vol20.json": (
        "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f"
    ),
    "discovery/github-code-260708332.json": (
        "0de20cf1d79f5955a0fdfabb51f4e8de26ac827e88f3cb51e87a990a03e84bd3"
    ),
    "discovery/author-homepage.html": "e0823bd7345c79d85b71207de40a5028029326d16b723d4efa9b78c431c4c89c",
    "discovery/huggingface-models-xalpha.json": (
        "3e0730c3ff5702f6fb5e9afef2729fde5ef75d98fd442ef7353bf8c759b5de42"
    ),
    "discovery/huggingface-datasets-xalpha.json": (
        "864847f3a441576f230dbb05e6e7424a6b5085aebf1f0836d4ee02bae0d9da35"
    ),
    "discovery/hf-xalpha-ablation-info.json": (
        "f7b33bef732a7706e8762c4ff5296e337bb6b66f83e817a664c72ad1a61ed889"
    ),
    "discovery/hf-xalpha-ablation-tree.json": (
        "b581196a6ff9979372acca7530af4b22bdd0965debb31ee71c0cbaf2c0a2e8df"
    ),
    "discovery/hf-antony-fu-profile.json": (
        "91c3f30a50b429bef6677b7e84b3a87a44f8f5ff8a67545dd101dc41cc10f44d"
    ),
}

METHODS = (
    "Ridge",
    "Random Forest",
    "LightGBM",
    "XGBoost",
    "CatBoost",
    "AdaBoost",
    "MLP",
    "Transformer",
    "GRU",
    "LSTM",
    "CNN",
    "Alpha360",
    "AutoAgent",
    "AlphaAgent",
    "R&D-Agent(Q)",
    "CogAlpha",
    "XAlpha",
)
METRICS = ("IC", "RankIC", "ICIR", "RankICIR", "AR", "AER", "IR")


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
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def token_jaccard(left: str, right: str) -> float:
    a = Counter(re.findall(r"\w+", left.lower()))
    b = Counter(re.findall(r"\w+", right.lower()))
    return sum((a & b).values()) / sum((a | b).values())


def verify_pins(scratch: Path) -> None:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise ValueError(f"pin mismatch: {relative}={observed}; expected {expected}")


def main_table(source: str) -> dict[str, list[float]]:
    table_start = source.index(r"\multirow{6}{*}{Machine Learning}")
    table_end = source.index(r"\bottomrule", table_start)
    table = source[table_start:table_end]
    parsed: dict[str, list[float]] = {}
    rows = table.split(r"\\")
    aliases = {method: method for method in METHODS}
    aliases[r"R\&D-Agent(Q)"] = "R&D-Agent(Q)"
    aliases[r"\method{}"] = "XAlpha"
    for row in rows:
        matched = next((alias for alias in aliases if alias in row), None)
        if matched is None:
            continue
        values = [float(value) for value in re.findall(r"-?\d+\.\d{4}", row)]
        if len(values) != 7:
            raise ValueError(f"unexpected main-table row for {aliases[matched]}: {values}")
        parsed[aliases[matched]] = values
    if tuple(parsed) != METHODS:
        raise ValueError(f"main-table methods changed: {tuple(parsed)}")
    return parsed


def result_rows(source: str) -> list[dict[str, Any]]:
    table = main_table(source)
    rows: list[dict[str, Any]] = []
    for method, values in table.items():
        for metric, value in zip(METRICS, values):
            ranking = sorted(table, key=lambda name: table[name][METRICS.index(metric)], reverse=True)
            rows.append(
                {
                    "result_family": "main_comparison_table",
                    "unit_id": f"{method}:{metric}",
                    "method_or_panel": method,
                    "metric": metric,
                    "printed_value": f"{value:.4f}",
                    "rank_within_column": ranking.index(method) + 1,
                    "source_asset_recovered": True,
                    "raw_result_value_recovered": False,
                    "author_native_pipeline_executed": False,
                    "author_native_result_regenerated": False,
                    "paper_result_credit": False,
                    "blocking_reason": (
                        "no public XALPHA implementation, exact data snapshot, factor library, run state, "
                        "predictions, returns, or result arrays"
                    ),
                }
            )
    extra = (
        ("representative_factor", "train_val_ic", "representative factor", "IC", "0.0382"),
        ("representative_factor", "train_val_rankic", "representative factor", "RankIC", "0.0564"),
        ("representative_factor", "train_val_icir", "representative factor", "ICIR", "0.2622"),
        ("representative_factor", "train_val_rankicir", "representative factor", "RankICIR", "0.3593"),
        ("representative_factor", "test_ic", "representative factor", "IC", "0.0440"),
        ("representative_factor", "test_rankic", "representative factor", "RankIC", "0.0634"),
        ("representative_factor", "test_icir", "representative factor", "ICIR", "0.2311"),
        ("representative_factor", "test_rankicir", "representative factor", "RankICIR", "0.3188"),
        ("representative_factor", "ast_complexity", "representative factor", "raw AST complexity", "14.788"),
        ("heatmap_summary", "single_mean_abs", "single-theme heatmap", "mean absolute correlation", "0.234"),
        ("heatmap_summary", "single_median_abs", "single-theme heatmap", "median absolute correlation", "0.181"),
        ("heatmap_summary", "single_below_03", "single-theme heatmap", "abs correlation below 0.3", "68.0%"),
        ("heatmap_summary", "six_mean_abs", "six-theme heatmap", "mean absolute correlation", "0.142"),
        ("heatmap_summary", "six_median_abs", "six-theme heatmap", "median absolute correlation", "0.099"),
        ("heatmap_summary", "six_below_03", "six-theme heatmap", "abs correlation below 0.3", "87.1%"),
        ("runtime_claim", "factor_seconds", "main runtime", "seconds per factor", "15"),
        ("runtime_claim", "generation_minutes", "main runtime", "minutes per generation", "16"),
        ("runtime_claim", "cycle_hours", "main runtime", "hours per cycle", "3"),
        ("runtime_claim", "h100_count", "main runtime", "H100 GPUs", "2"),
    )
    for family, unit, panel, metric, value in extra:
        rows.append(
            {
                "result_family": family,
                "unit_id": unit,
                "method_or_panel": panel,
                "metric": metric,
                "printed_value": value,
                "rank_within_column": "",
                "source_asset_recovered": True,
                "raw_result_value_recovered": False,
                "author_native_pipeline_executed": False,
                "author_native_result_regenerated": False,
                "paper_result_credit": False,
                "blocking_reason": (
                    "printed claim or raster asset is present, but its author run record and raw values are absent"
                ),
            }
        )
    if len(rows) != 138:
        raise ValueError(f"published result denominator changed: {len(rows)}")
    return rows


def figure_rows(scratch: Path) -> list[dict[str, Any]]:
    definitions = (
        ("framework", "figures/XAlpha.pdf", 1, 0, "multi-brain framework schematic"),
        ("rma", "figures/RMA_Layer.pdf", 1, 0, "RMA hierarchy schematic"),
        (
            "cumulative_return",
            "figures/baseline_cumulative_ar_curves_qlib_CSI300_v3_h10.png",
            1,
            1,
            "held-out cumulative-return curves",
        ),
        (
            "single_theme_correlation",
            "figures/single_theme_50_factor_corr_heatmap.png",
            1,
            1,
            "50-factor correlation heatmap",
        ),
        (
            "six_theme_correlation",
            "figures/six_theme_10_each_factor_corr_heatmap.png",
            1,
            1,
            "60-factor correlation heatmap",
        ),
    )
    rows = []
    for figure, asset, panels, empirical, description in definitions:
        path = scratch / "source" / asset
        rows.append(
            {
                "figure": figure,
                "active_panels": panels,
                "empirical_panels": empirical,
                "description": description,
                "source_asset": asset,
                "source_asset_sha256": sha256(path),
                "source_asset_recovered": True,
                "raw_result_array_recovered": False,
                "author_native_regeneration": False,
                "paper_result_credit": False,
            }
        )
    return rows


def prompt_rows(prompt_source: str) -> list[dict[str, Any]]:
    pattern = re.compile(r"\\begin\{xpromptlisting\}\{([^}]*(?:\{[^}]*\}[^}]*)*)\}")
    titles = pattern.findall(prompt_source)
    rows = []
    for title in titles:
        if title.startswith("Shared ") or "Shared Factor-Generation" in title:
            category = "shared_block"
        elif title.startswith("Macro Brain"):
            category = "macro_agent"
        elif title.startswith("Micro Brain"):
            category = "micro_agent"
        elif title.startswith("Cross Brain"):
            category = "cross_agent"
        elif title.startswith("Utility"):
            category = "utility"
        else:
            raise ValueError(f"unexpected prompt title: {title}")
        start = prompt_source.index(r"\begin{xpromptlisting}{" + title + "}")
        end = prompt_source.index(r"\end{xpromptlisting}", start)
        body = prompt_source[start:end]
        rows.append(
            {
                "prompt_title": title.replace(r"\texttt{", "").replace("}", ""),
                "category": category,
                "paper_framework_recovered": True,
                "declares_json_contract": "JSON" in body,
                "full_runtime_template_recovered": False,
                "filled_runtime_prompt_recovered": False,
                "author_model_response_recovered": False,
                "paper_result_credit": False,
                "boundary": "paper labels these selected prompt excerpts; cited detailed prompt repository is 404",
            }
        )
    counts = Counter(row["category"] for row in rows)
    expected = {"shared_block": 2, "macro_agent": 6, "micro_agent": 9, "cross_agent": 4, "utility": 1}
    if counts != expected:
        raise ValueError(f"prompt inventory changed: {counts}")
    return rows


def extract_listing(source: str, label: str) -> str:
    marker = f"label={{{label}}}"
    location = source.index(marker)
    begin = source.rfind(r"\begin{lstlisting}", 0, location)
    code_start = source.index("\n", begin) + 1
    code_end = source.index(r"\end{lstlisting}", code_start)
    return source[code_start:code_end].rstrip() + "\n"


def controlled_frame() -> pd.DataFrame:
    count = 240
    phase = np.arange(count, dtype=float)
    close = 100.0 * np.exp(0.0007 * phase + 0.035 * np.sin(phase / 7.0) + 0.018 * np.cos(phase / 19.0))
    open_price = close * (1.0 + 0.004 * np.sin(phase / 5.0))
    high = np.maximum(open_price, close) * (1.01 + 0.002 * np.cos(phase / 11.0))
    low = np.minimum(open_price, close) * (0.99 - 0.002 * np.sin(phase / 13.0))
    volume = 1_000_000.0 * (1.0 + 0.2 * np.sin(phase / 9.0) + 0.1 * np.cos(phase / 17.0))
    index = pd.MultiIndex.from_arrays(
        [pd.date_range("2020-01-01", periods=count, freq="B"), ["CONTROL"] * count],
        names=["date", "ticker"],
    )
    frame = pd.DataFrame({"open": open_price, "high": high, "low": low, "close": close, "volume": volume}, index=index)
    frame["prev_close"] = frame["close"].shift(1)
    frame["log_dollar_volume"] = np.log(frame["close"] * frame["volume"])
    frame["intra_1"] = frame["close"] / frame["open"] - 1.0
    return frame


def execute_factor(code: str, source_listing: str) -> tuple[dict[str, Any], pd.Series]:
    namespace = {"np": np, "pd": pd}
    exec(compile(code, source_listing, "exec"), namespace)
    function_name = re.search(r"^def\s+(\w+)\(", code, re.MULTILINE).group(1)  # type: ignore[union-attr]
    function = namespace[function_name]
    frame = controlled_frame()
    result = function(frame.copy())
    if not isinstance(result, pd.Series):
        raise TypeError(f"{function_name} returned {type(result)}")
    changed = frame.copy()
    changed.iloc[190:, :] = changed.iloc[190:, :] * 1.7 + 3.0
    changed_result = function(changed)
    prefix_equal = np.allclose(
        result.iloc[:190].to_numpy(dtype=float),
        changed_result.iloc[:190].to_numpy(dtype=float),
        equal_nan=True,
    )
    row = {
        "check": source_listing,
        "function_name": function_name,
        "paper_code_executed_verbatim": True,
        "output_is_series": True,
        "output_length": len(result),
        "index_aligned": result.index.equals(frame.index),
        "finite_output_count": int(np.isfinite(result.to_numpy(dtype=float)).sum()),
        "prefix_causality_check": bool(prefix_equal),
        "required_output_name": function_name,
        "observed_output_name": "" if result.name is None else str(result.name),
        "output_name_contract_passed": result.name == function_name,
        "author_native_pipeline_executed": False,
        "published_metric_regenerated": False,
        "paper_result_credit": False,
        "boundary": "verbatim paper-derived component on a deterministic controlled panel, not the CSI300 author run",
    }
    return row, result


def factor_rows(main_source: str, appendix_source: str) -> list[dict[str, Any]]:
    definitions = (
        ("main_overshoot_listing", extract_listing(main_source, "lst:xalpha_factor_example")),
        ("appendix_overshoot_listing", extract_listing(appendix_source, "lst:xalpha_factor_full")),
        ("appendix_dynamic_range_listing", extract_listing(appendix_source, "lst:dynamic_range_turnover_example")),
    )
    rows = []
    results: dict[str, pd.Series] = {}
    for name, code in definitions:
        row, result = execute_factor(code, name)
        rows.append(row)
        results[name] = result
    equivalent = np.allclose(
        results["main_overshoot_listing"].to_numpy(dtype=float),
        results["appendix_overshoot_listing"].to_numpy(dtype=float),
        equal_nan=True,
    )
    rows.append(
        {
            "check": "main_appendix_overshoot_value_equivalence",
            "function_name": "regime_overshoot_pressure_decay_20d_ma20_vol20",
            "paper_code_executed_verbatim": True,
            "output_is_series": True,
            "output_length": len(results["main_overshoot_listing"]),
            "index_aligned": True,
            "finite_output_count": int(np.isfinite(results["main_overshoot_listing"]).sum()),
            "prefix_causality_check": True,
            "required_output_name": "",
            "observed_output_name": "",
            "output_name_contract_passed": equivalent,
            "author_native_pipeline_executed": False,
            "published_metric_regenerated": False,
            "paper_result_credit": False,
            "boundary": "the two printed overshoot implementations are value-equivalent on the controlled panel",
        }
    )
    return rows


def method_rows() -> list[dict[str, Any]]:
    values = (
        ("data universe and snapshot", "partial", "CSI300 and Qlib-compatible adjusted daily OHLCV are named", "provider/version, point-in-time membership, snapshot, calendar and adjustment factors absent"),
        ("prediction target", "sufficient", "next-open 10-day adjusted open-to-open formula is explicit", ""),
        ("preprocessing", "partial", "invalid-row filtering, buffer, liquidity filtering and volume rescaling are described", "numeric thresholds, buffer length, dedupe rule, adjustment and rescaling constants absent"),
        ("LLM backend", "partial", "gpt-oss-120b is named", "exact checkpoint hash, serving stack, decoding parameters and seeds absent"),
        ("prompt programs", "partial", "20 agent/utility frameworks and two shared blocks are printed", "paper calls them excerpts; cited detailed repository returns 404; filled prompts and responses absent"),
        ("report-grounded memory input", "insufficient", "RMA schema and example traces are printed", "report corpus, report snapshots, chunking run and complete derived memory absent"),
        ("cycle routing", "partial", "five initial coarse-guided cycles followed by memory routing are stated", "coarse themes, total cycle count, route outputs and stochastic selections absent"),
        ("factor evolution", "partial", "64 seeds, pool 80, ten generations and novelty at generations 3 and 7 are stated", "operator allocation, calls, parents, children, repairs, lineage and checkpoints absent"),
        ("selection and scoring", "partial", "many formulas, windows, percentiles, floors and correlations are stated", "winsor limits, rolling hard thresholds, epsilon, warm-up length and selected pool rule absent"),
        ("factor library", "insufficient", "up to 40 factors and correlation below 0.60 are stated", "the selected 40 factors, full code, scores, panels and predictions absent"),
        ("portfolio backtest", "partial", "Qlib top-50/drop-5, open execution and three costs are stated", "Qlib commit/data bundle, account/exchange details, benchmark series, orders, fills and daily returns absent"),
        ("baselines", "insufficient", "16 baselines are named and seven metrics printed", "hyperparameters, seeds, exact feature implementations, factor sets, predictions and returns absent"),
        ("hardware and runtime", "partial", "two H100s and three average runtimes are printed", "hardware model topology, software versions, logs and measured run records absent"),
        ("randomness and run lineage", "insufficient", "stochastic diversification and sampling are acknowledged", "all random seeds, model request/response IDs, immutable run IDs and checkpoints absent"),
        ("raw empirical outputs", "insufficient", "119 main cells, nine factor claims, six heatmap summaries and three panels are printed", "raw matrices, tables, daily metrics, curves and result generator absent"),
    )
    return [
        {"dimension": dimension, "specification_level": level, "paper_evidence": evidence, "missing_for_exact_rerun": missing}
        for dimension, level, evidence, missing in values
    ]


def consistency_rows(table: dict[str, list[float]]) -> list[dict[str, Any]]:
    xalpha_best = all(table["XAlpha"][index] == max(row[index] for row in table.values()) for index in range(7))
    values = (
        ("main_table_best_claim", "consistent", "Paper says XAlpha is best on all seven metrics", f"parsed table confirms={xalpha_best}"),
        ("cited_prompt_repository", "unresolved", "Paper and first-author homepage link uwFengyuan/XAlpha_Prompt", "the exact repository endpoint returns HTTP 404"),
        ("appendix_overshoot_output_contract", "conflict", "Runtime contract requires Series.name to equal function name", "the appendix full listing inherits the name close instead; main-text listing names it correctly"),
        ("appendix_dynamic_output_contract", "conflict", "Runtime contract requires Series.name to equal function name", "the second appendix listing returns an unnamed Series"),
        ("heatmap_recoverability", "insufficient", "Six summary statistics and two raster heatmaps are printed", "50x50 and 60x60 numeric matrices and factor series are absent"),
        ("cumulative_curve_recoverability", "insufficient", "A 17-method plus benchmark raster curve is printed", "raw daily returns, portfolio paths and plot data are absent"),
        ("held_out_test_selection", "specified_claim_unverifiable", "Paper states test diagnostics are reporting-only", "no run lineage, checkpoints or selection records exist to audit the boundary"),
        ("huggingface_xalpha_ablation", "not_attributable_empty", "One search hit is named Antony-Fu/XAlpha_ablation", "account identity is unverified and repository tree contains only .gitattributes"),
    )
    return [{"issue": issue, "status": status, "paper_or_public_claim": claim, "audit_evidence": evidence} for issue, status, claim, evidence in values]


def release_rows(scratch: Path) -> list[dict[str, Any]]:
    discovery = scratch / "discovery"
    user = json.loads((discovery / "github-users-uwFengyuan.json").read_text())
    repos = json.loads((discovery / "github-user-repos.json").read_text())
    repo_404 = json.loads((discovery / "github-repos-uwFengyuan-XAlpha_Prompt.json").read_text())
    searches = {
        "github repository exact name": "github-repos-XAlphaPrompt.json",
        "github repository title and domain": "github-repos-XALPHAalphadiscovery.json",
        "github repository arxiv id": "github-repos-260708332.json",
        "github repository exact paper title": "github-repos-MemoryDrivenAIQuantResearcher.json",
        "github code prompt repository name": "github-code-XAlphaPrompt.json",
        "github code exact factor function": "github-code-regimeovershootpressuredecay20dma20vol20.json",
    }
    rows = [
        {
            "surface": "cited GitHub repository",
            "query_or_endpoint": "uwFengyuan/XAlpha_Prompt",
            "observed_matches": 0,
            "attributable_xalpha_release_found": False,
            "observation": f"exact endpoint status={repo_404.get('status')}",
            "negative_search_boundary": "bounded observation at the pinned audit time; not proof of permanent absence",
        },
        {
            "surface": "first-author GitHub inventory",
            "query_or_endpoint": user["login"],
            "observed_matches": len(repos),
            "attributable_xalpha_release_found": False,
            "observation": f"{len(repos)} public repositories inspected; none named XAlpha or XAlpha_Prompt",
            "negative_search_boundary": "public inventory only; private, deleted, renamed or later repositories are not excluded",
        },
    ]
    for surface, filename in searches.items():
        data = json.loads((discovery / filename).read_text())
        rows.append(
            {
                "surface": surface,
                "query_or_endpoint": filename,
                "observed_matches": data["total_count"],
                "attributable_xalpha_release_found": False,
                "observation": "complete bounded exact search",
                "negative_search_boundary": "zero search results are not absence proof",
            }
        )
    arxiv_code = json.loads((discovery / "github-code-260708332.json").read_text())
    rows.append(
        {
            "surface": "github code arxiv id",
            "query_or_endpoint": "2607.08332",
            "observed_matches": arxiv_code["total_count"],
            "attributable_xalpha_release_found": False,
            "observation": "105 index, bibliography and downstream-reference hits; no attributable implementation identified",
            "negative_search_boundary": "classification is limited to the returned public search set",
        }
    )
    hf_models = json.loads((discovery / "huggingface-models-xalpha.json").read_text())
    hf_datasets = json.loads((discovery / "huggingface-datasets-xalpha.json").read_text())
    hf_tree = json.loads((discovery / "hf-xalpha-ablation-tree.json").read_text())
    rows.extend(
        [
            {
                "surface": "Hugging Face models",
                "query_or_endpoint": "XAlpha",
                "observed_matches": len(hf_models),
                "attributable_xalpha_release_found": False,
                "observation": "four name-token matches; none attributable to the paper",
                "negative_search_boundary": "name search only",
            },
            {
                "surface": "Hugging Face datasets",
                "query_or_endpoint": "XAlpha",
                "observed_matches": len(hf_datasets),
                "attributable_xalpha_release_found": False,
                "observation": f"one unverified Antony-Fu/XAlpha_ablation hit; tree has {len(hf_tree)} .gitattributes-only file",
                "negative_search_boundary": "account name is not author identity proof and empty tree supplies no experiment data",
            },
        ]
    )
    return rows


def build(scratch: Path, output: Path) -> dict[str, Any]:
    verify_pins(scratch)
    output.mkdir(parents=True, exist_ok=True)
    main_source = (scratch / "source/neurips_2026.tex").read_text()
    prompt_source = (scratch / "source/appendix/prompt_excerpts.tex").read_text()
    appendix_source = (scratch / "source/appendix/case_studies.tex").read_text()
    official_text = (scratch / "primary/official.txt").read_text(errors="replace")
    rebuilt_text = (scratch / "primary/rebuilt.txt").read_text(errors="replace")
    overlap = token_jaccard(official_text, rebuilt_text)
    official_pages = len(PdfReader(scratch / "primary/official.pdf").pages)
    rebuilt_pages = len(PdfReader(scratch / "primary/rebuilt.pdf").pages)
    with tarfile.open(scratch / "primary/source.tar") as archive:
        source_files = sum(member.isfile() for member in archive.getmembers())
    if (official_pages, rebuilt_pages, source_files) != (61, 61, 22):
        raise ValueError("paper source/page denominator changed")

    results = result_rows(main_source)
    figures = figure_rows(scratch)
    prompts = prompt_rows(prompt_source)
    factors = factor_rows(main_source, appendix_source)
    methods = method_rows()
    table = main_table(main_source)
    consistency = consistency_rows(table)
    releases = release_rows(scratch)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "prompt_inventory.csv", prompts)
    write_csv(output / "factor_execution_audit.csv", factors)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "release_search_audit.csv", releases)

    provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "arxiv_version": "v2",
        "published_utc": "2026-07-09T10:17:22Z",
        "updated_utc": "2026-07-13T07:04:03Z",
        "source_files": source_files,
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "official_pages_visually_checked": 61,
        "rebuilt_pages_visually_checked": 61,
        "visual_defects_observed": 0,
        "official_rebuilt_token_jaccard": overlap,
        "paper_prompt_repository": "https://github.com/uwFengyuan/XAlpha_Prompt",
        "paper_prompt_repository_http_status": 404,
        "first_author_public_repositories_checked": 27,
        "attributable_xalpha_implementation_found": False,
        "negative_search_scope": (
            "bounded GitHub, first-author homepage/inventory and Hugging Face observations; this does not prove "
            "that private, deleted, renamed, unindexed or later artifacts do not exist"
        ),
        "pins": PINS,
    }
    write_json(output / "source_provenance.json", provenance)

    readme = (
        "# XALPHA paper-level replication audit\n\n"
        "**Verdict: unusually specification-rich, but not reproducible end to end.** The pinned arXiv-v2 "
        f"source rebuilds to 61 pages with {overlap:.2%} extracted-token overlap. All 61 official and all 61 "
        "rebuilt pages were visually checked without observed defects. The source exposes 20 named agent/utility "
        "prompt frameworks, two shared prompt blocks, runtime pseudocode, detailed evaluation equations, primitive "
        "features, two complete factor listings, and three empirical raster panels.\n\n"
        "The published empirical denominator is 138 numeric result units: 119 cells in the main 17-by-7 comparison, "
        "nine representative-factor values, six heatmap summaries, and four runtime/hardware claims. It also includes "
        "three empirical figure panels. **Zero of 138 numeric units and 0/3 panels are author-natively regenerated.** "
        "The paper and first-author homepage both link `uwFengyuan/XAlpha_Prompt`, but the exact endpoint is HTTP 404. "
        "The author's 27 public repositories contain no XAlpha repository; six bounded exact GitHub repository/code "
        "searches return zero, while 105 arXiv-ID code hits are indexes or downstream references rather than an "
        "attributable implementation. These bounded results are not proof of permanent absence.\n\n"
        "The strongest executable evidence is narrower. Three listings execute verbatim on a deterministic one-ticker "
        "MultiIndex panel, remain index-aligned and pass a prefix-causality perturbation. The main and appendix "
        "overshoot implementations are value-equivalent. Both appendix factors return a wrong Series name "
        "(`close` or `None`), however, "
        "contradicting the paper's own contract that the returned Series name must equal the function name; the "
        "shorter main-text overshoot listing repairs that specific defect. These are paper-derived component checks, "
        "not the author pipeline and not reproductions of the printed CSI300 metrics.\n\n"
        "The method is well described in several respects: CSI300, the next-open 10-day label, 2011--2025 split, "
        "gpt-oss-120b, 64 initial factors, pool size 80, ten generations, novelty injections, Ridge alpha 10, up to "
        "40 final factors, Qlib top-50/drop-5 execution, and transaction costs are stated. Exact rerunning still needs "
        "the Qlib data/version and point-in-time universe, adjustment and preprocessing constants, report corpus and "
        "derived memory, exact checkpoint/serving/decoding configuration, stochastic seeds, coarse themes and total "
        "cycles, rolling thresholds and winsorization, generated factors and lineage, baseline configurations, "
        "predictions, orders/fills, daily returns, raw heatmap matrices, checkpoints, and result generator. The three "
        "empirical assets are rasters only. `strict_success` remains false.\n"
    )
    (output / "README.md").write_text(readme)

    generated = {
        path.name: sha256(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "active_numeric_result_units": len(results),
        "main_table_result_cells": 119,
        "author_native_numeric_result_units_regenerated": 0,
        "active_empirical_figure_panels": sum(row["empirical_panels"] for row in figures),
        "author_native_empirical_panels_regenerated": 0,
        "named_agent_utility_prompt_frameworks_recovered": sum(row["category"] != "shared_block" for row in prompts),
        "shared_prompt_blocks_recovered": sum(row["category"] == "shared_block" for row in prompts),
        "paper_factor_programs_executed": 3,
        "paper_factor_programs_passing_output_name_contract": sum(
            row["check"].endswith("listing") and row["output_name_contract_passed"] for row in factors
        ),
        "attributable_xalpha_implementation_found": False,
        "raw_result_arrays_recovered": 0,
        "strict_success": False,
        "generated_file_sha256": generated,
    }
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
    return int(args.strict and not manifest["strict_success"])


if __name__ == "__main__":
    raise SystemExit(main())
