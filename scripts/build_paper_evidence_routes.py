#!/usr/bin/env python3
"""Build the mutually exclusive paper-level evidence-route ledger.

Mapping fidelity and code availability are different axes. This builder gives
each retained canonical work one primary route while preserving the narrower
row-level mapping and native-fidelity dispositions.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path(
    "paper_runs/submission_evidence/replication_scope/"
    "paper_evidence_route_ledger.csv"
)
DEFAULT_TEX_OUTPUT = Path("docs/paper/generated_evidence_routes.tex")

PUBLIC_CODE_ROUTE = "public_code_available"
PAPER_SPECIFIED_ROUTE = "paper_only_sufficiently_specified"
PAPER_UNDERSPECIFIED_ROUTE = "paper_only_underspecified"
TESTABLE_RULE_TIERS = {
    "M1_named_rule_partial_support",
    "M2_released_seed_expression",
}
EXPECTED_ROUTE_COUNTS = {
    PUBLIC_CODE_ROUTE: 19,
    PAPER_SPECIFIED_ROUTE: 0,
    PAPER_UNDERSPECIFIED_ROUTE: 50,
}


def joined(values: pd.Series | list[str], separator: str = "; ") -> str:
    clean = {
        str(value).strip()
        for value in values
        if pd.notna(value) and str(value).strip()
    }
    return separator.join(sorted(clean))


def classify_route(
    public_code_available: bool,
    mapping_tiers: set[str],
) -> str:
    if public_code_available:
        return PUBLIC_CODE_ROUTE
    if mapping_tiers & TESTABLE_RULE_TIERS:
        return PAPER_SPECIFIED_ROUTE
    return PAPER_UNDERSPECIFIED_ROUTE


def mapping_disposition(waterfall_row: pd.Series) -> str:
    fidelity = str(waterfall_row["reconstruction_fidelity"])
    if fidelity == "source_grounded_component_test":
        return "source_grounded_component_only"
    if fidelity == "narrative_favorable_stress_test":
        return "clearly_labeled_motif_proxy"
    if fidelity == "availability_only":
        return "availability_only_no_performance_inference"
    raise ValueError(f"Unexpected retained-work reconstruction fidelity: {fidelity}")


def proxy_role(route: str, disposition: str) -> str:
    if disposition == "availability_only_no_performance_inference":
        return "no_proxy"
    if route == PUBLIC_CODE_ROUTE:
        return "secondary_diagnostic_after_native_review"
    if route == PAPER_SPECIFIED_ROUTE:
        return "stated_rule_or_procedure_reproduction"
    if disposition == "source_grounded_component_only":
        return "partial_source_component_not_full_procedure"
    return "clearly_labeled_favorable_motif_proxy"


def build_routes(
    metadata: pd.DataFrame,
    waterfall: pd.DataFrame,
    mapping_scope: pd.DataFrame,
    native_fidelity: pd.DataFrame,
) -> pd.DataFrame:
    retained = metadata[
        metadata["preferred_citation"].eq("yes")
        & metadata["main_ft"].eq("yes")
    ].copy()
    retained = retained.sort_values("canonical_work_id", kind="stable")
    if len(retained) != 69 or retained["canonical_work_id"].nunique() != 69:
        raise ValueError("Expected exactly 69 retained canonical works")

    retained_waterfall = waterfall[
        waterfall["screen_decision"].eq("retained_formula_or_trading")
    ].copy()
    if len(retained_waterfall) != 69:
        raise ValueError("Work-level waterfall does not contain 69 retained works")
    waterfall_by_work = retained_waterfall.set_index("canonical_work_id")

    included_mapping = mapping_scope[
        mapping_scope["headline_50_scope"].eq("included")
    ].copy()
    mapping_by_work = {
        work_id: group.copy()
        for work_id, group in included_mapping.groupby("canonical_work_id")
    }
    native_by_system = native_fidelity.set_index("system_id", drop=False)

    rows: list[dict[str, object]] = []
    for _, paper in retained.iterrows():
        work_id = str(paper["canonical_work_id"])
        if work_id not in waterfall_by_work.index:
            raise ValueError(f"Retained work is absent from waterfall: {work_id}")
        work = waterfall_by_work.loc[work_id]
        system_ids = [
            value.strip()
            for value in str(paper["system_ids"]).split(";")
            if value.strip()
        ]
        native_rows = native_by_system.loc[
            [system_id for system_id in system_ids if system_id in native_by_system.index]
        ].copy()
        if isinstance(native_rows, pd.Series):
            native_rows = native_rows.to_frame().T
        public_rows = native_rows[
            native_rows["public_artifact_status"].eq("reachable_static_snapshot")
            & native_rows["static_tier"].isin({"R1", "R2", "R3"})
        ]
        listed_rows = native_rows[
            native_rows["public_artifact_status"].ne("not_listed")
        ]

        mappings = mapping_by_work.get(work_id, pd.DataFrame())
        mapping_tiers = (
            set(mappings["mapping_fidelity_tier"].astype(str))
            if not mappings.empty
            else set()
        )
        route = classify_route(not public_rows.empty, mapping_tiers)
        disposition = mapping_disposition(work)
        targeted_statuses = [
            status
            for status in native_rows["targeted_execution_audit_status"]
            .astype(str)
            .tolist()
            if status != "not_targeted_in_legacy_execution_audit"
        ]
        targeted = bool(targeted_statuses)
        audited_rows = native_rows[
            native_rows["targeted_execution_audit_status"].ne(
                "not_targeted_in_legacy_execution_audit"
            )
        ]

        if route == PUBLIC_CODE_ROUTE:
            route_basis = (
                "reachable public code/artifact snapshot; native pipeline or "
                "precise blocker takes priority; any proxy is secondary"
            )
            blocker = joined(
                [
                    f"{row.system_id}:{row.blocking_stage}:{row.concise_evidence_note}"
                    for row in public_rows.itertuples()
                ]
            )
            if not blocker:
                raise ValueError(f"Public-code work lacks a precise blocker: {work_id}")
            native_disposition = (
                "targeted_execution_recorded"
                if targeted
                else "static_common_task_blocker_recorded_not_execution_targeted"
            )
        elif route == PAPER_SPECIFIED_ROUTE:
            route_basis = (
                "paper-only stated rule/procedure is sufficiently specific for "
                "the supported scope"
            )
            blocker = "no_reachable_public_code"
            native_disposition = (
                "paper_only_audit_recorded_no_native_code_pipeline"
                if targeted
                else "paper_only_no_native_code_pipeline"
            )
        else:
            route_basis = (
                "paper-only procedure is partial or underspecified; use a labeled "
                "component/motif proxy or availability-only disposition"
            )
            unresolved = listed_rows[
                listed_rows["public_artifact_status"].isin(
                    {"listed_check_failed", "listed_unreachable"}
                )
            ]
            blocker = (
                joined(
                    [
                        f"{row.system_id}:{row.blocking_stage}:{row.concise_evidence_note}"
                        for row in audited_rows.itertuples()
                    ]
                )
                or joined(
                    [
                        f"{row.system_id}:{row.blocking_stage}:{row.concise_evidence_note}"
                        for row in unresolved.itertuples()
                    ]
                )
                or "no_reachable_public_code"
            )
            native_disposition = (
                "paper_only_audit_recorded_no_native_code_pipeline"
                if targeted
                else "paper_only_no_native_code_pipeline"
            )

        rows.append(
            {
                "canonical_work_id": work_id,
                "bibtex_key": paper["bibtex_key"],
                "title": paper["title"],
                "year": int(paper["year"]),
                "paper_evidence_route": route,
                "route_basis": route_basis,
                "system_ids": joined(system_ids),
                "reachable_public_code_system_ids": joined(
                    public_rows["system_id"] if not public_rows.empty else []
                ),
                "public_artifact_statuses": joined(
                    listed_rows["public_artifact_status"]
                    if not listed_rows.empty
                    else ["not_listed"]
                ),
                "static_fidelity_tiers": joined(
                    public_rows["static_tier"] if not public_rows.empty else []
                ),
                "native_pipeline_disposition": native_disposition,
                "native_execution_audit_status": joined(targeted_statuses),
                "precise_native_or_access_blocker": blocker,
                "full_prompt_search_training_pipeline_reproduced": "no",
                "good_faith_reconstruction": work[
                    "good_faith_reconstruction"
                ],
                "mapping_count": int(work["mapping_count"]),
                "mapping_fidelity_tiers": joined(mapping_tiers),
                "mapping_disposition": disposition,
                "proxy_role": proxy_role(route, disposition),
                "negative_inference_boundary": work[
                    "negative_inference_boundary"
                ],
            }
        )

    routes = pd.DataFrame(rows)
    counts = {
        route: int(routes["paper_evidence_route"].eq(route).sum())
        for route in EXPECTED_ROUTE_COUNTS
    }
    if counts != EXPECTED_ROUTE_COUNTS:
        raise ValueError(
            f"Paper evidence-route partition changed: {counts}; "
            f"expected {EXPECTED_ROUTE_COUNTS}"
        )
    if not routes[
        "full_prompt_search_training_pipeline_reproduced"
    ].eq("no").all():
        raise ValueError("Current evidence incorrectly claims a native procedure run")
    public = routes[routes["paper_evidence_route"].eq(PUBLIC_CODE_ROUTE)]
    if public["precise_native_or_access_blocker"].eq("").any():
        raise ValueError("A public-code paper lacks its blocker record")
    if (
        public["good_faith_reconstruction"].eq("yes")
        & public["proxy_role"].ne("secondary_diagnostic_after_native_review")
    ).any():
        raise ValueError("A public-code proxy is not labeled secondary")
    return routes


def write_tex_macros(routes: pd.DataFrame, output: Path) -> None:
    public = routes[routes["paper_evidence_route"].eq(PUBLIC_CODE_ROUTE)]
    paper_only = routes[
        routes["paper_evidence_route"].eq(PAPER_UNDERSPECIFIED_ROUTE)
    ]
    values = {
        "PublicCodeRouteWorkCount": len(public),
        "PublicCodeTargetedWorkCount": int(
            public["native_pipeline_disposition"].eq(
                "targeted_execution_recorded"
            ).sum()
        ),
        "PublicCodeStaticBlockerWorkCount": int(
            public["native_pipeline_disposition"].eq(
                "static_common_task_blocker_recorded_not_execution_targeted"
            ).sum()
        ),
        "PaperOnlySpecifiedWorkCount": int(
            routes["paper_evidence_route"].eq(PAPER_SPECIFIED_ROUTE).sum()
        ),
        "PaperOnlyUnderspecifiedWorkCount": len(paper_only),
        "PaperOnlyPartialComponentWorkCount": int(
            paper_only["proxy_role"].eq(
                "partial_source_component_not_full_procedure"
            ).sum()
        ),
        "PaperOnlyMotifProxyWorkCount": int(
            paper_only["proxy_role"].eq(
                "clearly_labeled_favorable_motif_proxy"
            ).sum()
        ),
        "PaperOnlyAvailabilityWorkCount": int(
            paper_only["proxy_role"].eq("no_proxy").sum()
        ),
    }
    lines = [
        "% Generated by scripts/build_paper_evidence_routes.py; do not edit.",
        *[
            rf"\newcommand{{\{name}}}{{{value}\xspace}}"
            for name, value in values.items()
        ],
        "",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--tex-output", type=Path, default=DEFAULT_TEX_OUTPUT
    )
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output
    if not output.is_absolute():
        output = root / output
    routes = build_routes(
        pd.read_csv(
            root / "literature_review/census_v1/primary_record_metadata.csv"
        ),
        pd.read_csv(
            root
            / "paper_runs/submission_evidence/replication_scope/"
            "work_level_evidence_waterfall.csv"
        ),
        pd.read_csv(
            root
            / "paper_runs/submission_evidence/replication_scope/"
            "mapping_scope_ledger.csv"
        ),
        pd.read_csv(
            root / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
        ),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    routes.to_csv(output, index=False)
    tex_output = args.tex_output
    if not tex_output.is_absolute():
        tex_output = root / tex_output
    write_tex_macros(routes, tex_output)
    print(routes["paper_evidence_route"].value_counts().sort_index().to_dict())
    print(routes["mapping_disposition"].value_counts().sort_index().to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
