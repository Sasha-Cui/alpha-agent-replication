from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M015_maci"
AUDIT = ROOT / "paper_runs/paper_replication_audits/maci"


def test_m015_closes_v1_v2_without_substituting_v3_or_new_finetune():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250100826"
    assert recipe["version_scope"].startswith("v1/v2 four-expert")
    assert recipe["paper_configuration"]["base_model"] == "gpt-4o-2024-08-06"
    assert recipe["paper_configuration"]["universe"] == "weekly CoinGecko top 30"
    assert recipe["recovered_component_credit"]["historical_training_messages"] == 962
    assert recipe["recovered_component_credit"]["distinct_training_images"] == 930
    assert recipe["recovered_component_credit"]["reconstructed_finetuning_records"] == 961
    assert len(recipe["missing_headline_objects"]) == 6
    assert len(recipe["source_conflicts"]) == 5
    assert len(recipe["rejected_substitutes"]) == 5


def test_m015_matches_finetuning_and_result_boundary():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    native = json.loads((AUDIT / "native_execution.json").read_text())
    assert manifest["v1_v2_deleted_fine_tuning_message_records_recovered"] == 962
    assert manifest["v1_v2_fine_tuning_unique_image_payloads_recovered"] == 930
    assert manifest["v1_v2_reconstructed_single_0510_records"] == 961
    assert manifest["v1_v2_native_fine_tuning_contract_file_create_calls"] == 1
    assert manifest["v1_v2_native_fine_tuning_contract_job_create_calls"] == 1
    assert manifest["v1_v2_native_fine_tuning_remote_job_created"] is False
    assert manifest["v1_v2_actual_fine_tuning_upload_job_checkpoint_recovered"] is False
    assert manifest["v1_v2_table_units_faithfully_regenerated"] == 0
    assert manifest["v1_v2_published_table_units"] == 321
    assert manifest["v1_published_plotted_result_units_regenerated"] == 0
    assert manifest["v1_published_plotted_result_units_author_output_verified"] == 21
    assert native["paper_runner_executed"] is False
    with (AUDIT / "method_specification_audit.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    checkpoint = next(row for row in rows if row["paper_version"] == "v1/v2" and row["dimension"] == "checkpoints")
    assert checkpoint["status"] == "missing"


def test_m015_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m015 = rows["M015"]
    assert m015["status"] == "closed_not_evaluable"
    assert m015["monthly_returns_path"] == m015["metrics_path"] == m015["run_manifest_path"] == ""
    assert m015["recipe_path"] and m015["verdict_path"] and m015["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 15
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 13
