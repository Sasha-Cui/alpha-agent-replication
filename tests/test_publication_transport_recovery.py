"""Transport failures must not erase charges or repeat recoverable responses."""

from pathlib import Path
import importlib.util
import json
import sqlite3
import pytest

spec = importlib.util.spec_from_file_location(
    "transport_supervisor", Path(__file__).resolve().parents[1] / "scripts/resume_finagent_after_transport_failure.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def setup_case(tmp_path):
    root = tmp_path / "ledger"
    root.mkdir()
    state = {
        "calls": {
            "failed": {"status": "reserved", "study": module.STUDY, "reserved_usd": 0.12},
            "complete": {"status": "complete", "study": module.STUDY, "cost_usd": 0.03},
            "foreign": {"status": "reserved", "study": "other", "reserved_usd": 0.09},
        }
    }
    (root / "project_spend.json").write_text(json.dumps(state))
    with sqlite3.connect(root / "response_cache.sqlite3") as c:
        c.execute("CREATE TABLE responses (request_hash TEXT PRIMARY KEY, body TEXT)")
    log = tmp_path / "run.log"
    log.write_text("Traceback:\nTimeoutError: The read operation timed out\n")
    return root, log, state


def test_recovery_keeps_all_charges_and_unrelated_requests(tmp_path):
    root, log, before = setup_case(tmp_path)
    result = module.recover_transport(root, log, tmp_path / "archive")
    after = json.loads((root / "project_spend.json").read_text())
    assert result["retained_usd"] == 0.12
    assert after["calls"]["failed"]["reserved_usd"] == 0.12
    assert after["calls"]["failed"]["status"] == "response_unavailable"
    assert after["calls"]["complete"] == before["calls"]["complete"]
    assert after["calls"]["foreign"] == before["calls"]["foreign"]
    mappings = json.loads((root / "technical_recoveries.json").read_text())
    assert mappings["failed"]["attempt"] == 1
    assert (tmp_path / "archive/before_project_spend.json").exists()


@pytest.mark.parametrize("location", ["journal", "sqlite"])
def test_saved_response_never_triggers_another_paid_attempt(tmp_path, location):
    root, log, _ = setup_case(tmp_path)
    before = (root / "project_spend.json").read_bytes()
    if location == "journal":
        (root / "cohort_responses.jsonl").write_text(json.dumps({"request_hash": "failed"}) + "\n")
    else:
        with sqlite3.connect(root / "response_cache.sqlite3") as c:
            c.execute("INSERT INTO responses VALUES (?, ?)", ("failed", "{}"))
    with pytest.raises(RuntimeError, match="reconcile"):
        module.recover_transport(root, log, tmp_path / "archive")
    assert (root / "project_spend.json").read_bytes() == before
    assert not (root / "technical_recoveries.json").exists()


def test_request_recovery_limit_is_fail_closed(tmp_path):
    root, log, state = setup_case(tmp_path)
    state["calls"]["failed"]["technical_recovery"] = {"original_request_hash": "original", "attempt": 2}
    (root / "project_spend.json").write_text(json.dumps(state))
    before = (root / "project_spend.json").read_bytes()
    with pytest.raises(RuntimeError, match="bound exhausted"):
        module.recover_transport(root, log, tmp_path / "archive")
    assert (root / "project_spend.json").read_bytes() == before


def test_algorithm_or_budget_errors_are_not_retried(tmp_path):
    root, log, _ = setup_case(tmp_path)
    before = (root / "project_spend.json").read_bytes()
    log.write_text("RuntimeError: Budget exhausted before network call\n")
    with pytest.raises(RuntimeError, match="not an eligible"):
        module.recover_transport(root, log, tmp_path / "archive")
    assert (root / "project_spend.json").read_bytes() == before


def test_forked_transport_failure_with_waiting_peer(tmp_path):
    root, log, _ = setup_case(tmp_path)
    log.write_text(
        "\n".join(
            [
                "OSError: [Errno 101] Network is unreachable",
                "urllib.error.URLError: <urlopen error [Errno 101] Network is unreachable>",
                "RuntimeError: Unresolved previous request: failed",
                "RuntimeError: Validation worker failed; others were allowed to finish: {'native_causal': 1, 'no_retrieval': 1}",
            ]
        )
    )
    result = module.recover_transport(root, log, tmp_path / "archive")
    assert result["retained_usd"] == 0.12


@pytest.mark.parametrize(
    "peer_error",
    [
        "ValueError: invalid account",
        "RuntimeError: Budget exhausted before network call",
        "RuntimeError: Unresolved previous request: unknown",
    ],
)
def test_fork_wrapper_does_not_hide_nontransport_or_unknown_peer_failure(tmp_path, peer_error):
    root, log, _ = setup_case(tmp_path)
    before = (root / "project_spend.json").read_bytes()
    log.write_text(
        "\n".join(
            [
                "TimeoutError: The read operation timed out",
                peer_error,
                "RuntimeError: Validation worker failed; others were allowed to finish: {'native_causal': 1, 'no_retrieval': 1}",
            ]
        )
    )
    with pytest.raises(RuntimeError, match="not an eligible"):
        module.recover_transport(root, log, tmp_path / "archive")
    assert (root / "project_spend.json").read_bytes() == before


def test_incomplete_rebuild_is_distinct_from_changed_records(tmp_path):
    archive, native = tmp_path / "saved", tmp_path / "native"
    archive.mkdir()
    native.mkdir()
    (archive / "preserved_decisions.jsonl").write_text('{"date":"a","value":1}\n{"date":"b","value":2}\n')
    current = native / "decisions.jsonl"
    current.write_text('{"date":"a","value":1}\n')
    assert module.compare_preserved_prefixes(archive, native)["status"] == "partial"
    current.write_text('{"date":"a","value":9}\n')
    assert module.compare_preserved_prefixes(archive, native)["status"] == "fail"
    current.write_text('{"date":"a","value":1}\n{"date":"b","value":2}\n{"date":"c","value":3}\n')
    assert module.compare_preserved_prefixes(archive, native)["status"] == "pass"


def test_network_preflight_blocks_before_execution(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("Network is unreachable")

    monkeypatch.setattr(module.urllib.request, "urlopen", unavailable)
    target = tmp_path / "preflight.json"
    with pytest.raises(RuntimeError, match="before native execution"):
        module.network_preflight(target)
    result = json.loads(target.read_text())
    assert result["status"] == "network_blocked"
    assert result["paid_call"] is False
