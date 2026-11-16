"""Missing dates and changed economic settings must not become feature effects."""

import importlib.util
from pathlib import Path
import copy
import pandas as pd
import pytest

PATH = Path(__file__).parents[1] / "scripts/analyze_native_oos_v2.py"
SPEC = importlib.util.spec_from_file_location("native_oos_analysis", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def config():
    loader = {
        "class": "qlib.contrib.data.loader.QlibDataLoader",
        "kwargs": {"config": {"feature": ["$close"], "label": ["future_label"]}},
    }
    handler = {"data_loader": loader, "start_time": "2015-01-01"}
    return {
        "task": {
            "model": {"class": "LGBModel"},
            "dataset": {"kwargs": {"handler": {"kwargs": handler}, "segments": {"train": ["2015", "2019"]}}},
        },
        "data_handler_config": handler,
        "port_analysis_config": {"backtest": {"account": 100000000, "exchange_kwargs": {"open_cost": 0.0005}}},
    }


def test_feature_intervention_only():
    base = config()
    other = copy.deepcopy(base)
    original = other["task"]["dataset"]["kwargs"]["handler"]["kwargs"]["data_loader"]
    original["kwargs"]["config"]["feature"] = ["$volume", "$vwap"]
    other["task"]["dataset"]["kwargs"]["handler"]["kwargs"]["data_loader"] = {
        "class": "NestedDataLoader",
        "kwargs": {
            "dataloader_l": [
                original,
                {"class": "qlib.data.dataset.loader.StaticDataLoader", "kwargs": {"config": "fixed.pkl"}},
            ]
        },
    }
    assert MODULE.core_settings(base) == MODULE.core_settings(other)
    other["port_analysis_config"]["backtest"]["exchange_kwargs"]["open_cost"] = 0
    assert MODULE.core_settings(base) != MODULE.core_settings(other)


def test_training_or_label_change_is_not_a_feature_change():
    base = config()
    other = copy.deepcopy(base)
    other["task"]["dataset"]["kwargs"]["segments"]["train"][1] = "2025"
    assert MODULE.core_settings(base) != MODULE.core_settings(other)
    other = copy.deepcopy(base)
    other["task"]["dataset"]["kwargs"]["handler"]["kwargs"]["data_loader"]["kwargs"]["config"]["label"] = [
        "different_future_label"
    ]
    assert MODULE.core_settings(base) != MODULE.core_settings(other)


def test_no_calendar_intersection_and_no_incomplete_primary_trials():
    dates = pd.date_range("2025-01-06", periods=5)
    left = pd.Series([0.01] * 5, index=dates)
    right = pd.Series([0.0] * 4, index=dates[:-1])
    with pytest.raises(ValueError, match="silently intersect"):
        MODULE.aligned_difference(left, right)
    with pytest.raises(ValueError, match="incomplete or substituted"):
        MODULE.require_primary_library(
            "alphaagent", {"source_manifests": {"alphaagent_rounds_paper_gpt35_01": "digest"}}
        )


def test_primary_library_cannot_silently_drop_a_used_program(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(MODULE, "PRIVATE", tmp_path)
    folder = tmp_path / "quantaalpha_bounded"
    folder.mkdir()
    manifest = folder / "used_factor_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "experiments": [{"index": 0}, {"index": 1}],
                "programs": [
                    {"sha256": "a", "uses": [{"experiment_index": 0}]},
                    {"sha256": "b", "uses": [{"experiment_index": 1}]},
                ],
            }
        )
    )
    library = {"source_manifests": {"quantaalpha_bounded": MODULE.sha256(manifest)}, "programs": [{"code_sha256": "a"}]}
    with pytest.raises(ValueError, match="drops or substitutes"):
        MODULE.require_primary_library("quantaalpha", library)
    library["programs"].append({"code_sha256": "b"})
    MODULE.require_primary_library("quantaalpha", library)
    library["experiment_index_filter"] = 0
    with pytest.raises(ValueError, match="individual-task library"):
        MODULE.require_primary_library("quantaalpha", library)
