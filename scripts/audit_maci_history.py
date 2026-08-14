#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


def git(repo: Path, *args: str, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return result.stdout


def digest_lines(lines: list[str]) -> str:
    payload = "".join(f"{line}\n" for line in sorted(lines)).encode()
    return hashlib.sha256(payload).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(repo: Path) -> dict:
    commits = git(repo, "rev-list", "--all").splitlines()
    commit_dates = git(
        repo,
        "log",
        "--all",
        "--format=%H%x09%aI%x09%cI%x09%an%x09%ae",
    ).splitlines()
    roots = git(repo, "rev-list", "--all", "--max-parents=0").splitlines()
    refs = git(repo, "for-each-ref", "--format=%(refname)%09%(objectname)").splitlines()
    branches = [
        line
        for line in refs
        if line.startswith("refs/remotes/origin/") and not line.startswith("refs/remotes/origin/HEAD")
    ]
    local_branches = [line for line in refs if line.startswith("refs/heads/")]
    tags = [line for line in refs if line.startswith("refs/tags/")]

    object_lines = git(repo, "rev-list", "--objects", "--all").splitlines()
    object_ids = [line.split(" ", 1)[0] for line in object_lines]
    proc = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        input="".join(f"{oid}\n" for oid in object_ids),
        check=True,
        capture_output=True,
        text=True,
    )
    object_records = proc.stdout.splitlines()
    object_types = Counter(line.split()[1] for line in object_records)
    object_bytes = Counter()
    for line in object_records:
        _oid, kind, size = line.split()
        object_bytes[kind] += int(size)

    # Parse every historical path/object pair from raw, no-rename diffs.
    raw = git(
        repo,
        "log",
        "--all",
        "--format=commit%x09%H",
        "--raw",
        "--no-abbrev",
        "--no-renames",
        "--root",
    ).splitlines()
    path_object_records: list[str] = []
    changed_paths: set[str] = set()
    deleted_paths: set[str] = set()
    current_commit = ""
    for line in raw:
        if line.startswith("commit\t"):
            current_commit = line.split("\t", 1)[1]
            continue
        if not line.startswith(":"):
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        old_oid, new_oid, status = parts[2], parts[3], parts[4]
        changed_paths.add(path)
        if status == "D":
            deleted_paths.add(path)
        path_object_records.append(f"{current_commit}\t{status}\t{old_oid}\t{new_oid}\t{path}")

    current_paths = set(git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    historically_absent_now = sorted(changed_paths - current_paths)
    current_files = []
    for path in sorted(repo.rglob("*")):
        if (
            not path.is_file()
            or ".git" in path.relative_to(repo).parts
            or "__pycache__" in path.relative_to(repo).parts
        ):
            continue
        rel = path.relative_to(repo).as_posix()
        current_files.append(f"{rel}\t{path.stat().st_size}\t{file_sha(path)}")

    return {
        "repository": str(repo),
        "head": git(repo, "rev-parse", "HEAD").strip(),
        "shallow": git(repo, "rev-parse", "--is-shallow-repository").strip() == "true",
        "commit_count": len(commits),
        "commit_set_sha256": digest_lines(commits),
        "commit_metadata_sha256": digest_lines(commit_dates),
        "oldest_author_date": min(line.split("\t")[1] for line in commit_dates),
        "latest_author_date": max(line.split("\t")[1] for line in commit_dates),
        "oldest_committer_date": min(line.split("\t")[2] for line in commit_dates),
        "latest_committer_date": max(line.split("\t")[2] for line in commit_dates),
        "roots": sorted(roots),
        "refs": sorted(refs),
        "ref_sha256": digest_lines(refs),
        "local_branch_count": len(local_branches),
        "remote_branch_count": len(branches),
        "tag_count": len(tags),
        "reachable_object_count": len(object_ids),
        "reachable_object_set_sha256": digest_lines(object_ids),
        "object_type_counts": dict(sorted(object_types.items())),
        "object_type_bytes": dict(sorted(object_bytes.items())),
        "object_record_sha256": digest_lines(object_records),
        "unique_historical_path_count": len(changed_paths),
        "unique_historical_path_sha256": digest_lines(list(changed_paths)),
        "historical_path_object_revision_count": len(path_object_records),
        "historical_path_object_revision_sha256": digest_lines(path_object_records),
        "paths_deleted_at_least_once_count": len(deleted_paths),
        "paths_deleted_at_least_once": sorted(deleted_paths),
        "historical_paths_absent_from_head_count": len(historically_absent_now),
        "historical_paths_absent_from_head": historically_absent_now,
        "current_tracked_path_count": len(current_paths),
        "current_tracked_path_sha256": digest_lines(list(current_paths)),
        "current_non_git_non_cache_file_count": len(current_files),
        "current_non_git_non_cache_file_manifest_sha256": digest_lines(current_files),
    }


def object_bytes(repo: Path, revision_path: str) -> bytes:
    return git(repo, "show", revision_path, binary=True)


def text_content(value):
    if isinstance(value, str):
        return value
    return "\n".join(item.get("text", "") for item in value if item.get("type") == "text")


def training_records(repo: Path) -> dict:
    added_commit = "3236cd6929707315315f76240ec2f930e1e4f43f"
    removed_commit = "0203a30817d258aad8afe92d9a044982619cfece"
    paths = (
        "test/single_cs_0510.jsonl",
        "test/single_mkt_0510.jsonl",
        "test/test.jsonl",
    )
    rows = []
    for path in paths:
        data = object_bytes(repo, f"{added_commit}:{path}")
        records = [json.loads(line) for line in data.splitlines() if line.strip()]
        roles = Counter()
        labels = Counter()
        weeks = Counter()
        system_hashes = Counter()
        user_hashes = Counter()
        assistant_hashes = Counter()
        image_urls = []
        malformed = []
        for index, record in enumerate(records):
            messages = record.get("messages", [])
            roles.update(message.get("role", "") for message in messages)
            if [message.get("role") for message in messages] != ["system", "user", "assistant"]:
                malformed.append(index)
                continue
            system = text_content(messages[0].get("content"))
            user = text_content(messages[1].get("content"))
            assistant = text_content(messages[2].get("content"))
            system_hashes[hashlib.sha256(system.encode()).hexdigest()] += 1
            user_hashes[hashlib.sha256(user.encode()).hexdigest()] += 1
            assistant_hashes[hashlib.sha256(assistant.encode()).hexdigest()] += 1
            match = re.search(r"(?:Price|Market) trend:\s*(Rise|Fall)", assistant, re.I)
            labels[match.group(1).title() if match else "unparsed"] += 1
            content = messages[1].get("content")
            if isinstance(content, list):
                for item in content:
                    if item.get("type") != "image_url":
                        continue
                    url = item.get("image_url", {}).get("url", "")
                    image_urls.append(url)
                    week = re.search(r"_(\d{4})_(\d{1,2})\.png(?:$|\?)", url)
                    if week:
                        weeks[f"{week.group(1)}-W{int(week.group(2)):02d}"] += 1
        rows.append(
            {
                "path": path,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "records": len(records),
                "message_role_counts": dict(sorted(roles.items())),
                "malformed_record_indexes": malformed,
                "assistant_label_counts": dict(sorted(labels.items())),
                "unique_system_prompts": len(system_hashes),
                "system_prompt_sha256_counts": dict(sorted(system_hashes.items())),
                "unique_user_payloads": len(user_hashes),
                "unique_assistant_payloads": len(assistant_hashes),
                "image_url_count": len(image_urls),
                "unique_image_url_count": len(set(image_urls)),
                "image_week_count": len(weeks),
                "image_week_min": min(weeks) if weeks else None,
                "image_week_max": max(weeks) if weeks else None,
                "intended_role": "fine_tuning_message_records",
                "paper_result_credit": False,
            }
        )
    addition = git(
        repo,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        f"{added_commit}^",
        added_commit,
        "--",
        *paths,
    ).splitlines()
    deletion = git(
        repo,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        f"{removed_commit}^",
        removed_commit,
        "--",
        *paths,
    ).splitlines()
    if addition != [f"A\t{path}" for path in paths] or deletion != [f"D\t{path}" for path in paths]:
        raise ValueError("historical MACI training-record add/delete lineage changed")
    return {
        "added_commit": added_commit,
        "added_commit_author_date": git(repo, "show", "-s", "--format=%aI", added_commit).strip(),
        "removed_commit": removed_commit,
        "removed_commit_author_date": git(repo, "show", "-s", "--format=%aI", removed_commit).strip(),
        "addition_status": addition,
        "deletion_status": deletion,
        "files": rows,
        "total_records": sum(row["records"] for row in rows),
        "qualification": "These are complete fine-tuning-format message records recovered from public Git history, but the exact upload/job/selected checkpoint and test predictions remain absent.",
        "paper_result_credit": False,
    }


def v3_missing_module_history(repo: Path) -> dict[str, bool]:
    return {
        path: bool(git(repo, "log", "--all", "--format=%H", "--", path).strip())
        for path in (
            "environ/data/coingecko.py",
            "environ/data/cointelegraph.py",
            "environ/data/rag_store.py",
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repos", nargs="+", type=Path)
    args = parser.parse_args()
    if len(args.repos) != 2:
        raise ValueError("expected v1/v2 multi-agent repo and v3 cryptoMAS repo")
    v1, v3 = (repo.resolve() for repo in args.repos)
    v1_summary = summarize(v1)
    v3_summary = summarize(v3)
    v1_summary["repository"] = "https://github.com/lyc0603/multi-agent"
    v3_summary["repository"] = "https://github.com/lyc0603/cryptoMAS"
    print(
        json.dumps(
            {
                "v1_v2_repository_history": v1_summary,
                "v1_v2_deleted_training_records": training_records(v1),
                "v3_repository_history": v3_summary,
                "v3_missing_module_paths_present_in_any_commit": v3_missing_module_history(v3),
                "result_regeneration_credit": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
