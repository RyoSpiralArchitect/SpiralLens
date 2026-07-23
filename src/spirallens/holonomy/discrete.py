"""Path-ordered composition of discrete linear transport maps."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
from numpy.typing import ArrayLike, NDArray

from spirallens.contracts import ContinuousHolonomy


def _validate_matrix_stack(
    values: ArrayLike,
    *,
    name: str,
    minimum_count: int = 1,
) -> NDArray[np.generic]:
    matrices = np.asarray(values)
    if matrices.ndim != 3:
        raise ValueError(f"{name} must have shape (count, fiber, fiber)")
    if matrices.shape[0] < minimum_count:
        raise ValueError(f"{name} must contain at least {minimum_count} matrices")
    if matrices.shape[1] == 0 or matrices.shape[1] != matrices.shape[2]:
        raise ValueError(f"{name} matrices must be non-empty and square")
    if not np.issubdtype(matrices.dtype, np.number):
        raise TypeError(f"{name} must be numeric")
    if not np.all(np.isfinite(matrices)):
        raise ValueError(f"{name} must contain only finite values")
    return matrices


def compose_edge_transports(
    edge_transports: ArrayLike,
    *,
    loop_name: str = "loop",
    metadata: Mapping[str, Any] | None = None,
) -> ContinuousHolonomy:
    """Compose edge maps in column-vector, left-path-ordered convention."""

    transports = _validate_matrix_stack(
        edge_transports, name="edge_transports"
    )
    dtype = np.result_type(transports.dtype, np.float64)
    holonomy = np.eye(transports.shape[1], dtype=dtype)
    for edge_transport in transports:
        holonomy = edge_transport @ holonomy
    return ContinuousHolonomy(
        matrix=holonomy,
        edge_count=int(transports.shape[0]),
        loop_name=loop_name,
        metadata={} if metadata is None else metadata,
    )


def reverse_edge_transports(edge_transports: ArrayLike) -> NDArray[np.generic]:
    """Return maps for the same loop traversed in reverse from the same basepoint."""

    transports = _validate_matrix_stack(
        edge_transports, name="edge_transports"
    )
    reversed_transports = [np.linalg.inv(matrix) for matrix in transports[::-1]]
    return np.stack(reversed_transports)


def relative_holonomy(
    full: ContinuousHolonomy,
    baseline: ContinuousHolonomy,
    *,
    loop_name: str | None = None,
) -> ContinuousHolonomy:
    """Compute the calibrated residual ``H_baseline^{-1} H_full``.

    The result is still a continuous transport residual. It is not relabelled
    as semantic and it is not an integer winding.
    """

    if full.fiber_dimension != baseline.fiber_dimension:
        raise ValueError("full and baseline holonomies need equal fiber dimension")
    matrix = np.linalg.solve(baseline.matrix, full.matrix)
    return ContinuousHolonomy(
        matrix=matrix,
        edge_count=full.edge_count,
        loop_name=loop_name or f"{full.loop_name}:relative_to:{baseline.loop_name}",
        metadata={
            "operation": "baseline_inverse_times_full",
            "full_loop_name": full.loop_name,
            "baseline_loop_name": baseline.loop_name,
        },
    )


def pure_gauge_edge_transports(frames: ArrayLike) -> NDArray[np.generic]:
    """Build telescoping edge maps from a single-valued frame at every vertex.

    For vertex frames ``F_i`` this returns ``F_{i+1} F_i^{-1}``, including the
    closing edge. Local stretch, radial scaling, shear, or basis rotation may be
    large while the exact closed-loop holonomy remains identity.
    """

    frame_stack = _validate_matrix_stack(frames, name="frames", minimum_count=3)
    transports: list[NDArray[np.generic]] = []
    for index, frame in enumerate(frame_stack):
        next_frame = frame_stack[(index + 1) % frame_stack.shape[0]]
        transports.append(next_frame @ np.linalg.inv(frame))
    return np.stack(transports)


def gauge_transform_edge_transports(
    edge_transports: ArrayLike,
    gauges: ArrayLike,
) -> NDArray[np.generic]:
    """Change the local basis at every vertex.

    With fiber coordinates ``v'_i = G_i^{-1} v_i``, each edge transforms as
    ``T'_i = G_{i+1}^{-1} T_i G_i`` and closed-loop holonomy is conjugated by
    the basepoint gauge.
    """

    transports = _validate_matrix_stack(
        edge_transports, name="edge_transports"
    )
    gauge_stack = _validate_matrix_stack(gauges, name="gauges")
    if transports.shape != gauge_stack.shape:
        raise ValueError("gauges must have the same shape as edge_transports")

    transformed: list[NDArray[np.generic]] = []
    for index, transport in enumerate(transports):
        current_gauge = gauge_stack[index]
        next_gauge = gauge_stack[(index + 1) % gauge_stack.shape[0]]
        transformed.append(
            np.linalg.solve(next_gauge, transport @ current_gauge)
        )
    return np.stack(transformed)
