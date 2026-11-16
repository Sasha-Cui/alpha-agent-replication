# Paired experiment and confirmation-data blueprint

The prior economic/search launch gate remains closed. This version measures whether an unselected replicate-average statistic improves temporal precision at the original per-run exposure, and checks relevant existing-data metadata without reading new holdout outcomes.

## Exact estimand

The candidate is the expected monthly performance of a search algorithm over a fixed prespecified seed distribution, evaluated on one shared market path. Average each run's saved monthly performance across seeds and then form the arm difference. This differs from pooling factor libraries and running a union strategy. It also differs from compounding a newly investable seed-averaged portfolio; no such portfolio, rebalance costs or wealth path is claimed here. Calendar uncertainty conditions on three recorded LLM runs and does not fully establish future-generation uncertainty.

## Pairing contract

Both engines must use the same initial factor bank, operator language, available information, train/validation partitions, evaluator, selection/portfolio policy, execution and costs. Match evaluator perturbations and randomized data splits with explicitly named common random-number streams when their semantics genuinely match. Use independent proposal streams where the engines differ. Assigning the same integer label to two unrelated stochastic engines does not create common random numbers.

Fix seeds and arm counts before outcomes. Report all failed/invalid/duplicate proposals against the opportunity budget. The primary control is an adaptive grammar/evolution engine, not merely uniform random search. Pairing choices cannot be chosen for a favorable return or SE. More seeds measure algorithm variation on the same market; they do not multiply independent financial history. No leverage reduction, cash blend or active-exposure shrinkage is used to satisfy the 2-pp margin.

## Confirmation-data acceptance checklist

- Identify exact provider revision, license, raw fields, universe/membership rule, calendar and corporate-action conventions. A fixed legacy US50 universe supports only that limited universe; it is not a point-in-time representative equity sample.
- Before reading candidate holdout outcomes, document which data and periods have already influenced this study, earlier paper/source audits and model/strategy choices. Existing filenames, different countries, or a renamed period are insufficient proof of non-use.
- Pin model weights/snapshot and the model-information boundary. An outcome-unseen local file does not guarantee that an LLM lacks the historical information. A prospective fixed-policy test offers a stronger boundary.
- A forward test starts only after the actual executable policy, input workflow and selection choices have been frozen with hashes and a timestamp. A Markdown draft is not that policy seal; no already elapsed day will be retrospectively called forward observation.
- Freeze collector validation, raw immutable receipts, publication/availability timestamps, formation/execution lag and missing/delisting rules. Use the same evaluator for both arms and independent account checks.
- Freeze a sufficient evaluation horizon and the temporal/seed uncertainty method. The +2-pp/year decision boundary, 99% interval and 80% planning power remain unchanged. Neither a short prospective pilot nor extra seeds automatically supplies that precision.

## Continuation rule

Only a separately bound executable design with defensible joint seed/time precision and accepted validation inputs can open a new search launch. A smaller exploratory SE is not itself permission to launch or a new alpha result. If these conditions cannot be satisfied, the economic-alpha question remains unresolved; switching to prediction accuracy or research productivity would be a separate explicit research question.
