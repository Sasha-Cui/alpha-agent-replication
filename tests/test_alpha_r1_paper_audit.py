from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alpha_r1_paper.py"
SPEC = importlib.util.spec_from_file_location("alpha_r1_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_all_numeric_tables_are_enumerated_and_fail_closed() -> None:
    rows = audit.paper_table_rows()
    assert len(rows) == 124
    assert Counter(row["paper_table"] for row in rows) == {
        "Table 1 Main Experiment Results": 88,
        "Table 2 Ablation Study Results": 24,
        "Table 3 Gating Strategy Comparison": 12,
    }
    assert Counter(row["method"] for row in rows if row["paper_table"].startswith("Table 1")) == {
        method: 8 for method in audit.MAIN_RESULTS
    }
    assert len(
        {
            (row["paper_table"], row["method"], row["asset_pool"], row["metric"])
            for row in rows
        }
    ) == 124
    assert {row["paper_result_credit"] for row in rows} == {False}


def test_all_six_heatmaps_are_transcribed_and_match_default_table_cells() -> None:
    rows = audit.heatmap_rows()
    assert len(rows) == 528
    assert Counter((row["asset_pool"], row["metric"]) for row in rows) == {
        (pool, metric): 88 for pool, metric in audit.HEATMAP_TEXT
    }
    assert {row["top_n"] for row in rows} == set(audit.TOP_N_VALUES)
    assert {row["holding_days"] for row in rows} == set(audit.HOLDING_DAYS)
    assert {row["paper_result_credit"] for row in rows} == {False}
    default = {
        (row["asset_pool"], row["metric"]): row["paper_value"]
        for row in rows
        if row["top_n"] == 10 and row["holding_days"] == 5
    }
    assert default == {
        ("CSI 300", "CR_pct"): 13.0,
        ("CSI 300", "Sharpe"): 1.618,
        ("CSI 300", "MDD_pct"): 6.8,
        ("CSI 1000", "CR_pct"): 42.5,
        ("CSI 1000", "Sharpe"): 4.031,
        ("CSI 1000", "MDD_pct"): 9.3,
    }


def test_claim_gap_and_mechanism_censuses_are_explicit() -> None:
    claims = audit.published_non_table_claims()
    gaps = audit.specification_gaps()
    mechanisms = audit.mechanism_conformance()
    checks = audit.internal_and_source_checks()
    assert len(claims) == 60
    assert Counter(row["claim_role"] for row in claims) == {
        "configuration": 33,
        "result": 27,
    }
    assert {row["paper_result_credit"] for row in claims} == {False}
    assert len(gaps) == 50
    assert {row["resolved"] for row in gaps} == {"no"}
    assert len(mechanisms) == 70
    assert Counter(row["status"] for row in mechanisms) == {
        "absent": 67,
        "narrative_only_unverifiable": 3,
    }
    assert {row["paper_mechanism_credit"] for row in mechanisms} == {False}
    statuses = {row["check"]: row["status"] for row in checks}
    assert statuses["paper availability statement versus paper-era repository"] == "paper_source_release_claim_conflict"
    assert statuses["default CSI1000 Sharpe heatmap versus Table 1"] == "compatible_at_heatmap_precision"
    assert statuses["semantic-description Sharpe decline"] == "compatible_at_claim_precision"


def test_committed_audit_is_self_hashing_and_never_promotes_the_proxy() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/alpha_r1"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    tables = read_csv(output / "paper_numeric_table_conformance.csv")
    heatmaps = read_csv(output / "heatmap_numeric_cell_conformance.csv")
    claims = read_csv(output / "published_non_table_claims.csv")
    mechanisms = read_csv(output / "source_mechanism_conformance.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    assets = read_csv(output / "paper_source_asset_inventory.csv")
    native = json.loads((output / "native_release_inspection.json").read_text(encoding="utf-8"))
    forks = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    fork_census = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == "not_reproduced_official_repository_is_placeholder_zero_native_code_or_results"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_source_release_claim_conflict"] is True
    assert manifest["paper_numeric_table_cells_total"] == 124
    assert manifest["paper_heatmap_numeric_cells_total"] == 528
    assert manifest["published_table_and_heatmap_numeric_result_cells_total"] == 652
    assert manifest["native_table_and_heatmap_result_cells_reproduced"] == 0
    assert manifest["published_non_table_result_claims_total"] == 27
    assert manifest["native_non_table_result_claims_reproduced"] == 0
    assert manifest["source_mechanism_dimensions_total"] == 70
    assert manifest["source_mechanism_matches_or_analogues"] == 0
    assert manifest["source_mechanism_status_counts"] == {
        "absent": 67,
        "narrative_only_unverifiable": 3,
    }
    assert manifest["tracked_source_files_total"] == 1
    assert manifest["tracked_source_python_files_total"] == 0
    assert manifest["public_forks_accessible"] == 9
    assert manifest["public_fork_branch_refs_audited"] == 9
    assert manifest["public_fork_unique_heads_audited"] == 2
    assert manifest["public_fork_divergent_heads_audited"] == 0
    assert manifest["public_fork_unique_commits_beyond_official_history"] == 0
    assert manifest["public_fork_implementation_or_result_artifacts_found"] == 0
    assert manifest["local_motif_proxy_fidelity"] == "M0_narrative_translation"
    assert manifest["local_motif_proxy_paper_result_credit"] is False
    assert len(tables) == 124
    assert len(heatmaps) == 528
    assert len(claims) == 60
    assert len(mechanisms) == 70
    assert len(inventory) == 1 and inventory[0]["relative_path"] == "README.md"
    assert len(assets) == 22
    assert sum(row["asset_role"] == "numeric_result_figure" for row in assets) == 8
    assert sum(int(row["visible_numeric_cells"]) for row in assets) == 528
    assert native["source_history_commits"] == 3
    assert native["paper_era_tracked_files"] == ["README.md"]
    assert native["tracked_python_files"] == 0
    assert native["native_code_execution_possible"] is False
    assert native["motif_proxy_counted_as_native"] is False
    assert len(forks) == 9
    assert Counter(row["relation_to_official_head"] for row in forks) == {
        "official_head_exact": 8,
        "official_history_ancestor": 1,
    }
    assert Counter(row["commits_behind_official"] for row in forks) == {"0": 8, "1": 1}
    assert all(row["unique_commits_beyond_official_history"] == "0" for row in forks)
    assert all(row["unique_blobs_beyond_official_history"] == "0" for row in forks)
    assert all(row["implementation_or_result_artifact_found"] == "False" for row in forks)
    assert fork_census["census_date"] == audit.PUBLIC_FORK_CENSUS_DATE
    assert fork_census["github_rest_reported_forks"] == 9
    assert fork_census["accessible_public_forks"] == 9
    assert fork_census["accessible_branch_refs"] == 9
    assert fork_census["unique_heads"] == 2
    assert fork_census["divergent_unique_heads"] == 0
    assert fork_census["implementation_or_result_artifacts_found"] == 0
    assert fork_census["paper_result_credit"] is False
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_primary_sources_when_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/alpha_r1_source")
    paper_source = Path("/nfs/roberts/scratch/pi_btk22/zc362/alpha_r1_paper/source")
    if not source_root.exists() or not paper_source.exists():
        return
    assert str(audit.run_git(source_root, "rev-parse", "HEAD")).strip() == audit.SOURCE_COMMIT
    assert str(audit.run_git(source_root, "ls-tree", "-r", "--name-only", audit.PAPER_ERA_COMMIT)).splitlines() == [
        "README.md"
    ]
    assert len(audit.source_inventory(source_root)) == 1
    assert len(audit.paper_source_inventory(paper_source)) == 22
    fork_rows, fork_census = audit.public_fork_audit(source_root)
    assert len(fork_rows) == 9
    assert fork_census["unique_heads"] == 2
