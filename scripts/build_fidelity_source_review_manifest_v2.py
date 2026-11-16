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
