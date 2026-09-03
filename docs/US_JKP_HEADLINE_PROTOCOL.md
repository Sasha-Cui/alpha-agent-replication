# U.S./JKP headline-strategy milestones

## Research question and scope

For each of the 69 paper records (67 system lineages), extract its central
proposed trading strategy and evaluate the strongest defensible implementation
on monthly U.S. stocks using JKP. This is a common-data strategy-transfer study,
not a requirement to recreate every original paper table or the exact historical
LLM generation process. The September 3, 2026 user instruction is the governing
scope. Existing paper/source audits remain reusable evidence.

The central strategy must be selected from the paper's stated main method,
default configuration, or highlighted proposed strategy before inspecting its
new JKP performance. Do not run many paper variants and promote the best one.
Where the paper proposes a signal but no portfolio, use the common score-to-
portfolio adapter and explicitly identify that adapter as researcher supplied.
Where portfolio construction is itself central, preserve it where feasible and
record any necessary common-task changes before the run.

## One common evaluation contract

`paper_runs/us_jkp_headline/benchmark_contract.json` starts from the existing
corrected U.S. experiment, not the superseded legacy return builder. Before the
first strategy result, validate and lock its data hash, factor identifiers and
holding-month alignment, cost accounting, and coverage rules. The starting
settings retain the established largest-1,000 formation-date U.S. universe,
monthly rebalance, July 1999-November 2024 formations, August 1999-December 2024
realizations, 10 bp one-way costs, and FF5+momentum+JKP132 benchmark.

Use only information available at formation. In particular, next-month return
availability must not select holdings; future-data filling and future-informed
sign/parameter choices are prohibited. Record each required financial input,
its JKP definition, its availability convention, and any approximation. A column
name resemblance alone does not establish semantic equivalence.
Check the available definitions once and document annual/quarterly, denominator,
or cash-flow convention differences. Proceed with a labelled adaptation when the
central economic meaning is retained; do not turn the prescribed JKP data
substitution into another demand to recover unavailable original vendor data.

Use paper/default settings when implementable. Any learning, search, or tuning
must use only earlier outcomes with an explicitly recorded chronological policy.
If an original model/API is unavailable, a declared accessible replacement is
permitted when it preserves the mechanism. Fix that choice before evaluation and
report the substitution; do not wait indefinitely for a retired endpoint.
The U.S. history has already been inspected in prior project work: this study is
retrospective, not a pristine holdout or an ex-ante preregistration.

All evaluable strategies use the same timing, market-data version, transaction-
cost treatment, metric definitions, and factor benchmark. Report coverage and
exposure differences rather than silently changing calendars or masking missing
months. Score-only methods use the common portfolio adapter; an explicit native
portfolio rule must not be silently replaced just to obtain a convenient factor.

## Definition of a closed milestone

Each milestone must contain:

1. A short source-anchored headline recipe and a reason it is the main strategy.
2. Executable implementation or a specific, evidenced non-evaluability finding.
3. An input/adapter record distinguishing preserved rules from approximations.
4. Focused correctness tests, especially timing, formula/direction, missing data,
   and accounting checks. Use native golden cases where available.
5. For an evaluated implementation: reproducible monthly returns and coverage,
   holdings/provenance kept in approved storage, and gross/net return, Sharpe,
   drawdown, turnover, JKP alpha and uncertainty under the common contract.
6. A concise verdict: what was implemented, what was not, the measured result,
   and whether it is a headline adaptation, a central partial adaptation, or not
   evaluable. A strategy need not beat the benchmark to count as evaluated.

Terminal statuses are `completed_adapted`, `completed_partial`, and
`closed_not_evaluable`. The first two require an executed monthly strategy and
the common evaluation artifacts. A runnable import, formula unit test, historical
author output, or software-only component is insufficient. A non-evaluable case
requires a written limitation and effort record, not fabricated or zero returns.
Closed milestones are not all labelled successful replications.

## Bounded effort and sequencing

The active runner holds an operating-system lock and records its phase, host,
PID and Slurm allocation in `artifacts/us_jkp_headline/v1/operation.json`.
Heartbeat checks must verify the recorded process/allocation rather than treating
a status file alone as liveness. Current logs are
`paper_runs/us_jkp_headline/M001_preflight.log` and `M001_run.log`. Do not duplicate
a live job. The benchmark contract records the private data and public factor
hashes; completed run manifests pin the result artifacts.

- Keep at most one milestone `in_progress`.
- After the M001 shared foundation release, focused validation and a coherent
  commit are required for every milestone. Batch the full two-Python release
  gate, one push, and one CI run after every ten newly closed milestones. Run it
  earlier only after a material shared-infrastructure change, for final delivery,
  or on explicit request. Do not activate another paper while a batch release is
  live. This keeps progress moving without producing one workflow per paper.
- Start with the existing dossier, the relevant primary method section, and
  official code; do not repeat the whole forensic audit.
- Implement the most direct supported route, run it, and repair tractable bugs.
- If blocked, check the specific missing input/code and one plausible in-scope
  alternative. Record what was tried and why the remaining gap matters.
- Do not spend open-ended weeks chasing exact original numbers, unavailable
  historical APIs, unrelated ablations, or every public fork. Close the strongest
  defensible partial case or non-evaluable case and move to the next paper.
- Reopen a closed paper only for concrete new evidence or an explicit user
  request. Keep a short deferred-work list rather than a growing active backlog.
- Preserve the existing historical result packages; do not retroactively change
  their fidelity claims. Reuse a result only after checking the new recipe and
  common benchmark contract.

At 69 closures, produce the cross-paper table from the ledger, with separate
counts for evaluated headline adaptations, evaluated partial adaptations, and
non-evaluable cases. Apply the declared family-wide inference rules and finish
the manuscript consistency/reproducibility review. Do not claim 69 successful
strategies merely because 69 milestones are closed, and do not submit externally
without the user's instruction.

## First milestone

M001 is GPT-Signal's EVC signal. Sections 5.1-5.3 identify its explicit formula
and strongest absolute correlation claim. The paper's all-sector three-month
EVC/return correlation is -0.14, so the proposed trading orientation is fixed as
negative EVC, not selected on JKP returns. The JKP schema contains candidate
inputs `ni_at`, `ebitda_mev`, and `ocf_me`; their accounting-period and cash-flow
definitions must be checked before using the algebraic mapping. The common
portfolio construction is an adaptation, not a portfolio claimed in that paper.
The other five signals and the original figure-by-figure reproduction are not
the current milestone's scope.

Primary reference: https://arxiv.org/html/2410.18448v1
