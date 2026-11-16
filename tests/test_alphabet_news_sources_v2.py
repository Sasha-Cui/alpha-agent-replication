from alpha_evolve.alphabet_news_sources_v2 import install_single_news_source


def test_distinct_vendor_is_unavailable_instead_of_copying_corpus():
    class Tools:
        cutoff = "2024-01-09"

        def __init__(self):
            self.trace = []

        def call(self, name, kwargs):
            self.trace.append({"tool": name, "arguments": kwargs})
            return "Every word of the frozen financial news"

    install_single_news_source(Tools)
    tool = Tools()
    assert tool.call("get_finnhub_news", {}) == "Every word of the frozen financial news"
    answer = tool.call("get_google_news", {"curr_date": "2024-01-09"})
    assert "Unavailable" in answer and "get_finnhub_news" in answer
    assert tool.trace[-1]["unavailable"] is True


def test_explicit_start_date_preserved_with_driver_cutoff():
    class Tools:
        cutoff = "2024-01-09"

        def __init__(self):
            self.trace = []

        def call(self, name, kwargs):
            self.trace.append({"arguments": kwargs})
            return kwargs["look_back_days"]

    install_single_news_source(Tools)
    tool = Tools()
    arguments = {"start_date": "2024-01-01", "end_date": "2024-01-20"}
    assert tool.call("get_finnhub_news", arguments) == 8
    assert tool.trace[-1]["arguments"] == arguments
    assert tool.trace[-1]["resolved_start_date"] == "2024-01-01"
