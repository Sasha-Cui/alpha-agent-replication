#!/usr/bin/env python3
"""Build repository- and paper-level FF5Mom metric reports from JKP-only outputs."""
from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "paper_runs" / "registry.csv"
OUT_DIR = ROOT / "paper_runs"
EXTERNAL_REPOS = ROOT / "external_repos"
FF5 = "FF5MOM_JKP"


def norm_url(value: str) -> str:
    text = (value or "").strip().lower()
    if text.endswith(".git"):
        text = text[:-4]
    return text.rstrip("/")


def repo_remote(repo: Path) -> str:
    try:
        out = subprocess.check_output(["git", "-C", str(repo), "config", "--get", "remote.origin.url"], text=True).strip()
        return out
    except Exception:
        return ""


def safe_float(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else float("nan")
    except Exception:
        return float("nan")


def boolish(value: Any) -> bool | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def beat_verdict(row: dict[str, Any]) -> str:
    if row.get("metric_status") != "computed_jkp_only":
        return "not_computable_from_approved_inputs"
    alpha = safe_float(row.get("alpha_annualized"))
    tstat = safe_float(row.get("alpha_tstat_hac"))
    appraisal = safe_float(row.get("appraisal_ratio"))
    lift = safe_float(row.get("combined_minus_old_sharpe"))
    grs_reject = boolish(row.get("grs_reject_5pct"))
    if alpha > 0 and appraisal > 0 and tstat > 1.96 and lift > 0 and grs_reject is True:
        return "yes_positive_significant_alpha_vs_ff5mom"
    if alpha < 0 and appraisal < 0 and lift > 0 and grs_reject is True:
        return "no_declared_direction_negative_alpha_inverse_signal_adds_span_value"
    if alpha > 0 and appraisal > 0 and lift > 0:
        return "no_positive_but_not_statistically_significant_vs_ff5mom"
    if lift > 0:
        return "no_span_lift_only_not_positive_significant_declared_alpha"
    return "no"


def load_registry() -> list[dict[str, str]]:
    with REGISTRY.open() as f:
        return list(csv.DictReader(f))


def load_metrics_for_run(run_id: str) -> pd.DataFrame:
    run_dir = OUT_DIR / run_id
    if not run_dir.exists():
        return pd.DataFrame()
    frames = []
    for path in sorted(run_dir.glob("**/jkp_ff_benchmark_metrics.csv")):
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if "benchmark_set" not in df.columns:
            continue
        df = df[df["benchmark_set"].eq(FF5)].copy()
        if df.empty:
            continue
        df["metric_file"] = str(path.relative_to(ROOT))
        frames.append(df)
    summary = run_dir / "quantevolver_jkp_proxy_ff_summary.csv"
    if summary.exists():
        try:
            df = pd.read_csv(summary)
            df = df[df["benchmark_set"].eq(FF5)].copy()
            if not df.empty:
                df["metric_file"] = str(summary.relative_to(ROOT))
                frames.append(df)
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["candidate_id", "benchmark_set", "metric_file"], keep="last")
    # Prefer summary file duplicates only once per candidate by keeping the last sorted metric file.
    out = out.sort_values(["candidate_id", "metric_file"]).drop_duplicates(subset=["candidate_id", "benchmark_set"], keep="last")
    return out


def row_from_metric(reg: dict[str, str], metric: pd.Series, local_repo: str, repo_url: str) -> dict[str, Any]:
    row = {
        "ref_index": reg.get("ref_index"),
        "run_id": reg.get("run_id"),
        "title": reg.get("title"),
        "local_repo": local_repo,
        "code_status": reg.get("code_status"),
        "code_url": reg.get("code_url"),
        "repo_url": repo_url,
        "execution_state": reg.get("execution_state"),
        "registry_verdict": reg.get("verdict"),
        "metric_status": "computed_jkp_only",
        "candidate_id": metric.get("candidate_id"),
        "benchmark_set": metric.get("benchmark_set"),
        "metric_file": metric.get("metric_file"),
    }
    for col in [
        "candidate_standalone_oos_sharpe",
        "alpha_annualized",
        "alpha_tstat_hac",
        "appraisal_ratio",
        "information_ratio",
        "combined_minus_old_sharpe",
        "old_benchmark_set_annualized_sharpe",
        "new_combined_annualized_sharpe",
        "grs_f",
        "grs_p_value",
        "grs_reject_5pct",
        "grs_reject_1pct",
        "grs_exact_valid",
        "grs_df1",
        "grs_df2",
        "grs_active_ir_annualized",
        "r_squared",
        "overlap_start",
        "overlap_end",
        "n_overlap_months",
    ]:
        row[col] = metric.get(col, np.nan)
    row["beats_ff5mom_at_5pct"] = beat_verdict(row).startswith("yes_")
    row["beat_ff5mom_verdict"] = beat_verdict(row)
    return row


def row_without_metric(reg: dict[str, str], local_repo: str, repo_url: str) -> dict[str, Any]:
    reason = reg.get("verdict") or reg.get("execution_state") or "missing_metrics"
    row = {
        "ref_index": reg.get("ref_index"),
        "run_id": reg.get("run_id"),
        "title": reg.get("title"),
        "local_repo": local_repo,
        "code_status": reg.get("code_status"),
        "code_url": reg.get("code_url"),
        "repo_url": repo_url,
        "execution_state": reg.get("execution_state"),
        "registry_verdict": reg.get("verdict"),
        "metric_status": f"not_computable_from_approved_inputs:{reason}",
        "candidate_id": "",
        "benchmark_set": FF5,
        "metric_file": "",
        "candidate_standalone_oos_sharpe": np.nan,
        "alpha_annualized": np.nan,
        "alpha_tstat_hac": np.nan,
        "appraisal_ratio": np.nan,
        "information_ratio": np.nan,
        "combined_minus_old_sharpe": np.nan,
        "old_benchmark_set_annualized_sharpe": np.nan,
        "new_combined_annualized_sharpe": np.nan,
        "grs_f": np.nan,
        "grs_p_value": np.nan,
        "grs_reject_5pct": np.nan,
        "grs_reject_1pct": np.nan,
        "grs_exact_valid": np.nan,
        "grs_df1": np.nan,
        "grs_df2": np.nan,
        "grs_active_ir_annualized": np.nan,
        "r_squared": np.nan,
        "overlap_start": "",
        "overlap_end": "",
        "n_overlap_months": np.nan,
        "beats_ff5mom_at_5pct": False,
        "beat_ff5mom_verdict": "not_computable_from_approved_inputs",
    }
    return row


def select_repo_summary(group: pd.DataFrame) -> pd.Series:
    computed = group[group["metric_status"].eq("computed_jkp_only")].copy()
    if computed.empty:
        return group.iloc[0]
    computed["alpha_tstat_sort"] = pd.to_numeric(computed["alpha_tstat_hac"], errors="coerce").fillna(-1e9)
    computed["alpha_sort"] = pd.to_numeric(computed["alpha_annualized"], errors="coerce").fillna(-1e9)
    computed["lift_sort"] = pd.to_numeric(computed["combined_minus_old_sharpe"], errors="coerce").fillna(-1e9)
    return computed.sort_values(["alpha_tstat_sort", "alpha_sort", "lift_sort"], ascending=False).iloc[0]


def fmt(value: Any, digits: int = 3) -> str:
    x = safe_float(value)
    if not math.isfinite(x):
        return "NA"
    return f"{x:.{digits}f}"


def main() -> None:
    registry = load_registry()
    local_by_url: dict[str, tuple[str, str]] = {}
    if EXTERNAL_REPOS.exists():
        for repo in sorted(p for p in EXTERNAL_REPOS.iterdir() if p.is_dir()):
            remote = repo_remote(repo)
            local_by_url[norm_url(remote)] = (repo.name, remote)

    candidate_rows = []
    paper_rows = []
    for reg in registry:
        url_key = norm_url(reg.get("code_url", ""))
        local_repo, repo_url = local_by_url.get(url_key, ("", ""))
        metrics = load_metrics_for_run(reg["run_id"])
        if metrics.empty:
            row = row_without_metric(reg, local_repo, repo_url)
            paper_rows.append(row)
            if local_repo or reg.get("code_url", ""):
                candidate_rows.append(row)
        else:
            rows = [row_from_metric(reg, metric, local_repo, repo_url) for _, metric in metrics.iterrows()]
            paper_rows.extend(rows)
            if local_repo or reg.get("code_url", ""):
                candidate_rows.extend(rows)

    candidate_df = pd.DataFrame(candidate_rows)
    paper_df = pd.DataFrame(paper_rows)
    repo_df = candidate_df[candidate_df["local_repo"].astype(str).ne("")].copy()
    selected_rows = []
    for _, group in repo_df.groupby("local_repo", sort=True):
        selected_rows.append(select_repo_summary(group).to_dict())
    repo_summary = pd.DataFrame(selected_rows)

    candidate_df.to_csv(OUT_DIR / "repository_candidate_ff5mom_metrics.csv", index=False)
    repo_summary.to_csv(OUT_DIR / "repository_ff5mom_metrics_summary.csv", index=False)
    paper_df.to_csv(OUT_DIR / "paper_ff5mom_metrics_summary.csv", index=False)

    lines = [
        "# Repository FF5Mom Metrics Summary",
        "",
        "Scope: valid numeric metrics are computed only from approved JKP/USA inputs. Repositories without a valid approved-input candidate return stream are shown as `NA`, not backfilled from paper-shipped returns, yfinance, China data, or official French factors.",
        "",
        "Beat rule: `beats_ff5mom_at_5pct` requires positive annualized alpha, positive appraisal/information ratio, HAC alpha t-stat > 1.96, positive FF5Mom span Sharpe lift, and GRS rejection at 5%. Negative-alpha candidates may still have span value if inverted, but they do not beat FF5Mom in the declared direction.",
        "",
        "| repo | ref | metric status | selected candidate | Sharpe | alpha t | appraisal/IR | GRS F | GRS p | span lift | beats FF5Mom? | verdict |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, r in repo_summary.sort_values(["local_repo"]).iterrows():
        lines.append(
            "| {repo} | {ref} | {status} | {cand} | {sharpe} | {tstat} | {ir} | {grsf} | {grsp} | {lift} | {beat} | {verdict} |".format(
                repo=r.get("local_repo", ""),
                ref=r.get("ref_index", ""),
                status=str(r.get("metric_status", "")).replace("|", "/"),
                cand=(str(r.get("candidate_id", "")) or "NA").replace("|", "/"),
                sharpe=fmt(r.get("candidate_standalone_oos_sharpe")),
                tstat=fmt(r.get("alpha_tstat_hac")),
                ir=fmt(r.get("appraisal_ratio")),
                grsf=fmt(r.get("grs_f")),
                grsp=fmt(r.get("grs_p_value"), 4),
                lift=fmt(r.get("combined_minus_old_sharpe")),
                beat="yes" if boolish(r.get("beats_ff5mom_at_5pct")) else "no",
                verdict=str(r.get("beat_ff5mom_verdict", "")).replace("|", "/"),
            )
        )
    lines.extend([
        "",
        "Files:",
        "",
        "- `repository_ff5mom_metrics_summary.csv`: one selected row per cloned repository.",
        "- `repository_candidate_ff5mom_metrics.csv`: all FF5Mom candidate rows for cloned/code repositories.",
        "- `paper_ff5mom_metrics_summary.csv`: all registry paper rows, including no-code rows with NA metrics.",
        "",
    ])
    (OUT_DIR / "REPOSITORY_FF5MOM_METRICS.md").write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "repository_rows": int(len(repo_summary)),
        "repository_candidate_rows": int(len(candidate_df)),
        "paper_metric_rows": int(len(paper_df)),
        "computed_jkp_only_repository_rows": int(repo_summary["metric_status"].eq("computed_jkp_only").sum()) if len(repo_summary) else 0,
        "repositories_beating_ff5mom_at_5pct": int(repo_summary["beats_ff5mom_at_5pct"].map(lambda x: boolish(x) is True).sum()) if len(repo_summary) else 0,
        "output_files": [
            "paper_runs/repository_ff5mom_metrics_summary.csv",
            "paper_runs/repository_candidate_ff5mom_metrics.csv",
            "paper_runs/paper_ff5mom_metrics_summary.csv",
            "paper_runs/REPOSITORY_FF5MOM_METRICS.md",
        ],
    }
    (OUT_DIR / "repository_metrics_report_status.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
