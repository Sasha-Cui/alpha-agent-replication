#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Freeze daily prices and complete, lagged alternative text for source adapters."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import argparse
import hashlib
import urllib.error
import urllib.request
import pandas as pd
import tiktoken
from alpha_evolve.openrouter_budget import atomic_json, read_key, sha256
from alpha_evolve.publication_llm import canonical_meter
from alpha_evolve.fidelity_text_v2 import context_safe_chunks

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"
SOURCE_DATA = ROOT / "artifacts/publication_upgrade_v1/finsaber_data"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--context-repair", action="store_true", help="Full-coverage UTF8 byte bound for the diagnosed provider context rejection")
    args = p.parse_args()
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
    original_urlopen = urllib.request.urlopen
    def diagnosed_urlopen(*request_args, **request_kwargs):
        try:
            return original_urlopen(*request_args, **request_kwargs)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace").replace(meter.key, "[REDACTED]")
            atomic_json(PRIVATE / (args.symbol + "_provider_error.json"), {"http_status": error.code, "body": body, "request_retried_here": False})
            raise
    urllib.request.urlopen = diagnosed_urlopen
    tables = {
        kind: pd.concat(
            [
                pd.read_parquet(
                    SOURCE_DATA / kind / f"year={year}" / "part-000.parquet",
                    filters=[("symbol", "==", args.symbol)],
                )
                for year in range(2021, 2025)
            ],
            ignore_index=True,
        )
        for kind in ["price_daily", "news_items", "filingk", "filingq"]
    }
    prices = tables["price_daily"].sort_values("date")
    prices["date"] = pd.to_datetime(prices.date)
    prices = prices.drop_duplicates("date")
    dates = pd.DatetimeIndex(prices.date)
    prices = prices[
        (prices.date >= pd.Timestamp(args.start) - pd.Timedelta(days=450))
        & (prices.date <= pd.Timestamp(args.end) + pd.Timedelta(days=7))
    ].copy()
    prices["date"] = prices.date.dt.strftime("%Y-%m-%d")
    prices = prices.drop(columns=["cik"], errors="ignore")
    enc = tiktoken.get_encoding("cl100k_base")

    def call(t):
        r, _ = meter.chat(
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Summarize the following news within 200 tokens:\n{t}\nSummary:"},
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return r["choices"][0]["message"]["content"]

    def chunks(text):
        if args.context_repair:
            return context_safe_chunks(text, enc)
        tokens = enc.encode(text)
        return [enc.decode(tokens[k:k+6000]) for k in range(0,len(tokens),6000)]

    def summarize(text):
        tokens = enc.encode(text)
        if len(tokens) <= 200:
            return text, "unchanged_short_text"
        summaries = [call(chunk) for chunk in chunks(text)]
        while len(summaries) > 1:
            summaries = [call(chunk) for chunk in chunks("\n".join(summaries))]
        return summaries[0], "source_prompt_current_gpt35_full_coverage_mapreduce" + ("_utf8_context_safe" if args.context_repair else "")

    items = []
    for kind in ["news_items", "filingk", "filingq"]:
        frame = tables[kind].copy()
        frame["date"] = pd.to_datetime(frame.date)
        frame = frame.sort_values("date")
        lower = pd.Timestamp(args.start) - pd.Timedelta(days=30 if kind == "news_items" else 450)
        frame = frame[(frame.date >= lower) & (frame.date <= pd.Timestamp(args.end))]
        for n, row in enumerate(frame.itertuples()):
            i = dates.searchsorted(row.date, side="right")
            if i >= len(dates):
                continue
            text = getattr(row, "news_text" if kind == "news_items" else "filing_text")
            summary, method = summarize(text)
            items.append(
                {
                    "kind": kind,
                    "date": row.date.strftime("%Y-%m-%d"),
                    "available_date": dates[i].strftime("%Y-%m-%d"),
                    "text": summary,
                    "method": method,
                    "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
                }
            )
            if n % 100 == 0:
                print(args.symbol, kind, n, "of", len(frame), meter.snapshot(), flush=True)
    output = PRIVATE / f"{args.symbol}_{args.start}_{args.end}_inputs.json"
    atomic_json(output, {"symbol": args.symbol, "prices": prices.to_dict("records"), "items": items})
    atomic_json(
        output.with_name(output.stem + "_manifest.json"),
        {
            "sha256": sha256(output),
            "script_sha256": sha256(Path(__file__)),
            "requested_period": [args.start, args.end],
            "source_revision": "68bb21ef1500591c6f81e0cb934bcf079e807e38",
            "date_only_lag": "strictly next trading session",
            "source_snapshot_exact": False,
            "context_chunking": "Lossless<=6000cl100k_tokens_and<=12000UTF8bytes" if args.context_repair else "legacy6000cl100k_tokens",
            "usage": meter.snapshot(),
            "request_trace": meter.request_trace,
        },
    )
    print("COMPLETE", output, flush=True)


if __name__ == "__main__":
    main()
