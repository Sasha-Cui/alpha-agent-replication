#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Record a supplied human review; never manufacture reviewer identities or judgments."""

from pathlib import Path
import sys
import argparse
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.prospective import locked, timestamp


def main():
    p = argparse.ArgumentParser()
    p.add_argument("review_file", type=Path)
    args = p.parse_args()
    record = json.loads(args.review_file.read_text())
    root = ROOT / "paper_runs/publication_upgrade_v1/source_review"
    for field in ["case", "reviewer_name", "reviewer_relationship_to_implementation", "reviewed_at_utc", "verdict"]:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError("Human-supplied field required: " + field)
    if (
        record.get("human_attestation")
        != "I personally read the cited sources and reviewed the implementation differences."
    ):
        raise ValueError("Explicit human attestation is required")
    if record.get("independent_of_implementation") is not True:
        raise ValueError("This gate requires a reviewer independent of implementation")
    if record["verdict"] not in [
        "approved_for_conditional_mechanism_comparison",
        "changes_required",
        "not_economically_comparable",
    ]:
        raise ValueError("Unknown review verdict")
    if any(
        not isinstance(record.get("judgments", {}).get(k), str) or not record["judgments"][k].strip()
        for k in ["information", "mechanism", "economics", "control", "claim_boundary"]
    ):
        raise ValueError("Every review dimension requires a written judgment")
    if timestamp(record["reviewed_at_utc"]) > datetime.now(timezone.utc):
        raise ValueError("Review timestamp is in the future")
    with locked(root):
        path = root / "human_review_ledger.json"
        ledger = json.loads(path.read_text())
        if record.get("packet_sha256") != ledger["current_packets"].get(record["case"]):
            raise ValueError("Review does not match the current packet")
        record["source_review_file_sha256"] = sha256(args.review_file)
        record["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
        ledger["reviews"].append(record)

        def approved(case, digest):
            latest = {}
            for r in ledger["reviews"]:
                if r["case"] == case and r["packet_sha256"] == digest:
                    latest[r["reviewer_name"].strip().casefold()] = r
            return bool(latest) and all(
                r["verdict"] == "approved_for_conditional_mechanism_comparison"
                and r["independent_of_implementation"] is True
                for r in latest.values()
            )

        ledger["independent_human_review_complete"] = all(
            approved(case, digest) for case, digest in ledger["current_packets"].items()
        )
        atomic_json(path, ledger)
    print("Human-supplied review recorded; complete=", ledger["independent_human_review_complete"])


if __name__ == "__main__":
    main()
