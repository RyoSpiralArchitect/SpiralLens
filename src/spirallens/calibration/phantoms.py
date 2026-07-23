"""Closed-form fields and frame families with known expected behavior."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from spirallens.contracts import SampledLoop


def rotation_matrix_2d(angle_rad: float) -> NDArray[np.floating]:
    """Return an SO(2) rotation matrix."""

    if not np.isfinite(angle_rad):
        raise ValueError("angle_rad must be finite")
    cosine = np.cos(angle_rad)
    sine = np.sin(angle_rad)
    return np.array([[cosine, -sine], [sine, cosine]], dtype=float)


def complex_vortex_field(
    charge: int,
    *,
    core: tuple[float, float] = (0.0, 0.0),
    core_scale: float = 0.25,
) -> Callable[[NDArray[np.floating]], NDArray[np.complexfloating]]:
    """Return a smooth-amplitude complex field with declared integer charge.

    The core has zero amplitude, so its angle is intentionally undefined.
    Information is recovered from a loop around the core, never from the core
    sample itself.
    """

    if not isinstance(charge, (int, np.integer)):
        raise TypeError("charge must be an integer")
    core_array = np.asarray(core, dtype=float)
    if core_array.shape != (2,) or not np.all(np.isfinite(core_array)):
        raise ValueError("core must contain two finite coordinates")
    if not np.isfinite(core_scale) or core_scale <= 0:
        raise ValueError("core_scale must be finite and positive")

    def field(points: NDArray[np.floating]) -> NDArray[np.complexfloating]:
        values = np.asarray(points, dtype=float)
        if values.ndim != 2 or values.shape[1] != 2:
            raise ValueError("complex vortex field expects points with shape (n, 2)")
        if not np.all(np.isfinite(values)):
            raise ValueError("points must contain only finite values")
        relative = values - core_array
        radius = np.linalg.norm(relative, axis=1)
        polar_angle = np.arctan2(relative[:, 1], relative[:, 0])
        exponent = max(1, abs(int(charge)))
        envelope = np.tanh(radius / core_scale) ** exponent
        return envelope * np.exp(1j * int(charge) * polar_angle)

    return field


def _polar_coordinates(
    points: NDArray[np.floating],
    core: tuple[float, float],
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    values = np.asarray(points, dtype=float)
    core_array = np.asarray(core, dtype=float)
    if values.ndim != 2 or values.shape[1] != 2:
        raise ValueError("frame phantom expects points with shape (n, 2)")
    if core_array.shape != (2,):
        raise ValueError("core must contain two coordinates")
    relative = values - core_array
    return (
        np.linalg.norm(relative, axis=1),
        np.arctan2(relative[:, 1], relative[:, 0]),
    )


def stretch_frames(
    points: NDArray[np.floating],
    *,
    strength: float = 0.6,
    core: tuple[float, float] = (0.0, 0.0),
) -> NDArray[np.floating]:
    """Periodic axis-aligned stretch frames with unit determinant."""

    if not np.isfinite(strength):
        raise ValueError("strength must be finite")
    _radius, polar_angle = _polar_coordinates(points, core)
    log_scale = strength * np.cos(polar_angle)
    frames = np.zeros((len(polar_angle), 2, 2), dtype=float)
    frames[:, 0, 0] = np.exp(log_scale)
    frames[:, 1, 1] = np.exp(-log_scale)
    return frames


def radial_scale_frames(
    points: NDArray[np.floating],
    *,
    strength: float = 0.5,
    core: tuple[float, float] = (0.0, 0.0),
) -> NDArray[np.floating]:
    """Radial/tangential scale frames whose local axes rotate around the core."""

    if not np.isfinite(strength):
        raise ValueError("strength must be finite")
    radius, polar_angle = _polar_coordinates(points, core)
    radial_log_scale = strength * np.tanh(radius)
    frames: list[NDArray[np.floating]] = []
    for angle, log_scale in zip(polar_angle, radial_log_scale, strict=True):
        basis = rotation_matrix_2d(float(angle))
        local_scale = np.diag((np.exp(log_scale), np.exp(-0.5 * log_scale)))
        frames.append(basis @ local_scale @ basis.T)
    return np.stack(frames)


def shear_frames(
    points: NDArray[np.floating],
    *,
    strength: float = 0.9,
    core: tuple[float, float] = (0.0, 0.0),
) -> NDArray[np.floating]:
    """Periodic non-normal shear frames."""

    if not np.isfinite(strength):
        raise ValueError("strength must be finite")
    _radius, polar_angle = _polar_coordinates(points, core)
    shear = strength * (0.25 + np.sin(polar_angle))
    frames = np.broadcast_to(np.eye(2), (len(polar_angle), 2, 2)).copy()
    frames[:, 0, 1] = shear
    return frames


def basis_rotation_frames(
    points: NDArray[np.floating],
    *,
    turns: int = 1,
    wobble_rad: float = 0.2,
    core: tuple[float, float] = (0.0, 0.0),
) -> NDArray[np.floating]:
    """A single-valued rotating basis used as a pure-gauge null."""

    if not isinstance(turns, (int, np.integer)):
        raise TypeError("turns must be an integer")
    if not np.isfinite(wobble_rad):
        raise ValueError("wobble_rad must be finite")
    _radius, polar_angle = _polar_coordinates(points, core)
    basis_angle = int(turns) * polar_angle + wobble_rad * np.sin(polar_angle)
    return np.stack(
        [rotation_matrix_2d(float(angle)) for angle in basis_angle]
    )


def injected_rotation_edge_transports(
    loop: SampledLoop,
    total_angle_rad: float,
) -> NDArray[np.floating]:
    """Distribute a known total SO(2) rotation over a loop's edges."""

    if not np.isfinite(total_angle_rad):
        raise ValueError("total_angle_rad must be finite")
    edge_lengths = np.linalg.norm(loop.edge_vectors, axis=1)
    fractions = edge_lengths / edge_lengths.sum()
    return np.stack(
        [
            rotation_matrix_2d(float(total_angle_rad * fraction))
            for fraction in fractions
        ]
    )


def so2_vortex_connection(
    strength: float,
    *,
    core: tuple[float, float] = (0.0, 0.0),
    exclusion_radius: float = 1e-12,
) -> Callable[[NDArray[np.floating]], NDArray[np.floating]]:
    """Return ``strength * J dtheta`` as a singular SO(2) connection.

    A centered enclosing loop has transport angle ``2*pi*strength`` modulo
    ``2*pi``. A loop that does not enclose the core integrates to zero. Integer
    strength therefore gives identity matrix holonomy even though a separate
    complex order parameter may have nonzero integer winding.
    """

    if not np.isfinite(strength):
        raise ValueError("strength must be finite")
    core_array = np.asarray(core, dtype=float)
    if core_array.shape != (2,) or not np.all(np.isfinite(core_array)):
        raise ValueError("core must contain two finite coordinates")
    if not np.isfinite(exclusion_radius) or exclusion_radius < 0:
        raise ValueError("exclusion_radius must be finite and non-negative")
    generator = np.array([[0.0, -1.0], [1.0, 0.0]])

    def connection(point: NDArray[np.floating]) -> NDArray[np.floating]:
        location = np.asarray(point, dtype=float)
        if location.shape != (2,) or not np.all(np.isfinite(location)):
            raise ValueError("SO(2) vortex connection expects one planar point")
        x, y = location - core_array
        radius_squared = float(x * x + y * y)
        if radius_squared <= exclusion_radius * exclusion_radius:
            raise ValueError("connection is undefined at the vortex core")
        coefficients = strength * np.array(
            [-y / radius_squared, x / radius_squared]
        )
        return coefficients[:, None, None] * generator[None, :, :]

    return connection
