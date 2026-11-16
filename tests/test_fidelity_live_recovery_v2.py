import http.client
import json
import urllib.error
import urllib.request
import pytest
from alpha_evolve.fidelity_live_recovery_v2 import RecoveringLiveMeter


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(
            {"choices": [{"message": {"content": "ok"}}], "usage": {"cost": 0.000001}, "id": "valid_response"}
        ).encode()


def meter(tmp_path):
    (tmp_path / "project_spend.json").write_text(json.dumps({"version": 1, "imports": {}, "calls": {}}))
    m = RecoveringLiveMeter(
        tmp_path, "unused-test-key", "model", study="test", study_cap=1, input_price=1, output_price=1
    )
    m.retry_delay_seconds = 0
    return m


def test_retry_preserves_body_charge_and_other_pending_calls(tmp_path, monkeypatch):
    m = meter(tmp_path)
    with m.ledger() as state:
        state["calls"]["unrelated"] = {"status": "reserved", "study": "test", "pid": -1, "reserved_usd": 0.1}
    bodies = []

    def network(request, **kwargs):
        bodies.append(request.data)
        if len(bodies) == 1:
            raise http.client.IncompleteRead(b"partial")
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", network)
    response, key = m.chat([{"role": "user", "content": "fixed hypothesis"}], max_tokens=10)
    state = json.loads(m.ledger_path.read_text())
    assert response["id"] == "valid_response" and bodies[0] == bodies[1]
    assert state["calls"][key]["status"] == "complete"
    failed = [v for v in state["calls"].values() if v["status"] == "response_unavailable"]
    assert len(failed) == 1 and failed[0]["reserved_usd"] > 0
    assert state["calls"]["unrelated"] == {"status": "reserved", "study": "test", "pid": -1, "reserved_usd": 0.1}
    assert m.totals(state, "test")[0] == pytest.approx(0.1 + failed[0]["reserved_usd"] + 0.000001)
    assert len(m.request_trace) == 1


def test_same_original_request_cannot_exceed_two_recoveries(tmp_path, monkeypatch):
    m = meter(tmp_path)
    calls = []

    def network(*args, **kwargs):
        calls.append(1)
        raise TimeoutError("client read timed out")

    monkeypatch.setattr(urllib.request, "urlopen", network)
    with pytest.raises(RuntimeError, match="bound exhausted"):
        m.chat([{"role": "user", "content": "fixed"}], max_tokens=10)
    state = json.loads(m.ledger_path.read_text())
    assert len(calls) == 3 and len(state["calls"]) == 3
    assert all(v["status"] == "response_unavailable" and v["reserved_usd"] > 0 for v in state["calls"].values())


def test_http400_never_gets_an_automatic_retry(tmp_path, monkeypatch):
    m = meter(tmp_path)
    calls = []

    def network(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError("https://openrouter.ai", 400, "Bad Request", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", network)
    with pytest.raises(urllib.error.HTTPError):
        m.chat([{"role": "user", "content": "bad input"}], max_tokens=10)
    assert len(calls) == 1 and not (tmp_path / "technical_recoveries.json").exists()


def test_durable_journal_response_blocks_retry(tmp_path, monkeypatch):
    m = meter(tmp_path)
    calls = []

    def network(*args, **kwargs):
        calls.append(1)
        key = next(iter(json.loads(m.ledger_path.read_text())["calls"]))
        m.journal.write_text(json.dumps({"request_hash": key, "response": {"id": "durable"}}) + "\n")
        raise http.client.IncompleteRead(b"partial")

    monkeypatch.setattr(urllib.request, "urlopen", network)
    with pytest.raises(RuntimeError, match="Durable response exists"):
        m.chat([{"role": "user", "content": "fixed"}], max_tokens=10)
    assert len(calls) == 1 and not (tmp_path / "technical_recoveries.json").exists()


def test_durable_sqlite_response_blocks_retry(tmp_path, monkeypatch):
    import sqlite3

    m = meter(tmp_path)
    calls = []

    def network(*args, **kwargs):
        calls.append(1)
        key = next(iter(json.loads(m.ledger_path.read_text())["calls"]))
        with sqlite3.connect(m.cache) as connection:
            connection.execute("INSERT INTO responses VALUES (?,?)", (key, "{}"))
        raise http.client.RemoteDisconnected("closed")

    monkeypatch.setattr(urllib.request, "urlopen", network)
    with pytest.raises(RuntimeError, match="Durable response exists"):
        m.chat([{"role": "user", "content": "fixed"}], max_tokens=10)
    assert len(calls) == 1 and not (tmp_path / "technical_recoveries.json").exists()


def test_retry_still_obeys_shared_budget(tmp_path, monkeypatch):
    m = meter(tmp_path)
    calls = []

    def network(*args, **kwargs):
        calls.append(1)
        with m.ledger() as state:
            charge = next(iter(state["calls"].values()))["reserved_usd"]
            state["calls"]["other_completed"] = {
                "status": "complete",
                "study": "test",
                "pid": -1,
                "reserved_usd": 1 - charge - 1e-9,
                "cost_usd": 1 - charge - 1e-9,
            }
        raise TimeoutError("client read timed out")

    monkeypatch.setattr(urllib.request, "urlopen", network)
    with pytest.raises(RuntimeError, match="Budget exhausted before network call"):
        m.chat([{"role": "user", "content": "fixed"}], max_tokens=10)
    assert len(calls) == 1
