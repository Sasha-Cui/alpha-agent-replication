#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Export native Qlib accounts for the released 170-factor pool and 20-factor control."""

from pathlib import Path
import sys
import os
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
SOURCE = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_recovery/source_8a0343")
RECOVERY = SOURCE.parent
OUT = ROOT / "artifacts/publication_upgrade_v1/quantaalpha_native"
OUT.mkdir(parents=True, exist_ok=True)
os.chdir(OUT)
os.environ["MLFLOW_TRACKING_URI"] = "file://" + str(OUT / "mlruns")
from alpha_evolve.openrouter_budget import atomic_json, sha256
from rerun_quantaalpha_complete_pool import install_author_factor_modules, load_all_public_factors

install_author_factor_modules(SOURCE)
import numpy as np
import pandas as pd
import qlib.backtest as qbacktest
from backtest_v2.backtest_runner import BacktestRunner
from backtest_v2.factor_loader import FactorLoader

FactorLoader._parse_all_factors_from_json = load_all_public_factors
import qlib

original_init = qlib.init


def local_database_init(*args, **kwargs):
    kwargs["exp_manager"] = {
        "class": "MLflowExpManager",
        "module_path": "qlib.workflow.expm",
        "kwargs": {
            "uri": "sqlite:///" + str(OUT / "mlflow_tracking.sqlite3"),
            "default_exp_name": "publication_economic_fidelity",
        },
    }
    return original_init(*args, **kwargs)


qlib.init = local_database_init
original = qbacktest.backtest
active_case = None


def capture(*args, **kwargs):
    result = original(*args, **kwargs)
    metric, indicators = result
    if "1day" not in metric:
        raise ValueError("Native daily portfolio missing")
    report, positions = metric["1day"]
    path = OUT / active_case
    path.mkdir(parents=True, exist_ok=True)
    if not np.isfinite(report[["return", "cost", "bench"]].to_numpy()).all():
        raise ValueError("Nonfinite native returns cannot silently become zero")
    report.to_parquet(path / "daily_account.parquet")
    signal = kwargs["strategy"]["kwargs"]["signal"]
    signal.to_frame("score").to_parquet(path / "backtest_signal.parquet") if isinstance(
        signal, pd.Series
    ) else signal.to_parquet(path / "backtest_signal.parquet")
    rows = []
    for date, position in positions.items():
        for stock in position.get_stock_list():
            rows.append(
                {
                    "date": date,
                    "instrument": stock,
                    "amount": float(position.get_stock_amount(stock)),
                    "price": float(position.get_stock_price(stock)),
                    "weight": float(position.get_stock_weight(stock)),
                }
            )
    pd.DataFrame(rows).to_parquet(path / "positions.parquet", index=False)
    atomic_json(
        path / "backtest_contract.json",
        {
            "start": str(kwargs["start_time"]),
            "end": str(kwargs["end_time"]),
            "initial_account": kwargs["account"],
            "benchmark": kwargs["benchmark"],
            "exchange_kwargs": kwargs["exchange_kwargs"],
            "strategy": {k: v for k, v in kwargs["strategy"].items() if k != "kwargs"},
            "strategy_kwargs": {k: v for k, v in kwargs["strategy"]["kwargs"].items() if k != "signal"},
            "account_rows": len(report),
            "position_rows": len(rows),
        },
    )
    return result


qbacktest.backtest = capture
# This case reexecutes released factors, not fresh LLM discovery. Block HTTP paths.
import urllib.request
import requests

attempts = []


def blocked(*args, **kwargs):
    attempts.append(1)
    raise RuntimeError("Network forbidden in released-library execution")


urllib.request.urlopen = blocked
requests.sessions.Session.request = blocked
metrics = {}
for active_case, factor_source in [("released_170", "combined"), ("alpha158_20", "alpha158_20")]:
    runner = BacktestRunner(str(SOURCE / "backtest_v2/config.yaml"))
    runner.config["data"]["provider_uri"] = str(RECOVERY / "provider/cn_data")
    runner.config["llm"]["cache_dir"] = str(RECOVERY / "factor_cache_gpt_complete")
    runner.config["llm"]["auto_extract_cache"] = False
    runner.config.setdefault("factor_calculation", {})["n_jobs"] = 1
    runner.config["experiment"]["output_dir"] = str(OUT / active_case)
    runner.config["factor_source"]["custom"]["use_llm_for_incompatible"] = False
    metrics[active_case] = runner.run(
        factor_source=factor_source,
        factor_json=[str(SOURCE / "factor_library/RANKIC_desc_150_QA_round11_best_gpt_123_csi300.json")]
        if factor_source == "combined"
        else None,
        experiment_name="publication_" + active_case,
        output_name=active_case,
        test_period="default",
        ic_only=False,
    )
    if not (OUT / active_case / "daily_account.parquet").exists():
        raise ValueError("Native account exporter did not run")
    atomic_json(OUT / active_case / "native_metrics.json", metrics[active_case])
    print("CASE_COMPLETE", active_case, metrics[active_case], flush=True)
reference = json.loads(
    (ROOT / "paper_runs/paper_replication_audits/quantaalpha/complete_pool_native_result.json").read_text()
)["metrics"]
differences = {k: float(metrics["released_170"][k] - reference[k]) for k in reference}
if max(abs(v) for v in differences.values()) > 1e-9:
    raise ValueError("Complete-pool export changed the independently repeated native metric path: " + str(differences))
atomic_json(
    OUT / "completion.json",
    {
        "status": "complete",
        "implementation_type": "released_factor_library_and_predictor_reexecution",
        "fresh_agent_search": False,
        "network_attempts": len(attempts),
        "full_original_paper_reproduced": False,
        "metrics": metrics,
        "difference_from_frozen_170_result": differences,
        "source_config_sha256": sha256(SOURCE / "backtest_v2/config.yaml"),
        "factor_library_sha256": sha256(SOURCE / "factor_library/RANKIC_desc_150_QA_round11_best_gpt_123_csi300.json"),
        "runner_sha256": sha256(Path(__file__)),
        "source_backtest_runner_sha256": sha256(SOURCE / "backtest_v2/backtest_runner.py"),
        "outputs": {str(p.relative_to(OUT)): sha256(p) for p in OUT.glob("*/*") if p.is_file()},
    },
)
print("COMPLETE", flush=True)
