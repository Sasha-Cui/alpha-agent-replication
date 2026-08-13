from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/factorengine"
SPEC = importlib.util.spec_from_file_location("audit_factorengine_paper", ROOT / "scripts/audit_factorengine_paper.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(name: str) -> dict:
    return json.loads((AUDIT_DIR / name).read_text())


def test_two_original_revisions_rebuild_and_visual_qa_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["arxiv_id"] == "2603.16365"
    assert provenance["source_files_each_revision"] == 15
    assert provenance["revision_changed_assets"] == ["paper.tex"]
    assert provenance["revision_scientific_content_change"] is False
    assert provenance["official_pages_visually_checked"] == {"v1": 26, "v2": 26}
    assert provenance["rebuilt_pages_visually_checked"] == {"v1": 26, "v2": 26}
    assert provenance["visual_defects_observed"] == 0
    assert provenance["versions"]["v1"]["official_rebuilt_token_jaccard"] > 0.999
    assert provenance["versions"]["v2"]["official_rebuilt_token_jaccard"] > 0.999
    assert provenance["v1_v2_official_token_jaccard"] > 0.999


def test_all_published_table_measurements_fail_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 276
    assert Counter(row["table"] for row in results) == {
        "table_main_result": 224,
        "cost": 12,
        "parameter_ablation": 40,
    }
    assert all(row["source_tex_recovered"] == "True" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    values = {(row["table"], row["row"], row["metric"]): row["printed_value"] for row in results}
    assert values[("table_main_result", "FE-report-2", "csi300_ic")] == "0.0474"
    assert values[("table_main_result", "FE-report-2", "csi300_ar")] == "0.1899"
    assert values[("cost", "FactorEngine", "time_hours")] == "0.5"
    assert values[("parameter_ablation", "10alpha,2island,top-k", "ric")] == "0.0353"


def test_all_source_figures_are_pinned_without_empirical_credit() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 10
    assert sum(row["empirical"] == "True" for row in figures) == 8
    assert sum(int(row["panels"]) for row in figures if row["empirical"] == "True") == 8
    assert all(len(row["source_asset_sha256"]) == 64 for row in figures)
    assert all(row["raw_numeric_array_recovered"] == "False" for row in figures)
    assert all(row["author_native_regeneration"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_prompt_templates_are_source_specifications_not_runtime_traces() -> None:
    prompts = rows("prompt_template_ledger.csv")
    assert [row["template"] for row in prompts] == ["system_prompt", "chain_of_experience"]
    assert all(len(row["template_sha256"]) == 64 for row in prompts)
    assert all(row["source_tex_recovered"] == "True" for row in prompts)
    assert all(row["filled_runtime_request_recovered"] == "False" for row in prompts)
    assert all(row["filled_runtime_response_recovered"] == "False" for row in prompts)
    assert all(row["native_execution_credit"] == "False" for row in prompts)


def test_only_one_of_two_printed_factor_programs_executes_verbatim() -> None:
    listings = {row["listing"]: row for row in rows("factor_program_execution.csv")}
    assert set(listings) == {"seed_factor", "evolved_factor_after_40_iterations"}
    seed = listings["seed_factor"]
    assert seed["function"] == "factor"
    assert seed["syntax_valid"] == "True"
    assert seed["verbatim_controlled_execution_passed"] == "True"
    assert seed["finite_output_rows"] == "35"
    assert seed["paper_component_credit"] == "True"
    evolved = listings["evolved_factor_after_40_iterations"]
    assert evolved["function"] == "trend_factor"
    assert evolved["syntax_valid"] == "True"
    assert evolved["verbatim_controlled_execution_passed"] == "False"
    assert evolved["observed_failure"] == "NameError: daily_range_expr is not defined"
    assert evolved["paper_component_credit"] == "False"
    assert all(row["author_native_system_credit"] == "False" for row in listings.values())
    assert all(row["published_result_credit"] == "False" for row in listings.values())


def test_material_method_gaps_and_paper_conflicts_are_explicit() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["raw factor inputs"]["sufficiently_specified"] == "True"
    assert methods["fitness"]["sufficiently_specified"] == "True"
    assert methods["agent inference revision/settings"]["sufficiently_specified"] == "False"
    assert methods["Qlib revision and market-data snapshot"]["sufficiently_specified"] == "False"
    assert methods["pre-2017 research-report corpus"]["sufficiently_specified"] == "False"
    assert methods["generated factor pools and trajectories"]["sufficiently_specified"] == "False"
    issues = {row["issue"]: row for row in rows("internal_consistency_audit.csv")}
    assert set(issues) == {
        "mdd_200_run",
        "evolved_listing",
        "initial_factor_count",
        "expected_improvement_sign",
        "yearly_ric_caption",
        "coverage_symbol",
    }
    assert "15.57%" in issues["mdd_200_run"]["evidence"]
    assert "15.89%" in issues["mdd_200_run"]["evidence"]
    assert issues["evolved_listing"]["impact"] == "verbatim execution fails"
    assert "6alpha" in issues["initial_factor_count"]["evidence"]


def test_bounded_release_search_and_unaffiliated_candidate_get_no_native_credit() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["attributable_factorengine_release_found"] is False
    assert provenance["github_repository_search_count"] == 2
    assert provenance["github_code_search_count"] == 27
    assert provenance["huggingface_model_matches"] == 0
    assert provenance["huggingface_dataset_matches"] == 0
    assert "does not prove" in provenance["negative_search_scope"]
    candidate = load_json("candidate_release_audit.json")
    assert candidate["repository"] == "asher21600-svg/factor_engine_reproduction"
    assert candidate["pinned_commit"] == audit.CANDIDATE_COMMIT
    assert candidate["author_attribution"] is False
    assert candidate["compileall"] == "pass"
    assert candidate["only_repository_test"].startswith("fails")
    assert candidate["synthetic_smoke"] == {
        "best_reward": 0.12135,
        "evaluations": 26,
        "islands": 2,
        "iterations": 8,
        "seed_reward": 0.10164,
    }
    assert candidate["tracked_real_data_panels"] is False
    assert candidate["tracked_report_corpus"] is False
    assert candidate["paper_result_cells_regenerated"] == 0
    assert candidate["native_credit"] is False


def test_manifest_and_readme_state_the_exact_fail_closed_boundary() -> None:
    manifest = load_json("manifest.json")
    assert manifest["paper_versions_audited"] == 2
    assert manifest["official_pages_visually_checked"] == 52
    assert manifest["rebuilt_pages_visually_checked"] == 52
    assert manifest["published_numeric_table_units"] == 276
    assert manifest["native_table_units_regenerated"] == 0
    assert manifest["empirical_panels"] == 8
    assert manifest["native_empirical_panels_regenerated"] == 0
    assert manifest["printed_factor_programs"] == 2
    assert manifest["verbatim_factor_programs_executing"] == 1
    assert manifest["attributable_code_release_found"] is False
    assert manifest["strict_success"] is False
    expected = {path.name for path in AUDIT_DIR.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(manifest["generated_file_sha256"]) == expected
    assert all(len(value) == 64 for value in manifest["generated_file_sha256"].values())
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not reproducible end to end",
        "daily_range_expr",
        "0/276 table measurements",
        "0/8 empirical panels",
        "1/2 printed factor programs",
        "not recovered runtime traces",
    ):
        assert marker in readme


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned FactorEngine audit evidence is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audit_factorengine_paper.py"),
            "--output",
            str(tmp_path / "strict"),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict = json.loads((tmp_path / "strict/manifest.json").read_text())
    assert strict["native_table_units_regenerated"] == 0
    assert strict["native_empirical_panels_regenerated"] == 0
    assert strict["strict_success"] is False
