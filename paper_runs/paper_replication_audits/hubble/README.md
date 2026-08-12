# Hubble paper-faithfulness audit

This fail-closed audit pins and rebuilds both materially different official
arXiv editions of *Hubble*.  The unmodified v1 and v2 source bundles reproduce
the published 11- and 17-page layouts with extracted-token multiset Jaccard of
0.99737 and 0.99905.  All 28 rebuilt pages were visually checked without
clipping, overlap, missing figures, unreadable labels, or contrast failures.

## Honest reproduction boundary

The native Hubble experiment is **not reproduced**.  The source archives contain
manuscript assets, not the runtime, data, or stored artifacts advertised in the
paper.  The author-lab GitHub organization exists but has zero public
repositories, and bounded repository/code/author searches recovered no
attributable implementation.  Most decisively, v1 anonymizes the five factors
and v2 explicitly withholds their exact formulas and hyperparameters.  The
universe snapshots, prompts, RAG corpora/indexes, operator registry, model
requests, scoring constants, seeds, candidate/error records, environment, and
raw result arrays are also absent.

The published denominator is 50 numeric result cells in v1 (47 after three
semantic repeats) and 108 in v2 (102 after six semantic repeats), plus 11 and 39
displayed empirical figure series whose underlying arrays are not released.
Native result regeneration is 0/47 for v1, 0/102 for v2, and 0/50 figure series.
The independent AST fixture is a conditional method check only and receives
zero Hubble result credit.

## Material audit findings

- v1's accounting conflicts with its table definitions: `Evaluated + Errors`
  equals 81 per round, while the displayed evaluated counts total 186 and
  `OK + Errors` total 243.  Its prose also says zero Round-1 duplicates while
  the figure caption says five and the table implies five.
- v2's two named LLM backends first became public on 2026-03-11, after the
  claimed OOS window began on 2025-06-01 and two days before it ended.  Thus the
  literal statement that formulas were fixed before the OOS window began is
  contradicted by public chronology.  A later retrospective run using only the
  discovery slice could still be a valid data-layer holdout, but no timestamped
  freeze, requests, formulas, inputs, or outputs verify it.
- The claimed 840 discovery dates and 195 OOS dates do not follow directly from
  the stated endpoints: broad U.S. session data contain 855 and 197 dates.  A
  complete-case filter could explain the difference, but no included-date array
  or missing-data rule is released.
- v2 itself acknowledges the single split, short OOS, no neutralization, no
  transaction-cost evaluation, possible LLM temporal leakage, and lightweight
  backend check.  Those cautions are scientifically appropriate; they also mean
  the paper is preliminary evidence, not a fully reproducible alpha result.

Negative artifact searches are bounded current observations, not proof that
private, deleted, moved, or unindexed material never existed.  Unaffiliated
paper-inspired repositories and local fixtures are not credited as Hubble.
