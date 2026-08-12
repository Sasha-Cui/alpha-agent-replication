# TreEvo paper-level replication audit

Overall verdict: **document and prompt templates reproduced; native TreEvo
experiment not reproduced**.

## What is faithfully recovered

- Both official arXiv versions are byte-pinned, repeat-download identical, and
  source-rebuilt. Extracted-token multiset overlap with the official PDFs is
  99.88% for v1 and 99.91% for v2. Every official page was rendered and visually
  checked; no page was illegible or clipped.
- The audit transcribes all **96 v1** and **206 v2** displayed table-result
  entries, plus all exact numeric labels recoverable from figures: **18 v1** and
  **87 v2**. The figure ledger identifies eight v2 table duplicates, 30 mirrored
  heatmap cells, and 15 structural diagonals instead of treating repeats as new
  information. Curves and distributions without exact labels are not inferred
  from pixels. The audit also inventories all 22 traditional operators, eight
  v2 figures (23 panels), and all seven v2 prompt templates.
- The published IC and RankIC equations execute deterministically on a synthetic
  panel under audit-declared semantics. This is metric-component evidence only.

## Why result faithfulness is still zero

Neither source bundle contains a TreEvo implementation. The public materials do
not release the market-data snapshot or point-in-time memberships, actual seed
trees, the thought-to-code prompt, model requests/responses, generated factors,
parser/sandbox, search trajectories, random seeds, baseline configurations,
predictions, holdings, daily returns, or raw table/figure arrays. Therefore the
honest end-to-end result score is **0/114 for v1 and 0/293 for v2** displayed
numeric result units. Installing packages cannot reconstruct these scientific
inputs and lineage objects.

## Important revision and consistency findings

- v1 changes materially into v2: the title, DJI-to-NDX universe, traditional
  baseline results, evaluation budgets, return claims, figures, and result
  denominator all change. v2 adds valuable prompts and walk-forward results.
- v2 says EoH beats ReEvo in all Table 2 cases, but the displayed values support
  only 6/8. Its 14.31% claim is correct specifically as the mean per-market IC
  improvement over the stronger of EoH/ReEvo.
- v2 Tables 1 and 2 repeat the same TreEvo means but conflict on CSI300 and
  CSI500 IC standard deviations. v1 prints a likely anomalous 0.2410 SPX RankIC
  standard deviation. V1 Figure 5's displayed three-run averages also fail to
  match its Table 2 ReEvo/TreEvo means, with no released run lineage to reconcile
  the difference.
- v1 was submitted on 2025-08-22 naming Qwen3-Max, while Alibaba's public model
  history dates qwen3-max-preview to 2025-09-05. This is an unresolved public
  provenance conflict; a private prerelease may have existed but is not disclosed.
- The seven published templates still omit the crucial thought-to-executable-code
  prompt, and the initialization template contains an unreleased `{seed_tree}`.

The bounded public search found no attributable implementation. That is not proof
that private, deleted, inaccessible, or unindexed artifacts never existed. Run
`scripts/audit_treevo_paper.py` to regenerate the ledgers. `--strict`
intentionally exits nonzero while end-to-end reproduction remains false.
