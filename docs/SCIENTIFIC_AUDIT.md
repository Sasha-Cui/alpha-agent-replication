# Scientific claim audit

> [!CAUTION]
> **SUPERSEDED / INVALIDATED — DO NOT USE FOR CURRENT CLAIMS OR RESULTS.**
> This legacy document predates the current artifact-audit and fidelity framing and is retained only for provenance. Use the current claim-boundary document (`docs/FIDELITY_AUDIT.md`), the current manuscript (`docs/paper/icaif2026_submission.tex`; built PDF `output/pdf/icaif2026_submission.pdf`), and current fidelity evidence (`paper_runs/submission_evidence/native_fidelity_ledger.csv` and `paper_runs/submission_evidence/artifact_audit/`) instead. Claims, counts, and interpretations below are not authoritative for the current submission.

This page is the shortest path from the paper's claims to the exact code,
tracked evidence, denominators, and interpretation limits. It is written for a
skeptical reader trying to falsify the result.

## Precisely stated story

One-sentence takeaway: the 50 reconstructed strategies often look profitable
against narrow benchmarks, but the broad JKP132 benchmark drives median alpha
below zero, leaves no Holm-adjusted positive result, and links most return paths
to familiar factor families.

The claim is not that all 98 papers are wrong or that their reported returns are
fictitious. The defensible claim is narrower: conditional on these 50
researcher-implemented common-task mappings, the public evidence provides no
familywise-significant incremental alpha beyond the broad factor zoo. The
analysis does not reproduce 50 native agents, identify a causal pretraining
mechanism, or prove that an unavailable source system would earn the same
return.

## Denominators without shorthand

| Number | Unit | Role | Machine-readable evidence |
| ---: | --- | --- | --- |
| 103 | system lineages | Pre-deduplication screen | `literature_review/census_v1/system_registry.csv` |
| 98 | canonical scholarly works | Deduplicated screened corpus | `literature_review/census_v1/primary_record_metadata.csv`; `paper_runs/submission_evidence/replication_scope/work_level_evidence_waterfall.csv` |
| 69 | canonical works | Retained formula-discovery or trading corpus | `paper_runs/submission_evidence/replication_scope/work_level_evidence_waterfall.csv` |
| 40 | canonical works | Retained works with at least one reconstruction | `paper_runs/submission_evidence/replication_scope/work_level_evidence_waterfall.csv` |
| 50 | strategy mappings | Headline benchmark and correlation family | `paper_runs/submission_evidence/replication_scope/mapping_scope_ledger.csv`; `paper_runs/handoff/strategy_result_index.csv` |
| 62 | strategy mappings | Larger mapping audit, including 12 diagnostics from screened-out lineages | `paper_runs/submission_evidence/replication_scope/mapping_scope_ledger.csv` |
| 14 | code attempts | Secondary reproducibility audit, not the performance denominator | `paper_runs/submission_evidence/replication_scope/direct_code_attempt_inventory.csv` |
| 0 | native-agent replications | End-to-end native agents reproduced | `paper_runs/submission_evidence/replication_scope/direct_code_attempt_inventory.csv` |

The 62-to-50 decision is not implicit. Every row is classified in
`paper_runs/submission_evidence/replication_scope/mapping_scope_ledger.csv`
with its screened lineage, F/T decision, original screening rationale,
canonical work when applicable, and negative-evidence boundary. The 12 omitted
rows all come from lineages frozen as `main_FT=N`: four comparator/formula
methods, six benchmarks or audits, and two community repositories. All 12 are
M0 narrative translations; none is silently treated as a failed paper.

The paper-level route is now explicit in
`paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv`.
Of 69 retained works, 18 have reachable public code/artifact snapshots and
must receive native execution or a precise blocker before any proxy is treated
as a secondary diagnostic. The other 51 are paper-only or have inaccessible
artifacts. None is currently claimed as a full paper-only prompt/search/training
reproduction: three support only partial source-grounded components, 24 support
clearly labeled motif proxies, and 24 remain availability-only. See
`docs/EVIDENCE_ROUTE_POLICY.md` for the precedence rule and exact crosswalk.

## Estimand and benchmark ladder

For strategy \(i\), month \(t\), and one-way cost \(c=10\) basis points, the
analyzed return is

\[
r^{\mathrm{net}}_{i,t}
=r^{\mathrm{gross}}_{i,t}-c\,\tau_{i,t},
\]

where \(\tau_{i,t}\) is traded notional. For benchmark rung \(b\), slopes are
estimated using only the preceding 120 months. The broad rung leaves the six
market/FF5/momentum analogues unpenalized and ridge-controls the remaining 127
JKP characteristic returns. The next-month residual and annualized mean are

\[
e^{(b)}_{i,t}
=r^{\mathrm{net}}_{i,t}
-\widehat{\boldsymbol\beta}^{(b)\top}_{i,t-1}\mathbf f^{(b)}_t,
\qquad
\widehat\alpha^{(b)}_i
=12\,T^{-1}\sum_{t=1}^{T}e^{(b)}_{i,t}.
\]

The same 50 strategies, costs, and 126 evaluation months are used at every
rung. HAC standard errors use four lags. The repository reports two-sided
nominal \(p\)-values, Holm-adjusted \(p\)-values across the 50-strategy family,
and a 5,000-replication moving-block maximum-\(|t|\) procedure. The benchmark
ladder is descriptive and post-hoc because mappings and model choices were not
frozen before U.S. outcomes were inspected.

| Benchmark | Median annualized alpha | Positive estimates | Nominal positive | Holm positive |
| --- | ---: | ---: | ---: | ---: |
| CAPM | 9.97% | 44/50 | 28/50 | 6/50 |
| FF3 | 3.17% | 41/50 | 5/50 | 1/50 |
| FF5 + momentum | 2.69% | 41/50 | 7/50 | 2/50 |
| Market + JKP132 | -1.69% | 17/50 | 1/50 | 0/50 |

Source: `benchmark_summary.csv` and `strategy_benchmark_results.csv`, both
hash-pinned by `retained_benchmark_ladder/run_manifest.json`.

## Closest-factor evidence

For each strategy and each JKP characteristic return, the descriptive
correlation is

\[
\rho_{i,k}=\operatorname{Corr}(r^{\mathrm{net}}_{i,t},f^{\mathrm{JKP}}_{k,t}),
\qquad
k_i^*=\arg\max_{1\leq k\leq132}|\rho_{i,k}|.
\]

The current correlation ledger uses all 246 common months from August 2001
through January 2022. This is deliberately reported as a descriptive
return-path match, not an out-of-sample selection statistic. The benchmark
alpha estimates use only the final 126 months. A critic should not substitute
one window for the other.

| Repository label | JKP factor ID | Closest for | Median signed correlation | Direction implied by sign |
| --- | --- | ---: | ---: | --- |
| Betting-against-beta | `betabab_1260d` | 12 | -0.841 | Low-beta payoff relative to the published high-beta orientation |
| 52-week-high proximity | `prc_highprc_252d` | 8 | 0.846 | Near-high orientation |
| Realized volatility | `rvol_21d` | 3 | -0.817 | Low-volatility orientation |
| Idiosyncratic volatility | `ivol_capm_252d` | 3 | -0.778 | Low-idiosyncratic-volatility orientation |
| Quality-minus-junk safety | `qmj_safety` | 3 | 0.771 | Safer-firm orientation |
| 12-1 momentum | `ret_12_1` | 3 | 0.714 | Positive momentum orientation |

These six rows cover 32 of 50 strategies. The ten rows printed in Table 2
cover 39; eleven additional JKP factors are closest for one strategy each.
The labels are repository shorthand for JKP factor identifiers, not quotations
from the 40 source papers. Negative \(\rho\) means exposure opposite to the
published JKP portfolio orientation; it does not mean a negative economic
premium.

Correlation is supporting evidence, not the definition of absorption. The
paper's absorption statement combines the matched benchmark-ladder attenuation,
the disappearance of familywise-adjusted positive alpha, and the concentrated
closest-factor map.

## Claim-to-evidence map

| Claim | Primary evidence | Producing code | Enforced by |
| --- | --- | --- | --- |
| 98/69/40 work waterfall | `work_level_evidence_waterfall.csv` | `build_census_citation_assets.py` | `test_census_citation_assets.py` |
| 62 mappings partition into 50 headline and 12 diagnostic rows | `mapping_scope_ledger.csv` | `build_census_citation_assets.py` | `test_census_citation_assets.py` |
| 50 strategies receive the same four-rung ladder | `strategy_benchmark_results.csv` | `run_retained_benchmark_ladder.py` | `test_retained_benchmark_ladder.py` |
| 0 Holm-positive broad-JKP results | `benchmark_summary.csv` | `run_retained_benchmark_ladder.py` | `test_retained_benchmark_ladder.py` |
| 6,600 strategy-factor correlations | `strategy_jkp_factor_correlations.csv` | `run_retained_benchmark_ladder.py` | `test_retained_benchmark_ladder.py` |
| Top-factor counts and signs | `top_jkp_factor_frequency.csv` | `run_retained_benchmark_ladder.py` | `test_retained_benchmark_ladder.py` |
| 69 retained works have one of three paper evidence routes | `paper_evidence_route_ledger.csv` | `build_paper_evidence_routes.py` | `test_paper_evidence_routes.py` |
| 14 code attempts are secondary and produce 0 native replications | `direct_code_attempt_inventory.csv` | `build_replication_scope_assets.py` | `test_replication_scope_assets.py` |
| Tracked handoff is deterministic | `paper_runs/handoff/` | `build_collaborator_handoff.py` | `validate_submission_package.py` |

Evidence basenames in this table resolve under
`paper_runs/submission_evidence/`; producing code and enforcement tests
resolve under `scripts/` and `tests/`. The denominator table above uses
complete repository-relative paths.

## How to challenge or correct the result

An actionable challenge should identify a `candidate_id` or
`canonical_work_id`, the disputed claim, the exact source or input hash, the
command and environment used, and the expected versus observed value. Strong
challenges include a source-supported alternative mapping, a reproducible
timing or portfolio-construction error, a benchmark-alignment error, a
denominator mismatch, or a multiple-testing error.

The project should correct verified errors publicly, regenerate affected
manifests and tables, describe whether headline conclusions change, and retain
the superseded evidence as labeled provenance. Availability failures must never
be converted into zero returns, and restricted JKP/security-level data must not
be published merely to make the repository look self-contained.
