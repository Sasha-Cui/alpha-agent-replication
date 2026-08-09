from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_collaborator_handoff.py"
SPEC = importlib.util.spec_from_file_location("build_collaborator_handoff", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
OUTPUT = ROOT / "paper_runs/handoff"


def test_tracked_handoff_index_has_expected_scope_and_provenance() -> None:
    frame = pd.read_csv(OUTPUT / "strategy_result_index.csv")
    manifest = json.loads((OUTPUT / "manifest.json").read_text())
    assert len(frame) == frame["candidate_id"].nunique() == 50
    assert frame["canonical_work_id"].nunique() == 40
    assert frame["implementation_basis"].value_counts().to_dict() == {
        "in_spirit_reconstruction": 37,
        "released_code_component_adaptation": 1,
        "source_grounded_paper_component": 12,
    }
    assert set(frame["mapping_frozen_before_us_returns_inspected"]) == {"no"}
    assert set(frame["independent_second_coder"]) == {"no"}
    assert manifest["claim_boundary"]["native_agent_replications"] == 0
    assert manifest["coverage"]["strategies"] == 50
    assert manifest["coverage"]["papers"] == 40


def test_handoff_excludes_restricted_and_high_volume_data() -> None:
    frame = pd.read_csv(OUTPUT / "strategy_result_index.csv")
    manifest = json.loads((OUTPUT / "manifest.json").read_text())
    assert manifest["excluded_data"] == {
        "external_repository_contents_included": False,
        "jkp_factor_panel_included": False,
        "monthly_strategy_returns_included": False,
        "security_level_data_included": False,
    }
    assert "month" not in frame.columns
    assert not any(column.endswith("_return") for column in frame.columns)
    assert not any("security" in column for column in frame.columns)


def test_handoff_builder_is_deterministic(tmp_path: Path) -> None:
    index_path, manifest_path = MODULE.build_handoff(ROOT, tmp_path)
    assert index_path.read_bytes() == (OUTPUT / "strategy_result_index.csv").read_bytes()
    generated = json.loads(manifest_path.read_text())
    tracked = json.loads((OUTPUT / "manifest.json").read_text())
    generated["outputs"]["strategy_result_index"]["path"] = tracked["outputs"][
        "strategy_result_index"
    ]["path"]
    assert generated == tracked


def test_all_benchmark_rungs_and_closest_factor_are_present() -> None:
    frame = pd.read_csv(OUTPUT / "strategy_result_index.csv")
    for prefix in ("capm", "ff3", "ff5_mom", "ff5_mom_jkp132"):
        assert frame[f"{prefix}_alpha_annualized"].notna().all()
        assert frame[f"{prefix}_holm_p_value"].notna().all()
    assert frame["closest_factor_id"].notna().all()
    assert frame["closest_factor_absolute_correlation"].between(0, 1).all()
