"""Conservative family adjustment for grouped economic evidence."""

import math
from alpha_evolve.publication_inference import holm_adjust


def adjust_grouped_family(rows, family_size, complete):
    if not rows or family_size < len(rows) or (complete and len(rows) != family_size):
        raise ValueError("Incomplete or invalid multiplicity family")
    inputs = []
    for row in rows:
        raw = float(row["group_t_p_two_sided"])
        if not math.isfinite(raw) or not 0 <= raw <= 1:
            raise ValueError("Invalid grouped p-value")
        # A degenerate estimator has no usable sampling distribution. Its raw
        # diagnostic p=0 must not lower another contrast's Holm multiplier.
        inputs.append(1.0 if row["degenerate_sampling_variation"] else raw)
    adjusted = holm_adjust(inputs) if complete else [min(1.0, family_size * p) for p in inputs]
    return inputs, [float(p) for p in adjusted]
