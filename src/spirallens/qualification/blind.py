"""Truth-blind inputs and sealed predictions for the Level-0 D2 kernel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from .common import (
    AttemptStatus,
    CorePredictionClass,
    FloatArray,
    Int64Array,
    QualificationContractError,
    array_fingerprint,
    fingerprint_mapping,
    float_matrix,
    float_vector,
    immutable_array,
    int64_matrix,
    int64_vector,
    level0_boundary,
    require_bool,
    require_enum,
    require_sha256,
    require_slug,
)

BLIND_CORE_INPUT_RECEIPT_VERSION = "spirallens.blind-core-input.v0.3"
SEALED_CORE_PREDICTION_RECEIPT_VERSION = "spirallens.sealed-core-prediction.v0.1"

_BLIND_INPUT_FACTORY_TOKEN = object()
_SEALED_PREDICTION_FACTORY_TOKEN = object()


def _ordered_unique_rows(value: object, *, label: str) -> Int64Array:
    rows = int64_vector(value, label=label)
    if len({int(item) for item in rows}) != rows.shape[0]:
        raise QualificationContractError(f"{label} must be unique")
    return rows


def _canonical_graph_edges(
    value: object,
    *,
    row_ids: Int64Array,
) -> Int64Array:
    edges = int64_matrix(value, label="graph_edges", width=2)
    allowed = {int(item) for item in row_ids}
    tuples = tuple((int(left), int(right)) for left, right in edges)
    if any(left not in allowed or right not in allowed for left, right in tuples):
        raise QualificationContractError(
            "graph_edges must reference BlindCoreInput row IDs"
        )
    if any(left >= right for left, right in tuples):
        raise QualificationContractError(
            "graph_edges must be canonical with left < right"
        )
    if tuples != tuple(sorted(set(tuples))):
        raise QualificationContractError(
            "graph_edges must be unique and lexicographically ordered"
        )
    return edges


def _degree_counts(
    row_ids: Int64Array,
    graph_edges: Int64Array,
) -> Int64Array:
    row_index = {int(row_id): index for index, row_id in enumerate(row_ids)}
    counts = np.zeros(row_ids.shape[0], dtype="<i8")
    for left, right in graph_edges:
        counts[row_index[int(left)]] += 1
        counts[row_index[int(right)]] += 1
    return immutable_array(counts, dtype=np.dtype("<i8"))  # type: ignore[return-value]


@dataclass(frozen=True, slots=True, init=False)
class BlindCoreInput:
    """Factory-only charge-blind core input with no section direction."""

    primary_unit_sha256: str
    estimator_input_fingerprint_sha256: str
    field_graph_fingerprint_sha256: str
    field_estimate_fingerprint_sha256: str
    input_id: str
    row_ids: Int64Array
    amplitude: FloatArray
    identifiability_score: FloatArray
    edge_coherence: FloatArray
    support_counts: Int64Array
    orientation_resolved: bool
    orientation_preserving: bool | None
    graph_edges: Int64Array

    receipt_version: ClassVar[str] = BLIND_CORE_INPUT_RECEIPT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        primary_unit_sha256: str,
        estimator_input_fingerprint_sha256: str,
        field_graph_fingerprint_sha256: str,
        field_estimate_fingerprint_sha256: str,
        input_id: str,
        row_ids: NDArray[np.generic],
        amplitude: NDArray[np.generic],
        identifiability_score: NDArray[np.generic],
        edge_coherence: NDArray[np.generic],
        support_counts: NDArray[np.generic],
        orientation_resolved: bool,
        orientation_preserving: bool | None,
        graph_edges: NDArray[np.generic],
    ) -> None:
        if _factory_token is not _BLIND_INPUT_FACTORY_TOKEN:
            raise QualificationContractError(
                "BlindCoreInput must be produced by build_blind_core_input"
            )
        object.__setattr__(
            self,
            "primary_unit_sha256",
            require_sha256(
                primary_unit_sha256,
                label="primary_unit_sha256",
            ),
        )
        for name, value in (
            (
                "estimator_input_fingerprint_sha256",
                estimator_input_fingerprint_sha256,
            ),
            (
                "field_graph_fingerprint_sha256",
                field_graph_fingerprint_sha256,
            ),
            (
                "field_estimate_fingerprint_sha256",
                field_estimate_fingerprint_sha256,
            ),
        ):
            object.__setattr__(
                self,
                name,
                require_sha256(value, label=name),
            )
        object.__setattr__(
            self,
            "input_id",
            require_slug(input_id, label="input_id"),
        )
        object.__setattr__(
            self,
            "row_ids",
            int64_vector(row_ids, label="row_ids"),
        )
        object.__setattr__(
            self,
            "amplitude",
            float_vector(amplitude, label="amplitude"),
        )
        object.__setattr__(
            self,
            "identifiability_score",
            float_vector(
                identifiability_score,
                label="identifiability_score",
            ),
        )
        object.__setattr__(
            self,
            "edge_coherence",
            float_vector(edge_coherence, label="edge_coherence"),
        )
        object.__setattr__(
            self,
            "support_counts",
            int64_vector(support_counts, label="support_counts"),
        )
        row_count = self.row_ids.shape[0]
        for label, vector in (
            ("amplitude", self.amplitude),
            ("identifiability_score", self.identifiability_score),
            ("edge_coherence", self.edge_coherence),
            ("support_counts", self.support_counts),
        ):
            if vector.shape != (row_count,):
                raise QualificationContractError(
                    f"{label} must align with the row domain"
                )
        object.__setattr__(
            self,
            "orientation_resolved",
            require_bool(
                orientation_resolved,
                label="orientation_resolved",
            ),
        )
        if orientation_preserving is None:
            preserving: bool | None = None
        else:
            preserving = require_bool(
                orientation_preserving,
                label="orientation_preserving",
            )
        object.__setattr__(
            self,
            "orientation_preserving",
            preserving,
        )
        object.__setattr__(
            self,
            "graph_edges",
            int64_matrix(
                graph_edges,
                label="graph_edges",
                width=2,
            ),
        )

    @property
    def row_identity_sha256(self) -> str:
        value = array_fingerprint(self.row_ids)["sha256"]
        assert isinstance(value, str)
        return value

    @property
    def graph_consumption_sha256(self) -> str:
        value = array_fingerprint(self.graph_edges)["sha256"]
        assert isinstance(value, str)
        return value

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "input_id": self.input_id,
            "primary_unit_sha256": self.primary_unit_sha256,
            "estimator_input_fingerprint_sha256": (
                self.estimator_input_fingerprint_sha256
            ),
            "field_graph_fingerprint_sha256": (self.field_graph_fingerprint_sha256),
            "field_estimate_fingerprint_sha256": (
                self.field_estimate_fingerprint_sha256
            ),
            "input_scope": (
                "truth-label-charge-anchor-loop-and-direction-free-core-input"
            ),
            "row_ids": array_fingerprint(self.row_ids),
            "row_identity_sha256": self.row_identity_sha256,
            "section_direction_retained": False,
            "same_object_field_estimate_bound_by_fingerprint": True,
            "amplitude": array_fingerprint(self.amplitude),
            "identifiability_score": array_fingerprint(self.identifiability_score),
            "edge_coherence": array_fingerprint(self.edge_coherence),
            "support_counts": array_fingerprint(self.support_counts),
            "orientation": {
                "resolved": self.orientation_resolved,
                "preserving": self.orientation_preserving,
            },
            "graph_consumption": {
                "canonical_edges": array_fingerprint(self.graph_edges),
                "sha256": self.graph_consumption_sha256,
                "support_counts_recomputed_from_edges": True,
            },
            "oracle_truth_present": False,
            "supplied_charge_present": False,
            "anchor_present": False,
            "loop_observable_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def build_blind_core_input(
    *,
    primary_unit_sha256: str,
    estimator_input_fingerprint_sha256: str,
    field_graph_fingerprint_sha256: str,
    field_estimate_fingerprint_sha256: str,
    row_ids: object,
    section_values: object,
    identifiability_score: object,
    edge_coherence: object,
    support_counts: object,
    orientation_resolved: bool,
    orientation_preserving: bool | None,
    graph_edges: object,
) -> BlindCoreInput:
    """Build a label-free input and discard section directions immediately."""

    primary_digest = require_sha256(
        primary_unit_sha256,
        label="primary_unit_sha256",
    )
    provenance = {
        name: require_sha256(value, label=name)
        for name, value in (
            (
                "estimator_input_fingerprint_sha256",
                estimator_input_fingerprint_sha256,
            ),
            (
                "field_graph_fingerprint_sha256",
                field_graph_fingerprint_sha256,
            ),
            (
                "field_estimate_fingerprint_sha256",
                field_estimate_fingerprint_sha256,
            ),
        )
    }
    rows = _ordered_unique_rows(row_ids, label="row_ids")
    section = float_matrix(
        section_values,
        label="section_values",
        width=2,
    )
    if section.shape[0] != rows.shape[0]:
        raise QualificationContractError(
            "section_values and row_ids must have the same row count"
        )
    identifiability = float_vector(
        identifiability_score,
        label="identifiability_score",
    )
    coherence = float_vector(edge_coherence, label="edge_coherence")
    if np.any(identifiability < 0.0):
        raise QualificationContractError("identifiability_score must be non-negative")
    if np.any((coherence < 0.0) | (coherence > 1.0)):
        raise QualificationContractError("edge_coherence must lie in [0, 1]")
    edges = _canonical_graph_edges(graph_edges, row_ids=rows)
    declared_support = int64_vector(
        support_counts,
        label="support_counts",
    )
    if np.any(declared_support < 0):
        raise QualificationContractError("support_counts must be non-negative")
    expected_support = _degree_counts(rows, edges)
    row_count = rows.shape[0]
    for label, vector in (
        ("identifiability_score", identifiability),
        ("edge_coherence", coherence),
        ("support_counts", declared_support),
    ):
        if vector.shape != (row_count,):
            raise QualificationContractError(f"{label} must align with the row domain")
    if not np.array_equal(declared_support, expected_support):
        raise QualificationContractError(
            "support_counts must equal degree recomputed from graph_edges"
        )
    resolved = require_bool(
        orientation_resolved,
        label="orientation_resolved",
    )
    if resolved:
        preserving: bool | None = require_bool(
            orientation_preserving,
            label="orientation_preserving",
        )
    else:
        if orientation_preserving is not None:
            raise QualificationContractError(
                "unresolved orientation requires orientation_preserving=None"
            )
        preserving = None

    amplitude = np.hypot(section[:, 0], section[:, 1])
    if not np.all(np.isfinite(amplitude)):
        raise QualificationContractError("section amplitude arithmetic is nonfinite")
    amplitude = immutable_array(
        np.asarray(amplitude, dtype="<f8"),
        dtype=np.dtype("<f8"),
    )
    input_content = {
        "primary_unit_sha256": primary_digest,
        **provenance,
        "row_ids": array_fingerprint(rows),
        "amplitude": array_fingerprint(amplitude),
        "identifiability_score": array_fingerprint(identifiability),
        "edge_coherence": array_fingerprint(coherence),
        "support_counts": array_fingerprint(declared_support),
        "orientation_resolved": resolved,
        "orientation_preserving": preserving,
        "graph_edges": array_fingerprint(edges),
    }
    input_id = f"qci_{fingerprint_mapping(input_content)[:32]}"
    return BlindCoreInput(
        _factory_token=_BLIND_INPUT_FACTORY_TOKEN,
        primary_unit_sha256=primary_digest,
        estimator_input_fingerprint_sha256=provenance[
            "estimator_input_fingerprint_sha256"
        ],
        field_graph_fingerprint_sha256=provenance["field_graph_fingerprint_sha256"],
        field_estimate_fingerprint_sha256=provenance[
            "field_estimate_fingerprint_sha256"
        ],
        input_id=input_id,
        row_ids=rows,
        amplitude=amplitude,
        identifiability_score=identifiability,
        edge_coherence=coherence,
        support_counts=declared_support,
        orientation_resolved=resolved,
        orientation_preserving=preserving,
        graph_edges=edges,
    )


@dataclass(frozen=True, slots=True, init=False)
class SealedCorePrediction:
    """Factory-only immutable output produced before oracle access."""

    blind_input_fingerprint_sha256: str
    primary_unit_sha256: str
    policy_fingerprint_sha256: str
    estimator_id: str
    observed_attempt_status: AttemptStatus
    prediction_class: CorePredictionClass
    reason_codes: tuple[str, ...]
    candidate_rows: Int64Array
    oracle_read: bool

    receipt_version: ClassVar[str] = SEALED_CORE_PREDICTION_RECEIPT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        blind_input_fingerprint_sha256: str,
        primary_unit_sha256: str,
        policy_fingerprint_sha256: str,
        estimator_id: str,
        observed_attempt_status: AttemptStatus,
        prediction_class: CorePredictionClass,
        reason_codes: tuple[str, ...],
        candidate_rows: NDArray[np.generic],
    ) -> None:
        if _factory_token is not _SEALED_PREDICTION_FACTORY_TOKEN:
            raise QualificationContractError(
                "SealedCorePrediction must be produced by the D2 estimator"
            )
        object.__setattr__(
            self,
            "blind_input_fingerprint_sha256",
            require_sha256(
                blind_input_fingerprint_sha256,
                label="blind_input_fingerprint_sha256",
            ),
        )
        object.__setattr__(
            self,
            "primary_unit_sha256",
            require_sha256(
                primary_unit_sha256,
                label="primary_unit_sha256",
            ),
        )
        object.__setattr__(
            self,
            "policy_fingerprint_sha256",
            require_sha256(
                policy_fingerprint_sha256,
                label="policy_fingerprint_sha256",
            ),
        )
        object.__setattr__(
            self,
            "estimator_id",
            require_slug(estimator_id, label="estimator_id"),
        )
        status = require_enum(
            AttemptStatus,
            observed_attempt_status,
            label="observed_attempt_status",
        )
        prediction = require_enum(
            CorePredictionClass,
            prediction_class,
            label="prediction_class",
        )
        rows = int64_vector(
            candidate_rows,
            label="candidate_rows",
            nonempty=False,
        )
        if len({int(item) for item in rows}) != rows.shape[0]:
            raise QualificationContractError("candidate_rows must be unique")
        if tuple(reason_codes) != tuple(sorted(set(reason_codes))):
            raise QualificationContractError(
                "reason_codes must be unique and canonical"
            )
        if status is AttemptStatus.EVALUABLE:
            if (
                prediction
                not in {
                    CorePredictionClass.LOCALIZED_CORE,
                    CorePredictionClass.NO_CORE,
                }
                or reason_codes
            ):
                raise QualificationContractError(
                    "evaluable predictions require a decision and no reasons"
                )
            if (
                prediction is CorePredictionClass.LOCALIZED_CORE and rows.shape[0] == 0
            ) or (prediction is CorePredictionClass.NO_CORE and rows.shape[0] != 0):
                raise QualificationContractError(
                    "candidate rows disagree with the evaluable prediction"
                )
        elif status is AttemptStatus.INSUFFICIENT:
            if (
                prediction is not CorePredictionClass.ABSTAIN
                or not reason_codes
                or rows.shape[0] != 0
            ):
                raise QualificationContractError(
                    "insufficient predictions must abstain with reasons"
                )
        elif (
            prediction is not CorePredictionClass.NONE
            or reason_codes
            or rows.shape[0] != 0
        ):
            raise QualificationContractError(
                "not-run predictions cannot contain an output"
            )
        object.__setattr__(self, "observed_attempt_status", status)
        object.__setattr__(self, "prediction_class", prediction)
        object.__setattr__(self, "reason_codes", tuple(reason_codes))
        object.__setattr__(self, "candidate_rows", rows)
        object.__setattr__(self, "oracle_read", False)

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "blind_input_fingerprint_sha256": (self.blind_input_fingerprint_sha256),
            "primary_unit_sha256": self.primary_unit_sha256,
            "policy_fingerprint_sha256": self.policy_fingerprint_sha256,
            "estimator_id": self.estimator_id,
            "observed_attempt_status": self.observed_attempt_status.value,
            "prediction_class": self.prediction_class.value,
            "reason_codes": list(self.reason_codes),
            "candidate_rows": array_fingerprint(self.candidate_rows),
            "oracle_read": self.oracle_read,
            "sealed_before_oracle_score": True,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def _seal_core_prediction(
    *,
    blind_input: BlindCoreInput,
    policy_fingerprint_sha256: str,
    estimator_id: str,
    observed_attempt_status: AttemptStatus,
    prediction_class: CorePredictionClass,
    reason_codes: tuple[str, ...],
    candidate_rows: NDArray[np.generic],
) -> SealedCorePrediction:
    return SealedCorePrediction(
        _factory_token=_SEALED_PREDICTION_FACTORY_TOKEN,
        blind_input_fingerprint_sha256=blind_input.fingerprint_sha256,
        primary_unit_sha256=blind_input.primary_unit_sha256,
        policy_fingerprint_sha256=policy_fingerprint_sha256,
        estimator_id=estimator_id,
        observed_attempt_status=observed_attempt_status,
        prediction_class=prediction_class,
        reason_codes=reason_codes,
        candidate_rows=candidate_rows,
    )
