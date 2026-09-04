# M036: Profit Mirage / FactFin common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy because the final evolved strategy and the procedure that identifies it are unreleased**.

This paper contains two distinct objects. FinLake/FinLeak-Bench is a leakage/memorization question-answer benchmark and is outside the trading-strategy comparison. FactFin is in scope: RAG structures price, factor, and news state; an LLM generates executable buy/sell/hold code; MCTS evolves the code; and a counterfactual simulator penalizes prediction consistency and confidence invariance while rewarding input dependence. The headline policy is the resulting program C*, not the benchmark or a displayed baseline.

The paper discloses a mutable GPT-4o alias at temperature 0.7, top-5 `text-embedding-3-large` retrieval, MCTS depth 10 and UCB c=0.5. It does not release the program language/runtime, complete prompts, RAG corpus/index/results, MCTS state/action grammar, initial or evolved code, evaluator, perturbation generators, objective weights, convergence rule, seeds, original price/news rows, portfolio sizing, fill timing, costs, orders, or NAV. The paper's 14-file source bundle contains manuscript assets only. A 2026-09-04 author-surface recheck still finds one homepage repository whose Profit Mirage entry links only to arXiv.

The simplified prompt and Algorithm 1 cannot fill these gaps without researcher choices. Current Yahoo buy-and-hold data are a baseline diagnostic and match 0/6 displayed cells, not FactFin. Printed metrics and curves cannot be inverted into strategies or trades.

No monthly return is assigned. This is neither evidence that FactFin's positive claims are false nor a result below JKP; the system is unresolved/non-evaluable. The prior audit preserves 0/525 displayed cells and 0/120 direct FactFin cells regenerated, plus material benchmark-name, scorer, split, MDD-sign, Sharpe-headline, and causal-identification issues.
