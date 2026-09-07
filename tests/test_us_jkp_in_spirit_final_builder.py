from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_us_jkp_in_spirit_final.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("in_spirit_final_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_final_builder_loads_exact_terminal_dispositions_and_metrics():
    builder = load_builder()
    rows, family, metric_inputs = builder.load_results(ROOT)
    assert [row["milestone_id"] for row in rows] == [f"M{number:03d}" for number in range(1, 70)]
    assert {status: sum(row["disposition"] == status for row in rows) for status in builder.TERMINAL} == {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 45,
        "discarded_structural_mismatch": 7,
    }
    assert sum(row["common_jkp_evaluated"] for row in rows) == len(family) == len(metric_inputs) == 62
    assert not any(row["native_system_end_to_end_reproduced"] for row in rows)
    assert not any(row["native_empirical_claim_tested"] for row in rows)
    m067 = next(row for row in rows if row["milestone_id"] == "M067")
    assert m067["full_cagr"] == pytest.approx(0.0210054333640845)
    assert m067["jkp_excess_annualized"] == pytest.approx(-0.0215116689862938)


def test_final_builder_uses_the_declared_69_paper_holm_family():
    builder = load_builder()
    rows, family, _ = builder.load_results(ROOT)
    assert [row["rank"] for row in family] == list(range(1, 63))
    assert [row["holm_multiplier"] for row in family] == list(range(69, 7, -1))
    assert all(
        left["raw_p_two_sided"] <= right["raw_p_two_sided"]
        for left, right in zip(family, family[1:])
    )
    assert all(
        left["holm_adjusted_p"] <= right["holm_adjusted_p"]
        for left, right in zip(family, family[1:])
    )
    lookup = {row["milestone_id"]: row for row in rows}
    assert all(lookup[row["milestone_id"]]["holm_family_size"] == 69 for row in family)


def test_visual_and_no_image_reports_share_the_honest_claim_boundary():
    builder = load_builder()
    rows, family, _ = builder.load_results(ROOT)
    visual = builder.build_report(rows, family, True)
    no_image = builder.build_report(rows, family, False)
    for report in (visual, no_image):
        assert "17 carried source-anchored common evaluations" in report
        assert "45 researcher-authored in-spirit reconstructions" in report
        assert "7 structural discards" in report
        assert "cannot declare the original claims true or false" in report
        assert "zero complete native systems were reproduced end to end" in report
    assert "![" in visual
    assert "![" not in no_image
