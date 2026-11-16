"""Full-text source-style news views; audit metadata remains in input artifacts."""

from __future__ import annotations
import json


def render_news_view(response, symbol):
    prefix, separator, body = response.partition("\n")
    if not separator or not prefix.startswith("Alternative dated FNSPID/FINSABER company news;"):
        return response
    rows = json.loads(body)
    if not rows:
        return response
    blocks = []
    for row in rows:
        if row["kind"] != "news_items" or not isinstance(row["text"], str):
            raise ValueError("Unexpected news item")
        blocks.append(f"### {row.get('source_symbol', symbol)} news ({row['date']})\n{row['text']}")
    return prefix + "\n" + "\n\n".join(blocks)


def install_news_view(tool_class):
    original = tool_class.call

    def call(self, name, kwargs):
        result = original(self, name, kwargs)
        return render_news_view(result, self.symbol) if "news" in name else result

    tool_class.call = call
