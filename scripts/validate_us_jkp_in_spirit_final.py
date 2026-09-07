#!/usr/bin/env python3
"""Validate the final 69-paper in-spirit visual and audit synthesis."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
from PIL import Image


REQUIRED_SECTIONS = [
    "## Executive answer",
    "## 1. Final disposition",
    "## 2. Raw common-path performance",
    "## 3. JKP benchmark attribution",
    "## 4. Raw return versus benchmark distinctness",
    "## 5. Fidelity and claim boundary",
    "## 6. Metric contract",
    "## 7. Reproducibility and artifact index",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path) -> None:
    study = root / "paper_runs/us_jkp_in_spirit"
    manifest_path = study / "final_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    exact = {
        "status": "complete",
        "paper_milestones": 69,
        "carried_strict_evaluations": 17,
        "researcher_authored_in_spirit_reconstructions": 45,
        "structural_discards": 7,
        "common_paths_evaluated": 62,
        "full_native_systems_reproduced_end_to_end": 0,
        "native_empirical_claims_tested": 0,
        "holm_family_size": 69,
    }
    for key, expected in exact.items():
        if manifest.get(key) != expected:
            raise ValueError(f"manifest {key} changed: {manifest.get(key)!r}")
    for relative, expected in manifest["input_sha256"].items():
        path = root / relative
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"stale or missing synthesis input: {relative}")
    builder = root / manifest["builder_path"]
    if digest(builder) != manifest["builder_sha256"]:
        raise ValueError("final synthesis builder changed without regeneration")
    for relative, expected in manifest["output_sha256"].items():
        path = study / relative
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"stale or missing synthesis output: {relative}")

    complete = pd.read_csv(study / "visual_tables/complete_results_full_audit.csv")
    family = pd.read_csv(study / "visual_tables/family_inference_full_audit.csv")
    classes = pd.read_csv(study / "visual_tables/evaluation_class_summary_full_audit.csv")
    if complete.milestone_id.tolist() != [f"M{number:03d}" for number in range(1, 70)]:
        raise ValueError("complete result table is not an ordered 69-paper ledger")
    if complete.disposition.value_counts().to_dict() != {
        "completed_in_spirit": 45,
        "carried_common_evaluation": 17,
        "discarded_structural_mismatch": 7,
    }:
        raise ValueError("complete result disposition counts changed")
    evaluated = complete.loc[complete.common_jkp_evaluated]
    discarded = complete.loc[~complete.common_jkp_evaluated]
    if len(evaluated) != len(family) or len(evaluated) != 62:
        raise ValueError("common result and family tables do not contain 62 paths")
    metric_columns = [
        "full_cagr",
        "full_annualized_sharpe",
        "full_maximum_drawdown",
        "jkp_excess_annualized",
        "jkp_excess_p_two_sided",
    ]
    if not np.isfinite(evaluated[metric_columns].to_numpy(float)).all():
        raise ValueError("evaluated result table contains nonfinite primary metrics")
    if discarded[metric_columns].notna().any().any():
        raise ValueError("structural discards must keep performance missing")
    if family.raw_p_two_sided.tolist() != sorted(family.raw_p_two_sided.tolist()):
        raise ValueError("family inference is not ordered by raw p-value")
    if family.holm_multiplier.tolist() != list(range(69, 7, -1)):
        raise ValueError("Holm multipliers do not preserve the declared 69-paper family")
    if classes.paper_count.sum() != 69 or classes.common_path_count.sum() != 62:
        raise ValueError("evaluation-class summary counts changed")

    visual_path = study / "VISUAL_REPORT.md"
    no_image_path = study / "REPORT.md"
    visual = visual_path.read_text()
    no_image = no_image_path.read_text()
    for section in REQUIRED_SECTIONS:
        if section not in visual or section not in no_image:
            raise ValueError(f"required report section missing: {section}")
    if "![" in no_image or "```mermaid" in no_image:
        raise ValueError("table-first report contains image or Mermaid markup")
    stale_terms = ["not run", "placeholder text", "TODO"]
    for term in stale_terms:
        if term.lower() in visual.lower() or term.lower() in no_image.lower():
            raise ValueError(f"stale report term found: {term}")

    image_links = re.findall(r"!\[[^]]*\]\(([^)]+)\)", visual)
    if len(image_links) != 4:
        raise ValueError(f"expected four report figures, found {len(image_links)}")
    lines = visual.splitlines()
    for relative in image_links:
        path = study / relative
        if not path.is_file() or path.stat().st_size < 10_000:
            raise ValueError(f"missing or suspiciously small figure: {relative}")
        with Image.open(path) as image:
            rgb = np.asarray(image.convert("RGB"))
            if image.width < 900 or image.height < 600 or float(rgb.std()) < 5.0:
                raise ValueError(f"blank or undersized figure: {relative}")
        image_line = next(index for index, line in enumerate(lines) if f"]({relative})" in line)
        following = next((line for line in lines[image_line + 1 :] if line.strip()), "")
        if not following.startswith("|"):
            raise ValueError(f"figure is not immediately followed by a compact table: {relative}")

    csv_links = re.findall(r"\[[^]]+\]\((visual_tables/[^)]+\.csv)\)", visual)
    if len(csv_links) < 5 or any(not (study / relative).is_file() for relative in csv_links):
        raise ValueError("report contains a broken or incomplete full-audit CSV link set")
    print("final in-spirit synthesis validated")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    validate(args.root.resolve())


if __name__ == "__main__":
    main()
