# FinRS paper-faithfulness audit

This is a paper-derived component and cross-paper lineage audit, not an end-to-end FinRS replication. The official six-page arXiv-v1 source rebuilds without modification; every official and rebuilt page was visually checked with no observed defects.

The paper contains **225 displayed empirical cells across two tables** and one conceptual (zero-empirical-panel) figure. Zero of 225 cells were regenerated through an author-native pipeline. Three controlled mechanics execute, but their equations are identical to FinPos v1 and are paper-derived checks, not author code or FinRS result credit.

Cross-paper lineage is unusually strong: **216/225 FinRS cells exactly match FinPos v1**, published 16 days earlier. All 180 main-table cells match, as do four of five ablation rows (36/45 cells). The nine changed cells are the FinRS Market News-removal row. This is displayed-value reuse, not independent empirical corroboration.

The paper's main risk-sensitive contribution is not executable from the source. Scaled Kelly, CVaR, volatility adjustment, risk prompts, account exposure, and order sizing are named but not defined. The printed reward contains no risk-adjustment term, conflicts with the claimed P&L benchmark and horizon scaling, uses asset-scale-dependent raw dollars, and rewards total position rather than action/change. Future 1/7/30-day differences are described in the decision path without an explicit test-time exclusion.

No attributable code, immutable data, runtime prompts/responses, trades, positions, account path, raw arrays, or result generator was found. Therefore `strict_success` remains false. Negative searches are bounded and do not prove that private, deleted, moved, renamed, unindexed, or later material does not exist.
