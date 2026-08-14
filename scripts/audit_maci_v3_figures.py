#!/usr/bin/env python3
"""Verify cryptoMAS v3 author-figure correspondence without result inflation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pdfplumber


EXPECTED = {
    "flow.pdf": (
        "7c16b3933b02707bb0d84b77d3ade99307b942ab0c013ad1ddeafaaf25f7741a",
        "7c16b3933b02707bb0d84b77d3ade99307b942ab0c013ad1ddeafaaf25f7741a",
    ),
    "model_comparison_ann_vol.pdf": (
        "7386a4f8c8645748ddc171ac0ba094ebace80396d883e94b181c43064235fb0a",
        "7386a4f8c8645748ddc171ac0ba094ebace80396d883e94b181c43064235fb0a",
    ),
    "model_comparison_cum_ret.pdf": (
        "a932df3b3878d5bd56aa1a76ff0b5032fdae0e38d7cbdf2756486f16ef0a1782",
        "a932df3b3878d5bd56aa1a76ff0b5032fdae0e38d7cbdf2756486f16ef0a1782",
    ),
    "portfolio.pdf": (
        "368433897d6036075704eb276f06f690b174beffd4e660f2516b0e581cfbb505",
        "2e4af2bf512a936d83e546a7d4f401d92ec10f89b1002963cd701f91ed7e8ced",
    ),
    "risk_return.pdf": (
        "003266b78dbd2418786c84b8032ab86d69a62f9b9b526a899f785cddf348b549",
        "5dccf3fdd8514bfdd63864894d739235dd58fc17fcbf0b7b559044eb1295b952",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def style(curve: dict[str, Any]) -> tuple[str, str, int]:
    return str(curve.get("stroking_color")), str(curve.get("dash")), len(curve["pts"])


def pair_curves(
    paper: list[dict[str, Any]], author: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], dict[str, Any], float]]:
    used: set[int] = set()
    pairs = []
    for left in paper:
        candidates = []
        for index, right in enumerate(author):
            if index in used or style(left) != style(right):
                continue
            maximum_y = max(
                abs(point_left[1] - point_right[1]) for point_left, point_right in zip(left["pts"], right["pts"])
            )
            candidates.append((maximum_y, index, right))
        if not candidates:
            raise ValueError(f"cannot pair v3 portfolio curve style {style(left)}")
        maximum_y, index, right = min(candidates, key=lambda item: item[0])
        used.add(index)
        pairs.append((left, right, maximum_y))
    return pairs


def portfolio_geometry(paper_path: Path, author_path: Path) -> dict[str, Any]:
    with pdfplumber.open(paper_path) as paper_pdf, pdfplumber.open(author_path) as author_pdf:
        paper_page = paper_pdf.pages[0]
        author_page = author_pdf.pages[0]
        paper_curves = [curve for curve in paper_page.curves if len(curve["pts"]) == 52]
        author_curves = [curve for curve in author_page.curves if len(curve["pts"]) == 52]
    if len(paper_curves) != 23 or len(author_curves) != 26:
        raise ValueError("v3 portfolio main-path denominator changed")
    pairs = pair_curves(paper_curves, author_curves)
    stable = [pair for pair in pairs if pair[2] < 1.0]
    changed = [pair for pair in pairs if pair[2] >= 1.0]
    if len(stable) != 20 or len(changed) != 3:
        raise ValueError("v3 portfolio stable/changed path split changed")

    paper_y = np.array([point[1] for left, _right, _delta in stable for point in left["pts"]])
    author_y = np.array([point[1] for _left, right, _delta in stable for point in right["pts"]])
    design = np.column_stack([paper_y, np.ones_like(paper_y)])
    scale, offset = np.linalg.lstsq(design, author_y, rcond=None)[0]
    residual = np.abs(author_y - (scale * paper_y + offset))
    maximum_x = max(
        abs(point_left[0] - point_right[0])
        for left, right, _delta in stable
        for point_left, point_right in zip(left["pts"], right["pts"])
    )
    if maximum_x > 1e-9 or float(residual.max()) > 0.0000011:
        raise ValueError("v3 portfolio stable paths no longer share author geometry")
    return {
        "paper_main_52_week_paths": len(paper_curves),
        "author_main_52_week_paths": len(author_curves),
        "paired_paths": len(pairs),
        "shared_paths_after_single_affine_y_axis_transform": len(stable),
        "changed_deep_learning_baseline_paths": len(changed),
        "author_extra_ablation_paths": len(author_curves) - len(paper_curves),
        "shared_y_axis_affine_scale": float(scale),
        "shared_y_axis_affine_offset": float(offset),
        "maximum_shared_x_coordinate_difference": maximum_x,
        "maximum_shared_affine_y_residual": float(residual.max()),
    }


def figure_rows(paper_source: Path, author_repo: Path) -> list[dict[str, Any]]:
    rows = []
    units = {
        "flow.pdf": 0,
        "model_comparison_ann_vol.pdf": 48,
        "model_comparison_cum_ret.pdf": 48,
        "portfolio.pdf": 23,
        "risk_return.pdf": 23,
    }
    verified = {
        "flow.pdf": 0,
        "model_comparison_ann_vol.pdf": 48,
        "model_comparison_cum_ret.pdf": 48,
        "portfolio.pdf": 20,
        "risk_return.pdf": 20,
    }
    for name in units:
        paper_path = paper_source / "Figures" / name
        author_path = author_repo / "diagrams" / name if name == "flow.pdf" else author_repo / "figures" / name
        paper_hash = sha256_file(paper_path)
        author_hash = sha256_file(author_path)
        if (paper_hash, author_hash) != EXPECTED[name]:
            raise ValueError(f"v3 figure hash changed: {name}")
        if paper_hash == author_hash:
            relation = "byte_identical"
            evidence = "Exact paper/author-repository bytes."
        elif name == "portfolio.pdf":
            relation = "20_of_23_paper_paths_share_author_vector_geometry_three_final_baselines_changed"
            evidence = "Twenty 52-week paths pair after one shared affine y-axis transform; three deep-learning paths changed, and the repository adds three ablation paths."
        elif name == "risk_return.pdf":
            relation = "20_of_23_paper_points_have_matching_author_table_coordinates_three_final_baselines_changed"
            evidence = "Twenty strategy cumulative-return/volatility coordinate pairs match the pinned author table; LSTM, Informer, and Autoformer differ, and the repository adds three ablation points."
        else:
            raise ValueError(f"unexpected non-identical v3 figure: {name}")
        rows.append(
            {
                "asset": name,
                "role": "method_diagram" if name == "flow.pdf" else "quantitative_result_figure",
                "published_plotted_result_units": units[name],
                "author_output_verified_units": verified[name],
                "paper_sha256": paper_hash,
                "author_sha256": author_hash,
                "author_output_correspondence": relation,
                "evidence": evidence,
                "native_result_regenerated": False,
                "paper_result_credit": False,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-source", type=Path, required=True)
    parser.add_argument("--author-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = figure_rows(args.paper_source, args.author_repo)
    payload = {
        "paper": "MACI arXiv 2501.00826v3",
        "author_repository": "https://github.com/lyc0603/cryptoMAS",
        "author_head": "318e0fe905fed8b7f544322c3db1dfed6784d178",
        "figures": rows,
        "portfolio_vector_geometry": portfolio_geometry(
            args.paper_source / "Figures/portfolio.pdf",
            args.author_repo / "figures/portfolio.pdf",
        ),
        "published_plotted_result_units": sum(row["published_plotted_result_units"] for row in rows),
        "author_output_verified_units": sum(row["author_output_verified_units"] for row in rows),
        "native_result_regenerated_units": 0,
        "manual_visual_qa": {
            "date": "2026-08-14",
            "status": "passed_side_by_side_full_resolution_review",
            "checks": [
                "readable",
                "not_clipped",
                "paper/repository relationship consistent with vector and table audit",
            ],
        },
        "paper_result_credit": False,
    }
    encoded = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
