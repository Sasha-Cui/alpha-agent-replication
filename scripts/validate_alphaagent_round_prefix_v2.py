#!/usr/bin/env python3
# ruff: noqa: E402 - local validator bootstrap
"""Verify the corrected five-round replay against the recorded source attempt prefix."""

from pathlib import Path
import sys
import json
import argparse

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from validate_publication_replay import compare

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trial", choices=["source_gpt4turbo", "paper_gpt35"], required=True)
    args = p.parse_args()
    original = PRIVATE / ("alphaagent_bounded_" + args.trial + "_01")
    replay = PRIVATE / ("alphaagent_rounds_" + args.trial + "_01")
    result = json.loads((replay / "execution_exit.json").read_text())
    if result["status"] != "native_round_budget_exhausted" or result["attempted_rounds"] != 5:
        raise ValueError("Corrected replay did not complete five attempted rounds")
    errors = []
    maximum = [0.0]
    hashes = {}
    for name in ["model_calls.json", "embedding_calls.json"]:
        old = json.loads((original / name).read_text())
        new = json.loads((replay / name).read_text())
        compare(old[: len(new)], new, name, errors, maximum)
        hashes[name] = {
            "original": sha256(original / name),
            "replay": sha256(replay / name),
            "retained_events": len(new),
            "original_events": len(old),
        }
    old_events = json.loads((original / "stages.json").read_text())
    old_history = json.loads((original / "trajectories.json").read_text())
    rounds = [row["loop_index"] for row in old_events if row["stage"] == "feedback" and row.get("completed")]
    expected = [row for number, row in zip(rounds, old_history) if number < 5]
    actual = json.loads((replay / "trajectories.json").read_text())

    def financial(rows):
        return [
            {key: value for key, value in row.items() if key not in ["workspace", "factor_workspaces"]} for row in rows
        ]

    compare(financial(expected), financial(actual), "source_first_five_rounds", errors, maximum)
    record = {
        "status": "pass" if not errors else "fail",
        "scope": "Complete cached replay of the first five attempted source rounds, including failed rounds; later accidental proposals/rounds are not represented as part of the five-round study. All original costs/artifacts remain.",
        "trial": args.trial,
        "successful_trajectories": len(actual),
        "failed_round_indices": result["failed_round_indices"],
        "maximum_numeric_difference": maximum[0],
        "difference_count": len(errors),
        "differences": errors[:50],
        "request_hashes": hashes,
        "network_calls": 0,
        "ignored": "Only workspace-path provenance; no financial, factor, hypothesis, feedback, model or embedding identity is normalized away.",
        "script_sha256": sha256(Path(__file__)),
    }
    atomic_json(replay / "full_replay_validation.json", record)
    print(json.dumps(record), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
