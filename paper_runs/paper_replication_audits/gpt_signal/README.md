# GPT-Signal paper/source replication audit

This package audits the official 13-page arXiv v1 paper, the 12-page ACL
FinNLP version, all 71 arXiv source files, the deleted paper-listed repository,
its surviving Wayback capture, and all 13,884
tracked files in the author-owned `Yiningww/Thesis` repository. The author
repository is not linked by the paper, but its pre-publication commit contains
the exact company universe, FactSet workbooks, Yahoo price caches, GPT output
CSVs, formulas, and analysis logic needed to trace the published figures.

## Honest verdict

- **Published quantitative units regenerated from author inputs/source semantics:
  1549/1554
  (99.678%).** This comprises all 1,309 displayed heatmap cells and 240/245
  boxplot statistics. It is strong result-level recovery, not an end-to-end
  regeneration of GPT-Signal.
- The five failures are the all-sector EVC box. Every vector statistic in that
  box is exactly 0.02 above the deterministic replay. The unexplained shift
  changes EVC's median from below the baseline to above it.
- The paper's RAPS equation uses `ROE / (P/E * beta)`, while the raw GPT output,
  released code, and all published cells use `ROE / (P/E ** beta)`. The printed
  equation misses 104/1,309 heatmap cells at two-decimal display precision.
- The 1-month pipeline is not temporally faithful: descending quarterly
  workbooks are forward-filled without sorting, so January/February use the
  coming March quarter, April/May use June, and so on. Full-period mean
  imputation introduces a second future-data path.
- No LLM call was made. The recovered model is `gpt-4-1106-preview`, with no
  seed or temperature; that snapshot is retired. Raw generation output exists
  for five of six published signals, but VEC lacks raw GPT lineage.

## Why 99.678% result recovery is not 99.678% paper fidelity

The result grids can be replayed because the author repository preserved the
post-generation inputs and code semantics. The scientific procedure is less
faithful: the paper-listed repository was only a one-file placeholder in the
surviving post-workshop capture; the real source is unlinked and unlicensed;
there is no dependency lock; the current runner exits before step 2 and
hardcodes the wrong monthly loop length; the paper formula conflicts with its
results; monthly tests leak future data; and no portfolio, transaction-cost,
runtime, statistical-significance, or human-efficiency experiment supports the
broad alpha, speed, scale, or continual-refinement claims.

## Evidence artifacts

- `correlation_cell_reproduction.csv` and `correlation_matrix_summary.csv`:
  every displayed heatmap cell under both the source/GPT and printed-paper RAPS
  formulas.
- `boxplot_stat_reproduction.csv` and `boxplot_figure_summary.csv`: all five
  displayed box statistics for seven models across seven figures.
- `formula_lineage.csv`, `monthly_lookahead_trace.csv`, and
  `method_specification_audit.csv`: formula provenance, a concrete AAPL
  availability trace, and paper/source fidelity boundaries.
- `author_source_inventory.csv`, `paper_source_inventory.csv`,
  `source_provenance.json`, and `discovery_evidence.csv`: complete pinned source
  and artifact lineage. Credential-like strings are counted and redacted; no
  secret value is emitted.
- `native_execution.csv`, `native_execution.json`, and `manifest.json`: exact
  component outcomes and the fail-closed final verdict.
