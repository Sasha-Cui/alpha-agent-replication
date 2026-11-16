#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Independent checks of input timing, source endpoints, native model traces and budgets."""

from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256

PRIVATE = ROOT / "artifacts/publication_upgrade_v1"
PUBLIC = ROOT / "paper_runs/publication_upgrade_v1"


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    results = {}
    errors = []
    finmem = json.loads((PRIVATE / "finmem_inputs.json").read_text())
    manifest = json.loads((PRIVATE / "finmem_input_manifest.json").read_text())
    if sha256(PRIVATE / "finmem_inputs.json") != manifest["data_sha256"]:
        errors.append("FinMem prepared input changed")
    if any(r["source_date"] >= r["available_date"] for r in finmem["provenance"]):
        errors.append("FinMem date-only availability violation")
    for filename in ["AAPL_2024-01-02_2024-03-28_inputs.json", "TSLA_2022-06-01_2023-12-29_inputs.json"]:
        data = json.loads((PRIVATE / filename).read_text())
        meta = json.loads((PRIVATE / filename.replace(".json", "_manifest.json")).read_text())
        if sha256(PRIVATE / filename) != meta["sha256"]:
            errors.append("Prepared input changed: " + filename)
        if any(r["date"] >= r["available_date"] for r in data["items"]):
            errors.append("Date-only availability violation: " + filename)
        results[filename] = {
            "items": len(data["items"]),
            "quote_rows": len(data["prices"]),
            "sha256": sha256(PRIVATE / filename),
        }
    ledger = json.loads((ROOT / "runs/economic_fidelity/openrouter/project_spend.json").read_text())
    for case, chat, embedding in [
        ("finmem", "openai/gpt-4-turbo", "openai/text-embedding-ada-002"),
        ("finagent", "openai/gpt-4o", "openai/text-embedding-3-large"),
    ]:
        folder = PRIVATE / (case + "_native")
        if not (folder / "completion.json").exists():
            raise RuntimeError("Native case still running: " + case)
        rows = lines(folder / "decisions.jsonl")
        request_hashes = {call["request_hash"] for row in rows for call in row["requests"]}
        for key in request_hashes:
            call = ledger["calls"][key]
            if call["status"] != "complete":
                errors.append("Noncomplete response in a final trajectory")
            expected = embedding if call.get("endpoint") == "embeddings" else chat
            if call["model"] != expected:
                errors.append(f"{case}: wrong model {call['model']}")
        results[case] = {
            "records": len(rows),
            "unique_consumed_requests": len(request_hashes),
            "chat_model": chat,
            "embedding_model": embedding,
        }
        if case == "finmem":
            recipe = json.loads((PUBLIC / "finmem_recipe.json").read_text())
            dates = [r["date"] for r in finmem["rows"]]
            train = [r for r in rows if r["mode"] == "Train"]
            tests = [r for r in rows if r["mode"] == "Test"]
            last = max(r["date"] for r in train)
            last_label = dates[dates.index(last) + 1]
            if last_label > recipe["train_end"]:
                errors.append("FinMem training label crosses boundary")
            if any(r["date"] >= recipe["test_end"] for r in tests):
                errors.append("FinMem terminal date was used as an actor step")
            if any(r["latest_external_input_date"] and r["latest_external_input_date"] >= r["date"] for r in rows):
                errors.append("FinMem future/same-date text was supplied")
            results[case].update(last_training_decision=last, last_training_label=last_label, test_records=len(tests))
        else:
            training = [r for r in rows if r["mode"] == "train"]
            tests = [r for r in rows if r["mode"] == "valid"]
            if any(r["latest_price_in_state"] > "2023-05-31" for r in training):
                errors.append("FinAgent training sees validation prices")
            if any(
                r["latest_price_in_state"] > r["date"]
                or (r["latest_news_available_date"] and r["latest_news_available_date"] > r["date"])
                for r in tests
            ):
                errors.append("FinAgent validation sees future inputs")
            for arm in ["native_causal", "no_retrieval"]:
                selected = sorted([r for r in tests if r["arm"] == arm], key=lambda r: r["date"])
                previous = "HOLD"
                for row in selected:
                    if row["executed_previous_decision"] != previous:
                        errors.append("FinAgent execution does not match previous decision")
                    if row["realization_date"] != row["date"]:
                        errors.append("FinAgent NAV is assigned to the wrong date")
                    previous = row["decision"]
                # The source runner serialized numpy.bool_ through default=str.
                # Decode only its explicit literals; bool("False") is incorrect.
                raw_flags = [r["terminal_valuation"] for r in selected]
                if any(type(v) is not bool and v not in ("True", "False") for v in raw_flags):
                    errors.append("FinAgent terminal valuation flag is not a declared boolean literal")
                flags = [v is True or v == "True" for v in raw_flags]
                if sum(flags) != 1 or not flags[-1]:
                    errors.append("FinAgent terminal valuation convention failed")
            results[case].update(training_records=len(training), validation_records=len(tests))
    trading = json.loads((PRIVATE / "tradingagents_native/decisions.json").read_text())
    count = 0
    for row in trading:
        for call in row["tool_trace"]:
            count += 1
            if call["effective_cutoff"] > row["date"] or call["driver_cutoff"] != row["date"]:
                errors.append("TradingAgents tool cutoff violation")
            if call.get("latest_input_date") and call["latest_input_date"] > row["date"]:
                errors.append("TradingAgents future tool input")
    results["tradingagents"] = {"days": len(trading), "bounded_tool_events": count}
    source_proposals = json.loads((ROOT / "paper_runs/economic_fidelity/efs_v1/llm_proposals.json").read_text())
    expected = sum("code" in p for p in source_proposals)
    for seed in range(101, 111):
        record = json.loads((PRIVATE / f"efs_matched/seed_{seed}/completion.json").read_text())
        if record["candidate_count"] != expected:
            errors.append("EFS candidate count not matched")
    results["efs"] = {"matched_seeds": 10, "candidate_slots_each": expected}
    status = {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "checks": results,
        "interpretation": "Timing/model/account validation is automated technical evidence, not human source review or proof of original data/model equivalence.",
    }
    atomic_json(PRIVATE / "execution_contract_validation.json", status)
    print(json.dumps({"status": status["status"], "errors": errors}))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
