"""Branch-aware winding estimates on a declared sampled closed loop."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from spirallens.contracts import SampledLoop, SampledWinding, WindingEstimate

ComplexField = Callable[[NDArray[np.floating]], NDArray[np.complexfloating]]


class WindingResolutionError(ValueError):
    """Raised when a sampled estimate fails its declared resolution gates."""


def estimate_winding(
    order_parameter: ArrayLike,
    *,
    loop_name: str = "loop",
    amplitude_floor: float = 1e-8,
    residual_tolerance_cycles: float = 1e-6,
    branch_margin_rad: float = 1e-6,
) -> WindingEstimate:
    """Estimate sampled-loop winding from adjacent wrapped increments.

    Reliability is local to the supplied samples and their principal-branch
    interpolation. It is not a certificate for an unknown continuous field:
    unresolved turns between samples can alias. The local gates require:

    * no sample at or below ``amplitude_floor``;
    * no adjacent angular increment within ``branch_margin_rad`` of ``pi``;
    * a total increment within ``residual_tolerance_cycles`` of an integer.
    """

    values = np.asarray(order_parameter)
    if values.ndim != 1 or values.size < 3:
        raise ValueError("order_parameter must be a one-dimensional loop sample")
    if not np.issubdtype(values.dtype, np.number):
        raise TypeError("order_parameter must be numeric")
    if not np.all(np.isfinite(values)):
        raise ValueError("order_parameter must contain only finite values")
    if not np.isfinite(amplitude_floor) or amplitude_floor < 0:
        raise ValueError("amplitude_floor must be finite and non-negative")
    if (
        not np.isfinite(residual_tolerance_cycles)
        or residual_tolerance_cycles < 0
    ):
        raise ValueError(
            "residual_tolerance_cycles must be finite and non-negative"
        )
    if (
        not np.isfinite(branch_margin_rad)
        or branch_margin_rad <= 0
        or branch_margin_rad >= np.pi
    ):
        raise ValueError("branch_margin_rad must lie strictly between 0 and pi")

    complex_values = values.astype(np.complex128, copy=False)
    amplitudes = np.abs(complex_values)
    edge_products = np.roll(complex_values, -1) * np.conjugate(complex_values)
    edge_angles = np.angle(edge_products)
    closed_loop_angle = float(np.sum(edge_angles, dtype=np.float64))
    cycles = closed_loop_angle / (2.0 * np.pi)
    nearest_integer = int(np.rint(cycles))
    residual = float(cycles - nearest_integer)
    minimum_amplitude = float(np.min(amplitudes))
    maximum_edge_angle = float(np.max(np.abs(edge_angles)))

    reasons: list[str] = []
    if minimum_amplitude <= amplitude_floor:
        reasons.append("amplitude_at_or_below_floor")
    if maximum_edge_angle >= np.pi - branch_margin_rad:
        reasons.append("branch_cut_or_undersampling_ambiguity")
    if abs(residual) > residual_tolerance_cycles:
        reasons.append("non_integer_closed_loop_increment")

    return WindingEstimate(
        closed_loop_angle_rad=closed_loop_angle,
        nearest_integer=nearest_integer,
        residual_cycles=residual,
        minimum_amplitude=minimum_amplitude,
        maximum_edge_angle_rad=maximum_edge_angle,
        sample_count=int(values.size),
        reliable=not reasons,
        failure_reasons=tuple(reasons),
        loop_name=loop_name,
    )


def resolve_sampled_winding(estimate: WindingEstimate) -> SampledWinding:
    """Resolve a locally reliable estimate as a sampled-loop winding.

    The returned charge belongs to the chosen discrete interpolation. No
    continuous-field or band-limit claim is made.
    """

    if not estimate.reliable:
        reasons = ", ".join(estimate.failure_reasons)
        raise WindingResolutionError(
            f"cannot resolve sampled winding for {estimate.loop_name}: {reasons}"
        )
    return SampledWinding(charge=estimate.nearest_integer, estimate=estimate)


def estimate_winding_from_field(
    loop: SampledLoop,
    field: ComplexField,
    **kwargs: float,
) -> WindingEstimate:
    """Evaluate a complex field on a loop and estimate its winding."""

    values = np.asarray(field(loop.points))
    if values.shape != (loop.vertex_count,):
        raise ValueError(
            "field must return one scalar complex value per loop vertex"
        )
    return estimate_winding(values, loop_name=loop.name, **kwargs)


def sampled_winding_from_field(
    loop: SampledLoop,
    field: ComplexField,
    **kwargs: float,
) -> SampledWinding:
    """Evaluate a field and resolve winding on exactly the supplied samples."""

    return resolve_sampled_winding(
        estimate_winding_from_field(loop, field, **kwargs)
    )
