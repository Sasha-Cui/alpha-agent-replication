#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Execute frozen post-search Qlib comparisons only after explicit validation gates."""

from pathlib import Path
import argparse
import sys
import json
import os
import shutil
import hashlib
import importlib.metadata
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument(
        "--arm", choices=["source4", "source4_plus_library", "alpha158", "alpha158_plus_library"], required=True
    )
    parser.add_argument("--output-name", required=True)
    parser.add_argument(
        "--plumbing-search-period",
        action="store_true",
        help="Test pipeline using only the already-used source feedback period",
    )
    args = parser.parse_args()
    library = args.library.resolve()
    manifest = json.loads((library / "library_manifest.json").read_text())
    case = manifest["case"]
    source = PRIVATE / "dependencies" / ("alphaagent_95e478" if case == "alphaagent" else "quantaalpha_b7ceb27")
    source_hashes = {str(p.relative_to(source)): sha256(p) for p in sorted(source.rglob("*.py"))}
    source_hash = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    for name, digest in manifest["source_manifests"].items():
        run = PRIVATE / name
        if sha256(run / "used_factor_manifest.json") != digest:
            raise ValueError("Source used-library identity changed")
        replay = run / "full_replay_validation.json"
        if not replay.exists() or json.loads(replay.read_text())["status"] != "pass":
            raise ValueError("Source full replay is not validated: " + name)
        account = run / "independent_accounts/validation.json"
        if not account.exists() or json.loads(account.read_text())["status"] != "pass":
            raise ValueError("Native accounting is not validated")
    for row in manifest["programs"]:
        digest = row["code_sha256"]
        valid = False
        for name in row["source_runs"]:
            p = PRIVATE / name / "causality_full_universe" / (digest + ".json")
            if p.exists():
                proof = json.loads(p.read_text())
                if (
                    proof["status"] == "pass"
                    and proof["input_sha256"] == manifest["data_sha256"]
                    and proof["source_python_sha256"] == source_hash
                ):
                    valid = True
        if not valid:
            raise ValueError("Full-universe code/matrix/prefix gate missing for " + digest)
    for filename, key in [("fixed_factors.parquet", "matrix_sha256"), ("fixed_factors.pkl", "pickle_sha256")]:
        if sha256(library / filename) != manifest[key]:
            raise ValueError("Fixed feature matrix changed")
    out = PRIVATE / args.output_name
    if (out / "completion.json").exists():
        raise ValueError("Preserve completed new-period comparison")
    out.mkdir(parents=True, exist_ok=True)
    template = source / (
        "rdagent/scenarios/qlib/experiment/factor_template"
        if case == "alphaagent"
        else "quantaalpha/factors/factor_template"
    )
    for p in template.iterdir():
        if p.is_file() and p.suffix in [".py", ".yaml", ".md"]:
            shutil.copyfile(p, out / p.name)
    combined = args.arm.endswith("_plus_library")
    name = (
        ("conf_cn_combined.yaml" if case == "alphaagent" else "conf_combined_factors.yaml")
        if combined
        else ("conf.yaml" if case == "alphaagent" else "conf_baseline.yaml")
    )
    config = yaml.safe_load((template / name).read_text())
    embargo = json.loads(
        (ROOT / "paper_runs/fidelity_completion_v2/evaluation_label_embargo_amendment.json").read_text()
    )["cases"][case]
    config["qlib_init"]["provider_uri"] = json.loads((PRIVATE / "quantaalpha_data/manifest.json").read_text())[
        "provider_path"
    ]
    handler = config["task"]["dataset"]["kwargs"]["handler"]["kwargs"]
    if args.plumbing_search_period:
        handler["end_time"] = config["port_analysis_config"]["backtest"]["end_time"]
    else:
        handler["end_time"] = "2025-12-26"
        config["task"]["dataset"]["kwargs"]["segments"]["test"] = [
            embargo["first_evaluation_signal_date"],
            "2025-12-26",
        ]
        config["port_analysis_config"]["backtest"]["start_time"] = embargo["first_evaluation_execution_open"]
        config["port_analysis_config"]["backtest"]["end_time"] = "2025-12-26"
    if combined:
        target = "combined_factors_df.pkl" if case == "alphaagent" else "combined_factors_df.parquet"
        if (out / target).exists():
            raise ValueError("Unfinished output has an existing fixed matrix; inspect before reuse")
        os.link(library / ("fixed_factors.pkl" if case == "alphaagent" else "fixed_factors.parquet"), out / target)
    # Match the order/names of the released four-feature baseline in both
    # evaluation arms. Native search outputs retain their original source order.
    if combined and not args.arm.startswith("alpha158"):
        import copy

        baseline_name = "conf.yaml" if case == "alphaagent" else "conf_baseline.yaml"
        baseline_config = yaml.safe_load((template / baseline_name).read_text())
        baseline_loader = baseline_config["task"]["dataset"]["kwargs"]["handler"]["kwargs"]["data_loader"]
        handler["data_loader"]["kwargs"]["dataloader_l"][0] = copy.deepcopy(baseline_loader)
    if args.arm.startswith("alpha158"):
        from qlib.contrib.data.loader import Alpha158DL

        fields, names = Alpha158DL.get_feature_config()
        if len(fields) != 158 or len(names) != 158:
            raise ValueError("Unexpected native Alpha158 definition")
        loader = handler["data_loader"]
        if combined:
            loader = loader["kwargs"]["dataloader_l"][0]
        loader["kwargs"]["config"]["feature"] = [fields, names]
    configuration = out / "oos_config.yaml"
    configuration.write_text(yaml.safe_dump(config, sort_keys=False))
    atomic_json(
        out / "execution_recipe.json",
        {
            "case": case,
            "plumbing_search_period_only": args.plumbing_search_period,
            "arm": args.arm,
            "library_manifest_sha256": sha256(library / "library_manifest.json"),
            "config_sha256": sha256(configuration),
            "embargo": embargo,
            "financial_settings": "Unchanged source train/validation, model, processor, portfolio and fee parameters; only declared features and embargoed new-period dates differ. Source4 order/names are taken from its baseline in both paired arms.",
            "script_sha256": sha256(Path(__file__)),
            "logging_adapter_sha256": sha256(ROOT / "src/alpha_evolve/fidelity_qlib_logging_v2.py"),
            "full_original_paper_reproduced": False,
            "pristine_confirmatory_claim": False,
        },
    )
    os.chdir(out)
    os.environ["MLFLOW_TRACKING_URI"] = "file://" + str(out / "mlruns")
    os.environ["MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING"] = "false"
    from qlib.workflow.recorder import MLflowRecorder

    if hasattr(MLflowRecorder, "_log_uncommitted_code"):
        MLflowRecorder._log_uncommitted_code = lambda *a, **kw: None
    from alpha_evolve.fidelity_qlib_logging_v2 import install_long_parameter_logging

    install_long_parameter_logging(MLflowRecorder, out)
    from qlib.contrib.model.gbdt import LGBModel

    original_fit = LGBModel.fit

    def inspected_fit(self, dataset, *a, **kw):
        from qlib.data.dataset.handler import DataHandlerLP

        checks = []
        for segment in ["train", "valid", "test"]:
            frame = dataset.prepare(
                segment, col_set="feature", data_key=DataHandlerLP.DK_L if segment != "test" else DataHandlerLP.DK_I
            )
            values = frame.to_numpy(dtype=float)
            check = {
                "segment": segment,
                "rows": len(frame),
                "features": frame.shape[1],
                "infinite_values": int(np.isinf(values).sum()),
                "missing_values": int(np.isnan(values).sum()),
                "constant_or_missing_columns": int((frame.nunique(dropna=True) <= 1).sum()),
            }
            checks.append(check)
            if check["infinite_values"]:
                raise ValueError("Native model preprocessing leaves infinite inputs")
        atomic_json(out / "processed_feature_audit.json", checks)
        return original_fit(self, dataset, *a, **kw)

    LGBModel.fit = inspected_fit
    import socket
    import urllib.request

    def offline(*a, **kw):
        raise RuntimeError("Frozen new-period evaluation cannot access the network")

    socket.create_connection = offline
    socket.socket.connect = offline
    urllib.request.urlopen = offline
    entry = next(e for e in importlib.metadata.distribution("pyqlib").entry_points if e.name == "qrun")
    sys.argv = ["qrun", str(configuration)]
    entry.load()()
    sys.path.insert(0, str(ROOT / "scripts"))
    from export_native_qlib_record_v2 import export_record

    export_record(out)
    if not (out / "ret.pkl").exists() or not (out / "qlib_res.csv").exists():
        raise ValueError("Native evaluation artifacts missing")
    atomic_json(
        out / "completion.json",
        {
            "status": "native_new_period_run_complete_independent_validation_pending",
            "arm": args.arm,
            "case": case,
            "plumbing_search_period_only": args.plumbing_search_period,
            "returns_sha256": sha256(out / "ret.pkl"),
            "metrics_sha256": sha256(out / "qlib_res.csv"),
            "config_sha256": sha256(configuration),
            "new_model_calls": 0,
            "requires_independent_accounts_and_conditional_inference": True,
            "record_export_sha256": sha256(out / "record_export.json"),
        },
    )


if __name__ == "__main__":
    main()
