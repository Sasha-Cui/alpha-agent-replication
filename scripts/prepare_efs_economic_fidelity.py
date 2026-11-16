from pathlib import Path
import csv
import hashlib
import json
import re
from datetime import datetime
import pyarrow as pa
import pyarrow.dataset as ds
import pandas as pd

ROOT = Path("/nfs/roberts/project/pi_btk22/zc362/alpha_evolve")
OUT = ROOT / "artifacts/economic_fidelity/v1"
SOURCE = Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_paper_audit/source_v1/sections")
MAP = ROOT.parent / "KnowledgeTemplate/return_pipeline/return_data_assembly/ticker_mapping/code_to_permno.csv"
DAILY = ROOT.parent / "jkp-data/data/processed/return_data/world_dsf.parquet"
MONTHLY = ROOT.parent / "jkp-data/data/processed/characteristics/USA.parquet"


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


text = (SOURCE / "appendix.tex").read_text()
section = text[text.index("U.S. Stock Symbols") : text.index("\\label{tab:nasdaq_stocks_exact}")]
tickers = re.findall(r"\\cellcolor\{gray!10\}([A-Z][A-Z0-9-]*)\s*&", section)
assert len(tickers) == len(set(tickers)) == 50
rows = list(csv.DictReader(MAP.open()))
mapping = []
for ticker in tickers:
    matches = [
        r for r in rows if r["ticker"] == ticker and r["name_end"] >= "2019-01-01" and r["name_start"] <= "2024-12-31"
    ]
    if ticker == "BRK-B":
        matches = [
            r for r in rows if r["company_name"].startswith("BERKSHIRE HATHAWAY") and r["cusip"].startswith("08467020")
        ]
    if ticker == "META":
        matches = [r for r in rows if r["company_name"].startswith(("FACEBOOK INC", "META PLATFORMS INC"))]
    ids = {int(r["permno"]) for r in matches}
    assert len(ids) == 1, (ticker, ids)
    mapping.append({"ticker": ticker, "permno": ids.pop()})
pa.set_cpu_count(4)
ids = (
    ds.dataset(MONTHLY)
    .to_table(columns=["id", "permno"], filter=ds.field("permno").isin([r["permno"] for r in mapping]))
    .to_pandas()
    .drop_duplicates()
)
for r in mapping:
    vals = ids.loc[ids.permno == r["permno"], "id"].unique()
    if len(vals):
        assert len(vals) == 1 and int(vals[0]) == r["permno"], (r, vals)
    r["id"] = r["permno"]  # JKP's CRSP daily loader sets id=permno, including ADRs.
pd.DataFrame(mapping).to_csv(OUT / "efs_us50_identity.csv", index=False)
print("mapped all 50 paper tickers", flush=True)
data = ds.dataset(DAILY)
filter_ = (
    ds.field("id").isin([r["id"] for r in mapping])
    & (ds.field("date") >= pa.scalar(datetime(2018, 10, 1), type=data.schema.field("date").type))
    & (ds.field("date") <= pa.scalar(datetime(2024, 12, 31), type=data.schema.field("date").type))
)
frame = data.to_table(
    columns=["id", "date", "prc", "adjfct", "ret", "ret_exc", "source_crsp", "excntry"], filter=filter_
).to_pandas()
frame = frame.merge(pd.DataFrame(mapping), on="id", validate="many_to_one").sort_values(["date", "ticker"])
assert not frame.duplicated(["date", "ticker"]).any()
frame["adjusted_close"] = frame.prc.abs() / frame.adjfct
frame.to_parquet(OUT / "efs_us50_daily.parquet", index=False)
print("daily extraction", len(frame), str(frame.date.min()), str(frame.date.max()), frame.ticker.nunique(), flush=True)
manifest = {
    "source_daily_path": str(DAILY),
    "source_daily_bytes": DAILY.stat().st_size,
    "source_daily_mtime_ns": DAILY.stat().st_mtime_ns,
    "extraction_columns": list(frame.columns),
    "source_mapping_path": str(MAP),
    "source_mapping_sha256": digest(MAP),
    "daily_extract_sha256": digest(OUT / "efs_us50_daily.parquet"),
    "identity_sha256": digest(OUT / "efs_us50_identity.csv"),
    "source_tex_sha256": {
        p.name: digest(p) for p in [SOURCE / "appendix.tex", SOURCE / "methodology.tex", SOURCE / "experiments.tex"]
    },
    "rows": len(frame),
    "tickers": 50,
    "start": str(frame.date.min()),
    "end": str(frame.date.max()),
    "adjustment": "abs(prc)/adjfct, matching JKP code/aux_functions.py prc_adj",
    "universe_boundary": "Paper v1 static US50 universe; not a point-in-time selected universe; IPOs are not backfilled.",
}
(OUT / "data_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("data ready", flush=True)
