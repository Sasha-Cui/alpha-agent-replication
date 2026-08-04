from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "diagnose_international_failures.py"
SPEC = importlib.util.spec_from_file_location("diagnose_international_failures", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_clip_levels_are_monotone_and_include_unit_cap() -> None:
    assert MODULE.CLIP_LEVELS == sorted(MODULE.CLIP_LEVELS)
    assert MODULE.CLIP_LEVELS[0] == 1.0


def test_market_paths_point_to_jkp_characteristics() -> None:
    path = MODULE.market_path("FRA")
    assert path.name == "FRA.parquet"
    assert "characteristics" in path.parts
