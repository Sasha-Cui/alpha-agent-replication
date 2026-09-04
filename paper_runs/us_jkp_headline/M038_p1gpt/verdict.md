# M038: P1GPT common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy because the daily multi-agent decision policy is unreleased**.

The original paper's headline object is a five-layer workflow: multimodal inputs are planned into specialized technical, fundamental, semiconductor, news, search, revenue, trend, and recommendation tasks; an integration layer fuses their reports; and a decision layer emits daily Buy/Sell/Hold recommendations. The native backtest enters at the same-day close, exits on Sell, holds otherwise, claims no leverage/costs, and runs AAPL, GOOGL, and TSLA from February-September 2025. Original pages for the architecture, simulation, execution rule, result table, and an AAPL report were text-checked and visually inspected.

The attributable public repository is only a working web client. Its 22 Python files compile, but it calls a private `main-llm` service and database and ships no paper agents, daily prompt, fusion logic, model configuration, requests/responses, backtest, or outputs. All official branch heads remain unchanged as of 2026-09-04.

The author-rendered plots are unusually informative: 498 daily position values verify 11/12 P1GPT table cells under ordinary rounding. They remain generated outputs for three stocks and one interval, not an executable policy that can be transferred to 305 JKP months. They also expose serious problems: the March 24 report discusses iPhone Air events from September 2025, author positions reach seven units despite a no-leverage claim, and no single Sharpe/GOOGL-capital convention recovers all displayed cells.

No monthly return is assigned. P1GPT is not classified as false or below JKP; its common-task policy is unavailable. The old thematic JKP score, author positions, incomplete client, baselines, and static reports are all rejected as substitutes.
