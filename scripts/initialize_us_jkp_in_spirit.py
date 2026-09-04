#!/usr/bin/env python3
"""Initialize the separate U.S./JKP in-spirit reconstruction ledger."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


DISCARDED = {
    "M002": "crypto reflective-agent state and portfolio semantics",
    "M015": "crypto expert and blockchain-state portfolio",
    "M017": "fixed daily 84-stock RL state and action geometry",
    "M031": "intraday chart-reasoning and three-candle execution",
    "M035": "minute-level crypto grid-bot execution",
    "M045": "event-news language policy with future-CAR label release",
    "M058": "weekly commodity-ETF probability and allocation task",
}
CARRIED = {
    "completed_adapted",
    "completed_partial",
}
ACTIVE = "M003"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root: Path) -> dict:
    strict_root = root / "paper_runs/us_jkp_headline"
    strict_ledger_path = strict_root / "milestones.json"
    strict_manifest_path = strict_root / "final_manifest.json"
    contract_path = strict_root / "benchmark_contract.json"
    strict = json.loads(strict_ledger_path.read_text())
    strict_manifest = json.loads(strict_manifest_path.read_text())
    if strict_manifest["status"] != "complete" or strict_manifest["closed_milestones"] != 69:
        raise ValueError("strict study must be complete before initializing follow-up")

    rows = []
    for source in strict["milestones"]:
        milestone_id = source["milestone_id"]
        if source["status"] in CARRIED:
            status = "carried_common_evaluation"
            next_action = "No rerun. Carry the frozen common result with its original adaptation label."
        elif milestone_id in DISCARDED:
            status = "discarded_structural_mismatch"
            next_action = f"No proxy: discard because the central task is {DISCARDED[milestone_id]}."
        elif milestone_id == ACTIVE:
            status = "in_progress_in_spirit"
            next_action = "Freeze one paper-anchored researcher reconstruction before inspecting its JKP result."
        else:
            status = "queued_in_spirit"
            next_action = "Wait until prior active reconstruction is committed."
        rows.append(
            {
                "milestone_id": milestone_id,
                "canonical_work_id": source["canonical_work_id"],
                "title": source["title"],
                "system_ids": source["system_ids"],
                "strict_status": source["status"],
                "strict_recipe_path": source["recipe_path"],
                "strict_verdict_path": source["verdict_path"],
                "strict_metrics_path": source["metrics_path"],
                "status": status,
                "fidelity_label": (
                    source["status"] if status == "carried_common_evaluation" else
                    "structural_discard" if status == "discarded_structural_mismatch" else
                    "in_spirit_reconstruction"
                ),
                "recipe_path": "",
                "implementation_path": "",
                "run_manifest_path": "",
                "monthly_returns_path": "",
                "metrics_path": "",
                "verdict_path": "",
                "next_action": next_action,
            }
        )
    counts = {name: sum(row["status"] == name for row in rows) for name in (
        "carried_common_evaluation",
        "completed_in_spirit",
        "discarded_structural_mismatch",
        "in_progress_in_spirit",
        "queued_in_spirit",
    )}
    return {
        "schema_version": 1,
        "study_id": "us_jkp_in_spirit_v1",
        "governing_user_direction": "2026-09-04 best-effort in-spirit reconstruction; discard only seven structurally incompatible native tasks",
        "protocol_path": "docs/US_JKP_IN_SPIRIT_PROTOCOL.md",
        "strict_study_path": "paper_runs/us_jkp_headline",
        "strict_ledger_sha256": digest(strict_ledger_path),
        "strict_final_manifest_sha256": digest(strict_manifest_path),
        "benchmark_contract_path": "paper_runs/us_jkp_headline/benchmark_contract.json",
        "benchmark_contract_sha256": digest(contract_path),
        "paper_count": 69,
        "planned_common_evaluations": 62,
        "planned_new_in_spirit_reconstructions": 45,
        "declared_inference_family_size": 69,
        "progress_summary": counts,
        "milestones": rows,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "paper_runs/us_jkp_in_spirit/milestones.json"
    if output.exists():
        raise SystemExit(f"refusing to replace existing ledger: {output}")
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps(build(root), indent=2, allow_nan=False) + "\n")
    print(output)


if __name__ == "__main__":
    main()
