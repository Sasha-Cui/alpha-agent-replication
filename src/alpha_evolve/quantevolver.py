#!/usr/bin/env python3
"""Run QuantEvolver shipped seed ideas as USA/JKP monthly proxy factors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .jkp import DEFAULT_JKP_USA, DEFAULT_FF5MOM, long_short_one_month, weighted_mean, validate_columns

DERIVED_CANDIDATES = {
    "quantevolver_return_sharpe_60_proxy": {
        "seed_name": "return_sharpe_60",
        "seed_expr": "div(ts_mean(returns(60)), ts_std(returns(60)))",
        "jkp_proxy": "ret_12_1 / rvol_252d",
        "notes": "Monthly USA proxy for risk-adjusted return momentum using JKP twelve-minus-one momentum scaled by annual daily realized volatility.",
    },
    "quantevolver_price_zscore_reversal_120_proxy": {
        "seed_name": "price_zscore_reversal_120",
        "seed_expr": "neg(zscore(last(close(120)), close(120)))",
        "jkp_proxy": "-ret_12_1",
        "notes": "Monthly USA proxy for price displacement reversal using negative JKP twelve-minus-one momentum.",
    },
    "quantevolver_volume_price_corr_proxy": {
        "seed_name": "volume_price_corr",
        "seed_expr": "corr(returns(60), log_arr(volume(60)))",
        "jkp_proxy": "corr_1260d",
        "notes": "Closest available JKP USA proxy for long-window price/volume correlation.",
    },
}


def build(out_dir: Path, usa_path: Path, start: str, end: str, top_n: int, quantile: float, min_side: int) -> dict:
    benchmark_cols = DEFAULT_FF5MOM
    source_cols = ["permno", "eom", "ret_exc_lead1m", "me", *benchmark_cols, "rvol_252d", "corr_1260d"]
    source_cols = list(dict.fromkeys(source_cols))
    validate_columns(usa_path, source_cols)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_parquet(usa_path, columns=source_cols)
    raw["month"] = pd.to_datetime(raw["eom"], errors="coerce") + pd.offsets.MonthEnd(0)
    raw["ret_exc_lead1m"] = pd.to_numeric(raw["ret_exc_lead1m"], errors="coerce")
    raw["weight"] = pd.to_numeric(raw["me"], errors="coerce")
    raw = raw[(raw["month"] >= pd.Timestamp(start)) & (raw["month"] <= pd.Timestamp(end))].copy()
    raw = raw.replace([np.inf, -np.inf], np.nan).dropna(subset=["month", "permno", "ret_exc_lead1m", "weight"])
    raw = raw[raw["weight"] > 0]
    if top_n > 0:
        raw["_size_rank"] = raw.groupby("month")["weight"].rank(method="first", ascending=False)
        raw = raw[raw["_size_rank"] <= top_n].drop(columns=["_size_rank"]).copy()
    raw["quantevolver_return_sharpe_60_proxy"] = raw["ret_12_1"] / (raw["rvol_252d"].abs() + 1e-8)
    raw["quantevolver_price_zscore_reversal_120_proxy"] = -raw["ret_12_1"]
    raw["quantevolver_volume_price_corr_proxy"] = raw["corr_1260d"]

    months = sorted(raw["month"].dropna().unique())
    factor_rows = []
    candidate_rows = {name: [] for name in DERIVED_CANDIDATES}
    for month in months:
        frame = raw[raw["month"] == month]
        row = {"month": pd.Timestamp(month) + pd.offsets.MonthEnd(0)}
        row["jkp_topn_mkt"] = weighted_mean(frame["ret_exc_lead1m"], frame["weight"])
        row["n_stocks"] = int(frame["permno"].nunique())
        for col in benchmark_cols:
            row[f"char__{col}"] = long_short_one_month(frame, col, quantile, min_side)
        factor_rows.append(row)
        for candidate in DERIVED_CANDIDATES:
            candidate_rows[candidate].append({
                "month": pd.Timestamp(month) + pd.offsets.MonthEnd(0),
                "candidate_return": long_short_one_month(frame, candidate, quantile, min_side),
            })
    factor_panel = pd.DataFrame(factor_rows).sort_values("month")
    factor_panel_path = out_dir / "jkp_benchmark_factor_panel.csv"
    factor_panel.to_csv(factor_panel_path, index=False)
    candidate_paths = {}
    for candidate, rows in candidate_rows.items():
        path = out_dir / f"candidate_returns_{candidate}.csv"
        pd.DataFrame(rows).sort_values("month").to_csv(path, index=False)
        candidate_paths[candidate] = str(path)
    metadata = {
        "paper": "QuantEvolver",
        "source_repo": "external_repos/QuantEvolver",
        "source_seed_file": "external_repos/QuantEvolver/examples/seed_candidates.yaml",
        "usa_path": str(usa_path),
        "input_policy": "read-only JKP USA.parquet only; no native QuantEvolver return data used",
        "start": start,
        "end": end,
        "top_n_by_me_per_month": top_n,
        "quantile": quantile,
        "min_side": min_side,
        "n_months": int(len(factor_panel)),
        "n_rows_loaded_after_filters": int(len(raw)),
        "factor_panel_csv": str(factor_panel_path),
        "candidate_paths": candidate_paths,
        "candidate_definitions": DERIVED_CANDIDATES,
    }
    (out_dir / "quantevolver_jkp_proxy_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--usa-path", type=Path, default=DEFAULT_JKP_USA)
    parser.add_argument("--start", default="1999-07-31")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--top-n", type=int, default=1000)
    parser.add_argument("--quantile", type=float, default=0.1)
    parser.add_argument("--min-side", type=int, default=20)
    args = parser.parse_args()
    meta = build(args.out_dir, args.usa_path, args.start, args.end, args.top_n, args.quantile, args.min_side)
    print(json.dumps(meta, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
