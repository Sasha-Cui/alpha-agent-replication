#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for AlphaSchema."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphaschema_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/alphaschema"
WORK_ID = "CensusArxiv260726642"
SYSTEM_ID = "SYS-ALPHA-SCHEMA"
ARXIV_ID = "2607.26642"
REPOSITORY_URL = "https://github.com/JingyangYi/AlphaSchema"
REPOSITORY_HEAD = "1206a094abfaad7cc53e6dff39f8fae43e851acb"
REPOSITORY_ROOT = "db11e667b08a0d0d6ce0609cdc6c2c9c804ca4cb"
REPOSITORY_COMMIT_COUNT = 2
RESULT_PATH_PARTS = {
    "action", "actions", "checkpoint", "checkpoints", "experiment", "experiments",
    "fill", "fills", "holding", "holdings", "log", "logs", "output", "outputs",
    "prediction", "predictions", "result", "results", "run", "runs", "signal",
    "signals", "trial", "trials",
}
RESULT_ARTIFACT_SUFFIXES = (
    ".ckpt", ".csv", ".jsonl", ".npy", ".npz", ".parquet", ".pickle", ".pkl",
    ".pt", ".pth", ".safetensors", ".xls", ".xlsx",
)

PINS = {
    "primary/arxiv-abs.html": "bc27065df0aec01efb0be0280d7bdce4a5eb692a6da907eba15fbe5ed04483f9",
    "primary/arxiv-api.xml": "379e1b05bc1834e3a9f042f07cff0b497bd1cda284d9bae3ce46936e38a8d8f8",
    "primary/arxiv-v1.pdf": "85f0d13a673969c6b1b49c63c394fded2b7380583b6096028eb56d96ae8fb651",
    "source/arxiv-v1.tar": "d00111b4fdf76197ca9b057df092f0a5316f5c7421c065acb337490c0dcd9722",
    "discovery/alphaschema-1206a09.zip": "fa4a31a9b664f70e4d83a7474492603d03b9e801f15140bbcb4294d175550e49",
    "build/main.pdf": "c707aaf10367fd162e38f790b0d6e368f37893b043429d11cda5a0512a3c48ea",
    "build/pass1.txt": "bed2f2f822cafbebe75c68c17a26894d0818cd26ed608d815a62bbec25bfc819",
    "build/bibtex.txt": "10f0a835c653ea79f1e70531fcc1c3c038959fdd9fe1321942c6b60e9810e20a",
    "build/pass2.txt": "95bab14a77166562a10e8a9651c6062b222f3b28dde8813ef6589f4440ae259c",
    "build/pass3.txt": "64846045bb9d10b4dbb6bbd660e0272181c489eb8475c8db62cac7067ec106be",
    "native/pytest.txt": "b58b9700c556077bfd3fa020072b12e47319d2eb86d263c50ad1b7cabbbba67f",
    "native/compileall.txt": "f8ebc65bcf3d22d004eddde09612fcff2d08ea954cb441132209d74adf4b6451",
    "native/help.txt": "c625d37da7bdc9889a6dc9e9dc37ffa86001015f63cf3c8e08ed58ae4f386352",
    "native/pip-freeze.txt": "00238e711326d6935abcff183e7a80df63d31b35169cef58db3fc37734af90d5",
    "native/demo.txt": "3c848fa5052bf9c8644200c6fd28c5ef3ce7bee9ffd2890ad5215d2d768e57f0",
    "native/demo-artifacts.txt": "ecfaec46c752d852f549bd32a1a7c48d133a2fe967f2ccc8da0c2ac17050cab0",
    "native/component-checks.json": "04cbaa95d99cf5df5b8b13725e5b363ba260dfe1ac3e21e512b40993d691e127",
    "native/default-validate.txt": "9544a17dc850f0b7cbdd9d404439b6d6afd23a2039eb6fd1494851177910ee69",
    "native/default-run.txt": "73d2484b728528a4fc9ed6e8ea751809ddfd3104e03005a4a85c804075bd6856",
    "native/default-status.txt": "170541cb0ad1de23ac789f488be367ddfd50eec81f2b985c9e6380467dd4ef58",
    "viz/official-contact-1-9.jpg": "559959459d18a341e55ee1f46238a7b57d8821fcff10f2b98782c56ebeb23a7b",
    "viz/official-contact-10-18.jpg": "916b16de68b65127470f4a21568adc5f51c4eba22a12e73dffbad16eebf7723d",
    "viz/rebuilt-contact-1-9.jpg": "e2761c4813dacb114227d789847a4bfc1b488ae662534b00684ee1ec8e6b451d",
    "viz/rebuilt-contact-10-18.jpg": "da7e51964051553c255ec7eb89086395552e51ace78f1a29c9251e000796f4df",
}

RESULT_TABLES = {
    "tab:main_eval": 77,
    "tab:appendix_example_factor_rankic": 3,
    "tab:appendix_dominant_manifold_semantics": 16,
    "tab:appendix_realization_budget_efficiency": 25,
    "tab:appendix_schema_ablation_design": 24,
    "tab:appendix_schema_predictability_full": 32,
    "tab:appendix_code_agent_robustness": 35,
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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(history_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(history_root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def source_history_rows(history_root: Path) -> list[dict[str, Any]]:
    if git(history_root, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise ValueError("AlphaSchema history checkout is shallow")
    commits = git(history_root, "rev-list", "--reverse", "--all").splitlines()
    if len(commits) != REPOSITORY_COMMIT_COUNT:
        raise ValueError(f"AlphaSchema public commit count changed: {len(commits)}")
    if commits != [REPOSITORY_ROOT, REPOSITORY_HEAD]:
        raise ValueError(f"AlphaSchema public-history endpoints changed: {commits}")

    rows: list[dict[str, Any]] = []
    for commit in commits:
        authored_at, subject = git(
            history_root, "show", "-s", "--format=%aI%x09%s", commit
        ).rstrip("\n").split("\t", 1)
        paths = git(history_root, "ls-tree", "-r", "--name-only", commit).splitlines()
        schema_or_config_paths = [
            path for path in paths if path.startswith(("configs/", "schemas/")) and path.endswith(".json")
        ]
        result_paths = [
            path
            for path in paths
            if any(part in RESULT_PATH_PARTS for part in path.lower().split("/"))
            or path.lower().endswith(RESULT_ARTIFACT_SUFFIXES)
        ]
        unclassified = sorted(set(result_paths) - set(schema_or_config_paths))
        if unclassified:
            raise ValueError(f"AlphaSchema history contains an unreviewed result artifact: {unclassified}")
        rows.append(
            {
                "commit": commit,
                "authored_at": authored_at,
                "subject": subject,
                "tracked_paths": len(paths),
                "python_paths": sum(path.endswith(".py") for path in paths),
                "schema_or_config_json_paths": len(schema_or_config_paths),
                "unclassified_result_artifact_paths": 0,
                "paper_result_artifact_found": False,
            }
        )
    return rows


def safe_archives(scratch: Path) -> None:
    with tarfile.open(scratch / "source/arxiv-v1.tar", "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe source member: {member.name}")
    with zipfile.ZipFile(scratch / "discovery/alphaschema-1206a09.zip") as archive:
        for member in archive.infolist():
            pure = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            if pure.is_absolute() or ".." in pure.parts or (mode & 0o170000) == 0o120000:
                raise ValueError(f"unsafe repository member: {member.filename}")


def validate_inputs(scratch: Path) -> dict[str, int]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    safe_archives(scratch)
    with tarfile.open(scratch / "source/arxiv-v1.tar", "r:*") as archive:
        source = [member for member in archive.getmembers() if member.isfile()]
    if (len(source), sum(item.size for item in source)) != (23, 1_574_394):
        raise ValueError("paper source inventory changed")
    with zipfile.ZipFile(scratch / "discovery/alphaschema-1206a09.zip") as archive:
        release = [item for item in archive.infolist() if not item.is_dir()]
    if (len(release), sum(item.file_size for item in release)) != (32, 1_945_533):
        raise ValueError("repository archive inventory changed")
    return {"source_files": 23, "release_files": 32}


def result_rows() -> list[dict[str, Any]]:
    rows = []
    for table, count in RESULT_TABLES.items():
        for index in range(1, count + 1):
            rows.append({
                "version": "v1",
                "table_label": table,
                "printed_numeric_unit": index,
                "source_document_recovered": True,
                "author_native_experiment_executed": False,
                "published_result_regenerated": False,
                "paper_result_credit": False,
                "blocking_reason": "paper market data, memberships, factors, run histories, model calls, baseline runs, and result arrays are not released",
            })
    return rows


def figure_rows() -> list[dict[str, Any]]:
    specs = (
        ("fig:nav", 1, "CSI300 NAV trajectories"),
        ("fig:schema_leave_one_out", 1, "schema-component ablation"),
        ("fig:semantic_trajectory", 1, "semantic-space trajectory"),
        ("fig:realization_efficiency", 2, "reward estimation and budget-efficiency panels"),
        ("fig:code_agent_model_invariance", 1, "backend robustness"),
        ("fig:appendix_csi500_cumulative_return", 1, "CSI500 return trajectories"),
        ("fig:appendix_factor_decay", 1, "factor-decay trajectories"),
        ("fig:schema_predictability", 1, "reward-predictability comparison"),
    )
    return [{
        "version": "v1", "figure": figure, "empirical_series_or_panels": count,
        "description": description, "underlying_numeric_array_released": False,
        "author_native_figure_regenerated": False, "paper_result_credit": False,
    } for figure, count, description in specs]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official_document_source", "complete", "23-file source package recovered; 18-page manuscript rebuilt"),
        ("official_repository", "directly_linked_author_release", "manuscript directly links the first-author repository at the pinned head"),
        ("market_universe", "specified_not_released", "CSI300/SH000300 primary and CSI500 extension; dated constituent histories absent"),
        ("temporal_split", "specified", "train 2016--2020, validation 2021--2022, held-out test 2023--2025"),
        ("price_volume_schema", "released_but_revision_diverges", "paper states 40/40/50/3/7=140 components; release contains 54/43/59/3/8=167"),
        ("fundamental_schema", "missing", "paper's +Fundamental variant and 30 fundamental factors have no released schema/data implementation"),
        ("code_agent_prompts", "substantially_released", "generation and repair prompts plus OpenAI-compatible client are present"),
        ("search_core", "substantially_released", "sampling, novelty, LightGBM reward ensemble, exploitation, mutation, buffer, and reporting are present"),
        ("search_budget", "configured", "16 plans, 10,000 candidates, staged quotas, seed, and one repair are released"),
        ("paper_search_horizon", "manual_only", "CLI can be asked for 80 rounds but defaults to one; no five-independent-run orchestrator"),
        ("mutation_ranking", "paper_release_mismatch", "paper ranks mutation candidates by predicted reward; release accepts round-robin top-parent mutations before prediction"),
        ("exploration_schedule", "paper_release_mismatch", "paper specifies exponential exploration share; release implements fixed observation-threshold quotas"),
        ("schema_set_identity", "paper_release_mismatch", "paper defines qualities as a set; release preserves tuple order in keys and can treat permutations as distinct"),
        ("factor_realization", "component_executed", "literal manuscript appendix factor executes for periods 20/100 on a controlled 25-stock panel"),
        ("leakage_checks", "component_executed", "static and prefix-invariance checks pass on the controlled appendix-factor fixture"),
        ("main_forward_label", "paper_release_mismatch", "paper Ref(close,-6)/Ref(close,-1)-1 differs from release close.shift(-5)/close-1"),
        ("final_factor_pool_selection", "missing", "reward-ranked absolute-correlation <0.7 export logic and 120/150 factor pools are absent"),
        ("downstream_combiner", "missing", "paper's CSRankNorm/LightGBM combiner, tuning, 500 rounds, and early stopping are absent"),
        ("portfolio_backtest", "missing", "paper's Qlib Top50/Drop5 engine, open-price execution, fees, limits, benchmark, and NAV path are absent"),
        ("baselines", "missing", "MLP, XGBoost, Transformer, GRU, LSTM, Alpha158/360, RD-Agent, and QuantaAlpha runs are absent"),
        ("analysis_archives", "missing", "ablation, 12,126-pair predictability archive, repeated realizations, model robustness, CSI500, and decay arrays are absent"),
        ("default_launcher", "data_blocked", "default validate/run fail immediately because data/stock_bars is not released"),
        ("published_results", "not_regenerated", "zero published numeric units and zero empirical panels were regenerated"),
    )
    return [{"version": "v1", "dimension": dimension, "status": status, "detail": detail} for dimension, status, detail in specs]


def internal_rows() -> list[dict[str, str]]:
    specs = (
        ("main_forward_label", "paper_release_mismatch", "one-period timing-anchor difference between manuscript equation and backend"),
        ("schema_inventory", "paper_release_mismatch", "manuscript 140 price-volume components versus release 167 components"),
        ("quality_canonicalization", "paper_release_mismatch", "quality permutations denote the same set in the paper but different release keys"),
        ("mutation_scoring", "paper_release_mismatch", "release records predictions only after mutation candidates have already been chosen"),
        ("exploration_share", "paper_release_mismatch", "exponential equation is not implemented by the released staged quota schedule"),
        ("paper_example_periods", "release_configuration_difference", "appendix example metadata uses [20,100], default release config uses [20,80]"),
        ("five_run_protocol", "unreleased", "five independent runs are stated without a multi-run driver, seed set, calls, or outputs"),
        ("research_data", "unreleased", "market, fundamental, membership, benchmark, and experiment data are absent"),
        ("result_lineage", "unreleased", "factor pools, predictions, holdings, returns, tables, figures, and generators are absent"),
        ("repository_license", "not_declared", "pinned public repository has no license file or GitHub-detected license"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def release_audit(scratch: Path) -> dict[str, Any]:
    repo = next((scratch / "repo/extracted").iterdir())
    paper_main = (scratch / "source/extracted/main.tex").read_text()
    if REPOSITORY_URL not in paper_main:
        raise ValueError("paper no longer directly links the repository")
    if any((repo / name).exists() for name in ("LICENSE", "LICENSE.md", "COPYING")):
        raise ValueError("repository licensing evidence changed")
    checks = json.loads((scratch / "native/component-checks.json").read_text())
    expected_counts = {"event": 54, "context": 43, "quality": 59, "direction": 3, "output": 8}
    if checks["schema_counts"] != expected_counts or checks["schema_total"] != 167:
        raise ValueError("schema inventory changed")
    component = checks["paper_example_component"]
    if component["leakage_issues"] or not component["finite_reward"] or component["published_result_credit"]:
        raise ValueError("controlled appendix component evidence changed")
    if "9 passed in 2.22s" not in (scratch / "native/pytest.txt").read_text():
        raise ValueError("author test evidence changed")
    if (scratch / "native/demo.txt").read_text().count("round=") != 3:
        raise ValueError("native demo evidence changed")
    if (scratch / "native/default-status.txt").read_text() != "validate_status=1\nrun_status=1\n":
        raise ValueError("default launcher status changed")
    for relative in ("native/default-run.txt", "native/default-validate.txt"):
        if "Market data path does not exist" not in (scratch / relative).read_text():
            raise ValueError("default missing-data evidence changed")
    return {
        "url": REPOSITORY_URL,
        "head_sha": REPOSITORY_HEAD,
        "archive_sha256": PINS["discovery/alphaschema-1206a09.zip"],
        "archive_files": 32,
        "archive_bytes": 1_573_612,
        "archive_uncompressed_bytes": 1_945_533,
        "attribution": "directly linked from the manuscript and owned by first author Jingyang Yi",
        "license": "not_declared",
        "python_files": 16,
        "tracked_test_files": 1,
        "author_tests": "9 passed",
        "editable_install_passed": True,
        "central_environment": "/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alphaschema-py310-audit-20260812",
        "python_version": "3.10.8",
        "cli_help_passed": True,
        "bytecode_compilation_passed": True,
        "native_demo_rounds": 3,
        "native_demo_plans": 48,
        "native_demo_uses_mock_evaluator": True,
        "paper_appendix_factor_component": component,
        "paper_label_matches_release_backend": checks["release_backend_label_matches_paper_main_equation"],
        "paper_market_data_released": False,
        "paper_fundamental_schema_and_data_released": False,
        "paper_factor_pools_released": False,
        "paper_baseline_implementations_released": False,
        "paper_trial_outputs_released": False,
        "paper_downstream_combiner_released": False,
        "paper_portfolio_engine_released": False,
        "default_launcher_operational_as_released": False,
        "published_table_or_figure_regenerated": False,
        "paper_result_credit": False,
    }


def readme() -> str:
    return """# AlphaSchema paper and author-release audit

This audit pins arXiv `2607.26642v1`, its complete 23-file source package,
and the 32-file repository at `1206a094`. The manuscript directly links
`JingyangYi/AlphaSchema`, and the owner is first author Jingyang Yi, so the
provenance is direct rather than inferred. The source rebuilds to the same
18-page length. All 18 official and all 18 rebuilt pages were visually checked;
no unreadable, clipped, overlapping, or missing page content was found.

The release is a real implementation artifact. In an isolated Python 3.10.8
environment it installs, compiles, exposes its CLI, passes all 9 author tests,
and completes the 3-round/48-plan deterministic demo. The search release contains
schema sampling, novelty selection, a LightGBM reward ensemble, exploitation,
mutation, prompt-driven code realization and repair, static/prefix leakage checks,
reward computation, resumable records, and reports. The literal appendix factor
also executes for periods 20 and 100 on a controlled 25-stock synthetic panel,
produces two finite factor outputs, passes the native leakage check, and receives
a finite reward. These are meaningful implementation-conformance results.

They do not reproduce the paper's experiments. The default launcher fails at the
missing `data/stock_bars` path. No CSI300/CSI500 market snapshots, point-in-time
memberships, fundamental schema/data, five-run histories, model calls, exported
120/150-factor pools, baseline implementations, CSRankNorm/LightGBM pool combiner,
Qlib Top50/Drop5 portfolio engine, holdings/returns, or empirical result arrays and
generators are released. The repository also declares no license.

The complete non-shallow public history has only two commits. The second changes
README documentation and adds a method diagram; all implementation and schema
blobs are unchanged. Across both revisions, the only JSON payloads are the search
configuration and five schema definitions. No result/log/checkpoint/data path,
factor pool, prediction, holding, return, or paper-result array is present.

Several release details diverge from the manuscript. The paper's main target is
`Ref(close,-6)/Ref(close,-1)-1`, whereas the backend uses
`close.shift(-5)/close-1`. The paper states 140 price-volume components
(40/40/50/3/7), while the release contains 167 (54/43/59/3/8). The paper models
qualities as a set, but the release keeps tuple order in the plan key, so quality
permutations can become distinct plans. The manuscript says mutation candidates
are reward-model ranked before selection and defines an exponential exploration
share; the release accepts round-robin top-parent mutations before prediction and
uses fixed observation-threshold quotas.

The strict paper-level result is therefore **0/212 published numeric table units
and 0/9 empirical panels regenerated**. Rebuilding the PDF, passing author tests,
running the mock demo, and executing the appendix factor on synthetic data receive
no paper-result credit. This is currently a substantial implementation release,
not a true reproduction of AlphaSchema's reported predictive or portfolio results.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inventory = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    results = result_rows()
    figures = figure_rows()
    write_csv(output / "version_audit.csv", [{
        "version": "v1", "submitted": "2026-07-29",
        "title": "AlphaSchema: Exploring the Space of Trading Semantics for LLM-Based Alpha Mining",
        "authors": 5, "official_pages": 18, "source_files": inventory["source_files"],
        "rebuilt_pages": 18, "published_numeric_result_units": len(results),
        "empirical_panels": sum(row["empirical_series_or_panels"] for row in figures),
    }])
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "internal_consistency_audit.csv", internal_rows())
    history = source_history_rows(scratch / "discovery/alphaschema-history")
    write_csv(output / "released_source_history_inventory.csv", history)
    release = release_audit(scratch)
    write_json(output / "release_execution_audit.json", release)
    write_json(output / "source_provenance.json", {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv": {
            "id": ARXIV_ID, "versions": ["v1"],
            "pdf_sha256": {"v1": PINS["primary/arxiv-v1.pdf"]},
            "source_sha256": {"v1": PINS["source/arxiv-v1.tar"]},
            "visual_qa": {
                "official_pages_inspected": 18, "rebuilt_pages_inspected": 18,
                "unreadable_clipped_or_overlapping_pages": 0,
                "contact_sheet_sha256": {
                    "official_1_9": PINS["viz/official-contact-1-9.jpg"],
                    "official_10_18": PINS["viz/official-contact-10-18.jpg"],
                    "rebuilt_1_9": PINS["viz/rebuilt-contact-1-9.jpg"],
                    "rebuilt_10_18": PINS["viz/rebuilt-contact-10-18.jpg"],
                },
            },
        },
        "official_repository": release,
        "release_boundary": {
            "attribution_strength": "direct_manuscript_link_and_first_author_owner",
            "runtime_source_recovered": True,
            "author_tests_passed": True,
            "component_execution_completed": True,
            "default_end_to_end_launcher_operational": False,
            "complete_research_data_recovered": False,
            "published_result_lineage_recovered": False,
            "full_public_history_audited": True,
            "public_history_commits": len(history),
            "historical_unclassified_result_artifact_paths": sum(
                row["unclassified_result_artifact_paths"] for row in history
            ),
        },
    })
    (output / "README.md").write_text(readme(), encoding="utf-8")
    manifest = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "arxiv_id": ARXIV_ID,
        "official_versions_audited": ["v1"], "official_pdf_and_source_recovered": True,
        "document_rebuild_completed": True, "official_pages_visually_checked": 18,
        "rebuilt_pages_visually_checked": 18, "source_files": inventory["source_files"],
        "published_numeric_result_units": len(results), "native_numeric_units_regenerated": 0,
        "empirical_panels": sum(row["empirical_series_or_panels"] for row in figures),
        "native_empirical_panels_regenerated": 0, "official_repository_recovered": True,
        "repository_files": inventory["release_files"], "author_tests_passed": 9,
        "repository_history_commits_audited": len(history),
        "repository_history_unclassified_result_artifact_paths": sum(
            row["unclassified_result_artifact_paths"] for row in history
        ),
        "repository_history_paper_result_artifacts_found": sum(
            bool(row["paper_result_artifact_found"]) for row in history
        ),
        "native_demo_plans": 48, "native_component_checks_passed": 3,
        "full_launcher_operational_as_released": False,
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
