#!/usr/bin/env python3
"""Build a fail-closed original-paper audit for FactorMAD."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from pypdf import PdfReader

from alpha_evolve import factormad_paper_components as component


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/factormad_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/factormad"
WORK_ID = "CensusDOI10114537682923770377"
SYSTEM_ID = "SYS-FACTOR-MAD"
DOI = "10.1145/3768292.3770377"

PINS = {
    "primary/crossref.json": "70fe521ad1d30e9c4f807dfaed1b0ac313181ae94b51b20195f6ccf20e79c7af",
    "primary/dblp.xml": "1e7fb976f38d3c0e00f5b7fa2bb774556f51f60683e770b35ff87cfcd15d2067",
    "primary/official-acm.pdf": "5fb011bceea232aa52cd36ee0dc14a3238d3e5f5311bfc25af742127298afeab",
    "primary/official-acm.txt": "38b12be2c815e8c50efccc76eb16b326c3780e984243ec681a718054c48c6910",
    "primary/tsinghua-dissertation-summary.html": "8e511784d95312c8e0a7ec1cea388fc9a1f2f954dde89d97b44e94f0d648d04d",
    "discovery/github-code-doi.json": "28accf126d8dbf6a6bb417cb28f9fe2b9d6788e1a7105e227557261345c87345",
    "discovery/github-code-exact.json": "39e9ea068fb2f375179b9b5695db55d9ea3b68b0da441e446320f768ca160081",
    "discovery/github-repositories-doi.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-repositories-exact.json": "32ab944f2ef2864427026cce6de1d79306f0c4b42d12e3c9c5518db03088db2e",
    "discovery/huggingface-datasets-exact.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-models-exact.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-spaces-exact.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}

TABLE_COLUMNS = (
    "CSI300 AR",
    "CSI300 IR",
    "CSI300 RoMaD",
    "CSI500 AR",
    "CSI500 IR",
    "CSI500 RoMaD",
)
TABLE_VALUES = {
    "GP": ("0.004", "0.175", "0.047", "-0.010", "-0.449", "-0.118"),
    "DSO": ("-0.011", "-0.579", "-0.123", "0.070", "2.727", "1.860"),
    "AlphaGen": ("0.017", "0.872", "0.389", "0.052", "2.109", "0.790"),
    "CoE": ("0.046", "2.165", "1.116", "0.047", "1.807", "0.717"),
    "FactorMAD": ("0.063", "2.984", "1.350", "0.086", "3.411", "1.341"),
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


def verify_pins(scratch: Path) -> None:
    for relative, expected in PINS.items():
        observed = sha256(scratch / relative)
        if observed != expected:
            raise ValueError(f"pin mismatch: {relative}={observed}; expected {expected}")


def verify_paper(text: str) -> None:
    normalized = " ".join(text.split())
    markers = (
        "FactorMAD: A Multi-Agent Debate Framework Based on Large Language Models",
        "NY, USA, 9 pages.",
        "including 5255 stocks",
        "01/01/2014 to 12/31/2023",
        "GPT-4o 2024-08-",
        "For each method, we mine 100 factors",
        "we set k = 50 and Δ𝑡 = 10",
        "we set transaction costs at 0.3%",
        "number of trials (100)",
        "rounds (10), and agent initialization information",
    )
    missing = [marker for marker in markers if marker not in normalized]
    if missing:
        raise ValueError(f"paper markers changed or missing: {missing}")
    for method, values in TABLE_VALUES.items():
        pattern = rf"{re.escape(method)}\s+" + r"\s+".join(map(re.escape, values))
        if re.search(pattern, normalized) is None:
            raise ValueError(f"Table 2 row changed or missing: {method}")


def result_rows() -> list[dict[str, Any]]:
    blocker = (
        "no attributable implementation, exact A-share rows/provider, factor library, "
        "prompts/responses, complete model requests, seeds, generated factor programs, "
        "baseline configurations, trained models, predictions, portfolios, returns, "
        "raw arrays, or result generator"
    )
    rows = []
    for row_index, (method, values) in enumerate(TABLE_VALUES.items(), 1):
        for column_index, (column, value) in enumerate(zip(TABLE_COLUMNS, values), 1):
            rows.append({
                "table": "Table 2",
                "row_index": row_index,
                "method": method,
                "quantitative_column_index": column_index,
                "metric": column,
                "printed_cell": value,
                "unit_definition": "one populated displayed empirical quantitative table cell",
                "source_document_recovered": True,
                "raw_result_record_recovered": False,
                "author_native_experiment_executed": False,
                "published_result_regenerated": False,
                "paper_result_credit": False,
                "blocking_reason": blocker,
            })
    if len(rows) != 30:
        raise ValueError(f"Table 2 denominator changed: {len(rows)}")
    return rows


def component_rows() -> list[dict[str, Any]]:
    checks = (
        ("future_vwap_return", component.future_vwap_return([100, 110, 121], time_index=0, horizon=1), 0.1),
        ("alternating_proposer", [component.proposing_agent_index(i) for i in range(4)], [0, 1, 0, 1]),
        ("seed_source_branch", [
            component.choose_seed_source(uniform_draw=0.2, seed_probability=0.3),
            component.choose_seed_source(uniform_draw=0.3, seed_probability=0.3),
        ], ["existing_factor", "generated_factor"]),
        ("strict_factor_acceptance", [
            component.accept_factor(metric=0.03, maximum_correlation=0.4, metric_threshold=0.02, correlation_threshold=0.5),
            component.accept_factor(metric=0.02, maximum_correlation=0.4, metric_threshold=0.02, correlation_threshold=0.5),
        ], [True, False]),
        ("equal_weight_top_k", component.equal_weight_top_k([1, 3, 2], 2), [0.0, 0.5, 0.5]),
        ("ordinary_noncomment_line_count", component.noncomment_code_lines("# note\nx = 1\n\ny = 2  # inline\n"), 2),
    )
    rows = []
    for name, observed, expected in checks:
        if isinstance(expected, float):
            passed = math_isclose(observed, expected)
        else:
            passed = observed == expected
        rows.append({
            "component": name,
            "controlled_output": json.dumps(observed),
            "deterministic_control_passed": passed,
            "paper_derived_not_author_code": True,
            "author_native_pipeline_executed": False,
            "published_result_regenerated": False,
            "paper_result_credit": False,
            "boundary": component.PAPER_BOUNDARY,
        })
    fail_closed = (
        ("agent_initialization", component.initialize_agents),
        ("factor_code_validation", component.validate_factor_code),
        ("factor_code_correction", component.correct_factor_code),
        ("prediction_model_training", component.train_prediction_models),
        ("overlapping_topk_portfolios", component.combine_overlapping_top_k_portfolios),
        ("investment_metrics", component.calculate_investment_metrics),
        ("llm_request", lambda: component.reproduce_llm_request({})),
    )
    for name, operation in fail_closed:
        try:
            operation()
        except component.UnderspecifiedPaperMechanic as exc:
            rows.append({
                "component": name,
                "controlled_output": str(exc),
                "deterministic_control_passed": True,
                "paper_derived_not_author_code": True,
                "author_native_pipeline_executed": False,
                "published_result_regenerated": False,
                "paper_result_credit": False,
                "boundary": component.PAPER_BOUNDARY,
            })
        else:
            raise ValueError(f"{name} did not fail closed")
    return rows


def math_isclose(left: float, right: float) -> bool:
    return abs(left - right) < 1e-12


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official paper", "complete", "publisher PDF for DOI 10.1145/3768292.3770377 pinned; all nine pages visually checked"),
        ("paper source archive", "unavailable", "ACM exposes the PDF/HTML article but no TeX or source archive"),
        ("native implementation", "unreleased", "paper contains no code URL; bounded searches find no attributable repository, model, dataset, or Space"),
        ("paper artifact statement", "absent", "no code, data, model, or reproducibility availability statement is printed"),
        ("market universe", "substantial", "5255 Shanghai/Shenzhen A-share stocks are stated, but identifiers and membership-by-date are absent"),
        ("market period", "nominal", "01/01/2014--12/31/2023, in-sample 2014--2021, out-of-sample 2022--2023"),
        ("market fields", "complete_names_only", "daily high/open/low/close/VWAP/amount/volume are named without immutable rows or schema"),
        ("data provider and adjustments", "missing", "provider, query date, exchange calendar, suspensions, listings/delistings, corporate actions, limits, and missing values are absent"),
        ("label", "equation_complete", "future VWAP return VWAP[t+h+1]/VWAP[t+1]-1; mining horizon 10 days"),
        ("initial factor library", "missing", "existing factor programs, metrics, provenance, size, and construction are absent"),
        ("agent example sampling", "underspecified", "random subsets are named without k, distribution, replacement, or seed"),
        ("factor and seed prompts", "missing", "pi_alpha, pi_seed, perspective-summary and correction prompts are symbolic placeholders only"),
        ("LLM model", "dated_name_only", "GPT-4o 2024-08-06 is stated without provider API revision, parameters, seed, request/response log, or environment"),
        ("debate structure", "substantial", "two initialized agents alternate summary, critique and factor proposals; exact serialization/context limits are absent"),
        ("seed selection", "equation_partial", "existing-versus-generated branch printed, but p_seed value and generated-seed prompt are absent"),
        ("debate stopping", "partial", "ten rounds are stated for the ablation; general convergence criteria are not executable"),
        ("factor acceptance", "equation_partial", "strict metric/correlation gate printed, but epsilon_1, epsilon_2, correlation convention and comparison set are absent"),
        ("code generation contract", "partial", "Python function, input/output, library and example requirements are described but no full contract or examples are released"),
        ("code validator", "prose_only", "eleven error categories/suggestions are printed without executable checks or thresholds"),
        ("correction agent", "underspecified", "correction loop is printed without prompt, model settings, K, retry serialization, or terminal failure policy"),
        ("factor mining count", "complete_nominal", "100 factors are mined per method"),
        ("baselines", "names_only", "GP, DSO, AlphaGen and CoE are named without exact forks, commits, configs, seeds, budgets, or generated factors"),
        ("prediction models", "partial", "LR, three-layer MLP and LightGBM are named without hyperparameters, training schedule, seeds, or checkpoints"),
        ("prediction horizons", "complete_nominal", "10, 20 and 30 trading-day labels are evaluated"),
        ("rank normalization", "underspecified", "cross-sectional rank normalization is named without formula, centering, tie, missing-value, or temporal policy"),
        ("prediction metrics", "partial", "IC, RankIC, MSE and AUC are described without exact aggregation, sign/rank preprocessing, tie, or averaging conventions"),
        ("portfolio construction", "partial", "daily Top-50 equal-weight selection, 10-day holding period and CSI300/CSI500 benchmarks are stated"),
        ("overlapping holdings", "missing", "daily selection plus ten-day holding does not define how overlapping vintages combine"),
        ("transaction cost", "partial", "0.3% is stated without one-way/round-trip interpretation, turnover formula, or application timing"),
        ("investment metrics", "partial", "AR, IR and RoMaD prose lacks annualization, return alignment, denominator and drawdown conventions"),
        ("randomness and trials", "partial", "100 ablation trials are stated; all seeds, trial reuse and confidence/reporting conventions are absent"),
        ("raw empirical outputs", "missing", "no factor code, LLM trace, predictions, model artifacts, positions, returns, plot arrays, or result generator is released"),
    )
    return [{"dimension": dimension, "status": status, "evidence": evidence} for dimension, status, evidence in specs]


def consistency_rows() -> list[dict[str, str]]:
    values = (
        ("highest_performance_claim", "direct_numeric_conflict", "prose says FactorMAD achieves the highest Table 2 performance, but DSO's CSI500 RoMaD is 1.860 versus FactorMAD's 1.341"),
        ("rank_normalization_auc_labels", "definition_conflict", "labels are said to undergo rank normalization and AUC then labels raw returns above/below zero; an uncentered percentile rank has no negatives, while a centered rank changes the classification target"),
        ("annual_return_definition", "metric_conflict", "Table 2 metrics are said to be calculated from cumulative excess returns relative to the benchmark, yet AR is described as absolute performance"),
        ("figure3_average_population", "aggregation_undefined", "four Average panels do not state whether values average factors, dates, horizons, trials, model seeds, or some combination"),
        ("figure4_result_arrays", "static_only", "two cumulative-return panels expose curves but no underlying dates, benchmark/portfolio returns, cost deductions, or arrays"),
        ("factor_complexity_interpretability", "proxy_only", "non-comment line count is treated as complexity and interpretability without syntax, semantic, dependency, or financial-rationale measures"),
        ("daily_topk_ten_day_hold", "algorithm_underspecified", "daily TopK formation and a ten-day holding period leave overlapping portfolio vintages undefined"),
        ("metric_gate_thresholds", "algorithm_underspecified", "Algorithm 1 requires epsilon_1 and epsilon_2 but the experiment never reports their values"),
        ("correction_limit", "algorithm_underspecified", "Algorithm 1 requires maximum corrections K but no value or terminal failure behavior is reported"),
        ("seed_probability", "algorithm_underspecified", "Equation 3 requires p_seed but no experimental value is reported"),
        ("prompt_claim", "claim_artifact_gap", "the method depends on several prompts and code requirements, but no complete prompt or runnable contract is printed or released"),
        ("figure_values", "display_precision_unavailable", "Figures 3--6 are vector/static document evidence without printed point values or run lineage"),
    )
    return [{"check": check, "status": status, "evidence": evidence} for check, status, evidence in values]


def release_rows() -> list[dict[str, Any]]:
    boundary = "bounded search cannot exclude private, deleted, moved, renamed, unindexed, or later releases"
    values = (
        ("GitHub repositories", "exact FactorMAD", 2, "two unaffiliated secondary skills created in June/July 2026; neither is an author-native release"),
        ("GitHub repositories", "DOI 10.1145/3768292.3770377", 0, "no repository match"),
        ("GitHub code", "exact FactorMAD", 192, "citations, indexes, and secondary adaptations; no attributable implementation identified"),
        ("GitHub code", "DOI 10.1145/3768292.3770377", 14, "citations/indexes and secondary skills; no attributable implementation identified"),
        ("Hugging Face models", "FactorMAD", 0, "no model match"),
        ("Hugging Face datasets", "FactorMAD", 0, "no dataset match"),
        ("Hugging Face Spaces", "FactorMAD", 0, "no Space match"),
        ("Tsinghua dissertation system", "first-author dissertation", 1, "official abstract recovered; full 147-page dissertation preview requires authentication and is not treated as paper source or system code"),
    )
    return [{
        "surface": surface,
        "query": query,
        "observed_matches": count,
        "observation": observation,
        "attributable_release_found": False,
        "negative_search_boundary": boundary,
    } for surface, query, count, observation in values]


def proxy_rows() -> list[dict[str, Any]]:
    return [{
        "local_candidate": "paper_factormad_debate_interpretable",
        "local_method": "rank(be_me)+rank(ope_be)+rank(qmj_safety)+rank(ret_12_1)-rank(debt_at)-rank(rvol_252d)",
        "local_data": "JKP monthly U.S. characteristics, 2001--2024",
        "paper_data": "daily China A-shares, 2014--2023, seven price/volume fields",
        "paper_method_present": False,
        "two_agent_debate_present": False,
        "llm_factor_code_generation_present": False,
        "paper_prediction_models_present": False,
        "paper_portfolio_present": False,
        "paper_result_credit": False,
        "classification": "M0_narrative_translation_in_spirit_only",
        "boundary": "a favorable title-derived multifactor proxy is not a replication of FactorMAD",
    }]


def readme_text() -> str:
    return """# FactorMAD paper-faithfulness audit

This is an original-paper, paper-derived component audit, not an end-to-end replication. The official nine-page ACM proceedings PDF for DOI 10.1145/3768292.3770377 is pinned, its text is extracted, and all nine pages are visually checked. ACM provides no source archive. An official first-author Tsinghua dissertation record confirms FactorMAD as a dissertation contribution, but its 147-page full-text preview requires authentication; the abstract is supporting lineage evidence, not a substitute for the proceedings paper.

The paper contains **30 displayed empirical table cells in one result table** and **eight empirical panels across four figures**. Zero of 30 cells and zero of eight panels were regenerated through an author-native pipeline. Six uniquely printed mechanics pass controlled checks and seven core operations fail closed because the paper does not determine one executable procedure. These checks are independently implemented paper mechanics, not author code or empirical result credit.

The paper provides useful high-level constraints: 5,255 Shanghai/Shenzhen A-share stocks; seven daily price/volume fields; a 2014--2023 window split into 2014--2021 and 2022--2023; a future-VWAP label; GPT-4o 2024-08-06; 100 factors per method; LR, three-layer MLP and LightGBM models; 10/20/30-day horizons; a daily equal-weight Top-50 portfolio held ten days; and 0.3% transaction costs. But it releases no attributable implementation, exact data rows/provider, factor library, prompts, model requests/responses, generated factor programs, seeds, baseline configurations, trained models, predictions, positions, returns, plot arrays, or result generator. Essential values and rules are omitted: example count and sampling, `p_seed`, both acceptance thresholds, maximum corrections `K`, validator implementation, rank-normalization convention, model hyperparameters, overlapping-holding treatment, cost application, and precise AR/IR/RoMaD definitions.

The paper is not internally self-consistent. It says FactorMAD achieves the highest Table 2 performance, while DSO's printed CSI500 RoMaD is 1.860 versus FactorMAD's 1.341. It says labels are rank normalized, then defines AUC classes from returns above or below zero without specifying a centered rank transform. It says Table 2 metrics derive from cumulative excess return, yet calls AR absolute performance. Figure 3's averaging population is undefined, and Figures 3--6 provide no underlying arrays.

The existing local `paper_factormad_debate_interpretable` candidate is a title-derived U.S. monthly JKP multifactor portfolio. It contains no LLM, agent initialization, debate, code generation, validation/correction loop, China A-share data, paper prediction model, or paper portfolio construction. It remains an M0 in-spirit narrative translation and receives no FactorMAD method or result credit.

Therefore `strict_success` is false. The honest public replication frontier is a small executable specification skeleton plus a complete result-denominator and missing-artifact ledger, not a faithful empirical reproduction. Negative searches are bounded and do not prove that private, deleted, moved, renamed, unindexed, or later material does not exist.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    verify_pins(scratch)
    text = (scratch / "primary/official-acm.txt").read_text(errors="ignore")
    verify_paper(text)
    reader = PdfReader(scratch / "primary/official-acm.pdf")
    if len(reader.pages) != 9:
        raise ValueError(f"official page count changed: {len(reader.pages)}")
    crossref = json.loads((scratch / "primary/crossref.json").read_text())["message"]
    expected_title = "FactorMAD: A Multi-Agent Debate Framework Based on Large Language Models for Interpretable Stock Alpha Factor Mining"
    if crossref["DOI"] != DOI or crossref["title"] != [expected_title]:
        raise ValueError("Crossref identity changed")

    output.mkdir(parents=True, exist_ok=True)
    for old in output.iterdir():
        if old.is_file():
            old.unlink()

    results = result_rows()
    components = component_rows()
    provenance = {
        "doi": DOI,
        "title": expected_title,
        "authors": ["Yitong Duan", "Chuheng Zhang", "Jian Li"],
        "venue": "ICAIF '25",
        "published": "2025-11-14",
        "publisher_pages": "605-613",
        "official_pdf_pages": len(reader.pages),
        "official_pdf_bytes": (scratch / "primary/official-acm.pdf").stat().st_size,
        "official_pages_visually_checked": 9,
        "document_layout_defects_observed": 0,
        "paper_source_archive_found": False,
        "paper_contains_native_implementation_url": False,
        "paper_contains_public_dataset_model_or_result_url": False,
        "paper_contains_reproducibility_statement": False,
        "attributable_implementation_found": False,
        "official_first_author_dissertation_summary_recovered": True,
        "official_first_author_dissertation_full_text_recovered": False,
        "dissertation_full_text_access_observation": "online preview requires authentication",
        "observed_license": "NOASSERTION; PDF says publication rights licensed to ACM",
        "pinned_input_sha256": PINS,
    }
    write_json(output / "source_provenance.json", provenance)
    write_csv(output / "published_result_ledger.csv", results)

    figures = (
        ("Figure 1", 0, 0, "conceptual FactorMAD framework"),
        ("Figure 2", 0, 0, "conceptual four-phase factor-development workflow"),
        ("Figure 3", 4, 60, "IC, RankIC, MSE and AUC bar panels; 15 bars per panel"),
        ("Figure 4", 2, 12, "CSI300/CSI500 cumulative-return panels; six series per panel"),
        ("Figure 5", 1, 44, "four IC series across 11 iterations"),
        ("Figure 6", 1, 22, "two mean code-line series across 11 iterations plus uncertainty ribbons"),
    )
    write_csv(output / "figure_inventory.csv", [{
        "figure": figure,
        "empirical_panels": panels,
        "visible_primary_marks_or_series": marks,
        "description": description,
        "official_pdf_sha256": PINS["primary/official-acm.pdf"],
        "underlying_numeric_array_or_run_log_recovered": False,
        "author_native_panel_regenerated": False,
        "paper_result_credit": False,
    } for figure, panels, marks, description in figures])
    write_csv(output / "component_execution_audit.csv", components)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", consistency_rows())
    write_csv(output / "release_search_audit.csv", release_rows())
    write_csv(output / "local_proxy_boundary.csv", proxy_rows())
    (output / "README.md").write_text(readme_text())

    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "doi": DOI,
        "active_empirical_table_cells": len(results),
        "result_tables": 1,
        "author_native_table_cells_regenerated": 0,
        "empirical_figure_panels": 8,
        "author_native_empirical_panels_regenerated": 0,
        "paper_derived_components_executed": len(components),
        "paper_derived_components_passing_controlled_checks": len(components),
        "fail_closed_underspecified_core_operations": 7,
        "attributable_implementation_found": False,
        "raw_result_arrays_recovered": 0,
        "full_end_to_end_pipeline_reproduced": False,
        "local_m0_proxy_receives_paper_credit": False,
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
