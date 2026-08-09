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

- Repository test suite: 48 passed.
- ACM format audit: 71 of 71 checks passed.
- Major-revision semantic and locked-evidence validator: passed.
- Stable ICAIF validation entry point: passed.
- Collaborator index: deterministic 50-row rebuild with no tracked diff.
- Publication boundary: no tracked Parquet files, third-party repository
  clones, scratch paths, alternate output PDFs, or files larger than 100 MiB.

Run the complete non-mutating package check from the repository root after
loading TeX Live/Poppler on Bouchet:

```bash
python scripts/validate_submission_package.py
```

For a paper-only check:

```bash
python scripts/validate_icaif_submission.py \
  --pdf output/pdf/icaif2026_submission.pdf
```

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
