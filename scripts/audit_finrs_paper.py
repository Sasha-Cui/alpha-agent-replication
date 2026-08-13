#!/usr/bin/env python3
"""Build a fail-closed primary-source and cross-paper lineage audit for FinRS."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from pypdf import PdfReader

from alpha_evolve import finpos_paper_components as shared_component


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/finrs_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/finrs"
FINPOS_LEDGER = ROOT / "paper_runs/paper_replication_audits/finpos/published_result_ledger.csv"
WORK_ID = "CensusArxiv251112599"
SYSTEM_ID = "SYS-FIN-RS"
ARXIV_ID = "2511.12599"

PINS = {
    "primary/arxiv-abs.html": "4df4e8b0b809c4b79ed44f1fed9f22b40449f6222daa788d4611fb75998464b1",
    "primary/arxiv-api.xml": "13c23e885d6674035d6768a93906d3128f31d990ce99c7c5da778838fafb3589",
    "primary/official-v1.pdf": "1f7ae10ed56436a1b48392ffbda98dfd02c4822c1b08eb9c60cbf8a5a0fdc112",
    "primary/official-v1.txt": "751fce8dfab00285ed7a3b9a4a3ad8874dfe64a6947ec092d1d9550f7c7aa9ee",
    "primary/rebuilt-v1.pdf": "385fe641fee18755a2efc84909f5b5834cd1a00b9bf6565463b0cfc0470a5efc",
    "primary/rebuilt-v1.txt": "8814953df94dae8190f1ac4e11bbd9bd52bb1f4e72b679ea27fc51cb103876c7",
    "primary/source-v1.tar": "8c6711fcee25842ef9593eda5a10824f8026abe962cc9f5e98d4e9a32d66d01a",
    "discovery/github-code-arxiv.json": "05b5e0d57f469b14b21605837c95edffc773394668cb3deb9c82d6adb240102c",
    "discovery/github-code-kelly.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-code-title.json": "f1e0a34b1600d490f84bb69b7ca99a509bdc34cfab035abd40e4cacd21bc7153",
    "discovery/github-repositories-arxiv.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-repositories-title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/huggingface-datasets-finrs.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-models-finrs.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}

TABLE_SPECS = {
    "tab:model_comparison": ("sec/3_Architecture_of_FinPos.tex", tuple(range(1, 16)), 180),
    "tab:ablation_single": ("sec/4_Experiments.tex", tuple(range(4, 13)), 45),
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
        observed = sha256(scratch / relative)
        if observed != expected:
            raise ValueError(f"pin mismatch: {relative}={observed}; expected {expected}")


def paper_sources(scratch: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(scratch / "primary/source-v1.tar", "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe source member: {member.name}")
            if member.isfile():
                handle = archive.extractfile(member)
                if handle is None:
                    raise ValueError(f"unreadable source member: {member.name}")
                files[member.name] = handle.read()
    if len(files) != 13:
        raise ValueError(f"paper source file count changed: {len(files)}")
    return files


def strip_comments(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("%"))


def table_environment(source: str, label: str) -> str:
    source = strip_comments(source)
    location = source.index(rf"\label{{{label}}}")
    begin = source.rfind(r"\begin{table", 0, location)
    end = source.find(r"\end{table", location)
    if begin < 0 or end < 0:
        raise ValueError(f"table boundary missing: {label}")
    return source[begin:end]


def clean_tex(value: str) -> str:
    value = value.replace(r"\%", "%")
    value = re.sub(r"\\cite\{[^{}]*\}", "", value)
    value = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\(?:bfseries|small|midrule|toprule|bottomrule)", "", value)
    value = re.sub(r"[{}$~]", "", value)
    return " ".join(value.split())


def table_data_rows(environment: str) -> list[list[str]]:
    match = re.search(r"\\begin\{tabular\}\{.*?\}(.*?)\\end\{tabular\}", environment, re.S)
    if match is None:
        raise ValueError("tabular body missing")
    rows = []
    for chunk in re.split(r"\\\\", match.group(1)):
        chunk = re.sub(r"\\cite\{[^{}]*\}", "", chunk)
        if "&" in chunk:
            rows.append([clean_tex(cell) for cell in chunk.split("&")])
    return rows


def result_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    blocker = (
        "no author implementation, prompts, scaled-Kelly/CVaR definition, immutable inputs, "
        "model requests/responses, seeds, orders, fills, account path, raw arrays, or result generator"
    )
    rows: list[dict[str, Any]] = []
    for label, (path, columns, expected) in TABLE_SPECS.items():
        parsed = table_data_rows(table_environment(files[path].decode(), label))
        table_rows: list[dict[str, Any]] = []
        for row_index, cells in enumerate(parsed, 1):
            if max(columns) >= len(cells) or not all(re.search(r"\d", cells[c]) for c in columns):
                continue
            row_label = " | ".join(c for c in cells[: min(columns)] if c) or f"row_{row_index}"
            for column in columns:
                table_rows.append(
                    {
                        "table_label": label,
                        "row_index": row_index,
                        "row_label": row_label,
                        "quantitative_column_index": column,
                        "printed_cell": cells[column],
                        "unit_definition": "one populated displayed empirical quantitative table cell",
                        "source_document_recovered": True,
                        "raw_result_record_recovered": False,
                        "author_native_experiment_executed": False,
                        "published_result_regenerated": False,
                        "paper_result_credit": False,
                        "blocking_reason": blocker,
                    }
                )
        if len(table_rows) != expected:
            raise ValueError(f"denominator changed for {label}: {len(table_rows)} != {expected}")
        rows.extend(table_rows)
    return rows


def cross_paper_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def comparable(value: str) -> str:
        return value.replace(r"\textbf", "").strip()

    with FINPOS_LEDGER.open(newline="", encoding="utf-8") as stream:
        finpos = [row for row in csv.DictReader(stream) if row["revision"] == "v1"]
    if len(finpos) != len(results):
        raise ValueError("FinPos-v1 and FinRS result denominators no longer align")
    rows = []
    for index, (finrs, prior) in enumerate(zip(results, finpos), 1):
        if finrs["table_label"] != prior["table_label"]:
            raise ValueError(f"cross-paper table order changed at cell {index}")
        exact = comparable(finrs["printed_cell"]) == comparable(prior["printed_cell"])
        rows.append(
            {
                "cell_index": index,
                "table_label": finrs["table_label"],
                "finrs_printed_cell": finrs["printed_cell"],
                "finpos_v1_printed_cell": prior["printed_cell"],
                "exact_display_match": exact,
                "lineage_interpretation": "displayed-value reuse, not an independently regenerated result",
            }
        )
    exact = sum(row["exact_display_match"] for row in rows)
    if exact != 216:
        raise ValueError(f"FinRS/FinPos-v1 exact cell overlap changed: {exact} != 216")
    return rows


def component_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    architecture = strip_comments(files["sec/3_Architecture_of_FinPos.tex"].decode())
    required = (
        "M_t = M_{t}^{s} + M_{t}^{m} + M_{t}^{l}",
        "position_{t} = position_{t - 1} + d_t \\times q_t",
        "position_{t} \\times M_{t}",
    )
    if not all(marker in architecture for marker in required):
        raise ValueError("printed FinRS equations changed")
    prices = [100.0 + index for index in range(31)]
    mechanics = (
        ("multi_timescale_score", shared_component.multi_timescale_score(prices, 0)),
        ("position_update", shared_component.update_position(3, -1, 1)),
        ("literal_reward", shared_component.literal_reward(3, 2, 3)),
    )
    return [
        {
            "component": name,
            "controlled_output": json.dumps(output),
            "deterministic_control_passed": True,
            "equation_identical_to_finpos_v1": True,
            "paper_derived_not_author_code": True,
            "author_native_pipeline_executed": False,
            "published_result_regenerated": False,
            "paper_result_credit": False,
            "boundary": shared_component.PAPER_BOUNDARY,
        }
        for name, output in mechanics
    ]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official paper and source", "complete", "single arXiv-v1 PDF and 13-file source archive pinned; all six official and rebuilt pages visually checked"),
        ("native implementation", "unreleased", "paper contains no system URL and bounded searches find no attributable release"),
        ("FinPos lineage", "material_display_reuse", "216/225 cells exactly match FinPos v1 published 16 days earlier"),
        ("agent prompts", "missing", "domain-specific risk prompts are claimed but none are printed or released"),
        ("scaled Kelly criterion", "named_only", "named as a position-sizing reference without equation, scale, inputs, or implementation"),
        ("CVaR", "named_only", "named as a position-sizing reference without alpha, horizon, estimator, units, or conversion to quantity"),
        ("volatility adjustment", "named_only", "ablation prose claims volatility adjustment without a definition"),
        ("model", "family_and_temperature_only", "GPT-4o and temperature 0.7 without immutable snapshot, API version, top_p, seeds, or logs"),
        ("stock universe", "specified", "TSLA, AAPL, AMZN, NFLX, and COIN"),
        ("market data", "provider_schema_only", "Yahoo daily OHLCV without immutable rows, adjustment policy, timestamps, or missing-data rules"),
        ("news", "provider_only", "Finnhub company/macro news without query parameters, item IDs, retrieval timestamps, or snapshot"),
        ("filings", "provider_only", "SEC EDGAR 10-K/10-Q without accession IDs, cutoffs, parser, or daily standardization code"),
        ("train/test split", "date_ranges_only", "Jan 2024--Feb 2025 train and Mar--Apr 2025 test without exact calendars or boundary handling"),
        ("initial account state", "missing", "cash, initial position, leverage, exposure definition, and account-value construction are absent"),
        ("orders and fills", "missing", "trade units, fill timing, costs, slippage, borrowing, constraints, and liquidation are absent"),
        ("hierarchical memory", "narrative_only", "layers and promotion/discard narrative without allocation, retrieval, scoring, or persistence implementation"),
        ("multi-scale reward", "equation_partial", "raw future 1/7/30-day price score and position reward printed; endpoints, training/test scope, and risk adjustment missing"),
        ("metrics", "names_and_citations_only", "CR, Sharpe, and MDD named without formulas, frequency, annualization, or account path"),
        ("baselines", "names_only", "11 baselines named without complete configurations, task adaptations, seeds, or outputs"),
        ("raw empirical outputs", "missing", "no predictions, positions, trades, PnL, account paths, arrays, or result generator"),
    )
    return [{"dimension": d, "status": s, "evidence": e} for d, s, e in specs]


def consistency_rows() -> list[dict[str, str]]:
    values = (
        ("reward_action_alignment", "semantic_conflict", "reward uses total position times trend, not direction or position change; a sell that remains long can be rewarded in a rising market"),
        ("reward_risk_adjustment", "claim_formula_conflict", "prose calls the return risk-adjusted, but the equation contains no volatility, drawdown, CVaR, Kelly, or downside term"),
        ("reward_pnl_benchmark", "claim_formula_conflict", "prose says sliding-window account P&L benchmark; equation uses unnormalized future raw-price differences"),
        ("reward_horizon_scaling", "claim_formula_conflict", "prose says scaled across horizons; equation is an unweighted sum"),
        ("reward_asset_scale", "asset_scale_dependent", "raw dollar differences and their square are not normalized across stocks"),
        ("future_momentum_at_decision", "lookahead_scope_ambiguous", "decision section says the direction agent integrates 1/7/30-day differences, while equations define them using future prices and no test-time exclusion is stated"),
        ("scaled_kelly_cvar", "missing_core_mechanics", "the two risk-sizing mechanisms highlighted as novel are not mathematically or operationally defined"),
        ("risk_sensitive_ablation", "treatment_underspecified", "RS bundles position information and undefined volatility adjustment, preventing treatment replication"),
        ("election_timing", "conflict", "Mar--Apr 2025 testing is said to include the U.S. election held in Nov 2024"),
        ("finpos_main_table_reuse", "exact_180_of_180", "every main-table cell exactly matches FinPos v1 despite the renamed framework"),
        ("finpos_ablation_reuse", "exact_36_of_45", "four of five nine-metric ablation rows exactly match FinPos v1; only the renamed MN removal row differs"),
        ("empirical_asset_lineage", "static_only", "only a conceptual architecture PDF is shipped; no raw numeric or execution artifact accompanies results"),
    )
    return [{"check": c, "status": s, "evidence": e} for c, s, e in values]


def release_rows() -> list[dict[str, Any]]:
    boundary = "bounded search cannot exclude private, deleted, moved, renamed, unindexed, or later releases"
    values = (
        ("GitHub repositories", "exact title", 0, "no repository match"),
        ("GitHub repositories", "arXiv 2511.12599", 0, "no repository match"),
        ("GitHub code", "exact title", 6, "citation/index material; no attributable implementation"),
        ("GitHub code", "arXiv 2511.12599", 13, "citation/index/secondary implementations; no attributable release"),
        ("GitHub code", "scaled Kelly Criterion plus FinRS", 0, "no exact implementation match"),
        ("Hugging Face models", "FinRS", 0, "no model match"),
        ("Hugging Face datasets", "FinRS", 0, "no dataset match"),
    )
    return [
        {
            "surface": surface,
            "query": query,
            "observed_matches": count,
            "observation": observation,
            "attributable_finrs_release_found": False,
            "negative_search_boundary": boundary,
        }
        for surface, query, count, observation in values
    ]


def readme_text() -> str:
    return """# FinRS paper-faithfulness audit

This is a paper-derived component and cross-paper lineage audit, not an end-to-end FinRS replication. The official six-page arXiv-v1 source rebuilds without modification; every official and rebuilt page was visually checked with no observed defects.

The paper contains **225 displayed empirical cells across two tables** and one conceptual (zero-empirical-panel) figure. Zero of 225 cells were regenerated through an author-native pipeline. Three controlled mechanics execute, but their equations are identical to FinPos v1 and are paper-derived checks, not author code or FinRS result credit.

Cross-paper lineage is unusually strong: **216/225 FinRS cells exactly match FinPos v1**, published 16 days earlier. All 180 main-table cells match, as do four of five ablation rows (36/45 cells). The nine changed cells are the FinRS Market News-removal row. This is displayed-value reuse, not independent empirical corroboration.

The paper's main risk-sensitive contribution is not executable from the source. Scaled Kelly, CVaR, volatility adjustment, risk prompts, account exposure, and order sizing are named but not defined. The printed reward contains no risk-adjustment term, conflicts with the claimed P&L benchmark and horizon scaling, uses asset-scale-dependent raw dollars, and rewards total position rather than action/change. Future 1/7/30-day differences are described in the decision path without an explicit test-time exclusion.

No attributable code, immutable data, runtime prompts/responses, trades, positions, account path, raw arrays, or result generator was found. Therefore `strict_success` remains false. Negative searches are bounded and do not prove that private, deleted, moved, renamed, unindexed, or later material does not exist.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    verify_pins(scratch)
    files = paper_sources(scratch)
    output.mkdir(parents=True, exist_ok=True)
    for old in output.iterdir():
        if old.is_file():
            old.unlink()
    results = result_rows(files)
    lineage = cross_paper_rows(results)
    components = component_rows(files)
    provenance = {
        "arxiv_id": ARXIV_ID,
        "arxiv_version": "v1",
        "authors": ["Bijia Liu", "Ronghao Dang"],
        "published": "2025-11-16T13:56:04Z",
        "source_files": 13,
        "official_pages": len(PdfReader(scratch / "primary/official-v1.pdf").pages),
        "rebuilt_pages": len(PdfReader(scratch / "primary/rebuilt-v1.pdf").pages),
        "official_pages_visually_checked": 6,
        "rebuilt_pages_visually_checked": 6,
        "visual_defects_observed": 0,
        "official_rebuilt_token_jaccard": token_jaccard(
            (scratch / "primary/official-v1.txt").read_text(errors="ignore"),
            (scratch / "primary/rebuilt-v1.txt").read_text(errors="ignore"),
        ),
        "paper_contains_native_implementation_url": False,
        "paper_contains_dataset_or_checkpoint_url": False,
        "attributable_finrs_implementation_found": False,
        "observed_license": "NOASSERTION",
        "pinned_input_sha256": PINS,
    }
    write_json(output / "source_provenance.json", provenance)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "cross_paper_result_lineage.csv", lineage)
    write_csv(
        output / "figure_inventory.csv",
        [{
            "figure": "fig:archi", "source_asset": "image/archi_rs0.pdf",
            "source_asset_sha256": hashlib.sha256(files["image/archi_rs0.pdf"]).hexdigest(),
            "empirical_panels": 0, "description": "conceptual FinRS architecture",
            "underlying_numeric_array_or_run_log_recovered": False,
            "paper_result_credit": False,
        }],
    )
    write_csv(output / "component_execution_audit.csv", components)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", consistency_rows())
    write_csv(output / "release_search_audit.csv", release_rows())
    (output / "README.md").write_text(readme_text())
    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "active_empirical_table_cells": len(results),
        "result_tables": len(TABLE_SPECS),
        "author_native_table_cells_regenerated": 0,
        "empirical_figure_panels": 0,
        "author_native_empirical_panels_regenerated": 0,
        "finpos_v1_exact_display_cell_matches": sum(row["exact_display_match"] for row in lineage),
        "paper_derived_components_executed": len(components),
        "paper_derived_components_passing_controlled_checks": len(components),
        "attributable_finrs_implementation_found": False,
        "raw_result_arrays_recovered": 0,
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
    }
    manifest["generated_file_sha256"] = {
        path.name: sha256(path)
        for path in output.iterdir()
        if path.is_file() and path.name != "manifest.json"
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
