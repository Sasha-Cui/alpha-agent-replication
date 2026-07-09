#!/usr/bin/env python3
"""Convert shipped TradeTrap viewer equity curves into monthly candidate returns."""
from __future__ import annotations

import argparse
import json
import os
import re
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


def parse_timestamp(value: str) -> pd.Timestamp:
    text = str(value).strip()
    if " " in text:
        date_part, time_part = text.split(" ", 1)
        time_part = re.sub(r"[-_]", ":", time_part)
        text = f"{date_part} {time_part}"
    return pd.to_datetime(text, errors="raise")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "candidate"


def monthly_returns_from_equity(frame: pd.DataFrame, initial_cash: float) -> pd.DataFrame:
    daily = frame.sort_values("timestamp").copy()
    daily["date"] = daily["timestamp"].dt.date
    daily = daily.groupby("date", as_index=False).tail(1).copy()
    daily["month"] = daily["timestamp"].dt.normalize() + pd.offsets.MonthEnd(0)
    monthly_value = daily.groupby("month", as_index=False).tail(1)[["month", "total_asset"]].copy()
    previous = monthly_value["total_asset"].shift(1)
    previous.iloc[0] = initial_cash
    monthly_value["candidate_return"] = monthly_value["total_asset"] / previous - 1.0
    return monthly_value[["month", "candidate_return"]]


def convert(viewer_dir: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    candidate_paths = []
    for path in sorted(viewer_dir.glob("agents_data*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for agent_name, obj in data.items():
            positions = obj.get("positions") or {}
            if not isinstance(positions, dict):
                continue
            rows = []
            for raw_dt, entry in positions.items():
                if not isinstance(entry, dict) or "total_asset" not in entry:
                    continue
                try:
                    timestamp = parse_timestamp(entry.get("date", raw_dt))
                    total_asset = float(entry["total_asset"])
                except Exception:
                    continue
                rows.append({"timestamp": timestamp, "total_asset": total_asset})
            if not rows:
                continue
            equity = pd.DataFrame(rows).drop_duplicates("timestamp", keep="last").sort_values("timestamp")
            summary = obj.get("summary") or {}
            initial_cash = float(summary.get("initial_cash") or equity["total_asset"].iloc[0])
            candidate_slug = slugify(f"{path.stem}_{agent_name}")
            equity_path = out_dir / f"equity_curve_{candidate_slug}.csv"
            candidate_path = out_dir / f"candidate_returns_{candidate_slug}.csv"
            equity.to_csv(equity_path, index=False)
            monthly = monthly_returns_from_equity(equity, initial_cash)
            monthly.to_csv(candidate_path, index=False)
            candidate_paths.append(str(candidate_path))
            summary_rows.append({
                "source_file": str(path),
                "agent_name": agent_name,
                "candidate_id": candidate_slug,
                "n_intraday_points": int(len(equity)),
                "n_months": int(len(monthly)),
                "start": equity["timestamp"].min().isoformat(),
                "end": equity["timestamp"].max().isoformat(),
                "initial_cash": initial_cash,
                "final_total_asset": float(equity["total_asset"].iloc[-1]),
                "total_return": float(equity["total_asset"].iloc[-1] / initial_cash - 1.0),
                "candidate_returns_csv": str(candidate_path),
                "equity_curve_csv": str(equity_path),
            })
    summary = pd.DataFrame(summary_rows).sort_values(["n_months", "total_return"], ascending=[False, False])
    summary_path = out_dir / "tradetrap_viewer_return_paths_summary.csv"
    summary.to_csv(summary_path, index=False)
    meta = {
        "source_viewer_dir": str(viewer_dir),
        "candidate_definition": "monthly returns from shipped TradeTrap agent_viewer total_asset paths; first month uses initial_cash as prior value",
        "summary_csv": str(summary_path),
        "candidate_paths": candidate_paths,
        "n_candidates": int(len(candidate_paths)),
        "max_months": int(summary["n_months"].max()) if len(summary) else 0,
    }
    (out_dir / "candidate_metadata.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return meta


def main() -> None:
    require_legacy_non_jkp_opt_in()
    parser = argparse.ArgumentParser()
    parser.add_argument("--viewer-dir", type=Path, default=Path("external_repos/TradeTrap/agent_viewer/data"))
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    meta = convert(args.viewer_dir, args.out_dir)
    print(json.dumps(meta, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
