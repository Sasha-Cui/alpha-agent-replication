#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Validate report links, figure/table pairing, PDF text and scientific status gates."""

from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader
from alpha_evolve.openrouter_budget import atomic_json, sha256


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--preview", action="store_true")
    args = p.parse_args()
    out = ROOT / "paper_runs/publication_upgrade_v1"
    manifest = json.loads(
        (out / ("report_preview_manifest.json" if args.preview else "report_manifest.json")).read_text()
    )
    visual = (out / manifest["visual_report"]).read_text()
    plain = (out / manifest["no_image_report"]).read_text()
    errors = []
    if manifest["builder_sha256"] != sha256(ROOT / "scripts/build_publication_report.py"):
        errors.append("Report builder changed after the rendered artifact")
    if manifest["spend_summary_sha256"] != sha256(out / "spend_summary.json"):
        errors.append("Report spending snapshot is stale")
    for section in [
        "Abstract",
        "Research question",
        "Economic contracts",
        "Matched design",
        "Paired economic effects",
        "Costs and controlled adaptations",
        "Calibration and factor identification",
        "JKP-only",
        "Prospective record",
        "Reproducibility",
        "References",
    ]:
        if section not in plain:
            errors.append("Missing section: " + section)
    if re.search(r"!\[|```mermaid", plain):
        errors.append("No-image report contains an image or Mermaid")
    image_records = []
    for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", visual):
        target = out / match.group(1)
        if not target.exists():
            errors.append("Missing image: " + str(target))
            continue
        with Image.open(target) as image:
            pixels = np.asarray(image.convert("RGB"))
            width, height = image.size
            if min(width, height) < 200 or float(pixels.std()) < 2:
                errors.append("Blank or undersized figure: " + target.name)
        after = visual[match.end() :].lstrip()
        if not after.startswith("|"):
            errors.append("Figure not immediately followed by a table: " + target.name)
        image_records.append({"name": target.name, "width": width, "height": height, "sha256": sha256(target)})
    for match in re.finditer(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", visual):
        link = match.group(1)
        if link.startswith(("https://", "http://", "#")):
            continue
        if not (out / link).exists():
            errors.append("Missing audit link: " + link)
    analysis = out / ("analysis_preview" if args.preview else "analysis")
    for name, digest in manifest["analysis_file_sha256"].items():
        if sha256(analysis / name) != digest:
            errors.append("Analysis changed after rendering: " + name)
    effects = pd.read_csv(analysis / "paired_effects.csv")
    returns = pd.read_parquet(
        ROOT
        / "artifacts/publication_upgrade_v1"
        / ("analysis_preview_returns.parquet" if args.preview else "analysis_returns.parquet")
    )
    for entry in manifest["figures"]:
        if entry["name"] not in ["paths_long", "paths_short"]:
            continue
        presentation = pd.read_csv(out / entry["presentation_table"])
        for row in presentation.to_dict("records"):
            pair = effects[(effects["case"] == row["Case"]) & (effects.role == "primary")].iloc[0]
            for side, column in [("left", "Tested total return (%)"), ("right", "Control total return (%)")]:
                values = (
                    returns[(returns["case"] == row["Case"]) & (returns.arm == pair[side])]
                    .sort_values("date")["return"]
                    .to_numpy()
                )
                expected = 100 * (np.prod(1 + values) - 1)
                if column not in row or abs(float(row[column]) - expected) > 0.006:
                    errors.append("Incorrect holding-period return label/value: " + row["Case"] + " " + side)
    pdf = out / manifest["pdf"]
    if sha256(pdf) != manifest["pdf_sha256"]:
        errors.append("PDF differs from the report manifest")
    reader = PdfReader(pdf)
    texts = [page.extract_text() or "" for page in reader.pages]
    for index, text in enumerate(texts, 1):
        if len(text.strip()) < 60:
            errors.append(f"Page {index} has no useful text")
        if "\u25a0" in text or "\ufffd" in text:
            errors.append(f"Page {index} contains a missing-glyph marker")
    joined = "\n".join(texts)
    if re.search(r"\b(TODO|TBD|PLACEHOLDER)\b", joined):
        errors.append("Unresolved placeholder in PDF")
    if not args.preview:
        if (
            manifest["analysis_status"]["status"] != "complete"
            or len(manifest["analysis_status"]["complete_cases"]) != 6
        ):
            errors.append("Final report lacks six complete case studies")
        if manifest["analysis_status"]["open_cases"]:
            errors.append("Final report has open historical cases")
    # Reviews and future data are explicit external conditions, never auto-approved.
    ledger = json.loads((out / "source_review/human_review_ledger.json").read_text())
    if not ledger["reviews"] and ledger["independent_human_review_complete"]:
        errors.append("Empty human ledger falsely marked complete")
    result = {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "pages": len(reader.pages),
        "figures": image_records,
        "pdf_sha256": sha256(pdf),
        "human_review_complete": ledger["independent_human_review_complete"],
        "visual_inspection_required": True,
        "preview": args.preview,
    }
    atomic_json(out / ("report_preview_validation.json" if args.preview else "report_validation.json"), result)
    print(
        json.dumps(
            {"status": result["status"], "pages": result["pages"], "figures": len(image_records), "errors": errors}
        )
    )
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
