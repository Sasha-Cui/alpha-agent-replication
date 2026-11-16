"""Compare identical factor programs with and without future market observations."""

from __future__ import annotations
import numpy as np
import pandas as pd


def compare_prefix(reference, prefix, cutoff, tolerance=1e-12, require_future_rows=False):
    """Require the complete earlier index, columns, finite values and missing mask."""
    if isinstance(reference, pd.Series):
        reference = reference.to_frame()
    if isinstance(prefix, pd.Series):
        prefix = prefix.to_frame()
    if "datetime" not in reference.index.names or "datetime" not in prefix.index.names:
        raise ValueError("Factor must have a datetime index level")
    if require_future_rows and not (reference.index.get_level_values("datetime") > pd.Timestamp(cutoff)).any():
        raise ValueError("A causality check must remove actual future observations")
    expected = reference.loc[reference.index.get_level_values("datetime") <= pd.Timestamp(cutoff)].sort_index()
    actual = prefix.sort_index()
    if expected.index.has_duplicates or actual.index.has_duplicates:
        raise ValueError("Ambiguous duplicate factor index")
    if not expected.index.equals(actual.index) or not expected.columns.equals(actual.columns):
        return {
            "status": "fail",
            "reason": "earlier index or columns changed",
            "expected_rows": len(expected),
            "actual_rows": len(actual),
        }
    if not len(expected):
        raise ValueError("Empty prefix is not a causality check")
    left, right = expected.to_numpy(dtype=float), actual.to_numpy(dtype=float)
    equal = np.isclose(left, right, rtol=tolerance, atol=tolerance, equal_nan=True)
    finite = np.isfinite(left) & np.isfinite(right)
    differences = np.abs(left[finite] - right[finite])
    changed = np.argwhere(~equal)
    witnesses = []
    for i, j in changed[:10]:

        def number(value):
            return float(value) if np.isfinite(value) else str(value)

        witnesses.append(
            {
                "index": str(expected.index[i]),
                "column": str(expected.columns[j]),
                "full_value": number(left[i, j]),
                "prefix_value": number(right[i, j]),
            }
        )
    return {
        "status": "pass" if equal.all() else "fail",
        "rows": len(expected),
        "columns": len(expected.columns),
        "changed_values": int((~equal).sum()),
        "nan_mask_differences": int((np.isnan(left) != np.isnan(right)).sum()),
        "maximum_finite_absolute_difference": float(differences.max()) if len(differences) else None,
        "infinite_values": int(np.isinf(left).sum() + np.isinf(right).sum()),
        "witnesses": witnesses,
        "scope": "Prefix invariance checks future-row dependence; it does not establish paper fidelity, absence of historical model contamination or economic profitability.",
    }
