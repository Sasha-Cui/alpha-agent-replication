#!/usr/bin/env python3
"""Execute one unchanged generated factor against an isolated historical HDF view."""

from pathlib import Path
import argparse
import os
import runpy
import socket
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--code", type=Path, required=True)
parser.add_argument("--data", type=Path, required=True)
parser.add_argument("--work", type=Path, required=True)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--cutoff")
args = parser.parse_args()
code, data, work, source = (p.resolve() for p in [args.code, args.data, args.work, args.source])
work.mkdir(parents=True, exist_ok=True)
(work / "daily_pv.h5").symlink_to(data)
os.chdir(work)
__import__("sys").path.insert(0, str(source))
original = pd.read_hdf
reads = []


def bounded(path, *a, **kw):
    frame = original(path, *a, **kw)
    if Path(path).resolve() != data:
        raise RuntimeError("Unexpected external HDF input")
    if args.cutoff:
        frame = frame.loc[frame.index.get_level_values("datetime") <= pd.Timestamp(args.cutoff)].copy()
        frame.index = frame.index.remove_unused_levels()
    reads.append({"rows": len(frame), "latest_date": str(frame.index.get_level_values("datetime").max())})
    return frame


pd.read_hdf = bounded


def offline(*a, **kw):
    raise RuntimeError("Factor calculation must not access the network")


socket.create_connection = offline
socket.socket.connect = offline
runpy.run_path(str(code), run_name="__main__")
if not reads:
    raise RuntimeError("Factor did not consume the declared input")
(work / "reads.json").write_text(__import__("json").dumps(reads, indent=2) + "\n")
