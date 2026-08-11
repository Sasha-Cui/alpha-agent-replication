#!/usr/bin/env python3
"""Audit TradingAgents arXiv v7 against the nearest official source release.

The latest paper revision predates the first public code release by about two
days.  This audit therefore pins arXiv v7 and the official v0.1.0 tag, enumerates
every numeric cell in Table 1, checks the paper's own metric identities, audits
the published appendix transcript and source mechanisms, and executes only
dependency-isolated deterministic components from the tagged source.  It never
promotes compilation, graph topology, paper figures, current web data, or a
fresh one-day LLM decision to reproduction of the paper backtest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence


PAPER_URL = "https://arxiv.org/pdf/2412.20138v7"
PAPER_VERSION = "arXiv:2412.20138v7"
PAPER_DATE = "2025-06-03T05:45:06Z"
PAPER_SHA256 = "431d0c39365b4c46b43162371fa15b3dcf8d142b377d642b3e5925dc81f3487b"
PAPER_SOURCE_SHA256 = "17bc9ebe6c7379ed832ec9915eb147feccda3c8c582a84d93f1f87dfbaf3ed65"
SOURCE_URL = "https://github.com/TauricResearch/TradingAgents"
SOURCE_COMMIT = "cc97cb6d5deb10eac370db0c6678e2796a62eba8"
SOURCE_TAG = "v0.1.0"
SOURCE_COMMIT_DATE = "2025-06-05T03:08:28-07:00"
PRE_RELEASE_COMMIT = "635e91ac75f68e5a48eaf0c07760252f73326118"
DEFAULT_SOURCE_PYTHON = "/nfs/roberts/project/pi_btk22/zc362/environments/bin/kt-python"

PINNED_SOURCE_SHA256 = {
    "README.md": "aed2e950144639d239d9cb20b0c8ccd58ac6cb9aba611b5142de802289b7c236",
    "requirements.txt": "cdae55137676f17d91918e8d3a492b9e2d1c0d716829955e7764245096bfa577",
    "tradingagents/default_config.py": "8c4f20a0fadcb731d0690e98e7efc8c2944247e0d1ecbf7e1f49f145fc449dde",
    "tradingagents/graph/trading_graph.py": "d8a8477f6e16c1fcda3bfa579485e895a44602747a0929fd086284857ded8ee5",
    "tradingagents/graph/setup.py": "7437ae4c52769adad0beaa71d71bd90a98f18037998bbbb405330f27d5e15d93",
    "tradingagents/graph/conditional_logic.py": "8ec347c2b9a4581f6aa9cc9febf0ad6f777ea289cfffee22c6448957012cecec",
    "tradingagents/graph/propagation.py": "f0a2304b19e2ac5de92456795c37b87e9ec34873dfabc3947b6c1c1aea974ae5",
    "tradingagents/graph/reflection.py": "31a94b13591f13f907e58239406fac79aafaeb55e355f6447a0d96877beebfdd",
    "tradingagents/graph/signal_processing.py": "563df40af1bcffb29623f35c36f4d2f5950863ae78809581bcb7d7eef47591c2",
    "tradingagents/dataflows/interface.py": "4bdf5c2105ea82bae87e0021b32adfd61e3e45f45208d5de7d8886cd7eae1a1c",
}

PINNED_PAPER_SOURCE_SHA256 = {
    "main.tex": "9074ffe583f36834d97c0a8676519fb89332ecfc8502963046225291bb43f4d3",
    "tables/results.tex": "00c777122162fe05520a7f45212ee34d226fb0d5e363fc9347404795c2632ca4",
    "sections/3.methodology.tex": "5ded949606f9b9a72107356130403e60b73f06b4af408f77d67f6aa145ba45d9",
    "sections/4.expreiments.tex": "a7c50641d9eda9b80ea5c5492e97b99b370a5581eabd042b87dd7fcec4363801",
    "sections/5.results.tex": "fdc4eff57e031348cc0ae76204fff1623e6f11da8730dca9746f9c4fb0cc8bc2",
    "sections/appendix.tex": "14fe36d8bcf485b0e68714e161d9ba822ca2f78dae2442ede5b7f252766638f2",
    "sections/cases.tex": "5cbbda36e8bd6ce15e4fd7d46d315a438af6cdb254b4865b1aa5347141e60fed",
}

FIGURE_SHA256 = {
    "figures/AAPL/compare.pdf": "253c734192f00311c7ea5d01be0b551d84625bcce3fafee2ce7606cb56e3f9e4",
    "figures/AAPL/details.pdf": "4e7e79165f6f6c0803468e54fe1b446ecc81882106bebd942451defcf55d7607",
    "figures/AMZN/compare.pdf": "d037f3f53461689a8661118edf318e81450e18e87f70e66cfadde540a66b4326",
    "figures/AMZN/details.pdf": "56b380a7103985e142e76ae6d3b0ec1b0ec8394d7677c7bca5b18d0d5476f3c5",
    "figures/GOOGL/compare.pdf": "981423ff58684e6153f393b1ce423e6613223383188482cc616d31adbd333610",
    "figures/GOOGL/details.pdf": "6fabc415d0eaf6c0bcd29ba89534fdb1c6a2acaad047db320dd373941c54025f",
}

METRICS = ("CR_pct", "AR_pct", "SR", "MDD_pct")
ASSETS = ("AAPL", "GOOGL", "AMZN")
PERFORMANCE: dict[str, dict[str, tuple[float | None, ...]]] = {
    "B&H": {
        "AAPL": (-5.23, -5.09, -1.29, 11.90),
        "GOOGL": (7.78, 8.09, 1.35, 13.04),
        "AMZN": (17.1, 17.6, 3.53, 3.80),
    },
    "MACD": {
        "AAPL": (-1.49, -1.48, -0.81, 4.53),
        "GOOGL": (6.20, 6.26, 2.31, 1.22),
        "AMZN": (None, None, None, None),
    },
    "KDJ&RSI": {
        "AAPL": (2.05, 2.07, 1.64, 1.09),
        "GOOGL": (0.4, 0.4, 0.02, 1.58),
        "AMZN": (-0.77, -0.76, -2.25, 1.08),
    },
    "ZMR": {
        "AAPL": (0.57, 0.57, 0.17, 0.86),
        "GOOGL": (-0.58, 0.58, 2.12, 2.34),
        "AMZN": (-0.77, -0.77, -2.45, 0.82),
    },
    "SMA": {
        "AAPL": (-3.2, -2.97, -1.72, 3.67),
        "GOOGL": (6.23, 6.43, 2.12, 2.34),
        "AMZN": (11.01, 11.6, 2.22, 3.97),
    },
    "TradingAgents": {
        "AAPL": (26.62, 30.5, 8.21, 0.91),
        "GOOGL": (24.36, 27.58, 6.39, 1.69),
        "AMZN": (23.21, 24.90, 5.60, 2.11),
    },
}

IMPROVEMENT = {
    "AAPL": (24.57, 28.43, 6.57, None),
    "GOOGL": (16.58, 19.49, 4.26, None),
    "AMZN": (6.10, 7.30, 2.07, None),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return result.stdout


def git_blob(source_root: Path, relative: str) -> bytes:
    return run_git(source_root, "show", f"{SOURCE_COMMIT}:{relative}", binary=True)  # type: ignore[return-value]


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_table_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method, by_asset in PERFORMANCE.items():
        for asset in ASSETS:
            for metric, value in zip(METRICS, by_asset[asset]):
                if value is None:
                    continue
                status = (
                    "unavailable_missing_native_paper_result_path"
                    if method == "TradingAgents"
                    else "unavailable_missing_native_baseline_result_path"
                )
                rows.append(
                    {
                        "paper_table": 1,
                        "cell_kind": "direct_result",
                        "method": method,
                        "asset": asset,
                        "period": "2024-01-01 to 2024-03-29",
                        "metric": metric,
                        "paper_value": value,
                        "native_reproduced_value": "",
                        "absolute_difference": "",
                        "status": status,
                        "paper_result_credit": False,
                    }
                )
    for asset in ASSETS:
        for metric, value in zip(METRICS, IMPROVEMENT[asset]):
            if value is None:
                continue
            rows.append(
                {
                    "paper_table": 1,
                    "cell_kind": "derived_improvement",
                    "method": "Improvement(%)",
                    "asset": asset,
                    "period": "2024-01-01 to 2024-03-29",
                    "metric": metric,
                    "paper_value": value,
                    "native_reproduced_value": "",
                    "absolute_difference": "",
                    "status": "unavailable_missing_native_inputs",
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 77 or Counter(row["cell_kind"] for row in rows) != {
        "direct_result": 68,
        "derived_improvement": 9,
    }:
        raise RuntimeError("TradingAgents Table 1 numeric-cell denominator changed")
    return rows


def annualization_identity() -> list[dict[str, Any]]:
    inclusive_days = (date(2024, 3, 29) - date(2024, 1, 1)).days + 1
    years = inclusive_days / 365.25
    rows: list[dict[str, Any]] = []
    for method, by_asset in PERFORMANCE.items():
        for asset, values in by_asset.items():
            cr, ar = values[:2]
            if cr is None or ar is None:
                continue
            expected = ((1.0 + cr / 100.0) ** (1.0 / years) - 1.0) * 100.0
            difference = ar - expected
            rows.append(
                {
                    "method": method,
                    "asset": asset,
                    "paper_CR_pct": cr,
                    "paper_AR_pct": ar,
                    "inclusive_calendar_days": inclusive_days,
                    "N_years_literal": years,
                    "AR_pct_from_published_equation": expected,
                    "paper_minus_equation_pct_points": difference,
                    "display_precision_match": abs(difference) <= 0.015,
                    "status": "fails_literal_published_equation_at_display_precision",
                }
            )
    if len(rows) != 17 or any(row["display_precision_match"] for row in rows):
        raise RuntimeError("Published CR/AR identity boundary changed")
    return rows


def improvement_identity() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    baseline_methods = tuple(method for method in PERFORMANCE if method != "TradingAgents")
    for asset in ASSETS:
        for metric_index, metric in enumerate(METRICS[:3]):
            baseline = [
                PERFORMANCE[method][asset][metric_index]
                for method in baseline_methods
                if PERFORMANCE[method][asset][metric_index] is not None
            ]
            best = max(float(value) for value in baseline)
            ours = float(PERFORMANCE["TradingAgents"][asset][metric_index])
            published = float(IMPROVEMENT[asset][metric_index])
            expected = ours - best
            difference = published - expected
            if abs(difference) < 0.005:
                status = "exact_absolute_difference_from_displayed_cells"
            elif asset == "AMZN" and metric == "CR_pct" and abs(difference) <= 0.011:
                status = "not_exact_from_displayed_cells_hidden_precision_could_explain"
            else:
                status = "inconsistent_with_displayed_cells"
            rows.append(
                {
                    "asset": asset,
                    "metric": metric,
                    "best_displayed_baseline": best,
                    "TradingAgents_displayed": ours,
                    "paper_improvement_pct_label": published,
                    "absolute_difference_from_displayed_cells": expected,
                    "relative_improvement_pct": (expected / abs(best)) * 100.0,
                    "paper_minus_absolute_difference": difference,
                    "status": status,
                }
            )
    expected_counts = {
        "exact_absolute_difference_from_displayed_cells": 7,
        "not_exact_from_displayed_cells_hidden_precision_could_explain": 1,
        "inconsistent_with_displayed_cells": 1,
    }
    if Counter(row["status"] for row in rows) != expected_counts:
        raise RuntimeError("Published improvement identity boundary changed")
    return rows


def published_non_table_claims() -> list[dict[str, Any]]:
    raw = [
        ("Section 6.1.1", "minimum TradingAgents cumulative return", 23.21, "pct", "result", "exact"),
        ("Section 6.1.1", "minimum TradingAgents annual return", 24.90, "pct", "result", "exact"),
        ("Section 6.1.1", "margin over best baseline", 6.1, "pct", "result", "exact"),
        ("Section 6.1.1", "AAPL return lower bound", 26.0, "pct", "result", "lower_bound"),
        ("Section 6.1.3", "claimed maximum drawdown upper bound", 2.0, "pct", "result", "upper_bound"),
        ("Section 6.1.2 footnote", "LLM calls per prediction", 11.0, "calls", "configuration", "exact"),
        ("Section 6.1.2 footnote", "tool calls per prediction", 20.0, "calls", "configuration", "lower_bound"),
        ("Figure 6", "AAPL ending broker cash annotation", 246516.57, "currency_units", "result", "exact"),
        ("Figure 6", "AAPL ending broker value annotation", 130501.44, "currency_units", "result", "exact"),
        ("Figure S1", "AMZN ending broker cash annotation", 12315.59, "currency_units", "result", "exact"),
        ("Figure S1", "AMZN ending broker value annotation", 124872.71, "currency_units", "result", "exact"),
        ("Figure S3", "GOOGL ending broker cash annotation", 116445.06, "currency_units", "result", "exact"),
        ("Figure S3", "GOOGL ending broker value annotation", 127586.29, "currency_units", "result", "exact"),
        ("Figure S3", "GOOGL displayed negative trade PnL", -254.11, "currency_units", "result", "exact"),
    ]
    rows = []
    for location, claim, value, unit, role, exactness in raw:
        rows.append(
            {
                "paper_location": location,
                "claim": claim,
                "paper_value": value,
                "unit": unit,
                "claim_role": role,
                "exactness": exactness,
                "native_reproduced_value": "",
                "status": (
                    "unavailable_missing_native_paper_result_path"
                    if role == "result"
                    else "configuration_documented_not_reproduced"
                ),
                "paper_result_credit": False,
            }
        )
    if Counter(row["claim_role"] for row in rows) != {"result": 12, "configuration": 2}:
        raise RuntimeError("Non-table quantitative-claim boundary changed")
    return rows


def paper_internal_inconsistencies() -> list[dict[str, Any]]:
    return [
        {
            "dimension": "experiment_universe",
            "paper_evidence": "setup names Apple, Nvidia, Microsoft, Meta, Google; Table 1 reports AAPL, GOOGL, AMZN",
            "finding": "AMZN is not in the named five and NVDA/MSFT/META have no table results",
            "severity": "blocks_exact_scope",
        },
        {
            "dimension": "annualized_return_formula",
            "paper_evidence": "Appendix defines AR=(Vend/Vstart)^(1/N)-1 with N years; experiment spans 2024-01-01 to 2024-03-29",
            "finding": "all 17 displayed CR/AR pairs fail the literal equation at display precision",
            "severity": "paper_internal_numeric_inconsistency",
        },
        {
            "dimension": "GOOGL_ZMR_return_sign",
            "paper_evidence": "CR=-0.58% and AR=+0.58%",
            "finding": "the two signs cannot both follow the published formulas for positive N",
            "severity": "paper_internal_numeric_inconsistency",
        },
        {
            "dimension": "GOOGL_SR_improvement",
            "paper_evidence": "TradingAgents SR=6.39; best displayed baseline SR=2.31; improvement=4.26",
            "finding": "displayed subtraction is 4.08, not 4.26",
            "severity": "paper_internal_arithmetic_error",
        },
        {
            "dimension": "improvement_units",
            "paper_evidence": "row is labeled Improvement(%)",
            "finding": "seven cells are exact absolute metric-point differences, not relative percentage improvements",
            "severity": "metric_label_ambiguity",
        },
        {
            "dimension": "maximum_drawdown_claim",
            "paper_evidence": "text says maximum drawdown does not exceed 2; AMZN TradingAgents MDD is 2.11%",
            "finding": "the prose upper bound is contradicted by Table 1",
            "severity": "paper_internal_numeric_inconsistency",
        },
        {
            "dimension": "figure_value_metric_alignment",
            "paper_evidence": "broker values are 130501.44, 124872.71, 127586.29; initial capital is undisclosed",
            "finding": "under an inferred 100000 initial balance, implied returns align within 0.03 points of AR, not CR; this is suggestive only",
            "severity": "unresolved_metric_provenance",
        },
    ]


def case_tool_conformance(source_root: Path) -> list[dict[str, Any]]:
    released = git_blob(source_root, "tradingagents/agents/utils/agent_utils.py").decode()
    paper_tools = [
        ("get_EODHD_news", 1),
        ("get_EODHD_sentiment", 1),
        ("get_YFin_data", 1),
        ("get_finnhub_basic_company_financials", 1),
        ("get_finnhub_company_financials_history", 1),
        ("get_finnhub_company_insider_sentiment", 1),
        ("get_finnhub_company_insider_transactions", 1),
        ("get_finnhub_company_profile", 1),
        ("get_finnhub_news", 4),
        ("get_reddit_stock_info", 1),
        ("get_stockstats_indicators_report", 8),
    ]
    rows = []
    for tool, calls in paper_tools:
        exact = f"def {tool}(" in released
        rows.append(
            {
                "paper_case_tool": tool,
                "published_call_count": calls,
                "exact_name_in_v0_1_0": exact,
                "status": "exact_released_tool_name" if exact else "absent_from_nearest_release",
                "case_output_reproduced": False,
            }
        )
    if Counter(row["status"] for row in rows) != {
        "exact_released_tool_name": 6,
        "absent_from_nearest_release": 5,
    }:
        raise RuntimeError("Appendix case-tool boundary changed")
    return rows


def specification_gaps() -> list[dict[str, Any]]:
    raw = [
        ("asset_scope", "prose and Table 1 disagree on the tested assets", "blocks exact experiment set"),
        ("frozen_data", "no paper-era price/news/social/fundamental snapshot is released", "blocks input identity"),
        (
            "point_in_time_data",
            "publication and revision timestamps for every text/fundamental item are absent",
            "blocks look-ahead audit",
        ),
        (
            "data_provider_mapping",
            "provider-to-field and fallback precedence are not disclosed",
            "blocks multimodal reconstruction",
        ),
        (
            "sentiment_model",
            "auxiliary sentiment model, prompt, version, and outputs are absent",
            "blocks sentiment feature",
        ),
        (
            "technical_indicators",
            "the complete 60-indicator names, parameters, and warmups are absent",
            "blocks technical input",
        ),
        ("llm_snapshots", "model families are named without immutable API snapshots", "blocks LLM replay"),
        ("prompts", "exact experiment prompts and tool schemas are not pinned in the paper", "blocks agent replay"),
        (
            "sampling",
            "temperatures, seeds, token limits, retries, and concurrency are incomplete",
            "blocks stochastic replay",
        ),
        (
            "agent_model_assignment",
            "paper prose and nearest source disagree on quick/deep assignment",
            "blocks node equivalence",
        ),
        ("debate_rounds", "n and facilitator stopping behavior are not reported", "blocks debate trajectory"),
        ("trials", "number of trials and aggregation/selection rule are absent", "blocks table estimator"),
        ("initial_capital", "starting cash is not stated", "blocks portfolio values"),
        ("position_sizing", "size, limits, leverage, and cash constraints are absent", "blocks holdings"),
        ("execution_timing", "signal time, order time, execution price, and latency are absent", "blocks returns"),
        ("shorting", "short/borrow/margin semantics behind figure captions are absent", "blocks short positions"),
        ("costs", "commissions, bid-ask spread, slippage, and borrow costs are absent", "blocks net returns"),
        ("corporate_actions", "dividend and split treatment is not specified", "blocks value path"),
        (
            "multi_asset_portfolio",
            "cross-asset capital allocation and rebalance semantics are absent",
            "blocks portfolio interpretation",
        ),
        (
            "baseline_parameters",
            "lookbacks, thresholds, sizing, and execution rules for five baselines are absent",
            "blocks baselines",
        ),
        ("ZMR_definition", "zero reference line and signal rule are not mathematically specified", "blocks ZMR"),
        ("risk_free_rate", "Sharpe risk-free series/value is not reported", "blocks SR"),
        ("return_frequency", "Sharpe return frequency and annualization convention are absent", "blocks SR"),
        ("annualization_N", "N convention conflicts with the displayed AR values", "blocks AR target"),
        (
            "metric_arrays",
            "daily NAVs, returns, holdings, and exact plot arrays are absent",
            "blocks figures and metrics",
        ),
        (
            "backtest_outputs",
            "actions, orders, fills, reflections, and baseline outputs are absent",
            "blocks result verification",
        ),
        (
            "cost_accounting",
            "paper reports calls per prediction but no token/API cost ledger",
            "blocks cost reproduction",
        ),
    ]
    return [
        {"dimension": dimension, "missing_or_ambiguous_specification": gap, "consequence": consequence}
        for dimension, gap, consequence in raw
    ]


def source_conformance(source_root: Path) -> list[dict[str, Any]]:
    config = git_blob(source_root, "tradingagents/default_config.py").decode()
    graph = git_blob(source_root, "tradingagents/graph/trading_graph.py").decode()
    setup = git_blob(source_root, "tradingagents/graph/setup.py").decode()
    logic = git_blob(source_root, "tradingagents/graph/conditional_logic.py").decode()
    interface = git_blob(source_root, "tradingagents/dataflows/interface.py").decode()
    readme = git_blob(source_root, "README.md").decode()
    requirements = git_blob(source_root, "requirements.txt").decode()
    files = set(git_files(source_root))

    checks = [
        (
            "public_revision_timing",
            "paper-era implementation by 2025-06-03",
            "first code release 2025-06-05; predecessor has only three site files",
            "nearest_post_paper_release",
            False,
        ),
        (
            "four_analyst_roles",
            "fundamental, sentiment/social, news, technical/market",
            "four corresponding analyst nodes",
            "component_match",
            True,
        ),
        (
            "analyst_concurrency",
            "four analysts concurrently gather information",
            "analysts execute sequentially in selected_analysts order",
            "mismatch",
            False,
        ),
        (
            "structured_global_state",
            "structured reports in shared state",
            "typed AgentState report fields and message clearing",
            "component_match",
            True,
        ),
        (
            "bull_bear_debate",
            "bull and bear researchers",
            "Bull Researcher and Bear Researcher routing",
            "component_match",
            True,
        ),
        (
            "research_facilitator",
            "facilitator selects prevailing view",
            "Research Manager node",
            "component_match",
            True,
        ),
        ("trader", "trader synthesizes reports/debate", "Trader node and investment plan", "component_match", True),
        (
            "risk_perspectives",
            "risk-seeking, neutral, conservative debate",
            "Risky, Neutral, Safe nodes",
            "component_match",
            True,
        ),
        (
            "fund_manager",
            "separate fund manager approves and executes",
            "Risk Judge ends graph; no order execution node",
            "mismatch_conflated",
            False,
        ),
        ("action_vocabulary", "buy, sell, hold", "signal processor extracts BUY/SELL/HOLD", "component_match", True),
        (
            "react_tool_use",
            "ReAct-style reasoning and acting",
            "tool-calling analyst loops",
            "component_analogue",
            True,
        ),
        (
            "reflection_memory",
            "reflective agent improves decisions",
            "five Chroma memories plus manual reflect_and_remember",
            "component_analogue",
            True,
        ),
        (
            "automatic_reflection",
            "reflection integrated in sequential backtest",
            "caller must inject realized return; example call is commented",
            "missing",
            False,
        ),
        (
            "experiment_model_families",
            "gpt-4o/o1-preview family split",
            "README states o1-preview and gpt-4o experiments",
            "documentation_match_no_frozen_config",
            True,
        ),
        (
            "executable_experiment_model_config",
            "paper experiment configuration",
            "defaults are o4-mini/gpt-4o-mini; example uses gpt-4.1-nano",
            "mismatch",
            False,
        ),
        (
            "node_model_assignment",
            "analysts, researchers, traders use deep models",
            "all those nodes use quick model; only two managers use deep model",
            "mismatch",
            False,
        ),
        (
            "sampling_configuration",
            "exact paper sampling",
            "quick temperature=0.1, auxiliary temperature=1, deep unspecified",
            "incomplete",
            False,
        ),
        (
            "debate_round_control",
            "n rounds determined by facilitator",
            "hardcoded ConditionalLogic default 1; config value not passed",
            "mismatch",
            False,
        ),
        (
            "risk_round_control",
            "n rounds guided by facilitator",
            "hardcoded ConditionalLogic default 1; config value not passed",
            "mismatch",
            False,
        ),
        (
            "recursion_control",
            "experiment recursion configuration",
            "Propagator default 100; config max_recur_limit not passed",
            "mismatch",
            False,
        ),
        (
            "multimodal_categories",
            "prices, news, social, insiders, statements, indicators",
            "broad corresponding tool categories",
            "component_analogue",
            True,
        ),
        (
            "data_providers",
            "Bloomberg, Yahoo, EODHD, FinnHub, Reddit, X/Twitter, SEDI",
            "Yahoo, Google, FinnHub, Reddit, SimFin, OpenAI web search",
            "mismatch",
            False,
        ),
        ("technical_indicator_count", "60 indicators per asset", "13 selectable indicator keys", "mismatch", False),
        (
            "paper_case_tools",
            "11 unique named tools in appendix transcript",
            "6 exact names present; 5 absent",
            "partial_component_analogue",
            True,
        ),
        (
            "paper_case_output",
            "AAPL 2024-11-19 published transcript and BUY",
            "no frozen prompt inputs, trace, or deterministic replay",
            "missing",
            False,
        ),
        (
            "offline_data_snapshot",
            "paper multimodal panel",
            "author-local /Users/yluo/.../FR1-data path; files absent",
            "missing",
            False,
        ),
        (
            "point_in_time_guarantee",
            "only data available by each trade day",
            "mutable online search and no released timestamped snapshot",
            "unverifiable",
            False,
        ),
        (
            "single_ticker_interface",
            "multi-asset simulation",
            "propagate(company_name, trade_date) has no portfolio input",
            "mismatch",
            False,
        ),
        (
            "portfolio_state",
            "portfolio/fund state across days",
            "no holdings, cash, orders, or portfolio state",
            "missing",
            False,
        ),
        ("position_sizing", "timing and size of trades", "final output is categorical action only", "missing", False),
        (
            "execution_engine",
            "approved order executed in simulated exchange",
            "no exchange/broker execution path",
            "missing",
            False,
        ),
        (
            "long_short_semantics",
            "figure captions show long/short positions",
            "BUY/SELL/HOLD extraction without borrow or position semantics",
            "missing",
            False,
        ),
        (
            "transaction_costs",
            "realistic net trading",
            "no commission/slippage/borrow implementation",
            "missing",
            False,
        ),
        (
            "baseline_implementations",
            "B&H, MACD, KDJ+RSI, ZMR, SMA",
            "no baseline strategy source files",
            "missing",
            False,
        ),
        ("metric_implementations", "CR, AR, SR, MDD", "no metric calculator", "missing", False),
        ("paper_backtest_runner", "2024-01-01 through 2024-03-29", "one-day propagate example only", "missing", False),
        (
            "paper_experiment_config",
            "exact assets/models/data/rounds",
            "no paper config or reproduction script",
            "missing",
            False,
        ),
        (
            "trials_and_seeds",
            "published estimator provenance",
            "no trial count, seeds, or aggregation path",
            "missing",
            False,
        ),
        (
            "paper_outputs",
            "actions, fills, NAVs, returns, metrics, plots",
            "no tracked eval_results or dated output",
            "missing",
            False,
        ),
        (
            "runtime_state_logging",
            "explainable structured decision trace",
            "writes full_states_log.json when run",
            "component_match",
            True,
        ),
        (
            "source_prompts",
            "role-specific prompts",
            "role prompt functions are shipped",
            "component_match_unverified_experiment_version",
            True,
        ),
        ("upstream_tests", "validated source release", "v0.1.0 ships no tests or CI", "missing", False),
        (
            "dependency_lock",
            "reconstructible environment",
            "unversioned requirements and no lockfile",
            "missing",
            False,
        ),
        (
            "auxiliary_web_prompt",
            "ticker-specific social retrieval",
            "prompt says '{ticker} on TSLA', contaminating non-TSLA requests",
            "source_bug",
            False,
        ),
        (
            "published_numeric_results",
            "77 Table 1 numeric cells plus quantitative figure/text claims",
            "no native result path",
            "missing",
            False,
        ),
    ]

    assertions = [
        ('"data_dir": "/Users/yluo/Documents/Code/ScAI/FR1-data"' in config, "local data path"),
        ('"deep_think_llm": "o4-mini"' in config, "default deep model"),
        ("create_market_analyst(\n                self.quick_thinking_llm" in setup, "quick analyst allocation"),
        ("create_trader(self.quick_thinking_llm" in setup, "quick trader allocation"),
        ("ConditionalLogic()" in graph and "Propagator()" in graph, "ignored round/recursion config"),
        ("max_debate_rounds=1" in logic and "max_risk_discuss_rounds=1" in logic, "hardcoded rounds"),
        ("Can you search Social Media for {ticker} on TSLA" in interface, "auxiliary prompt bug"),
        (readme.count("o1-preview") >= 1 and readme.count("gpt-4o") >= 1, "README model claim"),
        ("pytest" not in requirements.lower(), "no declared test runner"),
        (not any(path.startswith("tests/") for path in files), "no source tests"),
    ]
    failed = [name for passed, name in assertions if not passed]
    if failed:
        raise RuntimeError(f"Pinned source evidence changed: {failed}")
    if len(checks) != 45:
        raise RuntimeError(f"Expected 45 source dimensions, got {len(checks)}")
    return [
        {
            "dimension": dimension,
            "paper_requirement": paper,
            "v0_1_0_evidence": released,
            "status": status,
            "paper_mechanism_credit": credit,
        }
        for dimension, paper, released, status, credit in checks
    ]


def git_files(source_root: Path) -> list[str]:
    output = run_git(source_root, "ls-tree", "-r", "--name-only", SOURCE_COMMIT)
    assert isinstance(output, str)
    return [line for line in output.splitlines() if line]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for relative in git_files(source_root):
        payload = git_blob(source_root, relative)
        rows.append(
            {
                "path": relative,
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "python_source": relative.endswith(".py"),
                "paper_result_artifact": False,
            }
        )
    if len(rows) != 56 or sum(bool(row["python_source"]) for row in rows) != 39:
        raise RuntimeError("Pinned v0.1.0 source inventory changed")
    return rows


def paper_source_inventory(paper_source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(paper_source_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(paper_source_root).as_posix()
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "asset_role": (
                    "numeric_result_figure" if relative in FIGURE_SHA256 else "paper_source_or_architecture_asset"
                ),
                "underlying_numeric_array_shipped": False,
            }
        )
    if len(rows) != 26:
        raise RuntimeError(f"Expected 26 arXiv source assets, got {len(rows)}")
    return rows


COMPONENT_DRIVER = r"""
import importlib.util
import json
import sys
import types
from pathlib import Path

root = Path(sys.argv[1])

def package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module
    return module

def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, root / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

for name in ["tradingagents", "tradingagents.agents", "tradingagents.agents.utils", "tradingagents.graph"]:
    package(name)

states = types.ModuleType("tradingagents.agents.utils.agent_states")
states.AgentState = dict
states.InvestDebateState = lambda value: dict(value)
states.RiskDebateState = lambda value: dict(value)
sys.modules[states.__name__] = states

lc = types.ModuleType("langchain_openai")
lc.ChatOpenAI = type("ChatOpenAI", (), {})
sys.modules[lc.__name__] = lc

class CaptureGraph:
    def __init__(self, state):
        self.nodes = []
        self.edges = []
        self.conditionals = []
    def add_node(self, name, node): self.nodes.append(name)
    def add_edge(self, left, right): self.edges.append([left, right])
    def add_conditional_edges(self, name, router, mapping): self.conditionals.append(name)
    def compile(self): return self

langgraph = package("langgraph")
lg_graph = types.ModuleType("langgraph.graph")
lg_graph.END = "__end__"
lg_graph.START = "__start__"
lg_graph.StateGraph = CaptureGraph
sys.modules[lg_graph.__name__] = lg_graph
lg_prebuilt = types.ModuleType("langgraph.prebuilt")
lg_prebuilt.ToolNode = type("ToolNode", (), {})
sys.modules[lg_prebuilt.__name__] = lg_prebuilt

agent_names = [
    "create_market_analyst", "create_social_media_analyst", "create_news_analyst",
    "create_fundamentals_analyst", "create_msg_delete", "create_bull_researcher",
    "create_bear_researcher", "create_research_manager", "create_trader",
    "create_risky_debator", "create_neutral_debator", "create_safe_debator",
    "create_risk_manager",
]
agents = sys.modules["tradingagents.agents"]
agents.__all__ = agent_names
def factory(name):
    def create(*args, **kwargs): return name
    return create
for name in agent_names:
    setattr(agents, name, factory(name))

agent_utils = types.ModuleType("tradingagents.agents.utils.agent_utils")
agent_utils.Toolkit = type("Toolkit", (), {})
sys.modules[agent_utils.__name__] = agent_utils

conditional = load("tradingagents.graph.conditional_logic", "tradingagents/graph/conditional_logic.py")
setup = load("tradingagents.graph.setup", "tradingagents/graph/setup.py")
propagation = load("tradingagents.graph.propagation", "tradingagents/graph/propagation.py")
signal = load("tradingagents.graph.signal_processing", "tradingagents/graph/signal_processing.py")

logic = conditional.ConditionalLogic(max_debate_rounds=1, max_risk_discuss_rounds=1)
graph = setup.GraphSetup(
    object(), object(), object(),
    {name: f"tools_{name}" for name in ["market", "social", "news", "fundamentals"]},
    object(), object(), object(), object(), object(), logic,
).setup_graph(["market", "social", "news", "fundamentals"])

debate_route = [
    logic.should_continue_debate({"investment_debate_state": {"count": 0, "current_response": ""}}),
    logic.should_continue_debate({"investment_debate_state": {"count": 1, "current_response": "Bull: case"}}),
    logic.should_continue_debate({"investment_debate_state": {"count": 2, "current_response": "Bear: case"}}),
]
risk_route = [
    logic.should_continue_risk_analysis({"risk_debate_state": {"count": 1, "latest_speaker": "Risky Analyst"}}),
    logic.should_continue_risk_analysis({"risk_debate_state": {"count": 2, "latest_speaker": "Safe Analyst"}}),
    logic.should_continue_risk_analysis({"risk_debate_state": {"count": 3, "latest_speaker": "Neutral Analyst"}}),
]

prop = propagation.Propagator()
initial = prop.create_initial_state("AAPL", "2024-01-02")

class Reply:
    content = "BUY"
class FakeLLM:
    def invoke(self, messages):
        assert "SELL, BUY, or HOLD" in messages[0][1]
        return Reply()
decision = signal.SignalProcessor(FakeLLM()).process_signal("FINAL TRANSACTION PROPOSAL: **BUY**")

result = {
    "topology_nodes": graph.nodes,
    "topology_node_count": len(graph.nodes),
    "unconditional_edges": graph.edges,
    "unconditional_edge_count": len(graph.edges),
    "conditional_router_nodes": graph.conditionals,
    "conditional_router_count": len(graph.conditionals),
    "debate_route": debate_route,
    "risk_route": risk_route,
    "initial_state_keys": sorted(initial),
    "recursion_limit": prop.get_graph_args()["config"]["recursion_limit"],
    "signal_extraction": decision,
}
print(json.dumps(result, sort_keys=True))
"""


def run_native_component_checks(source_root: Path, source_python: Path) -> dict[str, Any]:
    archive = run_git(source_root, "archive", "--format=tar", SOURCE_COMMIT, binary=True)
    assert isinstance(archive, bytes)
    with tempfile.TemporaryDirectory(prefix="tradingagents-v010-") as temporary:
        root = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
            bundle.extractall(root, filter="data")
        compile_run = subprocess.run(
            [str(source_python), "-m", "compileall", "-q", str(root)],
            capture_output=True,
            text=True,
        )
        if compile_run.returncode:
            raise RuntimeError(f"Pinned source compile failed: {compile_run.stderr}")
        driver = root / "_audit_component_driver.py"
        driver.write_text(COMPONENT_DRIVER, encoding="utf-8")
        outputs = []
        for _ in range(2):
            run = subprocess.run(
                [str(source_python), str(driver), str(root)],
                check=True,
                capture_output=True,
                text=True,
            )
            outputs.append(json.loads(run.stdout))
        if outputs[0] != outputs[1]:
            raise RuntimeError("Dependency-isolated source topology check is nondeterministic")
    observed = outputs[0]
    expected = {
        "topology_node_count": 20,
        "unconditional_edge_count": 12,
        "conditional_router_count": 9,
        "debate_route": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "risk_route": ["Safe Analyst", "Neutral Analyst", "Risk Judge"],
        "recursion_limit": 100,
        "signal_extraction": "BUY",
    }
    for key, value in expected.items():
        if observed[key] != value:
            raise RuntimeError(f"Pinned source component changed for {key}: {observed[key]!r}")
    normalized = json.dumps(observed, sort_keys=True, separators=(",", ":")).encode()
    return {
        "source_commit": SOURCE_COMMIT,
        "source_python": str(source_python),
        "tracked_python_files_compiled": 39,
        "compile_status": "passed_without_importing_declared_dependencies",
        "upstream_tests_shipped": 0,
        "dependency_environment_reproduced": False,
        "dependency_isolation": "import-only fakes for LangChain/LangGraph; actual tagged routing/setup/propagation/signal files executed",
        "semantic_component": observed,
        "semantic_component_sha256": sha256_bytes(normalized),
        "deterministic_across_two_runs": True,
        "paper_result_reproduction": False,
    }


def verify_pins(
    source_root: Path,
    paper_pdf: Path,
    paper_source_archive: Path,
    paper_source_root: Path,
) -> None:
    if sha256(paper_pdf) != PAPER_SHA256:
        raise RuntimeError(f"Paper PDF hash changed: {sha256(paper_pdf)}")
    if sha256(paper_source_archive) != PAPER_SOURCE_SHA256:
        raise RuntimeError(f"Paper source archive hash changed: {sha256(paper_source_archive)}")
    tag_commit = str(run_git(source_root, "rev-parse", f"{SOURCE_TAG}^{{}}")).strip()
    if tag_commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected {SOURCE_TAG} at {SOURCE_COMMIT}, found {tag_commit}")
    parent = str(run_git(source_root, "rev-parse", f"{SOURCE_COMMIT}^")).strip()
    if parent != PRE_RELEASE_COMMIT:
        raise RuntimeError(f"Expected pre-release parent {PRE_RELEASE_COMMIT}, found {parent}")
    prior_files = git_files_at(source_root, PRE_RELEASE_COMMIT)
    if prior_files != ["README.md", "index.html", "index_complete.html"]:
        raise RuntimeError(f"Pre-release tree changed: {prior_files}")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        observed = sha256_bytes(git_blob(source_root, relative))
        if observed != expected:
            raise RuntimeError(f"Pinned source hash changed for {relative}: {observed}")
    for relative, expected in {**PINNED_PAPER_SOURCE_SHA256, **FIGURE_SHA256}.items():
        observed = sha256(paper_source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned paper-source hash changed for {relative}: {observed}")


def git_files_at(source_root: Path, commit: str) -> list[str]:
    output = run_git(source_root, "ls-tree", "-r", "--name-only", commit)
    assert isinstance(output, str)
    return sorted(line for line in output.splitlines() if line)


def build_audit(
    source_root: Path,
    paper_pdf: Path,
    paper_source_archive: Path,
    paper_source_root: Path,
    source_python: Path,
    output_dir: Path,
) -> dict[str, Any]:
    verify_pins(source_root, paper_pdf, paper_source_archive, paper_source_root)
    table = paper_table_rows()
    annualization = annualization_identity()
    improvement = improvement_identity()
    claims = published_non_table_claims()
    inconsistencies = paper_internal_inconsistencies()
    tools = case_tool_conformance(source_root)
    mechanisms = source_conformance(source_root)
    gaps = specification_gaps()
    inventory = source_inventory(source_root)
    paper_assets = paper_source_inventory(paper_source_root)
    component = run_native_component_checks(source_root, source_python)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "table_1_conformance.csv", table)
    write_csv(output_dir / "annualized_return_identity_audit.csv", annualization)
    write_csv(output_dir / "improvement_identity_audit.csv", improvement)
    write_csv(output_dir / "published_non_table_claims.csv", claims)
    write_csv(output_dir / "paper_internal_inconsistencies.csv", inconsistencies)
    write_csv(output_dir / "appendix_case_tool_conformance.csv", tools)
    write_csv(output_dir / "source_mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "paper_specification_gaps.csv", gaps)
    write_csv(output_dir / "released_source_inventory.csv", inventory)
    write_csv(output_dir / "paper_source_asset_inventory.csv", paper_assets)
    (output_dir / "native_component.json").write_text(json.dumps(component, indent=2) + "\n", encoding="utf-8")

    mechanism_counts = Counter(row["status"] for row in mechanisms)
    credit = sum(bool(row["paper_mechanism_credit"]) for row in mechanisms)
    manifest: dict[str, Any] = {
        "audit": "TradingAgents arXiv v7 versus nearest official v0.1.0 source release",
        "overall_status": "not_reproduced_nearest_release_architecture_components_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": PAPER_VERSION,
        "paper_date": PAPER_DATE,
        "paper_sha256": PAPER_SHA256,
        "paper_source_sha256": PAPER_SOURCE_SHA256,
        "source_url": SOURCE_URL,
        "source_tag": SOURCE_TAG,
        "source_commit": SOURCE_COMMIT,
        "source_commit_date": SOURCE_COMMIT_DATE,
        "pre_release_commit": PRE_RELEASE_COMMIT,
        "pre_release_tree_files": 3,
        "paper_era_source_revision_available": False,
        "nearest_source_release_after_paper_hours": 52.3894,
        "paper_numeric_tables_audited": [1],
        "paper_numeric_table_cells_total": len(table),
        "paper_direct_result_cells_total": 68,
        "paper_derived_improvement_cells_total": 9,
        "native_paper_table_result_cells_reproduced": 0,
        "published_non_table_quantitative_claims_total": len(claims),
        "published_non_table_result_claims_total": 12,
        "native_non_table_result_claims_reproduced": 0,
        "annualized_return_pairs_checked": len(annualization),
        "annualized_return_pairs_matching_published_equation": 0,
        "improvement_cells_checked": len(improvement),
        "improvement_cells_exact_absolute_differences": 7,
        "improvement_cells_inconsistent_with_displayed_values": 1,
        "paper_internal_inconsistencies_total": len(inconsistencies),
        "paper_specification_gaps_total": len(gaps),
        "appendix_unique_tools_total": len(tools),
        "appendix_tools_exactly_present_in_nearest_release": 6,
        "appendix_case_output_reproduced": False,
        "source_mechanism_dimensions_total": len(mechanisms),
        "source_mechanism_status_counts": dict(mechanism_counts),
        "source_mechanism_matches_or_analogues": credit,
        "source_mechanism_fully_faithful": False,
        "tracked_source_files_total": len(inventory),
        "tracked_source_python_files_total": 39,
        "paper_source_assets_total": len(paper_assets),
        "numeric_result_figures_total": 6,
        "numeric_result_figure_arrays_shipped": 0,
        "native_source_python_files_compiled": component["tracked_python_files_compiled"],
        "native_source_upstream_tests_shipped": 0,
        "native_source_dependency_environment_reproduced": False,
        "native_topology_component_deterministic": True,
        "native_topology_component_paper_result_reproduction": False,
        "native_paper_data_snapshot_shipped": False,
        "native_paper_backtest_runner_shipped": False,
        "native_paper_baseline_implementations_shipped": False,
        "native_paper_metric_implementation_shipped": False,
        "native_paper_actions_orders_fills_shipped": False,
        "native_paper_nav_returns_holdings_shipped": False,
        "native_paper_llm_trajectories_shipped": False,
        "native_paper_cost_or_seed_ledger_shipped": False,
        "audit_runtime_called_llm_or_market_data_api": False,
        "interpretation": (
            "The nearest official code is a substantial multi-agent architecture release, but it "
            "arrived about 52 hours after arXiv v7 and the immediately preceding Git tree contains "
            "only site files. It implements several paper roles, structured state, debates, memories, "
            "tool loops, prompts, and runtime logging. It does not ship the paper data, experiment "
            "configuration, portfolio/execution engine, baseline or metric code, backtest runner, "
            "actions, fills, NAVs, returns, plots, seeds, or costs. Its analysts are sequential, its "
            "model assignment conflicts with the paper, only 6/11 appendix tool names remain, and "
            "several advertised config values are not wired into the graph. Therefore 0/77 Table 1 "
            "numeric cells and 0/12 additional quantitative result claims are reproduced. The paper "
            "also contains internal numeric inconsistencies: all 17 CR/AR pairs fail its literal "
            "annualization equation, GOOGL Sharpe improvement is arithmetically wrong, and the prose "
            "MDD bound contradicts AMZN."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
        "paper_source_file_sha256": PINNED_PAPER_SOURCE_SHA256,
        "paper_result_figure_sha256": FIGURE_SHA256,
    }

    report = f"""# TradingAgents paper-level conformance audit

Overall verdict: **not reproduced**. The nearest official release implements a
meaningful architecture subset, but not the experiment that produced the paper.

## Primary-source pins

- Official paper: {PAPER_URL} ({PAPER_VERSION}, {PAPER_DATE}; PDF SHA-256
  `{PAPER_SHA256}`; source archive SHA-256 `{PAPER_SOURCE_SHA256}`).
- Official source: {SOURCE_URL}, tag `{SOURCE_TAG}`, commit `{SOURCE_COMMIT}`
  ({SOURCE_COMMIT_DATE}). It is the first public code release, about 52.4 hours
  after v7. Its parent `{PRE_RELEASE_COMMIT}` contains only the README and two
  project-site HTML files, so no paper-date implementation is present in history.

## What genuinely passes

- All 39 tagged Python files compile under Python 3.12. The actual tagged graph
  setup, routing, state initialization, and signal extraction execute twice with
  identical output when unavailable framework imports are replaced by import-only
  fakes. This validates deterministic topology components, not the dependency
  environment, LLM calls, data, backtest, or paper results.
- The release contains four analyst roles, structured shared reports, bull/bear
  debate, a research manager, trader, three risk perspectives, role prompts,
  memories/reflection hooks, categorical BUY/SELL/HOLD extraction, and runtime
  state logging. These are substantive mechanism matches or analogues.
- Six of the eleven unique tool names in the published AAPL appendix transcript
  exist exactly in v0.1.0. The arXiv source also ships six vector performance
  figures, whose hashes and visible annotations are inventoried.

## Why the paper is not replicated

- Table 1 has **77 numeric cells**: 68 direct method results and nine derived
  improvements. **0/77** has a native released result path. Twelve additional
  quantitative result claims in prose/figures also have zero reproductions.
- No frozen multimodal dataset, 60-indicator definition, experiment config,
  backtest runner, baseline implementation, metric code, portfolio state,
  position sizing, execution engine, commission/slippage rules, action history,
  order/fill log, NAV/return path, plot array, trial seed, or API-cost ledger is
  released. Offline mode points to an author-local directory that is not shipped.
- The source executes analysts sequentially although the paper says concurrently;
  assigns the quick model to analysts/researchers/trader although the paper says
  deep; conflates the fund manager with the terminal risk judge; outputs only a
  categorical action; and does not wire configured debate/risk/recursion limits
  into the corresponding routing objects.
- Five of eleven appendix tool names are absent from the nearest release. The
  exact AAPL 2024-11-19 transcript and BUY cannot be replayed without its frozen
  inputs, model snapshots, prompts/tool schemas, and trace.

## Paper-internal barriers

- All 17 displayed CR/AR pairs fail the paper's literal annualized-return formula
  for the stated 89-day period; for example, AAPL TradingAgents CR=26.62% implies
  about 163.43% annualized, not the reported 30.5%.
- GOOGL TradingAgents SR 6.39 minus the best displayed baseline 2.31 is 4.08,
  not the reported 4.26. The improvement row is otherwise mostly absolute metric
  differences despite its percent label.
- GOOGL ZMR has negative CR but positive AR, impossible under the two published
  return formulas for positive N. The prose says MDD never exceeds 2%, while
  Table 1 reports 2.11% for AMZN.
- The setup names AAPL/NVDA/MSFT/META/GOOGL, while the result table reports
  AAPL/GOOGL/AMZN. The exact experiment universe is therefore internally unclear.

## Honest boundary

The architecture is real and useful, but a current one-day run would use mutable
data and changed model endpoints and would not reproduce the 2024 paper. The
vector figures expose annotations, not their daily numeric arrays. Run
`scripts/audit_tradingagents_paper.py` to regenerate this package; `--strict`
fails until the native paper data, exact experiment source/configuration, models,
traces, portfolio/execution rules, baselines, daily outputs, and published values
are reproduced.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get("TRADINGAGENTS_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_source")
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "TRADINGAGENTS_PAPER_PDF",
                project_root
                / "literature_review/papers/23_tradingagents_multi_agents_llm_financial_trading_framework.pdf",
            )
        ),
    )
    parser.add_argument(
        "--paper-source-archive",
        type=Path,
        default=Path(
            os.environ.get(
                "TRADINGAGENTS_PAPER_SOURCE_ARCHIVE",
                "/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_paper_v7/tradingagents_paper_v7_source.tar",
            )
        ),
    )
    parser.add_argument(
        "--paper-source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "TRADINGAGENTS_PAPER_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_paper_v7/source"
            )
        ),
    )
    parser.add_argument(
        "--source-python",
        type=Path,
        default=Path(os.environ.get("TRADINGAGENTS_SOURCE_PYTHON", DEFAULT_SOURCE_PYTHON)),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/tradingagents",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root,
        args.paper_pdf,
        args.paper_source_archive,
        args.paper_source_root,
        args.source_python,
        args.output_dir,
    )
    print(json.dumps(manifest, indent=2))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
