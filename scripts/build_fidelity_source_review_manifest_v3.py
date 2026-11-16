#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Preserve the exact interim methods evidence without claiming human review."""

from pathlib import Path
from datetime import datetime, timezone
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    packet = PUBLIC / "SOURCE_REVIEW_PACKET.md"
    paths = {packet, Path(__file__)}
    for target in re.findall(r"\]\(([^)]+)\)", packet.read_text()):
        if target == "source_review_evidence_manifest.json":
            continue
        p = PUBLIC / target
        if not p.is_file():
            raise ValueError("Broken methods-packet link: " + target)
        paths.add(p)
    runs = [
        PRIVATE / "quantaalpha_bounded",
        *[PRIVATE / f"alphaagent_rounds_paper_gpt35_{i:02d}" for i in range(1, 21)],
    ]
    for run in runs:
        replay_name = "full_replay_validation.json" if (run / "full_replay_validation.json").exists() else "observed_abort_replay_validation.json"
        if not (run / replay_name).exists():
            continue
        for name in [
            replay_name,
            "used_factor_manifest.json",
            "independent_accounts/validation.json",
        ]:
            p = run / name
            if not p.exists():
                raise ValueError("Partially available completed-source evidence: " + str(p))
            paths.add(p)
        paths.update((run / "causality_full_universe").glob("*.json"))
    for name in [
        "native_inference_calibration/summary.json",
        "native_grouped_calibration/summary.json",
        "quantaalpha_paper_parameters.yaml",
        "factor_search_input_boundary_amendment.json",
    ]:
        paths.add(PUBLIC / name)
    for name in [
        "native_secondary_evidence_v2.py",
        "analyze_native_secondary_oos_v2.py",
        "analyze_native_grouped_oos_v2.py",
        "analyze_native_oos_v2.py",
        "replay_native_open_execution_v2.py",
        "run_fidelity_http_recovery_v2.py",
        "evaluate_efs_pool_v2.py",
        "build_tradingagents_news_accounts_v2.py",
        "build_tradingagents_news_report_v2.py",
        "build_quanta_results_report_v2.py",
        "prepare_efs_grammar_pool_v2.py",
        "evaluate_efs_grammar_pool_v2.py",
        "analyze_efs_pooled_v2.py",
        "collect_v2_project_primary_family.py",
        "probe_efs_analysis_runtime_v2.py",
        "diagnose_alphaagent_final_http400_v2.py",
        "complete_alphaagent_failure_diagnosis_v2.py",
        "finalize_alphaagent_terminal_v2.py",
        "replay_alphaagent_terminal_v2.py",
        "fidelity_alpha_terminal_v2.py",
        "export_alphaagent_used_factors_v2.py",
        "prepare_native_oos_library_v2.py",
        "summarize_fidelity_completion_v2.py",
        "submit_alpha_secondary_v2.py",
        "diagnose_alphaagent_early_abort_v2.py",
        "finalize_alphaagent_early_abort_v2.py",
        "replay_alphaagent_early_abort_v2.py",
        "fidelity_alpha_early_abort_v2.py",
        "alpha_observed_history_evidence_v2.py",
        "build_alpha_observed_history_catalogue_v2.py",
        "prepare_alpha_observed_library_v2.py",
        "run_alpha_observed_oos_arm_v2.py",
        "analyze_alpha_observed_history_v2.py",
        "submit_alpha_observed_history_v2.py",
        "audit_alpha_observed_costs_v2.py",
        "alpha_constructor_abort_v3.py",
        "run_alpha_constructor_abort_v3.py",
        "fidelity_equity_evidence_v2.py",
        "build_fidelity_accounts_v2.py",
        "recover_efs_pool_walltime_v2.py",
        "quanta_paper_evaluation_evidence_v2.py",
        "analyze_quanta_paper_parameter_v2.py",
        "run_quanta_paper_eval_stage_v2.py",
        "submit_quanta_paper_eval_v2.py",



    ]:
        paths.add(ROOT / "scripts" / name)
    for name in [
        "fidelity_open_limits_v2.py",
        "fidelity_http_recovery_v2.py",
        "fidelity_live_recovery_v2.py",
        "quantaalpha_paper_parameters_v2.py",
        "fidelity_inference_v2.py",
        "fidelity_efs_pool_evidence_v2.py",
        "fidelity_efs_grammar_pool_v2.py",
    ]:
        paths.add(ROOT / "src/alpha_evolve" / name)
    paths.add(ROOT / "tests/test_alpha_terminal_failure_v2.py")
    paths.add(ROOT / "tests/test_alpha_secondary_submission_v2.py")
    paths.add(ROOT / "tests/test_alpha_early_abort_v2.py")
    paths.add(ROOT / "tests/test_alpha_observed_history_scope_v2.py")
    paths.add(ROOT / "tests/test_alpha_observed_financial_scope_v2.py")
    paths.add(ROOT / "tests/test_alpha_constructor_abort_v3.py")
    paths.add(ROOT / "tests/test_fidelity_equity_evidence_v2.py")
    paths.add(ROOT / "tests/test_quanta_paper_eval_v2.py")
    paths.add(PRIVATE / "efs_pool_walltime_recovery_20260918/jobs.json")
    paths.add(PRIVATE / "alpha_observed_history_jobs.json")
    paths.add(PRIVATE / "alpha_observed_launch_20260918/complete20_source_catalogue_at_submission.json")
    paths.add(PRIVATE / "efs_pool_walltime_recovery_20260918/completed19_observed_source_gates.json")
    paths.add(PRIVATE / "efs_pool_walltime_recovery_20260918/deepseek3_actual_source_gate.json")
    paths.add(PRIVATE / "quanta_paper_eval_setup_20260918/readiness.json")
    for name in ["source_manifest.json", "actual_existing_cohort_probe.json", "actual_all3_gpt_efs_source_gate.json", "partial_family_job.json"]:
        paths.add(PRIVATE / "equity_final_gate_20260918" / name)
    paths.add(PRIVATE / "final_equity_account_jobs.json")
    paths.add(PRIVATE / "observed_source_audit_20260918_0622/completed17_observed_source_gates.json")
    for name in ["jobs.json", "source_manifest.json", "alpha_observed_abort_admission_v3_frozen.json", "trial14/diagnosis.json", "trial15/diagnosis.json"]:
        paths.add(PRIVATE / "alpha_constructor_abort_v3_20260918" / name)
    for i in [14,15]:
        paths.add(PRIVATE / ("alphaagent_rounds_paper_gpt35_%02d" % i) / "constructor_abort_evidence_v3.json")
    for name in ["readiness.json", "financial_statement_conformance.json"]:
        paths.add(PRIVATE / "alpha_observed_history_scope_20260918/financial_implementation" / name)
    for name in ["readiness.json", "actual_source_gate_probe_final.json"]:
        paths.add(PRIVATE / "alpha_observed_history_scope_20260918" / name)
    paths.add(PRIVATE / "alphaagent_rounds_paper_gpt35_12/observed_abort_replay_validation.json")
    paths.add(PRIVATE / "alphaagent_rounds_paper_gpt35_12/used_factor_manifest.json")
    paths.add(PRIVATE / "alphaagent_rounds_paper_gpt35_12/independent_accounts/validation.json")
    paths.update((PRIVATE / "alphaagent_rounds_paper_gpt35_12/causality_full_universe").glob("*.json"))
    for name in ["diagnosis.json", "source_manifest.json", "jobs.json"]:
        paths.add(PRIVATE / "alpha_trial12_early_abort_20260918" / name)
    paths.add(PRIVATE / "alphaagent_rounds_paper_gpt35_12/early_abort_evidence.json")
    paths.add(PRIVATE / "alpha_secondary_launcher_20260918/manifest.json")
    for name in ["diagnosis.json", "response_absence.json", "source_manifest.json", "jobs.json"]:
        paths.add(PRIVATE / "alpha_trial08_failure_20260918" / name)
    paths.add(PRIVATE / "alphaagent_rounds_paper_gpt35_08/terminal_failure_closure.json")
    for name in ["audit.py", "validation.json", "library_manifest.json", "observed_source_catalogue.json", "audit_native.py", "native_validation.json"]:
        paths.add(PRIVATE / "alpha_observed_library_audit_20260918_1125" / name)
    paths.add(ROOT / "scripts/build_alpha_observed_report_v2.py")
    paths.add(PUBLIC / "alpha_observed_history_report/lineage.json")
    paths.add(PUBLIC / "alpha_observed_history_report/contract.json")
    for name in ["diagnose.py", "diagnose_v2.py", "diagnosis.json", "preservation_manifest.json", "proposed_manual_exception.json"]:
        paths.add(PRIVATE / "finagent_amzn_http500_20260918" / name)
    paths.add(PRIVATE / "efs_deep_pool_audit_20260918_1125/validation.json")
    paths.add(ROOT / "scripts/build_efs_pooled_report_v2.py")
    for name in ["completion.json", "primary_comparisons.json", "execution_evidence.json"]:
        paths.add(PUBLIC / "efs_pooled_analysis" / name)
    for name in ["lineage.json", "contract.json"]:
        paths.add(PUBLIC / "efs_pooled_report" / name)
    paths.add(PUBLIC / "project_primary_family/latest.json")
    paths.add(ROOT / "scripts/fidelity_archive_readiness_v2.py")
    paths.add(ROOT / "tests/test_fidelity_archive_readiness_v2.py")
    paths.add(PRIVATE / "archive_readiness_20260918_1325/actual_probe.json")
    paths.add(PRIVATE / "archive_readiness_20260918_1325/actual_final_probe.json")
    paths.add(PRIVATE / "archive_readiness_20260918_1325/final_source_manifest.json")
    paths.add(ROOT / "scripts/finagent_googl_xml_alias_v2.py")
    paths.add(ROOT / "scripts/probe_finagent_googl_xml_v2.py")
    paths.add(ROOT / "tests/test_finagent_googl_xml_alias_v2.py")
    for name in ["diagnose.py", "diagnose_v2.py", "diagnosis.json", "preservation_manifest.json", "prefix_ancestry_validation.json", "frozen_protocol.json", "probe_source_manifest.json", "jobs.json"]:
        paths.add(PRIVATE / "finagent_googl_xml_20260918" / name)
    paths.add(PRIVATE / "finagent_googl_xml_20260918/diagnostic_artifacts.json")
    for name in ["finagent_googl_xml_continuation_evidence_v2.py", "run_finagent_googl_xml_continuation_v2.py", "probe_finagent_walltime_prefix_v2.py"]:
        paths.add(ROOT / "scripts" / name)
    paths.add(ROOT / "tests/test_finagent_googl_xml_continuation_v2.py")
    paths.add(PRIVATE / "finagent_GOOGL_company_news_xml_prefix_probe/xml_prefix_probe_validation.json")
    for name in ["frozen_protocol.json", "source_manifest.json", "jobs.json", "submit_once.py", "final_guards_py312.log", "final_guards_py39.log"]:
        paths.add(PRIVATE / "finagent_googl_xml_continuation_20260919_0135" / name)
    for name in ["preserve.py", "preservation_manifest.json", "symlink_boundary.json", "audit_reservations.py", "reservation_diagnosis.json", "diagnose_orphans.py", "orphan_response_diagnosis.json", "finagent_probe_protocol.json", "submit_probes_once.py", "probe_jobs.json"]:
        paths.add(PRIVATE / "walltime_interruptions_20260919_0135" / name)
    paths.add(PRIVATE / "walltime_interruptions_20260919_0135/link_target_validation.json")
    paths.add(PRIVATE / "walltime_interruptions_20260919_0135/final_source_manifest.json")
    for name in ["finagent_walltime_evidence_v2.py", "run_finagent_walltime_continuation_v2.py", "settle_finagent_walltime_responses_v2.py", "fidelity_equity_evidence_v3.py", "build_fidelity_accounts_v3.py"]:
        paths.add(ROOT / "scripts" / name)
    paths.add(ROOT / "tests/test_finagent_walltime_continuation_v2.py")
    for name in ["frozen_protocol.json", "source_manifest.json", "planned_settlement.json", "settlement_attempt.json", "settlement_receipt.json", "canonical_read_only_response_validation.json", "existing_eight_admission_and_financial_conformance.json", "submit_once.py", "jobs.json"]:
        paths.add(PRIVATE / "finagent_walltime_continuation_20260919_0237" / name)
    for symbol in ["finagent_AAPL", "finagent_MSFT", "finagent_TSLA_schema_repair"]:
        paths.add(PRIVATE / (symbol + "_walltime_prefix_probe_20260919") / "prefix_probe_validation.json")
    for name in ["audit_checkpoints.py", "audit_checkpoints_v2.py", "audit.log", "audit_v2.log", "checkpoint_inventory.json", "source_manifest.json"]:
        paths.add(PRIVATE / "quanta_walltime_state_audit_20260919_0237" / name)
    paths.add(PRIVATE / "finagent_walltime_continuation_20260919_0237/final_source_manifest.json")
    paths.update((PRIVATE / "finagent_walltime_continuation_20260919_0237").glob("guards_*.log"))
    for name in ["quanta_walltime_reconstruction_v2.py", "quanta_walltime_reconstruction_v3.py", "probe_quanta_walltime_reconstruction_v2.py", "probe_quanta_walltime_reconstruction_v3.py", "probe_quanta_walltime_reconstruction_v4.py"]:
        paths.add(ROOT / "scripts" / name)
    for name in ["test_quanta_walltime_reconstruction_v2.py", "test_quanta_walltime_reconstruction_v3.py"]:
        paths.add(ROOT / "tests" / name)
    paths.add(PUBLIC / "quanta_walltime_reconstruction_protocol.json")
    paths.add(PUBLIC / "quanta_walltime_reconstruction_protocol_v3.json")
    paths.add(PRIVATE / "quanta_reconstruction_setup_20260919_0337/readiness_attempts_manifest.json")
    for subdir in ["", "v3", "v4"]:
        base=PRIVATE / "quanta_reconstruction_setup_20260919_0337" / subdir
        for name in ["source_manifest.json", "frozen_protocol.json", "construction_readiness.log"]:
            paths.add(base / name)
        paths.update(base.glob("guards_*.log"))
    for name in ["jobs.json", "submit_once.py", "final_source_manifest.json"]:
        paths.add(PRIVATE / "quanta_reconstruction_setup_20260919_0337/v4" / name)
    for name in ["software_readiness.json", "hook_installation.json", "runtime_import_processes.jsonl"]:
        paths.add(PRIVATE / "quantaalpha_paper_parameters_walltime_reconstruction_probe__v4_constructor_readiness" / name)
    for name in ["audit.py", "validation.json", "locked_budget.json", "scheduler.txt"]:
        paths.add(PRIVATE / "finagent_tsla_source_completion_20260919_0840" / name)
    for name in ["completion.json", "walltime_completion_validation.json", "live_prefix_gate.json", "wrapper.json"]:
        paths.add(PRIVATE / "finagent_TSLA_schema_repair_walltime_continuation_v2" / name)
    for name in ["quanta_walltime_continuation_v2.py","run_quanta_walltime_continuation_v2.py","quanta_continued_source_admission_v2.py","quanta_paper_evaluation_evidence_v3.py","run_quanta_paper_eval_stage_v3.py","analyze_quanta_paper_parameter_v3.py","submit_quanta_paper_eval_v3.py","close_quanta_continued_source_v2.py","summarize_fidelity_completion_v3.py"]:
        paths.add(ROOT/"scripts"/name)
    for name in ["test_quanta_walltime_continuation_v2.py","test_quanta_paper_eval_v3.py"]:paths.add(ROOT/"tests"/name)
    new=PRIVATE/"quanta_continuation_setup_20260919_after_reset"
    for name in ["native_artifact_lineage.json","audit_native_lineage.py","frozen_protocol.json","jobs.json","submit_once.py","constructor_readiness.log","guards_py312.log","guards_py39.log"]:paths.add(new/name)
    for name in ["frozen_protocol.json","financial_conformance.json","actual_preflight.json","guards_py312.log","guards_py39.log","closure_jobs.json","freeze_and_queue_closure.py"]:paths.add(new/"evaluation"/name)
    paths.add(PRIVATE/"quantaalpha_paper_parameters_walltime_reconstruction_probe__v4/reconstruction_validation.json")
    paths.add(PRIVATE/"quantaalpha_paper_parameters_walltime_reconstruction_probe__v4/reconstructed_rng_state.json")
    paths.add(PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v2_constructor_readiness/software_readiness.json")
    for name in ["audit.py","validation.json","locked_budget_corrected.json","scheduler.txt","update_status.py"]:paths.add(PRIVATE/"completion_admission_20260919_after_reset"/name)
    for name in ["finagent_GOOGL_company_news_xml_repair","finagent_TSLA_schema_repair_walltime_continuation_v2"]:
        paths.add(PRIVATE/(name+"_full_replay_validation.json"))
        for suffix in ["","_offline_replay"]:
            for file in ["completion.json","wrapper.json"]:paths.add(PRIVATE/(name+suffix)/file)
    for name in ["quanta_native_population_v2.py","audit_quanta_native_population_v2.py","quanta_paper_evaluation_evidence_v4.py","run_quanta_paper_eval_stage_v4.py","analyze_quanta_paper_parameter_v4.py","submit_quanta_paper_eval_v4.py","close_quanta_continued_source_v3.py"]:paths.add(ROOT/"scripts"/name)
    paths.add(ROOT/"tests/test_quanta_paper_eval_v4.py")
    v4=PRIVATE/"quanta_continuation_setup_20260919_after_reset/evaluation/v4"
    for name in ["frozen_protocol.json","financial_conformance.json","actual_preflight.json","guards_py312.log","guards_py39.log","closure_jobs.json","closure_intent_before_terminal_status_diagnosis.json","freeze_and_replace_closure_once.py","finish_replacement_after_terminal_audit.py"]:paths.add(v4/name)
    gate=PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v2/continuation_prefix_gate.json"
    if gate.exists():paths.add(gate)
    paths.add(PRIVATE/"quanta_continuation_setup_20260919_after_reset/actual_live_gate/validation.json")
    for name in ["quanta_walltime_continuation_v3.py","run_quanta_walltime_continuation_v3.py","quanta_continued_source_admission_v3.py","quanta_native_population_v3.py","audit_quanta_native_population_v3.py","quanta_paper_evaluation_evidence_v5.py","run_quanta_paper_eval_stage_v5.py","analyze_quanta_paper_parameter_v5.py","submit_quanta_paper_eval_v5.py","close_quanta_continued_source_v4.py"]:paths.add(ROOT/"scripts"/name)
    for name in ["test_quanta_walltime_continuation_v3.py","test_quanta_paper_eval_v5.py"]:paths.add(ROOT/"tests"/name)
    stopped=PRIVATE/"quanta_continuation_stop_20260919_1850"
    for name in ["preserve.py","preservation_manifest.json","diagnose.py","diagnosis.json","pending_model_identity.py","pending_model_identity.json"]:paths.add(stopped/name)
    newer=PRIVATE/"quanta_continuation_setup_20260919_after_reset/v3"
    for name in ["frozen_protocol.json","jobs.json","submit_once.py","constructor_readiness.log","guards_py312.log","guards_py39.log","freeze.py"]:paths.add(newer/name)
    for name in ["frozen_protocol.json","financial_conformance.json","actual_preflight.json","guards_py312.log","guards_py39.log","closure_jobs.json","freeze_and_submit_closure_once.py"]:paths.add(newer/"evaluation"/name)
    paths.add(PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v3_constructor_readiness/software_readiness.json")
    paths.add(ROOT/"scripts/fidelity_archive_readiness_v3.py")
    paths.add(ROOT/"tests/test_fidelity_archive_readiness_v3.py")
    archive3=PRIVATE/"archive_request_scope_v3_20260919_2123"
    for name in ["actual_preflight.json","source_manifest.json","guards_py312.log","guards_py39.log","record.py","locked_budget.json"]:paths.add(archive3/name)
    live3=PRIVATE/"quanta_v3_live_gate_audit_20260919_2224"
    for name in ["audit.py","audit.log","validation.json","locked_budget.json","first_completed_pool_entry.json","scheduler.txt","record.py"]:paths.add(live3/name)
    current=PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v3"
    for name in ["continuation_prefix_gate.json","partial_continuation_prefix_gate.json","reconstructed_rng_state.json","partial_reconstructed_rng_state.json"]:paths.add(current/name)
    msft=PRIVATE/"finagent_msft_source_completion_20260920_0229"
    for name in ["audit.py","audit.log","validation.json","locked_budget.json","scheduler.txt","record.py"]:paths.add(msft/name)
    for name in ["completion.json","walltime_completion_validation.json","live_prefix_gate.json","wrapper.json"]:paths.add(PRIVATE/"finagent_MSFT_walltime_continuation_v2"/name)
    msft_full=PRIVATE/"finagent_msft_full_replay_20260920_0246"
    for name in ["admit.py","admit.log","validation.json","scheduler.txt","record.py","primary_override_update_receipt.json"]:paths.add(msft_full/name)
    paths.add(PRIVATE/"finagent_MSFT_walltime_continuation_v2_full_replay_validation.json")
    for name in ["completion.json","walltime_completion_validation.json","wrapper.json"]:paths.add(PRIVATE/"finagent_MSFT_walltime_continuation_v2_offline_replay"/name)
    aapl=PRIVATE/"finagent_aapl_source_completion_20260920_0303"
    for name in ["audit.py","audit.log","validation.json","locked_budget.json","scheduler.txt","record.py"]:paths.add(aapl/name)
    for name in ["completion.json","walltime_completion_validation.json","live_prefix_gate.json","wrapper.json"]:paths.add(PRIVATE/"finagent_AAPL_walltime_continuation_v2"/name)
    aapl_full=PRIVATE/"finagent_aapl_full_replay_20260920_0429"
    for name in ["admit.py","admit.log","validation.json","scheduler.txt","record.py","primary_override_update_receipt.json"]:paths.add(aapl_full/name)
    paths.add(PRIVATE/"finagent_AAPL_walltime_continuation_v2_full_replay_validation.json")
    for name in ["completion.json","walltime_completion_validation.json","wrapper.json"]:paths.add(PRIVATE/"finagent_AAPL_walltime_continuation_v2_offline_replay"/name)
    q_source=PRIVATE/"quanta_v3_source_completion_20260920_0632"
    for name in ["audit.py","audit.log","boundary_diagnosis/diagnosis.json","v2/audit.py","v2/audit.log","v2/validation.json","v2/locked_budget.json"]:paths.add(q_source/name)
    q_replay=PRIVATE/"quanta_v3_full_replay_20260920_0632"
    for name in ["admit.py","admit.log","validation.json","scheduler.txt","preserved_v3_admission_failure.json","record.py"]:paths.add(q_replay/name)
    for name in ["continuation_completion.json","full_replay_validation.json","execution_exit.json","parameter_wiring.json","log/evolution_state.json"]:paths.add(PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v3"/name)
    for name in ["continuation_prefix_gate.json","partial_continuation_prefix_gate.json","reconstructed_rng_state.json","partial_reconstructed_rng_state.json","parameter_wiring.json"]:paths.add(PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v3_offline_replay"/name)
    eval6=PRIVATE/"quanta_continuation_setup_20260919_after_reset/v3/evaluation_v6"
    for name in ["frozen_protocol.json","actual_preflight.json","financial_conformance.json","guards_py312.log","guards_py39.log","freeze.py","submit_closure_once.py","closure_jobs.json","replacement_intent.json"]:paths.add(eval6/name)
    import json
    for row in json.loads((eval6/"frozen_protocol.json").read_text())["bindings"]:
        path=Path(row["path"])
        if not path.is_absolute():path=ROOT/path
        if path.is_relative_to(ROOT):paths.add(path)
        paths.add(ROOT/row["copy"])
    archive4=PRIVATE/"archive_request_scope_v4_20260920_0632"
    for name in ["source_manifest.json","actual_preflight.json","guards_py312.log","guards_py39.log"]:paths.add(archive4/name)
    for row in json.loads((archive4/"source_manifest.json").read_text())["bindings"]:paths.add(ROOT/row["path"])
    q_closure=PRIVATE/"quanta_source_closure_completion_20260920_0732"
    for name in ["audit.py","audit.log","validation.json","scheduler.txt","record.py"]:paths.add(q_closure/name)
    current=PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v3"
    for name in ["source_closure_gate.json","source_export_accounts_completion.json","native_model_population_validation.json","used_factor_manifest.json","independent_accounts/validation.json"]:paths.add(current/name)
    paths.add(PRIVATE/"quanta_paper_evaluation_jobs.json")
    stop=PRIVATE/"quanta_parameter_proof_stop_20260920_0732"
    for name in ["cancellation_intent.json","scheduler_before.txt","scheduler_after.txt","initial_preservation.json","matrix_path_diagnosis.json"]:paths.add(stop/name)
    proof_setup=PRIVATE/"quanta_continued_proof_setup_20260920_0732"
    for name in ["frozen_protocol.json","freeze.py","freeze.log","calculation_conformance.json","guards_py312.log","guards_py39.log","actual_matrix_preflight.json","submit_probe_once.py","probe_jobs.json"]:paths.add(proof_setup/name)
    for row in json.loads((proof_setup/"frozen_protocol.json").read_text())["bindings"]:
        path=Path(row["path"])
        if not path.is_absolute():path=ROOT/path
        if path.is_relative_to(ROOT):paths.add(path)
        paths.add(ROOT/row["copy"])
    proof_setup=PRIVATE/"quanta_continued_proof_setup_20260920_0732"
    for name in ["probe_validation.json","validate_probe.py","probe_scheduler.txt"]:paths.add(proof_setup/name)
    used=json.loads((PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v3/used_factor_manifest.json").read_text())
    paths.add(PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v3/causality_full_universe"/(used["programs"][0]["sha256"]+".json"))
    eval7=proof_setup/"v7"
    for name in ["frozen_protocol.json","freeze.py","freeze.log","financial_conformance.json","guards_py312.log","guards_py39.log","actual_source_gate.json","record.py"]:paths.add(eval7/name)
    paths.add(PRIVATE/"quanta_paper_evaluation_jobs_v7.json")
    for row in json.loads((eval7/"frozen_protocol.json").read_text())["bindings"]:
        path=Path(row["path"])
        if not path.is_absolute():path=ROOT/path
        if path.is_relative_to(ROOT):paths.add(path)
        paths.add(ROOT/row["copy"])
    archive5=PRIVATE/"archive_request_scope_v5_20260920_0732"
    for name in ["source_manifest.json","actual_preflight.json","guards_py312.log","guards_py39.log"]:paths.add(archive5/name)
    for row in json.loads((archive5/"source_manifest.json").read_text())["bindings"]:paths.add(ROOT/row["path"])
    all_proofs=PRIVATE/"quanta_all142_proofs_completion_20260920_1839"
    for name in ["audit.py","audit.log","validation.json","scheduler.txt","record.py"]:paths.add(all_proofs/name)
    used=json.loads((PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v3/used_factor_manifest.json").read_text())
    for row in used["programs"]:
        paths.add(ROOT/row["code"])
        paths.add(PRIVATE/"quantaalpha_paper_parameters_walltime_continuation_v3/causality_full_universe"/(row["sha256"]+".json"))
    economic=PRIVATE/"quanta_parameter_economic_completion_20260920_2141"
    for name in ["audit.py","audit.log","validation.json","scheduler.txt","report_preservation.json","archive_request_preflight.json","record.py"]:paths.add(economic/name)
    report=PUBLIC/"quanta_parameter_report"
    paths.update(p for p in report.rglob("*") if p.is_file())
    for name in ["build_quanta_parameter_report_v1.py","validate_quanta_parameter_report_v1.py"]:paths.add(ROOT/"scripts"/name)
    analysis=PUBLIC/"quanta_paper_parameter_sensitivity"
    paths.update(p for p in analysis.iterdir() if p.is_file())
    for arm in ["source4","alpha158"]:
        for suffix in ["","_open_information"]:
            run=PRIVATE/("quantaalpha_paper_parameters_oos_"+arm+"_plus_library"+suffix)
            for name in ["completion.json","execution_recipe.json","oos_config.yaml","independent_accounts/validation.json","independent_accounts/account.csv"]:paths.add(run/name)
    for name in ["library_manifest.json","parameter_sensitivity_evidence.json"]:paths.add(PRIVATE/"quantaalpha_paper_parameters_fixed_library"/name)
    draft=PUBLIC/"manuscript_draft_v1"
    paths.update(p for p in draft.rglob("*") if p.is_file())
    paths.add(PUBLIC/"manuscript_draft_completion_v1.json")
    draft_setup=PRIVATE/"manuscript_draft_setup_20260920_2243"
    for name in ["record.py","preservation.json","historical_method_bindings.json","source_version_diagnosis.json","prepare_inputs.py","prepare_inputs_v2.py","prepare_inputs_v2.log","validation_final.log","locked_budget.json"]:paths.add(draft_setup/name)
    for name in ["build_fidelity_manuscript_draft_v1.py","validate_fidelity_manuscript_draft_v1.py"]:paths.add(ROOT/"scripts"/name)
    for row in json.loads((draft_setup/"historical_method_bindings.json").read_text())["bindings"]:paths.add(ROOT/row["recorded_method_copy"])
    amzn=PRIVATE/"finagent_amzn_manual_retry_20260922"
    paths.add(PUBLIC/"finagent_amzn_manual_continuation_v1.json")
    for name in ["approval.json","protocol.json","continuation_protocol.json","continuation_guard_checks.json","retry_receipt.json","canonical_read_only_retry_validation.json","attempt_intent.json","reservation_committed.json","network_attempt_started.json","scheduler_before_retry.txt","scheduler_before_submission.txt","scheduler_after_submission.txt","test_guards.py","guards.log","freeze_continuation.py","submit_once.py","submission_intent.json","live_submission_intent.json","live_submission_response.json","replay_submission_intent.json","replay_submission_response.json","jobs.json","submission.log","record_progress.py"]:paths.add(amzn/name)
    for name in ["finagent_amzn_manual_retry_v1.py","run_finagent_amzn_continuation_v1.py","admit_finagent_amzn_manual_v1.py"]:paths.add(ROOT/"scripts"/name)
    paths.add(PUBLIC/"budget_authorization_1000_20260922.json")
    paths.add(PRIVATE/"budget_authorization_1000_20260922/authorization.json")
    amzn_transition=PRIVATE/"finagent_amzn_manual_retry_20260922/live_transition_20260922_0723"
    paths.update(p for p in amzn_transition.iterdir() if p.is_file())
    paths.add(PRIVATE/"finagent_amzn_manual_retry_20260922/validate_live_transition.py")
    paths.add(PUBLIC/"finagent_amzn_source_completion.json")
    amzn_source=PRIVATE/"finagent_amzn_source_completion_20260922_1627"
    for name in ["audit.py","audit.log","validation.json","scheduler.txt"]:paths.add(amzn_source/name)
    amzn_run=PRIVATE/"finagent_AMZN"
    for name in ["completion.json","manual_continuation_validation.json","wrapper.json","live_prefix_gate.json"]:paths.add(amzn_run/name)
    final_setup=PRIVATE/"final_equity_launch_20260922"
    paths.add(ROOT/"scripts/run_final_equity_accounts_v3_guarded.py")
    for name in ["protocol.json","freeze.py","preparation_diagnosis.json","actual_incomplete_replay_rejection.json","submit_once.py","pre_submission_admission.json","submission_intent.json","submission_response.json","jobs.json","runtime_preflight.json","completion.json"]:
        if (final_setup/name).exists():paths.add(final_setup/name)
    if (PUBLIC/"finagent_amzn_full_replay_completion.json").exists():
        paths.add(PUBLIC/"finagent_amzn_full_replay_completion.json")
        amzn_replay=PRIVATE/"finagent_amzn_full_replay_20260922_1627"
        for name in ["audit.py","audit.log","validation.json","scheduler.txt"]:paths.add(amzn_replay/name)
        paths.add(PRIVATE/"finagent_AMZN_full_replay_validation.json")
        for name in ["completion.json","manual_continuation_validation.json"]:paths.add(PRIVATE/"finagent_AMZN_offline_replay"/name)
    paths.add(PUBLIC/"final_equity_accounts_completion_v3.json")
    paths.add(PUBLIC/"final_equity_report_completion_v1.json")
    paths.update(p for p in (PUBLIC/"accounts").iterdir() if p.is_file())
    paths.update(p for p in (PUBLIC/"final_equity_report_v1").rglob("*") if p.is_file())
    final_completed=PRIVATE/"final_equity_completion_20260922_1627"
    for name in ["audit.py","audit.log","validation.json","scheduler.txt","archive_request_preflight.json","archive_request_preflight.log","report_preservation.json","seal_report.py","update_reporting.py"]:paths.add(final_completed/name)
    for name in ["build_final_equity_report_v1.py","validate_final_equity_report_v1.py"]:paths.add(ROOT/"scripts"/name)
    paths.add(PRIVATE/"final_equity_account_jobs_v3_20260922.json")
    paths.add(PUBLIC/"manuscript_completion_v2.json")
    paths.update(p for p in (PUBLIC/"manuscript_v2").rglob("*") if p.is_file())
    manuscript_setup=PRIVATE/"manuscript_v2_setup_20260922"
    for name in ["prepare_inputs.py","prepare.log","prepare_builder.py","refine_presentation.py","presentation_refinement.json","render_for_qa.py","render_final.py","render_sealed.py","render_comparison.json","render_sealed_comparison.json","build.log","build_v2.log","build_final.log","build_sealed.log","validation.log","validation_final.log","validation_sealed.log","historical_method_bindings.json","locked_budget.json","seal.py","preservation.json"]:paths.add(manuscript_setup/name)
    for name in ["build_fidelity_manuscript_v2.py","validate_fidelity_manuscript_v2.py"]:paths.add(ROOT/"scripts"/name)
    package_setup=PRIVATE/"final_package_setup_20260922"
    for name in ["fidelity_package_core_v2.py","package_fidelity_completion_v2.py","restore_fidelity_archive_v2.py","dispatch_fidelity_package_v1.py"]:paths.add(ROOT/"scripts"/name)
    for name in ["package_protocol.json","preparation_status.json","hash_protocol.json","hash_job.json","large_hash_completion.json","actual_readonly_gate_validation_v2.json","probe_actual_readonly_gates_v2.py","test_core_v2.py","test_packager_v2.py","core_v2_py312.log","core_v2_py39.log","packager_v2_py312.log","packager_v2_py39.log","BUNDLE_README.md","freeze_and_submit.py","package_job.json","public_boundary_preflight.json"]:
        if (package_setup/name).exists():paths.add(package_setup/name)
    paths.add(package_setup/"preserved_v1_lock_failure/diagnosis.json")
    if (PUBLIC/"publication_package_preparation_v1.json").exists():paths.add(PUBLIC/"publication_package_preparation_v1.json")
    stamp = datetime.now(timezone.utc).isoformat()
    snapshot = PRIVATE / "source_review_snapshots" / stamp.replace(":", "").replace("+", "_")
    snapshot.mkdir(parents=True)
    rows = []
    for path in sorted(paths):
        relative = path.relative_to(ROOT)
        data = path.read_bytes()
        if len(data) > 100_000_000:
            raise ValueError("Unexpected large file in methods-only evidence snapshot")
        saved = snapshot / "evidence" / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(data)
        digest = sha256(path)
        if sha256(saved) != digest:
            raise ValueError("Evidence changed during snapshot; do not certify it")
        rows.append(
            {
                "path": str(relative),
                "sha256": digest,
                "bytes": len(data),
                "snapshot_path": str(saved.relative_to(ROOT)),
                "private_reference_only": str(relative).startswith("artifacts/"),
            }
        )
    document = {
        "status": "interim_methods_evidence_snapshot_not_human_review",
        "created_utc": stamp,
        "packet_sha256": sha256(packet),
        "evidence": rows,
        "human_attestation": None,
        "source_runs_and_final_bundle_complete": False,
        "new_full_paper_reproduction_claims": 0,
        "selection": "Methods/protocols and currently available validation artifacts; no economic-performance selection. Incomplete source trials and proofs remain incomplete in progress.json.",
        "snapshot_scope": "Exact copies in the durable project allocation, verified against their hashes. This is not the final full study bundle or an independent off-allocation archive.",
        "snapshot": str(snapshot.relative_to(ROOT)),
    }
    atomic_json(snapshot / "source_review_evidence_manifest.json", document)
    atomic_json(PUBLIC / "source_review_evidence_manifest.json", document)
    for row in rows:
        if sha256(ROOT / row["snapshot_path"]) != row["sha256"]:
            raise ValueError("Snapshot copy verification failed")
    atomic_json(
        snapshot / "validation.json",
        {
            "status": "pass",
            "files": len(rows),
            "human_review": False,
            "manifest_sha256": sha256(snapshot / "source_review_evidence_manifest.json"),
        },
    )
    print("METHOD_PACKET_SNAPSHOT_PASS", len(rows), str(snapshot.relative_to(ROOT)))


if __name__ == "__main__":
    main()
