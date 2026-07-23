"""One-call deterministic calibration of the mathematical instrument."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from spirallens.contracts import CalibrationCheck, CalibrationReport
from spirallens.holonomy import (
    compose_edge_transports,
    integrate_matrix_connection,
    principal_rotation_angle_2d,
    pure_gauge_edge_transports,
    reverse_edge_transports,
)
from spirallens.loops import circle_loop, nested_circle_loops, reverse_loop
from spirallens.topology import sampled_winding_from_field

from .phantoms import (
    basis_rotation_frames,
    complex_vortex_field,
    injected_rotation_edge_transports,
    radial_scale_frames,
    shear_frames,
    so2_vortex_connection,
    stretch_frames,
)


def _scalar_check(
    name: str,
    observed: float,
    expected: float,
    tolerance: float,
    *,
    category: str,
    details: dict[str, object] | None = None,
) -> CalibrationCheck:
    error = abs(observed - expected)
    return CalibrationCheck(
        name=name,
        observed=float(observed),
        expected=float(expected),
        tolerance=float(tolerance),
        passed=bool(error <= tolerance),
        category=category,
        details={} if details is None else details,
    )


def _extend_winding_checks(
    checks: list[CalibrationCheck],
    *,
    samples: int,
) -> None:
    centered = circle_loop(radius=1.0, samples=samples, name="vortex:centered")
    centered_reverse = reverse_loop(centered)
    for charge in (-2, -1, 1, 2):
        field = complex_vortex_field(charge)
        observed = sampled_winding_from_field(centered, field).charge
        checks.append(
            _scalar_check(
                f"winding:q={charge}",
                observed,
                charge,
                0.0,
                category="sampled_winding",
            )
        )
        reversed_observed = sampled_winding_from_field(
            centered_reverse, field
        ).charge
        checks.append(
            _scalar_check(
                f"winding:q={charge}:reverse",
                reversed_observed,
                -charge,
                0.0,
                category="orientation_reversal",
            )
        )

    off_core = circle_loop(
        center=(2.0, 0.0),
        radius=0.5,
        samples=samples,
        name="vortex:off_core",
    )
    off_core_observed = sampled_winding_from_field(
        off_core, complex_vortex_field(1)
    ).charge
    checks.append(
        _scalar_check(
            "winding:off_core",
            off_core_observed,
            0,
            0.0,
            category="off_core_control",
        )
    )

    nested = nested_circle_loops(
        (0.35, 0.75, 1.5),
        samples=samples,
        name_prefix="vortex:nested",
    )
    for loop in nested:
        observed = sampled_winding_from_field(
            loop, complex_vortex_field(2)
        ).charge
        checks.append(
            _scalar_check(
                f"winding:{loop.name}",
                observed,
                2,
                0.0,
                category="nested_radius",
            )
        )


def _extend_sampling_alias_checks(checks: list[CalibrationCheck]) -> None:
    """Pin the boundary between sampled winding and continuous-field winding."""

    field = complex_vortex_field(129)
    for sample_count, expected in ((128, 1), (512, 129)):
        loop = circle_loop(
            radius=1.0,
            samples=sample_count,
            name=f"alias:q=129:samples={sample_count}",
        )
        observed = sampled_winding_from_field(loop, field).charge
        checks.append(
            _scalar_check(
                f"winding:{loop.name}",
                observed,
                expected,
                0.0,
                category="sampling_alias_boundary",
                details={
                    "continuous_phantom_charge": 129,
                    "sample_count": sample_count,
                    "claim_scope": "sampled_loop_only",
                },
            )
        )


def _null_frame_families(
    points: np.ndarray,
) -> Iterable[tuple[str, np.ndarray]]:
    yield "stretch", stretch_frames(points)
    yield "radial_scale", radial_scale_frames(points)
    yield "non_normal_shear", shear_frames(points)
    yield "basis_rotation", basis_rotation_frames(points)


def _extend_holonomy_checks(
    checks: list[CalibrationCheck],
    *,
    samples: int,
) -> None:
    loop = circle_loop(radius=1.0, samples=samples, name="transport:centered")
    injected_angle = 0.73
    injected_edges = injected_rotation_edge_transports(loop, injected_angle)
    injected = compose_edge_transports(
        injected_edges, loop_name="transport:injected"
    )
    checks.append(
        _scalar_check(
            "holonomy:injected_rotation",
            principal_rotation_angle_2d(injected),
            injected_angle,
            1e-10,
            category="continuous_holonomy",
        )
    )
    injected_reverse = compose_edge_transports(
        reverse_edge_transports(injected_edges),
        loop_name="transport:injected:reverse",
    )
    checks.append(
        _scalar_check(
            "holonomy:injected_rotation:reverse",
            principal_rotation_angle_2d(injected_reverse),
            -injected_angle,
            1e-10,
            category="orientation_reversal",
        )
    )

    for name, frames in _null_frame_families(loop.points):
        null_holonomy = compose_edge_transports(
            pure_gauge_edge_transports(frames),
            loop_name=f"transport:null:{name}",
        )
        checks.append(
            _scalar_check(
                f"holonomy:null:{name}",
                null_holonomy.identity_deviation_fro,
                0.0,
                2e-12,
                category="pure_gauge_null",
            )
        )

    connection = so2_vortex_connection(0.25)
    for nested_loop in nested_circle_loops(
        (0.4, 0.9, 1.6),
        samples=samples,
        name_prefix="connection:nested",
    ):
        holonomy = integrate_matrix_connection(nested_loop, connection)
        checks.append(
            _scalar_check(
                f"holonomy:{nested_loop.name}",
                principal_rotation_angle_2d(holonomy),
                np.pi / 2.0,
                5e-4,
                category="nested_radius",
            )
        )

    off_core_loop = circle_loop(
        center=(2.0, 0.0),
        radius=0.5,
        samples=samples,
        name="connection:off_core",
    )
    off_core = integrate_matrix_connection(off_core_loop, connection)
    checks.append(
        _scalar_check(
            "holonomy:connection:off_core",
            principal_rotation_angle_2d(off_core),
            0.0,
            5e-5,
            category="off_core_control",
        )
    )


def run_analytic_calibration(*, samples: int = 512) -> CalibrationReport:
    """Run all model-free v0.1 phantom checks."""

    if samples < 16:
        raise ValueError("samples must be at least 16 for calibration")
    checks: list[CalibrationCheck] = []
    _extend_winding_checks(checks, samples=samples)
    _extend_sampling_alias_checks(checks)
    _extend_holonomy_checks(checks, samples=samples)
    return CalibrationReport(checks=tuple(checks))
