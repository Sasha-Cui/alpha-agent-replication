#!/usr/bin/env python3
"""Build the alpha_evolve paper execution registry from literature metadata."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIT = ROOT / "literature_review"
OUT = ROOT / "paper_runs"

# Strict real public codebase among paper_links.csv rows. Ambiguous means actual
# code exists but is not clearly the official paper codebase.
STRICT_CODE = {
    "1": "https://github.com/CityU-MLO/AlphaBench",
    "3": "https://github.com/RndmVariableQ/AlphaAgent",
    "5": "https://github.com/QuantLLM/QuantEvolver",
    "6": "https://github.com/microsoft/RD-Agent",
    "21": "https://github.com/gta0804/AlphaPROBE",
    "24": "https://github.com/FinStep-AI/ContestTrade",
    "25": "https://github.com/Y-Research-SBU/QuantAgent",
    "42": "https://github.com/yejining99/GuruAgents",
    "45": "https://github.com/finbrain-lab-hkustgz/AlphaForgeBench",
    "47": "https://github.com/ulab-uiuc/live-trade-bench",
    "48": "https://github.com/HKUSTDial/DeepFund",
    "51": "https://github.com/Yanlewen/TradeTrap",
}
AMBIGUOUS_CODE = {
    "29": "https://github.com/MXGao-A/FAgent",
}
PLACEHOLDER_OR_EMPTY_CODE = {
    "33": "https://github.com/TauricResearch/Trading-R1",
}
SHARPE_STRATEGY = {
    "2", "10", "11", "18", "20", "21", "24", "26", "29", "30", "31", "32",
    "33", "34", "35", "36", "37", "39", "40", "42", "43", "44", "45", "47",
    "48", "51",
}
SHARPE_CRITIQUE = {"55"}

# Paper execution priority. First pass favors code-backed rows with Sharpe or
# strong benchmark relevance, then code-backed factor-mining rows without Sharpe,
# then no-code/reimplementation candidates.
PRIORITY = {
    "21": 1,   # AlphaPROBE
    "24": 2,   # ContestTrade
    "42": 3,   # GuruAgents
    "45": 4,   # AlphaForgeBench
    "47": 5,   # LiveTradeBench
    "48": 6,   # DeepFund
    "51": 7,   # TradeTrap
    "1": 8,    # AlphaBench
    "3": 9,    # AlphaAgent
    "5": 10,   # QuantEvolver
    "6": 11,   # R&D-Agent-Quant
    "25": 12,  # QuantAgent-HFT
    "29": 13,  # FinCon ambiguous
}
GOOD_IDEA_NOTES = {
    "1": "benchmark/toolchain for formulaic alpha mining",
    "3": "agentic alpha mining with regularized exploration",
    "5": "RFT loop for executable factor discovery",
    "6": "multi-agent quant R&D loop",
    "21": "principled evolutionary alpha mining baseline",
    "24": "agent contest selection mechanism; needs leakage/cost audit",
    "25": "price-driven HFT agent; code-backed but no Sharpe in paper text",
    "42": "guru-prompted multi-agent portfolio; needs benchmark validity audit",
    "45": "benchmark for executable strategy design; useful harness ideas",
    "47": "live-style benchmark designed to reduce static backtest leakage",
    "48": "live fund benchmark/time-travel critique",
    "51": "stress-test harness for trading-agent reliability",
}


def slug(text: str) -> str:
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif keep and keep[-1] != "_":
            keep.append("_")
    return "".join(keep).strip("_")[:80] or "untitled"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((LIT / "paper_links.csv").open(newline="")))
    registry = []
    for row in rows:
        ref = row["ref_index"]
        title = row["project_or_paper"] or row["reference_title"]
        if ref in STRICT_CODE:
            code_status = "real_public_code"
            code_url = STRICT_CODE[ref]
        elif ref in AMBIGUOUS_CODE:
            code_status = "ambiguous_unofficial_code"
            code_url = AMBIGUOUS_CODE[ref]
        elif ref in PLACEHOLDER_OR_EMPTY_CODE:
            code_status = "placeholder_or_empty_repo"
            code_url = PLACEHOLDER_OR_EMPTY_CODE[ref]
        else:
            code_status = "no_confirmed_real_code"
            code_url = ""
        if ref in SHARPE_STRATEGY:
            sharpe_status = "reports_strategy_sharpe"
        elif ref in SHARPE_CRITIQUE:
            sharpe_status = "reports_sharpe_in_critique"
        else:
            sharpe_status = "no_strategy_sharpe_found"
        execution_state = "queued"
        if code_status not in {"real_public_code", "ambiguous_unofficial_code"}:
            execution_state = "queued_reimplementation_or_skip_decision"
        registry.append({
            "priority": PRIORITY.get(ref, 900 + int(ref)),
            "ref_index": ref,
            "run_id": f"{int(ref):03d}_{slug(title)}",
            "title": title,
            "section": row["section"],
            "paper_url": row["paper_or_project_url"],
            "downloaded_pdf": row["downloaded_pdf"],
            "download_status": row["download_status"],
            "code_status": code_status,
            "code_url": code_url,
            "sharpe_status": sharpe_status,
            "good_idea_note": GOOD_IDEA_NOTES.get(ref, "needs paper-specific idea extraction"),
            "adapter_status": "missing",
            "candidate_returns_status": "missing",
            "ff3_ff5mom_status": "not_run",
            "execution_state": execution_state,
            "verdict": "pending",
        })
    registry.sort(key=lambda r: (int(r["priority"]), int(r["ref_index"])))
    out_csv = OUT / "registry.csv"
    with out_csv.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(registry[0].keys()))
        writer.writeheader()
        writer.writerows(registry)
    summary = {
        "registry_rows": len(registry),
        "strict_real_public_code_rows": sum(r["code_status"] == "real_public_code" for r in registry),
        "ambiguous_unofficial_code_rows": sum(r["code_status"] == "ambiguous_unofficial_code" for r in registry),
        "strategy_sharpe_rows": sum(r["sharpe_status"] == "reports_strategy_sharpe" for r in registry),
        "completed_ff3_ff5mom_rows": sum(r["ff3_ff5mom_status"] == "completed" for r in registry),
        "strict_serious_rows": 0,
    }
    (OUT / "status.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
