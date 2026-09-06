# M063: Fin-Analyst in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native Fin-Analyst gpt-4o-mini or TSLA action path.

The reconstruction preserves the paper's TSLA branch: eight source-specific specialists, action/confidence records, a high-confidence news override, five-specialist consensus, recency-weighted resolution, and split-panel HOLD behavior. Across 305,000 security-months, resolution counts were {'news_override': 31393, 'majority_buy': 57662, 'majority_sell': 58403, 'weighted': 157542} and final action counts were {'buy': 106549, 'hold': 88535, 'sell': 109916}. The fixed hierarchy uses no historical paper action or current forward return.

At 10 bp one-way costs, the 305-month path has CAGR 0.05%, annualized Sharpe 0.082, and maximum drawdown -63.08%. Mean monthly traded notional is 2.027, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -1.41% annually (HAC t=-0.657, p=0.5115, 95% interval [-5.63%, 2.80%]).

This result answers how one transparent Fin-Analyst-inspired specialist hierarchy transfers to the common monthly U.S. universe. It does not reproduce paper-time model calls, corpora, cached verdicts, specialist reasoning, the BTC branch, native TSLA actions, organizer execution, or paper empirical claims.
