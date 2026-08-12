# Strat-LLM paper-faithfulness audit

This fail-closed audit pins the canonical arXiv v1 PDF, API record, and six-file
source bundle for *Strat-LLM: Stratified Strategy Alignment for LLM-based Stock
Trading with Real-time Multi-Source Signals*.  The source rebuilds unmodified to
the published six-page layout with 0.99846 extracted-token multiset Jaccard, and
all six original pages were visually inspected without clipping or unreadable
content.

## Honest reproduction boundary

The native Strat-LLM experiment is **not reproduced**.  The advertised project
page returns HTTP 404, and bounded GitHub/Hugging Face searches recovered no
attributable implementation, dataset, or output release.  The paper/source ship
no stock list, exact window dates, point-in-time price/news/report snapshot,
complete strategy rules, prompts, immutable model requests, sampling settings,
broker/cost configuration, seeds, actions, orders, fills, holdings, NAV, returns,
or raw result arrays.  Consequently 0/186 unique table cells and 0/4 additional
unique Figure 2 values receive native paper-result credit.  The synthetic T+1
component is explicitly conditional and receives zero result credit.

## Published evidence denominator

- Table 1: 168 numeric cells.
- Table 2: 27 numeric cells, including nine exact repeats of Table 1.
- Figure 2: six numeric points, including two exact repeats of Table 1.
- Unique displayed empirical numeric units: 190.
- Native units regenerated: 0/190.

## Temporal finding

The literal claim of a live-forward experiment during the stated 2025 windows
is contradicted by public model chronology.  All ten model identities or
families represented in the result tables became public after at least part of
those windows, and eight first became public in 2026.  A later chronological
replay over frozen 2025 data could still avoid
look-ahead bias, but no input snapshot, timestamps, request logs, or actions were
released to verify that weaker interpretation.

Negative artifact searches are bounded current observations, not proof that
private, deleted, moved, or unindexed artifacts never existed.  No local proxy
or independent reimplementation is credited as Strat-LLM.
