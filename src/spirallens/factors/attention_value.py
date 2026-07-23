"""Fixed-routing attention value-path accounting."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def attention_value_jvp(
    probabilities: ArrayLike,
    value_tangent: ArrayLike,
    *,
    output_projection: ArrayLike | None = None,
) -> NDArray[np.float64]:
    """Evaluate ``P dV W_O`` with the routing probabilities held fixed."""

    routing = np.asarray(probabilities, dtype=np.float64)
    tangent = np.asarray(value_tangent, dtype=np.float64)
    if routing.ndim < 2 or tangent.ndim < 2:
        raise ValueError("probabilities and value_tangent must be matrix-like")
    if routing.shape[-1] != tangent.shape[-2]:
        raise ValueError("attention key axis and value token axis do not match")
    transported = np.matmul(routing, tangent)
    if output_projection is None:
        return transported
    projection = np.asarray(output_projection, dtype=np.float64)
    if projection.ndim != 2 or transported.shape[-1] != projection.shape[0]:
        raise ValueError("output_projection must map the transported value width")
    return np.matmul(transported, projection)
