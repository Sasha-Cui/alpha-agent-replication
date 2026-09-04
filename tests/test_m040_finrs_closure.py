from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M040_finrs"
AUDIT = ROOT / "paper_runs/paper_replication_audits/finrs"


def test_m040_selects_the_missing_risk_policy_not_shared_reward_equations():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv251112599"
    config = recipe["paper_configuration"]
    assert config["decision_agents"] == ["direction", "quantity and risk"]
    assert config["named_risk_references"] == [
        "scaled Kelly Criterion", "CVaR", "volatility adjustment", "account exposure"
    ]
    assert config["future_reward_horizons_days"] == [1, 7, 30]
    assert config["native_assets"] == ["TSLA", "AAPL", "AMZN", "NFLX", "COIN"]
    assert len(recipe["missing_headline_objects"]) == 10
    assert len(recipe["rejected_substitutes"]) == 5


def test_m040_matches_the_pinned_paper_release_and_component_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    provenance = json.loads((AUDIT / "source_provenance.json").read_text())
    assert recipe["paper_pdf_sha256"] == provenance["pinned_input_sha256"]["primary/official-v1.pdf"]
    assert recipe["paper_source_sha256"] == provenance["pinned_input_sha256"]["primary/source-v1.tar"]
    assert provenance["official_pages"] == 6
    assert manifest["active_empirical_table_cells"] == 225
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["attributable_finrs_implementation_found"] is False
    credit = recipe["paper_component_credit"]
    assert credit["paper_derived_mechanics_executed"] == 3
    assert credit["controlled_checks_passed"] == 3
    assert credit["components_identical_to_finpos_v1"] == 3
    live = recipe["live_release_recheck"]
    assert live["github_repository_search_arxiv"] == 0
    assert live["github_repository_search_title"] == 0
    assert live["attributable_implementation_found"] is False


def test_m040_cross_paper_lineage_is_reuse_not_result_credit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    lineage = recipe["cross_paper_lineage"]
    assert lineage["exact_display_matches"] == 216
    assert lineage["total_cells"] == 225
    assert lineage["main_table_exact_matches"] == lineage["main_table_cells"] == 180
    assert lineage["ablation_exact_matches"] == 36
    assert lineage["ablation_cells"] == 45
    with (AUDIT / "cross_paper_result_lineage.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 225
    assert sum(row["exact_display_match"] == "True" for row in rows) == 216
    with (AUDIT / "method_specification_audit.csv").open(newline="") as handle:
        method = {row["dimension"]: row for row in csv.DictReader(handle)}
    assert method["scaled Kelly criterion"]["status"] == "named_only"
    assert method["CVaR"]["status"] == "named_only"
    assert method["volatility adjustment"]["status"] == "named_only"
    assert method["multi-scale reward"]["status"] == "equation_partial"


def test_m040_has_no_return_artifact_and_closes_batch_of_forty():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m040 = rows["M040"]
    assert m040["status"] == "closed_not_evaluable"
    assert m040["monthly_returns_path"] == m040["metrics_path"] == m040["run_manifest_path"] == ""
    assert m040["recipe_path"] and m040["verdict_path"] and m040["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 40
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 33
