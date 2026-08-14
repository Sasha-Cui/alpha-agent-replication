# AlphaSchema paper and author-release audit

This audit pins arXiv `2607.26642v1`, its complete 23-file source package,
and the 32-file repository at `1206a094`. The manuscript directly links
`JingyangYi/AlphaSchema`, and the owner is first author Jingyang Yi, so the
provenance is direct rather than inferred. The source rebuilds to the same
18-page length. All 18 official and all 18 rebuilt pages were visually checked;
no unreadable, clipped, overlapping, or missing page content was found.

The release is a real implementation artifact. In an isolated Python 3.10.8
environment it installs, compiles, exposes its CLI, passes all 9 author tests,
and completes the 3-round/48-plan deterministic demo. The search release contains
schema sampling, novelty selection, a LightGBM reward ensemble, exploitation,
mutation, prompt-driven code realization and repair, static/prefix leakage checks,
reward computation, resumable records, and reports. The literal appendix factor
also executes for periods 20 and 100 on a controlled 25-stock synthetic panel,
produces two finite factor outputs, passes the native leakage check, and receives
a finite reward. These are meaningful implementation-conformance results.

They do not reproduce the paper's experiments. The default launcher fails at the
missing `data/stock_bars` path. No CSI300/CSI500 market snapshots, point-in-time
memberships, fundamental schema/data, five-run histories, model calls, exported
120/150-factor pools, baseline implementations, CSRankNorm/LightGBM pool combiner,
Qlib Top50/Drop5 portfolio engine, holdings/returns, or empirical result arrays and
generators are released. The repository also declares no license.

The complete non-shallow public history has only two commits. The second changes
README documentation and adds a method diagram; all implementation and schema
blobs are unchanged. Across both revisions, the only JSON payloads are the search
configuration and five schema definitions. No result/log/checkpoint/data path,
factor pool, prediction, holding, return, or paper-result array is present.

A dated census covers all four accessible public forks and five branch refs,
which collapse to two unique heads. One head is official-history reachable. The
sole divergent head has two unaffiliated post-paper commits touching ten paths:
timeout/retry hardening plus generated `egg-info` package metadata. It adds no
market data, search history, factor pool, prediction, portfolio, metric, table,
figure, or other paper-result artifact and receives zero paper-result credit.

Several release details diverge from the manuscript. The paper's main target is
`Ref(close,-6)/Ref(close,-1)-1`, whereas the backend uses
`close.shift(-5)/close-1`. The paper states 140 price-volume components
(40/40/50/3/7), while the release contains 167 (54/43/59/3/8). The paper models
qualities as a set, but the release keeps tuple order in the plan key, so quality
permutations can become distinct plans. The manuscript says mutation candidates
are reward-model ranked before selection and defines an exponential exploration
share; the release accepts round-robin top-parent mutations before prediction and
uses fixed observation-threshold quotas.

The strict paper-level result is therefore **0/212 published numeric table units
and 0/9 empirical panels regenerated**. Rebuilding the PDF, passing author tests,
running the mock demo, and executing the appendix factor on synthetic data receive
no paper-result credit. This is currently a substantial implementation release,
not a true reproduction of AlphaSchema's reported predictive or portfolio results.
