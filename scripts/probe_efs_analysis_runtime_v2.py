#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""SYNTHETIC integration fixture; no market-performance or source-replay credit."""

from pathlib import Path
import importlib.util
import argparse
import json
import shutil
import socket
import sys
import urllib.request
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REAL_ROOT = ROOT
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_economics import cash_account
from alpha_evolve.publication_inference import grouped_t_effect


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(path, obj)


def import_script(name):
    spec = importlib.util.spec_from_file_location("synthetic_" + name, REAL_ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=1)
    options = parser.parse_args()
    if options.attempt < 1:
        raise ValueError("Positive isolated fixture attempt required")
    suffix = "" if options.attempt == 1 else "_%02d" % options.attempt
    out = REAL_ROOT / ("artifacts/fidelity_completion_v2/efs_analysis_synthetic_fixture" + suffix)
    if out.exists():
        raise ValueError("Preserve fixture attempt; inspect before a new isolated attempt")
    fake = out / "SYNTHETIC_ROOT"
    public = fake / "paper_runs/fidelity_completion_v2"
    private = fake / "artifacts/fidelity_completion_v2"
    public.mkdir(parents=True)
    private.mkdir(parents=True)
    (out / "README.md").write_text(
        "# SYNTHETIC INTEGRATION FIXTURE\n\nThis is fabricated test data, not research evidence. Only the real market calendar is reused. Every return, holding, factor and source-completion record is synthetic. Source/replay validation is explicitly stubbed here; it is tested separately on actual artifacts. These outputs must never enter a study report, completion count or scientific bundle as market results. No human source review or replication credit.\n"
    )
    write_json(
        out / "scope.json",
        {
            "synthetic_fixture": True,
            "economic_result_credit": 0,
            "human_review": False,
            "real_source_validation_stubbed": True,
            "new_model_calls": 0,
        },
    )
    for name in ["evaluate_efs_pool_v2.py", "evaluate_efs_grammar_pool_v2.py"]:
        p = fake / "scripts" / name
        p.parent.mkdir(exist_ok=True)
        shutil.copyfile(REAL_ROOT / "scripts" / name, p)
    real_public = REAL_ROOT / "paper_runs/fidelity_completion_v2"
    for name in ["efs_pool_protocol.json", "efs_monthly_inference_reference.json"]:
        shutil.copyfile(real_public / name, public / name)
    plan = json.loads((real_public / "efs_final_analysis_protocol.json").read_text())
    recipe = json.loads((REAL_ROOT / "paper_runs/economic_fidelity/efs_v1/recipe.json").read_text())
    write_json(fake / "paper_runs/economic_fidelity/efs_v1/recipe.json", recipe)
    trials = ["gpt41_1", "gpt41_2", "gpt41_3", "deepseek_v3_1", "deepseek_v3_2", "deepseek_v3_3"]
    for trial in trials[1:]:
        write_json(public / "efs" / trial / "recipe.json", recipe)
    dates = pd.DatetimeIndex(
        pd.read_parquet(
            REAL_ROOT / "artifacts/economic_fidelity/v1/efs_us50_daily.parquet", columns=["date"]
        ).date.unique()
    ).sort_values()
    dates = dates[(dates >= "2019-01-01") & (dates <= "2024-12-31")]
    assert len(dates) == 1510
    rng = np.random.default_rng(731903)
    tickers = [f"SYNTHETIC_{i:02d}" for i in range(50)]
    returns = rng.normal(0.00015, 0.01, (1510, 50)) + rng.normal(0, 0.006, (1510, 1))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    frame = pd.DataFrame(
        {
            "date": np.repeat(dates, 50),
            "ticker": np.tile(tickers, 1510),
            "ret": returns.ravel(),
            "adjusted_close": prices.ravel(),
        }
    )
    path = fake / "artifacts/economic_fidelity/v1/efs_us50_daily.parquet"
    path.parent.mkdir(parents=True)
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame.to_parquet(path, index=False)
    write_json(path.with_name("data_manifest.json"), {"daily_extract_sha256": sha256(path), "synthetic_fixture": True})
    factor_names = pd.read_csv(REAL_ROOT / plan["jkp"]["factor_file"], nrows=0).columns
    columns = ["capm_top1000_mkt"] + [c for c in factor_names if c.startswith("char__")]
    factors = pd.DataFrame(rng.normal(0.002, 0.035, (72, 133)), columns=columns)
    factors.insert(0, "realization_month", pd.period_range("2019-01", "2024-12", freq="M").astype(str))
    factor_path = fake / plan["jkp"]["factor_file"]
    factor_path.parent.mkdir(parents=True)
    factors.to_csv(factor_path, index=False)
    plan["jkp"]["factor_sha256"] = sha256(factor_path)
    plan["synthetic_fixture"] = True
    write_json(public / "efs_final_analysis_protocol.json", plan)

    def source_proof(trial):
        return {"synthetic_fixture": True, "trial": trial, "real_replay_gate": "STUBBED_NOT_REPLICATION_EVIDENCE"}

    path_values = {}
    for group, offset in [("grammar_101_103", 0), ("gpt41", 10), ("deepseek_v3", 0)]:
        folder = public / "efs_pooled" / group
        priv = private / "efs_pooled" / group
        folder.mkdir(parents=True)
        priv.mkdir(parents=True)
        for mode, shift in [("causal_discovery_gated", 0), ("retrospective_final_union_diagnostic", 5)]:
            weights = np.zeros((1510, 50))
            weights[:, offset + shift : offset + shift + 10] = 0.1
            pd.DataFrame(weights, index=dates, columns=tickers).to_parquet(priv / (mode + "_weights.parquet"))
            daily = {"date": dates}
            for cost in [0, 10, 25, 50]:
                daily["total_cost_" + str(cost)] = cash_account(weights, returns, cost)[0]
            path_values[(group, mode)] = daily
            pd.DataFrame(daily).to_csv(folder / (mode + "_daily_returns.csv"), index=False)
            write_json(
                folder / (mode + "_selections.json"),
                [
                    {"execution_date": str(day.date()), "selected_future_discoveries": 0, "synthetic_fixture": True}
                    for day in dates
                ],
            )
        done = {
            "status": "complete",
            "causal_discovery_gating": True,
            "new_model_calls": 0,
            "synthetic_fixture": True,
            "library_factors": 10,
            "maximum_independent_account_error": 0,
        }
        if group == "grammar_101_103":
            done.update(
                control_seeds=[101, 102, 103],
                script_sha256=sha256(fake / "scripts/evaluate_efs_grammar_pool_v2.py"),
                protocol_sha256=sha256(public / "efs_final_analysis_protocol.json"),
            )
        else:
            names = trials[:3] if group == "gpt41" else trials[3:]
            done.update(
                trials=names,
                source_proofs={t: source_proof(t) for t in names},
                script_sha256=sha256(fake / "scripts/evaluate_efs_pool_v2.py"),
                protocol_sha256=sha256(public / "efs_pool_protocol.json"),
            )
        done.update(
            output_sha256={p.name: sha256(p) for p in folder.iterdir()},
            private_weights_sha256={p.name: sha256(p) for p in priv.iterdir()},
        )
        write_json(folder / "completion.json", done)
    controls = []
    for arm, n in [("initial", 5), ("equal_weight", 50)]:
        weights = np.zeros((1510, 50))
        weights[:, :n] = 1 / n
        r = cash_account(weights, returns, 10)[0]
        controls.extend(
            {"date": day, "return": value, "arm": arm, "cadence": "daily", "cost_bps": 10}
            for day, value in zip(dates, r)
        )
    path = fake / "artifacts/publication_upgrade_v1/efs_controls/daily_returns.parquet"
    path.parent.mkdir(parents=True)
    pd.DataFrame(controls).to_parquet(path, index=False)
    for seed in range(101, 111):
        path = fake / f"artifacts/publication_upgrade_v1/efs_matched/seed_{seed}/daily_returns.csv"
        path.parent.mkdir(parents=True)
        pd.DataFrame(path_values[("grammar_101_103", "causal_discovery_gated")]).to_csv(path, index=False)
        write_json(path.with_name("completion.json"), {"returns_sha256": sha256(path), "synthetic_fixture": True})
    for trial in trials:
        folder = fake / "paper_runs/economic_fidelity/efs_v1" if trial == "gpt41_1" else public / "efs" / trial
        pd.DataFrame(
            path_values[("gpt41" if trial.startswith("gpt41") else "deepseek_v3", "causal_discovery_gated")]
        ).to_csv(folder / "llm_daily_returns.csv", index=False)
    module = import_script("analyze_efs_pooled_v2")
    module.ROOT = fake
    module.PUBLIC = public
    module.PRIVATE = private
    module.validate_efs_trial = lambda root, trial: source_proof(trial)

    def marked_writer(path, value):
        if not Path(path).resolve().is_relative_to(fake.resolve()):
            raise RuntimeError("Fixture write escaped its isolated root")
        if isinstance(value, dict):
            value = {**value, "synthetic_fixture": True, "economic_result_credit": 0, "human_review": False}
        atomic_json(path, value)

    module.atomic_json = marked_writer

    def forbidden(*a, **kw):
        raise RuntimeError("Synthetic fixture must not access a network")

    socket.create_connection = forbidden
    socket.socket.connect = forbidden
    urllib.request.urlopen = forbidden
    print("SYNTHETIC_FIXTURE_BEGIN_NO_SCIENTIFIC_CREDIT", flush=True)
    module.main()
    result = public / "efs_pooled_analysis"
    primary = json.loads((result / "primary_comparisons.json").read_text())
    for row in primary:
        left = path_values[(row["backend"], "causal_discovery_gated")]["total_cost_10"]
        right = path_values[("grammar_101_103", "causal_discovery_gated")]["total_cost_10"]
        delta = []
        for month in pd.period_range("2019-01", "2024-12", freq="M"):
            use = dates.to_period("M") == month
            delta.append(np.prod(1 + left[use]) - np.prod(1 + right[use]))
        assert abs(row["full_sample_annualized_effect"] - 12 * np.mean(delta)) < 1e-12
    attribution = json.loads((result / "factor_attribution_diagnostics.json").read_text())
    assert sum(r["status"] == "not_identified" for r in attribution) == 2
    allocation = json.loads((result / "gross_factor_allocation_diagnostics.json").read_text())
    assert len(allocation) == 6 and all(r["common_jkp_only_baseline_verified"] for r in allocation)
    for name in ["gpt41", "deepseek_v3", "grammar"]:
        z = np.load(private / "efs_pooled_analysis" / (name + "_allocation_weights.npz"))
        assert z["weights"].shape == (36, 2, 134)
    native = public / "native_grouped_oos_analysis"
    native.mkdir()
    native_rows = []
    for case, n in [("alphaagent", 238), ("quantaalpha", 963)]:
        stats = grouped_t_effect(rng.normal(0, 0.003, n), frequency=252, groups=4, confidence=0.99)
        native_rows.append(
            {
                "case": case,
                "role": "primary_economic",
                "execution": "opening_information",
                "baseline": "alpha158",
                **stats,
            }
        )
    write_json(native / "comparisons.json", native_rows)
    write_json(
        native / "completion.json",
        {
            "status": "complete_family",
            "synthetic_fixture": True,
            "outputs": {"comparisons.json": sha256(native / "comparisons.json")},
        },
    )
    collector = import_script("collect_v2_project_primary_family")
    collector.ROOT = fake
    collector.PUBLIC = public
    collector.atomic_json = marked_writer
    sys.argv = ["synthetic_collector", "--require-complete"]
    collector.main()
    latest = json.loads((public / "project_primary_family/latest.json").read_text())
    family = json.loads((fake / latest["snapshot"] / "completion.json").read_text())
    assert family["status"] == "complete_four_contrast_family" and len(family["available_cases"]) == 4
    for folder in [result, fake / latest["snapshot"]]:
        completed = json.loads((folder / "completion.json").read_text())
        assert completed["synthetic_fixture"] and completed["economic_result_credit"] == 0
        for name, digest in completed["outputs"].items():
            assert sha256(folder / name) == digest
    assert sha256(fake / latest["snapshot"] / "completion.json") == latest["completion_sha256"]
    degenerate = next(row for row in primary if row["backend"] == "deepseek_v3")
    assert degenerate["degenerate_sampling_variation"] and degenerate["conservative_project_family_p"] == 1
    assert not degenerate["positive_pointwise99_and_project_bound_below001"]
    write_json(
        out / "validation.json",
        {
            "status": "synthetic_end_to_end_pass",
            "scope": "SYNTHETIC arithmetic/file-format/analysis integration only. Source and replay gate intentionally stubbed; no economic or replication credit.",
            "synthetic_returns_and_factors": True,
            "actual_market_calendar_only": True,
            "paired_means_match_independent_monthly_compounding": True,
            "unrestricted_ols_refused_for_both_synthetic_cases": True,
            "three_optional_sleeve_allocators_and_common_baseline_pass": True,
            "all4synthetic_cases_reach_collector": True,
            "metadata_marked_at_write_time_and_all_completion_hashes_match": True,
            "identical_synthetic_paths_do_not_become_significant": True,
            "new_model_calls": 0,
            "economic_result_credit": 0,
            "human_review": False,
            "probe_sha256": sha256(Path(__file__)),
            "analyzer_sha256": sha256(REAL_ROOT / "scripts/analyze_efs_pooled_v2.py"),
            "collector_sha256": sha256(REAL_ROOT / "scripts/collect_v2_project_primary_family.py"),
        },
    )
    print("SYNTHETIC_EFS_ANALYSIS_INTEGRATION_PASS_NO_SCIENTIFIC_CREDIT", flush=True)


if __name__ == "__main__":
    main()
