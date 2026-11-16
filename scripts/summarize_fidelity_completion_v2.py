#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Generate an evidence-linked progress snapshot, never an implied completion certificate."""

from pathlib import Path
import sys
import json
import fcntl
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.publication_llm import CohortOpenRouter
from alpha_evolve.openrouter_budget import atomic_json, sha256

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    proofs = []
    for p in sorted(PRIVATE.glob("*_full_replay_validation.json")):
        d = json.loads(p.read_text())
        if d["status"] != "pass":
            raise ValueError("Failed replay proof " + str(p))
        proofs.append(
            {
                "run": d["original"],
                "records": d["records"],
                "maximum_numeric_difference": d["maximum_numeric_difference"],
                "path": str(p.relative_to(ROOT)),
                "sha256": sha256(p),
            }
        )
    guards = []
    for p in sorted(PRIVATE.glob("finmem_*_offline_replay/guardrail_validation_events.json")):
        d = json.loads(p.read_text())
        guards.append(
            {
                "run": p.parent.name,
                "training_failures": d["training_validation_failures"],
                "test_failures": d["test_validation_failures"],
                "events": len(d["events"]),
            }
        )
    with (ROOT / "runs/economic_fidelity/openrouter/project_spend.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads((ROOT / "runs/economic_fidelity/openrouter/project_spend.json").read_text())
    spend = {
        name: CohortOpenRouter.totals(ledger, name)[1]
        for name in sorted({r["study"] for r in ledger["calls"].values()})
        if name.startswith("fidelity_v2")
    }
    total = CohortOpenRouter.totals(ledger, "snapshot_only")[0]
    evidence = json.loads((PUBLIC / "paper_dispositions.json").read_text())
    data = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress",
        "validated_new_replays": proofs,
        "validated_new_records": sum(r["records"] for r in proofs),
        "guardrail_events": guards,
        "project_committed_usd_including_uncertainty": total,
        "v2_study_committed_usd": spend,
        "project_soft_stop_usd": 450,
        "project_hard_ceiling_usd": 500,
        "all_papers_evidence_linked": evidence["paper_count"],
        "full_original_paper_replications_established": 0,
        "account_preview": "paper_runs/fidelity_completion_v2/account_preview/validation.json",
        "remaining": [
            "Finish FinAgent source settings/asset breadth and exact cache/preserved-prefix checks",
            "Preserve completed EFS sources, matched pools, two economic effects and diagnostic boundaries in the final publication",
            "Finish the separately declared QuantaAlpha paper-parameter source/replay/causality/economic sensitivity; released-default seven-task analysis is complete",
            "Preserve the completed all20 Alpha observed-history sensitivity and its strict20-by5/four-primary/54-secondary unavailability in the final publication",
            "Finish conditional inference, updated source review packets, v2 manuscript/report and immutable bundles",
            "Independent human source review remains external",
        ],
        "scope": "All69 papers remain separately tracked. Audit closure, surrogate runs, source components, and adapted native executions are not full-paper replication.",
    }
    factor_runs = []
    for name in ["alphaagent_bounded_source_gpt4turbo_01", "alphaagent_bounded_paper_gpt35_01", "quantaalpha_bounded"]:
        run = PRIVATE / name
        replay_path = run / "full_replay_validation.json"
        account_path = run / "independent_accounts/validation.json"
        manifest_path = run / "used_factor_manifest.json"
        if not all(path.exists() for path in [replay_path, account_path, manifest_path]):
            continue
        replay, account, manifest = [
            json.loads(path.read_text()) for path in [replay_path, account_path, manifest_path]
        ]
        digests = {row["sha256"] for row in manifest["programs"]}
        checked = sum(
            (run / "causality_full_universe" / (digest + ".json")).exists()
            and json.loads((run / "causality_full_universe" / (digest + ".json")).read_text())["status"] == "pass"
            for digest in digests
        )
        factor_runs.append(
            {
                "run": name,
                "full_replay": replay["status"],
                "independent_accounts": account["status"],
                "native_backtests": len(account["experiments"]),
                "source_used_programs": len(digests),
                "full_universe_causality_pass": checked,
                "source_manifest_sha256": sha256(manifest_path),
            }
        )
    data["bounded_factor_pilots"] = factor_runs
    data["efs_validated_replays"] = [
        {"trial": path.parents[1].name, "sha256": sha256(path), "status": json.loads(path.read_text())["status"]}
        for path in sorted((PRIVATE / "efs").glob("*/offline_replay/validation.json"))
    ]
    efs_source_path = PUBLIC / "efs_source_cohort_completion.json"
    if efs_source_path.exists():
        efs_source = json.loads(efs_source_path.read_text())
        if sha256(ROOT / efs_source["private_evidence_path"]) != efs_source["private_evidence_sha256"]:
            raise ValueError("EFS source cohort audit binding changed")
        data["efs_complete_source_cohort"] = {
            "status": efs_source["status"], "trials": efs_source["trial_count"],
            "sha256": sha256(efs_source_path), "economic_pool_completion_inferred": False,
        }
    observed_path = PUBLIC / "alpha_observed_source_progress.json"
    if observed_path.exists():
        observed = json.loads(observed_path.read_text())
        if sha256(ROOT / observed["catalogue_path"]) != observed["catalogue_sha256"]:
            raise ValueError("Observed Alpha source catalogue binding changed")
        data["alpha_observed_source_population"] = observed
    observed_library_path = PUBLIC / "alpha_observed_library_validation.json"
    if observed_library_path.exists():
        observed_library = json.loads(observed_library_path.read_text())
        if sha256(ROOT / observed_library["private_validation_path"]) != observed_library["private_validation_sha256"]:
            raise ValueError("Observed Alpha materialization audit binding changed")
        if sha256(PRIVATE / "alphaagent_observed20_fixed_library/library_manifest.json") != observed_library["manifest_sha256"]:
            raise ValueError("Observed Alpha materialized manifest changed")
        data["alpha_observed_materialized_library"] = observed_library
    observed_native_path = PUBLIC / "alpha_observed_native_validation.json"
    if observed_native_path.exists():
        observed_native = json.loads(observed_native_path.read_text())
        if sha256(ROOT / observed_native["private_validation_path"]) != observed_native["private_validation_sha256"]:
            raise ValueError("Observed Alpha native audit binding changed")
        data["alpha_observed_native_arms"] = observed_native
    data["native_plumbing_accounts"] = [
        {"run": path.parents[1].name, "status": json.loads(path.read_text())["status"]}
        for path in sorted(PRIVATE.glob("*_plumbing_*/independent_accounts/validation.json"))
    ]
    data["quanta_paper_parameter_jobs"] = (
        json.loads((PRIVATE / "quantaalpha_paper_parameters_jobs.json").read_text())
        if (PRIVATE / "quantaalpha_paper_parameters_jobs.json").exists()
        else None
    )
    data["corrected_alphaagent_paper_trials_completed"] = sum(
        (PRIVATE / ("alphaagent_rounds_paper_gpt35_%02d" % i) / "execution_exit.json").exists()
        and json.loads((PRIVATE / ("alphaagent_rounds_paper_gpt35_%02d" % i) / "execution_exit.json").read_text())[
            "status"
        ]
        == "native_round_budget_exhausted"
        for i in range(1, 21)
    )
    data["corrected_alphaagent_paper_trials_target"] = 20
    trial_gates = []
    for i in range(1, 21):
        run = PRIVATE / ("alphaagent_rounds_paper_gpt35_%02d" % i)
        row = {
            "trial": i,
            "execution_complete": False,
            "attempt_budget_closed": False,
            "terminal_final_attempt_failure": False,
            "full_replay_pass": False,
            "accounts_pass": False,
            "causality_all_programs_pass": False,
        }
        exit_path = run / "execution_exit.json"
        if exit_path.exists():
            done = json.loads(exit_path.read_text())
            row.update(
                execution_complete=done["status"] == "native_round_budget_exhausted" and done["attempted_rounds"] == 5,
                source_execution_status=done["status"],
                actual_attempted_rounds=done["attempted_rounds"],
                unattempted_round_indices=done.get("unattempted_round_indices", []),
                failed_attempted_round_indices=done.get("failed_round_indices", []),
                execution_exit_sha256=sha256(exit_path),
            )
            row["attempt_budget_closed"] = row["execution_complete"]
            if done["status"] == "native_final_attempt_failed":
                from alpha_constructor_abort_v3 import validate_five as validate_alpha_five_attempts
                validate_alpha_five_attempts(run, require_replay=False)
                row["attempt_budget_closed"] = True
                row["terminal_final_attempt_failure"] = True
        for filename, key in [
            ("full_replay_validation.json", "full_replay_pass"),
            ("observed_abort_replay_validation.json", "observed_early_abort_replay_pass"),
            ("independent_accounts/validation.json", "accounts_pass"),
        ]:
            path = run / filename
            if path.exists():
                row[key] = json.loads(path.read_text())["status"] == "pass"
                row[key + "_sha256"] = sha256(path)
        path = run / "used_factor_manifest.json"
        if path.exists():
            manifest = json.loads(path.read_text())
            digests = {p["sha256"] for p in manifest["programs"]}
            row["used_programs"] = len(digests)
            row["causality_programs_pass"] = sum(
                (run / "causality_full_universe" / (h + ".json")).exists()
                and json.loads((run / "causality_full_universe" / (h + ".json")).read_text())["status"] == "pass"
                for h in digests
            )
            row["causality_all_programs_pass"] = bool(digests) and row["causality_programs_pass"] == len(digests)
        trial_gates.append(row)
    data["corrected_alphaagent_trial_gates"] = trial_gates
    data["corrected_alphaagent_early_aborts"] = [r for r in trial_gates if r.get("source_execution_status") == "native_early_abort"]
    data["strict_alpha_five_attempt_comparison_blocked"] = bool(data["corrected_alphaagent_early_aborts"])
    data["corrected_alphaagent_attempt_budgets_closed"] = sum(r["attempt_budget_closed"] for r in trial_gates)
    data["corrected_alphaagent_terminal_final_failures"] = sum(r["terminal_final_attempt_failure"] for r in trial_gates)
    data["corrected_alphaagent_replay_and_accounts_pass"] = sum(
        r["attempt_budget_closed"] and r["full_replay_pass"] and r["accounts_pass"] for r in trial_gates
    )
    data["corrected_alphaagent_all_gates_pass"] = sum(
        r["attempt_budget_closed"] and r["full_replay_pass"] and r["accounts_pass"] and r["causality_all_programs_pass"]
        for r in trial_gates
    )
    data["secondary_native_analysis"] = {
        "protocol": "paper_runs/fidelity_completion_v2/native_secondary_analysis_protocol.json",
        "jobs": json.loads((PRIVATE / "native_oos_followthrough_jobs.json").read_text())["jobs"],
        "completed_cases": [
            case
            for case in ["quantaalpha", "alphaagent", "all"]
            if (PUBLIC / ("native_secondary_oos_" + case) / "completion.json").exists()
        ],
        "scope": "Every7Quanta task/20Alpha trial retained; explicit common baselines,54opening-information secondary comparisons with conservative multiplicity. One market history per case; no selected winner.",
    }

    data["transport_recoveries"] = [
        {
            "manifest": str(path.relative_to(ROOT)),
            "requests": len(record["requests"]),
            "retained_usd": record["retained_usd"],
        }
        for path in sorted(PRIVATE.glob("transport_recovery*/recovery.json"))
        for record in [json.loads(path.read_text())]
    ]
    data["new_period_comparisons"] = [
        {"run": path.parent.name, **json.loads(path.read_text())}
        for path in sorted(PRIVATE.glob("*_oos_*/completion.json"))
    ]
    result_path = PUBLIC / "native_grouped_oos_quantaalpha/comparisons.json"
    if result_path.exists():
        result = next(row for row in json.loads(result_path.read_text()) if row["role"] == "primary_economic")
        data["quanta_later_period_economic_result"] = {
            key: result[key]
            for key in [
                "full_sample_annualized_effect",
                "primary_ci_low",
                "primary_ci_high",
                "family_adjusted_p",
                "multiplicity_method",
            ]
        }
        data["quanta_later_period_economic_result"]["scope"] = (
            "Partial-case exploratory China/Alpha158 comparison with opening-information eligibility; not JKP132 attribution or a completed two-case family."
        )
    secondary_path = PUBLIC / "native_secondary_oos_quantaalpha/completion.json"
    if secondary_path.exists():
        completed = json.loads(secondary_path.read_text())
        if completed["status"] != "complete_case_partial_secondary_family":
            raise ValueError("Unexpected Quanta secondary result status")
        rows = json.loads((secondary_path.parent / "comparisons.json").read_text())
        rows = [r for r in rows if r["execution"] == "opening_information" and r["baseline"] == "alpha158"]
        if sorted(r["unit"] for r in rows) != list(range(7)):
            raise ValueError("Incomplete task result panel")
        from statistics import median

        data["quanta_secondary_task_result"] = {
            "tasks": 7,
            "negative_full_sample_mean_tasks": sum(r["full_sample_annualized_effect"] < 0 for r in rows),
            "median_full_sample_annualized_increment": median(r["full_sample_annualized_effect"] for r in rows),
            "positive_corrected_significance_flags": sum(
                r["positive_secondary_pointwise99_and_family_p_below001"] for r in rows
            ),
            "completion_sha256": sha256(secondary_path),
            "scope": "Complete seven-task China/Alpha158 secondary case, partial54comparison family; shared market history, no selected winner or full-paper claim.",
        }
    ta_path = PRIVATE / "tradingagents_GOOGL_single_news_source/completion.json"
    if ta_path.exists():
        ta_done = json.loads(ta_path.read_text())
        replay_path = PRIVATE / "tradingagents_GOOGL_single_news_source_full_replay_validation.json"
        account_path = PUBLIC / "tradingagents_news_accounts/completion.json"
        data["tradingagents_single_news_source"] = {
            "source_status": ta_done["status"],
            "completion_sha256": sha256(ta_path),
            "full_replay_status": json.loads(replay_path.read_text())["status"] if replay_path.exists() else "pending",
            "separate_account_status": json.loads(account_path.read_text())["status"]
            if account_path.exists()
            else "pending",
            "original_cohort_preserved": True,
        }
    observed_analysis = PUBLIC / "alpha_observed_history_sensitivity"
    if (observed_analysis / "completion.json").exists():
        completed = json.loads((observed_analysis / "completion.json").read_text())
        if completed["status"] != "exploratory_observed_history_sensitivity_complete_not_primary":
            raise ValueError("Wrong observed Alpha analysis scope")
        for name, digest in completed["outputs"].items():
            if sha256(observed_analysis / name) != digest:
                raise ValueError("Completed observed Alpha analysis changed")
        result = next(r for r in json.loads((observed_analysis / "comparisons.json").read_text()) if r["execution"] == "opening_information")
        data["alpha_observed_economic_result"] = {k: result[k] for k in ["full_sample_annualized_effect", "annualized_arithmetic_effect", "primary_ci_low", "primary_ci_high", "group_t_p_two_sided", "scope", "strict_primary_eligibility", "project_family_significance_claim"]}
        data["alpha_observed_economic_result"]["completion_sha256"] = sha256(observed_analysis / "completion.json")
    for name, key in [("finagent_amzn_http500_disposition.json", "finagent_amzn_failure"), ("efs_deep_pool_validation.json", "efs_deep_pool_validation"), ("efs_economic_completion.json", "efs_economic_completion")]:
        path = PUBLIC / name
        if path.exists():
            data[key] = json.loads(path.read_text())
    archive_policy = PUBLIC / "archive_request_handling_v2.json"
    if archive_policy.exists():
        policy = json.loads(archive_policy.read_text())
        if sha256(ROOT / policy["current_probe_path"]) != policy["current_probe_sha256"]:
            raise ValueError("Archive preflight evidence binding changed")
        data["archive_request_preflight"] = {k: policy[k] for k in ["current_probe_status", "current_probe_sha256", "retained_reservation_total_usd", "archive_created", "final_publication_ready"]}
    googl_status = PUBLIC / "finagent_googl_xml_repair_status.json"
    if googl_status.exists():
        data["finagent_googl_xml_repair"] = json.loads(googl_status.read_text())
    atomic_json(PUBLIC / "progress.json", data)
    aggregates = json.loads((PUBLIC / "account_preview/aggregate_performance.json").read_text())
    lookup = {(r["case"], r["arm"]): r for r in aggregates}
    text = [
        "# Fidelity completion v2 — work in progress",
        "",
        "The reopened fidelity work is not complete. The frozen six-case v1 package remains unchanged, and no full original-paper replication across all69 papers is claimed.",
        "",
        "## Verified execution",
        "",
        f"- {len(proofs)} new equity source runs passed full read-only cached replay: {data['validated_new_records']:,} records. Every economic, timing, reasoning, memory, and request-identity field matched.",
        "- Four added FinMem assets complete the five-equity breadth when combined with the frozen TSLA trajectory; there is one trajectory per equity, not the paper’s five-trial experiment.",
        "- TradingAgents completed AAPL, GOOGL and AMZN using the released deep/quick model roles. Historical inputs/model snapshots and portfolio sizing remain disclosed adaptations.",
        "- Independent price/share accounting matches the target-weight accounting to floating-point precision. Combined assets receive equal initial capital and drift without daily cross-account rebalancing.",
        "- The bounded QuantaAlpha source search passed full cached replay, independent accounting for seven native tasks, and full-universe causality checks for all sixteen consumed programs. Its pooled and all-seven-task later-period comparisons are complete; the separate paper-parameter sensitivity remains in progress.",
        "- Bounded AlphaAgent pilots passed full cached replay and accounting: four successful control backtests and five paper-model backtests. All eight control and seven paper-model programs passed full-universe code/matrix/prefix checks. Corrected five-attempted-round replays preserve the failed fifth control round.",
        f"- Corrected AlphaAgent paper-model trials: {data['corrected_alphaagent_paper_trials_completed']}/20 native source returns; {data['corrected_alphaagent_attempt_budgets_closed']}/20 five-attempt budgets closed, including {data['corrected_alphaagent_terminal_final_failures']} explicitly retained terminal final-attempt failure. {data['corrected_alphaagent_replay_and_accounts_pass']}/20 pass full replay and independent accounts, and {data['corrected_alphaagent_all_gates_pass']}/20 have all source-used program causality proofs. Failed attempts are never credited as successful backtests or replaced. The separately verified early-abort histories do not receive five-attempt credit. See [terminal failure protocol](alphaagent_final_attempt_failure_protocol.json).",
        "- The original secondary protocol specifies seven Quanta tasks and twenty Alpha trials, reused baselines and a54-contrast opening-information family. The Quanta case is complete; the full family is unavailable because early Alpha aborts fail its strict source scope. The observed-history sensitivity does not fill that gap. See native_secondary_analysis_protocol.json.",
        "- Confirmed transport failures were recovered with exact request identities, preserved pre-failure histories, and all missing-response reservations retained. EFS replay/pooling dependencies now track individual trials instead of the failed whole array.",
        "- All eight search-period source4/Alpha158 models, portfolios and independent accounts pass. Lost scalar logs were recovered from saved native artifacts without retraining; the full paired pipeline check passes.",
        "- QuantaAlpha’s four later-period native accounts and four opening-information sensitivities now pass for963sessions. The opening variant fixes the timing of eligibility inputs while preserving predictions, costs and portfolio rules. It remains a uniform price-limit proxy, not a full exchange simulation.",
        "- Synthetic calibration found undercoverage in the original bootstrap. It is retained as diagnostic; the conservative four-group99percent method is calibrated separately, with assumptions and Monte Carlo uncertainty explicit.",
        "- The released QuantaAlpha factor YAML is not wired into its constructor. Runtime settings are documented in quantaalpha_executed_settings_clarification.json. A separate GPT-5.2 paper-parameter source sensitivity is in progress with explicit active settings, guarded five-total-phase stopping, and the same shared75USDcap; full-paper reproduction is not claimed.",
        "",
        "## Descriptive account preview",
        "",
        "These are cumulative returns from the currently complete cohorts with next-close execution and10bp per traded notional. They are not significance results, JKP residual alphas, or an estimate over independent model trials.",
        "",
        "| Cohort | Sessions | Native | Matched buy-and-hold | Difference |",
        "|---|---:|---:|---:|---:|",
    ]
    for case, label in [
        ("finmem", "FinMem, five equity accounts"),
        ("tradingagents", "TradingAgents, three equity accounts"),
    ]:
        a, b = lookup[(case, "native")], lookup[(case, "buy_hold_matched_clock")]
        x, y = 100 * (a["ending_wealth"] - 1), 100 * (b["ending_wealth"] - 1)
        text.append(f"| {label} | {a['observations']} | {x:.3f}% | {y:.3f}% | {x - y:+.3f}pp |")
    if data["strict_alpha_five_attempt_comparison_blocked"]:
        early = ", ".join(str(r["trial"]) for r in data["corrected_alphaagent_early_aborts"])
        text += ["", f"The frozen Alpha twenty-trial, five-attempt comparison is unavailable: early-abort trials {early} contain unattempted rounds. Their observed histories have separate replay, account and program-proof evidence; that evidence cannot create missing attempts. No trial is omitted or replaced. The strict pooled job remains held, and the original four-primary/54-secondary families cannot be completed by substituting a sensitivity. See [early-abort disposition](alphaagent_early_abort_disposition.json).", ""]
    if "alpha_observed_source_population" in data:
        a = data["alpha_observed_source_population"]
        text += ["", f"All{len(a['verified_trials'])} original Alpha outcomes pass the separate observed-history source gate: {a['actual_attempted_rounds']} actual attempts, {a['unattempted_rounds']} unattempted rounds and {a['successful_native_histories']} completed native histories. These are not20 independent market histories. The separate economic chain was submitted after the complete source gate; submission alone does not establish a result. See [source evidence and recorded jobs](alpha_observed_source_progress.json).", ""]
    if "alpha_observed_materialized_library" in data:
        a = data["alpha_observed_materialized_library"]
        text += ["", f"Alpha's complete observed-history library is materialized and independently checked: {a['source_program_use_instances']} program uses, {a['distinct_program_hashes']} distinct program hashes and {a['distinct_expression_columns']} exact-expression columns over {a['matrix_rows']:,} rows. All saved columns match the combined matrix exactly, and both serialized matrices match. The {a['duplicate_expression_programs']} expression duplicates have identical values. Raw inputs retain {a['raw_infinite_cells_in_unique_matrix']} infinite cells; processed-feature checks and economic results require the separate model/account stages. See [materialization audit](alpha_observed_library_validation.json).", ""]
    if "alpha_observed_native_arms" in data:
        a = data["alpha_observed_native_arms"]
        text += ["", "Both Alpha observed-history native fits and independently reconstructed accounts now pass for238 sessions, with matched nonfeature settings and158/304 processed features. Processed infinities are zero. The augmented arm retains2 constant-or-missing columns in each segment and2,206,039/372,206/394,459 missing cells in train/validation/test, respectively. These are preserved native inputs, not silently repaired features. Native eligibility remains diagnostic; opening-information replay and separate paired analysis determine the economic sensitivity. See [native model/account bindings](alpha_observed_native_validation.json).", ""]
    if "alpha_observed_economic_result" in data:
        a = data["alpha_observed_economic_result"]
        text += ["", f"The separately declared all20 observed-history Alpha economic sensitivity is complete: opening-information full-sample annualized mean increment {100*a['full_sample_annualized_effect']:+.3f}pp/year, grouped99% interval [{100*a['primary_ci_low']:.3f}, {100*a['primary_ci_high']:.3f}]pp, descriptive raw p={a['group_t_p_two_sided']:.6f}. The wide interval includes zero and the+2pp margin. This does not replace strict Alpha or enter the original four/54 families. See the [complete observed-history report](alpha_observed_history_report/VISUAL_REPORT.md).", ""]
    if "finagent_amzn_failure" in data:
        text += ["", "FinAgent AMZN stopped on an embedding HTTP500 after220 complete training records. Its exact failed request and all prefixes are preserved; the missing-response reservation remains charged. AMZN replay26502919 and final-equity job26589541 were cancelled without execution. A narrow manual retry exception is awaiting the user's response; other FinAgent sources continue. See [failure disposition](finagent_amzn_http500_disposition.json).", ""]
    if "efs_deep_pool_validation" in data:
        text += ["", "The DeepSeek EFS three-trajectory pool is complete:2198 union functions and eight independently reconciled1510-day/72-month account paths. Both paired grammar comparisons are complete; the original four-case family remains partial. See [DeepSeek pool audit](efs_deep_pool_validation.json).", ""]
    if "efs_economic_completion" in data:
        text += ["", "Both EFS matched-pool effects are complete and inconclusive at2pp: GPT+4.128pp/year with99% interval[-17.462,+25.718]pp; DeepSeek+2.729pp/year with interval[-58.209,+63.667]pp. Both conservative4p bounds equal1.0. The collector includes3of4 original cases, retaining strict Alpha as missing. Identified low-dimensional and regularized JKP diagnostics do not establish unrestricted JKP132 alpha. See the [completed EFS case report](efs_pooled_report/VISUAL_REPORT.md).", ""]
    if "archive_request_preflight" in data:
        text += ["", "A separate read-only archive preflight recognizes the four exactly witnessed terminal Alpha charges totaling0.116085USD while retaining their original reserved status. Missing final source closures, unclassified requests and unsupported statuses block snapshot readiness. The actual probe remains blocked; no archive or retry authorization was created. See [archive request handling](archive_request_handling_v2.json).", ""]
    if "finagent_googl_xml_repair" in data:
        text += ["", "FinAgent GOOGL stopped on a response-format parser error after250 training and32 validation records. The returned response is intact in the canonical journal. A narrowly witnessed markup-only alias preserves all text; network-disabled prefix probe26674582 is queued, not validated at runtime. No live continuation or replacement response is authorized by that software readiness. See [GOOGL diagnosis](finagent_googl_xml_repair_status.json).", ""]
    if "efs_complete_source_cohort" in data:
        e = data["efs_complete_source_cohort"]
        text += ["", f"All{e['trials']} EFS source trajectories and exact cached replays pass the intrinsic290-round, output, holdings, preserved-prefix and frozen-engine gates. Source, pool and paired-economic evidence are separately recorded; source validation alone does not certify economic completion. See [complete EFS source cohort](efs_source_cohort_completion.json).", ""]
    if "quanta_later_period_economic_result" in data:
        q = data["quanta_later_period_economic_result"]
        text += [
            "",
            "## First later-period result",
            "",
            f"QuantaAlpha’s frozen library adds {100 * q['full_sample_annualized_effect']:.2f} percentage points of annualized mean net return over Alpha158 under opening-information eligibility. The grouped99percent interval is [{100 * q['primary_ci_low']:.2f}, {100 * q['primary_ci_high']:.2f}]pp; the conservative partial-family adjusted p-value is {q['family_adjusted_p']:.3f}. This is inconclusive at the2ppmargin and does not establish significant alpha. It is a Chinese-market Alpha158 comparison, not JKP132 attribution. See [case analysis](native_grouped_oos_quantaalpha/completion.json).",
            "",
        ]
    if "quanta_secondary_task_result" in data:
        q = data["quanta_secondary_task_result"]
        text += [
            "",
            "## Complete seven-task sensitivity",
            "",
            f"All seven QuantaAlpha task libraries completed native and opening-information evaluation. Under opening-information eligibility, {q['negative_full_sample_mean_tasks']}/7 have negative full-sample mean increments over Alpha158; the median is {100 * q['median_full_sample_annualized_increment']:+.2f}pp/year. None establishes a positive increment after the prespecified secondary correction. Every task is retained; model tasks share one market history. See the [figure-led case report](quantaalpha_later_period_report/VISUAL_REPORT.md) and [complete secondary case](native_secondary_oos_quantaalpha/completion.json).",
            "",
        ]
    if "tradingagents_single_news_source" in data:
        t = data["tradingagents_single_news_source"]
        text += [
            "",
            f"TradingAgents single-company-news sensitivity: source {t['source_status']}; strict replay {t['full_replay_status']}; separate descriptive accounts {t['separate_account_status']}. The original three-equity results remain preserved. See the [separate descriptive report](tradingagents_news_report/REPORT.md).",
            "",
        ]
    text += [
        "",
        "## Remaining fidelity limits",
        "",
        f"All{evidence['paper_count']} papers now have linked, hashed native-audit evidence and paper-specific residual gaps in [paper_dispositions.json](paper_dispositions.json). The audit review does not certify that every feasible new experiment has been exhausted. The bounded factor pilots now have replay, accounting and causality evidence; all twenty Alpha source outcomes and their separately scoped later-period evaluation are complete, while the strict five-attempt comparison remains unavailable.",
        "",
        "Read-only FinMem instrumentation recorded259 training validation failures and1test validation failure across the four added assets. The released fallback behavior was preserved. Nonempty fallback reflection records must not be reported as successful guardrail validation.",
        "",
        "Several copied recipes retain historical v1 narrative fields. [recipe_metadata_clarifications.json](recipe_metadata_clarifications.json) identifies those fields and the actual v2 execution scope without changing frozen recipes or outcomes.",
        "",
        "The sealed September8–9 prospective observation was settled without a new model call: after entry fees, LLM−1.4621%, grammar−1.3612%, initial−1.1659%, equal-weight−0.7305%. One observation provides no significance or continuous-portfolio conclusion.",
        "",
        f"The canonical project ledger commits ${total:.6f}, including retained uncertain reservations, against the unchanged $450 soft stop/$500 ceiling. Replays make no paid calls.",
        "",
        "The full original v2 family is unavailable because strict Alpha is missing. Feasible partial-family inference, final source-review evidence freeze, manuscript and reproducibility bundles remain pending. The interim source review packet has been updated; it is not human attestation. Independent human source review cannot be supplied by another automated audit.",
        "",
        "Machine-readable state: [progress.json](progress.json), [account checks](account_preview/validation.json), [EFS pooling protocol](efs_pool_protocol.json), [QuantaAlpha evaluation protocol](quantaalpha_evaluation_protocol.json).",
        "",
    ]
    (PUBLIC / "STATUS.md").write_text("\n".join(text))
    print(
        json.dumps(
            {
                "new_replays": len(proofs),
                "records": data["validated_new_records"],
                "committed_usd": total,
                "v2_studies": spend,
            }
        )
    )


if __name__ == "__main__":
    main()
