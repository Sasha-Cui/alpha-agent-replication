# AlphaAgent paper-level conformance audit

Overall verdict: **not reproduced**. The official repository is a runnable
post-paper component analogue, not the implementation that produced the paper.

## Primary-source pins

- Official paper: https://arxiv.org/pdf/2502.16789v2 (arXiv v2, 2025-06-09; SHA-256 `cf620c3b33a98edd4124230458b65741e1767fa37a3a180828de1035ded52ab1`).
- Official source: https://github.com/RndmVariableQ/AlphaAgent, commit `b42cb397025510da44355db9dcf278304321f589` (2026-07-03).
- The repository's first commit is `7debd15ca98309a8df9c1d50aca3831f320687cf` (2026-07-01T20:17:13+08:00); no
  paper-era source revision exists in its Git history.

## What genuinely passes

- All 80 upstream tests pass under Python 3.12 when import-only stubs replace the
  unavailable Tushare and AgentScope packages. This validates deterministic code
  components, not the declared dependency environment or any paper experiment.
- The post-paper DSL executes the four named paper base-factor formulas twice on
  synthetic OHLCV data with identical output hashes.
- The released operator library, factor evaluation tools, multi-candidate prompt,
  and metric-feedback loop are meaningful analogues to parts of the paper.
- The linked 524,248,466-byte `alphaagent-data-20260703.zip` is reachable and its
  public metadata is recorded. It is CSI1000/Tushare data through June 2026.

## Why the paper is not replicated

- Table 2 contains **100 numeric result cells** (10 methods x 2 markets x 5
  metrics). **0/100** has a native released result path. Table 1 contributes six
  trading-day configuration cells; none can be reconstructed from released
  paper data. Eighteen additional numeric result claims in figures/text also have
  zero native reproductions.
- The paper uses Baostock CSI500 and Yahoo S&P500 OHLCV panels, GPT-3.5-turbo,
  three specialized agents, LightGBM, and a Qlib top-50/drop-5 backtest. The
  release uses Tushare CSI1000, defaults to gpt-4o-mini, has one tool-calling
  trajectory, and marks model/portfolio/backtest packages as future work.
- Paper originality is largest-common-subtree AST isomorphism against Alpha101.
  Released similarity is mean daily cross-sectional Pearson correlation. Its
  parser compiles expressions to Python code strings and does not implement the
  paper's AST score, symbolic-length/free-parameter penalties, ER objective, or
  two-part LLM alignment score.
- No paper prompt, seed hypothesis, 20-trial trajectory, candidate pool, 15 final
  factors, LightGBM model, prediction, holding, daily return, Qlib recorder,
  baseline output, figure array, token log, or p-value sample is shipped.
- Seventeen paper specification gaps independently prevent exact reconstruction,
  including undisclosed alpha/beta weights, similarity normalization and filter
  thresholds, remaining LightGBM parameters, factor outputs, trial aggregation,
  universe history, and complete portfolio semantics.

## Honest boundary

The 13 DSL expressions and eight registry metric entries were generated in 2026
for a different dataset and protocol. They remain useful current-release evidence
but receive zero paper credit. The newer data package is likewise not retroactively
the frozen paper input. Run `scripts/audit_alphaagent_paper.py` to regenerate this
package; use `--strict` to fail until the paper-era data, source, prompts, trials,
factors, models, portfolios, baselines, and all published results are reproduced.
