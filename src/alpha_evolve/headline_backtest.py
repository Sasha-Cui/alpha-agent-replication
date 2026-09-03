"""Point-in-time formation and common accounting for the headline study."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .headline_strategies import gpt_signal_evc, gpt_signal_evc_trading_score
from .submission_analysis import (
    drift_weights, missing_return_gross_weight, realized_portfolio_return,
    target_weights, traded_notional, weight_diagnostics,
)


def formation_universe(raw: pd.DataFrame, start: str, end: str, top_n: int) -> pd.DataFrame:
    """Keep formation eligibility independent of future observations/returns."""
    frame = raw.rename(columns={"id": "security_id", "me": "weight"}).copy()
    frame["month"] = pd.to_datetime(frame["eom"]) + pd.offsets.MonthEnd(0)
    for name in ("weight", "ret", "ret_exc_lead1m"):
        frame[name] = pd.to_numeric(frame[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
    frame = frame.sort_values(["security_id", "month"], kind="mergesort")
    if frame.duplicated(["security_id", "month"]).any():
        raise ValueError("duplicate security-month observations")
    next_month = frame.groupby("security_id")["month"].shift(-1)
    frame["ret_total_lead1m"] = frame.groupby("security_id")["ret"].shift(-1)
    frame.loc[next_month.ne(frame["month"] + pd.offsets.MonthEnd(1)), "ret_total_lead1m"] = np.nan
    frame = frame.loc[frame["month"].between(pd.Timestamp(start), pd.Timestamp(end))]
    frame = frame.dropna(subset=["security_id", "month", "weight"])
    frame = frame.loc[frame["weight"] > 0].copy()
    # Match the corrected evaluator: sort by ID before deterministic size ties.
    rank = frame.groupby("month")["weight"].rank(method="first", ascending=False)
    return frame.loc[rank <= top_n].reset_index(drop=True)


def load_formations(path: Path, feature_columns: list[str], settings: dict) -> pd.DataFrame:
    metadata = ["id", "permno", "eom", "me", "ret", "ret_exc_lead1m"]
    source = pq.ParquetFile(path)
    required = set(metadata + feature_columns)
    if not required.issubset(source.schema.names):
        raise ValueError(f"missing input columns: {sorted(required - set(source.schema.names))}")
    thin = pd.read_parquet(path, columns=metadata)
    formed = formation_universe(thin, settings["formation_start"], settings["formation_end"],
                                settings["top_n_by_formation_market_equity"])
    del thin
    wanted = pd.MultiIndex.from_frame(formed[["security_id", "month"]])
    feature_parts = []
    for batch in source.iter_batches(batch_size=100_000, columns=["id", "eom", *feature_columns]):
        part = batch.to_pandas().rename(columns={"id": "security_id"})
        part["month"] = pd.to_datetime(part["eom"]) + pd.offsets.MonthEnd(0)
        selected = pd.MultiIndex.from_frame(part[["security_id", "month"]]).isin(wanted)
        if selected.any():
            feature_parts.append(part.loc[selected, ["security_id", "month", *feature_columns]])
    features = pd.concat(feature_parts, ignore_index=True)
    return formed.merge(features, on=["security_id", "month"], validate="one_to_one", how="left")


def evc_jkp_score(features: pd.DataFrame) -> pd.Series:
    """Documented JKP financial-ratio adaptation; no return column is consumed."""
    inputs = features[["ni_at", "ebitda_mev", "ocf_me"]].astype("float64")
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        evc = gpt_signal_evc(inputs["ni_at"], 1.0 / inputs["ebitda_mev"], 1.0 / inputs["ocf_me"])
    return gpt_signal_evc_trading_score(evc)


def score_weights(frame: pd.DataFrame, score_column: str, settings: dict) -> pd.Series:
    return target_weights(frame, score_column, "long_short_value_weighted_deciles",
                          quantile=settings["quantile"], min_side=settings["min_side"])


def build_factor_panel(formed: pd.DataFrame, characteristics: list[str], settings: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, coverage = [], []
    months = pd.date_range(settings["formation_start"], settings["formation_end"], freq=pd.offsets.MonthEnd())
    groups = {month: part for month, part in formed.groupby("month", sort=True)}
    for number, month in enumerate(months):
        frame = groups[month]
        market_weights = frame.set_index("security_id")["weight"]
        market_weights = market_weights / market_weights.sum()
        row = {"formation_month": month, "month": month + pd.offsets.MonthEnd(1),
               "capm_top1000_mkt": realized_portfolio_return(market_weights, frame)}
        for characteristic in characteristics:
            weights = score_weights(frame, characteristic, settings)
            row[f"char__{characteristic}"] = realized_portfolio_return(weights, frame)
            coverage.append({"formation_month": month, "characteristic": characteristic,
                             "n_available": int(np.isfinite(frame[characteristic]).sum()),
                             "missing_forward_return_gross_weight": missing_return_gross_weight(weights, frame),
                             **weight_diagnostics(weights)})
        rows.append(row)
        if number % 30 == 0:
            print(f"benchmark_months={number + 1}/{len(months)}", flush=True)
    result = pd.DataFrame(rows)
    if not np.isfinite(result[["capm_top1000_mkt", *[f"char__{c}" for c in characteristics]]]).all().all():
        raise ValueError("benchmark lacks complete factor coverage on the fixed calendar")
    return result, pd.DataFrame(coverage)


def build_strategy_path(formed: pd.DataFrame, scores: pd.Series, settings: dict,
                        missing_policy: str = "zero") -> tuple[pd.DataFrame, pd.DataFrame]:
    if not scores.index.equals(formed.index):
        raise ValueError("scores must align with the formation panel")
    scored = formed.assign(_headline_score=scores)
    groups = {month: part for month, part in scored.groupby("month", sort=True)}
    months = pd.date_range(settings["formation_start"], settings["formation_end"], freq=pd.offsets.MonthEnd())
    previous = pd.Series(dtype="float64")
    previous_returns = pd.Series(dtype="float64")
    failed = False
    rows, holdings = [], []
    for month in months:
        frame = groups[month]
        if failed:
            rows.append({"formation_month": month, "month": month + pd.offsets.MonthEnd(1),
                         "path_status": "failed_nonpositive_nav", "gross_return": np.nan})
            continue
        weights = score_weights(frame, "_headline_score", settings)
        pretrade = drift_weights(previous, previous_returns)
        turnover = traded_notional(weights, pretrade)
        gross = realized_portfolio_return(weights, frame, missing_return_policy=missing_policy)
        total = realized_portfolio_return(weights, frame, return_col="ret_total_lead1m")
        failed = bool(np.isfinite(total) and total <= -1.0)
        status = "failed_nonpositive_nav" if failed else "insufficient_formation_coverage" if weights.empty else "ok"
        row = {"formation_month": month, "month": month + pd.offsets.MonthEnd(1),
               "path_status": status, "gross_return": gross, "total_security_return": total,
               "traded_notional": turnover, "formation_universe": len(frame),
               "finite_signal_count": int(np.isfinite(frame["_headline_score"]).sum()),
               "missing_forward_return_gross_weight": missing_return_gross_weight(weights, frame),
               "missing_total_return_gross_weight": missing_return_gross_weight(weights, frame, return_col="ret_total_lead1m"),
               **weight_diagnostics(weights)}
        rows.append(row)
        holdings.extend({"formation_month": month, "month": month + pd.offsets.MonthEnd(1),
                         "security_id": security, "weight": weight} for security, weight in weights.items())
        previous = weights
        previous_returns = frame.set_index("security_id")["ret_total_lead1m"].fillna(0.0)
    return pd.DataFrame(rows), pd.DataFrame(holdings)


def return_statistics(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("incomplete or nonpositive-NAV return path")
    wealth = np.r_[1.0, np.cumprod(1.0 + values)]
    stdev = values.std(ddof=1)
    return {"months": len(values), "arithmetic_annualized_return": float(12 * values.mean()),
            "cagr": float(wealth[-1] ** (12 / len(values)) - 1),
            "cumulative_return": float(wealth[-1] - 1),
            "annualized_volatility": float(stdev * np.sqrt(12)),
            "annualized_sharpe": float(np.sqrt(12) * values.mean() / stdev) if stdev > 0 else None,
            "maximum_drawdown": float(np.min(wealth / np.maximum.accumulate(wealth) - 1))}
