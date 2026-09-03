from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M008_alpha_gpt_2_0"
AUDIT = ROOT / "paper_runs/paper_replication_audits/alpha_gpt_lineage"


def test_m008_closes_the_architecture_without_inventing_a_strategy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv240209746"
    assert "Alpha Mining, Alpha Modeling, and Alpha Analysis" in recipe["headline_strategy"]
    assert len(recipe["missing_headline_objects"]) == 7
    assert len(recipe["source_boundaries"]) == 4
    assert len(recipe["rejected_substitutes"]) == 4
    assert "No monthly return is fabricated" in recipe["result_policy"]


def test_m008_matches_the_authoritative_lineage_and_source_audit():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    provenance = json.loads((AUDIT / "source_provenance.json").read_text())
    assert manifest["alpha_gpt2_empirical_result_units"] == 0
    assert manifest["author_linked_code_found"] is False
    assert manifest["community_repository_native_credit"] is False
    assert provenance["alpha_gpt2_pdf_sha256"] == "d4e540118939d4fe18e4ba2a4d76c34971059603690f37d8a450c01673912ded"
    assert provenance["alpha_gpt2_source_sha256"] == "024a8b75847160906aa81c936b8ee3d92d2879699ca65c97dc9476c9dc244c8a"
    with (AUDIT / "version_lineage_audit.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    alpha_gpt2 = next(row for row in rows if row["version"] == "Alpha-GPT 2.0 arXiv v1")
    assert alpha_gpt2["empirical_scope"] == "none; explicitly Draft. Work in progress"
    assert alpha_gpt2["displayed_numeric_result_cells"] == "0"
    assert alpha_gpt2["plotted_result_series"] == "0"


def test_m008_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M008"]["status"] == "closed_not_evaluable"
    assert rows["M008"]["monthly_returns_path"] == rows["M008"]["metrics_path"] == ""
    assert rows["M008"]["run_manifest_path"] == ""
    assert ledger["progress_summary"]["closed"] >= 8
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 6
