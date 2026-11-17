"""Regression guards for strict new lint plus byte-bound historical diagnostics."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("frozen_lint", Path(__file__).parents[1] / "scripts/check_frozen_lint.py")
LINT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINT)


class FrozenLintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "scripts/frozen.py"
        source.parent.mkdir()
        source.write_text("x = 1; x += 1\n")
        self.source = source
        self.baseline = {"files": {"scripts/frozen.py": {
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "diagnostics": {"E702": 1}}},
            "diagnostic_count": 1}
        self.diagnostics = [{"filename": str(source), "code": "E702"}]

    def test_exact_frozen_source_and_findings_pass(self):
        self.assertEqual(LINT.compare_diagnostics(self.root, self.diagnostics, self.baseline), [])

    def test_changed_source_with_same_lint_count_fails(self):
        self.source.write_text("x = 9; x += 1\n")
        self.assertTrue(any("bytes changed" in e for e in self.compare()))

    def test_new_file_finding_is_not_hidden(self):
        self.diagnostics.append({"filename": str(self.root / "scripts/new.py"), "code": "F401"})
        self.assertTrue(any("New lint findings" in e for e in self.compare()))

    def test_additional_finding_in_frozen_file_fails(self):
        self.diagnostics.append({"filename": str(self.source), "code": "E702"})
        self.assertTrue(any("counts changed" in e for e in self.compare()))

    def test_missing_frozen_source_fails(self):
        self.source.unlink()
        self.assertTrue(any("missing" in e for e in self.compare()))

    def test_unknown_safety_rule_cannot_be_recorded_as_legacy(self):
        baseline = copy.deepcopy(self.baseline)
        baseline["files"]["scripts/frozen.py"]["diagnostics"] = {"F821": 1}
        diagnostics = [{"filename": str(self.source), "code": "F821"}]
        errors = LINT.compare_diagnostics(self.root, diagnostics, baseline)
        self.assertTrue(any("Unsupported legacy rule" in e for e in errors))

    def test_removed_diagnostic_requires_explicit_record_review(self):
        self.diagnostics.clear()
        self.assertTrue(any("counts changed" in e for e in self.compare()))

    def compare(self):
        return LINT.compare_diagnostics(self.root, self.diagnostics, self.baseline)


if __name__ == "__main__":
    unittest.main()
