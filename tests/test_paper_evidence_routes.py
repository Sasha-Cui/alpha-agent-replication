"""Contract tests for the mutually exclusive paper evidence routes."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_paper_evidence_routes.py"
SPEC = importlib.util.spec_from_file_location("build_paper_evidence_routes", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
TEX_OUTPUT = ROOT / "docs/paper/generated_evidence_routes.tex"

OUTPUT = (
    ROOT
    / "paper_runs/submission_evidence/replication_scope/"
    "paper_evidence_route_ledger.csv"
)


def test_route_precedence_puts_public_code_before_mapping_fidelity() -> None:
    assert (
        MODULE.classify_route(True, {"M0_narrative_translation"})
        == MODULE.PUBLIC_CODE_ROUTE
    )
    assert (
        MODULE.classify_route(False, {"M1_named_rule_partial_support"})
        == MODULE.PAPER_SPECIFIED_ROUTE
    )
    assert (
        MODULE.classify_route(False, {"M1_example_or_motif_partial_support"})
        == MODULE.PAPER_UNDERSPECIFIED_ROUTE
    )


def test_retained_papers_have_one_exhaustive_evidence_route() -> None:
    routes = pd.read_csv(OUTPUT)
    assert len(routes) == routes["canonical_work_id"].nunique() == 69
    assert routes["paper_evidence_route"].value_counts().to_dict() == {
        "paper_only_underspecified": 51,
        "public_code_available": 18,
    }
    assert not routes["paper_evidence_route"].eq(
        "paper_only_sufficiently_specified"
    ).any()
    assert routes[
        "full_prompt_search_training_pipeline_reproduced"
    ].eq("no").all()


def test_public_code_proxies_are_secondary_and_have_precise_blockers() -> None:
    routes = pd.read_csv(OUTPUT)
    public = routes[routes["paper_evidence_route"].eq("public_code_available")]
    assert len(public) == 18
    assert public["precise_native_or_access_blocker"].notna().all()
    assert public["precise_native_or_access_blocker"].str.contains(":A[123]_", regex=True).all()
    assert public["native_pipeline_disposition"].value_counts().to_dict() == {
        "targeted_execution_recorded": 18,
    }
    reconstructed = public[public["good_faith_reconstruction"].eq("yes")]
    assert len(reconstructed) == 13
    fincon = public[public["canonical_work_id"].eq("CensusArxiv240706567")]
    assert fincon["native_pipeline_disposition"].eq(
        "targeted_execution_recorded"
    ).all()
    assert reconstructed["proxy_role"].eq(
        "secondary_diagnostic_after_native_review"
    ).all()


def test_quantevolver_paper_audit_stays_separate_from_component_gate() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("CensusArxiv260515412")].iloc[0]
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_75_native_results_component_gate_separate"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_disposition"] == "source_grounded_component_only"
    assert row["proxy_role"] == "secondary_diagnostic_after_native_review"
    assert "0/75 table cells" in row["precise_native_or_access_blocker"]
    assert "3/3 grade-B component gate" in row["precise_native_or_access_blocker"]


def test_quantaalpha_audit_credits_components_but_zero_paper_results() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("CensusArxiv260207085")].iloc[0]
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_344_native_table_results_components_only"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["proxy_role"] == "secondary_diagnostic_after_native_review"
    assert "all 135 Python files" in row["precise_native_or_access_blocker"]
    assert "0/344 table cells" in row["precise_native_or_access_blocker"]
    assert "Large v1/v2-to-v3 result revisions" in row[
        "precise_native_or_access_blocker"
    ]


def test_completed_paper_audits_are_not_left_as_static_or_legacy_targets() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False).set_index(
        "canonical_work_id"
    )
    expected = {
        "CensusACL2024emnlpmain63": "paper_audit:partial_174_of_468_traditional_baseline_cells",
        "CensusACL2026findingsacl456": "paper_audit:completed_one_of_790_current_snapshot_buy_hold_match",
        "CensusArxiv231113743": "paper_audit:completed_16_of_235_current_snapshot_buy_hold_matches",
        "CensusArxiv250207393": "paper_audit:completed_zero_of_36_native_results_released_checkpoints_mismatch",
        "CensusArxiv250510278": "paper_audit:completed_zero_of_277_native_results_internal_state_only",
        "CensusArxiv250909995": "paper_audit:completed_zero_of_272_native_results_undocumented_feature_gap",
        "WorkAutomateStrategy": "paper_audit:completed_zero_of_40_integrated_portfolio_cells_factor_component_only",
    }
    for work_id, status in expected.items():
        row = routes.loc[work_id]
        assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
        assert row["native_execution_audit_status"] == status


def test_alpha_r1_placeholder_audit_never_promotes_the_motif_proxy() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("CensusArxiv251223515")].iloc[0]
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_652_native_results_official_placeholder"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["mapping_disposition"] == "clearly_labeled_motif_proxy"
    assert row["proxy_role"] == "secondary_diagnostic_after_native_review"
    assert "0/652 table/heatmap cells" in row["precise_native_or_access_blocker"]
    assert "0/70 audited implementation dimensions" in row["precise_native_or_access_blocker"]
    assert "M0 narrative motif proxy" in row["precise_native_or_access_blocker"]


def test_paper_only_partial_components_are_not_native_procedure_replications() -> None:
    routes = pd.read_csv(OUTPUT)
    partial = routes[
        routes["proxy_role"].eq("partial_source_component_not_full_procedure")
    ]
    assert len(partial) == 3
    assert set(partial["mapping_count"]) == {1, 2, 3}
    assert partial["paper_evidence_route"].eq(
        "paper_only_underspecified"
    ).all()
    assert partial["mapping_fidelity_tiers"].eq(
        "M1_example_or_motif_partial_support"
    ).all()


def test_tracked_route_ledger_matches_the_deterministic_builder() -> None:
    expected = MODULE.build_routes(
        pd.read_csv(ROOT / "literature_review/census_v1/primary_record_metadata.csv"),
        pd.read_csv(
            ROOT
            / "paper_runs/submission_evidence/replication_scope/"
            "work_level_evidence_waterfall.csv"
        ),
        pd.read_csv(
            ROOT
            / "paper_runs/submission_evidence/replication_scope/"
            "mapping_scope_ledger.csv"
        ),
        pd.read_csv(
            ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
        ),
    )
    actual = pd.read_csv(OUTPUT, keep_default_na=False)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)

def test_generated_paper_macros_match_route_counts(tmp_path: Path) -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    generated = tmp_path / "generated_evidence_routes.tex"
    MODULE.write_tex_macros(routes, generated)
    assert generated.read_bytes() == TEX_OUTPUT.read_bytes()
    text = generated.read_text()
    assert r"\newcommand{\PublicCodeRouteWorkCount}{18\xspace}" in text
    assert r"\newcommand{\PaperOnlySpecifiedWorkCount}{0\xspace}" in text
    assert r"\newcommand{\PaperOnlyUnderspecifiedWorkCount}{51\xspace}" in text
