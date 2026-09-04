#!/usr/bin/env python3
"""Evaluate CogAlpha's showcased evolved liquidity factor on monthly U.S./JKP data."""
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

from alpha_evolve.headline_backtest import build_strategy_path, formation_universe, return_statistics
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


CANDIDATE_ID = "cogalpha_evolved_price_impact"
SOURCE_FUNCTION = "factor_price_impact_per_vol_tanh_1d"
SOURCE_FORMULA = "tanh(abs(close-open)/(volume*close+1e-9))"
INPUT_COLUMNS = ["id", "permno", "eom", "me", "ret", "ret_exc_lead1m", "prc", "dolvol"]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def monthly_price_impact(frame: pd.DataFrame) -> pd.Series:
    """Adapt |close-open|/dollar-volume to a formation-month total-return price move."""
    ret = pd.to_numeric(frame["ret"], errors="coerce")
    price = pd.to_numeric(frame["prc"], errors="coerce").abs()
    dollar_volume = pd.to_numeric(frame["dolvol"], errors="coerce")
    raw = ret.abs().mul(price).div(dollar_volume + 1e-9)
    raw = raw.where(dollar_volume.gt(0) & price.gt(0))
    return pd.Series(np.tanh(raw), index=frame.index).replace([np.inf, -np.inf], np.nan)


def load_panel(path: Path, settings: dict) -> tuple[pd.DataFrame, pd.Series]:
    raw = pd.read_parquet(
        path,
        columns=INPUT_COLUMNS,
        filters=[
            ("eom", ">=", pd.Timestamp(settings["formation_start"])),
            ("eom", "<=", pd.Timestamp(settings["realized_return_end"])),
        ],
    )
    formed = formation_universe(
        raw,
        settings["formation_start"],
        settings["formation_end"],
        settings["top_n_by_formation_market_equity"],
    )
    return formed, monthly_price_impact(formed)


def build_metrics(
    contract: dict, root: Path, paths: dict[str, pd.DataFrame]
) -> tuple[list[dict], list[dict]]:
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    factors = pd.read_csv(root / contract["factor_panel_path"], parse_dates=["month"])
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
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
        raise ValueError("incomplete CogAlpha partial return path")
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
        raise ValueError("completed M041 run already exists")
    study = root / "paper_runs/us_jkp_headline"
    contract_path, recipe_path = study / "benchmark_contract.json", output / "recipe.json"
    component_path = root / "paper_runs/paper_replication_audits/cogalpha/component_execution.json"
    contract, recipe = json.loads(contract_path.read_text()), json.loads(recipe_path.read_text())
    component = json.loads(component_path.read_text())
    if contract["status"] != "frozen":
        raise ValueError("benchmark contract is not frozen")
    if recipe["candidate_id"] != CANDIDATE_ID or recipe["source_function"] != SOURCE_FUNCTION:
        raise ValueError("CogAlpha candidate identity mismatch")
    if recipe["source_formula"] != SOURCE_FORMULA or component["published_factor_listings_executed"] != 3:
        raise ValueError("CogAlpha source listing evidence mismatch")
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
    formed, score = load_panel(Path(contract["data"]["path"]), settings)
    paths, holdings = {}, None
    for policy in ["zero", "adverse_100"]:
        paths[policy], held = build_strategy_path(formed, score, settings, policy)
        if policy == "zero":
            holdings = held
    if any(not path.path_status.eq("ok").all() for path in paths.values()):
        raise ValueError("CogAlpha partial lacks complete formation coverage")
    private_holdings = root / "artifacts/us_jkp_headline/v1/M041_formation_holdings.parquet"
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
        "milestone_id": "M041",
        "candidate_id": CANDIDATE_ID,
        "benchmark_id": contract["benchmark_id"],
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "contract_sha256": digest(contract_path),
        "recipe_sha256": digest(recipe_path),
        "component_execution_sha256": digest(component_path),
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
        "--output", type=Path, default=Path("paper_runs/us_jkp_headline/M041_cogalpha")
    )
    args = parser.parse_args()
    os.umask(0o077)
    output = args.output if args.output.is_absolute() else args.root / args.output
    evaluate(args.root.resolve(), output.resolve())


if __name__ == "__main__":
    main()
