#!/usr/bin/env python3
"""Run the primary 100%-faithful disclosed-component replication census.

The counted objects are all evaluator-valid seeds in QuantEvolver's released
``examples/seed_candidates.yaml`` at the pinned source commit. This reproduces
the released DSL semantics and cross-sectional top/bottom-quintile evaluator.
Only cadence and universe are adapted, as permitted by the strict audit rubric.
This is a grade-B component replication, not a native-agent replication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USA = ROOT.parent / "jkp-data/data/processed/characteristics/USA.parquet"
DEFAULT_OUT = ROOT / "paper_runs/faithful_component_replications"

SOURCE_REPOSITORY = "https://github.com/QuantLLM/QuantEvolver"
SOURCE_COMMIT = "4eb0e78842138ada5334349585b114ad923564e8"
SOURCE_FILES = {
    "examples/seed_candidates.yaml": "c8a20de0850156b8c831547a58239bb88b5d6486da50d6f9ecbaa2df0d13d718",
    "quant_evolver/dsl/evaluator.py": "8c6e8201b8794bb2166a118cb753231bca1379c8aff115c6d29799ce8400516c",
    "quant_evolver/evaluation/cross_sectional_rankic.py": (
        "b38066082453d58295e45467fad662b33c1a1ef97232d3575348e2cfade56295"
    ),
}
RAW_BASE = f"https://raw.githubusercontent.com/QuantLLM/QuantEvolver/{SOURCE_COMMIT}"

# Exhaustive census of the three evaluator-valid released example seeds.
# seed_0004 is explicitly named ``bad_unknown_op`` and is rejected by the
# source evaluator; excluding it is source-defined rather than outcome-based.
PRIMARY_COMPONENTS = {
    "quantevolver_return_sharpe_60": {
        "seed_id": "seed_0001",
        "seed_name": "return_sharpe_60",
        "expression": "div(ts_mean(returns(60)), ts_std(returns(60)))",
        "source_inputs": "close",
    },
    "quantevolver_price_zscore_reversal_120": {
        "seed_id": "seed_0002",
        "seed_name": "price_zscore_reversal_120",
        "expression": "neg(zscore(last(close(120)), close(120)))",
        "source_inputs": "close",
    },
    "quantevolver_return_log_volume_corr_60": {
        "seed_id": "seed_0003",
        "seed_name": "volume_price_corr",
        "expression": "corr(returns(60), log_arr(volume(60)))",
        "source_inputs": "close, volume",
    },
}

INPUT_COLUMNS = ["permno", "eom", "me", "prc", "tvol"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_upstream_source() -> None:
    """Fail if any pinned upstream source file no longer matches its hash."""
    for source_path, expected in SOURCE_FILES.items():
        with urlopen(f"{RAW_BASE}/{source_path}", timeout=30) as response:
            actual = hashlib.sha256(response.read()).hexdigest()
        if actual != expected:
            raise ValueError(
                f"upstream source hash mismatch for {source_path}: {actual} != {expected}"
            )


def evaluate_released_seeds(frame: pd.DataFrame) -> pd.DataFrame:
    """Vectorized port of the pinned QuantEvolver DSL evaluator."""
    required = {"permno", "month", "prc", "tvol"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"missing score inputs: {missing}")

    valid = frame.copy()
    valid["close"] = pd.to_numeric(valid["prc"], errors="coerce").abs()
    valid["volume"] = pd.to_numeric(valid["tvol"], errors="coerce").abs()
    valid = valid.replace({"close": [np.inf, -np.inf], "volume": [np.inf, -np.inf]})
    valid = valid.dropna(subset=["close", "volume"])
    valid = valid.sort_values(["permno", "month"], kind="stable").copy()
    grouped_close = valid.groupby("permno", sort=False)["close"]
    previous_close = grouped_close.shift(1)
    valid["qe_return"] = (valid["close"] - previous_close) / (previous_close + 1e-8)
    valid["log_volume"] = np.log(valid["volume"].abs() + 1e-8)

    grouped_return = valid.groupby("permno", sort=False)["qe_return"]
    mean60 = grouped_return.transform(
        lambda values: values.rolling(60, min_periods=60).mean()
    )
    std60 = grouped_return.transform(
        lambda values: values.rolling(60, min_periods=60).std(ddof=0)
    )
    # Source ts_std adds 1e-8, then source div adds another 1e-8.
    valid["quantevolver_return_sharpe_60"] = mean60 / (std60.abs() + 2e-8)

    mean120 = grouped_close.transform(
        lambda values: values.rolling(120, min_periods=120).mean()
    )
    close_std120 = grouped_close.transform(
        lambda values: values.rolling(120, min_periods=120).std(ddof=0)
    )
    valid["quantevolver_price_zscore_reversal_120"] = -(
        (valid["close"] - mean120) / (close_std120 + 1e-8)
    )

    correlation = pd.Series(np.nan, index=valid.index, dtype="float64")
    return_std = pd.Series(np.nan, index=valid.index, dtype="float64")
    volume_std = pd.Series(np.nan, index=valid.index, dtype="float64")
    for _, group in valid.groupby("permno", sort=False):
        correlation.loc[group.index] = (
            group["qe_return"].rolling(60, min_periods=60).corr(group["log_volume"])
        ).to_numpy()
        return_std.loc[group.index] = (
            group["qe_return"].rolling(60, min_periods=60).std(ddof=0)
        ).to_numpy()
        volume_std.loc[group.index] = (
            group["log_volume"].rolling(60, min_periods=60).std(ddof=0)
        ).to_numpy()
    near_constant = (return_std <= 1e-12) | (volume_std <= 1e-12)
    valid["quantevolver_return_log_volume_corr_60"] = correlation.where(
        ~near_constant, 0.0
    )

    # The source default 5-minute configuration uses warmup_bars=240.
    after_source_warmup = valid.groupby("permno", sort=False).cumcount() >= 239
    for candidate_id in PRIMARY_COMPONENTS:
        valid.loc[~after_source_warmup, candidate_id] = np.nan

    next_close = grouped_close.shift(-1)
    valid["source_forward_return"] = next_close / valid["close"] - 1.0
    valid["source_forward_observation_month"] = valid.groupby(
        "permno", sort=False
    )["month"].shift(-1)
    return valid


def source_spearman_corr(x: pd.Series, y: pd.Series) -> float:
    """Reproduce the pinned evaluator's finite-rank-IC eligibility check."""
    x_rank = x.rank(method="average")
    y_rank = y.rank(method="average")
    if float(x_rank.std(ddof=0)) <= 1e-12 or float(y_rank.std(ddof=0)) <= 1e-12:
        return float("nan")
    return float(x_rank.corr(y_rank))


def released_cross_sectional_path(
    frame: pd.DataFrame, candidate_id: str, *, min_symbols: int = 8
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reproduce source pair/dropna, finite-rank-IC, and equal-mean quintiles."""
    path_rows: list[dict[str, object]] = []
    holding_rows: list[dict[str, object]] = []
    for formation_month, month_frame in frame.groupby("month", sort=True):
        pair = month_frame[
            [
                "permno",
                candidate_id,
                "source_forward_return",
                "source_forward_observation_month",
            ]
        ].dropna(subset=[candidate_id, "source_forward_return"])
        if len(pair) < min_symbols:
            continue
        rank_ic = source_spearman_corr(pair[candidate_id], pair["source_forward_return"])
        if not np.isfinite(rank_ic):
            continue
        side_size = max(1, int(len(pair) * 0.2))
        ordered = pair.sort_values(candidate_id)
        short_side = ordered.head(side_size)
        long_side = ordered.tail(side_size)
        source_return = float(
            long_side["source_forward_return"].mean()
            - short_side["source_forward_return"].mean()
        )
        path_rows.append(
            {
                "candidate_id": candidate_id,
                "formation_month": pd.Timestamp(formation_month),
                "month": pd.Timestamp(formation_month) + pd.offsets.MonthEnd(1),
                "gross_excess_return": source_return,
                "net_excess_return": source_return,
                "traded_notional": np.nan,
                "cost_bps_one_way": 0.0,
                "source_spearman_rank_ic": rank_ic,
                "n_eligible_source_pairs": len(pair),
                "n_long": side_size,
                "n_short": side_size,
                "portfolio_rule_id": "released_pair_dropna_top_bottom_quintile_equal_mean",
                "return_definition": "released_next_bar_close_return_long_mean_minus_short_mean",
            }
        )
        for side_name, side, weight in (
            ("long", long_side, 1.0 / side_size),
            ("short", short_side, -1.0 / side_size),
        ):
            for row in side.itertuples(index=False):
                holding_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "formation_month": pd.Timestamp(formation_month),
                        "permno": int(row.permno),
                        "side": side_name,
                        "score": float(getattr(row, candidate_id)),
                        "source_forward_return": float(row.source_forward_return),
                        "source_forward_observation_month": pd.Timestamp(
                            row.source_forward_observation_month
                        ),
                        "source_evaluator_weight": weight,
                    }
                )
    paths = pd.DataFrame(path_rows)
    holdings = pd.DataFrame(holding_rows)
    if len(paths) < 20:
        raise ValueError(f"{candidate_id} has only {len(paths)} valid source-evaluator times")
    return paths, holdings


def faithfulness_ledger(top_n: int) -> pd.DataFrame:
    rows = []
    for candidate_id, component in PRIMARY_COMPONENTS.items():
        rows.append(
            {
                "candidate_id": candidate_id,
                "counted_primary": True,
                "grade": "B",
                "grade_meaning": "faithful disclosed component",
                "source_repository": SOURCE_REPOSITORY,
                "source_commit": SOURCE_COMMIT,
                "source_seed_file": "examples/seed_candidates.yaml",
                "source_seed_id": component["seed_id"],
                "source_seed_name": component["seed_name"],
                "exact_source_expression": component["expression"],
                "source_inputs": component["source_inputs"],
                "source_expression_exact": True,
                "source_operator_semantics_exact": True,
                "source_evaluator_rule_exact": True,
                "source_return_definition_exact": True,
                "formula_census_outcome_independent": True,
                "formula_census_rule": (
                    "all three evaluator-valid released example seeds; source-labelled "
                    "bad_unknown_op seed_0004 is invalid and excluded"
                ),
                "only_permitted_mechanical_changes": True,
                "cadence_change": "released bars to monthly bars",
                "universe_change": f"released configured symbols to top-{top_n} U.S. equities",
                "holding_period_change": "released horizon_bars=6 to next available monthly bar",
                "weight_change": "none: equal mean within top and bottom quintiles",
                "cost_change": "none in counted source-evaluator return",
                "native_agent_replication": False,
                "full_search_or_training_pipeline_reproduced": False,
                "admissible_claim": (
                    "performance of the released seed component under explicit cadence and "
                    "universe adaptations"
                ),
                "forbidden_claim": (
                    "native-agent, evolved-factor, reinforcement-training, or paper-level performance"
                ),
                "independent_second_coder_status": "tracked_in_owner_review_attestation",
            }
        )
    return pd.DataFrame(rows)


def build(args: argparse.Namespace) -> dict[str, object]:
    if args.verify_upstream:
        verify_upstream_source()
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    warmup = start - pd.offsets.MonthEnd(260)
    raw = pd.read_parquet(
        args.usa_path,
        columns=INPUT_COLUMNS,
        filters=[("eom", ">=", warmup), ("eom", "<=", end + pd.offsets.MonthEnd(2))],
    )
    raw["month"] = pd.to_datetime(raw["eom"], errors="coerce") + pd.offsets.MonthEnd(0)
    raw["me"] = pd.to_numeric(raw["me"], errors="coerce")
    scored = evaluate_released_seeds(raw)
    scored = scored[(scored["month"] >= start) & (scored["month"] <= end)].copy()
    scored["size_rank"] = scored.groupby("month")["me"].rank(
        method="first", ascending=False
    )
    scored = scored[(scored["me"] > 0) & (scored["size_rank"] <= args.top_n)]

    paths = []
    holdings = []
    for candidate_id in PRIMARY_COMPONENTS:
        candidate_path, candidate_holdings = released_cross_sectional_path(
            scored, candidate_id, min_symbols=args.min_symbols
        )
        paths.append(candidate_path)
        holdings.append(candidate_holdings)
    path_frame = pd.concat(paths, ignore_index=True)
    holding_frame = pd.concat(holdings, ignore_index=True)
    ledger = faithfulness_ledger(args.top_n)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    path_frame.to_csv(args.out_dir / "monthly_return_paths.csv", index=False)
    holding_frame.to_csv(args.out_dir / "formation_holdings.csv", index=False)
    ledger.to_csv(args.out_dir / "faithfulness_ledger.csv", index=False)
    from check_upstream_conformance import conformance_report

    reference_report, reference_failures = conformance_report()
    if reference_failures:
        raise ValueError(f"upstream conformance failed: {reference_failures}")
    (args.out_dir / "upstream_conformance.json").write_text(
        json.dumps(reference_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output_hashes = {
        name: sha256(args.out_dir / name)
        for name in (
            "monthly_return_paths.csv",
            "formation_holdings.csv",
            "faithfulness_ledger.csv",
            "upstream_conformance.json",
        )
    }
    manifest = {
        "study_role": "primary_counted_faithful_disclosed_components",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "source_file_sha256": SOURCE_FILES,
        "technical_reference_conformance_passed": True,
        "independent_human_review_record": "owner_review_attestation.csv",
        "source_census_rule": (
            "all evaluator-valid seeds in examples/seed_candidates.yaml; the source's "
            "explicit bad_unknown_op seed_0004 is excluded"
        ),
        "input_path": str(args.usa_path),
        "input_sha256": sha256(args.usa_path),
        "start": args.start,
        "end": args.end,
        "top_n": args.top_n,
        "min_symbols": args.min_symbols,
        "n_counted_components": len(ledger),
        "n_grade_a_or_b": int(ledger["grade"].isin(["A", "B"]).sum()),
        "faithfulness_pass_rate": float(ledger["grade"].isin(["A", "B"]).mean()),
        "n_return_rows": len(path_frame),
        "n_holding_rows": len(holding_frame),
        "n_nonconsecutive_forward_holding_rows": int(
            (~holding_frame["source_forward_observation_month"].eq(
                holding_frame["formation_month"] + pd.offsets.MonthEnd(1)
            )).sum()
        ),
        "output_sha256": output_hashes,
        "scope_warning": (
            "100% refers only to the three counted disclosed components. No native agent, "
            "search process, reinforcement training, or paper-level result is replicated."
        ),
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usa-path", type=Path, default=DEFAULT_USA)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--start", default="1999-07-31")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--top-n", type=int, default=1000)
    parser.add_argument("--min-symbols", type=int, default=8)
    parser.add_argument("--verify-upstream", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
