# TradeTrap benchmark status

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/TradeTrap`

TradeTrap ships substantial public code plus data artifacts: price JSON files, agent position logs, and `agent_viewer` equity-curve JSON files. I converted the shipped viewer `total_asset` paths into monthly candidate returns using `scripts/prepare_tradetrap_candidate_returns.py`.

Artifacts:

- `tradetrap_viewer_return_paths_summary.csv`: 18 extracted candidate equity paths.
- `candidate_returns_*.csv`: one monthly return file per extracted viewer path.
- `results_deepseek_base_official_ff/ff_official_benchmark_metrics.csv`: official Kenneth French FF3 and FF5+Mom evaluator output for the shipped DeepSeek base path.

Result: the shipped viewer curves cover only one calendar month, October 2025. The official FF evaluator has one overlapping factor month and returns `insufficient_overlap` for both FF3 and FF5Mom. This is a real code/data artifact, but it is not a serious alpha result under the requested standard because the sample is far too short for Sharpe, HAC alpha, or factor-spanning inference.
