"""No silent calendar losses or incomplete-family promotion in final EFS analysis."""

import importlib.util
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_efs_pair_and_months_refuse_calendar_loss():
    m = module("analyze_efs_pooled_v2")
    dates = pd.date_range("2019-01-01", periods=5)
    a = pd.Series(0.01, index=dates)
    with pytest.raises(ValueError, match="calendars"):
        m.strict_pair(a, a.iloc[:-1])
    with pytest.raises(ValueError, match="72"):
        m.month_path(a)
    complete = pd.Series(0.0, index=pd.date_range("2019-01-31", "2024-12-31", freq="ME"))
    assert len(m.month_path(complete)) == 72


def test_four_case_partial_family_is_conservative_and_duplicates_fail():
    m = module("collect_v2_project_primary_family")
    row = {
        "project_case": "quantaalpha_opening_alpha158_increment",
        "group_t_p_two_sided": 0.139,
        "primary_ci_low": -0.04,
        "degenerate_sampling_variation": False,
    }
    assert m.adjust_project([row])[0]["project_adjusted_p"] == 0.556
    with pytest.raises(ValueError, match="incomplete"):
        m.adjust_project([row], True)
    with pytest.raises(ValueError, match="Duplicate"):
        m.adjust_project([row, row])


def test_full_project_family_retains_degenerate_contrast():
    m = module("collect_v2_project_primary_family")
    rows = [
        {
            "project_case": case,
            "group_t_p_two_sided": 0.003,
            "primary_ci_low": 0.001,
            "degenerate_sampling_variation": False,
        }
        for case in sorted(m.EXPECTED)
    ]
    rows[0].update(group_t_p_two_sided=0.0, degenerate_sampling_variation=True)
    out = m.adjust_project(rows, True)
    assert out[0]["project_adjusted_p"] == 1
    assert all(r["project_adjusted_p"] >= 0.012 for r in out[1:])


def test_partial_status_cannot_be_accepted_as_completed_analysis(tmp_path):
    import json

    m = module("collect_v2_project_primary_family")
    m.ROOT = tmp_path
    folder = tmp_path / "native_grouped_oos_analysis"
    folder.mkdir()
    path = folder / "comparisons.json"
    path.write_text("[]")
    (folder / "completion.json").write_text(
        json.dumps({"status": "waiting_for_inputs", "outputs": {"comparisons.json": m.sha256(path)}})
    )
    with pytest.raises(ValueError, match="not complete"):
        m.load(folder, "comparisons.json")


def test_real_date32_style_market_preserves_calendar_and_values(tmp_path):
    from datetime import date

    m = module("analyze_efs_pooled_v2")
    path = tmp_path / "market.parquet"
    pd.DataFrame(
        {
            "date": [date(2018, 12, 31), date(2019, 1, 2), date(2024, 12, 31), date(2025, 1, 2)],
            "ticker": ["A"] * 4,
            "ret": [0.9, 0.01, -0.02, 0.8],
        }
    ).to_parquet(path, index=False)
    result = m.load_market(path)
    assert result.index.equals(pd.DatetimeIndex(["2019-01-02", "2024-12-31"], name="date"))
    assert result.A.tolist() == [0.01, -0.02]
