from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_paper_assets.py"
SPEC = importlib.util.spec_from_file_location("build_paper_assets", SCRIPT)
assert SPEC and SPEC.loader
paper = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = paper
SPEC.loader.exec_module(paper)


def test_pdf_figure_writer_is_byte_deterministic(tmp_path: Path) -> None:
    outputs = []
    for name in ("first.pdf", "second.pdf"):
        path = tmp_path / name
        fig, ax = plt.subplots()
        ax.plot([0, 1], [1, 0], color=paper.COLORS["blue"])
        paper.save_figure(fig, path, "Deterministic fixture")
        outputs.append(path.read_bytes())
    assert outputs[0] == outputs[1]
    assert b"D:20260101000000Z" in outputs[0]
