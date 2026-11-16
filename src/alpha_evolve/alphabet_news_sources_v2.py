"""One frozen company-news corpus must not masquerade as independent vendors."""

from __future__ import annotations


def install_single_news_source(tool_class):
    original = tool_class.call

    def call(self, name, kwargs):
        if name in ["get_google_news", "get_global_news_openai"]:
            cutoff = min(str(kwargs.get("curr_date", kwargs.get("end_date", self.cutoff))), self.cutoff)
            self.trace.append(
                {
                    "tool": name,
                    "arguments": kwargs,
                    "driver_cutoff": self.cutoff,
                    "effective_cutoff": cutoff,
                    "unavailable": True,
                    "reason": "No independent dated Google/global news snapshot; one frozen company corpus is available through get_finnhub_news.",
                }
            )
            return (
                "Unavailable: there is no independent dated Google/global-news snapshot in this case. "
                "The complete frozen issuer-news corpus is available through get_finnhub_news. "
                "If that tool already returned it in this analysis, use that full response; another vendor label would only duplicate the same articles."
            )
        if name == "get_finnhub_news" and "start_date" in kwargs:
            from datetime import date

            cutoff = min(str(kwargs.get("end_date", kwargs.get("curr_date", self.cutoff))), self.cutoff)
            lower = str(kwargs["start_date"])
            if lower > cutoff:
                self.trace.append(
                    {
                        "tool": name,
                        "arguments": kwargs,
                        "driver_cutoff": self.cutoff,
                        "effective_cutoff": cutoff,
                        "unavailable": True,
                        "reason": "Start date follows effective cutoff",
                    }
                )
                return "Unavailable: the requested start date follows the effective decision cutoff."
            adapted = {**kwargs, "look_back_days": (date.fromisoformat(cutoff) - date.fromisoformat(lower)).days}
            result = original(self, name, adapted)
            record = next(row for row in self.trace if row.get("arguments") is adapted)
            record["arguments"] = kwargs
            record["resolved_start_date"] = lower
            return result
        return original(self, name, kwargs)

    tool_class.call = call
