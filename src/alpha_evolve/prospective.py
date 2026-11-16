# ruff: noqa: E401, E731 - preserve the committed prospective semantic snapshot
"""Local protocol seals and append-only prospective forecast/outcome records.

A local seal is not a public preregistration or a trusted external timestamp.
Human review and external registration are tracked separately and never inferred.
"""

from __future__ import annotations
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl, hashlib, json, os
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def utc_now():
    return datetime.now(timezone.utc)


def timestamp(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone-aware timestamps required")
    return result.astimezone(timezone.utc)


def code_digest(path):
    tree = ast.parse(Path(path).read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body.pop(0)
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()


@contextmanager
def locked(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / "run.lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def read_chain(path):
    path = Path(path)
    rows = []
    previous = None
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        row = json.loads(line)
        expected = digest({k: v for k, v in row.items() if k != "sha256"})
        if row["sha256"] != expected or row["previous_sha256"] != previous or row["sequence"] != len(rows) + 1:
            raise ValueError("Record chain integrity failure")
        rows.append(row)
        previous = row["sha256"]
    return rows


def append_chain(path, payload):
    path = Path(path)
    rows = read_chain(path)
    row = {"sequence": len(rows) + 1, "previous_sha256": rows[-1]["sha256"] if rows else None, "payload": payload}
    row["sha256"] = digest(row)
    with path.open("ab") as stream:
        stream.write(canonical(row) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return row


def ensure_seal(root, protocol, code_paths, clock=utc_now):
    root = Path(root)
    path = root / "seal.json"
    hashes = {str(Path(p).resolve()): code_digest(p) for p in code_paths}
    if path.exists():
        seal = json.loads(path.read_text())
        if seal["protocol"] != protocol or seal["semantic_code_sha256"] != hashes:
            raise ValueError("Protocol/code changed after seal; preserve this study and create a declared new version")
        return seal
    seal = {
        "created_at_utc": clock().isoformat(),
        "protocol": protocol,
        "semantic_code_sha256": hashes,
        "independent_human_review_complete": False,
        "externally_registered": False,
        "confirmatory_claim_eligible": False,
        "registration_type": "local prospective development-pilot seal",
    }
    seal["sha256"] = digest(seal)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(canonical(seal) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return seal


def commit_forecast(root, seal, forecast, clock=utc_now):
    now = clock()
    execution = timestamp(forecast["execution_at_utc"])
    evaluation = timestamp(forecast["evaluation_at_utc"])
    available = timestamp(forecast["maximum_input_available_at_utc"])
    if now < timestamp(seal["created_at_utc"]) or not available <= now < execution < evaluation:
        raise ValueError(
            "Forecast must be recorded after sealing and before future execution/evaluation; inputs must already be available"
        )
    rows = read_chain(Path(root) / "forecasts.jsonl")
    if any(row["payload"]["execution_at_utc"] == forecast["execution_at_utc"] for row in rows):
        raise ValueError("A forecast for this execution already exists; no replacement or reselection")
    payload = {
        **forecast,
        "recorded_at_utc": now.isoformat(),
        "seal_sha256": seal["sha256"],
        "status": "committed_before_execution",
    }
    return append_chain(Path(root) / "forecasts.jsonl", payload)


def commit_outcome(root, forecast_record, outcome, clock=utc_now):
    now = clock()
    evaluation = timestamp(forecast_record["payload"]["evaluation_at_utc"])
    if (
        now < evaluation
        or timestamp(outcome["observed_at_utc"]) < evaluation
        or timestamp(outcome["observed_at_utc"]) > now
    ):
        raise ValueError("Future outcome is not observable yet")
    known = read_chain(Path(root) / "forecasts.jsonl")
    if forecast_record["sha256"] not in {r["sha256"] for r in known}:
        raise ValueError("Unknown forecast")
    records = read_chain(Path(root) / "outcomes.jsonl")
    if any(r["payload"]["forecast_sha256"] == forecast_record["sha256"] for r in records):
        raise ValueError("Outcome already recorded; historical observations cannot be replaced")
    return append_chain(
        Path(root) / "outcomes.jsonl",
        {**outcome, "forecast_sha256": forecast_record["sha256"], "recorded_at_utc": now.isoformat()},
    )
