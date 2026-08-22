# QuantEvolver paper-level conformance audit

Overall verdict: **substantial public framework, but the paper is not
reproduced**. The implementation is genuine; the experiment is not public.

## Primary-source pins

- Official paper: https://arxiv.org/pdf/2605.15412v1 (arXiv:2605.15412v1, submitted 2026-05-14T20:54:40Z; PDF
  SHA-256 `55f119b0cdf47f10f72b9fed0d89a46228fc9c2b1d12c5e7f10b072d04bd0f7b`; TeX archive SHA-256 `e040fa429db69e648bacab920fcb2e5e8dcd6d6916745b6d6d8deab35d84cb46`).
- Official source: https://github.com/QuantLLM/QuantEvolver, commit `4eb0e78842138ada5334349585b114ad923564e8`
  (2026-05-15T04:38:26+08:00), about 16.2 minutes before arXiv submission. The first
  commit `6372a607f68f2717af2fe99601f5ae228721495a` contains only `README.md`; the second adds the
  complete 67-file release. The repository's 13-page PDF has SHA-256
  `9e72f2c188882b8f3cc8a67ac724021521c522d8f40627485a5921613548c905` and is not byte-identical to the 14-page arXiv PDF.

## What genuinely passes

- All 55 released package Python files
  parse in a clean Python 3.12 environment and all 52 package modules import.
  All three upstream tests pass. The actual released seed validator accepts 3/4
  example seeds, the example configuration builds nine seed-window tasks, and
  all three valid DSL expressions execute twice with identical values on
  deterministic synthetic OHLCV data.
- The released RFT bridge resolves against a compatibility-selected Verl 0.5.0:
  the nine tasks produce 16 training and four validation prompt rows, the
  `NoThinkRLHFDataset` subclass resolves, and the merged config selects GRPO and
  a vLLM rollout. This is not a training run or an exact historical environment:
  QuantEvolver pins neither Verl nor vLLM, vLLM is absent, and no GPU, model,
  rollout, reward loop, or optimizer executes. The 119-line resolved package
  freeze is tracked and hash-checked.
- 38/67 audited mechanism dimensions are direct
  matches or substantial analogues. The release includes structured scenario
  refinement, oracle-style seed generation, DSL validation/realization, seed
  scoring and AST deduplication, seed-window task construction, single-asset and
  cross-sectional evaluators, grouped Verl/GRPO training wiring, exact/family
  diversity shaping, behavioral archives, reward clipping, and factor saving.
- The separate disclosed-component gate still passes **3/3 grade B**. It
  preserves the three released example expressions, DSL/evaluator semantics,
  and return definition while explicitly adapting bars to monthly JKP data and
  the universe to top-1000 U.S. equities. It is useful component evidence.

## Why the paper is not replicated

- The two numeric tables contain **75 result cells**: 60 overall results and 15
  ablation results. **0/75** has a native released paper-result path. The paper
  also makes 31 numeric result assertions in prose/figures (including repeats
  of table values); **0/31** is reproduced from released paper artifacts.
- The README explicitly says the public repository is reusable framework code
  only and excludes private market data, trained checkpoints, experiment logs,
  and paper-specific reproduction scripts. It also omits the paper seed pool,
  task bank, prompts, model snapshots, mined factors, validation arrays, fusion
  inputs/outputs, baseline implementations, trial seeds, costs, and result
  tables. The five numeric result plot panels are vector graphics without their
  underlying arrays.
- The complete non-shallow public history has exactly two commits. Across both
  revisions, there are **0** result/log/checkpoint/data artifact paths and **0**
  occurrences of seven distinctive displayed paper-result literals outside the
  bundled paper PDF. There are no alternate official branches, tags, releases, or
  unreachable local Git objects supplying a hidden experiment path.
- The complete dated public-fork surface has four accessible forks, four branch
  refs, no tags, and one unique head. Every ref resolves exactly to the audited
  official head, adding zero unique commits and zero unique blobs. The forks
  therefore provide no missing experiment or result lineage.
- The generic examples are not paper configs: they use placeholder model and
  asset names, January 2024 example windows, one GPU, and generic thresholds.
  The paper does not identify Benchmark A's asset, Benchmark B's exchange or
  universe, or exact dates/splits for any benchmark, and it leaves many training,
  fusion, portfolio, cost, and baseline details unspecified.

## Paper and paper/source barriers

- The paper first says QuantEvolver uses `Qwen3-14B`, then says all compared
  methods use `Qwen-3.6-Plus`. No model snapshot resolves the conflict.
- The paper defines ICIR as mean IC divided by its standard deviation. The
  released cross-sectional evaluator multiplies this by `sqrt(T)`. It also
  transforms the primary RankIC into `5*RankIC + 0.02*tanh(ICIR)` before DiCo
  shaping, a transform not disclosed in the paper's reward definition.
- Benchmark A contains one asset, but the published IC and RankIC equations are
  cross-sectional correlations over assets and are undefined for `N_t=1`; no
  single-asset replacement definition is supplied.
- The headline 7.8% directional-accuracy improvement is not derivable from
  53.22% versus 52.59% (about 1.20%). The headline 109.5% best-RankIC gain is
  not derivable from 0.0586 versus 0.0337 (about 73.89%). The claimed 186.9%
  top-10 gain has no underlying values in the paper artifacts.
- The profitability arithmetic is at least display-compatible: 125.6% from
  NAV 1 implies 2.256, which rounds to the plotted/prose value 2.26.

## Honest boundary

The source is much closer to the paper's architecture than a proxy, but no
amount of local rerunning can recover withheld experiment inputs and outputs.
The 3/3 component gate must remain separate: it is an adapted component census,
not the Miner checkpoint, RFT search, three benchmarks, factor library, fusion,
or any published result. Run `scripts/audit_quantevolver_paper.py` to regenerate
this package; `--strict` intentionally fails until native paper artifacts and
all published values are actually reproduced.
