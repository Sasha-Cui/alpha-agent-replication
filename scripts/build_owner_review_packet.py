#!/usr/bin/env python3
"""Build the archived evidence-audit manuscript's owner-review packet."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "paper_runs" / "submission_evidence"
PRIMARY = EVIDENCE / "g7_ex_us_corrected"
ADVERSE = EVIDENCE / "g7_missing_adverse"
USA = EVIDENCE / "usa_retrospective_corrected"
OUTPUT = ROOT / "docs" / "owner_review_packet.md"
PAPER_PDF = ROOT / "output" / "pdf" / "alpha_agent_replication_paper.pdf"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(paths: Iterable[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"owner packet inputs missing: {missing}")


def clean(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    text = str(value).replace("|", "\\|").replace("\n", " ").strip()
    return text or "—"


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if columns is not None:
        columns = [column for column in columns if column in frame]
        frame = frame[columns]
    if frame.empty:
        return "_No rows._"
    header = "| " + " | ".join(map(clean, frame.columns)) + " |"
    rule = "| " + " | ".join(["---"] * len(frame.columns)) + " |"
    rows = [
        "| " + " | ".join(clean(value) for value in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    ]
    return "\n".join([header, rule, *rows])


def pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def main() -> int:
    paths = [
        ROOT / "literature_review" / "census_v1" / "system_registry.csv",
        EVIDENCE / "artifact_audit" / "artifact_audit.csv",
        EVIDENCE / "native_fidelity_ledger.csv",
        EVIDENCE / "analysis_lock.json",
        PRIMARY / "candidate_primary_results.csv",
        PRIMARY / "candidate_path_failures.csv",
        PRIMARY / "run_manifest.json",
        ADVERSE / "candidate_primary_results.csv",
        USA / "candidate_primary_results.csv",
        EVIDENCE / "claims.csv",
        EVIDENCE / "fixed_calendar_diagnostics" / "fixed_calendar_country_loo.csv",
        EVIDENCE / "fixed_calendar_diagnostics" / "manifest.json",
        ROOT / "docs" / "confirmatory_analysis_protocol.md",
        ROOT / "docs" / "reporting_addendum.md",
        ROOT / "docs" / "paper" / "alpha_agent_replication.tex",
        PAPER_PDF,
        ROOT / "LICENSES" / "CODE_LICENSE.txt",
        ROOT / "LICENSES" / "DOCUMENTATION_LICENSE.txt",
        ROOT / "LICENSES" / "THIRD_PARTY.md",
    ]
    require(paths)

    registry = pd.read_csv(paths[0], sep="|")
    artifact = pd.read_csv(paths[1])
    native = pd.read_csv(paths[2])
    lock = json.loads(paths[3].read_text())
    primary = pd.read_csv(paths[4])
    failures = pd.read_csv(paths[5])
    manifest = json.loads(paths[6].read_text())
    adverse = pd.read_csv(paths[7])
    usa = pd.read_csv(paths[8])
    claims = pd.read_csv(paths[9])
    fixed_calendar = pd.read_csv(paths[10])

    if len(registry) != 103 or int(registry["main_FT"].eq("Y").sum()) != 67:
        raise RuntimeError("registry denominator changed")
    if len(primary) != 62 or primary["candidate_id"].nunique() != 62:
        raise RuntimeError("primary family is not the frozen 62 candidates")
    if len(adverse) != 62 or len(usa) != 62:
        raise RuntimeError("sensitivity/retrospective family is incomplete")

    ft_artifact = artifact[artifact["main_FT"].eq("Y")]
    listed = int(ft_artifact["public_artifact_listed"].eq("Y").sum())
    reachable = int(
        ft_artifact["reachability_outcome"].astype(str).str.startswith("reachable").sum()
    )
    compatible = int(
        native["prespecified_G7_monthly_common_task_compatible"].eq("Y").sum()
    )
    shipped = int(native["native_dated_signal_or_return_shipped"].eq("Y").sum())
    ok = primary[primary["status"].eq("ok")].copy()
    adverse_ok = adverse[adverse["status"].eq("ok")].copy()
    usa_ok = usa[usa["status"].eq("ok")].copy()
    holm = ok[(ok["holm_p_value"] <= 0.05) & (ok["alpha_annualized"] > 0)]
    max_t = ok[(ok["max_abs_t_p_value"] <= 0.05) & (ok["alpha_annualized"] > 0)]
    bh = ok[(ok["bh_q_value"] <= 0.05) & (ok["alpha_annualized"] > 0)]
    by = ok[(ok["by_q_value"] <= 0.05) & (ok["alpha_annualized"] > 0)]
    material = ok[ok["simultaneous_ci_low_annualized"] >= 0.02]
    nominal = ok[(ok["p_value_two_sided"] <= 0.05) & (ok["alpha_annualized"] > 0)]

    failure_view = failures.copy()
    for column in ["observed_gross_return", "failure_total_return"]:
        if column in failure_view:
            failure_view[column] = failure_view[column].map(
                lambda value: "—" if pd.isna(value) else f"{float(value):.6f}"
            )

    review_rows = pd.DataFrame(
        [
            ["Census denominator", len(registry), "Must remain 103 lineages"],
            ["Primary F/T denominator", len(ft_artifact), "Must remain 67 systems"],
            ["Listed public artifacts", listed, f"{listed}/67 = {listed/67:.2%}"],
            ["Reachable public artifacts", reachable, f"{reachable}/67 = {reachable/67:.2%}"],
            ["Native dated output shipped", shipped, "Task compatibility assessed separately"],
            ["Native G7-common-task streams", compatible, "Unavailable is not zero return"],
            ["Frozen proxy family", len(primary), "Mechanism-inspired, not native"],
            ["Executable pooled paths", len(ok), "Failures retain p=1"],
            ["Nominal positive 5%", len(nominal), "Two-sided HAC and positive estimate"],
            ["Holm-positive 5%", len(holm), "Primary asymptotic family control"],
            ["BH-positive 5%", len(bh), "False-discovery control; 62-candidate p=1 padding"],
            ["BY-positive 5%", len(by), "Dependence-robust false-discovery control"],
            ["Max-|t|-positive 5%", len(max_t), "Paired moving-block family control"],
            ["Confirmed alpha >=2pp", len(material), "Simultaneous lower bound >=2pp"],
            ["Median net alpha", pct(float(ok["alpha_annualized"].median())), "10 bp one-way"],
            ["Adverse-policy executable paths", len(adverse_ok), "Position-adverse missing returns"],
            ["USA executable paths", len(usa_ok), "Retrospective, never confirmatory"],
            ["Bankruptcy events", len(failures), "Never clipped/restarted/recapitalized"],
        ],
        columns=["Item", "Observed", "Required interpretation"],
    )

    hash_paths = [
        paths[3],
        paths[4],
        paths[5],
        paths[7],
        paths[8],
        paths[9],
        paths[10],
        paths[11],
        paths[12],
        paths[13],
        paths[14],
        paths[15],
    ]
    hash_rows = pd.DataFrame(
        [[str(path.relative_to(ROOT)), sha256(path)] for path in hash_paths],
        columns=["File", "SHA-256"],
    )

    lines = [
        "# Owner review packet",
        "",
        "> **LEGACY EVIDENCE-AUDIT RECORD.** This packet belongs to the archived",
        "> `alpha_agent_replication.tex` workflow, not the current ICAIF submission.",
        "",
        "> **OWNER STATUS: PENDING — NOT APPROVED FOR SUBMISSION**",
        "",
        "This packet is generated from the immutable evidence outputs. It does not "
        "substitute for Sasha Cui's factual, statistical, citation, license, and visual review.",
        "",
        "## Decision summary to vet",
        "",
        markdown_table(review_rows),
        "",
        "The central claim is an artifact-to-evidence attrition result. The 62-candidate "
        "experiment is a lower-fidelity test of mechanism-inspired characteristic "
        "translations. It is not a ranking or replication of the named agents.",
        "",
        "## Machine-generated claim map",
        "",
        markdown_table(claims),
        "",
        "## Limited-liability and execution failures",
        "",
        "Any 100/100 sleeve with a realized total portfolio return at or below -100% "
        "is a complete-path failure. The evaluator neither clips the month nor injects "
        "capital. The hypothesis remains in the Holm/BH/BY denominator with p=1; "
        "max-statistic procedures use executable paths only.",
        "",
        markdown_table(
            failure_view,
            [
                "market",
                "month",
                "candidate_id",
                "selected_sleeve",
                "observed_gross_return",
                "failure_total_return",
                "path_status",
            ],
        ),
        "",
        "## Protocol deviations requiring explicit author acceptance",
        "",
        "1. The first G7 run was rejected after a line-level audit found four evaluator "
        "defects: future-return availability in formation, incorrect long-short NAV "
        "drift, mismatched country sets, and different ordinary/bootstrap calendars.",
        "2. The first amended attempt halted in Canada when a sleeve reached nonpositive "
        "NAV. After verifying return scale, Amendment 2 classified such paths as "
        "limited-liability implementation failures. No corrected alpha table or ranking "
        "was produced before the third lock.",
        "3. Accordingly, the G7 analysis is geographically external evidence under "
        "a disclosed post-outcome repair and post-runtime amendment, not a pristine confirmatory "
        "holdout. The USA analysis is retrospective.",
        "4. A post-hoc, separately hashed diagnostic fixes the 27 primary executable "
        "candidates and 293-month calendar for country/LOO comparisons and re-estimates "
        "G7 on the 281-month U.S. comparison calendar. It does not alter primary estimates.",
        "",
        "## Statistical checks",
        "",
        f"- Common pooled months: {int(ok['n_months'].iloc[0]) if len(ok) else 0}; "
        f"realized range: {clean(ok['start'].iloc[0]) if len(ok) else '—'} to "
        f"{clean(ok['end'].iloc[0]) if len(ok) else '—'}.",
        f"- Bootstrap: {manifest['bootstrap']['n_bootstrap']} paired circular moving-block "
        f"draws; block length {manifest['bootstrap']['block_length']}; seed "
        f"{manifest['bootstrap']['seed']}.",
        "- Confirm that every ordinary primary alpha equals its bootstrap point alpha, "
        "that all executable candidates share the same calendar, and that all requested "
        "country sleeves contribute to each retained pooled month.",
        "- Inspect HAC lags 0/3/6/12, block lengths 3/6/12, cost points 0/5/10/25/50, "
        "fixed-calendar leave-one-country-out estimates, and the position-adverse missing-return run.",
        "",
        "## Licensing and redistribution checks",
        "",
        "- Project code: Apache License 2.0.",
        "- Paper, protocols, and original annotations: CC BY 4.0.",
        "- Third-party papers, repositories, and JKP-derived data retain their own terms "
        "and are not relicensed. Restricted row-level return outputs remain on Bouchet.",
        "- The artifact ledger records observed licenses but makes no legal-compatibility opinion.",
        "",
        "## Exact reproduction commands",
        "",
        "```bash",
        "cd /nfs/roberts/project/pi_btk22/zc362/ideas/alpha_evolve",
        "PYTHONPATH=src /home/zc362/project_pi_btk22/zc362/environments/bin/kt-python -m pytest tests/test_submission_analysis.py tests/test_submission_runner.py -q",
        "PYTHONPATH=src .venv/bin/python scripts/run_submission_evidence.py --tag g7_ex_us_corrected --bootstrap 2000 --missing-return-policy zero",
        "PYTHONPATH=src .venv/bin/python scripts/run_submission_evidence.py --tag g7_missing_adverse --bootstrap 2000 --missing-return-policy adverse_100",
        "PYTHONPATH=src .venv/bin/python scripts/run_submission_evidence.py --markets USA --tag usa_retrospective_corrected --bootstrap 2000 --missing-return-policy zero",
        "PYTHONPATH=src .venv/bin/python scripts/run_fixed_calendar_diagnostics.py",
        "PYTHONPATH=src .venv/bin/python scripts/build_paper_assets.py",
        "module load texlive/20240312-GCC-13.3.0",
        "cd docs/paper",
        "pdflatex -interaction=nonstopmode -halt-on-error alpha_agent_replication.tex",
        "bibtex alpha_agent_replication",
        "pdflatex -interaction=nonstopmode -halt-on-error alpha_agent_replication.tex",
        "pdflatex -interaction=nonstopmode -halt-on-error alpha_agent_replication.tex",
        "```",
        "",
        "## Frozen/output hashes",
        "",
        f"Final analysis-lock SHA-256: `{sha256(paths[3])}` (schema "
        f"{lock['schema_version']}).",
        "",
        markdown_table(hash_rows),
        "",
        "## Required author sign-off",
        "",
        "Sasha Cui must explicitly vet the headline counts and prose, inspect every "
        "rendered page, sample registry and failure-ledger rows against primary records, "
        "confirm citation and license statements, and decide whether the disclosed "
        "protocol deviations permit submission. Until then, status remains **PENDING**.",
        "",
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT)
    print(sha256(OUTPUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
