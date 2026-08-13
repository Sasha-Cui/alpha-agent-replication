#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for TiMi."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/timi_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/timi"
WORK_ID = "CensusArxiv251004787"
SYSTEM_ID = "SYS-TRADE-IN-MINUTES"
ARXIV_ID = "2510.04787"
OPENREVIEW_ID = "ROEwZAxqyS"
SUPPLEMENT_PATH = "/attachment/a7f4111f00a10d307b4ee29926741553acafbb99.zip"

VERSION_SPECS = {
    "v1": ("2025-10-06T13:08:55Z", 16, 21, 3_855_092, 4, 6),
    "v2": ("2026-02-09T07:01:32Z", 17, 22, 4_063_963, 6, 6),
}

# One result unit is a printed empirical scalar in an active result table.  Data
# duration tokens are setup requirements, not results, and are excluded.
RESULT_TABLES = {
    "tab_backtest_2024": ("sections/experiments.tex", 1, 16, 144),
    "tab_DR_SR": ("sections/experiments.tex", 2, 7, 7),
    "tab_performance_comparison": ("sections/experiments.tex", 1, 16, 160),
    "tab:ablation": ("sections/experiments.tex", 2, 6, 18),
    "tab_latency": ("sections/appendix.tex", 1, 4, 12),
    "tab_ablation": ("sections/appendix.tex", 2, 2, 8),
}

PINS = {
    "arxiv-abs.html": "f7c1b5f7412648c600490979438bc2573ce643f144a613159bfcbce127485275",
    "arxiv-api.xml": "a1b473a31b99b76a20ca4003169fc45cfb46fea38fd483a611e1fe69b6b2d9ad",
    "timi-v1.pdf": "52c59e6eb4cc2c6eaede38b120fccc05ecaa4e7cfa89e72192ba6126b3e9ae92",
    "timi-v2.pdf": "2fb945c939b595a2a86af040b667079d2528e00996fef3c9fd6e7b3268f52adb",
    "timi-v1-source.tar": "894d95dcb8864781558d391934aa7ba1b80a2a42f1867beb5b1398da7119b196",
    "timi-v2-source.tar": "25b7014a6340b1cea08a5a9740c26ea0c3b2dbeb6c1e95c2a32f2252ca5d4c50",
    "build-v1/main.pdf": "8788d5358eee88902643680a1ff8276c0eb40837aff11839e65112424d1b4025",
    "build-v2/main.pdf": "a3f52cc62f405528d8fd31e05609b6d7afe7abc0bc4cbb7078da5d3a61d84a83",
    "contact-v1/sheet-1.jpg": "4b4686def86fc163f335b9241b1df276645f9026a6d11b4d9dc161f6c3e52668",
    "contact-v1/sheet-2.jpg": "dfc58fe944a636d317a75c6370b533594b1aa080adf553c4694cb8721493ac23",
    "contact-v2/sheet-1.jpg": "716e73a347918a2e02e1568f3e604e38c3c2a79dd1ceb79ef8cc8e3854632047",
    "contact-v2/sheet-2.jpg": "4b6ae1e458e6ea8ce694ee941156b50d4a09f3f6f0fcda2f3cebde22deac0691",
    "contact-v2/sheet-3.jpg": "4698f7f7f2b109bb642034bf4296fb933431000668f74d3e8712729e9dbb111b",
    "discovery/github-code-arxiv.json": "243573d6e81ef077809590a922b60759a8788d200183a5b814f068c5519a89eb",
    "discovery/github-code-title.json": "380b438bec905bb264843ea8fa2d4f8827a70643571225c5a12926f5dc9bf756",
    "discovery/github-repos-arxiv.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-repos-title.json": "628e61073d4ffc0dd0cbaf17fd1c6bd9c7a827258ae80a7e04543695252c5507",
    "discovery/qoeop-repo.json": "539464b2e4a4377d83682b1f7379f24fe551e39259f16b3a5a234ca061d4bf12",
    "discovery/qoeop-commits.json": "fa36413af4502643648f9d11103d85195bb806a547d02e456d045092189cc23c",
    "discovery/cajias-repo.json": "f8b74fab23b31dd6586a94dad0a97d96e2bddd067174e8c4fde567cc03ac5b35",
    "discovery/cajias-timi-commits.json": "7e52583efb3fbca87a62a9bcaed401ae5fb5aaa504c582c928399e258947bbac",
    "discovery/openreview-supplement-logical-response.html": "a2d811e0d24af89d9bd4b19cc9e8fbc474c67ef3827648550a6560eca2a5e332",
    "discovery/openreview-supplement-logical-status.txt": "97a58cc66d1cd6b51466af8ed52d6a38053b5572fee09a0ae8859c26b82bdf67",
    "discovery/openreview-supplement-immutable-response.html": "a73f7ab72b25a99369edc718ee28902bef6a38b582bc59940edd5060bf1e5ec7",
    "discovery/openreview-supplement-immutable-status.txt": "f8bf41177a5f5e808a7ccb648b51080b031f15ca8018d91a576263d6cc626eb6",
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


def validate_tar(path: Path) -> list[tarfile.TarInfo]:
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
    for member in members:
        pure = PurePosixPath(member.name)
        if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
            raise ValueError(f"unsafe archive member: {member.name}")
    return [member for member in members if member.isfile()]


def validate_inputs(scratch: Path) -> dict[str, list[tarfile.TarInfo]]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    inventories = {}
    for version, (_, pages, files, size, tables, figures) in VERSION_SPECS.items():
        members = validate_tar(scratch / f"timi-{version}-source.tar")
        if (len(members), sum(item.size for item in members)) != (files, size):
            raise ValueError(f"{version} source inventory changed")
        sections = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((scratch / f"source-{version}/sections").glob("*.tex"))
        )
        active_tables = sections.count(r"\begin{table") + sections.count(r"\begin{wraptable")
        if (active_tables, len(re.findall(r"\\label\{fig_", sections))) != (tables, figures):
            raise ValueError(f"{version} manuscript environment inventory changed")
        if len(PdfReader(scratch / f"timi-{version}.pdf").pages) != pages:
            raise ValueError(f"{version} official page count changed")
        if len(PdfReader(scratch / f"build-{version}/main.pdf").pages) != pages:
            raise ValueError(f"{version} rebuilt page count changed")
        inventories[version] = members
    if (scratch / "discovery/openreview-supplement-logical-status.txt").read_text() != "403\n":
        raise ValueError("OpenReview logical supplement access status changed")
    if (scratch / "discovery/openreview-supplement-immutable-status.txt").read_text() != "404\n":
        raise ValueError("OpenReview immutable supplement access status changed")
    return inventories


def table_block(text: str, label: str) -> str:
    marker = r"\label{" + label + "}"
    position = text.index(marker)
    begins = [
        text.rfind(r"\begin{table", 0, position),
        text.rfind(r"\begin{wraptable", 0, position),
    ]
    begin = max(begins)
    if begin < 0:
        raise ValueError(f"missing table begin for {label}")
    end_candidates = [
        value for value in (
            text.find(r"\end{table", position),
            text.find(r"\end{wraptable", position),
        ) if value >= 0
    ]
    return text[begin:min(end_candidates)]


def result_rows(source: Path) -> list[dict[str, Any]]:
    rows = []
    blocker = (
        "TiMi code, frozen market/news inputs, exact prompts/model calls, generated bots, "
        "simulation/live trade logs, baseline configs, fees/funding snapshots, seeds, and raw arrays are absent"
    )
    for label, (relative, first_result_column, expected_rows, expected) in RESULT_TABLES.items():
        text = (source / relative).read_text(encoding="utf-8")
        block = table_block(text, label)
        tabular_begin = block.index(r"\begin{tabular}")
        tabular_end = block.index(r"\end{tabular}", tabular_begin)
        tabular = block[tabular_begin:tabular_end]
        values = []
        matched_rows = 0
        units_per_row = expected // expected_rows
        for raw_row in re.split(r"\\\\(?:\[[^]]*\])?", tabular):
            raw_row = re.sub(r"(?<!\\)%.*", "", raw_row)
            raw_row = re.sub(r"\\multicolumn\{\d+\}\{[^}]*\}", "", raw_row)
            if "&" not in raw_row:
                continue
            row_values = []
            cells = raw_row.split("&")
            for cell in cells[first_result_column:]:
                row_values.extend(re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", cell))
            if label == "tab_DR_SR" and row_values:
                row_values = row_values[-1:]
            if len(row_values) == units_per_row:
                matched_rows += 1
                values.extend(row_values)
        if (matched_rows, len(values)) != (expected_rows, expected):
            raise ValueError(
                f"{label} has {matched_rows} result rows/{len(values)} units, "
                f"expected {expected_rows}/{expected}"
            )
        for index, value in enumerate(values, 1):
            rows.append({
                "version": "v2", "table_label": label,
                "printed_numeric_unit": index, "printed_value": value,
                "source_document_recovered": True,
                "author_native_experiment_executed": False,
                "published_result_regenerated": False,
                "paper_result_credit": False,
                "blocking_reason": blocker,
            })
    return rows


def figure_rows() -> list[dict[str, Any]]:
    specs = (
        ("fig_system", 1, 0, "system architecture"),
        ("fig_evolution_map", 1, 0, "illustrated optimization evolution map"),
        ("fig_AL_CUR", 2, 2, "action latency and capital utilization"),
        ("fig_violin", 1, 1, "ARR distributions across trading pairs"),
        ("fig_ablation", 1, 1, "bot-variant cumulative returns"),
        ("fig_timi_transactions", 4, 4, "four live transaction case charts"),
    )
    return [{
        "version": "v2", "figure": figure, "panels": panels,
        "empirical_panels": empirical, "description": description,
        "rendered_author_asset_recovered": True,
        "underlying_numeric_arrays_recovered": False,
        "author_native_figure_regenerated": False,
        "paper_result_credit": False,
    } for figure, panels, empirical, description in specs]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official_document_source", "complete", "arXiv v1/v2 PDFs and complete TeX source packages recovered and rebuilt"),
        ("accepted_record", "verified", "OpenReview ICLR 2026 Poster record is CC BY 4.0 and lists a supplementary ZIP"),
        ("supplement", "listed_but_currently_unrecoverable", f"logical endpoint returns 403 and immutable {SUPPLEMENT_PATH} returns 404"),
        ("paper_specific_release", "missing", "no attributable TiMi implementation or experiment package found"),
        ("markets_and_period", "partially_specified", "CME index futures and Binance cryptocurrencies; live January-April 2025, backtest 2024; exact instruments/dates are incomplete"),
        ("universe", "partially_specified", "213 supported pairs reported, but the full point-in-time pair list is not released"),
        ("frequency", "specified", "minute-level deployment; transaction figure uses 15-minute visualization candles"),
        ("market_data", "specified_not_frozen", "K-lines, volatility, liquidity, funding-rate changes, market capitalization, news, and indicators described without frozen records"),
        ("agent_architecture", "paper_specification_only", "macro analysis, strategy adaptation, bot evolution, and feedback reflection agents described but not released"),
        ("model_backbones", "named_not_replayable", "DeepSeek-V3, Qwen2.5-Coder-32B-Instruct, and DeepSeek-R1 named without immutable model/API requests or decoding configuration"),
        ("prompts", "not_released", "no exact runtime prompt templates, filled calls, responses, traces, or generated bots are included"),
        ("optimization", "paper_specification_only", "parameter/function/strategy escalation and three worked constraint examples are described without optimizer code or histories"),
        ("execution", "partially_specified", "LIMIT entries, TP/STOP monitoring, MARKET risk exits, CME/Binance, stateless recovery, and API checks are described"),
        ("costs_and_slippage", "underspecified", "fees and funding are modeled and LIMIT entry is said to eliminate entry slippage, but schedules, realized records, and simulator code are absent"),
        ("baselines", "underspecified", "16 baselines are named; several live results are estimated partial experiments and exact implementations/configurations are absent"),
        ("replications_and_uncertainty", "not_released", "no random seeds, repeat count, confidence intervals, significance tests, or raw per-run outputs"),
        ("published_results", "not_regenerated", "zero of 349 active current-table empirical units and zero of eight empirical figure panels regenerated"),
        ("search_for_release", "no_attributable_public_implementation_found", "exact GitHub title/arXiv searches found only references and later unaffiliated adaptations"),
    )
    return [{"version": "v2", "dimension": d, "status": s, "detail": detail} for d, s, detail in specs]


def internal_rows() -> list[dict[str, str]]:
    specs = (
        ("document_rebuild", "all_pages_match_visually", "33 official and 33 rebuilt pages checked; zero unreadable, clipped, overlapping, blank, or missing research pages"),
        ("transaction_figure_order_counts", "paper_prose_conflict", "Figure 6 reports OM=61 and SIGN=45 valid orders; v2 prose says 28 and 39"),
        ("supplement_release", "listed_but_not_retrievable", "accepted record identifies a public supplement but its logical and immutable paths currently return 403/404"),
        ("code_release_language", "not_fulfilled_in_pinned_evidence", "v1 commits to open-source code/records; v2 says code and corner cases will be released; no attributable release was found"),
        ("version_result_lineage", "material_revision_without_raw_lineage", "v2 adds 2024 backtests and component ablations after v1 without raw runs or immutable lineage"),
        ("posterior_information", "paper_acknowledges_risk", "v2 says LLM agents exploit news and potential posterior information; no timestamped provenance is released to audit leakage"),
        ("annual_return_formula", "not_annualized_as_printed", "ARR is described as annual rate but printed formula is a simple total return with no time annualization exponent"),
        ("baseline_comparability", "partial_and_estimated", "live table marks several supported-pair results as estimates from partial experiments and mixes minute/second/hourly/daily frequencies"),
        ("llm_disclosure", "scope_conflict", "paper uses LLM agents as core methodology while Appendix D says LLMs were used solely for grammar/polish; likely disclosure-form wording but literally inconsistent"),
        ("third_party_candidates", "unattributable", "qOeOp/vibe-trading begins 2026-01-11 under Vincent Xu; cajias/nautilus-trading TiMi material appears 2026-04-21 under Raul; neither author identity matches the paper"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def release_search(scratch: Path) -> dict[str, Any]:
    repo_arxiv = json.loads((scratch / "discovery/github-repos-arxiv.json").read_text())
    code_title = json.loads((scratch / "discovery/github-code-title.json").read_text())
    qoeop = json.loads((scratch / "discovery/qoeop-repo.json").read_text())
    qoeop_commits = json.loads((scratch / "discovery/qoeop-commits.json").read_text())
    cajias = json.loads((scratch / "discovery/cajias-repo.json").read_text())
    cajias_commits = json.loads((scratch / "discovery/cajias-timi-commits.json").read_text())
    if repo_arxiv != [] or [row["repository"]["nameWithOwner"] for row in code_title] != ["cajias/nautilus-trading"]:
        raise ValueError("GitHub TiMi search evidence changed")
    return {
        "official_paper_implementation_recovered": False,
        "official_transaction_records_recovered": False,
        "official_corner_case_list_recovered": False,
        "official_prompts_or_runtime_trajectories_recovered": False,
        "official_frozen_data_or_result_arrays_recovered": False,
        "microsoft_research_page_lists_project_or_github": False,
        "github_exact_arxiv_repository_matches": 0,
        "github_exact_title_code_candidates": ["cajias/nautilus-trading"],
        "unaffiliated_candidates": [
            {
                "repository": qoeop["full_name"],
                "created_at": qoeop["created_at"],
                "earliest_sampled_commit": qoeop_commits[-1]["commit"]["author"],
                "attribution": "Vincent Xu; no paper-author identity match",
                "native_paper_credit": False,
            },
            {
                "repository": cajias["full_name"],
                "created_at": cajias["created_at"],
                "timi_path_commit": cajias_commits[0]["commit"]["author"],
                "attribution": "Raul; no paper-author identity match",
                "native_paper_credit": False,
            },
        ],
        "bounded_negative_inference": (
            "No attributable public implementation was found in the pinned primary pages, Microsoft Research listing, "
            "or exact GitHub searches; this does not prove private, deleted, or unindexed artifacts never existed."
        ),
    }


def readme() -> str:
    return """# TiMi paper/source and public-release audit

This audit pins both official versions of arXiv `2510.04787`, both complete
source packages, the accepted OpenReview record, its listed supplement, and
bounded exact-title/arXiv release searches. The v1 and v2 sources rebuild to
the official 16- and 17-page counts. All 33 official and all 33 rebuilt pages
were visually checked side by side; no unreadable, clipped, overlapping,
blank, or missing research content was found. This is excellent manuscript
reproducibility, not experimental reproducibility.

The current v2 contains 349 printed empirical numeric units across six active
result tables and six author-rendered figure assets with ten total panels,
eight of them empirical. The source package contains those reported tables and
rendered PDFs, not their underlying arrays. It ships no TiMi implementation,
exact runtime prompts or model calls, generated bots, frozen K-lines/news,
point-in-time 213-pair universe, baseline configurations, fee/funding records,
simulation/live trade logs, seeds, portfolios, returns, or result generator.

The ICLR 2026 OpenReview record is first-party and CC BY 4.0. It explicitly
lists a supplementary ZIP at immutable path
`/attachment/a7f4111f00a10d307b4ee29926741553acafbb99.zip`.
At audit time the logical attachment endpoint returned HTTP 403 and that
immutable path returned HTTP 404, including through the signed-in visible UI.
The supplement therefore existed in metadata but is not currently recoverable;
it must not be treated as inspected or absent. The paper says real transaction
cost records are in that supplement, which makes the broken attachment a
material replication blocker.

Exact GitHub searches found no repository for the arXiv identifier and no
attributable author implementation. `qOeOp/vibe-trading` and the TiMi design
under `cajias/nautilus-trading` are later third-party adaptations whose commit
authors do not match any paper author. They may be useful engineering, but
neither can establish TiMi experiment lineage and both receive zero native
paper credit.

The strict paper-level result is **0/349 active empirical table units and 0/8
empirical figure panels regenerated**. The audit also finds material internal
or evidentiary weaknesses: Figure 6 reports 61 OM and 45 SIGN orders while v2
prose says 28 and 39; the printed ARR equation is an unannualized total return;
v2 acknowledges that LLM baselines may exploit potential posterior information;
several live baseline coverage values are estimates from partial experiments;
and the new v2 backtest/ablation results have no released raw lineage. TiMi is
well described conceptually and its paper is fully rebuildable, but it is not
currently a defensible true experimental replication package.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inventories = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    results = result_rows(scratch / "source-v2")
    figures = figure_rows()
    versions = []
    source_inventory = []
    for version, (submitted, pages, files, size, tables, figure_count) in VERSION_SPECS.items():
        versions.append({
            "version": version, "submitted": submitted,
            "title": "Trade in Minutes! Rationality-Driven Agentic System for Quantitative Financial Trading",
            "authors": 8, "official_pages": pages, "source_files": files,
            "source_uncompressed_bytes": size, "rebuilt_pages": pages,
            "active_table_environments": tables, "figure_assets": figure_count,
            "current_version_published_numeric_result_units": len(results) if version == "v2" else "",
            "current_version_empirical_panels": sum(row["empirical_panels"] for row in figures) if version == "v2" else "",
        })
        for member in inventories[version]:
            source_inventory.append({
                "version": version, "path": member.name, "bytes": member.size,
                "role": "official_manuscript_source",
                "paper_system_implementation": False,
                "underlying_experiment_data": False,
            })
    write_csv(output / "version_audit.csv", versions)
    write_csv(output / "source_inventory.csv", source_inventory)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", internal_rows())
    search = release_search(scratch)
    write_json(output / "release_search_audit.json", search)
    write_json(output / "source_provenance.json", {
        "work_id": WORK_ID, "system_id": SYSTEM_ID,
        "arxiv": {
            "id": ARXIV_ID, "versions": list(VERSION_SPECS),
            "pdf_sha256": {v: PINS[f"timi-{v}.pdf"] for v in VERSION_SPECS},
            "source_sha256": {v: PINS[f"timi-{v}-source.tar"] for v in VERSION_SPECS},
            "license": "CC BY 4.0",
            "visual_qa": {
                "official_pages_inspected": 33, "rebuilt_pages_inspected": 33,
                "unreadable_clipped_overlapping_blank_or_missing_pages": 0,
                "contact_sheet_sha256": {
                    key: value for key, value in PINS.items() if key.startswith("contact-")
                },
            },
        },
        "openreview": {
            "forum_id": OPENREVIEW_ID, "venue": "ICLR 2026 Poster",
            "license": "CC BY 4.0", "supplement_listed": True,
            "supplement_immutable_path": SUPPLEMENT_PATH,
            "supplement_recovered": False,
            "logical_endpoint_status": 403, "immutable_endpoint_status": 404,
        },
        "release_search": search,
        "release_boundary": {
            "attributable_timi_source_recovered": False,
            "complete_research_inputs_recovered": False,
            "published_result_lineage_recovered": False,
            "third_party_adaptations_counted_as_native": False,
        },
    })
    (output / "README.md").write_text(readme(), encoding="utf-8")
    manifest = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "arxiv_id": ARXIV_ID,
        "openreview_id": OPENREVIEW_ID, "official_versions_audited": list(VERSION_SPECS),
        "official_pdf_and_source_recovered": True, "document_rebuild_completed": True,
        "official_pages_visually_checked": 33, "rebuilt_pages_visually_checked": 33,
        "source_files_across_versions": len(source_inventory),
        "published_numeric_result_units": len(results), "native_numeric_units_regenerated": 0,
        "figures": len(figures), "figure_panels": sum(row["panels"] for row in figures),
        "empirical_panels": sum(row["empirical_panels"] for row in figures),
        "native_empirical_panels_regenerated": 0,
        "official_supplement_listed": True, "official_supplement_recovered": False,
        "attributable_timi_code_recovered": False, "third_party_candidates": 2,
        "full_end_to_end_pipeline_reproduced": False, "strict_success": False,
    }
    manifest["output_sha256"] = {
        path.name: sha256(path) for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(args.output)
    if args.strict and not manifest["strict_success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
