# QuantEvolver JKP benchmark status

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/QuantEvolver`

Scope constraint: all candidate and benchmark returns here were built only from read-only USA/JKP inputs:

- `${ALPHA_EVOLVE_JKP_ROOT}/data/processed/characteristics/USA.parquet`
- no native QuantEvolver market data or paper-supplied returns were used.

QuantEvolver ships a framework and example seed candidates, but no dated portfolio return stream. I mapped its three valid shipped seed ideas to monthly JKP USA proxies and evaluated top-1000 value-weighted long-short decile returns from 1999-07-31 through 2024-11-30:

1. `return_sharpe_60`: `ret_12_1 / rvol_252d`
2. `price_zscore_reversal_120`: `-ret_12_1`
3. `volume_price_corr`: `corr_1260d`

Results are in `quantevolver_jkp_proxy_ff_summary.csv`. Under FF5MOM_JKP, the risk-adjusted momentum proxy has annualized alpha 0.0033 with HAC t-stat 0.651; the reversal proxy is mechanically spanned by the benchmark momentum factor; and the volume-price proxy has annualized alpha -0.0094 with HAC t-stat -1.070.

Verdict: useful framework idea, but the shipped seed ideas do not produce relevant incremental USA/JKP alpha after FF5Mom controls in this proxy test.
