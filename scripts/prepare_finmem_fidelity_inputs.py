#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Dated alternative-input adapter; never deserialize third-party pickles."""

from pathlib import Path
import argparse
import pandas as pd
import tiktoken
from alpha_evolve.openrouter_budget import atomic_json, read_key, sha256
from alpha_evolve.publication_llm import canonical_meter

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "artifacts/publication_upgrade_v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    out = PRIVATE / "finmem_inputs.json"
    meter = canonical_meter(
        ROOT,
        "unused" if args.offline else read_key(ROOT.parent / "KnowledgeTemplate/.env"),
        model="openai/gpt-3.5-turbo",
        study="finmem_input_summaries_v1",
        cap=15,
        input_price=0.5,
        output_price=1.5,
        offline=args.offline,
    )
    source = PRIVATE / "finsaber_data"
    data = {
        kind: pd.concat(
            [
                pd.read_parquet(source / kind / f"year={year}" / "part-000.parquet", filters=[("symbol", "==", "TSLA")])
                for year in (2021, 2022, 2023)
            ],
            ignore_index=True,
        )
        for kind in ["price_daily", "news_items", "filingk", "filingq"]
    }
    prices = data["price_daily"].sort_values("date").copy()
    prices["date"] = pd.to_datetime(prices.date)
    prices = prices.drop_duplicates("date")
    dates = pd.DatetimeIndex(prices.date)
    enc = tiktoken.get_encoding("cl100k_base")
    views = {
        d.strftime("%Y-%m-%d"): {
            "date": d.strftime("%Y-%m-%d"),
            "close": float(r.close),
            "adjusted_close": float(r.adjusted_close),
            "open": float(r.open),
            "news": [],
            "filingk": [],
            "filingq": [],
            "input_dates": [],
        }
        for d, r in zip(dates, prices.itertuples())
        if pd.Timestamp("2021-08-17") <= d <= pd.Timestamp("2023-04-12")
    }
    records = []

    def summarize(text):
        tokens = enc.encode(text)
        if len(tokens) <= 200:
            return text, "unchanged_short_text"
        chunks = [enc.decode(tokens[k : k + 6000]) for k in range(0, len(tokens), 6000)]

        def call(t):
            response, _ = meter.chat(
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Summarize the following news within 200 tokens:\n{t}\nSummary:"},
                ],
                max_tokens=300,
                temperature=0.7,
            )
            return response["choices"][0]["message"]["content"]

        summaries = [call(t) for t in chunks]
        while len(summaries) > 1:
            joined = "\n".join(summaries)
            tokens = enc.encode(joined)
            summaries = [call(enc.decode(tokens[k : k + 6000])) for k in range(0, len(tokens), 6000)]
        return summaries[0], "source_prompt_current_gpt35_chunked" if len(chunks) > 1 else "source_prompt_current_gpt35"

    for kind in ["news_items", "filingk", "filingq"]:
        frame = data[kind].copy()
        frame["date"] = pd.to_datetime(frame.date)
        frame = frame.sort_values(["date"] + (["item_index"] if kind == "news_items" else ["filing_idx"]))
        for row in frame.itertuples():
            if row.date < pd.Timestamp("2021-08-17"):
                continue
            i = dates.searchsorted(row.date, side="right")
            if i >= len(dates):
                continue
            available = dates[i].strftime("%Y-%m-%d")
            if available not in views:
                continue
            text = getattr(row, "news_text" if kind == "news_items" else "filing_text")
            import hashlib

            result, method = summarize(text)
            views[available]["news" if kind == "news_items" else kind].append(result)
            views[available]["input_dates"].append(row.date.strftime("%Y-%m-%d"))
            records.append(
                {
                    "kind": kind,
                    "source_date": row.date.strftime("%Y-%m-%d"),
                    "available_date": available,
                    "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "summary_sha256": hashlib.sha256(result.encode()).hexdigest(),
                    "method": method,
                }
            )
        print(kind, "prepared", sum(r["kind"] == kind for r in records), meter.snapshot(), flush=True)
    atomic_json(out, {"rows": list(views.values()), "provenance": records})
    atomic_json(
        PRIVATE / "finmem_input_manifest.json",
        {
            "data_sha256": sha256(out),
            "script_sha256": sha256(Path(__file__)),
            "source_revision": "68bb21ef1500591c6f81e0cb934bcf079e807e38",
            "availability_rule": "strictly next trading session for date-only text",
            "original_snapshot": False,
            "missing_training_news_before": "2022-05-03",
            "paid_usage": meter.snapshot(),
            "request_trace": meter.request_trace,
        },
    )
    print("COMPLETE", sha256(out), flush=True)


if __name__ == "__main__":
    main()
