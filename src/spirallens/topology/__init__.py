"""Branch-aware winding estimation on explicitly sampled loops."""

from .winding import (
    WindingResolutionError,
    estimate_winding,
    estimate_winding_from_field,
    resolve_sampled_winding,
    sampled_winding_from_field,
)

__all__ = [
    "WindingResolutionError",
    "estimate_winding",
    "estimate_winding_from_field",
    "resolve_sampled_winding",
    "sampled_winding_from_field",
]
