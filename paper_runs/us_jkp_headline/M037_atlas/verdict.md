# M037: ATLAS common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy because the defining Adaptive-OPRO policy and its trajectories are unreleased**.

The original v5 paper makes the headline method clear. Market, news, and fundamental analysts supply daily summaries to a Central Trading Agent that submits executable orders through StockSim. Every five trading days, Adaptive-OPRO converts realized ROI to `clip(50 + 250*ROI, 0, 100)` and an optimizer LLM rewrites the agent's static instruction for the next window. Original-paper pages for the architecture, optimizer state/update, score, three-regime setup, order interface, and results were text-checked and visually inspected.

StockSim is genuine same-author precursor code, not ATLAS. After removing only an obsolete `asyncio` backport, 43/43 modules import and four component checks pass. A deleted historical XOM chart even preserves 20 dated orders and a 43-point, +5.01564% portfolio path over the paper window. It has no ATLAS, prompt, optimizer, model, seed, or paper-run identifier and matches none of the published ATLAS XOM means.

The current official repository remains unchanged and releases no ATLAS central-agent logic, baseline prompt, Adaptive-OPRO implementation/meta-prompt, optimizer requests, prompt-edit history, paper config, seeds, aligned data, actions, orders, fills, trajectories, or result arrays. The five-day score alone cannot determine a prompt update or an order. Running StockSim or using a technical baseline would test another strategy.

No monthly return is assigned. This is neither evidence that ATLAS's claims are false nor a below-JKP result. It is an attribution failure: 0/1,784 empirical numeric units and 0/5 empirical panels are regenerated, while the runnable StockSim and XOM evidence remain explicitly credited as precursor components.
