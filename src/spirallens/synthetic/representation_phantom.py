"""Deterministic representation-shaped phantoms for P1 calibration.

This module deliberately stops at substrate, graph, support, frame, and
section observations.  It does not construct loops, localize a core, estimate
winding, select an estimator, or implement a scientific promotion gate.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import math
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from spirallens.instrument_contracts.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)


FloatArray = NDArray[np.float64]
Int64Array = NDArray[np.int64]
Int32Array = NDArray[np.int32]
BoolArray = NDArray[np.bool_]

ANGULAR_SECTION_POSITIVE = "angular-section-positive"
FIXED_DIRECTION_NULL = "fixed-direction-null"

REASON_OK = 0
REASON_INSUFFICIENT_NEIGHBORS = 1
REASON_RANK_TWO_UNRESOLVED = 2
REASON_ZERO_AMPLITUDE = 3

F0_VALUE_COLUMNS = (
    "largest_eigenvalue",
    "second_eigenvalue",
    "third_eigenvalue",
    "relative_second_gap",
    "top_two_concentration",
    "entropy_effective_rank",
)

_FLOAT_DTYPE = np.dtype("<f8")
_INT64_DTYPE = np.dtype("<i8")
_INT32_DTYPE = np.dtype("<i4")
_BOOL_DTYPE = np.dtype("|b1")
RESOURCE_BUDGET_ESTIMATOR_ID = (
    "representation-phantom-conservative-static-estimate-v0.1"
)
RESOURCE_BUDGET_SAFETY_FACTOR = 4
RESOURCE_BUDGET_CLAIM_BOUNDARY = (
    "parameter-induced-runaway-allocation-guard-not-os-oom-guarantee"
)
MAX_ESTIMATED_PEAK_BYTES = 256 * 1024 * 1024
MAX_ESTIMATED_OUTPUT_BYTES = 256 * 1024 * 1024


def _resource_estimates(
    *,
    grid_side: int,
    ambient_dimension: int,
    probe_count: int,
    neighbor_count: int,
) -> tuple[int, int]:
    rows = grid_side * grid_side
    float_bytes = _FLOAT_DTYPE.itemsize
    shared_bytes = (
        rows * ambient_dimension * float_bytes
        + ambient_dimension * ambient_dimension * float_bytes
        + rows * 2 * float_bytes
    )
    numeric_pairwise_bytes = (
        rows * rows * ambient_dimension * float_bytes
        + rows * rows * float_bytes
        + rows * rows * _INT64_DTYPE.itemsize
        + rows * rows * 3 * _BOOL_DTYPE.itemsize
        + rows * neighbor_count * _INT64_DTYPE.itemsize
    )
    graph_container_bytes = (
        rows * neighbor_count * 96
        + rows * neighbor_count * 40
        + rows * 128
    )
    linear_algebra_scratch_bytes = (
        ambient_dimension * ambient_dimension * float_bytes * 64
    )
    per_case_bytes = (
        rows * probe_count * ambient_dimension * float_bytes
        + rows * ambient_dimension * ambient_dimension * float_bytes
        + rows * ambient_dimension * float_bytes
        + rows * ambient_dimension * 2 * float_bytes
        + rows * 24 * float_bytes
        + rows * 16 * _INT64_DTYPE.itemsize
    )
    estimated_output = shared_bytes + 2 * per_case_bytes
    estimated_peak = max(
        (
            shared_bytes
            + numeric_pairwise_bytes
            + graph_container_bytes
            + linear_algebra_scratch_bytes
        ),
        estimated_output * 2,
        estimated_output + per_case_bytes,
    )
    return (
        estimated_peak * RESOURCE_BUDGET_SAFETY_FACTOR,
        estimated_output * RESOURCE_BUDGET_SAFETY_FACTOR,
    )


def _integer(value: object, *, label: str, minimum: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
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
        value, (int, float, np.integer, np.floating)
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


@dataclass(frozen=True, slots=True)
class RepresentationPhantomSpec:
    """Canonical numeric inputs for a paired representation phantom."""

    seed: int = 1729
    grid_side: int = 7
    ambient_dimension: int = 12
    probe_count: int = 8
    neighbor_count: int = 4
    radial_scale: float = 1.0
    probe_scale: float = 1.0
    nuisance_scale: float = 0.02

    schema_version: ClassVar[str] = "spirallens.representation-phantom-spec.v0.1"

    def __post_init__(self) -> None:
        seed = _integer(self.seed, label="seed", minimum=0)
        grid_side = _integer(self.grid_side, label="grid_side", minimum=5)
        ambient_dimension = _integer(
            self.ambient_dimension,
            label="ambient_dimension",
            minimum=8,
        )
        probe_count = _integer(
            self.probe_count,
            label="probe_count",
            minimum=4,
        )
        neighbor_count = _integer(
            self.neighbor_count,
            label="neighbor_count",
            minimum=4,
        )
        if grid_side % 2 == 0:
            raise ValueError("grid_side must be odd")
        if probe_count % 4 != 0:
            raise ValueError("probe_count must be even and divisible by 4")
        if neighbor_count >= grid_side * grid_side:
            raise ValueError("neighbor_count must be smaller than row count")
        estimated_peak_bytes, estimated_output_bytes = _resource_estimates(
            grid_side=grid_side,
            ambient_dimension=ambient_dimension,
            probe_count=probe_count,
            neighbor_count=neighbor_count,
        )
        if estimated_peak_bytes > MAX_ESTIMATED_PEAK_BYTES:
            raise ValueError(
                "estimated peak memory exceeds the representation phantom "
                "resource budget"
            )
        if estimated_output_bytes > MAX_ESTIMATED_OUTPUT_BYTES:
            raise ValueError(
                "estimated output exceeds the representation phantom "
                "resource budget"
            )

        object.__setattr__(self, "seed", seed)
        object.__setattr__(self, "grid_side", grid_side)
        object.__setattr__(self, "ambient_dimension", ambient_dimension)
        object.__setattr__(self, "probe_count", probe_count)
        object.__setattr__(self, "neighbor_count", neighbor_count)
        object.__setattr__(
            self,
            "radial_scale",
            _real(self.radial_scale, label="radial_scale", positive=True),
        )
        object.__setattr__(
            self,
            "probe_scale",
            _real(self.probe_scale, label="probe_scale", positive=True),
        )
        object.__setattr__(
            self,
            "nuisance_scale",
            _real(
                self.nuisance_scale,
                label="nuisance_scale",
                positive=False,
            ),
        )

    @property
    def row_count(self) -> int:
        return self.grid_side * self.grid_side

    @property
    def even_probe_indices(self) -> tuple[int, ...]:
        return tuple(range(0, self.probe_count, 2))

    @property
    def odd_probe_indices(self) -> tuple[int, ...]:
        return tuple(range(1, self.probe_count, 2))

    @property
    def estimated_peak_bytes(self) -> int:
        return _resource_estimates(
            grid_side=self.grid_side,
            ambient_dimension=self.ambient_dimension,
            probe_count=self.probe_count,
            neighbor_count=self.neighbor_count,
        )[0]

    @property
    def estimated_output_bytes(self) -> int:
        return _resource_estimates(
            grid_side=self.grid_side,
            ambient_dimension=self.ambient_dimension,
            probe_count=self.probe_count,
            neighbor_count=self.neighbor_count,
        )[1]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "grid_side": self.grid_side,
            "ambient_dimension": self.ambient_dimension,
            "probe_count": self.probe_count,
            "neighbor_count": self.neighbor_count,
            "radial_scale": self.radial_scale,
            "probe_scale": self.probe_scale,
            "nuisance_scale": self.nuisance_scale,
            "row_order": "cartesian-row-major-y-then-x",
            "graph_rule": "exact-euclidean-mutual-knn",
            "even_probe_indices": list(self.even_probe_indices),
            "odd_probe_indices": list(self.odd_probe_indices),
            "even_probe_role": "rank-two-local-frame-fit",
            "odd_probe_role": "section-observation-mean",
            "resource_budget": {
                "claim_boundary": RESOURCE_BUDGET_CLAIM_BOUNDARY,
                "estimator_id": RESOURCE_BUDGET_ESTIMATOR_ID,
                "estimated_output_bytes": self.estimated_output_bytes,
                "estimated_peak_bytes": self.estimated_peak_bytes,
                "max_estimated_output_bytes": MAX_ESTIMATED_OUTPUT_BYTES,
                "max_estimated_peak_bytes": MAX_ESTIMATED_PEAK_BYTES,
                "preflight_status": "pass",
                "safety_factor": RESOURCE_BUDGET_SAFETY_FACTOR,
            },
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _frozen_array(
    value: object,
    *,
    dtype: np.dtype[object],
) -> NDArray[np.generic]:
    result = np.array(value, dtype=dtype, order="C", copy=True)
    if not result.flags.c_contiguous:
        result = np.ascontiguousarray(result, dtype=dtype)
    result.flags.writeable = False
    return result


def _array_sha256(value: NDArray[np.generic]) -> str:
    descriptor = (
        f"{value.dtype.str}|{','.join(str(item) for item in value.shape)}|"
    ).encode("ascii")
    return hashlib.sha256(descriptor + value.tobytes(order="C")).hexdigest()


@dataclass(frozen=True, slots=True)
class PhantomCase:
    """One immutable paired-phantom case and its deterministic estimators."""

    spec: RepresentationPhantomSpec
    case_id: str
    case_index: int
    states: FloatArray
    vertex_identities: Int64Array
    observation_identities: Int64Array
    valid_mask: BoolArray
    center_support_mask: BoolArray
    accounted_response: FloatArray
    neighbor_indices: Int64Array
    edges: Int64Array
    graph_weights: FloatArray
    components: Int64Array
    degree: Int64Array
    two_core_mask: BoolArray
    cycle_support: Int64Array
    local_covariance: FloatArray
    f0_spectra: FloatArray
    f0_values: FloatArray
    f0_uncertainty: FloatArray
    f0_support: BoolArray
    f0_reason_codes: Int32Array
    f1_frames: FloatArray
    f1_eigenvalues: FloatArray
    f1_support_count: Int64Array
    f1_support: BoolArray
    f1_reason_codes: Int32Array
    f2_coordinates: FloatArray
    f2_amplitude: FloatArray
    f2_support: BoolArray
    f2_reason_codes: Int32Array

    _ARRAY_DTYPES: ClassVar[dict[str, np.dtype[object]]] = {
        "states": _FLOAT_DTYPE,
        "vertex_identities": _INT64_DTYPE,
        "observation_identities": _INT64_DTYPE,
        "valid_mask": _BOOL_DTYPE,
        "center_support_mask": _BOOL_DTYPE,
        "accounted_response": _FLOAT_DTYPE,
        "neighbor_indices": _INT64_DTYPE,
        "edges": _INT64_DTYPE,
        "graph_weights": _FLOAT_DTYPE,
        "components": _INT64_DTYPE,
        "degree": _INT64_DTYPE,
        "two_core_mask": _BOOL_DTYPE,
        "cycle_support": _INT64_DTYPE,
        "local_covariance": _FLOAT_DTYPE,
        "f0_spectra": _FLOAT_DTYPE,
        "f0_values": _FLOAT_DTYPE,
        "f0_uncertainty": _FLOAT_DTYPE,
        "f0_support": _BOOL_DTYPE,
        "f0_reason_codes": _INT32_DTYPE,
        "f1_frames": _FLOAT_DTYPE,
        "f1_eigenvalues": _FLOAT_DTYPE,
        "f1_support_count": _INT64_DTYPE,
        "f1_support": _BOOL_DTYPE,
        "f1_reason_codes": _INT32_DTYPE,
        "f2_coordinates": _FLOAT_DTYPE,
        "f2_amplitude": _FLOAT_DTYPE,
        "f2_support": _BOOL_DTYPE,
        "f2_reason_codes": _INT32_DTYPE,
    }

    def __post_init__(self) -> None:
        if not isinstance(self.spec, RepresentationPhantomSpec):
            raise TypeError("spec must be a RepresentationPhantomSpec")
        expected_index = {
            ANGULAR_SECTION_POSITIVE: 0,
            FIXED_DIRECTION_NULL: 1,
        }.get(self.case_id)
        if expected_index is None:
            raise ValueError(f"unknown phantom case {self.case_id!r}")
        if self.case_index != expected_index:
            raise ValueError("case_index does not match case_id")

        for name, dtype in self._ARRAY_DTYPES.items():
            object.__setattr__(
                self,
                name,
                _frozen_array(getattr(self, name), dtype=dtype),
            )
        self._validate_layout()

    @property
    def row_ids(self) -> Int64Array:
        return self.vertex_identities

    def _validate_layout(self) -> None:
        n = self.spec.row_count
        d = self.spec.ambient_dimension
        p = self.spec.probe_count
        k = self.spec.neighbor_count
        shapes = {
            "states": (n, d),
            "vertex_identities": (n,),
            "observation_identities": (n, 2),
            "valid_mask": (n,),
            "center_support_mask": (n,),
            "accounted_response": (n, p, d),
            "neighbor_indices": (n, k),
            "edges": (None, 2),
            "graph_weights": (self.edges.shape[0],),
            "components": (n,),
            "degree": (n,),
            "two_core_mask": (n,),
            "cycle_support": (None, 4),
            "local_covariance": (n, d, d),
            "f0_spectra": (n, d),
            "f0_values": (n, len(F0_VALUE_COLUMNS)),
            "f0_uncertainty": (n, len(F0_VALUE_COLUMNS)),
            "f0_support": (n,),
            "f0_reason_codes": (n,),
            "f1_frames": (n, d, 2),
            "f1_eigenvalues": (n, 3),
            "f1_support_count": (n,),
            "f1_support": (n,),
            "f1_reason_codes": (n,),
            "f2_coordinates": (n, 2),
            "f2_amplitude": (n,),
            "f2_support": (n,),
            "f2_reason_codes": (n,),
        }
        for name, shape in shapes.items():
            value = getattr(self, name)
            if value.ndim != len(shape) or any(
                expected is not None and actual != expected
                for actual, expected in zip(value.shape, shape, strict=True)
            ):
                raise ValueError(
                    f"{name} has shape {value.shape}; expected {shape}"
                )
            if value.dtype.str != self._ARRAY_DTYPES[name].str:
                raise TypeError(
                    f"{name} has dtype {value.dtype.str}; expected "
                    f"{self._ARRAY_DTYPES[name].str}"
                )
            if not value.flags.c_contiguous or value.flags.writeable:
                raise ValueError(f"{name} must be frozen and C-contiguous")
            if not np.all(np.isfinite(value)):
                raise ValueError(f"{name} must contain only finite values")

    def to_dict(self) -> dict[str, object]:
        payloads = {
            item.name: {
                "dtype": getattr(self, item.name).dtype.str,
                "shape": list(getattr(self, item.name).shape),
                "sha256": _array_sha256(getattr(self, item.name)),
            }
            for item in fields(self)
            if item.name in self._ARRAY_DTYPES
        }
        return {
            "schema_version": "spirallens.representation-phantom-case.v0.1",
            "spec_sha256": self.spec.canonical_sha256,
            "case_id": self.case_id,
            "case_index": self.case_index,
            "payloads": payloads,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def validate(self) -> None:
        """Recompute generation, graph, and F0/F1/F2 relations.

        Canonical state and identity comparison is intentional: a consistently
        permuted row set is still rejected rather than accepted as a different
        serialization of the same phantom.
        """

        self._validate_layout()
        shared = _generate_shared(self.spec)
        exact_shared = {
            "states": shared.states,
            "vertex_identities": shared.vertex_identities,
            "valid_mask": shared.valid_mask,
            "center_support_mask": shared.center_support_mask,
        }
        for name, expected in exact_shared.items():
            if not np.array_equal(getattr(self, name), expected):
                raise ValueError(f"{name} does not match canonical row order")

        expected_observations = np.column_stack(
            (
                shared.vertex_identities,
                np.full(self.spec.row_count, self.case_index, dtype="<i8"),
            )
        )
        if not np.array_equal(
            self.observation_identities, expected_observations
        ):
            raise ValueError(
                "observation_identities do not bind row and case identities"
            )

        expected_response = _generate_accounted_response(
            self.spec,
            shared.ambient_basis,
            shared.grid_coordinates,
            case_id=self.case_id,
        )
        if not np.array_equal(self.accounted_response, expected_response):
            raise ValueError(
                "accounted_response violates the frozen probe construction"
            )

        graph = _build_mutual_knn(
            self.states,
            self.vertex_identities,
            neighbor_count=self.spec.neighbor_count,
        )
        graph_relations = {
            "neighbor_indices": graph.neighbor_indices,
            "edges": graph.edges,
            "graph_weights": graph.graph_weights,
            "components": graph.components,
            "degree": graph.degree,
            "two_core_mask": graph.two_core_mask,
            "cycle_support": graph.cycle_support,
        }
        for name, expected in graph_relations.items():
            if not np.array_equal(getattr(self, name), expected):
                raise ValueError(f"{name} does not match recomputed graph")

        derived = _derive_estimators(
            self.spec,
            self.accounted_response,
            self.edges,
            self.center_support_mask,
        )
        for name in _DerivedEstimators.__dataclass_fields__:
            expected = getattr(derived, name)
            actual = getattr(self, name)
            if not np.array_equal(actual, expected):
                raise ValueError(
                    f"{name} does not match recomputed estimator relation"
                )


@dataclass(frozen=True, slots=True)
class RepresentationPhantom:
    """The paired positive and fixed-direction-null phantom."""

    spec: RepresentationPhantomSpec
    ambient_basis: FloatArray
    grid_coordinates: FloatArray
    cases: tuple[PhantomCase, PhantomCase]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, RepresentationPhantomSpec):
            raise TypeError("spec must be a RepresentationPhantomSpec")
        object.__setattr__(
            self,
            "ambient_basis",
            _frozen_array(self.ambient_basis, dtype=_FLOAT_DTYPE),
        )
        object.__setattr__(
            self,
            "grid_coordinates",
            _frozen_array(self.grid_coordinates, dtype=_FLOAT_DTYPE),
        )
        d = self.spec.ambient_dimension
        if self.ambient_basis.shape != (d, d):
            raise ValueError("ambient_basis has the wrong shape")
        if self.grid_coordinates.shape != (self.spec.row_count, 2):
            raise ValueError("grid_coordinates has the wrong shape")
        if tuple(case.case_id for case in self.cases) != (
            ANGULAR_SECTION_POSITIVE,
            FIXED_DIRECTION_NULL,
        ):
            raise ValueError("cases must be in canonical positive/null order")

    @classmethod
    def generate(
        cls,
        spec: RepresentationPhantomSpec | None = None,
    ) -> "RepresentationPhantom":
        selected = spec or RepresentationPhantomSpec()
        if not isinstance(selected, RepresentationPhantomSpec):
            raise TypeError("spec must be a RepresentationPhantomSpec")
        shared = _generate_shared(selected)
        graph = _build_mutual_knn(
            shared.states,
            shared.vertex_identities,
            neighbor_count=selected.neighbor_count,
        )
        cases = tuple(
            _build_case(
                selected,
                shared,
                graph,
                case_id=case_id,
                case_index=case_index,
            )
            for case_index, case_id in enumerate(
                (ANGULAR_SECTION_POSITIVE, FIXED_DIRECTION_NULL)
            )
        )
        return cls(
            spec=selected,
            ambient_basis=shared.ambient_basis,
            grid_coordinates=shared.grid_coordinates,
            cases=cases,  # type: ignore[arg-type]
        )

    @property
    def angular_section_positive(self) -> PhantomCase:
        return self.cases[0]

    @property
    def fixed_direction_null(self) -> PhantomCase:
        return self.cases[1]

    def validate(self) -> None:
        shared = _generate_shared(self.spec)
        if not np.array_equal(self.ambient_basis, shared.ambient_basis):
            raise ValueError("ambient_basis does not match the seeded basis")
        if not np.array_equal(
            self.grid_coordinates, shared.grid_coordinates
        ):
            raise ValueError("grid_coordinates violates canonical row order")
        for case in self.cases:
            if case.spec != self.spec:
                raise ValueError("case spec does not match phantom spec")
            case.validate()
        positive, null = self.cases
        for name in (
            "states",
            "vertex_identities",
            "valid_mask",
            "center_support_mask",
            "neighbor_indices",
            "edges",
            "graph_weights",
            "components",
            "degree",
            "two_core_mask",
            "cycle_support",
        ):
            if not np.array_equal(getattr(positive, name), getattr(null, name)):
                raise ValueError(f"paired cases do not share {name}")
        if not np.array_equal(
            positive.accounted_response[:, self.spec.even_probe_indices, :],
            null.accounted_response[:, self.spec.even_probe_indices, :],
        ):
            raise ValueError("paired cases do not share even fit probes")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "spirallens.representation-phantom.v0.1",
            "spec": self.spec.to_dict(),
            "ambient_basis_sha256": _array_sha256(self.ambient_basis),
            "grid_coordinates_sha256": _array_sha256(
                self.grid_coordinates
            ),
            "cases": [case.to_dict() for case in self.cases],
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class _Shared:
    ambient_basis: FloatArray
    grid_coordinates: FloatArray
    states: FloatArray
    vertex_identities: Int64Array
    valid_mask: BoolArray
    center_support_mask: BoolArray


@dataclass(frozen=True, slots=True)
class _Graph:
    neighbor_indices: Int64Array
    edges: Int64Array
    graph_weights: FloatArray
    components: Int64Array
    degree: Int64Array
    two_core_mask: BoolArray
    cycle_support: Int64Array


@dataclass(frozen=True, slots=True)
class _DerivedEstimators:
    local_covariance: FloatArray
    f0_spectra: FloatArray
    f0_values: FloatArray
    f0_uncertainty: FloatArray
    f0_support: BoolArray
    f0_reason_codes: Int32Array
    f1_frames: FloatArray
    f1_eigenvalues: FloatArray
    f1_support_count: Int64Array
    f1_support: BoolArray
    f1_reason_codes: Int32Array
    f2_coordinates: FloatArray
    f2_amplitude: FloatArray
    f2_support: BoolArray
    f2_reason_codes: Int32Array


def _sign_canonical_columns(matrix: FloatArray) -> FloatArray:
    result = np.array(matrix, dtype="<f8", order="C", copy=True)
    for column_index in range(result.shape[1]):
        column = result[:, column_index]
        anchor = int(np.argmax(np.abs(column)))
        if column[anchor] < 0.0:
            result[:, column_index] *= -1.0
    return result


def _seeded_ambient_basis(spec: RepresentationPhantomSpec) -> FloatArray:
    rng = np.random.default_rng(spec.seed)
    raw = rng.standard_normal(
        (spec.ambient_dimension, spec.ambient_dimension),
        dtype=np.float64,
    )
    basis, _triangular = np.linalg.qr(raw)
    return np.ascontiguousarray(
        _sign_canonical_columns(basis),
        dtype="<f8",
    )


def _canonical_grid(spec: RepresentationPhantomSpec) -> FloatArray:
    radius = spec.grid_side // 2
    axis = np.arange(-radius, radius + 1, dtype="<f8") / float(radius)
    return np.ascontiguousarray(
        np.array([(x, y) for y in axis for x in axis], dtype="<f8")
    )


def _nuisance_features(
    spec: RepresentationPhantomSpec,
    coordinates: FloatArray,
) -> FloatArray:
    count = spec.ambient_dimension - 2
    if count == 0:
        return np.empty((coordinates.shape[0], 0), dtype="<f8")
    x = coordinates[:, 0]
    y = coordinates[:, 1]
    rng = np.random.default_rng(spec.seed ^ 0x5A17)
    frequencies = rng.integers(1, 5, size=(count, 2))
    phases = rng.uniform(-np.pi, np.pi, size=count)
    values = np.column_stack(
        [
            np.sin(
                np.pi
                * (frequencies[j, 0] * x + frequencies[j, 1] * y)
                + phases[j]
            )
            for j in range(count)
        ]
    )
    values -= values.mean(axis=0, keepdims=True)
    norms = np.linalg.norm(values, axis=0)
    norms[norms == 0.0] = 1.0
    values /= norms[None, :] / math.sqrt(values.shape[0])
    return np.ascontiguousarray(values, dtype="<f8")


def _generate_shared(spec: RepresentationPhantomSpec) -> _Shared:
    basis = _seeded_ambient_basis(spec)
    coordinates = _canonical_grid(spec)
    planar = spec.radial_scale * coordinates @ basis[:, :2].T
    nuisance = _nuisance_features(spec, coordinates)
    states = planar
    if nuisance.shape[1]:
        states = states + (
            spec.nuisance_scale
            * nuisance
            @ basis[:, 2:].T
            / math.sqrt(nuisance.shape[1])
        )
    n = spec.row_count
    center = np.all(coordinates == 0.0, axis=1)
    return _Shared(
        ambient_basis=np.ascontiguousarray(basis, dtype="<f8"),
        grid_coordinates=np.ascontiguousarray(coordinates, dtype="<f8"),
        states=np.ascontiguousarray(states, dtype="<f8"),
        vertex_identities=np.arange(n, dtype="<i8"),
        valid_mask=np.ones(n, dtype="|b1"),
        center_support_mask=np.ascontiguousarray(center, dtype="|b1"),
    )


def _component_labels(
    row_count: int,
    adjacency: list[list[int]],
) -> Int64Array:
    labels = np.full(row_count, -1, dtype="<i8")
    component = 0
    for start in range(row_count):
        if labels[start] >= 0:
            continue
        labels[start] = component
        stack = [start]
        while stack:
            vertex = stack.pop()
            for neighbor in adjacency[vertex]:
                if labels[neighbor] < 0:
                    labels[neighbor] = component
                    stack.append(neighbor)
        component += 1
    return labels


def _two_core(
    row_count: int,
    adjacency: list[list[int]],
) -> BoolArray:
    active = np.ones(row_count, dtype="|b1")
    degree = np.array([len(items) for items in adjacency], dtype="<i8")
    queue = [int(index) for index in np.flatnonzero(degree < 2)]
    cursor = 0
    while cursor < len(queue):
        vertex = queue[cursor]
        cursor += 1
        if not active[vertex]:
            continue
        active[vertex] = False
        for neighbor in adjacency[vertex]:
            if active[neighbor]:
                degree[neighbor] -= 1
                if degree[neighbor] == 1:
                    queue.append(neighbor)
    return active


def _build_mutual_knn(
    states: FloatArray,
    vertex_identities: Int64Array,
    *,
    neighbor_count: int,
) -> _Graph:
    row_count = states.shape[0]
    differences = states[:, None, :] - states[None, :, :]
    distances_squared = np.einsum(
        "ijk,ijk->ij", differences, differences, optimize=False
    )
    np.fill_diagonal(distances_squared, np.inf)
    directed = np.empty((row_count, neighbor_count), dtype="<i8")
    row_indices = np.arange(row_count, dtype="<i8")
    for row in range(row_count):
        order = np.lexsort(
            (row_indices, vertex_identities, distances_squared[row])
        )
        directed[row] = order[:neighbor_count]

    memberships = np.zeros((row_count, row_count), dtype="|b1")
    memberships[
        np.repeat(row_indices, neighbor_count),
        directed.reshape(-1),
    ] = True
    edges = [
        (left, right)
        for left in range(row_count)
        for right in range(left + 1, row_count)
        if memberships[left, right] and memberships[right, left]
    ]
    edge_array = (
        np.ascontiguousarray(edges, dtype="<i8").reshape(-1, 2)
        if edges
        else np.empty((0, 2), dtype="<i8")
    )
    weights = np.array(
        [
            math.sqrt(float(distances_squared[left, right]))
            for left, right in edges
        ],
        dtype="<f8",
    )
    adjacency: list[list[int]] = [[] for _ in range(row_count)]
    for left, right in edges:
        adjacency[left].append(right)
        adjacency[right].append(left)
    for items in adjacency:
        items.sort()
    degree = np.array([len(items) for items in adjacency], dtype="<i8")
    return _Graph(
        neighbor_indices=directed,
        edges=edge_array,
        graph_weights=weights,
        components=_component_labels(row_count, adjacency),
        degree=degree,
        two_core_mask=_two_core(row_count, adjacency),
        cycle_support=np.empty((0, 4), dtype="<i8"),
    )


def _rotation(angle: float) -> FloatArray:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return np.array(
        [[cosine, -sine], [sine, cosine]],
        dtype="<f8",
    )


def _paired_coefficients(count: int) -> FloatArray:
    pair_count = count // 2
    positive = np.array(
        [
            (
                math.sqrt(2.0)
                * math.cos(math.pi * index / pair_count),
                math.sin(math.pi * index / pair_count),
            )
            for index in range(pair_count)
        ],
        dtype="<f8",
    )
    return np.ascontiguousarray(
        np.concatenate((positive, -positive), axis=0),
        dtype="<f8",
    )


def _generate_accounted_response(
    spec: RepresentationPhantomSpec,
    ambient_basis: FloatArray,
    coordinates: FloatArray,
    *,
    case_id: str,
) -> FloatArray:
    row_count = spec.row_count
    response = np.empty(
        (row_count, spec.probe_count, spec.ambient_dimension),
        dtype="<f8",
    )
    even_indices = spec.even_probe_indices
    odd_indices = spec.odd_probe_indices
    coefficients = _paired_coefficients(len(even_indices))
    radii = np.linalg.norm(coordinates, axis=1)
    angles = np.arctan2(coordinates[:, 1], coordinates[:, 0])

    for row in range(row_count):
        frame_angle = 0.25 * float(angles[row]) + 0.075 * float(radii[row])
        local_frame = ambient_basis[:, :2] @ _rotation(frame_angle)
        for offset, probe_index in enumerate(even_indices):
            response[row, probe_index] = (
                spec.probe_scale
                * local_frame
                @ coefficients[offset]
            )

        section_angle = (
            float(angles[row])
            if case_id == ANGULAR_SECTION_POSITIVE
            else 0.0
        )
        envelope = math.tanh(float(radii[row]))
        section = (
            spec.probe_scale
            * envelope
            * ambient_basis[:, :2]
            @ np.array(
                [math.cos(section_angle), math.sin(section_angle)],
                dtype="<f8",
            )
        )
        odd_offsets = 0.125 * spec.probe_scale * (
            local_frame @ coefficients.T
        ).T
        for offset, probe_index in enumerate(odd_indices):
            response[row, probe_index] = section + odd_offsets[offset]
    return np.ascontiguousarray(response, dtype="<f8")


def _adjacency_from_edges(
    row_count: int,
    edges: Int64Array,
) -> list[list[int]]:
    adjacency: list[list[int]] = [[] for _ in range(row_count)]
    for left_raw, right_raw in edges:
        left = int(left_raw)
        right = int(right_raw)
        adjacency[left].append(right)
        adjacency[right].append(left)
    for items in adjacency:
        items.sort()
    return adjacency


def _covariance_from_rows(
    response: FloatArray,
    source_rows: list[int],
    even_indices: tuple[int, ...],
) -> FloatArray:
    dimension = response.shape[2]
    if not source_rows:
        return np.zeros((dimension, dimension), dtype="<f8")
    samples = response[
        np.asarray(source_rows, dtype="<i8")[:, None],
        np.asarray(even_indices, dtype="<i8")[None, :],
        :,
    ].reshape(-1, dimension)
    centered = samples - samples.mean(axis=0, keepdims=True)
    return np.ascontiguousarray(
        centered.T @ centered / float(samples.shape[0]),
        dtype="<f8",
    )


def _spectrum_and_diagnostics(
    covariance: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    eigenvalues = np.linalg.eigvalsh(covariance)[::-1]
    scale = max(1.0, float(np.max(np.abs(eigenvalues))))
    eigenvalues[np.abs(eigenvalues) < 64.0 * np.finfo(float).eps * scale] = 0.0
    eigenvalues = np.maximum(eigenvalues, 0.0)
    total = float(eigenvalues.sum())
    if total > 0.0:
        probabilities = eigenvalues[eigenvalues > 0.0] / total
        effective_rank = math.exp(
            -float(np.sum(probabilities * np.log(probabilities)))
        )
        concentration = float((eigenvalues[0] + eigenvalues[1]) / total)
    else:
        effective_rank = 0.0
        concentration = 0.0
    denominator = max(float(eigenvalues[0]), np.finfo(float).tiny)
    diagnostics = np.array(
        [
            eigenvalues[0],
            eigenvalues[1],
            eigenvalues[2],
            (eigenvalues[1] - eigenvalues[2]) / denominator,
            concentration,
            effective_rank,
        ],
        dtype="<f8",
    )
    return (
        np.ascontiguousarray(eigenvalues, dtype="<f8"),
        diagnostics,
    )


def _frame_from_covariance(
    covariance: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(-eigenvalues, kind="stable")
    ordered_values = np.maximum(eigenvalues[order], 0.0)
    frame = _sign_canonical_columns(eigenvectors[:, order[:2]])
    top_three = np.zeros(3, dtype="<f8")
    top_three[: min(3, len(ordered_values))] = ordered_values[:3]
    return (
        np.ascontiguousarray(frame, dtype="<f8"),
        top_three,
    )


def _derive_estimators(
    spec: RepresentationPhantomSpec,
    response: FloatArray,
    edges: Int64Array,
    center_support_mask: BoolArray,
) -> _DerivedEstimators:
    n = spec.row_count
    d = spec.ambient_dimension
    even = spec.even_probe_indices
    odd = spec.odd_probe_indices
    adjacency = _adjacency_from_edges(n, edges)

    local_covariance = np.zeros((n, d, d), dtype="<f8")
    f0_spectra = np.zeros((n, d), dtype="<f8")
    f0_values = np.zeros((n, len(F0_VALUE_COLUMNS)), dtype="<f8")
    f0_uncertainty = np.zeros_like(f0_values)
    f0_support = np.zeros(n, dtype="|b1")
    f0_reason_codes = np.full(
        n, REASON_INSUFFICIENT_NEIGHBORS, dtype="<i4"
    )

    f1_frames = np.zeros((n, d, 2), dtype="<f8")
    f1_eigenvalues = np.zeros((n, 3), dtype="<f8")
    f1_support_count = np.zeros(n, dtype="<i8")
    f1_support = np.zeros(n, dtype="|b1")
    f1_reason_codes = np.full(
        n, REASON_INSUFFICIENT_NEIGHBORS, dtype="<i4"
    )

    for row, source_rows in enumerate(adjacency):
        covariance = _covariance_from_rows(response, source_rows, even)
        spectrum, diagnostics = _spectrum_and_diagnostics(covariance)
        local_covariance[row] = covariance
        f0_spectra[row] = spectrum
        f0_values[row] = diagnostics
        f1_support_count[row] = len(source_rows) * len(even)

        if len(source_rows) >= 2:
            first_fold = source_rows[::2]
            second_fold = source_rows[1::2]
            _first_spectrum, first_diagnostics = _spectrum_and_diagnostics(
                _covariance_from_rows(response, first_fold, even)
            )
            _second_spectrum, second_diagnostics = (
                _spectrum_and_diagnostics(
                    _covariance_from_rows(response, second_fold, even)
                )
            )
            f0_uncertainty[row] = (
                0.5 * np.abs(first_diagnostics - second_diagnostics)
            )
            f0_support[row] = True
            f0_reason_codes[row] = REASON_OK

        frame, top_three = _frame_from_covariance(covariance)
        f1_frames[row] = frame
        f1_eigenvalues[row] = top_three
        rank_tolerance = max(
            float(top_three[0]) * 1e-12,
            np.finfo(float).eps,
        )
        if f0_support[row] and top_three[1] > rank_tolerance:
            f1_support[row] = True
            f1_reason_codes[row] = REASON_OK
        elif f0_support[row]:
            f1_reason_codes[row] = REASON_RANK_TWO_UNRESOLVED

    odd_mean = response[:, odd, :].mean(axis=1)
    f2_coordinates = np.einsum(
        "ndi,nd->ni", f1_frames, odd_mean, optimize=False
    )
    f2_amplitude = np.linalg.norm(f2_coordinates, axis=1)
    f2_support = f1_support.copy()
    f2_reason_codes = f1_reason_codes.copy()
    amplitude_tolerance = (
        128.0 * np.finfo(float).eps * spec.probe_scale
    )
    zero_amplitude = f2_amplitude <= amplitude_tolerance
    f2_support[zero_amplitude] = False
    f2_reason_codes[zero_amplitude] = REASON_ZERO_AMPLITUDE
    if np.count_nonzero(center_support_mask) != 1:
        raise ValueError("center_support_mask must identify exactly one row")

    return _DerivedEstimators(
        local_covariance=np.ascontiguousarray(
            local_covariance, dtype="<f8"
        ),
        f0_spectra=np.ascontiguousarray(f0_spectra, dtype="<f8"),
        f0_values=np.ascontiguousarray(f0_values, dtype="<f8"),
        f0_uncertainty=np.ascontiguousarray(
            f0_uncertainty, dtype="<f8"
        ),
        f0_support=np.ascontiguousarray(f0_support, dtype="|b1"),
        f0_reason_codes=np.ascontiguousarray(
            f0_reason_codes, dtype="<i4"
        ),
        f1_frames=np.ascontiguousarray(f1_frames, dtype="<f8"),
        f1_eigenvalues=np.ascontiguousarray(
            f1_eigenvalues, dtype="<f8"
        ),
        f1_support_count=np.ascontiguousarray(
            f1_support_count, dtype="<i8"
        ),
        f1_support=np.ascontiguousarray(f1_support, dtype="|b1"),
        f1_reason_codes=np.ascontiguousarray(
            f1_reason_codes, dtype="<i4"
        ),
        f2_coordinates=np.ascontiguousarray(
            f2_coordinates, dtype="<f8"
        ),
        f2_amplitude=np.ascontiguousarray(f2_amplitude, dtype="<f8"),
        f2_support=np.ascontiguousarray(f2_support, dtype="|b1"),
        f2_reason_codes=np.ascontiguousarray(
            f2_reason_codes, dtype="<i4"
        ),
    )


def _build_case(
    spec: RepresentationPhantomSpec,
    shared: _Shared,
    graph: _Graph,
    *,
    case_id: str,
    case_index: int,
) -> PhantomCase:
    response = _generate_accounted_response(
        spec,
        shared.ambient_basis,
        shared.grid_coordinates,
        case_id=case_id,
    )
    estimators = _derive_estimators(
        spec,
        response,
        graph.edges,
        shared.center_support_mask,
    )
    observation_identities = np.column_stack(
        (
            shared.vertex_identities,
            np.full(spec.row_count, case_index, dtype="<i8"),
        )
    )
    return PhantomCase(
        spec=spec,
        case_id=case_id,
        case_index=case_index,
        states=shared.states,
        vertex_identities=shared.vertex_identities,
        observation_identities=observation_identities,
        valid_mask=shared.valid_mask,
        center_support_mask=shared.center_support_mask,
        accounted_response=response,
        neighbor_indices=graph.neighbor_indices,
        edges=graph.edges,
        graph_weights=graph.graph_weights,
        components=graph.components,
        degree=graph.degree,
        two_core_mask=graph.two_core_mask,
        cycle_support=graph.cycle_support,
        **{
            name: getattr(estimators, name)
            for name in _DerivedEstimators.__dataclass_fields__
        },
    )


def generate_representation_phantom(
    spec: RepresentationPhantomSpec | None = None,
) -> RepresentationPhantom:
    """Generate the canonical paired phantom."""

    return RepresentationPhantom.generate(spec)
