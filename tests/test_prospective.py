from datetime import datetime, timezone, timedelta
import json
import pytest
from alpha_evolve.prospective import ensure_seal, commit_forecast, commit_outcome, read_chain, code_digest


def test_seal_forecast_and_future_outcome_barrier(tmp_path):
    code = tmp_path / "strategy.py"
    code.write_text("def score(x):\n    return x+1\n")
    now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)
    seal = ensure_seal(tmp_path, {"case": "unit"}, [code], clock=lambda: now)
    forecast = {
        "execution_at_utc": (now + timedelta(days=1)).isoformat(),
        "evaluation_at_utc": (now + timedelta(days=2)).isoformat(),
        "maximum_input_available_at_utc": (now - timedelta(days=1)).isoformat(),
        "targets": {"A": 1.0},
    }
    row = commit_forecast(tmp_path, seal, forecast, clock=lambda: now)
    with pytest.raises(ValueError, match="already exists"):
        commit_forecast(tmp_path, seal, forecast, clock=lambda: now)
    with pytest.raises(ValueError, match="not observable"):
        commit_outcome(tmp_path, row, {"observed_at_utc": now.isoformat()}, clock=lambda: now)
    later = now + timedelta(days=2, hours=1)
    result = commit_outcome(tmp_path, row, {"observed_at_utc": later.isoformat(), "return": 0.01}, clock=lambda: later)
    assert result["payload"]["forecast_sha256"] == row["sha256"]
    assert not seal["confirmatory_claim_eligible"]
    with pytest.raises(ValueError, match="already recorded"):
        commit_outcome(tmp_path, row, {"observed_at_utc": later.isoformat()}, clock=lambda: later)


def test_code_changes_and_chain_tampering_are_detected(tmp_path):
    code = tmp_path / "strategy.py"
    code.write_text("def score(x):\n    return x+1\n")
    old = code_digest(code)
    code.write_text('def score(x):\n    """New documentation."""\n    return x + 1\n')
    assert code_digest(code) == old
    now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)
    seal = ensure_seal(tmp_path, {}, [code], clock=lambda: now)
    code.write_text("def score(x):\n    return x+2\n")
    with pytest.raises(ValueError, match="changed after seal"):
        ensure_seal(tmp_path, {}, [code], clock=lambda: now)
    forecast = {
        "execution_at_utc": (now + timedelta(days=1)).isoformat(),
        "evaluation_at_utc": (now + timedelta(days=2)).isoformat(),
        "maximum_input_available_at_utc": now.isoformat(),
    }
    commit_forecast(tmp_path, seal, forecast, clock=lambda: now)
    path = tmp_path / "forecasts.jsonl"
    row = json.loads(path.read_text())
    row["payload"]["execution_at_utc"] = (now - timedelta(days=1)).isoformat()
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="integrity"):
        read_chain(path)


def test_backdated_forecast_is_rejected(tmp_path):
    code = tmp_path / "strategy.py"
    code.write_text("x=1\n")
    now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)
    seal = ensure_seal(tmp_path, {}, [code], clock=lambda: now)
    with pytest.raises(ValueError, match="before future"):
        commit_forecast(
            tmp_path,
            seal,
            {
                "execution_at_utc": (now - timedelta(days=1)).isoformat(),
                "evaluation_at_utc": now.isoformat(),
                "maximum_input_available_at_utc": (now - timedelta(days=2)).isoformat(),
            },
            clock=lambda: now,
        )
