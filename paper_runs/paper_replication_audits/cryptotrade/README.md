# CryptoTrade paper-level conformance audit

Overall verdict: **partial reproduction, not a full paper replication**. The pinned
public data and native trading environment strongly reproduce deterministic
traditional baselines. A public branch controlled by paper coauthor Nuo Chen also
preserves exact author action traces for part of the LLM table, but neither those
traces nor the official artifacts fully reproduce CryptoTrade's LLM/time-series study.

## Primary sources

- Official paper: https://aclanthology.org/2024.emnlp-main.63.pdf (SHA-256 `376606b05f5398c9200b0a560690693ea0a023a97631175ae02528e4dffec5cf`).
- Public source: https://github.com/Xtra-Computing/CryptoTrade, commit `210da73af5f17992be425e61305524a5c24dae40`.
- Paper-author history: Nuo Chen's public `nchen` branch, commit
  `2a6cefe6ea7dc291070b63e5699f95370a7d32d7` (89 commits inspected).
- A bounded GitHub census on 2026-08-14 covers all
  37 accessible forks and 39 fork branch refs.
  The first-author `NuoJohnChen` fork duplicates the already-audited `master` and
  `nchen` heads; it contributes no additional commit or result lineage.

## What reproduces

- A safe adapter over the released environment, 0.4% exchange cost, fixed gas cost,
  and traditional-signal logic matches 174/180 displayed cells
  across Buy-and-Hold, SMA, SLMA, MACD, and Bollinger Bands.
- 43/45 traditional strategy/asset/regime rows match all four
  displayed metrics (total return, daily mean, daily standard deviation, and
  Sharpe ratio). This includes every Buy-and-Hold, SLMA, MACD, and Bollinger row.
- The coauthor history corroborates 40/108 LLM table cells across
  10/27 LLM rows. For each credited row, all four displayed values match and every
  recorded action replays through the pinned official data/environment with zero
  state error. This verifies historical author outputs; it does **not** regenerate
  the LLM decisions or prove current endpoint determinism.
- Table 5 adds 12 result cells that were previously omitted from the audit
  denominator. All 12 have exact numeric correspondences in the paper-author
  history, and the six selected action traces replay with zero state error against
  their own pinned historical code/data snapshots. They receive **0/12 faithful
  result credit**: all six declare `gpt-3.5-turbo`, not the paper's stated GPT-4o,
  and the trace matching the Full row is BTC-bull rather than the ETH experiment
  described around Table 5. The closer ETH/full-prompt trace reports 28.11%/0.08,
  not 28.47%/0.23.
- ETH-sideways SMA matches the paper's -5.45% total return and -0.07 Sharpe, but
  the released path produces -0.07+/-1.00 daily return rather than -0.15+/-1.64.
  The paper's daily cell exactly duplicates its ETH-bear SMA daily cell.
- SOL-bear SMA is the larger mismatch: the paper reports +1.04% return,
  0.02+/-0.10 daily return, and 0.16 Sharpe. Those four cells exactly reproduce
  with a 1-day moving average, but the paper and source both define the candidate
  grid as [5, 10, 15, 20, 30]; every disclosed candidate loses 17.77%--22.19%.
  The numeric lineage is therefore diagnosed without claiming faithful replication.

## Why this is not a full reproduction

- 260/480 paper result cells remain unverifiable. The
  official release ships no complete LLM result paths; the recovered author history
  contains no matching GPT-3.5 paper row and no complete matching SOL-bear GPT-4o row.
- Six additional LLM rows numerically match the paper but receive no credit: five
  traces declare `gpt-3.5-turbo` although their filenames/table assignments imply
  GPT-4/GPT-4o, and ETH-sideways GPT-4 stops on August 6 instead of completing the
  paper period through August 30. See `author_history_llm_trace_audit.csv`.
- The original paper URL points to an anonymous 4open artifact that now returns
  HTTP 410 (`repository_expired`). All 11 commits in the successor
  official GitHub history were inspected; none preserves a result or log path.
  The recovered pre-reroot author snapshot and official root share all 406 earlier
  paths, with 400 byte-identical blobs; the remaining active execution logic is
  materially continuous, and action replay supplies the stronger numeric check.
- Of 39 fork refs, 35
  are already reachable from the pinned official/coauthor histories. The four
  divergent heads are all unaffiliated and post-paper: a Gemini 2.5 experiment
  with empty/non-paper result files, a NIFTY-50/Gemini rewrite, a local-model and
  Taiwan-market six-agent extension, and a descriptor/PDF-only fork. Their
  7 result/log-like paths
  receive zero paper credit. See `public_fork_divergence_inventory.csv`.
- Informer, AutoFormer, TimesNet, and PatchTST implementations are absent. The
  included LSTM is embedded in an ETH-only monolithic runner, has no seed, trains
  on the full requested interval, and ships no result path.
- The complete coauthor history contains 83 unique `.out` blobs totaling
  209,739,069 bytes. An exhaustive scan of their 1,371 final return/Sharpe summaries
  finds no standalone LSTM, Informer, AutoFormer, TimesNet, or PatchTST model token
  and no return/Sharpe pair matching any of the 45 published time-series rows. See
  `author_history_output_artifact_census.csv`.
- The paper says SMA/SLMA parameters are selected on validation performance. The
  source prints candidate validation results and then hard-codes SMA=15 and
  SLMA=15/30. Only 1/6
  fixed choices equal the released-data validation argmax.
- The paper does not disclose the transaction-fee rate. The source uses 0.4% of
  traded value plus a fixed gas charge, which is necessary to match the tables.
- `run_agent.sh` is tracked as non-executable and redirects into an absent `logs/`
  directory. Its active GPT-4o ETH/SOL sideways commands use dates that differ
  from Table 1. `run_baseline.py` omits `dataset` when constructing the environment
  and depends on packages absent from the README requirement list.
- Prompt templates hard-code ETH even for BTC and SOL. The paper's generic GPT-4
  label is implemented by the source as `gpt-4-turbo`; credited GPT-4 traces use
  that released mapping, so they are source-output corroboration rather than proof
  of exact paper endpoint identity. No immutable model snapshot exists, and a
  present-day paid rerun would not prove the published result.
- The released utility reads `OPENAI_API_KEY` from the environment. This audit does
  not import the API utility or call an endpoint.

## Paper/source inconsistencies retained as evidence

- Table 5 calls the ablation ETH/GPT-4o, but its Full values (28.47%, 0.23) exactly
  duplicate BTC-bull GPT-4o in Table 2; ETH-bull GPT-4o is 25.47%, 0.18 in Table 3.
  The recovered exact-value trace is BTC-bull and declares GPT-3.5, while the
  recovered ETH/full-prompt trace is 28.11%/0.08. The other five Table 5 values
  also come from traces declaring GPT-3.5. This supplies strong numeric lineage
  while making a method-faithful Table 5 reproduction less, not more, defensible.
- The released test-period data usually match Table 1 and exactly drive the
  traditional results, but validation prices diverge and the BTC-bear start and
  SOL-bull end prices also differ. See `dataset_split_conformance.csv`.

Run `scripts/audit_cryptotrade_paper.py` to regenerate this package. Use `--strict`
when a CI failure is desired until a defensible full-paper result exists.
