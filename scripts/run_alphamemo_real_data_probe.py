#!/usr/bin/env python3
"""Replay AlphaMemo's released real-data path on a frozen current-data probe.

This is deliberately a component probe, not a paper-result reproduction.  It
uses a small, hash-pinned Yahoo/Qlib panel, the released heuristic generator,
and explicit compatibility shims for two source-release defects.  It never
calls an LLM or a market-data endpoint while replaying the frozen snapshot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SOURCE_COMMIT = "412fee13d905bf5a25f0958aa572b7c668ccb925"
SOURCE_QRUN_SHA256 = "763585181461fa76eb948d0d21643d5bd3b5508f5a88915a6ea0b1a5761f944b"
SOURCE_QLIB_DATA_SHA256 = "88cc1a0461f297cd8765754a7d5f726d39d8043d1cf7ba96bd1fb1552515b4d6"
SOURCE_TEMPLATE_SHA256 = "70cb8bcadf8f818bf846632ab556ecddcf100c4b027f61459287daf14e4ad659"
PROVIDER_FILE_COUNT = 93
PROVIDER_TOTAL_BYTES = 920_339
PROVIDER_MANIFEST_SHA256 = "f3c7a475498dfda4b272053a4f4a96990cd8007911afd7285126e0d4f2c3eecc"
PROVIDER_CALENDAR_SHA256 = "1dc723282cb77f5c7484cdcee736afb36f267256d98f271d2b5cd03787648cfb"
PROVIDER_ALL_INSTRUMENTS_SHA256 = "143a5360c7a9a92480f2f3b2e3632190c44ff00ff7e5f94afd20c351fd66d5fd"
PROVIDER_MARKET_INSTRUMENTS_SHA256 = "51e8f25eb8b7c5df812e126d399af6404d8086626edefe8b4579cc1d56db72ec"
SOURCE_QLIB_MARKET_INSTRUMENTS_SHA256 = (
    "a65cb612d217432e0b8fad217c27b16a40261f62ce350b911d52ce6fa32d182a"
)
ENVIRONMENT_PACKAGE_COUNT = 202
ENVIRONMENT_MANIFEST_SHA256 = "460227814c582c751708bb664f1e7c59effcb7f76b696e8188e88c1518ee9875"
EXPECTED_DIRECT_PACKAGES = {
    "baostock": "0.9.1",
    "lightgbm": "4.6.0",
    "mlflow": "3.12.0",
    "numpy": "2.4.6",
    "pandas": "2.3.3",
    "pyqlib": "0.9.7",
    "pyyaml": "6.0.3",
    "scipy": "1.17.1",
    "yfinance": "1.7.0",
}
EXPECTED_PYTHON = "3.11.11"
EXPECTED_SEARCH_SHA256 = "271f4ef9f8cd72e5fe6950cdb1534123a4d6d80e44b7b50d23872d771e19e893"
EXPECTED_FORMULAS_SHA256 = "43852412d25735e34c609e6cea7476958b66ca2aa87a704f344b6afe22308904"
EXPECTED_METRICS = {
    "1day.excess_return_with_cost.annualized_return": -0.0258044079098057,
    "1day.excess_return_with_cost.information_ratio": -0.241495598241594,
    "1day.excess_return_with_cost.max_drawdown": -0.2562791240173313,
    "1day.excess_return_with_cost.mean": -0.0001084218819739,
    "1day.excess_return_with_cost.std": 0.0069262187025295,
    "1day.excess_return_without_cost.annualized_return": 0.0043657287718227,
    "1day.excess_return_without_cost.information_ratio": 0.0408419539772647,
    "1day.excess_return_without_cost.max_drawdown": -0.1857037589120873,
    "1day.excess_return_without_cost.mean": 1.8343398200936e-05,
    "1day.excess_return_without_cost.std": 0.0069288595924906,
    "1day.ffr": 1.0,
    "1day.pa": 0.0,
    "1day.pos": 0.0,
    "IC": -0.0072836690143443,
    "ICIR": -0.0241113441603328,
    "Rank IC": -0.0065183981444962,
    "Rank ICIR": -0.0215966243629362,
    "l2.train": 0.8930321417678118,
    "l2.valid": 0.9170045298192948,
}
FAILED_FIRST_TWENTY_SYMBOLS = ["ABC", "ABK", "ABMD", "ABS", "ACAS", "ADS"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def file_manifest(root: Path) -> tuple[list[dict[str, Any]], str]:
    rows = []
    canonical = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        digest = sha256(path)
        rows.append({"path": relative, "size_bytes": size, "sha256": digest})
        canonical.append(f"{relative}\t{size}\t{digest}")
    manifest_sha = hashlib.sha256(("\n".join(canonical) + "\n").encode()).hexdigest()
    return rows, manifest_sha


def environment_manifest(python: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    program = r'''
import importlib.metadata as metadata
import json
import sys
rows = sorted(set(
    (item.metadata["Name"].lower().replace("_", "-"), item.version)
    for item in metadata.distributions()
    if item.metadata["Name"]
))
print(json.dumps({"python": sys.version.split()[0], "packages": rows}))
'''
    result = subprocess.run(
        [str(python), "-c", program],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
    )
    payload = json.loads(result.stdout)
    rows = [{"package": name, "version": version} for name, version in payload["packages"]]
    canonical = "\n".join(f"{row['package']}=={row['version']}" for row in rows) + "\n"
    summary = {
        "python": payload["python"],
        "package_count": len(rows),
        "manifest_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "direct_packages": {
            row["package"]: row["version"]
            for row in rows
            if row["package"] in EXPECTED_DIRECT_PACKAGES
        },
    }
    return rows, summary


def copy_source(source_root: Path, destination: Path) -> None:
    shutil.copytree(
        source_root,
        destination,
        ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__", "*.pyc"),
    )


def network_guard(root: Path) -> Path:
    guard = root / "guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        """import json, os, socket\n"
        "_original_connect = socket.socket.connect\n"
        "def _blocked_connect(sock, address):\n"
        "    if sock.family in (socket.AF_INET, socket.AF_INET6):\n"
        "        path = os.environ.get('ALPHAMEMO_NETWORK_LOG')\n"
        "        if path:\n"
        "            with open(path, 'a', encoding='utf-8') as handle:\n"
        "                handle.write(json.dumps({'address': repr(address)}) + '\\n')\n"
        "        raise OSError('network disabled by AlphaMemo audit')\n"
        "    return _original_connect(sock, address)\n"
        "socket.socket.connect = _blocked_connect\n"
        """,
        encoding="utf-8",
    )
    return guard


def run_environment(
    base: dict[str, str],
    source_copy: Path,
    guard: Path,
    runtime_home: Path,
    network_log: Path,
    source_python: Path,
) -> dict[str, str]:
    isolated_home = runtime_home.parent / "original_home"
    isolated_home.mkdir(parents=True, exist_ok=True)
    return {
        **base,
        "HOME": str(isolated_home),
        "PYTHON_BIN": str(source_python),
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": os.pathsep.join([str(guard), str(source_copy)]),
        "QLIB_RUNTIME_HOME": str(runtime_home),
        "ALPHAMEMO_NETWORK_LOG": str(network_log),
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "",
    }


def command(
    source_python: Path,
    provider: Path,
    out_dir: Path,
    qrun: Path | None = None,
) -> list[str]:
    args = [
        str(source_python),
        "-m",
        "sspm",
        "main-table",
        "--preset",
        "paper2025",
        "--strategies",
        "alphamemo",
        "--markets",
        "sp500",
        "--us-provider-uri",
        str(provider),
        "--budget",
        "12",
        "--batch-size",
        "4",
        "--warmup",
        "4",
        "--generator",
        "heuristic",
        "--out-dir",
        str(out_dir),
        "--quiet",
    ]
    if qrun is not None:
        args.extend(["--run-backtest", "--qrun-bin", str(qrun)])
    return args


def run_once(
    *,
    source_python: Path,
    source_copy: Path,
    provider: Path,
    out_dir: Path,
    qrun: Path | None,
    guard: Path,
    network_log: Path,
    runtime_home: Path,
) -> subprocess.CompletedProcess[str]:
    env = run_environment(
        dict(os.environ), source_copy, guard, runtime_home, network_log, source_python
    )
    return subprocess.run(
        command(source_python, provider, out_dir, qrun),
        cwd=source_copy,
        env=env,
        capture_output=True,
        text=True,
    )


def load_metrics(path: Path) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows or len(rows[0]) != 2:
        raise RuntimeError(f"unexpected metric CSV: {path}")
    return {row[0]: float(row[1]) for row in rows[1:]}


def normalized_export(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in ("factor_pickle", "qlib_config", "result_reader"):
        payload.pop(key, None)
    payload["config"]["out_dir"] = "NORMALIZED"
    payload["config"]["run_json"] = "NORMALIZED"
    return payload


def validate_inputs(
    source_root: Path, source_python: Path, provider: Path, qlib_source: Path
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    if git_head(source_root) != SOURCE_COMMIT:
        raise RuntimeError("AlphaMemo source commit changed")
    if sha256(source_root / "scripts/qrun_alphamemo.sh") != SOURCE_QRUN_SHA256:
        raise RuntimeError("AlphaMemo qrun wrapper changed")
    if sha256(source_root / "sspm/evaluation/qlib_data.py") != SOURCE_QLIB_DATA_SHA256:
        raise RuntimeError("AlphaMemo Qlib loader changed")
    if sha256(source_root / "templates/qlib_factor_template/conf_us_combined_kdd_ver.yaml") != SOURCE_TEMPLATE_SHA256:
        raise RuntimeError("AlphaMemo Qlib template changed")

    provider_rows, provider_sha = file_manifest(provider)
    if (
        len(provider_rows) != PROVIDER_FILE_COUNT
        or sum(row["size_bytes"] for row in provider_rows) != PROVIDER_TOTAL_BYTES
        or provider_sha != PROVIDER_MANIFEST_SHA256
    ):
        raise RuntimeError("Frozen AlphaMemo current-data provider changed")
    if sha256(provider / "calendars/day.txt") != PROVIDER_CALENDAR_SHA256:
        raise RuntimeError("Frozen AlphaMemo calendar changed")
    if sha256(provider / "instruments/all.txt") != PROVIDER_ALL_INSTRUMENTS_SHA256:
        raise RuntimeError("Frozen AlphaMemo all-instruments file changed")
    if sha256(provider / "instruments/sp500.txt") != PROVIDER_MARKET_INSTRUMENTS_SHA256:
        raise RuntimeError("Frozen AlphaMemo market-instruments file changed")
    if sha256(qlib_source / "instruments/sp500.txt") != SOURCE_QLIB_MARKET_INSTRUMENTS_SHA256:
        raise RuntimeError("Official Qlib source instrument snapshot changed")

    env_rows, env_summary = environment_manifest(source_python)
    if env_summary != {
        "python": EXPECTED_PYTHON,
        "package_count": ENVIRONMENT_PACKAGE_COUNT,
        "manifest_sha256": ENVIRONMENT_MANIFEST_SHA256,
        "direct_packages": EXPECTED_DIRECT_PACKAGES,
    }:
        raise RuntimeError(f"AlphaMemo paper environment changed: {env_summary}")
    return provider_rows, env_rows, env_summary


def build_probe(
    source_root: Path,
    source_python: Path,
    provider: Path,
    qlib_source: Path,
    work_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    provider_rows, env_rows, env_summary = validate_inputs(
        source_root, source_python, provider, qlib_source
    )
    work_root.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="alphamemo-real-probe-", dir=work_root) as tmp:
        workspace = Path(tmp)
        source_copy = workspace / "source"
        copy_source(source_root, source_copy)
        guard = network_guard(workspace)
        network_log = workspace / "network.jsonl"

        raw_out = workspace / "raw"
        raw = run_once(
            source_python=source_python,
            source_copy=source_copy,
            provider=provider,
            out_dir=raw_out,
            qrun=None,
            guard=guard,
            network_log=network_log,
            runtime_home=workspace / "runtime-raw",
        )
        raw_search = raw_out / "sp500/alphamemo/search.json"
        expected_missing = workspace / "templates/qlib_factor_template/conf_us_combined_kdd_ver.yaml"
        raw_text = raw.stdout + raw.stderr
        if (
            raw.returncode == 0
            or not raw_search.exists()
            or sha256(raw_search) != EXPECTED_SEARCH_SHA256
            or "FileNotFoundError: missing Qlib template config" not in raw_text
            or str(expected_missing) not in raw_text
        ):
            raise RuntimeError(f"Raw AlphaMemo real-data boundary changed:\n{raw_text[-4000:]}")

        compatibility_templates = workspace / "templates"
        compatibility_templates.mkdir()
        (compatibility_templates / "qlib_factor_template").symlink_to(
            source_copy / "templates/qlib_factor_template", target_is_directory=True
        )
        qrun = workspace / "qrun_alphamemo_compat.sh"
        shutil.copyfile(source_copy / "scripts/qrun_alphamemo.sh", qrun)
        qrun.chmod(qrun.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        if sha256(qrun) != SOURCE_QRUN_SHA256:
            raise RuntimeError("Executable qrun compatibility copy changed bytes")

        run_paths = []
        for index in (1, 2):
            run_out = workspace / f"compatible-{index}"
            result = run_once(
                source_python=source_python,
                source_copy=source_copy,
                provider=provider,
                out_dir=run_out,
                qrun=qrun,
                guard=guard,
                network_log=network_log,
                runtime_home=workspace / f"runtime-{index}",
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Compatible AlphaMemo run {index} failed:\n{(result.stdout + result.stderr)[-8000:]}"
                )
            run_paths.append(run_out / "sp500/alphamemo")

        search_hashes = [sha256(path / "search.json") for path in run_paths]
        formula_hashes = [sha256(path / "qlib/selected_formulas.txt") for path in run_paths]
        if search_hashes != [EXPECTED_SEARCH_SHA256, EXPECTED_SEARCH_SHA256]:
            raise RuntimeError(f"AlphaMemo search outputs changed: {search_hashes}")
        if formula_hashes != [EXPECTED_FORMULAS_SHA256, EXPECTED_FORMULAS_SHA256]:
            raise RuntimeError(f"AlphaMemo selected formulas changed: {formula_hashes}")
        if normalized_export(run_paths[0] / "qlib/qlib_export_summary.json") != normalized_export(
            run_paths[1] / "qlib/qlib_export_summary.json"
        ):
            raise RuntimeError("AlphaMemo export semantics are not deterministic")

        search = json.loads((run_paths[0] / "search.json").read_text(encoding="utf-8"))
        export = json.loads(
            (run_paths[0] / "qlib/qlib_export_summary.json").read_text(encoding="utf-8")
        )
        summaries = [
            json.loads((path.parent.parent / "main_table_summary.json").read_text(encoding="utf-8"))[0]
            for path in run_paths
        ]
        metrics = [load_metrics(path / "qlib/qlib_res.csv") for path in run_paths]
        if set(metrics[0]) != set(EXPECTED_METRICS) or set(metrics[1]) != set(EXPECTED_METRICS):
            raise RuntimeError("AlphaMemo metric surface changed")
        max_expected_difference = max(
            abs(metrics[run_index][key] - expected)
            for run_index in (0, 1)
            for key, expected in EXPECTED_METRICS.items()
        )
        max_repeat_difference = max(abs(metrics[0][key] - metrics[1][key]) for key in metrics[0])
        if max_expected_difference > 1e-12 or max_repeat_difference > 1e-12:
            raise RuntimeError(
                "AlphaMemo real-data metrics changed: "
                f"expected={max_expected_difference} repeat={max_repeat_difference}"
            )
        reported_metrics = [
            {key: round(value, 12) for key, value in run.items()} for run in metrics
        ]
        max_reported_repeat_difference = max(
            abs(reported_metrics[0][key] - reported_metrics[1][key])
            for key in reported_metrics[0]
        )

        network_attempts = []
        if network_log.exists():
            network_attempts = [
                json.loads(line) for line in network_log.read_text(encoding="utf-8").splitlines()
            ]
        if network_attempts:
            raise RuntimeError(f"AlphaMemo replay attempted network access: {network_attempts}")

        metric_rows = []
        for key in sorted(reported_metrics[0]):
            metric_rows.append(
                {
                    "metric": key,
                    "run_1": reported_metrics[0][key],
                    "run_2": reported_metrics[1][key],
                    "absolute_difference": abs(
                        reported_metrics[0][key] - reported_metrics[1][key]
                    ),
                    "paper_result_credit": False,
                    "status": "current_input_bounded_heuristic_diagnostic_only",
                }
            )

        stages = [
            {
                "stage": "paper_declared_environment",
                "raw_status": "pass",
                "compatibility_status": "pass",
                "paper_result_credit": False,
                "evidence": "Python 3.11 with exact declared pyqlib, LightGBM, MLflow, and BaoStock pins",
            },
            {
                "stage": "current_yahoo_qlib_builder",
                "raw_status": "pass_frozen_snapshot",
                "compatibility_status": "not_needed",
                "paper_result_credit": False,
                "evidence": "2511 days, 14 source-selected stocks, and one benchmark; six obsolete symbols unavailable",
            },
            {
                "stage": "native_qlib_search",
                "raw_status": "pass_12_of_12_evaluations_zero_admitted",
                "compatibility_status": "pass_twice_byte_identical",
                "paper_result_credit": False,
                "evidence": "released Qlib evaluator and heuristic generator",
            },
            {
                "stage": "native_factor_export",
                "raw_status": "fail_template_root_parents_3",
                "compatibility_status": "pass_twice_12_factors",
                "paper_result_credit": False,
                "evidence": "scratch-only template symlink; pinned source unchanged",
            },
            {
                "stage": "native_qrun_entrypoint",
                "raw_status": "fail_mode_100644",
                "compatibility_status": "pass_byte_identical_executable_copy",
                "paper_result_credit": False,
                "evidence": "scratch-only executable bit repair; pinned source unchanged",
            },
            {
                "stage": "native_lightgbm_portfolio_backtest",
                "raw_status": "unreachable_after_two_release_defects",
                "compatibility_status": "pass_twice_19_metrics_atol_1e-12",
                "paper_result_credit": False,
                "evidence": "training, prediction, portfolio, cost, and metric paths execute offline",
            },
        ]

        payload = {
            "source_commit": SOURCE_COMMIT,
            "source_unmodified": subprocess.run(
                ["git", "status", "--short"],
                cwd=source_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            == "",
            "environment": env_summary,
            "frozen_current_data": {
                "acquisition_date": "2026-08-31",
                "builder": "scripts/build_us_qlib_yfinance.py",
                "builder_limit": 20,
                "requested_start": "2016-01-01",
                "requested_end_exclusive": "2025-12-27",
                "calendar_start": "2016-01-04",
                "calendar_end": "2025-12-26",
                "trading_days": 2511,
                "market_assets": 14,
                "benchmark_series": 1,
                "failed_first_twenty_symbols": FAILED_FIRST_TWENTY_SYMBOLS,
                "provider_file_count": len(provider_rows),
                "provider_total_bytes": sum(row["size_bytes"] for row in provider_rows),
                "provider_manifest_sha256": PROVIDER_MANIFEST_SHA256,
                "official_qlib_source_instrument_rows": 755,
                "official_qlib_source_calendar_end": "2020-11-10",
                "official_qlib_source_market_instruments_sha256": (
                    SOURCE_QLIB_MARKET_INSTRUMENTS_SHA256
                ),
                "paper_time_snapshot": False,
                "point_in_time_2025_membership": False,
            },
            "raw_execution": {
                "returncode": raw.returncode,
                "search_completed": True,
                "search_sha256": sha256(raw_search),
                "first_failure": "missing Qlib template config due SELF_EVO_ROOT=parents[3]",
                "expected_missing_path": (
                    "WORKSPACE/templates/qlib_factor_template/"
                    "conf_us_combined_kdd_ver.yaml"
                ),
                "paper_result_credit": False,
            },
            "compatible_execution": {
                "runs": 2,
                "search_byte_identical": len(set(search_hashes)) == 1,
                "search_sha256": search_hashes[0],
                "selected_formulas_byte_identical": len(set(formula_hashes)) == 1,
                "selected_formulas_sha256": formula_hashes[0],
                "search_summary": search["summary"],
                "n_selected_factors": export["n_selected_factors"],
                "n_dates": export["n_dates"],
                "n_instruments": export["n_instruments"],
                "metric_count": len(metrics[0]),
                "metric_reporting_decimal_places": 12,
                "expected_metrics_atol_1e_12": True,
                "metrics_repeat_atol_1e_12": max_repeat_difference <= 1e-12,
                "max_reported_repeat_difference": max_reported_repeat_difference,
                "network_attempts": network_attempts,
                "llm_calls": 0,
                "template_symlink_compatibility": True,
                "qrun_executable_bit_compatibility": True,
                "source_files_changed": False,
                "paper_configuration": False,
                "paper_result_credit": False,
                "main_table_summaries_have_qlib_metrics": all(
                    "qlib_metrics" in item for item in summaries
                ),
            },
            "paper_result_cells_reproduced": 0,
            "interpretation": (
                "The released current-data builder and native Qlib search/export/LightGBM/portfolio "
                "pipeline execute twice after two explicit scratch-only compatibility repairs. "
                "The bounded heuristic probe uses 14 current-source stocks, admits zero factors at "
                "the released 0.10 threshold, and is not the paper configuration or input snapshot."
            ),
        }

    write_csv(output_dir / "alphamemo_current_data_snapshot.csv", provider_rows)
    write_csv(output_dir / "alphamemo_paper_environment.csv", env_rows)
    write_csv(output_dir / "alphamemo_real_data_metrics.csv", metric_rows)
    write_csv(output_dir / "alphamemo_native_stage_audit.csv", stages)
    (output_dir / "alphamemo_real_data_probe.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-python", type=Path, required=True)
    parser.add_argument("--provider", type=Path, required=True)
    parser.add_argument("--qlib-source", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_probe(
        args.source_root.resolve(),
        args.source_python.absolute(),
        args.provider.resolve(),
        args.qlib_source.resolve(),
        args.work_root.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
