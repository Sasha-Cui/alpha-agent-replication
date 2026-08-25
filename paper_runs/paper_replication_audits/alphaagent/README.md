# AlphaAgent paper-level conformance audit

Overall verdict: **the paper is not reproduced end to end, but 5/100 Table 2
cells are corroborated by a native author run record and the paper-era
implementation is substantially recovered**. The previous audit looked only at
the rewritten default branch, then missed extensionless MLflow records in the
legacy tree; both omissions made it materially too pessimistic.

## Primary-source pins

- Final paper: https://arxiv.org/pdf/2502.16789v2 (arXiv v2, 2025-06-09; SHA-256 `cf620c3b33a98edd4124230458b65741e1767fa37a3a180828de1035ded52ab1`).
- Original preprint: https://arxiv.org/pdf/2502.16789v1 (10 pages; SHA-256 `943b286b40186ce03b8e39fc0dbd2f268807042c6192e9200e68972cb45ab890`).
- Both official PDFs and both matching arXiv source archives are hash-pinned.
  Each source compiles in two passes to the published 10-page count.
- Official repository: https://github.com/RndmVariableQ/AlphaAgent. It has two unrelated Git roots, not one
  continuous history: 8 commits on rewritten `main` and 485 on public
  `legacy-main`, 493 reachable commits in total. The public repository exposes
  only those two heads, with no tags or releases.
- A bounded GitHub GraphQL census on 2026-08-14 covered all 71 fork
  default branches: 57 point at the official legacy head, 10 at the official
  rewrite head, and four are divergent. Each divergent tip is object-pinned and
  audited separately; none receives author-native or paper-result credit.
- Mechanism snapshot: `95e47882cbed3ba0cafd42e812fe0032a8ae0681` (2025-02-12), before arXiv v1.
  It contains 856 tracked files, including 331 Python modules and 15 factor CSVs.
- The same author commit contains seven Qlib/MLflow run directories (385 files),
  executed on 2025-01-28: four S&P500 and three CSI500 runs. Every directory has
  metrics, parameters, a serialized task/config, and a fitted LightGBM state.
- The paper-era Qlib Dockerfile pins Qlib commit `c9ed050ef034fe6519c14b59f3d207abcb693282` and a
  PyTorch 2.2.1/CUDA 12.1 base image, then leaves CatBoost and XGBoost unpinned
  while pinning SciPy 1.11.4. The audit preserves this host/container split.
- The 2025-02-17 preprint-cutoff commit `0bc7a34ed9701a0149ae990b6484e7c73b347ea0` removed the
  factor zoo. The audit intentionally pins the earlier mechanism-complete tree
  and records that deletion instead of pretending the cutoff head is runnable.
- Rewritten main: `b42cb397025510da44355db9dcf278304321f589` (2026-07-03). Its first commit is
  `7debd15ca98309a8df9c1d50aca3831f320687cf` (2026-07-01T20:17:13+08:00) and has no common ancestor with the
  paper-era branch.

## What genuinely passes

- The all-version lineage contains 106 stable numeric table-cell identities.
  Version 2 revises five S&P500 AlphaForge result values and two test-period
  labels. Three logical figure assets are byte-identical, three are revised,
  and one base-LLM radar figure is added in v2. These are version facts, not
  experimental reproduction credit.
- The complete official two-root closure contains 493 commits, 3,907 blobs,
  3,912 trees, and 2,499 unique historical file paths. All 385 historical
  `saved_mlruns` paths belong to the same seven run IDs already audited; no
  prediction, return series, holding, or portfolio-analysis path is present.
- All 331 Python files in the paper-era snapshot compile under the reconstructed
  Python 3.10 host environment.
- The exact RD-Agent commit is installed with a hard dependency-release cutoff of
  `2025-02-12T13:30:56Z`. Its 153-line freeze passes `pip check`. Of 113
  modules selected by the authors' own import test, 112 import twice with real
  dependencies and zero blocked HTTP attempts. The sole failure is the committed
  developer file `rdagent.components.coder.factor_coder.test`, which opens the
  author's absolute `/home/tangziyi/RD-Agent/.../template_debug.jinjia2` path.
  The authors' singleton test passes twice; their import test therefore remains
  honestly 1/2 rather than being patched or reported green.
- A separate 119-line Qlib compatibility freeze passes `pip check`, installs the
  exact Qlib commit from the Dockerfile, retains SciPy 1.11.4, and resolves
  CatBoost 1.2.7 and XGBoost 2.1.4 using the same historical cutoff. PyTorch
  2.2.1 CPU substitutes for the unavailable CUDA container, so exact-container
  credit remains false.
- All seven shipped LightGBM model strings load twice in that Qlib environment.
  The matching S&P500 artifact is a 9-feature, 3-tree fitted model; deterministic
  zero/one-vector probes and feature-importance summaries are tracked. This proves
  the fitted states are executable, not that their paper inputs or metrics were
  regenerated.
- The exact Qlib downloader and its fallback route are now executed and pinned.
  The 450,094,816-byte US archive has 71,959 entries, 8,994 feature symbols,
  755 S&P500 membership rows, and 5,250 calendar dates from 1999-12-31 through
  2020-11-10. These are primary-source data-provenance facts; because the archive
  has no 2021--2024 observations and no `SPX` feature, they establish a replay
  failure rather than paper-result credit.
- The paper-era AST parser executes twice deterministically. Identical,
  commutative, and partially shared expressions return largest-common-subtree
  sizes 4, 3, and 3. An exact Alpha101 probe matches itself with size 23.
- A historical China candidate file has exactly 15 factors, matching Figure 4's
  caption count, but only 14 parse under the shipped AST grammar and no source
  lineage identifies it as the exact plotted pool. Count agreement is therefore
  candidate evidence, not Figure 4 reproduction.
- The loaded `alpha101.csv` has 116 rows: 101 named Alpha101 references plus 15
  appended generated expressions. That supports the paper's originality path but
  also exposes reference-zoo contamination that must be reported, not hidden.
- The historical source implements the structured hypothesis fields, multi-stage
  proposal/construct/calculate/backtest/feedback loop, factor-expression parser,
  prose description-expression alignment critic, failed/successful implementation
  memory, multi-candidate generation, and metric feedback into later rounds.
- Historical CN/US Qlib configs recover the four OHLCV feature formulas,
  next-day label, train/validation/test segments, full LightGBM kwargs, Qlib
  signal/portfolio records, top-50/drop-5 combined strategies, and stated fees.
- Fifteen historical factor CSVs contain 268 expression rows. Names identify CN,
  US, GP, o1, and DeepSeek candidate pools, but no released lineage proves which
  file or row produced any published metric.
- One full-period S&P500 record, `77b227f86e5a47bab48178cac409a98b`, carries the
  exact paper market/splits, four base factors plus five generated features,
  LightGBM depth 4, top-50/drop-5 strategy, SPX benchmark, open execution and
  5-bp sell cost. Its IC 0.0056356, ICIR 0.0552135, AR 8.7439%, IR 1.0544927,
  and MDD -9.0982% round exactly to all five AlphaAgent S&P500 cells in Table 2.
- Two full-period CSI500 records carry the paper configuration and 8/9 generated
  features, but neither matches the complete five-cell China row. Three other US
  and one China record use a 2020 test start or altered train split and receive
  no paper-cell credit.
- Separately, all 80 tests in the 2026 rewrite pass twice with real AgentScope,
  Tushare, OpenAI, LightGBM, and scikit-learn dependencies; all 72 rewrite
  modules import and no blocked HTTP send is attempted. Its 126-line environment
  freeze is tracked, and four synthetic base factors remain deterministic. This
  closes the rewrite's dependency-test gap, not the paper-era environment or any
  paper result, so these checks receive no paper-result credit.

## Why the paper is still not replicated

- Table 2 has **100 numeric result cells**. **5/100** are corroborated by one
  released native author run artifact; **0/100** have been independently
  regenerated. Eighteen more quantitative result claims in figures/text remain
  0/18. The run export omits predictions, daily returns, holdings/positions and
  complete portfolio-analysis artifacts, so its printed metrics cannot be
  recomputed from primitive outputs.
- The seven run records and factor zoo existed on 2025-02-12 but were removed
  on 2025-02-17. Consequently both the v1 submission cutoff (438 source
  commits) and v2 cutoff (483 commits) contain zero native run directories and
  zero factor-zoo files; recovery depends on earlier public history.
- The exact Baostock CSI500 and Yahoo S&P500 panels, constituent histories, and
  data transformations are absent. The US config points only to unversioned local
  `us_data`; it does not establish frozen panel identity. The paper-era Qlib
  downloader first asks for a versioned 0.9.5 archive, which is unavailable, then
  falls back to the hash-pinned `latest` asset observed on 2026-08-25. That asset
  reports Last-Modified 2024-05-22 but ends on 2020-11-10, lacks the configured
  `SPX` benchmark, does not fully cover validation, and has zero test-period dates.
  It therefore cannot be the missing panel or run the released 2021--2024 task.
- The matching model requires five generated features. At its 2025-01-28 run
  timestamp, the latest public commit contains four US candidate expressions; the
  paper snapshot contains six only after two more were added on 2025-02-12. The
  model stores anonymous `Column_0`--`Column_8` names, and no
  `combined_factors_df.pkl` exists in any reachable Git object. The exact five
  expressions, order, values, and preprocessing lineage are not recoverable.
- RD-Agent's host requirements and the Qlib Dockerfile's CatBoost/XGBoost installs
  were unpinned. A commit-date release cutoff gives a reproducible compatible
  reconstruction, but cannot prove the authors' exact installed wheels. Bouchet's
  CPU environment also does not reproduce the mirrored CUDA 12.1 image digest.
- The code defaults to GPT-4-turbo, while the paper reports GPT-3.5-turbo. The
  executed model/API snapshot, temperature, seeds, token limits, initial research
  directions, and 20 independent trial trajectories are not pinned.
- The paper's displayed regularizer is not faithfully implemented. The source has
  AST largest-subtree matching and a hard retry at duplicated size >=5, but no
  symbolic-length term, free-parameter count, numeric c1/c2 alignment scores,
  alpha=0.5 combination, beta-weighted ER function, normalization, or disclosed
  objective weights/acceptance thresholds.
- The paper says lower ER is better while adding an alignment term described as
  higher-is-better. That sign ambiguity, plus undisclosed alpha/beta weights and
  thresholds, prevents an exact objective even with recovered source.
- Historical run records substantially recover executed model/backtest settings
  and fitted LightGBM states. They expose only anonymous feature columns, however,
  so factor-pool identity, random seeds, predictions, returns, and portfolio paths
  remain missing. Exact metric correspondence is corroboration, not regeneration.
- The only divergent fork with a data candidate is the unaffiliated 2026
  `vodaza36/AlphaAgent` branch. Its 17,805,441-byte Qlib ZIP has 568 feature
  symbols and a 1,533-day calendar from 2020-01-02 through 2026-02-06, so it omits
  the paper's 2015--2019 training period. More seriously, its `sp500.txt` gives
  only 1/568 rows a finite membership end despite calling the package
  survivorship-bias-free. Its separate 2026 mining summary flags a 1,100% return
  as look-ahead leakage and ships no primitive result arrays. This is useful
  negative evidence, not a paper input or result.

## Honest boundary

The official historical source is much closer to the paper than the rewritten
default branch: this is a **substantial mechanism implementation with one exact
five-cell native output correspondence**, not merely an analogue. It is still not
an end-to-end replication of the published experiments.
The 2026 CSI1000/Tushare data package, DSL expressions, and registry metrics belong
to a disjoint rewrite and receive zero paper credit. The 71-fork census likewise
adds zero paper-result units. Run
`scripts/audit_alphaagent_paper.py` to regenerate the package; `--strict` remains
fail-closed until paper-era inputs, predictions, portfolios, stochastic trial
lineage, and every published result are reproduced.
