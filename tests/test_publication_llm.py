import json
import sqlite3
import hashlib
import pytest
from alpha_evolve.publication_llm import CohortOpenRouter


def test_offline_miss_never_reserves_or_calls(tmp_path):
    client = CohortOpenRouter(tmp_path, "unused", "openai/gpt-4o", study="test", offline=True)
    with pytest.raises(RuntimeError, match="Offline"):
        client.chat([{"role": "user", "content": "x"}])
    state = json.loads(client.ledger_path.read_text())
    assert state["calls"] == {}


def test_embedding_cache_uses_endpoint_qualified_identity(tmp_path):
    client = CohortOpenRouter(tmp_path, "unused", "openai/gpt-4o", study="test", offline=True)
    body = {
        "model": "openai/text-embedding-ada-002",
        "input": ["x"],
        "encoding_format": "float",
        "provider": {"order": ["OpenAI"], "allow_fallbacks": False},
    }
    envelope = {"endpoint": "embeddings", "request": body}
    key = hashlib.sha256(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    response = {"data": [{"index": 0, "embedding": [0.1, 0.2]}], "usage": {"prompt_tokens": 1}}
    with sqlite3.connect(client.cache) as c:
        c.execute("INSERT INTO responses VALUES (?,?)", (key, json.dumps({**envelope, "response": response})))
    with client.ledger() as state:
        state["calls"][key] = {"status": "complete", "study": "test", "cost_usd": 0.0000001, "reserved_usd": 0.001}
    result, actual = client.embeddings(["x"])
    assert actual == key and result == response
    assert client.snapshot()["study_committed_usd"] == 0.0000001


def test_provider_cost_exceeding_bound_is_cached_and_charged(tmp_path, monkeypatch):
    import io
    import urllib.request

    response = {
        "id": "expensive",
        "model": "openai/gpt-4o",
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"cost": 1.25},
    }
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(response).encode()))
    client = CohortOpenRouter(tmp_path, "unused", "openai/gpt-4o", study="test")
    with pytest.raises(RuntimeError, match="actual cost recorded"):
        client.chat([{"role": "user", "content": "x"}], max_tokens=1)
    assert client.snapshot()["project_committed_usd"] == 1.25
    actual, _ = client.chat([{"role": "user", "content": "x"}], max_tokens=1)
    assert actual == response


def test_ambiguous_network_failure_remains_reserved(tmp_path, monkeypatch):
    import urllib.request

    count = []

    def fail(*a, **k):
        count.append(1)
        raise TimeoutError("uncertain response")

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    client = CohortOpenRouter(tmp_path, "unused", "openai/gpt-4o", study="test")
    with pytest.raises(TimeoutError):
        client.chat([{"role": "user", "content": "x"}])
    with pytest.raises(RuntimeError, match="Unresolved"):
        client.chat([{"role": "user", "content": "x"}])
    assert len(count) == 1 and client.snapshot()["uncertain_calls"] == 1
    assert client.snapshot()["project_committed_usd"] > 0


def test_concurrent_responses_survive_in_journal_without_sqlite_writes(tmp_path, monkeypatch):
    import io
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    def respond(request, **kwargs):
        payload = json.loads(request.data)
        return io.BytesIO(
            json.dumps(
                {
                    "id": payload["messages"][0]["content"],
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"cost": 0.000001},
                }
            ).encode()
        )

    monkeypatch.setattr(urllib.request, "urlopen", respond)
    clients = [CohortOpenRouter(tmp_path, "unused", "openai/gpt-4o", study="test") for _ in range(4)]

    def call(i):
        return clients[i % 4].chat([{"role": "user", "content": str(i)}])

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(call, range(16)))
    assert clients[0].snapshot()["complete_calls"] == 16
    with sqlite3.connect(clients[0].cache) as c:
        assert c.execute("SELECT count(*) FROM responses").fetchone()[0] == 0
    for response, key in results:
        assert clients[0].cached_response(key)["response"] == response


def test_explicit_recovery_retains_old_bound_and_uses_new_cache_identity(tmp_path, monkeypatch):
    import io
    import urllib.request

    client = CohortOpenRouter(tmp_path, "unused", "openai/gpt-4o", study="test")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(TimeoutError()))
    with pytest.raises(TimeoutError):
        client.chat([{"role": "user", "content": "x"}])
    state = json.loads(client.ledger_path.read_text())
    old_key = next(iter(state["calls"]))
    old_bound = client.snapshot()["project_committed_usd"]
    client.recoveries.write_text(json.dumps({old_key: {"attempt": 1}}))
    response = {"id": "recovered", "choices": [{"message": {"content": "ok"}}], "usage": {"cost": 0.00001}}
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(response).encode()))
    result, new_key = client.chat([{"role": "user", "content": "x"}])
    assert result == response and new_key != old_key
    assert client.snapshot()["project_committed_usd"] == pytest.approx(old_bound + 0.00001)
    assert client.snapshot()["uncertain_calls"] == 1
    client.offline = True
    assert client.chat([{"role": "user", "content": "x"}])[1] == new_key


def test_read_only_snapshot_does_not_rewrite_ledger(tmp_path):
    client = CohortOpenRouter(tmp_path, "unused", "openai/gpt-4o", study="test", offline=True)
    client.snapshot()
    before = client.ledger_path.stat().st_mtime_ns
    client.snapshot()
    assert client.ledger_path.stat().st_mtime_ns == before
