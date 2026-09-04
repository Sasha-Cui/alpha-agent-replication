#!/usr/bin/env python3
"""Evaluate the frozen QuantaAlpha historical GPT factor pool on monthly U.S./JKP data."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import types
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

from alpha_evolve.headline_backtest import return_statistics
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


SOURCE_COMMIT = "8a034319ff925d9dc621077ebf97d48e1890dad2"
SOURCE_FACTOR_SHA256 = "659baa259a909b5e5600dc0270c076d95f7e1d4fde6479e74cd4e3f558a0bf4e"
SOURCE_FACTOR_PATH = "factor_library/RANKIC_desc_150_QA_round11_best_gpt_123_csi300.json"
INPUT_COLUMNS = [
    "id", "permno", "eom", "me", "ret", "ret_exc_lead1m", "prc", "prc_high", "prc_low", "tvol"
]
ALPHA158_20_NAMES = [
    "ROC0", "ROC1", "ROC5", "ROC10", "ROC20", "VRATIO5", "VRATIO10", "VSTD5_RATIO",
    "RANGE", "VOLATILITY5", "VOLATILITY10", "RET_VOL5", "RSV5", "RSV10", "HIGH_RATIO5",
    "LOW_RATIO5", "SHADOW_RATIO", "BODY_RATIO", "MA_RATIO5_10", "MA_RATIO10_20",
]
MODEL_PARAMETERS = {
    "objective": "mse",
    "verbosity": -1,
    "learning_rate": 0.1,
    "max_depth": 8,
    "num_leaves": 210,
    "colsample_bytree": 0.8879,
    "subsample": 0.8789,
    "lambda_l1": 205.6999,
    "lambda_l2": 580.9768,
    "num_threads": 20,
    "seed": 42,
    "random_state": 42,
    "min_child_samples": 100,
    "feature_fraction_bynode": 0.8,
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def translate_expression(expression: str) -> str:
    """Retain source expressions literally; one source period becomes one monthly period."""
    return expression


def monthly_bars(raw: pd.DataFrame) -> pd.DataFrame:
    close = pd.to_numeric(raw.prc, errors="coerce").abs()
    ret = pd.to_numeric(raw.ret, errors="coerce")
    opening = (close / (1.0 + ret)).where(ret.gt(-1.0) & np.isfinite(ret) & close.gt(0))
    return pd.DataFrame(
        {
            "$open": opening,
            "$high": pd.to_numeric(raw.prc_high, errors="coerce").abs(),
            "$low": pd.to_numeric(raw.prc_low, errors="coerce").abs(),
            "$close": close,
            "$volume": pd.to_numeric(raw.tvol, errors="coerce"),
            "$return": ret,
        },
        index=raw.index,
    )


def source_cs_rank_norm(frame: pd.DataFrame) -> pd.DataFrame:
    """Reproduce Fillna, ProcessInf, then CSRankNorm from the released profile."""
    values = frame.astype("float64").fillna(0.0)
    finite = values.replace([np.inf, -np.inf], np.nan)
    means = finite.groupby(level="datetime", sort=False).transform("mean")
    values = values.mask(~np.isfinite(values), means).fillna(0.0)
    ranks = values.groupby(level="datetime", sort=False).rank(method="average", pct=True)
    return (ranks - 0.5) * 3.46


def label_cs_rank_norm(label: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=label.index, dtype="float64")
    finite = label.loc[np.isfinite(label)]
    result.loc[finite.index] = (
        finite.groupby(level="datetime", sort=False).rank(method="average", pct=True) - 0.5
    ) * 3.46
    return result


def _package(name: str) -> None:
    module = types.ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def install_author_factor_modules(source_root: Path) -> tuple[Any, Any]:
    """Load the author's parser/operators without importing the LLM agent stack."""
    source_root = source_root.resolve()
    sys.path.insert(0, str(source_root))
    for name in (
        "alphaagent", "alphaagent.components", "alphaagent.components.coder",
        "alphaagent.components.coder.factor_coder",
    ):
        _package(name)
    factor_code = source_root / "alphaagent/components/coder/factor_coder"
    function_lib = _load(
        "alphaagent.components.coder.factor_coder.function_lib", factor_code / "function_lib.py"
    )
    parser = _load(
        "alphaagent.components.coder.factor_coder.expr_parser", factor_code / "expr_parser.py"
    )

    def broadcast_mean(value):
        return value.groupby(level="datetime").transform("mean")

    original_parallel = function_lib.Parallel

    def one_worker_parallel(*_args, **kwargs):
        kwargs["n_jobs"] = 1
        return original_parallel(**kwargs)

    function_lib.MEAN = broadcast_mean
    function_lib.Parallel = one_worker_parallel
    return parser, function_lib


def evaluate_expression(expression: str, data: pd.DataFrame, parser: Any, functions: Any) -> pd.Series:
    parsed = parser.parse_symbol(translate_expression(expression), data.columns)
    with redirect_stdout(io.StringIO()):
        parsed = parser.parse_expression(parsed)
    for column in data.columns:
        parsed = parsed.replace(column[1:], f"df[{column!r}]")
    namespace = {"df": data, "np": np, "pd": pd}
    namespace.update(
        (name, getattr(functions, name))
        for name in dir(functions)
        if not name.startswith("_") and callable(getattr(functions, name))
    )
    result = eval(parsed, {"__builtins__": {}}, namespace)  # noqa: S307 - pinned public expressions
    if isinstance(result, pd.DataFrame):
        result = result.iloc[:, 0]
    if not isinstance(result, pd.Series):
        result = pd.Series(result, index=data.index)
    return pd.to_numeric(result.reindex(data.index), errors="coerce").astype("float64")


def rolling(values: pd.Series, window: int, method: str) -> pd.Series:
    return values.groupby(level="instrument", sort=False).transform(
        lambda x: getattr(x.rolling(window, min_periods=1), method)()
    )


def alpha158_20_features(data: pd.DataFrame) -> pd.DataFrame:
    close, opening = data["$close"], data["$open"]
    high, low, volume = data["$high"], data["$low"], data["$volume"]
    prior = {window: close.groupby(level="instrument", sort=False).shift(window) for window in (1, 5, 10, 20)}
    mean_volume = {window: rolling(volume, window, "mean") for window in (5, 10)}
    mean_close = {window: rolling(close, window, "mean") for window in (5, 10, 20)}
    std_close = {window: rolling(close, window, "std") for window in (5, 10)}
    std_volume_5 = rolling(volume, 5, "std")
    returns = close / prior[1] - 1.0
    result = pd.DataFrame(index=data.index)
    result["ROC0"] = (close - opening) / opening
    result["ROC1"] = close / prior[1] - 1.0
    result["ROC5"] = (close - prior[5]) / prior[5]
    result["ROC10"] = (close - prior[10]) / prior[10]
    result["ROC20"] = (close - prior[20]) / prior[20]
    result["VRATIO5"] = volume / mean_volume[5]
    result["VRATIO10"] = volume / mean_volume[10]
    result["VSTD5_RATIO"] = std_volume_5 / mean_volume[5]
    result["RANGE"] = (high - low) / opening
    result["VOLATILITY5"] = std_close[5] / close
    result["VOLATILITY10"] = std_close[10] / close
    result["RET_VOL5"] = rolling(returns, 5, "std")
    low5, low10 = rolling(low, 5, "min"), rolling(low, 10, "min")
    high5, high10 = rolling(high, 5, "max"), rolling(high, 10, "max")
    result["RSV5"] = (close - low5) / (high5 - low5 + 1e-12)
    result["RSV10"] = (close - low10) / (high10 - low10 + 1e-12)
    result["HIGH_RATIO5"] = close / high5 - 1.0
    result["LOW_RATIO5"] = close / low5 - 1.0
    result["SHADOW_RATIO"] = (high - close) / (close - low + 1e-12)
    result["BODY_RATIO"] = (close - opening) / (high - low + 1e-12)
    result["MA_RATIO5_10"] = mean_close[5] / mean_close[10] - 1.0
    result["MA_RATIO10_20"] = mean_close[10] / mean_close[20] - 1.0
    return result[ALPHA158_20_NAMES]


def load_source_factors(factor_path: Path) -> list[dict[str, str]]:
    payload = json.loads(factor_path.read_text())
    rows = []
    for factor_id, item in payload.get("factors", {}).items():
        if item.get("factor_expression"):
            rows.append(
                {
                    "factor_id": factor_id,
                    "factor_name": item.get("factor_name", factor_id),
                    "factor_expression": item["factor_expression"],
                }
            )
    if len(rows) != 150 or len({row["factor_name"] for row in rows}) != 150:
        raise ValueError("expected 150 uniquely named public QuantaAlpha expressions")
    return rows


def load_monthly_panel(path: Path, settings: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    warmup = pd.Timestamp(settings["formation_start"]) - pd.offsets.MonthEnd(260)
    end = pd.Timestamp(settings["realized_return_end"])
    raw = pd.read_parquet(path, columns=INPUT_COLUMNS, filters=[("eom", ">=", warmup), ("eom", "<=", end)])
    raw["datetime"] = pd.to_datetime(raw.eom) + pd.offsets.MonthEnd(0)
    raw = raw.sort_values(["id", "datetime"], kind="stable")
    next_month = raw.groupby("id", sort=False).datetime.shift(-1)
    raw["ret_total_lead1m"] = raw.groupby("id", sort=False).ret.shift(-1)
    consecutive = next_month.eq(raw.datetime + pd.offsets.MonthEnd(1))
    raw.loc[~consecutive, "ret_total_lead1m"] = np.nan
    raw["me"] = pd.to_numeric(raw.me, errors="coerce")
    eligible = raw.me.gt(0) & raw.id.notna()
    ranks = raw.loc[eligible].groupby("datetime", sort=False).me.rank(method="first", ascending=False)
    keep = pd.Series(False, index=raw.index)
    keep.loc[ranks.index] = ranks.le(settings["top_n_by_formation_market_equity"])
    raw = raw.loc[keep].copy()
    raw = raw.sort_values(["datetime", "id"], kind="stable")
    index = pd.MultiIndex.from_frame(
        raw[["datetime", "id"]].rename(columns={"id": "instrument"}),
        names=["datetime", "instrument"],
    )
    raw.index = index
    bars = monthly_bars(raw)
    metadata = raw[["permno", "me", "ret_exc_lead1m", "ret_total_lead1m"]].copy()
    metadata["month"] = metadata.index.get_level_values("datetime")
    metadata["security_id"] = metadata.index.get_level_values("instrument")
    return bars, metadata


def compute_factor_panel(
    bars: pd.DataFrame, metadata: pd.DataFrame, factors: list[dict[str, str]], source_root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    parser, functions = install_author_factor_modules(source_root)
    formation_start = pd.Timestamp(metadata.attrs["formation_start"])
    formation_mask = metadata.month.ge(formation_start).to_numpy()
    target_index = metadata.index[formation_mask]
    values: dict[str, np.ndarray] = {}
    coverage_rows = []
    for number, row in enumerate(factors, start=1):
        result = evaluate_expression(row["factor_expression"], bars, parser, functions)
        selected = result.to_numpy()[formation_mask]
        values[row["factor_name"]] = selected
        coverage_rows.append(
            {
                "factor_name": row["factor_name"],
                "factor_id": row["factor_id"],
                "finite_rows": int(np.isfinite(selected).sum()),
                "rows": len(selected),
                "finite_fraction": float(np.isfinite(selected).mean()),
            }
        )
        if number == 1 or number % 10 == 0:
            print(f"custom_factor_progress={number}/150", flush=True)
    seeds = alpha158_20_features(bars).loc[target_index]
    custom = pd.DataFrame(values, index=target_index)
    features = pd.concat([custom, seeds], axis=1)
    if features.shape[1] != 170 or features.columns.duplicated().any():
        raise ValueError("complete QuantaAlpha source profile must contain 170 unique features")
    coverage_rows.extend(
        {
            "factor_name": name,
            "factor_id": f"alpha158_20::{name}",
            "finite_rows": int(np.isfinite(seeds[name]).sum()),
            "rows": len(seeds),
            "finite_fraction": float(np.isfinite(seeds[name]).mean()),
        }
        for name in ALPHA158_20_NAMES
    )
    return features, pd.DataFrame(coverage_rows)


def fit_fixed_lightgbm(
    features: pd.DataFrame, label: pd.Series, formation_months: list[pd.Timestamp]
) -> tuple[pd.Series, dict[str, Any]]:
    import lightgbm as lgb

    normalized = source_cs_rank_norm(features)
    normalized_label = label_cs_rank_norm(label)
    train_months, valid_months = formation_months[:60], formation_months[60:72]
    test_months = formation_months[72:]
    dates = normalized.index.get_level_values("datetime")
    train = dates.isin(train_months) & normalized_label.notna().to_numpy()
    valid = dates.isin(valid_months) & normalized_label.notna().to_numpy()
    test = dates.isin(test_months)
    if train.sum() < 30000 or valid.sum() < 6000 or test.sum() < 100000:
        raise ValueError("unexpected monthly train/validation/test coverage")
    dtrain = lgb.Dataset(normalized.to_numpy()[train], label=normalized_label.to_numpy()[train])
    dvalid = lgb.Dataset(normalized.to_numpy()[valid], label=normalized_label.to_numpy()[valid])
    evaluations: dict[str, Any] = {}
    model = lgb.train(
        MODEL_PARAMETERS,
        dtrain,
        num_boost_round=500,
        valid_sets=[dtrain, dvalid],
        valid_names=["train", "valid"],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(25), lgb.record_evaluation(evaluations)],
    )
    score = pd.Series(np.nan, index=features.index, dtype="float64")
    score.iloc[np.flatnonzero(test)] = model.predict(normalized.to_numpy()[test], num_iteration=model.best_iteration)
    evidence = {
        "train_start": str(train_months[0].date()),
        "train_end": str(train_months[-1].date()),
        "train_months": len(train_months),
        "train_rows": int(train.sum()),
        "validation_start": str(valid_months[0].date()),
        "validation_end": str(valid_months[-1].date()),
        "validation_months": len(valid_months),
        "validation_rows": int(valid.sum()),
        "test_start": str(test_months[0].date()),
        "test_end": str(test_months[-1].date()),
        "test_months": len(test_months),
        "test_rows": int(test.sum()),
        "feature_count": features.shape[1],
        "best_iteration": int(model.best_iteration),
        "best_score": model.best_score,
        "parameters": {**MODEL_PARAMETERS, "num_boost_round": 500, "early_stopping_rounds": 50},
        "evaluation_history": evaluations,
    }
    return score, evidence


def topk_dropout_trade(
    positions: dict[str, float], cash: float, scores: dict[str, float], *, topk: int, n_drop: int,
) -> tuple[dict[str, float], float, list[str], list[str]]:
    """Replicate Qlib's default top-buy/bottom-sell set transition and cash allocation."""
    def order_key(name: str) -> tuple[float, str]:
        value = scores.get(name, np.nan)
        return (-(value if np.isfinite(value) else -np.inf), name)
    current = sorted(positions, key=order_key)
    candidates = sorted((name for name, value in scores.items() if np.isfinite(value) and name not in positions), key=order_key)
    today = candidates[: max(0, n_drop + topk - len(current))]
    combined = sorted(set(current).union(today), key=order_key)
    bottom = set(combined[-n_drop:]) if n_drop else set()
    sold = [name for name in current if name in bottom]
    buy_count = len(sold) + topk - len(current)
    bought = today[: max(0, buy_count)]
    updated = dict(positions)
    sale_value = sum(updated.pop(name) for name in sold)
    available = cash + sale_value
    purchase_value = available if bought else 0.0
    if bought:
        each = available / len(bought)
        updated.update((name, each) for name in bought)
    traded = sale_value + purchase_value
    return updated, float(traded), bought, sold


def build_topk_path(
    formed: pd.DataFrame, benchmark: pd.DataFrame, *, policy: str, active_start: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if policy not in {"zero", "adverse_100"}:
        raise ValueError(policy)
    market = benchmark.set_index("month")["capm_top1000_mkt"]
    positions: dict[str, float] = {}
    cash = 1.0
    rows, holdings = [], []
    for formation_month, frame in formed.groupby("month", sort=True):
        realized_month = pd.Timestamp(formation_month) + pd.offsets.MonthEnd(1)
        if formation_month < active_start:
            rows.append(
                {
                    "month": realized_month, "formation_month": formation_month,
                    "gross_return": 0.0, "portfolio_excess_return": 0.0,
                    "benchmark_excess_return": float(market.loc[realized_month]),
                    "traded_notional": 0.0, "formation_universe": len(frame),
                    "finite_signal_count": int(np.isfinite(frame.score).sum()), "n_holdings": 0,
                    "n_bought": 0, "n_sold": 0, "gross_exposure": 0.0,
                    "missing_forward_return_gross_weight": 0.0,
                    "missing_total_return_gross_weight": 0.0,
                    "path_status": "training_or_validation_cash",
                }
            )
            continue
        score_map = frame.set_index("security_id").score.to_dict()
        positions, traded, bought, sold = topk_dropout_trade(
            positions, cash, score_map, topk=50, n_drop=5
        )
        cash = 0.0 if bought else cash
        if len(positions) != 50 or not np.isclose(sum(positions.values()) + cash, 1.0, atol=1e-10):
            raise ValueError(f"invalid TopkDropout book at {formation_month}")
        returns = frame.set_index("security_id")[["ret_exc_lead1m", "ret_total_lead1m"]]
        portfolio_excess = 0.0
        portfolio_total = 0.0
        missing_excess = 0.0
        missing_total = 0.0
        next_values = {}
        for security, weight in positions.items():
            excess = returns.ret_exc_lead1m.get(security, np.nan)
            total = returns.ret_total_lead1m.get(security, np.nan)
            if not np.isfinite(excess):
                missing_excess += weight
                excess = 0.0 if policy == "zero" else -1.0
            if not np.isfinite(total):
                missing_total += weight
                total = 0.0 if policy == "zero" else -1.0
            portfolio_excess += weight * float(excess)
            portfolio_total += weight * float(total)
            next_values[security] = weight * (1.0 + float(total))
            holdings.append(
                {
                    "formation_month": formation_month, "realized_month": realized_month,
                    "security_id": security, "pre_return_weight": weight,
                    "score": score_map.get(security), "missing_excess_return": not np.isfinite(returns.ret_exc_lead1m.get(security, np.nan)),
                    "missing_total_return": not np.isfinite(returns.ret_total_lead1m.get(security, np.nan)),
                    "missing_return_policy": policy,
                }
            )
        nav = cash + sum(next_values.values())
        if not np.isfinite(nav) or nav <= 0:
            raise ValueError(f"nonpositive TopkDropout NAV at {formation_month} under {policy}")
        positions = {name: value / nav for name, value in next_values.items() if value > 1e-15}
        cash /= nav
        benchmark_return = float(market.loc[realized_month])
        rows.append(
            {
                "month": realized_month, "formation_month": formation_month,
                "gross_return": portfolio_excess - benchmark_return,
                "portfolio_excess_return": portfolio_excess,
                "benchmark_excess_return": benchmark_return,
                "traded_notional": traded, "formation_universe": len(frame),
                "finite_signal_count": int(np.isfinite(frame.score).sum()),
                "n_holdings": len(next_values), "n_bought": len(bought), "n_sold": len(sold),
                "gross_exposure": 1.0, "missing_forward_return_gross_weight": missing_excess,
                "missing_total_return_gross_weight": missing_total, "path_status": "ok",
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(holdings)


def build_metrics(contract: dict, root: Path, paths: dict[str, pd.DataFrame]) -> tuple[list[dict], list[dict]]:
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    factors = pd.read_csv(root / contract["factor_panel_path"], parse_dates=["month"])
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack(
        [paths[policy].gross_return.to_numpy() - cost / 10000 * paths[policy].traded_notional.to_numpy()
         for policy, cost in cases]
    )
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError("incomplete QuantaAlpha partial return path")
    merged = paths["zero"][["month"]].merge(factors, on="month", validate="one_to_one")
    attr = contract["attribution"]
    reconstruction = rolling_crossfit_reconstruction(
        merged[contract["factor_columns"]].to_numpy(float), y, attr["train_months"],
        attr["validation_months"], np.asarray(attr["ridge_lambdas"]), attr["n_unpenalized"],
    )
    eval_dates = paths["zero"].month.iloc[attr["train_months"]:].reset_index(drop=True)
    lags, metrics, residual_rows = automatic_hac_lag(len(eval_dates)), [], []
    for column, ((policy, cost), name) in enumerate(zip(cases, names)):
        net, residual = y[:, column], reconstruction.residuals[:, column]
        alpha, se = float(residual.mean()), float(hac_mean_se(residual, lags))
        t_value, p_value = alpha / se, float(2 * norm.sf(abs(alpha / se)))
        path = paths[policy]
        metrics.append(
            {
                "case": name, "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
                "missing_return_policy": policy, "cost_bps_one_way": cost,
                **{f"full_{key}": value for key, value in return_statistics(net).items()},
                "evaluation_months": len(eval_dates), "evaluation_start": str(eval_dates.iloc[0].date()),
                "evaluation_end": str(eval_dates.iloc[-1].date()),
                "jkp_residual_mean_annualized": 12 * alpha, "jkp_residual_se_annualized": 12 * se,
                "jkp_residual_t_hac": t_value, "jkp_residual_p_two_sided": p_value,
                "exploratory_bonferroni69_p": min(1.0, 69 * p_value), "hac_lags": lags,
                "average_traded_notional": float(path.traded_notional.mean()),
                "annualized_linear_cost_drag": float(12 * cost / 10000 * path.traded_notional.mean()),
                "cash_warmup_months": int(path.path_status.eq("training_or_validation_cash").sum()),
                "scored_months": int(path.path_status.eq("ok").sum()),
                "minimum_active_finite_signal_count": int(path.loc[path.path_status.eq("ok"), "finite_signal_count"].min()),
                "maximum_missing_forward_gross_weight": float(path.missing_forward_return_gross_weight.max()),
            }
        )
        residual_rows.extend(
            {"case": name, "month": str(month.date()), "net_return": float(value),
             "factor_replication_return": float(fitted), "residual": float(remain),
             "selected_lambda": float(lam)}
            for month, value, fitted, remain, lam in zip(
                eval_dates, net[attr["train_months"]:], reconstruction.fitted_values[:, column],
                residual, reconstruction.selected_lambdas[:, column]
            )
        )
    return metrics, residual_rows


def evaluate(root: Path, output: Path, source_root: Path, factor_json: Path) -> None:
    if (output / "run_manifest.json").exists():
        raise ValueError("completed M043 run already exists")
    study = root / "paper_runs/us_jkp_headline"
    contract_path, recipe_path = study / "benchmark_contract.json", output / "recipe.json"
    contract, recipe = json.loads(contract_path.read_text()), json.loads(recipe_path.read_text())
    if contract["status"] != "frozen" or recipe["status"] != "frozen_for_execution":
        raise ValueError("frozen benchmark and recipe required")
    if digest(factor_json) != SOURCE_FACTOR_SHA256 or recipe["release_evidence"]["prepublication_factor_sha256"] != SOURCE_FACTOR_SHA256:
        raise ValueError("QuantaAlpha factor-pool hash mismatch")
    commit = subprocess.check_output(["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(source_root), "status", "--porcelain"], text=True).strip()
    if commit != SOURCE_COMMIT or dirty:
        raise ValueError("author source checkout is not the pinned clean prepublication result commit")
    implementation = [Path(__file__).resolve(), root / "src/alpha_evolve/headline_backtest.py",
                      root / "src/alpha_evolve/submission_analysis.py", root / "scripts/run_broad_jkp_crossfit.py"]
    relative = [str(path.relative_to(root)) for path in implementation]
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *relative], cwd=root, check=True)
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    bars, metadata = load_monthly_panel(Path(contract["data"]["path"]), settings)
    metadata.attrs["formation_start"] = settings["formation_start"]
    factors = load_source_factors(factor_json)
    features, coverage = compute_factor_panel(bars, metadata, factors, source_root)
    formed = metadata.loc[features.index].copy()
    formation_months = [pd.Timestamp(value) for value in sorted(formed.month.unique())]
    if len(formation_months) != 305 or formed.groupby("month").size().min() != 1000:
        raise ValueError("monthly common universe is incomplete")
    label = formed.ret_total_lead1m.astype(float)
    score, model_evidence = fit_fixed_lightgbm(features, label, formation_months)
    formed["score"] = score
    benchmark = pd.read_csv(root / contract["factor_panel_path"], parse_dates=["month"])
    active_start = formation_months[72]
    paths, primary_holdings = {}, None
    for policy in ("zero", "adverse_100"):
        paths[policy], holdings = build_topk_path(formed, benchmark, policy=policy, active_start=active_start)
        if policy == "zero":
            primary_holdings = holdings
    private = root / "artifacts/us_jkp_headline/v1"
    private.mkdir(parents=True, exist_ok=True)
    private_features = private / "M043_formation_factor_panel.parquet"
    private_holdings_path = private / "M043_formation_holdings.parquet"
    features.to_parquet(private_features)
    assert primary_holdings is not None
    primary_holdings.to_parquet(private_holdings_path, index=False)
    metrics, residual_rows = build_metrics(contract, root, paths)
    output.mkdir(parents=True, exist_ok=True)
    pd.concat([frame.assign(missing_return_policy=policy) for policy, frame in paths.items()]).to_csv(
        output / "monthly_returns.csv", index=False
    )
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    coverage.to_csv(output / "feature_coverage.csv", index=False)
    (output / "model_training.json").write_text(json.dumps(model_evidence, indent=2, allow_nan=False) + "\n")
    primary = next(row for row in metrics if row["primary"])
    primary_path = paths["zero"].copy()
    primary_path["net_return"] = primary_path.gross_return - 0.001 * primary_path.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    report = f'''# M043: QuantaAlpha historical complete GPT pool on monthly U.S./JKP data

Status: **completed central partial adaptation**, not a reproduction of the v3 GPT-5.2 headline run.

The paper's central strategy is a LightGBM synthesis of roughly 150 evolved factors with a Top-50/drop-5 portfolio, rather than one cherry-picked expression. The strongest executable author-attributed artifact is an earlier 150-expression GPT pool which the released profile combines with Alpha158(20), for 170 features. All expressions and source signs are retained; no factor was selected using this JKP outcome. The v3 pool is not released, so this is necessarily a historical-pool partial.

The fixed monthly adaptation retains every source lookback count as monthly observations, maps JKP OHLCV fields as recorded in `recipe.json`, trains the released LightGBM configuration once on the first 60 formation months with the next 12 months used only for early stopping, and applies the source TopkDropout mechanism thereafter. The first 72 months are explicit cash warmup. Primary returns are the long-only portfolio's excess return over the common JKP top-1,000 market, net of the common 10 bp one-way linear cost.

At 10 bp one-way costs, the 305-month path has CAGR {primary['full_cagr']:.2%}, annualized Sharpe {primary['full_annualized_sharpe']:.3f}, and maximum drawdown {primary['full_maximum_drawdown']:.2%}. There are {primary['scored_months']} scored out-of-sample months after {primary['cash_warmup_months']} cash months. The 185-month rolling JKP133 residual mean is {primary['jkp_residual_mean_annualized']:.2%} annually (HAC t={primary['jkp_residual_t_hac']:.3f}, p={primary['jkp_residual_p_two_sided']:.4f}; descriptive 69-test bound={primary['exploratory_bonferroni69_p']:.4f}).

This directly answers option **B** for the implemented historical pool if its transferred return is weak: the source formulas/model/portfolio were run, but that does not make the unavailable v3 claim true or false. The native CSI300 rerun already produces 3.61% ARR rather than the older 27.75% claim, while v3 silently changes the headline to 4.68% without releasing its pool. The monthly U.S. result therefore evaluates transfer of the strongest released central partial, not the unreleased current headline.

Monthly bars cannot preserve next-day opening execution or Chinese price limits. The opening field is a prior-close-implied proxy, periods change from days to months, the primary common cost is symmetric rather than the paper's 5/15 bp schedule, and prior project outcomes were known. Results are exploratory and were not used to revise the frozen recipe.
'''
    (output / "verdict.md").write_text(report)
    public_names = ["monthly_returns.csv", "primary_monthly_returns.csv", "metrics.csv",
                    "attribution_residuals.csv", "feature_coverage.csv", "model_training.json", "verdict.md"]
    manifest = {
        "status": "evaluated_partial", "milestone_id": "M043", "candidate_id": recipe["candidate_id"],
        "benchmark_id": contract["benchmark_id"], "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "contract_sha256": digest(contract_path), "recipe_sha256": digest(recipe_path),
        "source_factor_sha256": digest(factor_json), "source_commit": commit,
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                    "platform": platform.system()},
        "primary_result": primary, "model": {key: value for key, value in model_evidence.items() if key != "evaluation_history"},
        "private_factor_panel_path": str(private_features), "private_factor_panel_sha256": digest(private_features),
        "private_holdings_path": str(private_holdings_path), "private_holdings_sha256": digest(private_holdings_path),
        "prior_jkp_outcomes_seen": True, "confirmatory_claim": False,
        "implementation_sha256": {str(path.relative_to(root)): digest(path) for path in implementation},
        "output_sha256": {name: digest(output / name) for name in public_names},
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps(primary, indent=2), flush=True)


def main() -> None:
    default_source = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_recovery/source_8a0343")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("paper_runs/us_jkp_headline/M043_quantaalpha"))
    parser.add_argument("--source-root", type=Path, default=default_source)
    parser.add_argument("--factor-json", type=Path, default=default_source / SOURCE_FACTOR_PATH)
    args = parser.parse_args()
    os.umask(0o077)
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    private = root / "artifacts/us_jkp_headline/v1"
    private.mkdir(parents=True, exist_ok=True)
    with (private / "operation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status_path = private / "operation.json"
        status = {
            "state": "running", "phase": "factor_pool_evaluation", "milestone_id": "M043",
            "pid": os.getpid(), "hostname": socket.gethostname(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        }
        write_json(status_path, status)
        try:
            evaluate(root, output.resolve(), args.source_root.resolve(), args.factor_json.resolve())
        except BaseException as error:
            status.update(
                state="failed", finished_at_utc=datetime.now(timezone.utc).isoformat(),
                error_type=type(error).__name__, error=str(error),
            )
            write_json(status_path, status)
            raise
        status.update(state="complete", finished_at_utc=datetime.now(timezone.utc).isoformat())
        write_json(status_path, status)


if __name__ == "__main__":
    main()
