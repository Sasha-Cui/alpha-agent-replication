# MadEvolve trading paper and author-framework audit

This audit pins arXiv `2605.23007v1`, its complete 19-file source package,
and the 69-file MadEvolve framework repository at `8b881d3a`. The paper
directly links `madevolve.org`; that first-party site directly links
`tianyi-stack/MadEvolve`, whose owner Tianyi Li is the paper's second author.
This is a direct paper-to-framework-site-to-coauthor-repository route rather
than an inferred thematic match. The source rebuilds to the same 46-page
length. All 46 official and all 46 rebuilt pages were visually checked; no
unreadable, clipped, overlapping, blank, or missing research content was found.

The repository is a substantive general-purpose framework. It includes an
evolution orchestrator, multi-provider LLM gateway, differential-patch and
rewrite modes, MAP-Elites partitions, ring-island migration, an elite vault,
native and Slurm execution, SQLite artifact lineage, and report analysis. In a
controlled fixture, the patcher, grid, islands, elite vault, and artifact store
all work. These checks establish framework-component conformance only.

The full public Git history was also audited, rather than only the pinned head.
It contains six commits on one branch and no tags, releases, or unreachable Git
objects. Every revision has the same 69 tracked paths and 66 Python files, zero
structured data/result payloads, and zero Bitcoin, backtest, portfolio, or
paper-metric literals outside the README. No earlier or alternate public
revision supplies the missing trading research lineage.

The public fork surface was exhausted as of 2026-08-14. GitHub reports two
accessible forks with two branch refs and no tag refs. One ref is exactly the
official head and the other is the initial commit in the already-audited
official history. The two refs therefore add zero unique commits, zero unique
blobs, and zero trading or native-result artifacts. Neither fork supplies any
of the missing experiment lineage or earns paper-result credit.

The package does not run cleanly exactly as declared. Its editable install
resolves 39 packages, but the documented CLI immediately fails because
`python-dotenv` is imported and omitted from `pyproject.toml`. Adding that one
package only to the isolated audit environment restores version/help/core
imports. Even then, 64/66 modules import while `madevolve.templates` and
`madevolve.templates.insight` fail: `templates/insight.py` line 123 has an
unmatched parenthesis, so full bytecode compilation fails. The release ships no
tests. Its site and package metadata declare MIT, but the repository contains no
license text and GitHub detects no license.

More importantly, the release contains no trading-specific implementation at
all. There is no BTCUSD/OHLCV adapter, Polygon data snapshot, alpha forecaster,
order lifecycle, fill model, fees, market impact, backtester, paper configuration,
seed, exact model routing, call trace, candidate program, best evolved strategy,
run history, Optuna study, Claude Code ideas tree, run report, holdings, returns,
table array, or plot array. The appendix code is an incomplete skeleton with
omissions and unreleased project dependencies, not a runnable trading package.
The paper also uses five islands while the public default is four; interval five
and migration rate 0.1 match, but the actual paper configuration is absent.

The strict paper-level result is therefore **0/214 empirical numeric table units
and 0/21 empirical panels regenerated**. Rebuilding the PDF, adapting the CLI,
and exercising the general framework receive no paper-result credit. This is a
meaningful framework release, but it is not a true replication package for the
reported BTCUSD experiments. The paper itself appropriately cautions that its
exchange-aggregated data is not directly tradable and does not establish live
performance.
