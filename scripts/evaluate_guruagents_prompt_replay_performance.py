#!/usr/bin/env python3
"""Build investable return paths and factor tests for the GuruAgents prompt replay.

The script deliberately separates three objects:

* replayed LLM portfolios, reconstructed from each saved final answer;
* the authors' archived portfolio CSVs, evaluated through the same corrected clock;
* the existing long-short JKP motif proxies, retained as a separate diagnostic.

Formation portfolios are executed at the first trading close strictly after the
formation quarter end. Holdings then drift until the next quarterly rebalance.
The primary net series defaults to the paper-declared one basis point per unit
of one-way traded notional. Full JKP132 OLS is reported only where it is
identified; short replay histories additionally receive a clearly labelled leave-one-month-out ridge
diagnostic and a pre-2022 factor-only PCA compression test.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import scipy
from scipy import stats


AGENTS = ("graham", "buffett", "greenblatt", "piotroski", "altman")
DEFAULT_COST_BPS = 1.0
PRIMARY_FACTOR_COLUMNS = (
    "capm_top1000_mkt",
    "char__be_me",
    "char__market_equity",
    "char__at_gr1",
    "char__ope_be",
    "char__ret_12_1",
)
OFFICIAL_FF_FACTOR_COLUMNS = ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom")
JKP_BAB_FACTOR = "char__betabab_1260d"
JKP_LOW_RISK_FACTOR_COLUMNS = (
    JKP_BAB_FACTOR,
    "char__beta_60m",
    "char__beta_dimson_21d",
    "char__betadown_252d",
    "char__ivol_capm_252d",
    "char__rvol_21d",
    "char__qmj_safety",
)
ATTRIBUTION_BENCHMARK_ORDER = (
    "official_ff_capm_matched_jkp_window",
    "official_ff3_matched_jkp_window",
    "official_ff5_momentum_matched_jkp_window",
    "official_ff5_momentum_plus_jkp_bab",
    "official_ff5_momentum_plus_jkp_lowrisk",
)
ATTRIBUTION_MIN_MONTHS = 33
RIDGE_GRID = (0.1, 1.0, 10.0, 100.0, 1000.0)
TICKER_CORRECTIONS = {
    "CP": "CPRT",
    "CPTR": "CPRT",
    "CPWR": "CPRT",
    "CHRT": "CHTR",
    "INTEL": "INTC",
    "INTL": "INTC",
}
NON_SECURITY_LABELS = {"REMAINING", "CASH", "TOTAL", "N/A", "NA"}
PROXY_MAP = {
    "graham": "guru_graham_deep_value_defensive",
    "buffett": "guru_buffett_quality_compounder",
    "greenblatt": "guru_greenblatt_magic_formula",
    "piotroski": "guru_piotroski_fscore_proxy",
    "altman": "guru_altman_distress_avoidance",
    "ensemble": "guru_equal_weight_style_ensemble",
}


@dataclass
class Formation:
    candidate_id: str
    series_type: str
    archive: str
    agent: str
    mode: str
    formation_end: pd.Timestamp
    target_weights: Dict[str, float]
    raw_weight_sum: float
    table_weight_sum: float
    parsed_rows: int
    selected_table_index: int
    selected_table_count: int
    corrected_tickers: str
    dropped_labels: str
    dropped_unknown_tickers: str
    source_path: str
    experiment_id: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_locator(path: Path, repo_root: Path) -> Dict[str, str]:
    """Return a portable locator without publishing host-specific absolute paths."""
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(repo_root.resolve())
    except ValueError:
        return {
            "path": resolved.name,
            "path_scope": "external_authorized_input",
        }
    return {
        "path": relative.as_posix(),
        "path_scope": "repository_relative",
    }


def portable_source_locator(
    value: str,
    roots: Sequence[Tuple[str, Path]],
) -> str:
    """Replace an absolute audit source path with a stable scoped locator."""
    if not value.startswith("/"):
        return value
    resolved = Path(value).resolve()
    for scope, root in roots:
        try:
            relative = resolved.relative_to(root.resolve())
        except ValueError:
            continue
        return f"{scope}://{relative.as_posix()}"
    return f"external://{resolved.name}"


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def parse_number(value: str) -> Optional[float]:
    cleaned = re.sub(r"[^0-9eE+\-.]", "", value)
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number if np.isfinite(number) else None


def split_markdown_row(line: str) -> List[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def parse_markdown_portfolio_tables(text: str) -> List[List[Dict[str, Any]]]:
    """Parse each ticker/score/weight markdown table as a separate object."""
    lines = text.splitlines()
    tables: List[List[Dict[str, Any]]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip().startswith("|"):
            i += 1
            continue
        header = [re.sub(r"[^a-z%]", "", p.lower()) for p in split_markdown_row(line)]
        has_ticker = any("ticker" in p or "symbol" in p for p in header)
        has_score = any("score" in p for p in header)
        has_weight = any("weight" in p for p in header)
        if not (has_ticker and has_score and has_weight):
            i += 1
            continue
        ticker_idx = next(j for j, p in enumerate(header) if "ticker" in p or "symbol" in p)
        score_idx = next(j for j, p in enumerate(header) if "score" in p)
        weight_idx = next(j for j, p in enumerate(header) if "weight" in p)
        reason_idx = next((j for j, p in enumerate(header) if "reason" in p), None)
        rows: List[Dict[str, Any]] = []
        i += 1
        while i < len(lines) and lines[i].strip().startswith("|"):
            parts = split_markdown_row(lines[i])
            i += 1
            if len(parts) <= max(ticker_idx, score_idx, weight_idx):
                continue
            ticker = re.sub(r"[*`]", "", parts[ticker_idx]).strip().upper()
            if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,14}", ticker) or ticker == "TICKER":
                continue
            score = parse_number(parts[score_idx])
            weight = parse_number(parts[weight_idx])
            if score is None or weight is None:
                continue
            rows.append(
                {
                    "Ticker": ticker,
                    "Score": score,
                    "Weight (%)": weight,
                    "Reason": parts[reason_idx] if reason_idx is not None and reason_idx < len(parts) else "",
                }
            )
        if rows:
            tables.append(rows)
    return tables


def select_portfolio_table(text: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    tables = parse_markdown_portfolio_tables(text)
    if not tables:
        raise ValueError("No ticker/score/weight markdown table was found")
    scored: List[Tuple[Tuple[float, int, int], int, List[Dict[str, Any]]]] = []
    for index, rows in enumerate(tables):
        total = float(sum(max(float(row["Weight (%)"]), 0.0) for row in rows))
        unique = len({str(row["Ticker"]) for row in rows})
        # Prefer an allocation closest to 100%, then fewer duplicate rows, then
        # the later table when an answer restates its final allocation.
        score = (abs(total - 100.0), len(rows) - unique, -index)
        scored.append((score, index, rows))
    _, index, selected = min(scored, key=lambda item: item[0])
    return selected, {
        "selected_table_index": index,
        "selected_table_count": len(tables),
        "selected_table_weight_sum": float(sum(float(row["Weight (%)"]) for row in selected)),
    }


def read_archived_portfolio(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    parsed: List[Dict[str, Any]] = []
    for row in rows:
        ticker = str(row.get("Ticker", "")).strip().upper() or "REMAINING"
        score = parse_number(str(row.get("Score", "")))
        weight = parse_number(str(row.get("Weight (%)", "")))
        if score is None:
            score = 0.0
        if weight is None:
            continue
        parsed.append(
            {
                "Ticker": ticker,
                "Score": score,
                "Weight (%)": weight,
                "Reason": str(row.get("Reason", "")),
            }
        )
    return parsed


def clean_portfolio_rows(
    rows: Sequence[Mapping[str, Any]], available_tickers: Iterable[str]
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    available = set(available_tickers)
    grouped: Dict[str, float] = defaultdict(float)
    raw_weight_sum = 0.0
    corrections: List[str] = []
    dropped_labels: List[str] = []
    dropped_unknown: List[str] = []
    for row in rows:
        ticker = str(row["Ticker"]).strip().upper()
        weight = float(row["Weight (%)"])
        if not np.isfinite(weight) or weight <= 0:
            continue
        raw_weight_sum += weight
        if ticker in NON_SECURITY_LABELS:
            dropped_labels.append(f"{ticker}:{weight:g}")
            continue
        corrected = TICKER_CORRECTIONS.get(ticker, ticker)
        if corrected != ticker:
            corrections.append(f"{ticker}->{corrected}")
        if corrected not in available:
            dropped_unknown.append(f"{corrected}:{weight:g}")
            continue
        grouped[corrected] += weight
    investable_sum = float(sum(grouped.values()))
    if investable_sum <= 0:
        raise ValueError("Portfolio has no investable positive-weight holdings")
    normalized = {ticker: weight / investable_sum for ticker, weight in sorted(grouped.items())}
    return normalized, {
        "raw_weight_sum": raw_weight_sum,
        "investable_weight_sum": investable_sum,
        "normalized_holding_count": len(normalized),
        "corrected_tickers": ";".join(sorted(set(corrections))),
        "dropped_labels": ";".join(dropped_labels),
        "dropped_unknown_tickers": ";".join(dropped_unknown),
    }


def load_price_data(path: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    usecols = ["TICKERSYMBOL", "EVAL_D", "DIV_ADJ_CLOSE", "CLOSE_", "MKTCAP"]
    raw = pd.read_csv(path, usecols=usecols)
    raw["date"] = pd.to_datetime(raw["EVAL_D"], errors="coerce")
    raw["ticker"] = raw["TICKERSYMBOL"].astype(str).str.strip().str.upper()
    raw["price"] = pd.to_numeric(raw["DIV_ADJ_CLOSE"], errors="coerce")
    fallback = pd.to_numeric(raw["CLOSE_"], errors="coerce")
    raw["price"] = raw["price"].where(raw["price"].gt(0), fallback)
    raw["market_cap"] = pd.to_numeric(raw["MKTCAP"], errors="coerce")
    raw = raw.dropna(subset=["date", "ticker", "price"]).sort_values(["date", "ticker"])
    raw = raw.drop_duplicates(["date", "ticker"], keep="last")
    prices = raw.pivot(index="date", columns="ticker", values="price").sort_index().ffill()
    caps = raw.pivot(index="date", columns="ticker", values="market_cap").sort_index().ffill()
    return raw, prices, caps


def discover_formations(
    run_dir: Path, available_tickers: Iterable[str]
) -> Tuple[List[Formation], pd.DataFrame]:
    replay: List[Formation] = []
    authors_by_key: Dict[Tuple[str, str, str], Formation] = {}
    audit_rows: List[Dict[str, Any]] = []
    for experiment_dir in sorted((run_dir / "experiments").iterdir()):
        result_path = experiment_dir / "result.json"
        if not result_path.exists():
            continue
        info = json.loads(result_path.read_text(encoding="utf-8"))
        if info.get("status") != "success":
            continue
        rows, table_meta = select_portfolio_table(
            (experiment_dir / "final_output.md").read_text(encoding="utf-8")
        )
        weights, clean_meta = clean_portfolio_rows(rows, available_tickers)
        formation_end = pd.Timestamp(info["end_date"])
        candidate_id = f"replay__{info['archive']}__{info['mode']}__{info['agent']}"
        replay.append(
            Formation(
                candidate_id=candidate_id,
                series_type="replay",
                archive=str(info["archive"]),
                agent=str(info["agent"]),
                mode=str(info["mode"]),
                formation_end=formation_end,
                target_weights=weights,
                raw_weight_sum=float(clean_meta["raw_weight_sum"]),
                table_weight_sum=float(table_meta["selected_table_weight_sum"]),
                parsed_rows=len(rows),
                selected_table_index=int(table_meta["selected_table_index"]),
                selected_table_count=int(table_meta["selected_table_count"]),
                corrected_tickers=str(clean_meta["corrected_tickers"]),
                dropped_labels=str(clean_meta["dropped_labels"]),
                dropped_unknown_tickers=str(clean_meta["dropped_unknown_tickers"]),
                source_path=str(experiment_dir / "final_output.md"),
                experiment_id=str(info["experiment_id"]),
            )
        )
        author_key = (str(info["archive"]), str(info["agent"]), str(info["end_date"]))
        if author_key not in authors_by_key:
            portfolio_path = Path(info["portfolio_path"])
            author_rows = read_archived_portfolio(portfolio_path)
            author_weights, author_meta = clean_portfolio_rows(author_rows, available_tickers)
            authors_by_key[author_key] = Formation(
                candidate_id=f"authors__{info['archive']}__{info['agent']}",
                series_type="authors",
                archive=str(info["archive"]),
                agent=str(info["agent"]),
                mode="archived-portfolio",
                formation_end=formation_end,
                target_weights=author_weights,
                raw_weight_sum=float(author_meta["raw_weight_sum"]),
                table_weight_sum=float(author_meta["raw_weight_sum"]),
                parsed_rows=len(author_rows),
                selected_table_index=0,
                selected_table_count=1,
                corrected_tickers=str(author_meta["corrected_tickers"]),
                dropped_labels=str(author_meta["dropped_labels"]),
                dropped_unknown_tickers=str(author_meta["dropped_unknown_tickers"]),
                source_path=str(portfolio_path),
                experiment_id="authors-archived-portfolio",
            )
    formations = replay + list(authors_by_key.values())
    formations.extend(build_ensemble_formations(formations))
    for formation in formations:
        audit_rows.append(
            {
                "candidate_id": formation.candidate_id,
                "series_type": formation.series_type,
                "archive": formation.archive,
                "agent": formation.agent,
                "mode": formation.mode,
                "formation_end": formation.formation_end,
                "formation_month": formation.formation_end + pd.offsets.MonthEnd(0),
                "raw_weight_sum": formation.raw_weight_sum,
                "selected_table_weight_sum": formation.table_weight_sum,
                "parsed_rows": formation.parsed_rows,
                "investable_holding_count": len(formation.target_weights),
                "selected_table_index": formation.selected_table_index,
                "selected_table_count": formation.selected_table_count,
                "corrected_tickers": formation.corrected_tickers,
                "dropped_labels": formation.dropped_labels,
                "dropped_unknown_tickers": formation.dropped_unknown_tickers,
                "source_path": formation.source_path,
                "experiment_id": formation.experiment_id,
            }
        )
    return formations, pd.DataFrame(audit_rows).sort_values(
        ["series_type", "archive", "mode", "agent", "formation_end"]
    )


def build_ensemble_formations(formations: Sequence[Formation]) -> List[Formation]:
    grouped: Dict[Tuple[str, str, str, pd.Timestamp], List[Formation]] = defaultdict(list)
    for formation in formations:
        if formation.agent == "ensemble":
            continue
        grouped[(formation.series_type, formation.archive, formation.mode, formation.formation_end)].append(formation)
    ensembles: List[Formation] = []
    for (series_type, archive, mode, formation_end), sleeves in sorted(grouped.items(), key=lambda x: x[0]):
        agents = {s.agent for s in sleeves}
        if agents != set(AGENTS):
            continue
        combined: Dict[str, float] = defaultdict(float)
        for sleeve in sleeves:
            for ticker, weight in sleeve.target_weights.items():
                combined[ticker] += weight / len(AGENTS)
        candidate_id = (
            f"replay__{archive}__{mode}__ensemble"
            if series_type == "replay"
            else f"authors__{archive}__ensemble"
        )
        ensembles.append(
            Formation(
                candidate_id=candidate_id,
                series_type=series_type,
                archive=archive,
                agent="ensemble",
                mode=mode,
                formation_end=formation_end,
                target_weights=dict(sorted(combined.items())),
                raw_weight_sum=100.0,
                table_weight_sum=100.0,
                parsed_rows=sum(s.parsed_rows for s in sleeves),
                selected_table_index=0,
                selected_table_count=len(sleeves),
                corrected_tickers=";".join(sorted(set(filter(None, (s.corrected_tickers for s in sleeves))))),
                dropped_labels=";".join(filter(None, (s.dropped_labels for s in sleeves))),
                dropped_unknown_tickers=";".join(filter(None, (s.dropped_unknown_tickers for s in sleeves))),
                source_path="equal-weight combination of five sleeve formation portfolios",
                experiment_id="derived-equal-weight-ensemble",
            )
        )
    return ensembles


def value_positions(shares: Mapping[str, float], price_row: pd.Series) -> Tuple[float, Dict[str, float]]:
    values: Dict[str, float] = {}
    for ticker, quantity in shares.items():
        price = float(price_row.get(ticker, np.nan))
        if np.isfinite(price) and price > 0:
            values[ticker] = quantity * price
    return float(sum(values.values())), values


def backtest_candidate(
    candidate_formations: Sequence[Formation], prices: pd.DataFrame, cost_bps: float
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    formations = sorted(candidate_formations, key=lambda x: x.formation_end)
    if not formations:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    dates = prices.index
    events: Dict[pd.Timestamp, Formation] = {}
    event_audit: List[Dict[str, Any]] = []
    for formation in formations:
        after = dates[dates > formation.formation_end]
        execution = pd.Timestamp(after[0]) if len(after) else pd.NaT
        if pd.notna(execution):
            events[execution] = formation
        event_audit.append(
            {
                "candidate_id": formation.candidate_id,
                "formation_end": formation.formation_end,
                "execution_date": execution,
                "scheduled_realization_end": formation.formation_end + pd.offsets.QuarterEnd(1),
            }
        )
    valid_events = sorted(events)
    if not valid_events:
        return pd.DataFrame(), pd.DataFrame(event_audit), pd.DataFrame()
    start = valid_events[0]
    scheduled_end = max(f.formation_end + pd.offsets.QuarterEnd(1) for f in formations)
    end = min(pd.Timestamp(dates.max()), scheduled_end)
    active_dates = dates[(dates >= start) & (dates <= end)]
    gross_shares: Dict[str, float] = {}
    net_shares: Dict[str, float] = {}
    gross_cash = 1.0
    net_cash = 1.0
    daily_rows: List[Dict[str, Any]] = []
    turnover_rows: List[Dict[str, Any]] = []
    active_formation: Optional[Formation] = None
    last_event_turnover = 0.0
    last_event_cost = 0.0
    for date in active_dates:
        price_row = prices.loc[date]
        gross_security_value, gross_values = value_positions(gross_shares, price_row)
        net_security_value, _ = value_positions(net_shares, price_row)
        gross_nav_pre = gross_cash + gross_security_value
        net_nav_pre = net_cash + net_security_value
        event_turnover = 0.0
        event_cost = 0.0
        event_missing_weight = 0.0
        event_failure = ""
        if date in events:
            active_formation = events[date]
            valid_target = {
                ticker: weight
                for ticker, weight in active_formation.target_weights.items()
                if ticker in prices.columns
                and np.isfinite(float(price_row.get(ticker, np.nan)))
                and float(price_row.get(ticker, np.nan)) > 0
            }
            event_missing_weight = 1.0 - float(sum(valid_target.values()))
            if valid_target:
                total = float(sum(valid_target.values()))
                valid_target = {ticker: weight / total for ticker, weight in valid_target.items()}
                current_weights = {
                    ticker: value / gross_nav_pre
                    for ticker, value in gross_values.items()
                    if gross_nav_pre > 0
                }
                event_turnover = float(
                    sum(
                        abs(valid_target.get(ticker, 0.0) - current_weights.get(ticker, 0.0))
                        for ticker in set(valid_target) | set(current_weights)
                    )
                )
                gross_shares = {
                    ticker: gross_nav_pre * weight / float(price_row[ticker])
                    for ticker, weight in valid_target.items()
                }
                gross_cash = 0.0
                event_cost = (cost_bps / 10000.0) * event_turnover * net_nav_pre
                net_investable = max(net_nav_pre - event_cost, 0.0)
                net_shares = {
                    ticker: net_investable * weight / float(price_row[ticker])
                    for ticker, weight in valid_target.items()
                }
                net_cash = 0.0
            else:
                event_failure = "no_valid_execution_prices"
            last_event_turnover = event_turnover
            last_event_cost = event_cost
            turnover_rows.append(
                {
                    "candidate_id": active_formation.candidate_id,
                    "series_type": active_formation.series_type,
                    "archive": active_formation.archive,
                    "agent": active_formation.agent,
                    "mode": active_formation.mode,
                    "formation_end": active_formation.formation_end,
                    "execution_date": date,
                    "scheduled_realization_end": active_formation.formation_end + pd.offsets.QuarterEnd(1),
                    "traded_notional": event_turnover,
                    "transaction_cost_bps": cost_bps,
                    "transaction_cost_nav": event_cost,
                    "missing_execution_weight": max(event_missing_weight, 0.0),
                    "failure_flag": event_failure,
                }
            )
        gross_security_value, _ = value_positions(gross_shares, price_row)
        net_security_value, _ = value_positions(net_shares, price_row)
        daily_rows.append(
            {
                "date": date,
                "gross_nav": gross_cash + gross_security_value,
                "net_costed_nav": net_cash + net_security_value,
                "candidate_id": formations[0].candidate_id,
                "series_type": formations[0].series_type,
                "archive": formations[0].archive,
                "agent": formations[0].agent,
                "mode": formations[0].mode,
                "active_formation_end": active_formation.formation_end if active_formation else pd.NaT,
                "event_turnover": event_turnover,
                "event_transaction_cost_nav": event_cost,
                "last_rebalance_turnover": last_event_turnover,
                "last_rebalance_cost_nav": last_event_cost,
                "event_missing_execution_weight": event_missing_weight,
                "event_failure_flag": event_failure,
            }
        )
    daily = pd.DataFrame(daily_rows)
    daily["realization_month"] = daily["date"] + pd.offsets.MonthEnd(0)
    monthly = daily.sort_values("date").groupby("realization_month", as_index=False).tail(1).copy()
    monthly = monthly.sort_values("realization_month").reset_index(drop=True)
    prior_gross = monthly["gross_nav"].shift(1).fillna(1.0)
    prior_net = monthly["net_costed_nav"].shift(1).fillna(1.0)
    monthly["gross_return"] = monthly["gross_nav"] / prior_gross - 1.0
    monthly["net_costed_return"] = monthly["net_costed_nav"] / prior_net - 1.0
    turnover_by_month = (
        pd.DataFrame(turnover_rows)
        .assign(realization_month=lambda x: pd.to_datetime(x["execution_date"]) + pd.offsets.MonthEnd(0))
        .groupby("realization_month", as_index=False)
        .agg(
            traded_notional=("traded_notional", "sum"),
            transaction_cost_nav=("transaction_cost_nav", "sum"),
            missing_execution_weight=("missing_execution_weight", "max"),
            failure_flag=("failure_flag", lambda x: ";".join(v for v in x if v)),
        )
    )
    monthly = monthly.merge(turnover_by_month, on="realization_month", how="left")
    monthly["traded_notional"] = monthly["traded_notional"].fillna(0.0)
    monthly["transaction_cost_nav"] = monthly["transaction_cost_nav"].fillna(0.0)
    monthly["missing_execution_weight"] = monthly["missing_execution_weight"].fillna(0.0)
    monthly["failure_flag"] = monthly["failure_flag"].fillna("")
    price_max = pd.Timestamp(prices.index.max())
    price_max_period = price_max.to_period("M")
    monthly["month_complete"] = monthly["realization_month"].dt.to_period("M") < price_max_period
    monthly["scheduled_complete"] = monthly["realization_month"] <= scheduled_end
    monthly["analysis_eligible"] = (
        monthly["month_complete"]
        & monthly["scheduled_complete"]
        & monthly["failure_flag"].eq("")
        & monthly["gross_return"].notna()
        & monthly["net_costed_return"].notna()
    )
    monthly["formation_month"] = pd.to_datetime(monthly["active_formation_end"]) + pd.offsets.MonthEnd(0)
    monthly["candidate_return_kind"] = "long_only_total_return"
    monthly["cost_status"] = f"{cost_bps:g}bp_times_one_way_traded_notional"
    keep = [
        "candidate_id", "series_type", "archive", "agent", "mode", "formation_month",
        "realization_month", "date", "gross_return", "traded_notional", "net_costed_return",
        "gross_nav", "net_costed_nav", "transaction_cost_nav", "missing_execution_weight",
        "month_complete", "scheduled_complete", "analysis_eligible", "failure_flag",
        "candidate_return_kind", "cost_status",
    ]
    return monthly[keep], pd.DataFrame(event_audit), pd.DataFrame(turnover_rows)


def run_all_backtests(
    formations: Sequence[Formation], prices: pd.DataFrame, cost_bps: float
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    by_candidate: Dict[str, List[Formation]] = defaultdict(list)
    for formation in formations:
        by_candidate[formation.candidate_id].append(formation)
    monthly_parts: List[pd.DataFrame] = []
    event_parts: List[pd.DataFrame] = []
    turnover_parts: List[pd.DataFrame] = []
    holdings_rows: List[Dict[str, Any]] = []
    for candidate_id, candidate_formations in sorted(by_candidate.items()):
        monthly, events, turnover = backtest_candidate(candidate_formations, prices, cost_bps)
        monthly_parts.append(monthly)
        event_parts.append(events)
        turnover_parts.append(turnover)
        for formation in candidate_formations:
            for ticker, weight in formation.target_weights.items():
                holdings_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "series_type": formation.series_type,
                        "archive": formation.archive,
                        "agent": formation.agent,
                        "mode": formation.mode,
                        "formation_month": formation.formation_end + pd.offsets.MonthEnd(0),
                        "ticker": ticker,
                        "target_weight": weight,
                    }
                )
    return (
        pd.concat(monthly_parts, ignore_index=True),
        pd.concat(event_parts, ignore_index=True),
        pd.concat(turnover_parts, ignore_index=True),
        pd.DataFrame(holdings_rows),
    )


def build_nasdaq_market(prices: pd.DataFrame, caps: pd.DataFrame) -> pd.DataFrame:
    month_ends = prices.groupby(prices.index.to_period("M")).tail(1)
    cap_month_ends = caps.reindex(month_ends.index).ffill()
    returns = month_ends.pct_change()
    prior_caps = cap_month_ends.shift(1)
    rows: List[Dict[str, Any]] = []
    for date in month_ends.index[1:]:
        ret = returns.loc[date].astype("float64")
        cap = prior_caps.loc[date].astype("float64")
        ok = ret.notna() & cap.notna() & cap.gt(0)
        value = float(np.average(ret[ok], weights=cap[ok])) if int(ok.sum()) >= 10 else float("nan")
        rows.append(
            {
                "month": pd.Timestamp(date) + pd.offsets.MonthEnd(0),
                "nasdaq100_source_universe_market": value,
                "nasdaq100_market_constituent_count": int(ok.sum()),
            }
        )
    return pd.DataFrame(rows)


def construct_factor_years(
    usa_path: Path,
    membership: pd.DataFrame,
    factor_columns: Sequence[str],
    start_year: int,
    end_year: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    char_columns = [column.removeprefix("char__") for column in factor_columns if column.startswith("char__")]
    rows: List[Dict[str, Any]] = []
    audit_rows: List[Dict[str, Any]] = []
    usecols = ["permno", "permco", "eom", "ret_exc_lead1m", *char_columns]
    for year in range(start_year, end_year + 1):
        raw = pd.read_parquet(
            usa_path,
            columns=usecols,
            filters=[
                ("eom", ">=", pd.Timestamp(f"{year}-01-01")),
                ("eom", "<=", pd.Timestamp(f"{year}-12-31")),
            ],
        )
        if raw.empty:
            continue
        raw = raw.rename(columns={"eom": "month"})
        raw["month"] = pd.to_datetime(raw["month"]) + pd.offsets.MonthEnd(0)
        raw["permno"] = pd.to_numeric(raw["permno"], errors="coerce")
        raw["permco"] = pd.to_numeric(raw["permco"], errors="coerce")
        raw["ret_exc_lead1m"] = pd.to_numeric(raw["ret_exc_lead1m"], errors="coerce")
        raw = raw.dropna(subset=["permno", "permco", "month", "ret_exc_lead1m"]).copy()
        raw["permno"] = raw["permno"].astype("int64")
        raw["permco"] = raw["permco"].astype("int64")
        mem_y = membership[membership["month"].dt.year.eq(year)]
        raw = raw.merge(
            mem_y[["month", "permco", "market_cap_rank", "market_cap"]],
            on=["month", "permco"],
            how="inner",
            validate="m:1",
        ).drop_duplicates(["permno", "month"], keep="first")
        for month, group in raw.groupby("month", sort=True):
            group = group.sort_values("permno", kind="mergesort").reset_index(drop=True)
            ret = pd.to_numeric(group["ret_exc_lead1m"], errors="coerce").to_numpy(dtype="float64")
            ret_ok = np.isfinite(ret)
            if int(ret_ok.sum()) < 10:
                continue
            ret = ret[ret_ok]
            group = group.loc[ret_ok].reset_index(drop=True)
            cap = pd.to_numeric(group["market_cap"], errors="coerce").to_numpy(dtype="float64")
            cap_ok = np.isfinite(cap) & (cap > 0)
            market = float("nan")
            if int(cap_ok.sum()) >= 10:
                market = float(np.dot(cap[cap_ok] / float(cap[cap_ok].sum()), ret[cap_ok]))
            chars = group[char_columns].apply(pd.to_numeric, errors="coerce")
            chars = chars.fillna(chars.mean(axis=0, skipna=True)).fillna(0.0)
            counts = chars.notna().sum(axis=0).astype("float64")
            ranks = chars.rank(axis=0, method="average")
            standardized = (ranks - 1.0).divide((counts - 1.0).replace(0.0, np.nan), axis=1) - 0.5
            signals = standardized.fillna(0.0).to_numpy(dtype="float64", copy=True)
            signals -= signals.mean(axis=0, keepdims=True)
            gross = np.abs(signals).sum(axis=0)
            weights = np.divide(signals, gross, out=np.zeros_like(signals), where=gross > 0)
            factor_values = ret @ weights
            row: Dict[str, Any] = {"month": pd.Timestamp(month), "capm_top1000_mkt": market}
            row.update(
                {
                    f"char__{characteristic}": float(value) if np.isfinite(value) else float("nan")
                    for characteristic, value in zip(char_columns, factor_values)
                }
            )
            rows.append(row)
            audit_rows.append(
                {
                    "month": pd.Timestamp(month),
                    "factor_panel_permcos": int(group["permco"].nunique()),
                    "factor_panel_permnos": int(group["permno"].nunique()),
                    "factor_panel_rows": int(len(group)),
                    "factor_panel_market_cap_sum": float(pd.to_numeric(group["market_cap"], errors="coerce").sum()),
                    "factor_panel_source": "reconstructed_exact_same_universe_method",
                }
            )
    return pd.DataFrame(rows).sort_values("month"), pd.DataFrame(audit_rows).sort_values("month")


def build_extended_factor_panel(
    external_path: Path, usa_path: Path, membership_path: Path
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    external = pd.read_csv(external_path)
    external["month"] = pd.to_datetime(external["month"]) + pd.offsets.MonthEnd(0)
    factor_columns = ["capm_top1000_mkt", *[c for c in external if c.startswith("char__")]]
    if len(factor_columns) != 133:
        raise ValueError(f"Expected market plus 132 JKP factors, found {len(factor_columns)}")
    membership = pd.read_csv(membership_path)
    membership["month"] = pd.to_datetime(membership["month"]) + pd.offsets.MonthEnd(0)
    membership["permco"] = pd.to_numeric(membership["permco"], errors="coerce")
    membership["market_cap_rank"] = pd.to_numeric(membership["market_cap_rank"], errors="coerce")
    membership["market_cap"] = pd.to_numeric(membership["market_cap"], errors="coerce")
    membership = membership.dropna(subset=["month", "permco", "market_cap_rank"])
    membership["permco"] = membership["permco"].astype("int64")
    membership = membership[membership["market_cap_rank"].le(1000)].drop_duplicates(["month", "permco"])
    reconstruction, audit = construct_factor_years(
        usa_path=usa_path,
        membership=membership,
        factor_columns=factor_columns,
        start_year=2021,
        end_year=int(membership["month"].dt.year.max()),
    )
    overlap = external[external["month"].dt.year.eq(2021)][["month", *factor_columns]].merge(
        reconstruction[reconstruction["month"].dt.year.eq(2021)][["month", *factor_columns]],
        on="month",
        suffixes=("_published", "_rebuilt"),
        validate="1:1",
    )
    scaling_by_factor: Dict[str, float] = {}
    for column in factor_columns:
        published_values = pd.to_numeric(overlap[f"{column}_published"], errors="coerce")
        rebuilt_values = pd.to_numeric(overlap[f"{column}_rebuilt"], errors="coerce")
        ok = published_values.notna() & rebuilt_values.notna()
        denominator = float(np.dot(rebuilt_values[ok], rebuilt_values[ok]))
        if denominator <= 0:
            raise ValueError(f"Cannot calibrate published volatility scale for {column}")
        scaling_by_factor[column] = float(np.dot(rebuilt_values[ok], published_values[ok]) / denominator)
    scaled_reconstruction = reconstruction.copy()
    for column in factor_columns:
        scaled_reconstruction[column] = scaled_reconstruction[column] * scaling_by_factor[column]
    scaled_overlap = external[external["month"].dt.year.eq(2021)][["month", *factor_columns]].merge(
        scaled_reconstruction[scaled_reconstruction["month"].dt.year.eq(2021)][["month", *factor_columns]],
        on="month",
        suffixes=("_published", "_rebuilt"),
        validate="1:1",
    )
    differences: List[float] = []
    correlations: List[float] = []
    for column in factor_columns:
        left = pd.to_numeric(scaled_overlap[f"{column}_published"], errors="coerce")
        right = pd.to_numeric(scaled_overlap[f"{column}_rebuilt"], errors="coerce")
        differences.extend(np.abs(left - right).dropna().tolist())
        if left.notna().sum() >= 3 and right.notna().sum() >= 3:
            correlations.append(float(left.corr(right)))
    max_external_month = pd.Timestamp(external["month"].max())
    extension = scaled_reconstruction[scaled_reconstruction["month"].gt(max_external_month)][["month", *factor_columns]]
    extended = pd.concat([external[["month", *factor_columns]], extension], ignore_index=True)
    extended = extended.drop_duplicates("month", keep="first").sort_values("month").reset_index(drop=True)
    meta = {
        "factor_order": factor_columns,
        "published_start": str(external["month"].min().date()),
        "published_end": str(external["month"].max().date()),
        "extended_end": str(extended["month"].max().date()),
        "extension_months": int(len(extension)),
        "validation_overlap_months": int(len(overlap)),
        "validation_max_absolute_difference": float(max(differences)) if differences else None,
        "validation_median_factor_correlation": float(np.nanmedian(correlations)) if correlations else None,
        "method": "Exact KnowledgeTemplate top-1000 permco membership, cap-weight market, unit-gross centered cross-sectional rank characteristic factors, and published factor-specific 7%-annual-volatility scaling",
        "factor_scaling_policy": "Factor-specific through-origin scale calibrated against the published 2021 overlap; equivalent to the published 7%-annual-volatility normalization",
        "scaling_by_factor": scaling_by_factor,
        "month_label": "formation month; next-month excess returns; shift forward one month for realization",
    }
    return extended, audit, meta


def load_proxy_paths(proxy_root: Path) -> pd.DataFrame:
    parts: List[pd.DataFrame] = []
    for proxy_id in PROXY_MAP.values():
        path = proxy_root / f"candidate_returns_{proxy_id}.csv"
        frame = pd.read_csv(path)
        frame["formation_month"] = pd.to_datetime(frame["month"]) + pd.offsets.MonthEnd(0)
        frame["realization_month"] = frame["formation_month"] + pd.offsets.MonthEnd(1)
        frame["candidate_id"] = f"jkp_proxy__{proxy_id}"
        frame["series_type"] = "jkp_proxy"
        frame["archive"] = "jkp_1999_2024"
        frame["agent"] = next(key for key, value in PROXY_MAP.items() if value == proxy_id)
        frame["mode"] = "motif-proxy"
        frame["gross_return"] = pd.to_numeric(frame["candidate_return"], errors="coerce")
        frame["traded_notional"] = np.nan
        frame["net_costed_return"] = np.nan
        frame["gross_nav"] = (1.0 + frame["gross_return"].fillna(0.0)).cumprod()
        frame["net_costed_nav"] = np.nan
        frame["transaction_cost_nav"] = np.nan
        frame["missing_execution_weight"] = np.nan
        frame["month_complete"] = True
        frame["scheduled_complete"] = True
        frame["analysis_eligible"] = frame["gross_return"].notna()
        frame["failure_flag"] = ""
        frame["candidate_return_kind"] = "long_short_excess_return_proxy"
        frame["cost_status"] = "unavailable_no_published_holdings_or_turnover"
        frame["date"] = frame["realization_month"]
        parts.append(frame)
    columns = [
        "candidate_id", "series_type", "archive", "agent", "mode", "formation_month",
        "realization_month", "date", "gross_return", "traded_notional", "net_costed_return",
        "gross_nav", "net_costed_nav", "transaction_cost_nav", "missing_execution_weight",
        "month_complete", "scheduled_complete", "analysis_eligible", "failure_flag",
        "candidate_return_kind", "cost_status",
    ]
    return pd.concat(parts, ignore_index=True)[columns]


def newey_west_covariance(design: np.ndarray, residuals: np.ndarray, lag: int) -> np.ndarray:
    n, k = design.shape
    bread = np.linalg.pinv(design.T @ design, rcond=1e-12)
    scores = design * residuals.reshape(-1, 1)
    meat = scores.T @ scores
    for offset in range(1, min(lag, n - 1) + 1):
        weight = 1.0 - offset / (lag + 1.0)
        cross = scores[offset:].T @ scores[:-offset]
        meat += weight * (cross + cross.T)
    covariance = bread @ meat @ bread
    rank = int(np.linalg.matrix_rank(design))
    if n > rank:
        covariance *= n / (n - rank)
    return covariance


def ols_alpha(
    frame: pd.DataFrame,
    candidate_id: str,
    benchmark: str,
    factor_columns: Sequence[str],
    minimum_extra_df: int = 8,
) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    columns = ["month", "y", *factor_columns]
    sample = frame[columns].replace([np.inf, -np.inf], np.nan).dropna().sort_values("month")
    n = len(sample)
    k = len(factor_columns)
    base = {
        "candidate_id": candidate_id,
        "benchmark": benchmark,
        "n_months": n,
        "n_factors": k,
        "sample_start": sample["month"].min() if n else pd.NaT,
        "sample_end": sample["month"].max() if n else pd.NaT,
    }
    if n < k + 1 + minimum_extra_df:
        return (
            {
                **base,
                "status": "unidentified_or_insufficient_degrees_of_freedom",
                "alpha_monthly": np.nan,
                "alpha_annualized": np.nan,
                "alpha_tstat_hac": np.nan,
                "alpha_pvalue": np.nan,
                "r_squared": np.nan,
                "residual_monthly_volatility": np.nan,
                "factor_rank": np.nan,
            },
            pd.DataFrame(),
            pd.DataFrame(),
        )
    y = sample["y"].to_numpy(dtype="float64")
    factors = sample[list(factor_columns)].to_numpy(dtype="float64") if k else np.empty((n, 0))
    design = np.column_stack([np.ones(n), factors])
    rank = int(np.linalg.matrix_rank(design))
    beta = np.linalg.pinv(design, rcond=1e-12) @ y
    fitted = design @ beta
    residual = y - fitted
    covariance = newey_west_covariance(design, residual, lag=min(3, n - 1))
    se = float(math.sqrt(max(float(covariance[0, 0]), 0.0)))
    tstat = float(beta[0] / se) if se > 0 else float("nan")
    dof = max(n - rank, 1)
    pvalue = float(2.0 * stats.t.sf(abs(tstat), df=dof)) if np.isfinite(tstat) else float("nan")
    tss = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(residual**2)) / tss if tss > 0 else float("nan")
    result = {
        **base,
        "status": "identified_ols" if rank == k + 1 else "identified_pseudoinverse_rank_deficient",
        "alpha_monthly": float(beta[0]),
        "alpha_annualized": float(beta[0] * 12.0),
        "alpha_tstat_hac": tstat,
        "alpha_pvalue": pvalue,
        "r_squared": r2,
        "residual_monthly_volatility": float(np.std(residual, ddof=1)),
        "factor_rank": rank,
    }
    residuals = pd.DataFrame(
        {
            "candidate_id": candidate_id,
            "benchmark": benchmark,
            "month": sample["month"].to_numpy(),
            "candidate_excess_return": y,
            "factor_fitted_value": fitted - beta[0],
            "fitted_value_including_alpha": fitted,
            "residual": residual,
            "alpha_monthly": beta[0],
        }
    )
    loadings = pd.DataFrame(
        {
            "candidate_id": candidate_id,
            "benchmark": benchmark,
            "factor": ["intercept", *factor_columns],
            "loading": beta,
        }
    )
    return result, residuals, loadings


def prepare_pca_factors(
    formation_factors: pd.DataFrame, factor_columns: Sequence[str], n_components: int = 5
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    primary_chars = set(PRIMARY_FACTOR_COLUMNS[1:])
    remaining = [column for column in factor_columns if column.startswith("char__") and column not in primary_chars]
    train = formation_factors[formation_factors["month"].le(pd.Timestamp("2021-12-31"))].dropna(
        subset=remaining
    )
    means = train[remaining].mean(axis=0)
    stds = train[remaining].std(axis=0, ddof=1).replace(0.0, np.nan)
    standardized = ((train[remaining] - means) / stds).fillna(0.0).to_numpy(dtype="float64")
    _, singular_values, vt = np.linalg.svd(standardized, full_matrices=False)
    components = vt[:n_components]
    all_standardized = ((formation_factors[remaining] - means) / stds).fillna(0.0).to_numpy(dtype="float64")
    scores = all_standardized @ components.T
    out = formation_factors[["month", *PRIMARY_FACTOR_COLUMNS]].copy()
    pca_columns = []
    for index in range(n_components):
        name = f"jkp132_pre2022_pc{index + 1}"
        out[name] = scores[:, index]
        pca_columns.append(name)
    loadings = pd.DataFrame(
        {
            "factor": np.repeat(remaining, n_components),
            "component": np.tile(pca_columns, len(remaining)),
            "loading": components.T.reshape(-1),
        }
    )
    explained = singular_values**2
    meta = {
        "training_start": str(train["month"].min().date()),
        "training_end": str(train["month"].max().date()),
        "training_months": int(len(train)),
        "n_input_characteristics": len(remaining),
        "n_components": n_components,
        "explained_variance_ratio_first_components": (explained[:n_components] / explained.sum()).tolist(),
        "outcome_blind": True,
    }
    return out, loadings, meta


def ridge_fit_centered(x: np.ndarray, y: np.ndarray, penalty: float) -> Tuple[np.ndarray, float]:
    x_mean = x.mean(axis=0)
    y_mean = float(y.mean())
    xc = x - x_mean
    yc = y - y_mean
    n, p = xc.shape
    if p > n:
        system = xc @ xc.T + penalty * np.eye(n)
        beta = xc.T @ np.linalg.solve(system, yc)
    else:
        system = xc.T @ xc + penalty * np.eye(p)
        beta = np.linalg.solve(system, xc.T @ yc)
    intercept = y_mean - float(x_mean @ beta)
    return beta, intercept


def nested_lomo_ridge(
    frame: pd.DataFrame,
    candidate_id: str,
    factor_columns: Sequence[str],
    pretrain_scale: pd.Series,
) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    sample = frame[["month", "y", *factor_columns]].replace([np.inf, -np.inf], np.nan).dropna().sort_values("month")
    n = len(sample)
    base = {
        "candidate_id": candidate_id,
        "benchmark": "jkp132_full_lomo_ridge_exploratory",
        "n_months": n,
        "n_factors": len(factor_columns),
        "sample_start": sample["month"].min() if n else pd.NaT,
        "sample_end": sample["month"].max() if n else pd.NaT,
    }
    if n < 12:
        return (
            {
                **base,
                "status": "insufficient_months_for_lomo_ridge",
                "alpha_monthly": np.nan,
                "alpha_annualized": np.nan,
                "alpha_tstat_hac": np.nan,
                "alpha_pvalue": np.nan,
                "r_squared": np.nan,
                "residual_monthly_volatility": np.nan,
                "factor_rank": np.nan,
                "modal_ridge_penalty": np.nan,
            },
            pd.DataFrame(),
            pd.DataFrame(),
        )
    y = sample["y"].to_numpy(dtype="float64")
    raw_x = sample[list(factor_columns)].to_numpy(dtype="float64")
    scale = pretrain_scale.reindex(factor_columns).replace(0.0, np.nan).fillna(1.0).to_numpy(dtype="float64")
    x = raw_x / scale
    factor_fitted = np.full(n, np.nan)
    total_fitted = np.full(n, np.nan)
    selected_penalties = np.full(n, np.nan)
    loading_rows: List[Dict[str, Any]] = []
    all_indices = np.arange(n)
    for outer in range(n):
        training = all_indices[all_indices != outer]
        validation_errors: Dict[float, float] = {}
        for penalty in RIDGE_GRID:
            errors: List[float] = []
            for inner in training:
                inner_training = training[training != inner]
                beta_inner, intercept_inner = ridge_fit_centered(x[inner_training], y[inner_training], penalty)
                prediction = intercept_inner + float(x[inner] @ beta_inner)
                errors.append((float(y[inner]) - prediction) ** 2)
            validation_errors[penalty] = float(np.mean(errors))
        selected = min(RIDGE_GRID, key=lambda value: (validation_errors[value], value))
        beta_scaled, intercept = ridge_fit_centered(x[training], y[training], selected)
        beta_raw = beta_scaled / scale
        factor_fitted[outer] = float(raw_x[outer] @ beta_raw)
        total_fitted[outer] = intercept + factor_fitted[outer]
        selected_penalties[outer] = selected
        for factor, loading in zip(factor_columns, beta_raw):
            loading_rows.append(
                {
                    "candidate_id": candidate_id,
                    "benchmark": "jkp132_full_lomo_ridge_exploratory",
                    "month": sample.iloc[outer]["month"],
                    "selected_ridge_penalty": selected,
                    "factor": factor,
                    "loading": float(loading),
                }
            )
    alpha_residual = y - factor_fitted
    design = np.ones((n, 1), dtype="float64")
    covariance = newey_west_covariance(design, alpha_residual - alpha_residual.mean(), lag=min(3, n - 1))
    se = float(math.sqrt(max(float(covariance[0, 0]), 0.0)))
    alpha = float(alpha_residual.mean())
    tstat = alpha / se if se > 0 else float("nan")
    pvalue = float(2.0 * stats.t.sf(abs(tstat), df=max(n - 1, 1))) if np.isfinite(tstat) else float("nan")
    prediction_error = y - total_fitted
    tss = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(prediction_error**2)) / tss if tss > 0 else float("nan")
    mode_penalty = Counter(selected_penalties.tolist()).most_common(1)[0][0]
    result = {
        **base,
        "status": "exploratory_nested_lomo_ridge_noncausal_short_sample",
        "alpha_monthly": alpha,
        "alpha_annualized": alpha * 12.0,
        "alpha_tstat_hac": tstat,
        "alpha_pvalue": pvalue,
        "r_squared": r2,
        "residual_monthly_volatility": float(np.std(alpha_residual, ddof=1)),
        "factor_rank": int(np.linalg.matrix_rank(raw_x)),
        "modal_ridge_penalty": mode_penalty,
    }
    residuals = pd.DataFrame(
        {
            "candidate_id": candidate_id,
            "benchmark": "jkp132_full_lomo_ridge_exploratory",
            "month": sample["month"].to_numpy(),
            "candidate_excess_return": y,
            "factor_fitted_value": factor_fitted,
            "fitted_value_including_training_alpha": total_fitted,
            "residual": alpha_residual,
            "prediction_error": prediction_error,
            "selected_ridge_penalty": selected_penalties,
        }
    )
    return result, residuals, pd.DataFrame(loading_rows)


def holm_adjust(pvalues: pd.Series) -> pd.Series:
    valid = pvalues.dropna().sort_values()
    adjusted = pd.Series(np.nan, index=pvalues.index, dtype="float64")
    running = 0.0
    m = len(valid)
    for rank, (index, value) in enumerate(valid.items()):
        candidate = min((m - rank) * float(value), 1.0)
        running = max(running, candidate)
        adjusted.loc[index] = running
    return adjusted


def candidate_regression_frame(
    candidate_rows: pd.DataFrame,
    factor_realization: pd.DataFrame,
    nasdaq_market: pd.DataFrame,
    risk_free: pd.DataFrame,
    pca_realization: pd.DataFrame,
) -> pd.DataFrame:
    rows = candidate_rows[candidate_rows["analysis_eligible"].astype(bool)].copy()
    rows = rows.rename(columns={"realization_month": "month"})
    official_ff_columns = [column for column in OFFICIAL_FF_FACTOR_COLUMNS if column in risk_free]
    rows = rows.merge(
        risk_free[["month", "RF", *official_ff_columns]], on="month", how="left", validate="m:1"
    )
    series_type = str(rows["series_type"].iloc[0])
    if series_type == "jkp_proxy":
        rows["y"] = pd.to_numeric(rows["gross_return"], errors="coerce")
    else:
        rows["y"] = pd.to_numeric(rows["net_costed_return"], errors="coerce") - rows["RF"]
    rows = rows.merge(factor_realization, on="month", how="left", validate="m:1")
    rows = rows.merge(nasdaq_market, on="month", how="left", validate="m:1")
    rows["nasdaq100_market_excess"] = rows["nasdaq100_source_universe_market"] - rows["RF"]
    # Hold all official-FF and JKP additions to the exact same realization months.
    # The French cache continues three months beyond the reconstructed JKP extension;
    # allowing those extra observations only in the narrow models would confound
    # benchmark expansion with a sample change.
    jkp_overlap = rows["capm_top1000_mkt"].notna()
    rows.loc[~jkp_overlap, official_ff_columns] = np.nan
    pca_columns = [c for c in pca_realization if c.startswith("jkp132_pre2022_pc")]
    rows = rows.merge(pca_realization[["month", *pca_columns]], on="month", how="left", validate="m:1")
    return rows


def run_regressions(
    monthly_paths: pd.DataFrame,
    factor_formation: pd.DataFrame,
    nasdaq_market: pd.DataFrame,
    risk_free: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    factor_columns = ["capm_top1000_mkt", *[c for c in factor_formation if c.startswith("char__")]]
    factor_realization = factor_formation[["month", *factor_columns]].copy()
    factor_realization["month"] = factor_realization["month"] + pd.offsets.MonthEnd(1)
    pca_formation, pca_loadings, pca_meta = prepare_pca_factors(factor_formation, factor_columns)
    pca_realization = pca_formation.copy()
    pca_realization["month"] = pca_realization["month"] + pd.offsets.MonthEnd(1)
    pca_columns = [c for c in pca_realization if c.startswith("jkp132_pre2022_pc")]
    pretrain = factor_formation[factor_formation["month"].le(pd.Timestamp("2021-12-31"))]
    pretrain_scale = pretrain[factor_columns].std(axis=0, ddof=1)
    result_rows: List[Dict[str, Any]] = []
    residual_parts: List[pd.DataFrame] = []
    static_loading_parts: List[pd.DataFrame] = []
    rolling_loading_parts: List[pd.DataFrame] = []
    benchmark_sets = {
        "mean_excess_return": [],
        "nasdaq100_source_universe_capm": ["nasdaq100_market_excess"],
        "jkp_top1000_capm": ["capm_top1000_mkt"],
        "official_ff_capm_matched_jkp_window": ["Mkt-RF"],
        "official_ff3_matched_jkp_window": ["Mkt-RF", "SMB", "HML"],
        "official_ff5_momentum_matched_jkp_window": list(OFFICIAL_FF_FACTOR_COLUMNS),
        "official_ff5_momentum_plus_jkp_bab": [*OFFICIAL_FF_FACTOR_COLUMNS, JKP_BAB_FACTOR],
        "official_ff5_momentum_plus_jkp_lowrisk": [
            *OFFICIAL_FF_FACTOR_COLUMNS,
            *JKP_LOW_RISK_FACTOR_COLUMNS,
        ],
        "jkp_primary_six": list(PRIMARY_FACTOR_COLUMNS),
        "jkp132_compressed_pre2022_pca5": [*PRIMARY_FACTOR_COLUMNS, *pca_columns],
        "jkp132_full_ols": factor_columns,
    }
    for candidate_id, candidate_rows in monthly_paths.groupby("candidate_id", sort=True):
        frame = candidate_regression_frame(
            candidate_rows, factor_realization, nasdaq_market, risk_free, pca_realization
        )
        for benchmark, columns in benchmark_sets.items():
            minimum_extra_df = 8
            if benchmark in ATTRIBUTION_BENCHMARK_ORDER:
                minimum_extra_df = max(
                    minimum_extra_df, ATTRIBUTION_MIN_MONTHS - len(columns) - 1
                )
            result, residuals, loadings = ols_alpha(
                frame,
                candidate_id,
                benchmark,
                columns,
                minimum_extra_df=minimum_extra_df,
            )
            result["series_type"] = str(candidate_rows["series_type"].iloc[0])
            result["archive"] = str(candidate_rows["archive"].iloc[0])
            result["agent"] = str(candidate_rows["agent"].iloc[0])
            result["mode"] = str(candidate_rows["mode"].iloc[0])
            result_rows.append(result)
            if not residuals.empty:
                residual_parts.append(residuals)
            if not loadings.empty:
                static_loading_parts.append(loadings)
        if str(candidate_rows["series_type"].iloc[0]) in {"replay", "authors"}:
            result, residuals, loadings = nested_lomo_ridge(
                frame, candidate_id, factor_columns, pretrain_scale
            )
            result["series_type"] = str(candidate_rows["series_type"].iloc[0])
            result["archive"] = str(candidate_rows["archive"].iloc[0])
            result["agent"] = str(candidate_rows["agent"].iloc[0])
            result["mode"] = str(candidate_rows["mode"].iloc[0])
            result_rows.append(result)
            if not residuals.empty:
                residual_parts.append(residuals)
            if not loadings.empty:
                rolling_loading_parts.append(loadings)
    results = pd.DataFrame(result_rows)
    results["alpha_pvalue_holm_within_benchmark"] = results.groupby("benchmark")["alpha_pvalue"].transform(holm_adjust)
    results["significant_5pct_raw"] = results["alpha_pvalue"].lt(0.05)
    results["significant_5pct_holm"] = results["alpha_pvalue_holm_within_benchmark"].lt(0.05)
    results["alpha_pvalue_holm_replay_family"] = np.nan
    replay_mask = results["series_type"].eq("replay")
    results.loc[replay_mask, "alpha_pvalue_holm_replay_family"] = (
        results.loc[replay_mask]
        .groupby("benchmark")["alpha_pvalue"]
        .transform(holm_adjust)
    )
    results["significant_5pct_holm_replay_family"] = results[
        "alpha_pvalue_holm_replay_family"
    ].lt(0.05)
    return (
        results.sort_values(["benchmark", "series_type", "candidate_id"]),
        pd.concat(residual_parts, ignore_index=True) if residual_parts else pd.DataFrame(),
        pd.concat(static_loading_parts, ignore_index=True) if static_loading_parts else pd.DataFrame(),
        pd.concat(rolling_loading_parts, ignore_index=True) if rolling_loading_parts else pd.DataFrame(),
        {"pca": pca_meta, "factor_order": factor_columns, "ridge_grid": list(RIDGE_GRID), "pca_loadings": pca_loadings},
    )


def build_replay_attribution_outputs(
    regressions: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize the matched official-FF-to-JKP low-risk attribution ladder."""
    replay = regressions[
        regressions["series_type"].eq("replay")
        & regressions["benchmark"].isin(ATTRIBUTION_BENCHMARK_ORDER)
    ].copy()
    replay["benchmark"] = pd.Categorical(
        replay["benchmark"], categories=ATTRIBUTION_BENCHMARK_ORDER, ordered=True
    )
    identified = replay[replay["status"].astype(str).str.startswith("identified")].copy()
    summary_rows: List[Dict[str, Any]] = []
    for benchmark in ATTRIBUTION_BENCHMARK_ORDER:
        group = identified[identified["benchmark"].eq(benchmark)]
        positive = group["alpha_annualized"].gt(0)
        nominal = group["alpha_pvalue"].lt(0.05)
        holm = group["alpha_pvalue_holm_replay_family"].lt(0.05)
        summary_rows.append(
            {
                "benchmark": benchmark,
                "identified_replay_paths": int(len(group)),
                "sample_start": group["sample_start"].min() if len(group) else pd.NaT,
                "sample_end": group["sample_end"].max() if len(group) else pd.NaT,
                "n_months_min": int(group["n_months"].min()) if len(group) else np.nan,
                "n_months_max": int(group["n_months"].max()) if len(group) else np.nan,
                "median_alpha_annualized": float(group["alpha_annualized"].median()) if len(group) else np.nan,
                "positive_alpha_count": int(positive.sum()),
                "nominal_positive_count": int((positive & nominal).sum()),
                "holm_positive_count": int((positive & holm).sum()),
                "nominal_negative_count": int((~positive & nominal).sum()),
                "holm_negative_count": int((~positive & holm).sum()),
            }
        )
    summary = pd.DataFrame(summary_rows)

    base = identified[
        identified["benchmark"].eq("official_ff5_momentum_matched_jkp_window")
    ][["candidate_id", "alpha_annualized"]].rename(
        columns={"alpha_annualized": "ff5_momentum_alpha_annualized"}
    )
    by_candidate = identified.merge(base, on="candidate_id", how="left", validate="m:1")
    by_candidate["alpha_attenuation_from_ff5_momentum"] = (
        by_candidate["ff5_momentum_alpha_annualized"] - by_candidate["alpha_annualized"]
    )
    by_candidate["alpha_change_from_ff5_momentum"] = -by_candidate[
        "alpha_attenuation_from_ff5_momentum"
    ]
    return summary, by_candidate.sort_values(["benchmark", "candidate_id"])


def max_drawdown(returns: pd.Series) -> float:
    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    return float(drawdown.min()) if len(drawdown) else float("nan")


def performance_metrics(returns: pd.Series, excess_returns: pd.Series) -> Dict[str, Any]:
    values = pd.to_numeric(returns, errors="coerce").dropna()
    excess = pd.to_numeric(excess_returns.reindex(values.index), errors="coerce").dropna()
    n = len(values)
    if n < 2:
        return {key: np.nan for key in (
            "n_months", "n_excess_months", "cumulative_return", "annualized_geometric_return", "annualized_arithmetic_return",
            "annualized_volatility", "annualized_sharpe", "max_drawdown", "positive_month_fraction",
        )}
    cumulative = float((1.0 + values).prod() - 1.0)
    annualized_geometric = float((1.0 + cumulative) ** (12.0 / n) - 1.0) if cumulative > -1 else -1.0
    volatility = float(values.std(ddof=1) * math.sqrt(12.0))
    sharpe = float(excess.mean() / excess.std(ddof=1) * math.sqrt(12.0)) if len(excess) > 1 and excess.std(ddof=1) > 0 else np.nan
    return {
        "n_months": n,
        "n_excess_months": int(len(excess)),
        "cumulative_return": cumulative,
        "annualized_geometric_return": annualized_geometric,
        "annualized_arithmetic_return": float(values.mean() * 12.0),
        "annualized_volatility": volatility,
        "annualized_sharpe": sharpe,
        "max_drawdown": max_drawdown(values),
        "positive_month_fraction": float(values.gt(0).mean()),
    }


def summarize_economics(monthly_paths: pd.DataFrame, risk_free: pd.DataFrame) -> pd.DataFrame:
    rf = risk_free.set_index("month")["RF"]
    rows: List[Dict[str, Any]] = []
    for candidate_id, group in monthly_paths.groupby("candidate_id", sort=True):
        eligible = group[group["analysis_eligible"].astype(bool)].sort_values("realization_month").copy()
        series_type = str(group["series_type"].iloc[0])
        bases = [("gross", "gross_return")]
        if series_type != "jkp_proxy":
            bases.append(("net_costed", "net_costed_return"))
        for basis, column in bases:
            values = pd.Series(
                pd.to_numeric(eligible[column], errors="coerce").to_numpy(),
                index=pd.to_datetime(eligible["realization_month"]),
            )
            excess = values if series_type == "jkp_proxy" else values - rf.reindex(values.index)
            metrics = performance_metrics(values, excess)
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "series_type": series_type,
                    "archive": str(group["archive"].iloc[0]),
                    "agent": str(group["agent"].iloc[0]),
                    "mode": str(group["mode"].iloc[0]),
                    "return_basis": basis,
                    "sample_start": values.index.min() if len(values) else pd.NaT,
                    "sample_end": values.index.max() if len(values) else pd.NaT,
                    "mean_monthly_traded_notional": float(pd.to_numeric(eligible["traded_notional"], errors="coerce").mean()),
                    "annualized_traded_notional": float(pd.to_numeric(eligible["traded_notional"], errors="coerce").sum() * 12.0 / len(eligible)) if len(eligible) else np.nan,
                    **metrics,
                }
            )
    summary = pd.DataFrame(rows)
    gross = summary[summary["return_basis"].eq("gross")][["candidate_id", "annualized_geometric_return"]].rename(
        columns={"annualized_geometric_return": "gross_annualized_geometric_return"}
    )
    summary = summary.merge(gross, on="candidate_id", how="left")
    summary["annualized_cost_drag"] = summary["gross_annualized_geometric_return"] - summary["annualized_geometric_return"]
    return summary.sort_values(["series_type", "archive", "mode", "agent", "return_basis"])


def common_sample_metrics(
    left: pd.DataFrame,
    right: pd.DataFrame,
    left_column: str,
    right_column: str,
    risk_free: pd.DataFrame,
    right_is_excess: bool,
) -> Dict[str, Any]:
    merged = left[["realization_month", left_column]].rename(columns={left_column: "left_return"}).merge(
        right[["realization_month", right_column]].rename(columns={right_column: "right_return"}),
        on="realization_month",
        how="inner",
    ).dropna()
    if merged.empty:
        return {"common_months": 0}
    merged = merged.merge(risk_free, left_on="realization_month", right_on="month", how="left")
    left_values = pd.Series(merged["left_return"].to_numpy(), index=merged.index)
    right_values = pd.Series(merged["right_return"].to_numpy(), index=merged.index)
    left_metrics = performance_metrics(left_values, left_values - merged["RF"])
    right_excess = right_values if right_is_excess else right_values - merged["RF"]
    right_metrics = performance_metrics(right_values, right_excess)
    return {
        "common_months": int(len(merged)),
        "common_start": merged["realization_month"].min(),
        "common_end": merged["realization_month"].max(),
        "left_annualized_return": left_metrics["annualized_geometric_return"],
        "right_annualized_return": right_metrics["annualized_geometric_return"],
        "delta_annualized_return": left_metrics["annualized_geometric_return"] - right_metrics["annualized_geometric_return"],
        "left_annualized_sharpe": left_metrics["annualized_sharpe"],
        "right_annualized_sharpe": right_metrics["annualized_sharpe"],
        "delta_annualized_sharpe": left_metrics["annualized_sharpe"] - right_metrics["annualized_sharpe"],
        "return_correlation": float(left_values.corr(right_values)),
    }


def build_economic_comparisons(
    monthly_paths: pd.DataFrame,
    risk_free: pd.DataFrame,
    cost_bps: float,
) -> pd.DataFrame:
    eligible = monthly_paths[monthly_paths["analysis_eligible"].astype(bool)].copy()
    by_id = {candidate_id: group for candidate_id, group in eligible.groupby("candidate_id")}
    rows: List[Dict[str, Any]] = []
    replay_ids = [candidate_id for candidate_id in by_id if candidate_id.startswith("replay__")]
    author_ids = [candidate_id for candidate_id in by_id if candidate_id.startswith("authors__")]
    for left_id in sorted(replay_ids):
        parts = left_id.split("__")
        archive, agent = parts[1], parts[3]
        author_id = f"authors__{archive}__{agent}"
        if author_id in by_id:
            rows.append(
                {
                    "comparison_type": "replay_vs_authors_same_holdout_clock",
                    "left_candidate_id": left_id,
                    "right_candidate_id": author_id,
                    "comparison_limit": (
                        f"Same Nasdaq source universe and corrected clock; both net of "
                        f"{cost_bps:g}bp traded-notional costs."
                    ),
                    **common_sample_metrics(
                        by_id[left_id], by_id[author_id], "net_costed_return", "net_costed_return", risk_free, False
                    ),
                }
            )
        proxy_id = f"jkp_proxy__{PROXY_MAP[agent]}"
        if proxy_id in by_id:
            rows.append(
                {
                    "comparison_type": "replay_vs_jkp_motif_proxy",
                    "left_candidate_id": left_id,
                    "right_candidate_id": proxy_id,
                    "comparison_limit": (
                        f"Replay is long-only Nasdaq portfolio net of {cost_bps:g}bp; proxy is a "
                        "top-1000 long-short excess-return motif with unavailable turnover/costs."
                    ),
                    **common_sample_metrics(
                        by_id[left_id], by_id[proxy_id], "net_costed_return", "gross_return", risk_free, True
                    ),
                }
            )
    for author_id in sorted(author_ids):
        parts = author_id.split("__")
        agent = parts[-1]
        proxy_id = f"jkp_proxy__{PROXY_MAP[agent]}"
        if proxy_id in by_id:
            rows.append(
                {
                    "comparison_type": "authors_vs_jkp_motif_proxy",
                    "left_candidate_id": author_id,
                    "right_candidate_id": proxy_id,
                    "comparison_limit": (
                        f"Authors path is corrected long-only Nasdaq portfolio net of {cost_bps:g}bp; "
                        "proxy is long-short and has unavailable costs."
                    ),
                    **common_sample_metrics(
                        by_id[author_id], by_id[proxy_id], "net_costed_return", "gross_return", risk_free, True
                    ),
                }
            )
    return pd.DataFrame(rows)


def write_report(
    path: Path,
    monthly_paths: pd.DataFrame,
    economics: pd.DataFrame,
    regressions: pd.DataFrame,
    factor_meta: Mapping[str, Any],
    cost_bps: float,
) -> None:
    cost_label = f"{cost_bps:g} bp" if cost_bps == 1.0 else f"{cost_bps:g} bps"
    replay_paths = monthly_paths[monthly_paths["series_type"].eq("replay")]
    eligible_replay = replay_paths[replay_paths["analysis_eligible"].astype(bool)]
    replay_net = economics[
        economics["series_type"].eq("replay") & economics["return_basis"].eq("net_costed")
    ].sort_values("annualized_sharpe", ascending=False)
    top_lines = []
    for _, row in replay_net.head(8).iterrows():
        top_lines.append(
            f"| `{row['candidate_id']}` | {int(row['n_months'])} | {row['annualized_geometric_return']:.2%} | "
            f"{row['annualized_volatility']:.2%} | {row['annualized_sharpe']:.2f} | "
            f"{row['mean_monthly_traded_notional']:.3f} |"
        )
    benchmark_counts = (
        regressions[regressions["series_type"].eq("replay")]
        .groupby("benchmark")
        .agg(
            identified=("status", lambda values: int(sum(str(value).startswith(("identified", "exploratory")) for value in values))),
            nominal_positive=("alpha_pvalue", lambda values: 0),
        )
        .reset_index()
    )
    replay_regressions = regressions[regressions["series_type"].eq("replay")].copy()
    signed_counts = []
    for benchmark, group in replay_regressions.groupby("benchmark", sort=True):
        positive = group["alpha_annualized"].gt(0)
        nominal = group["alpha_pvalue"].lt(0.05)
        holm = group["alpha_pvalue_holm_replay_family"].lt(0.05)
        signed_counts.append(
            {
                "benchmark": benchmark,
                "nominal_positive": int((positive & nominal).sum()),
                "holm_positive": int((positive & holm).sum()),
                "nominal_negative": int((~positive & nominal).sum()),
            }
        )
    signed_counts_frame = pd.DataFrame(signed_counts)
    benchmark_counts = benchmark_counts.drop(columns=["nominal_positive"]).merge(
        signed_counts_frame, on="benchmark", how="left", validate="1:1"
    )
    benchmark_lines = [
        f"| `{row.benchmark}` | {int(row.identified)} | {int(row.nominal_positive)} | "
        f"{int(row.holm_positive)} | {int(row.nominal_negative)} |"
        for row in benchmark_counts.itertuples(index=False)
    ]
    attribution_summary, _ = build_replay_attribution_outputs(regressions)
    attribution_lines = [
        f"| `{row.benchmark}` | {int(row.identified_replay_paths)} | "
        f"{row.median_alpha_annualized:.2%} | {int(row.positive_alpha_count)} | "
        f"{int(row.nominal_positive_count)} | {int(row.holm_positive_count)} |"
        for row in attribution_summary.itertuples(index=False)
        if row.identified_replay_paths
    ]
    text = f"""# GuruAgents prompt-replay performance analysis

Generated `{utc_now()}` from the completed live replay. This package constructs corrected
formation-to-realization return paths for the replayed portfolios and the authors' archived
portfolios, charges transaction costs, measures traded notional, and runs factor tests.

## Return construction

- Formation label: source analysis quarter end.
- Execution: first trading close strictly after formation quarter end.
- Price: `DIV_ADJ_CLOSE`, with `CLOSE_` only as a missing-value fallback.
- Holding rule: buy-and-hold between quarterly rebalances; weights drift with prices.
- Transaction cost: {cost_label} times one-way traded notional, deducted at each rebalance.
- Realization label: calendar month end. The final partial source month is retained with
  `analysis_eligible=false` and is excluded from performance and alpha tests.
- Ticker corrections and dropped rows are explicit in `formation_audit.csv`.

There are {replay_paths['candidate_id'].nunique()} replay strategy paths and
{len(eligible_replay)} eligible replay strategy-month observations. Equal-weight multi-agent
ensembles are formed from the five sleeve target portfolios at each formation date.

## Economic results (replay, net {cost_label})

| Candidate | Months | Ann. return | Ann. vol | Sharpe | Mean monthly traded notional |
|---|---:|---:|---:|---:|---:|
{chr(10).join(top_lines)}

These are short realized histories, not long-run estimates. The `results` archive begins only
in January 2024 realization time; the `results_22_24` archive begins in April 2022.

## Alpha tests

| Benchmark | Identified replay paths | Nominal positive | Holm positive | Nominal negative |
|---|---:|---:|---:|---:|
{chr(10).join(benchmark_lines)}

The market test is shown both for the source Nasdaq-100 file's cap-weighted universe and for
the same-universe JKP top-1000 market. The primary six-factor benchmark is market plus the five
predeclared characteristics in factor order.

### Matched official Fama--French and low-risk attribution

| Benchmark | Identified replay paths | Median annual alpha | Positive | Nominal positive | Holm positive |
|---|---:|---:|---:|---:|---:|
{chr(10).join(attribution_lines)}

This nested ladder uses the exact common realization window shared by the official Kenneth
French factors and the extended JKP panel. `official_ff5_momentum_plus_jkp_bab` adds only the
JKP `betabab_1260d` return to official FF5 plus momentum. The predeclared low-risk block then
adds, in this fixed order, `{', '.join(JKP_LOW_RISK_FACTOR_COLUMNS)}`. This makes attenuation
after the BAB increment directly inspectable; it is not inferred from the generic JKP132 fit.
All five rows require the same {ATTRIBUTION_MIN_MONTHS}-month history, so the short archive is
reported as unavailable throughout the ladder. Holm counts in this report are computed within
the replay family for each benchmark.

An unrestricted market-plus-132-JKP OLS has 134 parameters including the intercept. It is not
identified for a replay path with roughly 13 or 34 monthly observations; those rows are
reported as unavailable rather than silently fit with a pseudoinverse. Two supplementary tests
are therefore included:

1. `jkp132_compressed_pre2022_pca5` freezes five principal components using factor returns only
   through 2021, then estimates replay exposure to the market, primary factors, and those fixed
   components.
2. `jkp132_full_lomo_ridge_exploratory` uses all 133 factors with nested leave-one-month-out
   ridge selection. Monthly penalties and loadings are published, but the test is labelled
   exploratory and noncausal because each fold can use future replay months.

The long-history JKP motif proxies do have enough observations for the full 133-factor OLS;
their direct JKP132 residuals and alpha tests are included for comparison.

## Factor extension and comparison limits

The published broad panel ends {factor_meta['published_end']}. It is extended through
{factor_meta['extended_end']} with the exact same top-1000 membership and unit-gross
cross-sectional-rank construction, validated on {factor_meta['validation_overlap_months']}
overlap months. The maximum reconstructed-versus-published overlap difference is
{factor_meta['validation_max_absolute_difference']:.3g}.

The JKP proxies are long-short top-1000 motif portfolios, while GuruAgents replay and author
paths are long-only portfolios in the source Nasdaq file. Proxy turnover and transaction costs
cannot be reconstructed from the published proxy return files. `economic_comparison.csv`
therefore reports common-month results with this mandate and cost asymmetry explicitly labelled;
it must not be read as a horse race between identical implementations.

## Main artifacts

- `monthly_return_paths.csv`: formation and realization labels, gross return, traded notional,
  {cost_label} net return, NAVs, eligibility, and failure flags.
- `formation_holdings.csv` and `formation_audit.csv`: the actual replay/author target matrices and
  all parsing/correction decisions.
- `factor_panel_extended_formation.csv` and `factor_panel_extended_realization.csv`: exact factor
  order with both clocks.
- `alpha_regressions.csv`, `factor_fitted_and_residuals.csv`, `static_factor_loadings.csv`, and
  `monthly_ridge_loadings.csv`: tests, fitted values, residuals, coefficients, and selected penalties.
- `replay_attribution_ladder.csv` and `replay_attribution_by_candidate.csv`: matched official
  Fama--French, BAB, and broader low-risk attribution results.
- `economic_performance.csv` and `economic_comparison.csv`: common economic metrics and pairwise
  author/replay/proxy comparisons.
- `manifest.json`: hashes, samples, clocks, costs, factor order, software, and licensing cautions.
"""
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    repo_root = Path(__file__).resolve().parents[1]
    project_root = repo_root.parent
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=repo_root / "runs/prompt_replay/guruagents/guruagents_full_20260809T010651Z",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/guruagents_prompt_replay_source"),
    )
    parser.add_argument(
        "--external-factor-panel",
        type=Path,
        default=project_root / "KnowledgeTemplate/performance_analysis/results/current/multifactor_value_add_20260624/benchmark_factor_panel.csv",
    )
    parser.add_argument(
        "--membership",
        type=Path,
        default=project_root / "KnowledgeTemplate/docs/data/dataset_backgrounds/djn_jkp/tables/market_cap_rank/jkp_top_1000_monthly_market_cap_membership.csv",
    )
    parser.add_argument(
        "--usa-path",
        type=Path,
        default=project_root / "jkp-data/data/processed/characteristics/USA.parquet",
    )
    parser.add_argument(
        "--risk-free",
        type=Path,
        default=repo_root / "paper_runs/042_guruagents/results/cache/kenneth_french_monthly_ff3_ff5mom.csv",
    )
    parser.add_argument(
        "--proxy-root",
        type=Path,
        default=repo_root / "paper_runs/idea_replications/jkp_paper_idea_proxies",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "paper_runs/prompt_replay/guruagents/performance",
    )
    parser.add_argument("--cost-bps", type=float, default=DEFAULT_COST_BPS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ohlcv_path = args.source_root / "data/nasdaq100_ohlcv.csv"
    raw_prices, prices, caps = load_price_data(ohlcv_path)
    formations, formation_audit = discover_formations(args.run_dir, prices.columns)
    source_roots = (
        ("replay_run", args.run_dir),
        ("guruagents_source", args.source_root),
        ("repository", args.repo_root),
    )
    formation_audit["source_path"] = formation_audit["source_path"].map(
        lambda value: portable_source_locator(str(value), source_roots)
    )
    holdings_monthly, event_clock, turnover, formation_holdings = run_all_backtests(
        formations, prices, args.cost_bps
    )
    proxy_paths = load_proxy_paths(args.proxy_root)
    monthly_paths = pd.concat([holdings_monthly, proxy_paths], ignore_index=True).sort_values(
        ["series_type", "candidate_id", "realization_month"]
    )
    nasdaq_market = build_nasdaq_market(prices, caps)
    factor_formation, factor_audit, factor_meta = build_extended_factor_panel(
        args.external_factor_panel, args.usa_path, args.membership
    )
    factor_columns = factor_meta["factor_order"]
    factor_realization = factor_formation[["month", *factor_columns]].copy()
    factor_realization = factor_realization.rename(columns={"month": "formation_month"})
    factor_realization.insert(1, "realization_month", factor_realization["formation_month"] + pd.offsets.MonthEnd(1))
    risk_free = pd.read_csv(args.risk_free)
    risk_free["month"] = pd.to_datetime(risk_free["month"]) + pd.offsets.MonthEnd(0)
    regressions, residuals, static_loadings, monthly_loadings, regression_meta = run_regressions(
        monthly_paths, factor_formation, nasdaq_market, risk_free
    )
    attribution_summary, attribution_by_candidate = build_replay_attribution_outputs(regressions)
    pca_loadings = regression_meta.pop("pca_loadings")
    economics = summarize_economics(monthly_paths, risk_free)
    comparisons = build_economic_comparisons(monthly_paths, risk_free, args.cost_bps)
    turnover_summary = (
        turnover.groupby(["candidate_id", "series_type", "archive", "agent", "mode"], as_index=False)
        .agg(
            n_rebalances=("execution_date", "size"),
            mean_traded_notional=("traded_notional", "mean"),
            median_traded_notional=("traded_notional", "median"),
            max_traded_notional=("traded_notional", "max"),
            total_traded_notional=("traded_notional", "sum"),
            total_transaction_cost_nav=("transaction_cost_nav", "sum"),
            max_missing_execution_weight=("missing_execution_weight", "max"),
        )
        .sort_values(["series_type", "archive", "mode", "agent"])
    )
    outputs: Dict[str, pd.DataFrame] = {
        "monthly_return_paths.csv": monthly_paths,
        "formation_holdings.csv": formation_holdings,
        "formation_audit.csv": formation_audit,
        "formation_execution_clock.csv": event_clock,
        "rebalance_traded_notional.csv": turnover,
        "turnover_summary.csv": turnover_summary,
        "nasdaq100_source_universe_market.csv": nasdaq_market,
        "factor_panel_extended_formation.csv": factor_formation,
        "factor_panel_extended_realization.csv": factor_realization,
        "factor_extension_universe_audit.csv": factor_audit,
        "factor_extension_scaling.csv": pd.DataFrame(
            {
                "factor": list(factor_meta["scaling_by_factor"]),
                "published_scale_multiplier": list(factor_meta["scaling_by_factor"].values()),
            }
        ),
        "alpha_regressions.csv": regressions,
        "factor_fitted_and_residuals.csv": residuals,
        "static_factor_loadings.csv": static_loadings,
        "monthly_ridge_loadings.csv": monthly_loadings,
        "official_ff_factor_panel_realization.csv": risk_free[
            ["month", *OFFICIAL_FF_FACTOR_COLUMNS, "RF"]
        ].rename(columns={"month": "realization_month"}),
        "replay_attribution_ladder.csv": attribution_summary,
        "replay_attribution_by_candidate.csv": attribution_by_candidate,
        "jkp132_pca_loadings.csv": pca_loadings,
        "economic_performance.csv": economics,
        "economic_comparison.csv": comparisons,
    }
    for name, frame in outputs.items():
        frame.to_csv(args.output_dir / name, index=False)
    write_report(
        args.output_dir / "REPORT.md",
        monthly_paths,
        economics,
        regressions,
        factor_meta,
        args.cost_bps,
    )
    input_paths = {
        "live_replay_manifest": args.run_dir / "manifest.json",
        "nasdaq100_ohlcv": ohlcv_path,
        "published_broad_factor_panel": args.external_factor_panel,
        "top1000_membership": args.membership,
        "jkp_usa_characteristics": args.usa_path,
        "risk_free_and_official_ff_cache": args.risk_free,
    }
    for proxy_id in PROXY_MAP.values():
        input_paths[f"proxy_{proxy_id}"] = args.proxy_root / f"candidate_returns_{proxy_id}.csv"
    input_manifest = {
        label: {
            **manifest_locator(path, args.repo_root),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
            "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        }
        for label, path in input_paths.items()
    }
    output_manifest = {
        path.name: {"sha256": sha256(path), "size_bytes": path.stat().st_size}
        for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "created_utc": utc_now(),
        "analysis": "GuruAgents live prompt replay formation-to-realization performance and factor tests",
        "replay_run_id": args.run_dir.name,
        "inputs": input_manifest,
        "outputs": output_manifest,
        "return_clock": {
            "formation_label": "source analysis quarter end",
            "execution": "first trading close strictly after formation quarter end",
            "realization_label": "calendar month end",
            "price": "DIV_ADJ_CLOSE; CLOSE_ fallback only",
            "rebalance_frequency": "quarterly",
            "between_rebalances": "buy and hold with price drift",
        },
        "costs": {
            "primary_cost_bps": args.cost_bps,
            "cost_base": "one-way traded notional divided by pretrade NAV",
            "first_rebalance_traded_notional": "cash-to-target investment, normally 1.0",
            "proxy_cost_status": "unavailable because proxy holdings/turnover were not retained",
        },
        "factors": factor_meta,
        "regression": {
            "ols_covariance": "Newey-West HAC, maximum lag 3",
            "minimum_extra_degrees_of_freedom": 8,
            "multiple_testing": "Holm within benchmark across all candidate paths",
            "replay_multiple_testing": "Holm within benchmark across replay paths; unavailable paths are omitted rather than imputed",
            "official_ff_attribution_order": list(ATTRIBUTION_BENCHMARK_ORDER),
            "official_ff_attribution_minimum_months": ATTRIBUTION_MIN_MONTHS,
            "jkp_bab_factor": JKP_BAB_FACTOR,
            "jkp_low_risk_factor_order": list(JKP_LOW_RISK_FACTOR_COLUMNS),
            "official_ff_sample_rule": "Exact overlap with the realized extended JKP panel; the three later French-cache months are excluded from every matched ladder step",
            "full_jkp132_replay_status": "unidentified in OLS because replay n is smaller than 134 parameters",
            "compressed_test": regression_meta["pca"],
            "ridge": {
                "status": "exploratory nested leave-one-month-out, noncausal short-sample diagnostic",
                "penalty_grid": list(RIDGE_GRID),
                "factor_scaling": "pre-2022 factor standard deviation; coefficients published in raw-return units",
                "loadings_published": True,
            },
        },
        "samples": {
            "monthly_paths_start": str(pd.to_datetime(monthly_paths["realization_month"]).min().date()),
            "monthly_paths_end": str(pd.to_datetime(monthly_paths["realization_month"]).max().date()),
            "replay_eligible_start": str(pd.to_datetime(holdings_monthly.loc[holdings_monthly["series_type"].eq("replay") & holdings_monthly["analysis_eligible"], "realization_month"]).min().date()),
            "replay_eligible_end": str(pd.to_datetime(holdings_monthly.loc[holdings_monthly["series_type"].eq("replay") & holdings_monthly["analysis_eligible"], "realization_month"]).max().date()),
        },
        "software": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
        },
        "licensing": {
            "jkp_data": "MIT license file present in jkp-data; retain its copyright and permission notice.",
            "guruagents_source": "No license file was detected in the source checkout. This package contains derived audit outputs only; do not redistribute raw source data or prompts without permission.",
            "openrouter_outputs": "Authorized research-collaborator artifact; provider/model terms still apply.",
            "market_data": "Derived returns only. Confirm upstream data rights before external redistribution.",
        },
        "known_limitations": [
            "The source Nasdaq file is a compiled 100-ticker universe and may embed survivorship bias.",
            "Execution uses the first post-formation close because intraday execution prices are unavailable.",
            "The short replay histories do not identify unrestricted 133-factor OLS.",
            "JKP proxy mandates and trading costs differ from the replayed long-only portfolios.",
        ],
    }
    atomic_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps({
        "output_dir": str(args.output_dir),
        "replay_candidates": int(holdings_monthly[holdings_monthly["series_type"].eq("replay")]["candidate_id"].nunique()),
        "author_candidates": int(holdings_monthly[holdings_monthly["series_type"].eq("authors")]["candidate_id"].nunique()),
        "proxy_candidates": int(proxy_paths["candidate_id"].nunique()),
        "monthly_rows": int(len(monthly_paths)),
        "regression_rows": int(len(regressions)),
        "outputs": len(output_manifest) + 1,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
