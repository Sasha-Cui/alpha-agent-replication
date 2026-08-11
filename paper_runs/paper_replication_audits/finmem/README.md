# FinMem paper-level conformance audit

Overall verdict: **not reproduced**. The public release contains the agent framework
and fake pipeline examples, but not the original five-stock inputs, trained memories,
five-trial action paths, comparator outputs, or paper-period results.

## Primary sources

- Official paper: https://arxiv.org/pdf/2311.13743 (SHA-256 `acb7527d02871cfad7d2754314b9a803f917b326847a456579df9cf7b0a648b9`).
- Public source: https://github.com/pipiku915/finmem-llm-stocktrading, commit `be814aa47970de9bf2fdd6a1d5a60ae5cf361b46`.

## What is genuinely reproduced

- The released metric formulas and a hash-pinned Yahoo adjusted-close retrieval
  reproduce the full five-metric TSLA Buy-and-Hold row exactly at four decimals for
  the ablation period (2022-06-16 to 2022-12-28) in both Tables 3 and 5.
- Across all repeated Buy-and-Hold cells in Tables 2--5, 16/40 match and
  24/40 differ. The five main Table 2 rows use the paper's stated dates,
  but none fully matches the 2026 Yahoo retrieval; these are input-snapshot
  mismatches, not proof that the authors' unavailable historical snapshot was wrong.
- The exact ablation match establishes fidelity of the adapter to the released
  signed-log-return, volatility, Sharpe, and drawdown implementation. It does not
  establish an LLM-agent result.

## Why the FinMem result is not reproduced

- All 195 non-Buy-and-Hold cells are unverifiable. The result/checkpoint
  directories contain only placeholders, and no five-trial action series is shipped.
- The paper's main configuration is GPT-4-Turbo, temperature 0.7, top-K=5, and five
  tickers. The only released GPT config is TSLA with GPT-3.5-Turbo-0125, omitted GPT
  temperature, and top-K=3. No configs exist for NFLX, AMZN, MSFT, or COIN.
- The paper trains from 2021-08-17 to 2022-10-05 and tests from 2022-10-06 to
  2023-04-10. The active shell example tests 2022-07-20 to 2022-08-01, and its
  required TSLA input/checkpoint files are absent.
- The paper's Alpaca/Benzinga news, SEC filings, and exact Yahoo snapshot are not
  released. `Fake-Sample-Data.zip` explicitly contains Kaggle-derived fake news and
  sample pipeline objects, not paper inputs or agent outputs; pickle payloads were
  inventoried without execution.
- The metrics script is not directly operational: it references an undefined
  lowercase ticker, hard-codes author-local result paths, and uses yfinance/pandas
  without declaring them in either locked environment file.
- The paper averages five repeated trials but provides no seeds or trial paths. It
  also reports whichever of three risk profiles has the highest cumulative return
  on the test period, an outcome-selected figure rather than a prespecified profile.

## Metric and paper consistency boundary

- The paper's "Cumulative Return" is the sum of daily log returns multiplied by
  each day's direction (-1/0/+1). It has no transaction costs, cash balance, or
  self-financing NAV, so it should be interpreted as a signed-return score rather
  than conventional cumulative portfolio return.
- Table 4's four annualized-volatility cells fail the paper's own identity,
  annualized volatility = daily volatility times sqrt(252). All 43
  corresponding rows in Tables 2, 3, and 5 are rounding-consistent.

Run `scripts/audit_finmem_paper.py` to regenerate this package. Use `--strict` when
a CI failure is desired until native paper action paths and original inputs exist.
