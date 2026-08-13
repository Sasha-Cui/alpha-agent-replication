from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_finrs_audit_routes_paper_only_without_native_credit() -> None:
    subprocess.run([sys.executable, "scripts/build_native_fidelity_ledger.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/build_paper_evidence_routes.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/refresh_static_paper_assets.py"], cwd=ROOT, check=True)

    with (ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        native = {row["system_id"]: row for row in csv.DictReader(stream)}
    row = native["SYS-FIN-RS"]
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["fidelity_class"] == "F0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_three_shared_finpos_mechanics_zero_of_225_table_cells_"
        "216_exact_finpos_v1_cells_zero_empirical_panels_no_attributable_pipeline"
    )
    note = row["concise_evidence_note"]
    for marker in (
        "225 displayed empirical cells",
        "216/225 FinRS cells exactly match FinPos v1",
        "displayed-value reuse, not independent empirical corroboration",
        "0/225 cells reproduce author-natively",
        "scaled Kelly, CVaR, and volatility adjustment",
        "future 1/7/30-day price differences",
    ):
        assert marker in note

    with (
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    ).open(newline="", encoding="utf-8") as stream:
        routes = {row["canonical_work_id"]: row for row in csv.DictReader(stream)}
    route = routes["CensusArxiv251112599"]
    assert route["paper_evidence_route"] == "paper_only_underspecified"
    assert route["reachable_public_code_system_ids"] == ""
    assert route["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert route["native_execution_audit_status"] == row["targeted_execution_audit_status"]
    assert route["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert route["mapping_count"] == "0"
    assert route["proxy_role"] == "no_proxy"
    assert route["good_faith_reconstruction"] == "no"

    generated = (ROOT / "docs/paper/generated_results.tex").read_text()
    assert r"\newcommand{\TargetedAuditCount}{67}" in generated
    with (ROOT / "paper_runs/submission_evidence/claims.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        claims = {row["macro"]: row for row in csv.DictReader(stream)}
    assert claims["TargetedAuditCount"]["rendered_value"] == "67"
