#!/usr/bin/env python3
"""Freeze the twice-amended evaluator before the corrected geographic rerun.

The initial pre-outcome lock and its defective outputs remain immutable in the
superseded-v1 provenance directory. The first amended lock and its runtime
failure remain immutable in the superseded-v2 directory. This lock is
explicitly post-outcome and post-runtime-failure: it freezes the disclosed
limited-liability rule before any evaluable corrected result is run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import run_paper_idea_jkp_proxies as proxy
from alpha_evolve.paths import DEFAULT_JKP_ROOT


CONTEST_ID = "contesttrade_internal_contest_trailing_sharpe"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frozen_candidates() -> pd.DataFrame:
    rows = []
    for candidate, metadata in proxy.IDEA_DEFINITIONS.items():
        rows.append({"candidate_id": candidate, **metadata})
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
    frame = pd.DataFrame(rows).sort_values("candidate_id").reset_index(drop=True)
    if len(frame) != 62 or frame["candidate_id"].nunique() != 62:
        raise RuntimeError(f"expected exactly 62 frozen candidates, observed {len(frame)}")
    return frame


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "paper_runs" / "submission_evidence",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--markets", default="CAN,FRA,DEU,ITA,JPN,GBR")
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    lock_path = args.out_dir / "analysis_lock.json"
    if lock_path.exists() and not args.force:
        raise FileExistsError(f"refusing to overwrite frozen lock: {lock_path}")

    candidates = frozen_candidates()
    candidate_path = args.out_dir / "frozen_candidate_registry.csv"
    candidates.to_csv(candidate_path, index=False)

    system_registry = REPO_ROOT / "literature_review" / "census_v1" / "system_registry.csv"
    systems = pd.read_csv(system_registry, sep="|")
    counts = systems["stratum"].value_counts().sort_index().to_dict()
    expected = {"F": 29, "T": 38, "B": 23, "C": 5, "M": 8}
    if counts != expected or len(systems) != 103:
        raise RuntimeError(f"system registry does not match frozen census: {counts}, n={len(systems)}")

    files = [
        REPO_ROOT / "docs" / "confirmatory_analysis_protocol.md",
        REPO_ROOT / "docs" / "current_project_execution_decisions.md",
        REPO_ROOT / "literature_review" / "paper_links.csv",
        REPO_ROOT / "literature_review" / "code_links.csv",
        system_registry,
        candidate_path,
        REPO_ROOT / "scripts" / "run_paper_idea_jkp_proxies.py",
        REPO_ROOT / "scripts" / "freeze_submission_analysis.py",
        REPO_ROOT / "scripts" / "run_submission_evidence.py",
        REPO_ROOT / "src" / "alpha_evolve" / "submission_analysis.py",
        REPO_ROOT / "tests" / "test_submission_analysis.py",
        REPO_ROOT / "tests" / "test_submission_runner.py",
    ]
    relative_hashes = {
        str(path.relative_to(REPO_ROOT)): sha256_file(path)
        for path in files
    }
    markets = [item.strip().upper() for item in args.markets.split(",") if item.strip()]
    expected_markets = ["CAN", "FRA", "DEU", "ITA", "JPN", "GBR"]
    if markets != expected_markets:
        raise ValueError(f"amended confirmatory lock requires {expected_markets}, observed {markets}")
    data_inputs = {}
    data_markets = [*markets, "USA"]
    for market in data_markets:
        data_path = (
            DEFAULT_JKP_ROOT
            / "data"
            / "processed"
            / "characteristics"
            / f"{market}.parquet"
        )
        print(f"hashing frozen data input {market}: {data_path}", flush=True)
        data_inputs[market] = {
            "path": str(data_path),
            "bytes": data_path.stat().st_size,
            "sha256": sha256_file(data_path),
        }
    superseded_lock = args.out_dir / "superseded_v1" / "analysis_lock_v1_original.json"
    if not superseded_lock.exists():
        raise FileNotFoundError(f"initial pre-outcome lock missing: {superseded_lock}")
    superseded_outputs = (
        args.out_dir / "superseded_v1" / "g7_ex_us_lookahead_and_calendar_bug"
    )
    superseded_v2_lock = (
        args.out_dir
        / "superseded_v2_nav_runtime_failure"
        / "analysis_lock_v2_amendment1.json"
    )
    superseded_v2_output = (
        args.out_dir
        / "superseded_v2_nav_runtime_failure"
        / "g7_ex_us_corrected_runtime_failure"
    )
    if not superseded_v2_lock.exists():
        raise FileNotFoundError(
            f"first amended lock missing: {superseded_v2_lock}"
        )
    if not superseded_v2_output.exists():
        raise FileNotFoundError(
            f"first amended runtime-failure output missing: {superseded_v2_output}"
        )
    lock = {
        "schema_version": 3,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision_owner": "Sasha Cui",
        "cutoff_utc": "2026-08-02T23:59:59Z",
        "lock_stage": (
            "post-outcome and post-runtime-failure correctness amendments; "
            "pre-evaluable-corrected-rerun"
        ),
        "initial_lock_created_before_g7_outcome_access": True,
        "amended_lock_created_after_g7_outcome_access": True,
        "corrected_g7_outputs_viewed_before_this_lock": False,
        "amendment1_runtime_failure_observed_before_this_lock": True,
        "amendment1_alpha_tables_or_rankings_produced": False,
        "initial_prelock_inspection": "file availability, date ranges, and cross-sectional counts only",
        "amendment_1_timestamp_utc": "2026-08-03T00:00:00Z",
        "amendment_2_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "amendment_1_reason": (
            "independent code audit found future-return availability in formation, "
            "incorrect long-short NAV drift, mismatched country sets, and different "
            "ordinary/bootstrap calendars"
        ),
        "amendment_2_reason": (
            "the first Amendment-1 run stopped during the Canada build when an "
            "extreme short-position gain made a 100/100 sleeve's NAV nonpositive; "
            "the evaluator now classifies such a complete path as a limited-liability "
            "implementation failure without clipping, restart, or recapitalization"
        ),
        "superseded_initial_lock": {
            "path": str(superseded_lock.relative_to(REPO_ROOT)),
            "sha256": sha256_file(superseded_lock),
        },
        "superseded_output_path": str(superseded_outputs.relative_to(REPO_ROOT)),
        "superseded_amendment1_lock": {
            "path": str(superseded_v2_lock.relative_to(REPO_ROOT)),
            "sha256": sha256_file(superseded_v2_lock),
        },
        "superseded_amendment1_runtime_output_path": str(
            superseded_v2_output.relative_to(REPO_ROOT)
        ),
        "system_registry_total": 103,
        "system_stratum_counts": expected,
        "primary_system_denominator_F_plus_T": 67,
        "candidate_family_size": 62,
        "holdout_markets": markets,
        "retrospective_markets": ["USA"],
        "holdout_label": "geographically external amended validation; overlapping dates, not a pristine temporal holdout",
        "primary_cost_bps_one_way": 10,
        "cost_sensitivity_bps_one_way": [0, 5, 10, 25, 50],
        "bootstrap_seed": 20260802,
        "bootstrap_block_months": 6,
        "bootstrap_minimum_replications": 2000,
        "multiplicity_primary": "Holm FWER with paired block-bootstrap max-|t| confirmation",
        "analysis_parameters": {
            "formation_start": "1999-07-31",
            "formation_end": "2024-11-30",
            "top_n": 1000,
            "quantile": 0.1,
            "min_side": 20,
            "allowed_missing_return_policies": ["zero", "adverse_100"],
            "minimum_bootstrap_replications": 2000,
            "limited_liability_failure_threshold_total_return": -1.0,
            "failed_candidate_multiplicity_input_p_value": 1.0,
        },
        "file_sha256": relative_hashes,
        "data_inputs": data_inputs,
        "paid_api_calls_before_lock": 0,
        "openrouter_spend_usd_before_lock": 0.0,
    }
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print(lock_path)
    print(sha256_file(lock_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
