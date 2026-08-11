# Validation Status

Validated on 2026-08-11 against the canonical ICAIF source, compiled PDF, and
tracked aggregate evidence on Bouchet.

## Canonical artifacts

| Artifact | SHA-256 |
| --- | --- |
| `docs/paper/icaif2026_submission.tex` | `70ad767203d3e118fc5ff2b764e4d9e02fd4bccfc03b9736d7a640d02fe88bda` |
| `output/pdf/icaif2026_submission.pdf` | `235d672d82736a6ddca1c259fe09790c202901473c0904c5d8543e721973a853` |

The PDF is six US-Letter pages, unencrypted, anonymous, and built with the
vendored ACM `acmart` 2.19 production template. All fonts are embedded and the
rendered pages were visually checked for clipping, overlaps, and unreadable
labels.

## Passing checks

- Repository test suite: 234 passed (one third-party deprecation warning).
- Fresh-clone source/PDF artifact audit: 62 of 62 checks passed without a
  LaTeX build log.
- Explicit release-build audit: 71 of 71 checks passed, including the supplied
  LaTeX log.
- Major-revision semantic and locked-evidence validator: passed.
- Primary faithful-component gate: 3/3 strict grade B (100%), with source hashes,
  exact evaluator mechanics, full holdings reconstruction, benchmark summaries,
  and within-benchmark Holm families verified.
- Exact-source offline conformance: 1,296 synthetic score comparisons and 105
  eligible portfolio timestamps match; portfolio-return discrepancy is zero.
- D07 owner review: complete, with all 3/3 rows approved by Sasha Cui on
  2026-08-11; it remains separately represented from the technical 100% result.
- QuantEvolver full-paper audit: 75/75 numeric table cells and 31/31 additional
  numeric result claims are enumerated, with zero native paper-result paths;
  38/67 source mechanism dimensions match or have meaningful analogues. The
  full-paper strict gate fails as intended and does not alter the separate 3/3
  grade-B component result.
- Alpha-R1 full-paper audit: 124/124 table cells and all 528 visible heatmap
  cells are enumerated, with zero native result paths; 0/70 implementation
  dimensions match because both the paper-era and current official repository
  trees contain only a README. The paper's full-implementation availability
  statement conflicts with the repository's Coming Soon roadmap. Its local M0
  motif proxy remains secondary and receives no replication credit; the
  full-paper strict gate fails as intended.
- Alpha-Jungle full-paper audit: all 64 official AAAI result cells, 956 arXiv-v1
  cells, and 1,312 arXiv-v3 cells are enumerated, with zero native paper-result
  paths. Three of six disclosed formulas execute only as monthly JKP U.S.
  adaptations and receive component rather than paper-result credit. The
  unaffiliated community implementation fails import and test collection and
  receives no native credit; version-lineage and AR/AER conflicts are recorded.
- FAMA full-paper audit: all 65 numeric table results and 38 visible result
  markers are enumerated, with zero native paper-result paths. The paper claims
  38 initial factors but Appendix B lists 71; its printed correlation equation,
  factor-acceptance algorithm, data split, prompt, and portfolio specification
  do not determine one exact implementation. The existing local mapping remains
  a momentum/trend motif only and receives no native FAMA-result credit.
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
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python scripts/validate_submission_package.py
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
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python scripts/build_icaif2026_submission_assets.py
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python scripts/build_icaif2026_submission.py
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python scripts/validate_icaif_submission.py \
  --pdf output/pdf/icaif2026_submission.pdf \
  --log docs/paper/icaif2026_submission.log \
  --bbl docs/paper/icaif2026_submission.bbl \
  --require-build-log
```

This mode reports `ICAIF RELEASE-BUILD AUDIT PASSED: 71 checks`. An explicit
missing log, a log from the wrong layout/anonymity mode, an overfull box,
undefined citations or references, or a fatal TeX marker fails validation.
An explicitly supplied compiled bibliography must contain at least 10 entries.
Logs and compiled bibliography files remain ignored because they are generated
build residue rather than canonical publication artifacts.

## Interpretation and operational boundaries

Passing validation means that the source, PDF, aggregate evidence, generated
handoff, and stated claims are internally consistent. It does not convert the
50 mappings into native-agent replications, make the retrospective mapping
exercise confirmatory, or establish a causal pretraining mechanism.
The primary formula census covers all three evaluator-valid seeds in the pinned
QuantEvolver release and passes 3/3 strict grade B (100%). The percentage applies
to disclosed evaluator components under cadence, universe, and horizon
adaptations, not the source discovery system or published portfolio.
The paper-level audit confirms the distinction: it reproduces 0/75 paper table
results and 0/31 non-table numeric result claims because the private data,
checkpoint, exact experiment configuration, logs, factors, baselines, fusion
arrays, seeds, and costs are not released. Passing public-framework tests and
38/67 architecture matches or analogues are component evidence only.
The exact-source synthetic conformance gate passes without empirical outcomes;
Sasha Cui's separate three-row D07 owner attestation is complete.
The older 12-formula bundle is a mixed-fidelity diagnostic outside that
denominator. The
separate GuruAgents experiment is a current-endpoint public-prompt replay with
archived deterministic tool observations, not an independent reconstruction of
the source data, original model snapshot, or native system. The 50 legacy
mappings remain construction diagnostics only.

The legacy `docs/paper/alpha_agent_replication.tex` and
its historical build script document an earlier evidence-audit manuscript.
They are not current submission artifacts. The canonical submission is the
single PDF and matching TeX source listed above.

Before upload, the submitting author must still confirm the CMT author list,
submission-limit, dual-submission, ORCID, review-service, and presentation
requirements described in `docs/paper/ICAIF2026_COMPLIANCE.md`.
