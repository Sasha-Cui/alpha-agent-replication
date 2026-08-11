# GuruAgents paper-prompt replay

This experiment evaluates the public GuruAgents prompting pipeline directly; it
does not map the paper to a JKP formula. The source repository ships five agent
prompts, deterministic finance-tool observations, and archived portfolios, so
the replay can be scored against the authors' own outputs.

## Complete grid

- `results`: five agents × seven quarters (2023Q4–2025Q2) = 35 cells.
- `results_22_24`: five agents × twelve quarters (2022Q1–2024Q4) = 60 cells.
- Two modes per cell = 190 experiments.

`archived-final` reconstructs the completed source tool transcript and replays
the final ranking/allocation decision. `tool-routing` starts from the exact
system prompt and source user request, lets the model choose tools, and serves
the matching archived deterministic observations. The second mode tests tool
routing as well as final portfolio construction.

The paper code uses `gpt-4o` at temperature zero. The default replay therefore
uses `openai/gpt-4o` through OpenRouter with `temperature=0`.

## Source and provenance

The current unmodified public source checkout is:

```text
/nfs/roberts/scratch/pi_btk22/zc362/guruagents_prompt_replay_source
```

Each run freezes its Git commit plus SHA-256 hashes of the prompt, archived
analysis JSON, and archived portfolio CSV.

## Concurrent run and cost controls

Create a dedicated OpenRouter key capped at **$475** and expose it only in the
active Bouchet shell as `OPENROUTER_API_KEY`. Do not save it in the repository.
The runner also enforces a shared **$450** ceiling across all workers. Each
request reserves a conservative maximum cost before dispatch and then settles
against OpenRouter's returned usage and dollar cost.

For a detached run, `--api-key-file /absolute/path` accepts a secret file with
mode `600`; place it outside the repository. The key value and file path are not
copied into run outputs.

Dry-run the entire grid first:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/run_guruagents_openrouter_replay.py \
  --dry-run \
  --workers 16 \
  --max-budget-usd 450
```

Then launch all 190 experiments concurrently through the bounded worker pool:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/run_guruagents_openrouter_replay.py \
  --workers 16 \
  --max-budget-usd 450
```

Interrupted runs are resumable; completed experiment directories are reused
unless `--overwrite` is supplied.

## Completed live run

The full concurrent batch `guruagents_full_20260809T010651Z` completed on
2026-08-09 using 32 workers:

- 190/190 experiments completed successfully.
- 3,628,981 prompt tokens and 185,193 completion tokens were billed.
- Cumulative OpenRouter cost was **$9.910302**.
- All 95 tool-routing experiments invoked every required public source tool.
- `archived-final` mean ticker-set Jaccard was 0.5688; exact ticker order was
  reproduced in 10/95 cells.
- `tool-routing` mean ticker-set Jaccard was 0.6074; exact ticker order was
  reproduced in 9/95 cells.

The sanitized aggregate is in `LIVE_RUN_RESULTS.json`; per-cell results are in
`live_run_summary.csv`. Raw request/response transcripts remain in the ignored
run directory on Bouchet.

## Outputs

Generated data live under `runs/prompt_replay/guruagents/<UTC-run-id>/` and are
git-ignored until reviewed:

- `manifest.json`: complete grid, hashes, source commit, pricing assumptions,
  key-limit metadata, conservative cost estimate, and final spend ledger.
- `usage.jsonl`: request-level tokens and OpenRouter cost.
- `summary.csv`: parse status, ticker-set Jaccard, exact-order agreement, weight
  error, score error, calls, tokens, and cost for every experiment.
- `experiments/<id>/`: exact request/transcript, raw responses, final markdown,
  provenance, and comparison with the authors' archived portfolio.

## Interpretation boundary

Agreement in `archived-final` tests whether the prompted LLM reconstructs the
authors' portfolio from identical finance signals. Agreement in `tool-routing`
also tests adherence to the public tool-use procedure. Neither validates the
underlying data engineering or the out-of-sample alpha claim.

## Published Table 1 conformance

The paper-level audit in paper_table_conformance/ compares all ten Table 1
metrics for five agents and two benchmarks with the pinned public source
workbook. It checks both the paper-labeled window through 2025Q2 and the
workbook's full shipped window.

Neither window reproduces a complete strategy row: zero of 14 strategy-window
rows pass, and only four of 140 individual cells match at the paper's displayed
precision. All four matches are the same benchmark maximum-drawdown values
repeated across the two windows. The audit also records that the paper and
notebook declare a one-basis-point transaction cost while the source notebook's
main return routine does not apply its declared cost variable.

Run scripts/audit_guruagents_paper_table.py to regenerate the audit. The 10-bp
corrected-clock analysis below is a separate conservative performance exercise
and must not be cited as reproduction of Table 1.

## Completed performance stage

The second stage is now in `performance/` and is reproducible with:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/evaluate_guruagents_prompt_replay_performance.py
```

It builds 24 replay paths (two archives × two replay modes × five agents plus
an equal-weight ensemble), 12 corrected author paths, and six existing JKP
motif-proxy paths. Formation portfolios execute at the first trading close
strictly after quarter end, use dividend-adjusted closes, drift between
quarterly rebalances, and incur 10 bps per unit of one-way traded notional.

The long archive provides 36 realized return months and 33 months with the
extended JKP factor panel. Its best replay path by net Sharpe is the
`archived-final` Buffett sleeve: 33.30% annualized geometric return, 21.70%
annualized volatility, and 1.26 Sharpe over this short sample. Across all
replay-versus-author common samples, replay paths average +1.87 percentage
points in annualized return and +0.095 in Sharpe, with mean return correlation
0.952. This is not independent evidence because both use the same archived
signals and source universe.

The matched official-factor ladder uses the 12 long-archive replay paths and
the same 33 realization months throughout. Median annualized alpha declines
from 5.80% under official FF5 plus momentum to 2.59% after adding only JKP
`betabab_1260d`; 11 of 12 alphas attenuate and 11 of 12 BAB loadings are
positive. One archived-final Buffett replay remains Holm-positive after BAB,
after the larger predeclared low-risk block, and in the outcome-blind pre-2022
compressed-JKP test. The exploratory full-JKP ridge test leaves no Holm-positive
replay. Unrestricted market-plus-132-JKP OLS is explicitly unavailable: it
requires 134 parameters including the intercept, while replay factor overlap is
only 12 or 33 months. The six long-history motif proxies do identify full-JKP132
OLS, and none has a raw 5% alpha rejection.

The factor extension reproduces the published 2021 panel after its
factor-specific 7%-annual-volatility scaling with maximum absolute overlap
error `9.77e-17`. It extends formation labels through 2024-11 (realization
through 2024-12); the source data do not provide the next-month return needed
to form a 2024-12 factor observation.

Primary performance artifacts include:

- `monthly_return_paths.csv`: gross return, traded notional, 10-bp net return,
  formation/realization clocks, NAVs, and eligibility/failure flags.
- `formation_holdings.csv`, `formation_audit.csv`, and
  `formation_execution_clock.csv`: target matrices and every parsing,
  correction, and execution decision.
- `factor_panel_extended_formation.csv`,
  `factor_panel_extended_realization.csv`, and
  `factor_extension_scaling.csv`: the market-plus-132-JKP panel, both clocks,
  exact factor order, and published scaling multipliers.
- `alpha_regressions.csv`, `factor_fitted_and_residuals.csv`,
  `static_factor_loadings.csv`, and `monthly_ridge_loadings.csv`: alpha tests,
  residuals, coefficients, monthly ridge penalties, and rolling loadings.
- `official_ff_factor_panel_realization.csv`, `replay_attribution_ladder.csv`,
  and `replay_attribution_by_candidate.csv`: official Fama--French factors and
  the matched FF-to-BAB/low-risk attribution results.
- `economic_performance.csv` and `economic_comparison.csv`: author, replay, and
  proxy performance with common-sample limits stated row by row.
- `guruagents_prompt_replay_performance_audit.xlsx`: formatted audit workbook.
- `REPORT.md` and `manifest.json`: interpretation, hashes, clocks, costs,
  factor order, software versions, and licensing cautions.

The JKP proxy comparison is deliberately not mandate matched: those proxies
are top-1000 long-short excess-return strategies with unavailable turnover and
costs, whereas GuruAgents paths are long-only portfolios in the source Nasdaq
file. It is a diagnostic contrast, not evidence that one implementation
dominates the other.
