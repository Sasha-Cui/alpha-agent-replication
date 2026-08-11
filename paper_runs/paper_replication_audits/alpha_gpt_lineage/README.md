# Alpha-GPT lineage paper/source replication audit

This package audits Alpha-GPT arXiv v1 and v2, the EMNLP 2025 authoritative
final, Alpha-GPT 2.0 v1, all three official TeX archives, four published
formula examples, ten repository searches, and the prominent unaffiliated
`parthmodi152/alpha-gpt` project. The audit is fail-closed: document rebuilds,
published figures, and a community implementation do not count as native
Alpha-GPT executions.

## Verdict

- **Alpha-GPT v1 native results reproduced: 0/20 displayed numeric cells and
  0/3 backtest line series.**
- **Alpha-GPT v2 / ACL-final native results reproduced: 0/47 displayed numeric
  cells and 0/2 search-enhancement line series.**
- **Alpha-GPT 2.0 has no empirical result denominator:** it is a four-page
  document explicitly marked `Draft. Work in progress` and contains no
  experiment.
- All source documents rebuild to the correct page counts. Extracted-token
  multiset Jaccard is 99.9000% for v1 and
  99.7583% for Alpha-GPT 2.0 after one
  current-TeX compatibility repair. The arXiv-v2 source rebuild is
  96.3649% against arXiv v2 and
  91.4431% against the separately produced ACL
  final; this is strong document evidence, not experiment reproduction.
- Of four exact formula examples, three pass ordinary arity checks and execute
  under an explicitly non-native conventional operator stub. The published
  Flow of Funds expression does not: `div` receives one argument and
  `cwise_mul` receives three, despite the paper's syntax/semantic-validation
  premise.
- Ten complete GitHub repository searches find no author-linked code or data.
  The broad search finds `parthmodi152/alpha-gpt`, but it is an acknowledged
  paper-inspired, work-in-progress project by a non-author. Its graph stops
  after LLM code generation and contains no GP, backtest, market data, or paper
  results.
- Both local strategies remain M0 narrative translations. Their JKP
  characteristics, signs, monthly U.S. universe, decile construction, weights,
  and returns were not generated or tested by either paper.

## Material blockers

- No author-linked implementation, data snapshot, universe membership, full
  prompts, retrieved memory, generated alpha set, GP state, model requests,
  portfolio evaluator, seeds, raw arrays, or runtime lock is released.
- V1 Table 1 says seven trading ideas but contains six. Its 12 IC cells and the
  three interaction curves have no underlying runs.
- The 2025 rewrite changes GPT-3.5/text-ada to Llama3/BGE-M3 and changes the
  data description from inter-day to intraday while carrying over qualitative
  assets. Version-specific provenance is therefore essential.
- The human comparison omits the item count, judge prompt, ordering, ties, and
  uncertainty. The interaction/search averages omit raw ICs, splits, and
  repeats.
- JoinQuant and WorldQuant claims have no immutable leaderboard/team record,
  generated alpha list, input snapshot, evaluator, or result export.
- Alpha-GPT 2.0's archive contains unused Alpha-GPT 1 experimental files; they
  are not rendered by `main.tex` and receive no 2.0 evidence credit.

## Files

- `source_provenance.json`, `source_file_inventory.csv`, and
  `source_build_audit.csv`: pinned original records, 108 source members, and
  document rebuild comparisons.
- `version_lineage_audit.csv`: model, scope, and result changes across four
  publication records.
- `displayed_result_conformance.csv`: every displayed numeric cell and plotted
  result object in v1 and the ACL-final study.
- `published_formula_conformance.csv`: exact parse, arity, and conditional-stub
  checks for four showcased expressions.
- `prompt_inventory.csv`, `method_specification_audit.csv`,
  `paper_internal_consistency_audit.csv`, and `claim_audit.csv`: missing
  specifications, conflicts, and fail-closed claims.
- `community_source_inventory.csv`, `community_method_conformance.csv`, and
  `source_search_inventory.csv`: non-native source-search evidence.
- `local_mapping_conformance.csv`, `native_execution.json`, and
  `manifest.json`: local M0 boundaries and machine-readable verdict.
