#!/usr/bin/env python3
# ruff: noqa: E402 - standalone audit tool
"""Explicit terminal-job transport recovery; preserve lost-response charges."""

from pathlib import Path
from contextlib import ExitStack, closing
from datetime import datetime, timezone
import argparse
import fcntl
import json
import re
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256


def terminal_transport(line):
    return line in {
        "http.client.RemoteDisconnected: Remote end closed connection without response",
        "TimeoutError: The read operation timed out",
    } or bool(re.fullmatch(r"http\.client\.IncompleteRead: IncompleteRead\(\d+ bytes read\)", line))


def recover(manifest_path, archive):
    spec = json.loads(manifest_path.read_text())
    ledger_root = ROOT / "runs/economic_fidelity/openrouter"
    # Scientific cases may share a meter. Every selected key is explicit; jobs
    # in the same meter that are still running are never selected implicitly.
    with ExitStack() as stack:
        for row in spec["runs"]:
            lock = stack.enter_context(Path(row["execution_lock"]).open("a+"))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.check_output(
                ["/opt/slurm/current/bin/sacct", "-X", "-n", "-P", "-j", row["job_id"], "-o", "JobID,State,ExitCode"],
                text=True,
            )
            records = [r.split("|") for r in result.splitlines()]
            if not any(r[:3] == [row["job_id"], "FAILED", "1:0"] for r in records):
                raise RuntimeError("Job is not a verified terminal failure: " + row["job_id"])
            line = Path(row["log"]).read_text(errors="replace").strip().splitlines()[-1]
            if not terminal_transport(line):
                raise RuntimeError("Failure needs separate diagnosis: " + line)
            row["terminal_error"] = line
        keys = set(spec["requests"])
        lock = stack.enter_context((ledger_root / "project_spend.lock").open("a+"))
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads((ledger_root / "project_spend.json").read_text())
        mappings_path = ledger_root / "technical_recoveries.json"
        mappings = json.loads(mappings_path.read_text()) if mappings_path.exists() else {}
        for key, expected in spec["requests"].items():
            entry = state["calls"][key]
            if entry["status"] != "reserved" or any(entry.get(k) != v for k, v in expected.items()):
                raise RuntimeError("Reservation identity/status changed: " + key)
        # A late durable response is a reconciliation case, never a paid retry.
        journal_lock = stack.enter_context((ledger_root / "cohort_response_journal.lock").open("a+"))
        fcntl.flock(journal_lock, fcntl.LOCK_EX)
        journal = ledger_root / "cohort_responses.jsonl"
        if journal.exists():
            needles = [k.encode() for k in keys]
            with journal.open("rb") as stream:
                for line in stream:
                    if any(k in line for k in needles) and json.loads(line)["request_hash"] in keys:
                        raise RuntimeError("Response found in journal; reconcile instead")
        with closing(
            sqlite3.connect("file:" + str(ledger_root / "response_cache.sqlite3") + "?mode=ro", uri=True)
        ) as connection:
            for key in keys:
                if connection.execute("SELECT 1 FROM responses WHERE request_hash=?", (key,)).fetchone():
                    raise RuntimeError("Response found in SQLite; reconcile instead")
        stamp = datetime.now(timezone.utc).isoformat()
        records = []
        for key in sorted(keys):
            entry = state["calls"][key]
            old = entry.get("technical_recovery", {})
            original = old.get("original_request_hash", key)
            attempt = old.get("attempt", 0) + 1
            if attempt > 2 or (original in mappings and mappings[original]["attempt"] != attempt - 1):
                raise RuntimeError("Bounded recovery mapping exhausted/inconsistent")
            cause = "Confirmed terminal v2 transport failure; no durable response. Entire original reservation retained; exact request body unchanged."
            entry.update(status="response_unavailable", reconciliation_reason=cause, reconciled_utc=stamp)
            mappings[original] = dict(
                attempt=attempt, cause=cause, recorded_utc=stamp, reserved_usd_retained=entry["reserved_usd"]
            )
            records.append(
                dict(
                    failed_request_hash=key,
                    original_request_hash=original,
                    new_attempt=attempt,
                    reserved_usd_retained=entry["reserved_usd"],
                    pid=entry["pid"],
                    study=entry["study"],
                )
            )
        archive.mkdir(parents=True, exist_ok=False)
        shutil.copy2(manifest_path, archive / "request_manifest.json")
        shutil.copy2(Path(__file__), archive / "executed_recovery_script.py")
        for row in spec["runs"]:
            dest = archive / row["name"]
            dest.mkdir()
            shutil.copy2(row["log"], dest / "failed_run.log")
            for directory in row["preserve_directories"]:
                source = Path(directory)
                target = dest / source.relative_to(ROOT)
                shutil.copytree(source, target)
        for filename in ["project_spend.json", "technical_recoveries.json"]:
            if (ledger_root / filename).exists():
                shutil.copy2(ledger_root / filename, archive / ("before_" + filename))
        record = dict(
            status="recovery_recorded",
            recorded_utc=stamp,
            runs=spec["runs"],
            requests=records,
            retained_usd=sum(r["reserved_usd_retained"] for r in records),
            script_sha256=sha256(Path(__file__)),
        )
        atomic_json(archive / "recovery.json", record)
        # Same fail-closed ordering as original recovery supervisor.
        atomic_json(ledger_root / "project_spend.json", state)
        atomic_json(mappings_path, mappings)
    return record


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--archive", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(recover(args.manifest, args.archive), indent=2))


if __name__ == "__main__":
    main()
