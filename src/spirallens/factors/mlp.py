"""MLP-path JVPs separated from residual and normalization paths."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray


def gelu_tanh_derivative(value: ArrayLike) -> NDArray[np.float64]:
    """Derivative of the common tanh GELU approximation."""

    x = np.asarray(value, dtype=np.float64)
    coefficient = np.sqrt(2.0 / np.pi)
    inner = coefficient * (x + 0.044715 * x**3)
    tanh_inner = np.tanh(inner)
    inner_derivative = coefficient * (1.0 + 3.0 * 0.044715 * x**2)
    return 0.5 * (1.0 + tanh_inner) + 0.5 * x * (1.0 - tanh_inner**2) * inner_derivative


def mlp_jvp(
    value: ArrayLike,
    tangent: ArrayLike,
    input_weight: ArrayLike,
    output_weight: ArrayLike,
    *,
    input_bias: ArrayLike | None = None,
    activation_derivative: Callable[[ArrayLike], ArrayLike] = gelu_tanh_derivative,
) -> NDArray[np.float64]:
    """Evaluate the JVP of ``activation(x W_in + b) W_out``."""

    x = np.asarray(value, dtype=np.float64)
    v = np.asarray(tangent, dtype=np.float64)
    weight_in = np.asarray(input_weight, dtype=np.float64)
    weight_out = np.asarray(output_weight, dtype=np.float64)
    if x.shape != v.shape or x.ndim < 1:
        raise ValueError("value and tangent must have matching non-scalar shapes")
    if weight_in.ndim != 2 or weight_out.ndim != 2:
        raise ValueError("input_weight and output_weight must be matrices")
    if x.shape[-1] != weight_in.shape[0] or weight_in.shape[1] != weight_out.shape[0]:
        raise ValueError("MLP weight dimensions are inconsistent")
    preactivation = np.matmul(x, weight_in)
    if input_bias is not None:
        bias = np.asarray(input_bias, dtype=np.float64)
        if bias.shape != (weight_in.shape[1],):
            raise ValueError("input_bias must match the MLP hidden width")
        preactivation = preactivation + bias
    derivative = np.asarray(activation_derivative(preactivation), dtype=np.float64)
    if derivative.shape != preactivation.shape:
        raise ValueError("activation_derivative returned an unexpected shape")
    hidden_tangent = np.matmul(v, weight_in) * derivative
    return np.matmul(hidden_tangent, weight_out)
