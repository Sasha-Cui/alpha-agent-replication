from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/finrs"
SPEC = importlib.util.spec_from_file_location("audit_finrs_paper", ROOT / "scripts/audit_finrs_paper.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(name: str) -> dict:
    return json.loads((AUDIT_DIR / name).read_text())


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_original_source_rebuild_and_visual_audit_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["arxiv_id"] == "2511.12599"
    assert provenance["arxiv_version"] == "v1"
    assert provenance["source_files"] == 13
    assert provenance["official_pages"] == provenance["rebuilt_pages"] == 6
    assert provenance["official_pages_visually_checked"] == 6
    assert provenance["rebuilt_pages_visually_checked"] == 6
    assert provenance["visual_defects_observed"] == 0
    assert provenance["official_rebuilt_token_jaccard"] > 0.997
    assert provenance["paper_contains_native_implementation_url"] is False
    assert provenance["attributable_finrs_implementation_found"] is False


def test_all_225_empirical_cells_fail_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 225
    assert Counter(row["table_label"] for row in results) == {
        "tab:model_comparison": 180,
        "tab:ablation_single": 45,
    }
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["raw_result_record_recovered"] == "False" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)


def test_cross_paper_lineage_records_216_exact_finpos_v1_cells() -> None:
    lineage = rows("cross_paper_result_lineage.csv")
    assert len(lineage) == 225
    assert sum(row["exact_display_match"] == "True" for row in lineage) == 216
    assert sum(
        row["exact_display_match"] == "True" and row["table_label"] == "tab:model_comparison"
        for row in lineage
    ) == 180
    assert sum(
        row["exact_display_match"] == "True" and row["table_label"] == "tab:ablation_single"
        for row in lineage
    ) == 36
    assert all("not an independently regenerated result" in row["lineage_interpretation"] for row in lineage)


def test_only_conceptual_figure_and_three_shared_equation_checks() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 1
    assert figures[0]["empirical_panels"] == "0"
    assert figures[0]["underlying_numeric_array_or_run_log_recovered"] == "False"
    components = {row["component"]: row for row in rows("component_execution_audit.csv")}
    assert set(components) == {"multi_timescale_score", "position_update", "literal_reward"}
    assert all(row["deterministic_control_passed"] == "True" for row in components.values())
    assert all(row["equation_identical_to_finpos_v1"] == "True" for row in components.values())
    assert all(row["author_native_pipeline_executed"] == "False" for row in components.values())


def test_missing_core_risk_mechanics_and_formula_conflicts_are_explicit() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 20
    assert methods["native implementation"]["status"] == "unreleased"
    assert methods["FinPos lineage"]["status"] == "material_display_reuse"
    assert methods["agent prompts"]["status"] == "missing"
    assert methods["scaled Kelly criterion"]["status"] == "named_only"
    assert methods["CVaR"]["status"] == "named_only"
    assert methods["orders and fills"]["status"] == "missing"
    assert methods["raw empirical outputs"]["status"] == "missing"

    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["reward_action_alignment"]["status"] == "semantic_conflict"
    assert checks["reward_risk_adjustment"]["status"] == "claim_formula_conflict"
    assert checks["reward_pnl_benchmark"]["status"] == "claim_formula_conflict"
    assert checks["reward_horizon_scaling"]["status"] == "claim_formula_conflict"
    assert checks["future_momentum_at_decision"]["status"] == "lookahead_scope_ambiguous"
    assert checks["scaled_kelly_cvar"]["status"] == "missing_core_mechanics"
    assert checks["election_timing"]["status"] == "conflict"
    assert checks["finpos_main_table_reuse"]["status"] == "exact_180_of_180"


def test_release_search_is_bounded_and_finds_no_attributable_release() -> None:
    releases = rows("release_search_audit.csv")
    assert len(releases) == 7
    assert all(row["attributable_finrs_release_found"] == "False" for row in releases)
    assert all(row["negative_search_boundary"] for row in releases)


def test_manifest_hashes_and_readme_state_fail_closed_result() -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_empirical_table_cells"] == 225
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["empirical_figure_panels"] == 0
    assert manifest["finpos_v1_exact_display_cell_matches"] == 216
    assert manifest["paper_derived_components_executed"] == 3
    assert manifest["strict_success"] is False
    assert manifest["generated_file_sha256"] == {
        path.name: file_sha256(path)
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not an end-to-end FinRS replication",
        "225 displayed empirical cells",
        "Zero of 225 cells",
        "216/225 FinRS cells exactly match FinPos v1",
        "Scaled Kelly, CVaR, volatility adjustment, risk prompts",
        "strict_success` remains false",
    ):
        assert marker in readme


def test_generator_is_deterministic_and_strict_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned FinRS evidence is only available on Bouchet")
    first, second = tmp_path / "first", tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_finrs_paper.py"), "--output", str(tmp_path / "strict"), "--strict"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 1
