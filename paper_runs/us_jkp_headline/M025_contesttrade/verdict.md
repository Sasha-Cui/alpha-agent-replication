# M025: ContestTrade common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy because the released entrypoint omits the central contests and portfolio**.

ContestTrade’s headline pipeline sends factor context through a token-budgeted diversity-aware Data Contest, sends research signals through a positive-Sharpe-weighted Research Contest, and trades the resulting daily A-share portfolio under T+1 and price limits.

The current repository contains useful components, including two Data Contest LightGBM models and the Research weight normalizer. But the real CLI calls only data agents, research agents, and `finalize`; it never invokes either contest, and `finalize` simply exposes all signals. The Research Contest lacks two model files and a called method. The Data Contest uses top-three sorting instead of facility-location allocation, and its reward ignores bearish ratings and clips/averages returns rather than implementing the signed paper equation.

There is no paper input panel, active portfolio, backtester, baseline/ablation runner, action/holding/return output, or run seed. A fork’s mixed manual/AI 2026 trades and the exact author raster are not the paper experiment. Completing these missing objects would be a new system, not a bounded adapter.

No monthly return is assigned. Zero of 49 table cells and 0 of 15 plotted series is independently reproduced. The positive claims remain unresolved—not demonstrated false and not shown merely to underperform JKP. M026, Chain-of-Alpha, is now active.
