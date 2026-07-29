"""Level-0 metamorphic laws for qualification observables.

These checks exercise transformation laws of already constructed numerical
objects.  They do not inspect oracle labels and they never turn a sampled
phase total into an integer or a topology claim.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_sha256

from .common import (
    QualificationContractError,
    QualificationState,
    array_fingerprint,
    float_matrix,
    level0_boundary,
    require_enum,
    require_finite_real,
    require_slug,
)

FloatArray = NDArray[np.float64]


class MetamorphLaw(str, Enum):
    """Closed set of transformation laws required by D3."""

    LOCAL_FRAME_GAUGE = "local_frame_gauge"
    REFERENCE_ORIENTATION = "reference_orientation"
    LOOP_REVERSAL = "loop_reversal"
    AMBIENT_SIGNED_PERMUTATION = "ambient_signed_permutation"
    SPIN_TWO_DOUBLE_ANGLE = "spin_two_double_angle"
    NONORIENTABLE_CONTROL = "nonorientable_control"


@dataclass(frozen=True, slots=True)
class MetamorphCheck:
    """One truth-free transformation-law result."""

    check_id: str
    law: MetamorphLaw
    state: QualificationState
    base_sha256: str
    transformed_sha256: str
    transformation_sha256: str
    nonidentity_verified: bool
    inverse_verified: bool
    composition_verified: bool
    observed_error: float
    tolerance: float
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        require_slug(self.check_id, label="check_id")
        require_enum(MetamorphLaw, self.law, label="law")
        require_enum(QualificationState, self.state, label="state")
        for label, value in (
            ("base_sha256", self.base_sha256),
            ("transformed_sha256", self.transformed_sha256),
            ("transformation_sha256", self.transformation_sha256),
        ):
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise QualificationContractError(
                    f"{label} must be a lowercase SHA-256 digest"
                )
        for label, value in (
            ("nonidentity_verified", self.nonidentity_verified),
            ("inverse_verified", self.inverse_verified),
            ("composition_verified", self.composition_verified),
        ):
            if type(value) is not bool:
                raise QualificationContractError(f"{label} must be boolean")
        require_finite_real(
            self.observed_error,
            label="observed_error",
            minimum=0.0,
        )
        require_finite_real(
            self.tolerance,
            label="tolerance",
            minimum=0.0,
        )
        if not self.reason_codes:
            raise QualificationContractError("reason_codes must be nonempty")
        for index, reason in enumerate(self.reason_codes):
            require_slug(reason, label=f"reason_codes[{index}]")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise QualificationContractError("reason_codes must be unique")
        if self.reason_codes != tuple(sorted(self.reason_codes)):
            raise QualificationContractError("reason_codes must be in canonical order")
        if self.state is QualificationState.PASS and (
            not self.nonidentity_verified
            or not self.inverse_verified
            or not self.composition_verified
            or self.observed_error > self.tolerance
        ):
            raise QualificationContractError(
                "passing metamorphs require nonidentity, inverse, composition, "
                "and tolerance checks"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "spirallens.metamorph-check.v0.1",
            **level0_boundary(),
            "check_id": self.check_id,
            "law": self.law.value,
            "state": self.state.value,
            "base_sha256": self.base_sha256,
            "transformed_sha256": self.transformed_sha256,
            "transformation_sha256": self.transformation_sha256,
            "nonidentity_verified": self.nonidentity_verified,
            "inverse_verified": self.inverse_verified,
            "composition_verified": self.composition_verified,
            "observed_error": self.observed_error,
            "tolerance": self.tolerance,
            "reason_codes": list(self.reason_codes),
            "sampled_continuous_observable_only": True,
            "integer_output_present": False,
            "oracle_read": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _float_tensor(
    value: object,
    *,
    label: str,
    ndim: int,
) -> FloatArray:
    source = np.asarray(value)
    if source.ndim != ndim or source.dtype.kind != "f":
        raise QualificationContractError(
            f"{label} must be a rank-{ndim} floating array"
        )
    result = np.array(source, dtype="<f8", order="C", copy=True)
    if not np.all(np.isfinite(result)):
        raise QualificationContractError(f"{label} must contain only finite values")
    result[result == 0.0] = 0.0
    return result


def _orthogonal(
    value: object,
    *,
    label: str,
    size: int | None = None,
    tolerance: float,
) -> FloatArray:
    source = np.asarray(value)
    if source.ndim != 2:
        raise QualificationContractError(
            f"{label} must be a two-dimensional float array"
        )
    matrix = float_matrix(value, label=label, width=source.shape[1])
    if matrix.shape[0] != matrix.shape[1]:
        raise QualificationContractError(f"{label} must be square")
    if size is not None and matrix.shape != (size, size):
        raise QualificationContractError(f"{label} must have shape ({size}, {size})")
    if not np.allclose(
        matrix.T @ matrix,
        np.eye(matrix.shape[0]),
        rtol=0.0,
        atol=tolerance,
    ):
        raise QualificationContractError(f"{label} must be orthogonal")
    return np.asarray(matrix)


def _digest_array(value: FloatArray) -> str:
    return canonical_json_sha256(array_fingerprint(np.asarray(value)))


def _digest_transform(value: FloatArray) -> str:
    return canonical_json_sha256(
        {
            "domain_version": "spirallens.metamorph-transform.v0.1",
            "array": array_fingerprint(np.asarray(value)),
        }
    )


def _maximum_error(left: FloatArray, right: FloatArray) -> float:
    if left.shape != right.shape:
        raise QualificationContractError(
            "metamorphic comparison arrays must have identical shapes"
        )
    if left.size == 0:
        return 0.0
    return float(np.max(np.abs(left - right)))


def _pass_or_fail(
    *,
    check_id: str,
    law: MetamorphLaw,
    base: FloatArray,
    transformed: FloatArray,
    transformation: FloatArray,
    observed_error: float,
    tolerance: float,
    nonidentity: bool,
    inverse: bool,
    composition: bool,
    pass_reason: str,
    fail_reason: str,
) -> MetamorphCheck:
    passed = nonidentity and inverse and composition and observed_error <= tolerance
    return MetamorphCheck(
        check_id=check_id,
        law=law,
        state=QualificationState.PASS if passed else QualificationState.FAIL,
        base_sha256=_digest_array(base),
        transformed_sha256=_digest_array(transformed),
        transformation_sha256=_digest_transform(transformation),
        nonidentity_verified=nonidentity,
        inverse_verified=inverse,
        composition_verified=composition,
        observed_error=observed_error,
        tolerance=tolerance,
        reason_codes=(pass_reason if passed else fail_reason,),
    )


def local_frame_gauge_check(
    *,
    local_frames: object,
    local_coordinates: object,
    gauges: object,
    tolerance: object = 1e-11,
) -> MetamorphCheck:
    """Verify ``(U_i G_i)(G_i.T z_i) == U_i z_i`` vertex by vertex."""

    frames = _float_tensor(local_frames, label="local_frames", ndim=3)
    coordinates = _float_tensor(
        local_coordinates,
        label="local_coordinates",
        ndim=2,
    )
    transforms = _float_tensor(gauges, label="gauges", ndim=3)
    threshold = require_finite_real(
        tolerance,
        label="tolerance",
        minimum=0.0,
    )
    if frames.shape[0] == 0 or frames.shape[2] != 2:
        raise QualificationContractError(
            "local_frames must have shape (rows, dimensions, 2)"
        )
    if coordinates.shape != (frames.shape[0], 2):
        raise QualificationContractError("local_coordinates must have shape (rows, 2)")
    if transforms.shape != (frames.shape[0], 2, 2):
        raise QualificationContractError("gauges must have shape (rows, 2, 2)")
    for row, transform in enumerate(transforms):
        _orthogonal(
            transform,
            label=f"gauges[{row}]",
            size=2,
            tolerance=max(threshold, 1e-13),
        )

    base = np.einsum("ndi,ni->nd", frames, coordinates, optimize=False)
    transformed_frames = np.einsum(
        "ndi,nij->ndj",
        frames,
        transforms,
        optimize=False,
    )
    transformed_coordinates = np.einsum(
        "nji,nj->ni",
        transforms,
        coordinates,
        optimize=False,
    )
    transformed = np.einsum(
        "ndi,ni->nd",
        transformed_frames,
        transformed_coordinates,
        optimize=False,
    )
    recovered_frames = np.einsum(
        "ndi,nji->ndj",
        transformed_frames,
        transforms,
        optimize=False,
    )
    recovered_coordinates = np.einsum(
        "nij,nj->ni",
        transforms,
        transformed_coordinates,
        optimize=False,
    )
    composed = np.einsum(
        "nij,njk->nik",
        transforms,
        np.swapaxes(transforms, 1, 2),
        optimize=False,
    )
    identity = np.broadcast_to(np.eye(2), composed.shape)
    error = max(
        _maximum_error(base, transformed),
        _maximum_error(frames, recovered_frames),
        _maximum_error(coordinates, recovered_coordinates),
        _maximum_error(composed, identity),
    )
    return _pass_or_fail(
        check_id="local-frame-gauge-law",
        law=MetamorphLaw.LOCAL_FRAME_GAUGE,
        base=base,
        transformed=transformed,
        transformation=transforms.reshape(transforms.shape[0], 4),
        observed_error=error,
        tolerance=threshold,
        nonidentity=not np.allclose(
            transforms,
            identity,
            rtol=0.0,
            atol=max(threshold, 1e-15),
        ),
        inverse=True,
        composition=True,
        pass_reason="local-frame-gauge-cancelled",
        fail_reason="local-frame-gauge-law-violated",
    )


def sampled_phase_total(section_values: object, loop_rows: object) -> float:
    """Return an unrounded signed phase total in cycles on one sampled loop."""

    values = _float_tensor(section_values, label="section_values", ndim=2)
    indices = np.asarray(loop_rows)
    if (
        values.shape[1] != 2
        or indices.ndim != 1
        or indices.dtype.kind not in {"i", "u"}
        or indices.shape[0] < 3
    ):
        raise QualificationContractError(
            "section_values must have width 2 and loop_rows must contain "
            "at least three integer rows"
        )
    normalized = np.asarray(indices, dtype=np.int64)
    if np.any(normalized < 0) or np.any(normalized >= values.shape[0]):
        raise QualificationContractError("loop_rows contains an out-of-range row")
    if len(set(normalized.tolist())) != normalized.shape[0]:
        raise QualificationContractError("loop_rows must not repeat a row")
    selected = values[normalized]
    amplitudes = np.linalg.norm(selected, axis=1)
    if np.any(amplitudes == 0.0):
        raise QualificationContractError("sampled phase is undefined at zero amplitude")
    unit = selected / amplitudes[:, None]
    following = np.roll(unit, -1, axis=0)
    cross = unit[:, 0] * following[:, 1] - unit[:, 1] * following[:, 0]
    dot = np.einsum("ni,ni->n", unit, following, optimize=False)
    increments = np.arctan2(cross, dot)
    return float(math.fsum(increments.tolist()) / (2.0 * math.pi))


def reference_orientation_check(
    *,
    section_values: object,
    loop_rows: object,
    reference_transform: object,
    tolerance: object = 1e-11,
) -> MetamorphCheck:
    """Verify the O(2) reference-frame law, including reflection sign."""

    values = _float_tensor(section_values, label="section_values", ndim=2)
    if values.shape[1] != 2:
        raise QualificationContractError("section_values must have width 2")
    threshold = require_finite_real(
        tolerance,
        label="tolerance",
        minimum=0.0,
    )
    transform = _orthogonal(
        reference_transform,
        label="reference_transform",
        size=2,
        tolerance=max(threshold, 1e-13),
    )
    transformed = values @ transform
    base_total = sampled_phase_total(values, loop_rows)
    transformed_total = sampled_phase_total(transformed, loop_rows)
    determinant = float(np.linalg.det(transform))
    expected_total = (1.0 if determinant > 0.0 else -1.0) * base_total
    recovered = transformed @ transform.T
    composed = transform @ transform.T
    error = max(
        abs(transformed_total - expected_total),
        _maximum_error(values, recovered),
        _maximum_error(composed, np.eye(2)),
    )
    return _pass_or_fail(
        check_id="reference-orientation-law",
        law=MetamorphLaw.REFERENCE_ORIENTATION,
        base=values,
        transformed=transformed,
        transformation=transform,
        observed_error=error,
        tolerance=threshold,
        nonidentity=not np.allclose(
            transform,
            np.eye(2),
            rtol=0.0,
            atol=max(threshold, 1e-15),
        ),
        inverse=True,
        composition=True,
        pass_reason="reference-orientation-law-satisfied",
        fail_reason="reference-orientation-law-violated",
    )


def loop_reversal_check(
    *,
    section_values: object,
    loop_rows: object,
    tolerance: object = 1e-11,
) -> MetamorphCheck:
    """Verify sign reversal and double-reversal identity of a sampled loop."""

    values = _float_tensor(section_values, label="section_values", ndim=2)
    indices = np.asarray(loop_rows)
    if indices.ndim != 1 or indices.dtype.kind not in {"i", "u"}:
        raise QualificationContractError("loop_rows must be an integer vector")
    normalized = np.asarray(indices, dtype=np.int64)
    forward = sampled_phase_total(values, normalized)
    reversed_rows = normalized[::-1]
    reverse = sampled_phase_total(values, reversed_rows)
    double_reversed = reversed_rows[::-1]
    error = max(
        abs(reverse + forward),
        float(np.max(np.abs(double_reversed - normalized))),
    )
    transform = np.column_stack(
        (
            normalized.astype("<f8"),
            reversed_rows.astype("<f8"),
        )
    )
    return _pass_or_fail(
        check_id="loop-reversal-law",
        law=MetamorphLaw.LOOP_REVERSAL,
        base=np.asarray(values),
        transformed=np.asarray(values[reversed_rows]),
        transformation=transform,
        observed_error=error,
        tolerance=require_finite_real(
            tolerance,
            label="tolerance",
            minimum=0.0,
        ),
        nonidentity=not np.array_equal(normalized, reversed_rows),
        inverse=np.array_equal(double_reversed, normalized),
        composition=np.array_equal(double_reversed, normalized),
        pass_reason="loop-reversal-sign-satisfied",
        fail_reason="loop-reversal-law-violated",
    )


def ambient_signed_permutation_check(
    *,
    states: object,
    local_frames: object,
    signed_permutation: object,
    tolerance: object = 1e-11,
) -> MetamorphCheck:
    """Verify ambient distance and projector covariance under one signed permutation."""

    values = _float_tensor(states, label="states", ndim=2)
    frames = _float_tensor(local_frames, label="local_frames", ndim=3)
    threshold = require_finite_real(
        tolerance,
        label="tolerance",
        minimum=0.0,
    )
    if values.shape[0] == 0 or frames.shape != (
        values.shape[0],
        values.shape[1],
        2,
    ):
        raise QualificationContractError(
            "local_frames must have shape (rows, dimensions, 2)"
        )
    transform = _orthogonal(
        signed_permutation,
        label="signed_permutation",
        size=values.shape[1],
        tolerance=max(threshold, 1e-13),
    )
    row_counts = np.sum(np.abs(transform) > max(threshold, 1e-13), axis=1)
    column_counts = np.sum(
        np.abs(transform) > max(threshold, 1e-13),
        axis=0,
    )
    nonzero = np.abs(transform[np.abs(transform) > max(threshold, 1e-13)])
    if (
        not np.all(row_counts == 1)
        or not np.all(column_counts == 1)
        or not np.allclose(nonzero, 1.0, rtol=0.0, atol=threshold)
    ):
        raise QualificationContractError(
            "signed_permutation must contain one signed unit entry per row and column"
        )
    transformed = values @ transform
    base_gram = values @ values.T
    transformed_gram = transformed @ transformed.T
    projectors = np.einsum("ndi,nei->nde", frames, frames, optimize=False)
    transformed_frames = np.einsum(
        "de,nei->ndi",
        transform.T,
        frames,
        optimize=False,
    )
    transformed_projectors = np.einsum(
        "ndi,nei->nde",
        transformed_frames,
        transformed_frames,
        optimize=False,
    )
    expected_projectors = np.einsum(
        "ab,nbc,cd->nad",
        transform.T,
        projectors,
        transform,
        optimize=False,
    )
    recovered = transformed @ transform.T
    error = max(
        _maximum_error(base_gram, transformed_gram),
        _maximum_error(transformed_projectors, expected_projectors),
        _maximum_error(values, recovered),
    )
    return _pass_or_fail(
        check_id="ambient-signed-permutation-law",
        law=MetamorphLaw.AMBIENT_SIGNED_PERMUTATION,
        base=values,
        transformed=transformed,
        transformation=transform,
        observed_error=error,
        tolerance=threshold,
        nonidentity=not np.array_equal(transform, np.eye(transform.shape[0])),
        inverse=True,
        composition=True,
        pass_reason="ambient-signed-permutation-law-satisfied",
        fail_reason="ambient-signed-permutation-law-violated",
    )


def spin_two_double_angle_check(
    *,
    spin_two_values: object,
    physical_angle: object,
    tolerance: object = 1e-11,
) -> MetamorphCheck:
    """Verify that a spin-two vector rotates through twice the physical angle."""

    values = _float_tensor(
        spin_two_values,
        label="spin_two_values",
        ndim=2,
    )
    if values.shape[0] == 0 or values.shape[1] != 2:
        raise QualificationContractError("spin_two_values must have shape (rows, 2)")
    angle = require_finite_real(physical_angle, label="physical_angle")
    threshold = require_finite_real(
        tolerance,
        label="tolerance",
        minimum=0.0,
    )
    if abs(math.remainder(angle, math.pi)) <= max(threshold, 1e-15):
        raise QualificationContractError(
            "physical_angle must induce a nonidentity spin-two transform"
        )

    def rotation(theta: float) -> FloatArray:
        return np.asarray(
            (
                (math.cos(theta), -math.sin(theta)),
                (math.sin(theta), math.cos(theta)),
            ),
            dtype="<f8",
        )

    transform = rotation(2.0 * angle)
    inverse_transform = rotation(-2.0 * angle)
    half_transform = rotation(angle)
    transformed = values @ transform.T
    recovered = transformed @ inverse_transform.T
    composed = half_transform @ half_transform
    error = max(
        _maximum_error(values, recovered),
        _maximum_error(transform, composed),
    )
    return _pass_or_fail(
        check_id="spin-two-double-angle-law",
        law=MetamorphLaw.SPIN_TWO_DOUBLE_ANGLE,
        base=values,
        transformed=transformed,
        transformation=transform,
        observed_error=error,
        tolerance=threshold,
        nonidentity=not np.allclose(
            transform,
            np.eye(2),
            rtol=0.0,
            atol=max(threshold, 1e-15),
        ),
        inverse=True,
        composition=True,
        pass_reason="spin-two-double-angle-law-satisfied",
        fail_reason="spin-two-double-angle-law-violated",
    )


def nonorientable_control_check(
    *,
    edge_determinants: object,
    cycle_edge_rows: object,
) -> MetamorphCheck:
    """Mark an orientation-reversing cycle insufficient instead of forcing SO(2)."""

    determinants = _float_tensor(
        edge_determinants,
        label="edge_determinants",
        ndim=1,
    )
    rows = np.asarray(cycle_edge_rows)
    if (
        determinants.shape[0] == 0
        or rows.ndim != 1
        or rows.dtype.kind not in {"i", "u"}
        or rows.shape[0] == 0
    ):
        raise QualificationContractError(
            "cycle_edge_rows must be a nonempty integer vector"
        )
    indices = np.asarray(rows, dtype=np.int64)
    if np.any(indices < 0) or np.any(indices >= determinants.shape[0]):
        raise QualificationContractError(
            "cycle_edge_rows contains an out-of-range edge"
        )
    selected = determinants[indices]
    if np.any(np.abs(np.abs(selected) - 1.0) > 1e-12):
        raise QualificationContractError(
            "edge_determinants must be signed unit determinants"
        )
    orientation_sign = float(np.prod(selected))
    nonorientable = orientation_sign < 0.0
    return MetamorphCheck(
        check_id="nonorientable-cycle-control",
        law=MetamorphLaw.NONORIENTABLE_CONTROL,
        state=(
            QualificationState.INSUFFICIENT
            if nonorientable
            else QualificationState.FAIL
        ),
        base_sha256=_digest_array(determinants),
        transformed_sha256=_digest_array(selected),
        transformation_sha256=_digest_transform(indices.astype("<f8")[:, None]),
        nonidentity_verified=True,
        inverse_verified=True,
        composition_verified=True,
        observed_error=0.0,
        tolerance=0.0,
        reason_codes=(
            "orientation-reversing-cycle"
            if nonorientable
            else "nonorientable-control-did-not-trigger",
        ),
    )
