# M042: Alpha-R1 in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native Alpha-R1 Qwen3-8B/GRPO strategy.

The reconstruction preserves a fixed 40-factor zoo, four-year historical linear betas, factor-performance profiles, market memory, contemporaneous price and earnings-news state, context-conditioned sparse activation, group-relative scoring, and ten selected factors. It replaces the unreleased semantic LLM with a causal numerical gate: 60 purged months train each factor's state-to-RankIC profile, fixed economic family affinities supply a semantic prior, and their equally weighted group-relative scores choose ten factors. Across the path, 40 factors were activated at least once; the five most frequent were rmax1_21d (120 months), chcsho_12m (114 months), rmax5_21d (107 months), rvol_21d (105 months), eqnetis_at (104 months). Mean selected gate score was 0.538 and mean absolute selected beta was 0.00275.

At 10 bp one-way costs, the 305-month path has CAGR -4.71%, annualized Sharpe -0.138, and maximum drawdown -87.47%. Mean monthly traded notional is 2.768, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -9.32% annually (HAC t=-2.412, p=0.0158, 95% interval [-16.88%, -1.75%]).

This result answers how one transparent Alpha-R1-inspired contextual factor gate transfers to the common monthly U.S. universe. The official repository still contains only a README promising future code and weights. The reconstruction does not reproduce Qwen3-8B reasoning, GRPO optimization, Alpha101 definitions, Chinese price/news state, daily top-10 rotating slots, VWAP fills, or the paper's native claims; the old favorable five-factor motif was explicitly excluded.
