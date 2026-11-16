#!/usr/bin/env python3
# ruff: noqa: E402 - pinned source bootstrap
"""Strict source QuantaAlpha replay with recorded nonfinancial lineage identities."""

from pathlib import Path
import sys
import json
import argparse
import importlib.util
import fcntl
import os

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/fidelity_completion_v2/dependencies/quantaalpha_b7ceb27"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(SOURCE)]
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.fidelity_transport_v2 import retry_stale_read
from alpha_evolve.openrouter_budget import sha256, atomic_json
from validate_publication_replay import compare

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-name", default="quantaalpha_bounded")
    args = parser.parse_args()
    original = PRIVATE / args.original_name
    replay = PRIVATE / (args.original_name + "_offline_replay")
    if not (original / "execution_exit.json").exists():
        raise ValueError("Original run incomplete")
    if (replay / "execution_exit.json").exists():
        raise ValueError("Preserve completed replay")
    pool = json.loads((original / "log/trajectory_pool.json").read_text())
    identities = {(row["direction_id"], row["round_idx"], row["phase"]): row for row in pool["trajectories"].values()}
    replay.mkdir(parents=True, exist_ok=True)
    data = json.loads((PRIVATE / "quantaalpha_data/manifest.json").read_text())
    os.environ.update(
        DATA_RESULTS_DIR=str(replay / "results"),
        QLIB_DATA_DIR=data["provider_path"],
        FACTOR_CoSTEER_data_folder=str(PRIVATE / "bounded_factor_inputs/quantaalpha/search"),
        FACTOR_CoSTEER_data_folder_debug=str(PRIVATE / "bounded_factor_inputs/quantaalpha/debug"),
        FACTOR_CoSTEER_python_bin=sys.executable,
        OPENAI_API_KEY="unused-read-only-replay",
    )
    os.chdir(replay)
    from quantaalpha.pipeline.evolution.trajectory import StrategyTrajectory

    native_init = StrategyTrajectory.__init__

    def init(self, *a, **kw):
        native_init(self, *a, **kw)
        if self.trajectory_id in pool["trajectories"]:
            self.created_at = pool["trajectories"][self.trajectory_id]["created_at"]

    def identifier(direction_id, round_idx, phase, timestamp=None):
        key = (direction_id, round_idx, phase.value)
        if key not in identities:
            raise RuntimeError("Unexpected source evolution task")
        return identities[key]["trajectory_id"]

    StrategyTrajectory.__init__ = init
    StrategyTrajectory.generate_id = staticmethod(identifier)
    path = ROOT / "scripts/run_quantaalpha_bounded_v2.py"
    spec = importlib.util.spec_from_file_location("quanta_native_replay", path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)

    class LockedReplay(ReadOnlyReplay):
        def __init__(self, root, *a, **kw):
            def initialize():
                with (Path(root) / "project_spend.lock").open("a+") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    super(LockedReplay, self).__init__(root, *a, **kw)

            retry_stale_read(initialize)

    driver.ReadOnlyReplay = LockedReplay
    sys.argv = [
        str(path),
        "--offline",
        "--output-name",
        replay.name,
        "--resume-prefix",
        str(original / "model_calls.json"),
    ]
    driver.main()
    differences = []
    maximum = [0.0]
    hashes = {}
    for filename in [
        "model_calls.json",
        "embedding_calls.json",
        "log/evolution_state.json",
        "log/trajectory_pool.json",
    ]:
        left = json.loads((original / filename).read_text())
        right = json.loads((replay / filename).read_text())
        if filename.endswith("trajectory_pool.json"):
            left.pop("saved_at", None)
            right.pop("saved_at", None)
        compare(left, right, filename, differences, maximum)
        hashes[filename] = {"original": sha256(original / filename), "replay": sha256(replay / filename)}
    result = {
        "status": "pass" if not differences else "fail",
        "difference_count": len(differences),
        "differences": differences[:50],
        "maximum_numeric_difference": maximum[0],
        "trajectories": len(pool["trajectories"]),
        "artifact_hashes": hashes,
        "network_calls": 0,
        "ledger_mutations": 0,
        "metadata_rule": "Replay original timestamp-derived trajectory IDs and creation timestamps so parent references/order remain identical. Ignore only pool save time; no financial, hypothesis, factor, feedback, request or lineage field is normalized away.",
        "replay_script_sha256": sha256(Path(__file__)),
    }
    atomic_json(original / "full_replay_validation.json", result)
    print(json.dumps(result), flush=True)
    if differences:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
