"""Exercise the generated guard, not merely its generator or an empty log."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "alphamemo_network_guard_probe", ROOT / "scripts/run_alphamemo_real_data_probe.py"
)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


def setup_guard(root):
    guard = probe.network_guard(root)
    env = probe.run_environment(
        dict(os.environ), root, guard, root / "runtime", root / "events.jsonl", Path(sys.executable)
    )
    return guard, env


def test_generated_guard_and_control_program_compile(tmp_path):
    guard, _ = setup_guard(tmp_path)
    compile((guard / "sitecustomize.py").read_text(), "sitecustomize.py", "exec")
    compile(probe.GUARD_SELFTEST, "guard-selftest.py", "exec")


def test_real_guard_blocks_parent_and_child_socket_and_dns_calls(tmp_path):
    guard, env = setup_guard(tmp_path)
    result = probe.verify_network_guard(Path(sys.executable), env, guard)
    assert result["interpreter_processes"] == 2
    assert result["blocked_operations"] == 20
    assert result["child_inherits_guard"] is True
    assert result["loopback_targets_only"] is True


def test_malformed_generated_guard_fails_before_launch(monkeypatch, tmp_path):
    guard, env = setup_guard(tmp_path)
    (guard / "sitecustomize.py").write_text('import socket\n"\n')
    monkeypatch.setattr(probe.subprocess, "run", lambda *a, **kw: pytest.fail("launched with malformed guard"))
    with pytest.raises(SyntaxError):
        probe.verify_network_guard(Path(sys.executable), env, guard)


def test_marker_without_blocking_hook_cannot_pass_positive_control(monkeypatch, tmp_path):
    fake = ('import sys\n'
            'sys._alphamemo_network_guard_ready="alphamemo-python-audit-hook-v2"\n'
            'class NetworkBlocked(PermissionError): pass\n')
    monkeypatch.setattr(probe, "GUARD_SOURCE", fake)
    guard, env = setup_guard(tmp_path)
    # If the guard is broken, this control only connects to loopback port 9.
    with pytest.raises(RuntimeError, match="self-test failed"):
        probe.verify_network_guard(Path(sys.executable), env, guard)


def test_guard_logging_failure_stops_python_before_user_code(tmp_path):
    guard, env = setup_guard(tmp_path)
    env["ALPHAMEMO_NETWORK_LOG"] = str(guard)  # a directory, not a log file
    result = subprocess.run(
        [sys.executable, "-c", "print('UNGUARDED_BODY_EXECUTED')"],
        cwd=tmp_path, env=env, text=True, capture_output=True, timeout=10,
    )
    assert result.returncode == 97
    assert "initialization failed" in result.stderr
    assert "UNGUARDED_BODY_EXECUTED" not in result.stdout


def test_missing_empty_or_wrong_version_log_is_not_zero_attempts(tmp_path):
    path = tmp_path / "events.jsonl"
    with pytest.raises(FileNotFoundError):
        probe.read_guard_events(path)
    path.write_text("")
    with pytest.raises(RuntimeError, match="activation evidence"):
        probe.read_guard_events(path)
    path.write_text(json.dumps({"version": "old", "event": "guard_loaded"}) + "\n")
    with pytest.raises(RuntimeError, match="activation evidence"):
        probe.read_guard_events(path)


def replay_records():
    result = []
    for stage in ("raw", "compatible-1", "compatible-2"):
        entries = ["module:sspm"]
        if stage != "raw":
            entries.extend(["command", "module:qlib.cli.run", "file:read_exp_res.py"])
        for entry in entries:
            common = {"version": probe.GUARD_VERSION, "phase": "replay", "stage": stage, "pid": len(result)}
            result.extend([{**common, "event": "guard_loaded"},
                           {**common, "event": "entrypoint", "entrypoint": entry}])
    return result


def test_replay_requires_guarded_main_qlib_and_reader_processes():
    result = probe.validate_replay_guard_events(replay_records())
    assert result["all_required_entrypoints_guarded"] is True
    assert [row["guarded_interpreters"] for row in result["stages"]] == [1, 4, 4]
    assert result["replay_blocked_operations"] == 0
    assert result["replay_network_silent"] is True
    without_child = [row for row in replay_records() if row.get("entrypoint") != "module:qlib.cli.run"]
    with pytest.raises(RuntimeError, match="coverage incomplete"):
        probe.validate_replay_guard_events(without_child)
    without_activation = [row for row in replay_records() if row["event"] != "guard_loaded"]
    with pytest.raises(RuntimeError, match="lacks guard activation"):
        probe.validate_replay_guard_events(without_activation)


def test_actual_network_attempt_or_selftest_records_cannot_be_counted_as_silent():
    events = replay_records()
    events.append({**events[0], "event": "blocked", "operation": "socket.connect"})
    report = probe.validate_replay_guard_events(events)
    assert report["replay_network_silent"] is False
    assert report["replay_blocked_operations"] == 1
    assert report["blocked_operation_counts"] == {"socket.connect": 1}
    assert len(report["blocked_attempts"]) == 1
    events = replay_records()
    events[0]["phase"] = "selftest"
    with pytest.raises(RuntimeError, match="mixed"):
        probe.validate_replay_guard_events(events)


def test_parent_python_environment_cannot_redirect_the_guard(tmp_path):
    guard, env = setup_guard(tmp_path)
    poisoned = {key: "bad" for key in ("PYTHONHOME", "PYTHONUSERBASE", "PYTHONPATH", "PYTHONINSPECT")}
    isolated = probe.run_environment(poisoned, tmp_path, guard, tmp_path / "runtime2", tmp_path / "events2", Path(sys.executable))
    assert "PYTHONHOME" not in isolated and "PYTHONUSERBASE" not in isolated
    assert "PYTHONINSPECT" not in isolated
    assert isolated["PYTHONPATH"].split(os.pathsep)[0] == str(guard)
    assert env["ALPHAMEMO_GUARD_PHASE"] == "replay"
