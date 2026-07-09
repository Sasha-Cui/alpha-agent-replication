# RD-Agent-Quant JKP benchmark status

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/RD-Agent`

Scope constraint: valid return data may come only from read-only JKP/return-data-assembly inputs. I did not run RD-Agent's qlib data pipeline or any China/CN setup.

RD-Agent is a real public framework for automated factor/model proposal and qlib execution. The repository contains qlib scenario code, prompts, templates, and documentation for factor-model co-optimization, but the cloned checkout does not ship dated USA/JKP candidate return streams, generated factor formulas tied to JKP columns, or model predictions that can be converted into monthly candidate returns.

Current status: no direct USA/JKP benchmark run. To advance this paper under the current data rule, we would need a custom adapter that makes RD-Agent propose factors over the JKP USA schema, writes the proposed formulas/predictions, and converts them to top-N monthly long-short returns using `scripts/build_jkp_long_short_returns.py` and `scripts/evaluate_candidate_returns_jkp.py`.
