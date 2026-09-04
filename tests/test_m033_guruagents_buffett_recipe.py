from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M033_guruagents_buffett"
SCRIPT = ROOT / "scripts/run_guruagents_buffett_milestone.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("guruagents_buffett_milestone", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_recipe_pins_the_paper_highlighted_buffett_source_formula():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    prompt_audit = pd.read_csv(
        ROOT / "paper_runs/paper_replication_audits/guruagents/source_prompt_conformance.csv"
    )
    buffett = prompt_audit.loc[prompt_audit.agent.eq("Warren Buffett")].iloc[0]
    assert recipe["status"] == "frozen_for_execution"
    assert recipe["canonical_work_id"] == "CensusArxiv251001664"
    assert recipe["source_commit"] == "74ad2e6ce2e604c73a6fc2829d48ab58fe6be050"
    assert recipe["source_prompt_sha256"] == "d720f8f10ee5583e8a793614d123ae6f4bd61d9f33963931f8fcc567246982f5"
    assert recipe["source_prompt_sha256"] == buffett.source_prompt_sha256
    assert "42.2% CAGR" in recipe["headline_selection_basis"]
    assert len(recipe["jkp_input_mapping"]) == 14
    assert [row["metric"] for row in recipe["intentionally_missing_source_metrics"]] == [
        "MarginStability", "BuybackYield"
    ]


def test_winsorized_minmax_obeys_no_spread_and_tail_rules():
    flat = pd.Series([3.0, 3.0, np.nan])
    assert MODULE.winsorized_minmax(flat).tolist()[:2] == [0.5, 0.5]
    values = pd.Series([-100.0, 0.0, 1.0, 2.0, 100.0])
    scaled = MODULE.winsorized_minmax(values)
    assert scaled.iloc[0] == 0.0
    assert scaled.iloc[-1] == 1.0
    assert scaled.between(0, 1).all()


def test_weighted_available_renormalizes_per_ticker():
    values = pd.DataFrame({"a": [1.0, np.nan], "b": [0.0, 0.25]})
    result = MODULE.weighted_available(values, {"a": 0.75, "b": 0.25}, total_weight=1.0)
    assert np.allclose(result, [0.75, 0.25])


def test_buffett_components_use_only_frozen_formation_inputs():
    frame = pd.DataFrame(
        {
            "at_be": [2.0, 3.0, 4.0],
            "ebit_int": [12.0, 7.0, 3.0],
            "ni_be": [0.20, 0.10, -0.05],
            "ni_sale": [0.18, 0.08, -0.02],
            "at_turnover": [1.0, 0.8, 0.5],
            "be_me": [0.5, 0.4, 0.3],
            "ni_me": [0.08, 0.04, -0.01],
            "fcf_me": [0.07, 0.02, -0.02],
            "ca_cl": [2.0, 1.5, 1.2],
            "nwc_at": [0.20, 0.10, 0.04],
            "ocf_me": [0.10, 0.04, -0.01],
            "capx_at": [0.03, 0.04, 0.02],
            "at_me": [1.0, 1.2, 1.5],
            "ebit_at": [0.15, 0.10, 0.02],
            "tax_pi": [0.21, 0.20, 0.10],
            "cash_at": [0.10, 0.08, 0.05],
            "ret_exc_lead1m": [99.0, -99.0, 99.0],
        }
    )
    first = MODULE.buffett_components(frame)
    changed = frame.copy()
    changed["ret_exc_lead1m"] *= -10
    second = MODULE.buffett_components(changed)
    assert np.allclose(first["score"], second["score"], equal_nan=True)
    assert first["score"].between(0, 1).all()
    assert np.isclose(first.loc[0, "owner_earnings_yield"], 0.082)


def test_score_proportional_weights_are_long_only_and_ignore_future_coverage():
    frame = pd.DataFrame(
        {
            "security_id": ["A", "B", "C"],
            "score": [0.2, 0.3, 0.5],
            "ret_exc_lead1m": [np.nan, 0.1, -0.2],
        }
    )
    weights = MODULE.score_proportional_weights(frame)
    assert np.allclose(weights.sort_index(), [0.2, 0.3, 0.5])
    assert weights.sum() == 1.0
    assert (weights > 0).all()
