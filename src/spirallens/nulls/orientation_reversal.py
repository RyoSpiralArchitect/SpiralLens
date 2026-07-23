"""Closed-loop orientation reversal checks."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class OrientationCheck:
    wrapped_sum: float
    absolute_error: float
    passed: bool


def _wrap_angle(angle: float) -> float:
    return float((angle + np.pi) % (2.0 * np.pi) - np.pi)


def check_orientation_reversal(
    forward_transport_angle: float,
    reverse_transport_angle: float,
    *,
    tolerance: float = 1e-6,
) -> OrientationCheck:
    """Check that reversing a loop negates, rather than preserves, its angle."""

    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative")
    wrapped_sum = _wrap_angle(forward_transport_angle + reverse_transport_angle)
    error = abs(wrapped_sum)
    return OrientationCheck(
        wrapped_sum=wrapped_sum,
        absolute_error=error,
        passed=error <= tolerance,
    )
