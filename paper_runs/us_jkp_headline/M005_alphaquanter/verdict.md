# M005: AlphaQuanter common-task verdict

Status: **closed—not evaluable on the monthly U.S./JKP task without creating a new policy**.

The headline method is a tool-augmented LLM trading policy trained by reinforcement learning, not its reward labels or Buy-and-Hold baseline. The release meaningfully preserves 2,615 dated prompt/reward rows and the multi-horizon reward formula. Those labels are generated from future returns; using them as monthly actions would be direct lookahead, not a causal AlphaQuanter strategy.

No 2025 paper-test prompts or actions are released. The source calls an absent VERL trainer, uses placeholder collected-data paths, and provides no complete multimodal inputs, checkpoint, three-seed paths, ratings or cost logs. Paper/source differences in inference temperature, Sharpe, rolling windows and seed selection leave multiple possible policies. Training a supervised label model or filling the PPO scaffold would make the learned strategy ours.

Therefore M005 records no common-task return. This preserves the real prompt/reward evidence without upgrading it into a policy result, and it does not establish that the paper's private results are false. M006 is now active.
