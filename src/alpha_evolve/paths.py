"""Path policy for the alpha-agent replication package.

Repository-local paths are discovered relative to this file. External research
inputs keep Bouchet defaults for reproducibility, but every external input can be
overridden with an environment variable for public/portable use.
"""
from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str, default: Path | str) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else Path(default)


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
LITERATURE_DIR = REPO_ROOT / "literature_review"
PAPER_RUNS_DIR = REPO_ROOT / "paper_runs"
REPORT_PATH = REPO_ROOT / "report.md"

DEFAULT_JKP_ROOT = _env_path("ALPHA_EVOLVE_JKP_ROOT", "/home/zc362/project_pi_btk22/zc362/jkp-data")
DEFAULT_JKP_USA = _env_path(
    "ALPHA_EVOLVE_JKP_USA",
    DEFAULT_JKP_ROOT / "data/processed/characteristics/USA.parquet",
)
DEFAULT_FACTOR_DATA_ROOT = _env_path(
    "ALPHA_EVOLVE_FACTOR_DATA_ROOT",
    "/home/zc362/project_pi_btk22/zc362/factor-data",
)
DEFAULT_RETURN_DATA_ROOT = _env_path(
    "ALPHA_EVOLVE_RETURN_DATA_ROOT",
    DEFAULT_FACTOR_DATA_ROOT / "return_pipeline/return_data_assembly",
)
DEFAULT_FACTOR_PANEL = _env_path(
    "ALPHA_EVOLVE_FACTOR_PANEL",
    DEFAULT_FACTOR_DATA_ROOT
    / "performance_analysis/results/current/multifactor_value_add_20260624/benchmark_factor_panel.csv",
)


def require_existing_path(path: Path, *, label: str) -> Path:
    """Return ``path`` when it exists, otherwise raise a useful error."""
    if not path.exists():
        raise FileNotFoundError(
            f"{label} does not exist: {path}. Override the location with the documented ALPHA_EVOLVE_* environment variable."
        )
    return path
