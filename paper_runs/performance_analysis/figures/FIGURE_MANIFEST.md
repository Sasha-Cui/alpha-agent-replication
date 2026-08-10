# Alpha Evolve Performance Figures

Generated from canonical alpha_evolve outputs streamed from Bouchet on 2026-07-05.

## Data Sources

- `paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_candidate_summary.csv`
- `paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_benchmark_metrics.csv`
- `paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_book_delta_mvo.csv`
- `paper_runs/performance_analysis/figures/metric_correlation_matrix.csv`
- `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_all_benchmark_metrics.csv`
- `paper_runs/idea_replications/jkp_paper_idea_proxies/candidate_returns_*.csv`
- `paper_runs/idea_replications/paper_derived_source_replication_ledger.csv`
- `paper_runs/repository_ff5mom_metrics_summary.csv`

## Figures

- `performance_outcome_counts.png`: audit funnel and direct-code audit counts.
- `ff5mom_alpha_tstat_ranking.png`: FF5Mom alpha t-stat ranking for all 62 candidate proxies; green points pass the strict FF5Mom positive-alpha rule.
- `textbenchmark_additivity_scatter.png`: full-span alpha t-stat versus long-only book delta Sharpe; marker size is optimized candidate weight; green points are strict additive candidates.
- `performance_metric_distributions.png`: distributions of standalone Sharpe, FF5Mom t-stat/IR, full-span t-stat/GRS p-value, and long-only delta Sharpe.
- `grs_pvalue_comparison.png`: FF5Mom versus full-span GRS p-value comparison.
- `strategy_return_correlation_heatmap.png`: pairwise Pearson correlation matrix across the 62 monthly strategy return streams; numbered rows/columns map to the t-stat table.
- `metric_correlation_heatmap.png`: Pearson correlations across 14 headline performance metrics for all 62 candidate proxies. It shows that several apparent positives are alternate views of the same factor-composite geometry rather than independent evidence.

## Tables And Support Artifacts

- `strategy_return_tstats.tex`: LaTeX longtable of each strategy's return t-stat, FF5Mom alpha t-stat, and full-span alpha t-stat.
- `strategy_return_tstats.md`: Markdown version of the same t-stat table.
- `strategy_return_tstats.csv`: Machine-readable t-stat table.
- `strategy_return_correlation_matrix.csv`: Machine-readable return-correlation matrix.
- `strategy_return_pairwise_month_counts.csv`: Pairwise monthly overlap counts for the return-correlation matrix.
- `metric_correlation_matrix.csv`: Machine-readable 14-by-14 matrix displayed in `metric_correlation_heatmap.png`.

## Regeneration

```bash
python scripts/build_metric_correlation_heatmap.py
```

The builder asserts the 62-proxy row count and four sentinel correlations
before writing the matrix and figure. It sets all foreground and background
colors explicitly and switches annotation colors on strong cells to preserve
readability.

## Headline Counts Encoded

- Unique sources: 55
- JKP-mappable sources: 51
- Candidate proxies: 62
- Strict FF5Mom beaters: 8
- Strict TextBenchmark/JKP132 additive candidates: 3
- Direct cloned repos: 14
- Direct repos with valid JKP returns: 1
- Direct repos beating FF5Mom: 0
