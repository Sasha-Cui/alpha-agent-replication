#!/usr/bin/env python3
"""Link every census paper to existing evidence without converting audit closure to replication."""

from pathlib import Path
import json
import re
import hashlib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arxiv_ids(value):
    return set(re.findall(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?", "\n".join(strings(value))))


def main():
    old = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    current = json.loads((PUBLIC / "paper_ledger.json").read_text())
    audits = []
    for path in sorted((ROOT / "paper_runs/paper_replication_audits").glob("*/manifest.json")):
        data = json.loads(path.read_text())
        # Match paper identity fields only; references in long audit prose can
        # name other papers and must not create false links.
        identity = {
            k: v
            for k, v in data.items()
            if k in ["paper", "paper_url", "title", "official_paper_url", "canonical_work_id", "paper_id"]
        }
        audits.append((path, data, arxiv_ids(identity)))
    # Manually verified same-paper folder identities; no similarity matching.
    explicit_identity = {"M007": "quantagent_self_improving", "M021": "alpha_jungle", "M023": "efs", "M026": "chain_of_alpha", "M041": "cogalpha", "M043": "quantaalpha", "M046": "factorengine"}
    updates = []
    unmatched = []
    for milestone, row in zip(old["milestones"], current["papers"]):
        assert milestone["milestone_id"] == row["id"]
        recipe_path = ROOT / milestone["recipe_path"]
        recipe = json.loads(recipe_path.read_text())
        explicit = set(re.findall(r"paper_runs/paper_replication_audits/([a-z0-9_]+)(?=/|\s|$)", "\n".join(strings(recipe))))
        if row["id"] in explicit_identity:
            explicit.add(explicit_identity[row["id"]])
        identifiers = arxiv_ids(
            {k: v for k, v in recipe.items() if k in ["paper_url", "source_url", "paper_source", "paper"]}
        )
        matches = [(p, d) for p, d, ids in audits if p.parent.name in explicit or identifiers & ids]
        reason = "explicit recipe audit path, matching paper identifier, or manually verified same-paper folder identity"
        if not matches:
            # The strict verdict itself is still concrete evidence; absence of
            # a machine-resolved audit link stays visible for manual disposition.
            unmatched.append({"id": row["id"], "title": row["title"]})
        limits = {
            k: v
            for k, v in recipe.items()
            if any(
                word in k
                for word in [
                    "missing",
                    "not_claimed",
                    "full_system_not_reproduced",
                    "scope_finding",
                    "source_execution_conflicts",
                    "portability",
                ]
            )
        }
        updated = {
            **row,
            "strict_recipe_sha256": fingerprint(recipe_path),
            "prior_documented_limitations": limits,
            "native_audit_links": [
                {
                    "path": str(p.relative_to(ROOT)),
                    "sha256": fingerprint(p),
                    "status": d.get("overall_status", d.get("status")),
                    "matching_basis": reason,
                    "full_paper_reproduced": d.get("full_paper_reproduced", False),
                }
                for p, d in matches
            ],
            "independent_human_review_complete": False,
        }
        updates.append(updated)
    result = {
        "status": "evidence_indexed_final_dispositions_pending",
        "indexed_at_utc": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(updates),
        "papers_with_resolved_native_audits": sum(bool(x["native_audit_links"]) for x in updates),
        "papers": updates,
        "unresolved_native_audit_links": unmatched,
        "rule": current["rule"],
        "source_availability_date": "Inherited pinned audits; no assertion that every upstream repository was freshly re-audited today.",
    }
    (PUBLIC / "paper_evidence_index.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "papers": len(updates),
                "resolved_audit_links": result["papers_with_resolved_native_audits"],
                "unmatched": unmatched,
            }
        )
    )


if __name__ == "__main__":
    main()
