# M053: AlphaCrafter multi-agent quantitative trading

Status: **closed not evaluable on monthly U.S./JKP data**.

AlphaCrafter's central strategy is the output of a three-stage, stateful multi-agent workflow: LLM miners generate and refine factors, a screener selects a factor pool, and an LLM trader turns that selected evidence into daily trades. The attributable MIT repository under the authors' NJU-LINK organization contains substantive miner, screener, trader, exchange, and evaluation code. Controlled checks execute six native accounting components, including the U.S. short/cover path and the paper-stated fees.

Those components do not identify a trading signal. The release contains templates and index series, not the paper's stock/fundamental/news snapshots, point-in-time memberships, model requests and responses, selected factor pools, trader actions, orders, holdings, or return arrays. Its default launcher asks for an unregistered `gpt-5.3-codex` model and always routes the main path through A-share instructions and tools. A bounded copied-tree substitution to the shipped `gpt-5.2` entry reached four guarded API attempts but received no responses and does not reproduce the disclosed GPT/Claude/Gemini experiment.

The current repository still points only to the audited head and has no tags or releases. Its complete 13-commit history and public forks yielded no attributable result artifacts. The sole divergent fork's result-shaped JSON files are synthetic display-parser fixtures without experiment lineage. Consequently, none of v2's 304 numeric result units or 14 empirical panels has been regenerated.

JKP can standardize the U.S. universe and benchmark, but it cannot infer the missing generated factors or stateful trader decisions. Substituting a generic technical or JKP factor would replace the paper's defining method, while the older `alphacrafter_full_stack_multifactor` study is explicitly a researcher motif proxy. No return path is fabricated. This closure does not show that AlphaCrafter's reported results are false; it records that the released code stops before the causal factor/action artifacts needed for independent evaluation.
