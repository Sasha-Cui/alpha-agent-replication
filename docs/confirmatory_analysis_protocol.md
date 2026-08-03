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

Native execution fidelity is recorded separately from the static artifact
packaging scale introduced in Amendment 1. Static packaging uses `R0` no
reachable public artifact, `R1` descriptive or incomplete materials, `R2`
source code plus an environment/setup manifest, and `R3` those materials plus
a visible runner and tests/examples/configuration. None of these static tiers
asserts successful execution or dated returns.

## Frozen proxy family

The secondary performance family contains all 62 already-defined proxy portfolios, including poor and failed rows. Candidate IDs, formula ingredients, signs, formation lag, portfolio rule, and source labels are frozen from `scripts/run_paper_idea_jkp_proxies.py`. No candidate may be reoriented, renamed to imply native fidelity, removed after failure, or selected because of an international result. One textually closest proxy per source is flagged for presentation, but all 62 remain in the multiplicity denominator.

The ContestTrade trailing-selection proxy has a 24-month warm-up. Its first
valid month defines the common family start, so all 62 primary estimates and
simultaneous tests use the same calendar.

## Geographic validation universe

The validation markets are the six G7 members outside the United States: `CAN`, `FRA`, `DEU`, `ITA`, `JPN`, and `GBR`. This institutional rule was chosen before outcomes were viewed. The primary analysis window is 1999-07 through 2024-11, subject to a candidate's formation warm-up.

Portfolios are formed independently within each country from the point-in-time JKP characteristic files. The security identifier is the country-file `id`. At each month, securities with a valid formation date, positive market equity, and the required score inputs are eligible; next-month return availability is not a formation condition. The largest 1,000 securities by market equity are retained; smaller markets use all eligible securities. No strategy-specific price or common-share filter is added because the frozen USA constructor did not apply one.

Long-short candidates buy the top score decile and short the bottom score decile, value weighted within each side, with one dollar long and one dollar short. Long-only candidates follow their frozen top-decile or top-five rule. Each decile side requires at least 20 securities; the top-five rule requires an eligible universe of at least 20 but holds exactly five. Quantile membership uses exact side counts with a deterministic identifier tie-break, so long and short legs cannot overlap. Signals observed at month-end are paired only with the supplied one-month-ahead excess return. A held security with a missing next-month return is assigned zero at its frozen weight in the primary analysis and its gross missing-return exposure is recorded. A position-adverse sensitivity assigns -100% to a missing long return and +100% to a missing short return, producing a contribution of minus the missing absolute weight without future-conditioned reweighting.

The primary pooled return is the equal-weight average of all six country sleeves in each retained month. A month is retained only if every candidate and factor is available in every country. Leave-one-country-out pools are robustness analyses. JKP files supply USD-converted total and excess returns. The primary endpoint uses the supplied USD excess return; no separate local-currency or FX-hedged series is constructed.

## Turnover and transaction costs

Monthly signed target weights are regenerated from the formation panel. Traded notional per dollar of strategy NAV is

\[
\tau_{j,t}=\sum_i\left|w^{\mathrm{target}}_{i,j,t}-w^{\mathrm{pretrade}}_{i,j,t}\right|.
\]

Pretrade weights are drift adjusted with the reconstructed next-month USD total return and a common post-return strategy-NAV denominator. The primary net return is

\[
r^{n}_{j,t}=r^{g}_{j,t}-0.001\tau_{j,t},
\]

corresponding to 10 basis points one way. Sensitivities use 0, 5, 25, and 50 basis points. The analysis reports monthly and annualized traded notional, the median and 90th percentile, number of names per side, maximum absolute weight, and concentration. Borrow fees and nonlinear price impact are unavailable, so no capacity claim is made and the cost model is explicitly stylized.

## Primary benchmark and estimands

The primary low-dimensional benchmark is a country-local JKP-built market plus value, size, investment, profitability, and momentum analogue (`FF5+Mom`). Candidate returns are not scaled using test-period volatility. For each candidate,

\[
r^n_{j,t}=\alpha_j+\beta_j^\top f_t+u_{j,t}.
\]

The primary endpoint is annualized net alpha, \(12\widehat\alpha_j\). Annualized appraisal-ratio and native net-Sharpe levels are descriptive secondary endpoints. The planned fixed 10% candidate overlay is not executed because the initial protocol did not fully specify a public benchmark sleeve and prior-only risk-scaling implementation; no overlay-improvement claim is made. The old single-asset GRS gate, full-sample 132-factor tangency portfolio, same-sample optimized candidate weight, and theoretical span-lift are not confirmatory endpoints.

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

Only the 2-percentage-point alpha threshold is operational for the proxy
family. The appraisal-ratio and Sharpe thresholds require a separately defined
paired active baseline or overlay that the frozen evaluator does not provide;
their levels are reported descriptively and are not counted as materiality
discoveries.

## Retrospective USA analysis

USA evidence is labeled exploratory. For stability only, it is split into 1999-07--2012-12, 2013-01--2018-12, and 2019-01--2024-11. The last period is `retrospective temporal validation`, not a locked test. Multiplicity corrections and 10-basis-point cost results are still reported to show how conclusions change under credible analysis.

## Reproducibility gates

The lock is valid only after candidate/formula, census, data-path, and code hashes are recorded and synthetic tests verify ranking, long-short weights, turnover, cost subtraction, HAC inference, multiplicity, and block resampling. Raw and failed outputs are preserved. The run writes its seed, software versions, file hashes, input paths, dates, and output checksums. No paid API call is required; project OpenRouter spend for this analysis is zero.

## Owner review

The execution team prepares a review packet containing every headline claim, all threshold crossings, exclusions, license decisions, sampled failure traces, proxy rationales, uncertainty, and exact reproduction commands. The review remains `pending` until Sasha Cui returns an explicit judgment. Automated analysis cannot substitute for that review.

## Amendment 1: evaluator defects found by independent code audit

**Amendment timestamp:** 2026-08-03 UTC, after the first G7 run but before its
results were accepted for the manuscript.

An independent line-level audit identified four evaluator defects in the
initial locked implementation. First, formation eligibility and the top-1,000
filter required a nonmissing one-month-ahead return, thereby conditioning the
formation universe on future outcome availability. Second, post-return
long-short weights were normalized within the long and short legs separately,
which omitted trades needed to restore gross exposures per dollar of strategy
NAV. Third, candidate returns, turnover, and factors could be averaged over
different country sets because missing values were skipped independently.
Fourth, ordinary HAC estimates used candidate-specific calendars while the
paired family bootstrap used the all-candidate complete calendar; the
ContestTrade warm-up therefore made point and simultaneous estimates target
different samples.

The first G7 output directory and lock are retained under
`paper_runs/submission_evidence/superseded_v1/` and are prohibited from use in
the paper. The partially started USA run was terminated. The amendment changes
no candidate formula, sign, country, date range, cost grid, benchmark family,
economic threshold, multiplicity method, bootstrap seed, or block length.

The following rules supersede the inconsistent clauses above:

1. Formation eligibility and the top-1,000 market-equity rank use only the
   identifier, formation month, positive formation-date market equity, and
   required score inputs. Next-month return availability is never a formation
   filter for candidates, market controls, or characteristic factors.
2. A held security with a missing next-month return is assigned a zero excess
   return at its frozen ex-ante weight. The portfolio is not reweighted with
   hindsight. Candidate and factor outputs record the absolute gross weight
   exposed to this policy. Because an integration audit found that this
   exposure can be material for concentrated rules, a prespecified
   position-adverse sensitivity assigns -100% to missing long returns and
   +100% to missing short returns. Missing total returns used only for drift
   remain zero in both runs because a single security-level adverse value
   cannot be adverse to both long and short portfolios; total-return missing
   exposure is reported separately.
3. If prior target weights are \(w_{i,t-1}\), realized USD total security
   returns are \(R_{i,t}\), and the portfolio total return is
   \(R^p_t=\sum_iw_{i,t-1}R_{i,t}\), the pretrade risky-asset weight is

   \[
   \widetilde w_{i,t}=\frac{w_{i,t-1}(1+R_{i,t})}{1+R^p_t}.
   \]

   The evaluator reconstructs the one-month-ahead total return from the next
   consecutive security-month row, while performance inference continues to
   use the supplied one-month-ahead excess return. All risky holdings share
   the same post-return NAV denominator. Turnover is
   the L1 difference between these pretrade weights and the new targets, so
   exposure-restoration trades are included.
4. Every cost-level alpha, nominal test, multiplicity adjustment, and paired
   bootstrap estimate uses the identical complete candidate-factor calendar.
   The 24-month ContestTrade warm-up therefore defines the common start date
   for all 62 family members. A pooled month is retained only when every
   candidate and every factor is available in all six countries, so candidate
   returns, turnover, and factor controls always average the identical country
   set. Code asserts both country counts and equality of the ordinary and
   bootstrap alpha point estimates before writing results. Country and
   leave-one-country-out diagnostics apply the same common-calendar rule
   within their respective panels.
5. The artifact audit's `R0`--`R3` fields are a separate static packaging
   scale: no reachable public artifact, descriptive/incomplete artifact,
   code plus environment, and code plus environment plus runner/support. They
   do not assert native execution. Native fidelity and dated-return
   availability remain separate fields.

This amendment is a correctness repair after outcome access and is therefore
reported prominently as a protocol deviation. Corrected scripts, tests, and
the amended protocol receive a new lock hash before the G7 files are rerun.
The amended implementation also executes the prespecified fixed HAC-lag
sensitivities (0, 3, 6, and 12) and three- and twelve-month block-length
sensitivities. It does not implement the under-specified 10% overlay, and it
restricts economic confirmation to the alpha threshold as stated above.

## Amendment 2: limited-liability handling after an amended-run runtime failure

**Amendment timestamp:** 2026-08-03 UTC, after the amended evaluator began its
Canada build but before it produced any corrected alpha table, candidate
ranking, or accepted corrected outcome.

The first attempt under Amendment 1 stopped during the Canada portfolio build
when a 100/100 long-short sleeve reached nonpositive NAV after an extreme gain
in a short position. A direct scale audit confirmed that the underlying JKP
security returns are decimal returns rather than percentage-point values: no
Canada total security return was below -100%, while the upper tail contained
valid observations large enough to bankrupt a leveraged short sleeve. The
failure therefore exposed an omitted economic state, not a corrupt return
scale. The halted output directory, log, and preceding lock are preserved as a
superseded runtime-infeasible attempt and cannot enter the paper's estimates.

The following limited-liability rule is frozen before another corrected run:

1. A candidate or the trailing-selection Contest sleeve is a complete-path
   implementation failure if its realized monthly total portfolio return is
   at most -100% in any market included in the analysis. Missing total returns
   continue to receive zero solely for drift, as specified in Amendment 1.
2. A failed path is never clipped, restarted, or recapitalized. Its observed
   failure month, total portfolio return, excess return, traded notional, market,
   and selected sleeve (when applicable) are written to a failure ledger.
3. If a candidate fails in any market in a pooled analysis, its entire pooled
   return path is unavailable. The candidate remains in the original family of
   62 hypotheses and enters Holm, BH, BY, and other family accounting with
   (p=1); it cannot be presented as a zero-return result.
4. The complete common calendar is defined over candidates whose full paths
   remain executable, plus every factor and every included country. Failed
   candidates do not erase otherwise valid months for executable candidates.
   Country and leave-one-country-out diagnostics reassess path failure within
   the markets included in that diagnostic.
5. A one-market USA retrospective writes leave-one-country-out rows as not
   applicable rather than attempting an empty-country regression.

This second amendment changes no signal formula, sign, universe, country, date
range, cost, factor control, materiality threshold, seed, or multiplicity
method. It is nevertheless a post-runtime protocol deviation and is disclosed
as such. The scripts, tests, and this text receive a third lock before the
evaluable corrected run begins.
