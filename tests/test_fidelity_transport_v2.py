import errno
import json
import pytest
from alpha_evolve.fidelity_transport_v2 import LockedLiveMeter, retry_stale_read
from alpha_evolve.publication_replay import LiveCachedMeter


def test_snapshot_uses_locked_accounting_and_preserves_reservations(tmp_path, monkeypatch):
    state = {
        "version": 1,
        "imports": {},
        "calls": {
            "a": {"study": "case", "status": "complete", "cost_usd": 0.25},
            "b": {"study": "case", "status": "response_unavailable", "reserved_usd": 0.4},
        },
    }
    path = tmp_path / "project_spend.json"
    path.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n")
    before = path.read_bytes()
    meter = LockedLiveMeter(tmp_path, "unused", "unused", study="case", offline=True)
    monkeypatch.setattr(
        LiveCachedMeter, "snapshot", lambda self: (_ for _ in ()).throw(AssertionError("Unsafe snapshot invoked"))
    )
    assert meter.snapshot()["project_committed_usd"] == 0.65
    assert meter.snapshot()["uncertain_calls"] == 1
    assert path.read_bytes() == before


def test_stale_read_retry_is_bounded_and_only_for_estale(monkeypatch):
    monkeypatch.setattr("alpha_evolve.fidelity_transport_v2.time.sleep", lambda _: None)
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise OSError(errno.ESTALE, "stale")
        return "read_ok"

    assert retry_stale_read(flaky) == "read_ok"
    assert len(calls) == 3
    with pytest.raises(OSError) as failure:
        retry_stale_read(lambda: (_ for _ in ()).throw(OSError(errno.ENOSPC, "full")))
    assert failure.value.errno == errno.ENOSPC
    calls.clear()

    def stale():
        calls.append(1)
        raise OSError(errno.ESTALE, "stale")

    with pytest.raises(OSError):
        retry_stale_read(stale, attempts=2)
    assert len(calls) == 2
