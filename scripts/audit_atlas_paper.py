#!/usr/bin/env python3
"""Build a fail-closed paper/source/StockSim audit for ATLAS."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/atlas_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/atlas"
WORK_ID = "CensusArxiv251015949"
SYSTEM_ID = "SYS-ATLAS"
ARXIV_ID = "2510.15949"
REPOSITORY_URL = "https://github.com/harrypapadakis/StockSim"
REPOSITORY_HEAD = "c1a25c195df4c93b2db4a748f80ceae0f1c9fe50"
STOCKSIM_HISTORY_COMMITS = (
    "48284a3ffbfdbfa2babef2330d238953ad4dc729",
    "294286ef454dd3117ce5722a7e0c33130d24c2f8",
    "c66bd75df824d458e70fe7775e607306194101ea",
    "b391cd859625908411bdef73778c6ddde5c0d682",
    "c6c52755a711c935957100dd69f6ce32195a8862",
    "9af70a58c032619928a52fe040eb6e1d21087b3c",
    "5975b94d128e05c48a0d49ae63293ecf8027e209",
    "3b175dabd71f97858fcc89e6bb7ec3fb61f69be4",
    "81edcf1993497d7af79d7503682f6e92dae9a55a",
    "66388ebccca9b692078b5d3210751a7c624d8d61",
    "bb00f483516dca1880dfb2abb2d5c312842d49d0",
    "3f4e16c068aef3e0eb7cea888e9dbe57e2f661b0",
    "06f6e3a7607d16f73c2a15138ca8257b9cbcc571",
    "b607c5f1fcb61d963a0a8853c83253f6af074d7a",
    "3cf30017accda061d2ac0e9f2e2f5d3319ab6b37",
    "bd34b2ebab06390e3d6d90195e7e5d57c779942f",
    REPOSITORY_HEAD,
    "c4a9cf368d2d9a5a01a477f266db0cd1e94edc10",
    "8cc07265d25d59c6f30402e63a5e1b6b6f83b759",
    "49ea2e5bc850a2c2aee0172db2d072c46de82e60",
)
STOCKSIM_INITIAL_COMMIT = STOCKSIM_HISTORY_COMMITS[0]
STOCKSIM_WEBSITE_HEAD = STOCKSIM_HISTORY_COMMITS[-1]
STOCKSIM_HISTORY_PATHS_SHA256 = "5913570cb5553dbdba8a2c55c648fdc802270f9ead3f7655d55481c08fa950d4"
STOCKSIM_OFFICIAL_REFS = ("refs/remotes/origin/main", "refs/remotes/origin/website")
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_HEADS = {
    "refs/remotes/forks/Young20050706/main": REPOSITORY_HEAD,
    "refs/remotes/forks/colsonSung/main": REPOSITORY_HEAD,
    "refs/remotes/forks/jingmouren/main": REPOSITORY_HEAD,
    "refs/remotes/forks/programmermw1986/main": REPOSITORY_HEAD,
    "refs/remotes/forks/shmaiii/dashboard": "e2f690b54be6f2b05e4b9d448b538f594ff663f2",
    "refs/remotes/forks/shmaiii/fix/market-data-source-timestamp": "7917911c790ed1ee1dbb6e423f855b7e789ff340",
    "refs/remotes/forks/shmaiii/fix/settlement-barrier-consistency": "89bff8c642a4e1b04b6f3a5124656a705db29230",
    "refs/remotes/forks/shmaiii/main": "4b59993913841a7249dd031e8f186caa1988892f",
    "refs/remotes/forks/shmaiii/orderbook-self-trade-prevention": "ee3a361f79ad2ec3ffedd2d5790b7435d6728829",
    "refs/remotes/forks/shmaiii/portfolio-metrics-state": "da8ae9bad605b0385aded617769127186df21f66",
    "refs/remotes/forks/shmaiii/research/diversity-infrastructure": "faaafbbf388eaaa736090d954e153746195995fa",
}
PUBLIC_FORK_REPOSITORIES = {
    "Young20050706": "Young20050706/StockSim",
    "colsonSung": "colsonSung/StockSim",
    "jingmouren": "jingmouren/harrypapa2002_StockSim",
    "programmermw1986": "programmermw1986/StockSim",
    "shmaiii": "shmaiii/StockSim",
}
PUBLIC_FORK_AHEAD_COUNTS = {
    "refs/remotes/forks/Young20050706/main": 0,
    "refs/remotes/forks/colsonSung/main": 0,
    "refs/remotes/forks/jingmouren/main": 0,
    "refs/remotes/forks/programmermw1986/main": 0,
    "refs/remotes/forks/shmaiii/dashboard": 4,
    "refs/remotes/forks/shmaiii/fix/market-data-source-timestamp": 6,
    "refs/remotes/forks/shmaiii/fix/settlement-barrier-consistency": 8,
    "refs/remotes/forks/shmaiii/main": 6,
    "refs/remotes/forks/shmaiii/orderbook-self-trade-prevention": 6,
    "refs/remotes/forks/shmaiii/portfolio-metrics-state": 5,
    "refs/remotes/forks/shmaiii/research/diversity-infrastructure": 7,
}
PUBLIC_FORK_CHANGED_PATHS = {
    "Dockerfile",
    "agents/agent.py",
    "agents/aml/__init__.py",
    "agents/aml/institutional_trader.py",
    "agents/aml/market_maker_trader.py",
    "agents/aml/retail_trader.py",
    "agents/benchmark_traders/trader.py",
    "exchanges/exchange_agent.py",
    "main_launcher.py",
    "simulation/simulation_clock.py",
    "test_orderbook_self_trade_prevention.py",
    "utils/alpha_vantage_client.py",
    "utils/orders.py",
}
PUBLIC_FORK_CHANGED_PATHS_SHA256 = "d4eeeee662e8d43df65e45efbdc5aecdbfad2c143ff4f3abd41d9001bc2f3b70"
ATLAS_AUTHOR_NAMES = {
    "Charidimos Papadakis",
    "Angeliki Dimitriou",
    "Giorgos Filandrianos",
    "Maria Lymperaiou",
    "Konstantinos Thomas",
    "Giorgos Stamou",
}
STOCKSIM_CHARTS = {
    "charts/LLY_stocksim_chart.html": (13, 313, False, "511f4b8658a532df3bdaf63de78b174f5b7d81aa6459c63d13961c6ee42dc2a0"),
    "charts/NVDA.html": (10, 293, False, "ac4b8fa14f907ffa05254b4d53a23323e3a9241d7f6779df08255501efcb07fb"),
    "charts/NVDA_stocksim_chart.html": (10, 313, False, "0b4bea58f68fdb8bd4aaacf5c11a5191a00ce120c233a1a369a4a3163017e1be"),
    "charts/XOM.html": (8, 293, True, "7cbd9cf03e459284fcc72599ec820666caf65e9f1edb38ee4b676d947c85da37"),
}

VERSION_SPECS = {
    "v1": ("2025-10-10T13:01:51Z", 37, 9, 4_583_668, 13, 9),
    "v2": ("2026-01-08T13:08:59Z", 43, 8, 4_520_462, 14, 9),
    "v3": ("2026-04-09T13:50:25Z", 43, 8, 4_520_293, 14, 9),
    "v4": ("2026-05-01T17:56:23Z", 43, 8, 4_520_293, 14, 9),
    "v5": ("2026-05-20T15:24:21Z", 43, 6, 632_112, 13, 10),
}

# Each unit is one printed empirical scalar, including every mean and displayed
# standard deviation. Provider/setup identifier tables are specification, not results.
RESULT_TABLES = {
    "tab:lly_results": (2, 235),
    "tab:xom_results": (2, 235),
    "tab:nvda_results": (2, 235),
    "tab:gpto4_mini_ablation": (2, 120),
    "tab:nvda_additional_results": (2, 167),
    "tab:xom_additional_results": (2, 168),
    "tab:lly_additional_results": (2, 168),
    "tab:nvda_main_results": (2, 150),
    "tab:xom_main_results": (2, 150),
    "tab:lly_main_results": (2, 150),
    "tab:reflection_cost": (1, 6),
}

PINS = {
    "arxiv-abs.html": "62ceccc3dc017bf9cd94fdb785e8b0910121019abc44a606f60e964d99576f89",
    "arxiv-api.xml": "93fc81863ff9570ecc9d3269022675c940a4229fbc3b58c0235c82361dd73c0d",
    "atlas-v1.pdf": "d7a9bda47c3451b5aef2cae5dd66e4e1db67e1be6a447b46c6bc3906ca98c034",
    "atlas-v2.pdf": "a4e9f8a261c9a07e015d2389e4b9523147db3d43b4d9d52d15732db3c71dff1d",
    "atlas-v3.pdf": "e44d5795b7d20ba6023d2ae0e335a7e9f73495702ee7eaedc625e87f5adcf337",
    "atlas-v4.pdf": "e265989150417b7995971e1fb5e4aee660c010ee6fd923601a6e71958ffb5dc4",
    "atlas-v5.pdf": "c648c9f58811dcad578b41d56e06760c715d3b8c6314aad01170536f62d84bf7",
    "atlas-v1-source.tar": "c3a390bdc21249bdb0847786b04f715c0a86537f337facb00feaf613350fae33",
    "atlas-v2-source.tar": "2151e42511123c1cc4c6d730a47347b12a05ccda3333a78fe652da48d97807ad",
    "atlas-v3-source.tar": "2ccb077f6d8dd8e5789fef0ebc3b8be1d6e915a9abb6a28738215aa2987493d3",
    "atlas-v4-source.tar": "79513f09ac59a3b5137aae6168b9b63204302d7afe59c5217dd36d5f7dd392cf",
    "atlas-v5-source.tar": "7b6ead28d2daed5f734b3b2d3c078e6051aa0a0e64fdddda53772f8fa9caad4f",
    "build-v1/acl_latex.pdf": "1e4c6a6cb0b9dcbe582f0dd395c4f7c852fbf756dfe284fe04ead7930e0ddf82",
    "build-v2/acl_latex.pdf": "afc5e7a6ac42e897e64c2912a5c9adf565a8129c2de8e07c04f23f51fb7bd25e",
    "build-v3/acl_latex.pdf": "1f4f32c125f94e0c203e75941504687f229642b8dd1dea9273478e07e2635071",
    "build-v4/acl_latex.pdf": "5cbb6f6516387f1304b796658e6a344ac86b7c0435d3d0f9f7d9bc5850d97305",
    "build-v5/acl_latex.pdf": "7f045fd40b39c8ec49c56143819f98519b1f41681331f4b5bbc23611be29b331",
    "release/c1a25c195df4c93b2db4a748f80ceae0f1c9fe50.tar.gz": "824b8b041ff5bf8733d2f755015432eefdc94fdb65fd53b1d1f22a2d99696db7",
    "release/repo.json": "e113aba5b3e95d539448d75a83f3104a5b4ab85851f07e87f7caf1539832a829",
    "release/commits.json": "08bcdd3d6e0f214c8d6acf613428a850172886d1d5496e1a983ad4a31618e9df",
    "release/branches.json": "99b98465e73b0a9e84a8f0d319709f2a34cea72ea4c24587c79d2e1143d4f59b",
    "release/tags.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "release/releases.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "release/search--Adaptive-Trading-with-LLM-AgentS-.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "release/search-2510-15949.json": "4e249914105697662a90cbfcc973d3aa4b816fafebc211d2a7148ae9f935d491",
    "release/search-Adaptive-OPRO.json": "95ad09ef6bf634ec6648c54b8d3ca9b6ba706775801651acd8afd63b22f19f8d",
    "release/search-configs-o4-mini-adaptive-opro-config-yaml.json": "0dbc6288a9540c888f8e02900f853ef386d313c04e33d81699a5738e0b336c10",
    "native/as-declared-asyncio-import-status.txt": "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
    "native/as-declared-asyncio-import.txt": "6f5081c3aac561303daa14bafe3b87c67d5d0dfae05781c9142488f4c590834a",
    "native/post-adjustment-asyncio-import-status.txt": "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    "native/post-adjustment-asyncio-import.txt": "1b49f29540ae03c5fcd553d1777d4c5765f1f9829991486d34916a10bf06c102",
    "native/pip-check-status.txt": "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    "native/pip-check.txt": "9261363b733079a641c2e4cc9bc46ffa1d8336945a87f807b6cf68847dbc9b09",
    "native/compileall-status.txt": "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    "native/compileall.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "native/module-imports.json": "a01102b7a0f5e6d104323d03385df2e71e5907578305ba6ce79685bec7e1a2eb",
    "native/component-checks.json": "ac6d709716577a7576798386ff01b6c08ea4b44628e353717f2ff744653b82e2",
    "native/environment.txt": "a2c9623016744b5352c77141be03fc3b29d689cf4086101f9460a34257f0a42e",
    "native/launcher-status.txt": "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
    "native/launcher-after-audit-adjustment.txt": "5a1f2a5cd5ad9fa90889ba57315fead93b7fac3c1f3b727f31fa1bc9e021f103",
}

_CONTACTS = {
    1: ["8743e549229f2c18587fb89e6185fe9dbd6bf35c0c97fc4f982315a50550f3f7", "92663aeac20c387af7755eb1d5e27ece624f8cd7c6f73a2d527025f4f1e4ae6f", "acd6e64875fdf4a942bba6c497eb4ff10ed5234bf25f8ce13cf49a043f2611cd", "ec8f58af6cdecde12436fc092de1f61086d297bd11dcd6aa40d9e627d4fbf660", "3eb111c58a9c6e45019361770a412e695cf4e17c402c4e4af6d87a26fb2538d7"],
    2: ["a15e0770444f27254dad38e5627b79e790127b7459f9751de1b59e88917e46eb", "bec9dcb2c15e69c2fc4c1eda298a1cfd5231e69f1d17b1c912fbb9c01ee66254", "67eefb56ad2225b5d41e8af45c63551478625ef66146acb380f8b698480b5c23", "f90a9f23520b9a9ac5cabe6c0b59c9d1486e5c7e0d2df77596d00d2c1c4e2406", "8b23c611fd973d034f02222b9d86bf3d1016c239c14c7645bd0fe21586983477"],
    3: ["5e37993442e2de330836bb198af9fac1e13949b3e41e538fdc2ca642e9816d74", "bec9dcb2c15e69c2fc4c1eda298a1cfd5231e69f1d17b1c912fbb9c01ee66254", "67eefb56ad2225b5d41e8af45c63551478625ef66146acb380f8b698480b5c23", "f90a9f23520b9a9ac5cabe6c0b59c9d1486e5c7e0d2df77596d00d2c1c4e2406", "8b23c611fd973d034f02222b9d86bf3d1016c239c14c7645bd0fe21586983477"],
    4: ["2228f9ac27adf4fabde9db510740ac78c1a6e15c53eb170aee04db9320685580", "bec9dcb2c15e69c2fc4c1eda298a1cfd5231e69f1d17b1c912fbb9c01ee66254", "67eefb56ad2225b5d41e8af45c63551478625ef66146acb380f8b698480b5c23", "f90a9f23520b9a9ac5cabe6c0b59c9d1486e5c7e0d2df77596d00d2c1c4e2406", "8b23c611fd973d034f02222b9d86bf3d1016c239c14c7645bd0fe21586983477"],
    5: ["d81b1b456c63d2217f0818c887f247c25f221bb0b63e707256b8b3227269d679", "9e1f02ba43f99a3194b95e332d3451061233caf7a879a239b1096ae03bc57171", "fdc6e169196a5dc811a823f4a5c5c5efb75e7f9999acb7a7b4c3f73c2b8ef85e", "a0bdc35176dc7aaa6e1e2fdc80dfe247727ee36b0283352aa80f3c112b39319a", "a2a689c6dbe91880c9444159153c6cd246f03c25510609a22af9c99b009cab94"],
}
for _version, _hashes in _CONTACTS.items():
    for _index, _digest in enumerate(_hashes):
        PINS[f"viz/v{_version}/contact-{_index:02d}.jpg"] = _digest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    ).stdout


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def validate_tar(path: Path) -> list[tarfile.TarInfo]:
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
    for member in members:
        pure = PurePosixPath(member.name)
        if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
            raise ValueError(f"unsafe archive member: {member.name}")
    return [member for member in members if member.isfile()]


def tar_texts(path: Path) -> dict[str, str]:
    values = {}
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            if member.isfile() and PurePosixPath(member.name).suffix.lower() in {
                ".py", ".md", ".txt", ".yaml", ".yml", ".json", "",
            }:
                stream = archive.extractfile(member)
                if stream:
                    values[member.name] = stream.read().decode("utf-8", errors="replace")
    return values


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    inventories = {}
    for version, (_, pages, files, size, tables, figures) in VERSION_SPECS.items():
        members = validate_tar(scratch / f"atlas-{version}-source.tar")
        if (len(members), sum(item.size for item in members)) != (files, size):
            raise ValueError(f"{version} source inventory changed")
        tex = (scratch / f"source-{version}/acl_latex.tex").read_text(encoding="utf-8")
        if (tex.count(r"\begin{table"), tex.count(r"\begin{figure")) != (tables, figures):
            raise ValueError(f"{version} manuscript environment inventory changed")
        if len(PdfReader(scratch / f"atlas-{version}.pdf").pages) != pages:
            raise ValueError(f"{version} official page count changed")
        if len(PdfReader(scratch / f"build-{version}/acl_latex.pdf").pages) != pages:
            raise ValueError(f"{version} rebuilt page count changed")
        inventories[version] = members
    release = validate_tar(
        scratch / f"release/{REPOSITORY_HEAD}.tar.gz"
    )
    if (len(release), sum(item.size for item in release)) != (81, 31_949_454):
        raise ValueError("StockSim archive inventory changed")
    return {"source": inventories, "release": release}


def table_block(tex: str, label: str) -> str:
    marker = r"\label{" + label + "}"
    position = tex.index(marker)
    begin = max(tex.rfind(r"\begin{table}", 0, position), tex.rfind(r"\begin{table*}", 0, position))
    end = tex.index(r"\end{table", position)
    if begin < 0:
        raise ValueError(f"missing table begin for {label}")
    return tex[begin:end]


def result_rows(tex: str) -> list[dict[str, Any]]:
    rows = []
    for label, (first_result_column, expected) in RESULT_TABLES.items():
        values = []
        for raw_row in re.split(r"\\\\(?:\[[^]]*\])?", table_block(tex, label)):
            raw_row = re.sub(r"(?<!\\)%.*", "", raw_row)
            if "&" not in raw_row:
                continue
            for cell in raw_row.split("&")[first_result_column:]:
                cell = cell.replace("{,}", "")
                values.extend(re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", cell))
        if len(values) != expected:
            raise ValueError(f"{label} has {len(values)} printed units, expected {expected}")
        for index, value in enumerate(values, 1):
            rows.append({
                "version": "v5", "table_label": label,
                "printed_numeric_unit": index, "printed_value": value,
                "source_document_recovered": True,
                "author_native_experiment_executed": False,
                "published_result_regenerated": False,
                "paper_result_credit": False,
                "blocking_reason": (
                    "ATLAS modifications, exact config, frozen market/news/fundamental inputs, "
                    "model requests/responses, prompts/trajectories, seeds, and result arrays are absent"
                ),
            })
    return rows


def figure_rows() -> list[dict[str, Any]]:
    specs = (
        ("fig:fig_1", 1, 0, "ATLAS architecture"),
        ("fig:protocol", 1, 0, "online Adaptive-OPRO protocol"),
        ("fig:opro_gain", 1, 1, "ROI gain over baseline"),
        ("fig:opro_performance", 3, 3, "ROI by backbone in three regimes"),
        ("unlabeled_daily_weekly_reflection", 1, 1, "daily versus weekly reflection ROI"),
        ("fig:header_evolution", 1, 0, "prompt header diff"),
        ("fig:architecture_evolution", 1, 0, "prompt architecture diff"),
        ("fig:workflow_evolution", 1, 0, "prompt workflow diff"),
        ("fig:intermediate_optimization", 1, 0, "intermediate evolved prompt"),
        ("fig:final_optimization", 1, 0, "final evolved prompt"),
    )
    return [{
        "version": "v5", "figure": figure, "panels": panels,
        "empirical_panels": empirical, "description": description,
        "rendered_author_figure_recovered": True,
        "author_latex_plot_coordinates_recovered": empirical > 0,
        "author_native_figure_regenerated": False,
        "paper_result_credit": False,
    } for figure, panels, empirical, description in specs]


def plotly_data(value: bytes) -> list[dict[str, Any]]:
    text = value.decode("utf-8")
    marker = text.rfind("Plotly.newPlot")
    if marker < 0:
        raise ValueError("Plotly payload missing")
    start = text.index("[", marker)
    data, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(data, list):
        raise ValueError("Plotly trace payload is not a list")
    return data


def xom_published_roi_means(tex: str) -> list[float]:
    values: list[float] = []
    for raw_row in re.split(r"\\\\(?:\[[^]]*\])?", table_block(tex, "tab:xom_results")):
        raw_row = raw_row.replace(r"\&", "and")
        cells = raw_row.split("&")
        if len(cells) < 3:
            continue
        match = re.search(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", cells[2])
        if match:
            values.append(float(match.group()))
    if len(values) != 26:
        raise ValueError(f"XOM ROI mean inventory changed: {len(values)}")
    return values


def stocksim_history_rows(
    scratch: Path, tex: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Audit every public StockSim commit and recover deleted precursor outputs."""
    repo = scratch / "stocksim"
    if git(repo, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise ValueError("StockSim history checkout is shallow")
    commits = git(repo, "rev-list", "--reverse", *STOCKSIM_OFFICIAL_REFS).splitlines()
    if commits != list(STOCKSIM_HISTORY_COMMITS):
        raise ValueError(f"StockSim public history changed: {commits}")
    unreachable = git(
        repo, "fsck", "--full", "--no-reflogs", "--unreachable", "--no-progress"
    ).strip()
    if unreachable:
        raise ValueError(f"StockSim has unreviewed unreachable objects: {unreachable}")
    branches = json.loads((scratch / "release/branches.json").read_text())
    branch_heads = sorted((row["name"], row["commit"]["sha"]) for row in branches)
    if branch_heads != sorted((("main", REPOSITORY_HEAD), ("website", STOCKSIM_WEBSITE_HEAD))):
        raise ValueError(f"StockSim public branches changed: {branch_heads}")
    if json.loads((scratch / "release/tags.json").read_text()) or json.loads(
        (scratch / "release/releases.json").read_text()
    ):
        raise ValueError("StockSim now exposes an unreviewed tag or release")

    all_paths = sorted(
        set(
            git(
                repo, "-c", "core.quotePath=false", "log", *STOCKSIM_OFFICIAL_REFS, "--name-only",
                "--pretty=format:",
            ).splitlines()
        )
        - {""}
    )
    paths_digest = sha256_bytes(("\n".join(all_paths) + "\n").encode())
    if len(all_paths) != 107 or paths_digest != STOCKSIM_HISTORY_PATHS_SHA256:
        raise ValueError(f"StockSim historical path surface changed: {len(all_paths)} {paths_digest}")

    rows: list[dict[str, Any]] = []
    search_pattern = r"ATLAS|Adaptive[-_ ]OPRO|2510[.]15949|o4-mini-adaptive"
    for commit in commits:
        authored_at, subject = git(
            repo, "show", "-s", "--format=%aI%x09%s", commit
        ).rstrip().split("\t", 1)
        paths = git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()
        source_paths = [path for path in paths if path.endswith(".py")]
        chart_paths = [path for path in paths if path.startswith("charts/")]
        order_paths = [path for path in paths if path.startswith("orders/")]
        search = subprocess.run(
            [
                "git", "-C", str(repo), "grep", "-I", "-l", "-i", "-E",
                search_pattern, commit, "--", "*.py", "*.yaml", "*.yml", "*.json",
                "*.md", "*.txt", "*.j2",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if search.returncode not in {0, 1}:
            raise ValueError(f"StockSim history search failed at {commit}: {search.stderr}")
        paper_specific_paths = search.stdout.splitlines()
        rows.append({
            "commit": commit,
            "authored_at": authored_at,
            "subject": subject,
            "tracked_paths": len(paths),
            "python_source_paths": len(source_paths),
            "historical_chart_paths": len(chart_paths),
            "historical_order_payload_paths": len(order_paths),
            "paper_specific_identifier_or_adaptive_opro_paths": len(paper_specific_paths),
            "paper_specific_system_source_found": bool(paper_specific_paths),
        })
    if any(row["python_source_paths"] != 43 for row in rows) or any(
        row["paper_specific_system_source_found"] for row in rows
    ):
        raise ValueError("StockSim source-history boundary changed")

    artifact_rows: list[dict[str, Any]] = []
    xom_portfolio: list[float] | None = None
    xom_orders = 0
    for path, (expected_traces, expected_candles, has_output, expected_sha) in STOCKSIM_CHARTS.items():
        value = git_bytes(repo, "show", f"{STOCKSIM_INITIAL_COMMIT}:{path}")
        if sha256_bytes(value) != expected_sha:
            raise ValueError(f"StockSim historical chart changed: {path}")
        traces = plotly_data(value)
        candles = next(trace for trace in traces if trace.get("type") == "candlestick")
        portfolio = next((trace for trace in traces if trace.get("name") == "Portfolio Value"), None)
        orders = next((trace for trace in traces if trace.get("name") == "LLM Trading Orders"), None)
        if len(traces) != expected_traces or len(candles["x"]) != expected_candles:
            raise ValueError(f"StockSim historical chart dimensions changed: {path}")
        if (portfolio is not None) is not has_output or (orders is not None) is not has_output:
            raise ValueError(f"StockSim historical output classification changed: {path}")
        if portfolio:
            xom_portfolio = [float(value) for value in portfolio["y"]]
            xom_orders = len(orders["x"])
        artifact_rows.append({
            "commit": STOCKSIM_INITIAL_COMMIT,
            "path": path,
            "sha256": expected_sha,
            "plotly_traces": len(traces),
            "market_candles": len(candles["x"]),
            "first_market_date": candles["x"][0],
            "last_market_date": candles["x"][-1],
            "dated_agent_order_events": 0 if orders is None else len(orders["x"]),
            "dated_portfolio_points": 0 if portfolio is None else len(portfolio["x"]),
            "artifact_role": "market_analysis_only" if portfolio is None else "stocksim_precursor_agent_output",
            "attributable_atlas_paper_run": False,
            "published_result_regenerated": False,
            "paper_result_credit": False,
        })
    if xom_portfolio is None or len(xom_portfolio) != 43 or xom_orders != 20:
        raise ValueError("StockSim historical XOM output dimensions changed")
    initial_cash_roi = xom_portfolio[-1] / 100_000.0 - 1.0
    published_roi_means = xom_published_roi_means(tex)
    exact_published_match = any(round(value, 2) == round(initial_cash_roi * 100, 2) for value in published_roi_means)
    if round(initial_cash_roi * 100, 5) != 5.01564 or exact_published_match:
        raise ValueError("StockSim historical XOM paper-linkage boundary changed")

    lob_orders = 0
    for index in range(10):
        payload = json.loads(
            git(repo, "show", f"{REPOSITORY_HEAD}:orders/original_part{index}.json")
        )
        if set(payload) != {"AAPL"}:
            raise ValueError("StockSim LOB payload asset changed")
        records = payload["AAPL"]
        if records[0]["timestamp"][:10] != "2025-03-01" or records[-1]["timestamp"][:10] != "2025-03-01":
            raise ValueError("StockSim LOB payload date changed")
        lob_orders += len(records)
    if lob_orders != 191_015:
        raise ValueError(f"StockSim LOB payload size changed: {lob_orders}")

    summary = {
        "public_commits_reviewed": len(commits),
        "public_branches_reviewed": len(branch_heads),
        "public_tags": 0,
        "public_releases": 0,
        "unreachable_objects": 0,
        "historical_unique_paths_reviewed": len(all_paths),
        "historical_charts_recovered": len(artifact_rows),
        "historical_market_analysis_only_charts": 3,
        "historical_precursor_agent_output_charts": 1,
        "historical_xom_portfolio_points": len(xom_portfolio),
        "historical_xom_order_events": xom_orders,
        "historical_xom_initial_cash_roi_percent": round(initial_cash_roi * 100, 5),
        "historical_xom_matches_published_atlas_xom_roi_mean": exact_published_match,
        "historical_xom_attributable_to_atlas_paper_run": False,
        "historical_xom_paper_result_credit": False,
        "historical_lob_asset": "AAPL",
        "historical_lob_date": "2025-03-01",
        "historical_lob_order_records": lob_orders,
        "history_complete_for_current_public_refs": True,
    }
    return rows, artifact_rows, summary


def stocksim_public_fork_audit(
    scratch: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Fail closed over every public StockSim fork branch visible at census time."""
    repo = scratch / "stocksim"
    observed_refs = {
        ref: git(repo, "rev-parse", ref).strip()
        for ref in git(
            repo,
            "for-each-ref",
            "--format=%(refname)",
            "refs/remotes/forks",
        ).splitlines()
    }
    if observed_refs != PUBLIC_FORK_HEADS:
        raise ValueError(f"StockSim public fork refs changed: {observed_refs}")

    branch_rows: list[dict[str, Any]] = []
    for ref, head in sorted(observed_refs.items()):
        relative = ref.removeprefix("refs/remotes/forks/")
        owner, branch = relative.split("/", 1)
        repository = PUBLIC_FORK_REPOSITORIES[owner]
        ahead = int(
            git(repo, "rev-list", "--count", head, "--not", *STOCKSIM_OFFICIAL_REFS).strip()
        )
        behind_main = int(
            git(repo, "rev-list", "--count", f"{head}..{REPOSITORY_HEAD}").strip()
        )
        if ahead != PUBLIC_FORK_AHEAD_COUNTS[ref] or behind_main != 0:
            raise ValueError(
                f"StockSim fork relationship changed for {ref}: "
                f"ahead={ahead} behind_main={behind_main}"
            )
        relation = "exact_official_main" if head == REPOSITORY_HEAD else "descendant_of_official_main"
        branch_rows.append({
            "repository": repository,
            "url": f"https://github.com/{repository}",
            "branch": branch,
            "head_commit": head,
            "relation_to_official_head": relation,
            "commits_ahead_of_official_history": ahead,
            "commits_behind_official_main": behind_main,
            "public_tag_refs": 0,
            "native_atlas_result_payload_found": False,
            "paper_result_credit": False,
        })

    fork_heads = sorted(set(observed_refs.values()))
    official_objects = set(
        git(
            repo, "rev-list", "--objects", "--no-object-names", *STOCKSIM_OFFICIAL_REFS
        ).splitlines()
    )
    fork_objects = set(
        git(repo, "rev-list", "--objects", "--no-object-names", *fork_heads).splitlines()
    )
    unique_objects = sorted(fork_objects - official_objects)
    object_types = {"commit": 0, "tree": 0, "blob": 0}
    for object_id in unique_objects:
        object_type = git(repo, "cat-file", "-t", object_id).strip()
        if object_type not in object_types:
            raise ValueError(f"unexpected StockSim fork object type: {object_type}")
        object_types[object_type] += 1
    if object_types != {"commit": 12, "tree": 26, "blob": 22}:
        raise ValueError(f"StockSim public fork object surface changed: {object_types}")

    unique_commits = sorted(
        set(git(repo, "rev-list", *fork_heads, "--not", *STOCKSIM_OFFICIAL_REFS).splitlines())
    )
    if len(unique_commits) != 12:
        raise ValueError(f"StockSim public fork commit surface changed: {len(unique_commits)}")

    search_pattern = r"ATLAS|Adaptive[-_ ]OPRO|2510[.]15949|o4-mini-adaptive"
    result_path_pattern = re.compile(
        r"(^|/)(checkpoints?|results?|outputs?|logs?|actions?|trajectories?|rollouts?|ratings?)(/|$)",
        re.IGNORECASE,
    )
    commit_rows: list[dict[str, Any]] = []
    all_changed_paths: set[str] = set()
    all_identifier_paths: set[str] = set()
    all_result_paths: set[str] = set()
    for commit in unique_commits:
        metadata = git(
            repo,
            "show",
            "-s",
            "--format=%aI%x00%an%x00%ae%x00%s",
            commit,
        ).rstrip("\n").split("\x00", 3)
        if len(metadata) != 4:
            raise ValueError(f"StockSim fork metadata parse failed for {commit}")
        authored_at, author_name, author_email, subject = metadata
        changed_paths = sorted(
            set(
                git(
                    repo,
                    "diff-tree",
                    "--root",
                    "-m",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    commit,
                ).splitlines()
            )
            - {""}
        )
        search = subprocess.run(
            [
                "git", "-C", str(repo), "grep", "-I", "-l", "-i", "-E",
                search_pattern, commit, "--", "*.py", "*.yaml", "*.yml", "*.json",
                "*.md", "*.txt", "*.j2",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if search.returncode not in {0, 1}:
            raise ValueError(f"StockSim fork search failed at {commit}: {search.stderr}")
        identifier_paths = sorted(set(search.stdout.splitlines()) - {""})
        result_paths = sorted(path for path in changed_paths if result_path_pattern.search(path))
        exact_author_name = author_name in ATLAS_AUTHOR_NAMES
        all_changed_paths.update(changed_paths)
        all_identifier_paths.update(identifier_paths)
        all_result_paths.update(result_paths)
        commit_rows.append({
            "commit": commit,
            "authored_at": authored_at,
            "author_name": author_name,
            "author_email": author_email,
            "subject": subject,
            "changed_paths": len(changed_paths),
            "atlas_identifier_paths_at_commit": len(identifier_paths),
            "changed_result_payload_paths": len(result_paths),
            "authored_after_atlas_v5_submission": authored_at[:10] > VERSION_SPECS["v5"][0][:10],
            "exact_atlas_author_display_name_match": exact_author_name,
            "native_atlas_result_payload_found": False,
            "paper_result_credit": False,
        })
    commit_rows.sort(key=lambda row: (row["authored_at"], row["commit"]))

    changed_paths_digest = sha256_bytes(
        ("\n".join(sorted(all_changed_paths)) + "\n").encode()
    )
    if (
        all_changed_paths != PUBLIC_FORK_CHANGED_PATHS
        or changed_paths_digest != PUBLIC_FORK_CHANGED_PATHS_SHA256
        or all_identifier_paths
        or all_result_paths
        or not all(row["authored_after_atlas_v5_submission"] for row in commit_rows)
        or any(row["exact_atlas_author_display_name_match"] for row in commit_rows)
    ):
        raise ValueError("StockSim public fork ATLAS-evidence boundary changed")

    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": 5,
        "accessible_public_forks": len(PUBLIC_FORK_REPOSITORIES),
        "accessible_branch_refs": len(branch_rows),
        "public_tag_refs": 0,
        "unique_heads": len(fork_heads),
        "official_head_exact_refs": sum(
            row["relation_to_official_head"] == "exact_official_main" for row in branch_rows
        ),
        "divergent_unique_heads": len(set(fork_heads) - {REPOSITORY_HEAD}),
        "unique_commits_beyond_official_history": len(unique_commits),
        "unique_trees_beyond_official_history": object_types["tree"],
        "unique_blobs_beyond_official_history": object_types["blob"],
        "unique_changed_paths": len(all_changed_paths),
        "unique_changed_paths_sha256": changed_paths_digest,
        "atlas_identifier_paths": len(all_identifier_paths),
        "changed_result_payload_paths": len(all_result_paths),
        "post_v5_unique_commits": sum(
            row["authored_after_atlas_v5_submission"] for row in commit_rows
        ),
        "exact_paper_author_display_name_attributions": sum(
            row["exact_atlas_author_display_name_match"] for row in commit_rows
        ),
        "native_atlas_result_payloads_found": 0,
        "paper_result_credit": False,
        "interpretation": (
            "One fork contains genuine post-paper StockSim engineering in AML integration, "
            "portfolio accounting, timestamp handling, synchronization, and market "
            "microstructure, but no attributable ATLAS or Adaptive-OPRO experiment lineage."
        ),
    }
    expected_summary_counts = {
        "accessible_public_forks": 5,
        "accessible_branch_refs": 11,
        "unique_heads": 8,
        "official_head_exact_refs": 4,
        "divergent_unique_heads": 7,
        "unique_commits_beyond_official_history": 12,
        "unique_changed_paths": 13,
        "post_v5_unique_commits": 12,
    }
    if any(summary[key] != value for key, value in expected_summary_counts.items()):
        raise ValueError(f"StockSim public fork census changed: {summary}")
    return branch_rows, commit_rows, summary


def prompt_rows() -> list[dict[str, Any]]:
    prompts = (
        ("central_trader_initial", "central trading agent initial decision template"),
        ("central_trader_followup", "central trading agent subsequent decision template"),
        ("market_analyst_initial", "market analyst initial template"),
        ("market_analyst_followup", "market analyst subsequent template"),
        ("news_analyst_initial", "news analyst initial template"),
        ("news_analyst_followup", "news analyst subsequent template"),
        ("fundamental_analyst_initial", "fundamental analyst initial template"),
        ("fundamental_analyst_followup", "fundamental analyst subsequent template"),
        ("adaptive_opro_optimizer", "optimizer meta-prompt and scored prompt history format"),
        ("weekly_reflection", "weekly reflection prompt"),
    )
    return [{
        "prompt": name, "description": description,
        "paper_template_recovered": True, "exact_runtime_payload_recovered": False,
        "model_request_response_recovered": False, "trajectory_recovered": False,
        "native_replayed": False, "paper_result_credit": False,
    } for name, description in prompts]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official_document_source", "complete", "all five arXiv PDFs and source packages recovered and rebuilt"),
        ("framework_provenance", "cited_same_author_precursor", "paper cites StockSim; repository owner Charidimos Papadakis is first author"),
        ("framework_release_date", "precedes_paper", "pinned main head is dated 2025-07-15; ATLAS v1 was submitted 2025-10-10"),
        ("paper_specific_release", "missing", "all 20 official StockSim revisions and all 11 branch refs across five public forks contain no attributable ATLAS, Adaptive-OPRO, paper identifier, promised ATLAS config, or native paper-result payload"),
        ("precursor_xom_configuration", "partially_recovered", "StockSim demo matches XOM, 2025-04-28 to 2025-06-28, daily cadence, $100,000 cash, and three analyst roles; it lacks the ATLAS central agent, prompting strategies, other assets, and experiment matrix"),
        ("assets_and_period", "partially_recovered_not_frozen", "StockSim demo exactly matches XOM and the paper window; LLY/NVDA experiment configs and frozen vendor snapshots are absent"),
        ("market_regimes", "specified", "LLY bearish-volatile, XOM sideways, NVDA bullish"),
        ("initial_portfolio", "specified", "$100,000 cash and no positions"),
        ("market_data", "precursor_chart_only", "initial StockSim history has LLY/XOM/NVDA market-analysis charts through 2025-06-27, not frozen ATLAS input snapshots or vendor-response lineage"),
        ("news_and_fundamentals", "not_released", "time-aligned source records, query responses, and preprocessing outputs absent"),
        ("execution_model", "specified_abstraction", "deterministic daily execution abstracts latency, slippage, impact, intraday partial fills"),
        ("agent_architecture", "precursor_components_execute", "StockSim analyst, trader, exchange, metric, order, and template modules import; four controlled checks pass"),
        ("model_backbones", "specified_not_replayable", "seven listed backbones; provider snapshots, decoding parameters, and responses absent"),
        ("baseline_prompting", "paper_templates_only", "appendix templates exist without exact filled runtime prompts or trajectories"),
        ("reflection", "paper_templates_only", "daily and weekly mechanisms described; logs, model calls, and complete trajectories absent"),
        ("adaptive_opro", "paper_specification_only", "K=5 and clipped score are specified; optimizer implementation, states, edit history, and requests absent"),
        ("replications", "specified_not_released", "three runs per configuration, but random seeds and run artifacts are absent"),
        ("precursor_native_output", "recovered_not_paper_attributable", "deleted initial XOM chart contains 20 dated orders and 43 portfolio points, ending +5.01564% from $100,000; no published ATLAS XOM ROI mean matches"),
        ("published_results", "not_regenerated", "zero of 1,784 empirical scalar units and zero of five empirical panels regenerated"),
        ("as_declared_environment", "fails_obsolete_dependency", "requirements installs obsolete asyncio backport that is a SyntaxError on Python 3.12"),
        ("bounded_environment_adjustment", "component_checks_pass", "after removing backport, pip check, compileall, 43/43 imports, and four deterministic component checks pass"),
        ("full_launcher", "blocked_external_and_missing_paper_payload", "demo validates then stops for RabbitMQ, log path, and market-data API key; it is not ATLAS"),
        ("author_tests", "absent_in_official_release", "zero tracked test files in the official release; one post-paper fork adds two StockSim self-trade-prevention tests, not ATLAS tests"),
        ("search_for_release", "no_public_atlas_implementation_found", "all 20 official commits, both official branches, five public forks with 11 branch refs and eight unique heads, zero public tags/releases, and exact GitHub searches expose no attributable ATLAS implementation"),
    )
    return [{"version": "v5", "dimension": d, "status": s, "detail": detail} for d, s, detail in specs]


def pearson_and_slope(x: list[float], y: list[float]) -> tuple[float, float]:
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    covariance = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
    x_square = sum((a - x_mean) ** 2 for a in x)
    y_square = sum((b - y_mean) ** 2 for b in y)
    return covariance / math.sqrt(x_square * y_square), covariance / x_square


def internal_rows() -> list[dict[str, str]]:
    baseline = [-9.19, -1.78, -10.62, -7.26, -4.46, -1.30, -6.11]
    reflection = [-8.44, -5.76, -7.76, -5.69, -8.60, -2.52, -4.60]
    adaptive = [-6.16, 1.33, -3.48, 0.35, -0.73, 9.06, 9.02]
    absolute_r, _ = pearson_and_slope(baseline, adaptive)
    gain_r, gain_beta = pearson_and_slope(baseline, [a - b for a, b in zip(adaptive, baseline)])
    reflection_r, reflection_beta = pearson_and_slope(baseline, [a - b for a, b in zip(reflection, baseline)])
    specs = (
        ("adaptive_absolute_correlation", "matches_rounded_claim", f"table-derived r={absolute_r:.6f}; paper reports 0.64"),
        ("adaptive_gain_correlation", "matches_rounded_claim", f"table-derived r={gain_r:.6f}, beta={gain_beta:.6f}; paper reports 0.05 and 0.06"),
        ("reflection_gain_correlation", "matches_rounded_claim", f"table-derived r={reflection_r:.6f}, beta={reflection_beta:.6f}; paper reports -0.78 and -0.61"),
        ("current_result_scalar_inventory", "source_parsed", "1,784 printed empirical scalars across 11 result tables"),
        ("version_history", "fully_audited", "v1-v5 source and PDFs recovered, rebuilt, and visually paired"),
        ("stock_sim_lineage", "cited_same_author_component", "real first-party precursor framework, but no ATLAS-specific payload"),
        ("stock_sim_public_history", "fully_audited", "20 commits across main and website, zero tags/releases, 107 historical paths, and no unreachable objects"),
        ("stock_sim_public_forks", "fully_audited_no_atlas_lineage", "five accessible forks expose 11 branch refs and eight unique heads; 12 post-v5 commits add genuine StockSim engineering across 13 paths but no ATLAS identifiers or native result payloads"),
        ("deleted_precursor_outputs", "recovered_no_paper_credit", "initial commit held LLY/NVDA/XOM charts; only XOM has 20 agent orders and a 43-point portfolio path, but it matches no published ATLAS XOM ROI mean"),
        ("lob_order_payloads", "unrelated_precursor_fixture", "191,015 AAPL order records dated 2025-03-01 support StockSim orderbook replay, not ATLAS's daily three-asset study"),
        ("repository_license", "readme_declaration_only", "README says MIT; no license-text file and GitHub reports no detected license"),
        ("repository_readme_paths", "stale_or_incorrect", "banner points to StockSim/StockSim and config.yaml, while repository is harrypapadakis/StockSim and ships demo_config.yaml"),
        ("code_release_language", "not_fulfilled_in_pinned_evidence", "v1-v4 promise release upon publication; v5 still references implementation details in code and a sample ATLAS config that are absent"),
        ("live_execution_scope", "paper_acknowledges_abstraction", "paper omits latency, slippage, impact, and intraday partial fills and does not establish live performance"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def release_audit(
    scratch: Path,
    history: Mapping[str, Any],
    public_forks: Mapping[str, Any],
) -> dict[str, Any]:
    archive = scratch / f"release/{REPOSITORY_HEAD}.tar.gz"
    members = validate_tar(archive)
    texts = tar_texts(archive)
    joined = "\n".join(texts.values()).lower()
    readme = next(value for name, value in texts.items() if name.endswith("/README.md"))
    requirements = next(value for name, value in texts.items() if name.endswith("/requirements.txt"))
    demo = next(value for name, value in texts.items() if name.endswith("/configs/demo_config.yaml"))
    for marker in ("adaptive-opro", "adaptive_opro", ARXIV_ID, "o4-mini-adaptive-opro-config"):
        if marker.lower() in joined:
            raise ValueError(f"ATLAS release boundary changed: found {marker}")
    if "asyncio>=3.4.3" not in requirements or not re.search(
        r"(?m)^instruments:\s*\n\s*- XOM\b", demo
    ):
        raise ValueError("StockSim dependency/config evidence changed")
    if "MIT License" not in readme or any(
        PurePosixPath(member.name).name.lower() in {"license", "license.md", "copying"}
        for member in members
    ):
        raise ValueError("StockSim license boundary changed")
    modules = json.loads((scratch / "native/module-imports.json").read_text())
    checks = json.loads((scratch / "native/component-checks.json").read_text())
    if (modules["attempted"], modules["passed"], modules["failed"]) != (43, 43, 0):
        raise ValueError("StockSim module import evidence changed")
    if checks.get("atlas_specific_component") is not False or checks.get("atlas_result_credit") is not False:
        raise ValueError("StockSim component boundary changed")
    if (scratch / "native/as-declared-asyncio-import-status.txt").read_text() != "1\n":
        raise ValueError("as-declared asyncio failure changed")
    if "SyntaxError: invalid syntax" not in (scratch / "native/as-declared-asyncio-import.txt").read_text():
        raise ValueError("as-declared asyncio failure reason changed")
    if (scratch / "native/post-adjustment-asyncio-import-status.txt").read_text() != "0\n":
        raise ValueError("adjusted asyncio import changed")
    if (scratch / "native/compileall-status.txt").read_text() != "0\n":
        raise ValueError("compileall evidence changed")
    launcher = (scratch / "native/launcher-after-audit-adjustment.txt").read_text()
    for marker in ("RABBITMQ_HOST", "LOG_DIR", "POLYGON_API_KEY or ALPHA_VANTAGE_API_KEY"):
        if marker not in launcher:
            raise ValueError(f"launcher blocker changed: {marker}")
    python_files = sum(member.name.endswith(".py") for member in members)
    test_files = sum("test" in PurePosixPath(member.name).name.lower() and member.name.endswith(".py") for member in members)
    return {
        "url": REPOSITORY_URL, "head_sha": REPOSITORY_HEAD,
        "head_commit_date": "2025-07-15T13:12:01+03:00",
        "archive_sha256": PINS[f"release/{REPOSITORY_HEAD}.tar.gz"],
        "archive_files": len(members), "archive_bytes": archive.stat().st_size,
        "archive_uncompressed_bytes": sum(member.size for member in members),
        "attribution": "paper cites StockSim; repository owner Charidimos Papadakis is ATLAS first author",
        "license_declaration": "MIT", "license_text_file_present": False,
        "github_detected_license": None, "python_files": python_files,
        "tracked_test_files": test_files, "author_tests": "absent",
        "as_declared_dependency_install_passed": True,
        "as_declared_asyncio_import_passed": False,
        "as_declared_failure": "obsolete PyPI asyncio backport uses tasks.async and is invalid on Python 3.12",
        "central_environment": (scratch / "native/environment.txt").read_text().strip(),
        "audit_adjustment": "removed obsolete asyncio backport so stdlib asyncio is used",
        "dependency_check_after_adjustment_passed": True,
        "bytecode_compilation_after_adjustment_passed": True,
        "modules_imported_after_adjustment": modules["passed"],
        "modules_failed_import_after_adjustment": modules["failed"],
        "native_component_fixture": checks,
        "native_component_checks_passed": 4,
        "demo_config_validated": True,
        "demo_config_matches_atlas_xom_asset": True,
        "demo_config_matches_atlas_date_window": True,
        "demo_config_matches_atlas_daily_cadence": True,
        "demo_config_matches_atlas_initial_cash": True,
        "demo_config_matches_atlas_three_analyst_roles": True,
        "demo_config_is_complete_atlas_experiment_config": False,
        "full_launcher_operational_without_external_services": False,
        "full_launcher_blockers": ["RabbitMQ host", "log directory", "Polygon or Alpha Vantage API key"],
        "atlas_specific_code_released": False,
        "adaptive_opro_implementation_released": False,
        "atlas_sample_config_released": False,
        "paper_data_snapshot_released": False,
        "paper_news_and_fundamental_inputs_released": False,
        "paper_model_requests_responses_released": False,
        "paper_runtime_prompts_and_trajectories_released": False,
        "paper_seeds_released": False,
        "paper_run_artifacts_released": False,
        "paper_result_arrays_released": False,
        "full_public_history_audit": dict(history),
        "public_fork_census": dict(public_forks),
        "historical_precursor_native_output_recovered": True,
        "historical_precursor_output_attributable_to_atlas_paper_run": False,
        "published_table_or_figure_regenerated": False,
        "paper_result_credit": False,
    }


def readme() -> str:
    return """# ATLAS paper and cited StockSim component audit

This audit pins all five official revisions of arXiv `2510.15949`, every
source package, and the cited same-author StockSim repository at `c1a25c1`.
Each source revision rebuilds to the official page count: 37 pages for v1 and
43 pages for v2-v5. All 209 official and all 209 rebuilt pages were visually
checked side by side. No unreadable, clipped, overlapping, blank, or missing
research content was found. This establishes excellent document-source
reproducibility, not experimental reproducibility.

The current v5 source contains 1,784 printed empirical scalar units across 11
result tables. It also contains 10 figures with 12 total panels, of which five
panels plot empirical results. The source exposes the author-rendered tables,
plot coordinates, architecture diagrams, prompt templates, evolved-prompt
examples, and detailed method prose. Rebuilding those author-authored assets
does not independently regenerate an ATLAS result.

StockSim is a genuine first-party precursor component: repository owner
Charidimos Papadakis is the paper's first author, and the paper cites StockSim.
The pinned release has 81 files and 43 Python modules, but no author tests. Its
declared environment installs an obsolete PyPI `asyncio` backport whose
`tasks.async` syntax is invalid on Python 3.12. After removing only that
backport in an isolated audit environment, dependency checking and bytecode
compilation pass, all 43/43 modules import, and four controlled checks cover
config validation, metrics, order matching, and candle-trigger semantics.
Those are StockSim component checks only and receive no ATLAS result credit.

The complete public StockSim history comprises 20 commits across `main` and
`website`, with zero tags, zero releases, 107 unique historical paths, and no
unreachable objects. The initial commit contained four later-deleted Plotly
charts. Three are market-analysis-only LLY/NVDA charts. `charts/XOM.html`
contains a native precursor run with 20 dated, explained orders and a 43-point
portfolio path over the paper's exact XOM window; it ends at $105,015.64, or
+5.01564% from the stated $100,000 cash. This value matches none of the 26
published ATLAS XOM ROI means, and the artifact has no ATLAS, prompting-strategy,
model, seed, or paper-run identifier. It is recoverable StockSim native-output
evidence, not an attributable ATLAS run or a regenerated paper result.

A 2026-08-14 census also exhausts all five public forks: 11 branch refs resolve
to eight unique heads. Four refs exactly match the official `main` head. The
remaining seven heads belong to one active fork and collectively add 12 commits,
26 trees, 22 blobs, and 13 changed paths after ATLAS v5. Those are genuine
StockSim engineering changes covering AML agents, portfolio accounting,
timestamp handling, synchronization, market microstructure, and two
self-trade-prevention tests. No changed or reachable file contains an ATLAS,
Adaptive-OPRO, paper-ID, promised-config, checkpoint, trajectory, action,
rating, or result payload. None of the 12 commit author display names exactly
matches a paper author. The work therefore improves StockSim but supplies no
attributable ATLAS experiment or result evidence.

The StockSim demo config is also closer to the method than a generic example:
it exactly matches XOM, 2025-04-28 through 2025-06-28, daily decisions,
$100,000 initial cash, and the market/news/fundamental analyst roles. It does
not contain the ATLAS central-agent implementation, Baseline/Reflection/
Adaptive-OPRO strategy logic, LLY/NVDA experiment configs, seven-model matrix,
or three-run design. Ten later JSON files contain 191,015 AAPL orders from
2025-03-01 for order-book replay and are unrelated to the ATLAS daily study.

Every official revision predates ATLAS v1 and contains no ATLAS identifier,
Adaptive-OPRO implementation, promised
`configs/o4-mini-adaptive-opro-config.yaml`, exact three-asset experiment
configuration, frozen Massive/Polygon data, news or fundamental inputs, model
requests/responses, filled runtime prompts, optimizer trajectory, seeds, run
artifacts, or result arrays. Its demo launcher validates an XOM configuration
but then correctly stops without RabbitMQ, a log directory, and a market-data
API key. Supplying those services would run a StockSim demo, not the paper.

The strict paper-level result is therefore **0/1,784 empirical numeric table units
and 0/5 empirical panels regenerated**. The table-derived correlations
reported in the paper can be recomputed from rounded published values, but
that is only an internal-consistency check. ATLAS is richly specified and its
manuscript is fully rebuildable, but not currently a true experimental replication
package. The short two-month, three-asset study and deterministic
execution abstraction also limit claims about generalization or live trading.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inventory = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    tex = (scratch / "source-v5/acl_latex.tex").read_text(encoding="utf-8")
    history_rows, historical_artifacts, history_summary = stocksim_history_rows(
        scratch, tex
    )
    fork_branch_rows, fork_commit_rows, fork_summary = stocksim_public_fork_audit(
        scratch
    )
    results = result_rows(tex)
    figures = figure_rows()
    versions = []
    source_inventory = []
    for version, (submitted, pages, files, size, tables, figure_count) in VERSION_SPECS.items():
        versions.append({
            "version": version, "submitted": submitted,
            "title": "ATLAS: Adaptive Trading with LLM AgentS Through Dynamic Prompt Optimization and Multi-Agent Coordination",
            "authors": 6, "official_pages": pages, "source_files": files,
            "source_uncompressed_bytes": size, "rebuilt_pages": pages,
            "table_environments": tables, "figure_environments": figure_count,
            "current_version_published_numeric_result_units": len(results) if version == "v5" else "",
            "current_version_empirical_panels": sum(row["empirical_panels"] for row in figures) if version == "v5" else "",
        })
        for member in inventory["source"][version]:
            source_inventory.append({
                "version": version, "path": member.name, "bytes": member.size,
                "role": "official_manuscript_source",
                "paper_system_implementation": False,
            })
    write_csv(output / "version_audit.csv", versions)
    write_csv(output / "source_inventory.csv", source_inventory)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "prompt_artifact_inventory.csv", prompt_rows())
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", internal_rows())
    write_csv(output / "released_source_history_inventory.csv", history_rows)
    write_csv(output / "historical_precursor_artifact_inventory.csv", historical_artifacts)
    write_csv(output / "public_fork_branch_ref_snapshot.csv", fork_branch_rows)
    write_csv(output / "public_fork_unique_commit_inventory.csv", fork_commit_rows)
    write_json(output / "public_fork_census.json", fork_summary)
    release = release_audit(scratch, history_summary, fork_summary)
    write_json(output / "release_execution_audit.json", release)
    write_json(output / "source_provenance.json", {
        "work_id": WORK_ID, "system_id": SYSTEM_ID,
        "arxiv": {
            "id": ARXIV_ID, "versions": list(VERSION_SPECS),
            "pdf_sha256": {version: PINS[f"atlas-{version}.pdf"] for version in VERSION_SPECS},
            "source_sha256": {version: PINS[f"atlas-{version}-source.tar"] for version in VERSION_SPECS},
            "license": "CC BY-NC-ND 4.0",
            "visual_qa": {
                "official_pages_inspected": 209, "rebuilt_pages_inspected": 209,
                "unreadable_clipped_overlapping_blank_or_missing_pages": 0,
                "contact_sheet_sha256": {
                    key.removeprefix("viz/").removesuffix(".jpg"): value
                    for key, value in PINS.items() if key.startswith("viz/")
                },
            },
        },
        "official_component_repository": release,
        "release_boundary": {
            "attribution_strength": "paper_cited_same_author_precursor_framework",
            "stock_sim_source_recovered": True,
            "stock_sim_component_execution_completed": True,
            "stock_sim_complete_public_history_reviewed": True,
            "stock_sim_all_public_forks_reviewed": True,
            "stock_sim_precursor_native_output_recovered": True,
            "stock_sim_fork_native_atlas_result_payload_recovered": False,
            "atlas_specific_source_recovered": False,
            "complete_research_inputs_recovered": False,
            "published_result_lineage_recovered": False,
        },
        "release_search_evidence_sha256": {
            key.removeprefix("release/").removesuffix(".json"): value
            for key, value in PINS.items() if key.startswith("release/search-")
        },
    })
    (output / "README.md").write_text(readme(), encoding="utf-8")
    manifest = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "arxiv_id": ARXIV_ID,
        "official_versions_audited": list(VERSION_SPECS),
        "official_pdf_and_source_recovered": True,
        "document_rebuild_completed": True,
        "official_pages_visually_checked": 209,
        "rebuilt_pages_visually_checked": 209,
        "source_files_across_versions": len(source_inventory),
        "published_numeric_result_units": len(results),
        "native_numeric_units_regenerated": 0,
        "figures": len(figures),
        "figure_panels": sum(row["panels"] for row in figures),
        "empirical_panels": sum(row["empirical_panels"] for row in figures),
        "native_empirical_panels_regenerated": 0,
        "paper_prompt_templates_recovered": len(prompt_rows()),
        "runtime_prompt_trajectories_recovered": 0,
        "official_component_repository_recovered": True,
        "repository_files": len(inventory["release"]),
        "repository_public_commits_audited": history_summary["public_commits_reviewed"],
        "repository_public_branches_audited": history_summary["public_branches_reviewed"],
        "repository_historical_unique_paths_audited": history_summary[
            "historical_unique_paths_reviewed"
        ],
        "public_forks_audited": fork_summary["accessible_public_forks"],
        "public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
        "public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "public_fork_unique_commits_beyond_official_history_audited": fork_summary[
            "unique_commits_beyond_official_history"
        ],
        "public_fork_unique_changed_paths_audited": fork_summary["unique_changed_paths"],
        "public_fork_native_atlas_result_payloads_recovered": fork_summary[
            "native_atlas_result_payloads_found"
        ],
        "historical_precursor_agent_output_artifacts_recovered": history_summary[
            "historical_precursor_agent_output_charts"
        ],
        "historical_precursor_dated_orders_recovered": history_summary[
            "historical_xom_order_events"
        ],
        "historical_precursor_portfolio_points_recovered": history_summary[
            "historical_xom_portfolio_points"
        ],
        "historical_precursor_output_attributable_to_atlas_paper_run": False,
        "author_tests_passed": 0,
        "native_component_checks_passed": 4,
        "modules_imported_after_audit_adjustment": 43,
        "modules_failed_import_after_audit_adjustment": 0,
        "atlas_specific_code_recovered": False,
        "full_launcher_operational_as_released": False,
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
    }
    manifest["output_sha256"] = {
        path.name: sha256(path) for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(args.output)
    if args.strict and not manifest["strict_success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
