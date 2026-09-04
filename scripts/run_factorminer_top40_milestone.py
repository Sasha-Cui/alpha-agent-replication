#!/usr/bin/env python3
"""Evaluate FactorMiner's frozen Top-40 IC-weighted library on monthly U.S./JKP data."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

from alpha_evolve.headline_backtest import build_strategy_path, return_statistics
from alpha_evolve.submission_analysis import automatic_hac_lag
from run_broad_jkp_crossfit import hac_mean_se, rolling_crossfit_reconstruction


PAPER_SOURCE_SHA256 = "36fea5dc198f772362166f3e59a5751cefd07e2cbfbb7a105c9ef583da79b669"
PAPER_FACTOR_TEX_SHA256 = "c65a7b94daae1d59feebb9cefce8a2478ae489c9c07365f0f33b32c46821fd4f"
FORMULA_LEDGER_SHA256 = "fb1d26440c14acd27a729d0b97ebbbc71479b266dfcd0b44eb81d7990f988fae"
INTERPRETER_COMMIT = "201309cfe3df51f84af8eeb509354d3853ae512a"
INPUT_COLUMNS = [
    "id", "permno", "eom", "me", "ret", "ret_exc_lead1m", "prc", "prc_high", "prc_low",
    "tvol", "dolvol",
]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def monthly_bars(raw: pd.DataFrame) -> pd.DataFrame:
    close = pd.to_numeric(raw.prc, errors="coerce").abs()
    ret = pd.to_numeric(raw.ret, errors="coerce")
    volume = pd.to_numeric(raw.tvol, errors="coerce")
    amount = pd.to_numeric(raw.dolvol, errors="coerce")
    opening = (close / (1.0 + ret)).where(ret.gt(-1.0) & np.isfinite(ret) & close.gt(0))
    vwap = (amount / volume).where(amount.gt(0) & volume.gt(0))
    return pd.DataFrame(
        {
            "$open": opening,
            "$high": pd.to_numeric(raw.prc_high, errors="coerce").abs(),
            "$low": pd.to_numeric(raw.prc_low, errors="coerce").abs(),
            "$close": close,
            "$volume": volume,
            "$amt": amount,
            "$vwap": vwap,
            "$returns": ret,
        },
        index=raw.index,
    )


def normalize_formula(value: str) -> str:
    return re.sub(r"\s+", "", value.replace(r"\allowbreak", "").replace(r"\$", "$"))


def parse_v2_tex(path: Path) -> list[tuple[str, str]]:
    rows = []
    for line in path.read_text().splitlines():
        match = re.match(r"\\frow\{(\d{3})\}\{\\texttt\{(.*)\}\}", line)
        if match:
            rows.append((match.group(1), normalize_formula(match.group(2))))
    if len(rows) != 110:
        raise ValueError(f"expected 110 v2 formulas, found {len(rows)}")
    return rows


def load_formulas(ledger_path: Path, paper_tex: Path) -> list[dict[str, str]]:
    with ledger_path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 110 or len({row["formula"] for row in rows}) != 110:
        raise ValueError("tracked FactorMiner ledger must contain 110 unique formulas")
    ledger = [(row["factor_id"], normalize_formula(row["formula"])) for row in rows]
    if ledger != parse_v2_tex(paper_tex):
        raise ValueError("tracked formula ledger differs from current v2 paper source")
    return [{"factor_id": row["factor_id"], "name": row["name"], "formula": row["formula"]} for row in rows]


def install_interpreter(checkout: Path):
    commit = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain"], text=True).strip()
    if commit != INTERPRETER_COMMIT or dirty:
        raise ValueError("FactorMiner replacement interpreter is not at its pinned clean commit")
    sys.path.insert(0, str(checkout))
    parser = importlib.import_module("factorminer.core.parser")
    expression_tree = importlib.import_module("factorminer.core.expression_tree")

    def nan_aware_ema(values: np.ndarray, window: int) -> np.ndarray:
        alpha = 2.0 / (window + 1)
        output = np.full_like(values, np.nan, dtype="float64")
        state = np.full(values.shape[0], np.nan, dtype="float64")
        for column in range(values.shape[1]):
            current = values[:, column]
            valid = np.isfinite(current)
            new = valid & ~np.isfinite(state)
            continuing = valid & np.isfinite(state)
            state[new] = current[new]
            state[continuing] = alpha * current[continuing] + (1 - alpha) * state[continuing]
            output[valid, column] = state[valid]
        return output

    expression_tree._ema = nan_aware_ema
    return parser.parse, commit


def load_dense_panel(path: Path, settings: dict) -> tuple[dict[str, np.ndarray], pd.DataFrame, np.ndarray, np.ndarray]:
    warmup = pd.Timestamp(settings["formation_start"]) - pd.offsets.MonthEnd(64)
    end = pd.Timestamp(settings["realized_return_end"])
    raw = pd.read_parquet(path, columns=INPUT_COLUMNS, filters=[("eom", ">=", warmup), ("eom", "<=", end)])
    raw["month"] = pd.to_datetime(raw.eom) + pd.offsets.MonthEnd(0)
    raw = raw.sort_values(["id", "month"], kind="stable")
    next_month = raw.groupby("id", sort=False).month.shift(-1)
    raw["ret_total_lead1m"] = raw.groupby("id", sort=False).ret.shift(-1)
    raw.loc[next_month.ne(raw.month + pd.offsets.MonthEnd(1)), "ret_total_lead1m"] = np.nan
    raw["me"] = pd.to_numeric(raw.me, errors="coerce")
    eligible = raw.me.gt(0) & raw.id.notna()
    ranks = raw.loc[eligible].groupby("month", sort=False).me.rank(method="first", ascending=False)
    keep = pd.Series(False, index=raw.index)
    keep.loc[ranks.index] = ranks.le(settings["top_n_by_formation_market_equity"])
    raw = raw.loc[keep].sort_values(["month", "id"], kind="stable").copy()
    formation = raw.loc[
        raw.month.between(pd.Timestamp(settings["formation_start"]), pd.Timestamp(settings["formation_end"]))
    ].copy()
    if formation.month.nunique() != 305 or formation.groupby("month").size().min() != 1000:
        raise ValueError("FactorMiner monthly common universe is incomplete")
    bars = monthly_bars(raw)
    bars["id"], bars["month"] = raw.id, raw.month
    instruments = pd.Index(sorted(raw.id.unique()), name="id")
    months = pd.date_range(raw.month.min(), pd.Timestamp(settings["formation_end"]), freq=pd.offsets.MonthEnd())
    data = {}
    for field in ("$open", "$high", "$low", "$close", "$volume", "$amt", "$vwap", "$returns"):
        data[field] = bars.pivot(index="id", columns="month", values=field).reindex(
            index=instruments, columns=months
        ).to_numpy(float)
    id_locations = pd.Series(np.arange(len(instruments)), index=instruments)
    month_locations = pd.Series(np.arange(len(months)), index=months)
    row_index = formation.id.map(id_locations).to_numpy(int)
    column_index = formation.month.map(month_locations).to_numpy(int)
    formation = formation.rename(columns={"id": "security_id", "me": "weight"}).reset_index(drop=True)
    return data, formation, row_index, column_index


def compute_features(
    formulas: list[dict[str, str]], data: dict[str, np.ndarray], row_index: np.ndarray,
    column_index: np.ndarray, parse: Any,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    values, coverage = {}, []
    expected_shape = next(iter(data.values())).shape
    for number, row in enumerate(formulas, start=1):
        result = parse(row["formula"]).evaluate(data)
        if result.shape != expected_shape:
            raise ValueError(f"FactorMiner factor {row['factor_id']} returned {result.shape}")
        selected = pd.to_numeric(pd.Series(result[row_index, column_index]), errors="coerce").to_numpy(float)
        values[row["factor_id"]] = selected
        coverage.append(
            {"factor_id": row["factor_id"], "name": row["name"], "rows": len(selected),
             "finite_rows": int(np.isfinite(selected).sum()),
             "finite_fraction": float(np.isfinite(selected).mean())}
        )
        if number == 1 or number % 10 == 0:
            print(f"factorminer_factor_progress={number}/110", flush=True)
    return pd.DataFrame(values), pd.DataFrame(coverage)


def select_ic_weighted(
    features: pd.DataFrame, panel: pd.DataFrame, *, training_months: int, top_n: int,
) -> pd.DataFrame:
    months = sorted(panel.month.unique())[:training_months]
    training = panel.month.isin(months)
    rows = []
    for factor_id in features:
        month_ics = []
        for month in months:
            mask = training & panel.month.eq(month)
            factor = features.loc[mask, factor_id]
            label = panel.loc[mask, "label"]
            finite = np.isfinite(factor) & np.isfinite(label)
            if finite.sum() >= 20:
                value = factor.loc[finite].rank(method="average").corr(label.loc[finite].rank(method="average"))
                if np.isfinite(value):
                    month_ics.append(float(value))
        mean_ic = float(np.mean(month_ics)) if month_ics else np.nan
        rows.append({"factor_id": str(factor_id), "mean_training_ic": mean_ic,
                     "absolute_mean_training_ic": abs(mean_ic), "training_ic_months": len(month_ics)})
    result = pd.DataFrame(rows).sort_values(
        ["absolute_mean_training_ic", "factor_id"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
    result["selection_rank"] = np.arange(1, len(result) + 1)
    result["selected"] = result.selection_rank.le(top_n)
    result["direction"] = np.where(result.mean_training_ic.ge(0), 1, -1)
    denominator = result.loc[result.selected, "absolute_mean_training_ic"].sum()
    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError("FactorMiner training ICs cannot define weights")
    result["weight"] = np.where(
        result.selected, result.absolute_mean_training_ic / denominator, 0.0
    )
    return result


def combined_score(features: pd.DataFrame, panel: pd.DataFrame, selection: pd.DataFrame, training_months: int) -> pd.Series:
    score = pd.Series(0.0, index=features.index)
    for row in selection.loc[selection.selected].itertuples():
        rank = features[row.factor_id].groupby(panel.month, sort=False).rank(method="average", pct=True)
        score += row.weight * row.direction * (2 * (rank - 0.5)).fillna(0.0)
    training = sorted(panel.month.unique())[:training_months]
    score.loc[panel.month.isin(training)] = np.nan
    return score


def cash_fill_warmup(path: pd.DataFrame) -> pd.DataFrame:
    result = path.copy()
    warmup = result.path_status.eq("insufficient_formation_coverage")
    columns = ["gross_return", "total_security_return", "traded_notional",
               "missing_forward_return_gross_weight", "missing_total_return_gross_weight"]
    result.loc[warmup, columns] = 0.0
    return result


def build_metrics(contract: dict, root: Path, paths: dict[str, pd.DataFrame]) -> tuple[list[dict], list[dict]]:
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    factors = pd.read_csv(root / contract["factor_panel_path"], parse_dates=["month"])
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack(
        [paths[policy].gross_return.to_numpy() - cost / 10000 * paths[policy].traded_notional.to_numpy()
         for policy, cost in cases]
    )
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError("incomplete FactorMiner partial return path")
    merged = paths["zero"][["month"]].merge(factors, on="month", validate="one_to_one")
    attr = contract["attribution"]
    reconstruction = rolling_crossfit_reconstruction(
        merged[contract["factor_columns"]].to_numpy(float), y, attr["train_months"],
        attr["validation_months"], np.asarray(attr["ridge_lambdas"]), attr["n_unpenalized"],
    )
    eval_dates = paths["zero"].month.iloc[attr["train_months"]:].reset_index(drop=True)
    lags, metrics, residual_rows = automatic_hac_lag(len(eval_dates)), [], []
    for column, ((policy, cost), name) in enumerate(zip(cases, names)):
        net, residual = y[:, column], reconstruction.residuals[:, column]
        alpha, se = float(residual.mean()), float(hac_mean_se(residual, lags))
        t_value, p_value = alpha / se, float(2 * norm.sf(abs(alpha / se)))
        path = paths[policy]
        metrics.append(
            {"case": name, "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
             "missing_return_policy": policy, "cost_bps_one_way": cost,
             **{f"full_{key}": value for key, value in return_statistics(net).items()},
             "evaluation_months": len(eval_dates), "evaluation_start": str(eval_dates.iloc[0].date()),
             "evaluation_end": str(eval_dates.iloc[-1].date()),
             "jkp_residual_mean_annualized": 12 * alpha, "jkp_residual_se_annualized": 12 * se,
             "jkp_residual_t_hac": t_value, "jkp_residual_p_two_sided": p_value,
             "exploratory_bonferroni69_p": min(1.0, 69 * p_value), "hac_lags": lags,
             "average_traded_notional": float(path.traded_notional.mean()),
             "annualized_linear_cost_drag": float(12 * cost / 10000 * path.traded_notional.mean()),
             "cash_warmup_months": int(path.path_status.eq("insufficient_formation_coverage").sum()),
             "scored_months": int(path.path_status.eq("ok").sum()),
             "minimum_active_finite_signal_count": int(path.loc[path.path_status.eq("ok"), "finite_signal_count"].min()),
             "maximum_missing_forward_gross_weight": float(path.missing_forward_return_gross_weight.max())}
        )
        residual_rows.extend(
            {"case": name, "month": str(month.date()), "net_return": float(value),
             "factor_replication_return": float(fitted), "residual": float(remain),
             "selected_lambda": float(lam)}
            for month, value, fitted, remain, lam in zip(
                eval_dates, net[attr["train_months"]:], reconstruction.fitted_values[:, column],
                residual, reconstruction.selected_lambdas[:, column]
            )
        )
    return metrics, residual_rows


def evaluate(
    root: Path, output: Path, paper_source: Path, paper_tex: Path, interpreter: Path,
) -> None:
    if (output / "run_manifest.json").exists():
        raise ValueError("completed M044 run already exists")
    study = root / "paper_runs/us_jkp_headline"
    contract_path, recipe_path = study / "benchmark_contract.json", output / "recipe.json"
    ledger_path = root / "paper_runs/paper_replication_audits/factorminer/formula_component_ledger.csv"
    contract, recipe = json.loads(contract_path.read_text()), json.loads(recipe_path.read_text())
    if contract["status"] != "frozen" or recipe["status"] != "frozen_for_execution":
        raise ValueError("frozen benchmark and FactorMiner recipe required")
    for path, expected in ((paper_source, PAPER_SOURCE_SHA256), (paper_tex, PAPER_FACTOR_TEX_SHA256),
                           (ledger_path, FORMULA_LEDGER_SHA256)):
        if digest(path) != expected:
            raise ValueError(f"FactorMiner source hash mismatch: {path}")
    implementation = [Path(__file__).resolve(), root / "src/alpha_evolve/headline_backtest.py",
                      root / "src/alpha_evolve/submission_analysis.py", root / "scripts/run_broad_jkp_crossfit.py"]
    relative = [str(path.relative_to(root)) for path in implementation]
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *relative], cwd=root, check=True)
    formulas = load_formulas(ledger_path, paper_tex)
    parse, interpreter_commit = install_interpreter(interpreter)
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    data, formed, row_index, column_index = load_dense_panel(Path(contract["data"]["path"]), settings)
    features, coverage = compute_features(formulas, data, row_index, column_index, parse)
    selection_panel = formed[["month", "security_id"]].copy()
    selection_panel["label"] = formed.ret_total_lead1m
    selection = select_ic_weighted(features, selection_panel, training_months=12, top_n=40)
    score = combined_score(features, selection_panel, selection, 12)
    paths, primary_holdings = {}, None
    for policy in ("zero", "adverse_100"):
        path, holdings = build_strategy_path(formed, score, settings, policy)
        paths[policy] = cash_fill_warmup(path)
        if policy == "zero":
            primary_holdings = holdings
    private = root / "artifacts/us_jkp_headline/v1"
    private_features = private / "M044_formation_factor_panel.parquet"
    private_holdings_path = private / "M044_formation_holdings.parquet"
    features.to_parquet(private_features, index=False)
    assert primary_holdings is not None
    primary_holdings.to_parquet(private_holdings_path, index=False)
    metrics, residual_rows = build_metrics(contract, root, paths)
    output.mkdir(parents=True, exist_ok=True)
    pd.concat([frame.assign(missing_return_policy=policy) for policy, frame in paths.items()]).to_csv(
        output / "monthly_returns.csv", index=False
    )
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    coverage.to_csv(output / "feature_coverage.csv", index=False)
    selection.to_csv(output / "factor_selection.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = paths["zero"].copy()
    primary_path["net_return"] = primary_path.gross_return - 0.001 * primary_path.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    selected_ids = ", ".join(selection.loc[selection.selected, "factor_id"].tolist())
    report = f'''# M044: FactorMiner Top-40 IC-weighted library on monthly U.S./JKP data

Status: **completed central partial adaptation**, not a reproduction of the FactorMiner agent or native 10-minute study.

The current v2 paper releases 110 formulas and makes the frozen Top-40 IC-weighted ensemble its strongest simple headline strategy. All 110 v2 strings are byte-lineage checked against the tracked formula ledger and evaluated before selection. The first 12 formation months determine absolute-IC ranking, signs, and normalized IC weights; those choices remain fixed for the following {primary['scored_months']} months. No factor was selected on its later return.

At the common 10 bp one-way cost, the 305-month path has CAGR {primary['full_cagr']:.2%}, annualized Sharpe {primary['full_annualized_sharpe']:.3f}, and maximum drawdown {primary['full_maximum_drawdown']:.2%}. The 185-month JKP133 residual mean is {primary['jkp_residual_mean_annualized']:.2%} annually (HAC t={primary['jkp_residual_t_hac']:.3f}, p={primary['jkp_residual_p_two_sided']:.4f}; descriptive 69-test bound={primary['exploratory_bonferroni69_p']:.4f}).

The paper releases no author-native runtime, selection IDs, weights, signals, or portfolio. Exact printed formulas therefore use the pinned independent interpreter's declared NumPy semantics, including the ambiguous Factor 001 `Min/Max(...,48)` parse. JKP fields, monthly periods, first-year selection, and common value-weighted deciles are disclosed adaptations. This does not reproduce the Gemini/memory mining process, 10-minute data, paper IC/ICIR, or a paper trading return.

Selected factor IDs: {selected_ids}.
'''
    (output / "verdict.md").write_text(report)
    public_names = ["monthly_returns.csv", "primary_monthly_returns.csv", "metrics.csv",
                    "attribution_residuals.csv", "feature_coverage.csv", "factor_selection.csv", "verdict.md"]
    manifest = {
        "status": "evaluated_partial", "milestone_id": "M044", "candidate_id": recipe["candidate_id"],
        "benchmark_id": contract["benchmark_id"], "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "contract_sha256": digest(contract_path), "recipe_sha256": digest(recipe_path),
        "paper_source_sha256": digest(paper_source), "paper_factor_tex_sha256": digest(paper_tex),
        "formula_ledger_sha256": digest(ledger_path), "interpreter_commit": interpreter_commit,
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                    "platform": platform.system()},
        "selection": {"training_months": 12, "factor_count": 110, "selected_count": 40,
                      "selected_ids": selection.loc[selection.selected, "factor_id"].tolist()},
        "primary_result": primary,
        "private_factor_panel_path": str(private_features), "private_factor_panel_sha256": digest(private_features),
        "private_holdings_path": str(private_holdings_path), "private_holdings_sha256": digest(private_holdings_path),
        "prior_jkp_outcomes_seen": True, "confirmatory_claim": False,
        "implementation_sha256": {str(path.relative_to(root)): digest(path) for path in implementation},
        "output_sha256": {name: digest(output / name) for name in public_names},
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps(primary, indent=2), flush=True)


def main() -> None:
    scratch = Path("/nfs/roberts/scratch/pi_btk22/zc362")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("paper_runs/us_jkp_headline/M044_factorminer"))
    parser.add_argument("--paper-source", type=Path, default=scratch / "factorminer_v2/source.tar.gz")
    parser.add_argument("--paper-tex", type=Path, default=scratch / "factorminer_v2/appendix_factors.tex")
    parser.add_argument("--interpreter", type=Path, default=scratch / "factorminer_audit/discovery/minihellboy-repo")
    args = parser.parse_args()
    os.umask(0o077)
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    private = root / "artifacts/us_jkp_headline/v1"
    private.mkdir(parents=True, exist_ok=True)
    with (private / "operation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status_path = private / "operation.json"
        status = {"state": "running", "phase": "factor_library_evaluation", "milestone_id": "M044",
                  "pid": os.getpid(), "hostname": socket.gethostname(),
                  "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
                  "started_at_utc": datetime.now(timezone.utc).isoformat(),
                  "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]}
        write_json(status_path, status)
        try:
            evaluate(root, output.resolve(), args.paper_source.resolve(), args.paper_tex.resolve(),
                     args.interpreter.resolve())
        except BaseException as error:
            status.update(state="failed", finished_at_utc=datetime.now(timezone.utc).isoformat(),
                          error_type=type(error).__name__, error=str(error))
            write_json(status_path, status)
            raise
        status.update(state="complete", finished_at_utc=datetime.now(timezone.utc).isoformat())
        write_json(status_path, status)


if __name__ == "__main__":
    main()
