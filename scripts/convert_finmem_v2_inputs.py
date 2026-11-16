#!/usr/bin/env python3
"""Translate already dated/summarized inputs into the unchanged FinMem actor schema."""

from pathlib import Path
import json
import argparse

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    a = p.parse_args()
    folder = ROOT / "artifacts/fidelity_completion_v2"
    data = json.loads((folder / f"{a.symbol}_2021-08-17_2023-04-12_inputs.json").read_text())
    views = {
        r["date"]: {
            **{k: r[k] for k in ["date", "close", "adjusted_close", "open"]},
            "news": [],
            "filingk": [],
            "filingq": [],
            "input_dates": [],
        }
        for r in data["prices"]
        if "2021-08-17" <= r["date"] <= "2023-04-12"
    }
    provenance = []
    for row in data["items"]:
        day = row["available_date"]
        if row["date"] < "2021-08-17" or day not in views:
            continue
        assert row["date"] < day
        kind = "news" if row["kind"] == "news_items" else row["kind"]
        views[day][kind].append(row["text"])
        views[day]["input_dates"].append(row["date"])
        provenance.append(
            {"source_date": row["date"], "available_date": day, "kind": kind, "source_sha256": row["source_sha256"]}
        )
    out = {"symbol": a.symbol, "rows": [views[k] for k in sorted(views)], "provenance": provenance}
    (folder / f"finmem_{a.symbol}_inputs.json").write_text(json.dumps(out, sort_keys=True) + "\n")
    print("FINMEM_INPUTS_READY", a.symbol, len(views), len(provenance))


if __name__ == "__main__":
    main()
