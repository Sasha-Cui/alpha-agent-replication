#!/usr/bin/env python3
"""Evaluate the frozen GuruAgents Buffett score on monthly U.S./JKP data."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm

from alpha_evolve.headline_backtest import formation_universe, return_statistics
from alpha_evolve.submission_analysis import (
    automatic_hac_lag,
    drift_weights,
    missing_return_gross_weight,
    realized_portfolio_return,
    traded_notional,
    weight_diagnostics,
)
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


CANDIDATE_ID = "guruagents_buffett_deterministic_score"
INPUT_COLUMNS = [
    "id", "permno", "eom", "me", "ret", "ret_exc_lead1m", "at_be", "ebit_int",
    "ni_be", "ni_sale", "at_turnover", "be_me", "ni_me", "fcf_me", "ca_cl",
    "nwc_at", "ocf_me", "capx_at", "at_me", "ebit_at", "tax_pi", "cash_at",
]
BASE_WEIGHTS = {
    "roe": 0.28,
    "interest_coverage": 0.22,
    "profit_margin": 0.18,
    "asset_turnover": 0.12,
    "valuation": 0.10,
    "current_ratio": 0.05,
    "working_capital_ratio": 0.05,
}
VALUATION_WEIGHTS = {"fcf_yield": 0.55, "pb_inverse": 0.25, "pe_inverse": 0.20}
QUALITY_POSITIVE_WEIGHTS = {"roce": 0.18, "cash_conversion": 0.10}
QUALITY_POSITIVE_BUDGET = 0.38
QUALITY_NEGATIVE_BUDGET = 0.06


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def winsorized_minmax(values: pd.Series) -> pd.Series:
    """Apply the source prompt's 5/95 winsorization and [0,1] scaling."""
    x = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    observed = x.dropna()
    result = pd.Series(np.nan, index=x.index, dtype="float64")
    if observed.empty:
        return result
    low, high = observed.quantile([0.05, 0.95]).to_numpy(dtype="float64")
    clipped = x.clip(lower=low, upper=high)
    spread = high - low
    if not np.isfinite(spread) or spread <= 0:
        result.loc[x.notna()] = 0.5
        return result
    return (clipped - low) / spread


def weighted_available(
    values: pd.DataFrame,
    weights: dict[str, float],
    *,
    total_weight: float,
    default: float = np.nan,
) -> pd.Series:
    """Drop missing components and proportionally restore the specified budget."""
    numerator = pd.Series(0.0, index=values.index)
    denominator = pd.Series(0.0, index=values.index)
    for name, weight in weights.items():
        finite = np.isfinite(values[name])
        numerator = numerator.add(values[name].where(finite, 0.0) * weight)
        denominator = denominator.add(finite.astype(float) * weight)
    result = numerator.div(denominator).mul(total_weight)
    return result.where(denominator.gt(0), default)


def buffett_components(frame: pd.DataFrame) -> pd.DataFrame:
    """Execute the disclosed Buffett prompt score without using a future return."""
    raw = pd.DataFrame(index=frame.index)
    for name in INPUT_COLUMNS:
        if name not in {"id", "permno", "eom"} and name in frame:
            raw[name] = pd.to_numeric(frame[name], errors="coerce").replace([np.inf, -np.inf], np.nan)

    raw["debt_to_equity"] = (raw["at_be"] - 1.0).where(raw["at_be"].ge(1.0))
    raw["interest_coverage"] = raw["ebit_int"]
    raw["roe"] = raw["ni_be"]
    raw["profit_margin"] = raw["ni_sale"]
    raw["asset_turnover"] = raw["at_turnover"].where(raw["at_turnover"].gt(0))
    raw["fcf_yield"] = raw["fcf_me"]
    raw["pb"] = (1.0 / raw["be_me"]).where(raw["be_me"].gt(0))
    raw["pe"] = (1.0 / raw["ni_me"]).where(raw["ni_me"].gt(0))
    raw["current_ratio"] = raw["ca_cl"].where(raw["ca_cl"].gt(0))
    raw["working_capital_ratio"] = raw["nwc_at"]
    raw["cash_conversion"] = raw["ocf_me"].div(raw["ni_me"]).replace([np.inf, -np.inf], np.nan)
    cl_at = raw["nwc_at"].div(raw["ca_cl"] - 1.0).replace([np.inf, -np.inf], np.nan)
    cl_at = cl_at.where(cl_at.between(0, 1))
    invested_capital_at = 1.0 - cl_at - raw["cash_at"]
    effective_tax = raw["tax_pi"].clip(lower=0, upper=0.35).fillna(0.21)
    raw["roce"] = raw["ebit_at"].mul(1.0 - effective_tax).div(invested_capital_at)
    raw["roce"] = raw["roce"].where(invested_capital_at.gt(0)).replace([np.inf, -np.inf], np.nan)
    raw["owner_earnings_yield"] = raw["ocf_me"] - 0.6 * raw["capx_at"].abs() * raw["at_me"]
    raw["capex_intensity"] = raw["capx_at"].abs().div(raw["asset_turnover"])
    raw["capex_intensity"] = raw["capex_intensity"].replace([np.inf, -np.inf], np.nan)

    scaled_names = [
        "roe", "interest_coverage", "profit_margin", "asset_turnover", "fcf_yield",
        "pb", "pe", "current_ratio", "working_capital_ratio", "roce",
        "cash_conversion", "capex_intensity",
    ]
    scaled = pd.DataFrame({name: winsorized_minmax(raw[name]) for name in scaled_names})
    valuation_inputs = pd.DataFrame(
        {
            "fcf_yield": scaled["fcf_yield"],
            "pb_inverse": 1.0 - scaled["pb"],
            "pe_inverse": 1.0 - scaled["pe"],
        }
    )
    raw["valuation"] = weighted_available(
        valuation_inputs, VALUATION_WEIGHTS, total_weight=1.0, default=0.5
    )
    base_inputs = pd.DataFrame(
        {
            "roe": scaled["roe"],
            "interest_coverage": scaled["interest_coverage"],
            "profit_margin": scaled["profit_margin"],
            "asset_turnover": scaled["asset_turnover"],
            "valuation": raw["valuation"],
            "current_ratio": scaled["current_ratio"],
            "working_capital_ratio": scaled["working_capital_ratio"],
        }
    )
    raw["base"] = weighted_available(base_inputs, BASE_WEIGHTS, total_weight=1.0)
    quality_inputs = pd.DataFrame(
        {"roce": scaled["roce"], "cash_conversion": scaled["cash_conversion"]}
    )
    raw["quality_positive"] = weighted_available(
        quality_inputs,
        QUALITY_POSITIVE_WEIGHTS,
        total_weight=QUALITY_POSITIVE_BUDGET,
        default=0.0,
    )
    raw["quality_negative"] = scaled["capex_intensity"].fillna(0.0) * QUALITY_NEGATIVE_BUDGET

    adjustment = pd.Series(0.0, index=raw.index)
    adjustment += (raw["roe"].ge(0.15) & raw["debt_to_equity"].le(0.5)).astype(float) * 0.05
    adjustment += raw["interest_coverage"].ge(10).astype(float) * 0.03
    adjustment += raw["profit_margin"].ge(0.15).astype(float) * 0.02
    adjustment += raw["owner_earnings_yield"].ge(0.05).astype(float) * 0.03
    adjustment -= raw["debt_to_equity"].gt(1.0).astype(float) * 0.08
    adjustment -= raw["debt_to_equity"].gt(2.0).astype(float) * 0.05
    adjustment -= raw["interest_coverage"].lt(5).astype(float) * 0.05
    adjustment -= (raw["pe"].gt(35) | raw["pb"].gt(6)).astype(float) * 0.05
    adjustment -= raw["fcf_yield"].le(0).astype(float) * 0.08
    raw["adjustment"] = adjustment
    raw["score_unrounded"] = (
        raw["base"] + raw["quality_positive"] - raw["quality_negative"] + raw["adjustment"]
    ).clip(lower=0, upper=1)
    raw["score"] = raw["score_unrounded"].round(2)
    return raw


def score_proportional_weights(frame: pd.DataFrame) -> pd.Series:
    """Form the source's long-only score-proportional portfolio without t+1 filtering."""
    x = frame[["security_id", "score"]].replace([np.inf, -np.inf], np.nan).dropna()
    x = x.drop_duplicates("security_id", keep="last").set_index("security_id")
    x = x.loc[x.score.gt(0)]
    if x.empty or not np.isfinite(x.score.sum()) or x.score.sum() <= 0:
        return pd.Series(dtype="float64")
    return (x.score / x.score.sum()).sort_index()


def load_panel(path: Path, settings: dict) -> pd.DataFrame:
    raw = pd.read_parquet(
        path,
        columns=INPUT_COLUMNS,
        filters=[("eom", ">=", pd.Timestamp(settings["formation_start"])),
                 ("eom", "<=", pd.Timestamp(settings["realized_return_end"]))],
    )
    return formation_universe(
        raw,
        settings["formation_start"],
        settings["formation_end"],
        settings["top_n_by_formation_market_equity"],
    )


def build_strategy_path(
    formed: pd.DataFrame, settings: dict, missing_policy: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = {month: part for month, part in formed.groupby("month", sort=True)}
    months = pd.date_range(settings["formation_start"], settings["formation_end"], freq=pd.offsets.MonthEnd())
    previous = pd.Series(dtype="float64")
    previous_returns = pd.Series(dtype="float64")
    failed = False
    rows, holdings = [], []
    for month in months:
        frame = groups[month].copy()
        if failed:
            rows.append({"formation_month": month, "month": month + pd.offsets.MonthEnd(1),
                         "path_status": "failed_nonpositive_nav", "gross_return": np.nan})
            continue
        components = buffett_components(frame)
        frame["score"] = components["score"]
        weights = score_proportional_weights(frame)
        pretrade = drift_weights(previous, previous_returns)
        turnover = traded_notional(weights, pretrade)
        gross = realized_portfolio_return(weights, frame, missing_return_policy=missing_policy)
        total = realized_portfolio_return(weights, frame, return_col="ret_total_lead1m")
        failed = bool(np.isfinite(total) and total <= -1.0)
        status = "failed_nonpositive_nav" if failed else "insufficient_formation_coverage" if weights.empty else "ok"
        rows.append(
            {
                "formation_month": month,
                "month": month + pd.offsets.MonthEnd(1),
                "path_status": status,
                "gross_return": gross,
                "total_security_return": total,
                "traded_notional": turnover,
                "formation_universe": len(frame),
                "finite_signal_count": int(np.isfinite(frame["score"]).sum()),
                "missing_forward_return_gross_weight": missing_return_gross_weight(weights, frame),
                "missing_total_return_gross_weight": missing_return_gross_weight(
                    weights, frame, return_col="ret_total_lead1m"
                ),
                **weight_diagnostics(weights),
            }
        )
        score_by_id = frame.set_index("security_id")["score"]
        holdings.extend(
            {
                "formation_month": month,
                "month": month + pd.offsets.MonthEnd(1),
                "security_id": security,
                "weight": weight,
                "score": float(score_by_id.loc[security]),
            }
            for security, weight in weights.items()
        )
        previous = weights
        previous_returns = frame.set_index("security_id")["ret_total_lead1m"].fillna(0.0)
    return pd.DataFrame(rows), pd.DataFrame(holdings)


def build_metrics(
    contract: dict, root: Path, paths: dict[str, pd.DataFrame]
) -> tuple[list[dict], list[dict]]:
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    factors = pd.read_csv(root / contract["factor_panel_path"], parse_dates=["month"])
    costs = sorted(set([1.0, *map(float, settings["cost_sensitivity_bps_one_way"])]))
    cases = [("zero", cost) for cost in costs]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack(
        [
            paths[policy].gross_return.to_numpy()
            - cost / 10000 * paths[policy].traded_notional.to_numpy()
            for policy, cost in cases
        ]
    )
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError("incomplete GuruAgents Buffett return path")
    merged = paths["zero"][["month"]].merge(factors, on="month", validate="one_to_one")
    attr = contract["attribution"]
    reconstruction = rolling_crossfit_reconstruction(
        merged[contract["factor_columns"]].to_numpy(float),
        y,
        attr["train_months"],
        attr["validation_months"],
        np.asarray(attr["ridge_lambdas"]),
        attr["n_unpenalized"],
    )
    eval_dates = paths["zero"].month.iloc[attr["train_months"]:].reset_index(drop=True)
    lags, metrics, residual_rows = automatic_hac_lag(len(eval_dates)), [], []
    for column, ((policy, cost), name) in enumerate(zip(cases, names)):
        net, residual = y[:, column], reconstruction.residuals[:, column]
        alpha, se = float(residual.mean()), float(hac_mean_se(residual, lags))
        t_value = alpha / se
        p_value = float(2 * norm.sf(abs(t_value)))
        path = paths[policy]
        metrics.append(
            {
                "case": name,
                "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
                "paper_cost": policy == "zero" and cost == 1.0,
                "missing_return_policy": policy,
                "cost_bps_one_way": cost,
                **{f"full_{key}": value for key, value in return_statistics(net).items()},
                "evaluation_months": len(eval_dates),
                "evaluation_start": str(eval_dates.iloc[0].date()),
                "evaluation_end": str(eval_dates.iloc[-1].date()),
                "jkp_residual_mean_annualized": 12 * alpha,
                "jkp_residual_se_annualized": 12 * se,
                "jkp_residual_t_hac": t_value,
                "jkp_residual_p_two_sided": p_value,
                "exploratory_bonferroni69_p": min(1.0, 69 * p_value),
                "hac_lags": lags,
                "average_traded_notional": float(path.traded_notional.mean()),
                "annualized_linear_cost_drag": float(
                    12 * cost / 10000 * path.traded_notional.mean()
                ),
                "minimum_finite_signal_count": int(path.finite_signal_count.min()),
                "maximum_missing_forward_gross_weight": float(
                    path.missing_forward_return_gross_weight.max()
                ),
            }
        )
        residual_rows.extend(
            {
                "case": name,
                "month": str(month.date()),
                "net_return": float(value),
                "factor_replication_return": float(fitted),
                "residual": float(remain),
                "selected_lambda": float(lam),
            }
            for month, value, fitted, remain, lam in zip(
                eval_dates,
                net[attr["train_months"]:],
                reconstruction.fitted_values[:, column],
                residual,
                reconstruction.selected_lambdas[:, column],
            )
        )
    return metrics, residual_rows


def evaluate(root: Path, output: Path) -> None:
    if (output / "run_manifest.json").exists():
        raise ValueError("completed M033 run already exists")
    study = root / "paper_runs/us_jkp_headline"
    contract_path, recipe_path = study / "benchmark_contract.json", output / "recipe.json"
    audit_path = root / "paper_runs/paper_replication_audits/guruagents/source_prompt_conformance.csv"
    contract, recipe = json.loads(contract_path.read_text()), json.loads(recipe_path.read_text())
    if contract["status"] != "frozen" or recipe["candidate_id"] != CANDIDATE_ID:
        raise ValueError("frozen contract or GuruAgents recipe mismatch")
    prompt_audit = pd.read_csv(audit_path)
    buffett = prompt_audit.loc[prompt_audit.agent.eq("Warren Buffett")].iloc[0]
    if buffett.source_prompt_sha256 != recipe["source_prompt_sha256"]:
        raise ValueError("GuruAgents Buffett prompt hash mismatch")
    implementation = [
        Path(__file__).resolve(),
        root / "src/alpha_evolve/headline_backtest.py",
        root / "src/alpha_evolve/submission_analysis.py",
        root / "scripts/run_broad_jkp_crossfit.py",
    ]
    frozen = [recipe_path, *implementation]
    relative = [str(path.relative_to(root)) for path in frozen]
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *relative], cwd=root, check=True)
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    formed = load_panel(Path(contract["data"]["path"]), settings)
    paths, holdings = {}, None
    for policy in ["zero", "adverse_100"]:
        paths[policy], held = build_strategy_path(formed, settings, policy)
        if policy == "zero":
            holdings = held
    if any(not path.path_status.eq("ok").all() for path in paths.values()):
        raise ValueError("GuruAgents Buffett path lacks complete formation coverage")
    private_holdings = root / "artifacts/us_jkp_headline/v1/M033_formation_holdings.parquet"
    assert holdings is not None
    holdings.to_parquet(private_holdings, index=False)
    metrics, residual_rows = build_metrics(contract, root, paths)
    output.mkdir(parents=True, exist_ok=True)
    pd.concat(
        [frame.assign(missing_return_policy=policy) for policy, frame in paths.items()]
    ).to_csv(output / "monthly_returns.csv", index=False)
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = paths["zero"].copy()
    primary_path["net_return"] = (
        primary_path.gross_return - 0.001 * primary_path.traded_notional
    )
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    public_names = [
        "monthly_returns.csv", "primary_monthly_returns.csv", "metrics.csv",
        "attribution_residuals.csv",
    ]
    manifest = {
        "status": "evaluated_partial",
        "milestone_id": "M033",
        "candidate_id": CANDIDATE_ID,
        "benchmark_id": contract["benchmark_id"],
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "contract_sha256": digest(contract_path),
        "recipe_sha256": digest(recipe_path),
        "source_prompt_conformance_sha256": digest(audit_path),
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.system(),
        },
        "primary_result": primary,
        "private_holdings_path": str(private_holdings),
        "private_holdings_sha256": digest(private_holdings),
        "prior_jkp_outcomes_seen": True,
        "confirmatory_claim": False,
        "implementation_sha256": {
            str(path.relative_to(root)): digest(path) for path in implementation
        },
        "output_sha256": {name: digest(output / name) for name in public_names},
    }
    (output / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(primary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output", type=Path,
        default=Path("paper_runs/us_jkp_headline/M033_guruagents_buffett"),
    )
    args = parser.parse_args()
    os.umask(0o077)
    output = args.output if args.output.is_absolute() else args.root / args.output
    evaluate(args.root.resolve(), output.resolve())


if __name__ == "__main__":
    main()
