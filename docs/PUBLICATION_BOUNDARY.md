# Publication Boundary

## Include

- `src/alpha_evolve/`: reusable package code.
- `scripts/`: compatibility entry points and research runners.
- `literature_review/*.csv`, `literature_review/*.json`, and `literature_review/source_pasted_text.txt`: source inventory and audit inputs.
- `literature_review/papers/`: the 46 downloaded source-paper PDFs recorded by
  `literature_review/download_log.csv`.
- `paper_runs/`: compact tracked ledgers, verdicts, summaries, small reproducibility CSVs, and final report figures under `paper_runs/performance_analysis/figures/`.
- `paper_runs/submission_evidence/`: frozen locks, manifests, aggregate estimates,
  multiplicity results, diagnostic summaries, and hashes of excluded reconstruction
  artifacts.
- `paper_runs/submission_evidence/strict_proxy_fidelity_audit/`: compact strict
  row-level grades and hash-pinned manifest for the 50 legacy mappings.
- `paper_runs/faithful_component_replications/`: primary strict-B ledger, pinned
  upstream hashes, aggregate attribution results, and manifests; licensed
  security-level holdings and monthly return paths remain excluded.
- `tests/upstream_snapshots/quantevolver/`: four bounded, hash-verified source
  files retained under the upstream MIT License for offline conformance; this
  is not a mutable or complete third-party repository clone.
- `docs/faithful_component_owner_review_packet.md` and the adjacent primary
  owner-review attestation: compact D07 human-review materials.
- `paper_runs/fidelity_formula_components/`: compact fidelity ledger, attribution
  estimates, summary, nearest-factor diagnostics, and manifests; licensed
  security-level holdings and monthly return paths remain excluded.
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
- `paper_runs/fidelity_formula_components/formation_holdings.csv` and
  `monthly_return_paths.csv`; their checksums remain in the tracked manifest and
  authorized inputs plus the tracked runner regenerate them.
- `paper_runs/faithful_component_replications/formation_holdings.csv` and
  `monthly_return_paths.csv`; their checksums remain in the tracked manifest and
  support the full-evidence mode of the fail-closed validator on authorized data.
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
