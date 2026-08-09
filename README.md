# Alpha Agent Replication

This repository is the central record for the Alpha Agent Replication project and its ICAIF 2026 submission. It contains the screened literature corpus, artifact and implementation audits, good-faith source-to-implementation mappings, frozen empirical summaries, paper source, validation code, and reviewable submission PDF.

The paper asks whether financial LLM agents discover alpha beyond familiar
asset-pricing factors. The evidence screen covers 98 works, retains 69 for the
operational census, reconstructs 50 strategies from 40 papers, and evaluates
every reconstruction against the same CAPM, FF3, FF5-plus-momentum, and JKP132
benchmark ladder. Profitable-looking returns largely disappear under the broad
factor benchmark: median annualized alpha falls from 9.97% under CAPM to
-1.69% under JKP132, with zero Holm-adjusted survivors. These retrospective
mapping results are not native-agent replications and do not identify model
pretraining as the causal mechanism.

## Collaborator Handoff

Start with [`COLLABORATOR_HANDOFF.md`](COLLABORATOR_HANDOFF.md), the experiment
map in [`docs/EXPERIMENT_INDEX.md`](docs/EXPERIMENT_INDEX.md), and the compact
50-row result dataframe in
[`paper_runs/handoff/strategy_result_index.csv`](paper_runs/handoff/strategy_result_index.csv).

The 50 rows are genuinely implemented and backtested common-task strategies,
but they are not 50 native-agent replications. They comprise one released-code
component adaptation, 12 source-grounded paper components, and 37 in-spirit
reconstructions. The direct-code audit reproduces zero native agents. This
provenance boundary is enforced by the handoff manifest and tests.

## Current ICAIF Submission

- [`output/pdf/icaif2026_submission.pdf`](output/pdf/icaif2026_submission.pdf) - current seven-page anonymous submission PDF.
- [`docs/paper/icaif2026_submission.tex`](docs/paper/icaif2026_submission.tex) - submission source using the vendored ACM 2.19 template.
- [`docs/source_anchor_review_packet.md`](docs/source_anchor_review_packet.md) - page-anchored audit of the 13 closest source mappings.
- [`docs/full_corpus_bibliography.md`](docs/full_corpus_bibliography.md) - all 98 screened canonical works.
- [`paper_runs/submission_evidence/`](paper_runs/submission_evidence/) - frozen aggregate evidence, manifests, mapping ledgers, and robustness outputs.

Build and validate the submission from the repository root:

```bash
python scripts/build_icaif2026_submission_assets.py
python scripts/build_icaif2026_submission.py
python scripts/validate_submission_package.py
```

The canonical source and PDF pass all 71 ACM-format checks and the current
locked-evidence wording gate. Their hashes and the exact validation commands
are recorded in [`docs/VALIDATION_STATUS.md`](docs/VALIDATION_STATUS.md).
Large licensed security-level inputs and regenerated monthly reconstruction
matrices remain outside Git; their paths and SHA-256 hashes are recorded in the
run manifests.

## Repository Layout

- `src/alpha_evolve/` - importable Python package for JKP return construction, benchmark evaluation, path policy, and shared utilities.
- `scripts/` - research runners, deterministic artifact builders, and validation entry points.
- `literature_review/` - source inventory used to build the paper/repository universe.
- `paper_runs/` - compact tracked replication ledgers, summaries, verdicts, small CSV outputs, and final report figures.
- `paper_runs/handoff/` - compact 50-strategy collaborator index and hash-pinned scope manifest.
- `output/pdf/icaif2026_submission.pdf` - tracked current submission artifact.
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
export ALPHA_EVOLVE_FACTOR_DATA_ROOT=/path/to/factor-data
export ALPHA_EVOLVE_FACTOR_PANEL=/path/to/benchmark_factor_panel.csv
```

Legacy diagnostics that use paper-shipped or official-French return streams are disabled by default. Enable them only for non-counting audit reproduction:

```bash
export ALLOW_LEGACY_NON_JKP_RETURNS=1
```

## Common Commands

Build monthly JKP long-short candidate returns:

```bash
alpha-evolve-build-jkp \
  --candidate-cols ret_12_1,be_me \
  --out-dir paper_runs/example_jkp
```

Evaluate a candidate against a JKP-built factor panel:

```bash
alpha-evolve-evaluate-jkp \
  --candidate-id example \
  --candidate-csv paper_runs/example_jkp/candidate_returns_jkp_ret_12_1.csv \
  --factor-panel-csv paper_runs/example_jkp/jkp_benchmark_factor_panel.csv \
  --out-dir paper_runs/example_jkp/results
```

The `scripts/*.py` entry points remain available for research-specific and
submission workflows; reusable portfolio and performance logic lives under
`src/alpha_evolve/`.

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
