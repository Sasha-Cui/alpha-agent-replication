"""Descriptive repair comparisons require the same complete market path."""

import importlib.util
from pathlib import Path
import copy
import pandas as pd
import pytest

SPEC = importlib.util.spec_from_file_location(
    "ta_news_account", Path(__file__).parents[1] / "scripts/build_tradingagents_news_accounts_v2.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture():
    price = pd.Series([100.0, 101.0, 102.0], index=["2024-01-02", "2024-01-03", "2024-01-04"])
    records = [
        {
            "date": d,
            "native": "BUY",
            "tool_trace": [{"driver_cutoff": d, "effective_cutoff": d, "latest_input_date": d}],
        }
        for d in price.index
    ]
    return price, records


def test_missing_or_reordered_days_cannot_be_intersected():
    price, records = fixture()
    MODULE.require_calendar_and_cutoffs(records, price, price.index[0], price.index[-1])
    for wrong in (records[:-1], records[::-1], records + [records[-1]]):
        with pytest.raises(ValueError, match="calendar"):
            MODULE.require_calendar_and_cutoffs(wrong, price, price.index[0], price.index[-1])


def test_future_tool_text_is_refused():
    price, records = fixture()
    records[0]["tool_trace"][0]["latest_input_date"] = "2024-01-03"
    with pytest.raises(ValueError, match="Future tool input"):
        MODULE.require_calendar_and_cutoffs(records, price, price.index[0], price.index[-1])


def test_news_pair_cannot_hide_model_or_price_changes():
    price, _ = fixture()
    recipe = {
        k: "same"
        for k in [
            "source_commit",
            "symbol",
            "start",
            "end",
            "model",
            "temperature",
            "max_completion_tokens",
            "economic_adapter",
            "controls",
        ]
    }
    a = {"prices": price, "recipe": recipe}
    b = copy.deepcopy(a)
    MODULE.require_pair(a, b)
    b["recipe"]["model"] = "different"
    with pytest.raises(ValueError, match="non-news"):
        MODULE.require_pair(a, b)
    b = copy.deepcopy(a)
    b["prices"].iloc[-1] += 1
    with pytest.raises(AssertionError):
        MODULE.require_pair(a, b)
