# Alpha Agent Replication

This repository is the research artifact for an ICAIF 2026 submission asking
whether public evidence substantiates claims that financial LLM agents discover
alpha beyond familiar asset-pricing factors. The current study puts source
fidelity before attribution. A strict audit of the prior 50 common-task mappings
assigns A0/B0/C15/D33/U2: none is a faithful system replication or faithful
disclosed component. Their broad benchmark ladder is retained only as a legacy
construction diagnostic, not as evidence that factors span the papers' agents.

The primary formula evidence is now an exhaustive three-seed census from the
pinned QuantEvolver release. All three counted rows preserve the released
expressions, executable DSL semantics, pairwise missing-data rule, forward-close
return definition, and equal-mean top/bottom-quintile evaluator; only cadence,
universe, and holding horizon change. The fail-closed PR-style gate reports 3/3 strict grade
B components (100%). The offline gate also executes the exact pinned upstream
evaluator on outcome-blind synthetic OHLCV data; all 1,296 score comparisons
and 105 portfolio timestamps conform. The separate D07 owner-review
attestation remains explicitly pending. Nine additional formulas with unpinned
or reconstructed
semantics remain visible as non-primary diagnostics. A separate GuruAgents replay
executes all 190 disclosed prompt cells, constructs 24 costed paths, and reports
matched factor attribution for 12 long-archive paths over a shared 33-month
window. These are component-level studies, not native-system replications.

The cutoff-bounded 98-work screen, artifact audit, and 67-lineage native-fidelity
ledger provide broader evidence about public availability and task compatibility;
they are supporting parts of the current claim record rather than its sole center.

## Collaborator Handoff

Start with the current claim boundary
([`docs/FIDELITY_AUDIT.md`](docs/FIDELITY_AUDIT.md)), current manuscript
([`docs/paper/icaif2026_submission.tex`](docs/paper/icaif2026_submission.tex)), and
tracked PDF ([`output/pdf/icaif2026_submission.pdf`](output/pdf/icaif2026_submission.pdf)),
then inspect the three principal evidence packages:

- [`paper_runs/submission_evidence/strict_proxy_fidelity_audit/`](paper_runs/submission_evidence/strict_proxy_fidelity_audit/) - strict A/B/C/D/U grades for the legacy 50 mappings.
- [`paper_runs/faithful_component_replications/`](paper_runs/faithful_component_replications/) - primary three-component census, strict grade-B ledger, source pins, and attribution outputs.
- [`paper_runs/prompt_replay/guruagents/performance/`](paper_runs/prompt_replay/guruagents/performance/) - the 190-cell GuruAgents replay, 24 costed paths, and 12-path-by-33-month matched attribution.

The older 12-formula package in [`paper_runs/fidelity_formula_components/`](paper_runs/fidelity_formula_components/) is retained as a mixed-fidelity diagnostic and is not part of the 100% denominator.

The cutoff-bounded artifact audit
([`paper_runs/submission_evidence/artifact_audit/`](paper_runs/submission_evidence/artifact_audit/))
and native-fidelity ledger
([`paper_runs/submission_evidence/native_fidelity_ledger.csv`](paper_runs/submission_evidence/native_fidelity_ledger.csv))
provide broader corpus and repository context. The experiment map is in
[`docs/EXPERIMENT_INDEX.md`](docs/EXPERIMENT_INDEX.md). The older 50-row dataframe
([`paper_runs/handoff/strategy_result_index.csv`](paper_runs/handoff/strategy_result_index.csv))
is retained only as a legacy ladder-construction diagnostic.
[`COLLABORATOR_HANDOFF.md`](COLLABORATOR_HANDOFF.md) provides a broader navigation
guide. Documents now marked SUPERSEDED / INVALIDATED, including
[`docs/SCIENTIFIC_AUDIT.md`](docs/SCIENTIFIC_AUDIT.md), are retained only for
provenance and must not be used as the current claim record. The outcome-blind,
double-coded protocol for historical mappings remains documented in
[`docs/INDEPENDENT_MAPPING_REVIEW_PLAN.md`](docs/INDEPENDENT_MAPPING_REVIEW_PLAN.md).

The 50 historical rows remain available as a reproducible common-construction
diagnostic, but their strict fidelity grades preclude paper- or agent-level
attribution. The formula and prompt packages are separately anchored to disclosed
source components. Neither recovers a native agent, search trajectory, training
process, or published performance table.

## Current ICAIF Submission

- [`output/pdf/icaif2026_submission.pdf`](output/pdf/icaif2026_submission.pdf) - current tracked six-page anonymous submission PDF (verified August 10, 2026). A later final build can change the page count, so rerun validation before submission.
- [`docs/paper/icaif2026_submission.tex`](docs/paper/icaif2026_submission.tex) - submission source using the vendored ACM 2.19 template.
- [`docs/FIDELITY_AUDIT.md`](docs/FIDELITY_AUDIT.md) - current claim and fidelity boundary.
- [`paper_runs/submission_evidence/strict_proxy_fidelity_audit/`](paper_runs/submission_evidence/strict_proxy_fidelity_audit/) - strict audit of the legacy 50 mappings.
- [`paper_runs/faithful_component_replications/`](paper_runs/faithful_component_replications/) - current primary 3/3 strict-B disclosed-component study.
- [`paper_runs/fidelity_formula_components/`](paper_runs/fidelity_formula_components/) - non-primary mixed-fidelity 12-formula diagnostic.
- [`paper_runs/prompt_replay/guruagents/performance/`](paper_runs/prompt_replay/guruagents/performance/) - current GuruAgents replay and factor-attribution package.
- [`docs/source_anchor_review_packet.md`](docs/source_anchor_review_packet.md) - legacy page-anchored audit for the prior mapping layer.
- [`docs/full_corpus_bibliography.md`](docs/full_corpus_bibliography.md) - all 98 screened canonical works.
- [`paper_runs/submission_evidence/`](paper_runs/submission_evidence/) - supporting artifact, native-fidelity, scope, and robustness evidence.

Build and validate the submission from the repository root:

```bash
python scripts/validate_faithful_component_replications.py
python scripts/validate_submission_package.py
```

This fresh-clone gate performs 62 source/PDF artifact checks and does not depend
on ignored LaTeX auxiliary files. A release build adds nine explicit build-log
checks:

```bash
python scripts/build_icaif2026_submission_assets.py
python scripts/build_icaif2026_submission.py
python scripts/validate_icaif_submission.py \
  --pdf output/pdf/icaif2026_submission.pdf \
  --log docs/paper/icaif2026_submission.log \
  --bbl docs/paper/icaif2026_submission.bbl \
  --require-build-log
```

The release build must pass both fail-closed validators and the locked-evidence
wording gate. The validation scopes, software prerequisites, hashes, and
exact commands are recorded in
[`docs/VALIDATION_STATUS.md`](docs/VALIDATION_STATUS.md).
Large licensed security-level inputs and regenerated monthly reconstruction
matrices remain outside Git; their paths and SHA-256 hashes are recorded in the
run manifests.
Authorized collaborators can use the documented external packager in
[`docs/AUTHORIZED_COLLABORATOR_BUNDLE.md`](docs/AUTHORIZED_COLLABORATOR_BUNDLE.md)
to receive the complete legacy 50-strategy and factor-reconstruction matrices without
placing licensed derived data in the public repository.

## Repository Layout

- `src/alpha_evolve/` - importable Python package for JKP return construction, benchmark evaluation, path policy, and shared utilities.
- `scripts/` - research runners, deterministic artifact builders, and validation entry points.
- `literature_review/` - source inventory used to build the paper/repository universe.
- `paper_runs/` - compact tracked replication ledgers, summaries, verdicts, small CSV outputs, and final report figures.
- `paper_runs/handoff/` - legacy 50-strategy construction-diagnostic index and scope manifest.
- `paper_runs/submission_evidence/strict_proxy_fidelity_audit/` - strict fidelity grades for the legacy 50 mappings.
- `paper_runs/faithful_component_replications/` - primary 100%-passing disclosed-component evidence.
- `paper_runs/fidelity_formula_components/` - mixed-fidelity formula diagnostics retained outside the primary denominator.
- `paper_runs/prompt_replay/guruagents/performance/` - current GuruAgents prompt-replay performance evidence.
- `paper_runs/submission_evidence/native_fidelity_ledger.csv` - supporting 67-lineage native-fidelity ledger.
- `paper_runs/submission_evidence/artifact_audit/` - supporting cutoff-bounded artifact-audit evidence.
- `docs/FIDELITY_AUDIT.md` - current claim and fidelity boundary.
- `output/pdf/icaif2026_submission.pdf` - tracked current submission artifact.
- `report.md` - superseded legacy replication report retained for provenance.
- `docs/alpha_agent_replication_report.tex` - superseded legacy TeX report retained for provenance.
- `docs/PUBLICATION_BOUNDARY.md` - tracked-vs-generated publication boundary.

## Install

For the tested dependency set, install the hash-pinned lock and then the
editable project without re-resolving dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --require-hashes -r requirements-lock.txt
python -m pip install --no-deps -e .
```

Use `python -m pip install -e ".[dev]"` only when intentionally updating the
lock. The Bouchet environment manifest is kept in `environment.toml`;
installed packages and virtualenvs are intentionally not tracked.

## External Inputs

Counted experiments use read-only local research inputs. The official [JKP data library](https://www.jkpfactors.com/data) supplies public factor returns, while the [JKP WRDS guide](https://www.jkpfactors.com/jkp-wrds-guide) explains authorized access to the stock-level panel required for end-to-end portfolio reconstruction. See [`docs/DATA_AND_ARTIFACTS.md`](docs/DATA_AND_ARTIFACTS.md) for the exact boundary and hash-verification procedure. Defaults point to the Bouchet project layout, and public users can override them:

```bash
export ALPHA_EVOLVE_REPO=/path/to/alpha-agent-replication
export ALPHA_EVOLVE_JKP_ROOT=/path/to/jkp-data
export ALPHA_EVOLVE_JKP_USA=/path/to/USA.parquet
export ALPHA_EVOLVE_FACTOR_DATA_ROOT=/path/to/KnowledgeTemplate
export ALPHA_EVOLVE_RETURN_DATA_ROOT=/path/to/KnowledgeTemplate/return_pipeline/return_data_assembly
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

## Project Governance

Contribution, security, citation, and release rules are recorded in [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), [`CITATION.cff`](CITATION.cff), and [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md). [`CHANGELOG.md`](CHANGELOG.md) distinguishes unreleased work from immutable releases.

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
