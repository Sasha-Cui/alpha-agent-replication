# AAPM paper/source replication audit

This package audits both official arXiv versions, both source bundles, the
complete nine-commit official GitHub history, every released file, all
65,733 metadata records, 114 v1 table cells,
162 v2 table cells, and 54 quantitative figure units.

## Honest verdict

- **End-to-end AAPM result cells reproduced: 0/162.** No native
  checkpoint, prediction array, portfolio-return series, baseline output, or
  table-valued result is released.
- The official repository is runnable component code, not an executable paper
  replication. A 135-package environment passes dependency checks; all four
  importable source modules load twice without HTTP, native Chroma memory and
  model-forward fixtures pass twice, and `model.py` exits cleanly offline.
  `analysis.py` first reaches the unreleased `Data/library/index.csv`. The
  released metadata keys deterministically reconstruct all 65,733 date/path rows,
  and an immutable `BAAI/bge-large-en-v1.5` snapshot last modified before the
  source cutoff loads fully offline. Two copied-tree runs then enter the first
  5,000-row chunk and stop at the first absent `news_analysis` record because
  `Tickers`, `Topics`, and `Content` are unavailable. The source still has no
  training entrypoint. The article bodies,
  returns, manual factors, generated embeddings, baselines, evaluation code,
  sweep histories, and native outputs are absent.
- The central hybrid claim is not implemented in the released model:
  `Model.forward` combines report and asset embeddings but never ingests manual
  financial factors or performs the stated historical-factor pretraining.
- The v2 experiment has no demonstrated code lineage. The current code differs
  from the September 2024 paper-era tree only in `README.md`; all six later
  commits are README-only. It still defaults to
  GPT-3.5-Turbo-1106, and the released metadata ends 2023-11-30 rather than the
  claimed 2024-09-29 endpoint.
- GitHub's complete dated public-fork surface contains 14 accessible forks, 14
  branch refs, no tags, and four unique heads. Every head is either the current
  official head or an official-history ancestor already covered by the complete
  nine-commit audit. The forks add zero unique commits and zero unique blobs, so
  they cannot recover any missing training or empirical-result lineage.

## Version and display integrity

- v1 contains 114 empirical table cells; v2 contains
  162 after adding the 48-cell foundation-model table. These
  are paper displays, not reproduced results.
- 112 of 114 common-position table cells changed.
  Yet 15/16 source raster figures are byte-identical. The unchanged decile plot
  still spans roughly October 2022 to September 2023, not a new v2 final year.
- The v2 paper says three years of news, but its 9-month/3-month/1-year split
  accounts for two years. Several prose percentages use the wrong comparator or
  disagree with displayed values; `paper_improvement_claim_audit.csv` gives the
  arithmetic rather than silently accepting the prose.

## Released-code defects that prevent faithful execution

- The `SKIP` path returns three values while its caller unpacks four.
- The macro note is assigned a formatted instruction prompt instead of an LLM
  response.
- `Model.eval` does not switch dropout/BatchNorm to evaluation mode; the alleged
  best-checkpoint path loads the periodic/latest checkpoint; and seed 42 is
  never applied.
- The paper fixes LLM temperature at 0.2, but the released API calls do not pass
  a temperature. Requirements are unpinned and list `yaml` rather than PyYAML.
- FlagEmbedding 1.2.11 omits its required `peft` dependency. The reconstructed
  environment adds the date-bounded package and substitutes PyYAML for the
  invalid `yaml` requirement. PyTorch 2.4.1 CPU satisfies the README's >=2.0
  instruction but not its contradictory statement that 1.10.1 was tested.

## Native component boundary

- The paper-era source-date cutoff, complete freeze, and clean dependency check
  are tracked. Exact historical versions remain unknown because every author
  requirement is unpinned.
- A supplied-embedding fixture executes the released Chroma add, query, filter,
  and pad paths without loading a model or calling an API.
- A two-run source-faithful probe pins ten files / 1,341,561,506 bytes from the
  immutable BGE commit `d4aa6901d3a41ba39fb536a557fa166f842b0e09` and reconstructs the
  1,901,562-byte metadata index. The model constructs offline and `analysis.py`
  starts deterministically with zero network attempts, but the first record lacks
  its private `news_analysis` JSON and fails on `Tickers` before any LLM call.
  This advances the native entrypoint without inventing article content and earns
  no result credit.
- A controlled six-date/two-asset fixture executes the released report-plus-asset
  embedding forward method with 49 parameters and finite outputs. The audit uses
  a disclosed CUDA no-op and seed 42 on CPU; this is component conformance, not
  training or paper-result credit.
- W&B, Chroma telemetry, model hubs, and outbound HTTP are disabled. No LLM,
  embedding-model, paid-data, or credentialed call is made.

## Evidence boundary

This is a pinned, fail-closed audit and a component-level source inspection. It
does not substitute synthetic news, public price proxies, a newer LLM, or a
freshly invented evaluation pipeline for unavailable native inputs. Doing so
would create an adaptation, not a faithful replication of either paper version.
