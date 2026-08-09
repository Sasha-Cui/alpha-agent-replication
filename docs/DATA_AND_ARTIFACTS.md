# Data and Artifact Guide

The repository publishes enough compact evidence to audit the numerical claims
without redistributing licensed research data or mirroring third-party
repositories. This document states exactly what a GitHub collaborator receives
and what must be acquired or regenerated separately.

## Included compact empirical artifacts

| Artifact | Rows | Columns | Purpose |
| --- | ---: | ---: | --- |
| `paper_runs/handoff/strategy_result_index.csv` | 50 | 58 | Single collaborator-facing join of provenance and benchmark results |
| `submission_evidence/artifact_audit/artifact_audit.csv` | 103 | 19 | Static repository/release availability audit |
| `submission_evidence/mapping_audit/mapping_audit.csv` | 62 | 31 | Formula, scope, support, discretion, and attribution ledger |
| `mapping_audit/source_anchor_review_packet.csv` | 13 | 13 | Page-anchored review of the closest source-supported components |
| `replication_scope/direct_code_attempt_inventory.csv` | 14 | 12 | Native/code-attempt blockers and outcomes |
| `replication_scope/work_level_evidence_waterfall.csv` | 98 | 12 | Distinct-work screening and empirical role |
| `source_benchmark_audit/source_benchmark_audit.csv` | 40 | 8 | Full-text access status and original-paper benchmark coding |
| `source_benchmark_audit/strategy_source_benchmark_results.csv` | 50 | 50 | Source benchmark coding joined to the matched strategy ladder |
| `usa_retrospective_corrected/candidate_primary_results.csv` | 62 | 38 | Compact U.S. primary regression and inference results |
| `retained_benchmark_ladder/strategy_benchmark_results.csv` | 200 | 33 | 50 strategies by four matched benchmark specifications |
| `retained_benchmark_ladder/benchmark_residuals.csv` | 504 | 52 | Evaluation-month residual matrix used for ladder summaries |
| `retained_benchmark_ladder/strategy_jkp_factor_correlations.csv` | 6,600 | 13 | Derived strategy-factor correlation ledger |
| `retained_benchmark_ladder/strategy_top_jkp_factors.csv` | 250 | 13 | Five closest derived factors per strategy |
| `international_failure_forensics/failure_event_forensics.csv` | 40 | 36 | Forensic decomposition of international plausibility failures |

Paths in the table are relative to `paper_runs/` when the prefix is omitted.
The repository also contains compact cost curves, HAC/block sensitivities,
multiplicity tables, turnover summaries, missing-return diagnostics, country
summaries, figures, generated TeX macros, and JSON manifests.

## Deliberately not included

| Excluded material | Reason | How a collaborator proceeds |
| --- | --- | --- |
| JKP security-level characteristic/return panels | Licensed research data; not granted for redistribution | Obtain authorized access and set `ALPHA_EVOLVE_JKP_ROOT` / `ALPHA_EVOLVE_JKP_USA` |
| JKP factor-panel time series | User explicitly does not need this exported; derived results are sufficient for initial handoff | Rebuild locally from authorized inputs or set `ALPHA_EVOLVE_FACTOR_PANEL` |
| Monthly candidate and factor reconstruction matrices | High-volume, reproducible intermediates derived from restricted inputs | Run the tracked portfolio builders; verify input/output hashes in manifests |
| `external_repos/` and `external_repos_code_links/` | Large third-party clones with independent licenses and mutable upstream histories | Use the artifact audit's URLs, revisions, license fields, and blockers to acquire allowed versions |
| Downloaded paper PDFs | Copyright and size | Use canonical bibliography, DOI/arXiv/ACL/OpenReview URLs, and source locators |
| Virtual environments, package caches, logs, and scratch | Machine-specific or regenerable | Install from `pyproject.toml`; use `environment.toml` on Bouchet |
| Alternate compiled manuscript versions | Avoid ambiguity during handoff | Use the one canonical PDF and its matching TeX source |

No JKP observations, monthly strategy-return series, or security identifiers are
present in `paper_runs/handoff/strategy_result_index.csv`. Closest-factor names,
correlations, alpha estimates, and inference flags are derived aggregate
statistics already contained in the frozen research outputs.

## Integrity and regeneration

Every counted run directory contains a manifest or is covered by the analysis
lock. The collaborator index adds a second compact hash layer over its three
tracked inputs.

```bash
python scripts/build_collaborator_handoff.py
git diff --exit-code -- paper_runs/handoff
sha256sum docs/paper/icaif2026_submission.tex
sha256sum output/pdf/icaif2026_submission.pdf
```

Expected canonical hashes:

```text
656bc442f93ea74de92434883dbdacc3711328ce12ceaa625c5503813dd14d6c  docs/paper/icaif2026_submission.tex
311cd1f799a70fe0208a7e3f7ce410c54bd9af9a749fe9605bec94dab6af8b35  output/pdf/icaif2026_submission.pdf
```

The handoff manifest records SHA-256 hashes for the mapping audit, matched
benchmark comparison, closest-factor diagnostics, and generated 50-row index.

## Licensing boundary

Project code and tests are Apache-2.0. Project-authored documentation,
manuscript material, figures, tables, and registry annotations are CC BY 4.0.
Third-party papers, repositories, software, and market data retain their own
terms. See `LICENSES/README.md` and `LICENSES/THIRD_PARTY.md` before sharing any
locally acquired input beyond the repository.
