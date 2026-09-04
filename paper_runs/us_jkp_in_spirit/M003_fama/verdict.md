# M003: FAMA in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native FAMA replication.

The reconstruction preserves FAMA's price/volume symbolic-factor domain, RankIC objective, seven correlation-diversity groups, two cross-samples, and RankICIR-ordered experience selection. Six available JKP characteristics seed a fixed 51-expression arithmetic grammar. Every month, only the preceding 60 realized RankIC observations select and orient two representatives; their cross-sectional ranks form the common score. The unreleased text-davinci-002 generator, original 38-factor set, paper data, and private experience chains are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR -0.59%, annualized Sharpe 0.047, and maximum drawdown -63.41%. Mean monthly traded notional is 2.909, and minimum signal coverage is 847 stocks. The most frequent first experience representatives are `product__prc_highprc_252d__turnover_126d` (123 months), `product__prc_highprc_252d__rvol_21d` (95 months), `mean__ret_1_0__rvol_21d` (22 months).

Across the 185-month rolling JKP attribution window, residual mean return is -0.36% annually (HAC t=-0.099, p=0.9208, 95% interval [-7.39%, 6.67%]).

This result answers how one transparent FAMA-inspired search transfers to the common task. It does not reproduce or validate the paper's private factors, 38.4% return, RankIC, RankICIR, or model comparison claims.
