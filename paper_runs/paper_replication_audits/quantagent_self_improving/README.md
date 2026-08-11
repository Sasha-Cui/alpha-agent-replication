# QuantAgent (self-improving LLM) paper/source replication audit

This package audits arXiv:2402.03755v1, its 15-page PDF, the official TeX
archive, all four published Python listings, and the public repository-search
surface. It is fail-closed: rebuilding a document or executing one isolated
formula with a stub is not a reconstruction of QuantAgent or its results.

## Verdict

- **Native QuantAgent results reproduced: 0/17 plotted line series and 0/400 heatmap cells.**
- **Document fidelity is high:** the official source rebuilds to 15 pages at
  99.9304% extracted-token multiset
  Jaccard against the arXiv PDF.
- The archive releases no native pipeline, idea-factor framework, prompts,
  500-stock membership, 2023 market snapshot, generated signal library,
  knowledge base, model predictions, result arrays, or immutable GPT requests.
- Of four published Python listings, three compile. Only the standalone
  VolatilityBreakout formula executes after stubbing the unreleased Factor base;
  both rejected Three Soldiers versions raise, and the mentor-passed V3 does
  not parse.
- Eight complete GitHub repository searches found no candidate repository. The
  popular Y-Research-SBU/QuantAgent repository belongs to a distinct 2025 HFT
  paper with different authors, data, task, and architecture.
- The two legacy monthly JKP candidates remain M0 narrative translations. A
  separate literal ATR14 component remains C-conditional because cadence,
  universe, and portfolio construction are researcher adaptations.

## Material blockers and conflicts

- Algorithm 1 computes `score` but tests undefined `r`; the outer-loop
  pseudocode fixes one problem while the experiment says ideas are resampled.
- The published v1/v2 Three Soldiers code mixes rolling windows with full
  histories. The printed mentor-passed V3 has malformed indexing, lowercase
  `false`, a missing bracket, and a stray LaTeX terminator.
- The breakout code shifts an already previous-close field, yielding a two-bar
  lag. V3 assigns a large positive volume ratio when volume is *not* increasing.
- The paper says significant performance differences are not apparent, then
  treats the blue curves as evidence of effectiveness without uncertainty or
  tests.
- The data split, future-return horizon, IC arrays, portfolio/Sharpe mechanics,
  XGBoost specification, prompts, KB/retrieval state, seeds, and package/runtime
  snapshot are absent.
- The end-to-end sublinear-in-KT theorem delegates key results and does not
  state rates or transfer conditions sufficient to reconstruct its conclusion.

## Files

- `source_file_inventory.csv`: all 44 source members and hashes.
- `source_build_audit.json`: 15-page document rebuild/text conformance.
- `published_code_conformance.csv`: exact compile/runtime status of four listings.
- `displayed_result_conformance.csv`: 17 plotted series and four 10x10 matrices.
- `prompt_inventory.csv`: one printed request and eight missing runtime prompts.
- `method_specification_audit.csv`: method-level replication requirements.
- `paper_internal_consistency_audit.csv`: code, algorithm, empirical, and theory conflicts.
- `claim_audit.csv`: fail-closed support status for central claims.
- `local_mapping_conformance.csv`: M0 and C-conditional local evidence boundaries.
- `source_search_inventory.csv` and `same_name_nonmatch.csv`: source-search provenance.
- `source_provenance.json`, `native_execution.json`, and `manifest.json`: machine-readable boundaries.
