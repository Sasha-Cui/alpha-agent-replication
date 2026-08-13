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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/blindtrade"
SPEC = importlib.util.spec_from_file_location("audit_blindtrade_paper", ROOT / "scripts/audit_blindtrade_paper.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(name: str) -> dict:
    return json.loads((AUDIT_DIR / name).read_text())


def test_original_source_rebuild_and_signed_record_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["arxiv_id"] == "2603.17692"
    assert provenance["arxiv_version"] == "v1"
    assert provenance["source_files"] == 14
    assert provenance["official_pages"] == 18
    assert provenance["rebuilt_pages"] == 18
    assert provenance["official_pages_visually_checked"] == 18
    assert provenance["rebuilt_pages_visually_checked"] == 18
    assert provenance["visual_defects_observed"] == 0
    assert provenance["official_rebuilt_token_jaccard"] > 0.998
    assert provenance["openreview_forum_id"] == "t8mBrVVAXh"
    assert provenance["openreview_code_or_dataset_exposed"] is False
    assert provenance["openreview_supplement_exposed"] is False
    assert provenance["openreview_revision_page"] == "No revisions to display."


def test_every_published_numeric_table_cell_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 98
    assert Counter(row["table"] for row in results) == {
        "ic_comparison": 15,
        "main_results": 24,
        "stability": 9,
        "extended_oos_full": 30,
        "extended_oos_breakdown": 20,
    }
    assert all(row["source_tex_recovered"] == "True" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["native_paper_result_credit"] == "False" for row in results)
    values = {(row["table"], row["row"], row["metric"]): row["printed_value"] for row in results}
    assert values[("main_results", "BlindTrade", "sharpe")] == "1.40 ± 0.22"
    assert values[("main_results", "SPY", "mdd")] == "-19.00"
    assert values[("extended_oos_full", "BlindTrade", "sharpe")] == "0.69 ± 0.23"
    assert values[("extended_oos_breakdown", "2024_bull:SPY", "mdd")] == "-8.4"


def test_all_source_figures_are_inventoried_without_result_credit() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 7
    assert sum(row["empirical"] == "True" for row in figures) == 5
    assert sum(int(row["panels"]) for row in figures if row["empirical"] == "True") == 9
    assert all(len(row["source_asset_sha256"]) == 64 for row in figures)
    assert all(row["raw_numeric_array_recovered"] == "False" for row in figures)
    assert all(row["author_native_regeneration"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_four_printed_prompts_are_not_runnable_json_contracts() -> None:
    prompts = rows("prompt_schema_audit.csv")
    assert [row["agent"] for row in prompts] == [
        "Momentum Agent",
        "News-Event Agent",
        "Mean-Reversion Agent",
        "Risk-Regime Agent",
    ]
    assert all(row["source_prompt_recovered"] == "True" for row in prompts)
    assert all(row["printed_schema_valid_json"] == "False" for row in prompts)
    assert all(row["schema_declares_cross_sectional_score"] == "False" for row in prompts)
    assert all(row["batch_instruction_requires_cross_sectional_score"] == "True" for row in prompts)
    assert all(row["filled_runtime_request_recovered"] == "False" for row in prompts)
    assert all(row["filled_runtime_response_recovered"] == "False" for row in prompts)
    assert all(row["native_execution_credit"] == "False" for row in prompts)


def test_current_public_passive_replay_is_component_evidence_only() -> None:
    replay = rows("passive_benchmark_replay.csv")
    assert len(replay) == 28
    matching = {
        (row["table"], row["row"], row["metric"]) for row in replay if row["matches_printed_precision"] == "True"
    }
    assert matching == {
        ("main_results", "SPY", "mdd"),
        ("main_results", "EQWL", "mdd"),
        ("extended_oos_full", "SPY", "cumret"),
        ("extended_oos_full", "SPY", "mdd"),
        ("extended_oos_breakdown", "2024_bull:SPY", "mdd"),
        ("extended_oos_breakdown", "2025_ytd_volatile:SPY", "mdd"),
    }
    assert all(row["price_basis"] == "unadjusted close" for row in replay)
    assert all(row["author_native_credit"] == "False" for row in replay)
    assert all(row["blindtrade_result_credit"] == "False" for row in replay)
    assert all(
        row["evidence_class"] == "current_public_snapshot_component"
        for row in replay
        if row["matches_printed_precision"] == "True"
    )


def test_material_method_gaps_and_validity_defects_are_explicit() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["universe"]["sufficiently_specified"] == "True"
    assert methods["cost"]["sufficiently_specified"] == "True"
    assert methods["anonymization"]["sufficiently_specified"] == "False"
    assert methods["LLM request settings"]["sufficiently_specified"] == "False"
    assert methods["GNN losses"]["sufficiently_specified"] == "False"
    assert methods["RL"]["sufficiently_specified"] == "False"
    assert methods["raw/LLM feature dataset"]["sufficiently_specified"] == "False"
    assert methods["holdings, returns, and plot arrays"]["sufficiently_specified"] == "False"
    issues = {row["issue"]: row for row in rows("internal_consistency_audit.csv")}
    assert set(issues) == {
        "holdout_feature_selection",
        "anonymization_not_ablated",
        "shuffle_control_overclaim",
        "eqwl_identity",
        "printed_json_schemas",
        "batch_schema_field",
        "fully_reproducible_claim",
        "model_cutoff_overlap",
    }
    assert issues["holdout_feature_selection"]["impact"] == "test-set selection leakage"
    assert "S&P 100" in issues["eqwl_identity"]["evidence"]
    assert "January 2025" in issues["model_cutoff_overlap"]["evidence"]


def test_bounded_release_search_never_becomes_absence_proof() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["attributable_blindtrade_release_found"] is False
    assert provenance["first_author_github"] == "ds-academy"
    assert provenance["first_author_public_repositories_checked"] == 14
    assert provenance["first_author_blindtrade_code_search_matches"] == 0
    assert provenance["generic_github_repository_search_count"] == 8
    assert provenance["generic_github_code_search_count"] == 99
    assert provenance["huggingface_model_matches"] == 0
    assert provenance["huggingface_dataset_matches"] == 0
    assert "does not prove" in provenance["negative_search_scope"]


def test_manifest_and_readme_state_the_exact_fail_closed_boundary() -> None:
    manifest = load_json("manifest.json")
    assert manifest["published_numeric_table_cells"] == 98
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["current_public_passive_benchmark_cells_replayed"] == 28
    assert manifest["current_public_passive_benchmark_cells_matching"] == 6
    assert manifest["empirical_figure_panels"] == 9
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["full_system_prompts_recovered"] == 4
    assert manifest["printed_prompt_schemas_valid_json"] == 0
    assert manifest["attributable_code_or_data_release_found"] is False
    assert manifest["strict_success"] is False
    expected = {path.name for path in AUDIT_DIR.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(manifest["generated_file_sha256"]) == expected
    assert all(len(value) == 64 for value in manifest["generated_file_sha256"].values())
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not reproducible end to end",
        "0/98 table cells",
        "0/9 empirical panels",
        "6/98 cells",
        "four verbatim output schemas fail JSON parsing",
        "features are screened on the reported holdout",
        "misidentifies EQWL",
    ):
        assert marker in readme


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned BlindTrade audit evidence is only available on Bouchet")
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
            str(ROOT / "scripts/audit_blindtrade_paper.py"),
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
    assert strict["author_native_table_cells_regenerated"] == 0
    assert strict["author_native_empirical_panels_regenerated"] == 0
    assert strict["strict_success"] is False
