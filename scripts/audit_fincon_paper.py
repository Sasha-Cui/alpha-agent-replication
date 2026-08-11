#!/usr/bin/env python3
"""Fail-closed paper-level audit of FinCon.

The NeurIPS 2024 proceedings paper is the result authority.  The audit also
pins all arXiv revisions and the complete history of the official repository.
The official repository contains only a README, so paper-source LaTeX
compilation is kept separate from native system execution and receives no
paper-result credit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


ARXIV_URL = "https://arxiv.org/abs/2407.06567"
PROCEEDINGS_URL = (
    "https://proceedings.neurips.cc/paper_files/paper/2024/hash/"
    "f7ae4fe91d96f50abc2211f09b6a7e49-Abstract-Conference.html"
)
PROCEEDINGS_PDF_URL = (
    "https://proceedings.neurips.cc/paper_files/paper/2024/file/"
    "f7ae4fe91d96f50abc2211f09b6a7e49-Paper-Conference.pdf"
)
DOI = "10.52202/079017-4354"
ARXIV_VERSIONS = {
    "v1": {
        "date": "2024-07-09T05:52:26Z",
        "pdf_sha256": "c8ea227452e855c7c9ec640b299cce2311364286f74d3cd4287892e8fc598c1f",
        "source_sha256": "e7d97c071f275267c04a89cc21bfa6b82c21540dee2b06a39247beb9b532bb50",
        "numeric_cells": 201,
    },
    "v2": {
        "date": "2024-07-10T06:59:18Z",
        "pdf_sha256": "a749d7334d5567650135ef37d280cdddaf391b2465b7979a3e9818d5e2247c18",
        "source_sha256": "167822f08299aa385a2d5453e868a3e48cbb21632f9cda1fcd079b5eba8b1476",
        "numeric_cells": 201,
    },
    "v3": {
        "date": "2024-11-07T00:54:30Z",
        "pdf_sha256": "3c09f3f3d9d2d2e50ef91e0ab6759dc2793755b94acd5a41e272dd63f9d54723",
        "source_sha256": "0042d91192940a04c51ec7de692f00bf32236fafb9d5c576235547c4cf692dbf",
        "numeric_cells": 306,
    },
}
ARXIV_API_SHA256 = "98b9800600dc95fb8ae2ba10e253fb45e56ae56d333b817bc5678734b44d0aa8"
PROCEEDINGS_PDF_SHA256 = "82af0bc37198f1110ca5c4c1d79a7fd22512fe879b5219746a9dec922a034a42"
SOURCE_URL = "https://github.com/The-FinAI/FinCon"
SOURCE_INITIAL_COMMIT = "831e3c2255f72304e104bdec64a62a1489109934"
SOURCE_INITIAL_DATE = "2024-10-28T20:04:28-04:00"
SOURCE_INITIAL_README_SHA256 = "d95577ba29c9d3e1cd9392c2a89ef5a1a83851d278a5b93e62fe25ac2c0d1f04"
SOURCE_CURRENT_COMMIT = "ca3256d037c497871c064bc2f5abab106993e189"
SOURCE_CURRENT_DATE = "2026-02-26T23:20:53-05:00"
SOURCE_CURRENT_README_SHA256 = "0aa1113065f1e71ee8688b89d87ac72751f2e1c1912a9d7ac739c865f50cccd7"
AUDIT_DATE = "2026-08-11"

METRICS = ("CR_pct", "SR", "MDD_pct")
METHODS = ("B&H", "FinCon", "GA", "FinGPT", "FinMem", "FinAgent", "A2C", "PPO", "DQN")

SINGLE_RESULTS: dict[str, dict[str, tuple[float, float, float]]] = {
    "TSLA": {
        "B&H": (6.425, 0.145, 58.150), "FinCon": (82.871, 1.972, 29.727),
        "GA": (16.535, 0.391, 54.131), "FinGPT": (1.549, 0.044, 42.400),
        "FinMem": (34.624, 1.552, 15.674), "FinAgent": (11.960, 0.271, 55.734),
        "A2C": (-35.644, -0.805, 61.502), "PPO": (1.409, 0.032, 49.740),
        "DQN": (-1.296, -0.029, 58.150),
    },
    "AMZN": {
        "B&H": (2.030, 0.072, 34.241), "FinCon": (24.848, 0.904, 25.889),
        "GA": (-5.631, -0.199, 37.213), "FinGPT": (-29.811, -1.810, 29.671),
        "FinMem": (-18.011, -0.773, 36.825), "FinAgent": (-24.588, -1.493, 33.074),
        "A2C": (-12.560, -0.444, 37.106), "PPO": (3.863, 0.138, 28.085),
        "DQN": (11.171, 0.398, 31.174),
    },
    "NIO": {
        "B&H": (-77.210, -1.449, 63.975), "FinCon": (17.461, 0.335, 40.647),
        "GA": (-3.176, -1.574, 3.155), "FinGPT": (-4.959, -0.121, 37.344),
        "FinMem": (-48.437, -1.180, 64.144), "FinAgent": (0.933, 0.051, 19.181),
        "A2C": (-91.910, -1.728, 68.911), "PPO": (-72.119, -1.352, 62.093),
        "DQN": (-35.419, -0.662, 56.905),
    },
    "MSFT": {
        "B&H": (27.856, 1.230, 15.010), "FinCon": (31.625, 1.538, 15.010),
        "GA": (-31.821, -1.414, 39.808), "FinGPT": (21.535, 1.315, 16.503),
        "FinMem": (-22.036, -1.247, 29.435), "FinAgent": (-27.534, -1.247, 39.544),
        "A2C": (21.397, 0.962, 21.458), "PPO": (-4.761, -0.214, 30.950),
        "DQN": (27.021, 1.216, 21.458),
    },
    "AAPL": {
        "B&H": (22.315, 1.107, 20.659), "FinCon": (27.352, 1.597, 15.266),
        "GA": (5.694, 0.372, 14.161), "FinGPT": (20.321, 1.161, 16.759),
        "FinMem": (12.397, 0.994, 11.268), "FinAgent": (20.757, 1.041, 19.896),
        "A2C": (13.781, 0.683, 14.226), "PPO": (14.041, 0.704, 22.785),
        "DQN": (21.125, 1.048, 16.131),
    },
    "GOOG": {
        "B&H": (22.420, 0.891, 21.191), "FinCon": (25.077, 1.052, 17.530),
        "GA": (-1.515, -0.192, 8.210), "FinGPT": (0.242, 0.011, 26.984),
        "FinMem": (0.311, 0.018, 21.503), "FinAgent": (-7.440, -1.024, 10.360),
        "A2C": (8.562, 0.340, 21.191), "PPO": (2.434, 0.097, 25.202),
        "DQN": (20.690, 0.822, 21.191),
    },
    "NFLX": {
        "B&H": (57.338, 1.794, 20.926), "FinCon": (69.239, 2.370, 20.792),
        "GA": (41.770, 1.485, 20.926), "FinGPT": (11.925, 0.472, 20.201),
        "FinMem": (-10.306, -0.478, 27.692), "FinAgent": (61.303, 1.960, 20.926),
        "A2C": (-8.176, -0.258, 49.579), "PPO": (-33.144, -1.049, 33.377),
        "DQN": (21.753, 0.687, 39.733),
    },
    "COIN": {
        "B&H": (-21.756, -0.311, 60.187), "FinCon": (57.045, 0.825, 42.679),
        "GA": (19.271, 0.277, 67.532), "FinGPT": (-99.553, -1.807, 74.967),
        "FinMem": (0.811, 0.017, 50.390), "FinAgent": (-5.971, -0.106, 56.882),
    },
}

PORTFOLIO_RESULTS = {
    "P1 (TSLA, MSFT, PFE)": {
        "FinCon": (113.836, 3.269, 16.163), "Markowitz MV": (12.636, 0.614, 17.842),
        "FinRL-A2C": (19.461, 0.831, 26.917), "Equal-Weighted ETF": (9.344, 0.492, 21.223),
    },
    "P2 (AMZN, GM, LLY)": {
        "FinCon": (32.922, 1.371, 21.502), "Markowitz MV": (10.289, 0.540, 25.099),
        "FinRL-A2C": (11.589, 0.649, 15.787), "Equal-Weighted ETF": (15.061, 0.867, 14.662),
    },
}

CVAR_RESULTS = {
    "GOOG": {"with": (25.077, 1.052, 17.530), "without": (-1.461, -0.006, 27.079)},
    "NIO": {"with": (17.461, 0.335, 40.647), "without": (-52.887, -1.002, 70.243)},
    "P1 (TSLA, MSFT, PFE)": {"with": (113.836, 3.269, 16.163), "without": (14.699, 1.142, 17.511)},
}

BELIEF_RESULTS = {
    "GOOG": {"with": (25.077, 1.052, 17.530), "without": (-11.944, -0.496, 29.309)},
    "NIO": {"with": (17.461, 0.335, 40.647), "without": (8.197, 0.156, 55.688)},
    "P1 (TSLA, MSFT, PFE)": {"with": (113.836, 3.269, 16.163), "without": (28.432, 1.181, 27.535)},
}

EXTREME_SINGLE = {
    "B&H": (-56.738, -1.625, 52.077), "FinCon": (22.460, 0.695, 45.215),
    "GA": (-51.251, -1.547, 48.763), "FinGPT": (-20.035, -0.805, 32.199),
    "FinMem": (-47.809, -1.549, 49.560), "FinAgent": (-31.119, -1.933, 33.224),
    "A2C": (-73.251, -2.142, 56.998), "PPO": (-78.007, -2.284, 59.003),
    "DQN": (-8.452, -1.328, 8.463),
}

EXTREME_PORTFOLIO = {
    "FinCon": (-8.429, -0.294, 26.176), "Markowitz MV": (-28.996, -1.805, 31.831),
    "FinRL-A2C": (-15.932, -1.195, 21.569), "Equal-Weighted ETF": (-28.008, -1.731, 30.070),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source_root), *args], check=True, capture_output=True, text=not binary
    )
    return proc.stdout


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError("refusing to write empty CSV: %s" % path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _table_row(
    table: str,
    experiment: str,
    item: str,
    metric: str,
    value: float,
    unique_id: str,
) -> dict[str, Any]:
    return {
        "paper_table": table,
        "experiment": experiment,
        "item": item,
        "metric": metric,
        "display_cell_id": f"{experiment}/{item}/{metric}",
        "unique_measurement_id": unique_id,
        "paper_value": f"{value:.3f}",
        "native_reproduced_value": "",
        "status": "not_reproduced_official_code_and_data_not_released",
        "paper_result_credit": False,
    }


def paper_table_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset, methods in SINGLE_RESULTS.items():
        table = "Table 2 single-asset comparison / part 1" if asset in ("TSLA", "AMZN", "NIO", "MSFT") else "Table 2 single-asset comparison / part 2"
        for method, values in methods.items():
            for metric, value in zip(METRICS, values):
                rows.append(_table_row(table, "regular_single", f"{asset}/{method}", metric, value, f"regular_single/{asset}/{method}/{metric}"))
    for portfolio, methods in PORTFOLIO_RESULTS.items():
        for method, values in methods.items():
            for metric, value in zip(METRICS, values):
                rows.append(_table_row("Table 3 portfolio comparison", "regular_portfolio", f"{portfolio}/{method}", metric, value, f"regular_portfolio/{portfolio}/{method}/{metric}"))
    for mechanism, values_by_target, table in (
        ("cvar", CVAR_RESULTS, "Table 4 CVaR ablation"),
        ("belief", BELIEF_RESULTS, "Table 5 belief-update ablation"),
    ):
        for target, variants in values_by_target.items():
            for variant, values in variants.items():
                for metric, value in zip(METRICS, values):
                    if variant == "with":
                        prefix = "regular_single" if target in SINGLE_RESULTS else "regular_portfolio"
                        unique_id = f"{prefix}/{target}/FinCon/{metric}"
                    else:
                        unique_id = f"ablation_{mechanism}/{target}/without/{metric}"
                    rows.append(_table_row(table, f"ablation_{mechanism}", f"{target}/{variant}", metric, value, unique_id))
    for method, values in EXTREME_SINGLE.items():
        for metric, value in zip(METRICS, values):
            rows.append(_table_row("Appendix extreme-market TSLA table", "extreme_single", f"TSLA/{method}", metric, value, f"extreme_single/TSLA/{method}/{metric}"))
    for method, values in EXTREME_PORTFOLIO.items():
        for metric, value in zip(METRICS, values):
            rows.append(_table_row("Appendix extreme-market P1 table", "extreme_portfolio", f"P1/{method}", metric, value, f"extreme_portfolio/P1/{method}/{metric}"))
    expected = {
        "Table 2 single-asset comparison / part 1": 108,
        "Table 2 single-asset comparison / part 2": 99,
        "Table 3 portfolio comparison": 24,
        "Table 4 CVaR ablation": 18,
        "Table 5 belief-update ablation": 18,
        "Appendix extreme-market TSLA table": 27,
        "Appendix extreme-market P1 table": 12,
    }
    if len(rows) != 306 or Counter(row["paper_table"] for row in rows) != expected:
        raise RuntimeError("FinCon paper numeric table census changed")
    return rows


def unique_measurement_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["unique_measurement_id"])
        if key not in unique:
            unique[key] = {
                "unique_measurement_id": key,
                "paper_value": row["paper_value"],
                "display_occurrences": 0,
                "native_reproduced_value": "",
                "status": row["status"],
                "paper_result_credit": False,
            }
        elif unique[key]["paper_value"] != row["paper_value"]:
            raise RuntimeError(f"Repeated FinCon measurement disagrees: {key}")
        unique[key]["display_occurrences"] += 1
    if len(unique) != 288 or Counter(row["display_occurrences"] for row in unique.values()) != {1: 279, 3: 9}:
        raise RuntimeError("FinCon unique-measurement census changed")
    return list(unique.values())


FIGURES: dict[str, tuple[str, ...]] = {
    **{f"Appendix regular single / {asset}.png": METHODS for asset in ("TSLA", "AMZN", "NIO", "MSFT", "AAPL", "GOOG_v2", "NFLX")},
    "Appendix regular single / COIN.png": METHODS[:6],
    "Figure 3 / portfolio_tsla_msft_pfe.png": ("FinCon-normal", "Markowitz", "Equal-Weighted ETF", "FinRL-A2C"),
    "Figure 3 / portfolio_amzn_gm_lly.png": ("FinCon-normal", "Markowitz", "Equal-Weighted ETF", "FinRL-A2C"),
    "Figure 4 CVaR / GOOG-nocvar.png": ("B&H", "FinCon w/ CVaR", "FinCon w/o CVaR"),
    "Figure 4 CVaR / NIO-abl_cvar.png": ("B&H", "FinCon w/ CVaR", "FinCon w/o CVaR"),
    "Figure 4 CVaR / regular_plot_withoutnocvar.png": ("FinCon w/ CVaR", "FinCon w/o CVaR"),
    "Figure 7 belief / GOOG-nobelief.png": ("B&H", "FinCon w/ Belief", "FinCon w/o Belief"),
    "Figure 7 belief / NIO-abl_belief.png": ("B&H", "FinCon w/ Belief", "FinCon w/o Belief"),
    "Figure 7 belief / regular_plot_withoutbelief.png": ("FinCon w/ Belief", "FinCon w/o Belief"),
    "Appendix extreme / TSLA_extreme_markets.png": METHODS,
    "Appendix extreme / portfolio_extreme_market_condition.png": ("FinCon-normal", "Markowitz", "Equal-Weighted ETF", "FinRL-A2C"),
}


def figure_rows() -> list[dict[str, Any]]:
    rows = []
    for figure, labels in FIGURES.items():
        for label in labels:
            rows.append({
                "figure": figure,
                "series": label,
                "underlying_numeric_series_released": False,
                "native_exact_series_reproduced": False,
                "status": "raster_only_no_underlying_series_or_generation_code",
                "paper_result_credit": False,
            })
    if len(rows) != 106 or len(FIGURES) != 18:
        raise RuntimeError("FinCon figure-series census changed")
    return rows


# The v1 and v2 result cells are identical.  These are the 64 shared cells
# whose values changed in v3/final.  The other 137 shared cells were unchanged.
V2_OVERRIDES: dict[str, float] = {}


def _old(experiment: str, item: str, values: Mapping[str, float]) -> None:
    for metric, value in values.items():
        V2_OVERRIDES[f"{experiment}/{item}/{metric}"] = value


_old("regular_single", "AMZN/B&H", {"CR_pct": 1.914, "SR": 0.067, "MDD_pct": 34.317})
_old("regular_single", "AMZN/FinCon", {"CR_pct": 24.964, "SR": 0.906})
_old("regular_single", "AMZN/GA", {"CR_pct": -5.515, "SR": -0.195})
_old("regular_single", "AMZN/FinGPT", {"SR": -1.805, "MDD_pct": -29.671})
_old("regular_single", "AMZN/FinMem", {"CR_pct": -18.126, "SR": -0.776})
_old("regular_single", "AMZN/FinAgent", {"CR_pct": -24.704, "SR": -1.496, "MDD_pct": 33.151})
_old("regular_single", "AMZN/A2C", {"CR_pct": -12.676, "SR": -0.447, "MDD_pct": 37.179})
_old("regular_single", "AMZN/PPO", {"SR": 0.137})
_old("regular_single", "AAPL/FinMem", {"CR_pct": 12.396})
_old("regular_single", "GOOG/FinCon", {"SR": 1.0521, "MDD_pct": 17.5299})
_old("regular_single", "GOOG/GA", {"CR_pct": -0.0151})
_old("regular_single", "GOOG/FinGPT", {"CR_pct": 0.207, "SR": 0.822, "MDD_pct": 21.191})
_old("regular_single", "GOOG/PPO", {"SR": -0.097})
_old("regular_portfolio", "P1 (TSLA, MSFT, PFE)/FinCon", {"CR_pct": 121.018, "SR": 3.435, "MDD_pct": 16.288})
_old("regular_portfolio", "P1 (TSLA, MSFT, PFE)/Markowitz MV", {"CR_pct": 32.521, "SR": 1.423, "MDD_pct": 20.658})
_old("regular_portfolio", "P1 (TSLA, MSFT, PFE)/FinRL-A2C", {"CR_pct": 33.479, "SR": 1.352, "MDD_pct": 27.124})
_old("regular_portfolio", "P1 (TSLA, MSFT, PFE)/Equal-Weighted ETF", {"CR_pct": 19.983, "SR": 1.003, "MDD_pct": 22.807})
_old("ablation_cvar", "GOOG/with", {"CR_pct": 28.972, "SR": 1.233, "MDD_pct": 16.990})
_old("ablation_cvar", "NIO/with", {"CR_pct": 7.981, "SR": 0.157})
_old("ablation_cvar", "NIO/without", {"CR_pct": -70.791, "SR": -1.383})
_old("ablation_cvar", "P1 (TSLA, MSFT, PFE)/with", {"CR_pct": 121.018, "SR": 3.435, "MDD_pct": 16.288})
_old("ablation_cvar", "P1 (TSLA, MSFT, PFE)/without", {"CR_pct": 16.994, "SR": 1.303, "MDD_pct": 17.646})
_old("ablation_belief", "GOOG/with", {"CR_pct": 28.972, "SR": 1.233, "MDD_pct": 16.990})
_old("ablation_belief", "NIO/with", {"CR_pct": 7.981, "SR": 0.157})
_old("ablation_belief", "NIO/without", {"CR_pct": -17.956, "SR": -0.356})
_old("ablation_belief", "P1 (TSLA, MSFT, PFE)/with", {"CR_pct": 121.018, "SR": 3.435, "MDD_pct": 16.288})
_old("ablation_belief", "P1 (TSLA, MSFT, PFE)/without", {"CR_pct": 20.677, "SR": 0.987, "MDD_pct": 23.975})


def version_drift_rows(table_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    final = {str(row["display_cell_id"]): row for row in table_rows}
    if len(V2_OVERRIDES) != 64:
        raise RuntimeError(f"FinCon v2 override census changed: {len(V2_OVERRIDES)}")
    rows = []
    for cell_id, old_value in V2_OVERRIDES.items():
        row = final[cell_id]
        rows.append({
            "display_cell_id": cell_id,
            "v1_value": f"{old_value:.4f}".rstrip("0").rstrip("."),
            "v2_value": f"{old_value:.4f}".rstrip("0").rstrip("."),
            "v3_and_proceedings_value": row["paper_value"],
            "status": "changed_in_v3",
        })
    return rows


def version_summary_rows() -> list[dict[str, Any]]:
    return [
        {"release": "arXiv v1", "date": ARXIV_VERSIONS["v1"]["date"], "numeric_cells": 201, "shared_cells_changed_from_prior": 0, "cells_added_from_prior": 0, "authority": False, "notes": "original six-stock, one-portfolio release"},
        {"release": "arXiv v2", "date": ARXIV_VERSIONS["v2"]["date"], "numeric_cells": 201, "shared_cells_changed_from_prior": 0, "cells_added_from_prior": 0, "authority": False, "notes": "result tables identical to v1; formatting and author metadata changed"},
        {"release": "arXiv v3", "date": ARXIV_VERSIONS["v3"]["date"], "numeric_cells": 306, "shared_cells_changed_from_prior": 64, "cells_added_from_prior": 105, "authority": False, "notes": "same displayed numeric result content as proceedings"},
        {"release": "NeurIPS 2024 proceedings", "date": "2025-01-17 PDF creation metadata", "numeric_cells": 306, "shared_cells_changed_from_prior": 0, "cells_added_from_prior": 0, "authority": True, "notes": "36-page final paper and audit result authority"},
    ]


ACTIVE_RESULT_ASSETS = {name.split(" / ", 1)[1] for name in FIGURES}


def source_asset_rows(paper_root: Path) -> list[dict[str, Any]]:
    archive = paper_root / "source.tar"
    with tarfile.open(archive, "r:*") as tar:
        names = sorted(member.name for member in tar.getmembers() if member.isfile() and re.search(r"\.(png|jpg|pdf)$", member.name, re.I))
    rows = []
    for name in names:
        path = paper_root / "source_v3" / name
        basename = Path(name).name
        rows.append({
            "path": name,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "active_result_figure": basename in ACTIVE_RESULT_ASSETS,
            "status": "raster_result_only_no_underlying_numeric_series" if basename in ACTIVE_RESULT_ASSETS else "informational_or_unused_paper_asset",
            "paper_result_credit": False,
        })
    if len(rows) != 37 or sum(bool(row["active_result_figure"]) for row in rows) != 18:
        raise RuntimeError("FinCon v3 source-asset census changed")
    return rows


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    names = str(run_git(source_root, "ls-tree", "-r", "--name-only", SOURCE_CURRENT_COMMIT)).splitlines()
    rows = []
    for name in names:
        path = source_root / name
        rows.append({
            "path": name,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "source_code": path.suffix in {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"},
            "data_or_model_artifact": path.suffix.lower() in {".csv", ".json", ".parquet", ".pkl", ".pt", ".pth", ".bin"},
            "status": "readme_only_no_fincon_implementation",
            "paper_result_credit": False,
        })
    if names != ["README.md"]:
        raise RuntimeError(f"Official FinCon source tree changed: {names}")
    return rows


def source_history_rows(source_root: Path) -> list[dict[str, Any]]:
    raw = str(run_git(source_root, "log", "--reverse", "--format=%H%x09%cI%x09%s"))
    rows = []
    for line in raw.splitlines():
        commit, date, subject = line.split("\t", 2)
        names = str(run_git(source_root, "ls-tree", "-r", "--name-only", commit)).splitlines()
        rows.append({
            "commit": commit,
            "date": date,
            "subject": subject,
            "tracked_files": len(names),
            "only_readme": names == ["README.md"],
            "implementation_released": False,
        })
    if len(rows) != 11 or any(not row["only_readme"] for row in rows):
        raise RuntimeError("Official FinCon repository history changed")
    return rows


def mechanism_conformance() -> list[dict[str, Any]]:
    mechanisms = [
        ("manager_analyst_hierarchy", "synchronous manager plus seven specialized analyst types"),
        ("news_analyst", "daily textual news distillation"),
        ("filing_analysts", "10-K and 10-Q textual report distillation"),
        ("ecc_audio_analyst", "earnings-call audio interpreted with Whisper API"),
        ("data_analysis_agent", "tabular indicators including momentum and CVaR"),
        ("stock_selection_agent", "portfolio selection from 42-stock pool"),
        ("manager_action_generation", "sole long/short/neutral decision maker"),
        ("portfolio_weight_optimizer", "direction-constrained convex mean-variance optimization"),
        ("working_memory", "role-specific observation, retrieval, distillation, consolidation"),
        ("procedural_memory", "per-step actions, reflections, and analyst insights"),
        ("episodic_memory", "manager-only trajectories, PnL and beliefs"),
        ("memory_relevance", "embedding cosine-similarity retrieval"),
        ("memory_importance_decay", "agent-specific exponential decay"),
        ("memory_access_counter", "Guardrails AI validation and +5 importance updates"),
        ("top_k_retrieval", "top five memory events"),
        ("within_episode_cvar", "bottom-one-percent PnL CVaR monitoring"),
        ("within_episode_alert", "risk alert on CVaR drop or negative PnL"),
        ("manager_self_reflection", "reflection on risk trigger"),
        ("cvrf_episode_comparison", "compare consecutive training trajectories"),
        ("cvrf_concept_attribution", "attribute wins and losses to analyst perspectives"),
        ("cvrf_overlap_learning_rate", "action overlap supplies textual learning rate"),
        ("cvrf_prompt_update", "textual gradient-descent belief update"),
        ("selective_belief_propagation", "manager sends updates to relevant analysts"),
        ("single_asset_environment", "daily sequential single-stock trading"),
        ("portfolio_environment", "daily multi-asset weights and one-million-dollar value"),
        ("five_epoch_selection", "median CR/SR test trajectory across five repetitions"),
        ("extreme_market_protocol", "separate high-volatility train/test split"),
        ("baseline_ga_adaptation", "finance-adapted Generative Agent prompts"),
        ("baseline_fingpt", "FinGPT execution"),
        ("baseline_finmem", "FinMem execution"),
        ("baseline_finagent", "FinAgent execution with multimodal inputs"),
        ("baseline_finrl", "A2C/PPO/DQN and portfolio A2C"),
        ("wilcoxon_significance", "paired non-parametric significance testing"),
    ]
    return [{
        "mechanism": name,
        "paper_specification": spec,
        "released_source_evidence": "none; official repository contains only README.md",
        "status": "missing_no_implementation_released",
        "paper_mechanism_credit": False,
    } for name, spec in mechanisms]


def config_conformance() -> list[dict[str, Any]]:
    configs = [
        ("LLM backbone", "GPT-4-Turbo"), ("LLM temperature", "0.3"),
        ("belief generation temperature", "0 in v1/v2 prose; omitted from active final text"),
        ("FinCon train interval", "2022-01-03 through 2022-10-04"),
        ("regular test interval", "2022-10-05 through 2023-06-10"),
        ("DRL train interval", "2018-01-01 through 2022-10-04"),
        ("extreme train interval", "2022-01-17 through 2022-03-31"),
        ("extreme test interval", "2022-04-01 through 2022-10-15"),
        ("repetitions", "five epochs"), ("reported trajectory", "median CR; appendix resolves different CR/SR medians to median-CR trajectory"),
        ("memory retrieval K", "5"), ("CVaR tail", "worst 1% daily PnL"),
        ("regular single assets", "TSLA, AMZN, NIO, MSFT, AAPL, GOOG, NFLX, COIN"),
        ("portfolio 1", "TSLA, MSFT, PFE"), ("portfolio 2", "AMZN, GM, LLY"),
        ("candidate pool", "42 stocks with more than 800 news articles"),
        ("initial portfolio value", "$1,000,000"),
        ("market prices", "Yahoo Finance daily OHLC adjusted close and volume"),
        ("news", "Refinitiv Real-Time News / Reuters; contradictory prose also names Alpaca"),
        ("filings", "SEC EDGAR 10-K section 7 and 10-Q part 1 item 2"),
        ("analyst research", "Zacks Equity Research; contradictory prose also names Capital IQ"),
        ("audio", "earnings conference calls and Whisper API"),
        ("single baselines", "B&H, GA, FinGPT, FinMem, FinAgent, A2C, PPO, DQN"),
        ("portfolio baselines", "Markowitz MV, FinRL-A2C, Equal-Weighted ETF"),
        ("metrics", "CR, Sharpe ratio, maximum drawdown"),
        ("training episodes", "four claimed in results; algorithm Max unspecified"),
    ]
    return [{
        "configuration": key,
        "paper_value": value,
        "released_source_value": "",
        "status": "paper_only_unverifiable_no_code_config_or_data",
        "paper_configuration_credit": False,
    } for key, value in configs]


def specification_gaps() -> list[dict[str, str]]:
    gaps = [
        ("source implementation", "No FinCon code, prompts, environment, configs, or tests are released."),
        ("dataset snapshot", "No exact multimodal dataset, file manifest, hashes, schemas, or timestamps are released."),
        ("commercial inputs", "Refinitiv, Zacks, Capital IQ, Alpaca, and ECC inputs are not archived with the paper."),
        ("data-source contradiction", "Raw-data prose names Yahoo/Alpaca/Capital IQ while the adjacent table names Refinitiv/Zacks/SEC/Yahoo/ECC."),
        ("data-end contradiction", "Experimental setup ends 2023-06-10; raw-data section says 2022-06-10."),
        ("LLM snapshot", "GPT-4-Turbo API model/version/date is not pinned."),
        ("Whisper snapshot", "Whisper API model/version and transcription settings are not pinned."),
        ("prompts", "System, role, analysis, action, reflection, CVRF, and baseline-adaptation prompts are absent."),
        ("LLM sampling", "Seed, top-p, max tokens, retries, timeout, and response parsing are absent."),
        ("agent roster", "Seven analyst types are claimed but their exact instantiated roster and per-task activation are not fully enumerated."),
        ("memory decay", "Agent-specific initial importance and decay ratios are omitted."),
        ("embedding model", "Embedding model, normalization, and retrieval tie handling are omitted."),
        ("memory persistence", "Database schema, event construction, pruning, and episode reset semantics are omitted."),
        ("CVaR estimator", "Window, minimum observations, quantile interpolation, and exact trigger comparison are omitted."),
        ("CVRF meta-prompt", "Concept extraction, comparison, update prompt, and update parsing are omitted."),
        ("textual learning rate", "Mapping from action overlap to prompt edits is not operationally specified."),
        ("action semantics", "Decision time, execution price, next-day mapping, position persistence, cash, leverage, and short constraints are omitted."),
        ("portfolio optimizer", "Solver, objective coefficients, constraints, covariance estimator, and direction-to-bound mapping are not fully specified."),
        ("trading frictions", "Transaction costs, slippage, borrowing costs, and liquidity constraints are omitted."),
        ("risk-free rate", "Sharpe risk-free rate, periodicity, and annualization are omitted."),
        ("metric implementation", "Exact CR, SR, and MDD code and aggregation conventions are absent."),
        ("five repetitions", "Seeds and whether baseline repetitions share data/model randomness are omitted."),
        ("test selection", "Appendix says the reported setting maximizes test cumulative return; the candidate settings and selection procedure are absent."),
        ("statistical test", "Wilcoxon pairing samples, comparator, statistic, p-values, corrections, and effect sizes are absent."),
        ("DRL features", "Observation features, preprocessing, action space, reward, hyperparameters, seeds, and checkpoints are absent."),
        ("baseline revisions", "Exact commits and dependencies for GA, FinGPT, FinMem, FinAgent, FinRL, and FinRL-Meta are not pinned."),
        ("baseline adaptations", "Finance prompt modifications and multimodal alignment are not released."),
        ("stock pool", "The exact 42-symbol eligible universe and point-in-time filtering record are not released as data."),
        ("stock selection", "Deterministic selection inputs and outputs for P1/P2 are not released."),
        ("raw trajectories", "Actions, prompts, responses, memory states, prices, PnL, and per-run metrics are absent."),
        ("figure data", "All 106 published result series are raster-only; no plotting inputs or scripts are released."),
        ("revision provenance", "The paper does not explain why 64 shared numeric cells changed between v2 and v3."),
        ("extreme protocol", "VIX computation/source, threshold selection procedure, and separate model/config details are not pinned."),
    ]
    return [{"gap": key, "detail": detail, "impact": "prevents exact paper-level replication"} for key, detail in gaps]


def internal_checks() -> list[dict[str, Any]]:
    checks = [
        ("result authority", "NeurIPS proceedings is final authority; arXiv v3 has same displayed numeric results", "pass", True),
        ("single-stock table reference", "narrative calls results Table 1, proceedings caption numbers it Table 2", "contradiction", False),
        ("single-stock figure asset count", "caption says six stocks but eight panels/assets are displayed", "contradiction", False),
        ("regular single MDD claim", "FinCon is best or tied-best MDD on only 3 of 8 assets, not most", "claim_not_supported_by_table", False),
        ("portfolio all-metrics claim", "P2 FinCon MDD 21.502 is worse than FinRL-A2C 15.787 and ETF 14.662", "claim_not_supported_by_table", False),
        ("extreme single all-metrics claim", "FinCon MDD 45.215 is worse than FinGPT 32.199, FinAgent 33.224, and DQN 8.463", "claim_not_supported_by_table", False),
        ("extreme portfolio all-metrics claim", "FinCon MDD 26.176 is worse than FinRL-A2C 21.569", "claim_not_supported_by_table", False),
        ("raw-data date", "raw-data section ends 2022-06-10 while setup/tests end 2023-06-10", "contradiction", False),
        ("raw-data vendors", "raw-data prose and table name different commercial sources", "contradiction", False),
        ("v1-v2 result stability", "all 201 displayed result cells are identical", "pass", True),
        ("v2-v3 result drift", "64 of 201 shared cells changed and 105 cells were added without released derivation", "unexplained_material_revision", False),
        ("Wilcoxon substantiation", "no paired observations, statistic, p-values, correction, or effect size", "insufficient_evidence", False),
        ("test-set model selection", "appendix reports the setting with highest test cumulative return", "methodological_leakage_risk", False),
        ("CR formula index", "cumulative simple-return product uses Daily Simple Return_t rather than index k", "formula_typo", False),
        ("official repository at paper time", "initial commit after submission contains only '# FinCon'", "implementation_absent", False),
        ("official repository current", "all 11 commits contain only README.md; current README says code/data are not released", "implementation_absent", False),
        ("announced release window", "February 2026 README promised 3-4 months; no implementation exists at 2026-08-11 audit", "missed_release_window", False),
        ("adjacent projects", "InvestorBench and Agent Market Arena are different systems and receive no FinCon credit", "correct_scope_boundary", True),
    ]
    return [{"check": name, "evidence": evidence, "status": status, "supports_replication": supports} for name, evidence, status, supports in checks]


def validate_primary_inputs(source_root: Path, paper_root: Path) -> None:
    if str(run_git(source_root, "rev-parse", "HEAD")).strip() != SOURCE_CURRENT_COMMIT:
        raise RuntimeError("FinCon source checkout is not at the pinned revision")
    if sha256(source_root / "README.md") != SOURCE_CURRENT_README_SHA256:
        raise RuntimeError("FinCon README hash mismatch")
    expected_files = {
        "paper_v1.pdf": ARXIV_VERSIONS["v1"]["pdf_sha256"],
        "source_v1.tar": ARXIV_VERSIONS["v1"]["source_sha256"],
        "paper_v2.pdf": ARXIV_VERSIONS["v2"]["pdf_sha256"],
        "source_v2.tar": ARXIV_VERSIONS["v2"]["source_sha256"],
        "paper.pdf": ARXIV_VERSIONS["v3"]["pdf_sha256"],
        "source.tar": ARXIV_VERSIONS["v3"]["source_sha256"],
        "arxiv_api.xml": ARXIV_API_SHA256,
        "neurips2024.pdf": PROCEEDINGS_PDF_SHA256,
    }
    for name, expected in expected_files.items():
        if sha256(paper_root / name) != expected:
            raise RuntimeError(f"FinCon primary artifact hash mismatch: {name}")
    if len(str(run_git(source_root, "log", "--format=%H")).splitlines()) != 11:
        raise RuntimeError("FinCon source history changed")


def compile_paper_source(paper_root: Path, latex_command: str) -> dict[str, Any]:
    executable = shutil.which(latex_command)
    if not executable:
        return {
            "attempted": False, "status": "latex_command_unavailable", "command": latex_command,
            "exit_code": None, "produced_pdf": False, "paper_result_credit": False,
        }
    with tempfile.TemporaryDirectory(prefix="fincon-paper-") as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(paper_root / "source.tar", "r:*") as tar:
            tar.extractall(tmp_path, filter="data")
        proc = subprocess.run(
            [executable, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            cwd=tmp_path, capture_output=True, text=True, timeout=180,
        )
        combined = proc.stdout + "\n" + proc.stderr
        produced = (tmp_path / "main.pdf").exists()
        pages = None
        match = re.search(r"Output written on main\.pdf \((\d+) pages", combined)
        if match:
            pages = int(match.group(1))
        return {
            "attempted": True,
            "status": "paper_latex_compiled_with_warnings_no_system_code" if proc.returncode == 0 and produced else "paper_latex_compile_failed",
            "command": executable,
            "exit_code": proc.returncode,
            "produced_pdf": produced,
            "produced_pdf_pages": pages,
            "undefined_reference_warnings": combined.count("undefined"),
            "paper_source_files": 48,
            "fincon_implementation_files": 0,
            "paper_result_credit": False,
        }


def render_readme(manifest: Mapping[str, Any]) -> str:
    return f"""# FinCon paper-replication audit

This audit uses the 36-page NeurIPS 2024 proceedings paper as the result authority and pins all three arXiv revisions, the official paper source, and the complete official Git history. It is deliberately fail-closed: paper LaTeX compilation, raster plot availability, a README, or a related project cannot substitute for executing FinCon and matching its published results.

## Honest result

- **Full paper reproduced:** no.
- **Displayed numeric table cells reproduced:** 0 / {manifest['paper_numeric_table_cells_total']}.
- **Unique numeric measurements reproduced:** 0 / {manifest['paper_unique_numeric_measurements_total']}.
- **Raster result series reproduced from native numeric data:** 0 / {manifest['paper_figure_series_total']}.
- **Paper mechanisms verified in released implementation:** 0 / {manifest['paper_mechanisms_total']}.
- **Official FinCon implementation/data/model artifacts released:** none. Every one of the repository's 11 commits contains only `README.md`.

The current README explicitly says commercial APIs prevent release of the full system and associated data and promises a future code release. InvestorBench and Agent Market Arena are separate systems and receive no FinCon credit.

## Result census and revision drift

The final paper displays 306 numeric cells. Nine FinCon metric triplets are repeated in the main table and both ablation tables, leaving 288 unique measurements. It also contains 106 result series across 18 raster assets; no underlying series or plot-generation code is released.

The v1 and v2 arXiv releases have the same 201 result cells. In v3/final, 105 cells were added and 64 of the 201 shared cells changed. The release provides no raw trajectories or derivation explaining those changes. `paper_version_numeric_drift.csv` records every changed shared cell.

## What did run

The released arXiv v3 LaTeX source compiles to a 30-page paper. That validates paper packaging only. There is no FinCon source entrypoint, import, environment, model, prompt set, dataset, or checkpoint to execute. Accordingly, the compilation earns zero system or result credit.

## Principal blockers

Exact replication requires the FinCon implementation; complete prompts and parsing; frozen multimodal commercial/public data; model/API snapshots; memory and CVRF parameters; action/execution semantics; trading frictions; all seeds and raw trajectories; baseline revisions/adaptations; statistical-test samples; and underlying plot data. See `paper_specification_gaps.csv` for the full fail-closed list.

## Important paper-internal findings

The final paper contains material inconsistencies: Table numbering does not match the narrative; a figure caption says six stocks while showing eight; several captions claiming FinCon leads *all* metrics are contradicted by their own MDD cells; data dates and vendors disagree between adjacent sections; Wilcoxon claims omit test outputs; and the appendix says the reported setting was chosen for the highest test cumulative return. These do not prove the results wrong, but they materially increase the evidence needed for a faithful replication.
"""


def audit(source_root: Path, paper_root: Path, output: Path, latex_command: str) -> dict[str, Any]:
    validate_primary_inputs(source_root, paper_root)
    table = paper_table_rows()
    unique = unique_measurement_rows(table)
    figures = figure_rows()
    drift = version_drift_rows(table)
    source_files = source_inventory(source_root)
    history = source_history_rows(source_root)
    assets = source_asset_rows(paper_root)
    mechanisms = mechanism_conformance()
    configs = config_conformance()
    gaps = specification_gaps()
    checks = internal_checks()
    native = {
        "official_source_revision": SOURCE_CURRENT_COMMIT,
        "tracked_files": 1,
        "source_code_files": 0,
        "data_model_or_checkpoint_files": 0,
        "native_system_execution_attempted": False,
        "native_system_execution_status": "impossible_no_fincon_implementation_released",
        "paper_latex_compilation": compile_paper_source(paper_root, latex_command),
        "paper_result_credit": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    csv_outputs = {
        "paper_numeric_table_conformance.csv": table,
        "paper_unique_measurement_conformance.csv": unique,
        "paper_figure_series_inventory.csv": figures,
        "paper_version_numeric_drift.csv": drift,
        "paper_version_summary.csv": version_summary_rows(),
        "paper_source_asset_inventory.csv": assets,
        "released_source_inventory.csv": source_files,
        "released_source_history.csv": history,
        "source_mechanism_conformance.csv": mechanisms,
        "source_config_conformance.csv": configs,
        "paper_specification_gaps.csv": gaps,
        "paper_internal_and_source_checks.csv": checks,
    }
    for name, rows in csv_outputs.items():
        write_csv(output / name, rows)
    (output / "native_execution.json").write_text(json.dumps(native, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest: dict[str, Any] = {
        "audit_date": AUDIT_DATE,
        "paper": "FinCon",
        "paper_result_authority": "NeurIPS 2024 proceedings PDF",
        "paper_urls": {"proceedings": PROCEEDINGS_URL, "proceedings_pdf": PROCEEDINGS_PDF_URL, "arxiv": ARXIV_URL, "doi": DOI},
        "paper_hashes": {"proceedings_pdf": PROCEEDINGS_PDF_SHA256, **{f"arxiv_{v}_pdf": data["pdf_sha256"] for v, data in ARXIV_VERSIONS.items()}, **{f"arxiv_{v}_source": data["source_sha256"] for v, data in ARXIV_VERSIONS.items()}},
        "official_source_url": SOURCE_URL,
        "official_source_revision": SOURCE_CURRENT_COMMIT,
        "overall_status": "paper_specification_audited_but_official_code_and_data_not_released",
        "full_paper_reproduced": False,
        "paper_numeric_table_cells_total": len(table),
        "paper_numeric_table_cells_with_paper_result_credit": 0,
        "paper_unique_numeric_measurements_total": len(unique),
        "paper_unique_numeric_measurements_with_paper_result_credit": 0,
        "paper_figure_assets_total": len(FIGURES),
        "paper_figure_series_total": len(figures),
        "native_exact_figure_series_reproduced": 0,
        "paper_mechanisms_total": len(mechanisms),
        "paper_mechanisms_verified_in_released_source": 0,
        "paper_configurations_total": len(configs),
        "paper_configurations_verified_in_released_source": 0,
        "paper_specification_gaps_total": len(gaps),
        "paper_source_assets_total": len(assets),
        "official_repository_commits_total": len(history),
        "official_repository_tracked_files_current": len(source_files),
        "official_repository_source_code_files_current": 0,
        "v1_v2_numeric_cells_changed": 0,
        "v2_v3_shared_numeric_cells_changed": len(drift),
        "v3_numeric_cells_added": 105,
        "v3_arxiv_source_latex_compiled": native["paper_latex_compilation"]["exit_code"] == 0,
    }
    (output / "README.md").write_text(render_readme(manifest), encoding="utf-8")
    output_names = [*csv_outputs, "native_execution.json", "README.md"]
    manifest["output_sha256"] = {name: sha256(output / name) for name in sorted(output_names)}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--latex-command", default="pdflatex")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = audit(args.source_root, args.paper_root, args.output, args.latex_command)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
