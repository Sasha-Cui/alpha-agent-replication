#!/usr/bin/env python3
# ruff: noqa: E402 - native source bootstrap
"""Reuse fixed predictions; recompute native portfolios under opening-only limits."""

from pathlib import Path
import argparse
import copy
import json
import os
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.fidelity_open_limits_v2 import install_opening_limits, PREVIOUS_CLOSE
from alpha_evolve.fidelity_qlib_logging_v2 import install_long_parameter_logging
from export_native_qlib_record_v2 import export_record


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-run", required=True)
    p.add_argument("--output-name", required=True)
    args = p.parse_args()
    private = ROOT / "artifacts/fidelity_completion_v2"
    source = private / args.source_run
    out = private / args.output_name
    if out.exists():
        raise ValueError("Preserve an existing execution sensitivity attempt")
    completion = json.loads((source / "completion.json").read_text())
    proof = json.loads((source / "independent_accounts/validation.json").read_text())
    if proof["status"] != "pass" or sha256(source / "ret.pkl") != completion["returns_sha256"]:
        raise ValueError("Source portfolio is not independently validated or changed")
    recipe = json.loads((source / "execution_recipe.json").read_text())
    if sha256(source / "oos_config.yaml") != recipe["config_sha256"] or proof["recipe_sha256"] != sha256(
        source / "execution_recipe.json"
    ):
        raise ValueError("Original source recipe changed")
    paths = list(source.glob("mlruns/*/*/artifacts/pred.pkl"))
    if len(paths) != 1:
        raise ValueError("Source prediction identity ambiguous")
    prediction = paths[0]
    label = prediction.with_name("label.pkl")
    if not label.exists():
        raise ValueError("Original signal label artifact absent")
    config = yaml.safe_load((source / "oos_config.yaml").read_text())
    exchange = config["port_analysis_config"]["backtest"]["exchange_kwargs"]
    if exchange["deal_price"] != "open" or exchange["limit_threshold"] != 0.095:
        raise ValueError("Unexpected original execution assumptions")
    exchange["subscribe_fields"] = list(dict.fromkeys([*exchange.get("subscribe_fields", []), PREVIOUS_CLOSE]))
    out.mkdir()
    (out / "oos_config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    updated = {
        **recipe,
        "script_sha256": sha256(Path(__file__)),
        "config_sha256": sha256(out / "oos_config.yaml"),
        "source_run": args.source_run,
        "source_prediction_sha256": sha256(prediction),
        "source_label_sha256": sha256(label),
        "source_execution_recipe_sha256": sha256(source / "execution_recipe.json"),
        "execution_sensitivity": "opening_information_limit_proxy",
        "execution_rule_sha256": sha256(ROOT / "src/alpha_evolve/fidelity_open_limits_v2.py"),
        "financial_settings": "Identical saved model predictions, portfolio rule, open fills, fees, lot rule, capital and dates. Eligibility uses known opening price and prior close under the same uniform9.5percent proxy. No retraining or market-liquidity equivalence claim.",
    }
    atomic_json(out / "execution_recipe.json", updated)
    os.chdir(out)
    import qlib
    from qlib.workflow.recorder import MLflowRecorder

    MLflowRecorder._log_uncommitted_code = lambda *a, **kw: None
    install_long_parameter_logging(MLflowRecorder, out)
    from qlib.backtest.exchange import Exchange

    install_opening_limits(Exchange, out)
    qlib.init(
        **config["qlib_init"],
        kernels=1,
        exp_manager={
            "class": "MLflowExpManager",
            "module_path": "qlib.workflow.expm",
            "kwargs": {"uri": (out / "mlruns").as_uri(), "default_exp_name": "opening_information_sensitivity"},
        },
    )
    import socket
    import urllib.request

    def forbidden(*a, **kw):
        raise RuntimeError("Saved-prediction execution replay cannot call network")

    socket.create_connection = forbidden
    socket.socket.connect = forbidden
    urllib.request.urlopen = forbidden
    from qlib.workflow import R
    from qlib.workflow.record_temp import SigAnaRecord, PortAnaRecord

    with R.start(experiment_name="opening_information_sensitivity"):
        recorder = R.get_recorder()
        recorder.log_artifact(str(prediction))
        recorder.log_artifact(str(label))
        recorder.log_params(
            source_run=args.source_run,
            execution_rule="opening_information_limit_proxy",
            source_prediction_sha256=sha256(prediction),
        )
        SigAnaRecord(recorder=recorder, ana_long_short=False, ann_scaler=252).generate()
        PortAnaRecord(recorder=recorder, config=copy.deepcopy(config["port_analysis_config"])).generate()
    saved = list(out.glob("mlruns/*/*/artifacts/pred.pkl"))
    if len(saved) != 1 or sha256(saved[0]) != sha256(prediction):
        raise ValueError("Prediction bytes changed")
    export_record(out)
    audit = json.loads((source / "processed_feature_audit.json").read_text())
    atomic_json(out / "processed_feature_audit.json", audit)
    atomic_json(
        out / "completion.json",
        {
            "status": "native_new_period_run_complete_independent_validation_pending",
            "case": recipe["case"],
            "arm": recipe["arm"],
            "plumbing_search_period_only": recipe["plumbing_search_period_only"],
            "returns_sha256": sha256(out / "ret.pkl"),
            "metrics_sha256": sha256(out / "qlib_res.csv"),
            "config_sha256": sha256(out / "oos_config.yaml"),
            "record_export_sha256": sha256(out / "record_export.json"),
            "execution_sensitivity": "opening_information_limit_proxy",
            "predictions_byte_identical": True,
            "retrained": False,
            "new_model_calls": 0,
            "requires_independent_accounts_and_conditional_inference": True,
        },
    )
    print("NATIVE_OPENING_INFORMATION_REPLAY_COMPLETE", out.name, flush=True)


if __name__ == "__main__":
    main()
