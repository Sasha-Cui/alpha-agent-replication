# AlphaQuanter paper-level conformance audit

Overall verdict: **not reproduced**. The public release provides meaningful prompt,
reward-label, reward-function, data-collection, and partial training-framework
components, but it does not ship the trained policies, paper-test prompts, original
multimodal inputs, decisions, three-seed paths, token/cost logs, or human ratings.

## Primary sources

- Official paper: https://aclanthology.org/2026.findings-acl.456.pdf (SHA-256 `433ff948a2a90cb7eb83cdb823d56ed49026795f7e2688bbe8b67bcdbd444fd5`).
- Public source: https://github.com/horizon-llm/AlphaQuanter, commit `fac423cb1b45a3d0593e88a0f9805c338d7e0fea`.
- The complete two-commit public history and all **11** accessible forks are
  exhausted as of 2026-08-14. Each fork exposes one `main` branch: one is exact
  at the current head and ten remain at the initial official commit. Across 11
  refs and two unique official-history heads, the forks add zero commits,
  blobs, tags, checkpoints, action streams, result payloads, or rating records.

## What is genuinely established

- The two Parquets contain 2,615 dated prompt/label rows: 395 trading
  dates per ticker for training and 128 per ticker for validation. Every prompt has
  the declared system/human roles, its date agrees with `extra_info`, and it requests
  at most eight tools. The file and `extra_info` call the validation split `test`;
  the paper's actual 2025 test split is absent.
- Applying the released seven-horizon, eta=0.8 forward-return formula to cent-rounded,
  hash-pinned current Yahoo prices gives 523/2,615
  exact numeric matches and 2,612/2,615
  matching BUY/HOLD/SELL reward regimes. All 640 validation regimes match. The three
  threshold crossings are documented row by row. These small differences are
  consistent with a changed adjusted-price snapshot and are not evidence of paper error.
- The audit reconstructs the released Backtrader market baseline exactly: cent-rounded
  OHLC, next-open order execution, repeated daily BUY orders using 90% of remaining
  cash, 0.1% commission, and the released ARR/SR/MDD formulas. On the current 2025
  Yahoo snapshot, only 1/34 repeated B&H cells matches at the paper's
  displayed precision; the match is rolling-window TSLA ARR. This is a baseline
  component check, not an agent result.
- The complete public Git surface contains exactly 2 commits on one branch, 31 unique
  historical paths, no tags/releases, and no unreachable objects. The initial commit
  already contains the complete released component tree; the only later change is
  `README.md` citation and paper-link editing. No revision contains a checkpoint,
  result/output/log, action/trajectory, rating, or other native paper-result payload.

## Why AlphaQuanter is not reproduced

- The audit enumerates all 790 numeric cells in Tables 5--8 and 10--14.
  The 34 B&H cells are recomputed; 33 differ on current inputs. The other 756 cells are
  unverifiable because no trained checkpoint, generated action path, per-seed trial,
  baseline output, token/cost log, or individual human rating is shipped.
- The release's `test.parquet` is the paper's 2024 validation split. No 2025 test
  Parquet is present. The paper states 122 test trading days, while the current
  exchange-calendar retrieval has 121 observations in the stated inclusive bounds.
- The checkout contains 31 tracked files and is a patch over VERL, not a standalone
  training tree: `run.sh` invokes absent `verl.trainer.main_ppo`; collection and
  evaluation use `/path/to/collected_data/`; documentation points to a plural
  `recipes/stock_trading` path that is not in the tree.
- The paper says deterministic inference at temperature 0, but `run.sh` validates at
  temperature 1.0/top-p 0.6. It reports means over three random seeds but releases no
  seed values or driver. The paper's Sharpe definition is unscaled mean/sample-std;
  source evaluation uses population std and multiplies by sqrt(number of rows).
- The rolling paper says three calendar months stepped seven days; source evaluation
  uses 60 observations stepped five rows and is hardcoded to the 128-row 2024
  validation split. The audit uses that released source behavior for its diagnostic.
- Table 5 disagrees with detailed Tables 10--11 in three displayed ARR cells by 0.01
  percentage point: FinRLA2C MSFT, FinRLA2C NVDA, and FinRLPPO MSFT.

Run `scripts/audit_alphaquanter_paper.py` to regenerate this package. Use `--strict`
when CI should fail until native checkpoints/actions, original inputs, seed protocol,
logs/ratings, and paper-test paths reproduce the published results.
