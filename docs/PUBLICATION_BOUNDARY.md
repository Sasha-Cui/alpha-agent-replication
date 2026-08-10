# Publication Boundary

## Include

- `src/alpha_evolve/`: reusable package code.
- `scripts/`: compatibility entry points and research runners.
- `literature_review/*.csv`, `literature_review/*.json`, and `literature_review/source_pasted_text.txt`: source inventory and audit inputs.
- `literature_review/papers/`: the 45 downloaded source-paper PDFs recorded by
  `literature_review/download_log.csv`.
- `paper_runs/`: compact tracked ledgers, verdicts, summaries, small reproducibility CSVs, and final report figures under `paper_runs/performance_analysis/figures/`.
- `paper_runs/submission_evidence/`: frozen locks, manifests, aggregate estimates,
  multiplicity results, diagnostic summaries, and hashes of excluded reconstruction
  artifacts.
- `report.md`, `README.md`, `pyproject.toml`, `environment.toml`, and this `docs/` directory, including manuscript source, bibliography, generated tables, and deterministic figure PDFs.
- `COLLABORATOR_HANDOFF.md` and `paper_runs/handoff/`: collaborator navigation,
  a compact 50-strategy aggregate result index, its deterministic builder, and
  a hash-pinned scope manifest.
- `output/pdf/icaif2026_submission.pdf`: the single canonical compiled manuscript.

## Exclude

The following are intentionally ignored because they are generated, local, private, or too large for the public source tree:

- virtualenvs and package installs: `.venv/`, `.venv_*/`, `__pycache__/`.
- cloned/vendor repositories: `external_repos/`, `external_repos_code_links/`.
- temporary paper-extraction payloads: `paper_runs/idea_replications/paper_pdf_tmp/`.
- run logs and scratch outputs: `logs/`, `runs/`, `artifacts/`, `tmp_scratch/`, `paper_runs/full_loop/`.
- high-volume monthly candidate and factor reconstruction matrices under
  `paper_runs/submission_evidence/`; their checksums remain in tracked run
  manifests and the licensed inputs plus tracked runners regenerate them.
- network-discovery caches, which may contain transient third-party payloads.
- alternate compiled manuscript PDFs, TeX auxiliary files, source archives, and
  local page renderings under `output/`, `docs/paper/`, and `tmp/`; the canonical
  `output/pdf/icaif2026_submission.pdf` is the sole tracked exception.

## Path Policy

Repository-local files are discovered relative to the checkout. External data defaults are Bouchet-compatible but must be overridden with `ALPHA_EVOLVE_*` environment variables outside Bouchet. Do not hardcode retired monorepo checkout paths in new code or docs.

## License

Original source code and tests are licensed under Apache-2.0. Original
documentation, manuscript material, figures, tables, and registry annotations
are licensed under CC BY 4.0. Third-party artifacts and market data retain their
own terms; see `LICENSES/README.md` and `LICENSES/THIRD_PARTY.md`.
