"""Status regressions: completed source/processes cannot hide missing financial paths."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("repository_docs", Path(__file__).parents[1] / "scripts/check_repository_docs.py")
DOCS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOCS)


class V2AdmissionStatusTests(unittest.TestCase):
    def setUp(self):
        self.status = {"study_status": "provisional", "mechanism_inventory": {
            "monthly_admitted_paper_ids": ["M023", "M050"],
            "primary_economic_comparison_admitted_paper_ids": ["M023"]}}
        self.package = {"source_admitted_paper_ids": ["M023", "M050"], "cases": {
            "M023": {"source_complete": True, "exact_replay_complete": True,
                     "verified_paths": 2, "failed_paths": 0, "primary_comparison_admitted": True},
            "M050": {"source_complete": True, "exact_replay_complete": True,
                     "verified_paths": 1, "failed_paths": 2, "primary_comparison_admitted": False,
                     "scheduler_exit_code": "0:0"}}}
        self.paths = [
            {"paper_id": "M023", "arm": a, "fee_bps": "10", "status": "verified_conditional_account"}
            for a in ["LLM_pooled", "grammar_pooled"]] + [
            {"paper_id": "M050", "arm": "ratio_FinBERT_nonhold", "fee_bps": "10", "status": "verified_conditional_account"},
            {"paper_id": "M050", "arm": "ratio_LLMS_nonhold", "fee_bps": "10", "status": "blocked"},
            {"paper_id": "M050", "arm": "ratio_universe_EW", "fee_bps": "10", "status": "blocked"}]

    def test_complete_source_and_partial_finance_are_validly_distinct(self):
        self.assertEqual(DOCS.validate_v2_admission(self.status, self.package, self.paths), [])

    def test_exit_zero_cannot_admit_a_failed_primary(self):
        bad = copy.deepcopy(self.package)
        bad["cases"]["M050"]["primary_comparison_admitted"] = True
        self.assertTrue(any("primary financial" in x for x in DOCS.validate_v2_admission(self.status, bad, self.paths)))

    def test_complete_study_cannot_hide_blocked_primary(self):
        bad = copy.deepcopy(self.status)
        bad["study_status"] = "complete"
        self.assertTrue(any("claim completion" in x for x in DOCS.validate_v2_admission(bad, self.package, self.paths)))

    def test_aggregate_counts_cannot_omit_a_failure(self):
        bad = copy.deepcopy(self.package)
        bad["cases"]["M050"]["failed_paths"] = 1
        self.assertTrue(any("path counts" in x for x in DOCS.validate_v2_admission(self.status, bad, self.paths)))


if __name__ == "__main__":
    unittest.main()
