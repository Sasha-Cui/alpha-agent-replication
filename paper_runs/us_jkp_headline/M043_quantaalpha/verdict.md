# M043: QuantaAlpha historical complete GPT pool on monthly U.S./JKP data

Status: **completed central partial adaptation**, not a reproduction of the v3 GPT-5.2 headline run.

The paper's central strategy is a LightGBM synthesis of roughly 150 evolved factors with a Top-50/drop-5 portfolio, rather than one cherry-picked expression. The strongest executable author-attributed artifact is an earlier 150-expression GPT pool which the released profile combines with Alpha158(20), for 170 features. All expressions and source signs are retained; no factor was selected using this JKP outcome. The v3 pool is not released, so this is necessarily a historical-pool partial.

The fixed monthly adaptation retains every source lookback count as monthly observations, maps JKP OHLCV fields as recorded in `recipe.json`, trains the released LightGBM configuration once on the first 60 formation months with the next 12 months used only for early stopping, and applies the source TopkDropout mechanism thereafter. The first 72 months are explicit cash warmup. Primary returns are the long-only portfolio's excess return over the common JKP top-1,000 market, net of the common 10 bp one-way linear cost.

At 10 bp one-way costs, the 305-month path has CAGR 1.38%, annualized Sharpe 0.186, and maximum drawdown -37.34%. There are 233 scored out-of-sample months after 72 cash months. The 185-month rolling JKP133 residual mean is 1.80% annually (HAC t=0.847, p=0.3972; descriptive 69-test bound=1.0000).

This directly answers option **B** for the implemented historical pool if its transferred return is weak: the source formulas/model/portfolio were run, but that does not make the unavailable v3 claim true or false. The native CSI300 rerun already produces 3.61% ARR rather than the older 27.75% claim, while v3 silently changes the headline to 4.68% without releasing its pool. The monthly U.S. result therefore evaluates transfer of the strongest released central partial, not the unreleased current headline.

Monthly bars cannot preserve next-day opening execution or Chinese price limits. The opening field is a prior-close-implied proxy, periods change from days to months, the primary common cost is symmetric rather than the paper's 5/15 bp schedule, and prior project outcomes were known. Results are exploratory and were not used to revise the frozen recipe.
