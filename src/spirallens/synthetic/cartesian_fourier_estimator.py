"""Truth-free F2 estimator for Cartesian Fourier-domain phantoms.

The first harmonic is estimated independently on the interleaved fit and
evaluation quadratures.  The evaluation harmonic is the final two-channel
section; the fit harmonic supplies an identification check.  A caller-supplied
field graph determines both observable neighborhood support and a graph-local
directional-coherence diagnostic.  Consequently the A axis changes a
claim-relevant prerequisite array, not merely receipt metadata, without
reading oracle loops, anchors, charges, or dispositions.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_sha256
from spirallens.graphs import GraphConstructionReceipt, GraphPurpose
from spirallens.graphs.common import array_fingerprint

from .cartesian_fourier_domain_phantom import CartesianFourierEstimatorInputs

_FLOAT = np.dtype("<f8")
_INT64 = np.dtype("<i8")
_BOOL = np.dtype("|b1")
_FIELD_FACTORY_TOKEN = object()

FloatArray = NDArray[np.float64]
Int64Array = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

CARTESIAN_FOURIER_FIELD_ESTIMATOR_ID = (
    "interleaved-first-harmonic-graph-local-direction-v0.4"
)
CARTESIAN_FOURIER_FIELD_RECEIPT_VERSION = (
    "spirallens.cartesian-fourier-field-estimate.v0.4"
)
_GRAPH_DIRECTION_SMOOTHING_WEIGHT = 0.125


class CartesianFourierEstimatorError(ValueError):
    """Raised when the truth-free Fourier estimator contract is violated."""


def _immutable(
    value: object,
    *,
    dtype: np.dtype[object],
    ndim: int,
    label: str,
) -> NDArray[np.generic]:
    source = np.asarray(value)
    if source.ndim != ndim:
        raise CartesianFourierEstimatorError(f"{label} must have rank {ndim}")
    if dtype.kind == "f" and source.dtype.kind != "f":
        raise TypeError(f"{label} must have a floating dtype")
    if dtype.kind == "i" and source.dtype.kind not in {"i", "u"}:
        raise TypeError(f"{label} must have an integer dtype")
    if dtype.kind == "b" and source.dtype.kind != "b":
        raise TypeError(f"{label} must have a boolean dtype")
    result = np.array(source, dtype=dtype, order="C", copy=True)
    if not np.all(np.isfinite(result)):
        raise CartesianFourierEstimatorError(f"{label} must contain only finite values")
    if dtype.kind == "f":
        result[result == 0.0] = 0.0
    backing = result.tobytes(order="C")
    return np.frombuffer(backing, dtype=dtype).reshape(result.shape)


def _moment(
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


def _support_counts(
    *,
    row_ids: Int64Array,
    edges: Int64Array,
) -> Int64Array:
    counts = np.zeros(row_ids.shape[0], dtype=_INT64)
    for left_raw, right_raw in edges:
        left = int(left_raw)
        right = int(right_raw)
        if (
            left < 0
            or right < 0
            or left >= row_ids.shape[0]
            or right >= row_ids.shape[0]
        ):
            raise CartesianFourierEstimatorError(
                "field graph edge references an unknown row position"
            )
        counts[left] += 1
        counts[right] += 1
    return counts


def _graph_directional_coherence(
    *,
    section_values: FloatArray,
    edges: Int64Array,
) -> FloatArray:
    """Return per-row mean oriented-vector agreement on actual graph edges."""

    amplitudes = np.linalg.norm(section_values, axis=1)
    unit = np.zeros_like(section_values)
    supported = amplitudes > np.finfo(np.float64).tiny
    unit[supported] = section_values[supported] / amplitudes[supported, None]
    sums = np.zeros(section_values.shape[0], dtype=_FLOAT)
    counts = np.zeros(section_values.shape[0], dtype=_INT64)
    for left_raw, right_raw in edges:
        left = int(left_raw)
        right = int(right_raw)
        if (
            left < 0
            or right < 0
            or left >= section_values.shape[0]
            or right >= section_values.shape[0]
        ):
            raise CartesianFourierEstimatorError(
                "field graph edge references an unknown row position"
            )
        if not (supported[left] and supported[right]):
            continue
        agreement = float(
            np.clip(
                0.5 * (1.0 + float(np.dot(unit[left], unit[right]))),
                0.0,
                1.0,
            )
        )
        sums[left] += agreement
        sums[right] += agreement
        counts[left] += 1
        counts[right] += 1
    result = np.zeros(section_values.shape[0], dtype=_FLOAT)
    nonzero = counts > 0
    result[nonzero] = sums[nonzero] / counts[nonzero]
    return result


def _graph_local_section(
    *,
    raw_section_values: FloatArray,
    edges: Int64Array,
) -> FloatArray:
    """Apply one fixed graph-local direction step while preserving amplitude."""

    amplitudes = np.linalg.norm(raw_section_values, axis=1)
    supported = amplitudes > np.finfo(np.float64).tiny
    unit = np.zeros_like(raw_section_values)
    unit[supported] = raw_section_values[supported] / amplitudes[supported, None]
    neighbor_sum = np.zeros_like(raw_section_values)
    neighbor_count = np.zeros(raw_section_values.shape[0], dtype=_INT64)
    for left_raw, right_raw in edges:
        left = int(left_raw)
        right = int(right_raw)
        if (
            left < 0
            or right < 0
            or left >= raw_section_values.shape[0]
            or right >= raw_section_values.shape[0]
        ):
            raise CartesianFourierEstimatorError(
                "field graph edge references an unknown row position"
            )
        if supported[right]:
            neighbor_sum[left] += unit[right]
            neighbor_count[left] += 1
        if supported[left]:
            neighbor_sum[right] += unit[left]
            neighbor_count[right] += 1
    result = np.zeros_like(raw_section_values)
    for row in np.flatnonzero(supported):
        direction = unit[row]
        if neighbor_count[row] > 0:
            neighbor_mean = neighbor_sum[row] / neighbor_count[row]
            direction = (
                1.0 - _GRAPH_DIRECTION_SMOOTHING_WEIGHT
            ) * direction + _GRAPH_DIRECTION_SMOOTHING_WEIGHT * neighbor_mean
        norm = float(np.linalg.norm(direction))
        if norm <= np.finfo(np.float64).tiny:
            direction = unit[row]
            norm = 1.0
        result[row] = amplitudes[row] * direction / norm
    result[result == 0.0] = 0.0
    return result


@dataclass(frozen=True, slots=True, init=False)
class CartesianFourierFieldEstimate:
    """Factory-produced, label-free F2 section and graph support."""

    estimator_inputs: CartesianFourierEstimatorInputs
    field_graph: GraphConstructionReceipt
    fit_section_values: FloatArray
    section_values: FloatArray
    second_harmonic_values: FloatArray
    amplitude: FloatArray
    first_harmonic_dominance_ratio: FloatArray
    edge_coherence: FloatArray
    split_disagreement: FloatArray
    support_count: Int64Array
    support: BoolArray

    receipt_version: ClassVar[str] = CARTESIAN_FOURIER_FIELD_RECEIPT_VERSION
    _ARRAY_LAYOUT: ClassVar[dict[str, tuple[np.dtype[object], int]]] = {
        "fit_section_values": (_FLOAT, 2),
        "section_values": (_FLOAT, 2),
        "second_harmonic_values": (_FLOAT, 2),
        "amplitude": (_FLOAT, 1),
        "first_harmonic_dominance_ratio": (_FLOAT, 1),
        "edge_coherence": (_FLOAT, 1),
        "split_disagreement": (_FLOAT, 1),
        "support_count": (_INT64, 1),
        "support": (_BOOL, 1),
    }

    def __init__(
        self,
        *,
        _factory_token: object = None,
        estimator_inputs: CartesianFourierEstimatorInputs,
        field_graph: GraphConstructionReceipt,
        fit_section_values: object,
        section_values: object,
        second_harmonic_values: object,
        amplitude: object,
        first_harmonic_dominance_ratio: object,
        edge_coherence: object,
        split_disagreement: object,
        support_count: object,
        support: object,
    ) -> None:
        if _factory_token is not _FIELD_FACTORY_TOKEN:
            raise CartesianFourierEstimatorError(
                "field estimates must be factory-produced"
            )
        if not isinstance(
            estimator_inputs,
            CartesianFourierEstimatorInputs,
        ):
            raise TypeError("estimator_inputs must be CartesianFourierEstimatorInputs")
        if not isinstance(field_graph, GraphConstructionReceipt):
            raise TypeError("field_graph must be a GraphConstructionReceipt")
        object.__setattr__(self, "estimator_inputs", estimator_inputs)
        object.__setattr__(self, "field_graph", field_graph)
        values = {
            "fit_section_values": fit_section_values,
            "section_values": section_values,
            "second_harmonic_values": second_harmonic_values,
            "amplitude": amplitude,
            "first_harmonic_dominance_ratio": (first_harmonic_dominance_ratio),
            "edge_coherence": edge_coherence,
            "split_disagreement": split_disagreement,
            "support_count": support_count,
            "support": support,
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
        rows = inputs.row_ids.shape[0]
        expected = {
            "fit_section_values": (rows, 2),
            "section_values": (rows, 2),
            "second_harmonic_values": (rows, 2),
            "amplitude": (rows,),
            "first_harmonic_dominance_ratio": (rows,),
            "edge_coherence": (rows,),
            "split_disagreement": (rows,),
            "support_count": (rows,),
            "support": (rows,),
        }
        for name, shape in expected.items():
            if getattr(self, name).shape != shape:
                raise CartesianFourierEstimatorError(f"{name} has the wrong shape")
        graph_input = self.field_graph.graph_input
        if self.field_graph.specification.purpose is not GraphPurpose.FIELD_ESTIMATION:
            raise CartesianFourierEstimatorError("field graph has the wrong purpose")
        if not np.array_equal(
            graph_input.vertex_ids, inputs.row_ids
        ) or not np.array_equal(graph_input.states, inputs.states):
            raise CartesianFourierEstimatorError(
                "field graph does not bind the estimator-visible rows and states"
            )
        expected_fit = _graph_local_section(
            raw_section_values=_moment(
                angles=inputs.fit_angles_rad,
                values=inputs.fit_values,
                harmonic=1,
            ),
            edges=self.field_graph.canonical_edges,
        )
        expected_section = _graph_local_section(
            raw_section_values=_moment(
                angles=inputs.evaluation_angles_rad,
                values=inputs.evaluation_values,
                harmonic=1,
            ),
            edges=self.field_graph.canonical_edges,
        )
        expected_second = _moment(
            angles=inputs.evaluation_angles_rad,
            values=inputs.evaluation_values,
            harmonic=2,
        )
        if not np.array_equal(self.fit_section_values, expected_fit):
            raise CartesianFourierEstimatorError(
                "fit_section_values differ from the graph-local estimator"
            )
        if not np.array_equal(self.section_values, expected_section):
            raise CartesianFourierEstimatorError(
                "section_values differ from the graph-local estimator"
            )
        if not np.array_equal(
            self.second_harmonic_values,
            expected_second,
        ):
            raise CartesianFourierEstimatorError(
                "second_harmonic_values differ from the evaluation moment"
            )
        expected_amplitude = np.linalg.norm(self.section_values, axis=1)
        if not np.array_equal(self.amplitude, expected_amplitude):
            raise CartesianFourierEstimatorError(
                "amplitude must derive from the final section values"
            )
        expected_disagreement = np.linalg.norm(
            self.fit_section_values - self.section_values,
            axis=1,
        )
        if not np.array_equal(self.split_disagreement, expected_disagreement):
            raise CartesianFourierEstimatorError(
                "split_disagreement differs from the two independent estimates"
            )
        expected_counts = _support_counts(
            row_ids=inputs.row_ids,
            edges=self.field_graph.canonical_edges,
        )
        if not np.array_equal(self.support_count, expected_counts):
            raise CartesianFourierEstimatorError(
                "support_count differs from the consumed field graph"
            )
        if not np.array_equal(self.support, self.support_count >= 2):
            raise CartesianFourierEstimatorError(
                "support differs from the fixed degree rule"
            )
        if np.any(self.first_harmonic_dominance_ratio < 0.0):
            raise CartesianFourierEstimatorError(
                "first_harmonic_dominance_ratio must be nonnegative"
            )
        fit_amplitude = np.linalg.norm(self.fit_section_values, axis=1)
        second_amplitude = np.linalg.norm(
            self.second_harmonic_values,
            axis=1,
        )
        expected_dominance = fit_amplitude / np.maximum(
            fit_amplitude + second_amplitude,
            np.finfo(np.float64).tiny,
        )
        if not np.array_equal(
            self.first_harmonic_dominance_ratio,
            expected_dominance,
        ):
            raise CartesianFourierEstimatorError(
                "first_harmonic_dominance_ratio differs from the frozen harmonic rule"
            )
        if np.any(self.edge_coherence < 0.0) or np.any(self.edge_coherence > 1.0):
            raise CartesianFourierEstimatorError("edge_coherence must lie in [0, 1]")
        scale = np.maximum(
            np.maximum(fit_amplitude, self.amplitude),
            np.finfo(np.float64).tiny,
        )
        split_coherence = np.clip(
            1.0 - self.split_disagreement / scale,
            0.0,
            1.0,
        )
        expected_coherence = np.minimum(
            split_coherence,
            _graph_directional_coherence(
                section_values=self.section_values,
                edges=self.field_graph.canonical_edges,
            ),
        )
        if not np.array_equal(self.edge_coherence, expected_coherence):
            raise CartesianFourierEstimatorError(
                "edge_coherence differs from the graph-local rule"
            )

    @property
    def field_consumption_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "domain_version": (
                    "spirallens.cartesian-fourier-field-consumption.v0.1"
                ),
                "field_graph_fingerprint_sha256": (self.field_graph.fingerprint_sha256),
                "canonical_edges": array_fingerprint(self.field_graph.canonical_edges),
                "support_count": array_fingerprint(self.support_count),
            }
        )

    @property
    def field_graph_fingerprint_sha256(self) -> str:
        return self.field_graph.fingerprint_sha256

    @property
    def estimator_input_fingerprint_sha256(self) -> str:
        return self.estimator_inputs.fingerprint_sha256

    @property
    def identifiability_score(self) -> FloatArray:
        """Return the estimator-specific score used by generic gates."""

        return self.first_harmonic_dominance_ratio

    @property
    def substantive_output_sha256(self) -> str:
        """Digest arrays that can change qualification, excluding bookkeeping."""

        return canonical_json_sha256(
            {
                "section_values": array_fingerprint(self.section_values),
                "amplitude": array_fingerprint(self.amplitude),
                "identifiability_score": array_fingerprint(self.identifiability_score),
                "edge_coherence": array_fingerprint(self.edge_coherence),
            }
        )

    @property
    def output_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "substantive_output_sha256": self.substantive_output_sha256,
                "support_count": array_fingerprint(self.support_count),
                "support": array_fingerprint(self.support),
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": "in-memory-fingerprint-only",
            "persistence_round_trip_supported": False,
            "claim_scope": "model-free-instrument-qualification-only",
            "claim_ceiling": "level_0",
            "estimator_id": CARTESIAN_FOURIER_FIELD_ESTIMATOR_ID,
            "estimator_input_fingerprint_sha256": (
                self.estimator_inputs.fingerprint_sha256
            ),
            "field_graph_fingerprint_sha256": (self.field_graph.fingerprint_sha256),
            "field_graph_family": (self.field_graph.family_identity.family.value),
            "field_consumption_sha256": self.field_consumption_sha256,
            "substantive_output_sha256": self.substantive_output_sha256,
            "output_sha256": self.output_sha256,
            "arrays": {
                item.name: array_fingerprint(getattr(self, item.name))
                for item in fields(self)
                if item.name in self._ARRAY_LAYOUT
            },
            "fit_role": "fit-quadrature-only",
            "evaluation_role": "evaluation-quadrature-final-section",
            "graph_local_direction_smoothing_weight": (
                _GRAPH_DIRECTION_SMOOTHING_WEIGHT
            ),
            "graph_local_step_preserves_raw_amplitude": True,
            "same_object_amplitude_and_direction": True,
            "truth_read": False,
            "anchor_read": False,
            "charge_read": False,
            "loop_read": False,
            "integer_output_authorized": False,
            "topology_claimed": False,
            "subject_access_authorized": False,
            "d0_d8_advanced": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def estimate_cartesian_fourier_field(
    estimator_inputs: CartesianFourierEstimatorInputs,
    field_graph: GraphConstructionReceipt,
) -> CartesianFourierFieldEstimate:
    """Estimate the F2 section without reading the Cartesian oracle."""

    if not isinstance(
        estimator_inputs,
        CartesianFourierEstimatorInputs,
    ):
        raise TypeError("estimator_inputs must be CartesianFourierEstimatorInputs")
    if not isinstance(field_graph, GraphConstructionReceipt):
        raise TypeError("field_graph must be a GraphConstructionReceipt")
    graph_input = field_graph.graph_input
    if (
        field_graph.specification.purpose is not GraphPurpose.FIELD_ESTIMATION
        or not np.array_equal(graph_input.vertex_ids, estimator_inputs.row_ids)
        or not np.array_equal(graph_input.states, estimator_inputs.states)
    ):
        raise CartesianFourierEstimatorError(
            "field graph does not bind the estimator-visible rows and states"
        )
    raw_fit = _moment(
        angles=estimator_inputs.fit_angles_rad,
        values=estimator_inputs.fit_values,
        harmonic=1,
    )
    raw_evaluation = _moment(
        angles=estimator_inputs.evaluation_angles_rad,
        values=estimator_inputs.evaluation_values,
        harmonic=1,
    )
    second = _moment(
        angles=estimator_inputs.evaluation_angles_rad,
        values=estimator_inputs.evaluation_values,
        harmonic=2,
    )
    fit = _graph_local_section(
        raw_section_values=raw_fit,
        edges=field_graph.canonical_edges,
    )
    evaluation = _graph_local_section(
        raw_section_values=raw_evaluation,
        edges=field_graph.canonical_edges,
    )
    amplitude = np.linalg.norm(evaluation, axis=1)
    fit_amplitude = np.linalg.norm(fit, axis=1)
    second_amplitude = np.linalg.norm(second, axis=1)
    denominator = np.maximum(
        fit_amplitude + second_amplitude,
        np.finfo(np.float64).tiny,
    )
    first_harmonic_dominance_ratio = fit_amplitude / denominator
    disagreement = np.linalg.norm(fit - evaluation, axis=1)
    scale = np.maximum(
        np.maximum(fit_amplitude, amplitude),
        np.finfo(np.float64).tiny,
    )
    split_coherence = np.clip(1.0 - disagreement / scale, 0.0, 1.0)
    graph_coherence = _graph_directional_coherence(
        section_values=evaluation,
        edges=field_graph.canonical_edges,
    )
    edge_coherence = np.minimum(split_coherence, graph_coherence)
    counts = _support_counts(
        row_ids=estimator_inputs.row_ids,
        edges=field_graph.canonical_edges,
    )
    return CartesianFourierFieldEstimate(
        _factory_token=_FIELD_FACTORY_TOKEN,
        estimator_inputs=estimator_inputs,
        field_graph=field_graph,
        fit_section_values=fit,
        section_values=evaluation,
        second_harmonic_values=second,
        amplitude=amplitude,
        first_harmonic_dominance_ratio=(first_harmonic_dominance_ratio),
        edge_coherence=edge_coherence,
        split_disagreement=disagreement,
        support_count=counts,
        support=counts >= 2,
    )
