"""Analytic LayerNorm values, JVPs, and dense calibration Jacobians."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _parameters(
    width: int,
    gain: ArrayLike | None,
    bias: ArrayLike | None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    gamma = np.ones(width, dtype=np.float64) if gain is None else np.asarray(gain, dtype=np.float64)
    beta = np.zeros(width, dtype=np.float64) if bias is None else np.asarray(bias, dtype=np.float64)
    if gamma.shape != (width,) or beta.shape != (width,):
        raise ValueError("gain and bias must match the normalized width")
    return gamma, beta


def layernorm(
    value: ArrayLike,
    *,
    gain: ArrayLike | None = None,
    bias: ArrayLike | None = None,
    epsilon: float = 1e-5,
) -> NDArray[np.float64]:
    """Apply LayerNorm over the last dimension."""

    x = np.asarray(value, dtype=np.float64)
    if x.ndim < 1 or not np.all(np.isfinite(x)):
        raise ValueError("value must be a finite array with a normalized dimension")
    if epsilon <= 0.0:
        raise ValueError("epsilon must be positive")
    gamma, beta = _parameters(x.shape[-1], gain, bias)
    centered = x - np.mean(x, axis=-1, keepdims=True)
    inverse_std = 1.0 / np.sqrt(np.mean(centered**2, axis=-1, keepdims=True) + epsilon)
    return centered * inverse_std * gamma + beta


def layernorm_jvp(
    value: ArrayLike,
    tangent: ArrayLike,
    *,
    gain: ArrayLike | None = None,
    epsilon: float = 1e-5,
) -> NDArray[np.float64]:
    """Apply the analytic LayerNorm Jacobian to ``tangent``."""

    x = np.asarray(value, dtype=np.float64)
    v = np.asarray(tangent, dtype=np.float64)
    if x.shape != v.shape or x.ndim < 1:
        raise ValueError("value and tangent must have the same non-scalar shape")
    if epsilon <= 0.0:
        raise ValueError("epsilon must be positive")
    gamma, _ = _parameters(x.shape[-1], gain, None)

    centered = x - np.mean(x, axis=-1, keepdims=True)
    centered_tangent = v - np.mean(v, axis=-1, keepdims=True)
    variance_eps = np.mean(centered**2, axis=-1, keepdims=True) + epsilon
    inverse_std = 1.0 / np.sqrt(variance_eps)
    covariance_tangent = np.mean(
        centered * centered_tangent,
        axis=-1,
        keepdims=True,
    )
    normalized_tangent = (
        centered_tangent * inverse_std
        - centered * covariance_tangent * inverse_std**3
    )
    return gamma * normalized_tangent


def layernorm_jacobian(
    value: ArrayLike,
    *,
    gain: ArrayLike | None = None,
    epsilon: float = 1e-5,
) -> NDArray[np.float64]:
    """Materialize a single-vector LayerNorm Jacobian for calibration only."""

    x = np.asarray(value, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("layernorm_jacobian expects one vector")
    identity = np.eye(x.size)
    return np.stack(
        [layernorm_jvp(x, identity[column], gain=gain, epsilon=epsilon) for column in range(x.size)],
        axis=1,
    )
