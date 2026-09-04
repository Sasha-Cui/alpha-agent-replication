# M035: Trade in Minutes common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy because neither an optimized TiMi bot nor its strategy-determining parameters are released**.

The original v2 paper and TeX source identify the headline object clearly. Four offline agents generate, adapt, program, simulate, reflect on, and hierarchically optimize a bot. The deployed bot filters liquid/volatile CME-futures and Binance-crypto pairs, then places a minute-level volatility grid of limit orders and progressively exits using a separate threshold vector. Original-paper pages for the agent chain, Algorithm 1, grid execution, implementation/models/markets, and transaction-cost appendix were text-checked and visually inspected.

The algorithm is not parameterized. The paper withholds its execution and lookback intervals, volume/volatility thresholds, allocation, price/quantity ladders, three scale coefficients, position divisor, profit/loss vector, generated bot, prompts, simulation feedback, optimization history, pair universe, frozen inputs, costs, orders, fills, and return arrays. Those are precisely the quantities that determine trades. Monthly JKP also cannot represent its intraday funding, maker-fee, order-book, and stop/exit state.

The official ICLR 2026 OpenReview record lists a supplementary ZIP, so it is not presumed absent. A 2026-09-04 recheck still reaches a browser-verification challenge/HTTP 403 at the logical attachment and HTTP 404 at the immutable ZIP path. Two later third-party implementations are unaffiliated and cannot establish TiMi lineage. The prior narrative JKP factor proxy is rejected because it does not execute Algorithm 1 or the optimization loop.

No monthly return is assigned. This is neither evidence that TiMi's positive claims are false nor a finding that it loses to JKP. The correct classification is unresolved/non-evaluable: 0/349 current empirical table units and 0/8 empirical figure panels are regenerated. Reopen M035 if the official supplement or an attributable implementation becomes accessible.
