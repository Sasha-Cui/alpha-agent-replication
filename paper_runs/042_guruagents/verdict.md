# GuruAgents FF3 / FF5Mom benchmark verdict

Status: completed provisional benchmark pass.

Candidate construction:

- Source workbook: external_repos/GuruAgents/results_22_24/multi_agent_backtest_results.xlsx.
- Paper-level candidate: equal-weight average of the five shipped daily agent return streams, compounded to monthly returns.
- Additional diagnostics: each individual guru-agent sleeve was also benchmarked.
- Factor source: official Kenneth French monthly FF3, FF5, and momentum factors via pandas_datareader, not the external factor-data project same-universe factor panel. This was necessary because the shipped GuruAgents returns run from 2022-04 through 2025-03, while the external factor panel ends in 2021-12.

Paper-level equal-weight result:

- Months: 36, 2022-04-30 to 2025-03-31.
- Excess Sharpe after 7 pct vol scaling: 0.612.
- FF5+Mom annualized alpha: 2.040%.
- FF5+Mom HAC alpha t-stat: 1.598.
- FF5+Mom appraisal ratio: 0.839.

Best individual sleeve:

- Candidate: 042_guruagents_warren_buffett.
- FF5+Mom annualized alpha: 4.919%.
- FF5+Mom HAC alpha t-stat: 2.889.
- FF5+Mom appraisal ratio: 1.330.

Verdict:

GuruAgents contains something potentially relevant, but only provisionally. The paper-level equal-weight candidate is positive after FF5+Mom controls but does not clear a t-stat above 2. The Warren Buffett sleeve does clear that threshold on the shipped 36-month sample. This is not enough to call the paper serious under the original strict standard because the sample is short, the candidate returns are post-2021, and the run uses official FF factors rather than the external same-universe benchmark span. It is worth a second pass using reconstructed holdings on a longer point-in-time universe.
