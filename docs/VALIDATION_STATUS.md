# Validation Status

Validated on 2026-08-09 against the canonical ICAIF source, compiled PDF, and
tracked aggregate evidence on Bouchet.

## Canonical artifacts

| Artifact | SHA-256 |
| --- | --- |
| `docs/paper/icaif2026_submission.tex` | `656bc442f93ea74de92434883dbdacc3711328ce12ceaa625c5503813dd14d6c` |
| `output/pdf/icaif2026_submission.pdf` | `311cd1f799a70fe0208a7e3f7ce410c54bd9af9a749fe9605bec94dab6af8b35` |

The PDF is seven US-Letter pages, unencrypted, anonymous, and built with the
vendored ACM `acmart` 2.19 production template. All fonts are embedded and the
rendered pages were visually checked for clipping, overlaps, and unreadable
labels.

## Passing checks

- Repository test suite: 55 passed.
- Fresh-clone source/PDF artifact audit: 62 of 62 checks passed without a
  LaTeX build log.
- Explicit release-build audit: 71 of 71 checks passed, including the supplied
  LaTeX log.
- Major-revision semantic and locked-evidence validator: passed.
- Stable ICAIF validation entry point: passed.
- Collaborator index: deterministic 50-row rebuild with no tracked diff.
- Publication boundary: no tracked Parquet files, third-party repository
  clones, scratch paths, alternate output PDFs, or files larger than 100 MiB.

### Fresh-clone gate

The default package check validates only tracked files and writes its temporary
handoff rebuild outside the checkout. It does not search for
`docs/paper/icaif2026_submission.log` or any other ignored auxiliary file.
It requires `pdfinfo`, `pdftotext`, and `pdffonts` from Poppler. On
Bouchet:

```bash
module load poppler/25.07.0-GCC-13.3.0
python scripts/validate_submission_package.py
```

The format portion reports `ICAIF ARTIFACT AUDIT PASSED: 62 checks`. Passing
means the vendored template hashes, source settings, anonymity, page geometry,
rendered text, font embedding, and canonical prebuilt PDF pass. It makes no
claim about a build log that is absent from a fresh clone.

### Release-build gate

To audit compilation as well, load TeX Live and Poppler, rebuild, and provide
the ignored log explicitly:

```bash
module load texlive/20240312-GCC-13.3.0
module load poppler/25.07.0-GCC-13.3.0
python scripts/build_icaif2026_submission_assets.py
python scripts/build_icaif2026_submission.py
python scripts/validate_icaif_submission.py \
  --pdf output/pdf/icaif2026_submission.pdf \
  --log docs/paper/icaif2026_submission.log \
  --require-build-log
```

This mode reports `ICAIF RELEASE-BUILD AUDIT PASSED: 71 checks`. An explicit
missing log, a log from the wrong layout/anonymity mode, an overfull box,
undefined citations or references, or a fatal TeX marker fails validation.
Logs remain ignored because they contain machine-specific paths and are not
canonical publication artifacts.

## Interpretation and operational boundaries

Passing validation means that the source, PDF, aggregate evidence, generated
handoff, and stated claims are internally consistent. It does not convert the
50 mappings into native-agent replications, make the retrospective mapping
exercise confirmatory, or establish a causal pretraining mechanism.

The legacy `docs/paper/alpha_agent_replication.tex`, owner-review packet, and
their historical build script document an earlier evidence-audit manuscript.
They are not current submission artifacts. The canonical submission is the
single PDF and matching TeX source listed above.

Before upload, the submitting author must still confirm the CMT author list,
submission-limit, dual-submission, ORCID, review-service, and presentation
requirements described in `docs/paper/ICAIF2026_COMPLIANCE.md`.
