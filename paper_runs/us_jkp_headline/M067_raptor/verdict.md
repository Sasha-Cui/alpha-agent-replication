# M067: RAPTOR reasoned portfolio rebalancing

Status: **closed not evaluable on monthly U.S./JKP data**.

RAPTOR's native strategy converts multimodal specialist/research/risk/execution-agent decisions into Black-Litterman views and a constrained long-only portfolio. The public release has exceptionally strong output evidence: all 166 daily portfolio snapshots are available; 18 of 42 scalar paper results verify directly from author output; 29 verify when current-benchmark and paper-internal routes are included; three raster curves correspond; and the native metric postprocessor executes exactly.

That evidence verifies a 2025 output path, not the policy that generated it. Paper-time prices, benchmark, Finnhub, Reddit, SimFin, Perplexity, full blackboard traces, model calls, seeds, and most per-date security decisions are absent. Only January 1 has 503 decision files, with long-only rewriting and some action/rationale contradictions. The candidate backtest cannot start without `testing/stock_prices.csv`, and the paper/runners conflict on cadence, lookback, risk aversion, tau, universe, views, and costs.

JKP cannot infer the missing agent views. Feeding generic characteristics into the released Black-Litterman component would replace RAPTOR's multi-agent reasoning; replaying the 2025 snapshots or Day-0 decisions across 1999–2024 would fabricate persistence and actions.

No common-benchmark path is fabricated. This closure preserves RAPTOR's unusually strong output/raster verification while distinguishing it from an end-to-end or transferable strategy replication. Reopen for complete point-in-time inputs and action/blackboard lineage or a causal released policy.
