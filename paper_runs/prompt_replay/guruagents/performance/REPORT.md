# GuruAgents prompt-replay performance analysis

Generated `2026-08-11T05:46:24.081257+00:00` from the completed live replay. This package constructs corrected
formation-to-realization return paths for the replayed portfolios and the authors' archived
portfolios, charges transaction costs, measures traded notional, and runs factor tests.

## Return construction

- Formation label: source analysis quarter end.
- Execution: first trading close strictly after formation quarter end.
- Price: `DIV_ADJ_CLOSE`, with `CLOSE_` only as a missing-value fallback.
- Holding rule: buy-and-hold between quarterly rebalances; weights drift with prices.
- Transaction cost: 1 bp times one-way traded notional, deducted at each rebalance.
- Realization label: calendar month end. The final partial source month is retained with
  `analysis_eligible=false` and is excluded from performance and alpha tests.
- Ticker corrections and dropped rows are explicit in `formation_audit.csv`.

There are 24 replay strategy paths and
660 eligible replay strategy-month observations. Equal-weight multi-agent
ensembles are formed from the five sleeve target portfolios at each formation date.

## Economic results (replay, net 1 bp)

| Candidate | Months | Ann. return | Ann. vol | Sharpe | Mean monthly traded notional |
|---|---:|---:|---:|---:|---:|
| `replay__results_22_24__archived-final__buffett` | 36 | 33.69% | 21.72% | 1.27 | 0.265 |
| `replay__results__tool-routing__greenblatt` | 19 | 21.04% | 11.34% | 0.97 | 0.330 |
| `replay__results_22_24__tool-routing__buffett` | 36 | 21.71% | 22.01% | 0.82 | 0.307 |
| `replay__results__tool-routing__buffett` | 19 | 26.12% | 16.51% | 0.79 | 0.374 |
| `replay__results__archived-final__graham` | 19 | 30.33% | 16.60% | 0.76 | 0.368 |
| `replay__results_22_24__archived-final__ensemble` | 36 | 19.25% | 21.12% | 0.75 | 0.232 |
| `replay__results__archived-final__buffett` | 19 | 26.59% | 17.91% | 0.66 | 0.421 |
| `replay__results_22_24__tool-routing__ensemble` | 36 | 16.57% | 21.16% | 0.64 | 0.223 |

These are short realized histories, not long-run estimates. The `results` archive begins only
in January 2024 realization time; the `results_22_24` archive begins in April 2022.

## Alpha tests

| Benchmark | Identified replay paths | Nominal positive | Holm positive | Nominal negative |
|---|---:|---:|---:|---:|
| `jkp132_compressed_pre2022_pca5` | 12 | 3 | 1 | 0 |
| `jkp132_full_lomo_ridge_exploratory` | 24 | 2 | 0 | 0 |
| `jkp132_full_ols` | 0 | 0 | 0 | 0 |
| `jkp_primary_six` | 12 | 1 | 0 | 0 |
| `jkp_top1000_capm` | 24 | 3 | 0 | 7 |
| `mean_excess_return` | 24 | 1 | 0 | 0 |
| `nasdaq100_source_universe_capm` | 24 | 1 | 0 | 0 |
| `official_ff3_matched_jkp_window` | 12 | 2 | 0 | 0 |
| `official_ff5_momentum_matched_jkp_window` | 12 | 3 | 1 | 0 |
| `official_ff5_momentum_plus_jkp_bab` | 12 | 2 | 1 | 0 |
| `official_ff5_momentum_plus_jkp_lowrisk` | 12 | 3 | 1 | 0 |
| `official_ff_capm_matched_jkp_window` | 12 | 3 | 0 | 0 |

The market test is shown both for the source Nasdaq-100 file's cap-weighted universe and for
the same-universe JKP top-1000 market. The primary six-factor benchmark is market plus the five
predeclared characteristics in factor order.

### Matched official Fama--French and low-risk attribution

| Benchmark | Identified replay paths | Median annual alpha | Positive | Nominal positive | Holm positive |
|---|---:|---:|---:|---:|---:|
| `official_ff_capm_matched_jkp_window` | 12 | 7.30% | 12 | 3 | 0 |
| `official_ff3_matched_jkp_window` | 12 | 6.23% | 12 | 2 | 0 |
| `official_ff5_momentum_matched_jkp_window` | 12 | 6.12% | 12 | 3 | 1 |
| `official_ff5_momentum_plus_jkp_bab` | 12 | 2.87% | 11 | 2 | 1 |
| `official_ff5_momentum_plus_jkp_lowrisk` | 12 | 3.50% | 11 | 3 | 1 |

This nested ladder uses the exact common realization window shared by the official Kenneth
French factors and the extended JKP panel. `official_ff5_momentum_plus_jkp_bab` adds only the
JKP `betabab_1260d` return to official FF5 plus momentum. The predeclared low-risk block then
adds, in this fixed order, `char__betabab_1260d, char__beta_60m, char__beta_dimson_21d, char__betadown_252d, char__ivol_capm_252d, char__rvol_21d, char__qmj_safety`. This makes attenuation
after the BAB increment directly inspectable; it is not inferred from the generic JKP132 fit.
All five rows require the same 33-month history, so the short archive is
reported as unavailable throughout the ladder. Holm counts in this report are computed within
the replay family for each benchmark.

An unrestricted market-plus-132-JKP OLS has 134 parameters including the intercept. It is not
identified for a replay path with roughly 13 or 34 monthly observations; those rows are
reported as unavailable rather than silently fit with a pseudoinverse. Two supplementary tests
are therefore included:

1. `jkp132_compressed_pre2022_pca5` freezes five principal components using factor returns only
   through 2021, then estimates replay exposure to the market, primary factors, and those fixed
   components.
2. `jkp132_full_lomo_ridge_exploratory` uses all 133 factors with nested leave-one-month-out
   ridge selection. Monthly penalties and loadings are published, but the test is labelled
   exploratory and noncausal because each fold can use future replay months.

The long-history JKP motif proxies do have enough observations for the full 133-factor OLS;
their direct JKP132 residuals and alpha tests are included for comparison.

## Factor extension and comparison limits

The published broad panel ends 2021-12-31. It is extended through
2024-11-30 with the exact same top-1000 membership and unit-gross
cross-sectional-rank construction, validated on 12
overlap months. The maximum reconstructed-versus-published overlap difference is
9.77e-17.

The JKP proxies are long-short top-1000 motif portfolios, while GuruAgents replay and author
paths are long-only portfolios in the source Nasdaq file. Proxy turnover and transaction costs
cannot be reconstructed from the published proxy return files. `economic_comparison.csv`
therefore reports common-month results with this mandate and cost asymmetry explicitly labelled;
it must not be read as a horse race between identical implementations.

## Main artifacts

- `monthly_return_paths.csv`: formation and realization labels, gross return, traded notional,
  1 bp net return, NAVs, eligibility, and failure flags.
- `formation_holdings.csv` and `formation_audit.csv`: the actual replay/author target matrices and
  all parsing/correction decisions.
- `factor_panel_extended_formation.csv` and `factor_panel_extended_realization.csv`: exact factor
  order with both clocks.
- `alpha_regressions.csv`, `factor_fitted_and_residuals.csv`, `static_factor_loadings.csv`, and
  `monthly_ridge_loadings.csv`: tests, fitted values, residuals, coefficients, and selected penalties.
- `replay_attribution_ladder.csv` and `replay_attribution_by_candidate.csv`: matched official
  Fama--French, BAB, and broader low-risk attribution results.
- `economic_performance.csv` and `economic_comparison.csv`: common economic metrics and pairwise
  author/replay/proxy comparisons.
- `manifest.json`: hashes, samples, clocks, costs, factor order, software, and licensing cautions.
