from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_efs_paper.py"
SPEC = importlib.util.spec_from_file_location("efs_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def output_dir() -> Path:
    return ROOT / "paper_runs/paper_replication_audits/efs"


def test_committed_v1_and_v2_result_censuses_are_complete() -> None:
    v1 = read_csv(output_dir() / "v1_table_result_conformance.csv")
    v2 = read_csv(output_dir() / "v2_table_result_conformance.csv")
    assert len(v1) == 773
    assert Counter(row["paper_table"] for row in v1) == audit.V1_EXPECTED_TABLE_COUNTS
    assert len(v2) == 877
    assert Counter(row["paper_table"] for row in v2) == audit.V2_EXPECTED_TABLE_COUNTS
    assert sum(row["paper_result_credit"] == "True" for row in v1) == 5
    assert sum(row["paper_result_credit"] == "True" for row in v2) == 8
    assert {row["native_efs_result_credit"] for row in v1 + v2} == {"False"}


def test_cited_baseline_credit_is_formula_specific_and_not_efs_credit() -> None:
    rows = read_csv(output_dir() / "cited_baseline_reproduction.csv")
    assert len(rows) == 27
    assert Counter(row["paper_version"] for row in rows) == {"v1": 15, "v2": 12}
    v1_credit = [row for row in rows if row["paper_version"] == "v1" and row["paper_result_credit"] == "True"]
    v2_credit = [row for row in rows if row["paper_version"] == "v2" and row["paper_result_credit"] == "True"]
    assert len(v1_credit) == 5
    assert {row["metric"] for row in v1_credit} == {"MDD"}
    assert len(v2_credit) == 8
    assert {row["native_efs_evidence"] for row in rows} == {"False"}
    assert {row["protocol"] for row in rows} == {
        "cited_ASMCVaR_623xN_price_relatives_row0_initial_622_equal_weight_transitions"
    }


def test_revision_lineage_detects_carryovers_and_semantic_relabels() -> None:
    rows = read_csv(output_dir() / "version_lineage_audit.csv")
    assert len(rows) == 240
    assert {row["same_at_v2_precision"] for row in rows} == {"True"}
    relabelled = [row for row in rows if row["method_semantics_relabelled"] == "True"]
    assert len(relabelled) == 48
    assert {int(row["v2_row_index"]) for row in relabelled} == {9, 11, 17, 19}
    assert {row["status"] for row in relabelled} == {
        "v1_scores_to_asset_weights_relabelled_as_v2_RMT_QP_factor_weights_same_rounded_value"
    }
    assert {row["native_reproduction_credit"] for row in rows} == {"False"}


def test_method_and_claim_audits_preserve_blocking_conflicts() -> None:
    methods = read_csv(output_dir() / "method_specification_audit.csv")
    claims = read_csv(output_dir() / "qualitative_claim_audit.csv")
    assert len(methods) == 60
    assert sum(row["severity"] == "blocking" for row in methods) == 31
    assert sum(row["assessment"] == "conflict" for row in methods) == 14
    assert {row["native_efs_verified"] for row in methods} == {"False"}
    lineage_claim = next(row for row in claims if "RMT/QP" in row["claim"])
    assert lineage_claim["assessment"] == "unsupported_result_relabel_without_released_lineage"
    native_claim = next(row for row in claims if row["claim"] == "faithful public end-to-end reproduction")
    assert native_claim["observed"].startswith("zero EFS native table cells")


def test_manifest_provenance_and_all_evidence_hashes_are_consistent() -> None:
    manifest = json.loads((output_dir() / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output_dir() / "native_execution.json").read_text(encoding="utf-8"))
    provenance = json.loads((output_dir() / "source_provenance.json").read_text(encoding="utf-8"))
    assert manifest["overall_status"] == (
        "partial_5_of_773_cited_baseline_cells_reproduced_zero_efs_native_results_"
        "v2_audited_separately"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_evidence_route"] == "paper_only_underspecified"
    assert manifest["original_v1_table_result_cells"] == 773
    assert manifest["original_v1_table_cells_reproduced"] == 5
    assert manifest["current_v2_table_result_cells"] == 877
    assert manifest["current_v2_table_cells_reproduced"] == 8
    assert manifest["native_efs_result_cells_reproduced"] == 0
    assert manifest["v1_v2_common_benchmark_cells_same_at_v2_precision"] == 240
    assert manifest["scores_to_weights_cells_relabelled_as_rw"] == 48
    assert manifest["paper_source_compilation"]["v1"]["pages"] == 27
    assert manifest["paper_source_compilation"]["v2"]["pages"] == 13
    assert native["efs_native_execution_attempted"] is False
    assert native["cited_baseline_formula_executed"] is True
    assert provenance["official_efs_repository_found"] is False
    assert provenance["original_paper"]["pdf_sha256"] == audit.ARXIV_V1_PDF_SHA256
    assert provenance["current_revision"]["pdf_sha256"] == audit.ARXIV_V2_PDF_SHA256
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output_dir() / filename) == expected


def test_pinned_sources_and_dynamic_parsers_when_available() -> None:
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_paper_audit")
    mssrm = paper / "mssrm_source"
    asm_cvar = paper / "asm_cvar_source"
    if not paper.exists() or not mssrm.exists() or not asm_cvar.exists():
        return
    assert audit.validate_inputs(paper, mssrm, asm_cvar)["github_search_total"] == 0
    v1 = audit.parse_v1_results(paper)
    v2 = audit.parse_v2_results(paper)
    metrics = audit.baseline_metrics(asm_cvar)
    baseline = audit.apply_baseline_credit(v1, metrics) + audit.apply_baseline_credit(v2, metrics)
    lineage = audit.apply_version_lineage(v1, v2)
    assert (len(v1), len(v2), len(baseline), len(lineage)) == (773, 877, 27, 240)
    assert sum(row["paper_result_credit"] for row in v1) == 5
    assert sum(row["paper_result_credit"] for row in v2) == 8
    assert sum(row["method_semantics_relabelled"] for row in lineage) == 48
