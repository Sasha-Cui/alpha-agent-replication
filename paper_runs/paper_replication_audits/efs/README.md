# EFS paper-level replication audit

The original arXiv v1 is the corpus/result authority. The current arXiv v2 is
audited separately because it materially changes the author list, method,
datasets, paper structure, and results.

## Honest outcome

- **EFS itself: 0 native result cells reproduced in either version.** No
  author-linked EFS code, exact configuration, model snapshot, factor pool,
  search trace, action/weight path, raw return, or result output was found.
- **Original v1: 5/773 table-result cells reproduced, all 1/N MDD baselines.**
  The check executes the equal-weight formula on the exact 623-row benchmark
  matrices in the official ASMCVaR release cited by EFS. This is baseline
  evidence, not EFS evidence.
- **Current v2: 8/877 cells reproduced at its coarser display precision, again
  baseline-only.** Paper/source compilation and table parsing are document
  evidence and receive no experiment credit.

## Version-lineage warning

All 240 v2 benchmark cells common to v1 are rounded carryovers. More
importantly, all 48 v1 cells labelled “+ Scores to Weights” are relabelled in
v2 as results from the newly introduced RMT/QP “+RW” factor-weighting method,
without released code, matrices, or run lineage. The two labels describe
different mechanisms, so those cells receive no new-method credit.

## Why this is not a faithful replication

The papers provide valuable equations, algorithms, v1 prompt text, several
example factors, and many settings. They do not identify the executable
experiment. Blocking gaps include immutable LLM revisions and decoding,
market-data snapshots and point-in-time universes, the EFS DSL and validator,
seeds, warmup/search schedules, generated factors, baseline wrappers, weights,
returns, and uncertainty. The two versions also conflict on cumulative-wealth
and Sharpe definitions, prompt availability, OOS search, per-dataset tuning,
and repeated result identities.

The paper therefore remains `paper_only_underspecified`. The three local EFS
JKP mappings remain M1 example/motif components; none is a native EFS formula,
portfolio, or paper-result reproduction.
