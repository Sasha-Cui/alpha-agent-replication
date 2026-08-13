from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_macro_economists_audit_routes_paper_only_without_native_credit() -> None:
    subprocess.run([sys.executable, "scripts/build_native_fidelity_ledger.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/build_paper_evidence_routes.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/refresh_static_paper_assets.py"], cwd=ROOT, check=True)

    with (ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        native = {row["system_id"]: row for row in csv.DictReader(stream)}
    row = native["SYS-MACRO-ECONOMISTS-MACHINE"]
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["fidelity_class"] == "F0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_18_paper_derived_mechanics_four_fail_closed_zero_of_132_"
        "table_cells_zero_of_12_empirical_panels_no_attributable_pipeline_major_figure_"
        "table_conflicts"
    )
    note = row["concise_evidence_note"]
    for marker in (
        "132 displayed quantitative result cells",
        "12 empirical figure panels",
        "0/132 cells and 0/12 panels reproduce author-natively",
        "upon reasonable request",
        "transaction-cost figure reports Sharpe ratios about 0.84--0.92",
        "Table 7 reports 0.481--0.571",
        "begins in 2017",
    ):
        assert marker in note

    with (
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    ).open(newline="", encoding="utf-8") as stream:
        routes = {row["canonical_work_id"]: row for row in csv.DictReader(stream)}
    route = routes["CensusArxiv260608283"]
    assert route["paper_evidence_route"] == "paper_only_underspecified"
    assert route["reachable_public_code_system_ids"] == ""
    assert route["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert route["native_execution_audit_status"] == row["targeted_execution_audit_status"]
    assert route["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert route["mapping_count"] == "0"
    assert route["proxy_role"] == "no_proxy"
    assert route["good_faith_reconstruction"] == "no"

    generated = (ROOT / "docs/paper/generated_results.tex").read_text()
    assert r"\newcommand{\TargetedAuditCount}{65}" in generated
    with (ROOT / "paper_runs/submission_evidence/claims.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        claims = {row["macro"]: row for row in csv.DictReader(stream)}
    assert claims["TargetedAuditCount"]["rendered_value"] == "65"
