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
        "paper_only_underspecified": 39,
        "public_code_available": 30,
    }
    assert not routes["paper_evidence_route"].eq(
        "paper_only_sufficiently_specified"
    ).any()
    assert routes[
        "full_prompt_search_training_pipeline_reproduced"
    ].eq("no").all()


def test_chain_of_alpha_withdrawn_paper_audit_stays_paper_only() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[
        routes["canonical_work_id"].eq("CensusArxiv250806312")
    ].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_180_result_cells_withdrawn_"
        "no_attributable_system"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "0/180 result cells" in blocker
    assert "current arXiv withdrawal" in blocker
    assert "two demo prompts" in blocker
    assert "post-paper unaffiliated candidates" in blocker
    assert "M0 monthly characteristic portfolio" in blocker


def test_treevo_two_version_paper_audit_stays_paper_only() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[
        routes["canonical_work_id"].eq("CensusArxiv250816334")
    ].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_v1_zero_of_114_v2_zero_of_293_"
        "seven_prompt_templates_no_attributable_pipeline"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["proxy_role"] == "no_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "0/114 v1" in blocker and "0/293 v2" in blocker
    assert "seven v2" in blocker
    assert "thought-to-code prompt" in blocker
    assert "Qwen3-Max" in blocker


def test_public_code_proxies_are_secondary_and_have_precise_blockers() -> None:
    routes = pd.read_csv(OUTPUT)
    public = routes[routes["paper_evidence_route"].eq("public_code_available")]
    assert len(public) == 30
    assert public["precise_native_or_access_blocker"].notna().all()
    assert public["precise_native_or_access_blocker"].str.contains(":A[123]_", regex=True).all()
    assert public["native_pipeline_disposition"].value_counts().to_dict() == {
        "targeted_execution_recorded": 30,
    }
    reconstructed = public[public["good_faith_reconstruction"].eq("yes")]
    assert len(reconstructed) == 20
    fincon = public[public["canonical_work_id"].eq("CensusArxiv240706567")]
    assert fincon["native_pipeline_disposition"].eq(
        "targeted_execution_recorded"
    ).all()
    assert reconstructed["proxy_role"].eq(
        "secondary_diagnostic_after_native_review"
    ).all()


def test_raptor_route_credits_shipped_outputs_without_claiming_reproduction() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("CensusORziuTkKhgT0")].iloc[0]
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == "SYS-RAPTOR"
    assert row["static_fidelity_tiers"] == "R3"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_16_of_42_author_output_scalar_units_zero_"
        "end_to_end_result_cells"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "recover 16/42 scalar units" in blocker
    assert "0/42 result units" in blocker
    assert "missing testing/stock_prices.csv" in blocker
    assert "paper/source cadence" in blocker
    assert "six-country security-level common-task panel" in blocker


def test_gpt_signal_route_separates_result_replay_from_full_method_fidelity() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("CensusArxiv241018448")].iloc[0]
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == "SYS-GPT-SIGNAL"
    assert row["static_fidelity_tiers"] == "R1"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["native_execution_audit_status"] == (
        "paper_audit:partial_1549_of_1554_published_units_author_thesis_source_recovery"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "1,549/1,554" in blocker
    assert "not an end-to-end GPT regeneration" in blocker
    assert "future-quarter fundamentals" in blocker
    assert "six-country security-level common-task panel" in blocker


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


def test_maci_route_separates_v1_source_lineage_from_unreleased_v3_system() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("CensusArxiv250100826")].iloc[0]
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == "SYS-MACI"
    assert row["static_fidelity_tiers"] == "R2"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_v1_v2_zero_of_321_table_units_21_author_output_"
        "plot_units_zero_regenerated_v3_zero_of_442_no_v3_code"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "0/321 v1/v2 table units" in blocker
    assert "0/442 v3 table units" in blocker
    assert "author-output correspondence" in blocker
    assert "no v3 hierarchical" in blocker
    assert "six-country security-level common task" in blocker


def test_completed_paper_audits_are_not_left_as_static_or_legacy_targets() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False).set_index(
        "canonical_work_id"
    )
    expected = {
        "CensusACL2024emnlpmain63": "paper_audit:partial_174_of_468_traditional_baseline_cells",
        "CensusACL2026findingsacl456": "paper_audit:completed_one_of_790_current_snapshot_buy_hold_match",
        "CensusArxiv231113743": "paper_audit:completed_16_of_235_current_snapshot_buy_hold_matches",
        "CensusArxiv240218485": "paper_audit:completed_zero_of_1061_published_result_units_substantial_source_conflicts",
        "CensusArxiv241018448": "paper_audit:partial_1549_of_1554_published_units_author_thesis_source_recovery",
        "CensusArxiv250207393": "paper_audit:completed_zero_of_36_native_results_released_checkpoints_mismatch",
        "CensusArxiv250510278": "paper_audit:completed_zero_of_277_native_results_internal_state_only",
        "CensusArxiv250909995": "paper_audit:completed_zero_of_272_native_results_undocumented_feature_gap",
        "WorkAutomateStrategy": "paper_audit:completed_zero_of_40_integrated_portfolio_cells_factor_component_only",
    }
    for work_id, status in expected.items():
        row = routes.loc[work_id]
        assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
        assert row["native_execution_audit_status"] == status


def test_flag_trader_paper_only_audit_preserves_its_evidence_boundary() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("CensusACL2025findingsacl716")].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_6_of_360_author_linked_buy_hold_baseline_cells_zero_flag_native_results"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert "zero FLAG-Trader cells reproduce" in row["precise_native_or_access_blocker"]
    assert "No author-linked FLAG-Trader source" in row["precise_native_or_access_blocker"]


def test_efs_paper_only_audit_preserves_versions_and_zero_native_credit() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("CensusArxiv250717211")].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_5_of_773_cited_baseline_cells_zero_efs_native_results_"
        "v2_revision_audited"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M1_example_or_motif_partial_support"
    assert row["proxy_role"] == "partial_source_component_not_full_procedure"
    assert "zero are native EFS results" in row["precise_native_or_access_blocker"]
    assert "All 240 v2 benchmark cells" in row["precise_native_or_access_blocker"]
    assert "48 values relabelled" in row["precise_native_or_access_blocker"]


def test_alpha_jungle_audit_preserves_zero_result_and_component_boundaries() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("CensusArxiv250511122")].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_64_published_cells_zero_native_results_"
        "three_of_six_formula_trees_conditionally_adapted"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M1_example_or_motif_partial_support"
    assert row["mapping_disposition"] == "source_grounded_component_only"
    assert row["proxy_role"] == "partial_source_component_not_full_procedure"
    blocker = row["precise_native_or_access_blocker"]
    assert "Zero official result cells reproduce" in blocker
    assert "Three of six disclosed factor formulas" in blocker
    assert "unaffiliated community repository" in blocker
    assert "AR-to-AER metric-definition change" in blocker


def test_alphaagents_audit_preserves_source_recovery_and_zero_result_boundaries() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[
        routes["canonical_work_id"].eq("CensusArxiv250811152")
    ].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_source_document_and_7_portfolios_zero_of_20_"
        "plotted_series_no_native_agent_pipeline"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["mapping_disposition"] == "clearly_labeled_motif_proxy"
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "recovers seven commented-out portfolio definitions" in blocker
    assert "0/20 plotted performance series reproduce" in blocker
    assert "Five unaffiliated GitHub reimplementations" in blocker
    assert "two local M0 factor scores" in blocker
    assert "receive no AlphaAgents-result credit" in blocker


def test_alpha_gpt_audit_preserves_versioned_result_and_formula_boundaries() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[routes["canonical_work_id"].eq("WorkAlphaGPT")].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_v1_zero_of_20_numeric_cells_zero_of_3_lines_"
        "final_zero_of_47_numeric_cells_zero_of_2_lines_alpha_gpt2_no_"
        "empirical_results"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["mapping_disposition"] == "clearly_labeled_motif_proxy"
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "Alpha-GPT v1 reproduces 0/20 displayed numeric cells" in blocker
    assert "v2/ACL-final study reproduces 0/47 displayed numeric cells" in blocker
    assert "Flow of Funds expression gives div one argument" in blocker
    assert "Ten complete repository searches" in blocker
    assert "receive no Alpha-GPT-result credit" in blocker


def test_alpha_gpt2_route_does_not_invent_an_empirical_result_denominator() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[
        routes["canonical_work_id"].eq("CensusArxiv240209746")
    ].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_v1_zero_of_20_numeric_cells_zero_of_3_lines_"
        "final_zero_of_47_numeric_cells_zero_of_2_lines_alpha_gpt2_no_"
        "empirical_results"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["mapping_disposition"] == "clearly_labeled_motif_proxy"
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "explicitly a work-in-progress architecture draft" in blocker
    assert "no experiment or empirical result denominator" in blocker
    assert "Both local M0 factor scores" in blocker
    assert "receive no Alpha-GPT-result credit" in blocker


def test_llmfactor_audit_preserves_component_and_zero_result_boundaries() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[
        routes["canonical_work_id"].eq("CensusArxiv240610811")
    ].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_prompt_metric_components_zero_of_82_native_cells_"
        "zero_of_206_total_cells_no_author_code"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["mapping_disposition"] == "clearly_labeled_motif_proxy"
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "0/82 native and 0/206 total cells reproduce" in blocker
    assert "prompt skeletons and the ACC/MCC formulas" in blocker
    assert "no LLM request or paper response is replayed" in blocker
    assert "No author-linked implementation" in blocker
    assert "two 2025 unaffiliated implementations" in blocker
    assert "receives no LLMFactor-result credit" in blocker


def test_quantagent_self_improving_audit_preserves_code_and_result_boundaries() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[
        routes["canonical_work_id"].eq("CensusArxiv240203755")
    ].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_document_and_4_listings_zero_of_17_line_series_"
        "zero_of_400_heatmap_cells_no_native_agent_pipeline"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["mapping_disposition"] == "clearly_labeled_motif_proxy"
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    blocker = row["precise_native_or_access_blocker"]
    assert "audits all four published Python listings" in blocker
    assert "mentor-passed V3 has a SyntaxError" in blocker
    assert "0/17 plotted line series and 0/400 heatmap cells reproduce" in blocker
    assert "two local M0 mappings" in blocker
    assert "receive no QuantAgent-result credit" in blocker


def test_fama_audit_preserves_zero_result_and_motif_only_boundaries() -> None:
    routes = pd.read_csv(OUTPUT, keep_default_na=False)
    row = routes[
        routes["canonical_work_id"].eq("CensusACL2024findingsacl233")
    ].iloc[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_65_table_results_zero_of_38_figure_markers_"
        "no_native_pipeline_equation_conflicts"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_fidelity_tiers"] == "M1_example_or_motif_partial_support"
    assert row["mapping_disposition"] == "source_grounded_component_only"
    assert row["proxy_role"] == "partial_source_component_not_full_procedure"
    blocker = row["precise_native_or_access_blocker"]
    assert "zero are reproduced" in blocker
    assert "71 Appendix-B identifiers" in blocker
    assert "without the Pearson square root" in blocker
    assert "preserves only a momentum/trend motif" in blocker
    assert "receive no FAMA-result credit" in blocker


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
    assert r"\newcommand{\PublicCodeRouteWorkCount}{30\xspace}" in text
    assert r"\newcommand{\PaperOnlySpecifiedWorkCount}{0\xspace}" in text
    assert r"\newcommand{\PaperOnlyUnderspecifiedWorkCount}{39\xspace}" in text
