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
        "static_common_task_blocker_recorded_not_execution_targeted": 9,
        "targeted_execution_recorded": 9,
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
