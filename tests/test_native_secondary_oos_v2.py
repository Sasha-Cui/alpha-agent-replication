"""Prevent selection, baseline substitution and silent factor loss in secondary panels."""

import copy
import importlib.util
import json
from pathlib import Path
import pytest

PATH = Path(__file__).parents[1] / "scripts/native_secondary_evidence_v2.py"
SPEC = importlib.util.spec_from_file_location("secondary_evidence", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture(tmp_path):
    run = tmp_path / "quantaalpha_bounded"
    run.mkdir()
    source = {
        "experiments": [{"index": 0}, {"index": 1}],
        "programs": [
            {"sha256": "a", "uses": [{"experiment_index": 0}]},
            {"sha256": "b", "uses": [{"experiment_index": 0}, {"experiment_index": 1}]},
            {"sha256": "c", "uses": [{"experiment_index": 1}]},
        ],
    }
    path = run / "used_factor_manifest.json"
    path.write_text(json.dumps(source))
    return {
        "case": "quantaalpha",
        "source_manifests": {"quantaalpha_bounded": MODULE.sha256(path)},
        "experiment_index_filter": 0,
        "programs": [{"code_sha256": "a"}, {"code_sha256": "b"}],
    }


def test_task_library_retains_all_and_only_used_programs(tmp_path):
    lib = fixture(tmp_path)
    MODULE.require_secondary_library("quantaalpha", lib, 0, tmp_path)
    for changed in (
        [{"code_sha256": "a"}],
        [{"code_sha256": "a"}, {"code_sha256": "b"}, {"code_sha256": "c"}],
        [{"code_sha256": "a"}, {"code_sha256": "a"}, {"code_sha256": "b"}],
    ):
        bad = copy.deepcopy(lib)
        bad["programs"] = changed
        with pytest.raises(ValueError, match="drops or substitutes"):
            MODULE.require_secondary_library("quantaalpha", bad, 0, tmp_path)


def test_different_task_or_trial_cannot_reuse_a_good_manifest(tmp_path):
    lib = fixture(tmp_path)
    with pytest.raises(ValueError, match="filter changed"):
        MODULE.require_secondary_library("quantaalpha", lib, 1, tmp_path)
    with pytest.raises(ValueError, match="Unplanned"):
        MODULE.require_secondary_library("quantaalpha", lib, 7, tmp_path)
    lib["source_manifests"] = {"quantaalpha_paper_parameters": "a"}
    with pytest.raises(ValueError, match="substituted"):
        MODULE.require_secondary_library("quantaalpha", lib, 0, tmp_path)


def test_incomplete_success_only_and_duplicate_panels_refused():
    MODULE.require_complete_panel("quantaalpha", list(range(7)))
    MODULE.require_complete_panel("alphaagent", list(range(1, 21)))
    for case, units in [
        ("quantaalpha", list(range(6))),
        ("quantaalpha", [0, 1, 2, 3, 4, 5, 5]),
        ("alphaagent", list(range(1, 20))),
    ]:
        with pytest.raises(ValueError, match="Incomplete"):
            MODULE.require_complete_panel(case, units)


def test_reused_baseline_binds_exact_parent_columns():
    row = {"code_sha256": "a", "data_sha256": "d", "output_sha256": "o", "expression": "factor"}
    parent = {"case": "quantaalpha", "data_sha256": "d", "membership_sha256": "m", "programs": [row]}
    lib = {**copy.deepcopy(parent), "reused_program_library_manifest_sha256": "p"}
    MODULE.require_parent_subset(lib, parent, "p")
    for key, value in [("reused_program_library_manifest_sha256", "different"), ("membership_sha256", "newuniverse")]:
        bad = copy.deepcopy(lib)
        bad[key] = value
        with pytest.raises(ValueError):
            MODULE.require_parent_subset(bad, parent, "p")
    bad = copy.deepcopy(lib)
    bad["programs"][0]["output_sha256"] = "newvalues"
    with pytest.raises(ValueError, match="columns"):
        MODULE.require_parent_subset(bad, parent, "p")


def test_failed_attempted_alpha_round_is_preserved(tmp_path):
    name = "alphaagent_rounds_paper_gpt35_02"
    run = tmp_path / name
    run.mkdir()
    manifest = run / "used_factor_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "experiments": [{"index": 0, "within_first_five_rounds": True}],
                "programs": [{"sha256": "a", "uses": [{"experiment_index": 0}]}],
            }
        )
    )
    done = run / "execution_exit.json"
    done.write_text(
        json.dumps({"status": "native_round_budget_exhausted", "attempted_rounds": 5, "failed_round_indices": [3]})
    )
    lib = {
        "case": "alphaagent",
        "source_manifests": {name: MODULE.sha256(manifest)},
        "experiment_index_filter": None,
        "programs": [{"code_sha256": "a"}],
    }
    MODULE.require_secondary_library("alphaagent", lib, 2, tmp_path)
    done.write_text(json.dumps({"status": "native_round_budget_exhausted", "attempted_rounds": 4}))
    with pytest.raises(ValueError, match="five attempted"):
        MODULE.require_secondary_library("alphaagent", lib, 2, tmp_path)


def test_opening_execution_cannot_use_a_different_prediction(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    original = source / "execution_recipe.json"
    original.write_text("{}")
    out = tmp_path / "source_open_information"
    out.mkdir()
    recipe = {
        "execution_sensitivity": "opening_information_limit_proxy",
        "source_run": "source",
        "source_execution_recipe_sha256": MODULE.sha256(original),
    }
    for name, key in [("pred.pkl", "source_prediction_sha256"), ("label.pkl", "source_label_sha256")]:
        for folder in (source, out):
            p = folder / "mlruns/1/2/artifacts" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"fixed")
        recipe[key] = MODULE.sha256(p)
    (out / "execution_recipe.json").write_text(json.dumps(recipe))
    (out / "completion.json").write_text(
        json.dumps({"predictions_byte_identical": True, "retrained": False, "new_model_calls": 0})
    )
    MODULE.validate_execution_identity("source_open_information", "opening_information", tmp_path)
    (out / "mlruns/1/2/artifacts/pred.pkl").write_bytes(b"changed")
    with pytest.raises(ValueError, match="prediction/label"):
        MODULE.validate_execution_identity("source_open_information", "opening_information", tmp_path)
    with pytest.raises(ValueError, match="cannot stand in"):
        MODULE.validate_execution_identity("source", "opening_information", tmp_path)
