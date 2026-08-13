#!/usr/bin/env python3
"""Audit AlphaAgent paper v2 against both roots of its official repository.

The repository's default ``main`` branch is a July 2026 rewrite, but the same
public repository also retains a disjoint 485-commit ``legacy-main`` history
beginning in April 2024.  That history contains the preprint-era AlphaAgent
workflow, prompts, AST matcher, Qlib configurations, and factor-expression
artifacts.  This audit pins and executes an intact February 2025 mechanism
snapshot, records later preprint-cutoff breakage, and separately inventories the
2026 rewrite.  Source and component evidence never receives paper-result credit:
the paper's predictions, portfolios, returns, trials, and metric arrays remain
unreleased.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SOURCE_COMMIT = "b42cb397025510da44355db9dcf278304321f589"
SOURCE_URL = "https://github.com/RndmVariableQ/AlphaAgent"
SOURCE_FIRST_COMMIT = "7debd15ca98309a8df9c1d50aca3831f320687cf"
LEGACY_HEAD_COMMIT = "1da96e94a06a925c3997899f1848899440585efe"
LEGACY_ROOT_COMMIT = "c740262752b585bc59e41e26807d826ec7bebe75"
PAPER_MECHANISM_COMMIT = "95e47882cbed3ba0cafd42e812fe0032a8ae0681"
LATEST_FULL_TREE_PREPRINT_COMMIT = "3cbb7b7e9abe9bc3f3beaa7fcb2102293fbbea4a"
PREPRINT_CUTOFF_COMMIT = "0bc7a34ed9701a0149ae990b6484e7c73b347ea0"
ALPHAAGENT_INTRO_COMMIT = "7f041be0793600188be180e3df2acf5421c1c644"
PAPER_URL = "https://arxiv.org/pdf/2502.16789v2"
PAPER_SHA256 = "cf620c3b33a98edd4124230458b65741e1767fa37a3a180828de1035ded52ab1"
PAPER_V1_URL = "https://arxiv.org/pdf/2502.16789v1"
PAPER_V1_SHA256 = "943b286b40186ce03b8e39fc0dbd2f268807042c6192e9200e68972cb45ab890"
DEFAULT_SOURCE_PYTHON = "/nfs/roberts/project/pi_btk22/zc362/environments/bin/kt-python"
EXPECTED_SYNTHETIC_SHA256 = (
    "e0bd090308b893c6bcf97cc1589538e4fcedc4a896bb90d21a0848e92d7a5dc9"
)

PINNED_SOURCE_SHA256 = {
    "README.md": "b90839541fdb8d2f31ba75d868e614561791f6f4e6f020a3a04ae6d1cf4ca292",
    "pyproject.toml": "7b8c4e7fe00b45d476384cc1c48a368f004624834b7dd152d967c3eb1039e3c7",
    "configs/data.yaml": "f220cd2ffeade57b7de8ec6ffb8ecc4551821d38b9d333100500591272acdd14",
    "docs/data_release.md": "793389162defa295eebdb0c733f72615416a2d89a27168668019ad2a2e17afae",
    "docs/dev_log.md": "3d75eb4528e62a9043dfdb687716fa6d4323430419e47fe04b50738aca60785f",
    "scripts/factor_mining.py": "b0b6a52998a19bb471d7b475aaf82920c8c22387079b34716c4ac40ce4b671c0",
    "alphaagent/factor/mining/config.py": "776ddb5dd26886cabefe7f01796a52e39cdede709ca5ed9977de3cadeba5f660",
    "alphaagent/factor/mining/loop.py": "04f8af1a2f996ef8f7eff4d7f0dbe5309148d0910bc8807463b9f3eaad06a989",
    "alphaagent/factor/mining/prompts.py": "3001f33376935d9ab43e7491a30bd04cc3641fd96981a409b7b6dcc0aeccfbab",
    "alphaagent/factor/zoo/similarity.py": "50139fe8a1d1c9bd01d3e20a5c9bdfda5368d33539047e114fb029ad4552a48c",
    "alphaagent/dsl/core/parser.py": "8edb9dbdb0c1e3a9f64a283d7d48026a60d31a0b3b061b19fc03907c86f4b4f3",
    "artifacts/factorzoo/stock_1d/mining_delivered_registry.json": "4c7e3fad8ed6cc57284642ef827fd1619f5ed94529e555f006431ff9536bacd7",
    "artifacts/factorzoo/stock_1d/mls_fmb_percentiles.json": "a5ebe6b28af119b0ea430106516b694ac790a814656dfdd999c3ae42f646ebf5",
}

PAPER_MECHANISM_SHA256 = {
    "factor_zoo/alpha101.csv": "d08d678a4a9003cf9427faa1f7b0d1a682a652bc51183d9f1b743bd3043524b5",
    "rdagent/app/qlib_rd_loop/conf.py": "d69138aca91dd4709a6c66afd57a241ac88521375d6ae4fa608ac05a6fe21552",
    "rdagent/components/coder/factor_coder/expr_parser_tree.py": "4cd66f0c207080e86e887bfd24f5592ac861966a35c4080ed8d17cfbc49dd777",
    "rdagent/components/coder/factor_coder/prompts_alphaagent.yaml": "699459f9ab9d6d22ccfbadff9fd12f7bd97dd317e9ccbe79b53ebb3a5d309f3b",
    "rdagent/components/workflow/alphaagent_loop.py": "6ed8bcfd34a830cc568f36c091780eff6a777a4abecfd93f19d75258d9a23b75",
    "rdagent/scenarios/qlib/experiment/factor_template/conf_cn_combined.yaml": "a1bbb321adb86ae913a8d46133d7c53c805fa2090de0c2f8604e20cd960f89d2",
    "rdagent/scenarios/qlib/experiment/factor_template/conf_us.yaml": "1e9c967acfd772aae9f206e65e11d7556136e7971ea129f4a6ae90d754edd37b",
    "rdagent/scenarios/qlib/experiment/factor_template/conf_us_combined.yaml": "a9e5ac589020624ac255276c241bc4b8a69930f7220f68f8f14edb04a4fe1a6d",
    "rdagent/scenarios/qlib/proposal/factor_proposal.py": "8b550d509942c63f14b4ffccd50025b7e417a647904f9130f44198f0dc8f5ecd",
    "rdagent/scenarios/qlib/proposal/prompts_alphaagent.yaml": "65f65b096a910a7ec3f018e83b49ba2cf963179aa4b062a77b3a49915fa9f9a9",
}

METRICS = ("IC", "ICIR", "AR_pct", "IR", "MDD_pct")

# method|CSI500 five metrics|S&P500 five metrics
TABLE_2_TEXT = """
LSTM|0.0175|0.1521|4.96|0.6225|-9.68|0.0028|0.0181|-1.51|-0.1671|-26.05
Transformer|0.0131|0.1074|4.11|0.5074|-17.45|0.0013|0.0129|-4.55|-0.4964|-34.96
LightGBM|0.0120|0.1209|-1.18|-0.1588|-18.97|0.0011|0.0116|-2.64|-0.4224|-21.17
TRA|0.0198|0.1794|2.91|0.4261|-12.73|-0.0003|-0.0027|-8.51|-1.1345|-49.55
Stock-Mixer|0.0000|0.0003|-0.35|-0.0496|-16.82|0.0030|0.0312|-2.49|-0.3342|-29.43
AlphaForge|0.0146|0.1299|3.45|0.3270|-17.67|0.0026|0.0240|2.45|0.3369|-10.91
RD-Agent|0.0113|0.0872|0.78|0.0744|-20.85|0.0019|0.0123|1.69|0.1664|-23.18
DeepSeek-R1 best-of-10|0.0132|0.1201|1.58|0.2086|-14.95|0.0048|0.0369|2.75|0.2400|-15.34
OpenAI-o1 best-of-10|0.0159|0.1502|0.46|0.0632|-21.29|0.0028|0.0217|2.29|0.2021|-16.35
AlphaAgent|0.0212|0.1938|11.00|1.488|-9.36|0.0056|0.0552|8.74|1.0545|-9.10
"""

DATASET_SPLITS = (
    ("S&P500", "training", "2015-01", "2019-12", 1258),
    ("S&P500", "validation", "2020-01", "2020-12", 253),
    ("S&P500", "testing", "2021-01", "2025-01", 1004),
    ("CSI500", "training", "2015-01", "2019-12", 1219),
    ("CSI500", "validation", "2020-01", "2020-12", 243),
    ("CSI500", "testing", "2021-01", "2025-01", 968),
)

BASE_FACTOR_EXPRESSIONS = {
    "intraday_return": "DIVIDE(SUBTRACT($close, $open), $open)",
    "daily_return": "SUBTRACT(DIVIDE($close, DELAY($close, 1)), 1)",
    "relative_volume_20d": "DIVIDE($volume, TS_MEAN($volume, 20))",
    "normalized_daily_range": "DIVIDE(SUBTRACT($high, $low), DELAY($close, 1))",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def git_files(root: Path) -> list[str]:
    output = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in output.splitlines() if line]


def git_output(root: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=check,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def git_tree_files(root: Path, commit: str) -> list[str]:
    output = git_output(
        root, "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", commit
    )
    return [line for line in output.splitlines() if line]


def git_commit_record(root: Path, commit: str) -> dict[str, str]:
    commit_hash, date, subject = git_output(
        root, "show", "-s", "--format=%H|%aI|%s", commit
    ).split("|", 2)
    return {"commit": commit_hash, "date": date, "subject": subject}


def extract_git_commit(source_root: Path, commit: str, destination: Path) -> None:
    with tempfile.NamedTemporaryFile(
        prefix=f"alphaagent-{commit[:12]}-", suffix=".tar", dir=destination.parent, delete=False
    ) as handle:
        archive_path = Path(handle.name)
    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(source_root),
                "archive",
                "--format=tar",
                f"--output={archive_path}",
                commit,
            ],
            check=True,
        )
        with tarfile.open(archive_path) as archive:
            try:
                archive.extractall(destination, filter="fully_trusted")
            except TypeError:  # pragma: no cover - Python versions before filter support
                archive.extractall(destination)
    finally:
        archive_path.unlink(missing_ok=True)


def history_audit(source_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    roots = sorted(git_output(source_root, "rev-list", "--all", "--max-parents=0").splitlines())
    merge_base = subprocess.run(
        ["git", "-C", str(source_root), "merge-base", SOURCE_COMMIT, LEGACY_HEAD_COMMIT],
        check=False,
        capture_output=True,
        text=True,
    )
    facts: dict[str, Any] = {
        "is_shallow": git_output(source_root, "rev-parse", "--is-shallow-repository") == "true",
        "reachable_commits": int(git_output(source_root, "rev-list", "--all", "--count")),
        "current_main_commits": int(git_output(source_root, "rev-list", SOURCE_COMMIT, "--count")),
        "legacy_main_commits": int(git_output(source_root, "rev-list", LEGACY_HEAD_COMMIT, "--count")),
        "root_commits": roots,
        "current_and_legacy_have_common_ancestor": merge_base.returncode == 0,
        "paper_mechanism_is_legacy_ancestor": subprocess.run(
            ["git", "-C", str(source_root), "merge-base", "--is-ancestor", PAPER_MECHANISM_COMMIT, LEGACY_HEAD_COMMIT],
            check=False,
        ).returncode
        == 0,
        "preprint_cutoff_is_legacy_ancestor": subprocess.run(
            ["git", "-C", str(source_root), "merge-base", "--is-ancestor", PREPRINT_CUTOFF_COMMIT, LEGACY_HEAD_COMMIT],
            check=False,
        ).returncode
        == 0,
        "paper_mechanism_files": len(git_tree_files(source_root, PAPER_MECHANISM_COMMIT)),
        "paper_mechanism_python_files": sum(
            path.endswith(".py") for path in git_tree_files(source_root, PAPER_MECHANISM_COMMIT)
        ),
        "paper_mechanism_factor_csvs": sum(
            path.startswith("factor_zoo/") and path.endswith(".csv")
            for path in git_tree_files(source_root, PAPER_MECHANISM_COMMIT)
        ),
        "preprint_cutoff_factor_csvs": sum(
            path.startswith("factor_zoo/") and path.endswith(".csv")
            for path in git_tree_files(source_root, PREPRINT_CUTOFF_COMMIT)
        ),
    }
    expected: dict[str, Any] = {
        "is_shallow": False,
        "reachable_commits": 493,
        "current_main_commits": 8,
        "legacy_main_commits": 485,
        "root_commits": sorted([SOURCE_FIRST_COMMIT, LEGACY_ROOT_COMMIT]),
        "current_and_legacy_have_common_ancestor": False,
        "paper_mechanism_is_legacy_ancestor": True,
        "preprint_cutoff_is_legacy_ancestor": True,
        "paper_mechanism_files": 856,
        "paper_mechanism_python_files": 331,
        "paper_mechanism_factor_csvs": 15,
        "preprint_cutoff_factor_csvs": 0,
    }
    if facts != expected:
        raise RuntimeError(f"Pinned two-root Git history changed: {facts!r}")

    timeline = [
        (LEGACY_ROOT_COMMIT, "legacy history begins"),
        (ALPHAAGENT_INTRO_COMMIT, "AlphaAgent workflow first appears"),
        (PAPER_MECHANISM_COMMIT, "mechanism-complete snapshot pinned for component audit"),
        (LATEST_FULL_TREE_PREPRINT_COMMIT, "latest full tree before cleanup; Alpha101 path is regressed"),
        (PREPRINT_CUTOFF_COMMIT, "latest commit before arXiv v1; factor_zoo removed"),
        (LEGACY_HEAD_COMMIT, "public legacy-main head"),
        (SOURCE_FIRST_COMMIT, "disjoint rewritten main begins"),
        (SOURCE_COMMIT, "pinned rewritten main head"),
    ]
    rows = []
    for commit, role in timeline:
        item = git_commit_record(source_root, commit)
        rows.append({**item, "role": role})
    return facts, rows


def git_first_commit(root: Path) -> tuple[str, str]:
    output = subprocess.run(
        ["git", "-C", str(root), "log", "--reverse", "--format=%H|%aI"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    commit, date = output[0].split("|", 1)
    return commit, date


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_numeric_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for market, split, start, end, days in DATASET_SPLITS:
        rows.append(
            {
                "paper_table": 1,
                "entity": split,
                "market": market,
                "period": f"{start} to {end}",
                "metric": "trading_days",
                "paper_value": float(days),
                "cell_role": "configuration",
            }
        )
    for line in TABLE_2_TEXT.strip().splitlines():
        method, *values = line.split("|")
        if len(values) != 10:
            raise RuntimeError(f"Malformed Table 2 row: {line}")
        for market, part in zip(("CSI500", "S&P500"), (values[:5], values[5:])):
            for metric, value in zip(METRICS, part):
                rows.append(
                    {
                        "paper_table": 2,
                        "entity": method,
                        "market": market,
                        "period": "2021-01-01 to 2024-12-31",
                        "metric": metric,
                        "paper_value": float(value),
                        "cell_role": "result",
                    }
                )
    if Counter(row["paper_table"] for row in rows) != {1: 6, 2: 100}:
        raise RuntimeError("Paper numeric-cell denominator changed")
    if Counter(row["cell_role"] for row in rows) != {
        "result": 100,
        "configuration": 6,
    }:
        raise RuntimeError("Paper result/configuration boundary changed")
    return rows


def table_conformance() -> list[dict[str, Any]]:
    rows = []
    for row in paper_numeric_rows():
        if row["cell_role"] == "result":
            status = "unavailable_missing_native_paper_result_path"
            reason = (
                "paper-era source and factor expressions survive in Git history, but no "
                "prediction, holding, return, recorder, baseline output, or metric file survives"
            )
        else:
            status = "paper_configuration_recovered_without_frozen_dataset"
            reason = (
                "preprint-era Qlib configs recover the market/split protocol, but the exact "
                "Baostock/Yahoo panels and their trading-day calendars are not shipped"
            )
        rows.append(
            {
                **row,
                "native_reproduced_value": "",
                "absolute_difference": "",
                "status": status,
                "reason": reason,
            }
        )
    return rows


def published_non_table_claims() -> list[dict[str, Any]]:
    raw = [
        ("Figure 3/text", "CSI500 cumulative excess return", 45.0, "pct", "approximate", "result"),
        ("Figure 3/text", "S&P500 cumulative excess return", 37.0, "pct", "lower_bound", "result"),
        ("Figure 4", "yearly evaluation periods", 5.0, "years", "exact", "configuration"),
        ("Figure 4 caption", "AlphaAgent factors in decay plot", 15.0, "factors", "exact", "configuration"),
        ("Figure 4/text", "AlphaAgent yearly IC", 0.02, "IC", "approximate", "result"),
        ("Figure 4/text", "AlphaAgent yearly RankIC", 0.025, "RankIC", "approximate", "result"),
        ("Section 4.5", "evolution rounds in ablation", 100.0, "rounds", "exact", "configuration"),
        ("Section 4.5", "rounds per market in ablation", 50.0, "rounds", "exact", "configuration"),
        ("Figure 6", "AlphaAgent hit ratio", 0.29, "ratio", "exact", "result"),
        ("Figure 6", "hit ratio without factor constraints", 0.16, "ratio", "exact", "result"),
        ("Section 4.5", "hit-ratio improvement", 81.0, "pct", "exact", "result"),
        ("Figure 6", "AlphaAgent development success rate", 0.83, "ratio", "exact", "result"),
        ("Figure 6", "development success without symbolic assembly", 0.75, "ratio", "exact", "result"),
        ("Figure 6", "AlphaAgent normalized token efficiency", 1.0, "ratio", "exact", "result"),
        ("Figure 6", "token efficiency without symbolic assembly", 0.81, "ratio", "exact", "result"),
        ("Section 4.5", "token-efficiency improvement", 23.0, "pct", "exact", "result"),
        ("Figure 7/text", "DeepSeek-R1 AlphaAgent ICIR", 0.0615, "ICIR", "exact", "result"),
        ("Figure 7/text", "DeepSeek-R1 AlphaAgent annualized return", 9.19, "pct", "exact", "result"),
        ("Figure 7/text", "DeepSeek-R1 AlphaAgent maximum drawdown", -6.50, "pct", "exact", "result"),
        ("Section 4.5", "GPT-3.5 AlphaAgent-vs-RD-Agent IC p-value", 0.0311, "p_value", "exact", "result"),
        ("Section 4.5", "Qwen-Plus AlphaAgent-vs-RD-Agent IC p-value", 0.0109, "p_value", "exact", "result"),
        ("Section 4.5", "DeepSeek-R1 AlphaAgent-vs-RD-Agent IC p-value", 0.0382, "p_value", "exact", "result"),
        ("Section 4.3", "independent trials for RD-Agent and AlphaAgent", 20.0, "trials", "exact", "configuration"),
        ("Section 4.3", "evolution rounds per trial", 5.0, "rounds", "exact", "configuration"),
        ("Table 2/method", "reasoning-model best-of candidates", 10.0, "candidates", "exact", "configuration"),
        ("Section 4.3", "reasoning-model iterative rounds", 5.0, "rounds", "exact", "configuration"),
    ]
    rows = []
    for location, claim, value, unit, exactness, role in raw:
        rows.append(
            {
                "paper_location": location,
                "claim": claim,
                "paper_value": value,
                "unit": unit,
                "exactness": exactness,
                "claim_role": role,
                "native_reproduced_value": "",
                "status": "unavailable_missing_native_paper_result_path"
                if role == "result"
                else "paper_configuration_recovered_without_complete_trial_inputs",
                "paper_result_credit": False,
            }
        )
    if Counter(row["claim_role"] for row in rows) != {
        "result": 18,
        "configuration": 8,
    }:
        raise RuntimeError("Non-table claim boundary changed")
    return rows


def specification_gaps() -> list[dict[str, Any]]:
    raw = [
        ("regularizer_weights", "alpha_1, alpha_2, alpha_3 are not disclosed", "blocks exact objective"),
        ("er_weights", "beta_1, beta_2, beta_3 are not disclosed", "blocks exact ER score"),
        ("similarity_normalization", "S(f) scaling to [0,1] is not defined", "blocks originality threshold"),
        ("alignment_sign", "C is added to a score said to be better when lower although C is better when higher", "objective sign is ambiguous"),
        ("constraint_thresholds", "no SL, PC, ER acceptance thresholds are disclosed", "blocks factor filter"),
        ("operator_library", "a large paper-era operator library is recovered, but the paper does not pin an exact library revision", "blocks proof of expression equivalence"),
        ("prompts", "paper-era idea/factor/eval prompts are recovered, but prompt/API versions used for every reported trial are not identified", "blocks exact agent replay"),
        ("llm_sampling", "temperature, seeds, API snapshots, and token limits are absent", "blocks stochastic replay"),
        ("seed_hypotheses", "initial research directions and all 20 trial inputs are absent", "blocks search replay"),
        ("factor_outputs", "multiple paper-era factor pools survive, including a 15-row CN candidate file, but no lineage proves which exact pools generated each paper panel", "blocks final model-input identity"),
        ("lightgbm", "the paper-era configs recover the full LightGBM kwargs, but the trained model state and random seeds are absent", "blocks fitted-model identity"),
        ("universe", "constituent histories, delisting rules, adjustment rules, and filters are absent", "blocks panel identity"),
        ("portfolio", "paper-era Qlib configs recover top-k/drop, benchmark, price, limits, account and recorders, but not the exact executed recorder/config lineage", "blocks result provenance"),
        ("transaction_costs", "paper-era configs recover fees, min costs, deal price and price-limit threshold, but frozen market-state/suspension inputs are absent", "blocks exact net returns"),
        ("trial_aggregation", "the aggregation/selection from 20 trials to Table 2 is not fully specified", "blocks metric target"),
        ("figure_arrays", "underlying daily curves, yearly values, and round distributions are absent", "blocks figure reproduction"),
        ("p_value_samples", "the IC samples used in the three Student t tests are absent", "blocks p-value reproduction"),
    ]
    return [
        {"dimension": dimension, "missing_specification": gap, "consequence": consequence}
        for dimension, gap, consequence in raw
    ]


def current_source_conformance(source_root: Path) -> list[dict[str, Any]]:
    parser_text = (source_root / "alphaagent/dsl/core/parser.py").read_text(encoding="utf-8")
    sim_text = (source_root / "alphaagent/factor/zoo/similarity.py").read_text(encoding="utf-8")
    prompt_text = (source_root / "alphaagent/factor/mining/prompts.py").read_text(encoding="utf-8")
    loop_text = (source_root / "alphaagent/factor/mining/loop.py").read_text(encoding="utf-8")
    config_text = (source_root / "alphaagent/factor/mining/config.py").read_text(encoding="utf-8")
    readme = (source_root / "README.md").read_text(encoding="utf-8")
    dev_log = (source_root / "docs/dev_log.md").read_text(encoding="utf-8")

    checks = [
        ("paper_era_source", "paper implementation released by June 2025", "first commit 2026-07-01", "mismatch_post_paper_rewrite", False),
        ("paper_markets", "CSI500 and S&P500", "CSI1000/A-shares reference dataset", "mismatch", False),
        ("paper_data_sources", "Baostock and Yahoo Finance", "Tushare/open parquet package", "mismatch", False),
        ("paper_input_fields", "OHLCV only", "price, fundamentals, industry, and market-cap fields", "mismatch", False),
        ("paper_test_period", "2021-01 to 2025-01", "default validation 2022-01 to 2024-12", "mismatch", False),
        ("paper_llm", "GPT-3.5-turbo", "gpt-4o-mini dataclass default; CLI requires MODEL", "mismatch", False),
        ("three_specialized_agents", "idea agent, factor agent, eval agent", "one tool-calling trajectory/AgentScope agent", "mismatch", False),
        ("structured_idea_agent", "observation/knowledge/justification/specification", "not implemented as a distinct typed stage", "missing", False),
        ("factor_agent_memory", "successful and failed implementations with failure modes", "delivered-factor registry only", "mismatch", False),
        ("eval_agent", "backtest plus similarity and performance feedback", "train/validation expression evaluation tools", "component_analogue", True),
        ("operator_library", "symbolic operator library", "native DSL operator registry", "component_match", True),
        ("ast_representation", "tree-valued AST T(f)", "pyparsing compiles to Python code strings", "mismatch", False),
        ("largest_common_subtree", "recursive subtree isomorphism size", "not implemented", "missing", False),
        ("alpha101_novelty_zoo", "compare against Alpha101", "no Alpha101 expressions or loader", "missing", False),
        ("similarity_kind", "AST structural similarity", "mean daily cross-sectional Pearson correlation", "mismatch", False),
        ("symbolic_length", "algorithmic SL(f)", "no computation or threshold", "missing", False),
        ("parameter_count", "algorithmic PC(f)", "no computation or threshold", "missing", False),
        ("alignment_c1", "LLM hypothesis-description consistency", "not implemented", "missing", False),
        ("alignment_c2", "LLM description-expression consistency", "not implemented", "missing", False),
        ("alignment_alpha", "alpha=0.5", "no scoring function", "missing", False),
        ("er_score", "beta-weighted novelty/alignment/feature penalty", "no scoring function", "missing", False),
        ("feedback_loop", "metrics guide later iterations", "tool results appended to LLM context", "component_match", True),
        ("multiple_candidates", "multiple expressions per hypothesis", "prompt requests 3--5 parallel train evaluations", "component_analogue", True),
        ("paper_lightgbm", "LightGBM next-day return model, depth 4", "model directory remains TODO", "missing", False),
        ("paper_qlib_backtest", "Qlib top-k dropout strategy", "no portfolio/backtest package", "missing", False),
        ("paper_transaction_fees", "market-specific buy/sell fees", "no paper backtest implementation", "missing", False),
        ("paper_baselines", "nine baselines in Table 2", "no exact baseline runners", "missing", False),
        ("paper_trials", "20 trials x 5 rounds", "no exact runner, seeds, or trajectories", "missing", False),
        ("paper_outputs", "15 factors, curves, predictions, holdings, returns, metrics", "post-paper registry metrics only", "missing", False),
        ("current_registry", "paper final factors", "8 post-paper delivered factors", "provenance_mismatch", False),
        ("current_expressions", "paper factor pool", "13 post-paper DSL expressions", "provenance_mismatch", False),
        ("current_data_release", "paper CSI500/S&P500 frozen panels", "2026 CSI1000 Tushare package", "provenance_mismatch", False),
    ]
    if "parse_multi_line_expression" not in parser_text:
        raise RuntimeError("Pinned parser implementation changed")
    if 'SIMILARITY_KIND = "cross_sectional_pearson_mean"' not in sim_text:
        raise RuntimeError("Pinned similarity implementation changed")
    if "3～5" not in prompt_text or "eval_on_train_set" not in prompt_text:
        raise RuntimeError("Pinned mining prompt changed")
    if "messages.append" not in loop_text or 'model: str = "gpt-4o-mini"' not in config_text:
        raise RuntimeError("Pinned mining loop/config changed")
    if "CSI 1000" not in readme or "Tushare" not in readme:
        raise RuntimeError("Pinned README provenance changed")
    if "model/" not in dev_log or "backtest/" not in dev_log:
        raise RuntimeError("Pinned development-state evidence changed")
    return [
        {
            "dimension": dimension,
            "paper_requirement": paper,
            "released_implementation": released,
            "status": status,
            "paper_mechanism_credit": credit,
        }
        for dimension, paper, released, status, credit in checks
    ]


def paper_era_source_conformance(snapshot_root: Path) -> list[dict[str, Any]]:
    proposal = (snapshot_root / "rdagent/scenarios/qlib/proposal/factor_proposal.py").read_text()
    workflow = (snapshot_root / "rdagent/components/workflow/alphaagent_loop.py").read_text()
    conf = (snapshot_root / "rdagent/app/qlib_rd_loop/conf.py").read_text()
    ast = (snapshot_root / "rdagent/components/coder/factor_coder/expr_parser_tree.py").read_text()
    coder_prompt = (
        snapshot_root / "rdagent/components/coder/factor_coder/prompts_alphaagent.yaml"
    ).read_text()
    cn = (
        snapshot_root
        / "rdagent/scenarios/qlib/experiment/factor_template/conf_cn_combined.yaml"
    ).read_text()
    us = (
        snapshot_root
        / "rdagent/scenarios/qlib/experiment/factor_template/conf_us_combined.yaml"
    ).read_text()
    llm_conf = (snapshot_root / "rdagent/oai/llm_conf.py").read_text()

    required = {
        "structured_hypothesis": "class AlphaAgentHypothesis" in proposal
        and "concise_specification" in proposal,
        "alpha101_loader": 'pd.read_csv("factor_zoo/alpha101.csv"' in proposal,
        "duplicate_filter": "duplicated_subtree_size >= 5" in proposal,
        "trace_feedback": "self.trace.hist.append" in workflow,
        "five_rounds": "evolving_n: int = 5" in conf,
        "largest_subtree": "def find_largest_common_subtree" in ast,
        "factor_alignment_prompt": "factor expression is align with the factor description"
        in coder_prompt,
        "cn_market": "market: &market csi500" in cn,
        "us_market": "market: &market SP500" in us,
        "cn_top50": "topk: 50" in cn and "n_drop: 5" in cn,
        "us_top50": "topk: 50" in us and "n_drop: 5" in us,
        "lightgbm_depth": "max_depth: 4" in cn and "max_depth: 4" in us,
        "default_llm_mismatch": 'chat_model: str = "gpt-4-turbo"' in llm_conf,
    }
    if not all(required.values()):
        raise RuntimeError(f"Pinned paper-era AlphaAgent mechanism changed: {required!r}")

    checks = [
        ("paper_era_source", "paper implementation available before the February 2025 preprint", "public legacy-main snapshot dated 2025-02-12", "recovered_preprint_source", True),
        ("paper_markets", "CSI500 and S&P500", "csi500 and SP500 Qlib configs", "component_match", True),
        ("paper_data_sources", "Baostock and Yahoo Finance", "Baostock URI is explicit; US uses an unversioned local us_data URI with no downloader provenance", "partial_source_match", True),
        ("paper_input_fields", "four OHLCV-derived base features", "the same four feature formulas and next-day label", "component_match", True),
        ("paper_test_period", "2021-01 through 2024-12", "2021-01-01 through 2024-12-30/31", "component_match", True),
        ("paper_llm", "GPT-3.5-turbo", "repository default is gpt-4-turbo; executed model selection is not pinned", "mismatch", False),
        ("three_specialized_agents", "idea, factor, and eval agents", "hypothesis generator, factor constructor/parser, runner/summarizer stages", "component_match", True),
        ("structured_idea_agent", "observation, knowledge, justification, specification", "typed AlphaAgentHypothesis has all four fields", "component_match", True),
        ("factor_agent_memory", "successful and failed implementations with failure modes", "Trace plus CoSTEER successful/failed knowledge stores", "component_match", True),
        ("eval_agent", "execution, stability, backtest and metric feedback", "factor evaluator, Qlib runner and LLM feedback summarizer", "component_match", True),
        ("operator_library", "symbolic operator library", "full function library and prompt semantics", "component_match", True),
        ("ast_representation", "tree-valued AST T(f)", "typed pyparsing Var/Number/Function/Binary/Conditional nodes", "component_match", True),
        ("largest_common_subtree", "recursive subtree isomorphism size", "find_largest_common_subtree executes and counts nodes", "component_match", True),
        ("alpha101_novelty_zoo", "compare against Alpha101", "loader and 101 named Alpha rows exist, but 15 generated rows contaminate the loaded 116-row file", "partial_contaminated_reference_zoo", True),
        ("similarity_kind", "AST structural largest-common-subtree similarity", "same structural operation, including commutative operators", "component_match", True),
        ("symbolic_length", "algorithmic SL(f)", "no SL term or weight is implemented", "missing", False),
        ("parameter_count", "algorithmic PC(f)", "no free-parameter count or weight is implemented", "missing", False),
        ("alignment_c1", "numeric hypothesis-description consistency", "hypothesis conditions factor generation, but no separate numeric c1 evaluator exists", "prompt_only_no_score", False),
        ("alignment_c2", "numeric description-expression consistency", "LLM evaluator checks the same semantic relation but returns prose, not a [0,1] score", "component_analogue", True),
        ("alignment_alpha", "alpha=0.5", "no combined numeric alignment function", "missing", False),
        ("er_score", "beta-weighted novelty/alignment/feature penalty", "no beta-weighted ER function; novelty is a hard retry at subtree size >=5", "mismatch_hard_filter", False),
        ("feedback_loop", "metrics guide later iterations", "runner metrics and feedback are appended to Trace and rendered into the next prompts", "component_match", True),
        ("multiple_candidates", "multiple expressions per hypothesis", "prompt requests 2--4 factors and constructor processes every response entry", "component_match", True),
        ("paper_lightgbm", "LightGBM next-day return model, depth 4", "full LGBModel kwargs and DatasetH segments are recovered", "configuration_match", True),
        ("paper_qlib_backtest", "Qlib top-50/drop-5 strategy", "combined CN/US configs use TopkDropoutStrategy topk=50, n_drop=5 and recorders", "configuration_match", True),
        ("paper_transaction_fees", "CN 5/15 bp and US 0/5 bp buy/sell fees", "matching open/close costs plus deal price, limit threshold and min costs", "configuration_match", True),
        ("paper_baselines", "nine Table 2 baselines", "named GP, o1 and DeepSeek factor-expression CSVs exist, but no exact baseline runners or outputs", "partial_unlinked_artifacts", False),
        ("paper_trials", "20 trials x 5 rounds", "evolving_n=5 is recovered; no 20-trial launcher, seeds or trajectories", "partial_configuration", False),
        ("paper_outputs", "factors, curves, predictions, holdings, returns and metrics", "factor-expression pools exist; result-bearing artifacts do not", "partial_factor_expressions_only", False),
        ("current_registry", "paper final factors", "8 entries from the disjoint 2026 rewrite", "provenance_mismatch", False),
        ("current_expressions", "paper factor pool", "13 expressions from the disjoint 2026 DSL", "provenance_mismatch", False),
        ("current_data_release", "paper CSI500/S&P500 frozen panels", "2026 CSI1000 Tushare package", "provenance_mismatch", False),
    ]
    return [
        {
            "dimension": dimension,
            "paper_requirement": paper,
            "released_implementation": released,
            "status": status,
            "paper_mechanism_credit": credit,
        }
        for dimension, paper, released, status, credit in checks
    ]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for relative in git_files(source_root):
        path = source_root / relative
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "paper_era_artifact": False,
                "paper_result_credit": False,
            }
        )
    return rows


def paper_era_source_inventory(
    source_root: Path, snapshot_root: Path
) -> list[dict[str, Any]]:
    rows = []
    for relative in git_tree_files(source_root, PAPER_MECHANISM_COMMIT):
        path = snapshot_root / relative
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "paper_era_artifact": True,
                "paper_result_credit": False,
            }
        )
    return rows


def paper_era_factor_rows(snapshot_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((snapshot_root / "factor_zoo").glob("*.csv")):
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = list(csv.reader(handle))
        if not reader:
            raise RuntimeError(f"Empty paper-era factor file: {path}")
        expression_rows = len(reader) - 1
        alpha101_reference_rows = min(101, expression_rows) if path.name == "alpha101.csv" else 0
        rows.append(
            {
                "path": f"factor_zoo/{path.name}",
                "expression_rows": expression_rows,
                "alpha101_reference_rows": alpha101_reference_rows,
                "other_expression_rows": expression_rows - alpha101_reference_rows,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "directly_referenced_by_alphaagent_code": path.name == "alpha101.csv",
                "paper_result_credit": False,
                "interpretation": (
                    "Alpha101 reference plus 15 appended generated expressions"
                    if path.name == "alpha101.csv"
                    else "author-released preprint-era factor-expression artifact with no result lineage"
                ),
            }
        )
    if len(rows) != 15 or sum(int(row["expression_rows"]) for row in rows) != 268:
        raise RuntimeError("Pinned paper-era factor inventory changed")
    return rows


def run_paper_era_component_checks(
    snapshot_root: Path, source_python: Path
) -> dict[str, Any]:
    compile_result = subprocess.run(
        [str(source_python), "-m", "compileall", "-q", str(snapshot_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    if compile_result.stdout or compile_result.stderr:
        raise RuntimeError(
            "Paper-era compile emitted unexpected output:\n"
            + compile_result.stdout
            + compile_result.stderr
        )
    program = r"""
import importlib.util, json, sys
from pathlib import Path
import pandas as pd

root = Path(sys.argv[1])
path = root / 'rdagent/components/coder/factor_coder/expr_parser_tree.py'
spec = importlib.util.spec_from_file_location('alphaagent_paper_era_expr_parser', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

def score(left, right):
    match = module.compare_expressions(left, right)
    return None if match is None else match.size

factor_df = pd.read_csv(root / 'factor_zoo/alpha101.csv')
probe = str(factor_df.iloc[0, 1])
self_score, subtree, matched = module.match_alphazoo(probe, factor_df)
print(json.dumps({
    'identical_expression_lcs_size': score('RANK(DELTA($open, 1))', 'RANK(DELTA($open, 1))'),
    'commutative_expression_lcs_size': score('$open + $close', '$close + $open'),
    'partial_expression_lcs_size': score('MEAN($close, 10) + STD($volume, 5)', 'MEAN($close, 10) - MAX($open, 2)'),
    'loaded_alpha101_csv_rows': len(factor_df),
    'named_alpha101_reference_rows': int(factor_df['factor_name'].astype(str).str.match(r'^Alpha#\d+$').sum()),
    'alpha101_self_match_lcs_size': self_score,
    'alpha101_self_match_exact': matched == probe,
    'alpha101_self_match_subtree_present': subtree is not None,
}, sort_keys=True))
"""
    outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(source_python), "-c", program, str(snapshot_root)],
            cwd=snapshot_root,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(json.loads(completed.stdout))
    if outputs[0] != outputs[1]:
        raise RuntimeError("Paper-era AST component is not deterministic")
    expected = {
        "identical_expression_lcs_size": 4,
        "commutative_expression_lcs_size": 3,
        "partial_expression_lcs_size": 3,
        "loaded_alpha101_csv_rows": 116,
        "named_alpha101_reference_rows": 101,
        "alpha101_self_match_lcs_size": 23,
        "alpha101_self_match_exact": True,
        "alpha101_self_match_subtree_present": True,
    }
    if outputs[0] != expected:
        raise RuntimeError(f"Pinned paper-era AST behavior changed: {outputs[0]!r}")
    return {
        "snapshot_commit": PAPER_MECHANISM_COMMIT,
        "python_files_compiled": 331,
        "compile_passed": True,
        "ast_component_runs": 2,
        "ast_component_deterministic": True,
        **outputs[0],
        "network_or_llm_calls": False,
        "paper_result_reproduction": False,
    }


def current_registry_rows(source_root: Path) -> list[dict[str, Any]]:
    registry = json.loads(
        (source_root / "artifacts/factorzoo/stock_1d/mining_delivered_registry.json").read_text(
            encoding="utf-8"
        )
    )
    rows = []
    for factor_id, item in sorted(registry.items()):
        metrics = item.get("ingest_metrics", {})
        config = item.get("ingest_config", {})
        rows.append(
            {
                "factor_id": factor_id,
                "ingested_at": item.get("ingested_at", ""),
                "label_col": config.get("label_col", ""),
                "eval_start": metrics.get("eval_start", ""),
                "eval_end": metrics.get("eval_end", ""),
                "ic": metrics.get("ic", ""),
                "icir": metrics.get("icir", ""),
                "rank_ic": metrics.get("rank_ic", ""),
                "paper_result_credit": False,
                "reason": "post-paper CSI1000/Tushare artifact, not a paper factor/output",
            }
        )
    return rows


def data_release_provenance() -> list[dict[str, Any]]:
    return [
        {
            "artifact": "alphaagent-data-20260703.zip",
            "official_share_url": "https://pan.baidu.com/s/1GsCl6McyoHyws5bl571HqQ?pwd=5qp5",
            "share_file_id": "640389739420941",
            "bytes": 524248466,
            "observed_available": True,
            "observed_on": "2026-08-11",
            "dataset_claim": "CSI1000 union, Tushare, 2015-01 through 2026-06",
            "paper_requirement": "CSI500 Baostock and S&P500 Yahoo Finance through 2025-01",
            "paper_data_credit": False,
            "status": "available_post_paper_data_with_wrong_markets_source_and_vintage",
        }
    ]


def _run_source_tests(source_root: Path, source_python: Path) -> dict[str, Any]:
    program = r"""
import sys, types, pytest
mods = {}
for name in ['tushare', 'agentscope', 'agentscope.agent', 'agentscope.event', 'agentscope.message']:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    mods[name] = mod
mods['tushare'].pro_api = lambda *args, **kwargs: None
mods['agentscope.agent'].Agent = type('Agent', (), {})
for name in ['ConfirmResult', 'EventType', 'UserConfirmResultEvent']:
    setattr(mods['agentscope.event'], name, type(name, (), {}))
mods['agentscope.message'].UserMsg = type('UserMsg', (), {})
raise SystemExit(pytest.main(['tests', '-q']))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root)
    completed = subprocess.run(
        [str(source_python), "-c", program],
        cwd=source_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    combined = completed.stdout + completed.stderr
    if "80 passed" not in combined:
        raise RuntimeError(f"Pinned source test count changed:\n{combined}")
    return {
        "status": "passed_with_import_only_dependency_stubs",
        "tests_passed": 80,
        "dependency_stubs": ["tushare", "agentscope"],
        "network_or_llm_calls": False,
        "paper_result_reproduction": False,
        "summary_tail": "80 passed",
    }


def _run_base_factor_component(
    source_root: Path, source_python: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    program = r"""
import hashlib, json, sys, types
import numpy as np
import pandas as pd

stub = types.ModuleType('tushare')
stub.pro_api = lambda *args, **kwargs: None
sys.modules['tushare'] = stub
from alphaagent.dsl import eval_factor

expressions = json.loads(sys.argv[1])
dates = pd.bdate_range('2020-01-01', periods=40)
assets = [f'S{i:02d}' for i in range(12)]
index = pd.MultiIndex.from_product([dates, assets], names=['datetime', 'instrument'])
t = np.repeat(np.arange(len(dates), dtype=float), len(assets))
a = np.tile(np.arange(len(assets), dtype=float), len(dates))
base = 20.0 + 0.07 * t + 0.03 * a + np.sin((t + a) / 5.0)
panel = pd.DataFrame(index=index)
panel['open'] = base * (1.0 + 0.001 * np.cos(a + t / 3.0))
panel['close'] = base * (1.0 + 0.002 * np.sin(a / 2.0 + t / 4.0))
panel['high'] = np.maximum(panel['open'], panel['close']) * 1.01
panel['low'] = np.minimum(panel['open'], panel['close']) * 0.99
panel['volume'] = 100000.0 + 1000.0 * a + 500.0 * t

rows = []
digest = hashlib.sha256()
for name, expression in sorted(expressions.items()):
    values = eval_factor(expression, panel).to_numpy(dtype=np.float64)
    canonical = np.nan_to_num(values, nan=9.87654321e99, posinf=8.7654321e99, neginf=-8.7654321e99)
    digest.update(name.encode())
    digest.update(canonical.tobytes())
    rows.append({
        'factor': name,
        'expression': expression,
        'rows': int(values.size),
        'finite_values': int(np.isfinite(values).sum()),
        'native_parser_executable': True,
        'paper_metric_reproduced': False,
        'status': 'post_paper_dsl_executes_on_synthetic_data_only',
    })
print(json.dumps({'sha256': digest.hexdigest(), 'rows': rows}, sort_keys=True))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root)
    outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(source_python), "-c", program, json.dumps(BASE_FACTOR_EXPRESSIONS)],
            cwd=source_root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(json.loads(completed.stdout))
    if outputs[0] != outputs[1]:
        raise RuntimeError("Post-paper DSL synthetic component is not deterministic")
    if outputs[0]["sha256"] != EXPECTED_SYNTHETIC_SHA256:
        raise RuntimeError("Pinned post-paper DSL synthetic output changed")
    return (
        {
            "synthetic_runs": 2,
            "deterministic": True,
            "sha256": outputs[0]["sha256"],
            "paper_result_reproduction": False,
        },
        outputs[0]["rows"],
    )


def run_native_component_checks(
    source_root: Path, source_python: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tests = _run_source_tests(source_root, source_python)
    synthetic, rows = _run_base_factor_component(source_root, source_python)
    component = {
        "source_python": str(source_python),
        "source_python_version": subprocess.run(
            [str(source_python), "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "upstream_tests": tests,
        "synthetic_base_factor_component": synthetic,
        "paper_result_reproduction": False,
    }
    return component, rows


def verify_pins(
    source_root: Path, paper_pdf: Path, paper_v1_pdf: Path
) -> tuple[str, str]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    observed_paper = sha256(paper_pdf)
    if observed_paper != PAPER_SHA256:
        raise RuntimeError(f"Expected paper SHA-256 {PAPER_SHA256}, found {observed_paper}")
    observed_v1 = sha256(paper_v1_pdf)
    if observed_v1 != PAPER_V1_SHA256:
        raise RuntimeError(
            f"Expected original-paper SHA-256 {PAPER_V1_SHA256}, found {observed_v1}"
        )
    for relative, expected in PINNED_SOURCE_SHA256.items():
        observed = sha256(source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned hash changed for {relative}: {observed}")
    first_commit, first_date = git_first_commit(source_root)
    if first_commit != SOURCE_FIRST_COMMIT or not first_date.startswith("2026-07-01"):
        raise RuntimeError(f"Pinned first-commit provenance changed: {first_commit}|{first_date}")
    for relative, expected in PAPER_MECHANISM_SHA256.items():
        observed = git_output(source_root, "show", f"{PAPER_MECHANISM_COMMIT}:{relative}")
        observed_hash = hashlib.sha256(observed.encode()).hexdigest()
        # git show as text strips the final newline; the extracted-tree hashes below are
        # authoritative.  This read only proves every pinned path still exists.
        if not observed or len(observed_hash) != 64:
            raise RuntimeError(f"Paper-era source path disappeared: {relative}")
    return commit, first_date


def build_audit(
    source_root: Path,
    paper_pdf: Path,
    paper_v1_pdf: Path,
    source_python: Path,
    output_dir: Path,
) -> dict[str, Any]:
    commit, first_date = verify_pins(source_root, paper_pdf, paper_v1_pdf)
    history, history_rows = history_audit(source_root)
    table_rows = table_conformance()
    claims = published_non_table_claims()
    gaps = specification_gaps()
    inventory = source_inventory(source_root)
    registry = current_registry_rows(source_root)
    release = data_release_provenance()
    component, base_factors = run_native_component_checks(source_root, source_python)

    with tempfile.TemporaryDirectory(prefix="alphaagent-paper-era-") as temp_dir:
        paper_era_root = Path(temp_dir)
        extract_git_commit(source_root, PAPER_MECHANISM_COMMIT, paper_era_root)
        for relative, expected in PAPER_MECHANISM_SHA256.items():
            observed = sha256(paper_era_root / relative)
            if observed != expected:
                raise RuntimeError(
                    f"Pinned paper-era hash changed for {relative}: {observed}"
                )
        mechanisms = paper_era_source_conformance(paper_era_root)
        current_mechanisms = current_source_conformance(source_root)
        paper_era_inventory = paper_era_source_inventory(source_root, paper_era_root)
        paper_era_factors = paper_era_factor_rows(paper_era_root)
        paper_era_component = run_paper_era_component_checks(
            paper_era_root, source_python
        )

    if len(inventory) != 141:
        raise RuntimeError(f"Expected 141 tracked source files, got {len(inventory)}")
    if len(registry) != 8:
        raise RuntimeError(f"Expected 8 post-paper registry entries, got {len(registry)}")
    if (
        len(mechanisms) != 32
        or len(current_mechanisms) != 32
        or len(gaps) != 17
        or len(base_factors) != 4
    ):
        raise RuntimeError("Pinned audit dimension counts changed")
    if Counter(row["status"] for row in table_rows) != {
        "unavailable_missing_native_paper_result_path": 100,
        "paper_configuration_recovered_without_frozen_dataset": 6,
    }:
        raise RuntimeError("Pinned numeric conformance boundary changed")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_1_2_conformance.csv", table_rows)
    write_csv(output_dir / "published_non_table_claims.csv", claims)
    write_csv(output_dir / "source_mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "current_rewrite_mechanism_conformance.csv", current_mechanisms)
    write_csv(output_dir / "official_history_timeline.csv", history_rows)
    write_csv(output_dir / "paper_specification_gaps.csv", gaps)
    write_csv(output_dir / "released_source_inventory.csv", inventory)
    write_csv(output_dir / "paper_era_source_inventory.csv", paper_era_inventory)
    write_csv(output_dir / "paper_era_factor_artifacts.csv", paper_era_factors)
    write_csv(output_dir / "post_paper_registry_metrics.csv", registry)
    write_csv(output_dir / "data_release_provenance.csv", release)
    write_csv(output_dir / "synthetic_base_factor_component.csv", base_factors)
    (output_dir / "native_component.json").write_text(
        json.dumps(component, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "paper_era_component.json").write_text(
        json.dumps(paper_era_component, indent=2) + "\n", encoding="utf-8"
    )

    mechanism_counts = Counter(row["status"] for row in mechanisms)
    manifest: dict[str, Any] = {
        "audit": "AlphaAgent paper v2 versus both roots of the official repository",
        "overall_status": "not_reproduced_paper_era_source_and_factor_artifacts_recovered",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": "arXiv:2502.16789v2",
        "paper_date": "2025-06-09",
        "paper_sha256": PAPER_SHA256,
        "paper_v1_url": PAPER_V1_URL,
        "paper_v1_sha256": PAPER_V1_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "source_commit_date": "2026-07-03",
        "source_first_commit": SOURCE_FIRST_COMMIT,
        "source_first_commit_date": first_date,
        "legacy_source_head": LEGACY_HEAD_COMMIT,
        "legacy_source_root": LEGACY_ROOT_COMMIT,
        "paper_mechanism_commit": PAPER_MECHANISM_COMMIT,
        "paper_mechanism_commit_date": "2025-02-12",
        "latest_full_tree_preprint_commit": LATEST_FULL_TREE_PREPRINT_COMMIT,
        "preprint_cutoff_commit": PREPRINT_CUTOFF_COMMIT,
        "paper_era_source_revision_available": True,
        "official_git_history": history,
        "paper_numeric_tables_audited": [1, 2],
        "paper_numeric_table_cells_total": 106,
        "paper_numeric_result_cells_total": 100,
        "paper_numeric_configuration_cells_total": 6,
        "paper_table_cell_counts": {"1": 6, "2": 100},
        "native_paper_table_result_cells_reproduced": 0,
        "paper_table_result_cells_unavailable": 100,
        "published_non_table_claims_total": 26,
        "published_non_table_result_claims_total": 18,
        "native_non_table_result_claims_reproduced": 0,
        "paper_specification_gaps_total": len(gaps),
        "source_mechanism_dimensions_total": len(mechanisms),
        "source_mechanism_status_counts": dict(mechanism_counts),
        "source_mechanism_component_matches_or_analogues": sum(
            bool(row["paper_mechanism_credit"]) for row in mechanisms
        ),
        "source_mechanism_fully_faithful": False,
        "paper_era_tracked_files_total": len(paper_era_inventory),
        "paper_era_python_files_compiled": paper_era_component["python_files_compiled"],
        "paper_era_factor_csv_files": len(paper_era_factors),
        "paper_era_factor_expression_rows": sum(
            int(row["expression_rows"]) for row in paper_era_factors
        ),
        "paper_era_named_alpha101_reference_rows": paper_era_component[
            "named_alpha101_reference_rows"
        ],
        "paper_era_loaded_alpha101_csv_rows": paper_era_component[
            "loaded_alpha101_csv_rows"
        ],
        "paper_era_ast_component_executable": True,
        "tracked_source_files_total": len(inventory),
        "post_paper_dsl_expressions_shipped": 13,
        "post_paper_registry_metric_entries": len(registry),
        "post_paper_registry_entries_receiving_paper_credit": 0,
        "current_post_paper_data_release_available": True,
        "current_post_paper_data_release_bytes": 524248466,
        "current_post_paper_data_release_valid_paper_input": False,
        "native_paper_data_snapshot_shipped": False,
        "native_paper_factor_pool_shipped": True,
        "native_paper_factor_pool_result_lineage_proven": False,
        "native_paper_llm_trajectories_shipped": False,
        "native_paper_prompts_shipped": True,
        "native_paper_predictions_or_returns_shipped": False,
        "native_paper_holdings_or_qlib_recorders_shipped": False,
        "native_paper_baseline_outputs_shipped": False,
        "native_paper_metric_or_figure_arrays_shipped": False,
        "native_source_tests_passed_with_dependency_stubs": 80,
        "native_source_tests_dependency_faithful": False,
        "native_synthetic_base_factors_executable": 4,
        "native_synthetic_component_deterministic": True,
        "native_synthetic_component_paper_result_reproduction": False,
        "audit_runtime_called_llm_or_market_data_api": False,
        "interpretation": (
            "The official repository has two unrelated roots. Its default main is a July 2026 "
            "CSI1000/Tushare rewrite, but public legacy-main retains a substantial preprint-era "
            "implementation. A pinned February 2025 snapshot contains the multi-stage workflow, "
            "structured hypothesis, prompts, operator library, AST largest-common-subtree matcher, "
            "Alpha101 reference expressions, Qlib/LightGBM configs, feedback loop, and 15 factor CSVs. "
            "The released implementation is still not the paper's exact objective: SL, PC, numeric "
            "c1/c2, alpha=0.5, beta-weighted ER, GPT-3.5 execution provenance, 20 trial seeds, and exact "
            "factor-to-result lineage are missing or divergent. Most importantly, no predictions, "
            "holdings, returns, Qlib recorders, baseline outputs, figure arrays, or metric arrays survive. "
            "Thus mechanism faithfulness is substantial, while 0/100 Table 2 result cells and 0/18 "
            "additional quantitative result claims are independently reproduced."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
        "paper_mechanism_file_sha256": PAPER_MECHANISM_SHA256,
    }

    report = f"""# AlphaAgent paper-level conformance audit

Overall verdict: **the paper results are not reproduced, but the paper-era
implementation is substantially recovered**. The previous audit looked only at
the rewritten default branch and was materially too pessimistic about mechanism
availability.

## Primary-source pins

- Final paper: {PAPER_URL} (arXiv v2, 2025-06-09; SHA-256 `{PAPER_SHA256}`).
- Original preprint: {PAPER_V1_URL} (10 pages; SHA-256 `{PAPER_V1_SHA256}`).
- Official repository: {SOURCE_URL}. It has two unrelated Git roots, not one
  continuous history: 8 commits on rewritten `main` and 485 on public
  `legacy-main`, 493 reachable commits in total.
- Mechanism snapshot: `{PAPER_MECHANISM_COMMIT}` (2025-02-12), before arXiv v1.
  It contains 856 tracked files, including 331 Python modules and 15 factor CSVs.
- The 2025-02-17 preprint-cutoff commit `{PREPRINT_CUTOFF_COMMIT}` removed the
  factor zoo. The audit intentionally pins the earlier mechanism-complete tree
  and records that deletion instead of pretending the cutoff head is runnable.
- Rewritten main: `{commit}` (2026-07-03). Its first commit is
  `{SOURCE_FIRST_COMMIT}` ({first_date}) and has no common ancestor with the
  paper-era branch.

## What genuinely passes

- All 331 Python modules in the paper-era snapshot compile under Python 3.12.
- The paper-era AST parser executes twice deterministically. Identical,
  commutative, and partially shared expressions return largest-common-subtree
  sizes 4, 3, and 3. An exact Alpha101 probe matches itself with size 23.
- The loaded `alpha101.csv` has 116 rows: 101 named Alpha101 references plus 15
  appended generated expressions. That supports the paper's originality path but
  also exposes reference-zoo contamination that must be reported, not hidden.
- The historical source implements the structured hypothesis fields, multi-stage
  proposal/construct/calculate/backtest/feedback loop, factor-expression parser,
  prose description-expression alignment critic, failed/successful implementation
  memory, multi-candidate generation, and metric feedback into later rounds.
- Historical CN/US Qlib configs recover the four OHLCV feature formulas,
  next-day label, train/validation/test segments, full LightGBM kwargs, Qlib
  signal/portfolio records, top-50/drop-5 combined strategies, and stated fees.
- Fifteen historical factor CSVs contain 268 expression rows. Names identify CN,
  US, GP, o1, and DeepSeek candidate pools, but no released lineage proves which
  file or row produced any published metric.
- Separately, all 80 tests in the 2026 rewrite pass with import-only Tushare and
  AgentScope stubs, and its four synthetic base factors are deterministic. Those
  checks receive no paper-result credit.

## Why the paper is still not replicated

- Table 2 has **100 numeric result cells**. **0/100** has a released native result
  path. Eighteen more quantitative result claims in figures/text are also 0/18.
  No prediction, holding, daily return, Qlib recorder, baseline output, figure
  array, token log, trial sample, or p-value sample survives.
- The exact Baostock CSI500 and Yahoo S&P500 panels, constituent histories, and
  data transformations are absent. The US config points only to unversioned local
  `us_data`; it does not establish Yahoo provenance or frozen panel identity.
- The code defaults to GPT-4-turbo, while the paper reports GPT-3.5-turbo. The
  executed model/API snapshot, temperature, seeds, token limits, initial research
  directions, and 20 independent trial trajectories are not pinned.
- The paper's displayed regularizer is not faithfully implemented. The source has
  AST largest-subtree matching and a hard retry at duplicated size >=5, but no
  symbolic-length term, free-parameter count, numeric c1/c2 alignment scores,
  alpha=0.5 combination, beta-weighted ER function, normalization, or disclosed
  objective weights/acceptance thresholds.
- The paper says lower ER is better while adding an alignment term described as
  higher-is-better. That sign ambiguity, plus undisclosed alpha/beta weights and
  thresholds, prevents an exact objective even with recovered source.
- Historical configs substantially recover model/backtest settings, but no
  executed-config hash, trained LightGBM state, seed, recorder, or mapping from a
  factor CSV to Table 2 exists. Configuration presence is not result reproduction.

## Honest boundary

The official historical source is much closer to the paper than the rewritten
default branch: this is a **substantial mechanism implementation**, not merely an
analogue. It is still not an end-to-end replication of the published experiments.
The 2026 CSI1000/Tushare data package, DSL expressions, and registry metrics belong
to a disjoint rewrite and receive zero paper credit. Run
`scripts/audit_alphaagent_paper.py` to regenerate the package; `--strict` remains
fail-closed until paper-era inputs, executed trials, models, portfolios, and every
published result are reproduced.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--paper-v1-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_PAPER_V1_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_paper_v1.pdf",
            )
        ),
    )
    parser.add_argument(
        "--source-python",
        type=Path,
        default=Path(os.environ.get("ALPHAAGENT_SOURCE_PYTHON", DEFAULT_SOURCE_PYTHON)),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/alphaagent",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.paper_pdf.resolve(),
        args.paper_v1_pdf.resolve(),
        args.source_python.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
