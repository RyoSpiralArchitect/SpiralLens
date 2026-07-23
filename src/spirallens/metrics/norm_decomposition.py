r"""Separate radial norm changes from angular displacement.

For vectors ``a`` and ``b`` the Euclidean distance has the exact decomposition

.. math::

   ||a-b||^2 = (||a||-||b||)^2
              + 2 ||a|| ||b|| (1-\cos(a,b)).

The first term is radial.  The second is angular.  Keeping both terms prevents
a large norm change from being reported as evidence of a rotation-like
candidate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True)
class NormAngularDecomposition:
    """Scalar decomposition for a pair of one-dimensional vectors."""

    norm_a: float
    norm_b: float
    cosine_similarity: float
    euclidean_distance: float
    radial_distance: float
    angular_distance: float
    relative_norm_gap: float
    angular_fraction_sq: float
    unit_chord_distance: float

    def to_dict(self, *, prefix: str = "") -> dict[str, float]:
        """Return JSON-ready values, optionally prefixing every key."""

        return {f"{prefix}{key}": value for key, value in asdict(self).items()}


def _as_floating_array(value: ArrayLike) -> NDArray[np.float64]:
    array = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError("vectors must contain only finite values")
    return array


def cosine_similarity(a: ArrayLike, b: ArrayLike, *, epsilon: float = 1e-12) -> float:
    """Return a guarded cosine similarity for two non-zero vectors."""

    left = _as_floating_array(a)
    right = _as_floating_array(b)
    if left.shape != right.shape:
        raise ValueError(f"shape mismatch: {left.shape} != {right.shape}")
    if left.ndim != 1:
        raise ValueError("cosine_similarity expects one-dimensional vectors")

    norm_a = float(np.linalg.norm(left))
    norm_b = float(np.linalg.norm(right))
    if norm_a <= epsilon or norm_b <= epsilon:
        raise ValueError("cosine similarity is undefined for a near-zero vector")
    cosine = float(np.dot(left, right) / (norm_a * norm_b))
    return float(np.clip(cosine, -1.0, 1.0))


def decompose_difference(
    a: ArrayLike,
    b: ArrayLike,
    *,
    epsilon: float = 1e-12,
) -> NormAngularDecomposition:
    """Return the exact norm/angular decomposition for a vector pair."""

    left = _as_floating_array(a)
    right = _as_floating_array(b)
    if left.shape != right.shape:
        raise ValueError(f"shape mismatch: {left.shape} != {right.shape}")
    if left.ndim != 1:
        raise ValueError("decompose_difference expects one-dimensional vectors")

    norm_a = float(np.linalg.norm(left))
    norm_b = float(np.linalg.norm(right))
    if norm_a <= epsilon or norm_b <= epsilon:
        raise ValueError("norm/angular decomposition requires non-zero vectors")

    cosine = float(np.clip(np.dot(left, right) / (norm_a * norm_b), -1.0, 1.0))
    radial_sq = (norm_a - norm_b) ** 2
    angular_sq = max(0.0, 2.0 * norm_a * norm_b * (1.0 - cosine))
    total_sq = max(0.0, radial_sq + angular_sq)
    mean_norm = 0.5 * (norm_a + norm_b)

    return NormAngularDecomposition(
        norm_a=norm_a,
        norm_b=norm_b,
        cosine_similarity=cosine,
        euclidean_distance=float(np.sqrt(total_sq)),
        radial_distance=abs(norm_a - norm_b),
        angular_distance=float(np.sqrt(angular_sq)),
        relative_norm_gap=abs(norm_a - norm_b) / max(mean_norm, epsilon),
        angular_fraction_sq=angular_sq / max(total_sq, epsilon),
        unit_chord_distance=float(np.sqrt(max(0.0, 2.0 * (1.0 - cosine)))),
    )


def pairwise_decomposition_from_cosine(
    norms_a: ArrayLike,
    norms_b: ArrayLike,
    cosines: ArrayLike,
    *,
    epsilon: float = 1e-12,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Vectorized radial, angular, and relative-norm terms for a cosine block.

    ``norms_a`` and ``norms_b`` are one-dimensional and ``cosines`` has shape
    ``(len(norms_a), len(norms_b))``.
    """

    left_norms = _as_floating_array(norms_a)
    right_norms = _as_floating_array(norms_b)
    cosine_block = _as_floating_array(cosines)
    expected = (left_norms.size, right_norms.size)
    if left_norms.ndim != 1 or right_norms.ndim != 1:
        raise ValueError("norm arrays must be one-dimensional")
    if cosine_block.shape != expected:
        raise ValueError(f"cosine block has shape {cosine_block.shape}, expected {expected}")

    left = left_norms[:, None]
    right = right_norms[None, :]
    radial = np.abs(left - right)
    angular = np.sqrt(np.maximum(0.0, 2.0 * left * right * (1.0 - cosine_block)))
    relative_norm_gap = radial / np.maximum(0.5 * (left + right), epsilon)
    return radial, angular, relative_norm_gap
