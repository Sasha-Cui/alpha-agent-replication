# FLAG-Trader paper-level replication audit

The ACL 2025 proceedings PDF is the result authority. The arXiv v3 source is
machine-readable supporting evidence and compiles to 14 pages. Its two
result tables contain 360 displayed numeric cells.

## Honest outcome

- **FLAG-Trader itself: 0/360 cells reproduced.** No author-linked
  FLAG-Trader code, checkpoint, configuration, seed, action trajectory, PnL/equity
  path, or raw result output was found.
- **Paper baseline only: 6 / 360 cells reproduced.** The paper says its
  13 baseline agents come from InvestorBench. The first author-linked
  InvestorBench release supplies five of the six datasets and an evaluator. A
  literal pinned execution matches four equity Buy-and-Hold MDD cells plus BTC
  AV and MDD. The BTC CR differs in the last displayed digit. This is baseline
  evidence, not FLAG-Trader evidence.
- The BTC Sharpe cell matches only when return annualization uses 252 days while
  volatility uses 365; the released evaluator uses one calendar consistently.
- FLAG-Trader is best in only 7/24 metric-by-asset comparisons (7/12 CR/SR and
  0/12 risk cells). Against Buy-and-Hold it has 17 wins, 2 ties, and 5 losses.

## Why this is not a faithful replication

The paper specifies useful high-level architecture and 22 settings, but the
executable procedure is not identified. Blocking omissions include the exact
data snapshot/vendor, price adjustment, TSLA data, news/macro inputs, model
revision, trainable-layer split, optimizer, initialization, seeds, run count,
checkpoint selection, action paths, and result files. The displayed state,
transaction-cost instruction, action mask, reward initialization, BTC
annualization, KL penalty, and value clipping also contain source-level
conflicts documented in `method_specification_audit.csv`.

The exact-name `parkxlab/flag-trader` repository is unaffiliated and does not
implement the paper's PPO/value-network method; it receives no native-source or
result credit.

## Evidence boundary

Compiling TeX, parsing the vector prompt, compiling related Python files, and
executing InvestorBench's Buy-and-Hold formula establish document/static or
baseline evidence only. They do not reconstruct the unavailable FLAG-Trader
training or test pipeline. The work remains `paper_only_underspecified`.
