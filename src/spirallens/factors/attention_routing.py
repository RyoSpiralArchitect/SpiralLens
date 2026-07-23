"""Attention routing-sensitivity accounting."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def softmax_jvp(
    probabilities: ArrayLike,
    score_tangent: ArrayLike,
) -> NDArray[np.float64]:
    """Apply the softmax Jacobian along the last axis."""

    probs = np.asarray(probabilities, dtype=np.float64)
    tangent = np.asarray(score_tangent, dtype=np.float64)
    if probs.shape != tangent.shape or probs.ndim < 1:
        raise ValueError("probabilities and score_tangent must have matching shape")
    if np.any(probs < 0.0) or not np.allclose(
        np.sum(probs, axis=-1),
        1.0,
        atol=1e-8,
    ):
        raise ValueError("probabilities must be normalized along the last axis")
    centered = tangent - np.sum(probs * tangent, axis=-1, keepdims=True)
    return probs * centered


def attention_routing_jvp(
    probabilities: ArrayLike,
    score_tangent: ArrayLike,
    values: ArrayLike,
    *,
    output_projection: ArrayLike | None = None,
) -> NDArray[np.float64]:
    """Evaluate ``(dP) V W_O`` while holding value vectors fixed."""

    routing_tangent = softmax_jvp(probabilities, score_tangent)
    value_rows = np.asarray(values, dtype=np.float64)
    if routing_tangent.shape[-1] != value_rows.shape[-2]:
        raise ValueError("routing key axis and value token axis do not match")
    transported = np.matmul(routing_tangent, value_rows)
    if output_projection is None:
        return transported
    projection = np.asarray(output_projection, dtype=np.float64)
    if projection.ndim != 2 or transported.shape[-1] != projection.shape[0]:
        raise ValueError("output_projection must map the transported value width")
    return np.matmul(transported, projection)
