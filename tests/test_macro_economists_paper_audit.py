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

from alpha_evolve import macro_economists_paper_components as component


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/macro_economists_machine"
SPEC = importlib.util.spec_from_file_location(
    "audit_macro_economists_paper", ROOT / "scripts/audit_macro_economists_paper.py"
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


def test_original_source_rebuild_and_visual_audit_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["arxiv_id"] == "2606.08283"
    assert provenance["arxiv_version"] == "v1"
    assert provenance["source_files"] == 7
    assert provenance["official_pages"] == provenance["rebuilt_pages"] == 46
    assert provenance["official_pages_visually_checked"] == 46
    assert provenance["rebuilt_pages_visually_checked"] == 46
    assert provenance["document_layout_defects_observed"] == 0
    assert provenance["official_rebuilt_token_jaccard"] > 0.998
    assert provenance["paper_contains_native_implementation_url"] is False
    assert provenance["paper_says_replication_materials_available_on_request"] is True
    assert provenance["attributable_implementation_found"] is False


def test_all_132_empirical_cells_and_12_panels_fail_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 132
    assert Counter(row["table_label"] for row in results) == {
        "tab:fullperiod": 25,
        "tab:incremental": 7,
        "tab:bootstrap": 24,
        "tab:subperiod": 15,
        "tab:txcost": 25,
        "tab:riskprofile": 36,
    }
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["raw_result_record_recovered"] == "False" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    figures = rows("figure_inventory.csv")
    assert len(figures) == 4
    assert sum(int(row["empirical_panels"]) for row in figures) == 12
    assert all(row["underlying_numeric_array_or_run_log_recovered"] == "False" for row in figures)


def test_18_equation_checks_and_four_fail_closed_core_operations() -> None:
    checks = {row["component"]: row for row in rows("component_execution_audit.csv")}
    assert len(checks) == 22
    assert all(row["deterministic_control_passed"] == "True" for row in checks.values())
    assert all(row["paper_derived_not_author_code"] == "True" for row in checks.values())
    assert all(row["author_native_pipeline_executed"] == "False" for row in checks.values())
    for name in (
        "rule_regime_probabilities",
        "constrained_portfolio_weights",
        "stationary_bootstrap_test",
        "llm_contract_validation",
    ):
        assert "not author code" in checks[name]["boundary"]


def test_literal_cap_can_violate_claimed_bound_and_ambiguities_raise() -> None:
    literal = component.literal_cyclical_cap_then_renormalize(
        [0.9, 0.1], [True, False], cap=0.45
    )
    assert literal[0] > 0.45
    with pytest.raises(component.UnderspecifiedPaperMechanic):
        component.rule_regime_probabilities({})
    with pytest.raises(component.UnderspecifiedPaperMechanic):
        component.constrained_portfolio_weights()
    with pytest.raises(component.UnderspecifiedPaperMechanic):
        component.stationary_bootstrap_sharpe_test()
    with pytest.raises(component.UnderspecifiedPaperMechanic):
        component.validate_llm_contract()


def test_missing_public_artifacts_and_method_boundaries_are_explicit() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 22
    assert methods["native implementation"]["status"] == "unreleased"
    assert methods["replication artifacts"]["status"] == "request_only"
    assert methods["LLM model"]["status"] == "mutable_alias_only"
    assert methods["LLM prompts"]["status"] == "partial"
    assert methods["cyclical set"]["status"] == "missing"
    assert methods["risk controls"]["status"] == "underspecified"
    assert methods["stationary bootstrap"]["status"] == "underspecified"
    assert methods["raw empirical outputs"]["status"] == "missing"
    releases = rows("release_search_audit.csv")
    assert len(releases) == 6
    assert all(row["attributable_release_found"] == "False" for row in releases)
    assert all(row["negative_search_boundary"] for row in releases)


def test_visual_and_algorithm_conflicts_are_not_silently_reconciled() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["cost_figure_vs_table"]["status"] == "major_numeric_conflict"
    assert checks["cost_figure_benchmark_ranking"]["status"] == "claim_conflict"
    assert checks["debate_weight_divergence_dates"]["status"] == "data_window_conflict"
    assert checks["soft_landing_endpoint"]["status"] == "label_conflict"
    assert checks["rule_signal_domain"]["status"] == "definition_conflict"
    assert checks["rule_regime_residual"]["status"] == "algorithm_conflict"
    assert checks["cyclical_cap_renormalization"]["status"] == "algorithm_conflict"
    assert checks["prompt_schema"]["status"] == "claim_artifact_gap"
    assert checks["any_llm_comparison"]["status"] == "statistic_undefined"


def test_manifest_hashes_readme_and_strict_mode_fail_closed(tmp_path: Path) -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_empirical_table_cells"] == 132
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["empirical_figure_panels"] == 12
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["paper_derived_components_executed"] == 22
    assert manifest["fail_closed_underspecified_core_operations"] == 4
    assert manifest["strict_success"] is False
    assert manifest["generated_file_sha256"] == {
        path.name: file_sha256(path)
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not an end-to-end replication",
        "132 displayed empirical table cells",
        "12 empirical panels",
        "Zero of 132 cells and zero of 12 panels",
        "upon reasonable request",
        "0.84--0.92",
        "roughly 0.48--0.57",
        "begins in 2017",
        "strict_success` remains false",
    ):
        assert marker in readme

    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned evidence is only available on Bouchet")
    first, second = tmp_path / "first", tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_macro_economists_paper.py"),
         "--output", str(tmp_path / "strict"), "--strict"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 1
