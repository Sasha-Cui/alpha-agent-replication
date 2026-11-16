# Quanta paper-parameter sensitivity — completed exploratory results

All four comparisons remain **inconclusive at the ±2 percentage-point annual margin**. Point estimates are positive, while every pointwise 99% interval covers zero and both margin endpoints. This does not establish equivalence, significant alpha, an isolated parameter effect or a faithful full-paper reproduction.

For the opening-information Alpha158 comparison, the full-sample mean increment is **+3.7759 pp/year**; the four-block estimate is **+3.7861 pp/year**, with grouped pointwise 99% interval **[-15.7627, +23.3350] pp/year** and raw two-sided p = **0.340210**. Ending wealth is **1.28390444** versus the reused baseline's **1.11534581**. The opening Source4 comparison is also inconclusive. All four comparisons are retained below.

## Comparison and inference

| Comparison | Full mean Δ pp/y | Group mean Δ pp/y | Pointwise 99% CI, pp/y | Raw p |
| --- | --- | --- | --- | --- |
| Opening proxy / Alpha158 | +3.7759 | +3.7861 | [-15.7627, +23.3350] | 0.340210 |
| Opening proxy / Source4 | +4.0826 | +4.0904 | [-25.9381, +34.1190] | 0.484381 |
| Native diagnostic / Alpha158 | +3.8652 | +3.8706 | [-8.2343, +15.9754] | 0.158622 |
| Native diagnostic / Source4 | +4.2444 | +4.2526 | [-26.4833, +34.9885] | 0.478149 |

[Full comparison audit CSV](visual_tables/comparisons_full_audit.csv). The figure uses equal-weight block means; the full-sample mean weights all963sessions equally. Blocks contain241/241/241/240sessions, explaining their small differences. Annualization is252×the corresponding daily mean difference. Intervals and p-values use four contiguous groups and3degrees of freedom, under the stated approximate block-independence/normality assumptions. These are pointwise intervals, not simultaneous margin bounds. The saved factor_count=0 denotes no factor adjustment; there is no JKP132 attribution or per-block model refit in this comparison. Raw p-values are descriptive exploratory values, with no project-family significance claim.

## Opening-information wealth paths

| Opening proxy | Baseline wealth | Augmented wealth | Baseline drawdown | Augmented drawdown |
| --- | --- | --- | --- | --- |
| Source4 | 1.01359912 | 1.16705330 | -24.916% | -24.409% |
| Alpha158 | 1.11534581 | 1.28390444 | -23.223% | -23.374% |

[Full performance audit CSV](visual_tables/performance_full_audit.csv). Both panels use the same963sessions,2022-01-07 through2025-12-26. Wealth compounds saved daily returns net of costs. The cagr field in the canonical audit means252-session geometric annualization, not calendar-year CAGR. Drawdown is the maximum compounded-wealth drawdown; it is not a drawdown of an additive excess-return curve.

## Fixed comparison contract

The default report view is the opening-information comparison; native execution is a conformance diagnostic. The intervention adds the entire142-expression library to Source4 or Alpha158. It is not an isolated comparison of one search parameter, and no configuration is selected for trading from these results.

| Contract | Completed setting |
| --- | --- |
| Baseline / augmented features | Source4:4→146; Alpha158:158→300 |
| New fits / opening replays |2augmented fits;2replays of their saved predictions |
| Common baseline reuse |4existing native/opening paths;0baseline refits |
| Economic settings |Identical within each comparison; buy5bp/sell15bp,min5, native lot rules and common calendars |
| Generation / evaluation boundary |Six generation fields bounded through2022-01-05; first signalJan6/fillJan7,2022 |
| Search settings |Symbol-length threshold250,base-feature threshold6,duplication5,consistencyON,3requested factors,10directions/10crossovers/five total phases |
| Meaning of symbol length |Expression complexity threshold; not the stock-universe size |
| Source model |Current GPT-5.2/OpenAI,max3000,reasoningnone,recorded ordinal seeds and supported request parameters |
| Source parameters versus released default |Multiple settings/routes/histories differ; no isolated parameter-effect or historical-model equivalence claim |

The opening proxy uses finite positive current open/prior close and the same9.5% threshold, with saved predictions/labels, fees,lots and dates held fixed. Native Qlib eligibility uses same-day closing-change/missingness information. Board/auction/liquidity/adjustment-vintage fidelity remains incomplete. Generation did not receive evaluation HDFs; later deterministic program proofs and fixed-library evaluation use the declared full panel. AppendixA.4 defines five total phases; AppendixBconflicts. Historical seeds,zoo,segment-splicing and pristine model/data snapshots remain gaps.

## Raw values and native preprocessing

| Completed raw library diagnostic | Value |
| --- | --- |
| Rows × expression columns | 801,001 × 142 |
| Raw infinite cells | 32,359 |
| Columns containing raw infinity | 7 |
| Raw missing cells | 1,977,960 |
| Full-universe proof programs flagged for infinity | 12 (different universe/check scope) |

[Raw-library diagnostic JSON](visual_tables/raw_library_diagnostics.json). The12full-universe proof flags and7membership-filtered library columns have different scopes; their cell counts must not be added. All142programs remain in the library. Raw infinities and missingness are retained in source/library evidence, even though the actual processed model inputs are finite.

| Arm / segment | Rows | Features | Processed missing | Processed infinity | Constant/missing columns |
| --- | --- | --- | --- | --- | --- |
| Source4 / train | 282,088 | 146 | 0 | 0 | 0 |
| Source4 / valid | 72,754 | 146 | 0 | 0 | 0 |
| Source4 / test | 289,011 | 146 | 0 | 0 | 0 |
| Alpha158 / train | 282,088 | 300 | 0 | 0 | 0 |
| Alpha158 / valid | 72,754 | 300 | 0 | 0 | 0 |
| Alpha158 / test | 289,011 | 300 | 0 | 0 | 0 |

[Full processed-feature audit CSV](visual_tables/processed_features_full_audit.csv). These are saved independent-validator diagnostics from the two actual native fits; the opening replays reuse their predictions and processed-feature evidence. No factor, model or account was regenerated for this report.

## Completed evidence and limits

The source/full replay preserve3644chat,589embedding and680quality-event records,50LOOP IDs separately from50POOL IDs, both original and partial history gates and reconstructed RNG receipts. Reconstructed RNG is not a comparison with unavailable original RAM. All51saved source-period backtest workspaces are accounted for:50pool/export experiments plus1explicit baseline. All50source accounts pass243sessions. The142full-universe program proofs pass four actual historical cutoffs and exact native matrix comparisons;12raw-infinity flags remain preserved. These counts are workflow records, not independent trials or scientific successes.

The fixed library contains801,001rows and142distinct expressions. The four later-period native/opening accounts pass independent validation for963sessions each, with their recipes, predictions, features, matrices and calendars hash-bound. The original timeout, V2continuation guard failure, terminal-telemetry admission issue and failed old matrix-containment proof attempts remain preserved. Only failed/unstarted work was continued; completed source/model/proof jobs and baseline fits were not repeated.

The experiment is a separately declared exploratory paper-parameter sensitivity. It does not replace released-default Quanta, the strict Alpha primary, the original four-primary family, the54-secondary family or any of the frozen v1six comparisons. All69paper dispositions remain separate. One market history, current models and incomplete historical inputs prevent a pristine or untouched-holdout claim. Existing bootstrap calibration limits remain relevant; no confidence guarantee is imported from a different sample length.

This case's numerical execution is complete. AMZN's separately unapproved retry and complete13-equity accounting remain unresolved elsewhere in the project. The full manuscript, immutable public/private bundles and durable independent archives remain separate work. Assistant numerical/visual QA is not independent human source review. Project preservation copies are not final/off-allocation archives.

## Audit artifacts and reproduction

[Canonical comparisons](../quanta_paper_parameter_sensitivity/comparisons.json), [canonical performance](../quanta_paper_parameter_sensitivity/performance.json), [analysis completion](../quanta_paper_parameter_sensitivity/completion.json), [source/proof admission](../quanta_all142_proofs_completion.json), [source accounts](../quanta_source_closure_completion.json), [full artifact index with absolute paths and hashes](visual_tables/artifact_index.csv), [report contract](report_contract.json).

Rebuild presentation artifacts only, from already completed results:

```bash
cd /nfs/roberts/project/pi_btk22/zc362/alpha_evolve
/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python scripts/build_quanta_parameter_report_v1.py
/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python scripts/validate_quanta_parameter_report_v1.py
```

A completed report is preserved; later presentation changes require a new report version. These commands do not rerun the study, its sources, models, accounts or completed factor proofs.
