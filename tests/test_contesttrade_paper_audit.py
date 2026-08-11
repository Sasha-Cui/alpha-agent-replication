from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_contesttrade_paper.py"
SPEC = importlib.util.spec_from_file_location("contesttrade_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_targets_cover_all_numeric_cells_in_tables_1_through_3() -> None:
    rows = audit.paper_result_rows()
    assert len(rows) == 49
    assert Counter(row["paper_table"] for row in rows) == {1: 27, 2: 4, 3: 18}
    assert len({(row["paper_table"], row["entity"], row["metric"]) for row in rows}) == 49


def test_zi_reward_semantics_expose_the_released_divergence() -> None:
    pairs = [(2.0, 5.0), (-2.0, -5.0)]
    assert audit.paper_zi_reward(pairs) == 20.0
    assert audit.released_zi_reward(pairs) == 5.0
    assert audit.paper_zi_reward([(-2.0, 5.0)]) == -10.0
    assert audit.released_zi_reward([(-2.0, 5.0)]) == 0.0
    assert audit.paper_zi_reward([(2.0, 5.0)]) == audit.released_zi_reward([(2.0, 5.0)])
    assert audit.paper_zi_reward([(1.0, 25.0)]) == 25.0
    assert audit.released_zi_reward([(1.0, 25.0)]) == 20.0


def test_committed_audit_preserves_the_native_result_boundary() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/contesttrade"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_1_3_conformance.csv")
    identities = read_csv(output / "paper_internal_consistency.csv")
    reachability = read_csv(output / "source_entrypoint_reachability.csv")
    zi_rows = read_csv(output / "zi_reward_semantics_audit.csv")
    models = read_csv(output / "shipped_lightgbm_model_inventory.csv")
    caches = read_csv(output / "released_cache_inventory.csv")
    config = read_csv(output / "source_config_conformance.csv")
    source = read_csv(output / "released_source_inventory.csv")

    assert manifest["overall_status"] == "not_reproduced_public_entrypoint_omits_contests"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_result_cells_total"] == 49
    assert manifest["native_paper_result_cells_reproduced"] == 0
    assert manifest["paper_numeric_result_cells_unavailable"] == 49
    assert manifest["paper_internal_repeated_cells_consistent"] == 3
    assert manifest["data_contest_reachable_from_public_entrypoint"] is False
    assert manifest["research_contest_reachable_from_public_entrypoint"] is False
    assert manifest["active_portfolio_constructor_present"] is False
    assert manifest["research_contest_required_model_files_present"] is False
    assert manifest["research_predict_signal_scores_method_present"] is False
    assert manifest["audit_unpickled_shipped_models"] is False
    assert manifest["audit_called_llm_or_external_api"] is False

    assert len(conformance) == 49
    assert {row["status"] for row in conformance} == {"unavailable_missing_native_result_path"}
    assert len(identities) == 3
    assert {row["status"] for row in identities} == {
        "paper_internal_identity_match_not_independent_reproduction"
    }
    assert Counter(row["status"] for row in zi_rows) == {"semantic_mismatch": 3, "match": 1}
    assert len(models) == 2
    assert {row["expected_five_feature_set"] for row in models} == {"True"}
    assert {row["safe_inspection_only"] for row in models} == {"True"}
    assert len(caches) == 7
    assert len(source) == 117
    assert len(config) == 29

    reach = {row["check"]: row for row in reachability}
    assert reach["active_workflow_nodes"]["status"] == "mismatch_contests_and_portfolio_absent"
    assert reach["data_contest_reachable"]["observed"] == "False"
    assert reach["research_contest_reachable"]["observed"] == "False"
    assert reach["research_model_files"]["status"] == "missing_both_required_models"
    assert reach["research_predict_signal_scores_method"]["status"] == "missing_called_method"

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_source_static_checks_when_source_is_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/contesttrade_source")
    if not source_root.exists():
        return
    rows = audit.entrypoint_reachability(source_root)
    checks = {row["check"]: row for row in rows}
    assert checks["public_cli_import"]["observed"] == "True"
    assert checks["active_workflow_nodes"]["observed"] == (
        "['run_data_agents', 'run_research_agents', 'finalize']"
    )
    assert audit.git_head(source_root) == audit.SOURCE_COMMIT
