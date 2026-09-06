# M065: FactorMAD in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native FactorMAD GPT-4o debates, factor code, or A-share model.

The reconstruction preserves two differently initialized agents, alternating proposal and critique, existing/generated seed branches, ten debate rounds, validator/corrector intervention, predictive and correlation gates, 100 accepted interpretable factors, and a frozen linear prediction model. It required 100 episodes, corrected 0 factors, used seed sources {'generated_factor': 51, 'existing_factor': 49}, and accepted complexity counts {'1': 5, '2': 95}. All debate feedback and model fitting used only the 120 pre-common training months.

At 10 bp one-way costs, the 305-month path has CAGR 7.15%, annualized Sharpe 0.446, and maximum drawdown -47.39%. Mean monthly traded notional is 2.361, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is 3.86% annually (HAC t=1.528, p=0.1265, 95% interval [-1.09%, 8.80%]).

This result answers how one transparent FactorMAD-inspired debate pipeline transfers to the common monthly U.S. universe. It does not reproduce the A-share panel, native prompts, GPT-4o responses, generated Python, validator traces, LR/MLP/LightGBM artifacts, overlapping Top-50 sleeves, or paper empirical claims.
