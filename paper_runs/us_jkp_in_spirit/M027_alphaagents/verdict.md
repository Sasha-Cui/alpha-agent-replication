# M027: AlphaAgents in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native GPT-4o/AutoGen AlphaAgents replication.

The reconstruction preserves separate fundamental, sentiment, and valuation specialists under the paper's direct risk-neutral profile. Every monthly stock begins with three role-specific JKP opinions. In each of two round-robin passes, every specialist retains 65% of its current view and incorporates 35% of the current peer median; a group assistant then consolidates the three post-debate views by median into BUY/SELL direction and confidence. Mean cross-sectional specialist disagreement fell from 69.55% before debate to 29.03% afterward. The recovered February 2024 ticker memberships are never used as inputs or backcast.

At 10 bp one-way costs, the 305-month path has CAGR 1.04%, annualized Sharpe 0.156, and maximum drawdown -65.58%. Mean monthly traded notional is 2.104, and minimum signal coverage is 832 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -2.40% annually (HAC t=-1.208, p=0.2270, 95% interval [-6.30%, 1.50%]).

This result answers how one transparent AlphaAgents-inspired specialist debate transfers to a repeatable monthly U.S. universe. It does not reproduce the paper's Bloomberg/filing inputs, GPT-4o conversations, human review, one-time technology portfolio, or native performance claims.
