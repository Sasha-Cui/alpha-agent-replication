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
| Strict legacy proxy audit | Current: 50 mappings; A0/B0/C15/D33/U2 | `scripts/build_strict_proxy_fidelity_audit.py` | `paper_runs/submission_evidence/strict_proxy_fidelity_audit/` | Frozen tracked candidate registry | Legacy mappings are construction diagnostics only; no paper- or agent-level performance inference |
| Primary faithful component census | Current: 3/3 strict grade B (100%) from one pinned source release | `scripts/run_faithful_component_replications.py`, `scripts/check_upstream_conformance.py`, `scripts/validate_faithful_component_replications.py`, `scripts/analyze_fidelity_formula_components.py` | `paper_runs/faithful_component_replications/` | Authorized JKP U.S. panel and factor panel; optional network source-hash check | Exhaustive valid-seed census with exact released expressions, DSL semantics, missing-pair rule, returns, and quintile evaluator; cadence/universe/horizon adapt; exact-source synthetic conformance passes and D07 owner attestation is complete (3/3); no native system |
| Mixed-fidelity formula diagnostic | Non-primary: 12 formula components from 4 sources | `scripts/run_fidelity_formula_components.py`, `scripts/analyze_fidelity_formula_components.py` | `paper_runs/fidelity_formula_components/` | Authorized JKP U.S. panel and factor panel | QuantEvolver rows are exact B; EFS, Alpha-Jungle, and QuantAgent are conditional and excluded from the 100% denominator |
| GuruAgents prompt-decision replay | Current: 190 cells, 24 costed paths; 12 paths with 33 matched factor months | `scripts/run_guruagents_full_replay.py`, `scripts/evaluate_guruagents_prompt_replay_performance.py` | `paper_runs/prompt_replay/guruagents/`, `runs/prompt_replay/guruagents/` | Archived observations, compiled Nasdaq universe, current OpenRouter endpoint | Current-endpoint decision-component replay, not end-to-end source-system replication |
| Published-result conformance audits | Current: GuruAgents Table 1, Automate Strategy Finding Tables 2/4, CryptoTrade Tables 2--4, FinMem Tables 2--5, MASS Tables 1--4, AlphaQuanter Tables 5--8/10--14, QuantHarness Tables 1--2 plus benchmark metadata, ContestTrade Tables 1--3 plus contest-source reachability, AlphaMemo Tables 2--9 plus a native synthetic component, and AlphaAgent Tables 1--2 plus 26 non-table claims and post-paper source/data provenance | `scripts/audit_guruagents_paper_table.py`, `scripts/audit_automate_strategy_paper.py`, `scripts/audit_cryptotrade_paper.py`, `scripts/audit_finmem_paper.py`, `scripts/audit_mass_paper.py`, `scripts/audit_alphaquanter_paper.py`, `scripts/audit_quantharness_paper.py`, `scripts/audit_contesttrade_paper.py`, `scripts/audit_alphamemo_paper.py`, `scripts/audit_alphaagent_paper.py` | `paper_runs/prompt_replay/guruagents/paper_table_conformance/`, `paper_runs/paper_replication_audits/` | Pinned official papers and public source workbooks/code/data | Fail-closed paper-level checks; missing native outputs remain unverifiable and component evidence is not promoted to full-paper replication |
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
| Paper assets and PDF | Current anonymous ICAIF submission; page count and checks are determined by the release validators | `scripts/build_icaif2026_submission_assets.py`, `scripts/build_icaif2026_submission.py`, `scripts/validate_submission_package.py` | `docs/paper/`, `output/pdf/icaif2026_submission.pdf`, `docs/VALIDATION_STATUS.md` | Poppler for tracked-PDF validation; TeX Live plus Poppler for release build | Maximum eight total pages; release mode requires an explicit build log |

## Compact review sequence

1. Read `docs/FIDELITY_AUDIT.md` for the current claim boundary.
2. Verify the 50-row A/B/C/D/U ledger and manifest in
   `paper_runs/submission_evidence/strict_proxy_fidelity_audit/`.
3. Run the 100% gate and inspect the three-row primary ledger, source pins, and
   attribution under `paper_runs/faithful_component_replications/`.
4. Treat the 12-row `paper_runs/fidelity_formula_components/` package only as a
   mixed-fidelity diagnostic outside the primary denominator.
5. Inspect the GuruAgents replay manifest, holdings, paths, and attribution in
   `paper_runs/prompt_replay/guruagents/performance/`.
6. Inspect the fail-closed published-result audits under
   `paper_runs/paper_replication_audits/` and the GuruAgents Table 1 audit.
7. Review the native-fidelity, artifact, and direct-attempt ledgers for the
   broader public-evidence boundary.
8. Use the 50-strategy ladder and 6,600 correlations only as a legacy
   construction diagnostic.
9. Run the test suite and release validators.
10. Read the canonical paper and confirm its claims match these ledgers.

## Commands that do not require restricted data

```bash
python -m pytest -q
python scripts/validate_faithful_component_replications.py
python scripts/build_strict_proxy_fidelity_audit.py
python scripts/build_collaborator_handoff.py
python scripts/build_source_anchor_review_packet.py
python scripts/build_replication_scope_assets.py
python scripts/build_icaif2026_submission_assets.py
python scripts/audit_guruagents_paper_table.py
python scripts/audit_automate_strategy_paper.py
python scripts/audit_cryptotrade_paper.py
python scripts/audit_finmem_paper.py
python scripts/audit_mass_paper.py
python scripts/audit_alphaquanter_paper.py
python scripts/audit_quantharness_paper.py
python scripts/audit_contesttrade_paper.py
python scripts/audit_alphamemo_paper.py
```

Before rerunning a frozen empirical stage, inspect its `run_manifest.json` and
the analysis lock. Do not silently overwrite frozen outputs with a different
input panel, calendar, cost assumption, mapping set, or factor definition.
The outcome-blind confirmatory repair for mapping discretion is specified in
[`INDEPENDENT_MAPPING_REVIEW_PLAN.md`](INDEPENDENT_MAPPING_REVIEW_PLAN.md).
