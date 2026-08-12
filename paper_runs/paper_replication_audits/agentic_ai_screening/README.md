# Agentic AI Screening paper/source audit

This audit pins arXiv `2603.23300v1`, rebuilds its 67-page source, visually
checks every official and rebuilt page, inventories all 22 result tables and
all **953 printed numeric result cells**, and assigns **0/953 native result credit**.
The source archive contains five document assets, not the authors'
experiment.  No attributable native implementation was recovered.

## What is genuinely recoverable

- The linked Hugging Face news revision is pinned and inspected: 4,589 rows,
  469 symbols, and publication dates from 2006-12-04 through 2024-04-20.
- The paper prints the LLM-S CrewAI agent/task prompt and deterministic rule
  output for December 2023.  This is one date, not the annual prompt, injected
  cross-section, tool-call, and output history required by the tests.
- The characteristic preprocessing, seven-day news weighting, ensemble rule,
  180-month window, three objectives, five estimator families, and 10 bp cost
  equation are described to varying degrees.  They are method specification,
  not executable result lineage.

## Why the paper is not truly replicated

The public package omits the point-in-time S&P 500 membership and identifiers;
CRSP/Compustat and IBES/WRDS snapshots; exact Fama--French input; full annual
prompts, data payloads, tool implementations, Gemini requests and rule outputs;
the FinBERT checkpoint and probabilities; all monthly signals and ensemble
sets; estimator/deep-learning implementations and hyperparameters; seeds and
environment; fitted matrices, portfolio weights, returns, costs, tables, and
decomposition arrays.  Consequently none of the 953 printed cells can be
regenerated through an author-native path.

Gemini 2.0 Flash first became public on 2024-12-11, seven months after the
reported test data end, so a retrospective data split is possible.  Its
documented knowledge cutoff is August 2024, after that test end.  The paper's
instruction to “use causal masking” is prompt text, not evidence of a model
attention control, a timestamped request, or a model-knowledge holdout.  Strict
prospective/model-chronology faithfulness therefore remains unverified.

## Checks on the printed record

- 313/315 Sharpe/return/variance triples reconcile within 0.002.  The 10-year
  LLM-S NLS/MSR row implies 0.4607 rather than printed 0.4691.
- The 10-year Agentic POET/MV return is printed as `01092`; interpreting it as
  `0.1092` reconciles with the printed 0.2358 Sharpe and is almost certainly a
  missing decimal, but the ledger preserves the source literally.
- Major cross-table comparison counts in the prose agree with the printed
  tables.  This internal agreement does not verify the experiment.
- Claims that signals do not align with subsequent returns, that the
  intersection contributes 1.037 of 1.187 Sharpe, that fallback-union dates
  are 50%, and that 22 stocks are selected on average lack released statistics
  or dated signal/output arrays.
- Stage 2 pools buy and sell names and may reverse their signs, so the screening
  labels do not constrain final position direction.  The theoretical guarantee
  is conditional on “sensible screening”; the public artifacts do not show the
  empirical agents satisfy that assumption.

A pinned later repository passes **114 tests**, which is useful evidence about
its own components.  It is an unaffiliated interpretation created over four
months after the paper and materially changes the model, sentiment agent,
estimator, return window, risk-free convention, and data sources.  It receives
no author-native or paper-result credit.

The honest present assessment is: strong document reproducibility, one exact linked
input component, one-date prompt/output specification, and zero end-to-end empirical replication.
Reaching 100% paper faithfulness from the
current public record is impossible without author data/runtime/output lineage;
that boundary is recorded rather than filled with proxies.
