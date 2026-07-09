#!/usr/bin/env python3
"""Convert shipped GuruAgents daily backtest workbooks into monthly candidate returns."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

LEGACY_NON_JKP_MESSAGE = (
    "This is a legacy non-JKP return-data script. It is disabled by default "
    "because valid experiments must use only ${ALPHA_EVOLVE_JKP_ROOT} "
    "or ${ALPHA_EVOLVE_RETURN_DATA_ROOT}. "
    "Use scripts/evaluate_candidate_returns_jkp.py for valid JKP-scope runs, or set "
    "ALLOW_LEGACY_NON_JKP_RETURNS=1 only for explicit non-counting audit reproduction."
)


def require_legacy_non_jkp_opt_in() -> None:
    if os.environ.get("ALLOW_LEGACY_NON_JKP_RETURNS") != "1":
        raise SystemExit(LEGACY_NON_JKP_MESSAGE)

AGENT_SHEETS = [
    "Benjamin_Graham_Returns",
    "Warren_Buffett_Returns",
    "Joel_Greenblatt_Returns",
    "Joseph_Piotroski_Returns",
    "Edward_Altman_Returns",
]


def monthly_from_daily(frame: pd.DataFrame, date_col: str, return_col: str) -> pd.DataFrame:
    df = frame[[date_col, return_col]].copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df[return_col] = pd.to_numeric(df[return_col], errors="coerce").fillna(0.0)
    df["month"] = df[date_col] + pd.offsets.MonthEnd(0)
    monthly = df.groupby("month", as_index=False)[return_col].apply(lambda x: (1.0 + x).prod() - 1.0)
    return monthly.rename(columns={return_col: "candidate_return"})


def main() -> None:
    require_legacy_non_jkp_opt_in()
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=Path("external_repos/GuruAgents/results_22_24/multi_agent_backtest_results.xlsx"))
    parser.add_argument("--out-dir", type=Path, default=Path("paper_runs/042_guruagents"))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    daily_parts = []
    individual_paths = []
    for sheet in AGENT_SHEETS:
        df = pd.read_excel(args.workbook, sheet_name=sheet)
        agent = sheet.replace("_Returns", "").lower()
        daily = df[["date", "daily_return"]].copy()
        daily["date"] = pd.to_datetime(daily["date"])
        daily["daily_return"] = pd.to_numeric(daily["daily_return"], errors="coerce").fillna(0.0)
        daily = daily.rename(columns={"daily_return": agent})
        daily_parts.append(daily)
        monthly = monthly_from_daily(df, "date", "daily_return")
        path = args.out_dir / f"candidate_returns_{agent}.csv"
        monthly.to_csv(path, index=False)
        individual_paths.append(str(path))
    merged = daily_parts[0]
    for part in daily_parts[1:]:
        merged = merged.merge(part, on="date", how="outer")
    agent_cols = [c for c in merged.columns if c != "date"]
    merged[agent_cols] = merged[agent_cols].fillna(0.0)
    merged["daily_return"] = merged[agent_cols].mean(axis=1)
    monthly_equal = monthly_from_daily(merged, "date", "daily_return")
    candidate_path = args.out_dir / "candidate_returns.csv"
    monthly_equal.to_csv(candidate_path, index=False)
    meta = {
        "source_workbook": str(args.workbook),
        "candidate_definition": "equal-weight average of the five shipped GuruAgents daily agent return streams, compounded monthly",
        "agent_sheets": AGENT_SHEETS,
        "candidate_returns_csv": str(candidate_path),
        "individual_candidate_paths": individual_paths,
        "month_start": monthly_equal["month"].min().date().isoformat(),
        "month_end": monthly_equal["month"].max().date().isoformat(),
        "n_months": int(len(monthly_equal)),
    }
    (args.out_dir / "candidate_metadata.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(meta, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
