# Publication Boundary

## Include

- `src/alpha_evolve/`: reusable package code.
- `scripts/`: compatibility entry points and research runners.
- `literature_review/*.csv`, `literature_review/*.json`, and `literature_review/source_pasted_text.txt`: source inventory and audit inputs.
- `paper_runs/`: compact tracked ledgers, verdicts, summaries, small reproducibility CSVs, and final report figures under `paper_runs/performance_analysis/figures/`.
- `report.md`, `README.md`, `pyproject.toml`, `environment.toml`, and this `docs/` directory, including the compact TeX report.

## Exclude

The following are intentionally ignored because they are generated, local, private, or too large for the public source tree:

- virtualenvs and package installs: `.venv/`, `.venv_*/`, `__pycache__/`.
- cloned/vendor repositories: `external_repos/`, `external_repos_code_links/`.
- downloaded paper PDFs and temporary extraction payloads: `literature_review/papers/`, `paper_runs/idea_replications/paper_pdf_tmp/`.
- run logs and scratch outputs: `logs/`, `runs/`, `artifacts/`, `tmp_scratch/`, `paper_runs/full_loop/`.

## Path Policy

Repository-local files are discovered relative to the checkout. External data defaults are Bouchet-compatible but must be overridden with `ALPHA_EVOLVE_*` environment variables outside Bouchet. Do not hardcode retired monorepo checkout paths in new code or docs.

## License

No license file has been selected in this change. Pick the intended license before publication, then add the license file and matching `pyproject.toml` metadata.
