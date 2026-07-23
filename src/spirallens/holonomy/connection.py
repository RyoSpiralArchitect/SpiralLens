"""Numerical integration of matrix-valued connections on polygonal loops."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import expm

from spirallens.contracts import ContinuousHolonomy, SampledLoop

from .discrete import compose_edge_transports

MatrixConnection = Callable[[NDArray[np.floating]], NDArray[np.generic]]


def connection_edge_transports(
    loop: SampledLoop,
    connection: MatrixConnection,
    *,
    substeps_per_edge: int = 1,
    generator_sign: float = 1.0,
) -> NDArray[np.generic]:
    """Integrate a connection along each polygon edge using midpoint steps.

    ``connection(x)`` must return an array with shape
    ``(ambient_dimension, fiber_dimension, fiber_dimension)``. The local
    generator is ``generator_sign * sum_mu A_mu(x) dx_mu``.
    """

    if substeps_per_edge < 1:
        raise ValueError("substeps_per_edge must be positive")
    if not np.isfinite(generator_sign):
        raise ValueError("generator_sign must be finite")

    edge_maps: list[NDArray[np.generic]] = []
    fiber_dimension: int | None = None
    result_dtype: np.dtype[Any] | None = None

    for edge_index, start in enumerate(loop.points):
        end = loop.points[(edge_index + 1) % loop.vertex_count]
        step = (end - start) / substeps_per_edge
        edge_map: NDArray[np.generic] | None = None
        for substep in range(substeps_per_edge):
            midpoint = start + (substep + 0.5) * step
            components = np.asarray(connection(midpoint))
            if components.ndim != 3:
                raise ValueError(
                    "connection must return (ambient, fiber, fiber) components"
                )
            if components.shape[0] != loop.ambient_dimension:
                raise ValueError(
                    "connection ambient dimension does not match the loop"
                )
            if components.shape[1] == 0 or components.shape[1] != components.shape[2]:
                raise ValueError("connection fiber matrices must be square")
            if not np.issubdtype(components.dtype, np.number):
                raise TypeError("connection components must be numeric")
            if not np.all(np.isfinite(components)):
                raise ValueError("connection components must be finite")
            if fiber_dimension is None:
                fiber_dimension = int(components.shape[1])
                result_dtype = np.result_type(components.dtype, np.float64)
                edge_map = np.eye(fiber_dimension, dtype=result_dtype)
            elif components.shape[1] != fiber_dimension:
                raise ValueError("connection fiber dimension changed along the loop")
            if edge_map is None:
                edge_map = np.eye(fiber_dimension, dtype=result_dtype)

            contracted = np.tensordot(step, components, axes=(0, 0))
            substep_map = expm(generator_sign * contracted)
            edge_map = substep_map @ edge_map
        if edge_map is None:  # pragma: no cover - guarded by substeps_per_edge
            raise RuntimeError("internal error: edge integration produced no map")
        edge_maps.append(edge_map)

    return np.stack(edge_maps)


def integrate_matrix_connection(
    loop: SampledLoop,
    connection: MatrixConnection,
    *,
    substeps_per_edge: int = 1,
    generator_sign: float = 1.0,
    metadata: Mapping[str, Any] | None = None,
) -> ContinuousHolonomy:
    """Return continuous holonomy for a matrix-valued connection."""

    transports = connection_edge_transports(
        loop,
        connection,
        substeps_per_edge=substeps_per_edge,
        generator_sign=generator_sign,
    )
    integration_metadata: dict[str, Any] = {
        "integrator": "piecewise_linear_midpoint_exponential",
        "substeps_per_edge": substeps_per_edge,
        "generator_sign": float(generator_sign),
    }
    if metadata is not None:
        integration_metadata.update(metadata)
    return compose_edge_transports(
        transports,
        loop_name=loop.name,
        metadata=integration_metadata,
    )
