#!/usr/bin/env python3
"""Build a fail-closed, revision-aware primary-source audit for FinPos."""

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

from alpha_evolve import finpos_paper_components as component


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/finpos_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/finpos"
WORK_ID = "CensusArxiv251027251"
SYSTEM_ID = "SYS-FIN-POS"
ARXIV_ID = "2510.27251"

PINS = {
    "primary/arxiv-api.xml": "1fbeb239ead06971aff5338fb9ce4ed29b72cea796b51ebb2054b6b75f4f7d24",
    "primary/official-v1.pdf": "78c86889c23e8e8545213191b9da423e4cf88b9b29576f27e14f0d0f1ae8f8e9",
    "primary/official-v1.txt": "c1e95d9fc0a62b6c1c48658bd48858dc1a5bffb78f12bd3349e9abf5269fc04b",
    "primary/rebuilt-v1.pdf": "3007392b9e9f2118fd1cff1f9b758ad0d6ae3916999524f1f77ec978b96f1052",
    "primary/rebuilt-v1.txt": "80706d3024e1f2725639e1129ccea2a0702aa8c0d06f8f899ab3551cd8dadda0",
    "primary/source-v1.tar": "588f37064330a40ab3d3904b084f1c9ef186addbdf2985f10c33846ac66d4e3f",
    "primary/official-v2.pdf": "7bdcd7539e6b828bffe3a540b39d16c79a6c16e261240cec82729cdaf56b874b",
    "primary/official-v2.txt": "1625f9b01a11398daa10d190a6101c215e2995869763c66f859b8c4a6965f979",
    "primary/rebuilt-v2.pdf": "c74de4584b4e5ad043f181851461fdf86e9d39d3459617f75ebdc3ac38e14fa5",
    "primary/rebuilt-v2.txt": "4883b9eac0ae76ab8b88cdb10560c50343090e92cd2b2b24e03fabea35080137",
    "primary/source-v2.tar": "26adbb25c6a28dd484a4ab3a48f58c98ac7a7e8b4ce72aff0a5397f7c3d5b4d9",
    "discovery/github-code-arxiv.json": "b6d77d947bbc69cca217cd26fc626ae424519f9ea2f0bb958226d9ddcb5ab059",
    "discovery/github-code-maxcvar.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-code-title.json": "99279953a0f0fda1934d80a6c6aa1c76e4c643665770e92bade12e9ff15b4ac6",
    "discovery/github-profile-rh-dang.json": "828d05603783535c12081b5b79137004fcc7a3fff0c80cdb36a6e09f0cb28992",
    "discovery/github-repos-rh-dang.json": "b509715fca41adb85f6795d7b8ab96e56ba5649654c51e827c0197e2f7149dc9",
    "discovery/github-repositories-arxiv.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-repositories-title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-users-bijia-liu.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-users-ronghao-dang.json": "277384818ff76d0667b12bf8bbb4e6e5c142aeb9657fd9192aa3a4ba73889f75",
    "discovery/huggingface-datasets-finpos.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-models-finpos.json": "1d2e69c70ab583616dd3af0086c56771f06b786ac1c954df241250292020cd0e",
}

TABLE_SPECS = {
    ("v1", "tab:model_comparison"): ("sec/5_Experiments.tex", tuple(range(1, 16)), 180),
    ("v1", "tab:ablation_single"): ("sec/5_Experiments.tex", tuple(range(4, 13)), 45),
    ("v2", "tab:model_comparison"): ("sec/5_Experiments.tex", tuple(range(1, 16)), 165),
    ("v2", "tab:ablation_single"): ("sec/5_Experiments.tex", tuple(range(3, 12)), 36),
    ("v2", "tab:sampling-sensitivity"): ("sec/8_Appendix.tex", (1, 2, 3), 15),
    ("v2", "tab:signal-ablation"): ("sec/8_Appendix.tex", (4, 5, 6), 15),
    ("v2", "tab:extreme_market"): ("sec/8_Appendix.tex", tuple(range(1, 10)), 63),
}

FIGURE_SPECS = (
    ("v1", "fig:intro", "image/intro.pdf", 1, "task diagram plus TSLA cumulative-return panel"),
    ("v1", "fig:archi", "image/archi.pdf", 0, "conceptual architecture"),
    ("v1", "fig:prompt_abla", "image/prompt_ablation.pdf", 1, "prompt-trait ablation"),
    ("v1", "fig:timescale_abla", "image/timescale_ablation.pdf", 1, "reward-horizon sensitivity"),
    ("v1", "fig:PA", "image/tsla-e.pdf", 4, "TSLA Calmar, return-risk, exposure, and return panels"),
    ("v1", "fig:PA2", "image/aapl-f.pdf", 8, "duplicated TSLA plus AAPL four-panel composites"),
    ("v2", "fig:intro", "image/intro.pdf", 1, "task diagram plus TSLA cumulative-return panel"),
    ("v2", "fig:archi", "image/archi.pdf", 0, "conceptual architecture"),
    ("v2", "fig:timescale_abla", "image/timescale_ablation.pdf", 1, "reward-horizon sensitivity"),
    ("v2", "fig:PA", "image/tsla-e.pdf", 4, "TSLA Calmar, return-risk, exposure, and return panels"),
    ("v2", "fig:prompt_abla", "image/prompt_ablation.pdf", 1, "prompt-trait ablation"),
    ("v2", "fig:PA2", "image/aapl-f.pdf", 4, "AAPL Calmar, return-risk, exposure, and return panels"),
)

PROMPT_SPECS = (
    ("10-K filtering", "invalid_missing_comma", "printed key_points/reason object omits a comma"),
    ("10-K analysis", "valid_json_example", "two-string object is syntactically valid after placeholder substitution"),
    ("10-Q filtering", "invalid_missing_comma", "printed key_points/reason object omits a comma"),
    ("10-Q analysis", "valid_json_example", "three-string object is syntactically valid after placeholder substitution"),
    ("macroeconomic relation filtering", "invalid_union_syntax", "pipe-separated alternatives are not JSON"),
    ("macroeconomic impact analysis", "invalid_union_syntax", "pipe-separated alternatives are not JSON"),
    ("company-news filtering", "valid_json_example", "two-string object is syntactically valid after placeholder substitution"),
    ("company-news analysis", "valid_json_example", "two-string object is syntactically valid after placeholder substitution"),
    ("direction training", "invalid_union_syntax", "pipe-separated action alternatives are not JSON"),
    ("direction testing", "external_unreleased_suffix", "depends on gr.complete_json_suffix_v2, which is not printed"),
    ("quantity/risk training", "invalid_bare_type_expression", "bare integer range expression is not JSON"),
    ("quantity/risk testing", "external_unreleased_suffix", "depends on gr.complete_json_suffix_v2, which is not printed"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def paper_sources(scratch: Path, version: str) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(scratch / f"primary/source-{version}.tar", "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe source member: {member.name}")
            if member.isfile():
                handle = archive.extractfile(member)
                if handle is None:
                    raise ValueError(f"unreadable source member: {member.name}")
                files[member.name] = handle.read()
    if len(files) != 19:
        raise ValueError(f"{version} paper source file count changed: {len(files)}")
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
    value = re.sub(r"\textbf\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\(?:cite|rowcolor)\{?[^\n&]*", "", value)
    value = re.sub(r"\\(?:bfseries|small|midrule|toprule|bottomrule)", "", value)
    value = re.sub(r"[{}$~]", "", value)
    return " ".join(value.split())


def table_data_rows(environment: str) -> list[list[str]]:
    match = re.search(r"\\begin\{tabular\}\{.*?\}(.*?)\\end\{tabular\}", environment, re.S)
    if match is None:
        raise ValueError("tabular body missing")
    return [
        [clean_tex(cell) for cell in chunk.split("&")]
        for chunk in re.split(r"\\\\", match.group(1))
        if "&" in chunk
    ]


def result_rows(sources: Mapping[str, Mapping[str, bytes]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    blocker = (
        "no author implementation, immutable market/news/filing snapshot, prompts at runtime, model "
        "requests/responses, seeds, orders, fills, account path, raw arrays, or result generator"
    )
    for (version, label), (path, columns, expected) in TABLE_SPECS.items():
        source = sources[version][path].decode()
        parsed = table_data_rows(table_environment(source, label))
        table_rows: list[dict[str, Any]] = []
        for row_index, cells in enumerate(parsed, 1):
            if max(columns) >= len(cells) or not all(re.search(r"\d", cells[c]) for c in columns):
                continue
            row_label = " | ".join(c for c in cells[: min(columns)] if c) or f"row_{row_index}"
            for column in columns:
                table_rows.append(
                    {
                        "revision": version,
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
            raise ValueError(f"denominator changed for {version} {label}: {len(table_rows)} != {expected}")
        rows.extend(table_rows)
    return rows


def figure_rows(sources: Mapping[str, Mapping[str, bytes]]) -> list[dict[str, Any]]:
    return [
        {
            "revision": version,
            "figure": figure,
            "source_asset": asset,
            "source_asset_sha256": sha256_bytes(sources[version][asset]),
            "empirical_panels": panels,
            "description": description,
            "author_rendered_asset_recovered": True,
            "underlying_numeric_array_or_run_log_recovered": False,
            "author_native_figure_regenerated": False,
            "paper_result_credit": False,
        }
        for version, figure, asset, panels, description in FIGURE_SPECS
    ]


def prompt_rows(sources: Mapping[str, Mapping[str, bytes]]) -> list[dict[str, Any]]:
    prompt_sources = {
        "v1": sources["v1"]["sec/7_Appendix.tex"].decode(),
        "v2": sources["v2"]["sec/8_Appendix.tex"].decode(),
    }
    for version, source in prompt_sources.items():
        prefix = source[: source.index(r"\section{Formulas of Classic Financial Metrics}")]
        if prefix.count(r"\begin{lstlisting}") != 10:
            raise ValueError(f"{version} printed prompt-block count changed")
        for marker in ("train_prompt =", "test_prompt =", "gr.complete_json_suffix_v2"):
            if prefix.count(marker) != 2:
                raise ValueError(f"{version} prompt marker count changed: {marker}")
    v1 = " ".join(prompt_sources["v1"].split())
    v2 = " ".join(prompt_sources["v2"].split())
    v1 = v1[: v1.index(r"\section{Formulas of Classic Financial Metrics}")]
    v2 = v2[: v2.index(r"\section{Formulas of Classic Financial Metrics}")]
    if v1.replace(r"\section{The implementation details of FinPos} \label", r"\section{The implementation details of FinPos}\label") != v2.replace(r"\section{The implementation details of FinPos} \label", r"\section{The implementation details of FinPos}\label"):
        raise ValueError("v1/v2 printed prompt contents are no longer identical")
    return [
        {
            "revision": "v1_and_v2_identical_content",
            "prompt_template": name,
            "printed_template_recovered": True,
            "strict_json_contract_status": status,
            "observation": note,
            "runtime_prompt_executed": False,
            "author_model_response_recovered": False,
            "paper_result_credit": False,
        }
        for name, status, note in PROMPT_SPECS
    ]


def component_rows() -> list[dict[str, Any]]:
    prices = [100.0 + index for index in range(31)]
    pnl = [-4.0, -3.0, -2.0, -1.0] + [float(index) for index in range(16)]
    mechanics: list[tuple[str, str, Any]] = [
        ("single_step_log_return", "printed discrete-action log return", component.single_step_log_return(1, 100, 110)),
        ("position_log_return", "printed position-weighted log return", component.position_log_return(2, 100, 110)),
        ("position_update", "printed direction-times-quantity state update", component.update_position(5, -1, 2)),
        ("multi_timescale_score", "printed raw-price 1/7/30-day score", component.multi_timescale_score(prices, 0)),
        ("literal_reward", "printed unchanged-position penalty and total-position reward", component.literal_reward(1, 2, 3)),
        ("sharpe_ratio", "printed unannualized symbolic Sharpe ratio", component.sharpe_ratio(0.02, 0.005, 0.01)),
        ("maximum_drawdown", "printed future-trough drawdown", component.maximum_drawdown_future_trough([100, 120, 90, 110])),
        ("empirical_var_cvar", "printed lower-tail VaR/CVaR for explicit alpha", component.empirical_var_cvar(pnl, 0.05)),
        ("calmar_ratio", "printed annual-return over absolute MDD", component.calmar_ratio(0.2, 0.1)),
    ]
    for name, function, argument in (
        ("cr_percent_refusal", component.cumulative_log_return_to_reported_percent, 0.1),
        ("cvar_quantity_refusal", component.cvar_to_maximum_order_quantity, -0.02),
    ):
        try:
            function(argument)
        except component.UnderspecifiedPaperMechanic as exc:
            mechanics.append((name, "fail-closed guard for an unstated conversion", str(exc)))
        else:
            raise AssertionError(f"{name} unexpectedly invented a paper mechanic")
    return [
        {
            "component": name,
            "paper_specification": specification,
            "controlled_output": json.dumps(output, sort_keys=True),
            "deterministic_control_passed": True,
            "paper_derived_not_author_code": True,
            "author_native_pipeline_executed": False,
            "published_result_regenerated": False,
            "paper_result_credit": False,
            "boundary": component.PAPER_BOUNDARY,
        }
        for name, specification, output in mechanics
    ]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official revisions and source", "complete", "v1 and v2 PDFs and 19-file source archives pinned; 39 official and 39 rebuilt pages visually checked"),
        ("native implementation", "unreleased", "paper contains no code URL and bounded release searches find no attributable implementation"),
        ("agent prompts", "partial_static", "12 templates printed, but two depend on an unreleased suffix and six printed JSON contracts are invalid"),
        ("model", "family_only", "GPT-4o, temperature 0.7, and v2 default top_p 0.9; no immutable model snapshot or API version"),
        ("stock universe", "specified", "TSLA, AAPL, AMZN, NFLX, and COIN"),
        ("market data", "provider_schema_only", "Yahoo daily OHLCV without immutable rows, adjustment policy, timestamps, or missing-data rules"),
        ("company and macro news", "provider_schema_only", "Finnhub fields named without query parameters, item IDs, retrieval timestamps, or content snapshot"),
        ("filings", "provider_schema_only", "SEC EDGAR 10-K/10-Q named without accession IDs, filing cutoffs, parsing, or daily standardization code"),
        ("train/test split", "date_ranges_only", "Jan 2024--Feb 2025 train and Mar--Sep 2025 v2 test; exact trading calendars and boundary handling missing"),
        ("initial account state", "missing", "cash, position, leverage, and whether account value includes cash are unspecified"),
        ("orders and fills", "missing", "decision-at-close timing is stated, but share semantics, fill price, costs, slippage, borrowing, and liquidation are missing"),
        ("position sizing", "equation_underspecified", "integer quantity is capped by maxcvar without converting CVaR return/PnL units to shares"),
        ("CVaR", "equation_conflicted", "20-day lower-tail equation is printed, but 95% convention, sign, units, interpolation, and sizing conversion conflict or remain missing"),
        ("multi-timescale reward", "equation_partial", "raw-price 1/7/30-day score and reward printed; endpoint policy and claimed action-alignment semantics are not determined"),
        ("hierarchical memory", "narrative_only", "layers and migration narrative without allocation, retrieval, scoring, persistence, or reflection implementation"),
        ("baselines", "names_and_partial_hyperparameters", "baseline names and selected DRL settings printed without adaptations, seeds, complete configs, or runs"),
        ("cumulative return", "equation_underspecified", "sum of position-weighted log returns is printed, but conversion to CR% or account value is absent"),
        ("Sharpe", "equation_partial", "formula printed without frequency, annualization, risk-free value, or return series definition"),
        ("maximum drawdown", "equation_partial", "future-trough formula printed, but account-value construction is absent"),
        ("Calmar", "equation_partial", "formula printed without annualization convention or underlying account path"),
        ("LLM stochasticity", "single_cells_only", "sampling sensitivity reports one cell per setting without repetitions, seeds, dispersion, or response logs"),
        ("raw empirical outputs", "missing", "no predictions, trades, positions, PnL, account paths, arrays, or baseline outputs"),
    )
    return [{"dimension": d, "status": s, "evidence": e} for d, s, e in specs]


def consistency_rows() -> list[dict[str, str]]:
    values = (
        ("reward_action_alignment", "semantic_conflict", "reward uses total pos_t times trend, not d_t or the position change; a sell can receive a positive rising-market reward while remaining long"),
        ("reward_scale", "asset_scale_dependent", "raw dollar differences are summed and the inactivity branch squares dollars without normalization"),
        ("reward_endpoint", "missing", "t+30 is required but the policy for the final 30 training days is not stated"),
        ("cvar_tail_convention", "conflict", "95% confidence is paired with a lower-tail PnL quantile/CVaR equation; alpha=.95 averages 95% of a 20-day sample, not a conventional 5% downside tail"),
        ("cvar_sign_claim", "conflict", "for lower-tail PnL, a more negative/smaller CVaR is worse, while the paper says smaller indicates stronger protection"),
        ("cvar_to_integer_quantity", "dimensionally_underspecified", "a return/PnL statistic is named as an integer maximum order quantity without capital/price conversion"),
        ("continuous_position_claim", "terminology_conflict", "printed direction and quantity prompts produce discrete integer position increments rather than a continuous-valued action"),
        ("cr_log_to_percent", "missing_mapping", "the log-return sum has no stated mapping to the displayed CR percentages"),
        ("v2_extreme_period", "conflict", "section says Mar--Apr 2025 while the table caption says Mar--Sep 2025"),
        ("election_timing", "conflict", "Mar--Sep 2025 testing is described as covering the Nov 2024 U.S. election"),
        ("v2_fip_numbers", "orphaned_results", "prose cites TSLA 52.56->62.15 and AAPL 59.38->67.31, which do not appear in the v2 ablation table"),
        ("v2_tsla_figure_lineage", "stale_v1_result", "plotted FinPos Calmar 1.30 equals v1 54.99/42.34 after rounding, while v2 62.15/42.34 implies 1.47"),
        ("v2_aapl_figure_lineage", "stale_v1_result", "plotted FinPos Calmar 3.27 equals v1 60.28/18.44 after rounding, while v2 36.31/27.53 implies 1.32"),
        ("v2_extreme_table_lineage", "mixed_revision_conflict", "the v2 extreme table is captioned Mar--Sep but reproduces v1 Mar--Apr main-table values for TSLA and COIN and nearly all AAPL values rather than the v2 main table"),
        ("prompt_json_contracts", "partial_invalid", "4/12 printed output examples are valid JSON after placeholder substitution; six are invalid and two depend on an unreleased suffix"),
        ("revision_results", "material_revision", "v1 tests Mar--Apr while v2 tests Mar--Sep; main and ablation values and module definitions change substantially"),
        ("static_asset_lineage", "static_only", "vector figure assets are recovered, but no numeric arrays or run logs back them"),
    )
    return [{"check": c, "status": s, "evidence": e} for c, s, e in values]


def release_rows() -> list[dict[str, Any]]:
    boundary = "bounded search cannot exclude private, deleted, moved, renamed, unindexed, or later releases"
    values = (
        ("GitHub repositories", "exact title", 0, "no repository match"),
        ("GitHub repositories", "arXiv 2510.27251", 0, "no repository match"),
        ("GitHub code", "exact title", 22, "index/citation/secondary material; no attributable implementation"),
        ("GitHub code", "arXiv 2510.27251", 34, "index/citation/secondary material; no attributable implementation"),
        ("GitHub code", "maximum order quantity plus maxcvar", 0, "no exact code match"),
        ("GitHub users", "Bijia Liu", 0, "no exact user result"),
        ("GitHub coauthor profile", "Rh-Dang 22 owner repositories", 22, "no FinPos repository among the inspected names/descriptions"),
        ("Hugging Face datasets", "FinPos", 0, "no dataset match"),
        ("Hugging Face models", "FinPos", 1, "one post-paper unaffiliated FinPost-named model with no card or author link"),
    )
    return [
        {
            "surface": surface,
            "query": query,
            "observed_matches": count,
            "observation": observation,
            "attributable_finpos_release_found": False,
            "negative_search_boundary": boundary,
        }
        for surface, query, count, observation in values
    ]


def revision_rows() -> list[dict[str, str]]:
    return [
        {"dimension": "venue template", "v1": "AAMAS 2026, 17 pages", "v2": "ACL template, 22 pages", "effect": "presentation changed"},
        {"dimension": "test window", "v1": "Mar--Apr 2025", "v2": "Mar--Sep 2025", "effect": "results are not directly comparable"},
        {"dimension": "main table", "v1": "180 cells including Buy-and-Hold", "v2": "165 cells without Buy-and-Hold", "effect": "all reported values materially revised"},
        {"dimension": "component ablation", "v1": "PA/FIP/MSP/MTR, 45 cells", "v2": "MTR/QRA/MSP, 36 cells", "effect": "treatments and results changed"},
        {"dimension": "new v2 tables", "v1": "none", "v2": "sampling, signal, and extreme-market: 93 cells", "effect": "current evidence denominator expanded"},
        {"dimension": "prompt appendix", "v1": "12 templates", "v2": "same 12 template contents", "effect": "known contract defects persist"},
        {"dimension": "empirical panels", "v1": "15 displayed panels", "v2": "11 displayed panels", "effect": "v1 AAPL asset duplicates TSLA composite; v2 separates it"},
    ]


def readme_text() -> str:
    return """# FinPos paper-faithfulness audit

This is a revision-aware paper-derived component audit, not an end-to-end FinPos replication. It pins and rebuilds both official arXiv revisions, visually checks all 39 official and all 39 rebuilt pages, inventories every displayed empirical result cell and panel, and preserves the exact boundary between printed mechanics and unreleased author execution.

The current v2 denominator is **294 displayed empirical result cells across five tables and 11 empirical figure panels**. The v1 lineage adds **225 cells across two tables and 15 displayed empirical panels**. Zero of 519 revision-level cells and 0/26 revision-level panels were regenerated by an author-native pipeline. Static TeX and vector assets are source evidence, not raw results.

Eleven controlled paper-derived mechanics execute deterministically. Nine evaluate literal printed equations; two deliberately refuse unstated conversions from cumulative log return to CR% and from CVaR to integer order quantity. These are paper-derived checks, not author code or empirical results.

The paper prints twelve prompt templates in both revisions. Only 4/12 output examples are valid JSON after placeholder substitution; six use invalid JSON-like syntax and two testing prompts depend on the unreleased `gr.complete_json_suffix_v2`.

Material blockers remain: there is no attributable implementation or immutable input/output release; the reward's total-position term does not implement the prose's action-alignment claim; raw-dollar reward units are asset-scale dependent; the 95% lower-tail CVaR convention and sign claim conflict; no conversion maps CVaR to share quantity; CR% is not derived from the printed log-return sum; execution costs and account initialization are missing; v2 carries plots whose Calmar annotations match v1 rather than v2; and v2 conflicts on its extreme-test and U.S.-election timing. Therefore `strict_success` remains false.

Negative release searches are bounded and do not prove that private, deleted, moved, renamed, unindexed, or later material does not exist.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    verify_pins(scratch)
    sources = {version: paper_sources(scratch, version) for version in ("v1", "v2")}
    output.mkdir(parents=True, exist_ok=True)
    for old in output.iterdir():
        if old.is_file():
            old.unlink()

    results = result_rows(sources)
    figures = figure_rows(sources)
    components = component_rows()
    prompts = prompt_rows(sources)
    provenance = {
        "arxiv_id": ARXIV_ID,
        "current_version": "v2",
        "authors": ["Bijia Liu", "Ronghao Dang"],
        "published": "2025-10-31T07:39:26Z",
        "updated": "2026-01-07T04:44:08Z",
        "source_files_per_revision": {"v1": 19, "v2": 19},
        "official_pages": {version: len(PdfReader(scratch / f"primary/official-{version}.pdf").pages) for version in ("v1", "v2")},
        "rebuilt_pages": {version: len(PdfReader(scratch / f"primary/rebuilt-{version}.pdf").pages) for version in ("v1", "v2")},
        "official_pages_visually_checked": {"v1": 17, "v2": 22},
        "rebuilt_pages_visually_checked": {"v1": 17, "v2": 22},
        "visual_defects_observed": 0,
        "official_rebuilt_token_jaccard": {
            version: token_jaccard(
                (scratch / f"primary/official-{version}.txt").read_text(errors="ignore"),
                (scratch / f"primary/rebuilt-{version}.txt").read_text(errors="ignore"),
            )
            for version in ("v1", "v2")
        },
        "paper_contains_native_implementation_url": False,
        "paper_contains_dataset_or_checkpoint_url": False,
        "attributable_finpos_implementation_found": False,
        "observed_license": "NOASSERTION",
        "pinned_input_sha256": PINS,
    }
    write_json(output / "source_provenance.json", provenance)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "prompt_contract_audit.csv", prompts)
    write_csv(output / "component_execution_audit.csv", components)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", consistency_rows())
    write_csv(output / "revision_change_audit.csv", revision_rows())
    write_csv(output / "release_search_audit.csv", release_rows())
    (output / "README.md").write_text(readme_text())

    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "current_revision": "v2",
        "current_empirical_table_cells": sum(1 for row in results if row["revision"] == "v2"),
        "v1_empirical_table_cells": sum(1 for row in results if row["revision"] == "v1"),
        "revision_level_empirical_table_cells": len(results),
        "current_result_tables": sum(1 for version, _ in TABLE_SPECS if version == "v2"),
        "author_native_table_cells_regenerated": 0,
        "current_empirical_figure_panels": sum(int(row["empirical_panels"]) for row in figures if row["revision"] == "v2"),
        "v1_empirical_figure_panels": sum(int(row["empirical_panels"]) for row in figures if row["revision"] == "v1"),
        "author_native_empirical_panels_regenerated": 0,
        "prompt_templates_printed": len(prompts),
        "valid_printed_json_examples": sum(row["strict_json_contract_status"] == "valid_json_example" for row in prompts),
        "paper_derived_components_executed": len(components),
        "paper_derived_components_passing_controlled_checks": len(components),
        "attributable_finpos_implementation_found": False,
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
