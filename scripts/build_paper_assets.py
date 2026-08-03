#!/usr/bin/env python3
"""Build every generated table, figure, macro, and claim record for the paper.

The builder is intentionally strict.  It verifies the artifact/census inputs,
the three analysis manifests and their output hashes, the 62-candidate family,
the p=1 treatment of failed paths, and the separation between failed paths and
finite return estimates before writing any paper asset.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPO_ROOT / "paper_runs" / "submission_evidence"
PAPER_DIR = REPO_ROOT / "docs" / "paper"
FIXED_CALENDAR_DIR = EVIDENCE_ROOT / "fixed_calendar_diagnostics"

COLORS = {
    "white": "#FFFFFF",
    "ink": "#17212B",
    "navy": "#16324F",
    "blue": "#276FBF",
    "teal": "#1B7F79",
    "gold": "#9A6700",
    "red": "#B42318",
    "panel": "#F2F6FA",
    "rule": "#C7D2DE",
    "muted": "#53677A",
    "failure": "#8A3943",
}

EXPECTED_MACROS = {
    "SystemCount",
    "MethodSystemCount",
    "ArtifactCountFT",
    "ArtifactRateFT",
    "ArtifactWilsonFT",
    "NativeReturnCount",
    "NativeDatedOutputCount",
    "ProxyCount",
    "NominalPositiveCount",
    "HolmPositiveCount",
    "BHPositiveCount",
    "BYPositiveCount",
    "MaxTPositiveCount",
    "EconomicConfirmedCount",
    "MedianAlphaPct",
    "BestAdjustedSummary",
    "ResultHeadline",
    "ReachableArtifactCountFT",
    "LicensedArtifactCountFT",
    "PinnedRepoCountFT",
    "ArtifactTierSummaryFT",
    "TargetedAuditCount",
    "TranslatableSeedCount",
    "NativeUnavailableCount",
    "AnalysisLockShort",
    "BootstrapCount",
    "ValidProxyCount",
    "PathFailureCandidateCount",
    "PathFailureEventCount",
    "AlphaIQRPct",
    "PositiveAlphaCount",
    "RealityCheckP",
    "BestAlphaPct",
    "BestCandidateName",
    "WorstAlphaPct",
    "WorstCandidateName",
    "MedianTurnover",
    "TurnoverIQR",
    "MedianCostDragPct",
    "BreakEvenBelowTenCount",
    "PositiveAtTwentyFive",
    "PositiveAtFifty",
    "MedianMissingExposure",
    "MissingExposurePninetyfive",
    "MaxMissingExposure",
    "AdverseMedianAlphaPct",
    "AdverseNominalPositiveCount",
    "AdverseHolmPositiveCount",
    "AdverseEconomicConfirmedCount",
    "MedianPositiveCountries",
    "AllCountryPositiveCount",
    "NoCountryPositiveCount",
    "BestCountry",
    "WorstCountry",
    "MaxLeaveOneOutMedianShiftPct",
    "BestCandidateLooRangePct",
    "USGSevenSpearman",
    "JointlyEstimableCount",
    "SignAgreementCount",
    "USNominalPositiveCount",
    "SameWindowUSGSevenSpearman",
    "SameWindowSignAgreementCount",
    "SameWindowGSevenNominalPositiveCount",
    "ResultInterpretation",
    "ConclusionResult",
    "ProtocolDeviationStatement",
    "HACSensitivitySummary",
    "BlockSensitivitySummary",
    "RegressionMonthCount",
    "RegressionStartMonth",
    "RegressionEndMonth",
}

RUN_CSV_FILES = {
    "primary": "candidate_primary_results.csv",
    "cost": "candidate_cost_alpha_results.csv",
    "metadata": "candidate_metadata.csv",
    "multiplicity": "multiplicity_adjustments.csv",
    "country": "candidate_country_results.csv",
    "loo": "candidate_leave_one_country_out.csv",
    "turnover": "turnover_summary.csv",
    "missing": "missing_return_exposure_summary.csv",
    "path_failures": "candidate_path_failures.csv",
}


class AssetBuildError(RuntimeError):
    """Raised when an input or an inferred paper claim is inconsistent."""


@dataclass(frozen=True)
class Claim:
    claim_id: str
    macro: str
    manuscript_location: str
    claim: str
    rendered_value: str
    source_file: str
    source_filter: str
    source_columns: str
    source_sha256: str
    producing_script: str
    review_status: str = "pending_owner_review"


@dataclass
class RunData:
    name: str
    path: Path
    manifest: dict[str, Any]
    frames: dict[str, pd.DataFrame]

    def frame(self, key: str) -> pd.DataFrame:
        return self.frames[key]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path) -> Path:
    if not path.is_file():
        raise AssetBuildError(f"required input is missing: {path}")
    return path


def read_csv(path: Path, required: Iterable[str]) -> pd.DataFrame:
    require_file(path)
    frame = pd.read_csv(path)
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise AssetBuildError(f"{path} omits required columns: {missing}")
    return frame


def assert_unique(frame: pd.DataFrame, columns: Sequence[str], label: str) -> None:
    if frame.duplicated(list(columns)).any():
        sample = frame.loc[frame.duplicated(list(columns), keep=False), list(columns)].head()
        raise AssetBuildError(f"duplicate {label} rows on {columns}:\n{sample}")


def finite_values(series: pd.Series, label: str, *, allow_empty: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty and not allow_empty:
        raise AssetBuildError(f"no finite observations for {label}")
    return values.astype(float)


def successful(frame: pd.DataFrame) -> pd.DataFrame:
    if "status" not in frame:
        raise AssetBuildError("result frame lacks status")
    return frame.loc[frame["status"].astype(str) == "ok"].copy()


def failed(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame["status"].astype(str) != "ok"].copy()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def latex_escape(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "---"
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def latex_escape_breakable(value: Any, *, chunk: int = 12) -> str:
    """Escape machine-like text while exposing safe line-break opportunities.

    Registry identifiers, formulas, paths, and exact filters contain long runs
    without spaces.  Plain ``latex_escape`` makes those runs unbreakable and can
    push appendix tables beyond the page boundary.  This renderer preserves the
    literal text while allowing a break after punctuation and, for long
    alphanumeric runs such as hashes, at fixed-width boundaries.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "---"
    text = str(value)
    escaped_chars = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    output: list[str] = []
    run_length = 0
    for char in text:
        output.append(escaped_chars.get(char, char))
        if char in "_/.:=,+-|;()[]":
            output.append(r"\allowbreak{}")
            run_length = 0
        elif char.isalnum():
            run_length += 1
            if run_length >= chunk:
                output.append(r"\allowbreak{}")
                run_length = 0
        else:
            run_length = 0
    return "".join(output)


def latex_href(url: Any, label: str) -> str:
    if url is None or (isinstance(url, float) and math.isnan(url)) or not str(url).strip():
        return "---"
    raw = str(url).split(";")[0].strip()
    # These escapes are accepted by hyperref inside its URL argument.
    escaped = (
        raw.replace("%", r"\%")
        .replace("#", r"\#")
        .replace("&", r"\&")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
    )
    return rf"\href{{{escaped}}}{{{latex_escape(label)}}}"


def fmt_number(value: float, digits: int = 2) -> str:
    if not np.isfinite(value):
        return "---"
    return f"{value:.{digits}f}"


def fmt_percent(value: float, digits: int = 2) -> str:
    if not np.isfinite(value):
        return "---"
    return f"{100.0 * value:.{digits}f}\\%"


def fmt_pp(value: float, digits: int = 2) -> str:
    """Format a decimal return as percentage points."""
    return fmt_percent(value, digits)


def fmt_p(value: float) -> str:
    if not np.isfinite(value):
        return "---"
    if value < 0.001:
        return "$<0.001$"
    return f"{value:.3f}"


def fmt_interval(low: float, high: float, *, percent: bool = True) -> str:
    if not np.isfinite(low) or not np.isfinite(high):
        return "---"
    if percent:
        return f"[{100.0 * low:.2f}\\%, {100.0 * high:.2f}\\%]"
    return f"[{low:.2f}, {high:.2f}]"


def fmt_count(value: float) -> str:
    if not np.isfinite(value):
        return "---"
    rounded = round(float(value))
    return str(int(rounded)) if np.isclose(value, rounded) else f"{value:.1f}"


def wilson_interval(successes: int, denominator: int) -> tuple[float, float]:
    if denominator <= 0 or successes < 0 or successes > denominator:
        raise AssetBuildError(f"invalid Wilson inputs: {successes}/{denominator}")
    z = 1.959963984540054
    p = successes / denominator
    denom = 1.0 + z * z / denominator
    center = (p + z * z / (2.0 * denominator)) / denom
    spread = z * math.sqrt(
        p * (1.0 - p) / denominator + z * z / (4.0 * denominator * denominator)
    ) / denom
    return center - spread, center + spread


def candidate_label(row: pd.Series | dict[str, Any]) -> str:
    getter = row.get
    candidate_id = str(getter("candidate_id", "unnamed candidate")).strip()
    proxy_code = "P-" + hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:6].upper()
    paper_ref = getter("paper_ref", "")
    if paper_ref is not None and str(paper_ref).strip() and str(paper_ref) != "nan":
        return f"{proxy_code} {str(paper_ref).strip()}"
    return f"{proxy_code} {candidate_id}"


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": COLORS["white"],
            "savefig.facecolor": COLORS["white"],
            "savefig.edgecolor": COLORS["white"],
            "axes.facecolor": COLORS["panel"],
            "axes.edgecolor": COLORS["rule"],
            "axes.labelcolor": COLORS["ink"],
            "axes.titlecolor": COLORS["navy"],
            "text.color": COLORS["ink"],
            "xtick.color": COLORS["ink"],
            "ytick.color": COLORS["ink"],
            "grid.color": COLORS["rule"],
            "legend.facecolor": COLORS["white"],
            "legend.edgecolor": COLORS["rule"],
            "legend.labelcolor": COLORS["ink"],
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "pdf.fonttype": 42,
        }
    )


def style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor(COLORS["panel"])
    for spine in ax.spines.values():
        spine.set_color(COLORS["rule"])
    ax.tick_params(axis="both", colors=COLORS["ink"])
    ax.xaxis.label.set_color(COLORS["ink"])
    ax.yaxis.label.set_color(COLORS["ink"])
    ax.title.set_color(COLORS["navy"])


def save_figure(fig: plt.Figure, path: Path, title: str) -> None:
    fig.patch.set_facecolor(COLORS["white"])
    fig.savefig(
        path,
        format="pdf",
        bbox_inches="tight",
        facecolor=COLORS["white"],
        edgecolor=COLORS["white"],
        transparent=False,
        metadata={"Title": title, "Creator": "build_paper_assets.py"},
    )
    plt.close(fig)
    if not path.is_file() or path.stat().st_size < 1000:
        raise AssetBuildError(f"figure was not written correctly: {path}")
    if path.read_bytes()[:4] != b"%PDF":
        raise AssetBuildError(f"figure is not a PDF: {path}")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def verify_balanced_tex(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(r"\begin{") != text.count(r"\end{"):
        raise AssetBuildError(f"unbalanced TeX environments in {path}")
    depth = 0
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise AssetBuildError(f"unbalanced closing brace in {path}")
    if depth != 0:
        raise AssetBuildError(f"unbalanced braces in {path}: depth={depth}")


def load_run(
    path: Path,
    *,
    name: str,
    expected_markets: Sequence[str],
    expected_missing_policy: str,
) -> RunData:
    if not path.is_dir():
        raise AssetBuildError(f"required run directory is missing: {path}")
    manifest_path = require_file(path / "run_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest.get("tag")) != path.name:
        raise AssetBuildError(
            f"{name} manifest tag {manifest.get('tag')!r} does not match directory {path.name!r}"
        )
    if sorted(manifest.get("markets", [])) != sorted(expected_markets):
        raise AssetBuildError(
            f"{name} markets are {manifest.get('markets')}, expected {list(expected_markets)}"
        )
    if manifest.get("missing_next_month_return_policy") != expected_missing_policy:
        raise AssetBuildError(
            f"{name} missing-return policy is {manifest.get('missing_next_month_return_policy')!r}, "
            f"expected {expected_missing_policy!r}"
        )
    output_hashes = manifest.get("output_sha256")
    if not isinstance(output_hashes, dict) or not output_hashes:
        raise AssetBuildError(f"{name} manifest lacks output_sha256")
    for filename, expected_hash in sorted(output_hashes.items()):
        output = require_file(path / filename)
        observed_hash = sha256_file(output)
        if observed_hash != expected_hash:
            raise AssetBuildError(
                f"{name} output hash mismatch for {filename}: {observed_hash} != {expected_hash}"
            )
    missing_manifest_hashes = sorted(set(RUN_CSV_FILES.values()) - set(output_hashes))
    if missing_manifest_hashes:
        raise AssetBuildError(
            f"{name} manifest does not hash required outputs: {missing_manifest_hashes}"
        )

    required_columns = {
        "primary": [
            "candidate_id",
            "status",
            "cost_bps_one_way",
            "alpha_annualized",
            "p_value_two_sided",
            "holm_p_value",
            "max_abs_t_p_value",
            "ci_low_annualized",
            "ci_high_annualized",
            "simultaneous_ci_low_annualized",
            "simultaneous_ci_high_annualized",
            "confirmed_alpha_at_least_2pp",
            "adjustment_input_p_value",
        ],
        "cost": [
            "candidate_id",
            "cost_bps_one_way",
            "status",
            "alpha_annualized",
            "p_value_two_sided",
        ],
        "metadata": [
            "candidate_id",
            "paper_ref",
            "paper_idea",
            "proxy_formula",
            "strategy",
            "replication_scope",
        ],
        "multiplicity": [
            "candidate_id",
            "adjustment_input_p_value",
            "holm_p_value",
            "bh_q_value",
            "by_q_value",
        ],
        "country": ["candidate_id", "market", "status", "alpha_annualized"],
        "loo": ["candidate_id", "excluded_market", "status", "alpha_annualized"],
        "turnover": [
            "candidate_id",
            "median_monthly_traded_notional",
            "gross_alpha_annualized",
            "alpha_break_even_cost_bps",
        ],
        "missing": [
            "market",
            "object_type",
            "object_id",
            "return_field",
            "mean_missing_return_gross_weight",
            "max_missing_return_gross_weight",
        ],
        "path_failures": [
            "market",
            "month",
            "candidate_id",
            "selected_sleeve",
            "observed_gross_return",
            "failure_total_return",
            "path_status",
        ],
    }
    frames: dict[str, pd.DataFrame] = {}
    for key, filename in RUN_CSV_FILES.items():
        columns = list(required_columns[key])
        # A one-market run has no meaningful leave-one-country-out regression;
        # the evaluator writes 62 explicit not-applicable rows without alpha
        # columns. Preserve those rows and normalize the unused numeric field.
        if key == "loo" and len(expected_markets) == 1:
            columns.remove("alpha_annualized")
        frame = read_csv(path / filename, columns)
        if key == "loo" and "alpha_annualized" not in frame:
            frame["alpha_annualized"] = np.nan
        frames[key] = frame
    run = RunData(name=name, path=path, manifest=manifest, frames=frames)
    validate_run(run, expected_markets=expected_markets)
    return run


def load_fixed_calendar_diagnostics(path: Path, primary: RunData) -> tuple[pd.DataFrame, Path, Path]:
    csv_path = require_file(path / "fixed_calendar_country_loo.csv")
    manifest_path = require_file(path / "manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("classification") != "post_hoc_fixed_calendar_diagnostic":
        raise AssetBuildError("fixed-calendar diagnostic manifest has the wrong classification")
    if manifest.get("primary_analysis_lock_sha256") != primary.manifest.get("analysis_lock_sha256"):
        raise AssetBuildError("fixed-calendar diagnostic does not reference the primary analysis lock")
    expected_output = manifest.get("output_sha256", {}).get(csv_path.name)
    if expected_output != sha256_file(csv_path):
        raise AssetBuildError("fixed-calendar diagnostic output hash mismatch")
    expected_script = manifest.get("script_sha256")
    script_path = REPO_ROOT / "scripts" / "run_fixed_calendar_diagnostics.py"
    if expected_script != sha256_file(require_file(script_path)):
        raise AssetBuildError("fixed-calendar diagnostic script hash mismatch")
    for filename, expected_hash in manifest.get("input_sha256", {}).items():
        source = primary.path / filename
        if expected_hash != sha256_file(require_file(source)):
            raise AssetBuildError(f"fixed-calendar diagnostic input hash mismatch for {filename}")
    frame = read_csv(
        csv_path,
        [
            "diagnostic",
            "market",
            "excluded_market",
            "candidate_id",
            "n_months",
            "start",
            "end",
            "alpha_annualized",
            "status",
        ],
    )
    if len(frame) != 351 or not frame["status"].astype(str).eq("ok").all():
        raise AssetBuildError("fixed-calendar diagnostic does not contain 351 successful rows")
    if set(pd.to_numeric(frame["n_months"], errors="coerce")) != {281, 293}:
        raise AssetBuildError("fixed-calendar diagnostic does not use the expected 293/281-month calendars")
    country = frame.loc[frame["diagnostic"] == "country_fixed_primary_calendar"]
    loo = frame.loc[frame["diagnostic"] == "loo_fixed_primary_calendar"]
    transport = frame.loc[frame["diagnostic"] == "g7_usa_common_calendar"]
    if len(country) != 162 or len(loo) != 162 or len(transport) != 27:
        raise AssetBuildError("fixed-calendar diagnostic panels are incomplete")
    return frame, csv_path, manifest_path


def validate_run(run: RunData, *, expected_markets: Sequence[str]) -> None:
    primary = run.frame("primary")
    cost = run.frame("cost")
    metadata = run.frame("metadata")
    multiplicity = run.frame("multiplicity")
    country = run.frame("country")
    loo = run.frame("loo")
    path_failures = run.frame("path_failures")

    assert_unique(metadata, ["candidate_id"], f"{run.name} candidate metadata")
    assert_unique(primary, ["candidate_id"], f"{run.name} primary result")
    assert_unique(cost, ["candidate_id", "cost_bps_one_way"], f"{run.name} cost result")
    assert_unique(multiplicity, ["candidate_id"], f"{run.name} multiplicity")
    assert_unique(country, ["candidate_id", "market"], f"{run.name} country result")
    assert_unique(loo, ["candidate_id", "excluded_market"], f"{run.name} LOO result")

    ids = set(metadata["candidate_id"].astype(str))
    if len(ids) != 62:
        raise AssetBuildError(f"{run.name} has {len(ids)} candidates, expected exactly 62")
    for key in ("primary", "multiplicity"):
        observed = set(run.frame(key)["candidate_id"].astype(str))
        if observed != ids:
            raise AssetBuildError(f"{run.name} {key} IDs differ from the frozen family")
    cost_values = sorted(pd.to_numeric(cost["cost_bps_one_way"], errors="coerce").dropna().unique())
    if cost_values != [0, 5, 10, 25, 50] or len(cost) != 62 * 5:
        raise AssetBuildError(
            f"{run.name} cost grid/row count is invalid: costs={cost_values}, rows={len(cost)}"
        )
    if not (pd.to_numeric(primary["cost_bps_one_way"], errors="coerce") == 10).all():
        raise AssetBuildError(f"{run.name} primary results are not uniformly at 10 bps")

    ok = successful(primary)
    bad = failed(primary)
    if ok.empty:
        raise AssetBuildError(f"{run.name} has no successful candidate estimate")
    for column in (
        "alpha_annualized",
        "p_value_two_sided",
        "holm_p_value",
        "max_abs_t_p_value",
        "ci_low_annualized",
        "ci_high_annualized",
        "simultaneous_ci_low_annualized",
        "simultaneous_ci_high_annualized",
    ):
        values = pd.to_numeric(ok[column], errors="coerce")
        if not np.isfinite(values).all():
            raise AssetBuildError(f"{run.name} successful rows have nonfinite {column}")
    if not bad.empty:
        alpha = pd.to_numeric(bad["alpha_annualized"], errors="coerce")
        if alpha.notna().any():
            raise AssetBuildError(
                f"{run.name} failed candidates contain numerical alpha estimates; failures cannot be zeros"
            )
        adjustment_input = pd.to_numeric(bad["adjustment_input_p_value"], errors="coerce")
        if adjustment_input.isna().any() or not np.isclose(adjustment_input, 1.0).all():
            raise AssetBuildError(f"{run.name} failed candidates are not retained with p=1")

    bootstrap = run.manifest.get("bootstrap", {})
    if int(bootstrap.get("n_candidates", -1)) != len(ok):
        raise AssetBuildError(
            f"{run.name} bootstrap candidate count {bootstrap.get('n_candidates')} != {len(ok)}"
        )
    if int(bootstrap.get("n_bootstrap", 0)) < 2000:
        raise AssetBuildError(f"{run.name} used fewer than 2,000 bootstrap draws")
    if int(bootstrap.get("block_length", -1)) != 6 or int(bootstrap.get("seed", -1)) != 20260802:
        raise AssetBuildError(f"{run.name} bootstrap block/seed differs from the protocol")
    n_months = pd.to_numeric(ok["n_months"], errors="coerce") if "n_months" in ok else pd.Series()
    if not n_months.empty and (
        n_months.nunique() != 1 or int(n_months.iloc[0]) != int(bootstrap.get("n_common_months", -1))
    ):
        raise AssetBuildError(f"{run.name} ordinary and bootstrap sample lengths differ")

    expected_market_set = set(expected_markets)
    if set(country["market"].astype(str)) != expected_market_set:
        raise AssetBuildError(f"{run.name} country-result markets differ from manifest markets")
    if len(country) != 62 * len(expected_market_set):
        raise AssetBuildError(f"{run.name} country-result row count is invalid")
    if len(expected_market_set) > 1:
        if set(loo["excluded_market"].astype(str)) != expected_market_set:
            raise AssetBuildError(f"{run.name} LOO markets differ from manifest markets")
        if len(loo) != 62 * len(expected_market_set):
            raise AssetBuildError(f"{run.name} LOO row count is invalid")
    else:
        if not loo["status"].astype(str).str.startswith("not_applicable:").all():
            raise AssetBuildError(f"{run.name} single-market LOO rows are not marked not applicable")

    path_failure_ids = set(path_failures["candidate_id"].astype(str))
    manifest_events = int(run.manifest.get("path_failure_events", -1))
    manifest_candidates = int(run.manifest.get("path_failure_candidates", -1))
    if manifest_events != len(path_failures) or manifest_candidates != len(path_failure_ids):
        raise AssetBuildError(
            f"{run.name} path-failure manifest counts disagree with candidate_path_failures.csv"
        )
    bankruptcy_ids = set(
        primary.loc[
            primary["status"].astype(str) == "failed:bankruptcy_nonpositive_nav", "candidate_id"
        ].astype(str)
    )
    if bankruptcy_ids != path_failure_ids:
        raise AssetBuildError(
            f"{run.name} primary bankruptcy IDs differ from path-failure event IDs"
        )


def load_static_inputs(
    registry_path: Path,
    audit_path: Path,
    audit_summary_path: Path,
    native_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    registry = pd.read_csv(require_file(registry_path), sep="|")
    audit = read_csv(
        audit_path,
        [
            "system_id",
            "system_name",
            "stratum",
            "main_FT",
            "public_artifact_listed",
            "reachability_outcome",
            "default_branch_head_shas",
            "observed_licenses",
            "static_fidelity_tier",
            "failure_category",
        ],
    )
    audit_summary = read_csv(
        audit_summary_path,
        ["group", "metric", "successes", "denominator", "proportion", "wilson_95_lower", "wilson_95_upper"],
    )
    native = read_csv(
        native_path,
        [
            "system_id",
            "native_task",
            "public_artifact_status",
            "static_tier",
            "native_dated_signal_or_return_shipped",
            "prespecified_G7_monthly_common_task_compatible",
            "blocking_stage",
            "evidence_url",
            "concise_evidence_note",
            "targeted_execution_audit_status",
            "fidelity_class",
        ],
    )
    required_registry = {
        "system_id",
        "system_name",
        "stratum",
        "main_FT",
        "primary_record",
        "official_artifact",
        "lineage_dedup_notes",
        "inclusion_exclusion_rationale",
    }
    missing = sorted(required_registry - set(registry.columns))
    if missing:
        raise AssetBuildError(f"registry omits required columns: {missing}")
    for frame, label in ((registry, "registry"), (audit, "artifact audit"), (native, "native ledger")):
        assert_unique(frame, ["system_id"], label)
    if len(registry) != 103 or set(registry["stratum"].value_counts().to_dict()) != {
        "F",
        "T",
        "B",
        "C",
        "M",
    }:
        raise AssetBuildError("registry does not contain the frozen 103-lineage five-stratum census")
    expected_counts = {"F": 29, "T": 38, "B": 23, "C": 5, "M": 8}
    if registry["stratum"].value_counts().to_dict() != expected_counts:
        raise AssetBuildError(f"registry stratum counts differ from the lock: {registry['stratum'].value_counts().to_dict()}")
    if set(audit["system_id"].astype(str)) != set(registry["system_id"].astype(str)):
        raise AssetBuildError("artifact audit IDs differ from the frozen registry")
    method_ids = set(registry.loc[registry["main_FT"] == "Y", "system_id"].astype(str))
    if len(method_ids) != 67 or set(native["system_id"].astype(str)) != method_ids:
        raise AssetBuildError("native ledger does not contain exactly the 67 F/T systems")

    audit_ft = audit.loc[audit["main_FT"] == "Y"]
    recomputed = {
        "public_artifact_listed": int((audit_ft["public_artifact_listed"] == "Y").sum()),
        "artifact_reachable_among_all": int((audit_ft["reachability_outcome"] == "reachable_all").sum()),
        "github_head_resolved_among_all": int(
            audit_ft["default_branch_head_shas"].fillna("").astype(str).str.strip().ne("").sum()
        ),
        "static_R2_or_R3_among_all": int(audit_ft["static_fidelity_tier"].isin(["R2", "R3"]).sum()),
        "static_R3_among_all": int((audit_ft["static_fidelity_tier"] == "R3").sum()),
    }
    summary_ft = audit_summary.loc[audit_summary["group"] == "F+T"].set_index("metric")
    for metric, observed in recomputed.items():
        if metric not in summary_ft.index or int(summary_ft.loc[metric, "successes"]) != observed:
            raise AssetBuildError(f"artifact summary disagrees with audit for {metric}")
        if int(summary_ft.loc[metric, "denominator"]) != 67:
            raise AssetBuildError(f"artifact summary denominator for {metric} is not 67")
    return registry, audit, audit_summary, native


def validate_cross_run(primary: RunData, adverse: RunData, usa: RunData) -> None:
    reference_ids = set(primary.frame("metadata")["candidate_id"].astype(str))
    reference_meta = primary.frame("metadata").sort_values("candidate_id").reset_index(drop=True)
    for run in (adverse, usa):
        if set(run.frame("metadata")["candidate_id"].astype(str)) != reference_ids:
            raise AssetBuildError(f"{run.name} candidate family differs from primary")
        observed_meta = run.frame("metadata").sort_values("candidate_id").reset_index(drop=True)
        columns = [
            "candidate_id",
            "paper_ref",
            "paper_idea",
            "proxy_formula",
            "strategy",
            "replication_scope",
        ]
        if not reference_meta[columns].fillna("").equals(observed_meta[columns].fillna("")):
            raise AssetBuildError(f"{run.name} candidate metadata differs from primary")
    lock_hashes = {
        str(run.manifest.get("analysis_lock_sha256")) for run in (primary, adverse, usa)
    }
    if len(lock_hashes) != 1 or "None" in lock_hashes:
        raise AssetBuildError(f"analysis lock hashes differ across runs: {lock_hashes}")
    for key in ("formation_start", "formation_end", "top_n", "quantile", "min_side"):
        values = {json.dumps(run.manifest.get(key), sort_keys=True) for run in (primary, adverse, usa)}
        if len(values) != 1:
            raise AssetBuildError(f"run manifests disagree on {key}: {values}")


class MacroBook:
    def __init__(self) -> None:
        self.macros: dict[str, str] = {}
        self.claims: list[Claim] = []

    def add(
        self,
        name: str,
        value: str | int,
        *,
        location: str,
        claim: str,
        sources: Sequence[Path],
        source_filter: str,
        source_columns: str,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z]+", name):
            raise AssetBuildError(f"invalid TeX control-word name: {name}")
        if name in self.macros:
            raise AssetBuildError(f"duplicate generated macro: {name}")
        rendered = str(value)
        self.macros[name] = rendered
        self.claims.append(
            Claim(
                claim_id=f"CLAIM-{len(self.claims) + 1:03d}",
                macro=name,
                manuscript_location=location,
                claim=claim,
                rendered_value=rendered,
                source_file=";".join(rel(path) for path in sources),
                source_filter=source_filter,
                source_columns=source_columns,
                source_sha256=";".join(sha256_file(require_file(path)) for path in sources),
                producing_script=rel(Path(__file__)),
            )
        )


def compute_metrics(
    *,
    registry: pd.DataFrame,
    audit: pd.DataFrame,
    native: pd.DataFrame,
    registry_path: Path,
    audit_path: Path,
    native_path: Path,
    primary: RunData,
    adverse: RunData,
    usa: RunData,
    fixed_calendar: pd.DataFrame,
    fixed_calendar_path: Path,
    fixed_calendar_manifest_path: Path,
) -> tuple[MacroBook, dict[str, Any]]:
    book = MacroBook()
    primary_result_path = primary.path / RUN_CSV_FILES["primary"]
    primary_cost_path = primary.path / RUN_CSV_FILES["cost"]
    primary_turnover_path = primary.path / RUN_CSV_FILES["turnover"]
    primary_missing_path = primary.path / RUN_CSV_FILES["missing"]
    country_path = fixed_calendar_path
    loo_path = fixed_calendar_path
    adverse_result_path = adverse.path / RUN_CSV_FILES["primary"]
    usa_result_path = usa.path / RUN_CSV_FILES["primary"]
    manifest_path = primary.path / "run_manifest.json"
    hac_sensitivity_path = primary.path / "hac_lag_sensitivity.csv"
    block_sensitivity_path = primary.path / "bootstrap_block_sensitivity.csv"

    system_count = int(len(registry))
    method_count = int((registry["main_FT"] == "Y").sum())
    book.add(
        "SystemCount",
        system_count,
        location="Abstract; Introduction; Conclusion",
        claim="Frozen named-system lineage count.",
        sources=[registry_path],
        source_filter="all registry rows",
        source_columns="system_id",
    )
    book.add(
        "MethodSystemCount",
        method_count,
        location="Abstract; Artifact Audit; Conclusion",
        claim="Formula-discovery and trading-system denominator.",
        sources=[registry_path],
        source_filter="main_FT == Y",
        source_columns="system_id, main_FT",
    )

    audit_ft = audit.loc[audit["main_FT"] == "Y"].copy()
    artifact_count = int((audit_ft["public_artifact_listed"] == "Y").sum())
    reachable_count = int((audit_ft["reachability_outcome"] == "reachable_all").sum())
    licenses = audit_ft["observed_licenses"].fillna("").astype(str).str.strip()
    licensed_count = int((licenses.ne("") & ~licenses.str.contains("NOASSERTION", case=False)).sum())
    pinned = audit_ft["default_branch_head_shas"].fillna("").astype(str).str.strip()
    pinned_count = int(pinned.ne("").sum())
    artifact_rate = artifact_count / method_count
    artifact_wilson = wilson_interval(artifact_count, method_count)
    tiers = audit_ft["static_fidelity_tier"].value_counts().reindex(["R0", "R1", "R2", "R3"], fill_value=0)
    tier_text = ", ".join(rf"\artifacttier{{{tier}}}: {int(tiers[tier])}" for tier in tiers.index)
    artifact_specs = [
        (
            "ArtifactCountFT",
            artifact_count,
            "Systems in the F/T denominator listing at least one public artifact.",
            "public_artifact_listed == Y",
            "system_id, public_artifact_listed",
        ),
        (
            "ArtifactRateFT",
            fmt_percent(artifact_rate, 1),
            "Listed-public-artifact proportion in the unchanged F/T denominator.",
            "main_FT == Y and public_artifact_listed == Y",
            "public_artifact_listed",
        ),
        (
            "ArtifactWilsonFT",
            fmt_interval(*artifact_wilson),
            "Wilson 95 percent interval for the listed-artifact proportion.",
            "Wilson score interval for ArtifactCountFT / MethodSystemCount",
            "public_artifact_listed",
        ),
        (
            "ReachableArtifactCountFT",
            reachable_count,
            "F/T systems with a reachable artifact at the frozen audit.",
            "main_FT == Y and reachability_outcome == reachable_all",
            "reachability_outcome",
        ),
        (
            "LicensedArtifactCountFT",
            licensed_count,
            "F/T systems with a nonempty observed license other than NOASSERTION.",
            "observed_licenses nonempty and excludes NOASSERTION",
            "observed_licenses",
        ),
        (
            "PinnedRepoCountFT",
            pinned_count,
            "F/T systems whose listed repository could be revision pinned.",
            "default_branch_head_shas nonempty",
            "default_branch_head_shas",
        ),
        (
            "ArtifactTierSummaryFT",
            tier_text,
            "Static evidence-tier distribution for the F/T denominator.",
            "main_FT == Y grouped by static_fidelity_tier",
            "static_fidelity_tier",
        ),
    ]
    for name, value, claim, source_filter, columns in artifact_specs:
        book.add(
            name,
            value,
            location="Abstract; Artifact Audit",
            claim=claim,
            sources=[audit_path],
            source_filter=source_filter,
            source_columns=columns,
        )

    native_count = int((native["prespecified_G7_monthly_common_task_compatible"] == "Y").sum())
    native_dated_count = int((native["native_dated_signal_or_return_shipped"] == "Y").sum())
    targeted_count = int(
        native["targeted_execution_audit_status"]
        .astype(str)
        .ne("not_targeted_in_legacy_execution_audit")
        .sum()
    )
    translatable_count = int(
        native["targeted_execution_audit_status"].astype(str).str.contains("seed_idea_proxy").sum()
    )
    native_specs = [
        (
            "NativeDatedOutputCount",
            native_dated_count,
            "Systems whose frozen public materials ship some dated native signal or return output, irrespective of common-task compatibility.",
            "native_dated_signal_or_return_shipped == Y",
        ),
        (
            "NativeReturnCount",
            native_count,
            "Native dated streams compatible with the prespecified six-country monthly common task.",
            "prespecified_G7_monthly_common_task_compatible == Y",
        ),
        (
            "NativeUnavailableCount",
            method_count - native_count,
            "F/T systems without an identified native compatible common-task stream.",
            "prespecified_G7_monthly_common_task_compatible != Y",
        ),
        (
            "TargetedAuditCount",
            targeted_count,
            "Systems examined in the earlier targeted execution audit.",
            "targeted_execution_audit_status != not_targeted_in_legacy_execution_audit",
        ),
        (
            "TranslatableSeedCount",
            translatable_count,
            "Targeted artifacts explicitly classified as proxy seed ideas rather than native execution.",
            "targeted_execution_audit_status contains seed_idea_proxy",
        ),
    ]
    for name, value, claim, source_filter in native_specs:
        book.add(
            name,
            value,
            location="Abstract; Artifact Audit",
            claim=claim,
            sources=[native_path],
            source_filter=source_filter,
            source_columns="system_id, prespecified_G7_monthly_common_task_compatible, targeted_execution_audit_status",
        )

    metadata = primary.frame("metadata")
    proxy_count = int(metadata["candidate_id"].nunique())
    book.add(
        "ProxyCount",
        proxy_count,
        location="Abstract; Common-Task Design; Results; Conclusion",
        claim="Frozen mechanism-inspired proxy-family size, including failed paths.",
        sources=[primary.path / RUN_CSV_FILES["metadata"]],
        source_filter="all candidate IDs",
        source_columns="candidate_id",
    )

    lock_hash = str(primary.manifest["analysis_lock_sha256"])
    book.add(
        "AnalysisLockShort",
        latex_escape(lock_hash[:12]),
        location="Common-Task Design",
        claim="Abbreviated amended analysis-lock SHA-256.",
        sources=[manifest_path],
        source_filter="manifest field",
        source_columns="analysis_lock_sha256",
    )
    bootstrap = primary.manifest["bootstrap"]
    book.add(
        "BootstrapCount",
        int(bootstrap["n_bootstrap"]),
        location="Dependence and Multiple Testing; Protocol Appendix",
        claim="Executed primary circular-block bootstrap replication count.",
        sources=[manifest_path],
        source_filter="bootstrap metadata",
        source_columns="bootstrap.n_bootstrap",
    )
    deviation = (
        "Two post-lock evaluator amendments are disclosed: Amendment~1 was a post-outcome correctness repair for "
        "formation availability, drift, country pooling, and common-calendar defects; "
        "Amendment~2 was a subsequent post-runtime complete-path limited-liability rule after a nonpositive-NAV "
        "runtime failure. Superseded outputs are archived and excluded."
    )
    book.add(
        "ProtocolDeviationStatement",
        deviation,
        location="Protocol Appendix",
        claim="Disclosure of the post-outcome correctness repair and subsequent post-runtime path amendment.",
        sources=[manifest_path],
        source_filter="amended lock used by completed run",
        source_columns="analysis_lock_sha256, analysis_lock_created_at_utc, limited_liability_policy",
    )

    primary_frame = primary.frame("primary").merge(
        metadata.drop_duplicates("candidate_id"), on="candidate_id", how="left", suffixes=("", "_meta")
    )
    primary_ok = successful(primary_frame)
    primary_bad = failed(primary_frame)
    alpha = finite_values(primary_ok["alpha_annualized"], "primary alpha")
    q1, median_alpha, q3 = np.quantile(alpha, [0.25, 0.5, 0.75])
    positive_count = int((pd.to_numeric(primary_ok["alpha_annualized"]) > 0).sum())
    nominal_count = int(
        ((pd.to_numeric(primary_ok["alpha_annualized"]) > 0) & (pd.to_numeric(primary_ok["p_value_two_sided"]) <= 0.05)).sum()
    )
    holm_count = int(
        ((pd.to_numeric(primary_ok["alpha_annualized"]) > 0) & (pd.to_numeric(primary_ok["holm_p_value"]) <= 0.05)).sum()
    )
    bh_count = int(
        ((pd.to_numeric(primary_ok["alpha_annualized"]) > 0) & (pd.to_numeric(primary_ok["bh_q_value"]) <= 0.05)).sum()
    )
    by_count = int(
        ((pd.to_numeric(primary_ok["alpha_annualized"]) > 0) & (pd.to_numeric(primary_ok["by_q_value"]) <= 0.05)).sum()
    )
    max_t_count = int(
        ((pd.to_numeric(primary_ok["alpha_annualized"]) > 0) & (pd.to_numeric(primary_ok["max_abs_t_p_value"]) <= 0.05)).sum()
    )
    economic_count = int((pd.to_numeric(primary_ok["simultaneous_ci_low_annualized"]) >= 0.02).sum())
    valid_count = int(len(primary_ok))
    regression_months = sorted(pd.to_numeric(primary_ok["n_months"], errors="coerce").dropna().unique())
    regression_starts = sorted(pd.to_datetime(primary_ok["start"], errors="coerce").dropna().unique())
    regression_ends = sorted(pd.to_datetime(primary_ok["end"], errors="coerce").dropna().unique())
    if len(regression_months) != 1 or len(regression_starts) != 1 or len(regression_ends) != 1:
        raise AssetBuildError("executable primary paths do not share one regression sample")
    regression_month_count = int(regression_months[0])
    regression_start = pd.Timestamp(regression_starts[0]).strftime("%B %Y")
    regression_end = pd.Timestamp(regression_ends[0]).strftime("%B %Y")

    hac_sensitivity = read_csv(
        hac_sensitivity_path,
        ["candidate_id", "fixed_hac_lags", "status", "alpha_annualized", "p_value_two_sided"],
    )
    expected_ok_ids = set(primary_ok["candidate_id"].astype(str))
    hac_rows: list[list[str]] = []
    hac_counts: dict[int, dict[str, int]] = {}
    for lag in (0, 3, 6, 12):
        frame = hac_sensitivity.loc[pd.to_numeric(hac_sensitivity["fixed_hac_lags"]) == lag].copy()
        if len(frame) != valid_count or set(frame["candidate_id"].astype(str)) != expected_ok_ids:
            raise AssetBuildError(f"HAC lag {lag} sensitivity does not contain the {valid_count} executable paths")
        if not frame["status"].astype(str).eq("ok").all():
            raise AssetBuildError(f"HAC lag {lag} sensitivity contains a non-ok row")
        alpha_lag = pd.to_numeric(frame["alpha_annualized"], errors="coerce").to_numpy(dtype=float)
        raw = pd.to_numeric(frame["p_value_two_sided"], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(alpha_lag).all() or not np.isfinite(raw).all():
            raise AssetBuildError(f"HAC lag {lag} sensitivity contains a nonfinite estimate")
        padded = np.concatenate([np.clip(raw, 0.0, 1.0), np.ones(62 - valid_count, dtype=float)])
        holm = multipletests(padded, alpha=0.05, method="holm")[1][:valid_count]
        bh = multipletests(padded, alpha=0.05, method="fdr_bh")[1][:valid_count]
        by = multipletests(padded, alpha=0.05, method="fdr_by")[1][:valid_count]
        positive = alpha_lag > 0
        counts = {
            "nominal": int((positive & (raw <= 0.05)).sum()),
            "holm": int((positive & (holm <= 0.05)).sum()),
            "bh": int((positive & (bh <= 0.05)).sum()),
            "by": int((positive & (by <= 0.05)).sum()),
        }
        hac_counts[lag] = counts
        hac_rows.append(
            [f"HAC lag {lag}", str(counts["nominal"]), str(counts["holm"]), str(counts["bh"]), str(counts["by"]), "---", "---"]
        )

    block_sensitivity = read_csv(
        block_sensitivity_path,
        [
            "candidate_id",
            "block_length",
            "bootstrap_alpha_point_monthly",
            "max_abs_t_p_value",
            "simultaneous_ci_low_annualized",
        ],
    )
    block_rows: list[list[str]] = []
    block_counts: dict[int, dict[str, int]] = {}
    for block_length in (3, 6, 12):
        if block_length == 6:
            frame = primary_ok[
                ["candidate_id", "alpha_monthly", "max_abs_t_p_value", "simultaneous_ci_low_annualized"]
            ].rename(columns={"alpha_monthly": "bootstrap_alpha_point_monthly"})
        else:
            frame = block_sensitivity.loc[
                pd.to_numeric(block_sensitivity["block_length"]) == block_length
            ].copy()
        if len(frame) != valid_count or set(frame["candidate_id"].astype(str)) != expected_ok_ids:
            raise AssetBuildError(
                f"block-length {block_length} sensitivity does not contain the {valid_count} executable paths"
            )
        point = pd.to_numeric(frame["bootstrap_alpha_point_monthly"], errors="coerce").to_numpy(dtype=float)
        max_t_p = pd.to_numeric(frame["max_abs_t_p_value"], errors="coerce").to_numpy(dtype=float)
        lower = pd.to_numeric(frame["simultaneous_ci_low_annualized"], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(point).all() or not np.isfinite(max_t_p).all() or not np.isfinite(lower).all():
            raise AssetBuildError(f"block-length {block_length} sensitivity contains a nonfinite estimate")
        counts = {
            "max_t": int(((point > 0) & (max_t_p <= 0.05)).sum()),
            "economic": int((lower >= 0.02).sum()),
        }
        block_counts[block_length] = counts
        block_rows.append(
            [f"Block {block_length}", "---", "---", "---", "---", str(counts["max_t"]), str(counts["economic"])]
        )
    best = primary_ok.loc[pd.to_numeric(primary_ok["alpha_annualized"]).idxmax()]
    worst = primary_ok.loc[pd.to_numeric(primary_ok["alpha_annualized"]).idxmin()]
    best_holm = float(best["holm_p_value"])
    best_max_t = float(best["max_abs_t_p_value"])
    def p_for_sentence(value: float) -> str:
        return "p<0.001" if value < 0.001 else f"p={value:.3f}"

    best_adjusted = (
        rf"Holm ${p_for_sentence(best_holm)}$ and max-$|t|$ ${p_for_sentence(best_max_t)}$"
        if min(best_holm, best_max_t) <= 0.05
        else (
            rf"not familywise significant (Holm ${p_for_sentence(best_holm)}$; "
            rf"max-$|t|$ ${p_for_sentence(best_max_t)}$)"
        )
    )
    reality_p = float(bootstrap["white_reality_check_style_p_value"])
    primary_specs = [
        ("ValidProxyCount", valid_count, "Candidates with finite complete-path primary estimates.", "status == ok", "status"),
        ("MedianAlphaPct", fmt_pp(median_alpha), "Median annualized 10-bp alpha among successful paths.", "status == ok", "alpha_annualized"),
        ("AlphaIQRPct", fmt_interval(q1, q3), "Interquartile range of annualized 10-bp alpha among successful paths.", "status == ok", "alpha_annualized"),
        ("PositiveAlphaCount", positive_count, "Successful candidates with positive point alpha.", "status == ok and alpha_annualized > 0", "alpha_annualized"),
        ("NominalPositiveCount", nominal_count, "Positive-alpha candidates with nominal two-sided HAC p <= 0.05.", "status == ok, alpha > 0, p_value_two_sided <= .05", "alpha_annualized, p_value_two_sided"),
        ("HolmPositiveCount", holm_count, "Positive-alpha candidates surviving Holm at 5 percent.", "status == ok, alpha > 0, holm_p_value <= .05", "alpha_annualized, holm_p_value"),
        ("BHPositiveCount", bh_count, "Positive-alpha candidates surviving Benjamini--Hochberg at 5 percent.", "status == ok, alpha > 0, bh_q_value <= .05", "alpha_annualized, bh_q_value"),
        ("BYPositiveCount", by_count, "Positive-alpha candidates surviving Benjamini--Yekutieli at 5 percent.", "status == ok, alpha > 0, by_q_value <= .05", "alpha_annualized, by_q_value"),
        ("MaxTPositiveCount", max_t_count, "Positive-alpha candidates surviving paired max-|t| adjustment at 5 percent.", "status == ok, alpha > 0, max_abs_t_p_value <= .05", "alpha_annualized, max_abs_t_p_value"),
        ("EconomicConfirmedCount", economic_count, "Candidates whose simultaneous alpha lower bound is at least two percentage points.", "status == ok and simultaneous_ci_low_annualized >= .02", "simultaneous_ci_low_annualized"),
        ("RealityCheckP", fmt_p(reality_p), "One-sided reality-check-inspired global maximum-t p-value.", "bootstrap metadata", "white_reality_check_style_p_value"),
        ("RegressionMonthCount", regression_month_count, "Month count in the complete executable-candidate regression calendar.", "status == ok; common n_months", "n_months"),
        ("RegressionStartMonth", regression_start, "First month in the complete executable-candidate regression calendar.", "status == ok; common start", "start"),
        ("RegressionEndMonth", regression_end, "Last month in the complete executable-candidate regression calendar.", "status == ok; common end", "end"),
        ("BestAlphaPct", fmt_pp(float(best["alpha_annualized"])), "Largest successful primary point alpha.", f"candidate_id == {best['candidate_id']}", "alpha_annualized"),
        ("BestCandidateName", latex_escape(candidate_label(best)), "Label of the largest successful primary point alpha.", f"candidate_id == {best['candidate_id']}", "paper_ref, candidate_id"),
        ("BestAdjustedSummary", best_adjusted, "Familywise adjusted evidence for the point-alpha leader.", f"candidate_id == {best['candidate_id']}", "holm_p_value, max_abs_t_p_value"),
        ("WorstAlphaPct", fmt_pp(float(worst["alpha_annualized"])), "Smallest successful primary point alpha.", f"candidate_id == {worst['candidate_id']}", "alpha_annualized"),
        ("WorstCandidateName", latex_escape(candidate_label(worst)), "Label of the smallest successful primary point alpha.", f"candidate_id == {worst['candidate_id']}", "paper_ref, candidate_id"),
    ]
    for name, value, claim, source_filter, columns in primary_specs:
        sources = [manifest_path] if name == "RealityCheckP" else [primary_result_path]
        book.add(
            name,
            value,
            location="Abstract; International Proxy Performance",
            claim=claim,
            sources=sources,
            source_filter=source_filter,
            source_columns=columns,
        )

    hac_summary = (
        "Across fixed HAC lags 0, 3, 6, and 12, nominal-positive counts are "
        + ", ".join(str(hac_counts[lag]["nominal"]) for lag in (0, 3, 6, 12))
        + "; Holm counts are "
        + ", ".join(str(hac_counts[lag]["holm"]) for lag in (0, 3, 6, 12))
        + "; BH counts are "
        + ", ".join(str(hac_counts[lag]["bh"]) for lag in (0, 3, 6, 12))
        + "; and BY counts are "
        + ", ".join(str(hac_counts[lag]["by"]) for lag in (0, 3, 6, 12))
        + ", respectively."
    )
    block_summary = (
        "At circular block lengths 3, 6, and 12 months, positive max-$|t|$ discovery counts are "
        + ", ".join(str(block_counts[length]["max_t"]) for length in (3, 6, 12))
        + ", while simultaneous 2-percentage-point confirmation counts are "
        + ", ".join(str(block_counts[length]["economic"]) for length in (3, 6, 12))
        + ", respectively."
    )
    book.add(
        "HACSensitivitySummary",
        hac_summary,
        location="Inference Robustness",
        claim="Positive-discovery counts under the prespecified fixed-HAC-lag sensitivity grid.",
        sources=[hac_sensitivity_path],
        source_filter="fixed_hac_lags in {0,3,6,12}; 35 failed hypotheses padded with p=1",
        source_columns="candidate_id, fixed_hac_lags, alpha_annualized, p_value_two_sided",
    )
    book.add(
        "BlockSensitivitySummary",
        block_summary,
        location="Inference Robustness",
        claim="Positive max-|t| and material-confirmation counts under the prespecified block-length grid.",
        sources=[primary_result_path, block_sensitivity_path],
        source_filter="block_length in {3,6,12}; executable paths only",
        source_columns=(
            "candidate_id, block_length, bootstrap_alpha_point_monthly, max_abs_t_p_value, "
            "simultaneous_ci_low_annualized"
        ),
    )

    path_failure_frame = primary.frame("path_failures")
    path_failure_candidates = int(path_failure_frame["candidate_id"].astype(str).nunique())
    path_failure_events = int(len(path_failure_frame))
    for name, value, claim, columns in (
        (
            "PathFailureCandidateCount",
            path_failure_candidates,
            "Unique candidates with at least one primary country-level limited-liability failure event.",
            "candidate_id",
        ),
        (
            "PathFailureEventCount",
            path_failure_events,
            "Primary country-level limited-liability failure-event count.",
            "candidate_id, market, month, failure_total_return",
        ),
    ):
        book.add(
            name,
            value,
            location="Abstract; International Proxy Performance; Path-Failure Appendix",
            claim=claim,
            sources=[primary.path / RUN_CSV_FILES["path_failures"]],
            source_filter="all recorded path_failure_event rows",
            source_columns=columns,
        )

    failure_count = int(len(primary_bad))
    if max_t_count > 0 or holm_count > 0:
        result_phrase = (
            f"{holm_count} Holm and {max_t_count} paired max-$|t|$ positive discoveries "
            f"among {valid_count} executable paths; {failure_count} failed paths remain in the "
            "62-hypothesis Holm/FDR families with $p=1$"
        )
    else:
        result_phrase = (
            f"no familywise-confirmed positive alpha among {valid_count} executable paths; "
            f"{failure_count} failed paths remain in the 62-hypothesis Holm/FDR families with $p=1$"
        )
    for name, location, claim in (
        ("ResultHeadline", "Introduction", "Calibrated headline for the common-task result."),
        ("ResultInterpretation", "Interpretation", "Calibrated interpretation of the common-task result."),
        ("ConclusionResult", "Conclusion", "Calibrated concluding statement for the locked evaluator."),
    ):
        book.add(
            name,
            result_phrase,
            location=location,
            claim=claim,
            sources=[primary_result_path],
            source_filter="62 planned rows; successful estimates summarized; failures retained at p=1",
            source_columns="status, alpha_annualized, holm_p_value, max_abs_t_p_value, adjustment_input_p_value",
        )

    cost = primary.frame("cost")
    cost_ok = successful(cost)
    cost_wide = cost_ok.pivot(index="candidate_id", columns="cost_bps_one_way", values="alpha_annualized")
    paired_cost = cost_wide.dropna(subset=[0, 10])
    if paired_cost.empty:
        raise AssetBuildError("no successful candidate has both 0-bp and 10-bp alpha")
    cost_drag = paired_cost[0] - paired_cost[10]
    turnover = primary.frame("turnover")
    turnover_ok = turnover.loc[turnover["candidate_id"].astype(str).isin(set(primary_ok["candidate_id"].astype(str)))]
    turnover_values = finite_values(turnover_ok["median_monthly_traded_notional"], "median turnover")
    tq1, tmedian, tq3 = np.quantile(turnover_values, [0.25, 0.5, 0.75])
    positive_gross = turnover_ok.loc[pd.to_numeric(turnover_ok["gross_alpha_annualized"], errors="coerce") > 0]
    break_even = pd.to_numeric(positive_gross["alpha_break_even_cost_bps"], errors="coerce")
    break_even_below_ten = int((break_even < 10).fillna(False).sum())
    cost_specs = [
        ("MedianTurnover", fmt_number(tmedian, 2), "Median candidate-level monthly traded notional among successful paths.", [primary_turnover_path], "primary-success candidate IDs", "median_monthly_traded_notional"),
        ("TurnoverIQR", f"{tq1:.2f}--{tq3:.2f}", "Interquartile range of monthly traded notional among successful paths.", [primary_turnover_path], "primary-success candidate IDs", "median_monthly_traded_notional"),
        ("MedianCostDragPct", fmt_pp(float(np.median(cost_drag))), "Median annualized alpha reduction from zero to 10 bps among paired successful paths.", [primary_cost_path], "status == ok at both cost 0 and cost 10", "cost_bps_one_way, alpha_annualized"),
        ("BreakEvenBelowTenCount", break_even_below_ten, "Positive-gross-alpha candidates with estimated break-even cost below 10 bps.", [primary_turnover_path], "gross_alpha_annualized > 0 and alpha_break_even_cost_bps < 10", "gross_alpha_annualized, alpha_break_even_cost_bps"),
        ("PositiveAtTwentyFive", int((pd.to_numeric(cost_ok.loc[cost_ok["cost_bps_one_way"] == 25, "alpha_annualized"]) > 0).sum()), "Positive successful point alphas at 25 bps.", [primary_cost_path], "status == ok, cost == 25, alpha > 0", "alpha_annualized"),
        ("PositiveAtFifty", int((pd.to_numeric(cost_ok.loc[cost_ok["cost_bps_one_way"] == 50, "alpha_annualized"]) > 0).sum()), "Positive successful point alphas at 50 bps.", [primary_cost_path], "status == ok, cost == 50, alpha > 0", "alpha_annualized"),
    ]
    for name, value, claim, sources, source_filter, columns in cost_specs:
        book.add(
            name,
            value,
            location="Turnover and Cost Sensitivity",
            claim=claim,
            sources=sources,
            source_filter=source_filter,
            source_columns=columns,
        )

    missing = primary.frame("missing")
    missing_candidates = missing.loc[
        (missing["object_type"].astype(str) == "candidate")
        & (missing["return_field"].astype(str) == "missing_excess_return_gross_weight")
    ].copy()
    missing_mean = finite_values(
        missing_candidates["mean_missing_return_gross_weight"], "candidate-country mean missing exposure"
    )
    missing_max = finite_values(
        missing_candidates["max_missing_return_gross_weight"], "candidate-country maximum missing exposure"
    )
    missing_specs = [
        ("MedianMissingExposure", fmt_percent(float(np.median(missing_mean)), 2), "Median candidate-country mean missing-excess-return exposure.", "object_type == candidate and return_field == missing_excess_return_gross_weight", "mean_missing_return_gross_weight"),
        ("MissingExposurePninetyfive", fmt_percent(float(np.quantile(missing_mean, 0.95)), 2), "95th percentile of candidate-country mean missing-excess-return exposure.", "object_type == candidate and return_field == missing_excess_return_gross_weight", "mean_missing_return_gross_weight"),
        ("MaxMissingExposure", fmt_percent(float(missing_max.max()), 2), "Largest single-month missing-excess-return gross exposure reported across candidate-country series.", "object_type == candidate and return_field == missing_excess_return_gross_weight", "max_missing_return_gross_weight"),
    ]
    for name, value, claim, source_filter, columns in missing_specs:
        book.add(
            name,
            value,
            location="Missing-Outcome Sensitivity",
            claim=claim,
            sources=[primary_missing_path],
            source_filter=source_filter,
            source_columns=columns,
        )

    adverse_ok = successful(adverse.frame("primary"))
    adverse_alpha = finite_values(adverse_ok["alpha_annualized"], "adverse alpha")
    adverse_specs = [
        ("AdverseMedianAlphaPct", fmt_pp(float(np.median(adverse_alpha))), "Median annualized alpha under the position-adverse missing-return policy among successful paths.", "status == ok", "alpha_annualized"),
        ("AdverseNominalPositiveCount", int(((pd.to_numeric(adverse_ok["alpha_annualized"]) > 0) & (pd.to_numeric(adverse_ok["p_value_two_sided"]) <= 0.05)).sum()), "Nominally significant positive adverse-policy alphas.", "status == ok, alpha > 0, nominal p <= .05", "alpha_annualized, p_value_two_sided"),
        ("AdverseHolmPositiveCount", int(((pd.to_numeric(adverse_ok["alpha_annualized"]) > 0) & (pd.to_numeric(adverse_ok["holm_p_value"]) <= 0.05)).sum()), "Holm-significant positive adverse-policy alphas.", "status == ok, alpha > 0, Holm p <= .05", "alpha_annualized, holm_p_value"),
        ("AdverseEconomicConfirmedCount", int((pd.to_numeric(adverse_ok["simultaneous_ci_low_annualized"]) >= 0.02).sum()), "Adverse-policy candidates with simultaneous lower alpha bound at least two percentage points.", "status == ok and simultaneous lower bound >= .02", "simultaneous_ci_low_annualized"),
    ]
    for name, value, claim, source_filter, columns in adverse_specs:
        book.add(
            name,
            value,
            location="Missing-Outcome Sensitivity",
            claim=claim,
            sources=[adverse_result_path],
            source_filter=source_filter,
            source_columns=columns,
        )

    markets = list(primary.manifest["markets"])
    country = fixed_calendar.loc[
        fixed_calendar["diagnostic"].astype(str) == "country_fixed_primary_calendar"
    ].copy()
    country_ok = successful(country)
    complete_country_ids = set(
        country_ok.groupby("candidate_id")["market"].nunique().loc[lambda values: values == len(markets)].index.astype(str)
    )
    if not complete_country_ids:
        raise AssetBuildError("no candidate has valid country estimates in all six primary markets")
    country_complete = country_ok.loc[country_ok["candidate_id"].astype(str).isin(complete_country_ids)]
    country_wide = country_complete.pivot(index="candidate_id", columns="market", values="alpha_annualized")
    positive_by_candidate = (country_wide > 0).sum(axis=1)
    country_medians = country_wide.median(axis=0)
    best_country = str(country_medians.idxmax())
    worst_country = str(country_medians.idxmin())

    loo = successful(
        fixed_calendar.loc[
            fixed_calendar["diagnostic"].astype(str) == "loo_fixed_primary_calendar"
        ].copy()
    )
    primary_alpha_by_id = primary_ok.set_index("candidate_id")["alpha_annualized"].astype(float)
    loo_shifts: dict[str, float] = {}
    for excluded, frame in loo.groupby("excluded_market"):
        series = frame.set_index("candidate_id")["alpha_annualized"].astype(float)
        common_ids = primary_alpha_by_id.index.intersection(series.index)
        if len(common_ids) == 0:
            raise AssetBuildError(f"no common successful candidates for LOO exclusion {excluded}")
        loo_shifts[str(excluded)] = float(
            series.loc[common_ids].median() - primary_alpha_by_id.loc[common_ids].median()
        )
    best_id = str(best["candidate_id"])
    best_loo = finite_values(
        loo.loc[loo["candidate_id"].astype(str) == best_id, "alpha_annualized"],
        "point-alpha leader leave-one-country-out estimates",
    )
    if len(best_loo) != len(markets):
        raise AssetBuildError("point-alpha leader lacks a valid LOO estimate for every country")
    country_specs = [
        ("MedianPositiveCountries", fmt_count(float(np.median(positive_by_candidate))), "Median number of positive country alphas for the fixed 27-candidate, 293-month diagnostic.", [country_path, fixed_calendar_manifest_path], "country_fixed_primary_calendar; all six markets", "diagnostic, market, candidate_id, alpha_annualized"),
        ("AllCountryPositiveCount", int((positive_by_candidate == len(markets)).sum()), "Candidates with positive alpha in every country on the fixed primary calendar.", [country_path, fixed_calendar_manifest_path], "country_fixed_primary_calendar and alpha > 0 in all six", "diagnostic, market, candidate_id, alpha_annualized"),
        ("NoCountryPositiveCount", int((positive_by_candidate == 0).sum()), "Candidates with no positive country alpha on the fixed primary calendar.", [country_path, fixed_calendar_manifest_path], "country_fixed_primary_calendar and no alpha > 0", "diagnostic, market, candidate_id, alpha_annualized"),
        ("BestCountry", latex_escape(best_country), "Country with the largest median alpha over the fixed 27-candidate, 293-month panel.", [country_path, fixed_calendar_manifest_path], "country_fixed_primary_calendar; grouped by market", "diagnostic, market, candidate_id, alpha_annualized"),
        ("WorstCountry", latex_escape(worst_country), "Country with the smallest median alpha over the fixed 27-candidate, 293-month panel.", [country_path, fixed_calendar_manifest_path], "country_fixed_primary_calendar; grouped by market", "diagnostic, market, candidate_id, alpha_annualized"),
        ("MaxLeaveOneOutMedianShiftPct", fmt_pp(max(abs(value) for value in loo_shifts.values())), "Largest absolute change in cross-candidate median alpha after a country is removed on the fixed primary calendar.", [primary_result_path, loo_path, fixed_calendar_manifest_path], "27 primary executable candidates; fixed 293-month calendar; each country exclusion", "diagnostic, candidate_id, excluded_market, alpha_annualized"),
        ("BestCandidateLooRangePct", fmt_interval(float(best_loo.min()), float(best_loo.max())), "Minimum-to-maximum fixed-calendar LOO alpha range for the pooled point-alpha leader.", [loo_path, fixed_calendar_manifest_path], f"loo_fixed_primary_calendar and candidate_id == {best_id}", "diagnostic, excluded_market, alpha_annualized"),
    ]
    for name, value, claim, sources, source_filter, columns in country_specs:
        book.add(
            name,
            value,
            location="Country Dispersion and Leave-One-Country-Out Stability",
            claim=claim,
            sources=sources,
            source_filter=source_filter,
            source_columns=columns,
        )

    usa_ok = successful(usa.frame("primary"))
    paired = primary_ok[["candidate_id", "alpha_annualized"]].merge(
        usa_ok[["candidate_id", "alpha_annualized"]],
        on="candidate_id",
        how="inner",
        suffixes=("_g7", "_usa"),
    )
    if len(paired) < 3:
        raise AssetBuildError("fewer than three paired successful U.S./G7 alpha estimates")
    spearman = float(paired[["alpha_annualized_g7", "alpha_annualized_usa"]].corr(method="spearman").iloc[0, 1])
    if not np.isfinite(spearman):
        raise AssetBuildError("U.S./G7 Spearman correlation is not finite")
    sign_agreement = int(
        (np.sign(paired["alpha_annualized_g7"]) == np.sign(paired["alpha_annualized_usa"])).sum()
    )
    usa_nominal = int(
        ((pd.to_numeric(usa_ok["alpha_annualized"]) > 0) & (pd.to_numeric(usa_ok["p_value_two_sided"]) <= 0.05)).sum()
    )
    shared_g7 = fixed_calendar.loc[
        fixed_calendar["diagnostic"].astype(str) == "g7_usa_common_calendar",
        ["candidate_id", "alpha_annualized", "p_value_two_sided"],
    ].copy()
    paired_same_window = shared_g7.merge(
        usa_ok[["candidate_id", "alpha_annualized"]],
        on="candidate_id",
        how="inner",
        suffixes=("_g7", "_usa"),
    )
    if len(paired_same_window) != len(paired):
        raise AssetBuildError("same-window U.S./G7 diagnostic does not contain all jointly estimable candidates")
    same_window_spearman = float(
        paired_same_window[["alpha_annualized_g7", "alpha_annualized_usa"]]
        .corr(method="spearman")
        .iloc[0, 1]
    )
    same_window_sign_agreement = int(
        (
            np.sign(paired_same_window["alpha_annualized_g7"])
            == np.sign(paired_same_window["alpha_annualized_usa"])
        ).sum()
    )
    same_window_g7_nominal = int(
        (
            (pd.to_numeric(shared_g7["alpha_annualized"]) > 0)
            & (pd.to_numeric(shared_g7["p_value_two_sided"]) <= 0.05)
        ).sum()
    )
    usa_specs = [
        ("JointlyEstimableCount", len(paired), "Candidates with successful alpha estimates in both U.S. and G7 runs.", "status == ok in both runs; inner join by candidate_id", "candidate_id, status"),
        ("USGSevenSpearman", f"{spearman:.3f}", "Spearman correlation of paired successful U.S. and G7 annualized alphas.", "status == ok in both runs; inner join by candidate_id", "candidate_id, alpha_annualized"),
        ("SignAgreementCount", f"{sign_agreement} of {len(paired)}", "Same-sign alpha count among paired successful U.S./G7 candidates.", "status == ok in both runs; signs compared", "candidate_id, alpha_annualized"),
        ("USNominalPositiveCount", usa_nominal, "Successful U.S. candidates with positive alpha and nominal HAC p <= .05.", "status == ok, alpha > 0, nominal p <= .05", "alpha_annualized, p_value_two_sided"),
        ("SameWindowUSGSevenSpearman", f"{same_window_spearman:.3f}", "Spearman correlation of U.S. and G7 alphas on their common 281-month calendar.", "g7_usa_common_calendar joined to successful U.S. rows", "candidate_id, alpha_annualized"),
        ("SameWindowSignAgreementCount", f"{same_window_sign_agreement} of {len(paired_same_window)}", "Same-sign U.S./G7 alpha count on the common 281-month calendar.", "g7_usa_common_calendar joined to successful U.S. rows; signs compared", "candidate_id, alpha_annualized"),
        ("SameWindowGSevenNominalPositiveCount", same_window_g7_nominal, "Positive nominally significant G7 alphas on the U.S. 281-month comparison calendar.", "g7_usa_common_calendar, alpha > 0, nominal p <= .05", "candidate_id, alpha_annualized, p_value_two_sided"),
    ]
    for name, value, claim, source_filter, columns in usa_specs:
        book.add(
            name,
            value,
            location="Retrospective U.S. Comparison",
            claim=claim,
            sources=(
                [usa_result_path]
                if name == "USNominalPositiveCount"
                else (
                    [fixed_calendar_path, fixed_calendar_manifest_path, usa_result_path]
                    if name.startswith("SameWindow")
                    else [primary_result_path, usa_result_path]
                )
            ),
            source_filter=source_filter,
            source_columns=columns,
        )

    if set(book.macros) != EXPECTED_MACROS:
        raise AssetBuildError(
            f"generated macro interface mismatch: missing={sorted(EXPECTED_MACROS - set(book.macros))}, "
            f"extra={sorted(set(book.macros) - EXPECTED_MACROS)}"
        )
    context = {
        "audit_ft": audit_ft,
        "artifact_tiers": tiers,
        "primary_frame": primary_frame,
        "primary_ok": primary_ok,
        "primary_bad": primary_bad,
        "best": best,
        "worst": worst,
        "cost": cost,
        "cost_wide": cost_wide,
        "turnover": turnover,
        "missing_candidates": missing_candidates,
        "adverse_ok": adverse_ok,
        "country": country,
        "country_wide": country_wide,
        "complete_country_ids": complete_country_ids,
        "loo": loo,
        "loo_shifts": loo_shifts,
        "paired_usa_g7": paired,
        "spearman": spearman,
        "paired_usa_g7_same_window": paired_same_window,
        "same_window_spearman": same_window_spearman,
        "markets": markets,
        "metadata": metadata,
        "inference_sensitivity_rows": hac_rows + block_rows,
    }
    return book, context


def longtable_tex(
    *,
    caption: str,
    label: str,
    column_spec: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    note: str,
    font_size: str = r"\scriptsize",
) -> str:
    header = " & ".join(rf"\color{{Navy}}\textbf{{{latex_escape(item)}}}" for item in headers) + r" \\"
    body = [
        r"\begingroup",
        r"\color{Ink}",
        r"\setlength{\tabcolsep}{1.5pt}",
        r"\renewcommand{\arraystretch}{1.10}",
        font_size,
        rf"\begin{{longtable}}{{@{{}}{column_spec}@{{}}}}",
        rf"\caption{{{caption}}}\label{{{label}}}\\",
        r"\toprule",
        header,
        r"\midrule",
        r"\endfirsthead",
        rf"\multicolumn{{{len(headers)}}}{{l}}{{\color{{Navy}}\emph{{Continued from previous page}}}}\\",
        r"\toprule",
        header,
        r"\midrule",
        r"\endhead",
        rf"\midrule\multicolumn{{{len(headers)}}}{{r}}{{\color{{Ink}}\emph{{Continued on next page}}}}\\",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
    ]
    body.extend(" & ".join(row) + r" \\" for row in rows)
    body.extend(
        [
            r"\end{longtable}",
            rf"\par\footnotesize\color{{Ink}}\emph{{Note:}} {note}",
            r"\endgroup",
        ]
    )
    return "\n".join(body)


def regular_table_tex(
    *,
    caption: str,
    label: str,
    column_spec: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    note: str,
) -> str:
    header = " & ".join(rf"\color{{Navy}}\textbf{{{latex_escape(item)}}}" for item in headers) + r" \\"
    body = [
        r"\begin{table}[H]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        r"\begingroup",
        r"\color{Ink}",
        r"\small",
        rf"\begin{{tabular}}{{{column_spec}}}",
        r"\toprule",
        header,
        r"\midrule",
    ]
    body.extend(" & ".join(row) + r" \\" for row in rows)
    body.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            rf"\par\vspace{{0.25em}}\footnotesize\color{{Ink}}\emph{{Note:}} {note}",
            r"\endgroup",
            r"\end{table}",
        ]
    )
    return "\n".join(body)


def build_inference_sensitivity_table(rows: Sequence[Sequence[str]], path: Path) -> None:
    tex = regular_table_tex(
        caption="Prespecified inference sensitivity across HAC lags and circular block lengths.",
        label="tab:inference-sensitivity",
        column_spec="lrrrrrr",
        headers=["Specification", "Nominal +", "Holm +", "BH +", "BY +", "Max-|t| +", "2pp LB"],
        rows=rows,
        note=(
            "Counts require a positive point alpha. HAC rows recompute two-sided p-values and pad the 27 "
            "estimable hypotheses with 35 p=1 failures before Holm, BH, and BY adjustment. Block rows apply "
            "paired max-|t| inference to the 27 estimable paths; 2pp LB counts simultaneous lower bounds at "
            "or above two percentage points. Dashes denote a procedure not defined for that sensitivity row."
        ),
    )
    write_text(path, tex)


def write_generated_results(book: MacroBook, path: Path) -> None:
    lines = [
        "% Generated by scripts/build_paper_assets.py; do not edit by hand.",
        "% Values are computed only from validated, hashed inputs.",
    ]
    for name in sorted(book.macros):
        lines.append(rf"\newcommand{{\{name}}}{{{book.macros[name]}}}")
    write_text(path, "\n".join(lines))


def write_claims(book: MacroBook, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(Claim.__dataclass_fields__)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for claim in book.claims:
            writer.writerow({field: getattr(claim, field) for field in fields})


def build_artifact_summary_table(
    audit: pd.DataFrame,
    native: pd.DataFrame,
    path: Path,
) -> None:
    ft = audit.loc[audit["main_FT"] == "Y"].copy()
    licenses = ft["observed_licenses"].fillna("").astype(str).str.strip()
    stages = [
        ("Public artifact listed", int((ft["public_artifact_listed"] == "Y").sum())),
        ("Artifact reachable", int((ft["reachability_outcome"] == "reachable_all").sum())),
        ("Observed reuse license", int((licenses.ne("") & ~licenses.str.contains("NOASSERTION", case=False)).sum())),
        ("Git revision pinned", int(ft["default_branch_head_shas"].fillna("").astype(str).str.strip().ne("").sum())),
    ]
    for tier in ("R0", "R1", "R2", "R3"):
        stages.append((f"Static tier {tier}", int((ft["static_fidelity_tier"] == tier).sum())))
    stages.extend(
        [
            ("Native dated output shipped", int((native["native_dated_signal_or_return_shipped"] == "Y").sum())),
            (
                "Native G7 common-task compatible",
                int((native["prespecified_G7_monthly_common_task_compatible"] == "Y").sum()),
            ),
        ]
    )
    rows = []
    for label, count in stages:
        low, high = wilson_interval(count, 67)
        rows.append(
            [
                latex_escape(label),
                str(count),
                "67",
                fmt_percent(count / 67, 1),
                fmt_interval(low, high),
            ]
        )
    tex = regular_table_tex(
        caption=(
            "Public-evidence availability in the fixed formula-discovery and trading-system denominator."
        ),
        label="tab:artifact-summary",
        column_spec="lrrrr",
        headers=["Observable stage", "Count", "Denom.", "Rate", "Wilson 95% CI"],
        rows=rows,
        note=(
            "Every rate retains all 67 F/T systems in its denominator. Static tiers describe visible "
            "packaging, not execution quality. Unavailable native streams are evidence states and are never returns."
        ),
    )
    write_text(path, tex)


def build_primary_results_table(primary_frame: pd.DataFrame, path: Path) -> None:
    frame = primary_frame.copy()
    frame["_sort_alpha"] = pd.to_numeric(frame["alpha_annualized"], errors="coerce")
    frame["_ok"] = frame["status"].astype(str).eq("ok")
    frame = pd.concat(
        [
            frame.loc[frame["_ok"]].sort_values("_sort_alpha", ascending=False),
            frame.loc[~frame["_ok"]].sort_values("candidate_id"),
        ]
    )
    rows: list[list[str]] = []
    for _, row in frame.iterrows():
        label = latex_escape(candidate_label(row))
        if row["status"] != "ok":
            status = "path failure"
            rows.append([label, status, "---", "---", "---", "1.000", "1.000", "1.000", "---", "---"])
            continue
        material = "Yes" if float(row["simultaneous_ci_low_annualized"]) >= 0.02 else "No"
        rows.append(
            [
                label,
                "ok",
                fmt_pp(float(row["alpha_annualized"])),
                fmt_interval(float(row["ci_low_annualized"]), float(row["ci_high_annualized"])),
                fmt_p(float(row["p_value_two_sided"])),
                fmt_p(float(row["holm_p_value"])),
                fmt_p(float(row["bh_q_value"])),
                fmt_p(float(row["by_q_value"])),
                fmt_p(float(row["max_abs_t_p_value"])),
                material,
            ]
        )
    tex = longtable_tex(
        caption=(
            "G7 ex-U.S. equal-country factor alpha net of 10-basis-point one-way costs for the complete frozen family."
        ),
        label="tab:primary-results",
        column_spec="L{0.22\\linewidth}L{0.11\\linewidth}rrrrrrrr",
        headers=["Proxy/source", "Path status", "Alpha", "HAC 95% CI", "Raw p", "Holm p", "BH q", "BY q", "Max-|t| p", "2pp confirmed"],
        rows=rows,
        note=(
            "Alpha and intervals are annualized. Distribution summaries use only status-ok paths. "
            "A complete-path limited-liability failure has no alpha estimate, remains in the 62-hypothesis "
            "Holm/FDR families with adjustment input p=1, and is not displayed or summarized as a zero return. "
            "Paired bootstrap max-|t| values are defined only for executable paths. Proxy codes map to the frozen registry."
        ),
        font_size=r"\tiny",
    )
    write_text(path, tex)


def build_system_registry_table(registry: pd.DataFrame, path: Path) -> None:
    rows = []
    for _, row in registry.sort_values(["stratum", "system_name"]).iterrows():
        rows.append(
            [
                latex_escape_breakable(row["system_id"]),
                latex_escape(row["system_name"]),
                latex_escape(row["stratum"]),
                latex_escape(row["main_FT"]),
                latex_href(row["primary_record"], "record"),
                latex_href(row["official_artifact"], "artifact"),
                latex_escape(row["lineage_dedup_notes"]),
                latex_escape(row["inclusion_exclusion_rationale"]),
            ]
        )
    tex = longtable_tex(
        caption="Frozen registry of 103 named system lineages at the 2 August 2026 cutoff.",
        label="tab:system-registry",
        column_spec="L{0.12\\linewidth}L{0.14\\linewidth}L{0.05\\linewidth}L{0.04\\linewidth}L{0.06\\linewidth}L{0.07\\linewidth}L{0.22\\linewidth}L{0.25\\linewidth}",
        headers=["System ID", "Name", "Stratum", "F/T", "Record", "Artifact", "Lineage note", "Inclusion rationale"],
        rows=rows,
        note=(
            "The unit is a named lineage rather than a publication or repository. F/T marks membership in "
            "the primary 67-method denominator; B, C, and M are reported separately."
        ),
        font_size=r"\tiny",
    )
    write_text(path, tex)


def build_candidate_registry_table(metadata: pd.DataFrame, path: Path) -> None:
    rows = []
    codes = [candidate_label(row).split()[0] for _, row in metadata.iterrows()]
    if len(codes) != len(set(codes)):
        raise AssetBuildError("proxy-code collision in candidate registry")
    for _, row in metadata.sort_values("candidate_id").iterrows():
        raw_scope = row["replication_scope"]
        if raw_scope is None or (isinstance(raw_scope, float) and math.isnan(raw_scope)) or not str(raw_scope).strip():
            scope = "mechanism-inspired; scope field blank"
        else:
            scope = str(raw_scope)
        frozen_id = (
            rf"\textbf{{{latex_escape(candidate_label(row).split()[0])}}}: "
            + latex_escape_breakable(row["candidate_id"])
        )
        rows.append(
            [
                frozen_id,
                latex_escape(row["paper_ref"]),
                latex_escape(row["paper_idea"]),
                latex_escape_breakable(row["proxy_formula"]),
                latex_escape_breakable(row["strategy"]),
                latex_escape_breakable(scope),
            ]
        )
    tex = longtable_tex(
        caption="Frozen registry of 62 mechanism-inspired proxy portfolios.",
        label="tab:candidate-registry",
        column_spec="L{0.16\\linewidth}L{0.10\\linewidth}L{0.22\\linewidth}L{0.25\\linewidth}L{0.13\\linewidth}L{0.10\\linewidth}",
        headers=["Proxy / frozen candidate ID", "Source", "Mapped idea", "Frozen formula", "Portfolio rule", "Mapping scope"],
        rows=rows,
        note=(
            "These formulas are characteristic translations, not native agent outputs. Candidate formulas, "
            "signs, and portfolio rules were frozen before the geographic evaluation. Short proxy codes are "
            "deterministic labels for presentation. A blank frozen scope field is displayed explicitly and does "
            "not change the mechanism-inspired-proxy classification."
        ),
        font_size=r"\tiny",
    )
    write_text(path, tex)


def build_artifact_failure_table(
    native: pd.DataFrame,
    registry: pd.DataFrame,
    path: Path,
) -> None:
    names = registry[["system_id", "system_name", "stratum"]]
    frame = native.merge(names, on="system_id", how="left", validate="one_to_one")
    rows = []
    for _, row in frame.sort_values(["stratum", "system_name"]).iterrows():
        rows.append(
            [
                latex_escape(row["system_name"]),
                latex_escape_breakable(row["public_artifact_status"]),
                latex_escape(row["static_tier"]),
                latex_escape(row["native_dated_signal_or_return_shipped"]),
                latex_escape(row["prespecified_G7_monthly_common_task_compatible"]),
                latex_escape_breakable(row["blocking_stage"]),
                latex_escape_breakable(row["fidelity_class"]),
                latex_escape(row["concise_evidence_note"]),
                latex_href(row["evidence_url"], "evidence"),
            ]
        )
    tex = longtable_tex(
        caption="Native-output and compatibility ledger for all 67 primary F/T systems.",
        label="tab:artifact-failures",
        column_spec="L{0.13\\linewidth}L{0.11\\linewidth}L{0.04\\linewidth}L{0.05\\linewidth}L{0.05\\linewidth}L{0.13\\linewidth}L{0.12\\linewidth}L{0.25\\linewidth}L{0.06\\linewidth}",
        headers=["System", "Artifact state", "Tier", "Dated", "G7", "Blocking stage", "Fidelity", "Evidence", "Link"],
        rows=rows,
        note=(
            "A blocking stage records what is publicly identifiable at the frozen audit. It is not a zero "
            "return, not evidence that the private or later system cannot work, and not a quality score."
        ),
        font_size=r"\tiny",
    )
    write_text(path, tex)


def build_cost_table(
    cost: pd.DataFrame,
    turnover: pd.DataFrame,
    metadata: pd.DataFrame,
    path: Path,
) -> None:
    merged = cost.merge(metadata[["candidate_id", "paper_ref"]], on="candidate_id", how="left")
    alpha = merged.pivot(index="candidate_id", columns="cost_bps_one_way", values="alpha_annualized")
    status = merged.pivot(index="candidate_id", columns="cost_bps_one_way", values="status")
    turn = turnover.set_index("candidate_id")
    rows = []
    for candidate in metadata.sort_values("candidate_id")["candidate_id"]:
        label_row = metadata.loc[metadata["candidate_id"] == candidate].iloc[0]
        values = [latex_escape(candidate_label(label_row))]
        for bps in (0, 5, 10, 25, 50):
            if candidate in status.index and status.loc[candidate, bps] == "ok":
                values.append(fmt_pp(float(alpha.loc[candidate, bps])))
            else:
                values.append("---")
        if candidate in turn.index:
            values.extend(
                [
                    fmt_number(float(turn.loc[candidate, "median_monthly_traded_notional"]), 2),
                    fmt_number(float(turn.loc[candidate, "alpha_break_even_cost_bps"]), 1),
                ]
            )
        else:
            values.extend(["---", "---"])
        rows.append(values)
    tex = longtable_tex(
        caption="Prespecified one-way transaction-cost sensitivity of annualized factor alpha.",
        label="tab:cost-results",
        column_spec="L{0.25\\linewidth}rrrrrrr",
        headers=["Proxy/source", "0 bp", "5 bp", "10 bp", "25 bp", "50 bp", "Median turnover", "Break-even bp"],
        rows=rows,
        note=(
            "Cells are annualized alpha and use only finite status-ok estimates. Dashes are failed or unavailable "
            "paths, never zeros. Break-even cost is the zero of the alpha-versus-cost regression slope."
        ),
        font_size=r"\tiny",
    )
    write_text(path, tex)


def build_country_table(
    country: pd.DataFrame,
    loo: pd.DataFrame,
    metadata: pd.DataFrame,
    markets: Sequence[str],
    path: Path,
) -> None:
    country_alpha = successful(country).pivot(index="candidate_id", columns="market", values="alpha_annualized")
    loo_alpha = successful(loo).pivot(index="candidate_id", columns="excluded_market", values="alpha_annualized")
    rows = []
    diagnostic_ids = set(country_alpha.index.astype(str)) & set(loo_alpha.index.astype(str))
    for candidate in metadata.loc[metadata["candidate_id"].astype(str).isin(diagnostic_ids)].sort_values("candidate_id")["candidate_id"]:
        label_row = metadata.loc[metadata["candidate_id"] == candidate].iloc[0]
        values = [latex_escape(candidate_label(label_row))]
        valid_country_values = []
        for market in markets:
            value = float(country_alpha.loc[candidate, market]) if candidate in country_alpha.index and market in country_alpha.columns else np.nan
            values.append(fmt_pp(value))
            if np.isfinite(value):
                valid_country_values.append(value)
        if len(valid_country_values) == len(markets):
            values.append(str(sum(value > 0 for value in valid_country_values)))
        else:
            values.append(f"{len(valid_country_values)}/{len(markets)} valid")
        if candidate in loo_alpha.index:
            loo_values = finite_values(loo_alpha.loc[candidate], f"LOO values for {candidate}", allow_empty=True)
        else:
            loo_values = pd.Series(dtype=float)
        values.append(
            fmt_interval(float(loo_values.min()), float(loo_values.max())) if not loo_values.empty else "---"
        )
        rows.append(values)
    tex = longtable_tex(
        caption="Post-hoc fixed-primary-calendar country and leave-one-country-out alpha robustness at 10 basis points.",
        label="tab:country-results",
        column_spec="L{0.22\\linewidth}" + "r" * len(markets) + "rr",
        headers=["Proxy/source", *markets, "Positive", "LOO range"],
        rows=rows,
        note=(
            "Country and LOO cells are annualized alpha in the post-hoc fixed-calendar diagnostic. Every row "
            "uses the 27 primary executable candidates and the identical 293 months from August 2000 through "
            "December 2024. LOO results remove one country while holding candidate set and calendar fixed; they "
            "do not redefine the primary family."
        ),
        font_size=r"\tiny",
    )
    write_text(path, tex)


def build_path_failure_table(path_failures: pd.DataFrame, metadata: pd.DataFrame, path: Path) -> None:
    frame = path_failures.merge(
        metadata[["candidate_id", "paper_ref"]], on="candidate_id", how="left", validate="many_to_one"
    )
    frame["month"] = pd.to_datetime(frame["month"], errors="coerce")
    if frame["month"].isna().any():
        raise AssetBuildError("path-failure table contains an invalid month")
    rows = []
    for _, row in frame.sort_values(["month", "market", "candidate_id"]).iterrows():
        rows.append(
            [
                row["month"].strftime("%Y-%m"),
                latex_escape(row["market"]),
                latex_escape(candidate_label(row)),
                latex_escape_breakable(row["selected_sleeve"]),
                fmt_percent(float(row["observed_gross_return"]), 2),
                fmt_percent(float(row["failure_total_return"]), 2),
                latex_escape_breakable(row["path_status"]),
            ]
        )
    tex = longtable_tex(
        caption="Complete-path limited-liability failure events in the primary G7 evaluation.",
        label="tab:path-failures",
        column_spec="llL{0.22\\linewidth}L{0.23\\linewidth}rrL{0.15\\linewidth}",
        headers=["Month", "Market", "Candidate/source", "Selected sleeve", "Observed excess", "Total return", "Path status"],
        rows=rows,
        note=(
            "Each event has a realized total portfolio return at or below -100 percent. The corresponding "
            "candidate's complete pooled path is unavailable, is never restarted or recapitalized, and remains "
            "in the 62-hypothesis denominator with p=1. These rows are not zero returns."
        ),
        font_size=r"\tiny",
    )
    write_text(path, tex)


def build_claim_map_table(claims: Sequence[Claim], path: Path) -> None:
    rows = []
    for claim in claims:
        rows.append(
            [
                latex_escape_breakable(claim.claim_id),
                latex_escape_breakable(claim.macro),
                latex_escape(claim.claim),
                claim.rendered_value,
                latex_escape_breakable(claim.source_file),
                latex_escape_breakable(claim.source_filter),
                latex_escape_breakable(claim.review_status),
            ]
        )
    tex = longtable_tex(
        caption="Claim-to-output provenance for every generated manuscript macro.",
        label="tab:claim-map",
        column_spec="L{0.07\\linewidth}L{0.12\\linewidth}L{0.21\\linewidth}L{0.09\\linewidth}L{0.17\\linewidth}L{0.22\\linewidth}L{0.08\\linewidth}",
        headers=["Claim", "Macro", "Statement", "Value", "Source", "Exact filter", "Review"],
        rows=rows,
        note=(
            "The machine-readable claims.csv additionally records exact source columns and SHA-256 hashes. "
            "Owner review remains pending until the named author verifies every claim."
        ),
        font_size=r"\tiny",
    )
    write_text(path, tex)


def build_census_funnel_figure(
    registry: pd.DataFrame,
    audit: pd.DataFrame,
    native: pd.DataFrame,
    path: Path,
) -> None:
    method_count = int((registry["main_FT"] == "Y").sum())
    audit_ft = audit.loc[audit["main_FT"] == "Y"]
    counts = [
        ("Frozen\nlineages", len(registry), COLORS["navy"]),
        ("F/T methods", method_count, COLORS["blue"]),
        ("Artifact\nlisted", int((audit_ft["public_artifact_listed"] == "Y").sum()), COLORS["teal"]),
        ("Artifact\nreachable", int((audit_ft["reachability_outcome"] == "reachable_all").sum()), COLORS["teal"]),
        ("Any dated\nnative output", int((native["native_dated_signal_or_return_shipped"] == "Y").sum()), COLORS["gold"]),
        ("G7 common-task\ncompatible", int((native["prespecified_G7_monthly_common_task_compatible"] == "Y").sum()), COLORS["red"]),
    ]
    fig, ax = plt.subplots(figsize=(11.2, 3.8), facecolor=COLORS["white"])
    ax.set_facecolor(COLORS["white"])
    ax.axis("off")
    xs = np.linspace(0.02, 0.82, len(counts))
    width, height, y = 0.14, 0.48, 0.28
    for index, ((label, count, color), x) in enumerate(zip(counts, xs)):
        box = mpatches.FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            transform=ax.transAxes,
            facecolor=COLORS["panel"] if index not in (0, 1) else COLORS["white"],
            edgecolor=color,
            linewidth=2.0,
        )
        ax.add_patch(box)
        ax.text(
            x + width / 2,
            y + 0.32,
            str(count),
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=20,
            fontweight="bold",
            color=color,
        )
        ax.text(
            x + width / 2,
            y + 0.13,
            label,
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=9,
            color=COLORS["ink"],
        )
        if index < len(counts) - 1:
            ax.annotate(
                "",
                xy=(xs[index + 1] - 0.008, y + height / 2),
                xytext=(x + width + 0.008, y + height / 2),
                xycoords=ax.transAxes,
                arrowprops={"arrowstyle": "->", "color": COLORS["muted"], "linewidth": 1.4},
            )
    ax.text(
        0.5,
        0.92,
        "From census inclusion to a compatible native return stream",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["navy"],
    )
    ax.text(
        0.5,
        0.08,
        "Counts are evidence states. Attrition never assigns a missing system a zero return.",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9,
        color=COLORS["ink"],
    )
    save_figure(fig, path, "Census construction and empirical attrition")


def build_artifact_attrition_figure(audit: pd.DataFrame, path: Path) -> None:
    ft = audit.loc[audit["main_FT"] == "Y"].copy()
    groups = ["F", "T", "F+T"]
    tiers = ["R0", "R1", "R2", "R3"]
    values = []
    for group in groups:
        frame = ft if group == "F+T" else ft.loc[ft["stratum"] == group]
        values.append([int((frame["static_fidelity_tier"] == tier).sum()) for tier in tiers])
    tier_colors = ["#D9E0E7", "#9CB7CF", COLORS["blue"], COLORS["teal"]]
    fig, ax = plt.subplots(figsize=(9.6, 4.8), facecolor=COLORS["white"])
    style_axis(ax)
    y = np.arange(len(groups))
    left = np.zeros(len(groups))
    for tier_index, (tier, color) in enumerate(zip(tiers, tier_colors)):
        width = np.array([row[tier_index] for row in values])
        bars = ax.barh(
            y,
            width,
            left=left,
            height=0.58,
            color=color,
            edgecolor=COLORS["white"],
            linewidth=1.0,
            label=tier,
        )
        for bar, count in zip(bars, width):
            if count > 0:
                text_color = COLORS["white"] if tier in ("R2", "R3") else COLORS["ink"]
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    str(int(count)),
                    ha="center",
                    va="center",
                    fontsize=9,
                    fontweight="bold",
                    color=text_color,
                )
        left += width
    ax.set_yticks(y, ["Formula discovery (F)", "Trading/portfolio (T)", "Combined F+T"])
    ax.set_xlabel("Number of systems")
    ax.set_title("Static public-evidence tiers in the fixed method denominator", pad=12)
    ax.grid(axis="x", alpha=0.45)
    ax.set_axisbelow(True)
    legend = ax.legend(title="Observable tier", ncol=4, loc="lower right")
    legend.get_title().set_color(COLORS["navy"])
    for text in legend.get_texts():
        text.set_color(COLORS["ink"])
    save_figure(fig, path, "Public artifact attrition by system class")


def build_alpha_forest_figure(primary_frame: pd.DataFrame, path: Path) -> None:
    frame = primary_frame.copy()
    frame["_alpha"] = pd.to_numeric(frame["alpha_annualized"], errors="coerce")
    ok = frame.loc[frame["status"].astype(str) == "ok"].sort_values("_alpha", ascending=False)
    bad = frame.loc[frame["status"].astype(str) != "ok"].sort_values("candidate_id")
    family = pd.concat([ok, bad], ignore_index=True)
    if len(family) != 62:
        raise AssetBuildError("forest plot does not contain the complete 62-candidate family")
    # Plot only estimable paths.  The complete failure set remains visible in
    # the adjacent full-family table and event ledger; drawing 35 text-only
    # failure rows made the figure illegible at journal page size.
    ordered = ok.reset_index(drop=True)
    labels = [candidate_label(row) for _, row in ordered.iterrows()]
    y = np.arange(len(ordered))
    fig_height = max(7.4, 0.31 * len(ordered))
    fig, ax = plt.subplots(figsize=(8.0, fig_height), facecolor=COLORS["white"])
    style_axis(ax)
    for index, row in ordered.iterrows():
        alpha = 100.0 * float(row["alpha_annualized"])
        low = 100.0 * float(row["ci_low_annualized"])
        high = 100.0 * float(row["ci_high_annualized"])
        positive = alpha > 0
        ax.errorbar(
            alpha,
            index,
            xerr=np.array([[alpha - low], [high - alpha]]),
            fmt="o",
            markersize=4.6,
            markerfacecolor=COLORS["teal"] if positive else COLORS["white"],
            markeredgecolor=COLORS["teal"] if positive else COLORS["blue"],
            ecolor=COLORS["muted"],
            elinewidth=1.0,
            capsize=1.8,
            zorder=3,
        )
    ax.axvline(0.0, color=COLORS["ink"], linewidth=1.0, zorder=1)
    ax.axvline(2.0, color=COLORS["gold"], linewidth=1.1, linestyle="--", zorder=1)
    ax.set_yticks(y, labels, fontsize=7.2)
    ax.invert_yaxis()
    for tick in ax.get_yticklabels():
        tick.set_color(COLORS["ink"])
    finite_ci = pd.concat(
        [pd.to_numeric(ok["ci_low_annualized"], errors="coerce"), pd.to_numeric(ok["ci_high_annualized"], errors="coerce")]
    ).dropna()
    x_low = min(-1.0, 100.0 * float(finite_ci.min()))
    x_high = max(3.0, 100.0 * float(finite_ci.max()))
    margin = 0.08 * (x_high - x_low)
    ax.set_xlim(x_low - margin, x_high + margin)
    ax.set_xlabel("Annualized factor alpha (%)")
    ax.set_title(
        f"Primary G7 ex-U.S. alpha: {len(ok)} executable paths",
        pad=12,
    )
    ax.grid(axis="x", alpha=0.45)
    ax.set_axisbelow(True)
    ax.text(
        0.01,
        1.005,
        f"Dashed gold line: 2 pp threshold; {len(bad)} additional family members have no return estimate",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        color=COLORS["ink"],
    )
    save_figure(fig, path, "G7 alpha forest for executable paths; failures are reported in the ledger")


def build_cost_sensitivity_figure(cost: pd.DataFrame, path: Path) -> None:
    ok = successful(cost)
    wide = ok.pivot(index="candidate_id", columns="cost_bps_one_way", values="alpha_annualized")
    costs = np.array([0, 5, 10, 25, 50], dtype=float)
    wide = wide.reindex(columns=costs).dropna(how="all")
    if wide.empty:
        raise AssetBuildError("no successful estimates for cost-sensitivity figure")
    fig, ax = plt.subplots(figsize=(9.6, 5.6), facecolor=COLORS["white"])
    style_axis(ax)
    for _, row in wide.iterrows():
        values = 100.0 * row.to_numpy(dtype=float)
        ax.plot(costs, values, color=COLORS["blue"], alpha=0.12, linewidth=0.8, zorder=1)
    quantiles = wide.quantile([0.25, 0.5, 0.75], axis=0)
    q1 = 100.0 * quantiles.loc[0.25].to_numpy(dtype=float)
    median = 100.0 * quantiles.loc[0.5].to_numpy(dtype=float)
    q3 = 100.0 * quantiles.loc[0.75].to_numpy(dtype=float)
    ax.fill_between(costs, q1, q3, color=COLORS["teal"], alpha=0.20, label="Interquartile range", zorder=2)
    ax.plot(costs, median, color=COLORS["navy"], linewidth=2.4, marker="o", label="Median", zorder=3)
    ax.axvline(10, color=COLORS["gold"], linewidth=1.5, linestyle="--", label="Primary 10 bp", zorder=2)
    ax.axhline(0, color=COLORS["ink"], linewidth=0.9, zorder=1)
    ax.set_xticks(costs)
    ax.set_xlabel("One-way transaction cost (basis points)")
    ax.set_ylabel("Annualized factor alpha (%)")
    ax.set_title("Alpha sensitivity to the prespecified linear cost schedule", pad=12)
    ax.grid(alpha=0.42)
    ax.set_axisbelow(True)
    legend = ax.legend(loc="best")
    for text in legend.get_texts():
        text.set_color(COLORS["ink"])
    save_figure(fig, path, "Transaction-cost sensitivity")


def build_country_robustness_figure(
    primary_ok: pd.DataFrame,
    country: pd.DataFrame,
    loo: pd.DataFrame,
    metadata: pd.DataFrame,
    markets: Sequence[str],
    path: Path,
) -> None:
    top_ids = (
        primary_ok.sort_values("alpha_annualized", ascending=False)["candidate_id"].astype(str).head(10).tolist()
    )
    if not top_ids:
        raise AssetBuildError("no candidates for country-robustness figure")
    country_matrix = successful(country).pivot(index="candidate_id", columns="market", values="alpha_annualized")
    loo_matrix = successful(loo).pivot(index="candidate_id", columns="excluded_market", values="alpha_annualized")
    country_values = 100.0 * country_matrix.reindex(index=top_ids, columns=markets).to_numpy(dtype=float)
    loo_values = 100.0 * loo_matrix.reindex(index=top_ids, columns=markets).to_numpy(dtype=float)
    finite = np.concatenate([country_values[np.isfinite(country_values)], loo_values[np.isfinite(loo_values)]])
    if finite.size == 0:
        raise AssetBuildError("country robustness matrices contain no finite values")
    bound = max(2.0, float(np.quantile(np.abs(finite), 0.95)))
    norm = mcolors.TwoSlopeNorm(vmin=-bound, vcenter=0.0, vmax=bound)
    cmap = plt.get_cmap("RdBu").copy()
    cmap.set_bad("#D9E0E7")
    lookup = metadata.set_index("candidate_id")
    labels = [candidate_label(lookup.loc[candidate]) for candidate in top_ids]

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 6.3), facecolor=COLORS["white"], sharey=True)
    titles = ["Country-local alpha", "Leave-one-country-out alpha"]
    matrices = [country_values, loo_values]
    images = []
    for ax, title, matrix in zip(axes, titles, matrices):
        ax.set_facecolor(COLORS["white"])
        masked = np.ma.masked_invalid(matrix)
        image = ax.imshow(masked, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
        images.append(image)
        ax.set_xticks(np.arange(len(markets)), markets, rotation=0)
        ax.set_yticks(np.arange(len(labels)), labels, fontsize=7.2)
        ax.tick_params(colors=COLORS["ink"])
        ax.set_title(title, color=COLORS["navy"], pad=10)
        for spine in ax.spines.values():
            spine.set_color(COLORS["rule"])
    axes[0].set_ylabel("Highest pooled-alpha executable proxies")
    cbar = fig.colorbar(images[0], ax=axes, orientation="horizontal", fraction=0.055, pad=0.14)
    cbar.set_label("Annualized alpha (%)", color=COLORS["ink"])
    cbar.ax.tick_params(colors=COLORS["ink"])
    cbar.outline.set_edgecolor(COLORS["rule"])
    fig.suptitle("Geographic dispersion and omission stability", color=COLORS["navy"], fontsize=14, y=0.98)
    fig.text(
        0.5,
        0.035,
        "Gray cells are unavailable path estimates; they are not zeros.",
        ha="center",
        va="center",
        color=COLORS["ink"],
        fontsize=8.5,
    )
    save_figure(fig, path, "Country and leave-one-country-out robustness")


def build_transfer_figure(
    paired: pd.DataFrame,
    metadata: pd.DataFrame,
    spearman: float,
    path: Path,
) -> None:
    frame = paired.merge(metadata[["candidate_id", "paper_ref"]], on="candidate_id", how="left")
    x = 100.0 * frame["alpha_annualized_usa"].to_numpy(dtype=float)
    y = 100.0 * frame["alpha_annualized_g7"].to_numpy(dtype=float)
    if len(frame) < 3 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise AssetBuildError("invalid paired data for U.S./G7 transfer figure")
    fig, ax = plt.subplots(figsize=(7.5, 6.7), facecolor=COLORS["white"])
    style_axis(ax)
    ax.scatter(
        x,
        y,
        s=42,
        c=COLORS["teal"],
        edgecolors=COLORS["white"],
        linewidths=0.7,
        alpha=0.90,
        zorder=3,
    )
    low = min(float(x.min()), float(y.min()))
    high = max(float(x.max()), float(y.max()))
    margin = 0.08 * max(1.0, high - low)
    low, high = low - margin, high + margin
    ax.plot([low, high], [low, high], color=COLORS["muted"], linewidth=1.2, linestyle="--", zorder=1)
    ax.axhline(0, color=COLORS["ink"], linewidth=0.8, alpha=0.7)
    ax.axvline(0, color=COLORS["ink"], linewidth=0.8, alpha=0.7)
    disagreement = np.abs(y - x)
    for index in np.argsort(disagreement)[-min(8, len(frame)) :]:
        label = candidate_label(frame.iloc[index])
        ax.annotate(
            label,
            (x[index], y[index]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7,
            color=COLORS["ink"],
        )
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_xlabel("Retrospective U.S. annualized alpha (%)")
    ax.set_ylabel("Geographically external G7 ex-U.S. annualized alpha (%)")
    ax.set_title(f"Transport among {len(frame)} jointly estimable proxies (Spearman {spearman:.3f})", pad=12)
    ax.grid(alpha=0.42)
    ax.set_axisbelow(True)
    save_figure(fig, path, "Retrospective U.S. versus G7 alpha transport")


def validate_manuscript_macro_interface(manuscript_path: Path, book: MacroBook) -> None:
    text = require_file(manuscript_path).read_text(encoding="utf-8")
    forbidden = [r"\PositiveAt25", r"\PositiveAt50", r"\P95MissingExposure", r"\USG7Spearman"]
    present_forbidden = [name for name in forbidden if name in text]
    if present_forbidden:
        raise AssetBuildError(f"manuscript still contains digit-bearing TeX controls: {present_forbidden}")
    used = set(re.findall(r"\\([A-Z][A-Za-z]*)", text))
    ignored = {"Large", "InputIfFileExists", "PackageError", "SI", "Cref"}
    generated_used = used - ignored
    missing_definitions = generated_used - set(book.macros)
    unused_definitions = set(book.macros) - generated_used
    if missing_definitions or unused_definitions:
        raise AssetBuildError(
            f"manuscript/generated macro mismatch: undefined={sorted(missing_definitions)}, "
            f"unused={sorted(unused_definitions)}"
        )


def publish_staged_assets(stage: Path, paper_dir: Path, claims_path: Path) -> None:
    destinations = {
        stage / "generated_results.tex": paper_dir / "generated_results.tex",
        stage / "claims.csv": claims_path,
    }
    for source in sorted((stage / "tables").glob("*.tex")):
        destinations[source] = paper_dir / "tables" / source.name
    for source in sorted((stage / "figures").glob("*.pdf")):
        destinations[source] = paper_dir / "figures" / source.name
    expected_table_names = {
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
    }
    expected_figure_names = {
        "census_funnel.pdf",
        "artifact_attrition.pdf",
        "g7_alpha_forest.pdf",
        "cost_sensitivity.pdf",
        "country_robustness.pdf",
        "usa_g7_transfer.pdf",
    }
    if {path.name for path in (stage / "tables").glob("*.tex")} != expected_table_names:
        raise AssetBuildError("staged table set is incomplete")
    if {path.name for path in (stage / "figures").glob("*.pdf")} != expected_figure_names:
        raise AssetBuildError("staged figure set is incomplete")
    for source, destination in destinations.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=REPO_ROOT / "literature_review" / "census_v1" / "system_registry.csv",
    )
    parser.add_argument(
        "--artifact-audit",
        type=Path,
        default=EVIDENCE_ROOT / "artifact_audit" / "artifact_audit.csv",
    )
    parser.add_argument(
        "--artifact-summary",
        type=Path,
        default=EVIDENCE_ROOT / "artifact_audit" / "artifact_audit_summary.csv",
    )
    parser.add_argument(
        "--native-ledger",
        type=Path,
        default=EVIDENCE_ROOT / "native_fidelity_ledger.csv",
    )
    parser.add_argument(
        "--g7-dir",
        type=Path,
        default=EVIDENCE_ROOT / "g7_ex_us_corrected",
    )
    parser.add_argument(
        "--adverse-dir",
        type=Path,
        default=EVIDENCE_ROOT / "g7_missing_adverse",
    )
    parser.add_argument(
        "--usa-dir",
        type=Path,
        default=EVIDENCE_ROOT / "usa_retrospective_corrected",
    )
    parser.add_argument(
        "--fixed-calendar-dir",
        type=Path,
        default=FIXED_CALENDAR_DIR,
    )
    parser.add_argument("--paper-dir", type=Path, default=PAPER_DIR)
    parser.add_argument("--claims", type=Path, default=EVIDENCE_ROOT / "claims.csv")
    args = parser.parse_args(argv)

    registry, audit, _audit_summary, native = load_static_inputs(
        args.registry,
        args.artifact_audit,
        args.artifact_summary,
        args.native_ledger,
    )
    primary = load_run(
        args.g7_dir,
        name="primary G7",
        expected_markets=["CAN", "FRA", "DEU", "ITA", "JPN", "GBR"],
        expected_missing_policy="zero",
    )
    adverse = load_run(
        args.adverse_dir,
        name="G7 adverse missing-return sensitivity",
        expected_markets=["CAN", "FRA", "DEU", "ITA", "JPN", "GBR"],
        expected_missing_policy="adverse_100",
    )
    usa = load_run(
        args.usa_dir,
        name="retrospective USA",
        expected_markets=["USA"],
        expected_missing_policy="zero",
    )
    validate_cross_run(primary, adverse, usa)
    fixed_calendar, fixed_calendar_path, fixed_calendar_manifest_path = load_fixed_calendar_diagnostics(
        args.fixed_calendar_dir, primary
    )
    book, context = compute_metrics(
        registry=registry,
        audit=audit,
        native=native,
        registry_path=args.registry,
        audit_path=args.artifact_audit,
        native_path=args.native_ledger,
        primary=primary,
        adverse=adverse,
        usa=usa,
        fixed_calendar=fixed_calendar,
        fixed_calendar_path=fixed_calendar_path,
        fixed_calendar_manifest_path=fixed_calendar_manifest_path,
    )
    validate_manuscript_macro_interface(args.paper_dir / "alpha_agent_replication.tex", book)

    configure_plotting()
    stage = Path(tempfile.mkdtemp(prefix=".paper-assets-", dir=args.paper_dir))
    try:
        (stage / "tables").mkdir(parents=True)
        (stage / "figures").mkdir(parents=True)
        write_generated_results(book, stage / "generated_results.tex")
        write_claims(book, stage / "claims.csv")
        build_artifact_summary_table(audit, native, stage / "tables" / "artifact_summary.tex")
        build_primary_results_table(context["primary_frame"], stage / "tables" / "primary_results.tex")
        build_system_registry_table(registry, stage / "tables" / "system_registry.tex")
        build_candidate_registry_table(context["metadata"], stage / "tables" / "candidate_registry.tex")
        build_artifact_failure_table(native, registry, stage / "tables" / "artifact_failures.tex")
        build_path_failure_table(
            primary.frame("path_failures"), context["metadata"], stage / "tables" / "path_failures.tex"
        )
        build_cost_table(
            primary.frame("cost"),
            primary.frame("turnover"),
            context["metadata"],
            stage / "tables" / "cost_results.tex",
        )
        build_country_table(
            context["country"],
            context["loo"],
            context["metadata"],
            context["markets"],
            stage / "tables" / "country_results.tex",
        )
        build_inference_sensitivity_table(
            context["inference_sensitivity_rows"], stage / "tables" / "inference_sensitivity.tex"
        )
        build_claim_map_table(book.claims, stage / "tables" / "claim_map.tex")

        build_census_funnel_figure(registry, audit, native, stage / "figures" / "census_funnel.pdf")
        build_artifact_attrition_figure(audit, stage / "figures" / "artifact_attrition.pdf")
        build_alpha_forest_figure(context["primary_frame"], stage / "figures" / "g7_alpha_forest.pdf")
        build_cost_sensitivity_figure(primary.frame("cost"), stage / "figures" / "cost_sensitivity.pdf")
        build_country_robustness_figure(
            context["primary_ok"],
            context["country"],
            context["loo"],
            context["metadata"],
            context["markets"],
            stage / "figures" / "country_robustness.pdf",
        )
        build_transfer_figure(
            context["paired_usa_g7_same_window"],
            context["metadata"],
            context["same_window_spearman"],
            stage / "figures" / "usa_g7_transfer.pdf",
        )

        for tex_path in [stage / "generated_results.tex", *(stage / "tables").glob("*.tex")]:
            verify_balanced_tex(tex_path)
        publish_staged_assets(stage, args.paper_dir, args.claims)
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    print(f"wrote {args.paper_dir / 'generated_results.tex'}")
    print(f"wrote {args.paper_dir / 'tables'}")
    print(f"wrote {args.paper_dir / 'figures'}")
    print(f"wrote {args.claims}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
