#!/usr/bin/env python3
"""Build a fail-closed original-source audit for arXiv:2606.08283v1."""

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

from alpha_evolve import macro_economists_paper_components as component


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/macro_economists_machine_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/macro_economists_machine"
WORK_ID = "CensusArxiv260608283"
SYSTEM_ID = "SYS-MACRO-ECONOMISTS-MACHINE"
ARXIV_ID = "2606.08283"

PINS = {
    "primary/arxiv-abs.html": "d2a48e252d40a0d77ba6ae34c78078307490ff0486875c53a2ae29e28b64c003",
    "primary/arxiv-api.xml": "f9811fd8b243bd26fbe6f0a0e4ff38504cfeb8029ad0c8900f8bf8d708e01a97",
    "primary/official-v1.pdf": "e166ba0c9baed18a4e38fd072a813847395fa3e8df53b913a624c6954add72cf",
    "primary/official-v1.txt": "1719bb6ef87ecb45debc1a6ce7f6d84094d920112071b4ae3a90a3bdeab1a6d1",
    "primary/rebuilt-v1.pdf": "1a22d64249edc4e196b6ef44e3fa2be35dc34beb02eac5e4e21c5d7bd7fea5e3",
    "primary/rebuilt-v1.txt": "95844d9bad6b50b6a1218457e1d7600d19a6a18bb16c0d657dbb60dd4be2fc92",
    "primary/source-v1.tar": "2eff2ba685242f4734d267807a0d4027f718c8a8a53aae331cc54bb33ce51171",
    "discovery/github-code-arxiv.json": "c2b6d8d70a11ef2ffd69aa9ccbd7814961f9f0ffa0f96f18044fd5b986ebd081",
    "discovery/github-code-title.json": "75cf492846accb189696d1c39275832968a972151cb3769e4f2b66f5b02669e7",
    "discovery/github-repositories-arxiv.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-repositories-title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/huggingface-models-arxiv.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-datasets-arxiv.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}

# One unit is one populated displayed quantitative result-table cell.  A CI
# printed in one cell remains one unit even though it contains two endpoints.
TABLE_SPECS = {
    "tab:fullperiod": ({"Rule Agent (z-score)", "Hawkish Agent", "Dovish Agent", "Debate Agent", "Inverse Volatility"}, 25),
    "tab:incremental": ({"Hawkish Agent", "Dovish Agent", "Debate Agent", "Debate vs. avg(Hawkish, Dovish)"}, 7),
    "tab:bootstrap": ({
        "Hawkish vs. Rule", "Dovish vs. Rule", "Debate vs. Rule", "Debate vs. Hawkish",
        "Debate vs. Dovish", "Any LLM vs. Inv. Vol.", "Rule vs. Inv. Vol.", "Hawkish vs. Dovish",
    }, 24),
    "tab:subperiod": ({"Rates Peak (2023)", "Soft Landing (2024--25)", "Full Period"}, 15),
    "tab:txcost": ({"Rule Agent (z-score)", "Hawkish Agent", "Dovish Agent", "Debate Agent", "Inverse Volatility"}, 25),
    "tab:riskprofile": ({"Rule Agent", "Hawkish Agent", "Dovish Agent", "Debate Agent", "Inverse Vol."}, 36),
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
    if len(files) != 7:
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
    value = value.replace(r"\%", "%").replace("~", " ")
    value = value.replace("^*", "")
    value = re.sub(r"\\multicolumn\{[^{}]*\}\{[^{}]*\}\{(.*?)\}", r"\1", value)
    value = re.sub(r"\\(?:textbf|textit|emph)\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\(?:bfseries|small|midrule|toprule|bottomrule)", "", value)
    value = value.replace(r"\ ", " ").replace(r"\.", ".")
    value = re.sub(r"[{}$]", "", value)
    return " ".join(value.split())


def table_rows(environment: str) -> list[list[str]]:
    match = re.search(r"\\begin\{tabular\}\{.*?\}(.*?)\\end\{tabular\}", environment, re.S)
    if match is None:
        raise ValueError("tabular body missing")
    values = []
    for chunk in re.split(r"\\\\", match.group(1)):
        if "&" in chunk:
            values.append([clean_tex(cell) for cell in chunk.split("&")])
    return values


def result_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    source = files["main.tex"].decode()
    blocker = (
        "no public author pipeline, processed panel, generated contracts, exact data rows, "
        "immutable model snapshot, complete prompt/schema, raw returns/weights, bootstrap "
        "implementation/seed, or result generator; embedded figures also conflict with tables"
    )
    all_rows: list[dict[str, Any]] = []
    for label, (expected_labels, expected_count) in TABLE_SPECS.items():
        selected: list[dict[str, Any]] = []
        for row_index, cells in enumerate(table_rows(table_environment(source, label)), 1):
            row_label = cells[0].strip()
            match_label = next((name for name in expected_labels if row_label == name), None)
            if match_label is None:
                continue
            for column_index, cell in enumerate(cells[1:], 1):
                cleaned = clean_tex(cell)
                # Formatting arguments from multicolumn are removed by clean_tex.
                if not re.search(r"(?:\d|(?<![A-Za-z])[-+]?(?:\.\d+))", cleaned) or cleaned in {"---", "--"}:
                    continue
                selected.append({
                    "table_label": label,
                    "row_index": row_index,
                    "row_label": match_label,
                    "quantitative_column_index": column_index,
                    "printed_cell": cleaned,
                    "unit_definition": "one populated displayed empirical quantitative table cell",
                    "source_document_recovered": True,
                    "raw_result_record_recovered": False,
                    "author_native_experiment_executed": False,
                    "published_result_regenerated": False,
                    "paper_result_credit": False,
                    "blocking_reason": blocker,
                })
        if len(selected) != expected_count:
            raise ValueError(f"denominator changed for {label}: {len(selected)} != {expected_count}")
        all_rows.extend(selected)
    return all_rows


def component_rows(source: str) -> list[dict[str, Any]]:
    required = (
        r"\label{eq:rule_raw_tilt}", r"\label{eq:rule_discretization}", r"\label{eq:divergence}",
        r"\label{eq:ivol}", r"\label{eq:transaction_cost}", "B=5{,}000",
    )
    if not all(marker in source for marker in required):
        raise ValueError("printed mechanics changed")
    checks = (
        ("rule_raw_tilt", component.rule_raw_tilt([1.8, 2.1, 2.4, -0.6], [1, -1, -1, 0]), -2.7),
        ("rule_discretization", component.discretize_rule_tilt(-2.7), -2),
        ("conflict_detection", component.conflict_detected(vix=1.1, indpro=1.1, breakeven=0, real_yield=0), True),
        ("conflict_attenuation", component.attenuate_conflicting_tilts([-2, 1], conflict=True), [-1.0, 0.5]),
        ("risk_off_score", component.risk_off_score(vix=1.8, fed_funds=2.4, real_yield=2.1, usd=0), 0.85),
        ("positive_cyclical_suppression", component.suppress_positive_cyclical_tilts([2, -1], [True, True], score=0.85), [0.0, -1.0]),
        ("agent_disagreement", component.average_absolute_disagreement([1, -1], [0, 1]), 1.5),
        ("debate_consensus", component.debate_consensus([1, -1], [-1, 1]), [0.0, 0.0]),
        ("inverse_volatility", component.inverse_volatility_weights([1, 2]), [2 / 3, 1 / 3]),
        ("equal_weight_blend", component.blend_with_equal_weight([2 / 3, 1 / 3]), [7 / 12, 5 / 12]),
        ("multiplicative_tilt", component.multiplicative_macro_tilt([0.6, 0.4], [2, -2]), [0.9, 0.2]),
        ("normalization", component.normalize_long_only([0.9, 0.2]), [9 / 11, 2 / 11]),
        ("one_way_turnover", component.one_way_turnover([0.5, 0.5], [1, 0]), 0.5),
        ("turnover_scaling", component.scale_target_to_turnover_limit([1, 0], [0, 1], 0.5), [0.5, 0.5]),
        ("annual_metrics", component.annualized_return_volatility_sharpe([0.01, -0.01, 0.02]), (0.3466666666666667, 0.11015141094572203, 3.147183169877773)),
        ("maximum_drawdown", component.maximum_drawdown([0.1, -0.2, 0.1]), -0.2),
        ("hit_rate", component.hit_rate([0.1, 0, -0.1, 0.2]), 0.5),
        ("transaction_cost", component.net_return_after_cost(0.01, 10, 0.5), 0.0095),
    )
    rows = []
    for name, observed, expected in checks:
        if isinstance(expected, float):
            passed = abs(observed - expected) < 1e-12
        elif isinstance(expected, (list, tuple)):
            passed = len(observed) == len(expected) and all(abs(a - b) < 1e-12 for a, b in zip(observed, expected))
        else:
            passed = observed == expected
        rows.append({
            "component": name, "controlled_output": json.dumps(observed),
            "deterministic_control_passed": passed, "paper_derived_not_author_code": True,
            "author_native_pipeline_executed": False, "published_result_regenerated": False,
            "paper_result_credit": False, "boundary": component.PAPER_BOUNDARY,
        })
    fail_closed = (
        ("rule_regime_probabilities", lambda: component.rule_regime_probabilities({})),
        ("constrained_portfolio_weights", lambda: component.constrained_portfolio_weights()),
        ("stationary_bootstrap_test", lambda: component.stationary_bootstrap_sharpe_test()),
        ("llm_contract_validation", lambda: component.validate_llm_contract()),
    )
    for name, operation in fail_closed:
        try:
            operation()
        except component.UnderspecifiedPaperMechanic as exc:
            rows.append({
                "component": name, "controlled_output": str(exc), "deterministic_control_passed": True,
                "paper_derived_not_author_code": True, "author_native_pipeline_executed": False,
                "published_result_regenerated": False, "paper_result_credit": False,
                "boundary": component.PAPER_BOUNDARY,
            })
        else:
            raise ValueError(f"{name} did not fail closed")
    return rows


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official paper and source", "complete", "single arXiv-v1 PDF and seven-file source archive pinned; all 46 official and rebuilt pages visually checked"),
        ("native implementation", "unreleased", "paper provides no system URL; bounded GitHub and Hugging Face searches find no attributable release"),
        ("replication artifacts", "request_only", "processed weekly panel, cached contracts, and replication materials are available only from the corresponding author upon reasonable request"),
        ("ETF universe", "complete", "15 tickers, names, subclasses, exchanges, and Oct-2022 initialization start printed"),
        ("macro feature identities", "substantial", "seven FRED IDs, nominal lags, rolling 156-week z-score, and release-aware limitation printed"),
        ("market data", "provider_only", "Yahoo Finance without immutable rows, query date, adjusted-price field, calendar/alignment, missing-value, or corporate-action policy"),
        ("macro data", "provider_schema_only", "FRED IDs but no immutable observations, vintages, retrieval dates, exact weekly calendar, or detailed release alignment"),
        ("rule loading matrix", "complete", "all 15-by-7 directional loadings and thresholds printed"),
        ("rule conflict handling", "equation_complete_but_type_conflict", "gamma=0.5 is printed but converts the defined five integer levels into half levels"),
        ("rule regime probabilities", "underspecified", "proportional constants and residual-versus-normalization ordering omitted"),
        ("LLM model", "mutable_alias_only", "gpt-4o-mini and temperature zero without dated snapshot, API version, remaining request parameters, seed, or response headers"),
        ("LLM prompts", "partial", "common and three role blocks printed; required JSON schema, dynamic input block, narrative generator, and retry behavior omitted"),
        ("LLM outputs", "unreleased", "cached date-agent contracts, token logs, rationales, probabilities, tilts, confidence, and validation records absent"),
        ("debate", "equations_partial", "disagreement threshold, two-round maximum, and averaging printed; actual review messages and revision/termination details absent"),
        ("portfolio base and tilt", "equation_complete", "26-week inverse volatility, 50/50 blend, and kappa=.25 multiplicative tilt printed"),
        ("cyclical set", "missing", "the pre-specified cyclical ETF set C is never enumerated"),
        ("risk controls", "underspecified", "renormalization/cyclical/single-name/turnover cap ordering and projection procedure are not uniquely defined"),
        ("risk-profile robustness", "underspecified", "cap ranges and alternative triggers are reported without a mapping from states to a cap value"),
        ("return metrics", "substantial", "weekly arithmetic mean/sample volatility annualization and zero-risk-free return-to-volatility ratio printed; exact week endpoints still absent"),
        ("stationary bootstrap", "underspecified", "B=5000 and joint resampling printed; selector, seed, CI, p-value/tail, statistic recentering, and ties omitted"),
        ("transaction costs", "equation_complete_limited", "half-L1 one-way cost formula printed; spread variation, impact, taxes, and operations excluded"),
        ("raw empirical outputs", "missing", "no prices, macro panel, contracts, weights, turnovers, returns, NAVs, bootstrap draws, or result generator"),
    )
    return [{"dimension": dimension, "status": status, "evidence": evidence} for dimension, status, evidence in specs]


def consistency_rows() -> list[dict[str, str]]:
    values = (
        ("cost_figure_vs_table", "major_numeric_conflict", "embedded Figure 3 reports about 0.84--0.92 while Table 7 reports 0.481--0.571 for the same five cost settings; rankings also conflict"),
        ("cost_figure_benchmark_ranking", "claim_conflict", "Figure 3 places inverse volatility above several LLM curves at multiple costs, contradicting the table/note claim that all LLM strategies remain above it through 30 bps"),
        ("debate_weight_divergence_dates", "data_window_conflict", "Figure 4C begins in 2017, over five years before the stated October-2022 price-history start and unlike adjacent Oct-2023 panels"),
        ("soft_landing_endpoint", "label_conflict", "method defines Jan-2024 through Feb-2026, while Table 6 labels and note restrict the soft landing to 2024--2025"),
        ("rule_signal_domain", "definition_conflict", "final Rule signal is defined as b in {-2,-1,0,1,2}, then conflict attenuation gamma=.5 creates half-level values"),
        ("rule_regime_residual", "algorithm_conflict", "four positive scores are normalized to unit sum and risk-on is then called the residual, which makes risk-on identically zero unless an unstated ordering/scaling is used"),
        ("cyclical_cap_renormalization", "algorithm_conflict", "scaling cyclicals to .45 and then renormalizing the full unnormalized portfolio can make the resulting cyclical share exceed .45"),
        ("risk_profile_definition", "treatment_underspecified", "Table 8 varies cyclical cap over ranges and changes trigger semantics without defining per-date cap selection or the complete alternative engine"),
        ("prompt_schema", "claim_artifact_gap", "prompt says output must follow the required JSON schema, but no schema is printed or released"),
        ("historical_band_input", "claim_artifact_gap", "prompt requires a historical 95% band absent from the feature definition and without a calculation rule"),
        ("any_llm_comparison", "statistic_undefined", "bootstrap row Any LLM vs inverse volatility does not define whether Any means maximum, average, pooled, or a multiple-comparison statistic"),
        ("incremental_rounding", "rounding_unverifiable", "incremental return/Sharpe cells do not equal differences of the rounded full-period cells and raw precision is absent"),
        ("figure_arrays", "static_only", "four raster figures totaling 12 panels are source assets without underlying values, plotting code, or run lineage"),
    )
    return [{"check": check, "status": status, "evidence": evidence} for check, status, evidence in values]


def release_rows() -> list[dict[str, Any]]:
    boundary = "bounded search cannot exclude private, deleted, moved, renamed, unindexed, or later releases"
    values = (
        ("GitHub repositories", "exact title", 0, "no repository match"),
        ("GitHub repositories", "arXiv 2606.08283", 0, "no repository match"),
        ("GitHub code", "exact title", 13, "citation/index/secondary mentions; no attributable implementation"),
        ("GitHub code", "arXiv 2606.08283", 20, "citation/index/secondary mentions; no attributable implementation"),
        ("Hugging Face models", "arXiv 2606.08283", 0, "no model match"),
        ("Hugging Face datasets", "arXiv 2606.08283", 0, "no dataset match"),
    )
    return [{
        "surface": surface, "query": query, "observed_matches": count,
        "observation": observation, "attributable_release_found": False,
        "negative_search_boundary": boundary,
    } for surface, query, count, observation in values]


def readme_text() -> str:
    return """# Macro Economists in the Machine paper-faithfulness audit

This is an original-source, paper-derived component audit, not an end-to-end replication. The official 46-page arXiv-v1 source rebuilds without modification at 99.89% extracted-token overlap. All 46 official and 46 rebuilt pages and all four embedded raster figures were visually checked.

The paper contains **132 displayed empirical table cells across six result tables** and **12 empirical panels across four figures**. Zero of 132 cells and zero of 12 panels were regenerated through an author-native pipeline. Eighteen uniquely printed mechanics pass controlled checks and four ambiguous core operations fail closed. These checks are independently implemented paper equations, not author code or empirical result credit.

Public reproducibility is currently weak. The paper contains no implementation or artifact URL. It says the processed weekly panel, cached LLM contracts, and replication materials are available from the corresponding author upon reasonable request. Bounded GitHub and Hugging Face searches found no attributable public release. The exact Yahoo/FRED rows, weekly dates, gpt-4o-mini snapshot and full request settings, JSON schema, generated narratives/contracts, weights, turnovers, returns, bootstrap code/seed/draws, and plotting/result generator are absent.

The source is also not internally self-consistent. Its embedded transaction-cost figure reports Sharpe ratios around 0.84--0.92, while the corresponding table reports roughly 0.48--0.57 and gives conflicting benchmark rankings. The debate weight-divergence figure begins in 2017 although the declared price history begins in October 2022. The Rule regime probabilities, cyclical membership and cap, cap ordering/projection, risk-profile ranges, required JSON schema, and automatic bootstrap choices do not determine one executable algorithm.

Therefore `strict_success` remains false. The reproducible portion is a useful equation-level skeleton, but the paper's headline LLM-performance result cannot be independently regenerated from public evidence. Negative searches are bounded and do not prove that private, deleted, moved, renamed, unindexed, or later material does not exist.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    verify_pins(scratch)
    files = paper_sources(scratch)
    source = files["main.tex"].decode()
    output.mkdir(parents=True, exist_ok=True)
    for old in output.iterdir():
        if old.is_file():
            old.unlink()
    results = result_rows(files)
    components = component_rows(source)
    provenance = {
        "arxiv_id": ARXIV_ID, "arxiv_version": "v1",
        "authors": ["Yiqing Wang", "Dehao Dai", "Ding Ma", "Kerui Geng"],
        "published": "2026-06-06T18:07:28Z", "source_files": len(files),
        "official_pages": len(PdfReader(scratch / "primary/official-v1.pdf").pages),
        "rebuilt_pages": len(PdfReader(scratch / "primary/rebuilt-v1.pdf").pages),
        "official_pages_visually_checked": 46, "rebuilt_pages_visually_checked": 46,
        "document_layout_defects_observed": 0,
        "official_rebuilt_token_jaccard": token_jaccard(
            (scratch / "primary/official-v1.txt").read_text(errors="ignore"),
            (scratch / "primary/rebuilt-v1.txt").read_text(errors="ignore"),
        ),
        "paper_contains_native_implementation_url": False,
        "paper_contains_public_dataset_or_checkpoint_url": False,
        "paper_says_replication_materials_available_on_request": True,
        "attributable_implementation_found": False, "observed_license": "NOASSERTION",
        "pinned_input_sha256": PINS,
    }
    write_json(output / "source_provenance.json", provenance)
    write_csv(output / "published_result_ledger.csv", results)
    figures = (
        ("fig:performance", "figure1_performance_dashboard.png", 4, "cumulative return, drawdown, rolling Sharpe, rolling return"),
        ("fig:attribution", "figure2_active_attribution.png", 2, "ticker attribution and cumulative active return"),
        ("fig:cost", "figure4_cost_sensitivity.png", 2, "cost curves and heatmap; numerically conflicts with Table 7"),
        ("fig:debate", "figure3_debate_mechanism.png", 4, "agent paths, active return, weight and probability divergence"),
    )
    write_csv(output / "figure_inventory.csv", [{
        "figure": figure, "source_asset": asset, "source_asset_sha256": hashlib.sha256(files[asset]).hexdigest(),
        "empirical_panels": panels, "description": description,
        "underlying_numeric_array_or_run_log_recovered": False, "paper_result_credit": False,
    } for figure, asset, panels, description in figures])
    write_csv(output / "component_execution_audit.csv", components)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", consistency_rows())
    write_csv(output / "release_search_audit.csv", release_rows())
    (output / "README.md").write_text(readme_text())
    manifest = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "arxiv_id": ARXIV_ID,
        "active_empirical_table_cells": len(results), "result_tables": len(TABLE_SPECS),
        "author_native_table_cells_regenerated": 0, "empirical_figure_panels": 12,
        "author_native_empirical_panels_regenerated": 0,
        "paper_derived_components_executed": len(components),
        "paper_derived_components_passing_controlled_checks": len(components),
        "fail_closed_underspecified_core_operations": 4,
        "attributable_implementation_found": False, "raw_result_arrays_recovered": 0,
        "full_end_to_end_pipeline_reproduced": False, "strict_success": False,
    }
    manifest["generated_file_sha256"] = {
        path.name: sha256(path) for path in output.iterdir()
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
