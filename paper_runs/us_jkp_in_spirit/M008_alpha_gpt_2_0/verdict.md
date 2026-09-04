# M008: Alpha-GPT 2.0 in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native Alpha-GPT 2.0 replication.

The reconstruction executes the draft's three-stage research cycle. A fixed human instruction asks the mining stage for mean-reversion alphas; a 51-expression grammar selects five factors using only the preceding 60 RankIC histories; a ridge modeling stage combines them on the same past window; and an analysis stage halves conviction for the highest-risk 20% using volatility and distress. The unspecified agents, SOP prompts, model zoo, knowledge graph, and human conversations are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR -5.58%, annualized Sharpe -0.235, and maximum drawdown -88.45%. Mean monthly traded notional is 2.973, and minimum signal coverage is 822 stocks. The most frequently selected mined expressions are `product__prc_highprc_252d__resff3_6_1` (142 selections), `difference__ret_1_0__resff3_6_1` (117 selections), `difference__ret_1_0__prc_highprc_252d` (110 selections).

Across the 185-month rolling JKP attribution window, residual mean return is -12.06% annually (HAC t=-3.647, p=0.0003, 95% interval [-18.55%, -5.58%]).

This result answers how one transparent Alpha-GPT 2.0-inspired research cycle transfers to the common task. The source paper reports no empirical result, and this does not turn the reconstruction into evidence for its proposed private system.
