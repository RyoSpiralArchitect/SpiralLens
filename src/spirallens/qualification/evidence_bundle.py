"""Full typed D2/D4/D5 evidence companions.

Normalized qualification summaries are convenient review records, but they
cannot establish that a sealed prediction was joined to its oracle and scored.
This module carries the complete runtime receipts needed to recheck those
joins.  It intentionally stores no subject data and grants no claim above
Level 0.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256

from .common import (
    AttemptStatus,
    CoreDisposition,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    LoopPredictionClass,
    ObligationMode,
    QualificationContractError,
    QualificationState,
    level0_boundary,
    require_finite_real,
    require_plain_int,
    require_sha256,
    require_slug,
)
from .contracts import (
    CoreCellSummary,
    CrossedCellSummary,
    CrossedNonvacuitySummary,
    StaticEvidenceReceipt,
)
from .protocol import QualificationProtocol

EVIDENCE_BUNDLE_SCHEMA_VERSION = "spirallens.qualification-evidence-bundle.v0.4"
CORE_CELL_EVIDENCE_SCHEMA_VERSION = "spirallens.qualification-core-cell-evidence.v0.1"
LOOP_CELL_EVIDENCE_SCHEMA_VERSION = "spirallens.qualification-loop-cell-evidence.v0.1"
NONVACUITY_EVIDENCE_SCHEMA_VERSION = "spirallens.qualification-nonvacuity-evidence.v0.2"
D1_CASE_EXECUTION_SCHEMA_VERSION = "spirallens.qualification-d1-case-execution.v0.2"
D1_FAMILY_EXECUTION_SCHEMA_VERSION = "spirallens.qualification-d1-family-execution.v0.2"
D1_NUMERIC_METRIC_SCHEMA_VERSION = "spirallens.qualification-d1-numeric-metric.v0.1"
D3_PIPELINE_EXECUTION_SCHEMA_VERSION = (
    "spirallens.qualification-d3-pipeline-execution.v0.3"
)
D2_CONFOUNDER_CELL_SCHEMA_VERSION = "spirallens.qualification-d2-confounder-cell.v0.2"
D2_CONFOUNDER_MATRIX_SCHEMA_VERSION = (
    "spirallens.qualification-d2-confounder-matrix.v0.2"
)

_BOUNDARY = level0_boundary()
_BOUNDARY_KEYS = frozenset(_BOUNDARY)
_ARRAY_FINGERPRINT_KEYS = frozenset({"dtype", "shape", "sha256"})


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise QualificationContractError(f"{label} must be a string-keyed mapping")
    return dict(value)


def _exact_keys(
    document: Mapping[str, object],
    expected: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    if set(document) != set(expected):
        raise QualificationContractError(
            f"{label} fields differ from the exact runtime receipt schema"
        )


def _constant(value: object, expected: object, *, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise QualificationContractError(f"{label} must equal {expected!r}")


def _canonical_reasons(value: object, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise QualificationContractError(f"{label} must be a JSON array")
    result = tuple(
        require_slug(item, label=f"{label}[{index}]")
        for index, item in enumerate(value)
    )
    if result != tuple(sorted(set(result))):
        raise QualificationContractError(
            f"{label} must be unique and in canonical order"
        )
    return result


def _array_fingerprint(value: object, *, label: str) -> dict[str, object]:
    document = _mapping(value, label=label)
    _exact_keys(document, _ARRAY_FINGERPRINT_KEYS, label=label)
    dtype = document["dtype"]
    shape = document["shape"]
    if not isinstance(dtype, str) or not dtype:
        raise QualificationContractError(f"{label}.dtype must be a string")
    if not isinstance(shape, list) or any(
        type(item) is not int or item < 0 for item in shape
    ):
        raise QualificationContractError(
            f"{label}.shape must contain nonnegative plain integers"
        )
    require_sha256(document["sha256"], label=f"{label}.sha256")
    return document


def _fingerprint_shape(
    value: object,
    *,
    label: str,
    ndim: int,
    width: int | None = None,
) -> dict[str, object]:
    document = _array_fingerprint(value, label=label)
    shape = document["shape"]
    assert isinstance(shape, list)
    if len(shape) != ndim or (width is not None and shape[-1] != width):
        raise QualificationContractError(
            f"{label}.shape differs from the typed runtime array layout"
        )
    return document


def _optional_finite_real(
    value: object,
    *,
    label: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    if value is None:
        return None
    return require_finite_real(
        value,
        label=label,
        minimum=minimum,
        maximum=maximum,
    )


def _exact_bool(value: object, *, expected: bool, label: str) -> None:
    _constant(value, expected, label=label)


def _int64_vector_fingerprint(values: tuple[int, ...]) -> dict[str, object]:
    for index, value in enumerate(values):
        if type(value) is not int or value < -(2**63) or value > 2**63 - 1:
            raise QualificationContractError(
                f"int64 vector row {index} is outside the signed 64-bit range"
            )
    descriptor = canonical_json_bytes({"dtype": "<i8", "shape": [len(values)]})
    payload = b"".join(struct.pack("<q", item) for item in values)
    return {
        "dtype": "<i8",
        "shape": [len(values)],
        "sha256": hashlib.sha256(descriptor + b"\x00" + payload).hexdigest(),
    }


def _runtime_receipt(
    value: object,
    *,
    label: str,
    receipt_version: str,
    runtime_keys: frozenset[str],
) -> dict[str, object]:
    document = _mapping(value, label=label)
    _exact_keys(
        document,
        frozenset({"receipt_version"}) | _BOUNDARY_KEYS | runtime_keys,
        label=label,
    )
    _constant(document["receipt_version"], receipt_version, label=f"{label}.version")
    for name, expected in _BOUNDARY.items():
        _constant(document[name], expected, label=f"{label}.{name}")
    return document


_CORE_BLIND_KEYS = frozenset(
    {
        "input_id",
        "primary_unit_sha256",
        "estimator_input_fingerprint_sha256",
        "field_graph_fingerprint_sha256",
        "field_estimate_fingerprint_sha256",
        "input_scope",
        "row_ids",
        "row_identity_sha256",
        "section_direction_retained",
        "same_object_field_estimate_bound_by_fingerprint",
        "amplitude",
        "identifiability_score",
        "edge_coherence",
        "support_counts",
        "orientation",
        "graph_consumption",
        "oracle_truth_present",
        "supplied_charge_present",
        "anchor_present",
        "loop_observable_present",
    }
)
_CORE_PREDICTION_KEYS = frozenset(
    {
        "blind_input_fingerprint_sha256",
        "primary_unit_sha256",
        "policy_fingerprint_sha256",
        "estimator_id",
        "observed_attempt_status",
        "prediction_class",
        "reason_codes",
        "candidate_rows",
        "oracle_read",
        "sealed_before_oracle_score",
    }
)
_CORE_ORACLE_KEYS = frozenset(
    {
        "blind_input_fingerprint_sha256",
        "primary_unit_sha256",
        "policy_fingerprint_sha256",
        "truth_id",
        "expected_disposition",
        "anchor_rows",
        "expected_prerequisite_reasons",
        "obligation_mode",
        "evaluation_unit",
        "estimator_input_allowed",
        "localization_gate_eligible",
    }
)
_CORE_EVALUATION_KEYS = frozenset(
    {
        "prediction_fingerprint_sha256",
        "truth_fingerprint_sha256",
        "blind_input_fingerprint_sha256",
        "policy_fingerprint_sha256",
        "observed_attempt_status",
        "expected_disposition",
        "gate_verdict",
        "reason_codes",
        "exact_anchor_match",
        "obligation_mode",
        "evaluation_unit",
    }
)
_LOOP_BLIND_KEYS = frozenset(
    {
        "primary_unit_sha256",
        "estimator_input_fingerprint_sha256",
        "field_graph_fingerprint_sha256",
        "field_estimate_fingerprint_sha256",
        "cycle_graph_fingerprint_sha256",
        "cycle_binding_fingerprint_sha256",
        "representative_content_sha256",
        "input_id",
        "input_scope",
        "ordered_loop_rows",
        "section_values",
        "boundary_amplitude",
        "boundary_identifiability_score",
        "boundary_coherence",
        "same_object_amplitude_and_direction",
        "expected_outcome_present",
        "integer_output_present",
    }
)
_LOOP_PREDICTION_KEYS = frozenset(
    {
        "blind_input_fingerprint_sha256",
        "primary_unit_sha256",
        "policy_fingerprint_sha256",
        "estimator_id",
        "observed_attempt_status",
        "prediction_class",
        "reason_codes",
        "signed_total_cycles",
        "max_abs_edge_increment_radians",
        "nearest_integer_residual_cycles",
        "comparison_tolerance_cycles",
        "oracle_read",
        "sealed_before_oracle_score",
        "sampled_continuous_observable_only",
        "integer_output_present",
    }
)
_LOOP_ORACLE_KEYS = frozenset(
    {
        "blind_input_fingerprint_sha256",
        "primary_unit_sha256",
        "policy_fingerprint_sha256",
        "truth_id",
        "expected_disposition",
        "expected_sampled_cycles",
        "expected_prerequisite_reasons",
        "obligation_mode",
        "evaluation_unit",
        "estimator_input_allowed",
        "oracle_integer_is_synthetic_expected_sampled_outcome",
        "observed_integer_output_present",
    }
)
_LOOP_EVALUATION_KEYS = frozenset(
    {
        "prediction_fingerprint_sha256",
        "truth_fingerprint_sha256",
        "blind_input_fingerprint_sha256",
        "policy_fingerprint_sha256",
        "observed_attempt_status",
        "expected_disposition",
        "gate_verdict",
        "reason_codes",
        "sampled_total_match",
        "signed_error_cycles",
        "obligation_mode",
        "evaluation_unit",
        "sampled_continuous_observable_only",
        "integer_output_present",
    }
)


@dataclass(frozen=True, slots=True)
class CoreCellEvaluationReceipt:
    """Full blind/prediction/oracle/evaluation chain for one D2 cell."""

    core_cell_id: str
    blind_input_receipt: dict[str, object]
    sealed_prediction_receipt: dict[str, object]
    oracle_truth_receipt: dict[str, object]
    case_evaluation_receipt: dict[str, object]
    candidate_rows: tuple[int, ...]
    anchor_rows: tuple[int, ...]
    normalized_summary_sha256: str
    schema_version: str = CORE_CELL_EVIDENCE_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "core_cell_id",
            "blind_input_receipt",
            "sealed_prediction_receipt",
            "oracle_truth_receipt",
            "case_evaluation_receipt",
            "candidate_rows",
            "anchor_rows",
            "normalized_summary_sha256",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            CORE_CELL_EVIDENCE_SCHEMA_VERSION,
            label="core cell evidence schema_version",
        )
        require_slug(self.core_cell_id, label="core cell evidence core_cell_id")
        require_sha256(
            self.normalized_summary_sha256,
            label="core cell evidence normalized_summary_sha256",
        )
        self._documents()

    def _documents(
        self,
    ) -> tuple[
        dict[str, object],
        dict[str, object],
        dict[str, object],
        dict[str, object],
    ]:
        blind = _runtime_receipt(
            self.blind_input_receipt,
            label="core blind input receipt",
            receipt_version="spirallens.blind-core-input.v0.3",
            runtime_keys=_CORE_BLIND_KEYS,
        )
        prediction = _runtime_receipt(
            self.sealed_prediction_receipt,
            label="core sealed prediction receipt",
            receipt_version="spirallens.sealed-core-prediction.v0.1",
            runtime_keys=_CORE_PREDICTION_KEYS,
        )
        oracle = _runtime_receipt(
            self.oracle_truth_receipt,
            label="core oracle truth receipt",
            receipt_version="spirallens.core-oracle-truth.v0.1",
            runtime_keys=_CORE_ORACLE_KEYS,
        )
        evaluation = _runtime_receipt(
            self.case_evaluation_receipt,
            label="core case evaluation receipt",
            receipt_version="spirallens.core-case-evaluation.v0.1",
            runtime_keys=_CORE_EVALUATION_KEYS,
        )
        for name in (
            "primary_unit_sha256",
            "estimator_input_fingerprint_sha256",
            "field_graph_fingerprint_sha256",
            "field_estimate_fingerprint_sha256",
            "row_identity_sha256",
        ):
            require_sha256(blind[name], label=f"core blind input {name}")
        require_slug(blind["input_id"], label="core blind input input_id")
        _constant(
            blind["input_scope"],
            "truth-label-charge-anchor-loop-and-direction-free-core-input",
            label="core blind input scope",
        )
        for name, expected in (
            ("section_direction_retained", False),
            ("same_object_field_estimate_bound_by_fingerprint", True),
            ("oracle_truth_present", False),
            ("supplied_charge_present", False),
            ("anchor_present", False),
            ("loop_observable_present", False),
        ):
            _exact_bool(
                blind[name],
                expected=expected,
                label=f"core blind input {name}",
            )
        row_fp = _fingerprint_shape(
            blind["row_ids"],
            label="core blind row_ids",
            ndim=1,
        )
        amplitude_fp = _fingerprint_shape(
            blind["amplitude"],
            label="core blind amplitude",
            ndim=1,
        )
        identifiability_fp = _fingerprint_shape(
            blind["identifiability_score"],
            label="core blind identifiability_score",
            ndim=1,
        )
        coherence_fp = _fingerprint_shape(
            blind["edge_coherence"],
            label="core blind edge_coherence",
            ndim=1,
        )
        support_fp = _fingerprint_shape(
            blind["support_counts"],
            label="core blind support_counts",
            ndim=1,
        )
        row_count = row_fp["shape"][0]  # type: ignore[index]
        if any(
            document["shape"] != [row_count]
            for document in (
                amplitude_fp,
                identifiability_fp,
                coherence_fp,
                support_fp,
            )
        ):
            raise QualificationContractError(
                "core blind input arrays do not share the row domain"
            )
        if blind["row_identity_sha256"] != row_fp["sha256"]:
            raise QualificationContractError(
                "core blind row identity differs from row_ids"
            )
        orientation = _mapping(
            blind["orientation"],
            label="core blind orientation",
        )
        _exact_keys(
            orientation,
            {"resolved", "preserving"},
            label="core blind orientation",
        )
        if type(orientation["resolved"]) is not bool:
            raise QualificationContractError(
                "core blind orientation.resolved must be boolean"
            )
        if orientation["resolved"]:
            if type(orientation["preserving"]) is not bool:
                raise QualificationContractError(
                    "resolved core orientation requires a preserving boolean"
                )
        elif orientation["preserving"] is not None:
            raise QualificationContractError(
                "unresolved core orientation cannot claim preservation"
            )
        graph_consumption = _mapping(
            blind["graph_consumption"],
            label="core blind graph consumption",
        )
        _exact_keys(
            graph_consumption,
            {
                "canonical_edges",
                "sha256",
                "support_counts_recomputed_from_edges",
            },
            label="core blind graph consumption",
        )
        graph_edges_fp = _fingerprint_shape(
            graph_consumption["canonical_edges"],
            label="core blind graph edges",
            ndim=2,
            width=2,
        )
        _constant(
            graph_consumption["sha256"],
            graph_edges_fp["sha256"],
            label="core blind graph consumption sha256",
        )
        _exact_bool(
            graph_consumption["support_counts_recomputed_from_edges"],
            expected=True,
            label="core blind graph support recomputation",
        )
        expected_input_id = (
            "qci_"
            + canonical_json_sha256(
                {
                    "primary_unit_sha256": blind["primary_unit_sha256"],
                    "estimator_input_fingerprint_sha256": blind[
                        "estimator_input_fingerprint_sha256"
                    ],
                    "field_graph_fingerprint_sha256": blind[
                        "field_graph_fingerprint_sha256"
                    ],
                    "field_estimate_fingerprint_sha256": blind[
                        "field_estimate_fingerprint_sha256"
                    ],
                    "row_ids": row_fp,
                    "amplitude": amplitude_fp,
                    "identifiability_score": identifiability_fp,
                    "edge_coherence": coherence_fp,
                    "support_counts": support_fp,
                    "orientation_resolved": orientation["resolved"],
                    "orientation_preserving": orientation["preserving"],
                    "graph_edges": graph_edges_fp,
                }
            )[:32]
        )
        _constant(
            blind["input_id"],
            expected_input_id,
            label="core blind input content pseudonym",
        )
        candidate_fp = _array_fingerprint(
            prediction["candidate_rows"], label="core candidate_rows fingerprint"
        )
        anchor_fp = _array_fingerprint(
            oracle["anchor_rows"], label="core anchor_rows fingerprint"
        )
        if candidate_fp != _int64_vector_fingerprint(self.candidate_rows):
            raise QualificationContractError(
                "core candidate rows differ from the sealed prediction receipt"
            )
        if anchor_fp != _int64_vector_fingerprint(self.anchor_rows):
            raise QualificationContractError(
                "core anchor rows differ from the oracle receipt"
            )
        blind_sha = canonical_json_sha256(blind)
        prediction_sha = canonical_json_sha256(prediction)
        oracle_sha = canonical_json_sha256(oracle)
        for label, observed, expected in (
            (
                "prediction blind input",
                prediction["blind_input_fingerprint_sha256"],
                blind_sha,
            ),
            ("oracle blind input", oracle["blind_input_fingerprint_sha256"], blind_sha),
            (
                "evaluation blind input",
                evaluation["blind_input_fingerprint_sha256"],
                blind_sha,
            ),
            (
                "evaluation prediction",
                evaluation["prediction_fingerprint_sha256"],
                prediction_sha,
            ),
            ("evaluation truth", evaluation["truth_fingerprint_sha256"], oracle_sha),
            (
                "prediction/oracle primary unit",
                prediction["primary_unit_sha256"],
                oracle["primary_unit_sha256"],
            ),
            (
                "blind/prediction primary unit",
                prediction["primary_unit_sha256"],
                blind["primary_unit_sha256"],
            ),
            (
                "prediction/oracle policy",
                prediction["policy_fingerprint_sha256"],
                oracle["policy_fingerprint_sha256"],
            ),
            (
                "evaluation policy",
                evaluation["policy_fingerprint_sha256"],
                prediction["policy_fingerprint_sha256"],
            ),
        ):
            if observed != expected:
                raise QualificationContractError(f"core {label} digest join mismatch")
        try:
            status = AttemptStatus(prediction["observed_attempt_status"])
            prediction_class = CorePredictionClass(prediction["prediction_class"])
            disposition = CoreDisposition(oracle["expected_disposition"])
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "core runtime receipt carries an unsupported enum value"
            ) from error
        prediction_reasons = _canonical_reasons(
            prediction["reason_codes"], label="core prediction reason_codes"
        )
        oracle_reasons = _canonical_reasons(
            oracle["expected_prerequisite_reasons"],
            label="core oracle prerequisite reasons",
        )
        candidate_rows = self.candidate_rows
        anchor_rows = self.anchor_rows
        if len(set(candidate_rows)) != len(candidate_rows):
            raise QualificationContractError("core candidate rows must be unique")
        if len(set(anchor_rows)) != len(anchor_rows):
            raise QualificationContractError("core anchor rows must be unique")
        require_slug(
            prediction["estimator_id"],
            label="core prediction estimator_id",
        )
        require_sha256(
            prediction["policy_fingerprint_sha256"],
            label="core prediction policy_fingerprint_sha256",
        )
        _exact_bool(
            prediction["oracle_read"],
            expected=False,
            label="core prediction oracle_read",
        )
        _exact_bool(
            prediction["sealed_before_oracle_score"],
            expected=True,
            label="core prediction sealed_before_oracle_score",
        )
        if status is AttemptStatus.EVALUABLE:
            if (
                prediction_class
                not in {
                    CorePredictionClass.LOCALIZED_CORE,
                    CorePredictionClass.NO_CORE,
                }
                or prediction_reasons
                or (
                    prediction_class is CorePredictionClass.LOCALIZED_CORE
                    and not candidate_rows
                )
                or (prediction_class is CorePredictionClass.NO_CORE and candidate_rows)
            ):
                raise QualificationContractError(
                    "core evaluable prediction receipt violates its typed state"
                )
        elif status is AttemptStatus.INSUFFICIENT:
            if (
                prediction_class is not CorePredictionClass.ABSTAIN
                or not prediction_reasons
                or candidate_rows
            ):
                raise QualificationContractError(
                    "core insufficient prediction receipt violates its typed state"
                )
        elif (
            prediction_class is not CorePredictionClass.NONE
            or prediction_reasons
            or candidate_rows
        ):
            raise QualificationContractError(
                "core not-run prediction receipt contains an output"
            )
        require_slug(oracle["truth_id"], label="core oracle truth_id")
        try:
            ObligationMode(oracle["obligation_mode"])
            EvaluationUnit(oracle["evaluation_unit"])
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "core oracle carries an unsupported obligation/evaluation mode"
            ) from error
        _exact_bool(
            oracle["estimator_input_allowed"],
            expected=False,
            label="core oracle estimator_input_allowed",
        )
        _exact_bool(
            oracle["localization_gate_eligible"],
            expected=False,
            label="core oracle localization_gate_eligible",
        )
        if disposition is CoreDisposition.LOCALIZED_CORE:
            if not anchor_rows or oracle_reasons:
                raise QualificationContractError(
                    "localized-core oracle requires anchors and no reasons"
                )
        elif disposition is CoreDisposition.NO_CORE:
            if anchor_rows or oracle_reasons:
                raise QualificationContractError(
                    "no-core oracle cannot carry anchors or reasons"
                )
        elif anchor_rows or not oracle_reasons:
            raise QualificationContractError(
                "prerequisite core oracle requires reasons and no anchors"
            )
        expected_truth_id = (
            "qct_"
            + canonical_json_sha256(
                {
                    "blind_input_fingerprint_sha256": blind_sha,
                    "policy_fingerprint_sha256": oracle["policy_fingerprint_sha256"],
                    "expected_disposition": disposition.value,
                    "anchor_rows": anchor_fp,
                    "expected_prerequisite_reasons": list(oracle_reasons),
                    "obligation_mode": oracle["obligation_mode"],
                    "evaluation_unit": oracle["evaluation_unit"],
                }
            )[:32]
        )
        _constant(
            oracle["truth_id"],
            expected_truth_id,
            label="core oracle truth content pseudonym",
        )
        exact_match: bool | None = None
        reasons: set[str] = set()
        if status is AttemptStatus.NOT_RUN:
            verdict = QualificationState.NOT_RUN
        elif disposition is CoreDisposition.PREREQUISITE_FAILURE:
            if (
                status is AttemptStatus.INSUFFICIENT
                and prediction_reasons == oracle_reasons
            ):
                verdict = QualificationState.PASS
            else:
                verdict = QualificationState.FAIL
                reasons.add(
                    "prerequisite_reason_mismatch"
                    if status is AttemptStatus.INSUFFICIENT
                    else "forced_output_on_prerequisite_failure"
                )
        elif status is AttemptStatus.INSUFFICIENT:
            verdict = QualificationState.INSUFFICIENT
            reasons.update(prediction_reasons)
        elif disposition is CoreDisposition.LOCALIZED_CORE:
            exact_match = candidate_rows == anchor_rows
            if prediction_class is CorePredictionClass.LOCALIZED_CORE and exact_match:
                verdict = QualificationState.PASS
            else:
                verdict = QualificationState.FAIL
                reasons.add("positive_anchor_not_recovered")
        else:
            exact_match = not candidate_rows
            if prediction_class is CorePredictionClass.NO_CORE:
                verdict = QualificationState.PASS
            else:
                verdict = QualificationState.FAIL
                reasons.add("false_core_localization")
        expected_evaluation = {
            "observed_attempt_status": status.value,
            "expected_disposition": disposition.value,
            "gate_verdict": verdict.value,
            "reason_codes": sorted(reasons),
            "exact_anchor_match": exact_match,
            "obligation_mode": oracle["obligation_mode"],
            "evaluation_unit": oracle["evaluation_unit"],
        }
        if any(
            evaluation[name] != expected
            for name, expected in expected_evaluation.items()
        ):
            raise QualificationContractError(
                "core case evaluation differs from mechanically recomputed scoring"
            )
        return blind, prediction, oracle, evaluation

    def validate_summary(self, summary: CoreCellSummary) -> None:
        if not isinstance(summary, CoreCellSummary):
            raise TypeError("summary must be a CoreCellSummary")
        blind, prediction, oracle, evaluation = self._documents()
        candidate_set = set(self.candidate_rows)
        anchor_set = set(self.anchor_rows)
        symmetric_difference = tuple(sorted(candidate_set ^ anchor_set))
        expected = {
            "core_cell_id": self.core_cell_id,
            "field_graph_fingerprint_sha256": blind["field_graph_fingerprint_sha256"],
            "field_estimate_fingerprint_sha256": blind[
                "field_estimate_fingerprint_sha256"
            ],
            "blind_input_fingerprint_sha256": canonical_json_sha256(blind),
            "prediction_fingerprint_sha256": canonical_json_sha256(prediction),
            "oracle_fingerprint_sha256": canonical_json_sha256(oracle),
            "candidate_fingerprint_sha256": canonical_json_sha256(
                prediction["candidate_rows"]
            ),
            "oracle_anchor_fingerprint_sha256": canonical_json_sha256(
                oracle["anchor_rows"]
            ),
            "candidate_anchor_symmetric_difference_rows": symmetric_difference,
            "attempt_status": prediction["observed_attempt_status"],
            "prediction_class": prediction["prediction_class"],
            "expected_disposition": oracle["expected_disposition"],
            "state": evaluation["gate_verdict"],
            "reason_codes": tuple(evaluation["reason_codes"]),  # type: ignore[arg-type]
        }
        observed = {
            "core_cell_id": summary.core_cell_id,
            "field_graph_fingerprint_sha256": (summary.field_graph_fingerprint_sha256),
            "field_estimate_fingerprint_sha256": (
                summary.field_estimate_fingerprint_sha256
            ),
            "blind_input_fingerprint_sha256": (summary.blind_input_fingerprint_sha256),
            "prediction_fingerprint_sha256": (summary.prediction_fingerprint_sha256),
            "oracle_fingerprint_sha256": summary.oracle_fingerprint_sha256,
            "candidate_fingerprint_sha256": (summary.candidate_fingerprint_sha256),
            "oracle_anchor_fingerprint_sha256": (
                summary.oracle_anchor_fingerprint_sha256
            ),
            "candidate_anchor_symmetric_difference_rows": (
                summary.candidate_anchor_symmetric_difference_rows
            ),
            "attempt_status": summary.attempt_status.value,
            "prediction_class": summary.prediction_class.value,
            "expected_disposition": summary.expected_disposition.value,
            "state": summary.state.value,
            "reason_codes": summary.reason_codes,
        }
        if observed != expected:
            raise QualificationContractError(
                "core normalized summary differs from its full evaluation receipt"
            )
        if self.normalized_summary_sha256 != canonical_json_sha256(summary.to_dict()):
            raise QualificationContractError(
                "core normalized summary digest differs from its receipt"
            )

    @classmethod
    def from_runtime(
        cls,
        *,
        core_cell_id: str,
        blind_input: object,
        sealed_prediction: object,
        oracle_truth: object,
        case_evaluation: object,
        summary: CoreCellSummary,
    ) -> CoreCellEvaluationReceipt:
        from .blind import BlindCoreInput, SealedCorePrediction
        from .prerequisites import CoreCaseEvaluation, CoreOracleTruth

        if not isinstance(blind_input, BlindCoreInput):
            raise TypeError("blind_input must be a BlindCoreInput")
        if not isinstance(sealed_prediction, SealedCorePrediction):
            raise TypeError("sealed_prediction must be a SealedCorePrediction")
        if not isinstance(oracle_truth, CoreOracleTruth):
            raise TypeError("oracle_truth must be a CoreOracleTruth")
        if not isinstance(case_evaluation, CoreCaseEvaluation):
            raise TypeError("case_evaluation must be a CoreCaseEvaluation")
        receipt = cls(
            core_cell_id=core_cell_id,
            blind_input_receipt=blind_input.to_dict(),
            sealed_prediction_receipt=sealed_prediction.to_dict(),
            oracle_truth_receipt=oracle_truth.to_dict(),
            case_evaluation_receipt=case_evaluation.to_dict(),
            candidate_rows=tuple(
                int(item) for item in sealed_prediction.candidate_rows
            ),
            anchor_rows=tuple(int(item) for item in oracle_truth.anchor_rows),
            normalized_summary_sha256=canonical_json_sha256(summary.to_dict()),
        )
        receipt.validate_summary(summary)
        return receipt

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "core_cell_id": self.core_cell_id,
            "blind_input_receipt": self.blind_input_receipt,
            "sealed_prediction_receipt": self.sealed_prediction_receipt,
            "oracle_truth_receipt": self.oracle_truth_receipt,
            "case_evaluation_receipt": self.case_evaluation_receipt,
            "candidate_rows": list(self.candidate_rows),
            "anchor_rows": list(self.anchor_rows),
            "normalized_summary_sha256": self.normalized_summary_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> CoreCellEvaluationReceipt:
        item = _mapping(value, label="core cell evaluation receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="core cell evaluation receipt")
        for name in ("candidate_rows", "anchor_rows"):
            if not isinstance(item[name], list):
                raise QualificationContractError(f"{name} must be a JSON array")
        return cls(
            schema_version=item["schema_version"],  # type: ignore[arg-type]
            core_cell_id=require_slug(item["core_cell_id"], label="core_cell_id"),
            blind_input_receipt=_mapping(
                item["blind_input_receipt"], label="blind_input_receipt"
            ),
            sealed_prediction_receipt=_mapping(
                item["sealed_prediction_receipt"], label="sealed_prediction_receipt"
            ),
            oracle_truth_receipt=_mapping(
                item["oracle_truth_receipt"], label="oracle_truth_receipt"
            ),
            case_evaluation_receipt=_mapping(
                item["case_evaluation_receipt"], label="case_evaluation_receipt"
            ),
            candidate_rows=tuple(
                require_plain_int(row, label="candidate row")
                for row in item["candidate_rows"]  # type: ignore[union-attr]
            ),
            anchor_rows=tuple(
                require_plain_int(row, label="anchor row")
                for row in item["anchor_rows"]  # type: ignore[union-attr]
            ),
            normalized_summary_sha256=require_sha256(
                item["normalized_summary_sha256"],
                label="normalized_summary_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class LoopCellEvaluationReceipt:
    """Full blind/prediction/oracle/evaluation chain for one D4/D5 cell."""

    cell_id: str
    blind_input_receipt: dict[str, object]
    sealed_prediction_receipt: dict[str, object]
    oracle_truth_receipt: dict[str, object]
    case_evaluation_receipt: dict[str, object]
    normalized_summary_sha256: str
    schema_version: str = LOOP_CELL_EVIDENCE_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "cell_id",
            "blind_input_receipt",
            "sealed_prediction_receipt",
            "oracle_truth_receipt",
            "case_evaluation_receipt",
            "normalized_summary_sha256",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            LOOP_CELL_EVIDENCE_SCHEMA_VERSION,
            label="loop cell evidence schema_version",
        )
        require_slug(self.cell_id, label="loop cell evidence cell_id")
        require_sha256(
            self.normalized_summary_sha256,
            label="loop cell evidence normalized_summary_sha256",
        )
        self._documents()

    def _documents(
        self,
    ) -> tuple[
        dict[str, object],
        dict[str, object],
        dict[str, object],
        dict[str, object],
    ]:
        blind = _runtime_receipt(
            self.blind_input_receipt,
            label="loop blind input receipt",
            receipt_version="spirallens.blind-loop-input.v0.3",
            runtime_keys=_LOOP_BLIND_KEYS,
        )
        prediction = _runtime_receipt(
            self.sealed_prediction_receipt,
            label="loop sealed prediction receipt",
            receipt_version="spirallens.sealed-loop-prediction.v0.1",
            runtime_keys=_LOOP_PREDICTION_KEYS,
        )
        oracle = _runtime_receipt(
            self.oracle_truth_receipt,
            label="loop oracle truth receipt",
            receipt_version="spirallens.loop-oracle-truth.v0.1",
            runtime_keys=_LOOP_ORACLE_KEYS,
        )
        evaluation = _runtime_receipt(
            self.case_evaluation_receipt,
            label="loop case evaluation receipt",
            receipt_version="spirallens.loop-case-evaluation.v0.1",
            runtime_keys=_LOOP_EVALUATION_KEYS,
        )
        blind_hash_fields = (
            "primary_unit_sha256",
            "estimator_input_fingerprint_sha256",
            "field_graph_fingerprint_sha256",
            "field_estimate_fingerprint_sha256",
            "cycle_graph_fingerprint_sha256",
            "cycle_binding_fingerprint_sha256",
            "representative_content_sha256",
        )
        for name in blind_hash_fields:
            require_sha256(blind[name], label=f"loop blind input {name}")
        require_slug(blind["input_id"], label="loop blind input input_id")
        _constant(
            blind["input_scope"],
            "one-ordered-representative-loop-and-boundary-observables",
            label="loop blind input scope",
        )
        for name, expected in (
            ("same_object_amplitude_and_direction", True),
            ("expected_outcome_present", False),
            ("integer_output_present", False),
        ):
            _exact_bool(
                blind[name],
                expected=expected,
                label=f"loop blind input {name}",
            )
        rows_fp = _fingerprint_shape(
            blind["ordered_loop_rows"],
            label="loop blind ordered_loop_rows",
            ndim=1,
        )
        section_fp = _fingerprint_shape(
            blind["section_values"],
            label="loop blind section_values",
            ndim=2,
            width=2,
        )
        amplitude_fp = _fingerprint_shape(
            blind["boundary_amplitude"],
            label="loop blind boundary_amplitude",
            ndim=1,
        )
        identifiability_fp = _fingerprint_shape(
            blind["boundary_identifiability_score"],
            label="loop blind boundary_identifiability_score",
            ndim=1,
        )
        coherence_fp = _fingerprint_shape(
            blind["boundary_coherence"],
            label="loop blind boundary_coherence",
            ndim=1,
        )
        loop_row_count = rows_fp["shape"][0]  # type: ignore[index]
        if section_fp["shape"] != [loop_row_count, 2] or any(
            document["shape"] != [loop_row_count]
            for document in (
                amplitude_fp,
                identifiability_fp,
                coherence_fp,
            )
        ):
            raise QualificationContractError(
                "loop blind input arrays do not share the ordered row domain"
            )
        expected_input_id = (
            "qli_"
            + canonical_json_sha256(
                {name: blind[name] for name in blind_hash_fields}
                | {
                    "ordered_loop_rows": rows_fp,
                    "section_values": section_fp,
                    "boundary_amplitude": amplitude_fp,
                    "boundary_identifiability_score": identifiability_fp,
                    "boundary_coherence": coherence_fp,
                }
            )[:32]
        )
        _constant(
            blind["input_id"],
            expected_input_id,
            label="loop blind input content pseudonym",
        )
        blind_sha = canonical_json_sha256(blind)
        prediction_sha = canonical_json_sha256(prediction)
        oracle_sha = canonical_json_sha256(oracle)
        for label, observed, expected in (
            (
                "prediction blind input",
                prediction["blind_input_fingerprint_sha256"],
                blind_sha,
            ),
            ("oracle blind input", oracle["blind_input_fingerprint_sha256"], blind_sha),
            (
                "evaluation blind input",
                evaluation["blind_input_fingerprint_sha256"],
                blind_sha,
            ),
            (
                "evaluation prediction",
                evaluation["prediction_fingerprint_sha256"],
                prediction_sha,
            ),
            ("evaluation truth", evaluation["truth_fingerprint_sha256"], oracle_sha),
            (
                "prediction/oracle primary unit",
                prediction["primary_unit_sha256"],
                oracle["primary_unit_sha256"],
            ),
            (
                "blind/prediction primary unit",
                prediction["primary_unit_sha256"],
                blind["primary_unit_sha256"],
            ),
            (
                "prediction/oracle policy",
                prediction["policy_fingerprint_sha256"],
                oracle["policy_fingerprint_sha256"],
            ),
            (
                "evaluation policy",
                evaluation["policy_fingerprint_sha256"],
                prediction["policy_fingerprint_sha256"],
            ),
        ):
            if observed != expected:
                raise QualificationContractError(f"loop {label} digest join mismatch")
        try:
            status = AttemptStatus(prediction["observed_attempt_status"])
            prediction_class = LoopPredictionClass(prediction["prediction_class"])
            disposition = LoopDisposition(oracle["expected_disposition"])
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "loop runtime receipt carries an unsupported enum value"
            ) from error
        prediction_reasons = _canonical_reasons(
            prediction["reason_codes"], label="loop prediction reason_codes"
        )
        oracle_reasons = _canonical_reasons(
            oracle["expected_prerequisite_reasons"],
            label="loop oracle prerequisite reasons",
        )
        require_slug(
            prediction["estimator_id"],
            label="loop prediction estimator_id",
        )
        require_sha256(
            prediction["policy_fingerprint_sha256"],
            label="loop prediction policy_fingerprint_sha256",
        )
        _exact_bool(
            prediction["oracle_read"],
            expected=False,
            label="loop prediction oracle_read",
        )
        _exact_bool(
            prediction["sealed_before_oracle_score"],
            expected=True,
            label="loop prediction sealed_before_oracle_score",
        )
        _exact_bool(
            prediction["sampled_continuous_observable_only"],
            expected=True,
            label="loop prediction sampled-continuous boundary",
        )
        _exact_bool(
            prediction["integer_output_present"],
            expected=False,
            label="loop prediction integer_output_present",
        )
        total = _optional_finite_real(
            prediction["signed_total_cycles"],
            label="loop signed_total_cycles",
        )
        maximum = _optional_finite_real(
            prediction["max_abs_edge_increment_radians"],
            label="loop max_abs_edge_increment_radians",
            minimum=0.0,
        )
        residual = _optional_finite_real(
            prediction["nearest_integer_residual_cycles"],
            label="loop nearest_integer_residual_cycles",
            minimum=0.0,
            maximum=0.5,
        )
        comparison_tolerance = require_finite_real(
            prediction["comparison_tolerance_cycles"],
            label="loop comparison_tolerance_cycles",
            minimum=0.0,
            maximum=0.5,
            maximum_inclusive=False,
        )
        if status is AttemptStatus.EVALUABLE:
            if (
                prediction_class
                not in {
                    LoopPredictionClass.NONZERO,
                    LoopPredictionClass.NULL,
                }
                or prediction_reasons
                or total is None
                or maximum is None
                or residual is None
            ):
                raise QualificationContractError(
                    "loop evaluable prediction receipt violates its typed state"
                )
        elif status is AttemptStatus.INSUFFICIENT:
            if (
                prediction_class is not LoopPredictionClass.ABSTAIN
                or not prediction_reasons
            ):
                raise QualificationContractError(
                    "loop insufficient prediction receipt violates its typed state"
                )
        elif (
            prediction_class is not LoopPredictionClass.NONE
            or prediction_reasons
            or total is not None
            or maximum is not None
            or residual is not None
        ):
            raise QualificationContractError(
                "loop not-run prediction receipt contains observations"
            )
        require_slug(oracle["truth_id"], label="loop oracle truth_id")
        try:
            ObligationMode(oracle["obligation_mode"])
            EvaluationUnit(oracle["evaluation_unit"])
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "loop oracle carries an unsupported obligation/evaluation mode"
            ) from error
        _constant(
            oracle["evaluation_unit"],
            EvaluationUnit.BOUNDARY_LOOP.value,
            label="loop oracle evaluation_unit",
        )
        _exact_bool(
            oracle["estimator_input_allowed"],
            expected=False,
            label="loop oracle estimator_input_allowed",
        )
        _exact_bool(
            oracle["oracle_integer_is_synthetic_expected_sampled_outcome"],
            expected=True,
            label="loop oracle synthetic sampled-outcome boundary",
        )
        _exact_bool(
            oracle["observed_integer_output_present"],
            expected=False,
            label="loop oracle observed_integer_output_present",
        )
        expected_total: int | None
        if oracle["expected_sampled_cycles"] is None:
            expected_total = None
        else:
            expected_total = require_plain_int(
                oracle["expected_sampled_cycles"],
                label="loop expected_sampled_cycles",
            )
        if disposition is LoopDisposition.NONZERO:
            if expected_total in {None, 0} or oracle_reasons:
                raise QualificationContractError(
                    "nonzero loop oracle requires a nonzero expected total"
                )
        elif disposition is LoopDisposition.NULL:
            if expected_total != 0 or oracle_reasons:
                raise QualificationContractError(
                    "null loop oracle requires expected total zero"
                )
        elif expected_total is not None or not oracle_reasons:
            raise QualificationContractError(
                "prerequisite loop oracle requires reasons and no total"
            )
        expected_truth_id = (
            "qlt_"
            + canonical_json_sha256(
                {
                    "blind_input_fingerprint_sha256": blind_sha,
                    "primary_unit_sha256": blind["primary_unit_sha256"],
                    "policy_fingerprint_sha256": oracle["policy_fingerprint_sha256"],
                    "expected_disposition": disposition.value,
                    "expected_sampled_cycles": expected_total,
                    "expected_prerequisite_reasons": list(oracle_reasons),
                    "obligation_mode": oracle["obligation_mode"],
                }
            )[:32]
        )
        _constant(
            oracle["truth_id"],
            expected_truth_id,
            label="loop oracle truth content pseudonym",
        )
        for name, expected in (
            ("sampled_continuous_observable_only", True),
            ("integer_output_present", False),
        ):
            _exact_bool(
                evaluation[name],
                expected=expected,
                label=f"loop evaluation {name}",
            )
        reasons: set[str] = set()
        matched: bool | None = None
        error_cycles: float | None = None
        if status is AttemptStatus.NOT_RUN:
            verdict = QualificationState.NOT_RUN
        elif disposition is LoopDisposition.PREREQUISITE_FAILURE:
            if (
                status is AttemptStatus.INSUFFICIENT
                and prediction_reasons == oracle_reasons
            ):
                verdict = QualificationState.PASS
            else:
                verdict = QualificationState.FAIL
                reasons.add(
                    "prerequisite_reason_mismatch"
                    if status is AttemptStatus.INSUFFICIENT
                    else "forced_output_on_prerequisite_failure"
                )
        elif status is AttemptStatus.INSUFFICIENT:
            verdict = QualificationState.INSUFFICIENT
            reasons.update(prediction_reasons)
        else:
            assert total is not None
            assert expected_total is not None
            error_cycles = abs(total - expected_total)
            within_tolerance = error_cycles <= comparison_tolerance
            if disposition is LoopDisposition.NONZERO:
                matched = (
                    prediction_class is LoopPredictionClass.NONZERO and within_tolerance
                )
                verdict = (
                    QualificationState.PASS if matched else QualificationState.FAIL
                )
                if not matched:
                    reasons.add("expected_signed_sampled_total_not_recovered")
            else:
                matched = (
                    prediction_class is LoopPredictionClass.NULL and within_tolerance
                )
                verdict = (
                    QualificationState.PASS if matched else QualificationState.FAIL
                )
                if not matched:
                    reasons.add("false_nonzero_sampled_phase")
        expected_evaluation = {
            "observed_attempt_status": status.value,
            "expected_disposition": disposition.value,
            "gate_verdict": verdict.value,
            "reason_codes": sorted(reasons),
            "sampled_total_match": matched,
            "signed_error_cycles": error_cycles,
            "obligation_mode": oracle["obligation_mode"],
            "evaluation_unit": oracle["evaluation_unit"],
        }
        if any(
            evaluation[name] != expected
            for name, expected in expected_evaluation.items()
        ):
            raise QualificationContractError(
                "loop case evaluation differs from mechanically recomputed scoring"
            )
        return blind, prediction, oracle, evaluation

    def validate_summary(self, summary: CrossedCellSummary) -> None:
        if not isinstance(summary, CrossedCellSummary):
            raise TypeError("summary must be a CrossedCellSummary")
        blind, prediction, oracle, evaluation = self._documents()
        signed_error = evaluation["signed_error_cycles"]
        expected = {
            "cell_id": self.cell_id,
            "field_graph_fingerprint_sha256": blind["field_graph_fingerprint_sha256"],
            "cycle_graph_fingerprint_sha256": blind["cycle_graph_fingerprint_sha256"],
            "field_estimate_fingerprint_sha256": blind[
                "field_estimate_fingerprint_sha256"
            ],
            "cycle_binding_fingerprint_sha256": blind[
                "cycle_binding_fingerprint_sha256"
            ],
            "representative_content_sha256": blind["representative_content_sha256"],
            "blind_input_fingerprint_sha256": canonical_json_sha256(blind),
            "prediction_fingerprint_sha256": canonical_json_sha256(prediction),
            "oracle_fingerprint_sha256": canonical_json_sha256(oracle),
            "attempt_status": prediction["observed_attempt_status"],
            "prediction_class": prediction["prediction_class"],
            "expected_disposition": oracle["expected_disposition"],
            "state": evaluation["gate_verdict"],
            "continuous_signed_total_cycles": prediction["signed_total_cycles"],
            "oracle_absolute_error_cycles": signed_error,
            "reason_codes": tuple(evaluation["reason_codes"]),  # type: ignore[arg-type]
        }
        observed = {
            "cell_id": summary.cell_id,
            "field_graph_fingerprint_sha256": (summary.field_graph_fingerprint_sha256),
            "cycle_graph_fingerprint_sha256": (summary.cycle_graph_fingerprint_sha256),
            "field_estimate_fingerprint_sha256": (
                summary.field_estimate_fingerprint_sha256
            ),
            "cycle_binding_fingerprint_sha256": (
                summary.cycle_binding_fingerprint_sha256
            ),
            "representative_content_sha256": (summary.representative_content_sha256),
            "blind_input_fingerprint_sha256": (summary.blind_input_fingerprint_sha256),
            "prediction_fingerprint_sha256": (summary.prediction_fingerprint_sha256),
            "oracle_fingerprint_sha256": summary.oracle_fingerprint_sha256,
            "attempt_status": summary.attempt_status.value,
            "prediction_class": summary.prediction_class.value,
            "expected_disposition": summary.expected_disposition.value,
            "state": summary.state.value,
            "continuous_signed_total_cycles": (summary.continuous_signed_total_cycles),
            "oracle_absolute_error_cycles": (summary.oracle_absolute_error_cycles),
            "reason_codes": summary.reason_codes,
        }
        if observed != expected:
            raise QualificationContractError(
                "loop normalized summary differs from its full evaluation receipt"
            )
        if self.normalized_summary_sha256 != canonical_json_sha256(summary.to_dict()):
            raise QualificationContractError(
                "loop normalized summary digest differs from its receipt"
            )

    @classmethod
    def from_runtime(
        cls,
        *,
        cell_id: str,
        blind_input: object,
        sealed_prediction: object,
        oracle_truth: object,
        case_evaluation: object,
        summary: CrossedCellSummary,
    ) -> LoopCellEvaluationReceipt:
        from .winding import (
            BlindLoopInput,
            LoopCaseEvaluation,
            LoopOracleTruth,
            SealedLoopPrediction,
        )

        if not isinstance(blind_input, BlindLoopInput):
            raise TypeError("blind_input must be a BlindLoopInput")
        if not isinstance(sealed_prediction, SealedLoopPrediction):
            raise TypeError("sealed_prediction must be a SealedLoopPrediction")
        if not isinstance(oracle_truth, LoopOracleTruth):
            raise TypeError("oracle_truth must be a LoopOracleTruth")
        if not isinstance(case_evaluation, LoopCaseEvaluation):
            raise TypeError("case_evaluation must be a LoopCaseEvaluation")
        receipt = cls(
            cell_id=cell_id,
            blind_input_receipt=blind_input.to_dict(),
            sealed_prediction_receipt=sealed_prediction.to_dict(),
            oracle_truth_receipt=oracle_truth.to_dict(),
            case_evaluation_receipt=case_evaluation.to_dict(),
            normalized_summary_sha256=canonical_json_sha256(summary.to_dict()),
        )
        receipt.validate_summary(summary)
        return receipt

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "cell_id": self.cell_id,
            "blind_input_receipt": self.blind_input_receipt,
            "sealed_prediction_receipt": self.sealed_prediction_receipt,
            "oracle_truth_receipt": self.oracle_truth_receipt,
            "case_evaluation_receipt": self.case_evaluation_receipt,
            "normalized_summary_sha256": self.normalized_summary_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> LoopCellEvaluationReceipt:
        item = _mapping(value, label="loop cell evaluation receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="loop cell evaluation receipt")
        return cls(
            schema_version=item["schema_version"],  # type: ignore[arg-type]
            cell_id=require_slug(item["cell_id"], label="cell_id"),
            blind_input_receipt=_mapping(
                item["blind_input_receipt"], label="blind_input_receipt"
            ),
            sealed_prediction_receipt=_mapping(
                item["sealed_prediction_receipt"], label="sealed_prediction_receipt"
            ),
            oracle_truth_receipt=_mapping(
                item["oracle_truth_receipt"], label="oracle_truth_receipt"
            ),
            case_evaluation_receipt=_mapping(
                item["case_evaluation_receipt"], label="case_evaluation_receipt"
            ),
            normalized_summary_sha256=require_sha256(
                item["normalized_summary_sha256"],
                label="normalized_summary_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class NonvacuityEvaluationReceipt:
    """Full crossed nonvacuity receipt joined to its normalized summary."""

    primary_unit_id: str
    crossed_nonvacuity_receipt: dict[str, object]
    normalized_summary_sha256: str
    schema_version: str = NONVACUITY_EVIDENCE_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "primary_unit_id",
            "crossed_nonvacuity_receipt",
            "normalized_summary_sha256",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            NONVACUITY_EVIDENCE_SCHEMA_VERSION,
            label="nonvacuity evidence schema_version",
        )
        require_slug(self.primary_unit_id, label="nonvacuity primary_unit_id")
        require_sha256(
            self.normalized_summary_sha256,
            label="nonvacuity normalized_summary_sha256",
        )
        self._receipt()

    def _receipt(self) -> dict[str, object]:
        document = _mapping(
            self.crossed_nonvacuity_receipt,
            label="crossed nonvacuity runtime receipt",
        )
        expected = frozenset(
            {
                "schema_version",
                *_BOUNDARY_KEYS,
                "state",
                "substantive_output_variation_required",
                "field_adjacency_variant_count",
                "cycle_adjacency_variant_count",
                "field_consumption_variant_count",
                "field_output_variant_count",
                "substantive_output_distance_metric",
                "maximum_pairwise_substantive_output_distance",
                "minimum_substantive_output_distance",
                "field_graph_pair_effects",
                "substantive_response_field_graph_ids",
                "substantive_response_field_graph_count",
                "required_substantive_response_field_graph_count",
                "matched_cycle_count",
                "representative_content_variant_count",
                "minimum_representative_content_variants",
                "reason_codes",
                "id_only_nonvacuity_forbidden",
                "field_estimate_to_graph_binding_verified",
                "substantive_output_excludes_support_bookkeeping",
                "edge_coherence_is_diagnostic_not_effect_eligible",
                "single_scalar_effect_is_insufficient",
                "every_a_graph_requires_substantive_response",
                "graph_cells_are_repeated_measures",
            }
        )
        _exact_keys(document, expected, label="crossed nonvacuity runtime receipt")
        _constant(
            document["schema_version"],
            "spirallens.crossed-nonvacuity.v0.4",
            label="crossed nonvacuity schema_version",
        )
        for name, expected_value in _BOUNDARY.items():
            _constant(
                document[name],
                expected_value,
                label=f"crossed nonvacuity {name}",
            )
        _constant(
            document["substantive_output_distance_metric"],
            ("per-component-rms-over-section-amplitude-identifiability-v0.2"),
            label="crossed nonvacuity substantive output distance metric",
        )
        for name in (
            "id_only_nonvacuity_forbidden",
            "field_estimate_to_graph_binding_verified",
            "substantive_output_excludes_support_bookkeeping",
            "edge_coherence_is_diagnostic_not_effect_eligible",
            "single_scalar_effect_is_insufficient",
            "every_a_graph_requires_substantive_response",
            "graph_cells_are_repeated_measures",
        ):
            _exact_bool(
                document[name],
                expected=True,
                label=f"crossed nonvacuity {name}",
            )
        from .crossed import CrossedNonvacuityReceipt

        CrossedNonvacuityReceipt.from_dict(document)
        return document

    def validate_summary(self, summary: CrossedNonvacuitySummary) -> None:
        if not isinstance(summary, CrossedNonvacuitySummary):
            raise TypeError("summary must be a CrossedNonvacuitySummary")
        document = self._receipt()
        fields = (
            "state",
            "substantive_output_variation_required",
            "field_adjacency_variant_count",
            "cycle_adjacency_variant_count",
            "field_consumption_variant_count",
            "field_output_variant_count",
            "maximum_pairwise_substantive_output_distance",
            "minimum_substantive_output_distance",
            "field_graph_pair_effects",
            "substantive_response_field_graph_ids",
            "substantive_response_field_graph_count",
            "required_substantive_response_field_graph_count",
            "matched_cycle_count",
            "representative_content_variant_count",
            "minimum_representative_content_variants",
            "reason_codes",
        )
        observed = summary.to_dict()
        for name in fields:
            expected = (
                list(summary.reason_codes)
                if name == "reason_codes"
                else (
                    [item.to_dict() for item in summary.field_graph_pair_effects]
                    if name == "field_graph_pair_effects"
                    else (
                        list(summary.substantive_response_field_graph_ids)
                        if name == "substantive_response_field_graph_ids"
                        else (
                            summary.state.value
                            if name == "state"
                            else getattr(summary, name)
                        )
                    )
                )
            )
            if document[name] != expected:
                raise QualificationContractError(
                    f"nonvacuity normalized {name} differs from its full receipt"
                )
        if (
            summary.primary_unit_id != self.primary_unit_id
            or summary.receipt_fingerprint_sha256 != canonical_json_sha256(document)
            or self.normalized_summary_sha256 != canonical_json_sha256(observed)
        ):
            raise QualificationContractError(
                "nonvacuity normalized identity differs from its full receipt"
            )

    @classmethod
    def from_runtime(
        cls,
        *,
        primary_unit_id: str,
        receipt: object,
        summary: CrossedNonvacuitySummary,
    ) -> NonvacuityEvaluationReceipt:
        from .crossed import CrossedNonvacuityReceipt

        if not isinstance(receipt, CrossedNonvacuityReceipt):
            raise TypeError("receipt must be a CrossedNonvacuityReceipt")
        result = cls(
            primary_unit_id=primary_unit_id,
            crossed_nonvacuity_receipt=receipt.to_dict(),
            normalized_summary_sha256=canonical_json_sha256(summary.to_dict()),
        )
        result.validate_summary(summary)
        return result

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "primary_unit_id": self.primary_unit_id,
            "crossed_nonvacuity_receipt": self.crossed_nonvacuity_receipt,
            "normalized_summary_sha256": self.normalized_summary_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> NonvacuityEvaluationReceipt:
        item = _mapping(value, label="nonvacuity evaluation receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="nonvacuity evaluation receipt")
        return cls(
            schema_version=item["schema_version"],  # type: ignore[arg-type]
            primary_unit_id=require_slug(
                item["primary_unit_id"], label="primary_unit_id"
            ),
            crossed_nonvacuity_receipt=_mapping(
                item["crossed_nonvacuity_receipt"],
                label="crossed_nonvacuity_receipt",
            ),
            normalized_summary_sha256=require_sha256(
                item["normalized_summary_sha256"],
                label="normalized_summary_sha256",
            ),
        )


_D1_NUMERIC_METRIC_CONTRACTS = {
    "cartesian": {
        "amplitude-max-absolute-error": (
            "at-most",
            "d1_numeric_tolerance",
        ),
        "direction-minimum-cosine": (
            "at-least",
            "d1_cartesian_direction_cosine_floor",
        ),
        "second-harmonic-max-absolute-error": (
            "at-most",
            "d1_numeric_tolerance",
        ),
        "split-max-disagreement": (
            "at-most",
            "d1_numeric_tolerance",
        ),
        "support-mismatch-count": ("exact-zero", None),
    },
    "representation": {
        "amplitude-max-absolute-error": (
            "at-most",
            "d1_numeric_tolerance",
        ),
        "phase-law-coherence": (
            "at-least",
            "d1_representation_phase_coherence_floor",
        ),
        "support-mismatch-count": ("exact-zero", None),
    },
}
_D1_NUMERIC_METRICS = {
    family: tuple(contracts)
    for family, contracts in _D1_NUMERIC_METRIC_CONTRACTS.items()
}


@dataclass(frozen=True, slots=True)
class D1NumericMetricReceipt:
    """One evaluator-side numeric obligation applied after output sealing."""

    metric_id: str
    graph_family: str
    field_graph_fingerprint_sha256: str
    estimator_output_sha256: str
    oracle_fingerprint_sha256: str
    comparator: str
    observed_value: float
    threshold: float
    passed: bool
    schema_version: str = D1_NUMERIC_METRIC_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "metric_id",
            "graph_family",
            "field_graph_fingerprint_sha256",
            "estimator_output_sha256",
            "oracle_fingerprint_sha256",
            "comparator",
            "observed_value",
            "threshold",
            "passed",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            D1_NUMERIC_METRIC_SCHEMA_VERSION,
            label="D1 numeric metric schema_version",
        )
        known_metrics = {
            metric
            for family_metrics in _D1_NUMERIC_METRICS.values()
            for metric in family_metrics
        }
        if self.metric_id not in known_metrics:
            raise QualificationContractError(
                "D1 numeric metric is outside the closed metric universe"
            )
        if self.graph_family not in {
            "fixed-radius",
            "mutual-knn",
            "shared-neighbor",
        }:
            raise QualificationContractError(
                "D1 numeric metric graph family is outside the closed universe"
            )
        for name in (
            "field_graph_fingerprint_sha256",
            "estimator_output_sha256",
            "oracle_fingerprint_sha256",
        ):
            require_sha256(getattr(self, name), label=f"D1 numeric {name}")
        if self.comparator not in {"at-least", "at-most", "exact-zero"}:
            raise QualificationContractError(
                "D1 numeric metric comparator is outside the closed universe"
            )
        observed = require_finite_real(
            self.observed_value,
            label="D1 numeric observed_value",
        )
        threshold = require_finite_real(
            self.threshold,
            label="D1 numeric threshold",
        )
        if threshold < 0.0:
            raise QualificationContractError("D1 numeric threshold must be nonnegative")
        if type(self.passed) is not bool:
            raise TypeError("D1 numeric passed must be a boolean")
        if self.comparator == "at-most":
            expected = observed <= threshold
        elif self.comparator == "at-least":
            expected = observed >= threshold
        else:
            if threshold != 0.0:
                raise QualificationContractError(
                    "D1 exact-zero metric threshold must equal zero"
                )
            expected = observed == 0.0
        if self.passed is not expected:
            raise QualificationContractError(
                "D1 numeric pass flag differs from its observed comparison"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "metric_id": self.metric_id,
            "graph_family": self.graph_family,
            "field_graph_fingerprint_sha256": (self.field_graph_fingerprint_sha256),
            "estimator_output_sha256": self.estimator_output_sha256,
            "oracle_fingerprint_sha256": self.oracle_fingerprint_sha256,
            "comparator": self.comparator,
            "observed_value": self.observed_value,
            "threshold": self.threshold,
            "passed": self.passed,
        }

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> D1NumericMetricReceipt:
        item = _mapping(value, label="D1 numeric metric receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="D1 numeric metric receipt")
        return cls(
            schema_version=item["schema_version"],  # type: ignore[arg-type]
            metric_id=require_slug(item["metric_id"], label="D1 metric_id"),
            graph_family=require_slug(
                item["graph_family"],
                label="D1 metric graph_family",
            ),
            field_graph_fingerprint_sha256=require_sha256(
                item["field_graph_fingerprint_sha256"],
                label="D1 metric field graph",
            ),
            estimator_output_sha256=require_sha256(
                item["estimator_output_sha256"],
                label="D1 metric estimator output",
            ),
            oracle_fingerprint_sha256=require_sha256(
                item["oracle_fingerprint_sha256"],
                label="D1 metric oracle",
            ),
            comparator=require_slug(
                item["comparator"],
                label="D1 metric comparator",
            ),
            observed_value=require_finite_real(
                item["observed_value"],
                label="D1 metric observed_value",
            ),
            threshold=require_finite_real(
                item["threshold"],
                label="D1 metric threshold",
            ),
            passed=item["passed"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class D1CaseExecutionReceipt:
    """One generator case consumed by three distinct field-graph executions."""

    case_id: str
    generator_case_receipt: dict[str, object]
    estimator_input_receipt: dict[str, object]
    estimator_output_receipts: tuple[dict[str, object], ...]
    numeric_metric_receipts: tuple[D1NumericMetricReceipt, ...]
    schema_version: str = D1_CASE_EXECUTION_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "case_id",
            "generator_case_receipt",
            "estimator_input_receipt",
            "estimator_output_receipts",
            "numeric_metric_receipts",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            D1_CASE_EXECUTION_SCHEMA_VERSION,
            label="D1 case execution schema_version",
        )
        require_slug(self.case_id, label="D1 case execution case_id")
        if type(self.estimator_output_receipts) is not tuple:
            raise TypeError("D1 estimator output receipts must be a tuple")
        if len(self.estimator_output_receipts) != 3:
            raise QualificationContractError(
                "D1 cases require exactly three graph-family estimator executions"
            )
        input_sha = canonical_json_sha256(self.estimator_input_receipt)
        graph_fingerprints: list[str] = []
        output_fingerprints: list[str] = []
        for index, output in enumerate(self.estimator_output_receipts):
            document = _mapping(output, label=f"D1 estimator output[{index}]")
            for key in (
                "estimator_input_fingerprint_sha256",
                "field_graph_fingerprint_sha256",
                "estimator_id",
            ):
                if key not in document:
                    raise QualificationContractError(
                        f"D1 estimator output[{index}] lacks {key}"
                    )
            if document["estimator_input_fingerprint_sha256"] != input_sha:
                raise QualificationContractError(
                    "D1 estimator output differs from its full input receipt"
                )
            require_slug(
                document["estimator_id"],
                label=f"D1 estimator output[{index}] estimator_id",
            )
            graph_fingerprints.append(
                require_sha256(
                    document["field_graph_fingerprint_sha256"],
                    label=f"D1 estimator output[{index}] field graph",
                )
            )
            output_fingerprints.append(canonical_json_sha256(document))
        if len(set(graph_fingerprints)) != 3:
            raise QualificationContractError(
                "D1 estimator outputs must consume three distinct graph receipts"
            )
        if len(set(output_fingerprints)) != 3:
            raise QualificationContractError(
                "D1 estimator output receipts must retain three distinct "
                "graph-bound execution identities"
            )
        family = (
            "cartesian"
            if self.case_id.startswith("cartesian-fourier-")
            else "representation"
        )
        required_metrics = _D1_NUMERIC_METRICS[family]
        expected_count = 3 * len(required_metrics)
        if (
            type(self.numeric_metric_receipts) is not tuple
            or len(self.numeric_metric_receipts) != expected_count
        ):
            raise QualificationContractError(
                "D1 case must carry the exact per-graph numeric metric matrix"
            )
        outputs_by_graph = {
            require_sha256(
                output["field_graph_fingerprint_sha256"],
                label="D1 output field graph",
            ): (
                require_slug(
                    output["field_graph_family"],
                    label="D1 output graph family",
                ),
                canonical_json_sha256(output),
            )
            for output in self.estimator_output_receipts
        }
        metrics_by_graph: dict[str, list[D1NumericMetricReceipt]] = {}
        for metric in self.numeric_metric_receipts:
            metrics_by_graph.setdefault(
                metric.field_graph_fingerprint_sha256,
                [],
            ).append(metric)
        if set(metrics_by_graph) != set(outputs_by_graph):
            raise QualificationContractError(
                "D1 numeric metrics differ from the exact estimator graph outputs"
            )
        expected_oracle = (
            self.generator_case_receipt.get("oracle_truth_fingerprint_sha256")
            if family == "cartesian"
            else canonical_json_sha256(self.generator_case_receipt)
        )
        for graph_sha256, metrics in metrics_by_graph.items():
            graph_family, output_sha256 = outputs_by_graph[graph_sha256]
            if (
                tuple(item.metric_id for item in metrics) != required_metrics
                or any(item.graph_family != graph_family for item in metrics)
                or any(
                    item.estimator_output_sha256 != output_sha256 for item in metrics
                )
                or len({item.oracle_fingerprint_sha256 for item in metrics}) != 1
                or any(
                    item.oracle_fingerprint_sha256 != expected_oracle
                    for item in metrics
                )
            ):
                raise QualificationContractError(
                    "D1 numeric metric group differs from its graph, output, "
                    "oracle, or exact metric order"
                )

    @property
    def observation_fingerprints_sha256(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    canonical_json_sha256(self.generator_case_receipt),
                    canonical_json_sha256(self.estimator_input_receipt),
                    *(
                        canonical_json_sha256(item)
                        for item in self.estimator_output_receipts
                    ),
                    *(item.canonical_sha256 for item in self.numeric_metric_receipts),
                }
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "generator_case_receipt": self.generator_case_receipt,
            "estimator_input_receipt": self.estimator_input_receipt,
            "estimator_output_receipts": list(self.estimator_output_receipts),
            "numeric_metric_receipts": [
                item.to_dict() for item in self.numeric_metric_receipts
            ],
        }

    @classmethod
    def from_dict(cls, value: object) -> D1CaseExecutionReceipt:
        item = _mapping(value, label="D1 case execution receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="D1 case execution receipt")
        outputs = item["estimator_output_receipts"]
        metrics = item["numeric_metric_receipts"]
        if not isinstance(outputs, list):
            raise QualificationContractError(
                "D1 estimator_output_receipts must be a JSON array"
            )
        if not isinstance(metrics, list):
            raise QualificationContractError(
                "D1 numeric_metric_receipts must be a JSON array"
            )
        return cls(
            schema_version=item["schema_version"],  # type: ignore[arg-type]
            case_id=require_slug(item["case_id"], label="D1 case_id"),
            generator_case_receipt=_mapping(
                item["generator_case_receipt"],
                label="D1 generator_case_receipt",
            ),
            estimator_input_receipt=_mapping(
                item["estimator_input_receipt"],
                label="D1 estimator_input_receipt",
            ),
            estimator_output_receipts=tuple(
                _mapping(entry, label="D1 estimator output") for entry in outputs
            ),
            numeric_metric_receipts=tuple(
                D1NumericMetricReceipt.from_dict(entry) for entry in metrics
            ),
        )


_D1_EXPECTED_CASES = {
    "cartesian-fourier-family-verified": (
        "cartesian-fourier-fixed-null",
        "cartesian-fourier-no-core-null",
        "cartesian-fourier-positive",
        "cartesian-fourier-prerequisite-failure",
    ),
    "representation-family-verified": (
        "angular-section-positive",
        "fixed-direction-null",
    ),
}


def _d1_metric(
    *,
    metric_id: str,
    estimate: object,
    oracle_fingerprint_sha256: str,
    comparator: str,
    observed_value: float,
    threshold: float,
) -> D1NumericMetricReceipt:
    output = estimate.to_dict()  # type: ignore[attr-defined]
    graph_family = output["field_graph_family"]
    graph_sha256 = output["field_graph_fingerprint_sha256"]
    if not isinstance(graph_family, str) or not isinstance(graph_sha256, str):
        raise QualificationContractError(
            "D1 estimate lacks a typed graph family or fingerprint"
        )
    passed = (
        observed_value <= threshold
        if comparator == "at-most"
        else (
            observed_value >= threshold
            if comparator == "at-least"
            else observed_value == 0.0
        )
    )
    return D1NumericMetricReceipt(
        metric_id=metric_id,
        graph_family=graph_family,
        field_graph_fingerprint_sha256=graph_sha256,
        estimator_output_sha256=canonical_json_sha256(output),
        oracle_fingerprint_sha256=oracle_fingerprint_sha256,
        comparator=comparator,
        observed_value=observed_value,
        threshold=threshold,
        passed=passed,
    )


def _cartesian_d1_numeric_metrics(
    *,
    case: object,
    estimate: object,
    numeric_tolerance: float,
    direction_cosine_floor: float,
) -> tuple[D1NumericMetricReceipt, ...]:
    """Score one sealed Cartesian estimate against evaluator-only field truth."""

    import numpy as np

    truth = case.oracle_truth  # type: ignore[attr-defined]
    amplitude = estimate.amplitude  # type: ignore[attr-defined]
    observed_support = estimate.support & (  # type: ignore[attr-defined]
        amplitude > numeric_tolerance
    )
    expected_support = truth.f2_support
    direction_rows = expected_support & observed_support
    if np.any(direction_rows):
        numerator = np.sum(
            estimate.section_values[direction_rows]  # type: ignore[attr-defined]
            * truth.f2_coordinates[direction_rows],
            axis=1,
        )
        denominator = amplitude[direction_rows] * truth.f2_amplitude[direction_rows]
        minimum_cosine = float(np.min(np.clip(numerator / denominator, -1.0, 1.0)))
    else:
        minimum_cosine = 1.0 if not np.any(expected_support) else -1.0
    values = {
        "amplitude-max-absolute-error": (
            float(np.max(np.abs(amplitude - truth.f2_amplitude))),
            "at-most",
            numeric_tolerance,
        ),
        "direction-minimum-cosine": (
            minimum_cosine,
            "at-least",
            direction_cosine_floor,
        ),
        "second-harmonic-max-absolute-error": (
            float(
                np.max(
                    np.abs(
                        estimate.second_harmonic_values  # type: ignore[attr-defined]
                        - truth.f4_coordinates
                    )
                )
            ),
            "at-most",
            numeric_tolerance,
        ),
        "split-max-disagreement": (
            float(
                np.max(
                    estimate.split_disagreement  # type: ignore[attr-defined]
                )
            ),
            "at-most",
            numeric_tolerance,
        ),
        "support-mismatch-count": (
            float(np.count_nonzero(observed_support != expected_support)),
            "exact-zero",
            0.0,
        ),
    }
    return tuple(
        _d1_metric(
            metric_id=metric_id,
            estimate=estimate,
            oracle_fingerprint_sha256=truth.fingerprint_sha256,
            comparator=values[metric_id][1],
            observed_value=values[metric_id][0],
            threshold=values[metric_id][2],
        )
        for metric_id in _D1_NUMERIC_METRICS["cartesian"]
    )


def _representation_d1_numeric_metrics(
    *,
    phantom: object,
    case: object,
    estimate: object,
    numeric_tolerance: float,
    phase_coherence_floor: float,
) -> tuple[D1NumericMetricReceipt, ...]:
    """Score one sealed representation estimate under a global O(2) gauge."""

    import numpy as np

    amplitude = estimate.amplitude  # type: ignore[attr-defined]
    observed_support = estimate.support & (  # type: ignore[attr-defined]
        amplitude > numeric_tolerance
    )
    expected_support = case.f2_support  # type: ignore[attr-defined]
    direction_rows = expected_support & observed_support
    if np.any(direction_rows):
        section = estimate.section_values[direction_rows]  # type: ignore[attr-defined]
        observed_unit = (section[:, 0] + 1j * section[:, 1]) / amplitude[direction_rows]
        if case.case_id == "angular-section-positive":  # type: ignore[attr-defined]
            coordinates = phantom.grid_coordinates[direction_rows]  # type: ignore[attr-defined]
            expected_complex = coordinates[:, 0] + 1j * coordinates[:, 1]
            expected_unit = expected_complex / np.abs(expected_complex)
        else:
            expected_unit = np.ones(
                observed_unit.shape[0],
                dtype=np.complex128,
            )
        phase_coherence = float(
            np.abs(np.mean(observed_unit * np.conjugate(expected_unit)))
        )
    else:
        phase_coherence = 1.0 if not np.any(expected_support) else 0.0
    values = {
        "amplitude-max-absolute-error": (
            float(
                np.max(
                    np.abs(
                        amplitude - case.f2_amplitude  # type: ignore[attr-defined]
                    )
                )
            ),
            "at-most",
            numeric_tolerance,
        ),
        "phase-law-coherence": (
            phase_coherence,
            "at-least",
            phase_coherence_floor,
        ),
        "support-mismatch-count": (
            float(np.count_nonzero(observed_support != expected_support)),
            "exact-zero",
            0.0,
        ),
    }
    return tuple(
        _d1_metric(
            metric_id=metric_id,
            estimate=estimate,
            oracle_fingerprint_sha256=case.canonical_sha256,  # type: ignore[attr-defined]
            comparator=values[metric_id][1],
            observed_value=values[metric_id][0],
            threshold=values[metric_id][2],
        )
        for metric_id in _D1_NUMERIC_METRICS["representation"]
    )


@dataclass(frozen=True, slots=True)
class D1FamilyExecutionReceipt:
    """Full generator and estimator receipts for one independent D1 family."""

    evidence_id: str
    generator_family_receipt: dict[str, object]
    cases: tuple[D1CaseExecutionReceipt, ...]
    schema_version: str = D1_FAMILY_EXECUTION_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "evidence_id",
            "generator_family_receipt",
            "cases",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            D1_FAMILY_EXECUTION_SCHEMA_VERSION,
            label="D1 family execution schema_version",
        )
        if self.evidence_id not in _D1_EXPECTED_CASES:
            raise QualificationContractError(
                "D1 family execution evidence_id is outside the closed universe"
            )
        if (
            tuple(item.case_id for item in self.cases)
            != _D1_EXPECTED_CASES[self.evidence_id]
        ):
            raise QualificationContractError(
                "D1 family execution differs from its exact required case universe"
            )
        generator_cases = self.generator_family_receipt.get("cases")
        if not isinstance(generator_cases, list):
            raise QualificationContractError(
                "D1 generator family receipt must contain full case receipts"
            )
        by_case: dict[str, dict[str, object]] = {}
        for document_raw in generator_cases:
            document = _mapping(document_raw, label="D1 generator family case")
            case_id = document.get("case_id")
            if not isinstance(case_id, str):
                raise QualificationContractError(
                    "D1 generator family case must carry case_id"
                )
            by_case[case_id] = document
        if set(by_case) != set(_D1_EXPECTED_CASES[self.evidence_id]):
            raise QualificationContractError(
                "D1 generator family receipt case universe differs from contract"
            )
        if self.evidence_id == "cartesian-fourier-family-verified":
            _exact_keys(
                self.generator_family_receipt,
                {
                    "receipt_version",
                    "record_scope",
                    "persistence_round_trip_supported",
                    "claim_scope",
                    "claim_ceiling",
                    "spec",
                    "family_identity",
                    "cases",
                    "graph_constructed",
                    "core_localized",
                    "loop_constructed",
                    "sampled_winding_observed",
                    "integer_output_authorized",
                    "qualification_gate_evaluated",
                    "d0_d8_advanced",
                    "subject_access_authorized",
                    "semantic_or_sae_labels_present",
                },
                label="Cartesian D1 generator family receipt",
            )
            _constant(
                self.generator_family_receipt.get("receipt_version"),
                "spirallens.cartesian-fourier-domain-phantom-receipt.v0.2",
                label="Cartesian D1 generator receipt version",
            )
            input_version = "spirallens.cartesian-fourier-estimator-inputs-receipt.v0.1"
            output_version = "spirallens.cartesian-fourier-field-estimate.v0.4"
            expected_estimator_id = (
                "interleaved-first-harmonic-graph-local-direction-v0.4"
            )
        else:
            _exact_keys(
                self.generator_family_receipt,
                {
                    "schema_version",
                    "spec",
                    "ambient_basis_sha256",
                    "grid_coordinates_sha256",
                    "cases",
                },
                label="representation D1 generator family receipt",
            )
            _constant(
                self.generator_family_receipt.get("schema_version"),
                "spirallens.representation-phantom.v0.1",
                label="representation D1 generator receipt version",
            )
            input_version = "spirallens.representation-estimator-input-receipt.v0.1"
            output_version = "spirallens.representation-field-estimate-receipt.v0.2"
            expected_estimator_id = (
                "local-rank-two-projector-global-reference-lift-v0.2"
            )
        for case in self.cases:
            if case.generator_case_receipt != by_case[case.case_id]:
                raise QualificationContractError(
                    "D1 case receipt differs from its full generator family receipt"
                )
            _constant(
                case.estimator_input_receipt.get("receipt_version"),
                input_version,
                label=f"D1 {case.case_id} estimator input version",
            )
            if self.evidence_id == "cartesian-fourier-family-verified":
                _exact_keys(
                    case.generator_case_receipt,
                    {
                        "receipt_version",
                        "record_scope",
                        "persistence_round_trip_supported",
                        "case_id",
                        "estimator_inputs_fingerprint_sha256",
                        "oracle_truth_fingerprint_sha256",
                        "observation_noise_scale",
                        "target_visible_noise_required_when_nonzero",
                        "truth_separated_from_estimator_inputs",
                    },
                    label=f"Cartesian D1 {case.case_id} generator case",
                )
                _exact_keys(
                    case.estimator_input_receipt,
                    {
                        "receipt_version",
                        "record_scope",
                        "persistence_round_trip_supported",
                        "input_id",
                        "arrays",
                        "truth_present",
                        "case_id_present",
                        "disposition_present",
                        "center_anchor_present",
                        "charge_present",
                        "expected_loop_response_present",
                        "semantic_labels_present",
                        "subject_values_present",
                    },
                    label=f"Cartesian D1 {case.case_id} estimator input",
                )
                output_keys = {
                    "receipt_version",
                    "record_scope",
                    "persistence_round_trip_supported",
                    "claim_scope",
                    "claim_ceiling",
                    "estimator_id",
                    "estimator_input_fingerprint_sha256",
                    "field_graph_fingerprint_sha256",
                    "field_graph_family",
                    "field_consumption_sha256",
                    "substantive_output_sha256",
                    "output_sha256",
                    "arrays",
                    "fit_role",
                    "evaluation_role",
                    "graph_local_direction_smoothing_weight",
                    "graph_local_step_preserves_raw_amplitude",
                    "same_object_amplitude_and_direction",
                    "truth_read",
                    "anchor_read",
                    "charge_read",
                    "loop_read",
                    "integer_output_authorized",
                    "topology_claimed",
                    "subject_access_authorized",
                    "d0_d8_advanced",
                }
            else:
                _exact_keys(
                    case.generator_case_receipt,
                    {
                        "schema_version",
                        "spec_sha256",
                        "case_id",
                        "case_index",
                        "payloads",
                    },
                    label=f"representation D1 {case.case_id} generator case",
                )
                _exact_keys(
                    case.estimator_input_receipt,
                    {
                        "receipt_version",
                        "record_scope",
                        "persistence_round_trip_supported",
                        "input_id",
                        "primary_unit_id",
                        "spec_sha256",
                        "fit_probe_indices",
                        "evaluation_probe_indices",
                        "arrays",
                        "truth_present",
                        "case_label_present",
                        "center_anchor_present",
                        "charge_present",
                        "cycle_present",
                        "loop_observable_present",
                        "subject_data_present",
                    },
                    label=f"representation D1 {case.case_id} estimator input",
                )
                output_keys = {
                    "receipt_version",
                    "record_scope",
                    "persistence_round_trip_supported",
                    "claim_ceiling",
                    "estimator_id",
                    "support_rule_id",
                    "canonical_edge_endpoint_namespace",
                    "estimator_input_fingerprint_sha256",
                    "primary_unit_id",
                    "field_graph_fingerprint_sha256",
                    "field_graph_family",
                    "field_consumption_sha256",
                    "substantive_output_sha256",
                    "output_sha256",
                    "arrays",
                    "fit_role",
                    "evaluation_role",
                    "trivialization_id",
                    "same_object_amplitude_and_direction",
                    "local_frame_gauge_cancelled_by_projector_reconstruction",
                    "truth_read",
                    "anchor_read",
                    "charge_read",
                    "loop_read",
                    "integer_output_authorized",
                    "core_localized",
                    "topology_claimed",
                    "semantic_claimed",
                    "subject_access_authorized",
                    "d0_d8_advanced",
                }
            graph_families: set[object] = set()
            estimator_input_sha256 = canonical_json_sha256(case.estimator_input_receipt)
            for output in case.estimator_output_receipts:
                _exact_keys(
                    output,
                    output_keys,
                    label=f"D1 {case.case_id} estimator output",
                )
                _constant(
                    output.get("receipt_version"),
                    output_version,
                    label=f"D1 {case.case_id} estimator output version",
                )
                _constant(
                    output["estimator_id"],
                    expected_estimator_id,
                    label=f"D1 {case.case_id} estimator_id",
                )
                _constant(
                    output["estimator_input_fingerprint_sha256"],
                    estimator_input_sha256,
                    label=(f"D1 {case.case_id} estimator-input fingerprint join"),
                )
                if self.evidence_id == "representation-family-verified":
                    _constant(
                        output["primary_unit_id"],
                        case.estimator_input_receipt["primary_unit_id"],
                        label=f"D1 {case.case_id} primary-unit join",
                    )
                graph_families.add(output["field_graph_family"])
                for flag in (
                    "truth_read",
                    "anchor_read",
                    "charge_read",
                    "loop_read",
                    "integer_output_authorized",
                    "topology_claimed",
                    "subject_access_authorized",
                    "d0_d8_advanced",
                ):
                    _constant(
                        output[flag],
                        False,
                        label=f"D1 {case.case_id} {flag}",
                    )
            if graph_families != {
                "fixed-radius",
                "mutual-knn",
                "shared-neighbor",
            }:
                raise QualificationContractError(
                    "D1 case does not execute the exact three graph families"
                )
            if (
                self.evidence_id == "cartesian-fourier-family-verified"
                and case.generator_case_receipt.get(
                    "estimator_inputs_fingerprint_sha256"
                )
                != canonical_json_sha256(case.estimator_input_receipt)
            ):
                raise QualificationContractError(
                    "Cartesian D1 generator case differs from estimator input"
                )
            if (
                self.evidence_id == "representation-family-verified"
                and case.generator_case_receipt["spec_sha256"]
                != case.estimator_input_receipt["spec_sha256"]
            ):
                raise QualificationContractError(
                    "representation D1 generator case differs from estimator input"
                )

    @property
    def obligation_ids(self) -> tuple[str, ...]:
        common = (
            "estimator-executed",
            "generator-estimator-module-separation",
            "negative-control-executed",
            "positive-control-executed",
        )
        if self.evidence_id == "cartesian-fourier-family-verified":
            return (
                "cartesian-oracle-numeric-law",
                *common,
                "prerequisite-control-executed",
            )
        return (*common, "representation-oracle-numeric-law")

    @property
    def failed_obligation_ids(self) -> tuple[str, ...]:
        if all(
            metric.passed
            for case in self.cases
            for metric in case.numeric_metric_receipts
        ):
            return ()
        if self.evidence_id == "cartesian-fourier-family-verified":
            return ("cartesian-oracle-numeric-law",)
        return ("representation-oracle-numeric-law",)

    @property
    def observation_fingerprints_sha256(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    canonical_json_sha256(self.generator_family_receipt),
                    *(
                        fingerprint
                        for case in self.cases
                        for fingerprint in case.observation_fingerprints_sha256
                    ),
                }
            )
        )

    def validate_against_protocol(
        self,
        protocol: QualificationProtocol,
    ) -> None:
        """Bind every metric comparator and threshold to the frozen protocol."""

        if not isinstance(protocol, QualificationProtocol):
            raise TypeError("protocol must be a QualificationProtocol")
        family = (
            "cartesian"
            if self.evidence_id == "cartesian-fourier-family-verified"
            else "representation"
        )
        contracts = _D1_NUMERIC_METRIC_CONTRACTS[family]
        for case in self.cases:
            for metric in case.numeric_metric_receipts:
                comparator, threshold_field = contracts[metric.metric_id]
                expected_threshold = (
                    0.0
                    if threshold_field is None
                    else getattr(protocol.thresholds, threshold_field)
                )
                if (
                    metric.comparator != comparator
                    or type(metric.threshold) is not float
                    or metric.threshold != expected_threshold
                ):
                    raise QualificationContractError(
                        "D1 numeric metric comparator or threshold differs "
                        "from its frozen protocol field"
                    )

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "generator_family_receipt": self.generator_family_receipt,
            "cases": [item.to_dict() for item in self.cases],
        }

    @classmethod
    def from_cartesian(
        cls,
        *,
        phantom: object,
        estimates_by_case: Mapping[str, tuple[object, ...]],
        numeric_tolerance: float,
        direction_cosine_floor: float,
    ) -> D1FamilyExecutionReceipt:
        from spirallens.synthetic.cartesian_fourier_domain_phantom import (
            CartesianFourierDomainPhantom,
        )
        from spirallens.synthetic.cartesian_fourier_estimator import (
            CartesianFourierFieldEstimate,
        )

        if not isinstance(phantom, CartesianFourierDomainPhantom):
            raise TypeError("phantom must be a CartesianFourierDomainPhantom")
        cases: list[D1CaseExecutionReceipt] = []
        by_id = {item.case_id: item for item in phantom.cases}
        for case_id in _D1_EXPECTED_CASES["cartesian-fourier-family-verified"]:
            case = by_id[case_id]
            estimates = estimates_by_case.get(case_id)
            if not isinstance(estimates, tuple) or any(
                not isinstance(item, CartesianFourierFieldEstimate)
                for item in estimates
            ):
                raise TypeError(
                    "Cartesian D1 estimates must be typed field-estimate tuples"
                )
            if any(
                item.estimator_inputs is not case.estimator_inputs
                and item.estimator_inputs.to_dict() != case.estimator_inputs.to_dict()
                for item in estimates
            ):
                raise QualificationContractError(
                    "Cartesian D1 estimate does not consume its generator case"
                )
            cases.append(
                D1CaseExecutionReceipt(
                    case_id=case_id,
                    generator_case_receipt=case.to_dict(),
                    estimator_input_receipt=case.estimator_inputs.to_dict(),
                    estimator_output_receipts=tuple(
                        item.to_dict() for item in estimates
                    ),
                    numeric_metric_receipts=tuple(
                        metric
                        for estimate in estimates
                        for metric in _cartesian_d1_numeric_metrics(
                            case=case,
                            estimate=estimate,
                            numeric_tolerance=numeric_tolerance,
                            direction_cosine_floor=(direction_cosine_floor),
                        )
                    ),
                )
            )
        return cls(
            evidence_id="cartesian-fourier-family-verified",
            generator_family_receipt=phantom.to_dict(),
            cases=tuple(cases),
        )

    @classmethod
    def from_representation(
        cls,
        *,
        phantom: object,
        executions: Mapping[str, tuple[object, tuple[object, ...]]],
        numeric_tolerance: float,
        phase_coherence_floor: float,
    ) -> D1FamilyExecutionReceipt:
        from spirallens.synthetic.representation_estimator import (
            RepresentationEstimatorInputs,
            RepresentationFieldEstimate,
        )
        from spirallens.synthetic.representation_phantom import (
            RepresentationPhantom,
        )

        if not isinstance(phantom, RepresentationPhantom):
            raise TypeError("phantom must be a RepresentationPhantom")
        by_id = {item.case_id: item for item in phantom.cases}
        cases: list[D1CaseExecutionReceipt] = []
        for case_id in _D1_EXPECTED_CASES["representation-family-verified"]:
            try:
                inputs, estimates = executions[case_id]
            except KeyError as error:
                raise QualificationContractError(
                    "representation D1 execution lacks a required case"
                ) from error
            if not isinstance(inputs, RepresentationEstimatorInputs) or any(
                not isinstance(item, RepresentationFieldEstimate) for item in estimates
            ):
                raise TypeError(
                    "representation D1 requires typed inputs and field estimates"
                )
            if any(
                item.estimator_inputs is not inputs
                and item.estimator_inputs.to_dict() != inputs.to_dict()
                for item in estimates
            ):
                raise QualificationContractError(
                    "representation D1 estimate does not consume its typed input"
                )
            cases.append(
                D1CaseExecutionReceipt(
                    case_id=case_id,
                    generator_case_receipt=by_id[case_id].to_dict(),
                    estimator_input_receipt=inputs.to_dict(),
                    estimator_output_receipts=tuple(
                        item.to_dict() for item in estimates
                    ),
                    numeric_metric_receipts=tuple(
                        metric
                        for estimate in estimates
                        for metric in _representation_d1_numeric_metrics(
                            phantom=phantom,
                            case=by_id[case_id],
                            estimate=estimate,
                            numeric_tolerance=numeric_tolerance,
                            phase_coherence_floor=phase_coherence_floor,
                        )
                    ),
                )
            )
        return cls(
            evidence_id="representation-family-verified",
            generator_family_receipt=phantom.to_dict(),
            cases=tuple(cases),
        )

    @classmethod
    def from_dict(cls, value: object) -> D1FamilyExecutionReceipt:
        item = _mapping(value, label="D1 family execution receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="D1 family execution receipt")
        cases = item["cases"]
        if not isinstance(cases, list):
            raise QualificationContractError("D1 cases must be a JSON array")
        return cls(
            schema_version=item["schema_version"],  # type: ignore[arg-type]
            evidence_id=require_slug(item["evidence_id"], label="D1 evidence_id"),
            generator_family_receipt=_mapping(
                item["generator_family_receipt"],
                label="D1 generator_family_receipt",
            ),
            cases=tuple(D1CaseExecutionReceipt.from_dict(entry) for entry in cases),
        )


_D3_OBLIGATIONS = {
    "cartesian-gauge-pipeline-rerun-verified": (
        "ambient-signed-permutation",
        "loop-reversal",
        "pipeline-rerun",
        "reference-reflection",
        "reference-rotation",
    ),
    "representation-gauge-pipeline-rerun-verified": (
        "ambient-signed-permutation",
        "local-frame-gauge",
        "loop-reversal",
        "nonorientable-control",
        "pipeline-rerun",
        "reference-orientation",
        "spin-two-double-angle",
    ),
}

_D3_CARTESIAN_LAWS = {
    "ambient-signed-permutation": "ambient_signed_permutation",
    "loop-reversal": "loop_reversal",
    "reference-reflection": "reference_reflection",
    "reference-rotation": "reference_rotation",
}

_D3_REPRESENTATION_LAWS = {
    "ambient-signed-permutation": "ambient_signed_permutation",
    "local-frame-gauge": "local_frame_gauge",
    "loop-reversal": "loop_reversal",
    "nonorientable-control": "nonorientable_control",
    "reference-orientation": "reference_orientation",
    "spin-two-double-angle": "spin_two_double_angle",
}


def _validate_representation_metamorph_receipt(
    value: object,
    *,
    obligation_id: str,
) -> dict[str, object]:
    from .metamorphic import MetamorphCheck, MetamorphLaw

    document = _mapping(value, label=f"D3 {obligation_id} metamorph receipt")
    runtime_keys = frozenset(
        {
            "schema_version",
            *_BOUNDARY_KEYS,
            "check_id",
            "law",
            "state",
            "base_sha256",
            "transformed_sha256",
            "transformation_sha256",
            "nonidentity_verified",
            "inverse_verified",
            "composition_verified",
            "observed_error",
            "tolerance",
            "reason_codes",
            "sampled_continuous_observable_only",
            "integer_output_present",
            "oracle_read",
        }
    )
    _exact_keys(document, runtime_keys, label=f"D3 {obligation_id} receipt")
    _constant(
        document["schema_version"],
        "spirallens.metamorph-check.v0.1",
        label=f"D3 {obligation_id} schema_version",
    )
    for name, expected in _BOUNDARY.items():
        _constant(document[name], expected, label=f"D3 {obligation_id} {name}")
    for name, expected in (
        ("sampled_continuous_observable_only", True),
        ("integer_output_present", False),
        ("oracle_read", False),
    ):
        _constant(document[name], expected, label=f"D3 {obligation_id} {name}")
    try:
        law = MetamorphLaw(document["law"])
        state = QualificationState(document["state"])
    except (TypeError, ValueError) as error:
        raise QualificationContractError(
            f"D3 {obligation_id} carries an unsupported enum"
        ) from error
    reasons = _canonical_reasons(
        document["reason_codes"],
        label=f"D3 {obligation_id} reason_codes",
    )
    if law.value != _D3_REPRESENTATION_LAWS[obligation_id]:
        raise QualificationContractError(
            f"D3 {obligation_id} receipt carries a different transformation law"
        )
    check = MetamorphCheck(
        check_id=require_slug(
            document["check_id"], label=f"D3 {obligation_id} check_id"
        ),
        law=law,
        state=state,
        base_sha256=require_sha256(
            document["base_sha256"], label=f"D3 {obligation_id} base_sha256"
        ),
        transformed_sha256=require_sha256(
            document["transformed_sha256"],
            label=f"D3 {obligation_id} transformed_sha256",
        ),
        transformation_sha256=require_sha256(
            document["transformation_sha256"],
            label=f"D3 {obligation_id} transformation_sha256",
        ),
        nonidentity_verified=document["nonidentity_verified"],  # type: ignore[arg-type]
        inverse_verified=document["inverse_verified"],  # type: ignore[arg-type]
        composition_verified=document["composition_verified"],  # type: ignore[arg-type]
        observed_error=require_finite_real(
            document["observed_error"],
            label=f"D3 {obligation_id} observed_error",
            minimum=0.0,
        ),
        tolerance=require_finite_real(
            document["tolerance"],
            label=f"D3 {obligation_id} tolerance",
            minimum=0.0,
        ),
        reason_codes=reasons,
    )
    if obligation_id == "nonorientable-control":
        if (
            check.law is not MetamorphLaw.NONORIENTABLE_CONTROL
            or check.state is not QualificationState.INSUFFICIENT
            or check.reason_codes != ("orientation-reversing-cycle",)
        ):
            raise QualificationContractError(
                "D3 nonorientable control must be the exact triggered "
                "orientation-reversing insufficient check"
            )
    elif check.state is not QualificationState.PASS:
        raise QualificationContractError(
            f"D3 {obligation_id} metamorphic check must pass"
        )
    return document


def _validate_cartesian_pipeline_check(
    value: object,
    *,
    obligation_id: str,
) -> dict[str, object]:
    document = _mapping(value, label=f"Cartesian D3 {obligation_id} receipt")
    required = {
        "receipt_version",
        *_BOUNDARY_KEYS,
        "check_id",
        "law",
        "state",
        "transformation_sha256",
        "base",
        "transformed",
        "inverse",
        "composition_sequential",
        "composition_direct",
        "expected_loop_orientation_sign",
        "maximum_distance_error",
        "maximum_field_law_error",
        "maximum_loop_law_error",
        "tolerance",
        "nonidentity_verified",
        "inverse_verified",
        "composition_verified",
        "all_graph_adjacencies_verified",
        "all_graph_edge_distances_bit_identical",
        "claim_relevant_field_law_verified",
        "continuous_loop_law_verified",
        "pipeline_rerun_verified",
        "reason_codes",
        "oracle_object_read",
        "case_id_read",
        "anchor_read",
        "charge_read",
        "subject_value_read",
        "sampled_continuous_observable_only",
        "integer_output_present",
        "topology_claimed",
        "d3_gate_advanced",
    }
    _exact_keys(document, required, label=f"Cartesian D3 {obligation_id} receipt")
    _constant(
        document["receipt_version"],
        "spirallens.cartesian-pipeline-metamorph-check.v0.1",
        label=f"Cartesian D3 {obligation_id} receipt_version",
    )
    for name, expected in _BOUNDARY.items():
        _constant(
            document[name],
            expected,
            label=f"Cartesian D3 {obligation_id} {name}",
        )
    _constant(
        document["state"],
        QualificationState.PASS.value,
        label=f"Cartesian D3 {obligation_id} state",
    )
    _constant(
        document["law"],
        _D3_CARTESIAN_LAWS[obligation_id],
        label=f"Cartesian D3 {obligation_id} law",
    )
    require_slug(
        document["check_id"],
        label=f"Cartesian D3 {obligation_id} check_id",
    )
    require_sha256(
        document["transformation_sha256"],
        label=f"Cartesian D3 {obligation_id} transformation_sha256",
    )
    _constant(
        document["expected_loop_orientation_sign"],
        (-1 if obligation_id in {"loop-reversal", "reference-reflection"} else 1),
        label=f"Cartesian D3 {obligation_id} loop orientation sign",
    )
    for name in (
        "nonidentity_verified",
        "inverse_verified",
        "composition_verified",
        "all_graph_adjacencies_verified",
        "all_graph_edge_distances_bit_identical",
        "claim_relevant_field_law_verified",
        "continuous_loop_law_verified",
        "pipeline_rerun_verified",
    ):
        _constant(
            document[name],
            True,
            label=f"Cartesian D3 {obligation_id} {name}",
        )
    for name, expected in (
        ("oracle_object_read", False),
        ("case_id_read", False),
        ("anchor_read", False),
        ("charge_read", False),
        ("subject_value_read", False),
        ("sampled_continuous_observable_only", True),
        ("integer_output_present", False),
        ("topology_claimed", False),
        ("d3_gate_advanced", False),
    ):
        _constant(
            document[name],
            expected,
            label=f"Cartesian D3 {obligation_id} {name}",
        )
    tolerance = require_finite_real(
        document["tolerance"],
        label=f"Cartesian D3 {obligation_id} tolerance",
        minimum=0.0,
    )
    for name in (
        "maximum_distance_error",
        "maximum_field_law_error",
        "maximum_loop_law_error",
    ):
        observed = require_finite_real(
            document[name],
            label=f"Cartesian D3 {obligation_id} {name}",
            minimum=0.0,
        )
        if observed > tolerance:
            raise QualificationContractError(
                f"Cartesian D3 {obligation_id} exceeds its tolerance"
            )
    if document["reason_codes"] != ["pipeline_transformation_law_verified"]:
        raise QualificationContractError(
            f"Cartesian D3 {obligation_id} reason is not mechanically passing"
        )
    snapshots: list[dict[str, object]] = []
    snapshot_keys = {
        "estimator_input_fingerprint_sha256",
        "graph_input_fingerprint_sha256",
        "crossed_execution_fingerprint_sha256",
        "field_graph_fingerprint_sha256",
        "cycle_graph_fingerprint_sha256",
        "field_estimate_fingerprint_sha256",
        "blind_loop_input_fingerprint_sha256",
        "sealed_loop_prediction_fingerprint_sha256",
    }
    for name in (
        "base",
        "transformed",
        "inverse",
        "composition_sequential",
        "composition_direct",
    ):
        snapshot = _mapping(
            document[name],
            label=f"Cartesian D3 {obligation_id} {name}",
        )
        _exact_keys(
            snapshot,
            snapshot_keys,
            label=f"Cartesian D3 {obligation_id} {name}",
        )
        for key in snapshot_keys:
            require_sha256(
                snapshot[key],
                label=f"Cartesian D3 {obligation_id} {name}.{key}",
            )
        snapshots.append(snapshot)
    if snapshots[0] == snapshots[1]:
        raise QualificationContractError(
            f"Cartesian D3 {obligation_id} base/transformed rerun is identity"
        )
    return document


def _validate_representation_blind_loop(
    value: object,
    *,
    label: str,
) -> tuple[dict[str, object], str]:
    document = _mapping(value, label=label)
    _exact_keys(
        document,
        {
            "receipt_version",
            *_BOUNDARY_KEYS,
            "primary_unit_sha256",
            "estimator_input_fingerprint_sha256",
            "field_graph_fingerprint_sha256",
            "field_estimate_fingerprint_sha256",
            "cycle_graph_fingerprint_sha256",
            "cycle_binding_fingerprint_sha256",
            "representative_content_sha256",
            "input_id",
            "input_scope",
            "ordered_loop_rows",
            "section_values",
            "boundary_amplitude",
            "boundary_identifiability_score",
            "boundary_coherence",
            "same_object_amplitude_and_direction",
            "expected_outcome_present",
            "integer_output_present",
        },
        label=label,
    )
    _constant(
        document["receipt_version"],
        "spirallens.blind-loop-input.v0.3",
        label=f"{label} receipt_version",
    )
    for name, expected in _BOUNDARY.items():
        _constant(document[name], expected, label=f"{label} {name}")
    for name in (
        "primary_unit_sha256",
        "estimator_input_fingerprint_sha256",
        "field_graph_fingerprint_sha256",
        "field_estimate_fingerprint_sha256",
        "cycle_graph_fingerprint_sha256",
        "cycle_binding_fingerprint_sha256",
        "representative_content_sha256",
    ):
        require_sha256(document[name], label=f"{label} {name}")
    require_slug(document["input_id"], label=f"{label} input_id")
    for name, expected in (
        (
            "input_scope",
            "one-ordered-representative-loop-and-boundary-observables",
        ),
        ("same_object_amplitude_and_direction", True),
        ("expected_outcome_present", False),
        ("integer_output_present", False),
    ):
        _constant(document[name], expected, label=f"{label} {name}")
    rows = _fingerprint_shape(
        document["ordered_loop_rows"],
        label=f"{label} ordered_loop_rows",
        ndim=1,
    )
    _constant(
        rows["dtype"],
        "<i8",
        label=f"{label} ordered_loop_rows.dtype",
    )
    row_shape = rows["shape"]
    assert isinstance(row_shape, list)
    if row_shape[0] < 3:
        raise QualificationContractError(
            f"{label} must contain at least three loop rows"
        )
    for name, ndim, width in (
        ("section_values", 2, 2),
        ("boundary_amplitude", 1, None),
        ("boundary_identifiability_score", 1, None),
        ("boundary_coherence", 1, None),
    ):
        fingerprint = _fingerprint_shape(
            document[name],
            label=f"{label} {name}",
            ndim=ndim,
            width=width,
        )
        _constant(
            fingerprint["dtype"],
            "<f8",
            label=f"{label} {name}.dtype",
        )
        shape = fingerprint["shape"]
        assert isinstance(shape, list)
        if shape[0] != row_shape[0]:
            raise QualificationContractError(
                f"{label} observable rows differ from ordered_loop_rows"
            )
    return document, canonical_json_sha256(document)


def _validate_representation_sealed_prediction(
    value: object,
    *,
    blind_input: Mapping[str, object],
    blind_input_sha256: str,
    label: str,
) -> tuple[dict[str, object], dict[str, object], float]:
    wrapper = _mapping(value, label=label)
    _exact_keys(
        wrapper,
        {"prediction_sha256", "receipt"},
        label=label,
    )
    prediction_sha256 = require_sha256(
        wrapper["prediction_sha256"],
        label=f"{label} prediction_sha256",
    )
    document = _mapping(wrapper["receipt"], label=f"{label} receipt")
    _exact_keys(
        document,
        {
            "receipt_version",
            *_BOUNDARY_KEYS,
            "blind_input_fingerprint_sha256",
            "primary_unit_sha256",
            "policy_fingerprint_sha256",
            "estimator_id",
            "observed_attempt_status",
            "prediction_class",
            "reason_codes",
            "signed_total_cycles",
            "max_abs_edge_increment_radians",
            "nearest_integer_residual_cycles",
            "comparison_tolerance_cycles",
            "oracle_read",
            "sealed_before_oracle_score",
            "sampled_continuous_observable_only",
            "integer_output_present",
        },
        label=f"{label} receipt",
    )
    _constant(
        document["receipt_version"],
        "spirallens.sealed-loop-prediction.v0.1",
        label=f"{label} receipt_version",
    )
    for name, expected in _BOUNDARY.items():
        _constant(document[name], expected, label=f"{label} {name}")
    for name, expected in (
        ("estimator_id", "truth-blind-sampled-phase-total-v0.2"),
        ("observed_attempt_status", AttemptStatus.EVALUABLE.value),
        ("prediction_class", LoopPredictionClass.NONZERO.value),
        ("oracle_read", False),
        ("sealed_before_oracle_score", True),
        ("sampled_continuous_observable_only", True),
        ("integer_output_present", False),
    ):
        _constant(document[name], expected, label=f"{label} {name}")
    if _canonical_reasons(
        document["reason_codes"],
        label=f"{label} reason_codes",
    ):
        raise QualificationContractError(
            f"{label} evaluable prediction cannot carry reason codes"
        )
    _constant(
        document["blind_input_fingerprint_sha256"],
        blind_input_sha256,
        label=f"{label} blind input binding",
    )
    _constant(
        document["primary_unit_sha256"],
        blind_input["primary_unit_sha256"],
        label=f"{label} primary unit binding",
    )
    require_sha256(
        document["policy_fingerprint_sha256"],
        label=f"{label} policy_fingerprint_sha256",
    )
    total = require_finite_real(
        document["signed_total_cycles"],
        label=f"{label} signed_total_cycles",
    )
    if total == 0.0:
        raise QualificationContractError(
            f"{label} positive representation prediction must be nonzero"
        )
    maximum = require_finite_real(
        document["max_abs_edge_increment_radians"],
        label=f"{label} max_abs_edge_increment_radians",
        minimum=0.0,
        maximum=math.pi,
        maximum_inclusive=False,
    )
    residual = require_finite_real(
        document["nearest_integer_residual_cycles"],
        label=f"{label} nearest_integer_residual_cycles",
        minimum=0.0,
        maximum=0.5,
    )
    comparison_tolerance = require_finite_real(
        document["comparison_tolerance_cycles"],
        label=f"{label} comparison_tolerance_cycles",
        minimum=0.0,
        minimum_inclusive=False,
        maximum=0.5,
        maximum_inclusive=False,
    )
    if residual > comparison_tolerance or maximum <= 0.0:
        raise QualificationContractError(
            f"{label} prediction diagnostics do not support its total"
        )
    if canonical_json_sha256(document) != prediction_sha256:
        raise QualificationContractError(
            f"{label} prediction_sha256 does not bind its full receipt"
        )
    return wrapper, document, total


def _validate_representation_loop_law(
    value: object,
    *,
    label: str,
    tolerance: float,
    expected_receipt_version: str,
    expected_law: str | None = None,
) -> dict[str, object]:
    document = _mapping(value, label=label)
    _exact_keys(
        document,
        {
            "receipt_version",
            "field_graph_id",
            "cycle_graph_id",
            "law",
            "transformation_sha256",
            "orientation_determinant",
            "base_blind_input_sha256",
            "transformed_blind_input_sha256",
            "base_blind_input",
            "transformed_blind_input",
            "base_prediction",
            "transformed_prediction",
            "base_signed_total_cycles",
            "expected_transformed_signed_total_cycles",
            "transformed_signed_total_cycles",
            "signed_total_error_cycles",
            "tolerance",
            "verified",
            "selection_seed_accessed",
            "oracle_read",
            "sampled_continuous_observable_only",
            "integer_output_present",
            "topology_claimed",
        },
        label=label,
    )
    _constant(
        document["receipt_version"],
        expected_receipt_version,
        label=f"{label} receipt_version",
    )
    field_graph_id = require_slug(
        document["field_graph_id"],
        label=f"{label} field_graph_id",
    )
    cycle_graph_id = require_slug(
        document["cycle_graph_id"],
        label=f"{label} cycle_graph_id",
    )
    law = require_slug(document["law"], label=f"{label} law")
    if expected_law is not None and law != expected_law:
        raise QualificationContractError(f"{label} carries a different signed loop law")
    allowed_laws = {
        "ambient_o2_alignment",
        "reference_rotation",
        "reference_reflection",
        "loop_reversal",
    }
    if law not in allowed_laws:
        raise QualificationContractError(
            f"{label} carries an unsupported signed loop law"
        )
    require_sha256(
        document["transformation_sha256"],
        label=f"{label} transformation_sha256",
    )
    determinant = require_finite_real(
        document["orientation_determinant"],
        label=f"{label} orientation_determinant",
        minimum=-1.0,
        maximum=1.0,
    )
    if abs(abs(determinant) - 1.0) > tolerance:
        raise QualificationContractError(
            f"{label} orientation determinant is not an O(2) sign"
        )
    if (
        law == "reference_rotation"
        and determinant <= 0.0
        or law in {"reference_reflection", "loop_reversal"}
        and determinant >= 0.0
    ):
        raise QualificationContractError(
            f"{label} determinant has the wrong sign for its law"
        )
    base_blind, base_blind_sha256 = _validate_representation_blind_loop(
        document["base_blind_input"],
        label=f"{label} base_blind_input",
    )
    transformed_blind, transformed_blind_sha256 = _validate_representation_blind_loop(
        document["transformed_blind_input"],
        label=f"{label} transformed_blind_input",
    )
    _constant(
        document["base_blind_input_sha256"],
        base_blind_sha256,
        label=f"{label} base_blind_input_sha256",
    )
    _constant(
        document["transformed_blind_input_sha256"],
        transformed_blind_sha256,
        label=f"{label} transformed_blind_input_sha256",
    )
    if base_blind_sha256 == transformed_blind_sha256:
        raise QualificationContractError(
            f"{label} transformed blind loop must be nonidentity"
        )
    _base_wrapper, base_prediction, base_total = (
        _validate_representation_sealed_prediction(
            document["base_prediction"],
            blind_input=base_blind,
            blind_input_sha256=base_blind_sha256,
            label=f"{label} base_prediction",
        )
    )
    _transformed_wrapper, transformed_prediction, transformed_total = (
        _validate_representation_sealed_prediction(
            document["transformed_prediction"],
            blind_input=transformed_blind,
            blind_input_sha256=transformed_blind_sha256,
            label=f"{label} transformed_prediction",
        )
    )
    if (
        base_prediction["policy_fingerprint_sha256"]
        != transformed_prediction["policy_fingerprint_sha256"]
    ):
        raise QualificationContractError(
            f"{label} predictions must use the same loop policy"
        )
    _constant(
        document["base_signed_total_cycles"],
        base_total,
        label=f"{label} base_signed_total_cycles",
    )
    _constant(
        document["transformed_signed_total_cycles"],
        transformed_total,
        label=f"{label} transformed_signed_total_cycles",
    )
    expected_total = determinant * base_total
    _constant(
        document["expected_transformed_signed_total_cycles"],
        expected_total,
        label=f"{label} expected transformed total",
    )
    error = abs(transformed_total - expected_total)
    _constant(
        document["signed_total_error_cycles"],
        error,
        label=f"{label} signed_total_error_cycles",
    )
    receipt_tolerance = require_finite_real(
        document["tolerance"],
        label=f"{label} tolerance",
        minimum=0.0,
        minimum_inclusive=False,
    )
    _constant(
        receipt_tolerance,
        tolerance,
        label=f"{label} frozen tolerance",
    )
    if error > tolerance:
        raise QualificationContractError(
            f"{label} violates its determinant-aware signed total law"
        )
    for name, expected in (
        ("verified", True),
        ("selection_seed_accessed", False),
        ("oracle_read", False),
        ("sampled_continuous_observable_only", True),
        ("integer_output_present", False),
        ("topology_claimed", False),
    ):
        _constant(document[name], expected, label=f"{label} {name}")
    base_rows = _mapping(
        base_blind["ordered_loop_rows"],
        label=f"{label} base rows",
    )
    transformed_rows = _mapping(
        transformed_blind["ordered_loop_rows"],
        label=f"{label} transformed rows",
    )
    if law == "loop_reversal":
        if base_rows == transformed_rows:
            raise QualificationContractError(
                f"{label} loop reversal did not change ordered rows"
            )
    elif base_rows != transformed_rows:
        raise QualificationContractError(
            f"{label} reference or ambient law changed matched loop rows"
        )
    if law == "ambient_o2_alignment":
        if (
            base_blind["field_estimate_fingerprint_sha256"]
            == transformed_blind["field_estimate_fingerprint_sha256"]
            or base_blind["estimator_input_fingerprint_sha256"]
            == transformed_blind["estimator_input_fingerprint_sha256"]
        ):
            raise QualificationContractError(
                f"{label} ambient law did not rerun transformed input and field"
            )
    elif (
        base_blind["estimator_input_fingerprint_sha256"]
        != transformed_blind["estimator_input_fingerprint_sha256"]
    ):
        raise QualificationContractError(
            f"{label} loop-only variant changed estimator input"
        )
    require_slug(field_graph_id, label=f"{label} field graph")
    require_slug(cycle_graph_id, label=f"{label} cycle graph")
    return document


def _validate_representation_pipeline_check(
    value: object,
    *,
    index: int,
    tolerance: float,
) -> dict[str, object]:
    label = f"representation D3 pipeline check[{index}]"
    document = _mapping(value, label=label)
    _exact_keys(
        document,
        {
            "field_graph_id",
            "base_estimator_fingerprint_sha256",
            "transformed_estimator_fingerprint_sha256",
            "adjacency_equal",
            "edge_distances_bit_identical",
            "support_equal",
            "alignment_matrix",
            "alignment_sha256",
            "alignment_determinant",
            "errors",
            "crossed_loop_checks",
            "verified",
        },
        label=label,
    )
    field_graph_id = require_slug(
        document["field_graph_id"],
        label=f"{label} field_graph_id",
    )
    base = require_sha256(
        document["base_estimator_fingerprint_sha256"],
        label=f"{label} base",
    )
    transformed = require_sha256(
        document["transformed_estimator_fingerprint_sha256"],
        label=f"{label} transformed",
    )
    if base == transformed:
        raise QualificationContractError(
            "representation D3 pipeline rerun must be nonidentity"
        )
    for name in (
        "adjacency_equal",
        "edge_distances_bit_identical",
        "support_equal",
        "verified",
    ):
        _exact_bool(
            document[name],
            expected=True,
            label=f"{label} {name}",
        )
    matrix = document["alignment_matrix"]
    if (
        not isinstance(matrix, list)
        or len(matrix) != 2
        or any(not isinstance(row, list) or len(row) != 2 for row in matrix)
    ):
        raise QualificationContractError(
            f"{label} alignment_matrix must be a 2 by 2 JSON array"
        )
    normalized = tuple(
        tuple(
            require_finite_real(
                value,
                label=f"{label} alignment_matrix[{row}][{column}]",
            )
            for column, value in enumerate(values)
        )
        for row, values in enumerate(matrix)
    )
    a, b = normalized[0]
    c, d = normalized[1]
    determinant = a * d - b * c
    declared_determinant = require_finite_real(
        document["alignment_determinant"],
        label=f"{label} alignment_determinant",
        minimum=-1.0,
        maximum=1.0,
    )
    if (
        abs(determinant - declared_determinant) > tolerance
        or abs(abs(determinant) - 1.0) > tolerance
        or max(
            abs(a * a + c * c - 1.0),
            abs(b * b + d * d - 1.0),
            abs(a * b + c * d),
        )
        > tolerance
    ):
        raise QualificationContractError(
            f"{label} alignment is not the declared O(2) transform"
        )
    _constant(
        document["alignment_sha256"],
        canonical_json_sha256({"alignment_matrix": matrix}),
        label=f"{label} alignment_sha256",
    )
    errors = _mapping(document["errors"], label=f"{label} errors")
    _exact_keys(
        errors,
        {
            "ambient_equivariance",
            "section_gauge_alignment",
            "amplitude",
            "identifiability",
            "coherence",
            "alignment_orthogonality",
            "alignment_determinant_unit",
        },
        label=f"{label} errors",
    )
    for name, error_value in errors.items():
        observed = require_finite_real(
            error_value,
            label=f"{label} {name}",
            minimum=0.0,
        )
        if observed > tolerance:
            raise QualificationContractError(
                "representation D3 pipeline check exceeds its exact tolerance"
            )
    raw_loops = document["crossed_loop_checks"]
    if not isinstance(raw_loops, list) or len(raw_loops) != 3:
        raise QualificationContractError(
            f"{label} requires all three matched B graph loop checks"
        )
    loops = tuple(
        _validate_representation_loop_law(
            item,
            label=f"{label} crossed_loop_checks[{loop_index}]",
            tolerance=tolerance,
            expected_receipt_version=(
                "spirallens.representation-crossed-loop-law.v0.1"
            ),
            expected_law="ambient_o2_alignment",
        )
        for loop_index, item in enumerate(raw_loops)
    )
    cycle_ids = tuple(item["cycle_graph_id"] for item in loops)
    if len(set(cycle_ids)) != 3:
        raise QualificationContractError(
            f"{label} crossed loops must cover three distinct B graphs"
        )
    for item in loops:
        _constant(
            item["field_graph_id"],
            field_graph_id,
            label=f"{label} crossed field graph binding",
        )
        _constant(
            item["orientation_determinant"],
            declared_determinant,
            label=f"{label} determinant-aware loop binding",
        )
        base_blind = _mapping(
            item["base_blind_input"],
            label=f"{label} base blind",
        )
        transformed_blind = _mapping(
            item["transformed_blind_input"],
            label=f"{label} transformed blind",
        )
        _constant(
            base_blind["field_estimate_fingerprint_sha256"],
            base,
            label=f"{label} base field estimate binding",
        )
        _constant(
            transformed_blind["field_estimate_fingerprint_sha256"],
            transformed,
            label=f"{label} transformed field estimate binding",
        )
    return document


@dataclass(frozen=True, slots=True)
class D3PipelineExecutionReceipt:
    """Full actual-rerun D3 aggregate with mechanically derived obligations."""

    evidence_id: str
    aggregate_runtime_receipt: dict[str, object]
    obligation_receipts: tuple[tuple[str, dict[str, object]], ...]
    base_estimator_fingerprint_sha256: str
    transformed_estimator_fingerprint_sha256: str
    pipeline_rerun_count: int
    schema_version: str = D3_PIPELINE_EXECUTION_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "evidence_id",
            "aggregate_runtime_receipt",
            "obligation_receipts",
            "base_estimator_fingerprint_sha256",
            "transformed_estimator_fingerprint_sha256",
            "pipeline_rerun_count",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            D3_PIPELINE_EXECUTION_SCHEMA_VERSION,
            label="D3 pipeline execution schema_version",
        )
        if self.evidence_id not in _D3_OBLIGATIONS:
            raise QualificationContractError(
                "D3 pipeline evidence_id is outside the closed universe"
            )
        ids = tuple(item[0] for item in self.obligation_receipts)
        expected = tuple(
            item
            for item in _D3_OBLIGATIONS[self.evidence_id]
            if item != "pipeline-rerun"
        )
        if ids != expected:
            raise QualificationContractError(
                "D3 obligation receipts differ from the closed law universe"
            )
        validated_documents: list[dict[str, object]] = []
        for obligation_id, document in self.obligation_receipts:
            require_slug(obligation_id, label="D3 obligation_id")
            if not isinstance(document, dict):
                raise TypeError("D3 obligation receipt must be a dict")
            validated_documents.append(
                _validate_cartesian_pipeline_check(
                    document,
                    obligation_id=obligation_id,
                )
                if self.evidence_id == "cartesian-gauge-pipeline-rerun-verified"
                else _validate_representation_metamorph_receipt(
                    document,
                    obligation_id=obligation_id,
                )
            )
        if len({canonical_json_sha256(item) for item in validated_documents}) != len(
            validated_documents
        ):
            raise QualificationContractError(
                "D3 obligation receipts must be distinct actual checks"
            )
        require_sha256(
            self.base_estimator_fingerprint_sha256,
            label="D3 base_estimator_fingerprint_sha256",
        )
        require_sha256(
            self.transformed_estimator_fingerprint_sha256,
            label="D3 transformed_estimator_fingerprint_sha256",
        )
        if (
            self.base_estimator_fingerprint_sha256
            == self.transformed_estimator_fingerprint_sha256
        ):
            raise QualificationContractError("D3 actual rerun must be nonidentity")
        require_plain_int(
            self.pipeline_rerun_count,
            label="D3 pipeline_rerun_count",
            minimum=2,
        )
        if self.evidence_id == "cartesian-gauge-pipeline-rerun-verified":
            aggregate = self.aggregate_runtime_receipt
            _exact_keys(
                aggregate,
                {
                    "receipt_version",
                    *_BOUNDARY_KEYS,
                    "development_seed",
                    "development_seed_only",
                    "selection_seed_accessed",
                    "generator_spec_receipt_sha256",
                    "source_estimator_input_fingerprint_sha256",
                    "estimator_input_selection_rule",
                    "checks",
                    "state",
                    "pipeline_rerun_verified",
                    "private_content_pseudonym_helper_imported",
                    "content_pseudonym_receipt_algorithm_reimplemented",
                    "content_pseudonym_dependency",
                    "future_gate_evidence_adapter_required",
                    "qualification_contract_module_imported",
                    "oracle_object_read",
                    "case_id_read",
                    "anchor_read",
                    "charge_read",
                    "subject_value_read",
                    "sampled_continuous_observable_only",
                    "integer_output_present",
                    "synthetic_qualification_advanced",
                    "d3_gate_advanced",
                },
                label="Cartesian D3 aggregate",
            )
            if (
                aggregate.get("receipt_version")
                != "spirallens.cartesian-pipeline-metamorphic-receipt.v0.1"
                or aggregate.get("state") != QualificationState.PASS.value
                or aggregate.get("pipeline_rerun_verified") is not True
                or not isinstance(aggregate.get("checks"), list)
            ):
                raise QualificationContractError(
                    "Cartesian D3 aggregate is not a passing actual-rerun receipt"
                )
            for name, expected_value in _BOUNDARY.items():
                _constant(
                    aggregate[name],
                    expected_value,
                    label=f"Cartesian D3 aggregate {name}",
                )
            for name, expected_value in (
                ("development_seed", 314159),
                ("development_seed_only", True),
                ("selection_seed_accessed", False),
                (
                    "estimator_input_selection_rule",
                    "canonical-generator-observable-position-zero",
                ),
                ("private_content_pseudonym_helper_imported", False),
                (
                    "content_pseudonym_receipt_algorithm_reimplemented",
                    True,
                ),
                (
                    "content_pseudonym_dependency",
                    "cartesian-fourier-label-free-content-v0.1",
                ),
                ("future_gate_evidence_adapter_required", True),
                ("qualification_contract_module_imported", False),
                ("oracle_object_read", False),
                ("case_id_read", False),
                ("anchor_read", False),
                ("charge_read", False),
                ("subject_value_read", False),
                ("sampled_continuous_observable_only", True),
                ("integer_output_present", False),
                ("synthetic_qualification_advanced", False),
                ("d3_gate_advanced", False),
            ):
                _constant(
                    aggregate[name],
                    expected_value,
                    label=f"Cartesian D3 aggregate {name}",
                )
            require_sha256(
                aggregate["generator_spec_receipt_sha256"],
                label="Cartesian D3 aggregate generator_spec_receipt_sha256",
            )
            source_estimator_input_sha256 = require_sha256(
                aggregate["source_estimator_input_fingerprint_sha256"],
                label=(
                    "Cartesian D3 aggregate source_estimator_input_fingerprint_sha256"
                ),
            )
            aggregate_checks = aggregate["checks"]
            assert isinstance(aggregate_checks, list)
            by_obligation = dict(self.obligation_receipts)
            expected_aggregate_checks = [
                by_obligation["ambient-signed-permutation"],
                by_obligation["reference-rotation"],
                by_obligation["reference-reflection"],
                by_obligation["loop-reversal"],
            ]
            if aggregate_checks != expected_aggregate_checks:
                raise QualificationContractError(
                    "Cartesian D3 aggregate checks differ from the exact "
                    "closed pipeline-check sequence"
                )
            base_snapshots = [
                _mapping(
                    document["base"],
                    label="Cartesian D3 aggregate base snapshot",
                )
                for document in expected_aggregate_checks
            ]
            if any(
                snapshot["estimator_input_fingerprint_sha256"]
                != source_estimator_input_sha256
                for snapshot in base_snapshots
            ):
                raise QualificationContractError(
                    "Cartesian D3 aggregate source estimator input differs "
                    "from its actual base pipeline snapshots"
                )
            ambient = expected_aggregate_checks[0]
            ambient_base = _mapping(
                ambient["base"],
                label="Cartesian D3 ambient base snapshot",
            )
            ambient_transformed = _mapping(
                ambient["transformed"],
                label="Cartesian D3 ambient transformed snapshot",
            )
            if (
                self.base_estimator_fingerprint_sha256
                != ambient_base["field_estimate_fingerprint_sha256"]
                or self.transformed_estimator_fingerprint_sha256
                != ambient_transformed["field_estimate_fingerprint_sha256"]
                or self.pipeline_rerun_count != 20
            ):
                raise QualificationContractError(
                    "Cartesian D3 rerun identities are not derived from its "
                    "exact ambient pipeline check and closed rerun count"
                )
        else:
            aggregate = self.aggregate_runtime_receipt
            _exact_keys(
                aggregate,
                {
                    "schema_version",
                    "development_seed",
                    "selection_seed_accessed",
                    "transformation_sha256",
                    "tolerance",
                    "pipeline_checks",
                    "loop_variant_checks",
                    "all_algebraic_checks",
                    "checks",
                    "pipeline_rerun_verified",
                    "base_estimator_fingerprint_sha256",
                    "transformed_estimator_fingerprint_sha256",
                    "pipeline_rerun_count",
                    "field_pipeline_execution_count",
                    "crossed_loop_cell_count",
                    "loop_variant_rerun_count",
                    "sealed_loop_prediction_count",
                    "procrustes_o2_determinant_explicit",
                    "signed_loop_law_verified",
                    "verified",
                    "integer_output_present",
                    "topology_claimed",
                },
                label="representation D3 aggregate",
            )
            _constant(
                aggregate["schema_version"],
                "spirallens.representation-pipeline-metamorphic-receipt.v0.3",
                label="representation D3 aggregate schema_version",
            )
            _constant(
                aggregate["development_seed"],
                314159,
                label="representation D3 development_seed",
            )
            for name, expected_value in (
                ("selection_seed_accessed", False),
                ("pipeline_rerun_verified", True),
                ("procrustes_o2_determinant_explicit", True),
                ("signed_loop_law_verified", True),
                ("verified", True),
                ("integer_output_present", False),
                ("topology_claimed", False),
            ):
                _constant(
                    aggregate[name],
                    expected_value,
                    label=f"representation D3 aggregate {name}",
                )
            require_sha256(
                aggregate["transformation_sha256"],
                label="representation D3 transformation_sha256",
            )
            tolerance = require_finite_real(
                aggregate["tolerance"],
                label="representation D3 tolerance",
                minimum=0.0,
                minimum_inclusive=False,
            )
            raw_pipeline_checks = aggregate["pipeline_checks"]
            if (
                not isinstance(raw_pipeline_checks, list)
                or len(raw_pipeline_checks) != 3
            ):
                raise QualificationContractError(
                    "representation D3 requires exactly three graph-family "
                    "pipeline checks"
                )
            pipeline_checks = tuple(
                _validate_representation_pipeline_check(
                    item,
                    index=index,
                    tolerance=tolerance,
                )
                for index, item in enumerate(raw_pipeline_checks)
            )
            pipeline_pairs = tuple(
                (
                    item["base_estimator_fingerprint_sha256"],
                    item["transformed_estimator_fingerprint_sha256"],
                )
                for item in pipeline_checks
            )
            if len(set(pipeline_pairs)) != len(pipeline_pairs):
                raise QualificationContractError(
                    "representation D3 graph-family pipeline checks must be distinct"
                )
            field_graph_ids = tuple(item["field_graph_id"] for item in pipeline_checks)
            if len(set(field_graph_ids)) != 3:
                raise QualificationContractError(
                    "representation D3 pipeline must cover three distinct A graphs"
                )
            crossed_by_cell: dict[
                tuple[object, object],
                dict[str, object],
            ] = {}
            for pipeline_check in pipeline_checks:
                raw_crossed = pipeline_check["crossed_loop_checks"]
                assert isinstance(raw_crossed, list)
                for crossed in raw_crossed:
                    crossed_document = _mapping(
                        crossed,
                        label="representation D3 crossed loop",
                    )
                    key = (
                        crossed_document["field_graph_id"],
                        crossed_document["cycle_graph_id"],
                    )
                    if key in crossed_by_cell:
                        raise QualificationContractError(
                            "representation D3 crossed A by B cell is duplicated"
                        )
                    crossed_by_cell[key] = crossed_document
            if len(crossed_by_cell) != 9:
                raise QualificationContractError(
                    "representation D3 must execute all three A by three B "
                    "matched-loop cells"
                )
            raw_variants = aggregate["loop_variant_checks"]
            if not isinstance(raw_variants, list) or len(raw_variants) != 27:
                raise QualificationContractError(
                    "representation D3 requires three actual loop variants "
                    "for every A by B cell"
                )
            variant_checks = tuple(
                _validate_representation_loop_law(
                    item,
                    label=f"representation D3 loop variant[{index}]",
                    tolerance=tolerance,
                    expected_receipt_version=(
                        "spirallens.representation-loop-variant-law.v0.1"
                    ),
                )
                for index, item in enumerate(raw_variants)
            )
            expected_variant_sequence = tuple(
                (
                    crossed["field_graph_id"],
                    crossed["cycle_graph_id"],
                    law,
                )
                for pipeline_check in pipeline_checks
                for crossed in pipeline_check["crossed_loop_checks"]  # type: ignore[union-attr]
                for law in (
                    "reference_rotation",
                    "reference_reflection",
                    "loop_reversal",
                )
            )
            observed_variant_sequence = tuple(
                (
                    item["field_graph_id"],
                    item["cycle_graph_id"],
                    item["law"],
                )
                for item in variant_checks
            )
            if observed_variant_sequence != expected_variant_sequence:
                raise QualificationContractError(
                    "representation D3 loop variants differ from the exact "
                    "A by B by law sequence"
                )
            for variant in variant_checks:
                key = (
                    variant["field_graph_id"],
                    variant["cycle_graph_id"],
                )
                base_crossed = crossed_by_cell.get(key)
                if base_crossed is None:
                    raise QualificationContractError(
                        "representation D3 loop variant has no crossed base cell"
                    )
                if (
                    variant["base_blind_input"] != base_crossed["base_blind_input"]
                    or variant["base_blind_input_sha256"]
                    != base_crossed["base_blind_input_sha256"]
                    or variant["base_prediction"] != base_crossed["base_prediction"]
                ):
                    raise QualificationContractError(
                        "representation D3 loop variant differs from its sealed "
                        "crossed base prediction"
                    )
            if not all(item["alignment_determinant"] < 0.0 for item in pipeline_checks):
                raise QualificationContractError(
                    "representation D3 fixed signed permutation must exercise "
                    "the determinant-negative Procrustes branch"
                )
            base = canonical_json_sha256(
                {
                    "field_estimate_fingerprints": [
                        item["base_estimator_fingerprint_sha256"]
                        for item in pipeline_checks
                    ]
                }
            )
            transformed = canonical_json_sha256(
                {
                    "field_estimate_fingerprints": [
                        item["transformed_estimator_fingerprint_sha256"]
                        for item in pipeline_checks
                    ]
                }
            )
            if (
                self.base_estimator_fingerprint_sha256 != base
                or self.transformed_estimator_fingerprint_sha256 != transformed
                or aggregate["base_estimator_fingerprint_sha256"] != base
                or aggregate["transformed_estimator_fingerprint_sha256"] != transformed
                or self.pipeline_rerun_count != 18
                or aggregate["pipeline_rerun_count"] != 18
                or aggregate["field_pipeline_execution_count"] != 2
                or aggregate["crossed_loop_cell_count"] != 9
                or aggregate["loop_variant_rerun_count"] != 27
                or aggregate["sealed_loop_prediction_count"] != 45
            ):
                raise QualificationContractError(
                    "representation D3 rerun identities are not derived from "
                    "its full field, crossed-loop, and loop-variant executions"
                )
            raw_algebraic_checks = aggregate["all_algebraic_checks"]
            if (
                not isinstance(raw_algebraic_checks, list)
                or len(raw_algebraic_checks) != 7
            ):
                raise QualificationContractError(
                    "representation D3 requires all seven algebraic checks"
                )
            algebraic_obligations = (
                "ambient-signed-permutation",
                "local-frame-gauge",
                "reference-orientation",
                "reference-orientation",
                "loop-reversal",
                "spin-two-double-angle",
                "nonorientable-control",
            )
            algebraic_checks = tuple(
                _validate_representation_metamorph_receipt(
                    item,
                    obligation_id=obligation_id,
                )
                for item, obligation_id in zip(
                    raw_algebraic_checks,
                    algebraic_obligations,
                    strict=True,
                )
            )
            if len({canonical_json_sha256(item) for item in algebraic_checks}) != len(
                algebraic_checks
            ):
                raise QualificationContractError(
                    "representation D3 algebraic checks must be distinct actual "
                    "transformations"
                )
            selected_indices = {
                "ambient-signed-permutation": 0,
                "local-frame-gauge": 1,
                "reference-orientation": 2,
                "loop-reversal": 4,
                "spin-two-double-angle": 5,
                "nonorientable-control": 6,
            }
            selected = {
                obligation_id: document
                for obligation_id, document in self.obligation_receipts
            }
            if any(
                selected[obligation_id] != algebraic_checks[index]
                for obligation_id, index in selected_indices.items()
            ):
                raise QualificationContractError(
                    "representation D3 selected obligations differ from the "
                    "full algebraic-check sequence"
                )
            expected_wrappers = [
                {
                    "obligation_id": obligation_id,
                    "receipt": document,
                }
                for obligation_id, document in self.obligation_receipts
            ]
            if aggregate["checks"] != expected_wrappers:
                raise QualificationContractError(
                    "representation D3 aggregate differs from its exact rerun "
                    "and check identities"
                )

    @property
    def obligation_ids(self) -> tuple[str, ...]:
        return _D3_OBLIGATIONS[self.evidence_id]

    @property
    def failed_obligation_ids(self) -> tuple[str, ...]:
        return ()

    @property
    def observation_fingerprints_sha256(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    canonical_json_sha256(self.aggregate_runtime_receipt),
                    *(
                        canonical_json_sha256(document)
                        for _, document in self.obligation_receipts
                    ),
                    self.base_estimator_fingerprint_sha256,
                    self.transformed_estimator_fingerprint_sha256,
                }
            )
        )

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "aggregate_runtime_receipt": self.aggregate_runtime_receipt,
            "obligation_receipts": [
                {"obligation_id": obligation_id, "receipt": receipt}
                for obligation_id, receipt in self.obligation_receipts
            ],
            "base_estimator_fingerprint_sha256": (
                self.base_estimator_fingerprint_sha256
            ),
            "transformed_estimator_fingerprint_sha256": (
                self.transformed_estimator_fingerprint_sha256
            ),
            "pipeline_rerun_count": self.pipeline_rerun_count,
        }

    @classmethod
    def from_cartesian(
        cls,
        receipt: object,
    ) -> D3PipelineExecutionReceipt:
        from .pipeline_metamorphic import (
            CartesianPipelineMetamorphicReceipt,
            PipelineMetamorphLaw,
        )

        if not isinstance(receipt, CartesianPipelineMetamorphicReceipt):
            raise TypeError("receipt must be a CartesianPipelineMetamorphicReceipt")
        if (
            receipt.state is not QualificationState.PASS
            or not receipt.pipeline_rerun_verified
        ):
            raise QualificationContractError(
                "Cartesian D3 aggregate must mechanically pass"
            )
        by_law = {item.law: item for item in receipt.checks}
        law_mapping = (
            (
                "ambient-signed-permutation",
                PipelineMetamorphLaw.AMBIENT_SIGNED_PERMUTATION,
            ),
            ("loop-reversal", PipelineMetamorphLaw.LOOP_REVERSAL),
            ("reference-reflection", PipelineMetamorphLaw.REFERENCE_REFLECTION),
            ("reference-rotation", PipelineMetamorphLaw.REFERENCE_ROTATION),
        )
        obligations = tuple(
            (obligation_id, by_law[law].to_dict()) for obligation_id, law in law_mapping
        )
        base = receipt.checks[0].base.field_estimate_fingerprint_sha256
        transformed = receipt.checks[0].transformed.field_estimate_fingerprint_sha256
        return cls(
            evidence_id="cartesian-gauge-pipeline-rerun-verified",
            aggregate_runtime_receipt=receipt.to_dict(),
            obligation_receipts=obligations,
            base_estimator_fingerprint_sha256=base,
            transformed_estimator_fingerprint_sha256=transformed,
            pipeline_rerun_count=(
                sum(5 for check in receipt.checks if check.pipeline_rerun_verified)
            ),
        )

    @classmethod
    def from_representation(
        cls,
        *,
        obligation_checks: Mapping[str, object],
        pipeline_checks: tuple[Mapping[str, object], ...],
        loop_variant_checks: tuple[Mapping[str, object], ...],
        all_algebraic_checks: tuple[object, ...],
        development_seed: int,
        transformation_sha256: str,
        tolerance: float,
    ) -> D3PipelineExecutionReceipt:
        from .metamorphic import MetamorphCheck

        if len(all_algebraic_checks) != 7 or any(
            not isinstance(check, MetamorphCheck) for check in all_algebraic_checks
        ):
            raise TypeError(
                "representation D3 requires all seven typed algebraic checks"
            )
        selected_indices = {
            "ambient-signed-permutation": 0,
            "local-frame-gauge": 1,
            "reference-orientation": 2,
            "loop-reversal": 4,
            "spin-two-double-angle": 5,
            "nonorientable-control": 6,
        }
        obligations: list[tuple[str, dict[str, object]]] = []
        for obligation_id in _D3_OBLIGATIONS[
            "representation-gauge-pipeline-rerun-verified"
        ]:
            if obligation_id == "pipeline-rerun":
                continue
            check = obligation_checks.get(obligation_id)
            if not isinstance(check, MetamorphCheck):
                raise TypeError(
                    "representation D3 obligations require actual MetamorphCheck "
                    "objects"
                )
            expected_check = all_algebraic_checks[selected_indices[obligation_id]]
            if check is not expected_check and check != expected_check:
                raise QualificationContractError(
                    "representation D3 selected obligation differs from its "
                    "full algebraic-check sequence"
                )
            if check.state not in {
                QualificationState.PASS,
                QualificationState.INSUFFICIENT,
            }:
                raise QualificationContractError(
                    "representation D3 metamorphic check did not succeed"
                )
            obligations.append((obligation_id, check.to_dict()))
        pipeline_documents = tuple(
            _mapping(
                item,
                label=f"representation D3 pipeline check[{index}]",
            )
            for index, item in enumerate(pipeline_checks)
        )
        if len(pipeline_documents) != 3:
            raise QualificationContractError(
                "representation D3 requires three graph-family pipeline checks"
            )
        loop_variant_documents = tuple(
            _mapping(
                item,
                label=f"representation D3 loop variant[{index}]",
            )
            for index, item in enumerate(loop_variant_checks)
        )
        if len(loop_variant_documents) != 27:
            raise QualificationContractError(
                "representation D3 requires 27 A by B by loop-law reruns"
            )
        base_estimator_fingerprint_sha256 = canonical_json_sha256(
            {
                "field_estimate_fingerprints": [
                    require_sha256(
                        item["base_estimator_fingerprint_sha256"],
                        label="representation D3 base estimator fingerprint",
                    )
                    for item in pipeline_documents
                ]
            }
        )
        transformed_estimator_fingerprint_sha256 = canonical_json_sha256(
            {
                "field_estimate_fingerprints": [
                    require_sha256(
                        item["transformed_estimator_fingerprint_sha256"],
                        label=("representation D3 transformed estimator fingerprint"),
                    )
                    for item in pipeline_documents
                ]
            }
        )
        aggregate = {
            "schema_version": (
                "spirallens.representation-pipeline-metamorphic-receipt.v0.3"
            ),
            "development_seed": development_seed,
            "selection_seed_accessed": False,
            "transformation_sha256": transformation_sha256,
            "tolerance": tolerance,
            "pipeline_checks": list(pipeline_documents),
            "loop_variant_checks": list(loop_variant_documents),
            "all_algebraic_checks": [
                check.to_dict()  # type: ignore[union-attr]
                for check in all_algebraic_checks
            ],
            "checks": [
                {"obligation_id": obligation_id, "receipt": document}
                for obligation_id, document in obligations
            ],
            "pipeline_rerun_verified": True,
            "base_estimator_fingerprint_sha256": (base_estimator_fingerprint_sha256),
            "transformed_estimator_fingerprint_sha256": (
                transformed_estimator_fingerprint_sha256
            ),
            "pipeline_rerun_count": 18,
            "field_pipeline_execution_count": 2,
            "crossed_loop_cell_count": 9,
            "loop_variant_rerun_count": 27,
            "sealed_loop_prediction_count": 45,
            "procrustes_o2_determinant_explicit": True,
            "signed_loop_law_verified": True,
            "verified": True,
            "integer_output_present": False,
            "topology_claimed": False,
        }
        return cls(
            evidence_id="representation-gauge-pipeline-rerun-verified",
            aggregate_runtime_receipt=aggregate,
            obligation_receipts=tuple(obligations),
            base_estimator_fingerprint_sha256=(base_estimator_fingerprint_sha256),
            transformed_estimator_fingerprint_sha256=(
                transformed_estimator_fingerprint_sha256
            ),
            pipeline_rerun_count=18,
        )

    @classmethod
    def from_dict(cls, value: object) -> D3PipelineExecutionReceipt:
        item = _mapping(value, label="D3 pipeline execution receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="D3 pipeline execution receipt")
        raw_obligations = item["obligation_receipts"]
        if not isinstance(raw_obligations, list):
            raise QualificationContractError(
                "D3 obligation_receipts must be a JSON array"
            )
        obligations: list[tuple[str, dict[str, object]]] = []
        for raw in raw_obligations:
            document = _mapping(raw, label="D3 obligation wrapper")
            _exact_keys(
                document,
                {"obligation_id", "receipt"},
                label="D3 obligation wrapper",
            )
            obligations.append(
                (
                    require_slug(document["obligation_id"], label="D3 obligation_id"),
                    _mapping(document["receipt"], label="D3 obligation receipt"),
                )
            )
        return cls(
            schema_version=item["schema_version"],  # type: ignore[arg-type]
            evidence_id=require_slug(item["evidence_id"], label="D3 evidence_id"),
            aggregate_runtime_receipt=_mapping(
                item["aggregate_runtime_receipt"],
                label="D3 aggregate_runtime_receipt",
            ),
            obligation_receipts=tuple(obligations),
            base_estimator_fingerprint_sha256=require_sha256(
                item["base_estimator_fingerprint_sha256"],
                label="D3 base estimator fingerprint",
            ),
            transformed_estimator_fingerprint_sha256=require_sha256(
                item["transformed_estimator_fingerprint_sha256"],
                label="D3 transformed estimator fingerprint",
            ),
            pipeline_rerun_count=require_plain_int(
                item["pipeline_rerun_count"],
                label="D3 pipeline_rerun_count",
                minimum=2,
            ),
        )


@dataclass(frozen=True, slots=True)
class D2CoreConfounderCellReceipt:
    """One truth-blind D2 confounder execution on one frozen A graph."""

    cell_id: str
    confounder_id: str
    construction_id: str
    field_graph_id: str
    policy_fingerprint_sha256: str
    expected_attempt_status: AttemptStatus
    expected_prediction_class: CorePredictionClass
    expected_reason_codes: tuple[str, ...]
    construction_observation: dict[str, object]
    blind_input_receipt: dict[str, object]
    sealed_prediction_receipt: dict[str, object]
    candidate_rows: tuple[int, ...]
    state: QualificationState
    reason_codes: tuple[str, ...]
    schema_version: str = D2_CONFOUNDER_CELL_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "cell_id",
            "confounder_id",
            "construction_id",
            "field_graph_id",
            "policy_fingerprint_sha256",
            "expected_attempt_status",
            "expected_prediction_class",
            "expected_reason_codes",
            "construction_observation",
            "blind_input_receipt",
            "sealed_prediction_receipt",
            "candidate_rows",
            "state",
            "reason_codes",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            D2_CONFOUNDER_CELL_SCHEMA_VERSION,
            label="D2 confounder cell schema_version",
        )
        for name in (
            "cell_id",
            "confounder_id",
            "construction_id",
            "field_graph_id",
        ):
            require_slug(getattr(self, name), label=f"D2 confounder {name}")
        require_sha256(
            self.policy_fingerprint_sha256,
            label="D2 confounder policy_fingerprint_sha256",
        )
        if not isinstance(self.expected_attempt_status, AttemptStatus):
            raise TypeError("expected_attempt_status must be an AttemptStatus")
        if not isinstance(self.expected_prediction_class, CorePredictionClass):
            raise TypeError("expected_prediction_class must be a CorePredictionClass")
        if not isinstance(self.state, QualificationState):
            raise TypeError("D2 confounder state must be a QualificationState")
        expected_reasons = tuple(sorted(set(self.expected_reason_codes)))
        if self.expected_reason_codes != expected_reasons:
            raise QualificationContractError(
                "D2 confounder expected reasons must be unique and canonical"
            )
        for reason in expected_reasons:
            require_slug(reason, label="D2 confounder expected reason")
        reasons = tuple(sorted(set(self.reason_codes)))
        if self.reason_codes != reasons:
            raise QualificationContractError(
                "D2 confounder reasons must be unique and canonical"
            )
        for reason in reasons:
            require_slug(reason, label="D2 confounder reason")
        construction = _mapping(
            self.construction_observation,
            label="D2 confounder construction observation",
        )
        _exact_keys(
            construction,
            {
                "probe_row",
                "probe_row_role",
                "probe_amplitude",
                "probe_identifiability_score",
                "probe_measurement_support",
                "core_amplitude_ceiling",
                "identifiability_floor",
                "minimum_support_count",
                "core_amplitude_threshold_satisfied",
                "direction_loss_threshold_satisfied",
                "measurement_support_threshold_satisfied",
                "selection_seed_present",
                "oracle_input_present",
            },
            label="D2 confounder construction observation",
        )
        probe_row = require_plain_int(
            construction["probe_row"],
            label="D2 confounder probe_row",
            minimum=0,
        )
        probe_row_role = require_slug(
            construction["probe_row_role"],
            label="D2 confounder probe_row_role",
        )
        probe_amplitude = require_finite_real(
            construction["probe_amplitude"],
            label="D2 confounder probe_amplitude",
        )
        probe_identifiability = require_finite_real(
            construction["probe_identifiability_score"],
            label="D2 confounder probe_identifiability_score",
        )
        probe_support = require_plain_int(
            construction["probe_measurement_support"],
            label="D2 confounder probe_measurement_support",
            minimum=0,
        )
        amplitude_ceiling = require_finite_real(
            construction["core_amplitude_ceiling"],
            label="D2 confounder core_amplitude_ceiling",
        )
        identifiability_floor = require_finite_real(
            construction["identifiability_floor"],
            label="D2 confounder identifiability_floor",
        )
        minimum_support = require_plain_int(
            construction["minimum_support_count"],
            label="D2 confounder minimum_support_count",
            minimum=1,
        )
        expected_thresholds = {
            "core_amplitude_threshold_satisfied": (
                probe_amplitude <= amplitude_ceiling
            ),
            "direction_loss_threshold_satisfied": (
                probe_identifiability <= identifiability_floor
            ),
            "measurement_support_threshold_satisfied": (
                probe_support >= minimum_support
            ),
            "selection_seed_present": False,
            "oracle_input_present": False,
        }
        for name, expected in expected_thresholds.items():
            _exact_bool(
                construction[name],
                expected=expected,
                label=f"D2 confounder construction {name}",
            )
        from .protocol import (
            D2_IDENTIFIABILITY_LOSS_DECOY_CONSTRUCTION_ID,
            D2_MISSING_CANDIDATE_SUPPORT_CONSTRUCTION_ID,
        )

        if self.construction_id == D2_IDENTIFIABILITY_LOSS_DECOY_CONSTRUCTION_ID:
            construction_matches = (
                probe_row_role == "offcenter"
                and probe_row == 0
                and probe_amplitude > amplitude_ceiling
                and not expected_thresholds["core_amplitude_threshold_satisfied"]
                and expected_thresholds["direction_loss_threshold_satisfied"]
                and expected_thresholds["measurement_support_threshold_satisfied"]
            )
        elif self.construction_id == D2_MISSING_CANDIDATE_SUPPORT_CONSTRUCTION_ID:
            construction_matches = (
                probe_row_role == "center"
                and probe_amplitude == 0.0
                and expected_thresholds["core_amplitude_threshold_satisfied"]
                and expected_thresholds["direction_loss_threshold_satisfied"]
                and not expected_thresholds["measurement_support_threshold_satisfied"]
            )
        else:
            construction_matches = False
        if not construction_matches:
            raise QualificationContractError(
                "D2 confounder observation differs from its exact construction"
            )
        if len(set(self.candidate_rows)) != len(self.candidate_rows):
            raise QualificationContractError(
                "D2 confounder candidate rows must be unique"
            )
        blind = _runtime_receipt(
            self.blind_input_receipt,
            label="D2 confounder blind input receipt",
            receipt_version="spirallens.blind-core-input.v0.3",
            runtime_keys=_CORE_BLIND_KEYS,
        )
        prediction = _runtime_receipt(
            self.sealed_prediction_receipt,
            label="D2 confounder sealed prediction receipt",
            receipt_version="spirallens.sealed-core-prediction.v0.1",
            runtime_keys=_CORE_PREDICTION_KEYS,
        )
        blind_sha256 = canonical_json_sha256(blind)
        _constant(
            prediction["blind_input_fingerprint_sha256"],
            blind_sha256,
            label="D2 confounder prediction blind-input join",
        )
        _constant(
            prediction["policy_fingerprint_sha256"],
            self.policy_fingerprint_sha256,
            label="D2 confounder prediction policy join",
        )
        _constant(
            prediction["candidate_rows"],
            _int64_vector_fingerprint(self.candidate_rows),
            label="D2 confounder candidate-row receipt",
        )
        _exact_bool(
            prediction["oracle_read"],
            expected=False,
            label="D2 confounder oracle_read",
        )
        _exact_bool(
            prediction["sealed_before_oracle_score"],
            expected=True,
            label="D2 confounder sealed_before_oracle_score",
        )
        try:
            observed_status = AttemptStatus(prediction["observed_attempt_status"])
            observed_class = CorePredictionClass(prediction["prediction_class"])
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "D2 confounder prediction carries an unsupported enum"
            ) from error
        observed_reasons = _canonical_reasons(
            prediction["reason_codes"],
            label="D2 confounder observed reasons",
        )
        behavior_matches = (
            observed_status is self.expected_attempt_status
            and observed_class is self.expected_prediction_class
            and observed_reasons == self.expected_reason_codes
            and not self.candidate_rows
        )
        expected_state = (
            QualificationState.PASS if behavior_matches else QualificationState.FAIL
        )
        expected_failure_reasons = (
            () if behavior_matches else ("d2_false_core_confounder_behavior_mismatch",)
        )
        if (
            self.state is not expected_state
            or self.reason_codes != expected_failure_reasons
        ):
            raise QualificationContractError(
                "D2 confounder state differs from exact truth-blind behavior"
            )

    @classmethod
    def from_runtime(
        cls,
        *,
        cell_id: str,
        declaration: object,
        field_graph_id: str,
        policy: object,
        probe_row: int,
        probe_row_role: str,
        blind_input: object,
        sealed_prediction: object,
    ) -> D2CoreConfounderCellReceipt:
        from .blind import BlindCoreInput, SealedCorePrediction
        from .prerequisites import CorePrerequisitePolicy
        from .protocol import D2CoreConfounderDeclaration

        if not isinstance(declaration, D2CoreConfounderDeclaration):
            raise TypeError("declaration must be a D2CoreConfounderDeclaration")
        if not isinstance(blind_input, BlindCoreInput):
            raise TypeError("blind_input must be a BlindCoreInput")
        if not isinstance(sealed_prediction, SealedCorePrediction):
            raise TypeError("sealed_prediction must be a SealedCorePrediction")
        if not isinstance(policy, CorePrerequisitePolicy):
            raise TypeError("policy must be a CorePrerequisitePolicy")
        row_matches = tuple(
            index
            for index, row_id in enumerate(blind_input.row_ids)
            if int(row_id) == probe_row
        )
        if len(row_matches) != 1:
            raise QualificationContractError(
                "D2 confounder probe row must join the blind row domain"
            )
        row_index = row_matches[0]
        behavior_matches = (
            sealed_prediction.observed_attempt_status
            is declaration.expected_attempt_status
            and sealed_prediction.prediction_class
            is declaration.expected_prediction_class
            and sealed_prediction.reason_codes == declaration.expected_reason_codes
            and sealed_prediction.candidate_rows.shape[0] == 0
        )
        return cls(
            cell_id=cell_id,
            confounder_id=declaration.confounder_id,
            construction_id=declaration.construction_id,
            field_graph_id=field_graph_id,
            policy_fingerprint_sha256=policy.fingerprint_sha256,
            expected_attempt_status=declaration.expected_attempt_status,
            expected_prediction_class=declaration.expected_prediction_class,
            expected_reason_codes=declaration.expected_reason_codes,
            construction_observation={
                "probe_row": probe_row,
                "probe_row_role": probe_row_role,
                "probe_amplitude": float(blind_input.amplitude[row_index]),
                "probe_identifiability_score": float(
                    blind_input.identifiability_score[row_index]
                ),
                "probe_measurement_support": int(blind_input.support_counts[row_index]),
                "core_amplitude_ceiling": policy.core_amplitude_ceiling,
                "identifiability_floor": policy.identifiability_floor,
                "minimum_support_count": policy.minimum_support_count,
                "core_amplitude_threshold_satisfied": bool(
                    blind_input.amplitude[row_index] <= policy.core_amplitude_ceiling
                ),
                "direction_loss_threshold_satisfied": bool(
                    blind_input.identifiability_score[row_index]
                    <= policy.identifiability_floor
                ),
                "measurement_support_threshold_satisfied": bool(
                    blind_input.support_counts[row_index]
                    >= policy.minimum_support_count
                ),
                "selection_seed_present": False,
                "oracle_input_present": False,
            },
            blind_input_receipt=blind_input.to_dict(),
            sealed_prediction_receipt=sealed_prediction.to_dict(),
            candidate_rows=tuple(
                int(item) for item in sealed_prediction.candidate_rows
            ),
            state=(
                QualificationState.PASS if behavior_matches else QualificationState.FAIL
            ),
            reason_codes=(
                ()
                if behavior_matches
                else ("d2_false_core_confounder_behavior_mismatch",)
            ),
        )

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "cell_id": self.cell_id,
            "confounder_id": self.confounder_id,
            "construction_id": self.construction_id,
            "field_graph_id": self.field_graph_id,
            "policy_fingerprint_sha256": self.policy_fingerprint_sha256,
            "expected_attempt_status": self.expected_attempt_status.value,
            "expected_prediction_class": self.expected_prediction_class.value,
            "expected_reason_codes": list(self.expected_reason_codes),
            "construction_observation": self.construction_observation,
            "blind_input_receipt": self.blind_input_receipt,
            "sealed_prediction_receipt": self.sealed_prediction_receipt,
            "candidate_rows": list(self.candidate_rows),
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, value: object) -> D2CoreConfounderCellReceipt:
        item = _mapping(value, label="D2 confounder cell receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="D2 confounder cell receipt")
        candidate_rows = item["candidate_rows"]
        if not isinstance(candidate_rows, list) or any(
            type(row) is not int for row in candidate_rows
        ):
            raise QualificationContractError(
                "D2 confounder candidate_rows must be an integer array"
            )
        return cls(
            schema_version=item["schema_version"],  # type: ignore[arg-type]
            cell_id=require_slug(item["cell_id"], label="D2 confounder cell_id"),
            confounder_id=require_slug(item["confounder_id"], label="D2 confounder_id"),
            construction_id=require_slug(
                item["construction_id"],
                label="D2 confounder construction_id",
            ),
            field_graph_id=require_slug(
                item["field_graph_id"], label="D2 confounder field_graph_id"
            ),
            policy_fingerprint_sha256=require_sha256(
                item["policy_fingerprint_sha256"],
                label="D2 confounder policy fingerprint",
            ),
            expected_attempt_status=AttemptStatus(item["expected_attempt_status"]),
            expected_prediction_class=CorePredictionClass(
                item["expected_prediction_class"]
            ),
            expected_reason_codes=_canonical_reasons(
                item["expected_reason_codes"],
                label="D2 confounder expected reasons",
            ),
            construction_observation=_mapping(
                item["construction_observation"],
                label="D2 confounder construction observation",
            ),
            blind_input_receipt=_mapping(
                item["blind_input_receipt"],
                label="D2 confounder blind input receipt",
            ),
            sealed_prediction_receipt=_mapping(
                item["sealed_prediction_receipt"],
                label="D2 confounder sealed prediction receipt",
            ),
            candidate_rows=tuple(candidate_rows),
            state=QualificationState(item["state"]),
            reason_codes=_canonical_reasons(
                item["reason_codes"],
                label="D2 confounder reasons",
            ),
        )


@dataclass(frozen=True, slots=True)
class D2CoreConfounderMatrixReceipt:
    """Exact seed-free confounder registry crossed with every frozen A graph."""

    policy_fingerprint_sha256: str
    confounder_declarations: tuple[dict[str, object], ...]
    field_graph_ids: tuple[str, ...]
    cells: tuple[D2CoreConfounderCellReceipt, ...]
    state: QualificationState
    failed_cell_ids: tuple[str, ...]
    selection_seed_consumed: bool = False
    oracle_scoring_used: bool = False
    joint_loop_registry_consumed: bool = False
    schema_version: str = D2_CONFOUNDER_MATRIX_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "policy_fingerprint_sha256",
            "confounder_declarations",
            "field_graph_ids",
            "cells",
            "state",
            "failed_cell_ids",
            "selection_seed_consumed",
            "oracle_scoring_used",
            "joint_loop_registry_consumed",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            D2_CONFOUNDER_MATRIX_SCHEMA_VERSION,
            label="D2 confounder matrix schema_version",
        )
        require_sha256(
            self.policy_fingerprint_sha256,
            label="D2 confounder matrix policy fingerprint",
        )
        for name in (
            "selection_seed_consumed",
            "oracle_scoring_used",
            "joint_loop_registry_consumed",
        ):
            _exact_bool(
                getattr(self, name),
                expected=False,
                label=f"D2 confounder matrix {name}",
            )
        if self.field_graph_ids != tuple(sorted(set(self.field_graph_ids))):
            raise QualificationContractError(
                "D2 confounder matrix graph IDs must be unique and canonical"
            )
        for graph_id in self.field_graph_ids:
            require_slug(graph_id, label="D2 confounder matrix graph ID")
        from .protocol import D2CoreConfounderDeclaration

        declarations = tuple(
            D2CoreConfounderDeclaration.from_dict(item)
            for item in self.confounder_declarations
        )
        confounder_ids = tuple(item.confounder_id for item in declarations)
        if confounder_ids != tuple(sorted(set(confounder_ids))):
            raise QualificationContractError(
                "D2 confounder declarations must be unique and canonical"
            )
        if type(self.cells) is not tuple or any(
            not isinstance(item, D2CoreConfounderCellReceipt) for item in self.cells
        ):
            raise TypeError("D2 confounder matrix cells have the wrong type")
        expected_pairs = tuple(
            (declaration.confounder_id, graph_id)
            for declaration in declarations
            for graph_id in self.field_graph_ids
        )
        observed_pairs = tuple(
            (cell.confounder_id, cell.field_graph_id) for cell in self.cells
        )
        if self.state is QualificationState.NOT_RUN:
            if self.cells or self.failed_cell_ids:
                raise QualificationContractError(
                    "not-run D2 confounder matrix cannot carry runtime cells"
                )
            return
        if self.state not in {
            QualificationState.PASS,
            QualificationState.FAIL,
        }:
            raise QualificationContractError(
                "attempted D2 confounder matrix state must be pass or fail"
            )
        if observed_pairs != expected_pairs:
            raise QualificationContractError(
                "D2 confounder cells differ from the exact confounder x A matrix"
            )
        declaration_by_id = {item.confounder_id: item for item in declarations}
        for cell in self.cells:
            declaration = declaration_by_id[cell.confounder_id]
            expected_cell_id = f"d2cf.{cell.confounder_id}.{cell.field_graph_id}"
            if (
                cell.cell_id != expected_cell_id
                or cell.construction_id != declaration.construction_id
                or cell.policy_fingerprint_sha256 != self.policy_fingerprint_sha256
                or cell.expected_attempt_status
                is not declaration.expected_attempt_status
                or cell.expected_prediction_class
                is not declaration.expected_prediction_class
                or cell.expected_reason_codes != declaration.expected_reason_codes
            ):
                raise QualificationContractError(
                    "D2 confounder cell differs from its exact declaration"
                )
        failed = tuple(
            cell.cell_id
            for cell in self.cells
            if cell.state is not QualificationState.PASS
        )
        if self.failed_cell_ids != failed:
            raise QualificationContractError(
                "D2 confounder failed IDs differ from cell states"
            )
        expected_state = (
            QualificationState.PASS if not failed else QualificationState.FAIL
        )
        if self.state is not expected_state:
            raise QualificationContractError(
                "D2 confounder matrix state differs from its cells"
            )

    @property
    def reason_codes(self) -> tuple[str, ...]:
        if self.state is QualificationState.PASS:
            return ()
        if self.state is QualificationState.NOT_RUN:
            return ("d2_false_core_confounder_matrix_not_run",)
        return ("d2_false_core_confounder_matrix_nonpass",)

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def validate_protocol(self, protocol: object) -> None:
        from .protocol import QualificationProtocol

        if not isinstance(protocol, QualificationProtocol):
            raise TypeError("protocol must be a QualificationProtocol")
        if self.confounder_declarations != tuple(
            item.to_dict() for item in protocol.d2_core_confounders
        ):
            raise QualificationContractError(
                "D2 confounder receipt declarations differ from the protocol"
            )
        expected_graph_ids = tuple(
            item.graph_id for item in protocol.graphs.field_estimation
        )
        if self.field_graph_ids != expected_graph_ids:
            raise QualificationContractError(
                "D2 confounder receipt A graphs differ from the protocol"
            )
        from .prerequisites import CorePrerequisitePolicy

        thresholds = protocol.thresholds
        expected_policy = CorePrerequisitePolicy(
            policy_id="qualification-core-prerequisites-v0.5",
            core_amplitude_ceiling=thresholds.core_amplitude_ceiling,
            identifiability_floor=thresholds.identifiability_floor,
            edge_coherence_floor=thresholds.coherence_floor,
            minimum_support_count=thresholds.minimum_support_count,
            max_localized_core_fraction=(thresholds.max_localized_core_fraction),
            minimum_core_contrast_ratio=(thresholds.minimum_core_contrast_ratio),
        )
        if self.policy_fingerprint_sha256 != expected_policy.fingerprint_sha256:
            raise QualificationContractError(
                "D2 confounder receipt policy differs from protocol thresholds"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_fingerprint_sha256": self.policy_fingerprint_sha256,
            "confounder_declarations": list(self.confounder_declarations),
            "field_graph_ids": list(self.field_graph_ids),
            "cells": [cell.to_dict() for cell in self.cells],
            "state": self.state.value,
            "failed_cell_ids": list(self.failed_cell_ids),
            "selection_seed_consumed": self.selection_seed_consumed,
            "oracle_scoring_used": self.oracle_scoring_used,
            "joint_loop_registry_consumed": (self.joint_loop_registry_consumed),
        }

    @classmethod
    def from_dict(cls, value: object) -> D2CoreConfounderMatrixReceipt:
        item = _mapping(value, label="D2 confounder matrix receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="D2 confounder matrix receipt")
        raw_declarations = item["confounder_declarations"]
        raw_graph_ids = item["field_graph_ids"]
        raw_cells = item["cells"]
        raw_failed = item["failed_cell_ids"]
        if not all(
            isinstance(value, list)
            for value in (
                raw_declarations,
                raw_graph_ids,
                raw_cells,
                raw_failed,
            )
        ):
            raise QualificationContractError(
                "D2 confounder matrix arrays must be JSON arrays"
            )
        return cls(
            schema_version=item["schema_version"],  # type: ignore[arg-type]
            policy_fingerprint_sha256=require_sha256(
                item["policy_fingerprint_sha256"],
                label="D2 confounder matrix policy fingerprint",
            ),
            confounder_declarations=tuple(
                _mapping(entry, label="D2 confounder declaration")
                for entry in raw_declarations
            ),
            field_graph_ids=tuple(
                require_slug(entry, label="D2 confounder graph ID")
                for entry in raw_graph_ids
            ),
            cells=tuple(
                D2CoreConfounderCellReceipt.from_dict(entry) for entry in raw_cells
            ),
            state=QualificationState(item["state"]),
            failed_cell_ids=tuple(
                require_slug(entry, label="D2 failed cell ID") for entry in raw_failed
            ),
            selection_seed_consumed=item["selection_seed_consumed"],  # type: ignore[arg-type]
            oracle_scoring_used=item["oracle_scoring_used"],  # type: ignore[arg-type]
            joint_loop_registry_consumed=item["joint_loop_registry_consumed"],  # type: ignore[arg-type]
        )


StaticRuntimeEvidenceReceipt = D1FamilyExecutionReceipt | D3PipelineExecutionReceipt


def _parse_static_runtime_receipt(
    value: object,
) -> StaticRuntimeEvidenceReceipt:
    document = _mapping(value, label="static runtime evidence receipt")
    schema = document.get("schema_version")
    if schema == D1_FAMILY_EXECUTION_SCHEMA_VERSION:
        return D1FamilyExecutionReceipt.from_dict(document)
    if schema == D3_PIPELINE_EXECUTION_SCHEMA_VERSION:
        return D3PipelineExecutionReceipt.from_dict(document)
    raise QualificationContractError(
        "static runtime evidence receipt schema is not supported"
    )


@dataclass(frozen=True, slots=True)
class QualificationEvidenceBundle:
    """Exact full-receipt universe underlying attempted D2/D4/D5 summaries."""

    protocol_canonical_sha256: str
    source_binding_receipt_sha256: str
    selection_freeze_artifact_sha256: str
    selection_attempt_claim_sha256: str
    d2_confounder_matrix_receipt: D2CoreConfounderMatrixReceipt
    static_runtime_receipts: tuple[StaticRuntimeEvidenceReceipt, ...]
    core_cell_receipts: tuple[CoreCellEvaluationReceipt, ...]
    loop_cell_receipts: tuple[LoopCellEvaluationReceipt, ...]
    nonvacuity_receipts: tuple[NonvacuityEvaluationReceipt, ...]
    schema_version: str = EVIDENCE_BUNDLE_SCHEMA_VERSION
    claim_ceiling: str = "level_0"
    scientific_claim_eligible: bool = False
    subject_access_authorized: bool = False
    semantic_authority: bool = False
    integer_or_topology_authority: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "claim_ceiling",
            "protocol_canonical_sha256",
            "source_binding_receipt_sha256",
            "selection_freeze_artifact_sha256",
            "selection_attempt_claim_sha256",
            "d2_confounder_matrix_receipt",
            "static_runtime_receipts",
            "core_cell_receipts",
            "loop_cell_receipts",
            "nonvacuity_receipts",
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            EVIDENCE_BUNDLE_SCHEMA_VERSION,
            label="evidence bundle schema_version",
        )
        _constant(self.claim_ceiling, "level_0", label="evidence bundle claim_ceiling")
        for name in (
            "protocol_canonical_sha256",
            "source_binding_receipt_sha256",
            "selection_freeze_artifact_sha256",
            "selection_attempt_claim_sha256",
        ):
            require_sha256(getattr(self, name), label=f"evidence bundle {name}")
        if not isinstance(
            self.d2_confounder_matrix_receipt,
            D2CoreConfounderMatrixReceipt,
        ):
            raise TypeError(
                "evidence bundle d2_confounder_matrix_receipt has the wrong type"
            )
        for name in (
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
        ):
            _constant(getattr(self, name), False, label=f"evidence bundle {name}")
        for values, expected_type, identifier, label in (
            (
                self.core_cell_receipts,
                CoreCellEvaluationReceipt,
                "core_cell_id",
                "core cell receipts",
            ),
            (
                self.loop_cell_receipts,
                LoopCellEvaluationReceipt,
                "cell_id",
                "loop cell receipts",
            ),
            (
                self.nonvacuity_receipts,
                NonvacuityEvaluationReceipt,
                "primary_unit_id",
                "nonvacuity receipts",
            ),
        ):
            if type(values) is not tuple or any(
                not isinstance(item, expected_type) for item in values
            ):
                raise TypeError(f"evidence bundle {label} have the wrong type")
            ids = tuple(getattr(item, identifier) for item in values)
            if ids != tuple(sorted(set(ids))):
                raise QualificationContractError(
                    f"evidence bundle {label} must be unique and canonical"
                )
        if type(self.static_runtime_receipts) is not tuple:
            raise TypeError("evidence bundle static runtime receipts must be a tuple")
        static_pairs = tuple(
            (
                "d1" if isinstance(item, D1FamilyExecutionReceipt) else "d3",
                item.evidence_id,
            )
            for item in self.static_runtime_receipts
        )
        if static_pairs != tuple(sorted(set(static_pairs))):
            raise QualificationContractError(
                "evidence bundle static runtime receipts must be unique and canonical"
            )

    def validate_static_receipts(
        self,
        receipts: tuple[StaticEvidenceReceipt, ...],
    ) -> None:
        """Bind D1/D3 summaries to actual full generator/pipeline receipts."""

        attempted = {
            (item.gate_id.value, item.evidence_id): item
            for item in receipts
            if item.attempt_status is not AttemptStatus.NOT_RUN
        }
        runtime = {
            (
                "d1" if isinstance(item, D1FamilyExecutionReceipt) else "d3",
                item.evidence_id,
            ): item
            for item in self.static_runtime_receipts
        }
        if set(attempted) != set(runtime):
            raise QualificationContractError(
                "static runtime evidence differs from attempted D1/D3 receipts"
            )
        for pair, receipt in attempted.items():
            underlying = runtime[pair]
            if (
                receipt.attempt_status is not AttemptStatus.EVALUABLE
                or receipt.underlying_receipt_sha256 != underlying.canonical_sha256
                or receipt.checked_obligation_ids != underlying.obligation_ids
                or receipt.failed_obligation_ids != underlying.failed_obligation_ids
                or receipt.observation_fingerprints_sha256
                != underlying.observation_fingerprints_sha256
            ):
                raise QualificationContractError(
                    "static evidence summary differs from its full typed runtime "
                    "receipt"
                )
            if isinstance(underlying, D1FamilyExecutionReceipt):
                if (
                    receipt.pipeline_rerun_count != 0
                    or receipt.base_estimator_fingerprint_sha256 is not None
                    or receipt.transformed_estimator_fingerprint_sha256 is not None
                ):
                    raise QualificationContractError(
                        "D1 static receipt carries impossible pipeline fields"
                    )
            elif (
                receipt.pipeline_rerun_count != underlying.pipeline_rerun_count
                or receipt.base_estimator_fingerprint_sha256
                != underlying.base_estimator_fingerprint_sha256
                or receipt.transformed_estimator_fingerprint_sha256
                != underlying.transformed_estimator_fingerprint_sha256
            ):
                raise QualificationContractError(
                    "D3 static receipt differs from the actual rerun identities"
                )

    def validate_d1_receipts_against_protocol(
        self,
        protocol: QualificationProtocol,
        *,
        recomputed_receipts: tuple[
            D1FamilyExecutionReceipt,
            D1FamilyExecutionReceipt,
        ],
    ) -> None:
        """Require frozen thresholds and exact current-engine D1 reproduction."""

        if not isinstance(protocol, QualificationProtocol):
            raise TypeError("protocol must be a QualificationProtocol")
        persisted = tuple(
            item
            for item in self.static_runtime_receipts
            if isinstance(item, D1FamilyExecutionReceipt)
        )
        expected_ids = tuple(_D1_EXPECTED_CASES)
        if (
            tuple(item.evidence_id for item in persisted) != expected_ids
            or tuple(item.evidence_id for item in recomputed_receipts) != expected_ids
        ):
            raise QualificationContractError(
                "D1 runtime receipts differ from the exact family universe"
            )
        for receipt in persisted:
            receipt.validate_against_protocol(protocol)
        if persisted != recomputed_receipts or tuple(
            item.canonical_bytes for item in persisted
        ) != tuple(item.canonical_bytes for item in recomputed_receipts):
            raise QualificationContractError(
                "persisted D1 receipts differ from the fixed-development-seed "
                "current-engine recomputation"
            )

    def validate_summaries(
        self,
        *,
        protocol_canonical_sha256: str,
        source_binding_receipt_sha256: str,
        selection_freeze_artifact_sha256: str,
        selection_attempt_claim_sha256: str,
        core_cells: tuple[CoreCellSummary, ...],
        loop_cells: tuple[CrossedCellSummary, ...],
        nonvacuity: tuple[CrossedNonvacuitySummary, ...],
    ) -> None:
        for label, observed, expected in (
            (
                "protocol",
                self.protocol_canonical_sha256,
                protocol_canonical_sha256,
            ),
            (
                "source binding",
                self.source_binding_receipt_sha256,
                source_binding_receipt_sha256,
            ),
            (
                "selection freeze",
                self.selection_freeze_artifact_sha256,
                selection_freeze_artifact_sha256,
            ),
            (
                "selection attempt claim",
                self.selection_attempt_claim_sha256,
                selection_attempt_claim_sha256,
            ),
        ):
            if observed != expected:
                raise QualificationContractError(
                    f"evidence bundle {label} identity mismatch"
                )
        attempted_core = {
            item.core_cell_id: item
            for item in core_cells
            if item.attempt_status is not AttemptStatus.NOT_RUN
        }
        attempted_loop = {
            item.cell_id: item
            for item in loop_cells
            if item.attempt_status is not AttemptStatus.NOT_RUN
        }
        attempted_nonvacuity = {
            item.primary_unit_id: item
            for item in nonvacuity
            if item.attempt_status is not AttemptStatus.NOT_RUN
        }
        if set(attempted_core) != {
            item.core_cell_id for item in self.core_cell_receipts
        }:
            raise QualificationContractError(
                "evidence bundle core receipts differ from attempted D2 cells"
            )
        if set(attempted_loop) != {item.cell_id for item in self.loop_cell_receipts}:
            raise QualificationContractError(
                "evidence bundle loop receipts differ from attempted D4/D5 cells"
            )
        if set(attempted_nonvacuity) != {
            item.primary_unit_id for item in self.nonvacuity_receipts
        }:
            raise QualificationContractError(
                "evidence bundle nonvacuity receipts differ from attempted D4 units"
            )
        for receipt in self.core_cell_receipts:
            receipt.validate_summary(attempted_core[receipt.core_cell_id])
        for receipt in self.loop_cell_receipts:
            receipt.validate_summary(attempted_loop[receipt.cell_id])
        for receipt in self.nonvacuity_receipts:
            receipt.validate_summary(attempted_nonvacuity[receipt.primary_unit_id])

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_ceiling": self.claim_ceiling,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "source_binding_receipt_sha256": self.source_binding_receipt_sha256,
            "selection_freeze_artifact_sha256": (self.selection_freeze_artifact_sha256),
            "selection_attempt_claim_sha256": (self.selection_attempt_claim_sha256),
            "d2_confounder_matrix_receipt": (
                self.d2_confounder_matrix_receipt.to_dict()
            ),
            "static_runtime_receipts": [
                item.to_dict() for item in self.static_runtime_receipts
            ],
            "core_cell_receipts": [item.to_dict() for item in self.core_cell_receipts],
            "loop_cell_receipts": [item.to_dict() for item in self.loop_cell_receipts],
            "nonvacuity_receipts": [
                item.to_dict() for item in self.nonvacuity_receipts
            ],
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "subject_access_authorized": self.subject_access_authorized,
            "semantic_authority": self.semantic_authority,
            "integer_or_topology_authority": self.integer_or_topology_authority,
        }

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> QualificationEvidenceBundle:
        item = _mapping(value, label="qualification evidence bundle")
        _exact_keys(item, cls._ROOT_KEYS, label="qualification evidence bundle")
        for name, expected in (
            ("schema_version", EVIDENCE_BUNDLE_SCHEMA_VERSION),
            ("claim_ceiling", "level_0"),
            ("scientific_claim_eligible", False),
            ("subject_access_authorized", False),
            ("semantic_authority", False),
            ("integer_or_topology_authority", False),
        ):
            _constant(item[name], expected, label=f"evidence bundle {name}")
        sequence_values: dict[str, list[object]] = {}
        for name in (
            "static_runtime_receipts",
            "core_cell_receipts",
            "loop_cell_receipts",
            "nonvacuity_receipts",
        ):
            raw = item[name]
            if not isinstance(raw, list):
                raise QualificationContractError(f"{name} must be a JSON array")
            sequence_values[name] = raw
        return cls(
            protocol_canonical_sha256=require_sha256(
                item["protocol_canonical_sha256"],
                label="protocol_canonical_sha256",
            ),
            source_binding_receipt_sha256=require_sha256(
                item["source_binding_receipt_sha256"],
                label="source_binding_receipt_sha256",
            ),
            selection_freeze_artifact_sha256=require_sha256(
                item["selection_freeze_artifact_sha256"],
                label="selection_freeze_artifact_sha256",
            ),
            selection_attempt_claim_sha256=require_sha256(
                item["selection_attempt_claim_sha256"],
                label="selection_attempt_claim_sha256",
            ),
            d2_confounder_matrix_receipt=(
                D2CoreConfounderMatrixReceipt.from_dict(
                    item["d2_confounder_matrix_receipt"]
                )
            ),
            static_runtime_receipts=tuple(
                _parse_static_runtime_receipt(entry)
                for entry in sequence_values["static_runtime_receipts"]
            ),
            core_cell_receipts=tuple(
                CoreCellEvaluationReceipt.from_dict(entry)
                for entry in sequence_values["core_cell_receipts"]
            ),
            loop_cell_receipts=tuple(
                LoopCellEvaluationReceipt.from_dict(entry)
                for entry in sequence_values["loop_cell_receipts"]
            ),
            nonvacuity_receipts=tuple(
                NonvacuityEvaluationReceipt.from_dict(entry)
                for entry in sequence_values["nonvacuity_receipts"]
            ),
        )
