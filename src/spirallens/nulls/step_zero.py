"""Initial-checkpoint and architecture-baseline controls."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def baseline_corrected_operator(
    full_operator: ArrayLike,
    baseline_operator: ArrayLike,
) -> NDArray[np.float64]:
    """Return the group-relative operator ``baseline^-1 full``."""

    full = np.asarray(full_operator, dtype=np.float64)
    baseline = np.asarray(baseline_operator, dtype=np.float64)
    if full.shape != baseline.shape or full.ndim != 2 or full.shape[0] != full.shape[1]:
        raise ValueError("operators must be matching square matrices")
    try:
        return np.linalg.solve(baseline, full)
    except np.linalg.LinAlgError as error:
        raise ValueError("baseline operator is singular") from error


def matched_delta(observed: ArrayLike, baseline: ArrayLike) -> NDArray[np.float64]:
    """Return an additive delta for scalar/vector observables only."""

    value = np.asarray(observed, dtype=np.float64)
    control = np.asarray(baseline, dtype=np.float64)
    if value.shape != control.shape:
        raise ValueError("observed and baseline must have matching shapes")
    return value - control
