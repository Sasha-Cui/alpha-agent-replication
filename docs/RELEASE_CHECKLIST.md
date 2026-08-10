# Release Checklist

Use this checklist for each public software or evidence release. Preparing these
files does not itself create a release; the maintainer must review, commit, tag,
and publish it.

## Evidence freeze

- [ ] Choose a semantic version and move reviewed entries from `Unreleased` in
  `CHANGELOG.md`.
- [ ] Freeze mappings, input identities, sample dates, costs, factor definitions,
  and inference settings in the analysis lock and run manifests.
- [ ] Confirm restricted inputs remain outside Git and verify no tracked file is
  larger than 100 MiB.
- [ ] Record SHA-256 hashes for every external input and regenerated compact
  output; investigate differences from the preceding release.
- [ ] Obtain independent review for changed mappings and label exploratory work
  separately from confirmatory evidence.

## Environment and validation

- [ ] Regenerate `requirements-lock.txt` from `pyproject.toml` on the oldest
  supported Python version and review every dependency change.
- [ ] Install the lock into a clean Python 3.9 and 3.12 environment using
  `--require-hashes`.
- [ ] Run Ruff, the complete test suite, and
  `scripts/validate_submission_package.py` from a clean checkout.
- [ ] Rebuild the paper assets and canonical PDF with the documented TeX/Poppler
  toolchain; review the PDF visually and update recorded source/PDF hashes.
- [ ] Confirm CI succeeds for the exact release commit.

## Publication

- [ ] Update `CITATION.cff`, version metadata, README validation counts, and the
  data/artifact guide.
- [ ] Require review of the release commit through repository branch protection.
- [ ] Create a signed annotated `vX.Y.Z` tag from that reviewed commit; never
  move or reuse a published tag.
- [ ] Publish a GitHub release containing the changelog entry, canonical PDF,
  validation summary, and artifact hashes.
- [ ] Archive the release in a DOI-granting repository when archival citation is
  required, then add the DOI without rewriting the released evidence.
