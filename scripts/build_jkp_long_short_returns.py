#!/usr/bin/env python3
"""Compatibility wrapper: Build USA/JKP-only monthly candidate and benchmark factor returns."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from alpha_evolve.jkp import *  # noqa: F401,F403,E402
from alpha_evolve.jkp import main  # noqa: E402


if __name__ == "__main__":
    main()
