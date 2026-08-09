# ICAIF 2026 Anonymous Submission Source

The submission is pinned to the ACM `acmart` 2.19 production release dated
2026-06-27. This is the latest production release available before the ICAIF
2026 deadline. The unmodified class source, generated class, bibliography
style, provenance, and checksums are in `acm_template_2_19/`.

Build from the repository root:

```sh
python scripts/build_icaif2026_submission.py
python scripts/validate_icaif2026_format.py
```

The final CMT upload is `output/pdf/icaif2026_submission.pdf`. Do not upload
an appendix, source archive, or empirical artifact: the ICAIF 2026 call accepts
only a self-contained PDF and explicitly forbids supplementary materials.

`generated_results.tex` and `icaif2026_results.tex` contain headline values generated from hash-verified frozen evidence. The included PDF figures are deterministic outputs of the repository's asset builders. Restricted row-level security data are not part of this source archive.
