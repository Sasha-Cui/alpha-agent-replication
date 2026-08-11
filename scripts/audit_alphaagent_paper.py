#!/usr/bin/env python3
"""Audit AlphaAgent paper v2 against its pinned official source release.

The official repository was first committed in July 2026, more than a year
after the June 2025 paper, and implements a different research framework. This
audit enumerates every numeric result cell in the paper's only performance
table, treats the dataset table's trading-day counts as configuration cells,
records the paper's quantitative figure/text claims, and tests only the
post-paper release's deterministic source components. It never promotes source
presence, synthetic outputs, post-paper registry metrics, or the newer CSI-1000
data package to paper-result reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SOURCE_COMMIT = "b42cb397025510da44355db9dcf278304321f589"
SOURCE_URL = "https://github.com/RndmVariableQ/AlphaAgent"
SOURCE_FIRST_COMMIT = "7debd15ca98309a8df9c1d50aca3831f320687cf"
PAPER_URL = "https://arxiv.org/pdf/2502.16789v2"
PAPER_SHA256 = "cf620c3b33a98edd4124230458b65741e1767fa37a3a180828de1035ded52ab1"
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
                "the release ships no paper-era factor pool, model, prediction, "
                "portfolio, baseline output, or metric file"
            )
        else:
            status = "configuration_not_reproduced_by_post_paper_release"
            reason = (
                "the release defaults to different splits and does not ship the "
                "Baostock/Yahoo CSI500/S&P500 paper panels"
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
                else "configuration_not_reproduced_by_post_paper_release",
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
        ("operator_library", "the complete paper operator library and semantics are absent", "blocks expression equivalence"),
        ("prompts", "idea/factor/eval agent prompts are absent", "blocks agent replay"),
        ("llm_sampling", "temperature, seeds, API snapshots, and token limits are absent", "blocks stochastic replay"),
        ("seed_hypotheses", "initial research directions and all 20 trial inputs are absent", "blocks search replay"),
        ("factor_outputs", "the 15 decay-analysis factors and final factor pools are not published", "blocks model inputs"),
        ("lightgbm", "only maximum depth 4 is disclosed", "remaining hyperparameters and seeds absent"),
        ("universe", "constituent histories, delisting rules, adjustment rules, and filters are absent", "blocks panel identity"),
        ("portfolio", "Qlib top-k=50/drop=5 is disclosed without full strategy/rebalance/benchmark config", "blocks returns"),
        ("transaction_costs", "fee rates are disclosed without full slippage/limit/suspension semantics", "blocks net returns"),
        ("trial_aggregation", "the aggregation/selection from 20 trials to Table 2 is not fully specified", "blocks metric target"),
        ("figure_arrays", "underlying daily curves, yearly values, and round distributions are absent", "blocks figure reproduction"),
        ("p_value_samples", "the IC samples used in the three Student t tests are absent", "blocks p-value reproduction"),
    ]
    return [
        {"dimension": dimension, "missing_specification": gap, "consequence": consequence}
        for dimension, gap, consequence in raw
    ]


def source_conformance(source_root: Path) -> list[dict[str, Any]]:
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
        "summary_tail": combined.strip().splitlines()[-1],
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


def verify_pins(source_root: Path, paper_pdf: Path) -> tuple[str, str]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    observed_paper = sha256(paper_pdf)
    if observed_paper != PAPER_SHA256:
        raise RuntimeError(f"Expected paper SHA-256 {PAPER_SHA256}, found {observed_paper}")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        observed = sha256(source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned hash changed for {relative}: {observed}")
    first_commit, first_date = git_first_commit(source_root)
    if first_commit != SOURCE_FIRST_COMMIT or not first_date.startswith("2026-07-01"):
        raise RuntimeError(f"Pinned first-commit provenance changed: {first_commit}|{first_date}")
    return commit, first_date


def build_audit(
    source_root: Path,
    paper_pdf: Path,
    source_python: Path,
    output_dir: Path,
) -> dict[str, Any]:
    commit, first_date = verify_pins(source_root, paper_pdf)
    table_rows = table_conformance()
    claims = published_non_table_claims()
    mechanisms = source_conformance(source_root)
    gaps = specification_gaps()
    inventory = source_inventory(source_root)
    registry = current_registry_rows(source_root)
    release = data_release_provenance()
    component, base_factors = run_native_component_checks(source_root, source_python)

    if len(inventory) != 141:
        raise RuntimeError(f"Expected 141 tracked source files, got {len(inventory)}")
    if len(registry) != 8:
        raise RuntimeError(f"Expected 8 post-paper registry entries, got {len(registry)}")
    if len(mechanisms) != 32 or len(gaps) != 17 or len(base_factors) != 4:
        raise RuntimeError("Pinned audit dimension counts changed")
    if Counter(row["status"] for row in table_rows) != {
        "unavailable_missing_native_paper_result_path": 100,
        "configuration_not_reproduced_by_post_paper_release": 6,
    }:
        raise RuntimeError("Pinned numeric conformance boundary changed")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_1_2_conformance.csv", table_rows)
    write_csv(output_dir / "published_non_table_claims.csv", claims)
    write_csv(output_dir / "source_mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "paper_specification_gaps.csv", gaps)
    write_csv(output_dir / "released_source_inventory.csv", inventory)
    write_csv(output_dir / "post_paper_registry_metrics.csv", registry)
    write_csv(output_dir / "data_release_provenance.csv", release)
    write_csv(output_dir / "synthetic_base_factor_component.csv", base_factors)
    (output_dir / "native_component.json").write_text(
        json.dumps(component, indent=2) + "\n", encoding="utf-8"
    )

    mechanism_counts = Counter(row["status"] for row in mechanisms)
    manifest: dict[str, Any] = {
        "audit": "AlphaAgent paper v2 versus pinned official post-paper source",
        "overall_status": "not_reproduced_post_paper_component_analogue_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": "arXiv:2502.16789v2",
        "paper_date": "2025-06-09",
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "source_commit_date": "2026-07-03",
        "source_first_commit": SOURCE_FIRST_COMMIT,
        "source_first_commit_date": first_date,
        "paper_era_source_revision_available": False,
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
        "tracked_source_files_total": len(inventory),
        "post_paper_dsl_expressions_shipped": 13,
        "post_paper_registry_metric_entries": len(registry),
        "post_paper_registry_entries_receiving_paper_credit": 0,
        "current_post_paper_data_release_available": True,
        "current_post_paper_data_release_bytes": 524248466,
        "current_post_paper_data_release_valid_paper_input": False,
        "native_paper_data_snapshot_shipped": False,
        "native_paper_factor_pool_shipped": False,
        "native_paper_llm_trajectories_shipped": False,
        "native_paper_prompts_shipped": False,
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
            "The official source is not a paper-era release: its Git history starts in July 2026, "
            "after the June 2025 paper, and its README/dev log describe a new CSI1000/Tushare "
            "framework. The current DSL, operator library, evaluation tools, feedback loop, and "
            "post-paper registry are real executable components. They do not implement the paper's "
            "three agents, AST largest-common-subtree originality, Alpha101 comparison, SL/PC/ER "
            "regularizers, alignment scoring, LightGBM/QLib portfolio, baselines, or paper protocol. "
            "The official 2026 data package is available but has the wrong market, source, and vintage. "
            "Consequently 0/100 Table 2 result cells and 0/18 additional quantitative result claims "
            "are independently reproduced."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
    }

    report = f"""# AlphaAgent paper-level conformance audit

Overall verdict: **not reproduced**. The official repository is a runnable
post-paper component analogue, not the implementation that produced the paper.

## Primary-source pins

- Official paper: {PAPER_URL} (arXiv v2, 2025-06-09; SHA-256 `{PAPER_SHA256}`).
- Official source: {SOURCE_URL}, commit `{commit}` (2026-07-03).
- The repository's first commit is `{SOURCE_FIRST_COMMIT}` ({first_date}); no
  paper-era source revision exists in its Git history.

## What genuinely passes

- All 80 upstream tests pass under Python 3.12 when import-only stubs replace the
  unavailable Tushare and AgentScope packages. This validates deterministic code
  components, not the declared dependency environment or any paper experiment.
- The post-paper DSL executes the four named paper base-factor formulas twice on
  synthetic OHLCV data with identical output hashes.
- The released operator library, factor evaluation tools, multi-candidate prompt,
  and metric-feedback loop are meaningful analogues to parts of the paper.
- The linked 524,248,466-byte `alphaagent-data-20260703.zip` is reachable and its
  public metadata is recorded. It is CSI1000/Tushare data through June 2026.

## Why the paper is not replicated

- Table 2 contains **100 numeric result cells** (10 methods x 2 markets x 5
  metrics). **0/100** has a native released result path. Table 1 contributes six
  trading-day configuration cells; none can be reconstructed from released
  paper data. Eighteen additional numeric result claims in figures/text also have
  zero native reproductions.
- The paper uses Baostock CSI500 and Yahoo S&P500 OHLCV panels, GPT-3.5-turbo,
  three specialized agents, LightGBM, and a Qlib top-50/drop-5 backtest. The
  release uses Tushare CSI1000, defaults to gpt-4o-mini, has one tool-calling
  trajectory, and marks model/portfolio/backtest packages as future work.
- Paper originality is largest-common-subtree AST isomorphism against Alpha101.
  Released similarity is mean daily cross-sectional Pearson correlation. Its
  parser compiles expressions to Python code strings and does not implement the
  paper's AST score, symbolic-length/free-parameter penalties, ER objective, or
  two-part LLM alignment score.
- No paper prompt, seed hypothesis, 20-trial trajectory, candidate pool, 15 final
  factors, LightGBM model, prediction, holding, daily return, Qlib recorder,
  baseline output, figure array, token log, or p-value sample is shipped.
- Seventeen paper specification gaps independently prevent exact reconstruction,
  including undisclosed alpha/beta weights, similarity normalization and filter
  thresholds, remaining LightGBM parameters, factor outputs, trial aggregation,
  universe history, and complete portfolio semantics.

## Honest boundary

The 13 DSL expressions and eight registry metric entries were generated in 2026
for a different dataset and protocol. They remain useful current-release evidence
but receive zero paper credit. The newer data package is likewise not retroactively
the frozen paper input. Run `scripts/audit_alphaagent_paper.py` to regenerate this
package; use `--strict` to fail until the paper-era data, source, prompts, trials,
factors, models, portfolios, baselines, and all published results are reproduced.
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
        args.source_python.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
