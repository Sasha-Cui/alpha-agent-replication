#!/usr/bin/env python3
"""Audit ContestTrade paper v4 against its pinned public source release.

The audit is deliberately fail closed. It inventories every numeric result in
paper Tables 1--3, statically traces the public CLI, checks the two isolated
contest components, compares the ZI reward equations with released semantics,
and inventories shipped model/cache artifacts. It never imports the upstream
package, unpickles its joblib files, or calls an LLM or external data API.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SOURCE_COMMIT = "22432f9bbba5f1d6862d3b6b5508d4d882b40b94"
SOURCE_URL = "https://github.com/FinStep-AI/ContestTrade"
PAPER_URL = "https://arxiv.org/pdf/2508.00554v4"
PAPER_SHA256 = "a2fd14e7e9074c535ab238a4a9028365c860169743e06223bd20302de549a15c"

PINNED_SOURCE_SHA256 = {
    "README.md": "fb77bb27b3ba888c015d0fa9cbdc82bb083aa0be79d72081b030eff1ac771830",
    "README_en.md": "ed99cc6175beb76bf81e846e4ed9d6b26cc1d6f778d23ecdea6511ede255820f",
    "config.yaml": "1f5835d06f46ccf528c1861802e37bab90cac52fcd596c3001682a8e3af1f1f7",
    "uv.lock": "5563509e7ae60e3c8e833ed54cc86d13fc1f9e503d074baf251a60fe861c1cb7",
    "contest_trade/main.py": "6b25ceda52272a10876f398d1c230999e5392f128a6ef022b8df3dd36c959880",
    "contest_trade/contest/data_analyst/data_contest.py": "e59b7c66ceb718a55d22fe7d4e1397abe72fc12881e6c3136986324bcb0cf720",
    "contest_trade/contest/data_analyst/evaluator.py": "948bd379e55a7d75a20990ae966d4f1f5e7241935a891cad8384bc193ce56716",
    "contest_trade/contest/data_analyst/predictor.py": "e5b8c20b2f4308d073a8b5b50cfd89c692d6fcd75d87dc35412491749230a106",
    "contest_trade/contest/data_analyst/lightgbm_predictor/lgbm_mean_model.joblib": "b465f26e4493e77de35b9821038f95ee87074044cff92099d69fdf5478f7036e",
    "contest_trade/contest/data_analyst/lightgbm_predictor/lgbm_std_model.joblib": "418a45f8848aef18f1b1f1de17b26b9d3873e1d11f7da4e378be3e37d6769fbf",
    "contest_trade/contest/researcher/research_contest.py": "80004deb52f673d28e7c2ffbfef3f3da68be0794d2445903ad95e584b7f916af",
    "contest_trade/contest/researcher/research_predictor.py": "36742c53b7abf10d2599642fae05e87f8cd2e9052232d16d2468b6e3e461f0cc",
    "contest_trade/contest/researcher/research_weight_optimizer.py": "509725dc372c401f79158f5dd174c81a9a8da39f8a35c70ad53f462a0fa6296a",
    "contest_trade/contest/researcher/research_signal_judger.py": "768699811c13e2c5e480337884a0ec78c3f69b9cf5b1e652c1530ded03aa4e38",
    "contest_trade/utils/market_manager.py": "9ee554492cc6ea582ddf70ebf799a0a3fa5952ab722f28a7c63a243b627a040b",
    "contest_trade/agents/data_analysis_agent.py": "d71027810fd287438132a2ac87baf79fc416ba750e72909cc190f120161dbe83",
    "cli/main.py": "cab8909e0f4fe7e0adb9778b84cd9dac3bba8eb3192e768d919e32811cc0376f",
    "requirements.txt": "bb4d9ae6afd058639137e0f37b2a7f8487957d7431728c88ef3e59b801943945",
    "pyproject.toml": "f74bad584b3d452aa9c5cabcb5983e5335db17f52ef19a0cd4e9fa1f51a9a90e",
}

# method|cumulative return %|Sharpe ratio|max drawdown %
TABLE_1_TEXT = """
CSI All Share|4.42|0.46|13.75
MACD|2.69|0.10|10.65
RSI&KDJ|8.19|0.47|8.30
LGBM|-25.94|-1.30|34.17
LSTM|8.34|0.51|29.56
A2C|7.89|0.69|18.84
PPO|15.07|1.33|17.11
MASS|-19.12|-1.76|24.55
ContestTrade|52.80|3.12|12.41
"""

# team|setting|rank IC|ICIR
TABLE_2_TEXT = """
Data Analyst|Contest|0.054|0.13
Researcher|Contest|0.079|0.18
"""

# configuration|cumulative return %|Sharpe ratio|max drawdown %
TABLE_3_TEXT = """
Full|52.80|3.12|12.41
w/o LLM Judge|50.55|2.57|13.48
w/o Contest Researcher|32.83|1.78|16.70
w/o Contest Data Analyst|42.85|2.01|13.47
w/o Deep Research|43.75|2.08|20.55
w/o All|3.01|0.07|26.63
"""

METRICS = ("cumulative_return_pct", "sharpe_ratio", "max_drawdown_pct")
MODEL_FEATURES = (
    "reward_mean_1d",
    "reward_mean_3d",
    "reward_std_3d",
    "reward_mean_5d",
    "reward_std_5d",
)


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


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_result_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in TABLE_1_TEXT.strip().splitlines():
        method, *values = line.split("|")
        for metric, value in zip(METRICS, values):
            rows.append(
                {
                    "paper_table": 1,
                    "entity": method,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    for line in TABLE_2_TEXT.strip().splitlines():
        team, setting, rank_ic, icir = line.split("|")
        for metric, value in (("rank_ic", rank_ic), ("icir", icir)):
            rows.append(
                {
                    "paper_table": 2,
                    "entity": f"{team} {setting}",
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    for line in TABLE_3_TEXT.strip().splitlines():
        configuration, *values = line.split("|")
        for metric, value in zip(METRICS, values):
            rows.append(
                {
                    "paper_table": 3,
                    "entity": configuration,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    if Counter(row["paper_table"] for row in rows) != {1: 27, 2: 4, 3: 18}:
        raise RuntimeError("Paper result denominator changed")
    return rows


def result_conformance() -> list[dict[str, Any]]:
    reason_by_table = {
        1: "no released native return path, baseline runner, backtester, or metric evaluator",
        2: "no released native contest-score path, evaluation panel, or RankIC/ICIR evaluator",
        3: "no released ablation runner, return path, or metric evaluator",
    }
    return [
        {
            **row,
            "native_reproduced_value": "",
            "absolute_difference": "",
            "status": "unavailable_missing_native_result_path",
            "reason": reason_by_table[row["paper_table"]],
        }
        for row in paper_result_rows()
    ]


def paper_internal_consistency() -> list[dict[str, Any]]:
    table_1_ours = {
        row["metric"]: row["paper_value"]
        for row in paper_result_rows()
        if row["paper_table"] == 1 and row["entity"] == "ContestTrade"
    }
    table_3_full = {
        row["metric"]: row["paper_value"]
        for row in paper_result_rows()
        if row["paper_table"] == 3 and row["entity"] == "Full"
    }
    return [
        {
            "metric": metric,
            "table_1_contesttrade": table_1_ours[metric],
            "table_3_full": table_3_full[metric],
            "absolute_difference": abs(table_1_ours[metric] - table_3_full[metric]),
            "status": "paper_internal_identity_match_not_independent_reproduction",
        }
        for metric in METRICS
    ]


def ast_class_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
    raise RuntimeError(f"Class {class_name} not found in {path}")


def ast_string_calls(path: Path, attribute: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == attribute and node.args and isinstance(node.args[0], ast.Constant):
            if isinstance(node.args[0].value, str):
                values.append(node.args[0].value)
    return values


def entrypoint_reachability(source_root: Path) -> list[dict[str, Any]]:
    main_path = source_root / "contest_trade/main.py"
    cli_path = source_root / "cli/main.py"
    research_contest_path = source_root / "contest_trade/contest/researcher/research_contest.py"
    research_predictor_path = source_root / "contest_trade/contest/researcher/research_predictor.py"
    main_text = main_path.read_text(encoding="utf-8")
    cli_text = cli_path.read_text(encoding="utf-8")
    research_text = research_contest_path.read_text(encoding="utf-8")
    predictor_methods = ast_class_methods(research_predictor_path, "ResearchPredictor")
    nodes = ast_string_calls(main_path, "add_node")
    model_dir = research_predictor_path.parent / "lightgbm_predictor"
    return [
        {
            "check": "public_cli_import",
            "paper_requirement": "runnable system entrypoint",
            "released_evidence": "cli/main.py imports and constructs SimpleTradeCompany",
            "observed": str("from contest_trade.main import SimpleTradeCompany" in cli_text),
            "status": "component_present",
        },
        {
            "check": "active_workflow_nodes",
            "paper_requirement": "data agents -> Data Contest -> researchers -> Research Contest -> portfolio",
            "released_evidence": ",".join(nodes),
            "observed": str(nodes),
            "status": "mismatch_contests_and_portfolio_absent",
        },
        {
            "check": "data_contest_reachable",
            "paper_requirement": "Data Contest scores and allocates factor context",
            "released_evidence": "no DataContest reference/import/call in contest_trade/main.py",
            "observed": str("DataContest" in main_text),
            "status": "not_reachable_from_public_entrypoint",
        },
        {
            "check": "research_contest_reachable",
            "paper_requirement": "Research Contest predicts and weights signals",
            "released_evidence": "no ResearchContest reference/import/call in contest_trade/main.py",
            "observed": str("ResearchContest" in main_text),
            "status": "not_reachable_from_public_entrypoint",
        },
        {
            "check": "portfolio_construction",
            "paper_requirement": "positive-Sharpe weighted portfolio",
            "released_evidence": "finalize assigns best_signals = research_signals without allocation",
            "observed": str("best_signals = research_signals" in main_text),
            "status": "mismatch_no_active_allocation",
        },
        {
            "check": "research_model_files",
            "paper_requirement": "runnable Research Contest predictor",
            "released_evidence": "ResearchPredictor raises FileNotFoundError when two joblibs are absent",
            "observed": str((model_dir / "lgbm_mean_model.joblib").exists() or (model_dir / "lgbm_std_model.joblib").exists()),
            "status": "missing_both_required_models",
        },
        {
            "check": "research_predict_signal_scores_method",
            "paper_requirement": "Research Contest callable prediction method",
            "released_evidence": "research_contest.py calls predict_signal_scores",
            "observed": str("predict_signal_scores" in predictor_methods),
            "status": "missing_called_method" if "predict_signal_scores" in research_text else "changed_call_path",
        },
    ]


def paper_zi_reward(pairs: Sequence[tuple[float, float]]) -> float:
    """Paper Algorithm 1: signed rating times percent price change, summed."""
    return sum(rating * price_change_pct for rating, price_change_pct in pairs)


def released_zi_reward(pairs: Sequence[tuple[float, float]]) -> float:
    """Exact released evaluator behavior for valid price changes, without importing it."""
    if not pairs:
        return 0.0
    total = 0.0
    for rating, price_change_pct in pairs:
        clipped = max(-20.0, min(20.0, price_change_pct))
        if rating > 0:
            total += rating * clipped
    return total / len(pairs)


def zi_semantics_rows() -> list[dict[str, Any]]:
    cases = {
        "symmetric_bullish_and_correct_bearish": [(2.0, 5.0), (-2.0, -5.0)],
        "bearish_but_price_rises": [(-2.0, 5.0)],
        "single_bullish": [(2.0, 5.0)],
        "clipping_changes_large_move": [(1.0, 25.0)],
    }
    return [
        {
            "case": name,
            "rating_price_change_pct_pairs": json.dumps(pairs),
            "paper_signed_sum": paper_zi_reward(pairs),
            "released_positive_only_clipped_average": released_zi_reward(pairs),
            "absolute_difference": abs(paper_zi_reward(pairs) - released_zi_reward(pairs)),
            "status": "match" if paper_zi_reward(pairs) == released_zi_reward(pairs) else "semantic_mismatch",
        }
        for name, pairs in cases.items()
    ]


def safe_model_inventory(source_root: Path) -> list[dict[str, Any]]:
    """Inspect serialized model bytes as text; never execute joblib/pickle payloads."""
    model_dir = source_root / "contest_trade/contest/data_analyst/lightgbm_predictor"
    rows = []
    for name in ("lgbm_mean_model.joblib", "lgbm_std_model.joblib"):
        path = model_dir / name
        raw = path.read_bytes()
        text = raw.decode("latin1", errors="ignore")
        feature_match = re.search(r"feature_names=([^\r\n]+)", text)
        features = feature_match.group(1).strip().split() if feature_match else []
        rows.append(
            {
                "file": path.relative_to(source_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "safe_inspection_only": True,
                "model_class_string_present": "LGBMRegressor" in text,
                "objective_regression_l1_present": "objective=regression_l1" in text,
                "feature_names": " ".join(features),
                "feature_count": len(features),
                "expected_five_feature_set": features == list(MODEL_FEATURES),
                "training_dates_split_seed_provenance_present": False,
                "status": "shipped_component_without_training_provenance",
            }
        )
    return rows


def cache_inventory(source_root: Path) -> list[dict[str, Any]]:
    cache_dir = source_root / "contest_trade/utils/cache/market_manager"
    rows = []
    for path in sorted(cache_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if path.name == "trade_calendar.json":
            records = len(data["trade_dates"])
            start = data["trade_dates"][0]
            end = data["trade_dates"][-1]
            snapshot = data.get("last_updated", "")
        elif isinstance(data, list):
            records = len(data)
            trade_dates = sorted({str(row.get("trade_date", "")) for row in data if isinstance(row, dict) and row.get("trade_date")})
            start = trade_dates[0] if trade_dates else ""
            end = trade_dates[-1] if trade_dates else ""
            snapshot = trade_dates[-1] if trade_dates else ""
        else:
            records = len(data)
            start = ""
            end = ""
            snapshot = ""
        rows.append(
            {
                "file": path.relative_to(source_root).as_posix(),
                "sha256": sha256(path),
                "record_count": records,
                "date_start": start,
                "date_end": end,
                "snapshot_or_update_date": snapshot,
                "paper_native_input_or_output": False,
                "status": "released_market_metadata_cache_not_paper_experiment_panel",
            }
        )
    return rows


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for relative in git_files(source_root):
        path = source_root / relative
        rows.append(
            {
                "file": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "paper_result_artifact": False,
            }
        )
    return rows


def source_conformance(source_root: Path) -> list[dict[str, Any]]:
    data_contest = (source_root / "contest_trade/contest/data_analyst/data_contest.py").read_text(encoding="utf-8")
    evaluator = (source_root / "contest_trade/contest/data_analyst/evaluator.py").read_text(encoding="utf-8")
    predictor = (source_root / "contest_trade/contest/data_analyst/predictor.py").read_text(encoding="utf-8")
    research_predictor = (source_root / "contest_trade/contest/researcher/research_predictor.py").read_text(encoding="utf-8")
    optimizer = (source_root / "contest_trade/contest/researcher/research_weight_optimizer.py").read_text(encoding="utf-8")
    config = (source_root / "config.yaml").read_text(encoding="utf-8")
    data_agent = (source_root / "contest_trade/agents/data_analysis_agent.py").read_text(encoding="utf-8")
    market = (source_root / "contest_trade/utils/market_manager.py").read_text(encoding="utf-8")
    rows = [
        ("paper_test_period", "2025-01-01 through 2025-06-30", "no experiment date driver/config", "missing"),
        ("paper_training_validation_period", "2024-07 through 2024-12 or earlier", "no training dataset/split driver", "missing"),
        ("daily_a_share_universe", "China A-share daily", "market utilities exist; experiment universe snapshot absent", "partial"),
        ("transaction_cost", "0.001", "CN utility uses multiple commission/stamp/transfer/slippage fields", "mismatch"),
        ("t_plus_one_and_price_limits", "enforced", "market utility code exists; no released backtester", "partial_unverified"),
        ("data_history_window_m", "m=5", "Data predictor constructs 1d/3d/5d reward summaries", "component_match"),
        ("research_prediction_window_n", "n=5", "ResearchPredictor default prediction_window_days=3", "mismatch"),
        ("factor_model_features", "mean, volatility, trend, drawdown", "shipped models expose mean/std only", "mismatch"),
        ("rolling_daily_training", "retrain only on labels realized before decision t", "two fixed joblibs; no data-contest trainer or training provenance", "missing"),
        ("data_allocation", "token-budgeted facility-location lazy greedy; L0=32k L*=16k", "sort predicted scores and select top_k=3", "mismatch"),
        ("data_similarity", "embedding cosine similarity", "no facility-location/cosine path in DataContest", "missing"),
        ("research_allocation", "max(0, Sharpe) normalized", "optimizer clips negative Sharpe and normalizes positive total", "component_match"),
        ("zi_rating_scale", "integer -2,-1,0,1,2", "LLM rating prompt requests -2 through 2", "component_match"),
        ("zi_reward_aggregation", "signed rating*price-change sum", "positive ratings only; +/-20 clip; average over valid observations", "mismatch"),
        ("paper_agent_tool_count", "8 tools", "research config lists 7 tool names", "mismatch"),
        ("factor_context_budget", "about 4k tokens per factor", "default final_target_tokens=4000; at least one check uses string length", "partial"),
        ("data_contest_switch", "Data Contest active", "isolated code exists but active public workflow never calls it", "not_implemented_in_active_path"),
        ("research_contest_switch", "Research Contest active", "config contest_mode false and active workflow never calls it", "not_implemented_in_active_path"),
        ("deepseek_models", "DeepSeek-V3 and DeepSeek-R1", "aliases deepseek-chat and deepseek-reasoner; exact snapshots absent", "partial_unpinned"),
        ("llm_temperature", "paper provides no complete numeric run configuration", "mutable source values such as 0.7 and 0.1", "paper_underspecified"),
        ("temporal_search_filter", "records no later than formation date", "search request bounds prior 30 days; original returned record snapshot absent", "component_partial"),
        ("paper_input_snapshot", "exact news/financial/price data", "only market metadata caches shipped", "missing"),
        ("paper_output_snapshot", "contest scores, actions, holdings, returns", "no tracked native experiment outputs", "missing"),
        ("backtest_evaluator", "CR, Sharpe, MDD and constraints", "no released experiment backtester/metric evaluator", "missing"),
        ("baseline_implementations", "8 paper baselines", "no released native paper baseline runner", "missing"),
        ("ablation_runner", "five ablations plus full", "no released ablation experiment driver", "missing"),
        ("random_seeds", "exact stochastic controls", "no paper-run seeds", "missing"),
        ("cost_or_api_snapshot", "exact external services and responses", "keys/services required; no immutable response snapshot", "missing"),
        ("csi_component_cache_time", "point-in-time universe at each decision", "CSI utility paths load cache snapshot trade_date 20250630", "current_release_path_risk"),
    ]
    # Source-pinned assertions supporting the human-readable observations above.
    assert "top_k" in data_contest and "sorted" in data_contest
    assert "rating > 0" in evaluator and "total_reward / valid_count" in evaluator
    assert all(feature in predictor for feature in MODEL_FEATURES)
    assert "prediction_window_days: int = 3" in research_predictor
    assert "if sharpe_ratio > 0" in optimizer and "/ total_sharpe" in optimizer
    assert "contest_mode: False" in config
    assert "final_target_tokens" in data_agent
    assert "20250630" in market
    return [
        {
            "dimension": dimension,
            "paper_requirement": requirement,
            "released_evidence": evidence,
            "status": status,
        }
        for dimension, requirement, evidence, status in rows
    ]


def verify_pins(source_root: Path, paper_pdf: Path) -> str:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_pdf) != PAPER_SHA256:
        raise RuntimeError(f"Expected paper SHA-256 {PAPER_SHA256}, found {sha256(paper_pdf)}")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        path = source_root / relative
        observed = sha256(path)
        if observed != expected:
            raise RuntimeError(f"Pinned hash changed for {relative}: {observed}")
    return commit


def build_audit(source_root: Path, paper_pdf: Path, output_dir: Path) -> dict[str, Any]:
    commit = verify_pins(source_root, paper_pdf)
    conformance = result_conformance()
    identities = paper_internal_consistency()
    reachability = entrypoint_reachability(source_root)
    zi_rows = zi_semantics_rows()
    models = safe_model_inventory(source_root)
    caches = cache_inventory(source_root)
    source = source_inventory(source_root)
    config = source_conformance(source_root)

    if len(conformance) != 49 or {row["status"] for row in conformance} != {"unavailable_missing_native_result_path"}:
        raise RuntimeError("Pinned result-cell boundary changed")
    if len(source) != 117:
        raise RuntimeError(f"Expected 117 tracked source files, got {len(source)}")
    if len(caches) != 7 or len(models) != 2:
        raise RuntimeError("Pinned release artifact inventory changed")
    if len([row for row in zi_rows if row["status"] == "semantic_mismatch"]) != 3:
        raise RuntimeError("Pinned ZI semantic diagnostic changed")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_1_3_conformance.csv", conformance)
    write_csv(output_dir / "paper_internal_consistency.csv", identities)
    write_csv(output_dir / "source_entrypoint_reachability.csv", reachability)
    write_csv(output_dir / "zi_reward_semantics_audit.csv", zi_rows)
    write_csv(output_dir / "shipped_lightgbm_model_inventory.csv", models)
    write_csv(output_dir / "released_cache_inventory.csv", caches)
    write_csv(output_dir / "source_config_conformance.csv", config)
    write_csv(output_dir / "released_source_inventory.csv", source)

    manifest: dict[str, Any] = {
        "audit": "ContestTrade paper v4 Tables 1--3 versus pinned public release",
        "overall_status": "not_reproduced_public_entrypoint_omits_contests",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": "arXiv:2508.00554v4",
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "source_commit_date": "2025-12-22",
        "paper_numeric_tables_audited": [1, 2, 3],
        "paper_numeric_result_cells_total": 49,
        "paper_table_cell_counts": {"1": 27, "2": 4, "3": 18},
        "native_paper_result_cells_reproduced": 0,
        "paper_numeric_result_cells_unavailable": 49,
        "paper_internal_repeated_cells_consistent": 3,
        "paper_internal_repeated_cells_independent_reproductions": 0,
        "tracked_source_files_total": len(source),
        "active_public_workflow_nodes": ["run_data_agents", "run_research_agents", "finalize"],
        "data_contest_reachable_from_public_entrypoint": False,
        "research_contest_reachable_from_public_entrypoint": False,
        "active_portfolio_constructor_present": False,
        "isolated_data_contest_code_present": True,
        "data_contest_shipped_model_files": 2,
        "data_contest_model_training_provenance_present": False,
        "data_contest_facility_location_allocator_present": False,
        "research_contest_required_model_files_present": False,
        "research_predict_signal_scores_method_present": False,
        "research_positive_sharpe_weight_component_present": True,
        "zi_semantic_diagnostic_cases": len(zi_rows),
        "zi_semantic_mismatch_cases": sum(row["status"] == "semantic_mismatch" for row in zi_rows),
        "native_experiment_input_snapshot_shipped": False,
        "native_contest_scores_actions_holdings_or_returns_shipped": False,
        "native_backtest_metric_evaluator_shipped": False,
        "native_baseline_runner_shipped": False,
        "native_ablation_runner_shipped": False,
        "exact_paper_run_seeds_shipped": False,
        "audit_imported_upstream_package": False,
        "audit_unpickled_shipped_models": False,
        "audit_called_llm_or_external_api": False,
        "paper_v4_postdates_pinned_source_commit": True,
        "interpretation": (
            "The public release contains agent utilities and inspectable pieces of both contests, "
            "but the CLI runs SimpleTradeCompany, whose graph has only data agents, research "
            "agents, and finalize. It never calls DataContest or ResearchContest and finalize "
            "passes through all research signals without the paper's allocation. The isolated "
            "ResearchContest is not runnable as pinned because its two required model files and "
            "a called prediction method are absent. The isolated DataContest ships two fixed "
            "models but no rolling-training provenance, uses top-3 score sorting instead of the "
            "paper's token-budgeted facility-location allocator, and changes the signed ZI reward "
            "into a clipped positive-only average. With no paper data/output snapshot, experiment "
            "driver, baselines, backtester, ablations, or seeds, 0/49 paper result cells can be "
            "counted as native reproductions."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
    }

    report = f"""# ContestTrade paper-level conformance audit

Overall verdict: **not reproduced**. The current paper (arXiv v4) and public
source contain meaningful component-level evidence, but the released CLI does
not execute either contest described as the core contribution.

## Primary sources

- Official paper: {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}` (2025-12-22).

The source snapshot predates paper v4 (2026-07-08). This timing may explain some
formalism/source drift, but it cannot make absent public execution paths or data
count as reproduced.

## What the release genuinely preserves

- A public CLI constructs `SimpleTradeCompany`; its data and research agent paths
  are inspectable, and selected search tools bound requests to dates before the
  trigger date.
- The isolated Data Contest contains five-day reward features and two serialized
  LightGBM models. This audit reads their bytes only (never unpickles them) and
  confirms the five feature names and L1-regression metadata. No training dates,
  split, daily rolling trainer, seed, or dataset accompanies them.
- The isolated Research weight optimizer implements the paper's positive-Sharpe
  normalization rule. This is a component match, not an executed paper portfolio.
- The paper is internally consistent where Table 3 Full repeats the three Table 1
  ContestTrade metrics. Those identities are not independent results.

## Why the claimed system is not replicated

- Static tracing of the actual CLI reaches a three-node graph:
  `run_data_agents -> run_research_agents -> finalize`. Neither `DataContest` nor
  `ResearchContest` is imported or called. `finalize` simply exposes all research
  signals; it does not construct the paper portfolio.
- The isolated Research Contest requires two model files that are not released and
  calls `predict_signal_scores`, which `ResearchPredictor` does not define. Its
  default prediction horizon is three days, while paper v4 specifies five.
- The Data Contest sorts predicted scores and retains top three. It does not implement
  the paper's 32k-to-16k token-budgeted facility-location/lazy-greedy allocation or
  embedding cosine diversity objective.
- Paper Algorithm 1 sums signed rating x price change for ratings -2 through 2. The
  released evaluator ignores every non-positive rating, clips changes to +/-20%, and
  averages over valid observations. The committed synthetic diagnostic shows, for
  example, paper reward 20 versus released reward 5 for a correct bullish and a
  correct bearish observation.
- The release has no immutable paper input panel, contest scores, selected factors,
  actions, holdings, daily returns, experiment/backtest evaluator, baseline runner,
  ablation driver, or paper-run seeds. The seven JSON caches are market metadata,
  not the paper's news/financial/price inputs or outputs.

## Honest denominator

All **49** numeric cells in Tables 1--3 are enumerated: 27 main performance cells,
4 contest-score cells, and 18 ablation cells. **0/49** are native reproductions and
49/49 are unavailable from released result paths. The three repeated Full/Ours
cells agree internally but are counted only as identities. Static figures, code
presence, model strings, and architectural proxies never receive result credit.

Run `scripts/audit_contesttrade_paper.py` to regenerate this evidence package. Use
`--strict` to fail until the released system executes both contests and reproduces
the native paper data, configurations, trajectories, portfolio, and all 49 values.
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
                "CONTESTTRADE_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/contesttrade_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "CONTESTTRADE_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/contesttrade_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/contesttrade",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(), args.paper_pdf.resolve(), args.output_dir.resolve()
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
