# GuruAgents Additive Value to Long-Only JKP Book


Date: 2026-07-04

This section digs into the two paper-idea proxies that beat FF5Mom and asks whether their long-only versions add value to an existing long-only JKP factor book. I did not find an explicit `jkp132` constituent list in the approved folders. The primary book used here is therefore the equal-weight average of all 153 JKP metadata characteristics with available direction flags. As a robustness check, I also report the 119-characteristic subset with `significance = 1` in `factor_details.xlsx`.

All inputs are still JKP-only and USA-only. The existing book comes from `${ALPHA_EVOLVE_JKP_ROOT}/data/processed/portfolios/pfs.parquet`: for each characteristic, the long side is portfolio 3 when JKP direction is positive and portfolio 1 when JKP direction is negative, using capped value-weighted excess returns. The Guru candidate sleeves are built from `${ALPHA_EVOLVE_JKP_ROOT}/data/processed/characteristics/USA.parquet` using the same realized-return month labeling as JKP `pfs.parquet`.

### Primary Result

Primary construction: JKP-style top-tercile capped-VW long-only candidate sleeve, compared to the all-153 long-only JKP book.

| candidate | book SR | candidate SR | literal wt | literal dSR | 50/50 dSR | best wt | best dSR | alpha ann vs book | alpha t | IR | GRS p | corr |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guru_buffett_quality_compounder | 0.547 | 0.649 | 0.006 | 0.0007 | 0.054 | 1.000 | 0.102 | 1.93% | 2.805 | 0.542 | 0.0074 | 0.978 |
| guru_two_winner_equal_weight_combo | 0.547 | 0.660 | 0.006 | 0.0008 | 0.059 | 1.000 | 0.113 | 2.08% | 2.792 | 0.584 | 0.0040 | 0.976 |
| guru_equal_weight_style_ensemble | 0.547 | 0.667 | 0.006 | 0.0008 | 0.063 | 1.000 | 0.120 | 2.23% | 2.398 | 0.550 | 0.0066 | 0.968 |

Interpretation:

- The two Guru sleeves have positive residual alpha versus the long-only JKP book. Buffett-quality has annualized alpha 1.93%, HAC t-stat 2.805, IR 0.542, and GRS p-value 0.0074. The equal-weight guru ensemble has annualized alpha 2.23%, HAC t-stat 2.398, IR 0.550, and GRS p-value 0.0066.
- Literal insertion into a 153-sleeve equal-weight book has tiny mechanical impact: one added sleeve gets weight 1/154 = 0.65%, so Sharpe rises only about 0.0007 to 0.0008.
- At a meaningful allocation, the effect is larger: a 50/50 book/candidate blend raises Sharpe by about 0.054 to 0.063. The best long-only blend on a 0% to 100% candidate grid is 100% candidate for all three rows, because the candidate sleeves have higher Sharpe than the book.
- This is not a strong diversification result. Correlations to the book are 0.968 to 0.978. The evidence is better described as a quality/profitability/low-leverage refinement of the JKP long-only book, not an independent new return stream.

### Full Robustness Table

| book | construction | candidate | book SR | candidate SR | literal dSR | 50/50 dSR | alpha ann | alpha t | IR | GRS p | corr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| jkp119_significant | jkp_tercile_vw_cap | guru_two_winner_equal_weight_combo | 0.558 | 0.660 | 0.0009 | 0.053 | 1.89% | 2.776 | 0.559 | 0.0058 | 0.979 |
| jkp119_significant | jkp_tercile_vw_cap | guru_buffett_quality_compounder | 0.558 | 0.649 | 0.0008 | 0.049 | 1.75% | 2.631 | 0.502 | 0.0132 | 0.978 |
| jkp119_significant | jkp_tercile_vw_cap | guru_equal_weight_style_ensemble | 0.558 | 0.667 | 0.0010 | 0.057 | 2.03% | 2.401 | 0.534 | 0.0083 | 0.972 |
| jkp119_significant | top1000_decile_vw | guru_two_winner_equal_weight_combo | 0.558 | 0.686 | 0.0015 | 0.082 | 3.12% | 2.059 | 0.405 | 0.0448 | 0.862 |
| jkp119_significant | top1000_decile_vw | guru_equal_weight_style_ensemble | 0.558 | 0.662 | 0.0014 | 0.073 | 2.85% | 1.912 | 0.358 | 0.0766 | 0.844 |
| jkp119_significant | top1000_decile_vw | guru_buffett_quality_compounder | 0.558 | 0.674 | 0.0016 | 0.083 | 3.39% | 1.780 | 0.378 | 0.0613 | 0.836 |
| jkp119_significant | top_decile_vw_cap | guru_equal_weight_style_ensemble | 0.558 | 0.693 | 0.0013 | 0.075 | 2.73% | 2.054 | 0.509 | 0.0120 | 0.946 |
| jkp119_significant | top_decile_vw_cap | guru_two_winner_equal_weight_combo | 0.558 | 0.649 | 0.0009 | 0.052 | 1.96% | 1.934 | 0.405 | 0.0452 | 0.959 |
| jkp119_significant | top_decile_vw_cap | guru_buffett_quality_compounder | 0.558 | 0.598 | 0.0006 | 0.027 | 1.20% | 1.173 | 0.219 | 0.2770 | 0.953 |
| jkp153_all | jkp_tercile_vw_cap | guru_buffett_quality_compounder | 0.547 | 0.649 | 0.0007 | 0.054 | 1.93% | 2.805 | 0.542 | 0.0074 | 0.978 |
| jkp153_all | jkp_tercile_vw_cap | guru_two_winner_equal_weight_combo | 0.547 | 0.660 | 0.0008 | 0.059 | 2.08% | 2.792 | 0.584 | 0.0040 | 0.976 |
| jkp153_all | jkp_tercile_vw_cap | guru_equal_weight_style_ensemble | 0.547 | 0.667 | 0.0008 | 0.063 | 2.23% | 2.398 | 0.550 | 0.0066 | 0.968 |
| jkp153_all | top1000_decile_vw | guru_two_winner_equal_weight_combo | 0.547 | 0.686 | 0.0012 | 0.087 | 3.26% | 2.156 | 0.423 | 0.0365 | 0.861 |
| jkp153_all | top1000_decile_vw | guru_equal_weight_style_ensemble | 0.547 | 0.662 | 0.0011 | 0.078 | 3.00% | 1.979 | 0.373 | 0.0643 | 0.840 |
| jkp153_all | top1000_decile_vw | guru_buffett_quality_compounder | 0.547 | 0.674 | 0.0013 | 0.087 | 3.51% | 1.875 | 0.394 | 0.0512 | 0.837 |
| jkp153_all | top_decile_vw_cap | guru_equal_weight_style_ensemble | 0.547 | 0.693 | 0.0011 | 0.080 | 2.93% | 2.085 | 0.526 | 0.0094 | 0.941 |
| jkp153_all | top_decile_vw_cap | guru_two_winner_equal_weight_combo | 0.547 | 0.649 | 0.0008 | 0.057 | 2.15% | 2.016 | 0.434 | 0.0319 | 0.957 |
| jkp153_all | top_decile_vw_cap | guru_buffett_quality_compounder | 0.547 | 0.598 | 0.0005 | 0.032 | 1.37% | 1.340 | 0.252 | 0.2113 | 0.954 |

The significant-119 robustness book gives the same qualitative answer. Top-decile variants are noisier: the top-decile capped-VW equal-weight ensemble is still statistically positive versus the 153 book, while the top1000 decile versions are positive but weaker and several are near or above the 5% GRS threshold.

### Reproducibility

Run from the Bouchet canonical directory:

```bash
cd ${ALPHA_EVOLVE_REPO}
.venv/bin/python scripts/evaluate_guru_jkp_longonly_additive.py
```

Main artifacts:

- `paper_runs/idea_replications/guru_jkp_longonly_additive/guru_jkp_longonly_additive_summary.csv`
- `paper_runs/idea_replications/guru_jkp_longonly_additive/jkp_long_only_book_returns.csv`
- `paper_runs/idea_replications/guru_jkp_longonly_additive/guru_candidate_long_only_returns.csv`
- `paper_runs/idea_replications/guru_jkp_longonly_additive/run_metadata.json`
- `scripts/evaluate_guru_jkp_longonly_additive.py`

<!-- GURU_JKP_LONGONLY_ADDITIVE_END -->
