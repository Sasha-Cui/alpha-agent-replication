# Alpha-R1 paper-level conformance audit

Overall verdict: **not reproduced; the official repository is a placeholder**.
This is a release failure, not a failed attempt to run public Alpha-R1 code:
there is no public Alpha-R1 code to run.

## Primary-source pins

- Official paper: https://arxiv.org/pdf/2512.23515v1 (arXiv:2512.23515v1, submitted 2025-12-29T14:50:23Z; PDF
  SHA-256 `3b88ec9d3231b097d3633de6d9c0e9840873c99497c29df85e33b20b110d00de`; TeX archive SHA-256 `013e3201472be17a97c37a832e77fe1edf1b122d0cc6eeea1294c3cab8cf7e01`).
- Official repository: https://github.com/FinStep-AI/Alpha-R1, current commit `61feaa359bd57761f5ac58f75af46ddfed2d2d7b`
  (2025-12-30T19:40:48+08:00). Its complete three-commit history has one tracked file,
  `README.md`.
- The only pre-submission revision is `09b2f921fe2344fc370beafc26aa0d44a6913a5b`
  (2025-12-26T18:06:58+08:00), 76.72 hours before submission. It contains a
  two-line title README and nothing else. The expanded README arrived 20.79
  hours after submission and explicitly says the code and models are being
  organized; inference code and model weights remain marked **Coming Soon**.
- All **nine** accessible public forks are exhausted as of 2026-08-14. Each
  exposes one `main` branch: eight are exact at the official head and one is
  the one-commit-behind README-update parent. Across nine refs and two unique
  official-history heads, the forks add zero commits, blobs, tags,
  implementation files, weights, data, or result artifacts.

## Complete numeric-result boundary

- Tables 1--3 contain **124 numeric result cells**: 88 main, 24 ablation, and
  12 gating-comparison cells. The six source PNG heatmaps contain another
  **528 visible numeric cells** (11 TopN values by 8 holding periods by 3
  metrics by 2 universes). Thus the directly displayed table/heatmap
  denominator is **652**, not merely the headline table values. **0/652** has a
  native public reproduction path.
- The two NAV panels ship only raster curves. None of the eight numeric result
  figure panels includes its underlying array. The paper makes 27 other numeric
  result assertions in prose (including table repeats); **0/27** is reproduced.
- The heatmap transcription is checked against all six Table 1 values at the
  declared default `TopN=10`, `H=5`: 13.0/1.618/6.8 for CSI300 and
  42.5/4.031/9.3 for CSI1000 agree with 12.99/1.62/6.76 and
  42.49/4.03/9.25 at heatmap precision. The claimed 49% semantic-description
  Sharpe decline is also arithmetically compatible (48.765%). These internal
  checks establish transcription consistency, not experimental reproduction.

## What is missing

- No Python or other implementation, dependency file, runner, config, prompt,
  checkpoint, market/news data, 82- or 40-factor list, factor formula, fitted
  beta, baseline, ablation, seed, training log, selection, order, fill, return,
  NAV, or result table is present. **0/70** audited mechanism
  dimensions match an implementation; three are merely narrative claims in the
  README and the rest are absent.
- The paper omits enough operational detail that a clean-room implementation
  would still require material choices: exact model revisions/prompts, data
  vendors and point-in-time membership, factor conventions, reward/judge and
  structural-penalty definitions, GRPO hyperparameters, baseline settings,
  metric formulas, aggregation order, and run seeds.
- The paper says the full implementation and resources are available at the
  repository. The repository says they are coming soon. That is a direct
  paper/source release-availability conflict.

## Honest boundary

The paper specification is useful and its displayed results are substantially
internally coherent, so a future official release could make this tractable.
Today, however, rebuilding an Alpha101-based Chinese-equity strategy from the
paper would be an independent reimplementation, not replication of the trained
Alpha-R1 system. The local `code_alpha_r1_reasoning_screen` candidate is an
M0 favorable narrative translation on unrelated JKP data; it gets zero native
mechanism or paper-result credit. Run `scripts/audit_alpha_r1_paper.py` to
regenerate this package. `--strict` intentionally fails until the official
model, inputs, runnable experiment, and all published values are reproduced.
