# Trading-R1 paper replication audit

Authority: arXiv v1, submitted 2025-09-14T20:13:41Z. Audit snapshot: 2026-08-11.

## Honest result

The paper specification is partially reconstructable, but the Trading-R1 system and its published backtest are not reproducible from the official release. The official repository still contains one 49-byte release-soon README and no code, model, dataset, configuration, prediction, trade, or return artifact. The TauricResearch Hugging Face model and dataset queries are both empty in the pinned audit snapshot.

Paper-result credit is **0/348 numeric display units**: 0/312 cells from Tables 3--4 and 0/36 annotations from Figure 5. Compiling the 58-page paper and executing literal paper equations are not native result reproduction.

## What this audit did reproduce

- Parsed and source-checked all 312 table cells (13 models × 6 assets × 4 metrics).
- Extracted all 36 annotated Sharpe values from Figure 5. Only 35/36 are internally compatible with the rounded table cells; Trading-R1/NVDA is 2.72 in Table 3 but 1.881 in Figure 5 and 1.88 in prose.
- Executed a literal reconstruction of Algorithm S1 and the published decision matrix on synthetic diagnostics. These are labeled paper-spec reconstructions, never released-source executions.
- Compiled the pinned arXiv source twice to 58 pages.

## Material blockers and inconsistencies

- Algorithm S1 is described as using forward returns but computes trailing returns with `EMA.shift(tau)`.
- Its percentile thresholds are fit over the full supplied series. In the deterministic diagnostic, appending future observations changes 72/126 already assigned prefix labels.
- The decision matrix gives prediction Strong Buy / truth Strong Sell a -2.00 penalty and the reverse mistake -2.25, opposite the prose claim that false bullish errors are penalized more heavily.
- The claimed held-out June--August 2024 interval lies inside the January 2024--May 2025 collection interval, but no split manifest is released.
- The paper does not disclose action weights, exact holding/rebalance/entry/exit rules, costs, leverage/cash constraints, baseline snapshots, prompts/decoding, raw actions, equity paths, training hyperparameters, or seeds.
- The official project page says the Terminal is released, while its linked repository still says “Releasing soon.”

The complete boundaries are recorded in `paper_mechanism_conformance.csv`, `paper_specification_gaps.csv`, and `paper_internal_consistency_checks.csv`.
