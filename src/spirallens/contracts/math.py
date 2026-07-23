"""Validated value objects for loops, holonomy, and winding.

`ContinuousHolonomy` and `SampledWinding` are deliberately unrelated types.
A non-identity transport matrix is not evidence of integer winding, and an
integer-valued sampled winding can coexist with identity matrix holonomy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray


class LoopOrientation(str, Enum):
    """Declared traversal orientation for a planar loop."""

    COUNTERCLOCKWISE = "counterclockwise"
    CLOCKWISE = "clockwise"

    @property
    def sign(self) -> int:
        return 1 if self is LoopOrientation.COUNTERCLOCKWISE else -1


def _readonly_array(
    value: Any,
    *,
    ndim: int,
    name: str,
    allow_complex: bool = True,
) -> NDArray[np.generic]:
    array = np.asarray(value)
    if array.ndim != ndim:
        raise ValueError(f"{name} must have {ndim} dimensions, got {array.ndim}")
    if not allow_complex and np.iscomplexobj(array):
        raise ValueError(f"{name} must be real-valued")
    if not np.issubdtype(array.dtype, np.number):
        raise TypeError(f"{name} must be numeric")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    copy = np.array(array, copy=True)
    copy.setflags(write=False)
    return copy


def _readonly_metadata(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class SampledLoop:
    """A closed polygonal loop represented without a duplicated endpoint.

    The closing edge is implicit and runs from the final sample back to the
    first sample. Rejecting a duplicated endpoint prevents accidental zero
    edges from contaminating transport integration.
    """

    points: NDArray[np.floating]
    name: str = "loop"
    parameter_values: NDArray[np.floating] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        points = _readonly_array(
            self.points, ndim=2, name="points", allow_complex=False
        )
        if points.shape[0] < 3:
            raise ValueError("a sampled loop requires at least three vertices")
        if points.shape[1] < 2:
            raise ValueError("a sampled loop requires ambient dimension >= 2")
        if not self.name.strip():
            raise ValueError("loop name must not be empty")

        closed_edges = np.roll(points, -1, axis=0) - points
        scale = max(1.0, float(np.max(np.linalg.norm(points, axis=1))))
        if np.any(np.linalg.norm(closed_edges, axis=1) <= 1e-14 * scale):
            raise ValueError(
                "loop contains a zero-length edge; do not duplicate the endpoint"
            )

        if self.parameter_values is None:
            parameter_values = np.arange(points.shape[0], dtype=float) / points.shape[0]
        else:
            parameter_values = _readonly_array(
                self.parameter_values,
                ndim=1,
                name="parameter_values",
                allow_complex=False,
            )
            if parameter_values.shape != (points.shape[0],):
                raise ValueError(
                    "parameter_values must contain one value per loop vertex"
                )
            if np.any(np.diff(parameter_values) <= 0):
                raise ValueError("parameter_values must be strictly increasing")

        object.__setattr__(self, "points", points)
        object.__setattr__(self, "parameter_values", parameter_values)
        object.__setattr__(self, "metadata", _readonly_metadata(self.metadata))

    @property
    def vertex_count(self) -> int:
        return int(self.points.shape[0])

    @property
    def ambient_dimension(self) -> int:
        return int(self.points.shape[1])

    @property
    def edge_vectors(self) -> NDArray[np.floating]:
        return np.roll(self.points, -1, axis=0) - self.points

    @property
    def perimeter(self) -> float:
        return float(np.linalg.norm(self.edge_vectors, axis=1).sum())


@dataclass(frozen=True, slots=True)
class ContinuousHolonomy:
    """A continuous closed-loop transport result.

    Matrices act on column vectors. If edge map ``T_i`` transports vertex
    ``i`` to ``i+1``, the stored matrix is ``T_{n-1} ... T_1 T_0``.
    """

    matrix: NDArray[np.generic]
    edge_count: int
    loop_name: str = "loop"
    convention: str = "column_vectors:left_path_ordered"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        matrix = _readonly_array(self.matrix, ndim=2, name="matrix")
        if matrix.shape[0] != matrix.shape[1] or matrix.shape[0] == 0:
            raise ValueError("holonomy matrix must be non-empty and square")
        if self.edge_count < 1:
            raise ValueError("edge_count must be positive")
        if not self.loop_name.strip():
            raise ValueError("loop_name must not be empty")
        if not self.convention.strip():
            raise ValueError("convention must not be empty")
        object.__setattr__(self, "matrix", matrix)
        object.__setattr__(self, "metadata", _readonly_metadata(self.metadata))

    @property
    def fiber_dimension(self) -> int:
        return int(self.matrix.shape[0])

    @property
    def identity_deviation_fro(self) -> float:
        identity = np.eye(self.fiber_dimension, dtype=self.matrix.dtype)
        return float(np.linalg.norm(self.matrix - identity, ord="fro"))

    @property
    def determinant(self) -> complex:
        return complex(np.linalg.det(self.matrix))


@dataclass(frozen=True, slots=True)
class WindingEstimate:
    """A branch-aware estimate that has not necessarily been certified."""

    closed_loop_angle_rad: float
    nearest_integer: int
    residual_cycles: float
    minimum_amplitude: float
    maximum_edge_angle_rad: float
    sample_count: int
    reliable: bool
    failure_reasons: tuple[str, ...] = ()
    loop_name: str = "loop"

    def __post_init__(self) -> None:
        numeric_values = (
            self.closed_loop_angle_rad,
            self.residual_cycles,
            self.minimum_amplitude,
            self.maximum_edge_angle_rad,
        )
        if not all(np.isfinite(value) for value in numeric_values):
            raise ValueError("winding diagnostics must be finite")
        if self.sample_count < 3:
            raise ValueError("sample_count must be at least three")
        if self.minimum_amplitude < 0:
            raise ValueError("minimum_amplitude must be non-negative")
        if self.maximum_edge_angle_rad < 0:
            raise ValueError("maximum_edge_angle_rad must be non-negative")
        expected_residual = self.cycles - self.nearest_integer
        if not np.isclose(
            self.residual_cycles, expected_residual, atol=1e-10, rtol=1e-10
        ):
            raise ValueError("residual_cycles is inconsistent with the angle")
        if self.reliable and self.failure_reasons:
            raise ValueError("a reliable estimate cannot have failure reasons")
        if not self.reliable and not self.failure_reasons:
            raise ValueError("an unreliable estimate must explain why")

    @property
    def cycles(self) -> float:
        return float(self.closed_loop_angle_rad / (2.0 * np.pi))


@dataclass(frozen=True, slots=True)
class SampledWinding:
    """Integer-valued winding of a declared discrete loop interpolation.

    This type does not certify the winding of an unknown continuous field.
    Frequencies above the sampling resolution can alias to another charge.
    """

    charge: int
    estimate: WindingEstimate

    def __post_init__(self) -> None:
        if not self.estimate.reliable:
            raise ValueError("cannot construct SampledWinding from unreliable estimate")
        if self.charge != self.estimate.nearest_integer:
            raise ValueError("charge must match estimate.nearest_integer")

    @property
    def loop_name(self) -> str:
        return self.estimate.loop_name
