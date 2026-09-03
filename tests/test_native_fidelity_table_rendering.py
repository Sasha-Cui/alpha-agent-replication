from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_table_paper_assets", ROOT / "scripts/build_paper_assets.py")
assert spec and spec.loader
paper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = paper
spec.loader.exec_module(paper)


def test_cryptotrade_table_is_compact_without_strengthening_result_credit(tmp_path):
    native = pd.read_csv(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv", keep_default_na=False)
    row = native.loc[native.system_id == "SYS-CRYPTO-TRADE"].iloc[0]
    original = row.copy(deep=True)
    cell = paper.native_evidence_table_cell(row)
    manifest = json.loads((ROOT / "paper_runs/paper_replication_audits/cryptotrade/manifest.json").read_text())
    selection = manifest["traditional_selection_protocol"]
    assert len(cell.split()) < 160
    assert len(row.concise_evidence_note.split()) > 500
    pd.testing.assert_series_equal(row, original)
    assert f"{selection['matching_cells_under_both_objectives']}/72" in cell
    assert f"{selection['fixed_settings_match_cells']}/72" in cell
    assert "not full protocol-faithful credit" in cell
    assert "not fresh decisions" in cell
    assert "zero faithful-result credit because it uses future inputs" in cell
    assert "adapter hold/sell bug" in cell
    assert "not a disclosed strategy" in cell
    assert "Table 5 has zero faithful credit" in cell
    url = "https://github.com/Sasha-Cui/alpha-agent-replication/blob/main/paper_runs/paper_replication_audits/cryptotrade/README.md"
    assert paper.latex_href(url, "Full audit and limitations") in cell
    assert (ROOT / "paper_runs/paper_replication_audits/cryptotrade/README.md").is_file()
    registry = pd.DataFrame([{"system_id": "SYS-CRYPTO-TRADE", "system_name": "CryptoTrade", "stratum": "F"}])
    output = tmp_path / "table.tex"
    paper.build_artifact_failure_table(native.loc[native.system_id == "SYS-CRYPTO-TRADE"], registry, output)
    assert cell in output.read_text()


def test_other_native_table_notes_are_preserved():
    row = pd.Series({"system_id": "example", "concise_evidence_note": "0% is not missing evidence."})
    assert paper.native_evidence_table_cell(row) == paper.latex_escape(row.concise_evidence_note)
