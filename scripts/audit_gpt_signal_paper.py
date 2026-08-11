#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for GPT-Signal.

The audit pins both published papers, the arXiv source archive, the deleted
paper-listed repository evidence, and an author-owned thesis repository that
contains the otherwise-unreleased inputs, GPT outputs, and analysis code.  It
then independently replays every displayed heatmap cell and boxplot statistic
without making an LLM or network call.

Result-cell recovery is deliberately kept separate from full-paper fidelity.
The recovered implementation has a one-quarter lookahead in the monthly path,
the paper prints a different RAPS equation from the code/results, one plotted
series contains an unexplained uniform shift, and the original GPT snapshot is
no longer operationally reproducible.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import matplotlib.cbook as cbook
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]

TITLE = "GPT-Signal: Generative AI for Semi-automated Feature Engineering in the Alpha Research Process"
AUTHORS = ["Yining Wang", "Jinman Zhao", "Yuri Lawryshyn"]
ARXIV_RECORD = "https://arxiv.org/abs/2410.18448"
ARXIV_PDF_URL = "https://arxiv.org/pdf/2410.18448v1"
ARXIV_SOURCE_URL = "https://arxiv.org/e-print/2410.18448v1"
ACL_RECORD = "https://aclanthology.org/2024.finnlp-2.4/"
ACL_PDF_URL = "https://aclanthology.org/anthology-files/pdf/finnlp/2024.finnlp-2.4.pdf"
PAPER_REPO_URL = "https://github.com/Yiningww/GPT-signal"
AUTHOR_REPO_URL = "https://github.com/Yiningww/Thesis"

EXPECTED_ARXIV_PDF_SHA256 = "9859dd07b6eb48b9187979b0bd07a791c5ddb0af3b888fa4ca42b6d7f545a39e"
EXPECTED_ACL_PDF_SHA256 = "601154149267d49aae9f14c298fcde40011c50303245aa6a9fd998e7934f901c"
EXPECTED_SOURCE_SHA256 = "396536c647692c2e357cae30a53924e284ef503a095192fa48fc8df9452254be"
EXPECTED_ARXIV_PAGES = 13
EXPECTED_ACL_PAGES = 12
EXPECTED_SOURCE_FILES = 71
EXPECTED_SOURCE_BYTES = 4_294_017
EXPECTED_REBUILT_PDF_SHA256 = "98816276e2b4f395256adfaa1bd606d972f004dc58426595d484a096a5c73944"

EXPECTED_AUTHOR_HEAD = "434230ca9123048a4d79e2cc1390b23b050ef68e"
EXPECTED_AUTHOR_TREE_SHA256 = "582139c57512435020b7edc6471b308f018afaa3c41ea4f35529adcc13227318"
EXPECTED_AUTHOR_ARCHIVE_SHA256 = "451d7334bf4a6de94dcbc6cf2e29d9f5c30f228a58457fdd278d5ba9772992fd"
EXPECTED_AUTHOR_FILES = 13_884
EXPECTED_AUTHOR_BYTES = 170_997_569
EXPECTED_AUTHOR_EXTENSIONS = {
    "csv": 13_264,
    "xlsx": 373,
    "out": 145,
    "py": 6,
    "ipynb": 3,
}

EVIDENCE_HASHES = {
    "acl_metadata.bib": "a6dc3cf5462faaefd303e639424c12c7143fca397d415a3ade71251477660dcc",
    "acl_page.html": "f72c2fbbfdf40d7377e4acceb801abe2eb10dceb5b8433828603922ea081fa59",
    "arxiv_api.xml": "03c717993d6def194eec2937712952f98c6f23db8836e0f897d2c15715452312",
    "arxiv_record.html": "e044a55ebb1f2336584e8526f6a7044097da633456626c54ba6ed1328dac62e3",
    "github_commit_search.json": "08c082fdf7ca87ba911a2aabb0f0cf2d3e482a6feeaac9713e4578c20b2600b2",
    "github_repo.json": "a298fd3d1a255b0eb21a952212460852e05ba9721d3445fb42d7ad054d88f94a",
    "github_repos.json": "8a272b63c4fbbf11cb5e6eec10284bdf873f6e497374e459a31e033fdf0665c5",
    "github_search_exact.json": "0268da7713c8cc8413c2d0221bcad0a2e97de4ec6a2691d426e7d34a53881095",
    "github_user.json": "fe82a50e7671340ecc3c6d035870168a4feceeb97ec2a02e8caf2ff9b8d5d54e",
    "swh_origin.json": "1ff7378cf5607083e5e42658a9e0bee3b74347f0ae115225a821354a27681ca9",
    "thesis_commits.json": "f49794967ec08587239b62fd89a989234eef6fd01d2060ed8aea8bdcf66936ac",
    "thesis_repo.json": "0231c6587c0494b596618a634a381714c4d7e1789152f54f4dc27cd113f6bf91",
    "wayback_cdx.json": "7ad3d44d8ef5cedd6ddc2cca9767ee1e6ba130b2a66d4d13f26654ce08af82ba",
    "wayback_repo_20240816.html": "7f0d572de22f83eaf5b138c444a0c4f7396380d39066e0ffebb03259e87ce387",
}

FEATURES = [
    "Price/Earnings",
    "Price/Book Value",
    "Return on Assets",
    "Return on Equity ",
    "Free Cash Flow per Share",
    "Price/Cash Flow",
    "Enterprise Value/EBITDA",
    "Gross Margin",
    "Net Margin",
    "Sales per Share",
]
LABELS = ["P/E", "P/B", "ROA", "ROE", "FCF", "P/CF", "EBITDA", "GM", "NM", "SPS"]
NEW_LABELS = ["PVS", "RAPS", "EVC", "VEC", "PLF", "IQS"]
IT = [
    "AAPL", "AKAM", "AMD", "ANET", "ANSS", "APH", "CDNS", "CDW", "CTSH", "ENPH", "EPAM",
    "FFIV", "FSLR", "FTNT", "GEN", "GLW", "IBM", "INTC", "IT", "JNPR", "KLAC", "LRCX",
    "MCHP", "MPWR", "MSFT", "MSI", "NOW", "NXPI", "ON", "PTC", "QCOM", "ROP", "STX",
    "SWKS", "TDY", "TEL", "TER", "TRMB", "TXN", "TYL", "VRSN", "WDC", "ZBRA",
]
HC = [
    "ABBV", "ABT", "ALGN", "AMGN", "BAX", "BDX", "BIO", "BMY", "BSX", "CAH", "COR", "CRL",
    "CTLT", "CVS", "DGX", "DHR", "DXCM", "EW", "GILD", "HSIC", "TMO", "UHS", "VRTX", "VTRS",
    "IDXX", "ILMN", "INCY", "WST", "ZTS", "ISRG", "JNJ",
]
EN = [
    "APA", "COP", "CTRA", "EOG", "FANG", "HAL", "HES", "KMI", "MPC", "MRO", "OKE", "OXY",
    "PSX", "PXD", "SLB", "TRGP", "VLO", "WMB", "XOM",
]
GROUPS = {
    "it": [("Information Technology", IT)],
    "hc": [("Health Care", HC)],
    "en": [("Energy", EN)],
    "all": [("Information Technology", IT), ("Health Care", HC), ("Energy", EN)],
}

MATRIX_FILES = [
    ("it_3m_existing", "it_3m_16-20_old2.svg", "it", "3m", "existing"),
    ("it_3m_new", "it_3m_16-20_new2.svg", "it", "3m", "new"),
    ("it_1m_existing", "it_1m_16-20_old.svg", "it", "1m", "existing"),
    ("it_1m_new", "it_1m_16-20_new.svg", "it", "1m", "new"),
    ("hc_1m_existing", "hc_1m_16-20_old.svg", "hc", "1m", "existing"),
    ("hc_1m_new", "hc_1m_16-20_new.svg", "hc", "1m", "new"),
    ("hc_3m_existing", "hc_3m_16-20_old.svg", "hc", "3m", "existing"),
    ("hc_3m_new", "hc_3m_16-20_new.svg", "hc", "3m", "new"),
    ("en_1m_existing", "en_1m_16-20_old.svg", "en", "1m", "existing"),
    ("en_1m_new", "en_1m_16-20_new.svg", "en", "1m", "new"),
    ("en_3m_existing", "en_3m_16-20_old.svg", "en", "3m", "existing"),
    ("en_3m_new", "en_3m_16-20_new.svg", "en", "3m", "new"),
    ("all_3m_all", "corr_avg_allsector.svg", "all", "3m", "all"),
]

BOX_FILES = {
    ("all", "3m"): "2016_2020_3M_step2_allsector.svg",
    ("it", "1m"): "IT_2016_2020_1M_step2.svg",
    ("it", "3m"): "IT_2016_2020_3M_step2.svg",
    ("hc", "1m"): "HC_2016_2020_1M_step2.svg",
    ("hc", "3m"): "HC_2016_2020_3M_step2.svg",
    ("en", "1m"): "EN_2016_2020_1M_step2.svg",
    ("en", "3m"): "EN_2016_2020_3M_step2.svg",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_standardize(value: Any) -> np.ndarray:
    """Load the source-only dependency lazily so audit contracts remain importable."""
    from sklearn.preprocessing import StandardScaler

    return StandardScaler().fit_transform(value)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> None:
    materialized = list(rows)
    if not materialized:
        raise ValueError(f"refusing to write empty audit artifact: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(materialized[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(materialized)


def git(repo: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=not binary,
    )
    return result.stdout


def stored_bytes(path: Path) -> bytes:
    if path.is_symlink():
        return ("SYMLINK:" + os.readlink(path)).encode("utf-8")
    return path.read_bytes()


def validate_pdf(path: Path, expected_hash: str, pages: int, flavor: str) -> str:
    if sha256(path) != expected_hash:
        raise ValueError(f"{flavor} PDF hash changed")
    reader = PdfReader(path)
    if len(reader.pages) != pages:
        raise ValueError(f"{flavor} PDF page count changed: {len(reader.pages)}")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized = " ".join(text.split())
    for required in (
        "GPT-Signal: Generative AI for Semi-automated Feature",
        "Risk-Adjusted Performance Score",
        "5 out of 6 models",
        "github.com/ Yiningww/GPT-signal",
    ):
        if required not in normalized:
            raise ValueError(f"required {flavor} paper text missing: {required}")
    return text


def paper_source_inventory(archive: Path, source_dir: Path) -> list[dict[str, str]]:
    if sha256(archive) != EXPECTED_SOURCE_SHA256:
        raise ValueError("arXiv source archive hash changed")
    rows: list[dict[str, str]] = []
    total = 0
    with tarfile.open(archive, "r:gz") as bundle:
        members = [member for member in bundle.getmembers() if member.isfile()]
        if len(members) != EXPECTED_SOURCE_FILES:
            raise ValueError(f"arXiv source file count changed: {len(members)}")
        for member in sorted(members, key=lambda item: item.name):
            extracted = bundle.extractfile(member)
            if extracted is None:
                raise ValueError(f"cannot read arXiv member: {member.name}")
            payload = extracted.read()
            total += len(payload)
            disk = source_dir / member.name
            if not disk.is_file() or disk.read_bytes() != payload:
                raise ValueError(f"extracted arXiv source differs: {member.name}")
            suffix = Path(member.name).suffix.lower()
            if suffix == ".svg":
                role = "published_vector_figure"
            elif suffix in {".png", ".pdf"}:
                role = "paper_asset"
            elif suffix in {".tex", ".bib", ".bst", ".sty"}:
                role = "paper_source"
            else:
                role = "other"
            rows.append({
                "path": member.name,
                "bytes": str(len(payload)),
                "sha256": bytes_sha256(payload),
                "role": role,
                "system_code": "no",
                "system_data": "no",
            })
    if total != EXPECTED_SOURCE_BYTES:
        raise ValueError(f"arXiv source byte count changed: {total}")
    return rows


def author_source_inventory(repo: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    head = str(git(repo, "rev-parse", "HEAD")).strip()
    if head != EXPECTED_AUTHOR_HEAD:
        raise ValueError(f"author repository HEAD changed: {head}")
    tree_hash = bytes_sha256(bytes(git(repo, "ls-tree", "-r", "HEAD", binary=True)))
    archive_hash = bytes_sha256(bytes(git(repo, "archive", "--format=tar", "HEAD", binary=True)))
    if tree_hash != EXPECTED_AUTHOR_TREE_SHA256 or archive_hash != EXPECTED_AUTHOR_ARCHIVE_SHA256:
        raise ValueError("author repository tree/archive changed")
    if subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--"]).returncode != 0:
        raise ValueError("author repository tracked files are dirty")
    raw_paths = bytes(git(repo, "ls-files", "-z", binary=True)).split(b"\0")
    paths = [os.fsdecode(name) for name in raw_paths if name]
    if len(paths) != EXPECTED_AUTHOR_FILES:
        raise ValueError(f"author tracked file count changed: {len(paths)}")

    rows: list[dict[str, str]] = []
    extensions: Counter[str] = Counter()
    tracked_bytes = 0
    compiled = 0
    credential_matches = 0
    credential_files = 0
    credential_pattern = re.compile(rb"sk-[A-Za-z0-9_-]{10,}")
    for name in paths:
        path = repo / name
        payload = stored_bytes(path)
        tracked_bytes += len(payload)
        extension = Path(name).suffix.lower().lstrip(".")
        extensions[extension] += 1
        compile_status = "not_python"
        if extension == "py":
            compile(path.read_text(encoding="utf-8", errors="replace"), name, "exec")
            compile_status = "compiled"
            compiled += 1
        matches = len(credential_pattern.findall(payload))
        if matches:
            credential_matches += matches
            credential_files += 1
        if name.endswith(".xlsx"):
            role = "author_input_workbook"
        elif name.endswith(".csv") and "/historical_return/" in name:
            role = "author_price_input"
        elif name.endswith(".csv") and "/langchain/output/" in name:
            role = "author_llm_output"
        elif name.endswith(".py"):
            role = "author_implementation"
        elif name.endswith(".svg") or name.endswith(".png"):
            role = "author_figure"
        elif name.endswith(".ipynb"):
            role = "author_notebook"
        else:
            role = "other"
        rows.append({
            "path": name,
            "bytes": str(len(payload)),
            "sha256": bytes_sha256(payload),
            "role": role,
            "compile_status": compile_status,
            "contains_redacted_credential_pattern": "yes" if matches else "no",
            "paper_result_input": "yes" if role in {"author_input_workbook", "author_price_input"} else "no",
            "paper_result_output": "yes" if role in {"author_llm_output", "author_figure"} else "no",
        })
    if tracked_bytes != EXPECTED_AUTHOR_BYTES:
        raise ValueError(f"author tracked byte count changed: {tracked_bytes}")
    if compiled != EXPECTED_AUTHOR_EXTENSIONS["py"]:
        raise ValueError(f"author Python compile count changed: {compiled}")
    for extension, expected in EXPECTED_AUTHOR_EXTENSIONS.items():
        if extensions[extension] != expected:
            raise ValueError(f"author extension count changed: {extension}: {extensions[extension]}")
    if credential_matches != 4 or credential_files != 2:
        raise ValueError("plaintext credential exposure count changed")
    license_files = [name for name in paths if Path(name).name.lower().startswith(("license", "copying"))]
    dependency_files = [
        name for name in paths
        if Path(name).name.lower() in {"requirements.txt", "pyproject.toml", "environment.yml", "environment.yaml", "poetry.lock", "uv.lock"}
    ]
    if license_files or dependency_files:
        raise ValueError("author license/dependency-manifest status changed")
    facts = {
        "head": head,
        "tree_sha256": tree_hash,
        "archive_sha256": archive_hash,
        "tracked_files": len(paths),
        "tracked_bytes": tracked_bytes,
        "extension_counts": dict(sorted(extensions.items())),
        "compiled_python_files": compiled,
        "plaintext_credential_matches_redacted": credential_matches,
        "files_containing_plaintext_credentials": credential_files,
        "license": "none_observed",
        "dependency_manifest": "none_observed",
    }
    return rows, facts


def validate_discovery_evidence(directory: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name, expected in EVIDENCE_HASHES.items():
        path = directory / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"discovery evidence changed: {name}")
        rows.append({"artifact": name, "sha256": expected, "bytes": str(path.stat().st_size)})
    paper_repo = json.loads((directory / "github_repo.json").read_text(encoding="utf-8"))
    if paper_repo.get("message") != "Not Found":
        raise ValueError("paper-listed GitHub repository is no longer 404")
    swh = json.loads((directory / "swh_origin.json").read_text(encoding="utf-8"))
    if "not found" not in str(swh).lower():
        raise ValueError("Software Heritage origin status changed")
    cdx = json.loads((directory / "wayback_cdx.json").read_text(encoding="utf-8"))
    flattened = json.dumps(cdx)
    if "20240816022921" not in flattened:
        raise ValueError("Wayback capture changed")
    archived = (directory / "wayback_repo_20240816.html").read_text(encoding="utf-8", errors="replace")
    for required in (
        "818681062", "212518b57a66e65845793a25850e3bbb5187f707", "README.md", ">GPT-signal</h1>",
    ):
        if required not in archived:
            raise ValueError(f"archived placeholder fact missing: {required}")
    search = json.loads((directory / "github_search_exact.json").read_text(encoding="utf-8"))
    if search.get("total_count") != 32:
        raise ValueError("exact-name GitHub search count changed")
    commit_search = json.loads((directory / "github_commit_search.json").read_text(encoding="utf-8"))
    if commit_search.get("total_count") != 0:
        raise ValueError("placeholder commit search status changed")
    repo = json.loads((directory / "thesis_repo.json").read_text(encoding="utf-8"))
    commits = json.loads((directory / "thesis_commits.json").read_text(encoding="utf-8"))
    if repo.get("full_name") != "Yiningww/Thesis" or repo.get("license") is not None:
        raise ValueError("author repository API metadata changed")
    if len(commits) != 20 or commits[0].get("sha") != EXPECTED_AUTHOR_HEAD:
        raise ValueError("author repository commit evidence changed")
    return rows


class ReplayData:
    """Cached loader implementing the released data.py semantics."""

    def __init__(self, repo: Path):
        self.root = repo / "Code" / "Data"
        self._ratios: dict[tuple[str, str], pd.DataFrame] = {}
        self._returns: dict[tuple[str, str], pd.Series] = {}
        self._companies: dict[tuple[str, str, str, str], pd.DataFrame] = {}
        self._period_returns: dict[tuple[str, str, str], float] = {}

    def ratios(self, sector: str, ticker: str) -> pd.DataFrame:
        key = (sector, ticker)
        if key in self._ratios:
            return self._ratios[key].copy()
        path = self.root / sector / "DEC start" / f"{ticker}.xlsx"
        workbook = pd.ExcelFile(path, engine="openpyxl")
        sheet = next((ticker + suffix for suffix in ("-US", "-USA") if ticker + suffix in workbook.sheet_names), None)
        if sheet is None:
            raise ValueError(f"FactSet sheet absent: {path}")
        data = pd.read_excel(workbook, sheet_name=sheet).reset_index(drop=True).set_index("Date").T
        data.index = pd.to_datetime(data.index, format="%b '%y") + pd.offsets.MonthEnd()
        ratios = data.apply(pd.to_numeric)
        for column in FEATURES:
            if column not in ratios:
                ratios.loc[:, column] = 0
        ratios = ratios[FEATURES].apply(lambda series: series.fillna(series.mean()), axis=0)
        self._ratios[key] = ratios
        return ratios.copy()

    def returns(self, ticker: str, horizon: str) -> pd.Series:
        key = (ticker, horizon)
        if key in self._returns:
            return self._returns[key].copy()
        path = self.root / "historical_return" / f"{ticker}2015-12-31-2020-12-31.csv"
        data = pd.read_csv(path)
        data["Date"] = pd.to_datetime(data["Date"])
        close = data.set_index("Date")["Close"]
        rule = "ME" if horizon == "1m" else "3ME"
        result = close.resample(rule).last().pct_change().dropna()
        self._returns[key] = result
        return result.copy()

    def company(self, sector: str, ticker: str, horizon: str, raps: str = "power") -> pd.DataFrame:
        key = (sector, ticker, horizon, raps)
        if key in self._companies:
            return self._companies[key].copy()
        ratios = self.ratios(sector, ticker)
        outcome = self.returns(ticker, horizon)
        ratios.index = ratios.index + pd.DateOffset(days=1)
        aligned = ratios.reindex(outcome.index, method="ffill")
        frame = pd.concat([aligned, outcome.rename("Return")], axis=1)
        pe, pb = frame["Price/Earnings"], frame["Price/Book Value"]
        roa, roe = frame["Return on Assets"], frame["Return on Equity "]
        fcf, pcf = frame["Free Cash Flow per Share"], frame["Price/Cash Flow"]
        ebitda, gm, sps = frame["Enterprise Value/EBITDA"], frame["Gross Margin"], frame["Sales per Share"]
        frame["PVS"] = roe / pe
        frame["RAPS"] = roe / (pe ** 2 if raps == "power" else pe * 2)
        frame["EVC"] = (1 / roa) * (1 / ebitda) * (1 / pcf)
        frame["VEC"] = (pe + roe + fcf) / 3
        frame["PLF"] = roe * gm / pe
        frame["IQS"] = roe * (1 / pe) * (1 / pb) * np.log(sps.clip(lower=0.01))
        self._companies[key] = frame
        return frame.copy()

    def period_return(self, ticker: str, start: str, end: str) -> float:
        key = (ticker, start, end)
        if key in self._period_returns:
            return self._period_returns[key]
        path = self.root / "historical_return" / f"{ticker}{start}-{end}.csv"
        close = pd.read_csv(path)["Close"]
        value = float((close.iloc[-1] - close.iloc[0]) / close.iloc[0])
        self._period_returns[key] = value
        return value


def expected_matrix(svg: Path) -> tuple[list[str], np.ndarray]:
    comments = [item.strip() for item in re.findall(r"<!--(.*?)-->", svg.read_text(encoding="utf-8"), re.S)]
    n = int(round(len(comments) ** 0.5)) - 1
    if len(comments) != 2 * n + n * n + 1 or comments[:n] != comments[n:2 * n]:
        raise ValueError(f"cannot recover heatmap matrix: {svg}")
    values = np.array([float(item) for item in comments[2 * n:2 * n + n * n]]).reshape(n, n)
    return comments[:n], values


def replay_matrix(data: ReplayData, group: str, horizon: str, raps: str) -> np.ndarray:
    frames = [
        data.company(sector, ticker, horizon, raps)
        for sector, tickers in GROUPS[group]
        for ticker in tickers
    ]
    periods = 19 if horizon == "3m" else len(frames[0]) - 1
    total = np.zeros((17, 17))
    for index in range(periods):
        rows = []
        for frame in frames:
            x = frame[FEATURES + NEW_LABELS].iloc[:-1].iloc[index]
            y = frame["Return"].iloc[1:].iloc[index]
            rows.append([*x, y])
        total += pd.DataFrame(rows, columns=LABELS + NEW_LABELS + ["Return"]).corr(method="spearman").to_numpy()
    return total / periods


def correlation_reproduction(data: ReplayData, source: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    matrices: dict[tuple[str, str, str], np.ndarray] = {}
    rows: list[dict[str, str]] = []
    summaries: list[dict[str, str]] = []
    for matrix_id, filename, group, horizon, part in MATRIX_FILES:
        expected_labels, expected = expected_matrix(source / filename)
        if part == "existing":
            indexes = list(range(10)) + [16]
            labels = LABELS + ["Return"]
        elif part == "new":
            indexes = list(range(10, 17))
            labels = NEW_LABELS + ["Return"]
        else:
            indexes = list(range(17))
            labels = LABELS + NEW_LABELS + ["Return"]
        if expected_labels != labels:
            raise ValueError(f"heatmap label order changed: {filename}: {expected_labels}")
        actuals: dict[str, np.ndarray] = {}
        for formula in ("power", "multiply"):
            key = (group, horizon, formula)
            if key not in matrices:
                matrices[key] = replay_matrix(data, group, horizon, formula)
            actuals[formula] = matrices[key][np.ix_(indexes, indexes)]
        power_matches = 0
        multiply_matches = 0
        for row_index, row_label in enumerate(labels):
            for column_index, column_label in enumerate(labels):
                paper = float(expected[row_index, column_index])
                power = float(actuals["power"][row_index, column_index])
                multiply = float(actuals["multiply"][row_index, column_index])
                power_display = float(np.round(power, 2))
                multiply_display = float(np.round(multiply, 2))
                power_match = power_display == paper
                multiply_match = multiply_display == paper
                power_matches += power_match
                multiply_matches += multiply_match
                rows.append({
                    "result_id": f"COR-{len(rows)+1:04d}",
                    "matrix": matrix_id,
                    "source_svg": filename,
                    "row": row_label,
                    "column": column_label,
                    "paper_display": f"{paper:.2f}",
                    "source_code_power_value": repr(power),
                    "source_code_power_display": f"{power_display:.2f}",
                    "source_code_power_match": "yes" if power_match else "no",
                    "paper_equation_multiply_value": repr(multiply),
                    "paper_equation_multiply_display": f"{multiply_display:.2f}",
                    "paper_equation_multiply_match": "yes" if multiply_match else "no",
                    "llm_regenerated": "no",
                    "credit": "author_data_deterministic_replay",
                })
        summaries.append({
            "matrix": matrix_id,
            "source_svg": filename,
            "cells": str(expected.size),
            "source_code_power_matches": str(power_matches),
            "paper_equation_multiply_matches": str(multiply_matches),
            "horizon": horizon,
            "cross_sections": "19" if horizon == "3m" else "59",
        })
    if len(rows) != 1_309 or sum(row["source_code_power_match"] == "yes" for row in rows) != 1_309:
        raise ValueError("published heatmap recovery changed")
    if sum(row["paper_equation_multiply_match"] == "yes" for row in rows) != 1_205:
        raise ValueError("paper RAPS equation mismatch surface changed")
    return rows, summaries


def svg_axis(svg: str) -> tuple[float, float]:
    points: list[tuple[float, float]] = []
    for block in re.findall(r'<g id="ytick_\d+">(.*?)</g>\s*</g>\s*</g>', svg, re.S):
        y = re.search(r'<use[^>]* y="([0-9.]+)"', block)
        value = re.search(r'<!--\s*([^<>]+?)\s*-->', block)
        if y and value:
            try:
                points.append((float(y.group(1)), float(value.group(1).replace("−", "-"))))
            except ValueError:
                pass
    if len(points) < 2:
        raise ValueError("cannot recover SVG y-axis")
    (y1, v1), (y2, v2) = points[:2]
    slope = (v2 - v1) / (y2 - y1)
    return slope, v1 - slope * y1


def author_box_stats(path: Path) -> list[dict[str, float | str]]:
    svg = path.read_text(encoding="utf-8")
    slope, intercept = svg_axis(svg)
    black = re.findall(
        r'<path d="(M [^"]+?)" clip-path="[^"]+" style="fill: none; stroke: #000000; stroke-linecap: square"/>',
        svg, re.S,
    )
    medians = [
        float(value) for value in re.findall(
            r'<path d="M [0-9.]+ ([0-9.]+)\s+L [0-9.]+ \1\s+"[^>]*stroke: #ff7f0e', svg
        )
    ]
    if len(black) != 35 or len(medians) != 7:
        raise ValueError(f"cannot recover boxplot geometry: {path}")
    convert = lambda y: slope * y + intercept
    rows: list[dict[str, float | str]] = []
    for index in range(7):
        paths = black[index * 5:(index + 1) * 5]
        ys = [[float(y) for y in re.findall(r"(?:M|L) [0-9.]+ ([0-9.]+)", item)] for item in paths]
        if len(ys[0]) != 5 or any(len(item) != 2 for item in ys[1:]):
            raise ValueError(f"boxplot path layout changed: {path}")
        rows.append({
            "model": NEW_LABELS[index] if index < 6 else "baseline",
            "q1": convert(ys[0][0]),
            "q3": convert(ys[0][2]),
            "whislo": convert(ys[1][1]),
            "whishi": convert(ys[2][1]),
            "med": convert(medians[index]),
        })
    return rows


def interval_dates(horizon: str) -> list[str]:
    dates = ["2015-12-31"]
    endpoints = [(3, 31), (6, 30), (9, 30), (12, 31)]
    if horizon == "1m":
        endpoints = [
            (1, 31), (2, 28), (3, 31), (4, 30), (5, 31), (6, 30),
            (7, 31), (8, 31), (9, 30), (10, 31), (11, 30), (12, 31),
        ]
    for year in range(2016, 2021):
        dates.extend(f"{year}-{month:02d}-{day:02d}" for month, day in endpoints)
    return dates


def box_values(data: ReplayData, group: str, horizon: str) -> dict[str, list[float]]:
    pairs = [(sector, ticker) for sector, tickers in GROUPS[group] for ticker in tickers]
    frames = {ticker: data.company(sector, ticker, horizon, "power") for sector, ticker in pairs}
    dates = interval_dates(horizon)
    period_returns = [
        np.array([data.period_return(ticker, start, end) for _, ticker in pairs])
        for start, end in zip(dates[:-1], dates[1:])
    ]
    result: dict[str, list[float]] = {}
    for model in NEW_LABELS + ["baseline"]:
        columns = FEATURES + ([] if model == "baseline" else [model])
        beta_rows: list[dict[str, float]] = []
        for _, ticker in pairs:
            frame = frames[ticker]
            x = frame[columns].iloc[:-1]
            y = frame["Return"].iloc[1:]
            standardized = source_standardize(x)
            fit = sm.OLS(y, sm.add_constant(standardized), missing="drop").fit()
            beta_rows.append(dict(zip(["Constant", *columns], fit.params)))
        beta_frame = pd.DataFrame(beta_rows)
        beta_x = sm.add_constant(source_standardize(beta_frame[columns]))
        result[model] = [float(sm.OLS(y, beta_x, missing="drop").fit().rsquared_adj) for y in period_returns]
    return result


def boxplot_reproduction(data: ReplayData, source: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    summaries: list[dict[str, str]] = []
    medians_above = 0
    for (group, horizon), filename in BOX_FILES.items():
        expected = author_box_stats(source / filename)
        expected_by_model = {str(item["model"]): item for item in expected}
        values = box_values(data, group, horizon)
        matches = 0
        maximum = 0.0
        for model in NEW_LABELS + ["baseline"]:
            actual = cbook.boxplot_stats(values[model], whis=1.5)[0]
            author = expected_by_model[model]
            for field in ("q1", "med", "q3", "whislo", "whishi"):
                paper = float(author[field])
                replay = float(actual[field])
                delta = replay - paper
                match = abs(delta) <= 1e-4
                matches += match
                maximum = max(maximum, abs(delta))
                rows.append({
                    "result_id": f"BOX-{len(rows)+1:03d}",
                    "figure": f"{group}_{horizon}",
                    "source_svg": filename,
                    "model": model,
                    "statistic": field,
                    "paper_vector_value": repr(paper),
                    "source_replay_value": repr(replay),
                    "replay_minus_paper": repr(delta),
                    "match_tolerance_1e-4": "yes" if match else "no",
                    "llm_regenerated": "no",
                    "credit": "author_data_deterministic_replay" if match else "unexplained_published_plot_difference",
                })
        baseline = float(expected_by_model["baseline"]["med"])
        above = sum(float(expected_by_model[model]["med"]) > baseline for model in NEW_LABELS)
        medians_above += above
        summaries.append({
            "figure": f"{group}_{horizon}",
            "source_svg": filename,
            "statistics": "35",
            "matches_tolerance_1e-4": str(matches),
            "maximum_absolute_difference": repr(maximum),
            "new_signal_medians_above_baseline": str(above),
            "new_signal_medians_total": "6",
        })
    if len(rows) != 245 or sum(row["match_tolerance_1e-4"] == "yes" for row in rows) != 240:
        raise ValueError("published boxplot recovery changed")
    if medians_above != 35:
        raise ValueError(f"boxplot improvement count changed: {medians_above}")
    anomaly = [row for row in rows if row["match_tolerance_1e-4"] == "no"]
    if {(row["figure"], row["model"]) for row in anomaly} != {("all_3m", "EVC")}:
        raise ValueError("boxplot anomaly identity changed")
    if any(abs(float(row["replay_minus_paper"]) + 0.02) > 1e-7 for row in anomaly):
        raise ValueError("all-sector EVC uniform shift changed")
    return rows, summaries


def prompt_output(path: Path) -> str:
    with path.open(newline="", encoding="utf-8", errors="replace") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1 or "answer" not in rows[0]:
        raise ValueError(f"unexpected GPT output CSV: {path}")
    return rows[0]["answer"]


def formula_lineage(repo: Path, paper_source: Path) -> list[dict[str, str]]:
    base = repo / "Code/langchain/output/gpt-4-1106-preview/zero_shot_cot"
    raw = {
        "PVS": base / "out_gpt-4-1106-preview_zero_shot_cot_20240207-154023.csv",
        "RAPS": base / "out_gpt-4-1106-preview_zero_shot_cot_20240207-163355.csv",
        "EVC": base / "out_gpt-4-1106-preview_zero_shot_cot_20240207-164109.csv",
        "PLF": base / "new/out_gpt-4-1106-preview_zero_shot_cot.csv",
        "IQS": base / "new/out_gpt-4-1106-preview_zero_shot_cot_20240225-183705.csv",
    }
    checks = {
        "PVS": ("roe", "p/e"),
        "RAPS": ("power of beta", "roe"),
        "EVC": ("efficiency_value_composite", "-1"),
        "PLF": ("roe * gross margin", "p/e"),
        "IQS": ("investment quality score", "log(sales per share)"),
    }
    for signal, path in raw.items():
        answer = prompt_output(path).lower()
        if any(token not in answer for token in checks[signal]):
            raise ValueError(f"raw GPT formula lineage changed: {signal}")
    gpt_csvs = list((repo / "Code/langchain/output/gpt-4-1106-preview").rglob("*.csv"))
    if len(gpt_csvs) != 16:
        raise ValueError(f"GPT-4 output count changed: {len(gpt_csvs)}")
    source = (repo / "Code/Data/data.py").read_text(encoding="utf-8")
    tex = (paper_source / "acl_latex.tex").read_text(encoding="utf-8")
    if "current_ticker['2'] = roe / (pe**beta)" not in source:
        raise ValueError("released RAPS implementation changed")
    if r"RAPS = \frac{ROE}{P/E \cdot \beta}" not in tex:
        raise ValueError("paper RAPS equation changed")
    specs = [
        ("PVS", "ROE / P/E", "ROE / P/E", "yes", "same", "power_and_multiply_both_unaffected"),
        ("RAPS", "ROE / (P/E * beta), beta=2", "ROE / (P/E ** beta), beta=2", "yes", "contradiction", "only_source_and_GPT_power_formula_matches_all_1309_cells"),
        ("EVC", "ROA^-1 * EV/EBITDA^-1 * P/CF^-1", "same", "yes", "same", "matches_except_unexplained_all_sector_plot_shift"),
        ("VEC", "mean(P/E, ROE, FCF/share)", "same", "no", "missing_raw_generation_output", "formula_and_results_present_but_no_raw_GPT_lineage"),
        ("PLF", "ROE * gross margin / P/E", "same", "yes_generic_NF_name", "renamed", "raw_GPT_output_formula_matches_paper_signal"),
        ("IQS", "ROE * P/E^-1 * P/B^-1 * log(SPS)", "same", "yes", "same", "raw_GPT_output_formula_matches"),
    ]
    rows = []
    for signal, paper, code, output, assessment, evidence in specs:
        rows.append({
            "signal": signal,
            "paper_formula": paper,
            "released_code_formula": code,
            "raw_gpt4_output_recovered": output,
            "raw_output_path": str(raw[signal].relative_to(repo)) if signal in raw else "",
            "assessment": assessment,
            "result_evidence": evidence,
            "fresh_llm_call_made": "no",
        })
    return rows


def lookahead_trace(data: ReplayData) -> list[dict[str, str]]:
    ratios = data.ratios("Information Technology", "AAPL")
    if not ratios.index.is_monotonic_decreasing:
        raise ValueError("FactSet workbook ordering changed")
    returns = data.returns("AAPL", "1m")
    shifted = ratios.copy()
    shifted.index = shifted.index + pd.DateOffset(days=1)
    source = shifted.reindex(returns.index, method="ffill")
    chronological = shifted.sort_index().reindex(returns.index, method="ffill")
    rows: list[dict[str, str]] = []
    for date in returns.index[:6]:
        source_value = float(source.loc[date, "Price/Earnings"])
        correct_value = float(chronological.loc[date, "Price/Earnings"])
        rows.append({
            "ticker": "AAPL",
            "target_month_end": date.strftime("%Y-%m-%d"),
            "released_descending_ffill_pe": repr(source_value),
            "chronological_availability_ffill_pe": repr(correct_value),
            "difference": repr(source_value - correct_value),
            "future_quarter_value_used": "yes" if source_value != correct_value else "no",
            "paper_result_affected": "monthly_heatmaps_and_monthly_Fama_MacBeth_boxplots",
        })
    expected_source = [11.754171] * 3 + [10.911215] * 3
    expected_correct = [11.468153] * 3 + [11.754171] * 3
    if not np.allclose([float(row["released_descending_ffill_pe"]) for row in rows], expected_source):
        raise ValueError("released monthly AAPL lookahead trace changed")
    if not np.allclose([float(row["chronological_availability_ffill_pe"]) for row in rows], expected_correct):
        raise ValueError("chronological monthly AAPL trace changed")
    return rows


def method_audit() -> list[dict[str, str]]:
    specs = [
        ("paper-listed code", "promised at Yiningww/GPT-signal", "current 404; archived Aug 16 2024 snapshot contains only README", "missing", "paper-linked system code was not released in the captured snapshot"),
        ("recovered author source", "not disclosed", "Yiningww/Thesis at pre-paper commit 434230c", "recovered_unlinked", "supports source/data/result audit but weakens discoverability"),
        ("license", "not specified", "none observed in author repository", "missing", "no explicit reuse grant"),
        ("dependency environment", "not specified", "no requirements or environment lock", "missing", "native runtime cannot be recreated exactly"),
        ("LLM model", "GPT-4", "gpt-4-1106-preview", "source_only_detail", "exact retired snapshot absent from paper"),
        ("LLM randomness", "not specified", "no seed or temperature", "missing", "fresh generation is not deterministic"),
        ("LLM output lineage", "six signals", "raw GPT output located for five; VEC absent", "partial", "one signal lacks raw generation evidence"),
        ("iterative refinement", "series of refinements / continual improvement", "each recovered call is independent", "unsupported", "experiment does not implement claimed iterative learning"),
        ("prompt scope", "method image uses ellipses", "machine-readable prompt, 7 IT stocks, Jan 2016-Jan 2017", "recovered", "source resolves most prompt ambiguity"),
        ("universe", "43 IT + 31 Health Care + 19 Energy", "93 matching workbooks and price series", "matched", "historical constituent as-of date still absent"),
        ("constituent selection", "S&P 500 companies", "fixed list; no as-of date or delisting rule", "underspecified", "survivorship/selection bias cannot be assessed"),
        ("FactSet access", "called open-source; malformed https://https URL", "credentialed proprietary source exported to xlsx", "paper_error", "raw upstream retrieval cannot be independently repeated"),
        ("factor frequency", "historical signal data", "quarterly FactSet columns", "source_only_detail", "paper does not disclose quarterly granularity"),
        ("price field", "Yahoo Finance historical returns", "unadjusted Close", "source_only_detail", "dividends are omitted"),
        ("monthly factor alignment", "future one-month returns", "descending-index ffill selects next-quarter values", "lookahead_bias", "all 1M empirical panels are temporally contaminated"),
        ("quarterly availability guard", "not specified", "+1 day then unsorted ffill", "implementation_bug", "intended guard is defeated by descending index"),
        ("missing-value imputation", "not specified", "full-period column mean", "lookahead_bias", "future values enter historical imputations"),
        ("RAPS equation", "ROE / (P/E * beta)", "ROE / (P/E ** beta)", "contradiction", "code/GPT formula alone recovers displayed results"),
        ("monthly cross-sections", "2016-2020 monthly", "current data.py hardcodes ii=19", "stale_runner", "published 1M plots require 59, implying uncommitted manual edit"),
        ("native control flow", "two-step analysis", "data.py exits after correlation before step 2", "stale_runner", "single command cannot regenerate full analysis"),
        ("plot runner", "six new-signal models plus baseline", "plot.py contains 12 candidate models and exits before save", "stale_runner", "published selection/manual state is not encoded"),
        ("correlation result lineage", "13 heatmaps", "1309/1309 cells recover with source formula", "reproduced_from_author_data", "strong result-level lineage"),
        ("Fama-MacBeth result lineage", "7 boxplots", "240/245 vector statistics recover", "partial_reproduction", "five unexplained all-sector EVC statistics differ"),
        ("all-sector EVC plot", "median shown above baseline", "all five box statistics shifted +0.02 from replay", "unexplained_difference", "shift changes qualitative above/below-baseline conclusion"),
        ("IT 3M prose", "5 out of 6 improve", "published vector medians show 6 out of 6", "paper_internal_contradiction", "prose does not match its figure"),
        ("Energy 1M generalization", "similar patterns", "only 1 of 6 medians exceeds baseline", "weak_support", "broad conclusion is not uniform across sectors/horizons"),
        ("significance", "signals meaningfully predict returns", "no reported test, interval, or multiple-testing control", "unsupported", "correlation and adjusted R2 alone do not establish significance"),
        ("p-value asset", "not cited", "unused pvalue.svg/png with undefined test/lineage", "unusable", "cannot be credited as statistical evidence"),
        ("economic evaluation", "alpha research process", "no portfolio, costs, turnover, or excess-return backtest", "missing", "economic usefulness is not demonstrated"),
        ("speed/scale claims", "faster and processes large amounts of data", "no runtime, baseline, ablation, or human study", "unsupported", "claims are not measured"),
    ]
    return [
        {
            "dimension": dimension,
            "paper": paper,
            "recovered_source_or_evidence": source,
            "assessment": assessment,
            "fidelity_impact": impact,
            "full_paper_replication_credit": "no" if assessment not in {"matched", "reproduced_from_author_data"} else "component_only",
        }
        for dimension, paper, source, assessment, impact in specs
    ]


def artifact_audit() -> list[dict[str, str]]:
    return [
        {"artifact": "arXiv v1 paper", "url": ARXIV_PDF_URL, "status": "pinned_13_pages", "relationship": "official preprint", "credit": "paper provenance"},
        {"artifact": "ACL FinNLP paper", "url": ACL_PDF_URL, "status": "pinned_12_pages", "relationship": "published workshop version", "credit": "paper provenance"},
        {"artifact": "arXiv v1 source", "url": ARXIV_SOURCE_URL, "status": "pinned_71_files_rebuilt", "relationship": "paper source and exact vector figures", "credit": "paper/result extraction"},
        {"artifact": "paper-listed GPT-signal repository", "url": PAPER_REPO_URL, "status": "current_404_one_archived_placeholder_capture", "relationship": "paper-promised code", "credit": "no system code recovered"},
        {"artifact": "Software Heritage paper-repo origin", "url": "https://archive.softwareheritage.org/api/1/origin/" + PAPER_REPO_URL + "/get/", "status": "not_found", "relationship": "archive search", "credit": "absence evidence only"},
        {"artifact": "author Thesis repository", "url": AUTHOR_REPO_URL, "status": "public_pinned_pre_paper_commit_no_license", "relationship": "author-owned unlinked source/data/output recovery", "credit": "deterministic result replay and source audit"},
    ]


def native_execution_rows() -> list[dict[str, str]]:
    return [
        {"component": "arXiv TeX source", "attempted": "yes", "status": "pass", "detail": "pdflatex shell-escape, three passes, 13-page PDF; vector/source visual match", "result_credit": "paper_build_only"},
        {"component": "author Python source compile", "attempted": "yes", "status": "pass", "detail": "6/6 tracked Python files compile in memory", "result_credit": "no"},
        {"component": "released data.py end-to-end", "attempted": "source_inspection", "status": "not_runnable_as_published", "detail": "exit after heatmap makes step 2 unreachable; monthly ii=19 is stale; yfinance dependency absent", "result_credit": "no"},
        {"component": "deterministic correlation replay", "attempted": "yes", "status": "pass_1309_of_1309", "detail": "author xlsx/CSV inputs plus released formula semantics", "result_credit": "author_data_replay"},
        {"component": "deterministic boxplot replay", "attempted": "yes", "status": "partial_240_of_245", "detail": "five all-sector EVC statistics differ by a uniform +0.02 paper shift", "result_credit": "author_data_replay_except_five"},
        {"component": "GPT-4 signal generation", "attempted": "no", "status": "not_reproducible", "detail": "retired gpt-4-1106-preview, no seed/temperature, no request IDs; raw output recovered for 5/6", "result_credit": "historical_output_lineage_only"},
        {"component": "full paper pipeline", "attempted": "no", "status": "not_faithfully_defined", "detail": "LLM snapshot unavailable and monthly source path contains lookahead; a fresh run would not be comparable", "result_credit": "no_end_to_end_credit"},
    ]


def readme(manifest: dict[str, Any]) -> str:
    rate = 100 * manifest["published_result_units_reproduced"] / manifest["published_result_units"]
    return f"""# GPT-Signal paper/source replication audit

This package audits the official 13-page arXiv v1 paper, the 12-page ACL
FinNLP version, all 71 arXiv source files, the deleted paper-listed repository,
its surviving Wayback capture, and all {manifest['author_source_files']:,}
tracked files in the author-owned `Yiningww/Thesis` repository. The author
repository is not linked by the paper, but its pre-publication commit contains
the exact company universe, FactSet workbooks, Yahoo price caches, GPT output
CSVs, formulas, and analysis logic needed to trace the published figures.

## Honest verdict

- **Published quantitative units regenerated from author inputs/source semantics:
  {manifest['published_result_units_reproduced']}/{manifest['published_result_units']}
  ({rate:.3f}%).** This comprises all 1,309 displayed heatmap cells and 240/245
  boxplot statistics. It is strong result-level recovery, not an end-to-end
  regeneration of GPT-Signal.
- The five failures are the all-sector EVC box. Every vector statistic in that
  box is exactly 0.02 above the deterministic replay. The unexplained shift
  changes EVC's median from below the baseline to above it.
- The paper's RAPS equation uses `ROE / (P/E * beta)`, while the raw GPT output,
  released code, and all published cells use `ROE / (P/E ** beta)`. The printed
  equation misses 104/1,309 heatmap cells at two-decimal display precision.
- The 1-month pipeline is not temporally faithful: descending quarterly
  workbooks are forward-filled without sorting, so January/February use the
  coming March quarter, April/May use June, and so on. Full-period mean
  imputation introduces a second future-data path.
- No LLM call was made. The recovered model is `gpt-4-1106-preview`, with no
  seed or temperature; that snapshot is retired. Raw generation output exists
  for five of six published signals, but VEC lacks raw GPT lineage.

## Why 99.678% result recovery is not 99.678% paper fidelity

The result grids can be replayed because the author repository preserved the
post-generation inputs and code semantics. The scientific procedure is less
faithful: the paper-listed repository was only a one-file placeholder in the
surviving post-workshop capture; the real source is unlinked and unlicensed;
there is no dependency lock; the current runner exits before step 2 and
hardcodes the wrong monthly loop length; the paper formula conflicts with its
results; monthly tests leak future data; and no portfolio, transaction-cost,
runtime, statistical-significance, or human-efficiency experiment supports the
broad alpha, speed, scale, or continual-refinement claims.

## Evidence artifacts

- `correlation_cell_reproduction.csv` and `correlation_matrix_summary.csv`:
  every displayed heatmap cell under both the source/GPT and printed-paper RAPS
  formulas.
- `boxplot_stat_reproduction.csv` and `boxplot_figure_summary.csv`: all five
  displayed box statistics for seven models across seven figures.
- `formula_lineage.csv`, `monthly_lookahead_trace.csv`, and
  `method_specification_audit.csv`: formula provenance, a concrete AAPL
  availability trace, and paper/source fidelity boundaries.
- `author_source_inventory.csv`, `paper_source_inventory.csv`,
  `source_provenance.json`, and `discovery_evidence.csv`: complete pinned source
  and artifact lineage. Credential-like strings are counted and redacted; no
  secret value is emitted.
- `native_execution.csv`, `native_execution.json`, and `manifest.json`: exact
  component outcomes and the fail-closed final verdict.
"""


def build(args: argparse.Namespace) -> dict[str, Any]:
    arxiv_text = validate_pdf(args.arxiv_pdf.resolve(), EXPECTED_ARXIV_PDF_SHA256, EXPECTED_ARXIV_PAGES, "arXiv v1")
    acl_text = validate_pdf(args.acl_pdf.resolve(), EXPECTED_ACL_PDF_SHA256, EXPECTED_ACL_PAGES, "ACL")
    if "Empirical Asset Pricing with Large Language Model Agents" in acl_text:
        raise ValueError("unexpected later-paper title in GPT-Signal ACL PDF")
    paper_source = paper_source_inventory(args.source_archive.resolve(), args.source_dir.resolve())
    author_source, author_facts = author_source_inventory(args.author_repo.resolve())
    discovery = validate_discovery_evidence(args.evidence_dir.resolve())

    data = ReplayData(args.author_repo.resolve())
    workbook_count = sum(
        (data.root / sector / "DEC start" / f"{ticker}.xlsx").is_file()
        for sector, tickers in GROUPS["all"] for ticker in tickers
    )
    full_price_count = sum(
        (data.root / "historical_return" / f"{ticker}2015-12-31-2020-12-31.csv").is_file()
        for _, tickers in GROUPS["all"] for ticker in tickers
    )
    if workbook_count != 93 or full_price_count != 93:
        raise ValueError(f"relevant input coverage changed: {workbook_count}, {full_price_count}")

    correlations, correlation_summaries = correlation_reproduction(data, args.source_dir.resolve())
    boxes, box_summaries = boxplot_reproduction(data, args.source_dir.resolve())
    formulas = formula_lineage(args.author_repo.resolve(), args.source_dir.resolve())
    lookahead = lookahead_trace(data)
    methods = method_audit()
    artifacts = artifact_audit()
    native = native_execution_rows()

    reproduced = sum(row["source_code_power_match"] == "yes" for row in correlations) + sum(
        row["match_tolerance_1e-4"] == "yes" for row in boxes
    )
    total = len(correlations) + len(boxes)
    if (reproduced, total) != (1549, 1554):
        raise ValueError(f"overall published result recovery changed: {reproduced}/{total}")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in (
        ("paper_source_inventory.csv", paper_source),
        ("author_source_inventory.csv", author_source),
        ("discovery_evidence.csv", discovery),
        ("artifact_access_audit.csv", artifacts),
        ("correlation_cell_reproduction.csv", correlations),
        ("correlation_matrix_summary.csv", correlation_summaries),
        ("boxplot_stat_reproduction.csv", boxes),
        ("boxplot_figure_summary.csv", box_summaries),
        ("formula_lineage.csv", formulas),
        ("monthly_lookahead_trace.csv", lookahead),
        ("method_specification_audit.csv", methods),
        ("native_execution.csv", native),
    ):
        write_csv(output / name, rows)

    source_provenance = {
        "paper": TITLE,
        "authors": AUTHORS,
        "arxiv_record": ARXIV_RECORD,
        "arxiv_version": "v1_only_as_of_pinned_record",
        "arxiv_pdf_url": ARXIV_PDF_URL,
        "arxiv_pdf_sha256": EXPECTED_ARXIV_PDF_SHA256,
        "arxiv_pdf_pages": EXPECTED_ARXIV_PAGES,
        "arxiv_pdf_pages_visually_inspected": EXPECTED_ARXIV_PAGES,
        "acl_record": ACL_RECORD,
        "acl_pdf_url": ACL_PDF_URL,
        "acl_pdf_sha256": EXPECTED_ACL_PDF_SHA256,
        "acl_pdf_pages": EXPECTED_ACL_PAGES,
        "acl_pdf_pages_visually_inspected": EXPECTED_ACL_PAGES,
        "arxiv_source_url": ARXIV_SOURCE_URL,
        "arxiv_source_sha256": EXPECTED_SOURCE_SHA256,
        "arxiv_source_files": len(paper_source),
        "source_rebuild_pdf_sha256": EXPECTED_REBUILT_PDF_SHA256,
        "source_rebuild_pages": EXPECTED_ARXIV_PAGES,
        "source_rebuild_pages_visually_inspected": EXPECTED_ARXIV_PAGES,
        "paper_listed_repository": PAPER_REPO_URL,
        "paper_listed_repository_status": "current_404_archived_2024_08_16_placeholder_only_at_that_capture",
        "archived_placeholder_repository_id": 818681062,
        "archived_placeholder_head": "212518b57a66e65845793a25850e3bbb5187f707",
        "archived_placeholder_tracked_files": 1,
        "author_repository": AUTHOR_REPO_URL,
        "author_repository_relationship": "author_owned_pre_publication_source_recovery_not_linked_by_paper",
        **author_facts,
        "relevant_companies": 93,
        "relevant_factset_workbooks": workbook_count,
        "relevant_full_period_yahoo_csvs": full_price_count,
    }
    write_json(output / "source_provenance.json", source_provenance)

    native_json = {
        "author_source_available": True,
        "paper_listed_source_available": False,
        "paper_listed_source_archived_placeholder_only": True,
        "paper_tex_rebuilt": True,
        "tracked_python_files_compiled": 6,
        "deterministic_correlation_cells_reproduced": 1309,
        "deterministic_correlation_cells_total": 1309,
        "deterministic_boxplot_statistics_reproduced": 240,
        "deterministic_boxplot_statistics_total": 245,
        "llm_calls_made": 0,
        "llm_generation_reproduced": False,
        "full_end_to_end_pipeline_reproduced": False,
        "full_end_to_end_reason": "retired_nondeterministic_LLM_snapshot_plus_stale_runner_and_monthly_lookahead",
        "paper_result_credit": "partial_author_data_and_source_semantics_replay_not_full_paper_replication",
    }
    write_json(output / "native_execution.json", native_json)

    manifest = {
        "audit": "GPT-Signal official-paper, paper-source, deleted-artifact, and recovered-author-source audit",
        "overall_fidelity": "partial_1549_of_1554_published_quantitative_units_replayed_from_author_data_no_end_to_end_LLM_replication_monthly_lookahead_present",
        "official_papers_audited": 2,
        "official_pdf_pages_audited": EXPECTED_ARXIV_PAGES + EXPECTED_ACL_PAGES,
        "official_pdf_pages_visually_inspected": EXPECTED_ARXIV_PAGES + EXPECTED_ACL_PAGES,
        "rebuilt_pdf_pages_visually_inspected": EXPECTED_ARXIV_PAGES,
        "paper_source_files": len(paper_source),
        "author_source_files": len(author_source),
        "author_source_bytes": author_facts["tracked_bytes"],
        "compiled_python_files": author_facts["compiled_python_files"],
        "plaintext_credential_matches_redacted": author_facts["plaintext_credential_matches_redacted"],
        "published_correlation_cells": len(correlations),
        "published_correlation_cells_reproduced": sum(row["source_code_power_match"] == "yes" for row in correlations),
        "paper_equation_correlation_cells_reproduced": sum(row["paper_equation_multiply_match"] == "yes" for row in correlations),
        "published_boxplot_statistics": len(boxes),
        "published_boxplot_statistics_reproduced": sum(row["match_tolerance_1e-4"] == "yes" for row in boxes),
        "published_result_units": total,
        "published_result_units_reproduced": reproduced,
        "published_result_unit_recovery_rate": reproduced / total,
        "new_signal_medians_above_baseline": sum(int(row["new_signal_medians_above_baseline"]) for row in box_summaries),
        "new_signal_median_comparisons": 42,
        "raw_gpt_signal_outputs_recovered": 5,
        "published_signals": 6,
        "llm_calls_made": 0,
        "monthly_lookahead_present": True,
        "paper_code_formula_contradictions": 1,
        "unexplained_plot_statistics": 5,
        "full_end_to_end_pipeline_reproduced": False,
        "paper_result_credit": "partial_author_data_and_source_semantics_replay_not_full_paper_replication",
    }
    write_json(output / "manifest.json", manifest)
    (output / "README.md").write_text(readme(manifest), encoding="utf-8")
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--arxiv-pdf", type=Path, default=ROOT / "literature_review/papers/59_gpt_signal_generative_ai_for_semi_automated_feature_engineering_arxiv_v1.pdf")
    result.add_argument("--acl-pdf", type=Path, default=ROOT / "literature_review/papers/60_gpt_signal_generative_ai_for_semi_automated_feature_engineering_acl_2024.pdf")
    result.add_argument("--source-archive", type=Path, required=True)
    result.add_argument("--source-dir", type=Path, required=True)
    result.add_argument("--author-repo", type=Path, required=True)
    result.add_argument("--evidence-dir", type=Path, required=True)
    result.add_argument("--output", type=Path, default=ROOT / "paper_runs/paper_replication_audits/gpt_signal")
    return result


def main() -> None:
    print(json.dumps(build(parser().parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
