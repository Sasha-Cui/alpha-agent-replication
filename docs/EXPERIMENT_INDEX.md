# Experiment Index

This index maps each substantive result to its runner and frozen output. “Full
rerun” means recomputing security-level portfolios and therefore may require
authorized external data. “Compact rebuild” means regenerating a tracked table
from other tracked aggregate artifacts.

| Stage | Status and denominator | Main code | Primary tracked outputs | Full-rerun inputs | Interpretation boundary |
| --- | --- | --- | --- | --- | --- |
| Literature census | Frozen: 103 lineages, 98 distinct works, 69 retained operational works | `scripts/build_paper_registry.py`, `scripts/build_census_citation_assets.py`, `scripts/refresh_census_primary_record_metadata.py` | `literature_review/census_v1/`, `docs/full_corpus_bibliography.md`, `paper_runs/submission_evidence/replication_scope/work_level_evidence_waterfall.csv` | Public metadata/network access for refresh | Cutoff-bounded systematic screen, not a complete universe |
| Static artifact audit | Frozen: 103 lineage rows | `scripts/build_artifact_audit.py` | `paper_runs/submission_evidence/artifact_audit/` | Network access; optional third-party repositories | Static packaging/reachability evidence, not native execution |
| Direct-code scope | Frozen: 14 targeted attempts | `scripts/build_native_fidelity_ledger.py`, `scripts/build_replication_scope_assets.py` | `paper_runs/submission_evidence/native_fidelity_ledger.csv`, `paper_runs/submission_evidence/replication_scope/direct_code_attempt_inventory.csv` | Separately acquired third-party artifacts | 0 native replications; 1 released-code component adaptation |
| Mapping and attribution audit | Frozen: 62 mappings, including 50 from 40 retained papers and 12 screened-out diagnostics | `scripts/build_mapping_audit.py`, `scripts/build_census_citation_assets.py`, `scripts/build_source_anchor_review_packet.py` | `paper_runs/submission_evidence/mapping_audit/`, `replication_scope/mapping_scope_ledger.csv` | Source papers for independent re-review | Row-level scope reasons are public; mappings were not outcome-blind and lacked an independent second coder |
| Source-paper benchmark audit | Current: 40 papers; 38 verified full texts and 2 unresolved | `scripts/analyze_source_benchmarks.py` | `paper_runs/submission_evidence/source_benchmark_audit/` | Source papers for independent citation-level review | Descriptive coding; partial records cannot support negative evidence |
| U.S. common-task portfolios | Frozen: 62 candidate paths | `scripts/run_submission_evidence.py`, `src/alpha_evolve/submission_analysis.py` | `paper_runs/submission_evidence/usa_retrospective_corrected/` compact summaries | Authorized JKP security-level panel | Retrospective common-task diagnostic; monthly matrices are not published |
| Missing-return stress | Frozen: same 62 candidates | `scripts/run_usa_missing_return_sensitivity.py` | `paper_runs/submission_evidence/usa_missing_return_sensitivity/` | Ignored frozen monthly candidate matrix | Position-adverse unit move is a severe stress, not a delisting-return estimator |
| Broad JKP diagnostic | Frozen: post-hoc 133-return model | `scripts/run_broad_jkp_crossfit.py` | `paper_runs/submission_evidence/usa_broad_jkp_crossfit/` | Authorized factor panel plus ignored candidate monthly matrix | Post-hoc spanning diagnostic, not confirmatory inference |
| Matched retained-strategy ladder | Frozen: 50 strategies, 40 papers, 4 benchmark rungs | `scripts/run_retained_benchmark_ladder.py` | `paper_runs/submission_evidence/retained_benchmark_ladder/` | Authorized factor panel plus ignored candidate monthly matrix | Same 126 evaluation months and costs; 0 native-agent replications |
| Strategy-factor correlations | Frozen: 6,600 strategy-factor pairs and top-five table | `scripts/run_retained_benchmark_ladder.py` | `strategy_jkp_factor_correlations.csv`, `strategy_top_jkp_factors.csv`, `top_jkp_factor_frequency.csv` | Authorized factor panel plus ignored candidate monthly matrix | Correlation/spanning evidence does not identify a pretraining mechanism |
| International extension | Excluded from performance inference after plausibility failure | `scripts/run_submission_evidence.py`, `scripts/diagnose_international_failures.py`, `scripts/run_fixed_calendar_diagnostics.py` | `g7_ex_us_corrected/` summaries, `international_failure_forensics/`, `fixed_calendar_diagnostics/` | Authorized G7 security-level panels | 40 limited-liability events require independent data/implementation validation |
| Collaborator index | Current: 50 rows, 58 columns | `scripts/build_collaborator_handoff.py` | `paper_runs/handoff/` | None; joins tracked aggregates | Navigation artifact, not a new empirical run |
| Authorized monthly collaborator bundle | On-demand: 50 retained strategies, same-universe six-factor panel, external market-plus-JKP132 panel, and four-rung monthly reconstructions | `scripts/build_authorized_collaborator_bundle.py` | Generated outside Git; see `docs/AUTHORIZED_COLLABORATOR_BUNDLE.md` | Authorized aggregate candidate/factor matrices and benchmark reconstruction run | Access-gated inspection artifact; no security-level rows and no redistribution grant |
| Paper assets and PDF | Current: seven-page anonymous ICAIF submission; 62/62 fresh-clone artifact checks and 71/71 explicit release-build checks pass | `scripts/build_icaif2026_submission_assets.py`, `scripts/build_icaif2026_submission.py`, `scripts/validate_submission_package.py` | `docs/paper/`, `output/pdf/icaif2026_submission.pdf`, `docs/VALIDATION_STATUS.md` | Poppler for tracked-PDF validation; TeX Live plus Poppler for release build | Default validation has no dependency on ignored LaTeX residue; release mode requires an explicit build log |

## Compact review sequence

1. Read `paper_runs/handoff/strategy_result_index.csv` and its manifest.
2. Verify the 50 formulas and attribution boundaries in
   `paper_runs/submission_evidence/mapping_audit/mapping_audit.csv`.
3. Inspect the 13 closest source mappings in
   `docs/source_anchor_review_packet.md` and its CSV.
4. Inspect the 14 direct attempts in
   `paper_runs/submission_evidence/replication_scope/direct_code_attempt_inventory.csv`.
5. Review the 40-paper benchmark coding and the two unresolved records in
   `paper_runs/submission_evidence/source_benchmark_audit/`.
6. Check the four-rung result table in
   `retained_benchmark_ladder/strategy_benchmark_results.csv` and the complete
   6,600-row factor-correlation ledger.
7. Run the test suite and rebuild the handoff index.
8. Read the canonical paper only after the audit tables, because the tables
   encode the provenance qualifications that prevent overclaiming.

## Commands that do not require restricted data

```bash
python -m pytest -q
python scripts/build_collaborator_handoff.py
python scripts/build_source_anchor_review_packet.py
python scripts/build_replication_scope_assets.py
python scripts/build_icaif2026_submission_assets.py
```

Before rerunning a frozen empirical stage, inspect its `run_manifest.json` and
the analysis lock. Do not silently overwrite frozen outputs with a different
input panel, calendar, cost assumption, mapping set, or factor definition.
The outcome-blind confirmatory repair for mapping discretion is specified in
[`INDEPENDENT_MAPPING_REVIEW_PLAN.md`](INDEPENDENT_MAPPING_REVIEW_PLAN.md).
