"""Strictly read-only model replay from a frozen ledger index and checked responses."""

from __future__ import annotations
from contextlib import closing
import hashlib
import json
import sqlite3
from pathlib import Path
from alpha_evolve.publication_llm import CohortOpenRouter


class ReadOnlyReplay(CohortOpenRouter):
    def __init__(
        self,
        root,
        key,
        model,
        *,
        study,
        study_cap=25.0,
        project_cap=450.0,
        input_price=2.0,
        output_price=8.0,
        provider="OpenAI",
        offline=True,
    ):
        self.root = Path(root)
        self.key = "unused-read-only"
        self.model = model
        self.study = study
        self.study_cap = study_cap
        self.project_cap = project_cap
        self.input_price = input_price
        self.output_price = output_price
        self.provider = provider
        self.offline = True
        self.request_trace = []
        self.ledger_path = self.root / "project_spend.json"
        self.cache = self.root / "response_cache.sqlite3"
        self.journal = self.root / "cohort_responses.jsonl"
        self.recoveries = self.root / "technical_recoveries.json"
        ledger_bytes = self.ledger_path.read_bytes()
        self.frozen_state = json.loads(ledger_bytes)
        self.recovery_map = json.loads(self.recoveries.read_text()) if self.recoveries.exists() else {}
        self.ledger_sha256 = hashlib.sha256(ledger_bytes).hexdigest()

    def cached_response(self, key):
        entry = self.frozen_state["calls"].get(key)
        if entry is None or entry["status"] != "complete":
            raise RuntimeError("Offline response is not complete in the frozen cache: " + key)
        if "response_journal_offset" in entry:
            with self.journal.open("rb") as stream:
                stream.seek(entry["response_journal_offset"])
                line = stream.readline()
            if hashlib.sha256(line).hexdigest() != entry["response_journal_sha256"]:
                raise ValueError("Response journal checksum mismatch")
            body = json.loads(line)
            if body["request_hash"] != key:
                raise ValueError("Response journal identity mismatch")
            return body
        with closing(sqlite3.connect("file:" + str(self.cache) + "?mode=ro", uri=True, timeout=60)) as connection:
            row = connection.execute("SELECT body FROM responses WHERE request_hash=?", (key,)).fetchone()
        if row is None:
            raise ValueError("Paid response absent from cache")
        return json.loads(row[0])

    def request(self, endpoint, payload, *, input_price=None, output_price=None):
        if endpoint not in ["chat/completions", "embeddings"]:
            raise ValueError("Unsupported replay endpoint")
        body = dict(payload)
        body["provider"] = {"order": [self.provider], "allow_fallbacks": False}
        envelope = {"endpoint": endpoint, "request": body}

        def identity(value):
            return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

        original = identity(envelope)
        if original in self.recovery_map:
            envelope["technical_recovery"] = {
                "original_request_hash": original,
                "attempt": self.recovery_map[original]["attempt"],
            }
        key = identity(envelope)
        cached = self.cached_response(key)
        expected = {k: cached[k] for k in ["endpoint", "request"]}
        if "technical_recovery" in cached:
            expected["technical_recovery"] = cached["technical_recovery"]
        if identity(expected) != key:
            raise ValueError("Cached request hash mismatch")
        self.request_trace.append(
            {"request_hash": key, "endpoint": endpoint, "cached": True, "response_id": cached["response"].get("id")}
        )
        return cached["response"], key

    def snapshot(self):
        project, own = self.totals(self.frozen_state, self.study)
        calls = self.frozen_state["calls"].values()
        return {
            "project_committed_usd": project,
            "study_committed_usd": own,
            "project_soft_cap_usd": self.project_cap,
            "study_cap_usd": self.study_cap,
            "complete_calls": sum(c["status"] == "complete" and c["study"] == self.study for c in calls),
            "uncertain_calls": sum(
                c["status"] != "complete" and c["study"] == self.study for c in self.frozen_state["calls"].values()
            ),
            "read_only_replay": True,
            "frozen_ledger_sha256": self.ledger_sha256,
        }

    def complete(self, *args, **kwargs):
        raise RuntimeError("Read-only replay supports chat and embeddings only")


class LiveCachedMeter(CohortOpenRouter):
    """Reuse verified immutable cached responses quickly; new spend uses normal locks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_cache = ReadOnlyReplay(
            self.root,
            "unused",
            self.model,
            study=self.study,
            study_cap=self.study_cap,
            project_cap=self.project_cap,
            input_price=self.input_price,
            output_price=self.output_price,
            provider=self.provider,
        )
        self.initial_cache.request_trace = self.request_trace

    def request(self, *args, **kwargs):
        try:
            return self.initial_cache.request(*args, **kwargs)
        except RuntimeError as error:
            if not str(error).startswith("Offline response is not complete"):
                raise
        return super().request(*args, **kwargs)

    def snapshot(self):
        # Snapshot reporting does not mutate state. All paid reservations and
        # settlements still pass through the original locked request method.
        state = json.loads(self.ledger_path.read_text())
        project, own = self.totals(state, self.study)
        return {
            "project_committed_usd": project,
            "study_committed_usd": own,
            "project_soft_cap_usd": self.project_cap,
            "study_cap_usd": self.study_cap,
            "complete_calls": sum(
                c["status"] == "complete" and c["study"] == self.study for c in state["calls"].values()
            ),
            "uncertain_calls": sum(
                c["status"] != "complete" and c["study"] == self.study for c in state["calls"].values()
            ),
        }
