"""Small, dependency-free categorical Fisher metric primitives."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def categorical_probabilities(logits: ArrayLike) -> NDArray[np.float64]:
    """Return numerically stable probabilities for one logit vector."""

    values = np.asarray(logits, dtype=np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("logits must be a finite one-dimensional vector")
    shifted = values - np.max(values)
    weights = np.exp(shifted)
    return weights / np.sum(weights)


def categorical_fisher_quadratic(
    probabilities: ArrayLike,
    logit_tangent: ArrayLike,
) -> float:
    """Evaluate ``v.T (diag(p) - p p.T) v`` without forming the matrix."""

    probs = np.asarray(probabilities, dtype=np.float64)
    tangent = np.asarray(logit_tangent, dtype=np.float64)
    if probs.ndim != 1 or tangent.shape != probs.shape:
        raise ValueError("probabilities and logit_tangent must be matching vectors")
    if not np.all(np.isfinite(probs)) or not np.all(np.isfinite(tangent)):
        raise ValueError("inputs must contain only finite values")
    if np.any(probs < 0.0) or not np.isclose(np.sum(probs), 1.0, atol=1e-8):
        raise ValueError("probabilities must be non-negative and sum to one")

    mean = float(np.dot(probs, tangent))
    return float(np.dot(probs, np.square(tangent - mean)))


def pullback_fisher_matrix(
    logit_jacobian: ArrayLike,
    probabilities: ArrayLike,
) -> NDArray[np.float64]:
    """Return the hidden-space Fisher pullback ``J.T F J``.

    ``logit_jacobian`` has shape ``(vocab, hidden)``.  The implementation uses
    centered rows and does not materialize a vocabulary-sized Fisher matrix.
    """

    jacobian = np.asarray(logit_jacobian, dtype=np.float64)
    probs = np.asarray(probabilities, dtype=np.float64)
    if jacobian.ndim != 2 or probs.shape != (jacobian.shape[0],):
        raise ValueError("expected jacobian (vocab, hidden) and probabilities (vocab,)")
    if np.any(probs < 0.0) or not np.isclose(np.sum(probs), 1.0, atol=1e-8):
        raise ValueError("probabilities must be non-negative and sum to one")
    mean_row = probs @ jacobian
    centered = jacobian - mean_row
    return centered.T @ (probs[:, None] * centered)
