#!/usr/bin/env python3
"""Run post-hoc fixed-calendar country and leave-one-country-out diagnostics.

The primary pooled analysis is unchanged.  This script addresses a reviewer-
facing ambiguity in the original descriptive country/LOO outputs, whose
country-specific executable sets induced different estimation calendars.  It
holds the primary 27 executable candidates and their 293-month calendar fixed,
then re-estimates country-local and leave-one-country-out alphas at 10 bp.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

import pandas as pd

from alpha_evolve.submission_analysis import alpha_regression


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = REPO_ROOT / "paper_runs" / "submission_evidence" / "g7_ex_us_corrected"
DEFAULT_OUTPUT = REPO_ROOT / "paper_runs" / "submission_evidence" / "fixed_calendar_diagnostics"
MARKETS = ["CAN", "FRA", "DEU", "ITA", "JPN", "GBR"]
FACTOR_COLS = [
    "jkp_topn_mkt",
    "char__be_me",
    "char__at_gr1",
    "char__market_equity",
    "char__ope_be",
    "char__ret_12_1",
]
INPUT_FILES = [
    "candidate_primary_results.csv",
    "candidate_monthly_all_markets.csv",
    "factor_monthly_all_markets.csv",
    "candidate_monthly_country_equal.csv",
    "factor_monthly_country_equal.csv",
    "run_manifest.json",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_primary_inputs(run_dir: Path) -> dict:
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_hashes = manifest.get("output_sha256", {})
    for filename in INPUT_FILES:
        path = run_dir / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        if filename == "run_manifest.json":
            continue
        expected = output_hashes.get(filename)
        observed = sha256_file(path)
        if expected != observed:
            raise RuntimeError(f"primary input hash mismatch for {filename}: {observed} != {expected}")
    return manifest


def primary_contract(run_dir: Path) -> tuple[list[str], pd.DatetimeIndex]:
    primary = pd.read_csv(run_dir / "candidate_primary_results.csv")
    successful = primary.loc[primary["status"].astype(str) == "ok"].copy()
    ids = sorted(successful["candidate_id"].astype(str).unique())
    if len(ids) != 27:
        raise RuntimeError(f"expected 27 primary executable candidates, found {len(ids)}")
    month_counts = pd.to_numeric(successful["n_months"], errors="coerce").dropna().unique()
    starts = pd.to_datetime(successful["start"], errors="coerce").dropna().unique()
    ends = pd.to_datetime(successful["end"], errors="coerce").dropna().unique()
    if len(month_counts) != 1 or len(starts) != 1 or len(ends) != 1:
        raise RuntimeError("primary executable paths do not share one calendar")
    start, end = pd.Timestamp(starts[0]), pd.Timestamp(ends[0])
    calendar = pd.date_range(start, end, freq="ME")
    if len(calendar) != int(month_counts[0]) or len(calendar) != 293:
        raise RuntimeError("primary calendar does not match the frozen 293-month contract")
    return ids, calendar


def load_monthly(run_dir: Path, candidate_ids: list[str], calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = pd.read_csv(
        run_dir / "candidate_monthly_all_markets.csv",
        usecols=["market", "month", "candidate_id", "gross_return", "traded_notional"],
    )
    factors = pd.read_csv(
        run_dir / "factor_monthly_all_markets.csv",
        usecols=["market", "month", *FACTOR_COLS],
    )
    for frame in (candidates, factors):
        frame["month"] = pd.to_datetime(frame["month"], errors="raise")
    candidates = candidates.loc[
        candidates["candidate_id"].astype(str).isin(candidate_ids)
        & candidates["market"].astype(str).isin(MARKETS)
        & candidates["month"].isin(calendar)
    ].copy()
    factors = factors.loc[
        factors["market"].astype(str).isin(MARKETS) & factors["month"].isin(calendar)
    ].copy()
    candidates["net_return"] = pd.to_numeric(candidates["gross_return"], errors="coerce") - 0.001 * pd.to_numeric(
        candidates["traded_notional"], errors="coerce"
    )
    expected_candidate_rows = len(MARKETS) * len(calendar) * len(candidate_ids)
    expected_factor_rows = len(MARKETS) * len(calendar)
    if len(candidates) != expected_candidate_rows or len(factors) != expected_factor_rows:
        raise RuntimeError(
            f"fixed-calendar row-count mismatch: candidates={len(candidates)}/{expected_candidate_rows}, "
            f"factors={len(factors)}/{expected_factor_rows}"
        )
    if candidates["net_return"].isna().any() or factors[FACTOR_COLS].isna().any().any():
        raise RuntimeError("fixed primary candidate/calendar panel contains missing values")
    return candidates, factors


def regression_rows(
    candidates: pd.DataFrame,
    factors: pd.DataFrame,
    candidate_ids: list[str],
    calendar: pd.DatetimeIndex,
) -> list[dict]:
    rows: list[dict] = []
    for market in MARKETS:
        candidate_market = candidates.loc[candidates["market"] == market]
        factor_market = factors.loc[factors["market"] == market, ["month", *FACTOR_COLS]]
        wide = candidate_market.pivot(index="month", columns="candidate_id", values="net_return").reset_index()
        frame = factor_market.merge(wide, on="month", how="inner").sort_values("month")
        if not pd.DatetimeIndex(frame["month"]).equals(calendar):
            raise RuntimeError(f"country {market} does not use the primary calendar")
        for candidate_id in candidate_ids:
            result = asdict(alpha_regression(frame, candidate_id, FACTOR_COLS))
            result.update(
                {
                    "diagnostic": "country_fixed_primary_calendar",
                    "market": market,
                    "excluded_market": "",
                    "candidate_id": candidate_id,
                    "cost_bps_one_way": 10,
                    "status": "ok",
                }
            )
            rows.append(result)

    for excluded in MARKETS:
        included = [market for market in MARKETS if market != excluded]
        candidate_pooled = (
            candidates.loc[candidates["market"].isin(included)]
            .groupby(["month", "candidate_id"], as_index=False)["net_return"]
            .mean()
        )
        factor_pooled = factors.loc[factors["market"].isin(included)].groupby("month", as_index=False)[FACTOR_COLS].mean()
        wide = candidate_pooled.pivot(index="month", columns="candidate_id", values="net_return").reset_index()
        frame = factor_pooled.merge(wide, on="month", how="inner").sort_values("month")
        if not pd.DatetimeIndex(frame["month"]).equals(calendar):
            raise RuntimeError(f"LOO exclusion {excluded} does not use the primary calendar")
        for candidate_id in candidate_ids:
            result = asdict(alpha_regression(frame, candidate_id, FACTOR_COLS))
            result.update(
                {
                    "diagnostic": "loo_fixed_primary_calendar",
                    "market": "",
                    "excluded_market": excluded,
                    "candidate_id": candidate_id,
                    "cost_bps_one_way": 10,
                    "status": "ok",
                }
            )
            rows.append(result)
    return rows


def transport_rows(
    run_dir: Path,
    candidate_ids: list[str],
    primary_calendar: pd.DatetimeIndex,
) -> tuple[list[dict], pd.DatetimeIndex]:
    """Re-estimate pooled G7 alpha on the retrospective U.S. calendar."""
    calendar = primary_calendar[primary_calendar >= pd.Timestamp("2001-08-31")]
    candidates = pd.read_csv(
        run_dir / "candidate_monthly_country_equal.csv",
        usecols=["month", "candidate_id", "gross_return", "traded_notional"],
    )
    factors = pd.read_csv(
        run_dir / "factor_monthly_country_equal.csv",
        usecols=["month", *FACTOR_COLS],
    )
    for frame in (candidates, factors):
        frame["month"] = pd.to_datetime(frame["month"], errors="raise")
    candidates = candidates.loc[
        candidates["candidate_id"].astype(str).isin(candidate_ids) & candidates["month"].isin(calendar)
    ].copy()
    factors = factors.loc[factors["month"].isin(calendar)].copy()
    candidates["net_return"] = pd.to_numeric(candidates["gross_return"], errors="coerce") - 0.001 * pd.to_numeric(
        candidates["traded_notional"], errors="coerce"
    )
    if len(candidates) != len(calendar) * len(candidate_ids) or len(factors) != len(calendar):
        raise RuntimeError("shared U.S./G7 calendar rows are incomplete")
    wide = candidates.pivot(index="month", columns="candidate_id", values="net_return").reset_index()
    frame = factors.merge(wide, on="month", how="inner").sort_values("month")
    if not pd.DatetimeIndex(frame["month"]).equals(calendar) or frame[[*FACTOR_COLS, *candidate_ids]].isna().any().any():
        raise RuntimeError("shared U.S./G7 diagnostic does not use one complete calendar")
    rows: list[dict] = []
    for candidate_id in candidate_ids:
        result = asdict(alpha_regression(frame, candidate_id, FACTOR_COLS))
        result.update(
            {
                "diagnostic": "g7_usa_common_calendar",
                "market": "",
                "excluded_market": "",
                "candidate_id": candidate_id,
                "cost_bps_one_way": 10,
                "status": "ok",
            }
        )
        rows.append(result)
    return rows, calendar


def write_outputs(run_dir: Path, output_dir: Path) -> None:
    manifest = verify_primary_inputs(run_dir)
    candidate_ids, calendar = primary_contract(run_dir)
    candidates, factors = load_monthly(run_dir, candidate_ids, calendar)
    rows = regression_rows(candidates, factors, candidate_ids, calendar)
    shared_rows, shared_calendar = transport_rows(run_dir, candidate_ids, calendar)
    output = pd.DataFrame([*rows, *shared_rows])
    if len(output) != 13 * len(candidate_ids) or not output["status"].eq("ok").all():
        raise RuntimeError("fixed-calendar diagnostic output is incomplete")

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fixed-calendar-", dir=output_dir) as temp_dir:
        temp = Path(temp_dir)
        csv_path = temp / "fixed_calendar_country_loo.csv"
        output.to_csv(csv_path, index=False)
        diagnostic_manifest = {
            "schema_version": 1,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "classification": "post_hoc_fixed_calendar_diagnostic",
            "rationale": (
                "Hold the primary executable-candidate set and 293-month calendar fixed so country and "
                "leave-one-country-out comparisons do not inherit country-specific executable-set calendars."
            ),
            "primary_analysis_lock_sha256": manifest.get("analysis_lock_sha256"),
            "markets": MARKETS,
            "candidate_count": len(candidate_ids),
            "calendar": {
                "start": calendar.min().date().isoformat(),
                "end": calendar.max().date().isoformat(),
                "n_months": len(calendar),
            },
            "usa_g7_common_calendar": {
                "start": shared_calendar.min().date().isoformat(),
                "end": shared_calendar.max().date().isoformat(),
                "n_months": len(shared_calendar),
            },
            "factor_columns": FACTOR_COLS,
            "cost_bps_one_way": 10,
            "input_sha256": {filename: sha256_file(run_dir / filename) for filename in INPUT_FILES},
            "script_sha256": sha256_file(Path(__file__)),
            "output_sha256": {csv_path.name: sha256_file(csv_path)},
        }
        manifest_path = temp / "manifest.json"
        manifest_path.write_text(json.dumps(diagnostic_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        csv_path.replace(output_dir / csv_path.name)
        manifest_path.replace(output_dir / manifest_path.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    write_outputs(args.run_dir, args.output_dir)
    print(f"wrote {args.output_dir / 'fixed_calendar_country_loo.csv'}")
    print(f"wrote {args.output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
