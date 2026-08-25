# Automate Strategy Finding paper-level conformance audit

Overall verdict: **not reproduced**. The pinned public repository supports a partial
factor-analysis and prompt-selection component, not the integrated portfolio result.

## Primary sources

- Official paper: https://aclanthology.org/2025.findings-emnlp.1005.pdf (SHA-256 `6585377002a3b049a6bfadef3152a74adfe12d68ff5c48cccb8c76de4fd1b540`).
- Public source: https://github.com/kouzhizhuo/Automate-Strategy-Finding-with-LLM-in-Quant-investment, commit `8b50203faf50d0b561cf5ffee4d63dcdc4551884`.
- A bounded GitHub census on 2026-08-14 covers all 24 accessible
  forks and 25 fork branch refs. Every head is an exact commit in the
  already-audited official history, so the forks contribute no additional commit,
  result/log path, or paper-result lineage.

## What the public artifacts establish

- The 37-row seed workbook exposes factor names, formulas, signed ICs, and IRs.
- Seven individual-factor analysis workbooks contain IC summaries, five quantile
  cumulative-return paths, and turnover over 2022-09-30 through 2022-12-30.
- The public prompt files and logs show a GPT-4o Assistant-based factor-comparison
  workflow. This is component evidence, not the paper's final strategy.
- Recomputing Table 2 with the inferable mean-absolute-IC rule matches
  3/10 displayed cells at four-decimal precision.
- The seed workbook corroborates all 12/12 signed IC cells
  printed for Table 3's selected alphas at four-decimal precision. This is
  author-source component evidence, not an integrated portfolio replay.
- The complete public Git surface was reviewed: 7
  commits on 2 branches, 39 unique historical paths,
  zero tags/releases, and zero unreachable objects.
- All 25 branch refs across the 24 public forks resolve to those same
  official-history commits. See `public_fork_ref_inventory.csv`.

## What is missing or inconsistent

- No shipped workbook contains the integrated Jan 2023--Jan 2024 portfolio path,
  Table 4 schema, or the reported 53.173% final return; all 40 Table 4
  metric cells are therefore unverifiable, not zero-filled or counted as failures.
- Table 3's 12 learned weights and combined IC are absent. The public AutoGPT
  candidate directory contains only seven individual-factor workbooks and no
  weighted 12-alpha portfolio, prediction, or return path.
- The paper describes a 10-node DNN; `train_dnn.m` sets one hidden node and its
  required `result/profit.csv` and `result/alpha/` inputs are absent.
- The paper's top-k/drop-n portfolio rule (k=13, n=5) is not implemented in the
  released Python or MATLAB files.
- The later `New-project` branch adds a generic "Grail" scaffold, but it does not
  recover the missing experiment. It defaults to GPT-2 rather than GPT-4o; its
  three risk-profile copies merely rescale caller-provided confidence rather than
  implementing the paper's market-conditioned CSA/RPA; and its default MLP is
  100-64-10 rather than |A|-10-1. It accepts caller-supplied tensors, is not wired
  to any released workbook, and ships no command, frozen input, checkpoint, native
  output, portfolio path, or reported metric. Static syntax validity is not result credit.
- A bounded Bouchet probe imported the reconstructed package and exercised the simple
  confidence scaler. A one-row optimizer call failed with division by zero because
  it creates zero batches. Default GPT-2 construction could not be adjudicated: the
  centrally supplied tokenizer dependency terminated with SIGILL before model
  construction, so that environment crash is explicitly not attributed to author code.
- The paper itself reports SSE50 return as -13.22% in Table 4 but -11.73% in prose,
  and full-model ablation Sharpe as 1.94 in Table 7 but 1.73 in prose.
- The factor runner requires unbundled RQData access. The public agent file also
  contained a usable credential literal at the pinned historical commit. Current
  `main` redacts it, and that redaction is the only later main-branch change. This
  audit never prints, validates, or uses the historical value.

Run `scripts/audit_automate_strategy_paper.py` to regenerate this package. Use
`--strict` when a CI failure is desired until a native integrated return path exists.
