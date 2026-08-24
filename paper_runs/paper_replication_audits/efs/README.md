# EFS paper-level replication audit

The original arXiv v1 is the corpus/result authority. The current arXiv v2 is
audited separately because it materially changes the author list, method,
datasets, paper structure, and results.

## Honest outcome

- **EFS itself: 0 native result cells reproduced in either version.** No
  author-linked EFS code, exact configuration, model snapshot, factor pool,
  search trace, action/weight path, raw return, or result output was found.
- **Original v1: 7/773 table-result cells reproduced, all cited-baseline
  evidence.** Five are 1/N MDD cells; mSSRM and ASMCVaR contribute one isolated
  cell each. Neither cited sparse method reproduces a complete EFS row.
- **Current v2: 13/877 cells reproduce at its coarser display precision.** Eight
  are 1/N cells, three are mSSRM cells, and two are ASMCVaR cells. All are
  cited-baseline evidence, not EFS evidence. Paper compilation and parsing
  receive no experiment credit.

The mSSRM release was run twice for every combination of five EFS matrices
and m={10,15,20}. All 15 full 623-point wealth paths were bit-identical across
repeats, yet 44/45 original-v1 cells disagree with EFS at printed precision.
This is an EFS baseline-protocol mismatch, not a failure to replicate mSSRM:
all 36 CW/SR cells in the original NeurIPS mSSRM paper reproduce, and all six
untouched conference-supplement m=10 wealth paths equal the mirror bit-for-bit.

The ASMCVaR release was executed for all six original-paper datasets and
m={10,15,20} under MATLAB R2023b. It reproduces 95/96 original ICML empirical
cells: all 18 CW, 17/18 Sharpe, all 36 alpha/p-value, and all 24 sparsity-overlap
cells. The sole conflict is FF49 m=10 Sharpe: released code prints 0.2338 while
the paper prints 0.2339. Against EFS, only 1/45 v1 and 2/24 v2 ASMCVaR cells
match at display precision, and no complete row matches. A same-runtime repeat
is bit-identical; an independent Octave execution agrees within disclosed
floating-point tolerances.

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
