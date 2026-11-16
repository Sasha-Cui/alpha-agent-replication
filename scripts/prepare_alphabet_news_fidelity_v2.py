#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Append dated same-issuer GOOG news without changing GOOGL prices or frozen inputs."""

from pathlib import Path
import sys
import json
import hashlib
import argparse
import pandas as pd
import tiktoken

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.publication_llm import canonical_meter
from alpha_evolve.openrouter_budget import atomic_json, sha256, read_key
from alpha_evolve.fidelity_text_v2 import context_safe_chunks

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"
SOURCE = ROOT / "artifacts/publication_upgrade_v1/finsaber_data"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    base = PRIVATE / f"GOOGL_{args.start}_{args.end}_inputs.json"
    view = json.loads(base.read_text())
    output = PRIVATE / f"GOOGL_{args.start}_{args.end}_company_news_inputs.json"
    if output.exists():
        raise ValueError("Preserve completed company-news input")
    if view["symbol"] != "GOOGL":
        raise ValueError("Unexpected target security")
    prices_before = json.dumps(view["prices"], sort_keys=True, separators=(",", ":"))
    dates = pd.DatetimeIndex([row["date"] for row in view["prices"]])
    if dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("Invalid GOOGL calendar")
    rows = pd.concat(
        [
            pd.read_parquet(SOURCE / "news_items" / f"year={year}/part-000.parquet", filters=[("symbol", "==", "GOOG")])
            for year in range(2021, 2025)
        ],
        ignore_index=True,
    )
    rows["date"] = pd.to_datetime(rows.date)
    rows = rows[(rows.date >= pd.Timestamp(args.start) - pd.Timedelta(days=30)) & (rows.date <= args.end)].sort_values(
        "date", kind="stable"
    )
    if rows.cik.isna().any() or set(rows.cik.astype(str)) != {"0001652044"}:
        raise ValueError("Unverified issuer mapping")
    enc = tiktoken.get_encoding("cl100k_base")
    meter = canonical_meter(
        ROOT,
        "unused" if args.offline else read_key(ROOT.parent / "KnowledgeTemplate/.env"),
        model="openai/gpt-3.5-turbo",
        study="fidelity_v2_input_summaries",
        cap=5,
        input_price=0.5,
        output_price=1.5,
        offline=args.offline,
    )

    def call(text):
        result, _ = meter.chat(
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Summarize the following news within 200 tokens:\n{text}\nSummary:"},
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return result["choices"][0]["message"]["content"]

    def summarize(text):
        if len(enc.encode(text)) <= 200:
            return text, "unchanged_short_text"
        summaries = [call(chunk) for chunk in context_safe_chunks(text, enc)]
        while len(summaries) > 1:
            summaries = [call(chunk) for chunk in context_safe_chunks("\n".join(summaries), enc)]
        return summaries[0], "source_prompt_current_gpt35_full_coverage_mapreduce_utf8_context_safe"

    seen = {(row["date"], row["source_sha256"]) for row in view["items"] if row["kind"] == "news_items"}
    added = []
    duplicates = 0
    for row in rows.itertuples():
        text = row.news_text
        day = row.date.strftime("%Y-%m-%d")
        digest = hashlib.sha256(text.encode()).hexdigest()
        identity = (day, digest)
        if identity in seen:
            duplicates += 1
            continue
        index = dates.searchsorted(row.date, side="right")
        if index == len(dates):
            raise ValueError("No next-session availability date")
        summary, method = summarize(text)
        added.append(
            {
                "kind": "news_items",
                "date": day,
                "available_date": dates[index].strftime("%Y-%m-%d"),
                "text": summary,
                "method": method,
                "source_sha256": digest,
                "source_symbol": "GOOG",
                "company_cik": "0001652044",
            }
        )
        seen.add(identity)
    view["items"].extend(added)
    view["items"] = sorted(view["items"], key=lambda row: (row["available_date"], row["date"], row["kind"]))
    if json.dumps(view["prices"], sort_keys=True, separators=(",", ":")) != prices_before:
        raise ValueError("Security price substitution forbidden")
    atomic_json(output, view)
    atomic_json(
        output.with_name(output.stem + "_manifest.json"),
        {
            "status": "complete",
            "sha256": sha256(output),
            "base_input_sha256": sha256(base),
            "source_symbol": "GOOG",
            "target_security": "GOOGL",
            "verified_common_cik": "0001652044",
            "added_news": len(added),
            "duplicate_date_text_items_not_added": duplicates,
            "original_items_preserved": True,
            "original_prices_preserved": True,
            "date_only_lag": "strictly next GOOGL trading session",
            "dedup_rule": "Do not alter base items; append only news date/source-text hashes absent from base or earlier appended GOOG rows",
            "script_sha256": sha256(Path(__file__)),
            "usage": meter.snapshot(),
            "request_trace": meter.request_trace,
        },
    )
    print("COMPANY_NEWS_INPUT_COMPLETE", len(added), str(output), flush=True)


if __name__ == "__main__":
    main()
