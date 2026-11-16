#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Bounded, recorded transport recovery outside the frozen FinAgent experiment."""

from pathlib import Path
import sys
import json
import ast
import re
import argparse
import urllib.request
import socket
import fcntl
import sqlite3
import shutil
import signal
import subprocess
import time
from datetime import datetime, timezone
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256

STUDY = "finagent_native_v1"
MAX_RECOVERY_BATCHES = 4
MAX_ATTEMPT_PER_REQUEST = 2


def transport_leaf(message):
    return message in {
        "TimeoutError: The read operation timed out",
        "urllib.error.URLError: <urlopen error [Errno 101] Network is unreachable>",
    } or any(message.startswith(f"urllib.error.HTTPError: HTTP Error {code}:") for code in [500, 502, 503, 504])


def eligible_failure(lines, unresolved):
    """Recognize a direct transport error or its fully explained two-worker wrapper."""
    last = lines[-1]
    if transport_leaf(last):
        return True
    prefix = "RuntimeError: Validation worker failed; others were allowed to finish: "
    if not last.startswith(prefix):
        return False
    try:
        statuses = ast.literal_eval(last[len(prefix) :])
    except (SyntaxError, ValueError):
        return False
    if (
        not isinstance(statuses, dict)
        or set(statuses) != {"native_causal", "no_retrieval"}
        or any(type(v) is not int or v not in [0, 1] for v in statuses.values())
    ):
        return False
    exceptions = [line for line in lines[:-1] if re.match(r"^[\w.]*(Error|Exception|Interrupt): ", line)]
    leaves, causes = [], []
    for message in exceptions:
        if transport_leaf(message):
            leaves.append(message)
        elif message == "OSError: [Errno 101] Network is unreachable":
            causes.append(message)
        elif (
            message.startswith("RuntimeError: Unresolved previous request: ")
            and message.rsplit(" ", 1)[-1] in unresolved
        ):
            leaves.append(message)
        else:
            return False
    network_leaves = sum(
        m == "urllib.error.URLError: <urlopen error [Errno 101] Network is unreachable>" for m in leaves
    )
    return (
        len(leaves) == sum(statuses.values())
        and any(transport_leaf(m) for m in leaves)
        and len(causes) <= network_leaves
    )


def recover_transport(ledger_root, log, archive, now=None):
    """Caller owns the case execution lock and the failed process has exited."""
    ledger_root, log, archive = map(Path, [ledger_root, log, archive])
    lines = log.read_text(errors="replace").strip().splitlines()
    if not lines:
        raise RuntimeError("An empty log requires inspection")
    last = lines[-1]
    stamp = now or datetime.now(timezone.utc).isoformat()
    with (ledger_root / "project_spend.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger_path = ledger_root / "project_spend.json"
        state = json.loads(ledger_path.read_text())
        selected = {k: v for k, v in state["calls"].items() if v["status"] == "reserved" and v["study"] == STUDY}
        if not selected:
            raise RuntimeError("No unresolved case request to recover")
        if not eligible_failure(lines, set(selected)):
            raise RuntimeError("Failure requires inspection; not an eligible terminal transport error")
        # Persistence failures need reconciliation, never a new paid request.
        journal = ledger_root / "cohort_responses.jsonl"
        if journal.exists():
            with journal.open() as stream:
                for line in stream:
                    if json.loads(line)["request_hash"] in selected:
                        raise RuntimeError("A response exists in the journal; reconcile it instead of retrying")
        with closing(
            sqlite3.connect("file:" + str(ledger_root / "response_cache.sqlite3") + "?mode=ro", uri=True)
        ) as connection:
            for key in selected:
                if connection.execute("SELECT 1 FROM responses WHERE request_hash=?", (key,)).fetchone():
                    raise RuntimeError("A response exists in SQLite; reconcile it instead of retrying")
        mapping_path = ledger_root / "technical_recoveries.json"
        mappings = json.loads(mapping_path.read_text()) if mapping_path.exists() else {}
        records = []
        for key, entry in selected.items():
            old = entry.get("technical_recovery", {})
            original = old.get("original_request_hash", key)
            attempt = old.get("attempt", 0) + 1
            if attempt > MAX_ATTEMPT_PER_REQUEST:
                raise RuntimeError("Per-request recovery bound exhausted")
            if original in mappings and mappings[original]["attempt"] != attempt - 1:
                raise RuntimeError("Recovery mapping is inconsistent; manual reconciliation required")
            cause = (
                "Failed FinAgent process: " + last + "; no durable response found; original reserved charge retained."
            )
            entry.update(status="response_unavailable", reconciliation_reason=cause, reconciled_utc=stamp)
            mappings[original] = {
                "attempt": attempt,
                "cause": cause,
                "recorded_utc": stamp,
                "reserved_usd_retained": entry["reserved_usd"],
            }
            records.append(
                {
                    "failed_request_hash": key,
                    "original_request_hash": original,
                    "new_attempt": attempt,
                    "reserved_usd_retained": entry["reserved_usd"],
                }
            )
        archive.mkdir(parents=True, exist_ok=False)
        shutil.copy2(log, archive / "failed_run.log")
        for filename in ["project_spend.json", "technical_recoveries.json"]:
            if (ledger_root / filename).exists():
                shutil.copy2(ledger_root / filename, archive / ("before_" + filename))
        result = {
            "status": "recovery_recorded",
            "recorded_utc": stamp,
            "terminal_error": last,
            "failed_log_sha256": sha256(log),
            "requests": records,
            "retained_usd": sum(r["reserved_usd_retained"] for r in records),
        }
        atomic_json(archive / "recovery.json", result)
        # If interrupted between these atomic writes, fail closed on the next
        # launch: no reserved entry is erased and no request silently retries.
        atomic_json(ledger_path, state)
        atomic_json(mapping_path, mappings)
    return result


def compare_preserved_prefixes(archive, native):
    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_publication_replay import compare, read

    archive, native = Path(archive), Path(native)
    errors, maximum, lengths = [], [0.0], {}
    for saved in archive.glob("*decisions.jsonl"):
        arm = (
            "shared_training"
            if saved.name == "preserved_decisions.jsonl"
            else saved.name.removesuffix("_decisions.jsonl")
        )
        current_path = (
            native / "decisions.jsonl"
            if arm == "shared_training"
            else native / "validation_arms" / arm / "decisions.jsonl"
        )
        old = read(saved)
        current = read(current_path) if current_path.exists() else []
        overlap = min(len(old), len(current))
        compare(old[:overlap], current[:overlap], path=arm, errors=errors, maximum=maximum)
        lengths[arm] = {"preserved": len(old), "rebuilt": overlap}
    partial = any(v["preserved"] > v["rebuilt"] for v in lengths.values())
    return {
        "status": "fail" if errors else ("partial" if partial else "pass"),
        "lengths": lengths,
        "difference_count": len(errors),
        "differences": errors[:50],
        "maximum_numeric_difference": maximum[0],
    }


def network_preflight(path):
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "endpoint": "https://openrouter.ai/api/v1/models",
        "paid_call": False,
    }
    try:
        with urllib.request.urlopen(result["endpoint"], timeout=15) as response:
            result["http_status"] = response.status
        if result["http_status"] != 200:
            raise RuntimeError("OpenRouter metadata endpoint is not reachable")
        result["status"] = "pass"
    except Exception as exc:
        result.update(status="network_blocked", error_type=type(exc).__name__, error=str(exc))
        atomic_json(path, result)
        raise RuntimeError("Network preflight failed before native execution or new paid calls") from exc
    atomic_json(path, result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--resume-cached",
        action="store_true",
        help="Start from preserved responses without creating another recovery mapping",
    )
    args = parser.parse_args()
    private = ROOT / "artifacts/publication_upgrade_v1"
    log = private / "finagent_run.log"
    completion = private / "finagent_native/completion.json"
    pause = private / "PAUSE_FINAGENT"
    if completion.exists():
        print("CASE_ALREADY_COMPLETE", flush=True)
        return
    if pause.exists():
        raise RuntimeError("An explicit completed-day pause is pending; do not clear it automatically")
    signal.signal(signal.SIGUSR1, lambda *_: pause.touch())
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = private / ("finagent_transport_supervisor_" + run_id)
    root.mkdir(exist_ok=False)
    with (private / "finagent_execution.lock").open("a+") as case_lock:
        fcntl.flock(case_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for batch in range(MAX_RECOVERY_BATCHES):
            network_preflight(private / "network_preflight.json")
            archive = root / f"recovery_{batch}"
            if batch == 0 and args.resume_cached:
                with (ROOT / "runs/economic_fidelity/openrouter/project_spend.lock").open("a+") as ledger_lock:
                    fcntl.flock(ledger_lock, fcntl.LOCK_EX)
                    state = json.loads((ROOT / "runs/economic_fidelity/openrouter/project_spend.json").read_text())
                    if any(v["study"] == STUDY and v["status"] == "reserved" for v in state["calls"].values()):
                        raise RuntimeError("Cached resume cannot bypass an unresolved request")
                archive.mkdir(exist_ok=False)
                shutil.copy2(log, archive / "failed_run.log")
                recovery = {"status": "cached_resume_without_new_recovery", "requests": [], "retained_usd": 0}
                atomic_json(archive / "recovery.json", recovery)
            else:
                recovery = recover_transport(ROOT / "runs/economic_fidelity/openrouter", log, archive)
            original = private / "finagent_native/decisions.jsonl"
            if original.exists():
                shutil.copy2(original, archive / "preserved_decisions.jsonl")
            arms = private / "finagent_native/validation_arms"
            if arms.exists():
                for arm in arms.iterdir():
                    for filename in ["decisions.jsonl", "progress.json", "completion.json"]:
                        if (arm / filename).exists():
                            shutil.copy2(arm / filename, archive / (arm.name + "_" + filename))
            print(
                json.dumps(
                    {
                        "batch": batch,
                        "recovered_requests": len(recovery["requests"]),
                        "retained_usd": recovery["retained_usd"],
                    }
                ),
                flush=True,
            )
            time.sleep(30)
            with log.open("w") as output:
                result = subprocess.run(
                    [
                        str(ROOT / "scripts/run_finmem_fidelity_python.sh"),
                        str(ROOT / "scripts/run_finagent_economic_fidelity.py"),
                    ],
                    cwd=ROOT,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    pass_fds=(case_lock.fileno(),),
                )
            atomic_json(
                root / "status.json",
                {"batch": batch, "exit_code": result.returncode, "native_complete": completion.exists()},
            )
            # Every completed row from the previous attempt must survive exactly.
            sys.path.insert(0, str(ROOT / "scripts"))
            prefix = compare_preserved_prefixes(archive, private / "finagent_native")
            atomic_json(archive / "prefix_validation.json", prefix)
            if prefix["status"] == "fail":
                pause.touch()
                raise RuntimeError("A resumed prefix changed; stop at the completed-day pause")
            if result.returncode == 0:
                if not completion.exists():
                    raise RuntimeError("Driver exited without a completion manifest")
                print("FINAGENT_NATIVE_COMPLETE", flush=True)
                return
            if pause.exists():
                raise RuntimeError("Explicit pause reached")
        raise RuntimeError("Transport recovery batch bound exhausted; inspect the service before resuming")


if __name__ == "__main__":
    main()
