"""Numeric same-object derivations for F2, F3, and F4 referents."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_bytes
from spirallens.instrument_contracts.common import HypothesisId

from .common import ReferentContractError

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
Int64Array = NDArray[np.int64]

ORTHONORMAL_ABSOLUTE_TOLERANCE = 1e-12
ORTHONORMAL_RELATIVE_TOLERANCE = 1e-12
SYMMETRY_ABSOLUTE_TOLERANCE = 1e-12
SYMMETRY_RELATIVE_TOLERANCE = 1e-12


def _immutable_array(
    value: NDArray[np.generic],
    *,
    dtype: np.dtype[object],
) -> NDArray[np.generic]:
    """Copy an array into a C layout with immutable ``bytes`` backing."""

    contiguous = np.array(value, dtype=dtype, order="C", copy=True)
    backing = contiguous.tobytes(order="C")
    return np.frombuffer(backing, dtype=dtype).reshape(contiguous.shape)


def _amplitude_floor(value: object) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise ReferentContractError("amplitude_floor must be a real number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ReferentContractError("amplitude_floor must be finite and non-negative")
    if result == 0.0 and math.copysign(1.0, result) < 0.0:
        raise ReferentContractError("amplitude_floor must not be negative zero")
    return result


def _float_array(
    value: object,
    *,
    label: str,
    ndim: int,
) -> FloatArray:
    array = np.asarray(value)
    if array.ndim != ndim:
        raise ReferentContractError(f"{label} must have {ndim} dimensions")
    if array.dtype.kind != "f":
        raise ReferentContractError(f"{label} must have a floating dtype")
    result = np.array(array, dtype="<f8", order="C", copy=True)
    if not np.all(np.isfinite(result)):
        raise ReferentContractError(f"{label} must contain only finite values")
    result[result == 0.0] = 0.0
    return _immutable_array(result, dtype=np.dtype("<f8"))


def _bool_array(value: object, *, label: str, ndim: int) -> BoolArray:
    array = np.asarray(value)
    if array.ndim != ndim or array.dtype.kind != "b":
        raise ReferentContractError(
            f"{label} must be a {ndim}-dimensional boolean array"
        )
    return _immutable_array(array, dtype=np.dtype("|b1"))


def _row_identity_vector(value: object, *, label: str) -> Int64Array:
    array = np.asarray(value)
    if array.ndim != 1 or array.shape[0] == 0:
        raise ReferentContractError(f"{label} must be a nonempty vector")
    if array.dtype.kind not in {"i", "u"}:
        raise ReferentContractError(f"{label} must have an integer dtype")
    try:
        result = np.array(array, dtype="<i8", order="C", copy=True)
    except (OverflowError, TypeError, ValueError) as error:
        raise ReferentContractError(
            f"{label} cannot be represented as int64"
        ) from error
    if not np.array_equal(result, array):
        raise ReferentContractError(f"{label} exceeds the int64 range")
    return _immutable_array(result, dtype=np.dtype("<i8"))


def _ordered_row_identity_sha256(value: Int64Array) -> str:
    descriptor = canonical_json_bytes(
        {
            "schema_version": "spirallens.ordered-row-identity.v0.1",
            "dtype": value.dtype.str,
            "shape": list(value.shape),
        }
    )
    return hashlib.sha256(descriptor + b"\x00" + value.tobytes(order="C")).hexdigest()


def _section_arrays(
    values: object,
    *,
    amplitude_floor: float,
) -> tuple[FloatArray, FloatArray, FloatArray, BoolArray]:
    section = _float_array(values, label="values", ndim=2)
    if section.shape[0] == 0 or section.shape[1] != 2:
        raise ReferentContractError("values must have shape (rows, 2)")
    amplitude = np.sqrt(np.sum(section * section, axis=1))
    defined = amplitude > amplitude_floor
    direction = np.zeros_like(section)
    np.divide(
        section,
        amplitude[:, None],
        out=direction,
        where=defined[:, None],
    )
    amplitude = np.ascontiguousarray(amplitude, dtype="<f8")
    direction = np.ascontiguousarray(direction, dtype="<f8")
    defined = np.ascontiguousarray(defined, dtype="|b1")
    amplitude[amplitude == 0.0] = 0.0
    direction[direction == 0.0] = 0.0
    return (
        section,
        _immutable_array(amplitude, dtype=np.dtype("<f8")),
        _immutable_array(direction, dtype=np.dtype("<f8")),
        _immutable_array(defined, dtype=np.dtype("|b1")),
    )


@dataclass(frozen=True, slots=True)
class SectionObservation:
    """A two-channel section and views derived from that same object."""

    hypothesis_id: HypothesisId
    input_row_identities: Int64Array
    partition: ObservationPartition | None
    values: FloatArray
    amplitude: FloatArray
    unit_direction: FloatArray
    direction_defined: BoolArray
    amplitude_floor: float

    def __post_init__(self) -> None:
        if self.hypothesis_id not in {
            HypothesisId.F2_LOCAL_COVARIANT_SECTION,
            HypothesisId.F3_GLOBAL_PLANE_SECTION,
            HypothesisId.F4_SPIN_TWO_ANISOTROPY,
        }:
            raise ReferentContractError("section observations require F2, F3, or F4")
        floor = _amplitude_floor(self.amplitude_floor)
        values, expected_amplitude, expected_direction, expected_defined = (
            _section_arrays(self.values, amplitude_floor=floor)
        )
        row_identities = _row_identity_vector(
            self.input_row_identities,
            label="input_row_identities",
        )
        if row_identities.shape[0] != values.shape[0]:
            raise ReferentContractError(
                "input_row_identities must match the section row count"
            )
        if self.hypothesis_id in {
            HypothesisId.F2_LOCAL_COVARIANT_SECTION,
            HypothesisId.F4_SPIN_TWO_ANISOTROPY,
        } and not isinstance(self.partition, ObservationPartition):
            raise ReferentContractError(
                "F2 and F4 section observations require a validated "
                "ObservationPartition"
            )
        if self.partition is not None:
            if not isinstance(self.partition, ObservationPartition):
                raise TypeError("partition must be an ObservationPartition or None")
            if not np.array_equal(
                row_identities,
                self.partition.ordered_row_identities,
            ):
                raise ReferentContractError(
                    "input row identity differs from the partition's ordered row domain"
                )
        amplitude = _float_array(
            self.amplitude,
            label="amplitude",
            ndim=1,
        )
        direction = _float_array(
            self.unit_direction,
            label="unit_direction",
            ndim=2,
        )
        defined = _bool_array(
            self.direction_defined,
            label="direction_defined",
            ndim=1,
        )
        if (
            amplitude.shape != expected_amplitude.shape
            or direction.shape != expected_direction.shape
            or defined.shape != expected_defined.shape
        ):
            raise ReferentContractError(
                "section-derived arrays do not share the row layout"
            )
        if not np.array_equal(amplitude, expected_amplitude):
            raise ReferentContractError(
                "amplitude must be the norm of the same section values"
            )
        if not np.array_equal(defined, expected_defined):
            raise ReferentContractError(
                "direction_defined differs from the frozen amplitude floor"
            )
        if not np.array_equal(direction, expected_direction):
            raise ReferentContractError(
                "unit_direction must normalize the same section values"
            )
        object.__setattr__(self, "input_row_identities", row_identities)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "amplitude", amplitude)
        object.__setattr__(self, "unit_direction", direction)
        object.__setattr__(self, "direction_defined", defined)
        object.__setattr__(self, "amplitude_floor", floor)

    @property
    def row_identity_sha256(self) -> str:
        return _ordered_row_identity_sha256(self.input_row_identities)

    @property
    def partition_canonical_sha256(self) -> str | None:
        if self.partition is None:
            return None
        return self.partition.canonical_sha256


@dataclass(frozen=True, slots=True)
class SpinTwoObservation:
    """A traceless tensor and the F4 section derived from that tensor."""

    traceless_tensor: FloatArray
    section: SectionObservation

    def __post_init__(self) -> None:
        tensor = _float_array(
            self.traceless_tensor,
            label="traceless_tensor",
            ndim=3,
        )
        if tensor.shape != (self.section.values.shape[0], 2, 2):
            raise ReferentContractError("traceless_tensor must have shape (rows, 2, 2)")
        if self.section.hypothesis_id is not HypothesisId.F4_SPIN_TWO_ANISOTROPY:
            raise ReferentContractError("spin-two sections require F4")
        if not np.allclose(
            tensor,
            np.swapaxes(tensor, 1, 2),
            rtol=SYMMETRY_RELATIVE_TOLERANCE,
            atol=SYMMETRY_ABSOLUTE_TOLERANCE,
        ):
            raise ReferentContractError("traceless_tensor must be symmetric")
        if not np.allclose(
            np.trace(tensor, axis1=1, axis2=2),
            0.0,
            rtol=0.0,
            atol=SYMMETRY_ABSOLUTE_TOLERANCE,
        ):
            raise ReferentContractError("traceless_tensor must be traceless")
        expected_values = np.column_stack(
            (
                (tensor[:, 0, 0] - tensor[:, 1, 1]) / 2.0,
                tensor[:, 0, 1],
            )
        )
        if not np.array_equal(expected_values, self.section.values):
            raise ReferentContractError(
                "F4 values must derive from the same traceless tensor"
            )
        expected_amplitude = np.linalg.norm(tensor, axis=(1, 2)) / math.sqrt(2.0)
        if not np.allclose(
            expected_amplitude,
            self.section.amplitude,
            rtol=8.0 * np.finfo(float).eps,
            atol=0.0,
        ):
            raise ReferentContractError(
                "F4 amplitude must equal the traceless Frobenius norm "
                "divided by root two"
            )
        object.__setattr__(self, "traceless_tensor", tensor)


@dataclass(frozen=True, slots=True)
class ObservationPartition:
    """A computed identity split, not proof of estimator read behavior.

    The receipt proves declared identity disjointness and exact row alignment.
    It cannot independently prove that frame- or plane-fitting code honored
    the declared fit side; that requires a separately controlled execution
    boundary.
    """

    fit_identities: Int64Array
    evaluation_identities: Int64Array
    row_identity_column: int
    fit_identity_sha256: str
    evaluation_identity_sha256: str
    ordered_row_identity_sha256: str

    def __post_init__(self) -> None:
        for name in ("fit_identities", "evaluation_identities"):
            source = getattr(self, name)
            if (
                not isinstance(source, np.ndarray)
                or source.dtype.str != "<i8"
                or source.ndim != 2
                or not source.flags.c_contiguous
            ):
                raise ReferentContractError(
                    f"{name} must be a C-contiguous int64 matrix"
                )
            object.__setattr__(
                self,
                name,
                _immutable_array(source, dtype=np.dtype("<i8")),
            )
        if (
            self.fit_identities.shape[0] == 0
            or self.evaluation_identities.shape[0] == 0
            or self.fit_identities.shape[1] < 2
            or self.fit_identities.shape[1] != self.evaluation_identities.shape[1]
        ):
            raise ReferentContractError(
                "partition identity matrices must be nonempty, have at "
                "least two columns, and share one width"
            )
        if (
            type(self.row_identity_column) is not int
            or self.row_identity_column < 0
            or self.row_identity_column >= self.fit_identities.shape[1]
        ):
            raise ReferentContractError(
                "row_identity_column is outside the identity width"
            )
        for name in ("fit_identity_sha256", "evaluation_identity_sha256"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise ReferentContractError(
                    f"{name} must be a lowercase SHA-256 digest"
                )
        if (
            not isinstance(self.ordered_row_identity_sha256, str)
            or len(self.ordered_row_identity_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.ordered_row_identity_sha256
            )
        ):
            raise ReferentContractError(
                "ordered_row_identity_sha256 must be a lowercase SHA-256 digest"
            )
        fit_rows = _identity_rows(self.fit_identities)
        evaluation_rows = _identity_rows(self.evaluation_identities)
        if len(set(fit_rows)) != len(fit_rows):
            raise ReferentContractError("fit identities must be unique")
        if len(set(evaluation_rows)) != len(evaluation_rows):
            raise ReferentContractError("evaluation identities must be unique")
        if set(fit_rows).intersection(evaluation_rows):
            raise ReferentContractError(
                "fit and evaluation identities must be disjoint"
            )
        fit_domain = self.fit_identities[:, self.row_identity_column]
        evaluation_domain = self.evaluation_identities[:, self.row_identity_column]
        if not np.array_equal(fit_domain, evaluation_domain):
            raise ReferentContractError(
                "fit and evaluation identities must have the same exact "
                "ordered row domain"
            )
        expected_fit_sha256 = _identity_sha256(
            "fit",
            self.fit_identities,
        )
        expected_evaluation_sha256 = _identity_sha256(
            "evaluation",
            self.evaluation_identities,
        )
        if self.fit_identity_sha256 != expected_fit_sha256:
            raise ReferentContractError(
                "fit_identity_sha256 differs from the computed identity"
            )
        if self.evaluation_identity_sha256 != expected_evaluation_sha256:
            raise ReferentContractError(
                "evaluation_identity_sha256 differs from the computed identity"
            )
        expected_row_sha256 = _ordered_row_identity_sha256(fit_domain)
        if self.ordered_row_identity_sha256 != expected_row_sha256:
            raise ReferentContractError(
                "ordered_row_identity_sha256 differs from the computed "
                "ordered row domain"
            )

    @property
    def ordered_row_identities(self) -> Int64Array:
        result = self.fit_identities[:, self.row_identity_column]
        result.flags.writeable = False
        return result

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": "spirallens.observation-partition-receipt.v0.1",
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "row_identity_column": self.row_identity_column,
            "identity_width": self.fit_identities.shape[1],
            "observation_count": self.fit_identities.shape[0],
            "fit_identity_sha256": self.fit_identity_sha256,
            "evaluation_identity_sha256": self.evaluation_identity_sha256,
            "ordered_row_identity_sha256": (self.ordered_row_identity_sha256),
        }

    @property
    def canonical_sha256(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.to_dict())).hexdigest()


def _observation_identities(value: object, *, label: str) -> Int64Array:
    array = np.asarray(value)
    if array.ndim != 2 or array.shape[0] == 0 or array.shape[1] < 2:
        raise ReferentContractError(
            f"{label} must have shape (observations, identity_fields>=2)"
        )
    if array.dtype.kind not in {"i", "u"} or array.dtype.kind == "b":
        raise ReferentContractError(f"{label} must have an integer dtype")
    try:
        result = np.array(array, dtype="<i8", order="C", copy=True)
    except (OverflowError, TypeError, ValueError) as error:
        raise ReferentContractError(
            f"{label} cannot be represented as int64"
        ) from error
    if not np.array_equal(result, array):
        raise ReferentContractError(f"{label} exceeds the int64 range")
    return _immutable_array(result, dtype=np.dtype("<i8"))


def _identity_rows(value: Int64Array) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(item) for item in row) for row in value)


def _identity_sha256(label: str, value: Int64Array) -> str:
    descriptor = canonical_json_bytes(
        {
            "schema_version": "spirallens.observation-identity.v0.1",
            "label": label,
            "dtype": value.dtype.str,
            "shape": list(value.shape),
        }
    )
    return hashlib.sha256(descriptor + b"\x00" + value.tobytes(order="C")).hexdigest()


def validate_observation_partition(
    fit_identities: object,
    evaluation_identities: object,
    *,
    row_identity_column: int = 0,
) -> ObservationPartition:
    """Compute identity separation, not the fitting algorithm's read trace."""

    fit = _observation_identities(fit_identities, label="fit_identities")
    evaluation = _observation_identities(
        evaluation_identities,
        label="evaluation_identities",
    )
    if fit.shape[1] != evaluation.shape[1]:
        raise ReferentContractError(
            "fit and evaluation identities must have equal width"
        )
    if (
        type(row_identity_column) is not int
        or row_identity_column < 0
        or row_identity_column >= fit.shape[1]
    ):
        raise ReferentContractError("row_identity_column is outside the identity width")
    fit_rows = _identity_rows(fit)
    evaluation_rows = _identity_rows(evaluation)
    if len(set(fit_rows)) != len(fit_rows):
        raise ReferentContractError("fit identities must be unique")
    if len(set(evaluation_rows)) != len(evaluation_rows):
        raise ReferentContractError("evaluation identities must be unique")
    if set(fit_rows).intersection(evaluation_rows):
        raise ReferentContractError("fit and evaluation identities must be disjoint")
    fit_domain = fit[:, row_identity_column]
    evaluation_domain = evaluation[:, row_identity_column]
    if not np.array_equal(fit_domain, evaluation_domain):
        raise ReferentContractError(
            "fit and evaluation identities must have the same exact ordered row domain"
        )
    return ObservationPartition(
        fit_identities=fit,
        evaluation_identities=evaluation,
        row_identity_column=row_identity_column,
        fit_identity_sha256=_identity_sha256("fit", fit),
        evaluation_identity_sha256=_identity_sha256(
            "evaluation",
            evaluation,
        ),
        ordered_row_identity_sha256=_ordered_row_identity_sha256(
            fit_domain,
        ),
    )


def _section_observation(
    hypothesis_id: HypothesisId,
    values: FloatArray,
    *,
    input_row_identities: object,
    partition: ObservationPartition | None,
    amplitude_floor: object,
) -> SectionObservation:
    floor = _amplitude_floor(amplitude_floor)
    section, amplitude, direction, defined = _section_arrays(
        values,
        amplitude_floor=floor,
    )
    return SectionObservation(
        hypothesis_id=hypothesis_id,
        input_row_identities=_row_identity_vector(
            input_row_identities,
            label="input_row_identities",
        ),
        partition=partition,
        values=section,
        amplitude=amplitude,
        unit_direction=direction,
        direction_defined=defined,
        amplitude_floor=floor,
    )


def derive_f2_section(
    local_frames: object,
    evaluation_responses: object,
    *,
    partition: ObservationPartition,
    input_row_identities: object,
    amplitude_floor: object = 0.0,
) -> SectionObservation:
    """Derive ``z=U.T@s`` and both of its same-object scalar views."""

    frames = _float_array(local_frames, label="local_frames", ndim=3)
    responses = _float_array(
        evaluation_responses,
        label="evaluation_responses",
        ndim=2,
    )
    if (
        frames.shape[0] == 0
        or frames.shape[2] != 2
        or responses.shape != frames.shape[:2]
    ):
        raise ReferentContractError(
            "local_frames and evaluation_responses must have shapes "
            "(rows, dimensions, 2) and (rows, dimensions)"
        )
    grams = np.einsum("ndi,ndj->nij", frames, frames)
    target = np.broadcast_to(np.eye(2, dtype="<f8"), grams.shape)
    if not np.allclose(
        grams,
        target,
        rtol=ORTHONORMAL_RELATIVE_TOLERANCE,
        atol=ORTHONORMAL_ABSOLUTE_TOLERANCE,
    ):
        raise ReferentContractError("local_frames must have orthonormal columns")
    values = np.einsum("ndi,nd->ni", frames, responses)
    return _section_observation(
        HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        values,
        input_row_identities=input_row_identities,
        partition=partition,
        amplitude_floor=amplitude_floor,
    )


def derive_f3_section(
    global_plane: object,
    evaluation_responses: object,
    *,
    learned_plane: bool,
    input_row_identities: object,
    partition: ObservationPartition | None = None,
    amplitude_floor: object = 0.0,
) -> SectionObservation:
    """Derive the projection-dependent global-plane section."""

    if type(learned_plane) is not bool:
        raise ReferentContractError("learned_plane must be a boolean")
    if learned_plane and not isinstance(partition, ObservationPartition):
        raise ReferentContractError(
            "a learned F3 plane requires a validated ObservationPartition"
        )
    if not learned_plane and partition is not None:
        raise ReferentContractError(
            "a predeclared F3 plane must not claim a fit partition"
        )

    plane = _float_array(global_plane, label="global_plane", ndim=2)
    responses = _float_array(
        evaluation_responses,
        label="evaluation_responses",
        ndim=2,
    )
    if (
        plane.shape[1] != 2
        or responses.shape[0] == 0
        or responses.shape[1] != plane.shape[0]
    ):
        raise ReferentContractError(
            "global_plane and evaluation_responses must have shapes "
            "(dimensions, 2) and (rows, dimensions)"
        )
    gram = plane.T @ plane
    if not np.allclose(
        gram,
        np.eye(2, dtype="<f8"),
        rtol=ORTHONORMAL_RELATIVE_TOLERANCE,
        atol=ORTHONORMAL_ABSOLUTE_TOLERANCE,
    ):
        raise ReferentContractError("global_plane must have orthonormal columns")
    values = responses @ plane
    return _section_observation(
        HypothesisId.F3_GLOBAL_PLANE_SECTION,
        values,
        input_row_identities=input_row_identities,
        partition=partition,
        amplitude_floor=amplitude_floor,
    )


def derive_f4_spin_two(
    in_plane_symmetric_tensors: object,
    *,
    partition: ObservationPartition,
    input_row_identities: object,
    amplitude_floor: object = 0.0,
) -> SpinTwoObservation:
    """Derive the traceless spin-two vector and amplitude from one tensor."""

    tensors = _float_array(
        in_plane_symmetric_tensors,
        label="in_plane_symmetric_tensors",
        ndim=3,
    )
    if tensors.shape[0] == 0 or tensors.shape[1:] != (2, 2):
        raise ReferentContractError(
            "in_plane_symmetric_tensors must have shape (rows, 2, 2)"
        )
    if not np.allclose(
        tensors,
        np.swapaxes(tensors, 1, 2),
        rtol=SYMMETRY_RELATIVE_TOLERANCE,
        atol=SYMMETRY_ABSOLUTE_TOLERANCE,
    ):
        raise ReferentContractError("in_plane_symmetric_tensors must be symmetric")
    symmetric = (tensors + np.swapaxes(tensors, 1, 2)) / 2.0
    trace_half = np.trace(symmetric, axis1=1, axis2=2) / 2.0
    traceless = np.array(symmetric, dtype="<f8", order="C", copy=True)
    traceless[:, 0, 0] -= trace_half
    traceless[:, 1, 1] -= trace_half
    traceless[traceless == 0.0] = 0.0
    values = np.column_stack(
        (
            (traceless[:, 0, 0] - traceless[:, 1, 1]) / 2.0,
            traceless[:, 0, 1],
        )
    )
    section = _section_observation(
        HypothesisId.F4_SPIN_TWO_ANISOTROPY,
        values,
        input_row_identities=input_row_identities,
        partition=partition,
        amplitude_floor=amplitude_floor,
    )
    traceless.flags.writeable = False
    return SpinTwoObservation(
        traceless_tensor=traceless,
        section=section,
    )
