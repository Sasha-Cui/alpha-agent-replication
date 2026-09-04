# M004: FLAG-TRADER in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native FLAG-TRADER replication.

The reconstruction preserves the paper prompt's valuation, historical-trend, momentum, risk, and turnover semantics in a four-feature JKP state. A fixed semantic prior replaces the frozen language-model representation; separate linear actor and ridge critic heads update monthly from the preceding 60 months. The paper's learning rate, gradient cap, and proximal clip are retained, and 20% lagged action memory limits turnover. The unreleased SmolLM2 checkpoint, token policy, sampled Buy/Hold/Sell trajectory, and single-asset account environment are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR -2.44%, annualized Sharpe 0.034, and maximum drawdown -82.79%. Mean monthly traded notional is 1.685, and minimum signal coverage is 828 stocks. Final actor weights are be_me=0.555, ret_12_1=0.555, ret_1_0=0.277, rvol_21d=-0.555.

Across the 185-month rolling JKP attribution window, residual mean return is -2.91% annually (HAC t=-1.097, p=0.2727, 95% interval [-8.12%, 2.29%]).

This result answers how one transparent FLAG-TRADER-inspired actor/critic transfers to the common task. It does not reproduce or validate the paper's private checkpoint, action trajectories, six-asset returns, or model-comparison claims.
