# CryptoTrade paper-level conformance audit

Overall verdict: **partial reproduction, not a full paper replication**. The pinned
public data and native trading environment strongly reproduce deterministic
traditional baselines, but the released artifacts do not reproduce CryptoTrade's
full-period LLM results or the five time-series baselines.

## Primary sources

- Official paper: https://aclanthology.org/2024.emnlp-main.63.pdf (SHA-256 `376606b05f5398c9200b0a560690693ea0a023a97631175ae02528e4dffec5cf`).
- Public source: https://github.com/Xtra-Computing/CryptoTrade, commit `210da73af5f17992be425e61305524a5c24dae40`.

## What reproduces

- A safe adapter over the released environment, 0.4% exchange cost, fixed gas cost,
  and traditional-signal logic matches 174/180 displayed cells
  across Buy-and-Hold, SMA, SLMA, MACD, and Bollinger Bands.
- 43/45 traditional strategy/asset/regime rows match all four
  displayed metrics (total return, daily mean, daily standard deviation, and
  Sharpe ratio). This includes every Buy-and-Hold, SLMA, MACD, and Bollinger row.
- ETH-sideways SMA matches the paper's -5.45% total return and -0.07 Sharpe, but
  the released path produces -0.07+/-1.00 daily return rather than -0.15+/-1.64.
  The paper's daily cell exactly duplicates its ETH-bear SMA daily cell.
- SOL-bear SMA is the larger mismatch: the paper reports +1.04% return,
  0.02+/-0.10 daily return, and 0.16 Sharpe, while every released SMA window loses
  between 17.77% and 22.19%; the runner's fixed 15-day window produces -17.77%,
  -0.28+/-2.00, and -0.14.

## Why this is not a full reproduction

- 288/468 paper result cells are unverifiable: no complete
  GPT-3.5-turbo, GPT-4, or GPT-4o result paths are shipped, and the README contains
  only the first ETH-bull GPT-4 step rather than the paper's full-period result.
- Informer, AutoFormer, TimesNet, and PatchTST implementations are absent. The
  included LSTM is embedded in an ETH-only monolithic runner, has no seed, trains
  on the full requested interval, and ships no result path.
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
- Prompt templates hard-code ETH even for BTC and SOL. The paper's GPT-4 label is
  implemented as `gpt-4-turbo`; no immutable endpoint snapshot or complete API
  response log is available, so a present-day paid rerun would not prove the
  published result.
- The released utility reads `OPENAI_API_KEY` from the environment. This audit does
  not import the API utility or call an endpoint.

## Paper/source inconsistencies retained as evidence

- Table 5 calls the ablation ETH-bull, but its Full values (28.47%, 0.23) exactly
  duplicate BTC-bull GPT-4o in Table 2; ETH-bull GPT-4o is 25.47%, 0.18 in Table 3.
- The released test-period data usually match Table 1 and exactly drive the
  traditional results, but validation prices diverge and the BTC-bear start and
  SOL-bull end prices also differ. See `dataset_split_conformance.csv`.

Run `scripts/audit_cryptotrade_paper.py` to regenerate this package. Use `--strict`
when a CI failure is desired until a defensible full-paper result exists.
