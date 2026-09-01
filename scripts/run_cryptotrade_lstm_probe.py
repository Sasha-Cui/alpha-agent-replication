#!/usr/bin/env python3
"""Execute CryptoTrade's released ETH LSTM over fixed seed/look-back grids.

The released baseline file is not directly runnable: it requires an unused
plotting dependency, hard-codes an unavailable ``cuda:7`` device, omits the
required ``dataset`` argument, and does not expose metrics as a return value.
This driver applies only those four declared compatibility/instrumentation
changes in memory.  It never edits the pinned source, calls an LLM, or accesses
the network.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SOURCE_COMMIT = "210da73af5f17992be425e61305524a5c24dae40"
SOURCE_HASHES = {
    "README.md": "af3e98ec66435814f195919abc1b0c6523b7aec02b93e10878c53de3159ade80",
    "run_baseline.py": "9baf6e13ce4c504d7dee0bfe3fa14d5e953b3276cd43cc11b91cb862243e606e",
    "eth_env.py": "a05443b96d6e86b13ee33adf1c5d6a16dac9195de6857a3e9c2916cf0c393f3f",
    "data/eth_daily.csv": "d227fde2a131bea1508f5049da80611982dbae73256570eeb6bb3a1d28729339",
}
COMPATIBLE_ENVIRONMENT = {
    "python": "3.10.8",
    "torch": "2.4.1+cpu",
    "numpy": "2.1.1",
    "pandas": "2.2.3",
    "scikit_learn": "1.5.2",
    "torch_cuda_available": False,
}
PAPER_DECLARED_TORCH = "2.3.0"
LOOKBACKS = (1, 3, 5, 10, 20, 30)
PAPER_PERIODS = {
    "bear": ("2023-04-12", "2023-06-16"),
    "sideways": ("2023-06-20", "2023-08-31"),
    "bull": ("2023-10-01", "2023-12-01"),
}
VALIDATION_PERIODS = {"validation": ("2023-01-13", "2023-03-12")}
PAPER_VALUES = {
    "bear": {
        "total_return_pct": -13.22,
        "daily_return_mean_pct": -0.19,
        "daily_return_std_pct": 2.36,
        "sharpe_ratio": -0.08,
    },
    "sideways": {
        "total_return_pct": 1.27,
        "daily_return_mean_pct": 0.02,
        "daily_return_std_pct": 1.11,
        "sharpe_ratio": 0.15,
    },
    "bull": {
        "total_return_pct": 22.12,
        "daily_return_mean_pct": 0.36,
        "daily_return_std_pct": 2.59,
        "sharpe_ratio": 0.14,
    },
}
DISPLAY_TOLERANCE = 0.005 + 1e-12
METRICS = tuple(next(iter(PAPER_VALUES.values())))


WORKER_PROGRAM = r'''
from __future__ import annotations

import argparse
import io
import json
import socket
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import torch


parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--seed", type=int, required=True)
parser.add_argument("--repeat", type=int, required=True)
parser.add_argument("--lookback", type=int, required=True)
parser.add_argument("--periods-json", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.source))

network_attempts = []
original_connect = socket.socket.connect


def blocked_connect(sock, address):
    if sock.family in (socket.AF_INET, socket.AF_INET6):
        network_attempts.append(repr(address))
        raise OSError("network disabled by CryptoTrade LSTM audit")
    return original_connect(sock, address)


socket.socket.connect = blocked_connect
text = (args.source / "run_baseline.py").read_text(encoding="utf-8")
if text.count("device = 'cuda:7'") != 1:
    raise RuntimeError("CUDA compatibility anchor changed")
if text.count("import matplotlib.pyplot as plt\n") != 1:
    raise RuntimeError("matplotlib compatibility anchor changed")
namespace_anchor = "Namespace(starting_date=sargs['starting_date'], ending_date=sargs['ending_date'])"
if text.count(namespace_anchor) != 1:
    raise RuntimeError("dataset compatibility anchor changed")
text = text.split("strategy = 'optimal'", 1)[0]
text = text.replace("device = 'cuda:7'", "device = 'cpu'")
text = text.replace("import matplotlib.pyplot as plt\n", "")
text = text.replace(
    namespace_anchor,
    "Namespace(starting_date=sargs['starting_date'], "
    "ending_date=sargs['ending_date'], dataset='eth')",
)
return_anchor = "    print(result_str)\n"
if text.count(return_anchor) != 1:
    raise RuntimeError("metric-return instrumentation anchor changed")
text = text.replace(
    return_anchor,
    return_anchor
    + "    return {'total_return_pct': total_irr * 100, "
    + "'daily_return_mean_pct': irr_mean, 'daily_return_std_pct': irr_std, "
    + "'sharpe_ratio': result['sharp_ratio']}\n",
)
namespace = {"__name__": "cryptotrade_lstm_probe"}
with redirect_stdout(io.StringIO()):
    exec(compile(text, "run_baseline.py", "exec"), namespace)

periods = json.loads(args.periods_json)
rows = []
for regime, (start, end) in periods.items():
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    actions = []
    original_lstm = namespace["lstm_strategy"]

    def wrapped_lstm(df, start_date, end_date, look_back=5):
        del look_back
        action = original_lstm(df, start_date, end_date, args.lookback)
        actions.append(action)
        return action

    namespace["lstm_strategy"] = wrapped_lstm
    try:
        with redirect_stdout(io.StringIO()):
            metrics = namespace["run_strategy"](
                "LSTM", {"starting_date": start, "ending_date": end}
            )
    finally:
        namespace["lstm_strategy"] = original_lstm
    rows.append(
        {
            "seed": args.seed,
            "repeat": args.repeat,
            "lookback": args.lookback,
            "regime": regime,
            "start": start,
            "end": end,
            "steps": len(actions),
            "actions": actions,
            "action_counts": {name: actions.count(name) for name in sorted(set(actions))},
            "metrics": metrics,
        }
    )
if network_attempts:
    raise RuntimeError(f"unexpected network attempts: {network_attempts}")
args.output.write_text(json.dumps(rows, sort_keys=True) + "\n", encoding="utf-8")
'''


@dataclass(frozen=True)
class Job:
    seed: int
    repeat: int
    lookback: int


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def validate_source(source: Path) -> None:
    if git_head(source) != SOURCE_COMMIT:
        raise RuntimeError("CryptoTrade source commit changed")
    for relative, expected in SOURCE_HASHES.items():
        observed = sha256(source / relative)
        if observed != expected:
            raise RuntimeError(f"CryptoTrade source changed: {relative}={observed}")


def environment_snapshot(wrapper: Path) -> dict[str, Any]:
    program = (
        "import json,sys,numpy,pandas,sklearn,torch;"
        "print(json.dumps({'python':sys.version.split()[0],'torch':torch.__version__,"
        "'numpy':numpy.__version__,'pandas':pandas.__version__,"
        "'scikit_learn':sklearn.__version__,"
        "'torch_cuda_available':torch.cuda.is_available()},sort_keys=True))"
    )
    result = subprocess.run(
        [str(wrapper), "-c", program],
        check=True,
        capture_output=True,
        text=True,
        env=clean_environment(),
    )
    snapshot = json.loads(result.stdout)
    if snapshot != COMPATIBLE_ENVIRONMENT:
        raise RuntimeError(f"CryptoTrade compatible environment changed: {snapshot}")
    return snapshot


def clean_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in (
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONUSERBASE",
        "VIRTUAL_ENV",
        "_OLD_VIRTUAL_PATH",
        "__PYVENV_LAUNCHER__",
    ):
        environment.pop(key, None)
    environment.update(
        {
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "ALL_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "",
        }
    )
    return environment


def run_jobs(
    source: Path,
    wrapper: Path,
    work_root: Path,
    workers: int,
    jobs: Iterable[Job],
    periods: dict[str, tuple[str, str]],
) -> list[dict[str, Any]]:
    jobs = list(jobs)
    with tempfile.TemporaryDirectory(prefix="cryptotrade-lstm-", dir=work_root) as tmp:
        root = Path(tmp)
        worker = root / "worker.py"
        worker.write_text(WORKER_PROGRAM, encoding="utf-8")
        environment = clean_environment()
        periods_json = json.dumps(periods, sort_keys=True)

        def run(job: Job) -> list[dict[str, Any]]:
            path = root / f"{job.seed}-{job.repeat}-{job.lookback}.json"
            result = subprocess.run(
                [
                    str(wrapper),
                    str(worker),
                    "--source",
                    str(source),
                    "--seed",
                    str(job.seed),
                    "--repeat",
                    str(job.repeat),
                    "--lookback",
                    str(job.lookback),
                    "--periods-json",
                    periods_json,
                    "--output",
                    str(path),
                ],
                cwd=source,
                env=environment,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(
                    f"CryptoTrade LSTM job {job} failed:\n"
                    f"{(result.stdout + result.stderr)[-8000:]}"
                )
            return json.loads(path.read_text(encoding="utf-8"))

        rows = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for result in executor.map(run, jobs):
                rows.extend(result)
    return sorted(
        rows,
        key=lambda row: (row["seed"], row["repeat"], row["lookback"], row["regime"]),
    )


def action_sha256(actions: list[str]) -> str:
    return hashlib.sha256(("\n".join(actions) + "\n").encode()).hexdigest()


def paper_cell_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for run in runs:
        for metric, paper_value in PAPER_VALUES[run["regime"]].items():
            value = run["metrics"][metric]
            rows.append(
                {
                    "seed": run["seed"],
                    "repeat": run["repeat"],
                    "lookback": run["lookback"],
                    "regime": run["regime"],
                    "metric": metric,
                    "paper_value": paper_value,
                    "recomputed_value": round(value, 12),
                    "absolute_error": round(abs(value - paper_value), 12),
                    "display_match": abs(value - paper_value) <= DISPLAY_TOLERANCE,
                    "action_sha256": action_sha256(run["actions"]),
                    "action_counts": json.dumps(run["action_counts"], sort_keys=True),
                }
            )
    return rows


def fixed_mode(
    source: Path,
    wrapper: Path,
    output: Path,
    work_root: Path,
    workers: int,
    seeds: list[int],
    repeats: int,
) -> None:
    jobs = [Job(seed, repeat, 5) for seed in seeds for repeat in range(repeats)]
    runs = run_jobs(source, wrapper, work_root, workers, jobs, PAPER_PERIODS)
    cells = paper_cell_rows(runs)
    summary = []
    for regime in PAPER_VALUES:
        for metric, paper_value in PAPER_VALUES[regime].items():
            subset = [row for row in cells if row["regime"] == regime and row["metric"] == metric]
            summary.append(
                {
                    "regime": regime,
                    "metric": metric,
                    "paper_value": paper_value,
                    "observations": len(subset),
                    "matches": sum(row["display_match"] for row in subset),
                    "all_seeds_and_repeats_match": all(row["display_match"] for row in subset),
                    "unique_recomputed_values": len({row["recomputed_value"] for row in subset}),
                    "min_recomputed_value": min(row["recomputed_value"] for row in subset),
                    "max_recomputed_value": max(row["recomputed_value"] for row in subset),
                    "unique_action_paths": len({row["action_sha256"] for row in subset}),
                }
            )
    repeat_groups = {}
    for run in runs:
        key = (run["seed"], run["lookback"], run["regime"])
        normalized = {k: v for k, v in run.items() if k != "repeat"}
        repeat_groups.setdefault(key, []).append(normalized)
    payload = {
        "source_commit": SOURCE_COMMIT,
        "mode": "fixed_source_default_lookback",
        "seeds": seeds,
        "repeats_per_seed": repeats,
        "lookback": 5,
        "regimes": list(PAPER_PERIODS),
        "native_runs": len(jobs),
        "regime_runs": len(runs),
        "cell_observations": len(cells),
        "repeat_groups": len(repeat_groups),
        "repeat_exact_groups": sum(len({json.dumps(item, sort_keys=True) for item in values}) == 1 for values in repeat_groups.values()),
        "source_default_stable_matching_cells": sum(row["all_seeds_and_repeats_match"] for row in summary),
        "any_matching_cells": sum(row["matches"] > 0 for row in summary),
        "summary": summary,
    }
    write_csv(output / "cryptotrade_lstm_cell_census.csv", cells)
    write_csv(output / "cryptotrade_lstm_cell_summary.csv", summary)
    (output / "cryptotrade_lstm_probe.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def validation_mode(
    source: Path,
    wrapper: Path,
    output: Path,
    work_root: Path,
    workers: int,
    seeds: list[int],
    repeats: int,
) -> None:
    jobs = [
        Job(seed, repeat, lookback)
        for seed in seeds
        for repeat in range(repeats)
        for lookback in LOOKBACKS
    ]
    runs = run_jobs(source, wrapper, work_root, workers, jobs, VALIDATION_PERIODS)
    rows = []
    for run in runs:
        rows.append(
            {
                "seed": run["seed"],
                "repeat": run["repeat"],
                "lookback": run["lookback"],
                **{metric: round(run["metrics"][metric], 12) for metric in METRICS},
                "steps": run["steps"],
                "action_sha256": action_sha256(run["actions"]),
                "action_counts": json.dumps(run["action_counts"], sort_keys=True),
            }
        )
    selections = []
    for seed in seeds:
        subset = [row for row in rows if row["seed"] == seed and row["repeat"] == 0]
        best_return = max(row["total_return_pct"] for row in subset)
        best_sharpe = max(row["sharpe_ratio"] for row in subset)
        selections.append(
            {
                "seed": seed,
                "return_selected": [
                    row["lookback"] for row in subset if row["total_return_pct"] == best_return
                ],
                "sharpe_selected": [
                    row["lookback"] for row in subset if row["sharpe_ratio"] == best_sharpe
                ],
            }
        )
    repeat_groups = {}
    for row in rows:
        key = (row["seed"], row["lookback"])
        normalized = {k: v for k, v in row.items() if k != "repeat"}
        repeat_groups.setdefault(key, []).append(normalized)
    payload = {
        "source_commit": SOURCE_COMMIT,
        "mode": "paper_validation_lookback_grid",
        "seeds": seeds,
        "repeats_per_seed": repeats,
        "lookbacks": list(LOOKBACKS),
        "validation_period": list(VALIDATION_PERIODS["validation"]),
        "grid_runs": len(jobs),
        "repeat_groups": len(repeat_groups),
        "repeat_exact_groups": sum(len({json.dumps(item, sort_keys=True) for item in values}) == 1 for values in repeat_groups.values()),
        "selection_criterion_in_paper": "best performance (metric unspecified)",
        "return_selected_distribution": dict(
            Counter(str(value) for row in selections for value in row["return_selected"])
        ),
        "sharpe_selected_distribution": dict(
            Counter(str(value) for row in selections for value in row["sharpe_selected"])
        ),
        "all_lookbacks_tie_for_every_seed": all(
            row["return_selected"] == list(LOOKBACKS)
            and row["sharpe_selected"] == list(LOOKBACKS)
            for row in selections
        ),
        "selections": selections,
    }
    write_csv(output / "cryptotrade_lstm_validation_grid.csv", rows)
    (output / "cryptotrade_lstm_validation_selection.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def paper_grid_mode(
    source: Path,
    wrapper: Path,
    output: Path,
    work_root: Path,
    workers: int,
    seeds: list[int],
    suffix: str,
) -> None:
    jobs = [Job(seed, 0, lookback) for seed in seeds for lookback in LOOKBACKS]
    runs = run_jobs(source, wrapper, work_root, workers, jobs, PAPER_PERIODS)
    cells = paper_cell_rows(runs)
    summary = []
    for regime in PAPER_VALUES:
        for metric, paper_value in PAPER_VALUES[regime].items():
            subset = [row for row in cells if row["regime"] == regime and row["metric"] == metric]
            summary.append(
                {
                    "regime": regime,
                    "metric": metric,
                    "paper_value": paper_value,
                    "observations": len(subset),
                    "matches": sum(row["display_match"] for row in subset),
                    "all_seeds_and_lookbacks_match": all(row["display_match"] for row in subset),
                    "matching_seeds_by_lookback": json.dumps(
                        {
                            str(lookback): sum(
                                row["display_match"]
                                for row in subset
                                if row["lookback"] == lookback
                            )
                            for lookback in LOOKBACKS
                        },
                        sort_keys=True,
                    ),
                    "unique_recomputed_values": len({row["recomputed_value"] for row in subset}),
                    "min_recomputed_value": min(row["recomputed_value"] for row in subset),
                    "max_recomputed_value": max(row["recomputed_value"] for row in subset),
                    "unique_action_paths": len({row["action_sha256"] for row in subset}),
                    "protocol_robust_paper_result_credit": all(
                        row["display_match"] for row in subset
                    ),
                }
            )
    marker = f"_{suffix}" if suffix else ""
    payload = {
        "source_commit": SOURCE_COMMIT,
        "mode": "paper_seed_lookback_grid",
        "seeds": seeds,
        "lookbacks": list(LOOKBACKS),
        "regimes": list(PAPER_PERIODS),
        "native_seed_lookback_runs": len(jobs),
        "regime_runs": len(runs),
        "cell_observations": len(cells),
        "protocol_robust_matching_cells": sum(
            row["protocol_robust_paper_result_credit"] for row in summary
        ),
        "any_matching_cells": sum(row["matches"] > 0 for row in summary),
        "summary": summary,
    }
    write_csv(output / f"cryptotrade_lstm_paper_grid{marker}.csv", cells)
    (output / f"cryptotrade_lstm_paper_grid{marker}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--python-wrapper", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("fixed", "validation", "paper-grid"), required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(10)))
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--suffix", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    wrapper = args.python_wrapper.absolute()
    output = args.output_dir.resolve()
    work_root = args.work_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work_root.mkdir(parents=True, exist_ok=True)
    validate_source(source)
    environment = environment_snapshot(wrapper)
    if args.mode == "fixed":
        fixed_mode(source, wrapper, output, work_root, args.workers, args.seeds, args.repeats)
    elif args.mode == "validation":
        validation_mode(source, wrapper, output, work_root, args.workers, args.seeds, args.repeats)
    else:
        paper_grid_mode(source, wrapper, output, work_root, args.workers, args.seeds, args.suffix)
    metadata = {
        "source_commit": SOURCE_COMMIT,
        "compatible_environment": environment,
        "paper_declared_torch": PAPER_DECLARED_TORCH,
        "exact_declared_runtime_reproduced": False,
        "source_compatibility": {
            "removed_unused_matplotlib_import": True,
            "cuda7_to_cpu": True,
            "added_required_dataset_eth": True,
            "return_only_instrumentation": True,
            "pinned_source_modified": False,
        },
        "network_attempts": 0,
        "llm_calls": 0,
    }
    (output / "cryptotrade_lstm_runtime.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
