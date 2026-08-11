# AAPM paper/source replication audit

This package audits both official arXiv versions, both source bundles, the
paper-era and current official GitHub states, every released file, all
65,733 metadata records, 114 v1 table cells,
162 v2 table cells, and 54 quantitative figure units.

## Honest verdict

- **End-to-end AAPM result cells reproduced: 0/162.** No native
  checkpoint, prediction array, portfolio-return series, baseline output, or
  table-valued result is released.
- The official repository is useful component code, not an executable paper
  replication. Five Python files compile, but `analysis.py` is blocked before
  analysis and `model.py` has no training entrypoint. The article bodies,
  returns, manual factors, generated embeddings, baselines, evaluation code,
  sweep histories, and native outputs are absent.
- The central hybrid claim is not implemented in the released model:
  `Model.forward` combines report and asset embeddings but never ingests manual
  financial factors or performs the stated historical-factor pretraining.
- The v2 experiment has no demonstrated code lineage. The current code differs
  from the September 2024 paper-era tree only in `README.md`, still defaults to
  GPT-3.5-Turbo-1106, and the released metadata ends 2023-11-30 rather than the
  claimed 2024-09-29 endpoint.

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

## Evidence boundary

This is a pinned, fail-closed audit and a component-level source inspection. It
does not substitute synthetic news, public price proxies, a newer LLM, or a
freshly invented evaluation pipeline for unavailable native inputs. Doing so
would create an adaptation, not a faithful replication of either paper version.
