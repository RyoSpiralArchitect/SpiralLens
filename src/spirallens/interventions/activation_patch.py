"""Subspace-selective activation patching."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def patch_subspace(
    recipient: ArrayLike,
    donor: ArrayLike,
    frame: ArrayLike,
    *,
    strength: float = 1.0,
) -> NDArray[np.float64]:
    """Replace recipient coefficients by donor coefficients in a declared frame."""

    target = np.asarray(recipient, dtype=np.float64)
    source = np.asarray(donor, dtype=np.float64)
    basis = np.asarray(frame, dtype=np.float64)
    if target.shape != source.shape or target.ndim < 1:
        raise ValueError("recipient and donor must have matching non-scalar shapes")
    if basis.ndim != 2 or basis.shape[0] != target.shape[-1]:
        raise ValueError("frame must have shape (value width, rank)")
    if not np.allclose(basis.T @ basis, np.eye(basis.shape[1]), atol=1e-8):
        raise ValueError("frame columns must be orthonormal")
    if not np.isfinite(strength):
        raise ValueError("strength must be finite")
    coefficient_delta = (source - target) @ basis
    return target + strength * coefficient_delta @ basis.T
