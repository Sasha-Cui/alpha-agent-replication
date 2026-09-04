# M066: AlphaAgentEvo self-evolving agentic RL

Status: **closed not evaluable on monthly U.S./JKP data**.

AlphaAgentEvo's headline strategy is the output of a learned multi-turn Qwen3 policy. The policy calls factor-generation/evaluation tools, optimizes a five-part hierarchical reward, retains alpha offspring, and supplies a cross-sectional top-10-percent portfolio. The accepted paper specifies much of this architecture but prints no final alpha formula or score.

The OpenReview record lists a supplementary ZIP and says it contains the dataset plus complete training/evaluation source. Current direct access to the immutable attachment still returns 404, while API access returns 403. This proves a supplement was listed, not that it was inspected or never existed. No paper-author repository, checkpoint, factor pool, or result package is otherwise public.

Two later Hugging Face candidates receive no native credit. Neither is author-attributable: one is a mismatched 0.6B step-50 checkpoint; the other uses Vietnam-market prompts, different splits and reward logic, exceeds the stated tool-call cap, stops at step 90, and omits the expression parser/backtest backend. The local evolved-seed JKP proxy likewise has no policy, reward, tool, factor, or result lineage.

No common return path is fabricated. None of 147 table units, 21 empirical panels, or 40 figure annotations was regenerated author-natively. JKP can evaluate a released alpha, but it cannot infer the learned policy's missing offspring. Reopen if the official supplement or attributable factor/checkpoint/action lineage becomes accessible.
