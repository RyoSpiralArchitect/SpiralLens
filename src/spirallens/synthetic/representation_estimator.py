"""Truth-free crossed-graph estimator inputs for representation phantoms.

The frozen P1 representation phantom stores one development mutual-kNN
estimate.  This module does not reinterpret that estimate.  It exposes only
the observable arrays needed to recompute a local rank-two field on a caller
supplied ``FIELD_ESTIMATION`` graph.

The estimator uses fit probes to obtain local projectors and one deterministic
global reference plane.  Evaluation probes are projected through each local
projector and then expressed in that frozen reference:

``z_i = U_i.T @ s_i``
``s_tilde_i = U_i @ z_i``
``psi_i = B.T @ s_tilde_i``

Consequently a local frame gauge ``U_i -> U_i R_i`` cancels exactly between
``U_i`` and ``z_i``.  Amplitude and direction are derived from the same final
two-channel ``psi_i``.  The result is a model-free Level-0 calibration
observable, not a winding, core, topology, or subject claim.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, fields
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256
from spirallens.graphs import GraphConstructionReceipt, GraphPurpose

from .representation_phantom import RepresentationPhantomSpec

REPRESENTATION_ESTIMATOR_INPUT_RECEIPT_VERSION = (
    "spirallens.representation-estimator-input-receipt.v0.1"
)
REPRESENTATION_FIELD_ESTIMATE_RECEIPT_VERSION = (
    "spirallens.representation-field-estimate-receipt.v0.2"
)
REPRESENTATION_FIELD_ESTIMATOR_ID = (
    "local-rank-two-projector-global-reference-lift-v0.2"
)
REPRESENTATION_FIELD_EDGE_NAMESPACE = "graph-input-row-position"
REPRESENTATION_FIELD_SUPPORT_RULE_ID = "valid-degree-two-lambda2-scale-tolerance-v0.1"
REPRESENTATION_FIELD_CLAIM_CEILING = "level_0"
REPRESENTATION_FIELD_RECORD_SCOPE = "in-memory-fingerprint-only"
REPRESENTATION_FIELD_PERSISTENCE_ROUND_TRIP_SUPPORTED = False

_INPUT_PSEUDONYM = re.compile(r"^rpi_[0-9a-f]{32}$")
_PRIMARY_UNIT = re.compile(r"^representation-unit-[0-9a-f]{32}$")
_FLOAT = np.dtype("<f8")
_INT64 = np.dtype("<i8")
_BOOL = np.dtype("|b1")
_INT32 = np.dtype("<i4")
_FIELD_FACTORY_TOKEN = object()

FloatArray = NDArray[np.float64]
Int64Array = NDArray[np.int64]
BoolArray = NDArray[np.bool_]
Int32Array = NDArray[np.int32]


class RepresentationEstimatorError(ValueError):
    """Raised when the truth-free representation estimator contract fails."""


def _immutable(
    value: object,
    *,
    dtype: np.dtype[object],
    ndim: int,
    label: str,
) -> NDArray[np.generic]:
    source = np.asarray(value)
    if source.ndim != ndim:
        raise RepresentationEstimatorError(f"{label} must have rank {ndim}")
    if dtype.kind == "f" and source.dtype.kind != "f":
        raise TypeError(f"{label} must have a floating dtype")
    if dtype.kind == "i" and source.dtype.kind not in {"i", "u"}:
        raise TypeError(f"{label} must have an integer, non-boolean dtype")
    if dtype.kind == "b" and source.dtype.kind != "b":
        raise TypeError(f"{label} must have a boolean dtype")
    result = np.array(source, dtype=dtype, order="C", copy=True)
    if dtype.kind == "i" and not np.array_equal(
        result.astype(source.dtype, copy=False),
        source,
    ):
        raise RepresentationEstimatorError(
            f"{label} does not round-trip exactly through {dtype.str}"
        )
    if not np.all(np.isfinite(result)):
        raise RepresentationEstimatorError(f"{label} must contain only finite values")
    result[result == 0] = 0
    backing = result.tobytes(order="C")
    return np.frombuffer(backing, dtype=dtype).reshape(result.shape)


def _array_sha256(value: NDArray[np.generic]) -> str:
    descriptor = canonical_json_bytes(
        {
            "dtype": value.dtype.str,
            "shape": list(value.shape),
        }
    )
    return hashlib.sha256(descriptor + b"\x00" + value.tobytes(order="C")).hexdigest()


def _array_fingerprint(value: NDArray[np.generic]) -> dict[str, object]:
    return {
        "dtype": value.dtype.str,
        "shape": list(value.shape),
        "sha256": _array_sha256(value),
    }


def _sign_canonical_columns(value: FloatArray) -> FloatArray:
    result = np.array(value, dtype=_FLOAT, order="C", copy=True)
    for column_index in range(result.shape[1]):
        column = result[:, column_index]
        anchor = int(np.argmax(np.abs(column)))
        if column[anchor] < 0.0:
            result[:, column_index] *= -1.0
    return np.ascontiguousarray(result, dtype=_FLOAT)


def _leading_frame(covariance: FloatArray) -> tuple[FloatArray, FloatArray]:
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(-eigenvalues, kind="stable")
    ordered = np.maximum(eigenvalues[order], 0.0)
    frame = _sign_canonical_columns(eigenvectors[:, order[:2]])
    top_three = np.zeros(3, dtype=_FLOAT)
    top_three[: min(3, ordered.shape[0])] = ordered[:3]
    return frame, top_three


def _support_layout(
    *,
    valid_mask: BoolArray,
    support_count: Int64Array,
    top_three_eigenvalues: FloatArray,
) -> tuple[BoolArray, Int32Array]:
    """Apply the one shared rank-support and reason-code rule."""

    rank_tolerance = np.maximum(
        top_three_eigenvalues[:, 0] * 1e-12,
        np.finfo(np.float64).eps,
    )
    support = (
        valid_mask
        & (support_count >= 2)
        & (top_three_eigenvalues[:, 1] > rank_tolerance)
    )
    reason_codes = np.zeros(valid_mask.shape[0], dtype=_INT32)
    reason_codes[~valid_mask] = 1
    reason_codes[valid_mask & (support_count < 2)] = 2
    reason_codes[
        valid_mask
        & (support_count >= 2)
        & (top_three_eigenvalues[:, 1] <= rank_tolerance)
    ] = 3
    return support, reason_codes


def _content_pseudonym(
    *,
    spec: RepresentationPhantomSpec,
    vertex_ids: Int64Array,
    grid_coordinates: FloatArray,
    states: FloatArray,
    accounted_response: FloatArray,
    valid_mask: BoolArray,
) -> str:
    digest = canonical_json_sha256(
        {
            "domain_version": (
                "spirallens.representation-estimator-input-content.v0.1"
            ),
            "spec_sha256": spec.canonical_sha256,
            "arrays": {
                "vertex_ids": _array_fingerprint(vertex_ids),
                "grid_coordinates": _array_fingerprint(grid_coordinates),
                "states": _array_fingerprint(states),
                "accounted_response": _array_fingerprint(accounted_response),
                "valid_mask": _array_fingerprint(valid_mask),
            },
        }
    )
    return f"rpi_{digest[:32]}"


@dataclass(frozen=True, slots=True)
class RepresentationEstimatorInputs:
    """Only arrays a crossed-graph field estimator may observe.

    Outcome labels, case indices, supplied charge, center anchors, existing
    F0/F1/F2 outputs, cycles, and loop observables are absent by construction.
    """

    input_id: str
    spec: RepresentationPhantomSpec
    vertex_ids: Int64Array
    grid_coordinates: FloatArray
    states: FloatArray
    accounted_response: FloatArray
    valid_mask: BoolArray

    receipt_version: ClassVar[str] = REPRESENTATION_ESTIMATOR_INPUT_RECEIPT_VERSION
    _ARRAY_LAYOUT: ClassVar[dict[str, tuple[np.dtype[object], int]]] = {
        "vertex_ids": (_INT64, 1),
        "grid_coordinates": (_FLOAT, 2),
        "states": (_FLOAT, 2),
        "accounted_response": (_FLOAT, 3),
        "valid_mask": (_BOOL, 1),
    }

    def __post_init__(self) -> None:
        if not isinstance(self.spec, RepresentationPhantomSpec):
            raise TypeError("spec must be a RepresentationPhantomSpec")
        if (
            not isinstance(self.input_id, str)
            or _INPUT_PSEUDONYM.fullmatch(self.input_id) is None
        ):
            raise RepresentationEstimatorError(
                "input_id must be a label-free content pseudonym"
            )
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
        row_count = self.spec.row_count
        expected = {
            "vertex_ids": (row_count,),
            "grid_coordinates": (row_count, 2),
            "states": (row_count, self.spec.ambient_dimension),
            "accounted_response": (
                row_count,
                self.spec.probe_count,
                self.spec.ambient_dimension,
            ),
            "valid_mask": (row_count,),
        }
        for name, shape in expected.items():
            if getattr(self, name).shape != shape:
                raise RepresentationEstimatorError(
                    f"{name} has shape {getattr(self, name).shape}; expected {shape}"
                )
        if len(set(self.vertex_ids.tolist())) != row_count:
            raise RepresentationEstimatorError("vertex_ids must be unique")
        expected_input_id = _content_pseudonym(
            spec=self.spec,
            vertex_ids=self.vertex_ids,
            grid_coordinates=self.grid_coordinates,
            states=self.states,
            accounted_response=self.accounted_response,
            valid_mask=self.valid_mask,
        )
        if self.input_id != expected_input_id:
            raise RepresentationEstimatorError(
                "input_id differs from the observable content"
            )

    @property
    def primary_unit_id(self) -> str:
        return f"representation-unit-{self.input_id.removeprefix('rpi_')}"

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": REPRESENTATION_FIELD_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                REPRESENTATION_FIELD_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "input_id": self.input_id,
            "primary_unit_id": self.primary_unit_id,
            "spec_sha256": self.spec.canonical_sha256,
            "fit_probe_indices": list(self.spec.even_probe_indices),
            "evaluation_probe_indices": list(self.spec.odd_probe_indices),
            "arrays": {
                item.name: _array_fingerprint(getattr(self, item.name))
                for item in fields(self)
                if item.name in self._ARRAY_LAYOUT
            },
            "truth_present": False,
            "case_label_present": False,
            "center_anchor_present": False,
            "charge_present": False,
            "cycle_present": False,
            "loop_observable_present": False,
            "subject_data_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def build_representation_estimator_inputs(
    *,
    spec: RepresentationPhantomSpec,
    vertex_ids: object,
    grid_coordinates: object,
    states: object,
    accounted_response: object,
    valid_mask: object,
) -> RepresentationEstimatorInputs:
    """Build a label-free estimator input from explicitly allowed arrays."""

    if not isinstance(spec, RepresentationPhantomSpec):
        raise TypeError("spec must be a RepresentationPhantomSpec")
    normalized_vertex_ids = _immutable(
        vertex_ids,
        dtype=_INT64,
        ndim=1,
        label="vertex_ids",
    )
    normalized_coordinates = _immutable(
        grid_coordinates,
        dtype=_FLOAT,
        ndim=2,
        label="grid_coordinates",
    )
    normalized_states = _immutable(
        states,
        dtype=_FLOAT,
        ndim=2,
        label="states",
    )
    normalized_response = _immutable(
        accounted_response,
        dtype=_FLOAT,
        ndim=3,
        label="accounted_response",
    )
    normalized_valid = _immutable(
        valid_mask,
        dtype=_BOOL,
        ndim=1,
        label="valid_mask",
    )
    return RepresentationEstimatorInputs(
        input_id=_content_pseudonym(
            spec=spec,
            vertex_ids=normalized_vertex_ids,
            grid_coordinates=normalized_coordinates,
            states=normalized_states,
            accounted_response=normalized_response,
            valid_mask=normalized_valid,
        ),
        spec=spec,
        vertex_ids=normalized_vertex_ids,
        grid_coordinates=normalized_coordinates,
        states=normalized_states,
        accounted_response=normalized_response,
        valid_mask=normalized_valid,
    )


@dataclass(frozen=True, slots=True, init=False)
class RepresentationFieldEstimate:
    """Factory-produced local-projector field in one frozen reference."""

    estimator_inputs: RepresentationEstimatorInputs
    field_graph: GraphConstructionReceipt
    reference_frame: FloatArray
    local_frames: FloatArray
    local_coordinates: FloatArray
    ambient_section: FloatArray
    section_values: FloatArray
    amplitude: FloatArray
    top_three_eigenvalues: FloatArray
    relative_rank_gap: FloatArray
    edge_coherence: FloatArray
    support_count: Int64Array
    support: BoolArray
    reason_codes: Int32Array

    receipt_version: ClassVar[str] = REPRESENTATION_FIELD_ESTIMATE_RECEIPT_VERSION
    _ARRAY_LAYOUT: ClassVar[dict[str, tuple[np.dtype[object], int]]] = {
        "reference_frame": (_FLOAT, 2),
        "local_frames": (_FLOAT, 3),
        "local_coordinates": (_FLOAT, 2),
        "ambient_section": (_FLOAT, 2),
        "section_values": (_FLOAT, 2),
        "amplitude": (_FLOAT, 1),
        "top_three_eigenvalues": (_FLOAT, 2),
        "relative_rank_gap": (_FLOAT, 1),
        "edge_coherence": (_FLOAT, 1),
        "support_count": (_INT64, 1),
        "support": (_BOOL, 1),
        "reason_codes": (_INT32, 1),
    }

    def __init__(
        self,
        *,
        _factory_token: object = None,
        estimator_inputs: RepresentationEstimatorInputs,
        field_graph: GraphConstructionReceipt,
        reference_frame: object,
        local_frames: object,
        local_coordinates: object,
        ambient_section: object,
        section_values: object,
        amplitude: object,
        top_three_eigenvalues: object,
        relative_rank_gap: object,
        edge_coherence: object,
        support_count: object,
        support: object,
        reason_codes: object,
    ) -> None:
        if _factory_token is not _FIELD_FACTORY_TOKEN:
            raise RepresentationEstimatorError(
                "field estimates must be produced by estimate_representation_field"
            )
        if not isinstance(estimator_inputs, RepresentationEstimatorInputs):
            raise TypeError("estimator_inputs must be RepresentationEstimatorInputs")
        if not isinstance(field_graph, GraphConstructionReceipt):
            raise TypeError("field_graph must be a GraphConstructionReceipt")
        object.__setattr__(self, "estimator_inputs", estimator_inputs)
        object.__setattr__(self, "field_graph", field_graph)
        values = {
            "reference_frame": reference_frame,
            "local_frames": local_frames,
            "local_coordinates": local_coordinates,
            "ambient_section": ambient_section,
            "section_values": section_values,
            "amplitude": amplitude,
            "top_three_eigenvalues": top_three_eigenvalues,
            "relative_rank_gap": relative_rank_gap,
            "edge_coherence": edge_coherence,
            "support_count": support_count,
            "support": support,
            "reason_codes": reason_codes,
        }
        for name, (dtype, ndim) in self._ARRAY_LAYOUT.items():
            object.__setattr__(
                self,
                name,
                _immutable(
                    values[name],
                    dtype=dtype,
                    ndim=ndim,
                    label=name,
                ),
            )
        self._validate()

    def _validate(self) -> None:
        inputs = self.estimator_inputs
        row_count = inputs.spec.row_count
        dimension = inputs.spec.ambient_dimension
        expected = {
            "reference_frame": (dimension, 2),
            "local_frames": (row_count, dimension, 2),
            "local_coordinates": (row_count, 2),
            "ambient_section": (row_count, dimension),
            "section_values": (row_count, 2),
            "amplitude": (row_count,),
            "top_three_eigenvalues": (row_count, 3),
            "relative_rank_gap": (row_count,),
            "edge_coherence": (row_count,),
            "support_count": (row_count,),
            "support": (row_count,),
            "reason_codes": (row_count,),
        }
        for name, shape in expected.items():
            if getattr(self, name).shape != shape:
                raise RepresentationEstimatorError(f"{name} has the wrong shape")
        if self.field_graph.specification.purpose is not GraphPurpose.FIELD_ESTIMATION:
            raise RepresentationEstimatorError(
                "field estimate requires a field-estimation graph"
            )
        graph_input = self.field_graph.graph_input
        if graph_input.primary_unit_id != inputs.primary_unit_id:
            raise RepresentationEstimatorError(
                "field graph and estimator input primary units differ"
            )
        if not np.array_equal(graph_input.vertex_ids, inputs.vertex_ids):
            raise RepresentationEstimatorError(
                "field graph and estimator input row identities differ"
            )
        if not np.array_equal(graph_input.states, inputs.states):
            raise RepresentationEstimatorError(
                "field graph and estimator input states differ"
            )
        if not np.allclose(
            self.reference_frame.T @ self.reference_frame,
            np.eye(2),
            rtol=1e-12,
            atol=1e-12,
        ):
            raise RepresentationEstimatorError(
                "reference frame must have orthonormal columns"
            )
        grams = np.einsum(
            "ndi,ndj->nij",
            self.local_frames,
            self.local_frames,
            optimize=False,
        )
        if not np.allclose(
            grams,
            np.eye(2)[None, :, :],
            rtol=1e-11,
            atol=1e-11,
        ):
            raise RepresentationEstimatorError(
                "local frames must have orthonormal columns"
            )
        expected_ambient = np.einsum(
            "ndi,ni->nd",
            self.local_frames,
            self.local_coordinates,
            optimize=False,
        )
        if not np.allclose(
            self.ambient_section,
            expected_ambient,
            rtol=1e-12,
            atol=1e-12,
        ):
            raise RepresentationEstimatorError(
                "ambient_section differs from the local-frame reconstruction"
            )
        expected_section = self.ambient_section @ self.reference_frame
        if not np.allclose(
            self.section_values,
            expected_section,
            rtol=1e-12,
            atol=1e-12,
        ):
            raise RepresentationEstimatorError(
                "section_values differ from the frozen-reference lift"
            )
        expected_amplitude = np.linalg.norm(self.section_values, axis=1)
        if not np.array_equal(self.amplitude, expected_amplitude):
            raise RepresentationEstimatorError(
                "amplitude must derive from the same final section values"
            )
        if np.any(self.relative_rank_gap < 0.0):
            raise RepresentationEstimatorError("relative rank gaps must be nonnegative")
        if np.any(self.edge_coherence < 0.0) or np.any(self.edge_coherence > 1.0):
            raise RepresentationEstimatorError("edge coherence must lie in [0, 1]")
        if np.any(self.support_count < 0):
            raise RepresentationEstimatorError("support counts must be nonnegative")
        expected_support, expected_reasons = _support_layout(
            valid_mask=inputs.valid_mask,
            support_count=self.support_count,
            top_three_eigenvalues=self.top_three_eigenvalues,
        )
        if not np.array_equal(self.support, expected_support):
            raise RepresentationEstimatorError(
                "support differs from the estimator layout rule"
            )
        if not np.array_equal(self.reason_codes, expected_reasons):
            raise RepresentationEstimatorError(
                "reason_codes differ from the estimator layout rule"
            )

    @property
    def field_consumption_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "domain_version": ("spirallens.field-neighborhood-consumption.v0.2"),
                "graph_receipt_sha256": self.field_graph.fingerprint_sha256,
                "canonical_edge_endpoint_namespace": (
                    REPRESENTATION_FIELD_EDGE_NAMESPACE
                ),
                "canonical_edges": _array_fingerprint(self.field_graph.canonical_edges),
                "support_count": _array_fingerprint(self.support_count),
            }
        )

    @property
    def estimator_input_fingerprint_sha256(self) -> str:
        """Expose the generic crossed-pipeline input binding."""

        return self.estimator_inputs.fingerprint_sha256

    @property
    def field_graph_fingerprint_sha256(self) -> str:
        """Expose the generic crossed-pipeline graph binding."""

        return self.field_graph.fingerprint_sha256

    @property
    def identifiability_score(self) -> FloatArray:
        """Expose the true local covariance rank gap to generic gates."""

        return self.relative_rank_gap

    @property
    def substantive_output_sha256(self) -> str:
        """Digest only arrays that can alter generic qualification."""

        return canonical_json_sha256(
            {
                "section_values": _array_fingerprint(self.section_values),
                "amplitude": _array_fingerprint(self.amplitude),
                "identifiability_score": _array_fingerprint(self.identifiability_score),
                "edge_coherence": _array_fingerprint(self.edge_coherence),
            }
        )

    @property
    def output_sha256(self) -> str:
        return canonical_json_sha256(
            {
                name: _array_fingerprint(getattr(self, name))
                for name in self._ARRAY_LAYOUT
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": REPRESENTATION_FIELD_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                REPRESENTATION_FIELD_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "claim_ceiling": REPRESENTATION_FIELD_CLAIM_CEILING,
            "estimator_id": REPRESENTATION_FIELD_ESTIMATOR_ID,
            "support_rule_id": REPRESENTATION_FIELD_SUPPORT_RULE_ID,
            "canonical_edge_endpoint_namespace": (REPRESENTATION_FIELD_EDGE_NAMESPACE),
            "estimator_input_fingerprint_sha256": (
                self.estimator_inputs.fingerprint_sha256
            ),
            "primary_unit_id": self.estimator_inputs.primary_unit_id,
            "field_graph_fingerprint_sha256": (self.field_graph.fingerprint_sha256),
            "field_graph_family": (self.field_graph.family_identity.family.value),
            "field_consumption_sha256": self.field_consumption_sha256,
            "substantive_output_sha256": self.substantive_output_sha256,
            "output_sha256": self.output_sha256,
            "arrays": {
                name: _array_fingerprint(getattr(self, name))
                for name in self._ARRAY_LAYOUT
            },
            "fit_role": "fit-probes-only",
            "evaluation_role": "evaluation-probes-only",
            "trivialization_id": (
                "fit-split-global-reference-after-local-projector-v0.1"
            ),
            "same_object_amplitude_and_direction": True,
            "local_frame_gauge_cancelled_by_projector_reconstruction": True,
            "truth_read": False,
            "anchor_read": False,
            "charge_read": False,
            "loop_read": False,
            "integer_output_authorized": False,
            "core_localized": False,
            "topology_claimed": False,
            "semantic_claimed": False,
            "subject_access_authorized": False,
            "d0_d8_advanced": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _row_position_adjacency(
    field_graph: GraphConstructionReceipt,
) -> tuple[tuple[int, ...], ...]:
    """Decode receipt edges in their declared row-position namespace."""

    row_count = field_graph.graph_input.states.shape[0]
    adjacency: list[list[int]] = [[] for _ in range(row_count)]
    for left_raw, right_raw in field_graph.canonical_edges:
        left = int(left_raw)
        right = int(right_raw)
        if not (0 <= left < right < row_count):
            raise RepresentationEstimatorError(
                "field graph contains an invalid row-position edge"
            )
        adjacency[left].append(right)
        adjacency[right].append(left)
    return tuple(tuple(sorted(items)) for items in adjacency)


def _covariance(
    response: FloatArray,
    *,
    rows: tuple[int, ...],
    probes: tuple[int, ...],
) -> FloatArray:
    dimension = response.shape[2]
    if not rows:
        return np.zeros((dimension, dimension), dtype=_FLOAT)
    samples = response[
        np.asarray(rows, dtype=_INT64)[:, None],
        np.asarray(probes, dtype=_INT64)[None, :],
        :,
    ].reshape(-1, dimension)
    centered = samples - samples.mean(axis=0, keepdims=True)
    return np.ascontiguousarray(
        centered.T @ centered / float(samples.shape[0]),
        dtype=_FLOAT,
    )


def estimate_representation_field(
    estimator_inputs: RepresentationEstimatorInputs,
    field_graph: GraphConstructionReceipt,
) -> RepresentationFieldEstimate:
    """Estimate one truth-free local-projector field on ``field_graph``."""

    if not isinstance(estimator_inputs, RepresentationEstimatorInputs):
        raise TypeError("estimator_inputs must be RepresentationEstimatorInputs")
    if not isinstance(field_graph, GraphConstructionReceipt):
        raise TypeError("field_graph must be a GraphConstructionReceipt")
    if field_graph.specification.purpose is not GraphPurpose.FIELD_ESTIMATION:
        raise RepresentationEstimatorError(
            "field_graph must be declared for field estimation"
        )
    graph_input = field_graph.graph_input
    if (
        graph_input.primary_unit_id != estimator_inputs.primary_unit_id
        or not np.array_equal(graph_input.vertex_ids, estimator_inputs.vertex_ids)
        or not np.array_equal(graph_input.states, estimator_inputs.states)
    ):
        raise RepresentationEstimatorError(
            "field graph does not bind the estimator input"
        )

    spec = estimator_inputs.spec
    response = estimator_inputs.accounted_response
    row_count = spec.row_count
    dimension = spec.ambient_dimension
    fit_probes = spec.even_probe_indices
    evaluation_probes = spec.odd_probe_indices

    global_samples = response[
        :,
        np.asarray(fit_probes, dtype=_INT64),
        :,
    ].reshape(-1, dimension)
    global_centered = global_samples - global_samples.mean(
        axis=0,
        keepdims=True,
    )
    global_covariance = (
        global_centered.T @ global_centered / float(global_centered.shape[0])
    )
    reference_frame, _reference_eigenvalues = _leading_frame(
        np.ascontiguousarray(global_covariance, dtype=_FLOAT)
    )

    adjacency = _row_position_adjacency(field_graph)
    local_frames = np.empty((row_count, dimension, 2), dtype=_FLOAT)
    top_three = np.zeros((row_count, 3), dtype=_FLOAT)
    support_count = np.asarray(
        [len(items) for items in adjacency],
        dtype=_INT64,
    )
    for row, neighbors in enumerate(adjacency):
        frame, eigenvalues = _leading_frame(
            _covariance(
                response,
                rows=neighbors,
                probes=fit_probes,
            )
        )
        local_frames[row] = frame
        top_three[row] = eigenvalues

    odd_mean = response[
        :,
        np.asarray(evaluation_probes, dtype=_INT64),
        :,
    ].mean(axis=1)
    local_coordinates = np.einsum(
        "ndi,nd->ni",
        local_frames,
        odd_mean,
        optimize=False,
    )
    ambient_section = np.einsum(
        "ndi,ni->nd",
        local_frames,
        local_coordinates,
        optimize=False,
    )
    section_values = ambient_section @ reference_frame
    amplitude = np.linalg.norm(section_values, axis=1)

    denominator = np.maximum(
        top_three[:, 0],
        np.finfo(np.float64).tiny,
    )
    relative_rank_gap = np.maximum(
        (top_three[:, 1] - top_three[:, 2]) / denominator,
        0.0,
    )
    edge_coherence = np.ones(row_count, dtype=_FLOAT)
    for row, neighbors in enumerate(adjacency):
        if not neighbors:
            edge_coherence[row] = 0.0
            continue
        edge_coherence[row] = min(
            float(
                np.min(
                    np.linalg.svd(
                        local_frames[row].T @ local_frames[neighbor],
                        compute_uv=False,
                    )
                )
            )
            for neighbor in neighbors
        )
    edge_coherence = np.clip(edge_coherence, 0.0, 1.0)

    support, reason_codes = _support_layout(
        valid_mask=estimator_inputs.valid_mask,
        support_count=support_count,
        top_three_eigenvalues=top_three,
    )

    return RepresentationFieldEstimate(
        _factory_token=_FIELD_FACTORY_TOKEN,
        estimator_inputs=estimator_inputs,
        field_graph=field_graph,
        reference_frame=reference_frame,
        local_frames=local_frames,
        local_coordinates=local_coordinates,
        ambient_section=ambient_section,
        section_values=section_values,
        amplitude=amplitude,
        top_three_eigenvalues=top_three,
        relative_rank_gap=relative_rank_gap,
        edge_coherence=edge_coherence,
        support_count=support_count,
        support=support,
        reason_codes=reason_codes,
    )
