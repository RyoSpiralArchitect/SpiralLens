"""Deterministic Cartesian Fourier-domain phantoms for Level-0 qualification.

This separately implemented construction supplies a spatially indexed,
high-dimensional numerical substrate together with interleaved Fourier
quadrature observations.  Estimator-visible inputs and evaluator-only truth
are different immutable objects.

The module constructs no graph, inferred core, loop estimate, winding result,
qualification decision, subject observation, semantic label, or model claim.
The loop rows and expected sampled responses in the oracle are supplied
synthetic truth only; they are not estimator inputs and are not observed
qualification outputs.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, fields
from enum import Enum
from pathlib import Path
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256

from .generators import GeneratorFamilyIdentity

CARTESIAN_FOURIER_POSITIVE = "cartesian-fourier-positive"
CARTESIAN_FOURIER_FIXED_NULL = "cartesian-fourier-fixed-null"
CARTESIAN_FOURIER_NO_CORE_NULL = "cartesian-fourier-no-core-null"
CARTESIAN_FOURIER_PREREQUISITE_FAILURE = "cartesian-fourier-prerequisite-failure"

CARTESIAN_FOURIER_RESOURCE_ESTIMATOR_ID = (
    "cartesian-fourier-domain-linear-mixing-peak-v0.2"
)
CARTESIAN_FOURIER_STATE_MIXING_ID = "seeded-signed-permutation-v0.1"
CARTESIAN_FOURIER_RESOURCE_SAFETY_FACTOR = 4
MAX_CARTESIAN_FOURIER_ESTIMATED_PEAK_BYTES = 256 * 1024 * 1024
CARTESIAN_FOURIER_RELATION_RTOL = 1e-9
CARTESIAN_FOURIER_RELATION_ATOL = 128.0 * np.finfo(np.float64).eps
CARTESIAN_FOURIER_MAX_DENSITY_WARP = 0.9
CARTESIAN_FOURIER_STATE_NUISANCE_SCALE = 0.02
CARTESIAN_FOURIER_STATE_SHEAR = 0.01

_BASE_OVERHEAD_BYTES = 1024 * 1024
_FLOAT = np.dtype("<f8")
_INT64 = np.dtype("<i8")
_BOOL = np.dtype("|b1")
_CONTENT_PSEUDONYM = re.compile(r"^cfi_[0-9a-f]{32}$")

FloatArray = NDArray[np.float64]
Int64Array = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


class CartesianExpectedDisposition(str, Enum):
    """Evaluator-only joint core/loop role for one synthetic control."""

    NONZERO_WITH_CORE = "nonzero_with_core"
    NULL_WITH_CORE = "null_with_core"
    NULL_WITHOUT_CORE = "null_without_core"
    PREREQUISITE_FAILURE = "prerequisite_failure"


def _integer(value: object, *, label: str, minimum: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, np.integer),
    ):
        raise TypeError(f"{label} must be an integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return result


def _real(
    value: object,
    *,
    label: str,
    positive: bool,
) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, float, np.integer, np.floating),
    ):
        raise TypeError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise ValueError(f"{label} must be positive")
    if not positive and result < 0.0:
        raise ValueError(f"{label} must be non-negative")
    if result == 0.0 and math.copysign(1.0, result) < 0.0:
        raise ValueError(f"{label} must not be negative zero")
    return result


def _estimated_peak_bytes(
    *,
    row_count: int,
    ambient_dimension: int,
    samples_per_split: int,
    face_count: int,
) -> int:
    """Bound linear state mixing, retained cases, and later graph work."""

    pairwise_graph_work = (
        row_count * row_count * (3 * _FLOAT.itemsize + 2 * _INT64.itemsize)
    )
    state_mixing_work = (
        2 * row_count * ambient_dimension * _FLOAT.itemsize
        + 3 * ambient_dimension * _INT64.itemsize
    )
    retained_per_case = (
        row_count * ambient_dimension * _FLOAT.itemsize
        + row_count * 2 * _FLOAT.itemsize
        + row_count * 2 * samples_per_split * _FLOAT.itemsize
        + row_count * 20 * _FLOAT.itemsize
        + row_count * 12 * _INT64.itemsize
        + face_count * 3 * _INT64.itemsize
    )
    retained_arrays = 4 * retained_per_case
    return CARTESIAN_FOURIER_RESOURCE_SAFETY_FACTOR * (
        _BASE_OVERHEAD_BYTES + pairwise_graph_work + state_mixing_work + retained_arrays
    )


def _frozen(
    value: object,
    *,
    dtype: np.dtype[object],
    ndim: int,
    label: str,
) -> NDArray[np.generic]:
    source = np.asarray(value)
    if source.ndim != ndim:
        raise ValueError(f"{label} must have rank {ndim}")
    if dtype.kind == "f":
        if source.dtype.kind != "f":
            raise TypeError(f"{label} must have a floating dtype")
    elif dtype.kind == "i":
        if source.dtype.kind not in {"i", "u"}:
            raise TypeError(f"{label} must have an integer, non-boolean dtype")
        limits = np.iinfo(np.int64)
        if source.size and (
            (source.dtype.kind == "i" and np.any(source < limits.min))
            or np.any(source > limits.max)
        ):
            raise ValueError(f"{label} contains values outside int64 range")
    elif dtype.kind == "b":
        if source.dtype.kind != "b":
            raise TypeError(f"{label} must have a boolean dtype")
    else:  # pragma: no cover - the layouts below are closed
        raise TypeError(f"{label} has an unsupported expected dtype")

    result = np.array(source, dtype=dtype, order="C", copy=True)
    if dtype.kind == "i" and not np.array_equal(
        result.astype(source.dtype, copy=False),
        source,
    ):
        raise ValueError(f"{label} does not round-trip exactly through int64")
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
class CartesianFourierDomainSpec:
    """Bounded numerical inputs for one Cartesian Fourier construction."""

    seed: int = 314159
    grid_side: int = 7
    ambient_dimension: int = 12
    samples_per_split: int = 8
    baseline: float = 1.25
    second_harmonic_scale: float = 0.35
    noise_scale: float = 0.0
    density_warp_strength: float = 0.0

    receipt_version: ClassVar[str] = (
        "spirallens.cartesian-fourier-domain-spec-receipt.v0.2"
    )

    def __post_init__(self) -> None:
        seed = _integer(self.seed, label="seed", minimum=0)
        if seed > np.iinfo(np.int64).max:
            raise ValueError("seed must fit in signed int64")
        side = _integer(self.grid_side, label="grid_side", minimum=5)
        if side % 2 == 0:
            raise ValueError("grid_side must be odd")
        dimension = _integer(
            self.ambient_dimension,
            label="ambient_dimension",
            minimum=8,
        )
        samples = _integer(
            self.samples_per_split,
            label="samples_per_split",
            minimum=8,
        )
        if samples % 4 != 0:
            raise ValueError("samples_per_split must be divisible by four")
        baseline = _real(self.baseline, label="baseline", positive=True)
        second = _real(
            self.second_harmonic_scale,
            label="second_harmonic_scale",
            positive=True,
        )
        noise = _real(self.noise_scale, label="noise_scale", positive=False)
        warp = _real(
            self.density_warp_strength,
            label="density_warp_strength",
            positive=False,
        )
        if warp >= CARTESIAN_FOURIER_MAX_DENSITY_WARP:
            raise ValueError(
                "density_warp_strength must be smaller than the monotonicity bound"
            )
        combined_scale = baseline + 1.0 + second + noise
        safe_scale = math.sqrt(np.finfo(np.float64).max) / 16.0
        if not math.isfinite(combined_scale) or combined_scale > safe_scale:
            raise ValueError(
                "combined observation scale exceeds the arithmetic safety bound"
            )
        row_count = side * side
        face_count = 2 * (side - 1) * (side - 1)
        estimated_peak = _estimated_peak_bytes(
            row_count=row_count,
            ambient_dimension=dimension,
            samples_per_split=samples,
            face_count=face_count,
        )
        if estimated_peak > MAX_CARTESIAN_FOURIER_ESTIMATED_PEAK_BYTES:
            raise ValueError(
                "Cartesian Fourier estimated peak allocation exceeds the "
                "fixed 256 MiB cap"
            )
        object.__setattr__(self, "seed", seed)
        object.__setattr__(self, "grid_side", side)
        object.__setattr__(self, "ambient_dimension", dimension)
        object.__setattr__(self, "samples_per_split", samples)
        object.__setattr__(self, "baseline", baseline)
        object.__setattr__(self, "second_harmonic_scale", second)
        object.__setattr__(self, "noise_scale", noise)
        object.__setattr__(self, "density_warp_strength", warp)

    @property
    def row_count(self) -> int:
        return self.grid_side * self.grid_side

    @property
    def face_count(self) -> int:
        return 2 * (self.grid_side - 1) * (self.grid_side - 1)

    @property
    def estimated_peak_bytes(self) -> int:
        return _estimated_peak_bytes(
            row_count=self.row_count,
            ambient_dimension=self.ambient_dimension,
            samples_per_split=self.samples_per_split,
            face_count=self.face_count,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "seed": self.seed,
            "grid_side": self.grid_side,
            "ambient_dimension": self.ambient_dimension,
            "samples_per_split": self.samples_per_split,
            "baseline": self.baseline,
            "second_harmonic_scale": self.second_harmonic_scale,
            "noise_scale": self.noise_scale,
            "density_warp_strength": self.density_warp_strength,
            "row_order": "cartesian-row-major-y-then-x",
            "face_rule": "counterclockwise-lower-left-diagonal-triangles",
            "quadrature_split": ("interleaved-uniform-even-fit-odd-evaluation"),
            "amplitude_rules": {
                "with_core": "tanh-euclidean-radius",
                "without_core": "constant-one",
                "prerequisite_failure": "constant-zero",
            },
            "observation_rule": (
                "baseline-plus-a-cos-one-plus-c-a-cos-two-plus-"
                "deterministic-incommensurate-observation-noise"
            ),
            "noise_is_first-moment-visible_for_normal_controls": True,
            "prerequisite_failure_noise_disabled": True,
            "state_density_warp_rule": (
                "coordinate-plus-strength-times-sine-pi-coordinate-over-pi"
            ),
            "state_shear_rule": "y-plus-0.01-times-x",
            "state_mixing_id": CARTESIAN_FOURIER_STATE_MIXING_ID,
            "state_mixing_dense_square_allocation": False,
            "state_mixing_peak_order": "rows-times-ambient-dimension",
            "field_truth_uses_density_warp": False,
            "field_truth_uses_state_shear": False,
            "resource_estimator_id": CARTESIAN_FOURIER_RESOURCE_ESTIMATOR_ID,
            "resource_safety_factor": CARTESIAN_FOURIER_RESOURCE_SAFETY_FACTOR,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "max_estimated_peak_bytes": (MAX_CARTESIAN_FOURIER_ESTIMATED_PEAK_BYTES),
            "resource_model_peak_order": (
                "rows-times-ambient-dimension-plus-rows-times-samples-plus-rows-squared"
            ),
            "resource_claim_boundary": (
                "parameter-induced-runaway-allocation-guard-not-os-oom-guarantee"
            ),
            "claim_ceiling": "level_0",
        }

    @property
    def receipt_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def receipt_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _label_free_content_pseudonym(
    *,
    row_ids: Int64Array,
    states: FloatArray,
    site_coordinates: FloatArray,
    oriented_faces: Int64Array,
    fit_sample_ids: Int64Array,
    fit_angles_rad: FloatArray,
    fit_values: FloatArray,
    evaluation_sample_ids: Int64Array,
    evaluation_angles_rad: FloatArray,
    evaluation_values: FloatArray,
) -> str:
    arrays = {
        "row_ids": row_ids,
        "states": states,
        "site_coordinates": site_coordinates,
        "oriented_faces": oriented_faces,
        "fit_sample_ids": fit_sample_ids,
        "fit_angles_rad": fit_angles_rad,
        "fit_values": fit_values,
        "evaluation_sample_ids": evaluation_sample_ids,
        "evaluation_angles_rad": evaluation_angles_rad,
        "evaluation_values": evaluation_values,
    }
    digest = canonical_json_sha256(
        {
            "domain_version": ("spirallens.cartesian-fourier-label-free-content.v0.1"),
            "observable_array_fingerprints": {
                name: _array_fingerprint(value) for name, value in arrays.items()
            },
        }
    )
    return f"cfi_{digest[:32]}"


@dataclass(frozen=True, slots=True)
class CartesianFourierEstimatorInputs:
    """Only the arrays visible to a qualification estimator."""

    input_id: str
    row_ids: Int64Array
    states: FloatArray
    site_coordinates: FloatArray
    oriented_faces: Int64Array
    fit_sample_ids: Int64Array
    fit_angles_rad: FloatArray
    fit_values: FloatArray
    evaluation_sample_ids: Int64Array
    evaluation_angles_rad: FloatArray
    evaluation_values: FloatArray

    _ARRAY_LAYOUT: ClassVar[dict[str, tuple[np.dtype[object], int]]] = {
        "row_ids": (_INT64, 1),
        "states": (_FLOAT, 2),
        "site_coordinates": (_FLOAT, 2),
        "oriented_faces": (_INT64, 2),
        "fit_sample_ids": (_INT64, 1),
        "fit_angles_rad": (_FLOAT, 1),
        "fit_values": (_FLOAT, 2),
        "evaluation_sample_ids": (_INT64, 1),
        "evaluation_angles_rad": (_FLOAT, 1),
        "evaluation_values": (_FLOAT, 2),
    }

    receipt_version: ClassVar[str] = (
        "spirallens.cartesian-fourier-estimator-inputs-receipt.v0.1"
    )

    def __post_init__(self) -> None:
        if (
            not isinstance(self.input_id, str)
            or _CONTENT_PSEUDONYM.fullmatch(self.input_id) is None
        ):
            raise ValueError(
                "input_id must be a label-free Cartesian Fourier content pseudonym"
            )
        for name, (dtype, ndim) in self._ARRAY_LAYOUT.items():
            object.__setattr__(
                self,
                name,
                _frozen(
                    getattr(self, name),
                    dtype=dtype,
                    ndim=ndim,
                    label=name,
                ),
            )
        rows = self.row_ids.shape[0]
        if rows == 0 or len(set(self.row_ids.tolist())) != rows:
            raise ValueError("row_ids must be nonempty and unique")
        if self.states.shape[0] != rows or self.states.shape[1] < 8:
            raise ValueError(
                "states must have one row per identity and ambient dimension at least 8"
            )
        if self.site_coordinates.shape != (rows, 2):
            raise ValueError("site_coordinates must have shape (rows, 2)")
        if self.oriented_faces.shape[0] == 0 or self.oriented_faces.shape[1] != 3:
            raise ValueError("oriented_faces must have shape (faces, 3)")
        if np.any(self.oriented_faces < 0) or np.any(self.oriented_faces >= rows):
            raise ValueError("oriented_faces contain an out-of-range row")
        if np.any(np.diff(np.sort(self.oriented_faces, axis=1), axis=1) == 0):
            raise ValueError("each oriented face must contain three distinct rows")

        fit_count = self.fit_sample_ids.shape[0]
        evaluation_count = self.evaluation_sample_ids.shape[0]
        if fit_count == 0 or evaluation_count == 0:
            raise ValueError("fit and evaluation splits must be nonempty")
        if self.fit_angles_rad.shape != (fit_count,):
            raise ValueError("fit sample identities and angles differ")
        if self.evaluation_angles_rad.shape != (evaluation_count,):
            raise ValueError("evaluation sample identities and angles differ")
        if self.fit_values.shape != (rows, fit_count):
            raise ValueError("fit_values differ from the row/sample domain")
        if self.evaluation_values.shape != (rows, evaluation_count):
            raise ValueError("evaluation_values differ from the row/sample domain")
        fit_ids = set(self.fit_sample_ids.tolist())
        evaluation_ids = set(self.evaluation_sample_ids.tolist())
        if len(fit_ids) != fit_count or len(evaluation_ids) != evaluation_count:
            raise ValueError("sample identities must be unique within each split")
        if fit_ids & evaluation_ids:
            raise ValueError("fit and evaluation sample identities must be disjoint")
        if np.unique(self.fit_angles_rad).shape[0] != fit_count:
            raise ValueError("fit quadrature angles must be unique")
        if np.unique(self.evaluation_angles_rad).shape[0] != evaluation_count:
            raise ValueError("evaluation quadrature angles must be unique")
        if np.intersect1d(
            self.fit_angles_rad,
            self.evaluation_angles_rad,
        ).size:
            raise ValueError("fit and evaluation quadrature locations must be disjoint")

        expected_id = _label_free_content_pseudonym(
            row_ids=self.row_ids,
            states=self.states,
            site_coordinates=self.site_coordinates,
            oriented_faces=self.oriented_faces,
            fit_sample_ids=self.fit_sample_ids,
            fit_angles_rad=self.fit_angles_rad,
            fit_values=self.fit_values,
            evaluation_sample_ids=self.evaluation_sample_ids,
            evaluation_angles_rad=self.evaluation_angles_rad,
            evaluation_values=self.evaluation_values,
        )
        if self.input_id != expected_id:
            raise ValueError("input_id does not match estimator-observable content")

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "input_id": self.input_id,
            "arrays": {
                item.name: _array_fingerprint(getattr(self, item.name))
                for item in fields(self)
                if item.name in self._ARRAY_LAYOUT
            },
            "truth_present": False,
            "case_id_present": False,
            "disposition_present": False,
            "center_anchor_present": False,
            "charge_present": False,
            "expected_loop_response_present": False,
            "semantic_labels_present": False,
            "subject_values_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _optional_integer(value: object, *, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, np.integer),
    ):
        raise TypeError(f"{label} must be an integer or None")
    return int(value)


def evaluate_oracle_sampled_response(
    coordinates: FloatArray,
    loop_rows: Int64Array,
) -> int:
    """Evaluate one declared synthetic loop against evaluator-only truth.

    This helper is an oracle-side target calculation.  It is never an
    estimator output, integer-claim authority, or topology certificate.
    """

    values = coordinates[loop_rows, 0] + 1j * coordinates[loop_rows, 1]
    amplitudes = np.abs(values)
    if np.any(amplitudes <= 0.0):
        raise ValueError("oracle loop contains undefined zero-amplitude direction")
    increments = np.angle(np.roll(values, -1) * np.conjugate(values))
    if float(np.max(np.abs(increments))) >= np.pi - 1e-12:
        raise ValueError("oracle loop has a branch-ambiguous edge")
    cycles = float(np.sum(increments, dtype=np.float64) / (2.0 * np.pi))
    nearest = int(np.rint(cycles))
    if abs(cycles - nearest) > 1e-10:
        raise ValueError("oracle loop does not have an integer sampled response")
    return nearest


@dataclass(frozen=True, slots=True)
class CartesianFourierOracleTruth:
    """Evaluator-only field, anchor, and expected sampled responses."""

    truth_id: str
    row_ids: Int64Array
    disposition: CartesianExpectedDisposition
    f2_coordinates: FloatArray
    f2_amplitude: FloatArray
    f2_support: BoolArray
    f2_reason_codes: tuple[str, ...]
    f4_coordinates: FloatArray
    f4_amplitude: FloatArray
    f4_support: BoolArray
    f4_reason_codes: tuple[str, ...]
    geometric_center_mask: BoolArray
    core_anchor_mask: BoolArray
    outer_loop_vertex_rows: Int64Array
    central_loop_vertex_rows: Int64Array
    offcore_loop_vertex_rows: Int64Array
    supplied_charge: int | None
    expected_outer_sampled_winding: int | None
    expected_central_sampled_winding: int | None
    expected_offcore_sampled_winding: int | None

    _ARRAY_LAYOUT: ClassVar[dict[str, tuple[np.dtype[object], int]]] = {
        "row_ids": (_INT64, 1),
        "f2_coordinates": (_FLOAT, 2),
        "f2_amplitude": (_FLOAT, 1),
        "f2_support": (_BOOL, 1),
        "f4_coordinates": (_FLOAT, 2),
        "f4_amplitude": (_FLOAT, 1),
        "f4_support": (_BOOL, 1),
        "geometric_center_mask": (_BOOL, 1),
        "core_anchor_mask": (_BOOL, 1),
        "outer_loop_vertex_rows": (_INT64, 1),
        "central_loop_vertex_rows": (_INT64, 1),
        "offcore_loop_vertex_rows": (_INT64, 1),
    }

    receipt_version: ClassVar[str] = (
        "spirallens.cartesian-fourier-oracle-truth-receipt.v0.2"
    )

    def __post_init__(self) -> None:
        if not isinstance(self.truth_id, str) or not self.truth_id:
            raise ValueError("truth_id must be a nonempty string")
        if not isinstance(self.disposition, CartesianExpectedDisposition):
            raise TypeError("disposition must be a CartesianExpectedDisposition")
        for name, (dtype, ndim) in self._ARRAY_LAYOUT.items():
            object.__setattr__(
                self,
                name,
                _frozen(
                    getattr(self, name),
                    dtype=dtype,
                    ndim=ndim,
                    label=name,
                ),
            )
        rows = self.row_ids.shape[0]
        if rows == 0 or len(set(self.row_ids.tolist())) != rows:
            raise ValueError("oracle row_ids must be nonempty and unique")
        expected_shapes = {
            "f2_coordinates": (rows, 2),
            "f2_amplitude": (rows,),
            "f2_support": (rows,),
            "f4_coordinates": (rows, 2),
            "f4_amplitude": (rows,),
            "f4_support": (rows,),
            "geometric_center_mask": (rows,),
            "core_anchor_mask": (rows,),
        }
        for name, shape in expected_shapes.items():
            if getattr(self, name).shape != shape:
                raise ValueError(f"{name} has the wrong shape")
        if np.count_nonzero(self.geometric_center_mask) != 1:
            raise ValueError("geometric_center_mask must identify exactly one row")
        center_row = int(np.flatnonzero(self.geometric_center_mask)[0])
        expected_core_anchor_count = (
            1
            if self.disposition
            in {
                CartesianExpectedDisposition.NONZERO_WITH_CORE,
                CartesianExpectedDisposition.NULL_WITH_CORE,
            }
            else 0
        )
        if np.count_nonzero(self.core_anchor_mask) != expected_core_anchor_count:
            raise ValueError("core_anchor_mask disagrees with the joint control")
        if np.any(self.core_anchor_mask & ~self.geometric_center_mask):
            raise ValueError("core anchor must be the geometric center")

        for name in (
            "outer_loop_vertex_rows",
            "central_loop_vertex_rows",
            "offcore_loop_vertex_rows",
        ):
            loop = getattr(self, name)
            if loop.shape[0] < 3 or len(set(loop.tolist())) != loop.shape[0]:
                raise ValueError(f"{name} must contain at least three unique rows")
            if np.any(loop < 0) or np.any(loop >= rows):
                raise ValueError(f"{name} contains an out-of-range row")
            if center_row in set(loop.tolist()):
                raise ValueError(f"{name} must not sample the supplied center row")

        if len(self.f2_reason_codes) != rows or len(self.f4_reason_codes) != rows:
            raise ValueError("reason codes must contain one value per row")
        if not isinstance(self.f2_reason_codes, tuple) or not isinstance(
            self.f4_reason_codes,
            tuple,
        ):
            raise TypeError("reason codes must be tuples")
        if any(
            not isinstance(code, str) or not code
            for code in (*self.f2_reason_codes, *self.f4_reason_codes)
        ):
            raise ValueError("reason codes must be nonempty strings")

        expected_f2_amplitude = np.linalg.norm(self.f2_coordinates, axis=1)
        expected_f4_amplitude = np.linalg.norm(self.f4_coordinates, axis=1)
        if not np.array_equal(self.f2_amplitude, expected_f2_amplitude):
            raise ValueError("f2_amplitude must derive from f2_coordinates")
        if not np.array_equal(self.f4_amplitude, expected_f4_amplitude):
            raise ValueError("f4_amplitude must derive from f4_coordinates")
        if not np.array_equal(self.f2_support, self.f2_amplitude > 0.0):
            raise ValueError("f2_support must equal positive first-moment amplitude")
        if not np.array_equal(self.f4_support, self.f4_amplitude > 0.0):
            raise ValueError("f4_support must equal positive second-moment amplitude")
        for prefix, support, reasons, failure_reason in (
            (
                "f2",
                self.f2_support,
                self.f2_reason_codes,
                "zero_first_moment_direction_undefined",
            ),
            (
                "f4",
                self.f4_support,
                self.f4_reason_codes,
                "isotropic_second_moment_director_undefined",
            ),
        ):
            expected_reasons = tuple(
                "ok" if bool(item) else failure_reason for item in support
            )
            if reasons != expected_reasons:
                raise ValueError(f"{prefix} support and reason codes disagree")

        supplied = _optional_integer(
            self.supplied_charge,
            label="supplied_charge",
        )
        outer = _optional_integer(
            self.expected_outer_sampled_winding,
            label="expected_outer_sampled_winding",
        )
        central = _optional_integer(
            self.expected_central_sampled_winding,
            label="expected_central_sampled_winding",
        )
        offcore = _optional_integer(
            self.expected_offcore_sampled_winding,
            label="expected_offcore_sampled_winding",
        )
        object.__setattr__(self, "supplied_charge", supplied)
        object.__setattr__(self, "expected_outer_sampled_winding", outer)
        object.__setattr__(self, "expected_central_sampled_winding", central)
        object.__setattr__(self, "expected_offcore_sampled_winding", offcore)

        if self.disposition is CartesianExpectedDisposition.NONZERO_WITH_CORE:
            expected_responses = (1, 1, 1, 0)
        elif self.disposition in {
            CartesianExpectedDisposition.NULL_WITH_CORE,
            CartesianExpectedDisposition.NULL_WITHOUT_CORE,
        }:
            expected_responses = (0, 0, 0, 0)
        else:
            expected_responses = (None, None, None, None)
        if (supplied, outer, central, offcore) != expected_responses:
            raise ValueError(
                "supplied charge and expected sampled responses disagree "
                "with the disposition"
            )

        if self.disposition is CartesianExpectedDisposition.PREREQUISITE_FAILURE:
            if np.any(self.f2_support) or np.any(self.f4_support):
                raise ValueError(
                    "prerequisite-failure truth must have no supported moments"
                )
        elif self.disposition in {
            CartesianExpectedDisposition.NONZERO_WITH_CORE,
            CartesianExpectedDisposition.NULL_WITH_CORE,
        }:
            expected_unsupported = self.core_anchor_mask
            if not np.array_equal(~self.f2_support, expected_unsupported):
                raise ValueError(
                    "with-core first moment must vanish only at the anchor"
                )
            if not np.array_equal(~self.f4_support, expected_unsupported):
                raise ValueError(
                    "with-core second moment must vanish only at the anchor"
                )
        else:
            if not np.all(self.f2_support) or not np.all(self.f4_support):
                raise ValueError(
                    "without-core null must have supported moments everywhere"
                )

        if self.disposition is not CartesianExpectedDisposition.PREREQUISITE_FAILURE:
            observed = (
                evaluate_oracle_sampled_response(
                    self.f2_coordinates,
                    self.outer_loop_vertex_rows,
                ),
                evaluate_oracle_sampled_response(
                    self.f2_coordinates,
                    self.central_loop_vertex_rows,
                ),
                evaluate_oracle_sampled_response(
                    self.f2_coordinates,
                    self.offcore_loop_vertex_rows,
                ),
            )
            if observed != (outer, central, offcore):
                raise ValueError(
                    "expected sampled responses differ from the supplied truth"
                )
            if not np.all(self.f2_support[self.offcore_loop_vertex_rows]):
                raise ValueError("the off-core loop must have defined direction")

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "truth_id": self.truth_id,
            "disposition": self.disposition.value,
            "arrays": {
                item.name: _array_fingerprint(getattr(self, item.name))
                for item in fields(self)
                if item.name in self._ARRAY_LAYOUT
            },
            "f2_reason_codes": list(self.f2_reason_codes),
            "f4_reason_codes": list(self.f4_reason_codes),
            "supplied_charge": self.supplied_charge,
            "expected_outer_sampled_winding": (self.expected_outer_sampled_winding),
            "expected_central_sampled_winding": (self.expected_central_sampled_winding),
            "expected_offcore_sampled_winding": (self.expected_offcore_sampled_winding),
            "oracle_is_estimator_input": False,
            "anchor_is_localization_gate_result": False,
            "sampled_responses_are_supplied_truth_not_observed_results": True,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _observed_moment_coordinates(
    *,
    angles: FloatArray,
    values: FloatArray,
    harmonic: int,
) -> FloatArray:
    centered = values - np.mean(values, axis=1, keepdims=True)
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


def _require_observed_truth_relation(
    inputs: CartesianFourierEstimatorInputs,
    truth: CartesianFourierOracleTruth,
    *,
    observation_noise_scale: float,
) -> None:
    maximum_f2_residual = 0.0
    for split_name, angles, values in (
        ("fit", inputs.fit_angles_rad, inputs.fit_values),
        (
            "evaluation",
            inputs.evaluation_angles_rad,
            inputs.evaluation_values,
        ),
    ):
        scale = max(1.0, float(np.max(np.abs(values))))
        tolerance = CARTESIAN_FOURIER_RELATION_ATOL * scale
        observed_f2 = _observed_moment_coordinates(
            angles=angles,
            values=values,
            harmonic=1,
        )
        observed_f4 = _observed_moment_coordinates(
            angles=angles,
            values=values,
            harmonic=2,
        )
        f2_residual = float(np.max(np.abs(observed_f2 - truth.f2_coordinates)))
        f4_residual = float(np.max(np.abs(observed_f4 - truth.f4_coordinates)))
        maximum_f2_residual = max(maximum_f2_residual, f2_residual)
        allowed = tolerance + 4.0 * observation_noise_scale
        if f2_residual > allowed:
            raise ValueError(
                f"{split_name} observations exceed the declared f2 noise bound"
            )
        if f4_residual > allowed:
            raise ValueError(
                f"{split_name} observations exceed the declared f4 noise bound"
            )
    if (
        observation_noise_scale > 0.0
        and truth.disposition is not CartesianExpectedDisposition.PREREQUISITE_FAILURE
        and maximum_f2_residual <= observation_noise_scale * 1e-3
    ):
        raise ValueError(
            "declared observation noise is vacuous for the target first moment"
        )


@dataclass(frozen=True, slots=True)
class CartesianFourierCase:
    """Evaluator-side linkage; the estimator sees only ``estimator_inputs``."""

    case_id: str
    estimator_inputs: CartesianFourierEstimatorInputs
    oracle_truth: CartesianFourierOracleTruth
    observation_noise_scale: float

    receipt_version: ClassVar[str] = "spirallens.cartesian-fourier-case-receipt.v0.2"

    def __post_init__(self) -> None:
        expected = {
            CARTESIAN_FOURIER_POSITIVE: (
                CartesianExpectedDisposition.NONZERO_WITH_CORE
            ),
            CARTESIAN_FOURIER_FIXED_NULL: (CartesianExpectedDisposition.NULL_WITH_CORE),
            CARTESIAN_FOURIER_NO_CORE_NULL: (
                CartesianExpectedDisposition.NULL_WITHOUT_CORE
            ),
            CARTESIAN_FOURIER_PREREQUISITE_FAILURE: (
                CartesianExpectedDisposition.PREREQUISITE_FAILURE
            ),
        }.get(self.case_id)
        if expected is None:
            raise ValueError("unsupported Cartesian Fourier case_id")
        if not isinstance(
            self.estimator_inputs,
            CartesianFourierEstimatorInputs,
        ):
            raise TypeError("estimator_inputs must be CartesianFourierEstimatorInputs")
        if not isinstance(self.oracle_truth, CartesianFourierOracleTruth):
            raise TypeError("oracle_truth must be CartesianFourierOracleTruth")
        if self.oracle_truth.disposition is not expected:
            raise ValueError("case_id and evaluator disposition disagree")
        noise_scale = _real(
            self.observation_noise_scale,
            label="observation_noise_scale",
            positive=False,
        )
        object.__setattr__(
            self,
            "observation_noise_scale",
            noise_scale,
        )
        if not np.array_equal(
            self.estimator_inputs.row_ids,
            self.oracle_truth.row_ids,
        ):
            raise ValueError(
                "estimator inputs and truth require identical ordered row identities"
            )
        _require_observed_truth_relation(
            self.estimator_inputs,
            self.oracle_truth,
            observation_noise_scale=(
                0.0
                if self.oracle_truth.disposition
                is CartesianExpectedDisposition.PREREQUISITE_FAILURE
                else noise_scale
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "case_id": self.case_id,
            "estimator_inputs_fingerprint_sha256": (
                self.estimator_inputs.fingerprint_sha256
            ),
            "oracle_truth_fingerprint_sha256": (self.oracle_truth.fingerprint_sha256),
            "observation_noise_scale": self.observation_noise_scale,
            "target_visible_noise_required_when_nonzero": True,
            "truth_separated_from_estimator_inputs": True,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class CartesianFourierDomainPhantom:
    """Four deterministic joint core/loop controls and source identity."""

    spec: CartesianFourierDomainSpec
    family_identity: GeneratorFamilyIdentity
    cases: tuple[CartesianFourierCase, ...]

    receipt_version: ClassVar[str] = (
        "spirallens.cartesian-fourier-domain-phantom-receipt.v0.2"
    )

    def __post_init__(self) -> None:
        if not isinstance(self.spec, CartesianFourierDomainSpec):
            raise TypeError("spec must be a CartesianFourierDomainSpec")
        if not isinstance(self.family_identity, GeneratorFamilyIdentity):
            raise TypeError("family_identity must be a GeneratorFamilyIdentity")
        if self.family_identity != _family_identity():
            raise ValueError(
                "family_identity must equal the canonical source-bound "
                "Cartesian Fourier identity"
            )
        if not isinstance(self.cases, tuple) or any(
            not isinstance(case, CartesianFourierCase) for case in self.cases
        ):
            raise TypeError("cases must be a tuple of CartesianFourierCase values")
        expected_ids = (
            CARTESIAN_FOURIER_POSITIVE,
            CARTESIAN_FOURIER_FIXED_NULL,
            CARTESIAN_FOURIER_NO_CORE_NULL,
            CARTESIAN_FOURIER_PREREQUISITE_FAILURE,
        )
        if tuple(case.case_id for case in self.cases) != expected_ids:
            raise ValueError("Cartesian Fourier cases are not in canonical order")
        if len({case.estimator_inputs.input_id for case in self.cases}) != len(
            self.cases
        ):
            raise ValueError("estimator input pseudonyms must be unique")
        expected = _canonical_cases(self.spec)
        if tuple(case.to_dict() for case in self.cases) != tuple(
            case.to_dict() for case in expected
        ):
            raise ValueError("Cartesian Fourier cases do not match the canonical spec")

    @property
    def positive(self) -> CartesianFourierCase:
        return self.cases[0]

    @property
    def fixed_null(self) -> CartesianFourierCase:
        return self.cases[1]

    @property
    def prerequisite_failure(self) -> CartesianFourierCase:
        return self.cases[3]

    @property
    def no_core_null(self) -> CartesianFourierCase:
        return self.cases[2]

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "claim_scope": "model-free-level-0-development-controls-only",
            "claim_ceiling": "level_0",
            "spec": self.spec.to_dict(),
            "family_identity": self.family_identity.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
            "graph_constructed": False,
            "core_localized": False,
            "loop_constructed": False,
            "sampled_winding_observed": False,
            "integer_output_authorized": False,
            "qualification_gate_evaluated": False,
            "d0_d8_advanced": False,
            "subject_access_authorized": False,
            "semantic_or_sae_labels_present": False,
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
        family_id="cartesian-fourier-domain-v0.1",
        construction_family_id="cartesian-fourier-quadrature-lattice",
        implementation_id="numpy-cartesian-fourier-domain",
        implementation_version="v0.2",
        source_sha256=_module_sha256(),
    )


def _canonical_coordinates(side: int) -> FloatArray:
    radius = side // 2
    axis = np.arange(-radius, radius + 1, dtype=_FLOAT) / float(radius)
    return np.asarray(
        [(x, y) for y in axis for x in axis],
        dtype=_FLOAT,
    )


def _warped_coordinates(
    coordinates: FloatArray,
    strength: float,
) -> FloatArray:
    return np.asarray(
        coordinates + strength * np.sin(np.pi * coordinates) / np.pi,
        dtype=_FLOAT,
    )


def _deterministic_signed_permutation(
    dimension: int,
    *,
    seed: int,
) -> tuple[Int64Array, FloatArray]:
    """Return an O(d)-storage orthogonal coordinate mixing."""

    rng = np.random.default_rng(seed)
    permutation = np.asarray(rng.permutation(dimension), dtype=_INT64)
    sign_bits = rng.integers(0, 2, size=dimension, dtype=np.int8)
    signs = np.where(sign_bits == 0, -1.0, 1.0).astype(_FLOAT, copy=False)
    return permutation, signs


def _state_embedding(
    spec: CartesianFourierDomainSpec,
    coordinates: FloatArray,
) -> FloatArray:
    warped = _warped_coordinates(
        coordinates,
        spec.density_warp_strength,
    )
    state_coordinates = np.array(warped, dtype=_FLOAT, order="C", copy=True)
    state_coordinates[:, 1] += CARTESIAN_FOURIER_STATE_SHEAR * state_coordinates[:, 0]
    features = np.zeros(
        (coordinates.shape[0], spec.ambient_dimension),
        dtype=_FLOAT,
    )
    features[:, :2] = state_coordinates
    for column in range(2, spec.ambient_dimension):
        frequency = 1 + (column - 2) // 4
        mode = (column - 2) % 4
        if mode == 0:
            values = np.sin(frequency * np.pi * state_coordinates[:, 0])
        elif mode == 1:
            values = np.cos(frequency * np.pi * state_coordinates[:, 0])
        elif mode == 2:
            values = np.sin(frequency * np.pi * state_coordinates[:, 1])
        else:
            values = np.cos(frequency * np.pi * state_coordinates[:, 1])
        values = values - values.mean()
        features[:, column] = CARTESIAN_FOURIER_STATE_NUISANCE_SCALE * values
    permutation, signs = _deterministic_signed_permutation(
        spec.ambient_dimension,
        seed=spec.seed ^ 0x43A71E,
    )
    mixed = np.take(features, permutation, axis=1)
    mixed *= signs
    mixed[mixed == 0.0] = 0.0
    return np.asarray(mixed, dtype=_FLOAT)


def _oriented_grid_faces(side: int) -> Int64Array:
    faces: list[tuple[int, int, int]] = []
    for y in range(side - 1):
        for x in range(side - 1):
            lower_left = y * side + x
            lower_right = lower_left + 1
            upper_left = lower_left + side
            upper_right = upper_left + 1
            faces.extend(
                (
                    (lower_left, lower_right, upper_right),
                    (lower_left, upper_right, upper_left),
                )
            )
    return np.asarray(faces, dtype=_INT64)


def _rectangular_loop_rows(
    side: int,
    *,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> Int64Array:
    if not (0 <= x0 < x1 < side and 0 <= y0 < y1 < side):
        raise ValueError("rectangle lies outside the grid")
    rows: list[int] = []
    rows.extend(y0 * side + x for x in range(x0, x1 + 1))
    rows.extend(y * side + x1 for y in range(y0 + 1, y1 + 1))
    rows.extend(y1 * side + x for x in range(x1 - 1, x0 - 1, -1))
    rows.extend(y * side + x0 for y in range(y1 - 1, y0, -1))
    return np.asarray(rows, dtype=_INT64)


def _loop_truth(side: int) -> tuple[Int64Array, Int64Array, Int64Array]:
    center = side // 2
    outer = _rectangular_loop_rows(
        side,
        x0=0,
        y0=0,
        x1=side - 1,
        y1=side - 1,
    )
    central = _rectangular_loop_rows(
        side,
        x0=center - 1,
        y0=center - 1,
        x1=center + 1,
        y1=center + 1,
    )
    offcore = _rectangular_loop_rows(
        side,
        x0=0,
        y0=0,
        x1=1,
        y1=1,
    )
    return outer, central, offcore


def _split_quadrature(
    samples_per_split: int,
) -> tuple[Int64Array, FloatArray, Int64Array, FloatArray]:
    total = 2 * samples_per_split
    all_ids = np.arange(total, dtype=_INT64)
    all_angles = 2.0 * np.pi * all_ids.astype(_FLOAT) / float(total)
    return (
        all_ids[0::2],
        all_angles[0::2],
        all_ids[1::2],
        all_angles[1::2],
    )


def _noise_phase(spec: CartesianFourierDomainSpec) -> FloatArray:
    row_ids = np.arange(spec.row_count, dtype=_INT64)
    numerators = (37 * row_ids + (spec.seed % 1009)) % 1009
    return np.asarray(
        2.0 * np.pi * numerators.astype(_FLOAT) / 1009.0,
        dtype=_FLOAT,
    )


def _values(
    spec: CartesianFourierDomainSpec,
    *,
    angles: FloatArray,
    radial_amplitude: FloatArray,
    orientation: FloatArray,
    disposition: CartesianExpectedDisposition,
) -> FloatArray:
    if disposition is CartesianExpectedDisposition.PREREQUISITE_FAILURE:
        first = np.zeros_like(radial_amplitude)
        second = np.zeros_like(radial_amplitude)
        noise = np.zeros(
            (radial_amplitude.shape[0], angles.shape[0]),
            dtype=_FLOAT,
        )
    else:
        first = radial_amplitude
        second = spec.second_harmonic_scale * radial_amplitude
        noise = spec.noise_scale * np.cos(
            math.sqrt(2.0) * angles[None, :] + _noise_phase(spec)[:, None]
        )
    relative = angles[None, :] - orientation[:, None]
    return np.asarray(
        spec.baseline
        + first[:, None] * np.cos(relative)
        + second[:, None] * np.cos(2.0 * relative)
        + noise,
        dtype=_FLOAT,
    )


def _case(
    spec: CartesianFourierDomainSpec,
    *,
    case_id: str,
    disposition: CartesianExpectedDisposition,
    coordinates: FloatArray,
    states: FloatArray,
    oriented_faces: Int64Array,
) -> CartesianFourierCase:
    row_ids = np.arange(spec.row_count, dtype=_INT64)
    radius = np.linalg.norm(coordinates, axis=1)
    if disposition is CartesianExpectedDisposition.NULL_WITHOUT_CORE:
        radial_amplitude = np.ones(spec.row_count, dtype=_FLOAT)
    elif disposition is CartesianExpectedDisposition.PREREQUISITE_FAILURE:
        radial_amplitude = np.zeros(spec.row_count, dtype=_FLOAT)
    else:
        radial_amplitude = np.tanh(radius)
    if disposition is CartesianExpectedDisposition.NONZERO_WITH_CORE:
        orientation = np.arctan2(coordinates[:, 1], coordinates[:, 0])
    else:
        orientation = np.zeros(spec.row_count, dtype=_FLOAT)
    fit_ids, fit_angles, evaluation_ids, evaluation_angles = _split_quadrature(
        spec.samples_per_split
    )
    fit_values = _values(
        spec,
        angles=fit_angles,
        radial_amplitude=radial_amplitude,
        orientation=orientation,
        disposition=disposition,
    )
    evaluation_values = _values(
        spec,
        angles=evaluation_angles,
        radial_amplitude=radial_amplitude,
        orientation=orientation,
        disposition=disposition,
    )
    input_id = _label_free_content_pseudonym(
        row_ids=row_ids,
        states=states,
        site_coordinates=coordinates,
        oriented_faces=oriented_faces,
        fit_sample_ids=fit_ids,
        fit_angles_rad=fit_angles,
        fit_values=fit_values,
        evaluation_sample_ids=evaluation_ids,
        evaluation_angles_rad=evaluation_angles,
        evaluation_values=evaluation_values,
    )
    estimator_inputs = CartesianFourierEstimatorInputs(
        input_id=input_id,
        row_ids=row_ids,
        states=states,
        site_coordinates=coordinates,
        oriented_faces=oriented_faces,
        fit_sample_ids=fit_ids,
        fit_angles_rad=fit_angles,
        fit_values=fit_values,
        evaluation_sample_ids=evaluation_ids,
        evaluation_angles_rad=evaluation_angles,
        evaluation_values=evaluation_values,
    )

    if disposition is CartesianExpectedDisposition.PREREQUISITE_FAILURE:
        f2_coordinates = np.zeros((spec.row_count, 2), dtype=_FLOAT)
        f4_coordinates = np.zeros((spec.row_count, 2), dtype=_FLOAT)
    else:
        f2_coordinates = radial_amplitude[:, None] * np.column_stack(
            (np.cos(orientation), np.sin(orientation))
        )
        f4_coordinates = (
            spec.second_harmonic_scale
            * radial_amplitude[:, None]
            * np.column_stack(
                (
                    np.cos(2.0 * orientation),
                    np.sin(2.0 * orientation),
                )
            )
        )
    f2_amplitude = np.linalg.norm(f2_coordinates, axis=1)
    f4_amplitude = np.linalg.norm(f4_coordinates, axis=1)
    f2_support = f2_amplitude > 0.0
    f4_support = f4_amplitude > 0.0
    geometric_center = np.all(coordinates == 0.0, axis=1)
    core_anchor = (
        geometric_center
        if disposition
        in {
            CartesianExpectedDisposition.NONZERO_WITH_CORE,
            CartesianExpectedDisposition.NULL_WITH_CORE,
        }
        else np.zeros(spec.row_count, dtype=_BOOL)
    )
    outer, central, offcore = _loop_truth(spec.grid_side)
    if disposition is CartesianExpectedDisposition.NONZERO_WITH_CORE:
        supplied_charge: int | None = 1
        expected_outer: int | None = 1
        expected_central: int | None = 1
        expected_offcore: int | None = 0
    elif disposition in {
        CartesianExpectedDisposition.NULL_WITH_CORE,
        CartesianExpectedDisposition.NULL_WITHOUT_CORE,
    }:
        supplied_charge = 0
        expected_outer = 0
        expected_central = 0
        expected_offcore = 0
    else:
        supplied_charge = None
        expected_outer = None
        expected_central = None
        expected_offcore = None
    truth = CartesianFourierOracleTruth(
        truth_id=f"cartesian-fourier-truth-{case_id}",
        row_ids=row_ids,
        disposition=disposition,
        f2_coordinates=f2_coordinates,
        f2_amplitude=f2_amplitude,
        f2_support=f2_support,
        f2_reason_codes=tuple(
            "ok" if bool(item) else "zero_first_moment_direction_undefined"
            for item in f2_support
        ),
        f4_coordinates=f4_coordinates,
        f4_amplitude=f4_amplitude,
        f4_support=f4_support,
        f4_reason_codes=tuple(
            "ok" if bool(item) else "isotropic_second_moment_director_undefined"
            for item in f4_support
        ),
        geometric_center_mask=geometric_center,
        core_anchor_mask=core_anchor,
        outer_loop_vertex_rows=outer,
        central_loop_vertex_rows=central,
        offcore_loop_vertex_rows=offcore,
        supplied_charge=supplied_charge,
        expected_outer_sampled_winding=expected_outer,
        expected_central_sampled_winding=expected_central,
        expected_offcore_sampled_winding=expected_offcore,
    )
    return CartesianFourierCase(
        case_id=case_id,
        estimator_inputs=estimator_inputs,
        oracle_truth=truth,
        observation_noise_scale=spec.noise_scale,
    )


def _canonical_cases(
    spec: CartesianFourierDomainSpec,
) -> tuple[
    CartesianFourierCase,
    CartesianFourierCase,
    CartesianFourierCase,
    CartesianFourierCase,
]:
    coordinates = _canonical_coordinates(spec.grid_side)
    states = _state_embedding(spec, coordinates)
    faces = _oriented_grid_faces(spec.grid_side)
    return (
        _case(
            spec,
            case_id=CARTESIAN_FOURIER_POSITIVE,
            disposition=CartesianExpectedDisposition.NONZERO_WITH_CORE,
            coordinates=coordinates,
            states=states,
            oriented_faces=faces,
        ),
        _case(
            spec,
            case_id=CARTESIAN_FOURIER_FIXED_NULL,
            disposition=CartesianExpectedDisposition.NULL_WITH_CORE,
            coordinates=coordinates,
            states=states,
            oriented_faces=faces,
        ),
        _case(
            spec,
            case_id=CARTESIAN_FOURIER_NO_CORE_NULL,
            disposition=CartesianExpectedDisposition.NULL_WITHOUT_CORE,
            coordinates=coordinates,
            states=states,
            oriented_faces=faces,
        ),
        _case(
            spec,
            case_id=CARTESIAN_FOURIER_PREREQUISITE_FAILURE,
            disposition=CartesianExpectedDisposition.PREREQUISITE_FAILURE,
            coordinates=coordinates,
            states=states,
            oriented_faces=faces,
        ),
    )


class CartesianFourierDomainGenerator:
    """Generate the bounded Cartesian Fourier positive/null/failure controls."""

    @property
    def family_identity(self) -> GeneratorFamilyIdentity:
        return _family_identity()

    def generate(
        self,
        spec: CartesianFourierDomainSpec,
    ) -> CartesianFourierDomainPhantom:
        if not isinstance(spec, CartesianFourierDomainSpec):
            raise TypeError("spec must be a CartesianFourierDomainSpec")
        return CartesianFourierDomainPhantom(
            spec=spec,
            family_identity=self.family_identity,
            cases=_canonical_cases(spec),
        )
