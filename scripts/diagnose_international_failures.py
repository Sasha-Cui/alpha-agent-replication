#!/usr/bin/env python3
"""Reconstruct every international limited-liability event security by security.

This post-hoc forensic audit does not repair or reclassify the international
extension. It identifies whether each nonpositive-NAV event is driven by long-
short leverage, an extreme held-security return, missing data, or a failure to
reproduce the recorded event.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_paper_idea_jkp_proxies as proxy
import run_submission_evidence as runner
from alpha_evolve.paths import DEFAULT_JKP_ROOT
from alpha_evolve.submission_analysis import target_weights


DEFAULT_FAILURES = (
    ROOT / "paper_runs/submission_evidence/g7_ex_us_corrected/candidate_path_failures.csv"
)
DEFAULT_OUTPUT = ROOT / "paper_runs/submission_evidence/international_failure_forensics"
CLIP_LEVELS = [1.0, 2.0, 5.0, 10.0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def market_path(market: str) -> Path:
    return DEFAULT_JKP_ROOT / "data/processed/characteristics" / f"{market}.parquet"


def load_two_month_panel(market: str, formation_month: pd.Timestamp) -> pd.DataFrame:
    path = market_path(market)
    next_month = formation_month + pd.offsets.MonthEnd(1)
    columns = ["ret", *["id" if col == "permno" else col for col in proxy.BASE_COLS]]
    columns = list(dict.fromkeys(columns))
    raw = pd.read_parquet(
        path,
        columns=columns,
        filters=[("eom", ">=", formation_month), ("eom", "<=", next_month)],
    )
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
    raw = raw[raw["month"].eq(formation_month)].copy()
    raw = raw.replace([np.inf, -np.inf], np.nan)
    raw = raw.dropna(subset=["month", "security_id", "weight"])
    raw = raw[raw["weight"] > 0]
    raw["_size_rank"] = raw.groupby("month")["weight"].rank(method="first", ascending=False)
    return raw[raw["_size_rank"] <= 1000].drop(columns=["_size_rank", "_next_observation_month"])


def event_forensics(event: pd.Series) -> dict:
    market = str(event["market"])
    formation_month = pd.Timestamp(event["formation_month"]) + pd.offsets.MonthEnd(0)
    scored = proxy.build_scores_for_month(load_two_month_panel(market, formation_month))
    candidate = str(event["candidate_id"])
    weight_candidate = candidate
    if candidate == runner.CONTEST_ID:
        weight_candidate = str(event["selected_sleeve"])
    if not weight_candidate or weight_candidate not in proxy.IDEA_DEFINITIONS:
        raise ValueError(f"cannot reconstruct weights for {candidate}: selected={weight_candidate!r}")
    meta = proxy.IDEA_DEFINITIONS[weight_candidate]
    weights = target_weights(
        scored,
        weight_candidate,
        str(meta["strategy"]),
        quantile=0.1,
        min_side=20,
    )
    returns = (
        scored[["security_id", "ret_total_lead1m", "ret_exc_lead1m"]]
        .drop_duplicates("security_id", keep="last")
        .set_index("security_id")
        .reindex(weights.index)
    )
    missing = returns["ret_total_lead1m"].isna()
    total_returns = returns["ret_total_lead1m"].fillna(0.0).astype(float)
    contributions = weights.astype(float) * total_returns
    reconstructed = float(contributions.sum())
    recorded = float(event["failure_total_return"])
    if not np.isclose(reconstructed, recorded, atol=1e-10, rtol=1e-10):
        raise RuntimeError(
            f"failure mismatch {market} {formation_month.date()} {candidate}: "
            f"{reconstructed} != {recorded}"
        )
    contribution_frame = pd.DataFrame(
        {
            "weight": weights,
            "total_return": total_returns,
            "excess_return": returns["ret_exc_lead1m"],
            "contribution": contributions,
        }
    ).sort_values("contribution")
    top = contribution_frame.iloc[0]
    loss = abs(min(reconstructed, 0.0))
    top_loss_share = abs(min(float(top["contribution"]), 0.0)) / loss if loss > 0 else np.nan
    classification = "diffuse_or_leverage_driven"
    if float(top["weight"]) < 0 and float(top["total_return"]) > 1.0:
        classification = "extreme_positive_return_on_short_position"
    if top_loss_share >= 0.5 and classification.startswith("extreme"):
        classification = "single_extreme_short_position_dominates"
    if missing.any() and classification == "diffuse_or_leverage_driven":
        classification = "contains_missing_total_return_but_zero_filled"

    row = {
        "market": market,
        "formation_month": formation_month.date().isoformat(),
        "return_month": (formation_month + pd.offsets.MonthEnd(1)).date().isoformat(),
        "candidate_id": candidate,
        "weight_candidate_id": weight_candidate,
        "recorded_total_return": recorded,
        "reconstructed_total_return": reconstructed,
        "reconstruction_abs_error": abs(reconstructed - recorded),
        "strategy": meta["strategy"],
        "n_positions": int(len(weights)),
        "n_long": int((weights > 0).sum()),
        "n_short": int((weights < 0).sum()),
        "gross_exposure": float(weights.abs().sum()),
        "long_leg_contribution": float(contributions[weights > 0].sum()),
        "short_leg_contribution": float(contributions[weights < 0].sum()),
        "missing_total_return_weight_share": float(weights.abs()[missing].sum() / weights.abs().sum()),
        "worst_contributor_security_id": str(contribution_frame.index[0]),
        "worst_contributor_weight": float(top["weight"]),
        "worst_contributor_total_return": float(top["total_return"]),
        "worst_contributor_excess_return": float(top["excess_return"]),
        "worst_contribution": float(top["contribution"]),
        "worst_contributor_share_of_portfolio_loss": float(top_loss_share),
        "held_returns_over_100pct": int((total_returns > 1.0).sum()),
        "held_returns_over_500pct": int((total_returns > 5.0).sum()),
        "held_returns_over_1000pct": int((total_returns > 10.0).sum()),
        "max_held_total_return": float(total_returns.max()),
        "min_held_total_return": float(total_returns.min()),
        "forensic_classification": classification,
    }
    for cap in CLIP_LEVELS:
        clipped = total_returns.clip(lower=-1.0, upper=cap)
        value = float(np.dot(weights.to_numpy(dtype=float), clipped.to_numpy(dtype=float)))
        key = str(cap).replace(".", "_")
        row[f"portfolio_return_if_security_returns_capped_at_{key}"] = value
        row[f"failure_remains_if_capped_at_{key}"] = bool(value <= -1.0)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    failures = pd.read_csv(args.failures)
    rows = []
    for _, event in failures.iterrows():
        rows.append(event_forensics(event))
    detail = pd.DataFrame(rows).sort_values(["return_month", "market", "candidate_id"])
    by_month = (
        detail.groupby(["market", "return_month"], as_index=False)
        .agg(
            failure_events=("candidate_id", "size"),
            affected_candidates=("candidate_id", "nunique"),
            median_recorded_return=("recorded_total_return", "median"),
            worst_recorded_return=("recorded_total_return", "min"),
            median_worst_contributor_share=("worst_contributor_share_of_portfolio_loss", "median"),
            max_held_total_return=("max_held_total_return", "max"),
        )
        .sort_values(["failure_events", "market", "return_month"], ascending=[False, True, True])
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "failure_event_forensics.csv"
    month_path = args.output_dir / "failure_month_summary.csv"
    detail.to_csv(detail_path, index=False)
    by_month.to_csv(month_path, index=False)
    clip_counts = {}
    for cap in CLIP_LEVELS:
        key = str(cap).replace(".", "_")
        clip_counts[f"failures_remaining_cap_{key}"] = int(
            detail[f"failure_remains_if_capped_at_{key}"].sum()
        )
    manifest = {
        "analysis_label": "post_hoc_international_failure_forensics",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_failures_sha256": sha256(args.failures),
        "failure_events": int(len(detail)),
        "failure_candidates": int(detail["candidate_id"].nunique()),
        "failure_markets": detail.groupby("market").size().astype(int).to_dict(),
        "failure_months": int(detail["return_month"].nunique()),
        "single_extreme_short_position_dominates": int(
            detail["forensic_classification"].eq("single_extreme_short_position_dominates").sum()
        ),
        "extreme_short_classifications_total": int(
            detail["forensic_classification"].str.contains("extreme|single_extreme", regex=True).sum()
        ),
        "events_in_two_largest_month_cells": int(by_month.head(2)["failure_events"].sum()),
        **clip_counts,
        "interpretation": (
            "Capping is a post-hoc diagnostic, not a corrected return policy. Concentrated failures are treated as a data/implementation alarm and removed from headline performance evidence."
        ),
        "output_sha256": {
            detail_path.name: sha256(detail_path),
            month_path.name: sha256(month_path),
        },
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
