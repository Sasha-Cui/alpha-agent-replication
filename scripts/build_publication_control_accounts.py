#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Fixed source-clock, cost and cadence controls; preserve all prior study files."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import numpy as np
import pandas as pd
from alpha_evolve.publication_economics import cash_account
from alpha_evolve.openrouter_budget import atomic_json, sha256

PRIVATE = ROOT / "artifacts/publication_upgrade_v1"


def efs():
    out = PRIVATE / "efs_controls"
    out.mkdir(parents=True, exist_ok=True)
    original = ROOT / "artifacts/economic_fidelity/v1"
    data = pd.read_parquet(original / "efs_us50_daily.parquet")
    returns = data.pivot(index="date", columns="ticker", values="ret").sort_index()
    records = []
    for arm in ["llm", "initial", "equal_weight"]:
        weights = pd.read_parquet(original / f"{arm}_daily_weights.parquet")
        dates = pd.DatetimeIndex(weights.index)
        r = returns.reindex(index=dates, columns=weights.columns).to_numpy(float)
        for cadence in ["daily", "weekly", "monthly"]:
            group = dates.to_period("W-FRI" if cadence == "weekly" else "M")
            mask = np.ones(len(dates), bool) if cadence == "daily" else np.r_[True, group[1:] != group[:-1]]
            for cost in [0, 10, 25, 50]:
                values, turn, fees = cash_account(weights.to_numpy(), r, cost, rebalance_mask=mask)
                for date, value, traded, fee in zip(dates, values, turn, fees):
                    records.append(
                        {
                            "date": str(date.date()),
                            "arm": arm,
                            "cadence": cadence,
                            "cost_bps": cost,
                            "return": float(value),
                            "traded_notional": float(traded),
                            "fee_drag": float(fee),
                        }
                    )
                if cadence == "daily" and cost in [0, 10]:
                    old = pd.read_csv(ROOT / f"paper_runs/economic_fidelity/efs_v1/{arm}_daily_returns.csv")[
                        f"total_cost_{cost}"
                    ].to_numpy()
                    if not np.allclose(values, old, atol=3e-13, rtol=0):
                        raise ValueError("Independent EFS account does not match frozen path")
    pd.DataFrame(records).to_parquet(out / "daily_returns.parquet", index=False)
    atomic_json(
        out / "completion.json",
        {
            "status": "complete",
            "arms": 3,
            "cadences": ["daily", "weekly", "monthly"],
            "cost_bps": [0, 10, 25, 50],
            "independent_frozen_account_match": True,
            "cadence_rule": "Use the fixed daily target available for the first execution session of each calendar week/month, then let holdings drift. Factor search/evaluation remains daily/weekly as in the frozen generator. This isolates trading cadence conditional on the existing signal path.",
            "weights_sha256": {
                arm: sha256(original / f"{arm}_daily_weights.parquet") for arm in ["llm", "initial", "equal_weight"]
            },
            "output_sha256": sha256(out / "daily_returns.parquet"),
        },
    )
    print("EFS_CONTROLS_COMPLETE", flush=True)


def guru():
    out = PRIVATE / "guruagents_controls"
    out.mkdir(parents=True, exist_ok=True)
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/guruagents_prompt_replay_source")
    path = source / "data/nasdaq100_ohlcv.csv"
    raw = pd.read_csv(path, usecols=["TICKERSYMBOL", "EVAL_D", "DIV_ADJ_CLOSE", "CLOSE_"])
    raw["date"] = pd.to_datetime(raw.EVAL_D)
    raw["ticker"] = raw.TICKERSYMBOL.str.strip().str.upper()
    raw["price"] = pd.to_numeric(raw.DIV_ADJ_CLOSE, errors="coerce").where(
        lambda x: x > 0, pd.to_numeric(raw.CLOSE_, errors="coerce")
    )
    raw = (
        raw.dropna(subset=["date", "ticker", "price"])
        .sort_values(["date", "ticker"])
        .drop_duplicates(["date", "ticker"], keep="last")
    )
    # A missing held observation can be carried for at most five trading sessions.
    prices = raw.pivot(index="date", columns="ticker", values="price").sort_index().ffill(limit=5)
    history = prices.pct_change(fill_method=None)
    holdings_path = ROOT / "paper_runs/prompt_replay/guruagents/performance/formation_holdings.csv"
    holdings = pd.read_csv(holdings_path)
    holdings = holdings[(holdings.archive == "results_22_24") & (holdings.series_type != "jkp_proxy")]
    dates = prices.index[(prices.index >= pd.Timestamp("2022-04-01")) & (prices.index <= pd.Timestamp("2025-03-31"))]
    r = history.reindex(dates).to_numpy()
    columns = prices.columns
    records = []
    contracts = []
    failures = []
    for candidate, frame in holdings.groupby("candidate_id"):
        for delay in [0, 90]:
            targets = np.zeros((len(dates), len(columns)))
            mask = np.zeros(len(dates), bool)
            events = []
            for formation, stocks in frame.groupby("formation_month"):
                threshold = pd.Timestamp(formation) + pd.Timedelta(days=delay)
                index = prices.index.searchsorted(threshold, side="right")
                if index >= len(prices):
                    continue
                execution = prices.index[index]
                if execution not in dates:
                    continue
                row = dates.get_loc(execution)
                for stock in stocks.itertuples():
                    targets[row, columns.get_loc(stock.ticker)] += float(stock.target_weight)
                if not np.isclose(targets[row].sum(), 1, atol=1e-10):
                    raise ValueError("Source-normalized allocation does not sum to one")
                if not np.isfinite(prices.loc[execution].to_numpy()[targets[row] > 0]).all():
                    raise ValueError("Unavailable execution price")
                mask[row] = True
                events.append({"formation_end": str(formation), "execution_date": str(execution.date())})
            contracts.append({"candidate_id": candidate, "extra_information_lag_days": delay, "events": events})
            for cost in [0, 1, 10, 25, 50]:
                try:
                    values, turn, fees = cash_account(targets, r, cost, rebalance_mask=mask)
                except ValueError as exc:
                    failures.append(
                        {
                            "candidate_id": candidate,
                            "extra_information_lag_days": delay,
                            "cost_bps": cost,
                            "reason": str(exc),
                        }
                    )
                    continue
                for date, value, traded, fee in zip(dates, values, turn, fees):
                    records.append(
                        {
                            "date": str(date.date()),
                            "candidate_id": candidate,
                            "extra_information_lag_days": delay,
                            "cost_bps": cost,
                            "return": float(value),
                            "traded_notional": float(traded),
                            "fee_drag": float(fee),
                        }
                    )
    result = pd.DataFrame(records)
    result.to_parquet(out / "daily_returns.parquet", index=False)
    atomic_json(out / "execution_contracts.json", contracts)
    atomic_json(out / "failures.json", failures)
    atomic_json(
        out / "completion.json",
        {
            "status": "complete" if not failures else "complete_with_invalid_paths",
            "candidates": int(holdings.candidate_id.nunique()),
            "failed_paths": len(failures),
            "days": len(dates),
            "period": ["2022-04-01", "2025-03-31"],
            "source_ohlcv_sha256": sha256(path),
            "holdings_sha256": sha256(holdings_path),
            "output_sha256": sha256(out / "daily_returns.parquet"),
            "weights_rule": "Source notebook 03_backtesting.ipynb normalizes all non-100 percentage totals; preserved here. Research ensemble is the existing equal-allocation combination of all five gurus, not a source-paper headline strategy.",
            "quote_policy": "No backward fill; carry an absent quote at most five trading sessions, then fail if a held return is unavailable.",
            "fees_rule": "Exact self-financing securities-only fee equation; quarterly positions drift between trades.",
            "lag_stress": "90 extra calendar days after quarter end tests latency sensitivity; it does not certify original filing availability or eliminate restatements.",
            "fresh_llm_calls": False,
            "existing_real_llm_experiments": 190,
        },
    )
    print("GURU_CONTROLS_COMPLETE", len(failures), "invalid paths", flush=True)


if __name__ == "__main__":
    efs()
    guru()
