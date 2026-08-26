#!/usr/bin/env python3
"""Build a fail-closed version/source/release audit for MM-DREX / MM-ARC."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/mm_arc_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/mm_arc"
WORK_ID = "CensusArxiv250905080"
SYSTEM_ID = "SYS-MM-DREX"
ARXIV_ID = "2509.05080"
REPOSITORY_URL = "https://anonymous.4open.science/r/MM-ARC-32F7/"
LATEST_ARCHIVE = "discovery/MM-ARC-32F7-20260814.zip"
LATEST_REPO = "repo-20260814"
TOKENIZER_OID = "be75606093db2094d7cd20f3c2f385c212750648bd6ea4fb2bf507a6a4c55506"
TOKENIZER_BYTES = 11_422_650
TOKENIZER_SOURCE_REPOSITORY = (
    "zijiandongkurt/AI-Driven-Modular-Power-Electronics-Design-for-Next-Gen-Lithography"
)
TOKENIZER_SOURCE_COMMIT = "1c53940c0e8e19be895cf9e4025f9cb3b320e529"
TOKENIZER_SOURCE_PATH = "checkpoints/sft/sft_001/final/tokenizer.json"
LFS_POINTER_RE = re.compile(
    rb"\Aversion https://git-lfs\.github\.com/spec/v1\n"
    rb"oid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n\Z"
)

PINS = {
    "primary/arxiv-abs.html": "f4c90246ccfb9211dd1eb162146fa596e1f76e4121f4949135fef678fea09124",
    "primary/arxiv-api.xml": "b0fe61fbf6777214b8bc5c428de76f4434dfe59d0df8be51f1b381bf67239abc",
    "primary/arxiv-v1.pdf": "7edd0cb12388b8a8b7ab9b3a724b09066024033ca01a1b4c5bf98c24da2919f9",
    "primary/arxiv-v2.pdf": "f7c3865b8af0cd0cea629bdeff7901fdc467830b3aa3b24f3f614465a777c646",
    "primary/arxiv.pdf": "91aae07101aafcbb10e757cea1a2e63b55068d0467923ed6ab40daed9e73072c",
    "source/arxiv-v1.tar": "6f7a8d462c32557bfdedd6b43d54dd858c1bd3e014dba8d0091e21704cc4aeb7",
    "source/arxiv-v2.tar": "47a16ea47d73e92a200b5011c0d0b789ae5cc61defd3d52b940c221f22213a67",
    "source/arxiv.tar": "4ca6dcfcd9dce3419b2c00b967406c423b5a337dcecebf117a73f0655684945c",
    "build-v1/main.pdf": "0af4da79988fdecb7122526a0d468c2156a64790795fed76a1fb719d3e4701db",
    "build-v2/main.pdf": "16cb544f3e6b1b601c98dbcd6b667eb09890a6eaec1ba057b9b2d2504b4269dc",
    "build/main.pdf": "03b810f6edbd9aa776471c0f8f765b0831177a3e4fb4a8cce2672a6b1fe4c8f4",
    "discovery/MM-ARC-32F7.zip": "b0e647858678b06aaeeddb3cebcc6ee29af76d44877fc7d611c2a957f281098d",
    LATEST_ARCHIVE: "830e4257125e67f4f9c64c9ae2a446b02593f83b94bd81b19aae225f5014f317",
    "discovery/official-options-20260814.json": "d127e6b491e90ee97df601a25dfcd5e8c15c7a54c33d861af00bbac224eee308",
    "discovery/official-files-labo_evaluator_adapter-20260814.json": "fe83c316daecc5d25f926e654c080ba7ea626b55938734b8109f203c41d0f90e",
    "discovery/official-files-labo_generator_adapter-20260814.json": "4db4105879962c8b9150c7047a9673989426f9cf12a02af28eb3860c943fb334",
    "discovery/official-files-qwen_regime_adapter-20260814.json": "933376132eac74b9c6f60f7b083a9c1efe37c03f274294192f93bd15e907cf26",
    "discovery/official-files-rl_router_seed42-20260814.json": "8f2e2dd9bbcfcb8dfb0cda0b40badf54f703896779e19672286a93344177f44b",
    "discovery/official-files-strategy_pool-20260814.json": "9281873da0aff6dc096115b09480290053ea6cba55ffddb4d1aba2cf91a6df39",
    "discovery/tokenizer-source-github-20260814.json": "60868cc9877ee1c094505a731cfd6d54344873be659a01a6675baa93c052892d",
    f"recovered_lfs/{TOKENIZER_OID}": TOKENIZER_OID,
    "tokenizer-runtime-20260814.json": "87217e774cb93d4affcadcb2491375acae91d11cbd44511095b43955dbda5780",
    "native-pytest-python-m-20260814.xml": "5fcd0f466c0eb3997a0f773382cbad78a51c5142982c5dce2f1fbc72bcb966e3",
    "native-ruff-20260814.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "native-pytest.xml": "b90d330c409a39bc8f56b5fe0ab86a6164c3170253d783111a375899db2dffdb",
    "native-pytest-python-m.xml": "482613687bd83d2356ed750dc79fee155dbf3cdb0f4244f7dc7dc3bd501fbf2c",
    "native-ruff.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "artifact-verification.txt": "4a6f5ab963c39a6e465711d784183e3bf8586338838daf03387901b876933313",
}

OFFICIAL_LFS_PROBE_PATHS = (
    "models/labo_evaluator_adapter/adapter_model.safetensors",
    "models/labo_evaluator_adapter/tokenizer.json",
    "models/labo_generator_adapter/adapter_model.safetensors",
    "models/labo_generator_adapter/tokenizer.json",
    "models/qwen_regime_adapter/adapter_model.safetensors",
    "models/qwen_regime_adapter/tokenizer.json",
    "models/rl_router_seed42/best_model.pt",
    "strategy_pool/strict_rabo_sealed_rabo_robustness.csv",
    "strategy_pool/strict_rabo_sealed_strategy_signals.csv",
)
GLOBAL_LFS_CODE_SEARCHES = (
    ("oid_3b15057d.json", "oid_sha256", "3b15057d0e35dd46b53ee4908a666d22cb895970d78b1a81ab6fc42a03013ee7"),
    ("oid_125629f1.json", "oid_sha256", "125629f100aec4277a89251e081fca7e78191f6f818566bfc1b9f5e393f15697"),
    ("oid_44fc4462.json", "oid_sha256", "44fc4462b52592b23378e97e2fd48d451c61fcbcd7d0c0db36be14093a8f7f1c"),
    ("oid_4a34b844.json", "oid_sha256", "4a34b844a21c6122444ff6b9d9fb980182e28eb6a7efd5d90b41ae9168154b92"),
    ("oid_e363735b.json", "oid_sha256", "e363735b6ac8833ef45a69564a270746ca660e78cdab17acd00f20f7220669f8"),
    ("oid_71873cdf.json", "oid_sha256", "71873cdffe2e04404cc5e91c731ced28c741e2fab7e06c36510c0820184d3da7"),
    ("name_strategy_signals.json", "distinctive_path", "strict_rabo_sealed_strategy_signals.csv"),
    ("name_rabo_robustness.json", "distinctive_path", "strict_rabo_sealed_rabo_robustness.csv"),
    ("name_labo_evaluator.json", "distinctive_directory", "labo_evaluator_adapter"),
    ("name_qwen_regime.json", "distinctive_directory", "qwen_regime_adapter"),
)
for _relative in OFFICIAL_LFS_PROBE_PATHS:
    _name = _relative.replace("/", "_")
    PINS[f"discovery/official-lfs-{_name}-20260814.json"] = (
        "ad8e0238bdf46cf71cf2f7e519a1e601e863bff47973b0d31f7623f14d319b72"
    )
for _filename, _, _ in GLOBAL_LFS_CODE_SEARCHES:
    PINS[f"discovery/global_search_20260826/{_filename}"] = (
        "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f"
    )

V1_RESULT_TABLES = {
    "tab:comprehensive_results": 240,
    "tab:routing_comparison": 12,
    "tab:modality_ablation": 12,
    "tab:crisis_performance": 12,
    "tab:llm_overall_results": 60,
    "tab:llm_temporal_summary": 96,
    "tab:llm_30day_analysis": 55,
    "tab:llm_100day_analysis": 96,
    "tab:llm_250day_analysis": 88,
}

V3_RESULT_TABLES = {
    "tab:main_results": 42,
    "tab:statistical_summary": 38,
    "tab:combined_ablation": 76,
    "tab:shared_pool_difference": 12,
    "tab:resource_results": 18,
    "tab:dfrabo": 36,
    "tab:market_specific_costs": 41,
    "tab:per_seed_results": 105,
    "tab:seed_stability_statistics": 39,
    "tab:block_length_sensitivity": 72,
    "tab:per_market_audit": 60,
    "tab:regime_coverage": 30,
    "tab:numeric_integrity": 4,
    "tab:residual_diagnostics": 28,
    "tab:rabo_controls_appendix": 50,
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
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def safe_archives(scratch: Path) -> None:
    for relative in ("source/arxiv-v1.tar", "source/arxiv-v2.tar", "source/arxiv.tar"):
        with tarfile.open(scratch / relative, "r:*") as archive:
            for member in archive.getmembers():
                pure = PurePosixPath(member.name)
                if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                    raise ValueError(f"unsafe archive member: {relative}:{member.name}")
    for relative in ("discovery/MM-ARC-32F7.zip", LATEST_ARCHIVE):
        with zipfile.ZipFile(scratch / relative) as archive:
            for member in archive.infolist():
                pure = PurePosixPath(member.filename)
                mode = member.external_attr >> 16
                if pure.is_absolute() or ".." in pure.parts or (mode & 0o170000) == 0o120000:
                    raise ValueError(f"unsafe repository archive member: {relative}:{member.filename}")


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    safe_archives(scratch)
    v1_tex = (scratch / "build-v1/main.tex").read_bytes()
    v2_tex = (scratch / "build-v2/main.tex").read_bytes()
    if v1_tex != v2_tex:
        raise ValueError("v1 and v2 manuscript TeX are no longer byte-identical")
    if hashlib.sha256(v1_tex).hexdigest() != "095c9f765b4e47bc089eafd0d05c35a32fbef63e9c098b2b78520e75687b17d8":
        raise ValueError("legacy manuscript source changed")
    v3 = (scratch / "build/main.tex").read_text(errors="replace")
    for marker in ("MM-ARC", "Qwen3-VL-8B-Instruct", "anonymous.4open.science/r/MM-ARC-32F7"):
        combined = v3 + (scratch / "build/appendix.tex").read_text(errors="replace")
        if marker not in combined:
            raise ValueError(f"current manuscript marker changed: {marker}")
    legacy = v1_tex.decode(errors="replace")
    for marker in ("MM-DREX", "Qwen\\,2.5", "first 60\\% of data allocated for training"):
        if marker not in legacy:
            raise ValueError(f"legacy manuscript marker changed: {marker}")
    with zipfile.ZipFile(scratch / "discovery/MM-ARC-32F7.zip") as archive:
        old_payloads = {item.filename: archive.read(item.filename) for item in archive.infolist()}
    with zipfile.ZipFile(scratch / LATEST_ARCHIVE) as archive:
        new_payloads = {item.filename: archive.read(item.filename) for item in archive.infolist()}
    if len(old_payloads) != 107 or sum(map(len, old_payloads.values())) != 2_596_204:
        raise ValueError("2026-08-12 official repository archive inventory changed")
    if len(new_payloads) != 107 or sum(map(len, new_payloads.values())) != 2_595_188:
        raise ValueError("2026-08-14 official repository archive inventory changed")
    if set(old_payloads) != set(new_payloads):
        raise ValueError("official repository refresh changed the path inventory")
    changed = sorted(path for path in old_payloads if old_payloads[path] != new_payloads[path])
    if changed != ["DATA_CARD.md", "MODEL_CARD.md"]:
        raise ValueError(f"unexpected 2026-08-14 release changes: {changed}")
    latest_repo = scratch / LATEST_REPO
    for relative, payload in new_payloads.items():
        if (latest_repo / relative).read_bytes() != payload:
            raise ValueError(f"latest extracted repository differs from archive: {relative}")
    options = json.loads((scratch / "discovery/official-options-20260814.json").read_text())
    if options.get("lastUpdateDate") != "2026-08-14T04:49:09.000Z":
        raise ValueError("official repository refresh timestamp changed")
    listed: dict[str, dict[str, Any]] = {}
    for relative in (
        "discovery/official-files-labo_evaluator_adapter-20260814.json",
        "discovery/official-files-labo_generator_adapter-20260814.json",
        "discovery/official-files-qwen_regime_adapter-20260814.json",
        "discovery/official-files-rl_router_seed42-20260814.json",
        "discovery/official-files-strategy_pool-20260814.json",
    ):
        for item in json.loads((scratch / relative).read_text()):
            path = f"{item['path']}/{item['name']}".removeprefix("artifacts/")
            listed[path] = item
    if any(listed[path]["size"] != 133 for path in OFFICIAL_LFS_PROBE_PATHS):
        raise ValueError("official public file listing no longer exposes all LFS pointers")
    for relative in OFFICIAL_LFS_PROBE_PATHS:
        name = relative.replace("/", "_")
        body = json.loads(
            (scratch / f"discovery/official-lfs-{name}-20260814.json").read_text()
        )
        if body != {"error": "file_not_found"}:
            raise ValueError(f"official LFS endpoint outcome changed: {relative}")
    source = json.loads(
        (scratch / "discovery/tokenizer-source-github-20260814.json").read_text()
    )
    if (
        source.get("path") != TOKENIZER_SOURCE_PATH
        or source.get("sha") != "c7afbed2efcdf019f88ab0572ec29d3bf595dfe2"
        or source.get("size") != TOKENIZER_BYTES
    ):
        raise ValueError("independent tokenizer source metadata changed")
    runtime = json.loads((scratch / "tokenizer-runtime-20260814.json").read_text())
    if (
        runtime.get("payload_sha256") != TOKENIZER_OID
        or runtime.get("transformers") != "5.11.0"
        or runtime.get("tokenizers") != "0.22.2"
        or runtime.get("protobuf") != "7.35.0"
        or len(runtime.get("adapters", [])) != 3
        or not all(item.get("decoded_round_trip_exact") for item in runtime["adapters"])
    ):
        raise ValueError("tokenizer runtime evidence changed")
    return {
        "legacy_source_files": 16,
        "current_source_files": 30,
        "release_files": 107,
        "release_refresh_changed_files": changed,
        "release_unchanged_files": 105,
    }


def result_rows(version: str, specifications: Mapping[str, int]) -> list[dict[str, Any]]:
    rows = []
    for table, count in specifications.items():
        for index in range(1, count + 1):
            rows.append({
                "version": version,
                "table_label": table,
                "printed_numeric_unit": index,
                "source_document_recovered": True,
                "author_native_experiment_executed": False,
                "published_result_regenerated": False,
                "paper_result_credit": False,
                "blocking_reason": (
                    "legacy experiment code, data, checkpoints, prompts, and raw results were not released"
                    if version == "v1_v2"
                    else "full benchmark data, training/controller history, five trained seeds, and result arrays were not released"
                ),
            })
    return rows


def method_rows() -> list[dict[str, Any]]:
    specifications = (
        ("v1_v2", "official_document_source", "complete_document_only", "16-file source packages recovered; v1/v2 TeX is byte-identical"),
        ("v1_v2", "author_native_runtime", "missing", "the v3 release is a different method and does not implement the legacy experiment"),
        ("v1_v2", "market_data", "missing", "sources are named but the research corpus is not released"),
        ("v1_v2", "qwen_backbone", "specified_not_released", "Qwen2.5-VL-72B and LoRA settings are printed; weights and training records are absent"),
        ("v1_v2", "sft_rl_training", "underspecified_unreleased", "a 60/20/20 temporal split and seed 42 are printed; examples, labels, code, and checkpoints are absent"),
        ("v1_v2", "baseline_implementations", "missing", "15 named baselines have no released implementations or lineage"),
        ("v1_v2", "trading_costs", "absent", "the paper's future-work section says transaction costs and liquidity remain future work"),
        ("v1_v2", "raw_results", "missing", "no return arrays, prediction files, or experiment ledger is released"),
        ("v3", "official_document_source", "complete_document_only", "30-file source package recovered and rebuilt"),
        ("v3", "official_repository", "substantial_release", "107-file Apache-2.0 anonymous release linked directly from the paper"),
        ("v3", "official_repository_refresh", "two_document_files_changed", "the 2026-08-14 public refresh changes only DATA_CARD.md and MODEL_CARD.md; all 105 code/artifact files remain byte-identical"),
        ("v3", "universe_and_execution_contract", "released", "62-asset universe, per-market rules, and a 7,440-row acceptance replay are released"),
        ("v3", "strategy_pools", "mostly_released", "60 pools and 300 members are present; two large signal/robustness tables are LFS pointers"),
        ("v3", "qwen_and_router_artifacts", "tokenizers_recovered_weights_unavailable", "one exact generic tokenizer OID, repeated in three adapter directories, is independently recoverable; three trained adapters and the seed-42 router remain 133-byte LFS pointers"),
        ("v3", "full_benchmark_market_data", "missing", "the data card explicitly limits the release to a 120-observation acceptance fixture"),
        ("v3", "training_and_experiment_controller", "missing", "the model card explicitly places the full private history outside the release"),
        ("v3", "five_seed_training", "partial_one_seed_only", "the paper reports seeds 42--46; the release registers only seed 42"),
        ("v3", "result_arrays_and_report_generator", "missing", "the paper claims report generation but no published-table lineage arrays or table generator are present"),
        ("v3", "unit_integration_acceptance_tests", "executed", "111/111 pass with python -m pytest; tests use doubles and do not reproduce paper metrics"),
        ("v3", "artifact_integrity", "partial_exact_public_recovery", "26/35 files verify from the official archive; exact independent tokenizer recovery raises this to 29/35, while six paper-specific payloads still fail closed before model execution"),
        ("v3", "published_results", "not_regenerated", "zero published numeric table units and zero empirical figures were regenerated"),
    )
    return [
        {"version": version, "dimension": dimension, "status": status, "detail": detail}
        for version, dimension, status, detail in specifications
    ]


def release_snapshot_rows() -> list[dict[str, Any]]:
    return [
        {
            "observed_at_utc": "2026-08-12T23:18:45+00:00",
            "archive_sha256": PINS["discovery/MM-ARC-32F7.zip"],
            "archive_bytes": 1_122_274,
            "uncompressed_bytes": 2_596_204,
            "files": 107,
            "changed_from_previous": "initial_pinned_snapshot",
            "changed_paths": "",
            "code_or_artifact_paths_changed": False,
            "lfs_pointer_files": 9,
            "note": "first recovered official bulk archive",
        },
        {
            "observed_at_utc": "2026-08-14T21:45:30+00:00",
            "archive_sha256": PINS[LATEST_ARCHIVE],
            "archive_bytes": 1_121_831,
            "uncompressed_bytes": 2_595_188,
            "files": 107,
            "changed_from_previous": "2_of_107_files",
            "changed_paths": "DATA_CARD.md;MODEL_CARD.md",
            "code_or_artifact_paths_changed": False,
            "lfs_pointer_files": 9,
            "note": "latest public refresh removes two Limitations sections; equivalent benchmark/private-history boundaries remain elsewhere",
        },
    ]


def lfs_recovery_rows(scratch: Path, pointer_inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runtime = json.loads((scratch / "tokenizer-runtime-20260814.json").read_text())
    recovered_payload = scratch / f"recovered_lfs/{TOKENIZER_OID}"
    rows = []
    for item in pointer_inventory:
        pointer = (scratch / LATEST_REPO / "artifacts" / item["path"]).read_bytes()
        match = LFS_POINTER_RE.fullmatch(pointer)
        if match is None:
            raise ValueError(f"not a canonical LFS pointer: {item['path']}")
        oid = match.group(1).decode()
        pointer_bytes = int(match.group(2))
        if oid != item["expected_sha256"] or pointer_bytes != item["expected_bytes"]:
            raise ValueError(f"LFS pointer disagrees with registry: {item['path']}")
        recovered = oid == TOKENIZER_OID
        if recovered and (
            recovered_payload.stat().st_size != TOKENIZER_BYTES
            or sha256(recovered_payload) != TOKENIZER_OID
        ):
            raise ValueError("recovered tokenizer payload no longer matches its content address")
        rows.append({
            "path": item["path"],
            "oid_sha256": oid,
            "registered_bytes": pointer_bytes,
            "official_archive_observed_bytes": len(pointer),
            "official_public_file_endpoint": "404_file_not_found_2026-08-14",
            "exact_public_payload_recovered": recovered,
            "recovery_source_repository": TOKENIZER_SOURCE_REPOSITORY if recovered else "",
            "recovery_source_commit": TOKENIZER_SOURCE_COMMIT if recovered else "",
            "recovery_source_path": TOKENIZER_SOURCE_PATH if recovered else "",
            "payload_size_and_sha256_verified": recovered,
            "registry_verification_after_hydration": recovered,
            "declared_runtime_loaded": recovered,
            "declared_runtime": (
                f"Transformers {runtime['transformers']}; Tokenizers {runtime['tokenizers']}; "
                f"Protobuf {runtime['protobuf']}" if recovered else ""
            ),
            "author_attributable_recovery": False,
            "native_model_or_strategy_execution_enabled": False,
            "paper_result_credit": False,
            "boundary": (
                "byte-identical generic tokenizer recovered from an independent public GitHub blob; no MM-ARC author lineage"
                if recovered
                else "paper-specific trained or historical payload remains unavailable from the official endpoint and public exact-hash searches"
            ),
        })
    if len({row["oid_sha256"] for row in rows}) != 7:
        raise ValueError("expected seven unique LFS content addresses")
    if sum(row["exact_public_payload_recovered"] for row in rows) != 3:
        raise ValueError("expected one tokenizer OID repeated across three recovered paths")
    return rows


def global_lfs_search_rows(
    scratch: Path,
    pointer_inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    remaining_oids = {
        row["expected_sha256"]
        for row in pointer_inventory
        if row["expected_sha256"] != TOKENIZER_OID
    }
    queried_oids = {
        query
        for _, query_type, query in GLOBAL_LFS_CODE_SEARCHES
        if query_type == "oid_sha256"
    }
    if remaining_oids != queried_oids:
        raise ValueError("MM-ARC global LFS OID search coverage changed")
    rows: list[dict[str, Any]] = []
    for filename, query_type, query in GLOBAL_LFS_CODE_SEARCHES:
        payload = json.loads(
            (
                scratch
                / "discovery/global_search_20260826"
                / filename
            ).read_text()
        )
        if (
            payload.get("total_count") != 0
            or payload.get("incomplete_results") is not False
            or payload.get("items") != []
        ):
            raise ValueError(f"MM-ARC exact public code search changed: {filename}")
        rows.append(
            {
                "query_type": query_type,
                "query": query,
                "service": "GitHub authenticated global code search",
                "checked_at_utc": "2026-08-26T16:52:00Z",
                "total_count": 0,
                "incomplete_results": False,
                "public_payload_or_pointer_hit": False,
                "native_model_or_strategy_execution_enabled": False,
                "paper_result_credit": False,
                "boundary": (
                    "bounded exact-hash/name search found no indexed public recovery; "
                    "private, deleted, unindexed, or non-GitHub copies remain possible"
                ),
            }
        )
    if len(rows) != 10:
        raise ValueError("MM-ARC global LFS search inventory changed")
    return rows


def release_audit(scratch: Path) -> dict[str, Any]:
    repo = scratch / LATEST_REPO
    registry = json.loads((repo / "artifacts/registry.json").read_text())
    good, bad = [], []
    for item in registry["artifacts"]:
        path = repo / "artifacts" / item["path"]
        actual_size = path.stat().st_size
        actual_sha = sha256(path)
        row = {
            "path": item["path"],
            "expected_bytes": item["bytes"],
            "expected_sha256": item["sha256"],
            "observed_bytes": actual_size,
            "observed_sha256": actual_sha,
        }
        if actual_size == item["bytes"] and actual_sha == item["sha256"]:
            good.append(row)
        else:
            bad.append(row)
    if len(good) != 26 or len(bad) != 9 or sum(row["expected_bytes"] for row in bad) != 340_563_208:
        raise ValueError("release LFS boundary changed")
    recovery = lfs_recovery_rows(scratch, bad)
    junit = ET.parse(scratch / "native-pytest-python-m-20260814.xml").getroot().find("testsuite")
    direct = ET.parse(scratch / "native-pytest.xml").getroot().find("testsuite")
    if junit is None or direct is None:
        raise ValueError("pytest evidence has no suite")
    if (junit.get("tests"), junit.get("errors"), junit.get("failures")) != ("111", "0", "0"):
        raise ValueError("CI-style test evidence changed")
    if (direct.get("tests"), direct.get("errors")) != ("2", "2"):
        raise ValueError("direct pytest entry-point boundary changed")
    if json.loads((scratch / "native-ruff-20260814.json").read_text()) != []:
        raise ValueError("Ruff evidence is not clean")
    verification = (scratch / "artifact-verification.txt").read_text()
    if "expected=87368144, observed=133" not in verification:
        raise ValueError("artifact fail-closed evidence changed")
    return {
        "url": REPOSITORY_URL,
        "archive_sha256": PINS[LATEST_ARCHIVE],
        "previous_archive_sha256": PINS["discovery/MM-ARC-32F7.zip"],
        "archive_observed_at_utc": "2026-08-14T21:45:30+00:00",
        "official_last_update_at_utc": "2026-08-14T04:49:09.000Z",
        "archive_snapshot_count": 2,
        "archive_refresh_changed_files": ["DATA_CARD.md", "MODEL_CARD.md"],
        "archive_refresh_unchanged_code_and_artifact_files": 105,
        "archive_files": 107,
        "archive_bytes": 1_121_831,
        "archive_uncompressed_bytes": 2_595_188,
        "license": "Apache-2.0",
        "release_version": "v0.1.0",
        "artifact_registry_version": registry["version"],
        "registered_artifacts": len(registry["artifacts"]),
        "registered_artifact_bytes": sum(item["bytes"] for item in registry["artifacts"]),
        "verified_payload_files": len(good),
        "verified_payload_bytes": sum(row["expected_bytes"] for row in good),
        "lfs_pointer_files": len(bad),
        "lfs_payload_bytes_unavailable": sum(row["expected_bytes"] for row in bad),
        "lfs_pointer_inventory": bad,
        "unique_lfs_oids": len({row["oid_sha256"] for row in recovery}),
        "official_public_lfs_endpoint_file_not_found": len(recovery),
        "exact_public_payload_unique_oids_recovered": len({
            row["oid_sha256"] for row in recovery if row["exact_public_payload_recovered"]
        }),
        "exact_public_payload_registered_paths_recovered": sum(
            row["exact_public_payload_recovered"] for row in recovery
        ),
        "exact_public_payload_unique_bytes_recovered": TOKENIZER_BYTES,
        "exact_public_payload_registered_bytes_recovered": 3 * TOKENIZER_BYTES,
        "verified_payload_files_after_exact_public_recovery": len(good) + 3,
        "verified_payload_bytes_after_exact_public_recovery": (
            sum(row["expected_bytes"] for row in good) + 3 * TOKENIZER_BYTES
        ),
        "remaining_unavailable_pointer_files": len(bad) - 3,
        "remaining_unavailable_unique_oids": 6,
        "remaining_unavailable_registered_bytes": (
            sum(row["expected_bytes"] for row in bad) - 3 * TOKENIZER_BYTES
        ),
        "tokenizer_recovery_source_attributable_to_mm_arc_authors": False,
        "tokenizer_runtime_validation": json.loads(
            (scratch / "tokenizer-runtime-20260814.json").read_text()
        ),
        "base_model_id": registry["base_model"]["model_id"],
        "base_model_revision": registry["base_model"]["revision"],
        "base_model_registered_bytes": sum(item["bytes"] for item in registry["base_model"]["files"]),
        "test_command": "python -m pytest -q",
        "tests_passed": 111,
        "ruff_clean": True,
        "bytecode_compilation_passed": True,
        "direct_pytest_console_script_errors": 2,
        "direct_pytest_boundary": "console-script entry point cannot import repository scripts package; python -m pytest matches released CI",
        "tests_download_lfs": False,
        "tests_use_model_runtime_doubles": True,
        "artifact_verification_passed": False,
        "artifact_verification_failure": "after exact tokenizer hydration, three trained adapters, the router, and two historical strategy tables remain 133-byte LFS pointers",
        "full_model_forward_executed_in_audit": False,
        "paper_decision_cycle_executed_in_audit": False,
        "published_table_or_figure_regenerated": False,
        "paper_result_credit": False,
    }


def figure_rows() -> list[dict[str, Any]]:
    specs = (
        ("v1_v2", "fig:4-1", 1, "dataset-comparison radar"),
        ("v1_v2", "fig:performance_comparison", 3, "three NAV/stress-event curves"),
        ("v1_v2", "verified_vendor_asset_heatmap.png", 1, "model/asset accuracy heatmap"),
        ("v1_v2", "copper_window_curves", 3, "30/100/250-day forecasting plots"),
        ("v1_v2", "fig:performance_comparison2", 3, "three additional NAV/stress-event curves"),
        ("v3", "fig:mechanism_a", 2, "BO-best and full-RABO empirical CDFs"),
        ("v3", "fig:mechanism_b", 1, "3x4 average-capital-weight heatmap"),
        ("v3", "fig:cost_sensitivity_appendix", 4, "two methods across return and Sharpe panels"),
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
            "version": "v1", "submitted": "2025-09-05", "title": "MM-DREX: Multimodal-Driven Dynamic Routing of LLM Experts for Financial Trading",
            "authors": 9, "official_pages": 32, "source_files": 16, "rebuilt_pages": 30,
            "method_family": "Qwen2.5-VL-72B SFT-RL dynamic routing", "result_units": sum(V1_RESULT_TABLES.values()),
            "version_relationship": "legacy_original",
        },
        {
            "version": "v2", "submitted": "2025-09-10", "title": "MM-DREX: Multimodal-Driven Dynamic Routing of LLM Experts for Financial Trading",
            "authors": 9, "official_pages": 32, "source_files": 16, "rebuilt_pages": 32,
            "method_family": "Qwen2.5-VL-72B SFT-RL dynamic routing", "result_units": sum(V1_RESULT_TABLES.values()),
            "version_relationship": "source-identical_to_v1_except_arxiv_metadata_and_packaged_bibliography",
        },
        {
            "version": "v3", "submitted": "2026-07-27", "title": "MM-ARC: Multimodal Adaptive Routing of Capital with Robustness-Audited Strategy Pools",
            "authors": 10, "official_pages": 17, "source_files": 30, "rebuilt_pages": 16,
            "method_family": "Qwen3-VL-8B adapters, actor-critic router, RABO pools", "result_units": sum(V3_RESULT_TABLES.values()),
            "version_relationship": "wholesale_replacement_not_a_minor_revision",
        },
    ]


def internal_rows() -> list[dict[str, str]]:
    specs = (
        ("v1_v2_version_identity", "source_identical", "v1/v2 main.tex is byte-identical; v2 changes the arXiv stamp/packaged bibliography"),
        ("v2_to_v3_method_identity", "wholesale_replacement", "title, authors, backbone, method, dates, baselines, metrics, tables, figures, and results change"),
        ("v1_transaction_cost_scope", "explicit_future_work", "legacy results do not include the v3 normalized after-cost protocol"),
        ("v3_repository_claim", "partially_supported", "substantial pipeline is released, but the full benchmark/controller/result lineage is not"),
        ("v3_five_seed_claim", "release_incomplete", "paper reports five independently trained seeds; release contains only seed 42"),
        ("v3_complete_artifact_claim", "retrieved_archive_incomplete", "9 registered payloads are only LFS pointers"),
        ("v3_public_refresh", "two_document_only_changes", "the 2026-08-14 refresh changes DATA_CARD.md and MODEL_CARD.md only; 105 code/artifact files remain byte-identical"),
        ("v3_tokenizer_recovery", "exact_bytes_unattributable", "one generic tokenizer OID repeated across three paths is byte-exactly recoverable from an independent public GitHub blob; it is not MM-ARC author-output lineage"),
        ("v3_test_claim", "verified_with_boundary", "111 tests pass using python -m pytest without LFS/model execution"),
        ("v3_result_reconciliation_claim", "not_independently_verifiable", "no published-result arrays or table-generation path are released"),
        ("v3_acceptance_replay_scope", "correctly_disclaimed", "data/model cards state that the replay is not full benchmark reproduction"),
        ("v3_paper_source_build", "completed_with_layout_difference", "official source builds to 16 pages versus the 17-page arXiv rendering"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def readme() -> str:
    return """# MM-DREX / MM-ARC paper and release audit

This audit treats arXiv `2509.05080` as a versioned lineage, not a single stable
paper. Versions 1 and 2 are the legacy 32-page **MM-DREX** manuscript; their
`main.tex` files are byte-identical. Version 3 is a wholesale 17-page replacement
named **MM-ARC**, with a different backbone, method, experiment period, baseline
set, statistical protocol, author list, results, and official anonymous release.

The v3 release is substantial: 107 files, 19 pipeline modules, 60 pools, 300
active members, a 62-instrument universe, a 7,440-row acceptance replay, tests,
deployment contracts, and a content-addressed artifact registry. In the pinned
Python 3.12 environment, Ruff and compilation pass and the release's CI-style
`python -m pytest -q` command passes all 111 tests. These are real code-contract
results, not paper-result reproductions: CI checks out with LFS disabled and the
model-facing tests use doubles.

Two official snapshots are pinned. The 2026-08-14 refresh changes only
`DATA_CARD.md` and `MODEL_CARD.md` relative to 2026-08-12; all 105 code and
artifact paths are byte-identical. The newer cards remove two explicit
"Limitations" sections, but the README and remaining card text still identify
the short replay as an acceptance fixture rather than the complete benchmark,
place the private experiment-controller history outside the release, and package
only trained seed 42 although the paper reports five seeds.

The latest official archive is still not deployment-complete. Nine registered
files are 133-byte Git LFS pointers, covering 340,563,208 expected bytes: three
adapters, three tokenizers, one router, and two large strategy-pool tables. The
official public single-file endpoints returned `404 file_not_found` for all nine.
One generic tokenizer content address, repeated in three adapter directories, was
recovered byte-exactly from an independent public GitHub blob. It validates under
the declared Transformers 5.11.0 / Tokenizers 0.22.2 / Protobuf 7.35.0 contract
and raises registry verification from 26/35 to 29/35 files. This is exact byte
recovery, not MM-ARC author provenance. The three trained adapters, router, and
two historical strategy tables remain unavailable: six files and 306,295,258
registered bytes. Artifact verification and model execution therefore fail
closed.

An authenticated GitHub global code search on 2026-08-26 checked each of the six
remaining SHA-256 content addresses plus four distinctive release path/directory
names. All ten complete searches returned zero indexed files. This strengthens
the public-recovery boundary but is not proof that private, deleted, unindexed,
or non-GitHub copies do not exist.

Accordingly, the honest paper-level score remains **zero regenerated published
numeric table units and zero regenerated empirical figure series for every
version**. The release materially improves implementation and deployment
faithfulness for v3, but it cannot reproduce the v3 training, five-seed holdout,
statistical tests, tables, or figures; it does not reproduce the legacy v1/v2
MM-DREX experiment at all. No proxy, source-document rebuild, test double, or
acceptance replay receives native paper-result credit.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inventory = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    legacy_results = result_rows("v1_v2", V1_RESULT_TABLES)
    current_results = result_rows("v3", V3_RESULT_TABLES)
    write_csv(output / "version_revision_audit.csv", version_rows())
    write_csv(output / "published_result_ledger_v1_v2.csv", legacy_results)
    write_csv(output / "published_result_ledger_v3.csv", current_results)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "figure_inventory.csv", figure_rows())
    write_csv(output / "internal_consistency_audit.csv", internal_rows())
    release = release_audit(scratch)
    write_csv(output / "release_snapshot_history.csv", release_snapshot_rows())
    recovery = lfs_recovery_rows(scratch, release["lfs_pointer_inventory"])
    write_csv(
        output / "lfs_payload_recovery_audit.csv",
        recovery,
    )
    global_searches = global_lfs_search_rows(
        scratch, release["lfs_pointer_inventory"]
    )
    write_csv(output / "global_lfs_recovery_search.csv", global_searches)
    release["global_exact_lfs_code_search_queries"] = len(global_searches)
    release["global_exact_lfs_code_search_hits"] = sum(
        row["public_payload_or_pointer_hit"] for row in global_searches
    )
    release["global_remaining_lfs_oids_queried"] = 6
    write_json(output / "release_execution_audit.json", release)
    provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv": {
            "id": ARXIV_ID,
            "versions": ["v1", "v2", "v3"],
            "pdf_sha256": {"v1": PINS["primary/arxiv-v1.pdf"], "v2": PINS["primary/arxiv-v2.pdf"], "v3": PINS["primary/arxiv.pdf"]},
            "source_sha256": {"v1": PINS["source/arxiv-v1.tar"], "v2": PINS["source/arxiv-v2.tar"], "v3": PINS["source/arxiv.tar"]},
            "visual_qa": {
                "official_pages_inspected": {"v1": 32, "v2": 32, "v3": 17},
                "rebuilt_pages_inspected": {"v1": 30, "v2": 32, "v3": 16},
                "unreadable_clipped_or_overlapping_pages": 0,
            },
        },
        "official_repository": release,
        "public_exact_payload_recovery": {
            "classification": "independent_exact_content_not_author_attributable",
            "source_repository": TOKENIZER_SOURCE_REPOSITORY,
            "source_commit": TOKENIZER_SOURCE_COMMIT,
            "source_path": TOKENIZER_SOURCE_PATH,
            "payload_sha256": TOKENIZER_OID,
            "payload_bytes": TOKENIZER_BYTES,
            "registered_paths_recovered": 3,
            "declared_runtime_loaded": True,
            "native_model_or_strategy_execution_enabled": False,
            "paper_result_credit": False,
        },
        "release_boundary": {
            "v3_author_attribution": "directly linked from official v3 source",
            "v1_v2_implementation_recovered": False,
            "v3_runtime_source_recovered": True,
            "v3_deployment_payloads_all_recovered": False,
            "v3_exact_generic_tokenizer_oid_recovered": True,
            "v3_remaining_paper_specific_lfs_payloads": 6,
            "v3_complete_research_pipeline_recovered": False,
            "published_result_lineage_recovered": False,
        },
    }
    write_json(output / "source_provenance.json", provenance)
    (output / "README.md").write_text(readme(), encoding="utf-8")
    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_versions_audited": ["v1", "v2", "v3"],
        "legacy_v1_v2_source_identical": True,
        "v3_wholesale_replacement": True,
        "official_pdf_and_source_recovered": True,
        "official_document_rebuild_completed": True,
        "official_pages_visually_checked": 81,
        "rebuilt_pages_visually_checked": 78,
        "legacy_source_files": inventory["legacy_source_files"],
        "current_source_files": inventory["current_source_files"],
        "legacy_unique_published_numeric_table_units": len(legacy_results),
        "current_published_numeric_table_units": len(current_results),
        "legacy_native_numeric_units_regenerated": 0,
        "current_native_numeric_units_regenerated": 0,
        "native_empirical_figure_series_regenerated": 0,
        "official_repository_recovered": True,
        "official_repository_files": inventory["release_files"],
        "official_repository_tests_passed": release["tests_passed"],
        "official_repository_lfs_pointer_files": release["lfs_pointer_files"],
        "official_repository_snapshots_pinned": release["archive_snapshot_count"],
        "official_repository_refresh_changed_files": inventory["release_refresh_changed_files"],
        "official_repository_refresh_unchanged_files": inventory["release_unchanged_files"],
        "exact_public_payload_unique_oids_recovered": release["exact_public_payload_unique_oids_recovered"],
        "exact_public_payload_registered_paths_recovered": release["exact_public_payload_registered_paths_recovered"],
        "registered_artifact_files_verified_after_exact_public_recovery": release["verified_payload_files_after_exact_public_recovery"],
        "remaining_unavailable_lfs_payload_files": release["remaining_unavailable_pointer_files"],
        "remaining_unavailable_lfs_registered_bytes": release["remaining_unavailable_registered_bytes"],
        "global_exact_lfs_code_search_queries": release["global_exact_lfs_code_search_queries"],
        "global_exact_lfs_code_search_hits": release["global_exact_lfs_code_search_hits"],
        "global_remaining_lfs_oids_queried": release["global_remaining_lfs_oids_queried"],
        "trained_adapter_router_or_strategy_history_payload_recovered": False,
        "full_training_and_experiment_controller_released": False,
        "full_benchmark_data_released": False,
        "all_five_trained_seeds_released": False,
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
