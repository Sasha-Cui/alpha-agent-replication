# EFS paper-level replication audit

The original arXiv v1 is the corpus/result authority. The current arXiv v2 is
audited separately because it materially changes the author list, method,
datasets, paper structure, and results.

## Honest outcome

- **EFS itself: 0 native result cells reproduced in either version.** No
  author-linked EFS code, exact configuration, model snapshot, factor pool,
  search trace, action/weight path, raw return, or result output was found.
- **Original v1: 11/773 table-result cells reproduce, all cited-baseline
  evidence.** Five are daily-rebalanced 1/N MDD cells; the exact cited UBAH
  source adds the FF25 Sharpe cell; two are Mean-CVaR cells; and SSPO, mSSRM,
  plus ASMCVaR contribute one isolated cell each.
- **Current v2: 18/877 cells reproduce at its coarser display precision.**
  Eight are daily-rebalanced 1/N, three mSSRM, two SSPO, two Mean-CVaR, two
  ASMCVaR, and one is the source-grounded mSSRM m=N Max-Sharpe limit. The two
  exact-source UBAH matches overlap the eight 1/N cells. None forms a complete
  reproduced row or receives native EFS credit.

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

The cited release's exact `ubah_run_self.m` path was also executed twice on all
five EFS matrices under MATLAB R2023b. All five 623-point wealth, daily-return,
and weight paths are bit-identical across repeats. The source consumes all 623
rows, holds equal weights for the first five periods, and then propagates
drifted buy-and-hold weights; this is materially different from the audit's
direct daily-rebalanced 1/N interpretation that treats row zero as initial.
Source-native UBAH matches 1/15 v1 cells and 2/12 v2 cells. The v1 FF25 Sharpe
match is one new unique cell; both v2 matches already coincide with the
daily-rebalanced ledger. No complete 1/N row matches under either protocol.

The conventional Mean-CVaR baseline from the original ASMCVaR paper was
reimplemented directly from equations (1)--(3), with the disclosed rolling
window and conventional c=0.95 confidence. All six full wealth/weight paths
repeat bit-identically under Python 3.9 and 3.12, and all 12 published CW/SR
cells reproduce. Against EFS, only 2/15 v1 and 2/12 v2 cells match, with no
complete row.

The mSSRM source was also run at m=N, which removes the cardinality restriction
from equations (3.3)--(3.4) and supplies a source-grounded regularized
Max-Sharpe limit. All five full paths repeat bit-identically across 10 Octave
runs. It matches 0/15 v1 and only 1/12 v2 Max-Sharpe cells (FF25 MDD at coarse
precision), so it does not recover an EFS Max-Sharpe row. The EFS authors did
not release the wrapper needed to prove that this was their implementation.
The JMLR-linked SSPO source and the exact five OLPS datasets reproduce all 10
original-paper CW/SR cells, with all full wealth/weight paths equal across
repeats. The only Octave shim is MATLAB's standard soft-threshold operation.
On EFS's Fama--French matrices the same pinned source matches just 1/15 v1 and
2/12 v2 cells, all isolated in FF100, and no complete SSPO row.


A three-commit repository owned by ASMCVaR coauthor Zhao-Rong Lai explicitly
redirects to the executed `linyizun2024/ASMCVaR` repository. This establishes
author attribution for that cited source, but adds no executable files or EFS
lineage.


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
