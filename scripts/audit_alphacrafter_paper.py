#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for AlphaCrafter."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphacrafter_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/alphacrafter"
WORK_ID = "CensusArxiv260505580"
SYSTEM_ID = "SYS-ALPHA-CRAFTER"
ARXIV_ID = "2605.05580"
REPOSITORY_URL = "https://github.com/NJU-LINK/AlphaCrafter"
REPOSITORY_HEAD = "c6dbc1ba4e0a4ecbc3ea1454c5290dbea4b36b0d"

PINS = {
    "primary/arxiv-abs.html": "676a1af03dc2df13bbb7becb15394299af5137816e7a80a48f5636a39ac99506",
    "primary/arxiv-api.xml": "de6282b961ec3ad7462744ed8ae886dba5ba1570df6cc800395544054e1aa001",
    "primary/arxiv-v1.pdf": "7e7da45cdc80bab1ddbd272b3b6198113aef50712357508c2b589afd00d0239d",
    "primary/arxiv-v2.pdf": "50fac266012726355d34b64788c529adf09c8574a751395d55858640dc1a5e67",
    "source/arxiv-v1.tar": "511e441781702609d11024dbe31577c6396c1f68e3023f08326050417e399f53",
    "source/arxiv-v2.tar": "36a34ecb7ef524d8d7efe4a67002e726a0345bc6c3f5414325dd18a080829b84",
    "build-v1/main.pdf": "906e50f764e58c5f6b9ccc98b721e3762689120bd99297f4eef70f74a671c10e",
    "discovery/alphacrafter-c6dbc1b.zip": "41b7b55892cd43ec8594b7a6070ae2a70ebdf4da38b3b52ee06e99d54e0660b1",
    "native-component-checks.json": "9d1fbc4c5014b1884f76eaa6634d752aeb11a805b0b747bcf58b04d89c18928f",
    "native-main.txt": "d778467aa5554cb4de99089056f06013ed5791aa2ab93a72128486e89ea68b55",
    "native-pip-freeze.txt": "39ec7c8a551a4b96634c5ea1869ef87d21c16c44e62c2b9335c30211526222e8",
    "native-pytest.txt": "e20bfc015edf2db51a15a3b771e93294c2104148ca78858528c2278ae8946637",
    "native-ruff.json": "8a73043953116a9bbb20c65a1ea602e4f385d9aad8e294fec88b291465d4672b",
    "native-compileall.txt": "abc5ef4443b0ed37c77cf8f0c3663af805a0c12cd6ae08bca6cdb7121379ca84",
    "native-help.txt": "dfa40b04eb6a55fdb04e4468dd9667a842ade3b0edda66f2b20a6720191cff81",
    "build-v1-pass1.txt": "5b59153a434e6bb32af5161ce2645cd44188521560876b35df395d9fece638f7",
    "build-v1-pass2.txt": "67f1f55ff2049b58a0b035424ba765e0c94101f06fc45e7e4cda1f863eae7b79",
    "build-v1-bibtex.txt": "a60ace9defa315492874048ffd423d10fbf8b6413f572201c9a075025bca623c",
    "build-v2-pass1.txt": "ef8f919b8191ebba181c6f256f3fc134f8b1e7bf37f52bb2fc822c79f72b9378",
    "build-v2-pass2.txt": "320d7fe8207045aa30c19993ff50488fae1f32ad02df3e34c8a1901e6a430fb2",
    "build-v2-pass3.txt": "881ac946cbaf0d310c4cf56ff7d21602da15f9b4d25646573958a9adb5365e9f",
    "viz/v1-official-contact.jpg": "133553ba0d74032301b4275800dc93e64005bc4b4b612cedca0c575f452a5961",
    "viz/v2-official-contact.jpg": "eba5aecf8e4b75505fd0bac696929ea97adb10b4fec3373fb23bb708c21fc80c",
    "viz/v1-rebuilt-contact.jpg": "e339173a02746fb179dc0f09bf8ddcc1563cbe53373f305843d77458f733030a",
}

V1_RESULT_TABLES = {"tab:combined": 144, "tab:ablation": 32}
V2_RESULT_TABLES = {"tab:combined": 264, "tab:ablation": 40}


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
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def safe_archives(scratch: Path) -> None:
    for relative in ("source/arxiv-v1.tar", "source/arxiv-v2.tar"):
        with tarfile.open(scratch / relative, "r:*") as archive:
            for member in archive.getmembers():
                pure = PurePosixPath(member.name)
                if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                    raise ValueError(f"unsafe archive member: {relative}:{member.name}")
    with zipfile.ZipFile(scratch / "discovery/alphacrafter-c6dbc1b.zip") as archive:
        for member in archive.infolist():
            pure = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            if pure.is_absolute() or ".." in pure.parts or (mode & 0o170000) == 0o120000:
                raise ValueError(f"unsafe repository archive member: {member.filename}")


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    safe_archives(scratch)
    with tarfile.open(scratch / "source/arxiv-v1.tar", "r:*") as archive:
        v1_members = [member for member in archive.getmembers() if member.isfile()]
    with tarfile.open(scratch / "source/arxiv-v2.tar", "r:*") as archive:
        v2_members = [member for member in archive.getmembers() if member.isfile()]
    if (len(v1_members), sum(item.size for item in v1_members)) != (25, 1_848_965):
        raise ValueError("v1 source inventory changed")
    if (len(v2_members), sum(item.size for item in v2_members)) != (22, 1_574_465):
        raise ValueError("v2 source inventory changed")
    with zipfile.ZipFile(scratch / "discovery/alphacrafter-c6dbc1b.zip") as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
    if (len(files), sum(item.file_size for item in files)) != (79, 889_614):
        raise ValueError("attributable repository archive inventory changed")
    return {"v1_source_files": 25, "v2_source_files": 22, "release_files": 79}


def result_rows(version: str, specifications: Mapping[str, int]) -> list[dict[str, Any]]:
    rows = []
    for table, count in specifications.items():
        for index in range(1, count + 1):
            rows.append(
                {
                    "version": version,
                    "table_label": table,
                    "printed_numeric_unit": index,
                    "source_document_recovered": True,
                    "author_native_experiment_executed": False,
                    "published_result_regenerated": False,
                    "paper_result_credit": False,
                    "blocking_reason": (
                        "research market/news/fundamental data, baselines, trial outputs, model calls, and result arrays are not released"
                    ),
                }
            )
    return rows


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("v1", "official_document_source", "complete", "25-file primary source package recovered; 26-page manuscript rebuilt"),
        ("v2", "official_document_source", "complete_build_blocked", "22-file primary source recovered; available TeX Live repeatedly stalls in CJK encoding before PDF output"),
        ("v1_v2", "attributable_repository", "substantial_component_release", "79-file MIT repository under the authors' NJU-LINK organization matches title, authors, architecture, and arXiv id; the paper does not directly link it"),
        ("v1_v2", "market_universes", "specified", "CSI 300 and S&P 500 constituents"),
        ("v1_v2", "market_data", "named_not_released", "Baostock OHLCV, Yahoo Finance OHLCV, and Lixinger fundamentals/statements/news are named; research snapshots are absent"),
        ("v1_v2", "temporal_split", "specified", "training 2016-01-04--2022-12-30, validation 2023, backtest 2024-01-02--2026-02-27, live 2026-03-02--2026-06-12"),
        ("v1_v2", "constituent_history", "underspecified_unreleased", "point-in-time memberships and complete included-date arrays are not released"),
        ("v1_v2", "miner_screener_trader_prompts", "substantially_released", "role instructions and Markdown skill policies are present"),
        ("v1_v2", "workflow_budget", "released", "three miners, 25 iterations per role, and 150 cycles are configured"),
        ("v1_v2", "model_backbones", "paper_specified_release_incomplete", "paper uses GPT 5.3 Codex, Claude Opus 4.6, and Gemini 3.1 Pro; runtime is OpenAI Responses-only"),
        ("v1_v2", "default_model_configuration", "internally_broken", "config requests gpt-5.3-codex but shipped model registries contain only gpt-5 and gpt-5.2"),
        ("v1_v2", "a_share_exchange", "component_executed", "native buy, T+1 unlock, sell, and 2-bp commission behavior execute on controlled two-day data"),
        ("v1_v2", "us_exchange", "component_executed", "native short, cover, margin path, and 1-bp commission behavior execute on controlled two-day data"),
        ("v1_v2", "daily_metric_contract", "component_executed", "released evaluation contract computes total return and maximum drawdown on controlled NAVs"),
        ("v1_v2", "end_to_end_market_routing", "incomplete", "launcher always injects A-share instructions; BacktestTool and StepTool are instantiated with default A-share mode"),
        ("v1_v2", "release_data_payload", "templates_only", "index series and schemas are present; stock CSVs contain headers only and financial/news files are templates"),
        ("v1_v2", "release_date_coverage", "insufficient", "template calendars end 2026-03-31 while revised live evaluation ends 2026-06-12"),
        ("v1_v2", "baseline_implementations", "missing", "MACD, Grid, ML/DL, and agent baseline implementations/configurations are absent"),
        ("v1_v2", "trial_protocol", "partially_specified", "10 independent trials and interquartile-range averaging are stated; seeds and model sampling parameters are absent"),
        ("v1_v2", "transaction_costs", "implemented_simplification", "A-share 2 bp and U.S. 1 bp proportional fees match v2; market impact and time-varying slippage are abstracted"),
        ("v1_v2", "live_brokerage", "missing", "broker identity, paper-trading API integration, orders, fills, and logs are absent"),
        ("v1_v2", "raw_results", "missing", "no factor pools, model calls, actions, holdings, returns, trial arrays, or figure/table generator is released"),
        ("v1_v2", "published_results", "not_regenerated", "zero published numeric table units and zero empirical panels were regenerated"),
    )
    return [
        {"version": version, "dimension": dimension, "status": status, "detail": detail}
        for version, dimension, status, detail in specs
    ]


def figure_rows() -> list[dict[str, Any]]:
    specs = (
        ("v1", "fig:stability_analysis", 2, "trial-distribution panels"),
        ("v1", "fig:model_stability", 2, "backbone radar panels"),
        ("v1", "fig:alpha_decay_analysis", 2, "IC-decay panels"),
        ("v1", "fig:factor_case_study", 2, "factor-diversity panels"),
        ("v1", "fig:regime_heatmaps", 6, "trend, volatility, and correlation heatmaps for two markets"),
        ("v1", "fig:exposure_volatility", 2, "time-series and scatter panels"),
        ("v2", "fig:stability_trial", 1, "cross-trial range panel"),
        ("v2", "fig:stability_model", 1, "backbone radar panel"),
        ("v2", "fig:alpha_decay_analysis", 2, "IC-decay panels"),
        ("v2", "fig:factor_case_study", 2, "factor-diversity panels"),
        ("v2", "fig:regime_heatmaps", 6, "trend, volatility, and correlation heatmaps for two markets"),
        ("v2", "fig:exposure_volatility", 2, "time-series and scatter panels"),
    )
    return [
        {
            "version": version,
            "figure": figure,
            "empirical_series_or_panels": count,
            "description": description,
            "underlying_numeric_array_released": False,
            "author_native_figure_regenerated": False,
            "paper_result_credit": False,
        }
        for version, figure, count, description in specs
    ]


def version_rows() -> list[dict[str, Any]]:
    return [
        {
            "version": "v1",
            "submitted": "2026-05-07",
            "title": "AlphaCrafter: A Full-Stack Multi-Agent Framework for Cross-Sectional Quantitative Trading",
            "authors": 5,
            "official_pages": 26,
            "source_files": 25,
            "rebuilt_pages": 26,
            "result_units": sum(V1_RESULT_TABLES.values()),
            "empirical_panels": 16,
            "version_relationship": "original_submission",
        },
        {
            "version": "v2",
            "submitted": "2026-07-28",
            "title": "AlphaCrafter: Harnessing Multi-Agent Workflows for Cross-Sectional Quantitative Trading",
            "authors": 5,
            "official_pages": 22,
            "source_files": 22,
            "rebuilt_pages": "",
            "result_units": sum(V2_RESULT_TABLES.values()),
            "empirical_panels": 14,
            "version_relationship": "substantial_harness_reframing_and_result_revision",
        },
    ]


def internal_rows() -> list[dict[str, str]]:
    specs = (
        ("v1_to_v2_revision", "substantial", "title, framing, algorithm presentation, live window, result table, stability figures, and ablation change"),
        ("v1_full_model_cross_table", "conflicting_values", "main and ablation tables print different CSI MDD and S&P Sharpe for the Claude full model without released run lineage"),
        ("v2_full_model_cross_table", "consistent", "the six shared Claude full-model main/ablation values agree"),
        ("default_model_registry", "runtime_failure", "gpt-5.3-codex is requested but absent from models.json; launcher fails before any API call"),
        ("provider_generality", "paper_release_mismatch", "paper evaluates Claude and Gemini, but the release initializes only the OpenAI Responses client and tools describe OpenAI support"),
        ("us_end_to_end_path", "paper_release_mismatch", "U.S. components exist, but main always uses A-share instruction and default A-share trading tools"),
        ("released_data_coverage", "paper_release_mismatch", "schemas and index series are released, not the paper's stock/fundamental/news research corpus"),
        ("released_calendar_coverage", "paper_release_mismatch", "templates end March 31 although the revised live period ends June 12"),
        ("trial_reproducibility", "underspecified", "independent trials are stated without released seeds, requests, responses, or sampling controls"),
        ("live_execution_claim", "unverifiable_from_release", "no brokerage integration, order/fill records, or live NAV path is released"),
        ("v2_source_build", "toolchain_incompatible", "three bounded attempts stop or stall in TeX Live CJK encoding before output; source archive remains complete"),
        ("repository_attribution", "strong_but_not_direct", "NJU-LINK repository cites the exact paper and authors and matches the method, but the paper itself does not link it"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def release_audit(scratch: Path) -> dict[str, Any]:
    repo = scratch / "repo/NJU-LINK-AlphaCrafter-c6dbc1b"
    readme = (repo / "README.md").read_text(errors="replace")
    if ARXIV_ID not in readme or "AlphaCrafter" not in readme:
        raise ValueError("repository README no longer identifies the paper")
    if "MIT License" not in (repo / "LICENSE").read_text(errors="replace"):
        raise ValueError("repository license changed")
    config = (repo / "alphacrafter/config.yaml").read_text()
    models = json.loads((repo / "alphacrafter/sandbox/template_a/config/models.json").read_text())
    model_codes = sorted(models)
    if config.count('code: "gpt-5.3-codex"') != 3 or model_codes != ["gpt-5", "gpt-5.2"]:
        raise ValueError("default model mismatch evidence changed")
    main = (repo / "alphacrafter/main.py").read_text()
    if main.count("QUANTITATIVE_TRADING_INSTRUCTION_A +") != 3:
        raise ValueError("A-share-only instruction routing changed")
    components = json.loads((scratch / "native-component-checks.json").read_text())
    expected_true = (
        "a_share_buy_success", "a_share_sell_success",
        "a_share_t_plus_one_unlock_success", "us_short_success",
        "us_cover_success", "evaluation_metric_contract_success",
    )
    if not all(components[key] is True for key in expected_true):
        raise ValueError("native component evidence changed")
    if components["published_result_credit"] is not False:
        raise ValueError("component fixture incorrectly claims paper-result credit")
    ruff = json.loads((scratch / "native-ruff.json").read_text())
    if len(ruff) != 520:
        raise ValueError("Ruff diagnostic count changed")
    main_failure = (scratch / "native-main.txt").read_text()
    if "Model 'gpt-5.3-codex' not found" not in main_failure:
        raise ValueError("expected fail-before-API evidence changed")
    if "no tests ran in 0.06s" not in (scratch / "native-pytest.txt").read_text():
        raise ValueError("no-tests evidence changed")
    help_text = (scratch / "native-help.txt").read_text()
    if "Run quantitative trading workflow" not in help_text:
        raise ValueError("native CLI help evidence changed")
    return {
        "url": REPOSITORY_URL,
        "head_sha": REPOSITORY_HEAD,
        "archive_sha256": PINS["discovery/alphacrafter-c6dbc1b.zip"],
        "archive_files": 79,
        "archive_uncompressed_bytes": 889_614,
        "license": "MIT",
        "attribution": "author-organization repository with exact paper citation and matching authors/method; not directly linked from the paper",
        "python_files": 48,
        "editable_install_passed": True,
        "central_environment": "/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alphacrafter-py310-audit-20260812",
        "python_version": "3.10.8",
        "cli_help_passed": True,
        "bytecode_compilation_passed": True,
        "tracked_tests": 0,
        "pytest_outcome": "no tests collected (exit 5)",
        "ruff_diagnostics": 520,
        "ruff_role": "modern static/style diagnostic only; not paper-result evidence",
        "default_requested_model": "gpt-5.3-codex",
        "registered_models": model_codes,
        "full_launcher_reached_model_api": False,
        "full_launcher_failure": "default requested model is absent from the shipped model registry",
        "a_share_component_check": {key: components[key] for key in (
            "a_share_buy_success", "a_share_t_plus_one_unlock_success",
            "a_share_sell_success", "a_share_final_assets",
        )},
        "us_component_check": {key: components[key] for key in (
            "us_short_success", "us_cover_success", "us_final_assets",
        )},
        "metric_component_check": {key: components[key] for key in (
            "evaluation_metric_contract_success", "evaluation_total_return",
            "evaluation_max_drawdown",
        )},
        "component_fixture_uses_synthetic_data": True,
        "paper_stock_data_released": False,
        "paper_fundamental_statement_news_data_released": False,
        "paper_baseline_implementations_released": False,
        "paper_trial_outputs_released": False,
        "paper_brokerage_path_released": False,
        "published_table_or_figure_regenerated": False,
        "paper_result_credit": False,
    }


def readme() -> str:
    return """# AlphaCrafter paper and attributable-release audit

This audit treats arXiv `2605.05580` as a two-version lineage. Version 1 is the
26-page **Full-Stack Multi-Agent Framework** submission; version 2 is a substantial
22-page **Harnessing Multi-Agent Workflows** revision with changed framing,
algorithms, live window, results, figures, and ablations. The official v1 source
rebuilds to 26 visually sound pages. The complete v2 source is recovered, but the
available TeX Live toolchain repeatedly stalls in CJK encoding before producing a
PDF; that is recorded as a bounded toolchain incompatibility, not missing source.

The pinned 79-file MIT repository is strongly attributable: it belongs to the
authors' NJU-LINK organization, cites the exact arXiv paper and author list, and
matches the three-role architecture. The paper does not directly link it, so this
audit does not overstate the provenance. The source contains real miner, screener,
trader, data-tool, A-share exchange, U.S. exchange, and evaluation components.
Native controlled checks verify A-share buy/T+1/sell behavior, U.S. short/cover
behavior, the paper-stated 2-bp and 1-bp fees, and the return/drawdown metric
contract. These are component-conformance results on synthetic fixtures.

The checked-in full launcher is not operational as released: `config.yaml` asks
for `gpt-5.3-codex`, while every shipped `models.json` registers only `gpt-5` and
`gpt-5.2`; execution therefore fails before any API call. More fundamentally, the
paper evaluates GPT, Claude, and Gemini, while the runtime initializes only the
OpenAI Responses client. The launcher always injects the A-share instruction and
constructs its trading tools in their default A-share mode, so the released main
path does not select the paper's U.S. workflow even though U.S. components exist.

The release ships index series and empty/template schemas, not the paper's stock,
fundamental, statement, or news corpus. Its calendars end on 2026-03-31, before
the revised live period ends on 2026-06-12. Baseline implementations, point-in-time
memberships, model requests/responses, trial seeds, factor pools, actions, orders,
fills, brokerage integration, NAV/return arrays, and table/figure generators are
absent. There are no tracked tests; compilation and CLI help pass, while Ruff's
520 findings are recorded only as a modern static diagnostic.

Accordingly, the honest paper-level score is **0/176 v1 and 0/304 v2 published
numeric result units, and 0/16 v1 and 0/14 v2 empirical panels regenerated**.
The native component checks materially improve implementation faithfulness, but
no source rebuild, synthetic fixture, or local narrative proxy receives paper-result
credit. The older `alphacrafter_full_stack_multifactor` portfolio remains a clearly
labeled secondary motif translation, not an AlphaCrafter replication.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inventory = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    v1_results = result_rows("v1", V1_RESULT_TABLES)
    v2_results = result_rows("v2", V2_RESULT_TABLES)
    figures = figure_rows()
    write_csv(output / "version_revision_audit.csv", version_rows())
    write_csv(output / "published_result_ledger_v1.csv", v1_results)
    write_csv(output / "published_result_ledger_v2.csv", v2_results)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "internal_consistency_audit.csv", internal_rows())
    release = release_audit(scratch)
    write_json(output / "release_execution_audit.json", release)
    provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv": {
            "id": ARXIV_ID,
            "versions": ["v1", "v2"],
            "pdf_sha256": {"v1": PINS["primary/arxiv-v1.pdf"], "v2": PINS["primary/arxiv-v2.pdf"]},
            "source_sha256": {"v1": PINS["source/arxiv-v1.tar"], "v2": PINS["source/arxiv-v2.tar"]},
            "visual_qa": {
                "official_pages_inspected": {"v1": 26, "v2": 22},
                "rebuilt_pages_inspected": {"v1": 26, "v2": 0},
                "unreadable_clipped_or_overlapping_pages": 0,
                "contact_sheet_sha256": {
                    "v1_official": PINS["viz/v1-official-contact.jpg"],
                    "v2_official": PINS["viz/v2-official-contact.jpg"],
                    "v1_rebuilt": PINS["viz/v1-rebuilt-contact.jpg"],
                },
            },
            "v2_build_boundary": "complete source; three bounded attempts stalled/interrupted in TeX Live CJK encoding before output",
        },
        "attributable_repository": release,
        "release_boundary": {
            "attribution_strength": "author_organization_exact_citation_and_architecture_match_not_direct_paper_link",
            "runtime_source_recovered": True,
            "component_execution_completed": True,
            "default_end_to_end_launcher_operational": False,
            "complete_research_data_recovered": False,
            "multibackbone_runtime_recovered": False,
            "published_result_lineage_recovered": False,
        },
    }
    write_json(output / "source_provenance.json", provenance)
    (output / "README.md").write_text(readme(), encoding="utf-8")
    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_versions_audited": ["v1", "v2"],
        "v2_substantial_revision": True,
        "official_pdf_and_source_recovered": True,
        "v1_document_rebuild_completed": True,
        "v2_document_rebuild_completed": False,
        "v2_rebuild_blocker": "available TeX Live CJK encoding stall",
        "official_pages_visually_checked": 48,
        "rebuilt_pages_visually_checked": 26,
        "v1_source_files": inventory["v1_source_files"],
        "v2_source_files": inventory["v2_source_files"],
        "v1_published_numeric_result_units": len(v1_results),
        "v2_published_numeric_result_units": len(v2_results),
        "v1_native_numeric_units_regenerated": 0,
        "v2_native_numeric_units_regenerated": 0,
        "v1_empirical_panels": sum(row["empirical_series_or_panels"] for row in figures if row["version"] == "v1"),
        "v2_empirical_panels": sum(row["empirical_series_or_panels"] for row in figures if row["version"] == "v2"),
        "native_empirical_panels_regenerated": 0,
        "attributable_repository_recovered": True,
        "repository_files": inventory["release_files"],
        "native_component_checks_passed": 6,
        "full_launcher_operational_as_released": False,
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
    }
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output.iterdir())
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
