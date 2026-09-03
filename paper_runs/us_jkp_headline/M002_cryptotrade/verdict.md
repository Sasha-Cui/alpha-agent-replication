# M002: CryptoTrade common-task verdict

Status: **closed—not evaluable on the monthly U.S./JKP common task without inventing a new method**.

The central strategy is the full reflective LLM agent: on each daily single-crypto decision it calls an on-chain/technical analyst, news analyst, reflection analyst, and final trader, with recent performance memory and an asset-specific cash/holding state. The traditional indicators and LSTM are comparison baselines, not the proposed CryptoTrade strategy.

The fixed common task requires a formation-time score or portfolio for 1,000 U.S. securities over 305 months. A literal transfer would require 305,000 independent stateful decisions and 1,220,000 LLM calls. More importantly, JKP has no paper-defined stock equivalents for crypto transaction/network fields or point-in-time news text, and the source defines no way to combine 1,000 isolated accounts into one portfolio. Replacing these with arbitrary characteristics, historical crypto actions, an imitation classifier, or one batched prompt removes the method's defining observation and reflection loop.

Therefore no monthly return, zero return, or unfavorable-performance claim is recorded for M002. This does not show that the original crypto results are false. The existing audit separately preserves 174/180 deterministic baseline matches and 40 historical LLM-output correspondences, while also documenting the LSTM lookahead and incomplete/mislabelled LLM lineage. None of those is relabelled as the headline common-task strategy.

The recipe and effort record document the bounded routes considered and why each fails the attribution threshold. M002 is a legitimate non-evaluable closure, not a failed backtest. M003 is now active.
