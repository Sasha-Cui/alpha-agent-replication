# MASS paper-level conformance audit

Overall verdict: **not reproduced**. The public release contains real SSE50-like
input/label data and a dated learned agent-distribution snapshot, but it contains
none of the agent decisions, signals, baseline outputs, portfolios, backtests,
timing logs, or API accounting needed to reproduce final Tables 1--2 and 4--8.

## Primary sources

- Official paper: https://arxiv.org/pdf/2505.10278 (SHA-256 `c31e68b722b6c4d33dd69833b48a34de8fc29ec4171498f320307ede554e6135`).
- Public source: https://github.com/gta0804/MASS, commit `68edcaae9e6ac099d28eed90513219495b0852b7`.
- Earlier arXiv v1: SHA-256 `19a1845c9f199a532143957ef205c68843078a5290bb647ecb47db35d2ee20bd`.
- ICLR 2026 submission: https://openreview.net/forum?id=NNpE9iiPNR. Its 4open.science archive at
  https://anonymous.4open.science/r/MASS-AC96 was expired when checked on 2026-08-13; the paper's
  author-provided backup survives at https://github.com/anonymous3728/MASS_anonoymous, commit
  `67f80e88c6af3124d6821d8a1682c5a787cf45bb`.
- Final OpenReview PDF: SHA-256 `92697642e0f68afb3679a47ed32be46e705fbe3e670a78b2930a691d1425d385`, 26 pages,
  rejected by ICLR 2026. It adds GPT-OSS-120B, FactorVAE/HireVAE, 1024/1536-agent
  scaling, full Q1-2025 baselines, and Nasdaq-100/S&P-500 results beyond arXiv v2.

## What the release genuinely establishes

- The base, label, and feature panels contain 242 trading dates during 2023 and
  exactly 50 stocks per date (59 distinct identifiers across constituent changes).
- `ih_dist` is a real native internal-state artifact. After checking its pinned
  hash and every pickle opcode before a restricted primitive-only decode, it has
  263 dates from 20221202 through
  20231229, 16 investor-type masks per date, positive weights
  with invariant raw sum 16, and 216 changed
  transitions. This is optimizer state, not an action, signal, or return path.
- The entire named-release history has 13 reachable commits, one root, no tags,
  38 files at HEAD, and 58 unique historical paths. Recovered deleted files are
  an abandoned DTML/private-data precursor and cleaning utilities, not MASS
  decisions or results. The five ignored output directories have no reachable
  objects, and `git fsck --no-reflogs --unreachable` is empty.
- The anonymous backup has 39 files. Its only extra path is an empty `.README`;
  every shared non-README blob is identical to the named release. Its README says
  the full dataset will be released after review, so it does not add the missing
  pools, decisions, signals, portfolios, or results.
- The released model name, 16-by-32 agent scale, SSE50 candidate count, score
  weight for SSE50/CSI 300, cooling rate, and optimizer lookback agree with the
  corresponding paper declarations.

## Why no published result is reproduced

- The audit enumerates 774 final-paper table cells: 766 numeric
  claims and eight Table 2 EMCL markers across Tables 1--2 and 4--8 (Table 3 is
  descriptive stock metadata, separately inventoried without replication credit).
  It also inventories empirical Figures 2--6; none is reproduced. Figure 5 has only
  a partial upstream `ih_dist` state. All 766 numeric claims are unverifiable from
  the release. No cached individual decisions are present, so the distribution
  state cannot be converted into the paper's signals.
- This is now demonstrated constructively through the released native
  `InvestmentAnalyzer`: two valid 16-type x 32-agent decision assignments reuse
  the identical first dated distribution, candidate-pool size 20, five selections,
  and alpha=0.5, yet change 10
  stock signals (selected signals swap between 0.5 and 0.0). Therefore the missing
  decision tensor is not inferable from `ih_dist`.
- Only an SSE50-like panel is released. CSI 300, ChiNext 100, CSI A500, and the
  paper's full multimodal inputs are absent. The final revision's Nasdaq-100 and
  S&P-500 Qlib/Yahoo panels are also absent. The two news files are two-byte CRLF
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
  nor the risk-free rate behind Table 7 Sharpe ratios.
- Table 7/Figure 2 specify weekly top-20% portfolios and 0.1% round-trip costs, but
  the release has no portfolio/backtest/cost implementation. Table 6 has no timing,
  request, token, or fee logs.
- `InvestmentAnalyzer` is genuine native signal-aggregation source, and the audit
  executes it for the non-identifiability proof. This is source-path evidence only:
  neither official release contains a dated signal output or a published-result path.

Run `scripts/audit_mass_paper.py` to regenerate this package. Use `--strict` when
a CI failure is desired until the native decisions, complete inputs, experiment
configs/seeds, and result paths are released and reproduce at least one paper row.
