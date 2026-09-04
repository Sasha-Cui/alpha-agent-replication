# M055: SHARP evolved rubric policy

Status: **closed not evaluable on monthly U.S./JKP data**.

SHARP is unusually rich in algorithmic detail. Its headline mechanism evolves a bounded, human-readable rubric by attributing the 20 worst portfolio days to rule-level failures, proposing at most three atomic edits per round, validating each candidate, and freezing the best rubric after five rounds. At inference, an LLM analyst applies that rubric to price, news, and macro context; predicted return times confidence supplies the score for a daily equal-weight dollar-neutral 5-long/5-short next-open portfolio.

Seven paper-derived mechanics execute correctly on deterministic fixtures: composite scoring, tail ranking, next-open timing, entry costs, reported metrics, validation gating, and rubric bounds. They are meaningful specification evidence but do not generate a security score. The six printed shared initial rules merely adjust an LLM's base news prediction, the paper conflicts over whether a seventh rule exists, and the claimed sector rules are unavailable. Representative evolved-rule diffs do not disclose any complete final rubric or its model/window assignment.

The paper provides no implementation URL. The sole cited dataset repository and its owner still return 404; fresh exact arXiv/title repository searches found nothing attributable, and the one current code hit for a distinctive rule name is unrelated. Missing artifacts include exact prompts and schemas, Yahoo/Finnhub snapshots, split dates, LLM calls, evolved rubrics, scores, trades, holdings, daily returns, and result generators.

JKP cannot replace the missing causal policy: inserting a generic momentum or news proxy as the base prediction would bypass SHARP's attribution-guided symbolic evolution. No return path is fabricated, and none of the paper's 210 table cells or empirical panel has been author-natively regenerated. This closure does not establish that the reported gains are false; it records that the central evolved score cannot be reconstructed from the public evidence.
