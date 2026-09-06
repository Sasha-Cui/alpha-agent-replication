# M066: AlphaAgentEvo in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native AlphaAgentEvo Qwen3 policy, GRPO trajectory, or offspring pool.

The reconstruction preserves 150 persistent policy updates, four factor-evaluation tool calls per step, group-relative advantages, validity/quality/diversity/novelty/tool-efficiency rewards, clipped operator and feature preferences, and a diverse 20-alpha elite pool. The selected alpha was `pair_mean__ret_12_1__z_score` with hierarchical reward 0.847; operator calls were {'pair_product': 439, 'pair_difference': 93, 'pair_mean': 58, 'identity': 10}, and mean reward components were {'validity': 1.0, 'quality': 0.5368095238095238, 'diversity': 0.33226502238243305, 'novelty': 0.49541666666666667, 'tool_efficiency': 0.5208333333333334}. All policy learning occurred on the 120 pre-common training months.

At 10 bp one-way costs, the 305-month path has CAGR 3.99%, annualized Sharpe 0.281, and maximum drawdown -62.98%. Mean monthly traded notional is 1.072, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is 0.08% annually (HAC t=0.036, p=0.9711, 95% interval [-4.37%, 4.54%]).

This result answers how one transparent AlphaAgentEvo-inspired agentic-RL policy transfers to the common monthly U.S. universe. It does not reproduce AlphaEvo500, native prompts, Qwen3 weights, Verl/GRPO trajectories, evaluator tools, generated factors, checkpoints, five-day execution, or paper empirical claims.
