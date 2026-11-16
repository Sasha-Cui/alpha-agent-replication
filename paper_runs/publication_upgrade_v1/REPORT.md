# Economic Fidelity Before Alpha

Source-based financial LLM mechanisms, matched controls, calibrated inference, and a prospective research pilot

Research draft: all six case studies executed; independent human review and future pilot outcomes remain pending.

This study separates three questions: whether a released mechanism can be executed, whether it improves a matched economic outcome, and whether the observations identify incremental alpha relative to a specified benchmark. The historical experiments use modern model endpoints and disclosed data/execution adapters. They do not reproduce the original papers in full.

## Abstract

We extend an existing 69-paper availability audit and 62 common U.S. transfer paths with six source-specific case studies: EFS, FinMem, FinAgent, TradingAgents, GuruAgents, and QuantaAlpha. The implementations restore native decision cadence and substantive mechanisms, use real model calls where applicable, and distinguish source scores from self-financing portfolio returns. Controls isolate search, memory retrieval, risk discussion, tool routing, and released-factor inclusion. We also examine trading costs, execution timing, trading cadence and information latency. A calibration exercise rejects standard short-sample bootstrap intervals as overly optimistic and motivates conservative grouped-estimator bounds, validated on a separate simulation seed. Short native histories are not treated as identified unrestricted JKP132 regressions. Finally, an immutable local forecast record begins a prospective development pilot. The resulting evidence is conditional on the disclosed implementations and realized model trajectories; insignificant results are not interpreted as proof of no economically meaningful alpha.

Across 6 completed primary comparisons, the number meeting the declared Holm-adjusted positive-effect criterion is 0; the number unresolved against the 2 percentage-point annual economic margin is 6. EFS illustrates an accounting-sensitive result: the LLM path trails its initial library before fees but leads it after 10-basis-point trading costs. FinMem's positive directional log score coexists with a negative cash-adapter return. These observations support an audit of economic definitions and identification limits, rather than a universal absence-of-alpha conclusion.

## 1. Research question and evidence boundaries

The previous study evaluated 62 common JKP transfer paths: 17 carried evaluations and 45 explicitly researcher-authored reconstructions, with seven structural exclusions from the 69-paper census. Its manifest records zero full native systems reproduced end to end. Those artifacts remain frozen. A transfer result cannot by itself adjudicate a paper whose original information, cadence, action semantics or portfolio was replaced.

The new cohort is selected for recoverable mechanisms and useful contrasts, not as a random sample of all financial-agent papers. EFS is a paper-guided numerical reimplementation. FinMem, FinAgent and TradingAgents execute released core code with explicit adapters. GuruAgents reuses 190 actual source-prompt/tool replays. QuantaAlpha reexecutes a released factor library, predictor and portfolio; it does not rerun the original LLM search. FINSABER provides an alternative dated input source and an important neighboring benchmark, so the contribution here is the source-to-accounting audit and controlled economic attribution rather than a generic claim that LLM trading underperforms.

| Case | Executed object | Primary contrast |
| --- | --- | --- |
| EFS | Paper-guided search | LLM vs 10 grammar seeds |
| GuruAgents | Actual source-prompt replays | Tool routing vs one final call |
| QuantaAlpha | Released factors + native predictor | 170 vs 20 factors |
| FinMem | Released actor and memory | Layered vs semantic retrieval |
| TradingAgents | Released role graph | Full vs no risk discussion |
| FinAgent | Released multimodal pipeline | Full vs no retrieval |

[Full audit](source_review/packet_manifest.json)

## 2. Economic contracts

For source actors without a complete investable account, the research adapter maps BUY to a fully invested long position, SELL to cash, and HOLD to retaining the target. The primary signal uses completed information and executes at the next close. FinAgent instead retains the released whole-share buy/sell methods, while repairing the account clock: the prior order fills and NAV is marked at the current close before the actor observes its account. Date-only news and filings become available on the strictly next trading session. These are explicit assumptions, not recovered original execution logs.

| Case | Primary trading cost | Execution rule |
| --- | --- | --- |
| EFS | 10 bps per traded notional | Next close |
| FinMem | 10 bps research account | Next close; source score separate |
| FinAgent | 10 bps; whole shares | Prior order fills before current decision |
| TradingAgents | 10 bps research account | Next close |
| GuruAgents | 1 bp source convention | First close after quarter end |
| QuantaAlpha | 5 bps buys / 15 bps sells | Native Qlib open execution |

[Full audit](source_review/packet_manifest.json)

Cash earns zero interest in the source-style accounts. The reported costs cover the stated security-trading fees; market impact, taxes and unavailable vendor or financing costs are not manufactured. The exact code and input assumptions determine each comparison.

$$
G_t=C_{t-1}+\sum_i D_{i,t-1}(1+r_{i,t})
$$

$$
N_t=G_t-c\sum_i\left|N_t w_{i,t}-D_{i,t-1}(1+r_{i,t})\right|
$$

Here G is pretrade marked capital, N is post-fee capital, D is security value, C is cash and c is cost per traded notional. Cash itself is not charged as a second security trade. The implementation solves the self-financing fee equation and permits uninvested cash. Between scheduled rebalances, positions drift. Reported trade notional is the sum of absolute security trades divided by pretrade NAV; it is not half-L1 turnover.

Native conventions remain visible. FinMem's published signed-log score, its cumulative one-share feedback state, and the researcher's cash/stock account are different objects. QuantaAlpha's native annualized return is benchmark-relative after costs, not standalone CAGR. GuruAgents' released notebook explicitly renormalizes percentage-weight totals to 100, so that source convention is preserved. A 90-day information-lag stress is reported separately and does not certify point-in-time fundamentals or eliminate restatements.

$$
S_{\rm FinMem}=\sum_t a_t\log(P_{t+1}/P_t)
$$

The source score above is not cumulative portfolio return. HOLD contributes zero to this score, while a held portfolio can still earn or lose money. Source metric reproduction and economic portfolio reproduction are therefore reported separately.

| FinMem path | Directional log score x100 | Cash-adapter total return (%) | Cash-adapter drawdown (%) |
| --- | --- | --- | --- |
| Layered retrieval | +11.15 | -16.29 | -52.70 |
| Semantic retrieval | -2.49 | -14.37 | -52.26 |

[Full audit](analysis/economic_performance.csv)

The FinMem comparison above changes the measured economic object. A positive directional score and a negative long-only cash-account return can coexist because SELL and HOLD have different meanings in the score and the funded account. The cash mapping is an explicit research adapter, not a recovered original financing policy. Neither its loss nor the source score alone adjudicates every possible implementation of the paper.

Read-only instrumentation of the native guardrail records 60 training validation failures and 0 test validation failures. Source fallback behavior remains part of the executed system; these events are not relabelled as successful language-model reasoning. Both evaluation arms share the same trained state.

## 3. Matched design and statistical estimands

EFS controls use the same 290 search dates and 870 returned-code proposal slots, evaluator, trailing information, pruning, portfolio size and execution clock. All ten grammar seeds are retained; they are randomization replicates over one shared market history, not ten independent histories. The grammar is narrower than unrestricted model-generated Python. Other primary comparisons preserve their stated external information and account constraints while removing the relevant mechanism. The GuruAgents ensemble averages all five source roles as a research aggregation; every role is also reported separately.

The economic margin is fixed at 2 percentage points of annualized arithmetic return advantage. CAGR and drawdown are descriptive portfolio metrics. The uncertainty interval targets an annualized paired mean, or an intercept conditional on an explicitly specified factor model; it is not a CAGR interval. All factor coefficients are refitted when the estimator is resampled or estimated by block.

$$
\widehat{\Delta}_{\rm ann}=f\,\frac{1}{q}\sum_{b=1}^{q}\widehat{\Delta}_b,\qquad s=\frac{\operatorname{sd}(\widehat{\Delta}_1,\ldots,\widehat{\Delta}_q)}{\sqrt{q}}
$$

$$
\mathrm{CI}_{\rm primary}=f\left[\overline{\Delta}\ \pm\ t_{q-1,0.995}\,s\right]
$$

Primary bounds use contiguous-group estimator t inference with nominal 99% intervals. Four groups are used for paired means; a low-dimensional factor regression uses three when four would leave inadequate block-level residual degrees of freedom. The estimator requires approximately independent, approximately normal block estimates. Simulation checks support its behavior only on the tested designs, not every financial process. Primary zero-effect p-values receive Holm family adjustment; bounds remain explicitly casewise. Identical or degenerate observed paths do not establish population equivalence. Time-series uncertainty is conditional on these realized model trajectories and does not estimate variation across model generations.

## 4. Paired economic effects

### Figure 1. Effects relative to matched controls

Panels use different horizontal scales. Shading marks the +/-2 percentage-point margin. Intervals are nominal 99% grouped-t bounds, conditional on the stated study and model-trajectory assumptions.

| Case | Paired observations | Effect (pp/year) | Primary interval |
| --- | --- | --- | --- |
| EFS | 72 months | +13.18 | [-19.5, 45.9] |
| GuruAgents | 36 months | -2.29 | [-10.1, 5.6] |
| QuantaAlpha | 48 months | -1.48 | [-21.7, 18.8] |
| FinMem | 127 days | -2.10 | [-111.2, 107.0] |
| TradingAgents | 61 days | -6.33 | [-293.6, 281.0] |
| FinAgent | 147 days | -14.61 | [-162.2, 133.0] |

[Full audit](analysis/paired_effects.csv)

A confidence interval overlapping the economic margin leaves the claim unresolved. A negative point estimate or a conventional nonsignificant test is insufficient to establish absence of useful alpha. Conversely, an apparent gain in raw portfolio return can reflect market exposure, turnover, cost or the account adapter. The matched contrasts and factor-model boundaries limit the interpretation.

| Case | Approx. 80% power effect (pp/year) | Holm-adjusted zero-effect p |
| --- | --- | --- |
| EFS | 37.4 | 0.599 |
| GuruAgents | 9.0 | 0.935 |
| QuantaAlpha | 23.2 | 1.000 |
| FinMem | 124.9 | 1.000 |
| TradingAgents | 328.7 | 1.000 |
| FinAgent | 168.8 | 1.000 |

[Full audit](analysis/paired_effects.csv)

The power column is a planning approximation: the estimated grouped standard error multiplied by the nominal 99% t critical value plus the normal 80% power quantile. It is casewise, does not incorporate Holm adjustment or model-generation variability, and is not a guaranteed detection threshold. Large values show why these windows cannot settle a 2 percentage-point economic question. A degenerate realized difference is labelled not estimable rather than assigned zero population uncertainty.

### Figure 2. Portfolio paths over multi-year windows

Initial capital is normalized to 100. Native windows and source fee conventions differ across cases; the relevant comparisons are within panels. Tables show cumulative changes in wealth; annualized metrics remain in the audit.

| Case | Tested total return (%) | Control total return (%) | Tested max DD (%) |
| --- | --- | --- | --- |
| EFS | 142.67 | 17.82 | -50.33 |
| GuruAgents | 58.42 | 69.57 | -19.91 |
| QuantaAlpha | 9.86 | 10.17 | -29.54 |

[Full audit](analysis/economic_performance.csv)

### Figure 3. Portfolio paths over short native windows

Initial capital is normalized to 100. Native windows and source fee conventions differ across cases; the relevant comparisons are within panels. Tables show cumulative changes in wealth; annualized metrics remain in the audit.

| Case | Tested total return (%) | Control total return (%) | Tested max DD (%) |
| --- | --- | --- | --- |
| FinMem | -16.29 | -14.37 | -52.70 |
| TradingAgents | -11.66 | -10.14 | -12.94 |
| FinAgent | -4.67 | 4.41 | -34.42 |

[Full audit](analysis/economic_performance.csv)

Over June–December 2023, the FinAgent whole-share account returns -4.67%, versus +4.41% without retrieval and +15.78% for the matched-clock buy-and-hold reference. The annualized paired mean difference is -14.61 percentage points, with primary bounds [-162.2, 133.0]. Retrieval does not improve this realized trajectory; the wide bounds and one TSLA/model trajectory leave its general economic effect unresolved.

## 5. Costs and controlled adaptations

### Figure 4. EFS trading costs and cadence

All paths use the fixed generated factors and the same information. Weekly/monthly variants alter trading times and allow weights to drift; they do not manufacture daily rebalancing between those dates.

| Path | Daily CAGR (%) | Weekly CAGR (%) | Monthly CAGR (%) |
| --- | --- | --- | --- |
| LLM | 15.95 | 21.77 | 31.51 |
| Initial library | 13.96 | 17.78 | 28.07 |
| Equal weight | 28.90 | 29.16 | 28.79 |

[Full audit](analysis/controlled_adaptations.csv)

In the completed EFS pilot, gross CAGR is 30.42% for the initial library and 26.57% for the LLM path; at 10 bps, the ordering reverses to 13.96% and 15.95%. This is a cost-channel reversal at fixed signal paths, not evidence that LLM factor generation improves gross returns. The equal-weight reference is 28.90% net at 10 bps. These previously completed paths are preserved, while the new grammar controls address the additional value of model search more directly.

### Figure 5. GuruAgents information-lag stress

The fixed evaluation window is April 2022 through March 2025. Delayed paths remain in cash until their first eligible formation. The lag is a sensitivity analysis, not a certification of original filing timestamps.

| Mode | Extra lag (days) | Net CAGR (%) |
| --- | --- | --- |
| Tool routing | 0 | 11.16 |
| Tool routing | 90 | 14.20 |
| One final call | 0 | 12.91 |
| One final call | 90 | 14.81 |

[Full audit](analysis/controlled_adaptations.csv)

The extra 90-day lag changes which market conditions each recommendation encounters. In this historical window it raises both ensemble point returns; that does not establish that a delayed rule is preferable. Both timing variants are retained, and neither supplies the missing original publication-vintage evidence. This sensitivity shows why the mapping from a financial statement period to a tradable holding period must be explicit.

### Figure 6. Predictive and economic outcomes differ

The two panels have different metrics and scales. Native annual return is benchmark-relative after source fees; drawdown is also the native benchmark-relative metric. This comparison conditions on the released factor pool and does not establish the causal value of fresh LLM discovery.

| Library | IC | Net above benchmark (%/yr) | Native drawdown (%) |
| --- | --- | --- | --- |
| 20 core factors | 0.0051 | 4.63 | -22.19 |
| 170 released factors | 0.0423 | 3.61 | -12.56 |

[Full audit](quantaalpha_native_metrics.json)

Adding the released custom factors improves the native predictive correlations and reduces the native benchmark-relative drawdown, while the fixed portfolio earns a lower annual benchmark-relative return. These are different economic dimensions. The result supports a component-level comparison of this predictor and portfolio, not a general statement that predictive accuracy cannot create value or that the original search process has been reproduced.

## 6. Calibration and factor identification

### Figure 7. Calibration rejects optimistic short-sample intervals

Representative design: 72 monthly observations, six factors, AR(0.3) noise. Error bars are 95% Monte Carlo intervals for rejection rates. The dashed 5% line is an operating target, not the nominal size of the deliberately conservative 99% interval.

| Method | MC replications | False rejection (%) | MC interval (%) |
| --- | --- | --- | --- |
| Basic SB 95% | 600 | 12.67 | [10.24, 15.57] |
| Bootstrap-t 95% | 600 | 10.33 | [8.14, 13.03] |
| Grouped t 95% | 2000 | 5.45 | [4.54, 6.53] |
| Primary grouped t 99% | 2000 | 1.60 | [1.14, 2.25] |

[Full audit](visual_tables/calibration_full_audit.csv)

Independent-seed validation spans 36, 72 and 144 observations; AR coefficients 0, 0.3 and 0.6; Gaussian, Student-t(5) and deterministic heteroskedastic noise; and paired means or six-factor intercepts. There are 54 design cells, each with 2,000 replications. Primary nominal 99% bounds cover the true zero effect in 98.40% to 99.55% of these simulated samples. This supports conservative use on this grid, not an unconditional guarantee for arbitrary financial dependence or model-generation variation.

A known static 132-factor span is recovered to numerical precision when the sample identifies it. The short 72-by-132 regression is refused. A candidate constructed entirely from the observed JKP factors still produces nonzero chronological ridge/PCA reconstruction errors. Such errors reflect regularization and estimation as well as any omitted payoff; their mean is not automatically independent alpha.

| Issue | Treatment |
| --- | --- |
| Unrestricted JKP132 + market | Report not identified when sample/rank is insufficient |
| Six-factor projection | Explicit conditional model; coefficients refit within groups |
| Chronological ridge/PCA residual | Reconstruction diagnostic, with no spanning-alpha p-value |
| 2pp materiality | Bounds/equivalence; no inference from nonsignificance alone |
| Identical observed paths | No population equivalence claim from zero sampled variation |

[Full audit](analysis/factor_attribution.csv)

## 7. JKP-only versus agent-augmented allocation

### Figure 8. A fixed chronological allocation diagnostic

Both versions use the same past-only scaling, diagonal covariance shrinkage and utility rule. Training starts with 36 months and evaluation covers the subsequent 36 months. Factor internal turnover, financing and allocation costs are unavailable; this is not a deployable net fund or a test of the best factor frontier.

| Allocator | CAGR (%) | Volatility (%) | CE, gamma=10 (%/yr) |
| --- | --- | --- | --- |
| JKP only | 0.43 | 1.11 | 0.37 |
| JKP + EFS | 0.39 | 1.12 | 0.33 |

[Full audit](jkp_allocation_diagnostic/metrics.csv)

The allocation comparison answers a narrower question than factor spanning: whether this fixed past-only regularized rule benefits from being offered the EFS return stream. It does not identify the best attainable JKP frontier. The implementation is invariant to constant factor-unit rescalings and sign conventions, and a future-data perturbation test leaves earlier allocations unchanged. Exposures are coefficients on the supplied return series; their interpretation depends on the underlying factor portfolios and omitted financing costs.

## 8. Prospective record and independent review

### Figure 9. A prospective development pilot has begun

Four targets were committed together: LLM search, grammar search, the initial seed library and equal weight. This is a local development-pilot seal, not public preregistration or confirmatory evidence. No future return is supplied or invented.

| Record | Value |
| --- | --- |
| Forecast recorded | 2026-09-07T08:37:47.303509+00:00 |
| Execution close | 2026-09-08T20:00:00+00:00 |
| Evaluation close | 2026-09-09T20:00:00+00:00 |
| Eligible assets | 50 |
| Human review / public registration | Pending |

[Full audit](prospective_summary.json)

Forecast digest: 34b9c4fcbf349c1f04fff4ff6b81a64bdb2a1aa0f4a1e9a2531887241db77c53. The harness checks timezone-aware information availability, requires recording before execution and evaluation, links records by hashes, rejects replacement forecasts, and refuses to record outcomes before their evaluation close is observable. Settlement makes no new model calls. Future observations remain pending until the evaluation close.

Six outcome-free source-review packets and a code review bundle are available. The human-review ledger is empty unless an actual independent reviewer supplies an attested, hash-matched review. Automated compilation, tests, source checks and cached replay do not count as human review. A changed packet invalidates prior approval for that packet; unresolved reviewer objections remain visible.

## 9. Reproducibility, limitations and publication readiness

At this report's ledger snapshot, project research spending is 100.81 USD committed: 100.20 USD in known or tariff-accounted charges and 0.60 USD in conservative unresolved reservations. There are 0 in-flight requests. This includes prior imported usage, setup attempts, summaries, embeddings, recoveries and the prospective pilot; it is not a production-cost estimate.

| Cached source trace | Compared records | Differences | Maximum numeric difference |
| --- | --- | --- | --- |
| FinMem | 538 | 0 | 0.000000 |
| FinAgent | 544 | 0 | 0.000000 |
| TradingAgents | 61 | 0 | 0.000000 |

[Full audit](replay_summary.json)

Full cached replay compares decisions, economic state, timing, reasoning, memory fields and request/response identities. Only transport-cache flags and the order of independent transport events are ignored. It verifies deterministic reconstruction of the saved trajectory without new paid calls; it does not estimate uncertainty across fresh model generations or validate unavailable historical endpoints. The original EFS replay and independent account checks remain separately frozen.

All earlier studies remain intact. Paid requests share a project ledger with a soft spending stop of 450 USD below the 500 USD ceiling. Complete responses are persisted before accounting settlement, and unavailable responses retain conservative reservations. A shared SQLite write-lock failure, a development-allocation rollover and provider HTTP 500/read timeouts and compute-node network failures were recorded and reconciled; missing responses and their conservative charge bounds were not erased. Independent source embedding providers replace the early generic embedding adapters. An attempted batching optimization failed a full-prefix equivalence check and was retired; its responses and diagnostic failures remain available.

The source settings and modern substitutions limit external validity. Original vendor vintages and model snapshots are generally unavailable. Source universes can carry selection concerns. Current models may contain historical market information in pretraining even when supplied inputs are correctly timed. Short native windows and one realized model trajectory per arm constrain power and generalization. QuantaAlpha's released factor pool can contain selection informed by its historical test, so its comparison conditions on that pool. API/data/engineering costs are distinct from security trading costs; factor-sleeve financing and internal costs are not manufactured where holdings are missing.

The material deliverable is an auditable source-to-economic-account experiment and a calibrated statement of what the evidence identifies. The manuscript is a research draft for independent review. A claim of universal absence of alpha, original-paper reproduction, or prospective investment value would exceed this evidence. Independent source review and a substantially larger forward record are the remaining scientific conditions for stronger publication claims.

| Case | Study model / numerical route | Declared scope |
| --- | --- | --- |
| EFS | GPT-4.1, temperature 0.3 | Paper-guided factor search; current model |
| FinMem | GPT-4-Turbo, temperature 0.7; native Ada002 wrapper | Paper K=5; one TSLA trajectory per arm |
| FinAgent | GPT-4o, temperature 0.1; native 3-large/3072 embedding provider | Historical chat IDs unavailable; explicit current decoding choice |
| TradingAgents | GPT-4o, temperature 0.1 | Original v0.1.0 role graph; model-role substitution |
| GuruAgents | GPT-4o, temperature 0 | Actual source-prompt/tool replay |
| QuantaAlpha | Native LightGBM, seed 42; released factor library | No new LLM-search execution |

[Full audit](source_review/packet_manifest.json)

The final embedding computations are source-specific. FinMem delegates tokenization, document batching and normalization to its released wrapper. FinAgent executes the released provider configured for text-embedding-3-large with 3,072 dimensions, while prefetching independent per-document requests concurrently. The attempted generic Ada batching optimization did not preserve a saved training prefix and was rejected. These checks limit implementation drift; they do not establish equivalence to unavailable historical model services.

## 10. Artifact index and reproduction

| Artifact | Role |
| --- | --- |
| analysis/paired_effects.csv | Primary/secondary effects, bounds and Holm family fields |
| analysis/controlled_adaptations.csv | All declared cost/cadence/latency account variants |
| source_review/ | Outcome-free packets, templates and real review ledger |
| grouped_inference_validation_v2/ | Independent simulation validation |
| jkp_allocation_diagnostic/ | Past-only conditional allocation comparison |
| artifacts/publication_upgrade_v1/ | Private inputs, responses, accounts and recovery evidence |

The private execution inputs and response cache are separate from public presentation tables. Individual-security data, raw news and API responses remain private. File hashes, source pins, central environment paths and documented adapters are part of the reproducibility record. Reproduction requires the listed central environments or equivalent reconstructed dependencies and access to the appropriately licensed data.

```bash
cd /nfs/roberts/project/pi_btk22/zc362/alpha_evolve
# See docs/PUBLICATION_UPGRADE_RUNBOOK.md for complete cached replays.
ENV_ROOT=/nfs/roberts/project/pi_btk22/zc362/environments
PUBLICATION_PY="$ENV_ROOT/venvs/alpha-agent-replication-py312-20260813/bin/python"
"$PUBLICATION_PY" scripts/analyze_publication_upgrade.py
"$ENV_ROOT/bin/kt-python" scripts/build_publication_report.py
"$ENV_ROOT/bin/kt-python" scripts/validate_publication_report.py
# After the committed future evaluation close is observable:
scripts/run_finmem_fidelity_python.sh scripts/run_efs_prospective.py --settle-only
```

## References

[1] EFS: Evolutionary Factor Searching for Sparse Portfolio Optimization Using Large Language Models, v1. https://arxiv.org/abs/2507.17211v1

[2] FinMem: A Performance-Enhanced LLM Trading Agent with Layered Memory and Character Design. https://arxiv.org/abs/2311.13743

[3] A Multimodal Foundation Agent for Financial Trading: Tool-Augmented, Diversified, and Generalist. https://arxiv.org/abs/2402.18485

[4] TradingAgents: Multi-Agents LLM Financial Trading Framework, v7. https://arxiv.org/abs/2412.20138v7

[5] GuruAgents: Emulating Wise Investors with Prompt-Guided LLM Agents. https://arxiv.org/abs/2510.01664

[6] QuantaAlpha, v3. https://arxiv.org/abs/2602.07085v3

[7] FINSABER benchmark and released alternative data. https://arxiv.org/html/2505.07078v6

[8] Politis and Romano (1994), The Stationary Bootstrap. https://doi.org/10.1080/01621459.1994.10476870

[9] Newey and West (1987), A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix. https://www.jstor.org/stable/1913610

[10] Ibragimov and Muller (2010), t-Statistic Based Correlation and Heterogeneity Robust Inference. https://www.princeton.edu/~umueller/tstat.pdf

[11] Schuirmann (1987), A comparison of the two one-sided tests procedure and the power approach for assessing equivalence. https://pubmed.ncbi.nlm.nih.gov/3450848/
