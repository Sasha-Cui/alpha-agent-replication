# CogAlpha paper-faithfulness audit

This fail-closed audit separates the 27-page arXiv v1 study, the materially
expanded 35-page arXiv v4/ACL-final study, and the late author-owned prompt-only
release.  It does not use the existence of prompts or manuscript assets as a
substitute for native experiment reproduction.

## Honest reproduction boundary

The native CogAlpha experiments are **not reproduced**.  ArXiv v1 contains 150
unique empirical units after accounting for table repeats, and arXiv v4/ACL
final contains 306; 0/150 and 0/306 regenerate from a native pipeline.  The
author source does ship the exact four-series cumulative-return raster, so 4/4
curve series receive author-output correspondence credit, not regeneration
credit.  Three published factor listings and one declared prompt assembly run
on synthetic fixtures and receive source-component credit only.

The sole author repository is a single 2026-07-14 commit, after arXiv v4.  It
contains 39 attributable prompt templates and explicit assembly instructions,
but its README says it intentionally excludes runtime code, datasets,
experiment outputs, private model endpoints, and local paths.  No experiment
runner, frozen constituent memberships/OHLCV snapshot, immutable model
checkpoint or request log, realized factor pools, checker/evolution traces,
seeds, predictions, actions, holdings, dated returns, or raw result arrays are
released.

The complete public Git surface was also exhausted as of 2026-08-14.  The
official history has exactly that one commit, and all 47 Git paths are
byte-for-byte identical to the pinned release archive.  Across the full history
there is no structured result/data payload and none of six distinctive
published result values.  GitHub reports one accessible fork with one branch
ref and no tag refs; it resolves exactly to the official head and adds zero
result lineage.  It adds zero unique commits, zero unique blobs, and zero
paper-result credit.

## Edition denominators

- ArXiv v1: 150 table cells, 138 unique after 12 repeated cells; eight
  additional numeric factor claims; four cumulative-return series; 150 unique
  empirical units in total; 0 regenerated.
- ArXiv v4 / ACL final: 298 table cells, 270 unique after 28 repeated cells;
  32 additional numeric factor claims; four cumulative-return series; 306
  unique empirical units in total; 0 regenerated.
- Prompt release: 39 templates (22 hierarchy, 11 shared, four quality-checker,
  two thinking-evolution), all attributable and pinned, but zero model calls or
  paper outputs replayed.

## Source and claim findings

ArXiv v4 rebuilds unmodified to 35 pages at 0.999683 extracted-token multiset
Jaccard, and the ACL final is 0.994942 aligned with v4.  ArXiv v1 does not build
unmodified: its declared numeric `main.bbl` conflicts with author-year
`natbib`.  V1 also claims CogAlpha wins every metric although RandomForest's
0.4385 RankICIR exceeds CogAlpha's 0.4350; v4 explicitly acknowledges that
exception.  The paper calls one factor improvement significant without a test,
and its single stochastic mining round has no seeds or trace.

All 97 pages across v1, v4, and ACL final were visually inspected without a
blank, clipped, overlapping, or unreadable page.  Negative artifact searches
are bounded observations, not proof that private, deleted, moved, or unindexed
artifacts never existed.  No local proxy is credited as CogAlpha.
