#!/usr/bin/env python3
"""Build a static, reproducible artifact audit for the frozen system census.

This script deliberately does *not* install, import, or execute third-party
artifacts.  It records public availability, reachability, immutable Git HEADs,
observable licenses, and static package completeness only.  R0--R3 therefore
describe packaged materials, not empirical or native-execution fidelity.
"""
from __future__ import annotations

import argparse
import base64
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import urllib.error
import urllib.parse
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = REPO_ROOT / "literature_review" / "census_v1" / "system_registry.csv"
DEFAULT_OUT_DIR = REPO_ROOT / "paper_runs" / "artifact_audit"
EXPECTED_STRATA = {"F": 29, "T": 38, "B": 23, "C": 5, "M": 8}
EXPECTED_TOTAL = 103
EXPECTED_MAIN_FT = 67
WILSON_Z_95 = 1.959963984540054

URL_RE = re.compile(r"https?://[^;\s]+")
GITHUB_HOSTS = {"github.com", "www.github.com"}
CODE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".ipynb", ".java", ".jl", ".js",
    ".jsx", ".lua", ".m", ".py", ".r", ".rb", ".rs", ".scala", ".sh",
    ".sql", ".swift", ".ts", ".tsx",
}
ENVIRONMENT_NAMES = {
    "dockerfile", "environment.yml", "environment.yaml", "package.json",
    "pipfile", "poetry.lock", "pyproject.toml", "requirements.txt", "setup.cfg",
    "setup.py", "uv.lock",
}
RUNNER_NAMES = {
    "app.py", "cli.py", "main.py", "makefile", "run.py", "start.sh", "train.py",
}
STRONG_NONRUNNABLE_PHRASES = (
    "does not contain a runnable version",
    "pseudocode and algorithms",
    "pseudo-code and algorithms",
    "code will be released",
)
WEAK_NONRUNNABLE_PHRASES = (
    "coming soon",
)


def explicitly_nonrunnable(readme_lower: str, has_code: bool, has_runner: bool) -> bool:
    """Avoid treating a roadmap heading as a verdict on an otherwise runnable repo."""
    if any(phrase in readme_lower for phrase in STRONG_NONRUNNABLE_PHRASES):
        return True
    return (
        any(phrase in readme_lower for phrase in WEAK_NONRUNNABLE_PHRASES)
        and not has_code
        and not has_runner
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_manifest_path(path: Path) -> str:
    """Record repository paths without leaking a machine-specific checkout root."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return f"external_input:{resolved.name}"


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


class ProbeCache:
    """Small JSON cache for HTTP, git, and derived archive observations."""

    def __init__(self, path: Path, offline: bool, refresh: bool) -> None:
        self.path = path
        self.offline = offline
        self.refresh = refresh
        self.entries: Dict[str, Dict[str, Any]] = {}
        self.dirty = False
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("schema_version") != 1 or not isinstance(payload.get("entries"), dict):
                    raise ValueError("unsupported cache schema")
                self.entries = payload["entries"]
            except Exception as exc:  # cache corruption must be explicit, not silently ignored
                raise ValueError(f"could not read cache {path}: {exc}") from exc

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if self.refresh and not self.offline:
            return None
        value = self.entries.get(key)
        return dict(value) if value is not None else None

    def put(self, key: str, value: Mapping[str, Any]) -> Dict[str, Any]:
        result = dict(value)
        self.entries[key] = result
        self.dirty = True
        return result

    def miss(self, key: str) -> Dict[str, Any]:
        return {
            "cache_key": key,
            "cache_miss": True,
            "checked_at_utc": utc_now(),
            "error": "offline_cache_miss",
        }

    def save(self) -> None:
        if self.dirty:
            atomic_json(
                self.path,
                {
                    "schema_version": 1,
                    "updated_at_utc": utc_now(),
                    "entries": self.entries,
                },
            )


def fetch_http(
    url: str,
    cache: ProbeCache,
    timeout: float,
    user_agent: str,
    max_bytes: int = 512 * 1024,
    extra_headers: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    headers = {"User-Agent": user_agent, "Accept": "*/*"}
    if extra_headers:
        headers.update(extra_headers)
    key = "http:get:{}:{}:{}".format(url, max_bytes, compact_json(headers))
    cached = cache.get(key)
    if cached is not None:
        cached["from_cache"] = True
        return cached
    if cache.offline:
        return cache.miss(key)

    result: Dict[str, Any] = {
        "cache_key": key,
        "checked_at_utc": utc_now(),
        "requested_url": url,
        "from_cache": False,
    }
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes + 1)
            truncated = len(body) > max_bytes
            if truncated:
                body = body[:max_bytes]
            result.update(
                {
                    "status": int(response.status),
                    "final_url": response.geturl(),
                    "content_type": response.headers.get("Content-Type", ""),
                    "body_b64": base64.b64encode(body).decode("ascii"),
                    "body_truncated": truncated,
                    "reachable": 200 <= int(response.status) < 400,
                }
            )
    except urllib.error.HTTPError as exc:
        body = exc.read(max_bytes)
        result.update(
            {
                "status": int(exc.code),
                "final_url": exc.geturl(),
                "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
                "body_b64": base64.b64encode(body).decode("ascii"),
                "body_truncated": False,
                "reachable": False,
                "error": "HTTPError: {}".format(exc),
                "definitive_unreachable": int(exc.code) in {404, 410},
            }
        )
    except Exception as exc:
        result.update({"reachable": None, "error": "{}: {}".format(type(exc).__name__, exc)})
    return cache.put(key, result)


def decoded_body(response: Mapping[str, Any]) -> bytes:
    encoded = response.get("body_b64")
    if not encoded:
        return b""
    try:
        return base64.b64decode(encoded)
    except Exception:
        return b""


def split_urls(raw: str) -> List[str]:
    return URL_RE.findall(raw or "")


def url_type(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if host in GITHUB_HOSTS and len([part for part in parsed.path.split("/") if part]) >= 2:
        return "github_repository"
    if host == "huggingface.co" and path.startswith("/spaces/"):
        return "huggingface_space"
    if host == "huggingface.co" and path.startswith("/collections/"):
        return "huggingface_collection"
    if host.endswith("4open.science"):
        return "anonymous_code_snapshot"
    if "demo" in path or host.startswith("demo.") or host in {"paradoox.cn", "ama.thefin.ai"}:
        return "demo_or_live_endpoint"
    if host.endswith("github.io") or "lab" in path or "project" in path:
        return "project_page"
    return "public_web_artifact"


def github_owner_repo(url: str) -> Optional[Tuple[str, str]]:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() not in GITHUB_HOSTS:
        return None
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    return parts[0], re.sub(r"\.git$", "", parts[1])


def probe_git_head(
    url: str,
    cache: ProbeCache,
    timeout: float,
) -> Dict[str, Any]:
    key = "git:ls-remote:{}".format(url)
    cached = cache.get(key)
    if cached is not None:
        cached["from_cache"] = True
        return cached
    if cache.offline:
        return cache.miss(key)
    result: Dict[str, Any] = {
        "cache_key": key,
        "checked_at_utc": utc_now(),
        "from_cache": False,
        "command": ["git", "ls-remote", "--symref", url, "HEAD"],
    }
    try:
        completed = subprocess.run(
            result["command"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result.update(
            {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr[-4000:],
            }
        )
        branch = ""
        sha = ""
        for line in completed.stdout.splitlines():
            if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
                branch = line[len("ref: refs/heads/") : -len("\tHEAD")]
            elif line.endswith("\tHEAD") and re.match(r"^[0-9a-fA-F]{40}\tHEAD$", line):
                sha = line.split("\t", 1)[0].lower()
        result.update(
            {
                "default_branch": branch,
                "head_sha": sha,
                "reachable": completed.returncode == 0 and bool(sha),
            }
        )
        if not result["reachable"]:
            result["error"] = "git_ls_remote_failed"
    except Exception as exc:
        result.update({"reachable": None, "error": "{}: {}".format(type(exc).__name__, exc)})
    return cache.put(key, result)


def archive_static_observation(
    owner: str,
    repo: str,
    sha: str,
    cache: ProbeCache,
    timeout: float,
    user_agent: str,
    max_archive_bytes: int,
) -> Dict[str, Any]:
    key = "github:codeload:{}\u002f{}@{}:{}".format(owner, repo, sha, max_archive_bytes)
    cached = cache.get(key)
    if cached is not None:
        cached["from_cache"] = True
        return cached
    if cache.offline:
        return cache.miss(key)
    url = "https://codeload.github.com/{}/{}/tar.gz/{}".format(owner, repo, sha)
    result: Dict[str, Any] = {
        "cache_key": key,
        "checked_at_utc": utc_now(),
        "requested_url": url,
        "from_cache": False,
    }
    request = urllib.request.Request(url, headers={"User-Agent": user_agent}, method="GET")
    try:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as temporary:
            total = 0
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result["status"] = int(response.status)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_archive_bytes:
                        raise ValueError("archive_exceeds_max_bytes:{}".format(max_archive_bytes))
                    temporary.write(chunk)
            temporary.flush()
            result["archive_bytes"] = total
            code_markers: List[str] = []
            environment_markers: List[str] = []
            runner_markers: List[str] = []
            support_markers: List[str] = []
            readme_text = ""
            license_text = ""
            with tarfile.open(temporary.name, mode="r:gz") as archive:
                members = [member for member in archive.getmembers() if member.isfile()]
                result["file_count"] = len(members)
                for member in members:
                    raw_parts = [part for part in member.name.split("/") if part]
                    relative = "/".join(raw_parts[1:] if len(raw_parts) > 1 else raw_parts)
                    lower = relative.lower()
                    base = lower.rsplit("/", 1)[-1]
                    suffix = Path(base).suffix
                    if suffix in CODE_SUFFIXES:
                        code_markers.append(relative)
                    if (
                        base in ENVIRONMENT_NAMES
                        or base.startswith("requirements") and base.endswith(".txt")
                        or base.startswith("dockerfile")
                    ):
                        environment_markers.append(relative)
                    if (
                        base in RUNNER_NAMES
                        or re.match(r"^(run|train|eval|evaluate|start)[_-].*\.(py|sh|r|jl)$", base)
                        or lower.startswith("scripts/") and suffix in CODE_SUFFIXES
                    ):
                        runner_markers.append(relative)
                    if (
                        lower.startswith(("test/", "tests/", "example/", "examples/", "config/", "configs/"))
                        or "sample" in base
                    ):
                        support_markers.append(relative)
                    if not readme_text and base in {"readme", "readme.md", "readme.rst", "readme.txt"}:
                        extracted = archive.extractfile(member)
                        if extracted:
                            readme_text = extracted.read(256 * 1024).decode("utf-8", errors="replace")
                    if not license_text and (
                        base == "license" or base.startswith("license.") or base.startswith("copying")
                    ):
                        extracted = archive.extractfile(member)
                        if extracted:
                            license_text = extracted.read(256 * 1024).decode("utf-8", errors="replace")
            readme_lower = readme_text.lower()
            result.update(
                {
                    "reachable": True,
                    "has_code": bool(code_markers),
                    "has_environment": bool(environment_markers),
                    "has_runner": bool(runner_markers),
                    "has_support": bool(support_markers),
                    "code_markers": sorted(code_markers)[:20],
                    "environment_markers": sorted(environment_markers)[:20],
                    "runner_markers": sorted(runner_markers)[:20],
                    "support_markers": sorted(support_markers)[:20],
                    "explicit_nonrunnable": explicitly_nonrunnable(
                        readme_lower, bool(code_markers), bool(runner_markers)
                    ),
                    "readme_excerpt": readme_text[:20000],
                    "license_excerpt": license_text[:50000],
                }
            )
    except urllib.error.HTTPError as exc:
        result.update(
            {
                "status": int(exc.code),
                "reachable": False,
                "definitive_unreachable": int(exc.code) in {404, 410},
                "error": "HTTPError: {}".format(exc),
            }
        )
    except Exception as exc:
        result.update({"reachable": None, "error": "{}: {}".format(type(exc).__name__, exc)})
    return cache.put(key, result)


def detect_license(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.lower())
    rules = [
        ("AGPL-3.0", ("gnu affero general public license",)),
        ("GPL-3.0", ("gnu general public license", "version 3")),
        ("Apache-2.0", ("apache license", "version 2.0")),
        ("MIT", ("mit license", "permission is hereby granted, free of charge")),
        ("BSD-3-Clause", ("redistribution and use in source and binary forms", "neither the name")),
        ("BSD-2-Clause", ("redistribution and use in source and binary forms", "disclaimer")),
        ("MPL-2.0", ("mozilla public license version 2.0",)),
        ("CC-BY-NC-SA-4.0", ("creative commons attribution-noncommercial-sharealike",)),
        ("CC-BY-4.0", ("creative commons attribution 4.0",)),
    ]
    for identifier, needles in rules:
        if all(needle in normalized for needle in needles):
            return identifier
    return "NOASSERTION"


def probe_github_license(
    owner: str,
    repo: str,
    branch: str,
    archive: Mapping[str, Any],
    cache: ProbeCache,
    timeout: float,
    user_agent: str,
) -> Dict[str, Any]:
    errors: List[str] = []
    api_url = "https://api.github.com/repos/{}/{}/license".format(owner, repo)
    api = fetch_http(
        api_url,
        cache,
        timeout,
        user_agent,
        extra_headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    )
    if api.get("reachable"):
        try:
            payload = json.loads(decoded_body(api).decode("utf-8", errors="replace"))
            license_info = payload.get("license") or {}
            observed = license_info.get("spdx_id") or license_info.get("name") or "NOASSERTION"
            if observed not in {"NOASSERTION", "Other", ""}:
                return {"license": observed, "source": "github_api", "errors": errors}
            content = payload.get("content")
            if content:
                detected = detect_license(base64.b64decode(content).decode("utf-8", errors="replace"))
                if detected != "NOASSERTION":
                    return {"license": detected, "source": "github_api_content", "errors": errors}
        except Exception as exc:
            errors.append("github_api_parse:{}".format(exc))
    elif api.get("error"):
        errors.append(str(api["error"]))

    quoted_branch = urllib.parse.quote(branch or "HEAD", safe="")
    for filename in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        raw_url = "https://raw.githubusercontent.com/{}/{}/{}/{}".format(
            owner, repo, quoted_branch, filename
        )
        raw = fetch_http(raw_url, cache, timeout, user_agent, max_bytes=256 * 1024)
        if raw.get("reachable"):
            detected = detect_license(decoded_body(raw).decode("utf-8", errors="replace"))
            return {"license": detected, "source": "raw:{}".format(filename), "errors": errors}
        if raw.get("error") and raw.get("status") not in {404}:
            errors.append(str(raw["error"]))

    archive_license = str(archive.get("license_excerpt") or "")
    if archive_license:
        return {
            "license": detect_license(archive_license),
            "source": "static_archive_fallback",
            "errors": errors,
        }
    return {"license": "NOASSERTION", "source": "not_observed", "errors": errors}


def github_url_audit(
    url: str,
    cache: ProbeCache,
    timeout: float,
    user_agent: str,
    max_archive_bytes: int,
) -> Dict[str, Any]:
    owner_repo = github_owner_repo(url)
    if owner_repo is None:
        raise ValueError("not a GitHub repository URL: {}".format(url))
    owner, repo = owner_repo
    head = probe_git_head(url, cache, timeout)
    result: Dict[str, Any] = {
        "url": url,
        "url_type": "github_repository",
        "github_owner_repo": "{}/{}".format(owner, repo),
        "check_method": "git ls-remote --symref",
        "checked_at_utc": head.get("checked_at_utc", utc_now()),
        "reachable": head.get("reachable"),
        "default_branch": head.get("default_branch", ""),
        "head_sha": head.get("head_sha", ""),
        "errors": [],
    }
    if head.get("error"):
        result["errors"].append(str(head["error"]))
    if head.get("error") == "offline_cache_miss":
        result["offline_cache_miss"] = True
    if not head.get("reachable") and not cache.offline:
        fallback = fetch_http(url, cache, timeout, user_agent, max_bytes=128 * 1024)
        result["http_status"] = fallback.get("status")
        if fallback.get("reachable"):
            result["reachable"] = True
            result["check_method"] += "; HTTP fallback"
        elif fallback.get("definitive_unreachable"):
            result["reachable"] = False
            result["definitive_unreachable"] = True
        elif fallback.get("error"):
            result["errors"].append(str(fallback["error"]))

    archive: Dict[str, Any] = {}
    if head.get("head_sha"):
        archive = archive_static_observation(
            owner,
            repo,
            str(head["head_sha"]),
            cache,
            timeout,
            user_agent,
            max_archive_bytes,
        )
        result["static_observation"] = {
            key: archive.get(key)
            for key in (
                "archive_bytes", "file_count", "has_code", "has_environment", "has_runner",
                "has_support", "explicit_nonrunnable", "code_markers", "environment_markers",
                "runner_markers", "support_markers", "checked_at_utc", "error",
            )
            if key in archive
        }
        if archive.get("error"):
            result["errors"].append(str(archive["error"]))
    license_result = probe_github_license(
        owner,
        repo,
        str(head.get("default_branch") or "HEAD"),
        archive,
        cache,
        timeout,
        user_agent,
    )
    result.update(
        {
            "observed_license": license_result["license"],
            "license_source": license_result["source"],
        }
    )
    result["errors"].extend(license_result.get("errors", []))
    return result


def generic_url_audit(
    url: str,
    cache: ProbeCache,
    timeout: float,
    user_agent: str,
) -> Dict[str, Any]:
    response = fetch_http(url, cache, timeout, user_agent, max_bytes=128 * 1024)
    result: Dict[str, Any] = {
        "url": url,
        "url_type": url_type(url),
        "check_method": "HTTP GET (bounded body)",
        "checked_at_utc": response.get("checked_at_utc", utc_now()),
        "reachable": response.get("reachable"),
        "http_status": response.get("status"),
        "final_url": response.get("final_url", ""),
        "errors": [],
    }
    if response.get("definitive_unreachable"):
        result["definitive_unreachable"] = True
    if response.get("error"):
        result["errors"].append(str(response["error"]))
    if response.get("error") == "offline_cache_miss":
        result["offline_cache_miss"] = True
    return result


def aggregate_reachability(results: Sequence[Mapping[str, Any]], listed: bool) -> str:
    if not listed:
        return "not_listed"
    values = [result.get("reachable") for result in results]
    if values and all(value is True for value in values):
        return "reachable_all"
    if any(value is True for value in values):
        return "reachable_some"
    if any(result.get("offline_cache_miss") for result in results):
        return "offline_cache_miss"
    if values and all(
        value is False and result.get("definitive_unreachable")
        for value, result in zip(values, results)
    ):
        return "unreachable_all"
    return "check_failed"


def static_fidelity(results: Sequence[Mapping[str, Any]], reachability: str) -> Tuple[str, Dict[str, Any]]:
    definition = {
        "R0": "no listed public artifact or no reachable artifact",
        "R1": "reachable landing page, documentation, pseudocode, or statically incomplete repository",
        "R2": "observable source code plus dependency/setup manifest",
        "R3": "R2 plus a runner and tests/examples/configuration support",
    }
    if reachability in {"not_listed", "unreachable_all", "check_failed", "offline_cache_miss"}:
        return "R0", {"definition": definition, "basis": reachability}
    best = "R1"
    evidence: List[Dict[str, Any]] = []
    for result in results:
        if result.get("reachable") is not True:
            continue
        observation = result.get("static_observation") or {}
        if not observation:
            evidence.append({"url": result.get("url"), "tier": "R1", "basis": "reachable_non_code_or_uninspected"})
            continue
        if observation.get("explicit_nonrunnable"):
            tier = "R1"
            basis = "repository explicitly describes materials as non-runnable/pseudocode"
        elif observation.get("has_code") and observation.get("has_environment"):
            if observation.get("has_runner") and observation.get("has_support"):
                tier = "R3"
                basis = "code+environment+runner+tests/examples/config"
            else:
                tier = "R2"
                basis = "code+environment manifest"
        else:
            tier = "R1"
            basis = "missing code or dependency/setup manifest"
        if int(tier[1]) > int(best[1]):
            best = tier
        evidence.append({"url": result.get("url"), "tier": tier, "basis": basis, "markers": observation})
    return best, {"definition": definition, "evidence": evidence}


def failure_category(listed: bool, reachability: str, tier: str, results: Sequence[Mapping[str, Any]]) -> str:
    if not listed:
        return "no_public_artifact"
    if reachability == "offline_cache_miss":
        return "offline_cache_miss"
    if reachability == "unreachable_all":
        return "artifact_unreachable"
    if reachability == "check_failed":
        return "reachability_check_failed"
    if reachability == "reachable_some":
        return "partial_reachability"
    if tier == "R1":
        if any((result.get("static_observation") or {}).get("explicit_nonrunnable") for result in results):
            return "explicitly_nonrunnable_or_pseudocode"
        if any(result.get("url_type") == "github_repository" for result in results):
            return "static_package_insufficient"
        return "reachable_non_code_artifact"
    return "none"


def load_registry(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="|"))
    required = {"system_id", "system_name", "stratum", "main_FT", "official_artifact"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("registry is missing required columns: {}".format(sorted(required)))
    ids = [row["system_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("system_id values are not unique")
    strata = {key: 0 for key in EXPECTED_STRATA}
    for row in rows:
        if row["stratum"] not in strata:
            raise ValueError("unknown stratum {!r}".format(row["stratum"]))
        strata[row["stratum"]] += 1
        expected_main = "Y" if row["stratum"] in {"F", "T"} else "N"
        if row["main_FT"] != expected_main:
            raise ValueError("main_FT mismatch for {}".format(row["system_id"]))
    main_count = sum(row["main_FT"] == "Y" for row in rows)
    if len(rows) != EXPECTED_TOTAL or strata != EXPECTED_STRATA or main_count != EXPECTED_MAIN_FT:
        raise ValueError(
            "registry is not the frozen 103-row census: n={}, strata={}, F+T={}".format(
                len(rows), strata, main_count
            )
        )
    return rows


def audit_row(
    row: Mapping[str, str],
    cache: ProbeCache,
    timeout: float,
    user_agent: str,
    max_archive_bytes: int,
    audit_timestamp: str,
) -> Dict[str, Any]:
    raw_artifacts = row.get("official_artifact", "").strip()
    urls = split_urls(raw_artifacts)
    listed = bool(urls)
    results: List[Dict[str, Any]] = []
    for url in urls:
        if github_owner_repo(url):
            results.append(github_url_audit(url, cache, timeout, user_agent, max_archive_bytes))
        else:
            results.append(generic_url_audit(url, cache, timeout, user_agent))
    reachability = aggregate_reachability(results, listed)
    tier, tier_basis = static_fidelity(results, reachability)
    github_repos = [str(result.get("github_owner_repo")) for result in results if result.get("github_owner_repo")]
    heads = [
        "{}@{}={}".format(
            result.get("github_owner_repo"),
            result.get("default_branch") or "HEAD",
            result.get("head_sha"),
        )
        for result in results
        if result.get("github_owner_repo") and result.get("head_sha")
    ]
    licenses = [
        "{}={}".format(result.get("github_owner_repo"), result.get("observed_license"))
        for result in results
        if result.get("github_owner_repo")
    ]
    errors = [
        {"url": result.get("url"), "errors": result.get("errors")}
        for result in results
        if result.get("errors")
    ]
    return {
        "system_id": row["system_id"],
        "system_name": row["system_name"],
        "stratum": row["stratum"],
        "main_FT": row["main_FT"],
        "artifact_urls": raw_artifacts,
        "artifact_url_count": len(urls),
        "artifact_url_types": ";".join(url_type(url) for url in urls),
        "public_artifact_listed": "Y" if listed else "N",
        "reachability_outcome": reachability,
        "github_owner_repos": ";".join(github_repos),
        "default_branch_head_shas": ";".join(heads),
        "observed_licenses": ";".join(licenses),
        "static_fidelity_tier": tier,
        "static_fidelity_basis_json": compact_json(tier_basis),
        "failure_category": failure_category(listed, reachability, tier, results),
        "native_execution_attempted": "N",
        "audit_timestamp_utc": audit_timestamp,
        "artifact_url_results_json": compact_json(results),
        "errors_json": compact_json(errors),
    }


def wilson_interval(successes: int, total: int) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if total <= 0:
        return None, None, None
    proportion = successes / total
    z2 = WILSON_Z_95 * WILSON_Z_95
    denominator = 1.0 + z2 / total
    center = (proportion + z2 / (2.0 * total)) / denominator
    half_width = WILSON_Z_95 * math.sqrt(
        proportion * (1.0 - proportion) / total + z2 / (4.0 * total * total)
    ) / denominator
    return proportion, max(0.0, center - half_width), min(1.0, center + half_width)


def summary_rows(audit_rows: Sequence[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    groups: List[Tuple[str, List[Mapping[str, Any]]]] = []
    for stratum in ("F", "T", "B", "C", "M"):
        groups.append((stratum, [row for row in audit_rows if row["stratum"] == stratum]))
    groups.append(("F+T", [row for row in audit_rows if row["main_FT"] == "Y"]))
    groups.append(("ALL", list(audit_rows)))

    long_rows: List[Dict[str, Any]] = []
    json_groups: Dict[str, Any] = {}
    for group_name, rows in groups:
        listed = [row for row in rows if row["public_artifact_listed"] == "Y"]
        reachable = [row for row in rows if str(row["reachability_outcome"]).startswith("reachable_")]
        metrics = [
            ("public_artifact_listed", len(listed), len(rows)),
            ("artifact_reachable_among_all", len(reachable), len(rows)),
            (
                "artifact_reachable_given_listed",
                sum(str(row["reachability_outcome"]).startswith("reachable_") for row in listed),
                len(listed),
            ),
            (
                "github_head_resolved_among_all",
                sum(bool(row["default_branch_head_shas"]) for row in rows),
                len(rows),
            ),
            (
                "static_R2_or_R3_among_all",
                sum(row["static_fidelity_tier"] in {"R2", "R3"} for row in rows),
                len(rows),
            ),
            ("static_R3_among_all", sum(row["static_fidelity_tier"] == "R3" for row in rows), len(rows)),
        ]
        metric_payload: Dict[str, Any] = {}
        for metric, successes, total in metrics:
            proportion, lower, upper = wilson_interval(int(successes), int(total))
            record = {
                "group": group_name,
                "metric": metric,
                "successes": int(successes),
                "denominator": int(total),
                "proportion": proportion,
                "wilson_95_lower": lower,
                "wilson_95_upper": upper,
                "z": WILSON_Z_95,
            }
            long_rows.append(record)
            metric_payload[metric] = record
        json_groups[group_name] = {
            "n_systems": len(rows),
            "metrics": metric_payload,
            "static_fidelity_counts": {
                tier: sum(row["static_fidelity_tier"] == tier for row in rows)
                for tier in ("R0", "R1", "R2", "R3")
            },
            "reachability_counts": dict(sorted(_counts(row["reachability_outcome"] for row in rows).items())),
            "failure_category_counts": dict(sorted(_counts(row["failure_category"] for row in rows).items())),
        }
    return long_rows, json_groups


def _counts(values: Iterable[Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--cache-file",
        type=Path,
        help="JSON probe cache; defaults to OUT_DIR/artifact_audit_cache.json",
    )
    parser.add_argument("--offline", action="store_true", help="Use cache only; make no HTTP or git calls")
    parser.add_argument("--refresh", action="store_true", help="Refresh cached probes when online")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-archive-bytes", type=int, default=50 * 1024 * 1024)
    parser.add_argument(
        "--user-agent",
        default="alpha-agent-replication-artifact-audit/1.0 (public research audit; no author contact)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.timeout <= 0:
        raise ValueError("--timeout must be positive")
    if args.max_archive_bytes <= 0:
        raise ValueError("--max-archive-bytes must be positive")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = args.cache_file or args.out_dir / "artifact_audit_cache.json"
    registry_rows = load_registry(args.registry)
    audit_timestamp = utc_now()
    cache = ProbeCache(cache_path, offline=args.offline, refresh=args.refresh)
    audited: List[Dict[str, Any]] = []
    try:
        for index, row in enumerate(registry_rows, start=1):
            print("[{}/{}] {}".format(index, len(registry_rows), row["system_id"]))
            audited.append(
                audit_row(
                    row,
                    cache,
                    args.timeout,
                    args.user_agent,
                    args.max_archive_bytes,
                    audit_timestamp,
                )
            )
    finally:
        cache.save()

    audit_fields = [
        "system_id", "system_name", "stratum", "main_FT", "artifact_urls",
        "artifact_url_count", "artifact_url_types", "public_artifact_listed",
        "reachability_outcome", "github_owner_repos", "default_branch_head_shas",
        "observed_licenses", "static_fidelity_tier", "static_fidelity_basis_json",
        "failure_category", "native_execution_attempted", "audit_timestamp_utc",
        "artifact_url_results_json", "errors_json",
    ]
    audit_csv = args.out_dir / "artifact_audit.csv"
    audit_json = args.out_dir / "artifact_audit.json"
    summary_csv = args.out_dir / "artifact_audit_summary.csv"
    summary_json = args.out_dir / "artifact_audit_summary.json"
    atomic_csv(audit_csv, audited, audit_fields)
    long_summary, grouped_summary = summary_rows(audited)
    summary_fields = [
        "group", "metric", "successes", "denominator", "proportion",
        "wilson_95_lower", "wilson_95_upper", "z",
    ]
    atomic_csv(summary_csv, long_summary, summary_fields)
    metadata = {
        "schema_version": 1,
        "audit_timestamp_utc": audit_timestamp,
        "registry_path": portable_manifest_path(args.registry),
        "registry_sha256": sha256_file(args.registry),
        "registry_rows": len(registry_rows),
        "expected_stratum_counts": EXPECTED_STRATA,
        "expected_main_F_plus_T": EXPECTED_MAIN_FT,
        "offline": bool(args.offline),
        "cache_path": portable_manifest_path(cache_path),
        "network_timeout_seconds": args.timeout,
        "max_archive_bytes": args.max_archive_bytes,
        "native_execution_attempted": False,
        "author_contact_attempted": False,
        "authentication_tokens_used": False,
        "fidelity_scope": "static observable package materials only; not native execution or empirical replication",
        "wilson_method": {
            "confidence": 0.95,
            "z": WILSON_Z_95,
            "formula": "Wilson score interval without continuity correction",
        },
    }
    atomic_json(audit_json, {"metadata": metadata, "rows": audited})
    atomic_json(summary_json, {"metadata": metadata, "groups": grouped_summary})
    print(audit_csv)
    print(audit_json)
    print(summary_csv)
    print(summary_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
