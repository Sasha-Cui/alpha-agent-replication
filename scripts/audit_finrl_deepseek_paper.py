#!/usr/bin/env python3
"""Fail-closed paper-level audit of FinRL-DeepSeek.

The audit pins the arXiv paper, the nearest pre-submission and current source
revisions, the official Hugging Face data/checkpoint releases, the stored
notebook outputs, and native released-checkpoint evaluations.  Availability,
loadability, and component execution never imply paper-result reproduction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import py_compile
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


PAPER_URL = "https://arxiv.org/abs/2502.07393"
PAPER_SUBMITTED = "2025-02-11T09:23:14Z"
PAPER_PDF_SHA256 = "3a479199fac6b69525416028672288620009bb51c78381790821f4f42ce3e7ca"
PAPER_SOURCE_SHA256 = "f8def8f2b873cce6c495813201b5d3b49cc2123f72b0004859f8a94c76862719"
ARXIV_API_SHA256 = "35ed2de5cfcb3997029d3dd3a3b570ba38b60ebd1a6d78b16caa7815444da122"
SOURCE_URL = "https://github.com/benstaf/FinRL_DeepSeek"
PRE_SUBMISSION_COMMIT = "43e58573274c480e4d5f5b3c946073e2cb2e49a6"
PRE_SUBMISSION_DATE = "2025-02-07T18:05:01+01:00"
CURRENT_COMMIT = "5c21a923214bca6370800efd45f8c6c1ef776ae7"
CURRENT_DATE = "2025-04-08T14:22:13+02:00"
FINRL_NOTEBOOK_COMMIT = "cd016b667da1860939b43bb77aba7ff4e35f780f"
ELEGANTRL_NOTEBOOK_COMMIT = "2fa34dd9236498beada8d8443d927970a9de1f7f"
HF_DATASET_URL = "https://huggingface.co/datasets/benstaf/nasdaq_2013_2023"
HF_DATASET_COMMIT = "b80bc15e4320eac68f53cfdd2fff3365e55dfedd"
HF_AGENTS_URL = "https://huggingface.co/benstaf/Trading_agents"
HF_AGENTS_COMMIT = "2153a7266aac75f9613fdae1bde09dbd38691c59"

METRICS = ("Information Ratio", "CVaR", "Rachev Ratio")
TABLES = {
    "Table 1 main 100-epoch comparison": {
        "PPO": (0.0100, -0.0394, 1.0637),
        "CPPO": (-0.0148, -0.0439, 1.0404),
        "PPO-DeepSeek 10%": (-0.0093, -0.0338, 0.9890),
        "CPPO-DeepSeek 10%": (0.0078, -0.0437, 0.9818),
    },
    "Table 2 PPO infusion": {
        "PPO": (0.0100, -0.0394, 1.0637),
        "PPO-DeepSeek 10%": (-0.0093, -0.0338, 0.9890),
        "PPO-DeepSeek 1%": (-0.0252, -0.0459, 1.0394),
        "PPO-DeepSeek 0.1%": (-0.0011, -0.0375, 0.9536),
    },
    "Table 3 CPPO infusion": {
        "CPPO": (-0.0148, -0.0439, 1.0404),
        "CPPO-DeepSeek 10%": (0.0078, -0.0437, 0.9818),
        "CPPO-DeepSeek 1%": (-0.0032, -0.0365, 0.9573),
        "CPPO-DeepSeek 0.1%": (-0.0060, -0.0441, 0.9789),
    },
}

NOTEBOOK_RESULTS = {
    "cell80": {
        "PPO": (0.0013, -0.0415, 1.0430),
        "CPPO": (-0.0035, -0.0434, 1.1000),
        "PPO-DeepSeek 10%": (-0.0132, -0.0396, 0.9609),
        "CPPO-DeepSeek 10%": (0.0035, -0.0447, 0.9446),
    },
    "cell81": {
        "PPO": (0.0010, -0.0403, 1.0425),
        "PPO-DeepSeek 10%": (-0.0085, -0.0370, 1.0025),
        "PPO-DeepSeek 1%": (-0.0277, -0.0483, 1.0690),
    },
}

NOTEBOOK_CELL_FOR_TABLE = {
    "Table 1 main 100-epoch comparison": "cell80",
    "Table 2 PPO infusion": "cell81",
    "Table 3 CPPO infusion": "cell80",
}

FIGURES = {
    "Figure 1 / download4.png": (
        "2023-01--2023-12",
        ("PPO 25 epochs", "CPPO 25 epochs", "PPO-Qwen 25 epochs", "CPPO-Qwen 25 epochs", "Nasdaq-100 index"),
    ),
    "Figure 2 / download10.png": (
        "2020-01--2023-12",
        ("PPO 20 epochs", "CPPO 20 epochs", "PPO-DeepSeek 20 epochs", "PPO-Llama 20 epochs", "CPPO-DeepSeek 20 epochs", "CPPO-Llama 20 epochs", "Nasdaq-100 index"),
    ),
    "Figure 3 / download15.png": (
        "2020-01--2023-12",
        ("PPO 100 epochs", "CPPO 100 epochs", "PPO-DeepSeek 100 epochs", "CPPO-DeepSeek 100 epochs", "Nasdaq-100 index"),
    ),
    "Figure 4 / download13.png": (
        "2020-01--2023-12",
        ("PPO 100 epochs", "CPPO 100 epochs", "PPO-DeepSeek 100 epochs", "CPPO-DeepSeek 100 epochs", "Nasdaq-100 index"),
    ),
    "Figure 5 / download17.png": (
        "2020-01--2023-12",
        ("PPO", "PPO-DeepSeek 10%", "PPO-DeepSeek 1%", "PPO-DeepSeek 0.1%", "Nasdaq-100 index"),
    ),
    "Figure 6 / download18.png": (
        "2020-01--2023-12",
        ("CPPO", "CPPO-DeepSeek 10%", "CPPO-DeepSeek 1%", "CPPO-DeepSeek 0.1%", "Nasdaq-100 index"),
    ),
}

EXPECTED_DATA_HASHES = {
    "trade_data_2019_2023.csv": "01587b66236b5563df8f871f0110bbf752f1c593427a346192c20e271efffd3b",
    "trade_data_deepseek_risk_2019_2023.csv": "e5f510b815f7e6d05dba9307b71f2ca738f7370c77a4206b17b5fbd5dd23898d",
    "trade_data_deepseek_sentiment_2019_2023.csv": "1d827b3685e914bdbb4ee6270e556ba1a4490976a717bc85dc729f26ff980fef",
}

EXPECTED_AGENT_HASHES = {
    "agent_ppo_100_epochs_20k_steps.pth": "f138a91c36e0b88b27d58bf41549de24717aec48e7107641f3dfa1838b51177b",
    "agent_cppo_100_epochs_20k_steps.pth": "c7017d10df45958f1a09ee8e009d8c99346be867ff312b03876ed1b8cfb289b1",
    "agent_ppo_deepseek_100_epochs_20k_steps.pth": "ae05dd713d1c0e8a880daad0a3be49db0314c50211805272f8a61dd84794ef84",
    "agent_ppo_deepseek_100_epochs_20k_steps_01.pth": "0969fc0b9d4c49aa816b2ec88dd321ffa619d765df27d79ef8975797747b8d5b",
    "agent_ppo_deepseek_100_epochs_20k_steps_1.pth": "3f54f756654dc9a23c9c6fe6836a0be5ac03cc1fecf8952f020e58f63291fb8c",
    "agent_cppo_deepseek_100_epochs_20k_steps.pth": "b8dc3e1cc247a16c258d6940644008f3a491f0dd962145d37659a66c55b99d44",
    "agent_cppo_deepseek_100_epochs_20k_steps_01.pth": "672fa6bfc0e656f724833fac2046f04f5598fd9a87a1ea457bcaf9b1a2edcda0",
    "agent_cppo_deepseek_100_epochs_20k_steps_1.pth": "0995acb84653b5ffbfaab13fed295ff1efa8443df66f6dfe80e0ac82280fe53d",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return proc.stdout


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError("refusing to write empty CSV: %s" % path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_table_rows(native_seed0: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
    native = (native_seed0 or {}).get("results", {})
    rows: list[dict[str, Any]] = []
    for table, methods in TABLES.items():
        for method, values in methods.items():
            for metric, paper_value in zip(METRICS, values):
                native_value: Any = ""
                if metric == "CVaR" and method in native:
                    native_value = native[method]["cvar"]
                elif metric == "Rachev Ratio" and method in native:
                    native_value = native[method]["rachev_ratio"]
                match = native_value != "" and f"{float(native_value):.4f}" == f"{paper_value:.4f}"
                rows.append(
                    {
                        "paper_table": table,
                        "method": method,
                        "metric": metric,
                        "unique_measurement_id": method + " / " + metric,
                        "paper_value": f"{paper_value:.4f}",
                        "native_seed0_value": "" if native_value == "" else f"{float(native_value):.12g}",
                        "display_precision_match": match,
                        "status": (
                            "not_reproduced_benchmark_series_not_frozen"
                            if metric == "Information Ratio"
                            else "native_value_matches_but_protocol_unpinned_no_credit"
                            if match
                            else "native_released_checkpoint_mismatch"
                        ),
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 36 or len({row["unique_measurement_id"] for row in rows}) != 24:
        raise RuntimeError("FinRL-DeepSeek table census changed")
    return rows


def unique_measurement_rows(table_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in table_rows:
        key = str(row["unique_measurement_id"])
        if key not in unique:
            unique[key] = {
                "unique_measurement_id": key,
                "method": row["method"],
                "metric": row["metric"],
                "paper_value": row["paper_value"],
                "native_seed0_value": row["native_seed0_value"],
                "display_precision_match": row["display_precision_match"],
                "paper_result_credit": False,
            }
    if len(unique) != 24:
        raise RuntimeError("FinRL-DeepSeek unique result census changed")
    return list(unique.values())


def notebook_conformance_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table, methods in TABLES.items():
        cell = NOTEBOOK_CELL_FOR_TABLE[table]
        outputs = NOTEBOOK_RESULTS[cell]
        for method, paper_values in methods.items():
            notebook_values = outputs.get(method)
            for i, (metric, paper_value) in enumerate(zip(METRICS, paper_values)):
                notebook_value = "" if notebook_values is None else notebook_values[i]
                match = notebook_value != "" and f"{float(notebook_value):.4f}" == f"{paper_value:.4f}"
                rows.append(
                    {
                        "paper_table": table,
                        "notebook_cell": cell,
                        "method": method,
                        "metric": metric,
                        "paper_value": f"{paper_value:.4f}",
                        "stored_notebook_value": "" if notebook_value == "" else f"{float(notebook_value):.4f}",
                        "status": "missing_stored_output" if notebook_value == "" else "match" if match else "stored_output_mismatch",
                        "paper_result_credit": False,
                    }
                )
    return rows


def notebook_stale_output_rows() -> list[dict[str, Any]]:
    rows = []
    for method in ("PPO", "PPO-DeepSeek 10%"):
        for i, metric in enumerate(METRICS):
            a = NOTEBOOK_RESULTS["cell80"][method][i]
            b = NOTEBOOK_RESULTS["cell81"][method][i]
            rows.append(
                {
                    "method": method,
                    "metric": metric,
                    "cell80_value": f"{a:.4f}",
                    "cell81_value": f"{b:.4f}",
                    "status": "same_series_different_stored_output",
                }
            )
    return rows


def figure_rows() -> list[dict[str, Any]]:
    rows = []
    for figure, (span, series) in FIGURES.items():
        for label in series:
            rows.append(
                {
                    "figure": figure,
                    "visible_date_span": span,
                    "series": label,
                    "released_numeric_series": False,
                    "native_exact_curve_reproduced": False,
                    "status": "paper_raster_only",
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 32:
        raise RuntimeError("FinRL-DeepSeek figure series census changed")
    return rows


def figure_metric_rows() -> list[dict[str, Any]]:
    return [
        {"figure": "Figure 1", "series": method, "metric": "Information Ratio", "paper_value": f"{value:.4f}", "status": "raster_label_not_reproduced", "paper_result_credit": False}
        for method, value in (
            ("PPO 25 epochs", -0.0148),
            ("CPPO 25 epochs", -0.0382),
            ("PPO-Qwen 25 epochs", -0.0178),
            ("CPPO-Qwen 25 epochs", -0.0726),
        )
    ]


def mechanism_conformance() -> list[dict[str, Any]]:
    rows = [
        ("PPO clipped objective", "train_ppo.py compute_loss_pi", "implemented_match"),
        ("Gaussian actor and critic", "MLPActorCritic in training and notebook", "implemented_match"),
        ("recommendation score in state", "llm_sentiment appended to LLM environments", "implemented_match"),
        ("10% recommendation action multipliers", "env_stocktrading_llm.py uses 0.9/0.95/1.05/1.1", "implemented_match"),
        ("1% recommendation action multipliers", "env_stocktrading_llm_1.py uses 0.99/0.995/1.005/1.01", "implemented_match"),
        ("0.1% recommendation action multipliers", "env_stocktrading_llm_01.py uses 0.999/0.9995/1.0005/1.001", "implemented_match"),
        ("neutral recommendation factor", "paper says unchanged; 10% source multiplies neutral actions by 0.98", "mechanism_conflict"),
        ("CPPO CVaR objective", "source subtracts a clipped value update from GAE; it does not implement the displayed Lagrangian objective", "not_implemented_as_claimed"),
        ("CPPO trajectory-buffer isolation", "CPPOBuffer.finish_path subtracts the full valupdate buffer from the full advantage buffer on every trajectory, repeatedly modifying earlier slices", "implementation_bug"),
        ("CVaR alpha 0.05 worst tail", "source training default alpha is 0.85 and uses 1-alpha", "config_conflict"),
        ("trajectory return D(pi)", "source updates adjusted_D_pi at every environment step from ep_ret + v - r", "mechanism_conflict"),
        ("aggregate portfolio risk", "source weights risk scores by invested stock value and omits cash", "partial_match"),
        ("paper 10% CPPO risk weights", "only train_cppo_llm_old.py uses 0.9--1.1; it is a 25-epoch local Qwen path", "missing_exact_training_lineage"),
        ("100-epoch DeepSeek CPPO 1% risk weights", "train_cppo_llm_risk.py uses 0.99--1.01 and saves an unmatched _99_101 name", "source_checkpoint_name_conflict"),
        ("100-epoch DeepSeek CPPO 0.1% risk weights", "train_cppo_llm_risk_01.py saves a name absent from the official release", "source_checkpoint_name_conflict"),
        ("DeepSeek recommendation prompt", "paper gives zero-shot core prompt; post-paper source adds few-shot examples and batching", "post_paper_prompt_expansion"),
        ("DeepSeek risk prompt", "paper gives zero-shot core prompt; post-paper source adds few-shot examples and batching", "post_paper_prompt_expansion"),
        ("temperature zero", "post-paper DeepInfra scripts set temperature=0", "post_paper_implementation_only"),
        ("one random article per stock/day", "selection code, seed, and selected article IDs are absent", "missing_artifact"),
        ("FNSPID 15.7M to 2M reduction", "neither raw subset nor reduction manifest is released", "missing_artifact"),
        ("DeepSeek V3 signal values", "frozen derived sentiment/risk columns are released", "released_derived_artifact"),
        ("PPO/CPPO released checkpoint evaluation", "eight paper-relevant checkpoints load and execute on released CSVs", "native_component_executed"),
        ("stochastic evaluation", "notebook samples Gaussian actions but sets no evaluation seed", "unreproducible_random_protocol"),
        ("Nasdaq benchmark", "notebook downloads live Yahoo ticker ndx with no frozen series", "temporally_unpinned_input"),
        ("transaction costs", "all training/backtest environments set 0.1% buy and sell costs", "implemented_match"),
        ("turbulence liquidation", "backtest sets vix threshold 70; paper does not report it", "undisclosed_material_config"),
    ]
    return [{"paper_dimension": a, "source_evidence": b, "status": c, "paper_mechanism_credit": c == "implemented_match"} for a, b, c in rows]


def config_conformance() -> list[dict[str, Any]]:
    rows = [
        ("training dates", "2013-01-01--2018-12-31", "same in preprocessing scripts", "match"),
        ("trading dates", "2019-01-01--2023-12-31", "released CSV 2019-01-02--2023-12-28; main figures visibly start 2020", "paper_figure_conflict"),
        ("training steps", "2,000,000", "100 epochs x 20,000 parser/default", "match"),
        ("epochs", "100", "100 for named main scripts", "match"),
        ("hidden layers", "not stated", "512 x 512", "source_only"),
        ("PPO gamma", "not stated", "0.995", "source_only"),
        ("PPO clip ratio", "epsilon unspecified", "0.7", "paper_underspecified"),
        ("CPPO alpha", "example 0.05 worst tail", "0.85", "conflict"),
        ("CPPO beta", "symbol only", "3000.0", "source_only"),
        ("PPO seed", "not stated", "42", "paper_underspecified"),
        ("CPPO seed", "not stated", "0", "paper_underspecified"),
        ("evaluation seed", "not stated", "none", "missing"),
        ("hmax", "not stated", "100", "source_only"),
        ("initial cash", "not stated", "1,000,000", "source_only"),
        ("buy/sell costs", "not stated", "0.001 each", "source_only"),
        ("turbulence control", "not stated", "vix >= 70 liquidates all positions", "undisclosed_material_config"),
        ("stock universe", "Nasdaq-100", "84 survivors from July 17 2023 list across all years", "lookahead_universe"),
        ("benchmark symbol", "Nasdaq-100", "live Yahoo input 'ndx'", "temporally_unpinned"),
        ("missing sentiment", "not stated", "filled with 0 outside paper score range", "paper_underspecified"),
        ("missing risk", "not stated", "filled with neutral score 3", "source_only"),
    ]
    return [{"configuration": a, "paper_value": b, "source_value": c, "status": d} for a, b, c, d in rows]


def internal_checks() -> list[dict[str, Any]]:
    checks = [
        ("Table 1 values repeated in Tables 2/3", "12 repeated cells are internally identical", "pass"),
        ("notebook cell80 versus paper Table 1", "0/12 displayed values match", "paper_source_result_conflict"),
        ("notebook cell81 versus paper Table 2", "0/9 available values match; 3 are absent", "paper_source_result_conflict"),
        ("notebook Table 3 cell", "cell82 has no output and plots result instead of result_cppo", "broken_evaluation_cell"),
        ("notebook repeated PPO metrics", "cell80 and cell81 disagree on all three metrics for the same series", "stale_output_conflict"),
        ("notebook repeated PPO-DeepSeek 10% metrics", "cell80 and cell81 disagree on all three metrics for the same series", "stale_output_conflict"),
        ("PPO 0.1% notebook path", "normalization/filtering is commented out but later referenced", "broken_evaluation_cell"),
        ("figure 2 duration", "caption says 3 years, prose says 2019--2023, raster shows 2020--2023", "paper_internal_conflict"),
        ("main figure trading span", "Figures 2--6 visibly begin 2020 despite declared 2019 start", "paper_internal_conflict"),
        ("figure 1 training duration", "caption says 3 years while 2019--2022 is four calendar years", "paper_internal_conflict"),
        ("installation entrypoint", "installation_script.sh invokes nonexistent train_ppo_deepseek.py", "broken_installation_path"),
        ("current Python syntax", "risk_deepseek_deepinfra.py has an empty api_key assignment", "post_paper_syntax_error"),
        ("paper-era prompt implementation", "pre-submission source contains no LLM API scoring script", "missing_paper_era_source"),
        ("official checkpoint source lineage", "several released names have no exact producing script/log filename", "provenance_gap"),
    ]
    return [{"check": a, "evidence": b, "status": c} for a, b, c in checks]


def specification_gaps() -> list[dict[str, Any]]:
    gaps = [
        ("random article selection seed and selected IDs", "required for exact LLM inputs"),
        ("raw 2M-record selected FNSPID subset", "required to reconstruct derived signals"),
        ("exact paper-era API provider/model snapshot", "DeepSeek V3 service is mutable"),
        ("complete prompts including batching/few-shot messages", "paper and post-paper source differ"),
        ("LLM response logs and parsing failures", "derived scores cannot be traced"),
        ("exact FinRL/spinningup revisions used for training", "training installer follows live Git heads"),
        ("complete Python/package lock", "not released"),
        ("paper evaluation RNG seeds/states", "notebook samples actions without a seed"),
        ("frozen Nasdaq-100 benchmark series", "notebook performs a live Yahoo download"),
        ("numeric portfolio paths behind six rasters", "only PNGs are in paper source"),
        ("checkpoint-to-training-run manifest", "filenames do not provide exact lineage"),
        ("exact 100-epoch DeepSeek 10% CPPO entrypoint", "not released"),
        ("exact 100-epoch DeepSeek 1% PPO entrypoint", "not released"),
        ("exact 100-epoch DeepSeek 1% CPPO checkpoint name mapping", "not released"),
        ("exact 100-epoch DeepSeek 0.1% CPPO checkpoint name mapping", "not released"),
        ("paper table-generating notebook revision/output", "released stored outputs disagree"),
        ("explanation of 2020 raster start versus 2019 protocol", "not provided"),
        ("Nasdaq membership/reconstitution protocol", "source uses a July 2023 survivor list"),
        ("rationale for VIX threshold 70", "material backtest rule absent from paper"),
        ("replicate seeds/error bars", "paper shows two curves but no tabular uncertainty"),
    ]
    return [{"missing_item": a, "why_required": b, "resolved": "no"} for a, b in gaps]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    files = str(run_git(source_root, "ls-files")).splitlines()
    return [
        {
            "path": rel,
            "size_bytes": (source_root / rel).stat().st_size,
            "sha256": sha256(source_root / rel),
            "paper_result_artifact": False,
        }
        for rel in files
    ]


def paper_source_inventory(source_root: Path) -> list[dict[str, Any]]:
    return [
        {"path": str(path.relative_to(source_root)), "size_bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(source_root.rglob("*"))
        if path.is_file()
    ]


def hf_inventory(api_path: Path, tree_path: Path, kind: str) -> list[dict[str, Any]]:
    api = json.loads(api_path.read_text(encoding="utf-8"))
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    rows = []
    for item in tree:
        lfs = item.get("lfs") or {}
        rows.append(
            {
                "release_kind": kind,
                "repository_commit": api["sha"],
                "path": item["path"],
                "size_bytes": item["size"],
                "sha256_or_git_oid": lfs.get("oid", item.get("oid", "")),
                "last_commit_date": (item.get("lastCommit") or {}).get("date", ""),
                "paper_input_or_checkpoint": item["path"].endswith((".csv", ".pth")),
            }
        )
    return rows


def compile_revision(source_root: Path, revision: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        archive = run_git(source_root, "archive", revision, binary=True)
        tar_path = Path(tmp) / "source.tar"
        tar_path.write_bytes(archive)
        subprocess.run(["tar", "-xf", str(tar_path), "-C", tmp], check=True)
        python_files = sorted(Path(tmp).glob("*.py"))
        failures = []
        for path in python_files:
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                failures.append({"path": path.name, "error": str(exc)})
    return {"revision": revision, "python_files": len(python_files), "compiled": len(python_files) - len(failures), "failures": failures}


def validate_native_inputs(artifacts_root: Path) -> dict[str, Any]:
    checked = []
    for subdir, expected in (("data", EXPECTED_DATA_HASHES), ("agents", EXPECTED_AGENT_HASHES)):
        for name, digest in expected.items():
            path = artifacts_root / subdir / name
            actual = sha256(path)
            if actual != digest:
                raise ValueError("artifact hash mismatch: %s" % path)
            checked.append({"path": subdir + "/" + name, "sha256": actual, "size_bytes": path.stat().st_size})
    runs = {}
    for name in ("native_seed0.json", "native_seed42.json", "native_mean.json"):
        run = json.loads((artifacts_root / name).read_text(encoding="utf-8"))
        if run["source_revision"] != CURRENT_COMMIT or len(run["results"]) != 8:
            raise ValueError("invalid native execution record: %s" % name)
        runs[name] = run
    return {
        "execution_driver": "scripts/run_finrl_deepseek_native.py",
        "source_revision": CURRENT_COMMIT,
        "execution_environment": {
            "python": "3.12.8",
            "torch": "2.10.0+cu128",
            "numpy": "2.3.5",
            "pandas": "2.2.3",
            "scipy": "1.17.1",
            "device": "cpu",
            "omp_num_threads": 8,
            "mkl_num_threads": 8,
        },
        "input_artifacts": checked,
        "runs": runs,
        "paper_result_credit": False,
        "credit_reason": "Released components execute, but the paper/notebook fix no evaluation seed or benchmark snapshot, and no run reproduces the paper table at displayed precision.",
    }


def build_audit(
    source_root: Path,
    paper_root: Path,
    artifacts_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if str(run_git(source_root, "rev-parse", "HEAD")).strip() != CURRENT_COMMIT:
        raise ValueError("source checkout is not pinned to the audited current commit")
    expected_files = {
        "paper.pdf": PAPER_PDF_SHA256,
        "source.tar": PAPER_SOURCE_SHA256,
        "arxiv_api.xml": ARXIV_API_SHA256,
    }
    for name, expected in expected_files.items():
        if sha256(paper_root / name) != expected:
            raise ValueError("primary-source hash mismatch: %s" % name)
    data_api = json.loads((paper_root / "hf_nasdaq_api.json").read_text(encoding="utf-8"))
    agent_api = json.loads((paper_root / "hf_agents_api.json").read_text(encoding="utf-8"))
    if data_api["sha"] != HF_DATASET_COMMIT or agent_api["sha"] != HF_AGENTS_COMMIT:
        raise ValueError("Hugging Face release commit drift")

    output_dir.mkdir(parents=True, exist_ok=True)
    native = validate_native_inputs(artifacts_root)
    seed0 = native["runs"]["native_seed0.json"]
    tables = paper_table_rows(seed0)
    unique = unique_measurement_rows(tables)
    notebook = notebook_conformance_rows()
    figures = figure_rows()
    figure_metrics = figure_metric_rows()
    mechanisms = mechanism_conformance()
    configs = config_conformance()
    checks = internal_checks()
    gaps = specification_gaps()
    source_files = source_inventory(source_root)
    paper_files = paper_source_inventory(paper_root / "source")
    data_files = hf_inventory(paper_root / "hf_nasdaq_api.json", paper_root / "hf_nasdaq_tree.json", "dataset")
    agent_files = hf_inventory(paper_root / "hf_agents_api.json", paper_root / "hf_agents_tree.json", "checkpoint")
    compile_pre = compile_revision(source_root, PRE_SUBMISSION_COMMIT)
    compile_current = compile_revision(source_root, CURRENT_COMMIT)

    outputs = {
        "paper_numeric_table_conformance.csv": tables,
        "paper_unique_measurement_conformance.csv": unique,
        "released_notebook_metric_conformance.csv": notebook,
        "released_notebook_stale_output_conflicts.csv": notebook_stale_output_rows(),
        "paper_figure_series_inventory.csv": figures,
        "paper_numeric_figure_labels.csv": figure_metrics,
        "source_mechanism_conformance.csv": mechanisms,
        "source_config_conformance.csv": configs,
        "paper_internal_and_source_checks.csv": checks,
        "paper_specification_gaps.csv": gaps,
        "released_source_inventory.csv": source_files,
        "paper_source_asset_inventory.csv": paper_files,
        "released_dataset_inventory.csv": data_files,
        "released_agent_inventory.csv": agent_files,
    }
    for name, rows in outputs.items():
        write_csv(output_dir / name, rows)
    (output_dir / "native_released_agent_execution.json").write_text(json.dumps(native, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "source_compilation.json").write_text(json.dumps({"pre_submission": compile_pre, "current": compile_current}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    notebook_counts = Counter(row["status"] for row in notebook)
    native_matches = sum(str(row["display_precision_match"]) == "True" for row in tables)
    manifest = {
        "paper": "FinRL-DeepSeek: LLM-Infused Risk-Sensitive Reinforcement Learning for Trading Agents",
        "paper_url": PAPER_URL,
        "paper_submitted": PAPER_SUBMITTED,
        "source_url": SOURCE_URL,
        "pre_submission_source_commit": PRE_SUBMISSION_COMMIT,
        "current_source_commit": CURRENT_COMMIT,
        "hf_dataset_commit": HF_DATASET_COMMIT,
        "hf_agents_commit": HF_AGENTS_COMMIT,
        "overall_status": "released_data_checkpoints_and_code_execute_but_paper_results_not_reproduced",
        "full_paper_reproduced": False,
        "paper_numeric_table_cells_total": len(tables),
        "paper_unique_numeric_measurements_total": len(unique),
        "native_table_cells_display_precision_matches": native_matches,
        "native_table_cells_with_paper_result_credit": 0,
        "stored_notebook_table_cells_present": len(notebook) - notebook_counts["missing_stored_output"],
        "stored_notebook_table_cells_missing": notebook_counts["missing_stored_output"],
        "stored_notebook_table_cells_matching_paper": notebook_counts["match"],
        "stored_notebook_same_series_conflicts": 6,
        "paper_figure_series_total": len(figures),
        "paper_numeric_figure_labels_total": len(figure_metrics),
        "native_exact_figure_series_reproduced": 0,
        "paper_relevant_released_checkpoints_executed": 8,
        "native_evaluation_protocols_executed": 3,
        "released_dataset_files_total": len(data_files),
        "released_checkpoint_files_total": sum(row["path"].endswith(".pth") for row in agent_files),
        "current_tracked_source_files_total": len(source_files),
        "pre_submission_python_files_compiled": compile_pre["compiled"],
        "pre_submission_python_files_total": compile_pre["python_files"],
        "current_python_files_compiled": compile_current["compiled"],
        "current_python_files_total": compile_current["python_files"],
        "paper_mechanism_dimensions_audited": len(mechanisms),
        "paper_mechanism_dimensions_credited": sum(row["paper_mechanism_credit"] for row in mechanisms),
        "unresolved_specification_gaps": len(gaps),
    }
    report = f"""# FinRL-DeepSeek paper-level replication audit

## Verdict

The release is a substantial and unusually useful component package: the paper-era Hugging Face release contains 15 checkpoints, the dataset release contains frozen train/trade CSVs, the Git repository contains paper-era environments/training logs, and all eight checkpoints relevant to Tables 1--3 load and execute through the authors' environment code. That materially improves reproducibility, but it does not reproduce the paper.

The paper contains **36 displayed table cells representing 24 unique measurements**, **32 raster-only return series**, and **4 numeric IR labels in Figure 1**. The released notebook has stored values for {len(notebook) - notebook_counts['missing_stored_output']}/36 table cells, but **0 match the paper**; 9 cells have no stored output. Worse, its two stored evaluations of the same PPO and PPO-DeepSeek 10% series disagree on all six corresponding metrics. Three native protocols (stochastic seeds 0 and 42, plus policy means) executed all eight released checkpoints on hash-pinned released CSVs, but no table value earns paper-result credit. Information Ratio remains uncheckable from frozen inputs because the notebook downloads the benchmark live.

## Decisive fidelity gaps

- The paper does not fix evaluation seeds, while the notebook samples Gaussian actions.
- Figures 2--6 visibly start in 2020 despite the stated 2019--2023 trading interval.
- The exact 100-epoch DeepSeek 10% CPPO training lineage is absent. The only committed 0.9--1.1 risk script is an older 25-epoch local-Qwen path; the 100-epoch DeepSeek scripts use smaller weights and unmatched output names.
- The source's CPPO update is not the displayed CVaR-PPO Lagrangian: it applies a clipped per-step value adjustment to GAE, uses alpha=0.85, and repeatedly subtracts its full update buffer during trajectory finalization.
- The one-article-per-stock/day sample, selection seed/IDs, raw selected inputs, LLM responses, frozen Yahoo benchmark, and table-generating result paths are absent.
- The installation script invokes a nonexistent training file; the post-paper risk API script does not parse.

## Honest proximity

This is close to a runnable **artifact-level reconstruction** of the authors' code path and far better than a paper-only release. It is not a faithful result replication: 0/{len(tables)} displayed table cells, 0/{len(figures)} figure series, and 0/{len(figure_metrics)} raster metric labels are reproduced with defensible paper lineage. `--strict` remains nonzero until the pinned original protocol reproduces every claimed result within declared tolerances.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    paper_root = Path(os.environ.get("FINRL_DEEPSEEK_PAPER_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_paper"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(os.environ.get("FINRL_DEEPSEEK_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_source")))
    parser.add_argument("--paper-root", type=Path, default=paper_root)
    parser.add_argument("--artifacts-root", type=Path, default=Path(os.environ.get("FINRL_DEEPSEEK_ARTIFACTS_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_artifacts")))
    parser.add_argument("--output-dir", type=Path, default=project_root / "paper_runs/paper_replication_audits/finrl_deepseek")
    parser.add_argument("--strict", action="store_true", help="Return nonzero until the full paper is reproduced")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(args.source_root, args.paper_root, args.artifacts_root, args.output_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
