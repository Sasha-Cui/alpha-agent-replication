from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_factormad_audit_routes_paper_only_and_rejects_local_proxy_credit() -> None:
    subprocess.run([sys.executable, "scripts/build_native_fidelity_ledger.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/build_paper_evidence_routes.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/refresh_static_paper_assets.py"], cwd=ROOT, check=True)

    with (ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        native = {row["system_id"]: row for row in csv.DictReader(stream)}
    row = native["SYS-FACTOR-MAD"]
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["fidelity_class"] == "F0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_six_paper_derived_mechanics_seven_fail_closed_zero_of_"
        "30_table_cells_zero_of_8_empirical_panels_no_attributable_pipeline_local_m0_"
        "proxy_no_paper_credit"
    )
    note = row["concise_evidence_note"]
    for marker in (
        "30 displayed empirical result cells",
        "eight empirical panels",
        "0/30 cells and 0/8 panels reproduce author-natively",
        "CSI500 RoMaD of 1.860 versus FactorMAD's 1.341",
        "rank normalization also conflicts",
        "M0 narrative translation",
        "receives no method or result credit",
    ):
        assert marker in note

    with (
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    ).open(newline="", encoding="utf-8") as stream:
        routes = {row["canonical_work_id"]: row for row in csv.DictReader(stream)}
    route = routes["CensusDOI10114537682923770377"]
    assert route["paper_evidence_route"] == "paper_only_underspecified"
    assert route["reachable_public_code_system_ids"] == ""
    assert route["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert route["native_execution_audit_status"] == row["targeted_execution_audit_status"]
    assert route["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert route["mapping_count"] == "1"
    assert route["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert route["mapping_disposition"] == "clearly_labeled_motif_proxy"
    assert route["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    assert route["good_faith_reconstruction"] == "yes"

    generated = (ROOT / "docs/paper/generated_results.tex").read_text()
    assert r"\newcommand{\TargetedAuditCount}{67}" in generated
    with (ROOT / "paper_runs/submission_evidence/claims.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        claims = {row["macro"]: row for row in csv.DictReader(stream)}
    assert claims["TargetedAuditCount"]["rendered_value"] == "67"
