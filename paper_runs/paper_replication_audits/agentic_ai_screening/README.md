# Agentic AI Screening paper/source audit

This audit now covers both official arXiv versions of `2603.23300`.  It rebuilds
and visually checks all 67 v1 and 82 v2 pages.  The ledgers separately count
**953 v1 numeric cells** and **1,344 v2 numeric cells** across 22 and 26 rendered
tables, respectively.  Across both versions, **0/2,297 cells regenerate through
an author-native experiment**.  The expanded v2 archive is still document-only.

## What changed in v2

V2 is a major empirical rewrite, not a cosmetic revision.  It replaces the main
2020--2024/2015--2024 story with an October 2021--April 2024 medium window using
ChatGPT-3.5 and a November 2023--April 2024 short window using GPT-4o.  It adds
sample-covariance rows after screening, 120 turnover/leverage/concentration/
drawdown cells, five theory/concept figures, robustness tables, and new headline
Sharpe ratios of 1.0946 and 8.1612.  Eight legacy tables remain inside an
inactive `\iffalse ... \fi` block and three table shells are fully commented;
none are counted as rendered results.

## What is genuinely recoverable

- The linked Hugging Face news revision is pinned and inspected: 4,589 rows,
  469 symbols, and dates from 2006-12-04 through 2024-04-20.
- The three December-2023 LLM-S prompt/output listing bodies are byte-for-byte
  unchanged between v1 and v2.  They cover one date, not either full execution.
- OpenAI primary sources corroborate a September 2021 GPT-3.5 Turbo knowledge
  cutoff and GPT-4o pretraining data through October 2023.  The paper still does
  not identify the exact author snapshots or release requests and responses.
- Both documents and all released figures are reproducible from source.  This
  is document reproducibility, not empirical-result reproduction.

## Printed-record findings

V1 retains two non-rounding arithmetic conflicts, including the literal `01092`
return.  V2 has two new conflicts in the short LLM-S NW row: the MV and MSR
Sharpe values cannot reconcile with their printed returns and variances even
after propagating four-decimal rounding.  V2 prose also overlooks a larger
Sample Cov value when naming the medium LLM-S maximum, says 12/15 LLM-S cells
beat baseline when the tables show 11/15, says logistic wins 14/18 against a
15-cell baseline and actually wins 10/15, attributes 3.5374 to the wrong short
table, calls a 114.8% increase 99%, and says two LLM-plus-human cells beat humans
when the tables show one.  Matching claims are recorded too; internal agreement
never receives replication credit.

## Why this is still not a true replication

The public record omits point-in-time S&P membership and identifiers; exact
CRSP/Compustat, IBES/WRDS, and factor snapshots; the FinBERT checkpoint and
scores; full prompts, tool payloads, model calls, responses, and annual rules;
monthly signals and ensemble sets; all estimator and optimizer code; deep-
learning hyperparameters; seeds and environment; fitted matrices, weights,
returns, costs, paired Sharpe-test samples, rerun outputs, and table-generating
arrays.  Family-level knowledge cutoffs do not establish this missing execution
lineage.  Claims about 20 selected stocks, two similar reruns, 1/N returns, and
p-values 0.067/0.062 cannot be independently replayed.

A pinned later repository passes **114 tests**, useful only for its own
components.  It is unaffiliated and materially changes the model, sentiment
agent, estimators, return window, conventions, and data.  It receives no
author-native or paper-result credit.

The honest assessment is strong two-version document reproducibility, one exact
linked input component, one-date prompt/output specification, and **zero
end-to-end empirical replication**.  Full paper faithfulness remains impossible
without author data/runtime/output lineage; the audit records that boundary
instead of filling it with proxies.
