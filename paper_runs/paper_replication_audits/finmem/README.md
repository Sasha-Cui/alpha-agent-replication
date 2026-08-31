# FinMem paper-level conformance audit

Overall verdict: **strong author-output verification, not an end-to-end reproduction**.
The current tree omits the paper outputs, but its full public Git history preserves an
executed metrics notebook and 18 dated action CSVs. The original five-stock inputs,
trained memories, complete five-trial paths, and exact paper configuration remain absent.

## Primary sources

- Official paper record: https://arxiv.org/abs/2311.13743. Both v1 and v2 PDFs
  and matching TeX source archives are hash-pinned and audited; the current v2 PDF
  is https://arxiv.org/pdf/2311.13743 (SHA-256 `acb7527d02871cfad7d2754314b9a803f917b326847a456579df9cf7b0a648b9`).
- Public source: https://github.com/pipiku915/finmem-llm-stocktrading, commit `be814aa47970de9bf2fdd6a1d5a60ae5cf361b46`.
- Historical author-output snapshot: commit `0b7f499e556668bf49885fd8836efe85ef51558f`
  (2023-11-30), deleted from the current tree by commit
  `45169ea8509c29113c7e7945dc52a6b3e43521eb` (2024-02-09).
- Public-fork census: GitHub REST reported 192
  forks on 2026-08-14; GraphQL exposed
  181 repositories and
  187 branch refs. The
  11 unavailable repositories are
  explicitly not claimed as inspected.

## What is genuinely verified or reproduced

- The hash-pinned executed notebook provides machine-readable author outputs for all
  235 displayed metric cells. It matches 223/235 cells exactly and four
  more within one unit of the paper's last printed decimal, corroborating 227/235.
  The eight substantive disagreements are exactly the daily- and annualized-volatility
  entries for all four Table 4 rows.
- The official v1 and v2 PDFs each contain 22 pages. Their matching source archives
  contain 71 files in total. Table 4 was visually inspected on
  v1 page 17 and v2 page 18, and the printed cells were cross-checked against extracted
  PDF text and primary TeX. The same eight disputed numbers survive the revision.
- Exhaustive byte scanning covers all 171 blobs in the complete
  55-commit source history. The four paper annualized cells
  exactly equal the preserved character output's daily-volatility cells. Buy-and-Hold
  and Self-Adaptive daily values occur in a separate `TSLA-full.csv` notebook output
  whose returns and Sharpe ratios establish that it is a different experiment. The
  Risk-Seeking and Risk-Averse daily values occur in no reachable public source blob.
  This bounded evidence supports a cross-experiment/mislabeled-table construction
  defect; it does not prove what may have existed in unavailable private artifacts.
- The exact pinned `calculate_metrics` function executes all 15 historical action
  configurations with yfinance 0.2.32 imported and live downloads blocked. All 75
  values match the independent adapter within 1e-12 and 67/75 match
  the paper at display precision. Tables 3 and 5 match completely (55/55); Table 4
  matches cumulative return, Sharpe, and drawdown (12/20) but conflicts on the same
  eight volatility cells.
- This is stronger than paper-value transcription: it connects the paper values to
  author-shipped outputs and independently replays the ablation metric path. It is
  still not an end-to-end rerun of FinMem's LLM decisions or five repeated trials.
- The complete accessible-fork snapshot collapses to 20
  unique heads: 9 are reachable
  from official history and all 11 divergent
  heads were reviewed across 45 extra
  commits and 299 changed paths. None
  matches an official-source author identity or contributes a paper-result artifact.
  One post-paper fork contains a 19-row, 2016 TSLA action CSV whose directions are all
  hold, while its active config is phi3v/top-K=3 and its checkpoint identifies
  GPT-3.5. A second contains GPT-3.5/top-K=3 TSLA checkpoint state but no action or
  metric result file. These are unaffiliated mini-runs, not the paper's GPT-4-Turbo,
  top-K=5, five-ticker, five-trial lineage, and receive zero paper credit. The second
  branch deletes the 33-file historical author-output tree from the official root;
  those deleted files are already counted once as official history, not fork evidence.

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

## Why this is not a complete FinMem rerun

- The current result/checkpoint directories contain only placeholders. Public history
  supplies action paths and outputs, but does not identify five complete trial paths,
  their seeds, or the averaging lineage claimed by the paper.
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
- The reusable metric function now executes, but the outer script entrypoint remains
  non-operational: it references an undefined lowercase ticker, hard-codes author-local
  result paths, and uses yfinance/pandas without declaring them in either locked
  environment file.
- The paper averages five repeated trials but provides no seeds or trial paths. It
  also reports whichever of three risk profiles has the highest cumulative return
  on the test period, an outcome-selected figure rather than a prespecified profile.

## Metric and paper consistency boundary

- The paper's "Cumulative Return" is the sum of daily log returns multiplied by
  each day's direction (-1/0/+1). It has no transaction costs, cash balance, or
  self-financing NAV, so it should be interpreted as a signed-return score rather
  than conventional cumulative portfolio return.
- Table 4's four annualized-volatility cells fail the paper's own identity,
  annualized volatility = daily volatility times sqrt(252). More decisively, all eight
  Table 4 volatility entries disagree with both the preserved character output and the
  independent action replay. Version and blob forensics explain six literal lineages
  and bound the other two to the papers. All 43 corresponding
  rows in Tables 2, 3, and 5 are rounding-consistent.

Run `scripts/audit_finmem_paper.py` to regenerate this package. Use `--strict` when
a CI failure is desired until native paper action paths and original inputs exist.
