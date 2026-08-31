#!/usr/bin/env python3
"""Build a fail-closed, multi-version audit for the MACI crypto paper.

The arXiv identifier contains two materially different experiments.  Versions
1--2 use a four-expert, fine-tuned GPT-4o system and 2023--2024 data.  Version 3
replaces that study with three multi-agent architectures, four capability
variants, three model families, and calendar-2025 data.  This builder keeps the
lineages separate and never promotes document reconstruction, printed-value
arithmetic, component execution, or author-output correspondence into an
end-to-end paper-result reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import unquote, urlparse
from zipfile import ZipFile

from PIL import Image


EXPECTED = {
    "v1_pdf": "e6ac85d8805726811860b07281b7f4f9792918c0f5d664f31feb6d2238b30907",
    "v2_pdf": "14013a9d2af7585e00c8f3fcada0a745df15d3abf5fbd9adba03e64c408e7909",
    "v3_pdf": "cc2652f2f0a38e7b15e99734514381c759c803f90b2768696a568959675e0b27",
    "v1_source_tar": "3118bd36447fef00b39c80866e965bd6f436be53207cf457e72581c20e6b12c6",
    "v2_source_tar": "f4fae077906e28f97a0037235e4f9cf191c6c7994c5a92581b3dd9ff95b2fd74",
    "v3_source_tar": "3e7e9e020707bec1de3d7888715020a28d6a48377c874e5897f09016ca295a49",
    "v1_rebuild": "554e93a00877026967f9925bc18c0de0e20d73f0c73096984329af3ab741840b",
    "v2_rebuild": "9dda60dcf280d58a05cfd339d7e84ad10d9845af46a9283b1afc3b7bf8cabb3d",
    "v3_rebuild": "540b9fba5ba9d7e4be035bd2c1ddf0dbda094bdf362312c210ba43b132039a5d",
    "fama_french_archive": "cd6d8e0d175b6f423862a6ad15a3073a6e4264b52b2ac9262396c79f707c6bcb",
    "author_v1_commit": "962b83d7ca8908e675fc22c6d16ce24a0ec3e52f",
    "author_current_commit": "2326185cc2d1eff02724cfeb88116ebb13f904e7",
    "author_v3_commit": "318e0fe905fed8b7f544322c3db1dfed6784d178",
    "anonymous_v3_readme": "fd1c5988cf2d27d93497b551d115d781b2da210f3213a71cdeb274b9581da433",
    "v1_v2_history_commit_set": "e7e7218ac3bf00415de19596586d4188bed73b2124216f9471293ce672b39753",
    "v1_v2_history_object_set": "65af5077c6e1a03e87a908c11f50ad64e34692b3439eafa03fa0a32d22dd9c1d",
    "v1_v2_history_path_revisions": "1983e160d71489d63546a32c36655775b0b90d01bbd42fb8e8f29d3cda1b0496",
    "v3_history_commit_set": "d531309de21fb51322bf85c734fb80315cfdfb0d5338ba94dc8c4970801db2da",
    "v3_history_object_set": "96ad4d440559f4e3dc4085aee80e1eca95af1b6a001ec3dae46f596f38f1b338",
    "v3_history_path_revisions": "f5492d298fd8dda02571a575ec6646d5eb1c8f095f33de20037e8e70e7a10bef",
}

V1_V2_REPOSITORY = "https://github.com/lyc0603/multi-agent"
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
TRAINING_RECORDS_COMMIT = "3236cd6929707315315f76240ec2f930e1e4f43f"
TRAINING_RECORDS_REMOVAL_COMMIT = "0203a30817d258aad8afe92d9a044982619cfece"
TRAINING_JSONL_PINS = {
    "test/single_cs_0510.jsonl": (
        1_935_323,
        "7b5fdd8ec44f631657e3211868bdd77da22991c0ae3e508d6a2082462ee055ee",
        930,
    ),
    "test/single_mkt_0510.jsonl": (
        520_246,
        "ef7e0a5b7de4fd7ebc0e10e3fa7f6b3a64cad10ed46c150fe25afa835a242452",
        31,
    ),
    "test/test.jsonl": (
        2_068,
        "c2cef4f998ad056d68a4e7a8d4c66ac0953d591b106be15fda0c7040d3ae8dba",
        1,
    ),
}
TRAINING_IMAGE_MANIFEST_SHA256 = (
    "64d6cea8f5d3c5b52f720b9daa12764c440a2e652ac38da3c6baeb8422148f7b"
)
PUBLIC_FORK_HEADS = {
    "refs/remotes/forks/gelove/main": "2326185cc2d1eff02724cfeb88116ebb13f904e7",
    "refs/remotes/forks/jemxgw/main": "3ed387b3683d57eab04d36e1f18f3e49fdfc0bec",
}

FLOAT_RE = re.compile(r"(?<![\w])[-+]?\d+\.\d+")
METRICS_V1 = ("Mean", "Std", "Sharpe")
VARIANTS_V1 = ("single_gpt4o_raw", "single_gpt4o_fine_tuned", "multi_agent")
METRICS_V3 = ("Cum_pct", "Avg_pct", "Vol_pct", "SR", "MDD_pct", "Win_pct")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    ).stdout


def public_fork_audit(author_current: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Classify every public v1/v2 fork head against the audited official history."""
    if git(author_current, "rev-parse", "--is-shallow-repository") != "false":
        raise ValueError("v1/v2 fork-audit checkout is shallow")
    origin = git(author_current, "remote", "get-url", "origin")
    if origin.removesuffix(".git") != V1_V2_REPOSITORY:
        raise ValueError(f"v1/v2 fork-audit origin changed: {origin}")
    if git(author_current, "rev-parse", "refs/remotes/origin/main") != EXPECTED["author_current_commit"]:
        raise ValueError("v1/v2 official main head changed")

    fork_refs: dict[str, str] = {}
    for line in git(
        author_current,
        "for-each-ref",
        "--format=%(refname)%09%(objectname)",
        "refs/remotes/forks",
    ).splitlines():
        refname, head = line.split("\t")
        fork_refs[refname] = head
    if fork_refs != PUBLIC_FORK_HEADS:
        raise ValueError(f"MACI public-fork refs changed: {fork_refs}")

    official_commits = set(git(author_current, "rev-list", EXPECTED["author_current_commit"]).splitlines())
    if len(official_commits) != 164:
        raise ValueError(f"v1/v2 official history count changed: {len(official_commits)}")
    repositories = {
        "refs/remotes/forks/gelove/main": "gelove/multi-agent",
        "refs/remotes/forks/jemxgw/main": "jemxgw/multi-agent",
    }
    rows = []
    for refname, head in sorted(fork_refs.items()):
        ahead = int(git(author_current, "rev-list", "--count", head, "--not", EXPECTED["author_current_commit"]))
        behind = int(git(author_current, "rev-list", "--count", f"{head}..{EXPECTED['author_current_commit']}"))
        if head == EXPECTED["author_current_commit"]:
            relation = "official_head_exact"
        elif head in official_commits:
            relation = "official_history_ancestor"
        else:
            relation = "divergent_from_official_history"
        if ahead or relation == "divergent_from_official_history":
            raise ValueError(f"MACI fork adds unreviewed history: {refname} at {head}")
        rows.append(
            {
                "repository": repositories[refname],
                "url": f"https://github.com/{repositories[refname]}",
                "branch": "main",
                "head_commit": head,
                "relation_to_official_head": relation,
                "commits_ahead_of_official": ahead,
                "commits_behind_official": behind,
                "tag_refs": 0,
                "unique_commits_beyond_official_history": 0,
                "unique_blobs_beyond_official_history": 0,
                "native_result_artifact_found": False,
                "paper_result_credit": False,
            }
        )
    expected_relations = {
        ("gelove/multi-agent", "official_head_exact", 0),
        ("jemxgw/multi-agent", "official_history_ancestor", 3),
    }
    observed_relations = {
        (row["repository"], row["relation_to_official_head"], row["commits_behind_official"])
        for row in rows
    }
    if observed_relations != expected_relations:
        raise ValueError(f"MACI fork relations changed: {observed_relations}")
    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "official_repository": "lyc0603/multi-agent",
        "official_history_commits": len(official_commits),
        "github_rest_reported_forks": 2,
        "accessible_public_forks": len(rows),
        "accessible_branch_refs": len(rows),
        "tag_refs": 0,
        "unique_heads": len({row["head_commit"] for row in rows}),
        "official_head_exact_unique_heads": 1,
        "official_history_ancestor_unique_heads": 1,
        "divergent_unique_heads": 0,
        "unique_commits_beyond_official_history": 0,
        "unique_blobs_beyond_official_history": 0,
        "native_result_artifacts_found": 0,
        "paper_result_credit": False,
        "interpretation": (
            "both accessible public forks resolve entirely inside the complete audited "
            "164-commit official history: one is exact at the official head and the other "
            "is three official commits behind, so neither adds a commit, blob, tag, or "
            "native result lineage"
        ),
    }
    return rows, summary


def numbers(line: str) -> list[float]:
    return [float(value) for value in FLOAT_RE.findall(line)]


def data_lines(path: Path, required: str) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if required in line and line.rstrip().endswith(r"\\")
    ]


def result_row(
    version: str,
    table: str,
    category: str,
    strategy: str,
    subgroup: str,
    regime: str,
    metric: str,
    value: float,
    kind: str = "direct_result",
    native: bool = False,
    duplicate: str = "",
) -> dict[str, Any]:
    return {
        "paper_version": version,
        "experimental_lineage": "v1_v2_gpt4o_four_expert_2023_2024"
        if version == "v1/v2"
        else "v3_three_architecture_calendar_2025",
        "table": table,
        "category": category,
        "strategy_or_variant": strategy,
        "subgroup": subgroup,
        "regime_or_portfolio": regime,
        "metric": metric,
        "published_value": value,
        "cell_kind": kind,
        "native_maci_output": native,
        "duplicate_measurement_group": duplicate,
        "author_output_verified": False,
        "native_regenerated_value": "",
        "paper_result_credit": False,
        "note": "Printed paper value only; no released input-to-result lineage regenerates this cell.",
    }


def parse_v1_acc(path: Path) -> list[dict[str, Any]]:
    lines = data_lines(path, "databar{")
    if len(lines) != 6:
        raise ValueError(f"classification row count changed: {len(lines)}")
    experts = ("Crypto Factor", "Technical", "Collaboration", "Market Factor", "News", "Collaboration")
    rows = []
    for index, (line, expert) in enumerate(zip(lines, experts)):
        values = numbers(line)
        if len(values) != 6:
            raise ValueError(f"classification cell count changed: {line}")
        category = "crypto_prediction" if index < 3 else "market_prediction"
        for variant_index, variant in enumerate(VARIANTS_V1):
            for metric_index, metric in enumerate(("Accuracy", "MCC")):
                rows.append(
                    result_row(
                        "v1/v2",
                        "classification",
                        category,
                        variant,
                        expert,
                        "test",
                        metric,
                        values[variant_index * 2 + metric_index],
                        native=variant == "multi_agent",
                    )
                )
    return rows


def parse_v1_market_returns(path: Path) -> list[dict[str, Any]]:
    rows = []
    for regime in ("Rise", "Fall", "Diff"):
        line = next(item for item in path.read_text(encoding="utf-8").splitlines() if rf"\textbf{{{regime}}}" in item)
        values = numbers(line)
        if len(values) != 3:
            raise ValueError(f"market-return cell count changed: {line}")
        for variant, value in zip(VARIANTS_V1, values):
            rows.append(
                result_row(
                    "v1/v2",
                    "market_rise_fall",
                    "market_team_financial_significance",
                    variant,
                    "market_prediction",
                    regime,
                    "weekly_mean_return",
                    value,
                    kind="derived_difference" if regime == "Diff" else "direct_result",
                    native=variant == "multi_agent",
                )
            )
    return rows


def parse_v1_portfolio(path: Path) -> list[dict[str, Any]]:
    lines = data_lines(path, "textcolor")
    if len(lines) != 12:
        raise ValueError(f"portfolio row count changed: {len(lines)}")
    periods = ("All",) * 4 + ("Boom",) * 4 + ("Bust",) * 4
    strategies = ("Ours", "Market", "1/N", "Bitcoin") * 3
    rows = []
    for line, period, strategy in zip(lines, periods, strategies):
        values = numbers(line)
        if len(values) != 3:
            raise ValueError(f"portfolio cell count changed: {line}")
        for metric, value in zip(METRICS_V1, values):
            rows.append(
                result_row(
                    "v1/v2",
                    "portfolio",
                    "portfolio_performance",
                    strategy,
                    "weekly",
                    period,
                    metric,
                    value,
                    native=strategy == "Ours",
                )
            )
    return rows


def parse_v1_asset_pricing(path: Path) -> list[dict[str, Any]]:
    lines = data_lines(path, "databar{")
    if len(lines) != 18:
        raise ValueError(f"LLM asset-pricing row count changed: {len(lines)}")
    expert_groups = ("Crypto Factor",) * 6 + ("Technical",) * 6 + ("Collaboration",) * 6
    portfolios = ("Very Low", "Low", "Medium", "High", "Very High", "HML") * 3
    rows = []
    for line, expert, portfolio in zip(lines, expert_groups, portfolios):
        values = numbers(line)
        if len(values) != 9:
            raise ValueError(f"LLM asset-pricing cell count changed: {line}")
        for variant_index, variant in enumerate(VARIANTS_V1):
            for metric_index, metric in enumerate(METRICS_V1):
                rows.append(
                    result_row(
                        "v1/v2",
                        "llm_asset_pricing",
                        "quintile_and_hml",
                        variant,
                        expert,
                        portfolio,
                        metric,
                        values[variant_index * 3 + metric_index],
                        native=variant == "multi_agent",
                    )
                )
    return rows


def parse_v1_traditional(path: Path) -> list[dict[str, Any]]:
    lines = data_lines(path, "databar{")
    if len(lines) != 6:
        raise ValueError(f"traditional-factor row count changed: {len(lines)}")
    portfolios = ("Very Low", "Low", "Medium", "High", "Very High", "HML")
    factors = ("MOM_1_0", "MOM_4_0", "MOM_4_1")
    rows = []
    for line, portfolio in zip(lines, portfolios):
        values = numbers(line)
        if len(values) != 9:
            raise ValueError(f"traditional-factor cell count changed: {line}")
        for factor_index, factor in enumerate(factors):
            for metric_index, metric in enumerate(METRICS_V1):
                rows.append(
                    result_row(
                        "v1/v2",
                        "traditional_asset_pricing",
                        "cited_risk_factor_baseline",
                        factor,
                        "top_factor",
                        portfolio,
                        metric,
                        values[factor_index * 3 + metric_index],
                    )
                )
    return rows


def parse_v1_ablation(path: Path) -> list[dict[str, Any]]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if (r"\CIRCLE" in line or r"\Circle" in line) and line.rstrip().endswith(r"\\")
    ]
    if len(lines) != 6:
        raise ValueError(f"v1 ablation row count changed: {len(lines)}")
    variants = (
        "full_system",
        "minus_crypto_factor",
        "minus_technical",
        "minus_market_factor",
        "minus_news",
        "minus_interteam_collaboration",
    )
    metrics = ("Cumulative", "Mean", "Std", "Sharpe")
    rows = []
    for line, variant in zip(lines, variants):
        values = numbers(line)
        if len(values) != 4:
            raise ValueError(f"v1 ablation cell count changed: {line}")
        for metric, value in zip(metrics, values):
            duplicate = ""
            if variant == "full_system" and metric in METRICS_V1:
                duplicate = f"v1_full_system_{metric.lower()}"
            rows.append(
                result_row(
                    "v1/v2",
                    "ablation",
                    "agent_and_collaboration_ablation",
                    variant,
                    "multi_agent",
                    "All",
                    metric,
                    value,
                    native=True,
                    duplicate=duplicate,
                )
            )
    return rows


def v1_result_ledger(root: Path) -> list[dict[str, Any]]:
    tables = root / "Tables"
    rows = []
    rows.extend(parse_v1_acc(tables / "acc_mcc.tex"))
    rows.extend(parse_v1_market_returns(tables / "mkt_ap.tex"))
    rows.extend(parse_v1_portfolio(tables / "port.tex"))
    rows.extend(parse_v1_asset_pricing(tables / "ap.tex"))
    rows.extend(parse_v1_traditional(tables / "trad_ap.tex"))
    rows.extend(parse_v1_ablation(tables / "ablation.tex"))
    if len(rows) != 321:
        raise ValueError(f"v1/v2 denominator changed: {len(rows)}")
    if sum(row["cell_kind"] == "direct_result" for row in rows) != 318:
        raise ValueError("v1/v2 direct denominator changed")
    if sum(bool(row["native_maci_output"]) for row in rows) != 102:
        raise ValueError("v1/v2 native displayed-unit denominator changed")
    return rows


def clean_v3_strategy(line: str) -> str:
    second = line.split("&", 2)[1]
    second = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^]]*\])?\{([^{}]*)\}", r"\1", second)
    second = second.replace(r"\ ", " ").replace("$", "")
    return " ".join(second.split())


def parse_v3_performance(path: Path) -> list[dict[str, Any]]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        values = numbers(line)
        if line.rstrip().endswith(r"\\") and len(values) == 18:
            lines.append(line.strip())
    if len(lines) != 23:
        raise ValueError(f"v3 performance row count changed: {len(lines)}")
    categories = ("Hold",) * 2 + ("Deep Learning",) * 5 + ("Single Agent",) * 4 + ("Multi-Agent System",) * 12
    regimes = ("All", "Bull", "Bear")
    rows = []
    for line, category in zip(lines, categories):
        values = numbers(line)
        strategy = clean_v3_strategy(line)
        if not strategy:
            raise ValueError(f"cannot parse v3 strategy: {line}")
        for regime_index, regime in enumerate(regimes):
            for metric_index, metric in enumerate(METRICS_V3):
                rows.append(
                    result_row(
                        "v3",
                        "performance",
                        category,
                        strategy,
                        "GPT-4o",
                        regime,
                        metric,
                        values[regime_index * 6 + metric_index],
                        native=category == "Multi-Agent System",
                    )
                )
    if len(rows) != 414:
        raise ValueError("v3 performance denominator changed")
    return rows


def parse_v3_ablation(path: Path) -> list[dict[str, Any]]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.rstrip().endswith(r"\\") and ("Hier." in line or line.lstrip().startswith("$-$")):
            lines.append(line.strip())
    if len(lines) != 4:
        raise ValueError(f"v3 ablation row count changed: {len(lines)}")
    variants = ("Hierarchical ZS reference", "minus_news_agent", "minus_crypto_agent", "minus_memory")
    metrics = ("Cum_pct", "Vol_pct", "SR", "Win_pct")
    rows = []
    for line_index, (line, variant) in enumerate(zip(lines, variants)):
        values = numbers(line)
        direct = values if line_index == 0 else values[::2]
        deltas = [] if line_index == 0 else values[1::2]
        if len(direct) != 4 or (line_index and len(deltas) != 4):
            raise ValueError(f"v3 ablation cell count changed: {line}")
        for metric, value in zip(metrics, direct):
            rows.append(
                result_row(
                    "v3",
                    "ablation",
                    "multi_agent_component_ablation",
                    variant,
                    "GPT-4o",
                    "All",
                    metric,
                    value,
                    native=True,
                    duplicate=(f"v3_hier_zs_all_{metric.lower()}" if line_index == 0 else ""),
                )
            )
        for metric, value in zip(metrics, deltas):
            rows.append(
                result_row(
                    "v3",
                    "ablation",
                    "multi_agent_component_ablation",
                    variant,
                    "GPT-4o",
                    "All",
                    f"Delta_{metric}",
                    value,
                    kind="derived_delta",
                    native=True,
                )
            )
    if len(rows) != 28:
        raise ValueError(f"v3 ablation denominator changed: {len(rows)}")
    return rows


def v3_result_ledger(root: Path) -> list[dict[str, Any]]:
    exhibits = root / "Exhibits"
    rows = parse_v3_performance(exhibits / "performance.tex")
    rows.extend(parse_v3_ablation(exhibits / "ablation.tex"))
    if len(rows) != 442:
        raise ValueError(f"v3 denominator changed: {len(rows)}")
    if sum(row["cell_kind"] == "direct_result" for row in rows) != 430:
        raise ValueError("v3 direct denominator changed")
    if sum(bool(row["native_maci_output"]) for row in rows) != 244:
        raise ValueError("v3 native displayed-unit denominator changed")
    return rows


def apply_v3_author_table_lineage(paper_rows: list[dict[str, Any]], author_root: Path) -> dict[str, Any]:
    author_rows = parse_v3_performance(author_root / "tables" / "performance.tex")
    author_rows.extend(parse_v3_ablation(author_root / "tables" / "ablation.tex"))
    if len(author_rows) != len(paper_rows):
        raise ValueError("v3 author/paper table denominator changed")
    key_fields = (
        "table",
        "category",
        "strategy_or_variant",
        "subgroup",
        "regime_or_portfolio",
        "metric",
        "cell_kind",
    )
    for paper, author in zip(paper_rows, author_rows):
        if any(paper[field] != author[field] for field in key_fields):
            raise ValueError(f"v3 author/paper table alignment changed: {paper} != {author}")
        matched = paper["published_value"] == author["published_value"]
        paper["author_output_verified"] = matched
        paper["author_output_value"] = author["published_value"]
        paper["author_output_source"] = (
            f"lyc0603/cryptoMAS@{EXPECTED['author_v3_commit']}:tables/"
            f"{'performance.tex' if paper['table'] == 'performance' else 'ablation.tex'}"
        )
        paper["note"] = (
            "Printed unit matches the pinned author-repository table; this is output "
            "correspondence, not regeneration from released inputs."
            if matched
            else "Pinned author-repository table differs from the final paper; no "
            "input-to-output run lineage regenerates either value."
        )
    mismatch_rows = [row for row in paper_rows if not row["author_output_verified"]]
    mismatch_strategies = Counter(row["strategy_or_variant"] for row in mismatch_rows)
    expected_mismatch = {"LSTM": 17, "Informer": 18, "Autoformer": 13}
    if dict(mismatch_strategies) != expected_mismatch:
        raise ValueError(f"v3 author/paper mismatch split changed: {mismatch_strategies}")
    return {
        "published_table_units": len(paper_rows),
        "author_output_verified_units": sum(row["author_output_verified"] for row in paper_rows),
        "author_output_different_units": len(mismatch_rows),
        "mismatch_strategy_counts": expected_mismatch,
        "native_regenerated_units": 0,
        "paper_result_credit": False,
    }


def v3_source_inventory(root: Path) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", EXPECTED["author_v3_commit"]],
        check=True,
        capture_output=True,
        text=True,
    )
    paths = result.stdout.splitlines()
    if len(paths) != 42:
        raise ValueError(f"v3 tracked source inventory changed: {len(paths)}")
    rows = []
    for relative in paths:
        path = root / relative
        if not path.is_file():
            raise ValueError(f"v3 tracked file missing from checkout: {relative}")
        if relative.startswith("environ/") and path.suffix == ".py":
            role = "implementation_source"
        elif relative.startswith("scripts/") and path.suffix == ".py":
            role = "runner_or_evaluation_source"
        elif relative.startswith("tables/"):
            role = "author_output_table"
        elif relative.startswith(("figures/", "diagrams/")):
            role = "author_output_or_method_figure"
        elif relative in {"pyproject.toml", "setup_repo.sh", "README.md"}:
            role = "setup_or_documentation"
        else:
            role = "license_or_repository_metadata"
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "role": role,
                "paper_result_credit": False,
            }
        )
    return rows


def validate_repository_history(payload: Mapping[str, Any]) -> None:
    v1 = payload["v1_v2_repository_history"]
    v3 = payload["v3_repository_history"]
    expected = {
        "v1_v2": (
            v1,
            EXPECTED["author_current_commit"],
            164,
            7997,
            6649,
            7424,
            EXPECTED["v1_v2_history_commit_set"],
            EXPECTED["v1_v2_history_object_set"],
            EXPECTED["v1_v2_history_path_revisions"],
        ),
        "v3": (
            v3,
            EXPECTED["author_v3_commit"],
            20,
            209,
            50,
            130,
            EXPECTED["v3_history_commit_set"],
            EXPECTED["v3_history_object_set"],
            EXPECTED["v3_history_path_revisions"],
        ),
    }
    for label, values in expected.items():
        history, head, commits, objects, paths, revisions, commit_hash, object_hash, revision_hash = values
        observed = (
            history["head"],
            history["commit_count"],
            history["reachable_object_count"],
            history["unique_historical_path_count"],
            history["historical_path_object_revision_count"],
            history["commit_set_sha256"],
            history["reachable_object_set_sha256"],
            history["historical_path_object_revision_sha256"],
        )
        wanted = (head, commits, objects, paths, revisions, commit_hash, object_hash, revision_hash)
        if observed != wanted or history["shallow"]:
            raise ValueError(f"{label} repository history validation changed: {observed}")
    training = payload["v1_v2_deleted_training_records"]
    if training["total_records"] != 962 or len(training["files"]) != 3:
        raise ValueError("v1/v2 deleted training-record recovery changed")
    missing = payload["v3_missing_module_paths_present_in_any_commit"]
    if missing != {
        "environ/data/coingecko.py": False,
        "environ/data/cointelegraph.py": False,
        "environ/data/rag_store.py": False,
    }:
        raise ValueError(f"v3 missing-module history changed: {missing}")


def fine_tuning_record_lineage(
    author_current: Path,
    repository_history: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Recover every historical fine-tuning record and referenced image payload."""
    training = repository_history["v1_v2_deleted_training_records"]
    if (
        training["added_commit"] != TRAINING_RECORDS_COMMIT
        or training["removed_commit"] != TRAINING_RECORDS_REMOVAL_COMMIT
    ):
        raise ValueError("MACI fine-tuning record commit lineage changed")

    def tree(ref: str) -> dict[str, str]:
        rows = {}
        for line in git(author_current, "ls-tree", "-r", ref).splitlines():
            metadata, path = line.split("\t", 1)
            rows[path] = metadata.split()[2]
        return rows

    dataset_tree = tree(TRAINING_RECORDS_COMMIT)
    current_tree = tree(EXPECTED["author_current_commit"])
    expected_files = {
        item["path"]: (item["bytes"], item["sha256"], item["records"])
        for item in training["files"]
    }
    if expected_files != TRAINING_JSONL_PINS:
        raise ValueError("MACI fine-tuning JSONL history summary changed")

    def canonical_content(value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    image_cache: dict[str, dict[str, Any]] = {}
    records = []
    label_counts: Counter[str] = Counter()
    for dataset_path, (expected_bytes, expected_sha, expected_records) in sorted(
        TRAINING_JSONL_PINS.items()
    ):
        raw = git_bytes(author_current, "show", f"{TRAINING_RECORDS_COMMIT}:{dataset_path}")
        if len(raw) != expected_bytes or sha256_bytes(raw) != expected_sha:
            raise ValueError(f"MACI historical fine-tuning file changed: {dataset_path}")
        lines = raw.decode("utf-8").splitlines()
        if len(lines) != expected_records:
            raise ValueError(f"MACI fine-tuning record count changed: {dataset_path}")
        dataset_blob_oid = dataset_tree.get(dataset_path, "")
        if not dataset_blob_oid:
            raise ValueError(f"MACI dataset path missing at its addition commit: {dataset_path}")

        for record_index, line in enumerate(lines):
            payload = json.loads(line)
            messages = payload.get("messages", [])
            if [message.get("role") for message in messages] != [
                "system",
                "user",
                "assistant",
            ]:
                raise ValueError(
                    f"MACI fine-tuning role order changed: {dataset_path}:{record_index}"
                )
            by_role = {message["role"]: message["content"] for message in messages}
            assistant = canonical_content(by_role["assistant"])
            label = re.search(r"(?:Price|Market) trend:\s*(Rise|Fall)", assistant)
            if label is None:
                raise ValueError(
                    f"MACI assistant label missing: {dataset_path}:{record_index}"
                )
            assistant_label = label.group(1)
            label_counts[assistant_label] += 1

            image_urls = []
            if isinstance(by_role["user"], list):
                image_urls = [
                    item["image_url"]["url"]
                    for item in by_role["user"]
                    if item.get("type") == "image_url"
                ]
            if len(image_urls) > 1:
                raise ValueError(
                    f"MACI fine-tuning record has multiple images: {dataset_path}:{record_index}"
                )
            image_url = image_urls[0] if image_urls else ""
            image_path = ""
            image = {
                "dataset_blob_oid": "",
                "current_blob_oid": "",
                "sha256": "",
                "bytes": "",
                "width": "",
                "height": "",
                "mode": "",
                "format": "",
            }
            if image_url:
                parsed = urlparse(image_url)
                prefix = "/lyc0603/multi-agent/refs/heads/main/"
                if (
                    parsed.scheme != "https"
                    or parsed.netloc != "raw.githubusercontent.com"
                    or not parsed.path.startswith(prefix)
                ):
                    raise ValueError(f"MACI fine-tuning image URL changed: {image_url}")
                image_path = unquote(parsed.path[len(prefix) :])
                if image_path not in image_cache:
                    dataset_oid = dataset_tree.get(image_path, "")
                    current_oid = current_tree.get(image_path, "")
                    path = author_current / image_path
                    if not dataset_oid or dataset_oid != current_oid or not path.is_file():
                        raise ValueError(
                            f"MACI fine-tuning image lineage changed: {image_path}"
                        )
                    image_bytes = path.read_bytes()
                    git_oid = hashlib.sha1(  # noqa: S324 - Git object identity, not security.
                        f"blob {len(image_bytes)}\0".encode() + image_bytes,
                        usedforsecurity=False,
                    ).hexdigest()
                    if git_oid != dataset_oid:
                        raise ValueError(
                            f"MACI fine-tuning image worktree/blob mismatch: {image_path}"
                        )
                    with Image.open(BytesIO(image_bytes)) as opened:
                        width, height = opened.size
                        mode = opened.mode
                        image_format = opened.format
                        opened.verify()
                    image_cache[image_path] = {
                        "dataset_blob_oid": dataset_oid,
                        "current_blob_oid": current_oid,
                        "sha256": sha256_bytes(image_bytes),
                        "bytes": len(image_bytes),
                        "width": width,
                        "height": height,
                        "mode": mode,
                        "format": image_format,
                    }
                image = image_cache[image_path]

            records.append(
                {
                    "dataset_path": dataset_path,
                    "dataset_blob_oid": dataset_blob_oid,
                    "record_index": record_index,
                    "record_sha256": sha256_bytes(line.encode()),
                    "system_payload_sha256": sha256_bytes(
                        canonical_content(by_role["system"]).encode()
                    ),
                    "user_payload_sha256": sha256_bytes(
                        canonical_content(by_role["user"]).encode()
                    ),
                    "assistant_payload_sha256": sha256_bytes(assistant.encode()),
                    "assistant_label": assistant_label,
                    "image_reference_present": bool(image_url),
                    "image_url": image_url,
                    "image_path": image_path,
                    "image_dataset_blob_oid": image["dataset_blob_oid"],
                    "image_current_blob_oid": image["current_blob_oid"],
                    "image_sha256": image["sha256"],
                    "image_bytes": image["bytes"],
                    "image_width": image["width"],
                    "image_height": image["height"],
                    "image_mode": image["mode"],
                    "image_format": image["format"],
                    "referenced_image_payload_recovered": bool(image_url),
                    "complete_record_payload_recovered": True,
                    "paper_run_use_verified": False,
                    "paper_result_credit": False,
                }
            )

    manifest_lines = [
        "\t".join(
            (
                path,
                str(image["bytes"]),
                str(image["sha256"]),
                f"{image['width']}x{image['height']}",
                str(image["mode"]),
                str(image["format"]),
            )
        )
        for path, image in sorted(image_cache.items())
    ]
    manifest_hash = sha256_bytes("\n".join(manifest_lines).encode())
    image_references = sum(bool(row["image_reference_present"]) for row in records)
    if (
        len(records) != 962
        or image_references != 931
        or len(image_cache) != 930
        or sum(int(image["bytes"]) for image in image_cache.values()) != 53_574_400
        or {image["width"] for image in image_cache.values()} != {1000}
        or {image["height"] for image in image_cache.values()} != {800}
        or {image["mode"] for image in image_cache.values()} != {"RGBA"}
        or {image["format"] for image in image_cache.values()} != {"PNG"}
        or manifest_hash != TRAINING_IMAGE_MANIFEST_SHA256
        or label_counts != {"Fall": 496, "Rise": 466}
    ):
        raise ValueError("MACI fine-tuning message/image payload census changed")
    image_names = [Path(path).stem for path in image_cache]
    assets = {name.rsplit("_", 2)[0] for name in image_names}
    weeks = {tuple(map(int, name.rsplit("_", 2)[-2:])) for name in image_names}
    if len(assets) != 33 or len(weeks) != 31 or min(weeks) != (2023, 22) or max(weeks) != (2023, 52):
        raise ValueError("MACI fine-tuning image asset/week coverage changed")
    summary = {
        "dataset_commit": TRAINING_RECORDS_COMMIT,
        "dataset_commit_author_date": training["added_commit_author_date"],
        "dataset_removed_commit": TRAINING_RECORDS_REMOVAL_COMMIT,
        "dataset_removed_commit_author_date": training["removed_commit_author_date"],
        "dataset_added_after_paper_v2": True,
        "jsonl_files": len(TRAINING_JSONL_PINS),
        "fine_tuning_format_records": len(records),
        "system_messages": len(records),
        "user_messages": len(records),
        "assistant_messages": len(records),
        "assistant_label_counts": dict(sorted(label_counts.items())),
        "image_references": image_references,
        "unique_image_urls": len({row["image_url"] for row in records if row["image_url"]}),
        "unique_image_paths": len(image_cache),
        "unique_image_git_blobs": len(
            {image["dataset_blob_oid"] for image in image_cache.values()}
        ),
        "image_payloads_recovered": len(image_cache),
        "image_payloads_identical_at_current_head": sum(
            image["dataset_blob_oid"] == image["current_blob_oid"]
            for image in image_cache.values()
        ),
        "image_payload_bytes": sum(int(image["bytes"]) for image in image_cache.values()),
        "image_dimensions": [1000, 800],
        "image_mode": "RGBA",
        "image_format": "PNG",
        "image_assets": len(assets),
        "image_weeks": len(weeks),
        "image_week_min": "2023-W22",
        "image_week_max": "2023-W52",
        "image_manifest_sha256": manifest_hash,
        "all_referenced_image_payloads_recovered": True,
        "historical_fine_tuning_files_have_complete_message_and_image_payloads": True,
        "actual_uploaded_file_identity_recovered": False,
        "fine_tuning_job_and_selected_checkpoint_recovered": False,
        "paper_run_use_verified": False,
        "paper_result_credit": False,
    }
    return records, summary


def figure_rows(source: Path, author: Path, comparison: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    comparison_by_name = {row["asset"]: row for row in comparison}
    result_units = {
        "port_BTC.pdf": 3,
        "port_USD.pdf": 3,
        "scatter_cs.pdf": 3,
        "scatter_mkt.pdf": 3,
        "bar_cs.pdf": 3,
        "bar_mkt.pdf": 3,
        "radar_cs.pdf": 3,
    }
    qualitative = {"explanation.pdf": 2}
    names = sorted(path.name for path in (source / "Figures").iterdir() if path.suffix.lower() in {".pdf", ".png"})
    if len(names) != 17:
        raise ValueError(f"v1 figure-asset count changed: {len(names)}")
    rows = []
    for name in names:
        source_path = source / "Figures" / name
        author_matches = list(author.rglob(name))
        if len(author_matches) != 1:
            raise ValueError(f"author figure match count for {name}: {len(author_matches)}")
        author_path = author_matches[0]
        source_hash = sha256_file(source_path)
        author_hash = sha256_file(author_path)
        if source_hash == author_hash:
            correspondence = "byte_identical"
        elif name == "scatter_cs.pdf":
            details = comparison_by_name[name]["pages"][0]
            if details["exact_pixel_channel_fraction"] != 1.0:
                raise ValueError("scatter_cs is no longer render-identical")
            correspondence = "render_pixel_identical_metadata_only_difference"
        elif name == "scatter_mkt.pdf":
            details = comparison_by_name[name]["pages"][0]
            source_shapes = details["source"]["drawing_shape_hash_counts"]
            author_shapes = details["author"]["drawing_shape_hash_counts"]
            if any(source_shapes.get(key, 0) < value for key, value in author_shapes.items()):
                raise ValueError("scatter_mkt author geometry is no longer a submitted-figure subset")
            correspondence = "all_author_drawing_geometry_preserved_submitted_label_adds_factor"
        elif name.startswith("port_"):
            details = comparison_by_name[name]["pages"][0]
            source_records = [row for row in details["source"]["drawing_records"] if row["x_scale_normalized_points"]]
            author_records = [row for row in details["author"]["drawing_records"] if row["x_scale_normalized_points"]]
            maximum_x = 0.0
            maximum_y = 0.0
            for left in source_records:
                matches = [
                    right
                    for right in author_records
                    if right["point_count"] == left["point_count"] and right["color"] == left["color"]
                ]
                if len(matches) != 1:
                    raise ValueError(f"cannot pair portfolio path in {name}")
                for point_left, point_right in zip(
                    left["x_scale_normalized_points"], matches[0]["x_scale_normalized_points"]
                ):
                    maximum_x = max(maximum_x, abs(point_left[0] - point_right[0]))
                    maximum_y = max(maximum_y, abs(point_left[1] - point_right[1]))
            if maximum_x > 0.0000011 or maximum_y != 0:
                raise ValueError(f"portfolio path geometry changed: {name}")
            correspondence = "all_five_vector_paths_same_y_and_point_counts_after_horizontal_resize_legend_changed"
        else:
            raise ValueError(f"unexpected non-identical figure: {name}")
        rows.append(
            {
                "asset": name,
                "compiled_into_v1_pdf": name != "port_ETH.pdf",
                "role": (
                    "quantitative_result_figure"
                    if name in result_units
                    else "qualitative_result_example"
                    if name in qualitative
                    else "unused_quantitative_result_asset"
                    if name == "port_ETH.pdf"
                    else "method_or_input_illustration"
                ),
                "published_plotted_result_units": result_units.get(name, 0),
                "published_qualitative_outputs": qualitative.get(name, 0),
                "source_sha256": source_hash,
                "author_sha256": author_hash,
                "author_output_correspondence": correspondence,
                "native_result_regenerated": False,
                "paper_result_credit": False,
                "note": "Author-output lineage only; no inputs or execution regenerate the plotted output.",
            }
        )
    return rows


def method_rows() -> list[dict[str, Any]]:
    entries = [
        (
            "v1/v2",
            "system_architecture",
            "specified_and_source_present",
            "Four experts, team collaboration, and source classes are recoverable.",
        ),
        ("v1/v2", "base_model", "exact_snapshot_in_source", "gpt-4o-2024-08-06, temperature 0."),
        (
            "v1/v2",
            "fine_tuned_model_ids",
            "incomplete_unverified",
            "One commented fine-tuned model ID appears in source; the actual job, selected model, and complete lineage are not released.",
        ),
        (
            "v1/v2",
            "training_period",
            "specified",
            "June--October 2023 in paper; source fine-tuning bounds end November 1.",
        ),
        (
            "v1/v2",
            "test_period",
            "conflicting",
            "Paper says November 2023--September 2024; figures end August; source handlers end January 2025; metrics imply 43 weeks.",
        ),
        (
            "v1/v2",
            "universe",
            "high_level_only",
            "Weekly top-30 CoinGecko universe stated; exact memberships are absent.",
        ),
        (
            "v1/v2",
            "raw_inputs",
            "market_inputs_missing_training_images_recovered",
            "Market/factor data and processed_data are absent from every Git object; all 930 distinct image payloads referenced by the recovered fine-tuning-format files are present as tracked PNG blobs.",
        ),
        (
            "v1/v2",
            "processed_inputs",
            "market_inputs_missing_historical_training_payload_complete",
            "Factors, news, prices, and weekly universes are absent; all 962 historical training message records and every referenced image payload are recoverable.",
        ),
        (
            "v1/v2",
            "prompt_templates",
            "templates_plus_complete_historical_training_payload",
            "Templates plus 962 fine-tuning-format message records and all 930 distinct referenced image payloads are recovered. The files were added post-v2, and the actual uploaded file, job, and selected checkpoint remain absent.",
        ),
        (
            "v1/v2",
            "model_requests_responses",
            "training_examples_only",
            "Complete history recovers the historical training messages and referenced image payloads, but no immutable inference requests/responses, token/logprob records, or retry logs.",
        ),
        ("v1/v2", "checkpoints", "missing", "Runner names pickle checkpoints, but none are released."),
        ("v1/v2", "prediction_records", "missing", "Runner names JSON records, but none are released."),
        (
            "v1/v2",
            "portfolio_rules",
            "source_present",
            "Top-quintile, linear-probability ensemble, and market weights are inspectable.",
        ),
        ("v1/v2", "costs_and_slippage", "missing", "No execution-cost or slippage contract."),
        (
            "v1/v2",
            "risk_free_rate",
            "source_uses_zero",
            "Portfolio evaluator uses zero; paper does not identify a source.",
        ),
        ("v1/v2", "seeds_repetitions_uncertainty", "missing", "No seeds, repetitions, or uncertainty lineage."),
        ("v1/v2", "table_outputs", "missing", "Zero of 321 printed table units are shipped as source-derived records."),
        (
            "v1/v2",
            "figure_outputs",
            "author_output_verified",
            "All 16 compiled figure assets have author-repository content lineage; this is not regeneration.",
        ),
        (
            "v3",
            "system_architecture",
            "source_present_component_verified",
            "Pinned source implements hierarchical, collaborative, and two-round debate orchestration; nine non-RAG architecture/capability component paths execute with fixture agent outputs.",
        ),
        ("v3", "model_snapshots", "missing", "GPT-4o, GPT-5, and Claude Sonnet 4.5 snapshot IDs are not pinned."),
        ("v3", "experiment_period", "specified", "Calendar 2025, 52 weeks."),
        (
            "v3",
            "universe",
            "exact_list_source_present",
            "The same fixed 15-symbol universe is explicit in the paper and released agent source.",
        ),
        (
            "v3",
            "raw_and_processed_inputs",
            "missing_source_package_and_data",
            "No frozen price/news rows, timestamps, result records, or retrieval corpus are released; all three environ.data modules imported by the runner are absent from every public-history commit.",
        ),
        (
            "v3",
            "memory_rag_skill_state",
            "partial_source_rag_unrunnable",
            "Rolling memory and skill indicators are implemented; the RAG agent shell is present but its RAGStore implementation and corpus are absent.",
        ),
        (
            "v3",
            "prompts",
            "substantial_source_present",
            "Three prompts compile in the appendix and runtime source contains agent/system templates; exact instantiated requests and responses are absent.",
        ),
        (
            "v3",
            "react_loop",
            "paper_source_conflict",
            "The paper says ReAct reasoning/action interleaving is compulsory, while source provides single request/final JSON calls and CoT reasoning tags but no observation/action loop.",
        ),
        (
            "v3",
            "single_agent_capabilities",
            "hard_source_result_conflict",
            "The runner maps both single-agent RAG and Skill to zero-shot although the paper reports distinct results for all three variants.",
        ),
        ("v3", "decision_traces", "missing", "No traces are released despite the traceability claim."),
        ("v3", "actions_orders_fills", "missing", "No action, order, fill, or timing record."),
        (
            "v3",
            "baseline_code_checkpoints",
            "source_present_inputs_checkpoints_missing",
            "Baseline runner code is released, but frozen inputs, trained checkpoints, and native outputs are absent.",
        ),
        (
            "v3",
            "transaction_costs_slippage",
            "source_present",
            "Portfolio execution applies the stated 0.1% cost to buys and sells and omits slippage.",
        ),
        (
            "v3",
            "risk_free_rate",
            "hard_result_method_conflict",
            "Printed full-period Sharpe values imply approximately zero, not the cited Fama-French T-bill series.",
        ),
        (
            "v3",
            "seeds_repetitions_uncertainty",
            "missing",
            "No seeds, repetitions, confidence intervals, or run dispersion.",
        ),
        (
            "v3",
            "table_outputs",
            "394_author_output_verified_zero_regenerated",
            "394/442 printed units match pinned author-repository tables; all 28 ablation units and 366/414 performance units correspond, but zero have input-to-output run lineage.",
        ),
        (
            "v3",
            "figure_outputs",
            "136_author_output_verified_zero_regenerated",
            "Two 48-bar model-comparison figures are byte-identical; 20/23 portfolio paths and 20/23 risk/return points correspond. Zero of 142 units regenerate from inputs.",
        ),
    ]
    return [
        {"paper_version": version, "dimension": dimension, "status": status, "evidence_boundary": note}
        for version, dimension, status, note in entries
    ]


def prompt_rows(v1: Path, v3: Path) -> list[dict[str, Any]]:
    rows = []
    for version, root in (("v1/v2", v1), ("v3", v3)):
        for path in sorted((root / "Prompts").glob("*.tex")):
            compiled = version == "v1/v2" or path.name in {
                "crypto_instruc.tex",
                "trading_instruc.tex",
                "cot_instruc.tex",
            }
            rows.append(
                {
                    "paper_version": version,
                    "source_file": path.name,
                    "compiled_into_appendix": compiled,
                    "exact_runtime_values_released": False,
                    "actual_request_released": False,
                    "actual_response_released": False,
                    "note": (
                        "Appendix prompt source; placeholders remain uninstantiated."
                        if compiled
                        else "Legacy source residue not compiled into the v3 manuscript."
                    ),
                }
            )
    if sum(row["paper_version"] == "v3" for row in rows) != 18:
        raise ValueError("v3 prompt-source count changed")
    if sum(row["paper_version"] == "v3" and row["compiled_into_appendix"] for row in rows) != 3:
        raise ValueError("v3 compiled-prompt count changed")
    return rows


def consistency_rows(
    v1_rows: Sequence[Mapping[str, Any]], v3_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    performance = [row for row in v3_rows if row["table"] == "performance"]
    all_values: dict[str, dict[str, float]] = {}
    bear_values: dict[str, dict[str, float]] = {}
    for row in performance:
        target = (
            all_values
            if row["regime_or_portfolio"] == "All"
            else bear_values
            if row["regime_or_portfolio"] == "Bear"
            else None
        )
        if target is not None:
            target.setdefault(str(row["strategy_or_variant"]), {})[str(row["metric"])] = float(row["published_value"])
    implied_rf = [values["Avg_pct"] - values["SR"] * values["Vol_pct"] / 52 for values in all_values.values()]
    mdd_violations = [
        strategy
        for strategy, values in bear_values.items()
        if values["Cum_pct"] < 0 and values["MDD_pct"] > values["Cum_pct"]
    ]
    market_accuracy = [
        float(row["published_value"])
        for row in v1_rows
        if row["table"] == "classification" and row["category"] == "market_prediction" and row["metric"] == "Accuracy"
    ]
    annualized = (1 + 0.8347) ** (52 / 43) - 1
    entries = [
        (
            "v1/v2",
            "artifact_placeholder",
            "hard_release_claim_conflict",
            "v1 literally prints URL_TO_YOUR_ARTIFACTS; v2 comments the statement out.",
        ),
        (
            "v1/v2",
            "python_requirement",
            "hard_environment_conflict",
            "pyproject claims >=3.9.15, while two released match statements fail to parse on Python 3.9.",
        ),
        (
            "v1/v2",
            "test_dates",
            "unresolved_date_conflict",
            "Paper says through September 2024, plots through August, and source handlers through 2024-12-31.",
        ),
        (
            "v1/v2",
            "forty_three_week_lineage",
            "strong_internal_correspondence",
            f"Market accuracies are 43-week fractions and annualizing 0.8347 over 43 weeks gives {annualized:.6f}, matching 108.32%. Values: {market_accuracy}.",
        ),
        (
            "v1/v2",
            "fine_tuning_coverage",
            "source_execution_gap",
            "Only the crypto-factor fine-tuning block is active; other expert blocks are commented and require manual edits.",
        ),
        (
            "v1/v2",
            "explanation_dimensions",
            "paper_source_mismatch",
            "Judge source scores eight criteria; paper reports five and releases no evaluation records.",
        ),
        (
            "v1/v2",
            "figure_revision",
            "author_output_verified_not_regenerated",
            "All compiled assets correspond; portfolio legends/width and one scatter label changed after the pinned pre-submission commit.",
        ),
        (
            "v3",
            "code_lineage",
            "v3_source_recovered_incomplete",
            "The paper-listed anonymous artifact resolves to first-author cryptoMAS source with all three architectures, but the runner's coingecko, cointelegraph, and RAGStore modules are absent from all 20 commits.",
        ),
        (
            "v3",
            "strictly_out_of_pretraining_claim",
            "claim_not_supported",
            "Official provider dates/cutoffs do not support treating all calendar-2025 observations as strictly outside every model's training distribution.",
        ),
        (
            "v3",
            "retrospective_model_availability",
            "temporal_validity_risk",
            "GPT-5 and Claude Sonnet 4.5 were released during 2025, so their full-year evaluations were necessarily retrospective.",
        ),
        (
            "v3",
            "risk_free_rate",
            "hard_method_result_conflict",
            f"Across 23 full-period rows, implied weekly RF ranges {min(implied_rf):.6f}% to {max(implied_rf):.6f}% (mean {sum(implied_rf) / len(implied_rf):.6f}%), effectively zero rather than the cited 2025 Fama-French T-bill rate.",
        ),
        (
            "v3",
            "bear_regime_mdd",
            "unreported_convention_or_hard_value_conflict",
            f"{len(mdd_violations)}/23 bear rows have negative terminal cumulative return whose magnitude exceeds printed MDD; they cannot arise from the same regime-conditioned path under the printed definition.",
        ),
        (
            "v3",
            "action_timing",
            "ambiguous",
            "Inputs at t-1 produce A_t, while the wealth equation applies A_{t-1}; close/execution timing is not resolved.",
        ),
        (
            "v3",
            "traceability",
            "claim_unverifiable",
            "The paper says every decision is traceable but releases no trace.",
        ),
    ]
    return [
        {"paper_version": version, "claim_id": claim, "status": status, "evidence": evidence}
        for version, claim, status, evidence in entries
    ]


def source_rows() -> list[dict[str, Any]]:
    return [
        {
            "version": "v1",
            "submitted_utc": "2025-01-01T13:08:17Z",
            "pdf_sha256": EXPECTED["v1_pdf"],
            "source_tar_sha256": EXPECTED["v1_source_tar"],
            "pages": 14,
            "experimental_lineage": "v1_v2_gpt4o_four_expert_2023_2024",
        },
        {
            "version": "v2",
            "submitted_utc": "2025-01-07T00:15:11Z",
            "pdf_sha256": EXPECTED["v2_pdf"],
            "source_tar_sha256": EXPECTED["v2_source_tar"],
            "pages": 14,
            "experimental_lineage": "v1_v2_gpt4o_four_expert_2023_2024",
        },
        {
            "version": "v3",
            "submitted_utc": "2026-06-16T16:36:42Z",
            "pdf_sha256": EXPECTED["v3_pdf"],
            "source_tar_sha256": EXPECTED["v3_source_tar"],
            "pages": 10,
            "experimental_lineage": "v3_three_architecture_calendar_2025",
        },
    ]


def artifact_rows() -> list[dict[str, Any]]:
    return [
        {
            "artifact": "arXiv v1/v2 paper and TeX",
            "url_or_commit": "https://arxiv.org/abs/2501.00826",
            "availability": "complete manuscript source",
            "system_credit": False,
            "result_credit": False,
            "note": "Document/specification evidence.",
        },
        {
            "artifact": "arXiv v3 paper and TeX",
            "url_or_commit": "https://arxiv.org/abs/2501.00826",
            "availability": "complete manuscript source with three compiled prompts",
            "system_credit": False,
            "result_credit": False,
            "note": "Different experiment under the same identifier.",
        },
        {
            "artifact": "v1/v2 author repository",
            "url_or_commit": "https://github.com/lyc0603/multi-agent",
            "availability": "reachable MIT Python repository with complete 164-commit history",
            "system_credit": True,
            "result_credit": False,
            "note": "Author identity and paper title match.",
        },
        {
            "artifact": "pre-submission author commit",
            "url_or_commit": EXPECTED["author_v1_commit"],
            "availability": "2330 files; 147197324 bytes",
            "system_credit": True,
            "result_credit": False,
            "note": "Authentic v1-style source, figures, runner, and tests; constants/data/results are omitted.",
        },
        {
            "artifact": "current v1/v2 repository commit",
            "url_or_commit": EXPECTED["author_current_commit"],
            "availability": "6547 tracked paths; complete history has 7997 reachable objects",
            "system_credit": True,
            "result_credit": False,
            "note": "Restores constants and extends figures; complete history also recovers 962 deleted fine-tuning-format message records.",
        },
        {
            "artifact": "v1/v2 public-fork census",
            "url_or_commit": "https://github.com/lyc0603/multi-agent/forks",
            "availability": "two accessible public forks and two branch refs audited on 2026-08-14",
            "system_credit": False,
            "result_credit": False,
            "note": "One fork is exact at the official head and one is a three-commit-behind official-history ancestor; neither adds a commit, blob, tag, or result lineage.",
        },
        {
            "artifact": "paper-listed anonymous v3 artifact",
            "url_or_commit": "https://anonymous.4open.science/r/cryptoMAS-FCB2/",
            "availability": "repository landing endpoint requires connection, but its public file API serves a hash-pinned README",
            "system_credit": True,
            "result_credit": False,
            "note": "The README is byte-identical to the first-author cryptoMAS repository README and directs users to that GitHub repository.",
        },
        {
            "artifact": "v3 author repository",
            "url_or_commit": "https://github.com/lyc0603/cryptoMAS",
            "availability": "reachable public MIT repository; complete 20-commit history; 42 tracked files",
            "system_credit": True,
            "result_credit": False,
            "note": "Implements the three v3 architectures and author outputs, but omits every environ.data module, frozen data, records, and checkpoints.",
        },
        {
            "artifact": "v3 author repository head",
            "url_or_commit": EXPECTED["author_v3_commit"],
            "availability": "209 reachable objects; 50 unique historical paths; no tags",
            "system_credit": True,
            "result_credit": False,
            "note": "Head predates v3 submission and is pinned across source, table, figure, history, and component audits.",
        },
        {
            "artifact": "historical README repository target",
            "url_or_commit": "https://github.com/dlt-science/multi-agent",
            "availability": "HTTP 404",
            "system_credit": False,
            "result_credit": False,
            "note": "Bounded current access result, not proof no private/deleted artifact existed.",
        },
        {
            "artifact": "Fama-French factors",
            "url_or_commit": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
            "availability": "official monthly factor archive pinned",
            "system_credit": False,
            "result_credit": False,
            "note": "2025 monthly RF is 0.30--0.38%, conflicting with table-implied approximately-zero RF.",
        },
    ]


def external_primary_source_rows() -> list[dict[str, Any]]:
    return [
        {
            "subject": "GPT-4o API snapshot",
            "primary_source": "https://developers.openai.com/api/docs/models/gpt-4o",
            "source_fact": "OpenAI lists gpt-4o-2024-08-06 as a dated snapshot.",
            "audit_implication": "v1 source pins a real snapshot; v3 says GPT-4o without a snapshot ID.",
        },
        {
            "subject": "GPT-5 release and snapshot",
            "primary_source": "https://openai.com/index/introducing-gpt-5-for-developers/",
            "source_fact": "OpenAI released GPT-5 in the API on 2025-08-07.",
            "audit_implication": "A GPT-5 evaluation covering all of calendar 2025 is retrospective for the pre-release months.",
        },
        {
            "subject": "GPT-5 knowledge cutoff",
            "primary_source": "https://developers.openai.com/api/docs/models/gpt-5",
            "source_fact": "The GPT-5 model page lists a 2024-09-30 knowledge cutoff and dated snapshot gpt-5-2025-08-07.",
            "audit_implication": "The paper omits the exact snapshot; calendar-2025 is post-cutoff but not wholly prospective relative to release.",
        },
        {
            "subject": "Claude Sonnet 4.5 release",
            "primary_source": "https://www.anthropic.com/news/claude-sonnet-4-5",
            "source_fact": "Anthropic released Claude Sonnet 4.5 on 2025-09-29.",
            "audit_implication": "A Claude Sonnet 4.5 evaluation covering all of calendar 2025 is retrospective for the pre-release months.",
        },
        {
            "subject": "Claude Sonnet 4.5 training boundary",
            "primary_source": "https://www.anthropic.com/transparency",
            "source_fact": "Anthropic reports a Jan-2025 reliable knowledge cutoff and public internet training data through July 2025.",
            "audit_implication": "The blanket claim that all 2025 observations are strictly outside pretraining is contradicted by the disclosed training-data boundary.",
        },
        {
            "subject": "Claude Sonnet 4.5 snapshot",
            "primary_source": "https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions",
            "source_fact": "Anthropic documents the pinned ID claude-sonnet-4-5-20250929.",
            "audit_implication": "The paper names only Claude Sonnet 4.5, leaving the exact request-level model ID unrecorded.",
        },
        {
            "subject": "Fama-French risk-free factor",
            "primary_source": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
            "source_fact": "The pinned official monthly archive reports 2025 RF values from 0.30% to 0.38%.",
            "audit_implication": "The printed v3 full-period Sharpe values instead imply an approximately zero weekly risk-free rate.",
        },
    ]


def pdf_pages(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], check=True, text=True, capture_output=True)
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    if not match:
        raise ValueError(f"cannot read page count: {path}")
    return int(match.group(1))


def pdf_text_metrics(official: Path, rebuilt: Path) -> dict[str, Any]:
    def tokens(path: Path) -> list[str]:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=True,
            text=True,
            capture_output=True,
        )
        return re.findall(r"[A-Za-z0-9]+(?:[.'’-][A-Za-z0-9]+)*", result.stdout.lower())

    official_tokens = tokens(official)
    rebuilt_tokens = tokens(rebuilt)
    official_counts = Counter(official_tokens)
    rebuilt_counts = Counter(rebuilt_tokens)
    intersection = sum((official_counts & rebuilt_counts).values())
    union = sum((official_counts | rebuilt_counts).values())
    return {
        "official_tokens": len(official_tokens),
        "rebuilt_tokens": len(rebuilt_tokens),
        "token_delta": len(rebuilt_tokens) - len(official_tokens),
        "sequence_ratio": SequenceMatcher(None, official_tokens, rebuilt_tokens, autojunk=False).ratio(),
        "multiset_jaccard": intersection / union,
    }


def latex_log_summary(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    output = re.search(r"Output written on .*\((\d+) pages?", text)
    if not output:
        raise ValueError(f"cannot find final LaTeX output record: {path}")
    return {
        "undefined_citations": len(re.findall(r"Citation .* undefined", text)),
        "undefined_references": len(re.findall(r"Reference .* undefined", text)),
        "latex_errors": len(re.findall(r"^!", text, re.MULTILINE)),
        "overfull_hbox": text.count(r"Overfull \hbox"),
        "overfull_vbox": text.count(r"Overfull \vbox"),
        "underfull_hbox": text.count(r"Underfull \hbox"),
        "underfull_vbox": text.count(r"Underfull \vbox"),
        "output_pages": int(output.group(1)),
    }


def manuscript_provenance(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = []
    for version in ("v1", "v2", "v3"):
        official = getattr(args, f"official_{version}")
        run1 = getattr(args, f"rebuild_{version}_run1")
        run2 = getattr(args, f"rebuild_{version}_run2")
        final_log = getattr(args, f"rebuild_{version}_log")
        expected_pages = 10 if version == "v3" else 14
        rebuild_hash = EXPECTED[f"{version}_rebuild"]
        run1_hash = sha256_file(run1)
        run2_hash = sha256_file(run2)
        if run1_hash != rebuild_hash or run2_hash != rebuild_hash:
            raise ValueError(f"{version} rebuild hash changed")
        if pdf_pages(run1) != expected_pages or pdf_pages(run2) != expected_pages:
            raise ValueError(f"{version} rebuild page count changed")
        log = latex_log_summary(final_log)
        if log["latex_errors"] or log["undefined_citations"] or log["undefined_references"]:
            raise ValueError(f"{version} final manuscript log is not clean")
        rows.append(
            {
                "version": version,
                "official_pdf_sha256": sha256_file(official),
                "official_pages": pdf_pages(official),
                "source_tar_sha256": sha256_file(getattr(args, f"source_tar_{version}")),
                "rebuild_run1_sha256": run1_hash,
                "rebuild_run2_sha256": run2_hash,
                "rebuild_runs_byte_identical": run1_hash == run2_hash,
                "rebuild_pages": pdf_pages(run2),
                "official_rebuild_text": pdf_text_metrics(official, run2),
                "final_latex_log": log,
                "visual_qa": {
                    "status": "passed_full_document_contact_sheet_review",
                    "review_date": "2026-08-11",
                    "pages_reviewed_official": expected_pages,
                    "pages_reviewed_rebuild": expected_pages,
                    "checks": [
                        "readable_text",
                        "no_clipping",
                        "no_overlap",
                        "no_invisible_content",
                        "overall_layout_correspondence",
                    ],
                    "qualification": "Manual visual reconstruction QA only; it provides no experimental-result credit.",
                },
                "paper_result_credit": False,
            }
        )
    return rows


def author_source_inventory(v1: Path, current: Path, v3: Path) -> dict[str, Any]:
    def files(root: Path, suffix: str | None = None) -> list[Path]:
        return [
            path
            for path in root.rglob("*")
            if path.is_file()
            and ".git" not in path.relative_to(root).parts
            and (suffix is None or path.suffix == suffix)
        ]

    v1_python = files(v1, ".py")
    current_python = files(current, ".py")
    searchable = [path for path in files(current) if path.suffix.lower() in {".py", ".md"}]
    search_terms = ("hierarchical", "collaborative", "debate", "retrieval-augmented", "skill", "memory")
    hits = {term: 0 for term in search_terms}
    for path in searchable:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for term in search_terms:
            hits[term] += int(term in text)
    v3_python = files(v3, ".py")
    v3_tracked = subprocess.run(
        ["git", "-C", str(v3), "ls-tree", "-r", "--name-only", EXPECTED["author_v3_commit"]],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return {
        "pre_submission_commit": EXPECTED["author_v1_commit"],
        "current_commit": EXPECTED["author_current_commit"],
        "pre_submission_python_files": len(v1_python),
        "current_python_files": len(current_python),
        "pre_submission_constants_present": (v1 / "environ" / "constants.py").is_file(),
        "current_constants_present": (current / "environ" / "constants.py").is_file(),
        "pre_submission_data_files": len(files(v1 / "data")) if (v1 / "data").exists() else 0,
        "pre_submission_processed_data_files": len(files(v1 / "processed_data"))
        if (v1 / "processed_data").exists()
        else 0,
        "v1_v2_repository_v3_architecture_capability_term_file_hits": hits,
        "v1_v2_repository_contains_v3_implementation": any(hits.values()),
        "v3_author_commit": EXPECTED["author_v3_commit"],
        "v3_tracked_files": len(v3_tracked),
        "v3_python_files": len(v3_python),
        "v3_architecture_files": sorted(
            path.relative_to(v3).as_posix() for path in v3_python if path.parent.name == "architectures"
        ),
        "v3_data_package_present": (v3 / "environ" / "data").is_dir(),
        "v3_implementation_recovered": all(
            (v3 / "environ" / "architectures" / name).is_file()
            for name in ("hierarchical.py", "collaborative.py", "debate.py")
        ),
        "qualification": "The separate first-author cryptoMAS repository recovers the v3 implementation. Its missing data package prevents end-to-end execution and result regeneration.",
    }


def validate_fama_french(path: Path) -> dict[str, float]:
    if sha256_file(path) != EXPECTED["fama_french_archive"]:
        raise ValueError("Fama-French archive hash changed")
    with ZipFile(path) as archive:
        names = archive.namelist()
        if names != ["F-F_Research_Data_Factors.csv"]:
            raise ValueError(f"Fama-French archive members changed: {names}")
        text = archive.read(names[0]).decode("utf-8")
    values = {}
    for line in text.splitlines():
        match = re.match(r"^(2025\d{2}),.*?,\s*([-+]?\d+\.\d+)\s*$", line)
        if match:
            values[match.group(1)] = float(match.group(2))
    if len(values) != 12 or min(values.values()) != 0.30 or max(values.values()) != 0.38:
        raise ValueError(f"Fama-French 2025 RF values changed: {values}")
    return values


def validate_primary_inputs(args: argparse.Namespace) -> None:
    for version in ("v1", "v2", "v3"):
        pdf = getattr(args, f"official_{version}")
        if sha256_file(pdf) != EXPECTED[f"{version}_pdf"]:
            raise ValueError(f"official {version} PDF hash changed")
        expected_pages = 14 if version != "v3" else 10
        if pdf_pages(pdf) != expected_pages:
            raise ValueError(f"official {version} page count changed")
        source_tar = getattr(args, f"source_tar_{version}")
        if sha256_file(source_tar) != EXPECTED[f"{version}_source_tar"]:
            raise ValueError(f"official {version} source tar hash changed")
    if args.author_current_commit != EXPECTED["author_current_commit"]:
        raise ValueError("current author commit changed")
    if args.author_v3_commit != EXPECTED["author_v3_commit"]:
        raise ValueError("v3 author commit changed")
    observed_v3_head = subprocess.run(
        ["git", "-C", str(args.author_v3), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if observed_v3_head != EXPECTED["author_v3_commit"]:
        raise ValueError(f"v3 author checkout head changed: {observed_v3_head}")
    if sha256_file(args.anonymous_v3_readme) != EXPECTED["anonymous_v3_readme"]:
        raise ValueError("anonymous v3 README hash changed")
    if sha256_file(args.author_v3 / "README.md") != EXPECTED["anonymous_v3_readme"]:
        raise ValueError("anonymous artifact README no longer matches v3 author repository")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-source", type=Path, required=True)
    parser.add_argument("--v2-source", type=Path, required=True)
    parser.add_argument("--v3-source", type=Path, required=True)
    parser.add_argument("--source-tar-v1", type=Path, required=True)
    parser.add_argument("--source-tar-v2", type=Path, required=True)
    parser.add_argument("--source-tar-v3", type=Path, required=True)
    parser.add_argument("--author-v1", type=Path, required=True)
    parser.add_argument("--author-current", type=Path, required=True)
    parser.add_argument("--author-v3", type=Path, required=True)
    parser.add_argument("--official-v1", type=Path, required=True)
    parser.add_argument("--official-v2", type=Path, required=True)
    parser.add_argument("--official-v3", type=Path, required=True)
    parser.add_argument("--rebuild-v1-run1", type=Path, required=True)
    parser.add_argument("--rebuild-v1-run2", type=Path, required=True)
    parser.add_argument("--rebuild-v1-log", type=Path, required=True)
    parser.add_argument("--rebuild-v2-run1", type=Path, required=True)
    parser.add_argument("--rebuild-v2-run2", type=Path, required=True)
    parser.add_argument("--rebuild-v2-log", type=Path, required=True)
    parser.add_argument("--rebuild-v3-run1", type=Path, required=True)
    parser.add_argument("--rebuild-v3-run2", type=Path, required=True)
    parser.add_argument("--rebuild-v3-log", type=Path, required=True)
    parser.add_argument("--fama-french-archive", type=Path, required=True)
    parser.add_argument("--author-current-commit", required=True)
    parser.add_argument("--author-v3-commit", required=True)
    parser.add_argument("--anonymous-v3-readme", type=Path, required=True)
    parser.add_argument("--execution-json", type=Path, required=True)
    parser.add_argument("--v3-execution-json", type=Path, required=True)
    parser.add_argument("--figure-comparison-json", type=Path, required=True)
    parser.add_argument("--v3-figure-comparison-json", type=Path, required=True)
    parser.add_argument("--repository-history-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    validate_primary_inputs(args)
    v1 = v1_result_ledger(args.v1_source)
    v2 = v1_result_ledger(args.v2_source)
    if [row["published_value"] for row in v1] != [row["published_value"] for row in v2]:
        raise ValueError("v1/v2 printed result values changed")
    v3 = v3_result_ledger(args.v3_source)
    v3_table_lineage = apply_v3_author_table_lineage(v3, args.author_v3)
    comparison = json.loads(args.figure_comparison_json.read_text(encoding="utf-8"))
    figures = figure_rows(args.v1_source, args.author_v1, comparison)
    execution = json.loads(args.execution_json.read_text(encoding="utf-8"))
    v3_execution = json.loads(args.v3_execution_json.read_text(encoding="utf-8"))
    if v3_execution["head"] != EXPECTED["author_v3_commit"]:
        raise ValueError("v3 execution head changed")
    if v3_execution["paper_results_regenerated"] != 0 or v3_execution["llm_calls_made"] != 0:
        raise ValueError("v3 execution evidence crossed its zero-result/no-API boundary")
    v3_figure_comparison = json.loads(args.v3_figure_comparison_json.read_text(encoding="utf-8"))
    if (
        v3_figure_comparison["author_head"] != EXPECTED["author_v3_commit"]
        or v3_figure_comparison["published_plotted_result_units"] != 142
        or v3_figure_comparison["author_output_verified_units"] != 136
        or v3_figure_comparison["native_result_regenerated_units"] != 0
    ):
        raise ValueError("v3 figure comparison boundary changed")
    repository_history = json.loads(args.repository_history_json.read_text(encoding="utf-8"))
    validate_repository_history(repository_history)
    training_records, training_payload = fine_tuning_record_lineage(
        args.author_current,
        repository_history,
    )
    fork_branches, fork_summary = public_fork_audit(args.author_current)
    manuscripts = manuscript_provenance(args)
    source_inventory = author_source_inventory(args.author_v1, args.author_current, args.author_v3)
    v3_inventory = v3_source_inventory(args.author_v3)
    fama_french_rf = validate_fama_french(args.fama_french_archive)

    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "source_lineage.csv", source_rows())
    write_csv(output / "published_result_ledger_v1_v2.csv", v1)
    write_csv(output / "published_result_ledger_v3.csv", v3)
    write_csv(output / "figure_lineage_v1.csv", figures)
    write_csv(output / "figure_lineage_v3.csv", v3_figure_comparison["figures"])
    write_csv(output / "v3_source_inventory.csv", v3_inventory)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "prompt_inventory.csv", prompt_rows(args.v1_source, args.v3_source))
    write_csv(output / "internal_consistency_audit.csv", consistency_rows(v1, v3))
    write_csv(output / "artifact_access_audit.csv", artifact_rows())
    write_csv(output / "external_primary_source_audit.csv", external_primary_source_rows())
    write_csv(output / "public_fork_branch_ref_snapshot.csv", fork_branches)
    write_csv(output / "v1_v2_finetuning_record_lineage.csv", training_records)
    (output / "public_fork_census.json").write_text(
        json.dumps(fork_summary, indent=2) + "\n", encoding="utf-8"
    )
    (output / "native_execution.json").write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")
    (output / "native_execution_v3.json").write_text(json.dumps(v3_execution, indent=2) + "\n", encoding="utf-8")
    (output / "repository_history.json").write_text(json.dumps(repository_history, indent=2) + "\n", encoding="utf-8")
    (output / "v1_v2_finetuning_payload_summary.json").write_text(
        json.dumps(training_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "v3_author_output_summary.json").write_text(
        json.dumps(
            {
                "table_lineage": v3_table_lineage,
                "figure_lineage": v3_figure_comparison,
                "anonymous_artifact_readme_sha256": sha256_file(args.anonymous_v3_readme),
                "anonymous_readme_matches_v3_repository": True,
                "paper_result_credit": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "manuscript_provenance.json").write_text(json.dumps(manuscripts, indent=2) + "\n", encoding="utf-8")
    (output / "author_source_inventory.json").write_text(
        json.dumps(source_inventory, indent=2) + "\n", encoding="utf-8"
    )
    (output / "primary_source_validation.json").write_text(
        json.dumps(
            {
                "fama_french_archive_sha256": sha256_file(args.fama_french_archive),
                "fama_french_2025_monthly_rf_pct": fama_french_rf,
                "provider_source_count": 6,
                "paper_result_credit": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    v1_direct = [row for row in v1 if row["cell_kind"] == "direct_result"]
    v3_direct = [row for row in v3 if row["cell_kind"] == "direct_result"]
    v1_native_direct = [row for row in v1_direct if row["native_maci_output"]]
    v3_native_direct = [row for row in v3_direct if row["native_maci_output"]]
    manifest = {
        "audit": "MACI arXiv 2501.00826 multi-version paper/source/result audit",
        "overall_status": "both_lineages_have_incomplete_author_source_and_output_correspondence_zero_end_to_end_result_regeneration",
        "full_end_to_end_pipeline_reproduced": False,
        "v1_v2_published_table_units": len(v1),
        "v1_v2_direct_table_results": len(v1_direct),
        "v1_v2_unique_direct_measurements": len(v1_direct) - 3,
        "v1_v2_native_maci_direct_cells": len(v1_native_direct),
        "v1_v2_native_maci_unique_direct_measurements": len(v1_native_direct) - 3,
        "v1_v2_table_units_faithfully_regenerated": 0,
        "v1_v2_deleted_fine_tuning_message_records_recovered": repository_history["v1_v2_deleted_training_records"][
            "total_records"
        ],
        "v1_v2_fine_tuning_record_payloads_recovered": training_payload[
            "fine_tuning_format_records"
        ],
        "v1_v2_fine_tuning_image_references": training_payload["image_references"],
        "v1_v2_fine_tuning_unique_image_payloads_recovered": training_payload[
            "image_payloads_recovered"
        ],
        "v1_v2_fine_tuning_image_payload_bytes": training_payload[
            "image_payload_bytes"
        ],
        "v1_v2_fine_tuning_images_identical_at_current_head": training_payload[
            "image_payloads_identical_at_current_head"
        ],
        "v1_v2_fine_tuning_image_manifest_sha256": training_payload[
            "image_manifest_sha256"
        ],
        "v1_v2_historical_fine_tuning_payload_complete": training_payload[
            "historical_fine_tuning_files_have_complete_message_and_image_payloads"
        ],
        "v1_v2_historical_fine_tuning_files_added_after_paper_v2": training_payload[
            "dataset_added_after_paper_v2"
        ],
        "v1_v2_actual_fine_tuning_upload_job_checkpoint_recovered": False,
        "v1_v2_fine_tuning_payload_paper_result_credit": False,
        "v1_v2_public_history_commits_audited": repository_history["v1_v2_repository_history"]["commit_count"],
        "v1_v2_public_fork_census_date": fork_summary["census_date"],
        "v1_v2_public_forks_accessible": fork_summary["accessible_public_forks"],
        "v1_v2_public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
        "v1_v2_public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "v1_v2_public_fork_divergent_heads_audited": fork_summary["divergent_unique_heads"],
        "v1_v2_public_fork_unique_commits_beyond_official_history": fork_summary[
            "unique_commits_beyond_official_history"
        ],
        "v1_v2_public_fork_native_result_artifacts_found": fork_summary[
            "native_result_artifacts_found"
        ],
        "v3_published_table_units": len(v3),
        "v3_direct_table_results": len(v3_direct),
        "v3_unique_direct_measurements": len(v3_direct) - 4,
        "v3_native_maci_displayed_table_units": sum(bool(row["native_maci_output"]) for row in v3),
        "v3_native_maci_direct_cells": len(v3_native_direct),
        "v3_native_maci_unique_direct_measurements": len(v3_native_direct) - 4,
        "v3_table_units_faithfully_regenerated": 0,
        "v3_table_units_author_output_verified": v3_table_lineage["author_output_verified_units"],
        "v3_table_units_author_output_different": v3_table_lineage["author_output_different_units"],
        "v1_compiled_figure_assets": sum(bool(row["compiled_into_v1_pdf"]) for row in figures),
        "v1_compiled_figure_assets_with_author_output_correspondence": sum(
            bool(row["compiled_into_v1_pdf"]) for row in figures
        ),
        "v1_published_plotted_result_units_author_output_verified": sum(
            int(row["published_plotted_result_units"]) for row in figures if row["compiled_into_v1_pdf"]
        ),
        "v1_published_plotted_result_units_regenerated": 0,
        "v3_plotted_bars_lines_points": 142,
        "v3_plotted_bars_lines_points_author_output_verified": v3_figure_comparison["author_output_verified_units"],
        "v3_plotted_bars_lines_points_regenerated": 0,
        "v1_source_component_execution_passed": bool(execution.get("deterministic_component_harness_passed")),
        "v1_component_execution_is_paper_result_replication": False,
        "v3_source_files_recovered": len(v3_inventory),
        "v3_python_source_files_recovered": sum(row["path"].endswith(".py") for row in v3_inventory),
        "v3_public_history_commits_audited": repository_history["v3_repository_history"]["commit_count"],
        "v3_non_rag_architecture_component_paths_passed": v3_execution["architecture_component_execution"][
            "unmodified_non_rag_passed"
        ],
        "v3_non_rag_architecture_component_paths_denominator": v3_execution["architecture_component_execution"][
            "unmodified_non_rag_denominator"
        ],
        "v3_rag_architecture_paths_blocked_by_missing_source_module": v3_execution["architecture_component_execution"][
            "unmodified_rag_failures"
        ],
        "v3_runner_dry_run_with_labelled_data_overlay_passed": v3_execution["runner_dry_run_with_missing_data_overlay"][
            "passed"
        ],
        "v3_component_execution_is_paper_result_replication": False,
        "official_source_archives_hash_verified": 3,
        "manuscript_rebuilds_deterministic": all(row["rebuild_runs_byte_identical"] for row in manuscripts),
        "manuscript_rebuilds_visual_qa_passed": all(
            row["visual_qa"]["status"].startswith("passed_") for row in manuscripts
        ),
        "manuscript_rebuilds_are_result_replication": False,
        "provider_primary_sources_audited": 6,
        "fama_french_archive_hash_verified": True,
        "llm_calls_made": int(execution.get("llm_calls_made", 0)) + int(v3_execution["llm_calls_made"]),
        "paper_evidence_route_v1_v2": "public_code_available_incomplete_author_source",
        "paper_evidence_route_v3": "public_code_available_incomplete_author_source",
    }
    readme = """# MACI multi-version paper-level replication audit

Overall verdict: **not reproduced end to end**.

The same arXiv identifier contains two materially different experiments.
Versions 1--2 describe a four-expert, fine-tuned GPT-4o system over 2023--2024.
Version 3 replaces it with three multi-agent architectures, four capability
variants, three model families, and calendar-2025 data. Evidence is kept
strictly within its own lineage.

## Versions 1--2

The complete 164-commit, 7,997-object history of the first-author repository
is audited. The pre-submission source is genuine and substantial, and all 16
compiled manuscript figures have author-output correspondence, covering 21
plotted quantitative units. Complete history also recovers three deleted
fine-tuning-format JSONL files containing 962 system/user/assistant message
records. Every one of the 930 distinct referenced image URLs maps to a tracked,
valid 1000x800 RGBA PNG at the dataset commit; all 930 Git blobs are byte-identical
at the current official head and total 53,574,400 bytes. The 962 record-level
payloads and all referenced images are therefore recoverable, not merely URL
provenance. The files were added in May 2025 after paper v2, however, so this does
not prove they were the uploaded paper training set.

The public GitHub fork surface is also exhausted as of 2026-08-14. Both
accessible forks expose one `main` branch: one is exact at the official head
and the other is a three-commit-behind ancestor within the already audited
official history. Across two forks, two refs, and two unique heads, there are
zero divergent commits, unique blobs, tags, or additional native result
artifacts.

It is still not a paper-result reproduction. The exact fine-tuning upload/job,
selected checkpoint, test predictions, market/factor raw and processed inputs,
weekly universe, inference request/response logs, and portfolio arrays are absent.
**Zero of 321** table units and **zero of 21** plotted result units regenerate
from released inputs. The raw pre-submission source also fails its declared
Python 3.9 contract; a labelled later-constant overlay reaches deterministic
component checks but stops at missing blockchain data.

## Version 3

The paper's anonymous artifact was not absent: its public README API is
hash-pinned and byte-identical to the README in the first author's public
`cryptoMAS` repository. The complete 20-commit, 209-object history recovers 42
tracked files, including 24 Python files, all three claimed architectures,
rolling memory, skill indicators, portfolio execution, baselines, evaluation,
tables, and figures.

Author-output correspondence is strong but not regeneration. **394 of 442**
printed table units match the pinned repository tables: all 28 ablation units
and 366 of 414 performance units. The 48 differences are confined to LSTM,
Informer, and Autoformer. **136 of 142** plotted bars/paths/points have author
output correspondence: both 48-bar model-comparison PDFs are byte-identical,
and 20 of 23 portfolio paths plus 20 of 23 risk/return points match. **Zero of
442** table units and **zero of 142** plotted units regenerate from released
inputs.

The strict boundary is source incompleteness. `environ.data.coingecko`,
`environ.data.cointelegraph`, and `environ.data.rag_store` are absent from every
commit, so the raw runner fails before even displaying `--help`, RAG cannot
construct, and no frozen input or processed result record exists. The README
names a nonexistent fetch script, and `anthropic` is imported but undeclared.
The single-agent wrapper maps both RAG and Skill to zero-shot despite distinct
paper results, and source has no compulsory ReAct observation/action loop.

All nine non-RAG architecture/capability orchestration paths execute with
deterministic fixture agent outputs and no API calls. A labelled in-memory data
overlay also runs one dry-run week, and synthetic evaluation metrics execute.
These checks establish component behavior only and receive no paper-result
credit. The table-implied risk-free rate remains approximately zero rather than
the cited Fama--French series, and 20/23 bear rows remain inconsistent with the
printed cumulative-return/MDD definitions.

## Manuscript reconstruction

All three official PDFs and source archives are hash-pinned. Two independent
builds per version are byte-identical (14 pages for v1/v2 and 10 for v3), final
logs have no unresolved citations/references or TeX errors, and every official
and rebuilt page passed full-document visual review. These checks establish
faithful document reconstruction only; they do not fill any missing
experimental data, model records, or native result lineage.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256_file(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
