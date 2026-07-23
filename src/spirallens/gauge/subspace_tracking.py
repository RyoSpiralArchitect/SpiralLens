"""Track a low-rank subspace without mistaking basis flips for dynamics."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from spirallens.gauge.procrustes_connection import procrustes_connection


@dataclass(frozen=True)
class TrackedSubspaces:
    """Gauge-aligned frames and edge-wise connection metadata."""

    frames: tuple[NDArray[np.float64], ...]
    connections: tuple[NDArray[np.float64], ...]
    principal_angles: tuple[NDArray[np.float64], ...]
    alignment_residuals: tuple[float, ...]


def orthonormal_frame(matrix: ArrayLike, *, rank: int | None = None) -> NDArray[np.float64]:
    """Return an orthonormal column frame spanning a matrix's leading range."""

    value = np.asarray(matrix, dtype=np.float64)
    if value.ndim != 2 or not np.all(np.isfinite(value)):
        raise ValueError("matrix must be finite and two-dimensional")
    maximum_rank = min(value.shape)
    retained = maximum_rank if rank is None else int(rank)
    if not 1 <= retained <= maximum_rank:
        raise ValueError("rank lies outside the available matrix dimensions")
    left, singular_values, _ = np.linalg.svd(value, full_matrices=False)
    if singular_values[retained - 1] <= np.finfo(np.float64).eps:
        raise ValueError("requested frame includes a numerically null direction")
    frame = left[:, :retained]

    # Resolve the sign only for reproducible serialization.  Scientific
    # comparisons still use Procrustes alignment and do not rely on this gauge.
    largest_rows = np.argmax(np.abs(frame), axis=0)
    signs = np.sign(frame[largest_rows, np.arange(retained)])
    signs[signs == 0.0] = 1.0
    return frame * signs


def principal_angles(
    frame_a: ArrayLike,
    frame_b: ArrayLike,
) -> NDArray[np.float64]:
    """Return canonical angles between two equal-rank orthonormal frames."""

    left = np.asarray(frame_a, dtype=np.float64)
    right = np.asarray(frame_b, dtype=np.float64)
    if left.shape != right.shape or left.ndim != 2:
        raise ValueError("frames must have matching two-dimensional shapes")
    if not np.allclose(left.T @ left, np.eye(left.shape[1]), atol=1e-8):
        raise ValueError("frame_a columns must be orthonormal")
    if not np.allclose(right.T @ right, np.eye(right.shape[1]), atol=1e-8):
        raise ValueError("frame_b columns must be orthonormal")
    singular_values = np.linalg.svd(left.T @ right, compute_uv=False)
    return np.arccos(np.clip(singular_values, -1.0, 1.0))


def track_subspaces(
    frames: Sequence[ArrayLike],
    *,
    require_proper_rotation: bool = False,
) -> TrackedSubspaces:
    """Sequentially align frames while retaining their physical subspace drift."""

    if not frames:
        raise ValueError("frames must not be empty")
    raw = tuple(np.asarray(frame, dtype=np.float64) for frame in frames)
    shape = raw[0].shape
    if any(frame.shape != shape for frame in raw):
        raise ValueError("all frames must have matching shapes")
    for index, frame in enumerate(raw):
        if not np.allclose(frame.T @ frame, np.eye(shape[1]), atol=1e-8):
            raise ValueError(f"frame {index} columns must be orthonormal")

    aligned: list[NDArray[np.float64]] = [raw[0]]
    connections: list[NDArray[np.float64]] = []
    angles: list[NDArray[np.float64]] = []
    residuals: list[float] = []
    for current in raw[1:]:
        angles.append(principal_angles(aligned[-1], current))
        connection = procrustes_connection(
            current,
            aligned[-1],
            require_proper_rotation=require_proper_rotation,
        )
        aligned_current = current @ connection.rotation
        aligned.append(aligned_current)
        connections.append(connection.rotation)
        residuals.append(connection.residual_frobenius)
    return TrackedSubspaces(
        frames=tuple(aligned),
        connections=tuple(connections),
        principal_angles=tuple(angles),
        alignment_residuals=tuple(residuals),
    )
