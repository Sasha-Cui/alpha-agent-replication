from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_guruagents_openrouter_replay.py"
SPEC = importlib.util.spec_from_file_location("guru_replay", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
guru_replay = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guru_replay
SPEC.loader.exec_module(guru_replay)


def test_extracts_exact_template_and_tool_descriptions(tmp_path: Path) -> None:
    source = tmp_path / "agent.py"
    source.write_text(
        '''template = "Exact system prompt"

class Agent:
    def __init__(self):
        self.tools = [
            Tool(name="metric_one", description="Exact description", func=self.one),
            Tool(name="metric_two", description="Second description", func=self.two),
        ]
''',
        encoding="utf-8",
    )
    prompt, tools = guru_replay.extract_prompt_and_tools(source)
    assert prompt == "Exact system prompt"
    assert [(tool.name, tool.description) for tool in tools] == [
        ("metric_one", "Exact description"),
        ("metric_two", "Second description"),
    ]


def test_archived_transcript_contains_all_observations() -> None:
    steps = [
        {"tool_name": "metric_one", "tool_input": "2024Q1", "observation": "[1]"},
        {"tool_name": "metric_two", "tool_input": "2024Q1", "observation": "[2]"},
    ]
    messages = guru_replay.archived_messages("system", "request", steps)
    assert [message["role"] for message in messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
        "tool",
    ]
    assert messages[3]["content"] == "[1]"
    assert messages[5]["name"] == "metric_two"


def test_parser_and_fidelity_metrics() -> None:
    text = """
| Ticker | Score | Weight (%) | Reason |
|---|---:|---:|---|
| AAA | 1.00 | 60 | strongest |
| BBB | 0.50 | 40% | second |
"""
    replayed = guru_replay.parse_portfolio(text)
    archived = [
        {"Ticker": "AAA", "Score": 1.0, "Weight (%)": 55.0, "Reason": "x"},
        {"Ticker": "CCC", "Score": 0.5, "Weight (%)": 45.0, "Reason": "y"},
    ]
    comparison = guru_replay.compare_portfolios(replayed, archived)
    assert comparison["ticker_jaccard"] == pytest.approx(1 / 3)
    assert comparison["weight_l1_percentage_points"] == pytest.approx(90.0)
    assert comparison["replayed_weight_sum"] == pytest.approx(100.0)


def test_budget_rejects_concurrent_overcommitment() -> None:
    ledger = guru_replay.BudgetLedger(1.0)
    reservation = ledger.reserve(0.7)
    with pytest.raises(guru_replay.BudgetExceeded):
        ledger.reserve(0.4)
    ledger.settle(reservation, 0.5)
    assert ledger.snapshot()["remaining_usd"] == pytest.approx(0.5)


def test_discovers_public_archive_cells_and_counts(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "nasdaq100_bs_cf_is.csv").write_text(
        "QUARTER,TICKERSYMBOL\n2024Q1,AAA\n2024Q1,BBB\n2023Q1,AAA\n",
        encoding="utf-8",
    )
    directory = tmp_path / "results" / "altman_agent"
    directory.mkdir(parents=True)
    (directory / "altman_analysis_2024-01-01_2024-03-31.json").write_text(
        json.dumps(
            {
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "intermediate_steps": [
                    {
                        "tool_name": "metric_altman",
                        "tool_input": "2024Q1",
                        "observation": "[]",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (directory / "altman_portfolio_2024-01-01_2024-03-31.csv").write_text(
        "Ticker,Score,Weight (%),Reason\nAAA,1.0,100,test\n",
        encoding="utf-8",
    )
    cells = guru_replay.discover_cells(tmp_path, ["results"], ["altman"])
    assert len(cells) == 1
    assert cells[0].quarter == "2024Q1"
    assert cells[0].available_tickers == 2
    assert cells[0].historical_comparison is True


def test_archived_portfolio_skips_blank_ticker_remainder_row(tmp_path: Path) -> None:
    path = tmp_path / "portfolio.csv"
    path.write_text(
        "Ticker,Score,Weight (%),Reason\nAAA,1.0,90,holding\n,,10,Remaining allocation.\n",
        encoding="utf-8",
    )
    rows = guru_replay.archived_portfolio(path)
    assert [row["Ticker"] for row in rows] == ["AAA"]
