#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Export one finished native recorder explicitly, without changing model/results."""

from pathlib import Path
import argparse
import json
import shutil
import sys
from urllib.parse import urlparse, unquote
import pandas as pd
from mlflow.tracking import MlflowClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256


def recover_native_metric_artifacts(recorder):
    """Recover saved scalars/IC summaries; do not fit or rerun a portfolio."""
    artifacts = recorder / "artifacts"
    source = artifacts / "portfolio_analysis/port_analysis_1day.pkl"
    analysis = pd.read_pickle(source)
    if analysis.columns.tolist() != ["risk"] or analysis.index.nlevels != 2:
        raise ValueError("Unexpected native portfolio metric artifact")
    metrics = {"1day." + ".".join(key): float(value) for key, value in analysis["risk"].items()}
    proofs = {str(source.relative_to(recorder)): sha256(source)}
    for filename, mean_name, ratio_name in [("ic.pkl", "IC", "ICIR"), ("ric.pkl", "Rank IC", "Rank ICIR")]:
        path = artifacts / "sig_analysis" / filename
        values = pd.read_pickle(path)
        metrics[mean_name] = float(values.mean())
        metrics[ratio_name] = float(values.mean() / values.std())
        proofs[str(path.relative_to(recorder))] = sha256(path)
    return metrics, proofs


def export_record(workspace):
    workspace = Path(workspace).resolve()
    reports = list(workspace.glob("mlruns/*/*/artifacts/portfolio_analysis/report_normal_1day.pkl"))
    if len(reports) != 1:
        raise ValueError("Native recorder identity is missing or ambiguous")
    report = reports[0]
    recorder = report.parents[2]
    client = MlflowClient(tracking_uri=(workspace / "mlruns").as_uri())
    run = client.get_run(recorder.name)
    if run.info.status != "FINISHED" or run.info.end_time is None:
        raise ValueError("Native recorder is not finished")
    uri = urlparse(run.info.artifact_uri)
    if uri.scheme != "file" or Path(unquote(uri.path)).resolve() != report.parent.parent.resolve():
        raise ValueError("Native recorder points outside the selected workspace")
    if (workspace / "ret.pkl").exists() or (workspace / "qlib_res.csv").exists():
        raise ValueError("Preserve existing export; do not overwrite evidence")
    metrics = dict(run.data.metrics)
    scalar_proofs = {}
    metric_source = "existing_mlflow_metrics"
    if not metrics:
        # Old MLflow's async logger can die on a long feature-list parameter.
        # Preserve the empty original log; recover only independently stored data.
        metrics, scalar_proofs = recover_native_metric_artifacts(recorder)
        metric_source = "saved_native_portfolio_scalars_and_native_IC_series"
    shutil.copy2(report, workspace / "ret.pkl")
    pd.Series(metrics).to_csv(workspace / "qlib_res.csv")
    record = {
        "status": "pass",
        "native_recorder_id": recorder.name,
        "metric_source": metric_source,
        "saved_metric_artifact_hashes": scalar_proofs,
        "unrecovered_async_training_loss_history": not bool(run.data.metrics),
        "native_report_sha256": sha256(report),
        "ret_sha256": sha256(workspace / "ret.pkl"),
        "metrics_csv_sha256": sha256(workspace / "qlib_res.csv"),
        "native_metadata_sha256": sha256(recorder / "meta.yaml"),
        "native_metric_file_hashes": {
            str(p.relative_to(recorder)): sha256(p) for p in sorted((recorder / "metrics").rglob("*")) if p.is_file()
        },
        "export_script_sha256": sha256(Path(__file__)),
        "scope": "Copy the unique finished native account byte-for-byte and export its existing MLflow metrics through an explicit local tracking URI. If scalar logging failed, use saved native portfolio scalars and apply the native mean/sample-std formula to saved daily IC series. No fit, prediction, portfolio computation or return selection.",
    }
    atomic_json(workspace / "record_export.json", record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--finish-export-only-recovery", action="store_true")
    args = parser.parse_args()
    out = ROOT / "artifacts/fidelity_completion_v2" / args.run_name
    if (out / "completion.json").exists():
        raise ValueError("Preserve completed execution")
    recipe = json.loads((out / "execution_recipe.json").read_text())
    if sha256(out / "oos_config.yaml") != recipe["config_sha256"]:
        raise ValueError("Original native configuration changed")
    record = export_record(out)
    if args.finish_export_only_recovery:
        atomic_json(
            out / "export_recovery.json",
            {
                "status": "complete",
                "original_native_recipe_sha256": sha256(out / "execution_recipe.json"),
                "record_export_sha256": sha256(out / "record_export.json"),
                "retrained": False,
                "new_model_calls": 0,
                "reason": "Native execution completed; old reader/recorder discovery or inherited template export failed; old MLflow may also have lost scalar logs after its 1000-character parameter limit. Native artifact recovery preserves original logs.",
            },
        )
        atomic_json(
            out / "completion.json",
            {
                "status": "native_new_period_run_complete_independent_validation_pending",
                "arm": recipe["arm"],
                "case": recipe["case"],
                "plumbing_search_period_only": recipe["plumbing_search_period_only"],
                "returns_sha256": sha256(out / "ret.pkl"),
                "metrics_sha256": sha256(out / "qlib_res.csv"),
                "config_sha256": sha256(out / "oos_config.yaml"),
                "record_export_sha256": sha256(out / "record_export.json"),
                "new_model_calls": 0,
                "requires_independent_accounts_and_conditional_inference": True,
                "export_only_recovery": True,
            },
        )
    print("EXPLICIT_NATIVE_RECORDER_EXPORT_PASS", args.run_name, record["native_recorder_id"], flush=True)


if __name__ == "__main__":
    main()
