#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Physical search-data boundaries and source-compatible AlphaAgent OHLCV schema."""

from pathlib import Path
import sys
import os
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    source = PRIVATE / "quantaalpha_data/full/daily_pv.h5"
    original = pd.read_hdf(source)
    dates = original.index.get_level_values("datetime")
    columns = ["$open", "$close", "$high", "$low", "$volume"]
    target = PRIVATE / "bounded_factor_inputs"
    target.mkdir(exist_ok=True)
    records = {}

    def write(name, frame):
        directory = target / name
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "daily_pv.h5"
        frame = frame.copy()
        frame.index = frame.index.remove_unused_levels()
        if path.exists():
            pd.testing.assert_frame_equal(frame, pd.read_hdf(path), check_exact=True)
            records[name] = {
                "path": str(path),
                "sha256": sha256(path),
                "rows": len(frame),
                "columns": list(frame.columns),
                "start": str(frame.index.get_level_values("datetime").min()),
                "end": str(frame.index.get_level_values("datetime").max()),
                "instruments": int(frame.index.get_level_values("instrument").nunique()),
                "exact_value_roundtrip": True,
            }
            return
        temporary = directory / "daily_pv.tmp.h5"
        frame.to_hdf(temporary, key="data", format="fixed", complib="zlib", complevel=4)
        recovered = pd.read_hdf(temporary)
        pd.testing.assert_frame_equal(frame, recovered, check_exact=True)
        os.replace(temporary, path)
        records[name] = {
            "path": str(path),
            "sha256": sha256(path),
            "rows": len(frame),
            "columns": list(frame.columns),
            "start": str(frame.index.get_level_values("datetime").min()),
            "end": str(frame.index.get_level_values("datetime").max()),
            "instruments": int(frame.index.get_level_values("instrument").nunique()),
            "exact_value_roundtrip": True,
        }
        print("BOUNDED_INPUT", name, records[name]["rows"], records[name]["start"], records[name]["end"], flush=True)

    alpha = original.loc[dates >= pd.Timestamp("2015-01-01"), columns].sort_index()
    write("alphaagent/evaluation", alpha)
    alpha_search = alpha.loc[alpha.index.get_level_values("datetime") <= pd.Timestamp("2025-01-02")]
    write("alphaagent/search", alpha_search)
    instruments = alpha_search.index.get_level_values("instrument").unique()[:100]
    debug = alpha_search.loc[
        (alpha_search.index.get_level_values("datetime") <= pd.Timestamp("2024-12-30"))
        & alpha_search.index.get_level_values("instrument").isin(instruments)
    ]
    write("alphaagent/debug", debug)
    del alpha, alpha_search, debug
    write("quantaalpha/search", original.loc[dates <= pd.Timestamp("2022-01-05")])
    debug_source = PRIVATE / "quantaalpha_data/debug/daily_pv.h5"
    debug = pd.read_hdf(debug_source)
    if debug.index.get_level_values("datetime").max() > pd.Timestamp("2022-01-05"):
        raise ValueError("Debug data crosses search cutoff")
    directory = target / "quantaalpha/debug"
    directory.mkdir(parents=True, exist_ok=True)
    if not (directory / "daily_pv.h5").exists():
        os.link(debug_source, directory / "daily_pv.h5")
    if sha256(directory / "daily_pv.h5") != sha256(debug_source):
        raise ValueError("Frozen Quanta debug input changed")
    records["quantaalpha/debug"] = {
        "path": str(directory / "daily_pv.h5"),
        "sha256": sha256(debug_source),
        "rows": len(debug),
        "columns": list(debug.columns),
        "start": str(debug.index.get_level_values("datetime").min()),
        "end": str(debug.index.get_level_values("datetime").max()),
        "instruments": int(debug.index.get_level_values("instrument").nunique()),
        "identical_to_released_debug": True,
    }
    atomic_json(
        target / "manifest.json",
        {
            "status": "complete",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "original_full_sha256": sha256(source),
            "inputs": records,
            "alpha_debug_rule": "First100 instruments in chronological/instrument sorted source input, through2024-12-30, matching the released generator selection rule. Alternative vendor data remain disclosed.",
            "search_cutoff_rule": "Include only observations through final source-feedback label realization; evaluation data live separately and must never be passed to the search driver.",
            "source_values_changed": False,
            "source_column_projection": "AlphaAgent five originalOHLCVfields; QuantaAlpha retains its released six-field schema.",
            "script_sha256": sha256(Path(__file__)),
        },
    )


if __name__ == "__main__":
    main()
