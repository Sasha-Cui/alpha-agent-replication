# ruff: noqa: E401, E731 - preserve the committed prospective semantic snapshot
"""Metered chat/embeddings with a durable append journal and legacy SQLite reads.

All requests share the original project ledger/caps. A fsynced response journal
avoids multi-writer SQLite lock loss on the shared filesystem. Explicit technical
recovery mappings retain lost-response reservations and permit one new attempt.
"""

from __future__ import annotations
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import fcntl, hashlib, json, math, os, sqlite3
from pathlib import Path
import urllib.request
from alpha_evolve.openrouter_budget import MeteredOpenRouter


class CohortOpenRouter(MeteredOpenRouter):
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
        offline=False,
    ):
        if not 0 < study_cap <= project_cap <= 450:
            raise ValueError("Invalid spend caps")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.key, self.model, self.study = key, model, study
        self.study_cap, self.project_cap = study_cap, project_cap
        self.input_price, self.output_price = input_price, output_price
        self.ledger_path = self.root / "project_spend.json"
        self.cache = self.root / "response_cache.sqlite3"
        self.journal = self.root / "cohort_responses.jsonl"
        self.recoveries = self.root / "technical_recoveries.json"
        self.provider, self.offline, self.request_trace = provider, offline, []
        if not self.cache.exists():
            with closing(sqlite3.connect(self.cache, timeout=60)) as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS responses (request_hash TEXT PRIMARY KEY,body TEXT NOT NULL)"
                )
                connection.commit()

    @contextmanager
    def ledger(self):
        # Read-only cache hits and snapshots must not rewrite the growing ledger.
        with (self.root / "project_spend.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            before = self.ledger_path.read_bytes() if self.ledger_path.exists() else None
            state = json.loads(before) if before is not None else {"version": 1, "imports": {}, "calls": {}}
            try:
                yield state
            finally:
                try:
                    encoded = (json.dumps(state, indent=2, sort_keys=True) + "\n").encode()
                    if encoded != before:
                        temporary = self.ledger_path.with_suffix(self.ledger_path.suffix + ".tmp")
                        temporary.write_bytes(encoded)
                        os.replace(temporary, self.ledger_path)
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def cached_response(self, key):
        # The ledger is atomically replaced by the inherited locked writer. Avoid
        # acquiring that lock recursively when the caller already holds it.
        state = json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else {"calls": {}}
        entry = state["calls"].get(key, {})
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
        with closing(sqlite3.connect(self.cache, timeout=60)) as connection:
            row = connection.execute("SELECT body FROM responses WHERE request_hash=?", (key,)).fetchone()
        if row is None:
            raise ValueError("Paid response missing from durable cache")
        return json.loads(row[0])

    def _save_journal(self, key, envelope, response):
        encoded = (json.dumps({"request_hash": key, **envelope, "response": response}, sort_keys=True) + "\n").encode()
        with (self.root / "cohort_response_journal.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                with self.journal.open("ab") as stream:
                    offset = stream.tell()
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
        return offset, hashlib.sha256(encoded).hexdigest()

    def request(self, endpoint, payload, *, input_price=None, output_price=None):
        if endpoint not in {"chat/completions", "embeddings"}:
            raise ValueError("Unsupported paid endpoint")
        body = dict(payload)
        body["provider"] = {"order": [self.provider], "allow_fallbacks": False}
        envelope = {"endpoint": endpoint, "request": body}
        identity = lambda e: hashlib.sha256(json.dumps(e, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        original_key = identity(envelope)
        recoveries = json.loads(self.recoveries.read_text()) if self.recoveries.exists() else {}
        if original_key in recoveries:
            envelope["technical_recovery"] = {
                "original_request_hash": original_key,
                "attempt": recoveries[original_key]["attempt"],
            }
        key = identity(envelope)
        encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        ip = self.input_price if input_price is None else input_price
        op = self.output_price if output_price is None else output_price
        reservation = (len(encoded) * ip + int(body.get("max_tokens", 0)) * op) / 1e6
        if not math.isfinite(reservation) or reservation <= 0:
            raise ValueError("Invalid request reservation")
        with self.ledger() as state:
            if key in state["calls"]:
                if state["calls"][key]["status"] != "complete":
                    raise RuntimeError("Unresolved previous request: " + key)
                cached = self.cached_response(key)
                expected = {k: cached[k] for k in ["endpoint", "request"]}
                if "technical_recovery" in cached:
                    expected["technical_recovery"] = cached["technical_recovery"]
                if identity(expected) != key:
                    raise ValueError("Cache hash mismatch")
                self.request_trace.append(
                    {
                        "request_hash": key,
                        "endpoint": endpoint,
                        "cached": True,
                        "response_id": cached["response"].get("id"),
                    }
                )
                return cached["response"], key
            if self.offline:
                raise RuntimeError("Offline request is absent from cache: " + key)
            project, own = self.totals(state, self.study)
            if project + reservation >= self.project_cap or own + reservation >= self.study_cap:
                raise RuntimeError("Budget exhausted before network call")
            state["calls"][key] = {
                "status": "reserved",
                "study": self.study,
                "model": body["model"],
                "endpoint": endpoint,
                "reserved_usd": reservation,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "pid": os.getpid(),
            }
            if "technical_recovery" in envelope:
                state["calls"][key]["technical_recovery"] = envelope["technical_recovery"]
        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/" + endpoint,
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "Authorization": "Bearer " + self.key,
                "Content-Type": "application/json",
                "X-OpenRouter-Title": "Alpha Agent Replication publication upgrade",
            },
        )
        with urllib.request.urlopen(request, timeout=180) as result:
            response = json.loads(result.read())
        if (
            response.get("error")
            or (endpoint == "embeddings" and not response.get("data"))
            or (endpoint == "chat/completions" and not response.get("choices"))
        ):
            raise RuntimeError("Provider returned no usable result; reservation retained")
        # Durability precedes accounting/parsing; a later failure can be reconciled.
        offset, digest = self._save_journal(key, envelope, response)
        usage = response.get("usage", {})
        cost = usage.get("cost")
        cost_source = "provider_usage"
        if not isinstance(cost, (float, int)) or not math.isfinite(cost) or cost < 0:
            tokens = usage.get("prompt_tokens", len(encoded))
            completion = usage.get("completion_tokens", int(body.get("max_tokens", 0)))
            if not isinstance(tokens, (int, float)) or not math.isfinite(tokens) or tokens < 0:
                tokens = len(encoded)
            if not isinstance(completion, (int, float)) or not math.isfinite(completion) or completion < 0:
                completion = int(body.get("max_tokens", 0))
            cost = (tokens * ip + completion * op) / 1e6
            cost_source = "tariff_upper_bound"
        with self.ledger() as state:
            state["calls"][key].update(
                status="complete",
                cost_usd=float(cost),
                cost_source=cost_source,
                response_id=response.get("id"),
                response_model=response.get("model"),
                provider=response.get("provider"),
                usage=usage,
                response_journal_offset=offset,
                response_journal_sha256=digest,
            )
        self.request_trace.append(
            {"request_hash": key, "endpoint": endpoint, "cached": False, "response_id": response.get("id")}
        )
        if cost > reservation + 1e-9:
            raise RuntimeError("Reported price exceeded reservation; response cached and actual cost recorded")
        return response, key

    def chat(self, messages, *, max_tokens=2048, temperature=0.7, model=None, **parameters):
        return self.request(
            "chat/completions",
            {
                "model": model or self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **parameters,
            },
        )

    def embeddings(self, texts, *, model="openai/text-embedding-ada-002", price_per_million=0.1):
        return self.request(
            "embeddings",
            {"model": model, "input": texts, "encoding_format": "float"},
            input_price=price_per_million,
            output_price=0,
        )


def canonical_meter(
    root: Path, key: str, *, model: str, study: str, cap: float, input_price: float, output_price: float, offline=False
):
    return CohortOpenRouter(
        root / "runs/economic_fidelity/openrouter",
        key,
        model,
        study=study,
        study_cap=cap,
        input_price=input_price,
        output_price=output_price,
        offline=offline,
    )
