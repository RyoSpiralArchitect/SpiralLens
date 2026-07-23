"""Typed contracts shared by the mathematical core.

The public types intentionally keep continuous transport observations separate
from integer-valued winding observations on sampled loops.
"""

from .calibration import CalibrationCheck, CalibrationReport
from .math import (
    ContinuousHolonomy,
    LoopOrientation,
    SampledWinding,
    SampledLoop,
    WindingEstimate,
)

__all__ = [
    "CalibrationCheck",
    "CalibrationReport",
    "ContinuousHolonomy",
    "LoopOrientation",
    "SampledLoop",
    "SampledWinding",
    "WindingEstimate",
]
