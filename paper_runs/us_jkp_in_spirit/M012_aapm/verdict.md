# M012: AAPM in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native AAPM replication.

The reconstruction preserves separate stock-report, macro-report, manual-factor, and asset-embedding blocks; iterative report and note memory; historical pretraining; nonlinear hybrid interactions; and the paper's value-weighted decile portfolio. Numeric JKP states replace unavailable WSJ reports and BGE embeddings. A 23-feature hybrid state is fitted each month from only the preceding 120 formations. The private LLM reports, learned embedding table, deep network, and native predictions are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR -5.39%, annualized Sharpe -0.144, and maximum drawdown -90.25%. Mean monthly traded notional is 2.078, and minimum signal coverage is 653 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -6.37% annually (HAC t=-1.669, p=0.0952, 95% interval [-13.86%, 1.11%]).

This result answers how one transparent AAPM-inspired hybrid pricing model transfers to the common task. It does not reproduce or validate AAPM's LLM-agent outputs, trained model, asset-pricing errors, or native portfolio results.
