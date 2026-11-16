import json
from alpha_evolve.alphabet_news_view_v2 import render_news_view, install_news_view


def test_preserves_every_financial_text_and_date_without_metadata():
    rows = [
        {
            "kind": "news_items",
            "date": "2024-01-02",
            "available_date": "2024-01-03",
            "text": "Alphabet’s revenue rose.\nFull details stay intact.",
            "source_sha256": "private-audit-hash",
            "method": "bookkeeping",
            "source_symbol": "GOOG",
        },
        {
            "kind": "news_items",
            "date": "2024-01-03",
            "available_date": "2024-01-04",
            "text": "Another full story, including all its words.",
            "source_sha256": "another-audit-hash",
        },
    ]
    raw = "Alternative dated FNSPID/FINSABER company news; no contemporaneous web access.\n" + json.dumps(rows)
    result = render_news_view(raw, "GOOGL")
    for row in rows:
        assert row["text"] in result
        assert row["date"] in result
        assert row["source_sha256"] not in result
    assert result.index(rows[0]["text"]) < result.index(rows[1]["text"])
    assert "GOOG news" in result and "GOOGL news" in result


def test_unavailable_responses_and_cutoff_traces_preserved():
    class Tools:
        symbol = "GOOGL"

        def call(self, name, kwargs):
            self.trace = kwargs
            return "Unavailable: no dated source"

    install_news_view(Tools)
    tools = Tools()
    assert tools.call("get_news", {"cutoff": "2024-01-02"}) == "Unavailable: no dated source"
    assert tools.trace == {"cutoff": "2024-01-02"}
