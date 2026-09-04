from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "paper_runs/us_jkp_in_spirit"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_in_spirit_ledger_preserves_strict_study_and_has_one_active_case():
    ledger = json.loads((STUDY / "milestones.json").read_text())
    rows = ledger["milestones"]
    assert len(rows) == ledger["paper_count"] == 69
    assert ledger["planned_common_evaluations"] == 62
    assert ledger["planned_new_in_spirit_reconstructions"] == 45
    assert ledger["declared_inference_family_size"] == 69
    assert ledger["strict_ledger_sha256"] == digest(ROOT / "paper_runs/us_jkp_headline/milestones.json")
    assert ledger["strict_final_manifest_sha256"] == digest(ROOT / "paper_runs/us_jkp_headline/final_manifest.json")
    assert ledger["benchmark_contract_sha256"] == digest(ROOT / ledger["benchmark_contract_path"])
    progress = ledger["progress_summary"]
    assert progress["carried_common_evaluation"] == 17
    assert progress["discarded_structural_mismatch"] == 7
    assert progress["completed_in_spirit"] + progress["in_progress_in_spirit"] + progress["queued_in_spirit"] == 45
    assert sum(progress.values()) == 69
    assert progress["in_progress_in_spirit"] in {0, 1}
    active = [row for row in rows if row["status"] == "in_progress_in_spirit"]
    assert len(active) == progress["in_progress_in_spirit"]


def test_only_seven_structural_mismatches_are_discarded():
    ledger = json.loads((STUDY / "milestones.json").read_text())
    discarded = {
        row["milestone_id"]
        for row in ledger["milestones"]
        if row["status"] == "discarded_structural_mismatch"
    }
    assert discarded == {"M002", "M015", "M017", "M031", "M035", "M045", "M058"}


def test_new_study_never_relabels_reconstructions_as_native_replications():
    protocol = (ROOT / "docs/US_JKP_IN_SPIRIT_PROTOCOL.md").read_text()
    ledger = json.loads((STUDY / "milestones.json").read_text())
    assert "native replications" in protocol
    assert "tests that can falsify" in protocol
    for row in ledger["milestones"]:
        if row["status"] in {"in_progress_in_spirit", "queued_in_spirit"}:
            assert row["fidelity_label"] == "in_spirit_reconstruction"
