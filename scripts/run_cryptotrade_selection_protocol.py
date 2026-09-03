#!/usr/bin/env python3
"""Reconstruct validation-only SMA/SLMA selection using the native source loop.

The paper does not define 'best performance' or all SLMA search bounds. We
therefore keep two explicit objectives (return and Sharpe), retain every tied
winner, and use the released five periods / ten ordered short<long pairs.
Nothing is selected using held-out results. No extra faithful-paper credit is
assigned: this is a source-rule reconstruction on released, imperfectly matched
input snapshots, not recovery of the authors' missing tuning trace.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import redirect_stdout
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
from itertools import combinations

import numpy as np

import audit_cryptotrade_paper as audit


NATIVE_BASELINE_SHA256 = "9baf6e13ce4c504d7dee0bfe3fa14d5e953b3276cd43cc11b91cb862243e606e"
OBJECTIVES = ("total_return_pct", "sharpe_ratio")
SOURCE_NAMES = {"sma": "SMA", "slma": "SLMA", "macd": "MACD"}
TIE_ATOL = 1e-12


def parameter_key(parameter):
    return json.dumps(parameter, separators=(",", ":"))


def candidates(strategy):
    if strategy == "sma":
        return tuple(audit.SMA_PERIODS)
    if strategy == "slma":
        return tuple(combinations(audit.SMA_PERIODS, 2))
    raise ValueError(strategy)


def select_on_validation(rows, objective):
    if objective not in OBJECTIVES or not rows:
        raise ValueError("unsupported selection objective or empty validation grid")
    if any(row["split"] != "validation" for row in rows):
        raise ValueError("selection must not consume held-out results")
    scores = [float(row[objective]) for row in rows]
    if not all(math.isfinite(score) for score in scores):
        raise ValueError("nonfinite validation score")
    maximum = max(scores)
    return [row for row in rows if math.isclose(float(row[objective]), maximum, rel_tol=0, abs_tol=TIE_ATOL)]


def source_function(root):
    path = root / "run_baseline.py"
    if audit.sha256(path) != NATIVE_BASELINE_SHA256:
        raise RuntimeError("native baseline bytes changed")
    tree = ast.parse(path.read_text())
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_strategy")
    # Execute this function's verbatim AST, not the unused imports, LSTM code,
    # or the monolithic hard-coded launcher at module scope.
    return compile(ast.Module(body=[fn], type_ignores=[]), "run_baseline.py", "exec")


def simulate_native(root, module, compiled, asset, start, end, strategy, parameter):
    path = []
    created = []
    old_cwd = Path.cwd()
    os.chdir(root)
    try:
        data = module.ETHTradingEnv(audit.Namespace(dataset=asset, starting_date=start, ending_date=end)).data.copy()

        def environment(args):
            env = module.ETHTradingEnv(args)
            original_step = env.step

            def step(action):
                state, reward, done, info = original_step(action)
                path.append({"date": str(info["today"]), "action": float(action), "net_worth": float(state["net_worth"])})
                return state, reward, done, info

            env.step = step
            created.append(env)
            return env

        namespace = {
            "np": np, "df": data, "ETHTradingEnv": environment,
            # Only repair the released constructor's missing dataset argument.
            "Namespace": lambda **kwargs: audit.Namespace(dataset=asset, **kwargs),
            "BUY": 0.5, "SELL": -0.5, "FULL_BUY": 1, "FULL_SELL": -1,
        }
        exec(compiled, namespace)
        captured = {}
        code = namespace["run_strategy"].__code__

        def profile(frame, event, arg):
            if event == "return" and frame.f_code is code:
                values = frame.f_locals
                captured.update({"total_return_pct": float(values["total_irr"] * 100),
                                 "daily_return_mean_pct": float(values["irr_mean"]),
                                 "daily_return_std_pct": float(values["irr_std"]),
                                 "sharpe_ratio": float(values["result"]["sharp_ratio"])})

        args = {"starting_date": start, "ending_date": end}
        if strategy == "sma":
            args["period"] = parameter
        elif strategy == "slma":
            args.update(short=f"SMA_{parameter[0]}", long=f"SMA_{parameter[1]}")
        previous = sys.getprofile()
        sys.setprofile(profile)
        try:
            with redirect_stdout(io.StringIO()):
                namespace["run_strategy"](SOURCE_NAMES[strategy], args)
        finally:
            sys.setprofile(previous)
        if not captured or len(created) != 1:
            raise RuntimeError("native source execution not captured")
        columns = [f"SMA_{parameter}"] if strategy == "sma" else [f"SMA_{p}" for p in parameter] if strategy == "slma" else []
        warmup_rows = int(data.iloc[:-1][columns].isna().any(axis=1).sum()) if strategy in {"sma", "slma"} else 0
        metrics = audit.source_simulation(module, root, asset, start, end, strategy, parameter)
        if not all(math.isfinite(values[key]) for values in (captured, metrics) for key in audit.METRICS):
            raise RuntimeError("nonfinite native or adapter metric")
        difference = max(abs(captured[key] - metrics[key]) for key in audit.METRICS)
        if difference > 1e-12:
            raise RuntimeError(f"adapter differs from native loop for {asset}/{strategy}/{parameter}: {difference}")
        digest = hashlib.sha256((json.dumps(path, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()
        return captured, path, digest, warmup_rows
    finally:
        os.chdir(old_cwd)


def build(root, output):
    if audit.git_head(root) != audit.SOURCE_COMMIT:
        raise RuntimeError("source commit changed")
    if audit.git(root, "diff", "HEAD", "--name-only", "--", "run_baseline.py", "eth_env.py", "data").strip():
        raise RuntimeError("tracked native source or data differs from the pinned commit")
    module = audit.load_environment(root)
    compiled = source_function(root)
    grid = []
    run_paths = {}
    for asset, splits in audit.PAPER_SPLITS.items():
        start, end, *_ = splits["validation"]
        for strategy in ("sma", "slma"):
            for parameter in candidates(strategy):
                repetitions = [simulate_native(root, module, compiled, asset, start, end, strategy, parameter) for _ in range(2)]
                if repetitions[0] != repetitions[1]:
                    raise RuntimeError("validation native repeats differ")
                metrics, path, digest, warmup = repetitions[0]
                run_id = f"validation|{asset}|{strategy}|{parameter_key(parameter)}"
                run_paths[run_id] = path
                grid.append({"asset": asset, "strategy": strategy, "split": "validation",
                             "start": start, "end": end, "parameter": parameter_key(parameter),
                             **metrics, "decision_count": len(path), "undefined_indicator_decisions": warmup,
                             "path_sha256": digest, "repeat_exact": True, "adapter_native_match": True})

    paper = {(row["asset"], row["strategy"], row["regime"], row["metric"]): row["paper_value"]
             for row in audit.paper_result_rows()}
    choices = []
    cells = []
    test_cache = {}
    # Hold-out results are not available to select_on_validation.
    for asset in audit.PAPER_SPLITS:
        for strategy in ("sma", "slma"):
            validation_rows = [row for row in grid if row["asset"] == asset and row["strategy"] == strategy]
            for objective in OBJECTIVES:
                winners = select_on_validation(validation_rows, objective)
                choices.append({"asset": asset, "strategy": strategy, "objective": objective,
                                "selected_parameters": json.dumps([row["parameter"] for row in winners]),
                                "tie_count": len(winners), "validation_score": winners[0][objective],
                                "released_fixed_parameter": parameter_key(audit.fixed_parameter(strategy)),
                                "fixed_parameter_is_winner": parameter_key(audit.fixed_parameter(strategy)) in [r["parameter"] for r in winners],
                                "selection_uses_test_data": False})
                for winner in winners:
                    parameter = json.loads(winner["parameter"])
                    for regime in audit.REGIMES:
                        key = (asset, strategy, winner["parameter"], regime)
                        if key not in test_cache:
                            start, end, *_ = audit.PAPER_SPLITS[asset][regime]
                            repeats = [simulate_native(root, module, compiled, asset, start, end, strategy, parameter) for _ in range(2)]
                            if repeats[0] != repeats[1]:
                                raise RuntimeError("held-out native repeats differ")
                            test_cache[key] = repeats[0]
                            run_paths["|".join(key)] = repeats[0][1]
                        metrics, path, digest, _ = test_cache[key]
                        for metric in audit.METRICS:
                            expected = paper[(asset, strategy, regime, metric)]
                            cells.append({"asset": asset, "strategy": strategy, "regime": regime,
                                          "objective": objective, "parameter": winner["parameter"],
                                          "metric": metric, "paper_value": expected,
                                          "recomputed_value": metrics[metric],
                                          "display_match": abs(metrics[metric] - expected) <= audit.DISPLAY_TOLERANCE,
                                          "path_sha256": digest, "repeat_exact": True,
                                          "evidence_role": "validation_rule_reconstruction_not_recovered_author_tuning_trace"})
    objective_matches = {}
    matches = {}
    for objective in OBJECTIVES:
        groups = {}
        for row in cells:
            if row["objective"] == objective:
                groups.setdefault((row["asset"], row["strategy"], row["regime"], row["metric"]), []).append(row["display_match"])
        matches[objective] = {key for key, values in groups.items() if all(values)}
        objective_matches[objective] = len(matches[objective])
    fixed_matches = 0
    for asset in audit.PAPER_SPLITS:
        for strategy in ("sma", "slma"):
            parameter = audit.fixed_parameter(strategy)
            for regime in audit.REGIMES:
                key = (asset, strategy, parameter_key(parameter), regime)
                if key not in test_cache:
                    start, end, *_ = audit.PAPER_SPLITS[asset][regime]
                    repeats = [simulate_native(root, module, compiled, asset, start, end, strategy, parameter) for _ in range(2)]
                    if repeats[0] != repeats[1]:
                        raise RuntimeError("fixed-setting native repeats differ")
                    test_cache[key] = repeats[0]
                    run_paths["|".join(key)] = repeats[0][1]
                fixed_matches += sum(abs(test_cache[key][0][metric] - paper[(asset, strategy, regime, metric)]) <= audit.DISPLAY_TOLERANCE
                                     for metric in audit.METRICS)
    original_periods = module.SMA_PERIODS
    module.SMA_PERIODS = [1, *original_periods]
    try:
        neutral_runs = [simulate_native(root, module, compiled, "sol", "2023-04-12", "2023-06-16", "sma", 1) for _ in range(2)]
    finally:
        module.SMA_PERIODS = original_periods
    if neutral_runs[0] != neutral_runs[1] or any(row["action"] != 0 for row in neutral_runs[0][1]):
        raise RuntimeError("native SMA(1) is not the exact repeated hold path")
    run_paths["diagnostic|sol|sma1_hold"] = neutral_runs[0][1]
    constant_sell = audit.source_simulation(module, root, "sol", "2023-04-12", "2023-06-16", "constant_sell_counterfactual")
    summary = {
        "source_commit": audit.SOURCE_COMMIT, "native_baseline_sha256": NATIVE_BASELINE_SHA256,
        "execution_runtime": {"python": sys.version.split()[0], "numpy": np.__version__,
                              "pandas": audit.pd.__version__, "platform": sys.platform},
        "native_environment_sha256": audit.sha256(root / "eth_env.py"),
        "paper_url": audit.PAPER_URL, "paper_sha256": audit.PAPER_SHA256,
        "paper_locator": "Appendix E items 2-3, Tables 1-4",
        "validation_candidates": len(grid), "validation_native_runs": len(grid)*2,
        "selection_cases": len(choices), "objectives": list(OBJECTIVES),
        "held_out_distinct_configurations": len(test_cache), "held_out_native_runs": len(test_cache)*2,
        "all_native_repeats_exact": True, "all_adapter_native_metrics_equal_atol_1e_12": True,
        "selection_uses_test_data": False, "tie_absolute_tolerance": TIE_ATOL,
        "compared_paper_cells_per_objective": 72,
        "matching_cells_by_objective_all_ties_required": objective_matches,
        "matching_cells_under_both_objectives": len(set.intersection(*matches.values())),
        "fixed_settings_match_cells": fixed_matches,
        "native_sma1_hold_diagnostic_runs": 2,
        "native_sma1_sol_bear_metrics": neutral_runs[0][0],
        "constant_sell_counterfactual_metrics": {key: constant_sell[key] for key in audit.METRICS},
        "constant_sell_is_not_native_sma1": True,
        "additional_paper_result_credit": 0,
        "scope": "SMA uses the published grid; SLMA uses all short<long pairs from the released grid. Return and Sharpe are explicit alternative interpretations of the paper's unspecified best-performance objective. Released validation prices differ from the paper summary, so no exact author-protocol reconstruction is claimed.",
    }
    if fixed_matches != 66 or objective_matches != {"total_return_pct": 16, "sharpe_ratio": 16}:
        raise RuntimeError("recorded source-selection comparison changed")
    output.mkdir(parents=True, exist_ok=True)
    for filename, rows in (("traditional_validation_grid.csv", grid),
                           ("traditional_validation_choices.csv", choices),
                           ("traditional_selected_test_cells.csv", cells)):
        audit.write_csv(output / filename, rows, list(rows[0]))
    (output / "traditional_selection_protocol.json").write_text(json.dumps(summary, indent=2) + "\n")
    (output / "traditional_selection_paths.json").write_text(json.dumps(run_paths, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
