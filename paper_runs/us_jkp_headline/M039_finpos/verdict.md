# M039: FinPos common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy because the position-generating policy is unreleased and underidentified**.

The original v2 paper defines a daily carried-position task and a three-module FinPos system: domain agents filter price/news/filings into hierarchical memory; a Direction Agent selects sell/hold/buy; a Quantity/Risk Agent changes integer exposure with a CVaR reference; and future 1/7/30-day price differences generate a training-only reflection reward. Original pages for the position task, architecture, dual decision, future reward, and result tables were text-checked and visually inspected.

Eleven printed mechanics execute and pass controlled tests, including position/log-return accounting, the reward, risk metrics, and two deliberate refusals of unstated CR-percent and CVaR-to-shares conversions. These equations never map observable test-time state to direction and quantity. The future price score is explicitly training-only and would be lookahead if traded. The 95% CVaR has conflicting tail/sign semantics and no units-to-shares mapping.

No author implementation, model snapshot, valid complete prompts, memory state, immutable provider inputs, actions, quantities, fills, account path, or result generator is public. Current repository/title searches and a recently updated coauthor homepage still expose no FinPos release. Six of twelve printed JSON examples are invalid and two require an unreleased suffix.

No monthly return is assigned. The 11/11 component checks are genuine specification progress but not a strategy result. FinPos is neither classified as false nor below JKP; its positive results remain unresolved, with 0/294 current-v2 and 0/225 v1 cells regenerated author-natively.
