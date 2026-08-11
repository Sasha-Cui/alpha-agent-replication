# Alpha-Jungle paper-level replication audit

The official nine-page AAAI-26 proceedings paper is the publication authority.
The original arXiv v1 and current v3 extended sources are audited separately.

## Honest outcome

- **Published result reproduction: 0/64 official Table 1 cells.** No
  author-linked code, immutable experiment configuration, China/S&P500 data
  snapshot, factor pool, search trace, LLM call log, predictions, holdings,
  return path, or native result output was found.
- **Extended result reproduction: 0/956 v1 cells and 0/1,312 v3 cells.** Source
  compilation and exact table parsing verify the documents, not the experiments.
- **Formula-component evidence: 3/6 disclosed Ours formula trees.** Formulas
  4-6 are already executed locally with their operator trees preserved, but
  only after daily-China to monthly-U.S. universe/cadence and researcher-
  portfolio adaptations. They receive no MCTS, model, portfolio, or paper-
  result credit. Formulas 1-3 require VWAP, absent from the approved JKP input.
- **Prompts:** four detailed prompt templates are recoverable from both source
  releases. Exact filled runtime prompts, model responses, and immutable model
  snapshots are absent.

## Result-lineage warning

Across 932 semantically common v1/v3 cells, 925 retain the same displayed
number. All 16 v1 ablation cells labelled AR are unchanged when v3 and the
published final relabel them AER, even though AR uses total portfolio returns
and AER uses returns over an unspecified market benchmark. No executable run
lineage is released. Separately, 228 current-v3 appendix cells still use AR
headers while the current metric section and main text define AER.

The v3 cost table is arithmetically self-consistent: all 30 derived server,
API, and total-cost cells recompute from values printed in the same table. This
is an internal consistency check, not independent reproduction of runtimes or
token usage.

## Community repository

`dtbtc/mcts-llm-alpha` is pinned only as an unaffiliated community candidate.
All 40 tracked Python files compile, but the package imports a nonexistent
`mcts_llm_alpha.data` module and all three nominal tests fail collection. Its
defaults also conflict with the paper on model, search budget, dates, split,
and universes, and it contains no native factor pools or paper results.

Alpha-Jungle therefore remains
`paper_only_underspecified_with_three_adapted_disclosed_formula_components`.
