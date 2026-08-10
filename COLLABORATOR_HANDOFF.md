# Collaborator Handoff

This repository contains the research record for the Alpha Agent Replication
project and its ICAIF 2026 submission. It supports immediate claim auditing,
rebuilding compact public artifacts, and identifying runs that require
separately authorized data.
The repository favors machine-readable evidence and deterministic checks over
narrative claims, so each headline number has a traceable artifact.

## Read this first

The repository contains 50 implemented and backtested strategy mappings from
40 retained papers. They comprise 0 end-to-end native-agent replications, 1
released-code component adaptation, 12 source-grounded paper components, and
37 researcher-authored in-spirit reconstructions.

Each mapping has an executable formula, frozen candidate identifier, controlled
common-task returns, and matched four-rung benchmark results. Git publishes
aggregate tables and diagnostics, not licensed security-level inputs, factor
time series, or monthly strategy-return matrices.

Start with [`paper_runs/handoff/strategy_result_index.csv`](paper_runs/handoff/strategy_result_index.csv),
a 50-row, 58-column index joining paper identity, provenance, attribution
limits, benchmark estimates, inference flags, and closest-factor diagnostics.
Its scope and hashes are in [`paper_runs/handoff/manifest.json`](paper_runs/handoff/manifest.json).
Use [`docs/SCIENTIFIC_AUDIT.md`](docs/SCIENTIFIC_AUDIT.md) for the claim audit
and `paper_runs/submission_evidence/replication_scope/mapping_scope_ledger.csv`
for the row-level 62-to-50 selection.

## Current empirical status

The benchmark ladder evaluates all 50 strategies over the same 126 months
(2011-08-31 through 2022-01-31) at a 10-basis-point one-way cost. Positive
alpha estimates number 44 under CAPM, 41 under FF3, 41 under FF5 plus momentum,
and 17 under the market plus 132 JKP characteristics; Holm-positive counts are
6, 1, 2, and 0. Forty-seven strategies have absolute correlation of at least
0.50 with their closest JKP factor.

These are retrospective conditional spanning diagnostics. Mappings were not
frozen before U.S. outcomes or independently second-coded. Results neither
estimate unavailable native agents nor establish a causal pretraining channel.

The separate 14-attempt code audit reproduces zero native agents. One
QuantEvolver seed supports a component adaptation; remaining attempts retain
documented blockers. A blocker records an evidence limitation; it is not
encoded as a zero return. A source-benchmark audit covers all 40 mapped papers:
38 had verified full text, 37 had no identified asset-pricing spanning
regression, and one reported Carhart-four and FF5 loadings without a
factor-adjusted intercept. None used JKP132; two remain unresolved from partial
records. The coding is descriptive and not outcome-blind.

## Canonical paper

| Artifact | SHA-256 |
| --- | --- |
| `output/pdf/icaif2026_submission.pdf` | `311cd1f799a70fe0208a7e3f7ce410c54bd9af9a749fe9605bec94dab6af8b35` |
| `docs/paper/icaif2026_submission.tex` | `656bc442f93ea74de92434883dbdacc3711328ce12ceaa625c5503813dd14d6c` |

The PDF is seven US-Letter pages using vendored ACM 2.19. The fresh-clone gate
passes 62 source/PDF checks without build residue; the explicit release build
passes 71 checks. Both pass locked-evidence validation. See
[`docs/VALIDATION_STATUS.md`](docs/VALIDATION_STATUS.md). PDFs under
`docs/paper/figures/` are figures; other research reports and older manuscript
materials are labeled provenance, not alternate submissions. The matched
benchmark ladder and nearest-JKP-factor analysis appear in the canonical paper.

## Repository map

- `src/alpha_evolve/`: reusable portfolio and evaluation code.
- `scripts/`: runners, builders, and validators.
- `tests/`: unit and artifact-consistency tests.
- `literature_review/`: 98-work corpus, metadata, and screening rules.
- `paper_runs/submission_evidence/`: aggregate evidence and manifests.
- `paper_runs/handoff/`: collaborator result index.
- `docs/paper/`: canonical source, tables, figures, and ACM template.
- `output/pdf/icaif2026_submission.pdf`: canonical compiled paper.
- `LICENSES/`: publication and third-party boundaries.

See [`docs/EXPERIMENT_INDEX.md`](docs/EXPERIMENT_INDEX.md) and
[`docs/DATA_AND_ARTIFACTS.md`](docs/DATA_AND_ARTIFACTS.md).

## First-hour setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/build_collaborator_handoff.py
git diff --exit-code -- paper_runs/handoff
```

On Bouchet, use the central environment rather than installing into a local
`.venv` symlink:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/current/alpha-evolve/bin/python -m pytest -q
```

## Reproduction levels

### Level A: audit frozen evidence

No external data are required. Review the handoff index, mapping audit,
source-anchor packet, direct-code inventory, benchmark summaries, manifests,
tests, paper source, and PDF. Rebuild the index with:

```bash
python scripts/build_collaborator_handoff.py
```

### Level B: rebuild publication assets

Validate tracked summaries and the prebuilt PDF with:

```bash
python scripts/validate_submission_package.py
```

For an explicit release build:

```bash
python scripts/build_icaif2026_submission_assets.py
python scripts/build_icaif2026_submission.py
python scripts/validate_icaif_submission.py \
  --pdf output/pdf/icaif2026_submission.pdf \
  --log docs/paper/icaif2026_submission.log \
  --bbl docs/paper/icaif2026_submission.bbl \
  --require-build-log
```

Compilation requires TeX Live and Poppler-compatible tools.

### Level C: rerun empirical estimation

This requires authorized JKP security-level data and the factor panel. Configure
the `ALPHA_EVOLVE_*` paths in `README.md`. Full runners write ignored monthly
matrices; compact results and manifests are the publication artifacts. The
repository intentionally does not export the licensed inputs.

For collaborators independently authorized to use those inputs,
[`docs/AUTHORIZED_COLLABORATOR_BUNDLE.md`](docs/AUTHORIZED_COLLABORATOR_BUNDLE.md)
documents the license-gated builder for the 50 monthly candidate paths, both
factor panels, fitted values, residuals, monthly ridge choices, rolling
loadings, and a hash-pinned manifest. The generated directory and archive must
remain outside Git and travel only through an approved transfer channel.
