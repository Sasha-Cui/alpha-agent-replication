# Reporting addendum to the locked confirmatory protocol

**Date:** 2 August 2026

**Status:** Post-run reporting clarification; not part of the frozen analysis lock

The immutable protocol used by the completed runs is
`docs/confirmatory_analysis_protocol.md`, SHA-256
`0a0515cedbb211362356d4a3a28693696ae18edfd89d4298266588ea21fa8285`.
This addendum does not change an estimator, candidate, market, calendar, cost,
seed, threshold, or reported primary output. It makes three implementation
details explicit where the locked protocol used broader or imprecise prose.

1. The implemented resampler is a paired circular moving-block bootstrap with
   fixed block lengths of 3, 6, or 12 months. It draws the complete
   executable-candidate net-return and factor matrix jointly. Turnover is not a
   separately resampled state because realized turnover has already entered
   each candidate's cost-adjusted net return.
2. Complete-path failures have no alpha or studentized statistic. They enter
   Holm, Benjamini--Hochberg, and Benjamini--Yekutieli accounting as `p=1` in
   the 62-candidate family. Paired max-absolute-t and global maximum-t
   procedures use the 27 executable paths only, with failed paths fixed as
   non-rejections rather than imputed returns.
3. The implemented materiality flag is inclusive: a candidate is confirmed
   when its simultaneous annualized-alpha lower bound is greater than or equal
   to 2 percentage points. The locked protocol's word “above” is clarified as
   “at or above,” consistent with the frozen code, tests, output field, and
   threshold value.

During submission QA, we also observed that the originally generated
descriptive country and leave-one-country-out files allowed the executable set
in each panel to induce a different calendar. A separately labeled post-hoc
diagnostic therefore fixes the 27 primary executable candidates and their
293-month August 2000--December 2024 calendar before rerunning country-local
and country-exclusion regressions. It also re-estimates pooled G7 alpha on the
281-month U.S. comparison calendar. The diagnostic script and manifest are
`scripts/run_fixed_calendar_diagnostics.py` and
`paper_runs/submission_evidence/fixed_calendar_diagnostics/manifest.json`.
These diagnostics do not redefine the primary pooled analysis or its
multiplicity family.
