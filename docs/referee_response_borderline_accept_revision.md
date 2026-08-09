# Response to anonymous referee: borderline-accept revision

We thank the referee for recognizing the value of the evidence hierarchy and for identifying where the earlier manuscript still overreached. The revision does not claim to repair the one limitation that cannot be repaired retrospectively: the mappings were not outcome-blind and were not independently coded. We instead narrow the title and estimand, treat all mapping-based statistics as descriptive conditional diagnostics, make corpus discovery reconstructible to the extent supported by the frozen record, and add the requested cost and missing-return analyses.

## 1. Systematic construction of the 98-work screen

We replaced the claim of a “complete census” with “cutoff-bounded systematic screen.” The manuscript now reports:

- the 2 August 2026 public-artifact cutoff;
- the searched arXiv categories, ACL Anthology, OpenReview, ACM Digital Library, and SSRN;
- the three exact conceptual Boolean query families;
- backward and forward citation chasing from AlphaBench, AlphaQT-Bench, FINSABER, and the Agentic Trading survey;
- Crossref/OpenAlex deduplication and the restricted use of GitHub for record-linked artifacts;
- explicit `F`, `T`, `B`, `C`, and `M` strata, inclusion rules, and treatment of borderline records;
- the distinction among 103 lineages, 104 public record URLs, 98 canonical works, 69 retained works, and 67 retained lineages.

The artifact now includes `literature_review/census_v1/search_protocol.md` and a 22-route `search_log.csv`, in addition to row-level deduplication notes and inclusion/exclusion rationales. We explicitly disclose that vendor result rankings, raw hit counts, and exact execution timestamps were not preserved. The search can therefore be reconstructed conceptually and checked against every frozen disposition, but not replayed as an identical vendor-ranked result set. We regard that qualification as scientifically preferable to retaining an unsupported completeness claim.

## 2. Outcome-dependent mapping and lack of an independent coder

We agree this is the largest limitation. No new coder can now be both independent of the project and genuinely blind to the already-observed outcomes within the present submission process. We therefore do not claim to have solved it.

The revised title calls the exercise descriptive. The abstract, mapping section, estimator section, results, limitations, and conclusion now state that:

- the unknown mapping-choice process is outside the 62-formula multiplicity family;
- Holm and bootstrap values quantify sampling variation only conditional on the realized mappings;
- all mapping-based p-values and intervals are descriptive, even when a conditional adjusted value is below 5%;
- the 13 source-grounded mappings speak only to documented components;
- the 49 narrative mappings cannot support negative inference about their sources;
- confirmatory performance claims require a future independently coded, outcome-blind reconstruction.

The existing 144-combination exercise remains labeled only as a lower bound over alternatives that happened to be coded, not a substitute for independent coding.

## 3. Narrower title, abstract, and conclusion

The new title is **“Can Public Artifacts Substantiate Financial-Agent Alpha? A 98-Work Evidence Audit and Descriptive Spanning Exercise.”** The abstract now leads with the released-evidence question, describes the artifact gap, and explicitly says that the evidence does not establish that financial agents as a class lack alpha. The conclusion likewise separates three claims: artifact unavailability, limited component-level evidence under the common task, and exploratory narrative translations.

## 4. Transaction costs

We no longer let a single 10-bp convention carry the economic interpretation. The manuscript states that 10 bp is a locked transparent reference point, not a security-specific cost estimate, and emphasizes the full 0/5/10/25/50-bp curve. It reports:

- median alpha of 2.15% gross, 1.01% at 5 bp, and -0.05% at 10 bp;
- positive-estimate counts of 46/42/30/18/10 across the grid;
- conditional Holm counts of 1/1/1/0/0 across the same grid;
- among 46 gross-positive mappings, a median break-even cost of 21.4 bp with an 8.2--42.1 bp interquartile range.

The revision emphasizes that the median sign is cost-sensitive but that gross results also yield only one conditional adjusted result. It also states prominently that costed candidate returns are compared with gross benchmark factors, making the comparison asymmetric and conservative rather than a symmetric net-of-cost contest.

## 5. Missing realized returns

We added a deterministic U.S. sensitivity using the already-frozen portfolio weights and recorded missing-return exposure. The primary policy keeps a missing held return at zero without conditioning formation or reweighting on future coverage. The new position-adverse unit-move stress assigns -100% to a missing long and +100% to a missing short. This is intentionally severe and is not presented as an expected delisting-return estimate.

Across mappings, the median candidate's mean missing gross-weight share is 0.20% and the maximum candidate mean is 0.43%. Under the adverse stress, median annualized six-factor alpha is -4.84%; four estimates remain positive, none is nominally positive, none survives conditional Holm, and no simultaneous lower bound exceeds two percentage points. The revision therefore acknowledges that zero fill is economically consequential while showing that adverse missing outcomes do not create evidence of alpha. The complete sensitivity output, scope summaries, hashes, builder, and unit test are included.

## 6. Post-hoc 133-factor diagnostic

The diagnostic remains explicitly secondary. We changed “strengthens” to “is directionally consistent with” and retain the disclosures that it uses 126 evaluation months, selects ridge penalties along a realized rolling path, does not rerun model selection in the bootstrap, and was designed after primary outcomes. It is not described as confirmatory robustness evidence.

## Resulting claim

The paper's strongest result is now deliberately evidentiary: current public artifacts generally do not permit independent substantiation of financial-agent alpha claims. One released seed expression is directly testable; the reconstructable component subset provides limited descriptive evidence under the common task; and researcher-authored narrative mappings remain exploratory. The revision does not convert missing artifacts into zero returns, and it does not convert post-outcome mappings into confirmatory evidence.
