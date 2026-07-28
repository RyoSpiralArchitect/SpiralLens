"""Deterministic spectral-moment quadrature development generator.

This generator is a separately implemented, declared mathematical
construction family from the existing representation phantom.  It creates
scalar quadrature observations whose first and second Fourier moments have
declared F2- and F4-shaped oracle targets.  The estimator-facing inputs and
oracle truth are separate typed objects.  Its distinct family metadata is a
necessary comparison gate, not proof of epistemic or implementation
independence.

The outputs are model-free development controls.  They construct no graph,
core, loop, winding, qualification gate, or subject evidence.
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

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)

from .generators import GeneratorFamilyIdentity

SPECTRAL_MOMENT_PHANTOM_RECEIPT_VERSION = (
    "spirallens.spectral-moment-phantom-receipt.v0.1"
)

SPECTRAL_MOMENT_POSITIVE = "spectral-moment-positive"
SPECTRAL_MOMENT_FIXED_NULL = "spectral-moment-fixed-null"
SPECTRAL_MOMENT_PREREQUISITE_FAILURE = "spectral-moment-prerequisite-failure"

SPECTRAL_MOMENT_RESOURCE_ESTIMATOR_ID = "spectral-moment-conservative-peak-v0.1"
SPECTRAL_MOMENT_RESOURCE_SAFETY_FACTOR = 4
MAX_SPECTRAL_MOMENT_ESTIMATED_PEAK_BYTES = 256 * 1024 * 1024
SPECTRAL_MOMENT_MIN_HARMONIC_SIGNAL_RATIO = 1e-6
SPECTRAL_MOMENT_MIN_ABSOLUTE_SIGNAL = 16.0 * math.sqrt(np.finfo(np.float64).tiny)
SPECTRAL_MOMENT_MAX_SAFE_SCALAR_SCALE = math.sqrt(np.finfo(np.float64).max) / 16.0
_SPECTRAL_MOMENT_BASE_OVERHEAD_BYTES = 1024 * 1024
_SPECTRAL_MOMENT_BASE_CELL_BYTES = 128
_SPECTRAL_MOMENT_BASE_ROW_BYTES = 1024
_SPECTRAL_MOMENT_BASE_SAMPLE_BYTES = 1024
SPECTRAL_MOMENT_RELATION_RTOL = 1e-9
SPECTRAL_MOMENT_RELATION_ATOL = 64.0 * np.finfo(np.float64).eps

_FLOAT = np.dtype("<f8")
_INT64 = np.dtype("<i8")
_BOOL = np.dtype("|b1")
_CONTENT_PSEUDONYM = re.compile(r"^smi_[0-9a-f]{32}$")

FloatArray = NDArray[np.float64]
Int64Array = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


class ExpectedControlDisposition(str, Enum):
    """Declared development-control role, not a D-gate result."""

    POSITIVE = "positive"
    NULL = "null"
    PREREQUISITE_FAILURE = "prerequisite_failure"


def _integer(value: object, *, label: str, minimum: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{label} must be an integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return result


def _positive_real(value: object, *, label: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise TypeError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{label} must be finite and positive")
    return result


def _estimated_peak_bytes(*, row_count: int, samples_per_split: int) -> int:
    """Conservatively bound retained cases, validation copies, and temporaries."""

    base = (
        _SPECTRAL_MOMENT_BASE_OVERHEAD_BYTES
        + _SPECTRAL_MOMENT_BASE_CELL_BYTES * row_count * samples_per_split
        + _SPECTRAL_MOMENT_BASE_ROW_BYTES * row_count
        + _SPECTRAL_MOMENT_BASE_SAMPLE_BYTES * samples_per_split
    )
    return SPECTRAL_MOMENT_RESOURCE_SAFETY_FACTOR * base


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
            raise TypeError(f"{label} must have a real floating dtype")
    elif dtype.kind == "i":
        if source.dtype.kind not in {"i", "u"}:
            raise TypeError(f"{label} must have an integer, non-boolean dtype")
        int64_info = np.iinfo(np.int64)
        if source.size and (
            (source.dtype.kind == "i" and np.any(source < int64_info.min))
            or np.any(source > int64_info.max)
        ):
            raise ValueError(f"{label} contains values outside int64 range")
    elif dtype.kind == "b":
        if source.dtype.kind != "b":
            raise TypeError(f"{label} must have a boolean dtype")
    else:  # pragma: no cover - all layouts are closed above
        raise TypeError(f"{label} has an unsupported expected dtype")

    result = np.array(source, dtype=dtype, order="C", copy=True)
    if dtype.kind == "i" and not np.array_equal(
        result.astype(source.dtype, copy=False),
        source,
    ):
        raise ValueError(f"{label} does not round-trip exactly through int64")
    if not result.flags.c_contiguous:
        result = np.ascontiguousarray(result, dtype=dtype)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must contain only finite values")
    backing = result.tobytes(order="C")
    return np.frombuffer(backing, dtype=dtype).reshape(result.shape)


def _array_sha256(value: NDArray[np.generic]) -> str:
    descriptor = (
        f"{value.dtype.str}|{','.join(str(item) for item in value.shape)}|"
    ).encode("ascii")
    return hashlib.sha256(descriptor + value.tobytes(order="C")).hexdigest()


@dataclass(frozen=True, slots=True)
class SpectralMomentPhantomSpec:
    """Bounded inputs for the spectral-moment quadrature construction."""

    seed: int = 2718
    row_count: int = 12
    samples_per_split: int = 8
    baseline: float = 1.25
    f2_amplitude: float = 0.8
    f4_amplitude: float = 0.35

    receipt_version: ClassVar[str] = (
        "spirallens.spectral-moment-phantom-spec-receipt.v0.1"
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "seed",
            _integer(self.seed, label="seed", minimum=0),
        )
        object.__setattr__(
            self,
            "row_count",
            _integer(self.row_count, label="row_count", minimum=4),
        )
        samples = _integer(
            self.samples_per_split,
            label="samples_per_split",
            minimum=8,
        )
        if samples % 4 != 0:
            raise ValueError("samples_per_split must be divisible by four")
        object.__setattr__(self, "samples_per_split", samples)
        estimated_peak = _estimated_peak_bytes(
            row_count=self.row_count,
            samples_per_split=samples,
        )
        if estimated_peak > MAX_SPECTRAL_MOMENT_ESTIMATED_PEAK_BYTES:
            raise ValueError(
                "spectral-moment estimated peak allocation exceeds the "
                "fixed 256 MiB cap"
            )
        for name in ("baseline", "f2_amplitude", "f4_amplitude"):
            object.__setattr__(
                self,
                name,
                _positive_real(getattr(self, name), label=name),
            )
        signal_scale = self.baseline + self.f2_amplitude + self.f4_amplitude
        if not math.isfinite(signal_scale):
            raise ValueError(
                "baseline and harmonic amplitudes must have a finite "
                "combined numerical scale"
            )
        if signal_scale > SPECTRAL_MOMENT_MAX_SAFE_SCALAR_SCALE:
            raise ValueError(
                "combined numerical scale exceeds the predeclared "
                "derived-arithmetic safety bound"
            )
        for name in ("f2_amplitude", "f4_amplitude"):
            amplitude = getattr(self, name)
            if (
                amplitude < SPECTRAL_MOMENT_MIN_ABSOLUTE_SIGNAL
                or amplitude / signal_scale < SPECTRAL_MOMENT_MIN_HARMONIC_SIGNAL_RATIO
            ):
                raise ValueError(
                    f"{name} is below the predeclared numerical resolvability floor"
                )

    def to_dict(self) -> dict[str, object]:
        """Return an in-memory fingerprint receipt, not a persistence form."""

        return {
            "receipt_version": self.receipt_version,
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "seed": self.seed,
            "row_count": self.row_count,
            "samples_per_split": self.samples_per_split,
            "baseline": self.baseline,
            "f2_amplitude": self.f2_amplitude,
            "f4_amplitude": self.f4_amplitude,
            "split_rule": "interleaved-uniform-quadrature-even-fit-odd-evaluation",
            "estimator_input_scope": "scalar-quadrature-observations-only",
            "oracle_scope": "separate-first-and-second-moment-targets",
            "resource_estimator_id": SPECTRAL_MOMENT_RESOURCE_ESTIMATOR_ID,
            "resource_safety_factor": SPECTRAL_MOMENT_RESOURCE_SAFETY_FACTOR,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "max_estimated_peak_bytes": (MAX_SPECTRAL_MOMENT_ESTIMATED_PEAK_BYTES),
            "resource_claim_boundary": (
                "parameter-induced-runaway-allocation-guard-not-os-oom-guarantee"
            ),
            "harmonic_signal_scale": (
                self.baseline + self.f2_amplitude + self.f4_amplitude
            ),
            "min_harmonic_signal_ratio": (SPECTRAL_MOMENT_MIN_HARMONIC_SIGNAL_RATIO),
            "min_absolute_signal": SPECTRAL_MOMENT_MIN_ABSOLUTE_SIGNAL,
            "max_safe_scalar_scale": SPECTRAL_MOMENT_MAX_SAFE_SCALAR_SCALE,
            "relation_relative_tolerance": SPECTRAL_MOMENT_RELATION_RTOL,
            "relation_zero_signal_absolute_multiplier": (SPECTRAL_MOMENT_RELATION_ATOL),
        }

    @property
    def receipt_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def receipt_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @property
    def estimated_peak_bytes(self) -> int:
        return _estimated_peak_bytes(
            row_count=self.row_count,
            samples_per_split=self.samples_per_split,
        )


@dataclass(frozen=True, slots=True)
class SpectralMomentEstimatorInputs:
    """Only the arrays an estimator is permitted to observe.

    ``input_id`` is a deterministic label-free content pseudonym derived only
    from the estimator-observable arrays.  It does not carry a case identifier
    or expected-control disposition; that mapping lives only in
    :class:`SpectralMomentCase`, the evaluator-side object.  This is not a
    claim of cryptographic blindness against an evaluator-aware estimator.
    """

    input_id: str
    row_ids: Int64Array
    fit_sample_ids: Int64Array
    fit_angles_rad: FloatArray
    fit_values: FloatArray
    evaluation_sample_ids: Int64Array
    evaluation_angles_rad: FloatArray
    evaluation_values: FloatArray

    _ARRAY_LAYOUT: ClassVar[dict[str, tuple[np.dtype[object], int]]] = {
        "row_ids": (_INT64, 1),
        "fit_sample_ids": (_INT64, 1),
        "fit_angles_rad": (_FLOAT, 1),
        "fit_values": (_FLOAT, 2),
        "evaluation_sample_ids": (_INT64, 1),
        "evaluation_angles_rad": (_FLOAT, 1),
        "evaluation_values": (_FLOAT, 2),
    }

    def __post_init__(self) -> None:
        if (
            not isinstance(self.input_id, str)
            or _CONTENT_PSEUDONYM.fullmatch(self.input_id) is None
        ):
            raise ValueError(
                "input_id must be a label-free spectral-moment content pseudonym"
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
        fit_count = self.fit_sample_ids.shape[0]
        evaluation_count = self.evaluation_sample_ids.shape[0]
        if rows == 0:
            raise ValueError("row identities must be nonempty")
        if fit_count == 0:
            raise ValueError("fit sample identities must be nonempty")
        if evaluation_count == 0:
            raise ValueError("evaluation sample identities must be nonempty")
        if self.fit_angles_rad.shape != (fit_count,):
            raise ValueError("fit angles and sample identities differ")
        if self.evaluation_angles_rad.shape != (evaluation_count,):
            raise ValueError("evaluation angles and sample identities differ")
        if self.fit_values.shape != (rows, fit_count):
            raise ValueError("fit_values shape differs from row/sample identities")
        if self.evaluation_values.shape != (rows, evaluation_count):
            raise ValueError(
                "evaluation_values shape differs from row/sample identities"
            )
        if len(set(self.row_ids.tolist())) != rows:
            raise ValueError("row_ids must be unique")
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
        expected_input_id = _label_free_content_pseudonym(
            row_ids=self.row_ids,
            fit_sample_ids=self.fit_sample_ids,
            fit_angles_rad=self.fit_angles_rad,
            fit_values=self.fit_values,
            evaluation_sample_ids=self.evaluation_sample_ids,
            evaluation_angles_rad=self.evaluation_angles_rad,
            evaluation_values=self.evaluation_values,
        )
        if self.input_id != expected_input_id:
            raise ValueError("input_id does not match the estimator-observable content")

    def to_dict(self) -> dict[str, object]:
        """Return an array-fingerprint receipt, not array serialization."""

        return {
            "receipt_version": (
                "spirallens.spectral-moment-estimator-inputs-receipt.v0.1"
            ),
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "input_id": self.input_id,
            "arrays": {
                item.name: {
                    "dtype": getattr(self, item.name).dtype.str,
                    "shape": list(getattr(self, item.name).shape),
                    "sha256": _array_sha256(getattr(self, item.name)),
                }
                for item in fields(self)
                if item.name in self._ARRAY_LAYOUT
            },
            "truth_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class SpectralMomentOracleTruth:
    """Held-aside expected first/second moments and prerequisite semantics."""

    truth_id: str
    row_ids: Int64Array
    f2_disposition: ExpectedControlDisposition
    f4_disposition: ExpectedControlDisposition
    f2_coordinates: FloatArray
    f2_amplitude: FloatArray
    f2_support: BoolArray
    f2_reason_codes: tuple[str, ...]
    f4_spin_two_coordinates: FloatArray
    f4_traceless_tensor: FloatArray
    f4_amplitude: FloatArray
    f4_support: BoolArray
    f4_reason_codes: tuple[str, ...]

    _ARRAY_LAYOUT: ClassVar[dict[str, tuple[np.dtype[object], int]]] = {
        "row_ids": (_INT64, 1),
        "f2_coordinates": (_FLOAT, 2),
        "f2_amplitude": (_FLOAT, 1),
        "f2_support": (_BOOL, 1),
        "f4_spin_two_coordinates": (_FLOAT, 2),
        "f4_traceless_tensor": (_FLOAT, 3),
        "f4_amplitude": (_FLOAT, 1),
        "f4_support": (_BOOL, 1),
    }

    def __post_init__(self) -> None:
        if not isinstance(self.truth_id, str) or not self.truth_id:
            raise ValueError("truth_id must be a non-empty string")
        for name in ("f2_disposition", "f4_disposition"):
            if not isinstance(getattr(self, name), ExpectedControlDisposition):
                raise TypeError(f"{name} must be an ExpectedControlDisposition")
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
        rows = self.f2_coordinates.shape[0]
        if rows == 0:
            raise ValueError("oracle rows must be nonempty")
        expected = {
            "row_ids": (rows,),
            "f2_coordinates": (rows, 2),
            "f2_amplitude": (rows,),
            "f2_support": (rows,),
            "f4_spin_two_coordinates": (rows, 2),
            "f4_traceless_tensor": (rows, 2, 2),
            "f4_amplitude": (rows,),
            "f4_support": (rows,),
        }
        for name, shape in expected.items():
            if getattr(self, name).shape != shape:
                raise ValueError(f"{name} has the wrong shape")
        if len(set(self.row_ids.tolist())) != rows:
            raise ValueError("oracle row_ids must be unique")
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
            raise ValueError("reason codes must be non-empty strings")
        for prefix, support, reasons in (
            ("f2", self.f2_support, self.f2_reason_codes),
            ("f4", self.f4_support, self.f4_reason_codes),
        ):
            for is_supported, reason in zip(support, reasons, strict=True):
                if bool(is_supported) != (reason == "ok"):
                    raise ValueError(f"{prefix} support and reason codes disagree")
        for prefix, disposition, support in (
            ("f2", self.f2_disposition, self.f2_support),
            ("f4", self.f4_disposition, self.f4_support),
        ):
            expected_support = (
                disposition is not ExpectedControlDisposition.PREREQUISITE_FAILURE
            )
            if not np.all(support == expected_support):
                raise ValueError(f"{prefix} disposition and support mask disagree")
        expected_f2_reason = (
            "zero_first_moment_direction_undefined"
            if self.f2_disposition is ExpectedControlDisposition.PREREQUISITE_FAILURE
            else "ok"
        )
        if any(code != expected_f2_reason for code in self.f2_reason_codes):
            raise ValueError(
                "f2 reason codes do not match the exact disposition contract"
            )
        expected_f4_reason = (
            "isotropic_second_moment_director_undefined"
            if self.f4_disposition is ExpectedControlDisposition.PREREQUISITE_FAILURE
            else "ok"
        )
        if any(code != expected_f4_reason for code in self.f4_reason_codes):
            raise ValueError(
                "f4 reason codes do not match the exact disposition contract"
            )

        expected_f2_amplitude = np.linalg.norm(
            self.f2_coordinates,
            axis=1,
        )
        if not np.array_equal(self.f2_amplitude, expected_f2_amplitude):
            raise ValueError(
                "f2_amplitude must equal the row-wise norm of f2_coordinates"
            )
        if np.any(self.f2_amplitude[self.f2_support] <= 0.0):
            raise ValueError("supported f2 rows must have strictly positive amplitude")

        expected_f4_tensor = np.empty_like(self.f4_traceless_tensor)
        expected_f4_tensor[:, 0, 0] = self.f4_spin_two_coordinates[:, 0]
        expected_f4_tensor[:, 0, 1] = self.f4_spin_two_coordinates[:, 1]
        expected_f4_tensor[:, 1, 0] = self.f4_spin_two_coordinates[:, 1]
        expected_f4_tensor[:, 1, 1] = -self.f4_spin_two_coordinates[:, 0]
        if not np.array_equal(
            self.f4_traceless_tensor,
            expected_f4_tensor,
        ):
            raise ValueError(
                "f4_traceless_tensor must be the exact symmetric traceless "
                "tensor represented by f4_spin_two_coordinates"
            )
        expected_f4_amplitude = np.linalg.norm(
            self.f4_spin_two_coordinates,
            axis=1,
        )
        if not np.array_equal(self.f4_amplitude, expected_f4_amplitude):
            raise ValueError(
                "f4_amplitude must equal the row-wise norm of f4_spin_two_coordinates"
            )
        if np.any(self.f4_amplitude[self.f4_support] <= 0.0):
            raise ValueError("supported f4 rows must have strictly positive amplitude")

        unsupported_f2 = ~self.f2_support
        if np.any(self.f2_coordinates[unsupported_f2] != 0.0) or np.any(
            self.f2_amplitude[unsupported_f2] != 0.0
        ):
            raise ValueError(
                "unsupported f2 rows must have exact zero coordinates and amplitude"
            )
        unsupported_f4 = ~self.f4_support
        if (
            np.any(self.f4_spin_two_coordinates[unsupported_f4] != 0.0)
            or np.any(self.f4_traceless_tensor[unsupported_f4] != 0.0)
            or np.any(self.f4_amplitude[unsupported_f4] != 0.0)
        ):
            raise ValueError(
                "unsupported f4 rows must have exact zero coordinates, "
                "tensor, and amplitude"
            )

    def to_dict(self) -> dict[str, object]:
        """Return an array-fingerprint receipt, not array serialization."""

        return {
            "receipt_version": ("spirallens.spectral-moment-oracle-truth-receipt.v0.1"),
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "truth_id": self.truth_id,
            "f2_disposition": self.f2_disposition.value,
            "f4_disposition": self.f4_disposition.value,
            "arrays": {
                item.name: {
                    "dtype": getattr(self, item.name).dtype.str,
                    "shape": list(getattr(self, item.name).shape),
                    "sha256": _array_sha256(getattr(self, item.name)),
                }
                for item in fields(self)
                if item.name in self._ARRAY_LAYOUT
            },
            "f2_reason_codes": list(self.f2_reason_codes),
            "f4_reason_codes": list(self.f4_reason_codes),
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _directions_are_exactly_fixed(
    coordinates: FloatArray,
    amplitude: FloatArray,
) -> bool:
    """Apply the bounded control's exact, zero-tolerance direction rule."""

    directions = coordinates / amplitude[:, None]
    return bool(
        np.array_equal(
            directions,
            np.broadcast_to(directions[:1], directions.shape),
        )
    )


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
    estimator_inputs: SpectralMomentEstimatorInputs,
    oracle_truth: SpectralMomentOracleTruth,
) -> None:
    def relation_holds(
        observed: FloatArray,
        expected: FloatArray,
        support: BoolArray,
        *,
        observation_scale: float,
    ) -> bool:
        error = np.linalg.norm(observed - expected, axis=1)
        expected_amplitude = np.linalg.norm(expected, axis=1)
        if np.any(
            error[support] > SPECTRAL_MOMENT_RELATION_RTOL * expected_amplitude[support]
        ):
            return False
        return not np.any(
            error[~support] > SPECTRAL_MOMENT_RELATION_ATOL * observation_scale
        )

    for split_name, angles, values in (
        (
            "fit",
            estimator_inputs.fit_angles_rad,
            estimator_inputs.fit_values,
        ),
        (
            "evaluation",
            estimator_inputs.evaluation_angles_rad,
            estimator_inputs.evaluation_values,
        ),
    ):
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
        observation_scale = float(np.max(np.abs(values)))
        if not relation_holds(
            observed_f2,
            oracle_truth.f2_coordinates,
            oracle_truth.f2_support,
            observation_scale=observation_scale,
        ):
            raise ValueError(
                f"{split_name} observations do not recover the oracle f2 moment"
            )
        if not relation_holds(
            observed_f4,
            oracle_truth.f4_spin_two_coordinates,
            oracle_truth.f4_support,
            observation_scale=observation_scale,
        ):
            raise ValueError(
                f"{split_name} observations do not recover the oracle f4 moment"
            )


@dataclass(frozen=True, slots=True)
class SpectralMomentCase:
    """Evaluator-side mapping with estimator inputs and truth kept separate."""

    case_id: str
    estimator_inputs: SpectralMomentEstimatorInputs
    oracle_truth: SpectralMomentOracleTruth

    def __post_init__(self) -> None:
        if self.case_id not in {
            SPECTRAL_MOMENT_POSITIVE,
            SPECTRAL_MOMENT_FIXED_NULL,
            SPECTRAL_MOMENT_PREREQUISITE_FAILURE,
        }:
            raise ValueError("unsupported spectral-moment case_id")
        if not isinstance(
            self.estimator_inputs,
            SpectralMomentEstimatorInputs,
        ):
            raise TypeError("estimator_inputs must be SpectralMomentEstimatorInputs")
        if not isinstance(self.oracle_truth, SpectralMomentOracleTruth):
            raise TypeError("oracle_truth must be SpectralMomentOracleTruth")
        expected_disposition = {
            SPECTRAL_MOMENT_POSITIVE: ExpectedControlDisposition.POSITIVE,
            SPECTRAL_MOMENT_FIXED_NULL: ExpectedControlDisposition.NULL,
            SPECTRAL_MOMENT_PREREQUISITE_FAILURE: (
                ExpectedControlDisposition.PREREQUISITE_FAILURE
            ),
        }[self.case_id]
        if (
            self.oracle_truth.f2_disposition is not expected_disposition
            or self.oracle_truth.f4_disposition is not expected_disposition
        ):
            raise ValueError("case_id and evaluator-side oracle dispositions disagree")
        if expected_disposition in {
            ExpectedControlDisposition.POSITIVE,
            ExpectedControlDisposition.NULL,
        }:
            f2_fixed = _directions_are_exactly_fixed(
                self.oracle_truth.f2_coordinates,
                self.oracle_truth.f2_amplitude,
            )
            f4_fixed = _directions_are_exactly_fixed(
                self.oracle_truth.f4_spin_two_coordinates,
                self.oracle_truth.f4_amplitude,
            )
            if expected_disposition is ExpectedControlDisposition.POSITIVE and f2_fixed:
                raise ValueError("positive control must vary f2 direction across rows")
            if expected_disposition is ExpectedControlDisposition.POSITIVE and f4_fixed:
                raise ValueError("positive control must vary f4 direction across rows")
            if expected_disposition is ExpectedControlDisposition.NULL and not f2_fixed:
                raise ValueError("null control must have exact fixed f2 direction")
            if expected_disposition is ExpectedControlDisposition.NULL and not f4_fixed:
                raise ValueError("null control must have exact fixed f4 direction")
        if not np.array_equal(
            self.estimator_inputs.row_ids,
            self.oracle_truth.row_ids,
        ):
            raise ValueError(
                "estimator inputs and truth must have identical ordered row identities"
            )
        _require_observed_truth_relation(
            self.estimator_inputs,
            self.oracle_truth,
        )

    def to_dict(self) -> dict[str, object]:
        """Return an in-memory linkage receipt, not a persistence form."""

        return {
            "receipt_version": "spirallens.spectral-moment-case-receipt.v0.1",
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "case_id": self.case_id,
            "estimator_inputs_fingerprint_sha256": (
                self.estimator_inputs.fingerprint_sha256
            ),
            "oracle_truth_fingerprint_sha256": (self.oracle_truth.fingerprint_sha256),
            "truth_separated_from_estimator_inputs": True,
        }


@dataclass(frozen=True, slots=True)
class SpectralMomentPhantom:
    """Three bounded F2/F4 development controls."""

    spec: SpectralMomentPhantomSpec
    family_identity: GeneratorFamilyIdentity
    cases: tuple[SpectralMomentCase, ...]

    receipt_version: ClassVar[str] = SPECTRAL_MOMENT_PHANTOM_RECEIPT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.spec, SpectralMomentPhantomSpec):
            raise TypeError("spec must be a SpectralMomentPhantomSpec")
        if not isinstance(self.family_identity, GeneratorFamilyIdentity):
            raise TypeError("family_identity must be a GeneratorFamilyIdentity")
        if self.family_identity != _family_identity():
            raise ValueError(
                "family_identity must equal the canonical source-bound "
                "spectral-moment identity"
            )
        if not isinstance(self.cases, tuple):
            raise TypeError("cases must be a tuple")
        if any(not isinstance(case, SpectralMomentCase) for case in self.cases):
            raise TypeError("cases must contain only SpectralMomentCase values")
        if tuple(case.case_id for case in self.cases) != (
            SPECTRAL_MOMENT_POSITIVE,
            SPECTRAL_MOMENT_FIXED_NULL,
            SPECTRAL_MOMENT_PREREQUISITE_FAILURE,
        ):
            raise ValueError("spectral-moment cases are not in canonical order")
        if len({case.estimator_inputs.input_id for case in self.cases}) != len(
            self.cases
        ):
            raise ValueError("estimator input pseudonyms must be unique")
        if len({case.oracle_truth.truth_id for case in self.cases}) != len(self.cases):
            raise ValueError("evaluator truth identifiers must be unique")
        expected_cases = _canonical_cases(self.spec)
        actual_receipts = tuple(
            canonical_json_bytes(case.to_dict()) for case in self.cases
        )
        expected_receipts = tuple(
            canonical_json_bytes(case.to_dict()) for case in expected_cases
        )
        if actual_receipts != expected_receipts:
            raise ValueError(
                "spectral-moment cases do not match the canonical controls "
                "derived from the bound spec"
            )

    def to_dict(self) -> dict[str, object]:
        """Return a bounded in-memory receipt, not a persistence form."""

        return {
            "receipt_version": self.receipt_version,
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "claim_scope": "model-free-development-controls-only",
            "spec": self.spec.to_dict(),
            "family_identity": self.family_identity.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
            "graph_constructed": False,
            "core_localized": False,
            "loop_constructed": False,
            "integer_output_authorized": False,
            "qualification_gate_evaluated": False,
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
        family_id="spectral-moment-quadrature-v0.1",
        construction_family_id="spectral-moment-quadrature",
        implementation_id="numpy-interleaved-fourier-quadrature",
        implementation_version="v0.1",
        source_sha256=_module_sha256(),
    )


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


def _values(
    *,
    angles: FloatArray,
    orientations: FloatArray,
    baseline: float,
    first_amplitude: float,
    second_amplitude: float,
) -> FloatArray:
    relative = angles[None, :] - orientations[:, None]
    return np.asarray(
        baseline
        + first_amplitude * np.cos(relative)
        + second_amplitude * np.cos(2.0 * relative),
        dtype=_FLOAT,
    )


def _label_free_content_pseudonym(
    *,
    row_ids: Int64Array,
    fit_sample_ids: Int64Array,
    fit_angles_rad: FloatArray,
    fit_values: FloatArray,
    evaluation_sample_ids: Int64Array,
    evaluation_angles_rad: FloatArray,
    evaluation_values: FloatArray,
) -> str:
    observable_arrays = {
        "row_ids": row_ids,
        "fit_sample_ids": fit_sample_ids,
        "fit_angles_rad": fit_angles_rad,
        "fit_values": fit_values,
        "evaluation_sample_ids": evaluation_sample_ids,
        "evaluation_angles_rad": evaluation_angles_rad,
        "evaluation_values": evaluation_values,
    }
    digest = hashlib.sha256(
        canonical_json_bytes(
            {
                "domain_version": (
                    "spirallens.spectral-moment-label-free-content-pseudonym.v0.1"
                ),
                "observable_array_fingerprints": {
                    name: {
                        "dtype": value.dtype.str,
                        "shape": list(value.shape),
                        "sha256": _array_sha256(value),
                    }
                    for name, value in observable_arrays.items()
                },
            }
        )
    ).hexdigest()
    return f"smi_{digest[:32]}"


def _case(
    spec: SpectralMomentPhantomSpec,
    *,
    case_id: str,
    disposition: ExpectedControlDisposition,
    orientations: FloatArray,
    first_amplitude: float,
    second_amplitude: float,
) -> SpectralMomentCase:
    fit_ids, fit_angles, evaluation_ids, evaluation_angles = _split_quadrature(
        spec.samples_per_split
    )
    row_ids = np.arange(spec.row_count, dtype=_INT64)
    fit_values = _values(
        angles=fit_angles,
        orientations=orientations,
        baseline=spec.baseline,
        first_amplitude=first_amplitude,
        second_amplitude=second_amplitude,
    )
    evaluation_values = _values(
        angles=evaluation_angles,
        orientations=orientations,
        baseline=spec.baseline,
        first_amplitude=first_amplitude,
        second_amplitude=second_amplitude,
    )
    estimator_inputs = SpectralMomentEstimatorInputs(
        input_id=_label_free_content_pseudonym(
            row_ids=row_ids,
            fit_sample_ids=fit_ids,
            fit_angles_rad=fit_angles,
            fit_values=fit_values,
            evaluation_sample_ids=evaluation_ids,
            evaluation_angles_rad=evaluation_angles,
            evaluation_values=evaluation_values,
        ),
        row_ids=row_ids,
        fit_sample_ids=fit_ids,
        fit_angles_rad=fit_angles,
        fit_values=fit_values,
        evaluation_sample_ids=evaluation_ids,
        evaluation_angles_rad=evaluation_angles,
        evaluation_values=evaluation_values,
    )

    f2_coordinates = first_amplitude * np.column_stack(
        (np.cos(orientations), np.sin(orientations))
    )
    doubled = 2.0 * orientations
    f4_coordinates = second_amplitude * np.column_stack(
        (np.cos(doubled), np.sin(doubled))
    )
    f4_tensors = np.empty((spec.row_count, 2, 2), dtype=_FLOAT)
    f4_tensors[:, 0, 0] = f4_coordinates[:, 0]
    f4_tensors[:, 0, 1] = f4_coordinates[:, 1]
    f4_tensors[:, 1, 0] = f4_coordinates[:, 1]
    f4_tensors[:, 1, 1] = -f4_coordinates[:, 0]
    f2_amplitudes = np.linalg.norm(f2_coordinates, axis=1)
    f4_amplitudes = np.linalg.norm(f4_coordinates, axis=1)
    supported = disposition is not ExpectedControlDisposition.PREREQUISITE_FAILURE
    f2_support = np.full(spec.row_count, supported, dtype=_BOOL)
    f4_support = np.full(spec.row_count, supported, dtype=_BOOL)
    oracle_truth = SpectralMomentOracleTruth(
        truth_id=f"spectral-truth-{case_id}",
        row_ids=row_ids,
        f2_disposition=disposition,
        f4_disposition=disposition,
        f2_coordinates=f2_coordinates,
        f2_amplitude=f2_amplitudes,
        f2_support=f2_support,
        f2_reason_codes=tuple(
            "ok" if supported else "zero_first_moment_direction_undefined"
            for _ in range(spec.row_count)
        ),
        f4_spin_two_coordinates=f4_coordinates,
        f4_traceless_tensor=f4_tensors,
        f4_amplitude=f4_amplitudes,
        f4_support=f4_support,
        f4_reason_codes=tuple(
            "ok" if supported else "isotropic_second_moment_director_undefined"
            for _ in range(spec.row_count)
        ),
    )
    return SpectralMomentCase(
        case_id=case_id,
        estimator_inputs=estimator_inputs,
        oracle_truth=oracle_truth,
    )


def _canonical_cases(
    spec: SpectralMomentPhantomSpec,
) -> tuple[SpectralMomentCase, SpectralMomentCase, SpectralMomentCase]:
    offset = 2.0 * np.pi * ((spec.seed % 1009) / 1009.0)
    varying = np.asarray(
        offset
        + 2.0 * np.pi * np.arange(spec.row_count, dtype=_FLOAT) / float(spec.row_count),
        dtype=_FLOAT,
    )
    fixed = np.full(spec.row_count, offset, dtype=_FLOAT)
    return (
        _case(
            spec,
            case_id=SPECTRAL_MOMENT_POSITIVE,
            disposition=ExpectedControlDisposition.POSITIVE,
            orientations=varying,
            first_amplitude=spec.f2_amplitude,
            second_amplitude=spec.f4_amplitude,
        ),
        _case(
            spec,
            case_id=SPECTRAL_MOMENT_FIXED_NULL,
            disposition=ExpectedControlDisposition.NULL,
            orientations=fixed,
            first_amplitude=spec.f2_amplitude,
            second_amplitude=spec.f4_amplitude,
        ),
        _case(
            spec,
            case_id=SPECTRAL_MOMENT_PREREQUISITE_FAILURE,
            disposition=ExpectedControlDisposition.PREREQUISITE_FAILURE,
            orientations=fixed,
            first_amplitude=0.0,
            second_amplitude=0.0,
        ),
    )


class SpectralMomentGenerator:
    """Generate the bounded spectral-moment positive/null/failure controls."""

    @property
    def family_identity(self) -> GeneratorFamilyIdentity:
        return _family_identity()

    def generate(
        self,
        spec: SpectralMomentPhantomSpec,
    ) -> SpectralMomentPhantom:
        if not isinstance(spec, SpectralMomentPhantomSpec):
            raise TypeError("spec must be a SpectralMomentPhantomSpec")
        cases = _canonical_cases(spec)
        return SpectralMomentPhantom(
            spec=spec,
            family_identity=self.family_identity,
            cases=cases,
        )
