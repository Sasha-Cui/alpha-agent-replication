# M020: MASS common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy because the released internal state does not identify decisions or signals**.

MASS simulates 16 investor types with 32 agents each, assigns each agent a 20-stock candidate pool and five selections, aggregates their decisions using a learned investor-type distribution and alpha=0.5, optimizes the distribution by simulated annealing, and holds weekly top-20% signals with a stated 0.1% round-trip cost.

The release includes a real 263-date distribution snapshot and a 242-date SSE50-like input/label panel. But it includes no individual decisions, candidate-pool assignments, aggregated signals, U.S. panels, portfolio code, baselines, holdings, returns, timing/cost logs, or result arrays. This is not merely an inference: executing the native `InvestmentAnalyzer` with the same released distribution and two valid decision assignments changes ten stock signals. The distribution therefore cannot reconstruct the missing strategy.

The active source also conflicts with the paper’s optimizer settings and pool-update protocol and cannot run without source/data repairs. Labels are not actions, and arbitrary JKP values supplied as 512 agent decisions would invent the central simulation. No substitute receives a return.

MASS reports positive results, but 0 of 766 numeric result cells and 0 of five empirical figures is reproduced. The claims remain unresolved—not demonstrated false and not shown merely to underperform JKP.

M020 is closed without a return. The twenty-milestone release gate runs before M021 is activated.
