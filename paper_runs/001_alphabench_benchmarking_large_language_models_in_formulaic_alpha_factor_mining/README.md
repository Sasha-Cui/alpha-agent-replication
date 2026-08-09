# AlphaBench benchmark status

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/AlphaBench`

AlphaBench is a public benchmark/toolchain for formulaic alpha generation and evaluation. The repository includes Qlib/Assay-backed factor evaluation infrastructure, a factor pool, Alpha101/Alpha158-style libraries, search algorithms, and a small SQLite factor cache.

The shipped artifacts are not a portfolio return stream. The factor pool contains expressions, and the SQLite cache contains a handful of IC/RankIC-style evaluations for CSI300/CSI500 over 2023-2025. It does not contain dated factor returns, portfolio weights, monthly candidate returns, Sharpe calculations, or any FF3/FF5Mom comparison.

Current status: not directly benchmarkable under the common FF3/FF5Mom protocol. To turn AlphaBench into a candidate strategy, we would need a separate adapter that evaluates selected expressions on the same US monthly universe as the external same-universe factor panel, converts factor scores into long-short portfolio returns, and then feeds those returns into `scripts/evaluate_candidate_returns.py`.
