from __future__ import annotations

import numpy as np
import pytest

from spirallens.calibration import complex_vortex_field, so2_vortex_connection
from spirallens.contracts import ContinuousHolonomy, SampledWinding, WindingEstimate
from spirallens.holonomy import integrate_matrix_connection
from spirallens.loops import circle_loop, nested_circle_loops, reverse_loop
from spirallens.topology import (
    estimate_winding,
    resolve_sampled_winding,
    sampled_winding_from_field,
    WindingResolutionError,
)


@pytest.mark.parametrize("charge", [-2, -1, 1, 2])
def test_known_integer_vortex_charges(charge: int) -> None:
    loop = circle_loop(radius=1.0, samples=128)
    winding = sampled_winding_from_field(loop, complex_vortex_field(charge))

    assert isinstance(winding, SampledWinding)
    assert winding.charge == charge
    assert winding.estimate.reliable


@pytest.mark.parametrize("charge", [-2, -1, 1, 2])
def test_reversing_loop_reverses_winding(charge: int) -> None:
    loop = circle_loop(radius=1.0, samples=128)
    reversed_winding = sampled_winding_from_field(
        reverse_loop(loop), complex_vortex_field(charge)
    )

    assert reversed_winding.charge == -charge


def test_off_core_loop_has_zero_winding() -> None:
    loop = circle_loop(center=(2.0, 0.0), radius=0.5, samples=128)

    winding = sampled_winding_from_field(loop, complex_vortex_field(2))

    assert winding.charge == 0


def test_nested_radii_preserve_charge() -> None:
    loops = nested_circle_loops((0.2, 0.5, 1.0, 2.0), samples=128)
    field = complex_vortex_field(-2, core_scale=0.1)

    charges = [sampled_winding_from_field(loop, field).charge for loop in loops]

    assert charges == [-2, -2, -2, -2]


def test_core_sample_fails_amplitude_gate() -> None:
    samples = np.ones(16, dtype=np.complex128)
    samples[3] = 0.0

    estimate = estimate_winding(samples)

    assert isinstance(estimate, WindingEstimate)
    assert not estimate.reliable
    assert "amplitude_at_or_below_floor" in estimate.failure_reasons
    with pytest.raises(WindingResolutionError):
        resolve_sampled_winding(estimate)


def test_branch_cut_ambiguity_fails_certification() -> None:
    # q=2 sampled at four points moves exactly pi per edge.
    angles = np.arange(4) * np.pi
    estimate = estimate_winding(np.exp(1j * angles))

    assert not estimate.reliable
    assert "branch_cut_or_undersampling_ambiguity" in estimate.failure_reasons


def test_sampled_winding_and_continuous_holonomy_remain_separate() -> None:
    loop = circle_loop(radius=1.0, samples=512)
    winding = sampled_winding_from_field(loop, complex_vortex_field(1))
    holonomy = integrate_matrix_connection(loop, so2_vortex_connection(1.0))

    assert isinstance(winding, SampledWinding)
    assert isinstance(holonomy, ContinuousHolonomy)
    assert winding.charge == 1
    # exp(2*pi*J) is identity: matrix holonomy alone loses the integer charge.
    assert holonomy.identity_deviation_fro < 2e-4


def test_high_charge_alias_is_exposed_as_sampling_dependence() -> None:
    field = complex_vortex_field(129)
    coarse = sampled_winding_from_field(
        circle_loop(radius=1.0, samples=128),
        field,
    )
    fine = sampled_winding_from_field(
        circle_loop(radius=1.0, samples=512),
        field,
    )

    # Both are valid windings of their chosen discrete principal-branch
    # interpolations, but only the finer grid resolves the analytic phantom.
    assert coarse.charge == 1
    assert fine.charge == 129
