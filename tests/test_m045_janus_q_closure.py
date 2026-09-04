from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M045_janus_q"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m045_closure_uses_current_paper_and_fresh_release_heads():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    current = json.loads((OUTPUT / "current_release_check.json").read_text())
    assert recipe["status"] == recipe["classification"] == "closed_not_evaluable"
    assert recipe["paper_version"]["version"] == current["paper_version"] == "v2"
    assert recipe["paper_version"]["pdf_sha256"] == current["paper_pdf_sha256"]
    assert recipe["current_release_check"]["main_head"] == current["remote_heads"]["refs/heads/main"]
    assert current["main_readme_bytes"] == 1
    assert current["new_native_source_or_checkpoint_found"] is False


def test_m045_reuses_pinned_audit_and_rejects_future_car_actions():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    audit = recipe["reused_audit_evidence"]
    assert sha256(ROOT / audit["manifest"]) == audit["manifest_sha256"]
    assert audit["author_native_table_cells_regenerated"] == 0
    assert audit["author_native_system_source_files"] == 0
    assessment = recipe["monthly_jkp_assessment"]
    assert "future CAR" in assessment["why_released_labels_are_not_a_strategy"]
    assert "direct lookahead" in assessment["why_released_labels_are_not_a_strategy"]
    assert len(assessment["required_but_missing"]) == 5


def test_m045_has_no_fabricated_return_artifacts_and_ledger_is_closed():
    for name in ("run_manifest.json", "primary_monthly_returns.csv", "metrics.csv"):
        assert not (OUTPUT / name).exists()
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M045"]
    assert milestone["status"] == "closed_not_evaluable"
    assert milestone["recipe_path"] and milestone["verdict_path"]
    assert not milestone["implementation_path"]
    assert not milestone["monthly_returns_path"]
    assert not milestone["metrics_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 45
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 35
