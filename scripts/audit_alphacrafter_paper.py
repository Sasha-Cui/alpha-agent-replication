#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for AlphaCrafter."""
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
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphacrafter_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/alphacrafter"
WORK_ID = "CensusArxiv260505580"
SYSTEM_ID = "SYS-ALPHA-CRAFTER"
ARXIV_ID = "2605.05580"
REPOSITORY_URL = "https://github.com/NJU-LINK/AlphaCrafter"
REPOSITORY_HEAD = "c6dbc1ba4e0a4ecbc3ea1454c5290dbea4b36b0d"
REPOSITORY_ROOT = "15d46d501731eaef117c6a0de440cbebcf316de0"
REPOSITORY_COMMIT_COUNT = 13
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_BRANCHES = (
    (
        "maimaili421/AlphaCrafter",
        "main",
        "829b64df837187973ca0b97437c47d10f0a712f5",
        "official_history_ancestor",
        0,
        6,
    ),
    (
        "kleamend/AlphaCrafter",
        "main",
        "fe2616744651481031fcb9d1bf090fef7aef4d6d",
        "divergent",
        17,
        5,
    ),
    (
        "assigmeAI/AlphaCrafter",
        "main",
        "ebe23cdca6fd23912cf673697a30acacfa991fe6",
        "official_history_ancestor",
        0,
        5,
    ),
    (
        "balderdash518/AlphaCrafter",
        "main",
        "ebe23cdca6fd23912cf673697a30acacfa991fe6",
        "official_history_ancestor",
        0,
        5,
    ),
    (
        "zzwz02/AlphaCrafter",
        "main",
        REPOSITORY_HEAD,
        "official_head_exact",
        0,
        0,
    ),
    (
        "sskye123/AlphaCrafter",
        "main",
        REPOSITORY_HEAD,
        "official_head_exact",
        0,
        0,
    ),
)
PUBLIC_FORK_REST_COUNT = 6
PUBLIC_FORK_BRANCH_REF_COUNT = 6
PUBLIC_FORK_UNIQUE_HEAD_COUNT = 4
PUBLIC_FORK_TAG_REF_COUNT = 0
KLEAMEND_REPOSITORY = "kleamend/AlphaCrafter"
KLEAMEND_BASE = "ebe23cdca6fd23912cf673697a30acacfa991fe6"
KLEAMEND_HEAD = "fe2616744651481031fcb9d1bf090fef7aef4d6d"
KLEAMEND_CUMULATIVE_DIFF_SHA256 = (
    "0cdd0090188e4363e1820063a9a962d0eba4f69ea9c35d87abf40dd0a5714d34"
)
KLEAMEND_PROFILE_SNAPSHOT = {
    "login": "kleamend",
    "name": "Yongjian Zhang",
    "claimed_company": "Nanjing University",
    "claimed_bio": "Nanjing University",
    "claimed_blog": "https://nju.edu.cn",
    "paper_author_identity_match": False,
}
PAPER_AUTHORS = ("Yishuo Yuan", "Jiayi Sheng", "Sirui Zeng", "Jiaqi Wang", "Jiaheng Liu")
KLEAMEND_STRUCTURED_CHANGED_PATHS = {
    "alphacrafter/sandbox/template_a/config/models.json",
    "alphacrafter/sandbox/template_us/config/models.json",
    "display/package-lock.json",
    "display/package.json",
    "display/src/test/fixtures/backtest_results.json",
    "display/src/test/fixtures/miner_agent.json",
    "display/src/test/fixtures/screener_agent.json",
    "display/src/test/fixtures/snapshot.json",
    "display/src/test/fixtures/trader_agent.json",
    "display/src/test/fixtures/workflow.json",
    "display/tsconfig.json",
}
KLEAMEND_SYNTHETIC_FIXTURE_SHA256 = {
    "display/src/test/fixtures/backtest_results.json": "f4bc30d67dccbd8432b55eb56b66d770de15c88621ce9a5685be993882c79906",
    "display/src/test/fixtures/miner_agent.json": "d95dd4279718482f3d3ba2f1aa01665e1d4da2c13af8653ffeeab41f8933966b",
    "display/src/test/fixtures/screener_agent.json": "909b78d10c8f6ceea425a8202e5b0630eb30ab6d5d27d14da783e742158d8e15",
    "display/src/test/fixtures/snapshot.json": "cb799a958691d196dec3f4569157dd44d6fc8a01992b5e114fc1ac75c239d695",
    "display/src/test/fixtures/trader_agent.json": "b1459acbab00c49af7cd3b5d92606c22a2ad595461c3e5a1c9e676b13d3a4b7c",
    "display/src/test/fixtures/workflow.json": "65c91d2fd33b8d310675074db6ef03c155d62e65f94843850ab9494bb5dd5090",
}

STRUCTURED_SUFFIXES = (
    ".ckpt", ".csv", ".feather", ".json", ".jsonl", ".npy", ".npz",
    ".parquet", ".pickle", ".pkl", ".pt", ".pth", ".safetensors", ".xls", ".xlsx",
)
RESULT_PATH_PARTS = {
    "action", "actions", "checkpoint", "checkpoints", "experiment", "experiments",
    "fill", "fills", "holding", "holdings", "log", "logs", "output", "outputs",
    "prediction", "predictions", "result", "results", "run", "runs", "signal",
    "signals", "trial", "trials",
}
PAPER_RESULT_LITERALS = ("18.88", "1.6732", "15.66", "1.3425", "10.70", "1.1902", "16.26")

PINS = {
    "primary/arxiv-abs.html": "676a1af03dc2df13bbb7becb15394299af5137816e7a80a48f5636a39ac99506",
    "primary/arxiv-api.xml": "de6282b961ec3ad7462744ed8ae886dba5ba1570df6cc800395544054e1aa001",
    "primary/arxiv-v1.pdf": "7e7da45cdc80bab1ddbd272b3b6198113aef50712357508c2b589afd00d0239d",
    "primary/arxiv-v2.pdf": "50fac266012726355d34b64788c529adf09c8574a751395d55858640dc1a5e67",
    "source/arxiv-v1.tar": "511e441781702609d11024dbe31577c6396c1f68e3023f08326050417e399f53",
    "source/arxiv-v2.tar": "36a34ecb7ef524d8d7efe4a67002e726a0345bc6c3f5414325dd18a080829b84",
    "build-v1/main.pdf": "906e50f764e58c5f6b9ccc98b721e3762689120bd99297f4eef70f74a671c10e",
    "build-v2/main.pdf": "eebf4471f2ce2fd4899aab3d43f99d1c5963a45f8da226dba3f5d128719a9fb3",
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
    "build-v2-pass1-complete.txt": "8a907c138a4b2f68bde9b3a11d5bdaceb41c79ab1a41c17fad4d83b07aeeed16",
    "build-v2-bibtex-complete.txt": "945dfd4dd6ae1b9894c9e8eee5a735d4cd136106643d6272a3c151b3f6840176",
    "build-v2-pass2-complete.txt": "d4b86d533a72b38c86cfe68d9ac38f986d1ac219d87b5d836b136178d36dd98f",
    "build-v2-pass3-complete.txt": "be3cbfa7e52caefbd09bcafe80bad0ff9738046930e3aaf260335cb19c580bb0",
    "build-v2-pass4-complete.txt": "16546c393500e54450b5961c09c33f00e8057bc156b72bd03693414dc9aedeff",
    "viz/v1-official-contact.jpg": "133553ba0d74032301b4275800dc93e64005bc4b4b612cedca0c575f452a5961",
    "viz/v2-official-contact.jpg": "eba5aecf8e4b75505fd0bac696929ea97adb10b4fec3373fb23bb708c21fc80c",
    "viz/v1-rebuilt-contact.jpg": "e339173a02746fb179dc0f09bf8ddcc1563cbe53373f305843d77458f733030a",
    "viz/v2-rebuilt-contact.jpg": "b0d69e15e716cc42cf4fc7390ff507fe32c9c00197a358089e9002c8219182fb",
    "viz/v2-side-by-side/contact-01.jpg": "fbe8fa27f19779010373c385b0c19559136fb72fc869625ff4bf9ba982df3125",
    "viz/v2-side-by-side/contact-02.jpg": "56d366689e52d959d6e21ef39ee565920d03f238b1d3698ab96d4a4aa89567cd",
    "viz/v2-side-by-side/contact-03.jpg": "8260d2287c2fe398744b53638f5d607cd0228fc57866f9db736c2728e2a24b21",
    "viz/v2-side-by-side/contact-04.jpg": "08df67ab4860d9548aa041c93e315ef52356ec302540b08d7972df0e56ae7adb",
    "viz/v2-side-by-side/contact-05.jpg": "c87c8a2c34d362ad8e8ace9416c404c90a6ff4c1053d64ad1d3d14b17ab9e266",
    "viz/v2-side-by-side/contact-06.jpg": "d4008345c07d412363d63e8ce5e98d2c12d12745527c3b1dca5b0dd4f3898107",
    "v2-render-diff-metrics.json": "3f718a32ae0a6a911339edf8575f3bcdad64b066387f74c1b3ad37733aad0aed",
}

V1_RESULT_TABLES = {"tab:combined": 144, "tab:ablation": 32}
V2_RESULT_TABLES = {"tab:combined": 264, "tab:ablation": 40}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def git(history_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(history_root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def git_bytes(history_root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(history_root), *args],
        check=True,
        capture_output=True,
    ).stdout


def source_history_rows(history_root: Path) -> list[dict[str, Any]]:
    """Audit all public revisions without mistaking shipped templates for results."""
    if git(history_root, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise ValueError("AlphaCrafter history checkout is shallow")
    commits = git(
        history_root, "rev-list", "--reverse", "refs/remotes/origin/main"
    ).splitlines()
    if len(commits) != REPOSITORY_COMMIT_COUNT:
        raise ValueError(f"AlphaCrafter public commit count changed: {len(commits)}")
    if commits[0] != REPOSITORY_ROOT or commits[-1] != REPOSITORY_HEAD:
        raise ValueError("AlphaCrafter public-history endpoints changed")

    rows: list[dict[str, Any]] = []
    for commit in commits:
        authored_at, subject = git(
            history_root, "show", "-s", "--format=%aI%x09%s", commit
        ).rstrip("\n").split("\t", 1)
        paths = git(history_root, "ls-tree", "-r", "--name-only", commit).splitlines()
        structured = [path for path in paths if path.lower().endswith(STRUCTURED_SUFFIXES)]
        schema_or_config = [
            path
            for path in structured
            if "/config/" in path
            or path.endswith("/persistent/account.json")
            or path.endswith("/persistent/date.json")
            or path.endswith("/template.csv")
            or path.endswith("/template.json")
        ]
        index_series = [path for path in structured if "/persistent/index_data/" in path]
        result_paths = [
            path
            for path in paths
            if any(part in RESULT_PATH_PARTS for part in path.lower().split("/"))
            or path.lower().endswith((".ckpt", ".npy", ".npz", ".parquet", ".pickle", ".pkl", ".pt", ".pth", ".safetensors"))
        ]
        unclassified_structured = sorted(set(structured) - set(schema_or_config) - set(index_series))
        literal_hits: list[str] = []
        for path in paths:
            if path in index_series or path.lower().endswith((".pdf", ".png")):
                continue
            text = git_bytes(history_root, "show", f"{commit}:{path}").decode(
                "utf-8", errors="ignore"
            )
            literal_hits.extend(
                f"{path}:{literal}" for literal in PAPER_RESULT_LITERALS if literal in text
            )
        if result_paths or unclassified_structured or literal_hits:
            raise ValueError(
                f"AlphaCrafter history contains an unreviewed artifact at {commit}: "
                f"result={result_paths}, structured={unclassified_structured}, "
                f"paper_literals={literal_hits}"
            )
        rows.append(
            {
                "commit": commit,
                "authored_at": authored_at,
                "subject": subject,
                "tracked_paths": len(paths),
                "python_paths": sum(path.endswith(".py") for path in paths),
                "schema_or_config_structured_paths": len(schema_or_config),
                "index_series_paths": len(index_series),
                "unclassified_structured_paths": 0,
                "agent_result_or_run_artifact_paths": 0,
                "paper_result_literal_hits_outside_index_inputs": 0,
                "paper_result_artifact_found": False,
            }
        )
    return rows


def public_fork_audit(
    history_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Exhaust every dated public fork ref and fail closed on result-shaped payloads."""
    if git(history_root, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise ValueError("AlphaCrafter public-fork history checkout is shallow")
    official = git(history_root, "rev-parse", "refs/remotes/origin/main").strip()
    if official != REPOSITORY_HEAD:
        raise ValueError("AlphaCrafter official history ref changed")

    actual_refs = {}
    for line in git(
        history_root,
        "for-each-ref",
        "--format=%(refname)%09%(objectname)",
        "refs/remotes/forks",
    ).splitlines():
        refname, commit = line.split("\t")
        actual_refs[refname] = commit
    expected_refs = {
        f"refs/remotes/forks/{repository.split('/', 1)[0]}/{branch}": commit
        for repository, branch, commit, _relation, _ahead, _behind in PUBLIC_FORK_BRANCHES
    }
    if actual_refs != expected_refs:
        raise ValueError(
            f"AlphaCrafter public-fork branch refs changed: {actual_refs} != {expected_refs}"
        )
    if git(history_root, "for-each-ref", "--format=%(refname)", "refs/tags").strip():
        raise ValueError("AlphaCrafter public-fork clone unexpectedly contains tag refs")

    branch_rows = []
    repositories_by_head: dict[str, list[str]] = {}
    relation_by_head: dict[str, tuple[str, int, int]] = {}
    for repository, branch, commit, relation, ahead, behind in PUBLIC_FORK_BRANCHES:
        refname = f"refs/remotes/forks/{repository.split('/', 1)[0]}/{branch}"
        observed_behind, observed_ahead = map(
            int,
            git(
                history_root,
                "rev-list",
                "--left-right",
                "--count",
                f"{official}...{commit}",
            ).split(),
        )
        if (observed_ahead, observed_behind) != (ahead, behind):
            raise ValueError(f"AlphaCrafter fork relationship changed for {repository}")
        merge_base = git(history_root, "merge-base", official, commit).strip()
        observed_relation = (
            "official_head_exact"
            if commit == official
            else "official_history_ancestor"
            if merge_base == commit
            else "divergent"
        )
        if observed_relation != relation:
            raise ValueError(f"AlphaCrafter fork classification changed for {repository}")
        branch_rows.append(
            {
                "repository": repository,
                "url": f"https://github.com/{repository}",
                "branch": branch,
                "refname": refname,
                "head_commit": commit,
                "relation_to_official_head": relation,
                "commits_ahead_of_official": ahead,
                "commits_behind_official": behind,
                "tag_refs": 0,
                "native_result_artifact_found": False,
                "paper_result_credit": False,
            }
        )
        repositories_by_head.setdefault(commit, []).append(repository)
        relation_by_head[commit] = (relation, ahead, behind)

    divergent_commits = git(
        history_root, "rev-list", "--reverse", f"{KLEAMEND_BASE}..{KLEAMEND_HEAD}"
    ).splitlines()
    if len(divergent_commits) != 17 or divergent_commits[-1] != KLEAMEND_HEAD:
        raise ValueError("AlphaCrafter divergent fork history changed")
    if git(history_root, "merge-base", official, KLEAMEND_HEAD).strip() != KLEAMEND_BASE:
        raise ValueError("AlphaCrafter divergent fork merge base changed")
    if sha256_bytes(
        git_bytes(history_root, "diff", "--binary", KLEAMEND_BASE, KLEAMEND_HEAD)
    ) != KLEAMEND_CUMULATIVE_DIFF_SHA256:
        raise ValueError("AlphaCrafter divergent fork cumulative diff changed")

    commit_rows = []
    changed_union: set[str] = set()
    headline_literal_hits: list[str] = []
    seen_blobs: set[str] = set()
    for sequence, commit in enumerate(divergent_commits, start=1):
        metadata = git(
            history_root,
            "show",
            "-s",
            "--format=%aI%x1f%an%x1f%ae%x1f%s",
            commit,
        ).rstrip("\n").split("\x1f")
        if len(metadata) != 4 or metadata[1] != "kleamend":
            raise ValueError(f"AlphaCrafter divergent commit metadata changed: {commit}")
        changed = sorted(
            set(
                git(
                    history_root,
                    "show",
                    "--format=",
                    "--name-only",
                    commit,
                ).splitlines()
            )
        )
        changed_union.update(changed)
        fixtures_changed = sorted(set(changed) & set(KLEAMEND_SYNTHETIC_FIXTURE_SHA256))
        for path in changed:
            tree_line = git(history_root, "ls-tree", commit, "--", path).strip()
            if not tree_line:
                continue
            blob_id = tree_line.split()[2]
            if blob_id in seen_blobs:
                continue
            seen_blobs.add(blob_id)
            text = git_bytes(history_root, "show", f"{commit}:{path}").decode(
                "utf-8", errors="ignore"
            )
            headline_literal_hits.extend(
                f"{commit}:{path}:{literal}"
                for literal in PAPER_RESULT_LITERALS
                if literal in text
            )
        commit_rows.append(
            {
                "sequence": sequence,
                "commit": commit,
                "authored_at": metadata[0],
                "author_name": metadata[1],
                "author_email": metadata[2],
                "subject": metadata[3],
                "changed_paths": len(changed),
                "synthetic_test_fixture_paths_changed": ";".join(fixtures_changed),
                "native_result_artifact_paths": 0,
                "paper_result_literal_hits": 0,
                "classification": (
                    "adds_synthetic_display_parser_test_fixtures_no_native_output"
                    if fixtures_changed
                    else "implementation_or_documentation_change_no_native_output"
                ),
                "paper_result_credit": False,
            }
        )
    if headline_literal_hits:
        raise ValueError(
            f"AlphaCrafter divergent fork contains paper headline literals: {headline_literal_hits}"
        )
    structured_changed = {
        path for path in changed_union if path.lower().endswith(STRUCTURED_SUFFIXES)
    }
    if structured_changed != KLEAMEND_STRUCTURED_CHANGED_PATHS:
        raise ValueError(
            f"AlphaCrafter divergent structured path surface changed: {structured_changed}"
        )
    current_changed = set(
        git(
            history_root, "diff", "--name-only", KLEAMEND_BASE, KLEAMEND_HEAD
        ).splitlines()
    )
    transient_paths = sorted(changed_union - current_changed)
    if len(changed_union) != 144 or len(current_changed) != 141 or transient_paths != [
        "display/src/components/ConsoleShell.tsx",
        "display/src/components/HeroConsole.module.css",
        "display/src/components/HeroConsole.tsx",
    ]:
        raise ValueError("AlphaCrafter divergent fork changed-path inventory changed")
    for path, expected_hash in KLEAMEND_SYNTHETIC_FIXTURE_SHA256.items():
        if sha256_bytes(git_bytes(history_root, "show", f"{KLEAMEND_HEAD}:{path}")) != expected_hash:
            raise ValueError(f"AlphaCrafter synthetic fixture changed: {path}")
    parser_test = git_bytes(
        history_root,
        "show",
        f"{KLEAMEND_HEAD}:display/src/test/log-parser.test.ts",
    ).decode("utf-8")
    for marker in (
        'const FIXTURES_DIR = path.join(__dirname, "fixtures")',
        "fs.mkdtemp",
        'copyFixture("backtest_results.json"',
        'toBe(1.25)',
        'toBe(5.42)',
    ):
        if marker not in parser_test:
            raise ValueError("AlphaCrafter fork fixture/test relationship changed")
    backtest_fixture = json.loads(
        git_bytes(
            history_root,
            "show",
            f"{KLEAMEND_HEAD}:display/src/test/fixtures/backtest_results.json",
        )
    )
    expected_metrics = {
        "Total Return (%)": 5.42,
        "Annualized Return (%)": 12.3,
        "Sharpe Ratio": 1.25,
        "Max Drawdown (%)": -3.1,
        "Calmar Ratio": 3.97,
        "Average Gross Position Rate (%)": 65.4,
        "Average Net Position Rate (%)": 50.2,
    }
    if len(backtest_fixture) != 1 or backtest_fixture[0]["metrics"] != expected_metrics:
        raise ValueError("AlphaCrafter divergent display test metrics changed")
    if KLEAMEND_PROFILE_SNAPSHOT["name"] in PAPER_AUTHORS:
        raise ValueError("AlphaCrafter fork profile unexpectedly matches a paper author")

    unique_rows = []
    for commit in sorted(repositories_by_head):
        relation, ahead, behind = relation_by_head[commit]
        is_divergent = commit == KLEAMEND_HEAD
        unique_rows.append(
            {
                "head_commit": commit,
                "repositories": ";".join(sorted(repositories_by_head[commit])),
                "branch_ref_count": len(repositories_by_head[commit]),
                "relation_to_official_head": relation,
                "commits_ahead_of_official": ahead,
                "commits_behind_official": behind,
                "merge_base": git(history_root, "merge-base", official, commit).strip(),
                "extra_commits_audited": 17 if is_divergent else 0,
                "changed_paths_across_extra_history": 144 if is_divergent else 0,
                "synthetic_display_test_fixture_paths": 6 if is_divergent else 0,
                "profile_name_matches_paper_author": False if is_divergent else "not_applicable",
                "classification": (
                    "same_institution_claim_unlisted_person_ui_runtime_adaptation_synthetic_test_fixtures"
                    if is_divergent
                    else relation
                ),
                "native_result_artifact_found": False,
                "paper_result_credit": False,
            }
        )
    if len(unique_rows) != PUBLIC_FORK_UNIQUE_HEAD_COUNT:
        raise ValueError("AlphaCrafter public-fork unique head count changed")
    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": PUBLIC_FORK_REST_COUNT,
        "accessible_public_forks": len(PUBLIC_FORK_BRANCHES),
        "accessible_branch_refs": len(branch_rows),
        "tag_refs": PUBLIC_FORK_TAG_REF_COUNT,
        "unique_heads": len(unique_rows),
        "official_history_reachable_unique_heads": 3,
        "divergent_unique_heads": 1,
        "divergent_repository": KLEAMEND_REPOSITORY,
        "divergent_head_extra_commits_audited": len(divergent_commits),
        "divergent_head_changed_paths_across_history": len(changed_union),
        "divergent_head_current_changed_paths": len(current_changed),
        "divergent_head_transient_changed_paths": transient_paths,
        "divergent_owner_profile_snapshot": KLEAMEND_PROFILE_SNAPSHOT,
        "same_institution_claim_is_not_paper_author_identity_evidence": True,
        "divergent_structured_changed_paths": len(structured_changed),
        "divergent_synthetic_display_test_fixtures": len(
            KLEAMEND_SYNTHETIC_FIXTURE_SHA256
        ),
        "divergent_display_fixture_metrics": expected_metrics,
        "display_fixture_role": (
            "test-only parser fixture copied into a temporary test session; values are not "
            "linked to an AlphaCrafter experiment, paper table, factor pool, market-data "
            "snapshot, action ledger, holdings, returns, or model-call lineage"
        ),
        "paper_headline_literal_hits_in_divergent_history": 0,
        "native_result_artifacts_found": 0,
        "exact_paper_result_table_or_figure_paths_discovered": 0,
        "paper_result_credit": False,
    }
    return branch_rows, unique_rows, commit_rows, summary


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
        for member in v2_members:
            extracted = scratch / "build-v2" / member.name
            stream = archive.extractfile(member)
            if not extracted.is_file() or stream is None or extracted.read_bytes() != stream.read():
                raise ValueError(f"v2 build source differs from official archive: {member.name}")
    if (len(v1_members), sum(item.size for item in v1_members)) != (25, 1_848_965):
        raise ValueError("v1 source inventory changed")
    if (len(v2_members), sum(item.size for item in v2_members)) != (22, 1_574_465):
        raise ValueError("v2 source inventory changed")
    with zipfile.ZipFile(scratch / "discovery/alphacrafter-c6dbc1b.zip") as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
    if (len(files), sum(item.file_size for item in files)) != (79, 889_614):
        raise ValueError("attributable repository archive inventory changed")
    return {
        "v1_source_files": 25,
        "v2_source_files": 22,
        "v2_build_source_matches_archive": True,
        "release_files": 79,
    }


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
        ("v2", "official_document_source", "complete", "22-file primary source recovered unchanged; four pdfLaTeX passes plus BibTeX converge to a 22-page PDF matching the official manuscript"),
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
            "rebuilt_pages": 22,
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
        ("v2_source_build", "complete", "unmodified official source builds in four pdfLaTeX passes plus BibTeX; the CJK package takes about 45 seconds to initialize on the shared TeX installation, so earlier attempts were interrupted prematurely"),
        ("repository_attribution", "strong_but_not_direct", "NJU-LINK repository cites the exact paper and authors and matches the method, but the paper itself does not link it"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def v2_build_verification(scratch: Path) -> dict[str, Any]:
    """Verify the converged unmodified-source build and its visual QA evidence."""
    expected_log_markers = {
        "build-v2-pass1-complete.txt": ("Output written on main.pdf (19 pages", "elapsed=0:59.91 exit=0"),
        "build-v2-bibtex-complete.txt": ("Database file #1: ref.bib", "elapsed=0:00.08 exit=0"),
        "build-v2-pass2-complete.txt": ("Output written on main.pdf (22 pages", "elapsed=0:45.75 exit=0"),
        "build-v2-pass3-complete.txt": ("Output written on main.pdf (22 pages", "elapsed=0:50.61 exit=0"),
        "build-v2-pass4-complete.txt": ("Output written on main.pdf (22 pages", "elapsed=0:51.85 exit=0"),
    }
    for relative, markers in expected_log_markers.items():
        text = (scratch / relative).read_text(errors="replace")
        if not all(marker in text for marker in markers):
            raise ValueError(f"successful v2 build evidence changed: {relative}")

    metrics = json.loads((scratch / "v2-render-diff-metrics.json").read_text())
    if len(metrics) != 22 or [row["page"] for row in metrics] != list(range(1, 23)):
        raise ValueError("v2 page-comparison inventory changed")
    if any(row["size"] != [745, 1053] for row in metrics):
        raise ValueError("v2 render dimensions changed")
    max_mean_absolute_difference = max(max(row["mean_abs_rgb"]) for row in metrics)
    max_root_mean_square_difference = max(max(row["rms_rgb"]) for row in metrics)
    if max_mean_absolute_difference > 2.81 or max_root_mean_square_difference > 7.55:
        raise ValueError("v2 official/rebuilt raster correspondence changed")

    return {
        "official_source_tree_files": 22,
        "official_source_tree_modified_for_build": False,
        "build_engine": "pdfLaTeX (TeX Live 2024) plus BibTeX",
        "pdf_latex_passes": 4,
        "bibtex_passes": 1,
        "successful_pass_page_counts": [19, 22, 22, 22],
        "converged_on_pdf_latex_pass": 4,
        "auxiliary_state_stable_between_passes_3_and_4": True,
        "final_pdf_sha256": PINS["build-v2/main.pdf"],
        "official_pages": 22,
        "rebuilt_pages": 22,
        "manuscript_token_comparison": {
            "official_tokens_including_arxiv_overlay_and_date": 11_513,
            "rebuilt_tokens_including_build_date": 11_507,
            "expected_date_replacement": {
                "official": "2026-07-29",
                "rebuilt": "2026-08-14",
            },
            "expected_official_only_arxiv_overlay_tokens": [
                "arxiv", "2605.05580v2", "cs.ai", "28", "jul", "2026",
            ],
            "all_manuscript_tokens_match_after_expected_metadata_differences": True,
        },
        "visual_comparison": {
            "pages_compared": 22,
            "render_pixel_size": [745, 1053],
            "maximum_mean_absolute_channel_difference": max_mean_absolute_difference,
            "maximum_root_mean_square_channel_difference": max_root_mean_square_difference,
            "unreadable_clipped_overlapping_or_missing_elements": 0,
            "layout_tables_figures_pagination_match": True,
            "expected_visible_differences": [
                "arXiv side stamp on official page 1",
                "build-date header on page 1",
            ],
        },
    }


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
rebuilds to 26 visually sound pages. The unmodified official v2 source also builds:
four pdfLaTeX passes plus BibTeX converge to 22 pages after allowing roughly 45
seconds for the CJK package to initialize on Bouchet's shared TeX installation.
All 22 rebuilt pages match the official layout, tables, figures, and pagination.
Tokenized manuscript text is identical after excluding the official PDF's arXiv
side stamp and the expected build-date header difference.

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

The complete non-shallow repository history has 13 commits, one branch, no tags,
and no releases. Every revision is inventoried. The only structured payloads are
configuration/schema templates and, after the second commit, two index series;
no revision contains an agent result/run artifact, checkpoint, mined factor pool,
decision, prediction, signal, holding, order/fill record, or result array.
Seven distinctive v2 result literals also have zero occurrences outside the two
index input series.

The complete public-fork surface reported by GitHub on 2026-08-14 contains six
accessible forks, six branch refs, no tags, and four unique heads. Three heads are
the official head or official-history ancestors. The sole divergent head is a
17-commit `kleamend/AlphaCrafter` adaptation. Its owner profile says Nanjing
University but names Yongjian Zhang, who is not one of the five paper authors;
same-institution self-description is not author identity evidence. All 17 revisions
and 144 changed paths were checked. They add a display console, documentation,
localization, and a MiniMax chat-agent adaptation. The only result-shaped payloads
are six JSON files under `display/src/test/fixtures`, explicitly copied into a
temporary Vitest session to test a log parser. Their return, Sharpe, drawdown, and
Calmar values have no experiment identifier, inputs, action/holding/return lineage,
or paper-table correspondence. They are synthetic parser fixtures, not native
AlphaCrafter output, and receive zero result credit.

Accordingly, the honest paper-level score is **0/176 v1 and 0/304 v2 published
numeric result units, and 0/16 v1 and 0/14 v2 empirical panels regenerated**.
The native component checks materially improve implementation faithfulness, but
no source rebuild, synthetic fixture, or local narrative proxy receives paper-result
credit. The older `alphacrafter_full_stack_multifactor` portfolio remains a clearly
labeled secondary motif translation, not an AlphaCrafter replication.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inventory = validate_inputs(scratch)
    document_build = v2_build_verification(scratch)
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
    write_json(output / "document_build_verification.json", document_build)
    history = source_history_rows(scratch / "discovery/alphacrafter-history")
    write_csv(output / "released_source_history_inventory.csv", history)
    fork_branches, fork_heads, fork_commits, fork_summary = public_fork_audit(
        scratch / "discovery/alphacrafter-history"
    )
    write_csv(output / "public_fork_branch_ref_snapshot.csv", fork_branches)
    write_csv(output / "public_fork_unique_head_inventory.csv", fork_heads)
    write_csv(output / "public_fork_divergent_commit_inventory.csv", fork_commits)
    write_json(output / "public_fork_census.json", fork_summary)
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
                "rebuilt_pages_inspected": {"v1": 26, "v2": 22},
                "unreadable_clipped_or_overlapping_pages": 0,
                "contact_sheet_sha256": {
                    "v1_official": PINS["viz/v1-official-contact.jpg"],
                    "v2_official": PINS["viz/v2-official-contact.jpg"],
                    "v1_rebuilt": PINS["viz/v1-rebuilt-contact.jpg"],
                    "v2_rebuilt": PINS["viz/v2-rebuilt-contact.jpg"],
                },
                "v2_side_by_side_contact_sheet_sha256": [
                    PINS[f"viz/v2-side-by-side/contact-{index:02d}.jpg"]
                    for index in range(1, 7)
                ],
            },
            "v2_build_boundary": (
                "complete unmodified source; four pdfLaTeX passes plus BibTeX "
                "converged after allowing the CJK package's roughly 45-second initialization"
            ),
            "v2_build_verification": document_build,
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
            "full_public_history_audited": True,
            "public_history_commits": len(history),
            "historical_agent_result_or_run_artifacts": sum(
                row["agent_result_or_run_artifact_paths"] for row in history
            ),
            "historical_paper_result_literal_hits_outside_index_inputs": sum(
                row["paper_result_literal_hits_outside_index_inputs"] for row in history
            ),
        },
        "public_fork_boundary": fork_summary,
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
        "v2_document_rebuild_completed": True,
        "v2_rebuild_blocker": None,
        "v2_rebuild_note": (
            "unmodified source converged after four pdfLaTeX passes plus BibTeX; "
            "CJK initialization requires roughly 45 seconds"
        ),
        "v2_build_source_matches_official_archive": inventory[
            "v2_build_source_matches_archive"
        ],
        "v2_rebuilt_pdf_sha256": document_build["final_pdf_sha256"],
        "v2_rebuilt_manuscript_tokens_match": document_build[
            "manuscript_token_comparison"
        ]["all_manuscript_tokens_match_after_expected_metadata_differences"],
        "official_pages_visually_checked": 48,
        "rebuilt_pages_visually_checked": 48,
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
        "repository_history_commits_audited": len(history),
        "repository_history_unclassified_structured_paths": sum(
            row["unclassified_structured_paths"] for row in history
        ),
        "repository_history_agent_result_or_run_artifact_paths": sum(
            row["agent_result_or_run_artifact_paths"] for row in history
        ),
        "repository_history_paper_result_artifacts_found": sum(
            bool(row["paper_result_artifact_found"]) for row in history
        ),
        "repository_history_paper_result_literal_hits_outside_index_inputs": sum(
            row["paper_result_literal_hits_outside_index_inputs"] for row in history
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
        "public_fork_divergent_commits_audited": fork_summary[
            "divergent_head_extra_commits_audited"
        ],
        "public_fork_native_result_artifacts_found": False,
        "public_fork_paper_result_credit": False,
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
