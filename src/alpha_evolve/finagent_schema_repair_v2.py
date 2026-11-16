"""Lossless resolution of the released FinAgent prompt/parser key disagreement."""

from __future__ import annotations
import hashlib


def canonical_reflection(response):
    fields = response.get("reasoning")
    if not isinstance(fields, dict) or "long_term_reasoning" in fields or "long_term_reasonig" not in fields:
        return response, None
    value = fields["long_term_reasonig"]
    if not isinstance(value, str):
        raise ValueError("Ambiguous non-string source reflection alias")
    repaired = dict(response)
    repaired["reasoning"] = {
        ("long_term_reasoning" if key == "long_term_reasonig" else key): item for key, item in fields.items()
    }
    return repaired, {
        "source_key": "long_term_reasonig",
        "parser_key": "long_term_reasoning",
        "value_sha256": hashlib.sha256(value.encode()).hexdigest(),
        "text_changed": False,
    }


def install_schema_repair(output):
    from finagent.prompt.trading.low_level_reflection import LowLevelReflectionTrading
    from alpha_evolve.openrouter_budget import atomic_json

    original = LowLevelReflectionTrading.get_response_dict
    events = []

    def get_response(self, *args, **kwargs):
        response, html = original(self, *args, **kwargs)
        repaired, event = canonical_reflection(response)
        if event:
            provider = kwargs.get("provider")
            meter = getattr(provider, "meter", None)
            trace = getattr(meter, "request_trace", [])
            event["request_hash"] = next(
                (row["request_hash"] for row in reversed(trace) if row["endpoint"] == "chat/completions"), None
            )
            events.append(event)
            atomic_json(output / "schema_repair_events.json", events)
        return repaired, html

    LowLevelReflectionTrading.get_response_dict = get_response
