#!/usr/bin/env python3
"""Prepare the shared U.S./JKP benchmark, then evaluate the fixed M001 recipe."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
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

from alpha_evolve.headline_backtest import (
    build_factor_panel, build_strategy_path, evc_jkp_score, load_formations,
    return_statistics,
)
from alpha_evolve.paths import DEFAULT_FACTOR_PANEL, DEFAULT_JKP_ROOT
from alpha_evolve.submission_analysis import alpha_regression, automatic_hac_lag
from run_broad_jkp_crossfit import (
    BASE_FACTOR_COLUMNS, RIDGE_LAMBDAS, hac_mean_se, rolling_crossfit_reconstruction,
)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def prepare(root: Path) -> None:
    study = root / "paper_runs/us_jkp_headline"
    contract_path = study / "benchmark_contract.json"
    contract = json.loads(contract_path.read_text())
    if contract["status"] != "draft_pending_preflight":
        raise ValueError("benchmark already prepared; do not silently replace its lock")
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    source_path = Path(contract["data"]["path"])
    print("Verifying the fixed JKP input hash", flush=True)
    input_hash = digest(source_path)
    if input_hash != contract["data"]["expected_sha256_from_existing_lock"]:
        raise ValueError("JKP input bytes differ from the starting contract")
    identity_frame = pd.read_csv(DEFAULT_FACTOR_PANEL, nrows=0)
    characteristics = [column[6:] for column in identity_frame if column.startswith("char__")]
    if len(characteristics) != 132 or len(set(characteristics)) != 132:
        raise ValueError("expected 132 unique fixed benchmark characteristics")
    factor_columns = [*BASE_FACTOR_COLUMNS, *[f"char__{c}" for c in characteristics if f"char__{c}" not in BASE_FACTOR_COLUMNS]]
    if len(factor_columns) != 133:
        raise ValueError("FF5/momentum analogues must not be double counted")
    private = root / "artifacts/us_jkp_headline/v1"
    private.mkdir(parents=True, exist_ok=True)
    os.chmod(private, 0o700)
    formed = load_formations(source_path, list(dict.fromkeys([*characteristics, "ni_at", "ebitda_mev", "ocf_me"])), settings)
    prepared_path = private / "formation_panel.parquet"
    formed.to_parquet(prepared_path, index=False)
    print(f"formation_rows={len(formed)} months={formed.month.nunique()}", flush=True)
    factor_panel, coverage = build_factor_panel(formed, characteristics, settings)
    expected = pd.date_range(settings["realized_return_start"], settings["realized_return_end"], freq=pd.offsets.MonthEnd())
    if not factor_panel.month.equals(pd.Series(expected, name="month")):
        raise ValueError("rebuilt benchmark does not use the fixed realization calendar")
    # Independently check the market calculation without depending on old,
    # ignored exports that need not exist in this checkout.
    independent = []
    for month, frame in formed.groupby("month", sort=True):
        value = float(np.average(frame.ret_exc_lead1m.fillna(0.0).to_numpy(), weights=frame.weight.to_numpy()))
        independent.append({"month": month + pd.offsets.MonthEnd(1), "independent_market": value})
    check = factor_panel[["month", "capm_top1000_mkt"]].merge(pd.DataFrame(independent), on="month", validate="one_to_one")
    difference = float((check.capm_top1000_mkt - check.independent_market).abs().max())
    if len(check) != len(expected) or difference > 1e-12:
        raise ValueError(f"corrected market/clock conformance failed: n={len(check)}, error={difference}")
    factor_path = study / "benchmark_monthly.csv"
    coverage_path = study / "benchmark_coverage.csv"
    factor_panel.to_csv(factor_path, index=False)
    coverage.to_csv(coverage_path, index=False)
    legacy_market = pd.read_csv(DEFAULT_FACTOR_PANEL, usecols=["month", "capm_top1000_mkt"])
    legacy_market["month"] = pd.to_datetime(legacy_market.month) + pd.offsets.MonthEnd(1)
    clock = factor_panel[["month", "capm_top1000_mkt"]].merge(legacy_market, on="month", suffixes=("_new", "_legacy"), validate="one_to_one")
    clock_correlation = float(clock.capm_top1000_mkt_new.corr(clock.capm_top1000_mkt_legacy))
    if len(clock) < 120 or not np.isfinite(clock_correlation) or clock_correlation < 0.99:
        raise ValueError("independent historical market clock check failed")
    sources = {str(path): digest(path) for path in [DEFAULT_JKP_ROOT / "code/main.py", DEFAULT_JKP_ROOT / "code/aux_functions.py"]}
    definition_note = {
        "ni_at": "ni_x / at_x (current standardized net income / assets); JKP definition is used, not an assertion of exact FactSet denominator/period equivalence.",
        "ebitda_mev": "ebitda_x * fx / (me_company + netdebt_x * fx); JKP rejects nonpositive market enterprise value.",
        "ocf_me": "ocf_x * fx / me_company; operating cash flow is the explicitly declared P/CF adaptation.",
        "availability": "JKP main.py passes lag_to_public=4 and max_lag=18 for both annual and quarterly accounting characteristics before combining them. This is the supplied reporting-lag convention, not proof of historical as-reported vintages.",
        "scope": "Financial-ratio concepts are retained; accounting periods, denominator conventions and the original vendor snapshot are adaptations, not blockers for the prescribed JKP transfer."
    }
    preflight = {"status": "passed", "created_at_utc": timestamp(), "input_sha256": input_hash,
                 "source_definition_sha256": sources, "input_definition_mapping": definition_note,
                 "formation_rows": len(formed), "formation_months": len(expected),
                 "benchmark_factor_count": len(factor_columns), "benchmark_columns": factor_columns,
                 "old_factor_panel_role": "factor identities only; its 2021 endpoint is not used for the new returns",
                 "factor_identity_source_sha256": digest(DEFAULT_FACTOR_PANEL),
                 "corrected_market_max_absolute_error": difference,
                 "corrected_market_matching_months": len(check),
                 "market_check_source": "independent NumPy value-weighted formation-data calculation; missing realizations zero without renormalizing",
                 "legacy_market_clock_matching_months": len(clock),
                 "legacy_market_clock_correlation": clock_correlation,
                 "future_return_availability_used_for_formation": False,
                 "candidate_strategy_returns_computed": False}
    write_json(study / "benchmark_preflight.json", preflight)
    contract.update(status="frozen", frozen_at_utc=timestamp(),
                    factor_columns=factor_columns, factor_count=133,
                    factor_panel_path="paper_runs/us_jkp_headline/benchmark_monthly.csv",
                    factor_panel_sha256=digest(factor_path),
                    private_formation_panel_path=str(prepared_path), private_formation_panel_sha256=digest(prepared_path),
                    private_formation_panel_scope="Benchmark/M001 formation inputs only; not a universal warmup or training panel for later strategies",
                    preflight_path="paper_runs/us_jkp_headline/benchmark_preflight.json",
                    preflight_sha256=digest(study / "benchmark_preflight.json"),
                    factor_construction="Rebuilt from the same JKP formation-date top-1000 universe using deterministic value-weighted deciles, zero missing realization returns without reweighting, and the fixed 132 characteristic identities; not official published JKP portfolio returns.",
                    attribution={"method": "strictly past-trained rolling ridge factor slopes; intercept not subtracted",
                                 "train_months": 120, "validation_months": 24,
                                 "ridge_lambdas": RIDGE_LAMBDAS.tolist(), "n_unpenalized": 6,
                                 "evaluation_start": str(expected[120].date()), "evaluation_end": str(expected[-1].date()),
                                 "evaluation_months": len(expected) - 120,
                                 "hac_rule": "floor(4*(n/100)^(2/9)); normal approximation",
                                 "family_inference": "interim conservative 69-test Bonferroni bound; final Holm across all closed primary tests"},
                    cost_accounting="Gross-book NAV drift defines traded notional; subtract linear one-way fee drag from excess return. Fees are not fed back into subsequent gross-book targets; no explicit borrow fees or market impact are included.")
    contract["data"]["security_id"] = "id"
    contract["data"]["permno_reference_column"] = "permno"
    contract["data"]["hash_revalidated_at_utc"] = timestamp()
    contract["benchmark_source"] = "New causally formed 1999-2024 JKP-derived market plus 132-characteristic panel; old panel supplies fixed identities only."
    write_json(contract_path, contract)
    recipe_path = study / "M001_gpt_signal/recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe.update(input_mapping_status="checked_defensible_accounting_convention_adaptation",
                  input_definition_mapping=definition_note, input_definition_source_sha256=sources,
                  status="recipe_and_common_benchmark_fixed_before_strategy_run")
    write_json(recipe_path, recipe)
    print("benchmark_preflight=passed; common contract frozen; M001 returns not yet computed", flush=True)


def evaluate(root: Path) -> None:
    study = root / "paper_runs/us_jkp_headline"
    output = study / "M001_gpt_signal"
    contract_path = study / "benchmark_contract.json"
    recipe_path = output / "recipe.json"
    contract = json.loads(contract_path.read_text())
    recipe = json.loads(recipe_path.read_text())
    implementation_paths = [root / "src/alpha_evolve/headline_strategies.py", root / "src/alpha_evolve/headline_backtest.py",
                            root / "src/alpha_evolve/submission_analysis.py", root / "scripts/run_broad_jkp_crossfit.py",
                            Path(__file__).resolve()]
    relative_paths = [str(path.relative_to(root)) for path in implementation_paths]
    subprocess.run(["git", "ls-files", "--error-unmatch", *relative_paths], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *relative_paths], cwd=root, check=True)
    code_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    code_hashes = {str(path.relative_to(root)): digest(path) for path in implementation_paths}
    contract_hash, recipe_hash = digest(contract_path), digest(recipe_path)
    if contract["status"] != "frozen" or recipe["input_mapping_status"] != "checked_defensible_accounting_convention_adaptation":
        raise ValueError("complete and freeze preflight before evaluating")
    if (output / "run_manifest.json").exists():
        raise ValueError("M001 already has a run manifest; inspect it instead of silently rerunning")
    if recipe["trading_score_direction"] != -1:
        raise ValueError("the source-selected direction changed")
    factor_path = root / contract["factor_panel_path"]
    private_path = Path(contract["private_formation_panel_path"])
    for path, expected in [(factor_path, contract["factor_panel_sha256"]),
                           (private_path, contract["private_formation_panel_sha256"]),
                           (root / contract["preflight_path"], contract["preflight_sha256"])]:
        if digest(path) != expected:
            raise ValueError(f"frozen input changed: {path}")
    settings = contract["starting_settings_retained_from_corrected_us_study"]
    formed = pd.read_parquet(private_path)
    # Do not pass realized returns or any other columns to the signal function.
    scores = evc_jkp_score(formed[["ni_at", "ebitda_mev", "ocf_me"]])
    paths = []
    holdings_path = private_path.parent / "M001_formation_holdings.parquet"
    for policy in ("zero", "adverse_100"):
        result, holdings = build_strategy_path(formed, scores, settings, policy)
        result.insert(0, "missing_return_policy", policy)
        paths.append(result)
        if policy == "zero":
            holdings.to_parquet(holdings_path, index=False)
    all_paths = pd.concat(paths, ignore_index=True)
    all_paths.to_csv(output / "monthly_returns.csv", index=False)
    base = paths[0]
    factors = pd.read_csv(factor_path, parse_dates=["month"])
    merged = base.merge(factors, on="month", suffixes=("", "_benchmark"), validate="one_to_one")
    if len(merged) != len(base) or not base.path_status.eq("ok").all():
        raise ValueError("fixed-calendar strategy path has a formation or NAV failure; inspect recorded path, do not drop months")
    cases = [("zero", float(cost)) for cost in settings["cost_sensitivity_bps_one_way"]]
    cases.append(("adverse_100", float(settings["primary_cost_bps_one_way"])))
    case_names = [f"{policy}_cost_{cost:g}" for policy, cost in cases]
    y = np.column_stack([paths[0 if policy == "zero" else 1].gross_return.to_numpy()
                         - cost / 10000 * paths[0 if policy == "zero" else 1].traded_notional.to_numpy()
                         for policy, cost in cases])
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError("incomplete or nonpositive-NAV cost scenario; retain the path failure")
    attr = contract["attribution"]
    x = merged[contract["factor_columns"]].to_numpy(dtype=float)
    print(f"factor_attribution: {len(base)} months, {x.shape[1]} factors, {len(cases)} fixed cost/missingness scenarios", flush=True)
    reconstruction = rolling_crossfit_reconstruction(x, y, attr["train_months"], attr["validation_months"],
                                                      np.asarray(attr["ridge_lambdas"]), attr["n_unpenalized"])
    eval_dates = base.month.iloc[attr["train_months"]:].reset_index(drop=True)
    n = len(eval_dates)
    lags = automatic_hac_lag(n)
    metrics = []
    residual_rows = []
    for column, ((policy, cost), case) in enumerate(zip(cases, case_names)):
        candidate = paths[0 if policy == "zero" else 1]
        net = y[:, column]
        residual = reconstruction.residuals[:, column]
        alpha = float(residual.mean())
        se = float(hac_mean_se(residual, lags))
        t_stat = alpha / se
        p = float(2 * norm.sf(abs(t_stat)))
        row = {"case": case, "primary": policy == "zero" and cost == settings["primary_cost_bps_one_way"],
               "missing_return_policy": policy, "cost_bps_one_way": cost,
               **{f"full_{key}": value for key, value in return_statistics(net).items()},
               **{f"evaluation_{key}": value for key, value in return_statistics(net[attr["train_months"]:]).items()},
               "evaluation_start": str(eval_dates.iloc[0].date()), "evaluation_end": str(eval_dates.iloc[-1].date()),
               "jkp_alpha_annualized": 12 * alpha, "jkp_alpha_se_annualized": 12 * se,
               "jkp_alpha_t_hac": t_stat, "jkp_alpha_p_two_sided": p,
               "jkp_alpha_ci_low_annualized": 12 * (alpha - 1.959963984540054 * se),
               "jkp_alpha_ci_high_annualized": 12 * (alpha + 1.959963984540054 * se),
               "interim_bonferroni69_p": min(1.0, 69 * p), "hac_lags": lags,
               "average_traded_notional": float(candidate.traded_notional.mean()),
               "annualized_linear_cost_drag": float(12 * cost / 10000 * candidate.traded_notional.mean()),
               "minimum_finite_signal_count": int(candidate.finite_signal_count.min()),
               "maximum_missing_forward_gross_weight": float(candidate.missing_forward_return_gross_weight.max()),
               "full_path_start": str(base.month.iloc[0].date()), "full_path_end": str(base.month.iloc[-1].date())}
        ff_frame = merged[["month", *BASE_FACTOR_COLUMNS]].copy()
        ff_frame["net_return"] = net
        ff_result = asdict(alpha_regression(ff_frame.iloc[attr["train_months"]:], "net_return", BASE_FACTOR_COLUMNS))
        row.update(ff5mom_alpha_annualized=ff_result["alpha_annualized"], ff5mom_alpha_t_hac=ff_result["alpha_t_hac"])
        metrics.append(row)
        residual_rows.extend({"case": case, "month": str(month.date()), "net_return": float(value),
                              "factor_replication_return": float(fitted), "residual": float(remain),
                              "selected_lambda": float(lam)}
                             for month, value, fitted, remain, lam in zip(eval_dates, net[attr["train_months"]:],
                                                                         reconstruction.fitted_values[:, column], residual,
                                                                         reconstruction.selected_lambdas[:, column]))
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(output / "attribution_residuals.csv", index=False)
    primary = next(row for row in metrics if row["primary"])
    primary_path = base.copy()
    primary_path["net_return"] = base.gross_return - settings["primary_cost_bps_one_way"] / 10000 * base.traded_notional
    primary_path.to_csv(output / "primary_monthly_returns.csv", index=False)
    report = f'''# M001: GPT-Signal EVC on monthly U.S./JKP data

Status: **completed adapted headline-signal evaluation**, not an original-paper or fresh-LLM reproduction.

The published EVC reciprocal formula is retained. Direction is negative EVC from the paper's signed correlation, fixed before this run. Inputs use JKP net income/assets, EBITDA/market enterprise value, and operating cash flow/market equity. Accounting conventions, U.S. universe, monthly cadence and the value-weighted decile portfolio are disclosed adaptations.

## Primary result: 10 bp one-way costs

- Full return path: {primary['full_months']} months, {primary['full_path_start']} to {primary['full_path_end']}.
- Net CAGR: {primary['full_cagr']:.2%}; annualized Sharpe: {primary['full_annualized_sharpe']:.3f}; maximum drawdown: {primary['full_maximum_drawdown']:.2%}.
- Mean monthly traded notional: {primary['average_traded_notional']:.3f}; annualized linear cost drag: {primary['annualized_linear_cost_drag']:.2%}.
- Common rolling-attribution window: {n} months, {primary['evaluation_start']} to {primary['evaluation_end']}, after 120 training months with a 24-month inner validation block.
- JKP-derived 133-factor residual alpha: {primary['jkp_alpha_annualized']:.2%} per year; HAC t={primary['jkp_alpha_t_hac']:.3f}; two-sided p={primary['jkp_alpha_p_two_sided']:.4f}; 95% interval [{primary['jkp_alpha_ci_low_annualized']:.2%}, {primary['jkp_alpha_ci_high_annualized']:.2%}].
- Conservative interim 69-test Bonferroni p: {primary['interim_bonferroni69_p']:.4f}. Final family inference awaits the remaining milestones.

This is a retrospective strategy-transfer result on data already used in prior project work. It is not proof of live alpha, fresh GPT generation, or the original paper's reported performance. The benchmark is a fixed JKP-derived market plus 132-characteristic construction; FF5/momentum analogues are members, not six additional factors. Slopes and ridge choice use only earlier months. The fit's intercept is not removed from realized residuals.

No sign, factor formula or hyperparameter was changed after viewing the result. Other costs and the adverse missing-return policy are diagnostics, not alternative candidates selected for better results. Gross-book turnover and linear fee drag follow the shared convention; borrow fees, market impact, historical data vintages and exact FactSet accounting definitions are not reproduced. Compounded growth is for the normalized long-short risk-capital book, with no collateral cash yield added.

Sources: [GPT-Signal](https://arxiv.org/html/2410.18448v1), Sections 4-5; [JKP data/code](https://github.com/bkelly-lab/jkp-data), associated with Jensen, Kelly and Pedersen (2023), *Is There a Replication Crisis in Finance?* The supplied dataset's noncommercial data-license conditions are retained.

## Reproducibility

`recipe.json`, `../benchmark_contract.json`, `../benchmark_preflight.json`, `monthly_returns.csv`, `primary_monthly_returns.csv`, `metrics.csv` and `attribution_residuals.csv` preserve the public audit trail. Security-level formations and holdings remain in the ignored private artifact directory named in `run_manifest.json`.

Runner: `python scripts/run_us_jkp_headline.py --run` (refuses to overwrite an existing completed run). Input and benchmark hashes are checked before evaluation. The fixed benchmark was built first using `--prepare`.
'''
    (output / "verdict.md").write_text(report)
    if code_hashes != {str(path.relative_to(root)): digest(path) for path in implementation_paths}:
        raise RuntimeError("implementation changed during evaluation")
    if (contract_hash, recipe_hash) != (digest(contract_path), digest(recipe_path)):
        raise RuntimeError("frozen recipe or benchmark changed during evaluation")
    run = {"status": "evaluated", "benchmark_id": contract["benchmark_id"], "milestone_id": "M001",
           "completed_at_utc": timestamp(), "hostname": socket.gethostname(),
           "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "platform": platform.system()},
           "contract_sha256": contract_hash, "recipe_sha256": recipe_hash, "code_commit": code_commit,
           "input_sha256": contract["data"]["expected_sha256_from_existing_lock"],
           "benchmark_sha256": contract["factor_panel_sha256"],
           "private_holdings_path": str(holdings_path), "private_holdings_sha256": digest(holdings_path),
           "implementation_sha256": code_hashes,
           "primary_result": primary,
           "new_strategy_recipe_selection_used_jkp_results": False,
           "output_sha256": {name: digest(output / name) for name in
                             ["monthly_returns.csv", "primary_monthly_returns.csv", "metrics.csv", "attribution_residuals.csv", "verdict.md"]}}
    write_json(output / "run_manifest.json", run)
    print(json.dumps(primary, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    root = args.root.resolve()
    private = root / "artifacts/us_jkp_headline/v1"
    private.mkdir(parents=True, exist_ok=True)
    os.chmod(private, 0o700)
    # A real OS lock prevents another heartbeat from starting a duplicate job.
    with (private / "operation.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status = {"state": "running", "phase": "prepare" if args.prepare else "run",
                  "milestone_id": "M001", "pid": os.getpid(), "hostname": socket.gethostname(),
                  "slurm_job_id": os.environ.get("SLURM_JOB_ID"), "started_at_utc": timestamp(),
                  "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]}
        status_path = private / "operation.json"
        write_json(status_path, status)
        try:
            if args.prepare:
                prepare(root)
            else:
                evaluate(root)
        except BaseException as error:
            status.update(state="failed", finished_at_utc=timestamp(), error_type=type(error).__name__, error=str(error))
            write_json(status_path, status)
            raise
        status.update(state="complete", finished_at_utc=timestamp())
        write_json(status_path, status)


if __name__ == "__main__":
    main()
