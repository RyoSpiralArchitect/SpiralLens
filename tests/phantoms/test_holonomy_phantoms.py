from __future__ import annotations

import numpy as np
import pytest

from spirallens.calibration import (
    basis_rotation_frames,
    injected_rotation_edge_transports,
    radial_scale_frames,
    rotation_matrix_2d,
    shear_frames,
    so2_vortex_connection,
    stretch_frames,
)
from spirallens.contracts import ContinuousHolonomy
from spirallens.holonomy import (
    compose_edge_transports,
    gauge_transform_edge_transports,
    integrate_matrix_connection,
    principal_rotation_angle_2d,
    pure_gauge_edge_transports,
    relative_holonomy,
    reverse_edge_transports,
)
from spirallens.loops import circle_loop, nested_circle_loops, reverse_loop


def test_known_continuous_rotation_and_reverse() -> None:
    loop = circle_loop(samples=96)
    edge_maps = injected_rotation_edge_transports(loop, 0.8)

    forward = compose_edge_transports(edge_maps)
    reverse = compose_edge_transports(reverse_edge_transports(edge_maps))

    assert isinstance(forward, ContinuousHolonomy)
    assert principal_rotation_angle_2d(forward) == pytest.approx(0.8, abs=1e-12)
    assert principal_rotation_angle_2d(reverse) == pytest.approx(-0.8, abs=1e-12)
    assert reverse.matrix @ forward.matrix == pytest.approx(np.eye(2), abs=1e-12)


@pytest.mark.parametrize(
    "frame_factory",
    [stretch_frames, radial_scale_frames, shear_frames, basis_rotation_frames],
)
def test_frame_deformations_are_pure_gauge_holonomy_nulls(frame_factory) -> None:
    loop = circle_loop(samples=128)
    frames = frame_factory(loop.points)

    holonomy = compose_edge_transports(pure_gauge_edge_transports(frames))

    assert holonomy.identity_deviation_fro < 2e-12


def test_local_basis_change_conjugates_holonomy() -> None:
    loop = circle_loop(samples=96)
    edge_maps = injected_rotation_edge_transports(loop, 0.61)
    gauges = radial_scale_frames(loop.points, strength=0.35) @ basis_rotation_frames(
        loop.points, turns=1
    )

    original = compose_edge_transports(edge_maps)
    transformed = compose_edge_transports(
        gauge_transform_edge_transports(edge_maps, gauges)
    )
    expected = np.linalg.solve(gauges[0], original.matrix @ gauges[0])

    assert transformed.matrix == pytest.approx(expected, abs=2e-12)
    assert np.sort_complex(np.linalg.eigvals(transformed.matrix)) == pytest.approx(
        np.sort_complex(np.linalg.eigvals(original.matrix)), abs=2e-12
    )


def test_relative_holonomy_is_baseline_inverse_times_full() -> None:
    loop = circle_loop(samples=64)
    baseline = compose_edge_transports(
        injected_rotation_edge_transports(loop, 0.2),
        loop_name="baseline",
    )
    full = compose_edge_transports(
        injected_rotation_edge_transports(loop, 0.75),
        loop_name="full",
    )

    relative = relative_holonomy(full, baseline)

    assert principal_rotation_angle_2d(relative) == pytest.approx(0.55, abs=1e-12)


def test_connection_nested_radii_reverse_and_off_core() -> None:
    connection = so2_vortex_connection(0.2)
    nested = nested_circle_loops((0.3, 0.7, 1.4), samples=512)

    angles = [
        principal_rotation_angle_2d(
            integrate_matrix_connection(loop, connection)
        )
        for loop in nested
    ]
    reverse_angle = principal_rotation_angle_2d(
        integrate_matrix_connection(reverse_loop(nested[1]), connection)
    )
    off_core = circle_loop(center=(2.0, 0.0), radius=0.4, samples=512)
    off_core_angle = principal_rotation_angle_2d(
        integrate_matrix_connection(off_core, connection)
    )

    assert angles == pytest.approx([0.4 * np.pi] * 3, abs=4e-5)
    assert reverse_angle == pytest.approx(-0.4 * np.pi, abs=4e-5)
    assert off_core_angle == pytest.approx(0.0, abs=2e-6)


def test_principal_rotation_uses_polar_factor_not_shear_eigenvalues() -> None:
    shear = np.array([[1.0, 1.2], [0.0, 1.0]])
    angle = principal_rotation_angle_2d(shear)

    assert angle != pytest.approx(0.0)
    assert np.linalg.eigvals(shear) == pytest.approx([1.0, 1.0])


def test_rotation_matrix_rejects_nonfinite_angle() -> None:
    with pytest.raises(ValueError):
        rotation_matrix_2d(float("nan"))
