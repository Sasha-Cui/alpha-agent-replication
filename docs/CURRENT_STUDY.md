# Current native monthly U.S. investment study

**Verified November 17, 2026; paper provisional.** Both paper-based monthly implementations completed source execution and exact offline replay. EFS completed 12 of 12 declared economic paths. Screening completed 12 of 30 paths; the other 18, including the designated LLM-screening primary and its equal-weight control, remain blocked by unpriced held month-end assets. Overall study and paper closure remain unfinished.

## Research question and scope

Do published LLM investment methods deliver useful net U.S. monthly investment performance beyond actual FF5 + momentum + JKP132? Only paper-native monthly experiments are eligible. Central-method reconstruction from the paper is allowed; exact author runtime and every published result are not blanket gates. The [v1 audit](../paper_runs/native_monthly_study_v1_20261116/REPORT.md) remains historical and does not override the current v2 admission.

## Current result

At 10bp per side, the bounded EFS base experiment has terminal wealth **9.842** for LLM search and **9.274** for grammar search, versus **11.361** for the initial library. The LLM minus grammar annual arithmetic increment is **+0.136 percentage points**. Its actual-138-factor paired alpha is **+0.177pp/year**, with pointwise 99% CI **[-2.426, +2.780]** and raw two-sided HAC p **0.861**. Incremental LLM value is not established; this is not proof that all LLM investment methods lack alpha.

The [v2 status package](../paper_runs/native_monthly_implementation_v2_20261116/README.md) contains source/replay checks, every economic-path disposition and aggregate results. Both methods have completed source/replay; only EFS has an admitted designated primary economic comparison. MarketSenseAI 2.0 and Signal or Noise retain unverified essential input channels.

## What is done and what remains

- Done: 69-paper census and native-monthly screen; actual 138-factor benchmark; recovered market inputs; five source variants with exact offline replay; EFS conditional economics and attribution.
- Partial: screening has 12 completed secondary paths and 18 blocked paths, including the LLM-screening primary and equal-weight control.
- Not done: resolve or bound screening payoff gaps and the other two cases' input gaps; reconcile the bounded study into the provisional paper.

Read the [project briefing](PROJECT_BRIEFING.md), [technical handoff](RESEARCH_HANDOFF.md), [presentation](presentations/LLM_INVESTMENT_STUDY_20261117_beamer.pdf), and [slide text](presentations/LLM_INVESTMENT_STUDY_20261117.md). A scheduler COMPLETED/exit0 is not financial admission: screening's retained failures demonstrate why both are checked.

## Benchmark and inference

Actual FF5 + momentum + fixed132 signed JKP U.S. vw_cap factors, with RF separate, cover 305 months August 1999–December 2024. The complete EFS window has286 months, rank138 and147 residual degrees of freedom. Screening's attempted232-month design has93 residual degrees of freedom, but design identification cannot repair a missing primary portfolio path. Short published stock windows remain too short for139 unrestricted parameters. No reduced factor substitute is used.

The 2pp/year economic margin, conservative multiplicity accounting and approximate HAC limits remain explicit. Insignificance is not equivalence, missing cases are not zero-alpha observations, and pointwise 99% intervals are not simultaneous margin bounds.

## Evidence locations

- [Current status](study/status.json) and [readiness CSV](study/method_readiness.csv).
- [V2 saved-evidence verification](../paper_runs/native_monthly_implementation_v2_20261116/verification.json).
- [Benchmark contract](../paper_runs/us_monthly_actual_factors_v1_20261116/benchmark_contract.json).
- [Authorized source, response and accounting evidence](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/artifacts/native_monthly_implementation_v2_20261116).

The current private handoff is `artifacts/native_monthly_implementation_v2_20261116/HANDOFF.md`. Original studies, failed attempts, v1 admission records and sealed manuscripts remain unchanged.
