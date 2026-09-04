#!/usr/bin/env python3
"""Build the final 69-paper U.S./JKP headline-strategy synthesis."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd


TERMINAL_STATUSES = {
    "completed_adapted",
    "completed_partial",
    "closed_not_evaluable",
}
EVALUATED_STATUSES = {"completed_adapted", "completed_partial"}
SUMMARY_COLUMNS = [
    "milestone_id",
    "canonical_work_id",
    "title",
    "system_ids",
    "status",
    "common_evidence_class",
    "common_jkp_evaluated",
    "original_system_end_to_end_reproduced",
    "prior_evidence_route",
    "primary_cost_bps_one_way",
    "full_months",
    "full_cagr",
    "full_annualized_sharpe",
    "full_maximum_drawdown",
    "average_traded_notional",
    "jkp_excess_measure",
    "jkp_excess_annualized",
    "jkp_excess_t_hac",
    "jkp_excess_p_two_sided",
    "jkp_excess_ci_low_annualized",
    "jkp_excess_ci_high_annualized",
    "holm_rank_among_evaluable",
    "holm_family_size",
    "holm_adjusted_p",
    "holm_reject_5pct",
    "recipe_path",
    "implementation_path",
    "run_manifest_path",
    "monthly_returns_path",
    "metrics_path",
    "verdict_path",
    "evaluated_scope",
    "closure_reason",
]
FAMILY_COLUMNS = [
    "rank",
    "milestone_id",
    "title",
    "raw_p_two_sided",
    "holm_multiplier",
    "holm_critical_value_5pct",
    "holm_adjusted_p",
    "holm_reject_5pct",
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def csv_bytes(rows: list[dict[str, Any]], columns: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def primary_metric(path: Path) -> dict[str, Any]:
    frame = pd.read_csv(path)
    primary = frame.loc[frame["primary"].astype(str).str.lower().eq("true")]
    if len(primary) != 1:
        raise ValueError(f"expected exactly one primary row in {path}, found {len(primary)}")
    row = primary.iloc[0]
    alpha_schema = "jkp_alpha_annualized" in frame.columns
    prefix = "jkp_alpha" if alpha_schema else "jkp_residual"
    mean_column = f"{prefix}_annualized" if alpha_schema else f"{prefix}_mean_annualized"
    mean = float(row[mean_column])
    se = float(row[f"{prefix}_se_annualized"])
    ci_low_column = f"{prefix}_ci_low_annualized"
    ci_high_column = f"{prefix}_ci_high_annualized"
    return {
        "primary_cost_bps_one_way": float(row["cost_bps_one_way"]),
        "full_months": int(row["full_months"]),
        "full_cagr": float(row["full_cagr"]),
        "full_annualized_sharpe": float(row["full_annualized_sharpe"]),
        "full_maximum_drawdown": float(row["full_maximum_drawdown"]),
        "average_traded_notional": float(row["average_traded_notional"]),
        "jkp_excess_measure": "rolling_jkp_alpha" if alpha_schema else "rolling_jkp_residual_mean",
        "jkp_excess_annualized": mean,
        "jkp_excess_t_hac": float(row[f"{prefix}_t_hac"]),
        "jkp_excess_p_two_sided": float(row[f"{prefix}_p_two_sided"]),
        "jkp_excess_ci_low_annualized": (
            float(row[ci_low_column]) if ci_low_column in frame.columns else mean - 1.959963984540054 * se
        ),
        "jkp_excess_ci_high_annualized": (
            float(row[ci_high_column]) if ci_high_column in frame.columns else mean + 1.959963984540054 * se
        ),
    }


def holm_rows(evaluated: list[dict[str, Any]], family_size: int) -> list[dict[str, Any]]:
    """Apply Holm across the declared 69-paper family.

    Non-evaluable papers consume family slots but retain missing performance; they
    are not assigned synthetic returns or p-values in the public table.
    """
    ordered = sorted(evaluated, key=lambda row: (row["jkp_excess_p_two_sided"], row["milestone_id"]))
    adjusted_so_far = 0.0
    still_rejecting = True
    result = []
    for rank, row in enumerate(ordered, start=1):
        multiplier = family_size - rank + 1
        raw = float(row["jkp_excess_p_two_sided"])
        adjusted_so_far = max(adjusted_so_far, min(1.0, multiplier * raw))
        critical = 0.05 / multiplier
        reject = bool(still_rejecting and raw <= critical)
        if not reject:
            still_rejecting = False
        result.append(
            {
                "rank": rank,
                "milestone_id": row["milestone_id"],
                "title": row["title"],
                "raw_p_two_sided": raw,
                "holm_multiplier": multiplier,
                "holm_critical_value_5pct": critical,
                "holm_adjusted_p": adjusted_so_far,
                "holm_reject_5pct": reject,
            }
        )
    return result


def fmt_pct(value: Any) -> str:
    if value == "" or value is None:
        return "—"
    return f"{100 * float(value):.2f}%"


def fmt_num(value: Any, digits: int = 3) -> str:
    if value == "" or value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def markdown_summary(rows: list[dict[str, Any]], family: list[dict[str, Any]]) -> bytes:
    evaluated = [row for row in rows if row["common_jkp_evaluated"]]
    counts = {
        "adapted": sum(row["status"] == "completed_adapted" for row in rows),
        "partial": sum(row["status"] == "completed_partial" for row in rows),
        "unavailable": sum(row["status"] == "closed_not_evaluable" for row in rows),
        "positive_cagr": sum(row["full_cagr"] > 0 for row in evaluated),
        "positive_excess": sum(row["jkp_excess_annualized"] > 0 for row in evaluated),
        "raw_significant": sum(row["jkp_excess_p_two_sided"] < 0.05 for row in evaluated),
        "holm_significant": sum(row["holm_reject_5pct"] for row in evaluated),
    }
    lookup = {row["milestone_id"]: row for row in rows}
    lines = [
        "# Final U.S./JKP headline-strategy synthesis",
        "",
        "## Outcome",
        "",
        f"All {len(rows)} source-defined paper milestones are closed. The common study executed "
        f"{len(evaluated)} monthly U.S.-stock strategy paths: {counts['adapted']} headline adaptation "
        f"and {counts['partial']} central partial adaptations. The remaining {counts['unavailable']} "
        "papers are closed as not evaluable under the common contract; their performance is missing, "
        "not zero.",
        "",
        "No full original paper system was reproduced end to end by this common-data study. That is a "
        "stricter and different statement from saying that no paper evidence was checked: prior audits "
        "did verify some disclosed formulas, software components, author outputs, and individual result "
        "cells. Those checks are preserved in the paper dossiers but are not relabelled as executable "
        "monthly U.S./JKP strategies.",
        "",
        "## What the empirical results do and do not say",
        "",
        f"At the fixed 10 bp one-way cost, {counts['positive_cagr']} of {len(evaluated)} evaluated "
        f"adaptations have positive full-sample CAGR and {counts['positive_excess']} have positive "
        "annualized return after the rolling JKP reconstruction. None has a raw two-sided HAC "
        f"p-value below 5%, and none survives the declared 69-paper Holm family correction "
        f"({counts['holm_significant']} rejections).",
        "",
        "The A-versus-B interpretation is therefore conditional. For the 17 evaluated cases, the "
        "result is B-like only in the limited sense that a source-anchored adaptation or central "
        "component was actually traded and did not establish distinct performance against the common "
        "JKP benchmark. Because the universe, frequency, inputs, portfolio adapter, and often part of "
        "the original system changed, this does not show that the paper's native claim is false. For "
        "the 52 non-evaluable cases, neither A nor B is supported: the public evidence did not define "
        "a defensible transferable monthly U.S.-stock policy, so the original empirical claim was not "
        "tested here.",
        "",
        "This is a retrospective transfer study, not a pristine holdout. Recipes were frozen before "
        "their own JKP result was inspected, but earlier project work had already inspected U.S. "
        "outcomes. Results should be read as auditable comparison evidence, not as a new discovery "
        "claim.",
        "",
        "## Evaluated common-benchmark paths",
        "",
        "| ID | Evidence | CAGR | Sharpe | Max DD | JKP excess/yr | HAC t | raw p | Holm p |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in family:
        row = lookup[item["milestone_id"]]
        lines.append(
            f"| {row['milestone_id']} | {row['common_evidence_class']} | "
            f"{fmt_pct(row['full_cagr'])} | {fmt_num(row['full_annualized_sharpe'])} | "
            f"{fmt_pct(row['full_maximum_drawdown'])} | {fmt_pct(row['jkp_excess_annualized'])} | "
            f"{fmt_num(row['jkp_excess_t_hac'])} | {fmt_num(row['jkp_excess_p_two_sided'])} | "
            f"{fmt_num(row['holm_adjusted_p'])} |"
        )
    lines.extend(
        [
            "",
            "The JKP excess column is M001's rolling JKP alpha and the rolling JKP residual mean for "
            "the other strategies; the CSV records the measure explicitly. Full-path performance "
            "covers August 1999 through December 2024 (305 months). Factor attribution uses the fixed "
            "185-month evaluation window from August 2009 through December 2024.",
            "",
            "## Complete milestone disposition",
            "",
            "| ID | Status | Common evidence class | Title |",
            "|---|---|---|---|",
        ]
    )
    for row in rows:
        safe_title = str(row["title"]).replace("|", "\\|")
        lines.append(
            f"| {row['milestone_id']} | {row['status']} | {row['common_evidence_class']} | {safe_title} |"
        )
    lines.extend(
        [
            "",
            "## Reproducibility boundary",
            "",
            "`cross_paper_summary.csv` is the canonical 69-row table. `family_inference.csv` records "
            "the ordered Holm calculation for the 17 observed primary tests while retaining 69 as "
            "the declared family size. Non-evaluable cases use blank metric fields; the multiplicity "
            "procedure does not turn missing strategies into measured zero-return strategies. "
            "`final_manifest.json` pins the ledger, benchmark contract, every evaluated metrics file, "
            "the builder, and all generated synthesis files.",
            "",
        ]
    )
    return ("\n".join(lines)).encode()


def build(root: Path) -> dict[str, bytes]:
    study = root / "paper_runs/us_jkp_headline"
    ledger_path = study / "milestones.json"
    contract_path = study / "benchmark_contract.json"
    ledger = json.loads(ledger_path.read_text())
    contract = json.loads(contract_path.read_text())
    milestones = ledger["milestones"]
    family_size = int(contract["inference_family_size"])
    if len(milestones) != family_size or ledger["required_paper_count"] != family_size:
        raise ValueError("ledger and inference family must both contain exactly 69 papers")
    if any(row["status"] not in TERMINAL_STATUSES for row in milestones):
        raise ValueError("all milestones must be terminal before final synthesis")
    expected_ids = [f"M{number:03d}" for number in range(1, family_size + 1)]
    if [row["milestone_id"] for row in milestones] != expected_ids:
        raise ValueError("milestone IDs must be unique, ordered, and contiguous")

    summary_rows: list[dict[str, Any]] = []
    metric_inputs: list[Path] = []
    for milestone in milestones:
        evaluated = milestone["status"] in EVALUATED_STATUSES
        evidence_class = {
            "completed_adapted": "headline_adaptation",
            "completed_partial": "central_partial_adaptation",
            "closed_not_evaluable": "not_evaluable",
        }[milestone["status"]]
        row = {
            "milestone_id": milestone["milestone_id"],
            "canonical_work_id": milestone["canonical_work_id"],
            "title": milestone["title"],
            "system_ids": milestone["system_ids"],
            "status": milestone["status"],
            "common_evidence_class": evidence_class,
            "common_jkp_evaluated": evaluated,
            "original_system_end_to_end_reproduced": False,
            "prior_evidence_route": milestone["prior_evidence_route"],
            **{column: "" for column in SUMMARY_COLUMNS[9:25]},
            "recipe_path": milestone["recipe_path"],
            "implementation_path": milestone["implementation_path"],
            "run_manifest_path": milestone["run_manifest_path"],
            "monthly_returns_path": milestone["monthly_returns_path"],
            "metrics_path": milestone["metrics_path"],
            "verdict_path": milestone["verdict_path"],
            "evaluated_scope": milestone["evaluated_scope"],
            "closure_reason": milestone["closure_reason"],
        }
        if evaluated:
            if not all(milestone[key] for key in ("recipe_path", "implementation_path", "run_manifest_path", "monthly_returns_path", "metrics_path", "verdict_path")):
                raise ValueError(f"evaluated milestone has incomplete paths: {milestone['milestone_id']}")
            metric_path = root / milestone["metrics_path"]
            row.update(primary_metric(metric_path))
            metric_inputs.append(metric_path)
        else:
            if any(milestone[key] for key in ("run_manifest_path", "monthly_returns_path", "metrics_path")):
                raise ValueError(f"non-evaluable milestone has fabricated result paths: {milestone['milestone_id']}")
        summary_rows.append(row)

    evaluated_rows = [row for row in summary_rows if row["common_jkp_evaluated"]]
    family = holm_rows(evaluated_rows, family_size)
    family_lookup = {row["milestone_id"]: row for row in family}
    for row in evaluated_rows:
        item = family_lookup[row["milestone_id"]]
        row.update(
            holm_rank_among_evaluable=item["rank"],
            holm_family_size=family_size,
            holm_adjusted_p=item["holm_adjusted_p"],
            holm_reject_5pct=item["holm_reject_5pct"],
        )

    outputs = {
        "cross_paper_summary.csv": csv_bytes(summary_rows, SUMMARY_COLUMNS),
        "family_inference.csv": csv_bytes(family, FAMILY_COLUMNS),
        "FINAL_SUMMARY.md": markdown_summary(summary_rows, family),
    }
    builder_path = Path(__file__).resolve()
    input_paths = [ledger_path, contract_path, *metric_inputs]
    manifest = {
        "schema_version": 1,
        "study_id": contract["benchmark_id"],
        "status": "complete",
        "paper_milestones": family_size,
        "closed_milestones": len(summary_rows),
        "headline_adaptations_evaluated": sum(row["status"] == "completed_adapted" for row in summary_rows),
        "central_partial_adaptations_evaluated": sum(row["status"] == "completed_partial" for row in summary_rows),
        "closed_not_evaluable": sum(row["status"] == "closed_not_evaluable" for row in summary_rows),
        "full_original_systems_reproduced_end_to_end": 0,
        "raw_primary_rejections_at_5pct": sum(row["jkp_excess_p_two_sided"] < 0.05 for row in evaluated_rows),
        "holm_family_size": family_size,
        "holm_rejections_at_5pct": sum(row["holm_reject_5pct"] for row in evaluated_rows),
        "non_evaluable_performance_policy": "missing_not_zero",
        "input_sha256": {str(path.relative_to(root)): sha256_file(path) for path in input_paths},
        "builder_path": str(builder_path.relative_to(root)),
        "builder_sha256": sha256_file(builder_path),
        "output_sha256": {name: sha256_bytes(value) for name, value in outputs.items()},
        "claim_boundary": "Common JKP adaptations and central partial adaptations are not full end-to-end reproductions of the original paper systems.",
    }
    outputs["final_manifest.json"] = json_bytes(manifest)
    return outputs


def write_outputs(study: Path, outputs: dict[str, bytes]) -> None:
    for name, value in outputs.items():
        path = study / name
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_bytes(value)
        temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    outputs = build(root)
    study = root / "paper_runs/us_jkp_headline"
    if args.check:
        stale = [name for name, value in outputs.items() if not (study / name).exists() or (study / name).read_bytes() != value]
        if stale:
            raise SystemExit(f"stale or missing cross-paper outputs: {', '.join(stale)}")
        print("cross-paper synthesis is current")
    else:
        write_outputs(study, outputs)
        print(f"wrote {len(outputs)} final synthesis files")


if __name__ == "__main__":
    main()
