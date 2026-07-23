"""Account for fixed-value versus routing-sensitive attention JVPs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike


@dataclass(frozen=True)
class RoutingAccounting:
    full_norm: float
    fixed_routing_value_norm: float
    routing_residual_norm: float
    routing_fraction: float


def account_routing(
    full_attention_jvp: ArrayLike,
    fixed_routing_value_jvp: ArrayLike,
    *,
    epsilon: float = 1e-12,
) -> RoutingAccounting:
    """Measure the residual after the fixed-routing value path is accounted."""

    full = np.asarray(full_attention_jvp, dtype=np.float64)
    fixed = np.asarray(fixed_routing_value_jvp, dtype=np.float64)
    if full.shape != fixed.shape:
        raise ValueError("JVP arrays must have matching shapes")
    residual = full - fixed
    full_norm = float(np.linalg.norm(full))
    return RoutingAccounting(
        full_norm=full_norm,
        fixed_routing_value_norm=float(np.linalg.norm(fixed)),
        routing_residual_norm=float(np.linalg.norm(residual)),
        routing_fraction=float(np.linalg.norm(residual)) / max(full_norm, epsilon),
    )
