# AlphaAgents paper/source replication audit

This package audits arXiv:2508.11152v1, its nine-page PDF, the official TeX
source archive, and the public repository search surface. It is fail-closed:
manuscript compilation, source comments, raster plots, and unaffiliated
reimplementations are not native experimental results.

## Verdict

- **Native AlphaAgents performance reproduced: 0/20 plotted series.**
- **Document fidelity is high:** the official TeX source compiles to nine pages
  and reaches 99.7674% extracted-token
  multiset Jaccard against the arXiv PDF.
- **Portfolio specification improved:** seven commented-out TeX table rows
  recover 77 ticker
  memberships, including the 15-stock benchmark and six agent/risk portfolios.
- No author-linked implementation, Bloomberg/filing/price snapshot, model
  snapshot, filled risk-profile prompt, agent output, debate trace, raw return
  path, Phoenix score, or plot array was found.
- Five GitHub repositories were found and audited as unaffiliated community
  work. Every one changes core data, models, orchestration, universe, dates, or
  benchmark; none reproduces a paper result series.
- The two existing local AlphaAgents candidates remain M0 narrative
  translations. Their factor formulas, monthly long-short deciles, weights,
  and return streams are not the paper's agent-picked portfolios.

## Material blockers and conflicts

- The PDF says the risk-neutral fundamental portfolio expands the benchmark;
  the official source table instead lists 14 of the benchmark's 15 stocks.
- The sentiment agent is said to be excluded for insufficient coverage, but
  the next paragraph says a sentiment portfolio was constructed; no sentiment
  curve appears in the figures.
- GPT-4o is named both as the experiment LLM and as an embedding model, without
  a separately identified embedding endpoint or snapshot.
- The rolling Sharpe window, return frequency, Treasury-series identifier and
  rate conversion, adjusted-price convention, cumulative-return implementation,
  costs, and execution details are absent.
- Claims about reduced drawdown, lower volatility, RAG faithfulness/relevance,
  hallucination reduction, and analytical rigor have no released measurements.

## Files

- `source_file_inventory.csv`: every member and hash in the official source tar.
- `source_build_audit.json`: manuscript rebuild and text-conformance evidence.
- `source_only_portfolio_inventory.csv`: seven recovered portfolio lists.
- `plotted_result_series_conformance.csv`: all 20 result lines in Figures 6--8.
- `prompt_inventory.csv`: seven recovered fragments and three missing risk prompts.
- `method_specification_audit.csv`: exact-replication requirements and blockers.
- `paper_internal_consistency_audit.csv`: paper/source conflicts and ambiguities.
- `community_reimplementation_inventory.csv`: five non-author implementations.
- `source_search_inventory.csv` and `source_provenance.json`: pinned provenance.
- `native_execution.json` and `manifest.json`: machine-readable evidence boundary.
