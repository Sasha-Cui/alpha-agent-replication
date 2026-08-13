"""Contracts for the fail-closed GPT-Signal paper/source audit."""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_gpt_signal_paper.py"
SPEC = importlib.util.spec_from_file_location("audit_gpt_signal_paper", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)

ARXIV_PAPER = ROOT / "literature_review/papers/59_gpt_signal_generative_ai_for_semi_automated_feature_engineering_arxiv_v1.pdf"
ACL_PAPER = ROOT / "literature_review/papers/60_gpt_signal_generative_ai_for_semi_automated_feature_engineering_acl_2024.pdf"
OUTPUT = ROOT / "paper_runs/paper_replication_audits/gpt_signal"


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_both_official_papers_are_pinned_and_fully_visually_audited() -> None:
    assert audit.sha256(ARXIV_PAPER) == audit.EXPECTED_ARXIV_PDF_SHA256
    assert audit.sha256(ACL_PAPER) == audit.EXPECTED_ACL_PDF_SHA256
    audit.validate_pdf(ARXIV_PAPER, audit.EXPECTED_ARXIV_PDF_SHA256, 13, "arXiv v1")
    audit.validate_pdf(ACL_PAPER, audit.EXPECTED_ACL_PDF_SHA256, 12, "ACL")
    provenance = json.loads((OUTPUT / "source_provenance.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert provenance["arxiv_pdf_pages_visually_inspected"] == 13
    assert provenance["acl_pdf_pages_visually_inspected"] == 12
    assert provenance["source_rebuild_pages_visually_inspected"] == 13
    assert manifest["official_pdf_pages_visually_inspected"] == 25


def test_arxiv_source_archive_inventory_has_no_system_code_or_data() -> None:
    rows = csv_rows("paper_source_inventory.csv")
    assert len(rows) == 71
    assert sum(int(row["bytes"]) for row in rows) == 4_294_017
    assert Counter(row["role"] for row in rows) == {
        "published_vector_figure": 23,
        "paper_asset": 24,
        "paper_source": 4,
        "other": 20,
    }
    assert all(row["system_code"] == "no" and row["system_data"] == "no" for row in rows)


def test_author_source_is_completely_pinned_without_reemitting_credentials() -> None:
    rows = csv_rows("author_source_inventory.csv")
    assert len(rows) == 13_884
    assert sum(int(row["bytes"]) for row in rows) == 170_997_569
    assert sum(row["compile_status"] == "compiled" for row in rows) == 6
    roles = Counter(row["role"] for row in rows)
    assert roles["author_input_workbook"] == 373
    assert roles["author_llm_output"] == 17
    assert roles["author_implementation"] == 6
    assert sum(row["contains_redacted_credential_pattern"] == "yes" for row in rows) == 2
    provenance = json.loads((OUTPUT / "source_provenance.json").read_text(encoding="utf-8"))
    assert provenance["head"] == audit.EXPECTED_AUTHOR_HEAD
    assert provenance["tree_sha256"] == audit.EXPECTED_AUTHOR_TREE_SHA256
    assert provenance["archive_sha256"] == audit.EXPECTED_AUTHOR_ARCHIVE_SHA256
    assert provenance["plaintext_credential_matches_redacted"] == 4
    assert provenance["license"] == "none_observed"
    assert provenance["dependency_manifest"] == "none_observed"
    for path in OUTPUT.iterdir():
        if path.suffix.lower() in {".csv", ".json", ".md"}:
            assert re.search(r"sk-[A-Za-z0-9_-]{10,}", path.read_text(encoding="utf-8")) is None


def test_all_1309_published_heatmap_cells_replay_from_author_inputs() -> None:
    rows = csv_rows("correlation_cell_reproduction.csv")
    assert len(rows) == 1_309
    assert sum(row["source_code_power_match"] == "yes" for row in rows) == 1_309
    assert all(row["credit"] == "author_data_deterministic_replay" for row in rows)
    assert all(row["llm_regenerated"] == "no" for row in rows)
    summaries = {row["matrix"]: row for row in csv_rows("correlation_matrix_summary.csv")}
    assert len(summaries) == 13
    assert summaries["all_3m_all"]["source_code_power_matches"] == "289"
    assert summaries["it_1m_new"]["cross_sections"] == "59"
    assert all(row["source_code_power_matches"] == row["cells"] for row in summaries.values())


def test_paper_raps_equation_is_rejected_in_favor_of_code_and_raw_gpt_lineage() -> None:
    rows = csv_rows("correlation_cell_reproduction.csv")
    assert sum(row["paper_equation_multiply_match"] == "yes" for row in rows) == 1_205
    summaries = {row["matrix"]: row for row in csv_rows("correlation_matrix_summary.csv")}
    for key, row in summaries.items():
        if key.endswith("_new"):
            assert row["paper_equation_multiply_matches"] == "37"
        elif key == "all_3m_all":
            assert row["paper_equation_multiply_matches"] == "257"
        else:
            assert row["paper_equation_multiply_matches"] == row["cells"]
    formulas = {row["signal"]: row for row in csv_rows("formula_lineage.csv")}
    assert formulas["RAPS"]["assessment"] == "contradiction"
    assert "** beta" in formulas["RAPS"]["released_code_formula"]
    assert formulas["RAPS"]["raw_gpt4_output_recovered"] == "yes"
    assert formulas["VEC"]["raw_gpt4_output_recovered"] == "no"
    assert sum(row["raw_gpt4_output_recovered"].startswith("yes") for row in formulas.values()) == 5


def test_240_of_245_published_boxplot_statistics_replay() -> None:
    rows = csv_rows("boxplot_stat_reproduction.csv")
    assert len(rows) == 245
    assert sum(row["match_tolerance_1e-4"] == "yes" for row in rows) == 240
    anomalies = [row for row in rows if row["match_tolerance_1e-4"] == "no"]
    assert {(row["figure"], row["model"]) for row in anomalies} == {("all_3m", "EVC")}
    assert {row["statistic"] for row in anomalies} == {"q1", "med", "q3", "whislo", "whishi"}
    assert all(math.isclose(float(row["replay_minus_paper"]), -0.02, abs_tol=1e-7) for row in anomalies)
    summaries = {row["figure"]: row for row in csv_rows("boxplot_figure_summary.csv")}
    assert summaries["all_3m"]["matches_tolerance_1e-4"] == "30"
    assert all(row["matches_tolerance_1e-4"] == "35" for key, row in summaries.items() if key != "all_3m")


def test_complete_author_history_exhausts_preserved_output_lineage() -> None:
    history = csv_rows("author_history_inventory.csv")
    assert len(history) == 20
    assert history[0]["commit"] == audit.EXPECTED_AUTHOR_ROOT
    assert history[-1]["commit"] == audit.EXPECTED_AUTHOR_HEAD
    assert all(row["all_sector_trace_status"] == "absent" for row in history)
    assert sum(int(row["preserved_2016_2020_output_traces"]) > 0 for row in history) == 4
    assert {row["preserved_trace_group"] for row in history} == {
        "none", "information_technology", "energy",
    }

    rows = csv_rows("author_history_trace_conformance.csv")
    assert len(rows) == 70
    matched = Counter(row["trace"] for row in rows if row["match_tolerance_1e-4"] == "yes")
    assert matched == {"energy_3m": 35}
    assert sum(row["trace"] == "information_technology_3m" for row in rows) == 35
    assert all(
        row["paper_result_credit"] == "historical_author_output_trace"
        for row in rows if row["trace"] == "energy_3m"
    )


def test_published_median_claims_are_counted_instead_of_generalized() -> None:
    summaries = {row["figure"]: row for row in csv_rows("boxplot_figure_summary.csv")}
    assert sum(int(row["new_signal_medians_above_baseline"]) for row in summaries.values()) == 35
    assert summaries["it_3m"]["new_signal_medians_above_baseline"] == "6"
    assert summaries["en_1m"]["new_signal_medians_above_baseline"] == "1"
    methods = {row["dimension"]: row for row in csv_rows("method_specification_audit.csv")}
    assert methods["IT 3M prose"]["assessment"] == "paper_internal_contradiction"
    assert methods["Energy 1M generalization"]["assessment"] == "weak_support"
    assert methods["all-sector EVC plot"]["assessment"] == "unexplained_difference"


def test_monthly_quarterly_alignment_concretely_exposes_future_information() -> None:
    rows = csv_rows("monthly_lookahead_trace.csv")
    assert [row["target_month_end"] for row in rows] == [
        "2016-01-31", "2016-02-29", "2016-03-31", "2016-04-30", "2016-05-31", "2016-06-30",
    ]
    assert [float(row["released_descending_ffill_pe"]) for row in rows] == [11.754171] * 3 + [10.911215] * 3
    assert [float(row["chronological_availability_ffill_pe"]) for row in rows] == [11.468153] * 3 + [11.754171] * 3
    assert all(row["future_quarter_value_used"] == "yes" for row in rows)
    methods = {row["dimension"]: row for row in csv_rows("method_specification_audit.csv")}
    assert methods["monthly factor alignment"]["assessment"] == "lookahead_bias"
    assert methods["missing-value imputation"]["assessment"] == "lookahead_bias"


def test_deleted_paper_repo_and_recovered_unlinked_source_are_not_conflated() -> None:
    artifacts = {row["artifact"]: row for row in csv_rows("artifact_access_audit.csv")}
    assert artifacts["paper-listed GPT-signal repository"]["status"] == "current_404_one_archived_placeholder_capture"
    assert artifacts["paper-listed GPT-signal repository"]["credit"] == "no system code recovered"
    assert artifacts["author Thesis repository"]["relationship"] == "author-owned unlinked source/data/output recovery"
    provenance = json.loads((OUTPUT / "source_provenance.json").read_text(encoding="utf-8"))
    assert provenance["archived_placeholder_tracked_files"] == 1
    assert provenance["author_repository_relationship"] == "author_owned_pre_publication_source_recovery_not_linked_by_paper"
    evidence = {row["artifact"]: row for row in csv_rows("discovery_evidence.csv")}
    assert len(evidence) == len(audit.EVIDENCE_HASHES)
    assert evidence["wayback_repo_20240816.html"]["sha256"] == audit.EVIDENCE_HASHES["wayback_repo_20240816.html"]


def test_method_audit_states_every_major_nonfaithfulness_boundary() -> None:
    rows = {row["dimension"]: row for row in csv_rows("method_specification_audit.csv")}
    assert len(rows) == 31
    assert rows["LLM randomness"]["assessment"] == "missing"
    assert rows["iterative refinement"]["assessment"] == "unsupported"
    assert rows["FactSet access"]["assessment"] == "paper_error"
    assert rows["price field"]["assessment"] == "source_only_detail"
    assert rows["monthly cross-sections"]["assessment"] == "stale_runner"
    assert rows["native control flow"]["assessment"] == "stale_runner"
    assert rows["historical output traces"]["assessment"] == "history_exhausted"
    assert rows["significance"]["assessment"] == "unsupported"
    assert rows["economic evaluation"]["assessment"] == "missing"
    assert rows["speed/scale claims"]["assessment"] == "unsupported"


def test_manifest_reports_result_recovery_without_claiming_full_replication() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((OUTPUT / "native_execution.json").read_text(encoding="utf-8"))
    assert manifest["published_result_units_reproduced"] == 1_549
    assert manifest["published_result_units"] == 1_554
    assert manifest["author_history_commits_audited"] == 20
    assert manifest["historical_energy_3m_vector_statistics_matched"] == 35
    assert manifest["historical_information_technology_3m_vector_statistics_matched"] == 0
    assert manifest["historical_all_sector_output_trace_recovered"] is False
    assert math.isclose(manifest["published_result_unit_recovery_rate"], 1549 / 1554)
    assert manifest["overall_fidelity"] == "partial_1549_of_1554_published_quantitative_units_replayed_from_author_data_no_end_to_end_LLM_replication_monthly_lookahead_present"
    assert manifest["full_end_to_end_pipeline_reproduced"] is False
    assert manifest["llm_calls_made"] == 0
    assert native["llm_generation_reproduced"] is False
    assert native["author_history_commits_audited"] == 20
    assert native["historical_energy_3m_vector_statistics_matched"] == 35
    assert native["full_end_to_end_pipeline_reproduced"] is False
    assert native["paper_result_credit"] == "partial_author_data_and_source_semantics_replay_not_full_paper_replication"
    readme = " ".join((OUTPUT / "README.md").read_text(encoding="utf-8").split())
    assert "1549/1554 (99.678%)" in readme
    assert "not an end-to-end regeneration" in readme
    assert "Why 99.678% result recovery is not 99.678% paper fidelity" in readme
