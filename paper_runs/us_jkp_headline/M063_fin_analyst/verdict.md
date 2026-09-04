# M063: Fin-Analyst hybrid live trading agent

Status: **closed not evaluable on monthly U.S./JKP data**.

Fin-Analyst's native strategy is a daily hybrid vote for two assets: TSLA and BTC. Asset-specific LLM specialists, static corpora, technical momentum, and sentiment/failure state feed BUY/HOLD/SELL decisions, which the organizer scores with 6-bp fees and 10-bp slippage. This is a substantive public implementation and unusually strong output lineage, but it is not a cross-sectional stock policy.

The audit recovers and exactly rescored 97 official decisions. Six with-fee/no-fee/buy-and-hold equity arrays and 24 scalar outputs agree with the pinned organizer scorer. Thirty-three of 119 printed cells regenerate through official-decision/error or deterministic baseline lineage. None is generated end to end from the native LLM policy, and the headline live return/alpha/Sharpe/win cells do not match current official decisions. Deterministic baseline rows also require asset-specific data endpoints that contradict the paper's common endpoint.

Historical TSLA/BTC actions cannot generate formation-date choices for the top 1,000 U.S. stocks or the 1999–2024 history. Extracting the momentum vote would substitute one ingredient/baseline for the hybrid system. JKP lacks the asset-specific prompts, text corpora, Fear & Greed/WSB inputs, model calls, and votes; spreading two-asset decisions or generic momentum across JKP names would fabricate actions.

No common-benchmark return is fabricated. This closure preserves the 33 genuinely regenerated paper cells as separate source evidence while recognizing that they do not identify a transferable monthly U.S. strategy. Reopen for a causal security-level recommendation generator or cross-sectional policy.
