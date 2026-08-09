# Literature-search protocol for the 2026 financial-agent evidence census

## Scope and status

This document reconstructs the search procedure that produced the frozen census used in the ICAIF submission. The public-artifact cutoff is **2026-08-02 23:59:59 UTC**. Searches cover database inception through that cutoff. The frozen registry contains 103 candidate system lineages represented by 104 distinct public record URLs and resolving to 98 canonical scholarly works.

This is a cutoff-bounded systematic screen, not a claim to have enumerated every paper that could be described as a financial agent. The original database result pages, rankings, and hit counts were not preserved. That limitation prevents a literal replay of vendor-specific rankings and is disclosed in the manuscript. The exact query families, sources, screen rules, seed records, canonical records, deduplication decisions, and row-level dispositions are preserved.

## Discovery sources

The following scholarly sources were searched from inception through the cutoff:

- arXiv categories `cs.AI`, `cs.CL`, `cs.LG`, `cs.CE`, `q-fin.CP`, `q-fin.PM`, `q-fin.ST`, and `q-fin.TR`;
- ACL Anthology;
- OpenReview;
- ACM Digital Library;
- SSRN.

Crossref and OpenAlex were used to resolve metadata and duplicate publication manifestations. GitHub was not treated as a literature database; it was searched only for an exact-title, author-linked, or publication-linked artifact after a scholarly record was identified.

## Query families

The same three conceptual query families governed discovery. Database syntax and stemming were adapted only where a provider did not accept the generic Boolean form.

1. `(LLM OR "large language model" OR agent* OR multi-agent) AND ("alpha mining" OR "factor discovery" OR "formulaic alpha" OR "strategy generation")`
2. `(LLM OR "large language model" OR agent*) AND (trading OR portfolio OR "stock selection") AND (return OR Sharpe OR backtest OR live)`
3. `(benchmark OR evaluation OR audit OR reproducib* OR artifact OR leakage) AND ("alpha mining" OR "trading agent*" OR "quantitative investment")`

Backward and forward citation chasing used four seeds: AlphaBench, AlphaQT-Bench, FINSABER, and the Agentic Trading survey. The companion `search_log.csv` records every source-by-query route and distinguishes discovery, snowballing, deduplication, and artifact lookup.

## Screen and canonicalization

The screening unit is a named system/version lineage. Papers, proceedings versions, preprints, repositories, and project pages can map many-to-one to a lineage. Canonical scholarly works are a separate unit used for citation and the work-level waterfall.

Records are coded into five strata:

- `F`: an LLM- or agent-based method that generates, scores, searches, or selects executable factors or factor portfolios;
- `T`: an LLM- or agent-based method that emits dated trades or portfolio weights and has a historical, paper, or live return evaluation;
- `B`: a benchmark, audit, or evaluation environment for `F` or `T` systems;
- `C`: community software without a sufficiently specified scholarly system claim;
- `M`: a non-LLM mechanistic comparator.

The retained method census is `F + T`. Static prediction and question-answering papers without a tradable output, generic financial assistants, behavioral market simulations, benchmarks, audits, community projects, and mechanistic comparators remain in the screened registry but are not retained as candidate methods. Borderline records are therefore visible rather than silently discarded: their stratum and row-level `inclusion_exclusion_rationale` are recorded in `system_registry.csv` and propagated to `primary_record_metadata.csv` and the 98-row work-level waterfall.

Duplicate preprint/proceedings manifestations are collapsed when title, authorship, and system identity show that they report the same work. Methodologically distinct successor systems remain separate lineages. The frozen `lineage_dedup_notes` field records each decision.

## Reconstructing the denominator

A researcher can reconstruct the reported denominator as follows:

1. Apply the source coverage, query families, citation chasing, and cutoff above.
2. Resolve candidate records with Crossref/OpenAlex and locate only author- or paper-linked code artifacts.
3. Apply the five-stratum definitions and the row-level inclusion/exclusion rules.
4. Collapse publication manifestations using `lineage_dedup_notes` while retaining distinct successor systems.
5. Compare candidates to the frozen canonical record table in `primary_record_metadata.csv` and the disposition table in `system_registry.csv`.

The preserved result is 103 candidate lineages, 98 canonical works, 69 retained `F/T` works in 67 lineages, and 29 screened-out works. Additions discovered after the cutoff must be versioned separately and cannot silently change these denominators.
