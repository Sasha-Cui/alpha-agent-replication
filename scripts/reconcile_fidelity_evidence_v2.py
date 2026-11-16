#!/usr/bin/env python3
"""Paper-specific evidence review without relabeling audits or proxies as replications."""

from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"


def nested_missing(value, path=""):
    found = {}
    if isinstance(value, dict):
        for key, item in value.items():
            label = path + "." + key if path else key
            if any(
                term in key.lower()
                for term in [
                    "missing",
                    "required_but",
                    "not_reproduced",
                    "not_claimed",
                    "scope_finding",
                    "source_execution_conflicts",
                ]
            ):
                found[label] = item
            elif isinstance(item, (dict, list)):
                found.update(nested_missing(item, label))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            if isinstance(item, dict):
                found.update(nested_missing(item, path + "[" + str(i) + "]"))
    return found


def main():
    evidence = json.loads((PUBLIC / "paper_evidence_index.json").read_text())
    spirit = {
        r["milestone_id"]: r
        for r in json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())["milestones"]
    }
    result = []
    for row in evidence["papers"]:
        if not row["native_audit_links"]:
            raise ValueError("Unlinked native audit " + row["id"])
        for audit in row["native_audit_links"]:
            if hashlib.sha256((ROOT / audit["path"]).read_bytes()).hexdigest() != audit["sha256"]:
                raise ValueError("Audit changed since evidence index")
        strict = json.loads((ROOT / row["existing_recipe"]).read_text())
        current = spirit[row["id"]]
        if row["cohort_case"]:
            disposition = "native_economic_fidelity_extension_or_preserved_v1_case"
            next_action = "Complete and validate the bounded v2 extension, retaining all original-model/data/trial limitations; GuruAgents stays at its frozen completed v1 prompt-replay scope."
        elif current["status"] == "discarded_structural_mismatch":
            disposition = "outside_common_monthly_us_jkp_transfer_scope"
            next_action = "Retain native audit evidence and structural exclusion; no stock proxy is credited to the original nonmatching task."
        elif row["existing_strict_status"].startswith("completed_"):
            disposition = "source_component_evaluated_full_mechanism_unreplicated"
            next_action = "Preserve the source-component result and concrete missing mechanism evidence. Further fresh search may be possible with disclosed replacements; absence of the historical result is not proof that every new experiment is impossible."
        else:
            disposition = "missing_artifacts_or_underidentified_native_policy"
            next_action = "Use the pinned paper-specific missing objects and audit findings to delimit replication. Preserve any in-spirit reconstruction as a separate invented implementation."
        # Substantial source exists here, so do not classify the unexecuted
        # fresh search as impossible merely because author outputs are missing.
        if row["id"] == "M019":
            disposition = "recovered_source_fresh_search_in_progress"
            next_action = "Paper-era AlphaAgent source and reconstructed environments execute bounded source/paper-model pilots with full replays, independent accounts and source-used full-universe proofs. A corrected twenty-trial study is in progress under its frozen attempted-round protocol and shared20USD cap. Completion requires every trial, complete pooled libraries and opening-information economic evaluation; see progress.json for separate execution/replay/account/causality counts. Exact published five-factor US lineage/data and regularizer remain unavailable or conflicting."
        result.append(
            {
                "id": row["id"],
                "title": row["title"],
                "review_disposition": disposition,
                "existing_strict_status": row["existing_strict_status"],
                "existing_strict_scope": row["existing_scope"],
                "prior_strict_closure_reason": row["existing_closure_reason"],
                "in_spirit_status": current["status"],
                "in_spirit_recipe": current.get("recipe_path"),
                "native_audit_links": row["native_audit_links"],
                "remaining_paper_specific_gaps": nested_missing(strict),
                "next_action_or_claim_boundary": next_action,
                "fresh_upstream_availability_check_this_turn": False,
                "full_original_paper_reproduced": False,
                "independent_human_review_complete": False,
            }
        )
    counts = {
        category: sum(r["review_disposition"] == category for r in result)
        for category in sorted({r["review_disposition"] for r in result})
    }
    out = {
        "status": "evidence_review_index_complete_execution_completion_pending",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(result),
        "counts": counts,
        "full_original_paper_replications_established": 0,
        "scope": "All69 papers retain individual evidence. Dates and availability claims inside prior closure reasons belong to their pinned historical audits, not a new September17 web census. Evidence review does not close unfinished feasible experiments.",
        "papers": result,
    }
    (PUBLIC / "paper_dispositions.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"papers": len(result), "counts": counts}))


if __name__ == "__main__":
    main()
