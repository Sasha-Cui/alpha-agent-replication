# M054: Strat-LLM stratified strategy alignment

Status: **closed not evaluable on monthly U.S./JKP data**.

Strat-LLM is not one fixed technical rule. Its central experiment feeds price sequences, real-time news, and annual reports to an LLM, varies strategic autonomy across Free, Guided, and Strict prompts, and executes the resulting buy/hold/sell actions at the next-day open. The paper argues that the best constraint level depends on model architecture and market regime; it does not preselect one universal model/mode. Choosing the least-negative U.S. row after reading the results would be outcome-based specification selection.

The six-file source bundle contains the manuscript and figures but no implementation or data. The advertised project page still returns 404, and fresh exact repository searches for the arXiv identifier and title found no attributable release. Exact prompts, response schema, paper-time price/news/report snapshots, model calls, stock lists, broker settings, actions, holdings, and return arrays are all absent. The paper's four strategy motifs are also incomplete: only Breakout Momentum provides a 3-day-high entry clause, and even that lacks its price field, exit, sizing, and tie rules.

The prior synthetic check verifies only the stated action mapping, T+1 index shift, and cash truncation under a researcher-set zero transaction cost. It uses no paper model, input, action, or return and receives no strategy credit. Likewise, turning the isolated breakout clause or generic JKP momentum/reversal fields into a monthly portfolio would remove the paper's multi-source LLM alignment mechanism.

No return path is fabricated. None of the 190 unique displayed empirical units was regenerated. This closure does not establish that the reported returns are false; it records that the paper supplies neither a source-fixed executable strategy nor the actions needed to test its central experiment. The literal live-forward chronology is additionally contradicted by public model release dates, although a properly frozen post-hoc replay could in principle avoid look-ahead if its missing records were released.
