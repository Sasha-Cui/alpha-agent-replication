# LLM investment study presentation

Verified November 17, 2026. Provisional study. This text accompanies the primary [Beamer PDF](LLM_INVESTMENT_STUDY_20261117_beamer.pdf) and [LaTeX source](LLM_INVESTMENT_STUDY_20261117_beamer.tex). 13 slides: 11 main slides plus two evidence appendices.

[Portable PDF](LLM_INVESTMENT_STUDY_20261117.pdf) · [Editable presentation](https://chatgpt.com/space/page_8240054152248191a27a0ae77e9bb674). PowerPoint export is available in the editable viewer. The PDF preserves the reviewed slide appearance; this Markdown provides searchable slide text and notes.

## Slide 1 — LLM investment methods

Results, completed work and remaining gaps

Native monthly U.S. equity study

Provisional · Status verified November 17, 2026

### Speaking notes

Status verified November 17, 2026 from saved source/replay and economic receipts. Both mechanisms completed source/replay. EFS economics completed; screening retains 18 failed primary/control-related paths. Overall paper remains provisional. Source: paper_runs/native_monthly_implementation_v2_20261116/status.json and verification.json in https://github.com/Sasha-Cui/alpha-agent-replication . No scientific job was rerun for this reporting update.

## Slide 2 — The investment question

Do published LLM investment methods add useful net performance beyond established equity factors?

Population: U.S. equities with native monthly investment decisions

Test: matched controls, explicit turnover costs and actual FF5 + momentum + JKP132

Implement the central method from the paper; exact author runtime and every published result are not required

### Speaking notes

Goal: incremental investment value after costs and actual-factor risk adjustment. Native monthly only is fixed; monthly reporting of daily trading is not eligibility. Paper-based central implementation is allowed. Sources: user scope instructions; artifacts/native_monthly_implementation_v2_20261116/native_evaluation_protocol_v2.json. No performance conclusion is established by this setup.

## Slide 3 — 69 papers reviewed; four monthly candidates

| Stage | Count | Meaning |
| --- | --- | --- |
| Original research census | 69 | Each paper retains its own evidence and gaps |
| Papers with some released code | At least 24 | A release can be a component, not a runnable strategy |
| Native monthly investment candidates | 4 | Three stock systems; EFS also tests preformed equity portfolios |
| Central methods with completed source/replay | 2 | EFS and Agentic AI Screening; financial admission differs |

These are overlapping review stages, not four independent success rates

### Speaking notes

The code census is not only four releases. At least 24 papers had some code; supporting artifacts and central strategies differ. Four monthly cases follow the resolved native-monthly scope. Two currently have usable data and bounded central implementations. Counts are not alpha successes or full-paper reproductions. Sources: user-confirmed census; all69_native_monthly_dispositions.csv under paper_runs/native_monthly_study_v1_20261116/. Read the separate records rather than aggregate a success rate.

## Slide 4 — The benchmark now uses actual factor returns

| Factor family | Number of series |
| --- | --- |
| Fama–French equity factors | 5 |
| Momentum | 1 |
| JKP signed U.S. monthly factors | 132 |
| Total risk controls | 138 |

305 months: August 1999–December 2024. The risk-free series is separate.

Raw-source readback and full factor rank verified; each strategy still needs its own calendar and rank check

### Speaking notes

Actual French 5 plus momentum 1 plus fixed 132 signed JKP U.S.vw_cap factors. The full panel has 138 factor rank and 166 residual degrees of freedom including an intercept: 305 - 139. No proxy/PCA/reduced factor span substitutes for the main benchmark. Source: https://github.com/Sasha-Cui/alpha-agent-replication/blob/main/paper_runs/us_monthly_actual_factors_v1_20261116/benchmark_contract.json and authorized benchmark_independent_readback_v1/validation.json under artifacts/us_monthly_actual_factors_verified_v2_20261116/.

## Slide 5 — The four monthly candidates

| Paper | Central method | Verified November 17 |
| --- | --- | --- |
| EFS | LLM factor evolution and sparse portfolios | Source/replay complete; 12 economic paths pass |
| Agentic AI Screening | Annual LLM rules and monthly sentiment screening | Source/replay complete; 18 economic paths blocked |
| MarketSenseAI 2.0 | Specialist analyses with qualitative fundamentals and retrieval | Essential historical input channels not yet verified |
| Signal or Noise | Synthesized recommendations and strong-buy portfolios | Same historical input gap |

Exact author runtime is not a blanket requirement. Input gaps remain explicit unfinished work.

### Speaking notes

M023 and M050 each completed their bounded source and exact offline replay. EFS 12/12 economic paths pass. Screening 12/30 pass; 18 fail held month-end coverage, including designated LLM nonhold and universeEW control. M016 and M052 essential dated qualitative/macro inputs remain unverified; exact author runtime is not the blanket gate. Original papers: https://arxiv.org/html/2507.17211v2 ; https://arxiv.org/html/2603.23300v2 ; https://arxiv.org/html/2502.00415v1 ; https://arxiv.org/html/2604.17327v1 .

## Slide 6 — The implementations being evaluated

EFS base experiment

Monthly FF25 equity portfolios
Three LLM evolution trajectories
Past-only factor selection and pooling

286 completed economic months
August 1999–May 2023

Controls: grammar search, initial library and universe equal weight

LLM screening experiment

Historical S&P 500 stock universe
Annual rules and exact replay complete
First-opening account coverage failed

232-month intended transfer
Primary comparison blocked

Controls: same-universe equal weight; sentiment and combined screens separately

### Speaking notes

EFS: 286 months August 1999–May 2023, three stochastic search trajectories on one shared market path, bounded base search on FF25. It omits some revised-paper pruning/weighting refinements and underlying-stock costs. Screening intended 232 months January 2005–April 2024, with 20 annual rules in each raw/log BM variant; source/replay complete but primary/control paths financially blocked. Current weights/accounting and sparse news are transfer limitations. Frozen contract: paper_runs/native_monthly_implementation_v2_20261116/native_evaluation_protocol_v2.json .

## Slide 7 — What is verified, and what remains unverified

| Evidence | Verified status | Interpretation |
| --- | --- | --- |
| Actual factor benchmark | Raw readback and rank pass | The intended 138 controls are available |
| CRSP market inputs | Raw values, opens and event flags recovered | Inputs are not complete funded accounts |
| Source and offline replay | All five primary variants pass | Three EFS trajectories; two screening variants |
| EFS economics | 12 of 12 conditional paths pass | Completed bounded base experiment |
| Screening economics | 12 of 30 paths pass; 18 blocked | Primary and matched control remain unavailable |

### Speaking notes

Fresh verification checked five saved source/replay state pairs, frozen helper/input bindings, scheduler COMPLETED/exit0 and every saved economic output hash. EFS 12 conditional accounts pass independent accounting. Screening also exited 0 but reports 12 verified paths and 18 failures; process success is not financial admission. Passed screening paths are FinBERT and buy-only secondary variants, not substitutes for the designated primary/control. Source: v2 status.json, economic_path_status.csv and verification.json.

## Slide 8 — EFS base results at 10bp turnover cost

| Metric | LLM search | Grammar | Initial library | Universe EW |
| --- | --- | --- | --- | --- |
| Terminal wealth | 9.842 | 9.274 | **11.361** | 7.953 |
| Annual mean return | 11.341% | 11.206% | **12.041%** | 10.491% |
| Annual excess Sharpe | 0.526 | 0.502 | **0.548** | 0.476 |

Higher is better in each row; bold marks the best value. August 1999–May 2023, 286 months.

LLM minus grammar alpha: +0.177pp/year
Pointwise 99% CI [−2.426,+2.780]; raw HAC p = 0.861

Incremental value is not established. Portfolio-unit fees exclude underlying stock costs.

### Speaking notes

Primary bounded EFS base experiment at 10 bp each-way turnover. Terminal wealth LLM 9.842143653660083, grammar 9.274228261076734, initial 11.360617039685973, universe 7.953374704278749. Annual arithmetic means 11.341201620%,11.205659892%,12.041066082%,10.490882306%; annual excess Sharpe .525752879,.501774314,.548309096,.476097029. LLM-grammar annual arithmetic increment +.135541728pp. Actual 138-factor paired alpha +.177155396pp/year,99%CI[-2.425739484,+2.780050276], raw p = 0.860833471, multiplicity-adjusted p = 1. LLM own actual 138 alpha -.824439269pp/year,99%CI[-3.444938318,+1.796059779], raw p = 0.417718562. Paired and absolute effects differ. Approximate HAC/pointwise inference, modern model/data vintage and base-method limits qualify the claim. Source: paper_runs/native_monthly_implementation_v2_20261116/efs/performance.csv, matched_effects.csv and actual_factor_attribution.csv . No new research execution for reporting.

## Slide 9 — Work still required before study closure

1

Screening held-asset payoffs

Verify the missing quote or terminal value at blocked endpoints

2

Primary and control accounts

Reuse frozen policies in a separate version; retain original failures

3

Remaining monthly inputs

Recover or bound essential inputs for the other two cases

4

Paper closure

Report all outcomes, unresolved cases and uncertainty

### Speaking notes

Source/replay is complete, not a remaining step. Screening primary/control paths block on held month-end marks in September 2008 and February 2007. Diagnose quote/terminal evidence; any repair needs separate version, preserved failures and the same declared calendar/policies. No automatic provider/source rerun, zero-fill or outcome-selected truncation. M016/M052 need essential historical input channels recovered or explicitly bounded. Paper closure remains. Source: current v2 status.json, screening/coverage_failures.csv and docs/RESEARCH_HANDOFF.md .

## Slide 10 — Bounded EFS result; overall study unfinished

The completed EFS test does not establish incremental LLM value

Screening’s primary is unavailable, not a negative result

Two other monthly papers still have unverified input channels

One bounded experiment cannot establish a literature-wide conclusion that LLM investment methods lack alpha

### Speaking notes

EFS paired actual 138 alpha at 10 bp +0.177pp/year; pointwise 99% CI[-2.426,+2.780], raw HAC p = 0.861. This bounded implementation does not establish incremental LLM value; uncertainty still spans the 2 pp margin. Screening’s primary/control are unavailable, not negative-alpha data. Do not generalize EFS or input gaps to all LLM methods. Sources: efs/actual_factor_attribution.csv, native_evaluation_protocol_v2.json and the current project brief.

## Slide 11 — Resolve remaining economics and revise the paper

Complete the missing primary comparison

Keep completed source fixed. Resolve or bound held-payoff gaps and preserve every financial failure.

Then reconcile the provisional paper

Describe a 69-paper review plus tests of the executable monthly cohort. Do not present it as 69 successful reproductions.

A separate LLM-improvement study follows closure of this attempt

### Speaking notes

Finish missing financial admission using completed frozen source, not new LLM optimization. Preserve all cases and failures. Revise the provisional paper around a 69-paper review and the smaller executed monthly cohort; do not claim 69 successful reproductions or universal no-alpha. A separate improvement study follows honest closure. Sources: docs/PROJECT_BRIEFING.md and docs/RESEARCH_HANDOFF.md .

## Slide 12 — Appendix · Limits that affect interpretation

| Condition | Implication |
| --- | --- |
| Current model weights and accounting vintage | Retrospective transfer; no pristine historical snapshot |
| Sparse historical news archive | Report observed coverage; missing articles are not no news |
| Preformed FF25 equity portfolios | Portfolio-unit results do not certify stock implementation costs |
| Short native stock-paper windows | Cannot identify an unrestricted 138-factor intercept |
| Conditional vendor terminal valuations | Keep settlement and held-price coverage gaps explicit |
| Approximate statistical inference | Pointwise uncertainty is not a simultaneous economic guarantee |

These limits qualify the claim; they are not observations of zero performance

### Speaking notes

Primary 10 bp turnover per side; 0/25 bp sensitivities. Cash/distribution and terminal conventions are conditional; missing held returns remain failures. The base EFS reconstruction does not implement every revised-paper refinement. No pristine holdout or human review is claimed. Sources: native_evaluation_protocol_v2.json; native_timing_amendment.json; factor_design_calibration_v1. Brief: https://chatgpt.com/space/page_241af5d039988191a8303e6573d61289 .

## Slide 13 — Appendix · Where the evidence lives

Project briefing

Objective, completed work, four-case review and unfinished work

Technical handoff

Saved jobs, exact working paths and checks needed to resume

Public repository

Paper census, benchmark contract, code and historical guides

Authorized Bouchet workspace

Protocols, source/replay records, licensed inputs and account checks

Repository includes the current briefing, portable deck and aggregate evidence

### Speaking notes

Current repo: https://github.com/Sasha-Cui/alpha-agent-replication . Brief: docs/PROJECT_BRIEFING.md; handoff: docs/RESEARCH_HANDOFF.md; presentation and notes: docs/presentations/; evidence: paper_runs/native_monthly_implementation_v2_20261116/. Live brief https://chatgpt.com/space/page_241af5d039988191a8303e6573d61289 ; technical Page https://chatgpt.com/space/page_2666d39e8e648191a18735ae9fedb6a0 . Fresh saved-evidence status verified November 17, 2026. Licensed inputs, holdings and replies remain private.
