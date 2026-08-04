from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_replication_scope_assets.py"
SPEC = importlib.util.spec_from_file_location("build_replication_scope_assets", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_reference_number_parser_handles_multi_record_lineages() -> None:
    assert MODULE.ref_numbers("11;12") == {11, 12}
    assert MODULE.ref_numbers("—") == set()
