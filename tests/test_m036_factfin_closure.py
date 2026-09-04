from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M036_factfin"
AUDIT = ROOT / "paper_runs/paper_replication_audits/factfin"


def test_m036_separates_the_benchmark_from_the_factfin_trading_policy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv251007920"
    assert recipe["system_scope"]["SYS-FACTFIN"].startswith("in-scope")
    assert recipe["system_scope"]["SYS-FINLAKE-BENCH"].startswith("out-of-scope")
    config = recipe["paper_configuration"]
    assert config["components"] == [
        "Strategy Code Generator", "Retrieval-Augmented Generation",
        "Monte Carlo Tree Search", "Counterfactual Simulator",
    ]
    assert config["action_space"] == ["buy", "sell", "hold"]
    assert config["mcts_depth"] == 10
    assert config["mcts_ucb_c"] == 0.5
    assert len(recipe["missing_headline_objects"]) == 10
    assert len(recipe["rejected_substitutes"]) == 5


def test_m036_matches_the_pinned_paper_release_and_live_author_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    provenance = json.loads((AUDIT / "source_provenance.json").read_text())
    assert recipe["paper_pdf_sha256"] == provenance["official_pdf_sha256"]
    assert recipe["paper_source_sha256"] == provenance["arxiv_source_sha256"]
    assert manifest["arxiv_manuscript_source_files"] == 14
    assert manifest["public_system_source_files_recovered"] == 0
    assert manifest["public_benchmark_records_recovered"] == 0
    assert manifest["generated_strategies_recovered"] == 0
    assert manifest["published_empirical_or_derived_numeric_table_cells"] == 525
    assert manifest["factfin_direct_numeric_result_cells"] == 120
    assert manifest["factfin_cells_faithfully_regenerated"] == 0
    live = recipe["live_author_surface_recheck"]
    assert live["public_repositories"] == ["XiangyuLi616/XiangyuLi616.github.io"]
    assert live["homepage_head"] == provenance["author_homepage_repository_head"]
    assert live["new_factfin_or_benchmark_artifact_found"] is False


def test_m036_preserves_strategy_search_and_execution_gaps():
    with (AUDIT / "method_specification_audit.csv").open(newline="") as handle:
        method = {row["dimension"]: row for row in csv.DictReader(handle)}
    assert method["strategy_language"]["status"] == "missing_runtime_contract"
    assert method["rag_embedding"]["status"] == "specified_alias_and_k_only"
    assert method["mcts"]["status"] == "specified_two_hyperparameters_only"
    assert method["counterfactual_simulator"]["status"] == "specified_high_level_only"
    assert method["position_sizing"]["status"] == "missing_position_sizing"
    assert method["signal_to_fill_timing"]["status"] == "missing_fill_timing"
    assert method["generated_strategies"]["status"] == "missing_generated_strategy_code"
    with (AUDIT / "internal_consistency_audit.csv").open(newline="") as handle:
        checks = {row["claim_id"]: row for row in csv.DictReader(handle)}
    assert checks["benchmark_name"]["status"] == "hard_naming_conflict"
    assert checks["scoring_equation"]["status"] == "metric_definition_conflict"
    assert checks["fine_tune_test_overlap"]["status"] == "temporal_overlap_unresolved"


def test_m036_has_no_return_artifact_and_advances_the_ledger():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m036 = rows["M036"]
    assert m036["status"] == "closed_not_evaluable"
    assert m036["monthly_returns_path"] == m036["metrics_path"] == m036["run_manifest_path"] == ""
    assert m036["recipe_path"] and m036["verdict_path"] and m036["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 36
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 29
