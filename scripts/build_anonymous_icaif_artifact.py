#!/usr/bin/env python3
"""Build an inspectable anonymous ICAIF artifact from aggregate evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


REQUIRED = [
    "docs/confirmatory_analysis_protocol.md",
    "docs/good_faith_reconstruction_protocol.md",
    "docs/source_anchor_review_packet.md",
    "docs/full_corpus_bibliography.md",
    "docs/system_census_bibliography.md",
    "docs/paper/census_primary_records.bib",
    "docs/paper/generated_corpus_citations.tex",
    "literature_review/census_v1/primary_record_metadata.csv",
    "paper_runs/submission_evidence/analysis_lock.json",
    "paper_runs/submission_evidence/artifact_audit/artifact_audit.csv",
    "paper_runs/submission_evidence/artifact_audit/artifact_audit_summary.csv",
    "paper_runs/submission_evidence/native_fidelity_ledger.csv",
    "paper_runs/idea_replications/paper_derived_source_replication_ledger.csv",
    "paper_runs/submission_evidence/frozen_candidate_registry.csv",
    "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv",
    "paper_runs/submission_evidence/mapping_audit/source_scope_summary.csv",
    "paper_runs/submission_evidence/mapping_audit/within_source_mapping_sensitivity.csv",
    "paper_runs/submission_evidence/mapping_audit/mapping_combination_sensitivity.csv",
    "paper_runs/submission_evidence/mapping_audit/source_grounded_subset_results.csv",
    "paper_runs/submission_evidence/mapping_audit/source_grounded_subset_summary.csv",
    "paper_runs/submission_evidence/mapping_audit/source_anchor_review_packet.csv",
    "paper_runs/submission_evidence/mapping_audit/manifest.json",
    "paper_runs/submission_evidence/replication_scope/system_census_bibliography.csv",
    "paper_runs/submission_evidence/replication_scope/direct_code_attempt_inventory.csv",
    "paper_runs/submission_evidence/replication_scope/source_grounded_component_inventory.csv",
    "paper_runs/submission_evidence/replication_scope/pretrim_primary_record_inventory.csv",
    "paper_runs/submission_evidence/replication_scope/work_level_evidence_waterfall.csv",
    "paper_runs/repository_ff5mom_metrics_summary.csv",
    "paper_runs/submission_evidence/usa_retrospective_corrected/candidate_monthly_USA.csv",
    "paper_runs/submission_evidence/usa_retrospective_corrected/factor_monthly_USA.csv",
    "paper_runs/submission_evidence/usa_retrospective_corrected/candidate_primary_results.csv",
    "paper_runs/submission_evidence/usa_retrospective_corrected/candidate_cost_alpha_results.csv",
    "paper_runs/submission_evidence/usa_retrospective_corrected/hac_lag_sensitivity.csv",
    "paper_runs/submission_evidence/usa_retrospective_corrected/bootstrap_block_sensitivity.csv",
    "paper_runs/submission_evidence/usa_retrospective_corrected/turnover_summary.csv",
    "paper_runs/submission_evidence/usa_retrospective_corrected/run_manifest.json",
    "paper_runs/submission_evidence/usa_broad_jkp_crossfit/broad_jkp_crossfit_residuals.csv",
    "paper_runs/submission_evidence/usa_broad_jkp_crossfit/broad_jkp_crossfit_results.csv",
    "paper_runs/submission_evidence/usa_broad_jkp_crossfit/run_manifest.json",
    "paper_runs/submission_evidence/g7_ex_us_corrected/candidate_path_failures.csv",
    "paper_runs/submission_evidence/international_failure_forensics/failure_event_forensics.csv",
    "paper_runs/submission_evidence/international_failure_forensics/failure_month_summary.csv",
    "paper_runs/submission_evidence/international_failure_forensics/manifest.json",
    "scripts/build_mapping_audit.py",
    "scripts/build_source_anchor_review_packet.py",
    "scripts/build_census_citation_assets.py",
    "scripts/build_replication_scope_assets.py",
    "scripts/refresh_census_primary_record_metadata.py",
    "scripts/diagnose_international_failures.py",
    "scripts/build_icaif2026_submission_assets.py",
    "scripts/validate_icaif_major_revision.py",
    "tests/test_mapping_audit.py",
    "tests/test_source_anchor_review_packet.py",
    "tests/test_census_citation_assets.py",
    "tests/test_replication_scope_assets.py",
    "tests/test_international_failure_forensics.py",
]

README = """# Anonymous ICAIF 2026 empirical artifact

This package supports the paper's public-evidence audit and historical spanning tests.
It contains aggregate monthly portfolios and factors, source-to-proxy mappings, execution
statuses, statistical outputs, international failure forensics, analysis code, tests,
and a SHA-256 inventory. It does not contain restricted security-level market data.

## Interpretive boundaries

- Thirteen non-evaluable code attempts are evidence failures, not zero returns.
- The 62 U.S. portfolios are researcher-authored historical mechanism mappings, not
  native agent returns. They were frozen after U.S. outcomes were inspected and were
  not independently double-coded.
- Thirteen mappings are source-anchored partial component tests. The other 49 are favorable
  narrative stress tests whose failures cannot count as evidence against their sources.
- The pre-trim screen contains 103 lineages backed by 98 canonical works. The retained
  availability census contains 67 lineages backed by 69 formally cited works, not 67 replications.
  All 98 screened works are cited in the paper. Forty retained works receive 50
  good-faith mappings; 29 retained works remain availability-only. Five works support
  13 component tests, while 35 support 37 narrative-only favorable stress tests.
  Fourteen public implementations were targeted, only eight of which belong to the
  67-system F/T census; five benchmarks and one comparator were diagnostic additions.
  No native-agent replication was completed; one released 60-bar return/volatility
  seed yielded a monthly JKP adaptation, not a literal expression replication.
- The broad-factor analysis is post hoc and its bootstrap resamples fixed out-of-sample
  residuals rather than rerunning rolling tuning.
- International performance is not headline evidence. The included forensic ledger
  shows why all 40 insolvency events are treated as a data/implementation alarm.

## Entry points

- `paper_runs/submission_evidence/mapping_audit/mapping_audit.csv`: every mapping,
  formula, fidelity code, source-support field, benefit-of-the-doubt choice,
  anti-strawman role, negative-evidence boundary, omission, freeze timestamp, and hash.
- `docs/good_faith_reconstruction_protocol.md`: the claim-card, evidence-priority,
  favorable-implementation, alternative-mapping, and source-protection rules.
- `docs/source_anchor_review_packet.md` and the corresponding CSV: page/section or
  pinned-repository anchors, supported content, and researcher-supplied changes for
  the 13 closest mappings. This post-hoc packet awaits independent review.
- `docs/system_census_bibliography.md`: all 67 system lineages and primary records.
- `docs/full_corpus_bibliography.md`: all 98 pre-trim canonical works, including the
  69 works supporting retained F/T lineages.
- `paper_runs/submission_evidence/replication_scope/`: the exact 14 code attempts and
  13 source-anchored partial component mappings from five source papers, plus the 98-work
  evidence waterfall reconciling screening, code attempts, and reconstruction coverage.
- `paper_runs/submission_evidence/usa_retrospective_corrected/candidate_monthly_USA.csv`:
  aggregate monthly U.S. candidate returns.
- `paper_runs/submission_evidence/international_failure_forensics/`: event-level audit.
- `MANIFEST.json`: sizes and SHA-256 hashes for every packaged object.

Run `python scripts/validate_icaif_major_revision.py` from the repository root after
placing the package back into its original repository layout.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output or root / "output/anonymous_icaif2026_artifact").resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    inventory = []
    for relative in REQUIRED:
        source = root / relative
        if not source.is_file():
            raise FileNotFoundError(relative)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        inventory.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
    (output / "README.md").write_text(README, encoding="utf-8")
    inventory.append({"path": "README.md", "bytes": (output / "README.md").stat().st_size,
                      "sha256": sha256(output / "README.md")})
    manifest = {
        "artifact": "anonymous_icaif2026_public_evidence_audit",
        "file_count": len(inventory),
        "restricted_security_level_data_included": False,
        "files": sorted(inventory, key=lambda row: row["path"]),
    }
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    archive = output.with_suffix(".tar.gz")
    if archive.exists():
        archive.unlink()
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(output, arcname=output.name)
    print(json.dumps({"directory": str(output), "archive": str(archive),
                      "files": len(inventory), "archive_sha256": sha256(archive)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
