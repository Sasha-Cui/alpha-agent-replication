# Validation Status

Validated on 2026-08-09 after reconciling Bouchet `main` with `origin/main`.

## Passing checks

- Repository test suite: 48 passed.
- Collaborator index: deterministic rebuild; no diff from tracked CSV/manifest.
- Handoff Markdown: all local link targets resolve.
- Canonical TeX SHA-256:
  `7f88792a69c3be2e78306daaa4e457dacaed583c18c29b3710de8aa574ab9d03`.
- Canonical PDF SHA-256:
  `183443caa9f773e7aca10141c2c057b0efb98cda8a28b46fa1b1f041f98e76a4`.
- PDF structure: eight letter-sized pages, unencrypted, with all listed fonts
  embedded.

## Open submission blocker

The exact user-designated canonical PDF predates the stricter ACM 2.19 build
and validation infrastructure merged from `origin/main`. It passes 65 of the
71 current format checks. The six reported failures are:

1. DOI or ISBN metadata is not explicitly blank.
2. The source changes `\headheight`.
3. The source changes `\pagestyle`.
4. PDF metadata identifies acmart 2.12 rather than the vendored acmart 2.19.
5. Figure content introduces embedded Type 3 fonts.
6. The available LaTeX log contains an overfull-box warning.

The locked-evidence validator also stops at its first wording mismatch:

```text
required disclosure absent: released seed yields a testable monthly adaptation
```

This reflects divergence between the exact designated evidence-audit paper and
the newer validator expectations, not a hash or dataframe integrity failure.
The canonical paper was intentionally not overwritten during handoff cleanup.

## Required before submission

1. Decide whether the next canonical manuscript remains the public-artifact
   evidence audit or adopts the later matched benchmark-ladder framing.
2. Apply the chosen changes to one TeX source only; keep attribution boundaries
   and the 0/1/12/37 provenance counts explicit.
3. Build with the vendored ACM 2.19 template and explicitly blank DOI/ISBN
   metadata without template-altering page-style commands.
4. Regenerate figures with Type 1/TrueType text and remove overfull boxes.
5. Run both validators until they pass:

   ```bash
   python scripts/validate_icaif2026_format.py \
     --pdf output/pdf/icaif2026_submission.pdf
   python scripts/validate_icaif_major_revision.py \
     --root . --pdf output/pdf/icaif2026_submission.pdf
   ```

6. Render all eight pages and visually check clipping, overlaps, contrast,
   citations, tables, and figure labels.
7. Replace the canonical PDF only after the source, PDF, generated artifacts,
   validators, and documented SHA-256 hashes agree. Do not retain alternate
   compiled paper versions in Git.
