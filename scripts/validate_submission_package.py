#!/usr/bin/env python3
"""Fail loudly when the paper package and immutable evidence disagree."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "paper_runs" / "submission_evidence"
PAPER = ROOT / "docs" / "paper"
RUNS = {
    "g7_ex_us_corrected": ["CAN", "FRA", "DEU", "ITA", "JPN", "GBR"],
    "g7_missing_adverse": ["CAN", "FRA", "DEU", "ITA", "JPN", "GBR"],
    "usa_retrospective_corrected": ["USA"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_run(tag: str, markets: list[str], lock_hash: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    run = EVIDENCE / tag
    manifest_path = run / "run_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    assert manifest["markets"] == markets, (tag, manifest["markets"], markets)
    assert manifest["analysis_lock_sha256"] == lock_hash, tag
    assert manifest["paid_api_calls"] == 0 and manifest["openrouter_spend_usd"] == 0.0
    for name, expected in manifest["output_sha256"].items():
        path = run / name
        assert path.exists() and sha256(path) == expected, (tag, name)

    primary = pd.read_csv(run / "candidate_primary_results.csv")
    failures = pd.read_csv(run / "candidate_path_failures.csv")
    assert len(primary) == 62 and primary["candidate_id"].nunique() == 62
    assert set(primary["status"].astype(str).str.split(":").str[0]) <= {"ok", "failed"}
    ok = primary[primary["status"].eq("ok")]
    failed = primary[~primary["status"].eq("ok")]
    if not ok.empty:
        assert ok["n_months"].nunique() == 1
        assert ok["start"].nunique() == 1 and ok["end"].nunique() == 1
        assert np.allclose(
            ok["alpha_monthly"], ok["bootstrap_alpha_point_monthly"], rtol=1e-10, atol=1e-12
        )
        numeric = [
            "alpha_annualized",
            "alpha_t_hac",
            "p_value_two_sided",
            "holm_p_value",
            "max_abs_t_p_value",
            "simultaneous_ci_low_annualized",
            "simultaneous_ci_high_annualized",
        ]
        assert np.isfinite(ok[numeric].to_numpy(dtype=float)).all()
    if not failed.empty:
        adjustments = pd.read_csv(run / "multiplicity_adjustments.csv").set_index("candidate_id")
        assert (adjustments.loc[failed["candidate_id"], "adjustment_input_p_value"] == 1.0).all()

    costs = pd.read_csv(run / "candidate_cost_alpha_results.csv")
    assert len(costs) == 62 * 5
    assert set(costs["cost_bps_one_way"].unique()) == {0, 5, 10, 25, 50}
    successful_costs = costs[costs["status"].eq("ok")]
    for _, frame in successful_costs.groupby("candidate_id"):
        values = frame.sort_values("cost_bps_one_way")["alpha_annualized"].to_numpy(float)
        assert (np.diff(values) <= 1e-10).all()
    return primary, failures


def main() -> int:
    lock_path = EVIDENCE / "analysis_lock.json"
    lock = json.loads(lock_path.read_text())
    assert lock["schema_version"] == 3
    lock_hash = sha256(lock_path)
    for relative, expected_hash in lock["file_sha256"].items():
        locked_path = ROOT / relative
        assert locked_path.exists() and sha256(locked_path) == expected_hash, (
            "locked file mismatch",
            relative,
        )

    outputs = {
        tag: assert_run(tag, markets, lock_hash) for tag, markets in RUNS.items()
    }
    g7, g7_failures = outputs["g7_ex_us_corrected"]
    adverse, adverse_failures = outputs["g7_missing_adverse"]
    usa, usa_failures = outputs["usa_retrospective_corrected"]
    assert set(g7.loc[g7["status"].eq("ok"), "candidate_id"]) == set(
        adverse.loc[adverse["status"].eq("ok"), "candidate_id"]
    )
    failure_key = ["market", "month", "candidate_id", "failure_total_return"]
    pd.testing.assert_frame_equal(
        g7_failures[failure_key].sort_values(failure_key[:-1]).reset_index(drop=True),
        adverse_failures[failure_key].sort_values(failure_key[:-1]).reset_index(drop=True),
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    assert len(usa) == 62 and usa["status"].eq("ok").all() and usa_failures.empty

    required_tables = [
        "artifact_summary.tex",
        "primary_results.tex",
        "system_registry.tex",
        "candidate_registry.tex",
        "artifact_failures.tex",
        "path_failures.tex",
        "cost_results.tex",
        "country_results.tex",
        "inference_sensitivity.tex",
        "claim_map.tex",
    ]
    required_figures = [
        "census_funnel.pdf",
        "artifact_attrition.pdf",
        "g7_alpha_forest.pdf",
        "cost_sensitivity.pdf",
        "country_robustness.pdf",
        "usa_g7_transfer.pdf",
    ]
    required = [
        PAPER / "generated_results.tex",
        PAPER / "related_literature.tex",
        PAPER / "references.bib",
        EVIDENCE / "claims.csv",
        EVIDENCE / "fixed_calendar_diagnostics" / "fixed_calendar_country_loo.csv",
        EVIDENCE / "fixed_calendar_diagnostics" / "manifest.json",
        ROOT / "scripts" / "run_fixed_calendar_diagnostics.py",
        ROOT / "docs" / "reporting_addendum.md",
        ROOT / "docs" / "owner_review_packet.md",
        ROOT / "output" / "pdf" / "alpha_agent_replication_paper.pdf",
        *[PAPER / "tables" / name for name in required_tables],
        *[PAPER / "figures" / name for name in required_figures],
    ]
    missing = [str(path) for path in required if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise FileNotFoundError(f"missing/empty submission assets: {missing}")

    diagnostic_dir = EVIDENCE / "fixed_calendar_diagnostics"
    diagnostic_manifest = json.loads((diagnostic_dir / "manifest.json").read_text())
    assert diagnostic_manifest["classification"] == "post_hoc_fixed_calendar_diagnostic"
    assert diagnostic_manifest["primary_analysis_lock_sha256"] == lock_hash
    assert diagnostic_manifest["script_sha256"] == sha256(
        ROOT / "scripts" / "run_fixed_calendar_diagnostics.py"
    )
    for name, expected_hash in diagnostic_manifest["output_sha256"].items():
        assert sha256(diagnostic_dir / name) == expected_hash, name
    for name, expected_hash in diagnostic_manifest["input_sha256"].items():
        assert sha256(EVIDENCE / "g7_ex_us_corrected" / name) == expected_hash, name
    diagnostic = pd.read_csv(diagnostic_dir / "fixed_calendar_country_loo.csv")
    assert len(diagnostic) == 351 and diagnostic["status"].eq("ok").all()
    assert set(diagnostic["diagnostic"]) == {
        "country_fixed_primary_calendar",
        "loo_fixed_primary_calendar",
        "g7_usa_common_calendar",
    }

    manuscript = (PAPER / "alpha_agent_replication.tex").read_text()
    generated = (PAPER / "generated_results.tex").read_text()
    all_text = "\n".join(
        [manuscript, generated, (ROOT / "docs" / "owner_review_packet.md").read_text()]
        + [(PAPER / "tables" / name).read_text() for name in required_tables]
    )
    # Treat conventional editorial markers as unresolved, while allowing the
    # lower-case word "placeholder" when it is substantive audit evidence
    # (for example, a repository documented as a one-file placeholder).
    forbidden = re.compile(r"\b(?:TODO|TBD|PLACEHOLDER)\b|\?\?")
    assert not forbidden.search(all_text), forbidden.search(all_text).group(0) if forbidden.search(all_text) else ""
    assert not re.search(r"\\[A-Za-z]+[0-9]", manuscript), "digit-bearing TeX control word"
    for relative in re.findall(r"\\InputIfFileExists\{([^}]+)\}", manuscript):
        assert (PAPER / relative).exists(), relative
    for relative in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", manuscript):
        assert (PAPER / relative).exists(), relative

    bib = (PAPER / "references.bib").read_text()
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    cited: set[str] = set()
    for contents in re.findall(r"\\cite[pt]?\{([^}]+)\}", manuscript + "\n" + (PAPER / "related_literature.tex").read_text()):
        cited.update(key.strip() for key in contents.split(","))
    assert cited <= bib_keys, sorted(cited - bib_keys)

    owner = (ROOT / "docs" / "owner_review_packet.md").read_text()
    assert "OWNER STATUS: PENDING" in owner and "NOT APPROVED FOR SUBMISSION" in owner
    claims = pd.read_csv(EVIDENCE / "claims.csv")
    assert not claims.empty and len(claims) >= 15

    summary = {
        "analysis_lock_sha256": lock_hash,
        "g7_executable_candidates": int(g7["status"].eq("ok").sum()),
        "g7_failed_candidates": int((~g7["status"].eq("ok")).sum()),
        "g7_path_failure_events": int(len(g7_failures)),
        "adverse_executable_candidates": int(adverse["status"].eq("ok").sum()),
        "usa_executable_candidates": int(usa["status"].eq("ok").sum()),
        "claims": int(len(claims)),
        "paper_pdf_sha256": sha256(ROOT / "output" / "pdf" / "alpha_agent_replication_paper.pdf"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
