# LLM investment study briefing

**Verified November 17, 2026; paper provisional.** Both paper-based monthly implementations completed source execution and exact offline replay. EFS completed 12 of 12 declared economic paths. Screening completed 12 of 30 paths; the other 18, including the designated LLM-screening primary and its equal-weight control, remain blocked by unpriced held month-end assets. Overall study and paper closure remain unfinished.

[Presentation](presentations/LLM_INVESTMENT_STUDY_20261117.pdf) · [Slide text and speaking notes](presentations/LLM_INVESTMENT_STUDY_20261117.md) · [Technical handoff](RESEARCH_HANDOFF.md) · [Editable presentation](https://chatgpt.com/space/page_8240054152248191a27a0ae77e9bb674)

## What we wanted to find out

The original goal was to test whether published LLM investment methods add useful net investment performance on U.S. monthly equities beyond **actual FF5 + momentum + JKP132**. Recovering code and reproducing components supports that test, but difficulty recovering a method does not by itself establish that it lacks alpha.

The broad census retains all 69 papers. At least 24 have some released code; a code release may be a component or supporting artifact. The user narrowed investment eligibility to **native monthly methods only**. Daily, weekly and quarterly decision processes are excluded; aggregating them monthly would change that scope. Four papers have eligible monthly experiments. Two have bounded central implementations with currently verified inputs; two retain essential historical-input gaps. This is a 69-paper review plus a smaller performance study, not 69 full-paper reproductions.

## What we implemented

The user permits faithful implementation of a paper's central method without its exact author runtime, byte-identical prompts, old checkpoint or every published result. Preserve central information channels, monthly cadence and decision logic; state routine reconstruction and transfer choices before outcomes. The older strict v1 empty-cohort decision is preserved as historical evidence and is superseded for current execution.

| Paper | What was executed or reviewed | Current state |
| --- | --- | --- |
| EFS | Three monthly FF25 base-search trajectories, causal pooling, matched grammar and initial-library controls | Source and exact replay complete; 12 conditional economic paths pass |
| Agentic AI Screening | Annual LLM-S with printed prompts and four real tools; frozen monthly FinBERT; stated ensemble and equal-weight comparisons | Both feature variants and exact replay complete; primary economic comparison blocked |
| MarketSenseAI 2.0 | Paper-based specialist/synthesis architecture reviewed | Dated qualitative fundamentals, earnings-call and macro-research channels not yet recovered and verified |
| Signal or Noise | Monthly specialist/synthesis recommendations and portfolio mechanism reviewed | Same essential historical-input gap; original recommendations alone are not a runtime prerequisite |

The EFS base run uses 42 seeds, 30 monthly input bars, 60 months of completed feedback, three proposal slots per month, a pool cap of 60 and ten selected factors/assets. These are disclosed researcher choices; the run does not cover every revised-paper pruning or optimized-weight refinement. Three search trajectories share one market history and are not three independent market trials.

## What is verified

The actual benchmark has **138 factors over 305 months, August 1999–December 2024**, with RF separate. Raw-source identities, units, signs, calendar and independent readback passed. Its full factor rank is 138; each strategy still needs its own calendar and design check. Characteristic proxies, FF6 and principal components do not replace the main factor span.

Unmodified CRSP monthly records, actual opening prices, historical membership and dated accounting inputs were recovered. Missing values and event flags remain preserved. These are input checks, not a universal certificate of complete corporate-action cashflows.

All five primary source variants passed exact saved-state offline replay: three EFS trajectories of 286 months each, and two screening feature variants with 20 annual policies each. EFS has 12 verified conditional accounts; screening has 12 verified secondary paths and 18 retained failures. A zero scheduler exit did not turn those failures into success. [Current receipt and aggregate tables](../paper_runs/native_monthly_implementation_v2_20261116/README.md).

## The completed EFS comparison

At 10bp per side, the bounded EFS base experiment has terminal wealth **9.842** for LLM search and **9.274** for grammar search, versus **11.361** for the initial library. The LLM minus grammar annual arithmetic increment is **+0.136 percentage points**. Its actual-138-factor paired alpha is **+0.177pp/year**, with pointwise 99% CI **[-2.426, +2.780]** and raw two-sided HAC p **0.861**. Incremental LLM value is not established; this is not proof that all LLM investment methods lack alpha.

Window: August 1999–May 2023, 286 months. Higher is better for every metric below; bold marks the best displayed value in each row, including ties. Returns are annualized arithmetic means, not calendar CAGR.

| Metric | LLM search | Grammar search | Initial library | Universe EW |
| --- | ---: | ---: | ---: | ---: |
| Terminal wealth multiple | 9.842 | 9.274 | **11.361** | 7.953 |
| Annual arithmetic return % | 11.341 | 11.206 | **12.041** | 10.491 |
| Annual excess Sharpe | 0.526 | 0.502 | **0.548** | 0.476 |

[Full performance CSV](../paper_runs/native_monthly_implementation_v2_20261116/efs/performance.csv) · [Matched effects](../paper_runs/native_monthly_implementation_v2_20261116/efs/matched_effects.csv) · [Actual-factor attribution](../paper_runs/native_monthly_implementation_v2_20261116/efs/actual_factor_attribution.csv)

The LLM's own net excess-return alpha against actual 138 controls is -0.824pp/year, with pointwise 99% CI [-3.445, +1.796] and raw p 0.418. The paired comparison is a different estimand. The saved conservative 69×192 p-values are 1.0. Approximate HAC intervals can undercover with persistent errors; pointwise intervals do not establish simultaneous economic-margin bounds.

## Why screening remains incomplete

The intended transfer covers January 2005–April 2024, 232 months, with completed prior-month information and first-opening stock fills. Both annual-rule variants completed source/replay. The LLM-screened and combined non-hold paths fail an unpriced held endpoint in September 2008; the same-universe equal-weight control fails a held endpoint in February 2007. All 18 fee/feature failures are retained. No missing held return was zero-filled or month silently removed.

The 12 completed paths are sentiment-only and buy-only secondary variants. They do not supply the missing designated primary or its matched control. The news archive is sparse and uneven; missing archived articles are not proof that no relevant news existed. Public failure tables omit held security identifiers and values; exact witnesses remain private.

## What remains unfinished

1. Resolve the held-asset pricing or terminal-payoff evidence needed for screening. Any accounting correction must use a separate version and the already frozen policies, with preserved failures; no automatic model rerun or outcome-selected truncation.
2. Complete the screening primary and its same-universe control, or explicitly conclude that those financial paths remain unavailable.
3. Resolve or bound the essential input gaps for MarketSenseAI 2.0 and Signal or Noise. Missing cases remain in the denominator and are not zero-alpha observations.
4. Reconcile all outcomes, uncertainty, sensitivity results and limitations into the provisional paper. Source completion is no longer pending; the remaining gap is economic admission and reporting closure.

## Claim boundaries and next decision

The primary fee is 10bp per side, with 0/25bp sensitivities. EFS fees apply to preformed portfolio units and exclude unobserved underlying-stock implementation costs. Stock distributions and terminal values use explicit vendor cash-equivalent conventions, not independently certified historical settlement or merger exchange ratios. Current model weights, date-bearing research prompts and restated accounting do not provide a pristine historical snapshot or untouched holdout. Assistant verification is not external human review.

The EFS result is evidence about one bounded base-search implementation. It does not support a literature-wide no-alpha claim. The screening primary is unavailable rather than negative. Finish this bounded attempt and revise the paper before starting a separate LLM-improvement study.

## Reading the evidence

Start at [README](../README.md), then [current study](CURRENT_STUDY.md), the [69-paper inventory](study/method_readiness.csv), the [v2 aggregate package](../paper_runs/native_monthly_implementation_v2_20261116/README.md) and the [technical handoff](RESEARCH_HANDOFF.md). Match the source protocol, input bindings, replay, funded accounts and attribution before interpreting a result. Licensed inputs, holdings and response stores remain private. The [editable written brief](https://chatgpt.com/space/page_241af5d039988191a8303e6573d61289) and presentation mirror this status; the repository versions can be read without Pages access.
