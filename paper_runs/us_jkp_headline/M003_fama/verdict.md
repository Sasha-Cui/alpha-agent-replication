# M003: FAMA common-task verdict

Status: **closed—not evaluable on the monthly U.S./JKP task without designing a new factor miner**.

FAMA's headline is not an individual momentum/value formula. It is the complete neural-symbolic factor-mining loop: clustering a starting factor pool, retrieving and recombining experience, prompting an LLM with executable function definitions, evaluating generated factors, and retaining improvements.

The released record contains no author implementation, runtime operator definitions, final mined expression, search trace, checkpoint, paper-data snapshot or portfolio rule. The sole recovered prompt leaves `{function_definition}` unresolved. The paper also gives materially different executable procedures: 38 initial factors versus 71 Appendix identifiers; a correlation equation missing its denominator square root; and an algorithm that adds every generated factor outside the improvement condition even though the narrative says otherwise.

A new LLM search built around invented operators, one selected interpretation and JKP would be a new factor-mining system. Evaluating the old local FAMA motif would be worse: its value, profitability, size and portfolio rules are researcher supplied and were already graded as motif-only. Alpha101 factors are inputs/baselines, not FAMA's claimed output. None is used to manufacture a common-task return.

Accordingly M003 records no return rather than a zero or failed strategy. This says the public materials do not determine a defensible common-task strategy; it does not establish that the paper's private 38.4% annual-return claim is false. Existing prompt, formula and inconsistency evidence remains preserved separately. M004 is now active.
