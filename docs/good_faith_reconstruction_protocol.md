# Good-faith reconstruction protocol for unreleased financial-agent systems

## Purpose

This protocol governs what happens when a paper makes an empirical trading or alpha claim but does not release an executable return path. Its purpose is to give the proposed idea a strong, source-faithful opportunity to work while preventing a researcher-authored proxy from being misrepresented as the original system.

The protocol separates two questions:

1. Does a documented, implementable component contain incremental return under the common evaluator?
2. Does the original agent or paper work as claimed?

A reconstruction can inform the first question. Unless the original system is sufficiently specified and matched, it cannot answer the second.

## Reconstruction contract

### Step 1: Build a claim card before implementation

For each source, record the public location of the relevant paper section, appendix, repository file, or README and extract:

- original asset class and market;
- sampling and trading frequency;
- investable universe;
- prediction or portfolio objective;
- claimed metric and benchmark;
- signal inputs and their timing;
- formula, sign, nonlinearity, interaction, or named rule;
- portfolio constraints, rebalancing, and cost assumptions;
- agent-specific components such as language generation, retrieval, memory, debate, search, or execution.

Short source excerpts may be recorded with a page, section, equation, table, or line locator. A paraphrase alone does not support a claim of exact reproduction.

### Step 2: Use the strongest available evidence in a fixed hierarchy

Evidence is used in this order:

1. released executable expression or rule;
2. equation, pseudocode, or explicit stock-scoring rule in the paper;
3. worked example or named investment rule;
4. narrative economic mechanism;
5. title, abstract, or third-party summary.

Lower levels cannot override higher ones. Repository examples are not assumed to be trained-agent outputs unless the source says so.

### Step 3: Preserve the source before standardizing the evaluator

The implementation preserves every publicly specified ingredient, sign, lag, interaction, and portfolio constraint that the common data can represent. Only then are common-evaluator choices applied. Every forced substitution is recorded, including characteristic proxies, monthly aggregation, U.S. top-1,000 filtering, decile construction, value weighting, or omitted text and execution components.

If a central component cannot be represented, the result is downgraded to a mechanism stress test. It is not called a replication.

### Step 4: Give ambiguity the benefit of the doubt

When the source permits more than one reasonable implementation, the reconstruction should favor the claimed mechanism rather than a deliberately weak version:

- orient the score in the economically favorable direction stated by the source;
- do not reverse a sign after viewing returns;
- for a cross-sectional score, expose the full top-minus-bottom decile spread unless the source requires long-only treatment;
- honor sparse top-k or long-only rules when explicitly stated;
- report gross performance as a generous mechanism diagnostic and cost-adjusted performance as the implementable result;
- avoid extra filters, neutralizations, or risk scaling that the source did not require and that could mechanically suppress its signal;
- do not delete an unsuccessful candidate or choose among variants using test-period returns.

Favorable does not mean unconstrained optimization. Leverage, timing, and asset-class changes must remain comparable and disclosed.

### Step 5: Encode ambiguity as variants, not hidden judgment

If two or more mappings are substantively reasonable, all should be coded before inspecting their returns. All variants remain in the multiplicity family. The ledger explains why each variant is reasonable. A best-performing ex-post mapping may be reported only as an explicitly optimistic upper envelope, never as confirmatory evidence.

### Step 6: Apply a source-protection rule

Each output receives one of three empirical roles:

- **Native or adapted implementation:** may speak to the released implementation within the documented adaptation boundary.
- **Source-grounded component test:** based on a released expression, named rule, or worked example; may speak only to that component under the common task.
- **Exploratory favorable stress test:** based on narrative translation; cannot count as evidence against the source. It tests only whether the researcher's generous economic translation spans the benchmark.

No mechanism mapping in the current study supports a source-level negative conclusion because none exactly matches the full original task and metric.

### Step 7: Review without outcome access

The preferred workflow uses two reviewers. One prepares the claim card and mapping; the second sees the source and proposed implementation but not returns, then classifies it as faithful, favorably biased toward the source, incomplete, or invalid. Disagreements are resolved before execution and agreement is reported.

If outcome-blind second review was not performed, that absence is a design limitation and the result is not upgraded after the fact.

### Step 8: Preserve a reconstruction card

The public ledger must contain:

- source and locator;
- claim card fields;
- exact executable formula and portfolio rule;
- evidence tier;
- source-supported and researcher-supplied elements;
- benefit-of-the-doubt choices;
- central omissions and task deviations;
- reasonable alternatives considered;
- freeze time and hash;
- whether returns were seen before freezing;
- reviewer identities or anonymous roles and agreement status;
- the precise negative-evidence boundary.

## Application to the current 62-mapping family

This protocol was formalized after the existing mappings and U.S. outcomes had been inspected. It therefore cannot retroactively make those choices outcome-blind. The audit classifies:

- 1 monthly JKP adaptation of a released 60-bar return/volatility seed;
- 12 named-rule or example-supported component tests;
- 49 narrative favorable stress tests.

The 13 source-anchored partial component tests may be summarized as a post-hoc subset, with their own multiplicity correction, but only at component level. The QuantEvolver row preserves the released seed's risk-adjusted-momentum idea but changes the 60-bar return and volatility operators to a 12-month return and 252-day volatility proxy; it is therefore not the literal released expression. The other 12 retain only examples, motifs, or named rules. The page-anchored transformations and omissions are exposed in `docs/source_anchor_review_packet.md` and its machine-readable CSV. Independent review of that packet remains pending and does not repair the retrospective design.

The 49 narrative translations are retained to show the performance of generous economic interpretations; their null results are not evidence that the underlying papers or agents fail.

Future additions must complete the claim card and outcome-blind review before execution. A source author correction should be added as a versioned alternative rather than silently replacing the frozen mapping.
