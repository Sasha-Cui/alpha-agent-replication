"""A completed source is insufficient for a pooled EFS result."""

import copy
import pytest
from alpha_evolve.fidelity_efs_pool_evidence_v2 import require_replay_binding, validate_efs_trial


def pair():
    source = {"status": "complete", "llm_calls": 290, "output_sha256": {"factors.json": "a", "returns.csv": "b"}}
    replay = {
        "status": "pass",
        "network_calls": 0,
        "ledger_mutations": 0,
        "holdings_byte_identical": True,
        "exact_output_hashes": source["output_sha256"].copy(),
        "transport_prefix_validation": [],
    }
    return source, replay


def test_completed_source_without_replay_refused(tmp_path):
    with pytest.raises(ValueError, match="full replay unavailable"):
        validate_efs_trial(tmp_path, "gpt41_2")


def test_partial_or_substituted_replay_is_not_complete():
    source, replay = pair()
    require_replay_binding(source, replay)
    for key, value in [
        ("status", "fail"),
        ("network_calls", 1),
        ("holdings_byte_identical", False),
        ("ledger_mutations", 1),
        ("exact_output_hashes", {"factors.json": "a"}),
    ]:
        bad = copy.deepcopy(replay)
        bad[key] = value
        with pytest.raises(ValueError):
            require_replay_binding(source, bad)


def test_failed_preserved_prefix_or_missing_round_cannot_enter_pool():
    source, replay = pair()
    replay["transport_prefix_validation"] = [{"status": "fail"}]
    with pytest.raises(ValueError, match="history"):
        require_replay_binding(source, replay)
    source, replay = pair()
    source["llm_calls"] = 289
    with pytest.raises(ValueError, match="Incomplete"):
        require_replay_binding(source, replay)


def test_frozen_v1_ledger_attestation_is_accepted_only_when_true():
    source, replay = pair()
    replay.pop("ledger_mutations")
    replay["authoritative_ledger_unchanged"] = True
    require_replay_binding(source, replay)
    replay["authoritative_ledger_unchanged"] = False
    with pytest.raises(ValueError, match="ledger"):
        require_replay_binding(source, replay)
