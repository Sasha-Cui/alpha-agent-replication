# LLMFactor paper/source replication audit

This package audits the original arXiv v1 paper, the ACL 2024 authoritative
record, the official TeX archive, every displayed result cell, the disclosed
English/Chinese prompt skeletons, the ACC/MCC equations, six complete GitHub
repository searches, and two prominent later community implementations. It is
fail-closed: rebuilding the paper, rendering a prompt, evaluating a metric on a
fixture, or running unaffiliated code does not reproduce an LLMFactor result.

## Honest verdict

- **Native LLMFactor results reproduced: 0/82 displayed native result cells.**
- **All displayed experimental results reproduced: 0/206 cells**, including
  124 baselines that also lack released run inputs and predictions.
- The official nine-file source archive rebuilds without patching to 12 pages.
  Extracted-token multiset Jaccard is 99.9136%
  against arXiv v1 and 96.4103% against the
  ACL final. This is strong document provenance, not experiment reproduction.
- Three English prompt skeletons render deterministically on a declared fixture,
  and the published ACC/MCC formulas pass a deterministic confusion-matrix
  fixture. These are narrow conditional component checks only: no LLM was
  invoked and no paper request or output was replayed.
- Six complete repository searches find no author-linked code or data. The two
  relevant community repositories were created in 2025 by non-authors and
  materially change models, prompts, data paths, or windows. Neither reproduces
  a published cell.
- The local `paper_llmfactor_explainable_price_news` strategy remains an M0
  narrative translation. It is a monthly characteristic portfolio with no
  news, prompts, relation/factor extraction, daily labels, or paper metrics.

## Material blockers and paper-level ambiguities

- No author implementation, immutable API request/response log, exact data
  snapshot, split, preprocessing, universe membership, stock matcher, response
  parser, random seed, repeat count, predictions, confusion matrices, or raw
  result arrays is released.
- The paper itself states that variable LLM responses prevent guaranteed exact
  reproduction, but supplies no deterministic replay protocol.
- Four Table 3 cells are not recoverable by rounding the displayed Table 2
  inputs; hidden-precision values could explain this, but those values are not
  released. The stated MCC layer shares likewise do not exactly follow from the
  displayed ablation cells.
- The unqualified superiority wording fails for EDT accuracy: the EDT baseline
  reports 75.67, versus a best LLMFactor value of 60.83.
- Appendix claims about the best English/Chinese factor templates are not true
  across every displayed model/metric pair.
- Equal-price labels, multi-company matching, target alignment, and parsing of
  free-form rise/fall responses remain operationally undefined.

## Files

- `source_provenance.json`, `source_file_inventory.csv`, and
  `source_build_audit.csv`: pinned paper/source records and document rebuilds.
- `displayed_result_conformance.csv`: all 206 displayed cells, with the 82
  native LLMFactor cells distinguished from 124 baseline cells.
- `configuration_inventory.csv`, `prompt_template_conformance.csv`,
  `prompt_component_execution.csv`, and `metric_component_execution.csv`:
  disclosed settings and narrow executable components.
- `method_specification_audit.csv`, `paper_internal_consistency_audit.csv`, and
  `claim_audit.csv`: missing specifications, numerical lineage, and claims.
- `source_search_inventory.csv`, `community_source_inventory.csv`,
  `community_data_inventory.csv`, and `community_method_conformance.csv`:
  public-source evidence with zero native credit.
- `local_mapping_conformance.csv`, `native_execution.json`, and `manifest.json`:
  the local proxy boundary and machine-readable verdict.
