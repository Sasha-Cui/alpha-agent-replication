# M001: GPT-Signal EVC on monthly U.S./JKP data

Status: **completed adapted headline-signal evaluation**, not an original-paper or fresh-LLM reproduction.

The published EVC reciprocal formula is retained. Direction is negative EVC from the paper's signed correlation, fixed before this run. Inputs use JKP net income/assets, EBITDA/market enterprise value, and operating cash flow/market equity. Accounting conventions, U.S. universe, monthly cadence and the value-weighted decile portfolio are disclosed adaptations.

## Primary result: 10 bp one-way costs

- Full return path: 305 months, 1999-08-31 to 2024-12-31.
- Net CAGR: -1.44%; annualized Sharpe: -0.063; maximum drawdown: -58.42%.
- Mean monthly traded notional: 0.661; annualized linear cost drag: 0.79%.
- Common rolling-attribution window: 185 months, 2009-08-31 to 2024-12-31, after 120 training months with a 24-month inner validation block.
- JKP-derived 133-factor residual alpha: 2.97% per year; HAC t=1.360; two-sided p=0.1738; 95% interval [-1.31%, 7.26%].
- Conservative interim 69-test Bonferroni p: 1.0000. Final family inference awaits the remaining milestones.

This is a retrospective strategy-transfer result on data already used in prior project work. It is not proof of live alpha, fresh GPT generation, or the original paper's reported performance. The benchmark is a fixed JKP-derived market plus 132-characteristic construction; FF5/momentum analogues are members, not six additional factors. Slopes and ridge choice use only earlier months. The fit's intercept is not removed from realized residuals.

No sign, factor formula or hyperparameter was changed after viewing the result. Other costs and the adverse missing-return policy are diagnostics, not alternative candidates selected for better results. Gross-book turnover and linear fee drag follow the shared convention; borrow fees, market impact, historical data vintages and exact FactSet accounting definitions are not reproduced. Compounded growth is for the normalized long-short risk-capital book, with no collateral cash yield added.

Sources: [GPT-Signal](https://arxiv.org/html/2410.18448v1), Sections 4-5; [JKP data/code](https://github.com/bkelly-lab/jkp-data), associated with Jensen, Kelly and Pedersen (2023), *Is There a Replication Crisis in Finance?* The supplied dataset's noncommercial data-license conditions are retained.

## Reproducibility

`recipe.json`, `../benchmark_contract.json`, `../benchmark_preflight.json`, `monthly_returns.csv`, `primary_monthly_returns.csv`, `metrics.csv` and `attribution_residuals.csv` preserve the public audit trail. Security-level formations and holdings remain in the ignored private artifact directory named in `run_manifest.json`.

Runner: `python scripts/run_us_jkp_headline.py --run` (refuses to overwrite an existing completed run). Input and benchmark hashes are checked before evaluation. The fixed benchmark was built first using `--prepare`.
