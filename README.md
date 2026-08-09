# Alpha Agent Replication

This repository contains the publishable core of the `alpha_evolve` audit: a reproducible scan of LLM/agentic alpha-mining papers and public repositories against JKP-USA and TextBenchmark-style performance tests.

The headline finding is negative: direct public-code replications did not produce convincing new alpha beyond JKP/TextBenchmark, and the few in-spirit survivors are mostly classic value, quality, profitability, momentum, and low-risk composites.

## Repository Layout

- `src/alpha_evolve/` - importable Python package for JKP return construction, benchmark evaluation, path policy, and shared utilities.
- `scripts/` - backwards-compatible command wrappers and research-specific runners.
- `literature_review/` - source inventory used to build the paper/repository universe.
- `paper_runs/` - compact tracked replication ledgers, summaries, verdicts, small CSV outputs, and final report figures.
- `report.md` - final replication report.
- `docs/alpha_agent_replication_report.tex` - compact TeX version of the replication report for paper citation and circulation.
- `docs/PUBLICATION_BOUNDARY.md` - tracked-vs-generated publication boundary.

## Install

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

The Bouchet environment manifest is kept in `environment.toml`. Installed packages and virtualenvs are intentionally not tracked.

## External Inputs

Counted experiments use read-only local research inputs. Defaults point to the Bouchet project layout, and public users can override them:

```bash
export ALPHA_EVOLVE_REPO=/path/to/alpha-agent-replication
export ALPHA_EVOLVE_JKP_ROOT=/path/to/jkp-data
export ALPHA_EVOLVE_JKP_USA=/path/to/USA.parquet
export ALPHA_EVOLVE_factor_data_ROOT=/path/to/external-factor-data
export ALPHA_EVOLVE_FACTOR_PANEL=/path/to/benchmark_factor_panel.csv
```

Legacy diagnostics that use paper-shipped or official-French return streams are disabled by default. Enable them only for non-counting audit reproduction:

```bash
export ALLOW_LEGACY_NON_JKP_RETURNS=1
```

## Common Commands

Build monthly JKP long-short candidate returns:

```bash
alpha-evolve-build-jkp   --candidate-cols ret_12_1,be_me   --out-dir paper_runs/example_jkp
```

Evaluate a candidate against a JKP-built factor panel:

```bash
alpha-evolve-evaluate-jkp   --candidate-id example   --candidate-csv paper_runs/example_jkp/candidate_returns_jkp_ret_12_1.csv   --factor-panel-csv paper_runs/example_jkp/jkp_benchmark_factor_panel.csv   --out-dir paper_runs/example_jkp/results
```

The old `scripts/*.py` commands still work from a checkout; they now delegate to the package where practical.

## Open-Source Licensing

Alpha Agent Replication is open-source software intended to help researchers
audit and replicate claims about large-language-model and agent-based alpha
mining. The project's original source code, tests, and build scripts are
licensed under the Apache License, Version 2.0; see [`LICENSE`](LICENSE).

The manuscript, project-authored protocols, figures, tables, and original
registry annotations are licensed under Creative Commons Attribution 4.0
International. Third-party papers, repositories, software, and market data
retain their own terms and are not relicensed here. Some replication inputs
must therefore be obtained separately from their authorized sources. See
[`LICENSES/README.md`](LICENSES/README.md) for the complete licensing map.
