"""Orthogonal-basis reparameterization controls."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def random_orthogonal(width: int, *, seed: int, proper: bool = True) -> NDArray[np.float64]:
    """Draw a deterministic Haar-like orthogonal basis change."""

    if width <= 0:
        raise ValueError("width must be positive")
    rng = np.random.default_rng(seed)
    q, r = np.linalg.qr(rng.standard_normal((width, width)))
    signs = np.sign(np.diag(r))
    signs[signs == 0.0] = 1.0
    q = q * signs
    if proper and np.linalg.det(q) < 0.0:
        q[:, -1] *= -1.0
    return q


def conjugate_operator(operator: ArrayLike, basis_change: ArrayLike) -> NDArray[np.float64]:
    """Express a square column-vector operator in a new orthogonal basis."""

    matrix = np.asarray(operator, dtype=np.float64)
    basis = np.asarray(basis_change, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("operator must be square")
    if basis.shape != matrix.shape or not np.allclose(
        basis.T @ basis,
        np.eye(basis.shape[0]),
        atol=1e-8,
    ):
        raise ValueError("basis_change must be a matching orthogonal matrix")
    return basis.T @ matrix @ basis


def spectrum_invariance_error(
    operator: ArrayLike,
    reparameterized_operator: ArrayLike,
) -> float:
    """Return optimal-matching spectral discrepancy for a basis null."""

    from scipy.optimize import linear_sum_assignment

    original = np.linalg.eigvals(np.asarray(operator, dtype=np.float64))
    changed = np.linalg.eigvals(np.asarray(reparameterized_operator, dtype=np.float64))
    if original.shape != changed.shape:
        raise ValueError("operators must have the same spectral size")
    costs = np.abs(original[:, None] - changed[None, :])
    rows, columns = linear_sum_assignment(costs)
    return float(np.max(costs[rows, columns], initial=0.0))
