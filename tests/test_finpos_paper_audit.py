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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/finpos"
SPEC = importlib.util.spec_from_file_location(
    "audit_finpos_paper", ROOT / "scripts/audit_finpos_paper.py"
)
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


def test_both_original_revisions_rebuild_and_visual_audit_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["arxiv_id"] == "2510.27251"
    assert provenance["current_version"] == "v2"
    assert provenance["source_files_per_revision"] == {"v1": 19, "v2": 19}
    assert provenance["official_pages"] == provenance["rebuilt_pages"] == {"v1": 17, "v2": 22}
    assert provenance["official_pages_visually_checked"] == {"v1": 17, "v2": 22}
    assert provenance["rebuilt_pages_visually_checked"] == {"v1": 17, "v2": 22}
    assert provenance["visual_defects_observed"] == 0
    assert all(value > 0.999 for value in provenance["official_rebuilt_token_jaccard"].values())
    assert provenance["paper_contains_native_implementation_url"] is False
    assert provenance["attributable_finpos_implementation_found"] is False


def test_every_empirical_table_cell_in_both_revisions_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 519
    assert Counter((row["revision"], row["table_label"]) for row in results) == {
        ("v1", "tab:model_comparison"): 180,
        ("v1", "tab:ablation_single"): 45,
        ("v2", "tab:model_comparison"): 165,
        ("v2", "tab:ablation_single"): 36,
        ("v2", "tab:sampling-sensitivity"): 15,
        ("v2", "tab:signal-ablation"): 15,
        ("v2", "tab:extreme_market"): 63,
    }
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["raw_result_record_recovered"] == "False" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)


def test_rendered_vector_figures_are_static_evidence_not_raw_results() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 12
    assert sum(int(row["empirical_panels"]) for row in figures if row["revision"] == "v1") == 15
    assert sum(int(row["empirical_panels"]) for row in figures if row["revision"] == "v2") == 11
    assert all(len(row["source_asset_sha256"]) == 64 for row in figures)
    assert all(row["underlying_numeric_array_or_run_log_recovered"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)


def test_twelve_prompts_are_recovered_but_only_four_examples_are_valid_json() -> None:
    prompts = rows("prompt_contract_audit.csv")
    assert len(prompts) == 12
    assert Counter(row["strict_json_contract_status"] for row in prompts) == {
        "valid_json_example": 4,
        "invalid_missing_comma": 2,
        "invalid_union_syntax": 3,
        "external_unreleased_suffix": 2,
        "invalid_bare_type_expression": 1,
    }
    assert all(row["runtime_prompt_executed"] == "False" for row in prompts)
    assert all(row["author_model_response_recovered"] == "False" for row in prompts)


def test_eleven_paper_derived_mechanics_execute_with_zero_native_credit() -> None:
    components = {row["component"]: row for row in rows("component_execution_audit.csv")}
    assert set(components) == {
        "single_step_log_return", "position_log_return", "position_update",
        "multi_timescale_score", "literal_reward", "sharpe_ratio",
        "maximum_drawdown", "empirical_var_cvar", "calmar_ratio",
        "cr_percent_refusal", "cvar_quantity_refusal",
    }
    assert all(row["deterministic_control_passed"] == "True" for row in components.values())
    assert all(row["paper_derived_not_author_code"] == "True" for row in components.values())
    assert all(row["author_native_pipeline_executed"] == "False" for row in components.values())
    assert all("not author code" in row["boundary"] for row in components.values())


def test_method_and_consistency_ledgers_preserve_missing_lineage_and_conflicts() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 22
    assert methods["native implementation"]["status"] == "unreleased"
    assert methods["agent prompts"]["status"] == "partial_static"
    assert methods["position sizing"]["status"] == "equation_underspecified"
    assert methods["initial account state"]["status"] == "missing"
    assert methods["orders and fills"]["status"] == "missing"
    assert methods["raw empirical outputs"]["status"] == "missing"

    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["reward_action_alignment"]["status"] == "semantic_conflict"
    assert checks["reward_scale"]["status"] == "asset_scale_dependent"
    assert checks["cvar_tail_convention"]["status"] == "conflict"
    assert checks["cvar_sign_claim"]["status"] == "conflict"
    assert checks["cvar_to_integer_quantity"]["status"] == "dimensionally_underspecified"
    assert checks["continuous_position_claim"]["status"] == "terminology_conflict"
    assert checks["cr_log_to_percent"]["status"] == "missing_mapping"
    assert checks["v2_extreme_period"]["status"] == "conflict"
    assert checks["election_timing"]["status"] == "conflict"
    assert checks["v2_tsla_figure_lineage"]["status"] == "stale_v1_result"
    assert checks["v2_aapl_figure_lineage"]["status"] == "stale_v1_result"
    assert checks["v2_extreme_table_lineage"]["status"] == "mixed_revision_conflict"


def test_release_search_is_bounded_and_finds_no_attributable_release() -> None:
    releases = rows("release_search_audit.csv")
    assert len(releases) == 9
    assert all(row["attributable_finpos_release_found"] == "False" for row in releases)
    assert all(row["negative_search_boundary"] for row in releases)
    assert {row["observed_matches"] for row in releases if row["surface"] == "GitHub repositories"} == {"0"}


def test_manifest_hashes_and_readme_state_the_fail_closed_result() -> None:
    manifest = load_json("manifest.json")
    assert manifest["current_empirical_table_cells"] == 294
    assert manifest["v1_empirical_table_cells"] == 225
    assert manifest["revision_level_empirical_table_cells"] == 519
    assert manifest["current_empirical_figure_panels"] == 11
    assert manifest["v1_empirical_figure_panels"] == 15
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["prompt_templates_printed"] == 12
    assert manifest["valid_printed_json_examples"] == 4
    assert manifest["paper_derived_components_executed"] == 11
    assert manifest["strict_success"] is False
    expected = {
        path.name: file_sha256(path)
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert manifest["generated_file_sha256"] == expected
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not an end-to-end FinPos replication",
        "294 displayed empirical result cells",
        "Zero of 519 revision-level cells and 0/26 revision-level panels",
        "Only 4/12 output examples are valid JSON",
        "CVaR to integer order quantity",
        "strict_success` remains false",
    ):
        assert marker in readme


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned FinPos evidence is only available on Bouchet")
    first, second = tmp_path / "first", tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_finpos_paper.py"), "--output", str(tmp_path / "strict"), "--strict"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert json.loads((tmp_path / "strict/manifest.json").read_text())["strict_success"] is False
