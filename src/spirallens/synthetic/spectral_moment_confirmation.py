"""Development generator for a future construction-diverse confirmation.

This module maps a separable spectral-moment construction onto the existing
label-free Cartesian Fourier estimator-input type.  It does not call the
Cartesian phantom generator: the spatial states and first/second moments are
constructed here from a fixed sine/cosine basis on a matched 7 by 7 discrete
domain.

The generated objects are development inputs only.  They are not a D7 run,
confirmation evidence, a frozen confirmation seed, or authority for model,
semantic, integer, winding, or topology claims.  Evaluator-only case semantics
and oracle fields are held in objects separate from estimator-visible arrays.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, fields
from pathlib import Path
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256

from .cartesian_fourier_domain_phantom import CartesianFourierEstimatorInputs
from .generators import GeneratorFamilyIdentity

SPECTRAL_MOMENT_LOCALIZED_CORE_NONZERO = "spectral-moment-localized-core-nonzero"
SPECTRAL_MOMENT_LOCALIZED_CORE_NULL = "spectral-moment-localized-core-null"
SPECTRAL_MOMENT_NO_CORE_NULL = "spectral-moment-no-core-null"
SPECTRAL_MOMENT_PREREQUISITE_FAILURE = (
    "spectral-moment-confirmation-prerequisite-failure"
)
SPECTRAL_MOMENT_GENERATOR_FAMILY_ID = (
    "spectral-moment-confirmation-grid-v0.1"
)
SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID = "separable-spectral-moment-grid"
SPECTRAL_MOMENT_IMPLEMENTATION_ID = "numpy-separable-sine-moment-grid"
SPECTRAL_MOMENT_IMPLEMENTATION_VERSION = "v0.1"
SPECTRAL_MOMENT_SOURCE_PATH = (
    "src/spirallens/synthetic/spectral_moment_confirmation.py"
)

SPECTRAL_MOMENT_CASE_REGISTRY = (
    (
        SPECTRAL_MOMENT_LOCALIZED_CORE_NONZERO,
        "localized-core|nonzero",
        "separable-sine-localized-core-nonzero",
        "localized_core",
        "nonzero",
    ),
    (
        SPECTRAL_MOMENT_LOCALIZED_CORE_NULL,
        "localized-core|null",
        "fixed-spectral-localized-core-null",
        "localized_core",
        "null",
    ),
    (
        SPECTRAL_MOMENT_NO_CORE_NULL,
        "no-core|null",
        "fixed-spectral-no-core-null",
        "no_core",
        "null",
    ),
    (
        SPECTRAL_MOMENT_PREREQUISITE_FAILURE,
        "prerequisite-failure|prerequisite-failure",
        "zero-signal-prerequisite-failure",
        "prerequisite_failure",
        "prerequisite_failure",
    ),
)
"""Single canonical registry shared by the generator and D7 draft contract."""

SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS = tuple(
    item[1] for item in SPECTRAL_MOMENT_CASE_REGISTRY
)

_CASE_IDS = tuple(item[0] for item in SPECTRAL_MOMENT_CASE_REGISTRY)
_CASE_SEMANTICS = {
    item[0]: item[1]
    for item in SPECTRAL_MOMENT_CASE_REGISTRY
}

_GRID_SIDE = 7
_ROW_COUNT = _GRID_SIDE * _GRID_SIDE
_AMBIENT_DIMENSION = 12
_SAMPLES_PER_SPLIT = 8
_BASELINE = 1.25
_SECOND_MOMENT_SCALE = 0.25
_FLOAT = np.dtype("<f8")
_INT64 = np.dtype("<i8")
_BOOL = np.dtype("|b1")

FloatArray = NDArray[np.float64]
Int64Array = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


def _plain_seed(value: object) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, np.integer),
    ):
        raise TypeError("seed must be an integer")
    result = int(value)
    if result < 0 or result > np.iinfo(np.int64).max:
        raise ValueError("seed must be a non-negative signed-int64 value")
    return result


def _immutable(
    value: object,
    *,
    dtype: np.dtype[object],
    ndim: int,
    label: str,
) -> NDArray[np.generic]:
    source = np.asarray(value)
    if source.ndim != ndim:
        raise ValueError(f"{label} must have rank {ndim}")
    if dtype.kind == "f" and source.dtype.kind != "f":
        raise TypeError(f"{label} must have a floating dtype")
    if dtype.kind == "i" and source.dtype.kind not in {"i", "u"}:
        raise TypeError(f"{label} must have an integer, non-boolean dtype")
    if dtype.kind == "b" and source.dtype.kind != "b":
        raise TypeError(f"{label} must have a boolean dtype")
    result = np.array(source, dtype=dtype, order="C", copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must contain only finite values")
    if dtype.kind == "f":
        result[result == 0.0] = 0.0
    backing = result.tobytes(order="C")
    return np.frombuffer(backing, dtype=dtype).reshape(result.shape)


def _array_sha256(value: NDArray[np.generic]) -> str:
    descriptor = (
        f"{value.dtype.str}|{','.join(str(item) for item in value.shape)}|"
    ).encode("ascii")
    return hashlib.sha256(descriptor + value.tobytes(order="C")).hexdigest()


def _array_fingerprint(value: NDArray[np.generic]) -> dict[str, object]:
    return {
        "dtype": value.dtype.str,
        "shape": list(value.shape),
        "sha256": _array_sha256(value),
    }


@dataclass(frozen=True, slots=True)
class SpectralMomentConfirmationSpec:
    """One explicit development seed for the fixed construction.

    The seed has no default so this source cannot silently nominate a future
    confirmation seed.  A later frozen protocol must supply and bind it.
    """

    seed: int

    receipt_version: ClassVar[str] = "spirallens.spectral-moment-confirmation-spec.v0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "seed", _plain_seed(self.seed))

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": "in-memory-development-fingerprint-only",
            "seed": self.seed,
            "seed_role": "caller-supplied-development-or-future-frozen-input",
            "confirmation_seed_frozen_by_this_source": False,
            "grid_side": _GRID_SIDE,
            "row_count": _ROW_COUNT,
            "ambient_dimension": _AMBIENT_DIMENSION,
            "samples_per_split": _SAMPLES_PER_SPLIT,
            "baseline": _BASELINE,
            "second_moment_scale": _SECOND_MOMENT_SCALE,
            "construction_rule": (
                "separable-sine-first-moment-plus-fixed-spectral-null-controls"
            ),
            "quadrature_rule": "interleaved-uniform-even-fit-odd-evaluation",
            "required_case_semantics": list(SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS),
        }

    @property
    def receipt_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class SpectralMomentConfirmationDomain:
    """Matched discrete support shared by every generated case."""

    row_ids: Int64Array
    support_mask: BoolArray
    states: FloatArray
    site_coordinates: FloatArray
    oriented_faces: Int64Array

    _ARRAY_LAYOUT: ClassVar[dict[str, tuple[np.dtype[object], int]]] = {
        "row_ids": (_INT64, 1),
        "support_mask": (_BOOL, 1),
        "states": (_FLOAT, 2),
        "site_coordinates": (_FLOAT, 2),
        "oriented_faces": (_INT64, 2),
    }

    def __post_init__(self) -> None:
        for name, (dtype, ndim) in self._ARRAY_LAYOUT.items():
            object.__setattr__(
                self,
                name,
                _immutable(
                    getattr(self, name),
                    dtype=dtype,
                    ndim=ndim,
                    label=name,
                ),
            )
        if self.row_ids.shape != (_ROW_COUNT,):
            raise ValueError("row_ids must describe exactly one 7 by 7 grid")
        if not np.array_equal(self.row_ids, np.arange(_ROW_COUNT, dtype=_INT64)):
            raise ValueError("row_ids must use canonical row-major identity")
        if self.support_mask.shape != (_ROW_COUNT,) or not np.all(self.support_mask):
            raise ValueError("support_mask must include all 49 discrete vertices")
        if self.states.shape != (_ROW_COUNT, _AMBIENT_DIMENSION):
            raise ValueError("states must have shape (49, 12)")
        if self.site_coordinates.shape != (_ROW_COUNT, 2):
            raise ValueError("site_coordinates must have shape (49, 2)")
        if self.oriented_faces.shape != (72, 3):
            raise ValueError("oriented_faces must contain the 72 grid triangles")
        if np.any(self.oriented_faces < 0) or np.any(self.oriented_faces >= _ROW_COUNT):
            raise ValueError("oriented_faces contain an out-of-range row")

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": "spirallens.spectral-moment-domain.v0.1",
            "record_scope": "in-memory-fingerprint-only",
            "arrays": {
                item.name: _array_fingerprint(getattr(self, item.name))
                for item in fields(self)
                if item.name in self._ARRAY_LAYOUT
            },
            "matched_support_only": True,
            "field_oracle_present": False,
            "case_semantics_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _continuous_loop_total(
    field: FloatArray,
    loop_rows: Int64Array,
) -> float:
    vectors = field[loop_rows]
    amplitudes = np.linalg.norm(vectors, axis=1)
    if np.any(amplitudes <= 0.0):
        raise ValueError("oracle loop contains an undefined direction")
    unit = vectors / amplitudes[:, None]
    following = np.roll(unit, -1, axis=0)
    increments = np.arctan2(
        unit[:, 0] * following[:, 1] - unit[:, 1] * following[:, 0],
        np.sum(unit * following, axis=1),
    )
    if np.max(np.abs(increments)) >= np.pi - 1e-12:
        raise ValueError("oracle loop contains a branch-ambiguous edge")
    return float(np.sum(increments, dtype=np.float64))


@dataclass(frozen=True, slots=True)
class SpectralMomentConfirmationOracleTruth:
    """Evaluator-only fields and qualitative core/loop case semantics."""

    truth_id: str
    case_semantics: str
    row_ids: Int64Array
    first_moment_field: FloatArray
    second_moment_field: FloatArray
    field_support_mask: BoolArray
    core_anchor_mask: BoolArray
    probe_loop_vertex_rows: Int64Array

    _ARRAY_LAYOUT: ClassVar[dict[str, tuple[np.dtype[object], int]]] = {
        "row_ids": (_INT64, 1),
        "first_moment_field": (_FLOAT, 2),
        "second_moment_field": (_FLOAT, 2),
        "field_support_mask": (_BOOL, 1),
        "core_anchor_mask": (_BOOL, 1),
        "probe_loop_vertex_rows": (_INT64, 1),
    }

    def __post_init__(self) -> None:
        if not isinstance(self.truth_id, str) or not self.truth_id:
            raise ValueError("truth_id must be a nonempty string")
        if self.case_semantics not in SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS:
            raise ValueError("case_semantics is outside the closed vocabulary")
        for name, (dtype, ndim) in self._ARRAY_LAYOUT.items():
            object.__setattr__(
                self,
                name,
                _immutable(
                    getattr(self, name),
                    dtype=dtype,
                    ndim=ndim,
                    label=name,
                ),
            )
        if not np.array_equal(self.row_ids, np.arange(_ROW_COUNT, dtype=_INT64)):
            raise ValueError("oracle row_ids differ from the matched grid")
        for name in ("first_moment_field", "second_moment_field"):
            if getattr(self, name).shape != (_ROW_COUNT, 2):
                raise ValueError(f"{name} must have shape (49, 2)")
        for name in ("field_support_mask", "core_anchor_mask"):
            if getattr(self, name).shape != (_ROW_COUNT,):
                raise ValueError(f"{name} must have shape (49,)")
        expected_support = np.linalg.norm(self.first_moment_field, axis=1) > 0.0
        if not np.array_equal(self.field_support_mask, expected_support):
            raise ValueError("field_support_mask must derive from the first moment")
        if not np.array_equal(
            np.linalg.norm(self.second_moment_field, axis=1) > 0.0,
            expected_support,
        ):
            raise ValueError("first and second moments require matched support")
        expected_loop = np.asarray(
            (16, 17, 18, 25, 32, 31, 30, 23),
            dtype=_INT64,
        )
        if not np.array_equal(self.probe_loop_vertex_rows, expected_loop):
            raise ValueError("probe loop must be the fixed central 3 by 3 boundary")

        center_mask = np.zeros(_ROW_COUNT, dtype=_BOOL)
        center_mask[24] = True
        if self.case_semantics.startswith("localized-core|"):
            if not np.array_equal(self.core_anchor_mask, center_mask):
                raise ValueError("localized-core semantics require the center anchor")
            if not np.array_equal(~expected_support, center_mask):
                raise ValueError("localized-core field must vanish only at the center")
        elif np.any(self.core_anchor_mask):
            raise ValueError("non-core semantics cannot carry a core anchor")

        if self.case_semantics == "no-core|null" and not np.all(expected_support):
            raise ValueError("no-core null must be supported at every vertex")
        if self.case_semantics == (
            "prerequisite-failure|prerequisite-failure"
        ) and np.any(expected_support):
            raise ValueError("prerequisite-failure must have no field support")

        if self.case_semantics != ("prerequisite-failure|prerequisite-failure"):
            loop_total = _continuous_loop_total(
                self.first_moment_field,
                self.probe_loop_vertex_rows,
            )
            if self.case_semantics == "localized-core|nonzero":
                if abs(loop_total) <= math.pi:
                    raise ValueError(
                        "nonzero loop semantics require a nonzero continuous total"
                    )
            elif abs(loop_total) > 1e-12:
                raise ValueError("null loop semantics require a zero continuous total")

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": ("spirallens.spectral-moment-confirmation-oracle.v0.1"),
            "record_scope": "evaluator-only-in-memory-fingerprint",
            "truth_id": self.truth_id,
            "case_semantics": self.case_semantics,
            "arrays": {
                item.name: _array_fingerprint(getattr(self, item.name))
                for item in fields(self)
                if item.name in self._ARRAY_LAYOUT
            },
            "oracle_is_estimator_input": False,
            "loop_semantics_are_supplied_control_truth": True,
            "integer_loop_value_present": False,
            "topology_claimed": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _observed_moment(
    *,
    angles: FloatArray,
    values: FloatArray,
    harmonic: int,
) -> FloatArray:
    centered = values - values.mean(axis=1, keepdims=True)
    scale = 2.0 / float(angles.shape[0])
    return np.asarray(
        scale
        * np.column_stack(
            (
                centered @ np.cos(float(harmonic) * angles),
                centered @ np.sin(float(harmonic) * angles),
            )
        ),
        dtype=_FLOAT,
    )


@dataclass(frozen=True, slots=True)
class SpectralMomentConfirmationCase:
    """Evaluator-side linkage between label-free inputs and held-aside truth."""

    case_id: str
    estimator_inputs: CartesianFourierEstimatorInputs
    oracle_truth: SpectralMomentConfirmationOracleTruth

    def __post_init__(self) -> None:
        if self.case_id not in _CASE_IDS:
            raise ValueError("unsupported spectral-moment confirmation case_id")
        if not isinstance(
            self.estimator_inputs,
            CartesianFourierEstimatorInputs,
        ):
            raise TypeError("estimator_inputs must be CartesianFourierEstimatorInputs")
        if not isinstance(
            self.oracle_truth,
            SpectralMomentConfirmationOracleTruth,
        ):
            raise TypeError(
                "oracle_truth must be SpectralMomentConfirmationOracleTruth"
            )
        if self.oracle_truth.case_semantics != _CASE_SEMANTICS[self.case_id]:
            raise ValueError("case_id and exact case semantics disagree")
        if not np.array_equal(
            self.estimator_inputs.row_ids,
            self.oracle_truth.row_ids,
        ):
            raise ValueError("estimator inputs and oracle require identical row order")
        for split in ("fit", "evaluation"):
            observed_first = _observed_moment(
                angles=getattr(self.estimator_inputs, f"{split}_angles_rad"),
                values=getattr(self.estimator_inputs, f"{split}_values"),
                harmonic=1,
            )
            observed_second = _observed_moment(
                angles=getattr(self.estimator_inputs, f"{split}_angles_rad"),
                values=getattr(self.estimator_inputs, f"{split}_values"),
                harmonic=2,
            )
            if not np.allclose(
                observed_first,
                self.oracle_truth.first_moment_field,
                rtol=1e-12,
                atol=1e-12,
            ):
                raise ValueError(f"{split} observations do not recover first moment")
            if not np.allclose(
                observed_second,
                self.oracle_truth.second_moment_field,
                rtol=1e-12,
                atol=1e-12,
            ):
                raise ValueError(f"{split} observations do not recover second moment")

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": ("spirallens.spectral-moment-confirmation-case.v0.1"),
            "record_scope": "in-memory-fingerprint-only",
            "case_id": self.case_id,
            "estimator_inputs_fingerprint_sha256": (
                self.estimator_inputs.fingerprint_sha256
            ),
            "oracle_truth_fingerprint_sha256": (self.oracle_truth.fingerprint_sha256),
            "truth_separated_from_estimator_inputs": True,
        }


@dataclass(frozen=True, slots=True)
class SpectralMomentConfirmationBundle:
    """Four matched development cases, not a D7 evidence bundle."""

    spec: SpectralMomentConfirmationSpec
    family_identity: GeneratorFamilyIdentity
    domain: SpectralMomentConfirmationDomain
    cases: tuple[SpectralMomentConfirmationCase, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, SpectralMomentConfirmationSpec):
            raise TypeError("spec must be a SpectralMomentConfirmationSpec")
        if self.family_identity != _family_identity():
            raise ValueError("family_identity must match this exact source")
        if not isinstance(self.domain, SpectralMomentConfirmationDomain):
            raise TypeError("domain must be a SpectralMomentConfirmationDomain")
        if not isinstance(self.cases, tuple) or any(
            not isinstance(item, SpectralMomentConfirmationCase) for item in self.cases
        ):
            raise TypeError("cases must be a tuple of confirmation cases")
        if tuple(item.case_id for item in self.cases) != _CASE_IDS:
            raise ValueError("cases must use the exact canonical order")
        if tuple(item.oracle_truth.case_semantics for item in self.cases) != (
            SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS
        ):
            raise ValueError("cases do not realize the exact required semantics")
        if len({item.estimator_inputs.input_id for item in self.cases}) != 4:
            raise ValueError("each case requires distinct label-free content")
        for case in self.cases:
            inputs = case.estimator_inputs
            for actual, expected, label in (
                (inputs.row_ids, self.domain.row_ids, "row_ids"),
                (inputs.states, self.domain.states, "states"),
                (
                    inputs.site_coordinates,
                    self.domain.site_coordinates,
                    "site_coordinates",
                ),
                (
                    inputs.oriented_faces,
                    self.domain.oriented_faces,
                    "oriented_faces",
                ),
            ):
                if not np.array_equal(actual, expected):
                    raise ValueError(f"case does not share matched domain {label}")

    @property
    def positive(self) -> SpectralMomentConfirmationCase:
        return self.cases[0]

    @property
    def localized_core_null(self) -> SpectralMomentConfirmationCase:
        return self.cases[1]

    @property
    def no_core_null(self) -> SpectralMomentConfirmationCase:
        return self.cases[2]

    @property
    def prerequisite_failure(self) -> SpectralMomentConfirmationCase:
        return self.cases[3]

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": ("spirallens.spectral-moment-confirmation-bundle.v0.1"),
            "record_scope": "in-memory-development-fingerprint-only",
            "spec": self.spec.to_dict(),
            "family_identity": self.family_identity.to_dict(),
            "domain_fingerprint_sha256": self.domain.fingerprint_sha256,
            "cases": [item.to_dict() for item in self.cases],
            "claim_ceiling": "level_0",
            "development_only": True,
            "d7_runner_present": False,
            "d7_confirmation_executed": False,
            "confirmation_seed_frozen": False,
            "model_values_present": False,
            "semantic_labels_present": False,
            "model_claim_authorized": False,
            "semantic_claim_authorized": False,
            "integer_output_authorized": False,
            "topology_claim_authorized": False,
        }

    @property
    def receipt_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def receipt_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _module_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _family_identity() -> GeneratorFamilyIdentity:
    return GeneratorFamilyIdentity(
        family_id=SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
        construction_family_id=SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID,
        implementation_id=SPECTRAL_MOMENT_IMPLEMENTATION_ID,
        implementation_version=SPECTRAL_MOMENT_IMPLEMENTATION_VERSION,
        source_sha256=_module_sha256(),
    )


def _domain() -> SpectralMomentConfirmationDomain:
    axis = np.linspace(-1.0, 1.0, _GRID_SIDE, dtype=_FLOAT)
    x_grid, y_grid = np.meshgrid(axis, axis, indexing="xy")
    x = x_grid.reshape(-1)
    y = y_grid.reshape(-1)
    coordinates = np.column_stack((x, y))
    states = np.column_stack(
        (
            np.sin(0.5 * np.pi * x),
            np.sin(0.5 * np.pi * y),
            np.cos(0.5 * np.pi * x),
            np.cos(0.5 * np.pi * y),
            np.sin(0.5 * np.pi * (x + y)),
            np.cos(0.5 * np.pi * (x + y)),
            np.sin(0.5 * np.pi * (x - y)),
            np.cos(0.5 * np.pi * (x - y)),
            0.1 * np.sin(np.pi * x),
            0.1 * np.sin(np.pi * y),
            0.1 * np.cos(np.pi * x),
            0.1 * np.cos(np.pi * y),
        )
    )
    faces: list[tuple[int, int, int]] = []
    for y_index in range(_GRID_SIDE - 1):
        for x_index in range(_GRID_SIDE - 1):
            lower_left = y_index * _GRID_SIDE + x_index
            lower_right = lower_left + 1
            upper_left = lower_left + _GRID_SIDE
            upper_right = upper_left + 1
            faces.extend(
                (
                    (lower_left, lower_right, upper_right),
                    (lower_left, upper_right, upper_left),
                )
            )
    return SpectralMomentConfirmationDomain(
        row_ids=np.arange(_ROW_COUNT, dtype=_INT64),
        support_mask=np.ones(_ROW_COUNT, dtype=_BOOL),
        states=np.asarray(states, dtype=_FLOAT),
        site_coordinates=np.asarray(coordinates, dtype=_FLOAT),
        oriented_faces=np.asarray(faces, dtype=_INT64),
    )


def _seed_phase(seed: int) -> float:
    return 2.0 * np.pi * float((7919 * seed + 1049) % 104729) / 104729.0


def _rotate(vectors: FloatArray, angle: float) -> FloatArray:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return np.asarray(
        np.column_stack(
            (
                cosine * vectors[:, 0] - sine * vectors[:, 1],
                sine * vectors[:, 0] + cosine * vectors[:, 1],
            )
        ),
        dtype=_FLOAT,
    )


def _fields(
    domain: SpectralMomentConfirmationDomain,
    *,
    case_semantics: str,
    seed: int,
) -> tuple[FloatArray, FloatArray, BoolArray]:
    x = domain.site_coordinates[:, 0]
    y = domain.site_coordinates[:, 1]
    spectral_x = np.sin(0.5 * np.pi * x)
    spectral_y = np.sin(0.5 * np.pi * y)
    core_amplitude = np.hypot(spectral_x, spectral_y)
    phase = _seed_phase(seed)

    if case_semantics == "localized-core|nonzero":
        first = _rotate(
            np.column_stack((spectral_x, spectral_y)),
            phase,
        )
    elif case_semantics == "localized-core|null":
        first = core_amplitude[:, None] * np.asarray(
            (math.cos(phase), math.sin(phase)),
            dtype=_FLOAT,
        )
    elif case_semantics == "no-core|null":
        amplitude = 0.8 + 0.2 * (np.cos(0.5 * np.pi * x) * np.cos(0.5 * np.pi * y))
        first = amplitude[:, None] * np.asarray(
            (math.cos(phase), math.sin(phase)),
            dtype=_FLOAT,
        )
    else:
        first = np.zeros((_ROW_COUNT, 2), dtype=_FLOAT)

    first = np.asarray(first, dtype=_FLOAT)
    amplitudes = np.linalg.norm(first, axis=1)
    second = np.zeros_like(first)
    supported = amplitudes > 0.0
    if np.any(supported):
        orientations = np.arctan2(first[supported, 1], first[supported, 0])
        second[supported, 0] = (
            _SECOND_MOMENT_SCALE * amplitudes[supported] * np.cos(2.0 * orientations)
        )
        second[supported, 1] = (
            _SECOND_MOMENT_SCALE * amplitudes[supported] * np.sin(2.0 * orientations)
        )
    core_anchor = np.zeros(_ROW_COUNT, dtype=_BOOL)
    if case_semantics.startswith("localized-core|"):
        core_anchor[24] = True
    return first, second, core_anchor


def _quadrature() -> tuple[Int64Array, FloatArray, Int64Array, FloatArray]:
    sample_ids = np.arange(2 * _SAMPLES_PER_SPLIT, dtype=_INT64)
    angles = 2.0 * np.pi * sample_ids.astype(_FLOAT) / float(2 * _SAMPLES_PER_SPLIT)
    return sample_ids[0::2], angles[0::2], sample_ids[1::2], angles[1::2]


def _values(
    *,
    angles: FloatArray,
    first: FloatArray,
    second: FloatArray,
) -> FloatArray:
    return np.asarray(
        _BASELINE
        + first[:, 0, None] * np.cos(angles)[None, :]
        + first[:, 1, None] * np.sin(angles)[None, :]
        + second[:, 0, None] * np.cos(2.0 * angles)[None, :]
        + second[:, 1, None] * np.sin(2.0 * angles)[None, :],
        dtype=_FLOAT,
    )


def _case(
    domain: SpectralMomentConfirmationDomain,
    spec: SpectralMomentConfirmationSpec,
    *,
    case_id: str,
) -> SpectralMomentConfirmationCase:
    semantics = _CASE_SEMANTICS[case_id]
    first, second, core_anchor = _fields(
        domain,
        case_semantics=semantics,
        seed=spec.seed,
    )
    fit_ids, fit_angles, evaluation_ids, evaluation_angles = _quadrature()
    fit_values = _values(angles=fit_angles, first=first, second=second)
    evaluation_values = _values(
        angles=evaluation_angles,
        first=first,
        second=second,
    )
    estimator_inputs = CartesianFourierEstimatorInputs.from_observable_arrays(
        row_ids=domain.row_ids,
        states=domain.states,
        site_coordinates=domain.site_coordinates,
        oriented_faces=domain.oriented_faces,
        fit_sample_ids=fit_ids,
        fit_angles_rad=fit_angles,
        fit_values=fit_values,
        evaluation_sample_ids=evaluation_ids,
        evaluation_angles_rad=evaluation_angles,
        evaluation_values=evaluation_values,
    )
    oracle = SpectralMomentConfirmationOracleTruth(
        truth_id=f"spectral-moment-truth-{case_id}",
        case_semantics=semantics,
        row_ids=domain.row_ids,
        first_moment_field=first,
        second_moment_field=second,
        field_support_mask=np.linalg.norm(first, axis=1) > 0.0,
        core_anchor_mask=core_anchor,
        probe_loop_vertex_rows=np.asarray(
            (16, 17, 18, 25, 32, 31, 30, 23),
            dtype=_INT64,
        ),
    )
    return SpectralMomentConfirmationCase(
        case_id=case_id,
        estimator_inputs=estimator_inputs,
        oracle_truth=oracle,
    )


class SpectralMomentConfirmationGenerator:
    """Generate development cases for a later, separately frozen protocol."""

    @property
    def family_identity(self) -> GeneratorFamilyIdentity:
        return _family_identity()

    def generate(
        self,
        spec: SpectralMomentConfirmationSpec,
    ) -> SpectralMomentConfirmationBundle:
        if not isinstance(spec, SpectralMomentConfirmationSpec):
            raise TypeError("spec must be a SpectralMomentConfirmationSpec")
        domain = _domain()
        cases = tuple(_case(domain, spec, case_id=case_id) for case_id in _CASE_IDS)
        return SpectralMomentConfirmationBundle(
            spec=spec,
            family_identity=self.family_identity,
            domain=domain,
            cases=cases,
        )
