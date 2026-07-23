"""Orthogonal Procrustes connections between local subspace frames."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True)
class ProcrustesConnection:
    """Best orthogonal coordinate alignment from source frame to target frame."""

    rotation: NDArray[np.float64]
    singular_values: NDArray[np.float64]
    residual_frobenius: float
    orientation_preserving: bool


def _validated_frame(frame: ArrayLike, *, name: str) -> NDArray[np.float64]:
    value = np.asarray(frame, dtype=np.float64)
    if value.ndim != 2 or value.shape[0] < value.shape[1]:
        raise ValueError(f"{name} must have shape (ambient >= rank, rank)")
    if not np.all(np.isfinite(value)):
        raise ValueError(f"{name} must contain only finite values")
    gram = value.T @ value
    if not np.allclose(gram, np.eye(value.shape[1]), atol=1e-8):
        raise ValueError(f"{name} columns must be orthonormal")
    return value


def procrustes_connection(
    source_frame: ArrayLike,
    target_frame: ArrayLike,
    *,
    require_proper_rotation: bool = False,
) -> ProcrustesConnection:
    """Find ``Q`` minimizing ``||source_frame Q - target_frame||_F``."""

    source = _validated_frame(source_frame, name="source_frame")
    target = _validated_frame(target_frame, name="target_frame")
    if source.shape != target.shape:
        raise ValueError(f"frame shape mismatch: {source.shape} != {target.shape}")

    left, singular_values, right_transpose = np.linalg.svd(
        source.T @ target,
        full_matrices=False,
    )
    rotation = left @ right_transpose
    if require_proper_rotation and np.linalg.det(rotation) < 0.0:
        left = left.copy()
        left[:, -1] *= -1.0
        rotation = left @ right_transpose
    aligned = source @ rotation
    return ProcrustesConnection(
        rotation=rotation,
        singular_values=singular_values,
        residual_frobenius=float(np.linalg.norm(aligned - target, ord="fro")),
        orientation_preserving=bool(np.linalg.det(rotation) > 0.0),
    )
