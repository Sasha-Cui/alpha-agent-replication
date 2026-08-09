"""Input-data policy checks used by legacy diagnostic scripts."""
from __future__ import annotations

import os

APPROVED_INPUT_POLICY = (
    "Valid counted experiments must use only read-only JKP data or the "
    "external factor-data project return-data assembly. Paper-shipped, live, yfinance, "
    "China/A-share, crypto, or official-French-download returns are legacy "
    "diagnostics and must not be counted as valid alpha evidence."
)

LEGACY_NON_JKP_MESSAGE = (
    "This is a legacy non-JKP return-data script. It is disabled by default. "
    + APPROVED_INPUT_POLICY
    + " Set ALLOW_LEGACY_NON_JKP_RETURNS=1 only for explicit non-counting audit reproduction."
)


def require_legacy_non_jkp_opt_in() -> None:
    if os.environ.get("ALLOW_LEGACY_NON_JKP_RETURNS") != "1":
        raise SystemExit(LEGACY_NON_JKP_MESSAGE)
