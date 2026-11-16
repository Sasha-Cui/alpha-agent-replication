"""Budget recovery must never retry a durable result or disturb active calls."""

import importlib.util
import json
from pathlib import Path
import sqlite3
import pytest

SPEC = importlib.util.spec_from_file_location(
    "recovery_v2", Path(__file__).parents[1] / "scripts/recover_fidelity_transport_v2.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    monkeypatch.setattr(MODULE.subprocess, "check_output", lambda *a, **kw: "123|FAILED|1:0|\n")
    ledger = tmp_path / "runs/economic_fidelity/openrouter"
    ledger.mkdir(parents=True)
    call = dict(status="reserved", study="selected", pid=1234, reserved_usd=0.1)
    state = dict(
        calls={"failed": call, "active": dict(status="reserved", study="selected", pid=4321, reserved_usd=0.2)},
        imports={},
    )
    (ledger / "project_spend.json").write_text(json.dumps(state))
    with sqlite3.connect(ledger / "response_cache.sqlite3") as db:
        db.execute("CREATE TABLE responses (request_hash TEXT, body TEXT)")
    log = tmp_path / "failed.log"
    log.write_text("http.client.IncompleteRead: IncompleteRead(11 bytes read)\n")
    dirs = [tmp_path / part / "same_name" for part in ["private", "public"]]
    for p in dirs:
        p.mkdir(parents=True)
        (p / "evidence").write_text(str(p))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            dict(
                runs=[
                    dict(
                        name="run",
                        job_id="123",
                        execution_lock=str(tmp_path / "execution.lock"),
                        log=str(log),
                        preserve_directories=list(map(str, dirs)),
                    )
                ],
                requests={"failed": {"pid": 1234, "study": "selected", "reserved_usd": 0.1}},
            )
        )
    )
    return ledger, manifest, state


def test_retains_charge_active_call_and_both_artifact_trees(tmp_path, monkeypatch):
    ledger, manifest, before = fixture(tmp_path, monkeypatch)
    result = MODULE.recover(manifest, tmp_path / "archive")
    after = json.loads((ledger / "project_spend.json").read_text())
    assert after["calls"]["active"] == before["calls"]["active"]
    assert after["calls"]["failed"]["status"] == "response_unavailable"
    assert after["calls"]["failed"]["reserved_usd"] == result["retained_usd"] == 0.1
    assert (tmp_path / "archive/run/private/same_name/evidence").exists()
    assert (tmp_path / "archive/run/public/same_name/evidence").exists()
    assert MODULE.sha256(tmp_path / "archive/executed_recovery_script.py") == result["script_sha256"]
    assert json.loads((ledger / "technical_recoveries.json").read_text())["failed"]["attempt"] == 1


@pytest.mark.parametrize("storage", ["journal", "sqlite"])
def test_durable_response_forbids_retry(tmp_path, monkeypatch, storage):
    ledger, manifest, before = fixture(tmp_path, monkeypatch)
    if storage == "journal":
        (ledger / "cohort_responses.jsonl").write_text(json.dumps({"request_hash": "failed", "response": {}}) + "\n")
    else:
        with sqlite3.connect(ledger / "response_cache.sqlite3") as db:
            db.execute("INSERT INTO responses VALUES (?,?)", ("failed", "{}"))
    with pytest.raises(RuntimeError, match="reconcile instead"):
        MODULE.recover(manifest, tmp_path / "archive")
    assert json.loads((ledger / "project_spend.json").read_text()) == before
    assert not (ledger / "technical_recoveries.json").exists()


def test_running_job_and_nontransport_failure_forbid_retry(tmp_path, monkeypatch):
    ledger, manifest, before = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(MODULE.subprocess, "check_output", lambda *a, **kw: "123|RUNNING|0:0|\n")
    with pytest.raises(RuntimeError, match="terminal failure"):
        MODULE.recover(manifest, tmp_path / "archive")
    monkeypatch.setattr(MODULE.subprocess, "check_output", lambda *a, **kw: "123|FAILED|1:0|\n")
    (tmp_path / "failed.log").write_text("urllib.error.HTTPError: HTTP Error 400: Bad Request\n")
    with pytest.raises(RuntimeError, match="separate diagnosis"):
        MODULE.recover(manifest, tmp_path / "archive")
    assert json.loads((ledger / "project_spend.json").read_text()) == before
