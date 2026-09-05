# M028: TreEvo in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native Qwen/TreEvo replication.

The reconstruction preserves a population of ten hierarchical factor trees, exactly 200 candidate evaluations, rotating crossover/mutation/pruning generations, scoped root/internal/fine mutation, parent-plus-offspring survival, and parsimony. All search fitness uses 96 pre-common months ending June 1997; the final population is selected on 24 subsequent validation months ending June 1999. The chosen tree is `mean(mean(product(ret_6_1,rvol_21d),ret_1_0),difference(ret_6_1,ret_12_1))` with 9 nodes, training-oriented RankIC -0.0558, and validation RankIC 0.0636. 2 degenerate candidate evaluations were assigned fail-closed fitness and could not win.

At 10 bp one-way costs, the 305-month path has CAGR 0.65%, annualized Sharpe 0.124, and maximum drawdown -66.22%. Mean monthly traded notional is 2.733, and minimum signal coverage is 844 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -4.04% annually (HAC t=-1.218, p=0.2231, 95% interval [-10.55%, 2.46%]).

This result answers how one transparent TreEvo-inspired hierarchical search transfers to the common monthly U.S. universe. It does not reproduce the paper's LLM-generated thoughts, thought-to-code prompts, daily Top-50/Drop-5 portfolio, or native market results.
