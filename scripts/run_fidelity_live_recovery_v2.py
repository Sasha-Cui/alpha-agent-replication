#!/usr/bin/env python3
# ruff: noqa: E402 - isolated v2 transport wrapper
"""Run approved v2 drivers with bounded transport recovery, preserving source code."""

from pathlib import Path
import argparse
import json
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.fidelity_live_recovery_v2 import RecoveringLiveMeter
import alpha_evolve.publication_llm as publication_llm


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--driver", choices=["run_efs_fidelity_v2.py", "run_tradingagents_news_sources_repair_v2.py"], required=True
    )
    p.add_argument("--audit-name", required=True)
    p.add_argument("arguments", nargs=argparse.REMAINDER)
    args = p.parse_args()
    if not args.audit_name.replace("_", "").isalnum():
        raise ValueError("Invalid audit name")
    arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    if "--offline" in arguments:
        raise ValueError("Use existing strict replay driver for offline validation")
    driver = ROOT / "scripts" / args.driver
    out = ROOT / "artifacts/fidelity_completion_v2/live_transport_adapters" / args.audit_name
    out.mkdir(parents=True, exist_ok=True)
    record = {
        "driver": args.driver,
        "driver_sha256": sha256(driver),
        "wrapper_sha256": sha256(Path(__file__)),
        "helper_sha256": sha256(ROOT / "src/alpha_evolve/fidelity_live_recovery_v2.py"),
        "arguments": arguments,
        "scope": "Retry only this process own confirmed terminated TimeoutError/RemoteDisconnected/IncompleteRead attempts, after exact-key ownership and both durable-store checks. Preserve all charges, identical HTTP bodies and the existing maximum2technical attempts per original key. No HTTP4xx, parsing or strategy retry. Fast verified cache reuse is inherited from existing LockedLiveMeter.",
        "event_directory": "runs/economic_fidelity/openrouter/live_transport_recovery_events",
    }
    path = out / "execution.json"
    if path.exists() and json.loads(path.read_text()) != record:
        raise ValueError("Preserve prior transport wrapper provenance")
    atomic_json(path, record)
    publication_llm.CohortOpenRouter = RecoveringLiveMeter
    sys.argv = [str(driver), *arguments]
    runpy.run_path(str(driver), run_name="__main__")


if __name__ == "__main__":
    main()
