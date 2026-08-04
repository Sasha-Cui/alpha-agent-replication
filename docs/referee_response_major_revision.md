# Response to referee: major revision

We thank the referee for identifying a genuine mismatch between the earlier title and the estimand. The revision changes the paper's intellectual claim, adds two empirical audits, and makes the aggregate evidence inspectable. We do not treat unresolved concerns as if they had been solved: mapping was not outcome-blind, no independent second coder was used, and the broad bootstrap is conditional on an already-estimated fitting path. These facts are now prominent.

## 1. Title and headline conclusion

The title is now **“Does Public Evidence Support Financial-Agent Alpha Claims? An Artifact Audit and Historical Spanning Test.”** The abstract and conclusion state that the design does not test whether agents as a class can discover alpha. The direct performance denominator is now 0 of 1 testable code-backed adaptation; the other 13 attempts are explicitly non-evaluable evidence failures.

## 2. Mechanism-mapping discretion

We added a formal good-faith reconstruction protocol and `mapping_audit.csv`, a 62-row ledger containing every source, formula, portfolio rule, source-support assessment, benefit-of-the-doubt choice, empirical role, anti-strawman status, negative-evidence boundary, omitted native component, freeze timestamp/hash, outcome-blindness field, second-coder field, and existing alternative-mapping status. The protocol requires a source claim card; prioritizes released rules over examples and narrative; preserves supported ingredients, signs, lags, and constraints; implements ambiguity favorably; codes reasonable variants rather than selecting them with returns; and requires outcome-blind fidelity review in future applications.

We apply a source-protection rule to the current retrospective family. Thirteen released-expression, named-rule, or example-supported mappings are source-grounded component tests. Their median U.S. alpha is 0.88%, one is nominally positive, and none survives Holm; under the broad benchmark none is nominally positive. The 49 narrative mappings are favorable stress tests and cannot count as evidence against their source papers. The mappings were frozen after U.S. outcomes had been inspected and had no independent second coder, so the paper does not claim the new protocol retroactively removes that limitation. A limited 144-combination sensitivity remains explicitly a lower bound.

## 3. Retrospective design

We no longer describe the U.S. tests as discovery evidence. The paper states that many sources postdate the December 2024 return endpoint, that no credible publication-date out-of-sample test exists for much of the corpus, and that the 2026 mapping freeze followed outcome access. Results are called historical spanning diagnostics and cannot distinguish discovery from repackaging or correct for publication selection.

## 4. Broad-JKP truncation and inference

The paper now explains that the source broad-factor panel ends in December 2021 and is shifted one month, yielding a January 2022 candidate-return endpoint. The 120-month training window then leaves August 2011--January 2022 for evaluation. Ridge penalties are reselected at each evaluation month using past data. The 5,000-replication bootstrap resamples fixed out-of-sample residuals and does not repeat model fitting or tuning. We therefore label the result post hoc, descriptive, and potentially optimistic rather than robust.

## 5. International failures

We replaced the main international discovery table with an event-level forensic audit. All 40 nonpositive-NAV events are reproduced to numerical tolerance. Every event is dominated by one extreme positive return held on the short side; 31 occur in France, and 24 fall in two France month-cells. Return caps are reported only as diagnostics. International performance is removed from the headline evidence and the event ledger is included in the artifact.

## 6. Common-task fidelity

The manuscript and ledger now distinguish narrative translations, example/motif support, named-rule support, and a released seed expression. Results are reported by tier. The paper lists the common task's major deviations from original systems: frequency, universe, language/news inputs, memory, dynamic allocation, non-equity instruments, and execution. It states that proxy failure cannot prove native-agent failure and proxy success cannot be attributed to an agent.

## 7. Implementation details

The revision states gross exposure two for long-short portfolios; candidate costs and gross benchmark factors; omitted borrow, financing, impact, capacity, and locate constraints; cash/risk-free treatment; the automatic Newey--West rule; 2,000 primary and 5,000 broad bootstrap replications; and the post-outcome status of the two-percentage-point threshold. HAC sensitivity 0/1/1/0 is now in the abstract and main results.

## 8. Inspectable artifact

The anonymous artifact builder packages the census, screening and execution records, all formulas and mapping fields, aggregate monthly U.S. candidate and factor returns, cost and inference outputs, broad residuals, international event forensics, scripts, tests, and a SHA-256 inventory. Restricted security-level data are not redistributed. The artifact README states the interpretive boundaries rather than relying on hashes alone.

## Minor comments

- The 67 entries are now explicitly described as system lineages in an availability census, not 67 replications or necessarily 67 one-to-one papers. A complete 67-row primary-record bibliography is included in the artifact. The main paper separately names and cites all 14 targeted implementation attempts and the five papers underlying the 13 source-grounded component tests.
- The 67-system census, 55-source corpus, 51 mapped indices, and 62 portfolios are reconciled in the first methods subsection.
- The nine licenses are separated from the 14 execution attempts.
- The positive AlphaAgent-related row is always called a researcher-authored AlphaAgent-inspired mechanism proxy, with its 0.48% simultaneous lower bound.
- The audit found no explicit exact match to the full common monthly U.S. factor-alpha claim among the 51 mapped source indices; the paper therefore does not imply that every source originally claimed that metric.
- Every summary separates unavailable evidence, task incompatibility, and benchmark failure.
