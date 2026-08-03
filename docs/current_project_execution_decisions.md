# Current Project Execution Decisions

**Project:** Alpha Agent Replication

**Decision owner and sole author:** Sasha Cui

**Recorded:** 2026-08-02

**Scope:** Binding guidance for the current project only; it does not authorize separate follow-on studies.

This record resolves the ten design questions raised before execution. If a later implementation choice conflicts with this document, stop and surface the conflict rather than silently narrowing the project.

## D01 — Quality over the nearest deadline

There is no requirement to force a weak submission into the nearest conference cycle. Target a suitable upcoming venue only if the evidence and manuscript meet the quality bar. Otherwise continue to the next conference. Scheduling decisions should preserve locked tests and scientific credibility.

## D02 — Broad replication and comparison

This is both a replication study and a comparison across a large system universe. Three systems are categorically insufficient. Aim for as many relevant public systems as can reasonably be discovered, classified, and attempted.

Operational interpretation:

- Freeze a literature/repository census with an explicit search protocol and cutoff date.
- Attempt all in-scope systems; never choose only convenient winners.
- Record one row per system with paper, repository, commit, license, artifact availability, task, data, evaluator, attempt status, and fidelity class.
- Label implementations as official, adapted, reimplemented, mechanism-inspired, artifact unavailable, legally unusable, or technically incompatible.
- Keep a broad artifact/replicability census even when only a subset can enter a strictly common-task comparison.
- Exclude only for a documented scientific, legal, or technical reason—not because a system is inconvenient or performs poorly.
- Report failure denominators. Missing dependencies, infrastructure failure, invalid output, and empirical non-replication are different outcomes.

The target is maximum defensible breadth, not a fixed top-N leaderboard.

## D03 — Data and scope expansion authorized

The empirical scope may expand beyond the currently available datasets, markets, horizons, universes, features, and robustness checks wherever that materially strengthens the evidence. Every addition must be point-in-time where required, licensed for the intended use, versioned, and tied to a manifest. Expansion must not expose the locked confirmatory test to iterative tuning.

## D04 — Model and API policy

Use Codex and locally reproducible/open-weight computation for most work. OpenRouter is authorized as a secondary resource with a hard cumulative project spend strictly below USD 500.

Controls:

- Route all paid calls through one ledger that records provider, model identifier, timestamp, purpose, tokens, retries, and cost.
- Use a USD 450 soft stop so accounting lag cannot cross the USD 500 hard ceiling.
- Cache responses and never pay twice for an identical deterministic request unless repetition is part of a pre-specified experiment.
- Pin prompts and model/version identifiers; treat provider drift as a limitation.
- Prefer paid calls for targeted model-diversity or robustness cells, not routine preprocessing.
- No OpenRouter calls were made when this decision record or the future-idea folders were created.

## D05 — Economic relevance thresholds accepted

Use the recommended practical-effect thresholds as the primary economic materiality rule:

- Net annual alpha advantage of at least 2 percentage points; or
- Information-ratio advantage of at least 0.25; or
- Net Sharpe-ratio improvement of at least 0.10.

The main transaction-cost scenario is 10 basis points one way. Report uncertainty and the full effect distribution; a threshold crossing is not a substitute for statistical validity. Include lower/higher cost sensitivity, turnover, coverage, and capacity when inputs permit.

## D06 — Absolute prohibition on author contact

Do not contact the original authors of any paper, repository, benchmark, dataset, or system—now or later—for code, data, clarification, debugging, permission, or comment. Do not email, message, open an issue, post a discussion, submit a pull request for clarification, or ask a third party to contact them.

Use only publicly available materials and licensed artifacts. When ambiguity cannot be resolved publicly, document the ambiguity and lower the fidelity classification. This prohibition must not be relaxed merely to improve a replication result.

## D07 — Independent owner review

Sasha will perform the requested independent human review. The execution team must create a compact review packet with the relevant claims, sampled artifacts/traces, proposed judgments, uncertainty, and a reproducible way to inspect each item. Notify Sasha when that packet is complete. Do not record the review as completed until Sasha actually returns it, and do not fabricate or substitute an automated review.

## D08 — Bouchet compute policy

Charge the work to Slurm account pi_jss233. Use CPU-first workflows; this project is not assumed to require GPUs. A GPU job requires a concrete workload-based justification and an expected-utilization check.

Hard submission rule: no more than 200 jobs per hour. Conservatively count array elements as jobs unless Bouchet's scheduler documentation clearly establishes a different applicable accounting rule. Batch work, cache shared computation, use dependencies, and avoid scheduler spam. Record job IDs, manifests, resource requests, exit states, and output locations. The creation of this record does not authorize or submit any job.

## D09 — Authorship

Sasha Cui is the sole author. Do not add an author based on code reuse, tool assistance, routine feedback, infrastructure support, or benchmark provenance. Preserve citations, license notices, acknowledgments, and any required disclosure of AI assistance. Any future authorship change requires Sasha's explicit decision.

## D10 — Release and licensing policy delegated

Choose the most permissive legally compatible release that maximizes reproducibility without relicensing third-party material.

Default policy:

- Preserve the repository's existing license for modifications where applicable.
- Prefer Apache-2.0 for newly separable code if compatible with the repository and dependencies.
- Prefer CC BY 4.0 for original documentation and benchmark metadata where appropriate.
- Release configs, prompts, manifests, provenance, schemas, and derived aggregate results.
- Redistribute raw or derived data only when every upstream license and privacy restriction permits it.
- Retain notices and clearly inventory non-redistributable dependencies.

Perform a license audit before the public release; the above is a policy direction, not permission to override upstream terms.

## Current paper architecture

The evidence should be organized in four connected tracks:

1. **Artifact census and reproducibility audit:** the broadest system universe, including failures and unavailable artifacts.
2. **Native-protocol replication:** faithful or best-effort reproduction under each system's own claimed setting.
3. **Common-task comparison:** all systems whose outputs can be normalized onto common data, splits, evaluator, portfolio, and cost assumptions.
4. **Robustness and economic validity:** additional markets/periods, locked tests, uncertainty, costs, turnover, and practical-effect thresholds.

This architecture makes breadth substantive while avoiding false equivalence between incompatible native tasks.

## Non-negotiable execution guardrails

- Maintain a frozen system-registry version for each result table.
- Predefine primary claims and confirmatory tests before large-scale runs.
- Preserve raw outputs and failed runs; normalization must be reversible.
- Separate exploratory, validation, and locked-test results in filenames, manifests, and prose.
- Never tune on a confirmatory result.
- Stay below both the 200-jobs/hour and USD 500 caps.
- Do not contact original authors.
- Do not let the parked future studies displace the current replication project without a new explicit activation decision.
