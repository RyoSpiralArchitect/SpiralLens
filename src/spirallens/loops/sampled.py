"""Constructors for closed polygonal loops."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from numpy.typing import ArrayLike

from spirallens.contracts import LoopOrientation, SampledLoop


def _coerce_orientation(value: LoopOrientation | str) -> LoopOrientation:
    try:
        return value if isinstance(value, LoopOrientation) else LoopOrientation(value)
    except ValueError as exc:
        valid = ", ".join(item.value for item in LoopOrientation)
        raise ValueError(f"orientation must be one of: {valid}") from exc


def circle_loop(
    *,
    center: tuple[float, float] = (0.0, 0.0),
    radius: float = 1.0,
    samples: int = 256,
    orientation: LoopOrientation | str = LoopOrientation.COUNTERCLOCKWISE,
    starting_angle_rad: float = 0.0,
    name: str | None = None,
) -> SampledLoop:
    """Return a uniformly sampled planar circle without a duplicate endpoint."""

    if not np.isfinite(radius) or radius <= 0:
        raise ValueError("radius must be finite and positive")
    if samples < 3:
        raise ValueError("samples must be at least three")
    center_array = np.asarray(center, dtype=float)
    if center_array.shape != (2,) or not np.all(np.isfinite(center_array)):
        raise ValueError("center must contain two finite coordinates")
    if not np.isfinite(starting_angle_rad):
        raise ValueError("starting_angle_rad must be finite")

    declared_orientation = _coerce_orientation(orientation)
    parameter = np.arange(samples, dtype=float) / samples
    angles = (
        starting_angle_rad
        + declared_orientation.sign * 2.0 * np.pi * parameter
    )
    points = center_array + radius * np.column_stack(
        (np.cos(angles), np.sin(angles))
    )
    loop_name = name or f"circle_r{radius:g}_{declared_orientation.value}"
    return SampledLoop(
        points=points,
        name=loop_name,
        parameter_values=parameter,
        metadata={
            "constructor": "circle_loop",
            "center": tuple(float(item) for item in center_array),
            "radius": float(radius),
            "orientation": declared_orientation.value,
            "starting_angle_rad": float(starting_angle_rad),
        },
    )


def reverse_loop(loop: SampledLoop, *, name: str | None = None) -> SampledLoop:
    """Reverse traversal while retaining the original starting vertex."""

    indices = np.concatenate(
        ([0], np.arange(loop.vertex_count - 1, 0, -1, dtype=int))
    )
    metadata = dict(loop.metadata)
    metadata.update(
        {
            "derived_from": loop.name,
            "transformation": "reverse_orientation",
        }
    )
    return SampledLoop(
        points=loop.points[indices],
        name=name or f"{loop.name}:reversed",
        metadata=metadata,
    )


def nested_circle_loops(
    radii: Iterable[float],
    *,
    center: tuple[float, float] = (0.0, 0.0),
    samples: int = 256,
    orientation: LoopOrientation | str = LoopOrientation.COUNTERCLOCKWISE,
    name_prefix: str = "nested",
) -> tuple[SampledLoop, ...]:
    """Construct a preregistered family of concentric circular loops."""

    radius_values = tuple(float(radius) for radius in radii)
    if not radius_values:
        raise ValueError("radii must not be empty")
    if len(set(radius_values)) != len(radius_values):
        raise ValueError("radii must be unique")
    return tuple(
        circle_loop(
            center=center,
            radius=radius,
            samples=samples,
            orientation=orientation,
            name=f"{name_prefix}:r={radius:g}",
        )
        for radius in radius_values
    )


def affine_transform_loop(
    loop: SampledLoop,
    linear_map: ArrayLike,
    *,
    offset: ArrayLike | None = None,
    name: str | None = None,
) -> SampledLoop:
    """Apply an invertible affine map without projecting the loop."""

    matrix = np.asarray(linear_map, dtype=float)
    dimension = loop.ambient_dimension
    if matrix.shape != (dimension, dimension):
        raise ValueError(
            f"linear_map must have shape {(dimension, dimension)}, got {matrix.shape}"
        )
    if not np.all(np.isfinite(matrix)):
        raise ValueError("linear_map must contain only finite values")
    if abs(float(np.linalg.det(matrix))) <= np.finfo(float).eps:
        raise ValueError("linear_map must be invertible")
    translation = (
        np.zeros(dimension, dtype=float)
        if offset is None
        else np.asarray(offset, dtype=float)
    )
    if translation.shape != (dimension,) or not np.all(np.isfinite(translation)):
        raise ValueError(f"offset must contain {dimension} finite values")

    transformed = loop.points @ matrix.T + translation
    metadata = dict(loop.metadata)
    metadata.update(
        {
            "derived_from": loop.name,
            "transformation": "affine",
            "linear_map": matrix.tolist(),
            "offset": translation.tolist(),
        }
    )
    return SampledLoop(
        points=transformed,
        name=name or f"{loop.name}:affine",
        parameter_values=loop.parameter_values,
        metadata=metadata,
    )


def signed_area_2d(loop: SampledLoop) -> float:
    """Return the shoelace signed area of a planar loop."""

    if loop.ambient_dimension != 2:
        raise ValueError("signed_area_2d requires a planar loop")
    x = loop.points[:, 0]
    y = loop.points[:, 1]
    return float(0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1)))
