# M021: Navigating the Alpha Jungle: An LLM-Powered MCTS Framework for Formulaic Alpha Factor Mining disclosed component

Status: **completed partial monthly U.S./JKP evaluation**, not the LLM-guided Monte Carlo tree search over formulaic alpha factors.

The literal published Table 7 formula 4 volume moving-average-difference factor is evaluated from the fixed source formula `Diff(Ma(volume,20),3)/Ma(volume,60)`. Preserved: published formula tree; 20/60-period means; three-period difference; volume input. Adapted: daily China bars to monthly U.S. JKP bars; researcher portfolio; common costs and benchmark. The disclosed monthly adapter is: inputs: JKP monthly tvol in the formation-date top-1,000 U.S. universe; operators: Ma is rolling mean; Diff(x,3)=x-x.shift(3); formula tree is preserved; portfolio: researcher top-10 equal-weight long-only score portfolio; costs: common fixed cost cases with 10 bp primary; missing_returns: fixed holdings re-accounted under common zero and adverse-100 policies without reranking. This component was already mapped and evaluated before the new study, so this result is exploratory rather than newly outcome-blind.

At 10 bp one-way costs, the 305-month path has CAGR -5.24%, annualized Sharpe 0.021, and maximum drawdown -98.51%. The 185-month rolling JKP133 residual mean is 3.52% annually (HAC t=0.710, p=0.4776; descriptive 69-test bound=1.0000).

The result is performance of one disclosed formula component after explicit adaptations. It does not reproduce or claim: MCTS search; LLM prompts/responses; native model; native portfolio; paper result. It must not be used as evidence that the full paper system worked or failed.
