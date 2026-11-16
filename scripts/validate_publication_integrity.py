#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Recheck frozen EFS and prospective commitments using their sealed Python runtime."""

from pathlib import Path
import json
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.prospective import code_digest, digest, read_chain, timestamp


def main():
    if sys.version_info[:2] != (3, 10):
        raise RuntimeError("Use run_finmem_fidelity_python.sh: the original AST seal uses Python 3.10")
    private = ROOT / "artifacts/publication_upgrade_v1"
    recipe = json.loads((ROOT / "paper_runs/economic_fidelity/efs_v1/recipe.json").read_text())
    changed_efs = [name for name, value in recipe["implementation_sha256"].items() if sha256(ROOT / name) != value]
    forward = private / "prospective_efs_v1"
    seal = json.loads((forward / "seal.json").read_text())
    changed_semantics = [name for name, value in seal["semantic_code_sha256"].items() if code_digest(name) != value]
    errors = []
    if seal["sha256"] != digest({k: v for k, v in seal.items() if k != "sha256"}):
        errors.append("Prospective seal checksum changed")
    if seal["sha256"] != "bca17550a990fb9b9b636d8fa14927c229026d617041972c21449f76477b020d":
        errors.append("Prospective seal differs from the communicated commitment")
    forecasts = read_chain(forward / "forecasts.jsonl")
    outcomes = read_chain(forward / "outcomes.jsonl")
    expected = "34b9c4fcbf349c1f04fff4ff6b81a64bdb2a1aa0f4a1e9a2531887241db77c53"
    if not forecasts or forecasts[0]["sha256"] != expected:
        errors.append("First prospective forecast differs from the communicated commitment")
    for row in forecasts:
        payload = row["payload"]
        if (
            not timestamp(payload["recorded_at_utc"])
            < timestamp(payload["execution_at_utc"])
            < timestamp(payload["evaluation_at_utc"])
        ):
            errors.append("Prospective forecast clock order failed")
    now = datetime.now(timezone.utc)
    for row in outcomes:
        payload = row["payload"]
        matching = [forecast for forecast in forecasts if forecast["sha256"] == payload["forecast_sha256"]]
        if len(matching) != 1:
            errors.append("Prospective outcome references an unknown forecast")
            continue
        evaluation = timestamp(matching[0]["payload"]["evaluation_at_utc"])
        observed = timestamp(payload["observed_at_utc"])
        recorded = timestamp(payload["recorded_at_utc"])
        if not evaluation <= observed <= recorded <= now:
            errors.append("Prospective outcome clock order failed")
    record = {
        "status": "pass" if not changed_efs and not changed_semantics and not errors else "fail",
        "checked_at_utc": now.isoformat(),
        "checker_python": sys.version.split()[0],
        "frozen_efs_code_changes": changed_efs,
        "sealed_semantic_changes": changed_semantics,
        "committed_forecasts": len(forecasts),
        "observed_future_outcomes": len(outcomes),
        "forecast_sha256": expected,
        "errors": errors,
    }
    atomic_json(private / "frozen_evidence_integrity.json", record)
    print(json.dumps(record))
    if record["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
