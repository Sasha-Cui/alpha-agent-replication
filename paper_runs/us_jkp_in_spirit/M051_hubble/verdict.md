# M051: Hubble in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not Hubble's intentionally withheld native top-five formulas.

The reconstruction preserves safe DSL generation, AST-style complexity limits, positive and negative retrieval guidance, three feedback rounds, RankIC/Pearson/long-short/turnover/coverage/complexity scoring, similarity control, and a two-per-family cap. It deterministically evaluated 204 candidates on pre-common data and selected price_trend__identity__ret_12_1; price_volume_interaction__pair_product__ret_6_1__turnover_126d; price_trend__identity__resff3_12_1; price_volume_interaction__identity__dolvol_var_126d; range__pair_product__prc_highprc_252d__rmax5_21d; selected family counts were {'price_trend': 2, 'price_volume_interaction': 2, 'range': 1}.

At 10 bp one-way costs, the 305-month path has CAGR 8.61%, annualized Sharpe 0.481, and maximum drawdown -54.08%. Mean monthly traded notional is 1.990, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is 0.80% annually (HAC t=0.386, p=0.6995, 95% interval [-3.24%, 4.83%]).

This result answers how one transparent Hubble-inspired safe and diverse factor search transfers to the common monthly U.S. universe. It does not reproduce the hidden formulas, LLM/RAG calls, daily OHLCV executor, or native OOS claims. Common-period returns were not used in search.
