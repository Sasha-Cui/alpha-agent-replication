#!/usr/bin/env python3
"""Build USA/JKP-only monthly candidate and benchmark factor returns.

Reads only selected columns from the read-only JKP USA.parquet file and writes
all generated artifacts to the requested output directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .paths import DEFAULT_JKP_USA

DEFAULT_START = "1999-07-31"
DEFAULT_END = "2024-12-31"
DEFAULT_FF3 = ["be_me", "market_equity"]
DEFAULT_FF5MOM = ["be_me", "at_gr1", "market_equity", "ope_be", "ret_12_1"]


def available_columns(path: Path) -> list[str]:
    return pq.ParquetFile(path).schema.names


def parse_cols(text: str | None) -> list[str]:
    if not text:
        return []
    return [x.strip() for x in text.split(",") if x.strip()]


def validate_columns(path: Path, cols: Iterable[str]) -> None:
    avail = set(available_columns(path))
    missing = [c for c in cols if c not in avail]
    if missing:
        raise ValueError("Missing columns in JKP USA.parquet: " + ", ".join(missing))


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    v = pd.to_numeric(values, errors="coerce").astype("float64")
    w = pd.to_numeric(weights, errors="coerce").astype("float64")
    mask = np.isfinite(v) & np.isfinite(w) & (w > 0)
    if mask.sum() == 0:
        return float("nan")
    return float(np.average(v[mask], weights=w[mask]))


def long_short_one_month(frame: pd.DataFrame, char_col: str, quantile: float, min_side: int) -> float:
    x = frame[[char_col, "ret_exc_lead1m", "weight"]].replace([np.inf, -np.inf], np.nan).dropna()
    x = x[x["weight"] > 0]
    if len(x) < max(2 * min_side, 10):
        return float("nan")
    low_cut = x[char_col].quantile(quantile)
    high_cut = x[char_col].quantile(1.0 - quantile)
    low = x[x[char_col] <= low_cut]
    high = x[x[char_col] >= high_cut]
    if len(low) < min_side or len(high) < min_side:
        return float("nan")
    return weighted_mean(high["ret_exc_lead1m"], high["weight"]) - weighted_mean(low["ret_exc_lead1m"], low["weight"])


def build_returns(
    usa_path: Path,
    candidate_cols: list[str],
    benchmark_cols: list[str],
    out_dir: Path,
    start: str,
    end: str,
    top_n: int,
    quantile: float,
    min_side: int,
) -> dict:
    needed = ["permno", "eom", "ret_exc_lead1m", "me", *candidate_cols, *benchmark_cols]
    needed = list(dict.fromkeys(needed))
    validate_columns(usa_path, needed)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_parquet(usa_path, columns=needed)
    raw["month"] = pd.to_datetime(raw["eom"], errors="coerce") + pd.offsets.MonthEnd(0)
    raw["ret_exc_lead1m"] = pd.to_numeric(raw["ret_exc_lead1m"], errors="coerce")
    raw["weight"] = pd.to_numeric(raw["me"], errors="coerce")
    raw = raw[(raw["month"] >= pd.Timestamp(start)) & (raw["month"] <= pd.Timestamp(end))].copy()
    raw = raw.replace([np.inf, -np.inf], np.nan)
    raw = raw.dropna(subset=["month", "permno", "ret_exc_lead1m", "weight"])
    raw = raw[raw["weight"] > 0]
    if top_n > 0:
        raw["_size_rank"] = raw.groupby("month")["weight"].rank(method="first", ascending=False)
        raw = raw[raw["_size_rank"] <= top_n].copy()
        raw = raw.drop(columns=["_size_rank"])

    months = sorted(raw["month"].dropna().unique())
    factor_rows = []
    candidate_frames = {col: [] for col in candidate_cols}
    for month in months:
        frame = raw[raw["month"] == month]
        row = {"month": pd.Timestamp(month) + pd.offsets.MonthEnd(0)}
        row["jkp_topn_mkt"] = weighted_mean(frame["ret_exc_lead1m"], frame["weight"])
        row["n_stocks"] = int(frame["permno"].nunique())
        for col in benchmark_cols:
            row[f"char__{col}"] = long_short_one_month(frame, col, quantile, min_side)
        factor_rows.append(row)
        for col in candidate_cols:
            candidate_frames[col].append({
                "month": pd.Timestamp(month) + pd.offsets.MonthEnd(0),
                "candidate_return": long_short_one_month(frame, col, quantile, min_side),
            })

    factor_panel = pd.DataFrame(factor_rows).sort_values("month")
    factor_panel.to_csv(out_dir / "jkp_benchmark_factor_panel.csv", index=False)
    candidate_paths = {}
    for col, rows in candidate_frames.items():
        path = out_dir / f"candidate_returns_jkp_{col}.csv"
        pd.DataFrame(rows).sort_values("month").to_csv(path, index=False)
        candidate_paths[col] = str(path)
    meta = {
        "usa_path": str(usa_path),
        "input_policy": "read-only JKP USA.parquet; generated artifacts written outside input folders",
        "start": start,
        "end": end,
        "top_n_by_me_per_month": top_n,
        "quantile": quantile,
        "min_side": min_side,
        "candidate_cols": candidate_cols,
        "benchmark_cols": benchmark_cols,
        "factor_panel_csv": str(out_dir / "jkp_benchmark_factor_panel.csv"),
        "candidate_paths": candidate_paths,
        "n_months": int(len(factor_panel)),
        "n_rows_loaded_after_filters": int(len(raw)),
    }
    (out_dir / "jkp_build_metadata.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usa-path", type=Path, default=DEFAULT_JKP_USA)
    parser.add_argument("--candidate-cols", required=True, help="Comma-separated JKP characteristic columns to build as candidate returns.")
    parser.add_argument("--benchmark-cols", default=",".join(DEFAULT_FF5MOM), help="Comma-separated JKP columns for benchmark factor panel.")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--top-n", type=int, default=1000, help="Monthly top-N universe by me; <=0 uses all eligible stocks.")
    parser.add_argument("--quantile", type=float, default=0.1)
    parser.add_argument("--min-side", type=int, default=20)
    args = parser.parse_args()
    if not (0.0 < args.quantile < 0.5):
        raise ValueError("--quantile must be between 0 and 0.5")
    meta = build_returns(
        usa_path=args.usa_path,
        candidate_cols=parse_cols(args.candidate_cols),
        benchmark_cols=parse_cols(args.benchmark_cols),
        out_dir=args.out_dir,
        start=args.start,
        end=args.end,
        top_n=args.top_n,
        quantile=args.quantile,
        min_side=args.min_side,
    )
    print(json.dumps(meta, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
