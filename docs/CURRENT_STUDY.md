# Current monthly U.S. investment study

**Provisional as of November 16, 2026.** The research question is whether
published LLM investment mechanisms deliver useful investment performance on
U.S. equities beyond actual FF5 + momentum + JKP132. The current benchmark
is verified; the execution cohort and transfer contract are not final.

## Scope still to resolve

The earlier user instruction was to include only papers about monthly investing
and drop the others. The latest request calls for evaluating central mechanisms
under a defensible monthly U.S. transfer contract. Whether that permits adapting
daily or quarterly methods to monthly decisions is still pending clarification.

Until resolved, existing daily and quarterly runs are historical evidence, not
newly admitted monthly evaluations. Monthly reporting of a daily strategy does
not establish monthly investment decisions.

## What is complete

The benchmark contains 305 calendar months from August 1999 through December
2024: the five actual French factors, actual momentum, and the original fixed
132 actual JKP U.S. monthly `vw_cap` long-minus-short factor series. RF is
separate from these 138 factors.

Independent readback verified the pinned raw archives, identities, units,
directions, calendar, and full factor span. The full panel has factor rank 138
and 166 residual degrees of freedom with an intercept. Each method needs its
own calendar and rank check; these full-panel figures do not validate a short
method history.

Actual CRSP opening prices and unmodified monthly records have been recovered.
The monthly conversion preserves all vendor values, missing returns, and event
flags, and passed complete row-group readback. Data integrity is separate from
portfolio-accounting admission.

## Method readiness

The [69-paper inventory](study/method_readiness.csv) separates central-mechanism
execution evidence from release, input, runtime, and economic-accounting gaps.
The [status snapshot](study/status.json) identifies its source receipts.

Eight records have evidence that a central mechanism actually executes:
FinMem, FinAgent, TradingAgents, FinRL-DeepSeek, AlphaAgent, GuruAgents,
QuantaAlpha, and AlphaMemo. This is not a final monthly cohort. Some execution
evidence comes from historical or input-invalid runs; their financial results
are not admitted by this inventory.

Other substantial releases remain individually recorded. For example,
training code may support fresh training even when an old checkpoint is
unavailable. A missing historical checkpoint alone is not evidence that the
method cannot be executed.

## What remains before a result can be admitted

1. Resolve scope and freeze the eligible central-method variants.
2. Fix each variant's input coverage, source/data/model bindings, monthly
   decision clock, and any transfer choices before inspecting outcomes.
3. Execute the real supported mechanism, with complete request/prefix records
   and the required replay or conformance checks.
4. Validate funded portfolio accounts, costs, missing observations, corporate
   actions, and settlement assumptions independently.
5. Attribute the complete declared monthly path to the actual 138-factor span,
   reporting rank, residual degrees of freedom, uncertainty, and matched controls.
6. Reconcile the cohort, failures, results, and limitations into the provisional
   paper before marking this study complete.

The draft contract specifies causal inputs, explicit funding and cash, turnover
costs, chronological training/validation, and source-specific controls. It does
not authorize silently replacing a central agent with a deterministic proxy.

Monthly CRSP delisting flags distinguish included, excluded, and partial
payoffs. Do not compound a delisting return twice, treat an incomplete payoff
as complete because its number is finite, or silently drop a held delisting.

## Inference and claims

The actual 138-factor intercept is retrospective attribution, not a tradable
hedge portfolio. Short paths can leave that intercept unidentified. The saved
finite-design calibration also shows that approximate HAC intervals can
undercover with persistent errors.

Retain the stated 2-percentage-point annual economic margin and the declared
multiplicity accounting. Insignificance does not prove no alpha, and a
successful software check does not reproduce an entire paper.

## Evidence locations

The compact [status snapshot](study/status.json) and benchmark contract are
readable in the source checkout. The other working-evidence links below
require authorized Bouchet access:

- [Benchmark contract](../paper_runs/us_monthly_actual_factors_v1_20261116/benchmark_contract.json).
- [Independent benchmark readback](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/artifacts/us_monthly_actual_factors_verified_v2_20261116/benchmark_independent_readback_v1/validation.json).
- [CRSP recovery receipt](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/artifacts/us_monthly_actual_factors_verified_v2_20261116/CRSP_opening_price_recovery_completion_v1.json).
- [Transfer contract draft](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/artifacts/monthly_us_transfer_contract_v1_20261116/monthly_us_transfer_contract_draft_v1.json).
- [Detailed mechanism inventory](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/artifacts/monthly_us_transfer_contract_v1_20261116/all69_mechanism_readiness.json).

The newest working continuation is
`artifacts/us_monthly_actual_factors_verified_v2_20261116/HANDOFF.md`.
The November evidence-paper directory is
`paper_runs/llm_investment_evidence_paper_v1_20261105/`; its study correction
keeps the paper provisional. Sealed earlier manuscripts remain unchanged.
