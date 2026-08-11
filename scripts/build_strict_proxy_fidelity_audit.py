#!/usr/bin/env python3
"""Materialize the strict formula-level audit of the 50 legacy JKP proxies."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "paper_runs"
    / "idea_replications"
    / "paper_derived_candidate_replication_ledger.csv"
)
OUT = (
    ROOT
    / "paper_runs"
    / "submission_evidence"
    / "strict_proxy_fidelity_audit"
)

# The ordering and grades reproduce the independent strict review supplied for
# the revision. The source ledger supplies the tested formula and source-idea
# text; this script fails if the legacy registry changes underneath the review.
GRADE_BY_CANDIDATE = {
    "efs_momentum_low_vol_breakout": "C",
    "efs_short_reversal_low_noise": "D",
    "efs_sparse_top5_momentum_low_vol": "C",
    "repo_alphaagent_decay_resistant_quality": "D",
    "code_quantaalpha_self_evolving_factor": "D",
    "repo_quantevolver_return_sharpe_proxy": "C",
    "repo_rd_agent_factor_model_compact_ensemble": "C",
    "alpha_jungle_price_volume_momentum": "C",
    "alpha_jungle_volatility_compression_trend": "C",
    "paper_factorminer_memory_diverse_library": "D",
    "paper_cogalpha_code_evolved_hybrid": "D",
    "fama_value_momentum_interpretable": "D",
    "paper_alpha_gpt_interactive_formula": "D",
    "paper_alpha_gpt2_full_pipeline": "D",
    "paper_chain_of_alpha_formula_chain": "U",
    "paper_factormad_debate_interpretable": "U",
    "alphalogics_value_quality_growth": "D",
    "paper_alphaagentevo_evolved_seed": "D",
    "code_alpha_r1_reasoning_screen": "D",
    "alphacrafter_full_stack_multifactor": "C",
    "paper_llmfactor_explainable_price_news": "D",
    "paper_factorengine_program_knowledge": "D",
    "code_tradingagents_multi_agent": "D",
    "contesttrade_internal_contest_trailing_sharpe": "D",
    "repo_quantagent_hft_price_pattern": "D",
    "quantagent_three_soldiers_trend": "C",
    "quantagent_volatility_breakout": "C",
    "code_alphaquanter_tool_orchestrated_rl": "D",
    "code_finmem_memory_trend": "D",
    "repo_fincon_cvar_risk_controlled_allocator": "D",
    "paper_finagent_multimodal_generalist": "D",
    "paper_flag_trader_gradient_policy": "D",
    "mm_drex_dynamic_router_proxy": "D",
    "repo_trading_r1_risk_adjusted_reasoning": "D",
    "paper_janus_q_event_driven_proxy": "D",
    "paper_timi_minutes_technical_proxy": "D",
    "alphaagents_risk_averse_quality_lowrisk": "D",
    "alphaagents_risk_neutral_fundamental_momentum": "D",
    "marketsense_value_momentum_quality": "C",
    "paper_mountainlion_multimodal_allocation": "D",
    "paper_p1gpt_structured_workflow": "C",
    "finvision_trend_dip_risk_control": "C",
    "guru_altman_distress_avoidance": "D",
    "guru_buffett_quality_compounder": "C",
    "guru_equal_weight_style_ensemble": "D",
    "guru_graham_deep_value_defensive": "C",
    "guru_greenblatt_magic_formula": "D",
    "guru_piotroski_fscore_proxy": "C",
    "paper_quantagents_risk_controlled_system": "D",
    "hedgeagents_balanced_lowrisk_alpha": "D",
}

GRADE_MEANING = {
    "A": "faithful paper or system replication",
    "B": "faithful disclosed component",
    "C": "recognizable idea but materially changed",
    "D": "materially inconsistent with the source",
    "U": "source unavailable for strict verification",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    with SOURCE.open(newline="", encoding="utf-8-sig") as stream:
        source_rows = {row["candidate_id"]: row for row in csv.DictReader(stream)}
    missing = sorted(set(GRADE_BY_CANDIDATE) - set(source_rows))
    if missing:
        raise RuntimeError(f"strict-audit candidates missing from source ledger: {missing}")

    output_rows = []
    for candidate_id, grade in GRADE_BY_CANDIDATE.items():
        source = source_rows[candidate_id]
        if grade == "C":
            boundary = (
                "theme- or component-level sensitivity only; do not attribute "
                "performance to the paper or native agent"
            )
            mechanical = "no"
        elif grade == "D":
            boundary = (
                "construction diagnostic only; no source-specific performance inference"
            )
            mechanical = "no"
        else:
            boundary = "no source-specific inference"
            mechanical = "unknown"
        output_rows.append(
            {
                "candidate_id": candidate_id,
                "paper_ref": source["paper_ref"],
                "grade": grade,
                "grade_meaning": GRADE_MEANING[grade],
                "legacy_proxy_formula": source["proxy_formula"],
                "legacy_portfolio_rule": source["strategy"],
                "mechanical_changes_only": mechanical,
                "native_agent_output_reproduced": "no",
                "admissible_inference": boundary,
            }
        )

    counts = Counter(row["grade"] for row in output_rows)
    expected = {"A": 0, "B": 0, "C": 15, "D": 33, "U": 2}
    observed = {grade: counts.get(grade, 0) for grade in expected}
    if observed != expected:
        raise RuntimeError(f"strict-audit grade distribution changed: {observed}")

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "legacy_50_proxy_fidelity_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    manifest = {
        "audit_scope": "50 legacy common-task mappings to 40 source papers",
        "audit_standard": (
            "Only frequency, universe, holding period, weights, and costs may "
            "change while retaining the underlying disclosed signal."
        ),
        "grade_counts": expected,
        "jkp_characteristic_composites": 46,
        "common_monthly_portfolio_rule": 47,
        "closer_public_rule_not_used_lower_bound": 39,
        "native_agent_outputs_reproduced": 0,
        "allowed_empirical_use": (
            "researcher-authored construction diagnostics; never performance "
            "evidence about the 40 source papers or their native agents"
        ),
        "source_ledger": str(SOURCE.relative_to(ROOT)),
        "source_ledger_sha256": digest(SOURCE),
        "output_sha256": {csv_path.name: digest(csv_path)},
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
