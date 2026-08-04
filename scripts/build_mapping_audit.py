#!/usr/bin/env python3
"""Expose mapping discretion and run limited within-source mapping sensitivity.

This is an audit of the already-created 62-candidate family. It does not
retroactively make the mappings outcome-blind. The output deliberately marks
where an exact source expression, sign, or portfolio rule was not preserved.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "paper_runs/submission_evidence/frozen_candidate_registry.csv"
DEFAULT_RESULTS = ROOT / "paper_runs/submission_evidence/usa_retrospective_corrected/candidate_primary_results.csv"
DEFAULT_BROAD_RESULTS = ROOT / "paper_runs/submission_evidence/usa_broad_jkp_crossfit/broad_jkp_crossfit_results.csv"
DEFAULT_LOCK = ROOT / "paper_runs/submission_evidence/analysis_lock.json"
DEFAULT_OUTPUT = ROOT / "paper_runs/submission_evidence/mapping_audit"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def holm_adjust(pvalues: np.ndarray) -> np.ndarray:
    pvalues = np.asarray(pvalues, dtype=float)
    order = np.argsort(pvalues)
    adjusted = np.empty_like(pvalues)
    running = 0.0
    m = len(pvalues)
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvalues[idx])
        adjusted[idx] = min(running, 1.0)
    return adjusted


def source_category(source_index: int) -> str:
    if source_index <= 22:
        return "formula_or_factor_method"
    if source_index <= 44:
        return "sequential_trading_or_portfolio_method"
    if source_index <= 51:
        return "benchmark_or_audit"
    return "community_repository"


def mapping_tier(row: pd.Series) -> tuple[str, str, str, str]:
    candidate = str(row["candidate_id"])
    source_index = int(row["source_index"])
    scope = str(row.get("replication_scope", ""))
    if candidate == "repo_quantevolver_return_sharpe_proxy":
        return (
            "M2_released_seed_expression",
            "yes",
            "yes",
            "Released risk-adjusted-momentum seed; portfolio formation and weighting remain evaluator choices.",
        )
    if source_index == 42 or candidate.startswith("guru_"):
        return (
            "M1_named_rule_partial_support",
            "partial",
            "partial",
            "Named-investor screens support broad ingredients, but the exact JKP score and weights are researcher translations.",
        )
    if source_index in {2, 7, 10}:
        return (
            "M1_example_or_motif_partial_support",
            "partial",
            "partial",
            "The source supplies examples or economic motifs, not the complete tested score and portfolio rule.",
        )
    if "from_title" in scope or "low_evidence" in scope:
        note = "Mapping is based on a title, source summary, or low-evidence repository description; exact ingredients are unsupported."
    else:
        note = "The exact characteristics and signs are researcher-selected translations of narrative economic content."
    return "M0_narrative_translation", "no", "no", note


def omitted_components(row: pd.Series) -> str:
    scope = str(row.get("replication_scope", ""))
    omissions = ["language generation/search", "memory/debate/tool use", "native timing and execution"]
    if "no_news" in scope:
        omissions.insert(0, "news/text/event inputs")
    if "hft" in scope or "minutes" in scope:
        omissions.insert(0, "intraday frequency and microstructure execution")
    if "robustness_not_alpha_claim" in scope:
        omissions.insert(0, "source is an audit rather than an alpha-generating method")
    return "; ".join(dict.fromkeys(omissions))


def good_faith_fields(row: pd.Series) -> tuple[str, str, str, str, str, str, str]:
    """Define what a mapping may and may not say about its source.

    The classification is intentionally conservative. A generous common-task
    implementation is not upgraded to a source replication merely because it
    performs well or poorly.
    """
    tier = str(row["mapping_fidelity_tier"])
    strategy = str(row.get("strategy", ""))
    if tier == "M2_released_seed_expression":
        role = "source_grounded_component_test"
        extraction = "released expression preserved; evaluator portfolio rule remains researcher supplied"
        preservation = "released score ingredients and signs"
        boundary = "may evaluate the released seed expression under the common task; not the trained agent or original study"
        anti_strawman = "eligible_for_component_level_interpretation_only"
    elif tier.startswith("M1_"):
        role = "source_grounded_component_test"
        extraction = "named rule, example, or economic motif preserved; complete tested formula not supplied by source"
        preservation = "source-named rule or example-level mechanism"
        boundary = "may evaluate the documented component only; not the native system, full paper, or original metric"
        anti_strawman = "eligible_for_component_level_interpretation_only"
    else:
        role = "exploratory_favorable_stress_test"
        extraction = "narrative mechanism translated by researcher; exact tested formula is not source supplied"
        preservation = "directional economic narrative only"
        boundary = "cannot count as evidence against the source; tests only the researcher's favorable economic translation"
        anti_strawman = "exploratory_only_no_negative_inference"
    if strategy == "long_only_top5_equal_weighted":
        help_rule = (
            "use the source-motivated score in its favorable direction and implement sparse top-five equal weighting; "
            "report gross and cost-adjusted results"
        )
    elif strategy.startswith("long_only"):
        help_rule = (
            "use the source-motivated score in its favorable direction and hold the highest-score names long only; "
            "report gross and cost-adjusted results"
        )
    else:
        help_rule = (
            "use the source-motivated score in its favorable direction and expose the full top-minus-bottom decile spread "
            "with one unit notional per leg; report gross and cost-adjusted results"
        )
    task_card = (
        "incomplete_in_frozen_ledger: original domain, frequency, universe, objective, and claimed metric must be read "
        "from the cited source before any source-specific conclusion"
    )
    orientation = "pre-freeze outcome influence not excludable; no post-freeze sign reversal or candidate deletion"
    return role, extraction, preservation, help_rule, boundary, anti_strawman, task_card + "; " + orientation


def build_audit(registry: pd.DataFrame, lock: dict) -> pd.DataFrame:
    audit = registry.copy()
    audit["source_index"] = audit["paper_ref"].astype(str).str.extract(r"^(\d{3})")[0].astype(int)
    audit["source_name"] = audit["paper_ref"].astype(str).str.replace(r"^\d{3}\s+", "", regex=True)
    audit["source_category"] = audit["source_index"].map(source_category)
    audit["source_candidate_count"] = audit.groupby("paper_ref")["candidate_id"].transform("size")
    tiers = audit.apply(mapping_tier, axis=1, result_type="expand")
    tiers.columns = [
        "mapping_fidelity_tier",
        "source_supports_exact_ingredients",
        "source_supports_exact_signs",
        "mapping_support_note",
    ]
    audit = pd.concat([audit, tiers], axis=1)
    audit["source_supports_tested_weighting_rule"] = "no"
    audit["source_supports_monthly_us_top1000_common_task"] = "no"
    audit["exact_original_claim_matches_monthly_us_ff_alpha"] = "no explicit match identified"
    audit["central_omitted_components"] = audit.apply(omitted_components, axis=1)
    audit["alternative_mapping_status"] = np.where(
        audit["source_candidate_count"] > 1,
        "multiple already-coded mappings; included in limited sensitivity",
        "no alternative formula coded; mapping uncertainty unquantified",
    )
    audit["mapping_frozen_before_us_returns_inspected"] = "no"
    audit["mapping_freeze_timestamp_utc"] = lock["created_at_utc"]
    audit["mapping_freeze_sha256"] = lock["file_sha256"]["paper_runs/submission_evidence/frozen_candidate_registry.csv"]
    audit["independent_second_coder"] = "no"
    audit["source_evidence_status"] = np.where(
        audit["mapping_fidelity_tier"].eq("M2_released_seed_expression"),
        "released seed expression",
        "paraphrased source rationale; no exact source text supports the complete tested formula",
    )
    good_faith = audit.apply(good_faith_fields, axis=1, result_type="expand")
    good_faith.columns = [
        "good_faith_empirical_role",
        "claim_extraction_status",
        "source_content_preserved",
        "benefit_of_doubt_implementation",
        "negative_evidence_boundary",
        "anti_strawman_status",
        "task_card_and_orientation_status",
    ]
    audit = pd.concat([audit, good_faith], axis=1)
    columns = [
        "source_index",
        "source_name",
        "source_category",
        "paper_ref",
        "candidate_id",
        "paper_idea",
        "proxy_formula",
        "strategy",
        "replication_scope",
        "mapping_fidelity_tier",
        "source_supports_exact_ingredients",
        "source_supports_exact_signs",
        "source_supports_tested_weighting_rule",
        "source_supports_monthly_us_top1000_common_task",
        "exact_original_claim_matches_monthly_us_ff_alpha",
        "mapping_support_note",
        "central_omitted_components",
        "source_candidate_count",
        "alternative_mapping_status",
        "mapping_frozen_before_us_returns_inspected",
        "mapping_freeze_timestamp_utc",
        "mapping_freeze_sha256",
        "independent_second_coder",
        "source_evidence_status",
        "good_faith_empirical_role",
        "claim_extraction_status",
        "source_content_preserved",
        "benefit_of_doubt_implementation",
        "negative_evidence_boundary",
        "anti_strawman_status",
        "task_card_and_orientation_status",
    ]
    return audit[columns].sort_values(["source_index", "source_name", "candidate_id"]).reset_index(drop=True)


def source_grounded_subset(
    audit: pd.DataFrame, primary: pd.DataFrame, broad: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Post-hoc diagnostic restricted to released/named/example-supported components."""
    grounded = audit.loc[
        audit["good_faith_empirical_role"].eq("source_grounded_component_test"),
        ["candidate_id", "paper_ref", "mapping_fidelity_tier", "negative_evidence_boundary"],
    ].copy()
    frames = []
    summaries = []
    for label, results in [("six_factor_primary", primary), ("broad_jkp_post_hoc", broad)]:
        merged = grounded.merge(
            results[["candidate_id", "alpha_annualized", "p_value_two_sided"]],
            on="candidate_id",
            how="left",
            validate="1:1",
        )
        if merged[["alpha_annualized", "p_value_two_sided"]].isna().any().any():
            raise ValueError(f"missing {label} result in source-grounded subset")
        pvalues = np.where(
            merged["alpha_annualized"].to_numpy(dtype=float) > 0,
            merged["p_value_two_sided"].to_numpy(dtype=float),
            1.0,
        )
        merged["subset_holm_p_value"] = holm_adjust(pvalues)
        merged.insert(0, "benchmark", label)
        frames.append(merged)
        summaries.append(
            {
                "benchmark": label,
                "analysis_label": "post_hoc_source_grounded_component_subset",
                "candidate_count": int(len(merged)),
                "median_alpha_annualized": float(merged["alpha_annualized"].median()),
                "nominal_positive_5pct": int(
                    ((merged["alpha_annualized"] > 0) & (merged["p_value_two_sided"] <= 0.05)).sum()
                ),
                "holm_positive_5pct_within_subset": int(
                    ((merged["alpha_annualized"] > 0) & (merged["subset_holm_p_value"] <= 0.05)).sum()
                ),
                "interpretation": "component-level only; no source-level or native-agent negative inference",
            }
        )
    return pd.concat(frames, ignore_index=True), pd.DataFrame(summaries)


def mapping_sensitivity(audit: pd.DataFrame, results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    merged = audit.merge(
        results[["candidate_id", "status", "alpha_annualized", "p_value_two_sided"]],
        on="candidate_id",
        how="left",
        validate="1:1",
    )
    if not merged["status"].eq("ok").all():
        raise ValueError("U.S. mapping sensitivity requires all 62 candidate paths")

    multi = merged.groupby("paper_ref", sort=True).filter(lambda x: len(x) > 1)
    within_rows = []
    for paper_ref, group in multi.groupby("paper_ref", sort=True):
        within_rows.append(
            {
                "paper_ref": paper_ref,
                "n_coded_mappings": len(group),
                "candidate_ids": ";".join(group["candidate_id"]),
                "alpha_min_annualized": float(group["alpha_annualized"].min()),
                "alpha_max_annualized": float(group["alpha_annualized"].max()),
                "alpha_sign_stable": bool((group["alpha_annualized"] > 0).nunique() == 1),
                "raw_p_min": float(group["p_value_two_sided"].min()),
                "raw_p_max": float(group["p_value_two_sided"].max()),
            }
        )
    within = pd.DataFrame(within_rows)

    grouped = {key: grp.copy() for key, grp in merged.groupby("paper_ref", sort=True)}
    fixed = [grp.iloc[0] for grp in grouped.values() if len(grp) == 1]
    alternatives = [(key, grp) for key, grp in grouped.items() if len(grp) > 1]
    combination_rows = []
    for combination_id, choice_indices in enumerate(
        itertools.product(*[range(len(grp)) for _, grp in alternatives]), start=1
    ):
        selected = [*fixed]
        labels = []
        for (paper_ref, group), choice in zip(alternatives, choice_indices):
            row = group.iloc[choice]
            selected.append(row)
            labels.append(f"{paper_ref}:{row['candidate_id']}")
        selected_frame = pd.DataFrame(selected)
        adjusted = holm_adjust(selected_frame["p_value_two_sided"].to_numpy(dtype=float))
        positive = selected_frame["alpha_annualized"].to_numpy(dtype=float) > 0
        discoveries = selected_frame.loc[positive & (adjusted <= 0.05), "candidate_id"].tolist()
        combination_rows.append(
            {
                "combination_id": combination_id,
                "family_size_one_mapping_per_named_source": len(selected_frame),
                "choices": ";".join(labels),
                "n_positive_holm_5pct": len(discoveries),
                "holm_discoveries": ";".join(discoveries),
            }
        )
    combinations = pd.DataFrame(combination_rows)
    method_mask = merged["source_category"].isin(
        ["formula_or_factor_method", "sequential_trading_or_portfolio_method"]
    )
    method_results = merged[method_mask].copy()
    method_holm = holm_adjust(method_results["p_value_two_sided"].to_numpy(dtype=float))
    method_positive = method_results["alpha_annualized"].to_numpy(dtype=float) > 0
    method_discoveries = method_results.loc[
        method_positive & (method_holm <= 0.05), "candidate_id"
    ].tolist()
    summary = {
        "candidate_count": int(len(merged)),
        "indexed_source_count": int(merged["source_index"].nunique()),
        "named_source_rows": int(merged["paper_ref"].nunique()),
        "sources_with_multiple_coded_mappings": int(len(within)),
        "candidates_covered_by_existing_alternatives": int(len(multi)),
        "one_mapping_per_source_combinations": int(len(combinations)),
        "combination_holm_discovery_count_min": int(combinations["n_positive_holm_5pct"].min()),
        "combination_holm_discovery_count_max": int(combinations["n_positive_holm_5pct"].max()),
        "combination_unique_discovery_sets": sorted(combinations["holm_discoveries"].unique().tolist()),
        "method_source_candidate_count_post_hoc": int(len(method_results)),
        "method_source_holm_discoveries_post_hoc": method_discoveries,
        "limitation": (
            "This sensitivity varies only mappings already present in the frozen family. "
            "It does not quantify alternative formulas for singly mapped sources and is a lower bound on mapping uncertainty."
        ),
    }
    return within, combinations, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--broad-results", type=Path, default=DEFAULT_BROAD_RESULTS)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    registry = pd.read_csv(args.registry)
    results = pd.read_csv(args.results)
    broad_results = pd.read_csv(args.broad_results)
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    audit = build_audit(registry, lock)
    within, combinations, sensitivity = mapping_sensitivity(audit, results)
    grounded_detail, grounded_summary = source_grounded_subset(audit, results, broad_results)

    source_summary = (
        audit.groupby(["source_category", "mapping_fidelity_tier"], as_index=False)
        .agg(candidates=("candidate_id", "size"), indexed_sources=("source_index", "nunique"))
        .sort_values(["source_category", "mapping_fidelity_tier"])
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "mapping_audit.csv": audit,
        "source_scope_summary.csv": source_summary,
        "within_source_mapping_sensitivity.csv": within,
        "mapping_combination_sensitivity.csv": combinations,
        "source_grounded_subset_results.csv": grounded_detail,
        "source_grounded_subset_summary.csv": grounded_summary,
    }
    for name, frame in paths.items():
        frame.to_csv(args.output_dir / name, index=False)
    manifest = {
        "analysis_label": "post_hoc_mapping_discretion_audit",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_sha256": sha256(args.registry),
        "usa_results_sha256": sha256(args.results),
        "mapping_outcome_blind": False,
        "independent_second_coder": False,
        "exact_common_task_claims_identified": 0,
        "good_faith_reconstruction": {
            "source_grounded_component_tests": int(
                audit["good_faith_empirical_role"].eq("source_grounded_component_test").sum()
            ),
            "exploratory_favorable_stress_tests": int(
                audit["good_faith_empirical_role"].eq("exploratory_favorable_stress_test").sum()
            ),
            "source_level_negative_claims_permitted": 0,
            "orientation_caveat": "pre-freeze U.S. outcome influence cannot be excluded",
        },
        "sensitivity": sensitivity,
        "output_sha256": {name: sha256(args.output_dir / name) for name in paths},
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
