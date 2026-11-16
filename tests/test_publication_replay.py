import io
import json
import pytest
from alpha_evolve.publication_llm import CohortOpenRouter
from alpha_evolve.publication_replay import ReadOnlyReplay


def test_frozen_replay_matches_paid_response_and_never_writes_or_calls(tmp_path, monkeypatch):
    import urllib.request

    response = {"id": "source-response", "choices": [{"message": {"content": "saved"}}], "usage": {"cost": 0.000001}}
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(response).encode()))
    live = CohortOpenRouter(tmp_path, "unused", "openai/gpt-4o", study="unit")
    expected, key = live.chat([{"role": "user", "content": "x"}])
    before = live.ledger_path.read_bytes()
    replay = ReadOnlyReplay(tmp_path, "unused", "openai/gpt-4o", study="unit")
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network forbidden"))
    )
    actual, actual_key = replay.chat([{"role": "user", "content": "x"}])
    assert actual == expected and actual_key == key
    assert live.ledger_path.read_bytes() == before
    with pytest.raises(RuntimeError, match="Offline"):
        replay.chat([{"role": "user", "content": "miss"}])
    assert live.ledger_path.read_bytes() == before


def test_live_fast_cache_preserves_budget_enforcement(tmp_path, monkeypatch):
    import urllib.request
    from alpha_evolve.publication_replay import LiveCachedMeter

    calls = []

    def reply(*args, **kwargs):
        calls.append(1)
        return io.BytesIO(
            json.dumps(
                {"id": "initial", "choices": [{"message": {"content": "ok"}}], "usage": {"cost": 0.000001}}
            ).encode()
        )

    monkeypatch.setattr(urllib.request, "urlopen", reply)
    original = CohortOpenRouter(tmp_path, "unused", "openai/gpt-4o", study="unit")
    original.chat([{"role": "user", "content": "cached"}])
    fast = LiveCachedMeter(tmp_path, "unused", "openai/gpt-4o", study="unit", study_cap=0.001)
    fast.chat([{"role": "user", "content": "cached"}])
    assert len(calls) == 1
    with pytest.raises(RuntimeError, match="Budget"):
        fast.chat([{"role": "user", "content": "new"}], max_tokens=2048)
    assert len(calls) == 1
