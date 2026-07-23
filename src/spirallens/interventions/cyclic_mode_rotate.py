"""Rotate a declared two-dimensional mode without changing its norm."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True)
class RotationAudit:
    value: NDArray[np.float64]
    input_norm: NDArray[np.float64]
    output_norm: NDArray[np.float64]
    mode_input_norm: NDArray[np.float64]
    mode_output_norm: NDArray[np.float64]
    angle: float


def cyclic_mode_rotate(
    value: ArrayLike,
    frame: ArrayLike,
    angle: float,
    *,
    center: ArrayLike | None = None,
) -> RotationAudit:
    """Rotate coordinates in an orthonormal 2-plane and audit norm preservation."""

    x = np.asarray(value, dtype=np.float64)
    plane = np.asarray(frame, dtype=np.float64)
    if x.ndim < 1 or plane.shape != (x.shape[-1], 2):
        raise ValueError("frame must have shape (value width, 2)")
    if not np.allclose(plane.T @ plane, np.eye(2), atol=1e-8):
        raise ValueError("frame columns must be orthonormal")
    origin = np.zeros(x.shape[-1], dtype=np.float64) if center is None else np.asarray(
        center,
        dtype=np.float64,
    )
    if origin.shape != (x.shape[-1],):
        raise ValueError("center must match the value width")
    if not np.isfinite(angle):
        raise ValueError("angle must be finite")

    displaced = x - origin
    coordinates = displaced @ plane
    cosine = np.cos(angle)
    sine = np.sin(angle)
    rotation_transpose = np.array(
        [[cosine, sine], [-sine, cosine]],
        dtype=np.float64,
    )
    rotated_coordinates = coordinates @ rotation_transpose
    remainder = displaced - coordinates @ plane.T
    output = origin + remainder + rotated_coordinates @ plane.T
    return RotationAudit(
        value=output,
        input_norm=np.linalg.norm(displaced, axis=-1),
        output_norm=np.linalg.norm(output - origin, axis=-1),
        mode_input_norm=np.linalg.norm(coordinates, axis=-1),
        mode_output_norm=np.linalg.norm(rotated_coordinates, axis=-1),
        angle=float(angle),
    )
