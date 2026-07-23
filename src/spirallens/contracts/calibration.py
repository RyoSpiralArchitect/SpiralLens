"""Result contracts for deterministic analytic calibration."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True, slots=True)
class CalibrationCheck:
    """One scalar calibration assertion with its declared tolerance."""

    name: str
    observed: float
    expected: float
    tolerance: float
    passed: bool
    category: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.category.strip():
            raise ValueError("calibration name and category must not be empty")
        if not all(
            np.isfinite(value)
            for value in (self.observed, self.expected, self.tolerance)
        ):
            raise ValueError("calibration scalar values must be finite")
        if self.tolerance < 0:
            raise ValueError("calibration tolerance must be non-negative")
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    @property
    def absolute_error(self) -> float:
        return abs(self.observed - self.expected)


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    """Complete analytic calibration report."""

    checks: tuple[CalibrationCheck, ...]
    suite_name: str = "analytic_phantoms_v0_1"

    def __post_init__(self) -> None:
        if not self.checks:
            raise ValueError("calibration report must contain at least one check")
        if not self.suite_name.strip():
            raise ValueError("suite_name must not be empty")

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failed(self) -> tuple[CalibrationCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)

    def require_passed(self) -> None:
        if self.passed:
            return
        names = ", ".join(check.name for check in self.failed)
        raise RuntimeError(f"analytic calibration failed: {names}")
