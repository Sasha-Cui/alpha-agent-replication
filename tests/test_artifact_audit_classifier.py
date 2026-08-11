from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_artifact_audit.py"
SPEC = importlib.util.spec_from_file_location("build_artifact_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def test_coming_soon_roadmap_does_not_demote_substantial_package() -> None:
    assert audit.explicitly_nonrunnable(
        "coming soon: a separate future project", has_code=True, has_runner=True
    ) is False
    tier, basis = audit.static_fidelity(
        [
            {
                "reachable": True,
                "url": "https://example.invalid/repo",
                "static_observation": {
                    "explicit_nonrunnable": False,
                    "has_code": True,
                    "has_environment": True,
                    "has_runner": True,
                    "has_support": True,
                },
            }
        ],
        "reachable_all",
    )
    assert tier == "R3"
    assert basis["evidence"][0]["basis"] == (
        "code+environment+runner+tests/examples/config"
    )


def test_placeholder_coming_soon_and_strong_disclaimer_stay_nonrunnable() -> None:
    assert audit.explicitly_nonrunnable(
        "inference code coming soon", has_code=False, has_runner=False
    ) is True
    assert audit.explicitly_nonrunnable(
        "this does not contain a runnable version", has_code=True, has_runner=True
    ) is True
