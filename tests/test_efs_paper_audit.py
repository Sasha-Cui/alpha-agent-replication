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
    assert sum(row["paper_result_credit"] == "True" for row in v1) == 11
    assert sum(row["paper_result_credit"] == "True" for row in v2) == 18
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
        "audit_reconstruction_daily_rebalanced_1_over_N_on_cited_"
        "ASMCVaR_matrices_row0_initial_622_transitions"
    }
    assert {row["author_released_baseline_wrapper"] for row in rows} == {
        "False"
    }


def test_cited_ubah_source_adds_one_unique_v1_cell_without_protocol_mixing() -> None:
    rows = read_csv(output_dir() / "cited_ubah_source_reproduction.csv")
    assert Counter(row["paper_version"] for row in rows) == {"v1": 15, "v2": 12}
    matches = {
        (row["paper_version"], row["dataset"], row["metric"])
        for row in rows
        if row["paper_result_credit"] == "True"
    }
    assert matches == {
        ("v1", "FF25", "SR"),
        ("v2", "FF25", "SR"),
        ("v2", "FF49", "SR"),
    }
    new_unique = [
        row for row in rows if row["new_unique_paper_result_credit"] == "True"
    ]
    assert [
        (row["paper_version"], row["dataset"], row["metric"])
        for row in new_unique
    ] == [("v1", "FF25", "SR")]
    assert {row["matlab_release"] for row in rows} == {"2023b"}
    assert {row["source_commit"] for row in rows} == {audit.ASMCVAR_COMMIT}
    assert {row["native_ubah_source_evidence"] for row in rows} == {"True"}
    assert {row["native_efs_evidence"] for row in rows} == {"False"}
    assert {row["full_paths_repeat_equal"] for row in rows} == {"True"}
    assert {row["author_released_efs_baseline_wrapper"] for row in rows} == {
        "False"
    }
    assert len({row["cw_sha256"] for row in rows}) == 5
    assert len({row["daily_return_sha256"] for row in rows}) == 5
    assert len({row["weights_sha256"] for row in rows}) == 5


def test_cited_mssrm_source_execution_is_deterministic_but_mostly_mismatches() -> None:
    rows = read_csv(output_dir() / "cited_mssrm_native_reproduction.csv")
    assert len(rows) == 69
    assert Counter(row["paper_version"] for row in rows) == {"v1": 45, "v2": 24}
    assert sum(row["paper_result_credit"] == "True" for row in rows if row["paper_version"] == "v1") == 1
    assert sum(row["paper_result_credit"] == "True" for row in rows if row["paper_version"] == "v2") == 3
    v1_match = next(row for row in rows if row["paper_version"] == "v1" and row["paper_result_credit"] == "True")
    assert (v1_match["sparsity"], v1_match["dataset"], v1_match["metric"]) == (
        "10", "FF100MEOP", "SR"
    )
    assert {row["native_mssrm_source_evidence"] for row in rows} == {"True"}
    assert {row["native_efs_evidence"] for row in rows} == {"False"}
    assert {row["full_wealth_path_repeat_equal"] for row in rows} == {"True"}
    assert len({row["cw_sha256"] for row in rows}) == 15
    assert {row["octave_version"] for row in rows} == {audit.MSSRM_OCTAVE_VERSION}


def test_original_mssrm_paper_reproduces_despite_efs_baseline_mismatch() -> None:
    original = read_csv(output_dir() / "cited_mssrm_original_paper_reproduction.csv")
    supplement = read_csv(output_dir() / "cited_mssrm_neurips_supplement_correspondence.csv")
    assert len(original) == 36
    assert {row["dataset"] for row in original} == set(audit.MSSRM_ORIGINAL_DATASETS)
    assert {row["sparsity"] for row in original} == {"10", "15", "20"}
    assert {row["metric"] for row in original} == {"CW", "SR"}
    assert {row["original_mssrm_paper_result_credit"] for row in original} == {"True"}
    assert {row["full_wealth_path_repeat_equal"] for row in original} == {"True"}
    assert len({row["cw_sha256"] for row in original}) == 18
    assert {row["native_efs_evidence"] for row in original} == {"False"}
    assert len(supplement) == 6
    assert {row["full_wealth_path_equal_to_mirror"] for row in supplement} == {"True"}
    assert {row["sharpe_equal_to_mirror"] for row in supplement} == {"True"}
    assert {row["native_efs_evidence"] for row in supplement} == {"False"}


def test_asmcvar_original_paper_reproduces_but_efs_rows_do_not() -> None:
    inventory = read_csv(output_dir() / "cited_asmcvar_native_execution_inventory.csv")
    efs = read_csv(output_dir() / "cited_asmcvar_efs_reproduction.csv")
    performance = read_csv(output_dir() / "cited_asmcvar_original_performance_reproduction.csv")
    alpha = read_csv(output_dir() / "cited_asmcvar_original_alpha_reproduction.csv")
    overlap = read_csv(output_dir() / "cited_asmcvar_original_overlap_reproduction.csv")
    cross_runtime = read_csv(output_dir() / "cited_asmcvar_cross_runtime_correspondence.csv")
    assert len(inventory) == 18
    assert {row["matlab_release"] for row in inventory} == {"2023b"}
    assert {row["native_asmcvar_source_evidence"] for row in inventory} == {"True"}
    assert {row["native_efs_evidence"] for row in inventory} == {"False"}
    repeated = [row for row in inventory if row["repeat_path_present"] == "True"]
    assert len(repeated) == 1 and repeated[0]["repeat_path_equal"] == "True"
    assert Counter(row["paper_version"] for row in efs) == {"v1": 45, "v2": 24}
    assert Counter((row["paper_version"], row["paper_result_credit"]) for row in efs) == {
        ("v1", "False"): 44,
        ("v1", "True"): 1,
        ("v2", "False"): 22,
        ("v2", "True"): 2,
    }
    assert {row["native_efs_evidence"] for row in efs} == {"False"}
    assert len(performance) == 36
    mismatch = [row for row in performance if row["original_asmcvar_paper_result_credit"] == "False"]
    assert [(row["dataset"], row["sparsity"], row["metric"]) for row in mismatch] == [
        ("FF49", "10", "SR")
    ]
    assert sum(row["original_asmcvar_paper_result_credit"] == "True" for row in performance) == 35
    assert len(alpha) == 36 and {row["original_asmcvar_paper_result_credit"] for row in alpha} == {"True"}
    assert len(overlap) == 24 and {row["original_asmcvar_paper_result_credit"] for row in overlap} == {"True"}
    assert len(cross_runtime) == 2
    assert {row["equivalent_within_tolerance"] for row in cross_runtime} == {"True"}


def test_mean_cvar_original_paper_reproduces_but_efs_rows_do_not() -> None:
    original = read_csv(
        output_dir() / "cited_mean_cvar_original_paper_reproduction.csv"
    )
    efs = read_csv(output_dir() / "cited_mean_cvar_efs_reproduction.csv")
    assert len(original) == 12
    assert {row["dataset"] for row in original} == set(audit.ASMCVAR_DATASETS)
    assert {row["metric"] for row in original} == {"CW", "SR"}
    assert {row["confidence"] for row in original} == {"0.95"}
    assert {row["repeat_paths_equal"] for row in original} == {"True"}
    assert {
        row["original_mean_cvar_paper_result_credit"] for row in original
    } == {"True"}
    assert Counter(row["paper_version"] for row in efs) == {"v1": 15, "v2": 12}
    assert Counter(
        (row["paper_version"], row["paper_result_credit"]) for row in efs
    ) == {
        ("v1", "False"): 13,
        ("v1", "True"): 2,
        ("v2", "False"): 10,
        ("v2", "True"): 2,
    }
    matches = {
        (row["paper_version"], row["dataset"], row["metric"])
        for row in efs
        if row["paper_result_credit"] == "True"
    }
    assert matches == {
        ("v1", "FF100MEOP", "SR"),
        ("v1", "FF100MEOP", "MDD"),
        ("v2", "FF25", "MDD"),
        ("v2", "FF100", "MDD"),
    }
    assert {row["source_grounded_mean_cvar_evidence"] for row in efs} == {"True"}
    assert {row["native_efs_evidence"] for row in efs} == {"False"}


def test_max_sharpe_source_limit_does_not_recover_efs_rows() -> None:
    rows = read_csv(
        output_dir() / "cited_max_sharpe_limit_efs_reproduction.csv"
    )
    assert Counter(row["paper_version"] for row in rows) == {
        "v1": 15,
        "v2": 12,
    }
    assert Counter(
        (row["paper_version"], row["paper_result_credit"]) for row in rows
    ) == {
        ("v1", "False"): 15,
        ("v2", "False"): 11,
        ("v2", "True"): 1,
    }
    match = next(row for row in rows if row["paper_result_credit"] == "True")
    assert (match["paper_version"], match["dataset"], match["metric"]) == (
        "v2",
        "FF25",
        "MDD",
    )
    assert {row["source_model"] for row in rows} == {
        "mSSRM paper equations (3.3)-(3.4), m=N"
    }
    assert {row["source_commit"] for row in rows} == {audit.MSSRM_COMMIT}
    assert {row["full_wealth_path_repeat_equal"] for row in rows} == {"True"}
    assert len({row["cw_sha256"] for row in rows}) == 5
    assert {
        row["source_grounded_max_sharpe_limit_evidence"] for row in rows
    } == {"True"}
    assert {row["author_released_efs_baseline_wrapper"] for row in rows} == {
        "False"
    }
    assert {row["native_efs_evidence"] for row in rows} == {"False"}


def test_sspo_original_paper_reproduces_but_efs_rows_do_not() -> None:
    original = read_csv(
        output_dir() / "cited_sspo_original_paper_reproduction.csv"
    )
    efs = read_csv(output_dir() / "cited_sspo_efs_reproduction.csv")
    assert len(original) == 10
    assert {row["dataset"] for row in original} == set(
        audit.SSPO_ORIGINAL_DATASETS
    )
    assert {row["metric"] for row in original} == {"CW", "SR"}
    assert {row["source_commit"] for row in original} == {audit.SSPO_COMMIT}
    assert {row["data_commit"] for row in original} == {audit.OLPS_COMMIT}
    assert {row["repeat_paths_equal"] for row in original} == {"True"}
    assert {row["original_sspo_paper_result_credit"] for row in original} == {
        "True"
    }
    assert Counter(row["paper_version"] for row in efs) == {
        "v1": 15,
        "v2": 12,
    }
    assert Counter(
        (row["paper_version"], row["paper_result_credit"]) for row in efs
    ) == {
        ("v1", "False"): 14,
        ("v1", "True"): 1,
        ("v2", "False"): 10,
        ("v2", "True"): 2,
    }
    matches = {
        (row["paper_version"], row["dataset"], row["metric"])
        for row in efs
        if row["paper_result_credit"] == "True"
    }
    assert matches == {
        ("v1", "FF100", "SR"),
        ("v2", "FF100", "CW"),
        ("v2", "FF100", "SR"),
    }
    assert {row["wthresh_compatibility"] for row in efs} == {
        "exact_soft_threshold"
    }
    assert {row["full_paths_repeat_equal"] for row in efs} == {"True"}
    assert len({row["cw_sha256"] for row in efs}) == 5
    assert {row["native_sspo_source_evidence"] for row in efs} == {"True"}
    assert {row["native_efs_evidence"] for row in efs} == {"False"}


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
        "partial_11_of_773_cited_baseline_cells_reproduced_zero_efs_native_results_"
        "v2_audited_separately"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_evidence_route"] == "paper_only_underspecified"
    assert manifest["original_v1_table_result_cells"] == 773
    assert manifest["original_v1_table_cells_reproduced"] == 11
    assert manifest["current_v2_table_result_cells"] == 877
    assert manifest["current_v2_table_cells_reproduced"] == 18
    assert manifest["cited_ubah_v1_cells_checked"] == 15
    assert manifest["cited_ubah_v1_cells_reproduced"] == 1
    assert manifest["cited_ubah_v1_new_unique_cells"] == 1
    assert manifest["cited_ubah_v2_cells_checked"] == 12
    assert manifest["cited_ubah_v2_cells_reproduced"] == 2
    assert manifest["cited_ubah_v2_new_unique_cells"] == 0
    assert manifest["cited_mssrm_v1_cells_checked"] == 45
    assert manifest["cited_mssrm_v1_cells_reproduced"] == 1
    assert manifest["cited_mssrm_v2_cells_checked"] == 24
    assert manifest["cited_mssrm_v2_cells_reproduced"] == 3
    assert manifest["original_mssrm_paper_cells_checked"] == 36
    assert manifest["original_mssrm_paper_cells_reproduced"] == 36
    assert manifest["original_mssrm_neurips_supplement_paths_checked"] == 6
    assert manifest["original_mssrm_neurips_supplement_paths_equal_mirror"] == 6
    assert manifest["cited_asmcvar_v1_cells_checked"] == 45
    assert manifest["cited_asmcvar_v1_cells_reproduced"] == 1
    assert manifest["cited_asmcvar_v2_cells_checked"] == 24
    assert manifest["cited_asmcvar_v2_cells_reproduced"] == 2
    assert manifest["original_asmcvar_cells_checked"] == 96
    assert manifest["original_asmcvar_cells_reproduced"] == 95
    assert manifest["original_mean_cvar_cells_checked"] == 12
    assert manifest["original_mean_cvar_cells_reproduced"] == 12
    assert manifest["cited_mean_cvar_v1_cells_reproduced"] == 2
    assert manifest["cited_mean_cvar_v2_cells_reproduced"] == 2
    assert manifest["cited_max_sharpe_limit_v1_cells_checked"] == 15
    assert manifest["cited_max_sharpe_limit_v1_cells_reproduced"] == 0
    assert manifest["cited_max_sharpe_limit_v2_cells_checked"] == 12
    assert manifest["cited_max_sharpe_limit_v2_cells_reproduced"] == 1
    assert manifest["cited_sspo_v1_cells_checked"] == 15
    assert manifest["cited_sspo_v1_cells_reproduced"] == 1
    assert manifest["cited_sspo_v2_cells_checked"] == 12
    assert manifest["cited_sspo_v2_cells_reproduced"] == 2
    assert manifest["original_sspo_cells_checked"] == 10
    assert manifest["original_sspo_cells_reproduced"] == 10
    assert manifest["native_efs_result_cells_reproduced"] == 0
    assert manifest["v1_v2_common_benchmark_cells_same_at_v2_precision"] == 240
    assert manifest["scores_to_weights_cells_relabelled_as_rw"] == 48
    assert manifest["paper_source_compilation"]["v1"]["pages"] == 27
    assert manifest["paper_source_compilation"]["v2"]["pages"] == 13
    assert native["efs_native_execution_attempted"] is False
    assert native["cited_baseline_formula_executed"] is True
    assert native["v1_cited_baseline_cells_with_credit"] == 11
    assert native["v2_cited_baseline_cells_with_credit"] == 18
    assert native["cited_ubah_source_executed_with_matlab"] is True
    assert native["cited_ubah_matlab_release"] == "2023b"
    assert native["cited_ubah_native_runs"] == 10
    assert native["cited_ubah_full_paths_repeat_exact"] == 5
    assert native["cited_ubah_v1_new_unique_cells"] == 1
    assert native["cited_ubah_v2_new_unique_cells"] == 0
    assert native["cited_mssrm_source_executed_with_octave"] is True
    assert native["cited_mssrm_native_runs"] == 30
    assert native["cited_mssrm_full_paths_repeat_exact"] == 15
    assert native["original_mssrm_paper_cells_matching"] == 36
    assert native["original_mssrm_full_paths_repeat_exact"] == 18
    assert native["original_mssrm_supplement_paths_equal_mirror"] == 6
    assert native["cited_asmcvar_source_executed_with_matlab"] is True
    assert native["cited_asmcvar_native_configurations"] == 18
    assert native["cited_asmcvar_same_runtime_repeats_exact"] == 1
    assert native["original_asmcvar_total_cells_matching"] == 95
    assert native["cited_mean_cvar_equations_executed"] is True
    assert native["cited_mean_cvar_full_paths_repeat_exact"] == 6
    assert native["original_mean_cvar_cells_matching"] == 12
    assert native["cited_max_sharpe_limit_executed_with_octave"] is True
    assert native["cited_max_sharpe_limit_native_runs"] == 10
    assert native["cited_max_sharpe_limit_full_paths_repeat_exact"] == 5
    assert native["cited_sspo_source_executed_with_octave"] is True
    assert native["cited_sspo_native_runs"] == 10
    assert native["cited_sspo_full_paths_repeat_exact"] == 5
    assert native["original_sspo_cells_matching"] == 10
    assert native["sspo_wthresh_compatibility"] == "exact_soft_threshold"
    assert native["native_efs_cells_with_credit"] == 0
    assert provenance["official_efs_repository_found"] is False
    assert provenance["cited_mssrm_native_execution"]["efs_comparison_full_paths_repeat_exact"] == 15
    assert provenance["cited_mssrm_original_paper"]["pdf_sha256"] == audit.MSSRM_PAPER_SHA256
    assert provenance["cited_mssrm_original_paper"]["reported_cells_reproduced"] == 36
    assert provenance["cited_asmcvar_original_paper"]["pdf_sha256"] == audit.ASMCVAR_PAPER_SHA256
    assert provenance["cited_asmcvar_original_paper"]["reported_cells_reproduced"] == 95
    assert provenance["cited_asmcvar_native_execution"]["configurations"] == 18
    ubah = provenance["cited_ubah_native_execution"]
    assert ubah["source_commit"] == audit.ASMCVAR_COMMIT
    assert ubah["native_runs"] == 10
    assert ubah["same_runtime_repeat_paths_exact"] == 5
    assert ubah["efs_v1_new_unique_cells"] == 1
    assert ubah["efs_v2_new_unique_cells"] == 0
    assert ubah["wealth_sha256"] == audit.UBAH_CW_SHA256
    redirect = provenance["cited_asmcvar_author_redirect"]
    assert redirect["commit"] == audit.ASMCVAR_AUTHOR_REDIRECT_COMMIT
    assert redirect["paper_coauthor"] is True
    assert redirect["establishes_author_attribution_for_target"] is True
    assert redirect["additional_executable_source"] is False
    assert provenance["cited_mean_cvar_execution"]["original_paper_cells_reproduced"] == 12
    assert provenance["cited_max_sharpe_limit_execution"]["native_runs"] == 10
    assert provenance["cited_max_sharpe_limit_execution"]["efs_v1_cells_reproduced"] == 0
    assert provenance["cited_max_sharpe_limit_execution"]["efs_v2_cells_reproduced"] == 1
    assert provenance["original_paper"]["pdf_sha256"] == audit.ARXIV_V1_PDF_SHA256
    assert provenance["cited_sspo_original_paper"]["reported_cells_reproduced"] == 10
    assert provenance["cited_sspo_release"]["linked_by_jmlr_paper_page"] is True
    assert provenance["cited_sspo_data_release"]["commit"] == audit.OLPS_COMMIT
    assert provenance["cited_sspo_native_execution"]["native_runs"] == 20
    assert provenance["cited_sspo_native_execution"]["same_runtime_repeat_paths_exact"] == 10
    assert provenance["cited_sspo_native_execution"]["efs_v1_cells_reproduced"] == 1
    assert provenance["cited_sspo_native_execution"]["efs_v2_cells_reproduced"] == 2
    assert provenance["current_revision"]["pdf_sha256"] == audit.ARXIV_V2_PDF_SHA256
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output_dir() / filename) == expected


def test_pinned_sources_and_dynamic_parsers_when_available() -> None:
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_paper_audit")
    mssrm = paper / "mssrm_source"
    asm_cvar = paper / "asm_cvar_source"
    if not paper.exists() or not mssrm.exists() or not asm_cvar.exists():
        return
    validated = audit.validate_inputs(paper, mssrm, asm_cvar)
    assert validated["github_search_total"] == 0
    assert validated["asmcvar_author_redirect_commits"] == 3
    v1 = audit.parse_v1_results(paper)
    assert validated["sspo_source_commits"] == 6
    assert validated["olps_source_commits"] == 44
    v2 = audit.parse_v2_results(paper)
    metrics = audit.baseline_metrics(asm_cvar)
    baseline = audit.apply_baseline_credit(v1, metrics) + audit.apply_baseline_credit(v2, metrics)
    ubah_results = Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_ubah_runs")
    if ubah_results.exists():
        ubah_metrics = audit.load_ubah_native_metrics(ubah_results)
        ubah_rows = audit.apply_ubah_source_credit(
            v1, ubah_metrics
        ) + audit.apply_ubah_source_credit(v2, ubah_metrics)
        assert len(ubah_rows) == 27
        assert sum(row["new_unique_paper_result_credit"] for row in ubah_rows) == 1
    results = Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_octave_runs")
    if results.exists():
        mssrm_metrics = audit.load_mssrm_native_metrics(results)
        mssrm_baseline = audit.apply_mssrm_credit(v1, mssrm_metrics) + audit.apply_mssrm_credit(v2, mssrm_metrics)
        assert len(mssrm_baseline) == 69
        original_metrics = audit.load_mssrm_native_metrics(results, audit.MSSRM_ORIGINAL_DATASETS)
        assert len(audit.original_mssrm_paper_conformance(original_metrics)) == 36
        assert len(audit.mssrm_supplement_correspondence(results, original_metrics)) == 6
        original_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/mssrm_original_paper")
        assert audit.validate_mssrm_original_inputs(original_root, asm_cvar)["paper_pages"] == 28
        asmcvar_metrics = audit.load_asmcvar_native_metrics(results)
        asmcvar_efs = audit.apply_asmcvar_credit(v1, asmcvar_metrics) + audit.apply_asmcvar_credit(v2, asmcvar_metrics)
        assert len(audit.asmcvar_native_inventory(asmcvar_metrics)) == 18
        assert len(asmcvar_efs) == 69
        assert len(audit.original_asmcvar_paper_conformance(asmcvar_metrics)) == 36
        assert len(audit.asmcvar_alpha_conformance(asmcvar_metrics, asm_cvar)) == 36
        assert len(audit.asmcvar_overlap_conformance(asmcvar_metrics)) == 24
        assert len(audit.asmcvar_cross_runtime_correspondence(results)) == 2
        asmcvar_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/asmcvar_original_paper")
        assert audit.validate_asmcvar_original_input(asmcvar_root)["paper_pages"] == 17
    nonsparse = Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_nonsparse_runs")
    if nonsparse.exists():
        mean_cvar = audit.load_mean_cvar_metrics(nonsparse)
        assert len(audit.original_mean_cvar_conformance(mean_cvar)) == 12
        assert len(audit.apply_mean_cvar_credit(v1, mean_cvar)) == 15
        assert len(audit.apply_mean_cvar_credit(v2, mean_cvar)) == 12
        max_sharpe = audit.load_mssrm_nonsparse_metrics(nonsparse)
        assert len(audit.apply_max_sharpe_limit_credit(v1, max_sharpe)) == 15
        assert len(audit.apply_max_sharpe_limit_credit(v2, max_sharpe)) == 12
    lineage = audit.apply_version_lineage(v1, v2)
    sspo_results = Path("/nfs/roberts/scratch/pi_btk22/zc362/efs_sspo_runs")
    if sspo_results.exists():
        original_sspo = audit.load_sspo_metrics(sspo_results, original=True)
        assert len(audit.original_sspo_conformance(original_sspo)) == 10
        efs_sspo = audit.load_sspo_metrics(sspo_results, original=False)
        assert len(audit.apply_sspo_credit(v1, efs_sspo)) == 15
        assert len(audit.apply_sspo_credit(v2, efs_sspo)) == 12
    assert (len(v1), len(v2), len(baseline), len(lineage)) == (773, 877, 27, 240)
    expected_v1 = (7 if results.exists() else 5) + (1 if ubah_results.exists() else 0) + (2 if nonsparse.exists() else 0) + (1 if sspo_results.exists() else 0)
    expected_v2 = (13 if results.exists() else 8) + (3 if nonsparse.exists() else 0) + (2 if sspo_results.exists() else 0)
    assert sum(row["paper_result_credit"] for row in v1) == expected_v1
    assert sum(row["paper_result_credit"] for row in v2) == expected_v2
    assert sum(row["method_semantics_relabelled"] for row in lineage) == 48
