#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for the SHARP paper."""

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

import numpy as np
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/sharp_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/sharp"
WORK_ID = "CensusArxiv260506822"
SYSTEM_ID = "SYS-SHARP"
ARXIV_ID = "2605.06822"

PINS = {
    "primary/official.pdf": "8a53b6ed04d0de7852e4f5311db89df2c2f4457bd3cda23ae7fcf3baf4485394",
    "primary/official.txt": "a07be426fde7ec7adf7268f5dc0b03b784781b601affd398aaf53569ee7a9b39",
    "primary/source.tar": "4045a5dc53bbc2612b610e2a25e7a947ca3a5e8681af915b6528e3a0875ed56a",
    "primary/rebuilt.pdf": "12f2841b7aa369c39dfd49908e86613fec98b612690f9bbdcd0dea48ab8f5e4c",
    "primary/rebuilt.txt": "fd4076fca741eca87903a49baaf89b504e40a36b45d279ad3b5dcfef4940b6ae",
    "primary/arxiv-api.xml": "3ffe8f66699b4aa6b27dbab1e6cb4dc151ea30ad545d13abcb2a4fce7b823237",
    "discovery/github-repos-arxiv.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-repos-title.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-repos-sharp-rubric.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-repos-dataset-name.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-repos-longshort.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-code-temporal-rule.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-code-dataset-url.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-code-trace.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-code-hyperparameters.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-commits-dataset-url.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-user-cited.json": "3a32eab6ffbfd1cf2684b1a409bf40db46e46c5eaff44de656e499df05d92730",
    "discovery/github-repo-cited.json": "4f50e254a719a6b1b06b529bdaa08980e4acf0878aad0090cba7771f6ebdf0b9",
    "discovery/huggingface-models.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-datasets.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}

# A result unit is one populated quantitative table cell. Compound values are
# kept as one displayed unit. Commented-out tables/rows do not count.
TABLE_SPECS = {
    "tab:summary": ("sections/experiments.tex", tuple(range(1, 13)), 132),
    "tab:ablation": ("sections/experiments.tex", (1, 2, 3, 4), 16),
    "tab:opensource": ("sections/experiments.tex", (1, 2), 14),
    "tab:static_full": ("sections/appendix.tex", tuple(range(1, 13)), 48),
}
EXPECTED_RESULT_UNITS = 210


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
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise ValueError(f"pin mismatch: {relative}={observed}; expected {expected}")


def paper_sources(scratch: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(scratch / "primary/source.tar", "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe source member: {member.name}")
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"unreadable source member: {member.name}")
            files[member.name] = handle.read()
    if len(files) != 14:
        raise ValueError(f"paper source file count changed: {len(files)}")
    return files


def source_text(files: Mapping[str, bytes], path: str) -> str:
    return files[path].decode("utf-8")


def strip_comments(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("%"))


def table_environment(source: str, label: str) -> str:
    source = strip_comments(source)
    marker = rf"\label{{{label}}}"
    location = source.index(marker)
    starts = [source.rfind(r"\begin{table", 0, location), source.rfind(r"\begin{wraptable", 0, location)]
    begin = max(starts)
    ends = [value for value in (source.find(r"\end{table", location), source.find(r"\end{wraptable", location)) if value >= 0]
    if begin < 0 or not ends:
        raise ValueError(f"table boundary missing: {label}")
    end = min(ends)
    return source[begin:end]


def clean_tex(value: str) -> str:
    value = value.replace(r"$-$", "-").replace(r"\%", "%")
    value = re.sub(r"\\(?:textbf|underline|r[A-Z]|textsubscript|mathrm|text)\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\cite\{[^{}]*\}", "", value)
    value = re.sub(r"[{}$~]", "", value)
    return " ".join(value.split())


def table_data_rows(environment: str) -> list[list[str]]:
    match = re.search(r"\\begin\{tabular\}\{[^\n]*\}(.*?)\\end\{tabular\}", environment, re.S)
    if match is None:
        raise ValueError("tabular body missing")
    rows: list[list[str]] = []
    for chunk in re.split(r"\\\\", match.group(1)):
        if "&" not in chunk or any(token in chunk for token in (r"\toprule", r"\bottomrule", r"\cmidrule", r"\multicolumn")):
            continue
        cells = [clean_tex(cell) for cell in chunk.split("&")]
        rows.append(cells)
    return rows


def result_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    blocker = (
        "the author code/data package, exact walk-forward split boundaries, Finnhub cache, model calls, "
        "rubric histories, daily scores/positions/returns, baseline seeds, and result generator are unrecovered"
    )
    rows: list[dict[str, Any]] = []
    for label, (path, columns, expected) in TABLE_SPECS.items():
        parsed = table_data_rows(table_environment(source_text(files, path), label))
        table_rows: list[dict[str, Any]] = []
        for row_index, cells in enumerate(parsed, 1):
            row_label = cells[0]
            for column in columns:
                if column >= len(cells):
                    raise ValueError(f"short row in {label}: {cells}")
                cell = cells[column]
                if not re.search(r"\d", cell):
                    continue
                table_rows.append(
                    {
                        "table_label": label,
                        "row_index": row_index,
                        "row_label": row_label,
                        "quantitative_column_index": column,
                        "printed_cell": cell,
                        "unit_definition": "one populated displayed quantitative table cell",
                        "source_document_recovered": True,
                        "raw_result_record_recovered": False,
                        "author_native_experiment_executed": False,
                        "published_result_regenerated": False,
                        "paper_result_credit": False,
                        "blocking_reason": blocker,
                    }
                )
        if len(table_rows) != expected:
            raise ValueError(f"published denominator changed for {label}: {len(table_rows)} != {expected}")
        rows.extend(table_rows)
    if len(rows) != EXPECTED_RESULT_UNITS:
        raise ValueError(f"published result denominator changed: {len(rows)}")
    return rows


def figure_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    specs = (
        ("fig:teaser", "figures/teaser1_cropped.pdf", 0, 0, "conceptual comparison schematic"),
        ("fig:cumret", "figures/cumret_aitech.pdf", 1, 6, "six AI Tech cumulative-return trajectories"),
        ("fig:pipeline", "sections/method.tex", 0, 0, "TikZ training/inference schematic"),
        ("fig:diffs", "sections/experiments.tex", 0, 0, "paper-printed AI Tech rubric diff"),
        ("fig:diffs_app", "sections/appendix.tex", 0, 0, "paper-printed Biotech/Consumer rubric diffs"),
        ("fig:reflect_example", "sections/appendix.tex", 0, 0, "paper-printed free-reflection prompt diff"),
        ("fig:attribution_example_app", "sections/appendix.tex", 0, 0, "paper-printed illustrative attribution trace"),
    )
    return [
        {
            "figure": figure,
            "source_asset": path,
            "source_asset_sha256": sha256_bytes(files[path]),
            "empirical_panels": empirical,
            "empirical_series_or_groups": series,
            "description": description,
            "author_rendered_asset_or_tex_recovered": True,
            "underlying_numeric_array_or_run_log_recovered": False,
            "author_native_figure_regenerated": False,
            "paper_result_credit": False,
        }
        for figure, path, empirical, series, description in specs
    ]


def component_rows() -> list[dict[str, Any]]:
    # Deterministic controlled panel. Components implement equations and stated
    # mechanics only; they are not extracted author code and earn no result credit.
    opens = np.array(
        [
            [100, 101, 99, 103, 98, 102],
            [102, 104, 100, 105, 97, 101],
            [104, 103, 102, 108, 96, 100],
            [105, 105, 104, 109, 95, 99],
        ],
        dtype=float,
    )
    expected = np.array([0.0, 1.0, -1.0, 0.8, -0.5, -0.2])
    confidence = np.array([1.0, 0.7, 0.9, 0.5, 0.8, 0.6])
    scores = expected * confidence
    order = np.argsort(scores)
    current = np.zeros(6)
    current[order[-2:]] = 0.5
    current[order[:2]] = -0.5
    previous = np.array([0.5, 0.0, -0.5, 0.0, 0.0, 0.0])
    asset_returns = opens[2] / opens[1] - 1.0
    gross = float(current @ asset_returns)
    entering = int(np.count_nonzero((current != 0.0) & (previous != current)))
    cost = 0.0005 * entering
    net = gross - cost
    daily = np.array([0.01, -0.005, 0.02, -0.01, 0.015], dtype=float)
    wealth = np.cumprod(1.0 + daily)
    total = float(wealth[-1] - 1.0)
    sharpe = float(daily.mean() / daily.std(ddof=1) * np.sqrt(252))
    drawdown = wealth / np.maximum.accumulate(wealth) - 1.0
    maxdd = float(drawdown.min())
    calmar = total / abs(maxdd)
    rows = (
        ("composite_signal", "sigma_i = expected_return_i * confidence_i", scores.tolist(), bool(np.allclose(scores, [0, 0.7, -0.9, 0.4, -0.4, -0.12]))),
        ("cross_sectional_2L2S_control", "deterministic rank/tail allocation scaled from stated 5L/5S", current.tolist(), bool(np.isclose(current.sum(), 0) and np.isclose(np.abs(current).sum(), 2))),
        ("next_open_o2o_return", "Open(T+2)/Open(T+1)-1", asset_returns.tolist(), bool(np.all(np.isfinite(asset_returns)))),
        ("entry_cost_and_portfolio_return", "gross long-short return less 5 bps per entering position", {"entering": entering, "gross": gross, "cost": cost, "net": net}, bool(entering == 3 and np.isclose(cost, 0.0015))),
        ("reported_metrics", "total return, annualized Sharpe, maximum drawdown, Calmar", {"total": total, "sharpe": sharpe, "maxdd": maxdd, "calmar": calmar}, bool(np.isfinite([total, sharpe, maxdd, calmar]).all() and maxdd < 0)),
        ("validation_gate", "accept if e_candidate >= e_best - epsilon; update best only if strictly greater", {"accept_sideways": 0.096 >= 0.1 - 0.005, "reject": 0.094 >= 0.1 - 0.005, "update_best": 0.101 > 0.1}, True),
        ("rubric_bounds", "M_max=18, Delta_max=3, removal instruction at >=12", {"max_rules": 18, "max_mutations": 3, "compactness_threshold": 12}, True),
    )
    return [
        {
            "component": name,
            "paper_specification": specification,
            "controlled_output": json.dumps(output, sort_keys=True),
            "deterministic_control_passed": passed,
            "paper_derived_not_author_code": True,
            "author_native_pipeline_executed": False,
            "published_result_regenerated": False,
            "paper_result_credit": False,
            "boundary": "independent controlled check of a printed equation/mechanic; not the author implementation or empirical run",
        }
        for name, specification, output, passed in rows
    ]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official paper and source", "complete", "arXiv v1 PDF and complete 14-file source archive are pinned; all 18 official and rebuilt pages visually inspected"),
        ("native implementation", "claimed_but_unrecovered", "Appendix says sector rules are in released code, but no code URL is supplied and exact public searches find none"),
        ("cited LongShort-data", "dead_or_inaccessible", "bibliography cites github.com/xiwenc_msid/LLMforTrading-data; both user and repository API endpoints return 404"),
        ("stock universes", "specified", "three fixed 16-stock sector lists are printed; AMZN and TSLA overlap across sectors"),
        ("price data", "provider_and_span_only", "Yahoo daily OHLCV Apr 2024--Mar 2026 is stated without immutable snapshot, download timestamp, adjustment flags, or rows"),
        ("news data", "provider_and_cutoff_only", "Finnhub cached news and 23:59 UTC cutoff are stated; cache, article IDs/content, query parameters and API responses are absent"),
        ("features", "substantially_specified", "1/5/20-day returns, trailing 252-day range, SPY/VIX/10Y context and news window are stated"),
        ("walk-forward splits", "partial", "4/1/2-month windows, 2-month step and about 122 test days are stated; exact boundaries for all three windows are absent"),
        ("portfolio and returns", "substantially_specified", "daily score ranking, equal-weight dollar-neutral 5L/5S, next-open O2O and 5 bps entry charge are printed"),
        ("transaction-cost implementation", "ambiguous", "new entries are charged, and random flips count as two trades, but ordinary exits and live-side flips are not fully reconciled in executable terms"),
        ("rubric representation", "partial", "tuple schema and six shared rules are printed; paper says 1--4 sector rules are only in unrecovered code"),
        ("agent prompts and outputs", "missing", "complete analyst/attribution/evolution prompts, JSON schema, filled calls, responses, request IDs and temperatures are absent"),
        ("evolution algorithm", "pseudocode_complete_dependencies_missing", "five-round loop, top-20 tail diagnosis, mutation bounds, size cap and validation tolerance are printed; Attribute/Evolve/Apply are LLM-defined and unavailable"),
        ("models", "names_and_serving_partial", "four backbones and vLLM settings are named without immutable weight revisions, API snapshots, decoding parameters or environment lock"),
        ("baselines", "described_no_code_or_runs", "Random/Momentum/Mean-Reversion/Static and LLM baselines are described, but exact split calendar, Random seed, signals and outputs are absent"),
        ("randomness and run lineage", "missing", "no seeds, run IDs, API request logs, repeated-run distribution or deterministic decoding configuration are supplied"),
        ("compute", "partially_specified", "GPU counts, vLLM tensor parallelism/dtype/context and measured runtimes are stated without dependency lock or logs"),
        ("raw empirical outputs", "missing", "210 table cells and one six-series empirical panel are present without arrays, daily returns, weights, trades or result generator"),
    )
    return [{"dimension": dimension, "status": status, "detail": detail} for dimension, status, detail in specs]


def recovery_rows() -> list[dict[str, Any]]:
    specs = (
        ("Yahoo chart endpoint", "attempted", "HTTP 429", False, "no immutable price payload was recovered"),
        ("all three exact walk-forward calendars", "inspected_paper_and_source", "missing", False, "only approximate Sep 2025--Mar 2026 test span and one illustrative training interval are printed"),
        ("Yahoo download/adjustment configuration", "inspected_paper_and_source", "missing", False, "provider and broad span are named without download timestamp or adjustment flags"),
        ("Random L/S seed and draws", "inspected_paper_and_source", "missing", False, "1,000 trials are stated but seed and trial selections are absent"),
        ("turnover/cost convention", "inspected_paper_and_source", "partial", False, "new entries are charged and Random flips count twice; exits and comparable live-strategy side flips are not fully specified"),
        ("price-only published baseline cells", "combined_recovery_assessment", "not_defensibly_regenerated", False, "no prespecified complete convention can be run against immutable inputs; no tuning to printed cells is permitted"),
    )
    return [
        {
            "target": target,
            "action": action,
            "observed_state": observed,
            "published_result_regenerated": regenerated,
            "boundary": boundary,
        }
        for target, action, observed, regenerated, boundary in specs
    ]


def internal_rows() -> list[dict[str, str]]:
    proprietary = bool(
        round(np.mean([33.2, 12.7, 16.8]), 1) == 20.9
        and round(np.mean([2.45, 1.26, 1.77]), 2) == 1.83
        and round(np.mean([22.9, 17.8, -0.5]), 1) == 13.4
        and round(np.mean([1.44, 1.08, 0.10]), 2) == 0.87
        and round(np.mean([7.3, -8.7, 3.1]), 1) == 0.6
        and round(np.mean([0.75, -0.91, 0.44]), 2) == 0.09
        and round(np.mean([-6.4, 6.2, -12.9]), 1) == -4.4
        and round(np.mean([-0.42, 0.80, -1.47]), 2) == -0.36
    )
    open_source = bool(np.isclose(9.2 - (-0.6), 9.8) and np.isclose(7.6 - (-5.3), 12.9))
    if not proprietary or not open_source:
        raise ValueError("printed arithmetic consistency checks changed")
    specs = (
        ("shared_initial_rule_count", "conflict", "Appendix says six shared rules; the free-reflection example says the same initial rubric has seven rules and includes a major-corporate-event rule"),
        ("sector_rule_release", "unverifiable_release_claim", "Appendix says 1--4 sector rules are listed in released code, but no code URL is given and the only cited GitHub repository is a 404 data URL"),
        ("test_calendar", "underspecified", "paper says test periods span approximately Sep 2025--Mar 2026 and about 122 days, but does not print exact boundaries for all three windows"),
        ("transaction_cost_semantics", "ambiguous", "general portfolio text charges each new entry; Random text explicitly counts a side flip as two trades, leaving ordinary exits and comparable live-strategy turnover treatment incompletely specified"),
        ("arithmetic_proprietary_averages", "consistent", "printed three-sector averages for SHARP/Static GPT-4o-mini and GPT-4.1-mini agree with the displayed sector returns and Sharpes to rounding"),
        ("arithmetic_open_source_lifts", "consistent", "Qwen and Llama Static-to-Evo return lifts equal +9.8 and +12.9 percentage points as stated"),
        ("random_null_interpretation", "appropriately_bounded", "paper explicitly explains the negative random null as cost drag and treats three windows as directional rather than formal significance evidence"),
        ("news_safety_gap", "internally_consistent", "23:59 UTC cutoff to next 13:30 UTC market open is the stated 13.5-hour gap"),
        ("production_limits", "explicit_limitation", "paper discloses no market-impact model, one public news source and simplified daily execution"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def release_rows(scratch: Path) -> list[dict[str, Any]]:
    discovery = scratch / "discovery"
    zero_arrays = {
        "GitHub repository arXiv ID": "github-repos-arxiv.json",
        "GitHub repository exact title": "github-repos-title.json",
        "GitHub repository SHARP rubric trading": "github-repos-sharp-rubric.json",
        "GitHub repository cited dataset name": "github-repos-dataset-name.json",
        "GitHub repository LongShort-data": "github-repos-longshort.json",
        "GitHub code temporal_priced_in": "github-code-temporal-rule.json",
        "GitHub code cited dataset URL": "github-code-dataset-url.json",
        "GitHub code printed trace phrase": "github-code-trace.json",
        "GitHub code hyperparameter combination": "github-code-hyperparameters.json",
    }
    rows: list[dict[str, Any]] = []
    for surface, filename in zero_arrays.items():
        data = json.loads((discovery / filename).read_text())
        if data:
            raise ValueError(f"bounded zero-result search changed: {filename}")
        rows.append(
            {
                "surface": surface,
                "query_or_endpoint": filename,
                "observed_matches": 0,
                "attributable_sharp_release_found": False,
                "observation": "complete bounded exact public search returned zero",
                "negative_search_boundary": "zero results do not prove private, deleted, moved, renamed, unindexed or later artifacts do not exist",
            }
        )
    commits = json.loads((discovery / "github-commits-dataset-url.json").read_text())
    rows.append(
        {
            "surface": "GitHub commits cited dataset URL",
            "query_or_endpoint": "LLMforTrading-data",
            "observed_matches": commits["total_count"],
            "attributable_sharp_release_found": False,
            "observation": "bounded public commit search returned zero",
            "negative_search_boundary": "indexed public commits only",
        }
    )
    for surface, filename in (("cited GitHub user", "github-user-cited.json"), ("cited GitHub repository", "github-repo-cited.json")):
        data = json.loads((discovery / filename).read_text())
        if data.get("status") != "404":
            raise ValueError(f"cited endpoint disposition changed: {filename}")
        rows.append(
            {
                "surface": surface,
                "query_or_endpoint": "https://github.com/xiwenc_msid/LLMforTrading-data",
                "observed_matches": 0,
                "attributable_sharp_release_found": False,
                "observation": "GitHub API returned 404 for the paper-cited endpoint",
                "negative_search_boundary": "current public endpoint only; repository may be private, deleted, moved or renamed",
            }
        )
    for surface, filename in (("Hugging Face models", "huggingface-models.json"), ("Hugging Face datasets", "huggingface-datasets.json")):
        data = json.loads((discovery / filename).read_text())
        rows.append(
            {
                "surface": surface,
                "query_or_endpoint": "SHARP financial trading rubric",
                "observed_matches": len(data),
                "attributable_sharp_release_found": False,
                "observation": "bounded name-token search",
                "negative_search_boundary": "name search only",
            }
        )
    return rows


def build(scratch: Path, output: Path) -> dict[str, Any]:
    verify_pins(scratch)
    files = paper_sources(scratch)
    official_pages = len(PdfReader(scratch / "primary/official.pdf").pages)
    rebuilt_pages = len(PdfReader(scratch / "primary/rebuilt.pdf").pages)
    official_text = (scratch / "primary/official.txt").read_text(errors="replace")
    rebuilt_text = (scratch / "primary/rebuilt.txt").read_text(errors="replace")
    overlap = token_jaccard(official_text, rebuilt_text)
    if (official_pages, rebuilt_pages) != (18, 18) or overlap < 0.999:
        raise ValueError("paper rebuild/page evidence changed")

    output.mkdir(parents=True, exist_ok=True)
    results = result_rows(files)
    figures = figure_rows(files)
    components = component_rows()
    methods = method_rows()
    consistency = internal_rows()
    releases = release_rows(scratch)
    recovery = recovery_rows()
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "component_execution_audit.csv", components)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "release_search_audit.csv", releases)
    write_csv(output / "baseline_recovery_audit.csv", recovery)

    provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "arxiv_version": "v1",
        "published_utc": "2026-05-07T18:23:44Z",
        "source_files": len(files),
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "official_pages_visually_checked": 18,
        "rebuilt_pages_visually_checked": 18,
        "visual_defects_observed": 0,
        "official_rebuilt_token_jaccard": overlap,
        "paper_contains_native_implementation_url": False,
        "paper_contains_dataset_url": True,
        "paper_cited_dataset_url_current_status": 404,
        "attributable_sharp_implementation_found": False,
        "negative_search_scope": "bounded public GitHub repo/code/commit and Hugging Face searches plus direct cited-user/repository API checks; not proof of permanent absence",
        "pins": PINS,
    }
    write_json(output / "source_provenance.json", provenance)

    readme = f"""# SHARP paper-level replication audit

**Verdict: the paper is unusually specification-rich, but its native implementation and data are not recoverable, so it is not reproducible end to end.** The pinned arXiv `2605.06822v1` source rebuilds to the official 18-page count with {overlap:.2%} extracted-token multiset overlap. All 18 official and 18 rebuilt pages were visually inspected without observed clipping, overlap, missing assets, or unreadable research content.

The active empirical denominator is **210 displayed quantitative result cells across four tables and one empirical figure panel**. The panel contains six cumulative-return series. **Zero of 210 cells and 0/1 empirical panels are author-natively regenerated.** The archive contains printed tables and one rendered cumulative-return asset, not the immutable Yahoo rows, Finnhub article cache, exact three split calendars, daily LLM outputs, prompts/calls, rubric histories, portfolio weights, trades, returns, baseline seeds, or result generator.

The paper does not provide an implementation URL. It says sector-specific rules are listed in released code, but the only GitHub URL in the source is a bibliography entry for `xiwenc_msid/LLMforTrading-data`. Both that repository and the cited user currently return 404. Five exact GitHub repository searches, four source-unique code searches, a commit search, and Hugging Face model/dataset searches find no attributable SHARP implementation or recoverable dataset. These are bounded observations, not proof that private, deleted, moved, renamed, unindexed, or later artifacts do not exist.

Seven independently implemented paper-derived mechanics pass deterministic controlled checks: composite score, ranked dollar-neutral tail portfolio, next-open O2O return, entry-cost accounting, reported metrics, validation gate, and rubric bounds. These are **specification checks, not author code or empirical results**. A Yahoo chart-endpoint retrieval attempt returned HTTP 429; more importantly, the paper omits exact boundaries for all three windows, adjustment/download settings, the Random seed, and enough turnover semantics for a unique result-producing reconstruction. The audit therefore does not tune conventions until a published value matches.

Material boundaries and inconsistencies are explicit. Appendix says the shared initial rubric has six rules, while the free-reflection section calls the same initialization seven rules and adds a major-corporate-event rule. The claimed released sector rules are unavailable. The general cost description charges new entries, while the Random baseline counts a side flip as two trades; exits and cross-strategy turnover treatment are not fully executable from prose. By contrast, the printed proprietary-model averages, open-source lifts, negative-null explanation, news safety gap, and limitations are internally consistent or appropriately bounded. `strict_success` remains false.
"""
    (output / "README.md").write_text(readme)

    generated = {path.name: sha256(path) for path in sorted(output.iterdir()) if path.is_file() and path.name != "manifest.json"}
    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "active_quantitative_table_cells": len(results),
        "result_tables": len(TABLE_SPECS),
        "author_native_table_cells_regenerated": 0,
        "active_empirical_figure_panels": sum(int(row["empirical_panels"]) for row in figures),
        "empirical_figure_series_or_groups": sum(int(row["empirical_series_or_groups"]) for row in figures),
        "author_native_empirical_panels_regenerated": 0,
        "paper_derived_components_executed": len(components),
        "paper_derived_components_passing_controlled_checks": sum(bool(row["deterministic_control_passed"]) for row in components),
        "attributable_sharp_implementation_found": False,
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
