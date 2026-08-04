#!/usr/bin/env python3
"""Build explicit census, code-attempt, and source-grounded scope inventories."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def ref_numbers(value: object) -> set[int]:
    found = set()
    for token in str(value).replace(";", " ").split():
        try:
            found.add(int(token))
        except ValueError:
            pass
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "paper_runs/submission_evidence/replication_scope"
    output.mkdir(parents=True, exist_ok=True)

    census = pd.read_csv(root / "literature_review/census_v1/system_registry.csv", sep="|")
    census = census.loc[census["main_FT"].eq("Y")].copy()
    direct = pd.read_csv(root / "paper_runs/repository_ff5mom_metrics_summary.csv")
    mapping = pd.read_csv(root / "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv")
    links = pd.read_csv(root / "literature_review/paper_links.csv")
    grounded_refs = set(mapping.loc[
        mapping["good_faith_empirical_role"].eq("source_grounded_component_test"), "source_index"
    ].astype(int))
    direct_refs = set(direct["ref_index"].astype(int))

    roles = []
    for _, row in census.iterrows():
        refs = ref_numbers(row["old_refs"])
        is_direct = bool(refs & direct_refs)
        is_grounded = bool(refs & grounded_refs)
        if is_direct and is_grounded:
            role = "targeted_code_attempt_and_source_grounded_component_test"
        elif is_direct:
            role = "targeted_code_attempt"
        elif is_grounded:
            role = "source_grounded_component_test"
        else:
            role = "availability_census_only"
        roles.append(role)
    census["empirical_role_in_paper"] = roles
    census["bibliographic_unit"] = "system lineage; primary_record may contain multiple publications"
    census[[
        "system_id", "system_name", "stratum", "primary_record", "official_artifact",
        "empirical_role_in_paper", "bibliographic_unit", "inclusion_exclusion_rationale",
    ]].sort_values(["stratum", "system_name"]).to_csv(output / "system_census_bibliography.csv", index=False)

    old_ref_to_system = {}
    for _, row in census.iterrows():
        for ref in ref_numbers(row["old_refs"]):
            old_ref_to_system.setdefault(ref, []).append(str(row["system_name"]))
    paper_url = links.set_index("ref_index")["paper_or_project_url"].to_dict()
    direct_out = direct[[
        "ref_index", "title", "code_status", "code_url", "execution_state", "metric_status",
        "candidate_id", "alpha_annualized", "alpha_tstat_hac",
    ]].copy()
    direct_out["in_67_system_census"] = direct_out["ref_index"].astype(int).map(
        lambda ref: "yes" if ref in old_ref_to_system else "no"
    )
    direct_out["census_system_name"] = direct_out["ref_index"].astype(int).map(
        lambda ref: "; ".join(old_ref_to_system.get(ref, []))
    )
    direct_out["paper_url"] = direct_out["ref_index"].astype(int).map(paper_url)
    direct_out.sort_values("title").to_csv(output / "direct_code_attempt_inventory.csv", index=False)

    grounded = mapping.loc[
        mapping["good_faith_empirical_role"].eq("source_grounded_component_test")
    ].copy()
    grounded["paper_url"] = grounded["source_index"].astype(int).map(paper_url)
    grounded[[
        "source_index", "source_name", "paper_url", "candidate_id", "paper_idea",
        "proxy_formula", "strategy", "mapping_fidelity_tier", "source_content_preserved",
        "negative_evidence_boundary",
    ]].sort_values(["source_index", "candidate_id"]).to_csv(
        output / "source_grounded_component_inventory.csv", index=False
    )

    lines = [
        "# Complete 67-system census bibliography",
        "",
        "The unit is a system lineage, not necessarily one paper. This list is the complete",
        "F/T availability census. It must not be read as 67 replications.",
        "",
    ]
    for _, row in census.sort_values(["stratum", "system_name"]).iterrows():
        records = str(row["primary_record"]).split(" ; ")
        linked = ", ".join(f"[{index + 1}]({url})" for index, url in enumerate(records))
        lines.append(
            f"- `{row['system_id']}` - **{row['system_name']}** ({row['stratum']}); "
            f"role: `{row['empirical_role_in_paper']}`; primary record: {linked}."
        )
    (root / "docs/system_census_bibliography.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print({
        "census_lineages": len(census),
        "direct_code_attempts": len(direct_out),
        "direct_attempts_inside_census": int(direct_out["in_67_system_census"].eq("yes").sum()),
        "source_grounded_papers": int(grounded["source_index"].nunique()),
        "source_grounded_components": len(grounded),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
