# Frozen confirmatory analysis protocol

**Project:** From Reported Alpha to Reproducible Returns

**Decision owner and sole author:** Sasha Cui

**Protocol frozen:** 2026-08-02, before inspecting any non-USA candidate-return outcome

**Cutoff for public systems and artifacts:** 2026-08-02 23:59 UTC

## Purpose and evidentiary boundary

The existing USA proxy results through 2024-11 have already been inspected. They are exploratory and no USA date segment is a locked test. The confirmatory performance analysis is a geographic/domain validation on Canada, France, Germany, Italy, Japan, and the United Kingdom. Before this protocol was written, only file availability, date coverage, and cross-sectional counts were inspected for those markets; no candidate returns, factor-adjusted performance, strategy direction, or ranking was viewed.

A public artifact failure is not a zero return and is not evidence that the underlying method lacks alpha. A mechanism-inspired JKP proxy is not an output or replication of the named agent. The primary contribution is an artifact-to-evidence attrition audit. Performance claims are restricted to streams that actually enter the frozen evaluator.

## Research questions

1. What fraction of in-scope systems expose public artifacts sufficient to reconstruct their native claimed evaluation and dated returns?
2. Among public artifacts, where does evidence attrit: legal availability, environment reconstruction, data/model access, execution, valid dated output, or evaluator compatibility?
3. Do the already-frozen mechanism-inspired proxy portfolios deliver positive net alpha in a previously uninspected G7-ex-USA domain after multiplicity control?
4. Are any effects economically material after a stylized 10-basis-point one-way transaction cost?

## Census and registry lock

The unit is a named system/version lineage, not a paper, repository, benchmark row, or citation. Publications and artifacts are linked many-to-one to systems. The registry uses five strata:

- `F`: formulaic or cross-sectional alpha systems that generate, score, search, or select executable factors or factor portfolios;
- `T`: sequential trading or portfolio agents that emit dated actions or weights and have a closed-loop historical, paper, or live evaluation;
- `B`: benchmarks, audits, or evaluation environments for `F` or `T` systems;
- `C`: community software without a peer-reviewed or otherwise sufficiently specified system claim;
- `M`: non-LLM mechanistic comparators.

The main system denominator is `F + T`. Other strata are reported separately. Alpha-GPT versions are one lineage. Curated lists are discovery sources, not systems. Static prediction or QA papers without a tradable output, generic finance assistants, and market-simulation behavior studies are excluded with reasons.

Search families are run from inception through the cutoff in arXiv (cs.AI, cs.CL, cs.LG, cs.CE, q-fin.CP, q-fin.PM, q-fin.ST, q-fin.TR), ACL Anthology, OpenReview, ACM Digital Library, and SSRN; Crossref/OpenAlex are used for deduplication. GitHub is used only to locate exact-title, author-linked, or publication-linked public artifacts. The exact query families are:

1. `(LLM OR "large language model" OR agent* OR multi-agent) AND ("alpha mining" OR "factor discovery" OR "formulaic alpha" OR "strategy generation")`;
2. `(LLM OR "large language model" OR agent*) AND (trading OR portfolio OR "stock selection") AND (return OR Sharpe OR backtest OR live)`;
3. `(benchmark OR evaluation OR audit OR reproducib* OR artifact OR leakage) AND ("alpha mining" OR "trading agent*" OR "quantitative investment")`.

Backward and forward citation chasing starts from AlphaBench, AlphaQT-Bench, FINSABER, and the Agentic Trading survey. The registry and search log are frozen by SHA-256 in `paper_runs/submission_evidence/analysis_lock.json`. Additions discovered after the cutoff are documented but cannot change confirmatory denominators.

## Fidelity and failure taxonomy

Fidelity classes are mutually exclusive:

- `official_native`: official artifact executed under the claimed protocol;
- `official_adapted`: official code or expressions adapted to the common input/output contract;
- `independent_reimplementation`: the published mechanism independently implemented from a sufficiently explicit specification;
- `mechanism_inspired`: a thematic economic mapping that omits central components and is not a replication;
- `artifact_unavailable`, `legally_unusable`, or `technically_incompatible`.

Execution outcomes are: valid dated native returns; valid dated adapted returns; executed without dated strategy returns; artifact unavailable; legally unusable; task/data incompatible; install/infrastructure failure; runtime/invalid-output failure; and valid empirical output that fails the benchmark. Failures remain in the planned denominator and are never imputed as returns.

Artifact levels are `R0` paper only, `R1` code/configuration, `R2` runnable inputs/dependencies/prompts/adapters, `R3` exact native reproduction with dated returns, and `R4` independent common-task reproduction.

## Frozen proxy family

The secondary performance family contains all 62 already-defined proxy portfolios, including poor and failed rows. Candidate IDs, formula ingredients, signs, formation lag, portfolio rule, and source labels are frozen from `scripts/run_paper_idea_jkp_proxies.py`. No candidate may be reoriented, renamed to imply native fidelity, removed after failure, or selected because of an international result. One textually closest proxy per source is flagged for presentation, but all 62 remain in the multiplicity denominator.

The ContestTrade trailing-selection proxy has a 24-month warm-up and is analyzed on its resulting shorter calendar; it remains in the 62-test family as a non-rejection when unavailable on a common month.

## Geographic validation universe

The validation markets are the six G7 members outside the United States: `CAN`, `FRA`, `DEU`, `ITA`, `JPN`, and `GBR`. This institutional rule was chosen before outcomes were viewed. The primary analysis window is 1999-07 through 2024-11, subject to a candidate's formation warm-up.

Portfolios are formed independently within each country from the point-in-time JKP characteristic files. The security identifier is the country-file `id`. At each month, securities with a valid formation date, positive market equity, a valid lead excess return, and the required score inputs are eligible. The largest 1,000 securities by market equity are retained; smaller markets use all eligible securities. No strategy-specific price or common-share filter is added because the frozen USA constructor did not apply one.

Long-short candidates buy the top score decile and short the bottom score decile, value weighted within each side, with one dollar long and one dollar short. Long-only candidates follow their frozen top-decile or top-five rule. A side requires at least 20 securities. Signals observed at month-end are paired only with the supplied one-month-ahead excess return. Missing strategy months remain missing.

The primary pooled return is the equal-weight average of valid country sleeves in each month. A market-cap-weighted country aggregation and leave-one-country-out pools are robustness analyses. JKP files supply local-currency excess returns; no foreign-exchange series is introduced, so USD-unhedged performance is outside the primary evidence and is disclosed as unavailable.

## Turnover and transaction costs

Monthly signed target weights are regenerated from the formation panel. Traded notional per dollar of strategy NAV is

\[
\tau_{j,t}=\sum_i\left|w^{\mathrm{target}}_{i,j,t}-w^{\mathrm{pretrade}}_{i,j,t}\right|.
\]

When security-level realized returns permit it, pretrade weights are drift adjusted; otherwise target-to-target traded notional is reported and labeled as an approximation. The primary net return is

\[
r^{n}_{j,t}=r^{g}_{j,t}-0.001\tau_{j,t},
\]

corresponding to 10 basis points one way. Sensitivities use 0, 5, 25, and 50 basis points. The analysis reports monthly and annualized traded notional, the median and 90th percentile, number of names per side, maximum absolute weight, and concentration. Borrow fees and nonlinear price impact are unavailable, so no capacity claim is made and the cost model is explicitly stylized.

## Primary benchmark and estimands

The primary low-dimensional benchmark is a country-local JKP-built market plus value, size, investment, profitability, and momentum analogue (`FF5+Mom`). Candidate returns are not scaled using test-period volatility. For each candidate,

\[
r^n_{j,t}=\alpha_j+\beta_j^\top f_t+u_{j,t}.
\]

The primary endpoint is annualized net alpha, \(12\widehat\alpha_j\). Secondary endpoints are annualized appraisal ratio, native net Sharpe, and a fixed 10% candidate overlay on a benchmark sleeve whose risk scale uses only prior observations. The old single-asset GRS gate, full-sample 132-factor tangency portfolio, same-sample optimized candidate weight, and theoretical span-lift are not confirmatory endpoints.

Dense JKP132/TextBenchmark results are exploratory only. Any robustness using the broad factor library must use training-only PCA or rolling cross-fitted ridge; unregularized 134-regressor estimates on 270 months cannot support a claim.

## Statistical inference and multiplicity

Alpha standard errors use Newey-West HAC with Bartlett weights and

\[
L=\left\lfloor4(T/100)^{2/9}\right\rfloor.
\]

Lags 0, 3, 6, and 12 are sensitivities. Two-sided p-values and 95% intervals are reported, and a positive estimate is required for a positive claim.

A paired stationary/block bootstrap resamples months jointly across candidates, factors, returns, and turnover so cross-candidate dependence is preserved. The fixed seed is `20260802`; the target is 10,000 replications, with a minimum of 2,000 if runtime is prohibitive. Expected block length is six months, with three and twelve months as sensitivity. The bootstrap provides candidate intervals, a familywise max-absolute-t p-value, and simultaneous confidence bounds.

Holm familywise-error adjustment is primary. Benjamini-Hochberg and Benjamini-Yekutieli q-values are reported. All 62 planned hypotheses stay in the correction even if a run fails. A White reality-check-style maximum statistic is reported for the global family; any SPA implementation is labeled as a robustness analysis.

## Economic materiality

Net alpha is the primary economic endpoint. A point estimate is materially positive if at least one prespecified threshold is crossed:

- annualized net alpha at least 2 percentage points;
- annualized active appraisal/information ratio at least 0.25 under an explicitly defined active return;
- net out-of-sample Sharpe improvement at least 0.10.

“Confirmed material” requires a simultaneous lower confidence bound above the relevant threshold. “Economically ruled out” requires a simultaneous upper bound below it. A threshold crossing never substitutes for statistical validity.

## Retrospective USA analysis

USA evidence is labeled exploratory. For stability only, it is split into 1999-07--2012-12, 2013-01--2018-12, and 2019-01--2024-11. The last period is `retrospective temporal validation`, not a locked test. Multiplicity corrections and 10-basis-point cost results are still reported to show how conclusions change under credible analysis.

## Reproducibility gates

The lock is valid only after candidate/formula, census, data-path, and code hashes are recorded and synthetic tests verify ranking, long-short weights, turnover, cost subtraction, HAC inference, multiplicity, and block resampling. Raw and failed outputs are preserved. The run writes its seed, software versions, file hashes, input paths, dates, and output checksums. No paid API call is required; project OpenRouter spend for this analysis is zero.

## Owner review

The execution team prepares a review packet containing every headline claim, all threshold crossings, exclusions, license decisions, sampled failure traces, proxy rationales, uncertainty, and exact reproduction commands. The review remains `pending` until Sasha Cui returns an explicit judgment. Automated analysis cannot substitute for that review.
