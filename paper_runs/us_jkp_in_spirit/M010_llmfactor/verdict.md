# M010: LLMFactor in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native LLMFactor replication.

The reconstruction preserves LLMFactor's sequence: identify one related stock, select exactly five price-relevant factors, append five prior rose/fall-equivalent price movements, and produce a binary-direction margin. A formation-time nearest peer replaces news company matching; eight JKP characteristics replace extracted news factors; and a rolling ridge classifier replaces the LLM request and parser. Every factor selection and fitted prediction uses only the preceding 60 formations. The unavailable news, prompts, responses, and natural-language explanations are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR -8.13%, annualized Sharpe -0.264, and maximum drawdown -91.73%. Mean monthly traded notional is 2.892, and minimum signal coverage is 620 stocks. The most frequently selected factors are `rmax5_21d` (259 selections), `ret_1_0` (225 selections), `o_score` (224 selections).

Across the 185-month rolling JKP attribution window, residual mean return is -5.55% annually (HAC t=-1.711, p=0.0871, 95% interval [-11.91%, 0.81%]).

This result answers how one transparent LLMFactor-inspired sequential predictor transfers to the common task. It does not reproduce or validate the paper's 82 native classification cells, generated rationales, or original empirical claims.
