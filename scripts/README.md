# Research runner guide

Use [the current study guide](../docs/CURRENT_STUDY.md) to select a study before
selecting a script. The scripts directory retains historical entry points
because protocols and manifests bind their paths and contents.

## Reader checks

```bash
python scripts/check_repository_docs.py
```

This standard-library check validates current navigation and the compact
69-paper readiness snapshot. It does not call models or data services.

## Reusable package commands

The entry points declared in [pyproject.toml](../pyproject.toml) wrap
`src/alpha_evolve/`:

- `alpha-evolve-build-jkp`: construct returns from an authorized stock panel.
- `alpha-evolve-evaluate`: evaluate supplied return streams.
- `alpha-evolve-evaluate-jkp`: evaluate a JKP construction.
- `alpha-evolve-run-quantevolver`: a source-specific research entry point.

These are not shortcuts to completing the active actual-factor study. Inspect
the command's inputs, output path, and study protocol before running it.
The historical JKP construction does not replace actual FF5 + MOM + JKP132.

## Historical families

- `audit_*_paper.py`: paper/source conformance audits.
- `build_*`, `analyze_*`, and `validate_*`: artifact-specific builders,
  analyses, and gates. “Validate” does not imply universally read-only behavior.
- `run_*`, `dispatch_*`, and submission helpers: potentially expensive source,
  model, account, or scheduler work.
- `replay_*` and recovery helpers: exact case-specific replay/recovery protocols,
  not generic retry entry points.
- `run_*_python.sh`: supported environment wrappers for particular source packages.

Read the relevant [study index](../paper_runs/README.md) and frozen protocol.
Do not bulk-run these scripts, overwrite an existing run directory, or retry
a failed/uncertain request. The active study's working adapters currently live
with its private, versioned evidence; the readiness inventory does not claim
that a new portable public runner is complete.

## Development

See [development and validation scopes](../docs/DEVELOPMENT.md).
