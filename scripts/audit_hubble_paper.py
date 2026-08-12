#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for Hubble.

Hubble has two materially different arXiv editions.  Both source bundles can be
rebuilt, but neither bundle contains the advertised runtime or empirical
artifacts, and v2 intentionally withholds the five winning formulas.  This
audit grants document and conditional method-component credit only; it never
converts manuscript prose, rendered plots, or an independent reimplementation
into native experiment/result reproduction.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/hubble_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/hubble"
WORK_ID = "CensusArxiv260409601"
SYSTEM_ID = "SYS-HUBBLE"
ARXIV_ID = "2604.09601"

PINS = {
    "primary/arxiv-abs.html": "4f485315c275a493b5efe4eb4a244e36c90288141b0057061e0eb1657595b93a",
    "primary/arxiv-api.xml": "d62ddfd494be8087ebce449c1d98b87b672b491a5ae7abeee53881c0b788a86b",
    "primary/arxiv-v1.pdf": "f728edcf6e03b359053764fdbe2659c3e714bd23e1abb61f75d6bee5a4130af1",
    "primary/arxiv-v1.tar": "3a08b6824149c2a112e0e2d3c0bd7c74a4ed7768fd5b93d9139c80dd6707d842",
    "primary/arxiv-v2.pdf": "774c98f53a6fb1e32535ea0ab51a234548c3dbdb29b594a0cf537cf96275a288",
    "primary/arxiv-v2.tar": "97acc42edc0ea803a8187f3c8d08f2007a3dec505be57a1f4affeb9b1c455318",
    "primary/hunter-alpha.html": "bc65407cf09dbd81328affbe78ed2b0a7443fffbc7f0b6955164c1703552580f",
    "primary/nemotron-hf-api.json": "f59768ae0f3507b1cd2aa4ef5daa25c3987b52e0de9f7cbe04006f30f8454c6c",
    "primary/nemotron-model-card.md": "31d42967cd73c5e2beea5ce60bbcb062d8b84bee71e816c80d4f76d27575f9a7",
    "rebuilt/arxiv-v1-source-rebuilt.pdf": "ca36ab285773ac91af1c190775af1aa2a2153c696f078a5bbf34c86506a51756",
    "rebuilt/arxiv-v2-source-rebuilt.pdf": "d4e1eb2e10caf24dcfc14252031feb2c5cf2729811f997e756e1361fb2a7ff11",
    "build-v1/pass3.log": "8e76cf90fc21f52c2e91c45303c41da9f1e8a75b67cca799748f3b5f3a6406a7",
    "build-v2/pass3.log": "862f74bf46dbc95f1e73c93682e951bc7e134dd53b217648e34b99b5ca21fe26",
    "discovery/github-code-arxiv.json": "e92b56aca0c82a7a3eba6e9a3c1bcee4fe24edeaa986269e8ff16fbf7d66c274",
    "discovery/github-code-title.json": "716d2cf05c86172dc5d28203dc1e06267ca9743f456ab202a17fbb509e0c4d93",
    "discovery/github-repositories-hubble-alpha.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/user_Celestial-Quant-Lab.json": "71f6de89bca39a12321b7d1f614ba57dfc78235a568a06d0c77d49dce8181981",
    "discovery/repos_Celestial-Quant-Lab.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/user_YuechengCai.json": "c5a204efd9a277e017ae1dd01a8f6d1a138503214419ac83680bb0b5aa340125",
    "discovery/repos_YuechengCai.json": "8221412a41846b30e5710754a8ab5b97eb2ea4b4a779426bff472044f7e053b6",
}

TREE_DIGESTS = {
    "source-v1": ("9122db9078ef5934bab2550fe4c3676a4624acc9be515fbac4bba6b5cfb6f124", 11),
    "source-v2": ("261afe671fab1efd205c3cf4ffd79057aa6990949a8d4e8a91c654909b3caedb", 19),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(path: Path) -> tuple[str, int]:
    rows = []
    files = sorted(item for item in path.rglob("*") if item.is_file())
    for item in files:
        rows.append(f"{item.relative_to(path)}\0{sha256(item)}\n")
    return hashlib.sha256("".join(rows).encode()).hexdigest(), len(files)


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


def safe_tar_members(path: Path) -> set[str]:
    members = set()
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe archive member: {member.name}")
            if member.isfile():
                members.add(str(pure))
    return members


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    for relative, expected in TREE_DIGESTS.items():
        actual = tree_digest(scratch / relative)
        if actual != expected:
            raise ValueError(f"tree mismatch for {relative}: {actual} != {expected}")

    for archive in ("primary/arxiv-v1.tar", "primary/arxiv-v2.tar"):
        safe_tar_members(scratch / archive)
    abs_html = (scratch / "primary/arxiv-abs.html").read_text(errors="replace")
    for marker in (
        "Submitted on 9 Mar 2026", "last revised 14 Apr 2026",
        "2604.09601v2", "Runze Shi", "Shengyu Yan", "Yuecheng Cai", "Chengxi Lv",
    ):
        if marker not in abs_html:
            raise ValueError(f"arXiv record marker missing: {marker}")
    for edition, pages in (("v1", 11), ("v2", 17)):
        log = (scratch / f"build-{edition}/pass3.log").read_text(errors="replace")
        if f"Output written on main.pdf ({pages} pages" not in log:
            raise ValueError(f"{edition} source rebuild did not finish at {pages} pages")

    nemotron = (scratch / "primary/nemotron-model-card.md").read_text(errors="replace")
    hunter = (scratch / "primary/hunter-alpha.html").read_text(errors="replace")
    if "March 11, 2026" not in nemotron or "03/11/2026" not in nemotron:
        raise ValueError("Nemotron release-date markers changed")
    if 'releaseDate\\":\\"2026-03-11T20:24:31.000Z' not in hunter:
        raise ValueError("Hunter Alpha release-date marker changed")
    if "early testing version of MiMo-V2-Pro" not in hunter:
        raise ValueError("Hunter Alpha identity disclosure changed")

    lab = json.loads((scratch / "discovery/user_Celestial-Quant-Lab.json").read_text())
    lab_repos = json.loads((scratch / "discovery/repos_Celestial-Quant-Lab.json").read_text())
    if lab["login"] != "Celestial-Quant-Lab" or lab["public_repos"] != 0 or lab_repos:
        raise ValueError("author-lab public repository boundary changed")
    return {
        "v1_source_files": TREE_DIGESTS["source-v1"][1],
        "v2_source_files": TREE_DIGESTS["source-v2"][1],
    }


def table_block(tex: str, label: str) -> str:
    for match in re.finditer(r"\\begin\{table\}.*?\\end\{table\}", tex, re.S):
        if f"\\label{{{label}}}" in match.group(0):
            return match.group(0)
    raise ValueError(f"table not found: {label}")


def number(value: str) -> float:
    clean = value.replace("$", "").replace("\\textbf{", "").replace("}", "")
    clean = clean.replace("\\%", "").replace("%", "").replace("\\dagger", "")
    clean = clean.replace("\\ast", "").replace("*", "").replace("−", "-")
    clean = clean.replace("$-$", "-").replace("\\-", "-").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", clean)
    if not match:
        raise ValueError(f"numeric value missing: {value}")
    return float(match.group())


def result_row(
    edition: str,
    table: str,
    identity: str,
    metric: str,
    rendered: str,
    duplicate_of: str = "",
) -> dict[str, Any]:
    return {
        "edition": edition,
        "table": table,
        "identity": identity,
        "metric": metric,
        "rendered_value": rendered.strip(),
        "numeric_value": number(rendered),
        "duplicate_kind": "exact_semantic_repeat" if duplicate_of else "none",
        "duplicate_of": duplicate_of,
        "native_pipeline_executed": False,
        "native_result_regenerated": False,
        "paper_result_credit": False,
    }


def parse_v1_tables(tex: str) -> list[dict[str, Any]]:
    rows = []
    round_values = {
        "R1": ("41", "76", "71", "10", "0.827"),
        "R2": ("41", "60", "60", "21", "$-0.279$"),
        "R3": ("40", "50", "50", "31", "0.717"),
        "Total": ("122", "186", "181", "62", "0.827"),
    }
    metrics = ("Candidates", "Evaluated", "OK", "Errors", "Best Score")
    block = table_block(tex, "tab:round_summary")
    for identity, values in round_values.items():
        if not all(value in block for value in values):
            raise ValueError(f"v1 round row changed: {identity}")
        for metric, value in zip(metrics, values):
            duplicate = "v1/R1/Best Score" if identity == "Total" and metric == "Best Score" else ""
            rows.append(result_row("arxiv_v1", "round_summary", identity, metric, value, duplicate))
    top_values = {
        "f1": ("0.827", "0.0185", "1.310", "52.7\\%", "0.902", "100\\%"),
        "f2": ("0.717", "0.0185", "1.298", "51.7\\%", "0.945", "100\\%"),
        "f3": ("0.506", "0.0044", "0.319", "53.1\\%", "0.028", "100\\%"),
        "f4": ("0.218", "0.0026", "0.187", "53.7\\%", "0.039", "100\\%"),
        "f5": ("0.161", "0.0021", "0.151", "53.8\\%", "0.052", "100\\%"),
    }
    metrics = ("Score", "RankIC", "RankICIR_ann", "IC_hit_pct", "Turnover", "Coverage_pct")
    block = table_block(tex, "tab:top_k")
    for identity, values in top_values.items():
        if not all(value in block for value in values):
            raise ValueError(f"v1 top-factor row changed: {identity}")
        for metric, value in zip(metrics, values):
            duplicate = ""
            if identity == "f1" and metric == "Score":
                duplicate = "v1/R1/Best Score"
            elif identity == "f2" and metric == "Score":
                duplicate = "v1/R3/Best Score"
            rows.append(result_row("arxiv_v1", "top_factors", identity, metric, value, duplicate))
    if len(rows) != 50:
        raise ValueError(f"expected 50 v1 result cells, found {len(rows)}")
    return rows


def parse_v2_tables(tex: str) -> list[dict[str, Any]]:
    rows = []
    round_values = {
        "R1": ("20", "40", "40", "0", "5.195"),
        "R2": ("20", "34", "34", "6", "5.622"),
        "R3": ("20", "30", "30", "10", "5.436"),
        "Total": ("60", "104", "104", "16", "5.622"),
    }
    metrics = ("Candidates", "Evaluated", "OK", "Errors", "Best Score")
    block = table_block(tex, "tab:round_summary")
    for identity, values in round_values.items():
        if not all(value in block for value in values):
            raise ValueError(f"v2 round row changed: {identity}")
        for metric, value in zip(metrics, values):
            duplicate = "v2/R2/Best Score" if identity == "Total" and metric == "Best Score" else ""
            rows.append(result_row("arxiv_v2", "round_summary", identity, metric, value, duplicate))

    is_values = {
        "Range-1": ("5.622", "0.0059", "0.350", "0.0127", "0.687", "0.000810", "0.113"),
        "Range-2": ("5.486", "0.0057", "0.342", "0.0130", "0.716", "0.000724", "0.161"),
        "Volatility-1": ("5.475", "0.0057", "0.368", "0.0133", "1.028", "0.000546", "0.174"),
        "Volatility-2": ("5.272", "0.0047", "0.297", "0.0124", "0.851", "0.000587", "0.137"),
        "Trend-1": ("4.609", "0.0115", "0.900", "0.0110", "0.968", "0.000350", "0.368"),
    }
    metrics = ("Score", "RankIC", "RankICIR_ann", "IC", "ICIR_ann", "LS_Return", "Turnover")
    block = table_block(tex, "tab:topk_is")
    for identity, values in is_values.items():
        if not all(value in block for value in values):
            raise ValueError(f"v2 IS row changed: {identity}")
        for metric, value in zip(metrics, values):
            duplicate = "v2/R2/Best Score" if identity == "Range-1" and metric == "Score" else ""
            rows.append(result_row("arxiv_v2", "top5_in_sample", identity, metric, value, duplicate))

    oos_values = {
        "Range-1": ("0.0242", "1.804", "1.75", "0.0391", "2.788", "2.98**", "0.00205", "2.17*", "0.133"),
        "Range-2": ("0.0245", "1.860", "1.81", "0.0385", "2.797", "3.01**", "0.00209", "2.31*", "0.182"),
        "Volatility-1": ("0.0275", "2.305", "2.25*", "0.0131", "1.656", "1.68", "0.00200", "2.60**", "0.173"),
        "Volatility-2": ("0.0232", "1.900", "1.81", "0.0204", "2.251", "2.47*", "0.00189", "2.27*", "0.133"),
        "Trend-1": ("0.0083", "0.794", "0.81", "$-$0.0034", "$-$0.380", "$-$0.39", "$-$0.00064", "$-$0.87", "0.374"),
    }
    metrics = ("RankIC", "RankICIR_ann", "RankIC_HAC_t", "IC", "ICIR_ann", "IC_HAC_t", "LS_Return", "LS_HAC_t", "Turnover")
    block = table_block(tex, "tab:topk_oos")
    for identity, values in oos_values.items():
        normalized = [value.replace("$-$", "$-$") for value in values]
        if not all(value in block for value in normalized):
            raise ValueError(f"v2 OOS row changed: {identity}")
        for metric, value in zip(metrics, values):
            rows.append(result_row("arxiv_v2", "top5_out_of_sample", identity, metric, value))

    robustness = {
        "Nemotron-120B-free": ("104", "104", "16", "5.622"),
        "Hunter-Alpha": ("107", "105", "15", "5.460"),
    }
    metrics = ("Total evaluated", "Total OK", "Total errors", "Best score")
    block = table_block(tex, "tab:robustness")
    for identity, values in robustness.items():
        if not all(value in block for value in values):
            raise ValueError(f"v2 robustness row changed: {identity}")
        for metric, value in zip(metrics, values):
            duplicate = ""
            if identity == "Nemotron-120B-free":
                duplicate = {
                    "Total evaluated": "v2/Total/Evaluated",
                    "Total OK": "v2/Total/OK",
                    "Total errors": "v2/Total/Errors",
                    "Best score": "v2/R2/Best Score",
                }[metric]
            rows.append(result_row("arxiv_v2", "backend_robustness", identity, metric, value, duplicate))
    if len(rows) != 108:
        raise ValueError(f"expected 108 v2 result cells, found {len(rows)}")
    return rows


def figure_rows() -> list[dict[str, Any]]:
    specifications = (
        ("arxiv_v1", "score_distribution", 3, "three round score distributions"),
        ("arxiv_v1", "error_breakdown", 2, "parse-error and duplicate series"),
        ("arxiv_v1", "topk_comparison", 3, "RankICIR, score, and turnover series"),
        ("arxiv_v1", "pipeline_efficiency", 3, "unique, evaluated, and OK-rate series"),
        ("arxiv_v2", "round_overview", 5, "four throughput series and best-score line"),
        ("arxiv_v2", "is_top_factor_metrics", 6, "six metric panels"),
        ("arxiv_v2", "oos_top_factor_metrics", 6, "six metric panels"),
        ("arxiv_v2", "is_bucket_profile", 1, "best-factor bucket profile"),
        ("arxiv_v2", "oos_bucket_profile", 1, "best-factor bucket profile"),
        ("arxiv_v2", "is_significance_topk", 3, "three significance panels"),
        ("arxiv_v2", "oos_significance_topk", 3, "three significance panels"),
        ("arxiv_v2", "is_ic_stability", 3, "three cumulative-IC curves"),
        ("arxiv_v2", "oos_ic_stability", 3, "three cumulative-IC curves"),
        ("arxiv_v2", "is_long_short_cumulative", 3, "three cumulative spread curves"),
        ("arxiv_v2", "oos_long_short_cumulative", 3, "three cumulative spread curves"),
        ("arxiv_v2", "family_diversity", 2, "candidate-pool and selected-set series"),
    )
    return [
        {
            "edition": edition,
            "figure": figure,
            "displayed_series": count,
            "description": description,
            "underlying_numeric_array_released": False,
            "native_figure_regenerated": False,
            "paper_result_credit": False,
        }
        for edition, figure, count, description in specifications
    ]


def method_rows() -> list[dict[str, Any]]:
    rows = (
        ("native_source", "missing", "both arXiv bundles contain manuscript assets only; author-lab organization exposes zero public repositories"),
        ("exact_factor_formulas", "intentionally_withheld", "v1 anonymizes f1-f5; v2 explicitly avoids exact formulas and hyperparameters"),
        ("operator_registry", "partial", "operator families and examples only; complete names, arities, and implementations absent"),
        ("ast_whitelist", "partial", "v1 names five allowed AST node classes; implementation and full rejection semantics absent"),
        ("data_universe_v1", "missing", "30 U.S. equities named but ticker list absent"),
        ("data_universe_v2", "missing", "sp500.txt and 501 valid stocks named but list, vintage, filtering, and membership policy absent"),
        ("market_data", "missing", "daily OHLCV named; vendor, snapshot, adjustments, timezone, missing-data policy, and delistings absent"),
        ("discovery_window", "partial", "date endpoints and claimed day counts supplied; included-date array absent"),
        ("oos_window", "partial", "v2 endpoints and claimed 195 days supplied; included-date array absent"),
        ("survivorship_controls", "missing", "no point-in-time S&P 500 membership protocol"),
        ("prompts", "missing", "prompt construction described but exact system/user templates and runtime fills absent"),
        ("rag_corpus", "missing", "positive/negative RAG described; corpus, index, embedding model, retrieval parameters, and snapshot absent"),
        ("model_v1", "missing", "no LLM identity or immutable endpoint/checkpoint"),
        ("models_v2", "partial", "two mutable OpenRouter display identifiers; no immutable request or provider snapshot"),
        ("model_call_parameters", "missing", "temperature, top-p, token limits, seed, reasoning controls, retries, and concurrency absent"),
        ("random_seeds", "missing", "no generation/evaluation seeds or repeated-run protocol"),
        ("scoring_v1", "partial", "linear weights supplied, but input preprocessing and drop-ratio implementation absent"),
        ("scoring_v2", "missing", "centers, scales, weights, direct penalty magnitudes, bonuses, and similarity thresholds absent"),
        ("family_assignment", "missing", "family taxonomy and classifier/assignment implementation absent"),
        ("duplicate_detection", "missing", "normalization and similarity/exact-duplicate rule absent"),
        ("forward_label", "partial", "formula given; horizon h and price/return conventions absent"),
        ("portfolio_construction", "partial", "buckets and top-minus-bottom named; quantile/tie/weight/rebalance conventions absent"),
        ("transaction_costs", "missing", "paper explicitly omits transaction-cost evaluation"),
        ("neutralization", "missing", "paper explicitly reports no market, sector, or style neutralization"),
        ("hac_configuration", "partial", "Bartlett kernel and automatic lag named; exact lag rule/implementation absent"),
        ("runtime_artifacts", "missing", "claimed prompts, responses, checkpoints, JSON summaries, and diagnostics are not released"),
        ("candidate_formulas", "missing", "generated and rejected formula sets absent"),
        ("raw_result_arrays", "missing", "IC, bucket, long-short, turnover, coverage, and complexity arrays absent"),
        ("environment_dependencies", "missing", "no runtime environment, package versions, or lockfile"),
        ("oos_protocol", "partial", "one retrospective split; no walk-forward and no prospectively timestamped freeze artifact"),
    )
    return [{"dimension": x, "status": y, "evidence": z} for x, y, z in rows]


def consistency_rows() -> list[dict[str, str]]:
    rows = (
        ("v1_round_accounting", "caption_and_counts_conflict", "Evaluated + Errors equals 81 in every round, not Evaluated; totals 181 + 62 = 243 versus 186 evaluated"),
        ("v1_round1_duplicates", "prose_conflicts_with_table_and_figure", "error-distribution prose says zero R1 duplicates, while the figure caption says five and Table 1 implies five duplicates plus five parse errors"),
        ("v1_pass_rate", "passes_displayed_arithmetic", "181 / 186 = 97.31%, consistent with the reported 97.3%"),
        ("v1_computational_stability", "not_independently_verifiable", "zero crashes and 100% stability are asserted without runtime logs or outputs"),
        ("v2_round_accounting", "internally_reconcilable_but_terminology_ambiguous", "120 attempted slots can reconcile as 104 evaluated + 16 duplicates, but Candidates denotes only 60 primary generations"),
        ("v2_discovery_day_count", "underspecified_against_public_calendar", "paper reports 840 dates; broad U.S. session data have 855 dates in the stated interval, and the 15 exclusions are not identified"),
        ("v2_oos_day_count", "underspecified_against_public_calendar", "paper reports 195 dates; broad U.S. session data have 197 dates in the stated interval, and the two exclusions are not identified"),
        ("v2_literal_pre_oos_freeze", "contradicted_by_model_release_chronology", "both named backends first became public on 2026-03-11, after the 2025-06-01 OOS start and two days before its end"),
        ("v2_defensible_temporal_interpretation", "retrospective_holdout_possible_but_unverified", "a later run using only the discovery slice could preserve data-layer holdout, but no timestamped freeze, inputs, requests, formulas, or outputs are released"),
        ("v2_formula_disclosure", "intentional_reproduction_blocker", "the paper explicitly withholds exact formulas and hyperparameters, preventing independent factor/result regeneration"),
        ("v2_backend_identity", "hunter_alpha_later_disclosed", "OpenRouter now identifies Hunter Alpha as an early testing version of MiMo-V2-Pro"),
        ("v2_robustness", "lightweight_by_author_admission", "one alternate backend is reported without seeds, repeated runs, uncertainty, or the proposed RAG/scoring ablations"),
        ("v2_oos_scope", "preliminary_not_definitive", "single 195-day claimed split, no neutralization, costs, or walk-forward; this matches the paper's own limitations"),
        ("author_name_rendering", "metadata_source_inconsistency", "arXiv metadata says Chengxi Lv while the v2 TeX author line says Chenxi Lv"),
    )
    return [{"check": a, "status": b, "detail": c} for a, b, c in rows]


def discovery_rows(scratch: Path) -> list[dict[str, Any]]:
    arxiv = json.loads((scratch / "discovery/github-code-arxiv.json").read_text())
    title = json.loads((scratch / "discovery/github-code-title.json").read_text())
    repos = json.loads((scratch / "discovery/github-repositories-hubble-alpha.json").read_text())
    author_repos = json.loads((scratch / "discovery/repos_YuechengCai.json").read_text())
    return [
        {
            "route": "github_exact_repository_title",
            "result_count": repos["total_count"],
            "finding": "zero exact-title repositories",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded current indexed search; not proof that private, deleted, moved, or unindexed material never existed",
        },
        {
            "route": "github_code_arxiv_id",
            "result_count": arxiv["total_count"],
            "finding": "visible matches are citations/indexes or unaffiliated paper-inspired work",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded current indexed search; not proof that private, deleted, moved, or unindexed material never existed",
        },
        {
            "route": "github_code_exact_title",
            "result_count": title["total_count"],
            "finding": "visible matches are citations/indexes, not an attributable implementation",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded current indexed search; not proof that private, deleted, moved, or unindexed material never existed",
        },
        {
            "route": "github_author_lab_organization",
            "result_count": 0,
            "finding": "Celestial-Quant-Lab account exists but exposes zero public repositories",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "bounded current public API observation; private or future releases are outside the observation",
        },
        {
            "route": "github_named_author_account",
            "result_count": len(author_repos),
            "finding": "attributable UBC author account has unrelated structural-ML repositories only",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "identity attribution is bounded; other accounts or private material may exist",
        },
        {
            "route": "arxiv_source_bundles",
            "result_count": 2,
            "finding": "manuscript, bibliography, style, and rendered figure assets only; no code/data/output archives",
            "attributable_native_artifact_recovered": False,
            "negative_search_limit": "describes the pinned v1/v2 source bundles only",
        },
    ]


def sandbox_component() -> dict[str, Any]:
    allowed_nodes = (ast.Expression, ast.Call, ast.Name, ast.Load, ast.Constant, ast.UnaryOp, ast.USub)
    registry = {"ADD": 2, "TS_SMA": 2, "GT": 2, "IF": 3}
    variables = {"OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"}

    def validate(expression: str) -> tuple[bool, str]:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError:
            return False, "syntax_error"
        nodes = list(ast.walk(tree))
        if len(nodes) > 1000:
            return False, "node_limit"
        for node in nodes:
            if not isinstance(node, allowed_nodes):
                return False, f"forbidden_ast:{type(node).__name__}"
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in registry:
                    return False, "unregistered_operator"
                if len(node.args) != registry[node.func.id] or node.keywords:
                    return False, "arity"
            if isinstance(node, ast.Name) and not isinstance(getattr(node, "ctx", None), ast.Load):
                return False, "identifier_context"
            if isinstance(node, ast.Name) and node.id not in variables | set(registry):
                return False, "unknown_identifier"
        return True, "accepted"

    cases = []
    for expression, expected in (
        ("TS_SMA(CLOSE, 5)", True),
        ("IF(GT(CLOSE, OPEN), CLOSE, OPEN)", True),
        ("__import__('os').system('id')", False),
        ("CLOSE > OPEN", False),
        ("TS_SMA(CLOSE)", False),
        ("UNKNOWN(CLOSE)", False),
    ):
        accepted, reason = validate(expression)
        if accepted != expected:
            raise ValueError(f"conditional sandbox fixture mismatch: {expression}")
        cases.append({"expression": expression, "accepted": accepted, "reason": reason})
    return {
        "component": "paper-described AST whitelist/registry/arity subset",
        "cases": cases,
        "native_hubble_code_used": False,
        "paper_candidate_or_output_used": False,
        "paper_result_credit": False,
        "boundary": "independent conditional conformance fixture; incomplete registry and no native implementation",
    }


def build(scratch: Path, output: Path) -> dict[str, Any]:
    validated = validate_inputs(scratch)
    v1_tex = (scratch / "source-v1/main.tex").read_text(encoding="utf-8")
    v2_tex = (scratch / "source-v2/main.tex").read_text(encoding="utf-8")
    tables = parse_v1_tables(v1_tex) + parse_v2_tables(v2_tex)
    figures = figure_rows()
    methods = method_rows()
    consistency = consistency_rows()
    discovery = discovery_rows(scratch)

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "published_result_ledger.csv", tables)
    write_csv(output / "figure_series_inventory.csv", figures)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "discovery_evidence.csv", discovery)
    write_json(output / "sandbox_component_execution.json", sandbox_component())
    write_json(
        output / "model_release_chronology.json",
        {
            "oos_start": "2025-06-01",
            "oos_end": "2026-03-13",
            "models": [
                {
                    "paper_identifier": "nvidia/nemotron-3-super-120b-a12b:free",
                    "first_public_date": "2026-03-11",
                    "primary_record": "NVIDIA Hugging Face model card pinned at commit 7d7e5797b8a3c7abbab54033b6004e93e8b6bc91",
                    "after_oos_start": True,
                },
                {
                    "paper_identifier": "openrouter/hunter-alpha",
                    "first_public_date": "2026-03-11",
                    "primary_record": "OpenRouter model page; later disclosed as early MiMo-V2-Pro testing version",
                    "after_oos_start": True,
                },
            ],
            "literal_fixed_before_oos_window_begins_supported": False,
            "retrospective_data_layer_holdout_possible": True,
            "retrospective_data_layer_holdout_verified": False,
        },
    )
    provenance = {
        "arxiv": {
            "id": ARXIV_ID,
            "versions": [
                {
                    "version": "v1", "submitted": "2026-03-09", "pages": 11,
                    "source_files": validated["v1_source_files"], "rebuild_pages": 11,
                    "rebuild_token_multiset_jaccard": 0.9973730297723292,
                    "visual_qa": {"pages_inspected": 11, "unreadable_clipped_or_overlapping_pages": 0},
                },
                {
                    "version": "v2", "submitted": "2026-04-14", "pages": 17,
                    "source_files": validated["v2_source_files"], "rebuild_pages": 17,
                    "rebuild_token_multiset_jaccard": 0.9990454371897671,
                    "visual_qa": {"pages_inspected": 17, "unreadable_clipped_or_overlapping_pages": 0},
                },
            ],
        },
        "release_boundary": {
            "attributable_native_implementation_recovered": False,
            "data_snapshot_recovered": False,
            "exact_factor_formulas_recovered": False,
            "exact_prompts_recovered": False,
            "runtime_requests_responses_recovered": False,
            "candidate_and_error_records_recovered": False,
            "raw_result_arrays_recovered": False,
            "bounded_negative_search_is_proof_of_nonexistence": False,
        },
    }
    write_json(output / "source_provenance.json", provenance)

    v1 = [row for row in tables if row["edition"] == "arxiv_v1"]
    v2 = [row for row in tables if row["edition"] == "arxiv_v2"]
    readme = """# Hubble paper-faithfulness audit

This fail-closed audit pins and rebuilds both materially different official
arXiv editions of *Hubble*.  The unmodified v1 and v2 source bundles reproduce
the published 11- and 17-page layouts with extracted-token multiset Jaccard of
0.99737 and 0.99905.  All 28 rebuilt pages were visually checked without
clipping, overlap, missing figures, unreadable labels, or contrast failures.

## Honest reproduction boundary

The native Hubble experiment is **not reproduced**.  The source archives contain
manuscript assets, not the runtime, data, or stored artifacts advertised in the
paper.  The author-lab GitHub organization exists but has zero public
repositories, and bounded repository/code/author searches recovered no
attributable implementation.  Most decisively, v1 anonymizes the five factors
and v2 explicitly withholds their exact formulas and hyperparameters.  The
universe snapshots, prompts, RAG corpora/indexes, operator registry, model
requests, scoring constants, seeds, candidate/error records, environment, and
raw result arrays are also absent.

The published denominator is 50 numeric result cells in v1 (47 after three
semantic repeats) and 108 in v2 (102 after six semantic repeats), plus 11 and 39
displayed empirical figure series whose underlying arrays are not released.
Native result regeneration is 0/47 for v1, 0/102 for v2, and 0/50 figure series.
The independent AST fixture is a conditional method check only and receives
zero Hubble result credit.

## Material audit findings

- v1's accounting conflicts with its table definitions: `Evaluated + Errors`
  equals 81 per round, while the displayed evaluated counts total 186 and
  `OK + Errors` total 243.  Its prose also says zero Round-1 duplicates while
  the figure caption says five and the table implies five.
- v2's two named LLM backends first became public on 2026-03-11, after the
  claimed OOS window began on 2025-06-01 and two days before it ended.  Thus the
  literal statement that formulas were fixed before the OOS window began is
  contradicted by public chronology.  A later retrospective run using only the
  discovery slice could still be a valid data-layer holdout, but no timestamped
  freeze, requests, formulas, inputs, or outputs verify it.
- The claimed 840 discovery dates and 195 OOS dates do not follow directly from
  the stated endpoints: broad U.S. session data contain 855 and 197 dates.  A
  complete-case filter could explain the difference, but no included-date array
  or missing-data rule is released.
- v2 itself acknowledges the single split, short OOS, no neutralization, no
  transaction-cost evaluation, possible LLM temporal leakage, and lightweight
  backend check.  Those cautions are scientifically appropriate; they also mean
  the paper is preliminary evidence, not a fully reproducible alpha result.

Negative artifact searches are bounded current observations, not proof that
private, deleted, moved, or unindexed material never existed.  Unaffiliated
paper-inspired repositories and local fixtures are not credited as Hubble.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    manifest: dict[str, Any] = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_versions_audited": ["v1", "v2"],
        "official_pdfs_and_sources_recovered": True,
        "official_document_rebuilds_completed": True,
        "attributable_native_implementation_recovered": False,
        "published_v1_numeric_cells": len(v1),
        "published_v1_unique_numeric_cells": sum(row["duplicate_kind"] == "none" for row in v1),
        "published_v2_numeric_cells": len(v2),
        "published_v2_unique_numeric_cells": sum(row["duplicate_kind"] == "none" for row in v2),
        "published_empirical_figure_series": sum(int(row["displayed_series"]) for row in figures),
        "native_empirical_units_regenerated": 0,
        "native_figure_series_regenerated": 0,
        "full_end_to_end_pipeline_reproduced": False,
        "literal_pre_oos_freeze_supported": False,
        "retrospective_data_layer_holdout_verified": False,
        "conditional_sandbox_component_executed": True,
        "conditional_sandbox_component_paper_result_credit": False,
        "paper_evidence_route": "paper_only_intentionally_underspecified",
        "output_sha256": {},
    }
    output_files = sorted(path for path in output.iterdir() if path.is_file() and path.name != "manifest.json")
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
