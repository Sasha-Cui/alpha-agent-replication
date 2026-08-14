#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for MadEvolve trading."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/madevolve_trading_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/madevolve_trading"
WORK_ID = "CensusArxiv260523007"
SYSTEM_ID = "SYS-MAD-EVOLVE"
ARXIV_ID = "2605.23007"
FRAMEWORK_SITE = "https://madevolve.org"
REPOSITORY_URL = "https://github.com/tianyi-stack/MadEvolve"
REPOSITORY_HEAD = "8b881d3a45d8f68050c28c8d64c2bb653001103a"
REPOSITORY_COMMITS = (
    "679b50b462ede99b91920e48fcca4c18d777ae61",
    "78bf474816e84151ba50d1d57bf7d71bed0e1f68",
    "ed2a79b350015dfbb3f79dd1c51bef178716e8d4",
    "9f9567807f567b0ed9cd02b03b9bca26fcaaf552",
    "4f8f629cc98229845960441c0020b4ebf0626ef1",
    REPOSITORY_HEAD,
)
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_REPOSITORIES = (
    "2275131633/MadEvolve",
    "mardom/MadEvolve",
)
PUBLIC_FORK_HEADS = {
    "2275131633/MadEvolve": REPOSITORY_HEAD,
    "mardom/MadEvolve": REPOSITORY_COMMITS[0],
}
PUBLIC_FORK_COUNT = 2
PUBLIC_FORK_BRANCH_REF_COUNT = 2
PUBLIC_FORK_UNIQUE_HEAD_COUNT = 2
PUBLIC_FORK_TAG_REF_COUNT = 0
RESULT_ARTIFACT_SUFFIXES = (
    ".ckpt", ".csv", ".db", ".json", ".jsonl", ".npy", ".npz", ".parquet",
    ".pickle", ".pkl", ".pt", ".pth", ".safetensors", ".sqlite", ".tsv",
    ".xls", ".xlsx",
)
PAPER_DOMAIN_MARKERS = (
    "annualized return", "backtest", "bitcoin", "btcusd", "maximum drawdown",
    "polygon.io", "portfolio", "sharpe", "sortino", "trading strategy",
)

PINS = {
    "primary/arxiv-abs.html": "72c67fd4c5b22a7ea6bf27fc7303ad86ccfaa23d50663067fb80b30d95f76ef8",
    "primary/arxiv.pdf": "9a8c776fddbeab3ca753dcaed8f04e74884b18d40e818e5d23ab9c0051751c16",
    "source/arxiv-v1.tar": "e05e19e79fcf119e462c72bf7cd484b2c1cd9694fdca31d6f10ffbdafd4671ab",
    "discovery/madevolve.org.html": "d09d523b35c633a6d9714fc5e746aa53c8629aeab4f9438cde8c54904f930016",
    "discovery/github-branches.json": "6fdf8c9fe38ad3bfd139a06eb5884c41aa12aef3231d8724d3818cb63ce39335",
    "discovery/github-tags.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/github-releases.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "release/github-repository.json": "7c13c3bbe7f519210ed99b416878deb4f4d5df9fdb54d5496897269929b3efcf",
    "release/github-commit.json": "c8a975c13385521e0d5cf06099b6dd2a541059136e9b7644bb4f49473c1d61a4",
    "release/madevolve-8b881d3.tar.gz": "79a2bad2ac108a66d1c5c6737778ebe05c3021f165f63527b552c4eb52e39f11",
    "build/main.pdf": "9124e5f5298b91727092cc4524901a138b0719194873081c45ab48fdb389bce6",
    "build/pass1.txt": "7b45d4c85ccda30a344794ecb9858b954eb0889bc46bc4e9b72ecad1842ecc6a",
    "build/bibtex.txt": "4156676413e46d1eb3edc41dc814cb106360a97a28a8e5493102afd0e3d38974",
    "build/pass2.txt": "dda25f827eb45ef7d5042478bdd0e4e81b3398eefafd931783f30e1a3f8313c2",
    "build/pass3.txt": "c7cbb485c9dfa47c03dd414b01428dcb88b092f18be635cf36feebc0e9a64aad",
    "native/venv.txt": "bb1f55375b8b4bd7be698b0a44103e7d57eb24ae53ba0bf675cb80601b01c952",
    "native/install.txt": "9e263c5839d68babdc7be7c723e45b865ae112a979f67b6f7d563cec9a792681",
    "native/pre-fix-status.txt": "8594feb6b7709c5687f47153cc8ed49decd6e8ef875c11e38649cb82f7c0c8dd",
    "native/install-dotenv.txt": "1a66d8e1edadc1e93b5531b4a190edb5f33d6d705acc307141c0845a89b779d4",
    "native/post-dotenv-status.txt": "19b74f9cc7218e74386e212bdd3746bf7a3f762c5b8b054f35178da16e0016a2",
    "native/version-after-dotenv.txt": "9f8f1aca4c2d8213be6032de9c6e8f9d0364f24feebac0d20fc02da5723ffae5",
    "native/help-after-dotenv.txt": "a812fed6967ba352a8d18cb010adbaaf1976cef946b368c71a9877602d3c1573",
    "native/core-imports-after-dotenv.txt": "fbded4c7d092cbea15ce5c427345a763bf544fc8c73a43cfed3cd6a07e0575c8",
    "native/uv-pip-check.txt": "f87bfdad50ac9d237750854c5dc6a7130788e49fec70af79c78cf36e16b8c4a9",
    "native/uv-pip-check-status.txt": "64aa5650f6734c96ee64e20f32657605ae344f0e095007754ea852e3bad4bce5",
    "native/pip-freeze.txt": "77abfb56a622e6ce67b8c2e48e7b0dd104bb37d0f2edf977a4b552def8d57fd3",
    "native/compileall.txt": "5d1ef6f8c943b8f3448f405140f5be146e5fad033fac5e3febc2ec6950a38862",
    "native/compileall-status.txt": "a2493e47bbdf76c81ad931686b3e7d3bcee14ec007cd0bbc065da5cff7da1da8",
    "native/component-checks.json": "cf7cfa0436dcf1eee90bba82093de01a093fa83daa7fb820fb4c3fe9bd14765b",
    "native/module-imports.json": "eddafba52ff87753409c47fc9b6ce5c786479f317a3dfeca54fe6583c25e2bd0",
    "viz/official-low-contact-1-12.jpg": "ab28ea43393232cac092265e1cbda8bc7e7fa5e524a5c075ebef3af25c83a696",
    "viz/official-low-contact-13-24.jpg": "e1e90bf2f96b7eab717f528d296d23c699278b31c12ee3eb13ed1e6b558b43ee",
    "viz/official-low-contact-25-36.jpg": "39a80da34a5a6dcbbe78f3a48a70174475966c10f870b792edfe0c0c904e3f68",
    "viz/official-low-contact-37-46.jpg": "de7152c62e60cda943a03071a6841b76d2671b3887ef79a10f44e68b8084da5a",
    "viz/rebuilt-low-contact-1-12.jpg": "c6c9b7a02c0bde3a1767eb2176a84c4ae776e1951977aa88a5a41f060916decc",
    "viz/rebuilt-low-contact-13-24.jpg": "7d8dd60c322fa4ce141e194de0a9d70b660595b19a3e07eeb47a8b72a6e171b1",
    "viz/rebuilt-low-contact-25-36.jpg": "890e2fe04e946b37d35bef0a31ef46ea92513f003681de48567a59c086feeff7",
    "viz/rebuilt-low-contact-37-46.jpg": "709cbe35a3be324aa9b38c713b466a9969a07ce3b1c5bb74f4841c81c5c9382f",
}

# One unit is each displayed empirical number, including ratios in parentheses.
# Setup/parameter tables are audited as specifications, not empirical results.
RESULT_TABLES = {
    "tab:summary": 54,
    "tab:run4_metrics": 27,
    "tab:run5_metrics": 39,
    "tab:hyperparam_results": 42,
    "tab:model_stats": 20,
    "tab:claude_strategy_search": 20,
    "tab:claude_feature_evolution": 12,
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


def git(history_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(history_root), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def source_history_rows(scratch: Path) -> list[dict[str, Any]]:
    """Audit every public revision and fail closed on latent paper artifacts."""
    history_root = scratch / "discovery/madevolve-history"
    if git(history_root, "rev-parse", "--is-shallow-repository").stdout.strip() != "false":
        raise ValueError("MadEvolve history checkout is shallow")
    commits = git(history_root, "rev-list", "--reverse", "--all").stdout.splitlines()
    if commits != list(REPOSITORY_COMMITS):
        raise ValueError(f"MadEvolve public history changed: {commits}")
    unreachable = git(
        history_root, "fsck", "--full", "--no-reflogs", "--unreachable", "--no-progress"
    ).stdout.strip()
    if unreachable:
        raise ValueError(f"MadEvolve checkout has unreviewed unreachable objects: {unreachable}")

    branches = json.loads((scratch / "discovery/github-branches.json").read_text())
    tags = json.loads((scratch / "discovery/github-tags.json").read_text())
    releases = json.loads((scratch / "discovery/github-releases.json").read_text())
    if [(row["name"], row["commit"]["sha"]) for row in branches] != [
        ("main", REPOSITORY_HEAD)
    ]:
        raise ValueError("MadEvolve public branch topology changed")
    if tags or releases:
        raise ValueError("MadEvolve now exposes an unreviewed tag or release")

    rows: list[dict[str, Any]] = []
    for commit in commits:
        authored_at, subject = git(
            history_root, "show", "-s", "--format=%aI%x09%s", commit
        ).stdout.rstrip("\n").split("\t", 1)
        paths = git(history_root, "ls-tree", "-r", "--name-only", commit).stdout.splitlines()
        payload_paths = [path for path in paths if path.lower().endswith(RESULT_ARTIFACT_SUFFIXES)]
        domain_hits: list[str] = []
        for path in paths:
            if path == "README.md" or not path.endswith((".py", ".toml")):
                continue
            text = git(history_root, "show", f"{commit}:{path}").stdout.lower()
            domain_hits.extend(marker for marker in PAPER_DOMAIN_MARKERS if marker in text)
        if payload_paths or domain_hits:
            raise ValueError(
                "MadEvolve history contains an unreviewed paper artifact or domain literal: "
                f"paths={payload_paths}, literals={sorted(set(domain_hits))}"
            )
        rows.append({
            "commit": commit,
            "authored_at": authored_at,
            "subject": subject,
            "tracked_paths": len(paths),
            "python_paths": sum(path.endswith(".py") for path in paths),
            "structured_result_or_data_payload_paths": len(payload_paths),
            "paper_domain_literal_hits_outside_readme": len(domain_hits),
            "paper_result_artifact_found": False,
        })
    return rows


def public_fork_audit(
    scratch: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Exhaust every accessible public fork ref against the official history."""
    history_root = scratch / "discovery/madevolve-history"
    actual_refs: dict[str, str] = {}
    for line in git(
        history_root,
        "for-each-ref",
        "--format=%(refname)%09%(objectname)",
        "refs/remotes/forks",
    ).stdout.splitlines():
        refname, head = line.split("\t")
        actual_refs[refname] = head
    expected_refs = {
        f"refs/remotes/forks/{repository.split('/', 1)[0]}/main": head
        for repository, head in PUBLIC_FORK_HEADS.items()
    }
    if actual_refs != expected_refs:
        raise ValueError(f"MadEvolve public-fork branch refs changed: {actual_refs}")
    if git(history_root, "for-each-ref", "--format=%(refname)", "refs/tags").stdout.strip():
        raise ValueError("MadEvolve public-fork checkout unexpectedly contains tags")
    official = git(history_root, "rev-parse", "refs/remotes/origin/main").stdout.strip()
    if official != REPOSITORY_HEAD:
        raise ValueError("MadEvolve official remote head changed")

    branch_rows: list[dict[str, Any]] = []
    repositories_by_head: dict[str, list[str]] = {}
    for repository in PUBLIC_FORK_REPOSITORIES:
        owner = repository.split("/", 1)[0]
        head = actual_refs[f"refs/remotes/forks/{owner}/main"]
        official_only, fork_only = map(
            int,
            git(
                history_root,
                "rev-list",
                "--left-right",
                "--count",
                f"{official}...{head}",
            ).stdout.split(),
        )
        unique_commits = git(
            history_root,
            "rev-list",
            head,
            "--not",
            "refs/remotes/origin/main",
        ).stdout.splitlines()
        if fork_only or unique_commits:
            raise ValueError(f"MadEvolve fork adds unreviewed commits: {repository}")
        if head == official:
            relation = "official_head_exact"
        elif head in REPOSITORY_COMMITS and not fork_only:
            relation = "official_history_ancestor"
        else:
            raise ValueError(f"MadEvolve fork head is outside audited official history: {repository}")
        repositories_by_head.setdefault(head, []).append(repository)
        branch_rows.append({
            "repository": repository,
            "url": f"https://github.com/{repository}",
            "branch": "main",
            "head_commit": head,
            "relation_to_official_head": relation,
            "commits_ahead_of_official": fork_only,
            "commits_behind_official": official_only,
            "tag_refs": 0,
            "unique_commits_beyond_official_history": 0,
            "unique_blobs_beyond_official_history": 0,
            "native_result_artifact_found": False,
            "paper_result_credit": False,
        })

    unique_rows: list[dict[str, Any]] = []
    for head, repositories in sorted(repositories_by_head.items()):
        authored_at, subject = git(
            history_root, "show", "-s", "--format=%aI%x09%s", head
        ).stdout.rstrip("\n").split("\t", 1)
        unique_rows.append({
            "head_commit": head,
            "authored_at": authored_at,
            "subject": subject,
            "repositories": ";".join(sorted(repositories)),
            "branch_ref_count": len(repositories),
            "relation_to_official_history": (
                "official_head_exact" if head == official else "official_history_ancestor"
            ),
            "unique_commits_beyond_official_history": 0,
            "unique_blobs_beyond_official_history": 0,
            "native_result_artifact_found": False,
            "paper_result_credit": False,
        })
    if len(branch_rows) != PUBLIC_FORK_BRANCH_REF_COUNT:
        raise ValueError("MadEvolve public-fork branch-ref count changed")
    if len(unique_rows) != PUBLIC_FORK_UNIQUE_HEAD_COUNT:
        raise ValueError("MadEvolve public-fork unique-head count changed")
    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": PUBLIC_FORK_COUNT,
        "accessible_public_forks": len(branch_rows),
        "accessible_branch_refs": len(branch_rows),
        "tag_refs": PUBLIC_FORK_TAG_REF_COUNT,
        "unique_heads": len(unique_rows),
        "official_head_exact_unique_heads": sum(
            row["relation_to_official_history"] == "official_head_exact"
            for row in unique_rows
        ),
        "official_history_ancestor_unique_heads": sum(
            row["relation_to_official_history"] == "official_history_ancestor"
            for row in unique_rows
        ),
        "divergent_unique_heads": 0,
        "unique_commits_beyond_official_history": 0,
        "unique_blobs_beyond_official_history": 0,
        "native_result_artifacts_found": 0,
        "paper_result_credit": False,
        "interpretation": (
            "both accessible public forks and both branch refs resolve within the six-commit "
            "audited official history: one is the official head and one is its initial commit; "
            "they add no unique commit, blob, trading payload, or paper-result lineage"
        ),
    }
    return branch_rows, unique_rows, summary


def validate_tar(path: Path) -> list[tarfile.TarInfo]:
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
    for member in members:
        pure = PurePosixPath(member.name)
        if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
            raise ValueError(f"unsafe archive member: {member.name}")
    return [member for member in members if member.isfile()]


def validate_inputs(scratch: Path) -> dict[str, int]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    source = validate_tar(scratch / "source/arxiv-v1.tar")
    release = validate_tar(scratch / "release/madevolve-8b881d3.tar.gz")
    if (len(source), sum(item.size for item in source)) != (19, 666_909):
        raise ValueError("paper source inventory changed")
    if (len(release), sum(item.size for item in release)) != (69, 413_976):
        raise ValueError("repository archive inventory changed")
    return {"source_files": len(source), "release_files": len(release)}


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
                "blocking_reason": (
                    "trading adapter, Polygon data snapshot, experiment configs, seeds, "
                    "model-call traces, candidate programs, backtests, and result arrays are absent"
                ),
            })
    return rows


def figure_rows() -> list[dict[str, Any]]:
    specs = (
        ("fig:pnl_per_volume", 4, "sizing counterfactual, Sharpe, and Calmar panels"),
        ("fig:run1_pnl", 2, "validation and held-out cumulative PnL"),
        ("fig:run1_progress", 1, "cumulative-best evolution score"),
        ("fig:run2_pnl", 2, "validation and held-out cumulative PnL"),
        ("fig:run2_progress", 1, "cumulative-best evolution score"),
        ("fig:run3_pnl", 2, "validation and held-out cumulative PnL"),
        ("fig:run3_progress", 1, "cumulative-best evolution score"),
        ("fig:run5_pnl", 2, "validation and held-out cumulative PnL"),
        ("fig:run5_progress", 1, "cumulative-best evolution score"),
        ("fig:run5_is_oos_degradation", 1, "IS/OOS degradation curve"),
        ("fig:hyperparam_convergence", 2, "two Optuna convergence panels"),
        ("fig:model_improvement", 1, "per-model/per-run improvement rates"),
        ("fig:null_comparison", 1, "evolution-selected result versus null"),
    )
    return [{
        "version": "v1", "figure": figure, "empirical_series_or_panels": count,
        "description": description, "rendered_author_figure_recovered": True,
        "underlying_numeric_array_released": False,
        "author_native_figure_regenerated": False, "paper_result_credit": False,
    } for figure, count, description in specs]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official_document_source", "complete", "19-file source and 46-page PDF recovered; source rebuilds to 46 pages"),
        ("framework_provenance", "direct", "paper links madevolve.org; site links coauthor Tianyi Li's tianyi-stack/MadEvolve repository"),
        ("framework_release", "substantial_general_framework", "orchestrator, provider gateway, patch/rewrite modes, MAP-Elites, islands, elites, executors, storage, and reports"),
        ("framework_release_date", "precedes_paper", "pinned head committed 2026-03-03; paper submitted 2026-05-21"),
        ("framework_public_history", "complete_no_paper_payload", "all six commits on the only public branch audited; no tags, releases, unreachable objects, structured payloads, or paper-domain literals outside README"),
        ("framework_public_forks", "complete_no_additional_payload", "both accessible forks and both branch refs audited; one is the official head and one is the initial official-history commit, with no unique commits, blobs, or result artifacts"),
        ("market_data", "specified_not_released", "Polygon BTCUSD one-minute OHLCV; exact downloaded snapshot and exchange-aggregation state absent"),
        ("temporal_split", "specified", "fit 2022--2023, optimize on 2024, held-out test through 2025-10-10"),
        ("trading_adapter", "missing", "no BTC, OHLCV, order, fill, inventory, PnL, market-impact, or backtest implementation in the release"),
        ("baseline_forecaster", "pseudocode_only", "appendix skeleton contains omissions and depends on unreleased project classes and data"),
        ("baseline_strategy", "pseudocode_only", "appendix skeleton is not standalone and the complete simulator/evaluator is absent"),
        ("execution_model", "specified_not_released", "one resting limit order, candle-range fills, replacement lifecycle, fees, and impact equations described only in paper"),
        ("evolution_topology", "framework_component_executed", "MAP-Elites grid, two-island fixture, elite vault, patcher, and SQLite lineage store pass controlled checks"),
        ("paper_islands", "configuration_missing", "paper uses five islands; release default is four and no paper configuration is shipped"),
        ("paper_migration", "framework_default_matches", "release defaults match paper interval five and rate 0.1, but paper run configuration is absent"),
        ("llm_ensemble", "provider_support_only", "OpenAI, Anthropic, Google, and DeepSeek adapters exist; five paper model routing configuration and calls are absent"),
        ("generation_modes", "substantially_released", "differential patch and holistic rewrite paths exist; exact paper query mode draws are absent"),
        ("five_madevolve_runs", "missing", "no initial programs, configs, seeds, calls, candidates, lineages, scores, evolved code, or reports are shipped"),
        ("claude_code_strategy_search", "missing", "prompt/workflow, 200 proposals, 170 successes, ideas tree, candidate code, and outputs are absent"),
        ("claude_code_feature_search", "missing", "200 proposals, feature candidates, selection traces, code, and outputs are absent"),
        ("optuna_sweeps", "specified_not_released", "two 120-trial searches and bounds are described; studies, seeds, trial tables, and runner are absent"),
        ("null_analysis", "specified_not_released", "rendered figure and equations exist; underlying per-candidate arrays and calculation script are absent"),
        ("package_install", "passes_with_declared_dependencies", "editable package install resolves 39 declared packages"),
        ("cli_as_declared", "fails_missing_dependency", "python-dotenv is imported but omitted from pyproject dependencies"),
        ("cli_after_audit_dependency", "passes_after_adaptation", "help, version, and core imports pass only after adding python-dotenv to isolated audit env"),
        ("bytecode_compilation", "fails_release_syntax_error", "madevolve/templates/insight.py line 123 has an unmatched parenthesis"),
        ("author_tests", "absent", "zero test files are shipped"),
        ("published_results", "not_regenerated", "zero empirical table units and zero empirical panels were regenerated"),
    )
    return [{"version": "v1", "dimension": d, "status": s, "detail": detail} for d, s, detail in specs]


def internal_rows() -> list[dict[str, str]]:
    specs = (
        ("paper_program_total", "consistent", "per-model program counts sum to the stated 4,559 evolved programs"),
        ("five_run_candidate_total", "consistent", "990+997+1059+775+743 equals 4,564 total candidates; subtracting five baselines gives 4,559 evolved programs"),
        ("run5_count", "consistent", "main text reports 743 candidates and approximately program 733 as the best"),
        ("paper_framework_url", "direct", "paper directly names madevolve.org"),
        ("site_repository_route", "direct", "madevolve.org directly links tianyi-stack/MadEvolve"),
        ("repository_author_lineage", "coauthor_owned", "repository owner Tianyi Li is the second paper author"),
        ("repository_license", "metadata_only", "pyproject and site declare MIT, but repository has no LICENSE/COPYING text and GitHub detects no license"),
        ("repository_project_urls", "stale_or_mismatched", "pyproject points to madevolve/madevolve instead of the site-linked tianyi-stack/MadEvolve"),
        ("paper_island_count", "configuration_missing", "paper says five; released defaults use four"),
        ("cli_dependency_closure", "broken", "documented install omits imported python-dotenv"),
        ("source_compilation", "broken", "insight template contains unmatched parenthesis"),
        ("research_payload", "unreleased", "release contains no trading-specific code, data, configuration, candidate, or result artifact"),
        ("research_payload_history", "unreleased_all_revisions", "all six public revisions preserve the same 69-path framework tree with zero structured data/result payloads and zero paper-domain literals outside README"),
        ("research_payload_forks", "unreleased_all_public_forks", "both accessible forks collapse to two official-history heads and add no unique commit, blob, trading payload, or result artifact"),
        ("live_trading_claim", "paper_disclaims_transfer", "paper says exchange-aggregated data is not directly tradable and live performance is unassessed"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def release_audit(scratch: Path) -> dict[str, Any]:
    repo = scratch / "release/extracted/tianyi-stack-MadEvolve-8b881d3"
    paper = (scratch / "source/v1/main.tex").read_text(encoding="utf-8")
    site = (scratch / "discovery/madevolve.org.html").read_text(encoding="utf-8")
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    if FRAMEWORK_SITE not in paper or REPOSITORY_URL not in site:
        raise ValueError("paper-to-site-to-repository lineage changed")
    if "license = {text = \"MIT\"}" not in pyproject:
        raise ValueError("repository license metadata changed")
    if any((repo / name).exists() for name in ("LICENSE", "LICENSE.md", "COPYING")):
        raise ValueError("repository license-text boundary changed")
    searchable = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(repo.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".toml"}
    ).lower()
    for marker in ("btcusd", "ohlcv", "backtest", "polygon"):
        if marker in searchable:
            raise ValueError(f"trading payload boundary changed: found {marker}")
    checks = json.loads((scratch / "native/component-checks.json").read_text())
    if checks != {
        "artifact_store": {"best": "p1", "best_score": 3.0, "lineage": ["p0", "p1"]},
        "differential_patch": {"contains_mutation": True, "errors": [], "success": True, "syntax_valid": True},
        "elite_vault": {"add_results": [True, True, True], "top": ["p1", "p2"]},
        "islands": {"island_sizes": [3, 2], "num_islands": 2, "total_members": 5},
        "paper_result_credit": False,
        "paper_trading_component": False,
        "partition_grid": {"coverage": 0.125, "ids": ["p1", "p2"], "insertions": [True, True, True]},
        "seed": 260523007,
    }:
        raise ValueError("native component evidence changed")
    if (scratch / "native/pre-fix-status.txt").read_text() != (
        "version_status=1\nhelp_status=1\ncore_import_status=1\n"
    ):
        raise ValueError("as-declared CLI failure evidence changed")
    if (scratch / "native/post-dotenv-status.txt").read_text() != (
        "version_status=0\nhelp_status=0\ncore_import_status=0\n"
    ):
        raise ValueError("adapted CLI evidence changed")
    modules = json.loads((scratch / "native/module-imports.json").read_text())
    if (modules["attempted"], modules["passed"], modules["failed"]) != (66, 64, 2):
        raise ValueError("module import inventory changed")
    failures = {row["module"] for row in modules["modules"] if not row["imported"]}
    if failures != {"madevolve.templates", "madevolve.templates.insight"}:
        raise ValueError("module import failure set changed")
    if (scratch / "native/compileall-status.txt").read_text() != "compileall_status=1\n":
        raise ValueError("compile failure status changed")
    if "SyntaxError: unmatched ')'" not in (scratch / "native/compileall.txt").read_text():
        raise ValueError("compile failure reason changed")
    if "All installed packages are compatible" not in (scratch / "native/uv-pip-check.txt").read_text():
        raise ValueError("audit environment dependency check changed")
    return {
        "url": REPOSITORY_URL,
        "head_sha": REPOSITORY_HEAD,
        "head_commit_date": "2026-03-03T22:38:41Z",
        "archive_sha256": PINS["release/madevolve-8b881d3.tar.gz"],
        "archive_files": 69,
        "archive_bytes": 97_517,
        "archive_uncompressed_bytes": 413_976,
        "attribution": "paper links framework site; site links repository owned by coauthor Tianyi Li",
        "license_declaration": "MIT",
        "license_text_file_present": False,
        "github_detected_license": None,
        "python_files": 66,
        "tracked_test_files": 0,
        "author_tests": "absent",
        "editable_install_passed": True,
        "declared_dependency_check_after_audit_addition_passed": True,
        "central_environment": "/nfs/roberts/project/pi_btk22/zc362/environments/venvs/madevolve-py310-audit-20260812",
        "python_version": "3.10.19",
        "cli_help_as_declared_passed": False,
        "cli_failure_missing_dependency": "python-dotenv",
        "cli_help_after_audit_dependency_passed": True,
        "bytecode_compilation_passed": False,
        "compile_failure": "madevolve/templates/insight.py:123 unmatched parenthesis",
        "modules_imported_after_audit_dependency": 64,
        "modules_failed_import_after_audit_dependency": 2,
        "native_component_fixture": checks,
        "paper_trading_code_released": False,
        "paper_market_data_released": False,
        "paper_configs_and_seeds_released": False,
        "paper_model_call_traces_released": False,
        "paper_candidate_programs_released": False,
        "paper_best_evolved_programs_released": False,
        "paper_backtester_released": False,
        "paper_optuna_studies_released": False,
        "paper_claude_code_search_artifacts_released": False,
        "paper_run_reports_released": False,
        "paper_result_arrays_released": False,
        "full_launcher_operational_as_released": False,
        "published_table_or_figure_regenerated": False,
        "paper_result_credit": False,
    }


def readme() -> str:
    return """# MadEvolve trading paper and author-framework audit

This audit pins arXiv `2605.23007v1`, its complete 19-file source package,
and the 69-file MadEvolve framework repository at `8b881d3a`. The paper
directly links `madevolve.org`; that first-party site directly links
`tianyi-stack/MadEvolve`, whose owner Tianyi Li is the paper's second author.
This is a direct paper-to-framework-site-to-coauthor-repository route rather
than an inferred thematic match. The source rebuilds to the same 46-page
length. All 46 official and all 46 rebuilt pages were visually checked; no
unreadable, clipped, overlapping, blank, or missing research content was found.

The repository is a substantive general-purpose framework. It includes an
evolution orchestrator, multi-provider LLM gateway, differential-patch and
rewrite modes, MAP-Elites partitions, ring-island migration, an elite vault,
native and Slurm execution, SQLite artifact lineage, and report analysis. In a
controlled fixture, the patcher, grid, islands, elite vault, and artifact store
all work. These checks establish framework-component conformance only.

The full public Git history was also audited, rather than only the pinned head.
It contains six commits on one branch and no tags, releases, or unreachable Git
objects. Every revision has the same 69 tracked paths and 66 Python files, zero
structured data/result payloads, and zero Bitcoin, backtest, portfolio, or
paper-metric literals outside the README. No earlier or alternate public
revision supplies the missing trading research lineage.

The public fork surface was exhausted as of 2026-08-14. GitHub reports two
accessible forks with two branch refs and no tag refs. One ref is exactly the
official head and the other is the initial commit in the already-audited
official history. The two refs therefore add zero unique commits, zero unique
blobs, and zero trading or native-result artifacts. Neither fork supplies any
of the missing experiment lineage or earns paper-result credit.

The package does not run cleanly exactly as declared. Its editable install
resolves 39 packages, but the documented CLI immediately fails because
`python-dotenv` is imported and omitted from `pyproject.toml`. Adding that one
package only to the isolated audit environment restores version/help/core
imports. Even then, 64/66 modules import while `madevolve.templates` and
`madevolve.templates.insight` fail: `templates/insight.py` line 123 has an
unmatched parenthesis, so full bytecode compilation fails. The release ships no
tests. Its site and package metadata declare MIT, but the repository contains no
license text and GitHub detects no license.

More importantly, the release contains no trading-specific implementation at
all. There is no BTCUSD/OHLCV adapter, Polygon data snapshot, alpha forecaster,
order lifecycle, fill model, fees, market impact, backtester, paper configuration,
seed, exact model routing, call trace, candidate program, best evolved strategy,
run history, Optuna study, Claude Code ideas tree, run report, holdings, returns,
table array, or plot array. The appendix code is an incomplete skeleton with
omissions and unreleased project dependencies, not a runnable trading package.
The paper also uses five islands while the public default is four; interval five
and migration rate 0.1 match, but the actual paper configuration is absent.

The strict paper-level result is therefore **0/214 empirical numeric table units
and 0/21 empirical panels regenerated**. Rebuilding the PDF, adapting the CLI,
and exercising the general framework receive no paper-result credit. This is a
meaningful framework release, but it is not a true replication package for the
reported BTCUSD experiments. The paper itself appropriately cautions that its
exchange-aggregated data is not directly tradable and does not establish live
performance.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inventory = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    results = result_rows()
    figures = figure_rows()
    write_csv(output / "version_audit.csv", [{
        "version": "v1", "submitted": "2026-05-21",
        "title": "MadEvolve: Evolutionary Optimization of Trading Systems with Large Language Models",
        "authors": 4, "official_pages": 46, "source_files": inventory["source_files"],
        "rebuilt_pages": 46, "published_numeric_result_units": len(results),
        "empirical_panels": sum(row["empirical_series_or_panels"] for row in figures),
    }])
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "internal_consistency_audit.csv", internal_rows())
    history = source_history_rows(scratch)
    write_csv(output / "released_source_history_inventory.csv", history)
    fork_branches, fork_heads, fork_summary = public_fork_audit(scratch)
    write_csv(output / "public_fork_branch_ref_snapshot.csv", fork_branches)
    write_csv(output / "public_fork_unique_head_inventory.csv", fork_heads)
    write_json(output / "public_fork_census.json", fork_summary)
    release = release_audit(scratch)
    write_json(output / "release_execution_audit.json", release)
    write_json(output / "source_provenance.json", {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv": {
            "id": ARXIV_ID, "versions": ["v1"],
            "pdf_sha256": {"v1": PINS["primary/arxiv.pdf"]},
            "source_sha256": {"v1": PINS["source/arxiv-v1.tar"]},
            "visual_qa": {
                "official_pages_inspected": 46, "rebuilt_pages_inspected": 46,
                "unreadable_clipped_overlapping_blank_or_missing_pages": 0,
                "contact_sheet_sha256": {
                    key.removeprefix("viz/").removesuffix(".jpg"): value
                    for key, value in PINS.items() if key.startswith("viz/")
                },
            },
        },
        "framework_site": {
            "url": FRAMEWORK_SITE,
            "sha256": PINS["discovery/madevolve.org.html"],
            "direct_repository_link": REPOSITORY_URL,
        },
        "official_framework_repository": release,
        "release_boundary": {
            "attribution_strength": "direct_manuscript_site_to_coauthor_repository",
            "general_framework_source_recovered": True,
            "framework_component_execution_completed": True,
            "trading_research_code_recovered": False,
            "complete_research_data_recovered": False,
            "published_result_lineage_recovered": False,
            "full_public_history_audited": True,
            "public_history_commits": len(history),
            "public_branches": 1,
            "public_tags": 0,
            "public_releases": 0,
            "unreachable_git_objects": 0,
            "public_fork_census_date": fork_summary["census_date"],
            "public_forks_reported_by_github_rest": fork_summary[
                "github_rest_reported_forks"
            ],
            "public_forks_accessible": fork_summary["accessible_public_forks"],
            "public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
            "public_fork_tag_refs_audited": fork_summary["tag_refs"],
            "public_fork_unique_heads_audited": fork_summary["unique_heads"],
            "public_fork_divergent_heads_audited": fork_summary["divergent_unique_heads"],
            "public_fork_unique_commits_beyond_official_history": fork_summary[
                "unique_commits_beyond_official_history"
            ],
            "public_fork_unique_blobs_beyond_official_history": fork_summary[
                "unique_blobs_beyond_official_history"
            ],
            "public_fork_native_result_artifacts_found": False,
            "public_fork_paper_result_credit": False,
            "historical_structured_result_or_data_payload_paths": sum(
                row["structured_result_or_data_payload_paths"] for row in history
            ),
            "historical_paper_domain_literal_hits_outside_readme": sum(
                row["paper_domain_literal_hits_outside_readme"] for row in history
            ),
        },
    })
    (output / "README.md").write_text(readme(), encoding="utf-8")
    manifest = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "arxiv_id": ARXIV_ID,
        "official_versions_audited": ["v1"], "official_pdf_and_source_recovered": True,
        "document_rebuild_completed": True, "official_pages_visually_checked": 46,
        "rebuilt_pages_visually_checked": 46, "source_files": inventory["source_files"],
        "published_numeric_result_units": len(results), "native_numeric_units_regenerated": 0,
        "empirical_panels": sum(row["empirical_series_or_panels"] for row in figures),
        "native_empirical_panels_regenerated": 0, "official_framework_repository_recovered": True,
        "repository_files": inventory["release_files"], "author_tests_passed": 0,
        "repository_history_commits_audited": len(history),
        "repository_history_structured_result_or_data_payload_paths": sum(
            row["structured_result_or_data_payload_paths"] for row in history
        ),
        "repository_history_paper_result_artifacts_found": sum(
            bool(row["paper_result_artifact_found"]) for row in history
        ),
        "public_fork_census_date": fork_summary["census_date"],
        "public_forks_reported_by_github_rest": fork_summary[
            "github_rest_reported_forks"
        ],
        "public_forks_accessible": fork_summary["accessible_public_forks"],
        "public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
        "public_fork_tag_refs_audited": fork_summary["tag_refs"],
        "public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "public_fork_divergent_heads_audited": fork_summary["divergent_unique_heads"],
        "public_fork_unique_commits_beyond_official_history": fork_summary[
            "unique_commits_beyond_official_history"
        ],
        "public_fork_unique_blobs_beyond_official_history": fork_summary[
            "unique_blobs_beyond_official_history"
        ],
        "public_fork_native_result_artifacts_found": False,
        "public_fork_paper_result_credit": False,
        "native_component_checks_passed": 5, "modules_imported_after_audit_dependency": 64,
        "modules_failed_import_after_audit_dependency": 2,
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
