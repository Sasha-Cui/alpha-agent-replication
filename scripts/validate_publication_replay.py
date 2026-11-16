#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Compare source execution to complete cached replay without ignoring economic fields."""

from pathlib import Path
import sys
import argparse
import json
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256

PRIVATE = ROOT / "artifacts/publication_upgrade_v1"


def read(path):
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines()]
    return json.loads(path.read_text())


def compare(left, right, path="", errors=None, maximum=None):
    errors = [] if errors is None else errors
    maximum = [0.0] if maximum is None else maximum
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            errors.append(path + ": keys differ")
            return errors, maximum
        for key in left:
            if key == "requests":

                def project(rows):
                    return sorted((r["endpoint"], r["request_hash"], r.get("response_id") or "") for r in rows)

                if project(left[key]) != project(right[key]):
                    errors.append(path + ".requests: identity differs")
            else:
                compare(left[key], right[key], path + "." + key, errors, maximum)
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            errors.append(path + ": length differs")
            return errors, maximum
        for i, (a, b) in enumerate(zip(left, right)):
            compare(a, b, path + f"[{i}]", errors, maximum)
    elif isinstance(left, (float, int)) and not isinstance(left, bool) and isinstance(right, (float, int)):
        difference = abs(left - right)
        if not math.isfinite(difference) or difference > 1e-10:
            errors.append(path + ": numerical difference")
        if math.isfinite(difference):
            maximum[0] = max(maximum[0], difference)
    elif left != right:
        errors.append(path + ": value differs")
    return errors, maximum


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", choices=["finmem", "finagent", "tradingagents"], required=True)
    p.add_argument("--replay-name")
    args = p.parse_args()
    name = args.case
    if name == "tradingagents" and not args.replay_name:
        paths = [PRIVATE / f"tradingagents_shard_{a}_{b}/decisions.json" for a, b in [(0, 15), (15, 31), (31, 61)]]
        original = []
        for path in paths:
            original.extend(read(path))
        replay_path = PRIVATE / "tradingagents_native/decisions.json"
        replayed = read(replay_path)
        original = sorted(original, key=lambda row: row["date"])
        replayed = sorted(replayed, key=lambda row: row["date"])
        input_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in paths}
    else:
        extension = "json" if name == "tradingagents" else "jsonl"
        original_path = PRIVATE / (name + "_native") / ("decisions." + extension)
        replay_path = PRIVATE / (args.replay_name or name + "_offline_replay") / ("decisions." + extension)
        original = read(original_path)
        replayed = read(replay_path)
        input_hashes = {str(original_path.relative_to(ROOT)): sha256(original_path)}
    errors, maximum = compare(original, replayed)
    result = {
        "status": "pass" if not errors else "fail",
        "case": name,
        "records": len(original),
        "replay_records": len(replayed),
        "maximum_numeric_difference": maximum[0],
        "differences": errors[:50],
        "difference_count": len(errors),
        "source_sha256": input_hashes,
        "replay_sha256": sha256(replay_path),
        "ignored": "Only cached-status flags and ordering of independent transport request events; request hashes/response IDs and all economic, timing, reasoning and memory fields remain compared.",
    }
    atomic_json(PRIVATE / (name + "_full_replay_validation.json"), result)
    print(json.dumps({k: v for k, v in result.items() if k not in ["source_sha256", "ignored", "differences"]}))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
