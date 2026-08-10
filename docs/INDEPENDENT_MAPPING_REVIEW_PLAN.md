# Independent Mapping Review Protocol

## Purpose

The current 50 source-to-strategy mappings were constructed retrospectively by
the research team. They are transparent and auditable, but they were not fixed
before return outcomes were examined and were not independently double-coded.
No documentation change can retroactively remove that discretion. The repair is
to preserve the current analysis as exploratory and conduct a separately
versioned, outcome-blind confirmatory mapping exercise.

## Design

1. **Freeze the exploratory record.** Tag the mapping ledger, source packet,
   analysis lock, and current aggregate results by commit and SHA-256. Do not
   edit or overwrite those files during confirmatory review.
2. **Prepare blind review packets.** Give reviewers the source paper, cited
   pages, a uniform extraction form, and the admissible JKP variable dictionary.
   Do not provide candidate returns, factor correlations, alpha estimates,
   significance flags, or the existing team's chosen mapping.
3. **Use at least two independent coders.** Each coder records the signal
   formula, sign, lag, holding period, rebalance rule, universe, weighting,
   missing-data treatment, and every assumption not fixed by the source. A
   coder may choose “not implementable from the source” rather than inventing a
   proxy.
4. **Measure agreement before adjudication.** Report exact agreement for
   implementability and categorical fields, plus field-level disagreement
   counts for continuous/formula choices. Preserve both original forms.
5. **Adjudicate without outcomes.** A third reviewer resolves discrepancies
   using only sources and the predeclared variable dictionary. The adjudicated
   ledger is then frozen and hashed before anyone reveals or computes returns.
6. **Predeclare ambiguity sets.** When multiple defensible implementations
   remain, enumerate all variants in advance, identify one rule-based primary
   variant, and treat the rest as a specification set. Adjust inference across
   both papers and mapping variants rather than selecting the best-performing
   version afterward.
7. **Run confirmatory computation once.** Execute the frozen ledger in a new
   output directory. Keep exploratory and confirmatory results side by side,
   and explain every numerical difference rather than replacing the original.
8. **Invite source-author correction.** Send each paper's frozen extraction to
   its authors for factual correction. Version and disclose responses; do not
   condition inclusion on whether a correction strengthens or weakens results.

## Minimum review record

Each row should contain stable paper and component identifiers; source URL and
page/section anchors; verbatim-short source evidence within quotation limits;
implementability status; formula; sign; timing and lag; formation and holding
periods; universe; weighting; breakpoints; missing-data rule; JKP variables;
unsupported assumptions; coder ID; timestamp; adjudicator decision; author
response status; and hashes of the source file, extraction form, and final
ledger.

## Interpretation after the review

The 37 “in-spirit” reconstructions should remain exploratory unless blind
reviewers can anchor them more closely to source instructions. Primary
confirmatory claims should emphasize released code and source-grounded
components, with narrative proxies reported separately. This protocol cannot
guarantee agreement or rescue an underspecified paper; it converts discretion
from an invisible researcher choice into a prespecified, reviewable source of
uncertainty.
