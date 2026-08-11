# FAMA paper-level replication audit

This package audits the authoritative ACL 2024 paper and its official ACL
Anthology record. It is deliberately fail-closed. Published numbers copied from
the PDF are an inventory, not reproduced evidence.

## Verdict

- **Native FAMA paper results reproduced: 0/65 table cells and 0/38 visible figure markers.**
- No author-linked implementation, data snapshot, model snapshot, filled prompt,
  final mined factor set, search/experience trace, prediction, portfolio path, or
  raw result file was found.
- Appendix D recovers one prompt template, but its required
  `{function_definition}` remains unresolved. It is specification evidence only.
- The existing local FAMA mapping remains M1 motif-level evidence: the paper
  discusses momentum/trend principles, while value, profitability, size, equal
  score weights, monthly deciles, and the tested return stream are
  researcher-supplied.

## Material paper conflicts

- Section 4.1 says the initial Alpha101 pool contains 38 factors; Appendix B
  lists 71 distinct identifiers.
- Equation 7 labels an expression as correlation but omits the Pearson
  denominator square root, changing CSS clustering and CoE matching semantics.
- Algorithm 1 adds every generated factor to `Fi` outside the improvement test,
  contrary to the method narrative.
- The abstract's 0.105 RankICIR gain conflicts with the 0.106 table difference
  and Section 4.4.
- The stated 2020-06-01--2021-01-01 fitting window crosses the paper's declared
  training/validation boundary while being called 10% of training.
- Portfolio construction, cost treatment, result units, and random seeds are not
  specified enough to reconstruct the reported 38.4% AR or 667.2% SR.

## Files

- `official_table_result_conformance.csv`: all 65 numeric performance cells.
- `numeric_configuration_audit.csv`: eight Table 1 training-usage cells.
- `figure_result_inventory.csv`: all 38 visible result markers in Figures 3--4.
- `initial_factor_inventory.csv`: the 71 Appendix B identifiers.
- `paper_internal_consistency_audit.csv`: equation, count, split, algorithm, and
  unit conflicts.
- `method_specification_audit.csv`: exact-replication requirements and blockers.
- `paper_prompt_template.txt`: the recovered Appendix D template.
- `source_search_inventory.csv` and `source_provenance.json`: pinned source and
  negative repository-search evidence.
- `native_execution.json` and `manifest.json`: machine-readable evidence boundary.
