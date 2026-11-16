"""Bounded same-process recovery of a confirmed failed HTTP attempt only.

No parsing, strategy or HTTP4xx retries. Missing-response charges remain committed.
The canonical ledger/cache and the existing two-attempt technical limit apply.
"""

import copy
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone

from alpha_evolve.fidelity_transport_v2 import LockedLiveMeter
from alpha_evolve.openrouter_budget import atomic_json


def identity(envelope):
    return hashlib.sha256(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class RecoveringLiveMeter(LockedLiveMeter):
    max_technical_attempt = 2
    retry_delay_seconds = 2

    def __init__(self, *args, **kwargs):
        self._executed_helper_source = Path(__file__).read_bytes()
        self._executed_helper_sha256 = hashlib.sha256(self._executed_helper_source).hexdigest()
        super().__init__(*args, **kwargs)

    def record_failed_attempt(self, endpoint, payload, error):
        body = dict(payload)
        body["provider"] = {"order": [self.provider], "allow_fallbacks": False}
        envelope = {"endpoint": endpoint, "request": body}
        original = identity(envelope)
        root = Path(self.root)
        with (root / "project_spend.lock").open("a+") as ledger_lock:
            fcntl.flock(ledger_lock, fcntl.LOCK_EX)
            state = json.loads(self.ledger_path.read_text())
            path = root / "technical_recoveries.json"
            mappings = json.loads(path.read_text()) if path.exists() else {}
            attempt = mappings.get(original, {}).get("attempt", 0)
            if attempt:
                envelope["technical_recovery"] = {"original_request_hash": original, "attempt": attempt}
            key = identity(envelope)
            entry = state["calls"].get(key, {})
            if entry.get("status") != "reserved" or entry.get("pid") != os.getpid() or entry.get("study") != self.study:
                raise RuntimeError("Failed-attempt ownership/state changed; manual reconciliation required")
            with (root / "cohort_response_journal.lock").open("a+") as journal_lock:
                fcntl.flock(journal_lock, fcntl.LOCK_EX)
                if self.journal.exists():
                    needle = key.encode()
                    with self.journal.open("rb") as stream:
                        for line in stream:
                            if needle in line and json.loads(line)["request_hash"] == key:
                                raise RuntimeError("Durable response exists; reconcile instead of retrying")
                with closing(sqlite3.connect("file:" + str(self.cache) + "?mode=ro", uri=True)) as connection:
                    if connection.execute("SELECT 1 FROM responses WHERE request_hash=?", (key,)).fetchone():
                        raise RuntimeError("Durable response exists; reconcile instead of retrying")
                stamp = datetime.now(timezone.utc).isoformat()
                allowed = attempt < self.max_technical_attempt
                cause = (
                    "Own synchronous HTTP attempt terminated with "
                    + type(error).__name__
                    + "; no durable response. Original charge retained; identical HTTP body only."
                )
                out = root / "live_transport_recovery_events" / key
                out.mkdir(parents=True, exist_ok=False)
                record = {
                    "status": "retry_authorized" if allowed else "technical_bound_exhausted",
                    "created_utc": stamp,
                    "failed_request_hash": key,
                    "original_request_hash": original,
                    "failed_attempt": attempt,
                    "next_attempt": attempt + 1 if allowed else None,
                    "study": self.study,
                    "pid": os.getpid(),
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "retained_usd": entry["reserved_usd"],
                    "request_envelope": envelope,
                    "helper_sha256": self._executed_helper_sha256,
                    "other_requests_reconciled": 0,
                }
                atomic_json(out / "event.json", record)
                (out / "executed_helper.py").write_bytes(self._executed_helper_source)
                entry.update(status="response_unavailable", reconciliation_reason=cause, reconciled_utc=stamp)
                if allowed:
                    mappings[original] = {
                        "attempt": attempt + 1,
                        "cause": cause,
                        "recorded_utc": stamp,
                        "reserved_usd_retained": entry["reserved_usd"],
                    }
                # Crash between these writes fails closed; no reservation is erased.
                atomic_json(self.ledger_path, state)
                atomic_json(path, mappings)
        if not allowed:
            raise RuntimeError("Per-request technical recovery bound exhausted") from error
        return record

    def request(self, endpoint, payload, **kwargs):
        frozen = copy.deepcopy(payload)
        while True:
            try:
                return super().request(endpoint, frozen, **kwargs)
            except (TimeoutError, http.client.RemoteDisconnected, http.client.IncompleteRead) as error:
                if self.offline:
                    raise
                self.record_failed_attempt(endpoint, frozen, error)
                time.sleep(self.retry_delay_seconds)
