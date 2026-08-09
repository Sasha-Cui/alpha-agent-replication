# AlphaPROBE run notes

Status: adapter blocked on comparable data contract.

Official repo cloned at external_repos/AlphaPROBE.

Findings:

- The repo is real code, not a placeholder.
- run_adaptive_combination.py can produce a daily ret_s.npy return stream after evaluating an expression file.
- The repo does not ship expression files or candidate return artifacts.
- The default data path is external Qlib CN/US data, and no Qlib data was found under the project or home paths on Bouchet.
- A direct run would not satisfy the FF3/FF5Mom requirement unless we either obtain the exact candidate expression set and map returns to the same monthly US top-1000 universe, or reimplement AlphaPROBE retrieved/generated factors against the external same-universe return panel.

Next action:

Build an adapter that takes AlphaPROBE or AlphaGen expressions, evaluates them on the external same-universe top-1,000 stock panel, forms monthly candidate returns, and then calls scripts/evaluate_candidate_returns.py.
