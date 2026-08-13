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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/alphaagentevo"
SPEC = importlib.util.spec_from_file_location(
    "audit_alphaagentevo_paper", ROOT / "scripts/audit_alphaagentevo_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text())


def test_accepted_manuscript_is_pinned_and_visually_checked() -> None:
    data = manifest()
    assert data["official_pdf_recovered"] is True
    assert data["official_pages_visually_checked"] == 18
    assert data["official_source_recovered"] is False
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    opened = provenance["openreview"]
    assert opened["forum_id"] == "lNmZrawUMu"
    assert opened["venue"] == "ICLR 2026 Poster"
    assert opened["license"] == "CC BY 4.0"
    assert opened["official_pdf_sha256"] == audit.PINS[
        "discovery/openreview-current.pdf"
    ]
    visual = opened["visual_qa"]
    assert visual["pages_inspected"] == 18
    assert visual["unreadable_clipped_overlapping_blank_or_missing_pages"] == 0
    assert len(visual["contact_sheet_sha256"]) == 2


def test_every_table_result_unit_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 147
    assert Counter(row["table"] for row in results) == {
        table: count for table, (_, _, count) in audit.TABLES.items()
    }
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    assert manifest()["native_numeric_units_regenerated"] == 0


def test_figure_panels_and_exact_annotations_fail_closed() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 8
    assert sum(int(row["display_panels"]) for row in figures) == 30
    assert sum(int(row["empirical_panels"]) for row in figures) == 21
    assert sum(int(row["printed_numeric_annotations"]) for row in figures) == 40
    assert all(row["underlying_numeric_arrays_recovered"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    numeric = rows("figure_numeric_ledger.csv")
    assert len(numeric) == 40
    assert all(row["published_annotation_regenerated"] == "False" for row in numeric)
    assert all(row["paper_result_credit"] == "False" for row in numeric)
    assert manifest()["native_empirical_panels_regenerated"] == 0


def test_listed_supplement_is_not_misrepresented_as_inspected_or_absent() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    opened = provenance["openreview"]
    assert opened["supplement_listed"] is True
    assert opened["supplement_immutable_path"] == audit.SUPPLEMENT_PATH
    assert opened["supplement_recovered"] is False
    assert "immutable path 404" in opened["supplement_access_observation"]
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["supplement"]["status"] == "listed_but_currently_unrecoverable"
    assert methods["paper_specific_release"]["status"] == "missing"


def test_public_checkpoints_are_unattributed_and_task_incompatible() -> None:
    release = json.loads((AUDIT_DIR / "candidate_release_audit.json").read_text())
    assert release["native_paper_credit"] is False
    assert release["paper_author_identity_matches"] == 0
    assert [item["repository"] for item in release["candidates"]] == [
        "PuLam/alphaagentevo-v2-0.6B",
        "nguyenha0501/alphaagentevo-qwen3-4b-v2",
    ]
    assert all(item["native_paper_credit"] is False for item in release["candidates"])
    candidate = release["nguyenha_source"]
    assert candidate["dataset_rows"] == {"train": 300, "val": 30, "test": 99}
    assert candidate["paper_dataset_rows"] == {"train": 350, "val": 50, "test": 100}
    assert candidate["prompt_market"] == "Vietnam stock market"
    assert candidate["paper_five_component_reward_active"] is False
    assert candidate["python_files_parsed"] == 11
    assert "private, deleted, or unindexed" in release["bounded_negative_inference"]


def test_third_party_training_log_is_a_failed_partial_run_not_paper_evidence() -> None:
    release = json.loads((AUDIT_DIR / "candidate_release_audit.json").read_text())
    candidate = release["nguyenha_source"]
    assert candidate["training_gpus"] == 4
    assert candidate["requested_steps"] == 150
    assert candidate["completed_unique_steps"] == 90
    assert candidate["last_completed_step"] == 90
    assert candidate["checkpoint_steps"] == list(range(10, 100, 10))
    assert candidate["reached_training_100_percent"] is False
    assert candidate["final_validation_emitted"] is False
    assert "1,800,000 ms" in candidate["termination"]
    assert candidate["successful_backtests_logged"] == 7004
    assert candidate["tool_call_numbers_above_declared_four"] == 545
    assert candidate["maximum_logged_call_number"] == 33
    rewards = candidate["validation_reward_mean_at_3"]
    assert rewards["80"] == 0.087
    assert rewards["90"] == -0.35


def test_method_and_internal_boundaries_are_explicit() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["dataset"]["status"] == "specified_not_released"
    assert methods["portfolio"]["status"] == "partially_specified"
    assert methods["reward"]["status"] == "equation_specified_with_ambiguity"
    assert methods["prompts_and_trajectories"]["status"] == "not_released"
    assert methods["published_results"]["status"] == "not_regenerated"
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["reward_denominator"]["status"] == "specification_ambiguity"
    assert checks["third_party_0_6b"]["status"] == "unattributable_task_mismatch"
    assert checks["third_party_4b"]["status"] == "unattributable_task_mismatch"


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned AlphaAgentEvo audit evidence is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_alphaagentevo_paper.py"),
         "--output", str(tmp_path / "strict"), "--strict"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert json.loads((tmp_path / "strict/manifest.json").read_text())[
        "full_end_to_end_pipeline_reproduced"
    ] is False


def test_manifest_hashes_every_output_and_readme_is_honest() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    readme = (AUDIT_DIR / "README.md").read_text()
    for marker in (
        "All 18 pages", "147 exact numeric units", "21", "40 exact numeric",
        "must not be represented\nas inspected", "Vietnam-market prompts",
        "step 90 of 150", "0/147 table units", "0/21", "0/40",
        "no AlphaAgentEvo mechanism or result credit",
    ):
        assert marker in readme
