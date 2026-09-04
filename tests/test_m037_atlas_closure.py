from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M037_atlas"
AUDIT = ROOT / "paper_runs/paper_replication_audits/atlas"


def test_m037_selects_adaptive_opro_and_keeps_stocksim_as_precursor():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv251015949"
    config = recipe["paper_configuration"]
    assert config["decision_agent"] == "Central Trading Agent"
    assert config["adaptive_window_trading_days"] == 5
    assert config["adaptive_score"] == "clip(50 + 250*ROI, 0, 100)"
    assert config["initial_cash"] == 100000
    assert config["runs_per_configuration"] == 3
    assert len(recipe["missing_atlas_objects"]) == 9
    assert len(recipe["rejected_substitutes"]) == 5
    precursor = recipe["precursor_credit"]
    assert precursor["python_modules"] == 43
    assert precursor["controlled_component_checks_passed"] == 4
    assert precursor["recovered_xom_attributable_to_atlas"] is False


def test_m037_matches_the_pinned_paper_release_and_live_source_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    provenance = json.loads((AUDIT / "source_provenance.json").read_text())
    release = json.loads((AUDIT / "release_execution_audit.json").read_text())
    assert recipe["paper_pdf_sha256"] == provenance["arxiv"]["pdf_sha256"]["v5"]
    assert recipe["paper_source_sha256"] == provenance["arxiv"]["source_sha256"]["v5"]
    assert recipe["source_commit"] == release["head_sha"]
    assert manifest["official_versions_audited"] == ["v1", "v2", "v3", "v4", "v5"]
    assert manifest["published_numeric_result_units"] == 1784
    assert manifest["native_numeric_units_regenerated"] == 0
    assert manifest["empirical_panels"] == 5
    assert manifest["native_empirical_panels_regenerated"] == 0
    live = recipe["live_source_recheck"]
    assert live["main_head_unchanged"] is True
    assert live["main_head"] == release["head_sha"]
    assert live["tags"] == live["releases"] == 0
    assert live["new_official_atlas_layer_found"] is False


def test_m037_preserves_the_exact_atlas_and_precursor_boundaries():
    with (AUDIT / "method_specification_audit.csv").open(newline="") as handle:
        method = {row["dimension"]: row for row in csv.DictReader(handle)}
    assert method["framework_provenance"]["status"] == "cited_same_author_precursor"
    assert method["paper_specific_release"]["status"] == "missing"
    assert method["adaptive_opro"]["status"] == "paper_specification_only"
    assert method["replications"]["status"] == "specified_not_released"
    assert method["precursor_native_output"]["status"] == "recovered_not_paper_attributable"
    assert method["published_results"]["status"] == "not_regenerated"
    release = json.loads((AUDIT / "release_execution_audit.json").read_text())
    assert release["atlas_specific_code_released"] is False
    assert release["adaptive_opro_implementation_released"] is False
    history = release["full_public_history_audit"]
    assert history["historical_xom_initial_cash_roi_percent"] == 5.01564
    assert history["historical_xom_paper_result_credit"] is False


def test_m037_has_no_return_artifact_and_advances_the_ledger():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m037 = rows["M037"]
    assert m037["status"] == "closed_not_evaluable"
    assert m037["monthly_returns_path"] == m037["metrics_path"] == m037["run_manifest_path"] == ""
    assert m037["recipe_path"] and m037["verdict_path"] and m037["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 37
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 30
