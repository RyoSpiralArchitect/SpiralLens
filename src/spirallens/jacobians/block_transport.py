"""Token-conditioned Jacobian blocks built from JVPs."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from spirallens.jacobians.component_jvp import finite_difference_jvp


SequenceFunction = Callable[[NDArray[np.float64]], ArrayLike]


def token_block_jacobian(
    function: SequenceFunction,
    point: ArrayLike,
    *,
    source_token: int,
    target_token: int,
    step: float | None = None,
) -> NDArray[np.float64]:
    """Construct ``d output[target] / d input[source]`` by basis JVPs.

    This is exact up to central-difference error and intentionally builds only
    the requested token block, not the full sequence Jacobian.
    """

    x = np.asarray(point, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("point must have shape (sequence, hidden)")
    sequence, hidden = x.shape
    if not 0 <= source_token < sequence or not 0 <= target_token < sequence:
        raise IndexError("source_token and target_token must index the sequence")

    columns: list[NDArray[np.float64]] = []
    for input_dimension in range(hidden):
        tangent = np.zeros_like(x)
        tangent[source_token, input_dimension] = 1.0
        image = finite_difference_jvp(function, x, tangent, step=step)
        if image.shape != x.shape:
            raise ValueError("function output must match the input sequence shape")
        columns.append(image[target_token])
    return np.stack(columns, axis=1)


def block_row_jacobian(
    function: SequenceFunction,
    point: ArrayLike,
    *,
    target_token: int,
    source_tokens: Sequence[int] | None = None,
    step: float | None = None,
) -> NDArray[np.float64]:
    """Return selected source blocks for one target as ``(sources, out, in)``."""

    x = np.asarray(point, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("point must have shape (sequence, hidden)")
    sources = tuple(range(x.shape[0])) if source_tokens is None else tuple(source_tokens)
    if not sources:
        raise ValueError("source_tokens must not be empty")
    return np.stack(
        [
            token_block_jacobian(
                function,
                x,
                source_token=source,
                target_token=target_token,
                step=step,
            )
            for source in sources
        ],
        axis=0,
    )
