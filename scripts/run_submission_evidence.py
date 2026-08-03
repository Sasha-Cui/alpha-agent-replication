#!/usr/bin/env python3
"""Build the frozen geographic-validation and cost evidence for the paper.

The script deliberately imports the already-defined proxy formulas without
modifying them.  It forms the same portfolios independently within each market,
records signed weights and turnover diagnostics, pools country sleeves, and
performs the pre-specified FF5+Mom inference.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import run_paper_idea_jkp_proxies as proxy
from alpha_evolve.paths import DEFAULT_JKP_ROOT
from alpha_evolve.submission_analysis import (
    alpha_regression,
    drift_weights,
    missing_return_gross_weight,
    multiplicity_adjustments,
    paired_block_bootstrap_alpha,
    realized_portfolio_return,
    target_weights,
    traded_notional,
    weight_diagnostics,
)


DEFAULT_MARKETS = ["CAN", "FRA", "DEU", "ITA", "JPN", "GBR"]
CONTEST_ID = "contesttrade_internal_contest_trailing_sharpe"
FACTOR_COLS = ["jkp_topn_mkt", *[f"char__{name}" for name in proxy.BENCHMARK_COLS]]
COSTS_BPS = [0, 5, 10, 25, 50]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lock(
    path: Path,
    required_files: list[Path],
    required_data_files: dict[str, Path],
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"analysis lock missing: {path}")
    lock = json.loads(path.read_text())
    expected = lock.get("file_sha256", {})
    failures = []
    required_rel = {str(file_path.relative_to(REPO_ROOT)) for file_path in required_files}
    if not required_rel.issubset(expected):
        raise RuntimeError(f"analysis lock omits required files: {sorted(required_rel - set(expected))}")
    for rel, expected_hash in expected.items():
        file_path = REPO_ROOT / rel
        if not file_path.exists():
            failures.append((rel, expected_hash, "missing"))
            continue
        observed = sha256_file(file_path)
        if expected_hash != observed:
            failures.append((rel, expected_hash, observed))
    if failures:
        raise RuntimeError(f"analysis lock mismatch: {failures}")
    expected_data = lock.get("data_inputs", {})
    data_failures = []
    for market, file_path in required_data_files.items():
        expected_row = expected_data.get(market, {})
        print(f"verifying frozen data input {market}: {file_path}", flush=True)
        observed_size = file_path.stat().st_size
        observed_hash = sha256_file(file_path)
        if (
            expected_row.get("path") != str(file_path)
            or expected_row.get("bytes") != observed_size
            or expected_row.get("sha256") != observed_hash
        ):
            data_failures.append(
                {
                    "market": market,
                    "expected": expected_row,
                    "observed": {
                        "path": str(file_path),
                        "bytes": observed_size,
                        "sha256": observed_hash,
                    },
                }
            )
    if data_failures:
        raise RuntimeError(f"frozen data input mismatch: {data_failures}")
    return lock


def market_path(market: str) -> Path:
    return DEFAULT_JKP_ROOT / "data" / "processed" / "characteristics" / f"{market}.parquet"


def load_market_panel(
    market: str,
    *,
    start: str,
    end: str,
    top_n: int,
) -> pd.DataFrame:
    path = market_path(market)
    columns = ["ret", *["id" if col == "permno" else col for col in proxy.BASE_COLS]]
    columns = list(dict.fromkeys(columns))
    raw = pd.read_parquet(path, columns=columns)
    raw = raw.rename(columns={"id": "security_id", "me": "weight"})
    raw["month"] = pd.to_datetime(raw["eom"], errors="coerce") + pd.offsets.MonthEnd(0)
    raw["ret_exc_lead1m"] = pd.to_numeric(raw["ret_exc_lead1m"], errors="coerce")
    raw["ret"] = pd.to_numeric(raw["ret"], errors="coerce")
    raw["weight"] = pd.to_numeric(raw["weight"], errors="coerce")
    raw = raw.sort_values(["security_id", "month"])
    if raw.duplicated(["security_id", "month"]).any():
        raise ValueError(f"duplicate security-month rows in {path}")
    raw["_next_observation_month"] = raw.groupby("security_id")["month"].shift(-1)
    raw["ret_total_lead1m"] = raw.groupby("security_id")["ret"].shift(-1)
    consecutive = raw["_next_observation_month"] == raw["month"] + pd.offsets.MonthEnd(1)
    raw.loc[~consecutive, "ret_total_lead1m"] = np.nan
    raw = raw.drop(columns="_next_observation_month")
    raw = raw[(raw["month"] >= pd.Timestamp(start)) & (raw["month"] <= pd.Timestamp(end))].copy()
    raw = raw.replace([np.inf, -np.inf], np.nan)
    # Formation eligibility must not depend on the next-month outcome. Missing
    # realized returns are handled by the frozen zero-return policy downstream.
    raw = raw.dropna(subset=["month", "security_id", "weight"])
    raw = raw[raw["weight"] > 0]
    if top_n > 0:
        raw["_size_rank"] = raw.groupby("month")["weight"].rank(method="first", ascending=False)
        raw = raw[raw["_size_rank"] <= top_n].drop(columns="_size_rank")
    return raw


def _returns_by_security(frame: pd.DataFrame, return_col: str) -> pd.Series:
    return (
        frame[["security_id", return_col]]
        .drop_duplicates("security_id", keep="last")
        .set_index("security_id")[return_col]
        .astype("float64")
        .fillna(0.0)
    )


def formation_value_weighted_return(
    frame: pd.DataFrame, missing_return_policy: str
) -> tuple[float, float]:
    """Top-N market return and missing-return exposure using ex-ante weights."""
    x = (
        frame[["security_id", "weight"]]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .drop_duplicates("security_id", keep="last")
        .set_index("security_id")["weight"]
        .astype("float64")
    )
    x = x[x > 0]
    if x.empty:
        return float("nan"), float("nan")
    weights = x / x.sum()
    return (
        realized_portfolio_return(
            weights, frame, missing_return_policy=missing_return_policy
        ),
        missing_return_gross_weight(weights, frame),
    )


def build_one_market(
    market: str,
    *,
    start: str,
    end: str,
    top_n: int,
    quantile: float,
    min_side: int,
    missing_return_policy: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = load_market_panel(market, start=start, end=end, top_n=top_n)
    months = sorted(pd.to_datetime(raw["month"].dropna().unique()))
    candidate_ids = list(proxy.IDEA_DEFINITIONS)
    sleeve_history = {candidate: [] for candidate in candidate_ids}
    previous_targets: dict[str, pd.Series] = {
        candidate: pd.Series(dtype="float64") for candidate in [*candidate_ids, CONTEST_ID]
    }
    previous_total_returns = pd.Series(dtype="float64")
    path_failures: dict[str, dict[str, Any]] = {}
    candidate_rows: list[dict[str, Any]] = []
    factor_rows: list[dict[str, Any]] = []

    for month_index, month in enumerate(months):
        frame = raw[raw["month"] == month].copy()
        scored = proxy.build_scores_for_month(frame)
        return_month = pd.Timestamp(month) + pd.offsets.MonthEnd(1)
        current_total_returns = _returns_by_security(scored, "ret_total_lead1m")
        current_targets: dict[str, pd.Series] = {}
        current_candidate_returns: dict[str, float] = {}
        failed_before_month = set(path_failures)

        for candidate in candidate_ids:
            meta = proxy.IDEA_DEFINITIONS[candidate]
            if candidate in failed_before_month:
                empty = pd.Series(dtype="float64")
                current_targets[candidate] = empty
                current_candidate_returns[candidate] = float("nan")
                failure = path_failures[candidate]
                candidate_rows.append(
                    {
                        "market": market,
                        "formation_month": pd.Timestamp(month),
                        "month": return_month,
                        "candidate_id": candidate,
                        "gross_return": float("nan"),
                        "traded_notional": float("nan"),
                        "observed_gross_return": float("nan"),
                        "observed_traded_notional": float("nan"),
                        "selected_sleeve": "",
                        "analysis_eligible": False,
                        "path_failure_event": False,
                        "path_status": "failed_bankruptcy_nonpositive_nav",
                        "failure_month": failure["failure_month"],
                        "failure_total_return": failure["failure_total_return"],
                        "missing_excess_return_gross_weight": float("nan"),
                        "missing_total_return_gross_weight": float("nan"),
                        **weight_diagnostics(empty),
                    }
                )
                continue
            weights = target_weights(
                scored,
                candidate,
                str(meta["strategy"]),
                quantile=quantile,
                min_side=min_side,
            )
            current_targets[candidate] = weights
            candidate_return = realized_portfolio_return(
                weights, scored, missing_return_policy=missing_return_policy
            )
            current_candidate_returns[candidate] = candidate_return
            pretrade = drift_weights(previous_targets[candidate], previous_total_returns)
            turnover = traded_notional(weights, pretrade)
            total_return = realized_portfolio_return(
                weights,
                scored,
                return_col="ret_total_lead1m",
                missing_return_policy="zero",
            )
            failure_event = bool(np.isfinite(total_return) and 1.0 + total_return <= 0.0)
            if failure_event:
                path_failures[candidate] = {
                    "failure_month": return_month,
                    "failure_total_return": float(total_return),
                }
            diagnostics = weight_diagnostics(weights)
            candidate_rows.append(
                {
                    "market": market,
                    "formation_month": pd.Timestamp(month),
                    "month": return_month,
                    "candidate_id": candidate,
                    "gross_return": float("nan") if failure_event else candidate_return,
                    "traded_notional": float("nan") if failure_event else turnover,
                    "observed_gross_return": candidate_return,
                    "observed_traded_notional": turnover,
                    "selected_sleeve": "",
                    "analysis_eligible": not failure_event,
                    "path_failure_event": failure_event,
                    "path_status": (
                        "failed_bankruptcy_nonpositive_nav" if failure_event else "ok"
                    ),
                    "failure_month": return_month if failure_event else pd.NaT,
                    "failure_total_return": total_return if failure_event else float("nan"),
                    "missing_excess_return_gross_weight": missing_return_gross_weight(
                        weights, scored, return_col="ret_exc_lead1m"
                    ),
                    "missing_total_return_gross_weight": missing_return_gross_weight(
                        weights, scored, return_col="ret_total_lead1m"
                    ),
                    **diagnostics,
                }
            )

        eligible_sleeves = [
            candidate
            for candidate, meta in proxy.IDEA_DEFINITIONS.items()
            if meta["strategy"] != "long_only_top5_equal_weighted"
            and candidate not in failed_before_month
        ]
        selected = ""
        if CONTEST_ID not in failed_before_month and month_index >= 24:
            trailing = {}
            for candidate in eligible_sleeves:
                history = pd.Series(sleeve_history[candidate][-36:], dtype="float64").dropna()
                if len(history) >= 24 and history.std(ddof=1) > 0:
                    trailing[candidate] = float(np.sqrt(12.0) * history.mean() / history.std(ddof=1))
            if trailing:
                selected = max(trailing, key=trailing.get)
        contest_weights = current_targets.get(selected, pd.Series(dtype="float64"))
        contest_return = current_candidate_returns.get(selected, float("nan"))
        if CONTEST_ID in failed_before_month:
            contest_weights = pd.Series(dtype="float64")
            contest_return = float("nan")
            contest_turnover = float("nan")
            contest_total_return = float("nan")
            contest_failure_event = False
        else:
            contest_pretrade = drift_weights(
                previous_targets[CONTEST_ID], previous_total_returns
            )
            contest_turnover = traded_notional(contest_weights, contest_pretrade)
            contest_total_return = realized_portfolio_return(
                contest_weights,
                scored,
                return_col="ret_total_lead1m",
                missing_return_policy="zero",
            )
            contest_failure_event = bool(
                np.isfinite(contest_total_return)
                and 1.0 + contest_total_return <= 0.0
            )
            if contest_failure_event:
                path_failures[CONTEST_ID] = {
                    "failure_month": return_month,
                    "failure_total_return": float(contest_total_return),
                }
        contest_failure = path_failures.get(CONTEST_ID)
        candidate_rows.append(
            {
                "market": market,
                "formation_month": pd.Timestamp(month),
                "month": return_month,
                "candidate_id": CONTEST_ID,
                "gross_return": (
                    float("nan")
                    if CONTEST_ID in path_failures
                    else contest_return
                ),
                "traded_notional": (
                    float("nan")
                    if CONTEST_ID in path_failures
                    else contest_turnover
                ),
                "observed_gross_return": contest_return,
                "observed_traded_notional": contest_turnover,
                "selected_sleeve": selected or "insufficient_history",
                "analysis_eligible": CONTEST_ID not in path_failures,
                "path_failure_event": contest_failure_event,
                "path_status": (
                    "failed_bankruptcy_nonpositive_nav"
                    if CONTEST_ID in path_failures
                    else "ok"
                ),
                "failure_month": (
                    contest_failure["failure_month"] if contest_failure else pd.NaT
                ),
                "failure_total_return": (
                    contest_failure["failure_total_return"]
                    if contest_failure
                    else float("nan")
                ),
                "missing_excess_return_gross_weight": missing_return_gross_weight(
                    contest_weights, scored, return_col="ret_exc_lead1m"
                ),
                "missing_total_return_gross_weight": missing_return_gross_weight(
                    contest_weights, scored, return_col="ret_total_lead1m"
                ),
                **weight_diagnostics(contest_weights),
            }
        )
        current_targets[CONTEST_ID] = contest_weights

        market_return, market_missing = formation_value_weighted_return(
            scored, missing_return_policy
        )
        factor_row: dict[str, Any] = {
            "market": market,
            "formation_month": pd.Timestamp(month),
            "month": return_month,
            "n_stocks": int(scored["security_id"].nunique()),
            "market_cap_sum": float(scored["weight"].sum()),
            "jkp_topn_mkt": market_return,
            "jkp_topn_mkt_missing_excess_return_gross_weight": market_missing,
            "jkp_topn_mkt_missing_total_return_gross_weight": missing_return_gross_weight(
                (
                    scored.dropna(subset=["security_id", "weight"])
                    .drop_duplicates("security_id", keep="last")
                    .set_index("security_id")["weight"]
                    .pipe(lambda values: values[values > 0] / values[values > 0].sum())
                ),
                scored,
                return_col="ret_total_lead1m",
            ),
        }
        for factor in proxy.BENCHMARK_COLS:
            factor_weights = target_weights(
                scored,
                factor,
                "long_short_decile_value_weighted",
                quantile=quantile,
                min_side=min_side,
            )
            factor_row[f"char__{factor}"] = realized_portfolio_return(
                factor_weights,
                scored,
                missing_return_policy=missing_return_policy,
            )
            factor_row[f"char__{factor}__missing_excess_return_gross_weight"] = (
                missing_return_gross_weight(
                    factor_weights, scored, return_col="ret_exc_lead1m"
                )
            )
            factor_row[f"char__{factor}__missing_total_return_gross_weight"] = (
                missing_return_gross_weight(
                    factor_weights, scored, return_col="ret_total_lead1m"
                )
            )
        factor_rows.append(factor_row)

        for candidate in candidate_ids:
            sleeve_history[candidate].append(current_candidate_returns[candidate])
        previous_targets = current_targets
        previous_total_returns = current_total_returns

    del raw
    gc.collect()
    candidate_frame = pd.DataFrame(candidate_rows)
    # Limited liability is enforced at the complete strategy-path level.  A
    # sleeve that ever reaches nonpositive NAV is an implementation failure,
    # not a return series that can be restarted or silently recapitalized.
    for candidate, failure in path_failures.items():
        failed = candidate_frame["candidate_id"] == candidate
        candidate_frame.loc[failed, ["gross_return", "traded_notional"]] = np.nan
        candidate_frame.loc[failed, "analysis_eligible"] = False
        candidate_frame.loc[failed, "path_status"] = "failed_bankruptcy_nonpositive_nav"
        candidate_frame.loc[failed, "failure_month"] = failure["failure_month"]
        candidate_frame.loc[failed, "failure_total_return"] = failure["failure_total_return"]
    return candidate_frame, pd.DataFrame(factor_rows)


def pool_country_sleeves(
    candidate_monthly: pd.DataFrame,
    factor_monthly: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pool an identical market set for every executable family member.

    A candidate that breaches limited liability in any included market remains
    in the planned family but its entire pooled path is unavailable.  It is
    consequently assigned ``p=1`` downstream instead of determining the
    common calendar for the candidates whose paths remain executable.
    """
    candidate_monthly = candidate_monthly.copy()
    if "path_failure_event" not in candidate_monthly:
        candidate_monthly["path_failure_event"] = False
    candidate_monthly["path_failure_event"] = candidate_monthly[
        "path_failure_event"
    ].fillna(False).astype(bool)
    failed_candidates = set(
        candidate_monthly.loc[
            candidate_monthly["path_failure_event"], "candidate_id"
        ].astype(str)
    )
    candidate_monthly["path_failed"] = candidate_monthly["candidate_id"].isin(
        failed_candidates
    )
    candidate_monthly.loc[
        candidate_monthly["path_failed"], ["gross_return", "traded_notional"]
    ] = np.nan
    expected_markets = sorted(
        set(candidate_monthly["market"].unique()) & set(factor_monthly["market"].unique())
    )
    availability = (
        candidate_monthly.assign(_valid=candidate_monthly["gross_return"].notna())
        .groupby(["candidate_id", "market"])["_valid"]
        .sum()
        .unstack("market", fill_value=0)
        .reindex(columns=expected_markets, fill_value=0)
    )
    candidate_ids = sorted(
        candidate
        for candidate in availability.index[(availability > 0).all(axis=1)].tolist()
        if candidate not in failed_candidates
    )
    if not candidate_ids:
        raise ValueError("no candidate has a return in every requested market")
    candidate_check = candidate_monthly.pivot(
        index=["market", "month"], columns="candidate_id", values="gross_return"
    ).reset_index()
    factor_check = factor_monthly[["market", "month", *FACTOR_COLS]].copy()
    complete = (
        factor_check.merge(candidate_check, on=["market", "month"], how="inner")
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=[*FACTOR_COLS, *candidate_ids])
    )
    complete_counts = complete.groupby("month")["market"].nunique()
    good_months = complete_counts[complete_counts == len(expected_markets)].index
    valid_keys = complete[complete["month"].isin(good_months)][["market", "month"]]
    candidate_monthly = candidate_monthly.merge(
        valid_keys, on=["market", "month"], how="inner"
    )
    factor_monthly = factor_monthly.merge(valid_keys, on=["market", "month"], how="inner")
    pooled_candidates = (
        candidate_monthly.groupby(["month", "candidate_id"], as_index=False)
        .agg(
            gross_return=("gross_return", "mean"),
            traded_notional=("traded_notional", "mean"),
            missing_excess_return_gross_weight=("missing_excess_return_gross_weight", "mean"),
            missing_total_return_gross_weight=("missing_total_return_gross_weight", "mean"),
            n_countries=("gross_return", "count"),
            n_long=("n_long", "median"),
            n_short=("n_short", "median"),
            max_abs_weight=("max_abs_weight", "median"),
            weight_hhi=("weight_hhi", "median"),
            gross_exposure=("gross_exposure", "median"),
            path_failed=("path_failed", "max"),
        )
    )
    factor_agg = {factor: "mean" for factor in FACTOR_COLS}
    factor_missing_cols = [
        column
        for column in factor_monthly.columns
        if "missing_" in column and column.endswith("return_gross_weight")
    ]
    factor_agg.update({column: "mean" for column in factor_missing_cols})
    factor_agg.update({"n_stocks": "sum", "market_cap_sum": "sum", "market": "nunique"})
    pooled_factors = factor_monthly.groupby("month", as_index=False).agg(factor_agg)
    pooled_factors = pooled_factors.rename(columns={"market": "n_countries"})
    expected_count = len(expected_markets)
    executable = ~pooled_candidates["path_failed"]
    if not (pooled_candidates.loc[executable, "n_countries"] == expected_count).all():
        raise RuntimeError("candidate country sleeves do not share the complete market set")
    if not (pooled_factors["n_countries"] == expected_count).all():
        raise RuntimeError("factor country sleeves do not share the complete market set")
    return pooled_candidates, pooled_factors


def candidate_metadata() -> pd.DataFrame:
    rows = []
    for candidate, meta in proxy.IDEA_DEFINITIONS.items():
        rows.append({"candidate_id": candidate, **meta})
    rows.append(
        {
            "candidate_id": CONTEST_ID,
            "paper_ref": "024 ContestTrade",
            "paper_idea": "Trailing selection among frozen proxy sleeves using only prior returns.",
            "proxy_formula": "past-36-month Sharpe winner with at least 24 months of history",
            "strategy": "meta_sleeve_selection_trailing_sharpe",
            "replication_scope": "mechanism_inspired_proxy",
        }
    )
    return pd.DataFrame(rows)


def _wide_net_frame(
    pooled_candidates: pd.DataFrame,
    pooled_factors: pd.DataFrame,
    cost_bps: int,
) -> pd.DataFrame:
    x = pooled_candidates.copy()
    x["net_return"] = x["gross_return"] - (cost_bps / 10000.0) * x["traded_notional"]
    wide = x.pivot(index="month", columns="candidate_id", values="net_return").reset_index()
    return pooled_factors.merge(wide, on="month", how="inner").sort_values("month")


def _with_candidate_columns(frame: pd.DataFrame, candidate_ids: list[str]) -> pd.DataFrame:
    """Add explicit all-missing columns for planned candidates that failed."""
    frame = frame.copy()
    for candidate in candidate_ids:
        if candidate not in frame:
            frame[candidate] = np.nan
    return frame


def _path_failure_ids(frame: pd.DataFrame) -> set[str]:
    if "path_failed" in frame:
        return set(frame.loc[frame["path_failed"].fillna(False), "candidate_id"].astype(str))
    if "path_failure_event" in frame:
        return set(
            frame.loc[frame["path_failure_event"].fillna(False), "candidate_id"].astype(str)
        )
    return set()


def restrict_common_calendar(frame: pd.DataFrame, candidate_ids: list[str]) -> pd.DataFrame:
    """Use the identical candidate-factor calendar for all family estimates."""
    required = [*FACTOR_COLS, *candidate_ids]
    common = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=required).copy()
    if common.empty:
        raise ValueError("no complete common candidate-factor calendar")
    common = common.sort_values("month").reset_index(drop=True)
    periods = pd.PeriodIndex(pd.to_datetime(common["month"]), freq="M")
    if periods.duplicated().any():
        raise ValueError("common calendar contains duplicate months")
    expected = pd.period_range(periods.min(), periods.max(), freq="M")
    if not periods.equals(expected):
        missing = expected.difference(periods)
        raise ValueError(f"common calendar is not consecutive; missing={list(map(str, missing))}")
    return common


def run_pooled_analysis(
    pooled_candidates: pd.DataFrame,
    pooled_factors: pd.DataFrame,
    metadata: pd.DataFrame,
    *,
    n_bootstrap: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    candidate_ids = metadata["candidate_id"].tolist()
    path_failure_ids = _path_failure_ids(pooled_candidates)
    availability_frame = _with_candidate_columns(
        _wide_net_frame(pooled_candidates, pooled_factors, 10), candidate_ids
    )
    minimum_observations = len(FACTOR_COLS) + 13
    eligible_candidate_ids = [
        candidate
        for candidate in candidate_ids
        if candidate not in path_failure_ids
        and availability_frame[candidate].replace([np.inf, -np.inf], np.nan).notna().sum()
        >= minimum_observations
    ]
    failed_availability_ids = sorted(set(candidate_ids) - set(eligible_candidate_ids))
    if not eligible_candidate_ids:
        raise ValueError("no candidate has sufficient return history")
    results = []
    wide_by_cost: dict[int, pd.DataFrame] = {}
    for cost_bps in COSTS_BPS:
        wide = restrict_common_calendar(
            _with_candidate_columns(
                _wide_net_frame(pooled_candidates, pooled_factors, cost_bps),
                candidate_ids,
            ),
            eligible_candidate_ids,
        )
        wide_by_cost[cost_bps] = wide
        for candidate in eligible_candidate_ids:
            try:
                estimate = alpha_regression(wide, candidate, FACTOR_COLS)
                row = asdict(estimate)
                row.update({"candidate_id": candidate, "cost_bps_one_way": cost_bps, "status": "ok"})
            except Exception as exc:
                row = {
                    "candidate_id": candidate,
                    "cost_bps_one_way": cost_bps,
                    "status": f"failed:{type(exc).__name__}:{exc}",
                }
            results.append(row)
        for candidate in failed_availability_ids:
            results.append(
                {
                    "candidate_id": candidate,
                    "cost_bps_one_way": cost_bps,
                    "status": (
                        "failed:bankruptcy_nonpositive_nav"
                        if candidate in path_failure_ids
                        else "failed:insufficient_return_history"
                    ),
                }
            )
    result_frame = pd.DataFrame(results).merge(metadata, on="candidate_id", how="left")

    primary = result_frame[result_frame["cost_bps_one_way"] == 10].copy()
    primary_by_id = primary.set_index("candidate_id", drop=False)
    p_map = {}
    for candidate in candidate_ids:
        row = primary_by_id.loc[candidate]
        raw_p = row.get("p_value_two_sided", np.nan)
        p_map[candidate] = (
            float(raw_p)
            if row.get("status") == "ok" and np.isfinite(raw_p)
            else 1.0
        )
    multiplicity = multiplicity_adjustments(p_map, planned_m=len(candidate_ids)).rename(
        columns={"p_value_two_sided": "adjustment_input_p_value"}
    )

    primary_wide = wide_by_cost[10]
    successful_ids = primary.loc[primary["status"] == "ok", "candidate_id"].tolist()
    bootstrap, bootstrap_meta = paired_block_bootstrap_alpha(
        primary_wide,
        successful_ids,
        FACTOR_COLS,
        n_bootstrap=n_bootstrap,
        block_length=6,
        seed=20260802,
    )
    primary = primary.merge(multiplicity, on="candidate_id", how="left")
    primary = primary.merge(bootstrap, on="candidate_id", how="left")
    successful_mask = primary["status"] == "ok"
    if not np.allclose(
        primary.loc[successful_mask, "alpha_monthly"],
        primary.loc[successful_mask, "bootstrap_alpha_point_monthly"],
        rtol=1e-10,
        atol=1e-12,
    ):
        raise RuntimeError("primary and bootstrap alpha point estimates use different samples")
    primary["point_alpha_at_least_2pp"] = successful_mask & (primary["alpha_annualized"] >= 0.02)
    primary["confirmed_alpha_at_least_2pp"] = primary["simultaneous_ci_low_annualized"] >= 0.02
    primary["holm_discovery_5pct"] = (primary["holm_p_value"] <= 0.05) & (
        primary["alpha_annualized"] > 0
    )
    primary["max_t_discovery_5pct"] = (primary["max_abs_t_p_value"] <= 0.05) & (
        primary["alpha_annualized"] > 0
    )
    return result_frame, primary, multiplicity, bootstrap_meta


def run_country_analysis(
    candidate_monthly: pd.DataFrame,
    factor_monthly: pd.DataFrame,
    metadata: pd.DataFrame,
    *,
    cost_bps: int = 10,
) -> pd.DataFrame:
    rows = []
    candidate_ids = metadata["candidate_id"].tolist()
    minimum_observations = len(FACTOR_COLS) + 13
    for market in sorted(factor_monthly["market"].unique()):
        factors = factor_monthly[factor_monthly["market"] == market]
        candidates = candidate_monthly[candidate_monthly["market"] == market].copy()
        path_failure_ids = _path_failure_ids(candidates)
        candidates["net_return"] = candidates["gross_return"] - (
            cost_bps / 10000.0
        ) * candidates["traded_notional"]
        wide = _with_candidate_columns(
            candidates.pivot(
                index="month", columns="candidate_id", values="net_return"
            ).reset_index(),
            candidate_ids,
        )
        merged = factors.merge(wide, on="month", how="inner")
        eligible_ids = [
            candidate
            for candidate in candidate_ids
            if candidate not in path_failure_ids
            and merged[candidate].replace([np.inf, -np.inf], np.nan).notna().sum()
            >= minimum_observations
        ]
        frame = restrict_common_calendar(merged, eligible_ids) if eligible_ids else None
        for candidate in candidate_ids:
            if candidate not in eligible_ids:
                rows.append(
                    {
                        "market": market,
                        "candidate_id": candidate,
                        "status": (
                            "failed:bankruptcy_nonpositive_nav"
                            if candidate in path_failure_ids
                            else "failed:insufficient_return_history"
                        ),
                    }
                )
                continue
            try:
                assert frame is not None
                result = asdict(alpha_regression(frame, candidate, FACTOR_COLS))
                result.update({"market": market, "candidate_id": candidate, "status": "ok"})
            except Exception as exc:
                result = {
                    "market": market,
                    "candidate_id": candidate,
                    "status": f"failed:{type(exc).__name__}:{exc}",
                }
            rows.append(result)
    return pd.DataFrame(rows).merge(metadata, on="candidate_id", how="left")


def run_hac_lag_sensitivity(
    primary_wide: pd.DataFrame,
    candidate_ids: list[str],
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for lag in (0, 3, 6, 12):
        for candidate in candidate_ids:
            try:
                result = asdict(
                    alpha_regression(primary_wide, candidate, FACTOR_COLS, hac_lags=lag)
                )
                result.update({"candidate_id": candidate, "fixed_hac_lags": lag, "status": "ok"})
            except Exception as exc:
                result = {
                    "candidate_id": candidate,
                    "fixed_hac_lags": lag,
                    "status": f"failed:{type(exc).__name__}:{exc}",
                }
            rows.append(result)
    return pd.DataFrame(rows).merge(metadata, on="candidate_id", how="left")


def run_block_length_sensitivity(
    primary_wide: pd.DataFrame,
    candidate_ids: list[str],
    *,
    n_bootstrap: int,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames = []
    metadata_rows = []
    for block_length in (3, 12):
        frame, metadata = paired_block_bootstrap_alpha(
            primary_wide,
            candidate_ids,
            FACTOR_COLS,
            n_bootstrap=n_bootstrap,
            block_length=block_length,
            seed=20260802,
        )
        frame.insert(1, "block_length", block_length)
        frames.append(frame)
        metadata_rows.append(metadata)
    return pd.concat(frames, ignore_index=True), metadata_rows


def leave_one_country_out(
    candidate_monthly: pd.DataFrame,
    factor_monthly: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    markets = sorted(factor_monthly["market"].unique())
    candidate_ids = metadata["candidate_id"].tolist()
    if len(markets) < 2:
        excluded = markets[0] if markets else "not_available"
        for candidate in candidate_ids:
            rows.append(
                {
                    "excluded_market": excluded,
                    "candidate_id": candidate,
                    "status": "not_applicable:single_market_retrospective",
                }
            )
        return pd.DataFrame(rows).merge(metadata, on="candidate_id", how="left")
    for excluded in markets:
        candidates = candidate_monthly[candidate_monthly["market"] != excluded]
        factors = factor_monthly[factor_monthly["market"] != excluded]
        pooled_candidates, pooled_factors = pool_country_sleeves(candidates, factors)
        path_failure_ids = _path_failure_ids(pooled_candidates)
        wide_all = _with_candidate_columns(
            _wide_net_frame(pooled_candidates, pooled_factors, 10), candidate_ids
        )
        minimum_observations = len(FACTOR_COLS) + 13
        eligible_ids = [
            candidate
            for candidate in candidate_ids
            if candidate not in path_failure_ids
            and wide_all[candidate].replace([np.inf, -np.inf], np.nan).notna().sum()
            >= minimum_observations
        ]
        wide = restrict_common_calendar(wide_all, eligible_ids) if eligible_ids else None
        for candidate in candidate_ids:
            if candidate not in eligible_ids:
                rows.append(
                    {
                        "excluded_market": excluded,
                        "candidate_id": candidate,
                        "status": (
                            "failed:bankruptcy_nonpositive_nav"
                            if candidate in path_failure_ids
                            else "failed:insufficient_return_history"
                        ),
                    }
                )
                continue
            try:
                assert wide is not None
                result = asdict(alpha_regression(wide, candidate, FACTOR_COLS))
                result.update({"excluded_market": excluded, "candidate_id": candidate, "status": "ok"})
            except Exception as exc:
                result = {
                    "excluded_market": excluded,
                    "candidate_id": candidate,
                    "status": f"failed:{type(exc).__name__}:{exc}",
                }
            rows.append(result)
    return pd.DataFrame(rows).merge(metadata, on="candidate_id", how="left")


def turnover_summary(
    pooled_candidates: pd.DataFrame,
    all_cost_results: pd.DataFrame,
) -> pd.DataFrame:
    summary = (
        pooled_candidates.groupby("candidate_id", as_index=False)
        .agg(
            valid_months=("gross_return", "count"),
            mean_monthly_traded_notional=("traded_notional", "mean"),
            median_monthly_traded_notional=("traded_notional", "median"),
            p90_monthly_traded_notional=("traded_notional", lambda x: x.quantile(0.9)),
            median_n_long=("n_long", "median"),
            median_n_short=("n_short", "median"),
            median_max_abs_weight=("max_abs_weight", "median"),
            median_weight_hhi=("weight_hhi", "median"),
            median_country_count=("n_countries", "median"),
            mean_missing_excess_return_gross_weight=("missing_excess_return_gross_weight", "mean"),
            max_missing_excess_return_gross_weight=("missing_excess_return_gross_weight", "max"),
            mean_missing_total_return_gross_weight=("missing_total_return_gross_weight", "mean"),
            max_missing_total_return_gross_weight=("missing_total_return_gross_weight", "max"),
        )
    )
    summary["annualized_traded_notional"] = 12.0 * summary["mean_monthly_traded_notional"]
    cost_lines = []
    for candidate_id, frame in all_cost_results[all_cost_results["status"] == "ok"].groupby(
        "candidate_id"
    ):
        frame = frame.sort_values("cost_bps_one_way")
        slope, intercept = np.polyfit(
            frame["cost_bps_one_way"].to_numpy(dtype="float64"),
            frame["alpha_annualized"].to_numpy(dtype="float64"),
            deg=1,
        )
        break_even = -intercept / slope if intercept > 0 and slope < 0 else np.nan
        cost_lines.append(
            {
                "candidate_id": candidate_id,
                "gross_alpha_annualized": float(intercept),
                "alpha_drag_annualized_per_cost_bp": float(-slope),
                "alpha_break_even_cost_bps": float(break_even),
            }
        )
    summary = summary.merge(pd.DataFrame(cost_lines), on="candidate_id", how="left")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markets", default=",".join(DEFAULT_MARKETS))
    parser.add_argument("--tag", default="g7_ex_us")
    parser.add_argument("--start", default="1999-07-31")
    parser.add_argument("--end", default="2024-11-30")
    parser.add_argument("--top-n", type=int, default=1000)
    parser.add_argument("--quantile", type=float, default=0.1)
    parser.add_argument("--min-side", type=int, default=20)
    parser.add_argument(
        "--missing-return-policy",
        choices=["zero", "adverse_100"],
        default="zero",
        help="Primary zero policy or position-adverse 100% missing-return sensitivity.",
    )
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument(
        "--out-root", type=Path, default=REPO_ROOT / "paper_runs" / "submission_evidence"
    )
    parser.add_argument(
        "--lock", type=Path, default=REPO_ROOT / "paper_runs" / "submission_evidence" / "analysis_lock.json"
    )
    args = parser.parse_args(argv)
    markets = [item.strip().upper() for item in args.markets.split(",") if item.strip()]
    required_files = [
        REPO_ROOT / "docs" / "confirmatory_analysis_protocol.md",
        REPO_ROOT / "scripts" / "run_paper_idea_jkp_proxies.py",
        REPO_ROOT / "scripts" / "freeze_submission_analysis.py",
        REPO_ROOT / "scripts" / "run_submission_evidence.py",
        REPO_ROOT / "src" / "alpha_evolve" / "submission_analysis.py",
        REPO_ROOT / "literature_review" / "census_v1" / "system_registry.csv",
        REPO_ROOT / "paper_runs" / "submission_evidence" / "frozen_candidate_registry.csv",
    ]
    lock = load_lock(
        args.lock,
        required_files,
        {market: market_path(market) for market in markets},
    )
    frozen_parameters = lock.get("analysis_parameters", {})
    observed_parameters = {
        "formation_start": args.start,
        "formation_end": args.end,
        "top_n": args.top_n,
        "quantile": args.quantile,
        "min_side": args.min_side,
    }
    parameter_failures = {
        key: {"expected": frozen_parameters.get(key), "observed": value}
        for key, value in observed_parameters.items()
        if frozen_parameters.get(key) != value
    }
    if args.missing_return_policy not in frozen_parameters.get(
        "allowed_missing_return_policies", []
    ):
        parameter_failures["missing_return_policy"] = {
            "expected": frozen_parameters.get("allowed_missing_return_policies"),
            "observed": args.missing_return_policy,
        }
    if args.bootstrap < int(frozen_parameters.get("minimum_bootstrap_replications", 0)):
        parameter_failures["bootstrap"] = {
            "expected_minimum": frozen_parameters.get("minimum_bootstrap_replications"),
            "observed": args.bootstrap,
        }
    allowed_market_sets = [
        sorted(lock.get("holdout_markets", [])),
        sorted(lock.get("retrospective_markets", [])),
    ]
    if sorted(markets) not in allowed_market_sets:
        parameter_failures["markets"] = {
            "expected_one_of": allowed_market_sets,
            "observed": sorted(markets),
        }
    if parameter_failures:
        raise RuntimeError(f"frozen analysis parameter mismatch: {parameter_failures}")
    out_dir = args.out_root / args.tag
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite nonempty output directory: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate_parts = []
    factor_parts = []
    for market in markets:
        print(f"building {market}", flush=True)
        candidates, factors = build_one_market(
            market,
            start=args.start,
            end=args.end,
            top_n=args.top_n,
            quantile=args.quantile,
            min_side=args.min_side,
            missing_return_policy=args.missing_return_policy,
        )
        candidates.to_csv(out_dir / f"candidate_monthly_{market}.csv", index=False)
        factors.to_csv(out_dir / f"factor_monthly_{market}.csv", index=False)
        candidate_parts.append(candidates)
        factor_parts.append(factors)
        print(f"completed {market}: {len(candidates):,} candidate-month rows", flush=True)

    candidate_monthly = pd.concat(candidate_parts, ignore_index=True)
    factor_monthly = pd.concat(factor_parts, ignore_index=True)
    observed_candidate_markets = sorted(candidate_monthly["market"].unique())
    observed_factor_markets = sorted(factor_monthly["market"].unique())
    if observed_candidate_markets != sorted(markets) or observed_factor_markets != sorted(markets):
        raise RuntimeError(
            "requested and observed markets differ: "
            f"requested={sorted(markets)}, candidates={observed_candidate_markets}, "
            f"factors={observed_factor_markets}"
        )
    candidate_monthly.to_csv(out_dir / "candidate_monthly_all_markets.csv", index=False)
    factor_monthly.to_csv(out_dir / "factor_monthly_all_markets.csv", index=False)
    failure_columns = [
        "market",
        "formation_month",
        "month",
        "candidate_id",
        "selected_sleeve",
        "observed_gross_return",
        "observed_traded_notional",
        "failure_total_return",
        "path_status",
    ]
    path_failures = candidate_monthly.loc[
        candidate_monthly["path_failure_event"].fillna(False), failure_columns
    ].copy()
    path_failures.to_csv(out_dir / "candidate_path_failures.csv", index=False)
    pooled_candidates, pooled_factors = pool_country_sleeves(candidate_monthly, factor_monthly)
    pooled_candidates.to_csv(out_dir / "candidate_monthly_country_equal.csv", index=False)
    pooled_factors.to_csv(out_dir / "factor_monthly_country_equal.csv", index=False)

    metadata = candidate_metadata()
    metadata.to_csv(out_dir / "candidate_metadata.csv", index=False)
    all_cost, primary, multiplicity, bootstrap_meta = run_pooled_analysis(
        pooled_candidates,
        pooled_factors,
        metadata,
        n_bootstrap=args.bootstrap,
    )
    all_cost.to_csv(out_dir / "candidate_cost_alpha_results.csv", index=False)
    primary.to_csv(out_dir / "candidate_primary_results.csv", index=False)
    multiplicity.to_csv(out_dir / "multiplicity_adjustments.csv", index=False)
    successful_ids = primary.loc[primary["status"] == "ok", "candidate_id"].tolist()
    sensitivity_wide = restrict_common_calendar(
        _wide_net_frame(pooled_candidates, pooled_factors, 10), successful_ids
    )
    hac_sensitivity = run_hac_lag_sensitivity(sensitivity_wide, successful_ids, metadata)
    hac_sensitivity.to_csv(out_dir / "hac_lag_sensitivity.csv", index=False)
    block_sensitivity, block_sensitivity_meta = run_block_length_sensitivity(
        sensitivity_wide,
        successful_ids,
        n_bootstrap=args.bootstrap,
    )
    block_sensitivity.to_csv(out_dir / "bootstrap_block_sensitivity.csv", index=False)
    country = run_country_analysis(candidate_monthly, factor_monthly, metadata)
    country.to_csv(out_dir / "candidate_country_results.csv", index=False)
    loo = leave_one_country_out(candidate_monthly, factor_monthly, metadata)
    loo.to_csv(out_dir / "candidate_leave_one_country_out.csv", index=False)
    turnover = turnover_summary(pooled_candidates, all_cost).merge(metadata, on="candidate_id", how="left")
    turnover.to_csv(out_dir / "turnover_summary.csv", index=False)

    candidate_missing_long = candidate_monthly.melt(
        id_vars=["market", "month", "candidate_id"],
        value_vars=["missing_excess_return_gross_weight", "missing_total_return_gross_weight"],
        var_name="return_field",
        value_name="missing_return_gross_weight",
    )
    candidate_missing = (
        candidate_missing_long.groupby(["market", "candidate_id", "return_field"], as_index=False)
        .agg(
            mean_missing_return_gross_weight=("missing_return_gross_weight", "mean"),
            max_missing_return_gross_weight=("missing_return_gross_weight", "max"),
            months_with_missing_return_exposure=(
                "missing_return_gross_weight",
                lambda values: int((values.fillna(0.0) > 0).sum()),
            ),
        )
        .rename(columns={"candidate_id": "object_id"})
    )
    candidate_missing.insert(1, "object_type", "candidate")
    factor_missing_cols = [
        column
        for column in factor_monthly.columns
        if "missing_" in column and column.endswith("return_gross_weight")
    ]
    factor_missing = factor_monthly.melt(
        id_vars=["market", "month"],
        value_vars=factor_missing_cols,
        var_name="object_id",
        value_name="missing_return_gross_weight",
    )
    factor_missing = (
        factor_missing.groupby(["market", "object_id"], as_index=False)
        .agg(
            mean_missing_return_gross_weight=("missing_return_gross_weight", "mean"),
            max_missing_return_gross_weight=("missing_return_gross_weight", "max"),
            months_with_missing_return_exposure=(
                "missing_return_gross_weight",
                lambda values: int((values.fillna(0.0) > 0).sum()),
            ),
        )
    )
    factor_missing.insert(1, "object_type", "factor")
    factor_missing.insert(
        3,
        "return_field",
        factor_missing["object_id"].str.extract(r"(missing_(?:excess|total)_return_gross_weight)")[0],
    )
    missing_summary = pd.concat([candidate_missing, factor_missing], ignore_index=True)
    missing_summary.to_csv(out_dir / "missing_return_exposure_summary.csv", index=False)

    run_manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "tag": args.tag,
        "markets": markets,
        "start": args.start,
        "end": args.end,
        "formation_start": args.start,
        "formation_end": args.end,
        "realized_return_start": str((pd.Timestamp(args.start) + pd.offsets.MonthEnd(1)).date()),
        "realized_return_end": str((pd.Timestamp(args.end) + pd.offsets.MonthEnd(1)).date()),
        "top_n": args.top_n,
        "quantile": args.quantile,
        "min_side": args.min_side,
        "formation_uses_next_month_return_availability": False,
        "missing_next_month_return_policy": args.missing_return_policy,
        "missing_total_return_for_drift_policy": "zero when reconstructed total return is missing; exposure recorded separately",
        "family_sample_policy": "complete common candidate-factor calendar at every cost",
        "weight_drift_policy": "all risky weights divided by common post-return strategy NAV",
        "weight_drift_return": "one-month-ahead USD total return reconstructed from the next consecutive JKP row",
        "limited_liability_policy": (
            "a candidate with realized total portfolio return <= -100% in any included "
            "market is a complete-path implementation failure, is never restarted or "
            "recapitalized, remains in the 62-hypothesis denominator with p=1, and does "
            "not determine the executable-candidate common calendar"
        ),
        "path_failure_events": int(len(path_failures)),
        "path_failure_candidates": int(path_failures["candidate_id"].nunique()),
        "costs_bps_one_way": COSTS_BPS,
        "primary_cost_bps_one_way": 10,
        "bootstrap": bootstrap_meta,
        "bootstrap_block_sensitivity": block_sensitivity_meta,
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "analysis_lock_sha256": sha256_file(args.lock),
        "analysis_lock_created_at_utc": lock.get("created_at_utc"),
        "input_files": {market: lock["data_inputs"][market] for market in markets},
        "paid_api_calls": 0,
        "openrouter_spend_usd": 0.0,
    }
    output_hashes = {}
    for path in sorted(out_dir.glob("*.csv")):
        output_hashes[path.name] = sha256_file(path)
    run_manifest["output_sha256"] = output_hashes
    (out_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
