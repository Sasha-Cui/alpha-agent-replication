# MASS paper-level conformance audit

Overall verdict: **not reproduced**. The public release contains real SSE50-like
input/label data and a dated learned agent-distribution snapshot, but it contains
none of the agent decisions, signals, baseline outputs, portfolios, backtests,
timing logs, or API accounting needed to reproduce Tables 1--4.

## Primary sources

- Official paper: https://arxiv.org/pdf/2505.10278 (SHA-256 `c31e68b722b6c4d33dd69833b48a34de8fc29ec4171498f320307ede554e6135`).
- Public source: https://github.com/gta0804/MASS, commit `68edcaae9e6ac099d28eed90513219495b0852b7`.

## What the release genuinely establishes

- The base, label, and feature panels contain 242 trading dates during 2023 and
  exactly 50 stocks per date (59 distinct identifiers across constituent changes).
- `ih_dist` is a real native internal-state artifact. After checking its pinned
  hash and every pickle opcode before a restricted primitive-only decode, it has
  263 dates from 20221202 through
  20231229, 16 investor-type masks per date, positive weights
  with invariant raw sum 16, and 216 changed
  transitions. This is optimizer state, not an action, signal, or return path.
- The released model name, 16-by-32 agent scale, SSE50 candidate count, score
  weight for SSE50/CSI 300, cooling rate, and optimizer lookback agree with the
  corresponding paper declarations.

## Why no published result is reproduced

- The audit enumerates 285 Table 1--4 cells: 277 numeric claims and
  eight Table 2 EMCL markers. All 277 numeric claims are unverifiable from the
  release. No cached individual decisions are present, so the distribution state
  cannot be converted into the paper's signals.
- Only an SSE50-like panel is released. CSI 300, ChiNext 100, CSI A500, and the
  paper's full multimodal inputs are absent. The two news files are two-byte CRLF
  placeholders and invalid Parquet.
- The entry point cannot run as released: it has three empty `ROOT_PATH` constants,
  two literal paths missing f-string interpolation, and references absent pool,
  label, news, price-feature, and result paths.
- The paper specifies simulated-annealing initial temperature 40 and 100 iterations;
  the active source constructs defaults 0.5 and 20. The paper uses alpha=0.2 for
  ChiNext, while the source always uses the 0.5 default.
- The paper's main candidate pools are static per agent and treats daily updating as
  a separate MASS(DU) ablation. The active source resamples with replacement every
  day. It also generates one strategy per agent/day rather than one per type/day.
- Random modality, candidate-pool, and optimizer draws have no run-level seed. The
  paper does not identify which released 1/5/10-day label horizon produced Table 1,
  nor the risk-free rate behind Table 4 Sharpe ratios.
- Table 4/Figure 2 specify weekly top-20% portfolios and 0.1% round-trip costs, but
  the release has no portfolio/backtest/cost implementation. Table 3 has no timing,
  request, token, or fee logs.

Run `scripts/audit_mass_paper.py` to regenerate this package. Use `--strict` when
a CI failure is desired until the native decisions, complete inputs, experiment
configs/seeds, and result paths are released and reproduce at least one paper row.
