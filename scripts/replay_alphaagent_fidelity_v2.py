#!/usr/bin/env python3
# ruff: noqa: E402 - native driver bootstrap
"""Full read-only AlphaAgent rerun, retaining all financial and model identities."""

from pathlib import Path
import sys
import argparse
import importlib.util
import fcntl
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.fidelity_transport_v2 import retry_stale_read
from validate_publication_replay import compare

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", choices=["source_gpt4turbo", "paper_gpt35"], required=True)
    args = parser.parse_args()
    original = PRIVATE / ("alphaagent_" + args.trial)
    replay = PRIVATE / ("alphaagent_" + args.trial + "_offline_replay")
    reference = json.loads((original / "execution_exit.json").read_text())
    if reference["completed_trajectories"] != 5 or reference["finished_stages"] != 25:
        raise ValueError("Original source run did not complete five full loops")
    if (replay / "execution_exit.json").exists():
        raise ValueError("Preserve completed replay")
    driver_path = ROOT / "scripts/run_alphaagent_fidelity_v2.py"
    spec = importlib.util.spec_from_file_location("native_alphaagent_replay_driver", driver_path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)

    class LockedReadOnlyReplay(ReadOnlyReplay):
        def __init__(self, root, *a, **kw):
            def initialize():
                with (Path(root) / "project_spend.lock").open("a+") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    super(LockedReadOnlyReplay, self).__init__(root, *a, **kw)

            retry_stale_read(initialize)

    driver.ReadOnlyReplay = LockedReadOnlyReplay
    sys.argv = [str(driver_path), "--offline", "--trial", args.trial, "--output-name", replay.name]
    driver.main()
    errors = []
    maximum = [0.0]
    proofs = {}
    for name in ["model_calls.json", "embedding_calls.json", "trajectories.json", "stages.json"]:
        left = json.loads((original / name).read_text())
        right = json.loads((replay / name).read_text())
        if name == "trajectories.json":

            def project(rows):
                return [{k: v for k, v in row.items() if k not in ["workspace", "factor_workspaces"]} for row in rows]

            left, right = project(left), project(right)
        elif name == "stages.json":
            left = [{k: v for k, v in row.items() if k != "started_utc"} for row in left]
            right = [{k: v for k, v in row.items() if k != "started_utc"} for row in right]
        compare(left, right, name, errors, maximum)
        proofs[name] = {"original_sha256": sha256(original / name), "replay_sha256": sha256(replay / name)}
    result = {
        "status": "pass" if not errors else "fail",
        "trial": args.trial,
        "trajectories": 5,
        "maximum_numeric_difference": maximum[0],
        "differences": errors[:50],
        "difference_count": len(errors),
        "artifact_hashes": proofs,
        "network_calls": 0,
        "ledger_mutations": 0,
        "ignored": "Only workspace path provenance and stage wall-clock timestamps. All factor definitions, feedback, hypotheses, backtest metrics, source stage sequence, chat/embedding request identities and response identities are compared.",
        "replay_driver_sha256": sha256(Path(__file__)),
        "executed_native_wrapper_sha256": sha256(driver_path),
        "full_original_paper_reproduced": False,
    }
    atomic_json(original / "full_replay_validation.json", result)
    print(json.dumps(result), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
