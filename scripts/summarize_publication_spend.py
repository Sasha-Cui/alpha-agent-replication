#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Summarize all known charges and retained bounds without exposing credentials."""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_llm import CohortOpenRouter


def main():
    path = ROOT / "runs/economic_fidelity/openrouter"
    meter = CohortOpenRouter(path, "unused", "unused", study="read_only_accounting", offline=True)
    with meter.ledger() as ledger:
        state = json.loads(json.dumps(ledger))
    rows = []
    historical = {}
    for record in state.get("imports", {}).values():
        historical.update(record["responses"])
    rows.append(
        {
            "study": "imported_prior_GuruAgents",
            "complete_provider_requests": len(historical),
            "unavailable_requests": 0,
            "in_flight_requests": 0,
            "known_or_tariff_cost_usd": sum(historical.values()),
            "reserved_bound_usd": 0.0,
            "committed_usd": sum(historical.values()),
        }
    )
    for study in sorted({c["study"] for c in state["calls"].values()}):
        calls = [c for c in state["calls"].values() if c["study"] == study]
        complete = [c for c in calls if c["status"] == "complete"]
        unresolved = [c for c in calls if c["status"] != "complete"]
        known = sum(c["cost_usd"] for c in complete)
        bound = sum(c["reserved_usd"] for c in unresolved)
        rows.append(
            {
                "study": study,
                "complete_provider_requests": len(complete),
                "unavailable_requests": sum(c["status"] == "response_unavailable" for c in calls),
                "in_flight_requests": sum(c["status"] == "reserved" for c in calls),
                "known_or_tariff_cost_usd": known,
                "reserved_bound_usd": bound,
                "committed_usd": known + bound,
            }
        )
    out = ROOT / "paper_runs/publication_upgrade_v1"
    pd.DataFrame(rows).to_csv(out / "spend_by_study.csv", index=False)
    atomic_json(
        out / "spend_summary.json",
        {
            "project_committed_usd": sum(r["committed_usd"] for r in rows),
            "known_or_tariff_cost_usd": sum(r["known_or_tariff_cost_usd"] for r in rows),
            "unresolved_reservations_usd": sum(r["reserved_bound_usd"] for r in rows),
            "unavailable_requests": sum(r["unavailable_requests"] for r in rows),
            "in_flight_requests": sum(r["in_flight_requests"] for r in rows),
            "project_soft_stop_usd": 450,
            "project_hard_ceiling_usd": 500,
            "ledger_sha256_at_snapshot": sha256(path / "project_spend.json"),
            "scope": "Includes prior imported usage, setup runs, abandoned implementation attempts, summaries, embeddings, explicit technical recoveries and the prospective pilot. This is project research spend, not a production-cost estimate.",
        },
    )
    print(
        "PROJECT_COMMITTED_USD",
        sum(r["committed_usd"] for r in rows),
        "IN_FLIGHT",
        sum(r["in_flight_requests"] for r in rows),
    )


if __name__ == "__main__":
    main()
