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
| `replication_scope/mapping_scope_ledger.csv` | 62 | 14 | Row-level reconciliation of the 50 headline mappings and 12 excluded diagnostics |
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

## Included source papers

The repository includes the 45 downloaded source-paper PDFs under
`literature_review/papers/`. Their filenames, download statuses, and byte counts
are recorded in `literature_review/download_log.csv`. Canonical primary records
are in `literature_review/census_v1/primary_record_metadata.csv`. These
third-party papers retain their own licenses and should not be interpreted as
project-authored artifacts.

## Deliberately not included

| Excluded material | Reason | How a collaborator proceeds |
| --- | --- | --- |
| JKP security-level characteristic/return panels | Licensed research data; not granted for redistribution | Obtain authorized access and set `ALPHA_EVOLVE_JKP_ROOT` / `ALPHA_EVOLVE_JKP_USA` |
| JKP factor-panel time series | User explicitly does not need this exported; derived results are sufficient for initial handoff | Rebuild locally from authorized inputs or set `ALPHA_EVOLVE_FACTOR_PANEL` |
| Monthly candidate and factor reconstruction matrices | High-volume, reproducible intermediates derived from restricted inputs | Run the tracked portfolio builders; verify input/output hashes in manifests |
| `external_repos/` and `external_repos_code_links/` | Large third-party clones with independent licenses and mutable upstream histories | Use the artifact audit's URLs, revisions, license fields, and blockers to acquire allowed versions |
| Virtual environments, package caches, logs, and scratch | Machine-specific or regenerable | Install from `pyproject.toml`; use `environment.toml` on Bouchet |
| Alternate compiled manuscript versions | Avoid ambiguity during handoff | Use the one canonical PDF and its matching TeX source |

No JKP observations, monthly strategy-return series, or security identifiers are
present in `paper_runs/handoff/strategy_result_index.csv`. Closest-factor names,
correlations, alpha estimates, and inference flags are derived aggregate
statistics already contained in the frozen research outputs.

## Obtaining JKP inputs for an end-to-end rerun

The compact public artifacts can be audited without licensed data. Rebuilding
the security-level portfolios requires the JKP stock-level monthly panel; this
input is intentionally not redistributed here.

1. Download public JKP factor returns from the official
   [JKP data library](https://www.jkpfactors.com/data) when only the factor
   benchmarks are needed.
2. For the headline security-level reconstruction, obtain authorized access to
   the monthly JKP characteristic/return panel. The official
   [JKP WRDS guide](https://www.jkpfactors.com/jkp-wrds-guide) documents the
   WRDS route and its CRSP/Compustat prerequisites. An equivalent local build
   from the official JKP code and appropriately licensed source data is also
   acceptable.
3. Preserve the acquired files read-only and record their SHA-256 hashes. A
   conventional local layout is:

   ```text
   /path/to/jkp-data/data/processed/characteristics/USA.parquet
   ```

4. Point the runners to the authorized files rather than copying them into the
   repository:

   ```bash
   export ALPHA_EVOLVE_JKP_ROOT=/path/to/jkp-data
   export ALPHA_EVOLVE_JKP_USA=/path/to/jkp-data/data/processed/characteristics/USA.parquet
   export ALPHA_EVOLVE_FACTOR_PANEL=/path/to/benchmark_factor_panel.csv
   ```

5. Compare the acquired-input hashes and all regenerated-output hashes with the
   applicable `run_manifest.json` and analysis lock before interpreting any
   numerical difference. Follow `docs/EXPERIMENT_INDEX.md` for the runner and
   output associated with each empirical stage.

The website's factor-return downloads are sufficient to audit or rebuild factor
benchmarks, but they do not replace the licensed stock-level panel needed to
reconstruct the 50 portfolios. With that authorized panel available, the
tracked runners can regenerate the omitted monthly matrices and compact result
files. The public repository therefore separates *redistributable audit
artifacts* from *access-dependent end-to-end computation*; it does not claim
that licensed observations are bundled in a fresh clone.

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
a2b95524a843e57fe3d8ed6b36b8c22eb6e96d85bebe0c80563c740f06dfc0ee  docs/paper/icaif2026_submission.tex
529aa46ecac2fcf4bd1c52946a68e03e647bf6faff142587cbedf1116d8dee93  output/pdf/icaif2026_submission.pdf
```

The handoff manifest records SHA-256 hashes for the mapping audit, matched
benchmark comparison, closest-factor diagnostics, and generated 50-row index.

## Licensing boundary

Project code and tests are Apache-2.0. Project-authored documentation,
manuscript material, figures, tables, and registry annotations are CC BY 4.0.
Third-party papers, repositories, software, and market data retain their own
terms. See `LICENSES/README.md` and `LICENSES/THIRD_PARTY.md` before sharing any
locally acquired input beyond the repository.
